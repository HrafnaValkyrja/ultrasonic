"""CAD-free dimensions of the K4 end-to-end pod shell (hw/mech/shell_k4.py). Owner O33 (2026-10-08), spec O29/O31, V8-thin-long.yaml K4, V9-k4-board.yaml B+.

    import sys; sys.path.insert(0, "hw/mech"); import dims_k4 as K     # numpy-free, no CAD kernel

Frame = shell_r2 / frame.py: x along the arm (rear face X1 fixed at 67.5 = heel E / rail / strut relief; front toward the hinge),
y outward from the temple (inner face Y_IN 4.3 on the adapter), z up. Layout along x:  [front wall | stack 11 | wire gap | cell 31 | dead zone | rear wall].
Feature numbers are the shell_r2 / dims_k1 ones (K1_DUCT=rec: hex seat R1.9 x 0.3, skin recess 0.1; KMT022 + puck button; VHB-hung board;
tub tongue / lid groove; seam rebate). What K4 changes: no belly, no dock window (see DOCK_FIT), flat 1.0 lid, 0.6 walls, board = placeholder block.
RELIEF=len (default) | lift: the strut relief (inner-bottom rear corner, frame-fixed) clips a cell that is 12.7 high in a 13.6 cavity;
'len' ends the cell at x 62.0 (dead zone behind it = stowage + heel channel, +3.8 L), 'lift' raises the cavity top 0.45 (+0.45 H) and keeps the cell to 65.8.
Owner size priority O27 (thin > short(height) > long) -> 'len' is the default.
"""
from __future__ import annotations

import os

# ---------------------------------------------------------------- pod body
Y_IN, T, WALL, LID_T = 4.3, 6.4, 0.6, 1.0
X1 = 67.5
Z0 = -9.7
RELIEF = (os.environ.get("K4_RELIEF") or "lift").strip()
if RELIEF not in ("len", "lift"):
    raise ValueError("K4_RELIEF: len | lift")
H = 14.8 + (0.45 if RELIEF == "lift" else 0.0)
Z1 = Z0 + H
ZC = (Z0 + Z1) / 2 if RELIEF == "len" else -2.3 + 0.225
Y_OUT = Y_IN + T                       # 10.7
Y_LID_IN = Y_OUT - LID_T               # 9.7 = seam plane (flat lid)
Y_SPLIT = Y_LID_IN
CAV = dict(y0=Y_IN + WALL, y1=Y_LID_IN, z0=Z0 + WALL, z1=Z1 - WALL, x1=X1 - WALL)

# ---------------------------------------------------------------- cell (Renata ICP401230UPR, V2-cells.yaml; datasheet ICP401230 V02 08/2019)
CELL_SPEC = dict(part="Renata ICP401230UPR", mAh=130, g=3.5, T=4.5, W=12.7, L=31.0)
TAPE = 0.10                            # thin transfer tape under the cell (cell swap = peel); was VHB 0.25, cut to buy lid clearance (2026-10-08, k4-dock.yaml)
LID_CLEAR_MIN = 0.2                    # cell swell allowance
DOCK = (os.environ.get("K4_DOCK") or "under").strip()   # under (default): M pad tab runs UNDER the cell in the 0.8 wire channel, pod +0 mm | front: tab ends before the cell, pod +1.5 mm at the front
if DOCK not in ("under", "front"):
    raise ValueError("K4_DOCK: under | front")
