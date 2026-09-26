import csv

from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .forms import VoidReturnForm
from .models import Barang, VoidReturn

# Header CSV laporan — urutan kolom mengikuti requirement bisnis. Jangan diubah.
HEADER_VOID = [
    "NO", "OUTLET", "TANGGAL", "NAMA PRODUK", "BARCODE",
    "QTY", "KASIR", "OTORITAS", "ALASAN VOID",
]
HEADER_RETURN = [
    "TANGGAL", "OUTLET", "NAMA KASIR", "NO.TRANS", "NAMA PRODUK",
    "BARCODE", "QTY", "H.JUAL", "OTORITAS", "ALASAN RETURN",
]


def dashboard(request):
    return render(request, "dashboard.html")


def input(request):
    if request.method == "POST":
        form = VoidReturnForm(request.POST, request.FILES)
        if form.is_valid():
            with transaction.atomic():
                transaksi = form.save()
            if transaksi.jenis == VoidReturn.JENIS_VOID:
                messages.success(request, "Transaksi Void berhasil disimpan.")
            else:
                messages.success(request, "Transaksi Return berhasil disimpan.")
            return redirect("inventory:input")
    else:
        form = VoidReturnForm()

    return render(request, "input.html", {"form": form})


@require_GET
def barcode_lookup(request, barcode):
    """Lookup Master Barang via barcode untuk AJAX (read-only).

    - Barcode diperlakukan sebagai string: exact match `barcode_aktif`,
      aman untuk leading zero (tidak di-cast ke integer, tanpa fuzzy).
    - Barcode tidak ditemukan adalah kondisi bisnis normal -> found=false
      dengan status 200 (bukan 500).
    - Barcode kosong -> tanpa query database.
    - Tidak ada perubahan data apa pun.
    """
    if not barcode:
        return JsonResponse({"found": False, "barcode": ""})

    try:
        barang = Barang.objects.get(barcode_aktif=barcode)
    except Barang.DoesNotExist:
        return JsonResponse({"found": False, "barcode": barcode})

    return JsonResponse(
        {"found": True, "barcode": barang.barcode_aktif, "nama": barang.nama}
    )


def daftar(request):
    """Daftar transaksi: filter jenis/waktu + search (kombinasi AND).

    Data diurutkan terbaru dulu (`tanggal` desc, tie-breaker `id` desc)
    dan memakai `select_related("barang")` untuk hindari query N+1.
    """
    transaksi_list = VoidReturn.objects.select_related("barang")

    # Filter jenis — whitelist, nilai GET arbitrer tidak dipercaya.
    jenis_filter = request.GET.get("jenis", "").strip()
    if jenis_filter in (VoidReturn.JENIS_VOID, VoidReturn.JENIS_RETURN):
        transaksi_list = transaksi_list.filter(jenis=jenis_filter)
    else:
        jenis_filter = ""

    # Filter waktu — whitelist.
    waktu_filter = request.GET.get("waktu", "").strip()
    if waktu_filter == "hari-ini":
        transaksi_list = transaksi_list.filter(tanggal=timezone.localdate())
    elif waktu_filter == "bulan-ini":
        hari_ini = timezone.localdate()
        transaksi_list = transaksi_list.filter(
            tanggal__year=hari_ini.year,
            tanggal__month=hari_ini.month,
        )
    else:
        waktu_filter = ""

    # Search — OR antar field, digabung dengan filter di atas (AND).
    search_query = request.GET.get("q", "").strip()
    if search_query:
        transaksi_list = transaksi_list.filter(
            Q(barang__barcode_aktif__icontains=search_query)
            | Q(barang__nama__icontains=search_query)
            | Q(nama_kasir__icontains=search_query)
            | Q(no_trans__icontains=search_query)
        )

    transaksi_list = transaksi_list.order_by("-tanggal", "-id")

    return render(
        request,
        "daftar.html",
        {
            "transaksi_list": transaksi_list,
            "search_query": search_query,
            "jenis_filter": jenis_filter,
            "waktu_filter": waktu_filter,
        },
    )


