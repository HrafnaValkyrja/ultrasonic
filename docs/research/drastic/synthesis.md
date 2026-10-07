# drastic/synthesis: routes to a drastically smaller pod (merged from 5 lanes + own layout runs)

```yaml
id: DRASTIC-SYN
doc: docs/research/drastic/synthesis.md
date: 2026-10-03 01:24-01:45 EDT
status: research synthesis only. No spec/board/schematic/CAD/firmware edit, not committed. tools/plm.py impact NOT run (read-only).
inputs: [drastic/00-owner-priority.md (O27 thin > short > length), power-cell.md, silicon.md, architecture.md, packaging.md, requirements.md, spec §1/D18/O27 (grep), integration-map.md §1]
own_runs: "scratchpad/drastic/syn/{e2e.py, ou.py, concepts.py}: sim/checks/size_budget.scenario() re-used with custom stacks; fenced MemoryMax=3G; 2026-10-03 01:25-01:27 EDT"
baseline: {phase2_MZ2: "6259 mm3, L38.0 T10.40 H14.5 (+belly 2.05), 12.2 mm off the temple, 11.92 g [E size_budget]", revF: "7801 mm3 [E miniaturization-prelim BL-6]"}
tags: "[V src date] primary verified | [E] estimate (method named) | [T] TBD"
ranking_rule: "O27 (owner 2026-10-03): mm of THICKNESS saved first, then HEIGHT, then volume; length may stay ~38 mm (temple zone: vision line in front, Ear-open hook behind -> L is a soft cap ~38-40, architecture.md BL-1)"
glossary:
  ICP501233PA-02: "Renata Li-ion polymer pouch with PCM (protection board), 175 mAh, 5.3x12x35 (today's cell)"
  ICP401230UPR: "Renata pouch with PCM, 130 mAh, 4.5x12.7x31 [V renata.com LiPo catalogue, cached 2026-10-03 01:18]"
  ICP390831PR: "Renata pouch, 85 mAh, 4.3x8.7x33 [V same]; PCM per suffix [T]"
  ICP281029HPG: "Renata pouch, 68 mAh, 3.3x10.2x30.5 [V same]; HP = 4.35 V class [T]; PCM [T]"
  ICP331319PM: "Renata pouch, 50 mAh, 3.7x12.8x21.0 [V same]; PCM per suffix [T]"
  ICP341018PM: "Renata pouch, 35 mAh, 3.7x10.2x19.5 [V same]"
  STM32U575: "ST Cortex-M33 MCU with core SMPS (U1 today, QFN48 7x7; WLCSP-90 4.20x3.95 = U575OIY6QTR)"
  STM32U3 (U385KGU6/U375KGU6): "ST near-threshold Cortex-M33, 96 MHz, core SMPS, ADF, USB FS, TIM1, UFQFPN-32 5x5; ~16 uA/MHz [secondary CNX 2025-03-05]"
  SPH0641LU4H-1: "Knowles/Syntiant PDM MEMS mic with ultrasonic mode (U2)"
  B0/B1/B2/B3: "power budgets from power-cell.md §2: B0 today; B1 firmware-only levers; B2 B1 + mic 1.8 V rail + bridge on VSYS + 1M gate pulls; B3 B2 + DSP at <=24 MHz Range 4"
```

## 0. Bottom line (blunt)

```yaml
SYN-1: "All five lanes converge: the pod is the CELL, and the cell is set by HOW D18 (>=8 h, ~12 h target) is read, not by any chip. Today's 175 mAh is sized for 12 h at the stacked worst corner (always awake, every block high, LED 0.86 mA, 75 % usable = 10.65 mA -> 170 mAh). Reading D18 as '8 h at the worst corner + 12 h at a 50 %-awake aged design point' needs 114 mAh with TODAY's electronics [E power-cell pc.py]. That is an owner call, not engineering."
SYN-2: "Silicon integration (PMIC, smart amp, haptic driver, Ambiq, SoC) gives ~0 mm3: board AREA is free while the board is shorter than the cell, and no part found draws less than the discrete bridge (0.83 mA) or BQ25180 + TPS7A2030. Only LOWER CURRENT shrinks the pod. The mic (1.35 mA always on) is the floor once the MCU is slowed."
SYN-3: "Packaging gives a no-function-loss -16 % on today's cell: plate off (-379), walls 0.6 (-386), thin dock (-238): 5265 mm3, T 9.3 [E]. Do it in every concept (plate is her styling call)."
SYN-4: "NEW (synth run, owner's 'stop stacking' idea): putting cell and board END-TO-END instead of stacked removes the 2.5 mm electronics band from the thickness. It only works with a SHORT thin cell (<= ~21 mm) and a <= 16 mm two-face board (needs WLCSP U575 or a QFN32 STM32U3). Result: T 5.6-6.0 mm (-4.4..-4.8), 7.4-7.8 mm off the temple (vs 12.2), 3563-3917 mm3 (-37..-43 %), L 40.1-40.5 (+2), with a 50 mAh Renata ICP331319PM. That is the largest THICKNESS cut found; it needs the B3 power budget (DSP at <= 24 MHz) to be a real 8-12 h device."
SYN-5: "Stacked thin cell (ICP281029HPG 68 mAh, 3.3 mm) + trims reaches almost the same VOLUME (3691 mm3, -41 %) but T 7.3, i.e. 1.7 mm thicker than end-to-end. Under O27 (thin first) end-to-end wins if its two gates pass (50 mAh cell pulse rating; 16 mm board density)."
SYN-6: "Nothing below ~8.5 mm thick is reachable without spending runtime margin. Below ~7.5 mm needs B3 = DSP in Range 4 (async SMPS spur risk E11/D11) AND her ears accepting algorithm A or a slim algorithm B. Every 'drastic' number is [E]: current is unmeasured (E4, blocked by O21)."
SYN-7: "Rejected (all lanes agree): central MCU / shared cell across the frame (one side +21 %, cable across both hinges, D2/O26), cell in adapter/pad/temple, radio sync, wireless charging, PMICs, smart amps, Ambiq for rev 1, coin cells (5.4-5.6 mm thick = thicker than today, O27), rigid-flex end-cap (L +5, T 8.5: superseded by end-to-end), COB/SiP/embedding/potting, 01005, cutting the 96 kHz top (§1 LOCKED)."
```

