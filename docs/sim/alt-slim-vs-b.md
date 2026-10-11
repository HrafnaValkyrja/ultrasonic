# Alternative test: slim B (P72) vs shipping B (P112) on Port Meadow (2026-10-11, SIMULATED)

Src: sim/perf/port_meadow.py new configs `slim`, `slim+loud12` (knob b_variant 1, A look-ahead, otherwise A defaults); 54 clips, 2059 calls, fenced 3G run 66 s; baseline re-blessed, all 8 prior configs bit-identical. Current model: fe405bf/2370328 (exciter physical term, bridge ripple 0.45 mA squelched); MCU row slim P72 R2 (dsp_icount "slim" 45.2-57.8 MHz) vs B P112 R1. Model, not bench. Firmware defaults unchanged. Runtime = 130 mAh x 0.85 usable at dense 81 % / walk 40 % / dusk 18 % awake (h).

| config | wake rec | sound rec | false wakes/min (scoring v2; v1 3.14) | lat p50 / p90 ms | level p50 / max dBFS | mean mA (scene) | dense / walk / dusk h |
|---|---|---|---|---|---|---|---|
| B (= "A", loud off) | 0.854 | 0.855 | 1.71 | 90.1 / 642 | -34.2 / -3.0 | 10.91 | 10.2 / 17.2 / 27.1 |
| slim | 0.854 | 0.850 | 1.71 | 89.7 / 643 | -34.5 / -3.5 | 9.07 | 12.2 / 20.0 / 30.2 |
| B + loud12 | 0.854 | 0.855 | 1.71 | 90.4 / 641 | -22.2 / -2.6 | 14.83 | 7.5 / 13.2 / 22.4 |
| slim + loud12 | 0.854 | 0.855 | 1.71 | 90.4 / 641 | -22.6 / -2.6 | 13.16 | 8.4 / 14.6 / 24.2 |

Awake mA (derived): B 12.83, slim 10.57; B+loud12 17.63, slim+loud12 15.59.

## Verdict
- Detection is identical: same wake recall, false wakes (1.71/min under scoring v2, was 3.14), latency. Only sound recall differs, -0.4 pt (0.855 -> 0.850, inside the 0.01 tolerance), and only with loud off. With loud12 it is equal. Level: -0.25 dB median, peak 0.5 dB lower (loud off); essentially equal with loud12.
- Slim saves 1.8 mA mean (-17 %) loud off, 1.7 mA (-11 %) with loud12: +2.0 h dense, +2.8 h walk, +3.1 h dusk (usable), i.e. +20 % / +16 % / +11 %.
- Yes, slim is the better trade on every metric the simulation sees, and it is a free win for a thin battery. It does not hear a difference between 16 and 28 bands: spectral/audio quality is NOT measured here, so the E2 listening test decides. Recommendation: keep B as default until E2; if she cannot hear the difference, switch to slim (variant + P72; needs an ECR, fwsim rerun, DWT check at P72 80 % load). Owner decides.
- Caveat: bridge normalisation kept at ARR 280 in the sim (duty is clock-independent, so the exciter term is unchanged); the slim MCU current is the nominal row from runtime_fw.py, not bench.
