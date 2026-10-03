# SUB-DEBUG-TEST: SWD, test pads + dots, isolation links, ROM DFU, USB self-test, bring-up
Changelog: Rev F 2026-10-02: R11 removed (ROM loader pulls PA10 up; PA10 = GB_P now, R5 also pulls it up); TP7 printf dot + TP8–TP10 MDF mic-fallback dots added; leg B on PA10/PB15, PA3/PA9/PB0 free; J6 merged into shared GND pad J4 (J3|J4|J5); first flash = DFU-first via R1's PH3 pad; board routed.
Status: schematic Rev F (`hw/pod/gen.py` 407e143, 2026-10-02); board routed `hw/pod/draft_r1/pod_r1_routed.kicad_pcb` (687 tracks, 118 vias; **2 unconnected incl. SWCLK→TP2**; DRC 19 courtyard overlaps only, none on a TP; `summary.json`, `drc.json` 2026-10-02T20:07). Not done: snap-off test frame; self-test firmware (requirements only, FWSIM-R57..R61); no hardware ordered (O21) → no bring-up. Updated 2026-10-02.

```yaml
abbrev: {SWD: "Arm 2-wire debug port", DFU: "USB Device Firmware Upgrade (ST ROM bootloader)", CDC: "USB virtual serial port", TP: "test pad/dot", P50: "spring test pin, 1.27 mm pitch", MDF/ADF: "STM32U5 multi/audio digital filter", F/B: "board faces: F = outer (lid), B = inner (cell)", "(x, y)": "board mm, origin top-left, KiCad top view"}
src_of_truth: ["hw/pod/gen.py L153-155 (NRST, C10, R1), L193-200 (R21/R22/C22), L253 (R20), L274-291 (TP1-TP10, spare pins)", "hw/pod/place_r1.py L45-46, L49 (TP row), L57 (TP7), L60 (TP8-TP10), L68, L76", "hw/lib/pod.pretty/TestPoint_Pad_D0.7mm, TestDot_D0.5mm", "docs/system/pin-contract.yaml (DBG_TX, MDF_CCK, MDF_SDI, SWDIO, SWCLK, NRST, BOOT0)", "docs/system/integration-map.md F14 (generated)"]
owner_decisions: {O9: "rev 1 = prototype: pads + snap-off frame", O10: "bonded final build, cut-openable", O13: "own bench, no tool purchases", O14: "layout together", O15: "self-test over USB (size clause superseded by O20)", O18: "fail informatively; DFU most-verified, SWD backup; spare pins to pads; removals stated", O19: "diagnosability", O20: "test access must not cost size", O21: "no orders before freeze", O22: "freeze = evidence gate"}
ecrs_open: {ECR-0003: "implemented in Rev F; file still says proposed", ECR-0005: "self-test drive level vs U4 300 mA", ECR-0009: "no output while docked vs docked self-test (DBG-12)", ECR-0010: "bring-up plan + firmware before order", ECR-0013: "S1 implemented (PB5 strapped to GND); S2 firmware (UCPD_DBDIS order) open; S3 partial (C15 25 V, C21 still 10 V)", ECR-0015: "Package B Phase 2: SIZ-01/02, ASM-09 'post-bond hand pads on B' would move TP row + R1 pad (DBG-13)"}
diagrams: ["docs/diagrams/schematic-rev1.png (Rev F flowchart, 56eb73e)", "docs/diagrams/board-map-revF.png (tools/board_map.py, build output)", "board-regions.png is Rev E (2026-10-01): stale"]
```

