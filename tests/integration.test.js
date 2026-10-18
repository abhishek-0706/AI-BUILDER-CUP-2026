/* Browser regressions for the data and persistence boundary. AI responses are mocked. */
const assert=require('node:assert/strict');
const {chromium}=require('playwright');
const vm=require('node:vm'),fs=require('node:fs');
const ctx=vm.createContext({});vm.runInContext(fs.readFileSync('retail_data.js','utf8')+';globalThis.data=RETAIL_DATA;',ctx);
const base=process.env.RETAILIQ_URL||'http://localhost:5190/index.html?role=rep';
let checks=0;
const check=(condition,message)=>{assert.ok(condition,message);console.log('PASS '+message);checks++;};
(async()=>{
 const browser=await chromium.launch();
 try {
  const page=await browser.newPage({viewport:{width:1600,height:1100}});
  await require('./browser-utils').offlineNetwork(page,base);
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(base,{waitUntil:'networkidle'});
  check(await page.evaluate(()=>tradePrice(D.products.find(p=>p.id==='R01')))===54.6,'unit trade price rounds monetary arithmetic to two decimals');
  await page.evaluate(()=>{capture.R01={onShelf:0,oos:true};});
  await page.evaluate(()=>saveCapture());
  let events=await page.evaluate(()=>JSON.parse(localStorage.getItem('retailiq_demo_events')));
  check(events[0].store_id==='BLR-KOR-014'&&events[0].rep_id==='TSE-4417','capture logs canonical IDs');
  check(events[0].metadata.capture.R01.oos,'capture evidence persists');
  await page.reload({waitUntil:'networkidle'});
  check((await page.textContent('#recent-events')).includes('capture'),'manager sees saved event after reload');
  await page.evaluate(()=>{renderOrder();const id=Object.keys(orderQty)[0];orderQty[id]=4999;setVisit(1);});
  check(!(await page.evaluate(()=>Object.values(orderQty))).includes(4999),'edited order quantity does not leak between visits');
  await page.evaluate(()=>{
    renderPlanoResult(D.benchmark.rules.map((r,i)=>`RULE: ${i?'Unknown '+i:r.rule} | PASS | fine`).join('\n'));
  });
  check(!/judged criteria passed/.test(await page.textContent('#plano-out')),'unknown rules cannot complete a score');
  await page.evaluate(()=>{
    capture={};renderOrder();const p=D.products.find(p=>p.id==='R01');p.predictedUnitsPerDay=40;p.unitsOnOrder=100;
  });
  const forecastLine=await page.evaluate(()=>{const l=orderLines().find(l=>l.p.id==='R01');return {quantity:l.suggested,reasons:l.reasons};});
  check(forecastLine.quantity===684&&forecastLine.reasons.includes('Demand forecast'),'forecast sizing nets inbound inventory');
  await page.evaluate(async()=>{
    globalThis.sseText=await readGeminiResponse(new Response('data: {"candidates":[{"content":{"parts":[{"text":"Hello"}]}}]}'),()=>{});
  });
  check(await page.evaluate(()=>sseText)==='Hello','SSE consumes final chunk without newline');
  check(await page.evaluate(async()=>{
    try{await readGeminiResponse(new Response('data: {"error":{"message":"upstream failed"}}\n\n'),()=>{});return false;}
    catch(e){return e.message==='upstream failed';}
  }),'streamed API errors surface to users');
  // Simulate the real server contract, including server-backed mode without a browser Gemini key.
  const warehouse=JSON.parse(JSON.stringify(ctx.data));warehouse.source='bigquery';warehouse.products[0].price=991;
  const saved=[];let modelBody;
  await page.route('**/runtime-config.js',r=>r.fulfill({contentType:'application/javascript',body:'window.RETAILIQ_RUNTIME={backend:true};'}));
  await page.route('**/api/bootstrap',r=>r.fulfill({json:warehouse}));
  await page.route('**/api/visits/log**',r=>{
    if(r.request().method()==='POST'){saved.push(r.request().postDataJSON());return r.fulfill({json:{status:'logged'}});}
    return r.fulfill({json:{events:saved}});
  });
  await page.route('**/api/chat',r=>{modelBody=r.request().postDataJSON();return r.fulfill({contentType:'text/event-stream',body:'data: {"candidates":[{"content":{"parts":[{"text":"Server answer"}]}}]}\n\n'});});
  await page.reload({waitUntil:'networkidle'});
  check(await page.evaluate(()=>aiAvailable()&&!getKey()&&D.products[0].price===991),'server data and inference work without a browser Gemini key');
  check(await page.evaluate(()=>callGeminiVision('Audit','Check',[{mime:'image/jpeg',b64:'dGVzdA=='}],()=>{}))==='Server answer','vision uses server streaming proxy');
  check(modelBody.images.length===1&&modelBody.images[0].data==='dGVzdA==','vision frame contract reaches server');
  const modernModel=await page.evaluate(()=>/^gemini-3\.6(?:-|$)/i.test(MODEL));
  check(modelBody.max_output_tokens===6144,'vision inference has enough output budget for all assigned rules');
  await page.evaluate(()=>callGemini('System','Question',[],()=>{}));
  const proseBody=modelBody;
  check(modernModel?!Object.hasOwn(proseBody,'temperature'):proseBody.temperature===0.2,'text inference uses sampling parameters supported by its model');
  check(await page.evaluate(()=>samplingOptions(0.1,0.2,'gemini-3.5-flash-lite').temperature===0.1&&samplingOptions(undefined,0.2,'gemini-3.5-flash-lite').temperature===0.2),'older-model adapters preserve explicit and default temperature options');
  check(proseBody.system_prompt.includes('WRITING STYLE FOR EVERYTHING YOU OUTPUT'),'prose requests retain the application writing style');
  const schema={type:'object',properties:{value:{type:'number'},quote:{type:'string'}},required:['value','quote'],additionalProperties:false};
  const ticks=String.fromCharCode(96).repeat(3);
  const verbatim='20 to 22% retailer margin '+String.fromCharCode(0x2014)+' 330ml '+String.fromCharCode(0x20b9)+'70 **unchanged** __literal__ '+String.fromCharCode(96)+'code'+String.fromCharCode(96)+' '+ticks+'json literal'+ticks;
  const structuredPayload=JSON.stringify({value:70,quote:verbatim}),fenced=ticks+'json\n'+structuredPayload+'\n'+ticks;
  await page.route('**/api/chat',route=>{modelBody=route.request().postDataJSON();return route.fulfill({contentType:'text/event-stream',body:'data: '+JSON.stringify({candidates:[{content:{parts:[{text:fenced}]}}]})+'\n\n'});});
  const structured=await page.evaluate(schema=>callGemini('System','Return a numeric value and exact quote.',[],()=>{},{responseSchema:schema,temperature:0.1}),schema);
  check(JSON.stringify(modelBody.response_schema)===JSON.stringify(schema)&&(modernModel?!Object.hasOwn(modelBody,'temperature'):modelBody.temperature===0.1),'native JSON schema reaches the backend with model-compatible sampling');
  check(modelBody.max_output_tokens===8192,'structured inference reserves enough output tokens for complete JSON');
  check(structured===structuredPayload&&JSON.parse(structured).value===70&&JSON.parse(structured).quote===verbatim,'only outer JSON fences are removed; quoted percent, units, dashes and markup stay verbatim');
  check(!modelBody.system_prompt.includes('WRITING STYLE FOR EVERYTHING YOU OUTPUT')&&modelBody.system_prompt.includes('quoted source passages verbatim'),'structured backend requests omit prose rewriting instructions');
  const rawStream=await page.evaluate(async payload=>{
   const pieces=[payload.slice(0,17),payload.slice(17)];
   const body=pieces.map(text=>'data: '+JSON.stringify({candidates:[{content:{parts:[{text}]}}]})+'\n\n').join('');
   const chunks=[];const result=await readGeminiResponse(new Response(body),text=>chunks.push(text),{structured:true});
   return{result,lastChunk:chunks[chunks.length-1]};
  },structuredPayload);
  check(rawStream.result===structuredPayload&&rawStream.lastChunk===structuredPayload,'structured streaming preserves raw JSON across chunk boundaries');
  let developerBody;
  await page.route('https://generativelanguage.googleapis.com/**',route=>{
    const headers={'Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'content-type,x-goog-api-key','Access-Control-Allow-Methods':'POST,OPTIONS'};
    if(route.request().method()==='OPTIONS')return route.fulfill({status:204,headers,body:''});
    developerBody=route.request().postDataJSON();
    return route.fulfill({headers,contentType:'text/event-stream',body:'data: '+JSON.stringify({candidates:[{content:{parts:[{text:structuredPayload}]}}]})+'\n\n'});
  });
  const directAnswer=await page.evaluate(async schema=>{
   RetailAPI.enabled=false;localStorage.setItem('retailiq_gemini_key','TEST-ONLY-KEY');
   try{return await callGemini('System','Return a numeric value and exact quote.',[],()=>{},{responseSchema:schema,temperature:0.1});}
   finally{RetailAPI.enabled=true;localStorage.removeItem('retailiq_gemini_key');}
  },schema);
  const directConfig=developerBody.generationConfig;
  check(JSON.parse(directAnswer).value===70&&directConfig.responseMimeType==='application/json'&&JSON.stringify(directConfig.responseJsonSchema)===JSON.stringify(schema)&&(modernModel?!Object.hasOwn(directConfig,'temperature'):directConfig.temperature===0.1)&&directConfig.thinkingConfig.thinkingLevel==='MEDIUM','Developer API uses the native schema and supported 3.6 thinking/sampling configuration');
  check(directAnswer===structuredPayload&&!developerBody.systemInstruction.parts[0].text.includes('WRITING STYLE FOR EVERYTHING YOU OUTPUT'),'Developer API preserves exact JSON evidence without prose styling or cleanup');

  await page.evaluate(()=>logVisitEvent('audit','No facings',{score:0}));
  check(saved[0].store_id==='BLR-KOR-014'&&saved[0].rep_id==='TSE-4417','server logs include required store and rep identifiers');
  await page.route('**/api/visits/log**',r=>r.fulfill({status:503,json:{detail:'Database unavailable'}}));
  check(await page.evaluate(()=>logVisitEvent('audit','test'))===false,'failed writes do not report saved');
  check((await page.textContent('#event-status')).includes('Not saved'),'failed write is visible');
  await page.route('**/api/bootstrap',r=>r.fulfill({status:503,json:{detail:'Warehouse unavailable'}}));
  await page.reload({waitUntil:'networkidle'});
  check(!await page.evaluate(()=>aiAvailable()),'warehouse failure disables AI instead of using fixture data');
  check((await page.textContent('#data-status')).includes('Warehouse unavailable'),'warehouse failure explains why data could not load');
  check(errors.length===0,'no uncaught JavaScript errors: '+errors.join(', '));
  console.log(`${checks} integration checks passed`);
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
