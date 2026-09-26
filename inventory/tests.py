"""Test form transaksi Void/Return (Phase 3.1) dan Create View (Phase 3.2).

Fixtures dibuat sendiri — tidak bergantung pada Master Barang produksi
(17.257 record). Foto dibuat via Pillow: PNG kecil, BMP valid > 5 MB,
dan file non-gambar.

Foto yang tersimpan lewat Create View ditulis ke folder media sementara
(MEDIA_ROOT dipindah selama test) supaya tidak mengotori folder media/
project.
"""

import os
import shutil
import tempfile
from decimal import Decimal
from io import BytesIO

from django.core.files.storage import default_storage, storages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import empty
from PIL import Image

from inventory.forms import VoidReturnForm
from inventory.models import Barang, VoidReturn


def foto_kecil():
    """Foto valid berukuran kecil (PNG)."""
    buf = BytesIO()
    Image.new("RGB", (16, 16), "red").save(buf, format="PNG")
    return SimpleUploadedFile("struk.png", buf.getvalue(), content_type="image/png")


def foto_lebih_5mb():
    """Foto valid berukuran > 5 MB (BMP tanpa kompresi: 1900x1900x3 ~ 10,8 MB)."""
    buf = BytesIO()
    Image.new("RGB", (1900, 1900), "blue").save(buf, format="BMP")
    return SimpleUploadedFile("besar.bmp", buf.getvalue(), content_type="image/bmp")


def file_bukan_gambar():
    """File yang jelas bukan gambar."""
    return SimpleUploadedFile(
        "catatan.txt", b"ini bukan gambar", content_type="text/plain"
    )


class VoidReturnFormTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.barang = Barang.objects.create(
            kode="TES001",
            nama="Produk Tes",
            barcode_aktif="8991234567890",
            isi=1,
            h_jual=Decimal("10000.00"),
            qty_bad_stock=0,
            qty_akhir=0,
            qty_gd=0,
            sat_k="",
            sat_b="",
            pareto="SM",
            jenis="BKP",
        )
        cls.barang_lain = Barang.objects.create(
            kode="TES002",
            nama="Produk Lain",
            barcode_aktif="8999999999999",
            isi=1,
            h_jual=Decimal("20000.00"),
            qty_bad_stock=0,
            qty_akhir=0,
            qty_gd=0,
            sat_k="",
            sat_b="",
            pareto="SM",
            jenis="BKP",
        )

    # ------------------------------------------------------------------
    # Pembantu
    # ------------------------------------------------------------------
    def data_void(self, **ubah):
        data = {
            "jenis": "VOID",
            "tanggal": timezone.localdate().isoformat(),
            "outlet": "BT1",
            "nama_kasir": "Siti",
            "otoritas": "Andi",
            "barcode": "8991234567890",
            "quantity": "3",
            "alasan": "Barang rusak",
        }
        data.update(ubah)
        return data

    def data_return(self, **ubah):
        data = {
            "jenis": "RETURN",
            "tanggal": timezone.localdate().isoformat(),
            "outlet": "BT5",
            "nama_kasir": "Budi",
            "otoritas": "Maya",
            "no_trans": "TRX-001",
            "barcode": "8991234567890",
            "quantity": "1",
            "harga_jual": "15000.50",
            "alasan": "Salah kirim",
        }
        data.update(ubah)
        return data

    def files(self, foto="kecil"):
        if foto == "kecil":
            return {"foto": foto_kecil()}
        if foto == "besar":
            return {"foto": foto_lebih_5mb()}
        if foto == "bukan-gambar":
            return {"foto": file_bukan_gambar()}
        return {}  # "tidak" — tanpa foto

    def form(self, data, foto="kecil"):
        return VoidReturnForm(data=data, files=self.files(foto))

    # ------------------------------------------------------------------
    # Kasus valid
    # ------------------------------------------------------------------
    def test_void_valid_dengan_barcode_valid(self):
        form = self.form(self.data_void())
        self.assertTrue(form.is_valid(), form.errors)

        # Barang berasal dari lookup barcode, bukan input frontend
        self.assertEqual(form.cleaned_data["barang"], self.barang)

        instance = form.save(commit=False)
        self.assertEqual(instance.jenis, "VOID")
        self.assertEqual(instance.barang, self.barang)
        self.assertEqual(instance.outlet, "BT1")
        self.assertEqual(instance.quantity, 3)
        # VOID: No. Trans & H. Jual harus NULL
        self.assertIsNone(instance.no_trans)
        self.assertIsNone(instance.harga_jual)
        self.assertTrue(instance.foto)

    def test_return_valid_dengan_h_jual_manual(self):
        form = self.form(self.data_return())
        self.assertTrue(form.is_valid(), form.errors)

        instance = form.save(commit=False)
        self.assertEqual(instance.jenis, "RETURN")
        self.assertEqual(instance.barang, self.barang)
        self.assertEqual(instance.no_trans, "TRX-001")
        # H. Jual dari input user (manual), bukan dari Barang.h_jual
        self.assertEqual(instance.harga_jual, Decimal("15000.50"))
        self.assertNotEqual(instance.harga_jual, self.barang.h_jual)

    def test_return_tanpa_no_trans_dinormalisasi_null(self):
        form = self.form(self.data_return(no_trans=""))
        self.assertTrue(form.is_valid(), form.errors)

        instance = form.save(commit=False)
        self.assertIsNone(instance.no_trans)
        self.assertEqual(form.cleaned_data["barang"], self.barang)

    # ------------------------------------------------------------------
    # Kasus invalid
    # ------------------------------------------------------------------
    def test_barcode_tidak_ditemukan_ditolak(self):
        form = self.form(self.data_void(barcode="0000000000000"))
        self.assertFalse(form.is_valid())
        self.assertIn("barcode", form.errors)
        self.assertIn(
            "Barcode tidak ditemukan di Master Barang.", form.errors["barcode"]
        )

    def test_outlet_bt0_ditolak(self):
        form = self.form(self.data_void(outlet="BT0"))
        self.assertFalse(form.is_valid())
        self.assertIn("outlet", form.errors)
        self.assertIn("Outlet tidak valid. Pilih BT1 sampai BT27.", form.errors["outlet"])

    def test_outlet_di_luar_bt1_bt27_ditolak(self):
        form = self.form(self.data_void(outlet="BT28"))
        self.assertFalse(form.is_valid())
        self.assertIn("outlet", form.errors)
        self.assertIn("Outlet tidak valid. Pilih BT1 sampai BT27.", form.errors["outlet"])

    def test_quantity_nol_ditolak(self):
        form = self.form(self.data_void(quantity="0"))
        self.assertFalse(form.is_valid())
        self.assertIn("quantity", form.errors)
        self.assertIn("Quantity harus minimal 1.", form.errors["quantity"])

    def test_quantity_negatif_ditolak(self):
        form = self.form(self.data_void(quantity="-5"))
        self.assertFalse(form.is_valid())
        self.assertIn("quantity", form.errors)
        self.assertIn("Quantity harus minimal 1.", form.errors["quantity"])

    def test_return_tanpa_h_jual_ditolak(self):
        form = self.form(self.data_return(harga_jual=""))
        self.assertFalse(form.is_valid())
        self.assertIn("harga_jual", form.errors)
        # Pesan berasal dari aturan clean() model VoidReturn (satu, tanpa ganda).
        # Posisi-agnostic terhadap wording model: "wajib diisi" + "Return".
        self.assertTrue(
            any("wajib diisi" in e and "Return" in e for e in form.errors["harga_jual"]),
            form.errors["harga_jual"],
        )

    def test_void_dengan_h_jual_ditolak(self):
        form = self.form(self.data_void(harga_jual="15000"))
        self.assertFalse(form.is_valid())
        self.assertIn("harga_jual", form.errors)
        self.assertIn("H. Jual tidak digunakan untuk Void.", form.errors["harga_jual"])

    def test_void_dengan_no_trans_ditolak(self):
        form = self.form(self.data_void(no_trans="TRX-9"))
        self.assertFalse(form.is_valid())
        self.assertIn("no_trans", form.errors)
        self.assertIn("No. Trans tidak digunakan untuk Void.", form.errors["no_trans"])

    def test_foto_wajib_untuk_void_dan_return(self):
        for label, pembuat in (("VOID", self.data_void), ("RETURN", self.data_return)):
            with self.subTest(jenis=label):
                form = VoidReturnForm(data=pembuat(), files={})
                self.assertFalse(form.is_valid())
                self.assertIn("foto", form.errors)
                self.assertIn("Foto wajib diunggah.", form.errors["foto"])

    def test_foto_lebih_dari_5mb_ditolak(self):
        form = self.form(self.data_void(), foto="besar")
        self.assertFalse(form.is_valid())
        self.assertIn("foto", form.errors)
        self.assertTrue(
            any("5 MB" in e for e in form.errors["foto"]), form.errors["foto"]
        )

    def test_file_bukan_gambar_ditolak(self):
        form = self.form(self.data_void(), foto="bukan-gambar")
        self.assertFalse(form.is_valid())
        self.assertIn("foto", form.errors)
        self.assertIn(
            "File yang diunggah harus berupa gambar.", form.errors["foto"]
        )

    # ------------------------------------------------------------------
    # Kasus tambahan (konsistensi requirement)
    # ------------------------------------------------------------------
    def test_jenis_tidak_valid_ditolak(self):
        form = self.form(self.data_void(jenis="REFUND"))
        self.assertFalse(form.is_valid())
        self.assertIn("jenis", form.errors)
        self.assertIn("Jenis harus VOID atau RETURN.", form.errors["jenis"])

    def test_input_barang_dari_frontend_diabaikan(self):
        """Manipulasi field `barang` lewat POST tidak memengaruhi hasil."""
        data = self.data_void(barang=str(self.barang_lain.pk))
        form = self.form(data)
        self.assertTrue(form.is_valid(), form.errors)
        # Yang dipakai tetap hasil lookup barcode, bukan nilai yang diposting
        self.assertEqual(form.cleaned_data["barang"], self.barang)
        self.assertEqual(form.save(commit=False).barang, self.barang)

    def test_label_dan_tanggal_default(self):
        form_void = VoidReturnForm(data=self.data_void())
        form_return = VoidReturnForm(data=self.data_return())

        self.assertEqual(form_void.fields["alasan"].label, "Alasan Void")
        self.assertEqual(form_return.fields["alasan"].label, "Alasan Return")
        self.assertEqual(form_void.fields["otoritas"].label, "Otoritas / MOD")
        self.assertEqual(form_void.fields["no_trans"].label, "No. Trans")

        kosong = VoidReturnForm()
        self.assertEqual(kosong.fields["tanggal"].initial, timezone.localdate())


