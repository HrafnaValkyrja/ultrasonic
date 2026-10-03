# drastic/power-cell: power budget -> smaller cell (lane notes)

```yaml
id: DRASTIC-PWRCELL
doc: docs/research/drastic/power-cell.md
date: 2026-10-03 ~01:15-01:35 EDT
status: read-only research lane. No spec/board/schematic/firmware edit, no commit. Numbers [V]=verified primary src+date, [E]=estimate (method named), [T]=TBD.
script: /tmp/claude-1000/-home-hrafnavalkyrja-Desktop-ultrasonic/759e00a7-254c-4cd3-926a-efbece430ab6/scratchpad/drastic/pc.py (+ pc.json); imports sim/checks/size_budget.scenario(); fenced 3G; run 2026-10-03T01:19 EDT
inputs: [sim/checks/power.py rev2, docs/system/rail-budget.yaml (2026-10-02), spec §7/D18/O8/O16/O19-O21, docs/research/tws-power-size.md, A3-u575-plan.md §1.3/§5, C2-cpu-budget.md, miniaturization-prelim.md MZ-2, hw/mech/shell_r2.py]
reference_pod: "MZ-2 / shell_r2: board 30x12 one-face, cell Renata ICP501233PA-02 175 mAh, env 6259 mm3, L38.0 T10.40 H14.5 (+belly), 11.92 g [E size_budget, reproduced]"
glossary:
  ICP501233PA-02: "Renata (Swatch Group) Li-ion polymer pouch, 5.3x12x35 mm, 175 mAh, PCM inside (protection circuit module = over/under-voltage + over-current cut-off). Today's cell."
  ICPttwwll: "Renata pouch code: thickness x0.1 mm / width / length; suffix letters = PCM/lead style (PA, PS, PR, PM, UPR, UPM: PCM fitted per Renata naming [T per part]; HPG/HPMT = high-voltage 4.35 V class)"
  ICRddhh: "Renata rechargeable Li-ion coin cell (steel can), Ø dd mm x hh/10 mm; NO PCM"
  CP: "Varta CoinPower rechargeable Li-ion coin cell (steel can), Ø x height; PCM mandatory per Varta"
  STM32U575: "ST Cortex-M33 MCU with internal core SMPS (switch-mode supply for the 1.1 V core); U1"
  SPH0641LU4H-1: "Knowles/Syntiant PDM MEMS mic with an ultrasonic mode (3.072-4.8 MHz clock); U2"
  TPS7A2030: "TI 3.0 V 300 mA low-noise LDO; U4"
  BQ25180: "TI 1-cell linear charger with power path, I2C; U3"
  ADF/LPDMA/SAD: "U575 audio digital filter (runs in Stop 2) / low-power DMA / ADF sound-activity detector"
  Range 1-4: "U575 core voltage ranges; Range 4 (<=25 MHz) runs the SMPS asynchronously (spur risk, D11/E11)"
```

## 0. Bottom line (blunt)

