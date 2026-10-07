# SUB-DEBUG-TEST: SWD, test pads + dots, isolation links, ROM DFU, USB self-test, bring-up
Rev MZ-2 2026-10-07: body rewritten to the Phase-2 design (`hw/current.yaml`, ECR-0018): TP1-TP6 bare 0.7 pads on F in per-pad VHB cut-outs (reachable only before the board is bonded to the lid); TP7-TP10 dots, R1 PH3 tack pad, R20/R21 and every probe point on B (reachable with the lid lifted); R21 0402; LN-M03 1.29 % PASS; all nets routed. Rev F/G facts moved to the last section.
Status: schematic = Rev G nets, MZ-2 packages (`hw/pod/pod_mz2.net`; bom_check netlist/nets PASS 2026-10-07); board `hw/pod/draft_r2/out/routed.kicad_pcb`: 610 track segments, 136 vias (0.35/0.15), DRC 0, 0 unconnected (pcbnew probe + ECR-0018 log, 2026-10-07); interfaces.py clamp-bands (VHB face) PASS 91 % bonded, 2026-10-07. Not done: snap-off test frame; self-test firmware (requirements only, FWSIM-R57..R61); no hardware ordered (O21) → no bring-up. Updated 2026-10-07.

```yaml
abbrev: {SWD: "Arm 2-wire debug port", DFU: "USB Device Firmware Upgrade (ST ROM bootloader)", CDC: "USB virtual serial port", TP: "test pad/dot", VHB: "3M VHB 4914 0.25 mm acrylic foam tape that hangs the board from the lid", MDF/ADF: "STM32U5 multi/audio digital filter", F/B: "board faces: F = outer (bonded to the lid), B = inner (toward the cell)", "(x, y)": "board mm, origin top-left, KiCad top view"}
item: SUB-DEBUG-TEST
src_of_truth: ["hw/pod/gen.py (NRST, C10, R1; R21/R22/C22; R20; TP1-TP10; MZ2 table)", "hw/pod/draft_r2/out/routed.kicad_pcb (positions)", "hw/pod/draft_r2/placement.yaml", "hw/mech/dims_r2.py (F_PADS, TP_PAD_D, TP_CUT_MARGIN)", "hw/mech/shell_r2.py::vhb", "hw/lib/pod.pretty/TestPoint_Pad_D0.7mm, TestDot_D0.5mm", "docs/system/pin-contract.yaml", "docs/system/integration-map.md F14 (generated)"]
owner_decisions: {O9: "rev 1 = prototype: pads + snap-off frame", O10: "bonded final build, cut-openable", O13: "own bench, no tool purchases", O15: "self-test over USB (size clause superseded by O20)", O18: "fail informatively; DFU most-verified, SWD backup; spare pins to pads; removals stated", O19: "diagnosability", O20: "test access must not cost size", O21: "no orders before freeze", O22: "freeze = evidence gate", O25: "Claude lays out; owner reviews in 1-2 weeks (supersedes O14 for rev 1)", O26: "Phase 2 now"}
ecrs_open: {ECR-0005: "self-test drive level vs U4 300 mA (interfaces.py rails: +3V0 peak 326 mA, 2026-10-07)", ECR-0009: "no output while docked vs docked self-test (DBG-12)", ECR-0010: "bring-up plan + firmware before order", ECR-0013: "S1 implemented (PB5 strapped to GND); S2 firmware (UCPD_DBDIS order) open; S3 partial", ECR-0018: "Phase 2 package set + board (approved, owner review pending)"}
checks: ["tools/checks/interfaces.py [clamp-bands] (2026-10-07: PASS, 7 F parts in VHB cut-outs, 91 % bonded)", "tools/checks/interfaces.py [board-nets] (PASS)", "sim/noise LN-M03 (2026-10-07: 1.29 % PASS)"]
diagrams: ["docs/diagrams/board-map-phase2.png (tools/board_map.py)", "docs/diagrams/schematic-rev1.png (block flowchart, nets unchanged)"]
```

