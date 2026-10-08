"""Real programme through the output chain -> per-1/3-octave eq. SPL at the ear vs day-to-day ambient spectra.
Programme: sim/out/nature/2_translated_only.wav (algorithm B on Port Meadow AudioMoth 192 kS/s, Zenodo 22079773, CC-BY-4.0; sim/dsp/nature_demo.py), 48 kS/s, peaks <= -12 dBFS.
Chain: sample = duty fraction of Vdd diff; 0.6353 -> 208 mA clamp (fw/variants.yaml, FWSIM-R64) => i = x*0.3274 A.
Force/A: sim/acoustics/out/bone_tf.json mag_db_n_per_a (nominal, Bl 1.0 assumed). Threshold: bone_tf thr_front_measured_db_re_1uN (Surendran 2023).
eq SPL = force dB re 1uN - thr_front + ISO226 air threshold Tf(f) [recall values]. Ambient spectra: shapes below [recall], normalised to the dBA."""
import json, pathlib, sys, numpy as np
from scipy.io import wavfile
from scipy import signal
R = pathlib.Path(__file__).parents[3]; sys.path.insert(0, str(R / "tools"))
import plotstyle; plotstyle.apply(); from plotstyle import plt, SERIES, TEXT, TEXT_2
fs, y = wavfile.read(R / "sim/out/nature/2_translated_only.wav"); x = y.astype(float) / 32768
A_PER_UNIT = 0.208 / 0.6353; CLAMP, CEIL_A, CEIL_C = 0.6353, 0.5203, 10 ** (-12 / 20)
tf = json.load(open(R / "sim/acoustics/out/bone_tf.json")); f_tf = np.array(tf["f_hz"])
magA = np.array(tf["mag_db_n_per_a"]); thr = np.array(tf["thr_front_measured_db_re_1uN"])
CF = np.array([315, 400, 500, 630, 800, 1000, 1250, 1600, 2000, 2500, 3150, 4000, 5000, 6300], float)
ISO = dict(zip([315,400,500,630,800,1000,1250,1600,2000,2500,3150,4000,5000,6300],[8.6,6.2,4.4,3.0,2.2,2.4,3.5,1.7,-1.3,-4.2,-6.0,-5.4,-1.5,6.0]))
def aw(f):
    f2 = f * f; r = 12194**2 * f2**2 / ((f2 + 20.6**2) * np.sqrt((f2 + 107.7**2) * (f2 + 737.9**2)) * (f2 + 12194**2))
    return 20 * np.log10(r) + 2.0
def interp(f, ys): return np.interp(np.log10(f), np.log10(f_tf), ys)
def bands_rms(sig, mask=None):
    """1/3-oct band rms of sig (A) via Welch PSD; mask selects time frames."""
    f, P = signal.welch(sig, fs, nperseg=4096)
    out = []
    for c in CF:
        s = (f >= c / 2**(1/6)) & (f < c * 2**(1/6)); out.append(np.sqrt(np.sum(P[s]) * (f[1]-f[0])))
    return np.array(out)
