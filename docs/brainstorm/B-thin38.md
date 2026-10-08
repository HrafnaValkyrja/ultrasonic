# B-thin38: thinnest pod in the 38 mm slot (blind design, 2026-10-08)
Window: X = 29.5..67.5 mm from hinge (38 L), H <= 15.25. T = thickness off the arm (priority 1). `[unsourced]` = no dated source found; treat as assumption.

## Architecture (2 options, recommend A)
- **A (recommend): one 0.8 mm rigid board, cell on its inner face, all ICs on the outer face, single deck.** Cell lies *beside nothing*: it sits under the board, so the board's 36 mm length is all usable. Thickness = wall + cell + board + tallest IC + wall.
- B: two decks (cell deck + logic deck) -> +0.8 mm board + 0.3 gap, T ~8.5; no benefit, more parts. Rejected.
- Rejected earlier by evidence: single-deck cell *beside* the logic fails at 38 mm (cell is 31 long, leaves 7 mm; see D-slab38 in repo log, not read).
- Chain unchanged in principle: mic (MEMS) -> MCU DSP -> noise-shaped PWM -> H-bridge -> exciter; linear charger with NTC; 3.0 V linear rail; MCU core SMPS only.

## Cell (real, datasheet)
**EEMB LP401230** (EEMB = Chinese Li-polymer maker; model = ~4.0 x 12 x 30 mm pouch). Product overview table (sos.sk PDF of EEMB catalogue, fetched 2026-10-08): 3.7 V, 100 mAh typical / **90 mAh minimum**, **4.3 T x 12.5 W x 31 L mm, 2.0 g**. Page https://eemb.com/product-121 (2026-10-08): UL1642/UN38.3/IEC62133, -20..+60 C.
Pulse: EEMB LP401230-PCM-LD spec (2015, via search result, PDF itself not opened): **max discharge 200 mA = 2.0C**, cut-off 2.75 V, max charge 100 mA = 1C. Bare-cell pulse rating not found `[unsourced]` -> design cap below uses the PCM-LD figure; confirm with EEMB datasheet before freeze.
Thinner alt LP301230: 70 typ / 60 min mAh, 3.5 x 12.5 x 31, 1.4 g (same catalogue). Saves 0.8 mm but fails 8 h worst case (below).

## Stack (section through arm, outer = away from glasses)
```
 outer wall 0.8 | IC face: STM32U375 WLCSP 0.58 (~0.6) | PCB 0.8 | glue 0.1 | cell 4.3 | inner wall 0.8   = 7.4 mm
 tail (mic only, no cell): wall 0.8 + mic ~1.0 `[unsourced]` + PCB 0.8 + wall 0.8 = 3.4 -> inside 7.4
```
Wall 0.8 = printed shell assumption; 0.6 -> T 7.0 if print allows. Passives 0402-class (~0.35 `[unsourced]`) < WLCSP height, so IC sets height.

## Numbers
| | value | basis |
|---|---|---|
| **T x H x L** | **7.4 x 15.0 x 38.0 mm** | H: PCB 13.4 + 2x0.8; cell 12.5 W fits under 13.4. L: PCB 36.4 + 2x0.8 |
| Start | X = 29.5 (shell front) .. 67.5 | whole pod in window; cell rear-justified (X 36.5..67.5) |
| Mass | **~7.6 g/side** | cell 2.0 (sourced) + board w/ parts ~1.1 + shell ~1.5 + clasp/adapter ~1.0 + PCM/wires 0.5 + exciter+arm ~1.5; all but the cell `[unsourced]` estimates, in the 7.3-8.8 g spec band |
| Exciter | outside the 38 mm box, on a swept arm to tragus | size/mass unknown; the 38 mm box does not include it (flag) |

**Runtime budget** (all loads on cell via linear rail, so I_cell = I_load):
mic 1.0 mA (distributor "supply current 1 mA"; Knowles SPH0641LU4H-1 mode current not confirmed; sibling LM4H-1 235 uA low-power) + MCU 1.5 mA (STM32U375, ST datasheet: 13 uA/MHz @48 MHz CoreMark; AN6195: 1.1 mA @48 MHz, 2.74 mA @96 MHz; I take 1.5 mA incl. margin; 3-4 MHz PDM clock handled by DMA/filter) + output stage avg 6.0 mA `[assumption: exciter drive, no spec number]` + charger/LDO/LED/gauge 0.1 mA = **8.6 mA**.
- LP401230 min 90 mAh x 0.80 usable (aging, 3.0 V rail dropout, tolerance) = 72 mAh -> **72/8.6 = 8.4 h worst case** (pass). Typical 100 -> 80 mAh -> 9.3 h.
- LP301230: 60 x 0.8 = 48 mAh -> 5.6 h (typ 70 -> 6.5 h): **fails**. So T is set by the cell.
- Normal day, Transient-only mode (exciter avg ~3 mA assumed): 5.6 mA -> 12.9 h on 72 mAh (meets 12 h).

**Peak current vs pulse rating:** exciter drive limited in hardware (bridge supply series limiter / current-sense trip) to **150 mA peak** <= 200 mA (2C, PCM-LD spec) <= bare-cell rating `[unsourced]`. Average 6 mA is 0.07C. Charge: 45 mA (0.45C) <= 0.5C (S§9 B3) and <= 1C max (100 mA).

## Buildability (hand assembly, ~8 steps)
1 JLC assembles single 4-layer 0.8 mm board, one-sided SMT (ICs outer face only; fine-pitch WLCSP 0.35 mm pitch is JLC-feasible `[unsourced]`). 2 Tin cell tabs to board pads (bare cell + PCM at tail end of cell, on the board's inner face, in the 5 mm board tail). 3 Glue cell to inner face (0.1 mm tape). 4 Solder exciter pair on edge pads. 5 Seat sub-assembly into inner shell half. 6 Mic port gasket. 7 Outer shell, 2 screws/clips. 8 Clasp. Cell replace = steps 7,5,2 reversed.

## Wins / loses (vs spec figures)
Wins: T 7.4 mm (thickness-first); one board, ~30 parts `[estimate]`; mass ~7.6 g. Loses: L uses the full 38 mm (length is last priority; fine); H 15.0 near limit; 8.4 h worst case has only 5% margin and depends on the unmeasured 6 mA output average; no spare volume for a bigger cell. Cell is sealed under the board, so cell swap needs full open.
Hard-no's stretched: none; exciter outside box is the open item. To unstretch: measure exciter drive current at ceiling, get LP401230 bare-cell pulse spec from EEMB, confirm mic height/current from Knowles datasheet.

Sources (fetched 2026-10-08): eemb.com/product-121; sos.sk/novinky/pdf/2587_eemb-lipol-overview-en-1.pdf; ST STM32U375/U385 datasheet + AN6195 (via alldatasheet/st.com search results); distributor listings for SPH0641LU4H-1.
