"""
BALAT - Simulasi animasi geofence + HerdSync tanpa gateway
----------------------------------------------------------
Jalankan:
    python balat_animasi.py            -> jendela animasi
    python balat_animasi.py --gif      -> simpan animasi ke balat_animasi.gif
Butuh: pip install numpy matplotlib pillow

Aturan yang disimulasikan:
- Zona aman (poligon) + jalan raya di luar zona (bahaya paling tinggi)
- GPS dibaca tiap GPS_MENIT dengan galat; status AMAN / WASPADA / BAHAYA / JALAN
- WASPADA -> bunyi; BAHAYA -> bunyi + getar; JALAN -> bunyi + getar kuat (prioritas)
- Sapi lolos: peringatan berhenti bila di luar zona > LOLOS_MENIT
- HerdSync (BLE): kalung yang berdekatan bertukar posisi terbaru + kejadian
- Tanpa gateway: HP peternak berkeliling dan mengambil data dari kalung terdekat;
  daftar "sudah diterima" dari HP ikut disebar antar-kalung
Perilaku sapi (peluang patuh) adalah ASUMSI; ganti dengan data uji lapangan.
"""
import sys, math
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.patches import Polygon

# ---------------- PARAMETER ----------------
SEED, N_SAPI = 4, 15
LAHAN = (700, 450)
ZONA = [(40, 40), (520, 30), (580, 160), (560, 300), (430, 410), (60, 400)]
JALAN_X = 640                 # jalan raya vertikal di x = 640 m (lebar 14 m)
KANDANG = (110, 220)
WASPADA_M, JALAN_WASPADA_M = 20, 60
GPS_MENIT, RADIO_MENIT, LOLOS_MENIT = 5, 5, 10
JANGKAUAN_BLE, JANGKAUAN_HP = 30, 20
P_BUNYI, P_GETAR, P_GETAR_KUAT = 0.45, 0.80, 0.90
MENIT_PER_FRAME, JAM_MULAI, JAM_SELESAI = 3, 6, 18

rng = np.random.default_rng(SEED)
zona_np = np.array(ZONA, float)
pusat = zona_np.mean(axis=0)


def dalam(p):
    hasil = False
    for k in range(len(ZONA)):
        (x1, y1), (x2, y2) = ZONA[k], ZONA[(k + 1) % len(ZONA)]
        if (y1 > p[1]) != (y2 > p[1]) and p[0] < x1 + (p[1] - y1) * (x2 - x1) / (y2 - y1):
            hasil = not hasil
    return hasil


def jarak_batas(p):
    d = 1e9
    for k in range(len(ZONA)):
        a, b = zona_np[k], zona_np[(k + 1) % len(ZONA)]
        u = np.clip(np.dot(p - a, b - a) / np.dot(b - a, b - a), 0, 1)
        d = min(d, np.linalg.norm(p - a - u * (b - a)))
    return d


def status(p):
    if abs(p[0] - JALAN_X) < JALAN_WASPADA_M:
        return "JALAN"
    if not dalam(p):
        return "BAHAYA"
    return "WASPADA" if jarak_batas(p) < WASPADA_M else "AMAN"


class Kalung:
    def __init__(self, i):
        self.i = i
        self.p = np.array(KANDANG, float) + rng.normal(0, 15, 2)
        self.arah = rng.uniform(0, 2 * math.pi)
        self.jelajah = i % 4 == 0
        self.patuh, self.balik, self.luar, self.alarm = 1.0, 0, -1, True
        self.st, self.kedip = "AMAN", 0
        self.posisi = {}          # id sapi -> (menit, x, y) posisi terbaru yang diketahui
        self.kejadian = {}        # id kejadian -> dict
        self.sudah = set()        # id kejadian yang sudah diterima HP


kalung = [Kalung(i) for i in range(N_SAPI)]
hp = dict(p=np.array(KANDANG, float), tujuan=pusat.copy(), posisi={}, kejadian={}, tunda=[])
st = dict(bunyi=0, getar=0, jalan=0, lolos=0, balik=0, dibuat=0)
t = [JAM_MULAI * 60]
garis_tukar = []


def buat_kejadian(k, jenis, menit):
    kid = f"{k.i}-{menit}-{jenis}"
    k.kejadian[kid] = dict(sapi=k.i, jenis=jenis, menit=menit, x=k.p[0], y=k.p[1])
    st["dibuat"] += 1


