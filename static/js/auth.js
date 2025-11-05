// Simple front-end auth helper
// Responsibilities: login, logout, token storage, auth header, role checks, guards
// Integrates with auth-bootstrap.js for race-condition-free operation

const auth = (function(){
  const TOKEN_KEY = 'token';
  const USER_KEY = 'user';
  const EXP_KEY = 'token_exp';

  function nowSec(){ return Math.floor(Date.now()/1000); }

  function saveSession(token, payload){
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify({ id: payload.sub, role: payload.role, username: payload.username, branch_id: payload.branch_id, branch_code: payload.branch_code }));
    if (payload.exp) localStorage.setItem(EXP_KEY, payload.exp);
  }

  function parseJwt (token) {
    try {
      const base64Url = token.split('.')[1];
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
          return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
      }).join(''));
      return JSON.parse(jsonPayload);
    } catch { return {}; }
  };

  async function login(username, password, branch_code){
    // Use JSON endpoint to allow branch selection
    const body = JSON.stringify({ username, password, branch_code });
    try {
      const res = await fetch('/api/v1/auth/login-json', { method:'POST', headers:{'Content-Type':'application/json'}, body });
      if (!res.ok) {
        let msg = 'Invalid credentials';
        try { const err = await res.json(); msg = err.detail || msg; } catch {}
        throw new Error(msg);
      }
      const data = await res.json();
      const payload = parseJwt(data.access_token);
      payload.role = data.role; // augment for convenience
      payload.username = data.username;
      payload.branch_id = data.branch_id;
      payload.branch_code = data.branch_code;
      saveSession(data.access_token, payload);
      
      // Redirect based on role after successful login
      const role = (data.role || '').toLowerCase();
      if(role === 'cashier' || role === 'pos_user') {
        window.location.replace('/static/pos.html');
      }
      
      // Update user display in navbar
      updateUserDisplayInNavbar();
      
      return data;
    } catch (e){
      throw e;
    }
  }

  function logout(reason){
    try {
      if (reason) {
        try { localStorage.setItem('logout_reason', reason); } catch {}
      }
      // Remove known keys
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
      localStorage.removeItem(EXP_KEY);
      localStorage.removeItem('current_pos_session_id');
      localStorage.removeItem('selected_branch_id');
      // Do NOT clear all localStorage so reason survives
      try { sessionStorage.clear(); } catch {}
    } catch(e){ console.warn('Logout cleanup issue', e); }
    window.location.replace('/static/login.html');
  }

  function getToken(){ return localStorage.getItem(TOKEN_KEY); }
  function getUser(){ try { return JSON.parse(localStorage.getItem(USER_KEY)||'null'); } catch { return null; } }
  function isAuthenticated(){
    // Use bootstrap's validation if available (more robust)
    if (window.authBootstrap && typeof window.authBootstrap.isAuthenticated === 'function') {
      return window.authBootstrap.isAuthenticated();
    }
    // Fallback to local validation
    const t = getToken();
    if (!t) return false;
    const exp = parseInt(localStorage.getItem(EXP_KEY) || '0', 10);
    if (exp && nowSec() > exp) { logout(); return false; }
    return true;
  }
  function authHeader(){ const t=getToken(); return t? { 'Authorization':'Bearer '+t }: {}; }
  function requireAuth(){ if(!isAuthenticated()) { window.location.replace('/static/login.html'); return false; } return true; }
  function hasRole(roles){ const u=getUser(); if(!u) return false; if(!Array.isArray(roles)) roles=[roles]; return roles.includes(u.role) || u.role==='super_admin'; }
  
  // Role-based redirection
  function redirectBasedOnRole(){
    const user = getUser();
    if(!user) return;
    
    const role = (user.role || '').toLowerCase();
    const currentPath = window.location.pathname;
    
    // POS users should only access POS pages
    if(role === 'cashier' || role === 'pos_user') {
      // If they're not on a POS page, redirect them
      if(!currentPath.includes('pos.html') && !currentPath.includes('login.html')) {
        window.location.replace('/static/pos.html');
        return;
      }
    }
  }

  // Update user display in navbar
  function updateUserDisplayInNavbar() {
    // Try to update user display if navbar loader is available
    if (window.navbarLoader && typeof window.navbarLoader.updateUserDisplay === 'function') {
      window.navbarLoader.updateUserDisplay();
    }
    // Also try the standalone function
    if (typeof updateUserDisplay === 'function') {
      updateUserDisplay();
    }
  }

  // Inactivity monitor
  const INACTIVITY_LIMIT_MS = (window.AUTH_INACTIVITY_LIMIT_MINUTES || 15) * 60 * 1000; // default 15 minutes
  let lastActivity = Date.now();
  function recordActivity(){ lastActivity = Date.now(); }
  ['click','mousemove','keydown','touchstart','scroll','focus'].forEach(evt=>{
    window.addEventListener(evt, recordActivity, { passive:true });
  });
  setInterval(()=>{
    try {
      if (!isAuthenticated()) return;
      const idle = Date.now() - lastActivity;
      if (idle > INACTIVITY_LIMIT_MS) {
        logout('Session expired due to inactivity');
      }
    } catch(e){ /* silent */ }
  }, 30000); // check every 30s

  async function switchBranch(branch_id){
    if(!isAuthenticated()) throw new Error('Not authenticated');
    const res = await fetch('/api/v1/auth/switch-branch', { method:'POST', headers:{ 'Content-Type':'application/json', ...authHeader() }, body: JSON.stringify({ branch_id }) });
    if(!res.ok) { let msg='Branch switch failed'; try { const e=await res.json(); msg=e.detail||msg; } catch{} throw new Error(msg); }
    const data = await res.json();
    const payload = parseJwt(data.access_token);
    payload.role = data.role; payload.username = data.username; payload.branch_id = data.branch_id; payload.branch_code = data.branch_code;
    saveSession(data.access_token, payload);
    updateUserDisplayInNavbar();
    return data;
  }

  return { login, logout, getToken, getUser, isAuthenticated, authHeader, requireAuth, hasRole, redirectBasedOnRole, switchBranch, updateUserDisplayInNavbar };
})();

// Auto-attach to window
window.auth = auth;
// Provide legacy global logout() for inline onclick="logout()" usage
if (typeof window.logout !== 'function') {
  window.logout = function(reason){ auth.logout(reason); };
}
// Signal to other scripts (e.g., navbar-loader) that auth is ready
try { document.dispatchEvent(new Event('authReady')); } catch(_) {}