## 1. Ranked routes (duplicates merged; ranked by O27: thickness, then height, then volume)

| # | Route (lanes) | dT mm | dH mm | pod mm3 (vs 6259) | Function impact | Risk | Effort Claude / owner | Owner call |
|---|---|--:|--:|---|---|---|---|---|
| R1 | **End-to-end layout ("stop stacking")**: cell beside the board along L, two-face 16 mm board (WLCSP U575 or QFN32 STM32U3), 50 mAh ICP331319PM (synth e2e.py) | -3.7 (-4.8 with R4) | +0.4..+0.8 | 4441 (-29 %); with R4 trims 3563 (-43 %) [E] | needs B3 power for >=8 h worst (7.3 h; 10.3 h with exciter mean cap R6); design point 15.7 h | high: board density at 16 mm [T], 50 mAh vs 315 mA bridge peak (6.3C) [T], WLCSP rework (O19) or U3 port, wire stowage +100-140 mm3 [E], L +2 | 8-12 d / 3-5 d | yes (D18, D5, O19, plate) |
| R2 | **Thin cell, same stacked layout** (power-cell L8/C, arch ARC-1, req F01): ICP281029HPG 68 mAh 3.3 mm (B3) / ICP390831PR 85 mAh 4.3 mm (B2) / ICP401230UPR 130 mAh 4.5 mm (B0/B1) | -2.0 / -1.0 / -0.8 | -0.3 / -0.3 / +0.7 | 4487 (-28 %) / 5316 (-15 %) / 5480 (-12 %) [E pc.py] | none for 130 (worst 9.2 h B0, 11.4 h B1); 85 needs B2 (worst 9.3 h); 68 needs B3 (worst 9.9 h) | low (130) / med (85) / high (68: E11, listening, 4.6C peak) | 0.5 / 2-3 / 4-6 d; owner 0.5 / 1-2 / 2-3 d | yes (D18 reading) |
| R3 | **Runtime sizing rule** (power-cell L0, req F01/OC-1/OC-3, silicon SI-BL-5): 8 h worst + 12 h at 50 %-awake aged design point; state an end-of-life rule | enables R1/R2 | - | enabler (170 -> 114 mAh B0, 91 B1, 73 B2, 55 B3) | none at typical use; short day possible at the stacked worst corner | low if E4 measured, high if not | 0 / decision | **yes: the gate for everything** |
| R4 | **No-loss packaging trims** (PK-01/02, F07/F09, ARC-2a/F06a): plate 0.7 off (or 0.2-0.3 engraved skin), walls+lid 0.6, thin dock target | -1.1 | -0.4 (belly -0.7) | 5265 (-16 %) on today's cell; adds -700..-1000 to any concept [E concepts.py] | none (look; durability of 0.6 walls) | low-med (0.6 wall coupon, thin target part [T]) | 1-1.5 d / 0.5-1 d | yes (plate = styling, O16(3) keep-out) |
| R5 | **Firmware power levers B1** (PC-L1 LED PWM, L2 55 MHz Range 3 + ADF decimation, L3 Stop-2 idle, L6 dead time 25 ns) | via cell | - | need 114 -> 91 mAh [E] | LED dimmer (O8 'solid' kept at >= 1 kHz PWM) | low-med (cycle budget S3, E11 in Stop 2) | 2-3 d / 0 | LED only |
| R6 | **Exciter mean-power cap** (PC-L5) | via cell | - | worst exciter 2.5 -> 1.0 mA; -16 mAh at 8 h worst [E] | mild compression of long loud sources | low | 0.5 d / 0 | yes |
| R7 | **Hardware power levers B2** (PC-L4 mic on own 1.8 V LDO + 1-bit translator, PDM 3.072 MHz; L7 bridge on VSYS + VBAT gain; 1M gate pulls; F20) | via cell | - | need 91 -> 73 mAh; also fixes ECR-0005 (315 mA on a 300 mA LDO) [E] | none expected (OSR 16 noise check) | med (+2 parts ~3 mm2; mic current at 1.8 V [V] vs 3.0 V re-derived) | 1.5-2 d / 1 d | yes (schematic, O19) |
| R8 | **DSP at <= 24 MHz Range 4** (PC-L8, ARCH-SI-0/SI-M6, F04): algorithm A or slim B + FMAC | via cell | - | need 73 -> 55 mAh (B3) [E] | possible sound change (her ears) | high (async SMPS spurs E11/D11; PWM 120 steps) | 2-3 d / listening sessions | yes (D12/D14) |
| R9 | **STM32U3 swap** (ARCH-SI-1): U385/U375KGU6 QFN32 5x5 | enabler for R1 without WLCSP (-30 mm2 courtyard) | - | worst -1.6..-2.0 mA -> cell -18..-22 % [E secondary] | log ring 256 KB SRAM (230 KB ring shrinks), MDF fallback dots go | med (primary DS unread, JLC stock 7-14) | 0.2 d verify + 3-5 d port / 0.5 d | yes (D5, O18) |
| R10 | Board on the cell's top edge (PK-03) | -1.9 | +2.7 | 5912 (-5.5 %); 5129 with R4 | none; WLCSP + mic flag board | high | 4-6 d / 1-2 d | yes |
| R11 | Over-under: board strip ABOVE the cell in H (synth ou.py) | -3.4..-4.8 | **+3.2..+5.7** | 4272-5441 (-13..-32 %) | none | med; violates O27 #2 (short) | 6-8 d / 2-3 d | only if she prefers thin over short this strongly |
| R12 | Adapter-backed 0.4 tub wall (PK-05), PCBWay 0.6/0.4 laminate (PK-06) | -0.4 / -0.2..-0.4 | - | -241 / -120..-241 | none | med (adapter rigidity; 2nd fab) | 1 / 1-2 d | yes |
| R13 | Perceived size: straddle the temple (ARC-5) | outward 12.2 -> ~6.9 (inner +7) | - | 0 (+100-300) | none | med (temple-head gap on both frames [T]) | 1 d CAD / 1 d print fit | yes |
| R14 | Dock in envelope, 4-pin USB magnetic (ARC-2b/c) | 0 | belly -2.05 | up to -496 (realistic -230..-400) | none if D+/D- kept | med (part not found [T]) | 1 d / 0.5 d | yes (O12a/O16(3)) |

