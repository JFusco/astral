import {createHealthGalaxy} from './health-galaxy.js';
import {connectHealth} from './health-client.js';
import {ui,pageHeader,statusClass,statusDot,topicClass,finishBoot} from './ui.js';
import {mountAppShell} from './app-shell.js';
mountAppShell('health');
document.querySelector('.intro').outerHTML=pageHeader({title:'App health',eyebrow:'APPLICATION / HEALTH',subtitle:'Live checks for the application, data, workers and connected services.',action:'<div class="text-right text-xxs tracking-widest text-cyan">LIVE STATUS<span class="mt-2 block text-caption tracking-normal text-muted">Assessments every 10 seconds</span></div>'});
document.querySelector('.pulse-card>span').className=ui.label;
const theme=getComputedStyle(document.documentElement);
const token=name=>theme.getPropertyValue('--color-'+name).trim();
const $=s=>document.querySelector(s),esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const colors=Object.fromEntries(Object.keys(statusClass).map(name=>[name,token('status-'+name)]));
const canvas=$('#health-universe'),pulse=$('#pulse'),pc=pulse.getContext('2d');
let state=null,connected=false,received=0,lastSequence=null,lastPulse=-10000,selected='application',issuesOnly=false,topic='all';
const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
const topics={
  core:{name:'Application',color:token('topic-core'),kind:'star',description:'Application, collector and health storage'},
  execution:{name:'Broker & execution',color:token('topic-execution'),kind:'ring',description:'Paper broker connection and readback'},
  market:{name:'Market data',color:token('topic-market'),kind:'planet',description:'Crypto and ETF quote freshness'},
  workers:{name:'Engines & workers',color:token('topic-workers'),kind:'ring',description:'Research, reconciliation and scheduled engines'},
  sources:{name:'Public intelligence',color:token('topic-sources'),kind:'star',description:'News, calendars and protocol sources'},
  providers:{name:'Service providers',color:token('topic-providers'),kind:'ring',description:'Published service status reports'},
  models:{name:'Models',color:token('topic-models'),kind:'star',description:'Recorded model state without paid probes'},
  local:{name:'Local runtime',color:token('topic-local'),kind:'planet',description:'Docker, LEAN, account setup and local capacity'}
};
const groups=Object.keys(topics);
const expandedGroups=new Set(['core']);
function scopeNodes(){return nodes().filter(n=>topic==='all'||n.group===topic);}
function attention(n){return ['degraded','down','unknown'].includes(n.status);}
function live(){return connected&&state?.heartbeat_live&&Date.now()-received<15000&&Date.now()-Date.parse(state.checked_at)<=30000;}
function nodes(){return (state?.nodes||[]).map(n=>live()?n:{...n,status:'unknown',detail:'Health engine unavailable or heartbeat missed. Retained observation only.'});}
function inspect(){const n=nodes().find(n=>n.id===selected);$('#inspector').innerHTML=n?`<span class="inline-flex rounded border border-current px-2 py-1 text-xxs font-semibold tracking-wide uppercase ${statusClass[n.status]||statusClass.unknown}">${esc(n.status)}</span><h3 class="font-display text-xl text-ink">${esc(n.name)}</h3><p>${esc(n.detail)}</p><p>Group: ${esc(topics[n.group]?.name||n.group)}<br>Observed: ${esc(n.checked_at||'No observation')}<br>${n.required?'Used by the application':'Optional / not currently active'}</p>`:state?'<p>No dependencies match this attention filter.</p>':'<p>Waiting for the health engine. No healthy state is assumed.</p>';}

