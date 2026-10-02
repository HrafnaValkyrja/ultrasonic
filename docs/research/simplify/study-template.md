# Simplification study: ranking, three packages, one recommendation

Dated **2026-10-02** (machine clock Fri 2026-10-02 18:5x EDT = 22:5x UTC; the harness header said 2026-10-01 and is one day stale, so every date below is the real one). Status: **read-only opportunity study**. No design file was edited. ECRs raised in the tracker: see section 8. Rule applied (owner, spec O19/O20): rev 1 is the final device, so score by reliability and size first (co-equal), then daily convenience, diagnosability (O18), serviceability, and money last. **Revised 2026-10-02 (late) after the map audit:** the gates now respect O21 and O22 (section 3.9), the USB-C fallback that SIZ-06 spends is stated (IB-13), spare pins are counted honestly (3.4), FW-1 is split into what is free and what is a knob (3.7), the same-commit file list is longer (section 9), and the heel bores no longer shrink. Section 13 lists every change and the findings I rejected.

Method in one paragraph: five domain explorers (power, output, periphery, size, assembly) proposed 12-15 ideas each; an independent skeptic re-checked every claim against datasheets, the JLC parts API and ngspice; an integration pass built pin, rail and function ledgers and refused any package with a conflict. This note ranks what survived, packages it, and recommends one. Every total below is computed by `docs/research/simplify/synthesis.py` (placements and BOM lines by set arithmetic on `hw/pod/bom_jlc.csv` and the block map; pod volume and mass from `sim/checks/size_budget.py`, calibrated on `hw/mech/shell_r1.py`). Nothing here is measured on hardware.

![Today vs each package](../diagrams/simplification.png)

## 1. Bottom line (blunt)

1. **No "one expensive part replaces five cheap ones" option survived.** I checked every integration candidate that could have absorbed the sensing, charger, LDO or bridge parts (section 6). Each fails on size, on D11 (switchers only for the MCU core), on package fragility, on the bridge's ~315 mA peaks, or on D14 (coherent clocking). What survives are **deletions, firmware knobs and mechanical trims**.
2. **Recommend Package B, after one owner decision (section 3.9).** B's hardware-only gates need samples (a dock pair, exciters, wear-dummy wire), and **O21 forbids buying them before the freeze**, while O22 says hardware-only items are proved on rev 1. Either you lift O21 for a named ~$20 sample set (recommended), or you freeze on the evidence-free defaults (**B3**: PER-01D and PER-07 off). B as written: pod-board placements 56 -> 49 (eight 0402 passives out, the LED in), BOM lines per JLC order 30 -> 27, Extended types 11 -> 12 (the R21 shunt: no Basic 0402 0.1 ohm exists, verified 2026-10-02T22:51Z), pod 7.80 -> 6.83 cm3 (-12.5 %), height with belly 18.7 -> 16.55 mm, mass -0.46 g, hand-soldered wires 12 -> 9, arm wires 4 -> 2, +3V0 peak 326 -> about 92 mA, MCU pins listed free 8 -> 9 (8 unassigned, 4 clean: section 3.4), average current -0.03 mA with the over-current guard off. B3: 49 placements, 28 BOM lines, 12 wires / 11 pads, 4 arm wires, the same 6.83 cm3.
3. **Package A alone does not satisfy O20**: it removes four 0402 parts and changes nothing about size. It is the floor; every A item is inside B.
4. **The three biggest wins are not electrical parts:** arm wires 4 -> 2 by moving the LED to the lid (PER-07, needs your O8 reversal and E1), bending the dock tails flat (SIZ-06, -407 mm3; it also spends the in-shell USB-C fallback, O16(3): IB-13), and making the self-test current sense better by firmware instead of by a filter cap (OUT-03).
5. **PER-01 (take CC out of the pod) is the weakest item in B.** It pays one resistor, one pad and one wire, and it carries a hardware-only rotation risk and loses the pogo head being dead until a pod is mated. It ranks last of the 38 items. With 4 contacts at 2.5 mm pitch there is no rotation-safe pin order (180 degrees swaps 1<->4 and 2<->3, so VBUS and GND cannot both be safe), so it works only if the magnets key hard. It is gated on a keying test that needs a $5.21 sample pair, which O21 blocks; pass = the rotated head repels on the exact pair to be bought, any partial hold fails. The default (no sample, test fails, or you dislike a live head) is "keep Rd and J12 in the pod" with a 5-contact dock, VBUS on the centre pin (50 placements instead of 49).
6. **BQ25186 (Package C) is a robustness swap, not a simplification:** no part removed, +3.2 mm2, still an X-ray-only package, and its datasheet contradicts itself in six places. Take it only if you value hand-reworkable pads, the cooler exposed-pad path (68.3 vs 107.1 C/W) and the /PG and /CE hooks over 3.2 mm2.
7. **The ceiling (D) shows what "aggressive" costs.** 41 placements and 5.94 cm3, but it stacks five hardware-only, irreversible decisions (no crystal, no LED, no I2C pull-ups, no armour plate, thin walls) on a device worn for years. Not recommended; no ECR raised.
8. **The money model in `bom.md` is wrong and it changes nothing you should do.** JLC Standard PCBA (the only option this board can use) charges **$1.53 per BOM line, Basic or Extended**, plus $51.12 setup, $16.42 stencil, X-ray per hidden-joint body: roughly $124-168 of fixed fees per order, not $58-100. "Fewer Extended types" is the wrong metric; fewer BOM lines and fewer hidden-joint packages is the right one. Money stays last in the ranking.
9. **The tracker cannot see most of what we cut.** `plm.py impact` returns no relation for R4, R6, R15-R19, C17, C20, D1, J12 or Y1 (section 9). The YAML contracts (`pin-contract.yaml`, `rail-budget.yaml`, `vcrm.yaml`) are the only machine guard, and removing a part without editing them in the same commit turns `tools/checks/interfaces.py` red. The audit found more files that name the removed refs and no guard watches them at all: the firmware-emulation and layout-noise sim contracts, the `bom_check.py` self-test, `system_map.py`, `place_r1.py` and `docs/build/bom.py` (section 9).
10. **The gates and O21 form a loop.** Gates need parts, parts need the freeze (O21), the freeze needs the evidence (O22). Section 3.9 asks you to cut it once, with a recommendation.

## 2. Ranked opportunities (all survivors, one table)

Score = `3*P + 2*W + 4*F + area/5 + vol/40 + r + 2*c + 2*d - 2*h - g` (P placements removed, W hand-solder joints removed, F fragile or hidden-joint packages retired, area = courtyard mm2 removed on part cuts, vol = pod or pad mm3 removed, r extra reliability, c daily convenience, d diagnosability, h = 1 if a wrong guess is hardware-only, g = owner, sample or bench gates). Money is deliberately not in the formula. The score ranks value **before** the gates clear; the Pkg column says where each item lands. Columns: **Plc** placements removed system-wide (negative = added; PER-07 moves the LED from the pad board to the pod board, so it is 0 here and +1 on the pod board), **Ext** Extended types removed (negative = added), **$/order** for 4 assembled boards under the corrected Standard-PCBA model (parts + $1.53 per BOM line removed; `*` = derived, unquoted pad-board saving), **$/pod** BOM parts, **Area** courtyard mm2 (negative = saved), **Vol** mm3 (pod, or pad for PER-07/08). Relation ids are `R-<name>` in `docs/system/plm/items.yaml`. Part numbers are glossed where they first appear.

<!--RANKED-->

Notes on the table. **PER-08 competes with PER-07** (LED to the lid or no LED); only one can be taken. **OUT-03 needs OUT-07** (state length for the sample window) and **OUT-05 needs OUT-07** (rail bulk drops 25 -> 15 uF). **SIZ-01 and SIZ-03 need SIZ-02** (usable height). **PER-01D is the dock half of PER-01 and PWR-04** (they are the same cut with different contact orders); PWR-03 is its no-risk half. Duplicates counted once: PWR-03 = PER-01 CC half = PWR-04 CC half = SIZ-09; PWR-06 = PER-03; PWR-07 = PER-04; PWR-12 = OUT-07; ASM-06 = OUT-06; ASM-07 = PWR-01; ASM-08 = SIZ-01; ASM-10 = SIZ-03.

## 3. Packages

### 3.1 Totals (computed, today = Rev E)

<!--TOTALS-->