Own end-to-end / over-under runs (size_budget.scenario, band 3.0 = F 0.95 + board 0.8 + B 1.25, swell gap 0.4, gap 0.5 cell-board) [E]:

| run | cell | board | L | T | H | env mm3 | d vs 6259 | off-temple mm |
|---|---|---|--:|--:|--:|--:|--:|--:|
| E0 | today 175 | 30 one-face | 68.5 | 8.3 | 14.5 | 8297 | +2038 | 10.1 (L impossible) |
| E1 | ICP331319PM 50 | 16 two-face | 40.5 | 6.7 | 15.3 | 4441 | -1818 | 8.5 |
| E1c | same, plate 0, thin dock | 16 | 40.5 | 6.0 | 15.3 | 3917 | -2342 | 7.8 |
| CC | same + walls 0.6 | 16 | 40.1 | 5.6 | 14.9 | 3563 | -2696 | 7.4 |
| CC20 | same, QFN48 two-face 20 mm | 20 | 44.1 | 5.6 | 14.9 | 3889 | -2370 | 7.4 (L +6) |
| E2 | ICP281029HPG 68 | 16 | 50.0 | 6.3 | 14.5 | 4746 | -1513 | 8.1 (L +12: too long) |
| E3 | ICP401230UPR 130 | 16 | 50.5 | 7.5 | 15.2 | 5963 | -296 | 9.3 (too long) |
| E4 | ICP341018PM 35 | 16 | 39.0 | 6.7 | 14.5 | 4121 | -2138 | 8.5 (35 mAh: too small) |
| OU1 | ICP281029HPG 68 | 35x7 above cell | 38.0 | 6.3 | 20.2 | 4997 | -1262 | 8.1 (H +5.7) |
| OU4 | same, 35x6, plate 0, thin dock | 35x6 | 38.0 | 5.6 | 19.2 | 4272 | -1987 | 7.4 (H +4.7) |

```yaml
e2e_caveats:
  - "board 16 mm two-face is [E]: one-face courtyard need ~227 mm2 with QFN48 (31.5 x 12 @U0.60, miniaturization-prelim) -> two-face @U0.50 ~19-20 mm; WLCSP-90 (-28..-45 mm2) or STM32U3 QFN32 (-30 mm2) -> ~15-17 mm. Placement-only density trial needed (no routing, no FreeRouting)."
  - "wire stowage (12 wires, 107-142 mm3, requirements F13) has no free rear zone in e2e -> add ~+100-140 mm3 (dock FPC tail -76..-100) [E]"
  - "mic stays bottom-port on the board B face, port through the board to the lid duct (as F1 today); B face now faces the temple-side wall, not the cell -> no swell allowance in the board band"
  - "mass moves: cell (rear/ear side or front/hinge side) is a free choice now -> balance (D18) can be tuned; mass 7.5-8.5 g vs 11.9 [E]"
  - "size_budget fixed adders (spine, heel, plate area) are calibrated on shell_r1 -> small pods are OVER-estimated (architecture.md caveat) -> e2e numbers are conservative"
```

