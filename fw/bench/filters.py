#!/usr/bin/env python3
"""Do the tap counts costed in kernels.h do their job? (V4 assumption check, not a sound check.)

- x16 interpolator: prototype 16*TPP taps at 200 kHz; passband 0-4.25 kHz; images of the
  12.5 kS/s output start at 12.5-4.25 = 8.25 kHz (audible) -> stopband 8.25-100 kHz.
- algorithm A decimator: stage 1 /4 (A_N1 taps, 200k->50k) must kill what folds onto 0-4.25 kHz
  (50k+-4.25k, 100k-4.25k..100k); stage 2 /4 (A_N2 taps, 50k->12.5k): stopband 8.25-25 kHz.
Prints worst stopband attenuation (dB) for each candidate length (least-squares FIR design).
"""
import numpy as np
from scipy import signal


def att(h, fs, stop):
    w, H = signal.freqz(h, worN=1 << 15, fs=fs)
    g = 20 * np.log10(np.abs(H) / np.abs(H[0]) + 1e-12)
    m = np.zeros_like(w, bool)
    for a, b in stop:
        m |= (w >= a) & (w <= b)
    pb = (w <= 4250)
    return -g[m].max(), np.ptp(g[pb])


def design(n, fs, stop):
    bands, des = [0, 4250], [1, 1]
    for a, b in stop:
        bands += [a, min(b, fs / 2)]
        des += [0, 0]
    h = signal.firls(n - 1 if n % 2 == 0 else n, bands, des, fs=fs)   # odd linear-phase; even n = odd + one zero tap
    return np.append(h, 0.0) if n % 2 == 0 else h


if __name__ == "__main__":
    for tpp in (4, 6, 8, 12):
        h = design(16 * tpp, 200e3, [(8250, 100e3)])
        a, r = att(h, 200e3, [(8250, 100e3)])
        print(f"interp x16 TPP={tpp:2d} ({16*tpp} taps): image rejection {a:5.1f} dB, passband ripple {r:.2f} dB")
    s1 = [(45750, 54250), (95750, 100e3)]
    for n in (8, 12, 16):
        h = design(n, 200e3, s1)
        a, r = att(h, 200e3, s1)
        print(f"A stage1 /4 N1={n:2d}: alias rejection {a:5.1f} dB, ripple {r:.2f} dB")
    for n in (24, 32, 40, 48):
        h = design(n, 50e3, [(8250, 25e3)])
        a, r = att(h, 50e3, [(8250, 25e3)])
        print(f"A stage2 /4 N2={n:2d}: alias rejection {a:5.1f} dB, ripple {r:.2f} dB")
