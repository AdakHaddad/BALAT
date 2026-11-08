"""Skematik KiCad BALAT versi terintegrasi: sinyal ditarik dengan kabel, daya pakai simbol daya.
Satu skematik untuk kalung A dan B. Butuh: pip install kiutils"""
import uuid, re, csv
from collections import defaultdict
from kiutils.schematic import Schematic
from kiutils.symbol import Symbol, SymbolPin
from kiutils.items.common import Position, Property, Effects, Font, Stroke, Fill, Justify, TitleBlock
from kiutils.items.syitems import SyRect, SyPolyLine
from kiutils.items.schitems import (SchematicSymbol, SymbolInstance, Connection, Junction, NoConnect, Text,
                                    SymbolProjectInstance, SymbolProjectPath, HierarchicalSheetInstance)

uid = lambda: str(uuid.uuid4())
E = lambda h=1.27, hide=False, j=None: Effects(font=Font(height=h, width=h), hide=hide,
                                             justify=Justify(horizontally=j) if j else Justify())
P = lambda x, y, a=None: Position(round(x, 4), round(y, 4), a)

# ---------- definisi simbol: pin = (nomor, nama, x, y, arah) koordinat pustaka (y ke atas) ----------
def kotak(hw, hh, pins):
    return dict(rect=(hw, hh), pins=pins)

SIM = {
    "H2": kotak(3.81, 2.54, [("1", "1", -6.35, 0, 0), ("2", "2", 6.35, 0, 180)]),
    "V2": kotak(2.54, 3.81, [("1", "1", 0, 6.35, 270), ("2", "2", 0, -6.35, 90)]),
    "NPN": kotak(3.81, 3.81, [("1", "B", -6.35, 0, 0), ("2", "C", 6.35, 2.54, 180), ("3", "E", 6.35, -2.54, 180)]),
    "PNP": kotak(3.81, 3.81, [("1", "B", -6.35, 0, 0), ("3", "E", 6.35, 2.54, 180), ("2", "C", 6.35, -2.54, 180)]),
    "TP4056": kotak(7.62, 6.35, [("1", "IN+", -10.16, 3.81, 0), ("2", "IN-", -10.16, 1.27, 0),
                                 ("5", "OUT+", 10.16, 3.81, 180), ("3", "B+", 10.16, 1.27, 180),
                                 ("4", "B-", 10.16, -1.27, 180), ("6", "OUT-", 10.16, -3.81, 180)]),
    "ESP32C3": kotak(7.62, 11.43, [("1", "5V", -10.16, 8.89, 0), ("3", "3V3", -10.16, 6.35, 0), ("2", "GND", -10.16, 3.81, 0)] +
                     [(str(4 + i), n, 10.16, 8.89 - 2.54 * i, 180) for i, n in
                      enumerate(["GPIO0", "GPIO1", "GPIO3", "GPIO4", "GPIO5", "GPIO6", "GPIO10", "GPIO20_RX"])]),
    "GPS": kotak(7.62, 3.81, [("1", "VCC", -10.16, 1.27, 0), ("2", "GND", -10.16, -1.27, 0),
                              ("3", "TX", 10.16, 1.27, 180), ("4", "RX", 10.16, -1.27, 180)]),
    "DS18B20": kotak(7.62, 3.81, [("2", "DQ", -10.16, 1.27, 0), ("3", "VDD", 10.16, 1.27, 180), ("1", "GND", 10.16, -1.27, 180)]),
}

