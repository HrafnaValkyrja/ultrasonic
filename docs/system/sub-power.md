# Power: cell, charger, power path, LDO, rails (item SUB-POWER)
Rev MZ-2 2026-10-07: Phase-2 package set (ECR-0018): RT1 0201, R8/R9/R12/R13/R15/R16 0201, C19 0201, D4 PMEG3005EL SOD-882; every part on B of the 30 x 12 board; +3V0 is the In2 plane (U4 -> bridge 40 mohm, was ~200); cell on 0.25 VHB 1.4 mm under the hanging board; Rev F/G facts -> "Reference design" at the end.
Status: schematic = Rev G nets with the MZ-2 packages (`POD_PACKAGES=mz2 python3 hw/pod/gen.py` -> `hw/pod/pod_mz2.net`, `hw/pod/bom_jlc_mz2.csv`; bom_check [nets] PASS 195 pins / 42 nets, 2026-10-07). Board `hw/pod/draft_r2/out/routed.kicad_pcb` (commit f6291e6): DRC 0, 0 unconnected (ECR-0018 log 2026-10-07); layout-noise valid on it (`sim/noise/out_r2/budget.json`, sha da4e8b13). Charger firmware not written. Updated 2026-10-07.

```yaml
abbrev: {CC/CV: constant-current / constant-voltage charge, ICHG: charge current, ILIM: input current limit, BUVLO: battery undervoltage lockout,
  VINDPM: input-voltage regulation threshold, JEITA: battery-industry temperature rule set (cut/stop charge when cold or hot), PCM: protection circuit module inside the cell,
  TS: U3 thermistor input (TS/MR = thermistor + manual-reset button input), SOC: state of charge, DFU: USB firmware update via the ST ROM loader,
  VHB: 3M VHB 4914 acrylic foam tape, MZ-2: Phase-2 package set (ECR-0018), F/B: board face to the lid / to the cell,
  LN-*/LF-*: layout-noise metrics/findings (docs/sim/layout-noise.yaml), PWR-I#: open issue in this doc}
item: SUB-POWER
src_of_truth: [hw/current.yaml (design pointer), "hw/pod/gen.py (blocks CHARGER, LDO, VBAT_SENSE, CELL_PADS; DOCK_USB for VBUS parts; MZ2 table L93)", hw/pod/draft_r2/out/routed.kicad_pcb, hw/mech/dims_r2.py CELL B_GAP, "docs/spec.md §7 D11 D12 D18"]
generated_views: ["docs/system/integration-map.md (nets/pins/blocks, authoritative)", "docs/system/rail-budget.yaml (checked by tools/checks/interfaces.py rails)"]
owner_decisions: [O1, O5, O12(c), O13, O16(1)(2), O9/O15 (R20 test link), O19 (cell replaced as it ages), O26/O27 (Phase 2, thin first)]
open_ecrs: [ECR-0005 (LDO rating), ECR-0008 (cell supply), ECR-0009 (R23 safety), "ECR-0013 (S1 done; S3 partial: C15 25 V, C21 still 10 V C19702; S2 + F1-F5 firmware open)", ECR-0018 (Phase 2, approved, implementing)]
checks: ["tools/checks/interfaces.py rails (2026-10-07: WARN +3V0 peak 326 mA > U4 300 mA [ECR-0005]; WARN VSYS peak 327 mA = 93 % of cell 2C 350 mA)", "tools/checks/interfaces.py pins (TS on PA2 hazard, ECR-0013; 2026-10-07 WARN as before)", "tools/checks/bom_check.py (2026-10-07: PASS refs/netlist/nets/jlc-bom/cost-bom; WARN stock-lock: 8 of 31 LCSC numbers without a lock row)"]
diagrams: [docs/diagrams/schematic-rev1.png (flowchart, nets == Phase 2), "board map: tools/board_map.py (defaults to hw/current.yaml)"]
```

## Purpose
```yaml
functions: {F5: charge the cell, F6: temperature-safe charge, F7: system power rail, F8: battery level, F13: charger link (power side)}   # integration-map §1
feeds: [every +3V0 load, VSYS -> R14 -> LED (F12, sub-ui)]
requirements:
  runtime: ">= 8 h per charge, target ~12 h (D18, O1)"
  charge: "as fast as the cell allows, temperature-qualified (O12c)"
  noise: "linear regulators only; MCU core SMPS is the one exception (D11)"
  off_mode: "D12 Off = MCU Stop 2"
```

