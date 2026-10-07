# Audio in: ultrasonic mic, acoustic port, PDM capture
Rev MZ-2 2026-10-07: body rewritten to the Phase-2 design (`hw/current.yaml`, ECR-0018): U2 on the one-face board at (2.65, 6.0), port (1.88, 6.0) = pod 32.43; sealed D1.0 duct + gauge pin (O24 option B) replaces the open gap; acoustics `phase2_r2`; layout noise on the routed Phase-2 board; R2 now at the PB3 end; R2/C13 0201. Rev F/G facts moved to the last section.
Status: schematic = Rev G nets with the MZ-2 package set (`POD_PACKAGES=mz2 python3 hw/pod/gen.py` -> `hw/pod/pod_mz2.net`; bom_check netlist/nets PASS, 195 pin-net assignments, 2026-10-07); board `hw/pod/draft_r2/out/routed.kicad_pcb` routed, DRC 0, 0 unconnected (ECR-0018 log 2026-10-07); shell `hw/mech/shell_r2.py` (constants `hw/mech/dims_r2.py`); interfaces.py [mic-port] PASS 2026-10-07. Updated 2026-10-07.
· Source of truth: `hw/pod/gen.py` (mic block; MZ2 table L93-112), the routed board above, `hw/mech/dims_r2.py` (MIC, DUCT_D, HEX_R/HEX_DEPTH, `board_mic()`, `duct_offsets()`), `hw/mech/shell_r2.py::lid_base` (bore + hex window) · Owner decisions: O9, O12, O16-5, O19, O24 (sealed duct ID 1.0 + x-stop/locating feature + EQ notch), O26/O27 (Phase 2) · Open ECRs: ECR-0008 (supply: add U2 to the reservation list), ECR-0018 (Phase 2, approved, owner review pending)

