from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models



class Barang(models.Model):
    kode = models.CharField(max_length=50)
    nama = models.CharField(max_length=255, verbose_name="Nama Barang")

    barcode_aktif = models.CharField(max_length=50, unique=True, verbose_name="Barcode")

    isi = models.IntegerField(verbose_name="Isi")

    h_jual = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name="Harga Jual")

    qty_bad_stock   = models.IntegerField(verbose_name="Qty Bad Stock")
    qty_akhir       = models.IntegerField(verbose_name="Qty Akhir")
    qty_gd          = models.IntegerField(verbose_name="Qty Gudang")

    sat_k = models.CharField(max_length=32, blank=True, verbose_name="Satuan Kecil")
    sat_b = models.CharField(max_length=32, blank=True, verbose_name="Satuan Besar")

    pareto  = models.CharField(max_length=16, verbose_name="Pareto")
    jenis   = models.CharField(max_length=32, verbose_name="Jenis Barang")

    class Meta:
        verbose_name = "Barang"
        verbose_name_plural = "Barang"
        ordering = ["nama"]

    def __str__(self):
        return f"{self.nama} ({self.barcode_aktif})"



OUTLET_CHOICES  = [(f"BT{i}", f"BT{i}") for i in range(1, 28)]
OUTLET_VALUES   = [value for value, _ in OUTLET_CHOICES]

UKURAN_MAKS_FOTO = 5 * 1024 * 1024  # 5 MB


def validasi_foto(foto):
    if foto is None:
        return
    if foto.size > UKURAN_MAKS_FOTO:
        raise ValidationError(
            "Ukuran foto melebihi batas maksimal 5 MB.", code="max_size"
        )
    content_type = getattr(foto, "content_type", "") or ""
    if content_type and not content_type.startswith("image/"):
        raise ValidationError("File harus berupa gambar.", code="not_image")


class VoidReturn(models.Model):
    JENIS_VOID = "VOID"
    JENIS_RETURN = "RETURN"
    JENIS_CHOICES = [
        (JENIS_VOID, "VOID"),
        (JENIS_RETURN, "RETURN"),
    ]

    jenis       = models.CharField(max_length=6, choices=JENIS_CHOICES)
    tanggal     = models.DateField()
    outlet      = models.CharField(max_length=4, choices=OUTLET_CHOICES)
    nama_kasir  = models.CharField(max_length=100)
    otoritas    = models.CharField(max_length=100, verbose_name="Otoritas/MOD")

    no_trans    = models.CharField(max_length=50, null=True, blank=True, verbose_name="No Transaksi")

    barang      = models.ForeignKey(Barang, on_delete=models.PROTECT, related_name="transaksi")

    quantity    = models.PositiveIntegerField(validators=[MinValueValidator(1)])


    harga_jual  = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name="Harga Jual")

    alasan      = models.TextField(blank=True)

    foto        = models.ImageField(upload_to="foto/%Y/%m/", validators=[validasi_foto])

    class Meta:
        verbose_name        = "Transaksi Void/Return"
        verbose_name_plural = "Transaksi Void/Return"
        ordering            = ["-tanggal", "-id"]
        constraints         = [
                                models.CheckConstraint(condition=models.Q(quantity__gte=1),              name="voidreturn_qty_min_1",),
                                models.CheckConstraint(condition=models.Q(jenis__in=["VOID", "RETURN"]), name="voidreturn_jenis_valid"),
                                models.CheckConstraint(condition=models.Q(outlet__in=OUTLET_VALUES),     name="voidreturn_outlet_valid",),
                                models.CheckConstraint(condition=~models.Q(jenis="RETURN") | models.Q(harga_jual__isnull=False), name="voidreturn_return_harga_wajib",),
                                models.CheckConstraint(condition=~models.Q(jenis="VOID") | ((models.Q(no_trans__isnull=True) | models.Q(no_trans="")) & models.Q(harga_jual__isnull=True)),name="voidreturn_void_kosong",),
                                models.CheckConstraint(condition=~models.Q(foto=""), name="voidreturn_foto_wajib")
                            ]
        indexes             = [
                                models.Index(fields=["jenis", "tanggal"], name="voidreturn_jenis_tanggal_idx"),
                            ]

    def clean(self):
        super().clean()

        if not self.no_trans:
            self.no_trans = None

        if self.jenis == self.JENIS_RETURN:
            if self.harga_jual is None:
                raise ValidationError(
                    {
                        "harga_jual": "Harga jual wajib diisi untuk Return."
                    }
                )
        elif self.jenis == self.JENIS_VOID:
            galat = {}
            if self.no_trans:
                galat["no_trans"] = "Nomor transaksi tidak digunakan untuk Void."
            if self.harga_jual is not None:
                galat["harga_jual"] = "Harga jual tidak digunakan untuk Void."
            if galat:
                raise ValidationError(galat)

    def __str__(self):
        return f"{self.jenis} {self.tanggal or '-'} - {self.barang or '-'}"
