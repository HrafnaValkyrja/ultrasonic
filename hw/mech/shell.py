"""Pod shell = TWO resin prints: TUB (inner face + top/bottom/front/rear walls up to the seam) and
LID (0.9 mm outer wall + Blade armour, circuit-trace groove, dorsal fin, button flexure, mic chimney).

    source tools/env.sh && systemd-run --user --scope --quiet -p MemoryMax=2G -p MemorySwapMax=0 \
        python3 hw/mech/shell.py          # -> hw/mech/out/parts/shell/ (STEP, STL, checks.json, PNG)

Builds two variants against the pre-rev-1 pod (PRE_R1 below; was frame.py's until ECR-0001) + frame.py's adapter/fasteners:

  "proposed" (RECOMMENDED, exported at the top of out/parts/shell/)
      The tub is an empty box apart from features outside the cell's drop-in corridor: front cap,
      front PCB stops, rear nut bosses. The LID locates the PCB: its ribs press the outer-face clamp
      bands, its webs locate the board edges and its rear stops push it forward. Two strips of soft
      foam on the cell press the PCB up against the lid. The lid goes on 0.45 mm behind its seat and
      slides forward so its front tongue hooks under the tub's front cap. The PCB rides along, so the
      chimney, washer, button nub and tongue never slide over the board. Needs two interface changes
      (see INTERFACE_REQUESTS): the PCM lies flat on the cell's rear top face, and the lid screws
      move to x = 64.2, behind the cell.

  "as_frame" (the task text, literally; exported to out/parts/shell/as_frame/)
      PCB ledge ribs and nut bosses at frame.LID_SCREWS in the tub. checks.json shows why it can't be
      built. The ledges leave a 10.4 mm gap for a 12.5 mm cell, and the x = 60.8 bosses sit over the
      cell/PCM, so the cell cannot be put in or taken out once the tub is printed.

Frame: x rearward, y outward, z up; mm. Resin rules (frame.RESIN): walls >= 0.6 (0.8 preferred),
slots >= 0.3, ream critical holes after printing, captured brass nuts (no heat-set inserts).
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from build123d import (Box, Compound, Cylinder, Plane, Pos, Rot, chamfer, export_step, export_stl)

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "tools"))
import frame as _frame  # noqa: E402
from types import SimpleNamespace  # noqa: E402

# Pre-rev-1 pod (2026-09-30): the numbers this shell was designed on. frame.py held them until ECR-0001 (2026-10-07) moved
# frame.py's pod names to the current design; frozen here unchanged so this historical shell (and hw/padboard/mech.py's
# pre-rev-1 checks) still build what they built. NOT the current pod: see frame.pod_facts() / hw/current.yaml.
_X0, _X1, _Z0, _Z1, _WALL, _Y_OUT, _Y_SPLIT = 29.5, 67.5, -9.5, 5.5, 0.8, 14.3, 13.4
PRE_R1 = dict(
    X0=_X0, X1=_X1, Z0=_Z0, Z1=_Z1, ZC=-2.0, Y_OUT=_Y_OUT, WALL=_WALL, Y_SPLIT=_Y_SPLIT, EDGE_CHAMFER=1.0,
    CAV=dict(x0=_X0 + _WALL, x1=_X1 - _WALL, y0=_frame.Y_IN + _WALL, y1=_Y_SPLIT, z0=_Z0 + _WALL, z1=_Z1 - _WALL),
    TAPE=0.3,
    CELL=dict(x0=30.6, x1=61.6, y0=5.4, y1=9.7, z0=-8.25, z1=4.25),       # LP401230 MAX envelope
    PCM=dict(x0=61.8, x1=64.8, y0=5.4, y1=9.7, z0=-8.25, z1=4.25),        # cell protection board [Low]
    PCB=dict(x0=30.6, x1=50.6, y0=11.1, y1=11.9, z0=-7.75, z1=3.75),      # 20 x 11.5 x 0.8, 4-layer
    PARTS_IN=dict(y0=9.9, y1=11.1), PARTS_OUT=dict(y0=11.9, y1=13.1),
    PCB_CLAMP_BAND=0.6, PCB_END_KEEPOUT=0.5,
    WIRE_PADS=["OUT_A", "OUT_B", "LED+", "LED-", "BAT+", "BAT-", "VBUS", "GND_CHG"],
    WIRE_PAD=dict(x0=49.2, x1=50.4, z_top=3.0, pitch=1.3, h=1.0),
    MIC_PORT=dict(x=34.5, z=-1.0, d_pcb=0.6, d_lid=1.0),
    MIC_SEAL=dict(chimney_od=2.6, chimney_id=1.0, washer_od=3.0, washer_t=0.8, keepout_r=1.6),
    BUTTON=dict(x=42.5, z=1.9, body=(3.0, 2.0), height=0.6, travel=0.25, force_n=1.6),   # KXT321LHS on the outer face
    LID_SCREWS=[(60.8, 2.7), (60.8, -6.4)], LID_HOOK=dict(z0=-5.0, z1=1.0),
)


# blade.py's rail/adapter/fin/armour default to the CURRENT pod since ECR-0001: pin them to the pre-rev-1 body this shell was built on
def rail():
    return _blade.rail(zc=PRE_R1["ZC"])


def adapter():
    return _blade.adapter(zc=PRE_R1["ZC"])


def fin():
    return _blade.fin(z1=PRE_R1["Z1"], y_out=PRE_R1["Y_OUT"])


def armour_and_trace():
    return _blade.armour_and_trace(y_out=PRE_R1["Y_OUT"], z1=PRE_R1["Z1"], mic=(29.5 + 5.0, PRE_R1["ZC"] + 1.0))


# F: frame.py's own constants (adapter, fasteners, resin, arm) + the frozen pre-rev-1 pod
F = SimpleNamespace(**{k: getattr(_frame, k) for k in dir(_frame) if k.isupper() and k not in PRE_R1 and k != "POD_NAMES"}, **PRE_R1)
import blade as _blade  # noqa: E402
from blade import prism_xy, prism_xz  # noqa: E402
from styles import plate  # noqa: E402

OUT = HERE / "out" / "parts" / "shell"
T0 = time.time()

# ============================================================================ parameters
X0, X1, Z0, Z1 = F.X0, F.X1, F.Z0, F.Z1
Y_IN, Y_OUT, YS = F.Y_IN, F.Y_OUT, F.Y_SPLIT
CAV = F.CAV
FIT = F.RESIN["slide_fit"]                       # 0.15 per side for sliding fits
ARM_T = 0.8                                      # armour plate (blade.armour_and_trace)
Y_ARM = Y_OUT + ARM_T                            # 15.1 armour face
UP_T = 0.45                                      # upper (button) plate thickness
Y_UP = Y_ARM + UP_T                              # 15.55

# --- front hook: tongue under an overhanging cap of the tub's front wall (frame.LID_HOOK z band)
CAP_X1 = 30.8          # rear face of the tub's front cap (lid layer); overhangs the wall's inner face by 0.5
SEAM = 0.15            # cap <-> lid gap on the outer face (visible panel line)
LID_X0 = CAP_X1 + SEAM                            # 30.95 lid front face
TONGUE = dict(x0=CAV["x0"] + FIT, x1=31.05, y0=12.7, y_top=YS - 0.05, root_x1=32.0, root_y0=13.15,
              z0=F.LID_HOOK["z0"] + FIT, z1=F.LID_HOOK["z1"] - FIT)
SLIDE = 0.45           # lid goes on this far behind its seat, then slides forward (engagement 0.35 + 0.1)

# --- PCB location
PCB = F.PCB
BAND = F.PCB_CLAMP_BAND
RIB_GAP = 0.05         # lid rib tip <-> PCB outer face, nominal (shim with Kapton if it rattles)
RIB_Y0 = PCB["y1"] + RIB_GAP                      # 11.95
TOP_BAND = (PCB["z1"] - BAND, PCB["z1"])          # 3.15 .. 3.75
BOT_BAND = (PCB["z0"], PCB["z0"] + BAND)          # -7.75 .. -7.15
EDGE_GAP = 0.2         # lid web <-> PCB top/bottom edge (z location)
WEB_T = 0.6
RIB_X = (31.0, 50.6)   # lid ribs/webs along the board (front 0.4 is the board's own end keepout)
REAR_STOP_X = (PCB["x1"] + 0.05, PCB["x1"] + 0.7)  # lid rear stops push the PCB forward during the slide
FRONT_STOP_X1 = PCB["x0"] - 0.05                  # tub front stops (in front of the cell: x < 30.6)

# --- button flexure (the small upper armour plate becomes a hinged tongue)
BTN = F.BUTTON
UP_PTS = [(34.5, 3.5), (45.6, 3.5), (43.6, 1.3), (34.5, 1.3)]  # blade's upper plate, rear edge +1.6 to cover the button
HINGE_X = (36.2, 37.8)  # thinned hinge (front end of the tongue); slot arms start at HINGE_X[0]
HINGE_T = 0.6
SLOT_W = 0.4
RELIEF = 0.45           # tongue underside relieved so it can't touch 1.2 mm parts when pressed
NUB_R = 0.5
NUB_GAP = 0.05

# --- mic seal (frame.MIC_SEAL): chimney on the lid, punched foam washer seated on its tip
MIC = F.MIC_PORT
SEAL = F.MIC_SEAL
WASHER_SQUEEZE = 0.2    # 0.8 foam compressed to 0.6
CHIM_Y0 = PCB["y1"] + SEAL["washer_t"] - WASHER_SQUEEZE   # 12.5 chimney tip

# --- fasteners: M1.4 x 3 pan head into captured brass DIN 934 nuts; heads double as charge contacts
SCREW = F.FASTENERS["M1.4_pan"]
NUT = F.FASTENERS["M1.4_nut"]
SCREW_L = 3.0
CB_D = SCREW["head_d"] + 0.2                       # counterbore 2.8
Y_CB = Y_ARM - SCREW["head_h"]                     # 14.2 head bearing face (head flush with the armour)
ROOF = 0.8                                         # boss material between nut and lid
POCKET_H = NUT["m"] + FIT                          # 1.35
Y_POCKET1 = YS - ROOF                              # 12.6
Y_POCKET0 = Y_POCKET1 - POCKET_H                   # 11.25
BOSS_Y0 = 9.9                                      # 0.2 above the cell's MAX top face
HOLE_Y0 = 10.5                                     # blind screw hole bottom (floor 0.6 guards the cell)
SIDE_WALL = 0.65

VARIANTS = {
    "proposed": dict(screws=[(64.2, 2.7), (64.2, -5.6)], boss_x=(62.0, CAV["x1"]),
                     pcm=dict(x0=57.4, x1=61.4, y0=9.75, y1=11.95, z0=-8.0, z1=4.0),
                     pcb_by="lid"),
    "as_frame": dict(screws=list(F.LID_SCREWS), boss_x=None, pcm=F.PCM, pcb_by="tub"),
}
HEEL_KEEP = dict(x0=50.0, x1=68.0, y0=-5.0, y1=6.3, z0=-15.0, z1=-4.3)   # heel.py's region: no bosses here

RESIN_RHO = 1.18e-3     # g/mm^3, cured tough/ABS-like resin (typical datasheet 1.1-1.2 g/cm^3)
E_RESIN = 2000.0        # MPa, tough/ABS-like resin (1.5-2.5 GPa typical); used for the hinge force only


# ============================================================================ helpers
def box(x0, x1, y0, y1, z0, z1):
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(x1 - x0, y1 - y0, z1 - z0)


def bx(d, **kw):
    e = dict(d)
    e.update(kw)
    return box(e["x0"], e["x1"], e["y0"], e["y1"], e["z0"], e["z1"])


def cyl_y(x, z, r, y0, y1):
    return Pos(x, (y0 + y1) / 2, z) * Rot(90, 0, 0) * Cylinder(r, y1 - y0)


def hex_pts(x, z, af, vertex_up=True):
    R = af / math.sqrt(3)
    a0 = 90.0 if vertex_up else 0.0
    return [(x + R * math.cos(math.radians(a0 + 60 * k)), z + R * math.sin(math.radians(a0 + 60 * k)))
            for k in range(6)]


def offset_poly(pts, d):
    """Outward offset of a convex polygon (x, z) by d (mitred corners)."""
    n = len(pts)
    area = sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1] for i in range(n))
    s = 1.0 if area > 0 else -1.0
    lines = []
    for i in range(n):
        (xa, za), (xb, zb) = pts[i], pts[(i + 1) % n]
        tx, tz = xb - xa, zb - za
        L = math.hypot(tx, tz)
        nx, nz = s * tz / L, -s * tx / L          # outward normal
        lines.append(((xa + d * nx, za + d * nz), (tx, tz)))
    out = []
    for i in range(n):
        (p1, d1), (p2, d2) = lines[i - 1], lines[i]
        den = d1[0] * d2[1] - d1[1] * d2[0]
        t = ((p2[0] - p1[0]) * d2[1] - (p2[1] - p1[1]) * d2[0]) / den
        out.append((p1[0] + t * d1[0], p1[1] + t * d1[1]))
    return out


def vol(s):
    try:
        return float(s.volume) if s is not None else 0.0
    except Exception:
        return 0.0


def overlap(a, b):
    try:
        return round(vol(a & b), 4)
    except Exception as e:      # noqa: BLE001
        return f"error: {e}"


def gap(a, b):
    try:
        return round(a.distance_to(b), 3)
    except Exception as e:      # noqa: BLE001
        return f"error: {e}"


def outer_box():
    b = box(X0, X1, Y_IN, Y_OUT, Z0, Z1)
    return chamfer(b.edges(), F.EDGE_CHAMFER)


def panel_line():
    """blade.build's panel line across the top face at x = 41, made 0.2 deep (leaves a 0.6 wall)."""
    return box(40.75, 41.25, Y_OUT - 4.0, Y_OUT + 2.0, Z1 - 0.2, Z1 + 0.5)