# ---------- penempatan komponen: ref, simbol, nilai, x, y, nama pin tampil (untuk 2 kaki) ----------
PART = [
    ("PV1", "H2", "Panel 2V", 38.1, 76.2, ("-", "+")), ("PV2", "H2", "Panel 2V", 57.15, 76.2, ("-", "+")),
    ("PV3", "H2", "Panel 2V", 76.2, 76.2, ("-", "+")), ("D1", "H2", "1N5819", 95.25, 76.2, ("A", "K")),
    ("U3", "TP4056", "TP4056 + proteksi", 119.38, 80.01, None),
    ("BT1", "V2", "18650", 152.4, 93.98, ("+", "-")), ("F1", "H2", "Polyfuse 1A", 165.1, 76.2, ("1", "2")),
    ("SW1", "H2", "ON/OFF", 184.15, 76.2, ("1", "2")), ("C1", "V2", "470uF", 203.2, 86.36, ("+", "-")),
    ("U1", "ESP32C3", "ESP32-C3 Super Mini", 254.0, 152.4, None),
    ("R1", "V2", "100k", 304.8, 92.71, ("1", "2")), ("R2", "V2", "100k", 304.8, 105.41, ("1", "2")),
    ("C2", "V2", "100nF", 317.5, 105.41, ("1", "2")),
    ("R3", "V2", "4,7k", 335.28, 115.57, ("1", "2")), ("U4", "DS18B20", "DS18B20", 358.14, 123.19, None),
    ("R4", "H2", "1k", 297.18, 139.7, ("1", "2")), ("R5", "V2", "10k", 307.34, 146.05, ("1", "2")),
    ("Q1", "NPN", "S8050", 318.77, 139.7, None), ("BZ1", "V2", "Buzzer 3,3V", 383.54, 125.73, ("+", "-")),
    ("R6", "H2", "470", 297.18, 170.18, ("1", "2")), ("R7", "V2", "10k", 307.34, 176.53, ("1", "2")),
    ("Q2", "NPN", "2N2222", 318.77, 170.18, None), ("M1", "V2", "Motor PS", 345.44, 158.75, ("+", "-")),
    ("D2", "V2", "1N5819", 358.14, 158.75, ("K", "A")), ("C3", "V2", "100nF", 370.84, 158.75, ("1", "2")),
    ("R8", "H2", "1k", 297.18, 208.28, ("1", "2")), ("R9", "V2", "10k", 307.34, 201.93, ("1", "2")),
    ("Q3", "PNP", "S8550", 318.77, 208.28, None), ("C4", "V2", "100nF", 335.28, 217.17, ("1", "2")),
    ("U2", "GPS", "GY-NEO6MV2", 355.6, 212.09, None),
    ("SW2", "H2", "Tombol lapor", 297.18, 226.06, ("1", "2")),
    ("R10", "H2", "220", 297.18, 246.38, ("1", "2")), ("D3", "H2", "LED", 316.23, 246.38, ("A", "K")),
]
POS = {r: (x, y) for r, s, v, x, y, n in PART}
JENIS = {r: s for r, s, v, x, y, n in PART}


def ujung(ref, pin):
    """Koordinat ujung pin di skematik (y ke bawah)."""
    for no, nm, px, py, a in SIM[JENIS[ref]]["pins"]:
        if no == pin:
            x, y = POS[ref]
            return (round(x + px, 4), round(y - py, 4))
    raise KeyError(ref + "." + pin)


# ---------- kabel: daftar titik (polyline); angka = koordinat, string "REF.pin" = ujung pin ----------
def t(p): return ujung(*p.split(".")) if isinstance(p, str) else p

