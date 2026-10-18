/* Reproducible narrated walkthrough. Uses the labelled no-key scenario, never mocks live AI. */
'use strict';
const fs=require('node:fs'),path=require('node:path');
const {execFileSync}=require('node:child_process');
const {chromium}=require(path.resolve(__dirname,'../../node_modules/playwright'));
const {startServer}=require('../../tests/server');
const {offlineNetwork}=require('../../tests/browser-utils');
const root=path.resolve(__dirname,'../..');
const {values}=require('node:util').parseArgs({options:{narration:{type:'string'},output:{type:'string'},'voice-label':{type:'string'}}});
const narrationPath=path.resolve(root,values.narration||'tmp/submission-narration.json');
const output=path.resolve(root,values.output||'demo/RetailIQ_submission_walkthrough.mp4');
const clips=JSON.parse(fs.readFileSync(narrationPath,'utf8'));
const voiceLabel=values['voice-label']||'Windows system voice';
const outDir=path.join(root,'tmp/submission-recording');
fs.mkdirSync(outDir,{recursive:true});
const captions={
 intro:['RetailIQ: shelf evidence to accountable action','Recorded walkthrough | synthetic commercial context | no live model call'],
 observe:['Evidence with honest uncertainty','Own-brand audit and competitor benchmark are distinct questions'],
 confirm:['Verify the gap before ordering','Zero shelf facings + positive system stock = locate and reconcile stock'],
 save:['Save the originating visit and evidence','This example saves locally. A configured server persists to Firestore.'],
 manager:['Accountable review and measurable business value','Illustrative: 7 min x 1,320 visits = 154 h | INR 46,200 capacity - INR 6,600 cost target = INR 39,600; not measured savings'],
 order:['Quantities follow retail constraints','Forecast or sales average | inbound netting | cases | short product life'],
 draft:['A proposed order stays a draft','Human review and the enterprise order system control placement'],
 shopper:['One catalogue for product discovery','Available products, transparent prices and nutrition facts'],
 close:['Ready for a measured pilot','Google Cloud server implementation | Current hosting: free Firebase Spark demo | No live AI call in this recording']
};
(async()=>{
 const server=await startServer();let browser,context;
 try {
  browser=await chromium.launch();
  context=await browser.newContext({viewport:{width:1440,height:1000},deviceScaleFactor:1,recordVideo:{dir:outDir,size:{width:1440,height:1000}}});
  const clockStart=Date.now();const page=await context.newPage();const video=page.video();
  await offlineNetwork(page,server.url);
  await page.goto(server.url,{waitUntil:'networkidle'});
  await page.evaluate(()=>{
   const caption=document.createElement('div');caption.id='video-caption';
   caption.style.cssText='position:fixed;bottom:0;left:0;right:0;z-index:9999;padding:17px 28px;background:rgba(6,53,45,.97);color:white;border-top:3px solid #d3a36d;pointer-events:none;font-family:Segoe UI,Arial,sans-serif';
   document.body.append(caption);
  });
  const actions={
   intro:async()=>{},
   observe:async()=>{await page.click('#guided-demo-btn');await page.locator('#plano-out').scrollIntoViewIfNeeded();},
   confirm:async()=>{await page.click('#confirm-gap-btn');await page.locator('#capture-grid').scrollIntoViewIfNeeded();},
   save:async()=>{await page.locator('#save-audit-btn').scrollIntoViewIfNeeded();await page.click('#save-audit-btn');},
   manager:async()=>{await page.click('#tab-biz');await page.locator('#recent-events').scrollIntoViewIfNeeded();},
   order:async()=>{await page.click('#tab-rep');await page.evaluate(()=>openRepPane('order'));await page.locator('#order-list').scrollIntoViewIfNeeded();},
   draft:async()=>{await page.getByRole('button',{name:'Save proposed order',exact:true}).click();await page.click('#tab-biz');await page.locator('#recent-events').scrollIntoViewIfNeeded();},
   shopper:async()=>{await page.click('#tab-shop');await page.evaluate(()=>scrollTo(0,0));},
   close:async()=>{await page.click('#tab-rep');await page.evaluate(()=>openRepPane('plan'));await page.evaluate(()=>scrollTo(0,0));}
  };
  for(const scene of clips){
   await actions[scene.id]();
   const sceneCaption=[...captions[scene.id]];
   if(scene.id==='intro'&&values['voice-label'])sceneCaption[1]+=' | '+voiceLabel;
   await page.evaluate(([title,subtitle])=>{const c=document.getElementById('video-caption');c.replaceChildren();const t=document.createElement('div');t.textContent=title;t.style.cssText='font-size:23px;font-weight:650;margin-bottom:5px';const s=document.createElement('div');s.textContent=subtitle;s.style.cssText='font-size:14px;color:#d7e6dd';c.append(t,s);},sceneCaption);
   scene.startMs=Date.now()-clockStart;
   console.log('Scene '+scene.id+' at '+scene.startMs+'ms');
   await page.waitForTimeout(scene.durationMs+450);
  }
  await page.screenshot({path:path.join(root,'tmp/submission-final-screen.png')});
  await context.close();context=null;
  const recorded=await video.path(),ffmpeg=require('./node_modules/ffmpeg-static');
  const timing=require('./align_recording').alignCapturedScenes(ffmpeg,recorded,clips);
  clips.splice(0,clips.length,...timing.scenes);
  const args=['-y','-i',recorded];for(const scene of clips)args.push('-i',scene.audio);
  const filters=clips.map((s,i)=>`[${i+1}:a]adelay=${s.startMs}:all=1[a${i}]`);
  filters.push(clips.map((_,i)=>`[a${i}]`).join('')+`amix=inputs=${clips.length}:normalize=0:dropout_transition=0[a]`);
  args.push('-filter_complex',filters.join(';'),'-map','0:v','-map','[a]','-vf','tpad=stop_mode=clone:stop_duration='+timing.padSeconds.toFixed(3),'-c:v','libx264','-preset','fast','-crf','22','-pix_fmt','yuv420p','-r','25','-c:a','aac','-b:a','128k','-movflags','+faststart',output);
  execFileSync(ffmpeg,args,{stdio:['ignore','ignore','pipe'],timeout:120000});
  const metadata={recorded_example:true,model_calls:0,narration:voiceLabel,alignment:timing.alignment,scenes:clips,output};
  const metadataPath=path.join(root,'tmp',path.basename(output,'.mp4')+'.recording.json');
  fs.writeFileSync(metadataPath,JSON.stringify(metadata,null,2));
  if(!values.output)fs.writeFileSync(path.join(root,'tmp/submission-recording.json'),JSON.stringify(metadata,null,2));
  console.log('Wrote '+output+' ('+(fs.statSync(output).size/1048576).toFixed(1)+' MB)');
 }finally{if(context)await context.close();if(browser)await browser.close();await server.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
