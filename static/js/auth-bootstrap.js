// Auth Bootstrap - Synchronous auth state restoration
// This script MUST load first to prevent race conditions with navbar/API calls
(function(){
  'use strict';
  
  const TOKEN_KEY = 'token';
  const USER_KEY = 'user';
  const EXP_KEY = 'token_exp';
  
  function nowSec(){ return Math.floor(Date.now()/1000); }
  
  function getStoredToken(){ return localStorage.getItem(TOKEN_KEY); }
  function getStoredUser(){ 
    try { return JSON.parse(localStorage.getItem(USER_KEY)||'null'); } 
    catch { return null; } 
  }
  function isTokenValid(){
    const t = getStoredToken();
    if (!t) return false;
    const exp = parseInt(localStorage.getItem(EXP_KEY) || '0', 10);
    if (exp && nowSec() > exp) { 
      // Token expired - clean up
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
      localStorage.removeItem(EXP_KEY);
      return false; 
    }
    return true;
  }
  
  // Early auth check - redirect to login if not authenticated (except on login page)
  const isLoginPage = window.location.pathname.includes('login.html');
  if (!isLoginPage && !isTokenValid()) {
    console.log('[auth-bootstrap] No valid token found, redirecting to login');
    window.location.replace('/static/login.html');
    return;
  }
  
  // Create minimal auth object immediately for other scripts
  window.authBootstrap = {
    isAuthenticated: () => isTokenValid(),
    getToken: getStoredToken,
    getUser: getStoredUser,
    authHeader: () => {
      const t = getStoredToken();
      return t ? { 'Authorization': 'Bearer ' + t } : {};
    }
  };
  
  // Install global fetch wrapper immediately to ensure auth headers
  if (!window.__authFetchBootstrapped) {
    window.__authFetchBootstrapped = true;
    const origFetch = window.fetch.bind(window);
    window.fetch = async function(input, init){
      try {
        init = init || {};
        init.headers = init.headers || {};
        
        // Normalize headers
        let headersObj = {};
        if (init.headers instanceof Headers) {
          init.headers.forEach((v,k)=> headersObj[k] = v);
        } else if (Array.isArray(init.headers)) {
          init.headers.forEach(([k,v])=> headersObj[k]=v);
        } else {
          headersObj = {...init.headers};
        }
        
        // Add auth header if not present and we have a token
        const hasAuth = Object.keys(headersObj).some(k => k.toLowerCase() === 'authorization');
        if (!hasAuth && window.authBootstrap && window.authBootstrap.getToken()) {
          const authHeaders = window.authBootstrap.authHeader();
          headersObj = { ...headersObj, ...authHeaders };
        }
        
        init.headers = headersObj;
      } catch(e){ 
        console.warn('[auth-bootstrap] Error in fetch wrapper:', e); 
      }
      
      const resp = await origFetch(input, init);
      
      // Handle 401 responses
      if (resp.status === 401 && window.authBootstrap && window.authBootstrap.getToken()) {
        console.log('[auth-bootstrap] 401 response with valid token, clearing auth and redirecting');
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
        localStorage.removeItem(EXP_KEY);
        if (!window.location.pathname.includes('login.html')) {
          window.location.replace('/static/login.html');
        }
      }
      
      return resp;
    };
  }
  
  console.log('[auth-bootstrap] Auth state initialized, token valid:', isTokenValid());
})();
