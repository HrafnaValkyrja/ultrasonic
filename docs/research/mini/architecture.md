# mini/architecture: Phase-2 architecture levers (PRELIMINARY research, read-only)

```yaml
doc: docs/research/mini/architecture.md
lane: architecture (Phase 2 miniaturization, preliminary)
status: research only; no board/schematic/placement/routing/spec edit; not committed
date: 2026-10-03T00:47Z (UTC; owner-local 2026-10-02 evening)
builds_on: docs/research/simplification-study.md (Package B = ECR-0015; B3 = Rev F), docs/research/simplify/size.md (SIZ-*), simplify/assembly.md (ASM-*)
baseline_for_deltas: Package B envelope 6829 mm3 (sim/checks/size_budget.py, params below); Rev F board numbers from probe of hw/pod/draft_r1/pod_r1_routed.kicad_pcb
guardrails: memory/two-phase-redesign.md (Phase 2 after owner review); O8 O9 O12 O16 O19 O20 O21 O22 respected; reversals listed as options needing owner call
abbr:
  T: pod thickness off the temple axis (y), mm
  H: pod height (z) without belly
  F/B: board faces; F = lid side (outer), B = cell side
  Fgap: y from board F surface to lid inner face (size_budget y_fgap); Bgap: board B surface to cell (y_bgap)
  CY: courtyard area (part footprint + clearance), mm2
  FPC: flexible printed circuit
  ZIF: zero-insertion-force FPC connector
  env: outer pod envelope volume, mm3 (size_budget v_env)
conf_marks: "[V] verified src (cited)  [E] estimate (derived, method given)  [T] TBD"
```

## 0. Bottom line

```yaml
BL-1: "Board AREA is volume-free inside the cell footprint (35 x 12 mm per face). 28x12 -> 34x12 board = 0 mm3 env, +0.11 g [E: size_budget, board_L 28 vs 34]. Pod L and H are set by the cell (Renata ICP501233PA-02, 175 mAh Li-po pouch with protection circuit, 35x12x5.3). So mm2 saved on the board (TPs, pads, LED/CC/self-test cuts) buys 0 mm3 unless it enables a y-stack change."
BL-2: "Every real architecture lever is in the y-stack (T). Rate: 0.1 mm of T = 60 mm3 env [E: size_budget]. In Package B the electronics stack Bgap 1.4 + board 0.8 + Fgap 1.25 = 3.45 mm = 30 % of T."
BL-3: "Bgap (1.4) is pinned by the mic (SPH0641LU4H-1, Knowles/Syntiant ultrasonic bottom-port PDM MEMS mic, 1.08 mm max [V part_heights.yaml]) plus an unknown cell-swelling margin. It cannot shrink without a top-port mic (rejected, size.md s9) or swelling data [T]."
BL-4: "Fgap (1.25 in B) is set by tall F parts: L1 1.00, C4/C7 0.90, Y1 0.90, C11/C12 0.70, J pad solder blobs 0.8 allowance [V part_heights.yaml]. It is the one free lever: cap F part height (ARCH-01, -210 mm3) or empty the F face except the switch nested in a lid pocket (ARCH-02, -570 mm3)."
BL-5: "Recommended Phase-2 direction: ARCH-02 (all parts on B; SW1 and the optional lid LED alone on F, nested in lid pockets), gated by a placement-only density trial; fallback ARCH-01. Add ARCH-07 (dock FPC tail) only if the owner reads O16(3) as allowing it. Combined ARCH-02+07: 6173 mm3 (-656 vs B, -9.6 %), T 11.35->10.4, 13.15->12.2 mm off the temple [E]."
BL-6: "Rejected on numbers: board stacked/split/folded (adds T; JLC has no rigid-flex [V]); board under the cell in the belly (inner width ~6.6 mm -> ~231 mm2/face, too small) [E]; Bgap trim; flex main board for rev 1 (high risk)."
BL-7: "Cell share of env: S0 28.5 %, B 32.6 %, ARCH-02+07 36.1 % [E]. After these levers the cell plus walls dominate; the only bigger lever is the cell itself (SIZ-12, not recommended: O16(1), E4 unmeasured)."
```

## 1. Facts used (sources + dates)

