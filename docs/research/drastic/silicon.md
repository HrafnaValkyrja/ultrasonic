# drastic/silicon: silicon integration lane (can chips collapse blocks and shrink the pod?)

```yaml
id: DRS-SI
doc: docs/research/drastic/silicon.md
date: 2026-10-03 ~01:20 EDT (05:20Z)
status: research note, lane "silicon" of the drastic-size workflow. NO spec/board/schematic edit, not committed. Time-boxed (~25 min): see missing[] at the end.
conf: "[V src date] verified primary source | [E] estimate (method named) | [T] TBD / unverified"
inputs_read: [docs/research/miniaturization-prelim.md (BL-1..BL-7, MZM-*), docs/research/mini/packages.md, area-model.md, pcb-tech.md (grep), docs/research/tws-power-size.md (cell table, levers, do-not-copy), sim/checks/power.py (run 2026-10-03T05:15Z), docs/spec.md D18 + §7 (grep), docs/system/pin-contract.yaml (27 signals)]
scratch: /tmp/claude-1000/-home-hrafnavalkyrja-Desktop-ultrasonic/759e00a7-254c-4cd3-926a-efbece430ab6/scratchpad/drastic/ (pdftotext copies)
```

## 0. Bottom line (blunt)

```yaml
SI-BL-1: "Silicon integration cannot shrink the pod drastically. The board is already a near-minimal set (MCU with core SMPS, DSBGA charger, 1x1 LDO, two DFN1010 MOSFET pairs as the 'amp'). Board AREA is volume-free (MINI BL-1); the only volume path for silicon is LOWER CURRENT -> SMALLER CELL."
SI-BL-2: "The cell is sized by the worst corner: 10.55 mA (awake 9.79 high + LED 0.75) at 75 % usable -> 169 mAh for 12 h [E tws-power-size.md + power.py]. MCU + its peripherals are 4.0 mA of that (3.2 + 0.8, power.py high column). CEILING if the MCU drew ZERO: 6.55 mA -> 105 mAh for 12 h, 70 mAh for 8 h = cell -40 % (~-890 mm3 of cell at Renata's 291 Wh/L) [E arithmetic]. The other 5.7 mA (mic 2.15, transducer 2.5 [untraced guess, PWR-04], bridge 1.0, LED 0.75) no chip in this lane removes."
SI-BL-3: "Best realistic silicon lever: ST STM32U3 (ST near-threshold ultra-low-power Cortex-M33, 96 MHz, same STM32Cube family as our U575, has the audio digital filter ADF, USB FS, an advanced motor-control timer = TIM1, core SMPS). 16 uA/MHz CoreMark @3.3 V/96 MHz on SMPS vs our U575 model ~34-40 uA/MHz [secondary: CNX Software 2025-03-05 quoting ST; st.com unreachable 2026-10-03; power.py]. At 80 MHz: MCU 2.7 -> ~1.4 mA nom, worst corner 10.55 -> ~8.6-9.0 mA -> 12 h needs 137-143 mAh (-18..-22 %) -> cell -400..-480 mm3, pod ~-450..-650 mm3 IF the cell lane finds a thinner pouch of that capacity [E]. Bonus: its UFQFPN-32 5x5 (at JLC: U385KGU6 7 pcs, U375KGU6 14 pcs [V JLC API 2026-10-03T05:18Z]) saves ~30 mm2 courtyard vs our QFN48 7x7 while staying hand-reworkable -> the MZ-2 one-face board fits without the WLCSP [E]. Catch: U375/U385 have 256 KB SRAM / 1 MB flash (FWSIM-R62 log ring 230 KB does not fit beside the DSP); the 640 KB / 2 MB STM32U3B5/C5 (Mar 2026) is 0 stock at JLC and only in QFN48 7x7 or larger/WLCSP [secondary CNX 2026-03-06; V JLC 05:22Z]."
SI-BL-4: "Rejected on evidence: smart/class-D amps and haptic drivers (higher idle current than our 0.83 mA discrete bridge, bigger, wrong band); PMICs (nPM1300, BQ25125, MAX77654: same or larger area than BQ25180 + TPS7A2030, their bucks break D11, no cell saving); Ambiq for rev 1 (0 JLC stock, no USB on Apollo3, 1.71-2.2 V core-supply parts need level shifting for the bridge gates); edge-AI chips (NDP120/IA8201 need a host MCU anyway: +1 chip)."
SI-BL-5: "Cheapest 'silicon' lever is not a chip: E4 (measure). 2.5 mA of the 10.55 mA worst corner is an untraced transducer guess and 2.15 mA a re-derived mic figure; if E4 lands near nominal (6.76 + 0.75), 12 h needs ~106 mAh with the CURRENT silicon [E power.py nominal x 12 / 0.85]. That is about the same cell cut as the zero-current-MCU ceiling."
```

