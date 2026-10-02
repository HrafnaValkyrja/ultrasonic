"""Output-stage simplification study (2026-10-02): three numeric checks behind docs/research/simplify/output.md.

    python3 sim/checks/output_simplify.py runtime   # battery runtime of each output-stage variant (power.py model, 175 mAh)
    python3 sim/checks/output_simplify.py rail      # +3V0 audio-rate ripple with and without the 22 uF C14 (ngspice)
    python3 sim/checks/output_simplify.py f4        # F4: signed coil current from R21 sampled at mid-state A and B (ngspice)

All three are idealised models in the sense of C3-output-stage.md: the FET stand-in is the Diodes DMC2400UV model
(PMCXB290UE's own SPICE model is not available, sub-output.md issue 7), the exciter is 8 ohm + L, and the ADC is ideal
(no noise, offset or quantisation). Run `rail` and `f4` inside a memory fence:
    systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 python3 sim/checks/output_simplify.py f4

runtime: every variant changes only the active-chain current (idle is untouched, the bridge is stopped there).
  amp       = MAX98357A IDD (2.0 / 2.4 / 2.9 mA at 3.7 V: Maxim Rev 7 2/16 p.4, min / typ / max-ish) minus the bridge
              (0.5 / 0.77 / 1.0 mA) and gate pulls (0.06 mA), minus what the MCU no longer does (shaper + x16 interpolator
              6-12 Mcycle/s at 23 uA each = 0.14-0.28 mA, TIM1 0.20 mA -> SAI1 0.11 mA: 0.37 / 0.30 / 0.23 mA).
  AO3400A   = 4 x Qg(3 V) x 200 kHz; Qg read off AO3400A / AO3401A Fig. 7 (VDS 15 V): ~4.0 nC N, ~4.5 nC P -> 17 nC =
              3.4 mA total, the datasheet-conditions upper bound; ~11 nC = 2.1 mA at the real VDS of 3 V (the Miller part
              shrinks, derived estimate); the table uses the increase over today's 0.30 mA: +1.8 / +2.4 / +3.1 mA.
rail:     LDO = 3.0 V + 0.3 ohm behind a one-way diode (TPS7A2030 cannot sink), MCU + mic 4.5 mA, effective rail capacitance
          25.5 uF with C14 (X5R derated at 3 V bias), 15.5 uF without, 5 uF as a stress case.
f4:       TIM1 centre-aligned: state A (Q1P + Q2N) is centred on mid-period, state B on the period boundary; the ADC (RM0456
          Rev 7 Table 307: adc_ext_trg9 = tim1_trgo) is triggered by the update event at both. R21 carries +i in A and -i in
          B, so clip0(V_A) - clip0(V_B) = i with a unipolar ADC and no offset resistor.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(REPO / "sim/checks"))
import bridge_spice as B  # noqa: E402  (gate_pwl, fmt, MODEL, T: the project's own bridge netlist pieces)
import power as P  # noqa: E402
import spice  # noqa: E402

T = B.T


# --------------------------------------------------------------------------------------------- runtime
def runtime():
    led = (0.55, 0.55, 0.75)       # sub-power.md runtime table: 0.55 mA nominal, 0.75 pessimistic

    def rt(mah, duty, i, d_active):
        act = sum(v[i] for v in P.ACTIVE.values()) + d_active[i]
        idl = sum(v[i] for v in P.IDLE.values())
        return mah * P.USABLE[i] / (duty * act + (1 - duty) * idl + led[i])

    amp = tuple([2.0, 2.4, 2.9][k] - (P.ACTIVE["bridge gate charge + ripple"][k] + 0.06) - [0.37, 0.30, 0.23][k]
                for k in range(3))
    variants = {
        "today (discrete, 4 pulls, 12.5 ns)": (0.0, 0.0, 0.0),
        "simplified discrete (R4/R6 gone, -0.03 mA)": (-0.03, -0.03, -0.03),
        "discrete + AO3400A/AO3401A (+1.8 .. +3.1 mA gate)": (1.8, 2.4, 3.1),
        "discrete, PWM 800 kHz (MP-01 fallback, +0.8 mA)": (0.8, 0.8, 0.8),
        "MAX98357A from VSYS": amp,
    }
    print("amp active-chain delta vs today, mA (low / nominal / high):", [round(x, 2) for x in amp])
    print(f"{'variant':52s} {'18 % awake':>14s} {'50 %':>14s} {'100 %':>14s}   h, pessimistic .. nominal, 175 mAh, LED included")
    for name, d in variants.items():
        row = [f"{rt(175, duty, 2, d):5.1f} .. {rt(175, duty, 1, d):5.1f}" for duty in (0.18, 0.5, 1.0)]
        print(f"{name:52s} " + "  ".join(f"{x:>14s}" for x in row))
    print("\nAged cell, 140 mAh (80 % of 175), always awake:")
    for name, d in variants.items():
        print(f"{name:52s} {rt(140, 1.0, 2, d):5.1f} .. {rt(140, 1.0, 1, d):5.1f} h")


# --------------------------------------------------------------------------------------------- rail ripple
def _rail_net(amp, f_sig, L, ctot, n_per, dt=12.5e-9):
    k = np.arange(n_per)
    d_a = 0.5 + 0.5 * amp * np.sin(2 * np.pi * f_sig * (k + 0.5) * T)
    t_end = n_per * T
    pa, na = B.gate_pwl(d_a, dt, t_end)
    pb, nb = B.gate_pwl(1 - d_a, dt, t_end, centre_offset=T / 2 + 100e-12)
    return f"""* rail ripple
