"""K4 two-board stack builder + placement rule check (ECR-0020 rev 3, V9-k4-board.yaml, owner O33).

    source tools/env.sh && systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 \
        python3 hw/pod/place_k4.py [--pack] [--L 11.8]

P = upper board (MCU, SMPS, bridge), M = lower board (mic, charger, LDO, dock, button). Joined by a Hirose BM28 30-pin pair at
identical stack XY: plug J21 on P's inner face (file F), receptacle J20 on M's inner face (file F); mated gap 0.6 mm [T].
Stack frame = M's file frame (x = 0 at the mic end, y = 0 top edge). P is flipped across the LONG axis, so a P file point
(x, y) sits at stack (x, H - y); its plug is placed rot 180 and then mates pin n to pin n.
Faces: P file B = outer top (MCU etc.), P file F = inner; M file F = inner (mic, charger ...), M file B = belly (SW1, dock pads,
magnet seats, port exit). The mic (1.08 mm) is taller than the gap, so P has a notch over it (Edge.Cuts) and no part sits there.
--pack lays out placement_P.yaml / placement_M.yaml with a greedy courtyard packer (no router; targets from the NEAR rules);
without it the yaml files are read. Writes out/P|M/placed.kicad_pcb + check.json (+ out/stack.json). Never routes.

Checks (place_r2 set, adapted): fit (+ notch), near, escape, pads (+ J3/J5), port keep-out (M, on the exit face B), LSE/VDDA/NRST
preroute (P), axis (M), density; 'far' replaced by: no switching part on M within 10 mm of the port; new: gap (inner-face part
heights <= 0.6, and P-F x M-F overlaps), mate (BM28 pad n at the same x), notch.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import pcbnew
import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import place_r2 as R2                                # noqa: E402
R1, P = R2.R1, R2.P
mm, MM = pcbnew.FromMM, pcbnew.ToMM
K4 = HERE / "k4"
H = 12.0
GAP = 0.6                                            # BM28 mated height [V: Hirose BM28 catalog Aug 2019, stacking height 0.6; tol +-0.05 still T]
# part heights (mm) [T: typical, none read from datasheets except where noted]; default by footprint family
HEIGHT = {"C_0201": 0.33, "R_0201": 0.26, "C_0402": 0.5, "R_0402": 0.35, "C_0603": 0.9, "Nexperia_SOT1216": 0.37,
          "D_SOD-882": 0.5, "X1SON": 0.4, "X2SON": 0.4, "DSBGA": 0.5, "SOT-553": 0.55, "TestPoint": 0.0, "TestDot": 0.0,
          "WirePad": 0.0, "BM28": 0.0, "SW-SMD": 0.65, "Knowles": 1.08, "QFN-48": 0.9, "L0806": 1.0, "Crystal": 0.7}
MIC_CX = 1.75                                        # mic centre x; the courtyard then starts at ~0.15
MIC_ROT, _MIC_R, MIC_CY = None, None, H / 2
U1_CY = 4.5
U1_ROT = 270
SWITCHING = {"L1", "Q1", "Q2", "U1"}
FAR_MIN = 10.0
SW1_X = 5.3
CONN_XY = None                                       # set in plan(): BM28 centre in the stack frame
F_PREF = {  # packer: faces to try in order. B = outer (P top / M belly). 'F' = inner (<= GAP tall)
    "P": {"Q1": "BF", "Q2": "BF", "R3": "FB", "R4": "FB", "R5": "FB", "R6": "FB", "R21": "FB", "R22": "FB", "R23": "FB",
          "C22": "FB", "R15": "FB", "R16": "FB", "C14": "B", "C4": "B", "C7": "B", "L1": "B", "Y1": "B", "J1": "BF", "J2": "BF"},
    "M": {"J5": "B", "J7": "B", "J8": "B", "J9": "B", "J3": "B", "J4": "B", "J10": "B", "J11": "B", "SW1": "B", "C21": "B",
          "TP6": "B"}}


def height(fpid):
    n = fpid.split(":")[1]
    for k, v in HEIGHT.items():
        if n.startswith(k):
            return v
    return 0.5


def fp_name(ref, fpid):
    if ref == "J20":
        return "lcsc", "BM28B0.6-30DS_2-0.35V"
    return tuple(fpid.split(":"))


_REL = {}
_SCR = pcbnew.BOARD()                                 # Flip() needs the footprint to live on a board


def rel(fpid, ref, rot, flip):
    """Courtyard rect (l, t, r, b), port offset and pad rects of a footprint at the origin, as build() will place it."""
    key = (fpid, ref == "J20", rot, flip)
    if key not in _REL:
        lib, name = fp_name(ref, fpid)
        fp = pcbnew.FootprintLoad(R1.P.fp_lib(lib), name)
        _SCR.Add(fp)
        fp.SetPosition(pcbnew.VECTOR2I(0, 0)); fp.SetOrientationDegrees(rot)
        if flip:
            fp.Flip(pcbnew.VECTOR2I(0, 0), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        cy = fp.GetCourtyard(pcbnew.B_CrtYd if flip else pcbnew.F_CrtYd)
        bb = cy.BBox() if cy.OutlineCount() else fp.GetBoundingBox(False)
        r = tuple(MM(v) for v in (bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom()))
        pb = [MM(q) for q in (1e9, 1e9, -1e9, -1e9)] if False else [1e9, 1e9, -1e9, -1e9]
        for p in fp.Pads():
            if p.GetAttribute() != pcbnew.PAD_ATTRIB_NPTH:
                q = p.GetBoundingBox()
                pb = [min(pb[0], MM(q.GetLeft())), min(pb[1], MM(q.GetTop())), max(pb[2], MM(q.GetRight())), max(pb[3], MM(q.GetBottom()))]
        r = (min(r[0], pb[0] - 0.12), min(r[1], pb[1] - 0.12), max(r[2], pb[2] + 0.12), max(r[3], pb[3] + 0.12))
        port = next(((MM(p.GetPosition().x), MM(p.GetPosition().y)) for p in fp.Pads()
                     if p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH), None)
        _REL[key] = (r, port, tuple(pb))
    return _REL[key]


def shift(r, x, y):
    return (r[0] + x, r[1] + y, r[2] + x, r[3] + y)


def hit(a, b, m=0.0):
    return a[0] < b[2] + m and b[0] < a[2] + m and a[1] < b[3] + m and b[1] < a[3] + m


# --------------------------------------------------------------------------------------------------- planning (packer)
def _mic_rot(fpid):
    best = None
    for rot in (0, 180, 90, 270):
        r, port, _ = rel(fpid, "U2", rot, False)
        key = (round(r[2] - r[0], 2), port[0])
        if best is None or key < best[0]:
            best = (key, rot, r, port)
    return best[1], best[2], H / 2 - best[3][1]




def notch_rect():
    """P's Edge.Cuts notch over the mic: through-board, so it is also keep-out on both P faces."""
    return (-0.5, H - MIC_CY - _MIC_R[3], MIC_CX + _MIC_R[2] + 0.1, H - MIC_CY - _MIC_R[1])   # P file frame (y mirrored)


