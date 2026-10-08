"""Last-resort bridge for a boxed-in pad: maze-route a short trace on an INNER plane layer (default In2, the +3V0 plane)
from a legal via beside the pad to the nearest via of the net's other island. Kept only if the board saves; check DRC
(unconnected + plane islands) afterwards. Used 2026-10-07 for I2C_SCL at U1.26 (Phase 2 board), which no outer-layer
route could reach (8.97 mm on In2, plane stays one island, -4 mm2).

    systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 \
        python3 hw/pod/inner_bridge.py BOARD.kicad_pcb I2C_SCL U1 26 [In2|In1|F]

2026-10-07 (B-DOC-AUDIT-0007 re-route): layer F allowed (the lid face is nearly empty); pads on the layer and rule areas
(e.g. the mic-port keep-out) are obstacles; if the other island has no via, legal via spots beside its pads are targets
(a via + stub is added there).
"""
import sys, math, heapq, pathlib, pcbnew
sys.path.insert(0, str(pathlib.Path(__file__).parent)); import close_gaps as C
M = pcbnew.ToMM
path, net_name, ref, padnum = sys.argv[1:5]
layer_name = sys.argv[5] if len(sys.argv) > 5 else "In2"
LAY = {"In3": pcbnew.In3_Cu, "In4": pcbnew.In4_Cu, "In2": pcbnew.In2_Cu, "In1": pcbnew.In1_Cu, "F": pcbnew.F_Cu, "B": pcbnew.B_Cu}[layer_name]
b = pcbnew.LoadBoard(path); net = b.FindNet(net_name).GetNetCode()
G = 0.05; bb = b.GetBoardEdgesBoundingBox()
x0, y0, W, H = M(bb.GetLeft()), M(bb.GetTop()), M(bb.GetWidth()), M(bb.GetHeight())
nx, ny = int(W / G) + 1, int(H / G) + 1
blocked = bytearray(nx * ny)
edge = 0.3
obs = []
for t in b.GetTracks():
    if t.GetNetCode() == net or not t.IsOnLayer(LAY): continue
    if t.GetClass() == "PCB_VIA":
        p = t.GetPosition(); obs.append(("c", M(p.x), M(p.y), M(t.GetWidth(LAY)) / 2))
    else:
        obs.append(("s", M(t.GetStart().x), M(t.GetStart().y), M(t.GetEnd().x), M(t.GetEnd().y), M(t.GetWidth()) / 2))
for f in b.GetFootprints():                          # pads on this layer (outer layers only carry pads)
    for p in f.Pads():
        if p.GetNetCode() != net and p.IsOnLayer(LAY):
            bb = p.GetBoundingBox()
            obs.append(("r", M(bb.GetLeft()), M(bb.GetTop()), M(bb.GetRight()), M(bb.GetBottom()), 0.0))
keep = C.CLR + C.TRACK_W / 2 + 0.01
def dseg(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay; L = dx * dx + dy * dy
    u = 0 if L == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - ax - u * dx, py - ay - u * dy)
for o in obs:
    if o[0] == "c": _, cx, cy, r = o; lo_x, hi_x, lo_y, hi_y = cx - r, cx + r, cy - r, cy + r
    elif o[0] == "r": _, lo_x, lo_y, hi_x, hi_y, r = o
    else: _, ax, ay, bx2, by2, r = o; lo_x, hi_x, lo_y, hi_y = min(ax, bx2) - r, max(ax, bx2) + r, min(ay, by2) - r, max(ay, by2) + r
    R = r + keep
    for i in range(max(0, int((lo_x - keep - x0) / G)), min(nx, int((hi_x + keep - x0) / G) + 2)):
        for j in range(max(0, int((lo_y - keep - y0) / G)), min(ny, int((hi_y + keep - y0) / G) + 2)):
            px, py = x0 + i * G, y0 + j * G
            if o[0] == "c": d = math.hypot(px - o[1], py - o[2])
            elif o[0] == "r": d = math.hypot(max(o[1] - px, 0, px - o[3]), max(o[2] - py, 0, py - o[4]))
            else: d = dseg(px, py, o[1], o[2], o[3], o[4])
            if d < R: blocked[i * ny + j] = 1
areas = [z for z in b.Zones() if z.GetIsRuleArea() and z.IsOnLayer(LAY) and z.GetDoNotAllowTracks()]
for i in range(nx):
    for j in range(ny):
        px, py = x0 + i * G, y0 + j * G
        if any(z.Outline().Collide(pcbnew.VECTOR2I(pcbnew.FromMM(px), pcbnew.FromMM(py)), pcbnew.FromMM(keep)) for z in areas):
            blocked[i * ny + j] = 1; continue
        if px < x0 + edge or px > x0 + W - edge or py < y0 + edge or py > y0 + H - edge: blocked[i * ny + j] = 1
