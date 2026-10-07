# Bring-up plan (ECR-0010)

Generated from `docs/build/bringup.yaml` by `docs/build/make_bringup.py` (2026-10-07). Edit the YAML, not this file.

**How to use it.** Work top to bottom. Each step has what to do, the tools, the value our models predict (with tolerance), the pass line and what to do on a fail. Write every reading into the board's log (board 1 becomes the reference for boards 2-3). A red **gate** means: stop here until the step before it passed.

![sequence](../diagrams/bringup-sequence.png)

9 stages, 40 steps. `[A]` = assumed tolerance, refine on board 1.

## Gates (never skip)

- **G0**: stage A done before any board is powered (parts and prints known good)
- **G1**: no power until B2 (all short/continuity checks) passes
- **G2**: no 5 V dock power until C1 (current-limited cell-side power) passes
- **G3**: no lid bond (physical.md step 8) until D4 (boot stub + DFU re-flash over USB) passes: SWD is gone after the bond (DBG-16)
- **G4**: no exciter until E7 (|Z| on a resistor) and E8 (fault break) pass
- **G5**: no wear on the head until H2 (Off current) and the supervised first charge (E6) pass (ECR-0009)

## Tools

- **Have:** soldering iron + flux + fine tips (O13); oscilloscope (O13); multimeter with diode mode [A: assumed, 'etc.']; current-limited bench supply [A: assumed]; LCR meter (spec L575); Nordic PPK2 power profiler (spec L575); loupe / microscope [A]; calipers; kitchen scale (1 g); pin vise + drills 0.8/0.85/1.0; PC with USB
- **Buy with the freeze order (O21):** pin-gauge set 0.50-1.00 mm x 0.01 (RPB-16); 20G hypodermic tube (gauge-pin sleeve); USB-UART 3.3 V adapter for TP7 printf; dock cable: 5-pin YZP0048 head + USB-C plug with CC wired (DK-09); thermocouple for the charge log (PWR-I4) [A: if the multimeter has none]; SWD probe only if DFU-first fails (DBG-1 option C)
- **Software:** dfu-util (FOSS) [TBD: confirm U575 DFU support]; fw/tools/pod_test.py (FWSIM-R63); python3 sim/fw/fmac_model.py --bench (FMAC expected words)

## Stage A: Before the board: prints, parts, coupons (no electricity)

### A1. print the tolerance coupon + tub, lid, 5-puck kit; wash, cure; measure holes 0.8/0.85/1.0/1.2/1.6 and slots 0.3/0.4/0.5; dry-fit the pad cap + pad board + exciter, shim tight fits

| | |
|---|---|
| Tools | calipers, pin vise |
| Expect | printed holes close ~0.05-0.1 [A]; after reaming the D1.0 bore: 1.00-1.02 |
| Pass | bore admits a 1.00 pin, not a 1.03 |
| On fail | adjust print compensation, reprint |
| Closes | PAD-4, RB-TOL |
| Source | tolerances.md Phase-2 section; dims_r2.duct_offsets |

### A2. ream the heel exit D0.8 neck from the cavity side (straight along -y); fish a wire through the D1.0 channel

| | |
|---|---|
| Tools | pin vise 0.8 |
| Expect | outer wall 0.60 stays intact; 4 x 0.21 litz + fish pass |
| Pass | no breakthrough, fish passes both bends |
| On fail | reprint; if the neck cracks again: widen wall in heel.py (CH_EXIT) |
| Closes | ARM-1R |
| Source | notes/heel.md build order; heel.py checks |

### A3. dry-fit the real Renata ICP501233PA-02 in the printed tub; note where its leads/PCM exit

| | |
|---|---|
| Tools | calipers |
| Expect | cell 35 x 12 x <=5.3 sits on the 0.3 VHB gap; exit hole 0.20 behind the cell end, rim-corner 0.36 |
| Pass | cell flat, heel exit not covered |
| On fail | record lead exit; adjust J5/J4 route or CELL constants; re-run dock_route.py + heel.py |
| Closes | ARM-1R, PWR-I10 |
| Source | reg-arm issue 1; physical issue 10 |

### A4. dock target sample: caliper the body + tab, identify contact order and magnet keying

