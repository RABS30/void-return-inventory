// API base URL
const API_BASE = '/api';

let allTransactions = [];
let filteredTransactions = [];

// Load transactions from server
async function loadTransactions() {
  try {
    const response = await fetch(`${API_BASE}/transactions`);
    const result = await response.json();
    
    if (result.success) {
      allTransactions = result.data;
      filteredTransactions = [...allTransactions];
      renderTable();
    }
  } catch (error) {
    console.error('Error loading transactions:', error);
    showToast('Gagal memuat data', 'error');
  }
}

// Render table
function renderTable() {
  const tableBody = document.getElementById('tableBody');
  const mobileList = document.getElementById('mobileList');
  
  if (filteredTransactions.length === 0) {
    tableBody.innerHTML = '<tr><td colspan="9" class="px-4 py-8 text-center text-slate-500">Tidak ada data</td></tr>';
    mobileList.innerHTML = '<div class="p-8 text-center text-slate-500">Tidak ada data</div>';
    updateStats();
    return;
  }
  
  // Desktop table
  tableBody.innerHTML = filteredTransactions.map(t => {
    const date = new Date(t.tanggal);
    const dateStr = date.toLocaleDateString('id-ID', { day: 'numeric', month: 'short' });
    
    return `
      <tr class="border-t border-slate-100 hover:bg-slate-50 dark:hover:bg-slate-800">
        <td class="px-4 py-3 text-xs text-slate-500">${dateStr}</td>
        <td class="px-4 py-3 text-xs font-semibold">${t.outlet}</td>
        <td class="px-4 py-3">
          <div class="font-semibold">${t.namaBarang}</div>
          <div class="text-xs font-mono text-slate-500">${t.barcode}</div>
        </td>
        <td class="px-4 py-3 text-center font-semibold">${t.quantity}</td>
        <td class="px-4 py-3">
          ${t.tipe === 'void' 
            ? '<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg text-[11px] font-extrabold bg-rose-100 text-rose-800"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" class="w-3 h-3"><circle cx="12" cy="12" r="8"/><path d="M6.8 6.8l10.4 10.4"/></svg>VOID</span>'
            : '<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg text-[11px] font-extrabold bg-emerald-100 text-emerald-800"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" class="w-3 h-3"><path d="M9.5 5.5L5 10l4.5 4.5"/><path d="M5 10h9a5 5 0 0 1 0 10h-2.5"/></svg>RETURN</span>'
          }
        </td>
        <td class="px-4 py-3 text-xs">${t.kasir}</td>
        <td class="px-4 py-3 text-xs">${t.otoritas}</td>
        <td class="px-4 py-3 text-xs">${t.alasan}</td>
        <td class="px-4 py-3 text-right">
          <button onclick="deleteTransaction(${t.id})" class="text-xs font-semibold text-rose-600 hover:underline inline-flex items-center gap-1">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" class="w-3 h-3">
              <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/>
            </svg>
            Hapus
          </button>
        </td>
      </tr>
    `;
  }).join('');
  
  // Mobile list
  mobileList.innerHTML = filteredTransactions.map(t => {
    const date = new Date(t.tanggal);
    const dateStr = date.toLocaleDateString('id-ID', { day: 'numeric', month: 'short' });
    
    return `
      <div class="p-4 border-b border-slate-100 last:border-0">
        <div class="flex items-start justify-between gap-2">
          <div class="min-w-0">
            <p class="font-semibold truncate">${t.namaBarang}</p>
            <p class="text-xs font-mono text-slate-500">${t.barcode}</p>
          </div>
          ${t.tipe === 'void' 
            ? '<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg text-[11px] font-extrabold bg-rose-100 text-rose-800 shrink-0"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" class="w-3 h-3"><circle cx="12" cy="12" r="8"/><path d="M6.8 6.8l10.4 10.4"/></svg>VOID</span>'
            : '<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg text-[11px] font-extrabold bg-emerald-100 text-emerald-800 shrink-0"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" class="w-3 h-3"><path d="M9.5 5.5L5 10l4.5 4.5"/><path d="M5 10h9a5 5 0 0 1 0 10h-2.5"/></svg>RETURN</span>'
          }
        </div>
        <div class="flex flex-wrap items-center gap-x-3 gap-y-1 mt-2 text-xs text-slate-500">
          <span>${dateStr}</span>
          <span>${t.outlet}</span>
          <span>Qty ${t.quantity}</span>
        </div>
        <p class="text-xs text-slate-600 dark:text-slate-400 mt-2">${t.alasan}</p>
        <div class="flex items-center justify-end gap-2 mt-3 pt-3 border-t border-dashed border-slate-100">
          <button onclick="deleteTransaction(${t.id})" class="text-xs font-semibold text-rose-600 inline-flex items-center gap-1">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" class="w-3 h-3">
              <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/>
            </svg>
            Hapus
          </button>
        </div>
      </div>
    `;
  }).join('');
  
  updateStats();
}