function render(){
  const current=scopeNodes(),counts={};current.forEach(n=>counts[n.status]=(counts[n.status]||0)+1);
  $('#healthy').textContent=state?counts.healthy||0:'—';$('#attention').textContent=state?(counts.degraded||0)+(counts.down||0)+(counts.unknown||0):'—';$('#inactive').textContent=state?counts.inactive||0:'—';
  $('#connection').textContent=live()?'● Health engine live':'● Health engine unavailable';$('#connection').classList.toggle('live',!!live());
  $('#last-check').textContent=state?`${live()?'Completed':'Last recorded'} ${new Date(state.checked_at).toLocaleTimeString()} · 10s cadence`:'Waiting for a real check';
  $('#inventory').textContent=current.length?`${current.length} dependencies · ${groups.filter(g=>current.some(n=>n.group===g)).length} ${topic==='all'?'topics':'topic'} · ${counts.checking||0} checking`:'Waiting for health data';
  $('.universe-panel h2').textContent=topic==='all'?'Service map':topics[topic].name;
  $('#cycle').textContent=live()?`CHECK ${String(state.sequence).padStart(4,'0')} / ${state.duration_ms} MS`:'HEARTBEAT NOT CURRENT';
  $('#updated').textContent=state?`Last checked ${state.checked_at}`:'Waiting for health data';
  const visible=current.filter(n=>!issuesOnly||attention(n));if(!visible.some(n=>n.id===selected))selected=visible[0]?.id||null;$('#node-count').textContent=visible.length;
  const list=$('#node-list'),focused=document.activeElement?.dataset?.node,focusedGroup=document.activeElement?.closest('details')?.dataset?.group;
  list.innerHTML=groups.map(g=>{
    const members=visible.filter(n=>n.group===g);if(!members.length)return '';
    const cfg=topics[g],bad=members.filter(attention).length;
    return `<details class="system-group my-2 overflow-hidden rounded-lg border border-line bg-app" data-group="${g}" ${expandedGroups.has(g)?'open':''}><summary class="flex cursor-pointer list-none items-center gap-2 px-3 py-3 text-caption ${topicClass[g]} marker:hidden [&::-webkit-details-marker]:hidden"><i class="size-1.5 shrink-0 rounded-full bg-current"></i><span>${cfg.name}<small class="mt-1 block text-xxs text-muted">${members.length} ${members.length===1?'system':'systems'}${bad?` · ${bad} attention`:''}</small></span><b class="ml-auto text-xxs font-normal text-muted">${members.length}</b></summary><div class="group-members border-t border-line p-1">${members.map(n=>`<button data-node="${esc(n.id)}" class="flex w-full cursor-pointer items-center gap-2 rounded-md border border-transparent px-2 py-3 text-left text-caption text-ink hover:bg-surface-raised [&.selected]:border-line [&.selected]:bg-surface-raised ${selected===n.id?'selected':''}"><i class="size-1.5 shrink-0 rounded-full ${statusDot[n.status]||statusDot.unknown}"></i><span class="min-w-0 flex-1">${esc(n.name)}</span><small class="node-status shrink-0 text-xxs font-semibold tracking-wide uppercase ${statusClass[n.status]||statusClass.unknown}">${esc(n.status)}</small></button>`).join('')}</div></details>`;
  }).join('')||'<p class="p-3 text-caption text-muted">No matching systems in this view.</p>';
  list.querySelectorAll('details').forEach(d=>d.addEventListener('toggle',()=>{if(d.open)expandedGroups.add(d.dataset.group);else expandedGroups.delete(d.dataset.group);}));
  list.querySelectorAll('button[data-node]').forEach(b=>b.onclick=()=>{selected=b.dataset.node;inspect();list.querySelectorAll('button[data-node]').forEach(x=>x.classList.toggle('selected',x===b));});
  if(focused){const b=[...list.querySelectorAll('button')].find(b=>b.dataset.node===focused);b?.focus({preventScroll:true});}else if(focusedGroup){[...list.querySelectorAll('details')].find(d=>d.dataset.group===focusedGroup)?.querySelector('summary')?.focus({preventScroll:true});}
  inspect();
  $('#changes').innerHTML=(state?.changes||[]).filter(r=>topic==='all'||current.some(n=>n.id===r.payload.id)).slice(0,4).map(r=>`<div class="flex justify-between gap-3 py-2 text-caption text-muted"><strong class="font-normal text-ink">${esc(r.payload.name)}</strong><span>${esc(r.payload.previous)} → ${esc(r.payload.status)} · ${esc(new Date(r.at).toLocaleTimeString())}</span></div>`).join('')||'No status changes recorded.';
}
connectHealth({onState:s=>{state=s;connected=true;received=Date.now();if(s.sequence!==lastSequence&&s.heartbeat_live){lastSequence=s.sequence;lastPulse=performance.now();}render();finishBoot();},onDisconnect:()=>{connected=false;render();finishBoot();}});
setInterval(()=>{if(state&&!live())render();},1000);
$('#all-filter').onclick=()=>{issuesOnly=false;$('#all-filter').setAttribute('aria-pressed','true');$('#issue-filter').setAttribute('aria-pressed','false');render();};
$('#issue-filter').onclick=()=>{issuesOnly=true;$('#all-filter').setAttribute('aria-pressed','false');$('#issue-filter').setAttribute('aria-pressed','true');render();};
let galaxy=null;
try{
  galaxy=createHealthGalaxy(canvas,{topics,colors,getNodes:nodes,getView:()=>({topic,issuesOnly,selected}),isLive:live,getPulse:()=>lastPulse,reduced,onSelect:id=>{selected=id;const n=nodes().find(n=>n.id===id);if(n)expandedGroups.add(n.group);render();}});
}catch(error){const note=document.createElement('p');note.className='renderer-note pointer-events-none absolute bottom-10 left-5 text-caption text-muted';note.textContent='3D view unavailable · use Systems by Type';canvas.parentElement.append(note);console.warn('Health 3D renderer unavailable',error.stack||error.message);}
$('#reset-view').onclick=()=>galaxy?.reset();
function size(c,context){const r=c.getBoundingClientRect(),d=Math.min(devicePixelRatio||1,2);if(c.width!==Math.round(r.width*d)||c.height!==Math.round(r.height*d)){c.width=Math.round(r.width*d);c.height=Math.round(r.height*d);}context.setTransform(d,0,0,d,0,0);return [r.width,r.height];}
function frame(t){
  const [pw,ph]=size(pulse,pc);pc.clearRect(0,0,pw,ph);pc.strokeStyle=live()?colors.checking:colors.unknown;pc.lineWidth=1.5;pc.beginPath();
  const elapsed=t-lastPulse;
  for(let x=0;x<pw;x++){const center=live()&&!reduced&&elapsed<2500?elapsed/2200:2,d=x/pw-center;let y=ph*.55;if(Math.abs(d)<.09)y+=Math.exp(-d*d/.0006)*Math.sin(d*120)*ph*.42;x?pc.lineTo(x,y):pc.moveTo(x,y);}pc.stroke();
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);