```yaml
BL-1: "The 175 mAh cell is sized for the STACKED worst corner AND 12 h at that corner (always awake, every block at its high, LED 0.86 mA, 75 % usable: 10.65 mA -> 170 mAh). The spec (D18) only asks >= 8 h minimum, ~12 h target. Sizing to '8 h at the worst corner + 12 h at a design point (50 % awake, nominal, aged 0.68 usable)' needs 114 mAh with TODAY's electronics [E pc.py]. => Renata ICP401230UPR 130 mAh: pod 6259 -> 5480 mm3 (-779, -12.4 %), T 10.40 -> 9.60, H +0.7, -0.9 g, ZERO circuit change. This is the cheapest big lever and it is a requirement-interpretation call for the owner, not engineering."
BL-2: "Firmware-only power levers (O18-clean) cut the awake budget 6.8 -> 5.3 mA nominal, 9.8 -> 8.4 high, idle 2.2 -> 1.6, LED 0.45 -> 0.08 [E]. Biggest: LED PWM dimming (-0.4..-0.7 mA, always on), MCU 80 -> 55 MHz Range 3 with the ADF doing decimation (-0.85), Stop-2 idle (-0.5 idle), dead time 25 ns (-0.3). Need then 91 mAh (8 h worst) / 62 (12 h design)."
BL-3: "The mic is the floor: 1.35 mA in EVERY state (61 % of idle after B1). Its datasheet point is 845 uA typ / 1000 max at 1.8 V, 3.072 MHz [V SPH0641LU4H-1 sheet, scratchpad copy]. A 1.8 V mic rail (+tiny LDO +1-bit translator, because U575 VIH = 0.5 VDDIO + 0.2 = 1.7 V at 3.0 V [V DS13737 I/O table]) is the one hardware lever that moves idle (-0.5 mA). With it + bridge on VSYS + 1M gate pulls (B2): need 73 / 51 mAh -> an 80-85 mAh cell -> -685..-943 mm3 (board 30) or -1517 (board 24)."
BL-4: "Drastic case B3 (B2 + DSP at <= 24 MHz Range 4: algorithm A heterodyne or a slimmed B, IF the async SMPS passes E11 and she accepts the sound): awake ~3.1 mA nominal / 5.0 high -> need 55 / 38 mAh -> Renata ICP281029HPG 68 mAh (3.3 x 10.2 x 30.5): pod 4487 mm3 (-1772, -28 %), T 8.40 (-2.0 mm off the temple), 9.07 g (-2.85 g). This is the largest volume cut found in this lane; it is contingent on 3 unknowns (E11 Range-4 noise, algorithm-A listening, exciter E1/E2) and on a 4.6C full-scale bridge peak the cell cannot feed (firmware peak cap or bulk cap needed)."
BL-5: "Coin cells (Renata ICR, Varta CoinPower) do NOT win on volume in the stacked layout: their Ø >= 12.2 sets pod HEIGHT (14.7-18.6), and a 30 mm board sets length anyway. They pay only if the board shrinks to ~24 mm (WLCSP MZ-3): 2x ICR1254 B2 154 mAh -> -1282 mm3 (needs a new PCM + spot-welded tabs). Pin cells / silicon-anode: no buyable datasheet found (prior lane + this run) [T]."
BL-6: "Pod volume is now set by cell T (each 0.1 mm = ~60 mm3) and cell L only below the 30 mm board. So the ranking among cells is THICKNESS first: 3.3 (ICP281029HPG) > 4.3 (ICP390831PR) > 4.5 (ICP401230UPR) > 5.3 (today)."
BL-7: "Recommendation (owner decides): Option A now = BL-1 (130 mAh) + B1 firmware levers -> meets 8 h at the stacked worst corner with margin (needs 91 of 130) and 12 h at design; Option B (major redesign) = B2 + ICP390831PR 85 mAh or ICP501022UPM 80 mAh; Option C (drastic, gated) = B3 + ICP281029HPG 68 mAh. Do not order any cell before E4 measures real current (O21 holds anyway)."
```

## 1. Current budget rebuilt and challenged (per block, mA from the battery, low / nom / high)

Source rows: `sim/checks/power.py` rev 2 = B0 [E repo, V-cited datasheet points inside]; rail-budget.yaml same numbers + LED R14.

