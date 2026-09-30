"""Transistor-level check of the D6 output stage with Diodes' own DMC2400UV model (ngspice).

    python3 sim/checks/bridge_spice.py       # table + sim/out/bridge/*.png

What it answers (the earlier checks used ideal switches):
  1. idle current at zero signal: ripple + switching + gate charge, from the 3.0 V rail and the GPIOs
  2. shoot-through with the real FETs at 0 / 12.5 / 25 ns dead time
  3. low-level distortion from dead time with real edge shapes (AD modulation)
The recommended bridge part is PMCXB290UE, whose model sits behind Nexperia's bot wall; the
DMC2400UV has similar gate charge and on-resistance (B-parts-selection.md), so it stands in.
The duty is not quantised here (the noise shaper's job, checked in pwm_noise.py); this run
isolates the analog effects.

Circuit: 3.0 V rail (LDO modelled as 0.3 ohm + 22 uF + 100 nF), two complementary legs,
transducer as R + L (8 ohm, 0.3 mH placeholder and 1.26 mH, the only published bone-transducer
inductance; D7), 35 pF ESD diode per lead, GPIO gate drive as 2 ns edges through 30 ohm,
100 k gate pulls (D6). TIM1 at 80 MHz, centre-aligned, 200 kHz.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
import plotstyle  # noqa: E402
import spice  # noqa: E402

OUT = REPO / "sim/out/bridge"
OUT.mkdir(parents=True, exist_ok=True)
MODEL = REPO / "sim/spice/models/DMC2400UV_ng.lib"   # convergence copy, see its header
VDD, FPWM, TCLK = 3.0, 200e3, 12.5e-9
T = 1 / FPWM
EDGE = 2e-9


def gate_pwl(duties, dt, t_end, centre_offset=0.0):
    """PWL gate waveforms for one leg. Returns (p_gate, n_gate) lists of (t, v).

    P-channel high side is ON when its gate is LOW. Dead time: turn the conducting FET off first,
    turn the other on dt later.
    """
    # Edges are NOT snapped to the 12.5 ns timer tick: at -40 dBFS the whole modulation spans ~2
    # ticks, and that quantisation is the noise shaper's job (pwm_noise.py). This check isolates
    # the analog effects (dead time, FET edges); fmt() still rounds to 1 ps for ngspice.
    q = lambda x: x
    p, n = [(0.0, VDD)], [(0.0, 0.0)]   # start: P off, N off (both pulled off at reset)

    def step(lst, t, v):
        if lst[-1][1] != v:
            lst.append((t, lst[-1][1]))
            lst.append((t + EDGE, v))

    # establish low state (N on) at t = 50 ns
    step(n, 50e-9, VDD)
    for k, d in enumerate(duties):
        tc = (k + 0.5) * T + centre_offset
        t_on, t_off = q(tc - d * T / 2), q(tc + d * T / 2)
        if tc + T / 2 > t_end:
            break
        # low -> high: N off, then P on
        step(n, t_on, 0.0)
        step(p, t_on + dt, 0.0)
        # high -> low: P off, then N on
        step(p, t_off, VDD)
        step(n, t_off + dt, VDD)
    return p, n


def fmt(pwl):
    # integer picoseconds: edges from different sources that should coincide do so exactly,
    # instead of landing 1e-19 s apart and forcing ngspice's timestep to zero
    return " ".join(f"{round(t * 1e12)}p {v:g}" for t, v in pwl)


def netlist(dt, amp, f_sig, L, n_per, fname):
    k = np.arange(n_per)
    d_a = 0.5 + 0.5 * amp * np.sin(2 * np.pi * f_sig * (k + 0.5) * T)
    t_end = n_per * T
    pa, na = gate_pwl(d_a, dt, t_end)
    # AD (2-level): leg B is leg A inverted, so its high window is centred on the period boundary.
    # (Centring both legs on the same instant with duty 1-d would be 3-level BD, not AD.)
    # +100 ps: real pin-to-pin skew; exactly simultaneous edges on both legs stall ngspice
    pb, nb = gate_pwl(1 - d_a, dt, t_end, centre_offset=T / 2 + 100e-12)
    return f"""* H-bridge, DMC2400UV, dead time {dt*1e9:.1f} ns