## Scope
```yaml
carries: [F14 debug/flash/test, "F4 test side (|Z| self-test; circuit owned by sub-output)"]   # integration-map §1
brief: "O18: rev 1 will partly fail; every failure diagnosable from the board (hooks, telemetry, isolation links); USB DFU = most-verified path; SWD = backup"
access_by_build_stage:   # physical.md assembly order; shell_r2.py docstring (2026-10-07)
  bare_board: "everything: F TP1-TP6 + B dots/pads"
  board_bonded_to_lid: "F face is on the VHB: TP1-TP6 unreachable (physical.md step 8). B face faces the cell: lifting the lid lifts the board on its wires and exposes B (test build: peel the seam tape)"
  final_bonded_pod: "dock only (USB DFU, CDC); B face after cutting the seam; SWD needs the board peeled/sawn off the lid (reg-pod-body issue 15)"
access_paths:
  - {id: AP-DFU1, what: "first flash, blank chip: tack R1 PH3 pad R1.1 (2.58, 3.85) B -> +3V0 at reset -> ROM USB DFU on J10/J11", src: "integration-map F14 'R1 pad = DFU tack point'; ECR-0018 log 2026-10-03 (field recovery = ROM DFU via R1/PH3 on B + dock USB)"}
  - {id: AP-SWD, what: "SWD on TP1/TP2/TP3/TP5 (TP4 = probe Vref sense only); bench only, before the lid bond", src: "gen.py TP block; dims_r2.F_PADS"}
  - {id: AP-USB, what: "app CDC self-test stream + boot-stub jump to ROM DFU for updates (boot stub not designed: sub-dock-usb)", src: "integration-map F10"}
  - {id: AP-UART, what: "TP7 = PB6 USART1_TX printf, B face (works with USB dead; SWO lost to MIC_CLK on PB3)", src: "pin-contract.yaml DBG_TX"}
  - {id: AP-HAND, what: "probe dots/cap terminals on B; lift R20 (rail) or R21 (bridge); both 0402 hand hooks (gen.py MZ2 'kept on purpose')", src: gen.py}
why_blank_needs_hook: "R1 holds BOOT0 low -> boot from (empty) flash; U575 has no empty-flash->bootloader rule (RM0456 Rev 7 Table 25 p.192; AN2606 Rev 69 Pattern 12)"
```

## Elements (Phase 2, positions: pcbnew probe of routed.kicad_pcb, fenced, 2026-10-07)
```yaml
elements:
- {ref: "TP5, TP4, TP2, TP1", part: "Ø0.7 bare copper pad (TestPoint_Pad_D0.7mm)", nets: "TP5 GND · TP4 +3V0 · TP2 SWCLK PA14(37) · TP1 SWDIO PA13(34)", at: "(1.6 / 3.1 / 4.6 / 6.1, 11.3) F: 1.5 mm pitch, 0.8 mm copper gap"}
- {ref: TP3, part: "Ø0.7 pad", net: "NRST(7)", at: "(9.3, 2.9) F, over U1"}
- {ref: TP6, part: "Ø0.7 pad", net: "VSYS", at: "(24.0, 10.9) F, near U3/U4"}
- {ref: "VHB cut-outs", what: "one 1.8 mm square per TP1-TP6 (pad Ø1.0 [A] + 0.4 margin each side) so bonded pads stay clean", src: "dims_r2 TP_PAD_D, TP_CUT_MARGIN; shell_r2.vhb(); interfaces.py clamp-bands 91 % bonded (2026-10-07)"}
- {ref: TP7, part: "Ø0.5 dot", net: "DBG_TX = PB6(42) USART1_TX AF7", at: "(4.25, 9.35) B"}
- {ref: TP8, part: "Ø0.5 dot", net: "MDF_CCK = PB8(45) MDF1_CCK0 AF5", at: "(3.5, 3.85) B"}
- {ref: TP9, part: "Ø0.5 dot", net: "MDF_SDI = PB1(19) MDF1_SDI0 AF6", at: "(2.05, 8.25) B"}
- {ref: TP10, part: "Ø0.5 dot", net: "MIC_DATA (PB4(40), U2 DATA)", at: "(3.1, 8.25) B"}
- {ref: R1, part: "10k 1% 0402 BOOT0 pull-down (hand hook, kept 0402)", net: "N$1 = PH3-BOOT0(44)", at: "(2.07, 3.85) B; PH3 pad R1.1 (2.58, 3.85)", lcsc: "C25744 (bom_jlc_mz2.csv 'dated lookup')"}
- {ref: C10, part: "100nF 0201 X5R NRST filter", net: NRST, at: "(9.55, 0.83) B", lcsc: "C76934"}
- {ref: R20, part: "0R 0402 link LDO_OUT->+3V0 (hand hook)", at: "(23.0, 11.0) B; LDO pad R20.1 (23.51, 11.0)", lcsc: "C17168"}
- {ref: R21, part: "ERJ2BSFR10X Panasonic 0.1R 1% 0402 current-sense (166 mW per docs/research/simplify/output.md L86)", net: "BRIDGE_RTN->GND", at: "(19.45, 6.45) B; GND pad R21.2 (18.94, 6.45) with two pad-hugging GND vias (hw/pod/kelvin_r21.py)", lcsc: "C409058 Extended"}
- {ref: "R22, C22", part: "1k 0201 / 10nF X7R 0201 low-pass 15.9 kHz", net: "BRIDGE_RTN->I_SENSE->PA6(16) ADC1_IN11", at: "(15.4, 3.55) / (15.4, 4.4) B", lcsc: "C270365 / C85930"}
mdf_fallback: "ADF clock duty out of spec (sub-audio-in issue 5): lift R2, wire TP8 (3.5, 3.85) -> R2.2 MIC_CLK (5.48, 8.07), TP9 (2.05, 8.25) -> TP10 (3.1, 8.25); firmware moves mic to MDF1. All on B: lid lifted"
free_pins_no_pad: "PC13(2), PH0(5), PH1(6), PA3(13), PB0(18), PA9(30)  # integration-map §4; PB5 strapped to GND (ECR-0013 S1)"
```