```yaml
blocks:
  mic_U2:
    B0: {awake: [1.1, 1.35, 2.15], idle: same, src: "power.py rev2 re-derivation at 3.0 V / 4.0 MHz, loaded [E]"}
    datasheet: "Ultrasonic mode IDD 845 typ / 1000 max uA (1.8 V, 3.072 MHz test point); Standard 620/700 @2.4 MHz; Low-power 235/270 @768 kHz; Sleep 80 uA; wake <= 15 ms; mode change <= 10 ms; dIDD = 0.5*VDD*dCLOAD*fCLOCK [V SPH0641LU4H-1 datasheet Rev B-1 2024-12-02, scratchpad sph0641_sq.txt, read 2026-10-03]"
    challenge:
      lower_PDM_clock: "4.0 -> 3.072 MHz (ultrasonic-mode minimum): OSR at 96 kHz drops 20.8 -> 16; saves the CLOAD term (~0.03 mA at 20 pF) + unknown internal scaling [E]; in-band noise rise must be checked in sim/dsp [T]. Small."
      LP_mode_or_duty_cycle: "REJECT for same-function: LP mode clock 351-815 kHz cannot carry 20-96 kHz; sleep->active 15 ms + mode change 10 ms vs 2-20 ms bat calls -> onsets lost (T2 degraded). Only as a degraded 'deep-quiet' mode (owner call)."
      1V8_rail: "mic VDD 1.8 V from its own LDO (e.g. TI TPS7A02 1.8 V class [T part pick]) -> 0.85 / 1.0 mA [V typ/max]; DATA (1.8 V CMOS) fails U575 VIH 0.5*VDDIO+0.2 = 1.7 V at VDDIO 3.0 V [V DS13737 I/O static table] -> 1-bit translator (TI SN74AXC1T45 class [T]) or ADF data pin on VDDIO2 port G if one exists [T: AF table]. Saves ~0.5 mA ALWAYS ON [E]. Hardware change (O19/O20)."
      whole_system_1V8: "REJECT: SMPS-fed MCU input current scales ~1/VDD, so MCU +0.8 mA eats the mic saving [E from SMPS power balance]."
  mcu_U1:
    B0: {awake: [2.3, 2.7, 3.2], idle: [0.5, 0.7, 1.0], src: "algo B 80 MHz Range 2 (~3.3 run / ~1.45 sleep interpolated, DS13737 Rev 8 T39/T46 via A3-u575-plan §5); idle = 256-pt FFT/5 ms at 16 MHz Range 3"}
    datasheet_rows: "Run SMPS 3.0 V: 160 MHz R1 7.15 mA; 110 R2 4.40; 72 R2 3.05; 64 R2 2.80; 55 R3 2.20 (sleep 0.92); 24 MHz R4 while(1) 0.47 mA @3.3 V (19.5 uA/MHz); Stop 2 SMPS 3.90-8.55 uA [V DS13737 Rev 8 Tables 39/42/46/58, via A3-u575-plan.md §5, read there 2026-10-01]"
    cycles: "algo B restructured 44-65 Mcyc/s incl. half-band FIR 5-10 + output x16 interp/noise shaper 6-10 + DMA 2-3; algo A 19-39 (C2-cpu-budget.md, M4 counts, M33 [T])"
    challenge:
      B1_55MHz_R3: "ADF CIC/decimation replaces the half-band FIR (-5..-10 Mcyc), q15 FFT (~1.5x on 22-26) -> ~30-50 Mcyc -> 55-90 % busy at 55 MHz -> 0.55..0.9*2.20 + rest*0.92 + MSI/PLL ~0.08 = [1.6, 1.85, 2.3] [E]. Firmware only. PWM resolution: TIM1 clock 55 MHz / 200 kHz = 275 steps if TIM1 on PLL; check D14 HCLK/400 lock [T]."
      B3_24MHz_R4: "algo A (13-28 Mcyc with ADF decimation) or a slimmed B (fewer bands, 128-pt FFT) at <= 24 MHz Range 4: ~0.45-0.9 mA [E from 19.5 uA/MHz]. GATES: Range 4 = SMPS asynchronous -> spur/whine risk -> E11 listening + in-band spur test (D11); algorithm A is her listening call; TIM1 at 24 MHz -> 120 PWM steps (-4.4 dB) unless noise shaping covers it [E]."
      idle_stop2: "ADF + LPDMA -> SRAM4 in Stop 2, CPU wakes per half-buffer for the band test: MCU ~0.1 mA (A3 §1.3 own estimate) + burst guess -> [0.1, 0.2, 0.35] vs 0.7 [E]. Also gated by E11 (async SMPS in Stop)."
      FMAC: "-0.1..-0.15 mA per 10 Mcyc moved off the CPU (tws-power-size §4) [E]; enabler for B3."
  peripherals:
    B0: [0.6, 0.73, 0.8]
    datasheet: "TIM1 2.52 uA/MHz, GPDMA1 1.52, ADF1 0.39+0.14 (Range 2, SMPS) -> ~0.36 mA at 80 MHz [V DS13737 T72 via A3 §5]"
    challenge: "B1 at 55 MHz: [0.3, 0.4, 0.6]; B3 at 24 MHz: [0.15, 0.2, 0.3] [E scaled per MHz]"
  bridge_Q1_Q2:
    B0: {awake: [0.5, 0.77, 1.0], src: "repo SPICE 12.5 ns dead time: 0.49 bus + 0.28 gate (audit PWR-03)"}
    challenge:
      dead_time_25ns: "-0.3 mA (bus 0.49 -> 0.10-0.20) [E repo SPICE, sub-output.md]; distortion check; TIM1 register (O18)"
      PWM_freq: "cannot drop: carrier must stay above the 96 kHz mic band and her hearing (pwm_ultrasonic_leak.py); 200 kHz kept"
      class_D_IC: "REJECT: TPA2011D1 Iq 1.5 mA typ (TI SLOS626B Nov 2015, via tws-power-size) > our 0.77"
      gate_pulls: "4x100k = 0.06 mA (power.py) -> 1M: 0.006 [E]; hardware value change only"
      bridge_on_VSYS: "feed the bridge from VSYS (3.3-4.2 V) instead of the 3.0 V LDO: for the same exciter power the supply current falls ~3.0/3.7 (-19 %) AND it removes the ECR-0005 315 mA-on-300 mA-LDO problem; cost: gain tracks VBAT (~1.8 dB, spec §7) -> firmware gain from the VBAT ADC; battery ripple on the bridge rail [E]. Hardware (re-route one net)."
  exciter:
    B0: {avg: [0.4, 1.1, 2.5], src: "UNTRACED GUESS (audit PWR-04) until E1/E2/E4"}
    physics: "lossless bridge, 3.0 V, ~9.3 ohm: I = m^2*3.0/(2*9.3): 1.6 mA at -20 dBFS continuous, 0.16 at -30 (tws-power-size §4, re-derived there) [E]"
    challenge:
      mean_power_cap: "firmware long-term output-power limiter (e.g. mean <= 1.0 mA) turns the 2.5 mA guess into a BOUND -> worst-case need falls ~16 mAh at 8 h; impact: sustained loud sources compressed (mild degradation, O18 knob) [E]"
      exciter_choice: "sensitivity (m/s^2 per W at the tragus) is the real lever, not impedance; unknown until E1/E2 [T]"
  ldo_misc:
    B0: [0.03, 0.05, 0.08]
    datasheet: "TPS7A20 IGND 6.5 typ / 8.5 max uA [V SBVS338H via rail-budget.yaml]; BQ25180 battery-only IQ_BAT 3 typ / 3.5 max uA (watchdog off), 4/5 uA with push-button; ship 3.2 uA [V TI BQ25180 datasheet, scratchpad bq25180.txt, read 2026-10-03]; VBAT divider 2.1 uA [V rail-budget calc]"
    challenge: "LDO vs nothing: REJECT removing it: U575 VDD max 3.6 V < 4.2 V cell; linear LDO costs no extra CURRENT (Iin = Iout), only voltage headroom. All quiescents sum < 0.02 mA: not a lever."
  led_R14:
    B0: [0.14, 0.45, 0.86]
    src: "R14 2k2 from VSYS, on battery 0.14-0.73, docked 0.82-0.86 (rail-budget.yaml / sub-power.md)"
    challenge: "PWM from PB7 (already wired, spec O8) at 10-20 % duty, >= 1 kHz (looks solid; O8 said 'solid, no pulsing' -> PWM is perceived solid, but it is her call) -> [0.03, 0.08, 0.15]: -0.37 nom / -0.71 high, ALWAYS ON. Or R14 2k2 -> 10k (hardware) -> ~0.1 [E]. Second-largest lever after the mic for the average."
  charger_PCM: "PCM inside Renata pouches: few uA [T: Renata does not state]; BQ25180 3 uA [V]. Not a lever."
```

