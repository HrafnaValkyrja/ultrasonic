"""dB waterfall: delivered alert eq. SPL (front site, nominal, pure tone) vs required for 60/65 dBA. Numbers: audibility-requirement.md."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parents[3] / "tools"))
import plotstyle; plotstyle.apply(); from plotstyle import plt, SERIES, TEXT, TEXT_2
steps = [("legacy\n-12 dBFS", 51.6), ("fw: 2.5 kHz +\nlimiter (D17 A)", 4.5), ("pad stiffness\n3e5 N/m", 4.0), ("resonant pad\n(extra, E1/E2)", 4.0), ("D17: drop shaper\nmargin (1.7)", 1.7)]
fig, ax = plt.subplots(figsize=(9, 4.8)); cum = 0; x = 0
for i, (n, v) in enumerate(steps):
    if i == 0: ax.bar(i, v, color=SERIES[0]); cum = v
    else: ax.bar(i, v, bottom=cum, color=SERIES[2] if i < 3 else SERIES[3]); cum += v
    ax.text(i, cum + .6, f"{cum:.1f}", ha="center", color=TEXT, fontsize=9)
for lvl, lab, c in ((58, "need 60 dBA: 58 (54.5-61.5)", SERIES[1]), (63, "need 65 dBA: 63 (59.5-66.5)", SERIES[7])):
    ax.axhline(lvl, color=c, ls="--"); ax.text(len(steps) - .45, lvl + .5, lab, color=c, ha="right", fontsize=8)
ax.set_xticks(range(len(steps))); ax.set_xticklabels([s[0] for s in steps], fontsize=8, color=TEXT_2)
ax.set_ylim(45, 72); ax.set_ylabel("alert eq. SPL at ear, dB (nominal, front site, pure tone)")
ax.set_title("Audibility waterfall: cheapest combination vs 60 / 65 dBA day-to-day (band +-10 dB not shown)")
fig.tight_layout(); fig.savefig(pathlib.Path(__file__).with_name("audibility_waterfall.png"), dpi=140, facecolor=fig.get_facecolor())
