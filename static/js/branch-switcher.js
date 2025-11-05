// Branch Switcher UI Component
// Shows a branch dropdown for super_admin/admin (and accountants with permission) and calls auth.switchBranch

(async function(){
  if(!window.auth || !auth.isAuthenticated()) return; 
  const user = auth.getUser();
  if(!user) return;
  const role = (user.role||'').toLowerCase();
  // Eligible roles: super_admin, admin, accountant (with permission check placeholder)
  if(!['super_admin','admin','accountant'].includes(role)) return;

  // Inject container into navbar right side if exists
  function mount(){
    const nav = document.querySelector('#navbar-container nav .navbar-nav');
    const targetParent = document.querySelector('#navbar-container nav .ms-auto, #navbar-container nav .d-flex, #navbar-container nav .navbar-nav:last-child') || nav;
    if(!targetParent) return false;
    if(document.getElementById('branchSwitcherContainer')) return true;
    const wrapper = document.createElement('li');
    wrapper.className='nav-item dropdown';
    wrapper.id='branchSwitcherContainer';
    wrapper.innerHTML = `
      <a class="nav-link dropdown-toggle modern-nav-link" href="#" role="button" data-bs-toggle="dropdown" aria-expanded="false">
        <i class="bi bi-diagram-3 me-1"></i><span id="activeBranchLabel">Branch</span>
      </a>
      <ul class="dropdown-menu modern-dropdown p-2" style="min-width:260px;max-height:320px;overflow:auto">
        <li class="px-2 mb-2">
          <input id="branchSearchInput" type="text" class="form-control form-control-sm" placeholder="Search branches..." />
        </li>
        <div id="branchListArea"><div class="text-muted small px-3 py-1">Loading branches...</div></div>
        <li><hr class="dropdown-divider"/></li>
        <li><button id="clearBranchBtn" class="dropdown-item text-danger">Global (All Branches)</button></li>
      </ul>`;
    targetParent.appendChild(wrapper);
    return true;
  }

  function updateActiveLabel(code){
    const el = document.getElementById('activeBranchLabel');
    if(el) el.textContent = code? `Branch: ${code}`: 'Branch: ALL';
  }

  async function fetchBranches(){
    try {
  const res = await fetch('/api/v1/branches/public');
      if(!res.ok) return [];
      const data = await res.json();
      return Array.isArray(data)? data: (data.data || []);
    } catch { return []; }
  }

  function renderList(branches){
    const area = document.getElementById('branchListArea');
    if(!area) return;
    if(!branches.length){ area.innerHTML='<div class="text-muted small px-3 py-1">No branches</div>'; return; }
    area.innerHTML = branches.map(b=>`<li><button class="dropdown-item branch-select-item" data-id="${b.id}" data-code="${b.code||b.name}"><i class="bi bi-building me-1"></i>${b.code||b.name}</button></li>`).join('');
  }

  function attachEvents(allBranches){
    // Filter
    const search = document.getElementById('branchSearchInput');
    if(search){
      search.addEventListener('input', e=>{
        const q = e.target.value.toLowerCase();
        const filtered = allBranches.filter(b=> (b.code||'').toLowerCase().includes(q) || (b.name||'').toLowerCase().includes(q));
        renderList(filtered);
      });
    }
    // Selection
    document.addEventListener('click', async (e)=>{
      const btn = e.target.closest('.branch-select-item');
      if(!btn) return;
      const id = btn.getAttribute('data-id');
      const code = btn.getAttribute('data-code');
      try {
        await auth.switchBranch(id);
        updateActiveLabel(code);
        // Refresh location if branch-scoped page
        if(window.location.pathname.includes('products') || window.location.pathname.includes('bank')){ window.location.reload(); }
      } catch(err){ console.error('Branch switch failed', err); }
    });
    const clearBtn = document.getElementById('clearBranchBtn');
    if(clearBtn){
      clearBtn.addEventListener('click', async ()=>{
        try { await auth.switchBranch(null); updateActiveLabel(null); window.location.reload(); } catch(err){ console.error(err); }
      });
    }
  }

  function init(){
    if(!mount()) { setTimeout(init,300); return; }
    const user = auth.getUser(); updateActiveLabel(user && user.branch_code);
    fetchBranches().then(branches=>{ renderList(branches); attachEvents(branches); });
  }

  // Wait for navbar
  document.addEventListener('navbarLoaded', ()=> init());
  if(window.navbarLoader && navbarLoader.isLoaded) init();
})();
