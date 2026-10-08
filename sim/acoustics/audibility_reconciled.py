"""Per-call audibility with temporal integration, real limiter (port of fw/core/lahead.c) and a slow-AGC option.
    systemd-run --user --scope -p MemoryMax=3G python3 sim/acoustics/audibility_reconciled.py -> docs/proof/electrical/audibility_reconciled.png + .json
Detection level per call = max over the call of the 200 ms sliding band rms (Plomp&Bouman 1959 JASA 31:749 (abstract fetched 2026-10-08): exponential build-up, time constant ~375 ms @250 Hz to ~150 ms @8 kHz, i.e. ~200 ms at 1.6-4 kHz; ISO 532-1 / Moore-Glasberg time-varying loudness use ~100-200 ms integration), NOT long-term LAeq and NOT the peak.
Chain/ambients as sim/acoustics/programme_audibility.py (same constants, same masked threshold max(q, amb-4))."""
import json, sys, pathlib, numpy as np
from scipy import signal
from scipy.io import wavfile
root = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / "tools")); import plotstyle; plotstyle.apply()
import matplotlib.pyplot as plt
FS = 12500.0; TAU = 0.2
fs0, y0 = wavfile.read(root / "sim/out/nature/2_translated_only.wav"); y0 = y0 / 32768.0
y = signal.resample_poly(y0, 25, 96); pk0 = np.abs(y).max()
fc = np.array([1250, 1600, 2000, 2500, 3150, 4000, 5000.]); SEL = slice(1, 6)
sos_b = [signal.butter(4, [f / 2 ** (1 / 6), f * 2 ** (1 / 6)], "bp", fs=FS, output="sos") for f in fc]
CLAMP, I_FULL = 0.635, 0.327
CEIL = {"a": 0.251, "A": 0.5203}; KNEE = 0.70; REL = np.exp(-1.0 / (FS * 0.060))   # lim_knee_pct 70, limiter_release_ms 60 (knobs_def.h)

def lahead(x, c, knee_pct=KNEE):                      # exact port of fw_lahead_hop (3-sample lookahead, min over 4, mean of 4, release)
    kn = c * knee_pct; w = c - kn; a = np.abs(x)
    u = np.where(a > kn, (a - kn) / w, 0.0)
    R = np.where(a > kn, (kn + w * (u / (1 + u))) / np.maximum(a, 1e-12), 1.0)
    m = np.minimum.reduce([np.roll(R, -j) for j in range(4)])      # min over [k, k+3]
    G = sum(np.roll(m, -j) for j in range(4)) / 4.0
    G = np.roll(G, 0); out = np.empty_like(x); g = 1.0
    xd = np.concatenate([np.zeros(3), x])[:len(x)]   # input delayed 3 samples
    Gs = np.concatenate([np.ones(6), G])[:len(x)]    # gain aligned (6-sample total path as in the C: G over m(i-6..i-3))
    for i in range(len(x)):
        gr = g + REL * (1 - g); g = Gs[i] if Gs[i] < gr else gr; out[i] = xd[i] * g
    return out
def tp_limit(x, c):                                   # legacy: instant-attack peak limiter, 60 ms release
    out = np.empty_like(x); g = 1.0
    for i, v in enumerate(x):
        gr = g + REL * (1 - g); a = abs(v)
        g = gr if a * gr <= c else c / a
        out[i] = v * g
    return out
def agc(x, ratio=3.0, gmax_db=18.0):                  # slow compressor on 1.25-5 kHz envelope: att 20 ms, rel 400 ms; gain=(1-1/R)(Lref-L), 0..gmax
    sos = signal.butter(4, [1100, 5600], "bp", fs=FS, output="sos"); e2 = signal.sosfilt(sos, x) ** 2
    ae, re_ = np.exp(-1 / (FS * .02)), np.exp(-1 / (FS * .4)); env = np.empty_like(x); s = 1e-12
    for i, v in enumerate(e2):
        k = ae if v > s else re_; s = k * s + (1 - k) * v; env[i] = s
    L = 10 * np.log10(env + 1e-12); Lref = np.percentile(L, 99.5)
    gdb = np.clip((1 - 1 / ratio) * (Lref - L), 0, gmax_db); return x * 10 ** (gdb / 20), gdb

