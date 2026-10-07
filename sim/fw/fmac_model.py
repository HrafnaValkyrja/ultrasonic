#!/usr/bin/env python3
"""sim/fw/fmac_model.py: bit-accurate host model of the STM32U575 FMAC FIR datapath (RM0456 Rev 7 s26.3.6-26.3.7, read 2026-10-07 from
~/Desktop/ultrasonic-scratch/st_new/rm7.txt) and the precision study for moving the x16 polyphase interpolator onto it (FWSIM-R47 lever).

FMAC arithmetic as the RM states it: q1.15 inputs and coefficients, 16x16 multiplier, 26-bit accumulator q4.22 that WRAPS (no saturation)
on partial sums, output gain 2^R (R 0..7) then either truncation of the unused accumulator bits or saturation (CLIPEN) to q1.15.
Not stated in the RM and therefore ASSUMED here [A]: (A1) each 30-bit fractional product enters the q4.22 accumulator truncated (arithmetic
shift right by 8 = floor); (A2) the q1.15 output takes accumulator bits [22..7] after the gain, i.e. floor (truncation toward -inf).
Both are the worst plausible choice (biased); a bench read-back of known vectors on the U575 (E4/V8) settles them.

  python3 sim/fw/fmac_model.py [--json PATH]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy import signal

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path[:0] = [str(REPO / "fw/tools"), str(REPO / "sim/dsp"), str(REPO / "sim/e2e")]

ACC_BITS = 26


def q15(x):
    """float -> q1.15 int, round to nearest, saturate"""
    return np.clip(np.round(np.asarray(x, float) * 32768.0), -32768, 32767).astype(np.int64)


def wrap(v, bits=ACC_BITS):
    m = 1 << bits
    return ((v + (m >> 1)) % m) - (m >> 1)


def fmac_fir(x_q, h_q, R=0, clip=True):
    """FMAC FIR (FUNC 8): y[n] = 2^R * sum_k h[k] x[n-k], inputs int q1.15 (x zero before n = 0). Returns int q1.15."""
    x_q, h_q = np.asarray(x_q, np.int64), np.asarray(h_q, np.int64)
    N = len(h_q)
    xp = np.concatenate([np.zeros(N - 1, np.int64), x_q])
    acc = np.zeros(len(x_q), np.int64)
    for k in range(N):                                     # sequential accumulation, wrap after every add (26 bits)
        prod = (h_q[k] * xp[N - 1 - k: N - 1 - k + len(x_q)]) >> 8     # q2.30 -> q.22, floor  [A1]
        acc = wrap(acc + prod)
    out = (acc << R) >> 7                                  # q.22 -> q1.15 after gain, floor  [A2]
    if clip:
        return np.clip(out, -32768, 32767)
    return ((out + 32768) % 65536) - 32768


def interp_tables(tpp):
    import dsp_tables as dt                                # the firmware's own prototype (fw/tools/dsp_tables.py)
    h, rej = dt.interp_proto(tpp)
    poly = np.array([[h[16 * t + p] for t in range(tpp)] for p in range(16)])
    return poly, rej


def interp_float(y, poly):
    """the firmware's float polyphase x16 (reference for the error)"""
    out = np.zeros(len(y) * 16)
    for p in range(16):
        out[p::16] = signal.lfilter(poly[p], 1.0, y)
    return out


def interp_fmac(y, poly, s):
    """polyphase x16 on FMAC: 16 FIR runs (one per phase, X2_BASE switched), input y*s in q1.15, coefficients scaled by 2^-Rc with gain R=Rc"""
    cmax = np.max(np.abs(poly))
    Rc = int(np.ceil(np.log2(cmax / (32767 / 32768)))) if cmax >= 1 else 0
    hq = q15(poly / 2 ** Rc)
    xq = q15(y * s)
    out = np.zeros(len(y) * 16)
    for p in range(16):
        out[p::16] = fmac_fir(xq, hq[p], R=Rc) / 32768.0 / s
    return out, Rc


def tone(f, dbfs, n, fs=12500.0):
    return 10 ** (dbfs / 20) * np.sin(2 * np.pi * f * np.arange(n) / fs)


def inband_err_db(err, ref, fs=200e3, band=(200.0, 16e3)):
    """error power in band (dBFS, peak-ref like pipeline.dbfs) and re the reference signal power in band (dB)"""
    w = np.hanning(len(err))
    E = np.abs(np.fft.rfft(err * w)) ** 2
    S = np.abs(np.fft.rfft(ref * w)) ** 2
    f = np.fft.rfftfreq(len(err), 1 / fs)
    b = (f >= band[0]) & (f < band[1])
    e_dbfs = 10 * np.log10(E[b].sum() / (np.sum(w ** 2) / 2) * 2 / len(err) + 1e-30)
    return float(e_dbfs), float(10 * np.log10(E[b].sum() / max(S[b].sum(), 1e-30) + 1e-30))


