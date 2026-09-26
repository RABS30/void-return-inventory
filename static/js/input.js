(function () {
    'use strict';

    var MAX_FOTO_BYTES = 5 * 1024 * 1024; // 5 MB

    var blokReturn = document.getElementById('blok-return');
    var inputNoTrans = document.getElementById('no-trans');
    var inputHJual = document.getElementById('h-jual');
    var labelAlasan = document.getElementById('label-alasan');
    var textareaAlasan = document.getElementById('alasan');
    var labelFoto = document.getElementById('label-foto');
    var deskripsiFoto = document.getElementById('deskripsi-foto');
    var inputFoto = document.getElementById('foto');
    var previewWrap = document.getElementById('preview-wrap');
    var previewFoto = document.getElementById('preview-foto');
    var toast = document.getElementById('toast');

    function logDebug(pesan) {
        if (window.console && console.warn) console.warn('[input.js] ' + pesan);
    }

    // Radio jenis: name="jenis" (HTML saat ini) — name="tipe" ditangani sebagai cadangan
    function cariRadioJenis() {
        var nodes = document.querySelectorAll(
            'input[type="radio"][name="jenis"], input[type="radio"][name="tipe"]'
        );
        return Array.prototype.slice.call(nodes);
    }

    function nilaiJenisTerpilih() {
        var radios = cariRadioJenis();
        for (var i = 0; i < radios.length; i++) {
            if (radios[i].checked) return String(radios[i].value || '').toUpperCase();
        }
        return 'VOID';
    }

    // Tampil/sembunyi memakai atribut hidden (native) DAN kelas Tailwind, supaya tetap
    // berfungsi walau CDN Tailwind belum termuat
    function setTampil(elemen, tampil) {
        if (!elemen) return;
        elemen.hidden = !tampil;
        if (elemen.classList) elemen.classList.toggle('hidden', !tampil);
    }

    // Sinkronkan tampilan & required state dengan jenis transaksi
    function updateForm() {
        var isReturn = nilaiJenisTerpilih() === 'RETURN';

        if (blokReturn) {
            setTampil(blokReturn, isReturn); // No. Trans + H. Jual tampil hanya untuk RETURN
        } else {
            logDebug('elemen #blok-return tidak ditemukan di halaman.');
        }

        // No. Transaksi: opsional (tidak pernah required), hanya aktif untuk RETURN
        if (inputNoTrans) {
            inputNoTrans.disabled = !isReturn;
            inputNoTrans.required = false;
        } else {
            logDebug('elemen #no-trans tidak ditemukan di halaman.');
        }

        // H. Jual: input manual, wajib hanya untuk RETURN, tidak aktif saat VOID
        if (inputHJual) {
            inputHJual.disabled = !isReturn;
            inputHJual.required = isReturn;
        } else {
            logDebug('elemen #h-jual tidak ditemukan di halaman.');
        }

        // Label alasan: Alasan Void / Alasan Return
        if (labelAlasan) {
            labelAlasan.textContent = isReturn ? 'Alasan Return' : 'Alasan Void';
        } else {
            logDebug('elemen #label-alasan tidak ditemukan di halaman.');
        }
        if (textareaAlasan) {
            textareaAlasan.placeholder = isReturn
                ? 'cth. alasan return, kondisi barang, dll'
                : 'cth. alasan void, kondisi barang, dll';
        }

        // Foto selalu wajib; deskripsi mengikuti jenis
        if (inputFoto) inputFoto.required = true;
        if (labelFoto) {
            labelFoto.textContent = isReturn ? 'Foto Struk *' : 'Foto (dokumentasi Void) *';
        }
        if (deskripsiFoto) {
            deskripsiFoto.textContent = isReturn
                ? 'Foto digunakan sebagai foto struk dan wajib diunggah.'
                : 'Foto digunakan sebagai dokumentasi Void dan wajib diunggah.';
        }
    }

    // Pasang listener langsung ke radio jenis (hindari pemasangan ganda)
    function pasangListenerRadio() {
        var radios = cariRadioJenis();
        for (var i = 0; i < radios.length; i++) {
            if (radios[i].getAttribute('data-jenis-listener') === '1') continue;
            radios[i].setAttribute('data-jenis-listener', '1');
            radios[i].addEventListener('change', updateForm);
        }
    }

    pasangListenerRadio();

    // Cadangan: delegasi peristiwa di level document, menangkap radio apa pun
    // yang bernilai VOID/RETURN meski nama radio berubah di kemudian hari
    document.addEventListener('change', function (e) {
        var t = e.target;
        if (!t || !t.tagName || String(t.tagName).toUpperCase() !== 'INPUT' || t.type !== 'radio') return;
        var nilai = String(t.value || '').toUpperCase();
        if (nilai === 'VOID' || nilai === 'RETURN') {
            pasangListenerRadio();
            updateForm();
        }
    });

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () {
            pasangListenerRadio();
            updateForm();
        });
    }

    // Validasi ringan foto + preview (bukan base64 dummy)
    var previewUrl = null;
    function bersihkanPreview() {
        if (previewUrl) {
            URL.revokeObjectURL(previewUrl);
            previewUrl = null;
        }
        if (previewFoto) previewFoto.removeAttribute('src');
        if (previewWrap) previewWrap.classList.add('hidden');
    }

    if (inputFoto) {
        inputFoto.addEventListener('change', function () {
            var file = inputFoto.files && inputFoto.files[0];
            bersihkanPreview();
            if (!file) return;

            if (file.type && file.type.indexOf('image/') !== 0) {
                inputFoto.value = '';
                showToast('File harus berupa gambar.');
                return;
            }

            if (file.size > MAX_FOTO_BYTES) {
                inputFoto.value = '';
                showToast('Ukuran foto melebihi 5 MB. Pilih foto yang lebih kecil.');
                return;
            }

            if (previewFoto && previewWrap) {
                previewUrl = URL.createObjectURL(file);
                previewFoto.src = previewUrl;
                previewWrap.classList.remove('hidden');
            }
        });
    }

    var toastTimer = null;
    function showToast(pesan) {
        if (!toast) return;
        toast.className = 'fixed z-50 top-4 right-4 rounded-xl px-4 py-3 shadow-lg text-sm font-semibold text-white bg-rose-600 pop';
        toast.textContent = pesan;
        if (toastTimer) clearTimeout(toastTimer);
        toastTimer = setTimeout(function () {
            toast.classList.add('hidden');
        }, 3500);
    }

    // ===== AJAX lookup barcode (Phase 3.6) ================================
    // Backend tetap source of truth: JS hanya menampilkan hasil JSON dari
    // endpoint inventory:barcode_lookup. Nama produk tidak pernah diambil
    // dari data lokal.
    var inputBarcode = document.getElementById('barcode');
    var inputNamaProduk = document.getElementById('nama-produk');
    var statusBarcode = document.getElementById('status-barcode');
    var urlTemplateBarcode = inputBarcode ? inputBarcode.getAttribute('data-url-template') : null;

    var lookupBerjalan = null; // AbortController request yang masih aktif
    var idLookup = 0;          // penanda urutan: response basi diabaikan
    var timerLookup = null;    // debounce ketikan cepat / scanner HID
    var pemberitahuLookup = null; // callback sekali-pakai: panel scanner diberi
                                  // tahu hasil lookup backend (tanpa mengubah
                                  // cara lookup menentukan hasil)

    function beritahuLookup(status) {
        if (!pemberitahuLookup) return;
        var f = pemberitahuLookup;
        pemberitahuLookup = null;
        f(status);
    }

    function setStatusBarcode(pesan, jenis) {
        if (!statusBarcode) return;
        if (!pesan) {
            statusBarcode.textContent = '';
            statusBarcode.className = 'mt-2 text-xs font-semibold hidden';
            return;
        }
        statusBarcode.textContent = pesan;
        // className dikelola penuh — elemen ini hanya membawa kelas tampilan.
        statusBarcode.className = 'mt-2 text-xs font-semibold ' + (jenis === 'gagal'
            ? 'text-rose-600 dark:text-rose-400'
            : 'text-slate-500 dark:text-slate-400');
    }

    function tampilkanNamaProduk(nama) {
        if (inputNamaProduk) inputNamaProduk.value = nama || '';
    }

    function batalkanLookup() {
        if (timerLookup) {
            clearTimeout(timerLookup);
            timerLookup = null;
        }
        if (lookupBerjalan) {
            lookupBerjalan.abort();
            lookupBerjalan = null;
        }
    }

    function lookupBarcode() {
        if (!inputBarcode || !urlTemplateBarcode) return;

        var barcode = String(inputBarcode.value || '').trim();

        // Barcode dikosongkan: bersihkan nama produk tanpa request.
        if (!barcode) {
            batalkanLookup();
            idLookup++;
            tampilkanNamaProduk('');
            setStatusBarcode('', null);
            beritahuLookup('kosong');
            return;
        }

        // Batalkan request lama sebelum mulai yang baru (race condition:
        // response request A tidak boleh menimpa hasil request B).
        batalkanLookup();
        idLookup++;
        var idSekarang = idLookup;

        lookupBerjalan = new AbortController();
        setStatusBarcode('Mencari barang…', 'info');

        // URL dirender Django (aman untuk subpath), placeholder diganti
        // nilai barcode yang di-encode — tanpa hard-code host/domain.
        fetch(urlTemplateBarcode.replace('__BARCODE__', encodeURIComponent(barcode)), {
            method: 'GET',
            headers: { 'Accept': 'application/json' },
            credentials: 'same-origin',
            signal: lookupBerjalan.signal
        })
            .then(function (res) {
                if (!res.ok) throw new Error('HTTP ' + res.status);
                return res.json();
            })
            .then(function (data) {
                if (idSekarang !== idLookup) return; // response basi — abaikan
                if (data && data.found) {
                    tampilkanNamaProduk(data.nama);
                    setStatusBarcode('', null);
                    beritahuLookup('ditemukan');
                } else {
                    tampilkanNamaProduk('');
                    setStatusBarcode('Barcode tidak ditemukan.', 'gagal');
                    beritahuLookup('tidak');
                }
            })
            .catch(function (err) {
                if (err && err.name === 'AbortError') return; // hasil pembatalan
                if (idSekarang !== idLookup) return;
                tampilkanNamaProduk('');
                setStatusBarcode('Gagal memeriksa barcode. Coba lagi.', 'gagal');
                beritahuLookup('gagal');
            })
            .then(function () {
                if (idSekarang === idLookup) lookupBerjalan = null;
            });
    }

    if (inputBarcode) {
        inputBarcode.addEventListener('input', function () {
            var barcode = String(inputBarcode.value || '').trim();

            // Kosongkan nama produk langsung, tanpa membuang request.
            if (!barcode) {
                batalkanLookup();
                idLookup++;
                tampilkanNamaProduk('');
                setStatusBarcode('', null);
                beritahuLookup('kosong');
                return;
            }

            setStatusBarcode('Mencari barang…', 'info');
            if (timerLookup) clearTimeout(timerLookup);
            timerLookup = setTimeout(function () {
                timerLookup = null;
                lookupBarcode();
            }, 250); // debounce ketikan cepat / scanner HID
        });
    }

    // Halaman dimuat ulang dengan barcode terisi (mis. setelah form error
    // saat submit): tampilkan nama hasil lookup backend, bukan data lokal.
    if (inputBarcode && String(inputBarcode.value || '').trim()) {
        setStatusBarcode('Mencari barang…', 'info');
        lookupBarcode();
    }

    // ===== Camera barcode scanner (V1.1) ==============================
    // Scanner HANYA mengisi field barcode. Hasil lookup tetap ditentukan
    // backend lewat GET /barcode/<barcode> yang sudah ada (source of truth):
    //    Kamera -> string barcode -> field -> flow lookup AJAX existing
    //        -> Barang.objects.get(barcode_aktif=...) -> nama produk
    //
    // Library (versi dipin, dimuat di input.html sebelum skrip ini):
    //    @zxing/library@0.23.0 (global ZXing) + @zxing/browser@0.2.1
    //    (global ZXingBrowser). BarcodeDetector TIDAK dipakai sebagai
    //    satu-satunya mekanisme (ketersediaannya terbatas di browser).
    //
    // Catatan secure context: akses kamera browser umumnya butuh HTTPS;
    // localhost dikecualikan browser untuk development.
    var tombolScan = document.getElementById('tombol-scan');
    var panelScanner = document.getElementById('scanner-panel');
    var videoScanner = document.getElementById('scanner-video');
    var statusScanner = document.getElementById('scanner-status');
    var tombolTutupScanner = document.getElementById('tombol-tutup-scanner');

    var readerScanner = null;       // instance BrowserMultiFormatReader
    var kontrolScanner = null;      // controls.stop() dari ZXing
    var scannerAktif = false;       // penanda stream sedang berjalan
    var timerTutupOtomatis = null;  // auto-close panel setelah ditemukan

    function setStatusScanner(pesan, jenis) {
        if (!statusScanner) return;
        statusScanner.textContent = pesan || '';
        var warna = 'text-slate-600 dark:text-slate-300';
        if (jenis === 'gagal') warna = 'text-rose-600 dark:text-rose-400';
        else if (jenis === 'sukses') warna = 'text-emerald-600 dark:text-emerald-400';
        statusScanner.className = 'text-xs font-semibold ' + warna;
    }

    function setPanelScanner(tampil) {
        setTampil(panelScanner, tampil);
        if (tombolScan) tombolScan.setAttribute('aria-expanded', tampil ? 'true' : 'false');
    }

    // Hentikan SEMUA sumber kamera: controls ZXing, track yang tersisa di
    // element video (jaring pengaman), lalu reset reader. Tidak boleh ada
    // stream yang tertinggal setelah panel ditutup.
    function hentikanKamera() {
        scannerAktif = false;
        if (kontrolScanner) {
            try { kontrolScanner.stop(); } catch (e) { logDebug('gagal stop kontrol scanner: ' + e); }
            kontrolScanner = null;
        }
        if (videoScanner && videoScanner.srcObject) {
            var tracks = videoScanner.srcObject.getTracks
                ? videoScanner.srcObject.getTracks()
                : [];
            for (var i = 0; i < tracks.length; i++) {
                try { tracks[i].stop(); } catch (e) { logDebug('gagal stop track kamera: ' + e); }
            }
            videoScanner.srcObject = null;
        }
        if (readerScanner) {
            try { readerScanner.reset(); } catch (e) { logDebug('gagal reset reader scanner: ' + e); }
            readerScanner = null;
        }
    }

    function tutupScanner(pesan) {
        if (timerTutupOtomatis) {
            clearTimeout(timerTutupOtomatis);
            timerTutupOtomatis = null;
        }
        hentikanKamera();
        setPanelScanner(false);
        if (pesan) setStatusScanner(pesan, 'info');
    }

    function pesanGalatKamera(err) {
        var nama = err && err.name ? err.name : '';
        if (nama === 'NotAllowedError' || nama === 'PermissionDeniedError' || nama === 'SecurityError') {
            return 'Akses kamera ditolak. Izinkan kamera pada pengaturan browser lalu coba lagi.';
        }
        if (nama === 'NotFoundError' || nama === 'DevicesNotFoundError' || nama === 'OverconstrainedError') {
            return 'Kamera tidak tersedia di perangkat ini.';
        }
        if (nama === 'NotReadableError' || nama === 'TrackStartError') {
            return 'Kamera tidak dapat dibuka (mungkin sedang dipakai aplikasi lain).';
        }
        return 'Gagal membuka kamera: ' + (err && err.message ? err.message : err);
    }

    function prosesHasilScan(teks) {
        // String apa adanya dari hasil decode — digit/leading zero TIDAK diubah.
        var nilai = String(teks == null ? '' : teks);
        if (!nilai || !scannerAktif) return;

        hentikanKamera(); // kamera berhenti begitu barcode terbaca
        setStatusScanner('Barcode terbaca: ' + nilai + ' — memeriksa ke database…', 'info');
        if (!inputBarcode) return;

        // Panel scanner hanya diberi tahu hasil lookup backend; penentuan
        // "ditemukan/tidak" tetap sepenuhnya oleh response backend.
        pemberitahuLookup = function (status) {
            if (status === 'ditemukan') {
                setStatusScanner('Barcode ditemukan — nama produk tampil.', 'sukses');
                if (timerTutupOtomatis) clearTimeout(timerTutupOtomatis);
                timerTutupOtomatis = setTimeout(function () {
                    timerTutupOtomatis = null;
                    tutupScanner('Scanner ditutup otomatis setelah barcode ditemukan.');
                }, 900);
            } else if (status === 'tidak') {
                setStatusScanner('Barcode tidak ditemukan — terbaca kamera, tetapi tidak ada di database.', 'gagal');
            } else if (status === 'gagal') {
                setStatusScanner('Gagal memeriksa barcode ke backend. Coba lagi.', 'gagal');
            } else {
                setStatusScanner('Barcode dikosongkan.', 'info');
            }
        };

        // Isi field barcode lalu jalankan flow lookup AJAX existing apa adanya
        // (debounce, AbortController, dan validasi backend tetap berlaku).
        inputBarcode.value = nilai;
        inputBarcode.dispatchEvent(new Event('input', { bubbles: true }));
    }

    function bukaScanner() {
        if (scannerAktif || readerScanner) return; // cegah lebih dari satu stream
        if (timerTutupOtomatis) {
            clearTimeout(timerTutupOtomatis);
            timerTutupOtomatis = null;
        }

        setPanelScanner(true);

        if (typeof ZXingBrowser === 'undefined' || typeof ZXing === 'undefined') {
            setStatusScanner('Library scanner gagal dimuat. Periksa koneksi internet lalu muat ulang halaman.', 'gagal');
            return;
        }
        if (!window.isSecureContext) {
            setStatusScanner('Kamera hanya bisa dibuka lewat HTTPS atau localhost. Buka aplikasi via HTTPS untuk scan.', 'gagal');
            return;
        }
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            setStatusScanner('Browser ini tidak mendukung akses kamera. Ketik barcode secara manual.', 'gagal');
            return;
        }

        setStatusScanner('Membuka kamera…', 'info');

        // Format retail 1D yang relevan dengan database — tanpa QR/2D agar
        // fokus ke kebutuhan scan produk; hasil decode berupa string murni.
        var hints = new Map();
        hints.set(ZXing.DecodeHintType.POSSIBLE_FORMATS, [
            ZXing.BarcodeFormat.EAN_13,
            ZXing.BarcodeFormat.EAN_8,
            ZXing.BarcodeFormat.UPC_A,
            ZXing.BarcodeFormat.UPC_E,
            ZXing.BarcodeFormat.CODE_128,
            ZXing.BarcodeFormat.CODE_39
        ]);
        hints.set(ZXing.DecodeHintType.TRY_HARDER, true);

        readerScanner = new ZXingBrowser.BrowserMultiFormatReader(
            hints,
            { delayBetweenScanAttempts: 250 }
        );
        scannerAktif = true;

        readerScanner
            .decodeFromConstraints(
                // facingMode ideal 'environment': prioritas kamera belakang
                // di smartphone; di desktop webcam tetap jalan (ideal tidak
                // gagal bila tidak ada).
                { audio: false, video: { facingMode: { ideal: 'environment' } } },
                videoScanner,
                function (hasil) {
                    if (!scannerAktif || !hasil) return;
                    var teks = typeof hasil.getText === 'function' ? hasil.getText() : null;
                    prosesHasilScan(teks);
                }
            )
            .then(function (kontrol) {
                if (!scannerAktif) {
                    // scanner sudah ditutup/di-decode lebih dulu — pastikan
                    // stream hasil resolve ikut berhenti.
                    try { kontrol.stop(); } catch (e) { logDebug('gagal stop kontrol telat: ' + e); }
                    return;
                }
                kontrolScanner = kontrol;
                if (videoScanner && videoScanner.paused && typeof videoScanner.play === 'function') {
                    var jalan = videoScanner.play();
                    if (jalan && jalan.catch) jalan.catch(function () { /* autoplay diblokir browser: abaikan */ });
                }
                setStatusScanner('Kamera aktif — arahkan ke barcode…', 'info');
            })
            .catch(function (err) {
                hentikanKamera();
                setStatusScanner(pesanGalatKamera(err), 'gagal');
            });
    }

    if (tombolScan) {
        tombolScan.addEventListener('click', function () {
            if (scannerAktif || readerScanner) tutupScanner('Scanner ditutup.');
            else bukaScanner();
        });
    }
    if (tombolTutupScanner) {
        tombolTutupScanner.addEventListener('click', function () {
            tutupScanner('Scanner ditutup.');
        });
    }

    // Pastikan tidak ada stream kamera tertinggal saat pindah halaman/reload.
    window.addEventListener('pagehide', function () { hentikanKamera(); });
    window.addEventListener('beforeunload', function () { hentikanKamera(); });

    updateForm();
})();
