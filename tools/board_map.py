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
# technical labels (--style tech): part numbers, nets and functions for a reader who knows electronics (owner 2026-10-03)
TECH = {
    "MCU": ("U1 STM32U575 (Cortex-M33, QFN48)", "ADF1 PDM in, TIM1 complementary PWM out, USB FS, I2C2 to U3, ADC1/4 sense", "#5b9ff2"),
    "CORE_SMPS": ("MCU SMPS: L1 2.2 uH, C7/C8/C9", "VLXSMPS -> L1 -> VDD11 1.1 V core; C7 10 uF at VDDSMPS", "#8d7ff0"),
    "CLOCK": ("Y1 32.768 kHz LSE + C11/C12", "RTC / LSE (PC14/PC15), C0G load caps", "#a4a9b0"),
    "MIC": ("U2 SPH0641LU4H-1 PDM mic", "ultrasonic mode; CLK PB3 via R2 33R, DATA PB4; VDD from PA5 (C13)", "#2fc98f"),
    "BRIDGE": ("H-bridge Q1/Q2 PMCXB290UE", "2x N+P pairs, 200 kHz AD PWM; R3-R6 100k gate pulls; C14 22 uF", "#f58a5c"),
    "SELFTEST": ("I_SENSE: R21 0.1R low-side shunt", "BRIDGE_RTN -> R22/C22 16 kHz LPF -> PA6 ADC1_IN11", "#ff6d6c"),
    "ARM_PADS": ("Arm pads J1/J2/J7/J8", "OUT_A/OUT_B to the exciter, LED_A/LED_K to the pad LED", "#f09bbd"),
    "DOCK_USB": ("Dock pads + protection", "D4 reverse-block Schottky; D5/D6 TPD1E10B06 (VBUS, CC); U6 TPD2E2U06 (D+/D-); R12/R13 VBUS_SENSE; R18 Rd 5k1", "#f2b632"),
    "CHARGER": ("U3 BQ25180 charger (DSBGA-8)", "I2C linear charger + power path: IN=VBUS, SYS=VSYS, BAT=VBAT; TS via RT1 or J9; R15/R16 I2C pull-ups", "#35b535"),
    "CELL_PADS": ("Cell pad J5", "", "#35b535"),
    "VBAT_SENSE": ("VBAT divider R8/R9 1M/1M + C19", "VBAT/2 -> PA4 (ADC4, runs in Stop 2)", "#7fd47f"),
    "LDO": ("U4 TPS7A2030 LDO", "VSYS -> 3.0 V (C17 in, C18 out); R20 0R link to +3V0", "#e8c86a"),
    "UI": ("SW1 KMT022 + LED drive", "SW1 -> PA0 WKUP1 (R10 2k2 pull-down); R14 2k2 LED series from VSYS, LED_K on PB7", "#e87ba4"),
    "DEBUG": ("Test pads", "TP1-6 SWDIO/SWCLK/NRST/3V0/GND/VSYS; TP7 USART1 TX printf; TP8-10 MDF mic fallback", "#c9ccd1"),
}
PAD_KEY_TECH = ("Wire pads:  5V = J3 DOCK_VBUS   G = J4 GND (dock + cell -)   B+ = J5 VBAT   T = J9 TS (cell NTC)   "
                "D+/D- = J10/J11 USB   CC = J12   SA/SB = J1/J2 OUT_A/OUT_B   L+/L- = J7/J8 LED_A/LED_K")
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


LABELS = PLAIN


LEGEND = []          # tech style: (number, colour, name, job) collected across both faces


def place_badges(ax, anchors):
    """Tech style: a numbered badge on each zone; the text goes in a legend under the figure (dense labels collide)."""
    for blk, (l, t_, r, b_, _) in sorted(anchors.items(), key=lambda kv: (kv[1][0], kv[1][1])):
        if blk == "PADS":
            name, job, col = "Wire pads J1-J5, J7-J12", "1.0 mm hand-solder pads, >= 0.8 mm gaps between nets (key below)", "#e7c24a"
        else:
            name, job, col = LABELS[blk]
        n = next((k for k, c, nm, j in LEGEND if nm == name), None)
        if n is None:
            n = len(LEGEND) + 1
            LEGEND.append((n, col, name, job))
        ax.add_patch(Circle((l + 0.15, t_ + 0.15), 0.42, fc=col, ec="#0b0b0b", lw=0.8, zorder=9))
        ax.text(l + 0.15, t_ + 0.17, str(n), ha="center", va="center", fontsize=8.5, fontweight="bold", color="#0b0b0b", zorder=10)