## Scope
```yaml
carries: [F14 debug/flash/test, "F4 test side (|Z| self-test; circuit owned by sub-output)"]   # integration-map §1
brief: "O18: rev 1 will partly fail; every failure diagnosable from the board (hooks, telemetry, isolation links); USB DFU = most-verified path; SWD = backup"
access_paths:
  - {id: AP-DFU1, what: "first flash, blank chip: tack R1 PH3 pad -> +3V0 at reset -> ROM USB DFU on J10/J11", src: "integration-map F14 'R1 pad = DFU tack point'; FWSIM HWC-2; periphery.md §2.8 (2026-10-02)"}
  - {id: AP-SWD, what: "SWD on TP1/TP2/TP3/TP5 (TP4 = probe Vref sense only); backup + recovery", src: gen.py L274-280}
  - {id: AP-USB, what: "app CDC self-test stream + boot-stub jump to ROM DFU for updates (boot stub not designed: sub-dock-usb)", src: "integration-map F10"}
  - {id: AP-UART, what: "TP7 = PB6 USART1_TX printf (works with USB dead; SWO lost to MIC_CLK on PB3)", src: "pin-contract.yaml DBG_TX"}
  - {id: AP-HAND, what: "probe pads/dots/cap terminals; lift R20 (rail) or R21 (bridge)", src: gen.py L196, L253}
why_blank_needs_hook: "R1 holds BOOT0 low -> boot from (empty) flash; U575 has no empty-flash->bootloader rule (RM0456 Rev 7 Table 25 p.192; AN2606 Rev 69 Pattern 12)"
```

## Elements (Rev F, positions from pod_r1_routed.kicad_pcb 2026-10-02)
```yaml
elements:
- {ref: TP1-TP6, part: "Ø0.7 copper pad, P50/probe", nets: "TP1 SWDIO PA13(34) · TP2 SWCLK PA14(37) · TP3 NRST(7) · TP4 +3V0 · TP5 GND · TP6 VSYS", at: "(24.40 + 1.27 i, 1.30) F, i=0..5", src: place_r1.py L49}
- {ref: TP7, part: "Ø0.5 dot", net: "DBG_TX = PB6(42) USART1_TX AF7", at: "(13.20, 1.50) F"}
- {ref: TP8, part: "Ø0.5 dot", net: "MDF_CCK = PB8(45) MDF1_CCK0 AF5", at: "(8.70, 9.40) B"}
- {ref: TP9, part: "Ø0.5 dot", net: "MDF_SDI = PB1(19) MDF1_SDI0 AF6", at: "(8.70, 3.60) B"}
- {ref: TP10, part: "Ø0.5 dot", net: "MIC_DATA (PB4(40), U2 DATA)", at: "(7.30, 3.00) B"}
- {ref: R1, part: "10k 1% 0402, BOOT0 pull-down", net: "N$1 = PH3-BOOT0(44)", at: "(17.0, 1.6) F; PH3 pad (16.49, 1.60)", lcsc: "C25744 Basic, 21.8 M (JLC API 2026-10-02T00:25Z)"}
- {ref: C10, part: "100nF 0402 X7R NRST filter", net: NRST, at: "(8.3, 7.88) F", lcsc: "C1525 Basic, 21.7 M (same query)"}
- {ref: R20, part: "0R 0402 link LDO_OUT->+3V0", at: "(23.4, 11.4) B; LDO pad (23.91, 11.40)", lcsc: "C17168 Basic, 9.30 M (same query)"}
- {ref: R21, part: "1206W4F100LT5E 0.1R ±1% 250 mW 1206 low-side shunt", net: "BRIDGE_RTN->GND", at: "(21.6, 7.6) B", lcsc: "C25334 Basic, 121,425 (same query)"}
- {ref: "R22, C22", part: "1k / 10nF 0402 low-pass 15.9 kHz", net: "BRIDGE_RTN->I_SENSE->PA6(16) ADC1_IN11", at: "(12.6, 11.6) / (10.6, 11.6) F", lcsc: "C11702 / C15195 Basic"}
mdf_fallback: "ADF clock duty out of spec (sub-audio-in issue 5): lift R2, wire TP8 -> R2 mic-side pad R2.2 = MIC_CLK (7.30, 7.49) B (R2.1 = N$2 = PB3 at (7.30, 8.51); pcbnew probe 2026-10-02), TP9 -> TP10; firmware moves mic to MDF1 (gen.py L282-283). B face: board out of the pod"
free_pins_no_pad: "PC13(2), PH0(5), PH1(6), PA3(13), PB0(18), PA9(30)  # integration-map §4; PC13 static (ES0499 §2.2.1); PB5 strapped to GND (ECR-0013 S1)"
```