# call-active frames: top 10 % of 50 ms frames by energy
n = int(0.05 * fs); fr = x[: len(x)//n*n].reshape(-1, n); e = (fr**2).sum(1); act = fr[e >= np.quantile(e, 0.9)].ravel()
crest = 20*np.log10(np.max(abs(x)) / np.sqrt(np.mean(x**2))); crest_act = 20*np.log10(np.max(abs(act)) / np.sqrt(np.mean(act**2)))
peak0 = np.max(abs(x))
def eq(sig_scale, extra_db=0.0, which="act"):
    s = (act if which == "act" else x) * sig_scale * A_PER_UNIT
    iA = bands_rms(s)
    F = 20*np.log10(iA + 1e-30) + interp(CF, magA) + 120 + extra_db     # N -> dB re 1 uN: +120
    return F - interp(CF, thr) + np.array([ISO[c] for c in CF])
# ambient shapes (Z-weighted relative, then normalised to dBA)
def amb(kind, dba):
    f = CF
    if kind == "traffic": rel = np.interp(f, [315,400,500,630,800,1000,1250,1600,2000,2500,3150,4000,5000,6300], [-14,-13,-12,-11,-9,-8,-9,-10,-11,-13,-12,-14,-16,-18]) - aw(f)   # EN 1793-3 style, A-weighted given
    elif kind == "office": rel = -3.0*np.log2(f/500) - 0*f                     # NC-like fall, ~3 dB/oct above 500 (Z)
    elif kind == "babble": rel = -9.0*np.log2(np.maximum(f,1000)/1000) - 3.0*np.log2(np.minimum(f,1000)/1000+1e-9)*0 # LTASS falls ~9 dB/oct above 1k (Z)
    elif kind == "car": rel = -6.0*np.log2(f/100)                              # Z, 6 dB/oct
    tot = 10*np.log10(np.sum(10**((rel + aw(f))/10)))
    return rel + dba - tot
scen = [("C: -12 dBFS fixed (now)", CEIL_C / peak0, 0), ("A: limiter at clamp-shaper (peak 0.520)", CEIL_A / peak0, 0), ("B: ceiling = clamp (peak 0.635)", CLAMP / peak0, 0)]
rows = {}
for nme, sc, ex in scen:
    for tag, e_db in (("", 0), (" + TEAX14C02-8", 7.6)):
        E = eq(sc, e_db); rows[nme + tag] = dict(scale=sc, band=E.tolist(), laeq=float(10*np.log10(np.sum(10**((E + aw(CF))/10)))), cur_peak_mA=float(peak0*sc*A_PER_UNIT*1e3))
ambs = {"residential 55 dBA (traffic shape)": amb("traffic", 55), "office 50 dBA": amb("office", 50), "shop/cafe 65 dBA (babble)": amb("babble", 65), "car 68 dBA": amb("car", 68), "subdivision+car pass 60 dBA": amb("traffic", 60)}
out = dict(crest_db=crest, crest_active_db=crest_act, peak_dbfs=20*np.log10(peak0), cf=CF.tolist(), rows=rows, amb={k: v.tolist() for k, v in ambs.items()})
# margin summary: bands where programme (active calls) exceeds ambient + 8, and mean margin over 1.5-4 kHz
sel = (CF >= 1600) & (CF <= 4000); summ = {}
for r, d in rows.items():
    for a, av in ambs.items(): summ[f"{r} | {a}"] = float(np.mean(np.array(d["band"])[sel] - av[sel]))
out["mean_margin_1p6_4k"] = summ; json.dump(out, open(pathlib.Path(__file__).with_name("audibility_playback.json"), "w"), indent=1)
print(f"crest {crest:.1f} dB (active {crest_act:.1f}), peak {out['peak_dbfs']:.1f} dBFS")
for r, d in rows.items(): print(f"{r:48s} LAeq-eq {d['laeq']:5.1f}  peak {d['cur_peak_mA']:.0f} mA")
for k, v in summ.items(): print(f"{k:90s} {v:+6.1f}")
fig, axs = plt.subplots(1, 2, figsize=(13, 5), sharey=True)
for ax, ttl, names in ((axs[0], "Without exciter change", [r for r in rows if "TEAX" not in r]), (axs[1], "With TEAX14C02-8 (+7.6 dB)", [r for r in rows if "TEAX" in r])):
    for i, r in enumerate(names): ax.plot(CF, rows[r]["band"], "-o", ms=3, color=SERIES[i], label=r.replace(" + TEAX14C02-8", ""))
    for j, (a, av) in enumerate(ambs.items()):
        if "subdivision" in a: continue
        ax.plot(CF, av + 8, "--", color=SERIES[3 + j % 4], lw=1, label=f"need: {a} +8")
    ax.set_xscale("log"); ax.set_xticks(CF[::2]); ax.set_xticklabels([f"{int(c)}" for c in CF[::2]]); ax.set_title(ttl, fontsize=10); ax.set_xlabel("1/3-octave centre, Hz")
axs[0].set_ylabel("call-active programme, eq. SPL per band (dB); dashed = ambient band + 8 dB"); axs[0].legend(fontsize=6)
fig.suptitle("Port Meadow playback (sim/out/nature/2_translated_only.wav) through the output chain: per-band level vs day-to-day ambient")
fig.tight_layout(); fig.savefig(pathlib.Path(__file__).with_name("audibility_playback.png"), dpi=140, facecolor=fig.get_facecolor())
