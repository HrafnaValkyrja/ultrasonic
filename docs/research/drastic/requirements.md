# drastic/requirements: feature-cost audit (what each requirement costs in pod mm3 and mA)

```yaml
id: DRASTIC-REQ
doc: docs/research/drastic/requirements.md
date: 2026-10-03 ~01:20 EDT (owner-local)
lane: REQUIREMENTS / FEATURE COST AUDIT (one of several parallel "drastic size" lanes)
status: read-only research. No spec/schematic/board/CAD edit, no commit. Numbers from repo models re-run fenced (3G).
inputs_read: [docs/spec.md §1 §2 §3 D2 D11-D18 §7 §12 O1-O26, docs/research/miniaturization-prelim.md (BL-1..7, MZM-*),
  docs/research/mini/skeptic.md (verdict lines), docs/research/tws-power-size.md §1, docs/research/tws/power.md (mic rows),
  docs/research/simplify/size.md (SIZ-*), sim/checks/power.py, sim/checks/size_budget.py, hw/mech/shell_r2.py (params)]
not_read_in_time: [integration-map.md body (only the doc list), simplification-study.md body, mini/architecture.md, pcb-tech.md]
own_runs:
  - "scratchpad/drastic-less: sens.py, sens2.py = size_budget.scenario() around the Phase-2 base, fenced MemoryMax=3G, 2026-10-03 ~01:16 EDT"
  - "base = MZ-2 / shell_r2 stack: board 28x12 (model), Bgap 1.4, Fgap 0.30, lid 0.8, plate 0.7, s_fixed 0.8, dock flat_tails -> 6259 mm3, T 10.40, H 14.5, L 38.0 [E size_budget; shell_r2 header says T 10.40, matches]"
tags: "[V src date] verified primary; [R repo-file] repo model/derived; [E] estimate; [T] TBD"
```

## 0. Bottom line (blunt)

```yaml
BL-R1: "Almost every electrical feature on the list costs AREA, not VOLUME. While the board is shorter than the cell (35 mm), area is free (BL-1). So self-test, SWD pads, ESD, NTC, LDO, crystal, gate pulls = 0 mm3 today. Dropping them buys nothing unless the cell shrinks first."
BL-R2: "Volume is the cell (2226 mm3 raw, ~36 % of the 6259 mm3 pod; the pod grows ~18-28 mm3 per mAh of cell [E sens runs]). So every mA of MEAN current is pod volume: 1 mA x 12 h / 0.85 usable = 14.1 mAh = ~255-395 mm3 of pod. At 8 h: ~170-265 mm3 per mA."
BL-R3: "The single biggest lever is not a feature, it is HOW the runtime requirement is read. D18 says >=8 h, target ~12 h. The 175 mAh cell is sized for 12 h at the PESSIMISTIC always-awake corner (+LED). Sizing for 12 h at NOMINAL always-awake (or 8 h pessimistic) needs ~100-115 mAh -> about -1800 mm3 (-29 %) [E]. Sizing for a measured duty cycle (idle mode load-bearing) needs ~50-70 mAh -> about -2300 mm3 (-37 %) [E]. No feature is lost; the risk is a short day on a busy/cold/aged-cell day."
BL-R4: "That cell win is only realised if the board also shrinks to <= cell length (~25-26 mm for a 25 mm cell). Today's one-face board is ~30-32 mm (MZ-2). So a small cell FORCES either two-face (+0.35..0.7 mm T, +210..390 mm3) or WLCSP (MZM-05 risk). Net of that, the cell lever is still ~-1400..-2000 mm3."
BL-R5: "Non-cell volume wins with no function loss: armour plate 0.7 mm (-379 mm3, styling only), thin dock target (-238), walls 0.8->0.6 (-386, durability risk). Together ~-1000 mm3 (-16 %)."
BL-R6: "§1-locked items (band 20-96 kHz, stereo, bone conduction, comfort/size first, self-noise) are not touched in the top-5. The only §1 item with a real power win is the 96 kHz top (-1.1..-2.1 mA awake -> -280..-800 mm3); it loses 60-96 kHz content. Owner-only; listed, not recommended."
BL-R7: "Biggest blocker for BL-R3: the current is not measured (E4 needs hardware; O21 no orders; O20 rev 1 = final size). Ways out: (a) buy a NUCLEO-U575 + mic breakout as a measurement rig only (owner call vs O18 'no bench rig' and O21), (b) accept the risk and size for nominal, (c) keep 175 mAh in rev 1. Owner call."
```