## 1. Power map that bounds this lane

```yaml
src: sim/checks/power.py (run 2026-10-03T05:15Z) + tws-power-size.md cell table (worst = awake high + LED 0.75 @ 75 % usable)
active_mA_low_nom_high: {mic: [1.1, 1.35, 2.15], MCU_80MHz_SMPS: [2.3, 2.7, 3.2], periph_TIM1_ADF_DMA: [0.6, 0.73, 0.8], bridge: [0.5, 0.77, 1.0], gate_pulls: 0.06, transducer: [0.4, 1.1, 2.5], LDO_xtal: [0.03, 0.05, 0.08], total: [4.99, 6.76, 9.79]}
idle_mA: [1.68, 2.20, 3.43]   # mic 1.35 dominates idle; MCU 0.7
cell_vs_worst_current: "C12h = I x 12 / 0.75; C8h = I x 8 / 0.75; cell vol ~12.7 mm3/mAh at 291 Wh/L (ICP501233PA-02: 2226 mm3 / 175 mAh) [E; small cells lose density, tws-power-size note]"
scenarios_E:
  baseline:              {worst: 10.55, C12h: 169, C8h: 113, cell_mm3: 2226}
  STM32U3_est:           {worst: "8.55-8.95", C12h: "137-143", C8h: "91-95", d_cell_mm3: "-400..-480", basis: "MCU high 3.2 -> 1.4-1.8 (16 uA/MHz x 80 MHz x ~1.1 for 3.0 V SMPS input + margin), periph 0.8 -> ~0.6 [E from secondary CNX 2025-03-05 ST figures]"}
  Apollo3_est:           {worst: 7.75, C12h: 124, C8h: 83, d_cell_mm3: -650, basis: "6 uA/MHz @3.3 V x 80 MHz = 0.48 mA + turbo overhead [T] + periph 0.4 [E]"}
  ceiling_MCU_zero:      {worst: 6.55, C12h: 105, C8h: 70, d_cell_mm3: -890}
pod_conversion: "pod T: 0.1 mm = ~60 mm3 (MINI BL-2). A cell -550 mm3 on the same 35 x 12 footprint = -1.3 mm cell thickness -> pod ~-780 mm3 IF the pouch exists at that thickness; if instead a shorter cell (stock sizes, e.g. Renata ICP401230UPR 130 mAh 4.5 x 12.7 x 31 [V tws-power-size Renata DS read 2026-10-02]) the board must also fit the shorter length -> silicon area savings start to matter [E]"
```

## 2. Candidates examined

### 2a. MCU / DSP SoCs (replace U1 STM32U575CIU6Q: ST Cortex-M33 MCU with core SMPS, UFQFPN-48 7x7)

