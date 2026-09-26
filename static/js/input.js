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

    updateForm();
})();
