"""Acoustic building blocks for the mic-port model: air, narrow-tube (Zwikker-Kosten / Kirchhoff) tubes
and slits, radiation impedance, end corrections, two-port (ABCD) algebra.

Convention: time dependence exp(+j w t); p = pressure (Pa), U = volume velocity (m^3/s); acoustic
impedance Z = p/U (Pa s / m^3).  Two-port: [p_in; U_in] = T [p_out; U_out], U positive in the
direction of propagation (into the next element).

Validity (state it, do not assume it):
 * Tube / slit sections are PLANE-WAVE (one mode): ka < 1.84 (first non-planar mode of a circular tube).
   For a = 0.3..1.0 mm that holds up to 96 kHz for a <= 1.0 mm (ka = 1.76 at a = 1.0 mm, 96 kHz, c 343),
   but the accuracy of a lumped end correction degrades as k*delta -> 1 (about 80 kHz for delta 0.4 mm).
 * Shear wavenumber s = a sqrt(w rho0 / mu) is 27..200 over 20..96 kHz for a = 0.3..1.0 mm: the thin
   boundary-layer regime (s >> 1).  The LOW-reduced-frequency (Zwikker-Kosten s < ~3, Poiseuille)
   approximation is INVALID here; the full Bessel (Kirchhoff) expressions below are used instead and
   reduce to the large-s expansion  k_c = k [1 + (1-j)/(sqrt(2) s) (1 + (gamma-1)/sqrt(Pr))].
 * Isothermal walls, no mean flow, linear acoustics (SPL << 140 dB at the mic port).
Sources: Zwikker & Kosten, Sound Absorbing Materials (1949); Tijdeman, J. Sound Vib. 39 (1975) 1-33;
Stinson, J. Acoust. Soc. Am. 89 (1991) 550-558; Kinsler & Frey ch. 7 (flanged piston); Karal, J. Acoust.
Soc. Am. 25 (1953) 327 (area-step end correction), Ingard, J. Acoust. Soc. Am. 25 (1953) 1037. Formulas
re-derived / numerically self-checked in sim/acoustics/selfcheck.py (none of those papers was opened
2026-10-02: the forms are standard and the self-checks cover limits only: label 'recalled').
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import special as sp


# ----------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Air:
    T: float = 293.15          # K
    P: float = 101325.0        # Pa
    gamma: float = 1.4
    Pr: float = 0.713
    cp: float = 1005.0
    Rs: float = 287.05

    @property
    def rho(self):
        return self.P / (self.Rs * self.T)

    @property
    def c(self):
        return float(np.sqrt(self.gamma * self.Rs * self.T))

    @property
    def mu(self):
        return 1.458e-6 * self.T ** 1.5 / (self.T + 110.4)     # Sutherland

    @property
    def kappa(self):
        return self.mu * self.cp / self.Pr


AIR = Air()


def _j1_over_j0(y):
    """J1(y)/J0(y) for complex y of any size (exponentially scaled Bessel: the scale cancels)."""
    return sp.jve(1, y) / sp.jve(0, y)


def tube_eff(f, a, air: Air = AIR):
    """Circular tube radius a (m): effective density rho_e(f), compressibility C_e(f) (1/Pa), shear wavenumber s."""
    w = 2 * np.pi * np.asarray(f, float)
    s = a * np.sqrt(w * air.rho / air.mu)
    y = s * np.exp(-1j * np.pi / 4)
    yt = y * np.sqrt(air.Pr)
    Fv = 2 * _j1_over_j0(y) / y
    Ft = 2 * _j1_over_j0(yt) / yt
    rho_e = air.rho / (1 - Fv)
    C_e = (1 + (air.gamma - 1) * Ft) / (air.gamma * air.P)
    return rho_e, C_e, s


def slit_eff(f, h, air: Air = AIR):
    """Parallel-plate slit of height h (m): effective density and compressibility (plane wave between plates)."""
    w = 2 * np.pi * np.asarray(f, float)
    g = 0.5 * h * np.sqrt(1j * w * air.rho / air.mu)
    gt = g * np.sqrt(air.Pr)
    rho_e = air.rho / (1 - np.tanh(g) / g)
    C_e = (1 + (air.gamma - 1) * np.tanh(gt) / gt) / (air.gamma * air.P)
    return rho_e, C_e


def tube_abcd(f, a, L, air: Air = AIR):
    """ABCD of a uniform lossy circular tube (radius a, length L).  Arrays over f: shape (nf, 2, 2)."""
    f = np.asarray(f, float)
    w = 2 * np.pi * f
    S = np.pi * a * a
    rho_e, C_e, _ = tube_eff(f, a, air)
    kc = w * np.sqrt(rho_e * C_e)
    Zc = np.sqrt(rho_e / C_e) / S
    T = np.empty(f.shape + (2, 2), complex)
    T[..., 0, 0] = np.cos(kc * L)
    T[..., 0, 1] = 1j * Zc * np.sin(kc * L)
    T[..., 1, 0] = 1j * np.sin(kc * L) / Zc
    T[..., 1, 1] = np.cos(kc * L)
    return T


def series_mass_abcd(f, a, delta, air: Air = AIR):
    """End correction as a series inertance of an equivalent length delta of the tube (radius a), with the
    tube's own viscous loss (effective density)."""
    f = np.asarray(f, float)
    w = 2 * np.pi * f
    S = np.pi * a * a
    rho_e, _, _ = tube_eff(f, a, air)
    Z = 1j * w * rho_e * delta / S
    return series_z_abcd(Z)