SOLDER_WIN = {"on": False}                          # P: through cutout over M's cell-wire pads J4/J5 (stack x 10.55, M y 7.9..11.6), P file frame y = H - y


def solder_win():
    return (9.45, H - 11.6, 11.65, H - 7.9)


CX_FIX = [None]                                      # --cx: hold the J20/J21 mate x while L grows


def u1_cx(L):
    return CX_FIX[0] if CX_FIX[0] is not None else L - 4.15 - 0.05


def pack(board, comps, nets, L):
    """Greedy courtyard packer. Returns {ref: [x, y, rot, side]} in the board's file frame. Fixed parts first, then the rest by
    NEAR-rule pull (distance to the anchor pads), nearest free grid spot wins."""
    fixed, order = {}, []
    occ = {"F": [], "B": []}            # occupied rects per face (file frame)
    blocked = {"F": [], "B": []}
    cx = u1_cx(L)
    if board == "P":
        n = notch_rect()
        blocked["F"].append(n); blocked["B"].append(n)
        if SOLDER_WIN["on"]:
            w = solder_win(); blocked["F"].append(w); blocked["B"].append(w)
        blocked["F"] += PINNER
        fixed.update({"U1": (cx, U1_CY, U1_ROT, "B"), "J21": (cx, H / 2, 180, "F")})
        if VIP["on"]:     # no inner-face part over U1's exposed pad: a +3V0 / signal via there would short to the EP (GND)
            blocked["F"].append((cx - 4.1, U1_CY - 4.1, cx + 4.1, U1_CY + 4.1))   # EP + via-in-pad ring (pad end 3.88 + via + clearance)
    else:
        fixed.update({"U2": (MIC_CX, MIC_CY, MIC_ROT, "F"), "U3": (4.6, 2.3, 90, "F"), "J20": (cx, H / 2, 0, "F"), "SW1": (SW1_X, H / 2, 0, "B"),
                      "J3": (10.55, 1.6, 0, "B"), "J10": (10.55, 3.8, 0, "B"), "J11": (10.55, 6.0, 0, "B"),
                      "J4": (10.55, 8.5, 0, "B"), "J5": (10.55, 10.9, 0, "B")})
        blocked["B"] += [(6.4, 1.2, 9.4, 4.2), (6.4, 7.8, 9.4, 10.8)]       # magnet seats 3 x 3 [E, k4-dock.yaml A]
        if VIP["on"]:     # room for the J20 via-in-pad rows (FreeRouting cannot escape the 0.35 mm pitch pads otherwise)
            for rr in ((cx - 2.9, H / 2 - 2.1, cx + 1.2, H / 2 - 0.8), (cx - 2.9, H / 2 + 0.8, cx + 1.2, H / 2 + 2.1)):
                blocked["F"].append(rr); blocked["B"].append(rr)
        _, port, _ = rel(comps["U2"], "U2", MIC_ROT, False)
        blocked["B"].append((MIC_CX + port[0] - 1.6, MIC_CY + port[1] - 1.6, MIC_CX + port[0] + 1.6, MIC_CY + port[1] + 1.6))   # duct-seat keep-out
        # P's inner-face parts block M's inner face wherever both would be taller than the gap together (all of them, simply)
    pos = {}
    ring = None
    for ref, (x, y, rot, side) in fixed.items():
        pos[ref] = (x, y, rot, side)
        occ[side].append(shift(rel(comps[ref], ref, rot, side == "B")[0], x, y))
    if board == "P":
        ring = shift(rel(comps["U1"], "U1", U1_ROT, True)[2], cx, H / 2)
        ring = (ring[0] - 0.7, ring[1] - 0.7, ring[2] + 0.7, ring[3] + 0.7)
    anchor = {}
    for part, a, lim in R2.NEAR:
        aref, _, apin = a.partition(".")
        anchor.setdefault(part, []).append((aref, apin or None, lim))
    prio = ["Y1", "C11", "C12", "C6", "C10", "L1", "C1", "C2", "C3", "C8", "C9", "C7", "C5", "R1", "R2", "C4",
            "C14", "Q1", "Q2", "R3", "R4", "R5", "R6", "R21", "C22", "R22", "R23", "R15", "R16", "J1", "J2",
            "C13", "C21", "U4", "C15", "C16", "C17", "C18", "D5", "D4", "U6", "R20", "TP6", "R8", "R9", "R10", "R12", "R13",
            "R14", "RT1", "C19", "J7", "J8", "J9"]
    rest = [r for r in comps if r not in pos and r not in prio]
    todo = [r for r in prio if r in comps and r not in pos] + sorted(rest)
    pads_of = {}                                      # ref -> [(net, pin, (x, y))] for placed parts, for pull targets
    def pad_xy(ref):
        x, y, rot, side = pos[ref]
        lib, name = fp_name(ref, comps[ref])
        fp = pcbnew.FootprintLoad(R1.P.fp_lib(lib), name)
        _SCR.Add(fp)
        fp.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y))); fp.SetOrientationDegrees(rot)
        if side == "B":
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        out = []
        for p in fp.Pads():
            if p.GetNumber():
                for nn, nodes in nets.items():
                    if (ref, p.GetNumber()) in nodes:
                        out.append((nn, p.GetNumber(), (MM(p.GetPosition().x), MM(p.GetPosition().y))))
        return out
    cache = {}
    def pads(ref):
        if ref not in cache:
            cache[ref] = pad_xy(ref)
        return cache[ref]
    def targets(ref, nets_of_ref):
        pts = []
        for aref, apin, lim in anchor.get(ref, []):
            if aref in pos:
                for nn, pin, xy in pads(aref):
                    if nn != "GND" and nn in nets_of_ref and (apin is None or pin == apin):
                        pts.append(xy)
        for q in PULL.get(ref, ()):                   # packer-only clustering (not a rule)
            if q in pos:
                pts.append((pos[q][0], pos[q][1]))
        if not pts:                                   # weak pull: the pads that share a non-GND net with placed parts
            for q in pos:
                for nn, pin, xy in pads(q):
                    if nn in nets_of_ref and nn != "GND":
                        pts.append(xy)
        return pts
    nets_by_ref = {}
    for nn, nodes in nets.items():
        for r, _ in nodes:
            nets_by_ref.setdefault(r, set()).add(nn)
    fails = []
    for ref in todo:
        h = height(comps[ref])
        faces = F_PREF[board].get(ref, "BF")
        faces = [f for f in faces if f == "B" or h <= GAP]
        pts = targets(ref, nets_by_ref.get(ref, set()))
        tx = sum(p[0] for p in pts) / len(pts) if pts else cx
        ty = sum(p[1] for p in pts) / len(pts) if pts else H / 2
        best = None
        for f in faces:
            for rot in (0, 90, 180, 270):
                r0, _, pb0 = rel(comps[ref], ref, rot, f == "B")
                w, hh = r0[2] - r0[0], r0[3] - r0[1]
                x = max(0.33 - pb0[0], 0.03 - r0[0])
                while x + max(pb0[2] + 0.33, r0[2] + 0.03) <= L:
                    y = max(0.33 - pb0[1], 0.03 - r0[1])
                    while y + max(pb0[3] + 0.33, r0[3] + 0.03) <= H:
                        r = shift(r0, x, y)
                        if (not any(hit(r, o) for o in occ[f]) and not any(hit(r, o) for o in blocked[f])
                                and not (board == "P" and f == "B" and ref not in R2.ESCAPE_OK and hit(r, ring))
                                and not (board == "P" and hit(shift(pb0, x, y), (n[0], n[1] - 0.33, n[2] + 0.33, n[3] + 0.33)))):
                            d = (math.hypot(x - tx, y - ty) if pts else math.hypot(x - tx, y - ty) * 0.2) + (0.3 if f != faces[0] else 0)
                            if pts:
                                d = sum(math.hypot(x - px_, y - py_) for px_, py_ in pts) / len(pts) + 0.001 * math.hypot(x - tx, y - ty)
                            d += (0.0 if f == faces[0] else 0.5)
                            if best is None or d < best[0]:
                                best = (d, x, y, rot, f)
                        y += 0.1
                    x += 0.1
        if best is None:
            fails.append(ref)
            continue
        _, x, y, rot, f = best
        pos[ref] = (round(x, 2), round(y, 2), rot, f)
        occ[f].append(shift(rel(comps[ref], ref, rot, f == "B")[0], x, y))
        cache.pop(ref, None)
        for grp, pins in ((("Y1", "C11", "C12"), ("3", "4")), (("C6", "C10"), ("7", "8", "9"))):
            if board == "P" and ref == grp[-1] and all(g in pos for g in grp):
                pts = [xy for nn, pin, xy in pads("U1") if pin in pins]
                rs = [shift(rel(comps[g], g, pos[g][2], pos[g][3] == "B")[0], pos[g][0], pos[g][1]) for g in grp]
                hull = (min([p[0] for p in pts] + [r[0] for r in rs]) - 0.2, min([p[1] for p in pts] + [r[1] for r in rs]) - 0.2,
                        max([p[0] for p in pts] + [r[2] for r in rs]) + 0.2, max([p[1] for p in pts] + [r[3] for r in rs]) + 0.2)
                occ["B"].append(hull)      # a lane for the pre-routed tracks (U1's own occupancy is separate)
    return {k: list(v) for k, v in pos.items()}, fails


