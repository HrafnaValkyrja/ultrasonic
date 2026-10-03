"""Bone-/cartilage-conduction path: coil -> exciter -> pad -> skin load -> perceived-level proxy.  Lumped mechanical network.

    exciter: moving mass m_m on suspension (k_s, c_s) inside housing; force Bl*I (reaction on the housing); back-EMF Bl*(v_m - v_h)
    housing + pad assembly: mass M_h; pad compliance K_p (complex, loss eta_p) in series with the skin / cartilage point impedance
    Z_L = R_L + j w M_L + K_L/(j w)  (series mass-spring-damper; Surendran 2023 measured values at the pre-tragal 'frontal' site)
    NiTi arm: infinite-beam resistance + weak spring to the pod, which is treated as ground at audio frequencies

Outputs: force on the skin F_L per ampere and per volt, skin velocity / acceleration, electrical |Z|, and a perceived-level
proxy SL = force level - threshold force level (re 1 uN) using published thresholds.  Every parameter has a range and a source
(PARAMS).  Sensitivity: Monte Carlo + standardised rank regression + one-at-a-time swings.

WHAT IT CAN / CANNOT PREDICT (plainly)
 can:   shape of F_L(f) over 0.25-16 kHz given a parameter set; which parameter dominates; the dB spread caused by the unknowns;
        how pad stiffness / housing mass / moving mass trade level against bandwidth; the expected electrical |Z| sweep so E1 can be fitted.
 cannot: absolute N/V (Bl, moving mass, f0 of the RC-BC02 are NOT published); pad material stiffness (Sugru / silicone: unmeasured);
        the owner's own tissue (point impedance varies several dB between people; static force 1 N vs the 2 N it was measured at);
        the cartilage-conduction (ear-canal radiation) path itself - it is only inside the measured threshold, not simulated;
        nonlinearity / contact loss above ~0.5 N peak force (D1: contact lost when vibration force exceeds static force); heat; hair.
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "2")
import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent

# ------------------------------------------------------------------------------------------------------------ parameters
# name: (nominal, lo, hi, scale, unit, status, source)
PARAMS = {
    "r_e":      (8.0, 8.0, 12.0, "discrete", "ohm", "vendor, disputed", "spec D7 L191: seller pages 8 ohm (12.5x5x3.5) vs 12 ohm (12.6x6x4); E1 measures"),
    "r_extra":  (1.52, 1.52, 1.52, "fixed", "ohm", "e2e", "docs/sim/e2e-chain.yaml exciter: r_pair 1.22 + r_wire 0.2 + r_shunt 0.1"),
    "l_e":      (0.5e-3, 0.3e-3, 1.3e-3, "log", "H", "assumed", "spec D7 L192: 0.3 mH placeholder; 1.26 mH published for the larger Adafruit 1674; E1"),
    "bl":       (1.0, 0.5, 2.0, "log", "N/A", "assumed", "not published. Anchor: Aeropex headset transducer 102 dB re 1 uN per 1 V flat <2 kHz (Surendran 2023 Fig 2B, read off the figure) = 0.126 N/V -> Bl/R ~ 0.1 N/(V) -> Bl ~ 1 N/A at 8 ohm"),
    "m_m":      (0.45e-3, 0.25e-3, 0.7e-3, "log", "kg", "assumed", "exciter total 1.2 g [Low] (reg-pad.md); moving magnet 20-60 % (guess); disassemble one sample to weigh"),
    "f0":       (350.0, 200.0, 800.0, "log", "Hz", "assumed", "vendor 'frequency 290/300-10000/19000 Hz' (low edge ~ f0 loaded); sibling RC-BC80B 'F0 140 Hz +-20 % without baffle', RC-BC29 100 Hz; e2e stub uses 800 Hz"),
    "q_m":      (3.0, 1.5, 8.0, "log", "-", "assumed", "mechanical Q of the free suspension (guess)"),
    "m_h":      (1.74e-3, 1.2e-3, 2.2e-3, "lin", "kg", "CAD", "pad assembly 2.19 g (reg-pad.md checks.json) minus moving mass; exciter mass itself [Low]"),
    "k_p":      (1.0e6, 1.0e5, 1.0e7, "log", "N/m", "assumed", "1 mm silicone/Sugru face: E 0.7-3 MPa (Shore A 30-50), area 50-150 mm2, shape-factor stiffening x3-9 -> 1e5..1e7 N/m; unmeasured"),
    "eta_p":    (0.2, 0.05, 0.5, "log", "-", "assumed", "loss factor of silicone rubber 1-4 kHz, typical 0.1-0.3 (unverified)"),
    "k_l":      (2.5e4, 1.2e4, 6.0e4, "log", "N/m", "measured (Surendran 2023)", "frontal site compliance 40 um/N at 2 N static force = 2.5e4 N/m; 8 um/N (1.25e5) at the mastoid; lower static force -> softer (Bekesy via Henry&Letowski 2007 s5.2)"),
    "m_l":      (1.1e-3, 0.6e-3, 1.5e-3, "lin", "kg", "measured (Surendran 2023)", "impedance of a pure 1.1 g mass above 2 kHz at both sites; Flottorp&Solberg 1976 skin M_S 0.6 g (via Henry&Letowski 2007 s3.4)"),
    "r_l":      (10.0, 4.0, 25.0, "log", "N s/m", "read from figure", "min of |Z| at ~0.7-1 kHz on Surendran Fig 2A (frontal, 2 N) ~ 8-10 N s/m; Flottorp&Solberg R_S 20 N s/m (skin)"),
    "z_arm":    (1.0, 0.3, 3.0, "log", "N s/m", "derived [Low]", "infinite-beam bending-wave resistance of the 0.85 mm NiTi wire at 3 kHz: 2 m' c_b = 0.74 N s/m (E 41 GPa, rho 6450); finite 20 mm wire not modelled"),
    "k_arm":    (250.0, 100.0, 600.0, "log", "N/m", "tragus-arm.md", "1 N per ~4 mm travel (NiTi arm B)"),
}


# ---- one source with the other sims: docs/sim/shared-params.yaml#exciter (nominal/lo/hi) and #thresholds. The shared file WINS;
# a disagreement with the table above is printed (drift = someone edited one side only). Integrator 2026-10-02.
def _apply_shared():
    import yaml  # noqa: PLC0415
    sh = yaml.safe_load((HERE.parents[1] / "docs/sim/shared-params.yaml").read_text())
    ex = sh["exciter"]
    keymap = {"r_e": "r_e_ohm", "l_e": "l_e_h", "bl": "bl_n_per_a", "m_m": "m_m_kg", "f0": "f0_hz", "q_m": "q_m"}
    for k, sk in keymap.items():
        nom, lo, hi, *rest = PARAMS[k]
        new = (ex[sk]["nom"], ex[sk]["lo"], ex[sk]["hi"])
        if any(abs(a - b) > 1e-12 * max(abs(a), 1.0) for a, b in zip((nom, lo, hi), new)):
            print(f"bone.py: PARAMS[{k}] {(nom, lo, hi)} != shared-params {new}: using shared-params", file=sys.stderr)
        PARAMS[k] = (*new, *rest)
    r_loop = ex["r_loop_ohm"]["nom"]
    PARAMS["r_extra"] = (r_loop, r_loop, r_loop, *PARAMS["r_extra"][3:])
    return sh["thresholds"]


_SHARED_THR = _apply_shared()


def draw(n, rng, fixed=None):
    out = {}
    for k, (nom, lo, hi, sc, *_r) in PARAMS.items():
        if sc == "fixed":
            out[k] = np.full(n, nom)
        elif sc == "discrete":
            out[k] = rng.choice([lo, hi], n)
        elif sc == "log":
            out[k] = np.exp(rng.uniform(np.log(lo), np.log(hi), n))
        else:
            out[k] = rng.uniform(lo, hi, n)
    if fixed:
        for k, v in fixed.items():
            out[k] = np.full(n, v)
    return out


def nominal():
    return {k: np.array([v[0]]) for k, v in PARAMS.items()}


# ------------------------------------------------------------------------------------------------------------ network
def solve(f, p, pad_k_scale=1.0):
    """Per ampere (I = 1 A phasor).  f: (nf,), p: dict of (N,) arrays.  Returns dict of (N, nf) complex arrays."""
    f = np.asarray(f, float)[None, :]
    w = 2 * np.pi * f
    jw = 1j * w
    g = lambda k: p[k][:, None]  # noqa: E731
    k_s = g("m_m") * (2 * np.pi * g("f0")) ** 2
    c_s = g("m_m") * 2 * np.pi * g("f0") / g("q_m")
    Zs = c_s + k_s / jw
    Zp = g("k_p") * pad_k_scale * (1 + 1j * g("eta_p")) / jw
    ZL = g("r_l") + jw * g("m_l") + g("k_l") / jw
    Zhl = 1.0 / (1.0 / Zp + 1.0 / ZL)
    Zarm = g("z_arm") + g("k_arm") / jw
    bl = g("bl")
    # [Zs + jw m_m, -Zs; -Zs, Zs + jw M_h + Zarm + Zhl] [v_m; v_h] = [Bl; -Bl]
    a11 = Zs + jw * g("m_m")
    a12 = -Zs
    a22 = Zs + jw * g("m_h") + Zarm + Zhl
    det = a11 * a22 - a12 * a12
    vm = (bl * a22 - a12 * (-bl)) / det
    vh = (a11 * (-bl) - a12 * bl) / det
    FL = Zhl * vh
    vL = FL / ZL
    Zin_per_I = g("r_e") + g("r_extra") + jw * g("l_e") + bl * (vm - vh)      # V per A at I = 1 A
    return dict(F_per_A=FL, vL_per_A=vL, Z_in=Zin_per_I, vh_per_A=vh, vm_per_A=vm, Zhl=Zhl, ZL=ZL, Zp=Zp, f=f[0])


def free_exciter_z(f, p):
    """Electrical |Z| of the exciter hanging free (no pad, no load, no arm): what E1's free sweep sees. Housing = exciter mass 1.2 g."""
    f = np.asarray(f, float)[None, :]
    w = 2 * np.pi * f
    jw = 1j * w
    g = lambda k: p[k][:, None]  # noqa: E731
    m_x = 1.2e-3 - g("m_m")
    k_s = g("m_m") * (2 * np.pi * g("f0")) ** 2
    c_s = g("m_m") * 2 * np.pi * g("f0") / g("q_m")
    Zs = c_s + k_s / jw
    bl = g("bl")
    a11 = Zs + jw * g("m_m")
    a22 = Zs + jw * m_x
    det = a11 * a22 - Zs * Zs
    vm = (bl * a22 - (-Zs) * (-bl)) / det
    vh = (a11 * (-bl) - (-Zs) * bl) / det
    return g("r_e") + jw * g("l_e") + bl * (vm - vh)


