# Audio in: ultrasonic mic, acoustic port, PDM capture
**Current design (2026-10-07): Phase 2, `hw/current.yaml` (ECR-0018); every tool and check defaults to it.** U2 on B at board (2.65, 6.0), port NPTH D0.6 at (1.88, 6.0) = pod 32.43; sealed duct ID 1.0 (reamed lid bore + VHB hole across the 0.30 F gap), gauge pin locates (worst 0.115 <= 0.20 mm); acoustics default `phase2_r2`: mean +5.6 dB, resonance 63 kHz Q6.4 (EQ notch target), MC60 p50 +4.51 dB, R14 all-pass 0.70 (`docs/sim/acoustics.yaml`); R2 33R 0201 (C473457). The body below is the Rev F/G reference design (`ULTRASONIC_DESIGN=revg`) unless it says Phase 2; its Phase-2 rewrite is open.
Status: schematic Rev F (ERC 0 errors / 311 warnings, `hw/pod/gen.erc` 2026-10-02 20:01), routed draft (`pod_r1_routed.kicad_pcb`, 2026-10-02), rev-1 shell; board port and lid bore aligned in Rev F (ECR-0011, Open issue 1 closed); updated 2026-10-01, Rev F port facts synced 2026-10-02 · Source of truth: `hw/pod/gen.py` (mic block, lines 140-151), the KiCad board once placement starts (today the draft `hw/pod/draft_r1/pod_r1_routed.kicad_pcb`), `hw/mech/shell_r1.py` (lid port, lines 36-45, 102-103) · Owner decisions: O9, O12, O14, O16-5, O19 (sealing is a daily-use requirement) · Open ECRs: ECR-0008 (supply: U2 stock falling, add it to the reservation list)

## Purpose
- Carries **F1 Hear 20-85 kHz** (`integration-map.md` §1) from air to PCM samples in RAM. Everything after that is `sub-processing.md` (F2).
- Must be **off in Off mode** (D12, `docs/spec.md` line 221): no mic current when the pod is "off".
- Must not hear the pod itself: bridge PWM noise, core SMPS, own speech/chewing (§1.2.3, T6; risks R8, R14, R15; MP-01).
- One board serves both pods, so the port sits on the board centre line (O16-5, `spec.md` line 642).