# ============================================================================ tub
def nut_boss(cx, cz, x0, x1, upper):
    """Boss hanging from the top (upper=True) or bottom wall, y 9.9..13.4 (the seam).
    The hex pocket has a ROOF toward the lid, so tightening pulls the nut against tub material and
    clamps the lid to the tub. The nut goes in from the SIDE: the pocket's slot opens toward the
    pod's mid-height (the wire gap between the bosses), and the nut slides in with its wire."""
    af = NUT["pocket_af"]
    R = af / math.sqrt(3)
    if upper:                      # slot mouth = the boss's bottom face, 2.2 below the nut centre
        z0, z1 = cz - 2.2, CAV["z1"]
    else:
        z0, z1 = CAV["z0"], cz + 2.2
    body = box(x0, x1, BOSS_Y0, YS, z0, z1)
    pocket = prism_xz(hex_pts(cx, cz, af, vertex_up=True), Y_POCKET0, Y_POCKET1)
    zm = z0 - 0.1 if upper else z1 + 0.1
    slot = box(cx - af / 2, cx + af / 2, Y_POCKET0, Y_POCKET1, min(zm, cz), max(zm, cz))
    hole = cyl_y(cx, cz, SCREW["clear"] / 2, HOLE_Y0, YS + 0.1)
    wire = box(cx - 0.45, cx + 0.45, Y_POCKET0 - 0.6, Y_POCKET0 + 0.01, min(zm, cz), max(zm, cz))
    cut = pocket + slot + hole + wire
    info = dict(cx=cx, cz=cz, x=(x0, x1), z=(round(z0, 2), round(z1, 2)), y=(BOSS_Y0, YS),
                walls_mm={
                    "roof (nut -> lid)": round(YS - Y_POCKET1, 2),
                    "floor under pocket": round(Y_POCKET0 - BOSS_Y0, 2),
                    "floor under blind hole": round(HOLE_Y0 - BOSS_Y0, 2),
                    "floor under wire notch": round(Y_POCKET0 - 0.6 - BOSS_Y0, 2),
                    "front (x-) beside flats": round(cx - af / 2 - x0, 2),
                    "rear (x+) beside flats": round(x1 - (cx + af / 2), 2) if x1 < CAV["x1"] else
                    round(X1 - (cx + af / 2), 2),
                    "closed end (vertex -> outside)": round((Z1 - (cz + R)) if upper else ((cz - R) - Z0), 2),
                })
    return body, cut, info


