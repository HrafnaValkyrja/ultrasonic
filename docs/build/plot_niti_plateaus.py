"""NiTi plateau stresses from the only primary source that publishes BOTH plateaus for straight-annealed
superelastic wire (Fort Wayne Metals, fwmetals.com/what-we-do/materials/nitinol/superelastic-nitinol,
accessed 2026-09-30), against the two numbers the arm model uses (450 MPa loading, 200 MPa unloading).

FWM values are MINIMUMS (">"), tested in tension at 22 C and 37 C; the lines join the two test points.

    source tools/env.sh && python3 docs/build/plot_niti_plateaus.py   ->  docs/build/niti-plateaus.png
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import plotstyle  # noqa: E402

plt = plotstyle.apply()
S = plotstyle.SERIES

# grade: (label, active Af, (upper22, lower22), (upper37, lower37))  [MPa, minimums]
FWM = [
    ("NiTi #1", "Af 10..18 C", (483, 138), (552, 207)),
    ("NiTi #2", "Af 0..18 C", (552, 207), (621, 276)),
    ("NiTi #9", "Af -10..5 C", (517, 172), (552, 207)),
]
T = (22, 37)

fig, ax = plt.subplots(figsize=(7.2, 4.4))
ax.axvspan(30, 34, color=plotstyle.GRID, alpha=0.8, lw=0)
ax.text(32, 650, "skin\n30-34 C", ha="center", va="top", color=plotstyle.TEXT_2, fontsize=8)
for i, (name, af, lo, hi) in enumerate(FWM):
    c = S[i]
    ax.plot(T, (lo[0], hi[0]), color=c, marker="o", ms=3)
    ax.plot(T, (lo[1], hi[1]), color=c, marker="o", ms=3, ls="--")
    ax.text(21.6, lo[0], f"{name} ({af}) loading", color=c, va="center", ha="right", fontsize=8)
    ax.text(21.6, lo[1], f"{name} unloading", color=c, va="center", ha="right", fontsize=8)
m = S[3]
ax.axhline(450, color=m, lw=1.0, ls=":")
ax.axhline(200, color=m, lw=1.0, ls=":")
ax.text(44.8, 458, "arm model: loading 450 MPa", color=m, fontsize=8, ha="right")
ax.text(44.8, 186, "arm model: unloading 200 MPa\n(unsourced)", color=m, fontsize=8, ha="right", va="top")
ax.set_xlim(8, 45)
ax.set_ylim(0, 660)
ax.set_xticks([22, 25, 30, 35, 37])
ax.set_xlabel("wire temperature (C)")
ax.set_ylabel("plateau stress, minimum (MPa)")
ax.set_title("Straight-annealed superelastic NiTi: published MINIMUM plateaus (solid = loading at 3%, "
             "dashed = unloading at 2.5%)\nFort Wayne Metals, accessed 2026-09-30", loc="left")
out = Path(__file__).with_name("niti-plateaus.png")
fig.savefig(out)
print(out)
