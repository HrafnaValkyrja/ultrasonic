---
name: pcb-kicad
description: Build, check and release this project's circuit boards with KiCad 10 from the command line - schematic-as-code in SKiDL, board scripting with the pcbnew API, autorouting with FreeRouting, ERC/DRC, Gerber/drill/BOM/placement files for JLCPCB, and rendered views to inspect. Use for any board work (bench H-bridge board, acoustic coupons, the product board); pair with the vendored PCBA skills for review gates.
---

# PCB work with KiCad 10 (headless)

Setup: `source tools/env.sh`. Proven end to end by `tools/smoke/run_all.py` (t_kicad_freerouting).
Gates, checklists and release discipline come from the vendored skills
(`design-and-review-circuit`, `pcb-layout-review`, `release-pcba-fabrication`,
`operate-jlcpcb-order`); CLAUDE.md says how they map onto this repo.

## Layout of a board in the repo
`hw/<board>/gen.py` (SKiDL, the schematic source of truth) → `hw/<board>/<board>.net` →
`hw/<board>/<board>.kicad_pcb` (board source of truth once placement starts) →
`hw/<board>/release/<rev>/` (frozen outputs + manifest).

## Schematic as code (SKiDL 2.3)
```python
import skidl
from skidl import Net, Part, generate_netlist, set_default_tool
set_default_tool(skidl.KICAD10)           # native KiCad 10 mode; env.sh sets the library paths
r = Part("Device", "R", value="10k", footprint="Resistor_SMD:R_0402_1005Metric", ref="R1")
r.fields["LCSC"] = "C25744"               # every part carries its LCSC number for the BOM
```
Give every part a stable `ref`; random tags make diffs noisy. A "Missing tag" warning is
SKiDL asking for `tag=` on parts it can't track across edits; set one for anything reused.

## Board
- The owner lays boards out in the KiCad GUI (spec Phase 3): she imports the `.net` file.
- Headless placement/scripting uses the `pcbnew` API (`FootprintLoad`, `SetPosition`,
  `SetNet`, `SaveBoard`); ignore the harmless `property.h ... assert` lines.
- Autoroute: `pcbnew.ExportSpecctraDSN(board, "b.dsn")` →
  `"$FREEROUTING_JAVA" -jar "$FREEROUTING_JAR" -de b.dsn -do b.ses -mp 20 --gui.enabled=false`
  → `pcbnew.ImportSpecctraSES(board, "b.ses")`. Autorouting is a draft; review it.

## Checks
```bash
kicad-cli pcb drc --format json --severity-error --output drc.json board.kicad_pcb
kicad-cli sch erc --format json --output erc.json board.kicad_sch     # when a .kicad_sch exists
```
Zero DRC errors is necessary, not sufficient (pcb-layout-review lists the rest).

## Look at it
```bash
kicad-cli pcb render --output top.png --width 1200 --height 800 --zoom 2 --quality high --background opaque board.kicad_pcb
kicad-cli pcb render --output bot.png --side bottom ...                                   # other side
kicad-cli pcb export svg --layers F.Cu,F.SilkS,Edge.Cuts --page-size-mode 2 --exclude-drawing-sheet --mode-single --output f.svg board.kicad_pcb
rsvg-convert -w 1600 -b white f.svg -o f.png
```
Inspect PNGs with the Read tool; send the owner the useful ones inline.

## JLCPCB outputs
```bash
kicad-cli pcb export gerbers --output release/gerbers board.kicad_pcb
kicad-cli pcb export drill --output release/gerbers/ board.kicad_pcb
kicad-cli pcb export pos --format csv --units mm --exclude-dnp --output release/pos.csv board.kicad_pcb
```
- JLC's placement (CPL) file wants `Designator, Mid X, Mid Y, Layer, Rotation`; rename the
  columns and **check every rotation in JLC's assembly preview**. Library footprints and JLC's
  part models often disagree by 90/180 degrees
  (`operate-jlcpcb-order/references/cpl-placement-review.md`).
- BOM columns for JLC: `Comment, Designator, Footprint, LCSC Part #`, generated from the SKiDL
  parts (their `LCSC` field), with dated stock from the jlc-parts skill.
- Zip the Gerber folder for upload. Build the release manifest with the release skill's
  scripts. The owner uploads, approves and pays; never automate ordering.

## Project board rules (spec §8)
Mic board thickness ≤ 0.8 mm, port hole 0.6–1.0 mm, no Class-2 ceramic capacitors near the
mic. Bridge gates need pull resistors (TIM1 floats at reset). Crystal close to the MCU. Keep
the 200 kHz transducer pair away from the mic port and the mic's clock and data lines.