def study(tpp=10, ceiling_dbfs=-12.0):
    poly, rej = interp_tables(tpp)
    c = 10 ** (ceiling_dbfs / 20)
    kappa = float(np.max(np.sum(np.abs(poly), axis=1)))     # worst-case interpolator overshoot for |y| <= 1
    rows = {}
    n = 12500
    cases = {
        # (A) limiter BEFORE the FMAC (12.5 kS/s sample limit at the ceiling): |y| <= c, input scale uses the overshoot bound
        "prelimited_scale": 0.999 / (c * kappa),
        # (C) recommended: scaling guard at ceiling + 6 dB before the FMAC, true-peak limiter unchanged after it
        "guard6_scale": 0.999 / (2 * c * kappa),
        # (B) today's placement (true-peak limiter AFTER interpolation): the FMAC sees the raw stream, up to ~+14 dBFS (L2 D17: 13.5 dBFS)
        "raw_scale": 0.999 / (10 ** (14.5 / 20) * kappa),
    }
    for name, s in cases.items():
        for f, db in ((2400.0, -40.0), (2400.0, -12.0), (1500.0, -60.0)):
            if name != "prelimited_scale" or db <= ceiling_dbfs:
                y = tone(f, db, n)
                ref = interp_float(y, poly)
                got, Rc = interp_fmac(y, poly, s)
                e_dbfs, e_rel = inband_err_db((got - ref)[1600:], ref[1600:])
                rows[f"{name}.{int(f)}Hz_{int(db)}dBFS"] = {"err_inband_dbfs": round(e_dbfs, 1), "err_re_tone_db": round(e_rel, 1),
                                                            "coef_gain_R": Rc, "input_scale": round(s, 4), "lsb_fs": float(1 / 32768 / s)}
    # D17.chain_thdn_m40_db with the FMAC error added (sim value -49.3 dB with the float interpolator, limit -45)
    base = -49.29
    for name in cases:
        e = rows[f"{name}.2400Hz_-40dBFS"]["err_re_tone_db"]
        rows[f"{name}.D17_chain_thdn_m40_db_est"] = round(10 * np.log10(10 ** (base / 10) + 10 ** (e / 10)), 2)
    # accumulator range: worst partial sum for a full-scale input
    hq = q15(poly / 2 ** rows[next(iter(rows))]["coef_gain_R"])
    acc_max = float(np.max(np.sum(np.abs(hq), axis=1)) / 32768)        # q1.15 input at full scale: |sum| in q4.22 units of 1.0
    return {"tpp": tpp, "image_rejection_db": round(rej, 1), "overshoot_kappa": round(kappa, 4), "acc_worst_partial_sum_q4_22": round(acc_max, 3),
            "acc_limit": 8.0, "assumptions": ["A1 product truncated (floor) into q4.22", "A2 output floor of bits [22..7] after the gain"], "cases": rows}


def check_c(n_trials=200, seed=7):
    """the firmware's C model (fw/core/fmac_model.c via sim/fw/fwlib.py) == this Python model, bit for bit, on random banks incl.
    extreme values (saturation, -32768 x -32768, accumulator wrap) and every gain R"""
    import ctypes as C
    import fwlib
    L = fwlib.lib()
    I16 = np.ctypeslib.ndpointer(np.int16, flags="C_CONTIGUOUS")
    L.shim_fmac_bank.argtypes = [I16, C.c_uint32, C.c_uint32, C.c_uint32, I16, C.c_uint32, I16]
    rng = np.random.default_rng(seed)
    bad = 0
    for i in range(n_trials):
        taps, nph, n_new, R = int(rng.integers(2, 128)), int(rng.integers(1, 17)), int(rng.integers(1, 17)), int(rng.integers(0, 8))
        if i % 4 == 0:
            coef = rng.choice([-32768, 32767, -1, 0, 1], size=nph * taps).astype(np.int16)
            x = rng.choice([-32768, 32767, -1, 0, 1], size=taps - 1 + n_new).astype(np.int16)
        else:
            coef = rng.integers(-32768, 32768, nph * taps).astype(np.int16)
            x = rng.integers(-32768, 32768, taps - 1 + n_new).astype(np.int16)
        y = np.zeros(n_new * nph, np.int16)
        L.shim_fmac_bank(coef, nph, taps, R, x, n_new, y)
        for p in range(nph):
            ref = fmac_fir(x.astype(np.int64), coef[p * taps:(p + 1) * taps].astype(np.int64), R)[taps - 1:]
            bad += int(np.sum(ref != y[p::nph]))
    return bad


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", type=Path)
    ap.add_argument("--check", action="store_true", help="C model vs Python model, bit-exact; exit 1 on any mismatch")
    ap.add_argument("--bench", action="store_true", help="expected read-back words of the backlog FMAC-RM-UNKNOWNS bench test")
    a = ap.parse_args(argv)
    if a.bench:
        x = np.array([0x0001, 0x007F, 0x0080, 0x00FF, -1, -127, -128, -255], np.int64)
        for name, b0, R in (("A1 (R=7, b0=0x0001)", 1, 7), ("A2 (R=0, b0=0x0100)", 0x100, 0)):
            y = [int(fmac_fir(np.array([v]), np.array([b0]), R)[0]) for v in x]
            print(f"{name}: x={[hex(v & 0xFFFF) for v in x]} -> y={y}")
        return 0
    if a.check:
        bad = check_c()
        print(f"fmac_model C vs Python: {bad} mismatching outputs")
        return 1 if bad else 0
    r = study()
    print(json.dumps(r, indent=1))
    if a.json:
        a.json.write_text(json.dumps(r, indent=1) + "\n")


if __name__ == "__main__":
    sys.exit(main())
