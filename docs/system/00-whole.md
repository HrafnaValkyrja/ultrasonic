# The whole pod, on one page
Rev MZ-2 2026-10-07: body rewritten to the Phase-2 design (`hw/current.yaml`, ECR-0018): one-face 30 × 12 board hung from the lid, MZ-2 package set, sealed D1.0 mic duct, SW1 pocket + puck, shell_r2; Rev F/G facts moved to "Reference design" at the end.
Status: Phase-2 miniaturised pod (package set MZ-2 "Balanced"): schematic = Rev G nets with MZ-2 packages (`POD_PACKAGES=mz2 python3 hw/pod/gen.py` → `hw/pod/pod_mz2.net`, `hw/pod/bom_jlc_mz2.csv`); board routed, DRC 0, 0 unconnected (`hw/pod/draft_r2/out/routed.kicad_pcb`, commit f6291e6, 2026-10-07); shell CAD `hw/mech/shell_r2.py` + `dims_r2.py`, not printed; no firmware. Owner review of Claude's layout pending (O25, 1–2 weeks from 2026-10-02). Updated 2026-10-07.

```yaml
abbrev: {MZ-2: "Phase-2 package set 'Balanced' (ECR-0018)", F: "board face toward the lid (outside)", B: "board face toward the cell", VHB: "3M VHB 4914 acrylic foam tape, 0.25 mm", LN-M0x: "layout-noise metrics (docs/sim/layout-noise.yaml)", NPTH: "non-plated through hole", MC: "Monte Carlo"}
item: WHOLE
design_pointer: hw/current.yaml (id phase2; reference = revg)
src_of_truth: [docs/spec.md, "hw/pod/gen.py (POD_PACKAGES=mz2, MZ2 table L93)", hw/pod/draft_r2/out/routed.kicad_pcb, hw/mech/dims_r2.py, hw/mech/shell_r2.py, hw/mech/frame.py, hw/mech/heel.py, hw/mech/pad.py]
owner_decisions: "O1-O27 (spec §12); Phase 2 = O25 (Claude lays out, owner reviews), O26 (miniaturise internals first), O27 (thin > short > long)"
open_ecrs: {ECR-0018: "approved (owner delegated), implementation in progress", others: "ECR-0001, 0005-0010, 0014-0016 proposed (plm.py status 2026-10-07)"}
checks_2026-10-07: {interfaces.py: "PASS mic-port, outline, inside, clamp-bands (VHB face, 91 % bonded), heights, board-nets; WARN switch (worst stack 0.05 over), pins (3 known hazards), rails (+3V0 326 mA vs U4 300 mA, ECR-0005), frame (8 of 10, ECR-0001)", bom_check.py: "PASS refs/netlist/footprints/fp-library/nets/assembly-tier/jlc-bom/cost-bom/selftest 61; WARN values, identity, stock-lock (8 rows missing), lock-drift (12)"}
```

Read this first, then [integration-map.md](integration-map.md), then the doc of every subsystem and region a change touches ([README](README.md) has the rule).