def _queryset_export(jenis):
    """Seluruh transaksi satu jenis (export tidak mengikuti filter daftar).

    `select_related("barang")` hindari query N+1; ordering sama dengan
    halaman daftar: terbaru dulu, tie-breaker `id`.
    """
    return (
        VoidReturn.objects.select_related("barang")
        .filter(jenis=jenis)
        .order_by("-tanggal", "-id")
    )


def _respons_csv(header, baris, nama_file):
    """Response CSV attachment: UTF-8 + BOM (utf-8-sig) agar Excel aman."""
    respons = HttpResponse(content_type="text/csv; charset=utf-8")
    respons["Content-Disposition"] = f'attachment; filename="{nama_file}"'
    # BOM UTF-8 (setara utf-8-sig) agar Excel membaca karakter non-ASCII
    # sebagai UTF-8, bukan ANSI.
    respons.write("\ufeff")
    penulis = csv.writer(respons)
    penulis.writerow(header)
    penulis.writerows(baris)
    return respons


def export_void(request):
    """Download CSV seluruh transaksi VOID (GET, tanpa filter daftar)."""
    baris = (
        (
            nomor,  # NO: nomor urut laporan, bukan ID database
            transaksi.outlet,
            transaksi.tanggal,
            transaksi.barang.nama,
            transaksi.barang.barcode_aktif,
            transaksi.quantity,
            transaksi.nama_kasir,
            transaksi.otoritas,
            transaksi.alasan,
        )
        for nomor, transaksi in enumerate(
            _queryset_export(VoidReturn.JENIS_VOID), start=1
        )
    )
    nama_file = f"laporan-void-{timezone.localdate().isoformat()}.csv"
    return _respons_csv(HEADER_VOID, baris, nama_file)


def export_return(request):
    """Download CSV seluruh transaksi RETURN (GET, tanpa filter daftar)."""
    baris = (
        (
            transaksi.tanggal,
            transaksi.outlet,
            transaksi.nama_kasir,
            transaksi.no_trans,  # boleh kosong (None -> sel kosong)
            transaksi.barang.nama,
            transaksi.barang.barcode_aktif,
            transaksi.quantity,
            transaksi.harga_jual,  # snapshot input manual, bukan dari master
            transaksi.otoritas,
            transaksi.alasan,
        )
        for transaksi in _queryset_export(VoidReturn.JENIS_RETURN)
    )
    nama_file = f"laporan-return-{timezone.localdate().isoformat()}.csv"
    return _respons_csv(HEADER_RETURN, baris, nama_file)


@require_POST
def hapus_transaksi(request, pk):
    """Hapus satu transaksi Void/Return (POST saja + CSRF via middleware).

    - 404 bila pk tidak ada (get_object_or_404).
    - 405 bila bukan POST (require_POST) — GET tidak pernah menghapus data.
    - File foto dibersihkan agar tidak menjadi orphan, tetapi hanya bila
      nama file tersebut tidak dipakai transaksi lain.
    """
    transaksi = get_object_or_404(VoidReturn, pk=pk)

    # Simpan nama file & storage sebelum record dihapus.
    penyimpanan = transaksi.foto.storage
    nama_foto = transaksi.foto.name

    # Hapus record: Collector.delete() Django sudah dibungkus transaction.atomic.
    transaksi.delete()

    # Bersihkan file foto. Storage FileSystemStorage sudah menelan
    # FileNotFoundError, jadi file yang sudah hilang tidak membuat error.
    if nama_foto and not VoidReturn.objects.filter(foto=nama_foto).exists():
        penyimpanan.delete(nama_foto)

    messages.success(request, "Transaksi berhasil dihapus.")
    return redirect("inventory:daftar")
