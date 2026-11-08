"""Bangun, rutekan, cek DRC, dan ekspor kedua PCB BALAT.
python3 jalankan.py  -> folder keluaran/ berisi file KiCad, Gerber, PDF cetak setrika, gambar."""
import os, re, json, subprocess, shutil
import pcbnew
from pcb_balat import Papan, MM, V
import tata_letak as T

OUT = "keluaran"
os.makedirs(OUT, exist_ok=True)

LABEL_UTAMA = [  # (teks, x, y, ukuran, rotasi)
    ("EN", 12.7, 52.2, 0.8, 0), ("TX", 15.24, 52.2, 0.8, 0), ("DQ", 17.78, 52.2, 0.8, 0),
    ("3V3", 20.32, 52.2, 0.8, 0), ("GND", 22.86, 52.2, 0.8, 0), ("VBAT", 25.4, 52.2, 0.8, 0),
    ("M-", 52.6, 29.21, 0.8, 0), ("M+", 52.6, 31.75, 0.8, 0),
    ("BTN", 2.2, 33.02, 0.7, 0), ("GND", 2.2, 35.56, 0.7, 0),
    ("BALAT - PCB UTAMA (kotak 1)", 27.0, 1.2, 0.9, 0),
]
LABEL_DAYA = [
    ("EN", 12.2, 7.62, 0.7, 0), ("TX", 12.2, 10.16, 0.7, 0), ("DQ", 12.2, 12.7, 0.7, 0),
    ("3V3", 12.4, 15.24, 0.7, 0), ("GND", 12.4, 17.78, 0.7, 0), ("VBAT", 12.6, 20.32, 0.7, 0),
    ("DQ", 2.2, 12.7, 0.7, 0), ("VDD", 2.2, 15.24, 0.7, 0), ("GND", 2.2, 17.78, 0.7, 0),
    ("VCC", 26.6, 12.7, 0.7, 0), ("TX", 26.6, 15.24, 0.7, 0), ("GND", 26.6, 17.78, 0.7, 0),
    ("SW", 7.6, 25.4, 0.8, 0), ("SW", 7.6, 27.94, 0.8, 0),
    ("OUT+", 9.6, 39.6, 0.8, 0), ("OUT-", 13.3, 39.6, 0.8, 0),
    ("IN+", 16.9, 39.6, 0.8, 0), ("IN-", 20.6, 39.6, 0.8, 0),
    ("PV-", 23.5, 39.6, 0.8, 0), ("PV+", 26.6, 39.6, 0.8, 0),
    ("BALAT - PCB DAYA (kotak 2)", 14.0, 46.0, 0.9, 0),
]
SPEC = {
    "utama": (T.UTAMA, T.UTAMA_KEEPOUT, [(31.5, 48.6, 45.5, 52.6)], ("BALAT-U v1", 38.5, 50.6), LABEL_UTAMA),
    "daya": (T.DAYA, [], [(14.5, 20.5, 27.0, 33.5)], ("BALAT-D v1", 20.7, 27.0), LABEL_DAYA),
}


def skala(pb):
    """Garis 50 mm di Dwgs.User untuk cek skala cetakan."""
    y = pb.h + 6
    s = pcbnew.PCB_SHAPE(pb.board); s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(pb.P(0, y)); s.SetEnd(pb.P(50, y)); s.SetLayer(pcbnew.Dwgs_User); s.SetWidth(MM(0.3))
    pb.board.Add(s)
    for x in (0, 50):
        t = pcbnew.PCB_SHAPE(pb.board); t.SetShape(pcbnew.SHAPE_T_SEGMENT)
        t.SetStart(pb.P(x, y - 2)); t.SetEnd(pb.P(x, y + 2)); t.SetLayer(pcbnew.Dwgs_User); t.SetWidth(MM(0.3))
        pb.board.Add(t)
    pb.teks("Garis ini harus 50 mm. Cetak skala 100% (tanpa fit to page). Jangan dicerminkan.", 25, y + 3.5,
            pcbnew.Dwgs_User, 1.6)