## 2. Redesign concepts (2-3; recommendation in §4)

```yaml
K1_right_size_same_layout:
  name: "Right-size, Phase-2 board kept (low risk)"
  what: "MZ-2 one-face 30x12 board UNCHANGED (no schematic edit) + Renata ICP401230UPR 130 mAh 4.5 mm + B1 firmware levers + R4 trims (plate off, walls/lid 0.6, thin dock)"
  pod: "4544 mm3 (-27 % vs 6259; -42 % vs Rev F 7801); L 33.6 T 8.5 (-1.9) H 14.8 (+0.3), 10.3 mm off the temple, 10.0 g [E concepts.py]. With 0.8 walls: 4884 (-22 %), T 8.9"
  runtime: "B1 worst 11.4 h, design 25 h; even B0 (no firmware levers) worst 9.2 h, design 18 h [E]"
  function: "none (LED PWM dimming is her call)"
  risk: "low: cell pulse rating vs 315 mA [T] (ICP501233: 175 cont / 350 pulse [V]); 0.6 walls need a coupon; H +0.7 from the 12.7 cell"
  effort: "Claude 1.5-2 d (shell_r3 params, size/balance/power reruns, docs); owner 0.5-1 d (plate + D18 decisions, print coupon)"
  archive: "not needed: Phase-2 board survives"
K2_low_power_thin_cell_stacked:
  name: "Low-power electronics + 3.3 mm cell, still stacked (medium-high risk)"
  what: "B2 hardware (mic 1.8 V LDO + 1-bit translator, bridge on VSYS, 1M pulls) + B3 firmware (DSP <= 24 MHz Range 4 + FMAC, Stop-2 idle, LED PWM, exciter mean cap) + Renata ICP281029HPG 68 mAh + R4 trims. Fallback cell if B3 fails: ICP390831PR 85 mAh with B2 only"
  pod: "68 mAh: 3691 mm3 (-41 %; -53 % vs Rev F), L 33.1 T 7.3 (-3.1) H 14.1, 9.1 mm off the temple, 8.4 g. Fallback 85 mAh: 4475 (-28.5 %), T 8.3 [E concepts.py]"
  runtime: "68 mAh B3: worst 9.9 h, design 21 h; 85 mAh B2: worst 9.3 h, design 20 h [E]"
  function: "possible sound change (Range-4 algorithm, her ears); otherwise none"
  risk: "high: E11 async-SMPS spurs in Range 4 / Stop 2; listening; 68 mAh vs 315 mA full-scale bridge peak (4.6C) -> firmware peak cap + bulk cap; cell PCM/pulse [T]; deeper daily cycles"
  effort: "Claude 4-6 d (schematic B2 rev, firmware budget, sims per O22, shell); owner 2-3 d + listening sessions"
  archive: "Phase-2 board needs a revision (2 parts + 1 net), not a new architecture"
K3_stop_stacking_end_to_end:
  name: "End-to-end cell + board, thin first (most drastic in thickness, highest risk)"
  what: "Renata ICP331319PM 50 mAh (3.7x12.8x21) beside a ~16 mm two-face board (U575 WLCSP-90 U575OIY6QTR, or STM32U3 QFN32 if its datasheet passes) along the pod length; B2 + B3 power + exciter mean cap; R4 trims"
  pod: "3563 mm3 (-43 %; -54 % vs Rev F), L 40.1 (+2.1) T 5.6 (-4.8) H 14.9 (+0.4), 7.4 mm off the temple (vs 12.2), 7.5 g [E concepts.py]; + stowage ~+100-140 -> ~3.7 cm3"
  runtime: "B3: worst 7.3 h (10.3 h with the exciter mean cap), design 15.7 h, expected 28 h [E]; with only B2: worst 5.5 h -> fails D18 unless the cap + design-point rule are accepted"
  function: "possible sound change (as K2); otherwise none"
  risk: "high: 16 mm two-face density [T]; 50 mAh peak (315 mA = 6.3C; normal D17 peaks ~85 mA = 1.7C) [T Renata pulse rating]; WLCSP not reworkable/probeable (O18/O19) or U3 port; new board + shell; all O22 sims redone"
  effort: "Claude 8-12 d (new placement two-face, gen.py/pin-contract if U3, shell_r3, noise/acoustic/thermal/balance re-runs); owner 3-5 d (review, fits on two frames O26, listening)"
  archive: "yes: Phase-2 (draft_r2 + shell_r2) becomes the reference design"
rejected_concepts:
  integrated_SoC_PMIC_smart_amp: "silicon.md: no part saves area or current vs today's set; PMIC bucks break D11; smart amps 4.6 mA (TAS2110) vs bridge 0.83. Best chip move = STM32U3 (R9), an enabler not a concept."
  shared_central_battery_or_MCU: "architecture.md ARC-3/3b: system -26 % but one side +21 % (7580 mm3), 20 cm cable across both hinges, asymmetric weight, O26 two frames, D2 reversed. Not recommended."
  over_under: "R11: T 5.6-6.3 but H +4.7..+5.7 -> violates O27 #2"
```

