// Simple front-end auth helper
// Responsibilities: login, logout, token storage, auth header, role checks, guards
// Integrates with auth-bootstrap.js for race-condition-free operation

const auth = (function(){
  const TOKEN_KEY = 'token';
  const USER_KEY = 'user';
  const EXP_KEY = 'token_exp';
  // Dev override: automatically disable inactivity logout when running on localhost unless explicitly re-enabled
  let DEV_NO_TIMEOUT = false;
  try {
    const host = (window.location && window.location.hostname) || '';
    if (['localhost','127.0.0.1','0.0.0.0'].includes(host)) {
      DEV_NO_TIMEOUT = true;
      console.log('[Auth] Localhost detected -> disabling inactivity timeout');
    }
    if (window.DEV_DISABLE_TIMEOUT === true) {
      DEV_NO_TIMEOUT = true;
      console.log('[Auth] DEV_DISABLE_TIMEOUT flag present -> disabling inactivity timeout');
    }
  } catch(_) {}

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
      
      // Validate that we got a real user (not the old dummy user)
      if (data.user_id === 'dev_user_123') {
        console.warn('Development login returned dummy user, trying with real credentials...');
        // Try with a known real user
        const realLoginBody = JSON.stringify({ username: 'superadmin', password: 'superadmin', branch_code: branch_code || 'MAIN' });
        const realRes = await fetch('/api/v1/auth/login-json', { method:'POST', headers:{'Content-Type':'application/json'}, body: realLoginBody });
        if (realRes.ok) {
          const realData = await realRes.json();
          if (realData.user_id !== 'dev_user_123') {
            console.log('Using real user credentials');
            data = realData;
          }
        }
      }
      
      const payload = parseJwt(data.access_token);
      payload.role = data.role; // augment for convenience
      payload.username = data.username;
      payload.branch_id = data.branch_id;
      payload.branch_code = data.branch_code;
      saveSession(data.access_token, payload);
      
      // Broadcast login to other tabs
      broadcastSessionUpdate('login', {
        token: data.access_token,
        user: { id: payload.sub, role: payload.role, username: payload.username, branch_id: payload.branch_id, branch_code: payload.branch_code },
        exp: payload.exp
      });
      
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
      
      // Broadcast logout to other tabs before clearing local storage
      broadcastSessionUpdate('logout');
      
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

  // Inactivity monitor - default 30 minutes (overridden by server); disabled in localhost dev
  let INACTIVITY_LIMIT_MS = (window.AUTH_INACTIVITY_LIMIT_MINUTES || 30) * 60 * 1000;
  let lastActivity = Date.now();
  function recordActivity(){ lastActivity = Date.now(); }
  ['click','mousemove','keydown','touchstart','scroll','focus'].forEach(evt=>{
    window.addEventListener(evt, recordActivity, { passive:true });
  });
  document.addEventListener('visibilitychange', ()=>{ if(!document.hidden) recordActivity(); });

  // Attempt to load server-configured timeout to override if available
  // preserve existing DEV_NO_TIMEOUT if already set by hostname heuristic
  let serverDebug = false;
  (async function loadTimeoutSetting(){
    try {
  const res = await fetch('/api/v1/settings/'); // unified settings endpoint (legacy alias)
      if(res.ok){
        const json = await res.json();
        // Support different response shapes; look for security.session_timeout_minutes or session_timeout
        let minutes = json?.data?.security?.session_timeout_minutes || json?.data?.session_timeout || json?.settings?.session_timeout_minutes;
          if(json?.data?.general?.debug_mode === true || json?.data?.debug_mode === true){
            serverDebug = true;
            DEV_NO_TIMEOUT = true;
            console.log('[Auth] Server debug mode active: disabling inactivity logout & auto-refresh threshold gating');
          }
        if(minutes && !isNaN(minutes) && minutes>0){
          INACTIVITY_LIMIT_MS = minutes * 60 * 1000;
          if(window.console) console.log('[Auth] Inactivity limit set to', minutes,'minutes from settings');
        }
      }
    } catch(e){ /* ignore */ }
  })();

  // Heartbeat / keep-alive to refresh token before expiry if user active
  let REFRESH_THRESHOLD_MIN = 10; // default, will be overridden by settings if available
  let IDLE_WARNING_MINUTES = 2; // default warning lead time
  // Load server-configurable refresh threshold & idle warning minutes
  (async function loadSessionTimingSettings(){
    try {
  const res = await fetch('/api/v1/settings/');
      if(res.ok){
        const json = await res.json();
        const security = json?.data?.security || {};
        if(security.refresh_threshold_minutes && !isNaN(security.refresh_threshold_minutes)) {
          REFRESH_THRESHOLD_MIN = security.refresh_threshold_minutes;
          console.log('[Auth] Refresh threshold set to', REFRESH_THRESHOLD_MIN, 'minutes');
        }
        if(security.idle_warning_minutes && !isNaN(security.idle_warning_minutes)) {
          IDLE_WARNING_MINUTES = security.idle_warning_minutes;
          console.log('[Auth] Idle warning lead time set to', IDLE_WARNING_MINUTES, 'minutes');
        }
      }
    } catch(e){ /* ignore */ }
  })();
  let refreshing = false;
  async function maybeRefreshToken(){
    try {
      if(refreshing) return;
      const exp = parseInt(localStorage.getItem(EXP_KEY) || '0', 10);
      if(!exp) return;
      const now = nowSec();
      const minutesLeft = (exp - now)/60;
      const idle = Date.now() - lastActivity;
    if(DEV_NO_TIMEOUT) return; // token already long-lived
      if(minutesLeft < REFRESH_THRESHOLD_MIN && idle < (INACTIVITY_LIMIT_MS - 60000)){
        refreshing = true;
        const resp = await fetch('/api/v1/auth/refresh', { method:'POST', headers: authHeader() });
        if(resp.ok){
          const data = await resp.json();
            const payload = parseJwt(data.access_token);
            payload.role = data.role; payload.username = data.username; payload.branch_id = data.branch_id; payload.branch_code = data.branch_code;
            saveSession(data.access_token, payload);
            if(window.console) console.log('[Auth] Token refreshed');
            try { broadcastSessionUpdate('refresh', { exp: payload.exp }); } catch{}
        } else {
            if(window.console) console.warn('[Auth] Token refresh failed', resp.status);
        }
        refreshing = false;
      }
    } catch(e){ refreshing=false; }
  }
  setInterval(maybeRefreshToken, 120000); // check every 2 minutes
  setInterval(()=>{
    try {
      if (!isAuthenticated()) return;
      const idle = Date.now() - lastActivity;
      if(DEV_NO_TIMEOUT) return; // hard skip in dev
      if (idle > INACTIVITY_LIMIT_MS) {
        console.warn('[Auth] Inactivity logout triggered', { idleMs: idle, limitMs: INACTIVITY_LIMIT_MS });
        logout('Session expired due to inactivity');
      }
  // Idle warning (configurable minutes before timeout) only if user currently idle beyond threshold - lead time
  const effectiveLead = Math.min(IDLE_WARNING_MINUTES, Math.max(1, (INACTIVITY_LIMIT_MS/60000) - 1));
  const warnThreshold = INACTIVITY_LIMIT_MS - (effectiveLead*60*1000);
      const existing = document.getElementById('idleWarningModal');
  if(!DEV_NO_TIMEOUT && idle > warnThreshold && idle < INACTIVITY_LIMIT_MS){
        if(!existing){
          const div=document.createElement('div');
          div.id='idleWarningModal';
          div.style.position='fixed';div.style.bottom='20px';div.style.right='20px';div.style.zIndex='20000';div.style.maxWidth='320px';
          div.innerHTML=`<div class="card border-warning shadow"><div class="card-body p-3"><h6 class="text-warning mb-2"><i class="bi bi-exclamation-triangle"></i> Session Expiring</h6><p class="small mb-3">You will be logged out soon due to inactivity. Click Continue to stay signed in.</p><div class="d-flex gap-2"><button class="btn btn-sm btn-primary" id="idleContinueBtn">Continue</button><button class="btn btn-sm btn-outline-secondary" id="idleDismissBtn">Dismiss</button></div></div></div>`;
          document.body.appendChild(div);
          div.querySelector('#idleContinueBtn').addEventListener('click', ()=>{ recordActivity(); maybeRefreshToken(); div.remove(); });
          div.querySelector('#idleDismissBtn').addEventListener('click', ()=>{ div.remove(); });
        }
      } else if(existing && idle <= warnThreshold){ existing.remove(); }
    } catch(e){ /* silent */ }
  }, 30000); // check every 30s

  // Expose debug info helper
  function debugInfo(){
    return {
      tokenPresent: !!getToken(),
      exp: parseInt(localStorage.getItem(EXP_KEY)||'0',10),
      nowSec: nowSec(),
      minutesLeft: (function(){ const exp=parseInt(localStorage.getItem(EXP_KEY)||'0',10); return exp? ((exp-nowSec())/60): null; })(),
      inactivityLimitMinutes: INACTIVITY_LIMIT_MS/60000,
      devNoTimeout: DEV_NO_TIMEOUT,
      lastActivityAgeSec: (Date.now()-lastActivity)/1000,
      refreshThresholdMin: typeof REFRESH_THRESHOLD_MIN!=='undefined'? REFRESH_THRESHOLD_MIN: undefined
    };
  }

  // Cross-tab session persistence
  const SESSION_UPDATE_KEY = 'auth_session_update';
  const LAST_ACTIVITY_KEY = 'auth_last_activity';

  // Function to broadcast session changes across tabs
  function broadcastSessionUpdate(action, data = {}) {
    try {
      const update = {
        action,
        timestamp: Date.now(),
        tabId: Math.random().toString(36).substr(2, 9),
        ...data
      };
      localStorage.setItem(SESSION_UPDATE_KEY, JSON.stringify(update));
      // Immediately remove to trigger storage event in other tabs
      setTimeout(() => localStorage.removeItem(SESSION_UPDATE_KEY), 100);
    } catch(e) {
      console.warn('Failed to broadcast session update:', e);
    }
  }

  // Function to update last activity across tabs
  function updateCrossTabActivity() {
    try {
      localStorage.setItem(LAST_ACTIVITY_KEY, Date.now().toString());
    } catch(e) {
      console.warn('Failed to update cross-tab activity:', e);
    }
  }

  // Listen for session updates from other tabs
  window.addEventListener('storage', function(e) {
    if (e.key === SESSION_UPDATE_KEY && e.newValue) {
      try {
        const update = JSON.parse(e.newValue);
        console.log('[auth] Received session update from another tab:', update.action);

        switch(update.action) {
          case 'login':
            // Another tab logged in, refresh our session state
            if (update.token && update.user) {
              localStorage.setItem(TOKEN_KEY, update.token);
              localStorage.setItem(USER_KEY, JSON.stringify(update.user));
              if (update.exp) localStorage.setItem(EXP_KEY, update.exp);
              // Update navbar display
              updateUserDisplayInNavbar();
              // Reset activity timer
              lastActivity = Date.now();
            }
            break;

          case 'logout':
            // Another tab logged out, clear our session
            localStorage.removeItem(TOKEN_KEY);
            localStorage.removeItem(USER_KEY);
            localStorage.removeItem(EXP_KEY);
            localStorage.removeItem('current_pos_session_id');
            localStorage.removeItem('selected_branch_id');
            // Redirect to login if not already there
            if (!window.location.pathname.includes('login.html')) {
              window.location.replace('/static/login.html');
            }
            break;

          case 'activity':
            // Another tab had activity, update our timer
            lastActivity = Math.max(lastActivity, update.timestamp);
            break;
        }
      } catch(err) {
        console.warn('Failed to process session update:', err);
      }
    }

    // Also listen for activity updates from other tabs
    if (e.key === LAST_ACTIVITY_KEY && e.newValue) {
      try {
        const otherActivity = parseInt(e.newValue, 10);
        lastActivity = Math.max(lastActivity, otherActivity);
      } catch(err) {
        console.warn('Failed to process activity update:', err);
      }
    }
  });

  // Override recordActivity to broadcast across tabs
  const originalRecordActivity = recordActivity;
  recordActivity = function() {
    originalRecordActivity();
    updateCrossTabActivity();
  };

  async function switchBranch(branch_id){
    if(!isAuthenticated()) throw new Error('Not authenticated');
    const res = await fetch('/api/v1/auth/switch-branch', { method:'POST', headers:{ 'Content-Type':'application/json', ...authHeader() }, body: JSON.stringify({ branch_id }) });
    if(!res.ok) { let msg='Branch switch failed'; try { const e=await res.json(); msg=e.detail||msg; } catch{} throw new Error(msg); }
    const data = await res.json();
    const payload = parseJwt(data.access_token);
    payload.role = data.role; payload.username = data.username; payload.branch_id = data.branch_id; payload.branch_code = data.branch_code;
    saveSession(data.access_token, payload);
    
    // Broadcast branch switch to other tabs
    broadcastSessionUpdate('login', {
      token: data.access_token,
      user: { id: payload.sub, role: payload.role, username: payload.username, branch_id: payload.branch_id, branch_code: payload.branch_code },
      exp: payload.exp
    });
    
    updateUserDisplayInNavbar();
    return data;
  }

  return { login, logout, getToken, getUser, isAuthenticated, authHeader, requireAuth, hasRole, redirectBasedOnRole, switchBranch, updateUserDisplayInNavbar, debugInfo };
})();

// Auto-attach to window
window.auth = auth;
// Provide a robust global logout() for inline onclick="logout()" usage
// Always assign to ensure stale definitions get overridden consistently
window.logout = function(reason){
  try {
    if (window.navbarLoader && typeof window.navbarLoader.handleLogout === 'function') {
      // Use enhanced confirm/logout flow when available
      window.navbarLoader.handleLogout();
      return;
    }
  } catch(_) {}
  // Fallback to direct auth logout
  try { auth.logout(reason); } catch(e) { try { window.location.replace('/static/login.html'); } catch(_) {} }
};
// Signal to other scripts (e.g., navbar-loader) that auth is ready
try { document.dispatchEvent(new Event('authReady')); } catch(_) {}
