# mini/area-model: lower-bound board area for Phase 2 (PRELIMINARY, read-only)

```yaml
id: MINI-AREA
lane: areamodel
date: 2026-10-02            # local; JLC API stamps read 2026-10-03T00:41-00:48Z = 2026-10-02 20:41-20:48 EDT
status: preliminary research. No board, schematic, placement or routing edit; nothing committed.
phase: 2 (miniaturization); input Rev F (Phase 1, awaiting owner review). Guardrails: memory/two-phase-redesign.md
script: sim/mini/area_model.py   (pcbnew API; ~1 s; fenced 3G)
out: sim/mini/out/area_model.json
reproduce: "source tools/env.sh && systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 python3 sim/mini/area_model.py"
abbrev:
  cy: courtyard area, mm2 (part body/pads + clearance)
  cy_norm: cy re-drawn by ONE rule for every part: (max(pad span, body) + 2c) per axis; c = 0.15 mm (body <= 1.15 mm) else 0.25 mm.
           KiCad-stock footprints keep their stock cy (same convention). Needed because easyeda (lcsc:) cy are inconsistent (U3, L1, Y1, U6, SW1 drawn at or inside the body)
  placeable: board area minus edge bands (0.3 mm all edges; 0.6 mm on long edges while clamp ribs exist)
  U: utilisation = sum cy_norm on a face / placeable area of that face
  2f / 1f: parts on both faces / on one face
  as-assigned: each part stays on its face (Package-B rule: every post-bond hand pad on B, ASM-09 / sim-study IB-07); balanced: ideal split (C_F + C_B)/2 per face
  eta: routed channel area (track length x (width + 0.09 space)) / routing capacity (free outer area on 2 faces + inner signal layers)
  K: fixed keep-out area per face (holds no part)
  floor: mic-noise separation length floor (below)
confidence_tags: "[verified src]" = number read from a named primary source this run; "[estimate]" = model/judgement; "[TBD]" = not resolved
```

## 1. Bottom line

- **The Rev F board is placement-limited by face imbalance, not by area.** F carries 172 mm2 cy_norm, B 87 (2:1). F sits at U 0.43, B at 0.22. Courtyards cover 29 % of the board overall, but the F face is as full as a dense board's average. [verified src: pcbnew probe of pod_r1_routed.kicad_pcb]
- **Lower bound with today's parts (Package-B mechanics, hand pads moved to B, U 0.50): 25.4 x 12 mm (305 mm2), against 34 x 13 (442).** That agrees with the simplification study's 28 x 12 choice, which adds margin for L1 vs the dock magnets and the J block. [estimate]
- **Package levers, cumulative at U 0.50, 2f as-assigned:** 0201 -> 22.1 mm; + small crystal / L1 / shunt -> 21.1 mm; + WLCSP90 MCU with via-in-pad (U 0.60) -> 16.3 mm (13.9 if balanced); + wire pads off-board -> 11.5 mm on area alone, **but the mic-noise floor (~14.6-16 mm) binds first.** [estimate]
- **A shorter board does not shrink the pod.** The cell sets pod length (35 mm) and height (12 mm board ceiling); simplify/size.md §0.7 and §4.2. Below about 26-28 mm, a shorter board only buys rear wire-stowage volume (SIZ-14).
- **The comfort lever that packages unlock is THICKNESS, through a one-face board.** All parts on B except SW1, which sits alone on F in a lid pocket. This deletes the F band: about 1.0-1.25 mm of pod thickness [estimate], or 9-11 % of S1's 11.25 mm. The one-face board fits the cell-limited 12 mm height at:
  - Rev F parts: 44.8 mm. Does not fit.
  - c (0201 + small crystal/L1/shunt): 35.5 mm at U 0.50, 29.9 at U 0.60. Fills the cell length and consumes the stowage zone.
  - d (+ WLCSP90): 27.7 mm at U 0.50, 23.3 at U 0.60. Fits with stowage left.
  - e' (+ trimmed pads): 25.0 / 21.1 mm.
  
  This trade (1f + WLCSP vs 2f) is the main Phase-2 question this model raises. It needs the owner, and the mech and thermal lanes.