```yaml
F-01: {fact: "Rev F board 34.05 x 13.05, 73 footprints, 118 vias; CY F parts 115.2, B parts 81.2, J pads 34.8 (all F), TP F 7.1 + B 1.5; total 239.7 mm2", src: "pcbnew probe of hw/pod/draft_r1/pod_r1_routed.kicad_pcb (Rev F, commit 4b2c058)", date: 2026-10-03T00:4xZ, conf: V}
F-02: {fact: "11 J wire pads, 1.0 mm round (J4 1.0x2.0 shared GND), 1.6 mm pitch, two columns at board x 31.4/33.0; field bbox 3.64 x 10.05 mm; 12 wires on 11 pads", src: "same probe; hw/pod/place_r1.py PLACE; reg-board.md issue 7", conf: V}
F-03: {fact: "J pad and TP-dot height allowance 0.8 mm (solder blob 0.5 + 0.21 litz + 0.09)", src: "tools/checks/part_heights.yaml by_footprint", conf: "V (allowance, not measured)"}
F-04: {fact: "F part maxima: L1 Murata DFE201610E-2R2M (2.2 uH SMPS inductor) 1.00; C4/C7 Samsung CL10A106 10 uF 0603 0.90; Y1 Epson FC-135 32.768 kHz crystal 0.90; C11/C12 FH 0402CG150J 15 pF 0.70; U1 STM32U575CIU6Q (ST Cortex-M33 MCU, QFN-48) 0.60; SW1 C&K KMT022NGJLHS (IP68 tact switch) 0.65 nominal, no tolerance given; 0402 caps 0.55-0.65; 0402 R 0.40", src: part_heights.yaml (datasheets read 2026-10-02), conf: V}
F-05: {fact: "B part maxima: U2 mic 1.08; D4 1N5819WS (Schottky, SOD-323) 1.00; C14/C21 0603 1.00/0.90; R21 1206 0.65; U3 BQ25180 (TI I2C Li-ion charger, DSBGA-8) 0.65 bound", src: part_heights.yaml, conf: V}
F-06: {fact: "C7 = VDDSMPS input cap; ST requires 10 uF, >= 10 V", src: "docs/system/sub-processing.md L38 (DS13737)", conf: V}
F-07: {fact: "JLC rigid PCB thickness list '0.4/0.6/0.8/1.0/1.2/1.6/2.0 mm', <1.0 mm tol +-0.1, manual review below 0.6", src: "https://jlcpcb.com/capabilities/pcb-capabilities", date: 2026-10-03, conf: V}
F-08: {fact: "JLC 4-layer controlled stackups (JLC04161H-*) list only 0.8/1.0/1.2/1.6/2.0 mm", src: "https://jlcpcb.com/impedance", date: 2026-10-03, conf: V, note: "conflicts with F-07 for 4L 0.6: TBD on the order form"}
F-09: {fact: "Via-in-pad (epoxy/copper filled, capped) default for >=6 layers; 4-layer option not stated; HDI 1-3 step offered; min via 0.15/0.25 mm", src: F-07 page, date: 2026-10-03, conf: V}
F-10: {fact: "JLC flex: 1/2/4 layers; 2L 0.11/0.12/0.2 mm; 4L 0.2-0.45 mm; stiffeners PI 0.1-0.25, FR4 0.1-1.6, steel 0.1-0.3; rigid-flex NOT offered", src: "https://jlcpcb.com/capabilities/flex-pcb-capabilities", date: 2026-10-03, conf: V}
F-11: {fact: "JLC PCBA on FPC allowed with a fixture ($23.57 per fixture); Standard PCBA min IC pitch 0.35, BGA 0.3, 0201 smallest; wire hand-soldering service exists", src: "https://jlcpcb.com/capabilities/pcb-assembly-capabilities", date: 2026-10-03, conf: V}
F-12: {fact: "JLC stock 2026-10-03T00:44Z: C15525 Samsung CL05A106MQ5NUNC 10 uF 6.3 V 0402 Basic 9.6M; no in-stock 2.2 uH inductor <= 0.65 mm found (DFE18SAN2R2*, TFM160808ALC-2R2: none); Murata DFE18SAN (1608 metal inductor) stocked only <= 1.0 uH; SPK0641HT4H-1 (Knowles top-port PDM mic, no ultrasonic spec) C5159510 Extended 68 @ $2.81; Hirose FH35C-11S-0.3SHW (0.3 mm-pitch 11-pin FPC ZIF) C5741856 Extended 220 @ $1.35", src: "tools/jlc.py", conf: V}
F-13: {fact: "Package B model: board 28x12, Bgap 1.4, Fgap 1.25, lid 0.8, plate 0.7, dock flat_tails, s_fixed 0.8 -> env 6829, T 11.35, H 14.5, belly 2.05, 13.15 off temple", src: "sim/checks/size_budget.py scenario(); simplification-study 3.1", conf: "V (model reproduces study)"}
F-14: {fact: "Mic duct = board 0.8 + Fgap + lid + plate; first quarter-wave c/4L (no end correction)", src: "size.md s7 method", conf: E}
F-15: {fact: "O16(3) 'no custom connector board'; ASM-12 (dock FPC tail) listed low-confidence, not in any package", src: "spec s12 O16; simplify/assembly.md L158, L231", conf: V}
```