def clamped_exciter_z(f, p):
    f = np.asarray(f, float)[None, :]
    return p["r_e"][:, None] + 1j * 2 * np.pi * f * p["l_e"][:, None]


def to_per_volt(res):
    """Per volt of BRIDGE differential drive (the PWM-average voltage; r_extra = bridge switches + wires + shunt in series)."""
    I_per_V = 1.0 / res["Z_in"]
    return res["F_per_A"] * I_per_V, res["vL_per_A"] * I_per_V


def to_per_volt_terminal(res, p):
    """Per volt measured ACROSS THE EXCITER TERMINALS (what E2's scope reads): Z_in minus r_extra."""
    return res["F_per_A"] / (res["Z_in"] - p["r_extra"][:, None])


# ------------------------------------------------------------------------------------------------------------ shaped PWM noise (T6)
FS_PWM, PWM_LEVELS, V_BRIDGE = 200e3, 201, 3.0     # spec D6 (ARR 200 at 80 MHz, 2-level AD), +3V0 bridge rail (sub-output.md)
NTF_ZERO_PAIR_HZ = 13e3                            # spec D6 L176: 3rd order, one DC zero + zero pair near 13 kHz


def shaped_noise_v_psd(f):
    """One-sided PSD (V^2/Hz) of the bridge differential voltage noise of the error-feedback shaper with TPDF dither:
    |NTF|^2 * (step^2/4) / (fs/2) * Vdd^2 (error variance = rounding step^2/12 + TPDF dither step^2/6).  Reproduces
    sim/checks/ntf_compare.py band powers to 0.4 dB (-92.7 / -90.2 / -70.6 vs sim -92.7 / -90.6 / -71.4 dB re FS, 2026-10-02)."""
    w = 2 * np.pi * np.asarray(f, float) / FS_PWM
    c = np.cos(2 * np.pi * NTF_ZERO_PAIR_HZ / FS_PWM)
    z1 = np.exp(-1j * w)
    ntf = (1 - z1) * (1 - 2 * c * z1 + z1 ** 2)
    step = 2.0 / (PWM_LEVELS - 1)
    return np.abs(ntf) ** 2 * (step ** 2 / 4) / (FS_PWM / 2) * V_BRIDGE ** 2