## What it does
1. Each pod hears ultrasound (realistically 20–85 kHz; the locked MVP says "roughly 20–96") with a PDM MEMS mic ([§1.1](../spec.md#1-mvp--locked-owner-defined-do-not-modify), D14 band-edge note).
2. An STM32U575 MCU (Arm Cortex-M33 microcontroller with a built-in core switching regulator) shifts it into 1.5–4 kHz (D9).
3. A discrete H-bridge (two N+P MOSFET pairs) drives a bone-conduction exciter pressed on the skin in front of the tragus (D1, D6).
4. Two identical pods clip onto her prescription glasses, one per temple arm, with no link between them (D2, §1.2.1).
5. A 175 mAh cell runs each pod for ≥ 8 h (target ~12 h); a magnetic USB dock charges it and loads firmware (D18, O12, O16).

Phase 2 changed packages, board, shell and placement only: **the circuit is frozen at Rev G** (`pod_mz2.net` nets == Rev G, gen.py `apply_packages` docstring; bom_check [nets] 195 pins / 42 nets PASS 2026-10-07). Every F-row, pin and rail below is the Rev G one.

## Functions (F-rows from integration-map.md §1) and the doc that owns each
| F | Function | Owner doc | Also touches |
|---|---|---|---|
| F1 | Hear 20–85 kHz | [sub-audio-in](sub-audio-in.md) | reg-board (mic on B, port NPTH), reg-pod-body (sealed D1.0 duct), physical |
| F2 | Process | [sub-processing](sub-processing.md) | sub-power (SMPS, D11), reg-board (In2 +3V0 plane) |
| F3 | Drive the exciter | [sub-output](sub-output.md) | reg-arm (wires), reg-pad (exciter) |
| F4 | Self-test exciter \|Z\| | [sub-output](sub-output.md) | sub-debug-test (USB self-test), reg-board (R21 Kelvin vias) |
| F5 | Charge the cell | [sub-power](sub-power.md) | sub-dock-usb, reg-pod-body (dock bay, cell on VHB) |
| F6 | Temperature-safe charge | [sub-power](sub-power.md) | sub-processing (PA2 20 °C rule) |
| F7 | System power rail | [sub-power](sub-power.md) | – |
| F8 | Battery level | [sub-power](sub-power.md) | sub-processing (ADC4 in Stop 2) |
| F9 | Dock detect | [sub-dock-usb](sub-dock-usb.md) | sub-processing |
| F10 | USB data / DFU | [sub-dock-usb](sub-dock-usb.md) | sub-processing (boot stub) |
| F11 | Wake / button | [sub-ui](sub-ui.md) | reg-pod-body (SW1 pocket, puck, skin) |
| F12 | Power LED (solid) | [sub-ui](sub-ui.md) | reg-arm (2 of the 4 wires), reg-pad (pad board) |
| F13 | Charger link (I2C) | [sub-power](sub-power.md) | sub-processing; reg-board (I2C_SCL runs inside In2) |
| F14 | Debug / flash / test | [sub-debug-test](sub-debug-test.md) | reg-board (TP1–TP6 bare on F), reg-pod-body (VHB cut-outs) |
| F15 | ESD at exposed contacts | [sub-dock-usb](sub-dock-usb.md) | sub-power (D5 at J3, D4 reverse block), reg-board (J-pad gaps) |

## Logical block diagram
![block schematic, gen.py](../diagrams/schematic-rev1.png)

*Source `docs/diagrams/schematic-rev1.svg`: the block structure is still right (nets unchanged since Rev G); package labels and three values on it are stale ("58 placed parts" → 53; "R21 0.33 Ω" → 0.1 Ω 0402; "~1C = 175 mA" → 170 mA).*

## Physical overview
Phase-2 views are build outputs (gitignored): `python3 hw/mech/shell_r2.py` → `hw/mech/out/r2/section.png` (y stack through the mic) and `plan.png`; `python3 tools/board_map.py` → `docs/diagrams/board-map-phase2.png`. `docs/diagrams/system-overview-physical.png` still draws Rev F (ribs, foam, parts on both faces): use it for topology only.

| Region | Holds (Phase 2) | Doc |
|---|---|---|
| Pod body | tub (cell on VHB, belly dock bay, heel), lid (sealed D1.0 mic duct + mesh window, SW1 pocket + puck + skin, x-stop), seam at the board's B face | [reg-pod-body](reg-pod-body.md) |
| Board | 30 × 12 × 0.8, 4 layers (In1 GND plane, In2 +3V0 plane). **B face: every part** (MCU, SMPS, crystal, mic, bridge, charger, LDO, dock protection, all J wire pads, TP7–TP10 dots). **F face: SW1 + bare TP1–TP6 only**; F is bonded to the lid by VHB with per-pad cut-outs | [reg-board](reg-board.md) |
| Cell | Renata 175 mAh pouch on 0.25 VHB in the tub; 1.4 mm gap to the board's B face (no foam) | [sub-power](sub-power.md), [physical](physical.md) |
| Arm | NiTi wire Ø0.80, printed strut cover, 4 litz wires to the rear B pads | [reg-arm](reg-arm.md) |
| Pad | cup + cap, RC-BC02 exciter, pad board with a blue LED, contact face | [reg-pad](reg-pad.md) |

## Key numbers
| Quantity | Value | Source (date) |
|---|---|---|
| Pod envelope (Phase 2) | L 38.0 × T 10.4 × H 14.5, belly 2.05; volume 6211 mm³ (body 5721 + plate 331 + spine 160); Rev F 7801 mm³ → −20 % | `hw/mech/out/r2/checks.json` envelope (shell_r2.py, commit c348661, 2026-10-07) |
| Stack (pod y, mm) | adapter face 4.3 · wall 0.8 · tape 0.3 · cell 5.4–10.7 · B gap 1.4 · board 12.1–12.9 · F gap 0.30 (VHB 0.25) · lid 13.2–14.0 · plate to 14.7 | `dims_r2.py` Y_* (2026-10-07) |
| Board | 30.0 × 12.0 × 0.8, R1.0 corners, 4 layers F / In1 GND / In2 +3V0 / B; pod x 30.55–60.55, 0.25 x-stop gap, 0.45 side gaps | routed board probe (pcbnew, 2026-10-07); checks.json board_in_cavity |
| Board parts | 74 footprints: 53 JLC-placed (52 B + SW1 on F) + 21 copper-only pads; 31 BOM lines; no DNP | bom_check.py [refs] [jlc-bom] 2026-10-07; board probe (B 67 / F 7 footprints) |
| Route | 610 track segments (F 277 mm, B 252 mm, In2 9.0 mm = the I2C_SCL bridge), 136 vias 0.35/0.15; DRC 0, 0 unconnected | board probe 2026-10-07; ECR-0018 log 2026-10-07 |
| Layout noise | LN-M01 26.5 dB (nominal 46.5, worst 14.0) PASS; LN-M02 20.1 dB PASS (review band); LN-M03 1.29 % ≤ 2 % PASS; LN-M04 0.127 mV PASS; LN-M05 8.7 µV PASS | `sim/noise/out_r2/budget.json` (valid, board sha da4e8b13 = routed board, 2026-10-07) |
| Mic port acoustics | phase2_r2 duct: mean 20–96 kHz +5.6 dB nominal; MC (n 60, ±0.2 mm, offset 0–0.2) p05/p50/p95 −0.06/4.51/8.43 dB; peak 63.0 kHz +18.5 dB Q6.4 (firmware EQ target); notch 26.0 kHz −7.8 dB | `sim/acoustics/port.py` scenario phase2_r2 (`sim/acoustics/out/port_results.json`), ECR-0018 log 2026-10-07 |
| Cell | Renata ICP501233PA-02 (Li-ion pouch with its protection circuit inside), 175 mAh, 35 × 12 × 5.3 mm | spec O16(1); `dims_r2.py` CELL |
| Arm | NiTi (superelastic nickel-titanium) wire Ø0.80, 20 mm, 30° sweep | `frame.py`; spec O7b |
| Pad force target | ≥ 1 N inward at the tragus | spec D1 |
| Mass per pod | **≥ ~9.5 g lower bound [derived]**: shell 2.52–2.58 (tub 1321.5 + lid 863.3 + puck 3.1 mm³ at 1.15–1.18 g/cm³) + cell ~4.2 + pad 2.19 + bare board ~0.53 (288 mm³ FR-4 at ~1.85 g/cm³ [A]); before parts, dock target, adapter, wires. Target ~8 g, ~15 g hurts (D18, R20) | checks.json volumes (2026-10-07); pad checks.json (2026-10-01); derived 2026-10-07 |
| Current, full chain awake | 5.0 / 6.8 / 9.8 mA (low / nominal / high) | spec §7; `sim/checks/power.py` rev 2 (circuit unchanged since Rev G) |
| Current, idle listening | 1.7 / 2.2 / 3.4 mA | same |
| Pad LED (O8) | +0.14–0.73 mA on battery, 0.82–0.86 mA docked; not in `power.py` | [sub-ui](sub-ui.md) |
| Runtime, 175 mAh (derived) | always awake 13.4–22.0 h; 12.5 h pessimistic with the LED at 0.75 mA | `power.py` (2026-10-01; same circuit) |
| Rail peaks | +3V0 326 mA vs U4 300 mA rating (ECR-0005); VSYS 327 mA = 93 % of the cell's 350 mA 2C pulse | interfaces.py [rails] 2026-10-07 |
| Charge current | 170 mA (ICHG code 44) at 20–45 °C; 50 mA below 20 °C; firmware sets it over I2C | [sub-power](sub-power.md) |
| Cost per pod | **$23.18 priced parts per pod, $46.36 per pair**, plus cell and exciter (no price) | `docs/build/bom.md` (bom.py, MZ-2 re-price JLC API 2026-10-07T11:31Z) |
| One-time per JLC order | $93–195 (rough, not a quote) | `bom.md` |
| Budget | ~$300 rev-1 milestone; O19 personal device, no volume-cost goals; O21 nothing ordered before the design freeze | O13, O19, O21 |
| MCU stock | U1 C5271013: 8 at JLC (ECR-0008) | bom.md / JLC API 2026-10-01 (not re-queried 2026-10-07) |
| Sealing target | IPX4 minimum, IPX5 preferred | O12(b) |
| Signal chain | mic 4.0 MHz PDM → 200 kS/s; output 1.5–4 kHz; PWM 200 kHz | D14, D9, D6 |

## Status of every part of the system (2026-10-07)
| Doc | State | Biggest open issue |
|---|---|---|
| [integration-map](integration-map.md) | Generated from gen.py mz2 + `system_map.py` hand-kept facts (Phase 2 mechanical facts since 07c8a83) | §10 item 6 still says "clamp bands" (generator text, system_map.py) |
| [physical](physical.md) | Phase-2 stack from `dims_r2.py`; board hung from the lid | Heel wire exit re-routed behind the cell end (2026-10-07; real-cell dry fit open); dock wire route belly → rear B pads undesigned; sealing unverified (physical issues 2, 3, 6) |
| [sub-power](sub-power.md) | Rev G circuit, MZ-2 packages, routed; charger firmware not written | U4 300 mA vs the 326 mA +3V0 peak (ECR-0005); charger defaults unsafe until firmware writes the register plan; J3 DOCK_VBUS–J5 VBAT now neighbours, 1.17 mm, no GND pad between (PWR-I17; ASM-09) |
| [sub-audio-in](sub-audio-in.md) | Mic at board (2.65, 6.0), port (1.88, 6.0) = pod 32.43; sealed D1.0 duct + gauge pin; acoustics phase2_r2 modelled | No mesh part (S8-mesh FAIL); 63 kHz Q6.4 duct resonance needs the firmware EQ notch (O24 text still says ~84.7 kHz); duct-seat keep-out broken by an F track; port_results.json now holds an n 40 MC (p50 4.30, all-pass 0.57) vs the n 60 run in the ECR-0018 log (4.51, 0.70) |
| [sub-processing](sub-processing.md) | U1 QFN-48 on B; routed; **no firmware** | No firmware (ECR-0010); 8 MCUs at JLC (ECR-0008); LSE traces use vias and both faces, VDDA caps C5/C6 ~9 mm from pin 9 (issues 13, 14) |
| [sub-output](sub-output.md) | Rev G circuit; R21 0402 with Kelvin vias (LN-M03 1.29 %); exciter not measured | Exciter unmeasured (E1, ECR-0007); U4 vs full-scale peaks (ECR-0005); R21 sits mid-board (19.45, 6.45), not at the edge MZD-4 asks for (edge tried 2026-10-07: LN-M03 2.48 % FAIL or unroutable BRIDGE_RTN; reg-board issue 20) |
| [sub-dock-usb](sub-dock-usb.md) | Dock pads on B rear columns; D5/D6/U6/D4 on B | BOM still pairs the 5-pin target with a 4-pin head (DK-01); dock wire route undesigned (DK-05); O16(3) USB-C space not carried into shell_r2, owner decision needed (DK-10) |
| [sub-ui](sub-ui.md) | SW1 alone on F in the lid pocket; puck kit modelled | Puck reach by selective fit, every tolerance [A]; the 1.2–2.0 N press is reacted by the VHB and the 0.8 mm board, nothing rigid backs SW1; skin not chosen; gesture model open (owner) |
| [sub-debug-test](sub-debug-test.md) | TP1–TP6 bare on F (VHB cut-outs), TP7–TP10 on B; no bring-up yet | First flash = ROM DFU via the R1 tack pad (no SWD probe, O13/O21); TP1–TP6 reachable only before the lid bond; TP4 +3V0 beside TP5 GND at 0.8 mm (DBG-2) |
| [reg-pod-body](reg-pod-body.md) | shell_r2 CAD, not printed; clash checks 0, printable | Switch lateral stack WARN (0.20 vs 0.15); heel exit vs cell; seam rebate 0.2 below the 0.4 resin minimum; duct-seat keep-out R-ACO-P6 holds (1.87 mm, rule area, 2026-10-07) |
| [reg-board](reg-board.md) | Routed: DRC 0, 0 unconnected; owner review pending (O25) | No dielectric stack-up in the file; DRC rules only in the untracked `routed.kicad_pro`; LSE vias, VDDA caps; J3–J5 1.17 mm (reg-board issues 2, 4, 16–18) |
| [reg-arm](reg-arm.md) | CAD rev 1, not built; heel/pad checks still read `frame.py` (ECR-0001) | Heel exit vs cell; pad force dips to 0.42–0.45 N on jaw opening; wire Ø 0.80 (frame) vs 0.75 (BOM) |
| [reg-pad](reg-pad.md) | CAD rev 1, not built; exciter not measured | Contact face Ø8 (~50 mm²) vs O16(4) 100–150 mm²; exciter size/leads unknown (E1); sealing undesigned |

## Decision index (everything that shapes the hardware)
Decisions: [spec §4](../spec.md#4-decisions). Owner decisions: [spec §12](../spec.md#owner-decisions-open). L = line in `docs/spec.md` (read 2026-10-07; header still says v0.14). Cite by ID first, line second.

| ID | Line | What it fixes in hardware |
|---|---|---|
| §1 MVP | L26 | Locked. Clip-on clasps, Ear (open) coexistence, self-noise ≤ ambient, comfort first |
| §8 | L435 | Physical layout per side; peripheral vision no-go zone (nothing forward of ~18 mm behind the pupil plane); mic port rules |
| D1 | L85 | Exciter on the skin in front of the tragus, pressing inward, ≥ 1 N |
| D2 | L107 | Two independent pods: own cell and MCU each, no wires across the hinges |
| D3 | L119 | Fixed gain + stepped volume: one button (SW1) does it all |
| D4 | L127 | Digital DSP, so an MCU |
| D5 | L131 | MCU = STM32U575CIU6Q, QFN-48 7 × 7 (kept in Phase 2, MZD-2), internal SMPS |
| D6 | L153 | 200 kHz 2-level PWM into a discrete H-bridge; gate pull resistors mandatory |
| D7 | L189 | Exciter = RC-BC02 class (measure in E1) |
| D8 | L199 | JLC machine assembly; the owner hand-solders only the wires, cell and exciter |
| D11 | L210 | The only switching regulator is the MCU core SMPS; the main rail is a linear LDO |
| D12 | L218 | Off = Stop 2 with the mic unpowered, so the mic is fed from PA5 |
| D13 | L224 | Mic SPH0641LU4H-1; no Class-2 ceramic caps near it; §8 port rules |
| D14 | L241 | One synchronous clock tree; mic clock 4.0 MHz |
| D16 | L285 | 32.768 kHz crystal Y1 (Phase 2: 2012 package, CL 7 pF) |
| D17 | L293 | Fixed output ceiling, pop-free starts |
| D18 | L297 | ≥ 8 h runtime, weight balance |
| O5 | L630 | Pod growth acceptable when it is clearance |
| O7, O7b | L632–633 | Superelastic NiTi arm, no heat-setting; 20 mm, 30° sweep |
| O8 | L634 | Solid power LED in the pad (R14, J7/J8, PB7) |
| O9 | L635 | Rev 1 is the prototype: test pads + snap-off test frame |
| O10 | L636 | Two-stage build: test build, then a bonded final build that can be cut open |
| O12 | L638 | Magnetic USB dock (charge + DFU), IPX4/IPX5, fastest practical charge |
| O13 | L639 | Budget is a milestone (~$300); "board stays double-sided": Phase 2 places one face by machine (SW1 is the only F part) |
| O14 | L640 | Layout together: **superseded for rev 1 by O25** |
| O16 | L642 | Renata 175 mAh, BQ25180, magnetic connector, near-flat pad, one board for both pods (mic + switch on the centre line), no screws, IP68 switch |
| O17 | L643 | Spine top; arm-joint wiring with clearance |
| O18 | L644 | Fail informatively: hooks (R1/R20/R21 stay hand-liftable 0402), spare pins to pads, every uncertain value a firmware knob |
| O19 | L645 | Personal device: comfort, reliability, serviceability; no volume-cost goals |
| O20 | L646 | Rev 1 aims to be the final device; size is a rev-1 priority (Phase 2 is its answer) |
| O21 | L647 | No orders until the design is final |
| O22 | L648 | Freeze = evidence gate, not a date |
| O23 | L649 | Black solder mask, white legend |
| O24 | L650 | Sealed D1.0 mic duct + x-stop/locating feature (+ EQ notch); C8/C9 10 V; D6 ESD at CC; long sim runs |
| O25 | L651 | Claude lays out the rev-1 board; owner reviews in 1–2 weeks |
| O26 | L652 | Phase 2 miniaturisation now, internals first; adapter deferred (two frames) |
| O27 | L653 | Size priority: thin, then short (height), then length |
| O3, O4 | L629, L654 | OPEN: shopping list; D18 reading (cell along the arm) |

## Where the spec and the design disagree today
- Spec §3 and §9 still describe the L452/DFSDM, MCP73831 charger, 105–150 mAh cell and old FET candidates; the design is U575/ADF1, BQ25180, Renata 175 mAh, PMCXB290UE.
- Spec §7 runtime and D18 are sized for 105–150 mAh; O16 picked 175 mAh. The charge rule "≤ 0.5C" is now 170 mA ≈ 1C (O12c).
- D5 names the Murata LQM21PN2R2MGHL SMPS inductor; the board fits the DFE201610E (L0806), whose magnetostriction (D11) isn't published.
- D5's v0.14 note still says the bridge is on PA8/PA7/PA9/PB0; it is PA8/PA7/PA10/PB15 (ECR-0003).
- O13 "board stays double-sided" vs Phase 2's one-face machine placement (SW1 alone on F; bom_check [assembly-tier] still counts it double-sided: 1 F + 52 B, 2026-10-07).
- O24(1) names the EQ notch at ~84.7 kHz; on the Phase-2 duct the peak is at 63.0 kHz (ECR-0018 log 2026-10-07).
- The spec header says v0.14; O10 "screwed where needed" vs O16(6) no screws; four cited research notes don't exist (`sealing-and-service.md`, `contact-face-and-preload.md`, `battery-and-charging.md`, `self-test-firmware.md`).

## Design-level cross-domain risks (Phase 2)
IDs kept from the Rev F list; a gap = closed by Phase 2 (reason in the Reference section).

| # | Risk | Docs |
|---|---|---|
| 1 | **J-pad neighbours a solder bridge turns into a fault.** Phase 2 keeps ≥ 0.8 mm copper gaps between harmful pairs (MZD-10; place_r2.py rule); see reg-board for the measured gaps | reg-board, sub-dock-usb, sub-power, sub-debug-test |
| 2 | **The exposed DOCK_VBUS contact is clamped by D5** (TPD1E10B06 at J3, now on B); D4 PMEG3005EL is the reverse-dock block (~0.07 W, Tj ~71 °C docked, ECR-0018 MZV-06); reverse-dock behaviour with D5 in place not re-analysed | sub-dock-usb, sub-power |
| 3 | **PB7 (LED_K) has no series resistor** and shares the arm bundle with OUT_A/OUT_B; pad-board J4 0.45 mm from J2 OUT_B | sub-ui, reg-pad, reg-arm, reg-board |
| 4 | **TS/MR is the NTC input and the charger's button input** (EN_PUSH default → ship mode if TS < 90 mV for 10 s); in ROM DFU PA2 (USART2_TX) drives TS high | sub-power, sub-processing, sub-debug-test |
| 5 | **Charger watchdog vs firmware update** (HW reset after 160 s without I2C unless the boot stub disables it) | sub-power, sub-dock-usb, sub-processing |
| 6 | **ECR-0009 (no output while docked) vs O15/O18 docked self-test**; the cap must cover U4 at 4.5 V VSYS and the ECR-0005 peak | sub-output, sub-debug-test, sub-power |
| 7 | **One board in mirrored shells (O16-5):** mic and SW1 sit on board y 6.0 (pod z −2.45, both pods); everything else lands at a different height per pod (TP row, J pads, dock pads); handed bought parts need a per-pod contact map; only the right pod is modelled | physical, reg-board, sub-dock-usb, reg-pod-body |
| 8 | **Board location in x/z:** the coarse x-stop (0.25) and side gaps (0.45) alone give 0.86 mm worst duct offset vs the 0.20 limit; the stepped gauge pin through the bore at bonding makes it 0.115 (dims_r2 duct_offsets). Without the pin, the mic port can be half-blocked | reg-pod-body, sub-audio-in, physical |
| 9 | **The single 3.0 V LDO value is load-bearing in four domains** (USB VDDUSB, bridge peak ECR-0005, mic supply via PA5, ADC reference) | sub-power, sub-dock-usb, sub-output, sub-audio-in, sub-processing |
| 10 | **Charge current vs cable** (ILIM by enumeration; CC not sensed) | sub-power, sub-dock-usb |
| 11 | **MCU reset defaults vs mic power gating (D12):** PB4's NJTRST pull-up back-feeds the unpowered mic in reset, ROM DFU and Off | sub-audio-in, sub-processing, sub-debug-test |
| 12 | **Button press loads the VHB bond, not a spring:** the board hangs from the lid on VHB; SW1's force goes puck → SW1 → board → VHB → lid. Switch stack: fixed tolerances pre-press (−0.198 worst), selective puck fit holds 0.005–0.135 (dims_r2 switch_stack); interfaces.py [switch] WARN 0.05 mm over in x/z; press FEM (sub-ui issue 2): 2 N moves SW1 ≤ 20 µm, VHB ≤ 52 kPa vs 3M's 85 kPa dynamic factor | reg-pod-body, sub-ui, reg-board |
| 13 | **Thermal placement vs cell safety (R23):** U3 (~0.3 W at start of CC) on B faces the pouch across the 1.4 mm gap | sub-power, reg-board, reg-pod-body |
| 15 | **Heel exit checked against the wrong cell** (`frame.py`; ECR-0001, interfaces.py [frame] 8 of 10 facts differ) | reg-arm, physical, sub-power, reg-pod-body |
| 16 | **Serviceability (O19) vs the bonded build:** the board is bonded to the lid, the cell to the tub; TP1–TP6 are reachable only before the lid bond or after a peel (checks.json F_face_pads); field recovery = ROM DFU via the R1 tack pad + dock USB | physical, reg-pod-body, reg-arm, sub-power, sub-debug-test |
| 17 | **No dielectric stack-up in the board file;** sim/noise uses the Rev E draft stack (budget.json board.stackup "unverified vs JLC page"); y fits (duct, puck) assume 0.8 mm | reg-board, physical, sub-audio-in |
| 18 | **Mass ≥ ~9.5 g before parts vs the ~8 g target** | 00-whole, physical, reg-pod-body, reg-pad, sub-power |
| 20 | **Mic acoustics and sealing:** the sealed duct raises the 20–96 kHz mean (+5.6 dB) but puts a 63 kHz Q6.4 peak in band; it needs the firmware EQ notch (O24) and a measured coupon. The duct-seat keep-out R-ACO-P6 (nothing within 1.6 mm of the port) holds since 2026-10-07: F.Cu rule area, nearest F copper / via 1.87 mm | sub-audio-in, reg-pod-body, sub-processing |
| 21 | **I2C_SCL runs 8.97 mm inside the In2 +3V0 plane** (hw/pod/inner_bridge.py): the plane stays one island (−4 mm², 1.4 %); modelled in sim/noise (LN metrics pass). Any re-route near U1 pin 26 or a plane cut must keep it | reg-board, sub-power, sub-processing |

## Before you change anything
Follow [README](README.md) "The rule" and walk the change through [integration-map.md §10](integration-map.md#10-required-cross-check-for-every-proposed-change). For any geometry change, read [physical.md](physical.md) "Before you change this". Switching designs: `hw/current.yaml` (env `ULTRASONIC_DESIGN=revg` selects the reference).

## Reference design (Rev F/G)
Kept in the repo, never deleted (`hw/current.yaml` reference): Rev G schematic / Rev F board `hw/pod/draft_r1/pod_r1_routed.kicad_pcb`, 34 × 13 × 0.8, parts on both faces (F 21 / B 31), In2 signals, 1 unconnected + 19 courtyard DRC; shell `hw/mech/shell_r1.py` ("Spine"): board on foam strips clamped by lid ribs, 1.5 mm unsealed mic gap, plunger Ø1.2; envelope 38.0 × 11.8 × 15.2 + belly 3.5, 7801 mm³; LN-M03 5.2 % FAIL, LN-M02 12.2 dB. Risks closed by Phase 2: 12 (floorless foam: no foam), 14 (USB-C fallback keep-out: not carried into shell_r2), 19 (simplification study: superseded by MZ-2). Full Rev F text: git history of this file before 2026-10-07.
