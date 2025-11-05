// Global fetch wrapper to ensure Authorization header is always attached when a token exists
// Load this early (navbar-loader injects if missing)
// Note: auth-bootstrap.js may have already wrapped fetch, so check before double-wrapping
(function(){
  if (window.__authFetchInstalled || window.__authFetchBootstrapped) return; // idempotent
  window.__authFetchInstalled = true;
  const origFetch = window.fetch.bind(window);
  window.fetch = async function(input, init){
    try {
      init = init || {};
      init.headers = init.headers || {};
      // Normalize headers object
      let headersObj = {};
      if (init.headers instanceof Headers) {
        init.headers.forEach((v,k)=> headersObj[k] = v);
      } else if (Array.isArray(init.headers)) {
        init.headers.forEach(([k,v])=> headersObj[k]=v);
      } else {
        headersObj = {...init.headers};
      }
      if (!('authorization' in Object.fromEntries(Object.entries(headersObj).map(([k,v])=>[k.toLowerCase(),v])))) {
        // Prefer full auth object if available, fallback to bootstrap
        const authSource = window.auth || window.authBootstrap;
        if (authSource && authSource.getToken && authSource.getToken()) {
          headersObj = { ...headersObj, ...authSource.authHeader() };
        }
      }
      init.headers = headersObj;
    } catch(e){ /* swallow */ }
    return origFetch(input, init);
  };
})();
