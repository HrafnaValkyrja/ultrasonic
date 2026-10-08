# D-k4trim: shortest K4 at T<=6.4 and >=8 h worst (2026-10-08)
Verdict: **does not clear X>=29.5.** Best X0 ~24.2 (L 43.3) with a custom 26.8 mm cell; ~20.0 with stock parts. Gap to line: 5.3 mm (custom) / 9.5 mm (stock).

## Inputs (src)
- hw/mech/dims_k4.py (lift: cell x 34.8-65.8): L 49.85 = rear wall 0.6 + rear gap 1.1 (heel exit 65.8-66.6 frame-fixed) + cell 31 + wire gap 0.8 + stack 15.5 + stop gap 0.25 + front wall 0.6.
- Runtime (docs/system/sub-power.md, battery.md method): worst 10.55 mA, 75 % usable -> 8 h needs **112.5 mAh**; 130 mAh = 9.2 h. Peak 219 mA clamped -> cell must pulse >=2C at 112.5 mAh (1.95C, no margin).
- Renata ICP401230UPR (V2-cells.yaml, datasheet 08/2019): 130 mAh, 4.5x12.7x31, 1C cont / 2C pulse (260 mA), density 73 mAh/cm3 at max envelope.
- Search 2026-10-08: LP401030-class cells 80-100 mAh, 4x10x30-32 mm, **1C** continuous, 3C 10 ms pulse (fpbattery.com, lipolbattery.com LP401030 datasheet, serui 401030). None sources 219 mA for a stretch -> fail. ICP390831PR 85 mAh: 2C=170 mA, fail. 401225 (~105 mAh est) [unverified, no datasheet found].

## Why no overlap
Cavity depth y 4.9-9.7 = 4.8 (lid-hung stack 3.2 + cell 4.5 + tapes/swell). Stack over/under cell needs ~7.7 > 6.4 T. Side-by-side in z needs 24.7 vs H 14. Only the 0.6 wire strip already runs under the cell. Cell thickness 3.0 (D-slab38 style) still 6.2+ walls. So no stack/cell overlap; dock tab already under cell.

## Length budget (mm)
| item | now | trimmed | saves | note |
|---|---|---|---|---|
| cell | 31.0 | 26.8 | 4.2 | custom 112.5 mAh at same 4.5x12.7 (MOQ/lead risk); stock = 0 |
| stack (boards) | 15.5 | 13.75 | 1.75 | re-lay both boards 12.0 -> 13.6 tall (cavity 14.05); weeks of relayout, DRC redo |
| wire gap | 0.8 | 0.5 | 0.3 | DROP_X clearance 0.14 to cell face; tight |
| stop gap | 0.25 | 0.10 | 0.15 | print tolerance |
| front wall | 0.6 | 0.5 | 0.1 | |
| rear gap/wall | 1.7 | 1.7 | 0 | heel exit fixed |
| dock | in X0-relative pads/magnets (head 21.2 < L) | - | 0 | fits to L ~24; not a lever |
| **L / X0** | 49.85 / 17.65 | **43.3 / 24.2** | 6.5 | line 29.5: short 5.3 |

## Options
1. **Stock cell only** + stack/gap trims: save 2.3 -> X0 ~20.0, 9.2 h. Cheap, no cell risk. Not enough.
2. **Custom 26.8 mm cell + all trims** (rec if K4 must be trimmed): X0 24.2, 8.0 h worst, 1.95C peak. Still 5.3 over the line.
3. To reach 29.5 you must give up a requirement: cell ~21 mm (~88 mAh) -> ~5.4 h worst and 2.5C peak, or relax peak clamp below 176 mA, or move vision line/pen test result. Recommend: do not chase; pick K1t or move the line.

## Curve: X0 reached vs cost (added after R-vision 21d7274: line likely 11-21 mm, so X0 16-26 with 5 mm margin)
Runtime worst = mAh x 0.75 / 10.55; cell mAh ~ 4.19 per mm of length at 4.5x12.7 (130/31). Order = cheapest first.
| X0 | what it takes | cell | worst h | peak C @219 mA | cost |
|---|---|---|---|---|---|
| 17.65 | today | 31.0 / 130 | 9.2 | 1.7 | - |
| 17.95-18.2 | wire gap 0.5, stop 0.10, front wall 0.5 (0.55 total) | 31.0 | 9.2 | 1.7 | tolerances only, no relayout |
| 19.95 | + stack 13.75 long (boards re-laid 13.6 tall) | 31.0 | 9.2 | 1.7 | weeks of relayout + DRC, stock parts |
| **21** | + cell 29.9 mm (custom ~125 mAh) | 29.9 / 125 | 8.9 | 1.75 | custom cell MOQ, small |
| **24.2** | + cell 26.8 mm (112.5 mAh) = 8 h floor | 26.8 / 112.5 | 8.0 | 1.95 | custom cell, zero peak margin |
| **26** | + cell 24.95 mm (~105 mAh... est 100) | 24.95 / 100 | 7.1 | 2.2 | breaks D18 >=8 h worst by 0.9 h, breaks 2C pulse; nominal method still ~11 h |
| 29.5 | cell ~21 mm (~88 mAh) | 21 / 88 | 6.3 | 2.5 | needs peak clamp <= ~176 mA too |
Cheap trims to X0 ~21: tolerances (0.55) + stack relayout (1.75) + a ~1 mm shorter custom cell (1.05) = 3.35 mm. To ~26: the same plus a 6 mm shorter cell, which costs the 8 h worst-case requirement (the only point on the curve that does); decide whether D18 is judged on worst or nominal.
