// Shared utility recipes. Keep complete class names visible to Tailwind's scanner.
export const ui=Object.freeze({
  page:'mx-auto w-full max-w-page px-4 py-6 md:px-8 md:py-8',
  heading:'mb-6 flex flex-wrap items-center justify-between gap-4',
  title:'font-display text-title font-medium tracking-tight text-ink',
  eyebrow:'mb-2 text-xxs font-semibold tracking-widest text-cyan',
  subtitle:'mt-2 max-w-3xl text-body text-muted',
  summaryGrid:'mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4',
  card:'min-h-36 rounded-panel border border-line bg-surface p-5 text-left',
  label:'flex items-center justify-between gap-2 text-xxs font-semibold tracking-widest text-muted',
  value:'my-3 block font-display text-metric font-medium tracking-tight tabular-nums',
  note:'block text-caption leading-relaxed text-muted',
  columns:'mb-6 grid grid-cols-1 gap-6 lg:grid-cols-2',
  panel:'overflow-hidden rounded-panel border border-line bg-surface',
  panelHeading:'flex min-h-16 flex-wrap items-center justify-between gap-3 border-b border-line px-5 py-4',
  panelBody:'space-y-4 p-5 text-body leading-relaxed text-muted',
  sectionTitle:'text-section font-medium text-ink',
  button:'inline-flex min-h-10 cursor-pointer items-center justify-center gap-2 rounded-lg border border-line bg-surface-raised px-4 py-2 text-caption font-medium text-ink transition-colors hover:border-cyan/50 hover:text-cyan focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cyan disabled:cursor-not-allowed disabled:opacity-40',
  notice:'mb-6 rounded-lg border border-cyan/25 bg-cyan/5 px-5 py-4 text-caption leading-relaxed text-muted [&.unavailable]:border-status-down/50 [&.unavailable]:text-status-down',
  footer:'mt-6 flex flex-wrap justify-between gap-3 border-t border-line py-5 text-xxs tracking-wider text-faint',
  table:'w-full border-collapse text-left text-caption [&_th]:pb-3 [&_th]:pr-4 [&_th]:text-xxs [&_th]:font-semibold [&_th]:tracking-wider [&_th]:text-muted [&_td]:border-t [&_td]:border-line [&_td]:py-3 [&_td]:pr-4 [&_td]:text-ink',
  counts:'space-y-2 [&>div]:flex [&>div]:justify-between [&>div]:gap-4 [&_dt]:capitalize [&_dd]:font-display [&_dd]:text-ink [&_dd]:tabular-nums',
});
export const escapeHtml=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const statusClass={healthy:'text-status-healthy',degraded:'text-status-degraded',down:'text-status-down',unknown:'text-status-unknown',inactive:'text-status-inactive',checking:'text-status-checking'};
export const statusDot={healthy:'bg-status-healthy',degraded:'bg-status-degraded',down:'bg-status-down',unknown:'bg-status-unknown',inactive:'bg-status-inactive',checking:'bg-status-checking'};
export const topicClass={core:'text-topic-core',execution:'text-topic-execution',market:'text-topic-market',workers:'text-topic-workers',sources:'text-topic-sources',providers:'text-topic-providers',models:'text-topic-models',local:'text-topic-local'};
export function pageHeader({title,eyebrow,subtitle,action=''}){
  return `<div class="page-heading ${ui.heading}"><div><p class="eyebrow ${ui.eyebrow}">${escapeHtml(eyebrow)}</p><h1 class="${ui.title}">${escapeHtml(title)}</h1><p class="page-subtitle ${ui.subtitle}">${escapeHtml(subtitle)}</p></div>${action}</div>`;
}
export function summaryCard({label,id,note,noteId='',value='—',tone=''}){
  return `<div class="summary-card ${ui.card}"><span class="summary-label ${ui.label}">${escapeHtml(label)}</span><strong id="${escapeHtml(id)}" class="summary-value ${ui.value} ${tone}">${escapeHtml(value)}</strong><small ${noteId?`id="${escapeHtml(noteId)}"`:''} class="summary-note ${ui.note}">${escapeHtml(note)}</small></div>`;
}
export function panel({title,id,subtitle=''}){
  return `<section class="panel ${ui.panel}"><div class="panel-heading ${ui.panelHeading}"><h2 class="${ui.sectionTitle}">${escapeHtml(title)}</h2>${subtitle?`<span class="text-caption text-muted">${escapeHtml(subtitle)}</span>`:''}</div><div id="${escapeHtml(id)}" class="panel-body ${ui.panelBody}">No report loaded.</div></section>`;
}
export function mountReportPage({title,subtitle,cards,sections,wide,limits}){
  document.querySelector('main').innerHTML=pageHeader({title,subtitle,eyebrow:`APPLICATION / ${title.toUpperCase()}`,action:`<button class="${ui.button}" id="refresh-report">Refresh report</button>`})+
    `<div class="report-notice ${ui.notice}" id="report-notice" role="status">Reading the latest saved report. Refresh does not start an evaluation.</div><section class="${ui.summaryGrid}" aria-label="${escapeHtml(title)} summary">${cards.map(summaryCard).join('')}</section><div class="${ui.columns}">${sections.map(panel).join('')}</div>${panel(wide)}<section class="report-limits mt-6 space-y-4 border-t border-line py-6 text-body leading-relaxed text-muted"><h2 class="${ui.sectionTitle}">Evaluation boundaries</h2>${limits}</section><footer class="bottom-bar ${ui.footer}"><span>${escapeHtml(title.toUpperCase())} / SAVED LOCAL REPORT</span><span id="report-updated">Waiting for a saved report</span></footer>`;
}