def drc(board, path):
    pcbnew.WriteDRCReport(board, path, pcbnew.EDA_UNITS_MILLIMETRES, True)
    txt = open(path).read()
    n_err = len(re.findall(r"^\[", txt, re.M))
    unconn = re.search(r"\*\* Found (\d+) unconnected pads", txt)
    viol = re.search(r"\*\* Found (\d+) DRC violations", txt)
    return txt, int(viol.group(1)) if viol else -1, int(unconn.group(1)) if unconn else -1


def buat(nama):
    spec, ko_ant, ko_text, (judul, tx, ty), labels = SPEC[nama]
    pb = Papan(nama, spec["w"], spec["h"], spec["notch"])
    for ref, jenis, nilai, x, y, rot, pn in spec["parts"]:
        pb.tambah(ref, jenis, nilai, x, y, rot, pn)
    gagal = pb.route(list(ko_ant) + list(ko_text), tries=25,
                     net_keepout=T.UTAMA_NET_KEEPOUT if nama == "utama" else None)
    print(nama, "net gagal:", gagal, "| GND diserahkan ke pour:", pb.gnd_gagal)
    pb.teks(judul, tx, ty, pcbnew.B_Cu, 1.2, mirror=True)
    for s, x, y, sz, rot in labels:
        pb.teks(s, x, y, pcbnew.F_SilkS, max(sz, 0.8), rot=rot)
    skala(pb)
    pb.zona_gnd(ko_ant)
    return pb


def ekspor(pb, nama):
    d = os.path.join(OUT, nama)
    os.makedirs(d, exist_ok=True)
    f = os.path.join(d, f"balat_{nama}.kicad_pcb")
    pb.simpan(f)
    b = pcbnew.LoadBoard(f)                     # isi pour GND pada papan yang dimuat ulang
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(f, b)
    txt, nv, nu = drc(b, os.path.join(d, "drc.txt"))
    g = os.path.join(d, "gerber"); os.makedirs(g, exist_ok=True)
    subprocess.run(["kicad-cli", "pcb", "export", "gerbers", "--layers", "B.Cu,F.SilkS,B.Mask,Edge.Cuts", "-o", g + "/", f],
                   check=True, capture_output=True)
    subprocess.run(["kicad-cli", "pcb", "export", "drill", "-o", g + "/", f], check=True, capture_output=True)
    # PDF cetak setrika: B.Cu + garis tepi + garis skala, hitam putih, TIDAK dicerminkan
    subprocess.run(["kicad-cli", "pcb", "export", "pdf", "--layers", "B.Cu,Edge.Cuts", "--black-and-white",
                    "--drill-shape-opt", "1",
                    "-o", os.path.join(d, f"cetak_setrika_{nama}.pdf"), f], check=True, capture_output=True)
    # peta pemasangan komponen (dilihat dari atas)
    subprocess.run(["kicad-cli", "pcb", "export", "pdf", "--layers", "F.SilkS,F.Fab,Edge.Cuts", "--black-and-white",
                    "-o", os.path.join(d, f"peta_komponen_{nama}.pdf"), f], check=True, capture_output=True)
    # gambar pratinjau
    for lay, nm in (("B.Cu,Edge.Cuts", "tembaga"), ("F.SilkS,F.Fab,Edge.Cuts", "komponen")):
        svg = os.path.join(d, f"{nm}.svg")
        subprocess.run(["kicad-cli", "pcb", "export", "svg", "--layers", lay, "--exclude-drawing-sheet",
                        "--page-size-mode", "2", "-o", svg, f], check=True, capture_output=True)
    return nv, nu, txt


if __name__ == "__main__":
    hasil = {}
    for nama in ("utama", "daya"):
        pb = buat(nama)
        nv, nu, txt = ekspor(pb, nama)
        hasil[nama] = (nv, nu)
        print(nama, "DRC pelanggaran:", nv, "pad belum tersambung:", nu)
    json.dump(hasil, open(os.path.join(OUT, "ringkasan_drc.json"), "w"))
    import cetak
    cetak.lembar_a4()
