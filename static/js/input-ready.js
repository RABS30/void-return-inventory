// Dummy data barang
const dummyBarang = {
  '8992388101010': { nama: 'Indomie Goreng 85g', hjual: 3500 },
  '8993675610019': { nama: 'Aqua Botol 600ml', hjual: 4000 },
  '8996001600016': { nama: 'Teh Pucuk Harum 350ml', hjual: 3000 },
  '8998866123456': { nama: 'Chitato Sapi Panggang 68g', hjual: 8500 },
  '8991001234567': { nama: 'Mie Sedaap Goreng 85g', hjual: 3200 },
  '8992761111111': { nama: 'Ultra Milk Coklat 200ml', hjual: 5500 },
};

// Conditional field Void/Return
document.querySelectorAll('input[name="tipe"]').forEach(radio => {
  radio.addEventListener('change', () => {
    const fotoBlock = document.getElementById('blok-foto');
    const notransBlock = document.getElementById('blok-notrans');
    const hjualBlock = document.getElementById('blok-hjual');
    const labelAlasan = document.getElementById('labelAlasan');
    const notransInput = document.getElementById('notrans');
    const hjualInput = document.getElementById('hjual');
    const fotoInput = document.getElementById('foto');
    
    if (radio.value === 'return' && radio.checked) {
      fotoBlock.classList.remove('hidden');
      notransBlock.classList.remove('hidden');
      hjualBlock.classList.remove('hidden');
      labelAlasan.textContent = 'Alasan Refund *';
      notransInput.required = true;
      hjualInput.required = true;
      fotoInput.required = true;
    } else if (radio.value === 'void' && radio.checked) {
      fotoBlock.classList.add('hidden');
      notransBlock.classList.add('hidden');
      hjualBlock.classList.add('hidden');
      labelAlasan.textContent = 'Alasan Void *';
      notransInput.required = false;
      hjualInput.required = false;
      fotoInput.required = false;
    }
  });
});

// Barcode lookup
const barcodeInput = document.getElementById('barcode');
const barangInfo = document.getElementById('barangInfo');
const barangError = document.getElementById('barangError');
const namaBarang = document.getElementById('namaBarang');

barcodeInput.addEventListener('input', function() {
  const barcode = this.value.trim();
  
  if (barcode.length === 0) {
    barangInfo.classList.add('hidden');
    barangError.classList.add('hidden');
    return;
  }
  
  if (dummyBarang[barcode]) {
    barangInfo.classList.remove('hidden');
    barangError.classList.add('hidden');
    namaBarang.textContent = dummyBarang[barcode].nama;
    
    // Auto-fill H. Jual jika Return
    const tipeReturn = document.querySelector('input[name="tipe"][value="return"]');
    if (tipeReturn && tipeReturn.checked) {
      document.getElementById('hjual').value = dummyBarang[barcode].hjual;
    }
  } else {
    barangInfo.classList.add('hidden');
    barangError.classList.remove('hidden');
  }
});

// Photo preview
const fotoInput = document.getElementById('foto');
const previewContainer = document.getElementById('previewContainer');
const preview = document.getElementById('preview');

fotoInput.addEventListener('change', function(e) {
  const file = e.target.files[0];
  if (file) {
    const reader = new FileReader();
    reader.onload = function(e) {
      preview.src = e.target.result;
      previewContainer.classList.remove('hidden');
    };
    reader.readAsDataURL(file);
  }
});

// Form submit handler
const form = document.getElementById('formInput');
const toast = document.getElementById('toast');

form.addEventListener('submit', function(e) {
  e.preventDefault();
  
  // Get form data
  const formData = {
    tanggal: document.getElementById('tanggal').value,
    quantity: document.getElementById('quantity').value,
    kasir: document.getElementById('kasir').value,
    otoritas: document.getElementById('otoritas').value,
    outlet: document.getElementById('outlet').value,
    barcode: document.getElementById('barcode').value,
    tipe: document.querySelector('input[name="tipe"]:checked').value,
    alasan: document.getElementById('alasan').value,
  };
  
  // Validate barcode
  if (!dummyBarang[formData.barcode]) {
    showToast('Barcode tidak ditemukan!', 'error');
    return;
  }
  
  if (formData.tipe === 'return') {
    formData.notrans = document.getElementById('notrans').value;
    formData.hjual = document.getElementById('hjual').value;
    formData.foto = fotoInput.files[0] ? fotoInput.files[0].name : '';
    
    if (!formData.notrans || !formData.hjual || !formData.foto) {
      showToast('Lengkapi semua field Return!', 'error');
      return;
    }
  }
  
  // Save to localStorage
  let transactions = JSON.parse(localStorage.getItem('transactions') || '[]');
  transactions.push({
    ...formData,
    id: Date.now(),
    namaBarang: dummyBarang[formData.barcode].nama,
    timestamp: new Date().toISOString()
  });
  localStorage.setItem('transactions', JSON.stringify(transactions));
  
  showToast('Data berhasil disimpan!', 'success');
  
  // Redirect after 1 second
  setTimeout(() => {
    window.location.href = '/daftar';
  }, 1000);
});

function showToast(message, type) {
  toast.textContent = message;
  toast.className = `fixed z-50 top-4 right-4 px-4 py-3 rounded-xl text-sm font-semibold shadow-lg ${
    type === 'success' ? 'bg-emerald-600 text-white' : 'bg-rose-600 text-white'
  }`;
  toast.classList.remove('hidden');
  
  setTimeout(() => {
    toast.classList.add('hidden');
  }, 3000);
}