## 2. Measures, ranked by env mm3 saved (deltas vs Package B 6829 mm3)

Model: `size_budget.scenario(**B, <override>)` (F-13); new dock row `flex_tail = dict(t=2.8, tail=0.5, L=25.5, g=0.9)` [E: 0.12 mm FPC + fillet + potting skin]. Run fenced 2026-10-03.

| id | measure | override | T | belly | env | d mm3 | d % | board mm2 | risk | owner call | conf |
|---|---|---|--:|--:|--:|--:|--:|--:|---|---|---|
| ARCH-02+07+05 | all-B + dock FPC + 0.6 mm 4L | fgap .30, L34, flex_tail, t .6 | 10.2 | 1.7 | 6054 | -775 | -11.3 | (as 02) | high | O16(3), board review | E/T |
| ARCH-02+07 | all-B + dock FPC tail | fgap .30, L34, flex_tail | 10.4 | 1.7 | 6173 | -656 | -9.6 | (as 02) | med-high | O16(3) | E |
| **ARCH-02** | all parts on B; SW1 (+PER-07 LED) alone on F, nested in lid pockets; full-face VHB | fgap .30, L34 | 10.4 | 2.05 | 6259 | **-570** | -8.3 | B CY ~197-230 on 408 = 48-56 % one face | med-high (density) | none reversed; layout O14 | E |
| ARCH-01b | F cap 0.60 (SW1 excluded: sits under its plunger) | fgap .85 | 10.95 | 2.05 | 6589 | -240 | -3.5 | F->B ~20 | medium | none | E |
| **ARCH-01** | F cap 0.65 (= SW1): L1, C4, C7, Y1 to B; C11/C12 -> 0.55 C0G | fgap .90 | 11.0 | 2.05 | 6619 | **-210** | -3.1 | F->B ~20 | medium (SMPS loop via) | none | E |
| ARCH-06 | 4L flex main board (0.3 incl. stiffener) | t .3 | 10.85 | 2.05 | 6529 | -300 | -4.4 | 0 | high | none, but not rev 1 | E |
| ARCH-05 | 0.6 mm 4-layer rigid | t .6 | 11.15 | 2.05 | 6709 | -120 | -1.8 | 0 | med (availability, stiffness) | none | T (F-07 vs F-08) |
| ARCH-07 | dock FPC tail (target tails trimmed into a 2L FPC) | flex_tail | 11.35 | 1.7 | 6735 | -94 | -1.4 | -5.6 | medium | O16(3) reading | E |
| ARCH-R1 | Bgap 1.4 -> 1.2 | bgap 1.2 | 11.15 | 2.05 | 6709 | -120 | -1.8 | 0 | **reject**: mic 0.12 from pouch, no swell data | - | E |
| ARCH-L | board 28 -> 34 long | L34 | 11.35 | 2.05 | 6829 | 0 | 0 | +72/face | none (eats rear stowage) | - | E |
| WP-*, TP-*, VAR-* | pad field, test points, LED/CC/self-test variants | - | - | - | - | 0 | 0 | see s5-s7 | - | see rows | E |

