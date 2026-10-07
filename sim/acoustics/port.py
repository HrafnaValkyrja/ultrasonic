"""Mic acoustic port model: free-field pressure at the lid outer face -> pressure at the MEMS diaphragm,
relative to the datasheet condition.  Lumped acoustic transmission line with visco-thermal losses.

    free field --(baffle/plate)--> hex window (short tube, flanged radiation) --step--> lid bore (tube)
      --> 1.5 mm open gap (parallel-plate two-port, lateral offset)  OR  sealed chimney (tube)
      --> board hole (tube) --> solder-standoff ring (shunt) --> mic package port (tube) --> front volume (shunt) = diaphragm

What it predicts / does not (read this before using a number):
 * It predicts the CHANGE of the response caused by OUR duct, relative to a reference condition (ref='ideal' flush port,
   or a short PCB hole), with the mic's own (unpublished) port + front-volume resonance represented by a calibrated
   2-parameter Helmholtz model.  The datasheet curve (+14.7 dB at 25 kHz, ~+8 dB 35-65 kHz) already contains the mic and
   an UNKNOWN test fixture; the e2e chain multiplies it by this ratio.
 * It does NOT know the mic internals (front volume, port length, diaphragm), the real cavity reflections (the F-side cavity
   walls), the parts in the gap, surface roughness, or the mesh's reactance.  Those are bands (sweeps / Monte Carlo) or flagged.
 * Open gap, two limits: Opt(cavity="matched") = infinite plates (walls absorb; valid >= ~15 kHz, below it the channel's
   compliance Lx Lz h is added and numbers are indicative) and Opt(cavity="channel") = rigid empty rectangle between the lid
   lip and the clamp ribs (gap.rect_n0_dz: wall reflections + channel modes).  The real gap (parts, lip slot, edge leaks)
   lies between them; neither sees the parts (heavy run H-A1).
Run: see sim/acoustics/smoke.sh.
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
from dataclasses import dataclass, replace
from pathlib import Path

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):   # shared machine: no 32-thread BLAS storms
    os.environ.setdefault(_v, "2")
import numpy as np  # noqa: E402
from scipy import interpolate, optimize  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from gap import gap_z, rect_n0_dz  # noqa: E402
from geometry import Geom, MM, load as load_geom  # noqa: E402
from narrow import (AIR, Air, cavity_y, chain, flanged_piston_z, mesh_series, series_mass_abcd,  # noqa: E402
                    series_z_abcd, shunt_y_abcd, step_delta, tube_abcd)

F_GRID = np.geomspace(1e3, 1e5, 500)
GAP_FGRID = np.geomspace(3e3, 1.2e5, 120)          # gap Z is smooth (no resonance in an infinite-plate waveguide): spline between
LOW_F_PATCH_HZ = 15e3                             # matched gap: below this a lumped compliance of the gap channel (Lx Lz h) is added


@dataclass(frozen=True)
class Opt:
    gap: str = "open"            # open | chimney
    cavity: str = "matched"      # open gap only: matched = infinite plates (walls fully absorbing) | channel = rigid empty rectangle (walls fully reflecting)
    a_chim: float = 1.05e-3      # chimney / gasket inner radius (sealed duct from the lid bore exit to the board hole)
    mesh: str = "none"           # none | mouth | floor
    r_mesh: float = 24.0         # rayl; 24 = 0.25 dB one-way infinite-tube insertion loss (brief: AN-000221, unverified)
    recess: bool = True          # hex window present
    cavity_patch: bool = True


@dataclass(frozen=True)
class Mic:
    """Calibrated mic internals (unpublished in the datasheet): front volume, damping; port length from Geom."""
    V_f: float = 0.8e-9
    eta: float = 0.2
    r_front: float = 0.5e-3


# ---------------------------------------------------------------------------------------------------- chain
def _gap_two_port(f, g: Geom, opt: Opt, air):
    from scipy.interpolate import CubicSpline
    fc = GAP_FGRID
    Z11, Z12, Z22 = gap_z(fc, g.h_gap, g.a_bore, g.a_hole, g.offset, air)
    out = []
    for Z in (Z11, Z12, Z22):
        out.append(CubicSpline(np.log(fc), Z.real)(np.log(f)) + 1j * CubicSpline(np.log(fc), Z.imag)(np.log(f)))
    Z11, Z12, Z22 = out
    if opt.cavity == "channel":                              # finite rigid channel: wall reflections + channel modes (incl. its compliance)
        d11, d12, d22 = rect_n0_dz(f, g.h_gap, g.a_bore, g.a_hole, (g.bore_cx, g.bore_cz), (g.hole_cx, g.hole_cz), g.cav_lx, g.cav_lz, air)
        Z11, Z12, Z22 = Z11 + d11, Z12 + d12, Z22 + d22
    elif opt.cavity_patch:                                   # matched: uniform-pressure compliance of the channel (valid << c/2L)
        Zc = 1.0 / (1j * 2 * np.pi * f * g.cav_lx * g.cav_lz * g.h_gap / (air.rho * air.c ** 2))
        Z11, Z12, Z22 = Z11 + Zc, Z12 + Zc, Z22 + Zc
    T = np.empty(f.shape + (2, 2), complex)
    T[..., 0, 0] = Z11 / Z12
    T[..., 0, 1] = (Z11 * Z22 - Z12 * Z12) / Z12
    T[..., 1, 0] = 1.0 / Z12
    T[..., 1, 1] = Z22 / Z12
    return T


def transfer(f, g: Geom, opt: Opt, mic: Mic, air: Air = AIR, *, ref: str | None = None):
    """Complex p_diaphragm / p_blocked(outer face).  ref=None: our path.  ref='ideal': port flush in the baffle, mic only.
    ref='pcb:<t_mm>:<D_mm>': mic on a PCB of thickness t with a hole of diameter D facing the free field."""
    f = np.asarray(f, float)
    a_p, l_p = g.a_port, g.l_port
    mic_in = [tube_abcd(f, a_p, l_p, air), series_mass_abcd(f, a_p, step_delta(a_p, mic.r_front), air),
              shunt_y_abcd(cavity_y(f, mic.V_f, air, loss_tan=mic.eta))]
    if ref == "ideal":
        Zs = flanged_piston_z(f, a_p, air)
        return 1.0 / ((chain(*mic_in))[..., 0, 0] + Zs * (chain(*mic_in))[..., 1, 0])
    if ref and ref.startswith("pcb:"):
        _, t_mm, d_mm = ref.split(":")
        a_r, t_r = float(d_mm) * MM / 2, float(t_mm) * MM
        Zs = flanged_piston_z(f, a_r, air)
        V_ring = math.pi * g.a_ring ** 2 * g.t_standoff
        els = [tube_abcd(f, a_r, t_r, air), shunt_y_abcd(cavity_y(f, V_ring, air)),
               series_mass_abcd(f, a_p, step_delta(a_p, a_r), air)] + mic_in
        T = chain(*els)
        return 1.0 / (T[..., 0, 0] + Zs * T[..., 1, 0])
    # ---- our path
    els = []
    if opt.recess and g.d_recess > 0:
        Zs = flanged_piston_z(f, g.a_recess, air)
        if opt.mesh == "mouth":
            els.append(mesh_series(f, opt.r_mesh, math.pi * g.a_recess ** 2))
        els.append(tube_abcd(f, g.a_recess, g.d_recess, air))
        els.append(series_mass_abcd(f, g.a_bore, step_delta(g.a_bore, g.a_recess), air))
    else:
        Zs = flanged_piston_z(f, g.a_bore, air)
        if opt.mesh == "mouth":
            els.append(mesh_series(f, opt.r_mesh, math.pi * g.a_bore ** 2))
    if opt.mesh == "floor":
        els.append(mesh_series(f, opt.r_mesh, math.pi * g.a_bore ** 2))
    els.append(tube_abcd(f, g.a_bore, g.l_bore, air))
    if opt.gap == "open":
        els.append(_gap_two_port(f, g, opt, air))
    else:
        els.append(series_mass_abcd(f, g.a_bore, step_delta(g.a_bore, opt.a_chim), air))
        els.append(tube_abcd(f, opt.a_chim, g.h_gap, air))
        els.append(series_mass_abcd(f, g.a_hole, step_delta(g.a_hole, opt.a_chim), air))
    els.append(tube_abcd(f, g.a_hole, g.t_board, air))
    V_ring = math.pi * g.a_ring ** 2 * g.t_standoff
    els.append(shunt_y_abcd(cavity_y(f, V_ring, air)))
    els.append(series_mass_abcd(f, a_p, step_delta(a_p, g.a_hole), air))
    T = chain(*(els + mic_in))
    return 1.0 / (T[..., 0, 0] + Zs * T[..., 1, 0])


# ---------------------------------------------------------------------------------------------------- mic calibration
_CAL_CACHE: dict = {}


def calibrate_mic(g: Geom, ref: str = "ideal", f_peak=25e3, peak_db=14.7, f_norm=1e3, air=AIR) -> Mic:
    """Cached front end of _calibrate_mic (the reference chain depends only on the mic port, ring and standoff)."""
    key = (ref, g.a_port, g.l_port, g.a_ring, g.t_standoff, f_peak, peak_db, f_norm, air)
    if key not in _CAL_CACHE:
        _CAL_CACHE[key] = _calibrate_mic(g, ref, f_peak, peak_db, f_norm, air)
    return _CAL_CACHE[key]


def _calibrate_mic(g: Geom, ref: str = "ideal", f_peak=25e3, peak_db=14.7, f_norm=1e3, air=AIR) -> Mic:
    """Choose (V_f, eta) so that the REFERENCE chain reproduces the datasheet's feature: peak at f_peak, +peak_db re f_norm.
    Assumption (stated in the output): the datasheet curve's 25 kHz peak is the mic's own port/front-volume resonance as seen
    through the reference condition.  Under-determined (one number each); the Monte Carlo spreads the reference assumption."""
    fs = np.geomspace(5e3, 1.0e5, 700)

    def feat(x):
        m = Mic(V_f=math.exp(x[0]) * 1e-9, eta=math.exp(x[1]), r_front=0.5e-3)
        H = np.abs(transfer(fs, g, Opt(), m, air, ref=ref))
        H1 = np.abs(transfer(np.array([f_norm]), g, Opt(), m, air, ref=ref))[0]
        i = int(np.argmax(H[(fs > 8e3) & (fs < 60e3)])) + int(np.argmax(fs > 8e3))
        return fs[i], 20 * np.log10(H[i] / H1)

    def resid(x):
        fp, pk = feat(x)
        return [(fp - f_peak) / 1e3, (pk - peak_db) / 1.0]

    best = None
    for x0 in ([math.log(0.8), math.log(0.2)], [math.log(0.3), math.log(0.1)], [math.log(2.0), math.log(0.5)]):
        r = optimize.least_squares(resid, x0, bounds=([math.log(0.01), math.log(1e-3)], [math.log(20), math.log(3)]))
        if best is None or r.cost < best.cost:
            best = r
    return Mic(V_f=math.exp(best.x[0]) * 1e-9, eta=math.exp(best.x[1]))


# ---------------------------------------------------------------------------------------------------- response container
def ratio(f, g, opt, mic, ref="ideal", air=AIR):
    return transfer(f, g, opt, mic, air) / transfer(f, g, Opt(), mic, air, ref=ref)


def db(x):
    return 20 * np.log10(np.abs(x) + 1e-30)


def band(f, y, lo, hi):
    m = (f >= lo) & (f <= hi)
    return y[m]


def lens_overlap_mm2(r1, r2, d):
    """Area of intersection of two circles (mm^2) - the projected overlap of the lid bore and the board hole."""
    if d >= r1 + r2:
        return 0.0
    if d <= abs(r1 - r2):
        return math.pi * min(r1, r2) ** 2
    a = r1 * r1 * math.acos((d * d + r1 * r1 - r2 * r2) / (2 * d * r1))
    b = r2 * r2 * math.acos((d * d + r2 * r2 - r1 * r1) / (2 * d * r2))
    c = 0.5 * math.sqrt((-d + r1 + r2) * (d + r1 - r2) * (d - r1 + r2) * (d + r1 + r2))
    return a + b - c


def features(f, H):
    """Band metrics of a path ratio H (complex) over the capture band."""
    d = db(H)
    cap = (f >= 20e3) & (f <= 96e3)
    hi = (f >= 80e3) & (f <= 96e3)
    lo = (f >= 20e3) & (f <= 40e3)
    i = int(np.argmax(d * cap - 1e3 * (~cap)))
    j = int(np.argmin(d + 1e3 * (~cap)))
    return dict(mean_20_96_db=float(d[cap].mean()), median_20_96_db=float(np.median(d[cap])), min_20_96_db=float(d[cap].min()), f_min_hz=float(f[j]),
                max_20_96_db=float(d[cap].max()), f_max_hz=float(f[i]), mean_80_96_db=float(d[hi].mean()),
                mean_20_40_db=float(d[lo].mean()), p2p_20_96_db=float(d[cap].max() - d[cap].min()))


def phase_deg(H):
    return np.degrees(np.unwrap(np.angle(H)))


# ---------------------------------------------------------------------------------------------------- scenarios
def size_variant(g: Geom, lid_mm: float, plate_mm: float, chim_mm: float, window: bool) -> Geom:
    """Simplification-study duct (docs/research/simplify/size.md s7): lid wall + plate, sealed chimney of length chim_mm.
    Window kept 0.8 deep at the outer face when the plate is there (as today); bore = the rest of lid + plate."""
    d_rec = min(0.8, lid_mm + plate_mm - 0.1) if window else 0.0
    return g.with_(offset=0.0, h_gap=chim_mm * MM, d_recess=d_rec * MM, l_bore=(lid_mm + plate_mm - d_rec) * MM)


def scenarios(g: Geom):
    """Named designs.  g = the CURRENT design's geometry (geometry.load: hw/current.yaml). Phase 2 (default): g is the r2 duct
    stack, so `phase2_r2` = g as read (U2 hole offset from the board) and the as_built* / chimney / gasket names are what-ifs
    on the r2 stack (as_built = the 0.30 F gap left OPEN, i.e. the VHB duct not sealed). revg: g = Rev F (shell_r1.py)."""
    a0 = g.with_(offset=0.0)
    r2 = g.info.get("design") not in (None, "revg")       # g already is the Phase-2 stack: keep its measured offset
    sealed = lambda a, **kw: Opt(gap="chimney", a_chim=a, **kw)  # noqa: E731
    return {
        "as_built": (g, Opt()),                                                   # open 1.5 mm gap, walls absorbing (smooth limit)
        "as_built_channel": (g, Opt(cavity="channel")),                           # open gap, rigid empty channel (resonant limit)
        "chimney_d1.0": (a0, sealed(0.5e-3)),                                     # sealed straight D1.0 duct lid -> board (gasket ID 1.0)
        "chimney_id1.4": (a0, sealed(0.7e-3)),
        "gasket_id2.1": (g, sealed(1.05e-3)),                                     # sealed gasket ID 2.1 round both holes (5.2 mm3 ring)
        "size_s1": (size_variant(g, 0.8, 0.7, 1.15, True), sealed(0.5e-3)),       # size study S1: 0.8 lid + 0.7 plate + 1.15 chimney
        "size_s2": (size_variant(g, 1.0, 0.0, 1.15, False), sealed(0.5e-3, recess=False)),   # S2: plate removed, 1.0 lid
        # Phase 2 (hw/mech/shell_r2.py, 2026-10-07): lid 0.8 + plate 0.7, hex window 0.8 deep, reamed D1.0 bore, then the
        # D1.0 hole in the 0.25 VHB across the 0.30 F gap (sealed), board hole D0.6; duct axis on the hole (gauge pin)
        "phase2_r2": (g if r2 else size_variant(g, 0.8, 0.7, 0.30, True), sealed(0.5e-3)),
        "phase2_r2+mesh_floor": (g if r2 else size_variant(g, 0.8, 0.7, 0.30, True), sealed(0.5e-3, mesh="floor")),
        "as_built+mesh_mouth": (g, Opt(mesh="mouth")),
        "chimney_d1.0+mesh_mouth": (a0, sealed(0.5e-3, mesh="mouth")),
        "chimney_d1.0+mesh_floor": (a0, sealed(0.5e-3, mesh="floor")),
    }


def run_scenarios(g, mic, ref="ideal"):
    f = F_GRID
    out = {}
    for name, (gg, oo) in scenarios(g).items():
        H = ratio(f, gg, oo, mic, ref)
        out[name] = dict(H=H, **features(f, H))
    return out


# ---------------------------------------------------------------------------------------------------- Monte Carlo
def monte_carlo(g: Geom, base_opt: Opt, n=60, seed=1, ref_mode="mixed", tol=0.2e-3, offset_range=None):
    """Draw geometry (+-tol on bore/hole radii and lengths, gap, board thickness 0.8|1.6), offset, mesh r, mic ref assumption.
    Returns f, array of dB ratios [n, nf] and the draws."""
    rng = np.random.default_rng(seed)
    f = F_GRID
    refs = ["ideal", "pcb:0.8:0.5", "pcb:1.6:0.8"] if ref_mode == "mixed" else [ref_mode]
    mics = {r: calibrate_mic(g, r) for r in refs}
    Hs, draws = [], []
    for k in range(n):
        r = refs[k % len(refs)]
        gg = g.with_(a_bore=g.a_bore + rng.uniform(-tol, tol) / 2, l_bore=g.l_bore + rng.uniform(-tol, tol),
                     a_hole=max(0.15e-3, g.a_hole + rng.uniform(-tol, tol) / 2),
                     h_gap=g.h_gap + rng.uniform(-tol, tol), t_board=g.t_board + rng.uniform(-0.1e-3, 0.1e-3),
                     offset=(rng.uniform(*offset_range) if offset_range else max(0.0, g.offset + rng.uniform(-tol, tol))),
                     l_port=g.l_port + rng.uniform(-0.1e-3, 0.1e-3))
        if base_opt.cavity == "channel":                     # channel modes move with the walls and the parts: +-10 % size, +-0.5 mm bore position
            gg = gg.with_(cav_lx=g.cav_lx * rng.uniform(0.9, 1.1), cav_lz=g.cav_lz * rng.uniform(0.9, 1.1),
                          bore_cx=g.bore_cx + rng.uniform(-0.5e-3, 0.5e-3), bore_cz=g.bore_cz + rng.uniform(-0.5e-3, 0.5e-3))
        oo = replace(base_opt, r_mesh=base_opt.r_mesh * 10 ** rng.uniform(-0.7, 0.7))
        H = ratio(f, gg, oo, mics[r], r)
        Hs.append(db(H))
        draws.append(dict(ref=r, a_bore_mm=gg.a_bore / MM, l_bore_mm=gg.l_bore / MM, a_hole_mm=gg.a_hole / MM, h_gap_mm=gg.h_gap / MM,
                          t_board_mm=gg.t_board / MM, offset_mm=gg.offset / MM, r_mesh=oo.r_mesh))
    return f, np.array(Hs), draws


if __name__ == "__main__":
    t0 = time.time()
    g = load_geom()
    mic = calibrate_mic(g)
    print("mic", mic, "calib s", round(time.time() - t0, 2))
    res = run_scenarios(g, mic)
    for k, v in res.items():
        print(f"{k:28s}", {kk: round(vv, 2) for kk, vv in v.items() if kk != "H"})
    print("t", round(time.time() - t0, 2))
