# Vendored: PCBA Design Skills

The eight skills below were copied from https://github.com/Keitark/pcba-design-skills
at commit `d41e9996f052016727403236cf0f7476f8f23a1b` (reviewed 2026-09-30), MIT License © 2026 keitark (each skill
keeps its own LICENSE file). Removed: the Codex-only `agents/openai.yaml` files.

- manage-pcba-program · plan-electronic-product · qualify-pcba-sourcing ·
  design-and-review-circuit · schematic-humanizer · pcb-layout-review ·
  release-pcba-fabrication · operate-jlcpcb-order

**Review notes:** the bundled scripts process local files only (no network access,
no subprocess); the order skill keeps component, placement, price and payment
approvals separate and never pays. How they map onto this project (artifact paths,
KiCad 10 tooling, SKiDL as the schematic source of truth, owner places orders) is
in the repository's CLAUDE.md, which every one of these skills reads first.

To update: re-clone, diff against this commit, review, then copy.
