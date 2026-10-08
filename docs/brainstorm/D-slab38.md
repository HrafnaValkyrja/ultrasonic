# D-slab38: I-003 single-deck slab sized to the real 38 mm (2026-10-08)
Verdict: **fails.** Side-by-side layout leaves a ~41 mAh cell -> ~3-5 h, and 41 mAh cannot source the 315 mA bridge peak (7.7C). Thin is real only if the board shrinks ~4x. Not worth a redesign.

## Inputs (src)
- Space: X 29.5 (vision line) to fixed rear 67.5 = 38.0 mm; H <= 15.25 (K4 default, physical.md l.221); walls 0.5 each -> inner width ~14.2.
- Board area: K4 P and M are 15.55 x 12.05 each (187 mm2 each, 374 total, parts on both faces; placement_P.yaml has F and B). BOM: P 31 lines (U1 QFN-48 7x7, 2x DFN1010 FETs, J21 BM28 30-pin, L1, Y1), M 21 lines (U2 SPH0641 mic 3.5x2.65, U3 BQ25180, U4 LDO, SW1 KMT022, J20 BM28, RT1). Merge: drop the BM28 pair (~-35 mm2 with keepouts) -> ~340 mm2 on one 4L 0.8 board, both faces.
- Cell density: AKYGA LP302030 140 mAh in 3.0 x 20 x 30 = 78 mAh/cm3 (web search 2026-10-08; EEMB LP302030HA only 110 mAh at 3.5x20.5x32 = 48/cm3, high-power). Renata ICP501233 = 88/cm3 (battery.md). Use 78. No 12-14 mm-wide 3.0 mm stock cell was found: custom width = MOQ/lead-time risk [unverified].

## Sizing
- Board 14.2 wide: 340/14.2 = 24 mm long. Gap/tabs 0.8. Cell: 38 - 24 - 0.8 = **13 mm** x 14.2 x 3.0 = 0.55 cm3 -> **~43 mAh**.
- T = 0.5 + 3.0 + 0.3 + 0.5 = **4.3** (deck: 0.5 F parts + 0.8 + 0.9 B parts = 2.2 < 3.0, OK). H 15.25. L 38.
- Runtime (sub-power method, battery.md l.130: worst 9.8 + 0.75 LED mA, 75 % usable; nominal 6.8 + 0.55, 85 %): worst 43 x 0.75 / 10.55 = **3.1 h**; nominal 43 x 0.85 / 7.35 = 5.0 h. Need 113 mAh (1.45 cm3) for 8 h worst: cell would have to be 34 mm long, board 4 mm.
- Mass ~5.0 g (cell 1.3, PCBA 1.4, shell 1.0, exciter/arm 0.9, clasp 0.4) [estimate].

## What breaks
1. Runtime 3.1 h worst vs >= 8 h (D18). Fatal.
2. Peak: bridge 315 mA, VSYS 327 mA (sub-power rail_check) vs 2C = 86 mA on 43 mAh. Cell cannot source it (K4's 130 mAh at 2C = 260 already short). Fatal.
3. Both faces populated, 24 mm of board: the M lid face is flat for the dock/VHB and SW1/pads need an outer face; mic port and pad faces compete for the same outer face. Redo of both K4 layouts (weeks).
4. Rigid-flex or BM28 kept: BM28 kept = +35 mm2 = cell -4 mAh more.
5. Exciter 8 mm-class (2 mm tall) arm unverified; mic port keep-out ~15.9 mm from bridge area fits poorly in 24 mm.

## Vs K4 (T 6.4, 11.85 mm into vision line) and K1t (T 8.5, clears)
Slab: T 4.3 (-2.1), clears the line, L 38 - but 3.1 h. Neither K4 (~9.2 h per battery.md for 130 mAh) nor K1t trade is matched: slab buys thickness by spending the cell. Hybrid (cell over board) is just K4 again (~6.4-6.6).
