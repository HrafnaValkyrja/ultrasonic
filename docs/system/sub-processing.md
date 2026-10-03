# SUB-PROCESSING: MCU, core SMPS, clocks, firmware
Rev F 2026-10-02: leg B on TIM1_CH3/CH3N PA10/PB15 (ECR-0003); R11, R19, C20 removed; PB5 strapped to GND; PA15 internal pull-up; TP7-TP10 debug/MDF dots; free pins now PC13 PH0 PH1 PA3 PA9 PB0.

```yaml
status: {schematic: "Rev F (Phase 1 logical simplification, package B3), hw/pod/gen.py docstring L35-60", layout: "draft routed 2026-10-02 (hw/pod/draft_r1/summary.json: 687 tracks, 118 vias, 2 unconnected, DRC 19 = courtyard overlaps only); owner layout session pending (O14)", firmware: "none written; requirements only in docs/sim/firmware-emulation.yaml (FWSIM); Python reference models in sim/dsp", updated: 2026-10-02}
item: SUB-PROCESSING   # docs/system/plm/items.yaml
src_of_truth: ["hw/pod/gen.py L133-163 (MCU, SMPS, LSE)", "gen.py L282-291 (TP7-TP10, spare pins)", "gen.py L222 (PB5 strap)", "docs/system/pin-contract.yaml (signal per net)", "docs/system/integration-map.md §4 (generated pin map)", "docs/research/A3-u575-plan.md (chip plan)", "docs/spec.md D5 L131, D11 L210, D12 L218, D14 L241, D15 L272, D16 L285, D17 L293, D18 L297, O18 L644, O19 L645"]
owner_decisions: [O6 (resolved -> D11), O9, O14, O15, O18 (fail informatively), O19 (changes via firmware only), O20 (final size, test access must not cost size)]
open_ecrs: {ECR-0003: "implemented in Rev F gen.py; file status still 'proposed'", ECR-0005: "+3V0 peak 326 mA > U4 300 mA (MCU shares the rail)", ECR-0008: "MCU reserve, 8 at JLC", ECR-0009: "fw interlocks: no output while docked, ceiling", ECR-0010: "fw tested before board order", ECR-0013: "pin hazards: S1 PB5 strap done in Rev F, S2 UCPD_DBDIS fw, PB4 back-feed, PA2 in DFU"}
checks: ["python3 tools/checks/interfaces.py [pins] (2026-10-02: WARN, 3 hazards: GB_N PB15, MIC_DATA PB4, TS PA2, all ECR-0013)", "python3 tools/plm.py impact SUB-PROCESSING"]
abbr: {ADF1: "audio digital filter (PDM->PCM, runs in Stop 2)", MDF1: "multi-function digital filter (ADF fallback)", SMPS: "MCU-internal core buck", LSE: "32.768 kHz crystal oscillator", MSIS: "multi-speed internal RC, PLL-locked to LSE", P80/P48: "clock plan 80.009 MHz / 48 MHz", hop: "DSP frame 128 samples = 0.64 ms", DS: "ST DS13737 Rev 10 (Jul 2024)", ES: "ST ES0499 errata", RM: "ST RM0456 Rev 7", UCPD: "USB-C PD block; dead-battery 5.1k pull-downs at reset", draft: "hw/pod/draft_r1/pod_r1_routed.kicad_pcb"}
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
### Parts (gen.py L133-163; positions from draft, probe 2026-10-02, board coords mm, origin = outline top-left)
| Ref | Part | LCSC · class | Draft | Why |
|---|---|---|---|---|
| U1 | STM32U575CIU6Q: ST Cortex-M33 MCU, 160 MHz max, FPU+DSP, 2 MB flash, 786 KB SRAM; C=48 pins, I=2 MB, U=UFQFPN 7x7, 6=-40-85 C, Q=SMPS pinout | C5271013 · Ext | F (13.03, 6.53) | D5; ADF1; ~40-45 µA/MHz on SMPS (DS §7) |
| L1 | DFE201610E-2R2M=P2: Murata 2.2 µH shielded metal-alloy, 2.0x1.6x1.0 mm, ~140 mΩ, 2.4 A | C337891 · Ext | F (20.42, 10.67) | SMPS coil; ST: 2.2 µH ±20 %, Isat > 0.5 A, DCR < 200 mΩ (B-parts-selection.md §3); differs from spec D5 L152 (issue 11) |
| C8, C9 | 2.2 µF 0402 10 V X5R CL05A225KP5NSNC (Rev G) | C107369 · Ext | F (17.62, 11.53), (20.32, 8.60) | VDD11 COUT; DS13737 Rev 10 p.153 rated >= 10 V: met since Rev G (ECR-0017, O24) |
| C7 | 10 µF 10 V X5R 0603 (Samsung CL10A106KP8NNNC) | C19702 · Basic | F (18.02, 6.53) | VDDSMPS CIN (DS: 10 µF, >= 10 V, ESR < 10 mΩ) |
| C1-C3 | 100 nF 16 V X7R 0402 (Samsung CL05B104KO5NNNC), one per VDD pin | C1525 · Basic | F; C1 (9.43, 1.88) | AN5373 Rev 7; C1 also serves VBAT pin 1 (PER-06: <= 1.5 mm from pins 1 and 48; probe 1.43 / 1.12 mm) |
| C4 | 10 µF 0603 bulk on +3V0 | C19702 · Basic | F (18.82, 3.53) | AN5373: 10 µF typ, 4.7 µF min after DC bias |
| C5, C6 | 1 µF 25 V X5R + 100 nF on VDDA | C52923, C1525 · Basic | F (8.33, 10.21), (7.33, 10.21) | AN5373 |
| C10 | 100 nF on NRST | C1525 · Basic | F (8.33, 7.91) | AN5373 |
| Y1 | Q13FC1350000400: Epson FC-135 32.768 kHz, 3.2x1.5 mm, CL 12.5 pF | C32346 · Basic | F (6.62, 4.23) | D16: pitch matched between unlinked pods |
| C11, C12 | 15 pF C0G 0402 (Fenghua 0402CG150J500NT) | C1548 · Basic | F | LSE load (B-parts §4) |
| R1 | 10 k, PH3-BOOT0 to GND; pad = DFU tack point | C25744 · Basic | F (17.02, 1.62) | boot from flash (AN5373) |
- drop_in_alt: STM32U585CIU6Q (same die + crypto), C5271021, 15 in stock, $12.52 (spec D5, 2026-09-30).
- not_fitted_by_design: VBAT cap (shares C1), PA10 pull-up (ROM loader + R5, see pins), CHG_INT pull-up (PA15 internal), CC sense divider (gen.py L37-40).

### Pins (integration-map §4, generated 2026-10-02; AF per pin-contract.yaml; 42 of 48 used)
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
free_NC: {2: PC13 (keep static, ES §2.2.1), 5: PH0, 6: PH1, 13: PA3 (ADC1_IN8; FWSIM HWC-9 candidate for VSYS/MIC_VDD sense), 18: PB0, 30: PA9 (ROM USART1_TX)}   # gen.py L290
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
| reg-board | U1 + SMPS on F; exposed pad GND vias to In1 | SMPS loop, decoupling distances (Key numbers) | R-PROC-BOARD |

## Constraints
- D5 L131: STM32U575CIU6Q. D11 L210: only the core SMPS switches; fixed frequency; owner listening test E11 (full chain, 16 MHz idle, Stop 2); L214: shielded, low-magnetostriction inductor.
- D14 L241 / A3 §2: every rate an integer ratio of HCLK; mic divider even; SYSCLK change restarts the ADF.
- D16 L285 crystal reference. D12 L218 modes. D15 L272 toolchain. D17 L293 fixed ceiling, no clicks.
- DS §5.1.6 p.153: COUT 2 x 2.2 µF ±20 %, ESR < 20 mΩ at 3 MHz, rated >= 10 V; CIN 10 µF, ESR < 10 mΩ, >= 10 V; L 2.2 µH.
- package UFQFPN48-SMPS: no PB2, PB9, PB10, PB12; no VDDUSB/VREF+ pins (A3 §3; datasheet-provenance.md L48).
- O14: layout together; draft positions not final. O20 L646: test access must not cost size.
- O18 L644: rev 1 fails informatively: spare pins to pads (Rev F: PB6/PB8/PB1 on dots TP7-TP9; 6 pins still NC, issue 12), board measures itself, every uncertain value a firmware knob (FWSIM-R6), DFU most-verified. O19 L645: after rev 1 changes via firmware only.
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
| LSE margin | gm_crit 2.16 vs Gmcritmax 2.7 µA/V (high drive) = 1.25x | B-parts §4 (DS Table 80) | 2026-09-30 |
| CPU alg. B | 55-81 % of 80 MHz (M4 counts, ±50 %) | C2-cpu-budget.md | 2026-09-30 |
| CPU idle detector rev 2 | ~3.4 Mcycle/s, ~21 % at 16 MHz | power.py L38; spec §7 | 2026-09-30 |
| latency target | <= 20 ms end to end | spec §5.3 | 2026-09-30 |
| draft: VDD11 pin 46 to nearest 2.2 µF | 10.2 mm (C9); pin 23 to C8 2.4 mm | pcbnew probe of draft (pad centres) | 2026-10-02 |
| draft: VDDSMPS pin 21 to C7 / VLXSMPS copper | 4.6 mm / 6.7 mm | same probe | 2026-10-02 |
| draft: VDD pin 48 / VBAT pin 1 to C1 | 1.12 / 1.43 mm centre-to-centre (pad edges 0.42 / 1.02 mm, reg-board; PER-06 <= 1.5 met on both metrics) | same probe | 2026-10-02 |
| draft: VDDA pin 9 to C5 / C6 | 3.2 / 3.7 mm | same probe | 2026-10-02 |
| draft: LSE copper | LSE_IN 4.5 mm, LSE_OUT 8.0 mm, F only | same probe | 2026-10-02 |
| draft: L1 to mic U2 | 16.3 mm centre-centre, opposite faces | same probe | 2026-10-02 |
| draft: unrouted on U1 nets | SWCLK -> TP2, LED_K -> J8 (layout-session items) | `hw/pod/draft_r1/drc.json` | 2026-10-02 20:07 |
| noise, MCU aggressors on Rev F draft | LN-M01 worst = A05_CPU_HOP 21.875 kHz, 23.1 dB pessimistic (pass >= 0); SMPS A01, A02 margins [TBD]; LN-M04 ADC ref ripple 0.199 mV pk (<= 0.37) at hop 1562 Hz | `sim/noise/smoke.sh on hw/pod/draft_r1/pod_r1_routed.kicad_pcb (sha e159bccb, 2026-10-02 21:20)` | 2026-10-02 21:20 |

## Open issues (IDs kept stable; other docs cite them)
1. CLOSED Rev G (ECR-0017, O24): C8/C9 now C107369 10 V. Was: C8/C9 6.3 V (C12530) vs DS §5.1.6 rated >= 10 V; `.pcba-workflow/sourcing-lock.csv` L9 still RECOMMENDED C107369 10 V. Options: (a) C107369 Extended 0402 10 V; (b) Basic 0603 16 V C23630 (2.5x area, conflicts O20); (c) keep, accept deviation. Recommend (a): explicit datasheet line, same footprint, ~$3/order for one more Extended type (`docs/build/bom.md`). Owner.
2. MCU stock 8 at JLC (2026-10-01): reserve before order or plan U585 drop-in (15 in stock, +$3.59). ECR-0008.
3. SMPS layout (draft): VDD11 pin 46 has no cap within 10 mm (LD-05); CIN 4.6 mm from VDDSMPS; switch node 6.7 mm. Closes: layout session (O14).
4. Idle mode: 16 MHz Range 3 run (power.py) vs Stop 2 + ADF + LPDMA (A3 §1.3; Stop 2 makes the SMPS asynchronous while the mic listens). Closes: pick one; E11 listens, E4 measures. FWSIM variant IDLE_PLAN.
5. CPU budget is an L452 estimate (M4 counts, 2nd-order shaper, 32-48 oscillators) vs design (M33, 3rd-order, 28-32 bands, ADF removes the 5-10 Mcycle/s half-band). 800 kHz PWM option (MP-01, sub-output.md) not costed. Closes: re-cost C2 for U575; benchmark on board 1 (S3); FWSIM cycle_budget.
6. No hardware bridge-fault input. TIM1_BKIN on this package only on PA6 (ST open pin data `STM32U575CIUxQ.xml`, 2026-10-02), which carries I_SENSE (31 mV at 315 mA, integration-map §5: below a digital threshold); TIM1_BKIN2 only on PA11 (USB). Internal COMP -> break routing [TBD: RM0456 TIM1 break sources]. ES requires faults via BKIN. Closes: decide whether a hardware cut-off is needed.
7. ROM-DFU boot stub and self-test firmware (O15) have no design note; `docs/research/self-test-firmware.md` (cited by spec O15 L641) does not exist; requirements partly in FWSIM (boot_dfu_handoff).
8. USB VDDUSB (bonded to VDD here): DS Table 150 p.304 3.0-3.6 V, functional to 2.7 V with degraded characteristics; +3V0 min 2.955 V; AN2606 3.3 V note is boilerplate (`audit-datasheet-claims.md` row 6). No LDO change; bench-test DFU at 2.95 V. Owned by sub-dock-usb.
9. Unverified: SMPS 3 MHz synchronous or free-running, and its tolerance (LF-5 whine risk with /20 mic divider); 80 MHz current interpolated (E4).
10. Missing PNGs: clock tree, MCU pin map (text only).
11. SMPS inductor differs from spec: D5 L152 names Murata LQM21PN2R2MGHL (0805, C341781); Rev F uses DFE201610E-2R2M=P2 (C337891); D11 L214 asks low-magnetostriction, DFE magnetostriction unpublished (sourcing lock). Closes: owner (spec or schematic); E11 listens for whine incl. dock magnets near L1 (`sub-dock-usb.md`; 00-whole.md risk 7).
12. O18 "spare pins to pads": PC13, PH0, PH1, PA3, PA9, PB0 are NC with no copper (gen.py L290). PA3 = ADC1_IN8 could read VSYS or MIC_VDD (FWSIM HWC-9). Trade-off vs O20 size; not decided [TBD].

## Before you change this, check
- pin moves: integration-map §4 (one job per pin); `tools/checks/interfaces.py pins` (AF per pin-contract); ADF only PB3/PB4; TIM1 complementary pairs; ADC4 pins for Stop 2; WKUP1 = PA0; USB fixed PA11/PA12; pin-contract hazards (PA15, PB15, PB4, PA2); ROM loader pin states (AN2606 Table 199); related docs sub-audio-in, sub-output, sub-power, sub-dock-usb, sub-ui, sub-debug-test.
- clock changes: D14 integer ratios, even mic divider, TIM1 ARR and dead-time tick, HSI48 for USB, D16 crystal margin, layout-noise fs_pdm_scan (LN-R11).
- SMPS parts or range/mode policy: DS §5.1.6, D11, E11, FW-1..FW-4.
- algorithm, PWM rate, clock per mode: issue 5, `sub-power.md` budget, MP-01 (`sub-output.md`).
- MCU swap: U585 drop-in; anything else redoes A3.
- run integration-map §10 cross-check; `python3 tools/plm.py impact SUB-PROCESSING`; afterwards `tools/plm.py status`.
