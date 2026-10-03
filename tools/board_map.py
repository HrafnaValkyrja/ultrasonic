"""Plain-language board map: both faces of a pod board, parts coloured by job, zones outlined, labels in everyday words.

    source tools/env.sh && python3 tools/board_map.py [board.kicad_pcb] [out.png] [--title T] [--changed REF,REF,...]

Reads any KiCad board (default: the Rev F routed draft) and hw/pod/system_map.py's block table, so every label sits on
the real part. Both faces are drawn as seen from ABOVE (the bottom face as if the board were glass), so a part on the
bottom lines up with the top view. Each block: parts filled in its colour, its cluster outlined, one label (name + job)
with a leader. Wire pads carry a short code (key in the footer). Dark style from tools/plotstyle.py. For the owner,
not for fabrication. Owner request 2026-10-02: "a sheet using colors and highlight + labels ... on both sides".
"""
from __future__ import annotations

import argparse
import sys
import textwrap
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(REPO / "hw/pod"))

import plotstyle  # noqa: E402

plotstyle.apply()
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle  # noqa: E402

import pcbnew  # noqa: E402
from system_map import BLOCKS  # noqa: E402

# block -> (plain name, one-line job, colour)
PLAIN = {
    "MCU": ("The brain", "microcontroller: turns ultrasound into sound you can hear", "#5b9ff2"),
    "CORE_SMPS": ("Brain's power converter", "small, efficient supply for the chip's core", "#8d7ff0"),
    "CLOCK": ("Clock crystal", "keeps time for the brain", "#a4a9b0"),
    "MIC": ("Ultrasonic microphone", "hears 20-85 kHz through the pinhole", "#2fc98f"),
    "BRIDGE": ("Speaker driver", "4 tiny switches push sound to the ear-pad speaker", "#f58a5c"),
    "SELFTEST": ("Self-check sensor", "measures speaker current: the pod tests itself", "#ff6d6c"),
    "ARM_PADS": ("Ear-pad wires", "speaker + light wires up the glasses arm", "#f09bbd"),
    "DOCK_USB": ("Dock contacts + guards", "magnetic charging dock, USB data, spark protection", "#f2b632"),
    "CHARGER": ("Battery charger", "fills the battery safely, watches its temperature", "#35b535"),
    "CELL_PADS": ("Battery wire", "", "#35b535"),
    "VBAT_SENSE": ("Battery gauge", "tells the brain how full the battery is", "#7fd47f"),
    "LDO": ("Quiet power regulator", "clean, steady 3.0 V for everything", "#e8c86a"),
    "UI": ("Button + light", "on/off button; feeds the status light", "#e87ba4"),
    "DEBUG": ("Test points", "gold dots for a programmer or a probe", "#c9ccd1"),
}
PAD_CODE = {"DOCK_VBUS": "5V", "GND": "G", "VBAT": "B+", "TS": "T", "LED_A": "L+", "LED_K": "L-", "USB_DP": "D+",
            "USB_DM": "D-", "CC": "CC", "OUT_A": "SA", "OUT_B": "SB"}
PAD_KEY = ("Wire pads:  5V dock power   G ground (dock and battery share it)   B+ battery +   T battery temperature   "
           "D+ D- USB data   CC 'I am a USB device' line   SA SB speaker   L+ L- light")
BLOCK_OF = {r: b for b, refs in BLOCKS.items() for r in refs.split()}
MM = pcbnew.ToMM
INK, INK2, BG = plotstyle.TEXT, plotstyle.TEXT_2, plotstyle.SURFACE


def box_of(fp):
    cy = fp.GetCourtyard(pcbnew.B_CrtYd if fp.IsFlipped() else pcbnew.F_CrtYd)
    bb = cy.BBox() if cy.OutlineCount() else fp.GetBoundingBox(False)
    return MM(bb.GetLeft()), MM(bb.GetTop()), MM(bb.GetRight()), MM(bb.GetBottom())


def clusters(boxes, gap=1.6):
    """Single-linkage groups of part boxes closer than `gap` mm: one outline per group."""
    groups = []
    for b in boxes:
        hit = [g for g in groups if any(b[0] - gap < o[2] and o[0] - gap < b[2] and b[1] - gap < o[3] and o[1] - gap < b[3] for o in g)]
        merged = [b] + [o for g in hit for o in g]
        groups = [g for g in groups if g not in hit] + [merged]
    return [(min(o[0] for o in g), min(o[1] for o in g), max(o[2] for o in g), max(o[3] for o in g), len(g)) for g in groups]