## Big picture
![Block schematic, rev 1 (mic top right)](../diagrams/schematic-rev1.png)
![Rev-1 pod, exploded: the hex window at the lid's front end is the mic port](../../hw/mech/out/r1/spine/exploded.png)

**No acoustic-path cross-section exists yet** (Open issue 12). The chain as built today:
```
sound -> lid hex window (0.8 deep) -> lid bore D1.0 (0.9 long) -> OPEN 1.5 mm gap (no seal)
      -> board hole D0.6 (0.8 long) -> mic port D0.325 -> MEMS diaphragm
PA5 (GPIO high) ---------------- MIC_VDD (C13 100n) ---> U2 VDD
PB3 ADF1_CCK0 -> R2 33R -> MIC_CLK -------------------> U2 CLOCK  4.0004 MHz
U2 DATA ------- MIC_DATA ------> PB4 ADF1_SDI0 -> CIC5 /5 (800 kS/s) -> RSFLT /4 -> 200 kS/s -> GPDMA -> SRAM
```
How it works:
- The mic is a bottom-port MEMS part on the board's inner face (B). Sound enters through the lid, crosses the board through a 0.6 mm hole, and reaches the mic's own 0.325 mm port.
- Its output is 1-bit PDM (pulse-density modulation) at the clock rate. The MCU's ADF1 (audio digital filter, a hardware sigma-delta decimator) turns it into 24-bit samples at 200 kS/s with zero CPU (A3-u575-plan.md §1.2, option D1).
- The mic's supply is a GPIO (PA5). Driving PA5 low removes the mic's power completely; its own sleep mode would still draw ~80 µA (mic datasheet, Syntiant Rev B-1, p.2), 10-20x the MCU's Stop 2 current.
- Every rate is an integer ratio of one clock (mic clock = HCLK/20, PCM = PWM = HCLK/400), so bridge-carrier leakage folds to 0 Hz (D14, `spec.md` line 249). Shaped PWM *noise* does not fold away (MP-01, below).

## Elements
| Ref / feature | What it is | LCSC · class | Where (draft) | Why |
|---|---|---|---|---|
| U2 | **SPH0641LU4H-1**: Knowles (now Syntiant) PDM MEMS microphone with an ultrasonic mode, 3.50 x 2.65 x 0.98 mm, bottom port | C2879853 · Extended | B face, body origin at board (4.67, 6.5), rot 90 (ECR-0011; port at (3.9, 6.5)) | Only JLC-stocked mic characterised to 80 kHz (D13; A1-A2-mcu-and-mic.md §A2) |
| U2 SELECT | Left/right select pin, tied to GND | - | - | Must not float (D13). SEL = GND: mic asserts DATA on the falling edge; the receiver latches on the **rising** edge (mic datasheet p.8 table) |
| R2 | 33 R 0402, series on the clock | C25105 · Basic | B, (6.6, 8.0), **mic end** of a 16.6 mm run | "Tames the 4 MHz clock edge" (gen.py line 148) |
| C13 | 100 nF 16 V X7R 0402 (Samsung CL05B104KO5NNNC) | C1525 · Basic | B, (6.6, 5.0) | Mic VDD bypass. X7R breaks the datasheet's "no Class 2 near the mic"; no 0402 C0G reaches 100 nF (B-parts-selection.md, Class-1 note) |
| Board port | NPTH D0.6 in footprint `Knowles_LGA-5_3.5x2.65mm_Port0.6`; copper ring ID 1.025 | - | **board (3.9, 6.50)** = pod x 34.5, under the lid bore; 0.77 mm from the body origin (4.67) (`place_r1.py` L61, ECR-0011; interfaces.py [mic-port] 0.000 mm, 2026-10-02) | Spec §8 rule: short, wide (0.6-1.0 mm), board <= 0.8 mm (`spec.md` lines 508-512) |
| Board | 0.8 mm, 4 layers, In1 solid GND | - | - | Short duct (§8); In1 shields mic nets from F-side traffic |
| Lid bore | D1.0 through 0.9 mm of lid, drilled after printing | - | pod (34.5, ZC) = board x 3.9 | `shell_r1.py` line 102; `docs/build/tolerances.md` row "Mic port" |
| Lid hex window | Hexagonal recess, circumradius 1.9, 0.8 deep, at the outer face | - | same | `shell_r1.py` line 103. Purpose not stated in code; the only candidate mesh seat |
| Mesh | **None designed or sourced** | - | - | Spec task D2 (`spec.md` line 688) open |
| MCU side | PA5 GPIO (supply), ADF1 on PB3/PB4 (AF3), GPDMA | in U1 | - | See `sub-processing.md` |

Backup mic, not fitted: **TDK T5838** (PDM mic with an ultrasonic mode, characterised to 50 kHz only), C7230692 (D13).

## Interfaces
| To | Nets / pins (as integration-map.md) | What crosses | Notes |
|---|---|---|---|
| [sub-processing](sub-processing.md) | MIC_VDD = U1.15 PA5; N$2 = U1.39 PB3 (-> R2 -> MIC_CLK); MIC_DATA = U1.40 PB4 | supply, 4 MHz clock out, PDM in | ADF1 config, mic start-up sequence, EQ, idle detector (F2) |
| [sub-power](sub-power.md) | +3V0 (through the PA5 output driver), GND (In1) | 1.1 / 1.35 / 2.15 mA | power.py rev 2 at 3.0 V / 4 MHz |
| [sub-output](sub-output.md) | none electrical; shared GND/+3V0 | PWM noise, 200 kHz gate edges, exciter vibration | MIC_VDD runs 1.0 mm from GA_N and 1.58 mm from BRIDGE_RTN on F (draft probe) |
| [sub-debug-test](sub-debug-test.md) | no test pad on any mic net (MIC_CLK/MIC_DATA pads added in eb88de7, cut in 1c82d5c) | mic stream checked over USB instead | gen.py docstring lines 26-30 |
| [reg-board](reg-board.md) | U2 on B (origin 4.67, 6.5), port NPTH at (3.9, 6.50) on the centre line; mic nets on B/In2/F | keep-outs | draft: MIC_CLK 3.6 mm (B), N$2 16.6 mm, MIC_DATA 13.7 mm, MIC_VDD 11.8 mm |
| [reg-pod-body](reg-pod-body.md) / [physical](physical.md) | lid bore (pod x 34.5), hex window, 1.5 mm gap board-to-lid; board port at pod x 34.5 (aligned with the bore) | the acoustic duct and a water path | `shell_r1.py` Y_SPLIT 14.4, PCB y 12.1-12.9 |

Firmware dependencies (integration-map §8): ADF1 on PB3/PB4 at 4 MHz; PA5 is a supply pin, not I/O.

## Constraints
- **D13** (`spec.md` 224-239): never power up or wake straight into ultrasonic mode; start at 1.024-2.475 MHz (plan: 2.0 MHz), wait, then switch; clock duty 48-52 % above 2.4 MHz; SELECT tied; no Class-2 caps near the mic.
- **D14 / A3-u575-plan.md §1**: ADF clock divider changes only with the filter stopped (stop, re-divide, restart). Keep CCKDIV+1 even (only route to 50 % duty; ST specifies no duty).
- **D12**: Off = mic unpowered (PA5 low).
- **§8 acoustic rules**: board <= 0.8 mm; port 0.6-1.0 mm; **no gasket cavity**; opening directly over the hole; thin mesh, never foam.
- **O16-5**: port on the board centre line, identical in both pods. **O12**: IPX4 minimum, IPX5 preferred.
- **D11 / §1.2.3**: self-noise no louder than ambient; SMPS and bridge stay away from the mic (far face).
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
| Port: mic / board / lid | D0.325 +-0.05 / D0.6 / D1.0 | datasheet p.9; footprint; shell_r1.py | 2026-10-01 |
| Duct as built (rev 1) | 0.8 board + 1.5 open gap + 0.9 lid + 0.8 window | shell_r1.py constants lines 36-44, 102-103 | 2026-10-01 |
| Board port vs lid bore offset | **0.000 mm** nominal (Rev F: U2 origin x 4.67, port x 3.9 = lid bore); Rev E was 0.77 mm (port 3.13), hole and bore overlapping by only 0.03 mm | interfaces.py [mic-port] (WARN = nominal only, worst-case stack margin 0.00 mm at limit 0.20); `place_r1.py` L61; shell_r1.py line 45 | 2026-10-02 |
| Shaped PWM noise in the mic band | -35 dB re FS (bridge V), -59 dB (coil I) at 200 kHz | spec D6 MP-01; `sim/checks/pwm_ultrasonic_leak.py` | 2026-09-30 |
| JLC stock / price | **960** · $1.99 (Extended); was 1,076 on 2026-09-30 and falling | JLC parts API, audit query (UTC; 2026-10-01 local) | 2026-10-02T00:44Z |
| ADF current | ~40 µA at 80 MHz (MDF ~0.28 mA) | A3 §1.4 (DS Table 72) | 2026-09-30 |

## Open issues
1. **CLOSED in Rev F (ECR-0011): board port and lid bore aligned.** U2 moved to board x 4.67, so its port (0.77 mm off the footprint origin) sits at board (3.9, 6.50) = pod x 34.5 under the lid bore (`place_r1.py` L61; interfaces.py [mic-port] 0.000 mm nominal, 2026-10-02; integration-map F1 states both). Rev E had the port at (3.13, 6.50), 0.77 mm off, holes overlapping by 0.03 mm. The port position also sets where a gasket or chimney presses (issue 2) and where the mesh sits (issue 3).
2. **No seal between board and lid.** Rev 1 dropped the round-1 chimney + PORON washer (`frame.py` MIC_SEAL; `hw/mech/notes/shell.md` line 79). The port opens into the whole F-side cavity: a resonant side volume (breaks §8 "no gasket cavity") and a **water path to the MCU** (O12). *Closes it:* restore a chimney/washer (or a sealed boss) and keep vias out of r1.6 around the port.
3. **No mesh exists.** integration-map §1 says "hydrophobic mesh"; no part, seat or source is in hw/mech, hardware.md or the BOM. *Closes it:* task D2: pick a mesh with ultrasonic transmission data; decide the seat.
4. **Acoustic coupons vs O9.** CLAUDE.md lists coupons as bench boards; O9 says no separate test boards. Options: (a) JLC coupon panel, 0.6/0.8/1.0 mm holes; (b) the rev-1 board plus printed lid variants (bore, seal, mesh); (c) both. **Recommend (b)**: the lid is where rev 1 is uncertain and prints cost nothing. Owner decides. Response of the as-built duct: unknown (round-1's 3.2 mm duct had quarter-wave ~24 kHz, shell.md line 214).
5. **Clock duty cycle unknown; Rev F has a hand-wire fallback.** ST specifies no CCK duty (A3 §1.1). The timer-clock fallback needs an MDF CKI pin; the ADF has none. Rev F adds the MDF fallback dots TP8 PB8 / TP9 PB1 / TP10 MIC_DATA on B (gen.py docstring L47-48, TP block L284-289): lift R2, wire TP8 to R2's mic-side pad R2.2 = MIC_CLK, TP9 to TP10; firmware moves the mic to MDF1 (sub-debug-test mdf_fallback). *Closes it:* scope PB3 (E6) before the board order.
6. RSFLT response at 800 kHz unpublished (R18). *Closes it:* swept tone, D1 vs D2 decimation, on the first board.
7. **MIC_VDD noise.** PA5 (pin 15) sits 2 pins from GA_N (pin 17) and 5 from VLXSMPS (pin 20); no RC filter, X7R bypass only; mic PSRR unspecified above 1 kHz. *Closes it:* a self-noise capture (USB stream, bridge on/off, SMPS vs LDO); a series R + C on MIC_VDD is the cheap fix if it shows.
8. **MP-01 self-hearing** (shaped PWM noise, 20-85 kHz) via rail, ground or exciter vibration. PWM rate is firmware (200/400/800 kHz). *Closes it:* S2 coupling measurement.
9. R2 sits at the mic end, so the 16.6 mm N$2 run carries the fast edge. Edge at the mic must stay <= 3 ns. *Closes it:* move R2 to PB3 in the together-session (O14); check GPIO speed setting.
10. No probe point on MIC_CLK on rev 1; E6 needs R2's pad on B (board out of the shell).
11. **Unpowered-mic back-feed.** Off-mode pin state isn't specified anywhere: park PB3/PB4 low/analog when PA5 is low (proposed firmware rule). Firmware can't cover two states: **reset and ROM DFU**, where PB4 is NJTRST with an internal pull-up and back-feeds MIC_DATA while MIC_VDD floats (sub-debug-test ROM table). Breaks "Off really is off" (D12) only in those states. *Closes it:* meter MIC_VDD in reset and DFU at bring-up (sub-debug-test step 6); if it lifts, the boot stub parks PB4 first, or the mic supply gets a pull-down.
12. Missing diagram: acoustic-path cross-section (lid, gap, board, mic, offset). `pcb-floorplan-rev1.png` is outdated (28 x 13 board).

## Before you change this, check
- **Moving U2 or its footprint:** the port, not the body, must match the lid bore (`shell_r1.py` MIC) in **both** pods (centre line, O16-5); `reg-board.md`, `reg-pod-body.md`, `physical.md`.
- **Lid, shell, mesh, board thickness:** the duct (§8 rules), sealing (O12), coupon plan; EQ curve (C8).
- **PA5 / PB3 / PB4:** pin map (`integration-map.md` §4); ADF only exists on PB3/PB4, MDF on PB8/PB1; D12 Off current.
- **Clock or decimation:** `sub-processing.md` clock tree (integer ratios, even divider), D14.
- **Anything new near the mic** (bridge, SMPS, Class-2 caps, vias): D11, D13, MP-01.
- **Mic part swap:** `sim/data/` response, power budget (`sub-power.md`), `sim/dsp/pipeline.py` constants.
- Run the cross-check in `integration-map.md` §10.

## Change log
- 2026-10-01: created from gen.py Rev E, the rev-1 draft board probe (19:44 route), shell_r1.py, spec v0.14, mic datasheet Rev B-1 and DS13737 Rev 10. Found issues 1-3.
- 2026-10-01 (editor pass): port position corrected to the board file, (3.13, 6.50), offset 0.77 mm, overlap 0.03 mm; issue 11 adds the reset/DFU back-feed through PB4's NJTRST pull-up; mic stock 960 (falling); spec line refs moved to v0.15 (O16 L642, task D2 L688).
