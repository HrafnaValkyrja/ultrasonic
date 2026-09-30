"""Run the Phase-1 signal-chain model on the synthetic corpus and write listenable results.

    python3 sim/dsp/run_phase1.py            # -> sim/out/dsp/*.wav, *.png, summary.json

Outputs (48 kHz WAVs so any player opens them):
  input_audible.wav     what you'd hear without the device (the scene's audible part only)
  b_transient.wav       algorithm B, transient-only (steady whines suppressed) - the default
  b_full.wav            algorithm B, everything above the mic's own hiss
  a_heterodyne.wav      algorithm A (fallback), 38 kHz LO
Plots: spectrograms in vs out, idle-detector timeline.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy import signal
from scipy.io import wavfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path[:0] = [str(HERE), str(REPO / "tools")]
import corpus  # noqa: E402
import pipeline as pl  # noqa: E402
import plotstyle  # noqa: E402

OUT = REPO / "sim/out/dsp"
OUT.mkdir(parents=True, exist_ok=True)


def to_wav(name, y, fs, peak_dbfs=None):
    """Resample to 48 kHz. Written at true level (0 dBFS = PWM full scale) unless peak_dbfs given."""
    y48 = signal.resample_poly(y, 48000, fs) if fs != 48000 else y
    if peak_dbfs is not None:
        y48 = y48 / (np.max(np.abs(y48)) + 1e-12) * 10 ** (peak_dbfs / 20)
    wavfile.write(OUT / name, 48000, (np.clip(y48, -1, 1) * 32767).astype(np.int16))


def main():
    t0 = time.time()
    parts, mix = corpus.scene()
    x400 = pl.microphone(mix, seed=3)
    x = pl.decimate_to_fs(x400)
    summary = {"input_dbfs": round(pl.dbfs(x), 1)}

    cfg_t = pl.BConfig()
    nb = pl.calibrate_noise(cfg_t)
    cfg_t.noise_band = nb
    y_bt, info = pl.algo_b(x, cfg_t)
    cfg_f = pl.BConfig(transient_only=False, noise_band=nb)
    y_bf, _ = pl.algo_b(x, cfg_f)
    y_a = pl.algo_a(x)
    active, frac = pl.idle_detector(x)
    summary.update(
        b_transient_dbfs=round(pl.dbfs(y_bt), 1), b_full_dbfs=round(pl.dbfs(y_bf), 1),
        a_dbfs=round(pl.dbfs(y_a), 1), idle_active_fraction=round(float(frac), 3),
        peak_b_transient=round(float(np.max(np.abs(y_bt))), 3),
    )

    # Per-source check: which sources get through transient mode? (energy in their time windows)
    fs_o = pl.FS_OUT
    tt = np.arange(len(y_bt)) / fs_o
    windows = {"hc_sr04": (0.2, 0.9), "bat_search": (0.3, 2.6), "bat_buzz": (2.6, 2.9),
               "red_bat": (3.2, 5.6), "keys": (4.8, 5.3), "whines_only": (5.6, 6.0)}
    summary["window_rms_dbfs_b_transient"] = {
        k: round(pl.dbfs(y_bt[(tt >= a) & (tt < b)]), 1) for k, (a, b) in windows.items()}
    summary["window_rms_dbfs_b_full"] = {
        k: round(pl.dbfs(y_bf[(tt >= a) & (tt < b)]), 1) for k, (a, b) in windows.items()}

    # Audible reference: what reaches the ear anyway (below 20 kHz), and silence-only test
    aud = signal.resample_poly(signal.sosfilt(signal.butter(6, 16e3, "lp", fs=corpus.FS, output="sos"), mix), 3, 25)
    to_wav("input_audible.wav", aud, 48000, peak_dbfs=-6)
    for name, y in [("b_transient.wav", y_bt), ("b_full.wav", y_bf), ("a_heterodyne.wav", y_a)]:
        to_wav(name, y, fs_o, peak_dbfs=-3)   # normalised for listening; true levels in summary

    # Silence test: mic self-noise only -> output must be ~silent
    xs = pl.decimate_to_fs(pl.microphone(np.zeros(len(mix) // 3), seed=11))
    ys, _ = pl.algo_b(xs, cfg_t)
    yf, _ = pl.algo_b(xs, cfg_f)
    _, frac_s = pl.idle_detector(xs)
    summary.update(silence_b_transient_dbfs=round(pl.dbfs(ys), 1), silence_b_full_dbfs=round(pl.dbfs(yf), 1),
                   silence_idle_active_fraction=round(float(frac_s), 3))

    # Quiet evening: how much of the time must the full chain be awake? (C9 power claim)
    qparts, qmix, events = corpus.quiet_scene()
    ev_sig = sum(np.abs(qparts[k][0]) for k in ("bats", "keys", "hc_sr04"))
    t400 = np.arange(len(ev_sig)) / corpus.FS
    onsets = [float(t400[(t400 >= a) & (t400 < b)][np.argmax(ev_sig[(t400 >= a) & (t400 < b)] > 0)])
              for a, b in events]
    xq = pl.decimate_to_fs(pl.microphone(qmix, seed=5))
    act_q, frac_q = pl.idle_detector(xq)
    tq = np.arange(len(act_q)) * 128 / pl.FS
    in_ev = np.zeros(len(act_q), bool)
    for a, b in events:
        in_ev |= (tq >= a) & (tq < b)
    # an event counts as caught if the detector is awake within 10 ms of its start (look-back buffer)
    caught = [bool(act_q[(tq >= o) & (tq < o + 0.010)].any()) for o in onsets]
    summary.update(quiet_event_fraction=round(float(in_ev.mean()), 3),
                   quiet_idle_active_fraction=round(float(frac_q), 3),
                   quiet_false_wake_fraction=round(float((act_q & ~in_ev).mean()), 3),
                   quiet_events_caught=caught)
    plot_quiet(tq, act_q, events)

    plot(x, y_bt, y_bf, y_a, active)
    summary["runtime_s"] = round(time.time() - t0, 1)
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


def plot_quiet(tq, act, events):
    plt = plotstyle.apply()
    fig, ax = plt.subplots(figsize=(10, 1.8))
    for a, b in events:
        ax.axvspan(a, b, color=plotstyle.SERIES[1], alpha=0.35, lw=0)
    ax.fill_between(tq, 0, act.astype(float) * 0.8, step="post", color=plotstyle.SERIES[2])
    ax.set_yticks([])
    ax.set_xlabel("time (s)")
    ax.set_title(f"Quiet evening: real events (orange) vs chain awake (green), awake {act.mean() * 100:.0f}% of the time")
    fig.savefig(OUT / "idle_quiet.png")


def plot(x, y_bt, y_bf, y_a, active):
    plt = plotstyle.apply()
    fig, axs = plt.subplots(5, 1, figsize=(10, 11), sharex=True,
                            gridspec_kw={"height_ratios": [3, 2, 2, 2, 0.6]})
    f, t, S = signal.spectrogram(x, pl.FS, nperseg=512, noverlap=384)
    axs[0].pcolormesh(t, f / 1e3, 10 * np.log10(S + 1e-16), vmin=-150, vmax=-70, cmap="magma", shading="auto")
    axs[0].set_ylabel("kHz")
    axs[0].set_title("IN: microphone at 200 kS/s (bats, katydid, whines, keys, rangefinder, speech)")
    for ax, y, ttl in [(axs[1], y_bt, "OUT B transient (default): steady whines removed"),
                       (axs[2], y_bf, "OUT B full: everything above mic hiss"),
                       (axs[3], y_a, "OUT A heterodyne (fallback)")]:
        f, t, S = signal.spectrogram(y, pl.FS_OUT, nperseg=256, noverlap=224)
        Sd = 10 * np.log10(S + 1e-16)
        vmax = np.percentile(Sd, 99.9)
        ax.pcolormesh(t, f / 1e3, Sd, vmin=vmax - 60, vmax=vmax, cmap="magma", shading="auto")
        ax.set_ylim(0, 6)
        ax.set_ylabel("kHz")
        ax.set_title(ttl)
    ta = np.arange(len(active)) * 128 / pl.FS
    axs[4].fill_between(ta, 0, active.astype(float), step="post", color=plotstyle.SERIES[2])
    axs[4].set_yticks([])
    axs[4].set_title(f"Idle detector: full chain awake {active.mean() * 100:.0f}% of this (busy) scene")
    axs[4].set_xlabel("time (s)")
    fig.savefig(OUT / "spectrograms.png")


if __name__ == "__main__":
    main()