def draw_face(ax, board, bottom, x0, y0, w, h, changed, port):
    X = lambda x: x - x0  # noqa: E731
    Y = lambda y: y - y0  # noqa: E731
    ax.add_patch(FancyBboxPatch((0, 0), w, h, boxstyle="round,pad=0,rounding_size=1.0", fc="#1c1d21", ec="#8a8f98", lw=1.4, zorder=0))   # black mask (spec O23)
    layer = pcbnew.B_Cu if bottom else pcbnew.F_Cu
    for t in board.GetTracks():
        if t.GetClass() == "PCB_TRACK" and t.GetLayer() == layer:
            s, e = t.GetStart(), t.GetEnd()
            ax.plot([X(MM(s.x)), X(MM(e.x))], [Y(MM(s.y)), Y(MM(e.y))], color="#b48ad6", lw=0.6, alpha=0.35, zorder=1)
    if port:
        ax.add_patch(Circle((X(port[0]), Y(port[1])), 0.3, fc=BG, ec=INK, lw=1.0, zorder=3))
    per_block = {}
    for fp in board.GetFootprints():
        if fp.IsFlipped() != bottom:
            continue
        ref = fp.GetReference()
        blk = BLOCK_OF.get(ref)
        col = PLAIN.get(blk, ("", "", "#888888"))[2]
        l, t_, r, b_ = box_of(fp)
        bx = (X(l), Y(t_), X(r), Y(b_))
        is_pad = ref.startswith("J")
        net = fp.Pads()[0].GetNetname() if is_pad and fp.Pads() else ""
        if is_pad:
            p = fp.Pads()[0]
            px, py = X(MM(p.GetPosition().x)), Y(MM(p.GetPosition().y))
            sx, sy = MM(p.GetSize().x), MM(p.GetSize().y)
            ax.add_patch(FancyBboxPatch((px - sx / 2, py - sy / 2), sx, sy, boxstyle=f"round,pad=0,rounding_size={min(sx, sy) / 2}",
                                        fc="#e7c24a", ec=col, lw=2.2, zorder=2))
            ax.text(px, py, PAD_CODE.get(net, "?"), ha="center", va="center", fontsize=8.5, fontweight="bold", color="#1a1300", zorder=4)
        else:
            ax.add_patch(Rectangle((bx[0], bx[1]), bx[2] - bx[0], bx[3] - bx[1], fc=col, ec="#0b0b0b", lw=0.5, alpha=0.92, zorder=2))
            fs = 6.5 if (bx[2] - bx[0]) < 1.4 or (bx[3] - bx[1]) < 1.4 else 9
            ax.text((bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2, ref, ha="center", va="center", fontsize=fs, color="#0b0b0b",
                    rotation=90 if (bx[3] - bx[1]) > 1.6 * (bx[2] - bx[0]) and fs < 9 else 0, zorder=3)
        if ref in changed:
            ax.add_patch(Rectangle((bx[0] - 0.12, bx[1] - 0.12), bx[2] - bx[0] + 0.24, bx[3] - bx[1] + 0.24, fc="none", ec="#ffffff",
                                   lw=1.6, ls=(0, (2, 1.2)), zorder=4))
        if blk and blk != "CELL_PADS" and not is_pad:
            per_block.setdefault(blk, []).append(bx)
        elif blk:                                                       # pads: one zone for the whole wire-pad column
            per_block.setdefault("PADS", []).append(bx)
    anchors = {}
    for blk, boxes in per_block.items():
        cl = clusters(boxes)
        col = "#e7c24a" if blk == "PADS" else PLAIN[blk][2]
        for (l, t_, r, b_, n) in cl:
            ax.add_patch(FancyBboxPatch((l - 0.3, t_ - 0.3), r - l + 0.6, b_ - t_ + 0.6, boxstyle="round,pad=0,rounding_size=0.5",
                                        fc="none", ec=col, lw=1.8, alpha=0.95, zorder=5))
        big = max(cl, key=lambda c: (c[4], (c[2] - c[0]) * (c[3] - c[1])))
        anchors[blk] = big
    return anchors


def place_labels(ax, anchors, w, h, bottom):
    items = []
    for blk, (l, t_, r, b_, _) in anchors.items():
        if blk == "PADS":
            name, job, col = "Wire pads", "hand-soldered wires: dock, battery, ear pad (codes below)", "#e7c24a"
        else:
            name, job, col = PLAIN[blk]
        items.append((blk, name, job, col, (l + r) / 2, (t_ + b_) / 2, (l, t_, r, b_)))
    above = [i for i in items if i[5] < h / 2]
    below = [i for i in items if i[5] >= h / 2]
    while abs(len(above) - len(below)) > 1:                         # balance the two label rows
        src, dst = (above, below) if len(above) > len(below) else (below, above)
        mv = min(src, key=lambda i: abs(i[5] - h / 2))
        src.remove(mv)
        dst.append(mv)
    for row, ylab, va in ((above, -1.0, "bottom"), (below, h + 1.0, "top")):
        row.sort(key=lambda i: i[4])
        n = len(row)
        for k, (blk, name, job, col, cx, cy, bb) in enumerate(row):
            lx = -0.5 + (k + 0.5) * (w + 1.0) / max(n, 1)
            ty = bb[1] - 0.3 if va == "bottom" else bb[3] + 0.3          # leader ends on the zone edge nearest the label
            tx = min(max(lx, bb[0]), bb[2])
            ax.plot([lx, tx], [ylab, ty], color=col, lw=1.1, alpha=0.9, zorder=6)
            ax.add_patch(Circle((tx, ty), 0.13, fc=col, ec="none", zorder=7))
            lines = textwrap.wrap(job, 30) if job else []
            body = "\n".join(lines)
            if va == "bottom":                                       # above the board: name on top, job nearest the board
                if body:
                    ax.text(lx, ylab, body, ha="center", va="bottom", fontsize=9.5, color=INK2, zorder=8, linespacing=1.15)
                ax.text(lx, ylab - 0.44 * len(lines) - 0.22, name, ha="center", va="bottom", fontsize=11.5, fontweight="bold", color=col, zorder=8)
            else:
                ax.text(lx, ylab, name, ha="center", va="top", fontsize=11.5, fontweight="bold", color=col, zorder=8)
                if body:
                    ax.text(lx, ylab + 0.62, body, ha="center", va="top", fontsize=9.5, color=INK2, zorder=8, linespacing=1.15)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("board", nargs="?", default=str(REPO / "hw/pod/draft_r1/pod_r1_routed.kicad_pcb"))
    ap.add_argument("out", nargs="?", default=str(REPO / "docs/diagrams/board-map-revF.png"))
    ap.add_argument("--title", default="Pod board, Rev F: what each part does")
    ap.add_argument("--changed", default="D5,J4,TP7,TP8,TP9,TP10,Q1,Q2,C15,C1")
    a = ap.parse_args()
    board = pcbnew.LoadBoard(a.board)
    bb = board.GetBoardEdgesBoundingBox()
    x0, y0, w, h = MM(bb.GetLeft()), MM(bb.GetTop()), MM(bb.GetWidth()), MM(bb.GetHeight())
    changed = set(filter(None, a.changed.split(",")))
    port = None
    for fp in board.GetFootprints():
        for p in fp.Pads():
            if p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                port = (MM(p.GetPosition().x), MM(p.GetPosition().y))
    fig, axes = plt.subplots(2, 1, figsize=(15, 18.5))
    faces = ((axes[0], False, "TOP face: faces the lid (the side you would see through a clear lid)"),
             (axes[1], True, "BOTTOM face: faces the battery (drawn as if the board were glass, seen from above)"))
    for ax, bottom, label in faces:
        anchors = draw_face(ax, board, bottom, x0, y0, w, h, changed, port)
        place_labels(ax, anchors, w, h, bottom)
        ax.set_xlim(-0.8, w + 0.8)
        ax.set_ylim(h + 4.9, -4.9)
        ax.set_aspect("equal")
        ax.grid(False)
        ax.set_xticks([])
        ax.set_yticks([])
        for s in ax.spines.values():
            s.set_visible(False)
        ax.set_title(label, fontsize=13, loc="left", color=INK, pad=4)
        ax.text(-0.6, -4.3, "← front of the glasses", fontsize=10, color=INK2, ha="left", va="top")
        ax.plot([w - 10.6, w - 0.6], [-4.0, -4.0], color=INK2, lw=2)
        ax.text(w - 5.6, -4.25, "10 mm", fontsize=10, color=INK2, ha="center", va="bottom")
    fig.suptitle(a.title, fontsize=17, color=INK, x=0.02, ha="left", y=0.985, fontweight="bold")
    fig.text(0.02, 0.962, f"Board {w:.0f} x {h:.0f} mm, 4 copper layers, 0.8 mm thick. Coloured blocks = parts (outline = one job). "
             "Dashed white outline = new or changed in Rev F. Faint lines = copper wiring.", fontsize=11, color=INK2)
    fig.text(0.02, 0.028, PAD_KEY, fontsize=10.5, color=INK2)
    fig.text(0.02, 0.012, "Why this arrangement: the microphone sits alone at the quiet front end; the noisy parts (speaker driver, "
             "power converter) are 11+ mm away, over a solid ground layer.", fontsize=10.5, color=INK2)
    fig.tight_layout(rect=(0, 0.04, 1, 0.955))
    fig.savefig(a.out, dpi=150)
    print(a.out)


if __name__ == "__main__":
    main()
