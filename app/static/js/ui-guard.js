// UI Guard for role-based frontend enforcement
(function(){
  // Wrap fetch once for global 401/403 handling
  if(!window.__fetchWrapped){
    window.__fetchWrapped=true;
    const origFetch = window.fetch;
    window.fetch = async function(resource, options={}){
      const resp = await origFetch(resource, options);
      if(resp.status === 401){
        // Only force logout if a token was actually present (avoid nuking session due to early unauthenticated prefetch)
        try {
          const hasToken = window.auth && auth.getToken();
          const path = (typeof resource === 'string' ? resource : (resource?.url||''));
          if(hasToken) {
            if(window.auth){ auth.logout('Session expired'); }
            else window.location.replace('/static/login.html');
          }
        } catch(_) {}
        return resp;
      }
      if(resp.status === 403){
        try {
          const clone = resp.clone();
          const data = await clone.json().catch(()=>null);
          const msg = data?.message || 'Forbidden';
          if(window.modernUI){ modernUI.showNotification(msg, 'warning'); }
        } catch(_){}
      }
      return resp;
    };
  }

  function guard(){
    if(!window.auth || !auth.isAuthenticated()) return; // login page handles itself
    const user = auth.getUser();
    if(!user) return;
    const role = (user.role||'').toLowerCase();

    // POS users (cashier/pos_user) should only access POS pages
    if(role === 'cashier' || role === 'pos_user') {
      const currentPath = window.location.pathname;
      
      // If they're not on a POS page, redirect them
      if(!currentPath.includes('pos.html') && !currentPath.includes('login.html')) {
        window.location.replace('/static/pos.html');
        return;
      }
      
      // If they're on a POS page, hide any navigation that could take them to other pages
      if(currentPath.includes('pos.html')) {
        // Hide home button and other navigation elements that could redirect to ERP
        const homeButtons = document.querySelectorAll('button, a, .btn');
        homeButtons.forEach(el => {
          const txt = (el.textContent || '').toLowerCase();
          const href = el.getAttribute('href') || '';
          const onclick = el.getAttribute('onclick') || '';
          
          // Hide elements that could redirect to ERP pages
          if(txt.includes('home') || txt.includes('dashboard') || 
             href.includes('index.html') || href.includes('dashboard') ||
             onclick.includes('goHome') || onclick.includes('index.html')) {
            el.style.display = 'none';
            el.setAttribute('disabled', 'disabled');
          }
        });
      }
    }

    // Apply read-only restrictions for cashier on products page (if they somehow get there)
    if(role === 'cashier' && /products\.html$/i.test(window.location.pathname)){
      // Disable create/edit/delete buttons
      document.querySelectorAll('button, a').forEach(el=>{
        const txt = (el.textContent||'').toLowerCase();
        if(/add|new|edit|delete|update|upload|remove|save/.test(txt)){
          el.classList.add('disabled');
          el.setAttribute('disabled','disabled');
          el.addEventListener('click', e=>e.preventDefault(), true);
        }
      });
      // Optional notice
      if(!document.getElementById('cashier-ro-banner')){
        const div = document.createElement('div');
        div.id='cashier-ro-banner';
        div.style.cssText='background:#fff3cd;border:1px solid #ffeeba;padding:6px 10px;font-size:12px;margin:8px 0;border-radius:4px;color:#856404;';
        div.innerHTML='<strong>Read Only:</strong> Cashier role cannot modify product records.';
        const target = document.querySelector('h1, h2, header') || document.body.firstElementChild;
        if(target && target.parentNode) target.parentNode.insertBefore(div, target.nextSibling);
      }
    }
  }
  document.addEventListener('DOMContentLoaded', guard);
  document.addEventListener('navbarLoaded', guard);
  // If auth was already present before ui-guard loaded, emit authReady to unify events for late listeners
  if(window.auth){ try { document.dispatchEvent(new Event('authReady')); } catch(_) {} }
})();
