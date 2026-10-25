import {createPortfolio,totals,fill} from './core.js';
import {connectBackend} from './backend.js';

const $=s=>document.querySelector(s);const $$=s=>[...document.querySelectorAll(s)];
const money=(v,d=2)=>new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',minimumFractionDigits:d,maximumFractionDigits:d}).format(v);
const signed=(v,d=2)=>(v>=0?'+':'−')+money(Math.abs(v),d);
const quantity=v=>new Intl.NumberFormat('en-US',{maximumFractionDigits:6}).format(v);
const book=createPortfolio();let selected='BTC',paused=false,events=0,newsFilter='all',period='1D';
let backendState=null,backendConnecting=true,backendAvailable=false,backend=null;
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const systemReduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
let motion=localStorage.getItem('astral-motion')||(systemReduced?'reduced':'cinematic');document.body.dataset.motion=motion;
const activity=[];const started=Date.now();let lastTick=Date.now(),lastTrade=Date.now(),lastNews=Date.now();
let toastTimer,eventTimer;const effects=[];
const newsItems=[
  {category:'markets',label:'MACRO / SAMPLE',title:'Inflation watch: the next release enters the risk window',tag:'MACRO',body:'Illustrative signal only. A connected version would track the official release calendar, prior values, revisions, and the exact time new information became available. This is not a report about a current event.'},
  {category:'crypto',label:'CRYPTO / SAMPLE',title:'Network activity meets price momentum in the crypto orbit',tag:'BTC · ETH',body:'Illustrative signal only. A connected version would link token identifiers, official project announcements, market context, and venue quotes. No current network measurement or investment conclusion is claimed here.'},
  {category:'markets',label:'ETF / SAMPLE',title:'A fresh holdings snapshot updates portfolio overlap',tag:'SPY · QQQ',body:'Illustrative signal only. The eventual ingestion layer will compare issuer holdings with fund exposure and preserve both the as-of date and the arrival timestamp. No issuer feed is connected in this prototype.'},
  {category:'crypto',label:'SECURITY / SAMPLE',title:'Project announcements enter the source verification queue',tag:'SOL',body:'Illustrative signal only. Security notices would be sourced from verified project and exchange channels, deduplicated, attributed, and reviewed for relevance. A source statement never grants order permissions.'}
];