## Probe points (no dedicated pad)
```yaml
VBAT: J5 (31.40, 7.20) F
"+3V0": "TP4; C3 pad1 (17.60, 3.99) F; C1 pad1 (9.40, 2.33) F"
VDD11: "C8 pad1 (17.12, 11.50) / C9 pad1 (19.82, 8.57) F"
DOCK_VBUS: "J3 (31.40, 3.00) F or D5 pad1 (29.90, 3.70) F"
VBUS: "C15 pad1 (21.20, 2.68) B or R12 pad1 (25.30, 2.71) B"
VSYS: "TP6; C21 pad1 (24.02, 2.00) B"
LDO_OUT_alone: "R20 pad1 (23.91, 11.40) B or C18 pad1 (24.68, 8.90) B (R20 lifted)"
MIC_VDD: "C13 pad1 (7.30, 5.48) B"
MIC_CLK: "R2 (7.30, 8.00) B: MCU side R2.1 N$2 = PB3 (7.30, 8.51), mic side R2.2 MIC_CLK (7.30, 7.49); duty check E6/D13 here"
MIC_DATA: TP10 B
I_SENSE: "C22 pad1 (10.12, 11.60) F"
BTN: "R10 pad1 (22.49, 9.50) F"
BOOT0: "R1 pad1 (16.49, 1.60) F"
GB_P / GB_N: "R5 pad1 (19.41, 6.60) / R6 pad1 (19.41, 9.40) B"
wire_pads: "OUT_A/B J1/J2, LED_A/K J7/J8, TS J9, CC J12, D+/D- J10/J11 (F, rear)"
silk: "refs on Fab only (hw/pod/silk.py, 2026-10-02): identify pads from board-map-revF.png, not the board"
```

## What the MCU reads about itself (O18)
```yaml
readable_over_usb:
- {what: "+3V0 = VDDA = ADC ref", how: "VREFINT ADC4 VIN[0] -> back-calc VDDA; VBAT/4 VIN[14] (VBAT pin 1 tied to +3V0)", src: "RM0456 Rev 7 Table 329 p.1383"}
- {what: "VDD11 / die temp", how: "VCORE VIN[12] / VSENSE VIN[13]", src: same}
- {what: "VBAT, VBUS, TS", how: "PA4 VBAT_SENSE (ADC4), PA1 VBUS_SENSE, PA2 TS", src: "integration-map §8"}
- {what: "bridge supply current", how: "PA6 I_SENSE ADC1_IN11", src: "F4; sub-output issue 1"}
- {what: "charger state", how: "U3 registers over I2C2 PB13/PB14", src: "integration-map F13"}
not_readable: "VSYS (TP6 only), LDO_OUT apart from +3V0, MIC_VDD + mic current, LED current, coil current, CC voltage (R19 removed Rev F; ILIM by enumeration)"
```

## USB self-test (O15): requirements only
```yaml
spec: "docs/sim/firmware-emulation.yaml FWSIM-R57 codec, R58 test set (ST-HELLO/RAILS/CLK/MIC/PWMAB/CHG/ZSWEEP/BTN/EVT/KNOB/CYC/USB/PINS), R59 |Z| sweep, R60 mic stream, R61 PWM-noise A/B (2026-10-02)"
firmware: "none (fw/ absent, 2026-10-02); docs/research/self-test-firmware.md (cited by O15) does not exist"
caveats:
  - "RAILS: VSYS not covered; docked values differ (VSYS ~4.5 V)"
  - "CLK: mic-clock duty 48-52 % (D13) needs a scope at R2"
  - "MIC: 200 kS/s x 16 bit = 3.2 Mbit/s vs USB FS bulk ~1.216 MB/s (FWSIM-R60, derived, unverified); docked = record only, never listen (spec L562)"
  - "PWMAB: bridge 200/400/800 kHz vs stopped (or R21 lifted); runs docked -> ECR-0009 conflict (DBG-12)"
  - "ZSWEEP: PA6 sees i·(2d-1): |Z|, phase at 2f + DC term (sub-output issue 1 option D, unverified); I_SENSE Kelvin error 5.2 % vs <= 2 % on Rev F (LN-M03; sim/noise/smoke.sh on hw/pod/draft_r1/pod_r1_routed.kicad_pcb (sha e159bccb, 2026-10-02 21:20); LF-1 = R21 pad-2 GND stub, layout-noise.yaml); full scale > U4 300 mA (ECR-0005); docked heats U4; blocked docked by ECR-0009 unless exemption (DBG-12)"
  - "CHG: U3 status + VBAT/TS/VBUS through a charge (CC no longer read)"
```

