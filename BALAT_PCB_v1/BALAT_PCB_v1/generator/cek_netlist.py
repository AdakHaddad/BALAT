"""Cocokkan net setiap pin skematik dengan pad di PCB (setelah pembacaan ulang file .kicad_pcb)."""
import sys, pcbnew
sys.path.insert(0, "/home/claude/balat_kicad")
import skematik_terintegrasi as S

pads = {}
for nama in ("utama", "daya"):
    b = pcbnew.LoadBoard(f"keluaran/{nama}/balat_{nama}.kicad_pcb")
    for fp in b.GetFootprints():
        for p in fp.Pads():
            pads[(fp.GetReference(), p.GetNumber())] = p.GetNetname()
ESP = {"1": "5V", "2": "GND", "3": "3V3", "4": "IO0", "5": "IO1", "6": "IO3", "7": "IO4", "8": "IO5", "9": "IO6", "10": "IO10", "11": "IO20"}
NPN = {"1": "2", "2": "3", "3": "1"}            # skematik B,C,E -> TO-92 pad E=1,B=2,C=3
PNP = {"1": "2", "2": "3", "3": "1"}
PETA = {  # ref skematik -> (ref PCB, pemetaan pin) ; None = di luar PCB lewat konektor
    "U1": ("U1", ESP), "Q1": ("Q1", NPN), "Q2": ("Q2", NPN), "Q3": ("Q3", PNP),
    "D3": ("D3", {"1": "2", "2": "1"}), "D1": ("D1", {"1": "2", "2": "1"}), "F1": ("F1", {"1": "2", "2": "1"}),
    "M1": ("J2", {"1": "2", "2": "1"}), "U2": ("JGPS", {"1": "1", "2": "3", "3": "2"}),
    "U4": ("JT", {"2": "1", "3": "2", "1": "3"}), "SW1": ("JSW", {"1": "2", "2": "1"}),
    "SW2": ("J3", {"1": "1", "2": "2"}), "R3": ("R3", {"1": "2", "2": "1"}),
}
LUAR = {"PV1.2", "PV2.1", "PV2.2", "PV3.1", "U3.3", "U3.4", "BT1.1", "BT1.2", "C3.1", "C3.2", "U2.4"}
KONEKTOR = {"PV1.1": ("JPV", "1"), "PV3.2": ("JPV", "2"), "U3.1": ("JTI", "1"), "U3.2": ("JTI", "2"),
            "U3.5": ("JTO", "1"), "U3.6": ("JTO", "2")}
salah, cek = [], 0
for pin, net in S.HARAP.items():
    if pin in LUAR:
        continue
    ref, no = pin.split(".")
    if pin in KONEKTOR:
        key = KONEKTOR[pin]
    elif ref in PETA:
        r2, m = PETA[ref]; key = (r2, m.get(no, no))
    else:
        key = (ref, no)
    got = pads.get(key)
    cek += 1
    if got != net:
        salah.append((pin, net, key, got))
print("pin dicek:", cek, "| salah:", salah if salah else "tidak ada")
