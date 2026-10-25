import {createPortfolio,totals,fill} from './core.js';

const $=s=>document.querySelector(s);const $$=s=>[...document.querySelectorAll(s)];
const money=(v,d=2)=>new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',minimumFractionDigits:d,maximumFractionDigits:d}).format(v);
const signed=(v,d=2)=>(v>=0?'+':'−')+money(Math.abs(v),d);
const quantity=v=>new Intl.NumberFormat('en-US',{maximumFractionDigits:6}).format(v);
const book=createPortfolio();let selected='BTC',paused=false,events=0,newsFilter='all',period='1D';
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
  $('#positions').innerHTML=open.map(a=>{const pnl=a.price*a.quantity-a.basis;return `<button class="position-row ${a.symbol===selected?'chosen':''}" data-asset="${a.symbol}" aria-label="Select ${a.name}, ${money(a.quantity*a.price)} value"><span class="position-asset"><span class="coin-icon">${a.icon}</span><span><strong>${a.symbol}</strong><small>${quantity(a.quantity)} ${a.type==='crypto'?a.symbol:'shares'}</small></span></span><span class="position-value"><strong>${money(a.quantity*a.price)}</strong><small class="${pnl<0?'negative':''}">${signed(pnl)} (${(pnl/a.basis*100).toFixed(2)}%)</small></span></button>`;}).join('');
  $$('#positions [data-asset]').forEach(el=>el.onclick=()=>selectAsset(el.dataset.asset));
  if(focusedAsset)$(`#positions [data-asset="${focusedAsset}"]`)?.focus({preventScroll:true});
  const a=book.assets.find(a=>a.symbol===selected);$('#selected-name').textContent=a.name;$('#selected-ticker').textContent=a.type==='crypto'?`${a.symbol} / USD`:`${a.symbol} / ETF`;$('#selected-icon').textContent=a.icon;$('#selected-price').textContent=money(a.price);$('#selected-change').textContent=`${a.change>=0?'+':''}${a.change.toFixed(2)}% · simulated`;$('#selected-change').classList.toggle('negative',a.change<0);
  $('#demo-buy').disabled=book.halted;$('#demo-sell').disabled=a.quantity<=0;
  $$('.orbit-label').forEach(el=>el.classList.toggle('selected',el.dataset.symbol===selected));
  const riskBlocked=book.halted||t.exposure>.5;$('#risk-state').textContent=book.halted?'ENTRIES HALTED':riskBlocked?'REDUCE EXPOSURE':'WITHIN LIMITS';$('#risk-state').style.color=riskBlocked?'#e5b489':'';
  drawChart();
}
function selectAsset(symbol){selected=symbol;renderPortfolio();}
function trade(side,automatic=false){
  const result=fill(book,selected,side,selected==='BTC'?650:500);
  if(!result.ok){if(!automatic)notify(result.reason);return;}
  lastTrade=Date.now();events++;activity.unshift(result);activity.splice(12);renderActivity();renderPortfolio();
  effects.push({symbol:selected,side,time:performance.now(),seed:Math.random()*100});
  $('#scene-event').className=`scene-event ${side}`;$('#scene-event span').textContent=`${side==='buy'?'NEBULA':'SUPERNOVA'} / ${selected} ${side.toUpperCase()} FILLED / SIMULATION`;
  clearTimeout(eventTimer);eventTimer=setTimeout(()=>{$('#scene-event').className='scene-event';$('#scene-event span').textContent='Every signal has a story.';},6500);
  if(!automatic)notify(`Simulated ${side}: ${quantity(result.quantity)} ${selected} at ${money(result.price)}. No broker order sent.`);
}
function renderActivity(){
  $('#activity').innerHTML=activity.slice(0,5).map(a=>`<div class="activity-row ${a.side}"><span class="trade-indicator">${a.side==='buy'?'↗':'↙'}</span><div class="activity-copy"><strong>${a.side==='buy'?'Bought':'Sold'} ${quantity(a.quantity)} ${a.symbol} <span>@ ${money(a.price)}</span></strong><small>${a.id} · SIMULATED FILL · fee ${money(a.fee)}</small></div><span class="activity-time">${new Date(a.time).toISOString().slice(11,19)}</span></div>`).join('');
  if(!activity.length)$('#activity').innerHTML='<div class="activity-row"><span class="trade-indicator">◎</span><div class="activity-copy"><strong>Paper lab initialized</strong><small>DEMO SNAPSHOT · NO BROKER CONNECTED</small></div></div>';
}
function renderNews(){
  const items=newsItems.map((n,i)=>({...n,index:i})).filter(n=>newsFilter==='all'||n.category===newsFilter);
  $('#news').innerHTML=items.slice(0,3).map(n=>`<button class="news-row" data-story="${n.index}"><span class="news-meta"><i class="${n.category==='crypto'?'crypto-source':''}"></i>${n.label}<span>· EXAMPLE</span></span><div class="news-title">${n.title}</div><span class="news-tag">${n.tag}</span></button>`).join('');
  $$('[data-story]').forEach(el=>el.onclick=()=>{const n=newsItems[Number(el.dataset.story)];openDialog('Illustrative intelligence','EXAMPLE / NOT CURRENT NEWS',`<span class="article-label">SIMULATED CONTENT</span><h3>${n.title}</h3><p class="article-body">${n.body}</p><div class="dialog-note">Source connection: none. The production design retains source URL, publication time, first-seen time, revisions, and feature versions for every item.</div>`);});
}
function drawChart(){
  const t=totals(book);const range=period==='1H'?.013:period==='1D'?.048:.085;const base=t.equity/(1+range);
  const values=Array.from({length:65},(_,i)=>{const x=i/64;const noise=(Math.sin(i*1.71)*.7+Math.sin(i*.57)*1.4)*Math.sin(Math.PI*x);return base+(t.equity-base)*(x+noise*.038);});
  const min=Math.min(...values)-(t.equity-base)*.12,max=Math.max(...values)+(t.equity-base)*.15;
  const points=values.map((v,i)=>[i/64*540,112-(v-min)/(max-min)*106]);const d=points.map(([x,y],i)=>`${i?'L':'M'}${x.toFixed(2)},${y.toFixed(2)}`).join(' ');
  $('#chart-line').setAttribute('d',d);$('#chart-area').setAttribute('d',`${d} L540,124 L0,124 Z`);$('#chart-point').setAttribute('cx',540);$('#chart-point').setAttribute('cy',points.at(-1)[1]);$('#trajectory-value').textContent=`+${(range*100).toFixed(2)}%`;$('#chart-start').textContent=period==='1H'?'−60 MIN':period==='1D'?'00:00':'−7 DAYS';$('#chart-middle').textContent=period==='1H'?'−30 MIN':period==='1D'?'12:00':'−3 DAYS';
}
function openDialog(title,eyebrow,content){$('#dialog-title').textContent=title;$('#dialog-eyebrow').textContent=eyebrow;$('#dialog-content').innerHTML=content;$('#detail-dialog').showModal();}
function openView(view){
  if(view==='overview'){$('#detail-dialog').close();window.scrollTo({top:0,behavior:motion==='reduced'?'instant':'smooth'});return;}
  if(view==='strategies')openDialog('Two horizons. One portfolio.','STRATEGY ALLOCATIONS / DEMO',`<p class="dialog-copy">A steady core and an opportunistic sleeve share one portfolio risk controller. These illustrative budgets are not active trading strategies.</p><div class="telemetry-row"><div>Core / swing<small>Daily signals · multi-day holding period</small></div><span>70% of strategy capital</span></div><div class="allocation-track"><span></span></div><div class="telemetry-row"><div>Opportunity / intraday<small>Five-minute signals · bounded risk</small></div><span>30% of strategy capital</span></div><div class="telemetry-row"><div>Learning / challenger<small>Record → replay → shadow → review</small></div><span>No candidate deployed</span></div><div class="dialog-note">Prototype guardrails: no leverage; 50% maximum total exposure; 20% maximum per asset; available cash required; halt blocks buys and permits sells. Complete production risk, session, stale-data and reconciliation controls remain to be built. No backtest or profitability evidence exists yet.</div>`);
  if(view==='intelligence')openDialog('An evidence-aware universe.','INTELLIGENCE SOURCES',`<p class="dialog-copy">Live source adapters will feed a timestamped, deduplicated evidence store. Every headline currently shown is a sample, not current news.</p>${[['Broker quotes & orders','Alpaca paper adapter'],['Market & symbol news','Alpaca / Benzinga entitlement to verify'],['Financial statements','SEC filings & Company Facts'],['ETF exposure','Official issuer holdings'],['Crypto context','CoinGecko + official project notices'],['Macro calendar','Federal Reserve / BLS / Treasury']].map(([a,b])=>`<div class="telemetry-row"><div>${a}<small>${b}</small></div><span class="source-state">Not connected</span></div>`).join('')}<div class="dialog-note">First-seen time is distinct from publication time. Stale inputs get visible warnings. Licensed content, coverage and account quotas must be verified before connection.</div>`);
  if(view==='system'){
    const t=totals(book);openDialog('The system behind the signal.','SIMULATED SYSTEM TELEMETRY',`<p class="dialog-copy">The browser simulation is running. There are no backend workers, broker connections, model calls or actual API charges.</p>${[['Market observer','Synthetic quotes / 1.5-second tick'],['Strategy engine','Demonstration events only'],['Risk controller',book.halted?'New entries halted':`${(t.exposure*100).toFixed(1)}% deployed / 50% cap`],['Execution adapter','Browser simulator / no broker'],['Evidence recorder',`${events} transient demo events`],['Learning evaluator','Design only / no evaluation run']].map(([a,b])=>`<div class="telemetry-row"><div>${a}<small>${b}</small></div><span>● DEMO</span></div>`).join('')}<div class="dialog-note">Session uptime: ${Math.floor((Date.now()-started)/1000)}s · Last synthetic tick: ${new Date(lastTick).toISOString().slice(11,19)} UTC · Simulated crypto fees: ${money(book.fees)} · Actual model API spend: $0. Browser state resets on reload.</div>`);
  }
}
function openSettings(){
  openDialog('Tune the atmosphere.','DISPLAY / SIMULATION',`<p class="dialog-copy">Keep the universe cinematic or turn the motion down. Financial values remain readable in every mode.</p><label class="setting-label" for="motion-select">Universe motion</label><select class="setting-select" id="motion-select"><option value="cinematic">Cinematic — orbital motion & fill effects</option><option value="calm">Calm — slower orbit & softer effects</option><option value="reduced">Reduced — static universe, no bursts</option></select><div class="telemetry-row"><div>Data mode<small>Synthetic prices, fictional news & browser fills</small></div><span>PAPER LAB</span></div><div class="dialog-note">This prototype cannot trade real money. Display settings are stored locally. A production service will run independently of this browser, with 24/7 monitoring and restart recovery.</div>`);
  $('#motion-select').value=motion;$('#motion-select').onchange=e=>{motion=e.target.value;document.body.dataset.motion=motion;localStorage.setItem('astral-motion',motion);effects.length=0;};
}
$('#close-dialog').onclick=()=>$('#detail-dialog').close();$('#detail-dialog').addEventListener('click',e=>{if(e.target===$('#detail-dialog')){const r=e.target.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)e.target.close();}});
$$('[data-view]').forEach(el=>el.onclick=()=>openView(el.dataset.view));$('#health-card').onclick=()=>openView('system');$('#settings-button').onclick=openSettings;
$('#demo-buy').onclick=()=>trade('buy');$('#demo-sell').onclick=()=>trade('sell');
$('#pause-button').onclick=()=>{paused=!paused;$('#pause-button').textContent=paused?'▷':'Ⅱ';$('#pause-button').setAttribute('aria-label',paused?'Resume simulation':'Pause simulation');$('#pause-button').title=paused?'Resume simulation':'Pause simulation';$('#stream-status').textContent=paused?'SIMULATION PAUSED':'SIMULATION STREAM';$('#health-label').textContent=paused?'Simulation paused':'All systems nominal';if(!paused){lastTrade=Date.now();lastNews=Date.now();}notify(paused?'Synthetic stream paused. Demo fill controls remain available.':'Simulation resumed. No external feeds connected.');};
$('#halt-button').onclick=()=>{book.halted=!book.halted;$('#halt-button').classList.toggle('halted',book.halted);$('#halt-button').innerHTML=book.halted?'<span>◇</span> Resume entries':'<span>◈</span> Halt entries';renderPortfolio();notify(book.halted?'Demo entries halted. Position updates and demo sells remain available.':'Demo entries resumed within the simulated exposure limits.');};
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
  if(paused||document.hidden)return;book.assets.forEach(a=>{const move=(Math.random()-.497)*.0007;a.price*=1+move;a.change+=move*100;});events+=book.assets.length;lastTick=Date.now();renderPortfolio();
},1500);
setInterval(()=>{if(paused||document.hidden)return;if(Date.now()-lastTrade>23000){const previous=selected;const tradable=book.assets.filter(a=>a.quantity>0);selected=tradable[Math.floor(Math.random()*tradable.length)].symbol;trade(book.halted?'sell':Math.random()>.45?'buy':'sell',true);selected=previous;renderPortfolio();}if(Date.now()-lastNews>30000){newsItems.push(newsItems.shift());renderNews();lastNews=Date.now();events++;}},1000);
document.addEventListener('visibilitychange',()=>{if(!document.hidden){lastTrade=Date.now();lastNews=Date.now();lastFrame=performance.now();}});
