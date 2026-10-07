#!/usr/bin/env python3
"""Verify self-test |Z| method option D (sub-output issue 1, sub-debug-test DBG-5).

Option D: keep R21 (0.1 ohm low-side shunt) -> R22 1k / C22 10n (15.9 kHz) -> PA6 (ADC1_IN11), add the (B) offset
resistor 100k from +3V0 to I_SENSE, and recover |Z| and phase by synchronous detection at 2f: PA6 sees the bridge
SUPPLY current i*(2d-1) = (m*I/2)[cos(phi) - cos(2wt - phi)], so the 2f term carries I and phi (nothing sits at f).

Model (switched, not averaged): class-AD H-bridge, legs complementary, centre-aligned TIM1 at 80 MHz / 200 kHz,
duty quantised to the 12.5 ns tick (no noise shaper: the shaper's dither only helps). Each state puts one P and one N
FET in series with the coil (Rds P 0.88 / N 0.34 ohm, sub-output LF-9) plus R21; rail 3.0 V ideal. Coil = R + L.
Exact ZOH discretisation per tick (scipy lfilter) for the coil current and the R22/C22 node; offset resistor as a
Thevenin source on the RC node. ADC: one conversion per PWM period at the period start (TIM1 TRGO), 14 bit over
VREF+ = 3.0 V (ADC1 is 14-bit on U5), 0.5 LSB rms input noise [A]. Lock-in over an integer number of tone periods.
Reports |Z| and phase error vs the true load (coil + Rds + R21; firmware subtracts the known series terms) for
L 0.3 / 1.26 mH (sub-output placeholders), R 8 ohm, f 0.5-4 kHz, m at -12 / -22 / -32 dBFS.
Run (fenced): systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 python3 sim/checks/selftest_lockin.py
"""
import json
from pathlib import Path

import numpy as np
from scipy.signal import lfilter

ROOT = Path(__file__).resolve().parents[2]
VDD, FCLK, FPWM = 3.0, 80e6, 200e3
NT = int(FCLK / FPWM)                 # 400 ticks per PWM period
DT = 1 / FCLK
R21, R22, C22 = 0.1, 1e3, 10e-9
R_OFF = 100e3                          # option (B) offset resistor +3V0 -> I_SENSE
RDS_P, RDS_N = 0.88, 0.34
ADC_BITS, VREF, NOISE_LSB = 14, 3.0, 0.5
RNG = np.random.default_rng(1)


