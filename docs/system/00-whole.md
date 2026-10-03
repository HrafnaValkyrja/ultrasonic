# The whole pod, on one page
Status: rev-1 prototype design (schematic Rev F, routed board draft, rev-1 "Spine" shell), updated 2026-10-01; Rev F facts synced 2026-10-02 (key numbers, status table, risks 1-4, 8, 10, 17, 20) · Sources of truth: `docs/spec.md`, `hw/pod/gen.py`, `hw/pod/place_r1.py` (until the KiCad board takes over), `hw/mech/shell_r1.py` + `frame.py` + `heel.py` + `pad.py` · Owner decisions: O1–O20 ([spec §12](../spec.md#owner-decisions-open); spec v0.15 at commit 092f2aa). **O20 (2026-10-01 20:48): rev 1 aims to be the final device, so the 34 × 13 board and the rev-1 shell, grown under O15, must be re-sized.**

Read this first, then [integration-map.md](integration-map.md), then the doc of every subsystem and region a change touches ([README](README.md) has the rule).

## What it does
1. Each pod hears ultrasound (realistically 20–85 kHz; the locked MVP says "roughly 20–96") with a PDM MEMS mic ([§1.1](../spec.md#1-mvp--locked-owner-defined-do-not-modify), D14 band-edge note, spec L269).
2. An STM32U575 MCU (Arm Cortex-M33 microcontroller with a built-in core switching regulator) shifts it into 1.5–4 kHz (D9, L203).
3. A discrete H-bridge (four transistors, as two N+P pairs) drives a bone-conduction exciter pressed on the skin in front of the tragus (D1, L85; D6, L153).
4. Two identical pods clip onto her prescription glasses, one per temple arm, with no link between them (D2, L107; §1.2.1).
5. A 175 mAh cell runs each pod for ≥ 8 h (target ~12 h); a magnetic USB dock charges it and loads firmware (D18, L297; O12, L638; O16, L642).

## Functions (F-rows from integration-map.md §1) and the doc that owns each
| F | Function | Owner doc | Also touches |
|---|---|---|---|
| F1 | Hear 20–85 kHz | [sub-audio-in](sub-audio-in.md) | reg-board (mic on B), reg-pod-body (lid port), physical |
| F2 | Process | [sub-processing](sub-processing.md) | sub-power (SMPS, D11) |
| F3 | Drive the exciter | [sub-output](sub-output.md) | reg-arm (wires), reg-pad (exciter) |
| F4 | Self-test exciter \|Z\| | [sub-output](sub-output.md) | sub-debug-test (USB self-test) |
| F5 | Charge the cell | [sub-power](sub-power.md) | sub-dock-usb, reg-pod-body (dock bay) |
| F6 | Temperature-safe charge | [sub-power](sub-power.md) | sub-processing (PA2 20 °C rule) |
| F7 | System power rail | [sub-power](sub-power.md) | – |
| F8 | Battery level | [sub-power](sub-power.md) | sub-processing (ADC4 in Stop 2) |
| F9 | Dock detect | [sub-dock-usb](sub-dock-usb.md) | sub-processing |
| F10 | USB data / DFU | [sub-dock-usb](sub-dock-usb.md) | sub-processing (boot stub) |
| F11 | Wake / button | [sub-ui](sub-ui.md) | reg-pod-body (plunger, skin) |
| F12 | Power LED (solid) | [sub-ui](sub-ui.md) | reg-arm (2 of the 4 wires), reg-pad (pad board) |
| F13 | Charger link (I2C) | [sub-power](sub-power.md) | sub-processing |
| F14 | Debug / flash / test | [sub-debug-test](sub-debug-test.md) | reg-board (TP1–TP6 on F) |
| F15 | ESD at exposed contacts | [sub-dock-usb](sub-dock-usb.md) | sub-power (D5 TPD1E10B06 at the J3 contact, D4 stays the reverse block), reg-board (J-pad adjacency) |

## Logical block diagram
![block schematic, gen.py Rev F](../diagrams/schematic-rev1.png)

*Source `docs/diagrams/schematic-rev1.svg`. Three labels are now stale: "58 placed parts" (now 56), "R21 0.33 Ω" (now 0.1 Ω after the 2026-10-01 audit) and "~1C = 175 mA max" (U3 can only set 170 mA). The signal-chain diagram `docs/diagrams/system-overview.svg` is from spec v0.13 (MCU/ADF chain still right); it has no current PNG in `docs/diagrams/`.*

## Physical overview: where each block lives, what crosses between regions
![physical overview](../diagrams/system-overview-physical.png)

*Source `docs/diagrams/system-overview-physical.svg` (new, 2026-10-01; text corrected in the editor pass). Panel A is the LEFT pod from outside with the lid off. That view is exactly KiCad's top view of the board. Panel B is the stack-up through the mic; it draws the board hole and lid bore in line; Rev F makes that true (ECR-0011; they were 0.77 mm apart in Rev E). Details: [physical.md](physical.md). CAD renders: `hw/mech/out/r1/spine/open.png`, `exploded.png` (right pod).*

| Region | Holds | Doc |
|---|---|---|
| Pod body | tub, lid (mic port, plunger, ribs), spine top, belly dock bay, heel (NiTi root) | [reg-pod-body](reg-pod-body.md) |
| Board (in the pod) | F face: MCU, SMPS, crystal, SW1, TP1–TP6, all J pads · B face: mic, bridge, charger, LDO, dock protection | [reg-board](reg-board.md) |
| Cell (in the pod) | Renata 175 mAh, under the board on foam | [sub-power](sub-power.md), [physical](physical.md) |
| Arm | NiTi wire Ø0.80, printed strut cover, 4 litz wires | [reg-arm](reg-arm.md) |
| Pad | cup + cap, RC-BC02 exciter, pad board with a blue LED, contact face | [reg-pad](reg-pad.md) |

## Key numbers
| Quantity | Value | Source (date) |
|---|---|---|
| Pod envelope, rev 1 | 38.0 long × 11.8 deep (adapter face to armour top) × 15.2 tall; belly adds 3.5 under the front 25.5 mm; spine adds up to 3.1 on top at the rear | `shell_r1.py` L35–37, L120–132; STL bounding boxes `hw/mech/out/r1/spine/` (measured 2026-10-01) |
| Board | 34 × 13 × 0.8 mm, 4 layers, In1 solid GND, parts on both faces | `place_r1.py` L1, L8 (2026-10-01) |
| Cell | Renata ICP501233PA-02 (Li-ion pouch with its protection circuit inside), 175 mAh, 35 × 12 × 5.3 mm | spec O16(1) L642; `shell_r1.py` L8 |
| Arm | NiTi (superelastic nickel-titanium) wire Ø0.80, 20 mm, 30° sweep | `frame.py` L68; spec O7b L633 |
| Pad force target | ≥ 1 N inward at the tragus | spec D1 L100 |
| Mass per pod | **≥ ~10.2 g lower bound [derived]**, before parts, dock target, adapter and wires: shell 2.92 + heel 0.26 + cell ~4.2 + pad **2.19** + bare board ~0.65. **Already above the ~8 g target**; ~15 g is where glasses start to hurt (D18, R20). Two resin densities in the sum (1.15 / 1.18 g/cm³). Last whole-pod figure: ~7.1 g for the older 38 × 10 × 15 pod with a 105 mAh cell | reg-pod-body Key numbers; pad checks.json (2026-10-01 00:54); spec §8 L455, L516 |
| Current, full chain awake | 5.0 / 6.8 / 9.8 mA (low / nominal / high) | spec §7 L408; `sim/checks/power.py` rev 2 |
| Current, idle listening | 1.7 / 2.2 / 3.4 mA | same |
| Pad LED (O8) | +0.14–0.73 mA on battery (VSYS 3.0–4.2 V), 0.82–0.86 mA docked (4.5 V); **not in `power.py`** | sub-ui Key numbers (R14 2k2, V<sub>F</sub> 2.6–2.7 V from pad-led.md) |
| Runtime, 175 mAh (derived) | always awake: 13.4–22.0 h (pessimistic–nominal); 12.5 h pessimistic with the LED at 0.75 mA; half awake: 19.9–33.2 h | `power.py` model with 175 mAh plugged in (run 2026-10-01 for this doc; the same model reproduces spec's 105 mAh 8.0–13.2 h) |
| Runtime requirement | ≥ 8 h, target ~12 h | D18 L297 |
| Charge current | **170 mA** (ICHG code 44, the nearest 10 mA step ≤ 1C) at 20–45 °C; 50 mA (code 32) below 20 °C; firmware sets it over I2C (U3 default 10 mA). gen.py L191 still says 175 mA | [sub-power](sub-power.md) register plan; SLUSE99C §8.5.1 |
| Charge time | **TBD** (no source computes it; needs the BQ25180 CC/CV profile with the real cell) | – |
| Cost per pod | $22.90 priced parts per pod, $45.81 per pair, **plus** cell and exciter (no price yet). Includes the **wrong** 4-pin cable head C5126845; with the 5-pin C5126847 ($1.39, 0 JLC stock 2026-10-02T00:03Z) the pod cost drops ~$0.68 (sub-dock-usb issue 1). bom.md also over-counts passives by 3 (23 caps vs 22; 21 resistors incl. R20/R21) | `docs/build/bom.md` L40 (JLC API 2026-10-01; lock 2026-09-30) |
| One-time per JLC order | $93–195 (rough, not a quote) | `bom.md` L50 |
| Budget | ~$300 rev-1 milestone (may double after); device target ~$150. O19: a personal device, no volume-cost goals; buy critical parts once with spares | O13 L639; O19 L645 |
| Board parts | 52 JLC-placed parts on 30 BOM lines; **11 Extended part types on the pod board** (+1, the pad-board LED C131223 = 12 loading fees per JLC order); 21 copper-only pads (J1–J5, J7–J12, TP1–TP10); no DNP (D1/D2 removed) | `hw/pod/bom_jlc.csv` (counts derived 2026-10-02); reg-board counts and Interfaces (Cost) row; JLC parts API 2026-10-02T00:44Z (audit query, every line) |
| ERC | 0 errors, 311 warnings | `hw/pod/gen.erc` (2026-10-02 20:01) |
| Board draft route | 687 tracks, 118 vias, **2 unconnected** (SWCLK→TP2, LED_K→J8), 19 DRC errors (all courtyard overlaps: 18 J-pad ring pairs + C1↔U1) | `hw/pod/draft_r1/summary.json`, `drc.json` (2026-10-02T20:07) |
| MCU / mic stock | U1: 8 at JLC (C5271013); U2: 960 and falling (1,076 on 2026-09-30) | `bom.md` L7 (2026-10-01); JLC API 2026-10-02T00:44Z; ECR-0008 |
| Sealing target | IPX4 minimum, IPX5 preferred | O12(b) L638 |
| Signal chain | mic 4.0 MHz PDM → 200 kS/s; output 1.5–4 kHz; PWM 200 kHz | D14 L241–258, D9 L203, D6 L155 |

## Status of every part of the system
Every doc below was created 2026-10-01 with this set and revised the same evening (editor pass). "State" mirrors each doc's own status line.

| Doc | State (2026-10-01) | Biggest open issue |
|---|---|---|
| [integration-map](integration-map.md) | Generated from `gen.py` Rev F; hand-kept facts live in `hw/pod/system_map.py` | Hand-kept facts lag: "~315 mA" peaks (interfaces.py rails: 326 mA on +3V0); LED "~0.35-0.75 mA" (sub-ui: 0.14-0.73 battery, 0.82-0.86 docked); TP1-TP6 only (TP7-TP10 exist); "PA8/PA7/PA9/PB0" in §8 (now PA8/PA7/PA10/PB15); LED duty "from VBAT"; shrink tube "through" the bores. All wait on `system_map.py` (list below) |
| [physical](physical.md) | Rev-1 shell + 34 × 13 draft; O20 says both must be re-sized | The foam strips have no floor (0.1 mm on the cell); mic port unsealed (port aligned with the lid bore since ECR-0011); heel exit vs the cell end |
| [sub-power](sub-power.md) | Schematic Rev F; routed, none of the 2 unconnected here; charger firmware not written | U3 defaults are unsafe for this cell (TS_HOT 60 °C, 10 mA); firmware must also set EN_PUSH = 0 and handle the watchdog in DFU. Cell is quote-only |
| [sub-audio-in](sub-audio-in.md) | Schematic Rev F; routed draft; rev-1 shell; port aligned with the lid bore (ECR-0011) | No seal across the 1.5 mm gap; acoustic path unmeasured; mic stock falling |
| [sub-processing](sub-processing.md) | Schematic Rev F; routed draft; **no firmware** | No firmware (ECR-0010); only 8 MCUs at JLC (ECR-0008); spec D5 names a different SMPS inductor |
| [sub-output](sub-output.md) | Schematic Rev F; routed, nothing unrouted here; firmware not written; exciter not measured | Exciter R and L unknown (E1, ECR-0007); Q1/Q2 footprint (ECR-0004); ECR-0009's docked interlock vs the self-test |
| [sub-dock-usb](sub-dock-usb.md) | Schematic Rev F; pads hand-wired to a bought target; belly bay modelled; cable, pin order and DFU firmware not designed | No wire route or gauge from the belly; wrong 4-pin head in the BOM (D5 now clamps the exposed DOCK_VBUS contact) |
| [sub-ui](sub-ui.md) | Schematic Rev F; BTN routed, LED_K→J8 unrouted; plunger and bore modelled, skin not chosen; gesture model partial; no firmware | Seated plunger sits 0.40 mm under the skin recess floor: head ↔ skin is set nowhere; nothing rigid (floorless foam) backs SW1 |
| [sub-debug-test](sub-debug-test.md) | Schematic Rev F; TP row placed; SWCLK→TP2 unrouted; test frame, self-test firmware and note don't exist; no bring-up yet | First flash needs an SWD probe (none recorded); ECR-0009 blocks the docked \|Z\| sweep; O20: test access may not cost size |
| [reg-pod-body](reg-pod-body.md) | Rev-1 shell CAD, not printed; overlap checks all 0; O20 re-size | Foam has no floor; spine is a floating solid; board has no x stop; seam cut line is a 0.2 mm rebate with no lip round the belly |
| [reg-board](reg-board.md) | Routed draft, not the layout: 2 unconnected, 19 DRC (courtyard overlaps); O20 re-size | 2 unconnected; J4 GND–J5 VBAT 0.60 mm (cell short), J5–J12 CC 0.89 mm; owner layout (O14) not started; Phase 2 miniaturization pending |
| [reg-arm](reg-arm.md) | CAD rev 1, not built; heel/pad checks still built against `frame.py` (ECR-0001) | Spring force unverified (bend a coupon, O7b); heel exit vs the rev-1 cell; wire Ø 0.80 (`frame.py`) vs 0.75 (BOM) |
| [reg-pad](reg-pad.md) | CAD rev 1, not built; `pad.py` all_pass false (2 known items); pad board DRC 0; exciter not measured | Exciter not bought; contact face Ø8 vs O16(4)'s 100–150 mm²; pad-board LED_K 0.45 mm from OUT_B |

## Decision index (everything that shapes the hardware)
Decisions: [spec §4](../spec.md#4-decisions). Owner decisions: [spec §12](../spec.md#owner-decisions-open). L = line in `docs/spec.md` v0.15 (commit 092f2aa; its header still says v0.14). Lines move whenever the spec grows: cite by ID first, line second.

| ID | Line | What it fixes in hardware |
|---|---|---|
| §1 MVP | L26 | Locked. Clip-on clasps, Ear (open) coexistence, self-noise ≤ ambient, comfort first |
| §8 v0.9 | L476 | Peripheral vision is a no-go zone: nothing forward of ~18 mm behind the pupil plane (E10 measures) |
| D1 | L85 | Exciter on the skin in front of the tragus, pressing inward, ≥ 1 N |
| D2 | L107 | Two independent pods: own cell and MCU each, no wires across the hinges |
| D3 | L119 | Fixed gain + stepped volume: one button (SW1) does it all |
| D4 | L127 | Digital DSP, so an MCU, not an analog divider |
| D5 | L131 | MCU = STM32U575CIU6Q, QFN-48 7 × 7, internal SMPS (its inductor, L152, differs from the schematic's: sub-processing issue 11) |
| D6 | L153 | 200 kHz 2-level PWM into a discrete H-bridge; gate pull resistors mandatory |
| D7 | L189 | Exciter = RC-BC02 class (vendor specs disagree; measure in E1) |
| D8 | L199 | JLC machine assembly; the owner hand-solders only the wires, cell and exciter |
| D11 | L210 | The only switching regulator is the MCU core SMPS (shielded, low-magnetostriction L1); the main rail is a linear LDO |
| D12 | L218 | Off = Stop 2 with the mic unpowered, so the mic is fed from PA5 |
| D13 | L224 | Mic SPH0641LU4H-1; no Class-2 ceramic caps near it; the §8 port rules (L508) follow from it |
| D14 | L241 | One synchronous clock tree; mic clock 4.0 MHz |
| D16 | L285 | 32.768 kHz crystal Y1 |
| D17 | L293 | Fixed output ceiling, pop-free starts (firmware; relies on the D6 gate pulls) |
| D18 | L297 | ≥ 8 h runtime, weight balance: sets cell size and position |
| D9, D10, D15 | L203, L207, L272 | Firmware-only (output band, band floor, toolchain) |
| R19–R25 | L612–L618 | v0.15 project-level risks: experience, wearability, silence, DOA rev 1, safety, joint fatigue, design paralysis; mitigations in ECR-0006…0010 |
| O1, O2 | L627, L628 | Runtime 8/12 h; tragus site (both resolved) |
| **O3** | L629 | OPEN: approve the shopping list |
| **O4** | L647 | OPEN: confirm the D18 reading (cell along the arm, nothing behind the ear) |
| **O5** | L630 | Pod growth is acceptable when it is clearance |
| O6 | L631 | Resolved into D11 (core SMPS allowed) |
| O7, O7b | L632, L633 | Superelastic NiTi wire arm, no heat-setting; 20 mm, 30° sweep, wiring option A (Ø0.75 proposal still awaiting OK) |
| O8 | L634 | Solid power LED in the pad (R14, J7/J8, PB7) |
| O9 | L635 | Rev 1 IS the prototype: test pads + snap-off test frame, no dev boards |
| O10 | L636 | Two-stage build: test build, then a bonded final build that can be cut open |
| O11 | L637 | Printed strut cover, Sugru contact, arms tilted inward for preload |
| O12 | L638 | Magnetic USB dock (charge + DFU), IPX4/IPX5, fastest practical charge |
| **O13** | L639 | Budget is a milestone (~$300); board stays double-sided |
| O14 | L640 | PCB layout done together; Claude teaches, the owner drives KiCad |
| O15 | L641 | Self-test over USB. "Rev 1 may be bigger" is **superseded by O20** |
| O16 | L642 | Renata 175 mAh, BQ25180, pre-built magnetic connector (+ USB-C space), bigger near-flat pad, one board for both pods, no screws in the housing, IP68 switch |
| O17 | L643 | Spine top; arm-joint wiring with clearance, no pinched wires |
| O18 | L644 | Fail informatively: test hooks, telemetry, isolation links; DFU the most-verified path, SWD backup; the board measures itself; spare MCU pins to pads; every uncertain value a firmware knob |
| O19 | L645 | A personal device: optimise comfort, reliability, durability, **serviceability** (cell swap, owner repairs) and diagnosability; no volume-cost goals; buy spares |
| O20 | L646 | Rev 1 aims to be the final device: size is a rev-1 priority; test access must not cost size; the 34 × 13 board and rev-1 shell must be re-sized |

## Where the spec and the design disagree today
- Spec §3 (L60–73) and §9 (L520–535) still describe the L452/DFSDM, MCP73831 charger, 105–150 mAh cell and the old FET candidates. Rev E is U575/ADF1, BQ25180, Renata 175 mAh and PMCXB290UE.
- Spec §7 runtime (L413–417) and D18 (L299) are sized for 105–150 mAh; O16 picked 175 mAh. The charge rule "≤ 0.5C" (L386) is now 170 mA ≈ 1C (O12c; sub-power).
- D5 (L152) names the Murata LQM21PN2R2MGHL SMPS inductor; Rev E fits the DFE201610E, whose magnetostriction (D11, L214) isn't published.
- O20 (L646) says rev 1 is final-size; the design in hand (34 × 13 board, rev-1 shell) was grown under O15 and hasn't been re-sized yet.
- The spec header still says v0.14; its changelog and content are v0.15 (owner to bump).
- O10 says the test build is "screwed where needed"; O16(6) (later) says the housing is taped, with no screws.
- Spec cites four research notes that don't exist: `sealing-and-service.md` (O10), `contact-face-and-preload.md` (O11), `battery-and-charging.md` (O12), `self-test-firmware.md` (O15).

## Design-level cross-domain risks
Each one crosses at least two docs; a change in any listed doc can trigger it. Raised by the 2026-10-01 inspection of this set.

| # | Risk | Docs |
|---|---|---|
| 1 | **J5 VBAT has two Rev F bridge paths; J4 GND now separates it from J3 DOCK_VBUS (3.2 mm).** J4 GND–J5 VBAT at 0.60 mm (a bridge shorts the cell through its PCM) and J5 VBAT–J12 CC at 0.89 mm (VBAT on an exposed dock contact: sweat electrolysis, shorts to the frame). J3 DOCK_VBUS–J4 GND (0.60) shorts dock 5 V; J12 CC–J1 OUT_A (0.60) puts a 200 kHz bridge output on the exposed CC contact (reg-board issue 4) | reg-board, sub-dock-usb, sub-power, sub-debug-test |
| 2 | **The exposed DOCK_VBUS contact is clamped by D5** (TPD1E10B06, bidirectional, 5.5 V working, at J3 since Rev F; Rev E had no clamp at the contact). D4 stays the reverse-dock block; reverse-dock behaviour with D5 in place [TBD: not re-analysed here]. Magnet keying and contact order still tie to both | sub-dock-usb, sub-power, integration-map F15 |
| 3 | **PB7 (LED_K) has no series resistor and three fault paths:** the arm bundle beside OUT_A/OUT_B, pad-board J4 0.45 mm from J2 OUT_B, and, on the pod board, J2 OUT_B beside J8 LED_K (0.60 mm); the Rev E J8–J9 bridge into TS is gone (1.72 mm apart in Rev F) | sub-ui, reg-pad, reg-arm, reg-board, sub-power |
| 4 | **TS/MR is the NTC input and the charger's button input.** With EN_PUSH at its default, TS < 90 mV for 10 s on battery = ship mode (pod dead until docked): a bridge from J9 to a pad that holds TS low (J8 LED_K is no longer a neighbour, 1.72 mm; J2 OUT_B 0.71 and J1 OUT_A 0.89 hold TS low only if the TIM1 idle state does [TBD]), PA2 driven low, or the NTC above ~84 °C. In ROM DFU, PA2 (USART2_TX) drives TS high: "cold", charging pauses | sub-power, sub-ui, sub-debug-test, sub-processing |
| 5 | **Charger watchdog vs firmware update.** Option B (HW reset after 160 s without I2C) power-cycles a long ROM DFU session unless the boot stub disables it first (40 s with setting 10) | sub-power, sub-dock-usb, sub-processing |
| 6 | **ECR-0009 (no output while docked) vs O15/O18 diagnostics.** The \|Z\| sweep and PWM-noise A/B run docked over USB. Needs an explicit capped self-test exemption; the cap must also cover U4 heating at 4.5 V VSYS and the ECR-0005 peak above 300 mA | sub-output, sub-debug-test, sub-power, sub-processing |
| 7 | **One board in mirrored shells (O16-5):** anything off the centre line lands at a different height per pod. TP row up in one, down in the other; L1 ~6.6 mm from the dock's rear magnet in the left pod vs ~14 mm in the right (derived); J-pad order and any move of the dock pads; rear-gap wire routes. Handed bought parts (the target's one-sided tab, the cell's lead exit) need a per-pod contact map. Only the right pod has been modelled | physical, reg-board, sub-dock-usb, reg-pod-body, sub-processing |
| 8 | **The board has no x stop** (~2.4 mm of slide). It moves SW1 under the Ø1.2 stem (switch top 3.0 × 2.6) and the mic port (aligned with the lid bore at nominal since ECR-0011; interfaces.py mic-port 0.000 mm): a tolerance becomes a dead button or a blocked mic | reg-pod-body, sub-ui, sub-audio-in, reg-board |
| 9 | **The single 3.0 V LDO value is load-bearing in four domains:** USB VDDUSB margin (≥ 3.0 V; AN2606's 3.3 V is boilerplate, DS13737 Table 150 allows USB down to 2.7 V: no LDO change needed), bridge gain and peak current (ECR-0005), the mic supply via PA5, the ADC reference. Raising it for DFU moves the bridge peak, `power.py` and the runtime | sub-power, sub-dock-usb, sub-output, sub-audio-in, sub-processing |
| 10 | **Charge current vs cable.** ILIM 500 mA default; ICHG powers up at 10 mA and firmware writes 170 mA (hold ILIM 100 mA until enumeration, VINDPM 4.2 V); a CC-less USB-A cable on an unenumerated port allows 100 mA. Firmware sets ILIM by enumeration (CC sense R19 removed in Rev F) | sub-power, sub-dock-usb |
| 11 | **MCU reset defaults vs mic power gating (D12).** PB4's NJTRST pull-up (and PB3 if driven while PA5 is low) back-feeds the unpowered mic in reset, ROM DFU and Off | sub-audio-in, sub-processing, sub-debug-test |
| 12 | **Retention and the button share one unsupported spring.** The edge foam has 0.1 mm of cell under it. A 1.2–2.0 N press can push the board ~0.2 mm until B parts (R21 under SW1, Q1/Q2, U3's DSBGA) land on the pouch: joint stress, pouch pressure, and a swallowed 0.15 mm switch stroke. A mic gasket adds load at the front | reg-pod-body, sub-ui, reg-board, sub-power, sub-audio-in |
| 13 | **Thermal placement vs cell safety (R23).** U3 (~0.3 W at start of constant current, ~+31 °C die; 0.2 W mid-charge) sits on B 0.2 mm above a pouch rated to charge at 0–45 °C, RT1 beside it. Moving U3 or changing the stack changes cell temperature in charge | sub-power, reg-board, reg-pod-body |
| 14 | **USB-C fallback (O16-3) may be unusable:** the keep-out sits behind the belly's 3.5 mm rear step; a plug overmold (~6.5 mm, unchecked) can't engage with the body bottom behind it and the heel, strut and pad inboard. `USBC_KEEPOUT` is never checked | sub-dock-usb, reg-pod-body, physical, reg-arm |
| 15 | **The heel exit is checked against the wrong cell** (`frame.py`'s old cell and PCM). The real PCM bulge or lead exit can close the 1.1 mm behind-cell gap or pinch the bundle (O17) while every check passes | reg-arm, physical, sub-power, reg-pod-body |
| 16 | **Serviceability (O19, R24) vs the bonded build.** Arm conductors and cell leads end on J pads inside the sealed pod, the cell is on permanent VHB, the cut line is a 0.2 mm rebate: every arm or cell swap is a cut-and-rebond cycle | physical, reg-pod-body, reg-arm, sub-power |
| 17 | **The proposed per-pod 3D fit check needs the board's stack-up:** the board file now sets 0.8 mm (`place_r1.py` L195, Rev F) but still has no stack-up block (reg-board issue 2); a wrong stack puts every fit off in y, the axis of the plunger stack and the mic duct | reg-board, physical, sub-ui, sub-audio-in |
| 18 | **Mass ≥ ~10.2 g before parts vs the ~8 g target** (~15 g hurts). Cell, shell growth and pad size all push the same way; no doc owned the total until now; ECR-0006's ballast depends on it; O20's re-size is the main lever | 00-whole, physical, reg-pod-body, reg-pad, sub-power |
| 19 | **The pending simplification study can change J-pad count and order, wire counts and board size.** Those feed the heel channel fill (0.36), strut bore, counterbores, rear-gap stowage, pad adjacencies, rib and foam lengths. `shell_r1.py` follows `PCB` automatically, but `heel.py`/`pad.py` read `frame.py`: a board change updates half the mechanics | reg-board, reg-arm, reg-pad, reg-pod-body, physical |
| 20 | **Mic acoustics and sealing interact.** A gasket or chimney for the 1.5 mm gap (§8, O12) must press round the board port at (3.9, 6.5), which since ECR-0011 sits under the lid bore (U2 moved to x 4.67; interfaces.py mic-port 0.000 mm), and it loads the board through the floorless foam. The mesh seat and gasket footprint follow that port position | sub-audio-in, reg-pod-body, physical |

## Fixes waiting in source files (outside this doc set)
Found and verified in the editor pass; this set may not edit them. Each belongs in the next commit that touches the file.
- **`hw/pod/gen.py`:** docstring L10–11 (MCP73831, 105 mAh, "charge status PA10" → BQ25180, Renata 175 mAh, PA10 = R11 pull-up); L15–17 and L247 ("fed from VBAT", duty "from VBAT" → VSYS, duty from VBAT on battery and 4.5 V docked); L34 ("14 -> 11 Extended" → 13 → 10 on the pod board, +1 pad LED); L172–174 (R21 reads supply current i·(2d−1)); L190 ("SLUSE13" → SLUSE99C); L191 (175 mA → 170 mA, code 44). Then regenerate the integration map.
- **`hw/pod/system_map.py`** (integration-map hand-kept text): F1 port at board (3.13, 6.50) = pod x 33.73 and "PB3 (N$2) → R2 33R → MIC_CLK → U2 CLOCK"; MECH mic keep-out; F2 clock plan → `A3-u575-plan.md` §2; F12 and FIRMWARE[5] duty from VSYS; F15 chain "DOCK_VBUS (J3, exposed) → D4 → VBUS (D3)"; RAILS['+3V0'] and CONSTRAINTS to `power.py` rev 2 (full chain 5.0/6.8/9.8 mA, idle 1.7/2.2/3.4 mA, LED not modelled); RAILS['VSYS'] LED 0.14–0.73 mA battery / 0.82–0.86 docked; arm bullet: bare litz (Ø0.51) through heel Ø1.0 and strut Ø1.2, shrink tube only across the 3 mm flex zone, 1.1 mm behind the cell; add O18 to CONSTRAINTS and to the §10 pins item ("say whether freed pins go to pads"); escape the "|Z|" in F4 (it breaks the §1 table).
- **`docs/build/bom.py`:** capacitors 22 (not 23), generic resistors 19 (R20/R21 have own rows), cable head C5126847, Extended note "10 + pad LED".
- **`docs/diagrams/schematic-rev1.svg`:** "~1C = 175 mA max" → 170 mA; 58 → 56 parts; R21 0.33 → 0.1 Ω.
- **`hw/mech/shell_r1.py`:** foam floor + a "foam ∩ support" check; seam groove in the lid (or a 0.4 tub rebate); lip round the belly; plunger head length; a check that uses `USBC_KEEPOUT`. **`hw/mech/heel.py`:** exit check against `shell_r1.CELL`.
- **Notes:** `docs/build/hardware.md` L67 and `hw/mech/notes/hardware.md` L47 (foam 1.1 × 17.5 is round-1); `notes/pad.md` and `notes/heel.md` (wire route); `notes/electronics.md` (35 mm slack).
- **PLM:** ECR-0001 should cover `pod.py` too; spec header v0.14 → v0.15 (owner).

## Before you change anything
Follow [README](README.md) "The rule" and walk the change through [integration-map.md §10](integration-map.md#10-required-cross-check-for-every-proposed-change). For any geometry change, read [physical.md](physical.md) "Before you change this" too.

## Change log
- 2026-10-01: created. New diagram `docs/diagrams/system-overview-physical.svg`. Kept the old v0.13 `system-overview.svg` (signal chain, used by `tools/smoke/run_all.py`). Runtime for 175 mAh derived from `power.py`.
- 2026-10-01 (editor pass, inspectors' fixes): status line O1–O20; Key numbers: charge 170 mA, LED on the VSYS basis, 10 Extended types on the pod board, mass ≥ ~10.2 g, cost caveat (wrong head); status table re-synced with each doc; decision index moved to spec v0.15 lines with R19–R25 and O18–O20; new sections "Design-level cross-domain risks" and "Fixes waiting in source files".
