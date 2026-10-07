# dummies: printable size-concept envelopes (V7), AI-facing

```yaml
id: MECH-DUMMIES
date: 2026-10-07
status: built + validated, not owner-tested. Implements synthesis.md §3 V7 (drastic size study). No design change: no spec/board/shell edit.
src: hw/mech/dummies.py
run: "source tools/env.sh && systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 python3 hw/mech/dummies.py  (~6 s)"
outputs:
  stl: "hw/mech/out/dummies/{MZ2,K1,K2,K3,OU4}.stl (solid) + *_ballast.stl (open-bottom pocket); gitignored (hw/mech/out/) -> regenerate locally"
  json: hw/mech/out/dummies/dummies.json (per concept frame, volumes, masses, pocket, validity)
  png: docs/diagrams/size-dummies.png (dark; side + end views to scale)
validity: "every STL = 1 build123d solid, is_valid, and the written STL is a closed oriented 2-manifold (edge count check) [run 2026-10-07]"
mounting: "SAME as shell_r2: blade.rail() dovetail (x 36-62, z centre -2.0) + catch bump on the inner face -> the existing frame adapter (blade.adapter) slides on from the front and latches. Pod frame kept (X0 29.5, Y_IN 4.3, Z0 -9.7). Heel/arm/pad NOT on the dummies (outside the envelope, identical for all concepts)."
envelope: "box L x T x H, 1.0 chamfer on all edges (shell_r2 outer_body style) + dock belly under the front. MZ2 = shell_r2.outer_body() + armour plate (real exterior). K1/K2/K3/OU4: plate off, thin dock belly 2.75 - (wall + 0.8) for 24 mm (size_budget DOCKS thin). No spine (160 mm3 styling, counted in synthesis env)."
engraving: "inner face, 0.3 deep, under the adapter: '<id> T<T>' above the rail, '<pod g> g' below it"
mass_rule: "pod g = synthesis §2 mass - pad 2.19 - adapter 0.49 (size_budget parts list); dummy is weighed WITHOUT adapter"
```

| id | T | H (+belly) | L | env synthesis mm3 | dummy env mm3 | pod target g | solid resin print g | pocket mm3 | cell (where the pocket sits) |
|---|--:|--:|--:|--:|--:|--:|--:|--:|---|
| MZ2 | 10.4 | 14.5 (+2.05) | 38.0 | 6259 | 6051 | 9.24 | 7.31 | 814 | 175 mAh, x 31-65.6 |
| K1 | 8.5 | 14.8 (+1.35) | 33.6 | 4544 | 4384 | 7.32 | 5.35 | 833 | 130 mAh, x 31-61.4 |
| K2 | 7.3 | 14.1 (+1.35) | 33.1 | 3691 | 3531 | 5.72 | 4.34 | 583 | 68 mAh, x 31-60.9 |
| K3 | 5.6 | 14.9 (+1.35) | 40.1 | 3563 | 3404 | 4.82 | 4.19 | 267 | 50 mAh FRONT [A], x 31-51.4 |
| OU4 | 5.6 | 19.2 (+1.15) | 38.0 | 4272 | 4113 | 6.22 [E] | 5.03 | 504 | 68 mAh, bottom, board strip above |

```yaml
print:
  resin (preferred, as the shell): "solid, 0.05 layers, inner face (rail side) UP, supports on the outer face/bottom only; rail + latch bump must stay clean (adapter fit 0.15/side, blade.FIT). Solid resin ~4-7 g each; cure fully."
  FDM (fallback): "0.12-0.16 layers, 100 % infill (else the mass is wrong), lying on the outer face, rail up; PETG/PLA. Dovetail wants ~0.25 clearance on FDM: if the adapter binds, sand the rail sides or reprint the adapter with blade.FIT 0.25."
  right side: "print a second copy mirrored in the slicer across the pod's y (thickness) axis; the engraving then reads backwards, which is fine"
ballast: "*_ballast.stl: pocket open on the bottom. Weigh the print, drop in steel shot / M2 nuts / cut steel strip until the scale reads the engraved g (pocket holds ~1.4x the nominal need at 4.5 g/cm3), seal with tape or a glue drop. Solid STL = size only."
wear_test (each on both frames, O26, 20-30 min, glasses on, then off/on 3x):
  - "thickness: how far it sticks out in a mirror, front and from above; does it catch hair, hood, headphone band, a pillow"
  - "height: does the top edge enter peripheral vision; does OU4's extra 4.7 mm feel worse than K3's +2 mm length"
  - "length: rear end vs the ear-open hook / ear top; front end vs the hinge and vision line"
  - "weight (ballast versions): nose-pad pressure and slip after 20 min; one side vs both sides on"
feedback_form (3 lines, one per dummy):
  - "Wearable? (yes / borderline / brick) and why in 3 words"
  - "Rank T, H, L that bothered most (e.g. H > T > L)"
  - "Biggest one I'd still accept: <id>; smallest I'd still want: <id>"
uncertain:
  - "[A] K3 cell at the front: synthesis says front or rear is free; the pocket moves the mass, the envelope is unchanged"
  - "[E] OU4 mass 8.9 g total: scaled from K2 by Claude (walls 0.8 on the larger shell +0.72 g, smaller board -0.22 g); not in synthesis"
  - "[E] every target mass is size_budget [E]; heel, arm and pad (2.19 g, at the ear) are absent, so balance on the nose is not reproduced"
  - "belly for K1-K3/OU4 assumes the 'thin' dock target (R4); if the dock stays YZT0675 the belly is 2.05 deep, 25.5 long as on MZ2"
  - "K-concept dummy env ~160 mm3 below synthesis = the spine top, not modelled"
```