.include {B.MODEL}
.model DID D(IS=1e-12 N=0.05 RS=0.02)
VIN vin 0 3.0
DL vin vlo DID
RLDO vlo vdd 0.3
CB1 vdd 0 {ctot * 1e6:.2f}u ic=3.0
IMCU vdd 0 4.5m
XPA outa gpa vdd DMC2400UV_PMOS
XNA outa gna 0 DMC2400UV_NMOS
XPB outb gpb vdd DMC2400UV_PMOS
XNB outb gnb 0 DMC2400UV_NMOS
VGPA gpa_s 0 PWL({B.fmt(pa)})
VGNA gna_s 0 PWL({B.fmt(na)})
VGPB gpb_s 0 PWL({B.fmt(pb)})
VGNB gnb_s 0 PWL({B.fmt(nb)})
RGPA gpa_s gpa 30
RGNA gna_s gna 30
RGPB gpb_s gpb 30
RGNB gnb_s gnb 30
RPUA gpa vdd 100k
RPDA gna 0 100k
RPUB gpb vdd 100k
RPDB gnb 0 100k
CESA outa 0 35p
CESB outb 0 35p
RX outa xm 8
LX xm outb {L}
.options method=trap reltol=2e-3 abstol=1e-8 vntol=1e-4 gmin=1e-10 rshunt=1e12 itl4=100
.tran 2n {t_end - T / 2:.10e} 0 5n uic
.end
"""


def rail():
    print("+3V0 audio-rate motion (mV peak-to-peak after a 0.6 ms settle, 200 kHz carrier averaged out)")
    print(f"{'tone':>8s} {'level':>9s} {'L':>7s} {'C_rail':>8s} {'pk-pk mV':>9s} {'max V':>7s} {'min V':>7s}")
    for f, amp, lab in ((2000.0, 0.251, "-12 dBFS"), (2000.0, 1.0, "0 dBFS"), (4000.0, 0.251, "-12 dBFS")):
        for L in (0.3e-3, 1.26e-3):
            for ctot in (25.5e-6, 15.5e-6, 5e-6):
                n_per = 500 if f == 2000.0 else 400
                r = spice.run(_rail_net(amp, f, L, ctot, n_per))
                t, v = r.tran["time"], r.tran["v(vdd)"]
                _, vv = spice.resample(t, v, 0.5e-6, 0.6e-3, t[-1])
                vs = np.convolve(vv, np.ones(10) / 10, mode="valid")
                print(f"{f:8.0f} {lab:>9s} {L * 1e3:5.2f}mH {ctot * 1e6:6.1f}uF {1e3 * (vs.max() - vs.min()):9.1f} "
                      f"{vs.max():7.3f} {vs.min():7.3f}")


# --------------------------------------------------------------------------------------------- F4
def _f4_net(amp, f_sig, L, n_per, dt=12.5e-9):
    k = np.arange(n_per)
    d_a = 0.5 + 0.5 * amp * np.sin(2 * np.pi * f_sig * (k + 0.5) * T)
    t_end = n_per * T
    pa, na = B.gate_pwl(d_a, dt, t_end)
    pb, nb = B.gate_pwl(1 - d_a, dt, t_end, centre_offset=T / 2 + 100e-12)
    return f"""* F4 mid-state sampling