tf = json.load(open(root / "sim/acoustics/out/bone_tf.json")); f_tf = np.array(tf["f_hz"]); NA = np.array(tf["mag_db_n_per_a"]); THR = np.array(tf["thr_front_measured_db_re_1uN"])
res = json.load(open(root / "sim/acoustics/out/bone_results.json"))["headline_per_volt"]
P = np.array([1500, 2000, 2500, 3000, 4000.])
ref = np.array([res[f"{int(f)}Hz"]["F_level_db_re_1uN_per_V_terminal"] for f in P]) + 20 * np.log10(0.208 * 8 / 2 ** .5)
OFF = float(np.mean(ref - (120 + np.interp(np.log(P), np.log(f_tf), NA) + 20 * np.log10(0.208 / 2 ** .5))))
q = np.interp(np.log(fc), np.log(P), [0.0, -1.3, -4.0, -5.8, -5.4])
thr = np.interp(np.log(fc), np.log(f_tf), THR); na = np.interp(np.log(fc), np.log(f_tf), NA) + OFF
Aw = lambda f: (lambda f2: 20 * np.log10(12194 ** 2 * f2 ** 2 / ((f2 + 20.6 ** 2) * np.sqrt((f2 + 107.7 ** 2) * (f2 + 737.9 ** 2)) * (f2 + 12194 ** 2))) + 2.0)(f ** 2)
oc = np.array([63, 125, 250, 500, 1000, 2000, 4000, 8000.])
amb_oct = {"Private office NC-35 [ETB]": [60, 52, 45, 40, 36, 34, 33, 32], "Street day, commercial [ETB]": [62, 57, 52, 47, 42, 38, 34, 32],
           "Open office NC-40 [ETB]": [64, 56, 50, 45, 41, 39, 38, 37], "Heavy traffic [ETB]": [72, 67, 62, 57, 52, 48, 44, 42]}
to3 = lambda o: np.interp(np.log(fc), np.log(oc), o) - 10 * np.log10(3)
amb = {k: to3(np.array(v, float)) for k, v in amb_oct.items()}
def scaled(shape, dba):
    ff = np.geomspace(100, 10000, 60); full = np.interp(np.log(ff), np.log(oc), shape) - 10 * np.log10(3)
    return to3(np.array(shape, float)) + dba - 10 * np.log10(np.sum(10 ** ((full + Aw(ff)) / 10)))
# Cafe: babble ~ speech spectrum. Shape = ANSI S3.5 normal-effort speech octave levels (63-8k) as tabulated in Odeon Application Note Restaurants (odeon.dk, fetched 2026-10-08);
# level 67 dBA = lowest occupied-venue mean in RWTH Aachen restaurant logging study (publications.rwth-aachen.de/record/772183, fetched 2026-10-08; range 67-77.8 dBA). Proxy, not a measured cafe 1/3-oct spectrum.
amb["Cafe 67 dBA [speech-shape proxy]"] = scaled([45.0, 55.0, 65.3, 69.0, 63.0, 55.8, 49.8, 44.5], 67)
amb["Car 68 dBA [unsourced]"] = scaled([72, 67, 62, 57, 52, 48, 44, 42], 68)

# events in the unprocessed programme: 100 ms frames within 20 dB of loudest, runs merged across gaps < 0.3 s
fr = int(.1 * FS); n = len(y) // fr; fr_rms = np.sqrt((y[:n * fr].reshape(n, fr) ** 2).mean(1)); act = fr_rms > fr_rms.max() * .1
ev = []; i = 0
while i < n:
    if act[i]:
        j = i
        while j + 1 < n and act[j + 1:j + 4].any(): j += 1
        ev.append((i * fr, (j + 1) * fr)); i = j + 1
    else: i += 1
