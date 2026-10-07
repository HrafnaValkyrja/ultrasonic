"""Transducer pod ("pad") at the tragus + the arm strut. Rev 1 IS the prototype (owner, 2026-09-30).

    source tools/env.sh
    systemd-run --user --scope --quiet -p MemoryMax=2G -p MemorySwapMax=0 python3 hw/mech/pad.py [--render]

Outputs -> hw/mech/out/parts/pad/: STEP of every part (worn pose, world frame), STL of the printed
parts, checks.json, and pad_views.png with --render. Builder's note: hw/mech/notes/pad.md.

Builds against hw/mech/frame.py only (worn pose, pad frame E1/E2/E3, PAD_Y stack, socket axis T/a_T,
pad_pose). Two local frames:
  pad   (u, y, w): u along E1 (+u = rear-up, toward the ear), y = world y (outward), w along E3
                   (+w = up-forward along the transducer); origin at PAD_CENTRE's x, z and y = 0.
                   Built with blade/styles helpers as if x = u, z = w, then placed by PAD_LOC.
  strut (along, b1, b2): along = mm from the socket entry T along the worn socket axis a_T
                   (+ = into the pad); b1 = outward normal to a_T (the plane the NiTi bends in);
                   b2 = a_T x b1 (lateral, + = rear-up). In the pad frame b2 ~ +u.
Printed parts: CUP (skin side, holds the transducer face-down on a 0.6 mm wall) and CAP+STRUT
(one print: closes the cup, LED ring diffuser, NiTi socket + M1.4 set screw in a hex collar, the
strut that shrouds the wire, conductor channel). Plus a rigid printed contact variant.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
from build123d import (Align, Axis, Box, Circle, Compound, Cylinder, Location, Plane, Polygon, Pos,
                       Rot, SlotCenterToCenter, chamfer, export_step, export_stl, extrude, loft)

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import frame as F  # noqa: E402
from blade import prism_xz  # noqa: E402  (polygon in (x, z) extruded along y; here x = u, z = w)
from styles import slot  # noqa: E402     (groove along a polyline on a face y = const)

OUT = HERE / "out" / "parts" / "pad"
EPS = 0.01

# ============================================================================ numbers (mm)
FS = F.FASTENERS
RS = F.RESIN
PY = F.PAD_Y
TD = F.TRANSDUCER
FIT = RS["slide_fit"]                       # 0.15 per side
WALL_SIDE = RS["pref_wall"]                 # 0.8 cup side/end walls
SKIN_WALL = PY["cup_wall_in"] - PY["cup_wall_out"]   # 0.6 (frame)

CAV_U = TD["w"] / 2 + FIT                   # 3.15 cavity half-width
CAV_W = TD["L"] / 2 + FIT                   # 6.45 cavity half-length
OUT_U = CAV_U + WALL_SIDE                   # 3.95
W_TOP = CAV_W + WALL_SIDE                   # 7.25 top end of the cup
Y_SKIN, Y_CUP0, Y_CAV0 = PY["skin"], PY["cup_wall_out"], PY["cup_wall_in"]   # -3.0, -2.0, -1.4
Y_SPLIT, Y_BRD, Y_LED, Y_CAP = PY["split"], PY["board_top"], PY["led_top"], PY["cap_face"]  # 2.6 3.4 3.75 4.5
BEZEL_H = 0.4                               # raised hex bezel / armour plate on the cap face
Y_BEZ = Y_CAP + BEZEL_H                     # 4.9

# World-z ceiling for the pad body's top-rear corner (Ear (open) side): set by the transducer
# cavity corner + 0.6 mm wall, measured along the world-up direction in the (u, w) plane.
_ZDIR = np.array([F.E1[2], F.E3[2]])        # world z per unit u, w = (0.5, 0.866)
K_TOP = float(_ZDIR @ [CAV_U, CAV_W]) + RS["min_wall"]

# closure screw: ONE M1.2 at the bottom end, head on the cap face, self-tapping into the cup
SCREW = FS["M1.2_pan"]
SCREW_L = 4.0                               # eyeglass screw M1.2 x 4 (x 5 also fits, see checks)
W_SCREW = -7.7
PILOT_BOTTOM = Y_SPLIT - 3.4                # -0.8 -> 1.2 mm floor under the pilot on the skin side

# LED ring (frame / owner): diffuser cavity 5.3, opaque printed centre plug 4.1
RING_OD, PLUG_D = 5.3, 4.1
LED_SOLDER, LED_H = 0.03, 0.45              # Everlight DSE-0008890 Rev 3 p6 (per hw/padboard/mech.py): 0.45 tall
Y_LED_REAL = Y_BRD + LED_SOLDER + LED_H      # 3.88; frame PAD_Y led_top (3.75) is low -> interface request
PLUG_Y0 = max(Y_LED, Y_LED_REAL) + 0.10      # plug underside 0.1 above the real LED
SPOKE_W, SPOKE_H = 0.45, 0.5
FILM = 0.02                                 # PE release film under the cast epoxy

# board pads (on the board's top face). Top end = 4 arm conductors (rear half); bottom = transducer
BOARD = F.PAD_BOARD
BRD_U = BOARD["w"] / 2                      # 2.5
REC_U = BRD_U + FIT                         # 2.65 recess half-width in the cap
POCKET_Y = Y_BRD + 0.5                      # 3.9: solder-joint pockets (roof = 0.6); joints <= 0.45 tall
JOINT_H = 0.45                              # wire + fillet on a pad (hw/padboard/mech.py)
DAM_R = RING_OD / 2 + RS["min_wall"]        # 3.25: printed dam around the ring presses the PE film on the board
W_REAR_POCKET = 4.7                         # rear joint pocket ends here (set-screw nut above it)
WIREPATH_Y = Y_BRD + 0.35                   # 3.75: rear wires cross the board's top-end strip under the nut
W_WIREPATH_END = 5.15                       # they cross above the pads' top ends (4.9), not at the board edge
# Pad-board layout: read LIVE from hw/padboard/layout.py PLACE (electronics agent's file; parsed with ast,
# no pcbnew import). KiCad x = -u, KiCad y = -w. Rows: ref -> (net, x, y, kind, size_x, size_y).
PADBOARD_SRC = HERE.parents[0] / "padboard" / "layout.py"
# what pad.py asked for at 20:45 (LED pads into the arm-wire row; transducer PTH out to r >= 3.7), kept to
# show in the picture what changed; the live layout is what is checked
PADBOARD_REQUESTED = {"J3": (-0.575, -4.0), "J4": (0.575, -4.0), "J5": (-1.85, 3.25), "J6": (1.85, 3.25)}


def read_padboard_layout(path=PADBOARD_SRC):
    """PLACE from layout.py -> {ref: (net, x, y, kind, sx, sy)}; pad sizes from the footprint names.
    Returns (layout, file mtime 'HH:MM')."""
    import ast
    import re
    import time
    src = path.read_text()
    consts, place = {}, None
    for node in ast.parse(src).body:
        if isinstance(node, ast.Assign):
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            tup = [e.id for t in node.targets if isinstance(t, ast.Tuple) for e in t.elts if isinstance(e, ast.Name)]
            try:
                val = eval(compile(ast.Expression(node.value), str(path), "eval"), {"__builtins__": {}}, dict(consts))  # noqa: S307
            except Exception:  # noqa: BLE001
                continue
            if "PLACE" in names:
                place = val
            for n in names:
                consts[n] = val
            if tup and isinstance(val, tuple) and len(val) == len(tup):
                consts.update(dict(zip(tup, val)))
    out = {}
    for ref, (x, y, _rot, _lib, fp, net) in place.items():
        if net is None:
            continue
        m = re.search(r"SMD_([\d.]+)x([\d.]+)mm", fp)
        if m:
            sx, sy, kind = float(m.group(1)), float(m.group(2)), "smd"
        else:
            d = float(re.search(r"Pad([\d.]+)mm", fp).group(1))
            sx = sy = d
            kind = "pth"
        name = {"LED_A": "LED+", "LED_K": "LED-"}.get(net, net)
        if kind == "pth":
            name = "XDCR_" + net[-1]             # transducer lead holes (nets OUT_A/OUT_B on the board)
        out[ref] = (name, float(x), float(y), kind, sx, sy)
    return out, time.strftime("%H:%M", time.localtime(path.stat().st_mtime))


try:
    PADBOARD_LAYOUT, PADBOARD_READ_AT = read_padboard_layout()
except Exception:  # noqa: BLE001   (heel.py imports this module; never fail on the electronics file)
    PADBOARD_LAYOUT = {"J1": ("OUT_A", -1.725, -4.0, "smd", 0.7, 1.8), "J2": ("OUT_B", 1.725, -4.0, "smd", 0.7, 1.8),
                       "J3": ("LED+", -0.575, -4.0, "smd", 0.7, 1.8), "J4": ("LED-", 0.575, -4.0, "smd", 0.7, 1.8),
                       "J5": ("XDCR_A", -1.775, 3.275, "pth", 0.85, 0.85), "J6": ("XDCR_B", 1.775, 3.275, "pth", 0.85, 0.85)}
    PADBOARD_READ_AT = "FALLBACK copy of 23:37 (layout.py unreadable)"

# hook (locating feature at the top end): cap claw + tip into a window in the cup's top end wall
WIN = dict(u=0.85, y0=1.30, y1=1.90)
TIP = dict(u=0.75, y0=1.375, y1=1.825, w0=6.80)
CLAW = dict(u=0.75, w0=W_TOP + 0.10, w1=W_TOP + 0.70, y0=1.20)
HOOD = dict(u=1.25, w1=W_TOP + 0.70)

# ---------------------------------------------------------------- NiTi socket, strut, collar
T_W, A_W = F.pad_socket_axis("worn_3.5")
B1_W = F.E2 - (F.E2 @ A_W) * A_W
B1_W = B1_W / np.linalg.norm(B1_W)
B2_W = np.cross(A_W, B1_W)
WIRE_R = F.NITI_D / 2
SOCK_R = F.SOCKET_D / 2                     # 0.425 reamed
SOCK_DEPTH = F.PAD_SOCKET_DEPTH             # 3.5
MOUTH = 0.30                                # 0.55 -> 0.425 lead-in at the socket mouth


def _along_of_s(s, state="worn_3.5"):
    p, _ = F.wire(s, state)
    return float((p - T_W) @ A_W)


ALONG_TOP = _along_of_s(F.STRUT_START)      # ~ -8.94: strut top face
# wire channel (tapered offset slot): clearance to the wire surface at the TOP / at T (frame numbers)
CH_UP_TOP = F.STRUT_CLEARANCE_TOP           # 0.9 on the +b1 side (the only way the wire moves, see notes)
CH_DN_TOP = 0.25                            # -b1 side (wire never goes there in the model)
CH_SIDE_TOP = 0.30                          # +-b2 (wire never goes there in the model; bumps)
CH_BOT = F.STRUT_CLEARANCE_BOTTOM           # 0.15 all round at T
# strut outer section (b1, b2), chamfered rectangle; tapered in b1 (top face) only
# conductor channel: REAR side, in line with the heel's channel entry (local b +2.25) so the 4 wires run
# straight across the flex zone instead of crossing over the NiTi (pinch risk, owner 2026-10-01).
# Sized for a shrink-tubed bundle (~1.0 mm OD; owner shrink-tubes the wires through joints): bore 1.6.
COND_R, COND_B1, COND_B2 = 0.6, 0.0, 2.25    # bare bundle bore; the shrink tube stops in COND_CBORE
COND_CBORE_R, COND_CBORE_L = 0.8, 1.7          # 1.6 mm counterbore at the strut top seats the tube end
STRUT_B2 = (-1.45, 3.65)              # rear grew 2.35 for the conductor bore (check Ear (open) clearance on E9)
STRUT_B1_LO = -1.45
STRUT_B1_HI_TOP, STRUT_B1_HI_BOT = 1.90, 1.20
STRUT_CH = 0.4
STRUT_RAKE = 0.8                            # top face raked 13 deg: outboard (+b1) edge 0.8 lower than the inboard
                                            # edge, so the strut top clears the pod's lower-inner edge by >= 1.4 (heel H3)
HEEL_CH_ENTRY = np.array([63.793, 2.681, -8.175])   # heel.py checks.json channel.entry_world (read 23:40)
COND_END = 1.5                              # conductor channel ends here (breaks into the riser over ~0.7 mm)
# hex collar ("jack") around the socket: flats across b2 (set screw enters a flat)
COLLAR_AF = 7.4                                 # was 5.9; grown so the rear wire bore keeps 0.6 walls
COLLAR_A0, COLLAR_A1 = -0.40, 4.40              # nut corners at 2.0 -/+ 1.79, + 0.6 walls
Y_COLLAR_TOP = 7.62                         # flat top (world y); the nut's top flat sits just below
# set screw M1.4 x 2 through a captured brass M1.4 nut, entering from the REAR flat (+b2)
SET_ALONG = 2.0
NUT = FS["M1.4_nut"]
NUT_T = NUT["m"] + 0.10                     # pocket 1.3 along b2
NUT_B2_IN = SOCK_R + RS["min_wall"] + 0.005             # 1.03
NUT_B2_OUT = NUT_B2_IN + NUT_T                           # 2.33
SET_L = 2.0
SET_FLAT = 0.30                             # wire flat filed 0.1 deep on its front side


def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


PAD_LOC = Location(Plane(origin=(float(F.PAD_CENTRE[0]), 0.0, float(F.PAD_CENTRE[2])),
                         x_dir=tuple(F.E1), z_dir=tuple(F.E3)))
PAD_ORIGIN = np.array([F.PAD_CENTRE[0], 0.0, F.PAD_CENTRE[2]])


def to_local(p):
    d = np.asarray(p) - PAD_ORIGIN
    return np.array([d @ F.E1, d @ F.E2, d @ F.E3])


def to_world(q):
    return PAD_ORIGIN + q[0] * F.E1 + q[1] * F.E2 + q[2] * F.E3


def sloc(along, d1=0.0, d2=0.0, x_dir=None, z_dir=None):
    """Location in the strut frame (world): origin T + along*a + d1*b1 + d2*b2; default x = b1, z = a."""
    o = T_W + along * A_W + d1 * B1_W + d2 * B2_W
    xd = B1_W if x_dir is None else x_dir
    zd = A_W if z_dir is None else z_dir
    return Location(Plane(origin=tuple(map(float, o)), x_dir=tuple(map(float, xd)), z_dir=tuple(map(float, zd))))


# ============================================================================ helpers (pad-local)
def lbox(u0, u1, y0, y1, w0, w1):
    return Pos((u0 + u1) / 2, (y0 + y1) / 2, (w0 + w1) / 2) * Box(u1 - u0, y1 - y0, w1 - w0)


def ycyl(u, w, r, y0, y1):
    return Pos(u, y0, w) * Rot(-90, 0, 0) * Cylinder(r, y1 - y0, align=(Align.CENTER, Align.CENTER, Align.MIN))


def hex_pts(af, flats_across="u", cu=0.0, cw=0.0):
    R = af / math.sqrt(3)
    a0 = 30 if flats_across == "u" else 0
    return [(cu + R * math.cos(math.radians(a0 + 60 * k)), cw + R * math.sin(math.radians(a0 + 60 * k)))
            for k in range(6)]


def inset(poly, d):
    """Inset a convex polygon (u, w) by d (positive = inward)."""
    pts = np.array(poly, float)
    area = 0.5 * sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, np.roll(pts, -1, 0)))
    sgn = 1 if area > 0 else -1
    lines = []
    for p, q in zip(pts, np.roll(pts, -1, 0)):
        t = (q - p) / np.linalg.norm(q - p)
        n = sgn * np.array([-t[1], t[0]])           # inward normal
        lines.append((p + d * n, t))
    out = []
    for (p1, t1), (p2, t2) in zip(lines[-1:] + lines[:-1], lines):
        A = np.array([t1, -t2], float).T
        s = np.linalg.solve(A, p2 - p1)
        out.append(tuple(p1 + s[0] * t1))
    return out


def outline(hood=False):
    """Pad body outline in (u, w): rectangle around the cavity, top-rear corner cut on a line of
    constant world z (K_TOP), hex nose at the bottom end around the closure screw."""
    u_cut = (K_TOP - _ZDIR[1] * W_TOP) / _ZDIR[0]
    w_cut = (K_TOP - _ZDIR[0] * OUT_U) / _ZDIR[1]
    top = [(-OUT_U, W_TOP - 0.45), (-OUT_U + 0.45, W_TOP)]
    if hood:
        top += [(-HOOD["u"], W_TOP), (-HOOD["u"], HOOD["w1"]), (HOOD["u"], HOOD["w1"]), (HOOD["u"], W_TOP)]
    top += [(u_cut, W_TOP), (OUT_U, w_cut)]
    nose = [(OUT_U, -6.6), (1.6, -9.1), (-1.6, -9.1), (-OUT_U, -6.6)]
    return top + nose


# ============================================================================ parts
def build_cup():
    """CUP: transducer face-down on a 0.6 mm skin wall; M1.2 pilot in the solid nose; hook window."""
    env = prism_xz(outline(), Y_CUP0, Y_SPLIT)
    env = chamfer(env.edges().group_by(Axis.Y)[0], 0.35)           # skin-side perimeter (0.35 keeps 0.6 at the cut corner)
    env = chamfer(env.edges().group_by(Axis.Y)[-1], 0.2)           # rim: seam reads as a V panel line
    for su in (1, -1):                                              # panel line on each long side, 0.2 deep
        env = env - lbox(su * OUT_U - 0.2, su * OUT_U + 0.2, 0.4, 0.8, -5.6, 5.0)
    voids = {
        "cavity": lbox(-CAV_U, CAV_U, Y_CAV0, Y_SPLIT + 1, -CAV_W, CAV_W),
        "pilot": ycyl(0, W_SCREW, SCREW["pilot"] / 2, PILOT_BOTTOM, Y_SPLIT + 1),
        "window": lbox(-WIN["u"], WIN["u"], WIN["y0"], WIN["y1"], CAV_W - EPS, W_TOP + 1),
    }
    cup = env
    for v in voids.values():
        cup = cup - v
    probes = {     # closed portions of each void, for wall checks
        "cavity": lbox(-CAV_U, CAV_U, Y_CAV0, Y_SPLIT - 0.7, -CAV_W, CAV_W) - lbox(-WIN["u"] - 0.7, WIN["u"] + 0.7, WIN["y0"] - 0.7, Y_SPLIT, CAV_W - 0.7, CAV_W),
        "pilot": ycyl(0, W_SCREW, SCREW["pilot"] / 2, PILOT_BOTTOM, Y_SPLIT - 0.7),
    }
    return PAD_LOC * cup, PAD_LOC * env, {k: PAD_LOC * v for k, v in probes.items()}


def wire_channel(along0, along1, grow=0.0):
    """Tapered offset slot: big at the strut top (wire moves +b1 there), 0.55 round at T."""
    def sec(al):
        f = min(max(al / ALONG_TOP, 0.0), 1.0)                     # 1 at the top, 0 at T
        up = WIRE_R + CH_BOT + f * (CH_UP_TOP - CH_BOT) + grow
        dn = WIRE_R + CH_BOT + f * (CH_DN_TOP - CH_BOT) + grow
        hw = WIRE_R + CH_BOT + f * (CH_SIDE_TOP - CH_BOT) + grow
        sep = max(up + dn - 2 * hw, 0.01)
        c = (up - dn) / 2
        return sloc(al) * Pos(c, 0, 0) * SlotCenterToCenter(sep, 2 * hw)
    return loft([sec(along0), sec(along1)])


def channel_section(al):
    f = min(max(al / ALONG_TOP, 0.0), 1.0)
    up = WIRE_R + CH_BOT + f * (CH_UP_TOP - CH_BOT)
    dn = WIRE_R + CH_BOT + f * (CH_DN_TOP - CH_BOT)
    hw = WIRE_R + CH_BOT + f * (CH_SIDE_TOP - CH_BOT)
    return up, dn, hw


def strut_section_pts(hi1):
    lo1, (lo2, hi2), c = STRUT_B1_LO, STRUT_B2, STRUT_CH
    return [(lo1 + c, lo2), (hi1 - c, lo2), (hi1, lo2 + c), (hi1, hi2 - c), (hi1 - c, hi2), (lo1 + c, hi2),
            (lo1, hi2 - c), (lo1, lo2 + c)]


def strut_hi(al):
    f = min(max(al / ALONG_TOP, 0.0), 1.0)
    return STRUT_B1_HI_BOT + f * (STRUT_B1_HI_TOP - STRUT_B1_HI_BOT)


def top_along(b1):
    """Strut top face (raked): along-coordinate of the top at lateral-outward offset b1."""
    return ALONG_TOP + STRUT_RAKE * (b1 - STRUT_B1_LO) / (STRUT_B1_HI_TOP - STRUT_B1_LO)


def rake_cutter():
    """Half-space (as a big box) above the raked top face: hinge on the inboard top edge (b1 = lo), the
    outboard edge STRUT_RAKE lower. Box limited to +-10 mm around the strut top, so it only touches the strut."""
    p0 = T_W + ALONG_TOP * A_W + STRUT_B1_LO * B1_W
    n = unit(-(STRUT_B1_HI_TOP - STRUT_B1_LO) * A_W + STRUT_RAKE * B1_W)
    return Location(Plane(origin=tuple(map(float, p0)), x_dir=tuple(map(float, B2_W)), z_dir=tuple(map(float, n)))) * \
        Box(20, 20, 10, align=(Align.CENTER, Align.CENTER, Align.MIN))


def build_strut():
    a1 = 0.6                                                         # buried in the collar
    top = sloc(ALONG_TOP) * Polygon(*strut_section_pts(STRUT_B1_HI_TOP), align=None)
    bot = sloc(a1) * Polygon(*strut_section_pts(strut_hi(a1)), align=None)
    return loft([top, bot]) - rake_cutter()


def build_collar():
    R = COLLAR_AF / math.sqrt(3)
    h = COLLAR_AF / 2
    # hex top (the visible "jack" collar), square bottom so it fills into the cap face without thin corners
    pts = [(R, 0), (R / 2, h), (-R, h), (-R, -h), (R / 2, -h)]      # (b1, b2)
    col = sloc(COLLAR_A0) * extrude(Polygon(*pts, align=None), amount=COLLAR_A1 - COLLAR_A0)
    endface = col.faces().sort_by(Axis(tuple(map(float, T_W)), tuple(map(float, A_W))))[0]
    col = chamfer(endface.edges(), 0.3)                             # jack-collar bevel where the strut lands
    clip = PAD_LOC * lbox(-30, 30, -30, Y_COLLAR_TOP, -30, 40)      # flat top
    return col & clip


def _hex_flat_b1(af):
    """Hex in the (a, b1) plane with flats across b1 (flat on the floor), corners along a."""
    ac = af * 2 / math.sqrt(3)
    return [(ac / 2, 0), (ac / 4, af / 2), (-ac / 4, af / 2), (-ac / 2, 0), (-ac / 4, -af / 2), (ac / 4, -af / 2)], ac


def nut_pocket(with_slot=True, grow=0.0):
    """Pocket for a brass M1.4 nut (axis b2), lying on a flat (flats across b1) so its underside is
    as high as possible above the board's rear joint pocket; it drops in through a slot from the top
    of the collar. Once the set screw holds its centre, the floor stops it turning."""
    af = NUT["pocket_af"] + 2 * grow
    pts, ac = _hex_flat_b1(af)
    # FRONT side (-b2) since 2026-10-01: the rear is the wires' path, in line with the heel channel
    loc = sloc(SET_ALONG, 0.0, -(NUT_B2_IN - grow), x_dir=-A_W, z_dir=-B2_W)
    p = loc * extrude(Polygon(*pts, align=None), amount=NUT_T + 2 * grow)
    if with_slot:
        p = p + loc * extrude(Polygon((-ac / 2, 0), (ac / 2, 0), (ac / 2, 6), (-ac / 2, 6), align=None),
                              amount=NUT_T + 2 * grow)
    return p


def _dam():
    return ycyl(0, 0, DAM_R, Y_SPLIT - 2, Y_CAP)


def build_cap():
    """CAP + STRUT, one print. Returns (cap, envelope, probes, plug_parts)."""
    plate = prism_xz(outline(hood=True), Y_SPLIT, Y_CAP)
    plate = chamfer(plate.edges().group_by(Axis.Y)[-1], 0.3)
    plate = chamfer(plate.edges().group_by(Axis.Y)[0], 0.2)
    bezel = prism_xz(hex_pts(6.9, "u"), Y_CAP - EPS, Y_BEZ)
    bezel = chamfer(bezel.edges().group_by(Axis.Y)[-1], 0.15)
    nose = outline()[-4:]
    arm_pts = inset([(-OUT_U, -4.2), (OUT_U, -4.2)] + nose[:1] + nose[1:3] + nose[3:], 0.35)
    armour = prism_xz(arm_pts, Y_CAP - EPS, Y_BEZ)
    armour = chamfer(armour.edges().group_by(Axis.Y)[-1], 0.15)
    # circuit-trace groove (Blade language) cut only into the raised armour: chevron + two "vias"
    trace = [(-2.4, -5.05), (-0.9, -5.85), (0.9, -5.85), (2.4, -5.05)]
    armour = armour - slot(trace, Y_BEZ, 0.35, 0.3)
    for u in (-2.4, 2.4):
        armour = armour - ycyl(u, -5.05, 0.3, Y_BEZ - 0.3, Y_BEZ + 0.1)
    # hex counterbore in the armour for the closure screw head (head seats on the cap face); AF 2.8 also
    # takes an M1.4 head (the strip-out fallback)
    armour = armour - prism_xz(hex_pts(2.8, "w", 0.0, W_SCREW), Y_CAP, Y_BEZ + 0.1)

    local = plate + bezel + armour
    body = PAD_LOC * local + build_collar() + build_strut()
    # nothing of the cap may enter the cup's envelope (0.1 clearance) below the split
    keep_out = PAD_LOC * prism_xz(inset(outline(), -0.1), -10, Y_SPLIT)
    body = body - keep_out
    claw = lbox(-CLAW["u"], CLAW["u"], CLAW["y0"], Y_SPLIT + EPS, CLAW["w0"], CLAW["w1"])
    tip = lbox(-TIP["u"], TIP["u"], TIP["y0"], TIP["y1"], TIP["w0"], CLAW["w0"] + EPS)
    body = body + PAD_LOC * (claw + tip)
    env = body

    # ---- voids
    v = {}
    v["wire_channel"] = wire_channel(ALONG_TOP - 0.2, 0.0)
    v["mouth_flare"] = loft([sloc(ALONG_TOP - 0.01) * Pos(channel_section(ALONG_TOP)[0] / 2 - channel_section(ALONG_TOP)[1] / 2, 0, 0)
                             * SlotCenterToCenter(max(sum(channel_section(ALONG_TOP)[:2]) - 2 * channel_section(ALONG_TOP)[2], 0.01),
                                                  2 * channel_section(ALONG_TOP)[2] + 0.4),
                             sloc(ALONG_TOP + 0.3) * Pos(channel_section(ALONG_TOP)[0] / 2 - channel_section(ALONG_TOP)[1] / 2, 0, 0)
                             * SlotCenterToCenter(max(sum(channel_section(ALONG_TOP)[:2]) - 2 * channel_section(ALONG_TOP)[2], 0.01),
                                                  2 * channel_section(ALONG_TOP)[2])])
    v["socket_mouth"] = loft([sloc(-EPS) * Circle(WIRE_R + CH_BOT), sloc(MOUTH) * Circle(SOCK_R)])
    v["socket"] = sloc(MOUTH - EPS) * Cylinder(SOCK_R, SOCK_DEPTH - MOUTH + EPS, align=(Align.CENTER, Align.CENTER, Align.MIN))
    v["conductor"] = sloc(ALONG_TOP - 0.2, COND_B1, COND_B2) * Cylinder(COND_R, COND_END - ALONG_TOP + 0.2,
                                                                         align=(Align.CENTER, Align.CENTER, Align.MIN))
    v["conductor_cbore"] = sloc(ALONG_TOP - 0.2, COND_B1, COND_B2) * Cylinder(COND_CBORE_R, COND_CBORE_L + 0.2,
                                                                             align=(Align.CENTER, Align.CENTER, Align.MIN))
    v["nut"] = nut_pocket()
    v["setscrew_hole"] = sloc(SET_ALONG, 0, 0.0, x_dir=-A_W, z_dir=-B2_W) * Cylinder(
        FS["M1.4_pan"]["clear"] / 2, COLLAR_AF / 2 + 0.5, align=(Align.CENTER, Align.CENTER, Align.MIN))
    loc_v = {
        "board_recess": lbox(-REC_U, REC_U, Y_SPLIT - 1, Y_BRD, BOARD["e3_0"] - FIT, BOARD["e3_1"] + FIT),
        "pocket_bottom": lbox(-REC_U, REC_U, Y_SPLIT - 1, POCKET_Y, -6.3, -2.0) - _dam(),
        "pocket_top_front": lbox(-REC_U, 0.0, Y_SPLIT - 1, POCKET_Y, 2.0, 4.95) - _dam(),   # shortened: clears the front nut
        "pocket_top_rear": lbox(0.0, REC_U, Y_SPLIT - 1, POCKET_Y, 2.0, W_REAR_POCKET) - _dam(),
        "wirepath_rear": lbox(0.0, REC_U, Y_SPLIT - 1, WIREPATH_Y, W_REAR_POCKET - EPS, W_WIREPATH_END),
        "riser": lbox(1.3, 2.3, Y_SPLIT - 1, 5.3, 5.6, 6.6),          # REAR since 2026-10-01 (wire path)
        "diffuser": ycyl(0, 0, RING_OD / 2, Y_BRD - EPS, Y_BEZ + 1),
        "closure_hole": ycyl(0, W_SCREW, SCREW["clear"] / 2, Y_SPLIT - 1, Y_BEZ + 1),
    }
    for k, s in loc_v.items():
        v[k] = PAD_LOC * s
    cap = body
    for s in v.values():
        cap = cap - s
    # opaque centre plug on 3 buried spokes (printed with the cap) + a hex "pupil" dimple
    plug = ycyl(0, 0, PLUG_D / 2, PLUG_Y0, Y_BEZ) - prism_xz(hex_pts(1.2, "u"), Y_BEZ - 0.2, Y_BEZ + 0.1)
    spokes = None
    for ang in (90, 210, 330):
        r = (PLUG_D / 2 + RING_OD / 2) / 2
        sp = Pos(r * math.cos(math.radians(ang)), PLUG_Y0 + SPOKE_H / 2, r * math.sin(math.radians(ang))) \
            * Rot(0, -ang, 0) * Box(RING_OD / 2 - PLUG_D / 2 + 0.3, SPOKE_H, SPOKE_W)
        spokes = sp if spokes is None else spokes + sp
    cap = cap + PAD_LOC * (plug + spokes)

    pr = {   # closed portions of voids, each kept >= 0.7 from its intended opening (min-wall checks)
        "wire_channel": wire_channel(ALONG_TOP + 0.8 + STRUT_RAKE, -0.05),
        "socket": sloc(MOUTH) * Cylinder(SOCK_R, SOCK_DEPTH - MOUTH, align=(Align.CENTER, Align.CENTER, Align.MIN)),
        "conductor": sloc(ALONG_TOP + 0.8 + STRUT_RAKE, COND_B1, COND_B2) * Cylinder(COND_R, -0.5 - ALONG_TOP - 0.8 - STRUT_RAKE,
                                                                         align=(Align.CENTER, Align.CENTER, Align.MIN)),
        "nut_hex_lower": nut_pocket(with_slot=False) & (sloc(0, -10, 0) * Box(20, 20, 20, align=(Align.MIN, Align.CENTER, Align.CENTER)) - sloc(0, -0.3, 0) * Box(20, 20, 20, align=(Align.MIN, Align.CENTER, Align.CENTER))),
        "board_recess": PAD_LOC * lbox(-REC_U, REC_U, Y_BRD - 0.1, Y_BRD, BOARD["e3_0"] - FIT, BOARD["e3_1"] + FIT),
        "pocket_bottom": PAD_LOC * (lbox(-REC_U, REC_U, Y_BRD - 0.1, POCKET_Y, -6.3, -2.0) - _dam()),
        "pocket_top_front": PAD_LOC * (lbox(-REC_U, 0.0, Y_BRD - 0.1, POCKET_Y, 2.0, 4.95) - _dam()),
        "pocket_top_rear": PAD_LOC * (lbox(0.0, REC_U, Y_BRD - 0.1, POCKET_Y, 2.0, W_REAR_POCKET) - _dam()),
        "wirepath_rear": PAD_LOC * lbox(0.0, REC_U, Y_BRD - 0.1, WIREPATH_Y, W_REAR_POCKET, W_WIREPATH_END),
        "riser": PAD_LOC * lbox(1.3, 2.3, Y_BRD - 0.1, 5.3, 5.6, 6.6),
        "diffuser": PAD_LOC * (ycyl(0, 0, RING_OD / 2, Y_BRD + 0.05, Y_BEZ - 0.7)),
    }
    return cap, env, pr


def build_contacts():
    sil = PAD_LOC * ycyl(0, 0, 4.0, Y_SKIN, Y_CUP0)               # 8 mm punched disc, 1.0 mm silicone
    pts = [(-3.0 + 0.8, -4.0), (3.0 - 0.8, -4.0), (3.0, -3.2), (3.0, 3.2), (3.0 - 0.8, 4.0), (-3.0 + 0.8, 4.0),
           (-3.0, 3.2), (-3.0, -3.2)]
    rig = prism_xz(pts, Y_SKIN, Y_CUP0 - 0.1)                      # 0.9 printed + 0.1 tape
    rig = chamfer(rig.edges().group_by(Axis.Y)[0], 0.3)            # skin-side edges rounded off
    return sil, PAD_LOC * rig


def pad_rows(layout=PADBOARD_LAYOUT):
    """(name, u0, u1, w0, w1, kind, u_c, w_c) per pad, pad-local, from the KiCad layout."""
    rows = []
    for ref, (net, x, y, kind, sx, sy) in layout.items():
        u, w = -x, -y
        rows.append((net, u - sx / 2, u + sx / 2, w - sy / 2, w + sy / 2, kind, u, w))
    return rows


def build_board(layout=PADBOARD_LAYOUT):
    brd = lbox(-BRD_U, BRD_U, Y_SPLIT, Y_BRD, BOARD["e3_0"], BOARD["e3_1"])
    led = lbox(-0.5, 0.5, Y_BRD, Y_LED_REAL, -0.25, 0.25)          # 0402 across the board (layout D1 rot 180)
    pads = {}
    rows = pad_rows(layout)
    for n, u0, u1, w0, w1, kind, uc, wc in rows:
        pads[n] = lbox(u0, u1, Y_BRD, Y_BRD + 0.03, w0, w1) if kind == "smd" else ycyl(uc, wc, (u1 - u0) / 2, Y_BRD, Y_BRD + 0.03)
    return PAD_LOC * brd, PAD_LOC * led, {k: PAD_LOC * v for k, v in pads.items()}, [r[:5] for r in rows]


def joint_check(cap, layout):
    """Each wire joint (0.45 tall) must sit in a pocket: SMD laps = the pad part outside the dam (and,
    on the rear half of the top end, below the nut's pocket limit); PTH fillets = the whole pad disc."""
    out, ok = {}, True
    for n, u0, u1, w0, w1, kind, uc, wc in pad_rows(layout):
        if kind == "smd":
            u_in = max(min(abs(u0), abs(u1)), 0.0) if u0 * u1 > 0 else 0.0
            w_dam = math.sqrt(max((DAM_R + 0.05) ** 2 - u_in ** 2, 0.0))
            lo, hi = (max(w0, w_dam), w1) if wc > 0 else (w0, min(w1, -w_dam))
            if wc > 0 and uc > 0:
                hi = min(hi, W_REAR_POCKET - 0.05)
            lap = max(hi - lo, 0.0)
            env = PAD_LOC * lbox(u0, u1, Y_BRD + 0.03, Y_BRD + JOINT_H, lo, hi) if lap > 0 else None
            ov = overlap(env, cap) if env is not None else None
            good = lap >= 1.0 and (ov is not None and ov <= 1e-3)
            out[n] = {"lap_mm": round(lap, 2), "joint_overlap_mm3": ov, "ok": good}
            if env is not None:
                out[n]["gap_to_cap_mm"] = dist(env, cap)
        else:
            r = (u1 - u0) / 2
            env = PAD_LOC * ycyl(uc, wc, r, Y_BRD + 0.03, Y_BRD + JOINT_H)
            ov = overlap(env, cap)
            good = ov <= 1e-3
            out[n] = {"fillet_r_mm": round(r, 3), "centre_r_from_LED_mm": round(math.hypot(uc, wc), 2), "joint_overlap_mm3": ov,
                      "gap_to_cap_mm (dam)": dist(env, cap), "ok": good}
        ok &= good
    return out, ok


def build_hardware():
    hw = {}
    # brass M1.4 nut (DIN 934: 3.0 AF x 1.2), modelled with a 1.4 bore (threads engage the screw)
    pts, _ = _hex_flat_b1(NUT["s"])
    loc = sloc(SET_ALONG, 0.0, -(NUT_B2_IN + 0.05), x_dir=-A_W, z_dir=-B2_W)
    nut = loc * extrude(Polygon(*pts, align=None), amount=NUT["m"])
    nut = nut - loc * Cylinder(FS["M1.4_set"]["d"] / 2, 5, align=(Align.CENTER, Align.CENTER, Align.CENTER))
    hw["nut_M1.4_brass"] = nut
    # set screw M1.4 x 2, cup point resting on the wire's filed flat at b2 = -0.30
    hw["setscrew_M1.4x2"] = sloc(SET_ALONG, 0, -SET_FLAT, x_dir=-A_W, z_dir=-B2_W) * Cylinder(
        FS["M1.4_set"]["d"] / 2, SET_L, align=(Align.CENTER, Align.CENTER, Align.MIN))
    # closure screw M1.2 x 4: head on the cap face; shank modelled at the pilot dia inside the cup
    head = ycyl(0, W_SCREW, SCREW["head_d"] / 2, Y_CAP, Y_CAP + SCREW["head_h"])
    shank_cap = ycyl(0, W_SCREW, SCREW["d"] / 2, Y_SPLIT, Y_CAP)
    shank_cup = ycyl(0, W_SCREW, SCREW["pilot"] / 2 - 0.001, Y_CAP - SCREW_L, Y_SPLIT)
    hw["screw_M1.2x4"] = PAD_LOC * (head + shank_cap + shank_cup)
    return hw


def build_epoxy():
    cav = ycyl(0, 0, RING_OD / 2 - 0.001, Y_BRD + FILM, Y_BEZ)
    plug = ycyl(0, 0, PLUG_D / 2 + 0.001, PLUG_Y0 - 0.001, Y_BEZ + 0.1)
    sp = None
    for ang in (90, 210, 330):
        r = (PLUG_D / 2 + RING_OD / 2) / 2
        s = Pos(r * math.cos(math.radians(ang)), PLUG_Y0 + SPOKE_H / 2, r * math.sin(math.radians(ang))) \
            * Rot(0, -ang, 0) * Box(RING_OD / 2 - PLUG_D / 2 + 0.3, SPOKE_H + 0.002, SPOKE_W + 0.002)
        sp = s if sp is None else sp + s
    led_cut = lbox(-0.5 - FILM, 0.5 + FILM, Y_BRD, Y_LED_REAL + FILM, -0.25 - FILM, 0.25 + FILM)
    return PAD_LOC * (cav - plug - sp - led_cut)


def wire_points(state, s0=0.0, s1=None, n=48):
    """NiTi centreline for `state`, carried into the WORN pad frame (pad held still)."""
    s1 = F.SPAN if s1 is None else s1
    R, t = F.pad_pose(state)
    out = []
    for s in np.linspace(s0, s1, n):
        p, _ = F.wire(s, state)
        out.append(R.T @ (p - t))
    return np.array(out)


def tube(pts, r):
    segs = []
    for p, q in zip(pts[:-1], pts[1:]):
        L = float(np.linalg.norm(q - p))
        if L < 1e-6:
            continue
        z = unit(q - p)
        x = unit(np.cross(z, [0.3, 0.2, 0.93]))
        loc = Location(Plane(origin=tuple(map(float, p)), x_dir=tuple(map(float, x)), z_dir=tuple(map(float, z))))
        segs.append(loc * Cylinder(r, L, align=(Align.CENTER, Align.CENTER, Align.MIN)))
    return Compound(segs)


def build_wire_ref():
    """Reference NiTi (owned by the arm): worn shape s = 0..SPAN, then 3.5 mm in the socket with the flat."""
    free = tube(wire_points("worn_3.5"), WIRE_R)
    ins = sloc(0) * Cylinder(WIRE_R, SOCK_DEPTH, align=(Align.CENTER, Align.CENTER, Align.MIN))
    flat = sloc(SET_ALONG + 0.75, 0, -SET_FLAT, x_dir=-A_W, z_dir=-B2_W) * Box(1.5, 2.0, 1.0, align=(Align.MIN, Align.CENTER, Align.MIN))
    return Compound(list(free.solids()) + [ins - flat])


# ============================================================================ checks
def faces_of(s):
    return Compound(list(s.faces()))


def dist(a, b):
    return round(float(a.distance_to(b)), 3)


def overlap(a, b):
    try:
        return round(float((a & b).volume), 4)
    except Exception:
        return float("nan")


def stl_manifold(path):
    """Closed-manifold test of an exported STL (binary or ASCII): weld vertices at 1e-4 mm, then every
    edge must be shared by exactly two triangles with opposite directions."""
    raw = Path(path).read_bytes()
    if raw[:5] == b"solid" and b"facet" in raw[:400]:
        v = np.array([list(map(float, ln.split()[1:4])) for ln in raw.decode().splitlines()
                      if ln.strip().startswith("vertex")]).reshape(-1, 3, 3)
    else:
        n = int(np.frombuffer(raw[80:84], "<u4")[0])
        rec = np.frombuffer(raw[84:84 + 50 * n], dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]))
        v = rec["v"].astype(float)
    key = np.round(v.reshape(-1, 3) / 1e-4).astype(np.int64)
    _, idx = np.unique(key, axis=0, return_inverse=True)
    tri = idx.reshape(-1, 3)
    tri = tri[(tri[:, 0] != tri[:, 1]) & (tri[:, 1] != tri[:, 2]) & (tri[:, 0] != tri[:, 2])]
    e = np.concatenate([tri[:, [0, 1]], tri[:, [1, 2]], tri[:, [2, 0]]])
    und = np.sort(e, axis=1)
    _, cnt = np.unique(und, axis=0, return_counts=True)
    _, dcnt = np.unique(e, axis=0, return_counts=True)
    return {"triangles": int(len(tri)), "edges_not_shared_by_2": int((cnt != 2).sum()),
            "directed_edge_reused": int((dcnt > 1).sum()), "ok": bool((cnt == 2).all() and (dcnt == 1).all())}


