"""Idle-listening wake detector: old (IIR band filters) vs rev 2 (FFT snapshots), audit dsp-1/2/8.

    python3 sim/checks/idle_detector.py     # table; sim/out/idle/summary.json

Synthetic scenes (built by the same author as the detector, so treat as sanity checks only):
  quiet evening WITH steady whines, WITHOUT whines (a room with no electronics), speech only.
Real recordings (independent ground truth): Port Meadow, Oxford, AudioMoth at 192 kS/s,
Zenodo 22079773 (CC-BY-4.0, downloaded 2026-09-30), 54 flypasts x 5 receivers, each with
machine-annotated bat calls (BatDetect2-style events_N.csv). Needs ../ultrasonic-scratch/rec.
"""
import glob
import json
import sys
from pathlib import Path

import numpy as np
from scipy import signal
from scipy.io import wavfile

REPO = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(REPO / "sim/dsp"), str(REPO / "tools")]
import corpus  # noqa: E402
import pipeline as pl  # noqa: E402

REC = REPO.parent / "ultrasonic-scratch/rec/extracts"
OUT = REPO / "sim/out/idle"
OUT.mkdir(parents=True, exist_ok=True)
CATCH_S = 0.010          # a call counts as caught if the chain is awake within 10 ms of its start


def old(x):
    a, frac = pl.idle_detector(x)
    return a, frac, 128 / pl.FS


def new(x):
    return pl.idle_detector_fft(x)


def awake_at(active, hop_s, t0, t1):
    i0, i1 = int(t0 / hop_s), int(np.ceil(t1 / hop_s)) + 1
    return bool(active[i0:i1].any())


def synthetic():
    res = {}
    for name, whines, keep in (("quiet + whines", True, None), ("quiet, no whines", False, None),
                               ("speech only", False, {"speech_band"})):
        parts, mix, events = corpus.quiet_scene(whines=whines)
        if keep:
            mix = sum(sig / np.sqrt(np.mean(sig[np.abs(sig) > 1e-9] ** 2)) * corpus.db_spl_to_pa_rms(db)
                      for k, (sig, db) in parts.items() if k in keep)
            events = []
        x = pl.decimate_to_fs(pl.microphone(mix, seed=5))
        ev_sig = sum(np.abs(parts[k][0]) for k in ("bats", "keys", "hc_sr04") if k in parts)
        t400 = np.arange(len(mix)) / corpus.FS
        onsets = []
        for a, b in events:
            m = (t400 >= a) & (t400 < b)
            onsets.append(float(t400[m][np.argmax(ev_sig[m] > 0)]))
        row = {}
        for lab, det in (("old", old), ("new", new)):
            act, frac, hop_s = det(x)
            caught = [awake_at(act, hop_s, o, o + CATCH_S) for o in onsets]
            row[lab] = {"awake": round(float(frac), 3), "caught": f"{sum(caught)}/{len(caught)}"}
        res[name] = row
    return res


def real():
    files = sorted(glob.glob(str(REC / "*/receiver_*.wav")))
    stats = {"old": [], "new": []}
    lat = {"old": [], "new": []}
    n_calls = 0
    for f in files:
        ev = Path(f).parent / f"events_{Path(f).stem.split('_')[1]}.csv"
        if not ev.exists():
            continue
        calls = []
        for line in ev.read_text().splitlines()[1:]:
            c = line.split(",")
            if len(c) >= 4 and float(c[1]) >= 0.5:          # BatDetect2 detection probability
                calls.append((float(c[2]), float(c[3])))
        if not calls:
            continue
        fs, y = wavfile.read(f)
        y = y.astype(float) / 32768.0
        if y.ndim > 1:
            y = y[:, 0]
        x = signal.resample_poly(y, 25, 24)                   # 192 -> 200 kS/s
        n_calls += len(calls)
        first = min(c[0] for c in calls)
        for lab, det in (("old", old), ("new", new)):
            act, frac, hop_s = det(x)
            stats[lab] += [awake_at(act, hop_s, s, s + CATCH_S) for s, _ in calls]
            on = np.nonzero(act)[0]
            lat[lab].append((on[0] * hop_s - first) if len(on) else np.nan)
    out = {"files": len(lat["new"]), "calls": n_calls}
    for lab in ("old", "new"):
        L = np.array(lat[lab])
        out[lab] = {"calls caught within 10 ms": round(float(np.mean(stats[lab])), 3),
                    "files never woken": int(np.isnan(L).sum()),
                    "median wake minus first call (ms)": round(float(np.nanmedian(L)) * 1e3, 1)}
    return out


def main():
    res = {"synthetic": synthetic()}
    print("SYNTHETIC (awake fraction; events caught within 10 ms)")
    for k, v in res["synthetic"].items():
        print(f"  {k:18s} old {v['old']['awake']:5.1%} {v['old']['caught']:>4s} | new {v['new']['awake']:5.1%} {v['new']['caught']:>4s}")
    if REC.exists():
        res["real"] = real()
        r = res["real"]
        print(f"REAL Port Meadow: {r['files']} recordings, {r['calls']} annotated calls")
        for lab in ("old", "new"):
            print(f"  {lab}: {r[lab]}")
    (OUT / "summary.json").write_text(json.dumps(res, indent=2))
    print("cost estimate: old ~8 biquads x 200 kS/s = ~10-13 Mcycle/s; new ~200 FFT/s x 17 kcycle = ~3.4 Mcycle/s")


if __name__ == "__main__":
    main()