## Power tree
```yaml
tree:   # nets as in integration-map §3/§5 (Phase 2 nets == Rev G)
  DOCK_VBUS: {from: J3 (dock contact), parts: [D5 ESD to GND at the contact], to: D4.A}
  VBUS: {from: D4.K (PMEG3005EL, reverse-dock block), parts: [C15 4.7 µF 25 V, R12/R13 100k/100k -> VBUS_SENSE PA1], to: U3.A2 IN}
  VSYS: {from: U3.B2 SYS, parts: [C21 10 µF], value: "4.5 V docked (SYS_REG default); ≈ VBAT - I x 55 mΩ on battery", to: [U4 IN/EN, C17, R14 -> LED_A (J7), TP6]}
  VBAT: {from: cell via J5 (cell +) / J4 (cell -, shared GND), parts: [C16 4.7 µF, R8/R9 1M/1M + C19 -> VBAT_SENSE PA4], to: U3.C2 BAT (battery FET 55 mΩ)}
  LDO_OUT: {from: U4 OUT (TPS7A2030 3.0 V), parts: [C18 1 µF], to: R20 0 Ω}
  +3V0: {from: R20, loads: [U1 VDD/VDDA/VDDSMPS/VBAT, Q1/Q2 S_P + C14 22 µF, R15/R16 I2C pull-ups, SW1, mic via PA5, TP4]}
  TS: {nodes: [U3.D1 TS/MR, PA2, RT1 (on board) OR J9 (cell NTC), never both]}
  control: {I2C2: "PB13 SCL / PB14 SDA, R15/R16 10k to +3V0, address 0x6A", CHG_INT: "U3.A1 /INT -> PA15, MCU internal pull-up (no external resistor); PB5 strapped to GND"}
modes:
  docked: "dock 5 V -> D4 -> VBUS -> U3 IN; U3 holds VSYS 4.5 V and charges the cell CC/CV to 4.2 V through its battery FET"
  battery: "U3 connects the cell to VSYS through the same FET (VSYS ≈ VBAT, 3.0-4.2 V); BUVLO cuts the cell off at 3.0 V"
  rail: "U4 makes +3V0 from VSYS; R20 joins LDO_OUT to +3V0 (lift: meter in series, or bench 3.0 V into TP4)"
  control: "MCU sets current/limits over I2C, takes /INT on PA15, reads VBAT/2 on PA4, NTC voltage on PA2; with no firmware U3 charges at 10 mA (ICHG default)"
  temperature: "one 10 kΩ NTC on TS: 38 µA bias with an adapter, compared with JEITA thresholds; on battery only TS/MR is pulsed with 60 µA as a push-button input unless EN_PUSH = 0 (register plan)"
  rom_dfu: "ROM loader drives PA2 as USART2_TX push-pull high -> TS reads 'cold' -> charging pauses during DFU (ECR-0013 F4)"
```

## Elements
```yaml
# LCSC from hw/pod/bom_jlc_mz2.csv (2026-10-07); class/stock/$ from docs/build/bom.md (JLC API; MZ-2 rows 2026-10-07T11:31Z) or as noted. Positions: board mm, routed board probe 2026-10-07, all on B unless noted
BT1: {part: "Renata ICP501233PA-02, 3.7 V Li-ion polymer pouch, 175 mAh, PCM built in, 2 x AWG 30 leads, no NTC", lcsc: "not JLC; distributor quote only (bom.md)", wiring: "hand-soldered: + to J5, - to J4"}
U3: {part: "TI BQ25180YBGR single-cell linear charger, power path, I2C, NTC/JEITA, ship mode; DSBGA-8 1.6 x 1.1 mm, 0.4 mm pitch", lcsc: C3682423 · Extended · $2.04, xy: "(19.2, 2.6) r90",
     balls: {A1: "/INT (19.0, 3.2)", A2: "IN (19.4, 3.2)", B1: "SCL (19.0, 2.8)", B2: "SYS (19.4, 2.8)", C1: "SDA (19.0, 2.4)", C2: "BAT (19.4, 2.4)", D1: "TS/MR (19.0, 2.0)", D2: "GND (19.4, 2.0)"}}
U4: {part: "TI TPS7A2030PDQNR 300 mA ultra-low-noise 3.0 V LDO, X2SON-4 1 x 1 mm, active output discharge", lcsc: C5220164 · Extended · $0.22, xy: "(23.0, 8.0)", pins: {1: OUT, 2: GND, 3: EN, 4: IN, 5: EP}, note: "IN and EN both on VSYS"}
RT1: {part: "Murata NCP03XH103F05RL 10 kΩ B3435 NTC 0201 (same XH family/B as the Rev G NCP15XH103)", lcsc: "C98098 · Extended · stock 175,122 · $0.0166 (bom.md, 2026-10-07T11:31Z)", xy: "(17.4, 2.7)", note: "fitted by default; measures BOARD temperature 1.8 mm (centres) from U3, not the cell (PWR-I4)"}
J9: {part: "1.0 mm wire pad (TS)", xy: "(28.9, 3.3)", note: "optional NTC taped to the cell, other lead to GND; if used RT1 is not fitted"}
J5: {part: "1.0 mm wire pad, VBAT (cell +)", xy: "(28.9, 1.1)"}
J4: {part: "1.0 x 2.0 mm wire pad pod:WirePad_1.0x2.0mm, GND = dock GND + cell -", xy: "(27.0, 1.9), long axis along y", note: "between J3 DOCK_VBUS (25.1, 1.7) and J5 VBAT (ASM-09, restored 2026-10-07 20bd842; J3-J5 2.85 mm; J4-J5 0.90 = cell short if bridged, PCM-limited)"}
R20: {part: "0 Ω 0402 link LDO_OUT -> +3V0 (kept 0402 as a hand hook, gen.py MZ2 comment)", lcsc: C17168 · Basic, xy: "(23.0, 11.0)", note: "test hook (O9/O15); carries every +3V0 mA, bridge peaks included (PWR-I6)"}
R8_R9_C19: {part: "1 MΩ / 1 MΩ divider 0201 + 100 nF 0201", lcsc: "C473482 (R8/R9), C76934 (C19)", xy: "R9 (15.4, 1.0), R8 (15.4, 1.85), C19 (15.4, 2.7)", note: "VBAT/2 -> PA4; always connected, 2.1 µA at 4.2 V"}
R15_R16: {part: "10 kΩ 0201 pull-ups to +3V0 on I2C_SCL / I2C_SDA", lcsc: C473048, xy: "R15 (17.4, 1.0), R16 (17.4, 1.85)", src: "TI asks 10 kΩ on SCL/SDA (SLUSE99C Table 6-1)"}
C16: {val: "4.7 µF 10 V X5R 0402 (VBAT)", lcsc: C23733 · Basic, xy: "(20.9, 2.3), VBAT pad 1.0 mm from ball C2"}
C21: {val: "10 µF 10 V X5R 0603 (VSYS)", lcsc: C19702 · Basic, xy: "(20.2, 0.9)", note: "TI recommends 25 V on IN/SYS (SLUSE99C 9.2.2.1); derated value must stay > 1 µF (CSYS 1/10/100 µF min/nom/max, Table 9-2); still 10 V (PWR-I14)"}
C17_C18: {val: "1 µF 25 V X5R 0402, LDO in / out", lcsc: C52923 · Basic, xy: "C17 (23.0, 9.6), C18 (23.0, 6.5) beside U4 OUT pin 1", note: "C18 must stay at U4 for stability"}
C15: {val: "4.7 µF 25 V X5R 0402 Murata GRM155R61E475ME15D, VBUS at U3 IN (block DOCK_USB)", lcsc: "C2858031 · Extended · $0.0833 (bom.md, JLC API 2026-10-02T23:50Z)", xy: "(20.9, 3.4), VBUS pad 1.0 mm from ball A2", note: "<= 10 µF USB attach limit; 25 V per SLUSE99C 9.2.2.1 (ECR-0013 S3)"}
D5: {part: "TI TPD1E10B06DPYR bidirectional ESD, 5.5 V working, X1SON-2, DOCK_VBUS to GND near J3 (block DOCK_USB)", lcsc: "C48260 · $0.0417 (bom.md)", xy: "(25.0, 3.5)", owner_doc: sub-dock-usb}
D4: {part: "Nexperia PMEG3005EL 30 V 0.5 A Schottky, SOD-882 (DFN1006-2), DOCK_VBUS -> VBUS (block DOCK_USB)", lcsc: "C282565 · Extended · stock 43,342 · $0.115 (bom.md, 2026-10-07T11:31Z)", xy: "(22.9, 1.0)", owner_doc: sub-dock-usb,
     thermal: "VF ~0.36 V at the ~0.2 A docked load -> ~0.07 W -> +36 K (500 K/W) -> Tj ~71 °C at 35 °C inside the pod, max 150 °C: PASS (ECR-0018 MZV-06, Nexperia data sheet read 2026-10-03)"}
```

