"""Summary bars for docs/proof/electrical/README.md: worst case / rating (1.0 = at the limit). Numbers are copied from the README table."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "tools"))
import plotstyle
plotstyle.apply()
import matplotlib.pyplot as plt
rows = [  # label, ratio, status
 ("Cell pulse: bridge peak 326 mA / 260 mA", 326/260, "FAIL"),
 ("U4 LDO rating: 326 mA / 300 mA", 326/300, "FAIL"),
 ("Cell charge: 130 mA / 1C 130 mA", 1.0, "PASS"),
 ("D5 ESD: VBUS 5.25 V / 5.5 V working", 5.25/5.5, "PASS"),
 ("Runtime: 8 h need / 10 h worst awake", 8/10.0, "PASS"),
 ("BM28 +3V0 pin: 163 mA / 300 mA", 163/300, "PASS"),
 ("Noise: 10 dB need / 34.8 dB margin", 10/34.8, "PASS"),
 ("D4 Schottky: 130 mA / 500 mA", 130/500, "PASS"),
 ("R20 link: 326 mA / 1 A", 0.326, "PASS"),
 ("R21 sense: 10 mW / 62.5 mW", 0.16, "PASS"),
]
col = {"PASS": "#3fb950", "FAIL": "#f85149", "OPEN": "#d29922"}
fig, ax = plt.subplots(figsize=(9, 4.8))
ax.barh([r[0] for r in rows][::-1], [r[1] for r in rows][::-1], color=[col[r[2]] for r in rows][::-1])
ax.axvline(1.0, color="#c9d1d9", ls="--", lw=1)
ax.set_xlabel("worst case / rating (1.0 = at the limit)")
ax.set_title("K4 P+M: electrical margins, 2026-10-08 (OPEN items in README)")
fig.tight_layout(); fig.savefig(pathlib.Path(__file__).with_name("summary.png"), dpi=140)