PULL = {"Q1": ["C14"], "Q2": ["Q1", "C14"], "C14": ["Q1", "Q2"], "R21": ["Q1", "Q2"], "R22": ["R21"], "R3": ["Q1"], "R4": ["Q1"], "R5": ["Q2"], "R6": ["Q2"]}
PINNER = []                                          # P's inner-face courtyards in the stack frame (y mirrored), set after P is packed


# --------------------------------------------------------------------------------------------------- building
def outline_k4(b, board, L):
    """M: rounded rectangle; P: the same with the mic notch cut out of the left edge (sharp inner corners)."""
    V = lambda x, y: pcbnew.VECTOR2I(mm(x), mm(y))                # noqa: E731
    if board == "M":
        P.W, P.H, P.CORNER = L, H, 1.0
        P.outline(b)
        return
    n = notch_rect()
    x1, y0, y1 = L, n[1], n[3]
    r = 1.0
    segs = [((r, 0), (x1 - r, 0)), ((x1, r), (x1, H - r)), ((x1 - r, H), (r, H)), ((0, H - r), (0, y1)), ((0, y1), (n[2], y1)),
            ((n[2], y1), (n[2], y0)), ((n[2], y0), (0, y0)), ((0, y0), (0, r))]
    for a, c in segs:
        s = pcbnew.PCB_SHAPE(b); s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetLayer(pcbnew.Edge_Cuts)
        s.SetStart(V(*a)); s.SetEnd(V(*c)); s.SetWidth(mm(0.05)); b.Add(s)
    if SOLDER_WIN["on"]:
        w = solder_win()
        pts = [(w[0], w[1]), (w[2], w[1]), (w[2], w[3]), (w[0], w[3])]
        for q in range(4):
            s = pcbnew.PCB_SHAPE(b); s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetLayer(pcbnew.Edge_Cuts)
            s.SetStart(V(*pts[q])); s.SetEnd(V(*pts[(q + 1) % 4])); s.SetWidth(mm(0.05)); b.Add(s)
    k = r * (1 - math.sqrt(0.5))
    for st, mid, en in (((0, r), (k, k), (r, 0)), ((x1 - r, 0), (x1 - k, k), (x1, r)),
                        ((x1, H - r), (x1 - k, H - k), (x1 - r, H)), ((r, H), (k, H - k), (0, H - r))):
        a = pcbnew.PCB_SHAPE(b); a.SetShape(pcbnew.SHAPE_T_ARC); a.SetLayer(pcbnew.Edge_Cuts)
        a.SetArcGeometry(V(*st), V(*mid), V(*en)); a.SetWidth(mm(0.05)); b.Add(a)


