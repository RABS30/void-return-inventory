// Dummy data transaksi
const dummyTransactions = [
  {
    id: 1,
    tanggal: '2026-09-21',
    outlet: 'BT5',
    barcode: '8992388101010',
    namaBarang: 'Indomie Goreng 85g',
    quantity: 2,
    tipe: 'void',
    kasir: 'Mawar Melati',
    otoritas: 'Raflesia Arnoldi',
    alasan: 'Kasir salah input jumlah'
  },
  {
    id: 2,
    tanggal: '2026-09-21',
    outlet: 'BT3',
    barcode: '8993675610019',
    namaBarang: 'Aqua Botol 600ml',
    quantity: 1,
    tipe: 'return',
    kasir: 'Tulip ',
    otoritas: 'Patrick',
    alasan: 'Kemasan bocor',
    notrans: 'TRX20260921001',
    hjual: 4000
  },
  {
    id: 3,
    tanggal: '2026-09-20',
    outlet: 'BT7',
    barcode: '8996001600016',
    namaBarang: 'Teh Pucuk Harum 350ml',
    quantity: 3,
    tipe: 'void',
    kasir: 'Anggrek',
    otoritas: 'Gabby',
    alasan: 'Pembeli batal beli'
  },
  {
    id: 4,
    tanggal: '2026-09-19',
    outlet: 'BT12',
    barcode: '8998866123456',
    namaBarang: 'Chitato Sapi Panggang 68g',
    quantity: 1,
    tipe: 'return',
    kasir: 'Jasmine',
    otoritas: 'Enzo',
    alasan: 'Salah rasa, ditukar',
    notrans: 'TRX20260919045',
    hjual: 8500
  },
  {
    id: 5,
    tanggal: '2026-09-20',
    outlet: 'BT2',
    barcode: '8991001234567',
    namaBarang: 'Mie Sedaap Goreng 85g',
    quantity: 5,
    tipe: 'void',
    kasir: 'Red Rose',
    otoritas: 'Raul',
    alasan: 'Sistem error saat transaksi'
  },
  {
    id: 6,
    tanggal: '2026-09-18',
    outlet: 'BT15',
    barcode: '8992761111111',
    namaBarang: 'Ultra Milk Coklat 200ml',
    quantity: 2,
    tipe: 'return',
    kasir: 'Pablo',
    otoritas: 'Miguel',
    alasan: 'Produk mendekati kadaluarsa',
    notrans: 'TRX20260918012',
    hjual: 5500
  }
];

// Load transactions
function loadTransactions() {
  const stored = localStorage.getItem('transactions');
  return stored ? JSON.parse(stored) : dummyTransactions;
}

const transactions = loadTransactions();

// Calculate statistics
function calculateStats() {
  const today = new Date().toISOString().split('T')[0];
  
  const voidTransactions = transactions.filter(t => t.tipe === 'void');
  const returnTransactions = transactions.filter(t => t.tipe === 'return');
  const todayTransactions = transactions.filter(t => t.tanggal === today);
  
  const totalQty = transactions.reduce((sum, t) => sum + parseInt(t.quantity), 0);
  const voidQty = voidTransactions.reduce((sum, t) => sum + parseInt(t.quantity), 0);
  const returnQty = returnTransactions.reduce((sum, t) => sum + parseInt(t.quantity), 0);
  const todayQty = todayTransactions.reduce((sum, t) => sum + parseInt(t.quantity), 0);
  
  return {
    total: transactions.length,
    totalQty,
    void: voidTransactions.length,
    voidQty,
    return: returnTransactions.length,
    returnQty,
    today: todayTransactions.length,
    todayQty
  };
}

