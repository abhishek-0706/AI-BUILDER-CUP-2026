'use strict';
// Keep offline suites independent of font/CDN availability and block accidental AI requests.
async function offlineNetwork(page,base){
 const origin=new URL(base).origin;
 await page.route('**/*',route=>{
  const requested=new URL(route.request().url());
  if(requested.origin===origin||requested.protocol==='data:')return route.continue();
  if(['fonts.googleapis.com','fonts.gstatic.com'].includes(requested.hostname))
   return route.fulfill({status:200,contentType:'text/css',body:''});
  return route.abort('blockedbyclient');
 });
}
module.exports={offlineNetwork};