- **Routing is not the binding limit down to about 250 mm2.** Required eta goes from 0.18 (a+B) to 0.20 (c) to 0.25-0.26 (d/e). Both routed boards used only 0.13 [verified src: measured]. No board in the repo demonstrates eta above 0.13, so d/e routing is unproven. [estimate]

## 2. Measured (pcbnew API, KiCad 10, 2026-10-02)

```yaml
revF:   # hw/pod/draft_r1/pod_r1_routed.kicad_pcb (commit 4b2c058 + silk e25f35f)
  outline: 34.05 x 13.05 = 441.1 mm2; placeable 396.4 (0.6 clamp bands on long edges)
  footprints: 73 (52 parts + 11 J wire pads + 10 TP/test dots); pads 230
  cy_raw: {F: 157.1, B: 82.6, sum: 239.7}
  cy_norm: {F: 172.1, B: 87.3, sum: 259.4}; union (overlaps removed) F 153.5 B 82.6
  U_placeable: {F: 0.434, B: 0.220, mean: 0.327}; cy_norm/board 0.294 (size study's '28 %' = raw/board)
  hand+test pads: 43.4 mm2 (17 % of all cy)
  vias: 118 x 0.35/0.15 mm; outside courtyards F 87, B 107; via squares (0.35+0.09)^2 = 22.8 mm2 per layer (through vias block all 4 layers)
  tracks_mm: {F.Cu: 199.0, B.Cu: 175.5, In2.Cu: 312.3, In1.Cu: 0 (solid GND)}; widths 0.10 mm (658 mm), 0.15 (29 mm)
  routing_overhead_outside_cy (channels + via squares)/board: {F: 0.081, B: 0.092}; In2 0.135; channels total 131.9 mm2; eta_used 0.127
  state: 2 unconnected (SWCLK-TP2, LED_K-J8), DRC = pad-ring courtyard overlaps only (summary.json)
old_dense:   # hw/pod/draft/pod_routed.kicad_pcb, Rev C/D netlist, commit 6e93246 (2026-09-30)
  outline: 20.05 x 11.55 = 229.1; placeable 213.0 (no clamp bands)
  footprints: 52; pads 178; 0 unconnected; 41 vias 0.35/0.15
  cy_norm: {F: 128.9, B: 78.6}; U_placeable {F: 0.605, B: 0.369, mean: 0.487}; raw/board 0.433 (= the size study's 43 %)
  no GND plane (In1 + In2 both signal); eta_used 0.132
  caveat: different netlist, no clamp bands, no 0.4 mm charger ball escape, 4 signal layers vs Rev F's 3
stock_courtyard_rule (KiCad 10 /usr/share/kicad/footprints, measured): chip 0201/0402 c=0.15; 0603/1206/QFN c=0.25; crystal 2012 c=0.5; ST WLCSP c=1.0 (BGA rule). bbox readings include ~0.045 mm line width
```

### 2.1 cy_norm by block (Rev F, mm2; map = integration-map.md §2)

| block | F | B | note |
|---|---|---|---|
| MCU (U1 + 9 passives) | 85.8 | 0 | U1 UFQFPN48 alone 65.6 = 25 % of the board's cy |
| DOCK_USB | 17.8 | 17.0 | J3/J4/J10/J11/J12 15.5 + D4 SOD-323 6.0 + U6 4.2 |
| CHARGER | 3.1 | 14.0 | U3 2.9 (DSBGA), C21 0603 4.3 |
| UI | 15.1 | 1.7 | SW1 13.3 (KMT0 pads span 3.8 mm) |
| MIC | 0 | 16.0 | U2 12.6 |
| BRIDGE | 0 | 15.1 | Q1/Q2 2 x 1.95, C14 0603 4.3 |
| SELFTEST | 3.4 | 10.2 | R21 1206 shunt 10.2 |
| CLOCK | 12.5 | 0 | Y1 FC-135 9.2 |
| ARM_PADS | 12.4 | 0 | J1/J2/J7/J8 |
| CORE_SMPS | 11.8 | 0 | L1 8.5 (easyeda land 3.2 x 1.8 for a 2.0 x 1.6 part) |
| DEBUG | 7.1 | 1.5 | TP1-6 1.1 each, test dots 0.5 |
| LDO | 0 | 6.7 | |
| VBAT_SENSE | 0 | 5.1 | |
| CELL_PADS | 3.1 | 0 | J5 |