def build_tub(v):
    o = outer_box()
    tub = (o & box(X0 - 1, X1 + 1, Y_IN - 1, YS, Z0 - 1, Z1 + 1)) - bx(CAV, y1=YS)
    cap = o & box(X0 - 1, CAP_X1, YS, Y_OUT + 1, Z0 - 1, Z1 + 1)
    tub = tub + cap
    feats = {}
    if v["pcb_by"] == "lid":
        # front stops only (they sit in front of the cell, x < 30.6, so they don't trap it)
        for (za, zb) in (TOP_BAND, BOT_BAND):
            feats.setdefault("pcb_stops", []).append(box(CAV["x0"] - 0.01, FRONT_STOP_X1, 10.9, PCB["y1"], za, zb))
    else:
        # literal task: ledge ribs under the inner-face clamp bands, z stops, front + rear stops
        L = []
        L.append(box(CAV["x0"] - 0.01, PCB["x1"], 9.9, PCB["y0"], TOP_BAND[0] + 0.05, CAV["z1"] + 0.01))
        L.append(box(CAV["x0"] - 0.01, PCB["x1"], PCB["y0"] - 0.01, PCB["y1"], PCB["z1"] + 0.1, CAV["z1"] + 0.01))
        L.append(box(CAV["x0"] - 0.01, PCB["x1"], 9.9, PCB["y0"], CAV["z0"] - 0.01, BOT_BAND[1] - 0.05))
        L.append(box(CAV["x0"] - 0.01, PCB["x1"], PCB["y0"] - 0.01, PCB["y1"], CAV["z0"] - 0.01, PCB["z0"] - 0.1))
        for (za, zb) in (TOP_BAND, BOT_BAND):
            L.append(box(CAV["x0"] - 0.01, FRONT_STOP_X1, PCB["y0"] - 0.01, PCB["y1"], za, zb))
        L.append(box(PCB["x1"] + 0.1, PCB["x1"] + 0.9, 9.9, PCB["y1"], TOP_BAND[0] + 0.05, CAV["z1"] + 0.01))
        L.append(box(PCB["x1"] + 0.1, PCB["x1"] + 0.9, 9.9, PCB["y1"], CAV["z0"] - 0.01, BOT_BAND[1] - 0.05))
        feats["pcb_ledges"] = L
    cuts, binfo = [], []
    for k, (sx, sz) in enumerate(v["screws"]):
        upper = sz > F.ZC
        R = NUT["pocket_af"] / math.sqrt(3)
        if v["boss_x"]:
            x0, x1 = v["boss_x"]
        else:
            x0, x1 = sx - NUT["pocket_af"] / 2 - SIDE_WALL, sx + NUT["pocket_af"] / 2 + SIDE_WALL
        body, cut, info = nut_boss(sx, sz, x0, x1, upper)
        feats.setdefault("bosses", []).append(body)
        cuts.append(cut)
        info["role"] = "VBUS contact" if k == 0 else "GND_CHG contact"
        binfo.append(info)
    for group in feats.values():
        for s in group:
            tub = tub + s
    tub = tub + rail()
    for c in cuts:
        tub = tub - c
    tub = tub - panel_line()
    return tub, feats, binfo


