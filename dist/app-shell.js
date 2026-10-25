import {ui} from './ui.js';
const pages=[['overview','/','Overview','⌂'],['health','/health.html','App health','♡'],['accounting','/accounting.html','Accounting','▤'],['learning','/learning.html','Learning','✧']];
const railLink='rail-button grid size-10 shrink-0 cursor-pointer place-items-center rounded-lg border border-transparent text-xl text-muted no-underline transition-colors hover:bg-surface-raised hover:text-ink focus-visible:outline-2 focus-visible:outline-cyan aria-[current=page]:border-accent/20 aria-[current=page]:bg-accent/10 aria-[current=page]:text-accent';
const navLink='rounded-lg border border-transparent px-1 py-2 text-caption font-medium text-muted no-underline sm:px-2 lg:px-3 transition-colors hover:bg-surface-raised hover:text-ink focus-visible:outline-2 focus-visible:outline-cyan aria-[current=page]:border-accent/20 aria-[current=page]:bg-accent/5 aria-[current=page]:text-accent';
export function mountAppShell(page='overview'){
  const body=document.body;
  body.classList.add('min-w-80','bg-app','font-sans','text-body','text-ink','antialiased','scheme-dark');
  document.querySelector('.workspace').className='workspace ml-rail-compact min-w-0 md:ml-rail';
  const rail=document.querySelector('.rail');
  rail.className='rail fixed inset-y-0 left-0 z-50 flex w-rail-compact flex-col items-center gap-3 border-r border-line bg-app py-4 md:w-rail';
  const brand='<a href="/" class="brandmark relative mb-4 grid size-10 shrink-0 place-items-center rounded-full border border-cyan/25 font-display text-3xl font-medium no-underline" aria-label="Astral overview">A<span class="absolute top-0 right-0 size-1 rounded-full bg-accent shadow-sm shadow-accent"></span></a>';
  const extras=[['strategies','Strategy allocations','⌁'],['intelligence','Intelligence sources','◉'],['system','System telemetry','⌘']];
  const additional=extras.map(([id,label,icon])=>page==='overview'?`<button class="${railLink}" data-view="${id}" aria-label="${label}" title="${label}">${icon}</button>`:`<a href="/?view=${id}" class="${railLink}" aria-label="${label}" title="${label}">${icon}</a>`).join('');
  rail.innerHTML=brand+pages.map(([id,href,label,icon],index)=>`<a href="${href}" class="${railLink}" aria-label="${label}" title="${label}" ${id===page?'aria-current="page"':''}>${icon}</a>${index===0?additional:''}`).join('')+'<div class="flex-1"></div>'+(page==='overview'?`<button class="${railLink}" id="settings-button" aria-label="Display settings" title="Display settings">⚙</button>`:`<a href="/?view=settings" class="${railLink}" aria-label="Display settings" title="Display settings">⚙</a>`)+'<div class="avatar grid size-8 shrink-0 place-items-center rounded-full border border-line bg-surface-raised text-xxs text-muted" title="Private workspace">JF</div>';
  const top=document.querySelector('.topbar');
  top.className='topbar flex min-h-header flex-wrap items-center gap-x-4 gap-y-3 border-b border-line bg-app px-4 py-4 md:px-8 lg:flex-nowrap';
  top.querySelector('.wordmark')?.remove();
  top.insertAdjacentHTML('afterbegin','<div class="wordmark flex h-8 shrink-0 items-center gap-4 font-display text-lg font-semibold tracking-widest">ASTRAL<span class="wordmark-rule hidden h-4 border-r border-line 2xl:block"></span><span class="wordmark-sub hidden font-sans text-xxs font-medium tracking-widest text-muted 2xl:block">TRADING COMMAND</span></div>');
  top.querySelector('.top-actions').className='top-actions ml-auto flex h-9 items-center gap-3 text-caption text-muted';
  top.querySelector('#pause-button')?.classList.add('max-lg:hidden');
  top.querySelector('#stream-status')?.classList.add('max-w-20','truncate','lg:max-w-none');
  top.querySelectorAll('.connection').forEach(el=>el.className='connection flex items-center gap-2 text-xxs font-semibold tracking-wide text-muted [&.live]:text-status-healthy [&_i]:size-1.5 [&_i]:rounded-full [&_i]:bg-status-healthy');
  const nav=document.createElement('nav');nav.className='app-pages order-3 flex w-full flex-wrap items-center gap-1 lg:order-none lg:w-auto lg:flex-1';nav.id='app-pages';nav.setAttribute('aria-label','Main navigation');
  nav.innerHTML=pages.map(([id,href,label])=>`<a class="${navLink}" href="${href}" ${id===page?'aria-current="page"':''}>${label}</a>`).join('');
  top.querySelector('.wordmark').after(nav);
  document.querySelector('main').classList.add(...ui.page.split(' '));
}