def port_keepout_layer(b, px, py, layer, r=R2.PORT_KEEPOUT, n=36):
    z = pcbnew.ZONE(b)
    z.SetIsRuleArea(True); z.SetLayer(layer)
    z.SetDoNotAllowTracks(True); z.SetDoNotAllowVias(True); z.SetDoNotAllowZoneFills(True)
    z.SetDoNotAllowPads(False); z.SetDoNotAllowFootprints(False)
    z.SetZoneName("mic port keep-out R-ACO-P6")
    ol = z.Outline(); ol.NewOutline()
    R = r / math.cos(math.pi / n)
    for k in range(n):
        a = 2 * math.pi * k / n
        ol.Append(mm(px + R * math.cos(a)), mm(py + R * math.sin(a)))
    b.Add(z)


def preroute_k4(b, fps):
    """Generic version of place_r2.preroute for any U1 / Y1 arrangement (all B.Cu, locked, no vias but the two pre-vias):
    for each pad pair try an L (both orders) then a Z path, keep the first that clears other copper."""
    import close_gaps as C
    R2.PRE.clear()
    pad = lambda ref, num=None, net=None: R2._pad(fps, ref, num, net)[0]          # noqa: E731
    p = {n: pad("U1", n) for n in ("1", "3", "4", "7", "8", "9", "48")}
    pairs = [("LSE_OUT", p["4"], pad("Y1", net="LSE_OUT")), ("LSE_OUT", pad("C12", net="LSE_OUT"), pad("Y1", net="LSE_OUT")),
             ("LSE_IN", p["3"], pad("Y1", net="LSE_IN")), ("LSE_IN", pad("C11", net="LSE_IN"), pad("Y1", net="LSE_IN")),
             ("GND", p["8"], pad("C6", net="GND")), ("GND", pad("C10", net="GND"), pad("C6", net="GND")),
             ("+3V0", p["9"], pad("C6", net="+3V0")), ("NRST", p["7"], pad("C10", net="NRST"))]
    bad = []
    layer = pcbnew.B_Cu
    def ok(ni, pts, w):
        for a, c in zip(pts, pts[1:]):
            if math.dist(a, c) < 1e-6:
                continue
            seg = pcbnew.SHAPE_SEGMENT(pcbnew.VECTOR2I(mm(a[0]), mm(a[1])), pcbnew.VECTOR2I(mm(c[0]), mm(c[1])), mm(w))
            if not C.clear(b, ni.GetNetCode(), layer, seg, R2.ROUTE_CLEARANCE):
                return False
        return True
    done = []                                         # placed segments of this call count as obstacles through the board itself
    for net, a, c in pairs:
        ni = b.FindNet(net); w = R2.PRE_W[net]
        cands = [[a, (a[0], c[1]), c], [a, (c[0], a[1]), c]]
        for off in (0.3, -0.3, 0.6, -0.6, 0.9, -0.9, 1.2, -1.2):
            cands.append([a, (a[0], c[1] + off), (c[0], c[1] + off), c])
            cands.append([a, (c[0] + off, a[1]), (c[0] + off, c[1]), c])
        cands.append([a, c])
        cands.insert(0, [a, c])
        lanes = [round(0.3 + 0.1 * k, 2) for k in range(int((max(R2.W_) - 0.6) / 0.1))]
        for u in sorted(lanes, key=lambda u: abs(u - a[1]) + abs(u - c[1])):
            cands.append([a, (a[0], u), (c[0], u), c])
        for u in sorted(lanes, key=lambda u: abs(u - a[0]) + abs(u - c[0])):
            cands.append([a, (u, a[1]), (u, c[1]), c])
        pts = next((q for q in cands if ok(ni, q, w)), None)
        if pts is None:
            bad.append(f"preroute: {net} {tuple(round(v, 2) for v in a)}-{tuple(round(v, 2) for v in c)} no clear path"); continue
        for s, e in zip(pts, pts[1:]):
            if math.dist(s, e) < 1e-6:
                continue
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(pcbnew.VECTOR2I(mm(s[0]), mm(s[1]))); t.SetEnd(pcbnew.VECTOR2I(mm(e[0]), mm(e[1])))
            t.SetWidth(mm(w)); t.SetLayer(layer); t.SetNet(ni); t.SetLocked(True); b.Add(t)
            R2.PRE.append((net, s, e, w))
    # VBAT pin 1 + VDD pin 48 corner via, tied to C1 (ECR-0018): via at the pad-free corner between the two pins
    c1v = pad("C1", net="+3V0"); corner = (p["48"][0], p["1"][1])
    ni = b.FindNet("+3V0")
    for a, c in (([p["1"], corner]), ([p["48"], corner]), ([c1v, p["48"]])):
        if not ok(ni, [a, c], 0.15):
            bad.append(f"preroute: +3V0 {tuple(round(v, 2) for v in a)}-{tuple(round(v, 2) for v in c)} not clear")
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(pcbnew.VECTOR2I(mm(a[0]), mm(a[1]))); t.SetEnd(pcbnew.VECTOR2I(mm(c[0]), mm(c[1])))
        t.SetWidth(mm(0.15)); t.SetLayer(layer); t.SetNet(ni); t.SetLocked(True); b.Add(t)
        R2.PRE.append(("+3V0", a, c, 0.15))
    v = pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(mm(corner[0]), mm(corner[1])))
    v.SetWidth(mm(R2.VIA_D)); v.SetDrill(mm(R1.VIA_DRILL)); v.SetNet(ni); v.SetLocked(True); b.Add(v)
    R2.PRE.append(("+3V0", corner, corner, R2.VIA_D))
    return bad


