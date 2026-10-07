#!/usr/bin/env python3
"""Belly-bay section (sub-dock-usb DK-14), generated from hw/mech/dims_r2.py + hw/mech/dock_route.py constants:
pod x-z section at the dock's centre plane (y = 9.15): window in the belly floor, YZT0675 target, tails bent flat
under the cell, potting, the dock ribbon to the rear gap, the cell above. Tail thickness and potting are [A] until a
sample is in hand (DK-02, DK-03).

    python3 docs/diagrams/make_belly_section.py   # -> docs/diagrams/belly-section.svg + .png (dark, tools/plotstyle.py)
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
from matplotlib.patches import Polygon, Rectangle  # noqa: E402

TXT, MUT = "#e8e8e5", "#a4a9b0"
TAIL_T = 0.20      # [A] flat tail thickness (brass strip), not dimensioned on the LCSC drawing
X_TAIL_END = 52.9  # [A] tails' end = dock_route.TAIL


def rect(ax, x0, x1, z0, z1, fc, ec=None, alpha=0.6, label=None, hatch=None):
    ax.add_patch(Rectangle((x0, z0), x1 - x0, z1 - z0, fc=fc, ec=ec or fc, alpha=alpha, label=label, hatch=hatch, lw=1.0))


def main():
    cv, ce, dk = D.CAV, D.CELL, D.DOCK
    fig, ax = plt.subplots(figsize=(14, 5.6))
    outline = [(D.X0, D.Z0 + 3.5), (D.X1, D.Z0 + 3.5), (D.X1, D.Z0), (D.X_BELLY, D.Z0), (D.X_BELLY, D.Z_BELLY), (D.X0, D.Z_BELLY)]
    ax.add_patch(Polygon(outline, closed=True, fc="#4a4d55", ec=MUT, alpha=0.45, label="tub (belly all tub, x < 55)"))
    rect(ax, cv["x0"], cv["x1"], cv["z0"], D.Z0 + 3.5, "#141518", alpha=1.0)
    rect(ax, D.BAY["x0"], D.BAY["x1"], D.BAY["z0"], D.BAY["z1"], "#141518", alpha=1.0)
    rect(ax, dk["x0"] - 0.1, dk["x1"] + 0.1, D.Z_BELLY, D.BAY["z0"], "#141518", alpha=1.0)          # window through the floor
    rect(ax, dk["x0"], dk["x1"], dk["z0"], dk["z1"], "#f58a5c", label="YZT0675 target 21.2 x 2.8 (5 contacts face out)")
    rect(ax, dk["x0"], X_TAIL_END, cv["z0"], cv["z0"] + TAIL_T, "#f28c3f", alpha=0.9, label="tails bent flat over the target back [A 0.2 thick]")
    rect(ax, dk["x0"], X_TAIL_END + 1.0, cv["z0"] + TAIL_T, ce["z0"] - 0.25, "#8d7ff0", alpha=0.35, hatch="..", label="potting over the tails (removable silicone, sealing S5)")
    ax.plot([X_TAIL_END, 65.85, 65.85], [-8.5, -8.5, -7.6], color="#ff6d6c", lw=2.5, label="dock ribbon (32/36 AWG enamel, flat) to the rear gap")
    rect(ax, ce["x0"], ce["x1"], ce["z0"], D.Z0 + 3.5, "#a19d8d", alpha=0.45, label="cell (0.8 above the cavity floor)")
    for x0, txt in ((31.0, "0.8 slack under the cell: tails + ribbon + potting"),):
        ax.annotate(txt, (x0, -7.6), color=TXT, fontsize=8)
    ax.annotate(f"belly {D.Z0 - D.Z_BELLY:.2f} deep, x < {D.X_BELLY}", (D.X0 + 0.3, D.Z_BELLY - 0.45), color=MUT, fontsize=8)
    ax.annotate("rear gap 1.1 (cell end 65.6 to wall 66.7)", (61.0, -6.9), color=MUT, fontsize=8)
    ax.set_xlim(28.5, 68.5)
    ax.set_ylim(-12.6, D.Z0 + 3.6)
    ax.set_aspect("equal")
    ax.set_xlabel("pod x (mm)")
    ax.set_ylabel("pod z (mm, up)")
    ax.set_title("Belly bay, section at the dock centre (y 9.15), generated from dims_r2: tails and potting [A] until a sample (DK-02/03)", color=TXT, fontsize=10)
    ax.legend(fontsize=7.5, loc="lower left", bbox_to_anchor=(0.0, -0.75), ncol=2, labelcolor=TXT, facecolor="#1e2025")
    fig.tight_layout()
    fig.savefig(HERE / "belly-section.svg", bbox_inches="tight")
    fig.savefig(HERE / "belly-section.png", dpi=130, bbox_inches="tight")
    print("wrote", HERE / "belly-section.svg")


if __name__ == "__main__":
    main()
