"""Post-route Kelvin fix for the current-sense shunt R21 (Phase 2 board, 2026-10-07, LN-M03).

Replaces the router's short B.Cu GND stub(s) and via(s) at the R21 GND pad with GND vias hugging the pad (0.25 mm stubs).
Options scored with sim/noise on the mid-board R21 (LN-M03, limit 2 %): stub 3.31 % / one edge via 2.38 % / two edge
vias 1.29 % / via-in-pad 1.54 % (needs filled+capped vias: extra fab cost). DRC 0 for all.

Generalised 2026-10-07 (B-DOC-AUDIT-0007, R21 moved to the board edge for MZD-4): the pad position, size and axis are read
from the board (pad 1 BRIDGE_RTN -> pad 2 GND = axis u). Spots: both sides of the GND pad across u ("edges"), plus one
beyond the pad along u ("edge3"); a spot is skipped if it would not clear other copper or sits < 0.3 mm from the board edge.

    systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 \
        python3 hw/pod/kelvin_r21.py IN.kicad_pcb OUT.kicad_pcb edge3 [rip]

`rip`: a side spot blocked by UNLOCKED copper of another net (a router via/stub) is cleared: those items are deleted and
their nets printed ("ripped NET"); reconnect each with hw/pod/fb_bridge.py BOARD NET, then DRC. (2026-10-07: a router
GA_P via sat 0.37 mm from the left spot at the edge position; pre-placing the vias before routing instead left U1 pins
11/27 boxed in on two routes.)
"""
import math
import pathlib
import sys

import pcbnew

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import close_gaps as C  # noqa: E402

EDGE = 0.3
src, dst, mode = sys.argv[1], sys.argv[2], sys.argv[3]
RIP = "rip" in sys.argv[4:]
b = pcbnew.LoadBoard(src); M, mm = pcbnew.ToMM, pcbnew.FromMM
gnd = b.FindNet("GND").GetNetCode()
r21 = b.FindFootprintByReference("R21")
pg = next(p for p in r21.Pads() if p.GetNetname() == "GND")
p1 = next(p for p in r21.Pads() if p.GetNetname() != "GND" and p.GetNumber())
px, py = M(pg.GetPosition().x), M(pg.GetPosition().y)
ux, uy = px - M(p1.GetPosition().x), py - M(p1.GetPosition().y)
n = math.hypot(ux, uy); ux, uy = ux / n, uy / n
nx, ny = -uy, ux
bb = pg.GetBoundingBox()
w, h = M(bb.GetWidth()), M(bb.GetHeight())
half_u = abs(ux) * w / 2 + abs(uy) * h / 2
half_n = abs(nx) * w / 2 + abs(ny) * h / 2

# remove the router's short GND items at the pad (every point within 0.75 mm of the pad centre)
for t in list(b.GetTracks()):
    pts = [t.GetPosition()] if t.GetClass() == "PCB_VIA" else [t.GetStart(), t.GetEnd()]
    if t.GetNetCode() == gnd and not t.IsLocked() and all(math.hypot(M(q.x) - px, M(q.y) - py) < 0.75 for q in pts):
        b.Delete(t)

side = [(px + nx * (half_n + 0.12), py + ny * (half_n + 0.12)), (px - nx * (half_n + 0.12), py - ny * (half_n + 0.12))]
if mode == "edges":
    spots = side
elif mode == "edge3":
    spots = side + [(px + ux * (half_u + 0.12), py + uy * (half_u + 0.12))]
else:                     # via in pad (needs filled + capped vias)
    spots = [(px, py)]
ebb = b.GetBoardEdgesBoundingBox()
X0, Y0, X1, Y1 = (M(v) for v in (ebb.GetLeft(), ebb.GetTop(), ebb.GetRight(), ebb.GetBottom()))
added = 0
have = [(M(t.GetPosition().x), M(t.GetPosition().y)) for t in b.GetTracks() if t.GetClass() == "PCB_VIA" and t.GetNetCode() == gnd]
for s in spots:
    r = C.VIA_D / 2
    if any(math.hypot(s[0] - h[0], s[1] - h[1]) < 0.05 for h in have):
        print("present", [round(v, 2) for v in s]); added += 1; continue
    if min(s[0] - X0, s[1] - Y0, X1 - s[0], Y1 - s[1]) < r + EDGE:
        print("edge", [round(v, 2) for v in s]); continue
    circ = pcbnew.SHAPE_CIRCLE(pcbnew.VECTOR2I(mm(s[0]), mm(s[1])), mm(r))
    if RIP and s in side and not all(C.clear(b, gnd, l, circ) for l in C.OUTER):
        for t in list(b.GetTracks()):
            if t.GetNetCode() != gnd and not t.IsLocked() and any(t.IsOnLayer(l) and t.GetEffectiveShape(l).Collide(circ, mm(C.CLR)) for l in C.OUTER):
                print("ripped", t.GetNetname(), t.GetClass()); b.Delete(t)
    if all(C.clear(b, gnd, l, circ) for l in C.OUTER):
        v = pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(mm(s[0]), mm(s[1]))); v.SetWidth(mm(C.VIA_D)); v.SetDrill(mm(C.VIA_DRILL)); v.SetNetCode(gnd); b.Add(v); added += 1
        if s != (px, py):
            t = pcbnew.PCB_TRACK(b); t.SetStart(pcbnew.VECTOR2I(mm(px), mm(py))); t.SetEnd(pcbnew.VECTOR2I(mm(s[0]), mm(s[1])))
            t.SetWidth(mm(0.25)); t.SetLayer(pcbnew.B_Cu); t.SetNetCode(gnd); b.Add(t)
    else:
        print("blocked", [round(v, 2) for v in s])
pcbnew.ZONE_FILLER(b).Fill(b.Zones()); pcbnew.SaveBoard(dst, b)
print(mode, "R21 GND pad", (round(px, 2), round(py, 2)), "vias added", added)
