"""NiTi tragus arm with the REAL build geometry: straight superelastic wire, clamped in a heel
socket, bending over a span `a`, then rigid (inside the pad and its strut) for a lever `b` to the
skin contact. Superelastic 'flag' fibre model, so both loading and unloading plateaus show.

    python3 sim/checks/niti_arm_real.py            # table for the geometry in hw/mech/out/arm_geometry.json
    import niti_arm_real as N; N.band(a, b, d)      # used by the CAD to set socket angles and clearances

Why (2026-09-30): the earlier tables treated all 20 mm from root to pad centre as bendable wire.
In the buildable design only the span between the heel socket and the pad/strut bends, so the
arm is stiffer and rides its plateau; the force band is then set by wire diameter and lever.

Material: loading plateau 450 MPa near skin temperature (Confluent SE508: >= 380 MPa at 3%, room
temperature, accessed 2026-09-30). The UNLOADING plateau (200 MPa) is NOT sourced (audit RC-01);
it is swept. E 58 GPa (data sheet 41-75). Transformation strain 6%. Small-slope beam theory.
Checks in main(): elastic cantilever 3EI/L^3 and fully-plastic Mp/L limits.
"""
from __future__ import annotations

import math

import numpy as np


class Beam:
    """Cantilever: `ns` sections along the bending span, each a circle cut into `nf` strips."""

    def __init__(self, a, b, d, ns=60, nf=41, E=58e3, sL=450.0, sU=200.0, epsL=0.06):
        r = d / 2
        edges = np.linspace(-r, r, nf + 1)
        self.y = 0.5 * (edges[1:] + edges[:-1])
        self.A = 2 * np.sqrt(np.maximum(r * r - self.y ** 2, 0)) * (edges[1] - edges[0])
        self.s = (np.arange(ns) + 0.5) * a / ns
        self.ds = a / ns
        self.lever = a + b - self.s
        self.a, self.b, self.d = a, b, d
        self.E, self.sL, self.sU, self.eL = E, sL, sU, epsL
        self.xi = np.zeros((ns, nf))                  # signed martensite fraction per strip
        self.k = np.zeros(ns)

    def _state(self, kappa):
        E, sL, sU, eL = self.E, self.sL, self.sU, self.eL
        eps = kappa[:, None] * self.y[None, :]
        xi = self.xi.copy()
        s = E * (eps - xi * eL)
        m = (xi > 0) & (s < sU)                        # reverse, tension side
        xi = np.where(m, np.clip((eps - sU / E) / eL, 0, 1), xi)
        s = E * (eps - xi * eL)
        m = (xi < 0) & (s > -sU)                       # reverse, compression side
        xi = np.where(m, np.clip((eps + sU / E) / eL, -1, 0), xi)
        s = E * (eps - xi * eL)
        m = (xi >= 0) & (s > sL)                       # forward, tension
        xi = np.where(m, np.clip((eps - sL / E) / eL, 0, 1), xi)
        s = E * (eps - xi * eL)
        m = (xi <= 0) & (s < -sL)                      # forward, compression
        xi = np.where(m, np.clip((eps + sL / E) / eL, -1, 0), xi)
        s = E * (eps - xi * eL)
        return (s * self.y[None, :] * self.A[None, :]).sum(axis=1), xi

    def curvatures(self, F):
        target = F * self.lever
        lo, hi = np.full_like(target, -0.6), np.full_like(target, 0.6)
        for _ in range(48):
            mid = 0.5 * (lo + hi)
            M, _ = self._state(mid)
            below = M < target
            lo, hi = np.where(below, mid, lo), np.where(below, hi, mid)
        return 0.5 * (lo + hi)

    def deflection(self, F):
        return float(np.sum(self.curvatures(F) * self.lever) * self.ds)

    def step(self, delta):
        lo, hi = -8.0, 8.0
        for _ in range(42):
            mid = 0.5 * (lo + hi)
            if self.deflection(mid) < delta:
                lo = mid
            else:
                hi = mid
        F = 0.5 * (lo + hi)
        k = self.curvatures(F)
        _, self.xi = self._state(k)
        self.k = k
        return F

    def shape(self):
        """Deflection w(s) of the span, tip rotation, and the largest gap between the wire and a
        rigid strut that follows the wire's END tangent (what a strut's channel must allow)."""
        s, k, ds = self.s, self.k, self.ds
        th = np.cumsum(k) * ds                          # slope
        w = np.cumsum(th) * ds                          # deflection
        th_end, w_end = th[-1], w[-1]
        strut_line = w_end - th_end * (self.a - s)      # strut is straight, along the end tangent
        return w, float(th_end), float(np.max(np.abs(w - strut_line)))


