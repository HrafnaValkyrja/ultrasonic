"""Deep inward preload for the NiTi pad arm, with the glasses' own give in series (2026-09-30).

Owner's idea: tilt the arm INWARD more, so putting the glasses on pushes the wire deep onto its
superelastic plateau and the pad force stops depending on fit. This script tests that idea.

    source tools/env.sh
    F="systemd-run --user --scope --quiet -p MemoryMax=2G -p MemorySwapMax=0"
    $F python3 sim/checks/niti_preload.py checks    # model checks against niti_arm_real.py and closed forms
    $F python3 sim/checks/niti_preload.py sweep     # set depth x wire x lower plateau, rigid glasses
    $F python3 sim/checks/niti_preload.py glasses   # + temple bend (k_t) and twist (k_th) in series, fit +-2 mm
    $F python3 sim/checks/niti_preload.py roots     # longer / larger-radius root saddles (the strain fix)
    $F python3 sim/checks/niti_preload.py design D S R L   # chosen wire D, set S, saddle radius R x length L (mm)
    $F python3 sim/checks/niti_preload.py curves    # force-interference curves + sim/out/mech/niti_preload.png
    (each part < 2 min; results -> sim/out/mech/niti_preload_<part>.json, plots -> sim/out/mech/*.png)

Model (same material law and beam as sim/checks/niti_arm_real.py, whose Beam this vectorises):
- Straight superelastic wire, clamped at the heel socket mouth E, bending over span a, then rigid
  (pad + strut) for a lever b to the skin contact. Small-slope beam theory. Fibre "flag" model:
  loading plateau sL, unloading plateau sU, transformation strain 6 %, E 58 GPa.
- NEW 1, curved root support: the heel's trumpet flare (radius R, tangent at E) caps the curvature
  at 1/R wherever the wire wraps onto it, for s < L_flare. As built (hw/mech/heel.py, checks.json):
  R 8 mm, tangent arc ends at s = 0.79 mm (5.7 deg), then a 0.4 mm lip round onto the land.
- NEW 2, the glasses in series: the temple arm bends outward (stiffness k_t, N/mm at the pod) and
  twists under the moment F x H (H = 25 mm, pad below the temple axis; torsional stiffness k_th,
  N mm/rad). Pad-side compliance C_g = 1/k_t + H^2/k_th. Total interference D (free pad position
  inside the skin, rigid glasses = the "set") is shared: D = wire deflection + F C_g.
- Histories are exact at their reversal points: within a monotonic step every section's moment is
  F x lever, so every fibre's strain is monotonic and the flag model's return map is exact. A jaw
  history is therefore just [set, set-2, set+2, set, set-2, set+2, set] (checked below against
  niti_arm_real's 0.25 mm stepping).

Not modelled: large rotations (pad tilts of 20-30 deg make small-slope theory optimistic by ~5-15 %),
skin/tissue compliance (acts exactly like more C_g), temperature (plateaus rise ~6-7 MPa/degC),
adapter and dovetail play (a fixed loss of set; estimated in `design`).
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "sim" / "checks"))
sys.path.insert(0, str(ROOT / "hw" / "mech"))
sys.path.insert(0, str(ROOT / "tools"))
OUT = ROOT / "sim" / "out" / "mech"

GEO = json.loads((ROOT / "hw" / "mech" / "out" / "arm_geometry.json").read_text())
A_SPAN, B_LEVER = GEO["a"], GEO["b"]          # 11.52 bending span, 7.60 rigid lever (CAD)
E_MOD, EPS_T = 58e3, 0.06
SL_NOM, SU_NOM = 450.0, 200.0
SL_FWM = 540.0              # FWM NiTi #9 loading plateau interpolated to 32 C (docs/build/hardware.md)
H_PAD = 25.0                # pad contact below the temple axis (frame.PAD_CONTACT z = -25)
JAW = 2.0
FLARE_AS_BUILT = (8.0, 8.0 * math.sin(math.radians(5.69)))   # (R, tangent length 0.79 mm)
NO_FLARE = (8.0, 0.0)
K_TH_NOM = 500.0            # N mm/rad, temple twist at the pod (estimate, see notes/preload.md)
STRAIN_MAX, PEAK_MAX = 0.04, 2.5
DELTAS = (2.0, 3.5, 5.0, 6.5, 8.0)
WIRES = (0.70, 0.75, 0.80, 0.85)
SUS = (150.0, 200.0, 250.0)


# ----------------------------------------------------------------------------- vectorised beam
class Batch:
    """C independent arms at once. Per-case: wire d, plateaus sL/sU, series compliance Cg (mm/N),
    root support (R, L): curvature <= 1/R for s < L (L = 0: no support)."""

    def __init__(self, d, sL=SL_NOM, sU=SU_NOM, Cg=0.0, flare=FLARE_AS_BUILT, a=A_SPAN, b=B_LEVER,
                 ns=40, nf=27):
        R, L = flare
        vals = [np.atleast_1d(np.asarray(v, float)) for v in (d, sL, sU, Cg, R, L)]
        C = max(v.size for v in vals)
        d, sL, sU, Cg, R, L = [np.broadcast_to(v, (C,)).copy() for v in vals]
        self.C, self.d, self.Cg = C, d, Cg
        r = d / 2
        edges = np.linspace(-1.0, 1.0, nf + 1)
        u = 0.5 * (edges[1:] + edges[:-1])
        self.y = r[:, None] * u[None, :]                                          # (C, nf)
        self.A = 2 * np.sqrt(np.maximum(r[:, None] ** 2 - self.y ** 2, 0)) * (2 * r[:, None] / nf)
        e = a * np.linspace(0.0, 1.0, ns + 1) ** 1.3           # sections bunched toward the root
        self.s = 0.5 * (e[1:] + e[:-1])
        self.ds = np.diff(e)
        self.lever = a + b - self.s
        self.a, self.b = a, b
        self.sL, self.sU = sL[:, None, None], sU[:, None, None]
        self.cap = np.where(self.s[None, :] < L[:, None], 1.0 / R[:, None], np.inf)   # (C, ns)
        self.Lf, self.Rf = L, R
        self.xi = np.zeros((C, ns, nf))
        self.k = np.zeros((C, ns))

    def _state(self, kappa):
        E, sL, sU, eL = E_MOD, self.sL, self.sU, EPS_T
        eps = kappa[:, :, None] * self.y[:, None, :]
        xi = self.xi
        s = E * (eps - xi * eL)
        m = (xi > 0) & (s < sU)
        xi = np.where(m, np.clip((eps - sU / E) / eL, 0, 1), xi)
        s = E * (eps - xi * eL)
        m = (xi < 0) & (s > -sU)
        xi = np.where(m, np.clip((eps + sU / E) / eL, -1, 0), xi)
        s = E * (eps - xi * eL)
        m = (xi >= 0) & (s > sL)
        xi = np.where(m, np.clip((eps - sL / E) / eL, 0, 1), xi)
        s = E * (eps - xi * eL)
        m = (xi <= 0) & (s < -sL)
        xi = np.where(m, np.clip((eps + sL / E) / eL, -1, 0), xi)
        s = E * (eps - xi * eL)
        return np.einsum("csf,cf->cs", s, self.y * self.A), xi

    def curvatures(self, F):
        target = F[:, None] * self.lever[None, :]
        lo = np.full_like(target, -0.4)
        hi = np.full_like(target, 0.4)
        for _ in range(28):
            mid = 0.5 * (lo + hi)
            M, _ = self._state(mid)
            below = M < target
            lo = np.where(below, mid, lo)
            hi = np.where(below, hi, mid)
        return np.clip(0.5 * (lo + hi), -self.cap, self.cap)

    def deflection(self, F):
        return (self.curvatures(F) * (self.lever * self.ds)[None, :]).sum(axis=1)

    def step(self, D):
        """Move every case to total pad interference D (C,), return metrics at the new state."""
        lo = np.full(self.C, -0.5)
        hi = np.full(self.C, 10.0)
        for _ in range(27):
            mid = 0.5 * (lo + hi)
            below = self.deflection(mid) + self.Cg * mid < D
            lo = np.where(below, mid, lo)
            hi = np.where(below, hi, mid)
        F = 0.5 * (lo + hi)
        if np.any(F > 9.9):
            raise RuntimeError("force bracket exceeded")
        k = self.curvatures(F)
        _, self.xi = self._state(k)
        self.k = k
        return self.metrics(F)

    def metrics(self, F):
        k, s, ds, r = self.k, self.s, self.ds, self.d / 2
        theta = np.cumsum(k * ds, axis=1)
        sup = np.isfinite(self.cap)                               # sections over the flare
        wrapped = np.isclose(np.abs(k), self.cap) & sup
        on_lip = (self.Lf > 0) & np.all(wrapped | ~sup, axis=1)  # wrapped all the way to the lip
        exit_slope = (k * ds * sup).sum(1)
        return {"F": F, "dw": (k * self.lever * ds).sum(1), "theta": theta[:, -1],
                "w_end": (k * (self.a - s) * ds).sum(1), "eps": np.abs(k).max(1) * r,
                "eps_at": s[np.abs(k).argmax(1)], "k": k.copy(), "on_lip": on_lip, "exit_slope": exit_slope,
                "wrap": (wrapped * ds).sum(1)}


def jaw_targets(D0, amp=JAW, cycles=2):
    """Reversal points of donning + jaw cycles: (C, 1 + 3*cycles)."""
    D0 = np.atleast_1d(np.asarray(D0, float))
    cols = [D0]
    for _ in range(cycles):
        cols += [np.maximum(D0 - amp, 0.0), D0 + amp, D0]
    return np.stack(cols, axis=1)


def run(batch, targets):
    hist = [batch.step(targets[:, j]) for j in range(targets.shape[1])]
    return hist


def summarise(batch, hist, k_th=None):
    """Per-case numbers from a jaw history built by jaw_targets(cycles=2)."""
    F = np.stack([h["F"] for h in hist], 1)
    eps = np.stack([h["eps"] for h in hist], 1)
    th = np.stack([h["theta"] for h in hist], 1)
    k_th = np.full(batch.C, np.inf) if k_th is None else np.broadcast_to(np.asarray(k_th, float), (batch.C,))
    phi = F * H_PAD / k_th[:, None]                                  # temple twist, rad
    r = batch.d / 2
    k_open, k_close = hist[4]["k"], hist[5]["k"]                     # 2nd jaw cycle, steady
    dk = 0.5 * np.abs(k_close - k_open)                               # alternating curvature along s
    i = dk.argmax(1)
    amp = dk[np.arange(batch.C), i] * r                               # worst alternating strain anywhere
    amp_mean = 0.5 * np.abs(k_close + k_open)[np.arange(batch.C), i] * r
    amp_s = batch.s[i]
    tilt = np.degrees(th + phi)
    return {
        "F_don": F[:, 0], "F_settled": F[:, -1], "F_min": F[:, 1:].min(1), "F_max": F[:, 1:].max(1),
        "F_peak": F.max(1), "eps_max": eps.max(1), "eps_don": eps[:, 0], "eps_amp": amp,
        "eps_amp_mean": amp_mean, "eps_amp_at": amp_s,
        "eps_at": hist[5]["eps_at"], "on_lip": np.any(np.stack([h["on_lip"] for h in hist], 1), 1),
        "exit_slope_deg": np.degrees(np.max(np.stack([h["exit_slope"] for h in hist], 1), 1)),
        "wrap_max": np.max(np.stack([h["wrap"] for h in hist], 1), 1),
        "theta_don_deg": np.degrees(th[:, 0]), "theta_settled_deg": np.degrees(th[:, -1]),
        "tilt_settled_deg": tilt[:, -1], "tilt_rock_deg": tilt[:, 5] - tilt[:, 4],
        "phi_settled_deg": np.degrees(phi[:, -1]),
        "dw_settled": hist[-1]["dw"], "dw_don": hist[0]["dw"],
        "w_end_don": hist[0]["w_end"], "w_end_settled": hist[-1]["w_end"],
    }


def _js(d):
    return {k: ((v.tolist() if v.dtype == bool else np.round(v, 4).tolist()) if isinstance(v, np.ndarray) else v)
            for k, v in d.items()}


def _save(name, obj):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"niti_preload_{name}.json").write_text(json.dumps(obj, indent=1))


# ----------------------------------------------------------------------------- heel socket axis
def free_axis(w_end):
    """frame._solve_axis, with the worn deflection at the end of the span w_end as input."""
    import frame as FR
    T = FR.PAD_CENTRE + 7.6 * FR.E3 + np.array([0.0, 4.6, 0.0])
    a_E = (T - FR.E) / np.linalg.norm(T - FR.E)
    for _ in range(40):
        n = FR.E2 - (FR.E2 @ a_E) * a_E
        n /= np.linalg.norm(n)
        chord = T - w_end * n - FR.E
        a_E = chord / np.linalg.norm(chord)
    return a_E, n, float(np.linalg.norm(chord)), T


def socket_tilt(w_end, theta_end):
    """Heel-socket axis change vs frame.A_E (deg, + = lower end toward the head) and the pad-socket
    axis change (deg) for a worn shape with end deflection w_end and end slope theta_end (rad)."""
    import frame as FR
    a_new, n_new, span, _ = free_axis(w_end)
    B = np.cross(FR.A_E, FR.N_BEND)
    B /= np.linalg.norm(B)
    tilt = math.degrees(math.atan2(np.cross(FR.A_E, a_new) @ B, FR.A_E @ a_new))
    _, aT_old = FR.pad_socket_axis("worn_3.5")
    aT_new = a_new + math.tan(theta_end) * n_new
    aT_new /= np.linalg.norm(aT_new)
    pad = math.degrees(math.atan2(np.cross(aT_old, aT_new) @ B, aT_old @ aT_new))
    return {"heel_tilt_deg": -tilt, "pad_socket_change_deg": -pad, "a_E_new": a_new.round(4).tolist(),
            "span_mm": round(span, 2), "free_pad_entry_shift_mm": round(float(w_end), 2)}


# ----------------------------------------------------------------------------- parts
def part_checks():
    import niti_arm_real as NR
    res = {}
    # 1. exactness of reversal-point histories + agreement with niti_arm_real (0.25 mm steps, ns 60 x nf 41)
    t0 = time.time()
    ref = NR.band(A_SPAN, B_LEVER, 0.80, d0=3.5, amp=2.0, sU=200.0)
    t_ref = time.time() - t0
    bt = Batch(0.80, flare=NO_FLARE)
    s = summarise(bt, run(bt, jaw_targets(3.5)))
    fine = Batch(0.80, flare=NO_FLARE)
    hist_f = [fine.step(np.array([x])) for x in NR.jaw_history(3.5, 2.0)]
    Ff = np.array([h["F"][0] for h in hist_f])
    nd = len(NR.jaw_history(3.5, 2.0, cycles=0))
    res["vs_niti_arm_real"] = {
        "ref (ns60 nf41, 0.25 mm steps)": {k: round(ref[k], 4) for k in ("F_don", "F_min", "F_max", "F_settled")},
        "this (ns40 nf27, reversal points)": {"F_don": round(float(s["F_don"][0]), 4), "F_min": round(float(s["F_min"][0]), 4),
                                              "F_max": round(float(s["F_max"][0]), 4), "F_settled": round(float(s["F_settled"][0]), 4)},
        "this (ns40 nf27, 0.25 mm steps)": {"F_don": round(float(Ff[nd - 1]), 4),
                                            "F_settled": round(float(Ff[-1]), 4), "F_min": round(float(Ff[nd:].min()), 4),
                                            "F_max": round(float(Ff[nd:].max()), 4)},
        "ref_runtime_s": round(t_ref, 1)}
    # arm_geometry.json's "worn_3.5" (F 1.0187 N): which branch is it?
    res["arm_geometry_worn_3.5_F"] = GEO["shapes"]["worn_3.5"]["F"]
    # 2. closed forms: elastic load-point compliance, fully-plastic limit, series spring, flare cap
    d = 0.80
    EI = E_MOD * math.pi * d ** 4 / 64
    Cw = (A_SPAN ** 3 / 3 + A_SPAN ** 2 * B_LEVER + A_SPAN * B_LEVER ** 2) / EI
    b1 = Batch(d, flare=NO_FLARE)
    F1 = b1.step(np.array([0.3]))["F"][0]
    b2 = Batch(d, Cg=2.0, flare=NO_FLARE)
    F2 = b2.step(np.array([0.9]))["F"][0]
    b3 = Batch(d, flare=NO_FLARE)
    for x in np.arange(1, 30.1, 1.0):
        F3 = b3.step(np.array([x]))["F"][0]
    b3e = Batch(d, flare=NO_FLARE, a=20.0, b=0.0)        # niti_arm_real's check geometry
    global EPS_T
    keep, EPS_T = EPS_T, 10.0
    for x in np.arange(0.5, 15.01, 0.5):
        F3e = b3e.step(np.array([x]))["F"][0]
    EPS_T = keep
    Mp = 450 * d ** 3 / 6
    b4 = Batch(d, flare=(8.0, 3.0))
    m4 = b4.step(np.array([9.0]))
    res["closed_forms"] = {
        "elastic: F(0.3 mm) model / 0.3/C_w": round(F1 / (0.3 / Cw), 4),
        "series: F(0.9 mm, Cg 2) model / 0.9/(C_w+2)": round(F2 / (0.9 / (Cw + 2.0)), 4),
        "endless plateau, 20 mm cantilever at 15 mm: F / (Mp/L)": round(F3e / (Mp / 20.0), 4),
        "6% plateau then martensite: F(30 mm) N": round(float(F3), 3),
        "flare R8 over 3 mm: root curvature x R (expect 1.000)": round(float(m4["k"][0, 0] * 8.0), 4),
        "C_w (elastic wire compliance at the pad, d 0.80) mm/N": round(Cw, 3)}
    # 3. discretisation: ns 40 x nf 27 vs ns 80 x nf 51 on a deep case with the as-built flare
    out = {}
    for ns, nf in ((40, 27), (80, 51)):
        bb = Batch(0.80, Cg=2.25, ns=ns, nf=nf)
        ss = summarise(bb, run(bb, jaw_targets(6.5)), k_th=K_TH_NOM)
        out[f"ns{ns}_nf{nf}"] = {k: round(float(ss[k][0]), 4) for k in ("F_don", "F_settled", "F_min", "F_max", "eps_max")}
    res["discretisation (d 0.80, set 6.5, Cg 2.25)"] = out
    # 4. frame.A_E reproduced from the worn_3.5 shape
    import frame as FR
    a_E, _, span, _ = free_axis(GEO["shapes"]["worn_3.5"]["w"][-1])
    res["frame_A_E_reproduced_deg_error"] = round(math.degrees(math.acos(min(1.0, float(a_E @ FR.A_E)))), 5)
    res["frame_span"] = [round(span, 3), round(FR.SPAN, 3)]
    return res


def part_sweep():
    """The owner's table: set x wire x lower plateau, rigid glasses, jaw +-2 mm; no flare and as built."""
    res = {}
    grid = [(D, d, sU) for D in DELTAS for d in WIRES for sU in SUS]
    D, d, sU = map(np.array, zip(*grid))
    for name, fl in (("no_flare", NO_FLARE), ("flare_as_built", FLARE_AS_BUILT)):
        bt = Batch(d, sU=sU, flare=fl)
        s = summarise(bt, run(bt, jaw_targets(D)))
        res[name] = {"set": D.tolist(), "d": d.tolist(), "sU": sU.tolist(), **_js(s)}
    # loading-plateau sensitivity (FWM #9 at 32 C), as-built flare, sU 200
    g2 = [(D_, d_) for D_ in DELTAS for d_ in WIRES]
    D2, d2 = map(np.array, zip(*g2))
    bt = Batch(d2, sL=SL_FWM, flare=FLARE_AS_BUILT)
    res["sL540_flare_as_built"] = {"set": D2.tolist(), "d": d2.tolist(), **_js(summarise(bt, run(bt, jaw_targets(D2))))}
    return res