## Probe points (no dedicated pad; all B unless noted; probe 2026-10-07)
```yaml
VBAT: "J5 (28.9, 1.1)"
"+3V0": "TP4 (3.1, 11.3) F; C1.1 (6.92, 0.83); C3.1 (13.23, 0.83); R5.2 (20.68, 10.8)"
VDD11: "C9.1 (5.38, 3.86); C8.1 (14.92, 9.15)"
DOCK_VBUS: "J3 (25.1, 1.7) or D5.1 (25.5, 3.5)"
VBUS: "C15.1 (20.42, 3.4) or R12.1 (17.72, 4.4)"
VSYS: "TP6 (24.0, 10.9) F; C21.1 (19.43, 0.9)"
LDO_OUT_alone: "R20.1 (23.51, 11.0) or C18.1 (23.48, 6.5) (R20 lifted)"
MIC_VDD: "C13.1 (5.12, 5.08)"
MIC_CLK: "R2 (5.48, 7.75): MCU side R2.1 N$2 = PB3 (5.48, 7.43), mic side R2.2 MIC_CLK (5.48, 8.07); duty check E6/D13 at R2.2"
MIC_DATA: "TP10"
I_SENSE: "C22.1 (15.72, 4.4)"
BTN: "R10.1 (17.62, 6.4)"
BOOT0: "R1.1 (2.58, 3.85)"
GB_P / GB_N: "R5.1 (21.32, 10.8) / R6.1 (21.32, 7.35)"
wire_pads: "OUT_A/B J1/J2, LED_A/K J7/J8, TS J9, CC J12, D+/D- J10/J11, VBAT J5, GND J4 (B, rear columns x 25-29)"
silk: "refs on Fab only (hw/pod/silk.py one-face mode); F silk = port motif + name; identify pads from board-map-phase2.png"
```

## What the MCU reads about itself (O18)
```yaml
readable_over_usb:
- {what: "+3V0 = VDDA = ADC ref", how: "VREFINT ADC4 VIN[0] -> back-calc VDDA; VBAT/4 VIN[14] (VBAT pin 1 tied to +3V0)", src: "RM0456 Rev 7 Table 329 p.1383"}
- {what: "VDD11 / die temp", how: "VCORE VIN[12] / VSENSE VIN[13]", src: same}
- {what: "VBAT, VBUS, TS", how: "PA4 VBAT_SENSE (ADC4), PA1 VBUS_SENSE, PA2 TS", src: "integration-map §8"}
- {what: "bridge supply current", how: "PA6 I_SENSE ADC1_IN11", src: "F4; sub-output issue 1"}
- {what: "charger state", how: "U3 registers over I2C2 PB13/PB14 (I2C_SCL partly routed on In2 inside the +3V0 plane, hw/pod/inner_bridge.py)", src: "integration-map F13; ECR-0018 log 2026-10-07"}
not_readable: "VSYS (TP6 only), LDO_OUT apart from +3V0, MIC_VDD + mic current, LED current, coil current, CC voltage (ILIM by enumeration)"
```