## ROM bootloader pin effects (AN2606 Rev 69 Nov 2025 §89 Table 199 pp.466-469; effects derived for Rev F nets)
```yaml
rom_dfu_pin_states:
- {pin: "PA2 TS", rom: "USART2_TX AF push-pull, pull-up, idles high", effect: "TS ~3.0 V -> U3 reads cold -> charging paused in ROM DFU (DBG-8)"}
- {pin: "PA3 free", rom: "USART2_RX input pull-up", effect: "idles high, no external load -> no false USART2 detect (CC-steal risk gone with R19)"}
- {pin: "PA4/PA5/PA6/PA7 VBAT_SENSE/MIC_VDD/I_SENSE/GA_N", rom: "SPI1 slave, pull-downs; PA6 MISO output", effect: "mic unpowered; leg-A N off; PA6 may drive I_SENSE via R22 (<= 3 mA)"}
- {pin: "PA8 GA_P", rom: untouched, effect: "R3 holds leg-A P off"}
- {pin: "PA9 free", rom: "USART1_TX output, pull-up", effect: none}
- {pin: "PA10 GB_P", rom: "USART1_RX input pull-up", effect: "+ R5 100k to +3V0 -> leg-B P off; RX idle"}
- {pin: "PB15 GB_N", rom: "SPI2_MOSI input pull-down", effect: "+ R6 100k (+ UCPD dead-battery 5.1k if still armed, ECR-0013 S2) -> leg-B N off"}
- {pin: "PB13/PB14 I2C_SCL/SDA", rom: "SPI2_SCK in pull-down / SPI2_MISO out", effect: "PB14 drives SDA; harmless while nothing talks to U3"}
- {pin: "PB5 (GND strap)", rom: "SPI3_MOSI input pull-down", effect: none}
- {pin: "PB6 DBG_TX TP7 / PB7 LED_K", rom: "I2C1 SCL/SDA open-drain pull-up", effect: "TP7 idles high; LED dark"}
- {pin: "PB8 MDF_CCK TP8", rom: "FDCAN1_RX AF pull-up", effect: "unwired: none; MDF fallback wired: pulls the unpowered mic's CLK up (same class as PB4)"}
- {pin: "PB4 MIC_DATA", rom: "not a ROM pin; reset = NJTRST internal pull-up", effect: "back-feeds unpowered mic DATA in reset + DFU (sub-audio-in issue 11); meter at TP10 / C13"}
- {pin: "PA11/PA12", rom: "USB FS DFU, HSI48 + CRS, no crystal, no ext pull-up; 'VDDUSB must be connected to 3.3 V'", effect: "+3V0 2.955-3.045 V (DBG-6)"}
bridge_in_dfu: "all four gates off (rows PA7, PA8, PA10, PB15)"
rom_resources: "60 MHz from HSI-PLL; 16 kB RAM from 0x2000 0000; image 0x0BF9 0000 (Table 199 p.466)"
local_copy: "scratchpad boot/an2606.pdf, fetched 2026-09-30, SHA-256 b0ed4c4839c41131 (docs/system/audit-datasheet-claims.md)"
```