DOCK_SHIFT = 1.5 if DOCK == "front" else 0.0                       # option A (k4-dock.yaml option_A_design): pod grows 1.5 at the FRONT (stack moves forward, wire gap 0.8 -> 2.3) so the M pad tab can end 0.55 before the cell; the cell cannot move back (strut relief fill clips it past x 62.0)
CELL_X1 = 62.0 if RELIEF == "len" else CAV["x1"] - 1.1   # 65.8: heel exit (frame-fixed 65.8-66.6) stays free
CELL_X0 = CELL_X1 - CELL_SPEC["L"]
CELL_Y0 = CAV["y0"] + TAPE
CELL_Y1 = CELL_Y0 + CELL_SPEC["T"]     # 9.50: 0.20 under the lid (4.5 max envelope + swell); T stays 6.4
assert Y_LID_IN - CELL_Y1 >= LID_CLEAR_MIN - 1e-9, "cell-to-lid clearance"
CELL_Z1 = CAV["z1"] - 0.1              # cell hangs under the cavity top (0.1 clear); free channel underneath (wires)
CELL_Z0 = CELL_Z1 - CELL_SPEC["W"]
CELL_EDGE_CHAMFER = 0.15             # cell edge break at (CELL_Y0, CELL_Z1): clears the cavity R0.5 fillet (shell_k4.placeholders)
CH_UNDER = CELL_Z0 - CAV["z0"]         # wire channel under the cell

# ---------------------------------------------------------------- board stack (placeholder block for B+ two-board stack, V9-k4-board.yaml B_plus)
def routed_board_length() -> tuple[float, str]:
    """Stack length = max over the routed boards' Edge.Cuts x-extent (hw/pod/k4/routed_P|M.kicad_pcb), else placement_P|M.yaml `L`, else 11.0. K4_STACK_L overrides."""
    import re
    from pathlib import Path
    d = Path(__file__).resolve().parents[1] / "pod" / "k4"
    num = r"(-?[\d.]+)"
    best, src = None, ""
    for b in "PM":
        f, L = d / f"routed_{b}.kicad_pcb", None
        if f.exists():
            xs = []
            for m in re.finditer(r"\((?:gr_line|gr_arc|gr_rect)\s+\(start " + num + r" " + num + r"\)\s+(?:\(mid " + num + r" " + num + r"\)\s+)?\(end " + num + r" " + num + r"\)(?:(?!\(layer ).)*\(layer \"Edge\.Cuts\"\)", f.read_text(), re.S):
                g = m.groups()
                xs += [float(g[0]), float(g[4])]
            if xs:
                L = max(xs) - min(xs)
        if L is None:
            y = d / f"placement_{b}.yaml"
            m = y.exists() and re.search(r"^L:\s*([\d.]+)", y.read_text(), re.M)
            L = float(m.group(1)) if m else None
        if L is not None and (best is None or L > best):
            best, src = L, f"routed_{b}"
    return (round(best, 3), src) if best else (11.0, "default")


_RB = routed_board_length()
STACK_L, STACK_H, STACK_T = float(os.environ.get("K4_STACK_L") or _RB[0]), 12.0, 3.2   # (T 3.2 = M 0.8 + gap 0.6 + P 0.8 + tallest P outer part L1 1.0; was a 4.3 placeholder) follows the router (Edge.Cuts of routed_P/M); STACK_L_SRC says where from
STACK_L_SRC = "K4_STACK_L env" if os.environ.get("K4_STACK_L") else _RB[1]
PCB_T, VHB_T = 0.8, 0.25
# ECR-0022 (2026-10-08, V9 option B_A_plus_C21_to_0402): the stack hangs on a printed ledge frame on the lid underside, VHB on its tip.
# Lid-face gap = LID_STANDOFF + VHB_T. Sized in sim/checks/k4_heights.py: tallest M lid-face part C21 0402 10 uF 0.70 max (Samsung CL05A106MP5NUNC spec sheet)
# + 0.10 margin + VHB +-0.0375 + lid print +-0.1 = 0.94 -> 0.70 ledge. Ledge band: LEDGE_W wide, inset LEDGE_INSET from the board edge, on a band free of M lid-face courtyards (shell_k4.ledge_check).
LID_STANDOFF = 0.70
LEDGE_W, LEDGE_INSET = 0.5, 0.2
DUCT_TUBE_D = 2.4                       # printed tube round the mic port bore, same height as the ledge; VHB ring on its tip (acoustic seal)
F_GAP = VHB_T + LID_STANDOFF; F_GAP_FLAT = VHB_T                          # was 0.30 (0.05 slack above the VHB); K4-SHELLCHK: slack removed so the worst-case floor clearance (VHB +-15 %, 2 boards +-0.1) is >= 0
Y_F = Y_LID_IN - F_GAP                 # 9.4 F face of the top board, bonded to the lid on VHB
Y_B = Y_F - PCB_T                      # 8.6 B face (mic U2 hangs below it)
STACK_Y1, STACK_Y0 = Y_F, Y_F - STACK_T   # 9.4 .. 5.1 (floor 4.9: 0.2 free)
X_STOP_GAP = 0.25
XB0 = CELL_X0 - DOCK_SHIFT - 0.8 - STACK_L   # DOCK_SHIFT = wire gap growth = pod length growth (both modes)
CAV["x0"] = XB0 - X_STOP_GAP
X0 = CAV["x0"] - WALL
L = X1 - X0
STACK_X0, STACK_X1 = XB0, XB0 + STACK_L
STACK_Z0, STACK_Z1 = ZC - STACK_H / 2, ZC + STACK_H / 2


