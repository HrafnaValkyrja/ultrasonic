"""Two-layer maze bridge on the OUTER faces (F + B, via hops allowed) between two islands of one net: for a long net the
autorouter left open when neither face alone has a path (2026-10-07, B-DOC-AUDIT-0007 re-route: LED_K U1.43 -> J8).
Grid 0.05 mm; obstacles = other nets' tracks, vias and pads per face, rule areas (mic-port keep-out), 0.3 mm edge band.
A via hop costs VIA_COST mm and needs a legal via on both faces. Every segment and via is re-checked with close_gaps
clear() before it is kept; the board is saved only if all pass. Run DRC afterwards.

    systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 \
        python3 hw/pod/fb_bridge.py BOARD.kicad_pcb NET [VIA_COST_MM] [rip=R]

rip=R (rip-up and repair): if no path exists, delete the UNLOCKED copper of other nets within R mm of the boxed island's
pads (never GND/+3V0 plane-fan-out vias' own pads, never locked pre-routes), bridge NET, then bridge every ripped net
again (no further rip). Saved only if every net closes. `riponly`: rip and save, no bridging (the caller then bridges
NET, e.g. with inner_bridge.py on In2, and every ripped net with this script).
"""
import heapq
import math
import pathlib
import sys

import pcbnew

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import close_gaps as C  # noqa: E402

M, mm = pcbnew.ToMM, pcbnew.FromMM
path, net_name = sys.argv[1], sys.argv[2]
VIA_COST = next((float(a) for a in sys.argv[3:] if a[:1].isdigit()), 1.5)
RIP = next((float(a[4:]) for a in sys.argv[3:] if a.startswith("rip=")), 0.0)
b = pcbnew.LoadBoard(path)
net = None
G = 0.05
bb = b.GetBoardEdgesBoundingBox()
x0, y0, W, H = M(bb.GetLeft()), M(bb.GetTop()), M(bb.GetWidth()), M(bb.GetHeight())
nx, ny = int(W / G) + 1, int(H / G) + 1
LAYERS = (pcbnew.F_Cu, pcbnew.B_Cu)
KT = C.CLR + C.TRACK_W / 2 + 0.01          # track centre keep
KV = C.CLR + C.VIA_D / 2 + 0.01            # via centre keep


def dseg(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay; L = dx * dx + dy * dy
    u = 0 if L == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - ax - u * dx, py - ay - u * dy)


def obstacles(lay):
    obs = []
    for t in b.GetTracks():
        if t.GetNetCode() == net or not t.IsOnLayer(lay):
            continue
        if t.GetClass() == "PCB_VIA":
            p = t.GetPosition(); obs.append(("c", M(p.x), M(p.y), M(t.GetWidth(lay)) / 2))
        else:
            obs.append(("s", M(t.GetStart().x), M(t.GetStart().y), M(t.GetEnd().x), M(t.GetEnd().y), M(t.GetWidth()) / 2))
    for f in b.GetFootprints():
        for p in f.Pads():
            if p.GetNetCode() != net and (p.IsOnLayer(lay) or p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH):
                r = p.GetBoundingBox()
                obs.append(("r", M(r.GetLeft()), M(r.GetTop()), M(r.GetRight()), M(r.GetBottom()), 0.0))
    return obs


