"""dB waterfall for AUDIO PLAYBACK (programme rms at the ear, eq. SPL, nominal front site, 2.5 kHz-class). Numbers: audibility-requirement.md."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parents[3] / "tools"))
import plotstyle; plotstyle.apply(); from plotstyle import plt, SERIES, TEXT, TEXT_2
steps = [("legacy -12 dBFS\nceiling", 43.9), ("limiter at clamp\n(D17 opt. A)", 6.3), ("drop shaper\nmargin (D17)", 1.7), ("playback compr.\ncrest 6->4 dB", 2.0), ("pad 3e5 N/m\n(same current)", 4.0), ("broad resonant\npad Q<=2", 2.0)]
fig, ax = plt.subplots(figsize=(9.5, 4.9)); cum = 0
for i, (n, v) in enumerate(steps):
    if i == 0: ax.bar(i, v, color=SERIES[0]); cum = v
    else: ax.bar(i, v, bottom=cum, color=SERIES[2] if i < 4 else SERIES[3]); cum += v
    ax.text(i, cum + .5, f"{cum:.1f}", ha="center", color=TEXT, fontsize=9)
for lvl, lab, c in ((50, "55 dBA subdivision: 50", SERIES[1]), (55, "60 dBA design: 55", SERIES[7]), (60, "65 dBA cafe: 60", SERIES[5])):
    ax.axhline(lvl, color=c, ls="--"); ax.text(len(steps) - .45, lvl + .4, lab, color=c, ha="right", fontsize=8)
ax.set_xticks(range(len(steps))); ax.set_xticklabels([s[0] for s in steps], fontsize=8, color=TEXT_2)
ax.set_ylim(40, 66); ax.set_ylabel("programme rms at ear, dB eq. SPL (+-10 dB)")
ax.set_title("Listening-level waterfall: need = ambient dBA - 5 (band -13, +8 dB headroom)")
fig.tight_layout(); fig.savefig(pathlib.Path(__file__).with_name("audibility_waterfall.png"), dpi=140, facecolor=fig.get_facecolor())
