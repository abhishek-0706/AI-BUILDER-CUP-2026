/* Same-origin backend adapter. Static hosting remains an explicit demo. */
const recordedDemoRequested=new URLSearchParams(location.search).get('demo')==='recorded';
window.RetailAPI = {
  recordedDemo:recordedDemoRequested,
  enabled: !recordedDemoRequested && !window.RETAILIQ_RUNTIME?.free_only && !!window.RETAILIQ_RUNTIME?.backend,
  ready: false,
  headers() {
    const token = sessionStorage.getItem('retailiq_access_token');
    return {'Content-Type':'application/json', ...(token ? {Authorization:'Bearer '+token} : {})};
  },
  async json(path, options={}) {
    const res = await fetch(path, {...options, headers:{...this.headers(),...options.headers}});
    let data;
    try { data = await res.json(); } catch { throw new Error('The server returned an unreadable response.'); }
    if(!res.ok) {
      const detail = typeof data.detail==='string' ? data.detail : data.detail?.detail;
      throw new Error(detail || 'Server request failed ('+res.status+').');
    }
    return data;
  },
  async chat(systemPrompt, message, history, frames, onChunk, options={}) {
    const res = await fetch('/api/chat', {
      method:'POST', headers:this.headers(),
      body:JSON.stringify({system_prompt:systemPrompt+(options.responseSchema?JSON_REPLY_RULES:PLAIN_WORDS),message,
        history:(history||[]).slice(-8),
        images:(frames||[]).map(f=>({mime_type:f.mime,data:f.b64})),
        ...samplingOptions(options.temperature,frames?.length ? 0.25 : 0.2),max_output_tokens:options.responseSchema?8192:(frames?.length?6144:4096),
        ...(options.responseSchema?{response_schema:options.responseSchema}: {})})
    });
    return readGeminiResponse(res,onChunk,{structured:!!options.responseSchema});
  }
};

function samplingOptions(temperature,fallback=0.2,model=MODEL){
  return /^gemini-3\.6(?:-|$)/i.test(model)?{}:{temperature:temperature??fallback};
}
function structuredReply(text){
  const outer=String(text).trim().match(/^```(?:json)?[ \t]*\r?\n?([\s\S]*?)\r?\n?```$/i);
  return outer?outer[1]:text;
}
async function readGeminiResponse(res,onChunk,options={}) {
  if(!res.ok) throw new Error(classifyApiError(res.status,await res.text()));
  const reader=res.body.getReader(), decoder=new TextDecoder();
  let buffer='', full='';
  const output=text=>options.structured?structuredReply(text):cleanReply(text);
  const consume=line=>{
    if(!line.startsWith('data:')) return;
    const payload=line.slice(5).trim();
    if(!payload || payload==='[DONE]') return;
    let event;
    try { event=JSON.parse(payload); } catch { throw new Error('Invalid streaming response.'); }
    if(event.error) throw new Error(event.error.message || 'The AI request failed.');
    const parts=event.candidates?.[0]?.content?.parts||[];
    const text=parts.filter(p=>!p.thought).map(p=>p.text||'').join('');
    if(text){full+=text;onChunk(output(full));}
  };
  try {
    while(true){
      const {done,value}=await reader.read();
      if(done) break;
      buffer+=decoder.decode(value,{stream:true});
      const lines=buffer.split('\n');buffer=lines.pop();lines.forEach(consume);
    }
    buffer+=decoder.decode();if(buffer.trim()) consume(buffer);
    if(!full.trim()) throw new Error('The AI returned no answer. Please retry.');
    return output(full);
  } finally { await reader.cancel().catch(()=>{}); }
}

function aiAvailable(){ return !RetailAPI.recordedDemo && !freeQuotaStopped() && (RetailAPI.enabled ? RetailAPI.ready : !!getKey()); }