def sbpt(bx, bz):
    """stack-local (x from the front edge, z from the centre line) -> pod (x, z)"""
    return STACK_X0 + bx, ZC + bz


MIC = sbpt(1.75, 0.0)                  # U2 port NPTH on routed_M.kicad_pcb: board (1.75, 6.0) from the outline corner (K4-SHELLCHK 2026-10-08; was 1.9 = K1's 1.88)
SW = sbpt(5.3, 0.0)                    # SW1 actuator = pad-bbox centre on routed_M.kicad_pcb: board (5.3, 6.0) (was 8.0, a pre-layout guess: 2.7 mm off the plunger)
U2 = dict(c=MIC, dx=2.65, dz=3.5, h=1.08)
MIC_HOLE_D = 0.65

# ---------------------------------------------------------------- lid features (K1_DUCT=rec numbers from dims_k1 / dims_r2)
DUCT_D = 1.0
HEX_R, HEX_DEPTH = 1.9, 0.3
POCKET = dict(dx=4.3, dz=3.1, top=Y_LID_IN + 0.6)
BORE_D, PUCK_D, NUB_D, NUB_H = 2.8, 2.3, 1.0, 0.10
SKIN_D, SKIN_T = 4.6, 0.1
SKIN_FLOOR = Y_OUT - SKIN_T
SW1 = dict(body=(3.0, 2.6), pads=(3.8, 2.6), h=0.65, travel=(0.05, 0.15, 0.25))   # KMT022 travel 0.15 +-0.1 (as dims_r2)
PRE_GAP = 0.07
PUCK_L = SKIN_FLOOR - PRE_GAP - (Y_F + SW1["h"])
# ECR-0023 (2026-10-08): floor post under P so the SW1 press (2 N) goes lid -> M -> BM28 -> P -> U1 top -> post -> tub floor instead of peeling the 19 mm2 ledge VHB.
# Placement (hw/pod/k4/routed_P.kicad_pcb): P's floor face (file B) is U1 (QFN48, body 7x7 at P (6.3..13.3, 1.3..8.3)) under the whole BM28 J21 line (x 6.19-13.46, y 6.0), so the only
# support that sits under the plug is the U1 body top; a post at a part-free spot (x < 4) would load the plug as a couple (13 N.mm per 2 N). Post bears on U1 top at P x 8.2, centre line.
# Rigid post = no fixed height works (floor-side tolerance chain +-0.54 linear, ~+-0.2 RSS), so it is printed at the nominal gap and fitted to a MEASURED gap POST_GAP: PET/Kapton shim on top (gap too big) or trim the top (gap too small).
POST_X = 8.2                           # board x of the post centre (U1 body 6.3..13.3; SW1 5.3; BM28 6.2..13.5)
POST_W = 2.4                           # square pad 2.4 x 2.4 on U1 top (0.35 MPa at 2 N, 1.7 MPa at 10 N)
POST_GAP = 0.0                         # ECR-0023 addendum 2: no fitting; the gap is filled at assembly by a bonded epoxy dab (was: fitted gap 0.015 post-top to U1 top (measure +-0.015): 0.000..0.030, never negative (FEM: VHB tension < 85 kPa needs gap <= 0.03 at E 0.5, <= 0.01 at E 2)
U1_H, U1_H_TOL = 0.60, 0.05            # ST DS13737 UFQFPN48 A max 0.60; +-0.05 [T]
POST_CHAIN_LIN = 0.15 * VHB_T + 4 * 0.10 + 0.05 + U1_H_TOL   # VHB + M board + P board + 2 cavity prints (floor, lid) + BM28 + U1 = linear worst case
POST_MARGIN = 0.05                                           # min air gap at the worst tolerance corner (must stay > 0: post never preloads U1)
POST_PRINT_GAP = round(POST_CHAIN_LIN + POST_MARGIN, 4)      # ECR-0023 add.2: printed SHORT by the full linear chain + margin -> gap 0.05..1.125 at every corner; filled by the cured dab (FILL_*). OLD: = POST_GAP                                    # printed at the nominal fitted gap (centres the +-chain fit range); fitted at assembly by shim (add) or trim (remove), never by guess
BM28_GAP, P_OUTER_MAX = 0.6, 1.0         # BM28 mated gap M inner face -> P inner face; tallest P outer-face part (L1)
P_OUT_Y = Y_F - 2 * PCB_T - BM28_GAP              # P file-B (floor-facing) board face
U1_TOP_Y = P_OUT_Y - U1_H                    # nominal U1 top (package max)
POST_TOP_Y = U1_TOP_Y - POST_PRINT_GAP       # printed post top (nominal U1 top minus 0.5875); the dab fills up to U1 (Kapton-covered)
POST_GAP_MAX = round(2 * POST_CHAIN_LIN + POST_MARGIN, 3)    # largest air gap to fill 1.125
FILL_VOL_MM3 = round(POST_W ** 2 * POST_GAP_MAX * 1.5, 1)    # dab volume: post top area x max gap x 1.5 (squeeze-out allowance, spreads into a 0.3 wide skirt) = 9.7 mm3 ~ 10 uL
FILL_E_MPA, FILL_SHRINK = 350.0, 0.02    # [A] cured 5-min epoxy: secant 350 MPa (2500 psi @ 5 % elong., Devcon 5 Minute data via vendor listings, searched 2026-10-08), shrink 2 % assumed; see sw1_press_fem.py fill sweep
PUCK_STEP = 0.05
PUCK_KIT = tuple(round(PUCK_L + k * PUCK_STEP, 2) for k in (-2, -1, 0, 1, 2))
TONGUE_W, TONGUE_H, GROOVE_CL, CORNER_KEEP = 0.35, 0.35, 0.05, 1.4   # tongue height 0.35 (r2: 0.5) so the 1.0 lid keeps 0.60 over the groove
REBATE_D, REBATE_H = 0.1, 0.4          # r2: 0.2; K4: 0.1 + a 0.1 inward ridge (shell_k4.seam_ridge) keeps the 0.6 residual wall

