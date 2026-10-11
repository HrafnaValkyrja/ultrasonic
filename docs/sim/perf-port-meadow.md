# Port Meadow end-to-end performance regression (2026-10-08; table re-run 2026-10-11)

**2026-10-11 re-run (authoritative):** after fe405bf (bridge duty normalised by plan ARR/2) and a070a87 (shipping clock P112, ECR-0027), baseline PASS, 54 clips, 2059 calls. Mean mA (dense) / runtime h on 130 mAh (0.85 usable) at dense 81 % / walk 40 % / dusk 18 % awake (aw = awake mA from scene; idle 1.60 + 0.45 bridge ripple unless hiz_idle; LED 0.08):

| config | mean mA | dense 81 % | walk 40 % | dusk 18 % |
|---|---|---|---|---|
| today | 10.67 | 12.2 (10.4) | 20.6 (17.5) | 32.4 (27.5) |
| A (shipping, loud off at boot) | 10.91 | 11.9 (10.1) | 20.2 (17.2) | 31.9 (27.1) |
| A+loud4 | 11.82 | 11.0 (9.3) | 18.9 (16.0) | 30.4 (25.9) |
| A+loud12 | 14.83 | 8.8 (7.5) | 15.5 (13.2) | 26.3 (22.4) |
| A+loud12+shape | 19.86 | 6.5 (5.6) | 12.0 (10.2) | 21.5 (18.3) |
| hiz_idle | 10.59 | 12.3 (10.4) | 21.5 (18.3) | 35.6 (30.3) |

Old -> new mean mA: 10.58->10.67, 10.76->10.91, 11.43->11.82, 13.63->14.83, 10.50->10.59 (shape 17.36 [10-08 re-bless] -> 19.86). Level/latency/recall rows below unchanged except A max -3.4 -> -3.0, loud max -3.0 -> -2.6 dBFS. Older tables below (10-08) are superseded; they quoted pre-fix currents.

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
| output level per call max (dBFS) | -12.0 | -3.0 | -2.6 | -2.6 | -12.0 | 0.3 |
| awake fraction | 0.815 | 0.815 | 0.815 | 0.815 | 0.815 | (via mean mA) |
| mean current (mA, model, this scene, reconciled 2026-10-08) | 10.67 | 10.91 | 11.82 | 14.83 | 10.59 | 0.02 |

Reading it
- Wake, false-wake and awake numbers are identical across configs: the knobs act downstream of the idle detector. Only the output side and current move.
- A raises the peak ceiling (-12 -> -3.4 dBFS) with p50 unchanged; loud12 lifts the median call +12 dB and the ceiling is held by the limiter/clamp (-3.0).
- Mean current (reconciled, see docs/proof/electrical/current-models-reconciled.md): exciter is now physical, 0.327 A x mean|x| (x = |CCR-centre|/128) on awake hops, not the 1.1 mA guess scaled by relative drive (that anchored on a guess and understated the delta ~5x). Delta over today: +0.18 (A), +0.85 (loud4), +3.05 (loud12) mA. Awake-hop bridge current 5.2 / 5.4 / 8.9 mA (today / A / loud12) is an upper bound: it includes ambient/noise that passes the squelch and ignores coil L filtering.
- hiz_idle: squelch is set on 19 % of hops but on only 0.6 % of awake hops (it is the IDLE state), so the old awake-only credit was ~0. Squelched hops keep the bridge's 0.45 mA switching ripple (D-hiz-idle.md s1) which the IDLE row omits; now charged to every config but hiz_idle. Saving here 0.08 mA (19 % squelched); in a quiet scene (82 % squelched) ~0.37 mA.
- Runtime on 130 mAh nominal (0.85 usable in brackets), if the whole day looked like: dense flypasts (81 % awake) / bat-rich walk (40 %) / quiet dusk (18 %): today 12.3 (10.4) / 20.7 (17.6) / 32.5 (27.6) h; A 12.1 / 20.4 / 32.2; loud12 9.5 (8.1) / 16.7 (14.2) / 27.8 (23.7); hiz_idle 12.4 / 21.6 / 35.8 h.
- Dense-scene runtime per config at the re-blessed 2026-10-08 baseline, 130 mAh cell (K4/K1t; 0.85 usable in brackets; the 175 mAh Renata cell is not the K4 cell): today 12.2 (10.4) h; A 12.0 (10.2); A+loud4 11.3 (9.6); A+loud12 9.5 (8.1); A+loud12+shape 7.5 (6.4) at 17.36 mA; hiz_idle 12.3 (10.5). Shape (loud mode on all day, worst case) costs 2 h nominal / 1.7 h usable vs loud12 alone.
- Baseline drift at the D17 re-bless: every config rose +0.0512 mA (today 10.5834 -> 10.6346 etc.), identical across configs, though the configs pin lim_lookahead/loud_db explicitly. Cause: `current()` takes the awake MCU load from `fw/out/dsp_icount.json` (gitignored, regenerated by each `fwsim all`), measured with the default knobs; the D17 default `lim_lookahead 1` adds the look-ahead limiter to the hop path, 33051 -> 33602 qemu insns/hop (+551, +1.7 %, spec B), i.e. +0.063 mA awake x 0.8148 awake = +0.051 mA. It is a measurement-basis shift, not a model or config change; the 'today' row now carries the look-ahead hop load though its output is legacy.
- Caveats: false wakes use incomplete labels (real calls unlabelled count as false); latency is first-call-of-episode to first unsquelched hop and includes the algorithm's own gating (p90 is dominated by trains where the squelch stays closed); the current is the runtime_fw.py B1 model (spec B P112) with a physical exciter term; 128 counts per unit duty read off today's 32-count / 0.251 peak, not a bench number; the 3x tiling makes the scene stationary.

