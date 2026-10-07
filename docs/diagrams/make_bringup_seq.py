#!/usr/bin/env python3
"""Bring-up sequence diagram from docs/build/bringup.yaml (ECR-0010): stages as boxes, gates as red bars.

    python3 docs/diagrams/make_bringup_seq.py   # -> docs/diagrams/bringup-sequence.svg + .png (dark, tools/plotstyle.py)
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
from matplotlib.patches import FancyBboxPatch  # noqa: E402

D = yaml.safe_load((ROOT / "docs/build/bringup.yaml").read_text())
TXT, MUT, RED, GRN, BLU, ORG = "#e8e8e5", "#a4a9b0", "#ff6d6c", "#52d39e", "#5b9ff2", "#f28c3f"
GATE_BEFORE = {"B": "G0", "C": "G1", "D": "G2", "F": "G3", "G": "G4", "I": "G5"}
COL = {"A": MUT, "B": BLU, "C": ORG, "D": BLU, "E": BLU, "F": GRN, "G": GRN, "H": GRN, "I": GRN}

stages = D["stages"]
fig, ax = plt.subplots(figsize=(12, 11))
fig.subplots_adjust(0.01, 0.04, 0.99, 0.95)
ax.set_xlim(0, 11)
ax.set_ylim(len(stages) * 1.4 - len(stages) * 1.4 + 0.8, len(stages) * 1.4 + 0.9)
ax.axis("off")
y = len(stages) * 1.4
for st in stages:
    g = GATE_BEFORE.get(st["id"])
    if g:
        ax.plot([0.3, 10.7], [y + 0.62, y + 0.62], color=RED, lw=2.5)
        ax.text(10.7, y + 0.68, f"GATE {g}: {D['gates'][g]}", color=RED, fontsize=8, ha="right", va="bottom")
    c = COL[st["id"]]
    ax.add_patch(FancyBboxPatch((0.3, y - 0.45), 10.4, 0.95, boxstyle="round,pad=0.02", fc="none", ec=c, lw=1.6))
    ax.text(0.5, y + 0.28, f"{st['id']}  {st['name']}", color=c, fontsize=11, weight="bold", va="center")
    ids = "  ".join(s["id"] for s in st["steps"])
    items = [f"{s['id']} {s['tag']}" for s in st["steps"]]
    short = "\n".join("   ".join(items[i:i + 5]) for i in range(0, len(items), 5))
    ax.text(0.5, y - 0.15, short, color=TXT, fontsize=8, va="center")
    y -= 1.4
ax.set_title(f"Bring-up sequence (ECR-0010, {D['date']}): {sum(len(s['steps']) for s in stages)} steps, top to bottom",
             color=TXT, fontsize=13)
fig.text(0.02, 0.01, "blue = electrical on the bare board, orange = first power, green = in the pod, grey = no electricity; "
         "red = do not pass until the step before it passed", color=MUT, fontsize=8)
for ext in ("svg", "png"):
    fig.savefig(HERE / f"bringup-sequence.{ext}", dpi=130)
print("wrote bringup-sequence.svg/.png")
