from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import VoidReturnForm
from .models import VoidReturn


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