Off-temple distance: B 13.15; ARCH-01 12.8; ARCH-02 12.2; ARCH-02+07+05 12.0 mm. Mass changes <= 0.2 g in every row (mass is cell 4.2 + shell + pad 2.19, size.md 1.3).

## 3. ARCH-02 / ARCH-01: component-side strategy (the main lever)

```yaml
CS-options:
  CS-0: {what: "both faces as Rev F/Package B (F parts to 1.0 mm)", fgap: 1.25, d: 0}
  CS-1 (=ARCH-01): {what: "F parts <= 0.65 mm", moves: "L1 (1.00) -> B under U1 pins 20-23; C7 (0.90, VDDSMPS, needs >= 10 V so the 6.3 V 0402 C15525 is NOT a swap, F-06) -> B; C4 (0.90) -> B or 2x 0402; Y1 FC-135 (0.90) -> B; C11/C12 FH 0.70 -> Samsung 0402 C0G (<= 0.55) [T part pick]; J pads + TP dots -> B (already Package B rule ASM-09/SIZ-02)", d_mm3: -210, cost: "SMPS loop VLXSMPS(F) -> L1(B) through >= 2 vias (AN5373 wants a same-side tight loop); layout-noise + E11 whine must re-run; no 2.2 uH <= 0.65 mm stocked at JLC (F-12)"}
  CS-1b: {what: "F cap 0.60, SW1 excluded (the plunger sits on it, so its 0.65 is not a lid-clearance item)", d_mm3: -240, note: "same moves as CS-1"}
  CS-2 (=ARCH-02): {what: "every part on B except SW1 (and the PER-07 lid LED if taken); SW1 body nests in a 3.3 x 2.9 x 0.4 mm pocket in the lid inner face round the D3.2 plunger bore", fgap: 0.30, d_mm3: -570,
    why_better_than_CS1: "MCU, L1, C7-C9 all on B keeps the SMPS loop same-side (removes CS-1's main risk); F face flat -> full-face VHB bond (fixes SIZ-02's bond-in-peel and SW1-press-in-tension risk, study 4.4); mic port sealed by a VHB annulus (closes physical.md issue 1 without a chimney); every part visible on lid lift (O18)",
    costs: "one-face CY density: Rev F parts 196.4 - Package-B cuts ~22 - SW1 7.7 + J pads 25-35 + TP ~5 = ~197-230 mm2 on B; at 34x12 (408) = 48-56 %, at 28x12 (336) = 59-68 %, vs the proven routed 43 % (two faces, commit 6e93246, different netlist); board grows to ~34 long (0 mm3, F-13) and eats the SIZ-14 rear stowage zone -> wants fewer loose wires (PER-07, PER-01D, ARCH-07); all heat sources face the cell (U3 already does, R23); still 2-sided assembly for SW1 unless hand-soldered",
    gate: "placement-only density trial in Phase 2 (no FreeRouting by parallel agents); lid pocket print coupon for KMT0 travel 0.15 +-0.1 (sub-ui issue 1)",
    conf: E}
  CS-3: {what: "all-F except the mic", d_mm3: "~0 (Bgap stays mic-pinned 1.3-1.4)", verdict: reject}
  CS-4: {what: "single-sided F + top-port mic SPK0641HT4H-1 (C5159510)", d: "~-1.0 mm T (~-600 mm3) [E]", verdict: "keep rejected (size.md s9: no response spec above 20 kHz; F1 is the product); coupon-measure only"}
duct_and_quarter_wave [E, F-14]: {B: "0.8+1.25+0.8+0.7 = 3.55 mm -> 24.2 kHz", ARCH-01: "3.2 mm -> 26.8 kHz", ARCH-02: "2.6 mm -> 33.0 kHz", note: "all in the 20-85 kHz band; shorter is the spec s8 direction; coupons (R14) decide"}
```

### Integration-map s10 cross-check (ARCH-02; ARCH-01 is a subset)

