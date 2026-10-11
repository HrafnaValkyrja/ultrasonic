#!/usr/bin/env python3
"""sim/perf/false_wake_audibility.py: is a Port Meadow false wake audible at the tragus? (docs/sim/false-wake-audibility.md)
Runs the port_meadow scenes through the host firmware (configs A=shipping B look-ahead, A+loud12, slim, slim+loud12), takes every
false-wake episode (IDLE->awake edge with no annotated call in [start-10 ms, end+30 ms], port_meadow.score rule), rebuilds the audio
the exciter gets (duty = CCR/140-1 averaged over the 8*reps PWM periods per 12.5 kHz sample, i.e. AFTER squelch + limiter), and applies the
audibility_reconciled.py chain: 5 third-octave bands 1.6-4 kHz, 200 ms integration (Plomp&Bouman 1959), I_FULL 0.327 A, bone TF + OFF,
front-of-tragus threshold (Surendran 2023) + masking offset q. Margin = best band level - threshold (dB); audible if > 0.
  systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 python3 sim/perf/false_wake_audibility.py [--json out.json]
"""
import sys, json, pathlib, argparse
import numpy as np
from scipy import signal
REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "sim/perf"))
import port_meadow as pm

FS = 12500.0; CH = 140.0; I_FULL = 0.327; WIN = int(0.2 * FS)
fc = np.array([1600, 2000, 2500, 3150, 4000.])
tf = json.load(open(REPO / "sim/acoustics/out/bone_tf.json")); f_tf = np.array(tf["f_hz"])
P = np.array([1500, 2000, 2500, 3000, 4000.])
res = json.load(open(REPO / "sim/acoustics/out/bone_results.json"))["headline_per_volt"]
ref = np.array([res[f"{int(f)}Hz"]["F_level_db_re_1uN_per_V_terminal"] for f in P]) + 20 * np.log10(0.208 * 8 / 2 ** .5)
NAall = np.array(tf["mag_db_n_per_a"])
OFF = float(np.mean(ref - (120 + np.interp(np.log(P), np.log(f_tf), NAall) + 20 * np.log10(0.208 / 2 ** .5))))
q = np.interp(np.log(fc), np.log(P), [0.0, -1.3, -4.0, -5.8, -5.4])
thr = np.interp(np.log(fc), np.log(f_tf), np.array(tf["thr_front_measured_db_re_1uN"]))
na = np.interp(np.log(fc), np.log(f_tf), NAall) + OFF
SOS = [signal.butter(4, [f / 2 ** (1 / 6), f * 2 ** (1 / 6)], "bp", fs=FS, output="sos") for f in fc]
OC = np.array([63, 125, 250, 500, 1000, 2000, 4000, 8000.])
AMB = {"quiet (threshold+q)": None,
       "private office NC-35": [60, 52, 45, 40, 36, 34, 33, 32],
       "street day": [62, 57, 52, 47, 42, 38, 34, 32]}
def amb3(o): return np.interp(np.log(fc), np.log(OC), o) - 10 * np.log10(3)

def audio(r, t0):
    per = len(r["ccr"]) // len(r["mode"]); reps = per // 8
    d = r["ccr"].astype(float).reshape(-1, reps).mean(1) / CH
    d = d - np.bincount(r["ccr"]).argmax() / CH          # remove squelch centre
    return d, int(t0 * FS)

def margins(x):
    """best-band margin (dB) time series vs each masking condition, and per-band level."""
    L = np.array([120 + 20 * np.log10(np.maximum(np.sqrt(np.convolve(signal.sosfilt(s, x) ** 2, np.ones(WIN) / WIN, "same")), 1e-9) * I_FULL) + n - t
                  for s, n, t in zip(SOS, na, thr)])      # level above quiet threshold, before q
    Lq = L + q[:, None]
    out = {k: (Lq - (q if v is None else np.maximum(q, amb3(np.array(v, float)) - 4))[:, None]).max(0) for k, v in AMB.items()}
    return out

def episodes(r, calls, t0):
    n = len(r["mode"]); t = (np.arange(n) + 1) * pm.HOP_S; a = (r["mode"] & 0xFF) != pm.IDLE_ST
    k0 = int(t0 / pm.HOP_S); tt = t[k0:] - t0; aa = a[k0:]
    rise = np.nonzero(aa[1:] & ~aa[:-1])[0] + 1
    eps = []
    for i in rise:
        if any(s - 0.010 <= tt[i] <= e + 0.030 for s, e in calls):
            continue
        j = i
        while j < len(aa) and aa[j:j + 78].any():       # merge awake gaps < 50 ms
            j += 1
        eps.append((i + k0, j + k0))                      # hop indices in full run
    return eps

def run(n_clips):
    real, quiet = pm.scenes(n_clips); out = {}
    for cfg in ("A", "A+loud12", "slim", "slim+loud12"):
        knobs, loud = pm.CONFIGS[cfg]; E = []; dur = 0.0
        for _, words, calls, t0 in real + quiet:
            r = pm.run_cfg(knobs, loud, words); dur += (len(r["mode"]) * pm.HOP_S - t0)
            eps = episodes(r, calls, t0)
            if not eps:
                continue
            x, _ = audio(r, t0); M = margins(x); a = (r["mode"] & 0xFF) != pm.IDLE_ST
            for h0, h1 in eps:
                s0 = h0 * 8; s1 = min(len(x), h1 * 8 + WIN)
                sq = r["sq"][h0:h1] == 0
                e = dict(awake_ms=(h1 - h0) * pm.HOP_S * 1e3, unsq_ms=float(sq.sum()) * pm.HOP_S * 1e3,
                         peak_dbfs=float(20 * np.log10(max(np.abs(x[s0:s1]).max(), 1e-6))))
                for k, m in M.items():
                    seg = m[s0:s1]; e[k] = dict(max=float(seg.max()), aud_s=float((seg > 0).sum() / FS))
                E.append(e)
        out[cfg] = dict(episodes=E, dur_s=dur)
    return out

def summarize(out):
    S = {}
    for cfg, o in out.items():
        E = o["episodes"]; n = len(E); hrs = o["dur_s"] / 3600; s = dict(n=n, per_min=n / o["dur_s"] * 60, dur_s=o["dur_s"])
        s["awake_ms_med"] = float(np.median([e["awake_ms"] for e in E])); s["unsq_ms_med"] = float(np.median([e["unsq_ms"] for e in E]))
        s["unsq_frac"] = float(np.mean([e["unsq_ms"] > 0 for e in E])); s["peak_dbfs_med"] = float(np.median([e["peak_dbfs"] for e in E]))
        for k in AMB:
            m = np.array([e[k]["max"] for e in E]); au = np.array([e[k]["aud_s"] for e in E])
            s[k] = dict(pct_audible=float((m > 0).mean() * 100), med_margin_all=float(np.median(m)), med_margin_audible=float(np.median(m[m > 0])) if (m > 0).any() else None,
                        p90_margin=float(np.percentile(m, 90)), max_margin=float(m.max()), aud_s_per_h=float(au.sum() / hrs), aud_med_s=float(np.median(au[m > 0])) if (m > 0).any() else None)
        S[cfg] = s
    return S

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--json", type=pathlib.Path); ap.add_argument("--clips", type=int, default=54); a = ap.parse_args()
    out = run(a.clips); S = summarize(out); print(json.dumps(S, indent=1))
    if a.json: a.json.write_text(json.dumps(dict(summary=S, episodes={k: v["episodes"] for k, v in out.items()}), indent=1))