## USB self-test (O15): requirements only
```yaml
spec: "docs/sim/firmware-emulation.yaml FWSIM-R57 codec, R58 test set (ST-HELLO/RAILS/CLK/MIC/PWMAB/CHG/ZSWEEP/BTN/EVT/KNOB/CYC/USB/PINS), R59 |Z| sweep, R60 mic stream, R61 PWM-noise A/B (2026-10-02)"
firmware: "none (fw/ absent); docs/research/self-test-firmware.md (cited by O15) does not exist"
caveats:
  - "RAILS: VSYS not covered; docked values differ (VSYS ~4.5 V)"
  - "CLK: mic-clock duty 48-52 % (D13) needs a scope at R2.2 (B)"
  - "MIC: 200 kS/s x 16 bit = 3.2 Mbit/s vs USB FS bulk ~1.216 MB/s (FWSIM-R60, derived, unverified); docked = record only, never listen (spec L562)"
  - "PWMAB: bridge 200/400/800 kHz vs stopped (or R21 lifted); runs docked -> ECR-0009 conflict (DBG-12)"
  - "ZSWEEP: PA6 sees i·(2d-1): |Z|, phase at 2f + DC term (sub-output issue 1 option D, unverified); I_SENSE Kelvin error 1.29 % <= 2 % PASS (LN-M03, sim/noise/out_r2/budget.json, board sha da4e8b13, 2026-10-07); full scale > U4 300 mA (ECR-0005); docked heats U4; blocked docked by ECR-0009 unless exemption (DBG-12)"
  - "CHG: U3 status + VBAT/TS/VBUS through a charge (CC not read)"
```

## ROM bootloader pin effects (AN2606 Rev 69 Nov 2025 §89 Table 199 pp.466-469; effects derived; nets unchanged from Rev G)
```yaml
rom_dfu_pin_states:
- {pin: "PA2 TS", rom: "USART2_TX AF push-pull, pull-up, idles high", effect: "TS ~3.0 V -> U3 reads cold -> charging paused in ROM DFU (DBG-8)"}
- {pin: "PA3 free", rom: "USART2_RX input pull-up", effect: "idles high, no external load"}
- {pin: "PA4/PA5/PA6/PA7 VBAT_SENSE/MIC_VDD/I_SENSE/GA_N", rom: "SPI1 slave, pull-downs; PA6 MISO output", effect: "mic unpowered; leg-A N off; PA6 may drive I_SENSE via R22 (<= 3 mA)"}
- {pin: "PA8 GA_P", rom: untouched, effect: "R3 holds leg-A P off"}
- {pin: "PA9 free", rom: "USART1_TX output, pull-up", effect: none}
- {pin: "PA10 GB_P", rom: "USART1_RX input pull-up", effect: "+ R5 100k to +3V0 -> leg-B P off; RX idle"}
- {pin: "PB15 GB_N", rom: "SPI2_MOSI input pull-down", effect: "+ R6 100k (+ UCPD dead-battery 5.1k if still armed, ECR-0013 S2) -> leg-B N off"}
- {pin: "PB13/PB14 I2C_SCL/SDA", rom: "SPI2_SCK in pull-down / SPI2_MISO out", effect: "PB14 drives SDA; harmless while nothing talks to U3"}
- {pin: "PB5 (GND strap)", rom: "SPI3_MOSI input pull-down", effect: none}
- {pin: "PB6 DBG_TX TP7 / PB7 LED_K", rom: "I2C1 SCL/SDA open-drain pull-up", effect: "TP7 idles high; LED dark"}
- {pin: "PB8 MDF_CCK TP8", rom: "FDCAN1_RX AF pull-up", effect: "unwired: none; MDF fallback wired: pulls the unpowered mic's CLK up (same class as PB4)"}
- {pin: "PB4 MIC_DATA", rom: "not a ROM pin; reset = NJTRST internal pull-up", effect: "back-feeds unpowered mic DATA in reset + DFU (sub-audio-in issue 11); meter at TP10 / C13.1"}
- {pin: "PA11/PA12", rom: "USB FS DFU, HSI48 + CRS, no crystal, no ext pull-up; 'VDDUSB must be connected to 3.3 V'", effect: "+3V0 2.955-3.045 V (DBG-6)"}
bridge_in_dfu: "all four gates off (rows PA7, PA8, PA10, PB15)"
rom_resources: "60 MHz from HSI-PLL; 16 kB RAM from 0x2000 0000; image 0x0BF9 0000 (Table 199 p.466)"
local_copy: "scratchpad boot/an2606.pdf, fetched 2026-09-30, SHA-256 b0ed4c4839c41131 (docs/system/audit-datasheet-claims.md)"
```

