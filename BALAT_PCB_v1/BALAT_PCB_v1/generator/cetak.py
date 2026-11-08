"""Satu lembar A4 untuk cetak setrika: 2x PCB utama + 2x PCB daya + garis skala 50 mm."""
import os, subprocess
import pypdf
from pypdf import Transformation
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm

OUT = "keluaran"
OX, OY = 30.0, 40.0          # posisi pojok kiri-atas papan di halaman A4 asal (mm)
PAGE_W, PAGE_H = 297.0, 210.0


def pdf_tembaga(nama):
    f = os.path.join(OUT, nama, f"balat_{nama}.kicad_pcb")
    p = os.path.join(OUT, nama, f"cetak_setrika_{nama}.pdf")
    subprocess.run(["kicad-cli", "pcb", "export", "pdf", "--layers", "B.Cu,Edge.Cuts", "--black-and-white",
                    "--drill-shape-opt", "1", "-o", p, f], check=True, capture_output=True)
    return p


def lembar_a4():
    letak = [("utama", 15, 30), ("utama", 80, 30), ("daya", 150, 30), ("daya", 192, 30)]
    dasar = os.path.join(OUT, "_dasar.pdf")
    c = canvas.Canvas(dasar, pagesize=(PAGE_W * mm, PAGE_H * mm))
    Y = lambda y: (PAGE_H - y) * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(15 * mm, Y(14), "BALAT - pola tembaga untuk transfer setrika (2 kalung)")
    c.setFont("Helvetica", 8)
    c.drawString(15 * mm, Y(19.5), "Cetak printer LASER, skala 100% / ukuran sebenarnya (matikan 'fit to page'). "
                 "JANGAN dicerminkan: pola ini sudah benar untuk lapisan bawah.")
    c.drawString(15 * mm, Y(24), "Hitam = tembaga yang dipertahankan. Titik putih kecil = tanda pusat bor (0,8-1 mm).")
    for nama, x, y in letak:
        c.drawString(x * mm, Y(y - 1.5), "PCB " + ("UTAMA (kotak 1)" if nama == "utama" else "DAYA (kotak 2)"))
    # garis skala
    y0 = 110
    c.setLineWidth(0.6)
    c.line(15 * mm, Y(y0), 65 * mm, Y(y0))
    for x in (15, 65):
        c.line(x * mm, Y(y0 - 3), x * mm, Y(y0 + 3))
    for i in range(1, 5):
        c.line((15 + 10 * i) * mm, Y(y0 - 1.5), (15 + 10 * i) * mm, Y(y0 + 1.5))
    c.setFont("Helvetica", 8)
    c.drawString(15 * mm, Y(y0 + 7), "Garis ini harus tepat 50 mm. Ukur dengan penggaris sebelum menyetrika.")
    c.drawString(15 * mm, Y(y0 + 11), "PCB utama = 54 x 54 mm, PCB daya = 28 x 44 mm.")
    c.save()
    out = pypdf.PdfWriter()
    base = pypdf.PdfReader(dasar).pages[0]
    src = {n: pdf_tembaga(n) for n in ("utama", "daya")}
    for nama, x, y in letak:
        pg = pypdf.PdfReader(src[nama]).pages[0]
        t = Transformation().translate(tx=(x - OX) * mm, ty=(OY - y) * mm)
        base.merge_transformed_page(pg, t)
    out.add_page(base)
    hasil = os.path.join(OUT, "CETAK_SETRIKA_A4.pdf")
    with open(hasil, "wb") as f:
        out.write(f)
    os.remove(dasar)
    return hasil


if __name__ == "__main__":
    print(lembar_a4())