# ============================================================================ lid
def upper_plate():
    return plate(UP_PTS, Y_ARM, UP_T, 0.2)


def button_cuts():
    """U-slot through lid+armour+plate around the tongue, hinge thinned from the inside, tongue
    underside relieved. Returns (cut solid, tongue outline pts, slot outer pts)."""
    outer = offset_poly(UP_PTS, SLOT_W)
    keep_front = box(X0 - 1, HINGE_X[0], YS - 1, Y_UP + 1, Z0 - 1, Z1 + 1)
    slot = prism_xz(outer, YS - 0.05, Y_UP + 0.3) - prism_xz(UP_PTS, YS - 0.1, Y_UP + 0.4) - keep_front
    hinge = box(HINGE_X[0], HINGE_X[1], YS - 0.1, Y_UP - HINGE_T, UP_PTS[3][1], UP_PTS[0][1])
    relief = prism_xz(UP_PTS, YS - 0.1, YS + RELIEF) & box(HINGE_X[0], X1, YS - 1, Y_UP, Z0, Z1)
    return slot + hinge + relief, outer


def lid_tongue():
    t = TONGUE
    pts = [(t["x0"], t["y0"]), (t["x1"], t["y0"]), (t["x1"], t["root_y0"]), (t["root_x1"], t["root_y0"]),
           (t["root_x1"], YS + 0.05), (LID_X0, YS + 0.05), (LID_X0, t["y_top"]), (t["x0"], t["y_top"])]
    return prism_xy(pts, t["z0"], t["z1"])


def lid_pcb_features(v):
    """Ribs press the PCB's outer-face clamp bands. In 'proposed' the lid also has webs beside the
    board edges (z location) and rear stops (x location; they push the board forward as the lid slides)."""
    f = []
    gap0, gap1 = 35.8, 46.6           # top rib interrupted under the button flexure
    top_rib = (TOP_BAND[0] + 0.05, CAV["z1"] - 0.15)      # 0.05 inside the band edge: never touches parts
    bot_rib = (CAV["z0"] + 0.15, BOT_BAND[1] - 0.05)
    for (xa, xb) in ((RIB_X[0], gap0), (gap1, RIB_X[1])):
        f.append(box(xa, xb, RIB_Y0, YS + 0.05, *top_rib))
    f.append(box(RIB_X[0], RIB_X[1], RIB_Y0, YS + 0.05, *bot_rib))
    if v["pcb_by"] == "lid":
        wz_top = (PCB["z1"] + EDGE_GAP, CAV["z1"] - 0.15)            # 3.95 .. 4.55
        wz_bot = (CAV["z0"] + 0.15, PCB["z0"] - EDGE_GAP)            # -8.55 .. -7.95
        wy0 = PCB["y0"] + 0.05                                        # 11.15: clear of the foam strips
        for wz in (wz_top, wz_bot):
            f.append(box(RIB_X[0], REAR_STOP_X[1], wy0, YS + 0.05, *wz))
        f.append(box(*REAR_STOP_X, wy0, YS + 0.05, TOP_BAND[0] + 0.05, wz_top[1]))
        f.append(box(*REAR_STOP_X, wy0, YS + 0.05, wz_bot[0], BOT_BAND[1] - 0.05))
    return f


def build_lid(v, armour_main):
    o = outer_box()
    lid = o & box(LID_X0, X1 + 1, YS, Y_OUT + 2, Z0 - 1, Z1 + 1)
    lid = lid + armour_main + upper_plate()
    # dorsal fin: the part over the tub rests 0.05 above the tub's top face; slivers trimmed
    fn = fin()
    fin_lid = (fn & box(40, 70, YS, 20, Z0, 20)) + (fn & box(53.0, 70, 10.4, YS + 0.01, Z1 + 0.05, 20))
    lid = lid + fin_lid
    for s in lid_pcb_features(v):
        lid = lid + s
    lid = lid + cyl_y(MIC["x"], MIC["z"], SEAL["chimney_od"] / 2, CHIM_Y0, YS + 0.05)
    lid = lid + lid_tongue()
    bcut, slot_outer = button_cuts()
    lid = lid - bcut
    lid = lid + cyl_y(BTN["x"], BTN["z"], NUB_R, PCB["y1"] + BTN["height"] + NUB_GAP, YS + RELIEF + 0.05)
    lid = lid - cyl_y(MIC["x"], MIC["z"], SEAL["chimney_id"] / 2, CHIM_Y0 - 0.1, Y_UP + 1)
    for (sx, sz) in v["screws"]:
        lid = lid - cyl_y(sx, sz, CB_D / 2, Y_CB, Y_UP + 1) - cyl_y(sx, sz, SCREW["clear"] / 2, YS - 0.2, Y_CB + 0.01)
    lid = lid - panel_line()
    return lid, slot_outer


# ============================================================================ placeholders
def placeholders(v):
    p = {}
    p["cell"] = bx(F.CELL)
    p["pcm"] = bx(v["pcm"])
    p["tape"] = box(F.CELL["x0"], F.CELL["x1"], CAV["y0"], CAV["y0"] + F.TAPE, F.CELL["z0"], F.CELL["z1"])
    p["pcb"] = bx(PCB) - cyl_y(MIC["x"], MIC["z"], MIC["d_pcb"] / 2, PCB["y0"] - 1, PCB["y1"] + 1)
    ex = dict(x0=PCB["x0"] + F.PCB_END_KEEPOUT, x1=PCB["x1"] - F.PCB_END_KEEPOUT,
              z0=PCB["z0"] + BAND, z1=PCB["z1"] - BAND)
    p["parts_in"] = bx(ex, y0=F.PARTS_IN["y0"], y1=F.PARTS_IN["y1"])
    bw, bh = BTN["body"]
    btn = dict(x0=BTN["x"] - bw / 2, x1=BTN["x"] + bw / 2, z0=BTN["z"] - bh / 2, z1=BTN["z"] + bh / 2)
    p["parts_out"] = (bx(ex, y0=F.PARTS_OUT["y0"], y1=F.PARTS_OUT["y1"])
                      - cyl_y(MIC["x"], MIC["z"], SEAL["keepout_r"], PCB["y1"] - 0.1, F.PARTS_OUT["y1"] + 0.1)
                      - bx(btn, y0=PCB["y1"] + BTN["height"], y1=F.PARTS_OUT["y1"] + 0.1))
    p["button"] = bx(btn, y0=PCB["y1"], y1=PCB["y1"] + BTN["height"])
    p["washer"] = (cyl_y(MIC["x"], MIC["z"], SEAL["washer_od"] / 2, PCB["y1"], CHIM_Y0)
                   - cyl_y(MIC["x"], MIC["z"], SEAL["chimney_id"] / 2, PCB["y1"] - 0.1, CHIM_Y0 + 0.1))
    if v["pcb_by"] == "lid":
        # soft foam strips on the cell under the PCB's inner-face bands (spring the PCB against the lid)
        for nm, (za, zb) in (("foam_top", (TOP_BAND[0], F.CELL["z1"])), ("foam_bot", (F.CELL["z0"], BOT_BAND[1]))):
            p[nm] = box(32.0, 49.5, F.CELL["y1"], PCB["y0"], za, zb)
    for k, (sx, sz) in enumerate(v["screws"]):
        y_nut1 = Y_POCKET1
        nut = prism_xz(hex_pts(sx, sz, NUT["s"], vertex_up=True), y_nut1 - NUT["m"], y_nut1)
        p[f"nut_{k}"] = nut - cyl_y(sx, sz, SCREW["d"] / 2, y_nut1 - 2, y_nut1 + 1)
        head = cyl_y(sx, sz, SCREW["head_d"] / 2, Y_CB, Y_CB + SCREW["head_h"])
        p[f"screw_{k}"] = head + cyl_y(sx, sz, SCREW["d"] / 2, Y_CB - SCREW_L, Y_CB + 0.01)
    return p