FINE = {"on": False}                                  # --fine: JLC 6L standard minimums (V10-hdi.yaml, 2026-10-07)
VIP = {"on": False}                                   # --vip: pre-placed via-in-pad (POFV) on U1 signal/power pads, J21 GND/+3V0 pads


def fine_rules(b):
    """JLC 6-layer standard capability (V10-hdi.yaml, S1/S2 read 2026-10-07): via pad 0.25 / hole 0.15 -> annular 0.05
    (JLC absolute min 0.15 is for PTH holes, not vias; vias 0.25/0.15 listed as via_min), track/space 0.09, hole-to-hole 0.2.
    Hole-to-copper (different net) = annular 0.05 + space 0.09 = 0.14: the 0.2 of the 4L rule cannot hold at 0.09 space."""
    b.SetCopperLayerCount(6)
    ds = b.GetDesignSettings()
    ds.m_TrackMinWidth = mm(0.088); ds.m_MinClearance = mm(0.088)     # JLC 3.5 mil = 0.0889
    ds.m_ViasMinSize = mm(0.25); ds.m_MinThroughDrill = mm(0.15); ds.m_ViasMinAnnularWidth = mm(0.05)
    ds.m_HoleClearance = mm(0.14); ds.m_HoleToHoleMin = mm(0.2); ds.m_CopperEdgeClearance = mm(0.2)
    nc = ds.m_NetSettings.GetDefaultNetclass()
    nc.SetViaDiameter(mm(0.25)); nc.SetViaDrill(mm(0.15)); nc.SetTrackWidth(mm(0.09))


def vip_vias(b, fps):
    """Via-in-pad on every U1 perimeter pad whose net leaves the B face (GND, +3V0, or a pad on the other face), at the pad's
    outer end (away from the EP), plus a via at the outer end of each J21 GND/+3V0 pad. Locked, same net as the pad."""
    out = []
    skipped = vip_vias.skipped = []
    def add(x, y, net):
        v = pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y))); v.SetWidth(mm(0.25)); v.SetDrill(mm(0.15))
        v.SetNet(b.FindNet(net)); v.SetLocked(True); b.Add(v); out.append((x, y))
    face = {}
    for ref, f in fps.items():
        for pd in f.Pads():
            if pd.GetNetname():
                face.setdefault(pd.GetNetname(), set()).add(f.IsFlipped())
    u1 = fps["U1"]; ux, uy = MM(u1.GetPosition().x), MM(u1.GetPosition().y)
    for pd in u1.Pads():
        n = pd.GetNetname(); sz = pd.GetSize()
        if not n or min(MM(sz.x), MM(sz.y)) > 3 or n == "GND" and False:
            continue
        multi = sum(1 for p3 in u1.Pads() if p3.GetNetname() == n) > 1
        if n != "GND" and n != "+3V0" and face[n] == {True} and not multi:
            continue
        x, y = MM(pd.GetPosition().x), MM(pd.GetPosition().y)
        dx, dy = x - ux, y - uy
        if abs(dx) > abs(dy):
            x += math.copysign(0.2, dx)
        else:
            y += math.copysign(0.2, dy)
        if any(p2.GetNetname() != n and p2.GetAttribute() != pcbnew.PAD_ATTRIB_NPTH and R1._d_rect(x, y, R1._rect(p2)) < 0.125 + 0.16
               for ref2, f2 in fps.items() if ref2 != "U1" for p2 in f2.Pads()):
            skipped.append((n, round(x, 2), round(y, 2)))      # an other-net pad of a part on F sits on the via spot
            continue
        add(x, y, n)
    j = fps["J21"]; jy = MM(j.GetPosition().y)
    rows = [MM(pd.GetPosition().y) for pd in j.Pads() if pd.GetNumber().isdigit()]
    cy = (min(rows) + max(rows)) / 2
    for pd in j.Pads():
        n = pd.GetNetname()
        if n == "GND" and pd.GetNumber().isdigit():
            x, y = MM(pd.GetPosition().x), MM(pd.GetPosition().y)
            add(x, y + math.copysign(0.31 + 0.08, y - cy), n)       # pad half-length 0.305 + via radius 0.125 - 0.05 overlap
    return out


def vip_j20(b, fps):
    """M: via-in-pad at the outer end of every J20 signal pad (FreeRouting never drops a via on an SMD pad itself, and the 0.35 mm
    pitch BM28 rows box the pads in). Skipped where another net's pad of a part sits on the via spot."""
    out = []
    j = fps["J20"]
    rows = [MM(pd.GetPosition().y) for pd in j.Pads() if pd.GetNumber().isdigit()]
    cy = (min(rows) + max(rows)) / 2
    for pd in j.Pads():
        n = pd.GetNetname()
        if not (pd.GetNumber().isdigit() and n and n != "GND"):
            continue
        x, y = MM(pd.GetPosition().x), MM(pd.GetPosition().y)
        y0 = y
        for sgn in (1, -1):
            y = y0 + sgn * math.copysign(0.39, y0 - cy)
            if not any(p2.GetNetname() != n and p2.GetAttribute() != pcbnew.PAD_ATTRIB_NPTH and R1._d_rect(x, y, R1._rect(p2)) < 0.125 + 0.16
                       for r2, f2 in fps.items() if r2 != "J20" for p2 in f2.Pads()) and not any(math.hypot(x - a, y - c) < 0.3 for a, c in out):
                break
        else:
            continue
        v = pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y))); v.SetWidth(mm(0.25)); v.SetDrill(mm(0.15))
        v.SetNet(b.FindNet(n)); v.SetLocked(True); b.Add(v); out.append((x, y))
    return out


