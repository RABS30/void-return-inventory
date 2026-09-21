# Void & Return Barang - Demo Ready Pages

## 📋 Halaman Demo yang Tersedia

Sistem ini memiliki **dua versi halaman**:

### 1. Halaman Original (Belum Backend)
- `/` - Dashboard original
- `/input` - Form input original
- `/daftar` - Daftar transaksi original

### 2. Halaman Ready (Dengan Dummy Data & JavaScript Interaktif)
- `/dashboard-ready` - Dashboard dengan statistik dinamis
- `/input-ready` - Form input lengkap dengan validasi
- `/daftar-ready` - Daftar dengan export CSV

## 🎯 Fitur Halaman Ready

### Dashboard Ready (`/dashboard-ready`)
✅ **Statistik Real-time:**
- Total entri transaksi
- Jumlah Void
- Jumlah Return
- Transaksi hari ini

✅ **Visualisasi:**
- Chart Void vs Return dengan bar progress
- Top 3 produk paling sering
- Tabel entri terbaru (5 data terakhir)

✅ **Data Source:**
- Menggunakan dummy data dari JavaScript
- Support localStorage untuk data dari form input

---

### Input Ready (`/input-ready`)
✅ **Form Lengkap:**
- Tanggal
- Quantity
- **Nama Kasir** ✨ (BARU)
- **Nama Otoritas/MOD** ✨ (BARU)
- **Outlet** (BT0-BT27) ✨ (BARU)
- Barcode dengan lookup otomatis
- Pilihan jenis: Void / Return

✅ **Conditional Fields:**
- **VOID:** Alasan Void
- **RETURN:** No. Trans, H. Jual, Alasan Refund, Foto Struk

✅ **Fitur Interaktif:**
- Barcode lookup real-time (dummy data)
- Auto-fill nama barang saat barcode ditemukan
- Preview foto struk saat upload
- Form validation
- Success/error toast notification
- Data tersimpan ke localStorage

✅ **Dummy Barcode yang Tersedia:**
```
8992388101010 - Indomie Goreng 85g (Rp 3.500)
8993675610019 - Aqua Botol 600ml (Rp 4.000)
8996001600016 - Teh Pucuk Harum 350ml (Rp 3.000)
8998866123456 - Chitato Sapi Panggang 68g (Rp 8.500)
8991001234567 - Mie Sedaap Goreng 85g (Rp 3.200)
8992761111111 - Ultra Milk Coklat 200ml (Rp 5.500)
```

---

### Daftar Ready (`/daftar-ready`)
✅ **Tabel Transaksi:**
- Tanggal
- Outlet
- Barang / Barcode
- Quantity
- Tipe (Void/Return)
- Kasir
- Otoritas
- Alasan
- Aksi (Hapus)

✅ **Fitur Filter & Search:**
- Filter: Semua / Void saja / Return saja
- Search: Barcode, nama barang, alasan, kasir, outlet
- Responsive desktop & mobile

✅ **Export CSV:**
- **Export Void** - Format sesuai AGENTS.md:
  ```
  NO, OUTLET, TANGGAL, NAMA PRODUK, BARCODE, QTY, KASIR, OTORITAS, ALASAN VOID
  ```
- **Export Return** - Format sesuai AGENTS.md:
  ```
  TANGGAL, OUTLET, NAMA KASIR, NO.TRANS, NAMA PRODUK, BARCODE, QTY, H.JUAL, OTORITAS, ALASAN REFUND
  ```

✅ **Delete Transaction:**
- Konfirmasi sebelum hapus
- Update statistik otomatis

---

## 🚀 Cara Menggunakan Demo

### 1. Akses Dashboard Ready
```
http://localhost:8000/dashboard-ready
```
- Lihat statistik dummy data
- Navigasi ke halaman lain

### 2. Test Input Form
```
http://localhost:8000/input-ready
```

**Test Void:**
1. Pilih tanggal
2. Isi Nama Kasir (contoh: "Mawar Melati")
3. Isi Nama Otoritas (contoh: "Raflesia Arnoldi")
4. Pilih Outlet (contoh: "BT5")
5. Masukkan barcode: `8992388101010`
6. Nama barang muncul otomatis: "Indomie Goreng 85g"
7. Pilih **VOID**
8. Isi Alasan Void: "Kasir salah input"
9. Klik **Simpan Data**
10. Toast success muncul, redirect ke daftar

**Test Return:**
1. Isi data seperti Void
2. Masukkan barcode: `8993675610019`
3. Pilih **RETURN**
4. Field tambahan muncul:
   - No. Trans: `TRX20260922001`
   - H. Jual: (auto-fill dari dummy data atau input manual)
   - Alasan Refund: "Kemasan bocor"
   - Foto Struk: Upload gambar
5. Preview foto muncul
6. Klik **Simpan Data**

### 3. Lihat Daftar & Export
```
http://localhost:8000/daftar-ready
```