KT = (np.inf, 5.0, 2.0, 1.0, 0.5)
SETS_G = (2.0, 3.5, 5.0, 6.5, 8.0, 9.5, 11.0)
FITS = (-2.0, 0.0, 2.0)


def cg(kt, kth):
    return (0.0 if not np.isfinite(kt) else 1.0 / kt) + (0.0 if not np.isfinite(kth) else H_PAD ** 2 / kth)


def part_glasses():
    """Temple bend k_t x twist (k_th nominal) in series; set x fit error x wire; sU 200; as-built flare."""
    rows = []
    for kt in KT:
        kth = np.inf if not np.isfinite(kt) else K_TH_NOM     # "rigid glasses" row has no twist either
        for S in SETS_G:
            for f in FITS:
                for d in WIRES:
                    rows.append((kt, kth, S, f, d))
    kt, kth, S, f, d = map(np.array, zip(*rows))
    Cg = np.array([cg(a, b) for a, b in zip(kt, kth)])
    bt = Batch(d, Cg=Cg, flare=FLARE_AS_BUILT)
    s = summarise(bt, run(bt, jaw_targets(np.maximum(S + f, 0.0))), k_th=kth)
    return {"k_t": [float(x) if np.isfinite(x) else None for x in kt],
            "k_th": [float(x) if np.isfinite(x) else None for x in kth], "Cg": Cg.round(4).tolist(),
            "set": S.tolist(), "fit": f.tolist(), "d": d.tolist(), **_js(s)}


