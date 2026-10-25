// The browser never receives broker credentials. Once connected, no simulation fallback.
export function connectBackend({onState,onFill,onDisconnect,onPreview}) {
  let established=false,lastMessage=0,source=null;
  const seen=new Set();
  async function request(path,body){
    const response=await fetch(path,{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json','X-Astral-Intent':'paper-only'}:{},body:body?JSON.stringify(body):undefined,signal:AbortSignal.timeout(15000)});
    const result=await response.json();if(!response.ok)throw new Error(result.detail||`Service returned ${response.status}`);return result;
  }
  function accept(state,initial=false){lastMessage=Date.now();if(initial)state.fills.forEach(f=>seen.add(f.id));onState(state);}
  (async()=>{
    try{
      const response=await fetch('/api/state',{signal:AbortSignal.timeout(3000)});
      if(!response.ok){onPreview();return;}
      const state=await response.json();if(state.service_version!=='0.2'){onPreview();return;}
      established=true;accept(state,true);
      source=new EventSource(`/api/events?after=${state.sequence}`);
      source.addEventListener('state',e=>{try{accept(JSON.parse(e.data));}catch{onDisconnect();}});
      source.addEventListener('ledger',e=>{lastMessage=Date.now();try{const event=JSON.parse(e.data);if(event.type==='fill'&&!seen.has(event.payload.id)){seen.add(event.payload.id);onFill(event.payload);} }catch{onDisconnect();}});
      source.onerror=()=>onDisconnect();
      setInterval(()=>{if(Date.now()-lastMessage>8000)onDisconnect();},2000);
    }catch{if(established)onDisconnect();else onPreview();}
  })();
  return {async order(intent){const order=await request('/api/orders',intent);accept(await request('/api/state'));return order;},
    async halt(halted){await request('/api/halt',{halted});accept(await request('/api/state'));},
    async cancel(clientId){const order=await request(`/api/orders/${encodeURIComponent(clientId)}/cancel`,{});accept(await request('/api/state'));return order;},
    async reconcile(){accept(await request('/api/reconcile',{}));},
    async research(){return await request('/api/research/run',{});},close(){source?.close();}};
}
