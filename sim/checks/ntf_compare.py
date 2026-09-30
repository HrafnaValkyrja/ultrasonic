# Compare noise-transfer functions (NTFs) for the 200 kHz / 201-level PWM (2-level "AD"
# bridge modulation): plain 2nd order, 2nd order with its zero pair moved up into the
# band, and 3rd order with one DC zero plus an in-band zero pair. Error-feedback
# quantizer with TPDF dither, then the coil's first-order low-pass.
# Output: noise power per band in dB relative to a full-scale sine.
import numpy as np
from scipy import signal

FS, LEVELS = 200e3, 201


def ntf_poly(dc_zeros, pair_hz=()):
    """NTF numerator in powers of z^-1: (1 - z^-1)^dc_zeros * prod(1 - 2cos(w) z^-1 + z^-2)."""
    p = np.array([1.0])
    for _ in range(dc_zeros):
        p = np.convolve(p, [1.0, -1.0])
    for f in pair_hz:
        w = 2 * np.pi * f / FS
        p = np.convolve(p, [1.0, -2 * np.cos(w), 1.0])
    return p


def band_noise(ntf, sig_dbfs=-30.0, f0=2500.0, dur=0.5, L=0.3e-3, R=8.0):
    h = ntf[1:]                        # y = v + e[n], v = x + sum(ntf[k]*e[n-k])  =>  Y = X + NTF*E
    n = int(FS * dur)
    x = 10 ** (sig_dbfs / 20) * np.sin(2 * np.pi * f0 * np.arange(n) / FS)
    step = 2.0 / (LEVELS - 1)
    e_hist = np.zeros(len(h))
    y = np.empty(n)
    rng = np.random.default_rng(1)
    for i in range(n):
        v = x[i] + np.dot(h, e_hist)
        d = (rng.random() - rng.random()) * step
        q = np.clip(np.round((v + d) / step) * step, -1, 1)
        e_hist = np.roll(e_hist, 1)
        e_hist[0] = q - v
        y[i] = q
    fc = R / (2 * np.pi * L)
    b, a = signal.bilinear([2 * np.pi * fc], [1, 2 * np.pi * fc], FS)
    err = signal.lfilter(b, a, y - x)
    f, P = signal.welch(err, FS, nperseg=8192)

    def band(lo, hi):
        m = (f >= lo) & (f < hi)
        return 10 * np.log10(np.sum(P[m]) * (f[1] - f[0]) / 0.5)

    return band(200, 8e3), band(8e3, 20e3), band(20e3, 40e3)


if __name__ == "__main__":
    cases = [
        ("2nd order, both zeros at DC", ntf_poly(2)),
        ("2nd order, zero pair at 11 kHz", ntf_poly(0, [11e3])),
        ("3rd order, DC + pair at 13 kHz", ntf_poly(1, [13e3])),
    ]
    for name, ntf in cases:
        r = band_noise(ntf)
        print(f"{name:34s} 0.2-8k {r[0]:6.1f} | 8-20k {r[1]:6.1f} | 20-40k {r[2]:6.1f}"
              "  (dB re FS, after coil)")
