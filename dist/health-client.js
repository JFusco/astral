// Cached assessments only: browser polling never triggers provider/model probes.
export function connectHealth({onState,onDisconnect}) {
  let pending=false;
  async function refresh(){
    if(pending)return;
    pending=true;
    try{
      const response=await fetch('http://127.0.0.1:8769/api/health/state',{cache:'no-store',credentials:'omit',signal:AbortSignal.timeout(4000)});
      if(!response.ok)throw new Error('Health service unavailable');
      const state=await response.json();
      const age=Date.now()-Date.parse(state.as_of);
      if(!Array.isArray(state.nodes)||!Number.isFinite(age)||age< -5000||age>15000)throw new Error('Invalid/stale health response');
      onState(state);
    }catch{onDisconnect();}
    finally{pending=false;}
  }
  refresh();
  const timer=setInterval(refresh,5000);
  const visible=()=>{if(!document.hidden)refresh();};
  document.addEventListener('visibilitychange',visible);
  return ()=>{clearInterval(timer);document.removeEventListener('visibilitychange',visible);};
}