.include {MODEL}
VIN vin 0 {VDD}
RLDO vin vdd 0.3
CB1 vdd 0 22u
CB2 vdd 0 100n
* leg A
XPA outa gpa vdd DMC2400UV_PMOS
XNA outa gna 0 DMC2400UV_NMOS
* leg B
XPB outb gpb vdd DMC2400UV_PMOS
XNB outb gnb 0 DMC2400UV_NMOS
VGPA gpa_s 0 PWL({fmt(pa)})
VGNA gna_s 0 PWL({fmt(na)})
VGPB gpb_s 0 PWL({fmt(pb)})
VGNB gnb_s 0 PWL({fmt(nb)})
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
* transducer: R + L
RX outa xm 8
LX xm outb {L}
.options method=trap reltol=2e-3 abstol=1e-8 vntol=1e-4 gmin=1e-10 rshunt=1e12 itl4=100
.tran 2n {t_end - T / 2:.10e} 0 5n
.end
"""


def run_case(dt, amp, L, n_per=500, f_sig=2000.0):
    # ngspice 42 occasionally stalls on a simultaneous turn-off/turn-on of the two legs (the model's
    # Cgd limiter diodes); a slightly shorter record steps past it. Reported, not hidden.
    for n_try in (n_per, n_per - 20, n_per - 40):
        try:
            res = spice.run(netlist(dt, amp, f_sig, L, n_try, None))
            break
        except spice.SpiceError:
            print(f"    (ngspice stalled at {n_try} periods; retrying shorter)")
    else:
        raise RuntimeError("bridge sim failed at all record lengths")
    t = res.tran["time"]
    i_vdd = -res.tran["i(vin)"]
    i_gates = sum(np.abs(res.tran[f"i(vg{x})"]) for x in ("pa", "na", "pb", "nb"))
    i_load = res.tran["i(lx)"]
    # current through the leg-A FETs during transitions: shoot-through shows as a bus current spike
    t0 = 5 * T
    avg_vdd = spice.tavg(t, i_vdd, t0, t[-1])
    # gate drive: the charge the GPIO supplies per cycle, as an average current from the 3 V rail
    gate_q = spice.tavg(t, i_gates, t0, t[-1]) / 2    # each edge's current counted once (charge + discharge)
    peak_bus = np.max(i_vdd[t > t0])
    return dict(t=t, i_vdd=i_vdd, i_load=i_load, avg_vdd=avg_vdd, gate=gate_q, peak_bus=peak_bus)


def thd(t, i, f_sig, t0):
    fs = 10e6        # well above the 200 kHz carrier: nothing aliases into the audio band
    tt, y = spice.resample(t, i, 1 / fs, t0, t[-1])
    n = len(y) - len(y) % int(fs / f_sig)
    y = (y[:n] - np.mean(y[:n])) * np.hanning(n)
    Y = np.abs(np.fft.rfft(y))
    f = np.fft.rfftfreq(n, 1 / fs)
    fund = Y[np.argmin(np.abs(f - f_sig))]
    band = (f > 300) & (f < 16e3) & (np.abs(f - f_sig) > 800)
    return 20 * np.log10(np.sqrt(np.sum(Y[band] ** 2)) / fund), f, 20 * np.log10(Y / Y.max() + 1e-12)


def main():
    rows = []
    for L in (0.3e-3, 1.26e-3):
        for dt in (0.0, 12.5e-9, 25e-9, 37.5e-9):
            r = run_case(dt, 0.0, L, n_per=60)
            rows.append(("idle", L, dt, r))
    print("Zero signal (idle), 3.0 V rail:")
    print(f"{'L':>7s} {'dead':>6s} {'bus avg mA':>11s} {'bus peak mA':>12s} {'gate drive mA':>14s}")
    for _, L, dt, r in rows:
        print(f"{L*1e3:5.2f}mH {dt*1e9:5.1f}ns {r['avg_vdd']*1e3:11.3f} {r['peak_bus']*1e3:12.1f} {r['gate']*1e3:14.3f}")

    print("\nIn-band distortion + noise of the coil current, 2 kHz tone (dB re tone):")
    plt = plotstyle.apply()
    fig, axs = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    for ax, amp, lab in ((axs[0], 0.251, "-12 dBFS (the output ceiling)"), (axs[1], 0.01, "-40 dBFS (quiet)")):
        for c, dt in zip(plotstyle.SERIES, (12.5e-9, 25e-9, 37.5e-9)):
            r = run_case(dt, amp, 0.3e-3, n_per=380)   # 1.9 ms: 3 full cycles after settling
            v, f, S = thd(r["t"], r["i_load"], 2000.0, 300e-6)   # skip 8 L/R time constants of start-up
            print(f"  {lab:32s} dead {dt*1e9:4.1f} ns: THD+N {v:6.1f} dB   bus avg {r['avg_vdd']*1e3:.2f} mA")
            ax.plot(f / 1e3, S, color=c, lw=0.9, label=f"dead time {dt*1e9:.1f} ns: THD+N {v:.0f} dB")
        ax.set_xlim(0, 16)
        ax.set_ylim(-110, 5)
        ax.set_xlabel("kHz")
        ax.set_title(f"Coil current spectrum, {lab}")
        ax.legend(loc="upper right")
    axs[0].set_ylabel("dB re the 2 kHz tone")
    fig.savefig(OUT / "bridge_spectrum.png")


if __name__ == "__main__":
    main()
