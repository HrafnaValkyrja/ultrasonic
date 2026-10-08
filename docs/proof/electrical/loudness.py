"""Loudness proof: 208 mA clamp -> exciter force -> sensation level -> vs ambient. Numbers: docs/proof/electrical/loudness.md."""
import json, sys, pathlib
import numpy as np
root = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(root / "tools")); import plotstyle; plotstyle.apply()
import matplotlib.pyplot as plt
d = json.load(open(root / "sim/acoustics/out/bone_results.json"))["headline_per_volt"]
F = np.array([1500, 2000, 2500, 3000, 4000])
Ft = np.array([d[f"{f}Hz"]["F_level_db_re_1uN_per_V_terminal"] for f in F])   # dB re 1 uN per 1 V rms at the terminals, nominal
lo = np.array([d[f"{f}Hz"]["terminal_p05"] for f in F])
RETFL = dict(zip([1250,1500,1600,2000,2500,3000,3150,4000],[39.0,36.5,35.5,31.0,29.5,30.0,31.0,35.5]))
retfl = np.interp(F, list(RETFL), list(RETFL.values()))
front = np.array([31.1, 33.7, 34.5, 30.9, 29.5])           # Surendran 2023 front site, from bone_results thr_front_measured
sites = {"front of tragus (measured, Surendran 2023)": front, "D1 bone-side (RETFL - 10)": retfl - 10, "mastoid RETFL (worst)": retfl}
q = np.array([0.0, -1.3, -4.0, -5.8, -5.4])                 # air hearing threshold, dB SPL (ISO 226:2003, rounded)
# drive
vdd, re_, rp, imax = 3.045, 8.0, 1.3, 0.208
v_full = vdd; i_full = vdd / (re_ + rp)
v_t_pk = imax * re_; v_t_rms = v_t_pk / 2**.5
p_mw = imax**2 * re_ / 2 * 1e3
clamp_db = 20*np.log10(imax / i_full)
Fl = Ft + 20*np.log10(v_t_rms)                              # force level at clamp, full-scale sine
print("full I %.0f mA, clamp %.0f mA (%.1f dB); Vpk term %.2f V, Vrms %.2f V, P %.0f mW" % (i_full*1e3, imax*1e3, clamp_db, v_t_pk, v_t_rms, p_mw))
print("F level", Fl.round(1), "p05", (lo + 20*np.log10(v_t_rms)).round(1))
for k, t in sites.items(): print(k, "SL", (Fl - t).round(1), "SL p05", (Fl - 9.0 - t).round(1))
# ambient: band level in the 1.5-4 kHz region ~ dBA - 11 (assumed spectrum), masked-tone threshold = band - 4 (critical ratio)
amb = {"quiet room 35": 35, "office 50": 50, "street 70": 70}
BAND = -11
res = {}
for site, t in sites.items():
    sl = Fl - 9.0 - t                                       # use p05 exciter (-9 dB) = pessimistic coupling/placement spread
    spl_eq = sl + q                                         # equivalent eardrum SPL of the exciter signal, dB
    for a, dba in amb.items():
        need = dba + BAND + 12.5 - 0                        # +10..15 above ambient band level (mid 12.5)
        res[(site, a)] = (spl_eq - need)
    print(site, "eq SPL", spl_eq.round(1))
fig, ax = plt.subplots(1, 2, figsize=(11, 4.6))
cols = ["#58a6ff", "#d29922", "#f85149"]
for (k, t), c in zip(sites.items(), cols):
    ax[0].plot(F/1e3, Fl - t, "-o", color=c, label=k + ", nominal")
    ax[0].plot(F/1e3, Fl - 9 - t, "--", color=c)
ax[0].set_xlabel("kHz"); ax[0].set_ylabel("sensation level at full-scale sine, 208 mA clamp (dB)")
ax[0].set_title("Headroom above hearing threshold (dashed = p05 exciter)")
ax[0].legend(fontsize=7)
site = list(sites)[1]
x = np.arange(len(amb)); w = .25
for i, (k, c) in enumerate(zip(sites, cols)):
    m = [res[(k, a)][1:4].mean() for a in amb]
    ax[1].bar(x + (i-1)*w, m, w, color=c, label=k)
ax[1].axhline(0, color="#c9d1d9", ls="--"); ax[1].set_xticks(x); ax[1].set_xticklabels(list(amb))
ax[1].set_ylabel("margin over ambient+12.5 dB alert target (dB, 2-3 kHz, p05)")
ax[1].set_title("Alert margin at full-scale sine (+ = passes)")
ax[1].legend(fontsize=7)
fig.suptitle("Exciter loudness at the 208 mA firmware clamp (RC-BC02 model, sim/acoustics/bone.py)")
fig.tight_layout(); fig.savefig(pathlib.Path(__file__).with_name("loudness.png"), dpi=140)
for k in sites: print(k, {a: res[(k, a)].round(1).tolist() for a in amb})