## Purpose
- Carries **F1 Hear 20-85 kHz** (`integration-map.md` §1) from air to PCM samples in RAM. Everything after that is `sub-processing.md` (F2).
- Must be **off in Off mode** (D12, `docs/spec.md` line 221): no mic current when the pod is "off".
- Must not hear the pod itself: bridge PWM noise, core SMPS, own speech/chewing (§1.2.3, T6; risks R8, R14, R15; MP-01).
- One board serves both pods, so the port sits on the board centre line y 6.0 (O16-5; dims_r2.py `bpt` docstring: the right pod's mirror flips board y, mic and SW1 sit on y 6.0).

## Big picture
![Block schematic, rev 1 (mic top right)](../diagrams/schematic-rev1.png)
![Acoustic port model: path response, Phase-2 duct (sim/acoustics/port.py, 2026-10-07)](../../sim/acoustics/out/port_path.png)

The chain as built in Phase 2 (pod y, `hw/mech/dims_r2.py`; acoustic stack from `sim/acoustics/out/port_results.json` scenarios.phase2_r2.stack_mm, 2026-10-07):
```
sound -> plate hex window (circumradius 1.9, 0.8 deep from the plate top y 14.7 = mesh seat, no mesh yet)
      -> reamed lid bore D1.0 (0.7 long, to the lid inner face y 13.2)
      -> D1.0 hole in the 0.25 VHB across the 0.30 F gap (SEALED: VHB bonds board F face to the lid)
      -> board hole NPTH D0.6 (0.8 long, y 12.9 -> 12.1) -> mic port D0.325 -> MEMS diaphragm (U2 on B)
PA5 (GPIO high) ---------------- MIC_VDD (C13 100n 0201) -> U2 VDD
PB3 ADF1_CCK0 -> R2 33R (at the MCU end, N$2 1.2 mm) -> MIC_CLK 9.5 mm (B) -> U2 CLOCK  4.0004 MHz
U2 DATA ------- MIC_DATA 4.6 mm (B) --> PB4 ADF1_SDI0 -> CIC5 /5 (800 kS/s) -> RSFLT /4 -> 200 kS/s -> GPDMA -> SRAM
```
(net lengths: pcbnew probe of the routed board, fenced, 2026-10-07)
How it works:
- The mic is a bottom-port MEMS part on the board's inner face (B, toward the cell). Sound enters through the lid, runs down a sealed straight duct of ID 1.0 (lid bore + VHB hole), crosses the board through a 0.6 mm hole and reaches the mic's own 0.325 mm port. The VHB that hangs the board from the lid is the duct's seal: there is no side cavity (spec §8 "no gasket cavity": PASS, side volume 0.0 mm3, port_results.json spec_checks.phase2_r2, 2026-10-07).
- Its output is 1-bit PDM (pulse-density modulation) at the clock rate. The MCU's ADF1 (audio digital filter, a hardware sigma-delta decimator) turns it into 24-bit samples at 200 kS/s with zero CPU (A3-u575-plan.md §1.2, option D1).
- The mic's supply is a GPIO (PA5). Driving PA5 low removes the mic's power completely; its own sleep mode would still draw ~80 µA (mic datasheet, Syntiant Rev B-1, p.2), 10-20x the MCU's Stop 2 current.
- Every rate is an integer ratio of one clock (mic clock = HCLK/20, PCM = PWM = HCLK/400), so bridge-carrier leakage folds to 0 Hz (D14, `spec.md` line 249). Shaped PWM *noise* does not fold away (MP-01, below).
- Alignment: the bore is the datum. While bonding, a stepped gauge pin (D0.98 body in the bore, D0.50 tip in the board hole) registers VHB and board to the bore; the front skirt wall is only a coarse x-stop 0.25 mm ahead of the board and never fights the pin (`shell_r2.py` docstring; `dims_r2.duct_offsets()`).

## Elements
| Ref / feature | What it is | LCSC · class | Where (Phase-2 board / shell) | Why |
|---|---|---|---|---|
| U2 | **SPH0641LU4H-1**: Knowles (now Syntiant) PDM MEMS microphone with an ultrasonic mode, 3.50 x 2.65 x 0.98 mm (1.08 incl. solder, part_heights.yaml), bottom port | C2879853 · Extended | B, origin board (2.65, 6.0) rot 90; port 0.77 mm from the origin -> (1.88, 6.0) (routed board read by `dims_r2.board_mic()`, 2026-10-07) | Only JLC-stocked mic characterised to 80 kHz (D13; A1-A2-mcu-and-mic.md §A2) |
| U2 SELECT | Left/right select pin, tied to GND | - | - | Must not float (D13). SEL = GND: mic asserts DATA on the falling edge; the receiver latches on the **rising** edge (mic datasheet p.8 table) |
| R2 | 33 R 0201 (0201WMF330JTEE), series on the clock | C473457 · Basic/lock (bom_jlc_mz2.csv "yes") | B (5.48, 7.75) rot -90, **MCU end**: R2.1 N$2 (5.48, 7.43), R2.2 MIC_CLK (5.48, 8.07) | Source-series termination: the 9.5 mm MIC_CLK run carries the softened edge |
| C13 | 100 nF 10 V X5R 0201 (Murata GRM033R61A104KE15D) | C76934 · lock "yes" | B (5.12, 5.4): MIC_VDD pad (5.12, 5.08) | Mic VDD bypass. X5R (Class 2) breaks the datasheet's "no Class 2 near the mic"; no small C0G reaches 100 nF (B-parts-selection.md, Class-1 note) |
| Board port | NPTH D0.6 in footprint `Knowles_LGA-5_3.5x2.65mm_Port0.6` | - | board (1.88, 6.0) = pod (32.43, -2.45) (dims_r2.MIC; interfaces.py [mic-port] 0.000 mm, 2026-10-07) | Spec §8: short, wide (0.6-1.0 mm), board <= 0.8 mm (S8-board/S8-hole PASS, port_results.json 2026-10-07) |
| Board | 30 x 12 x 0.8, 4 layers: F sig / In1 GND plane / In2 +3V0 plane / B sig | - | - | Short duct (§8); In1 shields mic nets on B from F-side traffic (reg-board) |
| VHB duct hole | D1.0 hole in the 0.25 mm 3M VHB 4914 sheet (DUCT_D) | - | on the bore axis | Seals the 0.30 F gap round the board hole (`shell_r2.vhb()`) |
| Lid bore | D1.0, printed undersize and reamed with a 1.0 drill (1.00-1.02 [A]) | - | pod (32.43, -2.45), y 13.2-13.9 | `dims_r2.DUCT_D`, `shell_r2.lid_base` |
| Hex window | circumradius 1.9, 0.8 deep from the plate top: the mesh seat | - | same axis | `dims_r2.HEX_R/HEX_DEPTH`; shell_r2 comment "hex window = mesh seat" |
| Gauge pin | stepped, turned brass [A]: body D0.98, tip D0.50, runout 0.02 | tool, not a part | in the bore during bonding only | `dims_r2.duct_offsets()` tolerances |
| Mesh | **None chosen** (S8-mesh FAIL, port_results.json 2026-10-07; spec task D2) | - | modelled at the window floor (`phase2_r2+mesh_floor`) | - |
| MCU side | PA5 GPIO (supply), ADF1 on PB3/PB4 (AF3), GPDMA | in U1 | U1 B (10.05, 5.4) | See `sub-processing.md` |

Backup mic, not fitted: **TDK T5838** (PDM mic with an ultrasonic mode, characterised to 50 kHz only), C7230692 (D13).

## Interfaces
| To | Nets / pins (as integration-map.md) | What crosses | Notes |
|---|---|---|---|
| [sub-processing](sub-processing.md) | MIC_VDD = U1.15 PA5; N$2 = U1.39 PB3 (-> R2 -> MIC_CLK); MIC_DATA = U1.40 PB4 | supply, 4 MHz clock out, PDM in | ADF1 config, mic start-up sequence, EQ (notch target now ~63 kHz, see Key numbers), idle detector (F2). Rel R-AUDIO-PROC |
| [sub-power](sub-power.md) | +3V0 (In2 plane, through the PA5 output driver), GND (In1) | 1.1 / 1.35 / 2.15 mA | power.py rev 2 at 3.0 V / 4 MHz |
| [sub-output](sub-output.md) | none electrical; shared GND/+3V0 | PWM noise, 200 kHz gate edges, exciter vibration | MIC_VDD runs 0.90 mm edge-to-edge from GA_N and 1.41 mm from BRIDGE_RTN, both on B near (13.5-14.2, 3.5-3.7) (probe 2026-10-07); LN-M01 PASS (Key numbers) |
| [sub-debug-test](sub-debug-test.md) | TP10 MIC_DATA dot (3.1, 8.25) B; MDF fallback TP8 (3.5, 3.85) / TP9 (2.05, 8.25) B; R2 pads = MIC_CLK probe | mic stream checked over USB; duty at R2.2 | all on B: reachable with the lid lifted (board hangs from the lid, B faces the cell) |
| [reg-board](reg-board.md) | U2 B (2.65, 6.0) rot 90, port NPTH (1.88, 6.0) on the centre line; mic nets all on B except MIC_VDD (F 12.1 + B 5.5 mm, 2 vias) | keep-outs; noisy parts >= 13 mm away | port -> nearest pad: C7 13.7, L1 13.8, Q1 15.9, R21 17.1, U3 17.4, Q2 19.0, U4 20.8 mm; nearest via 2.05 mm (GND) (probe 2026-10-07). Rel R-AUDIO-BOARD |
| [reg-pod-body](reg-pod-body.md) / [physical](physical.md) | lid bore + hex window at pod (32.43, -2.45); VHB duct hole; gauge pin at bonding | the acoustic duct; sealed (no water path past the VHB) | interfaces.py [mic-port] 0.000 mm nominal, worst-case margin 0.00 at limit 0.20 (PASS, 2026-10-07). Rel R-AUDIO-BODY |

Firmware dependencies (integration-map §8): ADF1 on PB3/PB4 at 4 MHz; PA5 is a supply pin, not I/O.

## Constraints
- **D13** (`spec.md` 224-239): never power up or wake straight into ultrasonic mode; start at 1.024-2.475 MHz (plan: 2.0 MHz), wait, then switch; clock duty 48-52 % above 2.4 MHz; SELECT tied; no Class-2 caps near the mic.
- **D14 / A3-u575-plan.md §1**: ADF clock divider changes only with the filter stopped (stop, re-divide, restart). Keep CCKDIV+1 even (only route to 50 % duty; ST specifies no duty).
- **D12**: Off = mic unpowered (PA5 low).
- **§8 acoustic rules**: board <= 0.8 mm; port 0.6-1.0 mm; **no gasket cavity**; opening directly over the hole; thin mesh, never foam. Phase 2: all PASS except mesh (port_results.json spec_checks.phase2_r2, 2026-10-07).
- **O24 (1)**: sealed straight duct ID 1.0 lid bore -> board hole, with a locating feature (gauge pin + x-stop) and an EQ notch.
- **R-ACO-P5 alignment**: bore axis vs hole axis <= r_duct - r_hole = 0.20 mm (`dims_r2.duct_offsets()` limit_R_ACO_P5).
- **O16-5**: port on the board centre line, identical in both pods. **O12**: IPX4 minimum, IPX5 preferred.
- **D11 / §1.2.3**: self-noise no louder than ambient; SMPS and bridge stay away from the mic (>= 10 mm, MZG-04; met: >= 13.7 mm).
- Mic datasheet (Syntiant Rev B-1): clock rise/fall tEDGE <= 3 ns (p.4); DATA load CLOAD <= 140 pF, VDD 1.62-3.6 V (p.2); bypass caps near VDD must not be Class 2 (p.8).

## Key numbers
| Quantity | Value | Source | Date |
|---|---|---|---|
| Ultrasonic-mode clock range | 3.072-4.8 MHz | mic datasheet (Syntiant Rev B-1) p.2; D13 | 2024-12-02 |
| Our mic clock | 4.0004 MHz (HCLK 80.009 / 20) | A3-u575-plan.md §2 table P80 | 2026-09-30 |
| PCM rate / passband edge | 200.02 kS/s; RSFLT edge 88.8 kHz | A3 §1.2 (D1), `[Unverified]` at 800 kHz | 2026-09-30 |
| CIC droop at 85 kHz; alias floor | -0.78 dB; ~-70 dB above ~120 kHz, 115-120 kHz only partly | A3 §1.2 | 2026-09-30 |
| Sensitivity | -26 dBFS +-1 dB at 94 dB SPL, 1 kHz | datasheet p.3 (ultrasonic table) | 2024-12-02 |
| SNR / AOP | 64.3 dB(A) (audio band only) / 120 dB SPL | datasheet p.3 | 2024-12-02 |
| Ultrasonic noise floor | **unknown** (not specified; E3) | A1-A2 §A2 | 2026-09-30 |
| Response re 1 kHz (fixture) | +1.6 dB at 10 kHz, **+14.7 dB at 25 kHz**, ~+8 dB 35-65 kHz, +12.7 dB at 80 kHz | `sim/data/sph0641_ultrasonic_response.json` (Rev B sheet 7, 1.8 V, 3.072 MHz) | 2026-09-30 |
| PSRR | 55 dBV/FS at 1 kHz only; nothing at 200 kHz or 3 MHz | datasheet p.3 | 2024-12-02 |
| Mic current at 3.0 V / 4 MHz | 1.1 / 1.35 / 2.15 mA (low/nom/high) | `sim/checks/power.py` lines 22-24; spec §7 v0.14 | 2026-09-30 |
| PA5 output drop | VOH >= VDD - 0.4 V at 4 mA, so MIC_VDD >= 2.6 V | DS13737 Rev 10 Table 94, p.232 | Jul 2024 |
| Power-up / mode change | <= 50 ms / <= 10 ms | datasheet p.2 | 2024-12-02 |
| Sleep current (why PA5) | 80 µA typ | datasheet p.2 | 2024-12-02 |
| Port: mic / board hole / duct | D0.325 +-0.05 / D0.6 (+-0.05 [A]) / D1.0 (reamed 1.00-1.02 [A]) | datasheet p.9; footprint; dims_r2.py | 2026-10-07 |
| Duct stack (Phase 2) | window 0.8 + bore 0.7 + sealed VHB/gap 0.30 + board 0.8 | port_results.json scenarios.phase2_r2.stack_mm | 2026-10-07 |
| Bore vs hole offset | **0.000 mm** nominal; worst with the gauge pin 0.155 mm <= 0.20 PASS; walls alone would allow 0.86 (FAIL), so the pin is required; walls never fight the pin | `dims_r2.duct_offsets()` (run 2026-10-07); interfaces.py [mic-port] | 2026-10-07 |
| Path response, phase2_r2 nominal | mean 20-96 kHz **+5.6 dB**; peaks 18.5 kHz +11.7 dB Q4.8, **63.0 kHz +18.5 dB Q6.4**; notch 26.0 kHz -7.8 dB; p2p 26.3 dB | port_results.json scenarios.phase2_r2; scratchpad v_aco.txt (sim/acoustics run) | 2026-10-07 |
| Same with a mesh on the window floor | mean +5.1 dB; 63.0 kHz peak trimmed to +16.0 dB (Q4.7) | port_results.json `phase2_r2+mesh_floor` | 2026-10-07 |
| In-pod (datasheet x path) 20-85 kHz | deepest -8.6 dB re median at 26.2 kHz; highest +11.5 dB at 63.6 kHz: R14 notch/peak PASS; EQ notch target ~63 kHz | port_results.json spec_checks.phase2_r2 (R14-notch, R14-peak) | 2026-10-07 |
| Monte Carlo phase2_r2 | mean 20-96 kHz p05/p50/p95 -0.09 / 4.30 / 8.13 dB; peak re median p95 17.5 dB; R14 all-pass 0.57 (20-85 kHz), 0.68 (20-80 kHz); **n 40 in the file on disk** (ECR-0018 log quotes an n 60 run: p50 4.51, all-pass 0.70) | port_results.json mc_summary.phase2_r2 | 2026-10-07 |
| Layout noise LN-M01 (mic supply spur margin) | 26.5 dB pessimistic PASS (nominal 46.5, worst 14.0 at A01 SMPS 28 MHz -> 39 kHz); sign-off >= 10 | `sim/noise/out_r2/budget.json` metrics (board sha da4e8b13 = current routed board) | 2026-10-07 |
| Layout noise LN-M02 (PDM line pickup) | 20.1 dB vs >= 12 PASS, flagged REVIEW (inside the +-10 dB L2 model error): F03 PDM clock -> MIC_CLK, magnetic | same | 2026-10-07 |
| Shaped PWM noise in the mic band | -35 dB re FS (bridge V), -59 dB (coil I) at 200 kHz | spec D6 MP-01; `sim/checks/pwm_ultrasonic_leak.py` | 2026-09-30 |
| JLC stock / price | 960 · $1.99 (Extended) | JLC parts API audit query; bom.md $1.9915 | 2026-10-02T00:44Z |
| ADF current | ~40 µA at 80 MHz (MDF ~0.28 mA) | A3 §1.4 (DS Table 72) | 2026-09-30 |

## Open issues (IDs stable; gaps = closed, see git)
2. **CLOSED in Phase 2 (O24, ECR-0018): seal between board and lid.** The VHB that hangs the board carries a D1.0 duct hole; spec §8 "no gasket cavity" PASS (side volume 0.0 mm3). Residual: VHB hole registration to the bore relies on the gauge pin (process step, physical.md).
3. **Mesh picked 2026-10-07 (analysis; buying waits for O21): Saatifil Acoustex 042 (performance grade: 42 MKS rayl, 29 % open, 46 µm, polyester; Saati TDS via marianinc.com, PDF mod 2024-09-26, SHA-256 dba5071d3a0dfcb1) on the hex-seat floor.** `sim/checks/mesh_pick.py` (phase2_r2 duct, mesh inertance added to the model: m = ρ(t + 1.7a)/open area; resistance ×1-×2 for ultrasonic viscous rise [A]): at the floor it costs −1.2 dB of the 20-96 kHz mean (−1.9 at 2× resistance) and cuts the duct peak +18.5 → +14.3 dB (−4.2; −6.6 at 2×), pulling it from 63.0 to ~56 kHz (the inertance; a resistance-only model missed that shift). At the window mouth every thin candidate (026/030/042/020/065) changes the mean ≤ 0.4 dB and leaves the peak alone. Alternatives: Acoustex 030 floor (−0.9 dB mean, −3.3 dB peak, less particle protection: 30.6 vs 21.4 mg metal dust); any of them at the mouth (no acoustic effect, no peak help). Still open: hydrophobic treatment (not on the sheet; sealing note), real ultrasonic transmission (coupon test, issue 4), and buying it (O21). Waterproof membranes are out: `sim/checks/membrane_loss.py` gives −5.4 dB (mouth) / −10.7 dB (floor) mean at 5 g/m², −11 to −22 dB at 10-20 g/m², with ±10 dB ripple; water protection = hydrophobic finish on the open mesh (~2.7 kPa Laplace hold at 42 µm [derived]; IPX5 to be tested), see sealing-and-service.md S3.
4. **Acoustic coupons vs O9.** Options: (a) JLC coupon panel, 0.6/0.8/1.0 mm holes; (b) the rev-1 board plus printed lid variants (bore, VHB hole, mesh); (c) both. **Recommend (b)**: the lid is where the duct is uncertain and prints cost nothing. Owner decides. The model is nominal + MC only; no measurement.
5. **Clock duty cycle unknown; hand-wire fallback.** ST specifies no CCK duty (A3 §1.1). Fallback (gen.py MDF dots): lift R2, wire TP8 (3.5, 3.85) to R2.2 = MIC_CLK (5.48, 8.07), TP9 (2.05, 8.25) to TP10 (3.1, 8.25); firmware moves the mic to MDF1 (sub-debug-test mdf_fallback). *Closes it:* scope R2.2 (E6) on board 1.
6. RSFLT response at 800 kHz unpublished (R18). *Closes it:* swept tone, D1 vs D2 decimation, on the first board.
7. **MIC_VDD noise.** PA5 (pin 15) sits 2 pins from GA_N (pin 17) and 5 from VLXSMPS (pin 20); MIC_VDD passes 0.90 mm from GA_N on B; no RC filter, X5R bypass only; mic PSRR unspecified above 1 kHz. Model: LN-M01 26.5 dB pessimistic, 14.0 dB worst (PASS). *Closes it:* a self-noise capture (USB stream, bridge on/off, SMPS vs LDO); a series R + C on MIC_VDD is the cheap fix if it shows.
8. **MP-01 self-hearing** (shaped PWM noise, 20-85 kHz) via rail, ground or exciter vibration. PWM rate is firmware (200/400/800 kHz). *Closes it:* S2 coupling measurement.
11. **Unpowered-mic back-feed.** Park PB3/PB4 low/analog when PA5 is low (proposed firmware rule). Firmware can't cover **reset and ROM DFU**, where PB4 is NJTRST with an internal pull-up and back-feeds MIC_DATA while MIC_VDD floats (sub-debug-test ROM table). Breaks "Off really is off" (D12) only in those states. *Closes it:* meter C13 pad (5.12, 5.08) and TP10 in reset and DFU at bring-up (sub-debug-test step 6).
12. **Acoustic diagram:** `sim/acoustics/out/port_path.png` plots the modelled path; no dimensioned CAD cross-section (lid, window, bore, VHB, board, mic) for the owner yet. `pcb-floorplan-rev1.png` is outdated. **Drawn 2026-10-07:** `docs/diagrams/duct-section.svg`, to scale, generated from dims_r2 by `docs/diagrams/make_duct_section.py` (seat, mesh, bore, VHB annulus, board hole, mic; live offset numbers).
13. **63 kHz duct resonance is the EQ target** (O24 named ~84.7 kHz for the Rev F chimney; Phase 2 moves it to 63.0 kHz, Q6.4). *Closes it:* firmware EQ notch constant set from a bench sweep on board 1 (O18 knob); spec O24 text still says 84.7 kHz (owner's record, not edited here). With the Acoustex 042 floor mesh (issue 3) the model puts the peak at ~56 kHz, +14.3 dB: the notch frequency comes from the bench sweep either way.
14. (closed 2026-10-07) MC on disk is n 60 (`sim/acoustics/out/port_results.json`, phase2 scenario), matching the ECR-0018 log (B-DOC-AUDIT-0007 item 6).
15. **Hole tolerance sourced 2026-10-07** (JLC +0.13/−0.08: the D0.6 port NPTH finishes 0.52-0.73; was assumed ±0.05). Gauge-pin worst offset 0.115 → 0.155 (≤ 0.20 PASS). **But 0.52 is below spec §8's 0.6-1.0 hole rule** (S8-hole). Options (backlog SAI-15D, owner): (A) keep D0.6 with JLC's press-fit tolerance ±0.05 (0.55-0.65: still 0.05 under the rule; pin worst 0.115); **(B, rec)** D0.65 + press-fit (0.60-0.70 meets the rule; duct limit (1.0-0.65)/2 = 0.175 vs pin worst 0.14 PASS; a footprint hole edit, no re-route; re-run acoustics); (C) D0.7 regular tolerance (0.62-0.83; limit 0.15 < pin worst 0.205: FAILS the duct stack). Print bore position 0.05 still [A] (measure a print). **Decided: option B** (decided 2026-10-07, decisions-log 9330d9c): D0.65 + JLC press-fit tolerance; footprint hole edit + acoustics re-run at the next layout pass (router). **Built (round 8):** footprint Knowles_LGA-5_3.5x2.65mm_Port0.65, hole D0.65 at board (1.90, 6.0) (moved +0.02 for 0.2075 to pad 3), duct follows (dims_r2 reads it); acoustics MC60: mean +5.93 dB (was +5.58), MC p05 +1.22, R14 all-pass 0.63 (was 0.70), duct peak 61.3 kHz +18.44 dB.

## Before you change this, check
- **Moving U2 or its footprint:** `dims_r2.board_mic()` reads U2 from the routed board, so the duct follows it automatically, but it asserts rot 90; the port (not the body) sets the duct in **both** pods (centre line y 6.0, O16-5); `reg-board.md`, `reg-pod-body.md`, `physical.md`; run `tools/checks/interfaces.py` [mic-port] and `sim/acoustics` (scenario `phase2_r2`).
- **Lid, plate, VHB thickness, mesh, board thickness:** the duct (§8 rules), sealing (O12), the 63 kHz resonance and EQ (C8), coupon plan.
- **PA5 / PB3 / PB4:** pin map (`integration-map.md` §4); ADF only exists on PB3/PB4, MDF on PB8/PB1; D12 Off current.
- **Clock or decimation:** `sub-processing.md` clock tree (integer ratios, even divider), D14.
- **Anything new near the mic** (bridge, SMPS, Class-2 caps, vias): D11, D13, MP-01; re-run `sim/noise` (LN-M01/M02).
- **Mic part swap:** `sim/data/` response, power budget (`sub-power.md`), `sim/dsp/pipeline.py` constants.
- Run `python3 tools/plm.py impact SUB-AUDIO-IN` and the cross-check in `integration-map.md` §10.

## Reference design (Rev F/G)
`ULTRASONIC_DESIGN=revg` (`hw/current.yaml` reference): two-face 34 x 13 board `hw/pod/draft_r1/pod_r1_routed.kicad_pcb`, shell `hw/mech/shell_r1.py`. U2 origin (4.67, 6.5), port (3.9, 6.5) = pod x 34.5 (ECR-0011 aligned it; Rev E was 0.77 mm off). Duct: lid bore D1.0 0.9 long + hex window, **open 1.5 mm gap** board-to-lid (no seal, a water path and a side cavity); acoustics `as_built` mean -2.5 dB (MC p05 -9.3), resonance at 84.7 kHz Q15.5 for the D1.0 chimney option. R2 0402 at the mic end of a 16.6 mm N$2 run; C13 0402 X7R. Layout noise on Rev F: LN-M01 23.1 dB, LN-M02 12.2 dB (0.2 dB margin). History: git.