// Update stat cards
function updateStats() {
  const stats = calculateStats();
  
  document.getElementById('statTotal').textContent = stats.total;
  document.getElementById('statTotalQty').textContent = stats.totalQty;
  document.getElementById('statVoid').textContent = stats.void;
  document.getElementById('statVoidQty').textContent = stats.voidQty;
  document.getElementById('statReturn').textContent = stats.return;
  document.getElementById('statReturnQty').textContent = stats.returnQty;
  document.getElementById('statToday').textContent = stats.today;
  document.getElementById('statTodayQty').textContent = stats.todayQty;
  document.getElementById('linkTotal').textContent = stats.total;
  
  // Update chart
  document.getElementById('chartVoid').textContent = stats.void;
  document.getElementById('chartReturn').textContent = stats.return;
  document.getElementById('chartTotal').textContent = stats.total;
  
  // Update bar chart
  const voidPercent = stats.total > 0 ? (stats.void / stats.total * 100) : 50;
  const returnPercent = stats.total > 0 ? (stats.return / stats.total * 100) : 50;
  document.getElementById('barVoid').style.width = voidPercent + '%';
  document.getElementById('barReturn').style.width = returnPercent + '%';
}

// Top products
function updateTopProducts() {
  const productCount = {};
  
  transactions.forEach(t => {
    if (!productCount[t.barcode]) {
      productCount[t.barcode] = {
        nama: t.namaBarang,
        qty: 0
      };
    }
    productCount[t.barcode].qty += parseInt(t.quantity);
  });
  
  const sorted = Object.values(productCount).sort((a, b) => b.qty - a.qty).slice(0, 3);
  
  const container = document.getElementById('topProducts');
  
  if (sorted.length === 0) {
    container.innerHTML = '<p class="text-sm text-slate-500">Belum ada data</p>';
    return;
  }
  
  const maxQty = sorted[0].qty;
  
  container.innerHTML = sorted.map(p => `
    <div>
      <div class="flex justify-between text-xs font-semibold mb-1">
        <span>${p.nama}</span>
        <span class="text-slate-500">${p.qty} pcs</span>
      </div>
      <div class="h-2.5 rounded-full bg-slate-100 overflow-hidden">
        <div class="h-full bg-brand-500" style="width:${(p.qty / maxQty * 100)}%"></div>
      </div>
    </div>
  `).join('');
}

// Recent entries
function updateRecentEntries() {
  const recent = transactions.slice(0, 5);
  const tbody = document.getElementById('recentTable');
  
  if (recent.length === 0) {
    tbody.innerHTML = '<tr><td colspan="5" class="px-4 py-8 text-center text-slate-500">Belum ada data</td></tr>';
    return;
  }
  
  tbody.innerHTML = recent.map(t => {
    const date = new Date(t.tanggal);
    const dateStr = date.toLocaleDateString('id-ID', { day: 'numeric', month: 'short' });
    
    return `
      <tr class="border-t border-slate-100 hover:bg-slate-50 dark:hover:bg-slate-800">
        <td class="px-4 py-3 text-xs text-slate-500">${dateStr}</td>
        <td class="px-4 py-3 text-xs font-semibold">${t.outlet}</td>
        <td class="px-4 py-3">
          <div class="font-semibold">${t.namaBarang}</div>
        </td>
        <td class="px-4 py-3 text-center font-semibold">${t.quantity}</td>
        <td class="px-4 py-3">
          ${t.tipe === 'void' 
            ? '<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg text-[11px] font-extrabold bg-rose-100 text-rose-800"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" class="w-3 h-3"><circle cx="12" cy="12" r="8"/><path d="M6.8 6.8l10.4 10.4"/></svg>VOID</span>'
            : '<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg text-[11px] font-extrabold bg-emerald-100 text-emerald-800"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" class="w-3 h-3"><path d="M9.5 5.5L5 10l4.5 4.5"/><path d="M5 10h9a5 5 0 0 1 0 10h-2.5"/></svg>RETURN</span>'
          }
        </td>
      </tr>
    `;
  }).join('');
}

// Initialize
updateStats();
updateTopProducts();
updateRecentEntries();