# ============================================================================ checks
def corridor_check(tub, v, feats=None):
    """The cell (+ PCM when it sits at the cell's end) drops in from the open (outer) side. Any tub
    material inside its xz footprint at y above the cell's seat blocks it. Try it at its seat and
    shifted rearward (it can be lowered behind its seat and slid forward under the front cap)."""
    res = {}
    parts = [F.CELL] + ([v["pcm"]] if v["pcm"]["y0"] < F.CELL["y1"] else [])
    for dx in (0.0, 0.3):
        sweep = None
        for d in parts:
            s = box(d["x0"] + dx, d["x1"] + dx, d["y1"] - 0.01, Y_OUT + 2, d["z0"], d["z1"])
            sweep = s if sweep is None else sweep + s
        res[f"overlap_mm3 (lowered at dx=+{dx})"] = overlap(tub, sweep)
        if dx == 0.0:
            sweep0 = sweep
    res["passes"] = min(v_ for v_ in res.values() if isinstance(v_, float)) < 1e-3
    if feats:
        res["blocking_by_feature_mm3 (dx=0, feature bodies before pocket cuts)"] = {k: round(sum(vol(s_ & sweep0) for s_ in g), 2)
                                                 for k, g in feats.items()}
        res["opening_between_ledges_z_mm"] = round((TOP_BAND[0] + 0.05) - (BOT_BAND[1] - 0.05), 2) \
            if "pcb_ledges" in feats else None
        res["cell_height_z_mm (MAX envelope)"] = round(F.CELL["z1"] - F.CELL["z0"], 2)
    return res


def slide_check(lid, tub, tub_contents):
    """Lid lowered SLIDE behind its seat, then pushed forward. In 'proposed' the PCB rides with the
    lid, so only tub-held contents (cell, PCM, nuts, foam) matter."""
    out = {}
    for dx in (SLIDE, 0.3, 0.15, 0.0):
        L = Pos(dx, 0, 0) * lid
        r = {"lid&tub": overlap(L, tub)}
        for k, s in tub_contents.items():
            r[f"lid&{k}"] = overlap(L, s)
        out[f"dx={dx}"] = r
    for dy in (2.0, 0.6):
        L = Pos(SLIDE, dy, 0) * lid
        out[f"drop dx={SLIDE} dy={dy}"] = {"lid&tub": overlap(L, tub)}
    ok = all(all((not isinstance(x, float)) or x < 1e-3 for x in r.values()) for r in out.values())
    out["passes"] = ok
    return out


def hinge_numbers():
    arm = BTN["x"] - (HINGE_X[0] + HINGE_X[1]) / 2
    Lh = HINGE_X[1] - HINGE_X[0]
    defl = NUB_GAP + BTN["travel"]
    theta = defl / arm
    kappa = theta / Lh
    strain = kappa * HINGE_T / 2
    width = UP_PTS[0][1] - UP_PTS[3][1]
    I = width * HINGE_T ** 3 / 12
    M = E_RESIN * I * kappa
    f_hinge = M / arm
    tip_x = max(p[0] for p in UP_PTS)
    return {
        "hinge_thickness_mm": HINGE_T, "hinge_length_mm": Lh, "hinge_width_mm": width,
        "slot_width_mm": SLOT_W, "nub_arm_from_hinge_centre_mm": round(arm, 2),
        "deflection_at_nub_mm (gap + switch travel)": round(defl, 3),
        "hinge_bending_strain_pct": round(100 * strain, 2),
        "hinge_spring_force_at_nub_N (E=2.0 GPa)": round(f_hinge, 2),
        "finger_force_at_nub_N (hinge + KXT321 1.6 N)": round(f_hinge + BTN["force_n"], 2),
        "tongue_tip_dip_mm": round(defl * (tip_x - (HINGE_X[0] + HINGE_X[1]) / 2) / arm, 2),
        "tongue_underside_to_parts_at_full_press_mm": round(
            YS + RELIEF - defl * (tip_x - (HINGE_X[0] + HINGE_X[1]) / 2) / arm - F.PARTS_OUT["y1"], 2),
        "verdict": "OK for tough/ABS-like resin (elongation >= 10%); standard brittle resin may fatigue",
    }


def mic_duct():
    seg = {"pcb_hole (d0.6)": PCB["y1"] - PCB["y0"], "washer (compressed)": CHIM_Y0 - PCB["y1"],
           "chimney": YS - CHIM_Y0, "lid wall": Y_OUT - YS}
    L = sum(seg.values())
    r = SEAL["chimney_id"] / 2
    Leff = L + 0.85 * r            # flanged open end (the armour hex window is a shallow recess)
    c = 343e3
    return {"segments_mm": {k: round(v_, 2) for k, v_ in seg.items()}, "length_mm": round(L, 2),
            "quarter_wave_kHz (closed at mic)": round(c / (4 * Leff) / 1e3, 1),
            "three_quarter_wave_kHz": round(3 * c / (4 * Leff) / 1e3, 1),
            "note": "both inside the 20-85 kHz band: S1 coupons must use THIS stack (R14); DSP EQ flattens it"}


