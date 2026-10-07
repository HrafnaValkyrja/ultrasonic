"""V5 placement-only density trial (docs/research/drastic/synthesis.md section 3): can concept K3's board shrink?

    source tools/env.sh && systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 \
        python3 hw/pod/density_trial.py [--variants a,b,c] [--jobs 4]

NO ROUTING (no FreeRouting, no autorouter). Builds a two-face, 12 mm high board per variant from hw/pod/pod_mz2.net
(mz2 packages), swaps the MCU footprint per variant, places every part with a deterministic greedy packer that honours
the place_r2.py rule set, then re-checks the result in pcbnew with real courtyard polygons. Variants:
  a  STM32U575 WLCSP-90 (U575OIY6QTR; the only U575 WLCSP), SMPS kept; ball map is SYNTHETIC (angular copy of the
     QFN48 pin order onto the two outer ball rings; the ST ballout was not read): ratsnest is approximate
  b  STM32U3 UFQFPN32 5x5 (U375/U385 K-suffix): pin map from docs/research/drastic/V3-stm32u3.yaml; no SMPS on this
     package (V3), so L1, C7 (VDDSMPS) and C3 (3rd VDD pin) go; VDD11 -> VCAP pin 31 (C8, C9 kept); MDF test dots TP8/9 go
  c  today's STM32U575 QFN48 7x7 (SMPS), netlist unchanged
Rules (place_r2.py, adapted to two faces): fit (courtyards inside, pads >= 0.3 mm from the edge, no courtyard overlap,
pads >= 0.12 mm), axis (port and SW1 on the centre line), near (NEAR table, U1 pins remapped), escape (0.6 mm ring
round the MCU pads, same face), far (L1/Q1/Q2 >= 10 mm from the port), pads (wire pads >= 0.8 mm, J3-J5 >= 2.0 mm,
same face), port (no F copper within 1.6 mm of the port; added for two faces: no F courtyard within 1.6 mm either,
the duct seat sits there), lse (Y1/C11/C12 on the MCU face: LSE pre-routed with no vias), face (SW1 on F, U2 on B).
Outputs hw/pod/density/<variant>_L<len>.kicad_pcb, hw/pod/density/results.json, docs/diagrams/density-trial.png.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pcbnew

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "tools"))
import place_r1 as R1                                # noqa: E402  (R1.P = place.py with the pod library)
import place_r2 as R2                                # noqa: E402  (NEAR, ESCAPE_OK, FAR_FROM_PORT ...)

P = R1.P
mm, MM = pcbnew.FromMM, pcbnew.ToMM
H = 12.0
PORT = (1.88, 6.0)                                   # mic port: board x ~1.9 from the front, centre line
U2_POSE = (2.65, 6.0, 90, "B")                       # today's mic pose gives exactly that port
OUT = HERE / "density"
GRID = 0.1
KEEP = []
EPS = 0.005
WIRE = R2.WIRE_PADS
NOISY = dict(R2.FAR_FROM_PORT)
CHIP_CY_MARGIN = 0.25                                # WLCSP courtyard = body + 0.25 (library draws body + 1.05)

QFN32_MAP = {  # QFN48 pin -> UFQFPN32 pin (STM32U3, DS14830 via V3-stm32u3.yaml); None = pin dropped
    "1": "1", "48": None, "9": "5", "25": "17", "36": None, "21": None,          # VDD 1/17, VDDA 5
    "3": "2", "4": "3", "7": "4",                                               # LSE PC14/PC15, NRST
    "8": "16", "22": None, "24": None, "35": "32", "41": None, "47": None, "49": "33",   # VSS 16/32 + EP
    "10": "6", "27": "7", "12": "8", "14": "9", "11": "10", "16": "11", "15": "12",     # PA0..PA6
    "17": "13", "43": "14", "28": "15", "29": "18", "42": "19", "31": "20",              # PA7 CH1N, PB0, PB1 CH3N, PA8 CH1, PA9 TX, PA10 CH3
    "32": "21", "33": "22", "34": "23", "37": "24", "38": "25",                          # USB, SWD, PA15 CHG_INT
    "39": "26", "40": "27", "26": "29", "44": "30",                                      # PB3 ADF_CCK0, PB4 ADF_SDI0, PB6 SCL, PB7-BOOT0
    "23": "31", "46": "31", "19": None, "45": None, "20": None,                          # VDD11 -> VCAP; MDF test pins, VLXSMPS gone
}
VARIANTS = {
    "a": dict(name="a_wlcsp90_u575", mcu="STM32U575OIY6QTR WLCSP-90 4.2x3.95 (SMPS)",
              fp="Package_CSP:ST_WLCSP-90_4.2x3.95mm_Layout18x10_P0.4mm_Stagger", remap="wlcsp", drop=[], target=16.0),
    "b": dict(name="b_qfn32_u3", mcu="STM32U375/U385 KxU6 UFQFPN32 5x5 (LDO only)",
              fp="Package_DFN_QFN:QFN-32-1EP_5x5mm_P0.5mm_EP3.45x3.45mm", remap=QFN32_MAP,
              drop=["L1", "C3", "C7", "TP8", "TP9"], target=16.0),
    "c": dict(name="c_qfn48_u575", mcu="STM32U575CIU6Q UFQFPN48 7x7 (SMPS, today)", fp=None, remap=None, drop=[], target=20.0),
}
ORDER = ["U2", "U1", "C13", "Y1", "C11", "C12", "C6", "C5", "C1", "C2", "C3", "C10", "C22", "R22", "C7", "C8", "C9", "L1",
         "C4", "R1", "R2", "Q1", "Q2", "SW1", "R3", "R4", "R5", "R6", "C14", "R21",
         "J5", "J4", "J3", "J1", "J2", "J7", "J8", "J9", "J10", "J11", "J12",
         "U3", "C15", "C16", "C21", "R8", "R9", "C19", "R12", "R13", "RT1", "D4", "U4", "C17", "C18", "R20", "U6", "D5",
         "D6", "R18", "R10", "R14", "R15", "R16"] + [f"TP{i}" for i in range(1, 11)]


# ------------------------------------------------------------------ netlist per variant
def wlcsp_map(fpid):
    """Synthetic QFN48 -> WLCSP-90 ball map: each QFN pin takes the free ball of the two outer rings nearest its angle."""
    q = load_fp("Package_DFN_QFN:QFN-48-1EP_7x7mm_P0.5mm_EP5.6x5.6mm")
    w = load_fp(fpid)
    pins = {p.GetNumber(): (MM(p.GetPosition().x), MM(p.GetPosition().y)) for p in q.Pads() if p.GetNumber() not in ("", "49")}
    balls = {p.GetNumber(): (MM(p.GetPosition().x), MM(p.GetPosition().y)) for p in w.Pads()}
    xm = max(abs(x) for x, _ in balls.values()); ym = max(abs(y) for _, y in balls.values())
    depth = {b: min(xm - abs(x), ym - abs(y)) for b, (x, y) in balls.items()}
    outer = [b for b in balls if depth[b] <= 0.45]
    m, used = {}, set()
    for pin in sorted(pins, key=int):
        a = math.atan2(pins[pin][1], pins[pin][0])
        best = min((b for b in outer if b not in used),
                   key=lambda b: abs(math.remainder(math.atan2(balls[b][1] / ym, balls[b][0] / xm) - a, 2 * math.pi)) + 0.3 * depth[b])
        m[pin] = best; used.add(best)
    centre = sorted((b for b in balls if b not in used), key=lambda b: math.hypot(*balls[b]))[:6]
    m["49"] = centre                                  # EP GND -> six central GND balls
    return m


def variant_netlist(v):
    comps, nets = P.parse_netlist(HERE / "pod_mz2.net")
    for r in v["drop"]:
        comps.pop(r)
    if v["fp"]:
        comps["U1"] = v["fp"]
    remap = wlcsp_map(v["fp"]) if v["remap"] == "wlcsp" else v["remap"]
    out = {}
    for n, nodes in nets.items():
        nn = []
        for ref, pin in nodes:
            if ref not in comps:
                continue
            if ref == "U1" and remap is not None:
                t = remap.get(pin)
                if t is None:
                    continue
                for tt in (t if isinstance(t, list) else [t]):
                    nn.append((ref, tt))
            else:
                nn.append((ref, pin))
        if nn:
            out[n] = nn
    near = []
    for part, anchor, lim in R2.NEAR:
        aref, _, apin = anchor.partition(".")
        if part not in comps or aref not in comps:
            continue
        if apin and remap is not None:
            t = remap.get(apin)
            if t is None:
                continue
            apin = t if isinstance(t, str) else t[0]
        near.append((part, aref, apin or None, lim))
    return comps, out, near, remap


# ------------------------------------------------------------------ footprint shapes
def load_fp(fpid):
    lib, name = fpid.split(":")
    f = pcbnew.FootprintLoad(P.fp_lib(lib), name)
    assert f is not None, fpid
    return f


def chip_courtyard(f):
    """Replace a WLCSP's library courtyard (body + 1.05 mm) with body + CHIP_CY_MARGIN (escape ring checked separately)."""
    for g in list(f.GraphicalItems()):
        if g.GetLayer() == pcbnew.F_CrtYd:
            f.Remove(g)
    bb = [MM(v) for v in (lambda r: (r.GetLeft(), r.GetTop(), r.GetRight(), r.GetBottom()))(f.GetBoundingBox(False))]
    pads = [p.GetBoundingBox() for p in f.Pads()]
    px0 = min(MM(p.GetLeft()) for p in pads); px1 = max(MM(p.GetRight()) for p in pads)
    py0 = min(MM(p.GetTop()) for p in pads); py1 = max(MM(p.GetBottom()) for p in pads)
    hx = max(2.1, (px1 - px0) / 2 + 0.2) + CHIP_CY_MARGIN; hy = max(1.975, (py1 - py0) / 2 + 0.2) + CHIP_CY_MARGIN
    s = pcbnew.PCB_SHAPE(f); s.SetShape(pcbnew.SHAPE_T_RECTANGLE); s.SetLayer(pcbnew.F_CrtYd)
    s.SetStart(pcbnew.VECTOR2I(mm(-hx), mm(-hy))); s.SetEnd(pcbnew.VECTOR2I(mm(hx), mm(hy))); s.SetWidth(mm(0.05))
    f.Add(s)
    del bb


