# B-thin: thinnest pod, blind design (2026-10-08)
Source: BRIEF-blind.md only. Part facts are from memory, NOT web-verified; every `[v]` needs a datasheet check. Numbers are estimates.

## Concept: "single-deck slab"
Break the usual stack (cell on top of board). Cell and electronics sit **side by side in one layer** along the arm, so thickness = cell thickness + two shell walls, not cell + board. Cost is length; the brief ranks length last.
- Rear (toward ear, in front of the hook): pouch cell, 3.0 x 15 x 35 mm, ~130 mAh [v] (ref: 302030 pouch ~150 mAh at 1.8 cm3 => ~83 mAh/cm3; 1.575 cm3 => ~130). Protection IC in the cell (R23). Rear placement also moves mass toward the ear.
- Front (toward hinge): one rigid-flex board, 0.8 mm FR4 rigid island 15 x 18 mm, one flex tail to the exciter arm, one flex tail to the cell tabs. Parts one side only, <=1.0 mm tall, so deck = 0.8+1.0+0.2 = 2.0 mm < cell 3.0 mm. Cell sets thickness.
- Output: thin 8 mm-class electromagnetic exciter, 2.0 mm tall [v], on a printed swept arm (flex runs inside). Option B piezo bender (1 mm, capacitive, easy for H-bridge) but only ~6 Vpp from 3 V: weak below 4 kHz; reject unless a bench test shows enough drive. Option C cheekbone fallback = same exciter, longer arm.

## Parts (gloss)
- Mic: Knowles SPH0641LU4H-1 [v] (ultrasonic PDM MEMS mic, 3.5 x 2.65 x 0.98 mm, bottom-port); port through the pod's outer face, mesh + EQ (D13).
- MCU: STM32U3-class Cortex-M33 (ST ultra-low-power Arm core with DSP, ~10 uA/MHz [v]), WLCSP; internal core SMPS only (D11). Runs PDM decimation, EQ, shift, gate, PWM ~200 kHz. 32.768 kHz crystal (3.2x1.5).
- Charger/power-path/LDO: TI BQ25155 [v] (I2C linear charger, NTC pin for JEITA, 150 mA 3.0 V LDO, ship mode), WCSP ~2 x 1.9. One chip gives charge + rail + battery level link: fewer parts.
- H-bridge: small dual-FET/half-bridge pair (e.g. 2 x TI TPS-class load switches or discrete N/P pairs), off until timer owns gates (pull-downs).
- ESD: 1 TVS array (4-ch, 0402-size) on the 4 dock pads. Button: dome switch on board under a thin printed membrane, 1.2 mm. LED: 0402 LED, light-pipe-less (shell thin window).
- Dock: 4 flush 2 mm gold pads + 3 x 1 mm magnet on outer-front face (VBUS, GND, D+, D-/SWD shared); dock holds pogo pins. Zero protrusion.
- Part count: ~11 actives/mech + ~22 passives = ~33 BOM lines, 1 board, 1 cell, 1 exciter.

## Section (along arm, top view of layers)
```
 hinge <--- front ---------------------------- rear ---> ear hook
 | mic+MCU+chg+bridge+btn |flex| CELL 3.0 x15x35 |      exciter arm sweeps back-down to tragus
 |==== board 2.0 tall ====|    |===== 3.0 =====|
 [outer wall 0.5][ parts ][inner wall 0.5][clasp C-hook on arm lower edge]
 THICKNESS: 0.5 + 3.0 + 0.3 (tape) + 0.5 = 4.3 mm outboard of the arm
```
Assembly (9 steps): 1 JLC rigid-flex PCBA arrives; 2 solder cell tabs to flex pads (hot bar/hand, kapton); 3 test-charge on bench, supervised (R23); 4 seat cell in rear pocket with tape; 5 solder 2 exciter wires/flex to arm, seal with potting; 6 fold flex, seat board in front pocket; 7 snap/glue inner shell (printed, sealed seam with silicone); 8 insert magnet, check pads flush; 9 clip to frame adapter. Cell replaceable: step 2/4 reversed (tabs are pads, not welded).

## Numbers
- T x H x L = **4.3 x 15 x ~58 mm**; starts X >= 30 mm from hinge (just past the 29.5 vision line), ends ~88 mm, within 60 mm usable [flag: assumes usable length counts from 30 mm; confirm]. Trades length for thickness.
- Mass: cell 3.1 g (130 mAh x 3.8 V = 0.49 Wh at ~160 Wh/kg incl. leads), PCBA 1.0, shell 0.9 (~0.8 cm3 PA12 at 1.0 g/cm3 + silicone), exciter + arm 0.9, clasp/adapter 0.6 => **~6.5 g**. Rear-weighted: ~2.5 g nose / ~4.0 g ear (lever estimate, `[Low]`). Beats 7.3-8.8 g by ~1-2 g.
- Current (rail side, 3.0 V LDO so cell current = load current): mic 0.9 mA [v], MCU 30% duty x 96 MHz x 10 uA = ~2.9, bridge+exciter average ~1.5 (quiet scene) to ~6 (loud), LED+misc 0.3 => normal ~5.6 mA, worst ~11 mA. Usable 90% of 130 = 117 mAh => **normal ~21 h, worst ~10.6 h** (>= 8 h). Margin thin on worst; each +1 mA costs ~1 h.
- Charge: 0.5C = 65 mA max; use 40 mA (0.3C). Chain: cell PCM (over/under-V, over-I, short) -> BQ25155 NTC/JEITA -> I2C limit -> no output when VBUS sensed (firmware + bridge gate pull-down). ~3 h to full.
- Band: out 1.5-4 kHz, floor 1.5 (D9). Ceiling: soft clip set so bridge peak <= 1.2 Vpk into exciter (~80 dB re 1 g? **unmeasured**; no numeric target in spec, so I propose: ceiling = loudest level that passes S2 minus 6 dB, tuned in E2). Loudness reasoning: tragus gives ~10 dB over cheek (D1); 3 V bridge into 8 ohm gives 0.56 W peak, >100x headroom over the ~5 mW average, so the limiter, not the supply, sets level.
- Self-noise: PWM at 200 kHz is out of her hearing only if filtered by exciter inductance/mechanics (exciter mechanical response falls >5 kHz); LDO noise ~10 uV/rtHz class [v]; mic SNR ~65 dB [v]. Target below ambient bedroom floor (~30 dBA); verify T6.

## Beats / loses
Beats: thickness 4.3 mm (stacked designs need cell 3.0 + board 2.0 + walls 1.0 = ~6+ mm; ~30% thinner), mass ~6.5 g, part count ~33, charging is one chip. Loses: length (58 vs ~40 stacked), longer foil rigid-flex cost (irrelevant per O19), cell cannot be larger without growing L, exciter 2 mm tall adds a swept arm, runtime worst-day margin only ~2.6 h. T1-T6: no design item prevents them; T3/T5 untested.

## Hard-no's stretched
None knowingly. Vision line is touched: pod begins at 30 mm; needs E10 measurement. Unverified datasheet currents [v] are the biggest risk; evidence = bench current log over a full mode cycle.