## Interfaces
```yaml
- to: sub-dock-usb   # relation R-PWR-DOCK
  nets: "DOCK_VBUS (J3, D5, D4.A); VBUS (D4.K, C15, R12, U3.A2 IN)"
  crosses: "5 V minus D4 drop (PMEG3005EL VF 295 / 430 mV typ at 100 / 500 mA, ~0.36 V at ~0.2 A, ECR-0018 MZV-06); U3 runs from VIN 3.0-5.5 V (VIN_OP; datasheet also states 3.0-5.9 V and 2.7-5.5 V, audit row h), OVP 5.7 V typ; ILIM 500 mA default; ESD clamped at the contact by D5, D4 stays the reverse block"
  src: "integration-map §1 F5/F15, §5; SLUSE99C §7.5"
- to: sub-processing   # relation R-PWR-PROC
  nets: "+3V0 -> U1 VDD/VDDA/VDDSMPS/VBAT(pin 1); I2C_SCL PB13 <-> U3.B1; I2C_SDA PB14 <-> U3.C1; CHG_INT PA15 <- U3.A1; TS PA2 <-> U3.D1; VBAT_SENSE PA4"
  invariants:
    - "I2C2, address 0x6A"
    - "/INT is a 128 µs low pulse (EXTI); PA15 needs its INTERNAL pull-up enabled by firmware (no R17 since Rev F)"
    - "PB5 tied to GND: keeps the UCPD dead-battery 5.1 kΩ pull-down off PA15; firmware also sets PWR_UCPDR.UCPD_DBDIS early (ECR-0013 S1, pin-contract.yaml hazards)"
    - "PA4 = ADC4 (works in Stop 2); PA4 < VDDA (VBATREG max 4.65 V -> 2.33 V)"
    - "PA2 MUST stay an analog input: TS held < 90 mV for ~10 s = ship-mode request (fires on release; PWR-reg plan disarms it)"
  src: "integration-map §1 F8/F13, §3; pin-contract.yaml; ECR-0013"
- to: sub-output   # relation R-PWR-OUT-RAIL
  nets: "+3V0 -> Q1/Q2 S_P, C14 22 µF"
  crosses: "+3V0 peak 326 mA at full drive into 8 Ω (tools/checks/interfaces.py rails, 2026-10-07; of it the exciter/bridge peak is 315 mA, gen.py R21 comment, sub-output 0.32-0.33 A) vs U4 300 mA rating, 360 mA min current limit: ECR-0005"
  copper: "+3V0 = In2 plane (281.8 mm², one island) + 15.7 mm of 0.15 mm B/F track + 24 vias (board probe 2026-10-07): U4.1 -> Q1.4 40.4 mΩ, -> Q2.4 39.5 mΩ, -> U1.25 42.8 mΩ: ~13 mV drop at 0.32 A (derived)"
  ripple: "LN-M05 bridge rail ripple x 10 % leg asymmetry 8.72 µV rms <= 50 PASS (A05 CPU hop 1562 Hz)"
  src: "sim/noise/out_r2/budget.json (board sha da4e8b13 = routed.kicad_pcb at f6291e6, 2026-10-07) keys dc_rail_paths_mohm, planes, metrics"
- to: sub-audio-in
  nets: "+3V0 -> PA5 -> MIC_VDD"
  crosses: "mic 1.1-2.15 mA (sim/checks/power.py); rail noise reaches the mic directly -> U4 is the 7 µVrms part; LN-M01 mic-supply spur margin 26.5 dB pessimistic (nominal 46.5, worst 14.0) PASS on the Phase-2 board (budget.json 2026-10-07); U4.1 -> mic path U1.15 -> U2.5 82.5 mΩ"
- to: sub-ui   # relation R-PWR-UI
  nets: "VSYS -> R14 2k2 -> LED_A (J7); SW1 pins 1/2 on +3V0"
  crosses: "LED 0.14-0.73 mA on battery (VSYS 3.0-4.2 V), 0.82-0.86 mA docked (4.5 V), VF 2.6-2.7 V (sub-ui key numbers); SW1 pressed 3.0 V / 2.2 kΩ ≈ 1.4 mA"
- to: sub-debug-test   # relation R-PWR-DEBUG
  nets: "TP4 +3V0, TP5 GND, TP6 VSYS; R20"
  crosses: "lift R20: meter the rail or inject 3.0 V on TP4"
- to: reg-board   # relation R-PWR-BOARD; routed board probe 2026-10-07 (hw/pod/draft_r2/out/routed.kicad_pcb), all on B
  charger: {U3: "(19.2, 2.6) r90; balls column x 19.0 = /INT SCL SDA TS, x 19.4 = IN SYS BAT GND (y 3.2 -> 2.0)", C15: "(20.9, 3.4) east of A2 IN", C16: "(20.9, 2.3) east of C2 BAT", C21: "(20.2, 0.9) VSYS", RT1: "(17.4, 2.7)", R15_R16: "(17.4, 1.0 / 1.85)", R12_R13: "(17.4, 4.4 / 3.55)", R8_R9_C19: "x 15.4, y 1.85 / 1.0 / 2.7"}
  ldo: {U4: "(23.0, 8.0)", C17: "(23.0, 9.6)", C18: "(23.0, 6.5)", R20: "(23.0, 11.0)"}
  dock_side: {D4: "(22.9, 1.0)", D5: "(25.0, 3.5)", R14: "(25.0, 8.3)"}
  pads_B: {J3: "(25.1, 1.7) DOCK_VBUS", J4: "(27.0, 1.9) 1.0 x 2.0 GND", J5: "(28.9, 1.1) VBAT", J9: "(28.9, 3.3) TS"}
  pads_F: {TP4: "(3.1, 11.3) +3V0", TP6: "(24.0, 10.9) VSYS"}
  rule: "U3 0.4 mm DSBGA: no track between balls, every ball escapes outward (reg-board)"
  routing: "all power nets routed; DRC 0, 0 unconnected (ECR-0018 log 2026-10-07); wire-pad copper gaps >= 0.90 mm (MZD-10 >= 0.8 holds); J4 GND between J3 and J5 (ASM-09, PWR-I17 closed 2026-10-07)"
- to: reg-pod-body / physical   # relation R-PWR-BODY
  envelope: "cell x 30.6-65.6, y 5.4-10.7, z -8.1..3.9 (dims_r2.CELL, pod mm), on 0.25 VHB in a 0.3 gap on the inner wall; board B face 1.4 mm above it (dims_r2 B_GAP, Y_B 12.1)"
  notes: ["the board hangs from the lid on VHB: no foam strips, nothing presses on the cell (reg-pod-body)",
          "B parts (tallest U2 1.08, interfaces.py heights 2026-10-07) face the cell across the 1.4 mm gap: U3 heats the pouch through 1.4 mm of air (PWR-I12)",
          "dock target sits directly below the cell in the belly (dims_r2.DOCK z -11.75..-8.95; sub-dock-usb)",
          "O19: the cell is a service part, but VHB is permanent (physical, Service)", "cell leads: + on J5, - on J4 together with the dock GND wire"]
- to: firmware (sub-processing)
  needs: "I2C2 driver, EXTI PA15 (internal pull-up), ADC4 PA4, ADC PA2 (TS only meaningful while docked, SLUSE99C Table 8-6), register plan below"
  sim: "docs/sim/firmware-emulation.yaml charger_plan, FWSIM-R20, FWSIM-R62"
```