## 1. Conversion factors (use these for every row)

```yaml
CF-1_cell_to_pod: "pod mm3 per mAh of cell: length lever 139 mm3/mm / 5.0 mAh/mm = 27.8; thickness lever 60 mm3/0.1 mm / 3.3 mAh/0.1 mm = 18.2; height lever 367 mm3/mm / 14.6 mAh/mm = 25.1 -> use 18-28 [E sens.py runs on size_budget; assumes the cell keeps 291 Wh/L]"
CF-2_cell_density: "ICP501233PA-02: 175 mAh, 35x12x5.3 = 2226 mm3 -> 291 Wh/L at 3.7 V [R tws-power-size.md §1 (2026-10-01/02)]. Smaller packs lose density (fixed PCM length ~2-3 mm): 50-100 mAh packs likely 200-260 Wh/L [E, cell lane must verify]"
CF-3_mA_to_mAh: "need = I_mean x hours / usable / EOL; usable 0.90/0.85/0.75 (power.py USABLE low/nom/pess) [R sim/checks/power.py]; EOL (80 % capacity after years, O19) is NOT in any repo requirement today [owner call]"
CF-4_mA_to_pod: "1 mA mean: 12 h -> 14.1 mAh -> 255-395 mm3; 8 h -> 9.4 mAh -> 170-265 mm3 (nominal usable 0.85) [E]"
CF-5_area_to_volume: "board area -> 0 mm3 while board L <= cell L and board H <= 12 (BL-1). Board H 13->12 = -282 mm3 (already taken) [R miniaturization-prelim BL-1]"
CF-6_thickness: "0.1 mm of pod T = ~60 mm3 [R BL-2; reproduced: T-1 run -601 mm3 per 1.0 mm]"
currents_now: "awake 5.0/6.8/9.8 mA, idle 1.7/2.2/3.4 mA (low/nom/pess) [R power.py rev 2]; LED 0.15-0.5 mA glowing [R O8], tws note stacks 0.75 worst"
```

## 2. Runtime design points (the requirement that sets the cell)

| DP | Requirement reading | I_mean mA | usable/EOL | Cell needed mAh | Pod mm3 [E] | vs today |
|---|---|---|---|---|---|---|
| DP0 | today: 12 h, pessimistic always-awake + LED 0.75 | 10.55 | 0.75 / none | 169 -> 175 cell | 6259 | 0 |
| DP0+ | same, at end of life (80 %) | 10.55 | 0.75 / 0.8 | 211 | ~+900 (does not fit; 175 gives 9.7 h EOL [R tws §1]) | worse |
| DP1 | 12 h, NOMINAL always-awake + LED 0.3 | 7.1 | 0.85 | 100 | ~4400 (25x12x4.3 class) | **-1840** |
| DP2 | 8 h, pessimistic always-awake + LED 0.75 | 10.55 | 0.75 | 113 | ~4600-4800 | ~-1500 |
| DP3 | 12 h, nominal, 50 % awake (idle mode load-bearing) | 4.8 | 0.85 | 68 | ~3960 (25x12x3.3 class) | **-2300** |
| DP4 | 8 h nominal always-awake | 7.1 | 0.85 | 67 | ~3960 | -2300 |
| DP5 | 12 h quiet-room duty 18 % (sim) | 3.3 | 0.85 | 47 | ~3400-3900 (cell size floor, board-limited) | -2400..-2900 |

```yaml
DP_notes:
  - "pod mm3 from sens.py/sens2.py runs: 25x12x4.3 -> 4416; 25x12x3.3 -> 3961; with plate 0 + thin dock: 3826 / 3395; 20x12x3.5 + plate 0 + thin dock: 2928 [E size_budget, fenced 2026-10-03 01:16]"
  - "CAVEAT model: size_budget sets pod L from cell L only. Board 28-32 mm does not fit a 25 mm cell: board must be <= ~26 mm (two-face Package B lower bound 24.8-25.4 mm @U0.50 [R skeptic]) -> +210..390 mm3 back (two-face Fgap). Net DP1 ~-1450..-1650; DP3 ~-1900..-2100 [E]"
  - "CAVEAT cells: the 25x12x4.3 / 25x12x3.3 rows are form factors at 291 Wh/L, not real part numbers; the cell lane must find real protected packs (fast-charge rating O12c narrows the catalogue) [T]"
  - "Which DP is 'the same functionality'? DP1 and DP2 keep D18's words (>=8 h, ~12 h target) at nominal/pessimistic respectively. DP3-DP5 make the idle mode load-bearing for the 12 h target (the spec already says it is load-bearing for margin, §7 v0.14)."
```