| | |
|---|---|
| Tools | calipers, multimeter |
| Expect | 21.2 x 6.86 x 2.8 body, 5.03 tab (LCSC drawing) |
| Pass | fits the belly window; order recorded in gen.py + sub-dock-usb |
| On fail | update dims_r2.DOCK and shell_r2 |
| Closes | DK-02, DK-03 |
| Source | sub-dock-usb DK-02/03 |

### A5. exciter E1: LCR meter R and L at 1 kHz (3+ samples, two listings)

| | |
|---|---|
| Tools | LCR meter |
| Expect | 8 or 12 ohm; L 0.3-1.3 mH (model placeholders) |
| Pass | R and L recorded; L < ~1 mH keeps 200 kHz PWM |
| On fail | L >= 1 mH: PWM-rate fallback 100 kHz (sub-output issue 2); 12 ohm clears ECR-0005 |
| Closes | ECR-0007 |
| Source | sub-output issues 2, 3 |

### A6. gauge pin kit: measure the 20G tube OD/ID and the pin gauges

| | |
|---|---|
| Tools | calipers, pin-gauge set |
| Expect | tube OD 0.88-0.92, ID 0.59-0.62 [A ISO 9626] |
| Pass | computed worst duct stack <= 0.175 (with the pin chosen to the actual board hole: ~0.12) |
| On fail | micro-turned stepped pin (RPB-16 option B) |
| Closes | RPB-16 |
| Source | reg-pod-body issue 16 |

### A7. VHB coupon: a bare FR-4 coupon on VHB to a printed lid piece; 1.6 N press (163 g on the kitchen scale) on a dummy SW1 spot; optional 600k-press rig

| | |
|---|---|
| Tools | kitchen scale |
| Expect | board deflection 1.4-20 um at 2 N (not visible); VHB 12-52 kPa vs 85 kPa design factor |
| Pass | no peel, no visible movement |
| On fail | back the switch (B back-stop) or a stiffer bond area |
| Closes | RPB-17 |
| Source | sim/checks/sw1_press_fem.py; sub-ui issue 2 |

### A8. NiTi coupons: wire 0.75/0.80/0.85 bend test at skin temperature, 100 on/off cycles; flare root under a loupe

| | |
|---|---|
| Tools | loupe, kitchen scale |
| Expect | plateau ~200 MPa [A]; force >= 0.5 N at jaw opening |
| Pass | pick the wire; no root crack after 100 cycles |
| On fail | STRUT_START 3 -> 4 mm (ARM-5) or the 0.85 wire (ARM-2 B) |
| Closes | ARM-3, ARM-4, ARM-5 |
| Source | reg-arm issues 3-5 |

### A9. body + wear: E9/E10/E12 measures on her glasses; weighted dummy pair 2 h with 11.2-13.2 g per side

| | |
|---|---|
| Tools | printed dummies, kitchen scale |
| Expect | comfortable for 2 h; temple give E12 |
| Pass | owner says yes |
| On fail | mass trims (PHYS-8D options B/C); set change ARM-2 |
| Closes | ECR-0006, ARM-2, ARM-9, Q-A-PHYSICAL-FIRSTWINS |
| Source | physical issue 8; reg-arm 2, 9 |

### A10. FMAC rounding read-back on any STM32U5 board (Nucleo-U575 if at hand, else at E10): FIR P=1, CLIPEN=1, 8 inputs

| | |
|---|---|
| Tools | U5 board, PC |
| Expect | TEST A1 under floor: 0,0,0,0,-1,-1,-1,-1; TEST A2: 0,0,1,1,-1,-1,-1,-2 (`python3 sim/fw/fmac_model.py --bench`) |
| Pass | matches floor (the firmware model) |
| On fail | change A1/A2 in fw/core/fmac_model.c + Python twin, re-run fwsim L0/L2/D17 |
| Closes | FMAC-RM-UNKNOWNS |
| Source | backlog FMAC-RM-UNKNOWNS |

## Stage B: Bare assembled board, unpowered

### B1. visual under the loupe: U3 balls, U1 QFN, Q1/Q2 (Nexperia land pattern), SW1, D5/D6, 0201 tombstones, R23 present, LED cathode mark on the pad board; mic hole clean

