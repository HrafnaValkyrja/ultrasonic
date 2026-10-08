"""Hand-finish for the last few nets FreeRouting leaves open: a 4-layer (F, In3, In4, B; In1/In2 stay planes) grid maze
router for ONE net, joining the listed pads in order. Own-net copper is not an obstacle; every other net's tracks, vias,
pads and rule areas are, with the JLC 6L fine rules (track 0.09 + clearance 0.10, via 0.25/0.15). Writes in place.

    systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 \
        python3 hw/pod/route_net3d.py BOARD.kicad_pcb NET REF.PAD REF.PAD [REF.PAD ...]

Phase 3 (K4), 2026-10-08: companion of inner_bridge.py, which needs a legal via beside the pad (none on a QFN edge pad).
"""
import sys, math, heapq, pathlib, pcbnew
M, mm = pcbnew.ToMM, pcbnew.FromMM
TRACK, CLR, VIA, DRILL = 0.10, 0.10, 0.25, 0.15
LAYS = [pcbnew.F_Cu, pcbnew.In3_Cu, pcbnew.In4_Cu, pcbnew.B_Cu]
G = 0.05
import os
VIA_COST = float(os.environ.get("VIA_COST", 12))


def main():
    path, net_name, *pads = sys.argv[1:]
    b = pcbnew.LoadBoard(path)
    net = b.FindNet(net_name).GetNetCode()
    bb = b.GetBoardEdgesBoundingBox()
    x0, y0, W, H = M(bb.GetLeft()), M(bb.GetTop()), M(bb.GetWidth()), M(bb.GetHeight())
    nx, ny = int(W / G) + 1, int(H / G) + 1
    nl = len(LAYS)
    tb = [bytearray(nx * ny) for _ in range(nl)]      # track centre blocked
    vb = [bytearray(nx * ny) for _ in range(nl)]      # via centre blocked
    edge = 0.3

    def mark(arr, o, keep):
        if o[0] == "c":
            _, cx, cy, r = o; lo_x, hi_x, lo_y, hi_y = cx - r, cx + r, cy - r, cy + r
        elif o[0] == "r":
            _, lo_x, lo_y, hi_x, hi_y = o
        else:
            _, ax, ay, bx, by, r = o; lo_x, hi_x, lo_y, hi_y = min(ax, bx) - r, max(ax, bx) + r, min(ay, by) - r, max(ay, by) + r
        for i in range(max(0, int((lo_x - keep - x0) / G)), min(nx, int((hi_x + keep - x0) / G) + 2)):
            for j in range(max(0, int((lo_y - keep - y0) / G)), min(ny, int((hi_y + keep - y0) / G) + 2)):
                px, py = x0 + i * G, y0 + j * G
                if o[0] == "c":
                    d = math.hypot(px - o[1], py - o[2]) - o[3]
                elif o[0] == "r":
                    d = math.hypot(max(o[1] - px, 0, px - o[3]), max(o[2] - py, 0, py - o[4]))
                else:
                    dx, dy = o[3] - o[1], o[4] - o[2]; L = dx * dx + dy * dy
                    u = 0 if L == 0 else max(0, min(1, ((px - o[1]) * dx + (py - o[2]) * dy) / L))
                    d = math.hypot(px - o[1] - u * dx, py - o[2] - u * dy) - o[5]
                if d < keep:
                    arr[i * ny + j] = 1

    kt = CLR + TRACK / 2 + 0.01
    kv = CLR + VIA / 2 + 0.01
    for k, L in enumerate(LAYS):
        for t in b.GetTracks():
            if t.GetNetCode() == net:
                continue
            if t.GetClass() == "PCB_VIA":
                p = t.GetPosition()
                o = ("c", M(p.x), M(p.y), M(t.GetWidth(L)) / 2)
            elif t.IsOnLayer(L):
                o = ("s", M(t.GetStart().x), M(t.GetStart().y), M(t.GetEnd().x), M(t.GetEnd().y), M(t.GetWidth()) / 2)
            else:
                continue
            mark(tb[k], o, kt); mark(vb[k], o, kv)
        for f in b.GetFootprints():
            for p in f.Pads():
                if p.GetNetCode() != net and p.IsOnLayer(L):
                    r = p.GetBoundingBox()
                    o = ("r", M(r.GetLeft()), M(r.GetTop()), M(r.GetRight()), M(r.GetBottom()))
                    mark(tb[k], o, kt); mark(vb[k], o, kv)
        areas = [z for z in b.Zones() if z.GetIsRuleArea() and z.IsOnLayer(L) and z.GetDoNotAllowTracks()]
        for i in range(nx):
            for j in range(ny):
                px, py = x0 + i * G, y0 + j * G
                if px < x0 + edge or px > x0 + W - edge or py < y0 + edge or py > y0 + H - edge:
                    tb[k][i * ny + j] = vb[k][i * ny + j] = 1; continue
                if areas and any(z.Outline().Collide(pcbnew.VECTOR2I(mm(px), mm(py)), mm(kt)) for z in areas):
                    tb[k][i * ny + j] = vb[k][i * ny + j] = 1
    # board outline cut-outs (notch/window) are Edge.Cuts: sample them as obstacles too
    for d in b.GetDrawings():
        if d.GetLayer() == pcbnew.Edge_Cuts:
            s = d.GetStart(); e = d.GetEnd()
            if d.GetShape() == pcbnew.SHAPE_T_SEGMENT:
                o = ("s", M(s.x), M(s.y), M(e.x), M(e.y), 0.0)
                for k in range(nl):
                    mark(tb[k], o, kt + 0.15); mark(vb[k], o, kv + 0.15)

    def cell(p):
        return (round((p[0] - x0) / G), round((p[1] - y0) / G))

    def padinfo(spec):
        if spec.startswith("@"):                      # a point reachable on every layer (e.g. a pre-placed via)
            xy, _, ls = spec[1:].partition("/")           # "@x,y" or "@x,y/1,2" (layer indices into LAYS)
            x, y = map(float, xy.split(","))
            return (x, y), [int(q) for q in ls.split(",")] if ls else list(range(nl))
        ref, pn = spec.split(".")
        p = b.FindFootprintByReference(ref).FindPadByNumber(pn)
        pos = (M(p.GetPosition().x), M(p.GetPosition().y))
        ls = [k for k, L in enumerate(LAYS) if p.IsOnLayer(L)]
        return pos, ls

    def route(a, c):
        (pa, la), (pc, lc) = a, c
        for pt, ls in ((pa, la), (pc, lc)):
            for k in ls:
                x, y = cell(pt)
                for dx in range(-3, 4):
                    for dy in range(-3, 4):          # open a small mouth at the pad centre
                        if abs(dx) + abs(dy) <= 4:
                            tb[k][(x + dx) * ny + y + dy] = 0
        starts = [(cell(pa), k) for k in la]
        goals = {(cell(pc), k) for k in lc}
        dist = {s: 0 for s in starts}; prev = {}; pq = [(0, s) for s in starts]
        found = None
        while pq:
            d, u = heapq.heappop(pq)
            if u in goals:
                found = u; break
            if d > dist[u]:
                continue
            (x, y), k = u
            nbrs = [(((x + dx, y + dy), k), 1.414 if dx and dy else 1) for dx, dy in
                    ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1))
                    if 0 <= x + dx < nx and 0 <= y + dy < ny and not tb[k][(x + dx) * ny + y + dy]
                    and (not (dx and dy) or (not tb[k][(x + dx) * ny + y] and not tb[k][x * ny + y + dy]))]
            if all(not vb[l][x * ny + y] for l in range(nl)):
                nbrs += [(((x, y), l), VIA_COST) for l in range(nl) if l != k and not tb[l][x * ny + y]]
            for v, c_ in nbrs:
                nd = d + c_
                if nd < dist.get(v, 1e18):
                    dist[v] = nd; prev[v] = u; heapq.heappush(pq, (nd, v))
        if not found:
            xs=[u[0][0] for u in dist]; ys=[u[0][1] for u in dist]
            print('  reached',len(dist),'states x',round(x0+min(xs)*G,2),round(x0+max(xs)*G,2),'y',round(y0+min(ys)*G,2),round(y0+max(ys)*G,2),'layers',sorted({u[1] for u in dist}))
            return None
        pts = [found]
        while pts[-1] in prev:
            pts.append(prev[pts[-1]])
        return list(reversed(pts))

    info = [padinfo(s) for s in pads]
    if os.environ.get("DBG"):
        for yy in [6.6 + 0.1 * q for q in range(0, 14)]:
            c_ = cell((8.4, yy)); print(round(yy, 2), [tb[k][c_[0] * ny + c_[1]] for k in range(nl)], [vb[k][c_[0] * ny + c_[1]] for k in range(nl)])
    for a, c in zip(info, info[1:]):
        path_ = route(a, c)
        if not path_:
            print("NO PATH between", a[0], c[0]); sys.exit(1)
        n_seg = n_via = 0
        pos = lambda u: a[0] if u == path_[0] else c[0] if u == path_[-1] else (x0 + u[0][0] * G, y0 + u[0][1] * G)
        run = [path_[0]]
        def flush(run):
            nonlocal n_seg
            pts = [pos(u) for u in run]
            simp = [pts[0]]
            for q in range(1, len(pts) - 1):
                p0, m_, n_ = simp[-1], pts[q], pts[q + 1]
                if abs((m_[0] - p0[0]) * (n_[1] - p0[1]) - (m_[1] - p0[1]) * (n_[0] - p0[0])) > 1e-6:
                    simp.append(m_)
            simp.append(pts[-1])
            simp[0], simp[-1] = (simp[0], simp[-1])
            for p0, p1 in zip(simp, simp[1:]):
                if math.hypot(p1[0] - p0[0], p1[1] - p0[1]) < 1e-6:
                    continue
                t = pcbnew.PCB_TRACK(b)
                t.SetStart(pcbnew.VECTOR2I(mm(p0[0]), mm(p0[1]))); t.SetEnd(pcbnew.VECTOR2I(mm(p1[0]), mm(p1[1])))
                t.SetWidth(mm(TRACK)); t.SetLayer(LAYS[run[0][1]]); t.SetNetCode(net); b.Add(t); n_seg += 1
        for u in path_[1:]:
            if u[1] != run[-1][1]:
                flush(run)
                v = pcbnew.PCB_VIA(b); at = pos(u)
                v.SetPosition(pcbnew.VECTOR2I(mm(at[0]), mm(at[1]))); v.SetWidth(mm(VIA)); v.SetDrill(mm(DRILL)); v.SetNetCode(net)
                b.Add(v); n_via += 1
                run = [u]
            else:
                run.append(u)
        flush(run)
        # snap ends onto pad centres
        print(f"{net_name}: {a[0]} -> {c[0]}: {n_seg} segments, {n_via} vias, cost {len(path_)}")
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(path, b)


main()
