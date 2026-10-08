"""CAD-free dimensions of the Phase-2 pod shell (hw/mech/shell_r2.py, ECR-0018): the single source of its numbers.

    import sys; sys.path.insert(0, "hw/mech"); import dims_r2 as D     # numpy only (via frame.py); no build123d
shell_r2.py builds the solids from these; tools read them without loading the CAD kernel (tools/current.py `shell_dims`):
tools/checks/interfaces.py (mic port, switch, outline, heights, VHB face, frame), sim/acoustics/geometry.py (duct stack).
Split out of shell_r2.py on 2026-10-07 with every value unchanged (verified: all upper-case names identical before/after).
Board-derived values (U2_XY, MIC_XY, F_PADS) are read from the Phase-2 routed board and placement.yaml at import.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import frame as F  # noqa: E402

# Variant hook (2026-10-07, K1 for packet Q1): a variant module (hw/mech/dims_k1.py) execs THIS file with a dict
# _OVERRIDES in its namespace; only the names below can be overridden and every derived value follows. Phase 2: empty.
_OVR = dict(globals().get("_OVERRIDES") or {})
_USED = set()


def _o(name, default):
    if name in _OVR:
        _USED.add(name)
        return _OVR[name]
    return default


# ---------------------------------------------------------------- stack-up (pod frame, mm; x fwd->rear, y out, z up)
W = _o("W", 0.8)
CELL_L, CELL_W = _o("CELL_L", 35.0), _o("CELL_W", 12.0)     # Renata ICP501233PA-02 envelope 35 x 12 (x 5.3)
X1 = 67.5                              # rear face: fixed to the frame (heel E, rail, strut relief); a shorter cell shortens the FRONT
REAR_GAP = 1.1 + (0.8 - W)             # 1.1; the cell's rear end stays at x 65.6 (heel exit hole 65.8-66.6 is frame-fixed), so a
                                       # thinner rear wall widens the gap instead of pushing the cell onto the exit (k1t, 2026-10-07)
X0 = X1 - (2 * W + 0.3 + CELL_L + REAR_GAP)  # 29.5: L 38.0 = 2 x 0.8 + 0.3 + cell 35 + rear gap 1.1 (size model)
Y_IN = F.Y_IN                          # 4.3 inner face on the adapter (frame.py)
TAPE = 0.3                             # cell VHB gap (0.25 tape)
CELL_T, B_GAP, PCB_T, F_GAP = _o("CELL_T", 5.3), 1.4, 0.8, 0.30
LID_T, PLATE_T = _o("LID_T", 0.8), _o("PLATE_T", 0.7)
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
H = 2 * W + CELL_W + 0.8 + 0.1         # 14.5: cell 12 + s_fixed 0.8 under + 0.1 over (size model)
Z1 = Z0 + H                            # 4.8
BELLY_D = 2.8 + 0.85 - (W + 0.8)       # 2.05: target 2.8 + flat tails 0.85 - (wall + slack under the cell)
Z_BELLY = Z0 - BELLY_D                 # -11.75
X_BELLY = X0 + 25.5                    # 55.0 (DOCKS['flat_tails'].L)
CAV = dict(x0=X0 + W, x1=X1 - W, y0=Y_IN + W, y1=Y_LID_IN, z0=Z0 + W, z1=Z1 - W)
BAY = dict(x0=X0 + W, x1=X_BELLY - W, z0=Z_BELLY + W, z1=CAV["z0"])
CELL = dict(x0=CAV["x0"] + 0.3, x1=CAV["x0"] + 0.3 + CELL_L, y0=Y_CELL0, y1=Y_CELL1, z0=CAV["z0"] + 0.8, z1=CAV["z0"] + 0.8 + CELL_W)

# ---------------------------------------------------------------- board (hw/pod/draft_r2/placement.yaml)
PCB_L, PCB_H, PCB_R = 30.0, 12.0, 1.0
X_STOP_GAP = 0.25                      # coarse x-stop: front skirt wall to board front edge
PCB = dict(x0=CAV["x0"] + X_STOP_GAP, y0=Y_B, y1=Y_F, z0=(CAV["z0"] + CAV["z1"]) / 2 - PCB_H / 2)
PCB["x1"], PCB["z1"] = PCB["x0"] + PCB_L, PCB["z0"] + PCB_H


def bpt(bx, by):
    """board (x, y) -> pod (x, z). Board +y = pod +z (the right pod's mirror flips it; mic and SW1 sit on y 6.0)."""
    return PCB["x0"] + bx, PCB["z0"] + by


MIC_HOLE_D = 0.65                      # SAI-15D (decided 2026-10-07): D0.65 + JLC press-fit tolerance (0.60-0.70) meets spec s8 0.6-1.0
def board_mic():
    """U2 centre and its port hole (board mm) read from the routed Phase-2 board, so the duct follows the layout."""
    import re
    f = Path(__file__).resolve().parents[1] / "pod/draft_r2/out/routed.kicad_pcb"
    s = f.read_text()
    i = s.index('"Reference" "U2"')
    blk = s[s.rfind("(footprint ", 0, i):i]
    x, y, rot = (float(v) for v in re.search(r"\(at ([\d.\-]+) ([\d.\-]+) ([\d.\-]+)\)", blk).groups())
    assert abs(rot - 90) < 1e-6, "port-hole offset below assumes U2 at rot 90"
    # 2026-10-07 (SAI-15D): read the NPTH's own local offset (0.75 since the hole moved +0.02 to clear pad 3 by 0.2075)
    j = s.index("np_thru_hole", i)
    off = float(re.search(r"\(at ([\d.\-]+) ([\d.\-]+)", s[j:j + 200]).group(2))
    return (x, y), (round(x + off, 4), y)    # board file stores the B-side local offset as (0, -0.75): hole = x + off


U2_XY, MIC_XY = board_mic()            # 2026-10-07: (2.65, 6.0) / (1.88, 6.0) after route closure v6
MIC = bpt(*MIC_XY)                     # board hole = duct axis (nominal offset 0)
SW = bpt(18.5, 6.0)
U2 = dict(c=bpt(*U2_XY), dx=2.65, dz=3.5, h=1.08)          # Knowles LGA 3.5 x 2.65, rot 90; tallest B part
SW1 = dict(body=_o("SW1_BODY", (3.0, 2.6)), pads=_o("SW1_PADS", (3.8, 2.6)), h=_o("SW1_H", 0.65), travel=_o("SW1_TRAVEL", (0.05, 0.15, 0.25)))  # KMT022: 3.0x2.6x0.65; travel 0.15+-0.1
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
HEX_R, HEX_DEPTH = _o("HEX_R", 1.9), _o("HEX_DEPTH", 0.8)   # r1 window (mesh seat), cut down from the plate top (variant hook: duct options)
POCKET = dict(dx=_o("POCKET_DX", 4.3), dz=_o("POCKET_DZ", 3.1), top=Y_LID_IN + _o("POCKET_H", 0.6))     # SW1 pocket: 4.3 x 3.1, ceiling at y 13.8
BORE_D, PUCK_D, NUB_D, NUB_H = 2.6, 2.3, 1.0, 0.10
SKIN_D, SKIN_T = 4.6, _o("SKIN_T", 0.25)   # SKIN_T = recess depth (= skin thickness in Phase 2; a K1 option sinks a 0.25 skin only 0.1)
SKIN_FLOOR = Y_TOP - SKIN_T            # 14.45
PRE_GAP = 0.07                         # nominal puck top -> skin underside (selective fit keeps it in 0.005..0.135)
PUCK_L = SKIN_FLOOR - PRE_GAP - (Y_F + SW1["h"])        # 0.83 nominal
PUCK_STEP = 0.05
PUCK_KIT = tuple(round(PUCK_L + k * PUCK_STEP, 2) for k in (-2, -1, 0, 1, 2))   # print all 5, measure, fit one

Y_MID = (Y_IN + Y_OUT) / 2
DOCK = dict(x0=X0 + 2.0, x1=X0 + 23.2, y0=Y_MID - 3.43, y1=Y_MID + 3.43, z0=Z_BELLY, z1=Z_BELLY + 2.8)   # YZT0675 21.2 x 6.86 x 2.8
TONGUE_W, TONGUE_H, GROOVE_CL, CORNER_KEEP = 0.35, 0.5, 0.05, 1.4
STEP_H = 0.35                          # belly-step key: its top must stay below the hanging board's lower edge (sweep)


# ---------------------------------------------------------------- checks
def duct_offsets():
    """Bore axis vs board-hole axis. Tolerances: [A] assumed, verify before freeze."""
    tol = dict(
        print_bore_pos=0.05,          # [A] resin print, bore position vs any lid feature (frame.RESIN class)
        bore_ream=(1.00, 1.02),       # reamed with a 1.0 drill, +0.02 [A]
        pin_body=0.98, pin_tip=0.50, pin_runout=0.02,   # stepped gauge pin [A] (turned brass)
        hole=(0.60, 0.70),            # D0.65 ordered with JLC's press-fit tolerance +-0.05 (PCB remark); regular +0.13/-0.08 would give 0.57-0.78
        outline_to_hole=0.20,         # JLC CNC routed outline +-0.2 regular (+-0.1 precision); hole position +-0.075
        # src: jlcpcb.com/capabilities/pcb-capabilities fetched 2026-10-07 (HTML SHA-256 62ffae95727c8b4e); board 0.8 +-0.1
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


def switch_stack(ns=None):
    """Puck top -> skin underside. Negative = switch pre-pressed. Tolerances [A] (C&K gives 0.65 nominal only)
    except vhb: 3M VHB 4914 TDS (rev 2024-09, SHA-256 prefix 2fc355523c5e5dff) thickness 0.25 mm +-15 % = +-0.0375."""
    g = ns if ns is not None else globals()      # ns: a variant's dims module namespace (dims_k4.switch_stack reuses this function, 2026-10-08)
    PRE_GAP, PUCK_L, PUCK_KIT, PUCK_STEP, SW1, POCKET, Y_F, VHB_T = (g[k] for k in ("PRE_GAP", "PUCK_L", "PUCK_KIT", "PUCK_STEP", "SW1", "POCKET", "Y_F", "VHB_T"))
    t = dict(vhb=round(0.15 * VHB_T, 4), sw_h=0.05, solder_lift=(0.0, 0.05), puck_print=0.05, recess_floor=0.05, lid_face=0.03)
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


def interface_facts():
    """The facts the board interfaces rest on, in the shape tools/checks/interfaces.py uses (pod frame mm)."""
    return dict(PCB=dict(PCB), CAV=dict(CAV), MIC=MIC, SWITCH=SW, ZC=PCB["z0"] + PCB_H / 2, X0=X0, X1=X1, Z0=Z0, CELL=dict(CELL),
                mic_port_d=DUCT_D, mic_hole_d=MIC_HOLE_D, switch_bore_d=BORE_D, plunger_head_d=PUCK_D,
                bands=dict(B=B_GAP, F=F_GAP), pocket=dict(ref="SW1", centre=SW, dx=POCKET["dx"], dz=POCKET["dz"], band=POCKET["top"] - Y_F),
                vhb=dict(t=VHB_T, inset=0.2, duct_d=DUCT_D, tp_cut_r=TP_PAD_D / 2 + TP_CUT_MARGIN, f_pads=dict(F_PADS)),
                x_stop_gap=X_STOP_GAP)


_unused = set(_OVR) - _USED
if _unused:
    raise ValueError(f"dims_r2: unknown override(s) {sorted(_unused)}")
