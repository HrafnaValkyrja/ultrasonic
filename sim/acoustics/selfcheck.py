"""Self-checks of the port model: analytic limits and the axisymmetric-FEM cross-check.

    python3 sim/acoustics/selfcheck.py [--fem-n N]      # fenced smoke: ~12 s, < 0.6 GB

Pass criteria are stated here and quoted in docs/sim/acoustics.yaml (selfchecks).
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "2")
import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from fem_axisym import Design, solve  # noqa: E402
from gap import _disc, gap_z, rect_n0_dz  # noqa: E402
from narrow import AIR, flanged_piston_z, slit_eff, step_delta, tube_eff  # noqa: E402
from port import Geom, Mic, Opt, db, transfer  # noqa: E402

CRIT = dict(fem_rms_below_60k_db=1.5, fem_max_below_60k_db=2.5, fem_rms_above_60k_db=3.0, asym_rel=2e-3, rad_rel=1e-3,
            gap_modes_rel=1e-3, gap_n0_quad_rel=1e-3, channel_vs_brute_rel=2e-3, channel_compliance_rel=0.01, channel_kc_rel=1e-4)


def check_narrow():
    out = {}
    f = np.array([20e3, 50e3, 96e3])
    worst = 0.0
    for a in (0.3e-3, 0.5e-3, 1.0e-3):
        rho_e, C_e, s = tube_eff(f, a)
        k = 2 * np.pi * f / AIR.c
        kc = 2 * np.pi * f * np.sqrt(rho_e * C_e)
        asym = k * (1 + (1 - 1j) / (np.sqrt(2) * s) * (1 + (AIR.gamma - 1) / np.sqrt(AIR.Pr)))
        worst = max(worst, float(np.max(np.abs(kc / asym - 1))))
    out["large_s_asymptote_max_rel_err"] = worst
    out["shear_wavenumber_range"] = [float(tube_eff(20e3, 0.3e-3)[2]), float(tube_eff(96e3, 1.0e-3)[2])]
    rho_e, _, s = tube_eff(50.0, 1e-5)                      # Poiseuille limit rho_e -> rho0 (4/3 + 8 mu/(j w rho a^2))
    ex = AIR.rho * (4 / 3 + 8 * AIR.mu / (1j * 2 * np.pi * 50.0 * AIR.rho * (1e-5) ** 2))
    out["poiseuille_limit_rel_err"] = float(abs(rho_e / ex - 1))
    z = flanged_piston_z(np.array([1.0]), 0.5e-3)[0] * np.pi * 0.25e-6 / (AIR.rho * AIR.c)   # ka -> 0: X = 8ka/(3 pi)
    ka = 2 * np.pi * 1.0 / AIR.c * 0.5e-3
    out["flanged_piston_lowka_X_rel_err"] = float(abs(z.imag / (8 * ka / (3 * np.pi)) - 1))
    out["step_delta_alpha0_over_a"] = float(step_delta(1e-3, 1e3) / 1e-3)          # 0.8216 (flanged orifice)
    return out


def check_gap():
    f = np.array([20e3, 50e3, 90e3])
    a = gap_z(f, 1.5e-3, 0.5e-3, 0.3e-3, 0.0, nmodes=64)
    b = gap_z(f, 1.5e-3, 0.5e-3, 0.3e-3, 0.0, nmodes=256)
    rel = max(float(np.max(np.abs(x / y - 1))) for x, y in zip(a, b))
    # radial-waveguide radiation resistance, low frequency, n=0 only: Re Z11 -> w rho / (4 h)
    z11 = gap_z(np.array([5e3]), 1.5e-3, 0.5e-3, 0.3e-3, 0.0)[0][0]
    ex = 2 * np.pi * 5e3 * AIR.rho / (4 * 1.5e-3)
    rho_e, C_e = slit_eff(np.array([5e3]), 1.5e-3)
    return dict(modes_64_vs_256_max_rel=rel, re_z11_vs_radial_wave_rel=float(abs(z11.real / ex - 1)))


def check_channel():
    """Finite gap channel (gap.rect_n0_dz): (1) n = 0 quadrature of gap_z vs a 32-point, +-0.1 %-panel reference; (2) hybrid
    (windowed difference + moments) vs a brute-force unwindowed modal sum to K = 120/a; (3) compliance limit at 100 Hz;
    (4) window convergence kc 14/a vs 24/a."""
    from scipy import special as sp
    from narrow import slit_eff
    h, a1, a2, dl = 1.5e-3, 0.5e-3, 0.3e-3, 0.77e-3
    Lx, Lz = 35.1e-3, 11.8e-3
    p1, p2 = (3.55e-3, 5.9e-3), (3.55e-3 - dl, 5.9e-3)
    f = np.array([300.0, 3e3, 20e3, 37e3, 63e3, 90e3])
    rho_e, C_e = slit_eff(f, h)
    k = 2 * np.pi * f * np.sqrt(rho_e * C_e)
    Z11, Z12, Z22, N0 = gap_z(f, h, a1, a2, dl, return_n0=True)
    gx, gw = np.polynomial.legendre.leggauss(32)
    q_err = 0.0
    for i, fi in enumerate(f[2:], start=2):
        kr = k[i].real
        e = np.unique(np.concatenate([kr * np.array([0, .5, .8, .9, .95, .98, .99, .995, .998, .999, 1, 1.001, 1.002, 1.005, 1.01, 1.02, 1.05, 1.1, 1.2, 1.5, 2, 3]),
                                      np.linspace(3 * kr, 200 / a2, 3000)]))
        q = np.concatenate([0.5 * (b - a) * gx + 0.5 * (b + a) for a, b in zip(e[:-1], e[1:])])
        w = np.concatenate([0.5 * (b - a) * gw for a, b in zip(e[:-1], e[1:])])
        base = w / q / (q ** 2 - k[i] ** 2)
        pref = 2j * 2 * np.pi * fi * rho_e[i] / (np.pi * h)
        ref = np.array([pref / a1 ** 2 * (base @ sp.j1(q * a1) ** 2), pref / (a1 * a2) * (base @ (sp.j1(q * a1) * sp.j1(q * a2) * sp.j0(q * dl))),
                        pref / a2 ** 2 * (base @ sp.j1(q * a2) ** 2)])
        q_err = max(q_err, float(np.max(np.abs(N0[:, i] / ref - 1))))
    d = np.array(rect_n0_dz(f, h, a1, a2, p1, p2, Lx, Lz))
    tot = N0 + d
    Kmax = 120 / a2
    m = np.arange(int(Kmax * Lx / np.pi) + 1)
    n = np.arange(int(Kmax * Lz / np.pi) + 1)
    G = np.zeros((3, len(f)), complex)
    for m0 in range(0, len(m), 200):
        mm = m[m0:m0 + 200]
        al, be = mm * np.pi / Lx, n * np.pi / Lz
        K = np.hypot(al[:, None], be[None, :])
        em = np.where(mm == 0, 1., 2.)[:, None] * np.where(n == 0, 1., 2.)[None, :]
        c1 = np.cos(al * p1[0])[:, None] * np.cos(be * p1[1])[None, :]
        c2 = np.cos(al * p2[0])[:, None] * np.cos(be * p2[1])[None, :]
        ok = K <= Kmax
        K, em, c1, c2 = K[ok], em[ok], c1[ok], c2[ok]
        D1, D2 = _disc(K * a1), _disc(K * a2)
        wgt = em / (Lx * Lz)
        A = np.stack([wgt * c1 * c1 * D1 * D1, wgt * c1 * c2 * D1 * D2, wgt * c2 * c2 * D2 * D2])
        G += A @ (1.0 / (K[:, None] ** 2 - (k ** 2)[None, :]))
    brute = 1j * 2 * np.pi * f * rho_e / h * G
    d24 = np.array(rect_n0_dz(f, h, a1, a2, p1, p2, Lx, Lz, kc_a=24.0))
    f0 = np.array([100.0])
    r0, c0 = slit_eff(f0, h)
    _, _, _, N00 = gap_z(f0, h, a1, a2, 0.0, return_n0=True)
    dd = rect_n0_dz(f0, h, a1, a2, p1, p1, Lx, Lz)
    comp = (N00[1] + dd[1])[0] * (1j * 2 * np.pi * 100.0 * Lx * Lz * h * c0[0])
    return dict(n0_quadrature_max_rel=q_err, hybrid_vs_brute_modal_max_rel=float(np.max(np.abs(brute / tot - 1))),
                compliance_limit_100hz_rel=float(abs(comp - 1)), kc14_vs_kc24_max_rel=float(np.max(np.abs((d24 - d) / tot))),
                z12_channel_over_matched_db={f"{fi / 1e3:g}k": round(float(20 * np.log10(abs(tot[1, i] / N0[1, i]))), 1) for i, fi in enumerate(f)})


def check_fem(n=10):
    """Lumped vs axisymmetric FEM (aligned designs, flat 0.3 mm front volume)."""
    g = Geom(a_recess=1.725e-3, a_bore=0.5e-3, l_bore=0.9e-3, d_recess=0.8e-3, h_gap=1.5e-3, t_board=0.8e-3, a_hole=0.3e-3,
             offset=0.0, a_port=0.15e-3, l_port=0.25e-3, a_ring=0.5e-3, t_standoff=0.05e-3)
    rf, hf = 0.9, 0.3
    mic = Mic(V_f=np.pi * (rf * 1e-3) ** 2 * hf * 1e-3, eta=0.11, r_front=rf * 1e-3)
    fr = np.geomspace(10e3, 100e3, n)
    cases = {
        "chimney_d1.0": (Design(gap="chimney", a_ch=0.5, r_front=rf, h_front=hf), Opt(gap="chimney", a_chim=0.5e-3)),
        "gasket_id2.1": (Design(gap="chimney", a_ch=1.05, r_front=rf, h_front=hf), Opt(gap="chimney", a_chim=1.05e-3)),
        "open_aligned (= as built, matched)": (Design(gap="open", r_front=rf, h_front=hf), Opt(gap="open")),
    }
    out = {}
    for name, (dd, oo) in cases.items():
        t = time.time()
        H, info = solve(dd, fr)
        Hl = transfer(fr, g, oo, mic)
        err = db(Hl) - db(H)
        m = fr < 60e3
        out[name] = dict(freqs_khz=[round(x / 1e3, 1) for x in fr], err_db=[round(float(x), 2) for x in err],
                         rms_below_60k=float(np.sqrt(np.mean(err[m] ** 2))), max_below_60k=float(np.abs(err[m]).max()),
                         rms_above_60k=float(np.sqrt(np.mean(err[~m] ** 2))), max_above_60k=float(np.abs(err[~m]).max()),
                         fem_s=round(time.time() - t, 1), ndof=info["ndof"], h_um=info["h_um"])
    return out


def main(argv=None):
    n = 10
    if argv and "--fem-n" in argv:
        n = int(argv[argv.index("--fem-n") + 1])
    t0 = time.time()
    res = dict(narrow=check_narrow(), gap=check_gap(), channel=check_channel(), fem=check_fem(n))
    n_ = res["narrow"]
    res["verdict"] = dict(
        narrow=bool(n_["large_s_asymptote_max_rel_err"] < CRIT["asym_rel"] and n_["poiseuille_limit_rel_err"] < 1e-3
                    and n_["flanged_piston_lowka_X_rel_err"] < CRIT["rad_rel"] * 10),
        gap=bool(res["gap"]["modes_64_vs_256_max_rel"] < CRIT["gap_modes_rel"] and res["gap"]["re_z11_vs_radial_wave_rel"] < 0.10),   # lossless formula; n = 0 carries rho_e: ~6 % expected at 5 kHz (exact check: channel.n0_quadrature)
        channel=bool(res["channel"]["n0_quadrature_max_rel"] < CRIT["gap_n0_quad_rel"] and res["channel"]["hybrid_vs_brute_modal_max_rel"] < CRIT["channel_vs_brute_rel"]
                     and res["channel"]["compliance_limit_100hz_rel"] < CRIT["channel_compliance_rel"] and res["channel"]["kc14_vs_kc24_max_rel"] < CRIT["channel_kc_rel"]),
        fem=bool(all(v["rms_below_60k"] < CRIT["fem_rms_below_60k_db"] and v["max_below_60k"] < CRIT["fem_max_below_60k_db"]
                     and v["rms_above_60k"] < CRIT["fem_rms_above_60k_db"] for v in res["fem"].values())))
    res["wall_s"] = round(time.time() - t0, 1)
    res["criteria"] = CRIT
    (HERE / "out").mkdir(exist_ok=True)
    (HERE / "out" / "selfcheck.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))
    return res


if __name__ == "__main__":
    main(sys.argv[1:])