ROOTS = {"as_built R8 L0.79": FLARE_AS_BUILT, "R10 L2": (10.0, 2.0), "R10 L4": (10.0, 4.0), "R10 long": (10.0, 11.6),
         "R12 L2": (12.0, 2.0), "R12 L4": (12.0, 4.0), "R12 long": (12.0, 11.6)}


def part_roots():
    """Root-support (saddle) variants x wire x set x fit x k_t (k_th nominal), sU 200."""
    rows = [(nm, d, S, f, kt) for nm in ROOTS for d in (0.75, 0.80) for S in (3.5, 5.0, 6.5, 8.0, 9.5)
            for f in FITS for kt in (5.0, 2.0, 1.0, 0.5)]
    nm, d, S, f, kt = map(np.array, zip(*rows))
    R = np.array([ROOTS[x][0] for x in nm])
    L = np.array([ROOTS[x][1] for x in nm])
    Cg = np.array([cg(k, K_TH_NOM) for k in kt])
    bt = Batch(d, Cg=Cg, flare=(R, L))
    s = summarise(bt, run(bt, jaw_targets(np.maximum(S + f, 0.0))), k_th=K_TH_NOM)
    return {"root": nm.tolist(), "d": d.tolist(), "set": S.tolist(), "fit": f.tolist(), "k_t": kt.tolist(),
            "Cg": Cg.round(4).tolist(), **_js(s)}


