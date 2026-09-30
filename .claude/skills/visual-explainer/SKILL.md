---
name: visual-explainer
description: Show the owner a picture instead of (or alongside) prose - block diagrams, signal flows, clock trees, keep-out zones, before/after comparisons, step-by-step sequences, plots, annotated photos, mind maps of a plan. Use whenever an explanation involves a mechanism, layout, flow, geometry or comparison; the owner is a visual learner and her chat shows PNGs inline. Everything is drawn locally - never external image-generation APIs.
---

# Visual explainer (local)

The owner learns visually. A diagram earns its place when it shows a mechanism a reader
would otherwise assemble from prose; if one sentence says it faster, write the sentence.

## Pick the medium
| Need | Medium | Where |
|---|---|---|
| Exact engineering drawing: signal chain, clock tree, geometry, keep-outs, side-by-side options | Hand-authored **SVG** | `docs/diagrams/<name>.svg` |
| Quick flowchart, sequence, state machine, mind map of a plan, timeline | **Mermaid** (`.mmd`) | `docs/diagrams/<name>.mmd` |
| Data: waveforms, spectra, sweeps, budgets | **matplotlib** with `tools/plotstyle.py` | script in `sim/`, PNG in scratchpad |
| Real object: ear, board, part | **Annotated photo/render** (PIL overlays, KiCad `pcb render`) | scratchpad (third-party photos never go in the repo) |

## Render and show
1. `docs/diagrams/render.sh <file.svg|file.mmd> <out.png>` renders a 2x PNG with the local
   headless Chromium (SVG) or mermaid-cli (Mermaid).
2. **Look at the PNG yourself (Read tool) before sending.** Fix overlaps, clipped labels,
   wrong numbers. One look, one fix pass.
3. Send the **PNG** with `SendUserFile` and no `display` argument; it shows inline in the
   owner's chat. SVG files only appear as file cards.
4. Caption: one sentence stating the claim the picture makes. Add 2-4 bullets of text
   companion in the message when the figure carries numbers.

## Drawing rules
- Depict the mechanism, not its name; label every arrow with what flows (`200 kS/s`,
  `clock 4.0 MHz`, `presses inward >=1 N`).
- Comparisons draw the difference: two options side by side, sharing one scale.
- Step-by-step processes: a **multi-frame** sequence (frame-1.png ... frame-n.png, same
  layout, one change per frame) beats one crowded figure.
- SVG: `viewBox` sized to content; explicit light card background (`#fbfaf7`) and dark
  strokes so it reads on any panel; one accent colour for the element the argument hinges
  on; 11-13 px text; align to a grid; no scripts or external images.
- Every label must be true. Numbers come from the spec, a datasheet or a script you ran; mark
  estimates `~` or with the spec's confidence tag.
- Keep sources: SVG/MMD in `docs/diagrams/` (committed); PNGs are build outputs (ignored).

## Why not AI image generation
Generated images can't be trusted to get labels, numbers or geometry right, and they would
send design details to a third party. Style ideas borrowed from ericblue/visual-explainer-skill
(MIT): multi-frame sequences, structured mind maps, a text companion per image.