def langkah():
    t[0] += 1
    m = t[0]
    for k in kalung:
        laju = 1.8 if rng.random() < 0.9 else 5
        pulang = m >= 16.5 * 60 and k.alarm             # sore: sapi pulang (yang lolos tidak)
        if pulang:
            tuju = np.array(KANDANG, float) + 12 * np.array([math.cos(k.i), math.sin(k.i)])
            k.arah = math.atan2(*(tuju - k.p)[::-1]); laju = 4 if np.linalg.norm(tuju - k.p) > 4 else 0
        elif m < k.balik:
            k.arah = math.atan2(*(pusat - k.p)[::-1]) + rng.normal(0, 0.3); laju = 5
        else:
            k.arah += rng.normal(0, 0.5)
            if k.jelajah and rng.random() < 0.08:
                k.arah = rng.uniform(-0.5, 0.5)                 # penjelajah menuju timur (jalan)
            elif np.linalg.norm(pusat - k.p) > (360 if k.jelajah else 150):
                k.arah = math.atan2(*(pusat - k.p)[::-1])
        k.p = np.clip(k.p + laju * np.array([math.cos(k.arah), math.sin(k.arah)]), 0, LAHAN)
        k.kedip = max(0, k.kedip - 1)
        k.posisi[k.i] = (m, *k.p)
        if (m + k.i) % GPS_MENIT:
            continue
        g = k.p + rng.normal(0, 2.5, 2)
        k.st = status(g)
        if not dalam(k.p):
            if k.luar < 0: k.luar = m
            if k.alarm and m - k.luar >= LOLOS_MENIT:
                k.alarm = False; st["lolos"] += 1; buat_kejadian(k, "LOLOS", m)
        else:
            k.luar, k.alarm = -1, True
        if not k.alarm or k.st == "AMAN":
            continue
        p = {"WASPADA": P_BUNYI, "BAHAYA": P_GETAR, "JALAN": P_GETAR_KUAT}[k.st] * k.patuh
        if k.st == "WASPADA": st["bunyi"] += 1
        else:
            st["getar"] += 1
            if k.st == "JALAN": st["jalan"] += 1
            buat_kejadian(k, k.st, m)
        k.kedip = 4
        if rng.random() < p: k.balik = m + 10; st["balik"] += 1
        else: k.patuh *= 0.97

    # HP peternak berjalan ke posisi kawanan yang ia ketahui, sesekali kembali ke kandang
    if m >= 16.5 * 60:
        hp["tujuan"] = np.array(KANDANG, float)          # sore: peternak menunggu di kandang
    elif np.linalg.norm(hp["tujuan"] - hp["p"]) < 5:
        if rng.random() < 0.3:
            hp["tujuan"] = np.array(KANDANG, float)
        else:
            kenal = list(hp["posisi"].values())
            hp["tujuan"] = (np.array(kenal[rng.integers(len(kenal))][1:]) if kenal else pusat.copy())
    v = hp["tujuan"] - hp["p"]
    hp["p"] = hp["p"] + 3.0 * v / (np.linalg.norm(v) + 1e-9)

    garis_tukar.clear()
    if m % RADIO_MENIT == 0:
        for a in range(N_SAPI):                                   # HerdSync antar-kalung
            for b in range(a + 1, N_SAPI):
                A, B = kalung[a], kalung[b]
                if np.linalg.norm(A.p - B.p) <= JANGKAUAN_BLE:
                    garis_tukar.append((A.p.copy(), B.p.copy()))
                    for s, v_ in list(A.posisi.items()) + list(B.posisi.items()):
                        for K in (A, B):
                            if s not in K.posisi or K.posisi[s][0] < v_[0]: K.posisi[s] = v_
                    sudah = A.sudah | B.sudah
                    gabung = {**A.kejadian, **B.kejadian}
                    for K in (A, B):
                        K.sudah = set(sudah)
                        K.kejadian = {x: e for x, e in gabung.items() if x not in sudah}
        for k in kalung:                                          # HP sebagai pengumpul data
            if np.linalg.norm(k.p - hp["p"]) <= JANGKAUAN_HP:
                garis_tukar.append((k.p.copy(), hp["p"].copy()))
                for s, v_ in k.posisi.items():
                    if s not in hp["posisi"] or hp["posisi"][s][0] < v_[0]: hp["posisi"][s] = v_
                for x, e in k.kejadian.items():
                    if x not in hp["kejadian"]:
                        hp["kejadian"][x] = e; hp["tunda"].append(m - e["menit"])
                k.sudah |= set(hp["kejadian"]); k.kejadian = {}