Top single cy_norm: U1 65.6, SW1 13.3, U2 12.6, R21 10.2, Y1 9.2, L1 8.5, D4 6.0, four 0603 caps 4.3 each, U6 4.2, J4 3.7, J pads 3.1 each.

## 3. Utilisation figure (what U to predict with)

```yaml
primary_source_for_a_universal_U: none found. Commonly quoted 50-70 % figures are rules of thumb, not standards. Calibrated on the repo's own two routed boards instead [estimate]
evidence:
  - old_dense F face U 0.605 routed with 0 unconnected, 0.35/0.15 through vias, 4 signal layers (no GND plane)   [verified src: measured]
  - old_dense mean 0.487; Rev F F face 0.434 (2 unconnected, placement/escape-limited: reg-board, ECR-0002)    [verified src: measured]
chosen:
  U=0.43: demonstrated two-face mean (raw/board), the size study's basis
  U=0.50: CENTRAL for through-via 4-layer boards with In1 solid GND (3 signal layers): below the demonstrated 0.605 face to pay for the lost signal layer
  U=0.60: CENTRAL for via-in-pad + 0.2/0.1 mm vias (d, e). Via squares fall from 0.194 to 0.084 mm2 each: Rev F's 118 vias free 12.9 mm2 per layer, about +0.04 U at 300 mm2
  U=0.65: stretch (HDI-like density); not demonstrated
JLC_process_facts: (jlcpcb.com/capabilities/pcb-capabilities, read 2026-10-02)
  - 4-layer track/space 0.09/0.09 mm; '3 mil acceptable in BGA fan-outs' (3-3.5 mil = +20 % of order, sim-study assembly.md citing extra-charge article Sep 09 2026)
  - via 0.15/0.25 mm min; 0.10/0.20 mm only for board <= 1 mm with ENIG/OSP  -> the 0.8 mm pod board qualifies
  - via-in-pad: 'Epoxy Filled & Capped' / 'Copper paste Filled & Capped', via dia 0.15-0.55 mm, 'default for 6-layer and above'; 4-layer availability and price [TBD on the quote form]
  - copper to routed edge >= 0.2 mm (model uses 0.3); BGA pad min 0.2 mm (0.2-0.25 needs ENIG); SMD pad gap 0.15; NPTH min 0.50
  - castellated holes >= 0.5 mm, 'hole-to-edge >= 1 mm', board >= 10 x 10
  - HDI 1-3 step offered (blind 0.075-0.15 mm) [not modelled]
  - Standard PCBA: min package 0201, IC pitch 0.35, BGA pitch 0.3 (jlcpcb.com/capabilities/pcb-assembly-capabilities read 2026-10-02, via docs/research/simplify/assembly.md §1.2)
```

## 4. Alternative packages (cy_norm, same rule as Rev F parts)

