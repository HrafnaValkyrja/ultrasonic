#!/usr/bin/env bash
# Fenced smoke run of the layout-noise scaffold. Read-only on the board. Expect ~6 s and ~0.3 GB.
#   sim/noise/smoke.sh [board.kicad_pcb]
set -euo pipefail
cd "$(dirname "$0")/../.."
source tools/env.sh
BOARD="${1:-hw/pod/draft_r1/pod_r1_routed.kicad_pcb}"   # Rev F routed board (the fanout board is Rev E)
exec systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 \
  timeout 60 /usr/bin/time -f 'wall %es  max RSS %M KB' \
  python3 sim/noise/extract.py "$BOARD" --selfcheck --budget
