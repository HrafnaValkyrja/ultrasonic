# K4 in 38 mm: can two boards + the 130 mAh cell fit? (2026-10-08, arithmetic [E], no CAD run)

Goal: pod <= 38.0 mm (spec s8 VISION_X 29.5 -> X1 67.5). Today K4 (lift): X0 17.65..X1 67.5 = 49.85 L, T 6.4, H 15.25 (hw/mech/dims_k4.py).
Length budget today (checked: sums to 49.85): wall 0.6 + stop gap 0.25 + stack 15.5 (routed_P) + wire gap 0.8 + cell 31.0 + rear relief/heel 1.1 + wall 0.6.
Need -11.85 mm. Sources: dims_k4.py; docs/research/drastic/V2-cells.yaml (cell envelopes); V8-thin-long.yaml (runtime); sim/out/mech/pod_mass_k4.json (mass baseline).

## Baseline K4 (pod_mass.py, 2026-10-08)
Body-only 6.88-7.48 g; worn (pod + pad + exciter + arm) 9.44-10.59 g; cell 3.5 g; tub+lid resin 1929 mm3.
Mass method for the options: everything but the shell unchanged (same cell/boards); shell (~2.3 g resin) scaled by outer surface area 2(LT+LH+TH).

## A. Cell under the boards (stack over the cell) - FITS
Boards (15.5 x 12, T 3.2) sit over the 31 mm cell, lid-side, as today (VHB on lid ledge); the cell goes between floor and boards. No wire gap along x.
- T = 0.6 floor + 0.1 tape + 4.5 cell + 0.2 clear + 3.2 stack + 0.95 lid standoff/VHB + 1.0 lid = 10.55 (+4.15). H 15.25. 
- L = 0.6 + 0.25 + 31.0 + 1.1 + 0.6 = 33.55 (stack lies inside the cell length; 4.45 mm spare under 38).
- A1 flat lid: 33.6 x 10.55 x 15.25. Shell ~2.0 g (-0.3): body-only ~6.6-7.2 g, worn ~9.1-10.3 g.
- A2 stepped lid (thick only over the 16.5 mm board zone, rest T 6.4): L 38.0 (zero margin, hard ban), mass ~A1 +0.1 g. Not recommended: no margin.
- Costs: T +65 % (K1-stacked era was T 9.6, rejected for thinness, O27/O33); off-temple ~12.4 (T+1.8, V8 rule). Charge/runtime unchanged: 130 mA (1C) ~1 h (O34c); slim_B 10.6 h typ / 8.2 EOL worst, spec_B 8.4 / 6.4 (V8-thin-long.yaml). Open: cell touches the board stack, so charger heat reaches the cell NTC (J9) - unquantified; mic port/ledge and wire routing need rework; ECR needed.

## B. Cell turned 90 deg (31 long along z, 12.7 along the arm)
- L = 0.6 + 0.25 + 15.5 + 0.8 + 12.7 + 1.1(relief, may drop) + 0.6 = 31.55. T 6.4. H = 31.0 + 0.2 + 1.2 walls = ~32.4 (+17).
- Mass: shell area +22 % -> +0.5 g: body-only ~7.4-8.0 g, worn ~9.9-11.1 g; CoM moves forward/down with the tall box.
- Costs: H doubles (15.25 -> 32.4), breaks the O34b height ruling and the K4 look (O34a); charge/runtime unchanged as A. Pod hangs 32 mm over/under the arm: ear/eyewear clearance unchecked. Reject.

## C. Smaller cell (ICP331319PM 50 mAh, 3.7 x 12.8 x 21.0, 2.0 g; V2-cells.yaml) - DOES NOT FIT ALONE
- End-to-end: L = 0.6 + 0.25 + 15.5 + 0.8 + 21.0 + 1.1 + 0.6 = 39.85 (1.85 over). T ~6.4 (stack sets it), H 15.25.
- Needs board over cell by >= 1.85 (T bump ~9.75 locally) or dropping relief + wire gap; no margin.
- Mass: cell -1.5 g, shell -0.3 g: body-only ~5.1-5.7, worn ~7.6-8.8 g.
- Cost: runtime fails D18/O28 (>= 8 h worst): slim_B 4.1 typ / 2.9 EOL h worst, normal 8.6 h (EOL) (V8 table); charge 50 mA 1C ~1 h but only 35 % of the energy. 68 mAh ICP281029HPG is only 0.5 mm shorter (L 30.5) and needs a 4.35 V charger: no help. 85 mAh ICP390831PR is 33 long: worse.

## Verdict
A1 (cell under the boards, 33.6 L x 10.55 T x 15.25 H, ~9.1-10.3 g worn) is the only layout that keeps 130 mAh and 8 h and clears 38 with 4.4 mm margin. Main cost: T 6.4 -> 10.55 (+4.15 mm off the temple), undoing K4's thin look; plus cell/board thermal coupling. Runtime/charge unchanged.
