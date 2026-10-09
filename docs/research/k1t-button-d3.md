# K1-thin button (issue #11) desk check: D3 dome and 2-pad layout vs the D4 ring
date: 2026-10-09 | board: hw/pod/draft_r2/out/routed.kicad_pcb (pcbnew read-only), SW1 at (18.5, 6.0), F.Cu | extends docs/research/k1t-button.md

## 1. F.Cu within r 2.6 of SW1 today (min distance from centre to track edge, mm)
| net | items | d_min |
|---|---|---|
| BTN | 14.56,4.76 -> 16.31,6.51 -> 16.43,6.92 -> 20.0,6.93; via 16.31,6.92 | 0.93 (its own pad exit) |
| I2C_SCL | 21.43,6.01 -> 19.65,6.01 -> 18.58,4.94 -> via 18.58,3.35 | 0.81 |
| CHG_INT | 25.16,5.67 -> 19.61,5.67 -> 19.0,5.06 -> via 19.0,3.59 | 1.02 |
| I_SENSE | 17.94,4.99 (via) -> 16.89,3.94 -> 14.69,3.94 | 1.15 (via), 2.62 end |
| GA_N | 15.76,6.93 -> 16.49,7.66 -> via 18.71,7.66 | 1.66 |
| GND vias | 18.55,6.45 (0.45); 18.94,6.01 (0.44); 16.98,5.75 (1.54); 17.58,8.01; 20.68,6.45 (2.2) | 0.44 |
| +3V0 | pad stubs 17.0/20.0 at y 5.07; vias 19.45,7.53 (1.8), 19.52,4.35 (1.94), 16.47,4.74, 20.53,4.74 | 1.76 |
| edge cases | I2C_SDA via 18.24,3.67; USB_DM/DP (y 8.4/8.6, x 9.5-21.5); LED_K via 16.84,7.99; VBUS via 20.56,4.16 | 2.3-2.76 |
Two GND vias sit under the dome centre (r 0.44): any centre pad (D0.8, r 0.4) needs them moved or merged into the centre net.

## 2. D3 dome (ring r 1.1-1.5, centre pad D0.8, mask-defined, 0.1 clearance -> keep-out r <= ~1.65)
- Part: no D3 snap dome is stocked at JLC. jlc.py 2026-10-09T01:04Z: "metal dome 3mm", "600-3", "HYP 600" return nothing in stock; only HYP 600-415S (D4, C256252/C256257/C256258). The nearest real HYP part is 610-203S-075 = C256277, D2 (metal size), height 0.12, 75 gf, 100k cycles, travel 0.12, 250 in stock, MOQ 50, $0.0092 (lcsc.com listing, 2026-10-09; datasheet lcsc.com/datasheet/C256277.pdf, not opened). Snaptron SQ-series starts at 4 mm (snaptron.com search snippet, 2026-10-09; page 403 to fetch). D3 exists only as custom/catalogue domes (metal-domes.com C-series 3 mm+, unverified: no free height, force or LCSC code). So D3 = custom order, not an LCSC pick.
- Lanes if it existed: still blocked (d_min < 1.65): CHG_INT (3 segments), I2C_SCL (3 segments), I_SENSE via 1.15, GND via 1.54, plus the 2 centre GND vias. Freed vs D4: GA_N (1.66, marginal), no +3V0 issue. So 3 nets to move instead of 4. Not a different job.

## 3. 2-pad dome (two rim arcs, no full ring), D4 r 1.5-2.0, arcs ±35 deg (|dy| <= 1.15)
- West arc (BTN side): free. BTN exits through it by design; I_SENSE/GA_N lie outside |dy|.
- East arc: crosses I2C_SCL (y 6.01) and CHG_INT (y 5.67). Move those two (or put the arcs N/S: worse, 4 nets cross x 18.2-19.0 north).
- Traces under the dome interior (r < 1.5, e.g. I2C_SCL diagonal d 0.81) are legal under mask; only the centre pad's 2 GND vias must go.
- Cost: 2 nets re-routed + 2 vias, ~1 h by hand vs 2-3 h for the full ring. Segmenting a D4 ring into 3 arcs is the same idea. A 2-leg dome footprint also needs a dome whose rim is round (all HYP/Snaptron round domes are).

## 4. Height
Dome (D2-D4) free height 0.12-0.20 -> top ~+0.275 above F face vs lid inner +0.30 (k1t-button.md): fits, 0.09 worst. KMT022 is 0.65 tall: it does not fit under the 0.6 lid (margin -0.05) and cannot coexist with any dome on the same spot; D3 vs D4 changes nothing in z. Diameter does not help height.

## Verdict
No lead re-route for D3: no real D3 part, and it frees only GA_N. If the dome is wanted, use the D4 600-415S on a 2-arc pad (2 nets: I2C_SCL, CHG_INT; ~1 h) or skip the board edit with option C (proud skin). Owner decides.