def build(board, placement, L):
    comps, nets = P.parse_netlist(K4 / f"pod_k4_{board}.net")
    missing = set(placement) ^ set(comps)
    assert not missing, f"placement and netlist disagree: {sorted(missing)}"
    R2.W_[0], R2.W_[1] = L, H
    for mod in (P, R1.P):
        mod.W, mod.H, mod.CORNER = L, H, 1.0
    b = pcbnew.BOARD()
    P.rules(b)
    if FINE["on"]:
        R2.VIA_D = R1.VIA_D = 0.25
        fine_rules(b)
    nc = b.GetDesignSettings().m_NetSettings.GetDefaultNetclass()
    nc.SetViaDiameter(mm(R2.VIA_D)); R1.VIA_D = R2.VIA_D
    outline_k4(b, board, L)
    fps = {}
    for ref, fpid in comps.items():
        lib, name = fp_name(ref, fpid)
        fp = pcbnew.FootprintLoad(R1.P.fp_lib(lib), name)
        assert fp is not None, f"footprint {fpid} not found"
        fp.SetReference(ref)
        x, y, rot, side = placement[ref]
        fp.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y))); fp.SetOrientationDegrees(rot)
        b.Add(fp)
        if side == "B":
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        fps[ref] = fp
    for name, nodes in nets.items():
        ni = pcbnew.NETINFO_ITEM(b, name); b.Add(ni)
        for ref, pin in nodes:
            for pd in fps[ref].Pads():
                if pd.GetNumber() == pin:
                    pd.SetNet(ni)
    b.GetDesignSettings().SetBoardThickness(mm(0.8))
    if board == "M":
        px, py = R2.port_xy(fps)
        port_keepout_layer(b, px, py, pcbnew.B_Cu)
        pre_bad = []
    else:
        px, py = -100.0, -100.0
        pre_bad = preroute_k4(b, fps)
    R2.PAD_RECTS[:] = [R1._rect(pd) for f in fps.values() for pd in f.Pads() if pd.GetAttribute() != pcbnew.PAD_ATTRIB_NPTH]
    mine = vip_vias(b, fps) if (VIP["on"] and board == "P") else (vip_j20(b, fps) if (VIP["on"] and board == "M") else [])
    nvia0 = len([t for t in b.GetTracks() if t.GetClass() == "PCB_VIA"])
    R1.AVOID = lambda x, y, seg_from=None: R2._avoid(x, y, seg_from, px, py) or any(math.hypot(x - a, y - c) < 0.5 for a, c in mine)
    added, skipped = R1.gnd_fanout(b, fps, 0.0) if "U1" in fps else R2.net_fanout(b, fps, "GND", 0.0)
    a3, s3 = R2.net_fanout(b, fps, R2.PWR_NET, 0.0)
    if VIP["on"] and board == "P":                      # drop fan-out vias that touch another net's pad or a locked via-in-pad
        keep = [t for t in b.GetTracks() if t.GetClass() == "PCB_VIA" and not t.IsLocked()]
        for v in keep:
            vx, vy = MM(v.GetPosition().x), MM(v.GetPosition().y)
            bad = any(pd.GetNetname() != v.GetNetname() and R1._d_rect(vx, vy, R1._rect(pd)) < 0.125 + 0.16
                      for f in fps.values() for pd in f.Pads() if pd.GetAttribute() != pcbnew.PAD_ATTRIB_NPTH)
            bad = bad or any(math.hypot(vx - a, vy - c) < 0.4 for a, c in mine)
            if board == "P":
                n_ = notch_rect()
                bad = bad or (n_[0] - 0.4 < vx < n_[2] + 0.4 and n_[1] - 0.4 < vy < n_[3] + 0.4)
            if bad:
                for t in list(b.GetTracks()):
                    if t.GetClass() != "PCB_VIA" and not t.IsLocked() and any(
                            math.hypot(MM(e.x) - vx, MM(e.y) - vy) < 0.01 for e in (t.GetStart(), t.GetEnd())):
                        b.Remove(t)
                b.Remove(v)
    R1.AVOID = None
    R1.gnd_plane(b)
    R2.pwr_plane(b, L, H)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    return b, fps, (added + a3, skipped + s3, pre_bad)


# --------------------------------------------------------------------------------------------------- checks
def crt(f):
    cy = f.GetCourtyard(pcbnew.B_CrtYd if f.IsFlipped() else pcbnew.F_CrtYd)
    bb = cy.BBox() if cy.OutlineCount() else f.GetBoundingBox(False)
    return [MM(v) for v in (bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom())]