```yaml
1_functions: "no F-row chain changes. F1 duct 3.55 -> 2.6 mm + VHB annulus seal. F11 SW1 stays F on the centre line (O16-5). F2 SMPS loop stays on one face (MCU+L1 both B)."
2_nets: none
3_pins: none
4_rails: "none electrically; L1 placement vs mic (IB-10: L1 >= 10 mm from mic, bridge x >= 14) and vs the left-pod dock magnets (study 3.5 VDD11 row) re-checked in placement"
5_offboard: "J pads all on B (Package B rule); count unchanged by ARCH-02 itself"
6_mechanical: "F face bare except SW1 (+LED); Fgap 0.30 (VHB 0.25 + 0.05); lid pocket for SW1; B band 1.4 unchanged; board ~34 x 12 (inside cell footprint); shell_r1.py y-stack, plunger length, lid features change; SIZ-03 superseded"
7_firmware: none
8_depends: "SIZ-02 lid-hung board, ASM-09, SIZ-15 dummies; benefits from PER-07, PER-01D, ARCH-07 (free the rear zone)"
conflicts: "SIZ-03 (replaced); study's 'chimney boss' mic seal (replaced by VHB annulus); R-PROC-BOARD text 'MCU on F centre'; R-UI-BODY plunger stack; R-BOARD-BODY bands"
plm_impact_run: "2026-10-03: hw/pod/place_r1.py -> 11 relations (R-AUDIO-BOARD, R-AUDIO-BODY, R-UI-BODY, R-DOCK-BOARD, R-PWR-BOARD, R-OUT-BOARD, R-DEBUG-BOARD, R-PROC-BOARD, R-BOARD-BODY, R-BOARD-ARM, R-COST-BOARD); hw/mech/shell_r1.py -> 8. Refs L1, C7, Y1, SW1, J3, TP1 and net VLXSMPS return NO relation (tracker blind spot, same as study s9)"
```

## 4. Board shape, split and placement vs shell and cell

```yaml
SH-1: {what: "rectangle inside the cell footprint, H = 12 (cell) , L free to 35", verdict: "keep; H over 12 costs ~0.7 mm H per +1 mm (SIZ-01 -294), L costs 0 (F-13)", conf: E}
SH-2 split_stacked: {what: "two boards stacked in y", d: ">= +1.6 mm T (board + parts band) = ~+960 mm3", verdict: reject}
SH-3 split_folded: {what: "rigid-flex fold to a second leaf", verdict: "reject: JLC has no rigid-flex (F-10); no free volume for a leaf (belly holds the target, rear gap 1.1-2.1, spine is a styling solid)"}
SH-4 board_in_belly: {what: "board horizontal under the cell carrying the dock target", calc: "T without the board stack = 0.8+0.3+5.3+0.3+0.8+0.7 = 8.2 -> inner width ~6.6 -> 6.6 x 35 = 231 mm2/face, target covers 21.2 x 6.86 of the bottom face; need ~286/face at 43 %", verdict: "reject (area); also mic would port down and SW1 leaves the board (O16-5)", conf: E}
SH-5 board_on_temple_side: {verdict: "reject: mic and SW1 must face out; no volume change"}
SH-6 board_on_cell_end: {verdict: "reject: L is fixed by the vision line and the Ear (open) hook (spec s8)"}
```

## 5. Rear wire-pad field (Rev F: 11 pads, 12 wires, CY 34.8 mm2, F face)

```yaml
WP-0: {what: "Rev F: 11 pads on F, 1.6 pitch", mm2: 0, mm3: 0, note: "blocks ARCH-01/02 (0.8 mm blob allowance on F) and SIZ-02 (F hidden after bonding)"}
WP-1: {what: "pads to B (ASM-09), same pitch; Package B 8 pads (J7 J8 J12 gone)", mm2: "-9.3 (B) / 0 (B3)", mm3: 0, risk: low, owner: "none (B) / O8+O12(a) via PER-07/PER-01D"}
WP-2 (=ARCH-07, ASM-12 extended): {what: "2-layer JLC FPC (0.11-0.12 mm, F-10): target tails trimmed and soldered through FPC holes, FPC runs the 0.8 mm under-cell channel and up the rear, lap-soldered to a 5-finger row on B (1.0 pitch)", mm2: "-5.6 (5 x 3.11 pads -> ~10 finger row)", mm3: "-94 (belly 2.05 -> 1.7)", joints: "10 -> 10, loose dock conductors 5 -> 0, fixes sub-dock-usb issue 16 fill/gauge", risk: "medium: second JLC order (FPC), hand lap joints, O21 sample of target first", owner: "O16(3): is an FPC tail a 'custom connector board'? (study read it as allowed only if 'no connector board', assembly.md L232)", conf: E}
WP-3: {what: "WP-2 + ZIF on the board (Hirose FH35C-11S-0.3SHW C5741856, 0.3 pitch 11-pin) for dock + cell (+NTC) so a cell swap needs no desoldering (O19 service)", mm2: "~+0..+3 vs pads [E]", mm3: "0 if <= Bgap; height [T: Hirose datasheet not opened]", risk: "medium-high: contact under exciter vibration, +1 Extended BOM line, cell leads must land on an FPC", owner: "O19 serviceability vs reliability trade"}
WP-4: {what: "cell leads land on B pads at the cell's lead exit", mm3: 0, blocked: "lead exit/PCM position unknown (physical.md issue 10)"}
WP-5: {what: "arm wires: keep litz on pads (2 with PER-07, 4 without)", verdict: "no connector fits the 2.1 mm gap"}
coupling: "fewer loose wires free the rear stowage zone, which ARCH-02 wants for board length"
```

