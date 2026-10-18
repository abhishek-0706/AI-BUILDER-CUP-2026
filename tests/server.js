'use strict';
const http=require('node:http'),fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'..');
const types={'.html':'text/html','.js':'application/javascript','.css':'text/css','.svg':'image/svg+xml','.mp4':'video/mp4','.png':'image/png','.jpg':'image/jpeg','.json':'application/json'};
async function startServer(){
 const server=http.createServer((req,res)=>{
  let file;
  try{file=path.resolve(root,'.'+decodeURIComponent(new URL(req.url,'http://local').pathname));}
  catch{res.writeHead(400);res.end();return;}
  if(file!==root&&!file.startsWith(root+path.sep)){res.writeHead(403);res.end();return;}
  if(file===root)file=path.join(root,'index.html');
  // No external network is needed; browser tests also block remote requests.
  fs.stat(file,(error,stat)=>{
   if(error||!stat.isFile()){res.writeHead(404);res.end();return;}
   res.writeHead(200,{'Content-Type':types[path.extname(file)]||'application/octet-stream','Cache-Control':'no-store'});
   fs.createReadStream(file).pipe(res);
  });
 });
 await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(0,'127.0.0.1',resolve);});
 return{url:'http://127.0.0.1:'+server.address().port+'/index.html?role=rep',close:()=>new Promise(resolve=>server.close(resolve))};
}
module.exports={startServer};