# ---------------------------------------------------------------- dock, option A (docs/research/k4-dock.yaml option_A_design; head = Xinyangze YZP0048-20048-04025-03, C5126845)
# 4 castellated gold half-hole pads on the M tab edge (pitch 2.5 = head pogo pitch) seen through 4 belly windows + 2 N52 discs 2.5 x 1.0 in bossed belly pockets.
# [T] = inferred, to be calipered / compassed on a head sample: HEAD_MAG_PITCH, pogo stroke, polarity.
DOCK_YC = Y_F - PCB_T / 2          # head/pad/magnet centre line = M mid-plane (pads are the 0.8 M edge), derived from the board stack (K4-DOCK-YALIGN: was a constant 6.8 before ECR-0022 moved M to 8.35). Flat belly y 5.3..9.7
DOCK_PITCH = 2.5
HEAD_MAG_PITCH = 13.2                  # [T] magnet centre-to-centre along the head's long axis (21.2 racetrack; pins span 7.5)
MAG_D, MAG_T, MAG_SKIN = 2.5, 1.0, 0.20
POCKET_D, POCKET_FIT = MAG_D + 0.1, 0.05
BOSS_D, BOSS_TOP = POCKET_D + 0.3, -8.45   # inward boss, top 0.15 under the cell/M edge (z -8.3)
MAG_X_FRONT = X0 + 2.3                    # pocket edge at 19.35 = where the 1.0 belly round starts (X0 18.35 + 1.0)
MAG_X_REAR = MAG_X_FRONT + HEAD_MAG_PITCH
DOCK_CX = MAG_X_FRONT + HEAD_MAG_PITCH / 2
PAD_X = [DOCK_CX + (i - 1.5) * DOCK_PITCH for i in range(4)]    # 23.45 .. 30.95 -> see option_A_design for the net order
WIN_W, WIN_H = 1.3, 1.2                # belly window x, y (pad half-hole 0.9 + 0.2/side)
TAB_Z_BOTTOM = -9.0                    # M tab edge, 0.1 above the cavity floor (-9.1); pad recess in the window 0.7 from the outer belly
TAB_STRIP_TOP = CELL_Z0 - 0.1            # tab part beyond the stack rear is a 0.6 high strip (z -9.0..-8.4) in the channel under the cell (cell bottom z -8.3)
TAB_X = (PAD_X[0] - WIN_W / 2 - 0.3, PAD_X[-1] + WIN_W / 2 + 0.3)
DOCK_FIT = dict(head_W=6.86, pod_T=T, head_overhang_each_side=round((6.86 - T) / 2, 2),
                note="head 21.2 x 6.86 sits on the 4.4 flat belly (fillet 1.0) and overhangs T 6.4 by 0.23/side when centred; it is centred on DOCK_YC, not on T")