def roots_table(Rr, kts_force=(2.0, 1.0, 0.5), kts_strain=(5.0, 2.0, 1.0, 0.5)):
    a = {k: np.array(v) for k, v in Rr.items()}
    out = []
    for nm in ROOTS:
        for d in (0.75, 0.80):
            for S in (3.5, 5.0, 6.5, 8.0, 9.5):
                base = (a["root"] == nm) & (a["d"] == d) & (a["set"] == S)
                mf = base & np.isin(a["k_t"], kts_force)
                ms = base & np.isin(a["k_t"], kts_strain)
                Fs = a["F_settled"][mf]
                out.append({"root": nm, "d": d, "set": S, "settled_min": Fs.min(), "settled_max": Fs.max(),
                            "ratio": Fs.max() / max(Fs.min(), 1e-6), "band_min": a["F_min"][mf].min(),
                            "band_max": a["F_max"][mf].max(), "don_max": a["F_don"][ms].max(),
                            "eps_max_plaus": a["eps_max"][mf].max(), "eps_max_all": a["eps_max"][ms].max(),
                            "eps_amp": a["eps_amp"][mf].max(), "wrap": a["wrap_max"][ms].max(),
                            "lip": bool(a["on_lip"][ms].any())})
    return out


def robust_table(G, kts=(2.0, 1.0, 0.5)):
    """Per (wire, set): spread of the settled force over fit {-2,0,2} x k_t in `kts`, and the limits."""
    arr = {k: np.array(v, dtype=float) if k not in ("k_t", "k_th") else np.array([np.inf if x is None else x for x in v])
           for k, v in G.items()}
    out = []
    for d in WIRES:
        for S in SETS_G:
            m = (arr["d"] == d) & (arr["set"] == S) & np.isin(arr["k_t"], kts)
            Fs = arr["F_settled"][m]
            out.append({"d": d, "set": S, "settled_min": Fs.min(), "settled_max": Fs.max(),
                        "ratio": Fs.max() / max(Fs.min(), 1e-6), "band_min": arr["F_min"][m].min(),
                        "don_max": arr["F_don"][m].max(), "peak_max": arr["F_peak"][m].max(),
                        "eps_max": arr["eps_max"][m].max(), "eps_amp_max": arr["eps_amp"][m].max(),
                        "ok": bool(arr["eps_max"][m].max() <= STRAIN_MAX + 1e-9 and arr["F_don"][m].max() <= PEAK_MAX)})
    return out


def strut_gap(batch, k, s_strut):
    """Largest gap between the wire and a straight strut that follows the wire's END tangent, for s >= s_strut
    (what the strut channel must allow; niti_arm_real.Beam.shape does the same from s = 0)."""
    th = np.cumsum(k * batch.ds, axis=1)
    w = np.cumsum(th * batch.ds, axis=1)
    line = w[:, -1:] - th[:, -1:] * (batch.a - batch.s[None, :])
    m = batch.s >= s_strut
    return np.abs(w - line)[:, m].max(1)


def lead_in_and_roll(F_don, F_set, F_peak, set_mm):
    """Donning lead-in and the temple roll couple (numbers for notes/preload.md)."""
    out = {}
    rise = set_mm + 0.5                                     # 0.5 mm clearance over the skin
    out["lead_in"] = {"rise_mm": rise, "ramp_len_mm": {f"{a}deg": round(rise / math.tan(math.radians(a)), 1)
                                                        for a in (20, 30, 40)},
                      "push_N_per_N_normal": {f"{a}deg_mu{mu}": round(math.tan(math.radians(a) + math.atan(mu)), 2)
                                              for a in (20, 30, 40) for mu in (0.6, 1.0)},
                      "push_at_F_don_30deg_mu0.6": round(F_don * math.tan(math.radians(30) + math.atan(0.6)), 2)}
    # roll: pad force F (outward, +y) at H_PAD below the temple axis -> M = F*H about the temple (x)
    # adapter (hw/mech/blade.py): plate on the temple's outer face (contact at its top edge z = +2.5),
    # bottom hook on the temple's inner face at z = -(2.5 - 0.25) = -2.25.
    z_t, z_h = 2.5, -2.25
    P = (H_PAD + z_h) / (z_t - z_h)                         # plate-top force per N of pad force
    Hk = 1 + P                                              # bottom-hook force per N
    out["roll"] = {"M_settled_Nmm": round(F_set * H_PAD, 1), "M_peak_Nmm": round(F_peak * H_PAD, 1),
                   "plate_top_N_per_N": round(P, 2), "bottom_hook_N_per_N": round(Hk, 2),
                   "bottom_hook_at_peak_N": round(Hk * F_peak, 1),
                   "pad_shift_per_0.1mm_channel_play_mm": round(H_PAD * 0.1 / (z_t - z_h), 2),
                   "friction_only_clamp_on_round_2mm_temple_N_at_peak_mu0.3": round(F_peak * H_PAD / (0.3 * 2.0), 0)}
    # pod on adapter: pod face pivots on the adapter plate's top edge (z = 3.9 - 0.4 chamfer), dovetail at ZC = -2
    z_piv, z_dt = 3.5, -2.0
    T = (H_PAD + z_piv) / (z_piv - z_dt)
    out["dovetail"] = {"flank_pull_N_per_N": round(T, 2), "flank_pull_at_peak_N": round(T * F_peak, 1),
                       "pad_shift_per_0.1mm_lift_mm": round((H_PAD + z_piv) * 0.1 / (z_piv - z_dt), 2)}
    return out


KT_DESIGN = (5.0, 2.0, 1.0, 0.5, 0.25)     # 0.25: a soft acetate temple as a free cantilever (notes/preload.md §3)


