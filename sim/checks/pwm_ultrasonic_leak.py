"""How much of the PWM noise shaper's output lands in the mic's 20-85 kHz band? (audit MP-01)

    python3 sim/checks/pwm_ultrasonic_leak.py    # table + sim/out/pwm_leak/leak.png

Spec D6 claimed switching leakage "can only land at 0 Hz" because the PWM clock is coherent with
the mic clock. That holds for the carrier and its harmonics. It does not hold for the shaper's
quantisation noise, which is broadband and spread up to fs_pwm/2 - straight through the band the
mic listens to. If any of it couples back (supply, ground, transducer vibration), the device hears
itself. This compares ways of moving that noise out of 20-85 kHz.

Model: error-feedback shaper, NTF zeros at DC plus a pair at 13 kHz (2nd order: DC pair), uniform
quantiser with ARR+1 levels, small dither, quiet 2.5 kHz tone at -40 dBFS. Reported in dB relative
to a full-scale sine, for the bridge VOLTAGE and for the transducer CURRENT (8 ohm + 0.3 mH).
"""
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
import plotstyle  # noqa: E402

OUT = REPO / "sim/out/pwm_leak"
OUT.mkdir(parents=True, exist_ok=True)
R, L = 8.0, 0.3e-3


def shaped(fs, levels, order, n=1 << 16, f0=2500.0, dbfs=-40.0, seed=0):
    t = np.arange(n) / fs
    x = 10 ** (dbfs / 20) * np.sin(2 * np.pi * f0 * t)
    if order == 3:
        w = 2 * np.pi * 13e3 / fs
        ntf = np.convolve([1, -1], [1, -2 * np.cos(w), 1])
    else:
        ntf = np.array([1, -2, 1])
    h = ntf[1:]                     # y = x + NTF*e requires v = x + sum(c_k e[n-k]); see ntf_compare.py
    q_step = 2.0 / (levels - 1)
    e = np.zeros(len(h))
    y = np.empty(n)
    rng = np.random.default_rng(seed)
    for i in range(n):
        v = x[i] + h @ e
        q = np.clip(np.round((v + rng.uniform(-0.5, 0.5) * q_step) / q_step) * q_step, -1, 1)
        y[i] = q
        e = np.r_[q - v, e[:-1]]
    win = np.hanning(n)
    Y = np.fft.rfft(y * win)
    f = np.fft.rfftfreq(n, 1 / fs)
    P = np.abs(Y) ** 2 / np.sum(win ** 2) * 2 / n        # power per bin, full-scale sine = 0.5
    return f, P


def band_db(f, P, a, b, weight=None):
    m = (f >= a) & (f < b)
    p = P[m] * (weight[m] if weight is not None else 1)
    return 10 * np.log10(p.sum() / 0.5 + 1e-30)


OPTIONS = [  # label, PWM update rate, levels, shaper order, timer clock, gate-drive current mA
    ("A  today: 200 kHz, 201 lvl, 3rd", 200e3, 201, 3, "80 MHz", 0.28),
    ("B  200 kHz, 201 lvl, 2nd", 200e3, 201, 2, "80 MHz", 0.28),
    ("C  400 kHz, 201 lvl, 3rd", 400e3, 201, 3, "160 MHz", 0.56),
    ("D  400 kHz, 101 lvl, 3rd", 400e3, 101, 3, "80 MHz", 0.56),
    ("E  800 kHz, 101 lvl, 3rd", 800e3, 101, 3, "160 MHz", 1.12),
    ("F  800 kHz, 51 lvl, 3rd", 800e3, 51, 3, "80 MHz", 1.12),
]


def main():
    plt = plotstyle.apply()
    fig, ax = plt.subplots(figsize=(9, 4.6))
    print(f"{'option':34s} {'audio 3-16k':>11s} {'mic band V':>11s} {'mic band I':>11s}  clock   gate mA")
    rows = []
    for (lab, fs, lv, od, clk, gate), c in zip(OPTIONS, plotstyle.SERIES):
        f, P = shaped(fs, lv, od)
        zi = 1 / np.abs(R + 2j * np.pi * f * L) * R            # current, normalised to DC
        wI = zi ** 2
        a = band_db(f, P, 3e3, 16e3)
        mv = band_db(f, P, 20e3, 85e3)
        mi = band_db(f, P, 20e3, 85e3, wI)
        rows.append((lab, a, mv, mi, clk, gate))
        print(f"{lab:34s} {a:11.1f} {mv:11.1f} {mi:11.1f}  {clk:7s} {gate:.2f}")
        k = max(1, len(f) // 2000)
        ps = 10 * np.log10(np.convolve(P, np.ones(64) / 64, "same") / 0.5 * len(f) / (fs / 2) * 1e3 + 1e-30)
        ax.plot(f[::k] / 1e3, ps[::k], color=c, lw=1.1, label=lab)
    ax.axvspan(20, 85, color=plotstyle.SERIES[7], alpha=0.12, lw=0)
    ax.text(21, -20, "mic processing band", color=plotstyle.SERIES[7], fontsize=8)
    ax.set_xlim(0, 200)
    ax.set_ylim(-140, -10)
    ax.set_xlabel("kHz")
    ax.set_ylabel("noise density (dB re FS sine per kHz)")
    ax.set_title("Where the PWM noise shaper puts its noise: options vs the mic's 20-85 kHz band")
    ax.legend(loc="lower right", fontsize=7.5)
    fig.savefig(OUT / "leak.png")
    return rows


if __name__ == "__main__":
    main()
