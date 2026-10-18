'use strict';
// This runner has no paid/provider fallback under the current free-only policy.
function assertFreeLiveOptions({confirmed,key,url}){
 if(!confirmed)throw new Error('Free-only live evaluation requires explicit --confirm-free-tier for an operator-confirmed unbilled AI Studio key.');
 if(!key||!key.trim())throw new Error('Free-only live evaluation requires GEMINI_API_KEY from an unbilled AI Studio project.');
 if(url){
  const host=new URL(url).hostname.toLowerCase();
  if(host.endsWith('.run.app')||host.endsWith('.cloudfunctions.net')||host==='aiplatform.googleapis.com'||host.endsWith('.aiplatform.googleapis.com'))
   throw new Error('Free-only policy refuses Cloud Run, Cloud Functions and Vertex targets before navigation.');
 }
}
function assertFreeRuntime({backendEnabled,freeOnly,model}){
 if(backendEnabled||!freeOnly)throw new Error('Free-only policy refuses backend/Vertex inference. Use the free-only static profile.');
 if(model!=='gemini-3.5-flash-lite')throw new Error('Free-only evaluation permits only the explicitly selected free-profile model.');
}
module.exports={assertFreeLiveOptions,assertFreeRuntime};

