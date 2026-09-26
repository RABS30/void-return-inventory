from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from inventory.models import Barang, VoidReturn, validasi_foto


class VoidReturnForm(forms.ModelForm):

    barcode = forms.CharField(
        label="Barcode",
        max_length=50,
        error_messages={
            "required": "Barcode wajib diisi.",
            "max_length": "Barcode maksimal 50 karakter.",
        },
    )

    tanggal = forms.DateField(
        label="Tanggal",
        widget=forms.DateInput(),
        error_messages={
            "required": "Tanggal wajib diisi.",
            "invalid": "Tanggal tidak valid.",
        },
    )

    quantity = forms.IntegerField(
        label="Quantity",
        min_value=1,
        error_messages={
            "required": "Quantity wajib diisi.",
            "invalid": "Quantity harus berupa angka yang valid.",
            "min_value": "Quantity harus minimal 1.",
        },
    )

    harga_jual = forms.DecimalField(
        label="H. Jual",
        max_digits=12,
        decimal_places=2,
        required=False,
        error_messages={
            "invalid": "H. Jual harus berupa angka yang valid.",
        },
    )

    foto = forms.ImageField(
        label="Foto",
        validators=[validasi_foto],
        error_messages={
            "required": "Foto wajib diunggah.",
            "invalid_image": "File yang diunggah harus berupa gambar.",
        },
    )

    class Meta:
        model = VoidReturn
        fields = (
            "jenis",
            "tanggal",
            "outlet",
            "nama_kasir",
            "otoritas",
            "no_trans",
            "quantity",
            "harga_jual",
            "alasan",
            "foto",
        )

    PESAN_WAJIB = {
        "jenis": "Jenis wajib diisi.",
        "outlet": "Outlet wajib dipilih.",
        "nama_kasir": "Nama kasir wajib diisi.",
        "otoritas": "Otoritas / MOD wajib diisi.",
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for nama, pesan in self.PESAN_WAJIB.items():
            self.fields[nama].error_messages["required"] = pesan

        
        self.fields["jenis"].error_messages["invalid_choice"] = (
            "Jenis harus VOID atau RETURN."
        )
        self.fields["outlet"].error_messages["invalid_choice"] = (
            "Outlet tidak valid. Pilih BT1 sampai BT27."
        )

        self.fields["otoritas"].label = "Otoritas / MOD"
        self.fields["no_trans"].label = "No. Trans"
        jenis_data = self.data.get("jenis") or self.instance.jenis
        if jenis_data == VoidReturn.JENIS_RETURN:
            self.fields["alasan"].label = "Alasan Return"
        elif jenis_data == VoidReturn.JENIS_VOID:
            self.fields["alasan"].label = "Alasan Void"
        else:
            self.fields["alasan"].label = "Alasan"

        self.fields["tanggal"].initial = timezone.localdate()


    def clean_barcode(self):
        barcode = self.cleaned_data["barcode"]
        try:
            barang = Barang.objects.get(barcode_aktif=barcode)
        except Barang.DoesNotExist:
            raise ValidationError(
                "Barcode tidak ditemukan di Database Barang.",
                code="tidak_ditemukan",
            ) from None
        self.cleaned_data["barang"] = barang
        return barcode

    def clean(self):
        cleaned = super().clean()  
        jenis = cleaned.get("jenis")
        harga_jual = cleaned.get("harga_jual")
        no_trans = cleaned.get("no_trans")

        if jenis == VoidReturn.JENIS_VOID:
            if no_trans:
                self.add_error("no_trans", "No. Trans tidak digunakan untuk Void.")
            if harga_jual is not None:
                self.add_error("harga_jual", "H. Jual tidak digunakan untuk Void.")
            cleaned["no_trans"] = None
            cleaned["harga_jual"] = None
        elif jenis == VoidReturn.JENIS_RETURN:
            cleaned["no_trans"] = no_trans or None

        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.barang = self.cleaned_data["barang"]
        if commit:
            instance.save()
        return instance