## 3. Feature cost table (every feature on the list + found extras)

Columns: requirement source; lock status; pod mm3 now; mA now (mean, nominal); win if relaxed; functional loss.

```yaml
F01_runtime_target:
  what: ">=8 h min, ~12 h target, nightly charge; cell sized for pessimistic always-awake corner"
  src: "spec D18 (owner 2026-09-30), O1 resolved, §7 v0.14, O5"
  lock: "OWNER decision (not §1). Revisitable."
  cost_now: "cell 2226 mm3 raw, ~2800-3300 mm3 of pod incl. bay walls/gaps [E]; 4.2 g"
  win: "DP1 -1840 / DP3 -2300 mm3 gross; net of board-length fix -1450..-2100 [E]; -0.7..-1.5 g [E]"
  loss: "none at nominal current; short days possible on pessimistic draw / cold / aged cell; LED auto-off and a low-battery cue soften it"
  owner_call: yes
F02_eol_and_charge_voltage:
  what: "implicit: must 12 h hold after years? Charge to 4.10-4.15 V for cycle life (tws §3) costs 7-14 % capacity"
  src: "O19 (years of wear), tws-power-size.md §1 'best use of the margin'"
  lock: "not written anywhere -> owner should state it; it moves the cell +8..+25 %"
  win: "negative lever: deciding 'EOL 8 h, new 12 h' fixes the design point; deciding '12 h at EOL + 4.1 V' needs ~230 mAh (bigger than today)"
  owner_call: yes
F03_upper_band_96k:
  what: "20-96 kHz band -> SPH0641 ultrasonic mode at 4 MHz clock, 200 kS/s chain, 80 MHz MCU (algo B)"
  src: "spec §1.1 (LOCKED: 'roughly 20-96 kHz'); D13, D14 (realistic top ~80-85 kHz today)"
  lock: "§1 LOCKED. Owner only."
  cost_now: "mic 1.35 mA always-on [R power.py]; CPU 2.7 mA awake at 80 MHz [R power.py]; 0 mm3 direct"
  win_if_top_50_60k: "mic -> TDK T5838 (TDK InvenSense PDM MEMS mic, ultrasonic mode, characterised to 50 kHz): 500 uA at 1.8 V/4.8 MHz vs SPH0641 (Knowles/Syntiant PDM MEMS ultrasonic mic) 845 uA at 1.8 V/3.072 MHz [R tws/power.md S15b, T5838 Rev 1.0 11 Jun 2022; SPH0641 Rev B-1 2 Dec 2024] -> -0.3..-0.85 mA [E]; chain at ~100-125 kS/s -> CPU -0.8..-1.3 mA awake [E from D14 algo-A clock saving]. Total -1.1..-2.1 mA awake -> -280..-800 mm3 at 12 h awake-sized [E]"
  loss: "loses 60-96 kHz: higher-frequency bats (some to 110 kHz), many electronics whines; T3 localisation unaffected"
  owner_call: "yes, and it edits §1 -> not recommended"
F04_algorithm_and_clock:
  what: "algorithm B (log compression) at 80 MHz vs A (heterodyne) at 48-64 MHz"
  src: "spec D12 v0.11 (choose by listening), D14"
  lock: "owner decision by ear (Phase-1 listening)"
  win: "-0.8..-1.0 mA awake [R spec D14] -> -200..-400 mm3 if cell is awake-sized [E]"
  loss: "sound character (priority 5); B was preferred for pleasantness"
  owner_call: yes
F05_led_in_pad:
  what: "solid blue 0402 LED in the ear pad, PWM from PB7, 2 extra arm wires"
  src: "O8 resolved 2026-09-30 (owner: yes, battery cost accepted)"
  lock: "OWNER decision, revisitable"
  cost_now: "0.15-0.5 mA glowing (0.75 stacked worst) [R O8, tws]; 7.9 mm2 board, 2 of 4 arm wires, pad -50..-110 mm3 outside the pod [R MZM-17]"
  win: "-0.15..-0.75 mA -> -40..-300 mm3 (12 h) [E]; arm 4->2 wires; stowage -2 wires. PER-07 (LED on the pod lid) keeps an indicator: same mA, wins wires+pad only"
  loss: "power-on indicator gone (or moved to the pod lid where she can't see it either; visible to others)"
  owner_call: yes
F06_dock_5contact_usb:
  what: "magnetic 5-contact dock (VBUS, GND, D+, D-, CC) + USB FS DFU; USB-C receptacle keep-out reserved"
  src: "O12(a) 2026-09-30, O16(3), O18 (USB/DFU = most-verified path), O24(3) CC ESD"
  lock: "OWNER decisions"
  cost_now: "belly 2.05 mm x 25.5 mm = ~496 mm3 of pod (dock 'none' run) [E sens2]; 5 dock wires = 76-100 mm3 of the 107-142 mm3 stowage need [R MZM-01.stowage]; YZT0675 target 21.2x6.86x2.8 [R shell_r2.py L117]"
  win:
    a_thin_target: "-238 mm3 (size_budget DOCKS.thin, YZ103915020T, owner-built cable head) [R simplify/size SIZ-08; reproduced]"
    b_drop_usbc_keepout: "-53 mm3 [R SIZ-07]"
    c_3contact_uart_dfu: "VBUS, GND, 1-wire/UART: ST ROM bootloader on a USART instead of USB DFU [T: AN2606 pin list for U575 not checked]; a 2-3 pin magnetic pogo target ~2.2x12 mm [E hypothetical] -> -376 mm3 [E sens2]; -2..3 dock wires; drops CC ESD + USB ESD"
  loss: "a: none (needs a part family check); b: loses the USB-C fallback; c: needs a custom USB-UART cable/dock head, DFU path less proven (O18 conflict)"
  owner_call: yes
F07_armour_plate:
  what: "0.7 mm decorative armour plate on the outer face (also hosts the 0.8 mm hex mesh seat)"
  src: "shell styling (r1/r2), O17 spine theme; simplify/size SIZ-05"
  lock: "OWNER styling call (not a requirement)"
  cost_now: "540.3 mm2 x 0.7 = 378 mm3 [R size_budget PLATE_AREA]"
  win: "-379 mm3, T 10.40 -> 9.70, -0.45 g [E sens2]"
  loss: "none functional; look changes; mesh seat must move into the lid (lid 0.8 = seat depth 0.8 -> needs a 0.3 mm thicker local boss or a thinner mesh) [E]"
  owner_call: yes
F08_spine:
  what: "vertebra 'Spine' fin on top"
  src: "O17 (owner 2026-10-01)"
  cost_now: "159.6 mm3 [R size_budget SPINE]"
  win: "-160 mm3 or shrink by half -80"
  loss: "aesthetic only; she chose it"
  owner_call: yes
F09_walls:
  what: "0.8 mm resin walls/lid"
  src: "design rule (shell), not spec"
  lock: "engineering; durability touches O19"
  win: "0.6 mm: -386 mm3 [E sens2]"
  loss: "none functional; drop/sweat/crack risk on a years-worn part; print-yield"
  owner_call: "sign-off (durability)"
F10_stereo_independence:
  what: "two fully independent units, no wire or radio between them"
  src: "§1.1 'in stereo' (LOCKED) + D2 [High] (independence is D2, not §1)"
  lock: "stereo LOCKED; independence = design decision"
  win_if_shared: "one cell/one MCU feeding both sides over a wire across the brow/bridge: removes one board+dock (~1000-1500 mm3 [E]) from ONE side but moves the cell energy to the other or to the bridge; wires cross the hinge/frame; violates §1.2.4 comfort spirit and adds hinge-flex fatigue"
  loss: "wire across the face, glasses no longer fold freely; one dock per pair is a plus"
  rank: "not in top 10 (worst win/loss)"
F11_ip68_button:
  what: "C&K KMT022NGJLHS (IP68 tact switch, 0.65 mm) in a 0.4 mm lid pocket"
  src: "O16(7)"
  cost_now: "~0 mm3 in MZ-2 (pocket in lid); 0.65 mm Fgap if left on F (+390 mm3, the reason MZ-2 pockets it) [E sens]"
  alt: "capacitive touch through the shell (STM32U575 TSC): 0 mm3, no bore (better seal); but rain/sweat false touches -> conflicts IPX4-5 outdoor wear (O12b)"
  win: "~0 mm3"
  owner_call: "no action"
F12_sealed_mic_duct:
  what: "sealed straight duct ID 1.0, VHB annulus (one-face)"
  src: "O24(1)"
  cost: "~0 mm3 in MZ-2 [R MZM-01]"
  win: 0
F13_wire_stowage:
  what: "12 wires: 4 arm (OD 0.3), 5 dock (OD 0.8), 2 cell (0.6), 1 NTC (0.5)"
  src: "consequence of O7b arm wiring, O12/O16 dock, cell leads, NTC"
  cost_now: "need 107-142 mm3; free today (rear zone 147-212 mm3 behind a short board) [R MZM-01.stowage]"
  becomes_real: "with a 25 mm cell the rear zone vanishes -> stowage is real volume: 107-142 (or 31-42 with dock FPC tail MZM-03) [E]"
  win_levers: "dock FPC tail -76..-100 mm3 need; LED out -2 wires; NTC lead (if the cell pack has a built-in NTC lead it still needs a wire) 0"
F14_ntc_jeita:
  what: "NTC at the cell + BQ25180 (TI 1-cell Li-ion charger, I2C, power path, JEITA) TS input"
  src: "O12(c) fast charge temperature-qualified; O16(2)"
  cost: "0402 + 1 wire; ~0 mm3; a few uA [T]"
  rec: "KEEP (Li cell on the head, charged unattended overnight). Never a size item."
F15_charge_rate:
  what: "fastest practical charge, fast-charge-rated cell"
  src: "O12(c)"
  cost: "0 mm3 direct; NARROWS the cell catalogue (fewer small fast-charge packs) -> blocks F01 wins"
  win: "relaxing to <=0.5-1C overnight (spec §7 already says overnight 2.5-3 h) widens cell choice; with nightly charging a 70 mAh cell at 1C = ~1.2 h anyway [E]"
  loss: "slower top-up if she forgets to charge"
  owner_call: yes (enabler for F01)
F16_self_test_swd_testpads:
  what: "self-test sense resistor/links, SWD pads, TP pads, snap-off test frame"
  src: "O15, O18, O20 ('test access must not cost size')"
  cost: "area only: TP-1 ~4 mm2, WP-1 9.3 mm2, OUT-01 R4/R6 3.4 mm2 [R MZM-*]; 0 mm3 while board < cell; I_SENSE shunt (ERJ2BSFR10X, Panasonic 0402 0.1 ohm) ~0.01 mA-equivalent [E]"
  win: "0 mm3 today; ~0.2-0.6 mm board length each (~30-80 mm3) only once the cell is shorter than the board [E]"
  loss: "diagnosability (O18) -> not recommended"
F17_esd:
  what: "TPD1E10B06 (TI single-line ESD diode, 0402) on dock contacts (+CC per O24(3))"
  cost: "~1 mm2 each, nA leakage; 0 mm3"
  rec: "KEEP: exposed contacts on a daily-docked device"
F18_ldo:
  what: "TPS7A2030 (TI 300 mA low-noise LDO, 3.0 V) main rail"
  src: "D11, §7 supply rail"
  cost: "area ~1-2 mm2 + caps; quiescent a few uA [T]; dropout cuts usable capacity below ~3.3 V (power.py usable 0.85 already includes the knee)"
  alt: "battery-to-3.0 V buck: ~10 % less current (D11) -> ~-0.7 mA awake -> -170..-280 mm3 [E]; but self-noise/§1.2.3 risk; D11 rejected for that reason"
  owner_call: "yes (D11 by ear); low priority"
F19_crystal:
  what: "32.768 kHz crystal trimming MSI (Epson X1A0000610006, 2.0x1.2)"
  src: "D16 [High] (interaural pitch match in heterodyne)"
  cost: "~0.3 uA, ~3-5 mm2, 0 mm3 [R D16, MZM-*]"
  rec: "KEEP: tiny; protects T3 localisation"
F20_mic_supply:
  what: "mic on the 3.0 V rail at 4 MHz"
  src: "engineering (D13), not a requirement"
  win: "1.8 V mic rail (a second tiny LDO + level shift) -0.3..-0.5 mA always-on [R tws/power.md 3.6b, Low] -> -75..-200 mm3 [E]"
  loss: "none; +2-3 parts, O18 adds an unknown"
  owner_call: no (engineering, but O19 'never touch the schematic again' -> owner sees it)
F21_bridge_pwm_200k:
  what: "200 kHz 2-level PWM, discrete H-bridge"
  src: "§1.2.3 (LOCKED: PWM well above her hearing), D6"
  cost: "0.77 mA (0.49 bus + 0.28 gate) [R power.py]"
  win: "lower rate is the wrong direction (hearing + ultrasonic leak into own mic); low-Qg FETs already taken. ~0"
F22_niti_arm_pad:
  what: "20 mm NiTi arm, 100-150 mm2 Sugru pad, printed strut"
  src: "O7, O7b, O11, O16(4)"
  cost: "0 pod mm3 (outside the pod); pad/arm wire count only"
  win: "0 for the pod"
F23_one_board_both_pods:
  what: "one board design for both pods, mic + button on the centre line"
  src: "O16(5)"
  cost: "placement constraint only, ~0 mm3"
F24_no_screws_bonded:
  what: "no screws in the pod; adhesives (final), tape (test)"
  src: "O16(6), O10"
  cost: "already the small option"
```