def _reset_storage():
    """Reset cache storage.

    Django tidak punya signal reset untuk MEDIA_ROOT (hanya STORAGES/
    STATIC_*), sehingga override_settings(MEDIA_ROOT) perlu dibantu
    mengosongkan cache instance storage agar path baru terbaca.
    """
    storages._storages = {}
    default_storage._wrapped = empty


class InputViewTests(TestCase):
    """Test Create View GET/POST /input (Phase 3.2)."""

    @classmethod
    def setUpTestData(cls):
        cls.barang = Barang.objects.create(
            kode="VIEW001",
            nama="Produk View Tes",
            barcode_aktif="8991111111111",
            isi=1,
            h_jual=Decimal("10000.00"),
            qty_bad_stock=0,
            qty_akhir=0,
            qty_gd=0,
            sat_k="",
            sat_b="",
            pareto="SM",
            jenis="BKP",
        )

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        _dir = os.path.join(tempfile.gettempdir(), "opencode")
        cls.media_dir = tempfile.mkdtemp(
            prefix="voidreturn_test_media_", dir=_dir if os.path.isdir(_dir) else None
        )
        cls._media_override = override_settings(MEDIA_ROOT=cls.media_dir)
        cls._media_override.enable()
        _reset_storage()

    @classmethod
    def tearDownClass(cls):
        cls._media_override.disable()
        _reset_storage()
        shutil.rmtree(cls.media_dir, ignore_errors=True)
        super().tearDownClass()

    def data_void(self, **ubah):
        data = {
            "jenis": "VOID",
            "tanggal": timezone.localdate().isoformat(),
            "outlet": "BT2",
            "nama_kasir": "Sari",
            "otoritas": "Rudi",
            "barcode": "8991111111111",
            "quantity": "2",
            "alasan": "Barang rusak",
            "foto": foto_kecil(),
        }
        data.update(ubah)
        return data

    def data_return(self, **ubah):
        data = {
            "jenis": "RETURN",
            "tanggal": timezone.localdate().isoformat(),
            "outlet": "BT7",
            "nama_kasir": "Dewi",
            "otoritas": "Lina",
            "no_trans": "",
            "barcode": "8991111111111",
            "quantity": "1",
            "harga_jual": "15000.50",
            "alasan": "Salah kirim",
            "foto": foto_kecil(),
        }
        data.update(ubah)
        return data

    def test_get_input_menampilkan_form(self):
        response = self.client.get(reverse("inventory:input"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "input.html")
        self.assertIn("form", response.context)
        self.assertIsInstance(response.context["form"], VoidReturnForm)
        self.assertFalse(response.context["form"].is_bound)

    def test_post_void_valid_tersimpan_dan_redirect(self):
        response = self.client.post(reverse("inventory:input"), self.data_void())

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("inventory:input"))

        self.assertEqual(VoidReturn.objects.count(), 1)
        transaksi = VoidReturn.objects.get()
        self.assertEqual(transaksi.jenis, VoidReturn.JENIS_VOID)
        self.assertEqual(transaksi.barang, self.barang)
        self.assertEqual(transaksi.outlet, "BT2")
        self.assertEqual(transaksi.nama_kasir, "Sari")
        self.assertEqual(transaksi.quantity, 2)
        # VOID: H. Jual dan No. Trans harus NULL
        self.assertIsNone(transaksi.harga_jual)
        self.assertIsNone(transaksi.no_trans)

    def test_post_return_valid_tersimpan_dan_redirect(self):
        response = self.client.post(
            reverse("inventory:input"), self.data_return(), follow=True
        )

        # POST -> save -> redirect (bukan render langsung)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.redirect_chain), 1)
        self.assertEqual(response.redirect_chain[0][1], 302)
        self.assertEqual(response.redirect_chain[0][0], reverse("inventory:input"))

        self.assertEqual(VoidReturn.objects.count(), 1)
        transaksi = VoidReturn.objects.get()
        self.assertEqual(transaksi.jenis, VoidReturn.JENIS_RETURN)
        self.assertEqual(transaksi.barang, self.barang)
        self.assertEqual(transaksi.harga_jual, Decimal("15000.50"))
        self.assertIsNone(transaksi.no_trans)  # "" -> NULL

        # success message tampil di halaman tujuan
        self.assertContains(response, "Transaksi Return berhasil disimpan.")

    def test_post_invalid_tidak_membuat_record(self):
        data = self.data_void(barcode="0000000000000")  # tidak ada di master
        response = self.client.post(reverse("inventory:input"), data)

        self.assertEqual(response.status_code, 200)  # bukan redirect
        self.assertTemplateUsed(response, "input.html")
        self.assertEqual(VoidReturn.objects.count(), 0)

        form = response.context["form"]
        self.assertTrue(form.is_bound)
        self.assertIn("barcode", form.errors)
        # data input tetap dipertahankan saat render ulang
        self.assertEqual(form.data["nama_kasir"], "Sari")
        self.assertEqual(form.data["outlet"], "BT2")

    def test_foto_diterima_multipart_dan_tersimpan(self):
        response = self.client.post(reverse("inventory:input"), self.data_void())
        self.assertEqual(response.status_code, 302)

        transaksi = VoidReturn.objects.get()
        self.assertTrue(transaksi.foto)  # request.FILES diterima view
        self.assertTrue(transaksi.foto.name.startswith("foto/"))
        self.assertTrue(transaksi.foto.path.startswith(self.media_dir))
        self.assertTrue(os.path.exists(transaksi.foto.path))  # file nyata di disk

    def test_success_message_void_tampil(self):
        response = self.client.post(
            reverse("inventory:input"), self.data_void(), follow=True
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Transaksi Void berhasil disimpan.")
        self.assertEqual(VoidReturn.objects.count(), 1)

    def test_csrf_aktif_menolak_post_tanpa_token(self):
        client = Client(enforce_csrf_checks=True)
        response = client.post(reverse("inventory:input"), self.data_void())

        self.assertEqual(response.status_code, 403)
        self.assertEqual(VoidReturn.objects.count(), 0)
