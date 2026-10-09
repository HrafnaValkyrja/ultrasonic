# Current models reconciled: d17-cost.md vs sim/perf/port_meadow.py (2026-10-08)

Verdict: **neither was a wrong bridge law, but #2 (port_meadow) had a wrong exciter model and a wrong hiz_idle accounting; #1 (d17-cost) is right for its scope (loud programme playback) and was mis-read as the worn-outdoors cost.** Both fixed/labelled.

## Side by side
| Input | d17-cost.md | port_meadow.py (before) | port_meadow.py (now) |
|---|---|---|---|
| Programme | `2_translated_only.wav`: 4 bat passes, every call scaled to 75 dB SPL, file peak -9.5 dBFS, 51 % active frames; or 100 % continuous | 54 real flypass clips, one global scale, call p50 -34 dBFS (A+loud12: -22), pod gated by idle detector (81 % awake in this dense scene) | same |
| Bridge law | 0.327 A x mean|x| (physical, no L filtering) | 1.1 mA GUESS (PWR-04) x (mean|CCR-centre| / today's) | 0.327 A x mean(|CCR-centre|/128) on awake hops |
| Delta loud12 vs today | +12 mA dense (2.4 -> 14.5), +21 continuous | +0.65 mA | +3.05 mA |
| hiz_idle | n/a (D-hiz-idle: 0.45 mA when bridge idles at 50 %) | credit only on awake+squelched hops = 0.56 % of awake hops -> 0.002 mA | 0.45 mA x squelched fraction: 0.08 mA (this scene), ~0.37 mA at 82 % squelched |

## Why they differed
1. **Level and density, not physics.** d17's programme is playback at the top of the range with 51 % of frames active and the limiter saturating (+12 dB into a 0.52 ceiling). Port Meadow calls are mostly far flypasts (p50 -34 dBFS) in short bursts; +12 dB lifts them to -22 dBFS, nowhere near the ceiling for most of the time. Same bridge law, 4x lower |x|.
2. **#2's exciter term was anchored to a guess.** Scaling 1.1 mA by a drive ratio cannot respond to level: physically the bridge on this scene averages 4.2 mA (today, all hops; 5.2 on awake hops) rising to 7.3 (8.9) at loud12. The ratio method gave +0.65 where the same law gives +3.05. Fixed.
3. **hiz_idle accounting.** In firmware, squelch means IDLE: set on 19 % of all hops but 0.6 % of awake hops. The old model credited only awake-and-squelched hops and charged no bridge ripple in IDLE, so the saving was ~0. The ripple (D-hiz-idle s1: bridge keeps switching) is now charged on squelched hops unless hiz_idle. The 0.45 mA headline is real but scales with time squelched.

## Which reflects wearing it outdoors at dusk
port_meadow (new). The pod's output there is the ambient, translated by the gate, at physical levels; d17 is a loud-programme/mode ceiling. Caveat both ways: awake bridge current (5-9 mA) includes noise passing the squelch and ignores coil L (tau ~ 40 us) filtering, so it is an upper bound [E]; the 75 dB SPL calibration is assumed; bench PWR-I12 not done.

## Runtime under real use (130 mAh nominal; 0.85 usable in brackets), hours
Awake fraction: dense flypasts 81 % (the clips) / bat-rich walk 40 % / quiet dusk 18 % (rail-budget expected case). Awake current from the scene, idle 1.60 mA, LED 0.08.
| Config | mean mA (dense) | dense 81 % | walk 40 % | dusk 18 % |
|---|---|---|---|---|
| today | 10.58 | 12.3 (10.4) | 20.7 (17.6) | 32.5 (27.6) |
| A (limiter) | 10.76 | 12.1 (10.3) | 20.4 (17.4) | 32.2 (27.4) |
| A+loud4 | 11.43 | 11.4 (9.7) | 19.4 (16.5) | 31.1 (26.4) |
| A+loud12 | 13.63 | 9.5 (8.1) | 16.7 (14.2) | 27.8 (23.7) |
| hiz_idle | 10.50 | 12.4 (10.5) | 21.6 (18.4) | 35.8 (30.5) |
So loud12 costs ~3 mA when awake in bats and still clears 8 h even in the dense scene with derating (8.1 h); the d17 4-6 h result applies only to continuous loud-programme playback (cafe/car mode).
Changed: `sim/perf/port_meadow.py` (current model; baseline re-blessed, mean_ma only), `sim/perf/port_meadow_current.py` (physical check), docs/sim/perf-port-meadow.md, d17-cost.md (scope), D-hiz-idle.md (scope note).
