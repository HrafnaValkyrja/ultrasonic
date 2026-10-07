"""Phase-2 board builder + placement rule check (ECR-0018, owner O25/O26): one-face pod board from pod_mz2.net.

    source tools/env.sh && systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 \
        python3 hw/pod/place_r2.py PLACEMENT.yaml [--W 32 --H 12] [--net hw/pod/pod_mz2.net] [--out DIR] [--route]

PLACEMENT.yaml: {ref: [x, y, rot_deg, side]} for every part in the netlist (side F|B; x = 0 at the mic end, y = 0 at the
top edge, centre line y = H/2). Writes DIR/placed.kicad_pcb + DIR/check.json (+ DIR/routed.kicad_pcb with --route) and
prints the check. --route runs FreeRouting ONCE, fenced: only the lead session routes, never parallel agents (CLAUDE.md).

The check encodes the Phase-2 rules (docs/research/miniaturization-prelim.md MZG-01..15, ECR-0018, Phase-1 lessons):
  face      every part on B except SW1 (F): the one-face strategy (MZD-1); bare test pads TP1-TP6 may sit on F
  fit       courtyards inside the outline; copper >= 0.3 mm from the edge; no courtyard overlap; pads >= 0.12 mm apart
  axis      mic port (U2 NPTH) and SW1 on the centre line (O16-5: one board for both pods)
  near      decoupling / support parts within a set distance of the pins they serve (ST/TI layout rules); I_SENSE filter tight
  escape    only U1's own support parts within 0.6 mm of its pads (QFN fan-out room)
  far       L1 and the bridge FETs >= 10 mm from the mic port (MZG-04)
  pads      wire pads of different nets >= 0.8 mm copper gap (Phase-1 lesson: J4-J5 0.60 mm = cell short); J3 DOCK_VBUS
            never a direct neighbour of J5 VBAT (ASM-09: a bridge would charge the cell past U3; J4 GND sits between them)
  port      no F copper and no via within 1.6 mm of the mic port centre (R-ACO-P6 duct-seat keep-out); the builder adds an
            F.Cu rule area (no tracks, no vias) so FreeRouting and DRC both enforce it, and the fan-out avoids it
  preroute  fixed (locked) B.Cu tracks laid before routing: LSE Y1 <-> U1 pins 3/4 and C11/C12 with no vias (R-CLOCK-BOARD),
            VDDA pin 9 / GND pin 8 straight to C6, NRST pin 7 to C10 + its via to TP3, one +3V0 via in the pin-1/48 QFN
            corner tied to C1 (ECR-0018, B-DOC-AUDIT-0007); each segment must clear other copper
  density   courtyard utilization per face (the area model's U)

    python3 hw/pod/place_r2.py --probe BOARD.kicad_pcb    prints the routed-board probe (port keep-out, LSE vias/lengths,
                                                          VDDA caps, R21 edge distance, wire-pad neighbours)
"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
from pathlib import Path

import pcbnew
import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import place as P                                    # noqa: E402  (outline, rules, parse_netlist, overlap checks)
import place_r1 as R1                               # noqa: E402  (gnd_fanout, gnd_plane)

mm, MM = pcbnew.FromMM, pcbnew.ToMM
EDGE_COPPER = 0.3
PAD_GAP = 0.8                                        # wire pads of different nets
F_ONLY = {"SW1"}
F_ALLOWED = {f"TP{i}" for i in range(1, 7)}   # bare SWD/power test pads: no part, no height; bench access before the lid bond
WIRE_PADS = {"J1", "J2", "J3", "J4", "J5", "J7", "J8", "J9", "J10", "J11", "J12"}
# (part, anchor ref, max mm between their nearest pads sharing a non-GND net); "anchor.pin" restricts to a pin
NEAR = [
    ("C1", "U1.1", 1.5), ("C1", "U1.48", 1.5), ("C2", "U1.25", 2.0), ("C3", "U1.36", 2.0),
    ("C6", "U1.9", 1.0), ("C5", "U1.9", 2.5),          # VDDA pin 9: 100 nF at the pin, 1 uF beside it (2026-10-07: was 'U1')
    ("C4", "U1", 4.0), ("C7", "U1", 2.0), ("C8", "U1", 2.5), ("C9", "U1", 2.5), ("L1", "U1", 2.5),
    # Y1: 4.0 (was 3.0) since the LSE pair is pre-routed on B with no vias; the copper per net is held by LSE_MAX (probe)
    ("C10", "U1", 3.0), ("Y1", "U1", 4.0), ("C11", "Y1", 2.0), ("C12", "Y1", 2.0), ("R1", "U1", 4.0), ("R2", "U1", 3.0),
    ("C15", "U3", 2.0), ("C16", "U3", 2.0), ("C21", "U3", 2.5), ("C17", "U4", 2.0), ("C18", "U4", 2.0),
    ("C13", "U2", 2.0), ("R3", "Q1", 3.0), ("R4", "Q1", 3.0), ("R5", "Q2", 3.0), ("R6", "Q2", 3.0), ("C14", "Q1", 4.0),
    ("C14", "Q2", 4.0), ("D5", "J3", 3.0), ("D6", "J12", 3.0), ("U6", "J10", 5.0), ("U6", "J11", 5.0),
    ("R21", "Q1", 5.0), ("R21", "Q2", 5.0), ("C22", "U1.16", 2.0), ("R22", "U1.16", 2.5), ("R22", "R21", 6.0),
]
# only U1's own support parts may sit within ESCAPE mm (courtyard) of its pads: the QFN needs room to fan out (judge 2026-10-03)
ESCAPE, ESCAPE_OK = 0.6, {"C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "C10", "C11", "C12", "Y1", "R2", "L1", "R1",
                          "C22", "R22"}
FAR_FROM_PORT = [("L1", 10.0), ("Q1", 10.0), ("Q2", 10.0)]
PORT_KEEPOUT = 1.6           # mm from the port centre: no F copper, no via (R-ACO-P6, docs/sim/acoustics.yaml)
NOT_NEIGHBOURS = [("J3", "J5", 2.0)]   # ASM-09: DOCK_VBUS / VBAT pads need >= 2.0 mm copper gap (another pad between)
LSE_MAX = 8.0                # mm copper per LSE net (Y1 pad to U1 pin), B only, no vias
PRE_W = {"LSE_IN": 0.1, "LSE_OUT": 0.1, "+3V0": 0.15, "GND": 0.15, "NRST": 0.1}
FR_ARGS = []                 # extra FreeRouting switches (--fr-args), e.g. "-is random" / "-us global": a different but valid route
PAD_RECTS = []               # every copper pad of the current build: fan-out vias never land on a pad (no via-in-pad)
PRE = []                     # [(net, (x0, y0), (x1, y1), width)] pre-routed B.Cu segments of the current build


ROUTE_CLEARANCE = 0.11          # FreeRouting rounds 45-degree segments ~8 um under target: 0.10 gave hole clearance 0.192 < 0.2
VIA_D = 0.35                    # 0.30 broke the 0.2 mm hole clearance (107 DRC errors, 2026-10-03)
PWR_NET = "+3V0"     # In2 is a +3V0 plane in Phase 2 (stack F sig / In1 GND / In2 +3V0 / B sig): F is almost empty, so it routes


def pwr_plane(b, W, H):
    b.SetLayerType(pcbnew.In2_Cu, pcbnew.LT_POWER)
    z = pcbnew.ZONE(b)
    z.SetLayer(pcbnew.In2_Cu)
    z.SetNet(b.FindNet(PWR_NET))
    z.SetLocalClearance(mm(0.2))
    z.SetMinThickness(mm(0.2))
    ol = z.Outline()
    ol.NewOutline()
    for x, y in ((0.3, 0.3), (W - 0.3, 0.3), (W - 0.3, H - 0.3), (0.3, H - 0.3)):
        ol.Append(mm(x), mm(y))
    b.Add(z)


def net_fanout(b, fps, netname, inset=0.0):
    """Same idea as place_r1.gnd_fanout for a second plane net: a short stub + via from each pad of `netname` to its plane."""
    net = b.FindNet(netname)
    VD, VDR, SW, GAP = R1.VIA_D, R1.VIA_DRILL, R1.STUB_W, R1.GAP
    others = [(R1._rect(p), p) for f in fps.values() for p in f.Pads() if p.GetNetname() != netname]
    vias = [(MM(t.GetPosition().x), MM(t.GetPosition().y)) for t in b.GetTracks() if t.GetClass() == "PCB_VIA"]
    V = lambda x, y: pcbnew.VECTOR2I(mm(x), mm(y))  # noqa: E731
    added, skipped = 0, []
    for ref, f in fps.items():
        if ref in FANOUT_SKIP:                      # fine-pitch ICs: their supply pins route to their own decoupling caps
            continue
        fx, fy = MM(f.GetPosition().x), MM(f.GetPosition().y)
        layer = pcbnew.B_Cu if f.IsFlipped() else pcbnew.F_Cu
        layer_pads = [(r, p) for r, p in others if p.IsOnLayer(layer)]
        layer_tracks = [t for t in b.GetTracks() if t.GetClass() == "PCB_TRACK" and t.GetLayer() == layer]
        for p in f.Pads():
            if p.GetNetname() != netname:
                continue
            r = R1._rect(p); cx, cy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
            ox, oy = cx - fx, cy - fy
            n = math.hypot(ox, oy)
            ox, oy = (ox / n, oy / n) if n > 1e-6 else (0.0, 1.0)
            half = max(r[2] - r[0], r[3] - r[1]) / 2
            done = False
            for dx, dy in [(ox, oy), (-oy, ox), (oy, -ox), (ox - oy, oy + ox), (ox + oy, oy - ox), (0, -1), (0, 1), (-1, 0), (1, 0)]:
                m_ = math.hypot(dx, dy); dx, dy = dx / m_, dy / m_
                for d in (half + VD / 2 + 0.05, half + VD / 2 + 0.25, half + VD / 2 + 0.5):
                    x, y = cx + dx * d, cy + dy * d
                    lo = 0.45 + inset
                    if not (lo <= x <= W_[0] - lo and lo <= y <= W_[1] - lo):
                        continue
                    if R1.AVOID is not None and R1.AVOID(x, y, (cx, cy)):
                        continue
                    if any(math.hypot(x - vx, y - vy) < VD + 0.2 for vx, vy in vias):
                        continue
                    if any(R1._d_rect(x, y, rr) < VD / 2 + GAP for rr, _ in others):
                        continue
                    if any(R1._d_rect(cx + (x - cx) * k / 10, cy + (y - cy) * k / 10, rr) < SW / 2 + GAP
                           for k in range(1, 10) for rr, _ in layer_pads):
                        continue
                    if any(t.GetEffectiveShape().Collide(pcbnew.SEG(V(cx, cy), V(x, y)), mm(SW / 2 + GAP)) for t in layer_tracks
                           if t.GetNetname() != netname):
                        continue
                    t = pcbnew.PCB_TRACK(b); t.SetStart(V(cx, cy)); t.SetEnd(V(x, y)); t.SetWidth(mm(SW)); t.SetLayer(layer); t.SetNet(net); b.Add(t)
                    v = pcbnew.PCB_VIA(b); v.SetPosition(V(x, y)); v.SetWidth(mm(VD)); v.SetDrill(mm(VDR)); v.SetNet(net); b.Add(v)
                    vias.append((x, y)); added += 1; done = True
                    break
                if done:
                    break
            if not done:
                skipped.append(f"{ref}.{p.GetNumber()}")
    return added, skipped


W_ = [32.0, 12.0]
FANOUT_SKIP = set()           # skipping U1/U3/U4 routed worse (10 unconnected + 4 clearance vs 8 + 0), 2026-10-03


def build(placement, netlist, W, H, inset=0.0, fanout=True):
    W_[0], W_[1] = W, H
    for mod in (P, R1.P):                           # place_r1 loads its own copy of place.py
        mod.W, mod.H, mod.CORNER = W, H, 1.0
    comps, nets = P.parse_netlist(netlist)
    missing = set(placement) ^ set(comps)
    assert not missing, f"placement table and netlist disagree: {sorted(missing)}"
    b = pcbnew.BOARD()
    P.rules(b, clearance=ROUTE_CLEARANCE if inset else 0.1)   # the routing copy asks FreeRouting for margin
    nc = b.GetDesignSettings().m_NetSettings.GetDefaultNetclass()
    nc.SetViaDiameter(mm(VIA_D))                     # 0.30/0.15: JLC 4-layer minimum (annular 0.075); the 0.15 drill already pays the small-via fee
    R1.VIA_D = VIA_D
    P.outline(b, inset)
    fps = {}
    for ref, fpid in comps.items():
        lib, name = fpid.split(":")
        fp = pcbnew.FootprintLoad(R1.P.fp_lib(lib), name)
        assert fp is not None, f"footprint {fpid} not found"
        fp.SetReference(ref)
        x, y, rot, side = placement[ref]
        fp.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
        fp.SetOrientationDegrees(rot)
        b.Add(fp)
        if side == "B":
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        fps[ref] = fp
    for name, nodes in nets.items():
        ni = pcbnew.NETINFO_ITEM(b, name)
        b.Add(ni)
        for ref, pin in nodes:
            for p in fps[ref].Pads():
                if p.GetNumber() == pin:
                    p.SetNet(ni)
    b.GetDesignSettings().SetBoardThickness(mm(0.8))
    px, py = port_xy(fps)
    port_keepout(b, px, py)
    pre_bad = preroute(b, fps)
    PAD_RECTS[:] = [R1._rect(p) for f in fps.values() for p in f.Pads() if p.GetAttribute() != pcbnew.PAD_ATTRIB_NPTH]
    R1.AVOID = lambda x, y, seg_from=None: _avoid(x, y, seg_from, px, py)
    if fanout:
        added, skipped = R1.gnd_fanout(b, fps, inset)
        a3, s3 = net_fanout(b, fps, PWR_NET, inset)
        added, skipped = added + a3, skipped + s3
    else:
        added, skipped = 0, []
    R1.AVOID = None
    R1.gnd_plane(b)
    pwr_plane(b, W, H)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    return b, fps, (added, skipped, pre_bad)


def port_keepout(b, px, py, r=PORT_KEEPOUT, n=36):
    """F.Cu rule area (no tracks, no vias) round the mic port; polygon circumscribes the r circle."""
    z = pcbnew.ZONE(b)
    z.SetIsRuleArea(True)
    z.SetLayer(pcbnew.F_Cu)
    z.SetDoNotAllowTracks(True); z.SetDoNotAllowVias(True); z.SetDoNotAllowZoneFills(True)
    z.SetDoNotAllowPads(False); z.SetDoNotAllowFootprints(False)
    z.SetZoneName("mic port keep-out R-ACO-P6")
    ol = z.Outline(); ol.NewOutline()
    R = r / math.cos(math.pi / n)
    for k in range(n):
        a = 2 * math.pi * k / n
        ol.Append(mm(px + R * math.cos(a)), mm(py + R * math.sin(a)))
    b.Add(z)


def _pad(fps, ref, num=None, net=None):
    for p in fps[ref].Pads():
        if (num is None or p.GetNumber() == num) and (net is None or p.GetNetname() == net) and p.GetNumber():
            r = R1._rect(p)
            return (MM(p.GetPosition().x), MM(p.GetPosition().y)), r
    raise SystemExit(f"preroute: {ref} pad {num or net} not found")


def preroute(b, fps):
    """Lay the fixed B.Cu tracks (locked: the Specctra export marks them protected, the SES import keeps them).
    LSE: pin 4 straight up to the LSE_OUT row and left to Y1's LSE_OUT pad; pin 3 up to a row 0.3 mm lower, left, then
    down beside Y1 (between Y1 and C1) to Y1's LSE_IN pad; C11/C12 straight into the Y1 pads. VDDA: pins 8/9 straight
    up into C6. Returns the segments that do not clear other copper (a check violation)."""
    import close_gaps as C
    PRE.clear()
    p3, _ = _pad(fps, "U1", "3"); p4, _ = _pad(fps, "U1", "4")
    yo, ro = _pad(fps, "Y1", net="LSE_OUT"); yi, ri = _pad(fps, "Y1", net="LSE_IN")
    c12, _ = _pad(fps, "C12", net="LSE_OUT"); c11, _ = _pad(fps, "C11", net="LSE_IN")
    _, rc1 = _pad(fps, "C1", net="+3V0")
    x_down = (ri[2] + rc1[0]) / 2                    # midway between Y1's pads and C1's pads
    y_in = yo[1] + 0.3
    paths = {"LSE_OUT": [[p4, (p4[0], yo[1]), yo], [c12, yo]],
             "LSE_IN": [[p3, (p3[0], y_in), (x_down, y_in), (x_down, yi[1]), yi], [c11, yi]]}
    p8, _ = _pad(fps, "U1", "8"); p9, _ = _pad(fps, "U1", "9")
    c6g, _ = _pad(fps, "C6", net="GND"); c6v, _ = _pad(fps, "C6", net="+3V0")
    paths["GND"] = [[p8, (p8[0], c6g[1] + 0.3), c6g]]
    # VBAT pin 1 + VDD pin 48: one +3V0 via in the QFN corner (pad-free; the LSE row above blocks their own fan-out) and C1
    p1, _ = _pad(fps, "U1", "1"); p48, _ = _pad(fps, "U1", "48"); c1v, _ = _pad(fps, "C1", net="+3V0")
    corner = (p48[0], p1[1])
    paths["+3V0"] = [[p9, (p9[0], c6v[1] + 0.3), c6v], [p1, corner], [p48, corner], [c1v, p48]]
    # NRST: pin 7 up and left under C10 into its NRST pad, with the via to TP3 (F) just under that pad; C10 GND to C6 GND
    p7, _ = _pad(fps, "U1", "7")
    c10n, _ = _pad(fps, "C10", net="NRST"); c10g, _ = _pad(fps, "C10", net="GND")
    y_n = c10n[1] + 0.45
    paths["NRST"] = [[p7, (p7[0], y_n), (c10n[0], y_n), c10n]]
    paths["GND"].append([c10g, c6g])
    nrst_via = (c10n[0], c10n[1] + 0.41)
    bad = []
    for net, polys in paths.items():
        ni = b.FindNet(net)
        for pts in polys:
            for a, c in zip(pts, pts[1:]):
                if math.dist(a, c) < 1e-6:
                    continue
                w = PRE_W[net]
                seg = pcbnew.SHAPE_SEGMENT(pcbnew.VECTOR2I(mm(a[0]), mm(a[1])), pcbnew.VECTOR2I(mm(c[0]), mm(c[1])), mm(w))
                if not C.clear(b, ni.GetNetCode(), pcbnew.B_Cu, seg, ROUTE_CLEARANCE):
                    bad.append(f"preroute: {net} segment {tuple(round(v, 2) for v in a)}-{tuple(round(v, 2) for v in c)} "
                               f"does not clear {ROUTE_CLEARANCE} mm")
                t = pcbnew.PCB_TRACK(b)
                t.SetStart(pcbnew.VECTOR2I(mm(a[0]), mm(a[1]))); t.SetEnd(pcbnew.VECTOR2I(mm(c[0]), mm(c[1])))
                t.SetWidth(mm(w)); t.SetLayer(pcbnew.B_Cu); t.SetNet(ni); t.SetLocked(True); b.Add(t)
                PRE.append((net, a, c, w))
    v = pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(mm(nrst_via[0]), mm(nrst_via[1])))
    v.SetWidth(mm(VIA_D)); v.SetDrill(mm(R1.VIA_DRILL)); v.SetNet(b.FindNet("NRST")); v.SetLocked(True); b.Add(v)
    PRE.append(("NRST", nrst_via, nrst_via, VIA_D))
    v = pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(mm(corner[0]), mm(corner[1])))
    v.SetWidth(mm(VIA_D)); v.SetDrill(mm(R1.VIA_DRILL)); v.SetNet(b.FindNet("+3V0")); v.SetLocked(True); b.Add(v)
    PRE.append(("+3V0", corner, corner, VIA_D))
    return bad


def _dseg(p, a, c):
    dx, dy = c[0] - a[0], c[1] - a[1]
    L = dx * dx + dy * dy
    u = 0 if L == 0 else max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L))
    return math.hypot(p[0] - a[0] - u * dx, p[1] - a[1] - u * dy)


def _avoid(x, y, seg_from, px, py):
    """Fan-out hook: reject a via inside the port keep-out or on a pre-route, and a stub that crosses a pre-route
    (pre-route segments that start at the stub's own pad are ignored for the stub)."""
    VR = VIA_D / 2
    if math.hypot(x - px, y - py) < PORT_KEEPOUT + VR + 0.05:
        return True
    if any(R1._d_rect(x, y, r) < VR + 0.05 for r in PAD_RECTS):
        return True
    for _, a, c, w in PRE:
        if _dseg((x, y), a, c) < w / 2 + VR + R1.GAP:
            return True
    if seg_from:
        for _, a, c, w in PRE:
            if math.dist(a, seg_from) < 1e-6 or math.dist(c, seg_from) < 1e-6:
                continue
            for k in range(1, 11):
                q = (seg_from[0] + (x - seg_from[0]) * k / 10, seg_from[1] + (y - seg_from[1]) * k / 10)
                if _dseg(q, a, c) < w / 2 + R1.STUB_W / 2 + R1.GAP:
                    return True
    return False


def _pads(f, net=None, pin=None):
    out = []
    for p in f.Pads():
        if p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
            continue
        if pin is not None and p.GetNumber() != pin:
            continue
        if net is not None and p.GetNetname() != net:
            continue
        bb = p.GetBoundingBox()
        out.append((p.GetNetname(), [MM(v) for v in (bb.GetX(), bb.GetY(), bb.GetRight(), bb.GetBottom())]))
    return out


def _gap(a, b):
    dx = max(b[0] - a[2], a[0] - b[2], 0)
    dy = max(b[1] - a[3], a[1] - b[3], 0)
    return math.hypot(dx, dy)


def port_xy(fps):
    for p in fps["U2"].Pads():
        if p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
            return MM(p.GetPosition().x), MM(p.GetPosition().y)
    raise SystemExit("U2 has no NPTH port")


def check(b, fps, W, H, fan):
    v, m = [], {}
    # face
    for ref, f in fps.items():
        want_f = ref in F_ONLY
        if ref in F_ALLOWED:
            continue
        if f.IsFlipped() == want_f:
            v.append(f"face: {ref} on {'B' if f.IsFlipped() else 'F'} (want {'F' if want_f else 'B'})")
    # fit
    for ref, f in fps.items():
        cy = f.GetCourtyard(pcbnew.B_CrtYd if f.IsFlipped() else pcbnew.F_CrtYd)
        bb = cy.BBox() if cy.OutlineCount() else f.GetBoundingBox(False)
        l, t, r, btm = (MM(x) for x in (bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom()))
        if l < -0.01 or t < -0.01 or r > W + 0.01 or btm > H + 0.01:
            v.append(f"fit: {ref} courtyard outside the outline ({l:.2f},{t:.2f})-({r:.2f},{btm:.2f})")
        for net, pr in _pads(f):
            if min(pr[0], pr[1], W - pr[2], H - pr[3]) < EDGE_COPPER:
                v.append(f"fit: {ref} pad within {EDGE_COPPER} mm of the edge")
                break
    for a, c, area in P.courtyard_overlaps(fps):
        v.append(f"fit: courtyards {a}/{c} overlap {area} mm2")
    for a, c in P.pad_clashes(fps):
        v.append(f"fit: pads {a}/{c} closer than 0.12 mm")
    v.extend(fan[2] if len(fan) > 2 else [])
    # axis
    px, py = port_xy(fps)
    m["port_xy"] = [round(px, 2), round(py, 2)]
    if abs(py - H / 2) > 0.05:
        v.append(f"axis: mic port y {py:.2f} != centre {H / 2}")
    sy = MM(fps["SW1"].GetPosition().y)
    if abs(sy - H / 2) > 0.05:
        v.append(f"axis: SW1 y {sy:.2f} != centre {H / 2}")
    # near
    for part, anchor, lim in NEAR:
        aref, _, apin = anchor.partition(".")
        pa = _pads(fps[part])
        pb = _pads(fps[aref], pin=apin or None)
        d = min((_gap(x[1], y[1]) for x in pa for y in pb if x[0] and x[0] == y[0] and x[0] != "GND"), default=None)
        if d is None:
            v.append(f"near: {part} shares no net with {anchor}")
        elif d > lim:
            v.append(f"near: {part} {d:.2f} mm from {anchor} (max {lim})")
    # QFN escape ring
    upads = [r for _, r in _pads(fps["U1"])]
    ring = [min(upads, key=lambda r: r[0])[0] - ESCAPE, min(upads, key=lambda r: r[1])[1] - ESCAPE,
            max(upads, key=lambda r: r[2])[2] + ESCAPE, max(upads, key=lambda r: r[3])[3] + ESCAPE]
    for ref, f in fps.items():
        if ref == "U1" or ref in ESCAPE_OK or f.IsFlipped() != fps["U1"].IsFlipped():
            continue
        cy = f.GetCourtyard(pcbnew.B_CrtYd if f.IsFlipped() else pcbnew.F_CrtYd)
        bb = cy.BBox() if cy.OutlineCount() else f.GetBoundingBox(False)
        r = [MM(x) for x in (bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom())]
        near_pad = any(_gap(r, u) < ESCAPE for u in upads)
        if near_pad and r[0] < ring[2] and r[2] > ring[0] and r[1] < ring[3] and r[3] > ring[1]:
            v.append(f"escape: {ref} within {ESCAPE} mm of U1's pads (only U1's support parts may sit there)")
    # far
    for ref, lim in FAR_FROM_PORT:
        x, y = (MM(c) for c in (fps[ref].GetPosition().x, fps[ref].GetPosition().y))
        d = math.hypot(x - px, y - py)
        if d < lim:
            v.append(f"far: {ref} {d:.1f} mm from the mic port (min {lim})")
    # wire pads
    wp = [(ref, n, r) for ref in WIRE_PADS for n, r in _pads(fps[ref])]
    for i, (ra, na, a) in enumerate(wp):
        for rb, nb, c in wp[i + 1:]:
            if na != nb and _gap(a, c) < PAD_GAP:
                v.append(f"pads: {ra}({na})-{rb}({nb}) gap {_gap(a, c):.2f} < {PAD_GAP}")
    for ra, rb, lim in NOT_NEIGHBOURS:
        d = min(_gap(x[1], y[1]) for x in _pads(fps[ra]) for y in _pads(fps[rb]))
        m[f"gap_{ra}_{rb}_mm"] = round(d, 2)
        if d < lim:
            v.append(f"pads: {ra}-{rb} gap {d:.2f} < {lim} (ASM-09: keep J4 GND between them)")
    # port keep-out (placement stage: pads, fan-out vias, pre-routes)
    ko = port_clear(b, px, py)
    m["port_keepout_mm"] = round(ko, 2)
    if ko < PORT_KEEPOUT:
        v.append(f"port: F copper / via {ko:.2f} mm from the mic port centre (min {PORT_KEEPOUT}, R-ACO-P6)")
    # ratsnest: sum over non-GND nets of the minimum spanning tree of pad centres (a routability proxy)
    pts = {}
    for f in fps.values():
        for p in f.Pads():
            n = p.GetNetname()
            if n and n != "GND" and p.GetAttribute() != pcbnew.PAD_ATTRIB_NPTH:
                pts.setdefault(n, []).append((MM(p.GetPosition().x), MM(p.GetPosition().y)))
    total = 0.0
    for n, q in pts.items():
        inside, rest = [q[0]], q[1:]
        while rest:
            d, k = min((math.dist(a, c), k) for k, c in enumerate(rest) for a in inside)
            total += d
            inside.append(rest.pop(k))
    m["ratsnest_mm"] = round(total, 1)
    # density
    area = {"F": 0.0, "B": 0.0}
    for ref, f in fps.items():
        cy = f.GetCourtyard(pcbnew.B_CrtYd if f.IsFlipped() else pcbnew.F_CrtYd)
        area["B" if f.IsFlipped() else "F"] += cy.Area() / 1e12 if cy.OutlineCount() else 0
    board = W * H - (4 - math.pi) * 1.0 ** 2
    m.update(board_mm2=round(board, 1), courtyard_B_mm2=round(area["B"], 1), courtyard_F_mm2=round(area["F"], 1),
             U_B=round(area["B"] / board, 3), gnd_vias=fan[0], gnd_fanout_skipped=fan[1])
    return v, m


def port_clear(b, px, py):
    """Smallest distance from the port centre to F copper (tracks, pads) or any via copper (mm)."""
    best = 1e9
    for t in b.GetTracks():
        if t.GetClass() == "PCB_VIA" or t.IsOnLayer(pcbnew.F_Cu):
            best = min(best, _copper_dist(t, px, py))
    for f in b.GetFootprints():
        for p in f.Pads():
            if p.GetAttribute() != pcbnew.PAD_ATTRIB_NPTH and p.IsOnLayer(pcbnew.F_Cu):
                best = min(best, R1._d_rect(px, py, R1._rect(p)))
    return best


def _copper_dist(t, px, py):
    if t.GetClass() == "PCB_VIA":
        return math.hypot(MM(t.GetPosition().x) - px, MM(t.GetPosition().y) - py) - MM(t.GetWidth(pcbnew.F_Cu)) / 2
    a, c = (MM(t.GetStart().x), MM(t.GetStart().y)), (MM(t.GetEnd().x), MM(t.GetEnd().y))
    return _dseg((px, py), a, c) - MM(t.GetWidth()) / 2


def probe(b):
    """Routed-board probe for the B-DOC-AUDIT-0007 items (numbers quoted in docs/system)."""
    fps = {f.GetReference(): f for f in b.GetFootprints()}
    px, py = port_xy(fps)
    out = {"port_xy": [round(px, 2), round(py, 2)], "port_keepout_mm": round(port_clear(b, px, py), 2)}
    for n in ("LSE_IN", "LSE_OUT"):
        L, vias = {}, 0
        for t in b.GetTracks():
            if t.GetNetname() != n:
                continue
            if t.GetClass() == "PCB_VIA":
                vias += 1
            else:
                k = b.GetLayerName(t.GetLayer())
                L[k] = round(L.get(k, 0) + MM(t.GetLength()), 2)
        out[n] = {"vias": vias, "mm": L, "ok": vias == 0 and sum(L.values()) <= LSE_MAX and set(L) <= {"B.Cu"}}
    u1 = {p.GetNumber(): p for p in fps["U1"].Pads()}
    p9 = (MM(u1["9"].GetPosition().x), MM(u1["9"].GetPosition().y))
    for r in ("C5", "C6"):
        q = next(p for p in fps[r].Pads() if p.GetNetname() == "+3V0")
        out[f"VDDA_pin9_to_{r}_mm"] = round(math.dist(p9, (MM(q.GetPosition().x), MM(q.GetPosition().y))), 2)
    bb = b.GetBoardEdgesBoundingBox()
    W, H = MM(bb.GetWidth()), MM(bb.GetHeight())
    r21 = fps["R21"]
    cy = r21.GetCourtyard(pcbnew.B_CrtYd).BBox()
    l, t_, r_, bt = (MM(x) for x in (cy.GetLeft(), cy.GetTop(), cy.GetRight(), cy.GetBottom()))
    out["R21"] = {"xy": [round(MM(r21.GetPosition().x), 2), round(MM(r21.GetPosition().y), 2)],
                  "courtyard_to_edge_mm": round(min(l, t_, W - r_, H - bt), 2)}
    wp = [(ref, n, rr) for ref in WIRE_PADS if ref in fps for n, rr in _pads(fps[ref])]
    gaps = []
    for i, (ra, na, a) in enumerate(wp):
        for rb, nb, c in wp[i + 1:]:
            if na != nb and _gap(a, c) < 1.5:
                gaps.append([f"{ra} {na}", f"{rb} {nb}", round(_gap(a, c), 2)])
    out["wire_pad_neighbours_lt_1.5mm"] = sorted(gaps, key=lambda g: g[2])
    out["gap_J3_J5_mm"] = round(min(_gap(x[1], y[1]) for x in _pads(fps["J3"]) for y in _pads(fps["J5"])), 2)
    return out


def route(placement, netlist, W, H, out):
    b, fps, _ = build(placement, netlist, W, H, inset=0.2)
    dsn, ses = out / "board.dsn", out / "board.ses"
    assert pcbnew.ExportSpecctraDSN(b, str(dsn))
    subprocess.run([os.environ["FREEROUTING_JAVA"], *os.environ.get("FREEROUTING_JAVA_OPTS", "-Xmx1g").split(),
                    "-jar", os.environ["FREEROUTING_JAR"], "-de", str(dsn), "-do", str(ses), "-mp", "200",
                    "--gui.enabled=false", *FR_ARGS], check=True, timeout=3000, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    b = _import(out, ses)
    target = out / "routed.kicad_pcb"
    pcbnew.SaveBoard(str(target), b)
    # second pass: FreeRouting again from the routed board (existing wiring kept), keep it if it is better (2026-10-03: 8 -> 5)
    first = _drc(target, out / "drc.json")
    dsn2, ses2 = out / "board2.dsn", out / "board2.ses"
    bt = pcbnew.LoadBoard(str(target))
    bt.GetDesignSettings().m_NetSettings.GetDefaultNetclass().SetClearance(mm(ROUTE_CLEARANCE))   # same margin as pass 1
    assert pcbnew.ExportSpecctraDSN(bt, str(dsn2))
    subprocess.run([os.environ["FREEROUTING_JAVA"], *os.environ.get("FREEROUTING_JAVA_OPTS", "-Xmx1g").split(),
                    "-jar", os.environ["FREEROUTING_JAR"], "-de", str(dsn2), "-do", str(ses2), "-mp", "200",
                    "--gui.enabled=false", *FR_ARGS], check=True, timeout=3000, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    b2 = _import(out, ses2)
    t2 = out / "routed2.kicad_pcb"
    pcbnew.SaveBoard(str(t2), b2)
    second = _drc(t2, out / "drc2.json")
    score = lambda r: (len(r["unconnected"]), sum(r["drc_by_type"].values()))  # noqa: E731
    best, bb = (second, b2) if score(second) < score(first) else (first, None)
    if bb is not None:
        pcbnew.SaveBoard(str(target), bb)
        (out / "drc.json").write_text((out / "drc2.json").read_text())
    best["passes"] = {"first": score(first), "second": score(second), "kept": "second" if bb is not None else "first"}
    best["probe"] = probe(pcbnew.LoadBoard(str(target)))
    side = Path(str(target) + ".silkdots")
    side.unlink(missing_ok=True)                    # fresh board: silk.py recomputes its pin-1 dot list
    subprocess.run([sys.executable, str(HERE / "silk.py"), str(target)], check=True, stdout=subprocess.DEVNULL)
    return best


def prune_dangling_vias(b):
    """Post-route cleanup (2026-10-07, CHK-DRCWARN): delete every via that touches copper on at most ONE layer (no track
    end on it, no pad over it, and at most one filled zone of its net). FreeRouting can leave such vias, and the locked
    NRST pre-via from preroute() stays unused when the router reaches TP3 another way; DRC flags them via_dangling.
    Zones must be filled before the call. Returns [(net, x, y)] deleted."""
    gone = []
    tracks = [t for t in b.GetTracks() if t.GetClass() == "PCB_TRACK"]
    pads = [p for fp in b.GetFootprints() for p in fp.Pads()]
    for v in [t for t in b.GetTracks() if t.GetClass() == "PCB_VIA"]:
        pos, r, net = v.GetPosition(), v.GetWidth(pcbnew.F_Cu) / 2, v.GetNetCode()
        layers = set()
        for t in tracks:
            if t.GetNetCode() == net and any((e - pos).EuclideanNorm() <= r for e in (t.GetStart(), t.GetEnd())):
                layers.add(t.GetLayer())
        for p in pads:
            if p.GetNetCode() == net and p.HitTest(pos):
                layers.update(l for l in (pcbnew.F_Cu, pcbnew.B_Cu) if p.IsOnLayer(l))
        for z in b.Zones():
            if z.GetNetCode() == net:
                layers.update(l for l in z.GetLayerSet().Seq() if z.HitTestFilledArea(l, pos))
        if len(layers) <= 1:
            gone.append((v.GetNetname(), round(pcbnew.ToMM(pos.x), 3), round(pcbnew.ToMM(pos.y), 3)))
            b.Delete(v)
    return gone


def _import(out, ses):
    b = pcbnew.LoadBoard(str(out / "placed.kicad_pcb"))
    assert pcbnew.ImportSpecctraSES(b, str(ses))
    for t in b.GetTracks():
        if t.GetClass() == "PCB_TRACK" and t.GetWidth() < mm(0.1):
            t.SetWidth(mm(0.1))
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    if prune_dangling_vias(b):                     # e.g. the unused NRST pre-via; refill so thermals follow
        pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    b.GetDesignSettings().m_NetSettings.GetDefaultNetclass().SetClearance(mm(0.09))
    return b


def _drc(target, drc):
    b = pcbnew.LoadBoard(str(target))
    subprocess.run(["kicad-cli", "pcb", "drc", "--format", "json", "--severity-error", "--output", str(drc), str(target)],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    d = json.loads(drc.read_text())
    kinds = {}
    for x in d.get("violations", []):
        kinds[x["type"]] = kinds.get(x["type"], 0) + 1
    tracks = list(b.GetTracks())
    vias = sum(1 for t in tracks if t.GetClass() == "PCB_VIA")
    return {"tracks": len(tracks) - vias, "vias": vias, "drc_by_type": kinds,
            "unconnected": [[i["description"] for i in u["items"]] for u in d.get("unconnected_items", [])]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("placement", nargs="?")
    ap.add_argument("--probe", default=None, help="probe a routed board and exit")
    ap.add_argument("--net", default=str(HERE / "pod_mz2.net"))
    ap.add_argument("--W", type=float, default=32.0)
    ap.add_argument("--H", type=float, default=12.0)
    ap.add_argument("--out", default=None)
    ap.add_argument("--route", action="store_true")
    ap.add_argument("--fr-args", default="", help='extra FreeRouting switches, e.g. "-us global"')
    a = ap.parse_args()
    FR_ARGS[:] = a.fr_args.split()
    if a.probe:
        print(json.dumps(probe(pcbnew.LoadBoard(a.probe)), indent=1))
        return
    placement = {k: tuple(v) for k, v in yaml.safe_load(open(a.placement)).items()}
    out = Path(a.out) if a.out else Path(a.placement).with_suffix("")
    out.mkdir(parents=True, exist_ok=True)
    b, fps, fan = build(placement, a.net, a.W, a.H)
    viol, metrics = check(b, fps, a.W, a.H, fan)
    pcbnew.SaveBoard(str(out / "placed.kicad_pcb"), b)
    rep = {"placement": a.placement, "W": a.W, "H": a.H, "pass": not viol, "violations": viol, "metrics": metrics}
    if a.route:
        rep["route"] = route(placement, a.net, a.W, a.H, out)
    (out / "check.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps(rep, indent=1))
    sys.exit(0 if not viol else 1)


if __name__ == "__main__":
    main()