def part_design(d_rec, set_rec, flare):
    res = {"d": d_rec, "set": set_rec, "flare": list(flare)}
    # 1. sensitivity at the chosen point: k_t x k_th x fit x sU, and sL 540
    rows = [(kt, kth, f, sU, sL) for kt in KT_DESIGN for kth in (np.inf, 1500.0, 500.0, 250.0)
            for f in FITS for sU in SUS for sL in (SL_NOM, SL_FWM)]
    kt, kth, f, sU, sL = map(np.array, zip(*rows))
    Cg = np.array([cg(a, b) for a, b in zip(kt, kth)])
    bt = Batch(d_rec, sL=sL, sU=sU, Cg=Cg, flare=flare)
    s = summarise(bt, run(bt, jaw_targets(set_rec + f)), k_th=kth)
    res["sensitivity"] = {"k_t": kt.tolist(), "k_th": [float(x) if np.isfinite(x) else None for x in kth],
                          "fit": f.tolist(), "sU": sU.tolist(), "sL": sL.tolist(), "Cg": Cg.round(3).tolist(), **_js(s)}
    # 1b. neutral jaw reached from BELOW (last move = opening -> neutral), sL 450 / sU 200: the top of the
    #     force you can find at neutral; `F_settled` above is reached from above (the bottom).
    rows = [(kt, kth, f) for kt in KT_DESIGN for kth in (np.inf, 1500.0, 500.0, 250.0) for f in FITS]
    kt2, kth2, f2 = map(np.array, zip(*rows))
    Cg2 = np.array([cg(a, b) for a, b in zip(kt2, kth2)])
    D0 = set_rec + f2
    bt = Batch(d_rec, Cg=Cg2, flare=flare)
    hist = run(bt, np.stack([D0, D0 + JAW, np.maximum(D0 - JAW, 0), D0], 1))
    res["neutral_from_below"] = {"k_t": kt2.tolist(), "k_th": [float(x) if np.isfinite(x) else None for x in kth2],
                                 "fit": f2.tolist(), "F_up": np.round(hist[-1]["F"], 4).tolist()}
    # 1c. fatigue: alternating strain for chewing-size jaw motion (+-1 mm) next to the full +-2 mm, fit 0, sU 200
    chew = {}
    for amp in (1.0, 2.0):
        rows = [(kt, kth) for kt in KT_DESIGN for kth in (np.inf, 1500.0, 500.0, 250.0)]
        kt3, kth3 = map(np.array, zip(*rows))
        bt = Batch(d_rec, Cg=np.array([cg(a, b) for a, b in zip(kt3, kth3)]), flare=flare)
        ss = summarise(bt, run(bt, jaw_targets(np.full(len(rows), set_rec), amp=amp)), k_th=kth3)
        chew[f"jaw_pm{amp:g}"] = {"k_t": kt3.tolist(), "k_th": [float(x) if np.isfinite(x) else None for x in kth3],
                                  "eps_amp": np.round(ss["eps_amp"], 5).tolist(),
                                  "eps_amp_mean": np.round(ss["eps_amp_mean"], 5).tolist(),
                                  "eps_amp_at": np.round(ss["eps_amp_at"], 2).tolist(),
                                  "F_min": np.round(ss["F_min"], 3).tolist(), "F_max": np.round(ss["F_max"], 3).tolist()}
    res["chew"] = chew
    # 2. heel-socket tilt: worn shape at the new set, rigid glasses (frame's convention), both branches
    tilts = {}
    for S in sorted({2.0, 3.5, 5.0, 6.5, 8.0, set_rec}):
        bt = Batch(d_rec, flare=flare)
        ss = summarise(bt, run(bt, jaw_targets(S)))
        tilts[str(S)] = {"donning": socket_tilt(float(ss["w_end_don"][0]), math.radians(float(ss["theta_don_deg"][0]))),
                         "settled": socket_tilt(float(ss["w_end_settled"][0]), math.radians(float(ss["theta_settled_deg"][0])))}
    res["socket_tilt"] = tilts
    # worn pose on a real head (k_t 1, k_th nominal, fit 0) vs the rigid-glasses design pose; strut gap
    pose = {}
    for name, kt_, kth_ in (("rigid", np.inf, np.inf), ("kt2_kth500", 2.0, K_TH_NOM), ("kt1_kth500", 1.0, K_TH_NOM),
                            ("kt0.5_kth500", 0.5, K_TH_NOM), ("kt0.25_kth500", 0.25, K_TH_NOM), ("kt1_kth250", 1.0, 250.0),
                            ("kt1.5_kth2000", 1.5, 2000.0), ("kt5_kthinf", 5.0, np.inf)):
        bt = Batch(d_rec, Cg=cg(kt_, kth_), flare=flare)
        hist = run(bt, jaw_targets(set_rec))
        ss = summarise(bt, hist, k_th=kth_)
        gaps = [float(strut_gap(bt, h["k"], s0)[0]) for h in hist for s0 in (3.0,)]
        gaps55 = [float(strut_gap(bt, h["k"], 5.5)[0]) for h in hist]
        pose[name] = {"F_settled": round(float(ss["F_settled"][0]), 3), "dw_settled": round(float(ss["dw_settled"][0]), 2),
                      "temple_bend_mm": round(float(ss["F_settled"][0]) / kt_, 2) if np.isfinite(kt_) else 0.0,
                      "temple_twist_mm_at_pad": round(float(ss["F_settled"][0]) * H_PAD ** 2 / kth_, 2) if np.isfinite(kth_) else 0.0,
                      "theta_settled_deg": round(float(ss["theta_settled_deg"][0]), 1),
                      "phi_settled_deg": round(float(ss["phi_settled_deg"][0]), 1),
                      "tilt_settled_deg": round(float(ss["tilt_settled_deg"][0]), 1),
                      "tilt_rock_deg": round(float(ss["tilt_rock_deg"][0]), 1),
                      "strut_gap_from_s3_max_mm": round(max(gaps), 2), "strut_gap_from_s5.5_max_mm": round(max(gaps55), 2)}
    res["pose"] = pose
    sens = res["sensitivity"]
    m = [i for i in range(len(sens["k_t"])) if sens["k_t"][i] == 1.0 and sens["k_th"][i] == K_TH_NOM
         and sens["fit"][i] == 0.0 and sens["sU"][i] == SU_NOM and sens["sL"][i] == SL_NOM][0]
    pk = max(sens["F_don"][i] for i in range(len(sens["k_t"])) if sens["k_t"][i] <= 2.0 and sens["sL"][i] == SL_NOM)
    res["lead_in_roll"] = lead_in_and_roll(sens["F_don"][m], sens["F_settled"][m], pk, set_rec)
    # 3. settled force vs actual interference (fit) for each k_t, chosen wire
    Ds = np.arange(0.0, 12.01, 0.5)
    rows = [(kt, D) for kt in (np.inf,) + KT_DESIGN for D in Ds]
    kt, D = map(np.array, zip(*rows))
    kth = np.where(np.isfinite(kt), K_TH_NOM, np.inf)
    Cg = np.array([cg(a, b) for a, b in zip(kt, kth)])
    bt = Batch(d_rec, Cg=Cg, flare=flare)
    s = summarise(bt, run(bt, jaw_targets(D)), k_th=kth)
    res["vs_fit"] = {"k_t": [float(x) if np.isfinite(x) else None for x in kt], "D": D.tolist(), **_js(s)}
    return res


def _seg(a, b, n):
    return np.linspace(a, b, n + 1)[1:]