function notify(text){$('#toast').textContent=text;$('#toast').classList.add('visible');clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('#toast').classList.remove('visible'),3500);}
function renderPortfolio(){
  const focusedAsset=document.activeElement?.classList.contains('position-row')?document.activeElement.dataset.asset:null;
  const t=totals(book);$('#equity').textContent=money(t.equity);$('#equity-change').textContent=`${signed(t.net)} (${(t.net/book.openingEquity*100).toFixed(2)}%)`;
  $('#net-profit').textContent=signed(t.net);$('#net-profit').classList.toggle('negative',t.net<0);$('#realized').textContent=`${money(book.realized,0)} realized`;$('#unrealized').textContent=`${money(t.unrealized,0)} open`;
  $('#deployed').textContent=money(t.deployed);$('#cash').textContent=`${money(book.cash,0)} available`;$('#exposure').textContent=`${(t.exposure*100).toFixed(1)}% exposure`;$('#capital-bar').style.width=`${t.exposure*100}%`;
  const open=book.assets.filter(a=>a.quantity>1e-9);$('#positions-count').textContent=open.length;
  $('#positions').innerHTML=open.map(a=>{const value=backendState?a.marketValue:a.price*a.quantity;const pnl=backendState?a.unrealized:value-a.basis;return `<button class="position-row ${a.symbol===selected?'chosen':''}" data-asset="${a.symbol}" aria-label="Select ${a.name}, ${money(value)} value"><span class="position-asset"><span class="coin-icon">${a.icon}</span><span><strong>${a.symbol}</strong><small>${quantity(a.quantity)} ${a.type==='crypto'?a.symbol:'shares'}</small></span></span><span class="position-value"><strong>${money(value)}</strong><small class="${pnl<0?'negative':''}">${signed(pnl)} (${(a.basis?pnl/a.basis*100:0).toFixed(2)}%)</small></span></button>`;}).join('');
  $$('#positions [data-asset]').forEach(el=>el.onclick=()=>selectAsset(el.dataset.asset));
  if(focusedAsset)$(`#positions [data-asset="${focusedAsset}"]`)?.focus({preventScroll:true});
  if(!open.length)$('#positions').innerHTML='<div class="empty-state">No open positions.<br>Unallocated cash is available capital.</div>';
  const a=book.assets.find(a=>a.symbol===selected);$('#selected-name').textContent=a.name;$('#selected-ticker').textContent=a.type==='crypto'?`${a.symbol} / USD`:`${a.symbol} / ETF`;$('#selected-icon').textContent=a.icon;$('#selected-price').textContent=money(a.price);$('#selected-change').textContent=`${a.change>=0?'+':''}${a.change.toFixed(2)}% · simulated`;$('#selected-change').classList.toggle('negative',a.change<0);
  $('#demo-buy').disabled=book.halted;$('#demo-sell').disabled=a.quantity<=0;
  $$('.orbit-label').forEach(el=>el.classList.toggle('selected',el.dataset.symbol===selected));
  const riskBlocked=book.halted||t.exposure>.5;$('#risk-state').textContent=book.halted?'ENTRIES HALTED':riskBlocked?'REDUCE EXPOSURE':'WITHIN LIMITS';$('#risk-state').style.color=riskBlocked?'#e5b489':'';
  drawChart();
  if(backendState)renderBackendLabels();
}
function selectAsset(symbol){selected=symbol;renderPortfolio();}
function trade(side,automatic=false){
  if(backendState){if(!automatic)openOrderForm(side);return;}
  const result=fill(book,selected,side,selected==='BTC'?650:500);
  if(!result.ok){if(!automatic)notify(result.reason);return;}
  lastTrade=Date.now();events++;activity.unshift(result);activity.splice(12);renderActivity();renderPortfolio();
  effects.push({symbol:selected,side,time:performance.now(),seed:Math.random()*100});
  $('#scene-event').className=`scene-event ${side}`;$('#scene-event span').textContent=`${side==='buy'?'NEBULA':'SUPERNOVA'} / ${selected} ${side.toUpperCase()} FILLED / SIMULATION`;
  clearTimeout(eventTimer);eventTimer=setTimeout(()=>{$('#scene-event').className='scene-event';$('#scene-event span').textContent='Every signal has a story.';},6500);
  if(!automatic)notify(`Simulated ${side}: ${quantity(result.quantity)} ${selected} at ${money(result.price)}. No broker order sent.`);
}
function renderActivity(){
  if(backendState){renderBackendActivity();return;}
  $('#activity').innerHTML=activity.slice(0,5).map(a=>`<div class="activity-row ${a.side}"><span class="trade-indicator">${a.side==='buy'?'↗':'↙'}</span><div class="activity-copy"><strong>${a.side==='buy'?'Bought':'Sold'} ${quantity(a.quantity)} ${a.symbol} <span>@ ${money(a.price)}</span></strong><small>${a.id} · SIMULATED FILL · fee ${money(a.fee)}</small></div><span class="activity-time">${new Date(a.time).toISOString().slice(11,19)}</span></div>`).join('');
  if(!activity.length)$('#activity').innerHTML='<div class="activity-row"><span class="trade-indicator">◎</span><div class="activity-copy"><strong>Paper lab initialized</strong><small>DEMO SNAPSHOT · NO BROKER CONNECTED</small></div></div>';
}
function renderNews(){
  if(backendState){renderBackendNews();return;}
  const items=newsItems.map((n,i)=>({...n,index:i})).filter(n=>newsFilter==='all'||n.category===newsFilter);
  $('#news').innerHTML=items.slice(0,3).map(n=>`<button class="news-row" data-story="${n.index}"><span class="news-meta"><i class="${n.category==='crypto'?'crypto-source':''}"></i>${n.label}<span>· EXAMPLE</span></span><div class="news-title">${n.title}</div><span class="news-tag">${n.tag}</span></button>`).join('');
  $$('[data-story]').forEach(el=>el.onclick=()=>{const n=newsItems[Number(el.dataset.story)];openDialog('Illustrative intelligence','EXAMPLE / NOT CURRENT NEWS',`<span class="article-label">SIMULATED CONTENT</span><h3>${n.title}</h3><p class="article-body">${n.body}</p><div class="dialog-note">Source connection: none. The production design retains source URL, publication time, first-seen time, revisions, and feature versions for every item.</div>`);});
}
function drawChart(){
  if(backendState){drawRecordedChart();return;}
  const t=totals(book);const range=period==='1H'?.013:period==='1D'?.048:.085;const base=t.equity/(1+range);
  const values=Array.from({length:65},(_,i)=>{const x=i/64;const noise=(Math.sin(i*1.71)*.7+Math.sin(i*.57)*1.4)*Math.sin(Math.PI*x);return base+(t.equity-base)*(x+noise*.038);});
  const min=Math.min(...values)-(t.equity-base)*.12,max=Math.max(...values)+(t.equity-base)*.15;
  const points=values.map((v,i)=>[i/64*540,112-(v-min)/(max-min)*106]);const d=points.map(([x,y],i)=>`${i?'L':'M'}${x.toFixed(2)},${y.toFixed(2)}`).join(' ');
  $('#chart-line').setAttribute('d',d);$('#chart-area').setAttribute('d',`${d} L540,124 L0,124 Z`);$('#chart-point').setAttribute('cx',540);$('#chart-point').setAttribute('cy',points.at(-1)[1]);$('#trajectory-value').textContent=`+${(range*100).toFixed(2)}%`;$('#chart-start').textContent=period==='1H'?'−60 MIN':period==='1D'?'00:00':'−7 DAYS';$('#chart-middle').textContent=period==='1H'?'−30 MIN':period==='1D'?'12:00':'−3 DAYS';
}
function openDialog(title,eyebrow,content){$('#dialog-title').textContent=title;$('#dialog-eyebrow').textContent=eyebrow;$('#dialog-content').innerHTML=content;$('#detail-dialog').showModal();}
function openView(view){
  if(view==='overview'){$('#detail-dialog').close();window.scrollTo({top:0,behavior:motion==='reduced'?'instant':'smooth'});return;}
  if(backendState){openBackendView(view);return;}
  if(view==='strategies')openDialog('Two horizons. One portfolio.','STRATEGY ALLOCATIONS / DEMO',`<p class="dialog-copy">A steady core and an opportunistic sleeve share one portfolio risk controller. These illustrative budgets are not active trading strategies.</p><div class="telemetry-row"><div>Core / swing<small>Daily signals · multi-day holding period</small></div><span>70% of strategy capital</span></div><div class="allocation-track"><span></span></div><div class="telemetry-row"><div>Opportunity / intraday<small>Five-minute signals · bounded risk</small></div><span>30% of strategy capital</span></div><div class="telemetry-row"><div>Learning / challenger<small>Record → replay → shadow → review</small></div><span>No candidate deployed</span></div><div class="dialog-note">Prototype guardrails: no leverage; 50% maximum total exposure; 20% maximum per asset; available cash required; halt blocks buys and permits sells. Complete production risk, session, stale-data and reconciliation controls remain to be built. No backtest or profitability evidence exists yet.</div>`);
  if(view==='intelligence')openDialog('An evidence-aware universe.','INTELLIGENCE SOURCES',`<p class="dialog-copy">Live source adapters will feed a timestamped, deduplicated evidence store. Every headline currently shown is a sample, not current news.</p>${[['Broker quotes & orders','Alpaca paper adapter'],['Market & symbol news','Alpaca / Benzinga entitlement to verify'],['Financial statements','SEC filings & Company Facts'],['ETF exposure','Official issuer holdings'],['Crypto context','CoinGecko + official project notices'],['Macro calendar','Federal Reserve / BLS / Treasury']].map(([a,b])=>`<div class="telemetry-row"><div>${a}<small>${b}</small></div><span class="source-state">Not connected</span></div>`).join('')}<div class="dialog-note">First-seen time is distinct from publication time. Stale inputs get visible warnings. Licensed content, coverage and account quotas must be verified before connection.</div>`);
  if(view==='system'){
    const t=totals(book);openDialog('The system behind the signal.','SIMULATED SYSTEM TELEMETRY',`<p class="dialog-copy">The browser simulation is running. There are no backend workers, broker connections, model calls or actual API charges.</p>${[['Market observer','Synthetic quotes / 1.5-second tick'],['Strategy engine','Demonstration events only'],['Risk controller',book.halted?'New entries halted':`${(t.exposure*100).toFixed(1)}% deployed / 50% cap`],['Execution adapter','Browser simulator / no broker'],['Evidence recorder',`${events} transient demo events`],['Learning evaluator','Design only / no evaluation run']].map(([a,b])=>`<div class="telemetry-row"><div>${a}<small>${b}</small></div><span>● DEMO</span></div>`).join('')}<div class="dialog-note">Session uptime: ${Math.floor((Date.now()-started)/1000)}s · Last synthetic tick: ${new Date(lastTick).toISOString().slice(11,19)} UTC · Simulated crypto fees: ${money(book.fees)} · Actual model API spend: $0. Browser state resets on reload.</div>`);
  }
}
function openSettings(){
  openDialog('Tune the atmosphere.','DISPLAY / SIMULATION',`<p class="dialog-copy">Keep the universe cinematic or turn the motion down. Financial values remain readable in every mode.</p><label class="setting-label" for="motion-select">Universe motion</label><select class="setting-select" id="motion-select"><option value="cinematic">Cinematic — orbital motion & fill effects</option><option value="calm">Calm — slower orbit & softer effects</option><option value="reduced">Reduced — static universe, no bursts</option></select><div class="telemetry-row"><div>Data mode<small>Synthetic prices, fictional news & browser fills</small></div><span>PAPER LAB</span></div><div class="dialog-note">This prototype cannot trade real money. Display settings are stored locally. A production service will run independently of this browser, with 24/7 monitoring and restart recovery.</div>`);
  $('#motion-select').value=motion;$('#motion-select').onchange=e=>{motion=e.target.value;document.body.dataset.motion=motion;localStorage.setItem('astral-motion',motion);effects.length=0;};
  if(backendState){$('#dialog-content .dialog-note').textContent='The Python backend runs independently of this page. Display settings affect this browser only. Simulator mode remains synthetic; Alpaca mode requires paper credentials and explicit server order enablement.';$('#dialog-content .telemetry-row').innerHTML=`<div>Data mode<small>${esc(backendState.mode==='simulator'?'Persistent synthetic simulator':'Alpaca paper account')}</small></div><span>${backendAvailable?'SERVICE CONNECTED':'SERVICE STALE'}</span>`;}
}
$('#close-dialog').onclick=()=>$('#detail-dialog').close();$('#detail-dialog').addEventListener('click',e=>{if(e.target===$('#detail-dialog')){const r=e.target.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)e.target.close();}});
$$('[data-view]').forEach(el=>el.onclick=()=>openView(el.dataset.view));$('#health-card').onclick=()=>openView('system');$('#settings-button').onclick=openSettings;
$('#demo-buy').onclick=()=>trade('buy');$('#demo-sell').onclick=()=>trade('sell');
$('#pause-button').onclick=()=>{paused=!paused;$('#pause-button').textContent=paused?'▷':'Ⅱ';$('#pause-button').setAttribute('aria-label',paused?'Resume simulation':'Pause simulation');$('#pause-button').title=paused?'Resume motion':'Pause motion';if(backendState){notify(paused?'Universe motion paused. The backend continues recording and managing orders.':'Universe motion resumed.');return;}$('#stream-status').textContent=paused?'SIMULATION PAUSED':'SIMULATION STREAM';$('#health-label').textContent=paused?'Simulation paused':'All systems nominal';if(!paused){lastTrade=Date.now();lastNews=Date.now();}notify(paused?'Synthetic stream paused. Demo fill controls remain available.':'Simulation resumed. No external feeds connected.');};
$('#halt-button').onclick=async()=>{if(backendState){try{await backend.halt(!book.halted);notify(book.halted?'Entry halt saved to the server.':'Entries resumed within server risk controls.');}catch(e){notify(e.message);}return;}book.halted=!book.halted;$('#halt-button').classList.toggle('halted',book.halted);$('#halt-button').innerHTML=book.halted?'<span>◇</span> Resume entries':'<span>◈</span> Halt entries';renderPortfolio();notify(book.halted?'Demo entries halted. Position updates and demo sells remain available.':'Demo entries resumed within the simulated exposure limits.');};
$$('[data-period]').forEach(el=>el.onclick=()=>{period=el.dataset.period;$$('[data-period]').forEach(b=>b.classList.toggle('selected',b===el));drawChart();});
$$('[data-news]').forEach(el=>el.onclick=()=>{newsFilter=el.dataset.news;$$('[data-news]').forEach(b=>b.classList.toggle('selected',b===el));renderNews();});

