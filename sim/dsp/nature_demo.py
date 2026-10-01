"""Real nature recordings through the firmware's translation: what you'd hear with and without the device.

    python3 sim/dsp/nature_demo.py      # -> sim/out/nature/{1_audible_only,2_translated_only,3_combined}.wav + .png

Input: Port Meadow, Oxford (night meadow with bats), AudioMoth at 192 kS/s, Zenodo 22079773, CC-BY-4.0,
downloaded 2026-09-30. Four separate bat passes, joined with short gaps.
Chain: the recording stands in for the mic signal (resampled 192 -> 200 kS/s), then algorithm B in its
default transient mode (sim/dsp/pipeline.py, 20-85 kHz in 28 log bands -> 1.5-4 kHz).
Assumptions (true calibration is unknown):
- each clip is scaled so its loudest 10 ms ultrasonic window equals a 75 dB SPL bat at the mic;
- the audible ambience keeps its recorded ratio to the bats;
- 'combined' = the audible scene + the device output at its fixed volume (peaks <= -12 dBFS ceiling).
Bone-conduction coloration and the exciter's response are NOT modelled.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy import signal
from scipy.io import wavfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path[:0] = [str(HERE), str(REPO / "tools")]
import pipeline as pl  # noqa: E402

REC = REPO.parent / "ultrasonic-scratch/rec/extracts"
CLIPS = ["20251021_172626/receiver_3.wav", "20251021_174242/receiver_4.wav",
         "20251021_175144/receiver_3.wav", "20251021_174003/receiver_1.wav"]
OUT = REPO / "sim/out/nature"
OUT.mkdir(parents=True, exist_ok=True)
GAP_S = 0.5
BAT_SPL = 75.0


def mic_dbfs_for_spl(spl, f=40e3):
    """Level (dBFS rms) our mic model produces for a pure tone of `spl` dB SPL at f, noise-free."""
    t = np.arange(int(0.05 * pl.FS_IN)) / pl.FS_IN
    p = np.sqrt(2) * pl.P_REF * 10 ** (spl / 20) * np.sin(2 * np.pi * f * t)
    x = pl.decimate_to_fs(pl.microphone(p, noise_scale=0.0))
    return 20 * np.log10(np.std(x[200:-200]))


def main():
    target = mic_dbfs_for_spl(BAT_SPL)
    sos_u = signal.butter(6, [20e3, 90e3], "bp", fs=192000, output="sos")
    sos_a = signal.butter(8, 18e3, "lp", fs=192000, output="sos")
    xs, auds = [], []
    for c in CLIPS:
        fs, y = wavfile.read(REC / c)
        y = y.astype(float) / 32768.0
        if y.ndim > 1:
            y = y[:, 0]
        u = signal.sosfilt(sos_u, y)
        win = int(0.01 * fs)
        peak_rms = np.sqrt(np.max(np.convolve(u ** 2, np.ones(win) / win, "valid")))
        g = 10 ** (target / 20) / peak_rms
        xs.append(signal.resample_poly(y * g, 25, 24))                       # mic stand-in at 200 kS/s
        auds.append(signal.resample_poly(signal.sosfilt(sos_a, y * g), 1, 4))   # audible part at 48 kS/s
        xs.append(np.zeros(int(GAP_S * pl.FS)))
        auds.append(np.zeros(int(GAP_S * 48000)))
    x = np.concatenate(xs)
    aud = np.concatenate(auds)

    y, _ = pl.algo_b(x, pl.BConfig())                    # default: transient mode
    y48 = signal.resample_poly(y, 96, 25)                 # 12.5 -> 48 kS/s
    n = min(len(aud), len(y48))
    aud, y48 = aud[:n], y48[:n]

    # the audible scene keeps its level relative to the bats; lift the whole scene into a listenable
    # range with ONE gain so it sits about -30 dBFS rms (quiet night ambience), same gain in 'combined'
    k = 10 ** (-30 / 20) / (np.std(aud) + 1e-12)
    aud_l = aud * k
    comb = aud_l + y48
    for name, sig in (("1_audible_only", aud_l), ("2_translated_only", y48), ("3_combined", comb)):
        wavfile.write(OUT / f"{name}.wav", 48000, (np.clip(sig, -1, 1) * 32767).astype(np.int16))
    print(f"scene {n / 48000:.1f} s; audible rms {20 * np.log10(np.std(aud_l)):.1f} dBFS, "
          f"translated peak {20 * np.log10(np.max(np.abs(y48)) + 1e-12):.1f} dBFS, "
          f"combined peak {20 * np.log10(np.max(np.abs(comb)) + 1e-12):.1f} dBFS")
    plot(x, aud_l, y48, comb)


def plot(x, aud, y48, comb):
    import plotstyle
    plt = plotstyle.apply()
    fig, axs = plt.subplots(4, 1, figsize=(11, 10), sharex=True)
    rows = [(x, pl.FS, 96, "IN: the recording, full band (bats are the bright marks above 20 kHz)"),
            (aud, 48000, 20, "1  What you hear without the device (audible band only)"),
            (y48, 48000, 6, "2  What the device adds: bats translated to 1.5-4 kHz"),
            (comb, 48000, 20, "3  What you'd actually hear: both together")]
    for ax, (s, fs, fmax, title) in zip(axs, rows):
        f, t, S = signal.spectrogram(s, fs, nperseg=1024 if fs > 100e3 else 512, noverlap=None)
        ax.pcolormesh(t, f / 1e3, 10 * np.log10(S + 1e-14), shading="auto", cmap="magma",
                      vmin=np.percentile(10 * np.log10(S + 1e-14), 20), vmax=np.percentile(10 * np.log10(S + 1e-14), 99.7))
        ax.set_ylim(0, fmax)
        ax.set_ylabel("kHz")
        ax.set_title(title, loc="left")
    axs[-1].set_xlabel("seconds (four separate bat passes, Port Meadow, Oxford)")
    fig.savefig(OUT / "spectrograms.png")


if __name__ == "__main__":
    main()
