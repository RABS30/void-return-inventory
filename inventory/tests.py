"""Test form (Phase 3.1), Create View /input (Phase 3.2), Daftar /daftar (Phase 3.3).

Fixtures dibuat sendiri — tidak bergantung pada Master Barang produksi
(17.257 record). Foto dibuat via Pillow: PNG kecil, BMP valid > 5 MB,
dan file non-gambar.

Foto yang tersimpan lewat Create View ditulis ke folder media sementara
(MEDIA_ROOT dipindah selama test) supaya tidak mengotori folder media/
project. Fixture Daftar cukup memakai path foto berbentuk string —
tidak menyentuh storage.
"""

import csv
import os
import shutil
import tempfile
from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO, StringIO

from django.core.files.storage import default_storage, storages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import Client, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
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


class DaftarTests(TestCase):
    """Test halaman Daftar /daftar (Phase 3.3: filter, search, ordering)."""

    @classmethod
    def setUpTestData(cls):
        cls.barang_indomie = Barang.objects.create(
            kode="DF001",
            nama="Indomie Goreng 85g",
            barcode_aktif="8992388101010",
            isi=1,
            h_jual=Decimal("3500.00"),
            qty_bad_stock=0,
            qty_akhir=0,
            qty_gd=0,
            sat_k="",
            sat_b="",
            pareto="A",
            jenis="BKP",
        )
        cls.barang_aqua = Barang.objects.create(
            kode="DF002",
            nama="Aqua Botol 600ml",
            barcode_aktif="8993675610019",
            isi=1,
            h_jual=Decimal("4000.00"),
            qty_bad_stock=0,
            qty_akhir=0,
            qty_gd=0,
            sat_k="",
            sat_b="",
            pareto="B",
            jenis="BKP",
        )

        cls.transaksi_void = VoidReturn.objects.create(
            jenis="VOID",
            tanggal=date(2026, 9, 20),
            outlet="BT1",
            nama_kasir="Budi Santoso",
            otoritas="Sri Wahyuni",
            barang=cls.barang_indomie,
            quantity=2,
            alasan="Kasir salah input jumlah",
            foto="foto/2026/09/void-daftar.jpg",
        )
        cls.transaksi_return = VoidReturn.objects.create(
            jenis="RETURN",
            tanggal=date(2026, 9, 21),
            outlet="BT5",
            nama_kasir="Indah Permata",
            otoritas="Rudi Hartono",
            no_trans="TRX-0001",
            barang=cls.barang_aqua,
            quantity=1,
            harga_jual=Decimal("15000.50"),
            alasan="Kemasan bocor",
            foto="foto/2026/09/return-daftar.jpg",
        )

    def test_get_daftar_menyediakan_context(self):
        response = self.client.get(reverse("inventory:daftar"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "daftar.html")
        self.assertIn("transaksi_list", response.context)
        self.assertIn("search_query", response.context)
        self.assertIn("jenis_filter", response.context)
        self.assertIn("waktu_filter", response.context)

    def test_transaksi_void_dan_return_muncul(self):
        response = self.client.get(reverse("inventory:daftar"))
        hasil = list(response.context["transaksi_list"])

        self.assertEqual(len(hasil), 2)
        self.assertIn(self.transaksi_void, hasil)
        self.assertIn(self.transaksi_return, hasil)

        # nama produk & barcode dari relasi Barang (bukan data duplikat)
        self.assertContains(response, "Indomie Goreng 85g")
        self.assertContains(response, "8992388101010")
        self.assertContains(response, "Aqua Botol 600ml")
        self.assertContains(response, "8993675610019")
        # jenis, quantity, outlet, no. trans, harga
        self.assertContains(response, "VOID")
        self.assertContains(response, "RETURN")
        self.assertContains(response, "Qty 2")
        self.assertContains(response, ">BT1<")
        self.assertContains(response, ">BT5<")
        self.assertContains(response, "TRX-0001")
        self.assertContains(response, "Rp15.000,50")

    def test_urutan_terbaru_dulu_dengan_tie_breaker_id(self):
        paling_lama = VoidReturn.objects.create(
            jenis="VOID",
            tanggal=date(2026, 9, 10),
            outlet="BT2",
            nama_kasir="Urutan",
            otoritas="Urutan",
            barang=self.barang_indomie,
            quantity=1,
            alasan="paling lama",
            foto="foto/x/urutan-lama.jpg",
        )
        tanggal_sama_1 = VoidReturn.objects.create(
            jenis="VOID",
            tanggal=date(2026, 9, 15),
            outlet="BT2",
            nama_kasir="Urutan",
            otoritas="Urutan",
            barang=self.barang_indomie,
            quantity=1,
            alasan="tanggal sama, id pertama",
            foto="foto/x/urutan-sama-1.jpg",
        )
        tanggal_sama_2 = VoidReturn.objects.create(
            jenis="VOID",
            tanggal=date(2026, 9, 15),
            outlet="BT2",
            nama_kasir="Urutan",
            otoritas="Urutan",
            barang=self.barang_indomie,
            quantity=1,
            alasan="tanggal sama, id kedua",
            foto="foto/x/urutan-sama-2.jpg",
        )

        response = self.client.get(reverse("inventory:daftar"))
        urutan = [t.pk for t in response.context["transaksi_list"]]

        self.assertEqual(
            urutan,
            [
                self.transaksi_return.pk,  # 21 Sep — terbaru
                self.transaksi_void.pk,  # 20 Sep
                tanggal_sama_2.pk,  # 15 Sep — id lebih besar menang
                tanggal_sama_1.pk,  # 15 Sep
                paling_lama.pk,  # 10 Sep — terlama
            ],
        )

    def test_filter_void(self):
        response = self.client.get(reverse("inventory:daftar"), {"jenis": "VOID"})
        hasil = list(response.context["transaksi_list"])

        self.assertEqual([t.pk for t in hasil], [self.transaksi_void.pk])
        self.assertEqual(response.context["jenis_filter"], "VOID")

    def test_filter_return(self):
        response = self.client.get(reverse("inventory:daftar"), {"jenis": "RETURN"})
        hasil = list(response.context["transaksi_list"])

        self.assertEqual([t.pk for t in hasil], [self.transaksi_return.pk])
        self.assertEqual(response.context["jenis_filter"], "RETURN")

    def test_search_nama_produk(self):
        # campur huruf besar/kecil — pencarian case-insensitive
        response = self.client.get(reverse("inventory:daftar"), {"q": "iNdOmIe"})

        self.assertEqual(
            [t.pk for t in response.context["transaksi_list"]],
            [self.transaksi_void.pk],
        )
        self.assertEqual(response.context["search_query"], "iNdOmIe")

    def test_search_barcode(self):
        # sebagian barcode saja
        response = self.client.get(reverse("inventory:daftar"), {"q": "36756100"})

        self.assertEqual(
            [t.pk for t in response.context["transaksi_list"]],
            [self.transaksi_return.pk],
        )

    def test_search_nama_kasir(self):
        response = self.client.get(reverse("inventory:daftar"), {"q": "budi"})

        self.assertEqual(
            [t.pk for t in response.context["transaksi_list"]],
            [self.transaksi_void.pk],
        )

    def test_search_no_trans(self):
        response = self.client.get(reverse("inventory:daftar"), {"q": "trx-00"})

        self.assertEqual(
            [t.pk for t in response.context["transaksi_list"]],
            [self.transaksi_return.pk],
        )

    def test_filter_dan_search_digabung_dengan_and(self):
        # positif: jenis RETURN AND barcode mengandung fragmen
        response = self.client.get(
            reverse("inventory:daftar"), {"jenis": "RETURN", "q": "36756100"}
        )
        self.assertEqual(
            [t.pk for t in response.context["transaksi_list"]],
            [self.transaksi_return.pk],
        )

        # negatif: jenis RETURN AND nama produk Indomie → kosong (bukan OR)
        response = self.client.get(
            reverse("inventory:daftar"), {"jenis": "RETURN", "q": "Indomie"}
        )
        self.assertEqual(list(response.context["transaksi_list"]), [])

    def test_filter_waktu_hari_ini(self):
        hari_ini = timezone.localdate()
        transaksi_hari_ini = VoidReturn.objects.create(
            jenis="VOID",
            tanggal=hari_ini,
            outlet="BT3",
            nama_kasir="Tepat Waktu",
            otoritas="Tepat Waktu",
            barang=self.barang_indomie,
            quantity=1,
            alasan="dibuat pada hari ini",
            foto="foto/x/waktu-hari-ini.jpg",
        )

        response = self.client.get(reverse("inventory:daftar"), {"waktu": "hari-ini"})
        hasil = list(response.context["transaksi_list"])

        self.assertIn(transaksi_hari_ini, hasil)
        self.assertTrue(all(t.tanggal == hari_ini for t in hasil))
        self.assertEqual(response.context["waktu_filter"], "hari-ini")

    def test_filter_waktu_bulan_ini(self):
        hari_ini = timezone.localdate()
        transaksi_bulan_ini = VoidReturn.objects.create(
            jenis="VOID",
            tanggal=hari_ini,
            outlet="BT3",
            nama_kasir="Bulan Ini",
            otoritas="Bulan Ini",
            barang=self.barang_indomie,
            quantity=1,
            alasan="dibuat bulan berjalan",
            foto="foto/x/waktu-bulan-ini.jpg",
        )
        transaksi_lama = VoidReturn.objects.create(
            jenis="VOID",
            tanggal=date(2000, 1, 1),
            outlet="BT3",
            nama_kasir="Bulan Lain",
            otoritas="Bulan Lain",
            barang=self.barang_indomie,
            quantity=1,
            alasan="di luar bulan berjalan",
            foto="foto/x/waktu-lama.jpg",
        )

        response = self.client.get(reverse("inventory:daftar"), {"waktu": "bulan-ini"})
        hasil = list(response.context["transaksi_list"])

        self.assertIn(transaksi_bulan_ini, hasil)
        self.assertNotIn(transaksi_lama, hasil)
        self.assertTrue(
            all(
                t.tanggal.year == hari_ini.year and t.tanggal.month == hari_ini.month
                for t in hasil
            )
        )
        self.assertEqual(response.context["waktu_filter"], "bulan-ini")

    def test_nilai_filter_tidak_valid_diabaikan(self):
        response = self.client.get(
            reverse("inventory:daftar"),
            {"jenis": "REFUND", "waktu": "kapan-saja"},
        )
        hasil = list(response.context["transaksi_list"])

        # nilai arbitrary dari GET diabaikan → semua transaksi tampil
        self.assertEqual(len(hasil), 2)
        self.assertEqual(response.context["jenis_filter"], "")
        self.assertEqual(response.context["waktu_filter"], "")

    def test_select_related_tidak_menyebabkan_n_plus_satu(self):
        with CaptureQueriesContext(connection) as sebelum:
            response = self.client.get(reverse("inventory:daftar"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["transaksi_list"]), 2)

        VoidReturn.objects.create(
            jenis="VOID",
            tanggal=date(2026, 9, 22),
            outlet="BT4",
            nama_kasir="Tambahan",
            otoritas="Tambahan",
            barang=self.barang_aqua,
            quantity=1,
            alasan="baris tambahan",
            foto="foto/x/n-plus-satu.jpg",
        )

        with CaptureQueriesContext(connection) as sesudah:
            response = self.client.get(reverse("inventory:daftar"))
        self.assertEqual(len(response.context["transaksi_list"]), 3)

        # jumlah query tetap sama meski baris bertambah → tidak ada N+1
        self.assertEqual(len(sesudah), len(sebelum))


class DaftarKosongTests(TestCase):
    """Halaman Daftar ketika belum ada transaksi (Phase 3.3)."""

    def test_empty_state_muncul(self):
        response = self.client.get(reverse("inventory:daftar"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "daftar.html")
        self.assertEqual(list(response.context["transaksi_list"]), [])
        self.assertContains(response, "Belum ada transaksi.")


class RupiahFormatTests(TestCase):
    """Format tampilan H. Jual (perbaikan: Rp14.000, bukan 14000.00)."""

    def test_format_rupiah_bulat(self):
        from inventory.templatetags.rupiah import rupiah

        self.assertEqual(rupiah(Decimal("14000.00")), "Rp14.000")
        self.assertEqual(rupiah(Decimal("15500.00")), "Rp15.500")
        self.assertEqual(rupiah(Decimal("24997.00")), "Rp24.997")

    def test_format_rupiah_desimal_dan_kosong(self):
        from inventory.templatetags.rupiah import rupiah

        self.assertEqual(rupiah(Decimal("15000.50")), "Rp15.000,50")
        self.assertEqual(rupiah(None), "—")
        self.assertEqual(rupiah(""), "—")

    def test_harga_return_tampil_dengan_format_rupiah(self):
        barang = Barang.objects.create(
            kode="RF001",
            nama="Barang Format Rupiah",
            barcode_aktif="8991111111111",
            isi=1,
            h_jual=Decimal("24997.00"),
            qty_bad_stock=0,
            qty_akhir=0,
            qty_gd=0,
            sat_k="",
            sat_b="",
            pareto="A",
            jenis="BKP",
        )
        VoidReturn.objects.create(
            jenis="RETURN",
            tanggal=date(2026, 9, 23),
            outlet="BT7",
            nama_kasir="Format Rupiah",
            otoritas="Format Rupiah",
            no_trans="TRX-FMT",
            barang=barang,
            quantity=1,
            harga_jual=Decimal("24997.00"),
            alasan="cek format harga",
            foto="foto/x/format-rupiah.jpg",
        )

        response = self.client.get(reverse("inventory:daftar"))

        self.assertContains(response, "Rp24.997")
        self.assertNotContains(response, "24997.00")


class HapusViewTests(TestCase):
    """Test Delete View POST /daftar/<pk>/hapus (Phase 3.4)."""

    @classmethod
    def setUpTestData(cls):
        cls.barang = Barang.objects.create(
            kode="DEL001",
            nama="Produk Hapus Tes",
            barcode_aktif="8997777777777",
            isi=1,
            h_jual=Decimal("12000.00"),
            qty_bad_stock=0,
            qty_akhir=0,
            qty_gd=0,
            sat_k="",
            sat_b="",
            pareto="A",
            jenis="BKP",
        )
        cls.transaksi_void = VoidReturn.objects.create(
            jenis="VOID",
            tanggal=date(2026, 9, 24),
            outlet="BT4",
            nama_kasir="Hapus Tes",
            otoritas="Hapus Tes",
            barang=cls.barang,
            quantity=1,
            alasan="dihapus lewat POST",
            foto="foto/hapus/void-fixture.jpg",
        )
        cls.transaksi_return = VoidReturn.objects.create(
            jenis="RETURN",
            tanggal=date(2026, 9, 25),
            outlet="BT6",
            nama_kasir="Hapus Tes",
            otoritas="Hapus Tes",
            no_trans="TRX-DEL",
            barang=cls.barang,
            quantity=2,
            harga_jual=Decimal("12000.00"),
            alasan="tetap ada",
            foto="foto/hapus/return-fixture.jpg",
        )

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        _dir = os.path.join(tempfile.gettempdir(), "opencode")
        cls.media_dir = tempfile.mkdtemp(
            prefix="voidreturn_hapus_media_", dir=_dir if os.path.isdir(_dir) else None
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

    def url_hapus(self, pk):
        return reverse("inventory:hapus_transaksi", args=[pk])

    def test_post_delete_menghapus_transaksi_dan_redirect(self):
        response = self.client.post(self.url_hapus(self.transaksi_void.pk))

        # redirect ke daftar (bukan render langsung)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("inventory:daftar"))

        self.assertFalse(
            VoidReturn.objects.filter(pk=self.transaksi_void.pk).exists()
        )
        # transaksi lain tidak ikut terhapus
        self.assertEqual(VoidReturn.objects.count(), 1)

    def test_success_message_muncul_setelah_delete(self):
        response = self.client.post(
            self.url_hapus(self.transaksi_void.pk), follow=True
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Transaksi berhasil dihapus.")

    def test_master_barang_tidak_ikut_terhapus(self):
        self.client.post(self.url_hapus(self.transaksi_void.pk))
        self.client.post(self.url_hapus(self.transaksi_return.pk))

        self.assertEqual(VoidReturn.objects.count(), 0)
        self.assertTrue(Barang.objects.filter(pk=self.barang.pk).exists())

    def test_get_tidak_menghapus_transaksi(self):
        response = self.client.get(self.url_hapus(self.transaksi_void.pk))

        # require_POST -> 405 Method Not Allowed, data tetap utuh
        self.assertEqual(response.status_code, 405)
        self.assertTrue(
            VoidReturn.objects.filter(pk=self.transaksi_void.pk).exists()
        )

    def test_transaksi_tidak_ditemukan_404(self):
        response = self.client.post(self.url_hapus(999999))

        self.assertEqual(response.status_code, 404)
        self.assertEqual(VoidReturn.objects.count(), 2)

    def test_csrf_terlindungi(self):
        client = Client(enforce_csrf_checks=True)
        response = client.post(self.url_hapus(self.transaksi_void.pk))

        self.assertEqual(response.status_code, 403)
        self.assertTrue(
            VoidReturn.objects.filter(pk=self.transaksi_void.pk).exists()
        )

    def test_daftar_menampilkan_form_delete(self):
        response = self.client.get(reverse("inventory:daftar"))
        url_void = self.url_hapus(self.transaksi_void.pk)
        url_return = self.url_hapus(self.transaksi_return.pk)

        self.assertContains(response, 'method="post"')
        self.assertContains(response, "csrfmiddlewaretoken")
        # form delete menunjuk ke pk transaksi yang benar (tabel + kartu mobile)
        self.assertContains(response, f'action="{url_void}"')
        self.assertContains(response, f'action="{url_return}"')
        # konfirmasi sederhana tanpa arsitektur JS tambahan
        self.assertContains(response, "return confirm(")
        # placeholder tombol tanpa aksi sudah tidak ada
        self.assertNotContains(
            response, '<button type="button" class="text-xs font-semibold text-rose-600'
        )

    def test_foto_transaksi_ikut_dihapus_dan_transaksi_lain_aman(self):
        # buat file foto nyata di MEDIA_ROOT sementara
        nama_void = default_storage.save("foto/hapus/void-nyata.png", foto_kecil())
        nama_return = default_storage.save(
            "foto/hapus/return-nyata.png", foto_kecil()
        )
        VoidReturn.objects.filter(pk=self.transaksi_void.pk).update(foto=nama_void)
        VoidReturn.objects.filter(pk=self.transaksi_return.pk).update(
            foto=nama_return
        )
        self.assertTrue(default_storage.exists(nama_void))
        self.assertTrue(default_storage.exists(nama_return))

        response = self.client.post(self.url_hapus(self.transaksi_void.pk))

        self.assertEqual(response.status_code, 302)
        self.assertFalse(default_storage.exists(nama_void))  # foto ikut dibersihkan
        # foto & record transaksi lain tidak tersentuh
        self.assertTrue(default_storage.exists(nama_return))
        self.assertTrue(
            VoidReturn.objects.filter(pk=self.transaksi_return.pk).exists()
        )

    def test_foto_dipakai_transaksi_lain_tidak_dihapus(self):
        nama = default_storage.save("foto/hapus/bersama.png", foto_kecil())
        VoidReturn.objects.filter(pk=self.transaksi_void.pk).update(foto=nama)
        VoidReturn.objects.filter(pk=self.transaksi_return.pk).update(foto=nama)

        self.client.post(self.url_hapus(self.transaksi_void.pk))

        # nama file masih dirujuk transaksi lain -> file dibiarkan
        self.assertFalse(
            VoidReturn.objects.filter(pk=self.transaksi_void.pk).exists()
        )
        self.assertTrue(default_storage.exists(nama))

    def test_hapus_berhasil_meski_file_foto_sudah_tidak_ada(self):
        # fixture memakai path yang tidak ada fisiknya; storage.delete
        # menelan FileNotFoundError -> tetap sukses
        response = self.client.post(self.url_hapus(self.transaksi_void.pk))

        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            VoidReturn.objects.filter(pk=self.transaksi_void.pk).exists()
        )
        self.assertEqual(VoidReturn.objects.count(), 1)


# Header CSV ditulis literal (bukan diimpor dari views) agar test mengunci
# spesifikasi requirement, bukan sekadar mengulang konstanta implementasi.
HEADER_VOID_PERSIS = [
    "NO", "OUTLET", "TANGGAL", "NAMA PRODUK", "BARCODE",
    "QTY", "KASIR", "OTORITAS", "ALASAN VOID",
]
HEADER_RETURN_PERSIS = [
    "TANGGAL", "OUTLET", "NAMA KASIR", "NO.TRANS", "NAMA PRODUK",
    "BARCODE", "QTY", "H.JUAL", "OTORITAS", "ALASAN RETURN",
]


class ExportCsvTests(TestCase):
    """Test Export CSV /daftar/export/void & /daftar/export/return (Phase 3.5)."""

    @classmethod
    def setUpTestData(cls):
        cls.barang_a = Barang.objects.create(
            kode="EXP001",
            nama="Indomie Goreng 85g",
            barcode_aktif="8991111111111",
            isi=1,
            h_jual=Decimal("3500.00"),
            qty_bad_stock=0,
            qty_akhir=0,
            qty_gd=0,
            sat_k="",
            sat_b="",
            pareto="A",
            jenis="BKP",
        )
        cls.barang_b = Barang.objects.create(
            kode="EXP002",
            nama='Chitato Sapi "Panggang" 68g',  # kutip ganda di nama produk
            barcode_aktif="8992222222222",
            isi=1,
            h_jual=Decimal("12500.00"),
            qty_bad_stock=0,
            qty_akhir=0,
            qty_gd=0,
            sat_k="",
            sat_b="",
            pareto="A",
            jenis="BKP",
        )

        # VOID — dua data (beda tanggal) supaya nomor urut & ordering bisa diuji.
        cls.void_baru = VoidReturn.objects.create(
            jenis="VOID",
            tanggal=date(2026, 9, 25),
            outlet="BT2",
            nama_kasir="Budi, Santoso",  # koma di dalam nilai
            otoritas="Andi Wijaya",
            barang=cls.barang_a,
            quantity=2,
            alasan='Salah pindai, "ganda" — komplain ñiño',
            foto="foto/exp/void-baru.jpg",
        )
        cls.void_lama = VoidReturn.objects.create(
            jenis="VOID",
            tanggal=date(2026, 9, 20),
            outlet="BT5",
            nama_kasir="Rina",
            otoritas="MOD Rina",
            barang=cls.barang_b,
            quantity=1,
            alasan="Kedaluwarsa",
            foto="foto/exp/void-lama.jpg",
        )

        # RETURN — satu dengan no_trans, satu no_trans kosong (NULL).
        cls.ret_no_trans = VoidReturn.objects.create(
            jenis="RETURN",
            tanggal=date(2026, 9, 24),
            outlet="BT7",
            nama_kasir="Dewi",
            otoritas="Hadi Kurnia",
            no_trans="TRX-0099",
            barang=cls.barang_a,
            quantity=1,
            harga_jual=Decimal("9999.50"),
            alasan='Salah kirim, "cek lagi"',
            foto="foto/exp/ret-no.jpg",
        )
        cls.ret_tanpa_no = VoidReturn.objects.create(
            jenis="RETURN",
            tanggal=date(2026, 9, 26),
            outlet="BT3",
            nama_kasir="Siti, Aminah",
            otoritas="Hadi Kurnia",
            no_trans=None,
            barang=cls.barang_b,
            quantity=3,
            harga_jual=Decimal("12500.00"),
            alasan="Rusak berat",
            foto="foto/exp/ret-tanpa.jpg",
        )

    def ambil_csv(self, nama_url):
        """GET endpoint export -> (response, teks tanpa BOM, baris csv)."""
        response = self.client.get(reverse(nama_url))
        teks = response.content.decode("utf-8-sig")
        return response, teks, list(csv.reader(StringIO(teks)))

    # --- Export Void -----------------------------------------------------

    def test_void_status_dan_content_type(self):
        response, _, _ = self.ambil_csv("inventory:export_void")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")

    def test_void_content_disposition_dan_filename(self):
        response, _, _ = self.ambil_csv("inventory:export_void")
        hari_ini = timezone.localdate().isoformat()

        disposition = response["Content-Disposition"]
        self.assertIn("attachment", disposition)
        self.assertIn(f'filename="laporan-void-{hari_ini}.csv"', disposition)

    def test_void_header_persis(self):
        _, _, baris = self.ambil_csv("inventory:export_void")

        self.assertEqual(baris[0], HEADER_VOID_PERSIS)

    def test_void_hanya_berisi_transaksi_void(self):
        _, teks, baris = self.ambil_csv("inventory:export_void")

        # dua transaksi VOID -> header + 2 baris data
        self.assertEqual(len(baris), 3)
        # penanda khusus data RETURN tidak boleh muncul
        self.assertNotIn("TRX-0099", teks)
        self.assertNotIn("Siti, Aminah", teks)
        self.assertNotIn("Rusak berat", teks)

    def test_void_isi_baris_lengkap(self):
        _, _, baris = self.ambil_csv("inventory:export_void")

        self.assertEqual(
            baris[1],
            [
                "1",                       # NO (nomor urut laporan)
                "BT2",                     # OUTLET
                "2026-09-25",              # TANGGAL
                "Indomie Goreng 85g",      # NAMA PRODUK (dari relasi Barang)
                "8991111111111",           # BARCODE
                "2",                       # QTY
                "Budi, Santoso",           # KASIR
                "Andi Wijaya",             # OTORITAS
                'Salah pindai, "ganda" — komplain ñiño',  # ALASAN VOID
            ],
        )
        self.assertEqual(
            baris[2],
            [
                "2", "BT5", "2026-09-20",
                'Chitato Sapi "Panggang" 68g',
                "8992222222222", "1", "Rina", "MOD Rina", "Kedaluwarsa",
            ],
        )

    def test_void_nomor_urut_berurutan_dari_satu(self):
        _, _, baris = self.ambil_csv("inventory:export_void")

        self.assertEqual(baris[1][0], "1")
        self.assertEqual(baris[2][0], "2")

    def test_void_tidak_mengikuti_filter_daftar(self):
        # parameter filter/search daftar tidak boleh memengaruhi export
        response = self.client.get(
            reverse("inventory:export_void"),
            {"q": "Siti", "jenis": "RETURN", "waktu": "hari-ini"},
        )
        baris = list(csv.reader(StringIO(response.content.decode("utf-8-sig"))))

        self.assertEqual(len(baris), 3)  # seluruh VOID tetap ikut

    # --- Export Return ---------------------------------------------------

    def test_return_status_dan_content_type(self):
        response, _, _ = self.ambil_csv("inventory:export_return")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")

    def test_return_content_disposition_dan_filename(self):
        response, _, _ = self.ambil_csv("inventory:export_return")
        hari_ini = timezone.localdate().isoformat()

        disposition = response["Content-Disposition"]
        self.assertIn("attachment", disposition)
        self.assertIn(f'filename="laporan-return-{hari_ini}.csv"', disposition)

    def test_return_header_persis(self):
        _, _, baris = self.ambil_csv("inventory:export_return")

        self.assertEqual(baris[0], HEADER_RETURN_PERSIS)

    def test_return_hanya_berisi_transaksi_return(self):
        _, teks, baris = self.ambil_csv("inventory:export_return")

        self.assertEqual(len(baris), 3)  # header + 2 data RETURN
        # penanda khusus data VOID tidak boleh muncul
        self.assertNotIn("Budi, Santoso", teks)
        self.assertNotIn("Kedaluwarsa", teks)
        self.assertNotIn("MOD Rina", teks)

    def test_return_isi_baris_lengkap(self):
        _, _, baris = self.ambil_csv("inventory:export_return")

        self.assertEqual(
            baris[1],
            [
                "2026-09-26",              # TANGGAL (terbaru dulu)
                "BT3",                     # OUTLET
                "Siti, Aminah",            # NAMA KASIR
                "",                        # NO.TRANS kosong (NULL)
                'Chitato Sapi "Panggang" 68g',
                "8992222222222",
                "3",                       # QTY
                "12500.00",                # H.JUAL (input manual)
                "Hadi Kurnia",             # OTORITAS
                "Rusak berat",             # ALASAN RETURN
            ],
        )
        self.assertEqual(
            baris[2],
            [
                "2026-09-24", "BT7", "Dewi", "TRX-0099",
                "Indomie Goreng 85g", "8991111111111", "1",
                "9999.50", "Hadi Kurnia", 'Salah kirim, "cek lagi"',
            ],
        )

    # --- Korrectness CSV -------------------------------------------------

    def test_koma_dalam_nilai_tetap_satu_kolom(self):
        _, _, baris_void = self.ambil_csv("inventory:export_void")
        _, _, baris_return = self.ambil_csv("inventory:export_return")

        # setiap baris harus selebar header (koma tidak memecah kolom)
        for baris in baris_void:
            self.assertEqual(len(baris), len(HEADER_VOID_PERSIS))
        for baris in baris_return:
            self.assertEqual(len(baris), len(HEADER_RETURN_PERSIS))

        # nilai "Budi, Santoso" utuh sebagai satu sel
        self.assertEqual(baris_void[1][6], "Budi, Santoso")
        self.assertEqual(baris_return[1][2], "Siti, Aminah")

    def test_tanda_kutip_di_escape_dengan_benar(self):
        response, teks, baris = self.ambil_csv("inventory:export_void")

        # csv.writer menggandakan kutip di dalam field berquote
        self.assertIn('""ganda""', teks)
        # setelah dibaca ulang, nilai kembali persis seperti aslinya
        self.assertEqual(
            baris[1][8], 'Salah pindai, "ganda" — komplain ñiño'
        )
        # nama produk berkutip juga ikut ter-escape & terbaca benar
        self.assertEqual(baris[2][3], 'Chitato Sapi "Panggang" 68g')

    def test_nilai_kosong_tidak_merusak_format(self):
        _, _, baris = self.ambil_csv("inventory:export_return")

        # no_trans NULL -> sel kosong, jumlah kolom tetap utuh
        self.assertEqual(baris[1][3], "")
        self.assertEqual(len(baris[1]), len(HEADER_RETURN_PERSIS))

    def test_karakter_utf8_benar_dengan_bom(self):
        response, teks, baris = self.ambil_csv("inventory:export_void")

        # diawali UTF-8 BOM (setara utf-8-sig) untuk Excel
        self.assertTrue(response.content.startswith(b"\xef\xbb\xbf"))
        # karakter non-ASCII terbaca utuh setelah decode utf-8-sig
        self.assertIn("ñiño", teks)
        self.assertIn("—", teks)
        self.assertIn("ñiño", baris[1][8])

    # --- Template --------------------------------------------------------

    def test_daftar_menampilkan_tombol_export_void(self):
        response = self.client.get(reverse("inventory:daftar"))

        self.assertContains(response, f'href="{reverse("inventory:export_void")}"')
        self.assertContains(response, "Export Void")

    def test_daftar_menampilkan_tombol_export_return(self):
        response = self.client.get(reverse("inventory:daftar"))

        self.assertContains(
            response, f'href="{reverse("inventory:export_return")}"'
        )
        self.assertContains(response, "Export Return")
        # placeholder tombol tanpa aksi sudah tidak ada
        self.assertNotContains(
            response, 'type="button" class="flex-1 sm:flex-none'
        )


class ExportKosongTests(TestCase):
    """Export tanpa data tetap menghasilkan CSV valid berisi header (Phase 3.5)."""

    def test_export_void_kosong_hanya_header(self):
        response = self.client.get(reverse("inventory:export_void"))
        baris = list(
            csv.reader(StringIO(response.content.decode("utf-8-sig")))
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        self.assertEqual(baris, [HEADER_VOID_PERSIS])

    def test_export_return_kosong_hanya_header(self):
        response = self.client.get(reverse("inventory:export_return"))
        baris = list(
            csv.reader(StringIO(response.content.decode("utf-8-sig")))
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        self.assertEqual(baris, [HEADER_RETURN_PERSIS])


class BarcodeLookupTests(TestCase):
    """Test endpoint AJAX lookup /barcode/<barcode> (Phase 3.6)."""

    @classmethod
    def setUpTestData(cls):
        cls.barang = Barang.objects.create(
            kode="AJX001",
            nama="YZ BROS / BEAUTY BROS",
            barcode_aktif="1000000020",
            isi=1,
            h_jual=Decimal("5000.00"),
            qty_bad_stock=0,
            qty_akhir=0,
            qty_gd=0,
            sat_k="",
            sat_b="",
            pareto="A",
            jenis="BKP",
        )
        cls.barang_nol = Barang.objects.create(
            kode="AJX002",
            nama="Produk Leading Zero",
            barcode_aktif="001234567890",  # leading zero, wajib tetap string
            isi=1,
            h_jual=Decimal("7500.00"),
            qty_bad_stock=0,
            qty_akhir=0,
            qty_gd=0,
            sat_k="",
            sat_b="",
            pareto="B",
            jenis="BKP",
        )

    def url(self, barcode):
        return reverse("inventory:barcode_lookup", args=[barcode])

    def test_barcode_valid_get_200_dan_json(self):
        response = self.client.get(self.url("1000000020"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Type"].startswith("application/json"))
        self.assertJSONEqual(
            response.content,
            {"found": True, "barcode": "1000000020", "nama": "YZ BROS / BEAUTY BROS"},
        )

    def test_barcode_tidak_ditemukan_found_false_bukan_500(self):
        response = self.client.get(self.url("9999999999999"))

        # tidak ditemukan = kondisi bisnis normal, bukan error server
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            response.content,
            {"found": False, "barcode": "9999999999999"},
        )

    def test_barcode_leading_zero_tetap_string(self):
        # record dengan leading zero tetap ditemukan
        response = self.client.get(self.url("001234567890"))

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            response.content,
            {"found": True, "barcode": "001234567890", "nama": "Produk Leading Zero"},
        )

        # versi tanpa leading zero TIDAK ditemukan -> bukan cast integer,
        # bukan pencarian fuzzy
        response = self.client.get(self.url("1234567890"))

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            response.content, {"found": False, "barcode": "1234567890"}
        )

    def test_barcode_kosong_tanpa_query_database(self):
        with self.assertNumQueries(0):
            response = self.client.get(self.url(""))

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"found": False, "barcode": ""})

    def test_post_ditolak_dan_tidak_mengubah_database(self):
        jumlah_void = VoidReturn.objects.count()
        jumlah_barang = Barang.objects.count()

        response = self.client.post(self.url("1000000020"))

        # lookup read-only: method selain GET ditolak, data tetap utuh
        self.assertEqual(response.status_code, 405)
        self.assertEqual(VoidReturn.objects.count(), jumlah_void)
        self.assertEqual(Barang.objects.count(), jumlah_barang)

    def test_get_tidak_membuat_transaksi_dan_tidak_mengubah_barang(self):
        sebelum = Barang.objects.get(pk=self.barang.pk)

        response = self.client.get(self.url("1000000020"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(VoidReturn.objects.count(), 0)  # tidak membuat transaksi
        sesudah = Barang.objects.get(pk=self.barang.pk)
        self.assertEqual(sesudah.nama, sebelum.nama)
        self.assertEqual(sesudah.barcode_aktif, sebelum.barcode_aktif)
        self.assertEqual(sesudah.h_jual, sebelum.h_jual)

    def test_struktur_json_konsisten(self):
        ditemukan = self.client.get(self.url("1000000020")).json()
        tidak_ditemukan = self.client.get(self.url("9999999999999")).json()

        self.assertEqual(set(ditemukan.keys()), {"found", "barcode", "nama"})
        self.assertEqual(set(tidak_ditemukan.keys()), {"found", "barcode"})
        self.assertIs(ditemukan["found"], True)
        self.assertIs(tidak_ditemukan["found"], False)

    def test_template_input_memuat_js_dan_url_lookup(self):
        response = self.client.get(reverse("inventory:input"))

        # memakai file JS existing (tanpa file duplikat)
        self.assertContains(response, "js/input.js")
        # URL dirender Django dengan placeholder (tanpa hard-code host)
        self.assertContains(
            response,
            'data-url-template="%s"'
            % reverse("inventory:barcode_lookup", args=["__BARCODE__"]),
        )
        # elemen feedback status ada untuk loading/error
        self.assertContains(response, 'id="status-barcode"')


class DashboardKosongTests(TestCase):
    """Dashboard Phase 8 ketika database transaksi kosong (empty state).

    Seluruh statistik harus 0, chart aman tanpa pembagian nol,
    empty state tampil, dan tidak ada lagi data dummy prototype.
    """

    def setUp(self):
        self.response = self.client.get(reverse("inventory:dashboard"))
        self.ctx = self.response.context

    def test_dashboard_200_dan_seluruh_statistik_nol(self):
        self.assertEqual(self.response.status_code, 200)
        for kunci in (
            "jumlah_void_hari_ini",
            "jumlah_return_hari_ini",
            "jumlah_transaksi_hari_ini",
            "jumlah_quantity_hari_ini",
            "quantity_void_hari_ini",
            "quantity_return_hari_ini",
            "jumlah_void_bulan_ini",
            "jumlah_return_bulan_ini",
            "jumlah_transaksi_bulan_ini",
            "jumlah_transaksi",
            "jumlah_quantity_total",
        ):
            self.assertEqual(self.ctx[kunci], 0, f"{kunci} harus 0")
        self.assertEqual(self.ctx["persen_void_bulan_ini"], 0)
        self.assertEqual(self.ctx["persen_return_bulan_ini"], 0)
        self.assertEqual(list(self.ctx["barang_paling_sering"]), [])
        self.assertEqual(list(self.ctx["entri_terbaru"]), [])

    def test_chart_nol_transaksi_tanpa_pembagian_nol(self):
        """Total bulan ini = 0 -> 0%/0%, tanpa NaN/Infinity/error template."""
        self.assertEqual(self.ctx["persen_void_bulan_ini"], 0)
        self.assertEqual(self.ctx["persen_return_bulan_ini"], 0)
        html = self.response.content.decode()
        self.assertNotIn("NaN", html)
        self.assertNotIn("Infinity", html)
        self.assertContains(self.response, "width:0%")

    def test_empty_state_entri_dan_barang_paling_sering(self):
        self.assertContains(self.response, "Belum ada transaksi.")
        self.assertContains(self.response, "Belum ada transaksi bulan ini.")

    def test_tidak_ada_data_dummy_lagi(self):
        html = self.response.content.decode()
        for dummy in (
            "Indomie Goreng 85g",
            "Aqua Botol 600ml",
            "Teh Pucuk Harum",
            "45 entri bulan ini",
            "156 data tersimpan",
            "45 pcs barang",
            "28 pcs dibatalkan",
            "17 pcs dikembalikan",
            "532 pcs sepanjang waktu",
            "width:62%",
            "width:38%",
        ):
            self.assertNotIn(dummy, html, f"data dummy '{dummy}' masih tampil")

    def test_tanggal_tetap_dinamis(self):
        """Judul tanggal memakai tanggal hari ini (Asia/Jakarta)."""
        self.assertContains(
            self.response, timezone.localdate().strftime("%d %B %Y")
        )


class DashboardTests(TestCase):
    """Dashboard Phase 8 dengan data transaksi aktual dari database."""

    @classmethod
    def setUpTestData(cls):
        cls.hari_ini = timezone.localdate()
        katalog = (
            ("DB001", "Produk Alpha Dashboard", "9000000000001", "A"),
            ("DB002", "Produk Beta Dashboard", "9000000000002", "B"),
            ("DB003", "Produk Cema Dashboard", "9000000000003", "C"),
        )
        cls.barang_alpha = Barang.objects.create(
            kode=katalog[0][0], nama=katalog[0][1], barcode_aktif=katalog[0][2],
            isi=1, h_jual=Decimal("10000.00"), qty_bad_stock=0, qty_akhir=0,
            qty_gd=0, sat_k="", sat_b="", pareto=katalog[0][3], jenis="BKP",
        )
        cls.barang_beta = Barang.objects.create(
            kode=katalog[1][0], nama=katalog[1][1], barcode_aktif=katalog[1][2],
            isi=1, h_jual=Decimal("20000.00"), qty_bad_stock=0, qty_akhir=0,
            qty_gd=0, sat_k="", sat_b="", pareto=katalog[1][3], jenis="BKP",
        )
        cls.barang_cema = Barang.objects.create(
            kode=katalog[2][0], nama=katalog[2][1], barcode_aktif=katalog[2][2],
            isi=1, h_jual=Decimal("30000.00"), qty_bad_stock=0, qty_akhir=0,
            qty_gd=0, sat_k="", sat_b="", pareto=katalog[2][3], jenis="BKP",
        )

    def _buat(self, jenis, tanggal, barang, quantity, **tambahan):
        """Buat transaksi test (hanya di database test, bukan produksi)."""
        data = {
            "jenis": jenis,
            "tanggal": tanggal,
            "outlet": "BT1",
            "nama_kasir": "Sari Wijaya",
            "otoritas": "MOD Satu",
            "barang": barang,
            "quantity": quantity,
            "alasan": "Transaksi uji dashboard",
            "foto": "foto/2026/09/dashboard.jpg",
        }
        if jenis == "RETURN":
            data["harga_jual"] = Decimal("10000.00")
        data.update(tambahan)
        return VoidReturn.objects.create(**data)

    def _GET(self):
        response = self.client.get(reverse("inventory:dashboard"))
        self.assertEqual(response.status_code, 200)
        return response, response.context

    def test_statistik_hari_ini(self):
        """VOID qty2 + VOID qty3 + RETURN qty4 -> void 2, return 1, total 3, qty 9."""
        self._buat("VOID", self.hari_ini, self.barang_alpha, 2)
        self._buat("VOID", self.hari_ini, self.barang_alpha, 3)
        self._buat("RETURN", self.hari_ini, self.barang_beta, 4)
        _, ctx = self._GET()
        self.assertEqual(ctx["jumlah_void_hari_ini"], 2)
        self.assertEqual(ctx["jumlah_return_hari_ini"], 1)
        self.assertEqual(ctx["jumlah_transaksi_hari_ini"], 3)
        self.assertEqual(ctx["jumlah_quantity_hari_ini"], 9)

    def test_transaksi_hari_lain_tidak_masuk_statistik_hari_ini(self):
        self._buat("VOID", self.hari_ini, self.barang_alpha, 2)
        kemarin = self.hari_ini - timedelta(days=1)
        self._buat("RETURN", kemarin, self.barang_beta, 50)
        _, ctx = self._GET()
        self.assertEqual(ctx["jumlah_void_hari_ini"], 1)
        self.assertEqual(ctx["jumlah_return_hari_ini"], 0)
        self.assertEqual(ctx["jumlah_transaksi_hari_ini"], 1)
        self.assertEqual(ctx["jumlah_quantity_hari_ini"], 2)

    def test_transaksi_bulan_lalu_tidak_masuk_periode_bulan_ini(self):
        # qty sengaja besar supaya menang jika ikut terhitung
        if self.hari_ini.month == 1:
            bulan_lalu = date(self.hari_ini.year - 1, 12, 15)
        else:
            bulan_lalu = date(self.hari_ini.year, self.hari_ini.month - 1, 15)
        self._buat("VOID", bulan_lalu, self.barang_cema, 100)
        self._buat("VOID", self.hari_ini, self.barang_alpha, 2)
        self._buat("RETURN", self.hari_ini, self.barang_beta, 4)
        _, ctx = self._GET()
        # chart bulan ini hanya memuat transaksi bulan berjalan
        self.assertEqual(ctx["jumlah_void_bulan_ini"], 1)
        self.assertEqual(ctx["jumlah_return_bulan_ini"], 1)
        self.assertEqual(ctx["jumlah_transaksi_bulan_ini"], 2)
        # barang bulan lalu tidak masuk "Barang paling sering bulan ini"
        nama = [b["nama"] for b in ctx["barang_paling_sering"]]
        self.assertNotIn(self.barang_cema.nama, nama)
        self.assertIn(self.barang_alpha.nama, nama)
        self.assertIn(self.barang_beta.nama, nama)

    def test_entri_terbaru_maksimal_5_terurut_tanggal_desc_id_desc(self):
        kemarin = self.hari_ini - timedelta(days=1)
        lusa = self.hari_ini - timedelta(days=2)
        urutan_buat = [
            self._buat("VOID", lusa, self.barang_alpha, 1).pk,
            self._buat("VOID", kemarin, self.barang_alpha, 1).pk,
            self._buat("RETURN", kemarin, self.barang_beta, 1).pk,
            self._buat("VOID", kemarin, self.barang_beta, 1).pk,
            self._buat("VOID", self.hari_ini, self.barang_alpha, 1).pk,
            self._buat("RETURN", self.hari_ini, self.barang_cema, 1).pk,
        ]
        _, ctx = self._GET()
        terbaru = list(ctx["entri_terbaru"])
        # 6 transaksi dibuat -> hanya 5 yang tampil
        self.assertEqual(len(terbaru), 5)
        # urutan: tanggal DESC, lalu id DESC (tie-break pada tanggal sama)
        self.assertEqual(
            [t.pk for t in terbaru],
            [urutan_buat[5], urutan_buat[4], urutan_buat[3],
             urutan_buat[2], urutan_buat[1]],
        )

    def test_entri_terbaru_tanpa_n_plus_satu(self):
        with CaptureQueriesContext(connection) as sedikit:
            self.client.get(reverse("inventory:dashboard"))
        kemarin = self.hari_ini - timedelta(days=1)
        for i in range(5):
            self._buat(
                "VOID" if i % 2 else "RETURN",
                kemarin if i % 2 else self.hari_ini,
                self.barang_alpha,
                1,
            )
        with CaptureQueriesContext(connection) as banyak:
            response, ctx = self._GET()
        self.assertEqual(len(list(ctx["entri_terbaru"])), 5)
        # jumlah query tetap meski baris bertambah -> select_related, tanpa N+1
        self.assertEqual(len(banyak), len(sedikit))

    def test_barang_paling_sering_pakai_sum_quantity_bukan_count(self):
        # Alpha: 2 transaksi, total qty 2 (count menang, sum kalah)
        self._buat("VOID", self.hari_ini, self.barang_alpha, 1)
        self._buat("RETURN", self.hari_ini, self.barang_alpha, 1)
        # Beta: 1 transaksi, total qty 3 -> menang karena SUM
        self._buat("VOID", self.hari_ini, self.barang_beta, 3)
        # Cema: sum sama dengan Beta (3) -> tie-break deterministic: nama
        self._buat("VOID", self.hari_ini, self.barang_cema, 3)
        _, ctx = self._GET()
        peringkat = list(ctx["barang_paling_sering"])
        self.assertEqual(
            [b["nama"] for b in peringkat],
            [self.barang_beta.nama, self.barang_cema.nama, self.barang_alpha.nama],
        )
        self.assertEqual([b["jumlah"] for b in peringkat], [3, 3, 2])
        # bar lebar relatif terhadap top (maks 3): 100%, 100%, 67%
        self.assertEqual([b["persen"] for b in peringkat], [100, 100, 67])

    def test_chart_void_return_bulan_ini_dan_persen(self):
        self._buat("VOID", self.hari_ini, self.barang_alpha, 2)
        self._buat("VOID", self.hari_ini, self.barang_beta, 1)
        self._buat("RETURN", self.hari_ini, self.barang_cema, 4)
        response, ctx = self._GET()
        self.assertEqual(ctx["jumlah_void_bulan_ini"], 2)
        self.assertEqual(ctx["jumlah_return_bulan_ini"], 1)
        self.assertEqual(ctx["jumlah_transaksi_bulan_ini"], 3)
        self.assertEqual(ctx["persen_void_bulan_ini"], 67)
        self.assertEqual(ctx["persen_return_bulan_ini"], 33)
        self.assertContains(response, "width:67%")
        self.assertContains(response, "width:33%")

    def test_pintasan_memakai_angka_dari_database(self):
        self._buat("VOID", self.hari_ini, self.barang_alpha, 2)
        self._buat("RETURN", self.hari_ini, self.barang_beta, 1)
        self._buat("VOID", self.hari_ini - timedelta(days=1), self.barang_cema, 3)
        response, ctx = self._GET()
        # angka pintasan diambil dari context, bukan hard-coded
        self.assertEqual(ctx["jumlah_transaksi"], 3)
        self.assertContains(response, f"{ctx['jumlah_transaksi']} data tersimpan")
        self.assertContains(
            response, f"{ctx['jumlah_transaksi_bulan_ini']} entri bulan ini"
        )
        html = response.content.decode()
        self.assertNotIn("45 entri bulan ini", html)
        self.assertNotIn("156 data tersimpan", html)

    def test_kartu_hari_ini_render_angka_aktual(self):
        self._buat("VOID", self.hari_ini, self.barang_alpha, 2)
        self._buat("VOID", self.hari_ini, self.barang_beta, 3)
        self._buat("RETURN", self.hari_ini, self.barang_cema, 4)
        response, ctx = self._GET()
        self.assertEqual(ctx["jumlah_transaksi_hari_ini"], 3)
        self.assertEqual(ctx["jumlah_quantity_hari_ini"], 9)
        self.assertEqual(ctx["quantity_void_hari_ini"], 5)
        self.assertEqual(ctx["quantity_return_hari_ini"], 4)
        html = response.content.decode()
        self.assertContains(response, "9 pcs barang")
        self.assertContains(response, "5 pcs dibatalkan")
        self.assertContains(response, "4 pcs dikembalikan")
        self.assertNotIn("45 pcs barang", html)
        self.assertNotIn("532 pcs sepanjang waktu", html)
