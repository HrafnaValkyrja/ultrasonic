#!/usr/bin/env python3
"""I-021 impedance sweep, series-resistor method. Wiring: out -> Rs -> exciter -> GND.
Input ch1 = node before Rs (source), ch2 = across exciter. Z = Rs*V2/(V1-V2).
Log-sine 200 Hz-8 kHz. Output: f0, Q (from the half-height width of Re{Z}), |Z| CSV.
  imp_sweep.py --load 1.5N --rs 10            # live
  imp_sweep.py --dry-run                        # stimulus WAV, CSV template, synthetic self-check
  imp_sweep.py --analyse rec.wav --rs 10        # recorded 2-ch WAV (same sweep)"""
import argparse, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rigcommon import *

F1, F2, DUR = 200.0, 8000.0, 6.0

def transfer(ref, rec, fs):
    """Deconvolve-free spectral ratio rec/ref for same-length signals."""
    n = len(ref)
    return np.fft.rfftfreq(n, 1 / fs), np.fft.rfft(rec[:n]) / (np.fft.rfft(ref) + 1e-30)

def impedance(v1, v2, rs, fs, f1=F1, f2=F2):
    f = np.fft.rfftfreq(len(v1), 1 / fs)
    V1, V2 = np.fft.rfft(v1), np.fft.rfft(v2)
    Z = rs * V2 / (V1 - V2 + 1e-30)
    m = (f >= f1) & (f <= f2)
    return f[m], Z[m]

def smooth(a, n=15):
    return np.convolve(a, np.ones(n) / n, 'same')

def f0_q(f, z):
    """f0 = |Z| peak. Q = f0/FWHM of the motional resistance Re{Z}-Re (a Lorentzian at resonance),
    Re = min Re{Z} below the peak. Returns f0, Q, Zmax, Re."""
    a = smooth(np.abs(z)); i = int(np.argmax(a)); r = smooth(z.real)
    re = float(np.min(r[:i])) if i > 5 else float(np.min(r))
    m = r - re; half = m[i] / 2
    lo = i
    while lo > 0 and m[lo] > half: lo -= 1
    hi = i
    while hi < len(m) - 1 and m[hi] > half: hi += 1
    return float(f[i]), float(f[i] / (f[hi] - f[lo])), float(a[i]), re

def synth(rs, fs=FS, f0=1200., Re=8., Q=4., Bl_term=12.):
    """Simulated exciter: Re + parallel-RLC motional branch. Returns (v1, v2) for the sweep."""
    x = log_sweep(F1, F2, DUR, fs)
    f = np.fft.rfftfreq(len(x), 1 / fs); w = 2 * np.pi * np.maximum(f, 1e-3)
    w0 = 2 * np.pi * f0
    Zm = Bl_term / (1 + 1j * Q * (w / w0 - w0 / w))   # motional impedance
    Z = Re + Zm
    X = np.fft.rfft(x); V2 = X * Z / (Z + rs)
    return x, np.fft.irfft(V2, len(x))

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--rs', type=float, default=10.0, help='series resistor, ohm')
    ap.add_argument('--load', default='light', help='pad load label (light/medium/1.5N)')
    ap.add_argument('--out', default='bench/rig/out'); ap.add_argument('--device', default=None)
    ap.add_argument('--dry-run', action='store_true'); ap.add_argument('--analyse')
    a = ap.parse_args()
    x = log_sweep(F1, F2, DUR)
    stim = os.path.join(a.out, 'imp_sweep_stim.wav')
    csvp = os.path.join(a.out, 'imp_sweep_results.csv')
    hdr = ['load', 'rs_ohm', 'f0_hz', 'Q', 'zmax_ohm', 're_ohm']
    if a.dry_run:
        write_wav(stim, x); write_csv(csvp, hdr)
        v1, v2 = synth(a.rs); f, z = impedance(v1, v2, a.rs, FS)
        print('dry-run: wrote', stim, csvp, '| synthetic check f0=%.0f Q=%.2f (truth 1200, ~4)' % f0_q(f, z)[:2])
        return
    if a.analyse:
        r, fs = read_wav(a.analyse); v1, v2 = r[:, 0], r[:, 1]
    else:
        pad = np.zeros(int(0.3 * FS)); out = np.concatenate([x, pad])
        r = play_rec(out, FS, 2, a.device); v1, v2 = r[:len(x), 0], r[:len(x), 1]
        write_wav(os.path.join(a.out, 'imp_%s_rec.wav' % a.load), r)
    f, z = impedance(v1, v2, a.rs, FS)
    f0, q, zmax, re = f0_q(f, z)
    print('load=%s f0=%.0f Hz Q=%.2f Zmax=%.1f Re=%.1f' % (a.load, f0, q, zmax, re))
    new = not os.path.exists(csvp)
    with open(csvp, 'a') as fh:
        if new: fh.write(','.join(hdr) + '\n')
        fh.write('%s,%g,%.1f,%.3f,%.2f,%.2f\n' % (a.load, a.rs, f0, q, zmax, re))
    print('Kill rule I-021: Q<2 or f0 drift >20%% across loads ->', 'Q FAIL' if q < 2 else 'Q ok')

if __name__ == '__main__':
    main()
