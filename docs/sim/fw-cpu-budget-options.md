# fw CPU budget: variant/clock resolution (2026-10-11, follows fw-target-budget-2026-10-11.md, bd287ea)

## 1. What ships, and was it known
- Shipping variant: algo=2, b_variant=0 = spec B, 28 bands (fw/spec/knobs.yaml L46, L52; slim = b_variant 1, "listening test E2 chooses").
- Shipping CLOCK is not 80 MHz. Design plan for spec B is **P112 = 112.012 MHz, Range 1** (fw/port_u575/hal_u575_sys.c L27; sim/checks/runtime_fw.py docstring, round 10, 2026-10-07: "lowest DS13737 point that keeps the QEMU-corrected worst load <= 80 %"). Slim = P72, A = P52, P104 = alternative.
- Known before: V4-cycles.yaml (2026-10-07) B_spec "doesn't fit at 55 MHz, ~88 MHz needed, tight at 80". The finding's "80 MHz plan clock" came from shared-params hop_cycles_at_hclk (51,200 = P80, the legacy A3 plan) and from knob **clock_plan default 0 = P80** (knobs.yaml L62; app.c L129 applies it). So the inconsistency is real but it is a knob default, not a design miss: the default knob (P80) disagrees with the design plan (P112) and with the power model.
- Hop budget (128 x HCLK / 200,022.5): P80 51,200; P104 66.4 k; P110 70.4 k; **P112 71,680**; P160 102,400.

## 2. Measure-grade numbers (spec B, look-ahead on, loud 12 + shape worst case; MHz incl. V4 overhead)
| basis | MHz | P80 | P112 | P160 |
|---|---|---|---|---|
| static model (0 WS, upper bound, pessimistic) | 81.0-103.9 | 130 % | 93 % | 65 % |
| QEMU insn count x CPI-corrected (dsp_icount.json 67.6-86.7, +0.9 loud/shape) | 68.5-87.6 | 110 % | **78 %** | 55 % |
| + cold-ICACHE envelope (V4: +2.5 MHz per flash WS: P112 3 WS = +7.5; P160 4 WS = +10) | hi 95.1 / 97.6 | - | 85 % | 61 % |
Flash WS (RM0456 Rev 7 Table 54): 80 MHz R2 = 2 WS; 112 MHz R1 = 3 WS; 160 MHz R1 = 4 WS. Hot code 6.5 KB + ISRs vs 8 KB ICACHE: fits warm, so cold is an envelope not an expectation (V4 assumption U4, conf L). R48 PASS rule is <= 80 %: P112 passes on the corrected number (78 %), fails only on the static bound and the cold envelope. Nothing here is measured; DWT CYCCNT on rev-1 (FWSIM-R49) closes it.
Top B costs (cycles/hop, static): fft_cfft128 11.1-13.8 k, fw_dsp_out (200 kHz shaper+interp, fixed) 10.4-12.8 k, b_synth 7.8-8.6 k, b_update 4.3-5.5 k, b_bands 3.1-4.0 k, fft_pack_ring 3.0-3.5 k, fft_split 2.7-3.4 k.

## 3. Options (MCU current: DS13737 Rev 10 Table 39/46 via sim/checks/runtime_fw.py, SMPS 3.0 V 25 C typ; model, not bench)
| | clock/variant | B load hi (qemu) | MCU mA (nom) | awake mA (lo/nom/hi) | verdict |
|---|---|---|---|---|---|
| **A0 (rec.)** | B at P112 R1 (as designed) | 78 % | 4.54 | 6.73 / 8.38 / 11.56 | R48 PASS on corrected |
| A1 | B at P110 R2 (110.0 MHz, 3 WS) | 79 % | 3.75 | 6.03 / 7.58 / 10.65 | saves 0.8 mA awake, but 79 % has no margin; try only if DWT reads <= 70 % |
| A2 | B at P104 R2 | 83 % | 3.66 | 5.91 / 7.45 / 10.50 | fails 80 % |
| A3 | B at P160 R1 | 55 % | 4.82 | 7.31 / 9.02 / 12.34 | fallback: +0.64 mA awake nom vs P112 (about -5 % runtime in the dense Port Meadow scene, 81 % awake) |
| B | optimise B hop | - | - | - | below |
| C | slim at P72 R2 | 80 % (45.2-57.8 / 72) | 2.63 | 4.76 / 6.19 / 9.06 | saves 2.2 mA awake nom vs P112 (about 20 % of the 10.6 mA scene mean, runtime +20-25 %); recall below |
R1 vs R2 step is the cost driver: P104 -> P112 jumps +0.93 mA awake for +8 MHz (R1 run 5.8 mA at 120 MHz vs R2 4.4 at 110).

**B (optimise), estimates, not implemented.** fft_cfft128 is already radix-2^2 fused (dsp.c L251). A CMSIS-style radix-4 + radix-2 f32 128-pt would save ~25-30 % of 11-14 k = 3-4 k cycles (4-6 % of a P112 hop). Fixed-point q15 FFT/bands: larger saving (V4 lever list) but changes numerics and the 0.854/0.855 baseline. Band merging 28 -> 24: -14 % of b_synth+b_update+b_bands (15-18 k) = 2.2-2.6 k, a behaviour change. Together 5-7 k: worst 55-56 k static = still > P80 (51.2 k), only helps the P104/P110 clocks (e.g. P104 static hi 84 %). No change is cheap AND behaviour-neutral AND needs fwsim re-verification, so none implemented. fw_dsp_out (10-13 k) is shared by all variants and is the other big lever (shaper order, FMAC offload exists already).

**C (slim) loses**, Port Meadow 54 clips / 2059 calls, scratch run 2026-10-11 (`b_variant=1`, look-ahead on): wake recall 0.854 -> 0.854, sound recall 0.855 -> 0.850 (-0.5 pt, tol 0.01), false wakes 3.14/min unchanged, latency p50 90.1 -> 89.7 ms, level p50 -34.2 -> -34.5 dBFS. The metric does not see 16 vs 28 bands spectral quality (E2 listening test decides).

## 4. Recommendation
1. Keep B and P112 (A0). Fix the one-line inconsistency: knob `clock_plan` default 0 (P80) -> 4 (P112) and make shared-params hop_cycles reflect it (not done: it changes the fwsim hop budget/QEMU timing and needs an ECR/gate rerun; the owner/integrator should schedule it).
2. Keep P160 as the DWT-triggered fallback (plan implemented, +0.64 mA).
3. Slim/P72 stays the E2 listening-test alternative: if she cannot hear the 28-band difference, slim saves ~2 mA awake for -0.5 pt recall. Owner decides.
4. Rev-1 DWT measurement with ICACHE on decides A1 (P110) vs A0 vs A3.
Integration-map cross-check: touches sub-processing (clock plan), shared-params clocks, knobs.yaml, power model; no PLM design change made, no docs/system edits.