function setDataStatus(message,error=false){
  let el=document.getElementById('data-status');
  if(!el){
    el=document.createElement('div');el.id='data-status';el.setAttribute('role','status');
    el.style.cssText='padding:9px 20px;background:#edf5f3;border-bottom:1px solid #ccdcd7;font-size:12px;position:relative;z-index:20';
    document.querySelector('.topbar')?.after(el) || document.body.prepend(el);
  }
  el.textContent=message;el.style.color=error?'#b91c1c':'#22534a';
}

async function initializeData(){
  if(!RetailAPI.enabled){
    setDataStatus((RetailAPI.recordedDemo?'Recorded walkthrough - no AI calls. Synthetic scenario dated ':window.RETAILIQ_RUNTIME?.free_only?'Free static workspace - optional unbilled AI Studio key. Synthetic data dated ':'Synthetic demo data - ')+D.asOfDate);
    if(RetailAPI.recordedDemo){
      const link=document.createElement('a');link.id='exit-recorded-demo';const live=new URL(location.href);live.searchParams.delete('demo');link.href=live.href;link.textContent=' Open live workspace';link.style.marginLeft='10px';document.getElementById('data-status').append(link);
    }
    return;
  }
  setDataStatus('Loading store data...');
  const data=await RetailAPI.json('/api/bootstrap');
  if(!Array.isArray(data.products)||!data.products.length||!Array.isArray(data.forecast)||!data.forecast.length)
    throw new Error('Store inventory or forecast is unavailable.');
  Object.assign(D,data);
  activeProfile=D.shopperProfiles[0];activeVisit=D.visits[0];
  RetailAPI.ready=true;
  setDataStatus('Store data: BigQuery'+(D.dataIsSynthetic?' (synthetic demo dataset)':'')+' - '+D.asOfDate+' - Field targets, visits, profiles and team figures use demo reference data');
}

function eventStatus(text,error=false){
  let el=document.getElementById('event-status');
  if(!el){el=document.createElement('div');el.id='event-status';el.setAttribute('role','status');
    el.style.cssText='position:fixed;bottom:12px;right:18px;padding:10px 14px;background:white;border:1px solid #ccc;border-radius:8px;z-index:100;font-size:13px;max-width:420px';document.body.append(el);}
  el.textContent=text;el.style.color=error?'#b91c1c':'#0c6b5f';
}