| change | from -> to | cy mm2 | part (gloss) / LCSC / class / stock / price, JLC API 2026-10-03T00:41-00:48Z | electrical check |
|---|---|---|---|---|
| 0402 R/C -> 0201 | R_0402 1.72, C_0402 1.65 -> 0.96 | -0.7 each, 34 parts | e.g. Uni-Royal 0201WMF1002TEE 10k (C473048, Ext, 9.97M, $0.0014); GRM033R60J104KE19D 100 nF (C76928, Ext); CL03A105MQ3CSNH 1 uF (C53067, Ext); CL03A225MQ3CRNC 2.2 uF (C77762, Ext); GRM035R60J475ME15D 4.7 uF 6.3 V (C335103, Ext); 0201CG150J500NT 15 pF (C64554, Ext); Murata NCP03XH103F05RL 10k NTC 0201 (C98098, Ext, 175k). **Every 0201 found is Extended** [verified src] | C15 (4.7 uF **25 V** on VBUS, TI 9.2.2.1) has no 0201: stays 0402. 0201 X5R at 2.2-4.7 uF loses most of its capacitance under DC bias [TBD per rail] |
| 0603 bulk -> 0402 | 4.28 -> 1.65 | -2.6 each (C4, C7, C14, C21) | CL05A106MQ5NUNC 10 uF 6.3 V (C15525, **Basic**, 9.6M, $0.0256); CL05A106MP5NUNC 10 uF 10 V (C315248, Ext, 552k); GRM155R60J226ME11D 22 uF 6.3 V (C415703, Ext, 194k, $0.1639) | C7 VDDSMPS: ST wants >= 10 V -> the 10 V part. C21 on VSYS (to ~4.5 V) and C14 22 uF on the 315 mA bridge peaks: derating [TBD, sub-power / sub-output] |
| Y1 crystal 3215 -> 2012 | 9.2 -> 4.25 (KiCad stock 6.55) | -5.0 | Epson FC-12M 32.768 kHz, X1A0000610002 (C55208, Ext, 21,677, $0.2387, SMD2012-2P); Seiko SC-20S 7/9 pF (C97602/C97603) | load capacitance vs C11/C12 and LSE drive level [TBD, A3-clock doc] |
| Y1 -> 1610 | 9.2 -> 3.15 [estimate: no stock footprint] | -6.1 | Micro Crystal CM9V-T1A 1.6 x 1.0 (C5341287 12.5 pF, Ext, 1,106, $0.6292) | ESR higher than 2012 parts [TBD] |
| L1 land only (same DFE201610E) | 8.5 -> 5.25 (KiCad L_Murata_DFE201610P) | -3.3 | no part change; the easyeda land spans 3.2 mm for a 2.0 mm part | none |
| L1 2016 -> 2012 | 8.5 -> 4.25 [estimate land] | -4.3 | Murata DFE201210U-2R2M=P2 2.0 x 1.2 x 1.0 (C2049745, Ext, 7,666, $0.1938); **DCR 228 mOhm max** (Murata spec, PDF 2017-04-18, ultrasonic-scratch/ds/dfe201210u.pdf) | **fails ST DS13737 Rev 10 §5.1.6: L 2.2 uH +/-20 %, ISAT > 0.5 A, DCR < 200 mOhm.** 1608 options fail harder: TDK MLZ1608A2R2WT000 (C76797) DCR 250 mOhm, Isat 130 mA; Murata LQM18PN2R2MFRL (C337910) DCR 300 mOhm (lcsc.com pages read 2026-10-02). DFE18SAN2R2 / TFM160808ALC-2R2: not at JLC. **Take the land fix, not the package** |
| R21 shunt 1206 -> 0402 | 10.24 -> 1.72 | -8.5 | Panasonic ERJ2BSFR10X 0.1 ohm current-sense (C409058, Ext, 15,928, $0.0732) = sim-study OUT-02 | vetted in sim-study OUT-02 (calibrate gain) |
| D4 SOD-323 -> SOD-523 | 6.03 -> 3.46 | -2.6 | candidate part not searched [TBD] | 1N5819WS reverse-block rating to be matched [TBD] |
| U1 UFQFPN48 -> WLCSP90 | 65.6 -> 20.9 tight (36.8 KiCad stock, 1.0 mm BGA rule) | -44.7 (-28.8) | ST STM32U575OIY6QTR (Cortex-M33 MCU, 2 MB, SMPS variant, WLCSP90 4.20 x 3.95 x 0.59 max, 0.4 mm pitch, staggered; DS13737 Rev 10 Table 157, July 2024) (C5271033, Ext, **10 in stock**, $15.14); OG variant C5271029 0 in stock | 90 balls vs 48 pins: every pin number changes -> pin-contract re-map (logic unchanged, all used ports expected present [TBD check ballout]). Pads 0.225 mm NSMD (Table 158) vs JLC BGA pad min 0.2 (ENIG). Inner balls need via-in-pad |
| J pads trim | 3.11 -> 1.61 (1.27 mm pitch cell; J4 2 cells) | -17 total | SIZ-10 | solder blob margin (part_heights solder_margin_mm 0.25) |
| J pads off-board | 3.11 -> 0 | -37 total | castellated rear edge (JLC >= 0.5 mm holes) or a flex tail | wires still land somewhere; see limits |

## 5. Scenarios (Rev F logic; package and mechanics only; H = 12.0 mm board, cell-limited)

