"""Open gap between lid and board as a two-port: impedance matrix of two circular ports on opposite rigid
plates of an (unbounded) parallel-plate waveguide, laterally offset.

Port 1 = lid bore exit (disc radius a1 on the plate z=0).  Port 2 = board hole entrance (disc radius a2 on the
plate z=h, lateral offset delta).  Uniform normal velocity on each disc; port pressure = mean over the disc.
Neumann Green function of the plate pair, modal sum n = 0..N-1 (cos(n pi z/h) modes):
    G = sum_n (eps_n/h) cos(n pi z/h) cos(n pi z'/h) g_n(rho),  g_n = (1/2 pi) int_0^inf J0(q rho) q dq/(q^2 - k_n^2),
    k_n^2 = k^2 - (n pi/h)^2
so, with the Graf addition theorem for the two discs,
    Z_ij = (2 j w rho / (pi a_i a_j h)) sum_n eps_n c_i c_j I_n,
    I_n = int_0^inf J1(q a_i) J1(q a_j) J0(q delta_ij) dq / (q (q^2 - k_n^2)),   c = cos(n pi z/h).
The n = 0 pole (q = k0, outgoing wave, k0 complex from the slit loss) is integrated on a dense panel grid;
n >= 1 are evanescent below c/(2h) (114 kHz for h = 1.5 mm): near-field only.
Assumptions (state them): lateral extent infinite (matched; the real cavity walls 3.4-30 mm away add reflections,
not modelled: widened uncertainty), rigid plates, parts and traces on the board in the gap ignored.
"""
from __future__ import annotations

import numpy as np
from scipy import special as sp

from narrow import AIR, slit_eff


def _qgrid(k, a_max_sum, n_osc_panels=1):
    """Composite Gauss-Legendre grid in q (rad/m) with a dense panel around the pole q = Re k."""
    gl_x, gl_w = np.polynomial.legendre.leggauss(16)
    # pole q = Re k0 carries the slit loss (Im/Re 0.3-1 %): panels down to +-0.1 % around it (2026-10-02: the earlier
    # +-3 % panel under-resolved it, n = 0 term off by 3.6 % at 90 kHz)
    edges = [x * k for x in (0.0, .5, .8, .9, .95, .98, .99, .995, .998, .999, 1.0, 1.001, 1.002, 1.005, 1.01, 1.02, 1.05, 1.1, 1.2, 1.5, 2.5)]
    q_hi = 60.0 / max(a_max_sum, 1e-5)                 # integrand ~ q^-4.5: truncation error ~ (60)^-3.5
    nx = int(np.ceil(q_hi / (np.pi / max(a_max_sum, 1e-5) * 2)))   # panels of ~2 oscillations
    edges += list(np.linspace(2.5 * k, q_hi, max(nx, 4) + 1)[1:])
    q, w = [], []
    for lo, hi in zip(edges[:-1], edges[1:]):
        if hi <= lo:
            continue
        q.append(0.5 * (hi - lo) * gl_x + 0.5 * (hi + lo))
        w.append(0.5 * (hi - lo) * gl_w)
    return np.concatenate(q), np.concatenate(w)