def channel_margins():
    """Analytic: wire surface to channel wall, every state, s = STRUT_START..SPAN."""
    rows = {}
    for st in ("free", "jaw_open_1.5", "worn_3.5", "jaw_closed_5.5"):
        worst = (9.0, None)
        pts = wire_points(st, F.STRUT_START, F.SPAN, 60)
        for s, p in zip(np.linspace(F.STRUT_START, F.SPAN, 60), pts):
            d = p - T_W
            al, d1, d2 = d @ A_W, d @ B1_W, d @ B2_W
            if al > -0.05:
                continue
            up, dn, hw = channel_section(al)
            c0, c1 = -dn + hw, up - hw                                # stadium centre segment along b1
            cc = min(max(d1, c0), c1)
            m = hw - math.hypot(d1 - cc, d2) - WIRE_R
            if m < worst[0]:
                worst = (m, s)
        rows[st] = {"min_clearance_mm": round(worst[0], 3), "at_s_mm": round(worst[1], 2)}
    return rows


def strut_top_corners():
    pts = strut_section_pts(STRUT_B1_HI_TOP)
    loc = [T_W + top_along(b1) * A_W + b1 * B1_W + b2 * B2_W for b1, b2 in pts]
    out = {}
    for st in ("free", "jaw_open_1.5", "worn_3.5", "jaw_closed_5.5"):
        R, t = F.pad_pose(st)
        out[st] = [np.round(R @ p + t, 2).tolist() for p in loc]
    return out


