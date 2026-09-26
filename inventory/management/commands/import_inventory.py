"""Import Master Barang dari inventory.csv (sumber resmi) ke model Barang.

Ini adalah pemuatan data awal (initial/master-data loading) melalui management
command internal — BUKAN fitur CSV import untuk user (fitur tersebut di luar V1).

Prinsip:
- akses kolom BERBASIS NAMA header (bukan posisi/index), sehingga kolom
  pertama yang tanpa nama dan kolom lain yang tidak dimodelkan tidak mengganggu;
- seluruh baris divalidasi DULU, baru ditulis — galat apa pun membatalkan
  seluruh proses (tidak ada baris yang dilewati diam-diam);
- transaction.atomic: gagal = rollback total, tidak ada data setengah jadi;
- tidak destructive: batal bila tabel Barang sudah berisi data
  (tanpa mode --replace/--clear pada phase ini).
"""

import csv
import io
import re
import time
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from inventory.models import Barang

# 12 kolom requirement — urutan tidak berpengaruh karena akses berbasis nama
KOLOM_WAJIB = (
    "Kode",
    "Nama",
    "BarcodeAktif",
    "Isi",
    "HJual",
    "QtyBadStock",
    "QtyAkhir",
    "QtyGD",
    "SatK",
    "SatB",
    "Pareto",
    "Jenis",
)

# (kolom CSV, field model, max_length) — teks yang wajib terisi sesuai model
TEKS_WAJIB = (
    ("Kode", "kode", 50),
    ("Nama", "nama", 255),
    ("BarcodeAktif", "barcode_aktif", 50),
    ("Pareto", "pareto", 16),
    ("Jenis", "jenis", 32),
)

# kolom CSV -> field model yang harus berupa integer
ANGKA = {
    "Isi": "isi",
    "QtyBadStock": "qty_bad_stock",
    "QtyAkhir": "qty_akhir",
    "QtyGD": "qty_gd",
}

# SatK/SatB boleh kosong di sumber (blank=True) -> disimpan sebagai ""
SATUAN = {"SatK": "sat_k", "SatB": "sat_b"}

# Format HJual sumber: "Rp 21,900.00" (spasi, pemisah ribuan koma, 2 desimal)
POLA_RUPIAH = re.compile(r"^Rp \d{1,3}(?:,\d{3})*\.\d{2}$")

# Format integer: hanya digit ASCII (tolak "1_0", "1.0", digit Unicode, dll.)
POLA_INTEGER = re.compile(r"[+-]?\d+\Z")

# Urutan decode: BOM/UTF-8 dulu, lalu Windows (cp1252), terakhir latin-1
ENCODING_DIDUKUNG = ("utf-8-sig", "cp1252", "latin-1")

# Batas rentang integer PostgreSQL (Django IntegerField)
MAKS_INTEGER = 2_147_483_647
MIN_INTEGER = -2_147_483_648

MAKS_TAMPIL_GALAT = 100


