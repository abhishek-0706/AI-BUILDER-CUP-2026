'use strict';
/* End-to-end browser regression. Backend/model responses are controlled test doubles.
   These checks verify rendering, saved evidence, arithmetic and context isolation. */
const assert=require('node:assert/strict');
const {chromium}=require('playwright');
const {data}=require('./eval-core');
const url=process.env.RETAILIQ_URL||'http://localhost:5190/index.html?role=rep';
let checks=0;
const check=(ok,name)=>{assert.ok(ok,name);checks++;console.log('PASS '+name);};
const clone=x=>JSON.parse(JSON.stringify(x));
(async()=>{
 const browser=await chromium.launch();
 try{
  const page=await browser.newPage({viewport:{width:1600,height:1100}});
  await require('./browser-utils').offlineNetwork(page,url);
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.route('**/runtime-config.js',route=>route.fulfill({contentType:'application/javascript',body:'window.RETAILIQ_RUNTIME={backend:false,free_only:false};'}));
  await page.goto(url,{waitUntil:'networkidle'});
  // Every interval must use the same coordinate system as its point estimate.
  await page.click('#tab-biz');
  const geometry=await page.evaluate(()=>[...document.querySelectorAll('.bar.fc')].map((bar,i)=>{
   const b=bar.getBoundingClientRect(),r=bar.querySelector('.band').getBoundingClientRect(),f=D.forecast[i];
   return{topError:Math.abs(r.top-(b.bottom-b.height*f.upper/f.predicted)),
    bottomError:Math.abs(r.bottom-(b.bottom-b.height*f.lower/f.predicted))};
  }));
  check(geometry.length===7&&geometry.every(g=>g.topError<3&&g.bottomError<3),'forecast interval bounds align with the revenue axis');
  await page.setViewportSize({width:390,height:844});
  for(const tab of ['#tab-biz','#tab-rep','#tab-shop']){
   await page.selectOption('#mobile-role',tab.replace('#tab-',''));
   const dimensions=await page.evaluate(()=>({content:document.documentElement.scrollWidth,viewport:innerWidth}));
   check(dimensions.content<=dimensions.viewport+2,'mobile '+tab+' fits the viewport ('+dimensions.content+'px)');
  }
  await page.setViewportSize({width:1600,height:1100});
  await page.evaluate(()=>{document.getElementById('debrief-in').value='PRIVATE NOTE FROM VISIT A';setVisit(1);});
  check(await page.inputValue('#debrief-in')==='','debrief notes clear when switching visits');
  // An in-flight shopper answer must not append to the next shopper's history.
  await page.evaluate(()=>{
   localStorage.setItem('retailiq_gemini_key','test-key');
   window.originalCallGemini=callGemini;
   callGemini=()=>new Promise(resolve=>{window.finishOldShopper=resolve;});
   document.getElementById('chat-in').value='PRIVATE QUESTION FROM SHOPPER A';
   window.oldShopperRequest=sendChat();
  });
  await page.waitForFunction(()=>typeof finishOldShopper==='function');
  await page.evaluate(()=>{setProfile(1);finishOldShopper('PRIVATE ANSWER FOR SHOPPER A');});
  await page.evaluate(()=>oldShopperRequest);
  check(await page.evaluate(()=>chatHistory.length===0),'late reply does not contaminate the next shopper history');
  check(!(await page.textContent('#chat-body')).includes('PRIVATE ANSWER'),'late reply does not appear for the next shopper');
  await page.evaluate(()=>{callGemini=originalCallGemini;localStorage.removeItem('retailiq_gemini_key');});
  // Guided evidence uses the production parser and deterministic sample, no model call.
  await page.click('#tab-rep');
  await page.click('#guided-demo-btn');
  check(await page.inputValue('#audit-mode')==='own','guided evidence selects the own-brand planogram');
  await page.click('#sample-audit-btn');
  check((await page.textContent('#plano-out')).includes('judged criteria passed'),'sample evidence passes through the scored rule renderer');
  const sample=await page.evaluate(()=>({audit:lastAudit,qty:orderLines().find(l=>l.p.id==='R01')?.suggested}));
  check(sample.audit?.brand==='Protiva'&&sample.audit?.rules.length===8,'own-brand audit checks all eight assigned rules');
  check(sample.audit?.score!=null&&sample.audit.score<100,'guided evidence exposes a visible compliance gap');
  await page.click('#save-audit-btn');
  const saved=await page.evaluate(()=>JSON.parse(localStorage.getItem('retailiq_demo_events')||'[]').find(e=>e.event_type==='audit'));
  check(saved?.metadata?.audit?.score===sample.audit.score,'saved audit contains its computed score');
  check(Array.isArray(saved?.metadata?.audit?.rules)&&saved.metadata.audit.rules.length===8,'saved audit retains the rule evidence');
  check(!!saved?.metadata?.audit?.mode,'saved audit explicitly identifies own-brand or benchmark mode');
  check(saved?.metadata?.evidence?.retained===false&&saved.metadata.evidence.source==='recorded-example','recorded example does not claim a retained live evidence photo');
  // Resolve an old audit after switching visit: no rendered score or incorrectly filed event.
  await page.evaluate(()=>{
   localStorage.setItem('retailiq_gemini_key','test-key');
   window.originalVision=callGeminiVision;
   shelfFrames=[{b64:'dGVzdA==',mime:'image/jpeg'}];
   window.oldAuditCount=JSON.parse(localStorage.getItem('retailiq_demo_events')||'[]').length;
   callGeminiVision=()=>new Promise(resolve=>{window.finishOldAudit=resolve;});
   window.oldAuditRequest=checkPlano();
  });
  await page.waitForFunction(()=>typeof finishOldAudit==='function');
  await page.evaluate(()=>{
   const reply=D.planogram.rules.map(r=>'RULE: '+r.rule+' | PASS | clear').join('\n');
   setVisit(1);finishOldAudit(reply);
  });
  await page.evaluate(()=>oldAuditRequest);
  check(await page.evaluate(()=>lastAudit===null),'late audit does not attach to a different visit');
  check(await page.evaluate(()=>JSON.parse(localStorage.getItem('retailiq_demo_events')||'[]').length===oldAuditCount),'late audit creates no event for the wrong visit');
  await page.evaluate(()=>{callGeminiVision=originalVision;localStorage.removeItem('retailiq_gemini_key');});
  await page.evaluate(()=>{setAuditMode('benchmark');renderPlanoResult(D.benchmark.rules.map(r=>'RULE: '+r.rule+' | PASS | visible').join('\n'));});
  check(await page.evaluate(()=>lastAudit?.mode==='benchmark'&&lastAudit.rules.length===7&&lastAudit.brand===D.benchmark.brand),'competitor benchmark remains scoped to its seven observable rules');
  // A warehouse field is untrusted even when the server authenticated successfully.
  const warehouse=clone(data);
  warehouse.source='bigquery';
  warehouse.promotions[0].name='<img src=x onerror="window.__warehouseXss=1">';
  warehouse.promotions[0].discount='<svg onload="window.__warehouseXss=2">';
  warehouse.products[0].name='<img src=x onerror="window.__warehouseXss=3">';
  warehouse.kbDocs[0].url='javascript:window.__warehouseXss=4';
  let pitchBody;
  await page.route('**/runtime-config.js',route=>route.fulfill({contentType:'application/javascript',body:'window.RETAILIQ_RUNTIME={backend:true,evidence_enabled:true};'}));
  await page.route('**/api/bootstrap',route=>route.fulfill({json:warehouse}));
  await page.route('**/api/visits/log**',route=>route.fulfill({json:{events:[],status:'logged'}}));
  await page.route('**/api/agent/pitch-brief',route=>{pitchBody=route.request().postDataJSON();return route.fulfill({json:{
   opening:'A grounded next step.',key_claims:['Evidence-backed draft [KB-103].'],sources:['KB-103'],close:'Confirm the proposal?',evidence:[{doc_id:'KB-103',title:'Synthetic trade sheet',fact:warehouse.kbDocs.find(k=>k.id==='KB-103').fact,is_synthetic:true}],guardrail_flags:[]}});});
  await page.reload({waitUntil:'networkidle'});
  await page.click('#tab-biz');
  await page.waitForTimeout(150);
  check(!await page.evaluate(()=>window.__warehouseXss),'warehouse promotion and product markup cannot execute');
  check((await page.textContent('#promo-list')).includes('<img'),'promotion markup is rendered as literal text');
  await page.evaluate(()=>{renderCitations('[KB-101]',document.getElementById('pitch-cites'));toggleCite('KB-101');});
  check(await page.locator('a[href^="javascript:"]').count()===0,'source links never expose executable URL schemes');
  await page.click('#tab-rep');
  await page.evaluate(()=>genPitch());
  check(!!pitchBody&&pitchBody.buyer_context.includes(warehouse.visits[0].id),'pitch UI calls the validated server pitch agent');
  check(pitchBody.buyer_context.length<=4000,'pitch buyer context respects the server validation limit');
  check((await page.textContent('#pitch-out')).includes('Evidence-backed draft'),'validated pitch response renders');
  for(const [name,claim] of [['unknown','UNSUPPORTED DRAFT [KB-99999].'],['missing','UNSUPPORTED DRAFT without a source.']]){
   await page.route('**/api/agent/pitch-brief',route=>route.fulfill({json:{opening:'Draft',key_claims:[claim],sources:['KB-103'],close:'Ask',evidence:[{doc_id:'KB-103',title:'Trade sheet',fact:'Supplied evidence',is_synthetic:true}]}}));
   await page.evaluate(()=>genPitch());
   check(/missing or unknown evidence citation/.test(await page.textContent('#pitch-out')),'pitch with '+name+' citations is withheld');
  }
  // Retained evidence is authenticated on the same origin and rendered as a temporary blob.
  const privatePhotoURI='gs://private-evidence/visits/test.jpg',photoToken='TEST-PHOTO-ACCESS-TOKEN';
  const retainedEvent={event_type:'audit',visit_id:warehouse.visits[0].id,store_id:warehouse.store.storeId,
   rep_id:warehouse.rep.employeeId,summary:'Retained shelf evidence',created_at:'2026-10-18T12:00:00Z',
   metadata:{audit:{brand:'Protiva',source:'live-model',frames:1,rules:[]},evidence:{retained:true,gcs_uri:privatePhotoURI}}};
  let photoRequest;
  await page.route('**/api/visits/log**',route=>route.fulfill({json:{events:[retainedEvent]}}));
  await page.route('**/api/evidence/image**',route=>{
   photoRequest={url:route.request().url(),authorization:route.request().headers().authorization};
   return route.fulfill({contentType:'image/jpeg',body:require('node:fs').readFileSync(require('node:path').join(__dirname,'..','demo','samples','shelf_compliant.jpg'))});
  });
  await page.evaluate(token=>{
   sessionStorage.setItem('retailiq_access_token',token);
   window.revokedEvidenceURLs=[];window.originalRevokeEvidenceURL=URL.revokeObjectURL.bind(URL);
   URL.revokeObjectURL=value=>{revokedEvidenceURLs.push(value);originalRevokeEvidenceURL(value);};
  },photoToken);
  await page.click('#tab-biz');await page.evaluate(()=>refreshVisitEvents());
  check(await page.locator('.view-evidence-photo').count()===1,'manager offers review for retained private evidence');
  await page.click('.view-evidence-photo');
  await page.waitForSelector('#evidence-viewer',{state:'visible'});
  await page.waitForFunction(()=>document.getElementById('evidence-image')?.naturalWidth>0);
  check(photoRequest?.authorization==='Bearer '+photoToken,'retained photo fetch sends the application bearer header');
  check(new URL(photoRequest.url).searchParams.get('gcs_uri')===privatePhotoURI&&!photoRequest.url.includes(photoToken),'retained photo URL contains the object reference and no access token');
  const privateBlob=await page.getAttribute('#evidence-image','src');
  check(privateBlob?.startsWith('blob:'),'retained photo renders through a local blob URL');
  check(await page.locator('a[href^="gs://"]').count()===0,'private storage objects are never exposed as public links');
  await page.click('#close-evidence');
  check(!await page.locator('#evidence-viewer').isVisible(),'manager can close the evidence viewer');
  check(await page.evaluate(blob=>revokedEvidenceURLs.includes(blob),privateBlob),'closing evidence revokes its temporary blob URL');
  // The explicit judge scenario must never contact a protected API or use an existing key.
  const demoApiRequests=[],demoModelRequests=[];
  await page.route('**/api/**',route=>{demoApiRequests.push(route.request().url());return route.fulfill({status:503,json:{detail:'Unexpected API call from recorded demo'}});});
  page.on('request',request=>{if(request.url().includes('generativelanguage.googleapis.com'))demoModelRequests.push(request.url());});
  await page.addInitScript(()=>localStorage.setItem('retailiq_gemini_key','SENTINEL_MODEL_KEY'));
  const recordedURL=new URL(url);recordedURL.searchParams.set('demo','recorded');
  await page.goto(recordedURL.href,{waitUntil:'networkidle'});
  check(await page.evaluate(()=>RetailAPI.recordedDemo&&!RetailAPI.enabled&&!aiAvailable()),'explicit recorded mode disables backend and live AI even with a stored key');
  check(await page.evaluate(()=>lastAudit?.brand==='Protiva'&&lastAudit.rules.length===8),'recorded judge URL opens the eight-rule guided scenario');
  check(/recorded/i.test(await page.textContent('#data-status')),'recorded judge URL visibly labels its evidence mode');
  const countBefore=await page.evaluate(()=>JSON.parse(localStorage.getItem('retailiq_demo_events')||'[]').length);
  await page.click('#save-audit-btn');
  check(await page.evaluate(()=>JSON.parse(localStorage.getItem('retailiq_demo_events')||'[]').length)===countBefore+1,'explicit recorded mode saves only a local visit event');
  check(await page.evaluate(async()=>{try{await callGemini('system','test',[],()=>{});return false;}catch{return true;}}),'recorded mode rejects direct text-model calls');
  check(await page.evaluate(async()=>{try{await callGeminiVision('system','test',[{mime:'image/jpeg',b64:'dGVzdA=='}],()=>{});return false;}catch{return true;}}),'recorded mode rejects direct vision-model calls');
  check(demoApiRequests.length===0&&demoModelRequests.length===0,'recorded judge mode makes zero API or model requests');
  check(errors.length===0,'no uncaught JavaScript errors: '+errors.join(', '));
  console.log(checks+' workflow checks passed');
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
