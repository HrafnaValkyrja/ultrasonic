#!/bin/bash
# Photoreal K4 stack render set (headless; fenced). Needs build123d (models), kicad-cli 10, blender 5. ~12 min CPU.
set -e; cd "$(dirname "$0")/../.."; source tools/env.sh; W=${1:-/tmp/k4_render}; O=docs/diagrams/k4-review/boards; F="systemd-run --user --scope --quiet -p MemoryMax=4G -p MemorySwapMax=0"
python3 tools/render_k4/make_models.py; python3 tools/render_k4/prep_boards.py $W
for n in P M; do (cd $W && $F kicad-cli pcb export glb -f --include-pads --include-tracks --include-zones --include-soldermask --include-silkscreen --subst-models --user-origin 0x0mm -o $n.glb $n.kicad_pcb); done
mkdir -p $O; $F blender -b -P tools/render_k4/stack_scene.py -- $W $O iso exploded scale side boards
python3 -I tools/render_k4/annotate_side.py $O; mv $O/stack_side_section.png $O/stack_side_raw.png 2>/dev/null || true