ev = [e for e in ev if fr_rms[e[0] // fr:e[1] // fr].max() > fr_rms.max() * .1]
win = int(TAU * FS)
def band_levels(x, extra):                           # per band: sliding 200 ms rms -> eq SPL time series
    out = []
    for sb, qq, tt, nn in zip(sos_b, q, thr, na):
        b = signal.sosfilt(sb, x); r = np.sqrt(np.convolve(b ** 2, np.ones(win) / win, "same"))
        out.append(120 + 20 * np.log10(np.maximum(r, 1e-9) * I_FULL) + nn + extra - tt + qq)
    return np.array(out)
def crest_stats(x):
    e = [x[a:b] for a, b in ev]; pk = np.abs(x).max()
    sw = np.convolve(x ** 2, np.ones(win) / win, "same")
    cal = [20 * np.log10(np.abs(x[a:b]).max() / np.sqrt(sw[a:b].max())) for a, b in ev]
    return 20 * np.log10(pk / x.std()), float(np.median(cal))

def prep(opt):
    base = y / pk0                                    # peak 1
    if opt == "a":   x = tp_limit(base * CEIL["a"], CEIL["a"]); return x, 0.0
    if opt == "A":   x = lahead(base * CEIL["A"], CEIL["A"]); return x, 0.0
    if opt == "Aplus12": x = lahead(base * CEIL["A"] * 10 ** (12 / 20), CEIL["A"]); return x, 0.0
    if opt == "T":   return None, 7.6
    if opt == "AGC":
        z, gdb = agc(base); z = z / np.abs(z).max() * CEIL["A"]; return lahead(z, CEIL["A"]), 0.0
OPTS = [("a  today D17 -12 dBFS, peak-normalised", "a", 0.0), ("A  look-ahead limiter, peak-normalised (limiter idle)", "A", 0.0),
        ("A  +12 dB drive into limiter", "Aplus12", 0.0), ("A + TEAX14C02-8 (+7.6 dB)", "A", 7.6),
        ("A + TEAX, +12 dB drive into limiter", "Aplus12", 7.6), ("A + slow AGC (3:1, 18 dB max) + TEAX", "AGC", 7.6), ("A + slow AGC (3:1, 18 dB max), no TEAX", "AGC", 0.0)]
R = {}; cache = {}
for name, key, ex in OPTS:
    if key not in cache: cache[key] = prep(key)[0]
    x = cache[key]; L = band_levels(x, ex); cr = crest_stats(x)
    inact = np.ones(len(x), bool)
    for a, b in ev: inact[max(0, a - win):b + win] = False
    bg = float(np.sqrt((x[inact] ** 2).mean())) if inact.any() else 0.0
    ent = {"crest_file_db": cr[0], "crest_call_peak_over_200ms_db": cr[1], "peak_dbfs": 20 * np.log10(np.abs(x).max()), "bg_rms_dbfs": 20 * np.log10(bg + 1e-9), "amb": {}}
    Lev = np.array([L[:, a:b].max(1) for a, b in ev])         # events x bands
    ent["call_best_band_eq_spl"] = [float(v) for v in Lev[:, SEL].max(1)]
    for an, av in amb.items():
        mt = np.maximum(q, av - 4)[None, :]
        m = (Lev - mt)[:, SEL].max(1)                           # best band per call
        h = (Lev - av[None, :])[:, SEL].max(1)
        ent["amb"][an] = {"margin_per_call": m.round(1).tolist(), "median": float(np.median(m)), "min": float(m.min()), "headroom_median": float(np.median(h))}
    R[name] = ent
json.dump({"events_s": [(a / FS, b / FS) for a, b in ev], "tau_s": TAU, "results": R, "amb_dba": {k: float(10 * np.log10(np.sum(10 ** ((v + Aw(fc)) / 10)))) for k, v in amb.items()}}, open(root / "sim/acoustics/out/audibility_reconciled.json", "w"), indent=1)
print("events", len(ev), [(round(a / FS, 1), round(b / FS, 1)) for a, b in ev])
for k, v in R.items():
    print("%-55s crest file %.1f, call peak-over-200ms %.1f, bg %.1f dBFS" % (k, v["crest_file_db"], v["crest_call_peak_over_200ms_db"], v["bg_rms_dbfs"]))
    print("    median(min) margin: " + " | ".join("%s %+.1f(%+.1f)" % (a[:12], d["median"], d["min"]) for a, d in v["amb"].items()))
    print("    headroom over ambient (median): " + " ".join("%+.1f" % d["headroom_median"] for d in v["amb"].values()))
# plot: heatmap of median margin
names = list(R); ans = list(amb)
M = np.array([[R[n]["amb"][a]["median"] for a in ans] for n in names]); Mn = np.array([[R[n]["amb"][a]["min"] for a in ans] for n in names])
fig, ax = plt.subplots(figsize=(11, 5)); ax.grid(False)
im = ax.imshow(M, cmap="RdYlGn", vmin=-25, vmax=32, aspect="auto")
for i in range(M.shape[0]):
    for j in range(M.shape[1]): ax.text(j, i, "%+.0f\n(%+.0f)" % (M[i, j], Mn[i, j]), ha="center", va="center", fontsize=8, color="#000", fontweight="bold")
ax.set_xticks(range(len(ans))); ax.set_xticklabels([a.replace(" [", "\n[") for a in ans], fontsize=7.5); ax.set_yticks(range(len(names))); ax.set_yticklabels(names, fontsize=7.5)
ax.set_title("Per-call detection margin, dB (median over %d calls; worst call in brackets): 200 ms integrated best band vs masked threshold" % len(ev), fontsize=9, loc="left")
fig.tight_layout(); fig.savefig(root / "docs/proof/electrical/audibility_reconciled.png", dpi=130)