## Bring-up sequence (proposal for ECR-0010; adapted from hw/mech/notes/electronics.md §A; build stages per physical.md assembly order)
```yaml
- {n: 0, stage: bare board, do: "loupe: U3 balls, U1, Q1/Q2 (Nexperia land pattern, ECR-0004), SW1, D5/D6, 0201 tombstones, pad-board LED cathode mark", fail: "photograph, stop"}
- n: 1
  stage: bare board
  do: "meter, unpowered: TP4-TP5, TP6-TP5, J5-J4, J3-J4, then every J-pad neighbour (copper gaps 0.90-1.22 mm, board probe 2026-10-07 after the J3/J4 swap): J3-J4 (dock supply short), J4-J5 (cell short), J4-D5.1 (J4 GND pad edge 0.76 mm from DOCK_VBUS), J4-J12, J4-J9, J12-J9, J12-J11, J10-J11, J10-J12, J9-J5, J9-J3, J9-J10, J1-J2, J1-J7, J1-J8, J7-J8, J7-J10, J7-J11, J8-J2, J8-J11; pad board J2-J4, J1-J3 (reg-pad issue 13); TP row TP5-TP4 (GND-+3V0, 0.8 mm)"
  expect: "no short; record board 1 as reference"
  fail: "J4-J5 = cell short (PCM cuts it). J3-J4 / J4-D5.1 = dock supply short. J12-J9 = CC on TS. J8-J2 / pad-board J2-J4 = bridge output into PB7. J1-J2 = exciter shorted across the bridge"
- {n: 2, stage: bare board, do: "bench 3.7 V, 50 mA limit, J5(+)/J4(-)", expect: "TP6 ~3.7 V; TP4 2.955-3.045 V; record blank-chip current (no reference)", fail: "lift R20 -> LDO_OUT alone at R20.1 -> 3.0 V into TP4 (30 mA limit) to split LDO side from load side"}
- {n: 3, stage: bare board, do: "first flash AP-DFU1: tack R1.1 PH3 (2.58, 3.85) B to +3V0 C1.1 (6.92, 0.83) B (5.3 mm wire; TP4 on F also works before the bond); 5 V current-limited on J3/J4, USB D+/D- on J10/J11; power-cycle; flash; remove tack. Then SWD on TP1/TP2/TP3/TP5 once, while F is still reachable", expect: "ROM DFU enumerates; image runs after tack removed; SWD attaches", fail: "AP-SWD if DFU fails (DBG-1); TP4 = Vref sense only, never drive a probe's 3.3 V into it; check NRST idles high"}
- {n: 4, stage: bare board, do: "clocks: LSE, MSI lock, PLL; scope MIC_CLK at R2.2 (B)", expect: "duty 48-52 % above 2.4 MHz (D13)", fail: "E6/R13: MDF fallback via TP8/TP9/TP10 (mdf_fallback above)"}
- {n: 5, stage: bare board, do: "pad board (or any LED) on J7/J8; press SW1; printf on TP7 (3.3 V-logic USB-UART RX)", expect: "LED on/off from PB7; +1.36 mA while pressed; PA0 high; TP7 text", fail: "LED dark = reversed"}
- {n: 6, stage: bare board, do: "USB: CDC enumerates; boot-stub jump to ROM DFU and re-flash over USB (O18); repeat with 2.95 V on TP4 (R20 lifted); meter C13.1 and TP10 in DFU (PB4 back-feed); DFU session > 160 s with charger watchdog armed (sub-power)", fail: "sub-dock-usb USB-at-3.0 V issue"}
- {n: 7, stage: bare board, do: "I2C2: read U3 at 0x6A (exercises the In2 SCL run); write register plan; charge the real cell; log via self-test", ref: "sub-power"}
- {n: 8, stage: "board bonded to the lid (TP1-TP6 now gone), lid lifted", do: "mic: PA5 on, 4 MHz; stream to PC through the real duct", expect: "spectrogram of HC-SR04 40 kHz (spec L574); duct resonance near 63 kHz visible (sub-audio-in)"}
- {n: 9, stage: same, do: "bridge: 8-12 Ω resistor on J1/J2 first (electronics.md A.5), low level; then exciter; |Z| sweep low amplitude; PWM-noise A/B", fail: "lift R21 (B) to rule the bridge out"}
- {n: 10, stage: same + puck fitted, do: "Off: Stop 2, PPK2 in series", expect: "≈15.5-22.7 µA (sub-power off_D12; derived, unmeasured)", fail: "+1.36 mA = SW1 pre-pressed: refit the puck (sub-ui issue 1)"}
- {n: 11, do: "only then close and seal (physical.md assembly order)"}
```

## Bench (O13 "iron, flux, oscilloscope, etc.: no tool purchases", spec L639)
```yaml
have: ["iron, flux, oscilloscope (O13)", "LCR meter, PPK2 Nordic Power Profiler Kit II (spec L575)", "multimeter + current-limited supply: assumed (electronics.md 'Testing'; O13 'etc.')"]
not_recorded: ["SWD probe (hardware.md §7: ST-Link V2 clone, 'not researched'; U575 support unverified)", "USB-UART 3.3 V adapter for TP7 [TBD]", "pogo pins (1.5 mm pitch row) + printed jig", "USB cable to J10/J11 (dock head stock: sub-dock-usb)", "DFU host tool for U575 [TBD: FOSS, support unverified]", "turned gauge pin D0.98/D0.50 for the bond (physical.md)"]
```