## Constraints
```yaml
D11: "U3 and U4 both linear: nothing in this subsystem switches"
D12: "Off = MCU Stop 2"
D18_O1: ">= 8 h, ~12 h target"
spec_§7_rail: "bridge on the regulated 3.0 V rail (gain does not track charge)"
O16: "Renata 175 mAh cell + BQ25180 are owner choices"
O12c: "fastest practical charge, temperature-qualified"
O13: "board may grow a little for charging"
cell:   # Renata spec Rev V03 08/2019, fetched 2026-10-01 (SHA-256 prefix c3bb2ebe9c1d78af)
  charge: "CC/CV to 4.2 V; normal 0.5C = 87.5 mA; max 1C = 175 mA"
  charge_temp: "0-45 °C only"
  cutoff: 3.0 V
  discharge: "175 mA continuous, 350 mA (2C) pulses"
  storage: "-20..45 °C (0-30 °C beyond 3 months)"
ichg_step: "above 35 mA ICHG moves in 10 mA steps (SLUSE99C §8.5.1.5): '1C' = 170 mA (180 mA exceeds 1C)"
ts_rule: "RT1 OR J9, never both: two 10 kΩ NTCs in parallel = 5 kΩ x 38 µA = 0.19 V = U3's 45 °C warm entry (0.185 V): room temperature reads warm"
U4: "input 1.6-6.0 V (VSYS <= 4.9 V by design); output 3.0 V ± 1.5 %; rated 300 mA"
```

