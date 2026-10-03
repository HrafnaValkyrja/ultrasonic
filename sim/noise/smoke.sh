#!/usr/bin/env bash
# Fenced smoke run of the layout-noise scaffold. Read-only on the board. Expect ~5 s and ~0.3 GB.
#   sim/noise/smoke.sh [board.kicad_pcb]
# No argument: pcbgeom.default_board (env NOISE_BOARD, else the newest routed draft_r1 board). Exit 1 when the board is
# stale vs hw/pod/pod.net, a net has no copper, or docs/sim/layout-noise.yaml disagrees with the run (budget.exit_code).
set -euo pipefail
cd "$(dirname "$0")/../.."
source tools/env.sh
exec systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 \
  timeout 60 /usr/bin/time -f 'wall %es  max RSS %M KB' \
  python3 sim/noise/extract.py ${1:+"$1"} --selfcheck --budget