## 4. Top 10 ranked by (win / functional loss)

Ranking uses: win = pod mm3 (net, [E]); loss scored 0 (none) / 1 (cosmetic or margin) / 2 (convenience) / 3 (capability). Ties broken by risk.

| # | Measure | Pod win mm3 [E] | Function loss | Owner call | Lock |
|---|---|---|---|---|---|
| 1 | **F01 runtime design point: 12 h at nominal always-awake (DP1) or measured duty (DP3); new cell ~70-110 mAh; board <= cell length** | -1450..-2100 net (-23..-34 %) | 1: margin only (short day at pessimistic draw / EOL) | YES (D18/O1/O5; and how to get E4 data under O20/O21) | owner |
| 2 | **F07 drop the 0.7 mm armour plate** | -379 (-6 %) | 0 (look; mesh seat moves) | YES (styling) | owner |
| 3 | **F06a thin dock target + F06b drop USB-C keep-out** | -238..-291 | 0..1 (owner-built cable head; no USB-C fallback) | YES (O16-3) | owner |
| 4 | F09 walls 0.8 -> 0.6 | -386 | 0 (durability risk) | sign-off | engineering |
| 5 | F05 LED out of the pad (or off) | -40..-300 via cell; 2 wires; pad smaller | 1: no on-indicator | YES (O8) | owner |
| 6 | F20 mic on a 1.8 V rail | -75..-200 via cell | 0 | sees it (O19) | engineering |
| 7 | F04 algorithm A at 48-64 MHz | -200..-400 via cell (awake-sized only) | 1-2: sound character | YES (by ear, D12) | owner |
| 8 | F08 spine halved/removed | -80..-160 | 0 (look) | YES (O17) | owner |
| 9 | F06c 3-contact dock, UART DFU | -376 (vs -238 for thin 5-contact) | 2: custom cable, DFU less proven (O18) | YES (O12a/O18) | owner |
| 10 | F03 band top 96 -> ~50-60 kHz (T5838 mic + slower chain) | -280..-800 via cell | 3: loses 60-96 kHz | YES, §1 edit | **§1 LOCKED** |

