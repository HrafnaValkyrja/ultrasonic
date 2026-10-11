# Alternative test: firmware-side false-wake cuts on Port Meadow (2026-10-11, SIMULATED)

Src: `sim/perf/alt_false_wake.py` (new), knobs in `fw/spec/knobs.yaml` -> `fw/gen/knobs_def.h`, code in `fw/core/idle.c`. Shipping B (idle_enable 1, A look-ahead, loud off) vs 3 idle-detector alternatives, all default 0 = bit-identical (port_meadow baseline PASS, 74.6 s fenced). Split: even-index clips = TRAIN (pick the value), odd = HOLDOUT (report); the 2 quiet scenes are in both. Model, not bench. False wakes/min here include the quiet scenes, so B reads 4.17/3.53 not the 3.14 of alt-slim-vs-b.md (real clips only). One event is about 0.5/min: differences of one step are noise.

- ALT-1 `idle_confirm` N: wake needs N consecutive 5 ms hits.
- ALT-2 `idle_width_max` W: reject a hit if more than W of the 83 bins are >= thr/10 over floor (broadband click vs narrow call: the band-shape check).
- ALT-3 `idle_adapt_pct` P: threshold = max(15 dB, P % x 5 s EMA of min(best-bin ratio, thr)).
- FM-sweep (bin-moves-between-frames) check dropped: calls are 1-3 frames long, so it would be ALT-1 in disguise.

| cfg | split | wake rec | false wakes/min | lat p50 / p95 ms | mean mA | dense / dusk h |
|---|---|---|---|---|---|---|
| B | train | 0.850 | 4.17 | 112 / 738 | 10.83 | 10.3 / 29.4 |
| B | hold | 0.858 | 3.53 | 87 / 669 | 10.99 | 10.1 / 29.0 |
| confirm 2 | train / hold | 0.288 / 0.359 | 6.26 / 5.04 | 1201 / 808 p50 | n/a | n/a |
| confirm 3 | train / hold | 0.056 / 0.090 | 4.70 / 4.54 | 1524 / 1314 p50 | n/a | n/a |
| width 25 | train / hold | 0.793 / 0.791 | 4.70 / 4.54 | 212 / 95 p50 | 9.91 / 10.06 | 10.5 / 10.2 dense |
| width 40 | train | 0.846 | 3.65 | 112 / 738 | 10.73 | 10.3 / 29.6 |
| width 40 | hold | 0.852 | 3.53 | 87 / 669 | 10.89 | 10.1 / 29.0 |
| width 60 | train / hold | 0.849 / 0.858 | 3.65 / 3.03 | 112 / 738 (both) | 10.80 / 11.00 | 10.3 / 10.1 dense |
| adapt 300 % | train / hold | 0.849 / 0.852 | 4.17 / 3.53 | 107 / 87 p50 | 10.80 / 10.95 | 10.3 / 10.1 dense |
| adapt 500 % | train / hold | 0.821 / 0.840 | 4.70 / 4.54 | 266 / 86 p50 | 10.53 / 10.84 | 10.3 / 10.0 dense |
| adapt 800 % | train / hold | 0.772 / 0.808 | 4.17 / 4.03 | 595 / 86 p50 | 10.05 / 10.59 | 10.3 / 10.0 dense |

Other rows (confirm 4, width 15, adapt 1200) are in the run JSON and are worse: recall 0.03-0.73. Dense/dusk hours: 130 mAh x 0.85 over the corrected current model at 81 % / 18 % awake, shifted by each config's change in false-awake time. mean mA of low-recall configs is low only because they stay asleep through calls; ignore it.

## Verdict
- None of the three is a win. Every setting that cuts false wakes also cuts recall by about as much or more, or changes nothing: the best (width 60) removes one event on holdout (3.53 -> 3.03/min) and zero-to-one on train at -0.1 to +0.0 pt recall, which is inside noise; its dense runtime gain is 0.0 h and dusk +0.0 h.
- Confirm-N is a disaster (recall 0.29 at N=2): calls give isolated single hits, not runs. Adaptive threshold costs recall and latency (p50 107 -> 595 ms at 800 %) for no false-wake reduction.
- Reading: the "false" wakes are most likely real in-band sound (insects, unlabelled calls, house clicks) that is narrowband too, so a detector cannot separate them from calls; only labelled ground truth for what they are would. Cost of the cuts is not the issue: CPU is a non-factor (about 100-300 extra cycles per 5.12 ms snapshot against 573 k cycles at P112, under 0.1 %; hand estimate, not measured on target).
- Recommendation: keep shipping defaults (all three knobs stay 0). Do not spend the false-wake budget on detector tricks; the lever is cheaper wakes (the awake-current of a false wake, e.g. a short hang of 0.3 s -> 0.15 s) or an owner-tunable sensitivity. Owner decides.
- Caveat: 54 clips from one site, about 50 false events in total, so the holdout resolves only effects above ~1/min. The knobs stay in the code (guarded) for E-series bench A/B.