| concept | env mm3 | vs 6259 | vs Rev F 7801 | T mm | H mm | L mm | off temple | cell | worst / design runtime h | risk |
|---|--:|--:|--:|--:|--:|--:|--:|---|---|---|
| Phase-2 MZ-2 | 6259 | 0 | -20 % | 10.4 | 14.5 | 38.0 | 12.2 | 175 | 12.3 / 24 (B0) | - |
| K1 | 4544 | -27 % | -42 % | 8.5 | 14.8 | 33.6 | 10.3 | 130 | 11.4 / 25 (B1) | low |
| K2 | 3691 | -41 % | -53 % | 7.3 | 14.1 | 33.1 | 9.1 | 68 | 9.9 / 21 (B3) | med-high |
| K3 | 3563 (+stowage ~3.7k) | -43 % | -54 % | 5.6 | 14.9 | 40.1 | 7.4 | 50 | 7.3 (10.3 capped) / 15.7 (B3) | high |

## 3. Verify first (cheapest first; each with what it unlocks)

```yaml
V1: {what: "Owner: D18 reading (12 h at worst corner vs 8 h worst + 12 h design point) + end-of-life rule (F02) + plate off", cost: "0 Claude; one decision", unlocks: "K1 at once; is the gate for K2/K3"}
V2: {what: "Renata datasheets for ICP331319PM, ICP281029HPG, ICP390831PR, ICP401230UPR: PCM, max envelope (pouch tolerance + tab), continuous/pulse current, charge rate (O12c), cycle life", cost: "Claude 0.3 d (renata.com PDFs via curl/pdftotext) or a distributor email", unlocks: "whether 50/68 mAh survive the bridge peak (sets K3 vs K2)"}
V3: {what: "STM32U3 primary datasheet (U375/U385): uA/MHz at 3.0 V per range, ADF max PDM clock (4.0 MHz?), QFN32 ballout vs 27 signals (TIM1 CH1/CH1N/CH3/CH3N, USB, ADF), ROM DFU (AN2606)", cost: "Claude 0.2 d when st.com is reachable (unreachable 2026-10-03 01:17-01:22)", unlocks: "K3 without WLCSP"}
V4: {what: "Cycle counts on the M33: algorithm B at 55 MHz (B1), algorithm A / slim B at 24 MHz (B3), ADF decimation path", cost: "Claude 1 d (ARM GCC build + static/instruction-set count or the FWSIM model; no hardware)", unlocks: "B1/B3 budgets; K2/K3 feasibility"}
V5: {what: "Placement-only density trial: 16 mm two-face board (WLCSP U575 and QFN32 U3 variants) and 20 mm with QFN48", cost: "Claude 1 d in KiCad (pcbnew API, NO routing, NO FreeRouting)", unlocks: "K3 length (40 vs 44 mm)"}
V6: {what: "Range-4 / Stop-2 async SMPS spur check in sim/noise (E11 precursor)", cost: "Claude 0.5 d sim; bench later", unlocks: "B3 (K2/K3) or kills it"}
V7: {what: "Printed envelope dummies K1/K2/K3 (and OU4 for the thin-vs-tall feel) on both frames (O26)", cost: "Claude 0.3 d CAD; owner 0.5 d print + wear", unlocks: "her O27 judgement in the hand, not on paper (show, don't tell)"}
V8: {what: "E4 current measurement (mic at 3.0 vs 1.8 V, MCU per clock, Stop 2, exciter level)", cost: "needs hardware: NUCLEO-U575ZI-Q + SPH0641 breakout + exciter ~$60-80 [E]; conflicts O18/O21 -> owner call", unlocks: "turns every [E] runtime into evidence (O22); the most valuable single item"}
```

## 4. Recommendation (owner decides)

```yaml
REC-1: "Archive Phase-2 NOW as a tagged reference (git tag + frozen docs/system snapshot; delete nothing). Cost ~0.2 Claude d. It is the O22 comparison baseline whichever concept wins."
REC-2: "Take K1 as the floor immediately after V1 (if she accepts the D18 design-point reading): -27 %, T 8.5, no schematic change, low risk."
REC-3: "Run V2, V3, V4, V5, V6, V7 in parallel (~3.5 Claude days, no hardware, no orders). Then choose: K3 if the 50 mAh cell's pulse rating and the 16 mm board pass and her ears accept the Range-4 algorithm (thin-first per O27: T 5.6, 7.4 mm off the temple); else K2 (T 7.3); else stay on K1."
REC-4: "Ask for V8 (a ~$60-80 measurement rig) as an O21 exception: K2/K3 size the cell at 50-68 mAh on estimates graded Low; one bench day decides whether the margin is real."
REC-5: "Do NOT pursue: central MCU/shared cell, PMIC/smart-amp integration, coin cells, rigid-flex end-cap, band-top cut (§1)."
integration_map_crosscheck (K1/K2/K3, docs/system/integration-map.md §1/§10):
  F1_hear: "K2/K3: MIC_VDD from PA5 GPIO -> 1.8 V LDO + enable; MIC_DATA via 1-bit translator to PB4 (ADF1); PDM 4.0 -> 3.072 MHz"
  F2_process: "K2/K3: Range 4 / Stop-2 clocking (D12, D14 HCLK/400 lock); K3 with U3: whole pin map §4 regenerates (pin-contract.yaml, gen.py, system_map.py)"
  F3_drive: "K2/K3: P sources from VSYS not +3V0 (net change), firmware VBAT gain; TIM1 at 24 MHz = 120 PWM steps"
  F5_F6_F7_F8: "all: new cell capacity -> BQ25180 ICHG/ILIM/VBATREG, J9 NTC if pack has one, F8 thresholds; F7 LDO no longer feeds the bridge (K2/K3)"
  F9_F10_F15: "R4 thin dock target: same 5 nets; belly bay geometry changes"
  F11_F12: "F12 LED PWM duty (firmware); F11 SW1 position moves with the K3 board"
  F14: "K3 WLCSP: fanned-out test pads mandatory (O18); TP row relocates"
  mechanical: "K1: cell bay 4.5 x 12.7 x 31; K3: new shell (cell and board end-to-end, mic duct over the board segment, stowage zone)"
  sims_to_rerun: [power.py, size_budget.py, sim/noise (async SMPS), acoustics (duct), thermal, balance, FWSIM cycle/memory]
missing:
  - "tools/plm.py impact not run (read-only); no diagram rendered (a to-scale T-stack PNG of MZ-2 vs K1/K2/K3 is the obvious next visual)"
  - "Renata PDFs (V2) not fetched; all cell PCM/pulse data [T]"
  - "e2e board length (16 mm) is an area estimate, not a placement"
```