// A perspective-projected 3D scene. It has no authority over trading/accounting.
const canvas=$('#universe'),ctx=canvas.getContext('2d');const stage=$('#universe-stage');let width=800,height=345,zoom=1,yaw=-.18,pitch=.48,dragging=false,lastPointer,manualYaw=0,manualPitch=0;
let sceneTime=0,lastFrame=performance.now();const TAU=Math.PI*2;
const randomSeed=(n)=>{const x=Math.sin(n*127.1+311.7)*43758.5453;return x-Math.floor(x);};
const stars=Array.from({length:260},(_,i)=>({x:randomSeed(i+1),y:randomSeed(i+400),r:.25+randomSeed(i+820)*.8,a:.12+randomSeed(i+980)*.6}));
const particles=Array.from({length:1150},(_,i)=>{const p=randomSeed(i+2000)*TAU,r=Math.pow(randomSeed(i+3300),.55)*240;return {x:Math.cos(p)*r,y:(randomSeed(i+4600)-.5)*45,z:Math.sin(p)*r,size:.2+randomSeed(i+6100)*.8,alpha:.10+randomSeed(i+7800)*.5};});
const labelEls=new Map(book.assets.map(a=>{const el=document.createElement('button');el.className=`orbit-label ${a.type} ${a.symbol===selected?'selected':''}`;el.dataset.symbol=a.symbol;el.setAttribute('aria-label',`Select ${a.name}`);el.innerHTML=`${a.symbol}<span>${a.type==='crypto'?'CRYPTO':'ETF'}</span>`;el.onclick=()=>selectAsset(a.symbol);$('#orbit-labels').append(el);return [a.symbol,el];}));
function resize(){const rect=stage.getBoundingClientRect();width=rect.width;height=rect.height;const dpr=Math.min(devicePixelRatio||1,2);canvas.width=width*dpr;canvas.height=height*dpr;ctx.setTransform(dpr,0,0,dpr,0,0);}
new ResizeObserver(resize).observe(stage);resize();
function project(x,y,z){const cy=Math.cos(yaw),sy=Math.sin(yaw),cp=Math.cos(pitch),sp=Math.sin(pitch);const rx=x*cy-z*sy,rz=x*sy+z*cy,ry=y*cp-rz*sp,zz=y*sp+rz*cp;const scale=(Math.min(width/690,height/330)*zoom)*720/(720+zz);return {x:width*.5+rx*scale,y:height*.47+ry*scale,z:zz,scale};}
function glow(x,y,r,color,alpha=1){if(r<=0)return;const g=ctx.createRadialGradient(x,y,0,x,y,r);g.addColorStop(0,color.replace('ALPHA',String(alpha)));g.addColorStop(.2,color.replace('ALPHA',String(alpha*.35)));g.addColorStop(1,color.replace('ALPHA','0'));ctx.fillStyle=g;ctx.fillRect(x-r,y-r,r*2,r*2);}
function pointFor(a){const angle=a.phase+sceneTime*.035*(a.type==='crypto'?1.1:.8);return project(Math.cos(angle)*a.radius,Math.sin(angle*2)*14,Math.sin(angle)*a.radius*.91);}
function renderScene(now){
  const dt=Math.min((now-lastFrame)/1000,.1);lastFrame=now;if(!paused&&motion!=='reduced')sceneTime+=dt*(motion==='calm'?.25:1);
  yaw=-.18+manualYaw+sceneTime*.016;pitch=.48+manualPitch;ctx.clearRect(0,0,width,height);
  for(const s of stars){const flicker=motion==='reduced'?1:.8+Math.sin(sceneTime*.4+s.x*20)*.2;ctx.fillStyle=`rgba(158,195,214,${s.a*flicker})`;ctx.beginPath();ctx.arc(s.x*width,s.y*height,s.r,0,TAU);ctx.fill();}
  const cx=width*.5,cy=height*.47;glow(cx-60,cy,180,'rgba(29,141,148,ALPHA)',.22);glow(cx+70,cy-4,170,'rgba(98,61,158,ALPHA)',.22);
  for(let i=0;i<5;i++){
    ctx.beginPath();for(let j=0;j<=160;j++){const angle=j/160*TAU,r=95+i*39;const p=project(Math.cos(angle)*r,Math.sin(angle*2+i)*8,Math.sin(angle)*r);j?ctx.lineTo(p.x,p.y):ctx.moveTo(p.x,p.y);}ctx.strokeStyle=i===2?'rgba(96,168,169,.20)':'rgba(96,135,163,.12)';ctx.lineWidth=.6;ctx.stroke();
  }
  for(const p of particles){const a=sceneTime*.011,px=p.x*Math.cos(a)-p.z*Math.sin(a),pz=p.x*Math.sin(a)+p.z*Math.cos(a);const v=project(px,p.y,pz);ctx.fillStyle=`rgba(${pz>0?'110,182,195':'143,130,199'},${p.alpha*(pz>0?.65:.45)})`;ctx.fillRect(v.x,v.y,p.size*v.scale,p.size*v.scale);}
  // A quiet spherical core and orbital rings create depth without obscuring figures.
  glow(cx,cy,74,'rgba(71,216,191,ALPHA)',.12);glow(cx,cy,37,'rgba(112,231,207,ALPHA)',.17);
  for(let k=0;k<9;k++){ctx.beginPath();const r=32;for(let j=0;j<=80;j++){const a=j/80*TAU;const p=project(Math.cos(a)*r,Math.sin(a)*r*Math.cos(k*.35),Math.sin(a)*r*Math.sin(k*.35));j?ctx.lineTo(p.x,p.y):ctx.moveTo(p.x,p.y);}ctx.strokeStyle=`rgba(113,222,205,${k===0?.19:.045})`;ctx.lineWidth=.7;ctx.stroke();}
  ctx.setLineDash([2,5]);ctx.beginPath();ctx.ellipse(cx,cy,53*zoom,13*zoom,-.22,0,TAU);ctx.strokeStyle='rgba(134,225,210,.20)';ctx.stroke();ctx.setLineDash([]);
  const sorted=book.assets.map(a=>({a,p:pointFor(a)})).sort((x,y)=>y.p.z-x.p.z);
  for(const {a,p} of sorted){
    const isSelected=a.symbol===selected;glow(p.x,p.y,(isSelected?18:11)*p.scale,isSelected?'rgba(170,245,190,ALPHA)':a.type==='crypto'?'rgba(169,133,225,ALPHA)':'rgba(95,203,223,ALPHA)',isSelected?.45:.26);
    ctx.beginPath();ctx.arc(p.x,p.y,(isSelected?3:2)*p.scale,0,TAU);ctx.fillStyle=isSelected?'#ceffcb':a.color;ctx.fill();
    if(isSelected){ctx.beginPath();ctx.arc(p.x,p.y,9*p.scale,0,TAU);ctx.strokeStyle='rgba(175,242,197,.32)';ctx.lineWidth=.7;ctx.stroke();}
    const el=labelEls.get(a.symbol);el.style.left=`${p.x}px`;el.style.top=`${p.y+22*p.scale}px`;el.style.opacity=String(Math.max(.4,Math.min(1,p.scale*.85)));el.style.zIndex=String(Math.round(720-p.z));
  }
  for(let e=effects.length-1;e>=0;e--){const effect=effects[e],age=(now-effect.time)/1000;if(age>6){effects.splice(e,1);continue;}if(motion==='reduced')continue;const a=book.assets.find(a=>a.symbol===effect.symbol),p=pointFor(a);const f=1-age/6;const power=motion==='calm'?.35:1;
    if(effect.side==='buy'){
      for(let i=0;i<32;i++){const angle=randomSeed(i+effect.seed)*TAU,spread=(15+randomSeed(i+effect.seed+70)*80)*(age*.18+.2);const x=p.x+Math.cos(angle)*spread,y=p.y+Math.sin(angle)*spread*.6;glow(x,y,(18+randomSeed(i+30)*25)*power,'rgba(93,211,177,ALPHA)',f*.10*power);}
      ctx.beginPath();ctx.ellipse(p.x,p.y,(12+age*22)*power,(4+age*9)*power,-.3,0,TAU);ctx.strokeStyle=`rgba(165,242,192,${f*.45})`;ctx.lineWidth=.8;ctx.stroke();
    }else{
      glow(p.x,p.y,(28+age*25)*power,'rgba(207,159,248,ALPHA)',f*.45*power);const r=(12+age*45)*power;ctx.beginPath();ctx.ellipse(p.x,p.y,r,r*.45,-.4,0,TAU);ctx.strokeStyle=`rgba(212,177,255,${f*.65})`;ctx.lineWidth=1.3;ctx.stroke();
      for(let i=0;i<32;i++){const angle=i/32*TAU;ctx.beginPath();ctx.moveTo(p.x+Math.cos(angle)*r*.4,p.y+Math.sin(angle)*r*.4);ctx.lineTo(p.x+Math.cos(angle)*r,p.y+Math.sin(angle)*r);ctx.strokeStyle=`rgba(197,173,241,${f*.25*power})`;ctx.lineWidth=.6;ctx.stroke();}
    }
  }
  requestAnimationFrame(renderScene);
}
canvas.addEventListener('pointerdown',e=>{dragging=true;lastPointer={x:e.clientX,y:e.clientY};canvas.setPointerCapture(e.pointerId);});
canvas.addEventListener('pointermove',e=>{if(!dragging)return;manualYaw+=(e.clientX-lastPointer.x)*.005;manualPitch=Math.max(-.5,Math.min(.6,manualPitch+(e.clientY-lastPointer.y)*.003));lastPointer={x:e.clientX,y:e.clientY};});
canvas.addEventListener('pointerup',()=>dragging=false);canvas.addEventListener('pointercancel',()=>dragging=false);
canvas.addEventListener('wheel',e=>{if(e.ctrlKey||e.metaKey)return;e.preventDefault();zoom=Math.max(.65,Math.min(1.4,zoom-e.deltaY*.0007));},{passive:false});$('#orbit-reset').onclick=()=>{manualYaw=0;manualPitch=0;zoom=1;notify('Orbital view reset.');};