def part_curves(d_rec, set_rec, flare):
    """Force vs interference for the plots: on to 12 mm and off again, and jaw loops at set 3.5 and
    the chosen set, for rigid glasses and k_t 1 / k_th nominal. Cases batched (equal step counts)."""
    C2 = np.array([0.0, cg(1.0, K_TH_NOM)])
    flag = np.concatenate([_seg(0, 12, 60), _seg(12, 0, 60)])
    bt = Batch(d_rec, Cg=C2, flare=flare)
    hs = [bt.step(np.full(2, x)) for x in flag]
    out = {"flag_D": flag.round(3).tolist()}
    for i, name in enumerate(("rigid", "kt1_kth500")):
        out[f"flag_{name}"] = {"F": [round(float(h["F"][i]), 4) for h in hs],
                               "eps": [round(float(h["eps"][i]), 5) for h in hs]}
    sets = np.array([3.5, 3.5, set_rec, set_rec])
    Cg4 = np.array([C2[0], C2[1], C2[0], C2[1]])
    path = [_seg(0, 1, 30)[:, None] * sets[None, :]]
    for a_, b_, n in ((0, -1, 10), (-1, 1, 20), (1, -1, 20), (-1, 0, 10)):
        path.append(sets[None, :] + JAW * _seg(a_, b_, n)[:, None])
    path = np.maximum(np.concatenate(path, 0), 0.0)
    bt = Batch(d_rec, Cg=Cg4, flare=flare)
    hs = [bt.step(row) for row in path]
    for i, (S_, nm) in enumerate(((3.5, "rigid"), (3.5, "kt1_kth500"), (set_rec, "rigid"), (set_rec, "kt1_kth500"))):
        out[f"jaw_{nm}_set{S_:g}"] = {"D": path[:, i].round(3).tolist(), "F": [round(float(h["F"][i]), 4) for h in hs],
                                      "n_don": 30}
    # wire shapes for the mechanism picture (rigid glasses = frame.py's convention): today's set 3.5 on the
    # as-built R8 flare, and the new set on the new saddle; worn = settled (reached from above), jaw closed = set + 2
    out["shapes"] = {}
    for nm, S_, fl in (("old", 3.5, FLARE_AS_BUILT), ("new", set_rec, flare)):
        bt = Batch(d_rec, flare=fl)
        hist = run(bt, jaw_targets(np.array([S_])))
        se = np.concatenate([[0.0], np.cumsum(bt.ds)])
        shp = {"s": se.round(4).tolist(), "set": S_, "flare": list(fl)}
        for st, h in (("worn", hist[-1]), ("closed", hist[5]), ("open", hist[4])):
            th = np.concatenate([[0.0], np.cumsum(h["k"][0] * bt.ds)])
            w = np.concatenate([[0.0], np.cumsum(0.5 * (th[1:] + th[:-1]) * bt.ds)])
            shp[st] = {"w": w.round(5).tolist(), "theta": th.round(6).tolist(), "F": round(float(h["F"][0]), 4)}
        out["shapes"][nm] = shp
    return out


def shapes_figure(cv, design):
    """Bending-plane picture: heel at the top, head to the LEFT, outward to the right. Both designs put the worn
    span end at the same point T (frame._solve_axis in 2D) and keep the pad's worn orientation (the pad socket is
    re-angled), so the worn pads coincide; the free pads show where each design sits off the head."""
    import plotstyle
    plt = plotstyle.apply()
    S = plotstyle.SERIES
    sh = cv["shapes"]

    def frame_of(alpha):          # alpha > 0: lower end toward the head (left)
        d = np.array([-math.sin(alpha), -math.cos(alpha)])
        return d, np.array([math.cos(alpha), -math.sin(alpha)])            # axis (down), outward normal

    def curve(alpha, shp, st, span):
        d, n = frame_of(alpha)
        s = np.array(shp["s"]) * span / A_SPAN
        w = np.zeros_like(s) if st == "free" else np.array(shp[st]["w"])
        th = 0.0 if st == "free" else shp[st]["theta"][-1]
        P = s[:, None] * d[None, :] + w[:, None] * n[None, :]
        t = d + math.tan(th) * n
        return P, t / np.linalg.norm(t), th

    old, new = sh["old"], sh["new"]
    T = curve(0.0, old, "worn", A_SPAN)[0][-1]
    a, span = 0.0, A_SPAN
    for _ in range(40):                                   # frame._solve_axis, 2D
        d, n = frame_of(a)
        chord = T - new["worn"]["w"][-1] * n
        a = math.atan2(-chord[0], -chord[1])
        span = float(np.linalg.norm(chord))
    _, t_old_worn, th_old = curve(0.0, old, "worn", A_SPAN)
    _, t_new_worn, th_new = curve(a, new, "worn", span)
    pad_off = math.atan2(t_old_worn[0], -t_old_worn[1]) - math.atan2(t_new_worn[0], -t_new_worn[1])

    def rot(v, ang):
        c, s_ = math.cos(ang), math.sin(ang)
        return np.array([c * v[0] - s_ * v[1], s_ * v[0] + c * v[1]])

    import frame as FR
    h = float(FR.T_WORN[1] - FR.PAD_Y["skin"])          # wire axis -> contact face, through the pad (8.2 mm)
    half = FR.TRANSDUCER["L"] / 2

    def nrm_of(t):
        n_ = np.array([-t[1], t[0]])
        return n_ if n_[0] > 0 else -n_

    def pad_block(Tp, t):
        n_ = nrm_of(t)
        c = Tp + B_LEVER * t - h * n_                        # contact centre
        return np.array([Tp + (B_LEVER - half) * t, Tp + (B_LEVER + half) * t,
                         Tp + (B_LEVER + half) * t - h * n_, Tp + (B_LEVER - half) * t - h * n_]), c

    fig, ax = plt.subplots(figsize=(7.8, 8.2))
    nrm = nrm_of(t_old_worn)
    _, c_w = pad_block(T, t_old_worn)                     # worn contact centre (both designs)
    sk = np.stack([c_w - 16 * t_old_worn, c_w + 10 * t_old_worn])
    ax.fill(np.r_[sk[:, 0], sk[::-1, 0] - 12], np.r_[sk[:, 1], sk[::-1, 1]], color=plotstyle.GRID, alpha=0.7, lw=0)
    ax.plot(sk[:, 0], sk[:, 1], color=plotstyle.TEXT_2, lw=2.0)
    ax.text(*(sk[0] + np.array([-11.5, -1.5])), "head\n(skin line = worn pad face)", color=plotstyle.TEXT_2, fontsize=8)
    handles = []
    for nm, shp, al, sp, col, lab in (("old", old, 0.0, A_SPAN, S[0], "today: set 3.5, R8 flare"),
                                      ("new", new, a, span, S[1], f"new: set {new['set']:g}, R{new['flare'][0]:g} x {new['flare'][1]:g} saddle")):
        Pf, _, _ = curve(al, shp, "free", sp)
        Pw, _, thw = curve(al, shp, "worn", sp)
        Pc, _, thc = curve(al, shp, "closed", sp)
        lever_w = t_old_worn                              # pad keeps its worn orientation in both designs
        lever_f = rot(lever_w, -thw)                      # the pad turns with the wire end
        lever_c = rot(lever_w, thc - thw)
        hw, = ax.plot(Pw[:, 0], Pw[:, 1], color=col, lw=2.2, label=f"{lab}: worn (rigid glasses)")
        hf, = ax.plot(Pf[:, 0], Pf[:, 1], color=col, lw=1.4, ls="--", label=f"{lab}: free (off the head)")
        handles += [hw, hf]
        blk_w, _ = pad_block(Pw[-1], lever_w)
        blk_f, c_f = pad_block(Pf[-1], lever_f)
        ax.fill(blk_w[:, 0], blk_w[:, 1], color=col, alpha=0.35 if nm == "new" else 0.0, lw=1.6 if nm == "old" else 1.0, ec=col)
        ax.fill(blk_f[:, 0], blk_f[:, 1], color=col, alpha=0.12, lw=1.0, ec=col, ls="--")
        for P_, t_ in ((Pw, lever_w), (Pf, lever_f)):
            ax.plot(*np.stack([P_[-1], P_[-1] + (B_LEVER - half) * t_]).T, color=col, lw=3, alpha=0.6)
        ax.plot(*c_f, "o", color=col, ms=5)
        if nm == "new":
            blk_c, _ = pad_block(Pc[-1], lever_c)
            ax.plot(Pc[:, 0], Pc[:, 1], color=col, lw=0.8, alpha=0.6)
            ax.fill(blk_c[:, 0], blk_c[:, 1], color=col, alpha=0.0, lw=0.7, ec=col, ls=":")
            R, L = shp["flare"]
            d, n = frame_of(al)
            ph = np.linspace(0, L / R, 30)
            arc = (R * np.sin(ph))[:, None] * d[None, :] + (R * (1 - np.cos(ph)))[:, None] * n[None, :]
            hs_, = ax.plot(arc[:, 0] + 0.45 * n[0], arc[:, 1] + 0.45 * n[1], color=S[2], lw=3.5,
                           label=f"saddle R{R:g} over {L:g} mm on the heel (strain cap r/R = {design['d'] / 2 / R * 100:.1f} %)")
            handles.append(hs_)
            ax.plot(*np.stack([np.zeros(2), 5 * d]).T, color=col, lw=0.6, ls=":")
        depth = float((c_f - c_w) @ (-nrm))
        ax.annotate(f"free pad face {depth:.1f} mm inside the skin\n(model set {shp['set']:g} mm, at the load line)",
                    c_f, c_f + np.array([-11.5, -4.5 if nm == "new" else -9.0]), color=col, fontsize=8,
                    arrowprops=dict(arrowstyle="-", color=col, lw=0.6))
    ax.plot(0, 0, "s", color=plotstyle.TEXT, ms=6)
    ax.text(0.6, 0.4, "E: heel socket mouth", fontsize=8, color=plotstyle.TEXT)
    ax.annotate(f"heel axis turned {math.degrees(a):.1f}° toward the head\n(3D vs frame.A_E: "
                f"{design['socket_tilt'][str(float(new['set']))]['settled']['heel_tilt_deg']:+.1f}°, build this one)",
                (-0.75, -4.0), (-19.5, -2.5), fontsize=8, color=S[1], arrowprops=dict(arrowstyle="-", color=S[1], lw=0.6))
    ax.text(c_w[0] + 0.8, c_w[1] - 2.5, f"worn pads coincide\n(pad socket re-angled {math.degrees(pad_off):+.1f}° 2D,\n"
            f"{design['socket_tilt'][str(float(new['set']))]['settled']['pad_socket_change_deg']:+.1f}° 3D)\n"
            "dotted: jaw closed +2 mm", fontsize=8, color=plotstyle.TEXT_2)
    ax.set_aspect("equal")
    ax.set_xlabel("outward from the head (mm)   [bending plane, small-slope beam model]")
    ax.set_ylabel("down from the heel socket mouth (mm)")
    ax.set_title(f"Deep set: turn the heel in, wrap the root on a saddle (Ø{design['d']:.2f} mm, rigid glasses)", fontsize=10)
    ax.set_xlim(-23.5, 9.0)
    fig.legend(handles=handles, loc="lower center", ncol=1, fontsize=7.5, frameon=False, labelcolor=plotstyle.TEXT)
    fig.tight_layout(rect=(0, 0.13, 1, 1))
    fig.savefig(OUT / "niti_preload_shapes.png")
    return {"alpha_2d_deg": math.degrees(a), "span_2d": span, "pad_socket_2d_deg": math.degrees(pad_off)}