```yaml
SI-M1: {part: "ST STM32U385KGU6 / STM32U375KGU6 (STM32U3 series, Cortex-M33 ULP MCU, UFQFPN-32 5x5)",
  jlc: "C44847720 U385CGU6 UFQFPN-48 7x7 Ext 30 pcs $9.13; C45066903 U385KGU6 UFQFPN-32 5x5 Ext 7 pcs $7.71; C45338536 U375KGU6 UFQFPN-32 Ext 14 pcs $7.26 [V JLC API 2026-10-03T05:18Z]",
  facts_secondary: "Cortex-M33 96 MHz; 1.71-3.6 V; LDO + SMPS step-down; run 9.5 uA/MHz while(1), 13 uA/MHz CoreMark @48 MHz, 16 uA/MHz CoreMark @96 MHz (all 3.3 V, SMPS); Stop 2 3.8-4.5 uA; 256 KB SRAM, 512 KB/1 MB flash; USB 2.0 FS; 1x SAI; audio digital filter with sound-activity detection; 1x 16-bit advanced motor-control timer; 2x 12-bit ADC 2.5 Msps; packages UFQFPN32 5x5 0.5 mm, (F)QFPN48/LQFP48 7x7, WLCSP52 3.1x3.2x0.6 0.4 mm, WLCSP68 0.35 mm; ST claims ~2x STM32U5 efficiency (117 ULPMark-CM) [CNX Software 2025-03-05 (updated 2026-03-05) quoting ST, SECONDARY; st.com product page + datasheet unreachable 2026-10-03 01:17-01:19 EDT: curl empty, WebFetch timeout, newsroom/blog HTTP 473]. U3B5/C5 (2026-03-06): 640 KB SRAM, 2 MB flash, HSP signal-processing accelerator, 12-20 uA/MHz, no QFN32 [CNX 2026-03-06]; JLC 0 stock [V 05:22Z]",
  unverified: "ADF max PDM clock (need 4.0 MHz for SPH0641 ultrasonic mode), ADF on the QFN32 pins, TIM1 complementary channels CH1/CH1N + CH3/CH3N on QFN32, USB DFU in ROM (AN2606), current at 3.0 V [T]",
  pins: "pin-contract.yaml has 27 signals incl. NRST/BOOT0/LSE/2 MDF fallback dots; a 32-pin QFN has ~25-26 GPIO [T ballout] -> tight; the 2 MDF fallback dots and DBG_TX would likely go [E]",
  area: "cy QFN48 7x7 65.6 mm2 (area-model) -> QFN32 5x5 ~35 mm2 [E KiCad QFN cy 0.25] = -30 mm2 = -4.2 mm of one-face board at H12 U0.60 [E]; ~70 % of the WLCSP90 saving with a hand-reworkable, probeable QFN (O18/O19)",
  power: "worst -1.6..-2.0 mA [E]; idle MCU 0.7 -> ~0.3 [E]",
  fw_impact: "same STM32Cube HAL family: clock tree, ADF, TIM1, SMPS, low-power modes re-ported; algorithm B must fit 96 MHz (U575 runs it at 80) [E]; 256 KB SRAM / 1 MB flash vs U575 786 KB / 2 MB -> FWSIM-R62 230 KB log ring must shrink or move (degradation of the logging feature, not of hearing) [E]; no MDF (only ADF) -> the MDF fallback mic-clock dots (O18) go [E]; spec D5 change",
  risk: "med: unverified specs; new series (errata maturity); stock 7-14 (buy-once at freeze, O21)", effort: "verify datasheet 0.2 Claude d; port + re-sim 3-5 Claude d; owner 0.5 d review", conf: "[V] existence/package/stock; [T] everything electrical"}
SI-M2: {part: "Ambiq Apollo3 Blue AMA3B1KK (Cortex-M4F, 48/96 MHz turbo, SPOT sub-threshold, BLE radio unused)",
  facts: "6 uA/MHz from flash/RAM @3.3 V; 1.755-3.63 V; WLCSP66 3.25 x 3.37 (37 GPIO), BGA81 5x5, QFN64 8x8; PDM mono/stereo; NO USB listed [V ambiq.com/apollo3-blue/ fetched 2026-10-03]",
  jlc: "KBR C5379117, KCR (WLCSP) C29652540, KQR C38309525: all stock 0 [V JLC API 2026-10-03T05:17Z]",
  blockers: "no USB -> F10 (USB data through the dock, DFU) needs a USB-UART bridge (+1 chip, +power) or a dock-protocol change; PDM max clock vs SPH0641 ultrasonic mode 4.0 MHz [T]; no ST-style TIM1 dead-time complementary PWM -> bridge timing re-design [T]; full firmware port off the ST stack; WLCSP 0.4-0.5 pitch [T] same assembly risk as MZM-06",
  power: "worst -2.8 mA [E] (best of the lane)", verdict: "not for rev 1 (stock 0, USB, port); keep as rev-2 reference"}
SI-M3: {part: "Ambiq Apollo4 Lite AMAP42KL-KBR (Cortex-M4 192 MHz, 4 uA/MHz from MRAM) / Apollo510 (Cortex-M55 Helium, 96/250 MHz, CSP AP510NFA-CCR)",
  facts: "4 uA/MHz MRAM; 5x5 146-pin BGA; Apollo510 Lite 4.0 x 4.0 x 0.5 CSP 68 GPIO; operating range 1.71-2.2 V, SIMO buck; PDM DMIC, I2S [V ambiq.com/apollo4-lite/ and /apollo510/ fetched 2026-10-03]; AMAP42KL-KBR JLC stock 0 [V JLC 05:18Z]",
  blockers: "1.71-2.2 V supply: new 1.8 V rail; bridge P/N gate drive from 1.8 V I/O cannot switch PMCXB290UE at VBAT -> gate level shifters (+parts, +current) [E]; 0.5 mm-ish BGA/CSP; 0 stock; full port",
  verdict: "reject for this product"}
SI-M4: {part: "Nordic nRF54L15 (Cortex-M33 128 MHz + 2.4 GHz radio)", jlc: "only placeholder rows, stock 0 [V JLC 05:18Z]", verdict: "reject: radio unused, PDM ultrasonic clock [T], no gain over SI-M1 found in time"}
SI-M5: {part: "edge-AI audio DSPs (Syntiant NDP120, Knowles IA8201)", verdict: "reject [E]: they still need a host MCU for USB/charger/bridge PWM -> +1 chip; ultrasonic PDM support [T]; not stocked at JLC [T not queried]"}
SI-M6: {part: "keep STM32U575, cut its clock (Range 4, <= 25 MHz, 19.5 uA/MHz headline per power.py comments) + FMAC offload", note: "firmware lane, not silicon; listed so the comparison is fair: if algorithm B fits ~24 MHz, MCU active falls ~2.7 -> ~0.6 mA [E] with ZERO hardware change -> same cell cut as SI-M1 without the port. Check before any chip swap"}
```

