"""Generator PCB BALAT: PCB Utama (kotak 1) dan PCB Daya (kotak 2), 1 lapis tembaga (B.Cu), komponen tusuk.
Jalankan dengan python3 milik sistem yang punya modul pcbnew (KiCad 7)."""
import sys, math, os
import pcbnew
import numpy as np
from router import Router

LIB = "/usr/share/kicad/footprints"
MM = pcbnew.FromMM
V = lambda x, y: pcbnew.VECTOR2I(MM(x), MM(y))

FP = {
    "R": ("Resistor_THT", "R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal"),
    "RV": ("Resistor_THT", "R_Axial_DIN0207_L6.3mm_D2.5mm_P2.54mm_Vertical"),
    "JP": ("Resistor_THT", "R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"),
    "C": ("Capacitor_THT", "C_Disc_D5.0mm_W2.5mm_P5.00mm"),
    "CP": ("Capacitor_THT", "CP_Radial_D8.0mm_P3.50mm"),
    "D": ("Diode_THT", "D_DO-41_SOD81_P7.62mm_Horizontal"),
    "Q": ("Package_TO_SOT_THT", "TO-92_Inline_Wide"),
    "LED": ("LED_THT", "LED_D3.0mm"),
    "BZ": ("Buzzer_Beeper", "Buzzer_12x9.5RM7.6"),
    "H2": ("Connector_PinHeader_2.54mm", "PinHeader_1x02_P2.54mm_Vertical"),
    "H3": ("Connector_PinHeader_2.54mm", "PinHeader_1x03_P2.54mm_Vertical"),
    "H4": ("Connector_PinSocket_2.54mm", "PinSocket_1x04_P2.54mm_Vertical"),
    "H6": ("Connector_PinHeader_2.54mm", "PinHeader_1x06_P2.54mm_Vertical"),
    "PF": ("Capacitor_THT", "C_Disc_D7.5mm_W2.5mm_P5.00mm"),
}
LEBAR = {"VBAT": 1.0, "GND": 0.8, "MOT_N": 1.0, "TP_OUT": 1.0, "FUSED": 1.0,
         "SOLAR_RAW": 1.0, "SOLAR_IN": 1.0, "PV_MIN": 1.0}


def esp_footprint(board):
    """ESP32-C3 Super Mini, dilihat dari atas, USB di atas (lokal -Y). Baris 15,24 mm, pitch 2,54 mm."""
    fp = pcbnew.FOOTPRINT(board)
    fp.SetFPID(pcbnew.LIB_ID("BALAT", "ESP32-C3_SuperMini"))
    kiri = ["5V", "GND", "3V3", "IO4", "IO3", "IO2", "IO1", "IO0"]
    kanan = ["IO5", "IO6", "IO7", "IO8", "IO9", "IO10", "IO20", "IO21"]
    for col, names, x in ((0, kiri, -7.62), (1, kanan, 7.62)):
        for i, n in enumerate(names):
            p = pcbnew.PAD(fp)
            p.SetNumber(n)
            p.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
            p.SetShape(pcbnew.PAD_SHAPE_RECT if n == "5V" else pcbnew.PAD_SHAPE_CIRCLE)
            p.SetSize(V(1.9, 1.9)); p.SetDrillSize(V(1.0, 1.0))
            p.SetLayerSet(p.PTHMask())
            p.SetPos0(V(x, -8.89 + 2.54 * i)); p.SetPosition(V(x, -8.89 + 2.54 * i))
            fp.Add(p)
    # garis badan modul + tanda USB + area antena (silkscreen atas)
    def garis(a, b, layer=pcbnew.F_SilkS, w=0.15):
        s = pcbnew.FP_SHAPE(fp, pcbnew.SHAPE_T_SEGMENT)
        s.SetStart0(V(*a)); s.SetEnd0(V(*b)); s.SetDrawCoord(); s.SetLayer(layer); s.SetWidth(MM(w)); fp.Add(s)
    W, H = 9.0, 11.26
    for a, b in [((-W, -H), (W, -H)), ((W, -H), (W, H)), ((W, H), (-W, H)), ((-W, H), (-W, -H))]:
        garis(a, b)
    garis((-4.5, -H - 1.5), (4.5, -H - 1.5)); garis((-4.5, -H - 1.5), (-4.5, -H)); garis((4.5, -H - 1.5), (4.5, -H))
    t = pcbnew.FP_TEXT(fp); t.SetText("USB"); t.SetPos0(V(0, -H + 1.5)); t.SetDrawCoord(); t.SetLayer(pcbnew.F_SilkS)
    t.SetTextSize(V(1, 1)); t.SetTextThickness(MM(0.15)); fp.Add(t)
    t = pcbnew.FP_TEXT(fp); t.SetText("ANTENA"); t.SetPos0(V(0, H - 1.6)); t.SetDrawCoord(); t.SetLayer(pcbnew.F_SilkS)
    t.SetTextSize(V(1, 1)); t.SetTextThickness(MM(0.15)); fp.Add(t)
    return fp