# ---------------------------------------------------------------- wires (K4-HEELWIRE 2026-10-08): cell + arm, in the K4 frame
# Pads (routed boards, board x from the front edge, y from the board edge; z = ZC + (y - 6.0)): M B face J5 BAT+ (10.55, 10.9), J4 GND/cell- (10.55, 8.5), J9 NTC (1.48, 1.18),
# J7 LED+ (3.78, 8.68), J8 LED- (12.68, 6.98); P J1 OUT_A (2.28, 3.58), J2 OUT_B (1.38, 1.48). ASSUMPTION [T]: wire-pad access past the P board (P covers x<=14.0): the router must keep a
# solder window or the wires leave sideways over the board z edge; modelled as a straight run rearward at the pad's y plane.
WIRE_OD, BUNDLE_OD, WIRE_R_MIN = 0.21, 0.51, 0.5
WIRE_PADS = {"BAT+": ("M", 10.55, 10.9), "GND": ("M", 10.55, 8.5), "NTC": ("M", 1.48, 1.18), "LED+": ("M", 3.78, 8.68), "LED-": ("M", 12.68, 6.98),
             "OUT_A": ("P", 2.28, 3.58), "OUT_B": ("P", 1.38, 1.48)}
HEEL_EXIT = (66.20, 5.15, -5.50)       # heel.CH_EXIT: conductor channel mouth in the tub's inner wall (frame-fixed)
ARM_NETS = ("OUT_A", "OUT_B", "LED+", "LED-")
LANE_Z = CAV["z0"] + 0.3               # under-cell / under-stack lane (cell bottom CELL_Z0, floor CAV z0): z -8.8
LANE_Y0 = 8.85                         # lane y 8.85..9.51: above the dock bosses (y 5.4..8.2, z <= -8.45) and the strut-relief fill; the lane is below the cell (z < -8.3)