def mask(lay, keep):
    m = bytearray(nx * ny)
    for o in obstacles(lay):
        if o[0] == "c": lo_x, hi_x, lo_y, hi_y, r = o[1] - o[3], o[1] + o[3], o[2] - o[3], o[2] + o[3], o[3]
        elif o[0] == "r": lo_x, lo_y, hi_x, hi_y, r = o[1], o[2], o[3], o[4], 0.0
        else: lo_x, hi_x, lo_y, hi_y, r = min(o[1], o[3]) - o[5], max(o[1], o[3]) + o[5], min(o[2], o[4]) - o[5], max(o[2], o[4]) + o[5], o[5]
        for i in range(max(0, int((lo_x - keep - x0) / G)), min(nx, int((hi_x + keep - x0) / G) + 2)):
            for j in range(max(0, int((lo_y - keep - y0) / G)), min(ny, int((hi_y + keep - y0) / G) + 2)):
                px, py = x0 + i * G, y0 + j * G
                if o[0] == "c": d = math.hypot(px - o[1], py - o[2]) - r
                elif o[0] == "r": d = math.hypot(max(o[1] - px, 0, px - o[3]), max(o[2] - py, 0, py - o[4]))
                else: d = dseg(px, py, o[1], o[2], o[3], o[4]) - r
                if d < keep: m[i * ny + j] = 1
    areas = [z for z in b.Zones() if z.GetIsRuleArea() and z.IsOnLayer(lay)]
    band = 0.3 + (keep - C.CLR)
    for i in range(nx):
        for j in range(ny):
            px, py = x0 + i * G, y0 + j * G
            if px < x0 + band or px > x0 + W - band or py < y0 + band or py > y0 + H - band:
                m[i * ny + j] = 1
            elif areas and any(z.Outline().Collide(pcbnew.VECTOR2I(mm(px), mm(py)), mm(keep)) for z in areas):
                m[i * ny + j] = 1
    return m


def bridge(name):
    """Bridge the two largest islands of net `name` on F+B; True if done (board edited in memory)."""
    global net
    net = b.FindNet(name).GetNetCode()
    mt = {l: mask(l, KT) for l in LAYERS}
    mv = bytearray(a | c for a, c in zip(mask(LAYERS[0], KV), mask(LAYERS[1], KV)))
    for f in b.GetFootprints():                          # no via hop on any pad, own net included (no via-in-pad)
        for p in f.Pads():
            r = p.GetBoundingBox()
            lx, ty, rx, by_ = M(r.GetLeft()), M(r.GetTop()), M(r.GetRight()), M(r.GetBottom())
            k = C.VIA_D / 2 + 0.05
            for i in range(max(0, int((lx - k - x0) / G)), min(nx, int((rx + k - x0) / G) + 2)):
                for j in range(max(0, int((ty - k - y0) / G)), min(ny, int((by_ + k - y0) / G) + 2)):
                    px, py = x0 + i * G, y0 + j * G
                    if math.hypot(max(lx - px, 0, px - rx), max(ty - py, 0, py - by_)) < k: mv[i * ny + j] = 1
    isl = C.net_islands(b, net)
    if len(isl) < 2:
        return True
    isl.sort(key=len, reverse=True)


    def anchors(g):
        out = []
        for it in g:
            if it.GetClass() == "PCB_VIA":
                out += [(M(it.GetPosition().x), M(it.GetPosition().y), l) for l in LAYERS]
            elif it.GetClass() == "PCB_TRACK" and it.GetLayer() in LAYERS:
                out += [(M(q.x), M(q.y), it.GetLayer()) for q in (it.GetStart(), it.GetEnd())]
            elif it.GetClass() == "PAD":
                out += [(M(it.GetPosition().x), M(it.GetPosition().y), l) for l in LAYERS if it.IsOnLayer(l)]
        return out


    cell = lambda x, y: (round((x - x0) / G), round((y - y0) / G))  # noqa: E731
    src = {(*cell(x, y), l) for x, y, l in anchors(isl[1])}
    dst = {(*cell(x, y), l): (x, y) for x, y, l in anchors(isl[0])}
    li = {LAYERS[0]: 0, LAYERS[1]: 1}
    dist, prev, pq = {}, {}, []
    for s in src:
        dist[s] = 0; heapq.heappush(pq, (0, s))
    found = None
    while pq:
        d, u = heapq.heappop(pq)
        if u in dst and d > 0 or (u in dst and u not in src):
            found = u; break
        if d > dist.get(u, 1e18): continue
        i, j, l = u
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            v = (i + dx, j + dy, l)
            if not (0 <= v[0] < nx and 0 <= v[1] < ny): continue
            if mt[l][v[0] * ny + v[1]] and v not in dst: continue
            nd = d + (1.414 if dx and dy else 1)
            if nd < dist.get(v, 1e18): dist[v] = nd; prev[v] = u; heapq.heappush(pq, (nd, v))
        if not mv[i * ny + j]:
            v = (i, j, LAYERS[1 - li[l]])
            nd = d + VIA_COST / G
            if nd < dist.get(v, 1e18): dist[v] = nd; prev[v] = u; heapq.heappush(pq, (nd, v))
    if not found:
        seen = {k for k in dist}
        print(name, "no F+B path; reached cells", len(seen), "src", sorted({(round(x0 + i * G, 2), round(y0 + j * G, 2), l) for i, j, l in src})[:4],
              "dst sample", list(dst.values())[:4])
        return False
    pts = [found]
    while pts[-1] in prev: pts.append(prev[pts[-1]])
    pts.reverse()
    P = [(x0 + i * G, y0 + j * G, l) for i, j, l in pts]
    P[-1] = (*dst[found], found[2])
    # split into runs per layer; collapse collinear points
    runs, vias = [], []
    cur = [P[0]]
    for q in P[1:]:
        if q[2] != cur[-1][2]:
            runs.append(cur); vias.append(cur[-1][:2]); cur = [(cur[-1][0], cur[-1][1], q[2])]
        else:
            cur.append(q)
    runs.append(cur)
    ok, segs = True, 0
    for v in vias:
        if not C.try_via(b, net, v): ok = False; print("via rejected", [round(c, 2) for c in v])
    for r in runs:
        s = [r[0]]
        for k in range(1, len(r) - 1):
            a, m_, c = s[-1], r[k], r[k + 1]
            if abs((m_[0] - a[0]) * (c[1] - a[1]) - (m_[1] - a[1]) * (c[0] - a[0])) > 1e-6: s.append(m_)
        s.append(r[-1])
        for a, c in zip(s, s[1:]):
            if math.dist(a[:2], c[:2]) < 1e-6: continue
            if C.try_segment(b, net, a[2], a[:2], c[:2]) is None: ok = False; print("segment rejected", a, c)
            segs += 1
    if not ok: print(name, "rejected"); return False
    L = sum(math.dist(p[:2], q[:2]) for p, q in zip(P, P[1:]) if p[2] == q[2])
    print(name, "bridged:", round(L, 2), "mm,", segs, "segments,", len(vias), "vias", [[round(c, 2) for c in v] for v in vias])
    return True


