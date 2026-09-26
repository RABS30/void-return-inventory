"""Template filter tampilan harga (format rupiah)."""

from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def rupiah(nilai):
    """Format harga gaya rupiah.

    Contoh:
        Decimal("14000.00") -> "Rp14.000"
        Decimal("15500.00") -> "Rp15.500"
        Decimal("24997.00") -> "Rp24.997"
        Decimal("15000.50") -> "Rp15.000,50"
        None                -> "—"
    """
    if nilai is None or nilai == "":
        return "—"

    try:
        harga = Decimal(str(nilai))
    except InvalidOperation:
        return str(nilai)

    tanda = "-" if harga < 0 else ""
    harga = abs(harga)

    utuh = int(harga)
    pecahan = harga - utuh

    hasil = f"{utuh:,}".replace(",", ".")
    if pecahan:
        hasil += f",{int(pecahan * 100):02d}"

    return f"{tanda}Rp{hasil}"