## Key numbers
```yaml
cell: {cap: "175 nom (170 min) mAh", size: "<= 5.3 x 12 x 35 mm", mass: "~4.2 g", R: "< 480 mΩ at 30 % SOC", src: "Renata V03 08/2019, fetched 2026-10-01"}
charge_current: {val: "170 mA (20-45 °C), 50 mA below 20 °C (firmware rule)", src: "gen.py U3 comment, adjusted to U3 10 mA steps; ICHG codes 44/32 confirmed audit row g (2026-10-02)"}
U3_defaults: {val: "ICHG 10 mA, VBATREG 4.20 V, BUVLO 3.0 V, ILIM 500 mA, SYS 4.5 V, safety timer 6 h, VINDPM disabled, WATCHDOG_SEL 00 (160 s register revert, armed after the first I2C transaction)", src: "SLUSE99C Rev C Jan 2023 §8.5.1 p.32-38; audit-datasheet-claims.md rows 3, 4, g (2026-10-02)"}
U3_TS: {val: "0 / 10 / 45 / 60 °C (cold / cool = ½ ICHG / warm = -100 mV / hot); bias 38 µA with adapter, 60 µA pulsed 4 ms / 196 ms on battery only; VTSMR 90 mV", src: "SLUSE99C §7.5, §8.5.1.12 (2026-10-01; audit row g)"}
U3_fet_iq: {val: "battery FET 55 mΩ typ (90 max); battery-only Iq 3 / 3.5 µA (watchdog and push-button disabled), 4 / 5 µA (push-button on); ship 3.2 µA; shutdown 15 nA; Iq with watchdog enabled not tabulated", src: "SLUSE99C §7.5 p.6 IQ_BAT; audit row e"}
U3_thermal: {val: "θJA 107 °C/W (JEDEC), 65 °C/W (TI EVM); thermal regulation 100 °C; dissipation ~0.3 W at start of CC (~+31 °C die rise), ~0.2 W mid-charge", src: "SLUSE99C §7.3, §8.5.1.6; audit 2026-10-02; ECR-0013 SAFETY"}
U4_out: {val: "3.0 V ± 1.5 % (2.955-3.045 V) over 1-300 mA, line, temperature", src: "TPS7A20 SBVS338H (Jul 2024) §5.5; local copy tps7a20.pdf 663a9ff5bca60864 (datasheet-provenance.md)"}
U4_limits: {val: "dropout <= 140 mV at 300 mA; current limit 360 / 520 / 730 mA; short-circuit 160 mA", src: "SBVS338H §5.5"}
U4_noise_iq: {val: "7 µVrms; PSRR 95 dB at 1 kHz, 75 dB at 100 kHz; Iq 6.5 µA typ (8.5 max at 25 °C); θJA 166 °C/W", src: "SBVS338H §5.4-5.5"}
bridge_peak: {val: "~315 mA exciter/bridge full-drive peak on +3V0 (3.0 V into 8 Ω + 1.2 Ω FETs + 0.1 Ω R21); the whole +3V0 peak with MCU, mic, pull-ups is 326 mA (rail_check)", src: "gen.py R21 comment; rail-budget.yaml exciter row (peak_ma 315); interfaces.py rails 2026-10-02"}
rail_check: {val: "+3V0 declared peak 326 mA vs U4 300 mA (WARN, waived by ECR-0005); VSYS peak 327 mA = 93 % of cell 2C 350 mA", src: "tools/checks/interfaces.py rails, run 2026-10-07 (unchanged by MZ-2: same parts on +3V0)"}
pullups: {val: "I2C R15/R16: 0.60 mA with both lines low (2 x 3.0 V / 10 kΩ); idle high = 0", src: "rail-budget.yaml (computed)"}
vbat_sense: {val: "VBAT/2 = 1.5-2.1 V at PA4; divider 2.1 µA; τ = 50 ms", src: "gen.py R8/R9/C19 (derived)"}
rail_hold: {val: "+3V0 at U4 holds at a 315 mA peak while VBAT >= ~3.32 V (3.0 + 0.14 dropout + 0.315 x (0.48 + 0.09)); at the bridge sources a further ~13 mV plane/copper drop (40 mΩ)", src: "derived: Renata + SLUSE99C + SBVS338H; sim/noise/out_r2/budget.json dc_rail_paths_mohm (2026-10-07)"}
```