### 2b. Amp / exciter drivers (replace Q1/Q2 Nexperia PMCXB290UE N+P MOSFET pairs DFN1010 + R21 shunt + gate resistors)

```yaml
baseline: "bridge 0.77 mA nom (gate charge + ripple) + 0.06 pulls; 2 x 1.0 x 1.0 mm DFN; TIM1 makes the ~200 kHz carrier directly (tws-power-size)"
SI-A1: {part: "TI TAS2110 (6.1 W digital-input class-D with 11 V class-H boost, VQFN-32 4 x 4.5)", facts: "current in active fs 48 kHz: 4.6 mA (VBAT) [V SLASET8 Dec 2019 p.8-14]; JLC C4991172 Ext 227 pcs $2.71 [V 05:18Z]", verdict: "reject: 6x our idle current, boost inductor, 18 mm2 body"}
SI-A2: {part: "TI DRV2605 (ERM/LRA haptic driver, DSBGA-9)", facts: "IQ 0.6 typ / 1 mA max no signal; PWM output 19.5-21.5 kHz [V SLOS825E Apr 2018 p.5-9]", verdict: "reject: 20 kHz PWM sits on the mic band edge (20-96 kHz) and cannot carry 1.5-4 kHz cleanly; LRA resonance tracking is for ~150-250 Hz actuators [E]"}
SI-A3: {part: "TI TPA2011D1 (3.2 W class-D)", facts: "Iq 1.5 typ / 2.3 max mA [V repo tws-power-size.md citing SLOS626B Nov 2015]", verdict: "reject (already rejected in repo)"}
SI-A4: {part: "ADI MAX98357A (I2S class-D, TQFN-16 3x3 at JLC)", facts: "JLC C910544 Ext 27361 pcs $1.32 [V 05:18Z]; Iq [T: analog.com fetch returned empty 2026-10-03]", verdict: "reject: needs I2S (adds SAI clocks), larger than 2 DFN1010, no I-V sense, Iq of its class is mA-level [E]"}
SI-A5: {part: "smart amps with I-V sense (TI TAS2563, Cirrus CS35L41, ADI MAX98390) and haptic/bone drivers (Cirrus CS40L2x, Awinic AW86xxx)", verdict: "not fetched in time [T]; class: boost + DSP smart amps for 0.5-6 W speakers, mA-class Iq [E]. The discrete bridge + R21 sense already gives our self-test (F4) at < 1 mA. Expect reject"}
conclusion: "the discrete H-bridge IS the integrated solution here: smallest area and lowest current of anything examined. Keep."
```

