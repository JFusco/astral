// Shared build-time and browser report definitions. No ledger data is embedded.
export const reportPages={
  accounting:{title:'Accounting',subtitle:'Recorded costs, gross trade records and unresolved money evidence.',
  cards:[
    {label:'PERSONAL MONTHLY BUDGET',id:'personal-budget',note:'Known subscription inputs; coverage may be incomplete',tone:'text-accent'},
    {label:'RECORDED ACTUAL CHARGES',id:'actual-charges',note:'Confirmed records; budgets are not invoices',tone:'data-[state=unknown]:text-status-unknown'},
    {label:'NET TRADING P&L',id:'net-pnl',value:'Unknown',note:'Requires reconciled fees, basis and cash flows',tone:'data-[state=unknown]:text-status-unknown'},
    {label:'CUSTODY RECONCILIATION',id:'custody-status',note:'No report loaded',noteId:'fill-count',tone:'data-[state=issue]:text-status-down'},
  ],sections:[{title:'Unresolved records',id:'account-issues'},{title:'Operating costs',id:'operating-costs'}],
  wide:{title:'Gross matches by book',id:'gross-matches',subtitle:'Before fees · retained source records'},
  limits:'<p id="money-reason">Net results require reconciled money evidence.</p><p>Source CSVs and gross lot matches are preparation records, not certified tax lots or a filing. Subscription funding notes do not create payment or reimbursement transactions.</p><p>This page displays an on-demand saved snapshot. Refresh does not run an evaluation, change a ledger, call a model or enable trading.</p>'},
  learning:{title:'Learning',subtitle:'Offline evidence readiness and checks of recorded model research.',
  cards:[
    {label:'OUTCOME READINESS',id:'outcome-status',value:'Unknown',note:'Reconciled financial labels are required',tone:'text-status-unknown'},
    {label:'RESOLVED NET P&L LABELS',id:'outcome-count',note:'Approvals and fills are not profit labels'},
    {label:'MODEL CONTRACTS CHECKED',id:'model-count',note:'Existing receipts only; no new model calls'},
    {label:'MODEL USEFULNESS',id:'usefulness-status',value:'Unknown',note:'Requires comparable, reconciled outcome pairs',tone:'text-status-unknown'},
  ],sections:[{title:'Data and outcomes',id:'learning-outcomes'},{title:'Model research quality',id:'model-quality'},
    {title:'Evidence inventory',id:'learning-inventory',subtitle:'Counts at the saved cutoff'},{title:'Recorded usage and costs',id:'learning-usage'}],
  wide:{title:'Protected evidence',id:'protected-evidence',subtitle:'Reserved forward windows'},
  limits:'<p>This page displays a saved offline audit. It cannot train, promote a strategy, change risk limits, call a model or place a trade.</p><p>Refresh reads the saved snapshot again. Protected outcome bodies and raw model prompts are not exposed here. A contract pass checks consistency with supplied evidence; it does not establish narrative truth or predictive skill.</p><div id="learning-issues"></div>'},
};
