"""Router grid sederhana 1 lapis (B.Cu) untuk PCB THT etsa rumahan.
A* 8 arah dengan penalti belokan; clearance dicek lewat distance transform."""
import heapq, math, random
import numpy as np
from scipy.ndimage import distance_transform_edt

G = 0.3175  # mm per sel


class Router:
    def __init__(self, w_mm, h_mm, outline_ok, clearance=0.45, edge=0.6):
        self.nx, self.ny = int(round(w_mm / G)) + 1, int(round(h_mm / G)) + 1
        xs = np.arange(self.nx) * G
        ys = np.arange(self.ny) * G
        self.X, self.Y = np.meshgrid(xs, ys, indexing="ij")
        self.inside = outline_ok(self.X, self.Y)          # bool: di dalam papan
        pad = np.pad(self.inside, 1, constant_values=False)
        self.edge_dist = (distance_transform_edt(pad)[1:-1, 1:-1] - 1.0) * G
        self.clear = clearance
        self.edge = edge
        self.keepout = np.zeros_like(self.inside)
        self.pads = []      # (net, shape, x, y, sx, sy)
        self.tracks = []    # (net, [(x,y),...], w)

    # ---------- raster tembaga ----------
    def cell(self, x, y):
        return int(round(x / G)), int(round(y / G))

    def pad_mask(self, p):
        net, shape, x, y, sx, sy = p
        dx, dy = np.abs(self.X - x), np.abs(self.Y - y)
        if shape == "circle":
            return dx ** 2 + dy ** 2 <= (sx / 2) ** 2
        if shape == "rect":
            return (dx <= sx / 2) & (dy <= sy / 2)
        r = min(sx, sy) / 2          # oval / stadion
        ax, ay = max(sx / 2 - r, 0), max(sy / 2 - r, 0)
        return (np.maximum(dx - ax, 0) ** 2 + np.maximum(dy - ay, 0) ** 2) <= r ** 2

    def seg_mask(self, a, b, w):
        ax, ay = a; bx, by = b
        vx, vy = bx - ax, by - ay
        L2 = vx * vx + vy * vy
        if L2 == 0:
            t = 0
        else:
            t = np.clip(((self.X - ax) * vx + (self.Y - ay) * vy) / L2, 0, 1)
        px, py = ax + t * vx, ay + t * vy
        return (self.X - px) ** 2 + (self.Y - py) ** 2 <= (w / 2) ** 2

    def copper(self, net=None, exclude=None):
        m = np.zeros_like(self.inside)
        for p in self.pads:
            if (net is None or p[0] == net) and p[0] != exclude:
                m |= self.pad_mask(p)
        for n, pts, w in self.tracks:
            if (net is None or n == net) and n != exclude:
                for a, b in zip(pts, pts[1:]):
                    m |= self.seg_mask(a, b, w)
        return m

    def blocked_for(self, net, w):
        foreign = self.copper(exclude=net)
        d = distance_transform_edt(~foreign) * G
        blk = d < (self.clear + w / 2 + 0.16)
        blk |= self.edge_dist < (self.edge + w / 2)
        blk |= self.keepout
        return blk

    # ---------- A* ----------
    def astar(self, start_xy, goals, blocked, target_xy):
        sx, sy = self.cell(*start_xy)
        tx, ty = target_xy[0] / G, target_xy[1] / G
        D = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]
        h = lambda i, j: math.hypot(i - tx, j - ty) * 0.9
        openh = [(h(sx, sy), 0.0, sx, sy, -1)]
        best = {(sx, sy, -1): 0.0}
        par = {}
        nx, ny = self.nx, self.ny
        n_exp = 0
        while openh:
            f, g, i, j, d = heapq.heappop(openh)
            if g > best.get((i, j, d), 1e18):
                continue
            if (i, j) in goals and (i, j) != (sx, sy):
                path = [(i, j)]
                k = (i, j, d)
                while k in par:
                    k = par[k]; path.append((k[0], k[1]))
                return path[::-1]
            n_exp += 1
            if n_exp > 400000:
                return None
            for nd, (di, dj) in enumerate(D):
                a, b = i + di, j + dj
                if not (0 <= a < nx and 0 <= b < ny):
                    continue
                if blocked[a, b] and (a, b) not in goals:
                    continue
                if di and dj and (blocked[i + di, j] or blocked[i, j + dj]):
                    continue
                step = 1.414 if di and dj else 1.0
                turn = 0 if d in (-1, nd) else 3.0
                ng = g + step + turn
                key = (a, b, nd)
                if ng < best.get(key, 1e18):
                    best[key] = ng
                    par[key] = (i, j, d)
                    heapq.heappush(openh, (ng + h(a, b), ng, a, b, nd))
        return None

    @staticmethod
    def simplify(path):
        if len(path) < 3:
            return path
        out = [path[0]]
        for k in range(1, len(path) - 1):
            d1 = (path[k][0] - out[-1][0], path[k][1] - out[-1][1])
            d2 = (path[k + 1][0] - path[k][0], path[k + 1][1] - path[k][1])
            n1 = (np.sign(d1[0]), np.sign(d1[1])); n2 = (np.sign(d2[0]), np.sign(d2[1]))
            if n1 != n2:
                out.append(path[k])
        out.append(path[-1])
        return out

    # ---------- rute satu net ----------
    def route_net(self, net, w):
        pins = [p for p in self.pads if p[0] == net]
        if len(pins) < 2:
            return True
        # urutan pin: Prim MST dari pin pertama
        tree = [pins[0]]
        rest = pins[1:]
        while rest:
            blocked = self.blocked_for(net, w)
            own = np.zeros_like(self.inside)
            for t in tree:
                own |= self.pad_mask(t)
            for n, pts, w0 in self.tracks:
                if n == net:
                    for a, b in zip(pts, pts[1:]):
                        own |= self.seg_mask(a, b, w0)
            goals = set()
            # sel tembaga sendiri yang aman + titik tengah pad + jalur track
            ok = own & ~blocked
            for i, j in zip(*np.nonzero(ok)):
                goals.add((int(i), int(j)))
            for p in pins:
                if p in tree:
                    goals.add(self.cell(p[2], p[3]))
            for n, pts, _ in self.tracks:
                if n == net:
                    for a, b in zip(pts, pts[1:]):
                        ca, cb = self.cell(*a), self.cell(*b)
                        steps = max(abs(cb[0] - ca[0]), abs(cb[1] - ca[1]), 1)
                        for s in range(steps + 1):
                            goals.add((round(ca[0] + (cb[0] - ca[0]) * s / steps), round(ca[1] + (cb[1] - ca[1]) * s / steps)))
            # pin berikut: terdekat ke pohon
            nxt = min(rest, key=lambda q: min(math.hypot(q[2] - t[2], q[3] - t[3]) for t in tree))
            tgt = min(tree, key=lambda t: math.hypot(nxt[2] - t[2], nxt[3] - t[3]))
            # pin sendiri: tengah pad dipaksa bebas
            for t in [nxt]:
                ci, cj = self.cell(t[2], t[3])
                blocked[ci, cj] = False
            path = self.astar((nxt[2], nxt[3]), goals, blocked, (tgt[2], tgt[3]))
            if path is None:
                return False
            path = self.simplify(path)
            pts = [(nxt[2], nxt[3])] + [(i * G, j * G) for i, j in path]
            end = path[-1]
            for t in tree:  # kalau berakhir di tengah pad, tempel ke titik pad tepat
                if self.cell(t[2], t[3]) == end:
                    pts.append((t[2], t[3]))
            clean = [pts[0]]
            for q in pts[1:]:
                if math.hypot(q[0] - clean[-1][0], q[1] - clean[-1][1]) > 1e-6:
                    clean.append(q)
            if len(clean) >= 2:
                self.tracks.append((net, clean, w))
            tree.append(nxt); rest.remove(nxt)
        return True

    def route_all(self, nets, widths, tries=40, seed=1, last=("GND",), net_keepout=None):
        """GND selalu dirutekan paling akhir. Kalau hanya GND yang gagal, urutan net lain diacak."""
        rnd = random.Random(seed)
        net_keepout = net_keepout or {}
        others = [n for n in nets if n not in last]
        lasts = [n for n in nets if n in last]
        best = None
        for it in range(tries):
            self.tracks = []
            failed = []
            for n in others + lasts:
                saved = self.keepout.copy()
                for (x0, y0, x1, y1) in net_keepout.get(n, []):
                    self.keepout |= (self.X >= x0) & (self.X <= x1) & (self.Y >= y0) & (self.Y <= y1)
                ok = self.route_net(n, widths.get(n, 0.8))
                self.keepout = saved
                if not ok:
                    failed.append(n)
            print(f"  iterasi {it + 1}: gagal {failed}", flush=True)
            if best is None or len(failed) < len(best[1]):
                best = (list(self.tracks), failed)
            if not failed:
                break
            bad = [n for n in failed if n not in last]
            if bad:
                others = bad + [n for n in others if n not in bad]
            else:
                rnd.shuffle(others)
        self.tracks = best[0]
        return best[1], []