def erb_hz(f):
    """Equivalent rectangular bandwidth, Glasberg & Moore 1990 (Hear Res 47:103): 24.7 (4.37 f/kHz + 1) Hz (recalled)."""
    return 24.7 * (4.37 * np.asarray(f, float) / 1000 + 1)


def noise_force_per_erb_db(f, FV):
    """Force level (dB re 1 uN) of the shaped noise inside one ERB at f, given complex force per bridge volt FV(f)."""
    return 10 * np.log10(shaped_noise_v_psd(f) * erb_hz(f) * np.abs(FV) ** 2 / 1e-12 + 1e-30)


# ------------------------------------------------------------------------------------------------------------ thresholds
# Published bone-conduction thresholds, force level dB re 1 uN, third-octave frequencies (Hz).
F_THR = np.array([250, 315, 400, 500, 630, 800, 1000, 1250, 1600, 2000, 2500, 3150, 4000, 5000, 6300, 8000, 10000, 12500], float)
# ANSI S3.6-1996 / ISO 389-3 mastoid RETFL (B-71 on the IEC 60318-6 coupler), via Henry & Letowski 2007 ARL-TR-4138 Table 8 (opened 2026-10-02): 250..8000 Hz
_RETFL_F = np.array([250, 315, 400, 500, 630, 750, 800, 1000, 1250, 1500, 1600, 2000, 2500, 3000, 3150, 4000, 5000, 6000, 6300, 8000], float)
_RETFL_M = np.array([67.0, 64.0, 61.0, 58.0, 52.5, 48.5, 47.0, 42.5, 39.0, 36.5, 35.5, 31.0, 29.5, 30.0, 31.0, 35.5, 40.0, 40.0, 40.0, 40.0])
# Surendran, Prodanovic & Stenfelt, Trends Hear 27 (2023), Fig 4A (n = 21, ipsilateral, median, Aeropex headset ~2 N, 'frontal' = in front of the ear
# canal opening): read from the figure image by pixel digitising, +-2 dB reading error; inter-subject SD about +-6-9 dB (error bars)
_FRONT_F = np.array([250, 315, 400, 500, 630, 800, 1000, 1250, 1600, 2000, 2500, 3150, 4000, 5000, 6300, 8000, 10000, 12500], float)
_FRONT_T = np.array([36.0, 36.5, 34.0, 31.7, 31.0, 30.6, 29.2, 29.8, 31.6, 33.7, 34.5, 30.0, 29.5, 28.3, 30.5, 30.0, 33.0, 47.0])
# shared-params#thresholds wins (same numbers on 2026-10-02; a mismatch is printed)
for _a, _key in ((_RETFL_M, "retfl_mastoid"), (_FRONT_T, "front_measured")):
    _sv = np.array(_SHARED_THR[_key]["db"], float)
    if _sv.shape != _a.shape or np.max(np.abs(_sv - _a)) > 1e-9:
        print(f"bone.py: threshold table {_key} differs from shared-params: using shared-params", file=sys.stderr)
    _a[:] = _sv if _sv.shape == _a.shape else _a
