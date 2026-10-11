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

    ab()


def ab():
    """Fuller (shipping B, 28 bands) vs lighter (slim, 16 bands): same 3 bat calls + 1 nature clip (4th Port Meadow clip),
    A+L defaults (loud off), each rendered to RMS -26 dBFS so loudness is matched. Plus a blind A/B sheet (seeded shuffle; key in its own file)."""
    import random
    AB = OUT / "ab"
    AB.mkdir(exist_ok=True)
    scs, _ = pm.scenes(4)
    ys = {}
    for i, (name, words, calls, t0) in enumerate(scs):
        lab = f"bat_call_{i+1}" if i < 3 else "nature"
        pair = {}
        for tag, cfg in (("fuller", "A"), ("lighter", "slim")):
            knobs, loud = pm.CONFIGS[cfg]
            y = decode(pm.run_cfg(knobs, loud, words), t0)
            pair[tag] = y * 10 ** (-26 / 20) / (np.sqrt(np.mean(y ** 2)) + 1e-12)
        g = min(1.0, 0.9 / max(np.abs(y).max() for y in pair.values()))
        for tag, y in pair.items():
            y = y * g
            ys[(lab, tag)] = (y * 32767).astype(np.int16)
            wavfile.write(AB / f"{lab}_{tag}.wav", 48000, ys[(lab, tag)])
            print(lab, tag, "RMS dBFS", round(20 * np.log10(np.sqrt(np.mean(y ** 2))), 1))
    rng = random.Random(20261011)
    labs = ["bat_call_1", "bat_call_2", "bat_call_3", "nature"] * 2
    rng.shuffle(labs)
    key = ["# Blind A/B answer key (do not open until you have filled in the sheet)", "", "| trial | first = | second = | clip |", "|---|---|---|---|"]
    sheet = ["# Blind A/B order sheet (Shokz test)", "",
             "Files `playlist/ab/blind_NN_1.wav` then `blind_NN_2.wav` (same clip, loudness-matched, one is fuller and one is lighter, order random).",
             "For each trial: which sounds more natural (1 / 2 / no difference)? Are they different at all (yes / no / guess)? Any confidence 1-3?", "",
             "| trial | more natural (1/2/same) | different? (y/n) | confidence 1-3 | notes |", "|---|---|---|---|---|"]
    for n, lab in enumerate(labs, 1):
        order = ["fuller", "lighter"]
        rng.shuffle(order)
        for k, tag in enumerate(order, 1):
            wavfile.write(AB / f"blind_{n:02d}_{k}.wav", 48000, ys[(lab, tag)])
        key.append(f"| {n:02d} | {order[0]} | {order[1]} | {lab} |")
        sheet.append(f"| {n:02d} | | | | |")
    (OUT.parent / "ab_blind_sheet.md").write_text("\n".join(sheet) + "\n")
    (OUT.parent / "ab_blind_key.md").write_text("\n".join(key) + "\n")


main()