KABEL = [
    ["PV1.2", "PV2.1"], ["PV2.2", "PV3.1"], ["PV3.2", "D1.1"], ["D1.2", "U3.1"],
    ["PV1.1", (31.75, 88.9), (106.68, 88.9), (106.68, 78.74), "U3.2"],
    ["U3.6", (132.08, 83.82), (132.08, 91.44)],
    ["U3.3", (152.4, 78.74), "BT1.1"], ["U3.4", (144.78, 81.28), (144.78, 104.14), (152.4, 104.14), "BT1.2"],
    ["U3.5", "F1.1"], ["F1.2", "SW1.1"], ["SW1.2", (203.2, 76.2)], ["C1.1", (203.2, 76.2)],
    [(203.2, 76.2), (215.9, 76.2)], [(215.9, 76.2), (215.9, 71.12)],
    [(215.9, 76.2), (238.76, 76.2), (238.76, 143.51)],
    # ESP daya
    ["U1.1", (238.76, 143.51)], ["U1.3", (233.68, 146.05)], ["U1.2", (241.3, 148.59), (241.3, 152.4)],
    # GPIO0 -> pembagi tegangan
    ["U1.4", (269.24, 143.51), (269.24, 99.06), "R1.2"], ["R1.2", "C2.1"],
    # GPIO1 -> DS18B20
    ["U1.5", (271.78, 146.05), (271.78, 121.92), "R3.2"], ["R3.2", "U4.2"],
    ["U4.3", (368.3, 116.84)], ["U4.1", (368.3, 129.54)],
    # GPIO3 -> buzzer
    ["U1.6", (274.32, 148.59), (274.32, 139.7), "R4.1"], ["R4.2", "R5.1"], ["R5.1", "Q1.1"],
    ["Q1.3", (325.12, 147.32)], ["Q1.2", (383.54, 137.16), "BZ1.2"],
    # GPIO4 -> motor
    ["U1.7", (279.4, 151.13), (279.4, 170.18), "R6.1"], ["R6.2", "R7.1"], ["R7.1", "Q2.1"],
    ["Q2.3", (325.12, 177.8)], ["Q2.2", (345.44, 167.64), "M1.2"], ["M1.2", "D2.2"], ["D2.2", "C3.2"],
    ["M1.1", "D2.1"], ["D2.1", "C3.1"],
    # GPIO5 -> saklar GPS (PNP) -> GPS
    ["U1.8", (276.86, 153.67), (276.86, 208.28), "R8.1"], ["R8.2", "R9.2"], ["R9.2", "Q3.1"],
    ["Q3.3", (325.12, 200.66)], ["Q3.2", "C4.1"], ["C4.1", "U2.1"], ["U2.2", (340.36, 213.36), (340.36, 218.44)],
    # GPIO6 -> tombol, GPIO10 -> LED, GPIO20 <- GPS TX
    ["U1.9", (274.32, 156.21), (274.32, 226.06), "SW2.1"], ["SW2.2", (307.34, 226.06), (307.34, 231.14)],
    ["U1.10", (271.78, 158.75), (271.78, 246.38), "R10.1"], ["R10.2", "D3.1"], ["D3.2", (325.12, 246.38), (325.12, 251.46)],
    ["U1.11", (269.24, 161.29), (269.24, 266.7), (375.92, 266.7), (375.92, 210.82), "U2.3"],
]
# simbol daya: (net, titik)
DAYA = [("GND", (132.08, 91.44)), ("VBAT", (215.9, 71.12)),
        ("GND", "C1.2"), ("3V3", (233.68, 146.05)), ("GND", (241.3, 152.4)),
        ("VBAT", "R1.1"), ("GND", "R2.2"), ("GND", "C2.2"), ("3V3", "R3.1"), ("3V3", (368.3, 116.84)), ("GND", (368.3, 129.54)),
        ("GND", "R5.2"), ("GND", (325.12, 147.32)), ("3V3", "BZ1.1"), ("GND", "R7.2"), ("GND", (325.12, 177.8)),
        ("VBAT", "M1.1"), ("3V3", "R9.1"), ("3V3", (325.12, 200.66)), ("GND", "C4.2"), ("GND", (340.36, 218.44)),
        ("GND", (307.34, 231.14)), ("GND", (325.12, 251.46))]