| | |
|---|---|
| Tools | loupe, pin gauges 0.60/0.70 |
| Expect | mic hole D0.65 press-fit: 0.60 enters, 0.70 does not |
| Pass | no bridge, no tombstone, hole in tolerance |
| On fail | photograph, rework with flux + iron or use board 2 |
| Closes | OUT-4, PAD-8 |
| Source | sub-debug-test step 0; SAI-15D |

### B2. short checks, ohms then diode mode both polarities: TP4-TP5 (+3V0-GND), TP6-TP5 (VSYS-GND), J5-J4 (VBAT-GND), J3-J4 (DOCK_VBUS-GND) and the 6 neighbour pairs J3-J4, J4-J5, J1-J2, J2-J8, J12-J9, J10-J11 (test-access-map.svg)

| | |
|---|---|
| Tools | multimeter |
| Expect | no pair < 5 ohm; J12-J9 ~15 kohm at 25 C (R18 5k1 + RT1 10k NTC, both to GND); others > 1 kohm in ohm mode, diode drops 0.3-0.8 V where a pin or body diode sits |
| Pass | no short, board 1 readings recorded as the reference for boards 2-3 |
| On fail | J4-J5 = cell short; J3-J4 = dock supply short; J12-J9 = CC on TS; J2-J8 = 200 kHz into PB7; J1-J2 = exciter shorted: find the bridge under the loupe, wick |
| Closes | RB-4 |
| Source | sub-debug-test step 1; reg-board issue 4 |

## Stage C: First power, current-limited, cell side

### C1. bench supply 3.70 V, current limit 50 mA, on J5(+)/J4(-) (cell pads); blank MCU

| | |
|---|---|
| Tools | bench supply, multimeter |
| Expect | TP6 VSYS ~3.7 V; TP4 +3V0 2.955-3.045 V (SBVS338H); supply current: record (blank U575 in reset/ROM, few mA [A]) |
| Pass | +3V0 in range, current < 15 mA [A], nothing warm |
| On fail | limit hit: lift R20 (LDO_OUT vs load), feed 3.0 V into TP4 at 30 mA to split; U3 battery POR needs VBAT > 3.46 V max |
| Closes | - |
| Source | sub-debug-test step 2; sub-power +3V0 |

## Stage D: Programming: DFU first, SWD backup, boot stub

### D1. first flash: tack R1.1 PH3 (2.58, 3.85) to +3V0 C1.1 (6.92, 0.83) (both B), 5 V at 100 mA limit on J3/J4, USB D+/D- on J10/J11, power-cycle, dfu-util flash the board-alive image, remove the tack

| | |
|---|---|
| Tools | iron, USB cable, PC, dfu-util |
| Expect | ROM DFU enumerates (ST DFU 0483:df11) WITHOUT PA9 VBUS sense (DK-17D option B test) |
| Pass | image runs after the tack is removed |
| On fail | no enumeration: DK-17 is real: SWD on TP1/TP2/TP3/TP5 (probe purchase decision, DBG-1 C), then R24 at the next placement round (DK-17D option C) |
| Closes | DK-17, DBG-1 |
| Source | sub-debug-test step 3; decisions-log DK-17D = B then C |

### D2. ST-HELLO + option-byte dump over USB CDC

| | |
|---|---|
| Tools | pod_test.py |
| Expect | build id = git sha of the image; RDP 0; nSWBOOT0/nBOOT0 defaults |
| Pass | matches the build |
| On fail | re-flash; record option bytes (CV-8) |
| Closes | - |
| Source | FWSIM rev1_telemetry; CV-8; HWC-12 |

### D3. SWD attach once while F is reachable (only if a probe exists)

| | |
|---|---|
| Tools | SWD probe (optional) |
| Expect | IDCODE read |
| Pass | attach + halt |
| On fail | note it; DFU stays the path |
| Closes | - |
| Source | sub-debug-test step 3 |

### D4. boot stub: jump to ROM DFU over USB and re-flash; repeat with 2.95 V on TP4 (R20 lifted); keep a DFU session > 160 s with the charger watchdog armed; with a cell fitted note charging pauses in DFU

| | |
|---|---|
| Tools | PC, bench supply |
| Expect | enumeration + full DFU at 2.95 V (DS13737 Table 150 fn 1: functional to 2.7 V); charger watchdog does not reset U3 mid-session (stub writes WATCHDOG_SEL 11); charging pauses (PA2 drives TS high) |
| Pass | all three |
| On fail | USB at 2.95 V fails: higher-V LDO option (DK-06 B); watchdog fires: fix the stub order |
| Closes | PWR-I7, DBG-8 |
| Source | sub-debug-test step 6; DK-06; PWR-I3 |

