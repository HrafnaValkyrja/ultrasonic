#!/usr/bin/env python3
"""Makes docs/bench/shokz/playlist/*.wav for the Shokz tragus test (A-SHOKZ-BENCH).
Run fenced:  systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 python3 docs/bench/shokz/make_playlist.py
Needs the Port Meadow extracts (../ultrasonic-scratch/rec/extracts). Same call, same firmware, three settings:
normal (A, loud off), loud (+12 dB), loud+shape (+12 dB, flat-top). Relative levels between those three are kept;
each call's 'normal' is set to RMS -26 dBFS, or lower if the loud copy would clip (then the three keep their relative levels) so calls compare with each other. Output = firmware drive
(CCR counts around the squelch centre), low-passed 20 kHz, 48 kS/s. Model output, not a measured exciter response."""
import sys, shutil
from pathlib import Path
import numpy as np
from scipy import signal
from scipy.io import wavfile
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "sim/perf"))
import port_meadow as pm  # noqa: E402

OUT = Path(__file__).resolve().parent / "playlist"
REPO = pm.REPO
CFG = [("1_normal", "A", ), ("2_loud", "A+loud12"), ("3_loud_shape", "A+loud12+shape")]
CLIPS = 3
HOP_PER = None


def decode(r, t0):
    ccr = r["ccr"].astype(float)
    centre = np.bincount(r["ccr"]).argmax()
    x = ccr - centre
    per = len(ccr) / len(r["mode"])
    fs = per / pm.HOP_S
    x = x[int(t0 * fs):]
    sos = signal.butter(6, 20000, "lp", fs=fs, output="sos")
    x = signal.sosfilt(sos, x)
    return signal.resample(x, int(len(x) * 48000 / fs))


def main():
    OUT.mkdir(exist_ok=True)
    scs, _ = pm.scenes(CLIPS)
    for i, (name, words, calls, t0) in enumerate(scs):
        ys = {}
        for tag, cfg in CFG:
            knobs, loud = pm.CONFIGS[cfg]
            ys[tag] = decode(pm.run_cfg(knobs, loud, words), t0)
        g = 10 ** (-26 / 20) / (np.sqrt(np.mean(ys["1_normal"] ** 2)) + 1e-12)
        g = min(g, 0.9 / max(np.abs(y).max() for y in ys.values()))   # keep all three un-clipped, relative levels intact
        print(name, "normal RMS dBFS", round(20 * np.log10(np.sqrt(np.mean((ys["1_normal"] * g) ** 2))), 1))
        for tag, y in ys.items():
            y = y * g
            wavfile.write(OUT / f"bat_call_{i+1}_{tag[2:]}.wav", 48000, (y * 32767).astype(np.int16))
    for src, dst in [("2_translated_only", "nature_translated_only"), ("1_audible_only", "nature_audible_only"), ("3_combined", "nature_both")]:
        shutil.copy(REPO / f"sim/out/nature/{src}.wav", OUT / f"{dst}.wav")


main()
