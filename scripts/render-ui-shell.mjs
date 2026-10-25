// Pre-render the same shell/report helpers used in the browser. No data fetching.
import {readFile,writeFile} from 'node:fs/promises';
import {renderAppShell,shellClasses} from '../dist/app-shell.js';
import {renderReportPage,ui} from '../dist/ui.js';
import {reportPages} from '../dist/report-pages.js';
const root=new URL('../',import.meta.url);
for(const [file,page,entry] of [['index.html','overview','app'],['health.html','health','health'],['accounting.html','accounting','accounting'],['learning.html','learning','learning']]){
  const path=new URL('dist/'+file,root),shell=renderAppShell(page);
  let html=await readFile(path,'utf8');
  html=html.replace(/<html[^>]*>/,'<html lang="en" class="bg-app text-ink [&[data-booting]_.rail]:invisible [&[data-booting]_.workspace]:invisible">');
  html=html.replace(/<body[^>]*>/,`<body data-shell="${page}" class="${shellClasses.body}">`);
  html=html.replace(/<aside class="rail[^\"]*"[^>]*>[\s\S]*?<\/aside>/,`<aside class="${shellClasses.rail}" aria-label="Workspace navigation">${shell.rail}</aside>`);
  html=html.replace(/class="workspace[^\"]*"/,`class="${shellClasses.workspace}"`);
  html=html.replace(/<header class="topbar[^\"]*">([\s\S]*?)<\/header>/,(_,content)=>{
    let actions=content.match(/<div class="top-actions[^\"]*">[\s\S]*/)?.[0]||'<div class="top-actions"></div>';
    actions=actions.replace(/class="top-actions[^\"]*"/,`class="${shellClasses.actions}"`).replace(/class="connection[^\"]*"/,`class="${shellClasses.connection}"`);
    actions=actions.replace(/class="([^\"]*)" id="pause-button"/, 'class="$1 max-lg:hidden" id="pause-button"');
    actions=actions.replace(/<span id="stream-status"[^>]*>/,'<span id="stream-status" class="max-w-20 truncate lg:max-w-none">');
    return `<header class="${shellClasses.topbar}">${shell.header}${actions}</header>`;
  });
  if(reportPages[page])html=html.replace(/<main[^>]*>[\s\S]*?<\/main>/,`<main data-report-layout="ready" class="${page}-page ${ui.page}">${renderReportPage(reportPages[page])}</main>`);
  html=html.replace(/<main class="([^\"]*)"/,(_,classes)=>`<main class="${[...new Set((classes+' '+ui.page).split(/\s+/))].join(' ')}"`);
  html=html.replace(/<link[^>]*rel="(?:preload|modulepreload)"[^>]*>/g,'').replace(/<script src="\/boot.js"><\/script>/g,'');
  const modules=['ui','app-shell',entry,...(reportPages[page]?['report-pages']:[])];
  const hints=['dm-sans','space-grotesk'].map(font=>`<link rel="preload" href="/fonts/${font}-latin-variable.woff2" as="font" type="font/woff2" crossorigin>`).join('')+modules.map(name=>`<link rel="modulepreload" href="/${name}.js">`).join('');
  html=html.replace('</head>',hints+'<script src="/boot.js"></script></head>');
  html=html.replace(/<div id="boot-status"[^>]*>[\s\S]*?<\/div>/g,'');
  html=html.replace('</body>','<div id="boot-status" role="status" hidden class="fixed top-24 right-5 left-20 z-50 rounded-lg border border-line bg-surface px-5 py-4 text-caption text-muted md:left-rail">Opening ASTRAL…</div></body>');
  html=html.replace(/<script type="module" src="[^\"]+"><\/script>/,`<script type="module" src="/${entry}.js"></script>`);
  html=html.replace(/class="([^\"]*)"/g,(_,classes)=>`class="${[...new Set(classes.split(/\s+/))].join(' ')}"`);
  await writeFile(path,html);
}
console.log('Shared frames and report placeholders rendered before browser startup');