def gap_z(f, h, a1, a2, delta, air=AIR, nmodes=64, return_n0=False):
    """Return Z11, Z12(=Z21), Z22 (acoustic, Pa s/m^3), arrays over f.  return_n0: also the n = 0 (plane-in-gap, radial
    wave) parts of the three entries, which rect_n0_dz() replaces by the finite-channel version."""
    f = np.atleast_1d(np.asarray(f, float))
    Z11 = np.empty(f.shape, complex)
    Z12 = np.empty(f.shape, complex)
    Z22 = np.empty(f.shape, complex)
    N0 = np.empty((3,) + f.shape, complex)
    rho_e, C_e = slit_eff(f, h, air)
    k0c = 2 * np.pi * f * np.sqrt(rho_e * C_e)          # complex plane-wave number between the plates
    n = np.arange(nmodes)
    eps = np.where(n == 0, 1.0, 2.0)
    sign = np.where(n % 2 == 0, 1.0, -1.0)
    kn2_ev = -(n * np.pi / h) ** 2                      # evanescent part (n>=1)
    for i, fi in enumerate(f):
        w = 2 * np.pi * fi
        k = w / air.c
        q, wq = _qgrid(k, a1 + a2 + abs(delta))
        J11 = sp.j1(q * a1) ** 2
        J22 = sp.j1(q * a2) ** 2
        J12 = sp.j1(q * a1) * sp.j1(q * a2) * sp.j0(q * delta)
        den = q[None, :] ** 2 - (k0c[i] ** 2 + kn2_ev)[:, None]          # (nmodes, nq)
        base = wq / q / den
        I11 = base @ J11
        I22 = base @ J22
        I12 = base @ J12
        pref = 2j * w * air.rho / (np.pi * h)
        # n = 0 (uniform across the gap) carries the slit's effective density rho_e (visco-thermal); n >= 1 are near-field, rho
        r0 = rho_e[i] / air.rho
        I11[0], I12[0], I22[0] = I11[0] * r0, I12[0] * r0, I22[0] * r0
        # same-plate sums converge like 1/N (log-type near field): Richardson tail from partial sums at N/2, N
        c11, c22 = np.cumsum(eps * I11), np.cumsum(eps * I22)
        h2 = nmodes // 2 - 1
        Z11[i] = pref / (a1 * a1) * (2 * c11[-1] - c11[h2])
        Z22[i] = pref / (a2 * a2) * (2 * c22[-1] - c22[h2])
        Z12[i] = pref / (a1 * a2) * np.sum(eps * sign * I12)
        N0[:, i] = (pref / (a1 * a1) * I11[0], pref / (a1 * a2) * I12[0], pref / (a2 * a2) * I22[0])
    if return_n0:
        return Z11, Z12, Z22, N0
    return Z11, Z12, Z22


# ------------------------------------------------------------------------------------------ finite gap channel
def _disc(x):
    """Disc-average factor 2 J1(x)/x (-> 1 at x = 0)."""
    x = np.asarray(x, float)
    out = np.ones_like(x)
    m = x > 1e-9
    out[m] = 2 * sp.j1(x[m]) / x[m]
    return out


