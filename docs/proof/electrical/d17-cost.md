# D17 loudness options: battery and heat cost on the real programme (2026-10-08)

Answer: **option A as shipped (limiter, ceiling 0.5203) costs ~2.5 mA and still meets 8 h with margin. A with +12 dB drive into the limiter (the variant that gets the cafe/car margin) costs ~12 mA extra: 8 h is MISSED in the continuous-calls and cell-pessimistic cases (4-6 h), met only for sparse scenes. U4/cell heat is a non-issue (+3.6 K worst realistic).** TEAX14C02-8 (7.8 ohm vs 8 ohm exciter) adds only ~2 % current.

**SCOPE (2026-10-08, reconciled: current-models-reconciled.md):** this table is the cost of PLAYING A LOUD PROGRAMME (the 75-dB-per-call translated nature file, calls at the top of the level range, 51 % active frames) or its continuous worst case. It is NOT the cost of wearing the pod outdoors: for that, `sim/perf/port_meadow.py` (real clips, relative levels, gated by the squelch) gives loud12 +3.1 mA over today, not +12. The 14.5-25 mA figures are a cafe/car loud-mode ceiling; use them only for hours spent in that mode.

## Method
- Programme: `sim/out/nature/2_translated_only.wav` (20 s, 51 % of 100 ms frames active), same chain/limiter port as `sim/acoustics/audibility_reconciled.py` (`lahead`, `tp_limit`, ceilings 0.251 / 0.5203). Sample = bridge duty fraction; supply current = mean |x| x 327 mA (full-scale 3.0 V into 8 ohm + FETs + 0.1 ohm, audibility-requirement.md l.7). The H-bridge draws |i| from +3V0 (U4 passes it 1:1 from VSYS).
- The `bats*.npz` vectors are mic PDM input words, not output; no firmware run was made (limiter port used, as in the audibility doc). Scenes: dense = the file as is; continuous = active-frame mean held 100 % of the time (worst); sparse = 18 % active (rail-budget "quiet room", sub-power.md l.176), background from the file's inactive frames.
- Runtime = 130 mAh / (awake base without exciter + exciter + 0.73 mA LED worst). Base from sub-power.md l.173 `full_chain_awake_mA` [5.0, 6.8, 9.8] minus the budget's exciter term [0.4, 1.1, 2.5] = [4.6, 5.7, 7.3] (rail-budget.yaml, sim/checks/power.py). 130 mAh nominal, no derating (as thermal/electrical row 1).
- TEAX: 3.0/(7.8+1.2+0.1) vs 3.0/9.3 = x1.022 current for the same duty. The 208 mA clamp still bounds it; A+12 peaks 166-170 mA, under it. (The Bl gain is acoustic; it is the +7.6 dB, not extra current.)

## Mean transducer current (mA) and runtime (h, low / nom / high base load, LED on)
| Option | peak mA | dense | continuous | sparse 18 % | runtime dense | continuous | sparse |
|---|---|---|---|---|---|---|---|
| today a, -12 dBFS | 82 | 2.4 | 4.2 | 1.1 | 16.9 / 14.8 / 12.5 | 13.6 / 12.2 / 10.6 | 20.2 / 17.2 / 14.2 |
| A, limiter idle, 0.5203 | 145 | 4.9 | 8.7 | 2.3 | 12.7 / 11.5 / 10.1 | 9.3 / 8.6 / **7.8** | 17.0 / 14.9 / 12.6 |
| A, +12 dB into limiter | 166 | 14.5 | 24.9 | 7.5 | **6.5 / 6.2 / 5.8** | **4.3 / 4.1 / 3.9** | 10.2 / 9.4 / 8.4 |
| A + TEAX 7.8 ohm, +12 dB | 170 | 14.9 | 25.5 | 7.6 | **6.4 / 6.1 / 5.7** | **4.2 / 4.1 / 3.9** | 10.0 / 9.3 / 8.3 |

Bold = misses the 8 h spec. Today's dense figure (2.4 mA) sits at the top of the budget's guessed 0.4-2.5 mA exciter band, so that guess is about right for a busy file.