### D5. PB4 back-feed in reset and DFU: meter C13.1 (MIC_VDD) and TP10 (MIC_DATA)

| | |
|---|---|
| Tools | multimeter, PPK2 |
| Expect | record; ~60 uA class back-feed path (ECR-0013 F5) |
| Pass | recorded; Off-mode rule documented |
| On fail | firmware parks PB3/PB4; accept in reset/DFU only |
| Closes | SAI-11 |
| Source | sub-audio-in issue 11 |

## Stage E: Peripherals with the firmware's self-tests (bare board, F still reachable)

### E1. ST-CLK: LSE start, MSI-PLL lock, PLL1, HSI48+CRS, ADF kernel; scope MIC_CLK at R2.2 (B) and the SMPS node near L1

| | |
|---|---|
| Tools | oscilloscope, pod_test.py |
| Expect | all ready, DWT-timestamped; MIC_CLK duty 48-52 % (spec R13/D13); SMPS ~3 MHz free-running (PROC-9) |
| Pass | duty in range, clocks locked |
| On fail | duty out: MDF fallback via TP8/TP9/TP10 (sub-audio-in issue 5) |
| Closes | SAI-5 |
| Source | CV-4, CV-10; sub-debug-test step 4 |

### E2. ST-RAILS + ST-PINS: VDDA from VREFINT, VBAT (ADC4) vs multimeter, VBUS, TS, die temp, I_SENSE idle offset

| | |
|---|---|
| Tools | multimeter, pod_test.py |
| Expect | VDDA 2.955-3.045 V; VBAT within 1 % of the meter [A]; I_SENSE idle = R23 offset 3.0 mV +-0.3 mV (3.0 V x 1k / 1.001M) plus the Kelvin term |
| Pass | all plausibility rules pass (FWSIM-R58 ST-PINS) |
| On fail | R23 offset off: check R23 value / I_SENSE copper |
| Closes | - |
| Source | FWSIM-R58; R23 1M (OUT-1B) |

### E3. UI: LED on a pad board (or any LED) on J7/J8; press SW1; printf on TP7 via the USB-UART

| | |
|---|---|
| Tools | USB-UART 3.3 V, multimeter |
| Expect | LED current (VSYS - VF)/2.2k: 0.45-0.50 mA at 3.7 V; +1.36 mA while pressed; PA0 high; TP7 text |
| Pass | LED from PB7, button edges logged |
| On fail | LED dark = reversed (PAD-8) |
| Closes | UI-7 |
| Source | sub-debug-test step 5; sub-ui key numbers |

### E4. ST-USB: CDC enumerates, 16-bit mic-rate stream for 60 s

| | |
|---|---|
| Tools | PC, pod_test.py |
| Expect | 0 gaps over 60 s; 3.2 Mbit/s (33 % of USB FS bulk) |
| Pass | 0 gaps |
| On fail | drop to 8-bit or shorter frames; check D+/D- pads |
| Closes | - |
| Source | FWSIM-R60; CV-5 |

### E5. I2C2: read U3 at 0x6A at 100 and 400 kHz; scope SCL rise time

| | |
|---|---|
| Tools | oscilloscope |
| Expect | ACK; rise time with R15/R16 10k + ~10-20 pF bus [A]: 85-170 ns (< 300 ns for 400 kHz); exercises the In2 SCL run |
| Pass | ACK at 400 kHz and rise < 300 ns |
| On fail | run 100 kHz (TIMINGR table, FWSIM-R27); check the In2 bridge |
| Closes | - |
| Source | FWSIM-R27; sub-debug-test step 7 |

### E6. ST-CHG with the real cell: register dump at first power-up vs OTP defaults, write the register plan, read back; first charge SUPERVISED with a thermocouple on the cell