```yaml
combos [E, size_budget, fenced 2026-10-03]:
  no_function_loss_stack: "plate 0 + thin dock + walls/lid 0.6 on today's 175 mAh cell: 5265 mm3 (-994, -16 %), T 9.3 [E combo run sens3.py 01:20]"
  with_runtime_design_point: "DP1 cell (25x12x4.3) + plate 0 + thin dock + two-face board (Fgap 0.95 for SW1 on F): 4106 mm3 (-34 %), T 9.35 [E combo run sens3.py]; walls 0.6 would add ~-300 more"
  aggressive: "DP3 cell (25x12x3.3) + plate 0 + thin dock + two-face: 3675 mm3 (-41 %), T 8.35 [E combo run sens3.py]"
  mass_note: "combo runs kept cell_g 4.2 g; a 70-100 mAh pack is ~1.6-2.6 g [E] -> pod mass ~-1.6..-2.6 g more"
  floor_seen: "20x12x3.5 cell (~60 mAh at 291 Wh/L, likely ~45-50 real) + plate 0 + thin dock: 2928 gross, board would have to be ~20x12 (two-face + WLCSP) [E; not credible for rev 1]"
not_recommended: [F10 shared cell / cross-frame wire, F16 drop self-test (O18), F14 drop NTC (safety), F17 drop ESD, F21 lower PWM, F11 capacitive button (rain)]
```

