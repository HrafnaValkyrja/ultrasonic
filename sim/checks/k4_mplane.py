#!/usr/bin/env python3
"""K4-DOCS-MPLANE (2026-10-08): does the M board's mid-plane (pad edge) line up with the dock windows and magnets at y = DOCK_YC after ECR-0022?

    source tools/env.sh && python3 sim/checks/k4_mplane.py     (reads hw/mech/dims_k4.py only; imports nothing heavy)

ECR-0021 pinned the M mid-plane at y 6.8 (pads = the 0.8 mm M edge, windows 1.2 high, magnets on y 6.8). ECR-0022 then hung the stack on the lid ledge
(F_GAP = VHB 0.25 + ledge 0.70): M is the lid-side board, F face Y_F, B face Y_F - 0.8. Mid-plane = Y_F - 0.4.
"""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hw/mech"))
import dims_k4 as K
mid = K.Y_F - K.PCB_T / 2
pad = (K.Y_F - K.PCB_T, K.Y_F)                       # M edge = pad face, y extent
win = (K.DOCK_YC - K.WIN_H / 2, K.DOCK_YC + K.WIN_H / 2)
ov = max(0.0, min(pad[1], win[1]) - max(pad[0], win[0]))
out = dict(Y_F=round(K.Y_F, 3), M_mid_plane=round(mid, 3), M_pad_y=[round(x, 3) for x in pad], DOCK_YC=K.DOCK_YC, window_y=[round(x, 3) for x in win],
           offset_mm=round(mid - K.DOCK_YC, 3), pad_window_overlap_mm=round(ov, 3), pass_=ov >= 0.5 * K.PCB_T)
out["belly_flat_y"] = [5.3, 9.7]
out["head_6p86_span_if_centred_on_mid"] = [round(mid - 3.43, 2), round(mid + 3.43, 2)]
out["pod_y"] = [K.Y_IN, K.Y_OUT]
print(json.dumps(out, indent=1)); sys.exit(0 if out["pass_"] else 1)