## Bring-up sequence (proposal for ECR-0010; no source defines one; adapted from hw/mech/notes/electronics.md §A)
```yaml
- {n: 0, do: "loupe: U3 balls, U1, Q1/Q2 (Nexperia land pattern, ECR-0004), SW1, D5, pad-board LED cathode mark", fail: "photograph, stop"}
- n: 1
  do: "meter, unpowered: TP4-TP5, TP6-TP5, J5-J4, J3-J4, then every J-pad neighbour (Rev F map, 0.6-0.9 mm edge gaps, place_r1.py L51-54): J4-J5, J5-J12, J5-J9, J5-J1, J3-J10, J4-J11, J4-J12, J10-J11, J11-J12, J12-J1, J1-J2, J2-J8, J7-J8, J7-J2, J9-J7, J9-J1, J9-J2, J3-D5; pad board J2-J4, J1-J3 (reg-pad issue 13)"
  expect: "no short; record board 1 as reference"
  fail: "J4-J5 = cell short (PCM trips). J5-J12 = VBAT on the exposed CC contact. J3-J4 = dock supply short. J2-J8 / pad-board J2-J4 = bridge output into PB7. J12-J1 = OUT_A on exposed CC. J9-J7 = VSYS via R14 into TS"
- {n: 2, do: "bench 3.7 V, 50 mA limit, J5(+)/J4(-)", expect: "TP6 ~3.7 V; TP4 2.955-3.045 V; record blank-chip current (no reference)", fail: "lift R20 -> LDO_OUT alone at R20 pad1 -> 3.0 V into TP4 (30 mA limit) to split LDO side from load side"}
- {n: 3, do: "first flash AP-DFU1: tack R1 PH3 pad (16.49, 1.60) to C3 pad1 +3V0 (17.60, 3.99), 2.6 mm; 5 V current-limited on J3/J4, USB D+/D- on J10/J11; power-cycle; flash; remove tack", expect: "ROM DFU enumerates; image runs after tack removed", fail: "AP-SWD on TP1/TP2/TP3/TP5 if a probe is available (DBG-1); TP4 = Vref sense only, never drive a probe's 3.3 V into it; check NRST idles high"}
- {n: 4, do: "clocks: LSE, MSI lock, PLL; scope MIC_CLK at R2 (B)", expect: "duty 48-52 % above 2.4 MHz (D13)", fail: "E6/R13: MDF fallback via TP8/TP9/TP10 (mdf_fallback above)"}
- {n: 5, do: "pad board (or any LED) on J7/J8; press SW1; printf on TP7 (3.3 V-logic USB-UART RX)", expect: "LED on/off from PB7; +1.36 mA while pressed; PA0 high; TP7 text", fail: "LED dark = reversed"}
- {n: 6, do: "USB: CDC enumerates; boot-stub jump to ROM DFU and re-flash over USB (O18); repeat with 2.95 V on TP4 (R20 lifted); meter MIC_VDD and TP10 in DFU (PB4 back-feed); DFU session > 160 s with charger watchdog armed (sub-power issue 3)", fail: "sub-dock-usb issue 6"}
- {n: 7, do: "I2C2: read U3 at 0x6A; write register plan; charge the real cell; log via self-test", ref: "sub-power issues 2-4"}
- {n: 8, do: "mic: PA5 on, 4 MHz; stream to PC", expect: "spectrogram of HC-SR04 40 kHz (spec L574)"}
- {n: 9, do: "bridge: 8-12 Ω resistor on J1/J2 first (electronics.md A.5), low level; then exciter; |Z| sweep low amplitude; PWM-noise A/B", fail: "lift R21 to rule the bridge out"}
- {n: 10, do: "Off: Stop 2, PPK2 in series", expect: "≈15.5-22.7 µA (sub-power off_D12: U3 3-3.5 µA with EN_PUSH 0, watchdog off; derived, unmeasured)", fail: "+1.36 mA = SW1 pre-pressed"}
- {n: 11, do: "only then depanel and build in (physical.md assembly order)"}
```