## Skeptic

```yaml
id: DRASTIC-SKEPTIC
date: 2026-10-03 01:29-01:40 EDT
method: "attack the top 6 claims (+1 found on the way) with primary data; numbers re-run in python from pc.py budgets; no edits outside this section, no commit"
new_primary_sources:
  RENATA-331: "Renata ICP331319PM datasheet V01 11/2022 (renata.com/en/downloads/?product=icp331319pm, fetched 2026-10-03 01:31 EDT): Safety Circuit YES; typ 50 / MIN 45 mAh; impedance <730 mOhm @30 % SOC; 4.2 V CV; charge 0.5C 25 mA, max 1C 50 mA; discharge max 1C 50 mA continuous / 2C 100 mA non-continuous; dims MAX 3.7 x 12.8 x 21.0 'after 500 cycles'; ~2.0 g; >80 % of min after 500 cycles; wire AWG30 [V]"
  RENATA-281: "Renata ICP281029HPG datasheet V01 11/2022 (fetched 01:31): Safety Circuit NO (bare cell); 3.8 V nominal, 4.35 V CV; typ 68 / MIN 65 mAh; <570 mOhm; 68 mA cont / 136 mA pulse; MAX 3.3 x 10.2 x 30.5 after 500 cycles; 2.4 g [V]"
  RENATA-390: "ICP390831PR V01 11/2022 (fetched 01:32): PCM YES; 85 / MIN 80; <530 mOhm; 85 cont / 170 pulse; MAX 4.3 x 8.7 x 33.0 after 500 cycles [V]"
  RENATA-401: "ICP401230UPR V02 08/2019 (fetched 01:32): PCM YES; 130 / MIN 125; <340 mOhm; 130 cont / 260 pulse; MAX 4.5 x 12.7 x 31.0 [V]"
  JLC: "tools/jlc.py 2026-10-03T05:31Z: STM32U575OIY6QTR (U575 in WLCSP-90) C5271033 Extended stock 10 $15.14; STM32U385KGU6 (STM32U3, UFQFPN-32 5x5) C45066903 Ext 7 $7.71; STM32U375KGU6 C45338536 Ext 14 $7.26 [V]"
  SPH0641: "SPH0641LU4H-1 sheet (scratchpad arch_sph.txt): ultrasonic mode clock 3.072-4.8 MHz; performance mode 1.024-2.475 MHz (gap between); CLOCK abs max -0.3..+5.0 V; VIH 0.7xVDD .. 3.6 V [V]"
  BQ25180: "TI BQ25180 sheet (scratchpad bq25180.txt): BATOCP 'reverse OCP only' 0.5/1/1.5 A/disabled; VBUVLO battery undervoltage [V]"
  ST: "STM32U3 primary datasheet still unreachable (curl st.com/resource/en/datasheet/stm32u385kg.pdf etc. returned nothing, 01:32 EDT) [T]"
recomputed_runtime_h (worst = always awake, high, x0.75; EOL = MIN cap x0.68; design = 50 % awake nominal, MIN x0.68):
  ICP331319PM_50: {B3_worst_typ: 7.3, B3_worst_min: 6.6, B3_worst_EOL: 6.0, B3_capped_typ: 9.5, B3_capped_min: 8.6, B3_capped_EOL: 7.8, B3_design_min: 14.2}
  ICP281029HPG_68: {B3_worst_min: 9.5, B3_worst_EOL: 8.6, B3_design_min: 20.5}
  ICP390831PR_85: {B2_worst_min: 8.8, B2_worst_EOL: 8.0, B2_design_min: 18.9}
  ICP401230UPR_130: {B0_worst_min: 8.8, B0_worst_EOL: 8.0, B1_worst_min: 11.0, B1_worst_EOL: 10.0, B0_design_min: 17.2}
peak_vs_rating (bridge full-scale 315 mA; D17 normal peak ~85 mA): {ICP331319PM: "3.15x pulse; 85 mA = 1.7x continuous", ICP281029HPG: "2.3x pulse", ICP390831PR: "1.85x pulse", ICP401230UPR: "1.21x pulse", ICP501233PA-02: "0.90x pulse (today)"}
```