# ---------------- TAMPILAN ----------------
WARNA = {"AMAN": "#1D9E75", "WASPADA": "#EF9F27", "BAHAYA": "#E24B4A", "JALAN": "#A32D2D"}
fig, ax = plt.subplots(figsize=(11, 6.5))
fig.subplots_adjust(right=0.72)
ax.add_patch(Polygon(ZONA, closed=True, facecolor="#E1F5EE", edgecolor="#0F6E56", lw=2))
ax.axvspan(JALAN_X - 7, JALAN_X + 7, color="#5F5E5A")
ax.axvspan(JALAN_X - JALAN_WASPADA_M, JALAN_X - 7, color="#F7C1C1", alpha=0.35)
ax.text(JALAN_X, LAHAN[1] - 12, "JALAN", color="white", ha="center", va="top", rotation=90, fontsize=9)
ax.scatter(*KANDANG, s=160, marker="s", color="#7F77DD", zorder=3)
ax.set_xlim(0, LAHAN[0]); ax.set_ylim(0, LAHAN[1]); ax.set_aspect("equal")
ax.set_xlabel("meter"); ax.set_ylabel("meter")
titik = ax.scatter([], [], s=60, zorder=5)
cincin = ax.scatter([], [], s=320, facecolors="none", zorder=4, linewidths=2)
dugaan = ax.scatter([], [], s=60, facecolors="none", edgecolors="#185FA5", zorder=4, linewidths=1)
hp_titik, = ax.plot([], [], marker="^", ms=13, color="#185FA5", zorder=6, ls="")
garis = [ax.plot([], [], color="#5DCAA5", lw=1, zorder=2)[0] for _ in range(80)]
panel = fig.text(0.74, 0.5, "", va="center", fontsize=10, family="monospace")
fig.text(0.74, 0.12, "● warna = status kalung\n○ biru = posisi menurut HP\n▲ = HP peternak\n— hijau = tukar data BLE",
         fontsize=9, color="#444441")


def frame(_):
    for _ in range(MENIT_PER_FRAME):
        if t[0] < JAM_SELESAI * 60: langkah()
    P = np.array([k.p for k in kalung])
    titik.set_offsets(P)
    titik.set_color([WARNA[k.st] if k.alarm else "#888780" for k in kalung])
    ked = [k for k in kalung if k.kedip > 0]
    cincin.set_offsets(np.array([k.p for k in ked]) if ked else np.empty((0, 2)))
    cincin.set_edgecolor([WARNA[k.st] for k in ked])
    tahu = list(hp["posisi"].values())
    dugaan.set_offsets(np.array([v[1:] for v in tahu]) if tahu else np.empty((0, 2)))
    hp_titik.set_data([hp["p"][0]], [hp["p"][1]])
    for g in garis: g.set_data([], [])
    for g, (a, b) in zip(garis, garis_tukar): g.set_data([a[0], b[0]], [a[1], b[1]])
    m = t[0]
    tunda = hp["tunda"]
    rata = f"{np.mean(tunda):.0f} mnt" if tunda else "-"
    panel.set_text(
        f"Jam {m // 60:02d}:{m % 60:02d}\n\n"
        f"Peringatan bunyi : {st['bunyi']}\n"
        f"Peringatan getar : {st['getar']}\n"
        f"  dekat jalan    : {st['jalan']}\n"
        f"Sapi berbalik    : {st['balik']}\n"
        f"Sapi lolos       : {st['lolos']}\n\n"
        f"Kejadian dibuat  : {st['dibuat']}\n"
        f"Sampai di HP     : {len(hp['kejadian'])}\n"
        f"Rata tunda       : {rata}\n")
    ax.set_title(f"BALAT tanpa gateway - {N_SAPI} sapi, HP tahu posisi {len(tahu)} sapi")
    return []


n_frame = (JAM_SELESAI - JAM_MULAI) * 60 // MENIT_PER_FRAME
anim = FuncAnimation(fig, frame, frames=n_frame, interval=60, blit=False, repeat=False)
if "--gif" in sys.argv:
    anim.save("balat_animasi.gif", writer="pillow", fps=15)
    print("Tersimpan: balat_animasi.gif")
else:
    plt.show()