.include {B.MODEL}
VIN vin 0 3.0
RLDO vin vdd 0.3
CB1 vdd 0 22u
CB2 vdd 0 100n
XPA outa gpa vdd DMC2400UV_PMOS
XNA outa gna brt DMC2400UV_NMOS
XPB outb gpb vdd DMC2400UV_PMOS
XNB outb gnb brt DMC2400UV_NMOS
R21 brt 0 0.1
VGPA gpa_s 0 PWL({B.fmt(pa)})
VGNA gna_s 0 PWL({B.fmt(na)})
VGPB gpb_s 0 PWL({B.fmt(pb)})
VGNB gnb_s 0 PWL({B.fmt(nb)})
RGPA gpa_s gpa 30
RGNA gna_s gna 30
RGPB gpb_s gpb 30
RGNB gnb_s gnb 30
RPUA gpa vdd 100k
RPUB gpb vdd 100k
CESA outa 0 35p
CESB outb 0 35p
RX outa xm 8
LX xm outb {L}
.options method=trap reltol=2e-3 abstol=1e-8 vntol=1e-4 gmin=1e-10 rshunt=1e12 itl4=100
.tran 2n {t_end - T / 2:.10e} 0 5n
.end
"""


def _f4_case(amp, L, f_sig=2000.0, n_per=400):
    for n_try in (n_per, n_per - 20, n_per - 40):      # ngspice occasionally stalls; a shorter record steps past it
        try:
            r = spice.run(_f4_net(amp, f_sig, L, n_try))
            break
        except spice.SpiceError:
            continue
    t, vb, il = r.tran["time"], r.tran["v(brt)"], r.tran["i(lx)"]
    ks = np.arange(8, n_try - 2)
    ks = ks[ks * T > 300e-6]
    t_a, t_b = (ks + 0.5) * T, ks * T                  # mid state A, mid state B
    v_a, v_b = np.interp(t_a, t, vb), np.interp(t_b, t, vb)
    ihat = (np.clip(v_a, 0, None) - np.clip(v_b, 0, None)) / 0.1
    ref = np.array([np.mean(np.interp(np.linspace(a - T / 2, a + T / 2, 41), t, il)) for a in t_a])

    def phasor(x, tt):
        return 2 * np.mean(x * np.exp(-2j * np.pi * f_sig * tt))

    p_hat, p_ref = phasor(ihat, t_a), phasor(ref, t_a)
    return (abs(p_ref) * 1e3, (abs(p_hat) / abs(p_ref) - 1) * 100, np.degrees(np.angle(p_hat / p_ref)),
            np.sqrt(np.mean((ihat - ref) ** 2)) * 1e3)


def f4():
    print("2 kHz tone, 12.5 ns dead time, ideal ADC; i_hat = clip0(V_A) - clip0(V_B) over R21 = 0.1 ohm")
    print(f"{'L':>8s} {'level':>10s} {'coil I pk mA':>13s} {'amp err %':>10s} {'phase err deg':>14s} {'rms err mA':>11s}")
    for L in (0.3e-3, 1.26e-3):
        for amp, lab in ((0.251, "-12 dBFS"), (0.0794, "-22 dBFS"), (0.0251, "-32 dBFS")):
            a, e, p, rm = _f4_case(amp, L)
            print(f"{L * 1e3:6.2f}mH {lab:>10s} {a:13.1f} {e:10.2f} {p:14.2f} {rm:11.2f}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    {"runtime": runtime, "rail": rail, "f4": f4}.get(cmd, lambda: print(__doc__))()
