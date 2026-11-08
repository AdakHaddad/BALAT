"""Gambar pratinjau dari file .kicad_pcb: zona GND, jalur, pad, label komponen."""
import sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Circle, Rectangle, FancyBboxPatch
import pcbnew

WARNA = {"GND": "#6b6b6b", "VBAT": "#d62728", "3V3": "#ff8c00"}


def gambar(path, out, judul, dari_bawah=False):
    b = pcbnew.LoadBoard(path)
    bb = b.GetBoardEdgesBoundingBox()
    x0, y0 = pcbnew.ToMM(bb.GetX()), pcbnew.ToMM(bb.GetY())
    W, H = pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight())
    fx = (lambda x: x0 + W - (x - x0)) if dari_bawah else (lambda x: x)
    fig, ax = plt.subplots(figsize=(7.5, 7.5 * H / W + 0.8), dpi=150)
    # outline
    for d in b.GetDrawings():
        if d.GetLayer() == pcbnew.Edge_Cuts and d.GetShape() == pcbnew.SHAPE_T_SEGMENT:
            s, e = d.GetStart(), d.GetEnd()
            ax.plot([fx(pcbnew.ToMM(s.x)), fx(pcbnew.ToMM(e.x))], [pcbnew.ToMM(s.y), pcbnew.ToMM(e.y)], "k", lw=1.2)
    # zona terisi
    for z in b.Zones():
        if z.GetIsRuleArea():
            o = z.Outline()
            pts = [(fx(pcbnew.ToMM(o.CVertex(i).x)), pcbnew.ToMM(o.CVertex(i).y)) for i in range(o.TotalVertices())]
            ax.add_patch(Polygon(pts, fc="none", ec="#999", ls="--", hatch="//", lw=0.6))
            continue
        fp = z.GetFilledPolysList(pcbnew.B_Cu)
        for i in range(fp.OutlineCount()):
            ol = fp.Outline(i)
            pts = [(fx(pcbnew.ToMM(ol.CPoint(k).x)), pcbnew.ToMM(ol.CPoint(k).y)) for k in range(ol.PointCount())]
            ax.add_patch(Polygon(pts, fc="#c9d3c3", ec="none"))
            for h in range(fp.HoleCount(i)):
                hl = fp.Hole(i, h)
                pts = [(fx(pcbnew.ToMM(hl.CPoint(k).x)), pcbnew.ToMM(hl.CPoint(k).y)) for k in range(hl.PointCount())]
                ax.add_patch(Polygon(pts, fc="white", ec="none"))
    for t in b.GetTracks():
        s, e = t.GetStart(), t.GetEnd()
        ax.plot([fx(pcbnew.ToMM(s.x)), fx(pcbnew.ToMM(e.x))], [pcbnew.ToMM(s.y), pcbnew.ToMM(e.y)],
                color=WARNA.get(t.GetNetname(), "#1f5fbf"), lw=pcbnew.ToMM(t.GetWidth()) * 7.5 * 72 / (W + 4) * 0.92,
                solid_capstyle="round")
    for fp in b.GetFootprints():
        for p in fp.Pads():
            c = p.GetPosition(); sz = p.GetBoundingBox()
            x, y = fx(pcbnew.ToMM(c.x)), pcbnew.ToMM(c.y)
            w, h = pcbnew.ToMM(sz.GetWidth()), pcbnew.ToMM(sz.GetHeight())
            if p.GetShape() == pcbnew.PAD_SHAPE_CIRCLE:
                ax.add_patch(Circle((x, y), w / 2, fc="#c8a040", ec="#5a4a10", lw=0.4))
            else:
                ax.add_patch(Rectangle((x - w / 2, y - h / 2), w, h, fc="#c8a040", ec="#5a4a10", lw=0.4))
            dr = pcbnew.ToMM(p.GetDrillSize().x)
            if dr > 0:
                ax.add_patch(Circle((x, y), dr / 2, fc="white", ec="none"))
        r = fp.GetPosition()
        ax.text(fx(pcbnew.ToMM(r.x)), pcbnew.ToMM(r.y) - 1.6, fp.GetReference(), fontsize=6, color="#003a8c",
                ha="center", weight="bold")
    ax.set_xlim(x0 - 2, x0 + W + 2); ax.set_ylim(y0 + H + 2, y0 - 2); ax.set_aspect("equal"); ax.axis("off")
    ax.set_title(judul, fontsize=10)
    plt.tight_layout(); plt.savefig(out); plt.close(fig)


if __name__ == "__main__":
    gambar(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "", len(sys.argv) > 4)
