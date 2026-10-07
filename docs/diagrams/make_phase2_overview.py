#!/usr/bin/env python3
"""Phase-2 physical overview (physical.md issue 11), generated from hw/mech/dims_r2.py: replaces the Rev F
system-overview-physical.png. Two to-scale panels: (a) cross-section through the dock (pod y-z at x = 45),
(b) plan seen through the lid (pod x-z). Right pod frame; the left pod mirrors the shell and flips the board
(hw/mech/board_in_pod.py).

    python3 docs/diagrams/make_phase2_overview.py   # -> docs/diagrams/phase2-overview.svg + .png (dark, tools/plotstyle.py)
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "hw/mech"))
sys.path.insert(0, str(ROOT / "tools"))
import dims_r2 as D  # noqa: E402
import plotstyle  # noqa: E402

plotstyle.apply()
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, Polygon, Rectangle  # noqa: E402

C = dict(body="#4a4d55", lid="#5b9ff2", plate="#8d7ff0", cell="#a19d8d", board="#35b535", vhb="#f28c3f", dock="#f58a5c",
         wire="#ff6d6c", text="#e8e8e5", muted="#a4a9b0")


def rect(ax, x0, x1, y0, y1, fc, ec=None, alpha=0.55, label=None, lw=1.0):
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc=fc, ec=ec or fc, alpha=alpha, lw=lw, label=label))


def main():
    fig, (a, b) = plt.subplots(1, 2, figsize=(15, 6.6), gridspec_kw=dict(width_ratios=[1, 2.3]))
    cv, ce, pc, dk = D.CAV, D.CELL, D.PCB, D.DOCK
    # (a) section y-z at x = 45 (inside the belly, through the dock target)
    rect(a, D.Y_IN, D.Y_OUT, D.Z0, D.Z1, C["body"], alpha=0.35, label="tub + lid shell (0.8 walls)")
    rect(a, D.Y_IN, D.Y_OUT, D.Z_BELLY, D.Z0, C["body"], alpha=0.35)
    rect(a, cv["y0"], cv["y1"], cv["z0"], cv["z1"], "#141518", alpha=1.0)
    rect(a, D.Y_IN + D.W, D.Y_OUT - D.W, D.Z_BELLY + D.W, cv["z0"], "#141518", alpha=1.0)
    rect(a, ce["y0"], ce["y1"], ce["z0"], ce["z1"], C["cell"], label="cell 175 mAh (VHB to the inner wall)")
    rect(a, pc["y0"], pc["y1"], pc["z0"], pc["z1"], C["board"], label="board 30 x 12 x 0.8, parts on B")
    rect(a, D.Y_F, D.Y_LID_IN, pc["z0"] + 0.2, pc["z1"] - 0.2, C["vhb"], label="VHB 0.25 (board hangs from the lid)")
    rect(a, D.Y_LID_IN, D.Y_OUT, D.Z0, D.Z1, C["lid"], alpha=0.35, label="lid 0.8")
    rect(a, D.Y_OUT, D.Y_TOP, D.Z0 + 0.6, D.Z1 - 0.6, C["plate"], label="armour plate 0.7")
    rect(a, dk["y0"], dk["y1"], dk["z0"], dk["z1"], C["dock"], label="dock target (belly)")
    a.plot([7.0, 10.0], [-8.5, -8.5], color=C["wire"], lw=2.5, label="dock ribbon under the cell")
    a.plot([D.Y_B, D.Y_B], [D.Z_BELLY - 0.3, D.Z1 + 0.3], ls=":", color=C["muted"], lw=0.8)
    a.text(D.Y_B + 0.1, D.Z_BELLY - 0.6, "seam y 12.1", color=C["muted"], fontsize=8)
    a.text(D.Y_IN - 0.1, D.Z1 + 0.5, "head side", color=C["muted"], fontsize=8, ha="right")
    a.text(D.Y_TOP + 0.1, D.Z1 + 0.5, "outside", color=C["muted"], fontsize=8, ha="left")
    a.set_xlim(3.5, 16.5)
    a.set_ylim(-12.5, 6.0)
    a.set_aspect("equal")
    a.set_xlabel("pod y (mm, through the thickness)")
    a.set_ylabel("pod z (mm, up)")
    a.set_title("(a) section at x = 45 (through the dock)")
    a.legend(fontsize=7, loc="lower left", bbox_to_anchor=(0.0, -0.52), labelcolor=C["text"], facecolor="#1e2025")
    # (b) plan x-z through the lid
    outline = [(D.X0, D.Z1), (D.X1, D.Z1), (D.X1, D.Z0), (D.X_BELLY, D.Z0), (D.X_BELLY, D.Z_BELLY), (D.X0, D.Z_BELLY)]
    b.add_patch(Polygon(outline, closed=True, fc=C["body"], ec=C["muted"], alpha=0.35, label="pod outline (belly x < 55)"))
    rect(b, ce["x0"], ce["x1"], ce["z0"], ce["z1"], C["cell"], alpha=0.35, label="cell (below the board)")
    rect(b, pc["x0"], pc["x1"], pc["z0"], pc["z1"], C["board"], alpha=0.45, label="board")
    rect(b, dk["x0"], dk["x1"], dk["z0"], dk["z1"], C["dock"], label="dock target 21.2 x 2.8 (belly)")
    rect(b, pc["x0"] + D.PAD_ZONE[0], pc["x1"], pc["z0"], pc["z1"], "none", ec=C["wire"], alpha=1.0, lw=1.2, label="rear wire pads (B), board x 25-30")
    rect(b, pc["x1"], cv["x1"], cv["z0"], cv["z1"], "none", ec=C["vhb"], alpha=1.0, lw=1.0, label="stowage zone behind the board")
    b.add_patch(Circle(D.MIC, D.DUCT_D / 2, fc="none", ec=C["wire"], lw=1.8, label="mic duct D1.0 (hex mesh seat)"))
    b.add_patch(Circle(D.SW, D.PUCK_D / 2, fc="none", ec=C["plate"], lw=1.8, label="button puck D2.3"))
    b.plot([66.2], [-5.5], "x", color=C["wire"], ms=9, label="heel wire exit -> NiTi arm -> pad")
    b.annotate("front (toward the hinge)", (D.X0, D.Z1 + 0.6), color=C["muted"], fontsize=8)
    b.annotate("rear (ear)", (D.X1 - 4, D.Z1 + 0.6), color=C["muted"], fontsize=8)
    b.set_xlim(28.5, 69.0)
    b.set_ylim(-12.5, 6.0)
    b.set_aspect("equal")
    b.set_xlabel("pod x (mm)")
    b.set_ylabel("pod z (mm, up)")
    b.set_title("(b) plan, seen through the lid (right pod; the left pod flips the board)")
    b.legend(fontsize=7, loc="lower left", bbox_to_anchor=(0.0, -0.52), ncol=3, labelcolor=C["text"], facecolor="#1e2025")
    fig.suptitle("Phase-2 pod (MZ-2): 38.0 x 10.4 x 14.5 mm + belly 2.05, generated from hw/mech/dims_r2.py", color=C["text"], y=1.03)
    fig.tight_layout()
    fig.savefig(HERE / "phase2-overview.svg", bbox_inches="tight")
    fig.savefig(HERE / "phase2-overview.png", dpi=130, bbox_inches="tight")
    print("wrote", HERE / "phase2-overview.svg")


if __name__ == "__main__":
    main()