## 6. Test points (Rev F TP1-TP6 0.7 mm pads on F, CY 7.1; TP7-TP10 0.5 mm dots, CY 2.0)

```yaml
TP-0: {what: "Rev F", mm2: 0}
TP-1: {what: "Package B: drop TP6 (PER-11), all to B, 0.5 mm dots (SIZ-10)", mm2: "~-4", mm3: 0, risk: low}
TP-2: {what: "duplicate SWD/NRST/3V0/GND to the O9 snap-off frame via a solid tab (ASM-01/ASM-02); keep 0.5 mm dots on the board for post-bond SWD", mm2: "~-1", mm3: 0, note: "removing the on-board dots loses SWD on a bonded pod (size.md s4.2): do not"}
verdict: "test access is < 4 % of one face and costs 0 mm3; O20 'must not cost size' already met. Only relevant as density relief for ARCH-02"
```

## 7. Study variants and their area effect (board CY, mm2; pod env 0 for all)

```yaml
VAR-PER-07: {what: "LED on the pod lid via light pipe; arm 4 -> 2 wires", mm2: "-6.2 (J7,J8) +~1.0 (0402 LED on F) = ~-5.2 [E]", other: "pad board deleted (pad -50..-110 mm3, outside pod env); LED on F fits ARCH-02 as a nested part", owner: O8}
VAR-PER-08: {what: "no LED", mm2: -7.94, owner: "O8, D3"}
VAR-PER-01D: {what: "CC out of the pod, 4-pin target", mm2: -4.83, mm3: "0 (same 21.2 mm body)", owner: "O12(a)/O16(3) + O21 sample"}
VAR-OUT-03: {what: "F4 by TRGO2 sampling, C22 gone", mm2: -1.65}
VAR-OUT-05: {what: "C14 22 uF 0603 -> 1 uF 0402", mm2: -2.63, height: "B 1.00 -> 0.60, but B is mic-pinned: 0 mm3"}
VAR-OUT-07: {what: "firmware duty clamp", mm2: 0}
VAR-OUT-02: {what: "R21 1206 -> 0402", mm2: -8.52}
VAR-OUT-01: {what: "R4/R6 out", mm2: -3.44, owner: "triage Q19 (kept in Rev F)"}
sum_Rev_F_to_B: "~-27 mm2 (239.7 -> ~212) [E from study rows + probe]"
value: "matters only as one-face density relief for ARCH-02 (each -10 mm2 = -2.5 points at 34x12)"
```

## 8. Mic port and other constraints that pin the layout

```yaml
PIN-1: "mic U2 on B (bottom port) -> Bgap >= 1.08 + clearance; port on the board centre line under the lid bore; same spot both pods (O16-5)"
PIN-2: "SW1 on F on the centre line under the plunger (O16-5, O16-7 KMT0 IP68): the last F part in ARCH-02"
PIN-3: "IB-10: L1 >= 10 mm from the mic; bridge x >= 14; L1 away from the left pod's rear dock magnet (E11 on the LEFT pod)"
PIN-4: "duct = board + Fgap + lid + plate: every Fgap cut is also an acoustic gain (s3)"
PIN-5: "cell swelling margin unknown (Renata gives no aged thickness): keeps Bgap 1.4"
PIN-6: "cell sets L 35 and H 12; board L is free <= 35, H must be <= 12"
PIN-7: "0.8 mm under-cell channel stays (strut-relief fill clears the cell corner by 0.07 mm, size.md s3): ARCH-07 cannot lower the cell"
```