## Bench (O13 "iron, flux, oscilloscope, etc.: no tool purchases", spec L639)
```yaml
have: ["iron, flux, oscilloscope (O13)", "LCR meter, PPK2 Nordic Power Profiler Kit II (spec L575)", "multimeter + current-limited supply: assumed (electronics.md 'Testing'; O13 'etc.')"]
not_recorded: ["SWD probe (hardware.md §7 L412: ST-Link V2 clone, 'not researched'; U575 support unverified)", "USB-UART 3.3 V adapter for TP7 [TBD]", "P50 pogo pins + printed jig", "USB cable to J10/J11 (dock head stock: sub-dock-usb issue 1)", "DFU host tool for U575 [TBD: FOSS, support unverified]"]
```

## Interfaces
```yaml
- {to: sub-processing, nets: "SWDIO PA13, SWCLK PA14, NRST, N$1 PH3-BOOT0 (R1), DBG_TX PB6, MDF_CCK PB8, MDF_SDI PB1", inv: "PA13 internal pull-up, PA14 pull-down (AN5373 Rev 7 §6.2.3 p.31); NRST pull-up 30-50 kΩ (DS13737 Rev 10 Table 100); BOOT0 latched at reset release (RM0456 Table 25 note)", rel: R-PROC-DEBUG}
- {to: sub-power, nets: "TP4 +3V0, TP6 VSYS, R20 LDO_OUT->+3V0", inv: "lift R20 before feeding TP4; R20 current rating unknown (DBG-9); battery-only power-up needs VBAT > 3.46 V max (SLUSE99C §7.5)", rel: R-PWR-DEBUG}
- {to: sub-output, nets: "BRIDGE_RTN, R21, I_SENSE (R22/C22 -> PA6)", inv: "lifting R21 floats BRIDGE_RTN: keep TIM1 stopped; Kelvin error LN-M03", rel: R-OUT-DEBUG}
- {to: sub-dock-usb, nets: "USB_DP/DM J10/J11, DOCK_VBUS J3, GND J4", inv: "DFU = main update path (O18); boot stub not designed (sub-dock-usb issue 4)"}
- {to: sub-audio-in, nets: "MIC_CLK (R2), MIC_VDD (C13), MIC_DATA (TP10), MDF fallback TP8/TP9", inv: "mic checked by USB stream; fallback is hand-wired, B face"}
- {to: sub-ui, nets: "BTN (R10), LED_K (J8)", inv: "stuck-button flag in telemetry; LED dark in ROM DFU"}
- {to: reg-board, what: "TP row y 1.3 F, TP7 F, TP8-TP10 B, R1 F, R20/R21 B", inv: "TP row pad edge 0.35 mm clear of the 0.6 mm clamp band (1.3 - 0.35 - 0.6); interfaces.py clamp-bands exempts the 10 TPs; SWCLK->TP2 unrouted (DBG-14)", rel: R-DEBUG-BOARD}
- {to: "reg-pod-body / physical", what: "TP row + R1 under the lid (F)", inv: "right pod: TP edge (y 0) at the bottom = KiCad top view rotated 180° (physical.md, derived)"}
```

## Constraints
```yaml
O9: "debug access = board pads + snap-off frame on the JLC panel; panel rails are the frame, traces to it need a solid tab (study ASM-01)"
O15+O20: "test access must not cost size (spec L646); Phase 2 re-sizes (DBG-13)"
O18: "DFU most-verified; SWD backup; board measures itself; spare pins to pads; removals stated"
O13: "no tool purchases; double-sided"
O14: "layout (TP order, SWCLK route) done together"
O10: "bonded build: SWD = cut open; DFU must be proven first"
spec_L562: "listening on battery only; USB streaming records only"
option_bytes: "set nSWBOOT0=0, nBOOT0=1 only once a write-protected boot stub works (periphery.md §2.8; AN5373 Table 4; FWSIM HWC-12: RDP 0 on rev 1)"
```