## 5. Owner calls (explicit list)

```yaml
OC-1: "Runtime reading (F01): keep '12 h at the pessimistic always-awake corner' (175 mAh), or '12 h at nominal / 8 h pessimistic' (~100-115 mAh), or '12 h at measured duty, idle mode load-bearing' (~50-70 mAh)? Recommendation: DP1/DP2 (~100-115 mAh) ONLY with measured current; else keep 175 for rev 1."
OC-2: "E4 data under O20/O21: allow a measurement-only purchase (NUCLEO-U575ZI-Q + SPH0641 breakout + exciter, ~$60-80 [E]) before the freeze? It is the only way to make OC-1 evidence-based (O22). Conflicts with O18 'no bench rig' and O21 'no orders until final'."
OC-3: "End-of-life rule (F02): must 12 h hold at 80 % capacity, or 8 h at EOL? State it; it sets the cell more than any feature."
OC-4: "Armour plate off (F07), spine smaller (F08): styling."
OC-5: "Dock: thin target + no USB-C keep-out (F06a/b); 3-contact UART-DFU dock (F06c) only if she accepts a custom cable head."
OC-6: "LED (F05): keep, move to pod lid, or drop."
OC-7: "Algorithm by ear (F04) already pending; note it is also a size lever once the cell is current-sized."
OC-8: "§1 band top (F03): NOT recommended; listed for completeness."
```