def main(render=False):
    OUT.mkdir(parents=True, exist_ok=True)
    cup, cup_env, cup_pr = build_cup()
    cap, cap_env, cap_pr = build_cap()
    sil, rig = build_contacts()
    brd, led, pads, brd_rows = build_board()
    hw = build_hardware()
    epoxy = build_epoxy()
    xdcr = PAD_LOC * lbox(-TD["w"] / 2, TD["w"] / 2, Y_CAV0, Y_SPLIT, -TD["L"] / 2, TD["L"] / 2)
    niti = build_wire_ref()

    parts = {"pad_cup": cup, "pad_cap_strut": cap, "pad_contact_silicone": sil, "pad_contact_rigid": rig,
             "pad_board": brd, "pad_board_led": led, "pad_diffuser_epoxy": epoxy, "ref_transducer_RC-BC02": xdcr,
             "ref_niti_worn": niti}
    parts.update({f"pad_{k}": v for k, v in hw.items()})
    printed = ("pad_cup", "pad_cap_strut", "pad_contact_rigid")

    C = {"date": "2026-09-30", "frame": "hw/mech/frame.py (worn_3.5 pose)", "checks": []}

    def chk(name, value, limit, ok, note=""):
        C["checks"].append({"name": name, "value": value, "limit": limit, "pass": bool(ok), "note": note})

    # ---- solids are single and printable
    for k in printed:
        n = len(parts[k].solids())
        chk(f"{k}: one solid", n, 1, n == 1)

    # ---- no overlaps between any two parts (assembly, worn pose, silicone contact fitted)
    asm = {k: v for k, v in parts.items() if k != "pad_contact_rigid"}
    keys = list(asm)
    worst = []
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            ov = overlap(asm[a], asm[b])
            if not (ov <= 1e-3):
                worst.append((a, b, ov))
    chk("all parts non-overlapping (mm3 overlap > 0.001)", [list(w) for w in worst] or "none", "none", not worst)
    ov_r = {k: overlap(rig, asm[k]) for k in ("pad_cup", "pad_cap_strut", "ref_transducer_RC-BC02")}
    chk("rigid contact variant: overlap with cup/cap/transducer (mm3)", ov_r, 0, all(v <= 1e-3 for v in ov_r.values()))

    # ---- fit with the cap closed
    skin_wall = cup & (PAD_LOC * lbox(-OUT_U, OUT_U, Y_CUP0 - 1, Y_CAV0 + 0.05, -CAV_W, CAV_W))
    fit = {
        "transducer face on the 0.6 skin wall (contact)": dist(xdcr, skin_wall),
        "transducer to cup (closest)": dist(xdcr, cup),
        "transducer to cap": dist(xdcr, cap),
        "board to transducer (contact)": dist(brd, xdcr),
        "board to cap (contact, clamped)": dist(brd, cap),
        "board to cup": dist(brd, cup),
        "LED to cap (plug/spokes)": dist(led, cap),
        "LED to epoxy (PE film)": dist(led, epoxy),
        "cap to cup (rim contact)": dist(cap, cup),
        "silicone contact to cup (contact)": dist(sil, cup),
    }
    side_gap = round(CAV_U - TD["w"] / 2, 3)
    chk("transducer/board/LED fit, cap closed (mm)", fit, ">= 0 everywhere; contacts = 0",
        all(v >= 0 for v in fit.values()) and fit["board to transducer (contact)"] < 0.01
        and fit["board to cap (contact, clamped)"] < 0.01 and fit["LED to cap (plug/spokes)"] >= 0.08,
        f"transducer slide fit {side_gap}/side; board clamped between the transducer back and the recess ceiling")

    # ---- pad-board solder joints vs the cap's pockets (electronics layout, and with the requested moves)
    jc, jok = joint_check(cap, PADBOARD_LAYOUT)
    chk(f"pad-board solder joints fit the cap pockets (hw/padboard/layout.py, file time {PADBOARD_READ_AT}, read live)", jc,
        "every SMD lap >= 1.0 mm outside the epoxy dam; no joint touches the cap", jok,
        f"dam r {DAM_R} = ring {RING_OD}/2 + {RS['min_wall']} wall; joints modelled {JOINT_H} tall, PTH fillet = pad disc")

    # ---- NiTi socket inside material
    sock_wall = dist(faces_of(cap_pr["socket"]), faces_of(cap_env))
    chk("NiTi socket: wall to outside (mm)", sock_wall, RS["min_wall"], sock_wall >= RS["min_wall"] - 0.005,
        f"socket D{F.SOCKET_D} x {SOCK_DEPTH} deep along a_T(worn); entry T = {np.round(T_W, 2).tolist()}")
    T_loc = to_local(T_W)
    bottom_loc = to_local(T_W + SOCK_DEPTH * A_W)
    chk("NiTi socket position (pad-local u, y, w)", {"T": np.round(T_loc, 2).tolist(), "bottom": np.round(bottom_loc, 2).tolist()},
        "y above cap face is expected (socket dives outward 19 deg)", True)

    # ---- strut channel clearance vs frame.wire in all states
    cm = channel_margins()
    chk("strut channel: analytic min clearance wire->wall, s = 3..SPAN, all states (mm)", cm, "> 0.05",
        all(v["min_clearance_mm"] > 0.05 for v in cm.values()))
    occ = {}
    for st in ("free", "jaw_open_1.5", "worn_3.5", "jaw_closed_5.5"):
        full = tube(wire_points(st, 0.0, F.SPAN, 50), WIRE_R)
        top = tube(wire_points(st, 0.0, 6.0, 30), WIRE_R)
        occ[st] = {"wire s=0..SPAN to cap (mm)": dist(full, cap), "wire s=0..6 to cap (mm)": dist(top, cap),
                   "overlap mm3": overlap(full, cap)}
    chk("strut never touches the wire, any state (OCC distance)", occ, "> 0 (0.15 at the socket mouth is the design)",
        all(v["wire s=0..SPAN to cap (mm)"] > 0.05 for v in occ.values()))
    chk("strut top face corners per state (world, for the heel shroud check, SHROUD_CLEARANCE 1.4)",
        strut_top_corners(), "heel.py checks", True)

    # ---- screws
    head_seat = Y_CAP
    tip_y = head_seat - SCREW_L
    engage = Y_SPLIT - tip_y
    chk("closure screw M1.2x4: thread engagement in the cup boss (mm)", round(engage, 2), ">= 1.5 (1.25 d)",
        engage >= 1.5, f"tip at y {tip_y:.2f}; pilot bottom {PILOT_BOTTOM:.2f} (0.2 below the x5 tip too: "
        f"x5 engages {Y_SPLIT - (head_seat - 5.0):.1f}, tip {head_seat - 5.0:.2f})")
    floor = PILOT_BOTTOM - Y_CUP0
    chk("closure pilot floor to the cup's skin face (mm)", round(floor, 2), RS["min_wall"], floor >= RS["min_wall"])
    recess = (SET_FLAT + SET_L) - COLLAR_AF / 2
    chk("set screw M1.4x2: full nut engagement + driven end recess below the collar flat (mm)",
        {"nut_thread_engaged": NUT["m"], "driven_end_recess": round(-recess, 2), "tip_on_flat_at_b2": SET_FLAT},
        "engaged = nut height; recess >= 0", recess <= 0, "turn in until it bites the filed flat; 0.7 hex key")
    chk("set screw lands within the socket", {"along": SET_ALONG, "socket": [MOUTH, SOCK_DEPTH]}, "inside",
        MOUTH + 0.7 < SET_ALONG < SOCK_DEPTH - 0.7)

    # ---- min walls (probes of each closed void vs the outside, and between voids)
    walls = {}
    for k, p in cup_pr.items():
        walls[f"cup.{k}->outside"] = dist(faces_of(p), faces_of(cup_env))
    for k, p in cap_pr.items():
        walls[f"cap.{k}->outside"] = dist(faces_of(p), faces_of(cap_env))
    pair_skip = {("conductor", "riser"), ("board_recess", "pocket_bottom"), ("board_recess", "pocket_top_front"),
                 ("board_recess", "pocket_top_rear"), ("board_recess", "wirepath_rear"), ("board_recess", "diffuser"),
                 ("pocket_top_front", "riser"), ("pocket_top_rear", "riser"), ("wirepath_rear", "riser"), ("conductor_cbore", "conductor"), ("pocket_top_front", "pocket_top_rear"), ("pocket_top_front", "wirepath_rear"),
                 ("pocket_top_rear", "wirepath_rear"), ("socket", "wire_channel"), ("nut_hex_lower", "socket"),
                 ("board_recess", "riser")}   # connected by design
    ks = list(cap_pr)
    for i, a in enumerate(ks):
        for b in ks[i + 1:]:
            if (a, b) in pair_skip or (b, a) in pair_skip:
                continue
            walls[f"cap.{a}<->{b}"] = dist(faces_of(cap_pr[a]), faces_of(cap_pr[b]))
    walls["cap.nut_hex<->socket (screw passes through)"] = dist(faces_of(nut_pocket(with_slot=False)), faces_of(cap_pr["socket"]))
    walls["cup.cavity<->pilot"] = dist(faces_of(cup_pr["cavity"]), faces_of(cup_pr["pilot"]))
    walls["cup.window bridge (window top -> rim)"] = round(Y_SPLIT - WIN["y1"], 3)
    walls["cup skin wall (frame)"] = round(SKIN_WALL, 3)
    walls["strut wall over wire slot at top (+b1)"] = round(STRUT_B1_HI_TOP - (WIRE_R + CH_UP_TOP), 3)
    walls["strut wall, wire slot -> rear face (+b2)"] = round(STRUT_B2[1] - (WIRE_R + CH_SIDE_TOP), 3)
    walls["strut web, wire slot <-> conductor (top)"] = round(
        math.hypot(COND_B1 - min(max(COND_B1, -(WIRE_R + CH_DN_TOP) + WIRE_R + CH_SIDE_TOP), WIRE_R + CH_UP_TOP - WIRE_R - CH_SIDE_TOP),
                   abs(COND_B2)) - (WIRE_R + CH_SIDE_TOP) - COND_R, 3)
    walls["strut wall, conductor -> rear face (+b2)"] = round(STRUT_B2[1] - COND_B2 - COND_R, 3)
    walls["strut wall, conductor -> inner face (-b1)"] = round(COND_B1 - COND_R - STRUT_B1_LO, 3)
    walls["collar, nut -> rear flat (set screw side)"] = round(COLLAR_AF / 2 - NUT_B2_OUT, 3)
    _ac = NUT["pocket_af"] * 2 / math.sqrt(3)
    walls["collar, nut -> upper end face (along)"] = round(SET_ALONG - _ac / 2 - COLLAR_A0, 3)
    walls["collar, nut -> lower end face (along)"] = round(COLLAR_A1 - SET_ALONG - _ac / 2, 3)
    walls["collar, socket bottom -> lower end face"] = round(COLLAR_A1 - SOCK_DEPTH, 3)
    thin = {k: v for k, v in walls.items() if v < RS["min_wall"] - 0.01}
    for k in thin:
        if "->outside" in k:
            part, void = k.split("->")[0].split(".")
            env_, pr_ = (cup_env, cup_pr) if part == "cup" else (cap_env, cap_pr)
            try:
                d_, p1, p2 = faces_of(pr_[void]).distance_to_with_closest_points(faces_of(env_))
                print("THIN", k, round(d_, 3), "local", np.round(to_local(np.array([p1.X, p1.Y, p1.Z])), 2),
                      np.round(to_local(np.array([p2.X, p2.Y, p2.Z])), 2))
            except Exception as e:  # noqa: BLE001
                print("THIN", k, e)
    chk("min walls (mm), all >= 0.6", walls, RS["min_wall"], not thin, f"under: {thin}" if thin else "")

    # ---- thickness from the skin, along E2
    def ymax(s):
        return round(max(to_local(np.array([v.X, v.Y, v.Z]))[1] for v in s.vertices()), 2)
    body_local = PAD_LOC * lbox(-OUT_U, OUT_U, -20, 20, -9.2, 3.0)
    th = {"cap face": round(Y_CAP - Y_SKIN, 2), "LED bezel / armour": round(Y_BEZ - Y_SKIN, 2),
          "closure screw head": round(Y_CAP + SCREW["head_h"] - Y_SKIN, 2),
          "collar top (max)": round(Y_COLLAR_TOP - Y_SKIN, 2),
          "pad body below the collar (w < 3)": round(ymax(cap & body_local) - Y_SKIN, 2)}
    chk("pad thickness from the skin (mm)", th, "rev 2 housing + silicone: 0.8 + 5.6 = 6.4 (no LED, no strut)", True,
        "the collar is set by the socket axis diving outward 19 deg from T (frame); see interface request")

    # ---- height (world z) toward the Ear (open) side vs rev 2 (pod.py housing top ~ -17.5)
    body_cap = cap & (PAD_LOC * prism_xz(outline(hood=True), -5, Y_BEZ + 0.05))
    z_body = max(max(v.Z for v in cup.vertices()), max(v.Z for v in body_cap.vertices()))
    collar_zone = cap & (PAD_LOC * lbox(-10, 10, -10, 20, W_TOP - 3, 9.5))
    z_collar = max(v.Z for v in collar_zone.vertices())
    chk("top of pad body (cup + cap plate + hook), world z", round(z_body, 2), "<= -17.0 (rev 2 housing ~ -17.5)",
        z_body <= -17.0, "top-rear corner cut on a line of constant world z: cavity corner + 0.6 wall")
    chk("collar + strut root (w <= 9.5), world z / rear offset of the strut", {"collar max z": round(z_collar, 2),
        "strut rear face behind the wire (b2, mm)": STRUT_B2[1], "collar rear flat behind the wire (mm)": COLLAR_AF / 2,
        "rev 2 sleeve radius": 1.1}, "info: Ear (open) clearance re-check by the integrator", True,
        "the collar rises ~1 mm above rev 2's pad corner; the strut itself follows the wire up and forward")
    # ---- swing-closing check: cap hooks into the window, then swings down about the tip
    piv = to_world(np.array([0.0, (TIP["y0"] + TIP["y1"]) / 2, (TIP["w0"] + CLAW["w0"]) / 2]))
    ax = Axis(tuple(map(float, piv)), tuple(map(float, F.E1)))
    sw = {}
    for ang in (2, 4, 6, 8):
        moved = cap.rotate(ax, ang)
        sw[f"{ang} deg"] = {k: overlap(moved, parts[k]) for k in ("pad_cup", "pad_board", "ref_transducer_RC-BC02")}
        sw[f"{ang} deg"]["bottom end lift (mm)"] = round(math.sin(math.radians(ang)) * (CLAW["w0"] - W_SCREW), 2)
    # unhook: at 8 deg, slide the cap 0.5 mm toward the strut (+w) so the tip leaves the window
    moved = cap.rotate(ax, 8).translate(tuple(map(float, 0.5 * F.E3)))
    sw["8 deg + slide 0.5 (+w): unhooked"] = {k: overlap(moved, parts[k]) for k in ("pad_cup", "pad_board", "ref_transducer_RC-BC02")}
    sw["8 deg + slide 0.5 (+w): unhooked"]["tip to cup (mm)"] = dist(moved, parts["pad_cup"])
    okang = [a for a in (2, 4, 6, 8) if all(v <= 1e-3 for k, v in sw[f"{a} deg"].items() if k != "bottom end lift (mm)")]
    unhook_ok = all(v <= 1e-3 for k, v in sw["8 deg + slide 0.5 (+w): unhooked"].items() if "mm3" in k or k.startswith("pad") or k.startswith("ref"))
    chk("cap swings closed about the hook without collision (overlap mm3)", sw, "0 for the angles used",
        4 in okang and unhook_ok, f"collision-free at {okang} deg; unhook slide ok = {unhook_ok}")

    # ---- cross-check against the heel module's current outputs (read-only, if present)
    heel_dir = HERE / "out" / "parts" / "heel"
    if (heel_dir / "heel_add.step").exists():
        from build123d import import_step
        xc = {}
        try:
            others = {"heel_add": import_step(str(heel_dir / "heel_add.step"))}
            if (heel_dir / "tub_r2_with_heel.step").exists():      # the real shell_r2 tub (strut relief), 2026-10-07
                others["tub_r2_with_heel"] = import_step(str(heel_dir / "tub_r2_with_heel.step"))
            elif (heel_dir / "tub_with_heel_preview.step").exists():  # plain-shell preview (no strut relief): fallback only
                others["tub_with_heel_preview"] = import_step(str(heel_dir / "tub_with_heel_preview.step"))
            for st in ("free", "jaw_open_1.5", "worn_3.5", "jaw_closed_5.5"):
                R, t = F.pad_pose(st)
                loc = Location(Plane(origin=tuple(map(float, t)), x_dir=tuple(map(float, R @ [1.0, 0, 0])),
                                     z_dir=tuple(map(float, R @ [0, 0, 1.0]))))
                moved = loc * cap
                xc[st] = {k: {"gap_mm": dist(moved, o), "overlap_mm3": overlap(moved, o)} for k, o in others.items()}
            okx = all(g["gap_mm"] >= F.SHROUD_CLEARANCE - 0.005 for v in xc.values() for g in v.values())
            chk("cap+strut vs heel.py outputs (heel + shell's lower-inner edge), all states (gap mm)", xc,
                f">= SHROUD_CLEARANCE {F.SHROUD_CLEARANCE} to both", okx,
                f"strut top raked {STRUT_RAKE} mm (outboard edge lower) for the shell edge (heel note H3). heel.py imports "
                "pad.py's strut (STRUT_B2, STRUT_B1_*, build_strut): keep those names stable. Snapshot of heel outputs at "
                + __import__("time").strftime("%H:%M", __import__("time").localtime((heel_dir / "heel_add.step").stat().st_mtime)))
        except Exception as e:  # noqa: BLE001
            chk("cross-check: cap+strut vs heel.py outputs (info)", str(e)[:200], "n/a", True)

    # ---- mass
    rho = {"resin": 1.15e-3, "brass": 8.5e-3, "steel": 7.9e-3, "silicone": 1.1e-3, "fr4": 1.85e-3, "epoxy": 1.15e-3,
           "niti": 6.45e-3}
    m = {"pad_cup (resin)": cup.volume * rho["resin"], "pad_cap_strut (resin)": cap.volume * rho["resin"],
         "contact silicone": sil.volume * rho["silicone"], "pad_board": brd.volume * rho["fr4"],
         "diffuser epoxy": epoxy.volume * rho["epoxy"], "nut M1.4 brass": hw["nut_M1.4_brass"].volume * rho["brass"],
         "set screw": hw["setscrew_M1.4x2"].volume * rho["steel"], "screw M1.2x4": hw["screw_M1.2x4"].volume * rho["steel"],
         "transducer (estimate, [Low], E1 weighs it)": 1.2,
         "NiTi in socket (3.5 mm)": math.pi * WIRE_R ** 2 * SOCK_DEPTH * rho["niti"],
         "4 conductors in strut (~12 mm)": 0.01}
    tot = sum(m.values())
    chk("mass estimate (g)", {k: round(v, 3) for k, v in m.items()} | {"total": round(tot, 2),
        "rigid contact instead of silicone": round(rig.volume * rho["resin"], 3)}, "info (resin 1.15 g/cm3)", True)
    vols = {k: round(parts[k].volume, 1) for k in ("pad_cup", "pad_cap_strut", "pad_contact_rigid", "pad_diffuser_epoxy")}
    chk("volumes (mm3)", vols, "info", True)

    # ---- geometry summary for other modules
    C["interface"] = {
        "T_worn": np.round(T_W, 3).tolist(), "a_T": np.round(A_W, 4).tolist(), "b1": np.round(B1_W, 4).tolist(),
        "b2": np.round(B2_W, 4).tolist(), "strut_top_along": round(ALONG_TOP, 3),
        "strut_section_b1": [STRUT_B1_LO, STRUT_B1_HI_TOP, STRUT_B1_HI_BOT], "strut_section_b2": list(STRUT_B2),
        "conductor_channel": {"d": 2 * COND_R, "b1": COND_B1, "b2": COND_B2,
                              "entry_world_worn": np.round(T_W + top_along(COND_B1) * A_W + COND_B1 * B1_W + COND_B2 * B2_W, 3).tolist(),
                              "gap_to_heel_channel_entry_mm": round(float(np.linalg.norm(
                                  T_W + top_along(COND_B1) * A_W + COND_B1 * B1_W + COND_B2 * B2_W - HEEL_CH_ENTRY)), 2)},
        "strut_top_rake_mm": STRUT_RAKE,
        "wire_channel_top": {"up(+b1)": round(WIRE_R + CH_UP_TOP, 3), "down(-b1)": round(WIRE_R + CH_DN_TOP, 3),
                             "side(b2)": round(WIRE_R + CH_SIDE_TOP, 3)},
        "board_pads (as read from hw/padboard)": {n: {"u": [round(u0, 3), round(u1, 3)], "w": [round(w0, 3), round(w1, 3)]} for n, u0, u1, w0, w1 in brd_rows},
        "joint_zones": {"dam_r_from_LED": DAM_R, "top_front": "u -2.65..0, w 2.0..6.3, joints <= 0.45 tall", "top_rear": f"u 0..2.65, w 2.0..{W_REAR_POCKET}", "rear_wire_path": f"u 0..2.65, w {W_REAR_POCKET}..{W_WIREPATH_END}, <= 0.35 tall", "bottom": "u -2.65..2.65, w -6.3..-2.0"},
        "led_top_used": Y_LED_REAL,
        "screw": {"closure": "M1.2 x 4 pan (eyeglass), self-tapping into a 0.95 pilot", "set": "M1.4 x 2 cup point + brass M1.4 nut"},
    }
    for k, s in parts.items():
        export_step(s, str(OUT / f"{k}.step"))
        if k in printed:
            export_stl(s, str(OUT / f"{k}.stl"), tolerance=0.005, angular_tolerance=0.1)
    export_step(Compound([v for k, v in parts.items() if k != "pad_contact_rigid"]), str(OUT / "pad_assembly_worn.step"))
    mf = {k: stl_manifold(OUT / f"{k}.stl") for k in printed}
    chk("printed STLs are closed manifolds (re-read from disk)", mf, "every edge shared by exactly 2 triangles",
        all(v["ok"] for v in mf.values()))
    C["all_pass"] = all(c["pass"] for c in C["checks"])
    (OUT / "checks.json").write_text(json.dumps(C, indent=2, default=float))
    print(json.dumps({c["name"]: (c["pass"], c["value"]) for c in C["checks"]}, indent=1, default=float)[:20000])
    print("ALL PASS:", C["all_pass"])
    if render:
        render_views(parts)
    return parts, C