## Interfaces
```yaml
- {to: sub-processing, nets: "SWDIO PA13, SWCLK PA14, NRST, N$1 PH3-BOOT0 (R1), DBG_TX PB6, MDF_CCK PB8, MDF_SDI PB1", inv: "PA13 internal pull-up, PA14 pull-down (AN5373 Rev 7 §6.2.3 p.31); NRST pull-up 30-50 kΩ (DS13737 Rev 10 Table 100); BOOT0 latched at reset release (RM0456 Table 25 note)", rel: R-PROC-DEBUG}
- {to: sub-power, nets: "TP4 +3V0, TP6 VSYS, R20 LDO_OUT->+3V0", inv: "lift R20 before feeding TP4; R20 current rating unknown (DBG-9); battery-only power-up needs VBAT > 3.46 V max (SLUSE99C §7.5)", rel: R-PWR-DEBUG}
- {to: sub-output, nets: "BRIDGE_RTN, R21, I_SENSE (R22/C22 -> PA6)", inv: "lifting R21 floats BRIDGE_RTN: keep TIM1 stopped; Kelvin error LN-M03 1.29 % (two GND vias at R21.2)", rel: R-OUT-DEBUG}
- {to: sub-dock-usb, nets: "USB_DP/DM J10/J11, DOCK_VBUS J3, GND J4", inv: "DFU = main update path once bonded (O18); boot stub not designed"}
- {to: sub-audio-in, nets: "MIC_CLK (R2.2), MIC_VDD (C13.1), MIC_DATA (TP10), MDF fallback TP8/TP9", inv: "mic checked by USB stream; fallback is hand-wired on B"}
- {to: sub-ui, nets: "BTN (R10.1), LED_K (J8)", inv: "stuck-button flag in telemetry; LED dark in ROM DFU"}
- {to: reg-board, what: "TP1/2/4/5 row y 11.3 + TP3 + TP6 on F; TP7-TP10, R1, R20, R21 on B", inv: "F carries only SW1 + TP1-TP6 (one-face rule); TP pads inside the outline (interfaces.py [inside] PASS)", rel: R-DEBUG-BOARD}
- {to: "reg-pod-body / physical", what: "TP1-TP6 in 1.8 mm VHB cut-outs facing the lid; B face exposed when the lid is lifted", inv: "VHB bond >= the clamp-bands rule (91 % bonded, 2026-10-07); a TP move must move its cut-out (dims_r2 reads F_PADS from placement.yaml live)", rel: R-BOARD-BODY}
```

## Constraints
```yaml
O9: "debug access = board pads + snap-off frame on the JLC panel; panel rails are the frame, traces to it need a solid tab (study ASM-01)"
O15+O20: "test access must not cost size (spec L646): Phase 2 met it by bare F pads under the VHB + B-face dots (no extra area for a pogo row outside a clamp band)"
O18: "DFU most-verified; SWD backup; board measures itself; spare pins to pads; removals stated"
O13: "no tool purchases"
O25: "pad order and TP placement are Claude's (layout), reviewed by the owner"
O10: "bonded build: SWD = peel the board off the lid; DFU must be proven first"
spec_L562: "listening on battery only; USB streaming records only"
option_bytes: "set nSWBOOT0=0, nBOOT0=1 only once a write-protected boot stub works (periphery.md §2.8; AN5373 Table 4; FWSIM HWC-12: RDP 0 on rev 1)"
```

