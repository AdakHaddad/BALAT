"""Peta pemasangan komponen (dilihat dari sisi komponen) + daftar komponen, A4 PDF dan PNG."""
import math, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Circle, Rectangle, Polygon, Arc
import pcbnew

MM = pcbnew.ToMM
CATATAN = {
    "U1": "pakai pin header jantan, tanpa soket (biar muat)",
    "Q1": "NPN; kaki E ke pad kotak (urutan E-B-C)", "Q2": "NPN; kaki E ke pad kotak (urutan E-B-C)",
    "Q3": "PNP! kaki E ke pad kotak (urutan E-B-C)", "D2": "garis putih (katoda) ke arah pad kotak", "D1": "garis (katoda) ke pad kotak",
    "C1": "kaki + ke pad kotak; boleh direbahkan", "D3": "kaki pendek (katoda) ke pad kotak",
    "BZ1": "kaki + ke pad kotak", "J1": "kabel 6 urat ke J1 PCB lain, urutan sama", "J2": "M-/M+ ke motor; 100nF disolder di kaki motor", "J3": "ke tombol 'mode lapor' di dinding kotak",
    "JT": "DS18B20 lewat kabel, tempelkan ke badan baterai", "JGPS": "VCC, TX, GND modul GPS (RX tidak dipakai)",
    "JTI": "ke IN+ / IN- modul TP4056", "JTO": "ke OUT+ / OUT- modul TP4056", "JSW": "ke saklar geser ON/OFF",
    "JPV": "ke rangkaian seri 3 panel surya", "F1": "polyfuse 1A, tidak berkutub",
}


def gambar_papan(ax, path, skala_teks=1.0):
    b = pcbnew.LoadBoard(path)
    bb = b.GetBoardEdgesBoundingBox()
    x0, y0, W, H = MM(bb.GetX()), MM(bb.GetY()), MM(bb.GetWidth()), MM(bb.GetHeight())
    for d in b.GetDrawings():
        if d.GetLayer() == pcbnew.Edge_Cuts:
            s, e = d.GetStart(), d.GetEnd()
            ax.plot([MM(s.x) - x0, MM(e.x) - x0], [MM(s.y) - y0, MM(e.y) - y0], "k", lw=1.5)
    # jalur tembaga tipis di latar (dilihat tembus dari atas)
    for t in b.GetTracks():
        s, e = t.GetStart(), t.GetEnd()
        ax.plot([MM(s.x) - x0, MM(e.x) - x0], [MM(s.y) - y0, MM(e.y) - y0], color="#e6d3a8", lw=2.2, zorder=1)
    rows = []
    for fp in sorted(b.GetFootprints(), key=lambda f: f.GetReference()):
        for g in fp.GraphicalItems():
            if g.GetClass() != "MGRAPHIC" or g.GetLayer() not in (pcbnew.F_Fab,):
                continue
            sh = g.GetShape()
            if sh == pcbnew.SHAPE_T_SEGMENT:
                s, e = g.GetStart(), g.GetEnd()
                ax.plot([MM(s.x) - x0, MM(e.x) - x0], [MM(s.y) - y0, MM(e.y) - y0], color="#1d3b6e", lw=0.9, zorder=3)
            elif sh == pcbnew.SHAPE_T_CIRCLE:
                c = g.GetCenter()
                ax.add_patch(Circle((MM(c.x) - x0, MM(c.y) - y0), MM(g.GetRadius()), fc="none", ec="#1d3b6e", lw=0.9, zorder=3))
            elif sh == pcbnew.SHAPE_T_RECT:
                s, e = g.GetStart(), g.GetEnd()
                ax.add_patch(Rectangle((min(MM(s.x), MM(e.x)) - x0, min(MM(s.y), MM(e.y)) - y0),
                                       abs(MM(e.x - s.x)), abs(MM(e.y - s.y)), fc="none", ec="#1d3b6e", lw=0.9, zorder=3))
            elif sh == pcbnew.SHAPE_T_ARC:
                c = g.GetCenter(); r = MM(g.GetRadius())
                a0 = math.degrees(math.atan2(MM(g.GetStart().y - c.y), MM(g.GetStart().x - c.x)))
                a1 = math.degrees(math.atan2(MM(g.GetEnd().y - c.y), MM(g.GetEnd().x - c.x)))
                ax.add_patch(Arc((MM(c.x) - x0, MM(c.y) - y0), 2 * r, 2 * r, theta1=a0, theta2=a1, ec="#1d3b6e", lw=0.9, zorder=3))
            elif sh == pcbnew.SHAPE_T_POLY:
                ps = g.GetPolyShape().Outline(0)
                pts = [(MM(ps.CPoint(k).x) - x0, MM(ps.CPoint(k).y) - y0) for k in range(ps.PointCount())]
                ax.add_patch(Polygon(pts, fc="#1d3b6e", ec="none", zorder=3))
        if fp.GetReference() == "U1":   # modul ESP digambar manual (garis silk)
            for g in fp.GraphicalItems():
                if g.GetClass() == "MGRAPHIC" and g.GetLayer() == pcbnew.F_SilkS and g.GetShape() == pcbnew.SHAPE_T_SEGMENT:
                    s, e = g.GetStart(), g.GetEnd()
                    ax.plot([MM(s.x) - x0, MM(e.x) - x0], [MM(s.y) - y0, MM(e.y) - y0], color="#1d3b6e", lw=0.9, zorder=3)
        for p in fp.Pads():
            c = p.GetPosition(); x, y = MM(c.x) - x0, MM(c.y) - y0
            sz = p.GetBoundingBox(); w, h = MM(sz.GetWidth()), MM(sz.GetHeight())
            if p.GetShape() == pcbnew.PAD_SHAPE_RECT:
                ax.add_patch(Rectangle((x - w / 2, y - h / 2), w, h, fc="#c8a040", ec="k", lw=0.5, zorder=4))
            else:
                ax.add_patch(Circle((x, y), min(w, h) / 2, fc="#c8a040", ec="k", lw=0.5, zorder=4))
            ax.add_patch(Circle((x, y), MM(p.GetDrillSize().x) / 2, fc="white", ec="none", zorder=5))
        bbx = fp.GetBoundingBox(False, False)
        cx = MM(bbx.GetCenter().x) - x0; cy = MM(bbx.GetCenter().y) - y0
        ax.text(cx, cy, fp.GetReference(), ha="center", va="center", fontsize=7 * skala_teks, weight="bold",
                color="#b00020", zorder=6, bbox=dict(fc="white", ec="none", alpha=0.75, pad=0.6))
        rows.append((fp.GetReference(), fp.GetValue()))
    for t in b.GetDrawings():
        if isinstance(t, pcbnew.PCB_TEXT) and t.GetLayer() == pcbnew.F_SilkS and len(t.GetText()) <= 5:
            p = t.GetPosition()
            ax.text(MM(p.x) - x0, MM(p.y) - y0, t.GetText(), fontsize=4.6 * skala_teks, ha="center", va="center",
                    color="#333", zorder=6)
    ax.set_xlim(-2, W + 2); ax.set_ylim(H + 2, -2); ax.set_aspect("equal"); ax.axis("off")
    return rows, (W, H)