| # | Claim attacked | Verdict | Evidence (short) |
|---|---|---|---|
| SK-1 | K1 / SYN-1 / R3: 130 mAh ICP401230UPR with today's electronics meets D18 (>= 8 h worst), "zero circuit change, low risk" | **holds** (runtime) / **weakened** (risk) | MIN 125 mAh: B0 worst 8.8 h, but EOL 8.0 h = zero margin; B1 (firmware) 11.0 / 10.0 h, so K1 needs B1, not B0. Pulse rating 260 mA < 315 mA full-scale peak (1.21x): needs the ECR-0005 peak cap at <= ~250 mA (-2 dB full-scale). That cap is already needed for the 300 mA LDO, so nothing new; "zero change" holds only once ECR-0005 closes. 340 mOhm, 0.11 V sag. H +0.7 confirmed (12.7 max). |
| SK-2 | B3 budget (DSP <= 24 MHz Range 4: awake 3.06 nom / 4.99 high mA) that K2/K3 rest on | **weakened** | (a) MCU 0.45/0.6/0.9 mA is scaled from ST's while(1) 19.5 uA/MHz point; the repo itself flags that figure (A3-u575-plan.md l.24). (b) Algorithm A = 19-39 Mcyc incl. the 6-10 Mcyc output interp/shaper (C2-cpu-budget.md); minus ADF decimation 5-10 gives 14-29 Mcyc = 58-121 % of 24 MHz. The top half does NOT fit; then Range 3 at ~32-36 MHz is ~1.3-1.5 mA [E 40 uA/MHz, A3], +0.4..+0.6 mA at worst. (c) Slim B needs a 2-2.7x cycle cut from 44-65; no count exists. (d) PDM: ultrasonic mode needs 3.072-4.8 MHz; 24 MHz/8 = 3.0 MHz lands in the dead gap, so the clock tree must come from MSIK 3.072/24.576 [T]. (e) Mic current NOT ignored (in idle and awake); the 1.8 V point is unloaded (+~0.05 mA loaded [E]); 3.0 V MIC_CLK into a 1.8 V mic is legal (VIH max 3.6 V) -> 1-bit translator on DATA is enough: that sub-claim holds. Net: B3 worst 5.14 -> ~5.5-5.7 mA if A's high count holds. |
| SK-3 | K3 / SYN-4: 50 mAh ICP331319PM end-to-end gives an 8-12 h device ("worst 7.3 h, 10.3 h capped") | **refuted for D18-at-worst; holds only under the design-point rule** | MIN capacity 45 (not 50): worst 6.6 h, EOL 6.0 h. The "10.3 h capped" subtracts 1.5 mA (B0's 2.5 -> 1.0) from B3, whose exciter high is already 2.0 (VSYS-scaled): correct capped worst is 9.5 h typ / 8.6 min / 7.8 EOL, a small double count. Peaks: 100 mA pulse rating vs 315 mA (3.15x); a 100 mA firmware cap = -10 dB full-scale headroom, which collides with spec R1 (transducer too quiet) until E2. 730 mOhm: 0.23 V sag at 315 mA. Daily DoD 54-77 % -> 500 cycles to 80 % of MIN = ~1.5-2 yr [E] (O19: replaceable cell, spares). PLUS for K3: dims are MAX "after 500 cycles", so the 0.4 swell gap can drop to ~0.1: T -0.2..-0.3 (strengthens thin). |
| SK-4 | K2: ICP281029HPG 68 mAh (3.3 mm) as a stacked drop-in | **refuted as a drop-in; weakened as a concept** | Datasheet: Safety Circuit NO. Spec R23 mitigation is literally "Cell with PCM". Options: an external protector (DW01-class protector IC + dual N-FET, +2 parts, ~4-6 mm2 [E]) or rely on BQ25180 VBUVLO + BATOCP (min 0.5 A = 7.4C, "reverse OCP only") with no independent overcharge protection; that is an owner safety call (O22 item 5). 4.35 V CV: BQ25180 VBATREG is I2C-programmable 3.5-4.65 V in 10 mV steps [V bq25180 sheet], so it is reachable, but the power-on default must be checked (if left at 4.2 V [T]: ~-8..-10 % capacity [E]). 136 mA pulse vs 315 (2.3x). Runtime holds if B3 holds (min 9.5 h worst). The PCM-equipped fallback ICP390831PR 85 mAh (4.3 mm) holds with B2: 8.8 h min, EOL 8.0 h. |
| SK-5 | K3 board: 16 mm two-face with U575 WLCSP-90 or STM32U3 QFN32; JLC-buildable | **weakened** | Stock is thin: WLCSP U575 10 pcs, U385 QFN32 7, U375 QFN32 14 (Extended, 05:31Z). O21 orders only at freeze, so stock may vanish. WLCSP-90 at 0.4 staggered pitch needs POFV/HDI on its inner balls; the repo's own pcb-tech lane (mini/pcb-tech.md B3) REJECTED HDI + WLCSP90 for O19/O20 (fragile, unreworkable, manual-priced HDI). K3 reverses that without new evidence. QFN32: 27 contract signals (pin-contract.yaml) vs ~23-26 I/O on a 32-pin SMPS package [E, ballout unread] -> drop MDF fallback x2 + DBG_TX (O18) and maybe LSE (D14 lock): unverified. packaging.md SC-2F says a two-face board at U~0.5 is "routable only with 0201 + 6L/POFV", so K3 implies a 6-layer + 0201 + POFV board. The 8-12 d effort looks low while the 30x12 one-face board is still being routed. L 40.1 + stowage; 41-44 with QFN boards: at or over the 38-40 soft cap. |
| SK-6 | Volume figures (R4 "no-loss -16 %", K1/K2/K3 totals): no double counting | **holds** (arithmetic) / **weakened** ("no loss") | Sub-additive everywhere: K1 4544 vs 6259-779-994 = 4486; K2 3691 vs 4487-994 = 3493; K3 3563 = E1 4441 - 878 of trims, which is less than the 994 the same trims save on today's cell. "No function loss" is overstated: the plate is her chosen styling (spec §8 "gunmetal armour plate ... fin and heel print as one part", and the heel holds the arm root), so plate-off must keep the heel/arm-root anchor [T]. 0.6 walls on a sealed, worn-for-years shell need the coupon. "Thin dock -238" is a target part that has not been found [T]. The headline 3563 omits stowage (+100-140); the "e2e is conservative" caveat is asserted, not shown. |
| SK-7 (extra) | R6 exciter mean-power cap: "mild compression only" | **weakened (stereo + spec conflict)** | Spec D17 asks for a FIXED ceiling, identical on both sides, with fixed gain (D3); a mean-power limiter is adaptive gain, so R6 needs a D3/D17 change (owner) first. The cap runs per pod with no inter-pod link (D2). A loud source on one side compresses that side more, which shrinks the ILD (interaural level difference) that T3 localisation relies on. K3 reaches D18 at the worst corner only because the cap engages when sources are loud. Fix [E]: a long time constant and a threshold above normal listening, or a fixed (non-adaptive) gain law; check ILD preservation in sim/dsp. No concept touches the §1 band or the stereo hardware: those hold. |

```yaml
skeptic_bottom_line:
  - "K1 survives (with B1 firmware + the ECR-0005 peak cap, which is already open). It is the only concept whose runtime holds at MIN capacity and end of life with margin (10.0 h)."
  - "K2 must swap to the PCM cell (ICP390831PR 85 mAh, T ~8.3 mm with trims) unless she accepts a bare cell + external protector. The 3.3 mm cell has no PCM [V]."
  - "K3's runtime number is wrong in the optimistic direction (min cap 45, cap double count). It meets 8 h at the worst corner only with the cap (8.6 h min, 7.8 EOL) and B3 fully working. B3 itself is weakened: algorithm A does not fit 24 MHz at its high count. Its thickness claim holds and even improves (no swell gap needed)."
  - "Biggest unchecked items: STM32U3 ballout and currents (st.com down), M33 cycle counts (V4), E4 measured currents. Any one can move K2/K3 by a cell size."
missing: ["STM32U3 primary datasheet (pin count, ADF clock)", "BQ25180 power-on VBATREG default not read (range 3.5-4.65 V is [V])", "D17 ceiling current not re-derived (used synthesis' ~85 mA)", "no sim run on ILD vs a per-pod limiter"]
```

## 5. Verification results (2026-10-07, V-status.yaml) and what they change

```yaml
K1: {verdict: "still the floor; recommended", change: "ICP401230UPR pulse 260 mA < bridge full-drive peak ~315 mA -> FWSIM-R64 hard current clamp (208 mA, about -3.9 dBFS) on full-scale paths only (self-test, CDC); the -12 dBFS listening ceiling (~79 mA) is already below it, so no audible cost; also clears ECR-0005", src: [V2-cells.yaml, docs/system/sub-power.md bridge_peak]}
K2: {verdict: "weaker", change: "ICP390831PR 85 mAh pulse 170 mA -> cap ~-6 dB (I_peak <= ~150 mA); the B3 24 MHz budget is dead (V4: nothing fits below ~34 MHz), so its 9.9 h worst-case runtime must be recomputed at >= 34 MHz (lower); ICP281029HPG (68 mAh, 3.3 mm) has NO PCM and charges to 4.35 V: needs a protection IC on the board", src: [V2-cells.yaml, V4-cycles.yaml]}
K3: {verdict: "not recommended now", change: "50 mAh cell pulse 100 mA (cap ~-10 dB); 24 MHz budget dead (V4); the 15-17 mm board places but only routes on 6 layers (V5: 1.6-1.9x today's routing load on 4); WLCSP needs filled via-in-pad", src: [V2-cells.yaml, V4-cycles.yaml, V5-density.yaml]}
firmware: {note: "spec algorithm B needs 61-71 MHz (not 55); slim B 35-44 MHz fits B1 if the owner's listening test accepts it (E2); A 22-36 MHz", src: V4-cycles.yaml}
REC-2b: "K1 after the owner's V1 answer (packet Q1), with the top-volume cap written into the firmware requirements. K2/K3 wait for E4 (a real current measurement) and, for K3, a 6-layer quote."
```