def screw_numbers(v):
    tip = Y_CB - SCREW_L
    nut0, nut1 = Y_POCKET1 - NUT["m"], Y_POCKET1
    engaged = max(0.0, nut1 - max(nut0, tip))
    return {"screw": f"M1.4 x {SCREW_L} pan/cheese head (eyeglass)", "head_bearing_y": Y_CB,
            "head_top_y (flush with armour)": round(Y_CB + SCREW["head_h"], 2),
            "lid_under_head_mm": round(Y_CB - YS, 2), "nut_y": [round(nut0, 2), round(nut1, 2)],
            "thread_engagement_mm": round(engaged, 2), "engagement_in_pitches (P=0.3)": round(engaged / 0.3, 1),
            "tip_y": round(tip, 2), "blind_hole_bottom_y": HOLE_Y0,
            "tip_to_hole_bottom_mm": round(tip - HOLE_Y0, 2),
            "longest_safe_screw_mm": round(Y_CB - HOLE_Y0 - 0.1, 2),
            "cell_top_y": F.CELL["y1"],
            "note": ("bosses are behind the cell (x >= 62): a long screw cannot reach it" if v["pcb_by"] == "lid"
                     else "bosses sit OVER the cell: never use screws longer than 3.5 mm (0.6 mm floor, then the LiPo)")}


# ============================================================================ figure
def section_polys(shape, plane, axes):
    try:
        sk = shape & plane
    except Exception:       # noqa: BLE001
        return []
    polys = []
    for f in sk.faces():
        try:
            verts, tris = f.tessellate(0.01)
        except Exception:   # noqa: BLE001
            continue
        P = np.array([[getattr(v_, a) for a in axes] for v_ in verts])
        for t in tris:
            polys.append(P[list(t)])
    return polys


def figure(parts, path, title):
    import plotstyle
    plt = plotstyle.apply()
    from matplotlib.collections import PolyCollection
    S = plotstyle.SERIES
    style = {"tub": (S[0], 0.85), "lid": (S[1], 0.85), "cell": (S[2], 0.35), "pcm": (S[2], 0.2),
             "pcb": (S[5], 0.9), "nut_0": (S[3], 1), "nut_1": (S[3], 1), "screw_0": (S[3], 0.7),
             "screw_1": (S[3], 0.7), "washer": (S[4], 0.9), "button": (S[6], 0.9),
             "parts_in": (plotstyle.TEXT_2, 0.15), "parts_out": (plotstyle.TEXT_2, 0.15),
             "foam_top": (S[4], 0.45), "foam_bot": (S[4], 0.45), "tape": (S[4], 0.3)}
    sx, sz = VARIANTS["proposed"]["screws"][0]
    views = [
        ("Outer face (cut at y = 14.7, in the armour)", Plane.XZ.offset(-14.7), ("X", "Z"), (29, 68), (-10, 9)),
        (f"Section x = {sx}: lid screw, captured nut (VBUS)", Plane.YZ.offset(sx), ("Y", "Z"), (3, 16.5), (-10, 9)),
        (f"Section x = {BTN['x']}: button flexure, PCB ribs/webs", Plane.YZ.offset(BTN["x"]), ("Y", "Z"), (3, 16.5), (-10, 9)),
        (f"Plan z = {MIC['z']}: front hook, mic chimney, rear wire gap", Plane.XY.offset(MIC["z"]), ("X", "Y"), (29, 68), (3, 16.5)),
    ]
    fig, axs = plt.subplots(2, 2, figsize=(13, 8.6), gridspec_kw=dict(width_ratios=[2.6, 1.1]))
    order = [axs[0, 0], axs[0, 1], axs[1, 1], axs[1, 0]]
    for ax, (ttl, pl, axes, xl, yl) in zip(order, views):
        for k, s in parts.items():
            if k not in style:
                continue
            col, a = style[k]
            polys = section_polys(s, pl, axes)
            if polys:
                ax.add_collection(PolyCollection(polys, facecolors=col, edgecolors=col, linewidths=0.15, alpha=a))
        ax.set_xlim(*xl)
        ax.set_ylim(*yl)
        ax.set_aspect("equal")
        ax.set_title(ttl)
        ax.set_xlabel(f"{axes[0].lower()} (mm)")
        ax.set_ylabel(f"{axes[1].lower()} (mm)")
    from matplotlib.patches import Patch
    handles = [Patch(color=style[k][0], label=lab) for k, lab in
               (("tub", "tub (print 1)"), ("lid", "lid (print 2)"), ("cell", "cell / PCM"), ("pcb", "PCB"),
                ("nut_0", "brass nut / screw"), ("washer", "foam washer / strips"), ("button", "KXT321"),
                ("parts_in", "parts envelopes"))]
    fig.legend(handles=handles, loc="lower center", ncol=8, frameon=False)
    fig.suptitle(title, color=plotstyle.TEXT)
    fig.savefig(path)
    plt.close(fig)


def figure_slide(parts, path):
    """Front hook, plan section z = -1: (a) lid + PCB lowered 0.45 mm behind the seat, (b) slid forward."""
    import plotstyle
    plt = plotstyle.apply()
    from matplotlib.collections import PolyCollection
    S = plotstyle.SERIES
    style = {"tub": (S[0], 0.85), "lid": (S[1], 0.85), "cell": (S[2], 0.35), "pcb": (S[5], 0.9),
             "washer": (S[4], 0.9), "parts_out": (plotstyle.TEXT_2, 0.15), "parts_in": (plotstyle.TEXT_2, 0.15)}
    moving = ("lid", "pcb", "washer", "parts_out", "parts_in")
    pl = Plane.XY.offset(MIC["z"])
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.6))
    for ax, dx, ttl in ((axs[0], SLIDE, f"1. Lower the lid (PCB on its ribs) {SLIDE} mm behind its seat"),
                        (axs[1], 0.0, "2. Push it forward: the tongue slides under the tub's front cap")):
        for k, sh in parts.items():
            if k not in style:
                continue
            col, a = style[k]
            sh2 = Pos(dx, 0, 0) * sh if k in moving else sh
            polys = section_polys(sh2, pl, ("X", "Y"))
            if polys:
                ax.add_collection(PolyCollection(polys, facecolors=col, edgecolors=col, linewidths=0.15, alpha=a))
        ax.set_xlim(29, 38.5)
        ax.set_ylim(9, 16)
        ax.set_aspect("equal")
        ax.set_title(ttl)
        ax.set_xlabel("x (mm)")
        ax.set_ylabel("y (mm)")
    t = TONGUE
    axs[1].annotate("tongue under cap\n0.35 mm", xy=((t["x0"] + CAP_X1) / 2, t["y_top"] - 0.2), xytext=(31.2, 9.6),
                    color=plotstyle.TEXT, fontsize=8, arrowprops=dict(arrowstyle="->", color=plotstyle.TEXT_2))
    axs[1].annotate("chimney + foam washer\n(moves with the PCB)", xy=(MIC["x"] + 1.3, 12.8), xytext=(35.6, 14.9),
                    color=plotstyle.TEXT, fontsize=8, arrowprops=dict(arrowstyle="->", color=plotstyle.TEXT_2))
    axs[0].annotate("", xy=(30.9, 15.6), xytext=(32.4, 15.6),
                    arrowprops=dict(arrowstyle="->", color=S[3], lw=2))
    axs[0].text(32.5, 15.45, f"slide {SLIDE} mm", color=S[3], fontsize=8)
    fig.suptitle("Front hook: no relative motion between lid features and the PCB", color=plotstyle.TEXT)
    fig.savefig(path)
    plt.close(fig)