# never ripped: plane nets (islands join through the zones) and power/high-current nets (a maze detour would add resistance)
NO_RIP = {"GND", "+3V0", "VBUS", "VSYS", "VBAT", "LDO_OUT", "DOCK_VBUS", "BRIDGE_RTN", "OUT_A", "OUT_B", "VDD11", "VLXSMPS"}


def rip_near(name, R):
    nc = b.FindNet(name).GetNetCode()
    isl = sorted(C.net_islands(b, nc), key=len)
    pads = [it for it in isl[0] if it.GetClass() == "PAD"] or [it for g in isl for it in g if it.GetClass() == "PAD"]
    ripped = set()
    for t in list(b.GetTracks()):
        if t.GetNetCode() == nc or t.GetNetname() in NO_RIP or t.IsLocked():
            continue
        for p in pads:
            if any(t.IsOnLayer(l) and p.IsOnLayer(l) and t.GetEffectiveShape(l).Collide(p.GetEffectiveShape(l), mm(R))
                   for l in LAYERS):
                ripped.add(t.GetNetname()); b.Delete(t); break
    return sorted(ripped)


if "riponly" in sys.argv[3:]:                       # just clear the pad's surroundings (then bridge NET on another layer)
    print("ripped", rip_near(net_name, RIP or 0.6))
    pcbnew.ZONE_FILLER(b).Fill(b.Zones()); pcbnew.SaveBoard(path, b); sys.exit(0)
if not bridge(net_name):
    if not RIP:
        sys.exit(1)
    rn = rip_near(net_name, RIP)
    print("ripped", rn)
    if not bridge(net_name):
        sys.exit(1)
    for n in rn:
        for _ in range(4):                          # a ripped net may fall into several islands
            if len(C.net_islands(b, b.FindNet(n).GetNetCode())) < 2:
                break
            if not bridge(n):
                sys.exit(1)
pcbnew.ZONE_FILLER(b).Fill(b.Zones()); pcbnew.SaveBoard(path, b)
print("saved")
