# OWNER SIZE PRIORITY (2026-10-03 ~01:20 local, spec O27) - READ FIRST, it ranks every measure in this folder
priority: [1. THIN (pod thickness off the temple / the glasses arm), 2. SHORT (pod height, vertical), 3. length LAST]
length: "may stay as long as today's pod (within the current dimension): it sits along the glasses arm"
thickness: "must not be thick: a thick pod is a brick"
consequences_for_ranking:
  - "score measures by mm of THICKNESS saved first, then mm of HEIGHT, then volume; a measure that saves volume by adding thickness is a regression"
  - "cells: prefer LONG, THIN pouch/prismatic cells (e.g. ~40-45 x 8-12 x 2.5-4 mm) over coin cells (CoinPower 12 x 5.4 is THICKER than today's 5.3 mm pouch)"
  - "boards: long and narrow is fine; stacking parts or folding flex onto the cell only if it does not add thickness"
lead_idea_to_evaluate (Claude, 2026-10-03 01:2x):
  - "STOP STACKING: today's thickness = cell 5.3 + B gap 1.4 (mic 1.08 tall) + board 0.8 + F gap/VHB + walls (MZ-2 T 10.4 mm). Putting the board END-TO-END with the cell along the pod's length makes T ~= max(cell, board + parts) + walls (~5-6 mm with a 3 mm cell): roughly HALF the thickness."
  - "The catch: length must stay within today's pod length (~38 mm, hw/mech/shell_r2.py X0..X1), so board + cell lengths must both shrink: e.g. a ~3 x 10 x 20 mm cell (~45-60 mAh) + a ~16-18 mm board (needs the low-power budget and denser silicon: WLCSP MCU, integrated PMIC/smart-amp)."
  - "Middle option: cell under ONLY part of the board, with the mic and tall parts beside the cell (no B gap over the cell)."
  - "Evaluate thickness, height and length for each; the power lane's budget decides the cell size."