## Scoring v2 (2026-10-11): false-wake rule only
Triage (docs/sim/false-wake-audibility.md) showed the v1 false-wake count (3.14/min, 11 real-clip events over 210 s) mixed labelling gaps with detector behaviour. Only the false-wake rule changed; recall, latency, level, current are bit-identical to v1 (checked all 10 configs). Old numbers stay in `sim/perf/port_meadow_baseline.json` under `v1_baseline` and as `false_wakes_per_min_v1`. Detection and firmware untouched. `scoring_version` = 2 in the JSON; tolerance check unchanged.

| rule (applied in this order, per IDLE->awake edge not excused by v1) | evidence (config A, same set in every config) | events removed |
|---|---|---|
| splice: ignore edges within 20 ms of the scored copy start or end | 175718 @4.996 s, 4 ms blip at the clip loop edge (simulation artefact) | 1 |
| unlabelled 15-40 kHz burst KEPT as false: onset +-30 ms shows >= 10 dB over the clip median in 15-25 or 25-40 kHz | 173324 @1.08, 174048 @3.51, 174106 @0.88, 174242 @0.64 and @1.07, 174648 @3.87 (insect or low bat, unresolved; the spectrogram triage listed 3, 6, 9, 10 and 8 as such; 174106 = triage #7 also has 15-40 kHz energy so it stays) | 0 (6 kept) |
| label tolerance +-50 ms (v1: -10 / +30 ms) and labels det_prob >= 0.3 also excuse (recall denominator stays det >= 0.5) | 172912 @0.045 (label 27 ms later), 173155 @1.94 and 174003 @2.88 (labels 36 and 41 ms off): bat passes, dense labels, wake is edge jitter | 3 |
| wake inside an active pass (labels < 0.5 s apart, +-50 ms), held or retriggered between calls | 174035 @0.18 (pass starts 0.30 s; 115 ms before the next label) | 1 |

Result: false wakes 3.14 -> 1.71/min on real clips (6 events), identical for B (A) and slim (and all 10 configs). Why the tolerance alone cannot do the job: all 11 wake edges lie 4-46 ms from a label because labels are dense inside passes, so a plain +-50 ms window would excuse every one, including the 15-40 kHz bursts; hence the band test. Limits: the 10 dB threshold is a judgement on 11 events; the burst test uses clip audio, not firmware state. `house_walk` (synthetic footsteps, 24.0/min) is no longer lumped in: `silence_false_wakes_per_min` (0.0) and `house_walk_false_wakes_per_min` are separate; `quiet_false_wakes_per_min` (10.0) kept for continuity. `false_wake_audibility.py` still treats house_walk as an episode source by design.

| | recall (wake / sound) | false wakes/min v1 -> v2 |
|---|---|---|
| B (= A) | 0.854 / 0.855 (unchanged) | 3.14 -> 1.71 |
| slim | 0.854 / 0.850 (unchanged) | 3.14 -> 1.71 |
