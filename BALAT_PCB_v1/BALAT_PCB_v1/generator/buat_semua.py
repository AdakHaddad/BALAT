import sys, math, collections
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Polygon
import pcbnew
from pcb_balat import Papan
import tata_letak as T

WARNA = {"GND": "#555", "VBAT": "#c00", "3V3": "#e67e00"}


def bangun(nama, spec):
    pb = Papan(nama, spec["w"], spec["h"], spec["notch"])
    for ref, jenis, nilai, x, y, rot, pn in spec["parts"]:
        pb.tambah(ref, jenis, nilai, x, y, rot, pn)
    return pb


def gambar(pb, path, judul, keepouts=()):
    fig, ax = plt.subplots(figsize=(8, 8 * pb.h / pb.w + 0.6), dpi=130)
    ax.add_patch(Polygon(pb.poly(), closed=True, fc="#f4f1e8", ec="k", lw=1))
    for x0, y0, x1, y1 in keepouts:
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc="none", ec="#999", ls="--", hatch="//"))
    for fp in pb.fps.values():
        bb = fp.GetBoundingBox(False, False)
        x0, y0 = pcbnew.ToMM(bb.GetX()) - pb.ox, pcbnew.ToMM(bb.GetY()) - pb.oy
        ax.add_patch(Rectangle((x0, y0), pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight()),
                               fc="none", ec="#4a7", lw=0.6))
        ax.text(x0 + 0.3, y0 + 0.9, fp.GetReference(), fontsize=6, color="#063", weight="bold")
    if hasattr(pb, "router"):
        for n, pts, w in pb.router.tracks:
            xs, ys = zip(*pts)
            ax.plot(xs, ys, color=WARNA.get(n, "#1f5fbf"), lw=w * 4.2, solid_capstyle="round", alpha=0.85)
    pads = pb.pad_list()
    byn = collections.defaultdict(list)
    for p in pads:
        nm, sh, x, y, sx, sy = p
        if sh == "circle":
            ax.add_patch(Circle((x, y), sx / 2, fc="#c8a040", ec="k", lw=0.3))
        else:
            ax.add_patch(Rectangle((x - sx / 2, y - sy / 2), sx, sy, fc="#c8a040", ec="k", lw=0.3))
        if not nm.startswith("__"):
            byn[nm].append((x, y))
            ax.text(x, y, nm.replace("VBAT_SENSE", "VS").replace("_CTRL", "").replace("TEMP_", "")[:6],
                    fontsize=3.6, ha="center", va="center")
    if not hasattr(pb, "router"):
        for n, ps in byn.items():  # ratsnest MST
            tree, rest = [ps[0]], ps[1:]
            while rest:
                a, b = min(((a, b) for a in tree for b in rest), key=lambda e: math.dist(*e))
                ax.plot([a[0], b[0]], [a[1], b[1]], color=WARNA.get(n, "#36c"), lw=0.6)
                tree.append(b); rest.remove(b)
    ax.set_xlim(-2, pb.w + 2); ax.set_ylim(pb.h + 2, -2); ax.set_aspect("equal")
    ax.set_title(judul, fontsize=10)
    plt.tight_layout(); plt.savefig(path); plt.close(fig)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "preview"
    for nama, spec, ko in (("utama", T.UTAMA, T.UTAMA_KEEPOUT), ("daya", T.DAYA, [])):
        pb = bangun(nama, spec)
        if mode == "preview":
            gambar(pb, f"pre_{nama}.png", f"PCB {nama} (rencana)", ko)
        else:
            gagal = pb.route(ko)
            print(nama, "GAGAL:", gagal)
            gambar(pb, f"rute_{nama}.png", f"PCB {nama} (jalur)", ko)