### Rails
```yaml
VBUS: {source: "dock via D4", range: "5 V - D4 drop [TBD at ~0.2 A]", loads: [U3 IN, R12/R13 (25 µA), C15]}
DOCK_VBUS: {source: J3 contact, loads: [D5 (leakage only), D4]}
VSYS: {source: U3 SYS, range: "4.5 V docked; ≈ VBAT - I x 55 mΩ on battery (3.0-4.2 V)", loads: [U4 IN/EN, C17, R14 LED, TP6]}
VBAT: {source: "cell <-> U3 BAT", range: 3.0-4.2 V, loads: [U3, R8/R9, C16]}
+3V0: {source: "U4 via R20", range: 2.955-3.045 V, loads: [MCU, mic (PA5), bridge, R15/R16, SW1, TP4]}
VDD11_MIC_VDD: "see sub-processing / sub-audio-in"
```

### Power budget and runtime
```yaml
model: "sim/checks/power.py rev 2 = spec §7 v0.14 (l.405-417); spec l.365 table is the older v0.6 budget"
full_chain_awake_mA: [5.0, 6.8, 9.8]   # low / nominal / high
idle_detector_mA: [1.7, 2.2, 3.4]
not_in_model: {LED: "0.14-0.73 mA battery, 0.82-0.86 mA docked (O8; sub-ui)", U3_battery_iq: "3-5 µA", SW1_pressed: 1.4 mA}
runtime_175mAh_h:   # same model at 175 mAh, run 2026-10-01 (no file written); LED 0.55 mA nominal / 0.75 mA pessimistic (conservative); pessimistic .. nominal
  awake_100pct: {no_led: "13.4 .. 22.0", led: "12.5 .. 20.3"}
  awake_50pct: {no_led: "19.9 .. 33.2", led: "17.8 .. 29.6"}
  awake_18pct_quiet_room: {no_led: "28.7 .. 49.2", led: "24.6 .. 41.7"}
verdict: "175 mAh meets 12 h even never idling with the LED on (105 mAh gave 8.0 h in that case)"
mz2_effect: "none on averages: same circuit, smaller packages (gen.py MZ2: nets untouched)"
```

### Charge time, Off, storage
```yaml
charge_1C: "CC >= 1.0 h (175 mAh / 170 mA) + CV taper to 17 mA termination; total [TBD bench]; <20 °C (50 mA) >= 3.5 h; <10 °C U3 halves again (>= 7 h) > 6 h safety timer unless 2XTMR_EN; spec §7 l.386 '2.5-3 h at <= 0.5C, MCP73831' is obsolete"
off_D12:
  parts_uA: {MCU: "3.9-8.55 (A3 §5)", U4: "6.5-8.5", U3: "3-3.5 with EN_PUSH 0 and watchdog off; watchdog-on (option B) figure [TBD measure]", divider: 2.1}
  total_uA: "≈ 15.5-22.7 (derived) -> ~274-400 days on 85 % of 175 mAh"
  hazard: "ECR-0013 F5: PB3/PB4 back-feed the PA5-gated mic ~60 µA unless firmware sets them analog/no-pull before Off; in reset / ROM DFU firmware cannot"
  hazard_2: "watchdog option B power-cycles an Off pod unless an RTC wake talks I2C < 160 s (audit row 3)"
storage_proposed: "U3 shutdown (EN_RST_SHIP = 01): SYS off, wakes only when docked; VBAT divider 2.1 µA is the only drain (cell side of the battery FET). Not decided. Ship-mode button wake doesn't help: SW1 is on PA0, not TS/MR"
```

### Charger register plan (proposed from SLUSE99C; firmware not written; mirror: docs/sim/firmware-emulation.yaml charger_plan)
```yaml
ICHG_CTRL_0x4: {default: 10 mA, set: "code 44 = 170 mA at 20-45 °C; code 32 = 50 mA below 20 °C; only after enumeration / known cable (ECR-0013 F1)", why: "cell 1C max; 20 °C rule from gen.py; TS read on PA2 while docked"}
TS_CONTROL_0xB_TS_HOT: {default: 60 °C, set: "45 °C (2b11)", why: "cell charges only at 0-45 °C: the default is UNSAFE for this cell"}
TMR_ILIM_ILIM: {default: 500 mA, set: "100 mA until USB enumeration, then the 500 mA default (ECR-0013 F1; Rev F: no CC sense, R19 removed)", why: "USB 2.0 unconfigured port = 100 mA (PWR-I13)"}
CHARGECTRL0_VINDPM: {default: disabled, set: 4.2 V, src: "ECR-0013 F1; audit row 4"}
IC_CTRL_0x7_WATCHDOG_SEL: {default: "00 (160 s register revert; also restores TS_HOT 60 °C)", set: "01 (HW reset after 160 s without I2C) + RTC keep-alive from Stop 2; boot stub writes 11 before ROM DFU, the application re-arms 01", src: "triage Q23 2026-10-02 (owner sees it in the safety packet, Q22); PWR-I3"}
IC_CTRL_2XTMR_EN: {default: 0, set: 1, why: "cold, slow charges must not hit the 6 h safety timer"}
keep: {VBAT_CTRL: "4.20 V", BUVLO: 3.0 V, SYS_REG: 4.5 V, why: "match the cell (4.2 V CV, 3.0 V cut-off); SYS_REG 000 battery tracking is NOT a U3 heat lever (audit 2026-10-02)", knob: "VBATREG 4.10-4.15 V option: firmware-emulation.yaml / docs/research/tws-power-size.md"}
MASK_ID_PG_INT_MASK: {default: "0 (enabled)", set: keep, why: "docking pulses CHG_INT and wakes the MCU from Stop 2 to write this plan"}
SHIP_RST_0x9_EN_PUSH: {default: "1 (TS/MR push-button on battery only, 60 µA pulsed)", set: 0, why: "no button on TS/MR"}
SHIP_RST_0x9_PB_LPRESS_ACTION: {default: "10 = ship mode after MR_LPRESS (10 s) hold, fires on RELEASE", set: "00", why: "EN_PUSH gates only battery mode; the push-button input is also live while charging (SLUSE99C Table 8-6). Paths it closes: a J9 solder bridge to a pad that holds TS low (Phase 2, routed board 2026-10-07: J9 (28.9, 3.3) neighbours J12 CC 1.17 mm (R18 5k1 || RT1 = 3.4 kΩ: 128 mV at 38 µA, 203 mV at 60 µA = reads hot, stays above 90 mV, derived) and J5 VBAT 1.20 mm (pulls TS high = 'cold')), PA2 driven low, NTC above ~84 °C (1.5 kΩ x 60 µA = 90 mV, derived)", src: "ECR-0013 F2; audit row 1 corrections A/B"}
write_when: "at boot and on every power-good interrupt; read back and verify (bench); re-assert after watchdog revert / HW reset (FWSIM-R20)"
```

