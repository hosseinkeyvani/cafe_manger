// Simple table filter (RTL-friendly)
function filterTable(inputId, tableId) {
  const q = (document.getElementById(inputId).value || "").toLowerCase().trim();
  const table = document.getElementById(tableId);
  if (!table) return;

  const rows = table.querySelectorAll("tbody tr");
  rows.forEach((tr) => {
    const text = tr.innerText.toLowerCase();
    tr.style.display = text.includes(q) ? "" : "none";
  });
}

function fmtMoney(n){
  try{
    const v = parseInt(n, 10);
    return v.toLocaleString('fa-IR');
  }catch(e){
    return n;
  }
}

function computePreview(itemSelectEl, qtyEl, outEl){
  if(!itemSelectEl || !qtyEl || !outEl) return;
  const opt = itemSelectEl.options[itemSelectEl.selectedIndex];
  const price = opt ? parseInt(opt.dataset.price || "0", 10) : 0;
  const qty = parseInt(qtyEl.value || "1", 10) || 1;
  const total = price * qty;
  outEl.value = total ? (fmtMoney(total) + " تومان") : "—";
}

let __deleteCfg = null;

function openConfirmDelete(kind, id, label){
  if(!__deleteCfg) return;
  const modalEl = document.getElementById('confirmDeleteModal');
  const form = document.getElementById('confirmDeleteForm');
  const text = document.getElementById('confirmDeleteText');

  let action = "";
  if(kind === 'menu') action = `${__deleteCfg.menuDeleteBase}/${id}/delete`;
  if(kind === 'customer') action = `${__deleteCfg.customerDeleteBase}/${id}/delete`;
  if(kind === 'order') action = `${__deleteCfg.orderDeleteBase}/${id}/delete`;

  form.action = action;
  text.textContent = `حذف "${label}"`;

  const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
  modal.show();
}

function setupDashboard(cfg){
  __deleteCfg = cfg;

  // MENU EDIT modal
  const menuEditModal = document.getElementById('menuEditModal');
  if(menuEditModal){
    menuEditModal.addEventListener('show.bs.modal', (ev) => {
      const btn = ev.relatedTarget;
      if(!btn) return;
      const id = btn.getAttribute('data-id');
      document.getElementById('menuEditId').value = id;
      document.getElementById('menuEditName').value = btn.getAttribute('data-name') || '';
      document.getElementById('menuEditCategory').value = btn.getAttribute('data-category') || 'عمومی';
      document.getElementById('menuEditPrice').value = btn.getAttribute('data-price') || '0';
      const available = btn.getAttribute('data-available') === '1';
      document.getElementById('menuEditAvailable').checked = available;

      const form = document.getElementById('menuEditForm');
      form.action = `${cfg.menuUpdateBase}/${id}/update`;
    });
  }

  // CUSTOMER EDIT modal
  const customerEditModal = document.getElementById('customerEditModal');
  if(customerEditModal){
    customerEditModal.addEventListener('show.bs.modal', (ev) => {
      const btn = ev.relatedTarget;
      if(!btn) return;
      const id = btn.getAttribute('data-id');
      document.getElementById('customerEditId').value = id;
      document.getElementById('customerEditFirst').value = btn.getAttribute('data-first') || '';
      document.getElementById('customerEditLast').value = btn.getAttribute('data-last') || '';
      document.getElementById('customerEditPhone').value = btn.getAttribute('data-phone') || '';

      const form = document.getElementById('customerEditForm');
      form.action = `${cfg.customerUpdateBase}/${id}/update`;
    });
  }

  // ORDER create preview
  const cItem = document.getElementById('orderCreateItem');
  const cQty = document.getElementById('orderCreateQty');
  const cOut = document.getElementById('orderCreateTotal');
  if(cItem && cQty && cOut){
    const update = () => computePreview(cItem, cQty, cOut);
    cItem.addEventListener('change', update);
    cQty.addEventListener('input', update);
  }

  // ORDER edit modal + preview
  const orderEditModal = document.getElementById('orderEditModal');
  if(orderEditModal){
    orderEditModal.addEventListener('show.bs.modal', (ev) => {
      const btn = ev.relatedTarget;
      if(!btn) return;

      const id = btn.getAttribute('data-id');
      const user = btn.getAttribute('data-user');
      const item = btn.getAttribute('data-item');
      const qty = btn.getAttribute('data-qty');
      const status = btn.getAttribute('data-status');
      const notes = btn.getAttribute('data-notes') || '';

      document.getElementById('orderEditId').value = id;
      document.getElementById('orderEditUser').value = user;
      document.getElementById('orderEditItem').value = item;
      document.getElementById('orderEditQty').value = qty || '1';
      document.getElementById('orderEditStatus').value = status || 'در انتظار';
      document.getElementById('orderEditNotes').value = notes;

      const form = document.getElementById('orderEditForm');
      form.action = `${cfg.orderUpdateBase}/${id}/update`;

      // preview
      const eItem = document.getElementById('orderEditItem');
      const eQty = document.getElementById('orderEditQty');
      const eOut = document.getElementById('orderEditTotal');
      computePreview(eItem, eQty, eOut);
    });

    // update preview while editing
    const eItem = document.getElementById('orderEditItem');
    const eQty = document.getElementById('orderEditQty');
    const eOut = document.getElementById('orderEditTotal');
    if(eItem && eQty && eOut){
      const update = () => computePreview(eItem, eQty, eOut);
      eItem.addEventListener('change', update);
      eQty.addEventListener('input', update);
    }
  }
}