def make_fp(ref, fpid, netof, x, y, rot, side, board):
    f = load_fp(fpid)
    if "WLCSP" in fpid:
        chip_courtyard(f)
    f.SetReference(ref)
    f.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
    f.SetOrientationDegrees(rot)
    board.Add(f)
    if side == "B":
        f.Flip(f.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    f.BuildCourtyardCaches()
    for p in f.Pads():
        n = netof.get((ref, p.GetNumber()))
        if n is not None:
            p.SetNet(board.FindNet(n))
    return f


def shape(ref, fpid, netof, rot, side, board):
    f = make_fp(ref, fpid, netof, 0.0, 0.0, rot, side, board)
    lay = pcbnew.B_CrtYd if side == "B" else pcbnew.F_CrtYd
    items = [g for g in f.GraphicalItems() if g.GetLayer() == lay]
    if len(items) == 1 and items[0].GetShape() == pcbnew.SHAPE_T_CIRCLE:
        c = items[0].GetCenter()
        bb = f.GetCourtyard(lay).BBox()                # polygonised outline incl. stroke: matches the final check
        cy = ("c", (MM(c.x), MM(c.y), max(MM(bb.GetWidth()), MM(bb.GetHeight())) / 2))
    else:
        cc = f.GetCourtyard(lay)
        bb = cc.BBox() if cc.OutlineCount() else f.GetBoundingBox(False)
        cy = ("r", tuple(MM(v) for v in (bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom())))
    rects, nets = [], []
    for p in f.Pads():
        if p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
            continue
        bb = p.GetBoundingBox()
        rects.append([MM(v) for v in (bb.GetX(), bb.GetY(), bb.GetRight(), bb.GetBottom())])
        nets.append(p.GetNetname())
    KEEP.append(f)                                    # board.Remove + GC corrupts the SWIG IO plugin (KiCad 10): keep it
    return dict(cy=cy, pads=np.array(rects, float).reshape(-1, 4), nets=nets, num=[p.GetNumber() for p in f.Pads()
                                                                                    if p.GetAttribute() != pcbnew.PAD_ATTRIB_NPTH])


def all_shapes(comps, nets):
    b = pcbnew.BOARD()
    for n in nets:
        b.Add(pcbnew.NETINFO_ITEM(b, n))
    netof = {(r, p): n for n, nodes in nets.items() for r, p in nodes}
    S = {}
    for ref, fpid in comps.items():
        for side in ("F", "B"):
            for rot in (0, 90, 180, 270):
                S[(ref, rot, side)] = shape(ref, fpid, netof, rot, side, b)
    return S, netof


# ------------------------------------------------------------------ vector geometry
def rect_gap(a, b):
    """a (N,4) vs b (M,4) -> (N,M) euclidean gap between axis-aligned rects (0 if touching/overlapping)."""
    dx = np.maximum(np.maximum(b[None, :, 0] - a[:, None, 2], a[:, None, 0] - b[None, :, 2]), 0)
    dy = np.maximum(np.maximum(b[None, :, 1] - a[:, None, 3], a[:, None, 1] - b[None, :, 3]), 0)
    return np.hypot(dx, dy)


def rect_overlap(a, b, e=EPS):
    return ((a[:, None, 0] < b[None, :, 2] - e) & (b[None, :, 0] < a[:, None, 2] - e) &
            (a[:, None, 1] < b[None, :, 3] - e) & (b[None, :, 1] < a[:, None, 3] - e))


def pt_rect_dist(px, py, r):
    """points (N,) vs rects (M,4) -> (N,M)."""
    dx = np.maximum(np.maximum(r[None, :, 0] - px[:, None], px[:, None] - r[None, :, 2]), 0)
    dy = np.maximum(np.maximum(r[None, :, 1] - py[:, None], py[:, None] - r[None, :, 3]), 0)
    return np.hypot(dx, dy)


def cy_collide(kind, geo, X, Y, placed):
    """candidate courtyard at (X,Y) vs placed [(kind, geo-abs)] same face -> (N,) bool."""
    hit = np.zeros(len(X), bool)
    rects = np.array([g for k, g in placed if k == "r"], float).reshape(-1, 4)
    circs = np.array([g for k, g in placed if k == "c"], float).reshape(-1, 3)
    if kind == "r":
        a = np.stack([X + geo[0], Y + geo[1], X + geo[2], Y + geo[3]], 1)
        if len(rects):
            hit |= rect_overlap(a, rects).any(1)
        if len(circs):
            dx = np.maximum(np.maximum(a[:, None, 0] - circs[None, :, 0], circs[None, :, 0] - a[:, None, 2]), 0)
            dy = np.maximum(np.maximum(a[:, None, 1] - circs[None, :, 1], circs[None, :, 1] - a[:, None, 3]), 0)
            hit |= (np.hypot(dx, dy) < circs[None, :, 2] - EPS).any(1)
    else:
        cx, cy_, r = X + geo[0], Y + geo[1], geo[2]
        if len(rects):
            hit |= (pt_rect_dist(cx, cy_, rects) < r - EPS).any(1)
        if len(circs):
            hit |= (np.hypot(cx[:, None] - circs[None, :, 0], cy_[:, None] - circs[None, :, 1]) < r + circs[None, :, 2] - EPS).any(1)
    return hit


def cy_abs(kind, geo, x, y):
    return (kind, (geo[0] + x, geo[1] + y, geo[2] + x, geo[3] + y)) if kind == "r" else (kind, (geo[0] + x, geo[1] + y, geo[2]))


def cy_bbox(kind, geo):
    return geo if kind == "r" else (geo[0] - geo[2], geo[1] - geo[2], geo[0] + geo[2], geo[1] + geo[2])


# ------------------------------------------------------------------ packer
class Packer:
    def __init__(self, L, S, near, comps, grid=GRID):
        self.L, self.S, self.near, self.comps, self.grid = L, S, near, comps, grid
        self.pose = {}
        self.cys = {"F": [], "B": []}
        self.pads = []            # rows: x0 y0 x1 y1 ; parallel lists net, side, ref
        self.pnet, self.pside, self.pref = [], [], []
        self.fail = {}
        self.pnum = {}

    def padarr(self, mask=None):
        a = np.array(self.pads, float).reshape(-1, 4)
        return a if mask is None else a[mask]

    def candidates(self, sh):
        k, g = sh["cy"]
        bx0, by0, bx1, by1 = cy_bbox(k, g)
        pr = sh["pads"]
        lo_x = max(-bx0, 0.3 - pr[:, 0].min()); hi_x = min(self.L - bx1, self.L - 0.3 - pr[:, 2].max())
        lo_y = max(-by0, 0.3 - pr[:, 1].min()); hi_y = min(H - by1, H - 0.3 - pr[:, 3].max())
        if hi_x < lo_x or hi_y < lo_y:
            return np.zeros(0), np.zeros(0)
        G = self.grid
        xs = np.round(np.arange(math.ceil(lo_x / G - 1e-9), math.floor(hi_x / G + 1e-9) + 1) * G, 3)
        ys = np.round(np.arange(math.ceil(lo_y / G - 1e-9), math.floor(hi_y / G + 1e-9) + 1) * G, 3)
        X, Y = np.meshgrid(xs, ys)
        return X.ravel(), Y.ravel()

    def evaluate(self, ref, rot, side, X, Y):
        """-> (rule masks dict, cost) for candidate positions."""
        sh = self.S[(ref, rot, side)]
        k, g = sh["cy"]
        pr, pn = sh["pads"], sh["nets"]
        N = len(X)
        bad = {}
        bad["fit"] = cy_collide(k, g, X, Y, self.cys[side])
        side_mask = np.array([s == side for s in self.pside], bool)
        allp = self.padarr()
        if side_mask.any():
            other = allp[side_mask]
            onet = [n for n, s in zip(self.pnet, self.pside) if s == side]
            clash = np.zeros(N, bool)
            for i in range(len(pr)):
                a = np.stack([X + pr[i, 0], Y + pr[i, 1], X + pr[i, 2], Y + pr[i, 3]], 1)
                diff = np.array([not (pn[i] and pn[i] == m) for m in onet], bool)
                if diff.any():
                    o = other[diff]
                    gap = 0.12
                    clash |= ((a[:, None, 0] - gap < o[None, :, 2]) & (o[None, :, 0] - gap < a[:, None, 2]) &
                              (a[:, None, 1] - gap < o[None, :, 3]) & (o[None, :, 1] - gap < a[:, None, 3])).any(1)
            bad["fit"] |= clash
        # escape ring round the MCU pads, same face, non-support parts
        if "U1" in self.pose and ref != "U1" and ref not in R2.ESCAPE_OK and self.pose["U1"][3] == side:
            bx0, by0, bx1, by1 = cy_bbox(k, g)
            a = np.stack([X + bx0, Y + by0, X + bx1, Y + by1], 1)
            bad["escape"] = rect_overlap(a, np.array([self.ring]), e=-0.002)[:, 0]
        if ref == "U1":                                # the reverse: nothing foreign may already sit in the ring
            pass
        if ref in NOISY:
            bad["far"] = np.hypot(X - PORT[0], Y - PORT[1]) < NOISY[ref]
        if side == "F":
            m = np.zeros(N, bool)
            for i in range(len(pr)):
                a = np.stack([X + pr[i, 0], Y + pr[i, 1], X + pr[i, 2], Y + pr[i, 3]], 1)
                m |= rect_gap(np.array([[PORT[0], PORT[1], PORT[0], PORT[1]]]), a)[0] < R2.PORT_KEEPOUT
            bx0, by0, bx1, by1 = cy_bbox(k, g)
            a = np.stack([X + bx0, Y + by0, X + bx1, Y + by1], 1)
            m |= rect_gap(np.array([[PORT[0], PORT[1], PORT[0], PORT[1]]]), a)[0] < R2.PORT_KEEPOUT
            bad["port"] = m
        if ref in WIRE:
            wm = np.array([r in WIRE and s == side for r, s in zip(self.pref, self.pside)], bool)
            if wm.any():
                o = allp[wm]
                onet = [n for n, r, s in zip(self.pnet, self.pref, self.pside) if r in WIRE and s == side]
                oref = [r for r, s in zip(self.pref, self.pside) if r in WIRE and s == side]
                m = np.zeros(N, bool)
                for i in range(len(pr)):
                    a = np.stack([X + pr[i, 0], Y + pr[i, 1], X + pr[i, 2], Y + pr[i, 3]], 1)
                    gp = rect_gap(a, o)
                    for j, (n, r) in enumerate(zip(onet, oref)):
                        lim = 2.0 if {ref, r} == {"J3", "J5"} else (R2.PAD_GAP if n != pn[i] else 0)
                        m |= gp[:, j] < lim
                bad["pads"] = m
        if ref in ("Y1", "C11", "C12") and "U1" in self.pose and self.pose["U1"][3] != side:
            bad["lse"] = np.ones(N, bool)
        if ref == "SW1":
            bad["axis"] = np.abs(Y - H / 2) > 1e-6
        # near rules with an already placed partner
        nm = np.zeros(N, bool)
        for part, aref, apin, lim in self.near:
            if ref not in (part, aref):
                continue
            other_ref = aref if ref == part else part
            if other_ref not in self.pose:
                continue
            idx = [j for j, r in enumerate(self.pref) if r == other_ref]
            onum = self.pnum[other_ref]
            if ref == aref and apin:                   # I am the anchor: restrict MY pads to the pin
                mine = [i for i in range(len(pr)) if sh["num"][i] == apin]
                theirs = idx
            else:
                mine = list(range(len(pr)))
                theirs = [j for jj, j in enumerate(idx) if apin is None or ref == aref or onum[jj] == apin]
            best = np.full(N, np.inf)
            for i in mine:
                if not pn[i] or pn[i] == "GND":
                    continue
                js = [j for j in theirs if self.pnet[j] == pn[i]]
                if not js:
                    continue
                a = np.stack([X + pr[i, 0], Y + pr[i, 1], X + pr[i, 2], Y + pr[i, 3]], 1)
                best = np.minimum(best, rect_gap(a, allp[js]).min(1))
            if np.isinf(best).all():
                continue                                # no shared net (variant dropped it)
            nm |= best > lim
        bad["near"] = nm
        # cost: ratsnest increment (+0.3 mm per face crossing), pulls
        cost = np.zeros(N)
        cx = (pr[:, 0] + pr[:, 2]) / 2; cyy = (pr[:, 1] + pr[:, 3]) / 2
        for n in set(pn):
            if not n or n == "GND":
                continue
            js = [j for j, m in enumerate(self.pnet) if m == n]
            if not js:
                continue
            q = allp[js]; qx = (q[:, 0] + q[:, 2]) / 2; qy = (q[:, 1] + q[:, 3]) / 2
            qs = np.array([0.0 if self.pside[j] == side else 0.3 for j in js])
            d = np.full(N, np.inf)
            for i in [i for i in range(len(pr)) if pn[i] == n]:
                d = np.minimum(d, (np.hypot(X[:, None] + cx[i] - qx[None], Y[:, None] + cyy[i] - qy[None]) + qs[None]).min(1))
            cost += d
        if ref in WIRE:
            cost += 1.0 * (self.L - X)
        if "U1" in self.pose:
            cost += 0.02 * np.hypot(X - self.pose["U1"][0], Y - self.pose["U1"][1])
        return bad, cost

    def commit(self, ref, x, y, rot, side):
        sh = self.S[(ref, rot, side)]
        self.pose[ref] = (float(x), float(y), rot, side)
        self.cys[side].append(cy_abs(*sh["cy"], x, y))
        self.pnum = getattr(self, "pnum", {})
        self.pnum[ref] = sh["num"]
        for r, n in zip(sh["pads"], sh["nets"]):
            self.pads.append([r[0] + x, r[1] + y, r[2] + x, r[3] + y]); self.pnet.append(n); self.pside.append(side); self.pref.append(ref)
        if ref == "U1":
            pr = sh["pads"]
            self.ring = (pr[:, 0].min() + x - R2.ESCAPE, pr[:, 1].min() + y - R2.ESCAPE,
                         pr[:, 2].max() + x + R2.ESCAPE, pr[:, 3].max() + y + R2.ESCAPE)

    def place(self, ref, sides=("B", "F"), rots=(0, 90, 180, 270), fixed=None):
        if fixed:
            self.commit(ref, *fixed)
            return
        best = None
        for side in sides:
            for rot in rots:
                X, Y = self.candidates(self.S[(ref, rot, side)])
                if not len(X):
                    continue
                free = ~cy_collide(*self.S[(ref, rot, side)]["cy"], X, Y, self.cys[side])
                if free.any():                         # cheap prefilter: courtyard-free positions only
                    X, Y = X[free], Y[free]
                bad, cost = self.evaluate(ref, rot, side, X, Y)
                nviol = sum(m.astype(int) for m in bad.values())
                key = nviol * 1000.0 + cost
                i = int(np.argmin(key))
                cand = (key[i], int(nviol[i]), cost[i], X[i], Y[i], rot, side, [k for k, m in bad.items() if m[i]])
                if best is None or cand[0] < best[0] - 1e-9:
                    best = cand
        if best is None:
            self.fail[ref] = ["fit: no position inside the outline"]
            return
        _, nv, _, x, y, rot, side, rules = best
        if nv:
            self.fail[ref] = rules
        self.commit(ref, x, y, rot, side)


def run_pack(args):
    L, u1pose, S, near, comps, grid = args
    pk = Packer(L, S, near, comps, grid)
    pk.place("U2", fixed=(*U2_POSE[:2], U2_POSE[2], U2_POSE[3]))
    x, y, rot = u1pose
    sh = S[("U1", rot, "B")]
    k, g = sh["cy"]
    bx0, by0, bx1, by1 = cy_bbox(k, g)
    if x + bx0 < 0 or x + bx1 > L or y + by0 < 0 or y + by1 > H:
        return None
    X, Y = np.array([x]), np.array([y])
    bad, _ = pk.evaluate("U1", rot, "B", X, Y)
    if any(m[0] for m in bad.values()):
        return None
    pk.commit("U1", x, y, rot, "B")
    k2, g2 = S[("U2", U2_POSE[2], U2_POSE[3])]["cy"]
    u2 = cy_bbox(k2, tuple(np.add(g2, (U2_POSE[0], U2_POSE[1], U2_POSE[0], U2_POSE[1]))) if k2 == "r" else g2)
    if rect_overlap(np.array([u2]), np.array([pk.ring]))[0, 0]:
        return None                                   # the mic would sit in the MCU escape ring
    for ref in ORDER:
        if ref in ("U2", "U1") or ref not in comps:
            continue
        if ref == "SW1":
            pk.place(ref, sides=("F",))
        else:
            pk.place(ref)
    for ref in comps:
        assert ref in pk.pose or ref in pk.fail, ref
    rats = ratsnest(pk.pads, pk.pnet)
    return dict(L=L, u1=u1pose, pose=pk.pose, fail=pk.fail, nfail=len(pk.fail), rats=rats)


def ratsnest(pads, pnet, skip=("GND",)):
    pts = {}
    for r, n in zip(pads, pnet):
        if n and n not in skip:
            pts.setdefault(n, []).append(((r[0] + r[2]) / 2, (r[1] + r[3]) / 2))
    total = 0.0
    for q in pts.values():
        inside, rest = [q[0]], list(q[1:])
        while rest:
            d, k = min((math.dist(a, c), k) for k, c in enumerate(rest) for a in inside)
            total += d
            inside.append(rest.pop(k))
    return round(total, 1)


# ------------------------------------------------------------------ pcbnew board + full check
def build_board(L, comps, nets, pose):
    for mod in (P, R2.P):
        mod.W, mod.H, mod.CORNER = L, H, 1.0
    b = pcbnew.BOARD()
    P.rules(b)
    P.outline(b)
    for n in nets:
        b.Add(pcbnew.NETINFO_ITEM(b, n))
    netof = {(r, p): n for n, nodes in nets.items() for r, p in nodes}
    fps = {}
    for ref, fpid in comps.items():
        x, y, rot, side = pose[ref]
        fps[ref] = make_fp(ref, fpid, netof, x, y, rot, side, b)
    b.GetDesignSettings().SetBoardThickness(mm(0.8))
    return b, fps


def full_check(b, fps, L, near):
    v = []
    for ref, f in fps.items():
        lay = pcbnew.B_CrtYd if f.IsFlipped() else pcbnew.F_CrtYd
        cy = f.GetCourtyard(lay)
        bb = cy.BBox() if cy.OutlineCount() else f.GetBoundingBox(False)
        l, t, r, btm = (MM(x) for x in (bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom()))
        if l < -0.01 or t < -0.01 or r > L + 0.01 or btm > H + 0.01:
            v.append(f"fit: {ref} courtyard outside the outline")
        for net, pr in R2._pads(f):
            if min(pr[0], pr[1], L - pr[2], H - pr[3]) < R2.EDGE_COPPER - 1e-3:
                v.append(f"fit: {ref} pad within {R2.EDGE_COPPER} mm of the edge"); break
    for a, c, area in P.courtyard_overlaps(fps):
        v.append(f"fit: courtyards {a}/{c} overlap {area} mm2")
    for a, c in P.pad_clashes(fps):
        v.append(f"fit: pads {a}/{c} closer than 0.12 mm")
    if fps["SW1"].IsFlipped():
        v.append("face: SW1 on B")
    if not fps["U2"].IsFlipped():
        v.append("face: U2 on F")
    px, py = R2.port_xy(fps)
    if abs(py - H / 2) > 0.05 or abs(px - PORT[0]) > 0.05:
        v.append(f"axis: port at {px:.2f},{py:.2f}")
    if abs(MM(fps["SW1"].GetPosition().y) - H / 2) > 0.05:
        v.append("axis: SW1 off the centre line")
    for part, aref, apin, lim in near:
        pa = R2._pads(fps[part]); pb = R2._pads(fps[aref], pin=apin)
        d = min((R2._gap(x[1], y[1]) for x in pa for y in pb if x[0] and x[0] == y[0] and x[0] != "GND"), default=None)
        if d is not None and d > lim + 1e-3:
            v.append(f"near: {part} {d:.2f} mm from {aref}{'.' + apin if apin else ''} (max {lim})")
    upads = [r for _, r in R2._pads(fps["U1"])]
    ring = [min(r[0] for r in upads) - R2.ESCAPE, min(r[1] for r in upads) - R2.ESCAPE,
            max(r[2] for r in upads) + R2.ESCAPE, max(r[3] for r in upads) + R2.ESCAPE]
    for ref, f in fps.items():
        if ref == "U1" or ref in R2.ESCAPE_OK or f.IsFlipped() != fps["U1"].IsFlipped():
            continue
        cy = f.GetCourtyard(pcbnew.B_CrtYd if f.IsFlipped() else pcbnew.F_CrtYd)
        bb = cy.BBox() if cy.OutlineCount() else f.GetBoundingBox(False)
        r = [MM(x) for x in (bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom())]
        if any(R2._gap(r, u) < R2.ESCAPE for u in upads) and r[0] < ring[2] and r[2] > ring[0] and r[1] < ring[3] and r[3] > ring[1]:
            v.append(f"escape: {ref} within {R2.ESCAPE} mm of U1's pads")
    for ref, lim in R2.FAR_FROM_PORT:
        if ref in fps:
            d = math.hypot(MM(fps[ref].GetPosition().x) - px, MM(fps[ref].GetPosition().y) - py)
            if d < lim:
                v.append(f"far: {ref} {d:.1f} mm from the mic port (min {lim})")
    wp = [(ref, fps[ref].IsFlipped(), n, r) for ref in WIRE if ref in fps for n, r in R2._pads(fps[ref])]
    for i, (ra, sa, na, a) in enumerate(wp):
        for rb, sb, nb, c in wp[i + 1:]:
            if sa == sb and na != nb:
                lim = 2.0 if {ra, rb} == {"J3", "J5"} else R2.PAD_GAP
                if R2._gap(a, c) < lim - 1e-3:
                    v.append(f"pads: {ra}-{rb} gap {R2._gap(a, c):.2f} < {lim}")
    ko = R2.port_clear(b, px, py)
    if ko < R2.PORT_KEEPOUT:
        v.append(f"port: F copper {ko:.2f} mm from the port")
    for ref, f in fps.items():
        if not f.IsFlipped():
            cy = f.GetCourtyard(pcbnew.F_CrtYd)
            if cy.OutlineCount():
                bb = cy.BBox()
                r = [MM(x) for x in (bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom())]
                if R2._gap(r, [px, py, px, py]) < R2.PORT_KEEPOUT:
                    v.append(f"port: F courtyard of {ref} within {R2.PORT_KEEPOUT} mm of the port (duct seat)")
    for ref in ("Y1", "C11", "C12"):
        if fps[ref].IsFlipped() != fps["U1"].IsFlipped():
            v.append(f"lse: {ref} not on the MCU face")
    return v


def metrics(b, fps, L):
    """Density + routability proxies. Calibrated against today's board (routed at its density)."""
    area = L * H - (4 - math.pi) * 1.0 ** 2
    cy = {"F": 0.0, "B": 0.0}
    padA = {"F": 0.0, "B": 0.0}
    pins = sig_pins = 0
    pads, pnet, pside = [], [], []
    for f in fps.values():
        s = "B" if f.IsFlipped() else "F"
        c = f.GetCourtyard(pcbnew.B_CrtYd if f.IsFlipped() else pcbnew.F_CrtYd)
        cy[s] += c.Area() / 1e12 if c.OutlineCount() else 0
        for p in f.Pads():
            if p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                continue
            bb = p.GetBoundingBox()
            r = [MM(v) for v in (bb.GetX(), bb.GetY(), bb.GetRight(), bb.GetBottom())]
            padA[s] += (r[2] - r[0] + 0.2) * (r[3] - r[1] + 0.2)      # pad + 0.1 mm clearance all round
            n = p.GetNetname()
            if n:
                pins += 1
                sig_pins += n not in ("GND", "+3V0")
                pads.append(r); pnet.append(n); pside.append(s)
    rats_all = ratsnest(pads, pnet)                                     # place_r2 metric (GND skipped)
    rats_sig = ratsnest(pads, pnet, skip=("GND", "+3V0"))               # what the 2 outer layers must carry
    plane_vias = sum(1 for n in pnet if n in ("GND", "+3V0"))
    nets_x = {}
    for n, s in zip(pnet, pside):
        nets_x.setdefault(n, set()).add(s)
    cross = sum(1 for n, s in nets_x.items() if len(s) == 2 and n not in ("GND", "+3V0"))
    demand = rats_sig * 0.2 + (plane_vias + 2 * cross) * 0.55 ** 2 * 2   # track pitch 0.2; vias block both outer layers
    supply = 2 * area - padA["F"] - padA["B"]
    return dict(board_mm2=round(area, 1), courtyard_F_mm2=round(cy["F"], 1), courtyard_B_mm2=round(cy["B"], 1),
                U_F=round(cy["F"] / area, 3), U_B=round(cy["B"] / area, 3), U_both=round((cy["F"] + cy["B"]) / (2 * area), 3),
                pins=pins, signal_pins=sig_pins, pins_per_mm2=round(pins / area, 3),
                ratsnest_mm=rats_all, ratsnest_signal_mm=rats_sig, ratsnest_per_mm2=round(rats_all / area, 3),
                cross_face_signal_nets=cross, demand_mm2=round(demand, 1), supply_mm2=round(supply, 1),
                demand_supply=round(demand / supply, 3),
                demand_supply_6L=round(demand / (supply + 2 * area), 3))   # + 2 inner signal layers (vias already in demand)


def today():
    b = pcbnew.LoadBoard(str(HERE / "draft_r2/out/placed.kicad_pcb"))
    fps = {f.GetReference(): f for f in b.GetFootprints()}
    m = metrics(b, fps, 30.0)
    rb = pcbnew.LoadBoard(str(HERE / "draft_r2/out/routed.kicad_pcb"))
    tl = {"F": 0.0, "B": 0.0, "in": 0.0}; vias = 0
    for t in rb.GetTracks():
        if t.GetClass() == "PCB_VIA":
            vias += 1
        else:
            k = "F" if t.GetLayer() == pcbnew.F_Cu else "B" if t.GetLayer() == pcbnew.B_Cu else "in"
            tl[k] += MM(t.GetLength())
    m["routed_track_mm"] = {k: round(v, 1) for k, v in tl.items()}
    m["routed_vias"] = vias
    return m, {r: (MM(f.GetPosition().x), MM(f.GetPosition().y), f.IsFlipped()) for r, f in fps.items()}, b, fps


def verdict(rel, legal):
    if not legal:
        return "no (placement illegal)"
    if rel <= 1.15:
        return "likely"
    if rel <= 1.5:
        return "possible (tight: expect via-in-pad / 6 layers / manual routing)"
    return "unlikely"


def run_variant(key, lengths, jobs, ref_ratio):
    v = VARIANTS[key]
    comps, nets, near, remap = variant_netlist(v)
    S, _ = all_shapes(comps, nets)
    results = []
    for L in lengths:
        t0 = time.time()
        poses = [(x, H / 2 + dy, rot) for x in np.arange(4.0, L - 2.0, 1.0) for dy in (0.0, -1.0, 1.0) for rot in (0, 90, 180, 270)]
        with Pool(jobs) as pool:                       # coarse 0.2 mm grid over all MCU poses, then the best 4 at 0.1 mm
            rs = [r for r in pool.map(run_pack, [(L, p, S, near, comps, 0.2) for p in poses]) if r]
            npose = len(rs)
            top = sorted(rs, key=lambda r: (r["nfail"], r["rats"]))[:4]
            rs = [r for r in pool.map(run_pack, [(L, r["u1"], S, near, comps, GRID) for r in top]) if r] + top
        if not rs:
            results.append(dict(L=L, legal=False, note="MCU does not fit")); continue
        best = min(rs, key=lambda r: (r["nfail"], r["rats"]))
        b, fps = build_board(L, comps, nets, best["pose"])
        viol = full_check(b, fps, L, near)
        m = metrics(b, fps, L)
        rel = round(m["demand_supply"] / ref_ratio, 2)
        rel6 = round(m["demand_supply_6L"] / ref_ratio, 2)
        res = dict(L=L, legal=not viol, violations=viol, packer_fail=best["fail"], u1_pose=[round(float(c), 2) for c in best["u1"]],
                   tried_u1_poses=npose, metrics=m, routing_load_vs_today=rel, routability=verdict(rel, not viol),
                   routing_load_6L_vs_today_4L=rel6, routability_6L=verdict(rel6, not viol),
                   pose={r: [round(p[0], 2), round(p[1], 2), p[2], p[3]] for r, p in best["pose"].items()}, secs=round(time.time() - t0, 1))
        OUT.mkdir(exist_ok=True)
        pcbnew.SaveBoard(str(OUT / f"{v['name']}_L{L:g}.kicad_pcb"), b)
        results.append(res)
        print(f"{v['name']} L={L:g}: legal={not viol} nviol={len(viol)} U={m['U_both']} pins/mm2={m['pins_per_mm2']} "
              f"rats={m['ratsnest_mm']} load x{rel} [{res['secs']} s] {viol[:4]}", flush=True)
    return dict(variant=v, near_rules=len(near), remap=(remap if key == "b" else ("synthetic WLCSP ball map" if remap else None)),
                results=results)


def plot(allres, today_m, today_pose, today_fps):
    sys.path.insert(0, str(REPO / "tools"))
    import plotstyle
    plt = plotstyle.apply()
    from matplotlib.patches import Rectangle, Circle
    rows = [("today: one face, 30 mm (routed)", 30.0, None)]
    for key, rv in allres.items():
        legal = [r for r in rv["results"] if r.get("legal")]
        tgt = [r for r in rv["results"] if r["L"] == rv["variant"]["target"]]
        show = []
        if tgt:
            show.append(tgt[0])
        if legal and (not tgt or not tgt[0]["legal"]):
            show.append(min(legal, key=lambda r: r["L"]))
        for r in show[:1] if len(show) == 1 or show[0]["L"] == show[-1]["L"] else show:
            rows.append((f"{rv['variant']['name']} L={r['L']:g} mm: {'LEGAL' if r['legal'] else 'ILLEGAL'}, U {r['metrics']['U_both']:.0%}, "
                         f"load x{r['routing_load_vs_today']} -> {r['routability']}", r["L"], (rv, r)))
    fig, axes = plt.subplots(len(rows), 2, figsize=(11, 2.7 * len(rows)), squeeze=False)
    fig.subplots_adjust(hspace=0.55)
    S = plotstyle.SERIES
    col = lambda ref: S[1] if ref in ("L1", "Q1", "Q2") else S[0] if ref == "U1" else S[2] if ref == "U2" else S[3] if ref in WIRE else S[6]  # noqa: E731
    for i, (title, L, data) in enumerate(rows):
        if data is None:
            fps = today_fps
        else:
            rv, r = data
            comps, nets, near, _ = variant_netlist(rv["variant"])
            _, fps = build_board(L, comps, nets, {k: tuple(p) for k, p in r["pose"].items()})
        bad = set()
        if data is not None:
            for s in r["violations"]:
                for tok in s.replace("/", " ").replace("-", " ").replace(",", " ").split():
                    if tok in fps:
                        bad.add(tok)
        for j, face in enumerate(("F", "B")):
            ax = axes[i][j]
            ax.add_patch(Rectangle((0, 0), L, H, fill=False, ec=plotstyle.TEXT_2, lw=1))
            for ref, f in fps.items():
                if ("B" if f.IsFlipped() else "F") != face:
                    continue
                c = f.GetCourtyard(pcbnew.B_CrtYd if f.IsFlipped() else pcbnew.F_CrtYd)
                bb = c.BBox() if c.OutlineCount() else f.GetBoundingBox(False)
                x0, y0, w, h = MM(bb.GetLeft()), MM(bb.GetTop()), MM(bb.GetWidth()), MM(bb.GetHeight())
                ax.add_patch(Rectangle((x0, y0), w, h, fc=col(ref), alpha=0.35, ec=S[7] if ref in bad else col(ref), lw=1.6 if ref in bad else 0.6))
                if w * h > 1.5:
                    ax.text(x0 + w / 2, y0 + h / 2, ref, ha="center", va="center", fontsize=5.5, color=plotstyle.TEXT)
            ax.add_patch(Circle(PORT, R2.PORT_KEEPOUT, fill=False, ec=S[2], ls="--", lw=0.8))
            ax.add_patch(Circle(PORT, 10.0, fill=False, ec=S[1], ls=":", lw=0.7))
            ax.set_xlim(-0.5, 30.5); ax.set_ylim(H + 0.5, -0.5); ax.set_aspect("equal"); ax.grid(False)
            ax.set_title(f"{title}\n{face} face" if j == 0 else f"{face} face", fontsize=7.5, loc="left")
            ax.tick_params(labelsize=6)
    fig.suptitle("V5 placement-only density trial (no routing). Orange = noisy (L1/Q1/Q2), dotted = 10 mm from the mic port, "
                 "red edge = part in a violation", fontsize=8.5, color=plotstyle.TEXT)
    out = REPO / "docs/diagrams/density-trial.png"
    fig.savefig(out)
    print("wrote", out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variants", default="a,b,c")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--lengths", default=None, help="override, e.g. 15,16,17")
    ap.add_argument("--plot-only", action="store_true", help="redraw the PNG from hw/pod/density/results.json")
    a = ap.parse_args()
    today_m, today_pose, tb, tfps = today()
    if a.plot_only:
        d = json.loads((OUT / "results.json").read_text())
        for rv in d["variants"].values():
            rv["variant"]["target"] = float(rv["variant"]["target"])
        plot(d["variants"], today_m, today_pose, tfps)
        return
    ref_ratio = today_m["demand_supply"]
    print("today", json.dumps(today_m), flush=True)
    sweep = {"a": [14, 15, 16, 17, 18, 19, 20], "b": [14, 15, 16, 17, 18, 19, 20], "c": [18, 19, 20, 21, 22, 23, 24]}
    allres = {}
    for k in a.variants.split(","):
        ls = [float(x) for x in a.lengths.split(",")] if a.lengths else sweep[k]
        allres[k] = run_variant(k, ls, a.jobs, ref_ratio)
    OUT.mkdir(exist_ok=True)
    if a.lengths and (OUT / "results.json").exists():    # merge extra lengths into the stored sweep
        old = json.loads((OUT / "results.json").read_text())["variants"]
        for k, rv in allres.items():
            if k in old:
                keep = [r for r in old[k]["results"] if r["L"] not in {x["L"] for x in rv["results"]}]
                rv["results"] = sorted(keep + rv["results"], key=lambda r: r["L"])
        allres = {**old, **allres}
        for rv in allres.values():
            rv["variant"]["target"] = float(rv["variant"]["target"])
    (OUT / "results.json").write_text(json.dumps({"today": today_m, "variants": allres}, indent=1, default=str))
    plot(allres, today_m, today_pose, tfps)


if __name__ == "__main__":
    main()
