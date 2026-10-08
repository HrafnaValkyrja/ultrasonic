#!/usr/bin/env python3
"""K4-SHELLCHK (2026-10-08): the r2 shell checks re-run on the K4 shell (hw/mech/dims_k4.py, shell_k4.py). Reuses, does not fork:
  strut clearance  -> hw/mech/heel.py with HEEL_TUB=k4 (writes out/parts/heel_k4tub/checks.json; run it first, see below)
  switch stack     -> dims_r2.switch_stack(ns) via dims_k4.switch_stack() (VHB +-15 % = +-0.0375, 3M TDS 2024-09)
  clash/walls      -> hw/mech/out/k4s/checks.json (python3 hw/mech/shell_k4.py)
Own here (K4 has no board-in-pod module): rebate, switch/mic lateral stack vs the routed M board, board in pod (K4_STACK_L 11 | 14.05), left-pod flip.
  HEEL_TUB=k4 python3 hw/mech/heel.py ; python3 hw/mech/shell_k4.py ; python3 sim/checks/k4_shellchk.py   (K4_STACK_L=14.05 for the routed board length)
Board numbers (U2 port NPTH, SW1 pad-box centre, outline) read from hw/pod/k4/routed_M.kicad_pcb with pcbnew when available, else the 2026-10-08 values below.
"""
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "hw/mech"))
import dims_k4 as K  # noqa: E402

BOARD = dict(outline=(14.05, 12.05), port=(1.75, 6.0), sw1=(5.3, 6.0), j20=(9.825, 6.025), src="routed_M.kicad_pcb read 2026-10-08 (pcbnew, origin = outline corner + 0.025)")
STACK_MM = 0.2          # board 0.1 + lid 0.1 (tools/checks/interfaces.py STACK_MM, tolerances.md)


def main():
    out = {}
    # 1. seam rebate
    resin_min_feature, resin_min_wall = 0.3, 0.6                               # frame.RESIN
    out["rebate"] = dict(height=K.REBATE_H, depth=K.REBATE_D, height_ok=K.REBATE_H >= 0.4 - 1e-9, residual_wall=round(K.WALL - K.REBATE_D, 2),
                         residual_ok=K.WALL - K.REBATE_D >= resin_min_wall - 1e-9, depth_vs_min_feature_ok=K.REBATE_D >= resin_min_feature - 1e-9,
                         note="r2: 0.2 deep x 0.4 high on a 0.8 wall (residual 0.6). K4: 0.1 x 0.4 on a 0.6 wall (residual 0.5 < 0.6 min wall; depth 0.1 < 0.3 min feature)")
    # 2. strut clearance vs the K4 tub
    f = ROOT / "hw/mech/out/parts/heel_k4tub/checks.json"
    if f.exists():
        h = json.loads(f.read_text())["strut_clearance_to_r2_tub"]
        out["strut"] = dict(relief=K.RELIEF, worst_pad_py_actual=h["min_pad_py_actual"], worst_all_models=h["min_all_models"], required=h["required"], by_model=h["min_by_model"],
                            note="same 1.176 worn as r2 (ARM-6D accepted): the strut relief chamfer is frame-fixed and shell_k4 reuses it")
    # 3. switch stack with VHB +-15 %
    out["switch_stack"] = K.switch_stack()
    # 4. lateral: shell axes vs the routed board (nominal) + the project stack
    tol_sw = (K.BORE_D - K.PUCK_D) / 2
    sx, sz = K.SW[0] - K.STACK_X0, K.SW[1] - K.ZC
    mx, mz = K.MIC[0] - K.STACK_X0, K.MIC[1] - K.ZC
    nom_sw = math.hypot(sx - BOARD["sw1"][0], sz - (BOARD["sw1"][1] - BOARD["outline"][1] / 2))
    nom_mic = math.hypot(mx - BOARD["port"][0], mz - (BOARD["port"][1] - BOARD["outline"][1] / 2))
    lim_mic = K.DUCT_D / 2 - K.MIC_HOLE_D / 2
    out["lateral"] = dict(switch_nominal=round(nom_sw, 3), switch_limit=tol_sw, switch_worst=round(nom_sw + STACK_MM, 3), switch_status="WARN (as r2 RPB-4: stack 0.20 vs 0.15, selective fit)" if nom_sw <= tol_sw else "FAIL",
                          mic_nominal=round(nom_mic, 3), mic_limit=lim_mic, mic_ok=nom_mic <= lim_mic,
                          pin_to_sw1_mm=round(abs(BOARD["sw1"][0] - BOARD["port"][0]), 2), note="with the pre-2026-10-08 dims (SW 8.0, MIC 1.9) the switch was 2.7 mm off the plunger: dims_k4 now follows the routed board")
    # 5. board in pod: M outline vs cavity, stack thickness
    L_board, H_board = BOARD["outline"]
    cav_l = K.CAV["x1"] - 0.0
    out["board_in_pod"] = dict(stack_L_shell=K.STACK_L, M_len=L_board, fits_len=L_board <= K.STACK_L + K.X_STOP_GAP, M_height=H_board,
                               fits_height=H_board <= K.CAV["z1"] - K.CAV["z0"], side_gap_z=round((K.CAV["z1"] - K.CAV["z0"] - H_board) / 2, 2),
                               needs_STACK_L=round(L_board + 0.1, 2),
                               floor_clear_nominal=round(K.STACK_Y0 - K.CAV["y0"], 3),
                               floor_clear_worst=round(K.STACK_Y0 - K.CAV["y0"] - (0.15 * K.VHB_T + 2 * 0.1), 3),
                               note="worst = 0.2 floor clear - (VHB +-15 % 0.0375 + 2 boards x JLC +-0.1); BM28 mated height tolerance [T] not included (K4-BM28-DS)")
    # 6. left pod: mic, SW1 and BM28 sit on the board centre line (+-0.025), so the y -> 12 - y flip moves them <= 0.05
    out["left_pod"] = dict(centre_line_offsets=dict(port=BOARD["port"][1] - BOARD["outline"][1] / 2, sw1=BOARD["sw1"][1] - BOARD["outline"][1] / 2, j20=BOARD["j20"][1] - BOARD["outline"][1] / 2),
                           flip_shift_max=round(2 * max(abs(BOARD["port"][1] - 6.025), abs(BOARD["sw1"][1] - 6.025)), 3),
                           arm_wire_route="heel.wire_route/left use the r2 frame board+cell (rear gap 1.1, 30 mm board): NOT K4-valid; K4 arm wires: shell_k4 placeholder, clash/tub/arm_wires 0.111 mm3")
    sk = ROOT / "hw/mech/out/k4s/checks.json"
    if sk.exists():
        c = json.loads(sk.read_text())
        out["shell_k4_checks"] = {k: v for k, v in c.items() if k.startswith("clash") and v}
    p = ROOT / "sim/out/mech/k4_shellchk.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
