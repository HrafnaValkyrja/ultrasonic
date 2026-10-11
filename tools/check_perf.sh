#!/usr/bin/env bash
# Opt-in slow check (~100 s): Port Meadow e2e regression vs sim/perf/port_meadow_baseline.json.
# On demand: tools/check_perf.sh   (extra args pass through, e.g. --bless to rewrite the baseline)
# Auto: .githooks/pre-commit runs it when fw/core, fw/gen or fw/dsp is staged (PRECOMMIT_SKIP_PERF=1 to skip).
# Skips cleanly (exit 0) when ../ultrasonic-scratch/rec/extracts is absent. Exit 1 = regression.
cd "$(git rev-parse --show-toplevel)" || exit 0
source tools/env.sh >/dev/null 2>&1
fence=(systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0)
command -v systemd-run >/dev/null 2>&1 || fence=()
exec "${fence[@]}" python3 sim/perf/port_meadow.py "$@"
