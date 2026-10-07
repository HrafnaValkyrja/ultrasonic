# SUB-PROCESSING: MCU, core SMPS, clocks, firmware
Rev MZ-2 2026-10-07: body moved to the Phase-2 design (hw/current.yaml, ECR-0018): U1 + SMPS + LSE on B of the one-face 30 x 12 board, Y1 FC-12M 2012 + 8p2 0201 load caps, 100n 0201 decoupling, +3V0 on the In2 plane, I2C_SCL bridged on In2; layout distances and noise margins re-probed; Rev F draft numbers moved to the reference section. Pins/nets unchanged (pod_mz2.net nets == Rev G).

```yaml
status: {schematic: "Rev G logic, package set MZ-2 (hw/pod/gen.py MZ2 table L93; POD_PACKAGES=mz2 -> hw/pod/pod_mz2.net); bom_check nets PASS 195 pins / 42 nets (2026-10-07)", layout: "Phase-2 board hw/pod/draft_r2/out/routed.kicad_pcb routed: DRC 0, 0 unconnected (kicad-cli 10.0.6 DRC re-run 2026-10-07; commit f6291e6); owner review pending (O25)", firmware: "none written; requirements only in docs/sim/firmware-emulation.yaml (FWSIM); Python reference models in sim/dsp", updated: 2026-10-07}
item: SUB-PROCESSING   # docs/system/plm/items.yaml
src_of_truth: ["hw/pod/gen.py L178-212 (MCU, SMPS, LSE; Y1 MZ-2 branch L202), L273 (PB5 strap), L335-346 (TP7-TP10, spare pins), MZ2 table L93-108 (Phase-2 packages)", "hw/pod/draft_r2/out/routed.kicad_pcb (positions)", "docs/system/pin-contract.yaml (signal per net)", "docs/system/integration-map.md §4 (generated pin map)", "docs/research/A3-u575-plan.md (chip plan)", "docs/system/plm/ecr/ECR-0018.md (Phase-2 log: MZV-08 LSE, route closure, noise)", "docs/spec.md D5 L131, D11 L210, D12 L218, D14 L241, D15 L272, D16 L285, D17 L293, D18 L297, O18 L644, O19 L645, O25-O27 L651-653"]
owner_decisions: [O6 (resolved -> D11), O9, O18 (fail informatively), O19 (changes via firmware only), O20 (final size), O25 (Claude lays out, owner reviews), O26 (Phase 2), O27 (thin > short > long)]
open_ecrs: {ECR-0018: "Phase 2 package set, approved, implementation in progress", ECR-0005: "+3V0 peak 326 mA > U4 300 mA (MCU shares the rail)", ECR-0008: "MCU reserve, 8 at JLC", ECR-0009: "fw interlocks: no output while docked, ceiling", ECR-0010: "fw tested before board order", ECR-0013: "pin hazards: S1 PB5 strap done, S2 UCPD_DBDIS fw, PB4 back-feed, PA2 in DFU"}
checks: ["python3 tools/checks/interfaces.py [pins] (2026-10-07: WARN, 3 known hazards GB_N PB15, MIC_DATA PB4, TS PA2, all ECR-0013)", "python3 tools/checks/bom_check.py [nets] (2026-10-07: PASS)", "sim/noise/out_r2/budget.json LN-M01/LN-M04 (2026-10-07: PASS)", "python3 tools/plm.py impact SUB-PROCESSING"]
abbr: {ADF1: "audio digital filter (PDM->PCM, runs in Stop 2)", MDF1: "multi-function digital filter (ADF fallback)", SMPS: "MCU-internal core buck", LSE: "32.768 kHz crystal oscillator", MSIS: "multi-speed internal RC, PLL-locked to LSE", P80/P48: "clock plan 80.009 MHz / 48 MHz", hop: "DSP frame 128 samples = 0.64 ms", DS: "ST DS13737 Rev 10 (Jul 2024)", ES: "ST ES0499 errata", RM: "ST RM0456 Rev 7", UCPD: "USB-C PD block; dead-battery 5.1k pull-downs at reset", board: "hw/pod/draft_r2/out/routed.kicad_pcb (Phase 2, sha256 da4e8b13...)", "F/B": "board faces: F toward the lid, B toward the cell", In2: "inner copper layer 3 = +3V0 plane"}
```

