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
function assertFreeBackendOptions({confirmed,url,key,token}){
 if(!confirmed)throw new Error('Backend evaluation requires explicit --confirm-free-tier.');
 if(!url)throw new Error('Backend evaluation requires RETAILIQ_URL.');
 const target=new URL(url);
 if(target.protocol!=='https:'||target.username||target.password||target.search||target.hash)throw new Error('Backend evaluation requires an HTTPS base URL without credentials, query or fragment.');
 if(key||token)throw new Error('Anonymous backend evaluation refuses supplied API keys or access tokens.');
}
function assertFreeBackendConfig(c){
 if(c.provider!=='gemini_free'||c.model!=='gemini-3.5-flash-lite'||c.data_source!=='synthetic_fixture'||c.public_judge!==true||c.auth_mode!=='anonymous_synthetic_session'||c.free_tier_attested!==true||c.chat_proxy!=='/api/chat')throw new Error('Backend evaluation refuses a provider, model, catalogue, authentication or free-tier configuration mismatch.');
}
function assertFreeBackendRuntime({backendEnabled,ready,model}){
 if(backendEnabled!==true||ready!==true||model!=='gemini-3.5-flash-lite')throw new Error('Backend evaluation requires the ready, approved production adapter.');
}
module.exports={assertFreeLiveOptions,assertFreeRuntime,assertFreeBackendOptions,assertFreeBackendConfig,assertFreeBackendRuntime};

