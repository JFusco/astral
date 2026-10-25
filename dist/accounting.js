import {mountAppShell} from './app-shell.js';
import {ui,mountReportPage,finishBoot} from './ui.js';
import {reportPages} from './report-pages.js';
mountAppShell('accounting');
mountReportPage(reportPages.accounting);
const custody=document.createElement('div');custody.id='custody-differences';custody.className=ui.panelBody+' overflow-x-auto';document.querySelector('#account-issues').after(custody);
const $=s=>document.querySelector(s),esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const amounts=v=>v&&Object.keys(v).length?Object.entries(v).map(([currency,value])=>`${currency} ${value}`).join(' · '):'Unknown';
let pending=false;
async function refresh(){
  if(pending)return;pending=true;$('#refresh-report').disabled=true;
  try{
    const response=await fetch('/api/accounting/report',{cache:'no-store',signal:AbortSignal.timeout(5000)});
    if(!response.ok)throw new Error('Saved accounting report is unavailable');
    const r=await response.json();if(r.status!=='saved_report')throw new Error(r.reason||'No saved accounting report');
    $('#accounting-connection').textContent='● Saved accounting snapshot';
    $('#report-notice').classList.remove('unavailable');
    $('#report-notice').textContent=`Saved ${r.as_of} · ${r.source_mode} records. This is an on-demand snapshot, not a live balance or profit calculation.`;
    const c=r.operating_costs;
    $('#personal-budget').textContent=amounts(c.monthly_astral_personal_budget_by_currency);
    $('#actual-charges').textContent=c.actual_total_by_currency===null?'Unknown':amounts(c.actual_total_by_currency);
    $('#actual-charges').dataset.state=c.actual_total_by_currency===null?'unknown':'recorded';
    $('#net-pnl').textContent=r.money_results.realized_net_pnl_usd===null?'Unknown':`USD ${r.money_results.realized_net_pnl_usd}`;
    $('#net-pnl').dataset.state=r.money_results.realized_net_pnl_usd===null?'unknown':'recorded';
    $('#custody-status').textContent=r.custody.status==='needs_review'?'Needs review':'Quantities matched';
    $('#custody-status').dataset.state=r.custody.status==='needs_review'?'issue':'recorded';
    $('#fill-count').textContent=`${r.fill_rows} retained fill rows · fee coverage unverified`;
    const issues=Object.entries(r.issues);
    $('#account-issues').innerHTML=issues.length?`<ul>${issues.map(([name,count])=>`<li>${esc(name.replaceAll('_',' '))} (${esc(count)})</li>`).join('')}</ul>`:'No quantity issues in this saved snapshot. Net results still require complete evidence.';
    $('#custody-differences').innerHTML=r.custody.differences.length?`<table class="w-full border-collapse text-left text-caption [&_th]:pb-3 [&_th]:pr-4 [&_th]:text-xxs [&_th]:font-semibold [&_th]:tracking-wider [&_th]:text-muted [&_td]:border-t [&_td]:border-line [&_td]:py-3 [&_td]:pr-4 [&_td]:text-ink"><thead><tr><th>ASSET</th><th>RECORDED NET QTY</th><th>BROKER QTY</th><th>UNEXPLAINED QTY</th></tr></thead><tbody>${r.custody.differences.map(d=>`<tr><td>${esc(d.symbol)}</td><td>${esc(d.recorded_net_quantity)}</td><td>${esc(d.broker_quantity)}</td><td>${esc(d.unexplained_quantity)}</td></tr>`).join('')}</tbody></table>`:'No comparable custody snapshot available.';
    $('#operating-costs').innerHTML=`<p>Personal ASTRAL monthly budget: ${esc(amounts(c.monthly_astral_personal_budget_by_currency))}</p><p>Subscription coverage: ${c.monthly_budget_complete?'User-asserted complete':'Incomplete / unverified plans remain'}</p><p>Recorded confirmed charge subtotal: ${esc(amounts(c.recorded_confirmed_charges_by_currency))}</p><p>Estimated charges: ${esc(amounts(c.estimated_charges_by_currency))}</p><p>Budgets, bills and included allocations are separate. Missing records do not mean zero spending. Employer-funded subscriptions can have a $0 personal budget.</p>`;
    const gross=r.gross_fifo_diagnostics;
    $('#gross-matches').innerHTML=`<p>${esc(gross.status.replaceAll('_',' '))}. ${esc(gross.basis)}</p>`+(gross.by_book.length?`<table class="w-full border-collapse text-left text-caption [&_th]:pb-3 [&_th]:pr-4 [&_th]:text-xxs [&_th]:font-semibold [&_th]:tracking-wider [&_th]:text-muted [&_td]:border-t [&_td]:border-line [&_td]:py-3 [&_td]:pr-4 [&_td]:text-ink"><thead><tr><th>ASSET</th><th>BOOK</th><th>GROSS REALIZED USD</th></tr></thead><tbody>${gross.by_book.map(b=>`<tr><td>${esc(b.symbol)}</td><td>${esc(b.book)}</td><td>${esc(b.gross_realized_usd)}</td></tr>`).join('')}</tbody></table>`:'No gross lot matches recorded.');
    $('#money-reason').textContent=r.money_results.reason;
    $('#report-updated').textContent=`Report cutoff ${r.as_of}`;
  }catch(error){
    $('#accounting-connection').textContent='● Accounting report unavailable';
    $('#report-notice').classList.add('unavailable');$('#report-notice').textContent=error.message+'. Any figures already displayed are retained from the previous response.';
  }finally{pending=false;$('#refresh-report').disabled=false;finishBoot();}
}
$('#refresh-report').onclick=refresh;
refresh();
