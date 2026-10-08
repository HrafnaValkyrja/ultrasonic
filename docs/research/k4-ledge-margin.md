# K4 ledge VHB margin (2026-10-08)
src: hw/mech/dims_k4.py (LEDGE_W 0.5, inset 0.2, POST_PRINT_GAP 0.5875, POST_CHAIN_LIN); ECR-0023 add.2/3; 3M VHB TDS rev 2024-09 (85 kPa dynamic design factor, datasheet-provenance.md).

## 1. Is gap <= 0.03 realistic?
- Add.3 (supersedes the shim fit) removed the 0.03 criterion: post printed short, air gap 0.05..1.125 mm at every corner, filled by epoxy dab bonded at zero gap. Gap ~0 by design; the print chain (+-0.54 linear) no longer matters.
- Residual risk is the fill, not the gap: voids/under-fill, epoxy shrink (FEM: stiff VHB E 2 fails at 2 % shrink for fill t >= 0.6 mm: 92-157 kPa), Kapton peel layer debond, and fill thickness up to 1.125 mm. Epoxy shrink is [A], bench-unverified (ECR open item).
- If the fill under-fills or shrinks, load returns to the ledge: 104 kPa mean (113-187 peak) vs 85.

## 2. Passing without the post (2 N)
- Mean-stress area for 85 kPa: 2/0.085 = 23.5 mm2; with 1.5x margin 35 mm2. Current 19.2 (104 kPa mean).
- FEM peak is 1.1-1.8x the mean (pocket-edge concentration), so peak-based need is ~45-65 mm2 [A, scaled].
- Board 15.55 x 12.05: perimeter 55.2 mm; a 0.5 band over the full perimeter is only 27.6 mm2, before M courtyard/duct/pocket exclusions. 35 mm2 needs ~0.65 mm band all round: does not fit with the existing exclusions (ledge_check bands), and the board edge is also the lid-face part courtyard limit. Widening is not a clean fix.
- Tape grade: no stronger grade at 0.25 mm known to me; thicker foam grades lose lid clearance (F_GAP). Not verified; no source fetched.

## Verdict
Real but bounded risk: only if the epoxy fill fails. Best fix: keep the post + epoxy (add.3) and gate it with a bench test (shrink, voids, 600k presses, MZV-11), spec fill t <= 0.3 mm (fill dab sized, post printed closer, less air gap) to cover stiff VHB. Do not rely on widening the ledge.
