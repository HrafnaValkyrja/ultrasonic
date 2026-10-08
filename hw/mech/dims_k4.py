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
RELIEF = (os.environ.get("K4_RELIEF") or "len").strip()
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
TAPE = 0.25                            # VHB under the cell (cell swap = peel)
CELL_X1 = 62.0 if RELIEF == "len" else CAV["x1"] - 1.1   # 65.8: heel exit (frame-fixed 65.8-66.6) stays free
CELL_X0 = CELL_X1 - CELL_SPEC["L"]
CELL_Y0 = CAV["y0"] + TAPE
CELL_Y1 = CELL_Y0 + CELL_SPEC["T"]     # 9.65: 0.05 under the lid for the 4.5 max envelope (swelling unknown)
CELL_Z1 = CAV["z1"] - 0.1              # cell hangs under the cavity top (0.1 clear); free channel underneath (wires)
CELL_Z0 = CELL_Z1 - CELL_SPEC["W"]
CH_UNDER = CELL_Z0 - CAV["z0"]         # wire channel under the cell

# ---------------------------------------------------------------- board stack (placeholder block for B+ two-board stack, V9-k4-board.yaml B_plus)
STACK_L, STACK_H, STACK_T = 11.0, 12.0, 4.3
PCB_T, F_GAP, VHB_T = 0.8, 0.30, 0.25
Y_F = Y_LID_IN - F_GAP                 # 9.4 F face of the top board, bonded to the lid on VHB
Y_B = Y_F - PCB_T                      # 8.6 B face (mic U2 hangs below it)
STACK_Y1, STACK_Y0 = Y_F, Y_F - STACK_T   # 9.4 .. 5.1 (floor 4.9: 0.2 free)
X_STOP_GAP = 0.25
XB0 = CELL_X0 - 0.8 - STACK_L          # 0.8 wire/bend gap stack rear -> cell front
CAV["x0"] = XB0 - X_STOP_GAP
X0 = CAV["x0"] - WALL
L = X1 - X0
STACK_X0, STACK_X1 = XB0, XB0 + STACK_L
STACK_Z0, STACK_Z1 = ZC - STACK_H / 2, ZC + STACK_H / 2


def sbpt(bx, bz):
    """stack-local (x from the front edge, z from the centre line) -> pod (x, z)"""
    return STACK_X0 + bx, ZC + bz


MIC = sbpt(1.9, 0.0)                   # port at the hinge end (F1); same offset from the front edge as the K1 board (1.88)
SW = sbpt(8.0, 0.0)                    # button toward the stack rear (K1: board x 18.5 of 30)
U2 = dict(c=MIC, dx=2.65, dz=3.5, h=1.08)
MIC_HOLE_D = 0.65

# ---------------------------------------------------------------- lid features (K1_DUCT=rec numbers from dims_k1 / dims_r2)
DUCT_D = 1.0
HEX_R, HEX_DEPTH = 1.9, 0.3
POCKET = dict(dx=4.3, dz=3.1, top=Y_LID_IN + 0.6)
BORE_D, PUCK_D, NUB_D, NUB_H = 2.6, 2.3, 1.0, 0.10
SKIN_D, SKIN_T = 4.6, 0.1
SKIN_FLOOR = Y_OUT - SKIN_T
SW1 = dict(body=(3.0, 2.6), pads=(3.8, 2.6), h=0.65)
PRE_GAP = 0.07
PUCK_L = SKIN_FLOOR - PRE_GAP - (Y_F + SW1["h"])
TONGUE_W, TONGUE_H, GROOVE_CL, CORNER_KEEP = 0.35, 0.35, 0.05, 1.4   # tongue height 0.35 (r2: 0.5) so the 1.0 lid keeps 0.60 over the groove
REBATE_D, REBATE_H = 0.1, 0.4          # r2: 0.2; a 0.6 wall keeps 0.5

# ---------------------------------------------------------------- dock (YZT0675, sub-dock-usb.md) - does not fit; see DOCK_FIT
DOCK_TARGET = (21.2, 6.86, 2.8)
DOCK_FIT = dict(target_w=DOCK_TARGET[1], pod_T=T, fits_across_T=DOCK_TARGET[1] <= T - 0.0,
                note="YZT0675 is 6.86 wide, pod T is 6.4: it cannot sit flush in the bottom, rear or any face of this pod. OPEN: owner/ECR (rotate on edge into the lid, shorter target, or pads only).")
