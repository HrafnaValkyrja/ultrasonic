# Port Meadow end-to-end performance regression (2026-10-08)

Script `sim/perf/port_meadow.py`, baseline `sim/perf/port_meadow_baseline.json`, runtime ~95 s fenced (3G). `--bless` rewrites the baseline; default run exits 1 if any metric leaves its tolerance.
Data: Zenodo 22079773 (Port Meadow, AudioMoth 192 kS/s, CC-BY-4.0), receiver_3 of all 54 flypasts, 2059 annotated calls (BatDetect2 det_prob >= 0.5), 210 s scored. One global Pa scale (loudest 10 ms of the 172626 clip = 75 dB SPL; calibration unknown). Each clip tiled 3x, last copy scored. Chain: sim/e2e front end -> host firmware (spec B, transient only, idle detector on).
Configs: today = defaults; A = lim_lookahead 1 (D17 rec A, fbfb38b); A+loud4/12 = A + loud_db 4/12 with the loud toggle on (bf5d6bd); hiz_idle = today + hiz_idle 1 (fdac294).

| metric | today | A | A+loud4 | A+loud12 | hiz_idle | tol (abs) |
|---|---|---|---|---|---|---|
| wake recall (awake <=10 ms after call start) | 0.854 | 0.854 | 0.854 | 0.854 | 0.854 | 0.01 |
| sound recall (output unsquelched <=30 ms) | 0.855 | 0.855 | 0.855 | 0.855 | 0.855 | 0.01 |
| false wakes /min (real clips, upper bound) | 3.14 | 3.14 | 3.14 | 3.14 | 3.14 | 2.0 |
| false-awake fraction (>50 ms from a call) | 0.082 | 0.082 | 0.082 | 0.082 | 0.082 | 0.01 |
| false wakes /min, call-free scenes (silence, house walk) | 10.0 | 10.0 | 10.0 | 10.0 | 10.0 | informational |
| wake-to-sound latency p50 / p90 (ms) | 89.7 / 641 | 90.1 / 642 | 90.4 / 641 | 90.4 / 641 | 89.7 / 641 | 0.7 / 1.4 |
| output level per call p50 (dBFS pre-quantiser) | -34.2 | -34.2 | -30.2 | -22.3 | -34.2 | 0.3 |
| output level per call max (dBFS) | -12.0 | -3.4 | -3.0 | -3.0 | -12.0 | 0.3 |
| awake fraction | 0.815 | 0.815 | 0.815 | 0.815 | 0.815 | (via mean mA) |
| mean current (mA, model) | 7.154 | 7.192 | 7.333 | 7.799 | 7.152 | 0.02 |

Reading it
- Wake, false-wake and awake numbers are identical across configs: the knobs act downstream of the idle detector. Only the output side and current move.
- A raises the peak ceiling (-12 -> -3.4 dBFS) with p50 unchanged; loud12 lifts the median call +12 dB and the ceiling is held by the limiter/clamp (-3.0).
- Mean current: +0.04 mA (A), +0.18 (loud4), +0.65 (loud12) over today; hiz_idle saves only 0.002 mA here because the pod is awake 81 % of this dense bat scene and rarely squelched while awake. Its real win is quiet scenes (not scored by the model: IDLE row has no bridge term).
- Caveats: false wakes use incomplete labels (real calls unlabelled count as false); latency is first-call-of-episode to first unsquelched hop and includes the algorithm's own gating (p90 is dominated by trains where the squelch stays closed); the current is the runtime_fw.py B1 model (spec B P112, exciter 1.1 mA guess scaled by PWM drive), not a bench number; the 3x tiling makes the scene stationary.