Keep-outs K (from Package B onward; a = today's mechanics):
- **F:** mic seal ring Ø3.2 = 8.04 mm2 (sub-audio-in #2), 2 NPTH Ø0.9 + ring (Ø1.6) = 4.02 (SIZ-02), 4 VHB spots at 9.0 [estimate, size not specified anywhere]. Total K_F = 21.1.
- **B:** NPTH 4.02 and the SW1 back-stop zone 3.0 x 2.6 = 7.8 (sim-study §4.4). Total K_B = 11.8.

Board length L in mm at a 12 mm height. Columns are 2f as-assigned (limiting face) / 2f balanced / 1f.

| id | what | C_F / C_B mm2 | U 0.43 | **U 0.50** | **U 0.60** | U 0.65 | pred. 2f (U central, floor, routing) | pred. 1f | eta needed |
|---|---|---|---|---|---|---|---|---|---|
| a | Rev F as-is, clamp bands | 172.1 / 87.3 | 38.4F / 28.9 / 53.6 | 33.2F / 25.0 / 46.2 | 27.9F / 21.0 / 38.6 | 25.9F / 19.4 / 35.7 | **33.2 x 12 = 398** (area) | 46.2 | 0.16 |
| a+B | + lid-hung (no bands; pins/VHB/back-stop), hand pads -> B | 130.7 / 128.7 | 29.1F / 28.5 / 51.8 | 25.4F / 24.8 / 44.8 | 21.6F / 21.0 / 37.6 | 20.1F / 19.5 / 34.8 | **25.4 x 12 = 305** | 44.8 | 0.18 |
| a0 | + L1 maker land (same parts) | 127.4 / 128.7 | 28.4F / 28.2 / 51.2 | 24.8F / 24.5 / 44.2 | 21.1F / 20.8 / 37.1 | 19.6F / 19.3 / 34.4 | **24.8 x 12 = 298** | 44.2 | 0.18 |
| b | + 0201 (C15 stays 0402), 0603 -> 0402 | 112.3 / 108.6 | 25.4F / 24.6 / 44.0 | 22.1F / 21.4 / 38.1 | 18.9F / 18.2 / 32.0 | 17.6F / 16.9 / 29.6 | **22.1 x 12 = 265** | 38.1 | 0.19 |
| c | b + FC-12M 2012, DFE201210U, R21 0402 | 106.3 / 100.1 | 24.1F / 23.1 / 41.0 | 21.1F / 20.2 / 35.5 | 18.0F / 17.1 / 29.9 | 16.8F / 16.0 / 27.7 | **21.1 x 12 = 253** | 35.5 | 0.20 |
| c+ | c + CM9V 1610 + SOD-523 | 105.2 / 97.5 | 23.9F / 22.7 / 40.3 | 20.9F / 19.8 / 34.9 | 17.8F / 16.9 / 29.3 | 16.7F / 15.7 / 27.2 | 20.9 x 12 = 251 | 34.9 | 0.20 |
| c_e' | c + pads trimmed (no WLCSP) | 106.3 / 84.7 | 24.1F / 21.5 / 37.9 | 21.1F / 18.8 / 32.8 | 18.0F / 16.0 / 27.6 | 16.8F / 14.9 / 25.6 | 21.1 (bal 18.8) | 32.8 | 0.20 |
| d | c + WLCSP90 (tight cy) + via-in-pad, 0.2/0.1 vias | 61.7 / 100.1 | 22.1B / 18.5 / 31.9 | 19.2B / 16.2 / 27.7 | 16.3B / 13.9 / 23.3 | 15.1B / 13.0 / 21.7 | **16.3 x 12 = 196** (U 0.60; bal 13.9 -> floor 14.6) | 23.3 | 0.25 |
| d_ks | d, KiCad stock WLCSP cy | 77.6 / 100.1 | 22.1B / 20.2 / 35.2 | 19.2B / 17.6 / 30.5 | 16.3B / 15.0 / 25.7 | 15.1B / 14.0 / 23.8 | 16.3 | 25.7 | 0.25 |
| e | d + J pads off-board | 61.7 / 65.3 | 15.0F / 15.0 / 24.8 | 13.3F / 13.2 / 21.6 | 11.5F / 11.3 / 18.3 | 10.8F / 10.6 / 17.0 | **14.6 x 12 = 175** (mic-noise floor binds; area 11.5) | 18.3 | 0.26 |
| e' | d + J pads trimmed | 61.7 / 84.7 | 18.9B / 17.0 / 28.8 | 16.5B / 14.9 / 25.0 | 14.0B / 12.7 / 21.1 | 13.1B / 11.9 / 19.6 | 14.6 (floor; area 14.0) | 21.1 | 0.26 |
| e0 | a0 + J pads off-board only | 127.4 / 94.0 | 28.4F / 24.6 / 44.1 | 24.8F / 21.5 / 38.1 | 21.1F / 18.2 / 32.1 | 19.6F / 17.0 / 29.7 | 24.8 (bal 21.5) | 38.1 | 0.18 |

Reading the table:
- **"As-assigned" flips to B once the MCU shrinks (d).** Then the charger, LDO, VBAT-sense or bridge parts must move to F (none is access-constrained) to reach the balanced figure.
- **e0 shows that taking the pads off only pays if the faces are rebalanced.** In e0, F stays limiting.
- **1f means all parts on B (cell side) and SW1 alone on F.** The mic is bottom-port and on B already, so its port still goes through the board to the lid.

## 6. Two faces vs one face

```yaml
2f: smaller outline (a+B 25.4 -> d 16.3 mm) but keeps both height bands. Board length below ~26-28 mm buys no pod volume (cell 35 x 12 sets L and H; size.md §0.7, §4.2); only rear wire-stowage (SIZ-14)
1f_B: (all on B, SW1 alone on F in a lid pocket)
  gain: F band deleted except at SW1. Pod thickness about -1.0 to -1.25 mm (S1 F gap 1.0-1.25 + clearance; SW1 0.65 nominal sits in the lid's 1.5 mm wall incl. plate) [estimate; mech lane to verify]. Thickness off the temple is comfort item #2 (size.md §2)
  fits_cell_length: Rev F parts 44.8 mm NO | c 35.5 (U .50) / 29.9 (U .60): only by eating the 10 mm stowage zone | d 27.7 / 23.3 YES | e' 25.0 / 21.1 YES
  costs:
    - heat sources (U3 charger, U4 LDO, bridge) face the cell (R23) [TBD thermal]
    - B gap must clear mic 1.08 mm + cell swelling margin: unchanged 1.4 (SIZ-03 keeps it)
    - SW1 alone on F: still a second side to assemble (JLC setup/stencil), or SW1 hand-soldered (assembly.md S1: -$33.77 setup/stencil, +$3.84 hand work)
    - L1 and bridge must stay >= 10 mm from the mic on ONE face: the floor still holds; easy at L >= 23
    - lid-hung bond: F becomes a flat bonding face (good for SIZ-02 VHB; mic seal ring sits on a part-free face)
1f_F: (all on the lid side) rejected again: needs a top-port mic with no ultrasonic spec (size.md §9, SPK0641HT4H-1)
```

## 7. Measures (for the structured summary)

| id | measure | board effect (U central) | risk / cost | owner | conf |
|---|---|---|---|---|---|
| AM-01 | Rebalance faces: hand pads (J, TP1-6) to B (= Package B ASM-09/SIZ-02) + lid-hung, no clamp bands | 398 -> 305 mm2 (33.2 -> 25.4 mm) | none electrical; it is Package B (awaiting review) | yes (Package B) | medium |
| AM-02 | L1 on Murata's land (KiCad L_Murata_DFE201610P) instead of the easyeda land; same part | cy -3.3; L -0.6 mm (-7 mm2) | footprint swap only; JLCDFM check | no (footprint fix) | high |
| AM-03 | 0201 passives (34 parts; C15 stays 0402) + 0603 bulk -> 0402 | cy -35; L -2.7 mm (-32 mm2) | all 0201 Extended (fee per line unchanged, $1.53 any class: assembly.md); DC-bias derating on 2.2-4.7 uF 0201 and 10/22 uF 0402; harder rework (O19 serviceability) | yes | medium |
| AM-04 | Crystal FC-12M 2012 (or CM9V-T1A 1610) + R21 0402 (OUT-02) + L1 DFE201210U | cy -14.5 to -18; L -1.0 mm (-12 mm2) | L1 2012 fails ST DCR < 200 mOhm (228 max): take only crystal + R21 unless ST margin is shown | yes | medium |
| AM-05 | U1 -> WLCSP90 STM32U575OIY6QTR with via-in-pad, 0.2/0.1 vias | cy -44.7; 2f 21.1 -> 16.3 mm (U .50 -> .60; at equal U .50: 19.2 / bal 16.2); 1f 35.5 -> 23.3 | 10 in stock (O21 risk); 0.4 mm pitch, 0.225 pads, X-ray only, no probing or rework (O18, O19); bare silicon light-sensitive (A1-A2 note) vs translucent case idea; via-in-pad on 4-layer cost [TBD]; pin-contract re-map | yes | low-medium |
| AM-06 | J wire pads off the faces (castellated rear edge or flex tail) or trimmed (SIZ-10) | cy -37 / -17; no gain until faces rebalance; floor-bound after d | castellations need hole-to-edge rules on a 0.8 mm board; solder access after lid-hung bond; J3/J5 spacing (IB-15) | yes | low |
| AM-07 | One-face board (all on B, SW1 alone on F) | pod thickness about -1.0 to -1.25 mm; board 23-28 mm long with d | thermal on the cell side (R23); needs d (WLCSP) to keep the stowage zone | yes + mech lane | low-medium |
| AM-08 | Smaller through vias 0.2/0.1 (board <= 1 mm, ENIG) even without WLCSP | via squares 22.8 -> 9.9 mm2/layer (about +0.03-0.04 U) | small-via surcharge already applies at 0.15/0.35 [TBD whether 0.1 adds more] | no (process choice) | medium |

## 8. Limits of the method (honest)

- **Area bound, not a placement.** Courtyards are summed and divided by U. Real lower limits that are local and invisible to this model:
  - QFN-48 0.5 mm and WLCSP 0.4 mm fan-out channels: the 7 then 2 unconnected on the 34 mm draft were escape and placement problems, not area (reg-board, ECR-0002).
  - The 0.4 mm DSBGA charger U3's ball escape.
  - The mic seal ring that must stay via-free (r1.6).
  - L1 vs the dock magnets (sim-study: 28 not 26 mm).
  - SW1 and the mic on the centre line (O16(5)).
  - Bridge and L1 at least 10 mm from the mic (floor 14.6-16 mm, [estimate], until the layout-noise sim reruns: docs/sim/, sim/noise).
- **U is calibrated on two boards only,** one of them a different netlist with 4 signal layers and no GND plane. 0.50 / 0.60 are judgements. A 0.05 change in U moves L by about 2 mm in the a-c range.
- **Height bands:** the model is 2D. The 1.2 mm F/B bands (shell_r1 PARTS), clamp bands (0.6 mm on the long edges, modelled in a only) and part heights (tools/checks/part_heights.yaml: tallest mic 1.08 on B, L1 1.00 on F) are not area. The 0201 and WLCSP parts are all lower (WLCSP 0.59 max), so heights only improve. A 1f board puts everything inside the B gap (mic 1.08 is the tallest).
- **Routing bound:** wirelength is scaled by sqrt(area) from the autorouted Rev F (detours included). Required eta 0.18-0.26 vs a demonstrated 0.13. Plausible by hand (O14) but unproven below about 230 mm2.
- **Keep-out sizes:** the 4 VHB spots (9 mm2) are guessed. The NPTH ring and back-stop come from the sim-study text, not a drawing.
- **Courtyards of easyeda parts** are re-derived from pads + body (BODY table in the script). SW1's 13.3 mm2 comes from its real pad span (3.8 mm); D5 and U6 grow 3x vs their drawn courtyards.
- **No electrical, thermal, acoustic or noise effect is modelled.** Phase-1 layout-dependent evidence is provisional (two-phase guardrail 2). Every Phase-2 outline must rerun the noise, acoustics and thermal sims (O22 criterion 4).

## 9. Integration-map cross-check (per proposal; `tools/plm.py impact` run 2026-10-02 on gen.py, place_r1.py)

```yaml
functions: F1 mic (AM-07: mic stays on B, port through board unchanged; seal ring kept as K_F), F2 (AM-04/05: Y1 load caps, L1 DCR spec, U1 package), F3/F4 (AM-04 R21 0402 = OUT-02), F5/F10 (AM-06 dock pads J3/J4/J10-J12), F11 (AM-07 SW1 alone on F), F14 (AM-05 kills probe access to U1 pins; TPs stay)
nets_pins: AM-05 changes every U1 pin number (UFQFPN48 -> WLCSP90 ballout) -> pin-contract.yaml, system_map.py, gen.py symbol; logic unchanged. Others: footprint/value only
rails: AM-03 derating on +3V0 (C4/C7/C14), VSYS (C17/C21), VDD11 (C8/C9), VBAT (C16) -> rail-budget.yaml [TBD]
mechanical: relations R-BOARD-BODY (outline, bands), R-AUDIO-BOARD/R-AUDIO-BODY (mic port), R-UI-BODY (SW1), R-BOARD-ARM (rear pads), R-DOCK-BOARD, R-PWR-BOARD, R-OUT-BOARD, R-DEBUG-BOARD, R-PROC-BOARD all watch place_r1.py -> any outline change re-checks them
firmware: AM-04 crystal -> LSE drive/load (firmware knob LSEDRV); AM-05 none beyond pin map
owner_decisions_touched: O8 (not touched), 5-contact dock (not touched), R4/R6 kept (not touched), O16(5) centre line, O18/O19 (AM-05, AM-03), O20 (size), O21 (WLCSP stock 10), O22 (sims rerun)
reversals_needing_owner_call: none proposed as done. AM-01 is Package B (pending her review); AM-05/AM-07 are new owner calls
```

## 10. Open questions

1. Owner: is ~1 mm of pod thickness (1f) worth a WLCSP MCU (no probing or rework, X-ray only, 10 in stock)? Or should she stay 2f with a QFN at ~25 x 12?
2. Mech lane: can SW1 sit alone in a lid pocket (1f), and what F-gap thickness does that really save?
3. Noise lane: what mic-to-switcher separation does sim/noise allow at 12 mm board height? It sets the 14.6-16 mm floor.
4. JLC: via-in-pad (epoxy filled and capped) and 0.1/0.2 vias on a 4-layer 0.8 mm board, price and availability; JLCDFM on the WLCSP90 0.225 mm pads.
5. ST margin: does DFE201210U's 228 mOhm max DCR still meet the SMPS efficiency/stability need? ST asks for < 200.
6. VHB spot size and the SW1 back-stop footprint: real numbers from the mech lane.
7. 0201/0402 DC-bias derating per rail (2.2-4.7 uF 0201, 10/22 uF 0402): which caps stay larger.

## 11. Sources (read 2026-10-02)

- Boards: hw/pod/draft_r1/pod_r1_routed.kicad_pcb (Rev F, commits 4b2c058, e25f35f); hw/pod/draft/pod_routed.kicad_pcb (commit 6e93246); pcbnew KiCad 10.
- KiCad 10 stock footprints /usr/share/kicad/footprints: Resistor_SMD, Capacitor_SMD, Crystal (2012, 3215), Inductor_SMD (L_Murata_DFE201610P, L_TDK_MLZ1608, L_0603_1608Metric), Package_CSP (ST_WLCSP-90_4.2x3.95mm_Layout18x10_P0.4mm_Stagger), Package_DFN_QFN (QFN-48 7x7), Diode_SMD (SOD-323, SOD-523).
- ST DS13737 Rev 10 (July 2024), local copy From Valkyrie/Datasheets/DS_stm32u575ag.pdf: Table 157 WLCSP90 (D 4.20, E 3.95, A 0.59 max, e 0.40), Table 158 (Dpad 0.225), §5.1.6 SMPS inductor (2.2 uH, ISAT > 0.5 A, DCR < 200 mOhm).
- Murata DFE201210U reference spec (PDF 2017-04-18), ultrasonic-scratch/ds/dfe201210u.pdf: 2R2M DCR 228 mOhm max.
- lcsc.com/product-detail/C76797.html (TDK MLZ1608A2R2WT000) and C337910.html (Murata LQM18PN2R2MFRL), read 2026-10-02.
- jlcpcb.com/capabilities/pcb-capabilities, read 2026-10-02. PCBA capability via docs/research/simplify/assembly.md (page read 2026-10-02).
- JLC parts API (tools/jlc.py) 2026-10-03T00:41Z and 00:48Z: every LCSC number, stock and price above.
- Repo: docs/research/simplify/size.md, simplification-study.md, assembly.md; docs/system/integration-map.md, reg-board.md, sub-audio-in.md, sub-output.md, physical.md; tools/checks/part_heights.yaml; hw/pod/place_r1.py, gen.py.
