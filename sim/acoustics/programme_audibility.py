"""Programme audibility: the REAL translated nature programme, through the output chain, at her ear, vs ambient spectra.

    python3 sim/acoustics/programme_audibility.py   # -> docs/proof/electrical/programme_audibility.png + stdout tables

Programme: sim/out/nature/2_translated_only.wav = sim/dsp/nature_demo.py algo_b output on four Port Meadow bat passes
(Zenodo 22079773, CC-BY-4.0; run `python3 sim/dsp/nature_demo.py` to regenerate). Peak is -9.45 dBFS before the output ceiling.
Chain: peak-normalise to the option's ceiling -> bridge current (327 mA at full scale, clamp 208 mA = 0.635) ->
force/current from bone_tf.json (nominal, calibrated to loudness.py) -> minus front-of-tragus threshold (Surendran 2023)
= sensation level -> plus air threshold q = equivalent eardrum SPL (loudness.md method, +-10 dB).
Not used: sim/fw/vectors/bats.npz holds only ADF input words (no output taps); the wav is the same chain's output.
"""
import json, sys, pathlib
import numpy as np
from scipy import signal
from scipy.io import wavfile
root = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / "tools")); import plotstyle; plotstyle.apply()
import matplotlib.pyplot as plt

CEIL = {"a": 0.251, "A": 0.5203, "c": 0.5203}   # D17 -12 dBFS; option A limiter (clamp minus shaper excursion)
BL_GAIN_C = 7.6                                  # TEAX14C02-8 vs assumed Bl 1.0 (R-exciter2.md)
I_FULL, CLAMP = 0.327, 0.635                     # A at full scale; clamp fraction (208 mA)
fc = np.array([1250, 1600, 2000, 2500, 3150, 4000, 5000], float)   # 1/3-octave centres analysed

fs, y = wavfile.read(root / "sim/out/nature/2_translated_only.wav"); y = y / 32768.0
# band rms of the programme (1/3 octave, fractions of full scale), whole file and 'active' frames
def third_rms(x, fs, fcs):
    out = []
    for f in fcs:
        sos = signal.butter(4, [f / 2 ** (1 / 6), f * 2 ** (1 / 6)], "bp", fs=fs, output="sos")
        out.append(signal.sosfilt(sos, x))
    return np.array(out)
B = third_rms(y, fs, fc)
fr = int(0.1 * fs); n = len(y) // fr
frame_rms = np.sqrt((y[:n * fr].reshape(n, fr) ** 2).mean(1))
active = frame_rms > frame_rms.max() * 10 ** (-20 / 20)
def rms_bands(mask):
    m = np.repeat(mask, fr)[:B.shape[1]] if mask is not None else slice(None)
    return np.sqrt((B[:, :len(np.repeat(mask, fr))][:, np.repeat(mask, fr)] ** 2).mean(1)) if mask is not None else np.sqrt((B ** 2).mean(1))
b_all, b_act = rms_bands(None), rms_bands(active)
pk = np.abs(y).max(); crest_db = 20 * np.log10(pk / y.std()); crest_act = 20 * np.log10(pk / np.sqrt((y[:n*fr].reshape(n, fr)[active] ** 2).mean()))

tf = json.load(open(root / "sim/acoustics/out/bone_tf.json"))
f_tf = np.array(tf["f_hz"]); NA = np.array(tf["mag_db_n_per_a"]); THR = np.array(tf["thr_front_measured_db_re_1uN"])
# calibrate N/A curve to loudness.py (per-volt terminal at 1.18 V rms) on its five probe points
res = json.load(open(root / "sim/acoustics/out/bone_results.json"))["headline_per_volt"]
P = np.array([1500, 2000, 2500, 3000, 4000.])
Fclamp_ref = np.array([res[f"{int(f)}Hz"]["F_level_db_re_1uN_per_V_terminal"] for f in P]) + 20 * np.log10(0.208 * 8 / 2 ** .5)
Fclamp_tf = 120 + np.interp(np.log(P), np.log(f_tf), NA) + 20 * np.log10(0.208 / 2 ** .5)
OFF = float(np.mean(Fclamp_ref - Fclamp_tf))
q = np.interp(np.log(fc), np.log([1500, 2000, 2500, 3000, 4000]), [0.0, -1.3, -4.0, -5.8, -5.4])   # ISO 226 air threshold, loudness.py
thr = np.interp(np.log(fc), np.log(f_tf), THR); na = np.interp(np.log(fc), np.log(f_tf), NA) + OFF

def eq_spl(bands, ceil, extra_db=0.0):
    g = ceil / pk                                       # peak-normalise to ceiling (volume set to just reach it)
    assert ceil <= CLAMP
    i_rms = bands * g * I_FULL                          # A rms in band
    F = 120 + 20 * np.log10(i_rms) + na + extra_db      # dB re 1 uN
    return F - thr + q                                  # SL + q

Aw = lambda f: (lambda f2: 20 * np.log10(12194 ** 2 * f2 ** 2 / ((f2 + 20.6 ** 2) * np.sqrt((f2 + 107.7 ** 2) * (f2 + 737.9 ** 2)) * (f2 + 12194 ** 2))) + 2.0)(f ** 2)
laeq = lambda L: 10 * np.log10(np.sum(10 ** ((L + Aw(fc)) / 10)))
opts = {"(a) today: D17 -12 dBFS": (CEIL["a"], 0.0), "(b) A: limiter at R64 clamp": (CEIL["A"], 0.0), "(c) A + TEAX14C02-8": (CEIL["c"], BL_GAIN_C)}
L_act = {k: eq_spl(b_act, c, e) for k, (c, e) in opts.items()}
L_all = {k: eq_spl(b_all, c, e) for k, (c, e) in opts.items()}

