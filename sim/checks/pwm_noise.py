# Quick sanity model: PWM treated as a uniformly-sampled quantizer (ignores PWM's own
# sampling nonlinearity), optional error-feedback noise shaping, then the coil's
# first-order R/L low-pass. Reports noise in bands relative to a full-scale sine.
import numpy as np
from scipy import signal

def run(fs, levels, order, sig_dbfs=-20.0, f0=2500.0, dur=0.5, dither=True, L=0.3e-3, R=8.0):
    n = int(fs*dur); t = np.arange(n)/fs
    x = 10**(sig_dbfs/20)*np.sin(2*np.pi*f0*t)            # full scale = +/-1
    step = 2.0/(levels-1)
    y = np.empty(n); e1 = e2 = 0.0
    rng = np.random.default_rng(0)
    for i in range(n):
        if order == 0: v = x[i]
        elif order == 1: v = x[i] - e1
        else: v = x[i] - 2*e1 + e2                         # NTF = (1 - z^-1)^2
        d = (rng.random()-rng.random())*step if dither else 0.0   # TPDF dither
        q = np.clip(np.round((v+d)/step)*step, -1, 1)
        e2, e1 = e1, q - v
        y[i] = q
    err = y - x
    # coil low-pass acting on current (first order, corner R/(2*pi*L))
    fc = R/(2*np.pi*L)
    b, a = signal.bilinear([2*np.pi*fc], [1, 2*np.pi*fc], fs)
    err_f = signal.lfilter(b, a, err)
    f, P = signal.welch(err, fs, nperseg=8192)
    f, Pf = signal.welch(err_f, fs, nperseg=8192)
    fs_power = 0.5                                          # full-scale sine power
    def band(Pxx, lo, hi):
        m = (f >= lo) & (f < hi); return 10*np.log10(np.sum(Pxx[m])*(f[1]-f[0])/fs_power)
    return {k: (band(P, *v), band(Pf, *v)) for k, v in
            {"0.2-8k": (200, 8e3), "8-20k": (8e3, 20e3), "20-40k": (20e3, 40e3)}.items()}, fc

cfgs = [("312.5 kHz, 256 lvl, no shaping", 312.5e3, 256, 0),
        ("312.5 kHz, 256 lvl, 2nd-order", 312.5e3, 256, 2),
        ("200 kHz, 401 lvl (BD), 2nd-order", 200e3, 401, 2)]
for name, fs, lv, o in cfgs:
    r, fc = run(fs, lv, o)
    print(f"{name:34s} " + "  ".join(f"{k}: {v[0]:6.1f} / {v[1]:6.1f}" for k, v in r.items()))
print(f"(dB re full-scale sine; 'raw / after coil LPF', coil corner {fc/1e3:.1f} kHz)")