class Command(BaseCommand):
    help = (
        "Import database Barang dari inventory.csv (sumber resmi) ke model Barang. "
        "Sekali jalan, validasi penuh sebelum tulis, tidak destructive."
    )

    def handle(self, *args, **options):
        t0 = time.perf_counter()
        path = Path(settings.BASE_DIR) / "inventory.csv"

        # --- 1. Tabel harus kosong: import tidak boleh menimpa data existing ---
        if Barang.objects.exists():
            raise CommandError(
                f"Tabel Barang sudah berisi {Barang.objects.count():,} data. "
                "Import dibatalkan (tidak menimpa/menghapus data existing)."
            )
        if not path.is_file():
            raise CommandError(f"File sumber tidak ditemukan: {path}")

        # --- 2. Baca file sebagai byte, decode dengan encoding yang terbukti ---
        raw = path.read_bytes()
        text = None
        enc_dipakai = None
        for enc in ENCODING_DIDUKUNG:
            try:
                text = raw.decode(enc)
            except UnicodeDecodeError as e:
                self.stdout.write(f"encoding {enc}: tidak cocok ({e.reason} di byte {e.start})")
                continue
            enc_dipakai = enc
            break
        if text is None:
            raise CommandError(
                "File tidak dapat didecode dengan encoding yang didukung "
                "(utf-8-sig, cp1252, latin-1)."
            )

        self.stdout.write(f"File     : {path}")
        self.stdout.write(f"Ukuran   : {len(raw):,} bytes")
        self.stdout.write(f"Encoding : {enc_dipakai}")

        # --- 3. Header: wajib ada; akses data berbasis nama kolom ---
        reader = csv.DictReader(io.StringIO(text, newline=""))
        if not reader.fieldnames:
            raise CommandError("CSV tidak memiliki header.")
        hilang = [k for k in KOLOM_WAJIB if k not in reader.fieldnames]
        if hilang:
            raise CommandError(f"Kolom wajib tidak ada di header: {', '.join(hilang)}")
        # Kolom pertama tanpa nama ("") dan kolom lain diabaikan — tidak masalah.

        # --- 4. Validasi SELURUH baris (read-only, belum ada tulis ke DB) ---
        rows = []
        galat = []
        barcode_terpakai = {}
        baris_data_kosong = 0

        for row in reader:
            nomor = reader.line_num  # nomor baris fisik pada file (header = 1)

            # Jumlah kolom kelebihan (DictReader menyimpan ekstra di key None)
            if None in row:
                galat.append(
                    (nomor, "<jumlah kolom>", f"{len(row[None])} kolom ekstra",
                     "melebihi jumlah kolom header")
                )
                continue

            nilai = {k: row.get(k) for k in KOLOM_WAJIB}
            if any(v is None for v in nilai.values()):
                kurang = [k for k in KOLOM_WAJIB if nilai[k] is None]
                galat.append(
                    (nomor, ", ".join(kurang), "", "kolom kurang dari jumlah header")
                )
                continue

            # Baris dengan semua kolom kosong bukan data (dilaporkan, bukan error)
            if all(not (v or "").strip() for v in nilai.values()):
                baris_data_kosong += 1
                continue

            err_awal = len(galat)
            data = {}

            # Teks wajib (model: blank=False)
            for kolom, field, maks in TEKS_WAJIB:
                v = (nilai[kolom] or "").strip()
                if not v:
                    galat.append((nomor, kolom, "", "wajib terisi (model tidak mengizinkan kosong)"))
                elif len(v) > maks:
                    galat.append((nomor, kolom, v[:60], f"melebihi max_length {maks}"))
                else:
                    data[field] = v

            # Integer: kosong TIDAK diam-diam menjadi 0
            for kolom, field in ANGKA.items():
                v = (nilai[kolom] or "").strip()
                if not v:
                    galat.append((nomor, kolom, "", "wajib angka; kosong tidak diubah menjadi 0"))
                    continue
                if not POLA_INTEGER.fullmatch(v):
                    galat.append((nomor, kolom, v, "bukan bilangan bulat yang valid"))
                    continue
                n = int(v)
                if not (MIN_INTEGER <= n <= MAKS_INTEGER):
                    galat.append((nomor, kolom, v, "di luar rentang integer PostgreSQL"))
                    continue
                data[field] = n

            # HJual: "Rp 21,900.00" -> Decimal("21900.00"); kosong -> NULL (bukan 0)
            v = (nilai["HJual"] or "").strip()
            if not v:
                data["h_jual"] = None
            elif not POLA_RUPIAH.match(v):
                galat.append((nomor, "HJual", v, 'bukan format "Rp n,n.nn" yang dikenal'))
            else:
                try:
                    harga = Decimal(v[len("Rp "):].replace(",", ""))
                except InvalidOperation:
                    galat.append((nomor, "HJual", v, "gagal dikonversi ke Decimal"))
                else:
                    # max_digits=12, decimal_places=2 -> maksimum 10 digit bilangan
                    if abs(harga) >= Decimal(10) ** 10:
                        galat.append((nomor, "HJual", v, "melebihi max_digits=12 DecimalField"))
                    else:
                        data["h_jual"] = harga

            # SatK/SatB: boleh kosong (blank=True) -> string ""
            for kolom, field in SATUAN.items():
                v = (nilai[kolom] or "").strip()
                if len(v) > 32:
                    galat.append((nomor, kolom, v[:60], "melebihi max_length 32"))
                else:
                    data[field] = v

            # Baris baru valid jika tidak menambah galat dan 12 field lengkap
            if len(galat) != err_awal or len(data) != len(KOLOM_WAJIB):
                continue

            # Barcode: STRING apa adanya (jangan diubah jadi integer), unik dalam file
            bc = data["barcode_aktif"]
            if bc in barcode_terpakai:
                galat.append(
                    (nomor, "BarcodeAktif", bc,
                     f"duplikat — sudah terpakai di baris {barcode_terpakai[bc]}")
                )
                continue
            barcode_terpakai[bc] = nomor
            rows.append(Barang(**data))

        baris_kosong_fisik = sum(1 for ln in text.splitlines() if not ln.strip())
        if baris_kosong_fisik or baris_data_kosong:
            self.stdout.write(
                f"Baris kosong fisik: {baris_kosong_fisik}, "
                f"baris semua-kolom-kosong: {baris_data_kosong} (bukan data, dilewati)"
            )

        # --- 5. Satu galat pun = batalkan SEMUANYA, tampilkan rinciannya ---
        if galat:
            self.stderr.write(
                self.style.ERROR(
                    f"VALIDASI GAGAL: {len(galat)} galat ditemukan. "
                    "Tidak ada satu pun baris yang ditulis ke database."
                )
            )
            for nomor, kolom, nilai_masalah, alasan in galat[:MAKS_TAMPIL_GALAT]:
                self.stderr.write(
                    f"  baris {nomor} | kolom {kolom} | nilai: {nilai_masalah!r} | {alasan}"
                )
            if len(galat) > MAKS_TAMPIL_GALAT:
                self.stderr.write(f"  ... dan {len(galat) - MAKS_TAMPIL_GALAT} galat lainnya")
            raise CommandError(
                "Import dibatalkan. Perbaiki data sumber (inventory.csv) terlebih dahulu."
            )

        if not rows:
            raise CommandError("Tidak ada baris valid untuk diimport.")

        self.stdout.write(f"Data valid: {len(rows):,} baris siap diimport")

        # --- 6. Tulis dalam SATU transaksi; gagal = rollback total ---
        with transaction.atomic():
            self.stdout.write("Menulis ke database (transaction.atomic, bulk_create)...")
            Barang.objects.bulk_create(rows, batch_size=1000)

            # Integrasi: jumlah di DB wajib sama persis dengan data valid
            jumlah_db = Barang.objects.count()
            if jumlah_db != len(rows):
                raise CommandError(
                    f"Jumlah database ({jumlah_db:,}) tidak sama dengan data valid "
                    f"({len(rows):,}) — seluruh transaksi di-rollback."
                )

        selesai = time.perf_counter() - t0
        self.stdout.write(
            self.style.SUCCESS(
                f"Berhasil: {jumlah_db:,} database Barang tersimpan di PostgreSQL "
                f"(encoding {enc_dipakai}, {selesai:.1f} detik)."
            )
        )
        self.stdout.write(f"  Barcode unik : {len(barcode_terpakai):,}")
        self.stdout.write(f"  H. Jual NULL : {sum(1 for b in rows if b.h_jual is None)}")
        self.stdout.write(f"  SatK kosong  : {sum(1 for b in rows if not b.sat_k)}")
        self.stdout.write(f"  SatB kosong  : {sum(1 for b in rows if not b.sat_b)}")
