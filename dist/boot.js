// Runs before body parsing: cloak only when JS is available, with a bounded fallback.
(()=>{
  const doc=document,root=doc.documentElement;
  root.dataset.booting='';
  let ready=false,failed=false;
  const showStatus=message=>{const node=doc.querySelector('#boot-status');if(node){node.textContent=message;node.hidden=false;}};
  const fallback=()=>{if(ready)return;failed=true;const main=doc.querySelector('main');if(main)main.hidden=true;delete root.dataset.booting;showStatus('This page is still loading. You can reload or use the navigation.');};
  const hint=setTimeout(()=>{if(!ready)showStatus('Opening ASTRAL…');},200);
  const deadline=setTimeout(fallback,3000);
  doc.addEventListener('astral:ready',()=>{ready=true;clearTimeout(hint);clearTimeout(deadline);delete root.dataset.booting;const main=doc.querySelector('main');if(main&&failed)main.hidden=false;const status=doc.querySelector('#boot-status');if(status)status.hidden=true;});
  window.addEventListener('error',event=>{if(event.error)fallback();});
  const modules={'/':'/app.js','/health.html':'/health.js','/accounting.html':'/accounting.js','/learning.html':'/learning.js'};
  const seen=new Set();
  function prefetch(href,intent=false){
    const url=new URL(href,location.href);
    if(url.origin!==location.origin||!(url.pathname in modules)||url.pathname===location.pathname)return;
    if(!seen.has(url.pathname)){
      seen.add(url.pathname);const link=doc.createElement('link');link.rel='prefetch';link.as='document';link.href=url.pathname;doc.head.append(link);
    }
    if(intent&&!seen.has('module:'+url.pathname)){
      seen.add('module:'+url.pathname);const link=doc.createElement('link');link.rel='modulepreload';link.href=modules[url.pathname];doc.head.append(link);
    }
  }
  doc.addEventListener('DOMContentLoaded',()=>{
    for(const type of ['pointerover','focusin','pointerdown'])doc.addEventListener(type,event=>{const link=event.target.closest?.('#app-pages a,.rail a[href]');if(link)prefetch(link.href,true);},{passive:true});
    if(!navigator.connection?.saveData){const warm=()=>Object.keys(modules).forEach(path=>prefetch(path));if('requestIdleCallback'in window)requestIdleCallback(warm,{timeout:1500});else setTimeout(warm,500);}
  },{once:true});
})();
