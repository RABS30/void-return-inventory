// API base URL
const API_BASE = '/api';

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

// Barcode lookup using API
const barcodeInput = document.getElementById('barcode');
const barangInfo = document.getElementById('barangInfo');
const barangError = document.getElementById('barangError');
const namaBarang = document.getElementById('namaBarang');

let currentBarangData = null;

barcodeInput.addEventListener('input', async function() {
  const barcode = this.value.trim();
  
  if (barcode.length === 0) {
    barangInfo.classList.add('hidden');
    barangError.classList.add('hidden');
    currentBarangData = null;
    return;
  }
  
  try {
    const response = await fetch(`${API_BASE}/barcode/${barcode}`);
    const result = await response.json();
    
    if (result.success) {
      barangInfo.classList.remove('hidden');
      barangError.classList.add('hidden');
      namaBarang.textContent = result.data.nama;
      currentBarangData = result.data;
      
      // Auto-fill H. Jual jika Return
      const tipeReturn = document.querySelector('input[name="tipe"][value="return"]');
      if (tipeReturn && tipeReturn.checked) {
        document.getElementById('hjual').value = result.data.hjual;
      }
    } else {
      barangInfo.classList.add('hidden');
      barangError.classList.remove('hidden');
      currentBarangData = null;
    }
  } catch (error) {
    barangInfo.classList.add('hidden');
    barangError.classList.remove('hidden');
    currentBarangData = null;
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

form.addEventListener('submit', async function(e) {
  e.preventDefault();
  
  // Validate barcode first
  const barcode = document.getElementById('barcode').value;
  if (!currentBarangData) {
    showToast('Barcode tidak ditemukan!', 'error');
    return;
  }
  
  // Get form data
  const formData = {
    tanggal: document.getElementById('tanggal').value,
    quantity: parseInt(document.getElementById('quantity').value),
    kasir: document.getElementById('kasir').value,
    otoritas: document.getElementById('otoritas').value,
    outlet: document.getElementById('outlet').value,
    barcode: barcode,
    namaBarang: currentBarangData.nama,
    tipe: document.querySelector('input[name="tipe"]:checked').value,
    alasan: document.getElementById('alasan').value,
    notrans: null,
    hjual: null,
    foto: null
  };
  
  if (formData.tipe === 'return') {
    formData.notrans = document.getElementById('notrans').value;
    formData.hjual = parseFloat(document.getElementById('hjual').value);
    formData.foto = fotoInput.files[0] ? fotoInput.files[0].name : null;
    
    if (!formData.notrans || !formData.hjual || !formData.foto) {
      showToast('Lengkapi semua field Return!', 'error');
      return;
    }
  }
  
  // Save to server via API
  try {
    const response = await fetch(`${API_BASE}/transaction/create`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(formData)
    });
    
    const result = await response.json();
    
    if (result.success) {
      showToast('Data berhasil disimpan!', 'success');
      
      // Redirect after 1 second
      setTimeout(() => {
        window.location.href = '/daftar';
      }, 1000);
    } else {
      showToast('Gagal menyimpan data: ' + result.error, 'error');
    }
  } catch (error) {
    showToast('Error: ' + error.message, 'error');
  }
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