def place_labels(ax, anchors, w, h, bottom):
    items = []
    for blk, (l, t_, r, b_, _) in anchors.items():
        if blk == "PADS":
            name, job, col = (("Wire pads J1-J5, J7-J12", "1.0 mm hand-solder pads, >= 0.8 mm gaps between nets (key below)", "#e7c24a")
                              if LABELS is TECH else ("Wire pads", "hand-soldered wires: dock, battery, ear pad (codes below)", "#e7c24a"))
        else:
            name, job, col = LABELS[blk]
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
            lines = textwrap.wrap(job, 34 if LABELS is TECH else 30) if job else []
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
    ap.add_argument("--style", choices=["plain", "tech"], default="plain")
    a = ap.parse_args()
    global LABELS
    LABELS = TECH if a.style == "tech" else PLAIN
    board = pcbnew.LoadBoard(a.board)
    bb = board.GetBoardEdgesBoundingBox()
    x0, y0, w, h = MM(bb.GetLeft()), MM(bb.GetTop()), MM(bb.GetWidth()), MM(bb.GetHeight())
    changed = set(filter(None, a.changed.split(",")))
    port = None
    for fp in board.GetFootprints():
        for p in fp.Pads():
            if p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                port = (MM(p.GetPosition().x), MM(p.GetPosition().y))
    tech = a.style == "tech"
    fig, axes = plt.subplots(2, 1, figsize=(15, 15.5 if tech else 18.5))
    if tech:
        fig.subplots_adjust(left=0.01, right=0.99, top=0.93, bottom=0.27, hspace=0.12)
    faces = ((axes[0], False, "TOP face: faces the lid (the side you would see through a clear lid)"),
             (axes[1], True, "BOTTOM face: faces the battery (drawn as if the board were glass, seen from above)"))
    for ax, bottom, label in faces:
        anchors = draw_face(ax, board, bottom, x0, y0, w, h, changed, port)
        if LABELS is TECH:
            place_badges(ax, anchors)
        else:
            place_labels(ax, anchors, w, h, bottom)
        ax.set_xlim(-0.8, w + 0.8)
        ax.set_ylim(*((h + 1.0, -2.6) if LABELS is TECH else (h + 4.9, -4.9)))
        ax.set_aspect("equal")
        ax.grid(False)
        ax.set_xticks([])
        ax.set_yticks([])
        for s in ax.spines.values():
            s.set_visible(False)
        ax.set_title(label, fontsize=13, loc="left", color=INK, pad=4)
        ty = -2.2 if LABELS is TECH else -4.3
        ax.text(-0.6, ty, "← front of the glasses", fontsize=10, color=INK2, ha="left", va="top")
        ax.plot([w - 10.6, w - 0.6], [ty + 0.3, ty + 0.3], color=INK2, lw=2)
        ax.text(w - 5.6, ty + 0.05, "10 mm", fontsize=10, color=INK2, ha="center", va="bottom")
    fig.suptitle(a.title, fontsize=17, color=INK, x=0.02, ha="left", y=0.985, fontweight="bold")
    fig.text(0.02, 0.962, f"Board {w:.0f} x {h:.0f} mm, 4 copper layers, 0.8 mm thick. Coloured blocks = parts (outline = one job). "
             + ("Dashed white outline = new or changed in Rev F. " if changed else "") + "Faint lines = copper wiring.", fontsize=11, color=INK2)
    if tech:
        half = (len(LEGEND) + 1) // 2
        for i, (n, col, name, job) in enumerate(LEGEND):
            cx, row = (0.02, i) if i < half else (0.51, i - half)
            y = 0.235 - row * 0.027
            fig.text(cx, y, f"{n}", fontsize=10, fontweight="bold", color="#0b0b0b",
                     bbox=dict(boxstyle="circle,pad=0.25", fc=col, ec="none"))
            fig.text(cx + 0.022, y, name, fontsize=10, fontweight="bold", color=col)
            fig.text(cx + 0.022, y - 0.012, textwrap.shorten(job, 100), fontsize=8.6, color=INK2)
    fig.text(0.02, 0.028, PAD_KEY_TECH if LABELS is TECH else PAD_KEY, fontsize=10.5, color=INK2)
    fig.text(0.02, 0.012, "Why this arrangement: the microphone sits alone at the quiet front end; the noisy parts (speaker driver, "
             "power converter) are 11+ mm away, over a solid ground layer.", fontsize=10.5, color=INK2)
    if not tech:
        fig.tight_layout(rect=(0, 0.04, 1, 0.955))
    fig.savefig(a.out, dpi=150)
    print(a.out)


if __name__ == "__main__":
    main()