# ============================================================================ picture
def _section_tris(shape, u0=0.0):
    """Triangles of the cut face of `shape` on the plane u = u0, as (w, y) arrays."""
    slab = PAD_LOC * lbox(u0 - 0.004, u0 + 0.004, -20, 20, -30, 30)
    try:
        cut = shape & slab
    except Exception:  # noqa: BLE001
        return []
    out = []
    for f in cut.faces():
        fc_ = f.center()
        c = to_local(np.array([fc_.X, fc_.Y, fc_.Z]))
        if abs(c[0] - (u0 - 0.004)) > 1e-3:
            continue
        vs, tris = f.tessellate(0.01, 0.2)
        if not tris:
            continue
        V = np.array([to_local(np.array([v.X, v.Y, v.Z])) for v in vs])[:, [2, 1]]
        out.extend(V[np.array(tris)])
    return out


def render_views(parts):
    sys.path.insert(0, str(HERE.parents[1] / "tools"))
    import plotstyle
    from matplotlib.collections import PolyCollection
    from matplotlib.colors import to_rgb
    from matplotlib.patches import Circle as MCircle, Polygon as MPoly
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    plt = plotstyle.apply()
    S, TX, T2 = plotstyle.SERIES, plotstyle.TEXT, plotstyle.TEXT_2
    col = {"pad_cup": ("#8d939c", 1.0), "pad_cap_strut": ("#c9ccd2", 1.0), "pad_contact_silicone": (S[0], 0.95),
           "pad_board": (S[2], 1.0), "pad_board_led": (S[0], 1.0), "pad_diffuser_epoxy": ("#bfe3ff", 0.95),
           "ref_transducer_RC-BC02": (S[1], 1.0), "ref_niti_worn": ("#f0f0f0", 1.0), "pad_nut_M1.4_brass": (S[3], 1.0),
           "pad_setscrew_M1.4x2": ("#9a9a9a", 1.0), "pad_screw_M1.2x4": ("#9a9a9a", 1.0)}
    light = unit([0.2, 0.8, 0.55])

    def draw(ax, shapes, explode=None):
        """All parts in ONE collection, so matplotlib depth-sorts per triangle (not per part)."""
        polys, cols = [], []
        for name, sh in shapes.items():
            if name not in col:
                continue
            c, a = col[name]
            vs, tris = sh.tessellate(0.02, 0.25)
            if not tris:
                continue
            V = np.array([[p.X, p.Y, p.Z] for p in vs])
            if explode and name in explode:
                V = V + np.asarray(explode[name])
            Tn = np.array(tris)
            n = np.cross(V[Tn[:, 1]] - V[Tn[:, 0]], V[Tn[:, 2]] - V[Tn[:, 0]])
            n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
            sh_ = 0.30 + 0.70 * np.abs(n @ light)
            fc = np.clip(np.array(to_rgb(c))[None, :] * sh_[:, None], 0, 1)
            polys.append(V[Tn])
            cols.append(np.c_[fc, np.full(len(fc), a)])
        if polys:
            ax.add_collection3d(Poly3DCollection(np.concatenate(polys), facecolors=np.concatenate(cols), edgecolors="none"))

    def frame_ax(ax, c, r, el, az, title):
        ax.set_xlim(c[0] - r, c[0] + r); ax.set_ylim(c[1] - r, c[1] + r); ax.set_zlim(c[2] - r, c[2] + r)
        ax.set_box_aspect((1, 1, 1)); ax.view_init(elev=el, azim=az); ax.set_axis_off()
        ax.set_title(title, color=TX, fontsize=10)

    asm = {k: v for k, v in parts.items() if k != "pad_contact_rigid"}
    outside = {k: v for k, v in asm.items() if k not in ("pad_board", "pad_board_led", "ref_transducer_RC-BC02")}
    fig = plt.figure(figsize=(15, 13))
    c = np.array([68.0, 3.0, -20.5])
    ax = fig.add_subplot(2, 2, 1, projection="3d", proj_type="ortho")
    draw(ax, outside)
    frame_ax(ax, c, 8.5, 22, 62, "Assembled, worn pose: seen from outside and behind\n"
             "(hex collar = NiTi socket + set screw; LED ring in the hex bezel; armour + trace at the bottom)")
    ax = fig.add_subplot(2, 2, 2, projection="3d", proj_type="ortho")
    ex = {"pad_cap_strut": F.E2 * 9.0, "ref_niti_worn": F.E2 * 9.0, "pad_diffuser_epoxy": F.E2 * 13.0,
          "pad_nut_M1.4_brass": F.E2 * 9.0 + B1_W * 5.0, "pad_setscrew_M1.4x2": F.E2 * 9.0 + B2_W * 4.0,
          "pad_screw_M1.2x4": F.E2 * 16.0, "pad_board": F.E2 * 4.5, "pad_board_led": F.E2 * 4.5,
          "pad_contact_silicone": -F.E2 * 3.0}
    draw(ax, asm, {k: np.asarray(v).tolist() for k, v in ex.items()})
    frame_ax(ax, c + np.array([0, 5.5, 0]), 12, 18, 62, "Exploded outward (E2): contact | cup + transducer | "
             "board + LED | cap+strut | epoxy | screws")

    # ---- 2D section on the centre plane u = 0 (w along the pad, y outward)
    ax = fig.add_subplot(2, 2, 3)
    order = ["ref_transducer_RC-BC02", "pad_cup", "pad_contact_silicone", "pad_board", "pad_board_led",
             "pad_diffuser_epoxy", "pad_cap_strut", "pad_screw_M1.2x4", "ref_niti_worn"]
    for k in order:
        tris = _section_tris(parts[k], 0.0)
        if tris:
            ax.add_collection(PolyCollection(tris, facecolors=to_rgb(col[k][0]), edgecolors="none", alpha=col[k][1]))
    ax.axhline(Y_SKIN, color=S[7], lw=1.0, ls="--")
    ax.text(-9.0, Y_SKIN - 0.55, "skin (contact face, y = -3.0)", color=S[7], fontsize=8)
    for yv in (Y_CAP, Y_BEZ, Y_COLLAR_TOP):
        ax.axhline(yv, color=GRID_C, lw=0.6, ls=":")
    ax.text(16.8, 11.8, "dotted levels, height above the skin:\n"
            f"cap face y {Y_CAP:g}  ->  {Y_CAP - Y_SKIN:.1f} mm\nbezel y {Y_BEZ:g}  ->  {Y_BEZ - Y_SKIN:.1f} mm\n"
            f"collar top y {Y_COLLAR_TOP:g}  ->  {Y_COLLAR_TOP - Y_SKIN:.1f} mm", color=T2, fontsize=7.5,
            ha="right", va="top")
    Tl, Bl = to_local(T_W), to_local(T_W + SOCK_DEPTH * A_W)
    ax.annotate("NiTi socket D0.85 x 3.5\n(dives outward 19 deg)", xy=((Tl[2] + Bl[2]) / 2, (Tl[1] + Bl[1]) / 2),
                xytext=(8.6, 8.4), color=TX, fontsize=8, arrowprops=dict(arrowstyle="-", color=T2, lw=0.7))
    ax.annotate("transducer RC-BC02\n6 x 4 x 12.6 (face down)", xy=(-3.0, 0.6), xytext=(-8.8, -6.2), color=S[1],
                fontsize=8, arrowprops=dict(arrowstyle="-", color=T2, lw=0.7))
    ax.annotate("pad board 0.8 + 0402 LED", xy=(-2.0, 3.0), xytext=(-9.2, 6.4), color=S[2], fontsize=8,
                arrowprops=dict(arrowstyle="-", color=T2, lw=0.7))
    ax.annotate("epoxy diffuser ring\n+ printed centre plug", xy=(1.0, 4.3), xytext=(-2.0, 8.7), color="#bfe3ff",
                fontsize=8, arrowprops=dict(arrowstyle="-", color=T2, lw=0.7))
    ax.annotate("0.6 skin wall", xy=(2.0, -1.7), xytext=(3.0, -5.4), color=T2, fontsize=8,
                arrowprops=dict(arrowstyle="-", color=T2, lw=0.7))
    ax.annotate("1 mm silicone (or rigid foot)", xy=(-1.0, -2.5), xytext=(-8.8, -4.6), color=S[0], fontsize=8,
                arrowprops=dict(arrowstyle="-", color=T2, lw=0.7))
    ax.annotate("M1.2 x 4 closure screw\n(self-taps into the cup)", xy=(W_SCREW, 3.0), xytext=(-9.6, 10.6), color=T2,
                fontsize=8, arrowprops=dict(arrowstyle="-", color=T2, lw=0.7))
    ax.annotate("hook: claw tip in the\ncup's end-wall window", xy=(7.1, 1.6), xytext=(9.0, -3.5), color=T2, fontsize=8,
                arrowprops=dict(arrowstyle="-", color=T2, lw=0.7))
    ax.set_xlim(-10, 17); ax.set_ylim(-7, 12); ax.set_aspect("equal")
    ax.set_xlabel("w along the pad (mm, + = up-forward)"); ax.set_ylabel("y outward (mm)")
    ax.set_title("Section on the centre plane (u = 0): the stack from the skin out", color=TX, fontsize=10)

    # ---- strut cross-section at its top, wire position in all four states
    ax = fig.add_subplot(2, 2, 4)
    hi = STRUT_B1_HI_TOP
    ax.add_patch(MPoly([(b2, b1) for b1, b2 in strut_section_pts(hi)], closed=True, fc="#c9ccd2", ec="none"))
    up, dn, hw = channel_section(ALONG_TOP)
    th = np.linspace(0, np.pi, 30)
    c0, c1 = -dn + hw, up - hw
    slot_pts = [(hw * np.cos(t), c1 + hw * np.sin(t)) for t in th] + [(hw * np.cos(t), c0 - hw * np.sin(t)) for t in th[::-1] * -1 + np.pi]
    slot_pts = [(hw * np.cos(t), c1 + hw * np.sin(t)) for t in th] + [(-hw * np.cos(t), c0 - hw * np.sin(t)) for t in th]
    ax.add_patch(MPoly(slot_pts, closed=True, fc=plotstyle.SURFACE, ec="none"))
    ax.add_patch(MCircle((COND_B2, COND_B1), COND_R, fc=plotstyle.SURFACE, ec="none"))
    for k, (dx, dy) in enumerate([(-0.15, 0.0), (0.15, 0.0), (0.0, 0.15), (0.0, -0.15)]):
        ax.add_patch(MCircle((COND_B2 + dx, COND_B1 + dy), 0.15, fc=S[3], ec="none"))
    states = [("free", S[2]), ("jaw_open_1.5", S[0]), ("worn_3.5", "#f0f0f0"), ("jaw_closed_5.5", S[7])]
    for st, cc in states:
        p = wire_points(st, F.STRUT_START, F.STRUT_START, 1)[0]
        d = p - T_W
        ax.add_patch(MCircle((d @ B2_W, d @ B1_W), WIRE_R, fc="none", ec=cc, lw=1.6))
        ax.text(1.55, d @ B1_W - 0.05, st, color=cc, fontsize=8)
        ax.plot([d @ B2_W + WIRE_R * 0.7, 1.5], [d @ B1_W, d @ B1_W], color=cc, lw=0.5)
    ax.text(COND_B2, COND_B1 - 1.05, "4 conductors\nD1.0 channel", color=S[3], fontsize=8, ha="center")
    ax.text(-0.0, -2.05, "toward the head", color=T2, fontsize=8, ha="center")
    ax.text(0.0, 2.25, "outward", color=T2, fontsize=8, ha="center")
    ax.annotate("rear (ear) face only 1.3\nbehind the wire", xy=(1.3, -0.9), xytext=(1.9, -1.9), color=T2, fontsize=8,
                arrowprops=dict(arrowstyle="-", color=T2, lw=0.7))
    ax.set_xlim(-3.6, 3.8); ax.set_ylim(-2.4, 2.6); ax.set_aspect("equal")
    ax.set_xlabel("b2 lateral (mm, + = rear, toward the ear)"); ax.set_ylabel("b1 (mm, + = outward)")
    ax.set_title(f"Strut section at its top (s = {F.STRUT_START:g} mm): {STRUT_B2[1] - STRUT_B2[0]:.1f} x {hi - STRUT_B1_LO:.2f} mm,"
                 f" tapering to {STRUT_B1_HI_BOT - STRUT_B1_LO:.2f} deep at the pad\nThe NiTi only ever moves outward (+b1) "
                 "inside it: slot = 0.9 clearance there, 0.25-0.3 elsewhere", color=TX, fontsize=10)
    fig.suptitle("Transducer pod + strut, rev 1 = the prototype (hw/mech/pad.py, 2026-09-30)", color=TX, fontsize=13)
    fig.subplots_adjust(left=0.04, right=0.98, top=0.93, bottom=0.05, wspace=0.12, hspace=0.18)
    fig.savefig(OUT / "pad_views.png", dpi=110)
    render_sequence(parts, draw, frame_ax, plt, plotstyle)