def series_z_abcd(Z):
    Z = np.asarray(Z, complex)
    T = np.zeros(Z.shape + (2, 2), complex)
    T[..., 0, 0] = 1
    T[..., 1, 1] = 1
    T[..., 0, 1] = Z
    return T


def shunt_y_abcd(Y):
    Y = np.asarray(Y, complex)
    T = np.zeros(Y.shape + (2, 2), complex)
    T[..., 0, 0] = 1
    T[..., 1, 1] = 1
    T[..., 1, 0] = Y
    return T


def cavity_y(f, V, air: Air = AIR, loss_tan=0.0):
    """Admittance of a small closed cavity (volume V m^3): adiabatic compliance V/(rho c^2), optional loss."""
    w = 2 * np.pi * np.asarray(f, float)
    C = V / (air.rho * air.c ** 2)
    return 1j * w * C * (1 - 1j * loss_tan)          # complex compliance C(1 - j eta): conductance +w C eta


def flanged_piston_z(f, a, air: Air = AIR):
    """Radiation impedance (acoustic) of a circular piston radius a in an infinite rigid baffle, any ka."""
    k = 2 * np.pi * np.asarray(f, float) / air.c
    x = 2 * k * a
    R = 1 - 2 * sp.j1(x) / x
    X = 2 * sp.struve(1, x) / x
    return air.rho * air.c / (np.pi * a * a) * (R + 1j * X)


def step_delta(a_small, a_big):
    """End correction (m) on the SMALL side of an abrupt area step into a larger tube (Karal 1953 form,
    delta/a = 0.8216 (1 - 1.347 alpha + 0.31 alpha^3), alpha = a_small/a_big; recalled, unverified; checked against
    the axisymmetric FEM in sim/acoustics/fem_axisym.py).  alpha -> 0 gives the flanged-orifice 0.8216 a."""
    al = np.minimum(a_small / a_big, 1.0)
    return 0.8216 * a_small * (1 - 1.347 * al + 0.31 * al ** 3)


def chain(*Ts):
    """Matrix product of ABCD arrays (all shape (nf,2,2)), left = source side."""
    out = Ts[0]
    for T in Ts[1:]:
        out = out @ T
    return out


def mesh_series(f, r_s, S_mesh, m_s=0.0):
    """Thin acoustic screen: specific resistance r_s (rayl = Pa s/m) and optional specific inertance m_s (kg/m2,
    ~ rho * (t + end corrections) / open-area fraction) over area S_mesh -> series R + j w M. m_s = 0 keeps the
    original resistance-only model (all results before 2026-10-07)."""
    w = 2 * np.pi * np.asarray(f, float)
    return series_z_abcd((r_s + 1j * w * m_s) / S_mesh + 0j * w)