# ambient: octave bands (63..8000) -> 1/3-octave by log-interp minus 10log10(3)
oc = np.array([63, 125, 250, 500, 1000, 2000, 4000, 8000.])
amb_oct = {  # Engineering ToolBox pages fetched 2026-10-08 (outdoor-noise_d_62 (2003); nc-noise-criterion_d_725 (2004))
    "Urban street, business/commercial, day [ETB]": [62, 57, 52, 47, 42, 38, 34, 32],
    "Next to heavy traffic (<91 m), day [ETB]": [72, 67, 62, 57, 52, 48, 44, 42],
    "Open-plan office, NC-40 [ETB/ASHRAE NC]": [64, 56, 50, 45, 41, 39, 38, 37],
    "Private office, NC-35 [ETB/ASHRAE NC]": [60, 52, 45, 40, 36, 34, 33, 32],
}
def to_third(o): return np.interp(np.log(fc), np.log(oc), o) - 10 * np.log10(3)
amb = {k: to_third(np.array(v, float)) for k, v in amb_oct.items()}
# [unsourced] shop/cafe and car: no fetchable spectrum; assumed shape = heavy-traffic row (falls ~4.5 dB/oct) scaled to an assumed dBA
def scaled(shape_oct, dba):
    full = np.interp(np.log(np.geomspace(100, 10000, 60)), np.log(oc), shape_oct) - 10 * np.log10(3)
    ff = np.geomspace(100, 10000, 60); cur = 10 * np.log10(np.sum(10 ** ((full + Aw(ff)) / 10)))
    return to_third(np.array(shape_oct, float)) + (dba - cur)
amb["Shop/cafe 65 dBA [unsourced]"] = scaled([57, 59, 61, 60, 56, 51, 46, 41], 65)
amb["Car interior 68 dBA [unsourced]"] = scaled([72, 67, 62, 57, 52, 48, 44, 42], 68)
amb_dba = {k: laeq(v) for k, v in amb.items()}

out = {"fc": fc.tolist(), "OFF_db": OFF, "crest_db": crest_db, "crest_active_db": crest_act, "peak_dbfs": 20 * np.log10(pk), "rms_dbfs": 20 * np.log10(y.std()),
       "laeq_active": {k: laeq(v) for k, v in L_act.items()}, "laeq_all": {k: laeq(v) for k, v in L_all.items()},
       "prog_active": {k: v.round(1).tolist() for k, v in L_act.items()}, "amb": {k: v.round(1).tolist() for k, v in amb.items()}, "amb_dba": amb_dba, "audibility": {}}
print("cal offset %.2f dB; peak %.1f dBFS crest %.1f dB (active frames %.1f); active frames %d/%d" % (OFF, out["peak_dbfs"], crest_db, crest_act, active.sum(), n))
for k, v in L_act.items(): print(k, "LAeq active %.1f whole %.1f" % (out["laeq_active"][k], out["laeq_all"][k]), v.round(1))
for a, av in amb.items():
    mt = np.maximum(q, av - 4.0)                       # masked threshold: ambient band - 4 dB (critical ratio, loudness.py), floor = quiet
    out["audibility"][a] = {}
    for k, v in L_act.items():
        au = v - mt; hd = v - av
        out["audibility"][a][k] = {"aud": au.round(1).tolist(), "head": hd.round(1).tolist(), "aud_mean": float(au[1:6].mean()), "head_mean": float(hd[1:6].mean())}
        print("%-48s %-30s audib %+5.1f  headroom %+5.1f (mean 1.6-4 kHz)  [crest-6dB compressed: audib %+5.1f head %+5.1f]" % (a, k, au[1:6].mean(), hd[1:6].mean(), au[1:6].mean()+crest_act-6, hd[1:6].mean()+crest_act-6))
json.dump(out, open(root / "sim/acoustics/out/programme_audibility.json", "w"), indent=1)

fig, axs = plt.subplots(2, 3, figsize=(14, 7.5), sharey=True)
cols = plotstyle.SERIES
for ax, (a, av) in zip(axs.ravel(), amb.items()):
    ax.fill_between(fc / 1e3, 0, np.maximum(q, av - 4), color="#2c2e34", alpha=.9, label="masked threshold (amb-4)")
    ax.plot(fc / 1e3, av, color=plotstyle.TEXT_2, ls="--", label="ambient 1/3-oct")
    for c, (k, v) in zip(cols, L_act.items()): ax.plot(fc / 1e3, v, "-o", color=c, label=k)
    ax.set_title("%s\n%.0f dBA" % (a, amb_dba[a]), fontsize=8, loc="left"); ax.set_xscale("log"); ax.set_xticks([1.25, 2, 3.15, 5]); ax.set_xticklabels(["1.25", "2", "3.15", "5"])
    ax.set_xlabel("kHz"); ax.set_ylim(0, 70); ax.minorticks_off()
    for lab, c in zip(opts, cols):
        m = out["audibility"][a][lab]["aud_mean"]
    ax.text(.02, .04, "mean audibility a/b/c: " + " / ".join("%+.0f" % out["audibility"][a][k]["aud_mean"] for k in opts) + " dB", transform=ax.transAxes, fontsize=7.5, color=plotstyle.TEXT)
axs[0, 0].set_ylabel("dB SPL at ear (1/3 octave)"); axs[1, 0].set_ylabel("dB SPL at ear (1/3 octave)"); axs[0, 0].legend(fontsize=6.5, loc="upper right", labelcolor=plotstyle.TEXT, facecolor=plotstyle.SURFACE)
fig.suptitle("Port Meadow bat programme at her ear (translated 1.5-4 kHz, active frames) vs day-to-day ambient")
fig.tight_layout(); fig.savefig(root / "docs/proof/electrical/programme_audibility.png", dpi=130)
