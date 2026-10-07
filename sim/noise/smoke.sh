#!/usr/bin/env bash
# Fenced smoke run of the layout-noise scaffold. Read-only on the board. Expect ~5 s and ~0.3 GB.
#   sim/noise/smoke.sh [board.kicad_pcb]
# No argument: pcbgeom.default_board (env NOISE_BOARD, else hw/current.yaml `board`; netlist + BOM from the same pointer;
# ULTRASONIC_DESIGN=revg runs the Rev G/F reference). Exit 1 when the board is stale vs the design netlist, a net has no
# copper, or docs/sim/layout-noise.yaml disagrees with the run (budget.exit_code). Metric FAILs do not set the exit code.
set -euo pipefail
cd "$(dirname "$0")/../.."
source tools/env.sh
python3 tools/current.py | head -1   # which design this run uses
exec systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 \
  timeout 60 /usr/bin/time -f 'wall %es  max RSS %M KB' \
  python3 sim/noise/extract.py ${1:+"$1"} --selfcheck --budget
