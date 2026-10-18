'use strict';
const {spawn}=require('node:child_process');
const fs=require('node:fs'),path=require('node:path');
const {startServer}=require('./server');
const root=path.resolve(__dirname,'..');
const suites=['structural.test.js','security.test.js','integration.test.js','workflow.test.js','free-mode.test.js','eval.js'];
(async()=>{
 const server=await startServer(),results=[];
 try{
  for(const suite of suites){
   console.log('\n=== '+suite+' ===');
   const started=Date.now();
   try{
    const code=await new Promise((resolve,reject)=>{
     const child=spawn(process.execPath,[path.join(__dirname,suite)],{
      cwd:root,env:{...process.env,RETAILIQ_URL:server.url},stdio:'inherit'});
     const timer=setTimeout(()=>{child.kill();reject(new Error(suite+' exceeded 180 seconds.'));},180000);
     child.once('error',e=>{clearTimeout(timer);reject(e);});
     child.once('exit',code=>{clearTimeout(timer);resolve(code??1);});
    });
    results.push({suite,pass:code===0,exit_code:code,duration_ms:Date.now()-started});
   }catch(error){
    results.push({suite,pass:false,error:error.message,duration_ms:Date.now()-started});console.error(error.message);
   }
  }
 }finally{await server.close();}
 const report={run_mode:'offline_regression',provider:'none',model_calls:0,created_at:new Date().toISOString(),results,
  pass:results.length===suites.length&&results.every(r=>r.pass),limitations:['Browser backend responses are mocked.','No cloud deployment or live model quality is measured.']};
 fs.mkdirSync(path.join(root,'tmp'),{recursive:true});
 fs.writeFileSync(path.join(root,'tmp','test-report.json'),JSON.stringify(report,null,2));
 console.log('\n'+results.filter(r=>r.pass).length+'/'+results.length+' suites passed; report: tmp/test-report.json');
 process.exitCode=report.pass?0:1;
})().catch(e=>{console.error(e);process.exitCode=1;});