## Key numbers
```yaml
- {q: "TP1-TP6 pads", v: "Ø0.7 on 1.27 mm = 0.57 mm gap; x 24.40-30.75, y 1.30, F", src: "place_r1.py L49; pod.pretty (2026-10-02)"}
- {q: "TP7-TP10 dots", v: "Ø0.5 (TestDot_D0.5mm)", src: "gen.py PAD_DOT; pod.pretty"}
- {q: "J pad pitch / gap", v: "1.6 mm centres, Ø1.0 -> 0.6 mm gap; J4 1.0 x 2.0", src: "place_r1.py L51-54; gen.py PAD_GND2"}
- {q: "boot", v: "BOOT0=0 -> flash 0x0800 0000; BOOT0=1 -> bootloader 0x0BF9 0000", src: "RM0456 Rev 7 (Mar 2026) Table 25 p.192"}
- {q: "DFU tack current", v: "3.0 V / 10k = 0.3 mA through R1", src: derived}
- {q: NRST, v: "pull-up 30/40/50 kΩ; with C10 τ ≈ 4 ms", src: "DS13737 Rev 10 (Jul 2024) Table 100 p.238; τ derived"}
- {q: "U3 battery-only POR", v: "VBATPOR 3.08/3.21/3.46 V", src: "SLUSE99C (Jan 2023) §7.5"}
- {q: "+3V0", v: "2.955-3.045 V", src: "SBVS338H §5.5 via sub-power"}
- {q: "USB at 3.0 V", v: "'functionality ensured down to 2.7 V, some electrical characteristics degraded 2.7-3.0 V'", src: "DS13737 Rev 10 Table 150 fn 1 (verified 2026-10-02)"}
- {q: "R21 signal", v: "31 mV at ~315 mA peak, ~170 counts 14-bit; 10 mW of 250 mW", src: "gen.py L193-195"}
- {q: "I_SENSE filter", v: "15.9 kHz (1 kΩ x 10 nF)", src: derived}
- {q: "I_SENSE Kelvin error", v: "5.2 % of R21 at 5 kHz (limit 2 %)", src: "LN-M03: sim/noise/smoke.sh on hw/pod/draft_r1/pod_r1_routed.kicad_pcb (sha e159bccb, 2026-10-02 21:20)"}
- {q: "Off current", v: "≈15.5-22.7 µA estimate (U3 3-3.5 µA with EN_PUSH 0, watchdog off)", src: "sub-power.md off_D12"}
- {q: "board", v: "34 x 13 x 0.8 mm, 4 layers", src: "interfaces.py outline PASS 2026-10-02"}
```