def run(R, L, f, m, n_cycles=40):
    """Return dict with estimated vs true Z for one case."""
    # integer tone periods and integer PWM periods
    n_pwm = int(round(n_cycles * FPWM / f))
    f = n_cycles * FPWM / n_pwm                 # snap the tone so the window is coherent
    k = np.arange(n_pwm)
    tc = (k + 0.5) / FPWM
    dA = 0.5 * (1 + m * np.sin(2 * np.pi * f * tc))
    on = np.round(dA * NT).astype(int)          # ticks with s = +1 (A high, B low), centred
    tick = np.arange(NT)
    lo = (NT - on) // 2
    s = np.where((tick[None, :] >= lo[:, None]) & (tick[None, :] < (lo + on)[:, None]), 1.0, -1.0).ravel()
    # coil: L di/dt = s*VDD - Rt*i  (ZOH exact)
    Rt = R + RDS_P + RDS_N + R21
    a = np.exp(-Rt * DT / L)
    b = (1 - a) / Rt
    i = lfilter([0, b], [1, -a], s * VDD)
    # sense node: R22 from v21 = R21*s*i, R_OFF from VDD, C22 to GND -> Thevenin
    rth = R22 * R_OFF / (R22 + R_OFF)
    vin = (R21 * s * i) * (R_OFF / (R22 + R_OFF)) + VDD * (R22 / (R22 + R_OFF))
    tau = rth * C22
    a2 = np.exp(-DT / tau)
    vc = lfilter([0, 1 - a2], [1, -a2], vin)
    # discard the first 25 % (start-up transient of L/R and the RC), keep integer tone periods
    vs = vc[::NT]                                 # one ADC sample per PWM period (period start)
    ts = k / FPWM
    keep = n_pwm // 4
    per = int(round(FPWM / f))
    nk = ((n_pwm - keep) // per) * per
    vs, ts = vs[-nk:], ts[-nk:]
    lsb = VREF / 2 ** ADC_BITS
    code = np.round(vs / lsb + RNG.normal(0, NOISE_LSB, vs.size))
    vq = code * lsb
    neg = float((vs < 0).mean())
    # lock-in at 2f
    w2 = 2 * np.pi * 2 * f
    X = 2 * np.mean(vq * np.exp(-1j * w2 * ts))
    # known chain: divider gain g, RC at 2f, plus the half-sample... sampled at period start (no extra delay beyond ZOH)
    g = R_OFF / (R22 + R_OFF)
    H = g / (1 + 1j * w2 * tau)
    P = X / (R21 * H)                             # = -(m I / 2) e^{-j phi}
    I_est = 2 * abs(P) / m
    phi_est = -np.angle(-P)
    Z_true = Rt + 1j * 2 * np.pi * f * L
    Zm_est = VDD * m / I_est
    dc = np.mean(vq) - VDD * (R22 / (R22 + R_OFF))
    return dict(R=R, L_mH=L * 1e3, f=round(f, 1), m=m, dBFS=round(20 * np.log10(m), 1),
                I_true_mA=round(1e3 * VDD * m / abs(Z_true), 2), sig_2f_uV=round(1e6 * abs(X), 1),
                Zmag_true=round(abs(Z_true), 3), Zmag_est=round(Zm_est, 3), Zmag_err_pct=round(100 * (Zm_est / abs(Z_true) - 1), 2),
                phase_true_deg=round(np.degrees(np.angle(Z_true)), 2), phase_est_deg=round(np.degrees(phi_est), 2),
                phase_err_deg=round(np.degrees(phi_est - np.angle(Z_true)), 2),
                raw_negative_frac=round(neg, 3), min_adc_V=round(float(vs.min()), 5), dc_term_uV=round(1e6 * dc, 1))


def main():
    rows = []
    for L in (0.3e-3, 1.26e-3):
        for f in (500.0, 1000.0, 2000.0, 4000.0):
            for dbfs in (-12, -22, -32):
                m = 10 ** (dbfs / 20)
                rows.append(run(8.0, L, f, m))
                print(rows[-1])
    long_rows = []                                 # 0.25 s window per point (firmware can integrate this long per sweep step)
    for L in (0.3e-3, 1.26e-3):
        for f in (1000.0, 4000.0):
            for dbfs in (-22, -32):
                m = 10 ** (dbfs / 20)
                long_rows.append(run(8.0, L, f, m, n_cycles=int(0.25 * f)))
                print("long", long_rows[-1])
    worst = dict(Zmag_err_pct=max(abs(r["Zmag_err_pct"]) for r in rows), phase_err_deg=max(abs(r["phase_err_deg"]) for r in rows))
    by_level = {d: dict(Zmag=max(abs(r["Zmag_err_pct"]) for r in rows if r["dBFS"] == d),
                        phase=max(abs(r["phase_err_deg"]) for r in rows if r["dBFS"] == d)) for d in (-12.0, -22.0, -32.0)}
    out = dict(src="sim/checks/selftest_lockin.py", date="2026-10-07",
               model="switched AD bridge at 12.5 ns ticks, R21->R22/C22 + 100k offset, 14-bit ADC 1 sample/PWM period, 2f lock-in, 40 tone periods",
               assumptions=dict(rds_p=RDS_P, rds_n=RDS_N, noise_lsb=NOISE_LSB, rail="ideal 3.0 V", coil="R + L (no motional term)"),
               worst=worst, worst_by_level=by_level, rows=rows,
               long_window_0p25s=dict(rows=long_rows, worst_Zmag_pct=max(abs(r["Zmag_err_pct"]) for r in long_rows),
                                      worst_phase_deg=max(abs(r["phase_err_deg"]) for r in long_rows)))
    od = ROOT / "sim/out/bridge"
    od.mkdir(parents=True, exist_ok=True)
    (od / "selftest_lockin.json").write_text(json.dumps(out, indent=1))
    print("worst", worst)
    print("by level", by_level)
    print("long window worst", out["long_window_0p25s"]["worst_Zmag_pct"], out["long_window_0p25s"]["worst_phase_deg"])


if __name__ == "__main__":
    main()
