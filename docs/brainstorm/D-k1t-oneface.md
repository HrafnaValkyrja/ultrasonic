# D-k1t-oneface: can K1t drop to 7.2-7.6 mm by putting all parts on one face? (ledger I-018)
date: 2026-10-08. src: hw/pod/draft_r2/out/routed.kicad_pcb (pcbnew courtyards, DRC 0), tools/checks/part_heights.yaml (datasheet max), hw/mech/dims_k1.py k1t (walls 0.6, lid 0.6, cell 4.5).

## verdict: DOES NOT BUY 7.2-7.6. The board is already one-face; the ledger stack omitted the component band.
- Phase-2 board 30 x 12 (360 mm2): 68 refs on B (courtyard sum 228 mm2 = 63%, routed, DRC 0), only 7 on F: SW1 (8.3 mm2, must face the lid button) + TP1-6 test pads (9.9 mm2).
- Area check if F joins B: 228 + 18.2 = 246 mm2 (68%). x1.4 packing = 345 mm2 = 96% of 360 -> area is NOT the blocker (TP1-6 can move to B or be dropped; only SW1 must stay F). Honest note: the 1.4 factor is pessimistic, the routed board packs at 63%.
- B refs by type (courtyard mm2): U1 STM32U575 69.7 (7x7 QFN, 0.60 high); caps 27 refs ~45; resistors 23 refs ~29; J pads 12 refs ~52 (inflated courtyards); Y1 7.1; U2 mic 13.3; L1 3.5; Q1/Q2 4.4; D4-D6 3.7; U3/U4/U6 5.0; TP7-10 3.2.

## height stack (datasheet max, mm)
| item | now (k1t) | one-face floor |
|---|---|---|
| wall 0.6 + cell VHB 0.3 | 0.9 | 0.9 |
| cell Renata ICP401230 | 4.5 | 4.5 |
| B band (board B face to cell) | 1.4 | 1.18 (mic U2 1.08 + 0.10) |
| board | 0.8 | 0.8 (0.6 if 4L 0.6 accepted: -0.2, stiffness/port unchecked) |
| F gap (VHB to lid; SW1 0.65 sits in lid pocket) | 0.3 | 0.3 |
| lid | 0.6 | 0.6 |
| **T** | **8.5** | **8.28 (8.08 with 0.6 board)** |
Tallest B parts: U2 mic 1.08, L1 1.0, C14 22u 1.0, C4/C7/C21 10u 0.9. Everything else <=0.65.
Ledger's 7.2 sums 0.6+0.6+0.8+0.1+4.5+0.6: it has no component band (1.08 mm) and no 0.3 cell tape/0.3 VHB gap; the 0.1 is not a real clearance.

## why not flip everything to F
Mic SPH0641 is bottom-port: it must sit on B and sing through the board hole to the lid duct. Flipping it to F points the port at the cell. So the mic pins the B band at >= 1.08 regardless of "one face". Only a top-port ultrasonic mic or a cell cut-out under U2 (shorter cell, ~4 mm x 4.19 mAh/mm = ~17-21 mAh, falls under the 112.5 mAh need) would remove it.

## fits only if
1) B_GAP trimmed 1.4 -> 1.18 (needs cell VHB flatness check): -0.22.  2) optional 0.6 board: -0.2.  3) 7.2-7.6 additionally needs the mic band gone (top-port mic, new part) -> not available. Recommendation: treat K1t as 8.1-8.3 at best; I-018 stays low-merit.