| | |
|---|---|
| Tools | thermocouple, multimeter, pod_test.py |
| Expect | defaults ICHG 10 mA, VBATREG 4.20 V, ILIM 500 mA, TS_HOT 60 C (then the plan: TS_HOT 45 C...); ILIM 100 mA until enumeration; U3 ~0.3 W at start of CC; RT1 reads hot (1.8 mm from U3) |
| Pass | read-back = plan; cell <= 45 C; charge ends at VBATREG |
| On fail | stop charge; reg plan or placement (RT1 lever, PWR-I4) |
| Closes | PWR-I4, PWR-I12, PWR-I10 |
| Source | FWSIM-R20, R62; CV-7; ECR-0009 item 3 |

### E7. bridge on an 8-12 ohm RESISTOR on J1/J2 (no exciter): low level tones, ST-ZSWEEP at -12 dBFS; scope OUT_A/OUT_B edges for dead time

| | |
|---|---|
| Tools | oscilloscope, 8-12 ohm resistor, pod_test.py |
| Expect | |Z| = R + 1.22 (Rds) + 0.1 (R21) within 2 % at -12 dBFS (selftest_lockin.py); dead time per knob 12.5-25 ns, no shoot-through spikes on the supply |
| Pass | |Z| within 2 %; no shoot-through |
| On fail | lift R21 to isolate the bridge; dead-time knob up |
| Closes | OUT-7 |
| Source | sub-debug-test step 9; sim/checks/selftest_lockin.py |

### E8. fault break (FWSIM-R65): with the resistor load, step the load to ~2 ohm through a current-limited supply rail or command an over-range test tone; confirm the MDF out-of-limit break fires and its polarity/threshold; record the MDF kernel clock

| | |
|---|---|
| Tools | oscilloscope, pod_test.py |
| Expect | TIM1 MOE cleared within 2 PWM periods [A], outputs to the safe state, BIF latched, event logged |
| Pass | break fires on both polarities of i*(2d-1); not on normal signals |
| On fail | fix BKOLD/threshold knobs; never ship without it (OUT-6 decided) |
| Closes | - |
| Source | FWSIM-R65; sub-processing issue 6 |

### E9. ST-PWMAB: PWM-noise A/B at 200/400/800 kHz vs stopped, mic streaming

| | |
|---|---|
| Tools | pod_test.py |
| Expect | 20-85 kHz band power difference per rate |
| Pass | lowest rate under the mic floor chosen |
| On fail | keep 400/800 kHz; MP-01 mitigations |
| Closes | OUT-8 |
| Source | FWSIM-R61; MP-01 |

### E10. ST-CYC micro-benchmarks + DWT per-hop stats; FMAC read-back if A10 had no Nucleo

| | |
|---|---|
| Tools | pod_test.py |
| Expect | cycles within the E1/E2 model bands (FWSIM-R47) |
| Pass | headroom >= the budget at the chosen clock |
| On fail | re-plan clock or algorithm (E2-ALGO) |
| Closes | FMAC-RM-UNKNOWNS |
| Source | FWSIM-R50; CV-2 |

## Stage F: Bond board to lid (gate G3), then the mic through the real duct

### F0. physical.md steps 6-8: solder wires, VHB die-cut, gauge pin through bore into the board hole, bond

| | |
|---|---|
| Tools | pin gauge + 20G tube, foam pad, kitchen scale (~30 N press [A]) |
| Expect | duct offset <= 0.14 (pin chosen to the hole) |
| Pass | pin slides out freely after the press |
| On fail | peel before cure |
| Closes | - |
| Source | physical.md steps 6-8; DBG-16 |

### F1. mic self-noise capture over USB: bridge on/off, SMPS vs LDO (REGSEL)

| | |
|---|---|
| Tools | pod_test.py |
| Expect | LN-M01 margin 26.5 dB modelled (worst 15.5 dB) |
| Pass | no line above the floor in 20-96 kHz |
| On fail | series R + C on MIC_VDD (sub-audio-in issue 7) |
| Closes | SAI-7 |
| Source | sim/noise smoke 2026-10-07 |

### F2. duct sweep: 40 kHz HC-SR04 + a swept ultrasonic source at a fixed distance, pod vs bare-board reference

| | |
|---|---|
| Tools | ultrasonic source, pod_test.py |
| Expect | mean 20-96 kHz +5.9 dB re flush (MC p05 +1.2); resonance ~61 kHz, +18.4 dB (~+14 dB with the floor mesh) |
| Pass | resonance found; EQ notch constant set (O18 knob) |
| On fail | mesh position / duct (sub-audio-in 3, 13) |
| Closes | SAI-13 |
| Source | acoustics MC60 2026-10-07 round 8 |