### 2c. Power management (replace U3 TI BQ25180 1-cell linear charger DSBGA-8 + U4 TI TPS7A2030 3.0 V LDO X2SON-4 1x1 + VBAT divider)

```yaml
SI-P1: {part: "TI BQ25125 (wearable charger + 300 mA buck + 100 mA LDO/load switch + push-button reset, DSBGA-25 2.5 x 2.5)", facts: "700 nA Iq with buck on; LDO/LS 0.8-3.3 V programmable, 100 mA; 6 external components; ship mode < 50 nA [V SLUSDL9A rev Jan 2021 p.1, p.4-12]; JLC C2871567 Ext 30 pcs $4.46 [V 05:18Z]", area: "6.25 mm2 body vs BQ25180 + TPS7A2030 ~2.5-3 mm2 bodies [E] -> +3..+4 mm2", power: "LDO path replaces TPS7A2030 (similar); buck would break D11 unless left off [T whether the buck can be disabled with LDO fed from SYS]", verdict: "reject: bigger, and only the LDO is usable"}
SI-P2: {part: "Nordic nPM1300 (charger 32-800 mA, 2 x 200 mA buck, 2 x LDO 50 mA / load switch 100 mA, fuel gauge, ship 370 nA)", facts: "[V nordicsemi.com/Products/nPM1300 fetched 2026-10-03]; WLCSP 3.1 x 2.4 (JLC C25346894 Ext 1088 pcs $2.67), QFN32 5x5 [V JLC 05:18Z]", area: "7.4 mm2 body -> +4..+5 mm2 [E]", plus: "fuel gauge (better SoC than VBAT/2 + ADC4, F8)", verdict: "reject for size; consider only for the fuel gauge, which is a feature not a size lever"}
SI-P3: {part: "ADI MAX77654 (SIMO PMIC: charger + 3 buck-boost outputs from one inductor + 2 LDO, WLP-30 2.79 x 2.34)", facts: "JLC C3189130 Ext 10 pcs $7.30 [V 05:18Z]; datasheet [T: analog.com fetch empty 2026-10-03]", verdict: "reject: SIMO switcher breaks D11 (only the MCU core SMPS may switch); bigger"}
conclusion: "BQ25180 + TPS7A2030 is already the minimal D11-compliant set. No PMIC saves area or current."
```

### 2d. Mics with on-chip processing

```yaml
SI-MIC: "Only Knowles/Syntiant SPH0641LU4H-1 specifies an ultrasonic mode (D13, packages.md). TDK T5838 (500 uA @1.8 V, 4.2-4.8 MHz clock, response plotted to 50 kHz only) is the one lower-power alternative already in the repo (tws-power-size lever 3, -0.3..-0.5 mA, band risk) [V repo]. Its on-chip activity detector is low-pass, cannot wake on ultrasound [V repo, T5838 Rev 1.0 Jun 2022]. No mic with on-chip ultrasonic DSP found [T: not searched exhaustively]."
```

## 3. Proposed integrated architectures (2-3)