_MAST_T = np.array([64.5, 71.6, 73.5, 76.0, 70.0, 61.0, 55.5, 50.0, 49.8, 50.0, 49.0, 50.0, 55.0, 53.0, 50.0, 48.2, 52.0, 55.0])


def retfl_mastoid(f):
    return np.interp(np.log(f), np.log(_RETFL_F), _RETFL_M)


def thr_front_measured(f):
    return np.interp(np.log(f), np.log(_FRONT_F), _FRONT_T)


def thr_front_norm_minus(f, gain_db=20.0):
    """e2e proxy convention: ISO mastoid RETFL minus a 'tragus gain' (Surendran: 20 dB typical, 10-40)."""
    return retfl_mastoid(f) - gain_db


def level_db_re_1uN(F):
    return 20 * np.log10(np.abs(F) / 1e-6 + 1e-30)


# ------------------------------------------------------------------------------------------------------------ analysis
FGRID = np.geomspace(250.0, 16000.0, 160)
PROBE = np.array([1500.0, 2000.0, 2500.0, 3000.0, 4000.0])


def monte_carlo(n=2000, seed=3, f=PROBE):
    rng = np.random.default_rng(seed)
    p = draw(n, rng)
    res = solve(f, p)
    FV, vL = to_per_volt(res)
    return p, FV


def srrc(p, y):
    """Standardised rank regression coefficients of y (N,) on the (log-)parameters: share of variance and sign."""
    from scipy.stats import rankdata
    names = [k for k, v in PARAMS.items() if v[3] != "fixed"]
    X = np.column_stack([rankdata(p[k]) for k in names])
    X = (X - X.mean(0)) / X.std(0)
    yy = rankdata(y)
    yy = (yy - yy.mean()) / yy.std()
    beta, *_ = np.linalg.lstsq(X, yy, rcond=None)
    return dict(zip(names, beta))