### F3. RSFLT response at 800 kHz: swept tone D1 vs D2 decimation

| | |
|---|---|
| Tools | ultrasonic source |
| Expect | record |
| Pass | decimation choice made |
| On fail | - |
| Closes | SAI-6 |
| Source | sub-audio-in issue 6 |

### F4. E11 whine: listen for SMPS / L1 whine, docked and undocked, RIGHT pod (dock magnets 5.5 mm from L1)

| | |
|---|---|
| Tools | ears |
| Expect | nothing audible |
| Pass | silent |
| On fail | LDO mode during listening (REGSEL) |
| Closes | DK-11 |
| Source | sub-dock-usb DK-11 |

## Stage G: Exciter and listening (gate G4)

### G1. exciter on J1/J2 via the arm; |Z| sweep low amplitude; listen for C14 'sing'

| | |
|---|---|
| Tools | pod_test.py, ears |
| Expect | |Z| close to A5's LCR values; no audible sing |
| Pass | both |
| On fail | C14 swap (OUT-5); PWM rate |
| Closes | OUT-5, PAD-11 |
| Source | sub-output issues 2, 5 |

### G2. E2 listening: translated nature files through the exciter at the tragus; pick the algorithm variant

| | |
|---|---|
| Tools | ears |
| Expect | spec B passes bat-call recall 0.83 in sim; slim B 0.65; A 0.39 |
| Pass | owner picks |
| On fail | - |
| Closes | E2-ALGO, ECR-0007 |
| Source | backlog E2-ALGO |

## Stage H: Close the pod, then current and feel

### H1. puck selective fit (physical.md step 9), skin, close with tape (test build)

| | |
|---|---|
| Tools | calipers |
| Expect | puck top -> skin 0.005-0.135 |
| Pass | one click per press, none at rest |
| On fail | next shorter / longer puck |
| Closes | - |
| Source | physical.md step 9 |

### H2. Off current: Stop 2, PPK2 in series with the cell

| | |
|---|---|
| Tools | PPK2 |
| Expect | 15.5-22.7 uA (off_D12) + R23 3.0 uA = 18.5-25.7 uA [derived] |
| Pass | <= ~26 uA |
| On fail | +1.36 mA = SW1 pre-pressed: refit the puck; else PB3/PB4 back-feed |
| Closes | PWR-I15 |
| Source | sub-power off_D12; CV-1 |

### H3. dock charge, LED, pad force T5 (kitchen scale under the pad)

| | |
|---|---|
| Tools | kitchen scale |
| Expect | pad force >= 0.5 N worn (preload model) |
| Pass | all |
| On fail | set change (ARM-2) |
| Closes | - |
| Source | physical.md step 14 |

## Stage I: Environment and wear (gate G5)

### I1. spray coupon IPX4 5 min, open along the rebate, inspect indicator tape; then IPX5; 3 open/rebond cycles

| | |
|---|---|
| Tools | spray nozzle, indicator tape |
| Expect | no water inside; mesh holds (Laplace ~2.7 kPa at 42 um) |
| Pass | dry inside |
| On fail | corner beads (RPB-13), mesh treatment, dock potting |
| Closes | - |
| Source | docs/research/sealing-and-service.md |

### I2. 2 h wear with the real pod pair, then a day

| | |
|---|---|
| Tools | - |
| Expect | comfortable; no rub |
| Pass | owner says yes |
| On fail | mass / force changes |
| Closes | ECR-0006 |
| Source | ECR-0006; PHYS-8D |

## Backlog items this plan closes

ARM-1R, ARM-2, ARM-3, ARM-4, ARM-5, ARM-9, DBG-1, DBG-8, DK-02, DK-03, DK-11, DK-17, E2-ALGO, ECR-0006, ECR-0007, FMAC-RM-UNKNOWNS, OUT-4, OUT-5, OUT-7, OUT-8, PAD-11, PAD-4, PAD-8, PWR-I10, PWR-I12, PWR-I15, PWR-I4, PWR-I7, Q-A-PHYSICAL-FIRSTWINS, RB-4, RB-TOL, RPB-16, RPB-17, SAI-11, SAI-13, SAI-5, SAI-6, SAI-7, UI-7