# ----------------------------------------------------------------------------- plots
def plots(design, cv):
    import plotstyle
    plt = plotstyle.apply()
    S = plotstyle.SERIES
    d, Srec = design["d"], design["set"]
    fig, axs = plt.subplots(1, 2, figsize=(10.4, 4.0))
    ax = axs[0]
    for i, name in enumerate(("rigid", "kt1_kth500")):
        c = cv[f"flag_{name}"]
        lab = "rigid glasses" if name == "rigid" else "glasses k_t 1 N/mm, k_th 500 N mm/rad"
        ax.plot(cv["flag_D"], c["F"], color=S[i], lw=1.0, alpha=0.55, label=f"{lab}: on to 12 mm, then off")
        for S_, ls in ((3.5, ":"), (Srec, "-")):
            j = cv[f"jaw_{name}_set{S_:g}"]
            n0 = j["n_don"]
            ax.plot(j["D"][n0 - 1:], j["F"][n0 - 1:], color=S[i], lw=1.8, ls=ls)
            ax.plot([S_], [j["F"][-1]], "o", color=S[i], ms=4)
    ax.axhspan(0, 1.0, color=plotstyle.GRID, alpha=0.5, lw=0)
    ax.axhline(PEAK_MAX, color=S[7], lw=0.8, ls="--")
    ax.text(11.8, PEAK_MAX + 0.04, "2.5 N comfort cap", color=S[7], fontsize=8, ha="right")
    ax.text(11.8, 0.05, "below the 1 N target (D1)", color=plotstyle.TEXT_2, fontsize=8, ha="right")
    ax.set_xlabel("pad interference D: how far inside the skin the free pad sits (mm)")
    ax.set_ylabel("pad force (N)")
    ax.set_title(f"Ø{d:.2f} mm wire, R{design['flare'][0]:g} saddle: force vs interference\n"
                 f"thin: on to 12 mm and off; thick: jaw ±2 mm at set 3.5 (dotted) and {Srec:g} (solid)", fontsize=10)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 3.0)
    ax.legend(loc="upper left", bbox_to_anchor=(0.0, 0.80), fontsize=7.5)
    ax = axs[1]
    vf = design["vs_fit"]
    kt = np.array([np.inf if x is None else x for x in vf["k_t"]])
    D = np.array(vf["D"])
    for i, k in enumerate((np.inf,) + KT_DESIGN):
        m = kt == k
        lab = "rigid" if not np.isfinite(k) else f"k_t {k:g} N/mm"
        ax.plot(D[m], np.array(vf["F_settled"])[m], color=S[i], label=lab, lw=2.0 if k == 1.0 else 1.3)
        if k == 1.0:
            ax.fill_between(D[m], np.array(vf["F_min"])[m], np.array(vf["F_max"])[m], color=S[i], alpha=0.18, lw=0,
                            label="jaw ±2 mm band, k_t 1")
    ax.axvspan(Srec - 2, Srec + 2, color=plotstyle.GRID, alpha=0.6, lw=0)
    ax.axvline(Srec, color=plotstyle.TEXT_2, lw=0.8, ls=":")
    ax.text(Srec, 2.85, f"set {Srec:g} ± 2 mm fit", ha="center", color=plotstyle.TEXT_2, fontsize=8)
    ax.axhline(PEAK_MAX, color=S[7], lw=0.8, ls="--")
    ax.set_xlabel("actual interference on this head (mm)")
    ax.set_ylabel("settled pad force (N)")
    ax.set_title(f"Ø{d:.2f} mm: settled force vs the interference on this head\n"
                 f"temple bend k_t in series, twist k_th {K_TH_NOM:g} N mm/rad", fontsize=10)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 3.0)
    ax.legend(loc="upper left", fontsize=7.5)
    fig.tight_layout()
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "niti_preload.png")