async function logVisitEvent(eventType,summary,metadata={},context=null){
  if(context?.current && !context.current())return false;
  const event={visit_id:context?.visitId||activeVisit.id,
    store_id:context?.storeId||activeVisit.storeId,rep_id:D.rep.employeeId,
    event_type:eventType,summary,metadata:JSON.parse(JSON.stringify(metadata)),
    ...(Number.isFinite(context?.score)?{score:context.score}:{})};
  try {
    if(RetailAPI.enabled){
      const result=await RetailAPI.json('/api/visits/log',{method:'POST',body:JSON.stringify(event)});
      if(result.status!=='logged')throw new Error('The server did not save this event.');
      if(!context?.current||context.current())eventStatus('Visit event saved to the server.');
    } else {
      const events=readDemoEvents();events.unshift({...event,created_at:new Date().toISOString()});
      localStorage.setItem('retailiq_demo_events',JSON.stringify(events.slice(0,100)));
      eventStatus('Demo event saved in this browser only.');
    }
    await refreshVisitEvents();return true;
  } catch(error){if(!context?.current||context.current())eventStatus('Not saved: '+error.message,true);return false;}
}
function readDemoEvents(){
  try {const events=JSON.parse(localStorage.getItem('retailiq_demo_events')||'[]');return Array.isArray(events)?events:[];}
  catch{return [];}
}
let eventsRequest=0;
async function refreshVisitEvents(){
  const box=document.getElementById('recent-events');if(!box)return;
  closeEvidenceViewer();
  const request=++eventsRequest;
  try {
    const events=RetailAPI.enabled
      ? (await RetailAPI.json('/api/visits/log?store_id='+encodeURIComponent(D.store.storeId))).events
      : readDemoEvents();
    if(request!==eventsRequest)return;
    box.replaceChildren();
    const status=document.createElement('p');status.style.color='var(--text-3)';
    status.textContent=RetailAPI.enabled?'Saved visit events from server storage. Refreshes while this manager view is open.':'Demo events stored only in this browser. Other tabs on this device update automatically.';box.append(status);
    if(!Array.isArray(events)||!events.length){const empty=document.createElement('div');empty.textContent='No saved visit events yet. Try the guided shelf workflow and save its audit.';box.append(empty);return;}
    events.slice(0,20).forEach(event=>{
      const row=document.createElement('div');row.className='event-row';row.style.cssText='padding:12px 0;border-bottom:1px solid #eee';
      const title=document.createElement('strong');title.textContent=event.event_type+' - '+event.visit_id+' - '+event.store_id;
      const date=document.createElement('small');const parsed=new Date(event.created_at);
      date.textContent=isNaN(parsed)?'Saved event':parsed.toLocaleString('en-IN',{timeZone:'Asia/Kolkata'});
      const detail=document.createElement('div');detail.textContent=event.summary;row.append(title,date,detail);
      const audit=event.metadata?.audit;
      if(audit&&Array.isArray(audit.rules)){
        const results=document.createElement('details'),summary=document.createElement('summary');
        summary.textContent='View '+audit.rules.length+' rule verdicts and follow-up';results.append(summary);
        const evidence=document.createElement('p');evidence.textContent='Evidence: '+(audit.source==='recorded-example'?'recorded example, not live inference':audit.frames+' model-inspected frames')+'. Photo retained: '+(event.metadata?.evidence?.retained?'yes':'no')+'.';results.append(evidence);
        const pre=document.createElement('pre');pre.textContent=audit.rules.map(r=>(r.rule||r.code)+': '+r.verdict+' - '+r.note).join('\n');results.append(pre);
        const next=document.createElement('p');next.textContent=event.metadata.action||'';results.append(next);
        if(Array.isArray(event.metadata.next_actions)){
          const actions=document.createElement('ul');event.metadata.next_actions.forEach(action=>{const li=document.createElement('li');li.textContent=action.product+' - '+action.action+' Owner: '+action.owner+'. Status: '+action.status+'.';actions.append(li);});results.append(actions);
        }
        row.append(results);
      }
      const retained=event.metadata?.evidence;
      if(retained?.retained && typeof retained.gcs_uri==='string' && retained.gcs_uri.startsWith('gs://')){
        const photo=document.createElement('button');photo.type='button';photo.className='btn view-evidence-photo';photo.style.marginTop='10px';photo.textContent='View retained photo';
        photo.disabled=!RetailAPI.enabled;photo.addEventListener('click',()=>showEvidencePhoto(retained));row.append(photo);
      }
      box.append(row);
    });
  } catch(error){if(request===eventsRequest)box.textContent='Visit events unavailable: '+error.message;}
}
async function saveOrder(){
  const context=beginOperation('order-save');
  const lines=Object.entries(orderQty).filter(([,q])=>q>0).map(([id,quantity])=>({product_id:id,quantity,unit_trade_price:tradePrice(D.products.find(p=>p.id===id))}));
  if(!lines.length){eventStatus('Add an order quantity first.',true);return;}
  const value=lines.reduce((sum,l)=>sum+l.quantity*l.unit_trade_price,0);
  await logVisitEvent('order','Proposed order: '+lines.length+' products, '+inr(value)+' at trade price. Buyer approval pending.',{lines,value,status:'proposed'},context);
}