NC = ["U2.4"]
# net yang diharapkan per pin (untuk pengecekan otomatis)
HARAP = {"PV1.1": "PV_MIN", "PV1.2": "PV12", "PV2.1": "PV12", "PV2.2": "PV23", "PV3.1": "PV23", "PV3.2": "SOLAR_RAW",
         "D1.1": "SOLAR_RAW", "D1.2": "SOLAR_IN", "U3.1": "SOLAR_IN", "U3.2": "PV_MIN", "U3.3": "BAT_P", "U3.4": "BAT_N",
         "U3.5": "TP_OUT", "U3.6": "GND", "BT1.1": "BAT_P", "BT1.2": "BAT_N", "F1.1": "TP_OUT", "F1.2": "FUSED",
         "SW1.1": "FUSED", "SW1.2": "VBAT", "C1.1": "VBAT", "C1.2": "GND", "U1.1": "VBAT", "U1.2": "GND", "U1.3": "3V3",
         "U1.4": "VBAT_SENSE", "U1.5": "TEMP_DQ", "U1.6": "BUZ_CTRL", "U1.7": "MOT_CTRL", "U1.8": "GPS_EN", "U1.9": "BTN",
         "U1.10": "LED_CTRL", "U1.11": "GPS_TX", "R1.1": "VBAT", "R1.2": "VBAT_SENSE", "R2.1": "VBAT_SENSE", "R2.2": "GND",
         "C2.1": "VBAT_SENSE", "C2.2": "GND", "R3.1": "3V3", "R3.2": "TEMP_DQ", "U4.2": "TEMP_DQ", "U4.3": "3V3", "U4.1": "GND",
         "R4.1": "BUZ_CTRL", "R4.2": "Q1_B", "R5.1": "Q1_B", "R5.2": "GND", "Q1.1": "Q1_B", "Q1.2": "BUZ_N", "Q1.3": "GND",
         "BZ1.1": "3V3", "BZ1.2": "BUZ_N", "R6.1": "MOT_CTRL", "R6.2": "Q2_B", "R7.1": "Q2_B", "R7.2": "GND", "Q2.1": "Q2_B",
         "Q2.2": "MOT_N", "Q2.3": "GND", "M1.1": "VBAT", "M1.2": "MOT_N", "D2.1": "VBAT", "D2.2": "MOT_N", "C3.1": "VBAT",
         "C3.2": "MOT_N", "R8.1": "GPS_EN", "R8.2": "Q3_B", "R9.2": "Q3_B", "R9.1": "3V3", "Q3.1": "Q3_B", "Q3.3": "3V3",
         "Q3.2": "GPS_VCC", "C4.1": "GPS_VCC", "C4.2": "GND", "U2.1": "GPS_VCC", "U2.2": "GND", "U2.3": "GPS_TX",
         "SW2.1": "BTN", "SW2.2": "GND", "R10.1": "LED_CTRL", "R10.2": "LED_A", "D3.1": "LED_A", "D3.2": "GND"}


# ---------- pengecekan sambungan ----------
def periksa():
    segs, titik_pin = [], {}
    for ref, s, *_ in PART:
        for no, *_ in SIM[s]["pins"]:
            titik_pin[ujung(ref, no)] = titik_pin.get(ujung(ref, no), []) + [f"{ref}.{no}"]
    for k in KABEL:
        pts = [t(p) for p in k]
        segs += list(zip(pts, pts[1:]))
    pw = [(n, t(p)) for n, p in DAYA]
    induk = {}
    def cari(a):
        while induk.setdefault(a, a) != a: a = induk[a]
        return a
    def gabung(a, b): induk[cari(a)] = cari(b)
    for a, b in segs: gabung(a, b)
    for n, p in pw: gabung(("NET", n), p)
    masalah = []
    semua_ujung = set(titik_pin) | {p for s in segs for p in s} | {p for _, p in pw}
    for a, b in segs:
        if a[0] != b[0] and a[1] != b[1]: masalah.append(f"kabel miring {a}-{b}")
        for q in semua_ujung:
            if q in (a, b): continue
            if (a[0] == b[0] == q[0] and min(a[1], b[1]) < q[1] < max(a[1], b[1])) or \
               (a[1] == b[1] == q[1] and min(a[0], b[0]) < q[0] < max(a[0], b[0])):
                masalah.append(f"titik {q} menempel di tengah kabel {a}-{b}")
    grup = defaultdict(set)
    for p, refs in titik_pin.items():
        for r in refs:
            if r in HARAP: grup[cari(p)].add(HARAP[r])
    for g, nets in grup.items():
        if len(nets) > 1: masalah.append(f"net tercampur: {nets}")
    perNet = defaultdict(set)
    for g, nets in grup.items():
        for n in nets: perNet[n].add(g)
    for n, gs in perNet.items():
        if len(gs) > 1: masalah.append(f"net {n} terputus jadi {len(gs)} bagian")
    return masalah, segs, pw


