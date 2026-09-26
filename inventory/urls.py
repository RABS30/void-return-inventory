from django.urls import path, re_path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("input", views.input, name="input"),
    # <str:> tidak bisa mewakili barcode kosong; satu regex menangani
    # "/barcode/" (kosong) dan "/barcode/<nilai>" dalam satu pola.
    re_path(r"^barcode/(?P<barcode>[^/]*)$", views.barcode_lookup, name="barcode_lookup"),
    path("daftar", views.daftar, name="daftar"),
    path("daftar/export/void", views.export_void, name="export_void"),
    path("daftar/export/return", views.export_return, name="export_return"),
    path("daftar/<int:pk>/hapus", views.hapus_transaksi, name="hapus_transaksi"),
]


app_name = "inventory"