## Key numbers
```yaml
- {q: "TP1-TP6 pads", v: "Ø0.7; row TP5/TP4/TP2/TP1 at x 1.6-6.1 pitch 1.5 (0.8 mm gap), y 11.3; TP3 (9.3, 2.9); TP6 (24.0, 10.9); F", src: "routed board probe 2026-10-07"}
- {q: "VHB at the TPs", v: "1.8 mm square cut per pad; 91 % of the VHB face bonded", src: "dims_r2 TP_PAD_D 1.0 [A] + 2 x 0.4; interfaces.py clamp-bands 2026-10-07"}
- {q: "TP7-TP10 dots", v: "Ø0.5 (TestDot_D0.5mm), B", src: "gen.py PAD_DOT; board probe 2026-10-07"}
- {q: "J pads", v: "Ø1.0 on B (J4 1.0 x 2.0); copper gaps 1.17-1.22 mm between neighbours (rule >= 0.8, MZD-10)", src: "board positions 2026-10-07, derived"}
- {q: "AP-DFU1 tack", v: "R1.1 (2.58, 3.85) -> C1.1 +3V0 (6.92, 0.83): 5.3 mm, both B", src: "board probe 2026-10-07"}
- {q: "boot", v: "BOOT0=0 -> flash 0x0800 0000; BOOT0=1 -> bootloader 0x0BF9 0000", src: "RM0456 Rev 7 (Mar 2026) Table 25 p.192"}
- {q: "DFU tack current", v: "3.0 V / 10k = 0.3 mA through R1", src: derived}
- {q: NRST, v: "pull-up 30/40/50 kΩ; with C10 τ ≈ 4 ms", src: "DS13737 Rev 10 (Jul 2024) Table 100 p.238; τ derived"}
- {q: "U3 battery-only POR", v: "VBATPOR 3.08/3.21/3.46 V", src: "SLUSE99C (Jan 2023) §7.5"}
- {q: "+3V0", v: "2.955-3.045 V", src: "SBVS338H §5.5 via sub-power"}
- {q: "USB at 3.0 V", v: "'functionality ensured down to 2.7 V, some electrical characteristics degraded 2.7-3.0 V'", src: "DS13737 Rev 10 Table 150 fn 1 (verified 2026-10-02)"}
- {q: "R21 signal", v: "31 mV at ~315 mA peak, ~170 counts 14-bit; 10 mW of 166 mW", src: "gen.py R21 comment; docs/research/simplify/output.md L86"}
- {q: "I_SENSE filter", v: "15.9 kHz (1 kΩ x 10 nF)", src: derived}
- {q: "I_SENSE Kelvin error", v: "1.29 % of R21 at 5 kHz (limit 2 %); was 3.31 % before kelvin_r21.py", src: "LN-M03, sim/noise/out_r2/budget.json (board sha da4e8b13), 2026-10-07"}
- {q: "+3V0 peak", v: "326 mA > U4 300 mA (WARN, ECR-0005)", src: "interfaces.py rails 2026-10-07"}
- {q: "Off current", v: "≈15.5-22.7 µA estimate", src: "sub-power.md off_D12"}
- {q: "board", v: "30 x 12 x 0.8 mm, 4 layers (F / In1 GND / In2 +3V0 / B)", src: "interfaces.py outline PASS 2026-10-07; board probe"}
```

