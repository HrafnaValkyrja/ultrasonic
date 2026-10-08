# Proof P-PHYS: is the K4 pod physically possible? (2026-10-08)
Re-run 2026-10-08, fenced 3G: `K4_RELIEF=lift python3 hw/mech/shell_k4.py` -> hw/mech/out/k4s_lift/checks.json (identical to committed); `python3 sim/checks/k4_heights.py` -> sim/out/k4_heights.json. k1t: hw/mech/out/k1t/checks.json (docs/research/k1t-vs-k4-parity.md, 2026-10-08). Figure: physical.png (plot.py).

| # | Check | K4 | K1-thin | Verdict | Source |
|---|---|---|---|---|---|
| 1 | 6L 0.8 mm stack-up (JLC) | JLC impedance page lists 6L only at 1.2/1.6/2.0 mm; 0.8 mm 6L unpublished; dielectric split chosen by JLC; no impedance control | n/a (4L 0.8 mm, JLC04081H-3313 published) | K4 OPEN (gate B4); k1t PASS | .pcba-workflow/k4-release/gate.yaml (fetched 2026-10-08); reg-board.md l.161 |
| 2 | Part heights vs floor (P file-B side) | clear nom 0.65, RSS 0.44, worst 0.163 (tallest L1 1.0) | board-B to cell 1.4, tallest 1.08, margin 0.32 | PASS both | k4_heights floor_side; k1t B_gap |
| 3 | Part heights vs lid (M file-B side + 0.25 VHB) | worst +0.112 (12 parts, 0 fail); only 0201-class under the lid; SW1 in pocket, mic bore | F gap slack 0.05 | PASS both (K4 thin) | k4_heights lid_side_M_fileB; k1t F_gap |
| 4 | Inner gap P-M (BM28 0.6 +-0.05) | 24 checked, 0 fail nominal/worst, 2 below margin | n/a | PASS (2 WARN) | k4_heights inner_gap |
| 5 | Clashes (shell checks) | all 0 except tub/cell 0.145 mm3 (cell corridor 0.145) | all 0, corridors 0 | K4 OPEN (tiny, known); k1t PASS | checks.json both |
| 6 | Printable (solids valid) | tub, lid, puck 1 solid each | all 1 solid; 0.6 wall corner 0.14 under chamfer, coupon unprinted | K4 PASS; k1t OPEN (wall coupon) | checks.json printable; parity doc gap 1 |
| 7 | Tolerance stack board/ledge/post (ECR-0023 add.2) | chain +-0.537 lin / +-0.215 RSS; post printed 0.5875 short, air gap 0.05..1.125, epoxy dab fills; ledge VHB 19 mm2 | no post | OPEN: epoxy fill (shrink, voids) is [A], bench-unverified; ledge alone 104 kPa vs 85 | k4_heights floor_post; docs/research/k4-ledge-margin.md; ECR-0023 |
| 8 | BM28 mated height | 0.6 mm gap +-0.05 [T] (C424570/C424571 BM28B0.6-30DP/DS, JLC 2026-10-08); in chain, floor worst 0.163 includes it | n/a (no B2B) | PASS | integration-map.md l.218; k4_heights TOL bm28 |
| 9 | Dock fit | head 21.2 x 6.86 on 4.4 flat belly overhangs T 6.4 by 0.23/side; tab to cell 3.55; tab-to-boss 0.45; clash dock_mags/dock_boss 0 | dock fits (clash/dock 0) | PASS (overhang is cosmetic, by design) | checks.json dock |
| 10 | Board in cavity | stack x 18.5-34.0, side gap 1.03, front gap 0.25 | board x 34.55-64.55, side gap 0.8, front 0.25 | PASS both | checks.json |
| 11 | Vision line (VISION_X 29.5 = pupil + 18 mm, estimate) | front X0 17.65: 11.85 mm inside; passes only if the pen-test line is <= 12.6 mm (parity doc) | X0 33.7: clear 4.2 mm | K4 OPEN (pen test, weekend bench day); k1t PASS on estimate | hw/mech/pod.py l.35; queue A-K4-VISION |
| 12 | Size | 49.85 x 6.4 x 15.25, 4805 mm3, 9.43-10.58 g | 33.8 x 8.5 x 14.8, 4779 mm3, 9.6-11.5 g | info | checks.json; parity doc |

## Bottom line
Geometry closes for K4 (no real clash, positive clearances at worst case). Three things are not proven: 6L 0.8 mm stack at JLC (B4), the epoxy post fill that keeps the ledge VHB alive under a 2 N press (bench), and the vision line (pen test). K1-thin is simpler on all three but owes the 0.6 mm wall coupon print, the button and duct fixes, and a release package (~5-6 h Claude time).