Reading the table: courtyard density is courtyards over both faces; the proven routed board (20.05 x 11.55 mm, 52 footprints, commit 6e93246, 2026-09-30) reached 42.9 %, today's 34 x 13 draft is 27.9 % and fails 7 nets, so B at 31.9 % is well inside what has routed. "Fees (lines)" is $1.53 x the change in BOM lines per order. "Pad board" is the periphery study's derived estimate for not ordering the second JLC design (unquoted). The three B variants (dock sample fails; PER-07 off; both off) are tabulated in section 3.9, computed by the same script. The runtime rows are at the 4.20 V charge target and with the FW-1 over-current guard off; the two FW-1 knobs (guard on, VBATREG 4.10-4.15 V) cost runtime as stated in 3.7. The $/order rows assume 4 boards while ASM-X recommends assembling 6-8: the parts rows scale by 1.5-2, the BOM-line and setup fees (per order) do not. Corrections to the integration ledger: it quoted 51 placements for the dock fallback (I recount 50: B's 49 plus R18) and 6.80 cm3 for B (I get 6.83 with the 1.25 mm F gap the skeptic required, not 1.15). The optional SWD frame header (ASM-02, HX PZ1.27-2x5P) would add one frame-only Extended line (13); it is not counted because it is not on the device.

### 3.2 What each package is

| | **A  Cleanups** | **B  Final-size integration (recommended)** | **C  B + BQ25186** |
|---|---|---|---|
| One line | Delete four 0402 parts, shrink the shunt, close ECR-0005 in firmware, fix the money model | A, plus the bridge and self-test cuts, CC out of the pod, LED on the lid, and the whole mechanical stack that makes rev 1 final-size | B, plus the charger swapped to a hand-reworkable WSON |
| Electrical members | OUT-02, OUT-04, OUT-07, PER-02, PER-03, PER-06, PWR-03, PER-11, FW-1 | A, plus OUT-01, OUT-03, OUT-05, PER-12, and PER-01D and PER-07 (**both gated and OFF by default unless you lift O21 for the sample set, 3.9**) | B, plus PWR-01 |
| Mechanical members | none | SIZ-01 (28 x 12), SIZ-02 (with an SW1 back-stop), SIZ-03 (1.25 mm), SIZ-04, SIZ-06 (spends O16(3)), SIZ-14, ASM-09 | same as B |
| Process members | ASM-01, ASM-05, ASM-11, ASM-X, SIZ-15 | same as A | same as A |
| Removed refs | R11 R17 C20 R19 | R11 R17 C20 R19 R18 R4 R6 C22 (LED1 added) | same as B |
| Swapped | R21 1206 -> 0402 | R21 -> 0402; C14 22 uF 0603 -> 1 uF 0402 | also U3 -> BQ25186 |
| Rule that must hold | OUT-07 clamp ships with the rail-budget edit | the 28 x 12 outline is frozen only after the wear dummies | BQ25186 re-audited and read back on board 1 |

### 3.3 After-state: function coverage F1-F15

"same" means the electrical chain in `integration-map.md` section 1 is unchanged. No function is dropped in A, B or C; F12 is dropped only in D.

| F | Function | A | B | C |
|---|---|---|---|---|
| F1 | Hear 20-85 kHz | same | same chain. Mic port moves to the board centre line (y 6.0), duct 4.0 -> 3.55 mm (first quarter-wave about 24 kHz, in band). +4 mV of 200 kHz carrier on +3V0 at the ceiling (OUT-05): scope TP4 | same as B |
| F2 | Process | same | same | same |
| F3 | Drive the exciter | same. Duty clamp CCR 50-150 of ARR 200 | N gates drive-only (R4/R6 gone), P gates held by R3/R5; init order matters; arm carries 2 wires | same as B |
| F4 | Self-test exciter impedance | R21 0402; C22 stays | **improved**: C22 gone, R21 sampled mid-state A and B by TIM1 TRGO2, signed coil current with phase | same as B |
| F5 | Charge the cell | same; ILIM policy replaces the CC advert | same; dock has 4 contacts if the sample keys, else 5 | U3 = BQ25186 (same 0x6A I2C map) |
| F6 | Temperature-safe charge | same (J9 kept) | same | same, TS chain unchanged |
| F7 | System rail | same; peak 326 -> about 92 mA | same | BATFET 115 mohm and a 3 A path |
| F8 | Battery level | same | same | same |
| F9 | Dock detect | same (R12/R13 -> PA1 kept) | same | same; /PG on PB1 optional |
| F10 | USB data / DFU | CC branch is R18 only (R19, PA3 gone) | CC leaves the pod if keyed (Rd in the cable plug); D+/D- unchanged. A USB-C receptacle fallback would need 2 x 5.1k Rd on CC1/CC2, fitted at the receptacle wiring once R18 and J12 are gone | same as B |
| F11 | Wake / button | same | same; SW1 x re-chosen on the 28 mm board, plunger stem -0.25 mm | same as B |
| F12 | Power LED | same (pad ring, 4 arm wires) | **moves**: LED on the pod board F face behind a lid light pipe, VSYS -> R14 -> LED -> PB7, no wires | same as B |
| F13 | Charger link | INT on PA15 internal pull-up (R17 gone); I2C pull-ups kept | same | same |
| F14 | Debug / flash / test | TP6 and R11 gone; DFU-first via R1's PH3 pad; TP1-TP5 stay | adds PB6 USART1_TX hook and 4 via-dot escapes (PB6; PB8 and PB1 for the MDF mic fallback; the MIC_DATA net); every hand pad on the B face | same as B |
| F15 | ESD at exposed contacts | D3, U6, D4 kept; D1/D2 footprints deleted. **Gap not closed:** J3 still has no clamp | same | BQ25186 OVP is 18.5 V (BQ25180: 5.7 V), so D3 is the only sub-6 V guard |

### 3.4 After-state: MCU pin map

Baseline free pins (8): PC13, PH0, PH1, PB1, PB15, PB5, PB6, PB8. **A, B, C: 9 listed** = PC13, PH0, PH1, PB1, PB15, PB6, PB8, **PA3** (CC_SENSE gone), **PA10** (R11 gone); **PB5 is consumed** as a GND strap (below). D: 12 listed (adds PC14, PC15, PB7). **Honest count for B and C (audit):** PB6 carries the USART1_TX hook, so **8 are unassigned**; PB1 and PB8 are reserved for the MDF mic-clock fallback (below); PC13 is static-only (never toggle, ES0499 2.2.1) and PB15 carries the UCPD dead-battery hazard (PWR_UCPDR.UCPD_DBDIS first, ECR-0013 S2). That leaves **4 clean pins: PH0, PH1, PA3, PA10** (the table in 3.1 carries all three counts).

| Pin | Change | Why / rule |
|---|---|---|
| PA3 (13) | freed in A, B, C | CC_SENSE and R19 deleted; also ends the ROM bootloader USART2_RX worry |
| PA10 (31) | freed in A, B, C | AN2606 Table 199: the ROM loader pulls PA10 up itself. If ECR-0003 is taken PA10 becomes GB_P and PB15 GB_N (PA9 and PB0 free up): the count stays 9 |
| PA15 (38) | CHG_INT as GPIO + internal 30-50 kohm pull-up + EXTI15 falling | R17 gone. The U575's USB-C block (UCPD) can switch a 5.1 kohm dead-battery pull-down onto PA15/PB15 at reset unless firmware sets PWR_UCPDR.UCPD_DBDIS first; PA15's is armed by a high on PB5. **Option byte (HWC-6, unverified reading):** ST's production FLASH_OPTR is 0x1FEFF8AA (RM0456 Rev 7 section 7.9.13), so PA15_PUPEN (bit 28) = 1 = "dead battery disabled / TDI pull-up activated" on PA15. If that reading is right, factory option bytes give PA15 a JTDI pull-up and no Rd at reset, which would soften ECR-0013 S1 on PA15 (PB15 still follows UCPD_DBDIS). The boot stub needs no option-byte change (leave PA15_PUPEN at the factory value; the GPIO pull-up is switched on in firmware anyway) and sets UCPD_DBDIS first either way; the PB5 strap stays as belt and braces (one via, one pin). Read FLASH_OPTR and PA15 at reset on board 1 |
| PB5 (41) | **strapped to GND** (a via) | cuts the PA15 pull-down path in hardware (ECR-0013 S1). One claim wins: not a TSC sensor (PER-10 rejected), not a spare stub |
| PB6 (42) | USART1_TX debug hook (B, C): counted as used | SWO is lost to the mic clock on PB3, so a printf line is the cheapest telemetry |
| PB1 (19), PB8 (45) | **reserved: MDF1_SDI0 (PB1) and MDF1_CCK0 (PB8), the mic fallback** | sub-audio-in issue 5: rev 1 has no mic-clock duty fallback (ST specifies no CCK duty; the timer-made-clock fallback needs an MDF clock-in pin and the ADF has none; A3 section 1.4 proposed 0 ohm links to PB8/PB1, Rev E did not fit them). C's optional BQ25186 /PG on PB1 is **excluded** unless the MDF fallback is dropped. Never also PWR-02's EXTI1 on PA1 (rejected): one port per EXTI line |
| MDF mic fallback (PER-12) | 4 via dots: PB6, PB8, PB1 and the MIC_DATA net; the clock end is R2's mic-side pad with R2 lifted | recommended: +0.2 mm2 over the first 3-dot plan keeps a hand-wire recovery (PB8 to R2's mic-side pad, PB1 to the MIC_DATA dot, then firmware moves the mic from ADF1 to MDF1, the A3 plan's alternative) for a bad ADF clock duty. The alternative is to **state the fallback is dropped** (your decision; a bad duty then has no recovery short of rev 2, hardware-only) and let C use PB1 for /PG |
| PC13, PB15 | listed free with restrictions | PC13: never toggle (ES0499 2.2.1). PB15: UCPD dead-battery pull-down, UCPD_DBDIS first (ECR-0013 S2); also the ECR-0003 leg-B N gate if taken |
| PA6 / TIM1 | F4 sampled by TIM1 TRGO2 + OC5/OC6 compare (internal, no pin) | RM0456 Table 307: adc_ext_trg10 = tim1_trgo2 |
| PA1, PA2, PA6 | all ADC1-only (PA1_IN6, PA2_IN7) | a self-test sweep on ADC1 pauses VBUS and TS reads: a firmware scheduling rule, not a pin clash |
| PA9 | also USB_OTG_FS_VBUS, but TIM1_CH2 on this board | set GCCFG.VBDEN = 0 and force B-session valid from PA1 or I2C: why R12/R13 and PA1 stay |

### 3.5 After-state: rail loads

| Rail | Today | A | B | C |
|---|---|---|---|---|
| +3V0 (U4 TPS7A2030, TI 300 mA 3.0 V LDO; ICL 360 mA min) | avg up to about 11.5 mA; **peak 326 mA** (5.8 MCU + 2.15 mic + 1.06 gates + 315 exciter + 0.93 pull-ups + 1.36 switch) vs 300 mA rating | pull-ups -2 parts; **peak about 92 mA (31 %)** with the clamp (ngspice: LDO cycle-average current 304 mA at 0 dBFS, 81 mA at the clamp, 24 mA at the -12 dBFS ceiling; the explorer's 161 mA was coil current, not supply current) | -0.03 mA (two pull-downs); carrier ripple at the ceiling 6.7 -> 10.9 mV pk-pk (C14 25 -> 15 uF effective) | same as B |
| VSYS (cell 175 mA continuous, 350 mA 2C pulse) | peak 327 mA = **93 %** of the pulse rating | about 93 mA = 27 % | same as A | BATFET 115 mohm (10 mV drop at 93 mA); U4 docked at 4.5 V VSYS +8 K at the ceiling, +22 K at the clamp; SYS_REG battery tracking cuts that 12-47 % (firmware) |
| VBUS | D4 kept; ILIM default 500 mA | ILIM 100 mA at boot, then enumeration / BC1.2 / step-up while watching PA1 | same | VINDPM options VBAT+300 mV / 4.5 V / 4.7 V / off (no 4.2 V); termination is disabled while VINDPM is active, so plan it off or measure VIN at the pin first |
| VBAT | unchanged | unchanged | unchanged | unchanged |
| VDD11 / L1 | unchanged | unchanged | SIZ-06 raises the dock target 1.45 mm: left-pod rear magnet to L1 goes from about 5.6 to 4.1 mm (derived): run E11 on the LEFT pod docked and undocked; SMPS -> LDO fallback is firmware | same as B |
| BRIDGE_RTN | R21 1206, 250 mW | R21 0402 166 mW: 10 mW at 322 mA | same | same |

### 3.6 After-state: wires, lid and shell

| | A | B | C |
|---|---|---|---|
| Arm wires | 4 | **2** (OUT_A, OUT_B); the LED wires and the 5.0 x 9.3 mm pad board are gone | 2 |
| Hand-solder wires / pads | 12 / 12 | **9 / 8** (J7, J8, J12 gone; J4 and J6 share one GND pad that also separates J3 DOCK_VBUS from J5 VBAT) | 9 / 8 |
| Hand joints along the arm | 10 (pod end 4; pad end 6 = 4 pad-board pads + 2 PTH) | 4 (pod end 2 + 2 exciter splices) | 4 |
| Board | 34 x 13 x 0.8 | **28 x 12 x 0.8**, centre line y 6.0 (mic, SW1, LED, lid pins) | same |
| Pod envelope | 7.80 cm3, 38.0 x 11.80 x 15.20 + 3.5 belly | **6.83 cm3**, 38.0 x 11.35 x 14.50 + 2.05 belly, 13.15 mm off the temple (was 13.60) | same |
| Lid / shell | none | board hung from the lid (2 printed 0.7 mm pins into 2 NPTH 0.9 mm, 4 VHB 0.25 mm spots, mic chimney boss); ribs, foam strips and clamp bands out, an SW1 back-stop in (a 1.4 mm compressed foam dot on the cell top under the button, or a printed post stopping the board 0.1-0.15 mm early; section 4.4); F gap 1.25; lid wall 0.8 with the 0.7 mm plate kept; LED light pipe D0.9-1.0 with clear epoxy plus boss; dock tails bent flat (belly 3.5 -> 2.05; this spends the USB-C fallback, see IB-13); heel channel, strut bore and counterbore **stay** Ø1.0 / Ø1.2 / Ø1.6 (a 2-wire bundle only adds slack; the heel has 196 degrees of R0.8 bends that cannot be reamed, so shrinking toward the resin's 0.8 mm limit buys nothing); pad -50 to -110 mm3, -0.15 g from the deleted pad board | same |
| Constants to change | none | `hw/mech/shell_r1.py`, `pad.py`, `heel.py`, `frame.py` after ECR-0001; `place_r1.py` | same |

Honest size picture: the cell sets the pod **length** (38.0 mm, unchanged) and the pod loses only 0.45 mm of thickness off the temple. The gain is **height** (18.7 -> 16.55 mm) and volume (-12.5 %). The 28 x 12 board is the irrevocable choice (O20); the shell can be reprinted, so print and wear S0/S1/S2 dummies first (SIZ-15, extends ECR-0006; the arm half needs NiTi wire and litz, which O21 blocks: section 3.9).

### 3.7 After-state: firmware work

| | A | B (adds) | C (adds) |
|---|---|---|---|
| Boot | UCPD_DBDIS first; PA15 input pull-up, EXTI falling; PA10 input pull-up in the stub before the DFU jump; write-protected boot stub (button + VBUS -> ROM DFU), U3 WATCHDOG_SEL = 11 before any jump; re-init I2C after DFU | N pins idle-low (OISxN = 0, OSSI = 1) **before** any P pin leaves analog or MOE is set; park the bridge by driving idle levels, never by returning pins to analog | read back every BQ25186 reset value; VINDPM off or measured; SYS_REG tracking; IBAT_OCP about 500 mA backstop (accuracy at 0.5 A unspecified) |
| Output | duty clamp CCR 50-150 applied **after** the shaper and dither, live before TIM1 first runs; self-test capped at -12 dBFS | F4: TIM1 MMS2 = OC5REF/OC6REF -> TRGO2 -> ADC1 trg10, shortest sample time, DMA raw samples summed in software (the ADC oversampler would mix A and B), auto-zero with the bridge off | none |
| Charge | ILIM 100 mA -> enumeration / BC1.2 / step to 300 mA watching VIN droop on PA1; ICHG 170 mA (50 mA below 20 C); EN_PUSH 0, PB_LPRESS_ACTION 00; **charge voltage is a knob** (VBATREG, default 4.20 V; 4.10-4.15 V = code 60-65 costs about 14 % energy, so worst-case runtime falls to 10.7-11.5 h, below D18's ~12 h target: set it only after E4 data) | none | none |
| Safety / diagnostics (FW-1) | over-current cutoff on the F4 samples **while the self-test runs** (power 0; normal listening is not covered, so sub-output issue 6 stays open, held by the OUT-07 clamp, the IWDG and R3/R5). An always-on ADC1 guard is a knob: +0.15 mA at 25 kS/s, +0.24 mA at 200 kS/s, +0.34 mA at 400 kS/s (about -0.4 / -0.7 / -1.0 h typical runtime), interpolated between the only two points DS13737 Rev 10 Table 103 gives (14-bit single-ended, IDDA_s + IDDV_s: 130 + 15 uA at 10 ksps, 550 + 90 uA at 1 Msps), and it must be scheduled on ADC1 against the PA1/PA2 reads; daily wire-health check (log exciter R and L: an arm-wire fatigue break shows as a number, not a silent pod); +3V0 droop log; interrupt and NACK counters; "assume docked" if PA1 and I2C are both unreadable | LED PWM exactly 200.0225 kHz (1 x fs_out = HCLK/400) or 400.045 kHz, per LN-R11/LF-6 (a bare "integer ratio of HCLK" is not the rule, and 100 kHz sits in the reshape filter's assumed 88.8-111.2 kHz transition band; the spec'd "> 20 kHz" sits inside the mic band); status patterns on the lid LED (the O8 reversal covers the site **and** non-solid patterns: O8 says solid, no pulsing); patterns run in Run mode, because TIM4 stops in Stop 2 and PB7 has no LPTIM output (sub-ui issue 6): a docked pattern in Stop 2 needs a wake tick at full duty; PB6 printf | none |

### 3.8 After-state: bench-verify, owner decisions, ECRs

| | A | B | C |
|---|---|---|---|
| **Must be verified on the bench (board 1)** | DFU entry with R11 absent; INT edge and stuck-low check with UCPD_DBDIS; ILIM policy at a wall charger (no D+/D-); duty clamp at 7-12 ohm; 322 mA step on +3V0/VBAT with a scope | A, plus: carrier ripple on TP4 and the MP-01 PWM-noise A/B (OUT-05); real-ADC noise and the sample instant for F4 (OUT-03); light-pipe leak and LED PWM whine (PER-07); dock keying (pass = the rotated head **repels** on the exact target + head pair to be bought; any partial hold fails), head/target mate, bent-tail pull test, wire gauge <= 0.35 mm OD, L1 vs magnets on the LEFT pod (E11); lid-hung bond under a drop and 600k presses at 1.2-2.0 N, SW1 stroke and click feel with the back-stop; ADF mic-clock duty on PB3 (E6) and the MDF fallback wire; FLASH_OPTR and PA15 at reset (HWC-6). Which of these can run before the freeze depends on O21: section 3.9 | B, plus: VINDPM, Device_ID, EN_PUSH / PB_LPRESS_ACTION, ILIM 400 vs 380 mA and RON_BAT read back (the datasheet contradicts itself); exposed-pad solder joint by X-ray |
| **Owner decisions** | accept firmware-only protection for ECR-0005 (D17 ceiling written down); O12(c) charge-time policy for CC-less chargers; O13 (Extended count +1, fee-neutral); Standard PCBA and a corrected budget (about $270-385 per order before cell and exciter, against the O13 ~$300 milestone) | A, plus: **O21: lift it for the named sample set, or take B3 (section 3.9)**; D6 wording narrows to "P-gate pull-ups mandatory"; **O8 reversal** (LED to the lid, and non-solid status patterns) after E1; O12(a)/O16(3) dock contacts (4-contact + Rd in the cable plug) after the keying test; **O16(3) USB-C fallback spent by SIZ-06** (or keep the 3.5 mm belly, +391 mm3); MDF mic fallback kept (4 dots) or dropped (3.4); VBATREG default 4.20 V until E4; freeze 28 x 12 after the dummies; plate kept (spec v0.14) | B, plus: **O16(2)** names BQ25180: approve BQ25186 after a fresh audit of SLUSF69A |
| **Failure classes it adds** | firmware-fixable: DBDIS order, ILIM policy, clamp bug (rail dip, not damage). Hardware-only: a bootloader that wants an external PA10 pull-up (unlikely; stub can pull up) | firmware-fixable: sample instant, init order, LED PWM. **Hardware-only:** board outline and routing at 28 x 12; lid-hung bond with the SW1 press in tension on the VHB (back-stop mitigates); light pipe and splice; keying; carrier ripple if the 1 uF C14 is not enough; no mic-clock recovery if the MDF dots are dropped | firmware-fixable: register differences (if read back). Hardware-only: WSON footprint and exposed-pad soldering |
| **Diagnosability (O18)** | keeps every register, TP and isolation link; loses the CC voltage on PA3 (replaced by STAT0 VIN_PGOOD, ILIM_ACTIVE, enumeration) and the TP6 pad (probe C21); gains DFU-first, PB5 strap, interrupt counter | gains signed coil impedance with phase and a sweepable sample instant, LED testable on the bare board and visible on the dock, B face exposed on lid lift, spare bare boards as fit coupons. Loses J7/J8/J12 test pads and F-face access after bonding (SWD, BOOT0, J5/J6 therefore sit on B). Residual: a bonded pod whose boot stub never runs needs a cut-open | gains a /PG level that works with I2C dead and a /CE hardware inhibit |
| **ECR-0001** (frame.py drift) | independent | **must land first** (shell, pad, heel constants) | same as B |
| **ECR-0002** (routing around U3) | item 4 (R11) superseded; item 1 survives for R15/R16 only (R17 gone) | same as A | items 1-2 moot (WSON pads, no ball escape); item 3 (C7 move) stays |
| **ECR-0003** (leg B to PA10/PB15) | compatible; R11 half subsumed; optional | same | same |
| **ECR-0004** (SOT1216 footprint) | pending the JLCDFM written verdict | same (superseded only on the NTZD3155C branch) | same |
| **ECR-0005** (LDO 300 vs 315 mA) | **closed** by OUT-07, with the rail-budget.yaml edit in the same commit | closed | closed |
| Also touched | ECR-0009 capped self-test; ECR-0010 DFU-first; ECR-0011 checked on a spare bare board; ECR-0013 S1 mandatory and F1 rewritten; ECR-0006 extended (SIZ-15; deferred by O21); ECR-0008 reserve more parts (deferred by O21) | same, plus ECR-0008: add the 4-pin target C42463273 (19 in stock) and head C5126845 (45) (deferred by O21: 3.9) | plus ECR-0008: BQ25186 (301-451 in stock, falling) |

### 3.9 Gates vs O21 and O22 (one owner decision)

The first version of this study said every hardware-only gate "resolves before the board order". That does not survive two owner rules that were already in the spec: **O21** (2026-10-02: parts, exciters, NiTi wire, cells and MCUs are not ordered before the design freeze; ECR-0006/0007/0008 deferred) and **O22** (the freeze is an evidence gate, and "hardware-only items are listed with the rev-1 measurement that proves each"). The gates below need purchases, purchases need the freeze, and the freeze needs evidence: a loop only you can cut. Prices: JLC parts API 2026-10-02T23:30Z; `docs/build/bom.md` for wire and litz.

| Gate | Needs | Does O21 block it? | A wrong answer costs | Rev-1 measurement that proves it (O22) |
|---|---|---|---|---|
| 1 JLCDFM written verdict on the exact footprints (PMCXB290UE DFN1010B-6 redraw, DSBGA U3) | the footprints and Gerbers only (a free upload) | no | a board re-order | JLC's own assembly result; X-ray of U3 |
| 2 Dock keying (PER-01D), bent-tail pull test, head/target mate | 4-pin target C42463273 (Extended, 19 in stock, $2.4857) + head C5126845 (45 in stock, $2.7230) = $5.21, plus a spare target to bend; the -03 head / -04 target pairing is itself a guess | yes (parts) | **board**: R18 and J12 are gone, so an unkeyed mate cannot be repaired in the pod, and it can hurt pod and host | the rotated mate on the real pair |
| 3 E1 exciter coil R/L and leads (the PER-07 splice) | 2-3 RC-BC02 exciters (price unknown: the listings were never saved) and an LCR meter | yes (exciters) | **board**: J7/J8 are deleted, going back is a board re-spin | E1 on the delivered exciter |
| 4 Wear dummies at S0/S1/S2 (SIZ-15, extends ECR-0006) before the 28 x 12 freeze | resin prints and ballast (you already print resin; ballast on hand is unknown to me); the arm half needs NiTi 0.75 mm ($13.49 per 5 ft) and litz ($0.71 per 10 m) | the arm half yes; a pod-only dummy no | **board**: the outline is the one irrevocable choice (O20) | 2 h wear (T5) in a reprinted shell |
| 5 Lid-hung bond and SW1 press coupon (SIZ-02) | 0.25 mm VHB tape and resin; O21's list does not name consumables but says "parts": ask | unclear | shell only (reprintable) | drop test and 600k presses on the real pod |

**Two ways to cut the loop (you decide):**

- **(a) Lift O21 for a named sample set (recommended).** One 4-pin target, one head and a spare target ($5.21 + $2.49), 2-3 RC-BC02 exciters, 0.25 mm VHB, NiTi and litz for the dummies: about $22 of priced items plus the exciters. It follows O22's intent (the freeze is an evidence gate), the set is tiny, and all five gates resolve before the freeze. STM32U575s, cells and the rest of the order stay frozen under O21.
- **(b) Freeze on the evidence-free defaults (B3).** PER-01D off (keep R18 and J12: a 5-contact dock with VBUS on the centre pin) and PER-07 off (the LED stays on the pad board, O8 kept). No sample is needed. This also matches the 19:10 authorization recorded in `docs/brief/decisions-log.yaml` (baseline within owner decisions, decision-changing measures built as measured variants). It gives up the arm-wire halving, the biggest single win (#1 in the ranking), and leaves R24 (arm-wire fatigue) on 4 wires.

Computed by `synthesis.py` (placements and BOM lines by set arithmetic on `bom_jlc.csv`; the pod envelope is the same in all four because neither item changes it):

<!--VARIANTS-->

Which of the five gates survive each choice:

| Gate | (a) lift O21 for the sample set | (b) freeze on the defaults (B3) |
|---|---|---|
| 1 JLCDFM verdict | survives (free) | survives (free) |
| 2 Dock keying | resolved before the freeze; pass = hard repel | gone: PER-01D is off and the 5-contact dock is the baseline |
| 3 E1 for the splice | resolved before the freeze | gone: PER-07 is off; E1 stays a plain rev-1 measurement |
| 4 Wear dummies / outline | resolved, pod and arm | pod-only dummies survive if resin and ballast are on hand; the arm half moves to the rev-1 wear test; SIZ-01 is frozen only after the pod-only dummies |
| 5 Bond and SW1 coupon | resolved | survives only if VHB is on hand; otherwise proved on rev 1 in a reprintable shell (O22) |

Gates 1-4 decide board-irrevocable choices and are the ones to settle before the freeze; the shell-side items (gate 5, the light pipe, the bent tails, SIZ-06) can be proved on rev 1 and reprinted. If you take (a) and a sample fails, the package falls back to B1 (keying fails) or B2 (E1 rules out the splice) with no re-planning.

### 3.10 Recommendation

**Take B, in the form your O21 decision allows.** It is the only package that meets O20 (final size) without betting the device on an irreversible guess, it makes the self-test better rather than worse, and with PER-07 it halves the arm wires (the failure-prone off-board item, R24). Its board-irrevocable gates (JLCDFM, keying, E1, wear dummies / outline) resolve before the freeze **only if you lift O21 for the sample set in 3.9 (recommended)**; otherwise take B3 and prove the rest on rev 1 under O22. Two pieces are separable if you disagree: PER-07 (the LED; costs you O8) and PER-01D (the dock CC cut; costs you nothing if the sample fails). Take **C only as a deliberate trade**: it buys hand rework and a /PG hook for 3.2 mm2 and a new datasheet to audit, and its /PG on PB1 is excluded while the MDF mic fallback stays. Treat **D as a menu to read, not a package**: its items are individually available, but each is hardware-only.

## 4. Per-domain detail

### 4.1 Power (charger, regulator, sensing)

Survived: PWR-03 (confirmed), PWR-06 = PER-03 (confirmed), PWR-12 = OUT-07 (confirmed), PWR-09 (confirmed, low value, D only), PWR-01 (revised: owner option), PWR-07 = PER-04 (bench-gated, D only), PWR-04 (option; recommend against). Rejected: PWR-02, PWR-05, PWR-08, PWR-10, PWR-11.

- **Her three questions.** (a) *Bridge from VBAT/VSYS:* no. A P-FET (PMCXB290UE: Nexperia 20 V complementary N+P pair, DFN1010B-6) with its source at 3.6-4.5 V cannot be turned off by a 3.0 V GPIO; it works only while VSYS <= about 3.45 V. Fixing it costs 4-8 parts and raises full-scale peaks to 0.45 A (4.2 V / 9.32 ohm), above the cell's 350 mA pulse rating. (b) *Bigger LDO:* not needed. TPS7A2030's current limit is 360 mA minimum (SBVS338H) and a clamp holds peaks near 92 mA; but that 360 mA is specified at VOUT = 0.9 x nominal and ISC is 160 mA typical, and a 7 ohm exciter already reaches 361 mA, so the **clamp is mandatory**, not optional. (c) *D4 (1N5819WS Schottky, reverse-dock guard):* keep it. Removing it (PWR-05) puts a reversed source on U3's IN, absolute minimum -0.3 V, next to a Li-ion cell; D3 (ESD9X5.0ST5G, onsemi 5 V one-way TVS in SOD-923) would conduct forward with an unverified rating; she builds the cable herself.
- **Why no PMIC.** nPM1300 (Nordic PMIC): LDOs are 50 mA, so U4 stays; the only stocked form is a 35-ball 0.4 mm WLCSP. BQ25155/BQ25150 (TI chargers with ADC): 20-ball 0.4 mm DSBGA, stock 25 and 201, extra caps cancel the saving. BQ25120A/BQ25125, MAX77654/MAX77650: integrated switchers, which D11 forbids. See section 6.
- **PWR-02 (drop R12/R13, read dock from the charger's /PG pin) rejected.** Sign error (the MCU's internal pull-up sinks 60-100 uA while docked against R12/R13's 25 uA); /PG is U3's own opinion (a weak 4.75 V host plus D4 at a full cell reads "undocked"); R12/R13 is the only VBUS reading that survives a dead U3 or dead I2C; and PA9 is TIM1_CH2 so the USB core needs PA1 for B-session valid.
- **PWR-01 revised.** Same I2C address 0x6A and register list; adds /PG and /CE; leadless WSON-10 2.2 x 2.0 x 0.8 mm; RthetaJA 68.3 vs 107.1 C/W; 115 vs 55 mohm battery FET. Corrections: it is not a size or JLC-process win (pads are 0.2 mm wide, below the 0.25 mm minimum the DFN is condemned for; X-ray still applies); VINDPM has no 4.2 V option and "termination is disabled when VINDPM is active" (a VINDPM-limited charge never terminates); the datasheet contradicts itself in six places (VINDPM reset, pushbutton in ship mode, Device_ID, ILIM 400 vs 380 mA, FET resistance, VIN range). The existing `audit-datasheet-claims.md` was done on SLUSE99C and must be redone.
- **Free firmware wins** from the missed list: charge voltage as a knob (4.10-4.15 V gives about 1.25-1.6x cell cycles for -14 % energy and +50-100 mV dock headroom, but worst-case runtime falls to 10.7-11.5 h, below D18's ~12 h target, so the default stays 4.20 V until E4 data), SYS_REG battery tracking, IBAT_OCP backstop, ILIM step-up; and settle the NTC location once (cell via J9 vs RT1 beside a 0.3 W U3).

### 4.2 Output stage (H-bridge, self-test)

Survived: OUT-01, OUT-02, OUT-03 (revised), OUT-04, OUT-05, OUT-07 (all confirmed or revised); OUT-06 only as a conditional fallback; OUT-08 rejected.

- **The bridge's area is not in the FETs.** Q1+Q2 are 2.2 of 28.1 mm2 of courtyard; **R21 alone is 10.2 mm2** (1206, 250 mW for a 10 mW job). Five discrete changes (OUT-01..05) cut the stage from 28.1 to about 10.7 mm2, remove 3 placements and 6 joints, add no current, keep every firmware knob.
- **OUT-01.** Shoot-through needs both FETs of a leg on. R3/R5 (100k to +3V0) hold both P-FETs off from power-up through reset; a floating-on N-FET with P off only grounds an output. ROM DFU leaves PA8 untouched (R3 holds it), PA9 high, PA7 low, PB0 floating: all safe (AN2606 Table 199). The rule that makes it safe is firmware: drive the N pins idle-low before the P pins leave analog. Needs edits to `rail-budget.yaml` (the bridge row assumes R3-R6; `interfaces.py` raises FAIL when an assumed ref is missing), `vcrm.yaml`, spec D6, spec section 9.
- **OUT-03.** R21 carries +i in state A (Q1P + Q2N) and -i in state B; `clip0(V_A) - clip0(V_B) = i`, so a unipolar ADC reads the **signed** current with no offset resistor and no filter. SPICE (ideal ADC): +0.1 / +0.5 / +1.7 % amplitude error at -12 / -22 / -32 dBFS, 0.3 mH. The skeptic's catch: the sample must land within about +/-25-50 ns of the state centre (10 mA/us ripple slope: 300 ns late gives +4.3 % at -12 dBFS, +51 % at -32 dBFS), so trigger from TRGO2 with the OC5/OC6 compare pulses and the shortest sample time, not from the update event.
- **OUT-07.** Clamp the TIM1 duty to |2d-1| <= 0.5 as a register constant and cap the self-test at -12 dBFS. The supply current is proportional to (2d-1) squared, so the clamp gives about 81 mA from the LDO, not 161. Closing ECR-0005 without editing `rail-budget.yaml` turns the interfaces check into FAIL ("waiver expired").
- **OUT-06/ASM-06.** DMC2400UV-7 (Diodes SOT-563 pair, C177025) went to **stock 0** between 05:04Z and 22:22Z on 2026-10-02. The only genuine fallback is NTZD3155C (C236117, 8,698 in stock, $0.1684): +0.49 mA gate drive (always-awake pessimistic 12.5 -> 11.8 h), +4.7 mm2, and the 800 kHz noise knob costs 3.3 mA instead of 1.2 mA. Decide on a written JLCDFM verdict for the ECR-0004 redraw first.
- **OUT-08 (MAX98357A, Maxim/ADI I2S class-D amplifier) rejected:** 2.4 mA idle against 0.83 mA, an asynchronous 330 kHz spread-spectrum carrier that breaks D14, no PWM-rate or dead-time knob, 16 kS/s only. Net +1.07 / +1.27 / +1.61 mA awake.
- Missed and folded into FW-1: use the OUT-03 samples as an over-current cutoff **while the self-test runs** (power 0), and run the F4 chain daily as a wire-health check. This does **not** close sub-output issue 6: the F4 samples exist only in self-test, so normal listening still has no fault cut-off beyond the OUT-07 clamp, the IWDG and R3/R5. An always-on guard needs ADC1 converting at the PWM rate and costs +0.15 mA (25 kS/s) to +0.34 mA (400 kS/s), 2-7 % of the 5-8.5 mA budget and about -0.4 to -1.0 h typical runtime (interpolated from DS13737 Rev 10 Table 103, which gives only 10 ksps and 1 Msps); it is a firmware knob you can switch on if rev 1 shows worn-wire shorts as brown-out loops.

### 4.3 Periphery (MCU, USB, UI)

- **PER-02 (R11).** AN2606 Rev 69 Table 199: the ROM loader uses PA10 as USART1_RX "alternate push-pull, pull-up". Confirmed in the local copy.
- **PER-03 (R17).** /INT is an open-drain 128 us low pulse; 40 kohm x 15 pF = 0.6 us. TI's pin table says 1-20 kohm, so this is outside the recommendation but with 200x margin. Pair it with the PB5 strap and UCPD_DBDIS (already ECR-0013 S1). HWC-6 asks to read FLASH_OPTR.PA15_PUPEN before deleting R17: ST's production OPTR 0x1FEFF8AA has bit 28 = 1, which RM0456 Rev 7 section 7.9.13 reads as "dead battery disabled / TDI pull-up activated" on PA15; if that is right, the stuck-low case of ECR-0013 S1 may not exist on PA15, the boot stub needs no option-byte change, and the PB5 strap stays as belt and braces (unverified: read it on board 1).
- **PER-01.** The dock-CC cut (USB Type-C R2.5 Table 3-2/3-14/3-15: a Type-C plug on a legacy cable carries its own Rd 5.1k; a USB-A plug needs nothing). Audit addition: with 4 contacts at 2.5 mm pitch a 180-degree mate swaps 1<->4 and 2<->3, so VBUS and GND cannot both be safe (the symmetric 5-pin trick, VBUS on the centre pin, is impossible); an unkeyed mate raises pod GND to host +5 V and back-drives the host's D+/D- through U6 and the MCU clamps, and D4 does not help. So the keying test must be a hard repel on the exact pair to be bought, and a failed test means the 5-contact target, not a cleverer 4-pin order; record the contact order in gen.py and sub-dock-usb when the sample is in hand. Corrections: the claimed hazards are overstated (VBUS on the centre pin already keeps 5 V off CC); mate pairing is a guess (three 4-pin heads and two 4-pin targets are listed, suffix meaning unknown); at a USB-C PD brick with no D+/D- the charge is 75-90 mA, about double the time; BCD may need the VBUS pad (GB_P here). 4-pin target C42463273 has the same 21.20 x 6.86 x 2.80 mm body: the belly does not shrink.
- **PER-04 (R15/R16).** tr = 0.8473 x R x C = 440 ns at 40 kohm x 13 pF, 847 ns at 50 kohm x 20 pF against the 1000 ns limit. The ROM loader parks PB13/PB14 as SPI2 pull-down/push-pull, so the bus is dragged low in DFU. TI says 10k, and this link sets TS_HOT 45 C for cell safety. D only.
- **PER-05 (crystal).** HSI16 +/-0.5 % maps to a 0.32 % output pitch error (map_freq): 4.8-12.9 Hz between ears, 3-8x the 1-2 Hz beat D16 accepted, so the docked SOF trim (HSITRIM 18/29/40 kHz per step plus PLL1FRACN) is **mandatory**, and a never-docked pod keeps the factory error. +67 uA awake (HSI16 150 uA vs MSIS about 83 uA), -0.35 uA in Off. Irreversible: no crystal-grade matching, no algorithm A fallback. D only.
- **PER-07/PER-08.** LED on the lid: 4 -> 2 arm wires (bundle 0.51 -> 0.42 mm; the bores **stay** at Ø1.0 heel channel, Ø1.2 strut bore and Ø1.6 counterbore: the first draft shrank them to 0.8 / 1.0 / 1.3 mm, which bought no pod size, put the printed channel at the resin's 0.8 mm limit, and the heel has 196 degrees of R0.8 bends that cannot be reamed, so the 2-wire bundle only adds slack and eases the O17 no-pinch rule), pad board deleted; pad thickness gain bounded to -0.5..-1.1 mm because strut, collar and the splice pocket remain. Credit missing in the first pass: a lid LED is visible on the dock (the charge indication sub-ui issue 5 never specified). PER-08 (no LED) trades 0.9 h of runtime for the only cheap "board alive" light: worse on convenience and diagnosability.
- **PER-11/PER-12.** DFU-first flash needs no SWD probe (none in the kit, O13); TP1/TP2/TP3/TP5 stay as the backup. PB5/PB6/PB8/PB15 are parked by the ROM loader. PER-12 is four dots, not 2-3: PB6 (TX), PB8 and PB1 (the MDF mic fallback of sub-audio-in issue 5) and the MIC_DATA net, with R2's mic-side pad as the clock end (section 3.4).
- Rejected: PER-09 (merge U6 + D3 into a 10-pad USON array: fragile for an area-neutral swap), PER-10 (capacitive touch: TSC cannot wake Stop 2, water false-touches are hardware-only).

### 4.4 Size and packaging

Pod today: 38.0 x 11.8 x 15.2 mm plus a 3.5 mm belly, 7.80 cm3 envelope, about 12.4 g (28.5 % cell, 29.8 % resin, 5.2 % dock target, 6 % board and parts, 30 % air and fill). The cell (35 mm) sets the length; the board only sets the height.

| Lever | Pod volume | Mass | Verdict |
|---|---|---|---|
| SIZ-06 bend dock tails flat (belly 3.5 -> 2.05) | -407 mm3 (-5.2 %) | -0.09 g | in B; spare-target bend and pull test first. **It spends O16(3)**: the USB-C receptacle (2.76 mm tall, 2.56 mm mouth) no longer fits a 2.05 mm belly; the fallback survives only as a reprinted shell with the belly back at 3.5 mm (+391 mm3 on the B core) |
| SIZ-01 board 28 x 12, pod top -0.7 mm (not -1.0: the cell stays 0.8 mm above the floor for the dock-wire channel; strut-relief fill clears the cell corner by 0.07 mm) | -294 (-3.8 %) | -0.22 g | in B at 28 mm, not 26 (L1 vs the dock magnets; J block + SW1 + LED need the last 6 mm; length buys no pod size) |
| SIZ-03 F gap 1.5 -> 1.25 | -166 (-2.1 %) | -0.02 g | in B; 1.15 not proven (fillets, lid +/-0.1) |
| SIZ-04 lid 1.0 -> 0.8, plate kept | -133 (-1.7 %) | -0.14 g | in B/C |
| SIZ-05 plate off | -378 (-4.8 %) | -0.45 g | D; owner aesthetic call |
| SIZ-11 walls 0.7 | -351 (-4.5 %) | -0.42 g | D; no data for 0.6-0.7 mm tough resin |
| SIZ-08 thin dock | -272 more | -0.15 g | D; 0.2 mm stubs on the daily contact |
| SIZ-07 delete USB-C keep-out | -53 (-0.7 %) | -0.01 g | moot in B: SIZ-06 has already spent the fallback |
| **B total** | **-972 mm3 (-12.5 %)** | **-0.46 g** | 6.83 cm3; 13.15 mm off the temple |
| D total | -1,866 mm3 (-23.9 %) | -1.35 g | 5.94 cm3 |

SIZ-02 (board hung from the lid) is the enabler: it removes the floorless foam, the clamp ribs and the x-slide, closing reg-pod-body issues 2 and 11 (11 is physical issue 12), but it hides the F face under the lid, so **every pad you hand-reach after bonding goes on B** (J1-J6, J9-J11, SWD pads, R1's PH3 pad). It also makes **sub-ui issue 2 worse**: today foam in compression reacts the 1.2-2.0 N SW1 press (600k cycles); hung from the lid, the press is reacted by four 0.25 mm VHB spots in tension with only 0.2 mm between the B-face parts and the cell, and a stretching tape eats part of the KMT0's 0.15 +/- 0.1 mm stroke (no-click risk). **Design response: an SW1 back-stop**, a 1.4 mm compressed silicone or PE foam dot on the cell top directly under SW1 (the cell lies under the board centre line there, so it is a real floor), or a printed post from the tub that stops the board 0.1-0.15 mm early; keep R21 (0402) and every other B part out of that footprint. The coupon spec is a drop test plus 600k presses at 1.2-2.0 N with stroke and click feel recorded. The cell (130 mAh option, SIZ-12) would take 1.06 cm3 but costs 12.4 -> 9.2 h worst-case runtime; not recommended (E4 unmeasured).

### 4.5 Assembly and JLC process

- **ASM-01.** Economic PCBA is single-sided, IC pitch >= 0.4 mm, BGA >= 0.5 mm: impossible here. Standard PCBA needs a >= 70 x 70 mm panel with 5 mm rails, fiducials and tooling holes; the rails **are** the O9 snap-off frame. Traces to the frame must cross a **solid** tab (mouse-bite holes at 0.2-0.3 mm spacing cannot pass a trace). The fee page also lists a fixture ($8.21 x 2) and storage fees not in the first model: add $16-26.
- **ASM-05.** 4-layer 0.8 mm, ENIG (U3's 0.2-0.25 mm pads need it; flat for 0.4 mm parts), track/space >= 0.10 mm (3.0-3.5 mil on 4-8 layers adds 20 % of the order), +/-0.1 mm routed edge, fill or tent the nine EP vias under U1. Do **not** mandate 0.20/0.45 mm vias: under 0.45 mm pad costs more but is a surcharge, not a limit, and the larger pad fights the shrink.
- **Rejected:** ASM-03 (frame USB-C simulator: exposed VBUS stubs on a final board), ASM-04 (coupon design: the 5-panel minimum already gives 6 spare bare boards as free fit coupons), ASM-10 (duplicate of SIZ-03), ASM-12 (FPC dock tail: collides with SIZ-06).
- **Build protocol (ASM-X):** order remark "no wash, no ultrasonic cleaning" and mask the mic port before any flux cleaning, coating or bonding; **assemble 6-8 boards, not 4** (fixed fees are per order, so a marginal board costs only its parts, about $15 of electronics per `bom.md`; the limit is the 8 U1 in stock); get a **written JLCDFM verdict** on the exact footprints (JLC's capability pages contradict each other: 0.35 mm pitch supported vs 0.25 mm minimum SMD pad); note the reflow side and pass count (L1 is rated 2 passes).

## 5. Integration: conflicts, requirements, invariant breaks

Binding rule: no package may contain a conflict or an uncovered function. Every item below is resolved by the package definitions in section 3.

### 5.1 Conflicts and how they were resolved

| # | A | B | Resolution |
|---|---|---|---|
| 1 | PWR-02 drop R12/R13, dock from /PG | ILIM step-up, ECR-0009 interlock, USB B-session override, periphery's rejection | Rejected. R12/R13 and PA1 stay everywhere. Optional /PG to PB1 in C |
| 2 | PER-01 4-contact dock | PWR-04 symmetric 5-pin, SIZ-08/09 | One cut, two contact orders. Decide after the keying sample: keyed -> PER-01; unkeyed -> 5-pin dock with Rd in the pod (B-fallback) or PWR-04 order [D+, GND, VBUS, GND, D-] |
| 3 | PWR-05 / "symmetric order + no D4" | O12(a), hand-built cable, 18.5 V OVP, U3 IN -0.3 V | D4 stays in every package |
| 4 | PER-07 LED to lid | PER-08 no LED | B/C take PER-07, D takes PER-08; both reverse O8 |
| 5 | SIZ-04 lid 0.8 | SIZ-05 plate off | B/C: SIZ-04; D: SIZ-05 |
| 6 | SIZ-06 bent tails | SIZ-08 thin dock | One belly. B: SIZ-06 after the spare-target test; SIZ-08 sample-only |
| 7 | SIZ-02 lid-hung board (F hidden) | ASM-09 pads by face, PER-11/ASM-02 pads on F, 'ledge + foam' | Rule: every post-bond hand pad on B; separate J3/J5 by order with a shared GND pad, not by face |
| 8 | SIZ-01 at 26 x 12 | L1 over the magnets, J block + SW1 + LED, ASM-08 at 30 | Freeze 28 x 12 (26 stretch, 30 not needed), after the dummies |
| 9 | PER-05 no crystal | algorithm A, D16 beat criterion | D only, with trim and an owner D16 amendment |
| 10 | PWR-01 BQ25186 | O16(2), ECR-0013, audit on SLUSE99C | Owner option (C); re-audit and read back on board 1 |
| 11 | PWR-07 = PER-04 I2C pull-ups | TI 10k, ROM DFU pulls PB13/PB14 | D only, bench-gated |
| 12 | OUT-06 SOT-563 pair | ECR-0004, MP-01 800 kHz knob | JLCDFM verdict first; NTZD3155C only if refused |
| 13 | PWR-08 delete J9 | tws-power-size Option A, cell swap | Rejected: J9 stays; PER-07 removes J8, which removes the J8/J9 ship-mode hazard |
| 14 | PER-10, PWR-10, OUT-08, ASM-03, ASM-04, ASM-12, SIZ-07, SIZ-10, SIZ-12, SIZ-13 | O18/O19, D14, size goal | Dropped from all packages (section 7) |
| 15 | OUT-01 (delete R4/R6), OUT-06 (DMC2400UV-7 sold out) | `docs/brief/triage-2026-10-02.yaml` Q19 (keep R4/R6 populated) and Q20 (adopt DMC2400UV-7), both Claude-decided at 19:05, two minutes before these ECRs | Not owner decisions and not edited here (outside my files). Resolve at the package pick: Q19's own undo path is to delete R4/R6 in gen.py before the freeze; Q20 is stale (stock 0 at 22:22Z, ECR-0004 pending) |
| 16 | gates (3.8) | O21 (no purchases before the freeze), O22 (hardware-only items proved on rev 1) | Section 3.9: one owner decision, B or B3 |

### 5.2 Requirements (A needs B)

| Item | Needs | Why |
|---|---|---|
| OUT-03 | OUT-07 | state >= 1.25 us so a 2.5-6.5 cycle sample fits |
| OUT-05 | OUT-07 (or a SPICE run of the 322 mA step at VBAT 3.3 V) | rail bulk 25 -> 15 uF |
| OUT-07 | rail-budget.yaml edit, owner acceptance, ECR-0009 cap | else interfaces.py turns FAIL; clamp after the shaper, live before TIM1 starts |
| OUT-01 | N-pin init order; D6 wording; yaml edits | floating N keeps its charge |
| PER-03 | PB5 strap, UCPD_DBDIS first | else INT reads stuck low |
| PER-02 | pin-contract BOOT_RX row edit | a shrinking contract FAILs |
| PER-01D / PWR-03 | ILIM policy, PA1 kept, B-session override, cable with Rd or USB-A plug, keying test, ECR-0008 target reserve | wall chargers never enumerate |
| PER-07 | E1, pad/heel/frame re-solve after ECR-0001, spray-tested light pipe, LED PWM >= 100 kHz | splice depends on exciter leads |
| SIZ-01 | SIZ-02, SIZ-15 | the outline is irrevocable |
| SIZ-02 | B-face pads, lip-ring keep-out, 0.25 mm VHB with a boss, drop/press coupon | bond in peel |
| SIZ-06 | wire gauge, spare-target test, potting budget, L1 check (left pod) | 0.85 mm stack has no spare |
| PER-11/ASM-02 | write-protected boot stub; bring-up step 6 at 2.95 V; solid tab; JLCDFM | DFU needs VDDUSB |
| PWR-01 | O16(2), re-audit, new symbol and DLH0010A footprint, part_heights row | register differences are firmware-fixable only if read back |
| Any cut | same-commit edits to pin-contract.yaml, rail-budget.yaml, vcrm.yaml, bom_check lock, part_heights.yaml, **and the files in section 9 that nothing watches** (firmware-emulation.yaml HWC-2/5/10, layout-noise.yaml and budget.py, the bom_check.py self-test, system_map.py, place_r1.py, bom.py), then regenerate integration-map and re-run layout-noise and e2e | the tracker is blind to most of these refs |

### 5.3 Invariants that break (and the fix)

IB-01 O8 and 4 arm wires -> PER-07 is owner-gated; re-run pad.py/heel.py/frame.py after ECR-0001. IB-02 5-contact dock and O12(a) -> keying test (pass = hard repel on the exact pair; fail = the 5-contact target, VBUS on the centre pin, Rd/J12 kept); D4 stays; cable carries Rd; a USB-C receptacle fallback needs 2 x 5.1k Rd on CC1/CC2 at the receptacle wiring once R18 and J12 are gone. IB-03 DFU gesture, B-session, ECR-0009 interlock and LED duty all key off PA1 -> PA1/R12/R13 stay; fail-safe "assume docked". IB-04 D6 "pulls mandatory" and rail-budget 'assumes R3-R6' -> narrowed with same-commit edits. IB-05 +3V0 300 mA and VSYS 350 mA, ECR-0005 waiver -> clamp plus declared peak. IB-06 D16 crystal -> D only. IB-07 F face reachable under the lid -> hand pads to B; centre line y 6.0; SW1 x re-chosen. IB-08 clamp bands and ribs -> replaced by pins and VHB. IB-09 cell 0.8 mm above the floor, 1.4 mm B gap -> height gain 0.7 mm only. IB-10 D11/MP-01 bridge and L1 >= 10 mm from the mic -> mic x 3.1-3.9, bridge x >= 14; L1 off the magnets. IB-11 O16(2) names BQ25180 -> C only. IB-12 Blade exterior and IPX4/5 -> D only. **IB-13 USB-C fallback (O16(3)) -> SIZ-06 spends it.** `shell_r1.py` USBC_KEEPOUT is 2.8 mm tall (z -12.4 to -9.6) and the Same Sky UJ32 receptacle is 2.76 mm tall with a 2.56 mm mouth. With the belly at 2.05 mm the bay floor rises from z -12.4 to -10.95, a receptacle would reach z -8.19 (0.09 mm below the cell bottom at z -8.1), and its mouth cannot open on a 2.05 mm step face. In B the fallback survives only as a reprinted shell with the belly back at 3.5 mm (+391 mm3, 7.22 cm3 and 18.0 mm total height on the B core; the board is unaffected because J3/J4/J10/J11/J12 stay the interface). That is an owner decision under SIZ-06: spend O16(3), or keep 3.5 mm. IB-14 O9/O18 hooks and O13 -> keep 5 pads and R1's pad. **IB-15 exposed J3 has no clamp and sits 0.6 mm from J5 VBAT: not closed by any surviving idea;** mitigated by pad order and a shared GND pad; the ESD option A/B/C decision (sub-dock-usb issue 15) stays with you.

## 6. Why no integrated part wins (your "one expensive part" rule)

| Candidate | Would absorb | Why it fails | Numbers |
|---|---|---|---|
| nPM1300 (Nordic PMIC) | U3, R8/R9/C19, R12/R13, R18/R19 | LDOs 50 mA (100 mA as load switches): U4 stays for the 322 mA bridge peaks; 35-ball 0.4 mm WLCSP is the only stocked form (QFN32 5x5 not stocked) | C25346894 1,093 in stock $2.67; own caps about 12 mm2 |
| BQ25155 / BQ25150 (TI charger with 16-bit ADC) | sensing parts, PA1/PA2/PA4 | 20-ball 0.4 mm DSBGA, inner balls cannot escape at 0.35/0.15 via rule; CPMID 22 uF, CVDD, CLDO, CINLS, TS bias | stock 25 and 201; LDO 150 mA; 500 mA charge |
| BQ25120A / BQ25125; MAX77654 / MAX77650 | charger + LDO | integrated switchers: D11 | 25-ball DSBGA; MAX stock 10 and 1 (unverified) |
| nPM1100, PCA9420, AXP2101, STNS01, MAX20303, ADP5360 | charger + regulators | no I2C, switchers, 150 mA LDOs, QFN-40 5x5 with undocumented noise | stock 0-49 (JLC listings, unverified) |
| MAX98357A (Maxim/ADI I2S class-D amp) | Q1, Q2, R3-R6, C14 | 2.4 mA idle vs 0.83 mA; asynchronous 330 kHz carrier breaks D14; no dead-time or PWM-rate knob; 16 kS/s only; F4 reduced to supply current | net +1.1/+1.3/+1.6 mA; TQFN 26.6 mm2 vs 10.7 simplified discrete |
| TAS2110/TAS2120 (TI smart amps), AW88261 (Awinic), NAU8315 (Nuvoton) | bridge | boost converter (D11) plus a 1.8 V rail; 4-11 mA idle | 227 / 40 / 0 in stock |
| AO3400A/AO3401A (SOT-23 discrete pair) | cheaper FETs | 17 nC x 200 kHz gate drive = +1.8..+3.1 mA | 9.6 h always-awake; +36 mm2 |
| Bridge from VSYS/VBAT | ECR-0005 | P-FET cannot turn off; 0.45 A > 350 mA pulse rating | +4..+8 parts |
| 500-600 mA LDO (LP5912, RT9080, TLV755P) | U4 | not needed: current limit clears the peak and a clamp bounds it | +3 mm2, 42-72 uVrms noise into the mic supply |

The honest reading: the project's parts are already small, cheap and mutually dependent; what remained was **clutter** (pulls, filters, DNP footprints, a 1206 shunt, a wire pair for a light) and **mechanical slack** (a belly sized for tails, a floorless foam, a board taller than the cell).

## 7. Rejected and deferred ideas

| Idea | Verdict | Reason |
|---|---|---|
| PWR-02 R12/R13 off, /PG dock detect | rejected | PG is U3's opinion; loses the only VBUS reading that survives a dead U3; +60-100 uA docked; PA9 B-session |
| PWR-05 remove D4 | rejected | reversed source on U3 IN (-0.3 V min); D3 forward rating unverified; +0.07 W |
| PWR-08 delete J9 | rejected | only way to read cell temperature (R23); tws-power-size Option A |
| PWR-10 switched VBAT divider | rejected | 2.1 uA for a spare pin and 0.9 uA injection into PA4's clamp |
| PWR-11 BQ25185 standalone | rejected | no I2C, fixed hot trip about 60 C vs the cell's 45 C limit |
| PER-09 merge U6 + D3 into a TPD4E05U06 array | rejected | 10-pad 0.5 mm USON, X-ray fee, area-neutral |
| PER-10 capacitive touch for SW1 | rejected | TSC cannot wake Stop 2; water/hair false touches are hardware-only; reverses O16(7) |
| OUT-08 MAX98357A | rejected | section 6 |
| ASM-03, ASM-12 | rejected | exposed stubs on a final board; custom FPC collides with bent tails |
| ASM-04 coupon design | rejected | the 6 spare bare boards are free coupons; extra design fee |
| ASM-10 | rejected | duplicate of SIZ-03 |
| SIZ-10 1.0 mm pads on 1.27 pitch | rejected | 0.27 mm pad gap on the VBUS/VBAT pair; no pod gain |
| SIZ-12 130 mAh cell | not recommended | -1.06 cm3 but 12.4 -> 9.2 h worst case; E4 unmeasured; O16(1) |
| SIZ-13 adapter stand-off 1.8 -> 1.2 | leave | R17 grip, snap-tab strain, NiTi E re-solve |
| SIZ-07 delete USB-C keep-out | moot in B | SIZ-06 has already spent the fallback (IB-13); the 0.7 % only matters in a shell that keeps the tails |
| 0.6 mm board | not taken | JLC lists 0.6 mm, but -0.2 mm and +/-0.1 tolerance; quote first |
| Single-sided board, 2-layer board, Economic PCBA | rejected | mic on B and SW1 on F; no GND plane under SMPS/PDM/bridge; Economic is single-sided |

## 8. ECRs raised by this study

Raised with `plm.py ecr new` (the tracker computed each impact list from the items the package changes). Each is status `proposed`; you decide. Bodies are in `docs/research/simplify/ecr-A.md`, `ecr-B.md`, `ecr-C.md`. After the map audit the three ECRs were edited in place (same ids, no package changed identity): ECR-0015 gained the O21/O22 gates and the B3 variant, all three gained the unwatched-files list.

<!--ECRS-->

## 9. Whole-system cross-check evidence

`plm.py impact` was run (2026-10-02T22:5xZ) on every ref, net and file the packages touch. It prints relations only for these targets: R21 (R-OUT-BOARD, R-OUT-DEBUG), C22 (R-OUT-DEBUG), C14 (R-PWR-OUT-RAIL), R11 (R-PROC-DEBUG), R14 (R-PWR-UI), TP6 (R-PWR-DEBUG), U3 (R-PWR-BOARD, R-PWR-DOCK), net CC_SENSE (R-PROC-DOCK), net CHG_INT (R-PWR-PROC), net LED_K (R-PROC-UI, R-UI-ARM, R-UI-PAD), `shell_r1.py` (8 relations), `pad.py` (R-ARM-PAD, R-OUT-PAD), `frame.py` (R-ARM-PAD, R-BODY-ARM, R-PHYS-FRAME), `place_r1.py` (11 relations). **It returns nothing for R4, R6, R15, R17, R18, R19, C17, C20, D1, J12 or Y1, and for net CC**: they have owner items but no relation watches. So the relation lists in section 2 combine the tracker's output with the explorers' hand lists (every id was checked to exist in `items.yaml`), and the real guard is the contracts. **Follow-up for the owner (not done here, outside my allowed files): add relation watches for those refs, or the next simplification will cut parts the tracker cannot see.**

Baseline of the machine-checked contracts, `tools/checks/interfaces.py`, 2026-10-02T22:56Z: PASS inside, clamp-bands, heights (F tallest L1 1.00 mm, B tallest U2 1.08 mm), board-nets; WARN mic-port, switch, outline (board file 1.60 mm thick vs 0.80), pins (3 known hazards), **rails (+3V0 peak 326 mA > 300 mA; VSYS 93 % of the cell pulse rating)**, frame (ECR-0001, 8 of 10 facts differ); selftest 54 of 54. The rails WARN clears only with OUT-07 plus the `rail-budget.yaml` edit.

Contract edits that must travel in the same commit as the schematic change: `pin-contract.yaml` (CC_SENSE, BOOT_RX, LSE_IN/LSE_OUT in D, I_SENSE role text, VBUS_SENSE untouched), `rail-budget.yaml` (R11/R15/R16/R17 pull-up row, bridge assumes R3-R6, R21 rating, ECR-0005 waiver and peak, relation text "buffered by C14"), `vcrm.yaml` (D6 gap text, D16 and D14 rows in D, O8-led, O12-dock), the sourcing lock and `part_heights.yaml` (C409058, LED, SOT-563/WSON rows), then regenerate `integration-map.md` with `system_map.py`.

**Files that nothing watches (audit, 2026-10-02).** Found by grepping `*.py` and `*.yaml` for the removed refs; hits that are spec risk numbers (R18 = RSFLT response, R19 = experience) were discarded. The O22 freeze criterion 4 needs the layout-noise and e2e sims re-run on the final layout, so these edits are part of the freeze.

| File | What names a removed or changed part | Edit |
|---|---|---|
| `docs/sim/firmware-emulation.yaml` | HWC-10 ("keep gate pulls R3-R6 ... keep R21/R22/C22"); HWC-5 (the lock-in assumes R22/C22 as built); HWC-2 (R1's PH3 pad on the F face); L267 `bridge_gates` ("gate pulls R3-R6 hold off"); L311 `zsweep_math` (R22/C22 corner, ~100 kohm offset); L247 (CHG_INT modelled with the R17 pull-up); FWSIM-R17 and FWSIM-R26 (reset/DFU/brown-out pin timelines and the R22/C22 scale constants) | P pulls R3/R5 hold P off, a floating N gate can only ground an output; F4 by TRGO2 sampling needs no filter or offset; PH3 pad on B; INT on the internal pull-up |
| `docs/sim/layout-noise.yaml`, `sim/noise/budget.py` | `P1_shared_rail` (22 uF C14); `adc_ref_mv_pk_max` (R22/C22 16 kHz pole); LN-M03 (R21 Kelvin path, footprint changes to 0402); the "MLCC piezo singing C14 22 uF" note; `rerun_when` gen.py / bom_jlc.csv | C14 = 1 uF 0402, no C22, R21 0402. The `C14.2 -> R21.2` pair in budget.py stays valid (C14 stays); re-run |
| `docs/sim/e2e-chain.yaml` | only the F4 provider note and `r_shunt_ohm` 0.1 (unchanged) | no edit; re-run |
| `tools/checks/bom_check.py` | self-test fixtures hard-code C20 (L1302, L1306) | switch them to a surviving ref such as C19, or the self-test breaks |
| `hw/pod/system_map.py` | hand-kept block lists and F4/F10/F12/F13/F14 text (L27-L35, L52-L69, L77, L87-L88, L101-L103, L120) | rewrite the hand text, then regenerate integration-map.md |
| `hw/pod/place_r1.py` | PLACE rows for C20, C22, R18, R19, J12, J7, J8, R4, R6, R11, R17 | new placement, done together (O14); not run here |
| `docs/build/bom.py` | C22 note (L39) and quantities | regenerate bom.md |
| `hw/padboard/` | the pad-board generators (J7/J8 blocks in mech.py) | retired with PER-07 |

## 10. What the study did not establish (unverified, labelled)

- Hardware keying of the Xinyangze magnets, the head/target mate, tail strength after bending, and wire gauge fit (no sample in hand).
- A real 14-bit ADC's noise and offset for OUT-03 (SPICE used an ideal ADC); the real 3 MHz SMPS origin (sub-processing issue 9); bus capacitance of I2C2 (estimated 12-15 pF).
- USB Type-C Cable and Connector Specification R2.5 (March 2026) tables were **not re-opened** by the reviewers (local copy fetched 2026-09-30); BCD behaviour without the VBUS pad; the ADI, ST, NXP and X-Powers PMIC rows (JLC listings and memory; analog.com timed out); MAX98360A-D, MAX98358, PAM8302A, NS4150B (listing only); Diodes DS35537 is marked "advance information".
- Anything priced in the pad-board saving (about $10 per order) and the JLC fixture and storage fees: not quotable from a static page; PCB fab price and shipping unquoted; whether the order form counts panels or boards.
- SLUSF69A (BQ25186) has at least six internal contradictions; every register assumption is "read back on board 1".
- Exciter coil resistance and leads (E1), cell swelling and pulse length (E4), temple stiffness (E12): all open; PER-07, SIZ-12 and SIZ-13 depend on them.
- Whether you have resin, ballast and VHB tape on hand (the O21 scope of gates 4 and 5), and the price of an RC-BC02 exciter (the listings were never saved).
- The ADC1 power of an always-on over-current guard: DS13737 Rev 10 Table 103 gives only 10 ksps and 1 Msps, so 25-400 kS/s is interpolated linearly (an assumption), and the 12 h runtime arithmetic uses tws-power-size.md's 21.2 h at 7 mA (usable about 148 mAh).
- The PA15_PUPEN reading (3.4): RM0456 Rev 7 and the ST production value are quoted, the behaviour at reset is not measured.
- The local Xinyangze 4-pin drawing was not re-opened for this revision: the rotation argument (180 degrees swaps 1<->4 and 2<->3) is arithmetic on 4 contacts at 2.5 mm pitch, the magnet polarity is unknown until a sample is in hand.

## 11. Sources (accessed 2026-10-02 unless noted)

Datasheets and notes (local copies in `ultrasonic-scratch/ds/` or cited by the sibling notes): TI **BQ25186** SLUSF69A Rev A (Jan 2025), https://www.ti.com/lit/ds/symlink/bq25186.pdf (sha256 96834a4566939677); TI **BQ25180** SLUSE99C Rev C (Jan 2023, sha256 c2008f613723fec3); TI **BQ25185** SLUSF65B Rev B, https://www.ti.com/lit/ds/symlink/bq25185.pdf (sha256 c73ed7d63e6532bb); TI **TPS7A20** SBVS338H (sha256 663a9ff5bca60864); ST DS13737 Rev 10 (Jul 2024), RM0456 Rev 7 (Mar 2026), AN2606 Rev 69 (Nov 2025), AN5373 Rev 7 (Nov 2023), ES0499 Rev 12 (Jun 2026); Nexperia PMCXB290UE v.1 (30 May 2023); Diodes DS35537 Rev 11-2 (Mar 2020); onsemi NTZD3155C (local); Maxim MAX98357A/B 19-6779 Rev 7 (2/16; Adafruit-hosted copy, sha256 abac92d3522a204f); Xinyangze drawings YZT0675-20048-05025-01 A.1 (2022-03-24), -04025-04 A.1 (2022-03-28), YZ103915020T-04025-02 D.0 (2015-07-08); Renata datasheets via `tws-power-size.md`; USB Type-C R2.5 (Mar 2026, local copy 2026-09-30).
JLC: fee page https://jlcpcb.com/help/article/pcb-assembly-price (last updated 2026-09-09, read 2026-10-02 22:30Z); capabilities https://jlcpcb.com/capabilities/pcb-assembly-capabilities and https://jlcpcb.com/capabilities/pcb-capabilities; extra-charge and process-edge articles (2026-09-09). Parts API: explorers 04:44-05:38Z, reviewers 22:22-22:34Z, and **this synthesis 2026-10-02T22:51Z** (Basic/Extended class of all 29 BOM lines: 10 Extended on the pod board; no Basic 0402 0.1 ohm resistor exists, only the 1206 C25334). Stock moves fast: DMC2400UV-7 98 -> 0 in 17 h; BQ25186 451 -> 301.
My own re-runs: `tools/checks/interfaces.py` (22:56Z), `plm.py impact` (22:5xZ), `sim/checks/size_budget.py` scenarios (reproduced S0 7,801 mm3 and every lever), `synthesis.py`.

## 12. Reproduce

```
source tools/env.sh
systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 python3 docs/research/simplify/synthesis.py     # tables + synthesis.json
python3 docs/research/simplify/build_study.py                                                                          # rewrites this note
python3 docs/research/simplify/make_diagram.py && bash docs/diagrams/render.sh docs/diagrams/simplification.svg        # diagram
```

Sibling notes (read these for the evidence behind each id): `docs/research/simplify/power.md`, `output.md`, `periphery.md`, `size.md`, `assembly.md`. ECR bodies: `docs/research/simplify/ecr-A.md`, `ecr-B.md`, `ecr-C.md`.

## 13. Audit changes (2026-10-02, after the map audit)

Eleven audit findings and one scope note were verified against the sources. All eleven were accepted; finding 3 only in part (two of its proposed edits were rejected, see the table). What changed:

| # | Finding | Verdict | Change |
|---|---|---|---|
| 1 | Gates vs O21/O22 (HIGH) | accepted | New section 3.9 (gate table, two ways to cut the loop, B variants computed by `synthesis.py`, which gates survive each); sections 1, 3.1, 3.2, 3.8, 3.10, ECR-0015 reworded. Recommendation: lift O21 for a named sample set; default if you say nothing: B3 |
| 2 | USB-C fallback spent by SIZ-06 (HIGH) | accepted | IB-13 rewritten (numbers from `shell_r1.py`, `size_budget.py`); SIZ-06/SIZ-07 rows; O16(3) added to the SIZ-06 decision; Rd pair note. The audit's +407 mm3 for keeping the belly is the S0-baseline figure; on the B core `size_budget.py` gives **+391** (7,220 vs 6,829 mm3) |
| 3 | Same-commit list omits files (HIGH) | accepted in part | Section 9 table and 5.2 row; ECR-0014/0015/0016. **Rejected:** a `docs/sim/e2e-chain.yaml` edit (its R18/R19 hits are spec risk numbers; it names no removed part, so re-run only); `sim/noise/budget.py` needs no edit (the C14.2 -> R21.2 pair survives, C14 stays); FWSIM-R17's text is unchanged, its emulator pin model is what must change |
| 4 | Spare pins double-counted (MED) | accepted | 3.1 now carries three counts (9 listed, 8 unassigned, 4 clean); PB1/PB8 reserved for the MDF mic fallback; C's /PG on PB1 excluded; PER-12 grows to 4 dots (+0.2 mm2); sub-audio-in issue 5 addressed |
| 5 | FW-1 cutoff is not free (MED) | accepted | Option (a) written down: self-test-only cutoff at 0 mA, sub-output issue 6 stays open; always-on guard is a knob with its cost (+0.15 to +0.34 mA, interpolated). The audit's "4-6 %" is 2-7 % over the 5-8.5 mA budget; its "-0.5 h" becomes -0.4 to -1.0 h typical, -0.2 to -0.35 h worst |
| 6 | SW1 press reaction after SIZ-02 (MED) | accepted | SW1 back-stop and coupon spec in 4.4, 3.6, 3.8; corrected the issue numbers (reg-pod-body 2 and 11, not 12) |
| 7 | 4-pin rotation (LOW) | accepted | Pass criterion = hard repel on the exact pair; fail = 5-contact target (50 placements); gate text in 1, 3.8, 4.3, IB-02 |
| 8 | PA15_PUPEN (LOW) | accepted | One line in 3.4 and 4.3; RM0456 Rev 7 bit 28 and ST production 0x1FEFF8AA confirmed in the local text; the reading is labelled unverified |
| 9 | 4.10-4.15 V is not free (LOW) | accepted | VBATREG is a knob, default 4.20 V until E4; runtime rows added to 3.1; 4-vs-6-8 boards note |
| 10 | Bore shrink buys nothing (LOW) | accepted | Bores stay Ø1.0 / Ø1.2 / Ø1.6; "bores shrink" removed from B (3.6, 4.3); the pad volume saving comes from the deleted pad board, so it is unchanged |
| 11 | LED PWM wording, O8, Stop 2 (LOW) | accepted | 200.0225 kHz or 400.045 kHz; O8 reversal covers patterns; patterns in Run mode or on a wake tick |
| 12 | Audit scope (INFO) | n/a | Nothing to fix; the audit's 12 pads for B3 counts ASM-09's shared GND pad as not applied, I carry 11 (the study's own B-fallback arithmetic keeps ASM-09) |

Found while checking, not in the audit: triage Q19/Q20 disagree with OUT-01/OUT-06 (5.1 row 15); the "closes reg-pod-body issues 2, 11, 12" claim mixed in a physical.md number (fixed).