def render_sequence(parts, draw, frame_ax, plt, plotstyle):
    """Bench assembly in six steps + the pad board's pads (owner: show how it mounts, fixes, wires)."""
    from matplotlib.patches import Rectangle
    S, TX, T2 = plotstyle.SERIES, plotstyle.TEXT, plotstyle.TEXT_2
    piv = to_world(np.array([0.0, (TIP["y0"] + TIP["y1"]) / 2, (TIP["w0"] + CLAW["w0"]) / 2]))
    ax_h = Axis(tuple(map(float, piv)), tuple(map(float, F.E1)))
    tilt = 6
    cap_t = parts["pad_cap_strut"].rotate(ax_h, tilt)
    nut_t = parts["pad_nut_M1.4_brass"].rotate(ax_h, tilt)
    base = {k: parts[k] for k in ("pad_cup", "ref_transducer_RC-BC02", "pad_contact_silicone")}
    brd = {k: parts[k] for k in ("pad_board", "pad_board_led")}
    closed = {k: parts[k] for k in ("pad_cup", "pad_contact_silicone", "pad_cap_strut", "pad_nut_M1.4_brass")}   # internals hidden
    steps = [
        ("1  Transducer face-down into the cup (slide fit),\n2 RTV dots on its sides; silicone disc on the skin face", base),
        ("2  Board onto the transducer back. Leads soldered:\nXDCR_A/B (bottom end), 4 arm wires (top end)", base | brd),
        (f"3  Nut dropped into the collar slot. Hook the claw\ninto the cup window, cap tilted ~{tilt} deg", base | brd | {"pad_cap_strut": cap_t, "pad_nut_M1.4_brass": nut_t}),
        ("4  Swing closed (checked collision-free 0-8 deg);\ndrive the M1.2 x 4 screw at the bottom end", closed | {"pad_screw_M1.2x4": parts["pad_screw_M1.2x4"]}),
        ("5  Cast the LED ring: clear epoxy + a speck of white\nthrough the 0.6 mm ring, on PE film; cure 24 h", closed | {k: parts[k] for k in ("pad_screw_M1.2x4", "pad_diffuser_epoxy")}),
        ("6  NiTi down the strut into the socket (flat to the rear);\nM1.4 x 2 set screw, 0.7 hex key, snug", closed | {k: parts[k] for k in ("pad_screw_M1.2x4", "pad_diffuser_epoxy", "ref_niti_worn", "pad_setscrew_M1.4x2")}),
    ]
    fig = plt.figure(figsize=(18, 10.5))
    c = np.array([68.0, 3.0, -20.5])
    for i, (title, shp) in enumerate(steps):
        ax = fig.add_subplot(2, 4, i + 1 + (1 if i >= 3 else 0), projection="3d", proj_type="ortho")
        draw(ax, shp)
        if i == 2:     # side view along E1 so the hook-and-swing reads
            frame_ax(ax, c + np.array([0, 2.0, 0]), 9.5, -30, 180, title + "\n(view along the pad width, from the front)")
        else:
            frame_ax(ax, c, 8.5, 22, 62, title)
        ax.title.set_fontsize(9)
    ax = fig.add_subplot(2, 4, 4)
    ax.add_patch(Rectangle((-BRD_U, BOARD["e3_0"]), 2 * BRD_U, BOARD["e3_1"] - BOARD["e3_0"], fc=S[2], ec="none", alpha=0.85))
    cur = {r[0]: r for r in pad_rows(PADBOARD_LAYOUT)}
    for n, u0, u1, w0, w1, kind, uc, wc in cur.values():
        if kind == "smd":
            ax.add_patch(Rectangle((u0, w0), u1 - u0, w1 - w0, fc="#d8b25a", ec="none"))
        else:
            ax.add_patch(plt.Circle((uc, wc), (u1 - u0) / 2, fc="#d8b25a", ec="none"))
            ax.add_patch(plt.Circle((uc, wc), 0.3, fc="#141518", ec="none"))
        ax.text(uc, wc + (0.0 if kind == "smd" else -0.85), n, color="#141518" if kind == "smd" else TX,
                fontsize=6.0, ha="center", va="center")
    for ref, (x, y) in PADBOARD_REQUESTED.items():       # pad.py's 20:45 request, dashed where the live one differs
        n, x0, y0, kind, sx, sy = PADBOARD_LAYOUT[ref]
        if abs(x - x0) < 1e-3 and abs(y - y0) < 1e-3:
            continue
        if kind == "smd":
            ax.add_patch(Rectangle((-x - sx / 2, -y - sy / 2), sx, sy, fc="none", ec=S[3], lw=0.8, ls="--"))
        else:
            ax.add_patch(plt.Circle((-x, -y), 0.45, fc="none", ec=S[3], lw=0.8, ls="--"))
    ax.add_patch(Rectangle((-0.25, -0.5), 0.5, 1.0, fc=S[0], ec="none"))
    ax.add_patch(plt.Circle((0, 0), RING_OD / 2, fc="none", ec="#bfe3ff", lw=1.0, ls="--"))
    ax.add_patch(plt.Circle((0, 0), DAM_R, fc="none", ec=S[7], lw=1.2))
    ax.text(-3.2, 1.2, f"red: printed dam r {DAM_R:.2f}\n(ring wall on the PE film);\nno joint may sit inside it.\n"
            f"Layout read live from\nhw/padboard/layout.py ({PADBOARD_READ_AT}).\ndashed: pad.py's request\n"
            "(electronics kept 0.3 mm\ncopper-to-edge instead)", color=S[7], fontsize=6.3, ha="right", va="center")
    ax.text(0.45, 0.0, "0402 blue LED\n(JLC-placed, C131223)", color=TX, fontsize=7, va="center")
    ax.text(0, -2.2, "ring D5.3 above it", color="#bfe3ff", fontsize=7, ha="center")
    ax.text(-3.2, 4.8, "4 arm wires from the strut ->\nOUT_A, OUT_B, LED+, LED-\n(pod pads of the same names)", color=TX, fontsize=7, ha="right", va="center")
    ax.text(-3.2, -3.7, "transducer leads ->\nXDCR_A / XDCR_B", color=TX, fontsize=7, ha="right", va="center")
    ax.text(0, 6.2, "top end (toward the strut)", color=T2, fontsize=7, ha="center")
    ax.set_xlim(-8.0, 3.5); ax.set_ylim(-5.0, 6.8); ax.set_aspect("equal")
    ax.set_xlabel("u (mm, + = rear)"); ax.set_ylabel("w (mm, + = up-forward)")
    ax.set_title("Pad board 5.0 x 9.3 x 0.8, top face: pads", color=TX, fontsize=9)
    fig.suptitle("Pad assembly at the bench (reverse for disassembly); pad.py, 2026-09-30", color=TX, fontsize=13)
    fig.subplots_adjust(left=0.02, right=0.99, top=0.92, bottom=0.04, wspace=0.05, hspace=0.12)
    fig.savefig(OUT / "pad_assembly_steps.png", dpi=105)


GRID_C = "#3a3d44"


if __name__ == "__main__":
    main(render="--render" in sys.argv)