DROP_X = round(CELL_X0 - 0.14, 2)                         # drop column: between the rear magnet boss edge (x 30.80 at y 8.35, less at the lane's higher y) and the cell front face (31.0); K4-WIRE-LANE clash 0 (2026-10-08)


def wire_routes():
    """{net: [(x, y, z), ...]} centrelines. Cell leads: pad -> rear -> stack/cell gap -> cell front-end lead. Arm: pad -> stack rear -> down to the lane under the stack/cell
    -> rearward under the cell -> dead zone (rise, then in to the heel channel mouth). Rectilinear + one diagonal; bends are filleted by the caller (R >= WIRE_R_MIN)."""
    out, xr = {}, STACK_X1 + 0.4
    y_lead = CELL_Y0 + 0.8
    for n in ("BAT+", "GND"):
        _, bx, by = WIRE_PADS[n]
        x, z = STACK_X0 + bx, ZC + (by - 6.0)
        out[n] = [(x, Y_B - 0.1, z), (xr, Y_B - 0.1, z), (xr, y_lead + (0.3 if n == "GND" else 0.0), z), (CELL_X0 + 0.3, y_lead + (0.3 if n == "GND" else 0.0), z)]
    _, bx, by = WIRE_PADS["NTC"]
    out["NTC"] = [(STACK_X0 + bx, Y_B - 0.1, ZC + (by - 6.0)), (xr, Y_B - 0.1, ZC + (by - 6.0)), (xr, CELL_Y0 + 0.2, ZC + (by - 6.0)), (CELL_X0 + 0.3, CELL_Y0 + 0.2, ZC + (by - 6.0))]
    for i, n in enumerate(ARM_NETS):
        b, bx, by = WIRE_PADS[n]
        yp = Y_B - 0.1 if b == "M" else Y_B - PCB_T - 1.08 + 0.1      # P pads sit on the lower board
        x, z = STACK_X0 + bx, ZC + (by - 6.0)
        xd = DROP_X                                           # one drop column DROP_X, wires staggered in y
        yl = LANE_Y0 + 0.22 * i
        tail = ([(CELL_X1 + 1.4, yl, -7.4), (HEEL_EXIT[0] - 0.8, HEEL_EXIT[1] + 0.2 * i * 0, HEEL_EXIT[2] - 0.3 + 0.2 * i), HEEL_EXIT] if RELIEF == "len" else
                [(CELL_X1 + 0.3, yl, -7.4), (HEEL_EXIT[0] - 0.1, HEEL_EXIT[1] + 0.2 * i * 0, HEEL_EXIT[2] - 0.3 + 0.2 * i), HEEL_EXIT])   # lift: 1.1 rear gap only, rise + turn inside it
        out[n] = [(x, yp, z), (xd, yp, z), (xd, yl, z), (xd, yl, LANE_Z), (CELL_X1 + 0.3, yl, LANE_Z)] + tail
    return out


def wire_lengths():
    import math
    return {n: round(sum(math.dist(a, b) for a, b in zip(p[:-1], p[1:])), 1) for n, p in wire_routes().items()}


def switch_stack():
    """Same function as dims_r2.switch_stack (VHB +-15 % = +-0.0375 per the 3M TDS), evaluated on this module's numbers. Lazy import: dims_r2 reads the r2 board at import."""
    import dims_r2
    return dims_r2.switch_stack(globals())