## Open issues (IDs stable; gaps = closed, see git)
```yaml
- id: DBG-1
  t: "First-flash path. Rev F hardware supports AP-DFU1 (no probe, no new pad) with SWD pads as backup; no SWD probe recorded (O13). Depends on USB at 3.0 V (DBG-6) and a DFU host tool [TBD]"
  options: "A buy a probe (breaks O13; O21 defers) / B DFU-first only / C both"
  rec: "B now; C only if DFU-first fails on board 1"
  owner: "FWSIM decision 9 (firmware-emulation.yaml L428) recommends C: owner picks"
- id: DBG-2
  t: "TP row puts rails beside GND: TP4 +3V0 | TP5 GND | TP6 VSYS at 0.57 mm; a smear or a jig off by one pitch shorts a rail"
  close: "reorder in the layout session (O14); candidate NRST, GND, SWDIO, +3V0, SWCLK, VSYS (each neighbour short harmless or current-limited; this doc 2026-10-01; round-1 rule in pcb-mech-interface.md §8)"
- id: DBG-3
  t: "snap-off test frame (O9) not designed for 34 x 13"
  options: "A header strip wired through a solid tab (crosses the clamp band; 6 cut trace ends to seal) / B rec: no-wire frame: panel tooling holes locate a printed P50 jig on TP1-TP6 / C none: tack wires once, then DFU"
- id: DBG-4
  t: "O18 gaps: 6 free pins without pads (PC13, PH0, PH1, PA3, PB0, PA9; study PER-12 states dots only for PB6/PB8/PB1/MIC_DATA); not readable: VSYS, MIC_VDD, LED current, coil current, CC; MIC_CLK only at R2 (B)"
  option: "FWSIM HWC-9: PA3 (ADC1_IN8) could sense VSYS or MIC_VDD via a divider: not in Rev F"
- id: DBG-5
  t: "self-test = requirements only (FWSIM-R57..R61); no firmware; self-test-firmware.md missing; |Z| method unverified (sub-output issue 1 option D)"
  close: "verify option D in sim/checks/bridge_spice.py; fix LN-M03 (LF-1: via-in-pad or stub <= 0.3 mm long, >= 0.3 mm wide at R21 pad 2) and re-run"
- id: DBG-6
  t: "ROM DFU: AN2606 'VDDUSB must be 3.3 V' vs +3V0 2.955-3.045 V; DS13737 fn 1: functional, degraded electricals below 3.0 V (sub-dock-usb issue 6)"
  close: "bring-up steps 3 + 6 incl. 2.95 V on TP4"
- id: DBG-8
  t: "ROM DFU pauses charging (PA2 USART2_TX drives TS high)"
  close: "boot stub leaves U3 known; check step 6 with a cell"
- id: DBG-9
  t: "R20 current rating unknown (sub-power issue 6); never feed TP4 with R20 fitted (back-drives U4 output; TI behaviour unsourced)"
- id: DBG-10
  t: "stale round-1 SWD scheme (1x5 header, front-edge column, lid-screw charging) in hw/mech/notes/electronics.md §A, docs/research/pcb-mech-interface.md §7-§8, docs/build/hardware.md §7"
- id: DBG-11
  t: "no test-access map (TPs, dots, probe points, lift links, both faces) or bring-up flow PNG; board-map-revF.png covers part"
- id: DBG-12
  t: "ECR-0009 (no output while VBUS) blocks docked ZSWEEP and PWMAB"
  options: "a rec: capped self-test-only exemption in ECR-0009 (drive <= ~-12 dBFS; covers ECR-0005, U4 heating) / b run on battery, log, read back over USB"
  same_as: "sub-output issue 12, sub-power issue 5; FWSIM-R59/R61 implement both"
- id: DBG-13
  t: "Phase 2 (O20 size, ECR-0015 SIZ-01/02, ASM-09 'every post-bond hand pad on B') moves TP row, R1 PH3 pad and J pads; conflicts with FWSIM HWC-2 'R1 PH3 pad on F'; O18: each removal stated"
- id: DBG-14
  t: "SWCLK->TP2 unrouted in Rev F draft (~10 mm, drc.json 2026-10-02T20:07)"
  close: "layout session (O14); AP-DFU1 does not need it"
- id: DBG-15
  t: "Rev F J-pad map: J5 VBAT neighbours J4 GND (0.6 mm) and J12 CC (exposed dock contact, diagonal ~0.9 mm); ASM-09 removed J3-J5 but a VBAT-to-exposed-contact bridge is still one smear (J5-J12)"
  close: "reg-board pad order in layout session; bring-up step 1 meters both"
```

## Before changing this, check
```yaml
tp_pads: "P50 pitch; 0.6 mm clamp band (reg-board, reg-pod-body); jig/frame (DBG-3); right pod 180° (physical); DBG-2 order"
r1_boot0: "AP-DFU1 tack point must stay reachable (HWC-2); RM0456 Table 25; AN2606 Table 199"
pa10_pb15: "ROM states keep leg B off (table above); R5/R6 stay"
dots: "TP7 printf (HWC-3); TP8-TP10 = only MDF fallback (sub-audio-in issue 5)"
r20: "every +3V0 load (sub-power); USB margin; ECR-0005 peak through a 0402 jumper"
r21_r22_c22: "F4 method (sub-output issue 1); LN-M03; PA6 vs TIM1_BKIN (sub-processing issue 6)"
removal: "O18: state and justify"
tools: "python3 tools/plm.py impact SUB-DEBUG-TEST; python3 tools/checks/interfaces.py; integration-map.md §10"
```