def main():
    part = sys.argv[1] if len(sys.argv) > 1 else "checks"
    t0 = time.time()
    if part == "checks":
        r = part_checks()
        print(json.dumps(r, indent=1))
    elif part == "sweep":
        r = part_sweep()
        for name in ("no_flare", "flare_as_built", "sL540_flare_as_built"):
            R = r[name]
            print(f"\n== {name} (rigid glasses, jaw ±2 mm) ==")
            print(f"{'set':>4} {'d':>5} {'sU':>4} {'don':>5} {'settl':>5} {'band':>10} {'peak':>5} {'eps':>5} {'amp':>5} "
                  f"{'tilt':>5} {'rock':>5} {'lip':>3}")
            for i in range(len(R["set"])):
                sU = R["sU"][i] if "sU" in R else 200
                print(f"{R['set'][i]:4.1f} {R['d'][i]:5.2f} {sU:4.0f} {R['F_don'][i]:5.2f} {R['F_settled'][i]:5.2f} "
                      f"{R['F_min'][i]:4.2f}-{R['F_max'][i]:4.2f} {R['F_peak'][i]:5.2f} {R['eps_max'][i] * 100:4.1f}% "
                      f"{R['eps_amp'][i] * 100:4.2f} {R['theta_settled_deg'][i]:5.1f} {R['tilt_rock_deg'][i]:5.1f} "
                      f"{'Y' if R['on_lip'][i] else '-':>3}")
        _save("sweep", r)
    elif part == "glasses":
        G = part_glasses()
        _save("glasses", G)
        for label, kts in (("plausible k_t 0.5-2", (2.0, 1.0, 0.5)), ("all k_t 0.5-5", (5.0, 2.0, 1.0, 0.5))):
            print(f"\n== robustness over fit ±2 mm x {label} (k_th {K_TH_NOM:g}), sU 200, as-built flare ==")
            print(f"{'d':>5} {'set':>5} {'settled':>11} {'ratio':>5} {'bandmin':>7} {'don':>5} {'peak':>5} {'eps':>5} {'amp':>5} ok")
            for row in robust_table(G, kts):
                print(f"{row['d']:5.2f} {row['set']:5.1f} {row['settled_min']:5.2f}-{row['settled_max']:4.2f} "
                      f"{row['ratio']:5.2f} {row['band_min']:7.2f} {row['don_max']:5.2f} {row['peak_max']:5.2f} "
                      f"{row['eps_max'] * 100:4.1f}% {row['eps_amp_max'] * 100:4.2f} {'OK' if row['ok'] else '--'}")
    elif part == "roots":
        Rr = part_roots()
        _save("roots", Rr)
        print("settled force over fit ±2 x k_t 0.5-2 (k_th 500); strain also over k_t 5; sU 200")
        print(f"{'root':>17} {'d':>5} {'set':>4} {'settled':>10} {'ratio':>5} {'band':>10} {'don':>5} "
              f"{'eps(.5-2)':>9} {'eps(.5-5)':>9} {'amp':>5} {'wrap':>5} lip")
        for r in roots_table(Rr):
            print(f"{r['root']:>17} {r['d']:5.2f} {r['set']:4.1f} {r['settled_min']:4.2f}-{r['settled_max']:4.2f} "
                  f"{r['ratio']:5.2f} {r['band_min']:4.2f}-{r['band_max']:4.2f} {r['don_max']:5.2f} "
                  f"{r['eps_max_plaus'] * 100:8.1f}% {r['eps_max_all'] * 100:8.1f}% {r['eps_amp'] * 100:5.2f} "
                  f"{r['wrap']:5.2f} {'Y' if r['lip'] else '-'}")
    elif part == "design":
        d_rec = float(sys.argv[2]) if len(sys.argv) > 2 else 0.75
        set_rec = float(sys.argv[3]) if len(sys.argv) > 3 else 8.0
        flare = (float(sys.argv[4]), float(sys.argv[5])) if len(sys.argv) > 5 else (10.0, 4.0)
        r = part_design(d_rec, set_rec, flare)
        _save("design", r)                                            # latest (what `curves` plots)
        _save(f"design_d{d_rec:g}_s{set_rec:g}_R{flare[0]:g}L{flare[1]:g}", r)
        print(json.dumps({k: r[k] for k in ("pose", "lead_in_roll")}, indent=1))
        for S_, v in r["socket_tilt"].items():
            print(f"set {S_:>4}: heel tilt vs frame.A_E {v['settled']['heel_tilt_deg']:+.2f} deg (donning branch "
                  f"{v['donning']['heel_tilt_deg']:+.2f}), pad-socket change {v['settled']['pad_socket_change_deg']:+.2f} deg, "
                  f"span {v['settled']['span_mm']} mm")
        nb = r["neutral_from_below"]
        for kt_ in KT_DESIGN:
            ii = [i for i in range(len(nb["k_t"])) if nb["k_t"][i] == kt_ and nb["k_th"][i] is not None]
            print(f"k_t {kt_:>4}: neutral force reached from below (k_th 250-1500, fit +-2): "
                  f"{min(nb['F_up'][i] for i in ii):.2f}-{max(nb['F_up'][i] for i in ii):.2f} N")
        for nm, c in r["chew"].items():
            print(f"{nm}: alternating strain (fit 0) " + ", ".join(
                f"kt{c['k_t'][i]:g}/kth{c['k_th'][i] if c['k_th'][i] else 'inf'}: {c['eps_amp'][i] * 100:.2f}% "
                f"(mean {c['eps_amp_mean'][i] * 100:.1f}% at s {c['eps_amp_at'][i]:.1f})" for i in range(len(c["k_t"]))))
        sens = r["sensitivity"]
        print("\nsensitivity (fit x sU at each k_t, k_th; sL 450 | 540):")
        for kt_ in KT_DESIGN:
            for kth_ in (None, 1500.0, 500.0, 250.0):
                for sL_ in (SL_NOM, SL_FWM):
                    ii = [i for i in range(len(sens["k_t"])) if sens["k_t"][i] == kt_ and sens["k_th"][i] == kth_
                          and sens["sL"][i] == sL_]
                    g = lambda k: [sens[k][i] for i in ii]
                    print(f"k_t {kt_:>3} k_th {str(kth_):>6} sL {sL_:.0f}: settled {min(g('F_settled')):.2f}-{max(g('F_settled')):.2f}"
                          f"  band {min(g('F_min')):.2f}-{max(g('F_max')):.2f}  don {max(g('F_don')):.2f}"
                          f"  eps {max(g('eps_max')) * 100:.1f}%  amp {max(g('eps_amp')) * 100:.2f}% (mean"
                          f" {max(g('eps_amp_mean')) * 100:.1f}%)  tilt {min(g('tilt_settled_deg')):.1f}-{max(g('tilt_settled_deg')):.1f}"
                          f"  rock {max(g('tilt_rock_deg')):.1f}  wrap {max(g('wrap_max')):.2f}")
    elif part == "curves":
        design = json.loads((OUT / "niti_preload_design.json").read_text())
        cv = part_curves(design["d"], design["set"], tuple(design["flare"]))
        plots(design, cv)
        cv["shapes_2d"] = shapes_figure(cv, design)
        print(json.dumps(cv["shapes_2d"], indent=1))
        _save("curves", cv)
    print(f"[{part}] {time.time() - t0:.1f} s")


if __name__ == "__main__":
    main()