## 2. Budgets (pc.py, 2026-10-03T01:19 EDT) [E all]

| budget | what changes | awake mA low/nom/high | idle mA | LED mA |
|---|---|---|---|---|
| **B0** repo rev 2 | nothing | 4.99 / 6.76 / 9.79 | 1.68 / 2.20 / 3.43 | 0.14 / 0.45 / 0.86 |
| **B1** firmware only | LED PWM, 55 MHz R3 + ADF decimation + q15, Stop-2 idle, dead time 25 ns | 3.79 / 5.26 / 8.39 | 1.23 / 1.60 / 2.58 | 0.03 / 0.08 / 0.15 |
| **B2** hw-moderate | B1 + mic 1.8 V rail (+LDO +translator), bridge on VSYS, gate pulls 1M | 3.31 / 4.51 / 6.69 | 0.88 / 1.10 / 1.43 | same |
| **B3** aggressive | B2 + DSP at <= 24 MHz Range 4 (algo A or slim B), peripherals at 24 MHz | 2.01 / 3.06 / 4.99 | 0.88 / 1.10 / 1.43 | same |

Required capacity (mAh rated). Policies: worst = always awake, all-high, 75 % usable (repo convention, already "aged, cool"); design = 50 % awake, nominal, 0.85 x 0.8 end-of-life; expected = 18 % awake (quiet room, idle_detector rev 2), nominal, 0.85.