## Open issues (IDs stable; gaps = closed, see git)
```yaml
- id: DBG-1
  t: "First-flash path: AP-DFU1 (no probe, B-face tack) with SWD as a bench-only backup; no SWD probe recorded (O13). Depends on USB at 3.0 V (DBG-6) and a DFU host tool [TBD]"
  options: "A buy a probe (breaks O13; O21 defers) / B DFU-first only / C both"
  rec: "B now; C only if DFU-first fails on board 1"
  owner: "FWSIM decision 9 (firmware-emulation.yaml L428) recommends C: owner picks"
- id: DBG-2
  t: "TP row puts +3V0 beside GND: TP4 | TP5 at 0.8 mm; a smear or a jig off by one pitch shorts the rail (TP6 VSYS now separate)"
  close: "reorder (e.g. SWDIO, GND, SWCLK, +3V0) at the next placement edit; dims_r2 reads F_PADS live, so the VHB cut-outs follow"
- id: DBG-3
  t: "snap-off test frame (O9) not designed for 30 x 12"
  options: "A header strip wired through a solid tab / B rec: no-wire frame: panel tooling holes locate a printed jig on TP1-TP6 (1.5 mm pitch) / C none: tack wires once, then DFU"
- id: DBG-4
  t: "O18 gaps: 6 free pins without pads (PC13, PH0, PH1, PA3, PB0, PA9); not readable: VSYS, MIC_VDD, LED current, coil current, CC"
  option: "FWSIM HWC-9: PA3 (ADC1_IN8) could sense VSYS or MIC_VDD via a divider: not in the design"
- id: DBG-5
  t: "self-test = requirements only (FWSIM-R57..R61); no firmware; self-test-firmware.md missing; |Z| method unverified (sub-output issue 1 option D)"
  close: "verify option D in sim/checks/bridge_spice.py (LN-M03 now passes)"
  status: "method verified 2026-10-07 (sim/checks/selftest_lockin.py): -12 dBFS |Z| <= 1.9 %, phase <= 0.7 deg; -22 dBFS <= 3 % / 3.4 deg at 0.25 s/point; -32 unusable. Needs the (B) 100k offset R (not in gen.py yet: schematic + placement/route item). Firmware note still missing (PROC-7)"
- id: DBG-6
  t: "ROM DFU: AN2606 'VDDUSB must be 3.3 V' vs +3V0 2.955-3.045 V; DS13737 fn 1: functional, degraded electricals below 3.0 V (sub-dock-usb)"
  close: "bring-up steps 3 + 6 incl. 2.95 V on TP4"
- id: DBG-8
  t: "ROM DFU pauses charging (PA2 USART2_TX drives TS high)"
  close: "boot stub leaves U3 known; check step 6 with a cell"
- id: DBG-9
  t: "R20 current rating unknown (sub-power); never feed TP4 with R20 fitted (back-drives U4 output; TI behaviour unsourced)"
- id: DBG-10
  t: "stale round-1 SWD scheme (1x5 header, front-edge column, lid-screw charging) in hw/mech/notes/electronics.md §A, docs/research/pcb-mech-interface.md §7-§8, docs/build/hardware.md §7"
  status: "banners added 2026-10-07 (electronics.md, pcb-mech-interface.md); hardware.md lid-screw charging section 6 bannered too; the SWD header scheme lives only in those bannered notes now"
- id: DBG-11
  t: "no test-access map (TPs, dots, probe points, lift links, both faces, per build stage) or bring-up flow PNG; board-map-phase2.png covers part"
- id: DBG-12
  t: "ECR-0009 (no output while VBUS) blocks docked ZSWEEP and PWMAB"
  options: "a rec: capped self-test-only exemption in ECR-0009 (drive <= ~-12 dBFS; covers ECR-0005, U4 heating) / b run on battery, log, read back over USB"
  same_as: "sub-output issue 12, sub-power issue 5; FWSIM-R59/R61 implement both"
- id: DBG-16
  t: "SWD is gone after the board->lid bond: a bricked app on a bonded pod means peeling/sawing the board off the VHB (physical.md reopening table: lid reprint). DFU-via-stub must be proven on the bare board (step 6) before step 8"
  close: "bring-up gate in physical.md: no lid bond before step 6 passes; boot stub write-protected (option_bytes)"
  status: "gate written into physical.md assembly step 8 (2026-10-07); remains: boot stub + option-byte WRP (fw agent), step 6 on board 1"
- id: DBG-17
  t: "B-face access while the board hangs from the lid relies on the arm/dock/cell wires' slack (lid lifts the board on its wires); slack length not designed"
  close: "wire-route design (physical.md, reg-board stowage zone)"
  status: "slack computed 2026-10-07: arm needs 2.65/3.04 mm (5 mm loop in heel.md); dock ribbon 0.0 worst (2 mm loop recommended); physical.md Service"
```

## Before changing this, check
```yaml
tp_pads: "F = SW1 + TP1-TP6 only (one-face); VHB cut-outs + bonded fraction (interfaces.py clamp-bands); jig/frame pitch (DBG-3); mirror pod (physical.md); DBG-2 order"
r1_boot0: "AP-DFU1 tack point must stay on B and reachable with the lid lifted (HWC-2); RM0456 Table 25; AN2606 Table 199"
pa10_pb15: "ROM states keep leg B off (table above); R5/R6 stay"
dots: "TP7 printf (HWC-3); TP8-TP10 = only MDF fallback (sub-audio-in issue 5)"
r20: "every +3V0 load (sub-power); USB margin; ECR-0005 peak through a 0402 jumper"
r21_r22_c22: "F4 method (sub-output issue 1); LN-M03 Kelvin vias (hw/pod/kelvin_r21.py); PA6 vs TIM1_BKIN (sub-processing)"
removal: "O18: state and justify"
tools: "python3 tools/plm.py impact SUB-DEBUG-TEST; python3 tools/checks/interfaces.py; integration-map.md §10"
```

## Reference design (Rev F/G)
`ULTRASONIC_DESIGN=revg`: two-face 34 × 13 board `hw/pod/draft_r1/pod_r1_routed.kicad_pcb`: TP1-TP6 pogo row Ø0.7 on 1.27 mm pitch at F (24.4-30.75, 1.3), outside a 0.6 mm clamp band; TP7 on F (13.2, 1.5); TP8-TP10 on B by the mic; R1 PH3 pad on F (16.49, 1.60); R21 1206 (C25334) at (21.6, 7.6) B; LN-M03 5.2 % FAIL; SWCLK→TP2 and LED_K unrouted; J pads on F with 0.60-0.89 mm neighbour gaps (J4-J5 cell short at 0.60). History: git.