renderPortfolio();renderActivity();renderNews();requestAnimationFrame(renderScene);
setInterval(()=>{$('#clock').textContent=new Date().toISOString().slice(11,19)+' UTC';$('#event-count').textContent=events.toLocaleString();},1000);
setInterval(()=>{
  if(backendState||backendConnecting||paused||document.hidden)return;book.assets.forEach(a=>{const move=(Math.random()-.497)*.0007;a.price*=1+move;a.change+=move*100;});events+=book.assets.length;lastTick=Date.now();renderPortfolio();
},1500);
setInterval(()=>{if(backendState||backendConnecting||paused||document.hidden)return;if(Date.now()-lastTrade>23000){const previous=selected;const tradable=book.assets.filter(a=>a.quantity>0);selected=tradable[Math.floor(Math.random()*tradable.length)].symbol;trade(book.halted?'sell':Math.random()>.45?'buy':'sell',true);selected=previous;renderPortfolio();}if(Date.now()-lastNews>30000){newsItems.push(newsItems.shift());renderNews();lastNews=Date.now();events++;}},1000);
document.addEventListener('visibilitychange',()=>{if(!document.hidden){lastTrade=Date.now();lastNews=Date.now();lastFrame=performance.now();}});

function applyBackendState(state){
  backendState=state;backendConnecting=false;backendAvailable=true;
  book.cash=state.account.cash??0;book.openingEquity=Number(state.account.opening_equity??0);book.halted=state.halted;book.realized=state.account.realized??0;
  for(const a of book.assets){const current=state.assets.find(x=>x.symbol===a.symbol);if(current)Object.assign(a,{price:current.price??0,quantity:current.quantity,basis:current.basis,marketValue:current.market_value,unrealized:current.unrealized,quote:current.quote,quoteFresh:current.quote_fresh});}
  events=state.sequence;renderPortfolio();renderActivity();renderNews();
}
function renderBackendLabels(){
  const s=backendState,a=s.account,sim=s.mode==='simulator',ready=backendAvailable&&s.connected;
  const display=v=>v===null||v===undefined?'—':money(v);
  $('#equity').textContent=display(a.equity);$('#net-profit').textContent=a.net===null?display(a.equity_change):signed(a.net);
  const profitLabel=$$('.metric-label')[1];profitLabel.innerHTML=sim?'NET TRADING P&L <span>◷</span>':'EQUITY CHANGE <span>◷</span>';
  $('#equity-change').textContent=a.equity===null?'No broker balance available':sim?`${signed(a.net)} since simulator inception`:`${signed(a.equity_change??0)} since connection`;
  $('#equity-change').classList.toggle('negative',(sim?a.net:a.equity_change)<0);
  $('.metric:first-child .metric-bottom>span:last-child').textContent='';
  $('.mini-chart').style.display='none';
  $('#realized').textContent=a.realized===null?'Realized P&L not reconciled':`${money(a.realized)} realized`;
  $('#unrealized').textContent=a.equity===null?'':`${money(a.unrealized)} open`;
  $('.metric-note').textContent=sim?'Synthetic fills · simulated fees included':'Cash flows & fees not fully reconciled';
  $('#deployed').textContent=a.equity===null?'—':display(a.deployed);$('#cash').textContent=a.cash===null?'No account readback':`${money(a.cash)} cash`;
  const exposure=a.equity?a.deployed/a.equity:0;$('#exposure').textContent=`${(exposure*100).toFixed(1)}% exposure`;$('#capital-bar').style.width=`${exposure*100}%`;
  const active=s.workers.filter(w=>['healthy','error'].includes(w.status));const healthy=backendAvailable?active.filter(w=>w.status==='healthy').length:0;
  $('#health-card').dataset.status=ready?'healthy':'stale';document.body.dataset.connection=ready?'healthy':'stale';
  $('#health-card .metric-value').innerHTML=`${healthy} <span class="metric-dim">/ ${active.length} reporting</span>`;
  $('#health-label').textContent=!backendAvailable?'Service connection lost':!s.configured?'Paper credentials needed':s.connected?'Readback healthy':'Broker readback stale';
  $('#health-card .metric-bottom>span:last-child').textContent='Server telemetry ↗';
  $('#stream-status').textContent=!backendAvailable?'BACKEND DISCONNECTED':sim?'SIMULATOR / SERVER STREAM':s.connected?'ALPACA / PAPER STREAM':'ALPACA / NOT CONNECTED';
  $('.mode-badge>div').innerHTML=`${sim?'PERSISTENT SIMULATOR':'ALPACA PAPER'}<span>${!backendAvailable?'Service stale; orders blocked':sim?'Synthetic data · saved on server':!s.configured?'Configure paper keys on server':s.orders_enabled?'Paper-only order access':'Read-only · orders disabled'}</span>`;
  const current=book.assets.find(x=>x.symbol===selected);$('#selected-price').textContent=current.price?money(current.price):'—';
  const quoteAge=Date.now()-Date.parse(current.quote?.at);const fresh=ready&&current.quoteFresh&&quoteAge>=0&&quoteAge<=15000;
  $('#selected-change').textContent=current.quote?.source?`${current.quote.source} · ${fresh?'fresh':'STALE'} · ${new Date(current.quote.at).toISOString().slice(11,19)} UTC`:'No market quote';
  $('#selected-change').classList.toggle('negative',!fresh);
  const allowed=ready&&s.orders_enabled&&fresh;
  $('#demo-buy').textContent=sim?'＋ Local buy':'＋ Paper buy';$('#demo-sell').textContent=sim?'− Local sell':'− Paper sell';
  $('#demo-buy').disabled=!allowed||s.halted;$('#demo-sell').disabled=!allowed||current.quantity<=0;
  $('#halt-button').classList.toggle('halted',s.halted);$('#halt-button').innerHTML=s.halted?'<span>◇</span> Resume entries':'<span>◈</span> Halt entries';$('#halt-button').disabled=!backendAvailable;
  $('#risk-state').textContent=!ready?'READBACK REQUIRED':s.risk_policy?.latched?'LOSS CIRCUIT LATCHED':!s.orders_enabled?'READ ONLY':s.halted?'ENTRIES HALTED':s.untracked_positions?.length?'UNTRACKED HOLDINGS':'SERVER RISK CHECKS';
  $('.positions-footer .footnote').textContent=s.untracked_positions?.length?'Untracked holdings exist; new risk blocked':'Fresh quotes + server checks required per order';
  $('.activity-panel .tiny-live').textContent=sim?'● SYNTHETIC':'● PAPER READBACK';
  $('.positions-panel .tiny-live').textContent=sim?'● SIM':'● PAPER';
  $('.scene-corner.top-right').innerHTML=`<i></i> ${ready?(sim?'SYNTHETIC':'OBSERVING'):'STANDBY'}`;
  $$('.strategy-pills button')[0].innerHTML='<i></i> Swing <span>not enabled</span>';
  $$('.strategy-pills button')[1].innerHTML='<i></i> Intraday <span>not enabled</span>';
  $('.bottom-bar>span:first-child').innerHTML=`<span class="label-dot"></span> ${ready?'SERVER CONNECTED':'WAITING FOR READBACK'} <span class="muted">/</span> <span id="event-count">${events}</span> durable events`;
  $('.bottom-bar>span:last-child').textContent=`${sim?'PERSISTENT SIMULATOR · NO BROKER':s.connected?'ALPACA PAPER · NO LIVE TRADING':'ALPACA PAPER · NOT CONNECTED'} / BALANCE AS OF ${s.as_of?new Date(s.as_of).toISOString().slice(11,19)+' UTC':'UNKNOWN'} / v0.2`;
}
function backendFill(f){
  effects.push({symbol:f.symbol,side:f.side,time:performance.now(),seed:Math.random()*100});
  $('#scene-event').className=`scene-event ${f.side}`;$('#scene-event span').textContent=`${f.side==='buy'?'NEBULA':'SUPERNOVA'} / ${f.symbol} ${f.side.toUpperCase()} FILL / ${backendState?.mode==='simulator'?'SYNTHETIC':'PAPER'}`;
  clearTimeout(eventTimer);eventTimer=setTimeout(()=>{$('#scene-event').className='scene-event';$('#scene-event span').textContent='Every signal has a story.';},6500);
}
function renderBackendActivity(){
  const active=backendState.orders.filter(o=>!['filled','canceled','expired','rejected','replaced'].includes(o.status));
  const pending=active.map(o=>`<div class="activity-row"><span class="trade-indicator">◷</span><div class="activity-copy"><strong>${esc(o.request.intent?.symbol||o.broker.symbol||'Order')} · ${esc(o.status)}</strong><small>${esc(o.client_id)}</small></div>${!o.external&&o.broker.id?`<button class="text-button" data-cancel="${esc(o.client_id)}">Cancel</button>`:''}</div>`).join('');
  const fills=backendState.fills.slice(0,5).map(f=>`<div class="activity-row ${esc(f.side)}"><span class="trade-indicator">${f.side==='buy'?'↗':'↙'}</span><div class="activity-copy"><strong>${f.side==='buy'?'Bought':'Sold'} ${quantity(Number(f.quantity))} ${esc(f.symbol)} <span>@ ${money(Number(f.price))}</span></strong><small>${backendState.mode==='simulator'?'SYNTHETIC':'PAPER'} FILL · ${f.fee===null?'fee not reported':`fee ${money(Number(f.fee))}`}</small></div><span class="activity-time">${new Date(f.at).toISOString().slice(11,19)}</span></div>`).join('');
  $('#activity').innerHTML=pending+fills||'<div class="empty-state">No recorded orders or fills.<br>History will persist across restarts.</div>';
  $$('[data-cancel]').forEach(el=>el.onclick=async()=>{el.disabled=true;try{const result=await backend.cancel(el.dataset.cancel);notify(`Order readback: ${result.status}`);}catch(e){notify(e.message);}finally{el.disabled=false;}});
}
function renderBackendNews(){
  const items=backendState.news.filter(n=>newsFilter==='all'||(n.symbols||[]).some(s=>['BTC','ETH','SOL','BTCUSD','ETHUSD','SOLUSD'].includes(s))===(newsFilter==='crypto'));
  $('#news').innerHTML=items.slice(0,10).map(n=>`<button class="news-row" data-server-story="${esc(n.id)}"><span class="news-meta">${esc(n.source)} · ${esc(n.created_at)}</span><div class="news-title">${esc(n.headline)}</div><span class="news-tag">${esc((n.symbols||[]).join(' · '))}</span></button>`).join('')||'<div class="empty-state">No connected news items.<br>Enable the source after verifying entitlement.</div>';
  $$('[data-server-story]').forEach(el=>el.onclick=()=>{const n=backendState.news.find(n=>String(n.id)===el.dataset.serverStory);const link=/^https:\/\//.test(n.url||'')?`<a href="${esc(n.url)}" target="_blank" rel="noopener noreferrer">Read the source ↗</a>`:'';openDialog('Source evidence','INGESTED NEWS METADATA',`<h3>${esc(n.headline)}</h3><p class="article-body">Source: ${esc(n.source)}<br>Published: ${esc(n.created_at)}<br>Updated: ${esc(n.updated_at)}<br>First seen: ${esc(n.first_seen_at)}</p>${link}<div class="dialog-note">Source content is evidence, never an instruction to trade. No full article or AI summary is fabricated.</div>`);});
}
function drawRecordedChart(){
  const cutoff=Date.now()-(period==='1H'?3600000:period==='1D'?86400000:604800000);
  const values=backendState.equity_history.filter(p=>Date.parse(p.at)>=cutoff);
  $('#performance-title').textContent='Recorded account equity';$('.chart-summary>span').textContent='DURABLE BACKEND SNAPSHOTS';
  $('#equity-chart').setAttribute('aria-label','Recorded account equity from server snapshots');
  if(values.length<2){$('#chart-line').setAttribute('d','');$('#chart-area').setAttribute('d','');$('#chart-point').setAttribute('r','0');$('#trajectory-value').textContent='Collecting…';$('#chart-start').textContent='';$('#chart-middle').textContent='Waiting for observations';return;}
  const nums=values.map(p=>Number(p.value)),lo=Math.min(...nums),hi=Math.max(...nums),pad=Math.max((hi-lo)*.15,.5),first=Date.parse(values[0].at),last=Date.parse(values.at(-1).at);
  const pts=values.map((p,i)=>[(Date.parse(p.at)-first)/Math.max(last-first,1)*540,112-(nums[i]-lo+pad)/(hi-lo+2*pad)*106]);
  const d=pts.map(([x,y],i)=>`${i?'L':'M'}${x.toFixed(2)},${y.toFixed(2)}`).join(' ');$('#chart-line').setAttribute('d',d);$('#chart-area').setAttribute('d',`${d} L540,124 L0,124 Z`);$('#chart-point').setAttribute('r','3.5');$('#chart-point').setAttribute('cx',pts.at(-1)[0]);$('#chart-point').setAttribute('cy',pts.at(-1)[1]);
  const pct=nums[0]?(nums.at(-1)/nums[0]-1)*100:0;$('#trajectory-value').textContent=`${pct>=0?'+':''}${pct.toFixed(2)}%`;
  $('#chart-start').textContent=new Date(first).toISOString().slice(11,16);$('#chart-middle').textContent=new Date((first+last)/2).toISOString().slice(11,16);
}
function openOrderForm(side){
  if(!backendAvailable){notify('Backend connection is stale; orders blocked.');return;}
  const a=book.assets.find(x=>x.symbol===selected),sim=backendState.mode==='simulator';const id='astral-'+crypto.randomUUID();let cachedIntent=null;
  openDialog(`${side==='buy'?'Buy':'Sell'} ${a.symbol}`,sim?'PERSISTENT SIMULATOR / SYNTHETIC FILL':'ALPACA PAPER / NO LIVE MONEY',`<p class="dialog-copy">The server checks quote freshness, session, cash, working orders and portfolio limits before submission.</p><form id="order-form"><label class="setting-label" for="order-amount">Maximum order amount (USD)</label><input class="setting-select" id="order-amount" type="number" min="1" max="1000" step="0.01" value="${a.type==='etf'?Math.min(1000,Math.ceil(a.price*1.01)):250}" required><label class="setting-label" for="order-style">Execution policy</label><select class="setting-select" id="order-style"><option value="bounded">Marketable limit — bounded price</option><option value="patient">Passive limit — wait, then expire</option><option value="market">Market — price can move</option></select><div class="dialog-note">${sim?'Synthetic quotes and fills; no Alpaca request.':'Paper order on the fixed Alpaca paper endpoint.'} Quantity rounds down to the instrument increment. Limit orders expire after 60 seconds; cancellation must be confirmed.</div><button class="submit-order" type="submit">Submit ${sim?'simulated':'paper'} ${side}</button><p id="order-error" role="status" class="order-error"></p></form>`);
  $('#order-form').onsubmit=async e=>{e.preventDefault();const button=$('#order-form button');button.disabled=true;
    cachedIntent??={client_order_id:id,symbol:a.symbol,side,notional:Number($('#order-amount').value),execution:$('#order-style').value,ttl_seconds:60,strategy_id:'manual'};$('#order-amount').disabled=true;$('#order-style').disabled=true;
    try{const order=await backend.order(cachedIntent);$('#detail-dialog').close();notify(`Order ${order.status}. ${order.status==='unknown'?'Reconciliation required; no automatic resubmission.':'Fill effects follow confirmed readback.'}`);}catch(error){$('#order-error').textContent=error.message;button.textContent='Recheck the same intent';}finally{button.disabled=false;}
  };
}
function openBackendView(view){
  if(view==='strategies'){openDialog('Deterministic rules. Measured risk.','RESEARCH ALGORITHMS / EXECUTION DISABLED',`<p class="dialog-copy">A reproducible research planner now calculates ATR14 volatility, trend and prior-20-bar breakout candidates. It uses closed historical bars with source and known-at timestamps. No historical feed or automatic entry worker is connected yet.</p><div class="telemetry-row"><div>Swing planner<small>SMA20 / SMA50 · 2 × ATR stop reference</small></div><span>0.25% planned-loss budget</span></div><div class="telemetry-row"><div>Intraday planner<small>SMA10 / SMA30 · 1.5 × ATR stop reference</small></div><span>0.10% planned-loss budget</span></div><div class="telemetry-row"><div>Decision evidence<small>Inputs, policy version, hash and risk vetoes</small></div><span>${backendState.learning.observations} observations</span></div><div class="telemetry-row"><div>Loss circuit<small>1% UTC-day equity decline / 5% high-water drawdown</small></div><span>${backendState.risk_policy?.latched?'LATCHED / REVIEW REQUIRED':'Monitored'}</span></div><div class="dialog-note">Sizing includes fees, slippage and gap stress assumptions, then floors quantity to venue increments. Stop and target levels are planning references; no protective order is placed. Server limits: $1,000 planned order, $100 market order; 50% gross; 10% ETF / 5% crypto; 25% economic group. These are paper-test policy choices. Predictive accuracy and profitability remain unvalidated; learning promotion is disabled.</div>`);return;}
  if(view==='intelligence'){openDialog('Sources remain explicit.','BACKEND EVIDENCE',`<p class="dialog-copy">Price source and age are attached to every quote. The backend does not display fictional news when it is connected.</p><div class="telemetry-row"><div>Execution venue</div><span>${backendState.mode==='simulator'?'Synthetic simulator':'Alpaca paper only'}</span></div><div class="telemetry-row"><div>News adapter</div><span>${esc(backendState.workers.find(w=>w.name==='news')?.status||'disabled')}</span></div><div class="telemetry-row"><div>Filings, issuer holdings, macro</div><span class="source-state">Not connected yet</span></div><div class="dialog-note">Alpaca news is optional and entitlement-dependent. Stored article metadata includes revisions and first-seen timestamps; no full-text license is assumed.</div>`);return;}
  openDialog('Persistent service telemetry.','BACKEND / PAPER ONLY',`<p class="dialog-copy">${backendState.mode==='simulator'?'The server simulator is synthetic and keeps its book in SQLite.':'Alpaca mode never falls back to the simulator.'} The service continues when this browser is closed.</p>${backendState.workers.map(w=>`<div class="telemetry-row"><div>${esc(w.name)}<small>${esc(w.detail)} · ${esc(w.at)}</small></div><span>${esc(w.status)}</span></div>`).join('')}<div class="dialog-note">Uptime ${backendState.uptime_seconds}s · Model API spend $0 (no model workers enabled) · Hosting/data charges unknown · ${backendState.sequence} durable events. Broker readiness and process liveness are separate.</div><button class="submit-order" id="reconcile-now">Reconcile account and orders</button>`);
  $('#reconcile-now').onclick=async()=>{const b=$('#reconcile-now');b.disabled=true;try{await backend.reconcile();notify('Account and order readback completed.');$('#detail-dialog').close();}catch(e){notify(e.message);}finally{b.disabled=false;}};
}
backend=connectBackend({onState:applyBackendState,onFill:backendFill,onDisconnect:()=>{backendAvailable=false;if(backendState)renderBackendLabels();},onPreview:()=>{backendConnecting=false;$('.mode-badge>div').innerHTML='UI PREVIEW<span>Browser simulation · no backend</span>';}});
