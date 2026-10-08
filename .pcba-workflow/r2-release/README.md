# r2 (phase-2 'mz2') release package - 2026-10-08 - gate BLOCKED (see gate.yaml)
Mirrors .pcba-workflow/k4-release. Files: `r2_gerber_drill.zip` (Protel-ext Gerbers F/In1/In2/B Cu, masks, paste, silk, Edge.Cuts; Excellon PTH+NPTH; maps; job), `bom.csv`, `cpl.csv` (JLC rotations via tools/jlc_rotations.py; bottom rule jlc2022), `jlc_rotation_corrections.csv`, `pin1_expected.png`, `pin1_check.csv`, `sourcing_dated.csv` (live JLC API), `cost_inputs.json`, `src/bom_jlc_mz2.csv`.
Rebuild: `python3 .pcba-workflow/k4-release/build_release.py r2` (default arg = K4). Gerbers: `kicad-cli pcb export gerbers --board-plot-params --no-x2` + `export drill --excellon-separate-th --generate-map --map-format gerberx2` on the board, zipped.
Quantity assumed 5 boards (JLC min). Nothing ordered.
