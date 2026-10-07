"""Phase-2 pod shell (ECR-0018, owner O24-O26, package MZ-2 'Balanced'): interior built around the one-face board.

    source tools/env.sh && systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 \
        python3 hw/mech/shell_r2.py          # -> hw/mech/out/r2/*.stl, parts.json, checks.json, section.png, plan.png

What changed from hw/mech/shell_r1.py (same frame, same heel, same rail, same bonded/screwless lid):
- Board hw/pod/draft_r2/placement.yaml: 30 x 12 x 0.8, every part on B (toward the cell) except SW1 on F.
  Size-model stack (sim/checks/size_budget.py, MZ-2): wall 0.8 | VHB 0.3 | cell 5.3 | B gap 1.4 | board 0.8 |
  F gap 0.30 | lid 0.8 | plate 0.7 -> T 10.40; H 14.5 (cell 12 + 0.8 under + 0.1 over); belly 2.05 (flat dock tails).
- The board HANGS FROM THE LID on full-face VHB (3M 4914, 0.25 mm) in the 0.30 F gap. Nothing touches its long
  edges. The seam moves down to the board's B face (y 12.1): the lid is a shallow cap whose skirt holds the board,
  so lifting the lid lifts the board on its wires and exposes the cell (cell swap needs no peel). Round the belly
  the seam steps to z = CAV z0 so the whole belly (dock window) is tub.
- Bare F test pads (TP1-TP6, read live from placement.yaml) get a VHB cut-out; bonded, they face the lid (no access).
- Seam location: tub tongue / lid groove on the straight wall runs (r1's inner lip would collide with the board's
  long edges), stopped 1.4 mm short of every convex corner (the 1 mm outer chamfer leaves only 0.42 mm of wall there).
- Mic port (O24 option B): sealed straight duct ID 1.0 = lid bore (reamed) + a D1.0 hole in the VHB, ending on the
  board's F face round the D0.6 board hole. Location: the bore itself is the datum. During bonding a stepped gauge
  pin (D0.98 body in the bore, D0.50 tip in the board hole) registers VHB and board to the bore; the front skirt
  wall is a coarse x-stop 0.25 mm ahead of the board (never touches within tolerance, so it cannot fight the pin).
- SW1 (C&K KMT022) sits in a 4.3 x 3.1 lid pocket (skeptic: >= ~4.1 x 2.9 for the J-lead pads); a printed puck in a
  D2.6 bore carries the press to a silicone skin in a D4.6 recess. Puck length is SELECTIVE-FIT (5 printed lengths, 0.05 apart),
  because the fixed stack's worst case pre-presses the switch.
- Wires: all board pads at the rear (board x 25-30); stowage gap behind the board, above the cell (MZG-10).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from build123d import (Box, Cylinder, Pos, Rot, RegularPolygon, chamfer, export_stl, extrude)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "sim" / "checks"))
import blade  # noqa: E402
import frame as F  # noqa: E402
from styles import plate, slot  # noqa: E402

OUT = HERE / "out" / "r2"

# ---------------------------------------------------------------- stack-up (pod frame, mm; x fwd->rear, y out, z up)
X0, X1 = 29.5, 67.5                    # L 38.0 = 2 x 0.8 + 0.3 + cell 35 + rear gap 1.1 (size model)
W = 0.8
Y_IN = F.Y_IN                          # 4.3 inner face on the adapter (frame.py)
TAPE = 0.3                             # cell VHB gap (0.25 tape)
CELL_T, B_GAP, PCB_T, F_GAP, LID_T, PLATE_T = 5.3, 1.4, 0.8, 0.30, 0.8, 0.7
Y_CELL0 = Y_IN + W + TAPE              # 5.4
Y_CELL1 = Y_CELL0 + CELL_T             # 10.7
Y_B = Y_CELL1 + B_GAP                  # 12.1 board B face
Y_F = Y_B + PCB_T                      # 12.9 board F face
Y_LID_IN = Y_F + F_GAP                 # 13.2 lid inner face
Y_OUT = Y_LID_IN + LID_T               # 14.0 body outer face
Y_TOP = Y_OUT + PLATE_T                # 14.7 armour plate top
Y_SPLIT = Y_B                          # seam: tub | lid, at the board's B face
VHB_T = 0.25                           # 3M VHB 4914 nominal (physical.md row 5.1-5.4)
Z0 = -9.7                              # bottom kept from r1 (heel, strut relief and NiTi clearances unchanged)
H = 2 * W + 12.0 + 0.8 + 0.1           # 14.5: cell 12 + s_fixed 0.8 under + 0.1 over (size model)
Z1 = Z0 + H                            # 4.8
BELLY_D = 2.8 + 0.85 - (W + 0.8)       # 2.05: target 2.8 + flat tails 0.85 - (wall + slack under the cell)
Z_BELLY = Z0 - BELLY_D                 # -11.75
X_BELLY = X0 + 25.5                    # 55.0 (DOCKS['flat_tails'].L)
CAV = dict(x0=X0 + W, x1=X1 - W, y0=Y_IN + W, y1=Y_LID_IN, z0=Z0 + W, z1=Z1 - W)
BAY = dict(x0=X0 + W, x1=X_BELLY - W, z0=Z_BELLY + W, z1=CAV["z0"])
CELL = dict(x0=CAV["x0"] + 0.3, x1=CAV["x0"] + 0.3 + 35.0, y0=Y_CELL0, y1=Y_CELL1, z0=CAV["z0"] + 0.8, z1=CAV["z0"] + 12.8)

# ---------------------------------------------------------------- board (hw/pod/draft_r2/placement.yaml)
PCB_L, PCB_H, PCB_R = 30.0, 12.0, 1.0
X_STOP_GAP = 0.25                      # coarse x-stop: front skirt wall to board front edge
PCB = dict(x0=CAV["x0"] + X_STOP_GAP, y0=Y_B, y1=Y_F, z0=(CAV["z0"] + CAV["z1"]) / 2 - PCB_H / 2)
PCB["x1"], PCB["z1"] = PCB["x0"] + PCB_L, PCB["z0"] + PCB_H


def bpt(bx, by):
    """board (x, y) -> pod (x, z). Board +y = pod +z (the right pod's mirror flips it; mic and SW1 sit on y 6.0)."""
    return PCB["x0"] + bx, PCB["z0"] + by


MIC_HOLE_D = 0.6
def board_mic():
    """U2 centre and its port hole (board mm) read from the routed Phase-2 board, so the duct follows the layout."""
    import re
    f = Path(__file__).resolve().parents[1] / "pod/draft_r2/out/routed.kicad_pcb"
    s = f.read_text()
    i = s.index('"Reference" "U2"')
    blk = s[s.rfind("(footprint ", 0, i):i]
    x, y, rot = (float(v) for v in re.search(r"\(at ([\d.\-]+) ([\d.\-]+) ([\d.\-]+)\)", blk).groups())
    assert abs(rot - 90) < 1e-6, "port-hole offset below assumes U2 at rot 90"
    return (x, y), (x - 0.77, y)      # Knowles LGA port hole at local (0, -0.77)


U2_XY, MIC_XY = board_mic()            # 2026-10-07: (2.65, 6.0) / (1.88, 6.0) after route closure v6
MIC = bpt(*MIC_XY)                     # board hole = duct axis (nominal offset 0)
SW = bpt(18.5, 6.0)
U2 = dict(c=bpt(*U2_XY), dx=2.65, dz=3.5, h=1.08)          # Knowles LGA 3.5 x 2.65, rot 90; tallest B part
SW1 = dict(body=(3.0, 2.6), pads=(3.8, 2.6), h=0.65, travel=(0.05, 0.15, 0.25))  # KMT022: 3.0x2.6x0.65; travel 0.15+-0.1
B_MAX = 1.08                           # tools/checks/part_heights.yaml: U2
PAD_ZONE = (25.0, 30.0)                # rear wire pads, board x


def _f_pads():
    """Bare F-face pads other than SW1 (TP1-TP6 since the 2026-10-03 00:28 placement edit), read live from the file."""
    try:
        import yaml
        pl = yaml.safe_load((ROOT / "hw/pod/draft_r2/placement.yaml").read_text())
        return {k: (v[0], v[1]) for k, v in pl.items() if isinstance(v, list) and len(v) >= 4 and v[3] == "F" and k != "SW1"}
    except Exception:          # noqa: BLE001  (the shell must build without the board file)
        return {}


F_PADS = _f_pads()
TP_PAD_D, TP_CUT_MARGIN = 1.0, 0.4     # [A] test-pad copper D1.0; VHB kept 0.4 clear so the pads stay clean

# ---------------------------------------------------------------- lid features
DUCT_D = 1.0                           # O24: ID 1.0; bore printed undersize and reamed with a 1.0 drill
HEX_R, HEX_DEPTH = 1.9, 0.8            # r1 window (mesh seat), cut down from the plate top
POCKET = dict(dx=4.3, dz=3.1, top=Y_LID_IN + 0.6)     # SW1 pocket: 4.3 x 3.1, ceiling at y 13.8
BORE_D, PUCK_D, NUB_D, NUB_H = 2.6, 2.3, 1.0, 0.10
SKIN_D, SKIN_T = 4.6, 0.25
SKIN_FLOOR = Y_TOP - SKIN_T            # 14.45
PRE_GAP = 0.07                         # nominal puck top -> skin underside (selective fit keeps it in 0.005..0.135)
PUCK_L = SKIN_FLOOR - PRE_GAP - (Y_F + SW1["h"])        # 0.83 nominal
PUCK_STEP = 0.05
PUCK_KIT = tuple(round(PUCK_L + k * PUCK_STEP, 2) for k in (-2, -1, 0, 1, 2))   # print all 5, measure, fit one

Y_MID = (Y_IN + Y_OUT) / 2
DOCK = dict(x0=31.5, x1=52.7, y0=Y_MID - 3.43, y1=Y_MID + 3.43, z0=Z_BELLY, z1=Z_BELLY + 2.8)   # YZT0675 21.2 x 6.86 x 2.8
TONGUE_W, TONGUE_H, GROOVE_CL, CORNER_KEEP = 0.35, 0.5, 0.05, 1.4
STEP_H = 0.35                          # belly-step key: its top must stay below the hanging board's lower edge (sweep)


def box(x0, x1, y0, y1, z0, z1):
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(x1 - x0, y1 - y0, z1 - z0)


def ycyl(x, z, d, y0, y1):
    return Pos(x, (y0 + y1) / 2, z) * Rot(90, 0, 0) * Cylinder(d / 2, y1 - y0)


def outer_body():
    main = chamfer(box(X0, X1, Y_IN, Y_OUT, Z0, Z1).edges(), 1.0)
    belly = chamfer(box(X0, X_BELLY, Y_IN, Y_OUT, Z_BELLY, Z0 + 1.5).edges(), 1.0)
    return main + belly


def cavity():
    return box(CAV["x0"], CAV["x1"], CAV["y0"], CAV["y1"], CAV["z0"], CAV["z1"]) + \
        box(BAY["x0"], BAY["x1"], CAV["y0"], CAV["y1"], BAY["z0"], BAY["z1"] + 0.01)


def tongue(g=0.0):
    """Seam locator on the straight wall runs: tub tongue (g=0) or lid groove (g = clearance)."""
    t, k, y0, y1 = TONGUE_W + g, CORNER_KEEP, Y_SPLIT - 0.01, Y_SPLIT + TONGUE_H + g
    c, b = CAV, BAY
    runs = [
        (X0 + k, X1 - k, c["z1"] - g, c["z1"] + t),                  # top
        (c["x1"] - g, c["x1"] + t, Z0 + k, Z1 - k),                  # rear
        (X_BELLY + k - 1.0, X1 - k, c["z0"] - t, c["z0"] + g),       # bottom behind the belly
        (c["x0"] - t, c["x0"] + g, c["z0"] + 0.4, Z1 - k),           # front (above the belly step)
    ]
    # belly step land (x < X_BELLY, z = CAV z0): tub's belly outer wall tongues up into the lid face, inner side
    step = box(X0 + k, X_BELLY - 0.4, Y_LID_IN - g, Y_LID_IN + t, c["z0"] - 0.01, c["z0"] + STEP_H + g)
    s = step
    for xa, xb, za, zb in runs:
        r = box(xa, xb, y0, y1, za, zb)
        s = r if s is None else s + r
    return s


def tub_region():
    """Stepped seam: y < Y_SPLIT everywhere, plus the whole belly (x < X_BELLY, z < CAV z0) so the dock window
    sits in one part. The lid's face meets the belly's outer wall on a 0.8 land at z = CAV z0."""
    return box(X0 - 1, X1 + 1, Y_IN - 2, Y_SPLIT, Z_BELLY - 1, Z1 + 1) + \
        box(X0 - 1, X_BELLY, Y_IN - 2, Y_OUT + 2, Z_BELLY - 1, CAV["z0"])


def seam_rebate():
    """Tub-only 0.2 x 0.3 rebate round the outside on the y = Y_SPLIT runs (cut line for reopening).
    The belly step (z = CAV z0, x < X_BELLY) is left unmarked (open item)."""
    band = box(X0 - 1, X1 + 1, Y_SPLIT - 0.3, Y_SPLIT + 0.01, Z_BELLY - 1, Z1 + 1)
    band = band - box(X0 + 0.2, X1 - 0.2, Y_SPLIT - 0.4, Y_SPLIT + 0.1, Z0 + 0.2, Z1 - 0.2)
    return band - box(X0 - 2, X_BELLY, Y_SPLIT - 1, Y_SPLIT + 1, Z_BELLY - 2, CAV["z0"])


def tub(heel_mod=None):
    t = outer_body() & tub_region()
    t = t + blade.rail()
    if heel_mod is not None:
        t = t + heel_mod.heel_add()
    t = t - cavity()
    if heel_mod is not None:
        t = t - heel_mod.heel_cut()
    t = t - box(DOCK["x0"] - 0.1, DOCK["x1"] + 0.1, DOCK["y0"] - 0.1, DOCK["y1"] + 0.1, Z_BELLY - 1, DOCK["z1"])
    # strut relief, identical to r1 (same Z0, CAV y0/z0): fill the inner-bottom rear corner, cut the outside back
    cz = CAV["z0"]
    t = t + blade.prism_yz([(CAV["y0"], cz), (CAV["y0"] + 1.0, cz), (CAV["y0"], cz + 1.0)], 62.0, CAV["x1"])
    t = t - blade.prism_yz([(3.9, -12.5), (3.9, -3.65 - 3.9), (-3.65 + 12.5, -12.5)], 62.0, 68.5)
    t = t + (tongue() & outer_body())
    t = t + (plate(PLATE_PTS, Y_OUT, PLATE_T, 0.3) & tub_region())      # armour plate below the belly step
    t = t - slot(TRACE, Y_TOP, 0.7, 0.45)                                 # trace continues across the step
    return t - seam_rebate()


def _zmap(z):
    """r1 plate/trace z -> r2 (r1 spans belly -13.2 .. top 5.5; r2 spans -11.75 .. 4.8)."""
    return Z_BELLY + (z + 13.2) * (Z1 - Z_BELLY) / (5.5 + 13.2)


PLATE_PTS = [(x, _zmap(z)) for x, z in [(31.8, 4.0), (46.0, 4.0), (47.8, 5.0), (66.2, 5.0), (66.2, -8.2), (61.0, -9.3),
                                         (55.0, -9.3), (53.5, -12.4), (34.5, -12.4), (31.8, -10.0)]]
TRACE = [(x, _zmap(z)) for x, z in [(36.5, -11.0), (51.0, -11.0), (55.5, -6.0), (63.8, -6.0), (63.8, 2.6)]]


def lid_base():
    l = outer_body() - tub_region()
    l = l + (plate(PLATE_PTS, Y_OUT, PLATE_T, 0.3) - tub_region())
    l = l - slot(TRACE, Y_TOP, 0.7, 0.45)
    l = l - cavity()
    l = l - tongue(GROOVE_CL)
    # mic duct: reamed D1.0 bore from the lid inner face to the hex window floor; hex window = mesh seat
    l = l - ycyl(MIC[0], MIC[1], DUCT_D, Y_LID_IN - 0.01, Y_TOP + 0.01)
    l = l - Pos(MIC[0], Y_TOP - HEX_DEPTH / 2, MIC[1]) * Rot(90, 0, 0) * extrude(RegularPolygon(HEX_R, 6), amount=HEX_DEPTH / 2, both=True)
    # SW1: pocket (VHB is cut to the same outline), puck bore, skin recess
    l = l - box(SW[0] - POCKET["dx"] / 2, SW[0] + POCKET["dx"] / 2, Y_LID_IN - 0.01, POCKET["top"], SW[1] - POCKET["dz"] / 2, SW[1] + POCKET["dz"] / 2)
    l = l - ycyl(SW[0], SW[1], BORE_D, POCKET["top"] - 0.01, Y_TOP + 0.01)
    l = l - ycyl(SW[0], SW[1], SKIN_D, SKIN_FLOOR, Y_TOP + 0.01)
    return l


def puck(length=None):
    L = PUCK_L if length is None else length
    y_sw = Y_F + SW1["h"]
    return ycyl(SW[0], SW[1], NUB_D, y_sw, y_sw + NUB_H + 0.01) + ycyl(SW[0], SW[1], PUCK_D, y_sw + NUB_H, y_sw + L)


def board():
    b = box(PCB["x0"], PCB["x1"], PCB["y0"], PCB["y1"], PCB["z0"], PCB["z1"])
    b = b.fillet(PCB_R, [e for e in b.edges() if abs(e.length - PCB_T) < 1e-6]) if hasattr(b, "fillet") else b
    return b - ycyl(MIC[0], MIC[1], MIC_HOLE_D, PCB["y0"] - 0.1, PCB["y1"] + 0.1)


def vhb():
    v = box(PCB["x0"] + 0.2, PCB["x1"] - 0.2, Y_LID_IN - VHB_T, Y_LID_IN, PCB["z0"] + 0.2, PCB["z1"] - 0.2)
    v = v - ycyl(MIC[0], MIC[1], DUCT_D, Y_LID_IN - 1, Y_LID_IN + 1)
    v = v - box(SW[0] - POCKET["dx"] / 2, SW[0] + POCKET["dx"] / 2, Y_LID_IN - 1, Y_LID_IN + 1, SW[1] - POCKET["dz"] / 2, SW[1] + POCKET["dz"] / 2)
    if F_PADS:                 # one strip round the F test-pad row: no adhesive on the pads
        r = TP_PAD_D / 2 + TP_CUT_MARGIN
        xs = [bpt(*xy)[0] for xy in F_PADS.values()]
        zs = [bpt(*xy)[1] for xy in F_PADS.values()]
        v = v - box(min(xs) - r, max(xs) + r, Y_LID_IN - 1, Y_LID_IN + 1, min(zs) - r, max(zs) + r)
    return v


def placeholders():
    e = 0.3
    return {
        "cell": box(CELL["x0"], CELL["x1"], CELL["y0"], CELL["y1"], CELL["z0"], CELL["z1"]),
        "pcb": board(),
        "vhb": vhb(),
        # B parts: envelope at the tallest B height everywhere (conservative) and U2 itself
        "parts_B": box(PCB["x0"] + e, PCB["x1"] - e, Y_B - B_MAX, Y_B, PCB["z0"] + e, PCB["z1"] - e),
        "u2_mic": box(U2["c"][0] - U2["dx"] / 2, U2["c"][0] + U2["dx"] / 2, Y_B - U2["h"], Y_B, U2["c"][1] - U2["dz"] / 2, U2["c"][1] + U2["dz"] / 2),
        "sw1": box(SW[0] - SW1["body"][0] / 2, SW[0] + SW1["body"][0] / 2, Y_F, Y_F + SW1["h"], SW[1] - SW1["body"][1] / 2, SW[1] + SW1["body"][1] / 2)
        + box(SW[0] - SW1["pads"][0] / 2, SW[0] + SW1["pads"][0] / 2, Y_F, Y_F + 0.2, SW[1] - 0.4, SW[1] + 0.4),
        "dock": box(DOCK["x0"], DOCK["x1"], DOCK["y0"], DOCK["y1"], DOCK["z0"], DOCK["z1"]),
        "skin": ycyl(SW[0], SW[1], SKIN_D - 0.1, SKIN_FLOOR, Y_TOP),
    }


def stowage_zone():
    """Behind the board (board rear edge -> rear wall), cell top -> lid inner face, full height; + behind the cell."""
    behind_board = box(PCB["x1"], CAV["x1"], Y_CELL1, Y_LID_IN, CAV["z0"], CAV["z1"])
    behind_cell = box(CELL["x1"], CAV["x1"], CAV["y0"], Y_CELL1, CAV["z0"], CAV["z1"])
    return behind_board, behind_cell


def top_concept():
    """r1 'spine' top (159.6 mm3 in the size model), moved onto the r2 outer face and top."""
    import shell_r1 as R1
    return Pos(0, Y_TOP - (R1.Y_OUT + 0.7), Z1 - R1.Z1) * R1.concept_spine()


# ---------------------------------------------------------------- checks
def duct_offsets():
    """Bore axis vs board-hole axis. Tolerances: [A] assumed, verify before freeze."""
    tol = dict(
        print_bore_pos=0.05,          # [A] resin print, bore position vs any lid feature (frame.RESIN class)
        bore_ream=(1.00, 1.02),       # reamed with a 1.0 drill, +0.02 [A]
        pin_body=0.98, pin_tip=0.50, pin_runout=0.02,   # stepped gauge pin [A] (turned brass)
        hole=(0.55, 0.65),            # NPTH D0.6 +-0.05 [A: JLC capability, verify]
        outline_to_hole=0.20,         # [A] JLC routed outline +-0.2 (verify), sets the edge-stop error
    )
    pin_r = (tol["bore_ream"][1] - tol["pin_body"]) / 2 + (tol["hole"][1] - tol["pin_tip"]) / 2 + tol["pin_runout"]
    stop_dx = X_STOP_GAP + tol["outline_to_hole"] + tol["print_bore_pos"]
    stop_dz = (CAV["z1"] - CAV["z0"] - PCB_H) / 2 + tol["outline_to_hole"] + tol["print_bore_pos"]
    hole = bpt(*board_mic()[1])         # re-read: the duct must sit on the board's port hole as built
    nominal = math.hypot(MIC[0] - hole[0], MIC[1] - hole[1])
    lim = DUCT_D / 2 - MIC_HOLE_D / 2
    # the pin must never be fought by the x-stop / skirt walls: wall gap > outline error
    walls_free = X_STOP_GAP > tol["outline_to_hole"] and (CAV["z1"] - CAV["z0"] - PCB_H) / 2 > tol["outline_to_hole"]
    return dict(limit_R_ACO_P5=round(lim, 3), nominal=round(nominal, 3),
                worst_walls_only=round(math.hypot(stop_dx, stop_dz), 3), worst_walls_only_pass=math.hypot(stop_dx, stop_dz) <= lim,
                worst_with_gauge_pin=round(pin_r, 3), worst_with_gauge_pin_pass=pin_r <= lim + 1e-9,
                walls_never_fight_pin=walls_free, tolerances=tol)


def switch_stack():
    """Puck top -> skin underside. Negative = switch pre-pressed. Tolerances [A] (C&K gives 0.65 nominal only)."""
    t = dict(vhb=0.025, sw_h=0.05, solder_lift=(0.0, 0.05), puck_print=0.05, recess_floor=0.05, lid_face=0.03)
    sym = t["vhb"] + t["sw_h"] + t["puck_print"] + t["recess_floor"] + t["lid_face"]
    g_min, g_max = PRE_GAP - sym - t["solder_lift"][1], PRE_GAP + sym
    rss = math.sqrt(t["vhb"] ** 2 + t["sw_h"] ** 2 + t["puck_print"] ** 2 + t["recess_floor"] ** 2 + t["lid_face"] ** 2 + 0.025 ** 2)
    # selective fit: gauge the skin-floor -> SW1-top depth through the bore (+-0.02), measure each printed puck
    # (calipers +-0.02; its print error drops out), fit the one that leaves PRE_GAP: residual = half a kit step + both
    sel_err = PUCK_STEP / 2 + 0.02 + 0.02
    sel = (PRE_GAP - sel_err, PRE_GAP + sel_err)
    tmin = SW1["travel"][0]
    return dict(nominal_gap=PRE_GAP, puck_L=round(PUCK_L, 3), puck_kit=PUCK_KIT,
                fixed_worst=[round(g_min, 3), round(g_max, 3)], fixed_rss=[round(PRE_GAP + 0.025 - rss, 3), round(PRE_GAP + 0.025 + rss, 3)],
                fixed_worst_prepress=g_min < -tmin, selective_fit=[round(sel[0], 3), round(sel[1], 3)],
                selective_fit_ok=sel[0] >= 0.0 and sel[1] < 0.3,
                pocket_ceiling_clear_nominal=round(POCKET["top"] - (Y_F + SW1["h"]), 3),
                pocket_ceiling_clear_worst=round(POCKET["top"] - (Y_F + SW1["h"]) - t["vhb"] - t["sw_h"] - t["solder_lift"][1] - t["lid_face"], 3),
                rule_travel_min=tmin, tolerances=t)


def main():
    import heel
    from size_budget import scenario
    OUT.mkdir(parents=True, exist_ok=True)
    t = tub(heel)
    lid0 = lid_base()
    lid = lid0 + top_concept()
    ph = placeholders()
    pk = puck()
    c = {}
    # 1 board inside the cavity, nothing collides
    for k in ("pcb", "parts_B", "u2_mic", "sw1", "cell", "vhb", "dock"):
        for name, part in (("tub", t), ("lid", lid)):
            c[f"clash/{name}/{k}"] = round((part & ph[k]).volume, 4)
    c["clash/tub/lid"] = round((t & lid).volume, 4)
    # cell drops in along -y; lid + hanging board come down along -y: nothing of the tub may sit in either path
    c["corridor/cell_drop_in"] = round((t & box(CELL["x0"], CELL["x1"], CELL["y0"], Y_SPLIT + 1, CELL["z0"], CELL["z1"])).volume, 4)
    c["corridor/board_drop_in"] = round((t & box(PCB["x0"], PCB["x1"], Y_B - B_MAX, Y_SPLIT + 3, PCB["z0"], PCB["z1"])).volume, 4)
    c["clash/parts_B/cell"] = round((ph["parts_B"] & ph["cell"]).volume, 4)
    c["clash/puck/lid"] = round((pk & lid).volume, 4)
    c["clash/puck/sw1"] = round((pk & ph["sw1"]).volume, 4)
    bb = ph["pcb"].bounding_box()
    c["board_in_cavity"] = dict(x=[round(bb.min.X, 2), round(bb.max.X, 2)], cav_x=[CAV["x0"], CAV["x1"]], z=[round(bb.min.Z, 2), round(bb.max.Z, 2)],
                                cav_z=[CAV["z0"], CAV["z1"]], side_gap_z=round((CAV["z1"] - CAV["z0"] - PCB_H) / 2, 2), front_gap=X_STOP_GAP,
                                inside=bb.min.X >= CAV["x0"] and bb.max.X <= CAV["x1"] and bb.min.Z >= CAV["z0"] and bb.max.Z <= CAV["z1"])
    # 2 B gap and F gap
    c["B_gap"] = dict(board_B_to_cell=round(Y_B - Y_CELL1, 3), tallest_B=B_MAX, margin=round(Y_B - Y_CELL1 - B_MAX, 3), ok=Y_B - Y_CELL1 >= B_MAX)
    c["F_face_pads"] = dict(refs=sorted(F_PADS), vhb_cut_out=bool(F_PADS), vhb_area_mm2=round(ph["vhb"].volume / VHB_T, 1),
                            reachable_assembled=False, note="F faces the lid: these pads are reachable only before the bond (or after a peel)")
    c["F_gap"] = dict(gap=round(Y_LID_IN - Y_F, 3), vhb=VHB_T, slack=round(Y_LID_IN - Y_F - VHB_T, 3), ok=Y_LID_IN - Y_F >= VHB_T)
    # 3 SW1 in its pocket
    c["SW1_pocket"] = dict(pocket=[POCKET["dx"], POCKET["dz"]], need_skeptic=[4.1, 2.9], pads=list(SW1["pads"]),
                           ok=POCKET["dx"] >= 4.1 and POCKET["dz"] >= 2.9, **switch_stack())
    # 4 duct axis vs board hole
    c["duct"] = duct_offsets()
    # 5 stowage
    zb, zc = stowage_zone()
    free_b = (zb - t - lid).volume
    free_c = (zc - t - lid - ph["cell"]).volume
    c["stowage"] = dict(behind_board_mm3=round(free_b, 1), behind_cell_mm3=round(free_c, 1), total_mm3=round(free_b + free_c, 1),
                        zone_len_x=round(CAV["x1"] - PCB["x1"], 2), need_mm3=[107, 142], need_src="miniaturization-prelim.md MZM-01.stowage",
                        ok=free_b + free_c >= 142)
    # 6 envelope vs the size model
    body_v = outer_body().volume
    plate_v = plate(PLATE_PTS, Y_OUT, PLATE_T, 0.3).volume
    top_v = top_concept().volume
    pred = scenario("MZ-2", board_H=12.0, board_L=PCB_L, y_bgap=B_GAP, y_fgap=F_GAP, lid_wall=LID_T, s_fixed=0.8, dock="flat_tails")
    env = body_v + plate_v + top_v
    c["envelope"] = dict(body_mm3=round(body_v, 1), plate_mm3=round(plate_v, 1), top_spine_mm3=round(top_v, 1), total_mm3=round(env, 1),
                         size_model_live=pred["v_env"], size_model_doc=6259, delta_mm3=round(env - 6259, 1),
                         T=round(Y_TOP - Y_IN, 2), L=X1 - X0, H=round(H, 2), belly=round(BELLY_D, 2), model_body=pred["v_body"])
    c["volumes"] = dict(tub=round(t.volume, 1), lid=round(lid.volume, 1), puck=round(pk.volume, 2))
    c["printable"] = {n: dict(solids=len(s.solids()), valid=bool(s.is_valid)) for n, s in (("tub", t), ("lid", lid), ("puck", pk))}
    print(json.dumps(c, indent=1))
    (OUT / "checks.json").write_text(json.dumps(c, indent=1))
    # parts.json follows render_final.py (materials from its MATS, explode offsets in mm): blender -b -P hw/mech/render_final.py -- hw/mech/out/r2
    mats = {"cell": "cell", "pcb": "pcb", "vhb": "silicone", "parts_B": "chips", "u2_mic": "chips", "sw1": "metal", "dock": "metal", "skin": "silicone"}
    expl = {"tub": (0, 0, 0), "cell": (0, 3, 0), "dock": (0, 0, -6), "pcb": (0, 9, 0), "parts_B": (0, 9, 0), "u2_mic": (0, 9, 0), "sw1": (0, 9, 0),
            "vhb": (0, 11, 0), "puck": (0, 13, 0), "lid": (0, 14, 0), "skin": (0, 16, 0)}
    parts = {"tub": (t, "body"), "lid": (lid, "armour"), "puck": (pk, "metal"), **{k: (v, mats[k]) for k, v in ph.items()}}
    info = {}
    for k, (s, m) in parts.items():
        export_stl(s, str(OUT / f"{k}.stl"), tolerance=0.01, angular_tolerance=0.1)
        info[k] = {"mat": m, "explode": expl[k]}
    for L in PUCK_KIT:                       # selective-fit kit: exported, not part of the assembly list
        export_stl(puck(L), str(OUT / f"puck_L{L:.2f}.stl"), tolerance=0.01, angular_tolerance=0.1)
    (OUT / "parts.json").write_text(json.dumps(info, indent=1))
    section_png({"tub": t, "lid": lid, "pcb": ph["pcb"], "cell": ph["cell"], "dock": ph["dock"], "vhb": ph["vhb"], "sw1": ph["sw1"], "puck": pk,
                 "u2_mic": ph["u2_mic"], "skin": ph["skin"]}, c)
    plan_png(c)


# ---------------------------------------------------------------- section plot (dark, tools/plotstyle.py)
def _section(solid, c, axis="Z"):
    hs = box(0, 100, -10, 40, -40, c) if axis == "Z" else box(0, c, -10, 40, -40, 40)
    cut = solid & hs
    return [f for f in cut.faces() if abs(getattr(f.center(), axis) - c) < 1e-5 and abs(abs(getattr(f.normal_at(), axis)) - 1) < 1e-6]


def _draw(ax, secs, col, uv):
    from matplotlib.collections import PolyCollection
    for k, faces in secs.items():
        for f in faces:
            vs, tris = f.tessellate(0.01, 0.2)
            polys = [[(getattr(vs[i], uv[0]), getattr(vs[i], uv[1])) for i in tri] for tri in tris]
            ax.add_collection(PolyCollection(polys, facecolors=col[k], edgecolors="face", linewidths=0.3, alpha=1.0))
            for e in f.edges():
                pts = [e.position_at(u) for u in [i / 16 for i in range(17)]]
                ax.plot([getattr(p, uv[0]) for p in pts], [getattr(p, uv[1]) for p in pts], color="#e8e8e5", lw=0.35)


def section_png(solids, c):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    sys.path.insert(0, str(ROOT / "tools"))
    import plotstyle
    plotstyle.apply()
    S = plotstyle.SERIES
    col = {"tub": "#6b7280", "lid": "#9aa3b2", "pcb": S[2], "cell": S[1], "vhb": S[3], "sw1": S[6], "puck": S[4], "u2_mic": S[0], "skin": S[5], "dock": S[7]}
    zc = MIC[1]
    secs = {k: _section(s, zc) for k, s in solids.items()}
    fig = plt.figure(figsize=(15, 8.8))
    gs = fig.add_gridspec(2, 3, height_ratios=[1.0, 1.25], width_ratios=[1.0, 1.0, 0.85])
    axes = [fig.add_subplot(gs[0, :]), fig.add_subplot(gs[1, 0]), fig.add_subplot(gs[1, 1])]
    ax4 = fig.add_subplot(gs[1, 2])
    ax4.set_axisbelow(True)
    _draw(ax4, {k: _section(s, MIC[0], "X") for k, s in solids.items()}, col, ("Y", "Z"))
    ax4.axhline(MIC[1], color=S[0], lw=0.6, ls="--")
    ax4.set_xlim(3.6, 15.2)
    ax4.set_ylim(Z_BELLY - 0.4, Z1 + 0.4)
    ax4.set_aspect("equal")
    ax4.set_title(f"Section x = {MIC[0]:.2f} (through the duct)", fontsize=10)
    ax4.set_xlabel("pod y (mm, out)")
    ax4.set_ylabel("pod z (mm, up)")
    ax4.annotate("long edges free\n(0.45 each side)", xy=(12.3, PCB["z1"] + 0.15), fontsize=7, color=plotstyle.TEXT, ha="center")
    views = [((28.5, 68.5), (3.6, 15.4), "Section z = %.2f (board centre line: mic duct and SW1)" % zc),
             ((MIC[0] - 2.6, MIC[0] + 3.4), (9.8, 15.0), "Mic duct: bore D1.0 + VHB hole -> board hole D0.6"),
             ((SW[0] - 3.2, SW[0] + 3.2), (9.8, 15.0), "SW1 pocket, puck, skin")]
    for ax, (xl, yl, title) in zip(axes, views):
        ax.set_axisbelow(True)
        _draw(ax, secs, col, ("X", "Y"))
        ax.axvline(MIC[0], color=S[0], lw=0.6, ls="--")
        ax.axvline(SW[0], color=S[6], lw=0.6, ls="--")
        ax.set_xlim(*xl)
        ax.set_ylim(*yl)
        ax.set_aspect("equal")
        ax.set_title(title, fontsize=10)
        ax.set_xlabel("pod x (mm, front -> rear)")
        ax.set_ylabel("pod y (mm, out)")
    ax = axes[0]
    for k in col:
        ax.plot([], [], color=col[k], lw=6, label=k)
    fig.legend(loc="lower center", fontsize=8, ncol=10, frameon=False)
    box_kw = dict(facecolor=plotstyle.SURFACE, alpha=0.85, edgecolor="none")
    s = c["stowage"]
    ax.annotate(f"stowage {s['behind_board_mm3']:.0f} + {s['behind_cell_mm3']:.0f} mm3", xy=(PCB["x1"] + 0.5, 12.0), fontsize=8, color=plotstyle.TEXT)
    ax.annotate(f"x-stop (front skirt wall), gap {X_STOP_GAP}", xy=(CAV['x0'] + 0.3, 11.3), fontsize=7, color=plotstyle.TEXT_2)
    d = c["duct"]
    axes[1].annotate(f"offset nominal {d['nominal']}, worst with gauge pin {d['worst_with_gauge_pin']} (limit {d['limit_R_ACO_P5']})",
                     xy=(MIC[0] - 2.5, 10.0), fontsize=7, color=plotstyle.TEXT, bbox=box_kw)
    sw = c["SW1_pocket"]
    axes[2].annotate(f"puck {sw['puck_L']} (kit {sw['puck_kit'][0]}-{sw['puck_kit'][-1]}); gap: fixed worst {sw['fixed_worst']}, selective fit {sw['selective_fit']}",
                     xy=(SW[0] - 3.1, 10.0), fontsize=7, color=plotstyle.TEXT, bbox=box_kw)
    e = c["envelope"]
    fig.suptitle(f"Pod shell r2 (MZ-2): envelope {e['total_mm3']:.0f} mm3 vs size model {e['size_model_doc']} | T {e['T']} | board 30x12 hung from the lid on VHB",
                 fontsize=11, color=plotstyle.TEXT)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(OUT / "section.png", dpi=160)
    plt.close(fig)


def plan_png(c):
    """Plan view (x-z, seen from outside through the lid): board, parts, mic, SW1 pocket, dock, stowage, seam keys."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, FancyBboxPatch, Rectangle
    import yaml
    sys.path.insert(0, str(ROOT / "tools"))
    import plotstyle
    plotstyle.apply()
    S, T2 = plotstyle.SERIES, plotstyle.TEXT_2
    fig, ax = plt.subplots(figsize=(13, 6.4))
    ax.set_axisbelow(True)

    def rect(x0, x1, z0, z1, **kw):
        ax.add_patch(Rectangle((x0, z0), x1 - x0, z1 - z0, **kw))

    rect(X0, X1, Z0, Z1, fc="none", ec="#9aa3b2", lw=1.2)
    rect(X0, X_BELLY, Z_BELLY, Z0, fc="none", ec="#9aa3b2", lw=1.2)
    rect(CAV["x0"], CAV["x1"], CAV["z0"], CAV["z1"], fc="none", ec="#6b7280", lw=0.8, ls="--")
    rect(CELL["x0"], CELL["x1"], CELL["z0"], CELL["z1"], fc=S[1], alpha=0.18, ec=S[1], lw=0.8, label="cell (behind the board)")
    rect(DOCK["x0"], DOCK["x1"], DOCK["z0"], DOCK["z1"], fc=S[7], alpha=0.35, ec=S[7], lw=0.8, label="dock target (belly)")
    ax.add_patch(FancyBboxPatch((PCB["x0"] + PCB_R, PCB["z0"] + PCB_R), PCB_L - 2 * PCB_R, PCB_H - 2 * PCB_R,
                                boxstyle=f"round,pad={PCB_R}", fc=S[2], alpha=0.25, ec=S[2], lw=1.2, label="board 30 x 12 (B parts face away)"))
    rect(PCB["x0"] + PAD_ZONE[0], PCB["x1"], PCB["z0"], PCB["z1"], fc="none", ec=S[3], lw=1.0, ls=":", label="rear wire pads (B)")
    rect(PCB["x1"], CAV["x1"], CAV["z0"], CAV["z1"], fc=S[3], alpha=0.12, ec="none", label=f"stowage {c['stowage']['total_mm3']:.0f} mm3")
    pl = yaml.safe_load((ROOT / "hw/pod/draft_r2/placement.yaml").read_text())
    for ref, v in pl.items():
        if not isinstance(v, list) or len(v) < 4:
            continue
        x, z = bpt(v[0], v[1])
        ax.plot(x, z, "o" if v[3] == "B" else "s", ms=2.2 if v[3] == "B" else 4, color=S[2] if v[3] == "B" else S[6],
                label=None)
        if ref in ("U1", "U2", "U3", "U4", "L1", "Q1", "Q2", "SW1", "J1", "J5"):
            ax.annotate(ref, (x, z), xytext=(2, 2), textcoords="offset points", fontsize=7, color=plotstyle.TEXT)
    rect(SW[0] - POCKET["dx"] / 2, SW[0] + POCKET["dx"] / 2, SW[1] - POCKET["dz"] / 2, SW[1] + POCKET["dz"] / 2, fc="none", ec=S[6], lw=1.0, label="SW1 pocket 4.3 x 3.1")
    ax.add_patch(Circle(SW, SKIN_D / 2, fc="none", ec=S[5], lw=0.8, label="skin recess D4.6"))
    ax.add_patch(Circle(MIC, DUCT_D / 2, fc=S[0], ec=S[0], lw=0.8, label="duct D1.0 (bore + VHB hole)"))
    ax.add_patch(Circle(MIC, MIC_HOLE_D / 2, fc=plotstyle.SURFACE, ec=S[0], lw=0.6))
    ax.add_patch(Circle(MIC, HEX_R, fc="none", ec=S[0], lw=0.6, ls=":"))
    t = TONGUE_W
    runs = [(X0 + CORNER_KEEP, X1 - CORNER_KEEP, CAV["z1"], CAV["z1"] + t), (CAV["x1"], CAV["x1"] + t, Z0 + CORNER_KEEP, Z1 - CORNER_KEEP),
            (X_BELLY + CORNER_KEEP - 1.0, X1 - CORNER_KEEP, CAV["z0"] - t, CAV["z0"]), (CAV["x0"] - t, CAV["x0"], CAV["z0"] + 0.4, Z1 - CORNER_KEEP),
            (X0 + CORNER_KEEP, X_BELLY - 0.4, CAV["z0"], CAV["z0"] + STEP_H)]
    for i, (xa, xb, za, zb) in enumerate(runs):
        rect(xa, xb, za, zb, fc="#e8e8e5", ec="none", alpha=0.7, label="seam keys (tub tongue)" if i == 0 else None)
    ax.plot([X0, X_BELLY], [CAV["z0"], CAV["z0"]], color=S[4], lw=0.8, ls="-.", label="belly seam step (z -8.9)")
    ax.annotate("x-stop: front skirt wall\n0.25 ahead of the board", (CAV["x0"], PCB["z1"] - 1.0), xytext=(-60, 30), textcoords="offset points",
                fontsize=7, color=T2, arrowprops=dict(arrowstyle="-", color=T2, lw=0.6))
    ax.annotate("long edges free, 0.45 to the wall", (41.0, PCB["z1"] - 0.9), fontsize=7, color=T2)
    ax.set_xlim(X0 - 3, X1 + 1)
    ax.set_ylim(Z_BELLY - 1, Z1 + 1.5)
    ax.set_aspect("equal")
    ax.set_xlabel("pod x (mm, front -> rear)")
    ax.set_ylabel("pod z (mm, up)")
    d, sw = c["duct"], c["SW1_pocket"]
    ax.set_title(f"Shell r2 plan, seen through the lid | duct offset worst {d['worst_with_gauge_pin']} with gauge pin (limit {d['limit_R_ACO_P5']}) | "
                 f"puck selective fit gap {sw['selective_fit']}", fontsize=10)
    ax.plot([], [], "o", ms=3, color=S[2], label="B part (toward the cell)")
    ax.plot([], [], "s", ms=4, color=S[6], label="F: SW1 + bare TP1-TP6")
    if F_PADS:
        r = TP_PAD_D / 2 + TP_CUT_MARGIN
        xs = [bpt(*xy)[0] for xy in F_PADS.values()]
        zs = [bpt(*xy)[1] for xy in F_PADS.values()]
        rect(min(xs) - r, max(xs) + r, min(zs) - r, max(zs) + r, fc="none", ec=S[6], lw=0.8, ls="--", label="VHB cut-out over F test pads")
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0), fontsize=7, frameon=False, labelcolor=plotstyle.TEXT)
    fig.tight_layout()
    fig.savefig(OUT / "plan.png", dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    main()
