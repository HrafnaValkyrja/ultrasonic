# RESUME (live 2026-10-11 16:1x; pace slow, 1 worker; may be frozen at short notice)
Next she-uses-it milestone: bench day 1 (pen test + cardboard dummy pick the pod; Shokz/tragus listen to loud mode).
Branch claude/clever-mayer-s5rxuw, all pushed. Stashes: @{0} pre-session K4 scratch outputs, @{1} ECR-0025 dome prep (#11).

## Since 16:1x thaw
- hiz_idle (7930c14, c472455, 6449fa9): +2.7-3.3 h dusk sim, click inaudible; REAL BUG fixed (bridge pins never restored to TIM1 AF after Hi-Z); default stays OFF until bench PWR-I12 (bench-day item 6).
- False wakes (55656e7, 25fc262): no cheap detector fix beats B; most "false" wakes were scoring errors or real bats. Scorer v2: 3.14 -> 1.71/min, recall same (v1 kept). Remaining ~6 bursts 15-40 kHz (insects?) audible ~0.5 s blips; packet Q via Stolas (default keep).
- Alternative slim vs B (edc6e3d, docs/sim/alt-slim-vs-b.md): same detection, slim +2 h dense battery; sound needs her ears -> blind A/B pair in the Shokz kit (docs/bench/shokz/playlist/ab, ab_blind_sheet.md). Packet question sent to Stolas (default: keep B).

## Since 06:47 thaw
- CPU fixed: clock_plan default P112 (ECR-0027 a070a87), fwsim green. Runtime model corrected (fe405bf, 2370328): dense nominal (usable) A 11.9 (10.1), loud12 8.8 (7.5), shape 6.5 (5.6); dusk 26 h.
- Screening page for her: docs/progress/2026-10-11/progress.png (+ .md). Cap harness ready: python3 sim/checks/cap_derating.py (sourced reqs, adabe80).
- Issue sweep: open = #9 #11 #12 (mine), #1 #4 #7 #8 #14 (her chores, owner-only). Her word: chores another week.

## State
- D17 = A+L BUILT and tested (limiter on, loud +12 via triple press, off at boot; battery saver off + knob). Clamp check all carriers (b92e59c). fwsim green.
- Runtime real use (130 mAh, 0.85 usable): loud12 8.1 h dense / 23.7 h dusk. loud_shape (OFF): 6.4 h dense.
- Ready for bench: docs/bench/bench-day-1.md (+png), k4-dummy-template.pdf, bench/rig/ (sounddevice installed), docs/bench/shokz/ (protocol, playlist, teardown).
- K4-trim 13.75 x 13.6 boards fit the existing cavity if 9 parts move; ~8-12 h lead re-route; only if pen test lands 12.6-15 (5be49b4).
- tools/check_perf.sh = manual Port Meadow regression after fw changes (not in the hook; agents never edit .githooks/pre-commit).
- Heartbeat cron recreated on thaw must run `python3 tools/board_card.py` each beat.

## NEXT (movable)
1. #7 cap derating when ./inbox has the Samsung files (CL03A225MP3CRNC, CL03A105MO3NRNC).
2. Taste WHY for D17 (prediction missed).
3. II round 7 (needs a fresh question; live rows are bench-gated).

## Waiting
- #7 files from her; bench day (#1 pen test + I-029 dummy, #14 list); #11 K1t button only if K1t still needed; #4 body measure; #8 order after freeze (owner-only).