def halaman(pdf, path, judul, out_png):
    fig = plt.figure(figsize=(11.69, 8.27))
    ax = fig.add_axes([0.03, 0.08, 0.55, 0.82])
    rows, (W, H) = gambar_papan(ax, path, 1.15)
    fig.text(0.03, 0.94, judul, fontsize=14, weight="bold")
    fig.text(0.03, 0.91, f"Dilihat dari sisi KOMPONEN (atas). Ukuran papan {W:.0f} x {H:.0f} mm. "
             "Jalur krem = tembaga di bawah (tembus pandang).", fontsize=8.5)
    tab = fig.add_axes([0.60, 0.06, 0.38, 0.84]); tab.axis("off")
    y = 1.0
    tab.text(0, y, "Ref", weight="bold", fontsize=8.5); tab.text(0.13, y, "Komponen", weight="bold", fontsize=8.5)
    tab.text(0.45, y, "Catatan pasang", weight="bold", fontsize=8.5)
    for ref, val in rows:
        y -= 0.034
        tab.text(0, y, ref, fontsize=8, color="#b00020", weight="bold"); tab.text(0.13, y, val, fontsize=8)
        note = CATATAN.get(ref, "")
        tab.text(0.45, y, note, fontsize=6.6, color="#333")
    pdf.savefig(fig); fig.savefig(out_png, dpi=130); plt.close(fig)


if __name__ == "__main__":
    with PdfPages("keluaran/PETA_KOMPONEN.pdf") as pdf:
        halaman(pdf, "keluaran/utama/balat_utama.kicad_pcb", "BALAT - PCB UTAMA (kotak 1, ESP32)", "keluaran/peta_utama.png")
        halaman(pdf, "keluaran/daya/balat_daya.kicad_pcb", "BALAT - PCB DAYA (kotak 2, baterai + GPS)", "keluaran/peta_daya.png")
    print("ok")