| budget | worst I / 8 h / 12 h | design I / 8 h / 12 h | expected I / 8 h / 12 h |
|---|---|---|---|
| B0 | 10.65 / **114** / 170 | 4.93 / 58 / **87** | 3.47 / 33 / 49 |
| B1 | 8.54 / **91** / 137 | 3.51 / 41 / **62** | 2.34 / 22 / 33 |
| B2 | 6.84 / **73** / 109 | 2.88 / 34 / **51** | 1.79 / 17 / 25 |
| B3 | 5.14 / **55** / 82 | 2.16 / 25 / **38** | 1.53 / 14 / 22 |

Sizing rule proposed (owner call, reads D18 literally): need = max(8 h at worst, 12 h at design) -> **B0 114, B1 91, B2 73, B3 55 mAh**. Today's rule (12 h at worst) -> 170 / 137 / 109 / 82.

## 3. Candidate cells and pod volume (stacked MZ-2 layout, size_budget.scenario, board 30x12 or a WLCSP-class 24x12)

Renata catalogue rows [V renata.com/en/products/lithium-polymer-batteries/ and /rechargeable-lithium-coin-cells/, fetched 2026-10-03 01:17 EDT]: capacity + T x W x L only (nominal names; max envelopes, PCM and discharge ratings need each datasheet [T] except where noted). Varta [V cached datasheets: CP1454 A3 (Ø14.1 x 5.4, 85 mAh nominal, 170 mA cont, 255 mA 2 s pulse, >500 cyc); CP1254 A4 2020-02-18 (Ø12.1 x 5.4, 70 nominal @4.3 V, 140 cont, 210 pulse); CoinPower handbook 2017-12 table: CP1654 A3 120 mAh 5.4 mm 3.0 g; CP1654 diameter 16.1 [E: glyph unreadable in PDF]]. Masses not in the catalogue are [E] (~29 mAh/g scaling).

| cell | mAh | T x H x L mm | PCM | pod env mm3 (board 30) | d vs 6259 | pod env (board 24) | T / H pod | mass g | meets (rule max(8h worst,12h design)) |
|---|---|---|---|---|---|---|---|---|---|
| ICP501233PA-02 (today) | 175 | 5.3 x 12 x 35 | yes [V] | 6259 | 0 | 6259 | 10.40 / 14.5 | 11.92 | all |
| ICP501230PS-03 | 135 | 5.5 x 12 x 31.5 | PS [T] | 5883 | -376 | 5883 | 10.60 / 14.5 | 11.00 | B0..B3 |
| **ICP401230UPR** | 130 | 4.5 x 12.7 x 31 | yes [V tws note: V02 08/2019] | **5480** | **-779 (-12.4 %)** | 5480 | 9.60 / 15.2 | 11.05 | **B0..B3** |
| ICP501421PS-01 | 115 | 5.2 x 14.1 x 22.5 | PS [T] | 6174 | -85 | 5230 (-1029) | 10.30 / 16.6 | 10.56 | B0..B3 |
| 2x ICR1254 B2 coin | 154 | 5.6 x 12.2 x 24.4 | none: add | 5789 | -470 | 4977 (-1282) | 10.70 / 14.7 | 11.17 | B0..B3 |
| ICR1454 B1 coin | 104 | 5.6 x Ø14.2 | none: add | 6445 | +186 | 5455 (-804) | 10.70 / 16.7 | 10.00 | B1..B3 |
| CP1654 A3 coin | 120 | 5.4 x Ø16.1 | none: add | 6936 | +677 | 5854 (-405) | 10.50 / 18.6 | 10.82 | B0..B3 |
| **ICP390831PR** | 85 | 4.3 x 8.7 x 33 | PR [T] | **5316** | **-943 (-15 %)** | 5316 | 9.40 / 14.2 | 9.64 | B2, B3 |
| ICP501022UPM | 80 | 5.5 x 10 x 24 | UPM [T] | 5574 | -685 | **4742 (-1517, -24 %)** | 10.60 / 14.2 | 9.52 | B2, B3 |
| CP1454 A3 coin | 85 | 5.4 x Ø14.1 | none: add | 6293 | +34 | 5329 (-930) | 10.50 / 16.6 | 9.98 | B2, B3 |
| **ICP281029HPG** | 68 | 3.3 x 10.2 x 30.5 | [T] (HP = HV class [T]) | **4487** | **-1772 (-28 %)** | 4487 | **8.40** / 14.2 | **9.07** | B3 only |