## Heat (thermal README row 8 case (b) redone)
U4 power = (VSYS - 3.0) x I, drop 1.2-1.5 V docked/full cell, theta-JA 166 C/W (README). Old case (b): 2.5 mA -> 3.8 mW -> +0.6 K.
| Option | U4 mW (dense / continuous) | dT U4 K (dense / continuous) |
|---|---|---|
| today | 2.8-3.5 / 5.0-6.3 | 0.5-0.6 / 0.8-1.0 |
| A, limiter idle | 5.9-7.3 / 10.4-13.0 | 1.0-1.2 / 1.7-2.2 |
| A, +12 dB | 17.4-21.8 / 29.9-37.4 | 2.9-3.6 / 5.0-6.2 |
| A + TEAX, +12 dB | 17.8-22.3 / 30.6-38.2 | 3.0-3.7 / 5.1-6.3 |
U4 junction worst ~35 + 3 (shell) + 6.3 = ~45 C vs 125 C limit. Cell: I_rms 34-41 mA x Rint 0.34 ohm = under 1 mW, negligible. Bound (a) (continuous full-clamp sine, +33 K) unchanged.

## Verdict
- Heat: PASS for every option (largest realistic +6.3 K, shell/touch unchanged within 0.1 K).
- Runtime: A (limiter, no extra drive) PASS: >= 7.8 h worst, 10-17 h typical. **A + 12 dB drive FAILS 8 h** unless scenes are sparse (>= 8.3 h at 18 % active); dense/continuous calls give 4-6 h. TEAX does not change this.
- Recommendation (owner decides): ship A (+TEAX if bought, which gives +7.6 dB acoustically for ~2 % current, the cheapest loudness); treat +12 dB drive as a user "loud" mode, or use the slow AGC variant (gain only on quiet calls) which raises mean current far less than blanket +12 dB (not simulated here for current). Needs a 4-6 h runtime caveat if +12 dB is default. OPEN: 130 mAh derating (cold, age) would worsen every row; bench current log (PWR-I12) not done.

## Adversarial check of ledger I-019 (TEAX + 4.4 dB drive = current driver + 12 dB), 2026-10-08
Script `sim/acoustics/teax_drive_check.py` (reuses audibility_reconciled.py chain, limiter, 5-call margins; current as above with TEAX x1.022; scenes dense / continuous / sparse 18 %; runtime nominal base, LED on). Margin = per-call dB over masked threshold, median (worst call).
| Config | pk mA | mean mA dense / cont / sparse | runtime h dense / cont / sparse | Private office | Open office | Heavy traffic | Cafe 67 | Car 68 |
|---|---|---|---|---|---|---|---|---|
| A + 12 (current driver) | 166 | 14.5 / 24.9 / 7.6 | 6.2 / 4.1 / 9.3 | +23.3 (+12.5) | +18.3 (+7.5) | +10.2 (-0.5) | +8.6 (-2.1) | +6.2 (-4.5) |
| A + TEAX +0 | 148 | 5.0 / 8.9 / 2.4 | 11.4 / 8.5 / 14.7 | +24.7 (+8.1) | +19.7 (+3.1) | +11.7 (-4.9) | +10.1 (-6.5) | +7.7 (-8.9) |
| A + TEAX +4.4 | 161 | 7.8 / 13.8 / 3.8 | 9.1 / 6.4 / 12.7 | +27.6 (+12.5) | +22.6 (+7.5) | +14.6 (-0.5) | +13.0 (-2.1) | +10.6 (-4.5) |
| A + TEAX +6 | 164 | 9.1 / 16.0 / 4.5 | 8.4 / 5.8 / 11.9 | +28.5 (+14.1) | +23.5 (+9.1) | +15.4 (+1.1) | +13.8 (-0.5) | +11.4 (-2.9) |
| A + TEAX +12 | 170 | 14.9 / 25.5 / 7.7 | 6.1 / 4.1 / 9.2 | +30.9 (+20.1) | +25.9 (+15.1) | +17.8 (+7.1) | +16.2 (+5.5) | +13.8 (+3.1) |
(Street-day row omitted; it tracks open office +2.)

Verdict: **PARTLY CONFIRMED.** Audibility: TEAX+4.4 has the SAME worst-call margin as current+12 in every scene (identical to 0.1 dB; the limiter ceiling sets the worst call) and a median 4.4 dB better. Current: the ~8 mA / 9 h figure holds for the dense file only (7.8 mA, 9.1 h). Continuous calls give 13.8 mA and 6.4 h (misses 8 h), so "8.5-9 h" is not general. Savings vs current+12: 46 % in mean mA (14.5 -> 7.8), +2.9 h dense.
Drive keeping >= 8 h: dense scenes TEAX +6 (8.4 h; worst-call +1.1 heavy traffic, -0.5 cafe, -2.9 car, best of those that pass); continuous scenes only TEAX +0 (8.5 h nominal, 7.7 h high base; worst-call -4.9 heavy traffic). Sparse: any drive up to +12 passes. No drive meets 8 h continuous AND the +12 worst-call margin; that needs a larger cell or a loud mode (owner decides).