# ============================================================================ main
def build_variant(name, armour_main):
    v = VARIANTS[name]
    tub, feats, binfo = build_tub(v)
    lid, slot_outer = build_lid(v, armour_main)
    ph = placeholders(v)
    return v, tub, lid, ph, feats, binfo, slot_outer


def run_checks(name, v, tub, lid, ph, feats, binfo, slot_outer):
    c = {}
    contents = ["cell", "pcm", "tape", "pcb", "parts_in", "parts_out", "button", "washer"] + \
               [k for k in ph if k.startswith("foam")]
    c["overlap_mm3 (must be 0)"] = {f"{p}&{k}": overlap(s, ph[k]) for p, s in (("tub", tub), ("lid", lid))
                                    for k in contents}
    c["overlap_mm3 (must be 0)"]["tub&lid"] = overlap(tub, lid)
    c["min_gap_mm"] = {f"{p}&{k}": gap(s, ph[k]) for p, s in (("tub", tub), ("lid", lid))
                       for k in ("cell", "pcm", "pcb", "parts_in", "parts_out")}
    c["min_gap_mm"]["nub&button (design 0.05)"] = gap(
        cyl_y(BTN["x"], BTN["z"], NUB_R, PCB["y1"] + BTN["height"] + NUB_GAP, YS), ph["button"])
    c["min_gap_mm"]["chimney tip&washer (design 0 = seated)"] = gap(lid, ph["washer"])
    c["nut_fit"] = {f"tub&nut_{k}": overlap(tub, ph[f"nut_{k}"]) for k in range(len(v["screws"]))}
    c["nut_fit"].update({f"lid&screw_{k} (head in counterbore)": overlap(lid, ph[f"screw_{k}"])
                         for k in range(len(v["screws"]))})
    c["heel_region_free_of_bosses"] = {
        "boss&heel_region_mm3": sum(overlap(b, bx(HEEL_KEEP)) or 0 for b in feats.get("bosses", []))}
    c["cell_insertion_corridor"] = corridor_check(tub, v, feats)
    c["single_solid"] = {"tub": len(tub.solids()), "lid": len(lid.solids())}
    c["rail&heel_region_mm3 (for heel.py)"] = overlap(rail(), bx(HEEL_KEEP))
    ad = adapter()
    c["frame_adapter (blade.adapter)"] = {"adapter&tub_mm3": overlap(ad, tub), "adapter&lid_mm3": overlap(ad, lid),
                                          "adapter_to_tub_gap_mm": gap(ad, tub)}
    tub_contents = {k: ph[k] for k in ph if k in ("cell", "pcm", "tape") or k.startswith(("nut", "foam"))}
    if v["pcb_by"] == "lid":
        c["lid_slide_on (PCB rides with the lid)"] = slide_check(lid, tub, tub_contents)
    else:
        moving = dict(tub_contents)
        moving.update({k: ph[k] for k in ("parts_out", "pcb", "washer")})
        c["lid_slide_on (PCB stays in the tub)"] = slide_check(lid, tub, moving)
    c["nut_bosses"] = binfo
    c["screws"] = screw_numbers(v)
    t = TONGUE
    c["front_hook"] = {"tongue_engagement_under_cap_mm": round(CAP_X1 - t["x0"], 2),
                       "tongue_thickness_mm": round(t["y_top"] - t["y0"], 2),
                       "tongue_width_z_mm": round(t["z1"] - t["z0"], 2),
                       "tongue_to_lid_fusion_width_mm": round(t["root_x1"] - LID_X0, 2),
                       "cap_overhang_mm": round(CAP_X1 - CAV["x0"], 2), "cap_thickness_mm": round(Y_OUT - YS, 2),
                       "slide_to_engage_mm": SLIDE, "seam_gap_mm": SEAM,
                       "screw_hole_radial_play_mm (keeps it engaged)": round((SCREW["clear"] - SCREW["d"]) / 2, 2)}
    c["button_flexure"] = hinge_numbers()
    from build123d import RegularPolygon, extrude
    hexwin = Pos(MIC["x"], Y_ARM, MIC["z"]) * Rot(90, 0, 0) * extrude(RegularPolygon(1.9, 6), amount=2.0, both=True)
    slot_only = (prism_xz(slot_outer, YS - 0.05, Y_UP + 0.3) - prism_xz(UP_PTS, YS - 0.1, Y_UP + 0.4)
                 - box(X0 - 1, HINGE_X[0], YS - 1, Y_UP + 1, Z0 - 1, Z1 + 1))
    c["button_flexure"]["slot_to_mic_hex_window_mm"] = gap(slot_only, hexwin)
    c["button_flexure"]["slot_to_chimney_mm"] = gap(slot_only, cyl_y(MIC["x"], MIC["z"], SEAL["chimney_od"] / 2, CHIM_Y0, YS))
    c["button_flexure"]["armour_strip_above_slot_mm"] = round(4.3 - (UP_PTS[0][1] + SLOT_W), 2)
    c["mic_duct"] = mic_duct()
    rear = box(PCB["x1"], CAV["x1"], 9.9, YS, CAV["z0"], CAV["z1"])
    free = vol(rear) - vol(rear & tub) - vol(rear & lid) - vol(rear & ph["pcm"])
    c["service_loop_space_mm3 (behind the PCB, y 9.9..13.4)"] = round(free, 1)
    c["walls_mm"] = {"lid": round(Y_OUT - YS, 2), "tub walls": F.WALL, "cap": round(Y_OUT - YS, 2),
                     "fin over tub: min height": 0.6, "fin gap to tub top": 0.05,
                     "hinge": HINGE_T, "tongue (hook)": round(t["y_top"] - t["y0"], 2),
                     "nut-boss minimum (see nut_bosses)": min(min(b["walls_mm"].values()) for b in binfo),
                     "web/rib": WEB_T, "panel-line floor": 0.6}
    c["mass_g"] = {"tub": round(vol(tub) * RESIN_RHO, 2), "lid": round(vol(lid) * RESIN_RHO, 2)}
    return c