Model notes: pod L = max(cell L, board L) + walls/gaps; H floor 14.2 is the 12 mm board (cells < 12.4 mm tall gain nothing in H); T = cell T + the MZ-2 board stack (Bgap 1.4, board 0.8, Fgap 0.3, lid 0.8, plate 0.7). Coin rows exclude the added PCM (~2 small parts, a few mm2 of board [E]) and tab welds. Not modelled: wire stowage change, belly (dock) unchanged.

```yaml
cell_risks:
  peak_current: "bridge full-scale ~315 mA (rail-budget.yaml). At 68-85 mAh that is 3.7-4.6C; normal D17-ceiling peaks ~85 mA = 1.0-1.25C. Small cells need a firmware peak cap (ECR-0005 direction) and/or bulk cap; Renata pulse ratings for ICP281029HPG / ICP390831PR not read [T]. ICP501233PA-02: 175 cont / 350 pulse [V Renata V03 08/2019 via rail-budget]."
  depth_of_discharge: "smaller cell = deeper daily cycle. 68 mAh at B3 expected 1.53 mA x 16 h = 24.5 mAh (36 % DoD, fine); at B3 worst 12 h = 62 mAh (91 %): faster ageing. Renata rates >500 cycles to 80 % of MIN capacity [V tws note]. Charge to 4.10-4.15 V halves this risk at -7..-14 % capacity (BU-808, secondary) — but eats the margin that small cells don't have. O19: buy spares, cell replaceable."
  availability: "Renata: distributor quote only, no public price/MOQ (tws note 2026-10-02) [T]; same channel for every Renata row. Varta CoinPower: Digi-Key/TME zero (2026-10-01/02) [V tws note]. Ordering waits for O21 freeze anyway."
  swelling: "no pouch swelling % in any primary source opened; coin cells (steel can) avoid it but need PCM + welding."
  not_found: "pin/cylindrical cells (AirPods-stem class), silicon-anode (Enovix/Amprius/Sila) at <100 mAh buyable in ones: no datasheet obtained (prior lane 2026-10-02 + this run) [T]. Grepow pages are JS-only (fetch 2026-10-03 returned no data)."
```

## 4. Levers ranked (mA saved at the sizing point; mm3 via the cell it enables)