pp = b.FindFootprintByReference(ref).FindPadByNumber(padnum)
pad = (M(pp.GetPosition().x), M(pp.GetPosition().y), {l for l in C.OUTER if pp.IsOnLayer(l)})
spots = [s[0] for s in C.via_spots(b, net, pad, radii=(0.45, 0.6, 0.8, 1.0), n_ang=24) if s[1]]
isl = C.net_islands(b, net)
mine = next(g for g in isl if any(it.m_Uuid.AsString() == pp.m_Uuid.AsString() for it in g))
targets = [(M(v.GetPosition().x), M(v.GetPosition().y)) for g in isl if g is not mine for v in g if v.GetClass() == "PCB_VIA"]
own = [(M(v.GetPosition().x), M(v.GetPosition().y)) for v in mine if v.GetClass() == "PCB_VIA"]
spots = own + spots                                   # the pad's island may already own a via: start there (no new via)
tpad = {}
if not targets:                                       # other island has no via: legal via spots beside its pads
    for g in isl:
        if g is mine: continue
        for it in g:
            if it.GetClass() == "PAD":
                a = (M(it.GetPosition().x), M(it.GetPosition().y), {l for l in C.OUTER if it.IsOnLayer(l)})
                for s_ in C.via_spots(b, net, a, radii=(0.45, 0.6, 0.8), n_ang=16):
                    if s_[1]: targets.append(s_[0]); tpad[s_[0]] = a
cell = lambda p: (round((p[0] - x0) / G), round((p[1] - y0) / G))
goal = {cell(t): t for t in targets}
for g in goal: blocked[g[0] * ny + g[1]] = 0
best = None
for sp in spots:
    s = cell(sp); blocked[s[0] * ny + s[1]] = 0
    dist = {s: 0}; prev = {}; pq = [(0, s)]
    found = None
    while pq:
        d, u = heapq.heappop(pq)
        if u in goal: found = u; break
        if d > dist[u]: continue
        for dx, dy in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)):
            v = (u[0] + dx, u[1] + dy)
            if not (0 <= v[0] < nx and 0 <= v[1] < ny) or blocked[v[0] * ny + v[1]]: continue
            nd = d + (1.414 if dx and dy else 1)
            if nd < dist.get(v, 1e18): dist[v] = nd; prev[v] = u; heapq.heappush(pq, (nd, v))
    if found and (best is None or dist[found] < best[0]):
        pts = [found]
        while pts[-1] != s: pts.append(prev[pts[-1]])
        best = (dist[found], sp, [(x0 + p[0] * G, y0 + p[1] * G) for p in reversed(pts)], goal[found])
if not best: print("no maze path on", layer_name, "spots", len(spots), "targets", len(targets), "blocked %", round(100 * sum(blocked) / len(blocked))); sys.exit(1)
L, sp, pts, tgt = best
pts[0], pts[-1] = sp, tgt
# simplify collinear runs
simp = [pts[0]]
for k in range(1, len(pts) - 1):
    a, m, c = simp[-1], pts[k], pts[k + 1]
    if abs((m[0] - a[0]) * (c[1] - a[1]) - (m[1] - a[1]) * (c[0] - a[0])) > 1e-6: simp.append(m)
simp.append(pts[-1])
added = True if sp in own else C.try_via(b, net, sp)
if tgt in tpad:                                       # new via + stub at the far island
    a = tpad[tgt]
    if not (C.try_via(b, net, tgt) and C.try_segment(b, net, next(iter(a[2])), a[:2], tgt)): print("target via rejected"); sys.exit(1)
st = True if sp in own else C.try_segment(b, net, next(iter(pad[2])), pad[:2], sp)
segs_ok = added and st is not None
for q, r in zip(simp, simp[1:]):
    sg = C.try_segment(b, net, LAY, q, r)
    if sg is None: segs_ok = False; print("segment check failed at", q, r)
if not segs_ok: print("rejected"); sys.exit(1)
pcbnew.ZONE_FILLER(b).Fill(b.Zones()); pcbnew.SaveBoard(path, b)
print(layer_name, "path", round(L * G, 2), "mm,", len(simp) - 1, "segments, via", [round(v, 2) for v in sp], "-> target via", tgt)
