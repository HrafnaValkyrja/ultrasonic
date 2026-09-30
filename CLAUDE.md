# Stereo Ultrasound: instructions for Claude

**The spec is the source of truth:** `docs/spec.md`.
- §1 (the MVP) is owner-locked. Never edit it.
- §0 working rules apply to all work:
  - gloss every part number;
  - use primary sources, with dates;
  - present 2–3 options with a recommendation, and the owner decides;
  - switching regulators only as spec D11 allows (MCU core SMPS; self-noise no louder than ambient);
  - be blunt;
  - show, don't just tell.
- Research notes live in `docs/research/`; numeric checks in `sim/checks/`.

## Owner preferences
- **Visual learner.** Diagrams are the default for any mechanism, layout, flow or comparison.
  - Author diagrams locally: SVG in `docs/diagrams/`, or Mermaid.
  - Render to PNG with `docs/diagrams/render.sh` and send the **PNG** into the chat, where it shows inline. SVG files only appear as file cards.
  - Never send project content to external image-generation APIs.
  - Skill: `.claude/skills/visual-explainer/`.
- **Dark mode for every visual.** `render.sh` darkens SVGs by default (`docs/diagrams/darken.py`); `tools/plotstyle.py` is dark by default. Use the palette colours those files map.
- **Self-taught, wants the why.** Explain briefly, never condescend.
  - **Level:** RF, analogue, digital packets/data, CAD and device physics are known ground. Pitch explanations at the black boxes: MCU internals, datasheets, PCB stack-ups, DSP on sampled audio (`docs/learn/`).

## Where this runs
On the owner's machine (Valhalla: i9-14900HX, 32 threads, 30 GB RAM, native Ubuntu 26.04, Python 3.14) with Remote Control, so she can steer from the Claude app. Cloud sessions were retired on 2026-09-30. The SessionStart hook sources `tools/env.sh` locally; it never installs anything locally, because setup needs sudo.
- **Memory discipline (after the 2026-09-30 OOM freeze, `docs/incidents/2026-09-30-oom.md`):** the machine is shared with the owner's desktop, games and other agents.
  - Start sessions with `tools/claude-session.sh` (tmux + an 18 GB fence).
  - Run any simulation, routing or bulk data job inside a fence: `systemd-run --user --scope --quiet -p MemoryMax=4G -p MemorySwapMax=0 <cmd>`.
  - Workflows: cap live agents (the audit script uses 5). Never let parallel agents run FreeRouting.
  - **If you are one of several parallel agents (a workflow or audit):** fence every simulation at 3G (`systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 <cmd>`). If it's killed (exit 137), shrink the problem rather than raising the limit past 4G. Never run FreeRouting, `hw/pod/place.py` or any autorouter.
  - Before resuming heavy background work, check `journalctl -k` for recent OOM kills.

## Tools
- `tools/setup.sh` installs everything idempotently (details in `tools/README.md`). Run `source tools/env.sh` before using the tools.
- **Circuits:** ngspice 45 (Valhalla; the retired cloud image had 42).
- **PCB:** KiCad 10 (`kicad-cli`, `pcbnew` Python API), SKiDL, FreeRouting, easyeda2kicad (footprints by LCSC number).
- **Firmware:** ARM GCC.
- **Mechanics:** build123d, scikit-fem.
- **Parts:** JLC stock and price from the JLCPCB parts API. Always record the query date.

## How the vendored PCBA skills map onto this project
The eight skills in `.claude/skills/` (manage-pcba-program, plan-electronic-product, qualify-pcba-sourcing, design-and-review-circuit, schematic-humanizer, pcb-layout-review, release-pcba-fabrication, operate-jlcpcb-order) come from `.claude/skills/PCBA-SKILLS-VENDORED.md`. In this repo:
- **Requirements:** `docs/spec.md` is authoritative. A `product-brief.yaml` or `architecture.md` may be derived from it but must never contradict it; spec changes come first.
- **Artifacts** go in `.pcba-workflow/` at the repo root, which is the skills' default. Gate status is `PASS`, `BLOCKED` or `USER_REVIEW`. Owner decisions are also tracked as O-items in spec §12.
- **Schematic source of truth:** the SKiDL generator scripts under `hw/<board>/`. KiCad schematic and netlist files are generated from them. Change the generator, never only the generated files.
- **PCB source of truth:** the KiCad board file once placement starts. The owner does layout; Claude reviews, runs DRC and produces the release files.
- **EDA adapter:** KiCad 10 native tooling.
  - ERC/DRC: `kicad-cli sch erc`, `kicad-cli pcb drc`.
  - Release files: `kicad-cli pcb export gerbers|drill|pos`.
  - Renders: `kicad-cli pcb render`, `kicad-cli sch export svg`.
  - Scripting: the `pcbnew` Python API.
- **Fabricator:** JLCPCB. Prefer Basic parts, then Extended; record the LCSC number and a dated stock check for every line.
- **Orders:** the owner places every order and makes every payment. `operate-jlcpcb-order` prepares and reviews the upload (BOM/CPL matching, placement preview checklist) and stops there.

## Boards
- **Bench (Phase 2):** H-bridge test board; acoustic coupons (mic port-geometry tests).
- **Product (Phase 3):** one board per side (see spec §8–§9).

## Git
Work on the session's designated branch. Commit with the attribution trailer the session specifies. Never push to another branch.