```yaml
L0: {what: "Sizing rule: 8 h at the stacked worst corner + 12 h at a 50 %-awake aged design point (instead of 12 h at the worst corner)", saves: "need 170 -> 114 mAh with B0", enables: "ICP401230UPR 130 mAh: -779 mm3, T -0.8 mm, -0.9 g", impact: "none at design/expected use; at the stacked worst corner runtime 12.4 -> ~9.2 h (still >= 8 h)", owner: "yes: D18 reading", conf: "[E] model; cell dims [V]"}
L1: {what: "LED R14 PWM dim (PB7) 10-20 % duty, or R14 2k2 -> 10k", saves: "-0.37 nom / -0.71 high, always", impact: "dimmer pad ring (brightness knob); O8 'solid' kept if PWM >= 1 kHz (her call)", owner: yes, conf: "[E]"}
L2: {what: "MCU 80 -> 55 MHz Range 3 + ADF decimation + q15 FFT (algo B kept)", saves: "-0.85 awake nom (+ peripherals -0.33)", impact: "none if cycles fit (M33 cycle counts [T], S3 cycle counter)", owner: no, conf: "[E]; DS rows [V]"}
L3: {what: "Idle detector in Stop 2 (ADF + LPDMA + SRAM4)", saves: "-0.5 idle (x idle fraction)", impact: "none if E11 passes in Stop 2 (async SMPS)", owner: no, conf: "[E]"}
L4: {what: "Mic on its own 1.8 V LDO + 1-bit translator (+ PDM 3.072 MHz)", saves: "-0.5 always on (1.35 -> 0.85 typ)", impact: "none expected; noise/OSR check at 3.072 MHz; +2 small parts (~3 mm2)", owner: "yes (hardware, O19/O20)", conf: "[V] 1.8 V current; [E] saving vs the 3.0 V re-derivation"}
L5: {what: "Exciter mean-power cap in firmware", saves: "high-corner exciter 2.5 -> ~1.0 mA (-1.5 at worst only)", impact: "mild compression of long loud sources", owner: yes, conf: "[E]"}
L6: {what: "Dead time 12.5 -> 25 ns", saves: "-0.3 awake", impact: "distortion check", owner: no, conf: "[E] repo SPICE"}
L7: {what: "Bridge on VSYS (not the LDO) + firmware VBAT gain", saves: "~-0.2 nom (-19 % of exciter current); fixes ECR-0005", impact: "gain tracking compensated in firmware; ripple check", owner: yes, conf: "[E]"}
L8: {what: "DSP at <= 24 MHz Range 4 (algo A heterodyne or slim B) + FMAC", saves: "-1.25 awake nom vs B1", impact: "possible sound change (her listening call) + Range-4 async SMPS spurs (E11, D11)", owner: yes, conf: "[E], high uncertainty"}
L9: {what: "Gate pulls 100k -> 1M", saves: "-0.05", impact: "slower turn-off on reset (check)", owner: no, conf: "[E]"}
rejected: ["mic LP mode / duty-cycled mic (cannot hear 20-96 kHz; 15-25 ms wake vs 2-20 ms calls)", "integrated class-D (Iq > ours)", "remove LDO (U575 VDD max 3.6 V)", "1.8 V whole system (SMPS input current rises)", "PWM below 200 kHz (in-band leak)", "buck for the rail (D11)"]
```

## 5. Options for the owner (2-3, recommendation first)

| | Option | Changes | Pod (vs 6259 mm3) | Function | Risk | Effort (Claude days / owner) |
|---|---|---|---|---|---|---|
| **A (rec)** | 130 mAh ICP401230UPR + B1 firmware levers + L0 sizing rule | shell bay re-size (-0.8 T, -4 L, +0.7 H); firmware knobs; no circuit change | **5480 (-12.4 %)**, T 9.60, -0.9 g | none (worst-corner runtime ~11.4 h with B1: 130x0.75/8.54) | low; H grows 0.7 | 0.5 shell + firmware later / 0.5 review |
| B | B2 hardware + ICP390831PR 85 mAh (or ICP501022UPM 80 with a 24 mm board) | mic 1.8 V rail + translator, bridge on VSYS, pulls; shell | 5316 (-15 %) / 4742 (-24 %, needs MZ-3 WLCSP board) | none expected | med: new parts, E3/E4 proof, peak cap | 2-3 / 1-2 |
| C | B3 + ICP281029HPG 68 mAh | B2 + Range-4 DSP (algo A or slim B), firmware peak cap | **4487 (-28 %)**, T 8.40, 9.07 g | possible sound change; deep daily cycles | high: E11 Range 4, listening, 4.6C peaks, cell PCM/pulse [T] | 4-6 / 2-3 + listening sessions |

```yaml
missing_or_TBD:
  - "Renata datasheets for ICP281029HPG, ICP390831PR, ICP501022UPM, ICP501230PS-03, ICP501421PS-01 (max envelope, PCM, pulse rating, cycle life) - only catalogue rows read"
  - "Real currents: E3/E4 (mic at 3.0 V vs 1.8 V, MCU per clock, Stop 2), E1/E2 exciter level"
  - "M33 cycle counts for algo B at 55 MHz and algo A at 24 MHz (S3)"
  - "U575 VDDIO2/port-G AF for ADF/MDF data (translator-free 1.8 V mic)"
  - "Pin-cell and silicon-anode datasheets (none buyable found)"
  - "Pod model ignores coin PCM board area, wire stowage and the dock belly change"
```
