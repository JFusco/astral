import {mountAppShell} from './app-shell.js';
import {mountReportPage} from './ui.js';
mountAppShell('learning');
mountReportPage({title:'Learning',subtitle:'Offline evidence readiness and checks of recorded model research.',
  cards:[
    {label:'OUTCOME READINESS',id:'outcome-status',value:'Unknown',note:'Reconciled financial labels are required',tone:'text-status-unknown'},
    {label:'RESOLVED NET P&L LABELS',id:'outcome-count',note:'Approvals and fills are not profit labels'},
    {label:'MODEL CONTRACTS CHECKED',id:'model-count',note:'Existing receipts only; no new model calls'},
    {label:'MODEL USEFULNESS',id:'usefulness-status',value:'Unknown',note:'Requires comparable, reconciled outcome pairs',tone:'text-status-unknown'},
  ],sections:[{title:'Data and outcomes',id:'learning-outcomes'},{title:'Model research quality',id:'model-quality'},
    {title:'Evidence inventory',id:'learning-inventory',subtitle:'Counts at the saved cutoff'},{title:'Recorded usage and costs',id:'learning-usage'}],
  wide:{title:'Protected evidence',id:'protected-evidence',subtitle:'Reserved forward windows'},
  limits:'<p>This page displays a saved offline audit. It cannot train, promote a strategy, change risk limits, call a model or place a trade.</p><p>Refresh reads the saved snapshot again. Protected outcome bodies and raw model prompts are not exposed here. A contract pass checks consistency with supplied evidence; it does not establish narrative truth or predictive skill.</p><div id="learning-issues"></div>'});
const $=s=>document.querySelector(s),esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const label=v=>String(v).replaceAll('_',' ');
const counts=values=>Object.keys(values||{}).length?`<dl class="report-counts space-y-2 [&>div]:flex [&>div]:justify-between [&>div]:gap-4 [&_dt]:capitalize [&_dd]:font-display [&_dd]:text-ink [&_dd]:tabular-nums">${Object.entries(values).map(([key,value])=>`<div><dt>${esc(label(key))}</dt><dd>${esc(value)}</dd></div>`).join('')}</dl>`:'<p>No records in this category.</p>';
document.querySelector('#learning-inventory').classList.add('overflow-x-auto');
let pending=false;
async function refresh(){
  if(pending)return;pending=true;$('#refresh-report').disabled=true;
  try{
    const response=await fetch('/api/learning/report',{cache:'no-store',signal:AbortSignal.timeout(5000)});
    if(!response.ok)throw new Error('Saved learning report is unavailable');
    const r=await response.json();if(r.status!=='saved_report')throw new Error(r.reason||'No saved learning report');
    $('#learning-connection').textContent='Saved learning snapshot';
    $('#report-notice').classList.remove('unavailable');
    $('#report-notice').textContent=`Saved ${r.as_of} · ${r.source_mode} records. This is an on-demand audit, not a live learning loop.`;
    const data=r.data_and_outcomes,model=r.model_research,checks=model.contract_checks;
    $('#outcome-status').textContent=label(data.status);
    $('#outcome-count').textContent=data.resolved_net_pnl_labels;
    $('#model-count').textContent=(checks.contract_passed||0)+(checks.contract_failed||0);
    $('#usefulness-status').textContent=label(model.usefulness.status);
    $('#learning-outcomes').innerHTML=`<p>${esc(data.reason)}</p>${counts(data.decision_categories)}<p>Training rows: ${esc(data.training_rows)}. Research packets inspected: ${esc(data.research_packets_inspected)}.</p>`;
    $('#model-quality').innerHTML=`<h3 class="text-body font-medium text-ink">Receipt categories</h3>${counts(model.receipt_categories)}<h3 class="text-body font-medium text-ink">Contract and timing checks</h3>${counts(checks)}<p>${esc(model.usefulness.reason)}</p>`;
    $('#learning-inventory').innerHTML=`<table class="w-full border-collapse text-left text-caption [&_th]:pb-3 [&_th]:pr-4 [&_th]:text-xxs [&_th]:font-semibold [&_th]:tracking-wider [&_th]:text-muted [&_td]:border-t [&_td]:border-line [&_td]:py-3 [&_td]:pr-4 [&_td]:text-ink"><thead><tr><th>SOURCE</th><th>AVAILABLE</th><th>PROTECTED</th><th>AFTER CUTOFF</th><th>INVALID TIME</th></tr></thead><tbody>${Object.entries(r.inventory).map(([name,v])=>`<tr><td>${esc(label(name))}</td>${['available','protected_window','after_cutoff','invalid_timestamp'].map(key=>`<td>${esc(v[key]||0)}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
    $('#learning-usage').innerHTML=`${counts(model.recorded_usage)}<p>Attributable model cost: ${model.costs.total_actual_usd===null?'unknown':esc(model.costs.total_actual_usd)+' USD'}.</p><p>Unknown-cost receipts: ${esc(model.costs.unknown_cost_receipts)}. ${esc(model.costs.scope)}.</p><p>Platform subscriptions and employer reimbursements belong to Accounting.</p>`;
    $('#protected-evidence').innerHTML=r.protected_windows.map(w=>`<div class="protected-window space-y-2 border-b border-line pb-4 last:border-0 last:pb-0"><h3 class="text-body font-medium text-ink">${esc(w.id)}</h3><p>${esc(w.starts_at)} → ${esc(w.ends_at)}</p><p>${esc(w.policy)}</p></div>`).join('');
    $('#learning-issues').innerHTML=Object.keys(r.issues).length?`<h3 class="text-body font-medium text-ink">Report issues</h3>${counts(r.issues)}`:'';
    $('#report-updated').textContent=`Report cutoff ${r.as_of}`;
  }catch(error){
    $('#learning-connection').textContent='Learning report unavailable';$('#report-notice').classList.add('unavailable');
    $('#report-notice').textContent=error.message+'. Any figures already displayed are retained from the previous response.';
  }finally{pending=false;$('#refresh-report').disabled=false;}
}
$('#refresh-report').onclick=refresh;refresh();