def export(name, tub, lid, ph, folder):
    folder.mkdir(parents=True, exist_ok=True)
    for f in folder.glob("*.st[ep]*"):
        f.unlink()
    files = []
    for k, s in (("tub", tub), ("lid", lid)):
        export_step(s, str(folder / f"{k}.step"))
        export_stl(s, str(folder / f"{k}.stl"), tolerance=0.01, angular_tolerance=0.1)
        files += [f"{k}.step", f"{k}.stl"]
    for k, s in ph.items():
        export_step(s, str(folder / f"ph_{k}.step"))
        files.append(f"ph_{k}.step")
    asm = Compound(children=[tub, lid] + list(ph.values()))
    export_step(asm, str(folder / "assembly.step"))
    files.append("assembly.step")
    return files


INTERFACE_REQUESTS = [
    "BLOCKING (frame.LID_SCREWS + frame.PCM): bosses at x = 60.8 sit over the cell's rear end and the PCM "
    "(y 9.9..13.4), so the 12.5 mm cell can't pass them. The tub would trap the cell. Proposal: PCM folded flat "
    "on the cell's rear top face (placeholder x 57.4..61.4, y 9.75..11.95, z -8..4; MEASURE B4), then "
    "LID_SCREWS = [(64.2, 2.7), (64.2, -5.6)], with bosses at x 62.0..66.7 behind the cell. Lower screw raised "
    "to z -5.6 so its counterbore clears the armour's bottom edge. The circuit-trace groove now ends in the "
    "VBUS screw head.",
    "BLOCKING (task text 'PCB ledge ribs in the tub'): ledges under the PCB's inner-face bands overhang the cell "
    "(10.4 mm gap for a 12.5 mm cell). Proposal: the LID locates the PCB (outer-face ribs, edge webs, rear stops). "
    "Two soft foam strips (about 1.5 mm, closed-cell) on the cell's top face under the bands spring it up "
    "against the lid. The tub keeps only front stops at x < 30.6.",
    "frame.LID_HOOK: implemented as a tongue (x 30.45..31.05, y 12.7..13.35, z -4.85..0.85) under a 0.5 mm "
    "overhang of the tub's front cap, engaged by sliding the lid 0.45 mm forward. This only works because the "
    "PCB rides with the lid. With the PCB fixed in the tub, the slide drags the chimney/washer 0.45 mm across "
    "parts outside MIC_SEAL.keepout_r and sweeps the tongue over x 31.1..31.5 of the outer face.",
    "hw/pod (gen.py/place.py): the button tongue needs the KXT321 at frame.BUTTON with its 3.0 mm side along x. "
    "No PCB parts may sit under the lid's top-band rib at x 31.0..35.8 and 46.6..50.6 (the band already "
    "guarantees this). The draft place.py has Y1/C12 inside the r1.6 mic keepout, so re-place them.",
    "heel.py: the dovetail rail (blade.rail) on the tub's inner face spans x 36..62, y 3.3..4.3, z -5.2..1.2, "
    "so it overlaps the heel region at x 50..62, z -5.2..-4.3. The heel must merge with it or stop at x < 50 there. "
    "Wires to the heel run down the rear wire gap (x 62..66.7, z -3.4..0.5), then under the lower boss "
    "(y 5.1..9.9).",
    "frame.MIC_SEAL: washer_od 3.0 is larger than chimney_od 2.6. It's built as specified: the washer is "
    "stuck to the chimney's flat tip and overhangs it by 0.2. Consider washer_od = 2.6.",
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    armour_full, _paint = armour_and_trace()
    armour_main = armour_full & box(X0 - 1, X1 + 1, Y_OUT - 0.1, Y_ARM, Z0 - 1, Z1 + 3)
    result = {"date": "2026-09-30", "module": "hw/mech/shell.py", "frame": "hw/mech/frame.py",
              "recommended": "proposed", "variants": {}}
    for name in ("proposed", "as_frame"):
        t = time.time()
        v, tub, lid, ph, feats, binfo, slot_outer = build_variant(name, armour_main)
        chk = run_checks(name, v, tub, lid, ph, feats, binfo, slot_outer)
        folder = OUT if name == "proposed" else OUT / "as_frame"
        files = export(name, tub, lid, ph, folder)
        chk["files"] = [str((folder / f).relative_to(REPO)) for f in files]
        chk["build_s"] = round(time.time() - t, 1)
        result["variants"][name] = chk
        if name == "proposed":
            parts = {"tub": tub, "lid": lid}
            parts.update(ph)
            figure(parts, OUT / "shell_sections.png",
                   "Pod shell (proposed): tub + lid, resin; dark = section cut faces")
            figure_slide(parts, OUT / "shell_lid_slide.png")
        print(f"{name}: {chk['build_s']} s", flush=True)
    p, a = result["variants"]["proposed"], result["variants"]["as_frame"]

    def zero(d):
        return all((not isinstance(x, (int, float))) or x < 1e-3 for x in d.values())

    result["verdict"] = {
        "proposed": {
            "zero_overlap_with_contents": zero(p["overlap_mm3 (must be 0)"]),
            "cell_can_be_inserted": p["cell_insertion_corridor"]["passes"],
            "lid_slides_on_clean": p["lid_slide_on (PCB rides with the lid)"]["passes"],
            "status": "USER_REVIEW (needs the PCM/LID_SCREWS interface change)"},
        "as_frame": {
            "zero_overlap_with_contents": zero(a["overlap_mm3 (must be 0)"]),
            "cell_can_be_inserted": a["cell_insertion_corridor"]["passes"],
            "lid_slides_on_clean": a["lid_slide_on (PCB stays in the tub)"]["passes"],
            "status": "BLOCKED"},
    }
    result["interface_requests"] = INTERFACE_REQUESTS
    result["total_s"] = round(time.time() - T0, 1)
    (OUT / "checks.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result["verdict"], indent=2))
    print("total", result["total_s"], "s")


if __name__ == "__main__":
    main()
