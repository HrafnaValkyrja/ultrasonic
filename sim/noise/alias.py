"""Where does an interference line at frequency f end up after the mic's PDM sampling and the ADF1 decimation?

Chain (docs/research/A3-u575-plan.md section 1.2, spec D14; clocks from one 80.009 MHz HCLK):
  PDM sampling fs_pdm = HCLK/20 = 4.0004 MHz  ->  CIC5 (sinc^5) decimate by 5 -> 800 kS/s
  -> RSFLT (reshape filter) decimate by 4 -> 200.02 kS/s = fs_out.  PWM carrier = fs_out.
A line coherent with fs_out (an integer multiple) lands at exactly 0 Hz and the band-floor high-pass removes it.
Anything else lands at fold(f) in 0..100 kHz with the attenuation of CIC5 at f plus RSFLT at the 800 kS/s alias.

The RSFLT response is NOT published (risk R18, sub-audio-in open issue 6); the model below is the A3 working
assumption: 0 dB to 88.8 kHz, -70 dB from 111.2 kHz, linear in dB between. UNVERIFIED until S1 sweeps it.

    python3 sim/noise/alias.py            # self-test + table for the declared aggressor frequencies
"""
from __future__ import annotations

import math

HCLK = 80.009e6
FS_PDM = HCLK / 20.0
FS_CIC = FS_PDM / 5.0
FS_OUT = FS_CIC / 4.0
RSFLT_PASS, RSFLT_STOP, RSFLT_STOP_DB = 88.8e3, 111.2e3, -70.0  # A3 s1.2 working numbers, unverified


def fold(f: float, fs: float) -> float:
    """Alias of f into 0..fs/2."""
    return abs((f + fs / 2) % fs - fs / 2)


def cic5_db(f: float, fs_in: float = FS_PDM, r: int = 5, order: int = 5) -> float:
    """|H| of an order-5 CIC with decimation r at input rate fs_in, evaluated at the (unaliased) input frequency f."""
    x = math.pi * f / fs_in
    s = math.sin(x)
    if abs(s) < 1e-12:
        return 0.0 if abs(math.sin(r * x)) < 1e-12 and abs(math.cos(x) - 1) < 1e-9 else -400.0
    h = abs(math.sin(r * x) / (r * s)) ** order
    return 20 * math.log10(max(h, 1e-20))


def rsflt_db(f: float) -> float:
    """Assumed RSFLT magnitude at f (800 kS/s domain, 0..400 kHz)."""
    if f <= RSFLT_PASS:
        return 0.0
    if f >= RSFLT_STOP:
        return RSFLT_STOP_DB
    return RSFLT_STOP_DB * (f - RSFLT_PASS) / (RSFLT_STOP - RSFLT_PASS)


def chain(f: float, fs_out: float = FS_OUT, tol_hz: float = 1.0):
    """(f_out_hz, attenuation_db <= 0, folds_to_dc) for an interference line at f_hz entering the PDM path."""
    f1 = fold(f, FS_PDM)           # mic modulator samples at fs_pdm
    f2 = fold(f1, FS_CIC)          # CIC5 decimation by 5 (att evaluated at the unaliased f)
    fo = fold(f2, fs_out)          # RSFLT decimation by 4
    att = cic5_db(f) + rsflt_db(f2)
    return fo, att, fo < tol_hz or fs_out - fo < tol_hz


def window_scan(f0: float, tol: float, kmax: int, band=(20e3, 96e3), n: int = 4001, att_min_db: float = -40.0):
    """For harmonic k of an asynchronous source at f0 (+-tol fractional): the fraction of its frequency range that aliases
    into `band` with chain attenuation better than att_min_db, and the weakest attenuation seen there.
    Rows: (k, f_lo, f_hi, frac_unprotected, best_att_db). The unprotected windows are n*fs_pdm +- (20..96 kHz): sinc^5 has
    no null there (it nulls at multiples of 800 kHz that are not multiples of fs_pdm)."""
    out = []
    for k in range(1, kmax + 1):
        lo, hi = k * f0 * (1 - tol), k * f0 * (1 + tol)
        fs = [lo + (hi - lo) * i / (n - 1) for i in range(n)] if tol > 0 else [lo]
        hits = [c[1] for c in (chain(f) for f in fs) if band[0] <= c[0] <= band[1] and c[1] >= att_min_db]
        out.append((k, lo, hi, len(hits) / len(fs), max(hits) if hits else None))
    return out