## Open issues
```yaml
# ids stable (referenced from rail-budget.yaml, firmware-emulation.yaml, triage); I8 and I11 closed by Rev F; I16 (+3V0 0.1 mm trunk) closed by the Phase-2 In2 +3V0 plane (40 mΩ, budget.json 2026-10-07)
PWR-I1: {what: "U4 300 mA rating vs the 326 mA +3V0 peak (315 mA of it the bridge; below the 360 mA min current limit, outside rated/dropout range; interfaces.py rails 2026-10-07)", note: "12 Ω exciter (3.0 / 13.3 Ω ≈ 226 mA) removes it; 8 Ω doesn't", closes: "E1 (exciter R) + ECR-0005"}
PWR-I2: {what: "charger defaults unsafe/useless for this cell: TS_HOT 60 °C vs 45 °C; ICHG 10 mA can't fill inside the 6 h timer (fault)", closes: "firmware writes the register plan; bench read-back"}
PWR-I3: {what: "U3 watchdog policy", status: "default B decided by triage Q23 (01 + RTC keep-alive; boot stub sets 11 before ROM DFU; app re-arms); owner sees it in the safety packet (Q22)",
         alternatives: {A: "11 disabled: simple, U3 never self-resets; adopt only if WATCHDOG_15S_ENABLE still works with SEL=11 or the IWDG runs in Stop with RTC kicks", C: "00 default: restores TS_HOT 60 °C after a firmware hang: don't"},
         risk: "B kills a ROM DFU idle > 160 s since the last I2C access unless the stub writes 11 first; B fires in Off without RTC wakes"}
PWR-I4: {what: "RT1 1.8 mm (centres) from U3 on the Phase-2 board (Rev F 3.1) (~0.3 W at start of CC, ~+31 °C die rise at 107 °C/W): RT1 reads hot (errs safe, may stop 1C on warm days); plan on 0.3 W and taper ICHG at low VBAT", closes: "log TS vs a cell thermocouple during a 1C charge", levers: [move RT1 (reg-board), J9]}
PWR-I5: {what: "self-test while docked heats U4: VSYS 4.5 V -> ~1.5 V x bridge current across U4 (166 °C/W) during a full-scale |Z| sweep (F4 over USB); ECR-0009 'no exciter output while VBUS present' forbids it as written",
         closes: "owner's ECR-0009 decision (sub-output issue 12): capped self-test exemption (<= ~-12 dBFS) recommended; or SYS_MODE = 01 during the sweep; or sweep on battery and read back"}
PWR-I6: {what: "R20 0402 0 Ω carries the whole rail incl. peaks; jumper current rating not in any source", closes: "read the Uni-Royal 0402 jumper rating [TBD]"}
PWR-I7: {what: "+3V0 can be 2.955 V, 45 mV under VDDUSB 3.0 V 'USB used' min; DS13737 Rev 10 Table 150 fn 1: USB functional down to 2.7 V with degraded electricals", action: "no LDO change; bench enumeration + full DFU at 2.95 V (sub-dock-usb issue 6)", src: "audit row 6"}
PWR-I9: {what: "missing research note: spec O12 cites docs/research/battery-and-charging.md (absent); BQ25180 SLUSE99C (SHA-256 prefix c2008f613723fec3) and Renata V03 (c3bb2ebe9c1d78af) are not in datasheet-provenance.md", closes: "add both rows to datasheet-provenance.md", status: "rows added 2026-10-07 (datasheet-provenance.md Phase-2 section); battery-and-charging.md still absent"}
PWR-I10: {unknown: [Renata price (quote only), cell lead/PCM exit position, cell self-discharge, D4 forward drop at ~0.2 A, real charge time, "E4 currents (budget is Low-confidence until then)"]}
PWR-I12: {what: "R23 thermal placement: U3 (~0.3 W at start of CC) on the B face, 1.4 mm of air above a pouch (dims_r2 B_GAP) that charges only at 0-45 °C, RT1 beside it; moving U3 or changing the stack-up changes cell temperature during charge", closes: "ECR-0009 item 3 (board + cell temperature logged through a full charge before any wear)"}
PWR-I13: {what: "ILIM vs dock cable: CC-less USB-A cable on an unenumerated PC port = 100 mA (USB 2.0); Rev F has no CC sense", closes: "firmware holds ILIM 100 mA until enumeration (register plan; sub-dock-usb issue 9; FI-11)"}
PWR-I14: {what: "C21 (VSYS) is a 10 V part; TI recommends 25 V on SYS (SLUSE99C 9.2.2.1); derated value must stay > 1 µF", status: "still 10 V in MZ-2 (bom_jlc_mz2.csv C21 = C19702, 2026-10-07; only C15 moved to 25 V); ECR-0013 S3 text names C17 too, but C17 is already 25 V (sourcing-lock.csv C52923)", closes: "DC-bias check of C19702 at 4.5 V (Samsung curves, layout-noise UN-7) or 16/25 V Basic swap"}
PWR-I15: {what: "Off-mode current hazards: PB3/PB4 mic back-feed ~60 µA (ECR-0013 F5); watchdog-on Iq untabulated (audit row e)", closes: "firmware Off sequence + bench Off-current measurement"}
PWR-I18: {what: "R23 I_SENSE offset (OUT-1B, built 2026-10-07): +3V0 stays up in Off, so its path (+3V0 -> R23 -> R22 -> R21 -> GND) always conducts; 100k drew 29.7 uA (more than the 16.5-24 uA Off budget), so R23 = 1M: 3.0 uA, +3.0 mV offset", closes: "done (value); if Off current ever needs the last 3 uA: GPIO-driven offset on PA3 at the next placement round"}
PWR-I17: {status: "CLOSED 2026-10-07 (20bd842): J3/J4 swapped; J3 (25.1, 1.7), J4 (27.0, 1.9) between J3 and J5; J3-J5 2.85 mm, J3-J4 0.90, J4-J5 0.90; place_r2 check NOT_NEIGHBOURS J3-J5 >= 2.0", what: "(was) J3 DOCK_VBUS and J5 VBAT are direct neighbours (copper gap 1.17 mm, routed board 2026-10-07): a bridge puts dock 5 V straight on the cell, bypassing U3 CC/CV (PCM over-charge cut-off is the only limit). Rev F kept J4 GND between them (ASM-09); MZD-10 checks gaps >= 0.8 mm, not this pairing. Other dock-side pairs: J3-J4 0.90 (dock 5 V to GND), J3-J12 1.20", closes: "swap pads so J4 (or a harmless net) separates J3 and J5 (layout item, owner review O25), or accept with a bring-up meter check (sub-debug-test step 1)"}
```

