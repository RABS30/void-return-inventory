"""Test form (Phase 3.1), Create View /input (Phase 3.2), Daftar /daftar (Phase 3.3).

Fixtures dibuat sendiri — tidak bergantung pada Master Barang produksi
(17.257 record). Foto dibuat via Pillow: PNG kecil, BMP valid > 5 MB,
dan file non-gambar.

Foto yang tersimpan lewat Create View ditulis ke folder media sementara
(MEDIA_ROOT dipindah selama test) supaya tidak mengotori folder media/
project. Fixture Daftar cukup memakai path foto berbentuk string —
tidak menyentuh storage.
"""

import os
import shutil
import tempfile
from datetime import date
from decimal import Decimal
from io import BytesIO

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