// Update statistics
function updateStats() {
  const totalEntries = filteredTransactions.length;
  const totalQty = filteredTransactions.reduce((sum, t) => sum + parseInt(t.quantity), 0);
  
  document.getElementById('totalEntries').textContent = totalEntries;
  document.getElementById('totalQty').textContent = totalQty;
}

// Filter by jenis
document.getElementById('filterJenis').addEventListener('change', function() {
  const filter = this.value;
  
  if (filter === 'all') {
    filteredTransactions = [...allTransactions];
  } else {
    filteredTransactions = allTransactions.filter(t => t.tipe === filter);
  }
  
  renderTable();
});

// Search
document.getElementById('searchInput').addEventListener('input', function() {
  const query = this.value.toLowerCase().trim();
  
  if (query === '') {
    filteredTransactions = [...allTransactions];
  } else {
    filteredTransactions = allTransactions.filter(t => 
      t.barcode.toLowerCase().includes(query) ||
      t.namaBarang.toLowerCase().includes(query) ||
      t.alasan.toLowerCase().includes(query) ||
      t.kasir.toLowerCase().includes(query) ||
      t.outlet.toLowerCase().includes(query)
    );
  }
  
  renderTable();
});

// Delete transaction
async function deleteTransaction(id) {
  if (!confirm('Hapus transaksi ini?')) return;
  
  try {
    const response = await fetch(`${API_BASE}/transaction/delete/${id}`, {
      method: 'DELETE'
    });
    
    const result = await response.json();
    
    if (result.success) {
      // Reload data from server
      await loadTransactions();
      showToast('Transaksi berhasil dihapus', 'success');
    } else {
      showToast('Gagal menghapus: ' + result.error, 'error');
    }
  } catch (error) {
    showToast('Error: ' + error.message, 'error');
  }
}

// Export CSV
function exportToCSV(data, filename, headers) {
  const csvContent = [
    headers.join(','),
    ...data.map(row => row.map(field => `"${field}"`).join(','))
  ].join('\n');
  
  const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.click();
}

// Export Void
document.getElementById('btnExportVoid').addEventListener('click', function() {
  const voidData = allTransactions.filter(t => t.tipe === 'void');
  
  if (voidData.length === 0) {
    showToast('Tidak ada data Void untuk diekspor', 'error');
    return;
  }
  
  const headers = ['NO', 'OUTLET', 'TANGGAL', 'NAMA PRODUK', 'BARCODE', 'QTY', 'KASIR', 'OTORITAS', 'ALASAN VOID'];
  const rows = voidData.map((t, idx) => [
    idx + 1,
    t.outlet,
    t.tanggal,
    t.namaBarang,
    t.barcode,
    t.quantity,
    t.kasir,
    t.otoritas,
    t.alasan
  ]);
  
  const filename = `void_${new Date().toISOString().split('T')[0]}.csv`;
  exportToCSV(rows, filename, headers);
  showToast('Export Void berhasil!', 'success');
});

// Export Return
document.getElementById('btnExportReturn').addEventListener('click', function() {
  const returnData = allTransactions.filter(t => t.tipe === 'return');
  
  if (returnData.length === 0) {
    showToast('Tidak ada data Return untuk diekspor', 'error');
    return;
  }
  
  const headers = ['TANGGAL', 'OUTLET', 'NAMA KASIR', 'NO.TRANS', 'NAMA PRODUK', 'BARCODE', 'QTY', 'H.JUAL', 'OTORITAS', 'ALASAN REFUND'];
  const rows = returnData.map(t => [
    t.tanggal,
    t.outlet,
    t.kasir,
    t.notrans,
    t.namaBarang,
    t.barcode,
    t.quantity,
    t.hjual,
    t.otoritas,
    t.alasan
  ]);
  
  const filename = `return_${new Date().toISOString().split('T')[0]}.csv`;
  exportToCSV(rows, filename, headers);
  showToast('Export Return berhasil!', 'success');
});

// Toast notification
function showToast(message, type) {
  const toast = document.getElementById('toast');
  toast.textContent = message;
  toast.className = `fixed z-50 top-4 right-4 px-4 py-3 rounded-xl text-sm font-semibold shadow-lg ${
    type === 'success' ? 'bg-emerald-600 text-white' : 'bg-rose-600 text-white'
  }`;
  toast.classList.remove('hidden');
  
  setTimeout(() => {
    toast.classList.add('hidden');
  }, 3000);
}

// Initial load
loadTransactions();