def fs_pdm_scan(f_sw: float = 3.0e6, kmax: int = 24, dividers=(18, 20, 22, 24, 26), reach_hz: float = 100e3):
    """Mic-clock divider options (HCLK/d, d even, 3.072-4.8 MHz): which harmonics of an f_sw source sit within
    `reach_hz` of a window centre n*fs_pdm. Returns {d: (fs_pdm, [(k, offset_hz)...])}."""
    out = {}
    for d in dividers:
        fs = HCLK / d
        if not (3.072e6 <= fs <= 4.8e6):
            continue
        hits = []
        for k in range(1, kmax + 1):
            fk = k * f_sw
            n = round(fk / fs)
            off = fk - n * fs
            if n >= 1 and abs(off) <= reach_hz:
                hits.append((k, round(off)))
        out[d] = (fs, hits)
    return out


def selftest():
    assert fold(1.0e6, 800e3) - 200e3 < 1
    # every harmonic of the PWM carrier folds to DC
    for k in range(1, 40):
        fo, _, dc = chain(k * FS_OUT)
        assert dc, (k, fo)
    # the mic clock and its harmonics fold to DC
    for k in range(1, 10):
        assert chain(k * FS_PDM)[2]
    # a 3 MHz tone (SMPS) is NOT coherent: lands somewhere in 0..100 kHz
    fo, att, dc = chain(3.0e6)
    assert not dc
    return True


if __name__ == "__main__":
    selftest()
    print("alias self-test ok; fs_pdm %.4f MHz fs_cic %.3f kHz fs_out %.4f kHz" % (FS_PDM / 1e6, FS_CIC / 1e3, FS_OUT / 1e3))
    print("\nasynchronous source 3.0 MHz +-20 % (core SMPS; tolerance is an assumption): share of each harmonic's range that aliases into 20-96 kHz with better than -40 dB")
    print("%3s %9s %9s %9s %10s" % ("k", "f_lo MHz", "f_hi MHz", "unprot. %", "best att dB"))
    for k, lo, hi, fr, att in window_scan(3.0e6, 0.2, 14):
        print("%3d %9.2f %9.2f %9.1f %10s" % (k, lo / 1e6, hi / 1e6, 100 * fr, "-" if att is None else "%.1f" % att))
    print("\nUSB FS 6 MHz toggle, +-300 ppm: windows")
    for k, lo, hi, fr, att in window_scan(6.0e6, 3e-4, 6):
        print("%3d %9.3f %9.3f %9.1f %10s" % (k, lo / 1e6, hi / 1e6, 100 * fr, "-" if att is None else "%.1f" % att))
    print("\nmic-clock divider options vs the 3.0 MHz SMPS: harmonics k within 100 kHz of n*fs_pdm (offset Hz = k*3 MHz - n*fs_pdm)")
    for d, (fs, hits) in fs_pdm_scan().items():
        print("  /%d  fs_pdm %.5f MHz  fs_out %.3f kHz  %s" % (d, fs / 1e6, fs / 20e3, hits if hits else "none up to k=24"))
    print()
    print("%-34s %12s %10s %9s %s" % ("line", "f_in", "f_out_Hz", "att_dB", "note"))
    for name, f in [("SMPS 3.0 MHz", 3.0e6), ("SMPS 2nd harmonic", 6.0e6), ("PWM carrier 200.02k", FS_OUT), ("PWM + 40 kHz sideband", FS_OUT + 40e3),
                    ("PWM 3rd + 40 kHz", 3 * FS_OUT + 40e3), ("mic clock 4.0004 M", FS_PDM), ("I2C 400 kHz", 400e3),
                    ("USB 6 MHz", 6.0e6), ("USB 12 MHz", 12.0e6), ("LED PWM 25 kHz", 25e3), ("hop comb 40.6 kHz", 26 * 1562.5),
                    ("tone at 240 kHz", 240e3), ("tone at 800.08 kHz+40k", FS_CIC + 40e3)]:
        fo, att, dc = chain(f)
        print("%-34s %12.1f %10.1f %9.1f %s" % (name, f, fo, att, "DC (removed by band floor)" if dc else ("IN BAND 20-96k" if 20e3 <= fo <= 96e3 else "")))