**Filter:**
- Pilih "Void saja" untuk filter Void
- Pilih "Return saja" untuk filter Return

**Search:**
- Ketik barcode: `8992388101010`
- Ketik nama: `Indomie`
- Ketik outlet: `BT5`

**Export:**
- Klik **Ekspor Void** → Download CSV void data
- Klik **Ekspor Return** → Download CSV return data

**Hapus:**
- Klik tombol **Hapus** pada row
- Konfirmasi hapus
- Data hilang dari tabel dan statistik update

---

## 💾 Data Storage

### LocalStorage
Data transaksi dari form input tersimpan di browser localStorage dengan key:
```javascript
localStorage.getItem('transactions')
```

### Dummy Data
Jika localStorage kosong, sistem akan load dummy data default:
- 6 transaksi sample
- Mix antara Void dan Return
- Tanggal bervariasi (3 hari terakhir)

### Reset Data
Untuk reset ke dummy data default:
```javascript
localStorage.removeItem('transactions');
location.reload();
```

---

## 🎨 UI/UX Features

✅ **Responsive:**
- Desktop: Table layout
- Mobile: Card layout dengan FAB button

✅ **Dark Mode Support:**
- Otomatis detect system preference
- Tailwind dark mode classes

✅ **Toast Notifications:**
- Success: Green toast
- Error: Red toast
- Auto-hide setelah 3 detik

✅ **Form Validation:**
- Required fields
- Barcode tidak ditemukan → error
- Return tanpa foto → error

✅ **Loading States:**
- Smooth transitions
- Instant feedback

---

## 📊 CSV Export Format

### Void CSV
```csv
NO,OUTLET,TANGGAL,NAMA PRODUK,BARCODE,QTY,KASIR,OTORITAS,ALASAN VOID
1,BT5,2026-09-21,Indomie Goreng 85g,8992388101010,2,Mawar Melati,Raflesia Arnoldi,Kasir salah input jumlah
```

### Return CSV
```csv
TANGGAL,OUTLET,NAMA KASIR,NO.TRANS,NAMA PRODUK,BARCODE,QTY,H.JUAL,OTORITAS,ALASAN REFUND
2026-09-21,BT3,Tulip ,TRX20260921001,Aqua Botol 600ml,8993675610019,1,4000,Patrick,Kemasan bocor
```

**Format sesuai AGENTS.md Section 18 & 19**

---

## 🔧 Technical Details

### JavaScript Files
- `/static/js/dashboard-ready.js` - Dashboard logic
- `/static/js/input-ready.js` - Input form logic
- `/static/js/daftar-ready.js` - List & export logic

### Templates
- `/templates/dashboard-ready.html`
- `/templates/input-ready.html`
- `/templates/daftar-ready.html`

### Dummy Data
```javascript
// Barcode lookup (input-ready.js)
const dummyBarang = {
  '8992388101010': { nama: 'Indomie Goreng 85g', hjual: 3500 },
  '8993675610019': { nama: 'Aqua Botol 600ml', hjual: 4000 },
  // ...
};

// Transactions (daftar-ready.js & dashboard-ready.js)
const dummyTransactions = [
  { id: 1, tanggal: '2026-09-21', outlet: 'BT5', ... },
  // ...
];
```

---

## ⚠️ Catatan Penting

### Ini Adalah Demo Frontend
- **Tidak ada backend database**
- Data tersimpan di localStorage browser
- Data hilang jika clear browser cache
- Export CSV menggunakan Blob API client-side

### Untuk Production
Halaman ready ini akan digantikan dengan:
- Backend Django views dengan query database
- Model Barang dan VoidReturn
- Real barcode lookup API
- File upload ke server
- Server-side CSV generation
- Authentication & authorization

### Development Phases
1. ✅ **Phase Current:** Frontend demo dengan dummy data
2. 🔄 **Phase Next:** Database models (Barang, VoidReturn)
3. 🔄 **Phase Next:** Backend API & views
4. 🔄 **Phase Next:** Integration frontend-backend

---

## 🎯 Demo Checklist untuk Client

### Yang Bisa Dicoba:
- [x] Lihat dashboard dengan statistik
- [x] Input transaksi Void
- [x] Input transaksi Return dengan foto
- [x] Barcode lookup otomatis
- [x] Filter Void/Return
- [x] Search transaksi
- [x] Export CSV Void
- [x] Export CSV Return
- [x] Hapus transaksi
- [x] Responsive mobile/desktop
- [x] Toast notifications

### Yang Belum Ada (Nanti di Backend):
- [ ] Data persisten di database
- [ ] Real barcode dari master
- [ ] Upload foto ke server
- [ ] User authentication
- [ ] Multi-user support
- [ ] Audit trail
- [ ] Advanced reporting

---

## 📞 Support

Untuk pertanyaan atau issue terkait demo ini, hubungi developer.

**Happy Testing! 🎉**