```yaml
ARCH-SI-0 (recommended first, zero hardware): {what: "keep silicon; E4 measurement + SI-M6 firmware clock cut (U575 Range 4 if algorithm B fits ~24 MHz)", board: "unchanged", power: "worst 10.55 -> ~8.5 mA if MCU 3.2 -> ~1.0 [E]", cell: "-20..-37 % if E4 confirms (12 h at nominal 7.5 mA incl. LED = 106 mAh) [E]", pod: "-500..-900 mm3 via a thinner/shorter cell (cell lane)", fn: "none", risk: "low; depends on E4 (bench) and algorithm B cycle count", effort: "Claude 1-2 d (cycle-count study, power.py update); owner: E4 bench session (needs hardware: blocked by O21)", conf: "[E]"}
ARCH-SI-1 (worth a datasheet check now): {what: "U1 STM32U575 QFN48 -> STM32U3 (U385/U375) QFN32 5x5; everything else unchanged", board: "-30 mm2 cy -> MZ-2 one-face board ~31-32 -> ~27-28 mm long at U0.60 (no WLCSP) [E]", power: "worst -1.6..-2.0 mA [E from secondary 16 uA/MHz]", cell_pod: "cell -400..-480 mm3; pod -450..-650 mm3 via the cell lane [E]", fn: "hearing unchanged; degraded: on-device log ring (256 KB SRAM), MDF fallback dots and maybe DBG_TX pin lost (O18) [E/T pin count]", risk: "med (unverified datasheet, new series, stock 7-14)", cost: "~-$1.4/pod vs U575 [V JLC]", effort: "Claude: 0.2 d to verify DS + ballout; 3-5 d port/sims/pin-contract/gen.py; owner 0.5 d", owner_call: "yes (spec D5 MCU choice, O18 debug pins)", conf: "[V] part exists/stock; [T] electricals"}
ARCH-SI-2 (rev-2 reference only): {what: "Ambiq Apollo3 Blue WLCSP66 + USB-UART bridge (or dock protocol change)", board: "~-35 mm2 MCU cy, +~6 mm2 bridge chip [E]", power: "worst -2.8 mA [E]", cell_pod: "cell -650 mm3 [E]", fn: "degraded: USB DFU path changes; WLCSP unreworkable (O19)", risk: "high: JLC stock 0, PDM 4 MHz and dead-time PWM unverified, full port", effort: "Claude 8-12 d; owner 1-2 d", conf: "[V] Ambiq page; [E] rest"}
rejected_architectures: ["smart-amp/haptic driver output stage (SI-A*)", "PMIC consolidation (SI-P*)", "edge-AI audio DSP (SI-M5)", "Apollo4/510 1.8 V parts (SI-M3)"]
```

## 4. Integration-map cross-check (for any proposal above)

```yaml
touches: [U1 (pin-contract.yaml ids all 27 re-mapped for SI-1/2), F1 mic clock path (ADF1 -> U3 audio filter [T]), F3 TIM1 complementary bridge PWM, F10 USB + DFU, F8 VBAT sense on a Stop-mode ADC, D5 (MCU), D11 (SMPS rule: STM32U3 core SMPS stays within D11 if it has one [T]), D18 runtime, O18 debug/test hooks, O21 stock, cell bay (mech lane)]
sims_to_rerun_if_taken: [sim/checks/power.py, size_budget.py, sim/noise (SMPS frequency differs), FWSIM cycle/memory budget, E11 whine test]
not_touched: [spec §1, mic part, bridge, charger, LDO, dock]
```

## 5. Missing (time box hit)

```yaml
missing:
  - "STM32U3 PRIMARY datasheet (DS for STM32U375/385): current at 3.0 V per range, ADF PDM clock limit (4.0 MHz?), QFN32 ballout vs our 27 signals, ROM DFU, SMPS inductor/frequency (sim/noise, D11). Have only CNX Software secondary figures; st.com unreachable 2026-10-03 01:17-01:22 EDT. FIRST follow-up; ARCH-SI-1 stands or falls on it."
  - "Apollo3 PDM max clock and timer dead-time capability (Ambiq datasheet)"
  - "Smart amps TAS2563 / CS35L41 / MAX98390 / CS40L2x / AW86xxx Iq and package: not fetched (expected reject)"
  - "MAX98357A / MAX77654 datasheet numbers (analog.com returned empty)"
  - "STM32U575 algorithm-B cycle count at Range 4 (firmware lane; SI-M6)"
  - "Cell availability at ~105-132 mAh in a thinner 35 x 12 pouch (cell lane)"
```
