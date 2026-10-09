#!/usr/bin/env python3
"""sim/perf/port_meadow.py: end-to-end performance regression on the real Port Meadow bat recording (AudioMoth, Zenodo 22079773).

Real clips (receiver_3 of N (default all 54) flypasts, 3 s each, machine-annotated calls, det_prob >= 0.5) -> sim/e2e front end (acoustic port, mic,
supply, ADF D1 stub; ONE global Pa scale so relative clip levels survive: the loudest 10 ms ultrasonic window of the reference clip
is 75 dB SPL, true calibration unknown) -> host firmware (sim/fw/fwlib.py, spec B, transient only, idle detector on). Each clip is
tiled 3x (floors settle, 1 s since power-on) and only the last copy is scored. Plus two call-free scenes (silence, house walk)
for false wakes. Configs (firmware knobs):
  today      defaults (limiter off, loud_db 0, hiz_idle 0)
  A          lim_lookahead 1 (D17 rec A: look-ahead limiter at the R64 clamp)
  A+loud4/12 A + loud_db 4 / 12 with the loud toggle ON
  A+loud12+shape  A+loud12 + loud_shape 1 (tanh flat-top k 2.5, I-034)
  hiz_idle   today + hiz_idle 1
Metrics: wake recall (awake within 10 ms of call start), sound recall (output unsquelched within 30 ms), false wakes/min (IDLE->awake
edges with no annotated call in [start-10 ms, end+30 ms]; the BatDetect2 labels miss some real calls, so an upper bound), false awake
fraction (awake hops >50 ms from any call), wake-to-sound latency (first call of an episode, >=0.5 s gap, to first unsquelched hop
when it was squelched before; hop = 0.64 ms), output level per call (max pre-quantiser true peak, dBFS, in [start, start+30 ms]),
mean current (model, below). Current = spec B nominal awake mA (sim/checks/runtime_fw.py) x awake + IDLE x idle + LED, with the exciter
row replaced by 0.327 A x mean|CCR - centre|/128 on awake hops (physical, as d17-cost.md), plus 0.45 mA bridge ripple on squelched hops unless hiz_idle (I-027). Model, not bench.
    python3 sim/perf/port_meadow.py            # check against sim/perf/port_meadow_baseline.json (exit 1 on regression)
    python3 sim/perf/port_meadow.py --bless    # rewrite the baseline
Run fenced: systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 python3 sim/perf/port_meadow.py
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy import signal
from scipy.io import wavfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path[:0] = [str(REPO / "sim/fw"), str(REPO / "sim/e2e"), str(REPO / "sim/dsp"), str(REPO / "sim/checks"), str(REPO / "tools")]
import chain as ch  # noqa: E402
import corpus  # noqa: E402
import fwlib  # noqa: E402
import gen_vectors as gv  # noqa: E402
import runtime_fw as rt  # noqa: E402

PM = ch.PM_DIR
BASELINE = HERE / "port_meadow_baseline.json"
BASE_KNOBS = {"algo": 2, "transient_only": 1, "idle_enable": 1}
CONFIGS = {
    "today": ({"lim_lookahead": 0, "loud_db": 0}, False),   # pre-D17 legacy; since 2026-10-08 the fw DEFAULT is A + loud_db 12 (loud OFF at boot), so these are pinned explicitly
    "A": ({"lim_lookahead": 1, "loud_db": 0}, False),   # = shipped default with the loud toggle never used (battery cost of A alone)
    "A+loud4": ({"lim_lookahead": 1, "loud_db": 4}, True),
    "A+loud12": ({"lim_lookahead": 1, "loud_db": 12}, True),
    "A+loud12+shape": ({"lim_lookahead": 1, "loud_db": 12, "loud_shape": 1}, True),   # I-034 flat-top, k = 2.5 (default knob)
    "hiz_idle": ({"hiz_idle": 1, "lim_lookahead": 0, "loud_db": 0}, False),
}
IDLE_ST = 3
HOP_S = 0.00064
REPS = 3
# pass/fail tolerances vs baseline (absolute): the firmware is deterministic, so these only absorb float/compiler drift
TOL = {"wake_recall": 0.01, "sound_recall": 0.01, "false_wakes_per_min": 2.0, "false_awake_frac": 0.01,
       "latency_p50_ms": 0.7, "latency_p90_ms": 1.4, "level_p50_dbfs": 0.3, "level_max_dbfs": 0.3, "mean_ma": 0.02}


def load_clips(n):
    """n flypasts spread evenly over the 54: (name, 192 kS/s float audio, [(start, end)])."""
    dirs = sorted(d for d in PM.iterdir() if (d / "receiver_3.wav").exists())
    idx = np.unique(np.linspace(0, len(dirs) - 1, n).round().astype(int))
    out = []
    for i in idx:
        d = dirs[i]
        fs, y = wavfile.read(d / "receiver_3.wav")
        calls = []
        for line in (d / "events_3.csv").read_text().splitlines()[1:]:
            c = line.split(",")
            if len(c) >= 4 and float(c[1]) >= 0.5:
                calls.append((float(c[2]), float(c[3])))
        out.append((d.name, y.astype(float) / 32768.0, calls))
    return out


def global_scale(spl=75.0):
    fs, y = wavfile.read(PM / "20251021_172626/receiver_3.wav")
    y = y.astype(float) / 32768.0
    u = signal.sosfilt(signal.butter(6, [20e3, 90e3], "bp", fs=fs, output="sos"), y)
    win = int(0.01 * fs)
    peak = np.sqrt(np.max(np.convolve(u ** 2, np.ones(win) / win, "valid")))
    return corpus.db_spl_to_pa_rms(spl) / peak


def scenes(n_clips):
    sc = global_scale()
    res = []
    for k, (name, y, calls) in enumerate(load_clips(n_clips)):
        pa = signal.resample_poly(np.tile(y * sc, REPS), 25, 12)
        res.append((name, gv.front(pa, 100 + k, "D1"), calls, len(y) / 192000 * (REPS - 1)))
    quiet = [("silence", np.zeros(int(10.0 * ch.FS)), 4, 3.0), ("house_walk", ch.house_walk(2.0, 1, 6.0)[0], 1, 3.0)]
    q = [(n, gv.front(x, s, "D1"), [], t0) for n, x, s, t0 in quiet]
    return res, q


def run_cfg(knobs, loud, words):
    fw = fwlib.Firmware({**BASE_KNOBS, **knobs})
    if loud:
        fw.set_loud(True)
    w = words[: len(words) // 128 * 128]
    return fw.run(w, t0_us=1_000_000)


def episode_starts(calls, gap=0.5):
    s = [c[0] for c in calls]
    return [t for i, t in enumerate(s) if i == 0 or t - calls[i - 1][1] >= gap]


def score(r, calls, t0):
    n = len(r["mode"])
    t = (np.arange(n) + 1) * HOP_S                      # end of hop h
    a = (r["mode"] & 0xFF) != IDLE_ST
    snd = r["sq"] == 0                                  # output unsquelched
    k0 = int(t0 / HOP_S)
    tt = t[k0:] - t0
    a, snd, pk = a[k0:], snd[k0:], r["peak"][k0:]
    cc = r["ccr"].reshape(n, -1).astype(float)          # drive = |CCR - squelch centre| (centre = the most common CCR value)
    centre = np.bincount(r["ccr"]).argmax()
    rms = np.abs(cc - centre).mean(axis=1)[k0:]
    sqf = (r["sq"][k0:] != 0)
    dur = tt[-1]
    iv = lambda x0, x1: (tt >= x0) & (tt <= x1)
    wake = [bool(a[iv(s, s + 0.010)].any()) for s, _ in calls]
    sound = [bool(snd[iv(s, s + 0.030)].any()) for s, _ in calls]
    rise = np.nonzero(a[1:] & ~a[:-1])[0] + 1
    fw_n = sum(not any(s - 0.010 <= tt[i] <= e + 0.030 for s, e in calls) for i in rise)
    near = np.zeros(len(tt), bool)
    for s, e in calls:
        near |= iv(s - 0.05, e + 0.05)
    lat = []
    for s in episode_starts(calls):
        j0 = np.searchsorted(tt, s)
        if j0 < len(tt) and not snd[max(j0 - 1, 0)]:
            j = np.nonzero(snd[j0:])[0]
            if len(j):
                lat.append((tt[j0 + j[0]] - s) * 1e3)
    lvl = []
    for s, _ in calls:
        m = pk[iv(s, s + 0.030)]
        lvl.append(20 * np.log10(max(float(m.max()) if len(m) else 0.0, 1e-6)))
    return dict(dur=dur, calls=len(calls), wake=sum(wake), sound=sum(sound), fw=fw_n, fa_hops=int((a & ~near).sum()), hops=len(a),
                awake_hops=int(a.sum()), awake_sq_hops=int((a & sqf).sum()), sq_hops=int(sqf.sum()), rms_awake=float(rms[a].sum()), lat=lat, lvl=lvl)


BRIDGE_A_PER_UNIT = 0.327   # A per unit duty fraction (3.0 V into 8 ohm + FETs + 0.1 ohm; d17-cost.md, audibility-requirement.md l.7)
CCR_HALF = 128.0            # counts per unit duty (today: 32 counts = peak 0.251); L filtering ignored, as in d17-cost.md
BRIDGE_IDLE_MA = 0.45       # bridge keeps switching 50 % while squelched (D-hiz-idle.md s1); SPICE ripple, hiz_idle removes it


def current(awake_frac, sq_frac_all, rms_counts, hiz):
    """Reconciled 2026-10-08 (docs/proof/electrical/current-models-reconciled.md). Exciter = physical 0.327 A x mean|x| on awake hops
    (replaces 1.1 mA guess x relative drive). Squelched hops (mostly IDLE; the IDLE row has no bridge term) carry the bridge's 0.45 mA
    switching ripple unless hiz_idle."""
    m = rt.mcu(*[json.loads((REPO / "fw/out/dsp_icount.json").read_text())["B"]["MHz_qemu_corrected_V4ovh"]][0], "P112")
    aw = rt.awake(m[2], m[3])[1] - rt.B1["exciter (guess, PWR-04)"][1] + 1e3 * BRIDGE_A_PER_UNIT * rms_counts / CCR_HALF
    ripple = 0.0 if hiz else BRIDGE_IDLE_MA * sq_frac_all
    return awake_frac * aw + (1 - awake_frac) * rt.IDLE[1] + rt.LED[1] + ripple


def evaluate(n_clips):
    real, quiet = scenes(n_clips)
    out, ref_rms = {}, None
    for cfg, (knobs, loud) in CONFIGS.items():
        t_ = dict(dur=0, calls=0, wake=0, sound=0, fw=0, fa_hops=0, hops=0, awake_hops=0, awake_sq_hops=0, sq_hops=0, rms_awake=0.0, lat=[], lvl=[])
        for _, words, calls, t0 in real:
            s = score(run_cfg(knobs, loud, words), calls, t0)
            for k in t_:
                t_[k] = t_[k] + s[k]
        q_fw, q_dur, q_aw, q_h = 0, 0.0, 0, 0
        for _, words, _, t0 in quiet:
            s = score(run_cfg(knobs, loud, words), [], t0)
            q_fw += s["fw"]; q_dur += s["dur"]; q_aw += s["awake_hops"]; q_h += s["hops"]
        L, V = np.array(t_["lat"] or [np.nan]), np.array(t_["lvl"])
        rms_mean = t_["rms_awake"] / max(t_["awake_hops"], 1)
        if cfg == "today":
            ref_rms = rms_mean
        af = t_["awake_hops"] / t_["hops"]
        out[cfg] = {
            "wake_recall": round(t_["wake"] / t_["calls"], 4), "sound_recall": round(t_["sound"] / t_["calls"], 4),
            "false_wakes_per_min": round(t_["fw"] / t_["dur"] * 60, 2), "false_awake_frac": round(t_["fa_hops"] / t_["hops"], 4),
            "quiet_false_wakes_per_min": round(q_fw / q_dur * 60, 2), "quiet_awake_frac": round(q_aw / q_h, 4),
            "latency_p50_ms": round(float(np.nanmedian(L)), 2), "latency_p90_ms": round(float(np.nanpercentile(L, 90)), 2),
            "level_p50_dbfs": round(float(np.median(V)), 2), "level_max_dbfs": round(float(V.max()), 2),
            "awake_frac": round(af, 4), "_rms": rms_mean, "_sqa": t_["sq_hops"] / t_["hops"]}
    for cfg, o in out.items():
        o["mean_ma"] = round(current(o["awake_frac"], o.pop("_sqa"), o.pop("_rms"), cfg == "hiz_idle"), 4)
    n_calls = t_["calls"]
    return {"clips": len(real), "calls": n_calls, "audio_s": round(t_["dur"], 1), "configs": out}


def compare(new, base):
    bad = []
    for cfg, row in base["configs"].items():
        for k, tol in TOL.items():
            d = new["configs"][cfg][k] - row[k]
            if not abs(d) <= tol:
                bad.append(f"{cfg}.{k}: {row[k]} -> {new['configs'][cfg][k]} (tol {tol})")
    return bad


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--bless", action="store_true")
    ap.add_argument("--clips", type=int, default=54)
    ap.add_argument("--json", type=Path)
    a = ap.parse_args(argv)
    if not PM.exists():
        print("SKIP: ../ultrasonic-scratch/rec/extracts missing")
        return 0
    t = time.time()
    res = evaluate(a.clips)
    res["tolerances_abs"] = TOL
    res["runtime_s"] = round(time.time() - t, 1)
    print(json.dumps(res["configs"], indent=1))
    print(f"{res['clips']} clips, {res['calls']} calls, {res['runtime_s']} s")
    if a.json:
        a.json.write_text(json.dumps(res, indent=1) + "\n")
    if a.bless or not BASELINE.exists():
        BASELINE.write_text(json.dumps(res, indent=1) + "\n")
        print("baseline written", BASELINE)
        return 0
    base = json.loads(BASELINE.read_text())
    if base["clips"] != res["clips"]:
        print("FAIL: clip count differs from baseline")
        return 1
    bad = compare(res, base)
    print("FAIL" if bad else "PASS", *bad, sep="\n  ")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