def check(board, b, fps, comps, L, fan):
    v, m = [], {}
    inner = "F"
    # fit
    n = notch_rect()
    for ref, f in fps.items():
        l, t, r, btm = crt(f)
        if l < -0.01 or t < -0.01 or r > L + 0.01 or btm > H + 0.01:
            v.append(f"fit: {ref} courtyard outside the outline ({l:.2f},{t:.2f})-({r:.2f},{btm:.2f})")
        if board == "P" and hit((l, t, r, btm), n, -0.001):
            v.append(f"fit: {ref} courtyard inside the mic notch")
        for net, pr in R2._pads(f):
            if min(pr[0], pr[1], L - pr[2], H - pr[3]) < R2.EDGE_COPPER:
                v.append(f"fit: {ref} pad within {R2.EDGE_COPPER} mm of the edge"); break
            if board == "P" and hit(pr, (n[0], n[1] - 0.3, n[2] + 0.3, n[3] + 0.3), -0.001):
                v.append(f"fit: {ref} pad within 0.3 mm of the mic notch"); break
    for a, c, area in P.courtyard_overlaps(fps):
        v.append(f"fit: courtyards {a}/{c} overlap {area} mm2")
    for a, c in P.pad_clashes(fps):
        v.append(f"fit: pads {a}/{c} closer than 0.12 mm")
    v.extend(x for x in fan[2] if "LSE" in x)             # LSE is a rule; VDDA/NRST/+3V0 pre-routes are best effort (warn)
    m["preroute_warn"] = [x for x in fan[2] if "LSE" not in x]
    # axis + port (M)
    if board == "M":
        px, py = R2.port_xy(fps)
        m["port_xy"] = [round(px, 2), round(py, 2)]
        if abs(py - H / 2) > 0.05:
            v.append(f"axis: mic port y {py:.2f} != centre {H / 2}")
        sy = MM(fps["SW1"].GetPosition().y)
        if abs(sy - H / 2) > 0.05:
            v.append(f"axis: SW1 y {sy:.2f} != centre {H / 2}")
        if not fps["U2"].IsFlipped() is True and False:
            pass
        best = 1e9                                    # port exits on B: no B copper, no via within PORT_KEEPOUT
        for t in b.GetTracks():
            if t.GetClass() == "PCB_VIA" or t.IsOnLayer(pcbnew.B_Cu):
                best = min(best, R2._copper_dist(t, px, py))
        for f in b.GetFootprints():
            for pd in f.Pads():
                if pd.GetAttribute() != pcbnew.PAD_ATTRIB_NPTH and pd.IsOnLayer(pcbnew.B_Cu):
                    best = min(best, R1._d_rect(px, py, R1._rect(pd)))
        m["port_keepout_mm"] = round(best, 2)
        if best < R2.PORT_KEEPOUT:
            v.append(f"port: B copper / via {best:.2f} mm from the mic port centre (min {R2.PORT_KEEPOUT}, R-ACO-P6)")
        # replaces 'far': no switching part on M within 10 mm of the port
        for ref in SWITCHING & set(fps):
            x, y = MM(fps[ref].GetPosition().x), MM(fps[ref].GetPosition().y)
            if math.hypot(x - px, y - py) < FAR_MIN:
                v.append(f"switch: {ref} on M {math.hypot(x - px, y - py):.1f} mm from the port (min {FAR_MIN})")
        m["switching_parts_on_M"] = sorted(SWITCHING & set(fps))
    # near
    for part, anchor, lim in R2.NEAR:
        aref, _, apin = anchor.partition(".")
        if part not in fps or aref not in fps:
            continue
        pa, pb = R2._pads(fps[part]), R2._pads(fps[aref], pin=apin or None)
        d = min((R2._gap(x[1], y[1]) for x in pa for y in pb if x[0] and x[0] == y[0] and x[0] != "GND"), default=None)
        if d is None:
            v.append(f"near: {part} shares no net with {anchor}")
        elif d > lim:
            v.append(f"near: {part} {d:.2f} mm from {anchor} (max {lim})")
    # escape ring (P)
    if "U1" in fps:
        upads = [r for _, r in R2._pads(fps["U1"])]
        ring = [min(upads, key=lambda r: r[0])[0] - R2.ESCAPE, min(upads, key=lambda r: r[1])[1] - R2.ESCAPE,
                max(upads, key=lambda r: r[2])[2] + R2.ESCAPE, max(upads, key=lambda r: r[3])[3] + R2.ESCAPE]
        for ref, f in fps.items():
            if ref == "U1" or ref in R2.ESCAPE_OK or f.IsFlipped() != fps["U1"].IsFlipped():
                continue
            r = crt(f)
            if any(R2._gap(r, u) < R2.ESCAPE for u in upads) and r[0] < ring[2] and r[2] > ring[0] and r[1] < ring[3] and r[3] > ring[1]:
                v.append(f"escape: {ref} within {R2.ESCAPE} mm of U1's pads (only U1's support parts may sit there)")
    # wire pads
    wp = [(ref, nn, r) for ref in R2.WIRE_PADS if ref in fps for nn, r in R2._pads(fps[ref])]
    for i, (ra, na, a) in enumerate(wp):
        for rb, nb, c in wp[i + 1:]:
            if na != nb and fps[ra].IsFlipped() == fps[rb].IsFlipped() and R2._gap(a, c) < R2.PAD_GAP:
                v.append(f"pads: {ra}({na})-{rb}({nb}) gap {R2._gap(a, c):.2f} < {R2.PAD_GAP}")
    if "J3" in fps and "J5" in fps:
        d = min(R2._gap(x[1], y[1]) for x in R2._pads(fps["J3"]) for y in R2._pads(fps["J5"]))
        m["gap_J3_J5_mm"] = round(d, 2)
        if d < 2.0:
            v.append(f"pads: J3-J5 gap {d:.2f} < 2.0 (ASM-09)")
    # inner-face heights (single-board part)
    for ref, f in fps.items():
        face_in = not f.IsFlipped()
        if face_in and ref not in ("U2",) and not ref.startswith("J2") and height(comps[ref]) > GAP + 1e-9:
            v.append(f"gap: {ref} {height(comps[ref])} mm on the inner face (> {GAP} mm B2B gap)")
    # ratsnest + density
    pts = {}
    for f in fps.values():
        for pd in f.Pads():
            nn = pd.GetNetname()
            if nn and nn != "GND" and pd.GetAttribute() != pcbnew.PAD_ATTRIB_NPTH:
                pts.setdefault(nn, []).append((MM(pd.GetPosition().x), MM(pd.GetPosition().y)))
    total = 0.0
    for nn, q in pts.items():
        inside, rest = [q[0]], q[1:]
        while rest:
            d, k = min((math.dist(a, c), k) for k, c in enumerate(rest) for a in inside)
            total += d; inside.append(rest.pop(k))
    area = {"F": 0.0, "B": 0.0}
    for f in fps.values():
        cy = f.GetCourtyard(pcbnew.B_CrtYd if f.IsFlipped() else pcbnew.F_CrtYd)
        area["B" if f.IsFlipped() else "F"] += cy.Area() / 1e12 if cy.OutlineCount() else 0
    bd = L * H - (4 - math.pi) - (((notch_rect()[2]) * (notch_rect()[3] - notch_rect()[1])) if board == "P" else 0)
    m.update(ratsnest_mm=round(total, 1), board_mm2=round(bd, 1), courtyard_B_mm2=round(area["B"], 1), courtyard_F_mm2=round(area["F"], 1),
             U_B=round(area["B"] / bd, 3), U_F=round(area["F"] / bd, 3), U_both=round((area["B"] + area["F"]) / (2 * bd), 3),
             gnd_vias=fan[0], gnd_fanout_skipped=len(fan[1]))
    return v, m


