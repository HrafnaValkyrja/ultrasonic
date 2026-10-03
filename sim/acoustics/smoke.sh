#!/usr/bin/env bash
# Fenced smoke run of the acoustics scaffold: geometry read, self-checks (analytic limits, finite-channel modal sum, axisymmetric
# FEM), mic-port designs + sweeps + Monte Carlo, bone-conduction network + sensitivity + T6 noise, then a headline print.
# Read-only on the board and the shell.  Expect ~35 s and < 0.5 GB.
#   sim/acoustics/smoke.sh [board.kicad_pcb]        (default: newest of hw/pod/draft_r1/{pod_r1_routed,pod_r1_placed,fanout/pod_r1_routed})
set -euo pipefail
cd "$(dirname "$0")/../.."
source tools/env.sh >/dev/null
BOARD_ARG=()
[ $# -ge 1 ] && BOARD_ARG=(--board "$1")
exec systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 \
  timeout 60 /usr/bin/time -f 'wall %es  max RSS %M KB' bash -c '
    set -e
    python3 sim/acoustics/selfcheck.py > /dev/null
    python3 sim/acoustics/run_port.py --mc 40 "$@" 2>&1 | grep -v "Debug:\|property.h" > /dev/null
    python3 sim/acoustics/bone.py > /dev/null
    python3 sim/acoustics/headline.py
  ' _ "${BOARD_ARG[@]}"