## 9. Ranking (mm3 vs risk vs owner decisions)

```yaml
rank:
  1: {id: ARCH-02, mm3: -570, risk: med-high, owner: "none reversed; big layout change after her Phase-1 review; gate = placement-only density trial"}
  2: {id: ARCH-01, mm3: -210, risk: medium, owner: none, note: "fallback; subset path to ARCH-02; SMPS-loop-via cost"}
  3: {id: ARCH-07, mm3: -94, risk: medium, owner: "O16(3) reading; target sample (O21)"}
  4: {id: ARCH-05, mm3: -120, risk: medium, owner: none, note: "TBD 4L 0.6 availability; 2.4x board deflection (t^3) under the SW1 press and lid-hung bond"}
  5: {id: VAR-*/WP-1/TP-1, mm3: 0, mm2: "-27 to -40", risk: low-med, owner: "per study gates"}
  not_rev1: [ARCH-06 flex main board (-300, high), CS-4 top-port mic (-600, F1 risk)]
  reject: [ARCH-R1 Bgap trim, SH-2, SH-3, SH-4, SH-5, SH-6, DK-2 board-mounted target, DK-3 bare-pad contacts]
dock_contacts:
  DK-0: "wired target (Rev F/B): keep unless ARCH-07"
  DK-1: "= ARCH-07"
  DK-2: "target on a dock sub-board: back stack 0.8 board vs 0.85 bent tails = ~0 mm3, + a board-to-board link; O16(3) forbids a connector board -> reject"
  DK-3: "bare ENIG pads as contacts with own magnets: ENIG is not a mating finish; JLC capability page gives no hard-gold spec (F-07, 2026-10-03) -> reject for rev 1"
```

## 10. Open questions (owner or bench)

```yaml
Q-1: "Owner: Phase 2 may move every part to the cell side (ARCH-02) after her review of the two-sided Rev F? It changes no logic, only faces."
Q-2: "Owner: does O16(3) 'no custom connector board' allow a dock FPC tail (ARCH-07)?"
Q-3: "JLC: is 4-layer 0.6 mm orderable (capabilities list says 0.6, stackup page says 0.8 min, both 2026-10-03)? Quote on the order form."
Q-4: "Renata ICP501233PA-02 end-of-life swelling: sets the 1.4 mm Bgap (and the ARCH-R1 reject). No source."
Q-5: "C&K KMT022 height tolerance (0.65 nominal only): sets the ARCH-02 lid pocket depth."
Q-6: "Placement-only trial: does ~200-230 mm2 of CY fit one 34 x 12 face with GND fan-out at JLC rules? (Phase 2, single agent, fenced, no autorouter in parallel.)"
Q-7: "Hirose FH35C mated height and vibration rating (WP-3) - datasheet not opened."
Q-8: "Lower-profile 2.2 uH (<= 0.65 mm) meeting ST's Isat > 0.5 A, DCR < 200 mohm: none stocked at JLC 2026-10-03; only needed for ARCH-01 without moving L1."
```

## Reproduce

```
source tools/env.sh
# deltas: size_budget.scenario(**B, override) with B = dict(board_H=12, board_L=28, y_bgap=1.4, y_fgap=1.25, lid_wall=0.8, s_fixed=0.8, dock="flat_tails")
# add DOCKS["flex_tail"] = dict(t=2.8, tail=0.5, L=25.5, g=0.9) for ARCH-07
systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 python3 -c "import sys; sys.path.insert(0,'sim/checks'); import size_budget as S; print(S.scenario('x', board_H=12, board_L=34, y_bgap=1.4, y_fgap=0.30, lid_wall=0.8, s_fixed=0.8, dock='flat_tails')['v_env'])"   # ARCH-02 -> 6259
# courtyards: pcbnew.LoadBoard('hw/pod/draft_r1/pod_r1_routed.kicad_pcb'); fp.GetCourtyard(F_CrtYd|B_CrtYd).Area()/FromMM(1)**2
```