def stack_check(fp_P, fp_M, cP, cM, L):
    """Cross-board: B2B mate and inner-face stack height."""
    v, m = [], {}
    j21, j20 = fp_P["J21"], fp_M["J20"]
    x21, y21 = MM(j21.GetPosition().x), H - MM(j21.GetPosition().y)
    x20, y20 = MM(j20.GetPosition().x), MM(j20.GetPosition().y)
    m["b2b_xy_P_stack"], m["b2b_xy_M"] = [round(x21, 3), round(y21, 3)], [round(x20, 3), round(y20, 3)]
    if math.hypot(x21 - x20, y21 - y20) > 0.01:
        v.append(f"mate: BM28 centres differ ({x21:.2f},{y21:.2f}) vs ({x20:.2f},{y20:.2f})")
    pp = {p.GetNumber(): (MM(p.GetPosition().x), H - MM(p.GetPosition().y)) for p in j21.Pads()}
    mp = {p.GetNumber(): (MM(p.GetPosition().x), MM(p.GetPosition().y)) for p in j20.Pads()}
    worst = 0.0
    for k in pp:
        if k in mp and int(k) <= 30:
            worst = max(worst, abs(pp[k][0] - mp[k][0]))
            if abs(pp[k][1] - mp[k][1]) > 0.35 or (pp[k][1] - y21) * (mp[k][1] - y20) <= 0:
                v.append(f"mate: pad {k} row differs plug y {pp[k][1]:.2f} / receptacle y {mp[k][1]:.2f}")
    m["mate_max_dx_mm"] = round(worst, 3)
    # inner-face overlap sums
    innerP = [(ref, f) for ref, f in fp_P.items() if not f.IsFlipped()]
    innerM = [(ref, f) for ref, f in fp_M.items() if not f.IsFlipped()]
    worst_h = 0.0
    for ra, fa in innerP:
        a = crt(fa); a = (a[0], H - a[3], a[2], H - a[1])
        for rb, fb in innerM:
            if {ra, rb} == {"J21", "J20"}:
                continue
            if hit(a, crt(fb), -0.001):
                h = height(cP[ra]) + height(cM[rb])
                worst_h = max(worst_h, h)
                if h > GAP + 1e-9:
                    v.append(f"gap: P {ra} over M {rb}: {h:.2f} mm > {GAP}")
    m["max_stacked_pair_mm"] = round(worst_h, 2)
    # P parts over the mic and the mic's body: notch
    mic = crt(fp_M["U2"])
    for ref, f in fp_P.items():
        r = crt(f); r = (r[0], H - r[3], r[2], H - r[1])
        if hit(r, mic, -0.001):
            v.append(f"gap: P {ref} over the mic (1.08 mm > {GAP} mm gap)")
    px, py = R2.port_xy(fp_M)
    m["P_switching_to_port_mm"] = {ref: round(math.hypot(MM(fp_P[ref].GetPosition().x) - px, H - MM(fp_P[ref].GetPosition().y) - py), 1)
                                   for ref in sorted(SWITCHING & set(fp_P))}
    return v, m


# --------------------------------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pack", action="store_true")
    ap.add_argument("--L", type=float, default=12.6)
    ap.add_argument("--u1rot", type=int, default=90)
    ap.add_argument("--u1cy", type=float, default=4.8)
    ap.add_argument("--fine", action="store_true", help="JLC 6L minimum rules (via 0.25/0.15, annular 0.05, hole clearance 0.14)")
    ap.add_argument("--cx", type=float, default=None, help="fixed U1/J20/J21 x (default L-4.2)")
    ap.add_argument("--win", action="store_true", help="P solder-access window over M cell-wire pads")
    ap.add_argument("--vip", action="store_true", help="pre-placed via-in-pad on U1 / J21 pads (P only)")
    a = ap.parse_args()
    FINE["on"], VIP["on"] = a.fine, a.vip
    L = a.L
    CX_FIX[0] = a.cx
    SOLDER_WIN["on"] = a.win
    global MIC_ROT, _MIC_R, MIC_CY, U1_ROT, U1_CY
    U1_ROT, U1_CY = a.u1rot, a.u1cy
    MIC_ROT, _MIC_R, MIC_CY = _mic_rot(P.parse_netlist(K4 / 'pod_k4_M.net')[0]['U2'])
    comps, nets, plc = {}, {}, {}
    for bd in "PM":
        comps[bd], nets[bd] = P.parse_netlist(K4 / f"pod_k4_{bd}.net")
    if a.pack:
        plc["M"], fails_m = pack("M", comps["M"], nets["M"], L)
        PINNER[:] = [(r[0], H - r[3], r[2], H - r[1]) for ref, (x, y, rot, s) in plc["M"].items() if s == "F"
                     for r in [shift(rel(comps["M"][ref], ref, rot, False)[0], x, y)] if ref not in ("J20", "U2")]
        plc["P"], fails_p = pack("P", comps["P"], nets["P"], L)
        print("pack failures P:", fails_p, "M:", fails_m)
        if fails_p or fails_m:
            sys.exit(2)
        for bd in "PM":
            (K4 / f"placement_{bd}.yaml").write_text(yaml.safe_dump({k: v for k, v in sorted(plc[bd].items())}, default_flow_style=None))
    for bd in "PM":
        plc[bd] = {k: tuple(v) for k, v in yaml.safe_load(open(K4 / f"placement_{bd}.yaml")).items()}
    ok, fpall, reps = True, {}, {}
    for bd in "PM":
        out = K4 / "out" / bd
        out.mkdir(parents=True, exist_ok=True)
        b, fps, fan = build(bd, plc[bd], L)
        viol, met = check(bd, b, fps, comps[bd], L, fan)
        pcbnew.SaveBoard(str(out / "placed.kicad_pcb"), b)
        fpall[bd] = fps; reps[bd] = (viol, met)
    sv, sm = stack_check(fpall["P"], fpall["M"], comps["P"], comps["M"], L)
    for bd in "PM":
        viol, met = reps[bd]
        vv = viol + (sv if bd == "P" else [])
        rep = {"board": bd, "L": L, "H": H, "pass": not vv, "violations": vv, "metrics": met | ({"stack": sm} if bd == "P" else {})}
        (K4 / "out" / bd / "check.json").write_text(json.dumps(rep, indent=1))
        print(bd, "PASS" if not vv else f"FAIL ({len(vv)})")
        for x in vv:
            print("  ", x)
        print("  ", json.dumps(rep["metrics"]))
        ok &= not vv
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