def bangun():
    sch = Schematic.create_new(); sch.uuid = uid(); sch.version = 20230121
    sch.paper.paperSize = "A3"
    sch.titleBlock = TitleBlock(title="BALAT - Kalung (dipakai untuk kalung A dan B)", date="2026-11-08", revision="2",
                                company="BALAT Smart Virtual Barrier",
                                comments={1: "Sinyal ditarik kabel; VBAT, 3V3, GND memakai simbol daya.",
                                          2: "IN- TP4056 = B- (sebelum proteksi): JANGAN disambung ke GND sistem (OUT-)."})
    sch.sheetInstances = [HierarchicalSheetInstance(instancePath="/", page="1")]
    dipakai = set()
    for ref, s, val, x, y, nm in PART:
        nama_lib = s if nm is None else f"{s}_{nm[0]}{nm[1]}".replace("+", "p").replace("-", "m")
        if nama_lib not in dipakai:
            dipakai.add(nama_lib)
            hw, hh = SIM[s]["rect"]
            unit = Symbol(entryName=nama_lib, unitId=1, styleId=1)
            unit.graphicItems.append(SyRect(start=P(-hw, hh), end=P(hw, -hh), stroke=Stroke(width=0.254, type="default"),
                                            fill=Fill(type="background")))
            for i, (no, pn, px, py, a) in enumerate(SIM[s]["pins"]):
                tampil = pn if nm is None else nm[i]
                unit.pins.append(SymbolPin(electricalType="passive", position=P(px, py, a), length=2.54, name=tampil,
                                           number=no, nameEffects=E(1.0), numberEffects=E(1.0)))
            lib = Symbol(libraryNickname="BALAT", entryName=nama_lib, inBom=True, onBoard=True, pinNamesOffset=0.508)
            lib.properties = [Property("Reference", "U", 0, P(0, hh + 1.27, 0), E()),
                              Property("Value", nama_lib, 1, P(0, -hh - 1.27, 0), E()),
                              Property("Footprint", "", 2, P(0, 0, 0), E(hide=True)),
                              Property("Datasheet", "", 3, P(0, 0, 0), E(hide=True))]
            lib.units.append(unit); sch.libSymbols.append(lib)
        hw, hh = SIM[s]["rect"]
        sym = SchematicSymbol(libraryNickname="BALAT", entryName=nama_lib, position=P(x, y, 0), unit=1,
                              inBom=True, onBoard=True, uuid=uid())
        geser = hw + 1.27
        sym.properties = [Property("Reference", ref, 0, P(x + geser, y - 1.27, 0), E(j="left")),
                          Property("Value", val, 1, P(x + geser, y + 1.27, 0), E(j="left")),
                          Property("Footprint", "", 2, P(x, y, 0), E(hide=True)),
                          Property("Datasheet", "", 3, P(x, y, 0), E(hide=True))]
        if s in ("H2", "TP4056", "ESP32C3", "GPS", "DS18B20", "NPN", "PNP"):
            sym.properties[0].position = P(x, y - hh - 1.27, 0); sym.properties[0].effects = E()
            sym.properties[1].position = P(x, y + hh + 1.27, 0); sym.properties[1].effects = E()
        sym.pins = {no: uid() for no, *_ in SIM[s]["pins"]}
        sym.instances = [SymbolProjectInstance(name="balat_kalung", paths=[SymbolProjectPath("/" + sch.uuid, ref, 1)])]
        sch.schematicSymbols.append(sym)
        sch.symbolInstances.append(SymbolInstance(path="/" + sym.uuid, reference=ref, unit=1, value=val, footprint=""))
    # simbol daya
    for net in ("GND", "3V3", "VBAT"):
        unit = Symbol(entryName=f"PWR_{net}", unitId=1, styleId=1)
        if net == "GND":
            unit.graphicItems.append(SyPolyLine(points=[P(0, 0), P(0, -1.27), P(1.27, -1.27), P(0, -2.54), P(-1.27, -1.27), P(0, -1.27)],
                                                stroke=Stroke(width=0.254, type="default"), fill=Fill(type="none")))
            pin = SymbolPin(electricalType="power_in", position=P(0, 0, 270), length=0, name="GND", number="1", hide=True)
            vy = -3.81
        else:
            unit.graphicItems.append(SyPolyLine(points=[P(0, 0), P(0, 1.27), P(-1.27, 1.27), P(1.27, 1.27)],
                                                stroke=Stroke(width=0.254, type="default"), fill=Fill(type="none")))
            pin = SymbolPin(electricalType="power_in", position=P(0, 0, 90), length=0, name=net, number="1", hide=True)
            vy = 2.54
        unit.pins.append(pin)
        lib = Symbol(libraryNickname="BALAT", entryName=f"PWR_{net}", isPower=True, inBom=False, onBoard=True)
        lib.properties = [Property("Reference", "#PWR", 0, P(0, -5.08, 0), E(hide=True)),
                          Property("Value", net, 1, P(0, vy, 0), E()),
                          Property("Footprint", "", 2, P(0, 0, 0), E(hide=True)),
                          Property("Datasheet", "", 3, P(0, 0, 0), E(hide=True))]
        lib.units.append(unit); sch.libSymbols.append(lib)
    for i, (net, p) in enumerate(DAYA, 1):
        x, y = t(p); ref = f"#PWR{i:02d}"
        sym = SchematicSymbol(libraryNickname="BALAT", entryName=f"PWR_{net}", position=P(x, y, 0), unit=1,
                              inBom=False, onBoard=True, uuid=uid())
        vy = 3.81 if net == "GND" else -2.54
        sym.properties = [Property("Reference", ref, 0, P(x, y + 5.08, 0), E(hide=True)),
                          Property("Value", net, 1, P(x, y + vy, 0), E()),
                          Property("Footprint", "", 2, P(x, y, 0), E(hide=True)),
                          Property("Datasheet", "", 3, P(x, y, 0), E(hide=True))]
        sym.pins = {"1": uid()}
        sym.instances = [SymbolProjectInstance(name="balat_kalung", paths=[SymbolProjectPath("/" + sch.uuid, ref, 1)])]
        sch.schematicSymbols.append(sym)
        sch.symbolInstances.append(SymbolInstance(path="/" + sym.uuid, reference=ref, unit=1, value=net, footprint=""))
    # kabel, junction, no-connect
    hitung = defaultdict(int)
    for k in KABEL:
        pts = [t(p) for p in k]
        for a, b in zip(pts, pts[1:]):
            sch.graphicalItems.append(Connection(type="wire", points=[P(*a), P(*b)], stroke=Stroke(width=0, type="default"), uuid=uid()))
            hitung[a] += 1; hitung[b] += 1
    pin_pts = {ujung(r, no) for r, s, *_ in PART for no, *_ in SIM[s]["pins"]}
    for p, n in hitung.items():
        if n + (1 if p in pin_pts else 0) >= 3:
            sch.junctions.append(Junction(position=P(*p), diameter=0, uuid=uid()))
    for p in NC:
        sch.noConnects.append(NoConnect(position=P(*t(p)), uuid=uid()))
    for teks, (x, y) in [("DAYA: panel surya, pengisian, baterai", (25.4, 60.96)), ("OTAK: ESP32-C3", (243.84, 129.54)),
                         ("PERIFERAL: baterai, suhu, buzzer, motor, GPS, tombol, LED", (284.48, 68.58))]:
        sch.texts.append(Text(text=teks, position=P(x, y, 0), effects=E(1.8, j="left"), uuid=uid()))
    sch.to_file("balat_kalung.kicad_sch")
    teks = open("balat_kalung.kicad_sch").read()
    teks = re.sub(r"(-?\d+\.\d{5,})", lambda m: f"{round(float(m.group(1)), 4):g}", teks)
    open("balat_kalung.kicad_sch", "w").write(teks)
    open("balat_kalung.kicad_pro", "w").write('{\n  "meta": {"filename": "balat_kalung.kicad_pro", "version": 1}\n}\n')


if __name__ == "__main__":
    masalah, segs, pw = periksa()
    print("Masalah sambungan:", masalah if masalah else "tidak ada")
    if not masalah:
        bangun(); print("Tersimpan: balat_kalung.kicad_sch")