def jaw_history(d0=3.5, amp=2.0, cycles=2, step=0.25):
    h = list(np.arange(0, d0 + 1e-9, step))
    for _ in range(cycles):
        h += list(np.arange(d0, d0 - amp - 1e-9, -step)) + list(np.arange(d0 - amp, d0 + amp + 1e-9, step)) \
            + list(np.arange(d0 + amp, d0 - 1e-9, -step))
    return h


def band(a, b, d, d0=3.5, amp=2.0, sU=200.0):
    """Worn force band for a set of d0 mm (free pad sits d0 inside the skin), jaw +-amp."""
    beam = Beam(a, b, d, sU=sU)
    don = None
    Fs, dev = [], 0.0
    n_don = len(jaw_history(d0, amp, cycles=0))
    for i, delta in enumerate(jaw_history(d0, amp)):
        F = beam.step(delta)
        _, th, dv = beam.shape()
        dev = max(dev, dv)
        if i == n_don - 1:
            don = (F, th, float(np.max(np.abs(beam.k)) * d / 2))
        elif i >= n_don:
            Fs.append(F)
    _, th_end, _ = beam.shape()
    return {"F_don": don[0], "theta_don_deg": math.degrees(don[1]), "F_min": min(Fs), "F_max": max(Fs),
            "F_settled": Fs[-1], "theta_settled_deg": math.degrees(th_end), "strain_don": don[2],
            "strut_gap_mm": dev}


def checks():
    d, L = 0.75, 20.0
    EI = 58e3 * math.pi * d ** 4 / 64
    b = Beam(L, 0.0, d)
    F = b.step(0.3)
    ok1 = abs(F - 3 * EI * 0.3 / L ** 3) / (3 * EI * 0.3 / L ** 3)
    b = Beam(L, 0.0, d, epsL=10.0)          # endless plateau: isolates the fully-plastic limit
    for x in np.arange(0.5, 15.01, 0.5):
        F = b.step(x)
    ok2 = abs(F - 450 * d ** 3 / 6 / L) / (450 * d ** 3 / 6 / L)
    return ok1, ok2


def main():
    import json
    from pathlib import Path
    e1, e2 = checks()
    print(f"model checks: elastic 3EI/L^3 off by {e1 * 100:.1f}%, plastic Mp/L off by {e2 * 100:.1f}%")
    geo = Path(__file__).resolve().parents[2] / "hw/mech/out/arm_geometry.json"
    if geo.exists():
        g = json.loads(geo.read_text())
        a, b = g["a"], g["b"]
    else:
        a, b = 11.5, 7.6
    print(f"bending span a = {a:.1f} mm, rigid lever b = {b:.1f} mm ({'CAD' if geo.exists() else 'estimate'})")
    print("set 3.5 mm (free pad sits 3.5 mm inside the skin), jaw +-2 mm, 2 cycles, lower plateau 200 MPa")
    print(f"{'wire':>5s} {'donning':>8s} {'settled':>8s} {'jaw band':>11s} {'pad tilt':>8s} {'strain':>7s} {'strut gap':>9s}")
    rows = {}
    for d in (0.70, 0.75, 0.80, 0.85):
        r = band(a, b, d)
        rows[d] = r
        print(f"{d:5.2f} {r['F_don']:7.2f}N {r['F_settled']:7.2f}N {r['F_min']:4.2f}-{r['F_max']:.2f}N "
              f"{r['theta_settled_deg']:7.1f}° {r['strain_don'] * 100:6.1f}% {r['strut_gap_mm']:8.2f}mm")
    for sU in (150.0, 250.0):
        r = band(a, b, 0.80, sU=sU)
        print(f"  0.80 mm, lower plateau {sU:.0f} MPa: settled {r['F_settled']:.2f} N, jaw {r['F_min']:.2f}-{r['F_max']:.2f} N")
    return rows


if __name__ == "__main__":
    main()