let evidenceBlobURL=null,evidenceAbort=null,evidenceViewerEpoch=0;
function closeEvidenceViewer(){
  evidenceViewerEpoch++;evidenceAbort?.abort();evidenceAbort=null;
  const viewer=document.getElementById('evidence-viewer');if(viewer?.open)viewer.close();
  document.getElementById('evidence-image')?.removeAttribute('src');
  if(evidenceBlobURL){URL.revokeObjectURL(evidenceBlobURL);evidenceBlobURL=null;}
}
function evidenceViewer(){
  let viewer=document.getElementById('evidence-viewer');if(viewer)return viewer;
  viewer=document.createElement('dialog');viewer.id='evidence-viewer';viewer.setAttribute('aria-labelledby','evidence-title');
  viewer.style.cssText='width:min(94vw,960px);max-height:92vh;border:1px solid #bdd3cc;border-radius:14px;padding:20px;color:#143d34;box-shadow:0 24px 80px #0005';
  const title=document.createElement('h2');title.id='evidence-title';title.textContent='Retained shelf evidence';title.style.cssText='font-size:19px;margin:0 0 12px';
  const status=document.createElement('p');status.id='evidence-photo-status';status.setAttribute('role','status');status.style.fontSize='13px';
  const image=document.createElement('img');image.id='evidence-image';image.alt='Retained shelf photograph attached to this visit event';image.style.cssText='display:none;width:100%;max-height:70vh;object-fit:contain;border-radius:8px;background:#f3f7f5';
  const close=document.createElement('button');close.type='button';close.id='close-evidence';close.className='btn';close.textContent='Close photo';close.style.marginTop='14px';close.addEventListener('click',closeEvidenceViewer);
  viewer.append(title,status,image,close);viewer.addEventListener('cancel',event=>{event.preventDefault();closeEvidenceViewer();});
  document.body.append(viewer);return viewer;
}
async function showEvidencePhoto(evidence){
  closeEvidenceViewer();
  if(!RetailAPI.enabled||!evidence?.retained||typeof evidence.gcs_uri!=='string')return;
  const viewer=evidenceViewer(),status=document.getElementById('evidence-photo-status'),image=document.getElementById('evidence-image');
  image.style.display='none';status.textContent='Loading the private shelf photo...';viewer.showModal();
  const request=evidenceViewerEpoch;evidenceAbort=new AbortController();
  try {
    const response=await fetch('/api/evidence/image?gcs_uri='+encodeURIComponent(evidence.gcs_uri),{headers:RetailAPI.headers(),cache:'no-store',signal:evidenceAbort.signal});
    if(!response.ok)throw new Error(response.status===404?'This retained photo is unavailable or has expired.':'The photo could not load ('+response.status+'). Check workspace access and retry.');
    const mime=(response.headers.get('content-type')||'').split(';')[0].trim().toLowerCase();
    if(!['image/jpeg','image/png','image/webp','image/gif'].includes(mime))throw new Error('The server did not return a supported shelf image.');
    const bytes=await response.blob();
    if(bytes.size>6*1024*1024)throw new Error('The retained photo exceeds the supported size.');
    if(request!==evidenceViewerEpoch||!viewer.open)return;
    evidenceBlobURL=URL.createObjectURL(bytes);image.src=evidenceBlobURL;image.style.display='block';
    status.textContent='Private photo retrieved for this saved visit.'+(evidence.expires_after_days?' Retention: '+evidence.expires_after_days+' days.':'');
  } catch(error){if(request===evidenceViewerEpoch&&error.name!=='AbortError')status.textContent=error.message;}
  finally{if(request===evidenceViewerEpoch)evidenceAbort=null;}
}
window.addEventListener('pagehide',closeEvidenceViewer);

window.addEventListener('storage',event=>{if(event.key==='retailiq_demo_events')refreshVisitEvents();});
const eventRefreshTimer=setInterval(()=>{
  if(RetailAPI.enabled&&!document.hidden&&!document.getElementById('evidence-viewer')?.open&&document.getElementById('surface-biz')?.classList.contains('on'))refreshVisitEvents();
},20000);
window.addEventListener('pagehide',()=>clearInterval(eventRefreshTimer));
