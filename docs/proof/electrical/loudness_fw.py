"""Before/after alert margin for the loudness firmware fix (fw knobs alert_hz, lim_lookahead). Reuses the loudness.py chain.
Before = shipped chain: -12 dBFS true-peak ceiling (0.251 of Vdd diff), alert band 1.5-4 kHz average (no alert placement).
After  = alert at 2-3 kHz, look-ahead limiter ceiling = R64 clamp (0.6353) - shaper excursion (0.1150) = 0.5203.
Reference (loudness.md table) = full-scale sine at the clamp 0.6353, 2-3 kHz."""
import io, contextlib, pathlib, sys, numpy as np
sys.argv = ["x"]
with contextlib.redirect_stdout(io.StringIO()):
    import runpy
    g = runpy.run_path(str(pathlib.Path(__file__).with_name("loudness.py")))
plt, F, Fl, sites, q = g["plt"], g["F"], g["Fl"], g["sites"], g["q"]
front = list(sites)[0]; t = sites[front]
AMP_CLAMP = 0.635270; EXC = 0.115050
cases = {"before: -12 dBFS ceiling, 1.5-4 kHz": (0.2511886, [0,1,2,3,4]),
         "tone moved only (2-3 kHz), -12 dBFS ceiling": (0.2511886, [1,2,3]),
         "after: 2-3 kHz + look-ahead limiter at clamp": (AMP_CLAMP - EXC, [1,2,3]),
         "reference (doc table): full scale at clamp": (AMP_CLAMP, [1,2,3])}
amb = {"quiet 35": 35, "office 50": 50, "street 70": 70}
res = {}
for name, (amp, idx) in cases.items():
    gain = 20*np.log10(amp/AMP_CLAMP)                       # dB vs the clamp-level sine used in loudness.py
    for site_pretty, tt in (("p05", Fl - 9.0 - t), ("nominal", Fl - t)):
        eq = tt + gain + q
        for a, dba in amb.items():
            res[(name, site_pretty, a)] = float(np.mean((eq - (dba - 11 + 12.5))[idx]))
for k, v in res.items():
    if k[1] == "p05": print(f"{k[0]:48s} {k[2]:9s} p05 {v:+6.1f}  nominal {res[(k[0],'nominal',k[2])]:+6.1f}")
fig, ax = plt.subplots(figsize=(8.5, 4.4))
cols = ["#f85149", "#d29922", "#3fb950", "#8b949e"]; x = np.arange(3); w = .2
for i, (name, c) in enumerate(zip(cases, cols)):
    ax.bar(x + (i-1.5)*w, [res[(name, "p05", a)] for a in amb], w, color=c, label=name)
ax.axhline(0, color="#c9d1d9", ls="--"); ax.set_xticks(x); ax.set_xticklabels(list(amb))
ax.set_ylabel("alert margin over ambient+12.5 dB (dB, p05 exciter, front site)")
ax.set_title("Loudness fix: alert margin before / after (fw knobs alert_hz, lim_lookahead)"); ax.legend(fontsize=7)
fig.tight_layout(); fig.savefig(pathlib.Path(__file__).with_name("loudness_fw.png"), dpi=140)