# ---------------------------------------------------------------- interface facts for tools/checks/interfaces.py (K4, 2026-10-08)
# The checks read the M board (mic U2, SW1, lid-face parts, VHB) and the stack footprint; P sits under M and is checked by its own netlist.
def interface_facts():
    """Same shape as dims_r2.interface_facts (pod frame mm). PCB = the M board footprint in the stack; F_PADS none (K4 M has no bare F-face test pads)."""
    pcb = dict(x0=STACK_X0, x1=STACK_X1, y0=Y_B, y1=Y_F, z0=STACK_Z0, z1=STACK_Z1)
    return dict(PCB=pcb, CAV=dict(CAV), MIC=MIC, SWITCH=SW, ZC=ZC, X0=X0, X1=X1, Z0=Z0,
                CELL=dict(x0=CELL_X0, x1=CELL_X1, y0=CELL_Y0, y1=CELL_Y1, z0=CELL_Z0, z1=CELL_Z1),
                mic_port_d=DUCT_D, mic_hole_d=MIC_HOLE_D, switch_bore_d=BORE_D, plunger_head_d=PUCK_D,
                bands=dict(B=Y_B - (Y_IN + WALL), F=F_GAP),
                pocket=dict(ref="SW1", centre=SW, dx=POCKET["dx"], dz=POCKET["dz"], band=POCKET["top"] - Y_F),
                vhb=dict(t=VHB_T, inset=0.2, duct_d=DUCT_D, tp_cut_r=0.9, f_pads={}),
                x_stop_gap=X_STOP_GAP,
                # ECR-0022: VHB only on the notched lid ledge tip (not full-face); limits = sw1_press_fem.py (2 N press, 85 kPa 3M dynamic factor) + ECR-0023 post (VHB < 85 kPa needs gap <= 0.03)
                ledge=dict(w=LEDGE_W, inset=LEDGE_INSET, h=LID_STANDOFF, tube_d=DUCT_TUBE_D, press_N=2.0, limit_kPa=85.0, post_gap=POST_GAP, post_gap_max=0.03, clear=0.1),
                # B side = the whole stack under the lid-face VHB: M + BM28 gap + P + tallest P outer part must fit Y_F -> tub floor; M inner-face parts live in the gap (U2 also in the P notch)
                bstack=dict(m=PCB_T, gap=BM28_GAP, p=PCB_T, l1=P_OUTER_MAX, avail=Y_F - CAV["y0"], notch_refs=("U2",)))


def duct_offsets():
    """Bore axis vs board-hole axis (as dims_r2.duct_offsets; MIC is read from the routed M board, so nominal is 0 by construction)."""
    import math
    tol = dict(print_bore_pos=0.05, bore_ream=(1.00, 1.02), pin_body=0.98, pin_tip=0.50, pin_runout=0.02, hole=(0.60, 0.70), outline_to_hole=0.20)
    pin_r = (tol["bore_ream"][1] - tol["pin_body"]) / 2 + (tol["hole"][1] - tol["pin_tip"]) / 2 + tol["pin_runout"]
    stop_dx = X_STOP_GAP + tol["outline_to_hole"] + tol["print_bore_pos"]
    stop_dz = (CAV["z1"] - CAV["z0"] - STACK_H) / 2 + tol["outline_to_hole"] + tol["print_bore_pos"]
    lim = DUCT_D / 2 - MIC_HOLE_D / 2
    walls_free = X_STOP_GAP > tol["outline_to_hole"] and (CAV["z1"] - CAV["z0"] - STACK_H) / 2 > tol["outline_to_hole"]
    return dict(limit_R_ACO_P5=round(lim, 3), nominal=0.0, worst_walls_only=round(math.hypot(stop_dx, stop_dz), 3),
                worst_walls_only_pass=math.hypot(stop_dx, stop_dz) <= lim, worst_with_gauge_pin=round(pin_r, 3),
                worst_with_gauge_pin_pass=pin_r <= lim + 1e-9, walls_never_fight_pin=walls_free, tolerances=tol)


# aliases the generic readers (hw/mech/frame.py pod_facts, tools/checks/interfaces.py) expect from a dims module
W = WALL
PCB = dict(x0=STACK_X0, x1=STACK_X1, y0=Y_B, y1=Y_F, z0=STACK_Z0, z1=STACK_Z1)       # the M board footprint in the stack
CELL = dict(x0=CELL_X0, x1=CELL_X1, y0=CELL_Y0, y1=CELL_Y1, z0=CELL_Z0, z1=CELL_Z1)