## Before you change this, check
```yaml
charge_current_or_cell: [Renata 1C limit, U3 10 mA steps, safety timer, U3 heat -> RT1, runtime table, 2C peak vs bridge peaks (sub-output)]
U4_or_3V0_value: [VDDUSB (sub-dock-usb), mic supply limits (sub-audio-in), bridge gain + peak (sub-output), D11, ECR-0005]
NTC: [never RT1 and J9 together, PA2 analog-only]
CHG_INT: [firmware enables the PA15 internal pull-up, PB5 stays tied to GND]
U3_cluster_moves (reg-board): [0.4 mm ball escape, RT1 distance to U3 (PWR-I4), C15 beside A2 / C16 beside C2, I2C_SCL already routes through In2 (ECR-0018 log 2026-10-07)]
VBAT_SENSE: "PA4 < VDDA (VBATREG max 4.65 V -> 2.33 V OK)"
VSYS_loads: [LED brightens docked (sub-ui), U4 input <= 6 V]
cell_envelope_or_pads: [reg-pod-body, physical, B_GAP 1.4 vs B part heights, dock target under the cell (sub-dock-usb), J3-J5 kept apart by J4 (ASM-09, PWR-I17 closed), wire-pad gaps >= 0.8 mm (MZD-10)]
always: "walk the change through integration-map.md §10 and python3 tools/plm.py impact SUB-POWER"
```

## Reference design (Rev F/G)
```yaml
# hw/current.yaml `reference` (env ULTRASONIC_DESIGN=revg): hw/pod/draft_r1/pod_r1_routed.kicad_pcb, hw/pod/pod.net, hw/pod/bom_jlc.csv; history = git
packages: {RT1: "NCP15XH103F03RC 0402 C77131", D4: "1N5819WS SOD-323 C191023", R8_R9: "0402 C26083", R15_R16: "0402 C25744", C19: "0402 C1525"}
board: "34 x 13, parts on both faces; U3 (19.5, 3.0) B, U4 (24.2, 7.4) B, wire pads J3/J4/J5/J9 on F at x 31.4 with J4 between J3 and J5 (ASM-09)"
rail_copper: "+3V0 as 0.1 mm tracks: U4.1 -> Q1.4 202.5 mΩ (~65 mV at 0.32 A), LF-2 (sim/noise smoke on sha e159bccb, 2026-10-02)"
body: "cell under foam strips that overlapped it by 0.1 mm (shell_r1)"
```