## 6. Risks, cost, effort

```yaml
F01: {risk: "high without E4 (current is [Low] grade: transducer row is an untraced guess 0.4-2.5 mA); medium with E4", cost: "cell change ~$0 net; measurement rig ~$60-80 [E]", effort: "Claude 2-4 days (cell search, two-face board <= 26 mm re-placement, shell r3, re-run noise/thermal/sims per O22); owner: rig measurement 1 day + shipping wait"}
F07_F08: {risk: low, cost: 0, effort: "Claude 0.5 day (shell_r2 params, mesh seat in lid); owner review only"}
F06a_b: {risk: "medium: thin target family must carry 5 contacts and her cable head; sample blocked by O21", cost: "<$10 [E]", effort: "Claude 1 day; owner builds cable head 0.5 day"}
F09: {risk: "medium (cracks, sweat ingress over years)", cost: 0, effort: "Claude 0.5 day + FEM drop/press check; owner: print a coupon"}
F05: {risk: low, cost: 0, effort: "Claude 0.5 day (schematic Rev, arm wiring docs)"}
F20: {risk: "medium (new rail, level shift, mic mode at 1.8 V/4 MHz unverified)", cost: "<$1", effort: "Claude 1 day"}
F06c: {risk: "medium-high (DFU path O18)", cost: "custom head", effort: "Claude 2 days"}
F03: {risk: "§1", effort: "Claude 2-3 days (pipeline re-rate, mic swap, sims)"}
integration_map_crosscheck_brief: "F01 touches sub-power (rail-budget.yaml), reg-board (outline <= cell L), reg-pod-body (shell), physical.md (y/x stack), vcrm (runtime rows); F06 touches sub-dock-usb, sub-debug-test (DFU path), reg-pod-body belly; F07/F08/F09 reg-pod-body only (+ sub-audio-in mesh seat for F07); F05 reg-arm, reg-pad, sub-ui, pin-contract (PB7); F20 sub-audio-in, sub-power. tools/plm.py impact NOT run (read-only lane, time)."
```

## 7. Missing / not done (time limit 01:42)

```yaml
missing:
  - "no web/primary fetch this lane: all part currents are repo-cited datasheet points (dates as given in the repo notes); LDO/charger quiescent values [T]"
  - "no real cell part numbers for 50-115 mAh fast-charge protected packs (cell lane's job); density assumed 291 Wh/L, likely optimistic for small packs"
  - "three combo runs done (sens3.py); other combos not run"
  - "size_budget models L from the cell only; board-length constraint applied by hand (+210..390 mm3)"
  - "tools/plm.py impact not run; integration-map read only as a doc list"
  - "AN2606 USART bootloader pins for STM32U575 not verified (F06c)"
```
