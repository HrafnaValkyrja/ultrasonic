# NEXT 5 (ranked, movable today; 2026-10-08 21:15 ET)
1. PERF-PM: sim/perf/port_meadow.py e2e regression on the real recording (recall, false wakes, latency, level, current per config) + baseline. RUNNING.
2. FW-HOLD2: gesture test for the loud-mode toggle (bf5d6bd open item) + fwsim row; and docs/system + plm sync for loud_db / hiz_idle knobs. ~45 min.
3. BENCH-RIG: scripts for the E1 exciter rig so bench day is quick: sweep/log generator for I-021 (impedance), I-022 (pad force), I-028 (2.5 vs 4 kHz A/B), masked-threshold runner. ~1.5 h.
4. ECR-PREP-TEAX: draft (status: proposed, not applied) ECR for the TEAX14C02-8 tragus pad: footprint/pad model, wiring, BOM line with dated stock, so the #2 tap goes straight to build. ~1 h.
5. SIM-FID-U4: replace the assumed U4 thermal time constant (thermal row 8) with datasheet Zth/θJA (TPS7A2030, dated), re-run row 8 for loud mode. ~45 min.

## Waiting (blocked on her or the bench)
- #2 D17 loudness ruling (Rec A+X+L) -> limiter + loud_db defaults, re-bless goldens, apply the TEAX ECR.
- #1 pen test + I-029 cardboard dummy (bench day) -> pod pick.
- #11 K1-thin button: 2-arc D4 pad re-route (~1 h, stash@{0}) only if K1t is still needed after #1.
- #14 bench items: masked threshold, car log, I-021/22/27/28.
- #4-#8 owner rulings (Rec blocks posted).
