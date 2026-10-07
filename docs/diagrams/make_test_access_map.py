#!/usr/bin/env python3
"""Test-access map (sub-debug-test DBG-11), generated from hw/pod/draft_r2/placement.yaml: every probe point per face
and per build stage, plus the J-pad neighbour pairs to meter before power (reg-board issue 4).

    python3 docs/diagrams/make_test_access_map.py   # -> docs/diagrams/test-access-map.svg + .png (dark, tools/plotstyle.py)

Both panels are drawn in board coordinates as seen from the F face (B items seen through the board).
"""
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import plotstyle  # noqa: E402

plotstyle.apply()
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, Rectangle  # noqa: E402

P = yaml.safe_load((ROOT / "hw/pod/draft_r2/placement.yaml").read_text())
TXT, MUT = "#e8e8e5", "#a4a9b0"
F_ITEMS = {"TP1": "SWDIO", "TP2": "SWCLK", "TP3": "NRST", "TP4": "+3V0", "TP5": "GND", "TP6": "VSYS"}
B_DOTS = {"TP7": "printf TX (PB6)", "TP8": "MDF CCK (fallback)", "TP9": "fallback dot", "TP10": "fallback dot / PB4 meter",
          "R1": "BOOT0 tack -> DFU", "R20": "lift: meter +3V0 / inject", "R21": "lift: bridge off"}
J = {"J1": "OUT_A", "J2": "OUT_B", "J3": "DOCK_VBUS", "J4": "GND", "J5": "VBAT", "J7": "LED_A", "J8": "LED_K", "J9": "TS",
     "J10": "D+", "J11": "D-", "J12": "CC"}
PAIRS = [("J3", "J4"), ("J4", "J5"), ("J1", "J2"), ("J2", "J8"), ("J12", "J9"), ("J10", "J11")]   # reg-board issue 4
R21 = (19.45, 6.45)
OFF = {"TP9": (-0.2, -1.0), "R1": (-0.2, -1.0), "TP8": (0.45, 0.35), "TP10": (0.45, 0.35), "J3": (-3.6, -1.0)}   # label offsets (mm) where dots crowd


def xy(ref):
    if ref == "R21":
        return R21
    v = P[ref]
    return v[0], v[1]


def board(ax, title):
    ax.add_patch(Rectangle((0, 0), 30, 12, fc="#15301f", ec="#35b535", lw=1.2))
    ax.set_xlim(-1, 31)
    ax.set_ylim(-1.5, 13.8)
    ax.set_aspect("equal")
    ax.set_title(title, color=TXT, fontsize=11)
    ax.set_xlabel("board x (mm)")
    ax.set_ylabel("board y (mm)")


def main():
    fig, (a, b) = plt.subplots(2, 1, figsize=(12, 10.5))
    board(a, "F face (toward the lid): bare-board stage only - after the lid bond (assembly step 8) these are unreachable")
    for ref, net in F_ITEMS.items():
        x, y = xy(ref)
        a.add_patch(Circle((x, y), 0.5, fc="#5b9ff2", ec=TXT, lw=0.8))
        a.annotate(f"{ref}\n{net}", (x, y + 0.75), color=TXT, fontsize=8, ha="center")
    x, y = xy("SW1")
    a.add_patch(Rectangle((x - 1.5, y - 1.3), 3.0, 2.6, fc="none", ec="#8d7ff0", lw=1.2))
    a.annotate("SW1", (x, y), color="#8d7ff0", ha="center", va="center", fontsize=9)
    a.add_patch(Circle((1.88, 6.0), 0.3, fc="#141518", ec="#ff6d6c", lw=1.2))
    a.annotate("mic port\n(keep-out r 1.6)", (1.88, 4.4), color="#ff6d6c", fontsize=8, ha="center")
    a.text(0, -1.2, "SWD/pogo on TP1-TP6 (1.5 pitch; TP4 +3V0 beside TP5 GND: DBG-2 smear risk). Field path after the bond: dock USB -> ROM DFU (boot stub).",
           color=MUT, fontsize=8)
    board(b, "B face (toward the cell), seen through the board: reachable whenever the lid is lifted (board hangs on its wires)")
    for ref, what in B_DOTS.items():
        x, y = xy(ref)
        b.add_patch(Circle((x, y), 0.35, fc="#f28c3f", ec=TXT, lw=0.8))
        dx, dy = OFF.get(ref, (0.45, 0.35))
        b.annotate(f"{ref}: {what}", (x + dx, y + dy), color=TXT, fontsize=7.5)
    for ref, net in J.items():
        x, y = xy(ref)
        b.add_patch(Circle((x, y), 0.45, fc="#52d39e", ec=TXT, lw=0.8))
        dx, dy = OFF.get(ref, (0.55, -0.15))
        b.annotate(f"{ref} {net}", (x + dx, y + dy), color=TXT, fontsize=7)
    for p, q in PAIRS:
        (x1, y1), (x2, y2) = xy(p), xy(q)
        b.plot([x1, x2], [y1, y2], color="#ff6d6c", lw=1.5, ls="--")
    b.text(0, -1.2, "Red dashed = neighbour pairs to meter BEFORE first power (bring-up step 1): J3-J4, J4-J5, J1-J2, J2-J8, J12-J9, J10-J11.",
           color=MUT, fontsize=8)
    fig.suptitle("Test access map (Phase 2 board, from placement.yaml) - stages: bare board = all; wired, lid off = B only; bonded = dock USB only",
                 color=TXT, fontsize=11)
    fig.tight_layout()
    fig.savefig(HERE / "test-access-map.svg", bbox_inches="tight")
    fig.savefig(HERE / "test-access-map.png", dpi=130, bbox_inches="tight")
    print("wrote", HERE / "test-access-map.svg")


if __name__ == "__main__":
    main()
