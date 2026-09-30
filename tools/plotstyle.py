"""Shared matplotlib style for harness plots (PNG files that Claude and the owner inspect).

    import plotstyle; plotstyle.apply()
    ax.plot(t, v, color=plotstyle.SERIES[0])

Rules: categorical colours in this fixed order (never cycled past 8), one y-axis per
subplot (no twin axes), a legend only when a subplot has two or more series, quiet grid.
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

# Validated categorical palette (light surface), fixed order.
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
SURFACE = "#fcfcfb"
TEXT = "#0b0b0b"
TEXT_2 = "#52514e"
GRID = "#e4e3df"


def apply():
    plt.rcParams.update({
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "axes.edgecolor": TEXT_2,
        "axes.labelcolor": TEXT,
        "axes.titlecolor": TEXT,
        "axes.titlesize": 10,
        "axes.labelsize": 9,
        "axes.prop_cycle": matplotlib.cycler(color=SERIES),
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.6,
        "xtick.color": TEXT_2,
        "ytick.color": TEXT_2,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "legend.fontsize": 8,
        "legend.frameon": False,
        "lines.linewidth": 1.4,
        "font.size": 9,
        "figure.dpi": 110,
        "savefig.dpi": 110,
        "savefig.bbox": "tight",
    })
    return plt