## Purpose
- function: F2 Process (`integration-map.md` §1): 200 kS/s mic PCM -> 1.5-4 kHz signal -> 200 kHz PWM duty stream.
- hub_for: {F1: ADF1 PB3/PB4 + PA5 supply, F3: TIM1, F4: ADC1_IN11 PA6, F6: TS PA2, F8: ADC4 PA4, F9: PA1, F10: USB FS PA11/PA12, F11: WKUP1 PA0, F12: TIM4_CH2 PB7, F13: I2C2 PB13/PB14 + EXTI PA15, F14: SWD + BOOT0 + TP7-TP10}
- must: D12 modes (Full, Transient-only, Off); D18 runtime (`sub-power.md`); self-noise <= ambient (§1.2.3, D11).

## Big picture
- pictures: `docs/learn/02-inside-the-chip.png` (one sample's path), `sim/out/nature/spectrograms.png` (algorithm B on Port Meadow bats).
```
LSE 32.768 kHz (Y1) -lock-> MSIS 48.005 MHz -/3-> 16.00 -x20-> VCO 320.03 -/4-> SYSCLK = HCLK = TIM1 clock 80.009 MHz
   ADF1 kernel HCLK -/2-> proc_ck 40 MHz -/10-> mic clock 4.0004 MHz -> CIC5 /5 -> RSFLT /4 -> 200.02 kS/s
   TIM1 centre-aligned, ARR 200 ------------------------------------------> PWM 200.02 kHz (one DMA burst per period)
HSI48 (+ CRS trim) -> USB FS 48 MHz            internal SMPS 3 MHz: VLXSMPS -> L1 -> VDD11 (core ~1.1-1.2 V)
```
- invariant: one crystal-locked clock; mic clock, sample rate, PWM rate are integer ratios (A3 §2); bridge-carrier leakage into the mic folds to 0 Hz (D14).
- SMPS: the only switcher D11 allows; 3 MHz typ in Ranges 1-3 (DS Table 35 p.160); no min/max published; lock to HCLK unpublished (open issue 9).
- runtime: CPU wakes every hop; GPDMA fills an SRAM ring from ADF1 and feeds TIM1 CCRs (`docs/learn/02-inside-the-chip.png`).

## Elements
### Parts (gen.py + MZ2 table; positions = footprint centres, probe of the board 2026-10-07; board mm, origin = outline top-left, x from the mic end; all on B)
| Ref | Part | LCSC · class | Board (B) | Why |
|---|---|---|---|---|
| U1 | STM32U575CIU6Q: ST Cortex-M33 MCU, 160 MHz max, FPU+DSP, 2 MB flash, 786 KB SRAM; C=48 pins, I=2 MB, U=UFQFPN 7x7, 6=-40-85 C, Q=SMPS pinout | C5271013 · Ext | (10.05, 5.4) r-90 | D5; ADF1; QFN kept over WLCSP for rework/probing (ECR-0018 MZD-2, O18/O19) |
| L1 | DFE201610E-2R2M=P2: Murata 2.2 µH shielded metal-alloy, 2.0x1.6x1.0 mm, ~140 mΩ, 2.4 A | C337891 · Ext | (15.65, 7.0) r-90 | SMPS coil; ST: 2.2 µH ±20 %, Isat > 0.5 A, DCR < 200 mΩ; differs from spec D5 L152 (issue 11); kept in MZ-2 (gen.py L91) |
| C8, C9 | 2.2 µF 0402 10 V X5R Samsung CL05A225KP5NSNC | C107369 · Ext | (15.4, 9.15), (4.9, 3.86) | VDD11 COUT pins 23 / 46; DS p.153 rated >= 10 V (O24); stay 0402 in MZ-2 (0201 ESR at 3 MHz unproven, gen.py L90) |
| C7 | 10 µF 10 V X5R 0603 Samsung CL10A106KP8NNNC | C19702 · Basic | (15.6, 10.6) | VDDSMPS CIN (DS: 10 µF, >= 10 V, ESR < 10 mΩ); 0603 kept (ST bulk rule) |
| C1, C2, C3 | 100 nF 10 V X5R 0201 Murata GRM033R61A104KE15D, one per VDD pin | C76934 · Basic | (5.48, 2.2) r90, (11.97, 10.95), (5.37, 9.5) r90 (pins 48+1 / 25 / 36) | AN5373 Rev 7; C1 also serves VBAT pin 1 (PER-06) |
| C4 | 10 µF 0603 bulk on +3V0 | C19702 · Basic | (9.95, 11.2) | AN5373: 10 µF typ |
| C5, C6 | 1 µF 25 V X5R 0402 (C52923, Basic, kept for DC bias) + 100 nF 0201 (C76934) on VDDA | Basic | (13.75, 0.73), (11.05, 0.83) | AN5373; C6 1.13 mm / C5 2.32 mm from VDDA pin 9; C6 tied straight to pins 9/8 (pre-route; issue 13 closed) |
| C10 | 100 nF 0201 on NRST | C76934 · Basic | (9.55, 0.83) r180 | AN5373; pin 7 -> C10 -> via -> TP3 pre-routed |
| Y1 | X1A0000610006: Epson FC-12M 32.768 kHz, 2.05 x 1.2 mm, CL 7 pF, ESR 90 kΩ (generic Device:Crystal symbol, MPN field) | C99009 · Ext | (3.9, 1.7) r90 | D16: pitch matched between unlinked pods; gm_crit ~0.98 µA/V (ECR-0018 MZV-08) |
| C11, C12 | 8.2 pF C0G 0201 Murata GRM0335C1H8R2BA01D | C161441 · Basic | (2.01, 2.4), (2.01, 1.0) | LSE load for CL 7 pF assuming ~3 pF stray (CL = C/2 + Cs); ±2 pF stray = ±46 ppm, inside RTC calibration ±487 ppm (MZV-08) |
| R1 | 10 k 0402, PH3-BOOT0 to GND; pad = DFU tack point | C25744 · Basic | (2.07, 3.85) | boot from flash (AN5373); 0402 kept as a hand hook (O18) |
- drop_in_alt: STM32U585CIU6Q (same die + crypto), C5271021, 15 in stock, $12.52 (spec D5, 2026-09-30).
- not_fitted_by_design: VBAT cap (shares C1), PA10 pull-up (ROM loader + R5, see pins), CHG_INT pull-up (PA15 internal), CC sense divider (gen.py L37-41).
- class/price: docs/build/bom.md (JLC API 2026-10-01; Y1 re-priced 2026-10-07T11:31Z: $0.2125, Extended, stock 23426).

### Pins (integration-map §4, regenerated for MZ-2 2026-10-07; AF per pin-contract.yaml; 42 of 48 used; unchanged from Rev G)
```yaml
supplies: {1: VBAT +3V0, 9: VDDA, 21: VDDSMPS, 25/36/48: VDD, 20: VLXSMPS, 23/46: VDD11, 8/22/24/35/47/49: GND (49 = exposed pad)}
clock_reset_boot: {3: PC14 LSE_IN, 4: PC15 LSE_OUT, 7: NRST (C10, TP3), 44: PH3-BOOT0 (N$1, R1)}
mic_ADF1_AF3: {15: PA5 MIC_VDD (GPIO supply), 39: PB3 ADF1_CCK0 -> N$2 -> R2 33R -> MIC_CLK, 40: PB4 ADF1_SDI0 MIC_DATA (+TP10)}
bridge_TIM1_AF1: {29: PA8 GA_P CH1, 17: PA7 GA_N CH1N, 31: PA10 GB_P CH3, 28: PB15 GB_N CH3N}   # ECR-0003
analog: {11: PA1 VBUS_SENSE, 12: PA2 TS, 14: PA4 VBAT_SENSE (ADC4, runs in Stop 2), 16: PA6 I_SENSE (ADC1_IN11)}
charger: {26: PB13 I2C2_SCL, 27: PB14 I2C2_SDA, 38: PA15 CHG_INT (internal pull-up, EXTI15)}
usb_debug_ui: {32: PA11 USB_DM, 33: PA12 USB_DP, 34: PA13 SWDIO (TP1), 37: PA14 SWCLK (TP2), 10: PA0 BTN WKUP1, 43: PB7 LED_K TIM4_CH2 open-drain}
debug_dots: {42: PB6 USART1_TX DBG_TX (TP7), 45: PB8 MDF1_CCK0 MDF_CCK (TP8), 19: PB1 MDF1_SDI0 MDF_SDI (TP9)}   # PER-12, O18
strap: {41: PB5 -> GND}   # ECR-0013 S1: a high on PB5 would arm the UCPD 5.1k pull-down on PA15
free_NC: {2: PC13 (keep static, ES §2.2.1), 5: PH0, 6: PH1, 13: PA3 (ADC1_IN8; FWSIM HWC-9 candidate for VSYS/MIC_VDD sense), 18: PB0, 30: PA9 (ROM USART1_TX)}   # gen.py L343-345
```
- cost_of_map: PB3 = mic clock -> no SWO (printf on TP7 instead); PB4 = NJTRST after reset, pull-up back-feeds the unpowered mic in reset/DFU/Off (pin-contract hazards PB4); PA6 = I_SENSE -> TIM1_BKIN on the same pin unusable as a digital break (issue 6).
- pin_hazards (pin-contract.yaml hazards, ECR-0013): PA15 cleared by PB5 strap; PB15 UCPD 5.1k pull-down armed by PB14 high (I2C_SDA idles high) -> holds GB_N OFF until UCPD_DBDIS (safe default); PB4 back-feed; PA2 driven high by ROM USART2_TX in DFU.

### Modes (D12 L218)
| Mode | Clock / range / regulator | Mic | Bridge | MCU draw | src |
|---|---|---|---|---|---|
| Full / Transient-only, alg. B | P80, Range 2, SMPS 3 MHz | on | on | 2.3 / 2.7 / 3.2 mA + periph 0.6-0.8 | `sim/checks/power.py` L27-28 |
| same, alg. A | P48 (MSIS direct), Range 3 | on | on | ~1.3-1.8 mA | A3 §5 |
| Idle listening (C9) | two plans (issue 4) | on | stopped | 0.5-1.0 mA (16 MHz run) or ~0.1 mA (Stop 2 + LPDMA) `[Low]` | power.py L39; A3 §1.3 |
| Off | Stop 2 on SMPS (asynchronous) | unpowered | stopped | 3.90 / 4.25 (RTC on LSE) / 8.55 µA | DS Table 58 p.183 |
| Docked (charge, DFU) | [TBD] | - | 0 (ECR-0009 proposed) | [TBD] | integration-map F9/F10 |

### Firmware
- state: no `.c/.h`, linker script, CMake (no `fw/`, checked 2026-10-02). Requirements: `docs/sim/firmware-emulation.yaml` (FWSIM-R1..; board facts only via pin-contract.yaml, FWSIM-R5).
- reference_models: `sim/dsp/pipeline.py` (float64 chain; models D2 fallback decimation 400 kS/s + 31-tap half-band, not ADF D1), `sim/dsp/run_phase1.py`, `sim/dsp/nature_demo.py` (3 WAVs in `sim/out/nature/`), `sim/checks/{idle_detector,ntf_compare,pwm_ultrasonic_leak,deadtime_switching,power}.py`, `sim/e2e/`.
```
ADF1 -GPDMA-> SRAM ring 200 kS/s -IRQ per hop-> CPU
  B: 256-pt real FFT -> 28-32 log bands 20-85 kHz -> mic EQ -> floor / transient gate -> envelopes -> oscillator bank 12.5 kS/s
  A: x LO -> low-pass -> /16 -> 12.5 kS/s -> envelope squelch
  -> volume (D3) -> ceiling (D17) -> x16 interpolate -> 3rd-order shaper + TPDF dither -GPDMA burst-> TIM1 CCR1..CCR3, 200 kHz
Control: EXTI PA0, I2C2 + EXTI PA15, ADC1/ADC4, TIM4 LED, USB FS (CDC self-test, ROM DFU), SWD, USART1_TX printf PB6
```
| | A: heterodyne | B: log frequency compression |
|---|---|---|
| method | out = in - LO, one band, LO tunable (model 38 kHz) | channel vocoder; f_out = 1.5 kHz x (4/1.5)^u, u = ln(f/20k)/ln(85k/20k) (`pipeline.py` map_freq) |
| CPU at 80 MHz (C2, M4F counts) | 19-39 Mcycle/s = 23-48 % | 44-65 Mcycle/s = 55-81 % |
| clock | 48-64 MHz | 80 MHz |
| owner listening (NEXT.md §2, 2026-09-30) | "informative but aesthetically poor": fallback | transient-only good for noisy places; full acceptable |
| status | fallback only if B won't fit (D12 v0.11) | leading; 7-WAV real-recording set requested (NEXT.md §2), not made |
- toolchain (D15 L272): C11, arm-none-eabi-gcc, CMake, CMSIS + ST LL, CMSIS-DSP; CubeMX read-only.

### Firmware rules (each fixed by the cited source)
```yaml
FW-1:  "raise voltage range before REGSEL=1; never Range 4 on the SMPS"   # A3 §4; DS Table 35 note
FW-2:  "Stop 2 stays on the SMPS"                                          # ES §2.2.22 (LDO + partial RAM can lock the part)
FW-3:  "MSI PLL unlock IRQ: disable, re-enable PLL mode"                   # ES0499 Rev 12
FW-4:  "PLL2/PLL3/HSI48/SHSI off and RDY clear before Stop 2"              # ES §2.2.5
FW-5:  "LSEDRV = high"                                                     # ES §2.2.3/§2.2.16; B-parts §4
FW-6:  "ADF dividers only while stopped; even CCKDIV+1; mic starts in standard mode"   # sub-audio-in.md
FW-7:  "TIM1: OSSI + OIS/OISN idle levels before MOE; faults via BKIN, never ocref_clr" # ES0499 Rev 11
FW-8:  "ADC ref = VDDA = 3.0 V LDO (no VREF+ pin): calibrate against VREFINT"           # A3 §3
FW-9:  "diff RM0456 Rev 7 vs Rev 6 (PWR, RCC, GPIO, GPDMA, ADC4, TIM1) before coding"  # datasheet-provenance.md
FW-10: "TIM1 DMA burst DBA=CCR1, DBL=2 -> CCR1, CCR2 (unused), CCR3 per update"        # ECR-0003 L12
FW-11: "boot stub, first: set PWR_UCPDR.UCPD_DBDIS (releases PB15 GB_N, PA15); then PA15 pull-up + EXTI15 falling"   # pin-contract hazards; ECR-0013 S1/S2; gen.py L37-38
FW-12: "before Off: PB4 analog, no pull (mic back-feed); reset and ROM DFU back-feed not firmware-fixable"   # pin-contract hazards PB4
FW-13: "boot stub disables U3 charger watchdog before DFU jump"                         # 00-whole.md risk 5; sub-power.md
FW-14: "frequency plan: LED PWM f = n x fs_out or outside 20-96 kHz; mic divider chosen with alias.fs_pdm_scan (/20: SMPS h4 sits 1.35 kHz from 3 x fs_pdm; /18 no coincidence k<=24)"   # docs/sim/layout-noise.yaml LN-R11, LF-5, LF-6
```
- ROM_DFU_pin_states (AN2606 Rev 69 Table 199, tabulated in `sub-debug-test.md`; simplification-study.md L290): PA10 = USART1_RX with pull-up -> GB_P high, P-FET off (R5 holds it too); PA9 = USART1_TX -> NC; PA2 driven high (TS "cold", charging pauses).

## Interfaces
| To | Nets / pins | Peripheral / firmware | Relation |
|---|---|---|---|
| sub-audio-in | MIC_VDD PA5; PB3 -> N$2 -> R2 -> MIC_CLK; MIC_DATA PB4 (+TP10) | GPIO supply, ADF1 (Stop-2 capable), GPDMA; MDF1 fallback via TP8/TP9 hand-wire | R-AUDIO-PROC |
| sub-output | GA_P PA8, GA_N PA7 (CH1/CH1N); GB_P PA10, GB_N PB15 (CH3/CH3N), all AF1; I_SENSE PA6 | TIM1 complementary PWM + dead time (12.5 ns steps at P80); ADC1_IN11 self-test | R-PROC-OUT |
| sub-power | +3V0 on VDD/VDDA/VDDSMPS/VBAT; VBAT_SENSE PA4; TS PA2; I2C2 PB13/PB14; CHG_INT PA15; PB5 strap | ADC4 (Stop 2), I2C2, EXTI15; MCU = largest +3V0 load | R-PWR-PROC |
| sub-dock-usb | USB_DP PA12, USB_DM PA11, VBUS_SENSE PA1; CC not sensed (R18 Rd + J12 stay; ILIM by enumeration) | USB FS on HSI48 + CRS (DS §3.12 p.51); ROM DFU; boot stub (FW-11, FW-13) | R-PROC-DOCK |
| sub-ui | BTN PA0, LED_K PB7 | WKUP1/EXTI0; TIM4_CH2 open-drain PWM (FW-14) | R-PROC-UI |
| sub-debug-test | SWDIO PA13 (TP1), SWCLK PA14 (TP2), NRST (TP3), BOOT0 N$1 (R1 pad), DBG_TX PB6 (TP7), MDF_CCK PB8 (TP8), MDF_SDI PB1 (TP9), MIC_DATA (TP10) | SWD, ROM bootloader, USART1_TX printf, USB self-test (O15) | R-PROC-DEBUG |
| reg-board | U1, SMPS loop (L1, C7, C8/C9), Y1 + C11/C12 all on B; EP GND vias to In1; +3V0 from the In2 plane; I2C_SCL (pin 26) leaves on an 8.98 mm In2 bridge | SMPS loop, decoupling distances (Key numbers); LSE B only, 0 vias (issue 14 closed) | R-PROC-BOARD, R-SMPS-BOARD, R-CLOCK-BOARD |

## Constraints
- D5 L131: STM32U575CIU6Q. D11 L210: only the core SMPS switches; fixed frequency; owner listening test E11 (full chain, 16 MHz idle, Stop 2); L214: shielded, low-magnetostriction inductor.
- D14 L241 / A3 §2: every rate an integer ratio of HCLK; mic divider even; SYSCLK change restarts the ADF.
- D16 L285 crystal reference. D12 L218 modes. D15 L272 toolchain. D17 L293 fixed ceiling, no clicks.
- DS §5.1.6 p.153: COUT 2 x 2.2 µF ±20 %, ESR < 20 mΩ at 3 MHz, rated >= 10 V; CIN 10 µF, ESR < 10 mΩ, >= 10 V; L 2.2 µH.
- package UFQFPN48-SMPS: no PB2, PB9, PB10, PB12; no VDDUSB/VREF+ pins (A3 §3; datasheet-provenance.md L48).
- O25: Claude lays out, owner reviews (supersedes O14 for rev 1); O26 Phase 2 internals first; O27 thin > short > long. O20 L646: test access must not cost size.
- O18 L644: rev 1 fails informatively: spare pins to pads (PB6/PB8/PB1 on dots TP7-TP9, on B; 6 pins still NC, issue 12), board measures itself, every uncertain value a firmware knob (FWSIM-R6), DFU most-verified. O19 L645: after rev 1 changes via firmware only.
- ECR-0009 (proposed): no exciter output while VBUS present, ceiling independent of volume, pop-free start; conflicts with docked self-test (00-whole.md risk 6).

## Key numbers
| Quantity | Value | src | date |
|---|---|---|---|
| JLC stock U1 | 8, $8.93 | `docs/build/bom.md` (JLC API) | 2026-10-01 |
| SYSCLK P80 / range | 80.009 MHz / Range 2 (<= 110 MHz) | A3 §2 | 2026-09-30 |
| MSIS locked | 48.005 MHz = 1465 x LSE (+107 ppm, same both sides) | A3 §2 | 2026-09-30 |
| SMPS switching | 3 MHz typ (VDD > 1.9 V), Ranges 1-3; no tolerance published | DS Table 35 p.160 | Jul 2024 |
| SMPS ripple | ~110 mA p-p (108 derived, L 2.2 µH, Vout 1.15 V) | A3 §4; layout-noise.yaml A01 | 2026-09-30 |
| run current 80 MHz on SMPS | ~3.3 mA flat out (~41 µA/MHz), interpolated | A3 §5 (DS Rev 8 Table 39) | 2026-09-30 |
| MCU, alg. B duty-cycled | 2.3 / 2.7 / 3.2 mA | power.py L27 | 2026-09-30 |
| Stop 2 on SMPS, 3.0 V | 3.90 / 4.25 / 8.55 µA | DS Table 58 | Jul 2024 |
| LSE margin (FC-12M) | gm_crit ~0.98 vs Gmcritmax 2.7 µA/V (high drive) = ~2.8x (FC-135 was 2.16 = 1.25x) | ECR-0018 MZV-08; DS Table 80 | 2026-10-03 |
| CPU alg. B | 55-81 % of 80 MHz (M4 counts, ±50 %) | C2-cpu-budget.md | 2026-09-30 |
| CPU idle detector rev 2 | ~3.4 Mcycle/s, ~21 % at 16 MHz | power.py L38; spec §7 | 2026-09-30 |
| latency target | <= 20 ms end to end | spec §5.3 | 2026-09-30 |
| VDD11 pin 46 / pin 23 to nearest 2.2 µF | 1.25 mm (C9) / 2.07 mm (C8) | pcbnew probe of board, pad centres | 2026-10-07 |
| VDDSMPS pin 21 to C7 / VLXSMPS copper | 4.17 mm / 2.22 mm, B only, no via | same probe | 2026-10-07 |
| VDD pin 48 / VBAT pin 1 to C1 (+3V0 pad) | 1.14 / 1.90 mm centre-to-centre (C1 +3V0 pad tied to pin 48, both pins to one corner via); PER-06 rule (pad edge-to-edge <= 1.5, place_r2.py `_gap`) PASS in hw/pod/draft_r2/out/check.json | board probe 2026-10-07 (20bd842); place_r2.py NEAR | 2026-10-07 |
| VDD pin 25 / pin 36 to nearest cap | 1.98 mm (C2) / 2.17 mm (C3) | same probe | 2026-10-07 |
| VDDA pin 9 to C5 / C6 | 2.32 / 1.13 mm (+3V0 pad centres; was 9.22 / 8.78 before 20bd842) | place_r2 --probe | 2026-10-07 |
| LSE copper | LSE_IN B 7.72 mm, LSE_OUT B 7.43 mm, 0 vias (pre-routed; was F+B with 2 vias each) | place_r2 --probe | 2026-10-07 |
| L1 to mic U2 / to the mic port | 13.04 mm centre-centre, same face (B) / 12.87 mm nearest pad edge | same probe | 2026-10-07 |
| I2C_SCL route | F 9.89 + B 7.18 + In2 8.98 mm, 5 vias (inner bridge 2026-10-07) | same probe; ECR-0018 log | 2026-10-07 |
| noise, MCU aggressors (Phase-2 board, both planes modelled) | LN-M01 mic supply: A05_CPU_HOP 21.875 kHz 46.5 nominal / 26.5 pessimistic dB (PASS, sign-off >= 10); worst-PSRR case A01_SMPS_IN 28.04 MHz -> 38.96 kHz 14.0 dB; A02_SMPS_VDD11 >= 96 dB; LN-M04 ADC ref ripple 0.127 mV pk (<= 0.37) at hop 1562 Hz | `sim/noise/out_r2/budget.json` (board sha da4e8b13, valid, 195/195 pads) | 2026-10-07 |

## Open issues (IDs kept stable; other docs cite them)
1. CLOSED Rev G (ECR-0017, O24): C8/C9 now C107369 10 V. Was: C8/C9 6.3 V (C12530) vs DS §5.1.6 rated >= 10 V; `.pcba-workflow/sourcing-lock.csv` L9 still RECOMMENDED C107369 10 V. Options: (a) C107369 Extended 0402 10 V; (b) Basic 0603 16 V C23630 (2.5x area, conflicts O20); (c) keep, accept deviation. Recommend (a): explicit datasheet line, same footprint, ~$3/order for one more Extended type (`docs/build/bom.md`). Owner.
2. MCU stock 8 at JLC (2026-10-01): reserve before order or plan U585 drop-in (15 in stock, +$3.59). ECR-0008.
3. (closed in Phase 2) SMPS layout: VDD11 pin 46 -> C9 1.25 mm, pin 23 -> C8 2.07 mm, VLXSMPS 2.22 mm, CIN C7 4.17 mm (probe 2026-10-07). Residual: C7 > 2 mm from pin 21 (DS asks 'as close as possible'); owner review (O25).
4. Idle mode: 16 MHz Range 3 run (power.py) vs Stop 2 + ADF + LPDMA (A3 §1.3; Stop 2 makes the SMPS asynchronous while the mic listens). Closes: pick one; E11 listens, E4 measures. FWSIM variant IDLE_PLAN.
5. CPU budget is an L452 estimate (M4 counts, 2nd-order shaper, 32-48 oscillators) vs design (M33, 3rd-order, 28-32 bands, ADF removes the 5-10 Mcycle/s half-band). 800 kHz PWM option (MP-01, sub-output.md) not costed. Closes: re-cost C2 for U575; benchmark on board 1 (S3); FWSIM cycle_budget.
6. No hardware bridge-fault input. TIM1_BKIN on this package only on PA6 (ST open pin data `STM32U575CIUxQ.xml`, 2026-10-02), which carries I_SENSE (31 mV at 315 mA, integration-map §5: below a digital threshold); TIM1_BKIN2 only on PA11 (USB). Internal break routing: see the research note at the end of this item. Project rule (from ES0499 2.16.2): faults via the break function, never ocref_clr. Closes: decide whether a hardware cut-off is needed. **Research done 2026-10-07 (RM0456 Rev 7, March 2026, local copy SHA-256 prefix 6edaaaae0c5d57c5; ES0499 Rev 12; ST open pin data):** TIM1 break inputs on the U575 = TIM1_BKIN pin (PA6 only), comp1_out, comp2_out and **mdf1_break0** (RM0456 Table 541, tim_brk_cmp7). PA6 is not a COMP input on this package (COMP inputs: PA2, PB4, PB6 INP; PB1, PB3, PB7 INM), so COMP is out without a rewire. **No-board-change path:** ADC1 converts PA6 (ADC1_IN11) continuously and streams to MDF1 (RM0456 §16.3.18: adc1_dat → mdf1_adcx_dat, U575 listed; DATSRC in MDF_DFLTxCICR); the MDF out-of-limit detector (window, both signs, so the negative half of i·(2d−1) is caught) asserts mdf_break0 (BKOLD in MDF_OLDxCR) → TIM1 BKCMP7E: a real break (MOE cleared, outputs to their programmed idle state) with no CPU in the loop, latched until firmware clears it. Works in Run and Sleep (RM0456: ADC→MDF 'available down to Sleep'), which is where playback runs. Rejected: ADC1 analog watchdog → tim_etr8 → ocref_clr (exists, but ES0499 2.16.2 + project rule: never ocref_clr for faults). Constraints: ADC1 must be dedicated to PA6 while the guard runs (MDF sees every ADC1 conversion): VBAT moves to ADC4_IN9 (PA4); TS (PA2) and VBUS sense (PA1) are ADC1-only but matter while docked, when ECR-0009 already stops output. Cost: the always-on ADC1 current already quoted (+0.15–0.34 mA) plus MDF1 kernel clock [TBD E4]. Firmware-only; the decision (always-on vs self-test-only) stays with the owner (sub-output issue 6).
7. ROM-DFU boot stub and self-test firmware (O15) have no design note; `docs/research/self-test-firmware.md` (cited by spec O15 L641) does not exist; requirements partly in FWSIM (boot_dfu_handoff).
8. USB VDDUSB (bonded to VDD here): DS Table 150 p.304 3.0-3.6 V, functional to 2.7 V with degraded characteristics; +3V0 min 2.955 V; AN2606 3.3 V note is boilerplate (`audit-datasheet-claims.md` row 6). No LDO change; bench-test DFU at 2.95 V. Owned by sub-dock-usb.
9. Unverified: SMPS 3 MHz synchronous or free-running, and its tolerance (LF-5 whine risk with /20 mic divider); 80 MHz current interpolated (E4).
10. Missing PNGs: clock tree, MCU pin map (text only).
11. SMPS inductor differs from spec: D5 L152 names Murata LQM21PN2R2MGHL (0805, C341781); Rev F/G and MZ-2 use DFE201610E-2R2M=P2 (C337891); D11 L214 asks low-magnetostriction, DFE magnetostriction unpublished (sourcing lock). Closes: owner (spec or schematic); E11 listens for whine incl. dock magnets near L1 (`sub-dock-usb.md`; 00-whole.md risk 7).
12. O18 "spare pins to pads": PC13, PH0, PH1, PA3, PA9, PB0 are NC with no copper (gen.py L343-345). PA3 = ADC1_IN8 could read VSYS or MIC_VDD (FWSIM HWC-9). Trade-off vs O20 size; not decided [TBD].

13. (closed 2026-10-07, 20bd842) VDDA caps: C6 100 nF sits over pins 8/9 with straight stubs (1.13 mm), C5 1 µF 2.32 mm; C3 moved to VDD pin 36. place_r2 NEAR is per pin now (C6/C5 `U1.9`, C2 `U1.25`, C3 `U1.36`). LN-M04 0.127 mV unchanged.
14. (closed 2026-10-07, 20bd842) LSE: Y1 at (3.9, 1.7), C11/C12 at x 2.01; pins 3/4 pre-routed along the top strip on B, 0 vias, 7.72 / 7.43 mm (was 7.9 / 6.9 mm with 2 vias each). Guard: In1 GND plane under the whole run; nothing else in the strip between Y1 and pin 4. Load-error residue stays firmware-trimmable (MZV-08).

## Before you change this, check
- pin moves: integration-map §4 (one job per pin); `tools/checks/interfaces.py pins` (AF per pin-contract); ADF only PB3/PB4; TIM1 complementary pairs; ADC4 pins for Stop 2; WKUP1 = PA0; USB fixed PA11/PA12; pin-contract hazards (PA15, PB15, PB4, PA2); ROM loader pin states (AN2606 Table 199); related docs sub-audio-in, sub-output, sub-power, sub-dock-usb, sub-ui, sub-debug-test.
- clock changes: D14 integer ratios, even mic divider, TIM1 ARR and dead-time tick, HSI48 for USB, D16 crystal margin, layout-noise fs_pdm_scan (LN-R11).
- SMPS parts or range/mode policy: DS §5.1.6, D11, E11, FW-1..FW-4.
- algorithm, PWM rate, clock per mode: issue 5, `sub-power.md` budget, MP-01 (`sub-output.md`).
- MCU swap: U585 drop-in; anything else redoes A3.
- run integration-map §10 cross-check; `python3 tools/plm.py impact SUB-PROCESSING`; afterwards `tools/plm.py status`.
- B-face crowding: any U1-area move must keep the 0.6 mm escape ring (place_r2.py ESCAPE L55) and re-run `place_r2.py check` (owner/lead only; never as a parallel agent).

## Reference design (Rev F/G, `ULTRASONIC_DESIGN=revg`)
- U1 + SMPS + Y1 on F of the 34 x 13 board hw/pod/draft_r1/pod_r1_routed.kicad_pcb, U1 at (13.03, 6.53); Y1 Epson FC-135 Q13FC1350000400 3.2 x 1.5, CL 12.5 pF (C32346) + 15 pF 0402 C0G (C1548); 100 nF 0402 X7R (C1525).
- Draft probe 2026-10-02: VDD11 pin 46 to C9 10.2 mm (LD-05), CIN 4.6 mm, switch node 6.7 mm; C1 1.12 / 1.43 mm; LSE F only (4.5 / 8.0 mm); L1 16.3 mm from U2 on the opposite face; 2 unconnected (SWCLK, LED_K); noise LN-M01 23.1 dB, LN-M04 0.199 mV (sha e159bccb).
