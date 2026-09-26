from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect, render

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
    return render(request, "daftar.html")
