'use strict';
// Free-profile safety/transport regressions. All model responses are intercepted locally.
const assert=require('node:assert/strict');
const {chromium}=require('playwright');
const {offlineNetwork}=require('./browser-utils');
const {assertFreeLiveOptions,assertFreeRuntime}=require('./eval-policy');
const url=process.env.RETAILIQ_URL||'http://localhost:5190/index.html?role=rep';
let checks=0;
const check=(ok,name)=>{assert.ok(ok,name);checks++;console.log('PASS '+name);};
const rejects=(action,name)=>{assert.throws(action);checks++;console.log('PASS '+name);};
(async()=>{
 const browser=await chromium.launch();
 try{
  const page=await browser.newPage({viewport:{width:1600,height:1100}});
  await offlineNetwork(page,url);
  const errors=[],apiRequests=[],modelRequests=[];
  page.on('pageerror',error=>errors.push(error.message));
  await page.addInitScript(()=>{
   localStorage.setItem('retailiq_gemini_key','CACHED-UNCONFIRMED-TEST-KEY');
   localStorage.removeItem('retailiq_free_key_confirmation');
  });
  await page.route('**/api/**',route=>{apiRequests.push(route.request().url());return route.fulfill({status:503,json:{detail:'Unexpected backend request from free profile'}});});
  const schema={type:'object',properties:{value:{type:'number'},quote:{type:'string'}},required:['value','quote'],additionalProperties:false};
  const quote='22% margin '+String.fromCharCode(0x2014)+' **literal** '+String.fromCharCode(96)+'units'+String.fromCharCode(96);
  const payload=JSON.stringify({value:70,quote});
  let quota=false;
  await page.route('https://generativelanguage.googleapis.com/**',route=>{
   const headers={'Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'content-type,x-goog-api-key','Access-Control-Allow-Methods':'POST,OPTIONS'};
   if(route.request().method()==='OPTIONS')return route.fulfill({status:204,headers,body:''});
   modelRequests.push({url:route.request().url(),body:route.request().postDataJSON()});
   if(quota)return route.fulfill({status:429,headers,json:{error:{message:'Test-only free quota exhausted'}}});
   return route.fulfill({headers,contentType:'text/event-stream',body:'data: '+JSON.stringify({candidates:[{content:{parts:[{text:payload}]}}]})+'\n\n'});
  });
  await page.goto(url,{waitUntil:'networkidle'});
  check(await page.evaluate(()=>window.RETAILIQ_RUNTIME.free_only&&!RetailAPI.enabled),'static release defaults to free-only with backend inference disabled');
  check(await page.evaluate(()=>MODEL)==='gemini-3.5-flash-lite','free profile selects its configured optional model');
  check(await page.evaluate(()=>!getKey()&&!aiAvailable()&&localStorage.getItem('retailiq_gemini_key')==='CACHED-UNCONFIRMED-TEST-KEY'),'cached keys remain stored but inactive without key-specific confirmation');
  const unconfirmed=await page.evaluate(async()=>{
   const rejected=[];
   for(const action of [()=>callGemini('System','Test',[],()=>{}),()=>callGeminiVision('System','Test',[{mime:'image/jpeg',b64:'dGVzdA=='}],()=>{})]){
    try{await action();rejected.push(false);}catch{rejected.push(true);}
   }
   return rejected.every(Boolean);
  });
  check(unconfirmed&&modelRequests.length===0&&apiRequests.length===0,'unconfirmed cached keys trigger neither model nor backend requests');
  await page.evaluate(()=>openSettings());
  await page.locator('#modal .btn-primary').click();
  check(!await page.evaluate(()=>aiAvailable())&&/billing disabled/i.test(await page.textContent('#key-cost-status')),'saving a key requires explicit unbilled-project confirmation');
  await page.check('#free-key-confirm');
  await page.locator('#modal .btn-primary').click();
  check(await page.evaluate(()=>aiAvailable()&&localStorage.getItem('retailiq_free_key_confirmation')===keyFingerprint(getKey())),'explicit confirmation activates only the matching stored key');
  check(await page.evaluate(()=>localStorage.getItem('retailiq_free_key_confirmation')!==localStorage.getItem('retailiq_gemini_key')),'confirmation storage contains an identity fingerprint instead of another raw key copy');
  await page.evaluate(()=>localStorage.setItem('retailiq_gemini_key','CHANGED-UNCONFIRMED-TEST-KEY'));
  check(!await page.evaluate(()=>aiAvailable()||getKey()),'changing a cached key invalidates its previous confirmation');
  await page.evaluate(()=>openSettings());
  await page.check('#free-key-confirm');
  await page.fill('#key-in','CONFIRMED-FREE-PROFILE-TEST-KEY');
  check(!await page.isChecked('#free-key-confirm'),'editing the key clears the confirmation checkbox');
  await page.check('#free-key-confirm');
  await page.locator('#modal .btn-primary').click();
  check(await page.evaluate(()=>aiAvailable()&&getKey()==='CONFIRMED-FREE-PROFILE-TEST-KEY'),'a replacement key requires and receives its own explicit confirmation');
  const answer=await page.evaluate(schema=>callGemini('System','Return JSON.',[],()=>{},{responseSchema:schema,temperature:0.1}),schema);
  check(answer===payload&&JSON.parse(answer).quote===quote,'optional free-profile structured transport preserves raw numeric JSON and exact symbols');
  check(modelRequests.length===1&&modelRequests[0].url.includes('/gemini-3.5-flash-lite:')&&apiRequests.length===0,'confirmed optional requests stay on the configured direct model with no backend fallback');
  check(JSON.stringify(modelRequests[0].body.generationConfig.responseJsonSchema)===JSON.stringify(schema)&&!modelRequests[0].body.systemInstruction.parts[0].text.includes('WRITING STYLE FOR EVERYTHING YOU OUTPUT'),'free-profile native schemas preserve the JSON/prose separation');
  quota=true;
  const quotaMessage=await page.evaluate(async()=>{try{await callGemini('System','Quota test',[],()=>{});return '';}catch(error){return errMsg(error);}});
  check(/free quota/i.test(quotaMessage)&&/no paid fallback/i.test(quotaMessage),'HTTP 429 explains the free-quota stop and absence of a paid fallback');
  check(await page.evaluate(()=>freeQuotaStopped()&&!aiAvailable()),'HTTP 429 disables AI for the current page');
  const countAtStop=modelRequests.length;
  const stopped=await page.evaluate(async()=>{
   const rejected=[];
   for(const action of [()=>callGemini('System','Retry test',[],()=>{}),()=>callGeminiVision('System','Retry test',[{mime:'image/jpeg',b64:'dGVzdA=='}],()=>{})]){
    try{await action();rejected.push(false);}catch(error){rejected.push(error.message==='FREE_QUOTA_STOP');}
   }
   return rejected.every(Boolean);
  });
  await page.waitForTimeout(200);
  check(stopped&&modelRequests.length===countAtStop,'text and vision calls stop before fetch after quota exhaustion');
  check(apiRequests.length===0&&modelRequests.every(r=>r.url.includes('/gemini-3.5-flash-lite:')),'quota exhaustion triggers no backend, alternate model or automatic retry');
  await page.evaluate(()=>openSettings());
  await page.locator('#modal .btn-primary').click();
  check(await page.evaluate(()=>freeQuotaStopped()&&!aiAvailable()),'resaving the same confirmed key cannot clear the page quota stop');
  await page.click('#guided-demo-btn');
  check(await page.evaluate(()=>lastAudit?.source==='recorded-example'&&lastAudit.rules.length===8),'the recorded guided scenario remains usable after free quota exhaustion');
  await page.route('**/runtime-config.js',route=>route.fulfill({contentType:'application/javascript',body:"window.RETAILIQ_RUNTIME={backend:true,free_only:true,model:'gemini-3.5-flash-lite'};"}));
  await page.reload({waitUntil:'networkidle'});
  check(await page.evaluate(()=>!RetailAPI.enabled&&window.RETAILIQ_RUNTIME.backend),'free-only runtime overrides a conflicting backend-enabled setting');
  check(apiRequests.length===0,'free-profile initialization and manager events never contact application APIs');
  rejects(()=>assertFreeLiveOptions({confirmed:false,key:'test-key'}),'live evaluator refuses missing explicit free-tier attestation');
  rejects(()=>assertFreeLiveOptions({confirmed:true,key:''}),'live evaluator refuses a missing operator key');
  rejects(()=>assertFreeLiveOptions({confirmed:true,key:'test-key',url:'https://paid-example.run.app'}),'live evaluator rejects Cloud Run targets before navigation');
  rejects(()=>assertFreeRuntime({backendEnabled:true,freeOnly:true,model:'gemini-3.5-flash-lite'}),'live evaluator rejects backend inference even when a free-only flag is present');
  rejects(()=>assertFreeRuntime({backendEnabled:false,freeOnly:false,model:'gemini-3.5-flash-lite'}),'live evaluator rejects profiles without the free-only policy');
  rejects(()=>assertFreeRuntime({backendEnabled:false,freeOnly:true,model:'gemini-3.6-flash'}),'live evaluator rejects an unapproved alternate model');
  assertFreeLiveOptions({confirmed:true,key:'test-key',url:'http://127.0.0.1:5190'});
  assertFreeRuntime({backendEnabled:false,freeOnly:true,model:'gemini-3.5-flash-lite'});
  check(true,'live evaluator accepts only the explicitly attested direct free-profile contract');
  check(errors.length===0,'no uncaught JavaScript errors: '+errors.join(', '));
  console.log(checks+' free-profile checks passed; every model response was mocked');
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});