class Papan:
    def __init__(self, nama, w, h, notch=0.0, ox=30.0, oy=40.0):
        self.nama, self.w, self.h, self.notch, self.ox, self.oy = nama, w, h, notch, ox, oy
        self.board = pcbnew.BOARD()
        self.nets = {}
        self.fps = {}
        ds = self.board.GetDesignSettings()
        nc = ds.m_NetSettings.m_DefaultNetClass
        nc.SetClearance(MM(0.4)); nc.SetTrackWidth(MM(0.8))
        ds.m_TrackMinWidth = MM(0.5)
        ds.m_MinClearance = MM(0.4)
        ds.m_CopperEdgeClearance = MM(0.5)
        self.outline()

    def P(self, x, y):
        return V(self.ox + x, self.oy + y)

    def poly(self):
        w, h, n = self.w, self.h, self.notch
        if n <= 0:
            return [(0, 0), (w, 0), (w, h), (0, h)]
        return [(n, 0), (w - n, 0), (w - n, n), (w, n), (w, h - n), (w - n, h - n), (w - n, h), (n, h),
                (n, h - n), (0, h - n), (0, n), (n, n)]

    def outline(self):
        pts = self.poly()
        for a, b in zip(pts, pts[1:] + pts[:1]):
            s = pcbnew.PCB_SHAPE(self.board); s.SetShape(pcbnew.SHAPE_T_SEGMENT)
            s.SetStart(self.P(*a)); s.SetEnd(self.P(*b)); s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(MM(0.1))
            self.board.Add(s)

    def inside(self, X, Y):
        w, h, n = self.w, self.h, self.notch
        ok = (X >= 0) & (X <= w) & (Y >= 0) & (Y <= h)
        if n > 0:
            ok &= ~((X < n) & (Y < n)); ok &= ~((X > w - n) & (Y < n))
            ok &= ~((X < n) & (Y > h - n)); ok &= ~((X > w - n) & (Y > h - n))
        return ok

    def net(self, n):
        if n not in self.nets:
            ni = pcbnew.NETINFO_ITEM(self.board, n); self.board.Add(ni); self.nets[n] = ni
        return self.nets[n]

    def tambah(self, ref, jenis, nilai, x, y, rot, pinnet):
        if jenis == "ESP":
            fp = esp_footprint(self.board)
        else:
            lib, name = FP[jenis]
            fp = pcbnew.FootprintLoad(os.path.join(LIB, lib + ".pretty"), name)
        fp.SetReference(ref); fp.SetValue(nilai)
        # perbesar pad untuk etsa rumahan
        pads = list(fp.Pads())
        for p in pads:
            q = p.GetPosition()
            pitch = min([math.hypot(pcbnew.ToMM(q.x - o.GetPosition().x), pcbnew.ToMM(q.y - o.GetPosition().y))
                         for o in pads if o is not p] or [5])
            d = min(2.4, pitch - 0.62)
            sz = p.GetSize()
            sx, sy = pcbnew.ToMM(sz.x), pcbnew.ToMM(sz.y)
            if p.GetShape() == pcbnew.PAD_SHAPE_OVAL:
                dl = max(0.0, d - min(sx, sy))
                p.SetSize(V(sx + dl, sy + dl))
            else:
                p.SetSize(V(max(sx, d), max(sy, d)))
        fp.SetPosition(self.P(x, y))
        fp.SetOrientationDegrees(rot)
        for p in fp.Pads():
            n = pinnet.get(p.GetNumber())
            if n:
                p.SetNet(self.net(n))
        self.board.Add(fp)
        self.fps[ref] = fp
        return fp

    def teks(self, s, x, y, layer=pcbnew.F_SilkS, size=1.0, mirror=False, rot=0):
        t = pcbnew.PCB_TEXT(self.board); t.SetText(s); t.SetPosition(self.P(x, y)); t.SetLayer(layer)
        t.SetTextSize(V(size, size)); t.SetTextThickness(MM(size * 0.18)); t.SetMirrored(mirror)
        t.SetTextAngleDegrees(rot)
        self.board.Add(t)
        return t

    # ---------- routing ----------
    def pad_list(self):
        out = []
        for fp in self.fps.values():
            for p in fp.Pads():
                if p.GetNetname() == "":
                    nm = "__nc_%s_%s" % (fp.GetReference(), p.GetNumber())
                else:
                    nm = p.GetNetname()
                c = p.GetPosition(); bb = p.GetBoundingBox()
                shape = {pcbnew.PAD_SHAPE_CIRCLE: "circle", pcbnew.PAD_SHAPE_RECT: "rect"}.get(p.GetShape(), "oval")
                out.append((nm, shape, pcbnew.ToMM(c.x) - self.ox, pcbnew.ToMM(c.y) - self.oy,
                            pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight())))
        return out

    def route(self, keepout_rects=(), order=None, tries=40, net_keepout=None):
        r = Router(self.w, self.h, self.inside)
        for (x0, y0, x1, y1) in keepout_rects:   # diperlebar agar tepi jalur juga di luar area
            m = 0.6
            r.keepout |= (r.X >= x0 - m) & (r.X <= x1 + m) & (r.Y >= y0 - m) & (r.Y <= y1 + m)
        r.pads = self.pad_list()
        nets = order or sorted({p[0] for p in r.pads if not p[0].startswith("__")})
        gagal, self.gnd_gagal = r.route_all(nets, LEBAR, tries=tries, net_keepout=net_keepout)
        for n, pts, w in r.tracks:
            for a, b in zip(pts, pts[1:]):
                t = pcbnew.PCB_TRACK(self.board)
                t.SetStart(self.P(*a)); t.SetEnd(self.P(*b)); t.SetWidth(MM(w))
                t.SetLayer(pcbnew.B_Cu); t.SetNet(self.net(n)); self.board.Add(t)
        self.router = r
        return gagal

    def zona_gnd(self, keepouts=()):
        z = pcbnew.ZONE(self.board)
        z.SetLayer(pcbnew.B_Cu); z.SetNet(self.net("GND"))
        o = z.Outline(); o.NewOutline()
        for x, y in self.poly():
            v = self.P(x, y); o.Append(v.x, v.y)
        z.SetLocalClearance(MM(0.5)); z.SetMinThickness(MM(0.5))
        z.SetThermalReliefGap(MM(0.6)); z.SetThermalReliefSpokeWidth(MM(0.9))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        self.board.Add(z)
        for (x0, y0, x1, y1) in keepouts:
            k = pcbnew.ZONE(self.board); k.SetIsRuleArea(True)
            k.SetDoNotAllowCopperPour(True); k.SetDoNotAllowTracks(True); k.SetDoNotAllowVias(True)
            k.SetDoNotAllowPads(False); k.SetDoNotAllowFootprints(False)
            k.SetLayerSet(pcbnew.LSET(pcbnew.B_Cu))
            ko = k.Outline(); ko.NewOutline()
            for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
                v = self.P(x, y); ko.Append(v.x, v.y)
            self.board.Add(k)

    def simpan(self, path):
        self.board.SetFileName(path)
        pcbnew.SaveBoard(path, self.board)