def rect_n0_dz(f, h, a1, a2, p1, p2, Lx, Lz, air=AIR, kc_a=14.0, nmom=6):
    """Finite gap channel: rigid-walled rectangle Lx x Lz (lid lip and clamp ribs as walls), discs a1 at p1 = (x, z) (lid bore exit)
    and a2 at p2 (board hole), both measured from a corner.  Returns dZ11, dZ12, dZ22 (Pa s/m^3) to ADD to gap_z(): the n = 0
    (uniform-across-the-gap) field of the rectangle minus that of the infinite plate pair, i.e. the wall reflections and the
    channel's own resonances.  Rectangle: Neumann modal sum  G = sum eps_m eps_n cos(a x) cos(b z) cos(a x') cos(b z') / (Lx Lz (K^2 - k^2)),
    disc average of each mode = cos(a x_c) cos(b z_c) 2 J1(K a)/(K a).  Infinite: (1/2 pi) int D_i D_j J0(q d) q dq / (q^2 - k^2).
    Both carry the same smooth window exp(-(K/kc)^4), kc = kc_a / min(a); terms with K above 5 k_max are summed as a power series in
    k^2 (moments), so the cost per frequency is only the low modes.  Lossy k from the slit (narrow.slit_eff); walls lossless (upper
    bound on the channel Q: parts, the lip's 0.7 mm under-gap and the board-edge leaks only add loss)."""
    f = np.atleast_1d(np.asarray(f, float))
    rho_e, C_e = slit_eff(f, h, air)
    k2 = (2 * np.pi * f) ** 2 * rho_e * C_e
    k1 = 5.0 * float(np.sqrt(k2).real.max())
    kc = kc_a / min(a1, a2)
    kend = 1.7 * kc
    m = np.arange(int(np.ceil(kend * Lx / np.pi)) + 1)
    n = np.arange(int(np.ceil(kend * Lz / np.pi)) + 1)
    if len(m) * len(n) > 3e6:     # memory guard (a 1 m test channel asked for 6e8 modes and hit the 3 GB fence, 2026-10-02)
        raise ValueError(f"channel {Lx * 1e3:.0f} x {Lz * 1e3:.0f} mm needs {len(m) * len(n):.1e} modes: lower kc_a or use the matched model")
    al, be = m * np.pi / Lx, n * np.pi / Lz
    K = np.hypot(al[:, None], be[None, :])
    keep = K <= kend
    em = np.where(m == 0, 1.0, 2.0)[:, None] * np.where(n == 0, 1.0, 2.0)[None, :]
    c1 = np.cos(al * p1[0])[:, None] * np.cos(be * p1[1])[None, :]
    c2 = np.cos(al * p2[0])[:, None] * np.cos(be * p2[1])[None, :]
    K, em, c1, c2 = K[keep], em[keep], c1[keep], c2[keep]
    W = np.exp(-(K / kc) ** 4) * em / (Lx * Lz)
    D1, D2 = _disc(K * a1), _disc(K * a2)
    A = np.stack([W * c1 * c1 * D1 * D1, W * c1 * c2 * D1 * D2, W * c2 * c2 * D2 * D2])      # (3, nmodes)
    lo = K < k1
    Klo, Alo = K[lo], A[:, lo]
    Khi2 = K[~lo] ** 2
    Mr = np.stack([np.sum(A[:, ~lo] / Khi2 ** (j + 1), axis=1) for j in range(nmom)])         # (nmom, 3)
    # infinite plate, same window
    d = float(np.hypot(p1[0] - p2[0], p1[1] - p2[1]))
    gl_x, gl_w = np.polynomial.legendre.leggauss(16)

    def panels(edges):
        q, w = [], []
        for a_, b_ in zip(edges[:-1], edges[1:]):
            if b_ > a_:
                q.append(0.5 * (b_ - a_) * gl_x + 0.5 * (b_ + a_))
                w.append(0.5 * (b_ - a_) * gl_w)
        return np.concatenate(q), np.concatenate(w)

    def kern(q):
        Wq = np.exp(-(q / kc) ** 4)
        d1, d2 = _disc(q * a1), _disc(q * a2)
        return np.stack([d1 * d1, d1 * d2 * sp.j0(q * d), d2 * d2]) * Wq * q / (2 * np.pi)     # (3, nq)
    qh, wh = panels(np.linspace(k1, kend, 241))
    Kh = kern(qh)
    Mi = np.stack([(Kh / qh ** (2 * (j + 1))) @ wh for j in range(nmom)])                     # (nmom, 3)
    dG = np.empty((3,) + f.shape, complex)
    for i, kk2 in enumerate(k2):
        kr = float(np.sqrt(kk2).real)
        fr = [0, .5, .8, .9, .95, .98, .99, .995, .998, .999, 1.0, 1.001, 1.002, 1.005, 1.01, 1.02, 1.05, 1.1, 1.2, 1.5, 2.0, 3.0]
        e = sorted({x * kr for x in fr if x * kr < k1} | {0.0, k1})
        e = sorted(set(e) | set(np.linspace(3.0 * kr, k1, 25)[1:]))
        q, wq = panels(np.array(e))
        g_inf = (kern(q) / (q ** 2 - kk2)) @ wq
        g_rect = Alo @ (1.0 / (Klo ** 2 - kk2))
        ser = np.array([kk2 ** j for j in range(nmom)])
        dG[:, i] = g_rect - g_inf + ser @ (Mr - Mi)
    pref = 1j * 2 * np.pi * f * rho_e / h
    return pref * dG[0], pref * dG[1], pref * dG[2]


def gap_abcd(f, h, a1, a2, delta, air=AIR, nmodes=64):
    Z11, Z12, Z22 = gap_z(f, h, a1, a2, delta, air, nmodes)
    T = np.empty(Z11.shape + (2, 2), complex)
    T[..., 0, 0] = Z11 / Z12
    T[..., 0, 1] = (Z11 * Z22 - Z12 * Z12) / Z12
    T[..., 1, 0] = 1.0 / Z12
    T[..., 1, 1] = Z22 / Z12
    return T
