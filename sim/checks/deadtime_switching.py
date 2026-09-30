# Switching-level (not averaged) model of an H-bridge with dead time driving an R-L
# transducer. Compares:
#   AD: 2-level modulation, legs complementary. The ripple current crosses zero every
#       period, so at low signal levels the dead-time errors of the two edges cancel.
#   BD: 3-level modulation, legs in phase at idle. No idle ripple, so the load current's
#       sign follows the signal and dead time acts like crossover distortion.
# Hard-switching worst case: during dead time each bridge node follows the load current's
# direction (body diode). Duty is continuous (no quantization) to isolate dead-time effects.
# Reports in-band (<20 kHz) THD+N of the load current against the td=0 run, plus the
# resistive loss at idle (the price of AD's ripple).
import numpy as np

T_PWM = 5e-6  # 200 kHz, centre-aligned


def leg_edges(duty, inverted):
    """Centre-aligned high window [T(1-d)/2, T(1+d)/2]; returns (initial_state, edges)."""
    t_on, t_off = T_PWM * (1 - duty) / 2, T_PWM * (1 + duty) / 2
    if inverted:
        return 1, [(t_on, 0), (t_off, 1)]
    return 0, [(t_on, 1), (t_off, 0)]


def leg_state(s0, edges, t, td):
    """Commanded state at time t, and whether t falls inside a dead-time window."""
    s, dead = s0, False
    for te, new_state in edges:
        if t >= te + td:
            s = new_state
        elif t >= te:
            dead = True
    return s, dead


def run(mode, td, level_dbfs, L, R=8.0, vbus=3.0, f0=2500.0, n_per=8000):
    """Return per-period load current samples and the average resistive loss (W)."""
    k = np.arange(n_per)
    m_all = (10 ** (level_dbfs / 20) * np.sin(2 * np.pi * f0 * k * T_PWM)
             if level_dbfs is not None else np.zeros(n_per))
    i, loss, out = 0.0, 0.0, np.empty(n_per)
    for n, m in enumerate(m_all):
        dA = (1 + m) / 2
        if mode == "AD":                    # leg B is the logical inverse of leg A
            sA0, eA = leg_edges(dA, inverted=False)
            sB0, eB = leg_edges(dA, inverted=True)
        else:                               # BD: leg B runs at duty (1-m)/2, same polarity
            sA0, eA = leg_edges(dA, inverted=False)
            sB0, eB = leg_edges((1 - m) / 2, inverted=False)
        pts = {0.0, T_PWM}
        for t, _ in eA + eB:
            pts.add(t)
            pts.add(min(t + td, T_PWM))
        pts = sorted(pts)
        for t0, t1 in zip(pts[:-1], pts[1:]):
            dt = t1 - t0
            if dt <= 0:
                continue
            sA, deadA = leg_state(sA0, eA, t0 + 1e-15, td)
            sB, deadB = leg_state(sB0, eB, t0 + 1e-15, td)
            # current i flows A -> load -> B. During dead time a node sits on the rail its
            # body diode connects it to, which depends on the current's direction.
            vA = (0.0 if i > 0 else vbus) if deadA else sA * vbus
            vB = (vbus if i > 0 else 0.0) if deadB else sB * vbus
            i_inf = (vA - vB) / R
            decay = np.exp(-R * dt / L)
            c = i - i_inf
            loss += R * (i_inf ** 2 * dt + 2 * i_inf * c * (L / R) * (1 - decay)
                         + c ** 2 * (L / (2 * R)) * (1 - decay ** 2))
            i = i_inf + c * decay
        out[n] = i
    return out, loss / (n_per * T_PWM)


def inband_thd_n(x, ref):
    s = slice(len(x) // 4, None)
    x, ref = x[s], ref[s]
    g = np.dot(x, ref) / np.dot(ref, ref)   # a pure gain change is harmless; remove it
    w = np.hanning(len(x))
    E = np.abs(np.fft.rfft((x - g * ref) * w)) ** 2
    S = np.abs(np.fft.rfft(g * ref * w)) ** 2
    b = np.fft.rfftfreq(len(x), T_PWM) < 20e3
    return 10 * np.log10(E[b].sum() / S[b].sum())


if __name__ == "__main__":
    levels = (-20, -30, -40)
    for L in (0.3e-3, 1.0e-3):
        print(f"\nL = {L * 1e3:.1f} mH, R = 8 ohm, Vbus = 3.0 V, 200 kHz. In-band THD+N (dB re signal):")
        print(f"{'mode':>4} {'td':>7} | " + " ".join(f"{lv:>5}dBFS" for lv in levels) + " | idle loss")
        for mode in ("BD", "AD"):
            refs = {lv: run(mode, 0.0, lv, L)[0] for lv in levels}
            for td in (12.5e-9, 25e-9, 100e-9):
                row = [inband_thd_n(run(mode, td, lv, L)[0], refs[lv]) for lv in levels]
                idle = run(mode, td, None, L, n_per=400)[1]
                print(f"{mode:>4} {td * 1e9:5.1f}ns | " + " ".join(f"{v:9.1f}" for v in row)
                      + f" | {idle * 1e3:6.3f} mW")
