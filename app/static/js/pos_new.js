// New POS logic for CNPERP
// Contract:
// - Uses existing endpoints:
//   GET /api/v1/settings/
//   GET /api/v1/pos/sessions?status=open&branch_id=...
//   POST /api/v1/pos/sessions/open
//   GET /api/v1/pos/products?branch_id=...&search=...
//   GET /api/v1/pos/customers?branch_id=...&search=...
//   GET /api/v1/banking/accounts?branch_id=...
//   GET /api/v1/pos/branch-defaults/{branch_id}/card-bank
//   GET /api/v1/pos/defaults/card-bank
//   POST /api/v1/pos/sales
//   POST /api/v1/pos/sessions/close

(function(){
  // State
  let sessionId = null;
  let user = null;
  let branchId = null;
  let appSettings = { currency: 'BWP', currencySymbol: 'P', vatRate: 14.0, locale: 'en-BW', timezone: 'Africa/Gaborone', companyName: 'CNPERP' };
  let products = [];
  let customers = [];
  let cart = [];
  let selectedCustomer = null;
  let paymentMethod = 'cash';
  let bankAccounts = [];
  let defaultCardBankId = null;
  let recentReceipts = [];
  let receiptsModal = null;

  // Utils
  const authHeader = () => (window.auth && auth.isAuthenticated() ? auth.authHeader() : {});
  const getUser = () => (window.auth && auth.isAuthenticated() ? auth.getUser() : null);
  const getBranchId = () => {
    try { const u = getUser(); if (u && (u.branch_id || u.branchId)) return u.branch_id || u.branchId; } catch {}
    return localStorage.getItem('selected_branch_id') || localStorage.getItem('branch_id');
  };
  const fmt = (n) => {
    try { return new Intl.NumberFormat(appSettings.locale, { style:'currency', currency: appSettings.currency }).format(n); }
    catch { return (appSettings.currencySymbol || 'P') + Number(n || 0).toFixed(2); }
  };

  // Header
  function updateDateTime(){
    const now = new Date();
    const el = document.getElementById('dateTime'); if (el) el.textContent = now.toLocaleString();
  }

  async function resolveAndSetBranchDisplay(){
    try {
      const el = document.getElementById('branchName');
      if (!el) return;
      // Prefer explicit user metadata if available
      const u = getUser();
      const code = u?.branch_code || u?.branchCode;
      const name = u?.branch_name || u?.branchName;
      if (code || name){
        el.textContent = name ? (code ? `${code} - ${name}` : name) : code;
        return;
      }
      // Fallback: fetch public branches and resolve by ID
      if (!branchId) { el.textContent = 'Unknown'; return; }
      const r = await fetch('/api/v1/branches/public', { headers: authHeader() });
      if (r.ok){
        const list = await r.json();
        const br = Array.isArray(list) ? list.find(b => String(b.id)===String(branchId)) : null;
        if (br){
          const label = br.code ? (br.name ? `${br.code} - ${br.name}` : br.code) : (br.name || branchId);
          el.textContent = label;
          return;
        }
      }
      // Last resort: show truncated ID
      el.textContent = String(branchId || '').substring(0, 8) || 'Unknown';
    } catch {
      const el = document.getElementById('branchName');
      if (el) el.textContent = String(branchId || 'Unknown');
    }
  }

  async function ensureBranchContext(){
    if (branchId) return;
    try {
      const r = await fetch('/api/v1/branches/public', { headers: authHeader() });
      if (r.ok){
        const list = await r.json();
        const first = Array.isArray(list) && list.length ? list[0] : null;
        if (first && first.id){
          branchId = first.id;
          try { localStorage.setItem('selected_branch_id', branchId); } catch{}
        }
      }
    } catch {}
  }

  async function loadAppSettings(){
    try {
      const r = await fetch('/api/v1/settings/', { headers: authHeader() });
      if (r.ok) {
        const j = await r.json();
        const d = j.data || {};
        const cur = d.currency || {};
        appSettings = {
          currency: cur.currency || 'BWP',
          currencySymbol: cur.currency_symbol || 'P',
          vatRate: cur.vat_rate || 14.0,
          locale: cur.locale || 'en-BW',
          timezone: cur.timezone || 'Africa/Gaborone',
          companyName: (d.business && d.business.company_name) || 'CNPERP'
        };
      }
    } catch {}
    const brand = document.getElementById('brandName'); if (brand) brand.textContent = (appSettings.companyName || 'CNPERP') + ' POS';
  }

  // Session
  function showToast(message, variant='success'){
    try {
      const container = document.getElementById('toastContainer');
      if (!container) return;
      const id = 't_'+Date.now();
      const bg = variant==='success' ? 'bg-success' : (variant==='warning' ? 'bg-warning text-dark' : 'bg-danger');
      const el = document.createElement('div');
      el.className = `toast align-items-center text-white border-0 ${bg}`;
      el.id = id;
      el.role = 'alert'; el.ariaLive='assertive'; el.ariaAtomic='true';
      el.innerHTML = `<div class="d-flex"><div class="toast-body">${message}</div><button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button></div>`;
      container.appendChild(el);
      const t = new bootstrap.Toast(el, { delay: 2500 }); t.show();
      el.addEventListener('hidden.bs.toast', ()=> el.remove());
    } catch{}
  }

  async function ensureSession(){
    user = getUser();
    branchId = getBranchId();
    if (!branchId) { await ensureBranchContext(); }
    const cashierName = document.getElementById('cashierName');
    if (cashierName) cashierName.textContent = user ? (user.first_name ? `${user.first_name} ${user.last_name || ''}`.trim() : (user.username || 'User')) : 'Guest';
    await resolveAndSetBranchDisplay();

    // try reuse
    try {
      // localStorage cache first
      const cached = localStorage.getItem('current_pos_session_id');
      if (cached) { sessionId = cached; }

      const q = new URL('/api/v1/pos/sessions', window.location.origin);
      q.searchParams.set('status','open'); if (branchId) q.searchParams.set('branch_id', branchId);
      const r = await fetch(q.toString(), { headers: authHeader() });
      if (r.ok){
        const j = await r.json();
        const list = Array.isArray(j) ? j : (j.data || j.value || []);
        const mine = list.find && user ? list.find(s => String(s.user_id)===String(user.id)) : null;
        if (mine && mine.id) { sessionId = mine.id; localStorage.setItem('current_pos_session_id', sessionId); showToast('Reusing open POS session', 'success'); return; }
        // if we had a cached id but server doesn't list it (closed), clear it
        if (cached && (!mine || mine.id !== cached)) { localStorage.removeItem('current_pos_session_id'); }
      }
    } catch {}
    // open
    try {
      if (!user) { alert('Please login to open a POS session.'); return; }
      if (!branchId) { alert('Branch not resolved for POS session.'); return; }
      const payload = { user_id: user.id, branch_id: branchId, till_id: `TILL_${user.id}_${Date.now()}`, float_amount: 0 };
      const r2 = await fetch('/api/v1/pos/sessions/open', { method:'POST', headers:{ 'Content-Type':'application/json', ...authHeader() }, body: JSON.stringify(payload) });
      if (r2.ok) { const j2 = await r2.json(); sessionId = j2?.data?.session_id; if (sessionId) { localStorage.setItem('current_pos_session_id', sessionId); showToast('Session opened', 'success'); } }
      else {
        try { const err = await r2.json(); alert('Could not open POS session: ' + (err.detail || r2.statusText)); } catch { alert('Could not open POS session.'); }
      }
    } catch {}
  }

  // Products
  async function loadProducts(search){
    try {
      const url = new URL('/api/v1/pos/products', window.location.origin);
      if (branchId) url.searchParams.set('branch_id', branchId);
      if (search && String(search).trim()) url.searchParams.set('search', String(search).trim());
      const r = await fetch(url.toString(), { headers: authHeader() });
      if (r.ok){ const j = await r.json(); products = j.data || j.value || j || []; renderProducts(); }
    } catch {}
  }
  function renderProducts(){
    const grid = document.getElementById('productsGrid'); if (!grid) return; grid.innerHTML = '';
    if (!products.length){ grid.innerHTML = '<div class="text-center text-secondary py-5">No products</div>'; return; }
    products.forEach(p => {
      const col = document.createElement('div'); col.className = 'col-6 col-md-4 col-xl-3';
      const card = document.createElement('div'); card.className='product-card h-100';
      const name = document.createElement('div'); name.className='product-name'; name.textContent = p.name;
      const price = document.createElement('div'); price.className='product-price'; price.textContent = fmt(p.selling_price);
      const sku = document.createElement('div'); sku.className='product-sku'; sku.textContent = p.sku || '';
      const addBtn = document.createElement('button'); addBtn.className='btn btn-sm btn-outline-primary mt-2'; addBtn.innerHTML='<i class="bi bi-plus-circle me-1"></i>Add'; addBtn.onclick = (e)=>{ e.stopPropagation(); addToCart(p); };
      card.appendChild(name); card.appendChild(price); card.appendChild(sku); card.appendChild(addBtn);
      card.onclick = ()=> addToCart(p);
      col.appendChild(card); grid.appendChild(col);
    });
  }

  // Cart
  function addToCart(p){
    const idx = cart.findIndex(i=> i.id===p.id);
    if (idx>=0) cart[idx].quantity += 1; else cart.push({ id:p.id, name:p.name, unit_price:Number(p.selling_price), quantity:1, is_taxable:(p.is_taxable!==false) });
    renderCart(); recalcTotals();
  }
  function updateQty(i, d){ cart[i].quantity = Math.max(1, cart[i].quantity + d); renderCart(); recalcTotals(); }
  function removeItem(i){ cart.splice(i,1); renderCart(); recalcTotals(); }
  function renderCart(){
    const wrap = document.getElementById('cartList'); if (!wrap) return; wrap.innerHTML='';
    if (!cart.length){ wrap.innerHTML = '<div class="text-center text-secondary py-5">Cart empty</div>'; return; }
    cart.forEach((it,i)=>{
      const row = document.createElement('div'); row.className='bag-item d-flex align-items-center justify-content-between gap-2';
      const left = document.createElement('div'); left.innerHTML = '<div class="fw-semibold">'+ it.name +'</div><div class="text-secondary">'+ fmt(it.unit_price) +'</div>';
      const right = document.createElement('div'); right.className='d-flex align-items-center gap-2';
      const minus = document.createElement('button'); minus.className='qty-btn'; minus.textContent='-'; minus.onclick = ()=> updateQty(i,-1);
      const qty = document.createElement('span'); qty.className='px-2'; qty.textContent = String(it.quantity);
      const plus = document.createElement('button'); plus.className='qty-btn'; plus.textContent='+'; plus.onclick = ()=> updateQty(i,1);
      const total = document.createElement('div'); total.className='fw-semibold'; total.textContent = fmt(it.unit_price * it.quantity);
      const del = document.createElement('button'); del.className='btn btn-sm btn-outline-danger'; del.innerHTML='<i class="bi bi-trash"></i>'; del.onclick = ()=> removeItem(i);
      right.appendChild(minus); right.appendChild(qty); right.appendChild(plus); right.appendChild(total); right.appendChild(del);
      row.appendChild(left); row.appendChild(right); wrap.appendChild(row);
    });
  }

  function recalcTotals(){
    const vatRate = Number(appSettings.vatRate || 14.0);
    let subtotal=0, discount=0, vat=0;
    cart.forEach(it=>{ const line = it.unit_price * it.quantity; subtotal += line; if (it.is_taxable) vat += line * (vatRate/100); });
    const total = subtotal - discount + vat;
    const S = id=> document.getElementById(id);
    S('subtotal').textContent = fmt(subtotal);
    S('discount').textContent = fmt(discount);
    S('vat').textContent = fmt(vat);
    S('total').textContent = fmt(total);
    if (paymentMethod==='cash') updateChange();
  }

  function updateChange(){
    const total = parseFloat(document.getElementById('total').textContent.replace(/[^0-9.\-]/g,'')) || 0;
    const tendered = Number(document.getElementById('amountTendered').value || 0);
    const change = Math.max(0, tendered - total);
    document.getElementById('changeDue').textContent = fmt(change);
  }

  // Customers
  function openCustomerModal(){ new bootstrap.Modal(document.getElementById('customerModal')).show(); loadCustomers(); }
  async function loadCustomers(search){
    try {
      const url = new URL('/api/v1/pos/customers', window.location.origin);
      if (branchId) url.searchParams.set('branch_id', branchId);
      if (search && String(search).trim()) url.searchParams.set('search', String(search).trim());
      const r = await fetch(url.toString(), { headers: authHeader() });
      if (r.ok){ const j = await r.json(); customers = j.data || []; renderCustomers(); }
    } catch {}
  }
  function renderCustomers(){
    const box = document.getElementById('customerList'); const empty = document.getElementById('noCustomers');
    box.innerHTML=''; if (!customers.length){ empty.classList.remove('d-none'); return; } else { empty.classList.add('d-none'); }
    customers.forEach(c=>{
      const div = document.createElement('div'); div.className='border rounded p-2 mb-2';
      const title = document.createElement('div'); title.innerHTML = '<strong>'+ (c.name || 'Unnamed') +'</strong> <span class="ms-2 badge bg-secondary">'+ (c.customer_type || 'Retail') +'</span>';
      const det = document.createElement('div'); det.className='small text-secondary'; det.textContent = [c.email, c.phone].filter(Boolean).join(' • ');
      div.onclick = ()=> selectCustomer(c);
      div.appendChild(title); div.appendChild(det); box.appendChild(div);
    });
  }
  async function selectCustomer(c){
    selectedCustomer = c; document.getElementById('customerSummary').textContent = c.name || 'Customer';
    try { const r = await fetch(`/api/v1/sales/customers/${c.id}/balance`, { headers: authHeader() }); if (r.ok){ const j = await r.json(); document.getElementById('customerBalance').textContent = fmt(j.balance || 0); document.getElementById('customerBalanceWrap').classList.remove('d-none'); } } catch {}
    bootstrap.Modal.getInstance(document.getElementById('customerModal')).hide();
  }
  function useWalkIn(){ selectedCustomer = null; document.getElementById('customerSummary').textContent = 'Walk-in Customer'; document.getElementById('customerBalanceWrap').classList.add('d-none'); }

  // Banking defaults
  async function resolveCardDefaults(){
    defaultCardBankId = null;
    try {
      const br = branchId; if (!br) return;
      const r = await fetch(`/api/v1/pos/branch-defaults/${br}/card-bank`, { headers: authHeader() });
      if (r.ok){ const j = await r.json(); defaultCardBankId = j?.data?.default_card_bank_account_id || null; }
      if (!defaultCardBankId){ const g = await fetch('/api/v1/pos/defaults/card-bank', { headers: authHeader() }); if (g.ok){ const j2 = await g.json(); defaultCardBankId = j2?.data?.default_card_bank_account_id || null; } }
    } catch {}
  }
  async function loadBankAccounts(){
    try {
      const url = new URL('/api/v1/banking/accounts', window.location.origin); if (branchId) url.searchParams.set('branch_id', branchId);
      const r = await fetch(url.toString(), { headers: authHeader() }); const j = await r.json(); bankAccounts = j.data || [];
      const sel = document.getElementById('cardBankSelect'); sel.innerHTML='';
      if (!bankAccounts.length){ sel.innerHTML='<option value="">No bank accounts</option>'; return; }
      bankAccounts.forEach(a=>{ const opt = document.createElement('option'); opt.value=a.id; opt.textContent = a.name + (a.account_number ? ' ('+a.account_number+')' : ''); sel.appendChild(opt); });
      if (defaultCardBankId){ const exists = bankAccounts.some(a => String(a.id)===String(defaultCardBankId)); if (exists){ sel.value = defaultCardBankId; showDefaultBadge(defaultCardBankId); document.getElementById('cardControls').style.display = 'block'; } }
    } catch {}
  }
  function showDefaultBadge(id){
    const acc = bankAccounts.find(a => String(a.id)===String(id)); const badge = document.getElementById('defaultCardBadge');
    if (acc){ document.getElementById('defaultCardName').textContent = acc.name + (acc.account_number ? ' ('+acc.account_number+')' : ''); badge.classList.remove('d-none'); }
    else { badge.classList.add('d-none'); }
  }

  // Payment
  function setPayment(method){
    paymentMethod = method;
    const ids = ['pm-cash','pm-card','pm-credit']; ids.forEach(id => document.getElementById(id).classList.toggle('active', id==='pm-'+method));
    document.getElementById('cashControls').style.display = (method==='cash') ? 'flex' : 'none';
    document.getElementById('cardControls').style.display = (method==='card') ? 'block' : 'none';
    if (method==='card') showDefaultBadge(defaultCardBankId); else document.getElementById('defaultCardBadge').classList.add('d-none');
  }

  // Sale
  function cartToItems(){ return cart.map(it => ({ product_id: it.id, quantity: it.quantity, unit_price: it.unit_price, discount_amount: 0, is_taxable: it.is_taxable })); }
  async function confirmSale(){
    if (!sessionId){ alert('No open POS session.'); return; }
    if (!cart.length){ alert('Cart is empty.'); return; }
    const totalNum = parseFloat(document.getElementById('total').textContent.replace(/[^0-9.\-]/g,'')) || 0;
    const payload = {
      session_id: sessionId,
      items: cartToItems(),
      customer_id: selectedCustomer ? selectedCustomer.id : null,
      payment_method: paymentMethod,
      amount_tendered: paymentMethod==='cash' ? Number(document.getElementById('amountTendered').value || 0) : totalNum,
      vat_rate: Number(appSettings.vatRate || 14.0),
      currency: appSettings.currency,
      use_ifrs_posting: true
    };
    if (paymentMethod==='credit' && !selectedCustomer){ alert('Choose a customer for credit sales.'); return; }
    if (paymentMethod==='cash' && payload.amount_tendered < totalNum){ alert('Insufficient cash tendered.'); return; }
    if (paymentMethod==='card'){
      const chosen = document.getElementById('cardBankSelect').value || defaultCardBankId;
      if (chosen) payload.card_bank_account_id = chosen;
    }
    try {
      const r = await fetch('/api/v1/pos/sales', { method:'POST', headers:{ 'Content-Type':'application/json', ...authHeader() }, body: JSON.stringify(payload) });
      const j = await r.json();
      if (r.ok && j.success){
        // Try to open/print receipt if server provides one
        try {
          const receipt = j.data?.receipt;
          const url = receipt?.pdf_path || receipt?.pdf_url;
          if (url){
            window.open(url, '_blank');
          } else if (receipt?.html_content){
            const w = window.open('', '_blank');
            w.document.write(receipt.html_content); w.document.close(); w.print();
          }
        } catch{}
        // Reset UI
        cart = []; renderCart(); recalcTotals();
        document.getElementById('amountTendered').value='';
        document.getElementById('changeDue').textContent = fmt(0);
        document.getElementById('productSearch').value='';
        document.getElementById('barcodeScan').value='';
        document.getElementById('customerSummary').textContent = 'Walk-in Customer';
        document.getElementById('customerBalanceWrap').classList.add('d-none');
        selectedCustomer = null; paymentMethod = 'cash'; setPayment('cash');
        await loadRecentReceipts();
      } else {
        alert('Sale failed: ' + (j.detail || j.error || r.statusText));
      }
    } catch(e){ alert('Sale error: ' + e); }
  }

  // Misc
  function debounce(fn, ms){ let t; return function(...a){ clearTimeout(t); t = setTimeout(()=> fn.apply(this,a), ms); }; }
  async function testCardBank(){ if (paymentMethod!=='card'){ alert('Switch to Card to test.'); return; } const chosen = document.getElementById('cardBankSelect').value; if (chosen){ const acc = bankAccounts.find(a=> String(a.id)===String(chosen)); alert('Card will use: ' + (acc ? (acc.name + (acc.account_number? ' ('+acc.account_number+')' : '')) : ('Account ' + chosen))); return; } if (defaultCardBankId){ const acc2 = bankAccounts.find(a => String(a.id)===String(defaultCardBankId)); alert('Card will use default: ' + (acc2 ? (acc2.name + (acc2.account_number? ' ('+acc2.account_number+')' : '')) : ('Account ' + defaultCardBankId))); } else { alert('No default card bank configured. Set branch or global default in Settings.'); } }
  async function closeSession(){ if (!sessionId) return alert('No open session'); const cashSubmitted = prompt('Enter cash submitted amount', '0'); if (cashSubmitted==null) return; try{ const r = await fetch('/api/v1/pos/sessions/close', { method:'POST', headers:{ 'Content-Type':'application/json', ...authHeader() }, body: JSON.stringify({ session_id: sessionId, cash_submitted: Number(cashSubmitted) }) }); const j = await r.json(); if (r.ok && j.success){ alert('Session closed.'); sessionId = null; } else alert('Close failed.'); } catch(e){ alert('Close error: ' + e); } }

  // Receipt history
  async function ensureReceiptModal(){
    if (!receiptsModal){
      const el = document.getElementById('recentReceiptsModal');
      if (el){
        receiptsModal = new bootstrap.Modal(el);
      }
    }
    return receiptsModal;
  }

  function updateReceiptSummary(){
    const el = document.getElementById('recentReceiptsSummary');
    if (!el) return;
    if (!recentReceipts.length){
      el.textContent = 'No receipts recorded yet';
      return;
    }
    const printed = recentReceipts.filter(r => r.printed).length;
    const latest = recentReceipts[0];
    let dateLabel = '';
    if (latest?.created_at){
      const dt = new Date(latest.created_at);
      if (!Number.isNaN(dt.valueOf())){
        dateLabel = dt.toLocaleString();
      }
    }
    el.textContent = `${recentReceipts.length} receipt${recentReceipts.length === 1 ? '' : 's'} • ${printed} printed${dateLabel ? ` • latest ${dateLabel}` : ''}`;
  }

  function renderRecentReceipts(showError){
    const body = document.getElementById('recentReceiptsBody');
    const empty = document.getElementById('recentReceiptsEmpty');
    const wrap = document.getElementById('recentReceiptsTableWrap');
    if (!body) return;

    if (!Array.isArray(recentReceipts) || recentReceipts.length === 0){
      body.innerHTML = '';
      if (wrap) wrap.style.display = 'none';
      if (empty){
        empty.classList.remove('d-none');
        if (showError){
          const msg = empty.querySelector('div.text-secondary');
          if (msg) msg.textContent = 'Unable to load receipts right now';
        }
      }
      updateReceiptSummary();
      return;
    }

    if (wrap) wrap.style.display = 'block';
    if (empty) empty.classList.add('d-none');

    body.innerHTML = recentReceipts.map((receipt)=>{
      const created = receipt.created_at ? new Date(receipt.created_at).toLocaleString() : '-';
      const amount = fmt(receipt.amount || 0);
      const source = receipt.sale_id ? `Sale ${String(receipt.sale_id).slice(0,8)}…` : (receipt.invoice_id ? `Invoice ${String(receipt.invoice_id).slice(0,8)}…` : '-');
      const printedClass = receipt.printed ? 'bg-success' : 'bg-warning text-dark';
      const printedLabel = receipt.printed ? 'Printed' : 'Not Printed';
      const paymentLabel = receipt.payment_method ? receipt.payment_method.toUpperCase() : '';
      return `
        <tr data-id="${receipt.id}">
          <td>
            <div class="fw-semibold">${receipt.receipt_number}</div>
            ${paymentLabel ? `<div class="text-secondary small">${paymentLabel}</div>` : ''}
          </td>
          <td>${created}</td>
          <td>${amount}</td>
          <td>${source}</td>
          <td><span class="badge ${printedClass}">${printedLabel}</span>${receipt.print_count ? `<span class="ms-1 text-secondary small">(${receipt.print_count})</span>` : ''}</td>
          <td>
            <div class="btn-group btn-group-sm">
              <button type="button" class="btn btn-outline-light receipt-preview" data-id="${receipt.id}" title="Preview"><i class="bi bi-eye"></i></button>
              <button type="button" class="btn btn-outline-success receipt-print" data-id="${receipt.id}" title="Print"><i class="bi bi-printer"></i></button>
              <button type="button" class="btn btn-outline-info receipt-download" data-id="${receipt.id}" title="Open PDF"><i class="bi bi-file-earmark-pdf"></i></button>
            </div>
          </td>
        </tr>
      `;
    }).join('');

    body.querySelectorAll('.receipt-preview').forEach(btn => {
      btn.onclick = () => previewExistingReceipt(btn.dataset.id);
    });
    body.querySelectorAll('.receipt-print').forEach(btn => {
      btn.onclick = () => printExistingReceipt(btn.dataset.id);
    });
    body.querySelectorAll('.receipt-download').forEach(btn => {
      btn.onclick = () => openReceiptPdf(btn.dataset.id);
    });

    updateReceiptSummary();
  }

  async function fetchReceiptById(id){
    const resp = await fetch(`/api/v1/receipts/${id}`, { headers: authHeader() });
    if (!resp.ok){
      throw new Error('Receipt not found');
    }
    return resp.json();
  }

  async function loadRecentReceipts(){
    const loading = document.getElementById('recentReceiptsLoading');
    if (loading) loading.classList.remove('d-none');
    try {
      if (!branchId) await ensureBranchContext();
      const limitSelect = document.getElementById('recentReceiptsLimit');
      const limit = limitSelect ? Number(limitSelect.value || 20) : 20;
      const params = new URLSearchParams({ limit: String(limit) });
      if (branchId) params.set('branch_id', branchId);
      const resp = await fetch(`/api/v1/receipts/recent?${params.toString()}`, { headers: authHeader() });
      if (!resp.ok){
        recentReceipts = [];
        renderRecentReceipts(true);
        if (resp.status === 401) return;
        throw new Error('Failed to fetch receipts');
      }
      recentReceipts = await resp.json();
      renderRecentReceipts(false);
    } catch(err){
      console.error('Error loading recent receipts', err);
      showToast('Unable to load receipts', 'danger');
      recentReceipts = [];
      renderRecentReceipts(true);
    } finally {
      if (loading) loading.classList.add('d-none');
    }
  }

  async function previewExistingReceipt(id){
    try {
      const receipt = await fetchReceiptById(id);
      const previewHtml = receipt.html_content || '<p style="font-family: monospace;">Receipt preview is unavailable.</p>';
      const win = window.open('', '_blank');
      if (!win) return;
      win.document.write(previewHtml);
      win.document.close();
    } catch(err){
      console.error('Preview receipt error', err);
      showToast('Could not preview receipt', 'danger');
    }
  }

  async function printExistingReceipt(id){
    try {
      const receipt = await fetchReceiptById(id);
      const html = receipt.html_content || '<p style="font-family: monospace;">Receipt content unavailable.</p>';
      const win = window.open('', '_blank');
      if (!win) throw new Error('Popup blocked');
      win.document.write(html);
      win.document.close();
      setTimeout(()=>{ try { win.print(); } catch{} }, 200);
      await fetch(`/api/v1/receipts/${id}/print`, { method: 'POST', headers: authHeader() });
      showToast('Receipt sent to printer', 'success');
      await loadRecentReceipts();
    } catch(err){
      console.error('Print receipt error', err);
      showToast('Could not print receipt', 'danger');
    }
  }

  async function openReceiptPdf(id){
    try {
      let receipt = recentReceipts.find(r => r.id === id);
      if (!receipt){
        receipt = await fetchReceiptById(id);
      }
      if (receipt?.pdf_path){
        const url = receipt.pdf_path.startsWith('http') ? receipt.pdf_path : new URL(receipt.pdf_path, window.location.origin).href;
        window.open(url, '_blank');
      } else {
        await previewExistingReceipt(id);
      }
    } catch(err){
      console.error('Open receipt PDF error', err);
      showToast('Could not open receipt file', 'danger');
    }
  }

  async function openRecentReceiptsModal(){
    const modal = await ensureReceiptModal();
    if (!modal) return;
    modal.show();
    await loadRecentReceipts();
  }

  // Wire up
  document.addEventListener('DOMContentLoaded', async () => {
    // Require authentication for POS
    try { if (window.auth && typeof auth.requireAuth==='function') { const ok = auth.requireAuth(); if (ok===false) return; } } catch{}
    await loadAppSettings(); updateDateTime(); setInterval(updateDateTime, 1000);
    await ensureSession(); await resolveCardDefaults(); await loadBankAccounts(); await loadProducts();
    await loadRecentReceipts();

    // Inputs
    document.getElementById('productSearch').addEventListener('input', debounce((e)=> loadProducts(e.target.value), 250));
    document.getElementById('clearProductSearch').onclick = ()=> { document.getElementById('productSearch').value=''; loadProducts(''); };
    document.getElementById('chooseCustomerBtn').onclick = openCustomerModal;
    document.getElementById('useWalkIn').onclick = ()=> { useWalkIn(); bootstrap.Modal.getInstance(document.getElementById('customerModal')).hide(); };
    document.getElementById('customerSearch').addEventListener('input', debounce((e)=> loadCustomers(e.target.value), 300));
    document.getElementById('clearCustomerSearch').onclick = ()=> { document.getElementById('customerSearch').value=''; loadCustomers(''); };

    // Payments
    document.getElementById('pm-cash').onclick = ()=> setPayment('cash');
    document.getElementById('pm-card').onclick = ()=> setPayment('card');
    document.getElementById('pm-credit').onclick = ()=> setPayment('credit');
    document.getElementById('amountTendered').addEventListener('input', updateChange);
    document.getElementById('reloadBanks').onclick = async ()=> { await resolveCardDefaults(); await loadBankAccounts(); };
    document.getElementById('testCardBtn').onclick = testCardBank;
    document.getElementById('confirmBtn').onclick = confirmSale;
    document.getElementById('closeSessionBtn').onclick = closeSession;
    const refreshReceiptsBtn = document.getElementById('refreshReceiptsList');
    if (refreshReceiptsBtn){ refreshReceiptsBtn.onclick = ()=> loadRecentReceipts(); }
    const limitSelect = document.getElementById('recentReceiptsLimit');
    if (limitSelect){ limitSelect.addEventListener('change', ()=> loadRecentReceipts()); }

    // Auto-scan add (Enter triggers add by barcode/sku)
    const scan = document.getElementById('barcodeScan');
    if (scan){
      try { scan.focus(); } catch{}
      scan.addEventListener('keypress', (e)=>{
        if (e.key === 'Enter'){
          const code = String(scan.value || '').trim();
          if (!code) return;
          const match = products.find(p => String(p.sku||'').toLowerCase()===code.toLowerCase() || String(p.barcode||'').toLowerCase()===code.toLowerCase());
          if (match){ addToCart(match); recalcTotals(); scan.value=''; }
          else { // Try fetch with search to pull it in
            loadProducts(code).then(()=>{
              const m2 = products.find(p => String(p.sku||'').toLowerCase()===code.toLowerCase() || String(p.barcode||'').toLowerCase()===code.toLowerCase());
              if (m2){ addToCart(m2); recalcTotals(); scan.value=''; }
            });
          }
        }
      });
    }
  });
})();
