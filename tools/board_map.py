"""Plain-language board map: both faces of a pod board, parts coloured by job, callouts in everyday words.

    source tools/env.sh && python3 tools/board_map.py [board.kicad_pcb] [out.png] [--title T] [--changed REF,REF,...]

Reads any KiCad board (default: the Rev F routed draft) and hw/pod/system_map.py's block table, so every label sits on
the real part. Top face = seen from outside (lid side); bottom face = seen from the cell side (mirrored, as if the board
were flipped over in your hand). Dark style from tools/plotstyle.py. For the owner, not for fabrication.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(REPO / "hw/pod"))

import plotstyle  # noqa: E402

plotstyle.apply()
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Rectangle  # noqa: E402

import pcbnew  # noqa: E402
from system_map import BLOCKS  # noqa: E402

# block -> (plain name, one-line job, colour)
PLAIN = {
    "MCU": ("The brain", "microcontroller: runs the sound-shifting program", "#5b9ff2"),
    "CORE_SMPS": ("Brain's power converter", "efficient little supply for the chip's core", "#8d7ff0"),
    "CLOCK": ("Clock crystal", "keeps accurate time", "#a4a9b0"),
    "MIC": ("Ultrasonic microphone", "hears 20-96 kHz through a pinhole", "#2fc98f"),
    "BRIDGE": ("Speaker driver", "pushes the sound into the vibrating ear-pad speaker", "#f58a5c"),
    "SELFTEST": ("Self-check sensor", "measures speaker current so the pod can test itself", "#ff6d6c"),
    "ARM_PADS": ("Ear-pad wires", "speaker and light wires run up the arm", "#f09bbd"),
    "DOCK_USB": ("Charging contacts + guard", "magnetic dock: power and USB, with spark protection", "#f2b632"),
    "CHARGER": ("Battery charger", "charges safely, checks battery temperature", "#35b535"),
    "CELL_PADS": ("Battery wires", "", "#35b535"),
    "VBAT_SENSE": ("Battery gauge", "measures how full the battery is", "#7fd47f"),
    "LDO": ("Quiet power regulator", "clean, steady 3.0 V for everything", "#e8c86a"),
    "UI": ("Button + light", "on/off button; feeds the status light", "#e87ba4"),
    "DEBUG": ("Test points", "spots to probe or connect a programmer", "#c9ccd1"),
}
BLOCK_OF = {r: b for b, refs in BLOCKS.items() for r in refs.split()}
MM = pcbnew.ToMM


def footprint_box(fp):
    cy = fp.GetCourtyard(pcbnew.B_CrtYd if fp.IsFlipped() else pcbnew.F_CrtYd)
    bb = cy.BBox() if cy.OutlineCount() else fp.GetBoundingBox(False)
    return MM(bb.GetLeft()), MM(bb.GetTop()), MM(bb.GetRight()), MM(bb.GetBottom())


def draw_face(ax, board, bottom, x0, y0, w, h, changed):
    tx = (lambda x: w - (x - x0)) if bottom else (lambda x: x - x0)
    ty = lambda y: y - y0                                                           # noqa: E731
    ax.add_patch(FancyBboxPatch((0, 0), w, h, boxstyle="round,pad=0,rounding_size=1.0", fc="#0f3d2a", ec="#6b8f7b", lw=1.2, zorder=0))
    layer = pcbnew.B_Cu if bottom else pcbnew.F_Cu
    for t in board.GetTracks():                                                     # copper traces, faint
        if t.GetClass() == "PCB_TRACK" and t.GetLayer() == layer:
            s, e = t.GetStart(), t.GetEnd()
            ax.plot([tx(MM(s.x)), tx(MM(e.x))], [ty(MM(s.y)), ty(MM(e.y))], color="#c9a227", lw=0.5, alpha=0.35, zorder=1)
    centroids = {}
    for fp in board.GetFootprints():
        if fp.IsFlipped() != bottom:
            continue
        ref = fp.GetReference()
        blk = BLOCK_OF.get(ref)
        col = PLAIN.get(blk, ("", "", "#888888"))[2]
        l, t_, r, b_ = footprint_box(fp)
        xa, xb = sorted((tx(l), tx(r)))
        ax.add_patch(Rectangle((xa, ty(t_)), xb - xa, b_ - t_, fc=col, ec="#0b0b0b", lw=0.4, alpha=0.9, zorder=2))
        fs = 5.5 if (xb - xa) < 2.2 else 7
        ax.text((xa + xb) / 2, ty((t_ + b_) / 2), ref, ha="center", va="center", fontsize=fs, color="#0b0b0b", zorder=3)
        if ref in changed:
            ax.text(xb, ty(t_), "*", ha="right", va="top", fontsize=11, color="#ffffff", fontweight="bold", zorder=4)
        if blk:
            cx, cy_, n = centroids.get(blk, (0.0, 0.0, 0))
            centroids[blk] = (cx + (xa + xb) / 2, cy_ + ty((t_ + b_) / 2), n + 1)
    return {k: (cx / n, cy_ / n) for k, (cx, cy_, n) in centroids.items()}


def callouts(ax, cents, w, h):
    items = sorted(cents.items(), key=lambda kv: kv[1][0])
    top, bot = items[0::2], items[1::2]
    for row, y_lab, va in ((top, -2.2, "bottom"), (bot, h + 2.2, "top")):
        n = len(row)
        for i, (blk, (cx, cy)) in enumerate(row):
            lx = (i + 0.5) * w / max(n, 1)
            name, job, col = PLAIN[blk]
            ax.annotate(f"{name}\n{job}" if job else name, xy=(cx, cy), xytext=(lx, y_lab), ha="center", va=va, fontsize=7.2,
                        color=col, arrowprops=dict(arrowstyle="-", color=col, lw=0.8, alpha=0.9), zorder=5)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("board", nargs="?", default=str(REPO / "hw/pod/draft_r1/pod_r1_routed.kicad_pcb"))
    ap.add_argument("out", nargs="?", default=str(REPO / "docs/diagrams/board-map-revF.png"))
    ap.add_argument("--title", default="Pod board, Rev F (Phase 1 simplification): what each part does")
    ap.add_argument("--changed", default="")
    a = ap.parse_args()
    board = pcbnew.LoadBoard(a.board)
    bb = board.GetBoardEdgesBoundingBox()
    x0, y0, w, h = MM(bb.GetLeft()), MM(bb.GetTop()), MM(bb.GetWidth()), MM(bb.GetHeight())
    changed = set(filter(None, a.changed.split(",")))
    fig, axes = plt.subplots(2, 1, figsize=(13, 10.5))
    for ax, bottom, label in ((axes[0], False, "TOP face (faces the lid, outside)"), (axes[1], True, "BOTTOM face (faces the battery; shown flipped over)")):
        cents = draw_face(ax, board, bottom, x0, y0, w, h, changed)
        callouts(ax, cents, w, h)
        ax.set_xlim(-1, w + 1)
        ax.set_ylim(h + 8.5, -8.5)
        ax.set_aspect("equal")
        ax.grid(False)
        ax.set_xticks([])
        ax.set_yticks([])
        for s in ax.spines.values():
            s.set_visible(False)
        ax.set_title(label, fontsize=10, loc="left", color=plotstyle.TEXT_2)
    fig.suptitle(a.title, fontsize=13, color=plotstyle.TEXT, x=0.02, ha="left")
    note = f"Board {w:.0f} x {h:.0f} mm (about the size of a stick of gum cut in half). Coloured blocks = parts; thin gold lines = copper wiring."
    if changed:
        note += "  * = new or changed in Rev F."
    fig.text(0.02, 0.015, note, fontsize=8.5, color=plotstyle.TEXT_2)
    fig.tight_layout(rect=(0, 0.03, 1, 0.96))
    fig.savefig(a.out, dpi=150)
    print(a.out)


if __name__ == "__main__":
    main()