def tornado(f_probe, metric="F_per_V"):
    out = []
    nom = nominal()
    base = to_per_volt(solve(f_probe, nom))[0]
    base_db = 20 * np.log10(np.abs(base[0]))
    for k, (v0, lo, hi, sc, unit, status, src) in PARAMS.items():
        if sc == "fixed":
            continue
        row = dict(param=k, lo=lo, hi=hi, unit=unit)
        for tag, val in (("lo", lo), ("hi", hi)):
            p = {kk: vv.copy() for kk, vv in nom.items()}
            p[k] = np.array([val])
            FV = to_per_volt(solve(f_probe, p))[0]
            row["d_" + tag] = (20 * np.log10(np.abs(FV[0])) - base_db).tolist()
        out.append(row)
    return base_db.tolist(), out


def run(out_dir=HERE / "out", n=2000, plot=True):
    sys.path.insert(0, str(HERE.parents[1] / "tools"))
    t_nom = nominal()
    res = solve(FGRID, t_nom)
    FV, vL = to_per_volt(res)
    FA = res["F_per_A"]
    rng = np.random.default_rng(3)
    p = draw(n, rng)
    r = solve(FGRID, p)
    FV_mc, vL_mc = to_per_volt(r)
    FA_mc = r["F_per_A"]
    dbv = 20 * np.log10(np.abs(FV_mc))
    dba = 20 * np.log10(np.abs(FA_mc))
    pr = lambda a, q: np.percentile(a, q, axis=0)  # noqa: E731
    probe_idx = [int(np.argmin(np.abs(FGRID - fp))) for fp in PROBE]
    # headline: force level at 1 V rms drive, probe frequencies
    head = {}
    for fp, i in zip(PROBE, probe_idx):
        col = dbv[:, i]
        fl = level_db_re_1uN(FV[0, i])
        head[f"{int(fp)}Hz"] = dict(F_per_V_mN=float(abs(FV[0, i]) * 1e3), F_level_db_re_1uN_per_V=float(fl),
                                    p05=float(np.percentile(col, 5)) + 120.0, p95=float(np.percentile(col, 95)) + 120.0,
                                    min=float(col.min()) + 120.0, max=float(col.max()) + 120.0,
                                    thr_front_measured_db=float(thr_front_measured(fp)), thr_front_norm_minus20_db=float(thr_front_norm_minus(fp)),
                                    SL_per_V_measured_nom=float(fl - thr_front_measured(fp)), SL_per_V_norm_nom=float(fl - thr_front_norm_minus(fp)),
                                    V_at_threshold_mV_measured_nom=float(10 ** ((thr_front_measured(fp) - fl) / 20) * 1e3),
                                    V_at_threshold_mV_range=[float(10 ** ((thr_front_norm_minus(fp) - (np.percentile(col, 95) + 120.0)) / 20) * 1e3),
                                                             float(10 ** ((thr_front_measured(fp) - (np.percentile(col, 5) + 120.0)) / 20) * 1e3)])
    # sensitivity
    sens = {}
    for fp, i in zip(PROBE, probe_idx):
        c = srrc(p, dbv[:, i])
        sens[f"{int(fp)}Hz"] = {k: float(v) for k, v in sorted(c.items(), key=lambda kv: -abs(kv[1]))}
    tb = {}
    for fp in (2000.0, 3000.0):
        base, rows = tornado(np.array([fp]))
        tb[f"{int(fp)}Hz"] = dict(base_db_re_1N_per_V=base[0], rows=rows)
    # design levers: pad stiffness; static force (skin stiffness K_L ~ F^alpha, alpha unknown); drive at the D17 ceiling
    lever = {}
    fl = np.array([1500.0, 2000.0, 3000.0, 4000.0])
    for kp in (1e5, 3e5, 1e6, 3e6, 1e7):
        pp = nominal()
        pp["k_p"] = np.array([kp])
        lever[f"k_p={kp:.0e}"] = [round(float(level_db_re_1uN(to_per_volt(solve(fl, pp))[0][0, i])), 1) for i in range(len(fl))]
    force_sw = {}
    for F in (0.5, 1.0, 2.0):
        for alpha in (0.5, 1.0):
            pp = nominal()
            pp["k_l"] = pp["k_l"] * (F / 2.0) ** alpha
            force_sw[f"F={F}N,alpha={alpha}"] = [round(float(level_db_re_1uN(to_per_volt(solve(fl, pp))[0][0, i])), 1) for i in range(len(fl))]
    v_ceiling_rms = 3.0 * 10 ** (-12 / 20) / np.sqrt(2)
    ceiling = {}
    for fp, i in zip(PROBE, probe_idx):
        fl_ = float(level_db_re_1uN(FV[0, i])) + 20 * np.log10(v_ceiling_rms)
        ceiling[f"{int(fp)}Hz"] = dict(force_level_db_re_1uN=fl_, peak_force_mN=float(abs(FV[0, i]) * v_ceiling_rms * np.sqrt(2) * 1e3),
                                       SL_measured_front_thr=fl_ - float(thr_front_measured(fp)), SL_norm_minus20=fl_ - float(thr_front_norm_minus(fp)))
    # shaped PWM noise while the output runs un-squelched (dither on): force per ERB vs threshold (T6, R21)
    fn = FGRID
    nf_nom = noise_force_per_erb_db(fn, FV[0])
    nf_p95 = 10 * np.log10(shaped_noise_v_psd(fn) * erb_hz(fn) / 1e-12) + pr(dbv, 95)
    t6 = dict(what="shaped PWM quantisation noise (TPDF dither on, i.e. output active but no signal), force inside one ERB vs pure-tone threshold; "
                   "detectable when > 0 dB (critical-band power summation, assumed)",
              src="noise: spec D6 L176-L178 shaper (ntf_poly(1,[13e3]), 201 levels, 200 kHz, 3.0 V) as shaped_noise_v_psd(); thresholds as below",
              f_hz=[round(float(x), 1) for x in fn], noise_force_per_erb_db_re_1uN_nominal=[round(float(x), 2) for x in nf_nom],
              noise_force_per_erb_db_re_1uN_p95=[round(float(x), 2) for x in nf_p95])
    for lab, thr in (("measured_front", thr_front_measured(fn)), ("norm_minus20", thr_front_norm_minus(fn))):
        for tag, nf in (("nominal", nf_nom), ("p95", nf_p95)):
            sl = nf - thr
            for bname, (lo_, hi_) in (("1.5_4k", (1500, 4000)), ("4_12.5k", (4000, 12500)), ("0.25_1.5k", (250, 1500)), ("12.5_16k_thr_held", (12500, 16000))):
                m = (fn >= lo_) & (fn <= hi_)
                i = int(np.argmax(np.where(m, sl, -1e9)))
                t6[f"SL_max_{lab}_{tag}_{bname}"] = dict(db=round(float(sl[i]), 1), at_hz=round(float(fn[i])))
    # electrical |Z| predictions for E1 (nominal and spread)
    fz = np.geomspace(50, 20000, 120)
    Zfree = np.abs(free_exciter_z(fz, p))
    Zclamp = np.abs(clamped_exciter_z(fz, p))
    Zskin = np.abs(solve(fz, p)["Z_in"])
    bump = Zfree - Zclamp
    ib = np.argmax(bump, axis=1)
    bump_max = bump[np.arange(len(ib)), ib]
    Zsk = solve(fz, p)["Z_in"]
    loaded_pk = fz[np.argmax(np.abs(Zsk) - np.abs(p["r_e"][:, None] + p["r_extra"][:, None] + 1j * 2 * np.pi * fz[None, :] * p["l_e"][:, None]), axis=1)]
    e1 = dict(def_="motional bump = max over f of |Z_free| - |R_e + jw L_e| (free exciter hung by its leads); = Bl^2 / c_s at the suspension resonance",
              bump_ohm_p05_p50_p95=[round(float(x), 2) for x in np.percentile(bump_max, [5, 50, 95])],
              bump_freq_hz_p05_p50_p95=[round(float(x)) for x in np.percentile(fz[ib], [5, 50, 95])],
              loaded_on_skin_peak_hz_p05_p50_p95=[round(float(x)) for x in np.percentile(loaded_pk, [5, 50, 95])],
              bl_from_bump="Bl = sqrt(bump * c_s), c_s = 2 pi f0 m_m / Q_m: needs m_m (weigh the moving magnet) and Q_m (bump width)")
    zsum = dict(e1_expectation=e1, f_hz=[round(float(x), 1) for x in fz],
                free_p05=[round(float(x), 3) for x in pr(Zfree, 5)], free_p50=[round(float(x), 3) for x in pr(Zfree, 50)], free_p95=[round(float(x), 3) for x in pr(Zfree, 95)],
                clamped_p50=[round(float(x), 3) for x in pr(Zclamp, 50)], on_skin_p05=[round(float(x), 3) for x in pr(Zskin, 5)],
                on_skin_p50=[round(float(x), 3) for x in pr(Zskin, 50)], on_skin_p95=[round(float(x), 3) for x in pr(Zskin, 95)])
    # IF-BONE-TF
    ftf = FGRID
    tf = dict(schema="IF-BONE-TF v1 (docs/sim/e2e-chain.yaml interfaces)", date="2026-10-02",
              ref="coil current (A) -> force on the skin (N rms per A rms) through exciter, pad, skin/cartilage point impedance; and per volt at the exciter terminals "
                  "(r_extra 1.52 ohm included). Absolute level NOT measured: bands are the parameter ranges in PARAMS (Monte Carlo, n=%d)." % n,
              f_hz=[round(float(x), 2) for x in ftf],
              mag_db_n_per_a=[round(float(x), 3) for x in 20 * np.log10(np.abs(FA[0]))],
              mag_db_n_per_a_p05=[round(float(x), 3) for x in pr(dba, 5)], mag_db_n_per_a_p95=[round(float(x), 3) for x in pr(dba, 95)],
              mag_db_n_per_a_min=[round(float(x), 3) for x in dba.min(0)], mag_db_n_per_a_max=[round(float(x), 3) for x in dba.max(0)],
              phase_deg=[round(float(x), 2) for x in np.degrees(np.unwrap(np.angle(FA[0])))],
              mag_db_n_per_v=[round(float(x), 3) for x in 20 * np.log10(np.abs(FV[0]))],
              mag_db_n_per_v_p05=[round(float(x), 3) for x in pr(dbv, 5)], mag_db_n_per_v_p95=[round(float(x), 3) for x in pr(dbv, 95)],
              mag_db_n_per_v_min=[round(float(x), 3) for x in dbv.min(0)], mag_db_n_per_v_max=[round(float(x), 3) for x in dbv.max(0)],
              thr_front_measured_db_re_1uN=[round(float(x), 2) for x in thr_front_measured(ftf)],
              thr_front_norm_minus20_db_re_1uN=[round(float(x), 2) for x in thr_front_norm_minus(ftf)],
              cond=dict(force_n=1.0, per_volt='bridge drive (r_extra included)', pad="1 mm silicone/Sugru face, K_p 1e5..1e7 N/m", site="pre-tragal ('frontal' of Surendran 2023), skin-over-cartilage/bone point impedance",
                        nominal={k: float(v[0]) for k, v in nominal().items()}, ranges={k: [v[1], v[2]] for k, v in PARAMS.items()}),
              level_scale_note="the e2e MechBone currently uses F = Bl*i*H with Bl = 1.41 N/A; this file's nominal Bl is 1.0 N/A (assumed): replace Bl*H by 10^(mag_db_n_per_a/20)")
    (out_dir / "bone_tf.json").write_text(json.dumps(tf))
    FVt = to_per_volt_terminal(res, t_nom)
    r_mc = r
    FVt_mc = 20 * np.log10(np.abs(to_per_volt_terminal(r_mc, p)))
    for fp, i in zip(PROBE, probe_idx):
        head[f"{int(fp)}Hz"].update(F_per_V_terminal_mN=float(abs(FVt[0, i]) * 1e3), F_level_db_re_1uN_per_V_terminal=float(level_db_re_1uN(FVt[0, i])),
                                    terminal_p05=float(np.percentile(FVt_mc[:, i], 5)) + 120.0, terminal_p95=float(np.percentile(FVt_mc[:, i], 95)) + 120.0,
                                    V_terminal_at_threshold_mV_measured_nom=float(10 ** ((thr_front_measured(fp) - level_db_re_1uN(FVt[0, i])) / 20) * 1e3))
    summary = dict(date="2026-10-02", n_mc=n, per_volt_note="headline F_per_V* = per volt of bridge drive (1.52 ohm bridge+wire+shunt in series); "
                   "*_terminal = per volt across the exciter terminals (E2 reads this)", headline_per_volt=head, srrc=sens, tornado=tb, zin=zsum, t6_shaped_noise=t6,
                   levers=dict(freqs_hz=fl.tolist(), pad_stiffness_db_re_1uN_per_V=lever, static_force_db_re_1uN_per_V=force_sw,
                               ceiling_minus12dBFS=dict(v_rms=float(v_ceiling_rms), by_freq=ceiling)),
                   load_check=dict(
                       ZL_abs_Ns_per_m={str(fp): float(abs(solve(np.array([fp]), t_nom)["ZL"][0, 0])) for fp in (500.0, 1000.0, 2000.0, 3000.0, 4000.0)},
                       surendran_mass_1p1g_Ns_per_m={str(fp): float(2 * np.pi * fp * 1.1e-3) for fp in (500.0, 1000.0, 2000.0, 3000.0, 4000.0)}),
                   aeropex_anchor=dict(db_re_1uN_per_V={"500": 101.5, "1000": 102.5, "2000": 100.5, "3000": 96.0, "4000": 91.0, "5000": 89.0},
                                       src="Surendran 2023 Fig 2B blue curve, read off the figure (+-1.5 dB), B&K 4930 artificial mastoid, 1 V at the transducer"),
                   ours_nominal_db_re_1uN_per_V={str(int(fp)): float(level_db_re_1uN(FV[0, i])) for fp, i in zip(PROBE, probe_idx)})
    (out_dir / "bone_results.json").write_text(json.dumps(summary, indent=1))
    if plot:
        import matplotlib.pyplot as plt
        import plotstyle
        plotstyle.apply()
        S = plotstyle.SERIES
        fig, ax = plt.subplots(1, 2, figsize=(11, 4.4))
        L = lambda x: 20 * np.log10(np.abs(x) / 1e-6)  # noqa: E731
        ax[0].fill_between(ftf / 1e3, 120 + pr(dbv, 5), 120 + pr(dbv, 95), color=S[1], alpha=0.2, lw=0, label="5-95 % of parameter ranges")
        ax[0].plot(ftf / 1e3, L(FV[0]), color=S[1], label="nominal")
        aer_f = np.array([0.5, 1, 2, 3, 4, 5]) * 1e3
        ax[0].plot(aer_f / 1e3, [101.5, 102.5, 100.5, 96, 91, 89], "o--", color=S[2], ms=3, label="Aeropex transducer (published, artificial mastoid)")
        ax[0].set_xscale("log")
        ax[0].set_xlabel("kHz")
        ax[0].set_ylabel("force on skin, dB re 1 uN per 1 V rms")
        ax[0].legend(fontsize=7)
        ax[0].axvspan(1.5, 4, color=plotstyle.TEXT_2, alpha=0.08)
        ax[1].semilogx(ftf / 1e3, thr_front_measured(ftf), color=S[0], label="threshold, front site (Surendran 2023 Fig 4A)")
        ax[1].semilogx(ftf / 1e3, thr_front_norm_minus(ftf), color=S[3], label="ISO/ANSI mastoid RETFL minus 20 dB (e2e proxy)")
        ax[1].semilogx(ftf / 1e3, retfl_mastoid(ftf), color=S[4], ls=":", label="ISO/ANSI mastoid RETFL")
        ax[1].semilogx(fn / 1e3, nf_nom, color=S[2], label="PWM shaper noise per ERB, nominal exciter")
        ax[1].semilogx(fn / 1e3, nf_p95, color=S[2], ls="--", label="same, loudest 5 % of exciters")
        ax[1].set_xlabel("kHz")
        ax[1].set_ylabel("force level, dB re 1 uN")
        ax[1].set_title("hearing threshold vs the output's own noise (below the lines = inaudible)", fontsize=8)
        ax[0].set_title("force on the skin per volt of drive (band = the exciter's unknown specs)", fontsize=8)
        ax[1].legend(fontsize=7)
        fig.tight_layout()
        fig.savefig(out_dir / "bone_force.png", dpi=110)
        plt.close(fig)
        fig, ax = plt.subplots(1, 2, figsize=(11, 4.4))
        for key, col, lab in (("free_p50", S[0], "free in air (E1 sweep 1)"), ("clamped_p50", S[3], "clamped (E1 sweep 2) = R + jwL"), ("on_skin_p50", S[1], "on the tragus (E1 sweep 3)")):
            ax[0].semilogx(fz / 1e3, zsum[key], color=col, label=lab)
        ax[0].fill_between(fz / 1e3, zsum["free_p05"], zsum["free_p95"], color=S[0], alpha=0.15, lw=0)
        ax[0].fill_between(fz / 1e3, zsum["on_skin_p05"], zsum["on_skin_p95"], color=S[1], alpha=0.15, lw=0)
        ax[0].set_xlabel("kHz")
        ax[0].set_ylabel("|Z| ohm (nominal + 5-95 %)")
        ax[0].legend(fontsize=7)
        names = list(sens["2000Hz"].keys())
        y = np.arange(len(names))
        ax[1].barh(y - 0.2, [sens["2000Hz"][k] for k in names], 0.4, color=S[1], label="2 kHz")
        ax[1].barh(y + 0.2, [sens["4000Hz"][k] for k in names], 0.4, color=S[0], label="4 kHz")
        ax[1].set_yticks(y)
        ax[1].set_yticklabels(names, fontsize=7)
        ax[1].invert_yaxis()
        ax[1].set_xlabel("rank-regression coefficient on force/V (dB)")
        ax[1].legend(fontsize=7)
        fig.tight_layout()
        fig.savefig(out_dir / "bone_sensitivity.png", dpi=110)
        plt.close(fig)
    return summary


if __name__ == "__main__":
    s = run()
    print(json.dumps(s["headline_per_volt"], indent=1)[:3000])
