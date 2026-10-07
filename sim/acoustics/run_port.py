"""Mic-port driver: scenarios, sweeps, Monte Carlo bands, spec checks, interface files for the e2e chain, figures.

    python3 sim/acoustics/run_port.py [--board path.kicad_pcb] [--mc 60] [--no-plot]
Writes sim/acoustics/out/: port_response.json (+ port_response_<design>.json), port_results.json, port_*.png (dark).
Fenced smoke: ~20 s, < 0.6 GB.  Layout-agnostic: geometry from hw/mech/shell_r1.py (AST) and the newest board's U2 NPTH (pcbnew).
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
from dataclasses import replace
from pathlib import Path

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "2")
import numpy as np  # noqa: E402
from scipy import signal  # noqa: E402

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "tools"))
from geometry import MM, load as load_geom  # noqa: E402
from narrow import AIR, Air  # noqa: E402
from port import (F_GRID, Opt, calibrate_mic, db, features, lens_overlap_mm2, monte_carlo, phase_deg,  # noqa: E402
                  ratio, scenarios, transfer)

OUT = HERE / "out"
OUT.mkdir(exist_ok=True)
TODAY = "2026-10-02"
# model-form error of the lumped chain vs the axisymmetric FEM (selfcheck.py, aligned designs): added to the bands
MODEL_FORM_DB = dict(lo_below60k=-1.5, hi_below60k=+1.5, lo_above60k=-1.0, hi_above60k=+3.5)
R14_BAND_HZ = (20e3, 85e3)  # processed band (sim/dsp/pipeline.py algo_b band_hz); R14 ripple rules apply here (integrator 2026-10-02)
PRINT_TOL_MM = 0.1          # lateral position tolerance of a printed duct/boss vs the lid bore (ASSUMED, resin/FDM practice)
PARTS_RESIDUAL_DB = 1.5    # open gap only: parts in the gap / lip under-slot / edge leaks, beyond the matched..channel bracket (engineering margin)
SPEC = dict(s8_board="spec L509", s8_hole="spec L510", s8_rules="spec L511", r14="spec R14 L608", r8="spec R8 L601", d13="spec D13 L232",
            o12="spec O12 L638", d2="spec task D2 L690", c8="spec task C8 L683", e3="spec E3 L700")
DS = json.loads((REPO / "sim/data/sph0641_ultrasonic_response.json").read_text())     # datasheet Rev B sheet 7, 10-80 kHz, re 1 kHz


def in_pod_db(f, H):
    """Predicted in-pod mic response re 1 kHz = datasheet curve (fixture) + our path ratio; valid where the datasheet is (10-80 kHz)."""
    return np.interp(f / 1e3, DS["f_khz"], DS["db_re_1k"]) + db(H)


MC_DESIGNS = ("as_built", "as_built_channel", "chimney_d1.0", "gasket_id2.1", "phase2_r2")
IF_FILES = {"as_built": "port_response.json", "chimney_d1.0": "port_response_chimney_d1.0.json", "gasket_id2.1": "port_response_gasket_id2.1.json"}


def peaks(f, H, prominence=3.0, lo=5e3, hi=100e3):
    d = db(H)
    m = (f >= lo) & (f <= hi)
    idx, pr = signal.find_peaks(d[m], prominence=prominence)
    fm, dm = f[m], d[m]
    out = []
    for i, p in zip(idx, pr["prominences"]):
        half = dm[i] - 3.0
        l = i
        while l > 0 and dm[l] > half:
            l -= 1
        r = i
        while r < len(dm) - 1 and dm[r] > half:
            r += 1
        q = fm[i] / max(fm[r] - fm[l], 1.0)
        out.append(dict(f_hz=round(float(fm[i]), 0), db=round(float(dm[i]), 2), prom_db=round(float(p), 2), q=round(float(q), 1)))
    notches, pn = signal.find_peaks(-d[m], prominence=prominence)
    nn = [dict(f_hz=round(float(fm[i]), 0), db=round(float(dm[i]), 2), prom_db=round(float(p), 2)) for i, p in zip(notches, pn["prominences"])]
    return out, nn


def write_if_port(path, f, H, lo, hi, p05, p95, cond, extra=None):
    d = dict(schema="IF-ACOUSTIC-PORT v1 (docs/sim/e2e-chain.yaml interfaces)", date=TODAY,
             ref="p_diaphragm(ours) / p_diaphragm(reference) at equal free-field pressure; reference = mic port flush in a baffle "
                 "(mic internals calibrated to the datasheet 25 kHz / +14.7 dB feature). consumed by stages.AcousticPort.curve_db (mag_db only)",
             f_hz=[round(float(x), 2) for x in f], mag_db=[round(float(x), 3) for x in db(H)],
             phase_deg=[round(float(x), 2) for x in phase_deg(H)],
             mag_db_min=[round(float(x), 3) for x in lo], mag_db_max=[round(float(x), 3) for x in hi],
             mag_db_p05=[round(float(x), 3) for x in p05], mag_db_p95=[round(float(x), 3) for x in p95], cond=cond)
    if extra:
        d.update(extra)
    Path(path).write_text(json.dumps(d))


def widen(f, lo, hi, open_gap):
    lo = lo + np.where(f < 60e3, MODEL_FORM_DB["lo_below60k"], MODEL_FORM_DB["lo_above60k"]) - (PARTS_RESIDUAL_DB if open_gap else 0)
    hi = hi + np.where(f < 60e3, MODEL_FORM_DB["hi_below60k"], MODEL_FORM_DB["hi_above60k"]) + (PARTS_RESIDUAL_DB if open_gap else 0)
    return lo, hi


def tornado(g, opt, mic, ref):
    """One-at-a-time +-0.2 mm (and other) swings about a design: change of band-mean and peak-to-peak (20-96 kHz)."""
    f = F_GRID
    base = features(f, ratio(f, g, opt, mic, ref))
    rows = []

    def add(name, lo_g, hi_g, lo_label, hi_label, lo_air=None, hi_air=None):
        r = []
        for gg, air in ((lo_g, lo_air), (hi_g, hi_air)):
            if air is None:
                H = ratio(f, gg, opt, mic, ref)
            else:
                H = transfer(f, gg, opt, mic, air) / transfer(f, gg, Opt(), mic, air, ref=ref)
            r.append(features(f, H))
        rows.append(dict(param=name, low=lo_label, high=hi_label,
                         d_mean_lo=round(r[0]["mean_20_96_db"] - base["mean_20_96_db"], 2), d_mean_hi=round(r[1]["mean_20_96_db"] - base["mean_20_96_db"], 2),
                         d_p2p_lo=round(r[0]["p2p_20_96_db"] - base["p2p_20_96_db"], 2), d_p2p_hi=round(r[1]["p2p_20_96_db"] - base["p2p_20_96_db"], 2)))
    t = 0.2e-3
    add("bore diameter +-0.2 mm", g.with_(a_bore=g.a_bore - t / 2), g.with_(a_bore=g.a_bore + t / 2), f"{2 * g.a_bore / MM - 0.2:.1f}", f"{2 * g.a_bore / MM + 0.2:.1f}")
    add("bore length +-0.2 mm", g.with_(l_bore=g.l_bore - t), g.with_(l_bore=g.l_bore + t), f"{g.l_bore / MM - 0.2:.2f}", f"{g.l_bore / MM + 0.2:.2f}")
    add("board hole diameter +-0.2 mm (spec 0.6-1.0)", g.with_(a_hole=g.a_hole - t / 2), g.with_(a_hole=g.a_hole + t / 2), f"{2 * g.a_hole / MM - 0.2:.1f}", f"{2 * g.a_hole / MM + 0.2:.1f}")
    add("board thickness 0.8 -> 1.6 mm", g, g.with_(t_board=1.6e-3), f"{g.t_board / MM:.1f}", "1.6")
    add("lid-board gap / chimney length +-0.2 mm", g.with_(h_gap=g.h_gap - t), g.with_(h_gap=g.h_gap + t), f"{g.h_gap / MM - 0.2:.2f}", f"{g.h_gap / MM + 0.2:.2f}")
    add("window depth 0.4 / 1.2 mm", g.with_(d_recess=0.4e-3), g.with_(d_recess=1.2e-3), "0.4", "1.2")
    add("bore-hole offset 0 / 1.0 mm (open gap only)", g.with_(offset=0.0), g.with_(offset=1.0e-3), "0", "1.0")
    add("mic port length 0.15 / 0.35 mm (ASSUMED)", g.with_(l_port=0.15e-3), g.with_(l_port=0.35e-3), "0.15", "0.35")
    add("standoff 0.03 / 0.10 mm (ASSUMED)", g.with_(t_standoff=0.03e-3), g.with_(t_standoff=0.10e-3), "0.03", "0.10")
    add("air temperature 0 / 35 C", g, g, "0 C", "35 C", Air(T=273.15), Air(T=308.15))
    return base, rows


def quarter_wave_check(g, mic):
    """Sealed straight ducts of different stacks: first acoustic resonance (absolute response, mic included, re 1 kHz) vs c/(4L)."""
    rows = []
    stacks = {"today's stack sealed (window 0.8 + bore 0.9 + chimney 1.5 + hole 0.8 = 4.0 mm)": (g.with_(offset=0.0), Opt(gap="chimney", a_chim=0.5e-3)),
              "size S1 (window 0.8 + bore 0.7 + chimney 1.15 + hole 0.8 = 3.45 mm)": scenarios(g)["size_s1"],
              "size S2 (bore 1.0 + chimney 1.15 + hole 0.8 = 2.95 mm, no window)": scenarios(g)["size_s2"],
              "brief: 3 mm uniform D1.0 tube (bore 2.2 + hole 0.8 as D1.0)": (g.with_(offset=0.0, d_recess=0.0, l_bore=0.7e-3, h_gap=1.5e-3, a_hole=0.5e-3),
                                                                             Opt(gap="chimney", a_chim=0.5e-3, recess=False))}
    f = np.geomspace(5e3, 1e5, 1500)
    for name, (gg, oo) in stacks.items():
        L = (gg.d_recess if oo.recess else 0) + gg.l_bore + gg.h_gap + gg.t_board
        Ha = transfer(f, gg, oo, mic) / transfer(np.array([1e3]), gg, oo, mic)[0]
        pk, _ = peaks(f, Ha, prominence=2.0)
        Hr = ratio(f, gg, oo, mic, "ideal")
        pr, _ = peaks(f, Hr, prominence=3.0)
        rows.append(dict(stack=name, L_mm=round(L / MM, 2), c_over_4L_khz=round(AIR.c / (4 * L) / 1e3, 1),
                         abs_peaks=[dict(f_khz=round(p["f_hz"] / 1e3, 1), db_re_1k=p["db"], q=p["q"]) for p in pk],
                         ratio_peaks=[dict(f_khz=round(p["f_hz"] / 1e3, 1), db=p["db"], q=p["q"]) for p in pr]))
    return rows


def spec_checks(name, gg, oo, H, f, g_info, mc=None):
    cap = (f >= 20e3) & (f <= 96e3)
    d = db(H)
    med = float(np.median(d[cap]))
    ft = features(f, H)
    ov = lens_overlap_mm2(gg.a_bore / MM, gg.a_hole / MM, gg.offset / MM)
    a_h = math.pi * (gg.a_hole / MM) ** 2
    out = []

    def chk(id_, text, ok, val, src, basis):
        out.append(dict(id=id_, text=text, status=("PASS" if ok else "FAIL"), value=val, src=src, basis=basis))
    bt = g_info.get("board_thickness_setting_mm")
    chk("S8-board", "board <= 0.8 mm", gg.t_board / MM <= 0.8 + 1e-9 and (bt is None or bt <= 0.8 + 1e-9),
        f"{gg.t_board / MM:.2f} mm shell; board file setting {bt} mm", SPEC["s8_board"], "spec")
    chk("S8-hole", "port hole 0.6-1.0 mm", 0.6 - 1e-9 <= 2 * gg.a_hole / MM <= 1.0 + 1e-9, f"D{2 * gg.a_hole / MM:.2f} (0.6 = lower edge)", SPEC["s8_hole"], "spec")
    if oo.gap == "open":
        chk("S8-nogasketcavity", "no gasket cavity", False, f"open {gg.h_gap / MM:.2f} mm gap: the port opens into the whole lid-board channel "
            f"({gg.cav_lx / MM:.1f} x {gg.cav_lz / MM:.1f} x {gg.h_gap / MM:.1f} mm = {gg.cav_lx * gg.cav_lz * gg.h_gap / MM ** 3:.0f} mm3, parts not subtracted)", SPEC["s8_rules"], "spec")
    else:
        v_ring = math.pi * (oo.a_chim ** 2 - gg.a_bore ** 2) * gg.h_gap / MM ** 3 if oo.a_chim > gg.a_bore else 0.0
        chk("S8-nogasketcavity", "no gasket cavity", v_ring < 1.0, f"sealed duct ID {2 * oo.a_chim / MM:.1f}: side volume beyond the bore {max(v_ring, 0):.1f} mm3 (PASS < 1 mm3, basis derived)", SPEC["s8_rules"], "spec")
    chk("S8-opening-over-hole", "opening directly over the hole", ov >= 0.999 * a_h,
        f"bore-hole offset {gg.offset / MM:.2f} mm; projected overlap {ov:.3f} of {a_h:.3f} mm2 hole area", SPEC["s8_rules"] + "; ECR-0011", "spec")
    chk("S8-mesh", "thin mesh, never foam", oo.mesh != "none", "no mesh designed (task D2 open)" if oo.mesh == "none" else f"mesh {oo.r_mesh:.0f} rayl at the {oo.mesh}",
        SPEC["s8_rules"] + "; " + SPEC["d2"], "spec")
    mean_ok = ft["mean_20_96_db"] >= -6 and (mc is None or mc["mean_20_96_db"]["p05"] >= -9)
    chk("R14-level", "band mean 20-96 kHz >= -6 dB re a flush port (MC p05 >= -9 dB)", mean_ok,
        f"{ft['mean_20_96_db']:+.1f} dB" + (f" (MC p05 {mc['mean_20_96_db']['p05']:+.1f})" if mc else ""), SPEC["r14"] + "; " + SPEC["r8"], "assumed")
    # ripple rules on what the mic will actually deliver in the pod (datasheet x path ratio) over the PROCESSED band 20-85 kHz
    # (algo_b band_hz, sim/dsp/pipeline.py). The datasheet curve ends at 80 kHz: held at its 80 kHz value above (ASSUMED, stated).
    # 20-80 kHz (datasheet range only) and 20-96 kHz (MVP band, spec L28) are reported as info. Integrator fix 2026-10-02:
    # the old 20-80 kHz window hid the sealed duct's Q16 resonance at 84.7 kHz.
    ip = in_pod_db(f, H)
    m8 = (f >= 20e3) & (f <= R14_BAND_HZ[1])
    med8 = float(np.median(ip[m8]))
    j, i = int(np.argmin(np.where(m8, ip, 1e9))), int(np.argmax(np.where(m8, ip, -1e9)))
    chk("R14-notch", "in-pod response (datasheet x path) 20-85 kHz: no notch deeper than 10 dB below its median", ip[j] - med8 >= -10,
        f"deepest {ip[j] - med8:+.1f} dB re median at {f[j] / 1e3:.1f} kHz (path ratio alone: {ft['min_20_96_db'] - med:+.1f} at {ft['f_min_hz'] / 1e3:.1f} kHz)",
        SPEC["r14"], "assumed")
    chk("R14-peak", "in-pod response 20-85 kHz: no peak more than 15 dB above its median (EQ gain/Q limit)", ip[i] - med8 <= 15,
        f"highest {ip[i] - med8:+.1f} dB re median at {f[i] / 1e3:.1f} kHz (path ratio alone 20-96 kHz: {ft['max_20_96_db'] - med:+.1f} at {ft['f_max_hz'] / 1e3:.1f} kHz)",
        SPEC["r14"] + "; " + SPEC["c8"], "assumed")
    win = {}
    for lo_, hi_ in ((20e3, 80e3), (20e3, 85e3), (20e3, 96e3)):
        mw = (f >= lo_) & (f <= hi_)
        mdw = float(np.median(ip[mw]))
        jw, iw = int(np.argmin(np.where(mw, ip, 1e9))), int(np.argmax(np.where(mw, ip, -1e9)))
        win[f"{int(lo_ / 1e3)}_{int(hi_ / 1e3)}k"] = dict(notch_db=round(ip[jw] - mdw, 1), f_notch_khz=round(f[jw] / 1e3, 1),
                                                          peak_db=round(ip[iw] - mdw, 1), f_peak_khz=round(f[iw] / 1e3, 1))
    out.append(dict(id="info-in-pod", in_pod_db_re_1k={f"{k}k": round(float(np.interp(k * 1e3, f, ip)), 1) for k in (20, 25, 30, 40, 50, 60, 70, 80, 85, 90)},
                    p2p_20_85_db=round(float(ip[m8].max() - ip[m8].min()), 1), windows_re_median=win,
                    note="datasheet held flat at its 80 kHz value (+12.7 dB re 1 kHz) above 80 kHz: assumption"))
    # sealed duct: lateral tolerance stack vs the geometric rule offset <= r_duct - r_hole (the lumped duct cannot see offset)
    sl = g_info.get("board_slide_mm")
    if oo.gap != "open" and sl:
        allow = max(oo.a_chim - gg.a_hole, 0.0) / MM
        dx_n = gg.offset / MM * math.cos(gg.off_ang)
        dz_n = gg.offset / MM * math.sin(gg.off_ang)
        worst = max(math.hypot(dx_n + sx, dz_n + sz) for sx in (-sl["x_minus"], sl["x_plus"]) for sz in (-sl["z_minus"], sl["z_plus"])) + PRINT_TOL_MM
        chk("S8-duct-alignment-stack", "sealed duct: nominal offset + free board slide + print tolerance <= r_duct - r_hole (needs a board x-stop or a duct-locating feature)",
            worst <= allow, f"worst {worst:.2f} mm (slide x -{sl['x_minus']}/+{sl['x_plus']}, z -{sl['z_minus']}/+{sl['z_plus']}, print {PRINT_TOL_MM} mm ASSUMED) vs allowed {allow:.2f} mm",
            SPEC["s8_rules"] + "; docs/system/00-whole.md risk 8 (no x stop), risks 12/20", "derived")
    return out


def main(argv):
    n_mc = int(argv[argv.index("--mc") + 1]) if "--mc" in argv else 60
    board = argv[argv.index("--board") + 1] if "--board" in argv else None
    plot = "--no-plot" not in argv
    t0 = time.time()
    g = load_geom(board)
    f = F_GRID
    refs = ["ideal", "pcb:0.8:0.5", "pcb:1.6:0.8"]
    mics = {r: calibrate_mic(g, r) for r in refs}
    mic = mics["ideal"]
    res = dict(date=TODAY, geometry={k: round(v / MM, 4) for k, v in g.__dict__.items() if isinstance(v, float) and k != "off_ang"},
               geometry_src=g.src, geometry_info=g.info, warnings=list(g.warnings),
               mic_calibrated={k: (v * 1e9 if k == "V_f" else v) for k, v in mic.__dict__.items()})
    res["mic_calibrated"]["V_f_unit"] = "mm^3 (V_f), eta = compliance loss tangent"
    # ---- scenarios
    sc = scenarios(g)
    a0 = g.with_(offset=0.0)
    sc["chimney_d1.0_hole1.0"] = (a0.with_(a_hole=0.5e-3), Opt(gap="chimney", a_chim=0.5e-3))
    sc["chimney_d1.0_nowindow"] = (a0.with_(d_recess=0.0, l_bore=a0.l_bore + a0.d_recess), Opt(gap="chimney", a_chim=0.5e-3, recess=False))
    scen = {}
    for name, (gg, oo) in sc.items():
        H = ratio(f, gg, oo, mic, "ideal")
        pk, nt = peaks(f, H)
        Ha = transfer(f, gg, oo, mic) / transfer(np.array([1e3]), gg, oo, mic)[0]
        pka, _ = peaks(f, Ha, prominence=2.0)
        scen[name] = dict(H=H, feat={k: round(v, 2) for k, v in features(f, H).items()}, peaks=pk, notches=nt, abs_peaks_re_1k=pka,
                          offset_mm=round(gg.offset / MM, 3), overlap_mm2=round(lens_overlap_mm2(gg.a_bore / MM, gg.a_hole / MM, gg.offset / MM), 3),
                          gap=oo.gap, cavity=oo.cavity, mesh=oo.mesh, chimney_id_mm=(round(2 * oo.a_chim / MM, 2) if oo.gap == "chimney" else None),
                          stack_mm=dict(window=round(gg.d_recess / MM if oo.recess else 0, 2), bore=round(gg.l_bore / MM, 2), gap_or_chimney=round(gg.h_gap / MM, 2),
                                        board=round(gg.t_board / MM, 2), hole_d=round(2 * gg.a_hole / MM, 2)))
    # ---- Monte Carlo bands
    mc = {}
    for name in MC_DESIGNS:
        gg, oo = sc[name]
        sealed = oo.gap == "chimney"
        n_d = n_mc if oo.cavity != "channel" else max(n_mc // 2, 12)          # channel draws cost 4x: half the draws, no separate tight run
        fm, A, draws = monte_carlo(gg, oo, n=n_d, seed=7, tol=0.2e-3, offset_range=(0.0, 0.2e-3) if sealed else None)
        if oo.cavity == "channel":
            At = A
        else:
            fm, At, _ = monte_carlo(gg, oo, n=n_mc, seed=8, tol=0.075e-3, offset_range=(0.0, 0.1e-3) if sealed else None)
        mc[name] = dict(A=A, At=At, n=n_d)
    # ---- sweeps
    sweeps = {}
    rows = []
    for o in np.linspace(0, 1.2, 13):
        H = ratio(f, g.with_(offset=o * MM), Opt(), mic, "ideal")
        ft = features(f, H)
        rows.append(dict(offset_mm=round(float(o), 2), overlap_mm2=round(lens_overlap_mm2(g.a_bore / MM, g.a_hole / MM, float(o)), 3),
                         mean_20_96_db=round(ft["mean_20_96_db"], 2), min_20_96_db=round(ft["min_20_96_db"], 2), mean_80_96_db=round(ft["mean_80_96_db"], 2)))
    sweeps["offset_open_gap"] = rows
    rows = []
    for a_ch in (0.5, 0.7, 0.9, 1.05, 1.5, 2.0):
        for dh in (0.6, 0.8, 1.0):
            gg = a0.with_(a_hole=dh / 2 * MM)
            ft = features(f, ratio(f, gg, Opt(gap="chimney", a_chim=a_ch * MM), mic, "ideal"))
            rows.append(dict(chimney_id_mm=2 * a_ch, hole_d_mm=dh, ring_volume_mm3=round(math.pi * max(a_ch ** 2 - (g.a_bore / MM) ** 2, 0) * g.h_gap / MM, 2),
                             mean_20_96_db=round(ft["mean_20_96_db"], 2), notch_re_median=round(ft["min_20_96_db"] - ft["median_20_96_db"], 2),
                             peak_re_median=round(ft["max_20_96_db"] - ft["median_20_96_db"], 2), f_peak_khz=round(ft["f_max_hz"] / 1e3, 1)))
    sweeps["chimney_id_x_hole"] = rows
    rows = []
    i82 = int(np.argmin(np.abs(f - 82.5e3)))
    cap = (f >= 20e3) & (f <= 96e3)
    for dname in ("as_built", "chimney_d1.0"):
        gg, oo0 = sc[dname]
        H0 = ratio(f, gg, oo0, mic, "ideal")
        for place in ("mouth", "floor"):
            for r in (5, 12, 24, 60, 120, 300):
                H = ratio(f, gg, replace(oo0, mesh=place, r_mesh=float(r)), mic, "ideal")
                rows.append(dict(design=dname, place=place, r_mesh_rayl=r, d_mean_20_96_db=round(float(db(H)[cap].mean() - db(H0)[cap].mean()), 2),
                                 d_at_82k_db=round(float(db(H)[i82] - db(H0)[i82]), 2)))
    sweeps["mesh"] = rows
    t_base, t_rows = tornado(g, Opt(), mic, "ideal")
    sweeps["tornado_as_built"] = dict(base_mean=round(t_base["mean_20_96_db"], 2), rows=t_rows)
    t_base2, t_rows2 = tornado(a0, Opt(gap="chimney", a_chim=0.5e-3), mic, "ideal")
    sweeps["tornado_chimney_d1.0"] = dict(base_mean=round(t_base2["mean_20_96_db"], 2), rows=t_rows2)
    rows = []
    for r in refs:
        for name in ("as_built", "chimney_d1.0", "gasket_id2.1"):
            gg, oo = sc[name]
            ft = features(f, ratio(f, gg, oo, mics[r], r))
            rows.append(dict(ref=r, design=name, mean_20_96_db=round(ft["mean_20_96_db"], 2), mean_80_96_db=round(ft["mean_80_96_db"], 2),
                             f_min_hz=round(ft["f_min_hz"]), min_db=round(ft["min_20_96_db"], 2)))
    sweeps["reference_assumption"] = rows
    sweeps["quarter_wave"] = quarter_wave_check(g, mic)

    # ---- MC summaries
    res["mc_summary"] = {}
    for name, m in mc.items():
        A = m["A"]
        mb = A[:, cap].mean(axis=1)
        med = np.median(A[:, cap], axis=1)
        res["mc_summary"][name] = dict(n=m["n"], mean_20_96_db=dict(p05=round(float(np.percentile(mb, 5)), 2), p50=round(float(np.percentile(mb, 50)), 2), p95=round(float(np.percentile(mb, 95)), 2)),
                                       tight_mean_20_96_db_p05_p95=[round(float(x), 2) for x in np.percentile(m["At"][:, cap].mean(axis=1), [5, 95])],
                                       notch_re_median_db=dict(p05=round(float(np.percentile(A[:, cap].min(axis=1) - med, 5)), 2), p50=round(float(np.percentile(A[:, cap].min(axis=1) - med, 50)), 2)),
                                       peak_re_median_db=dict(p50=round(float(np.percentile(A[:, cap].max(axis=1) - med, 50)), 2), p95=round(float(np.percentile(A[:, cap].max(axis=1) - med, 95)), 2)))
        ip = np.interp(f / 1e3, DS["f_khz"], DS["db_re_1k"])[None, :] + A
        for tag, hi_ in (("", R14_BAND_HZ[1]), ("_20_80k", 80e3)):
            m8 = (f >= 20e3) & (f <= hi_)
            ipm = np.median(ip[:, m8], axis=1)
            notch8, peak8 = ip[:, m8].min(axis=1) - ipm, ip[:, m8].max(axis=1) - ipm
            ok = (mb >= -6) & (notch8 >= -10) & (peak8 <= 15)
            res["mc_summary"][name].update({f"in_pod_notch_re_median_db_p05{tag}": round(float(np.percentile(notch8, 5)), 2),
                                            f"in_pod_peak_re_median_db_p95{tag}": round(float(np.percentile(peak8, 95)), 2),
                                            f"r14_all_pass_fraction{tag}": round(float(ok.mean()), 2)})
        res["mc_summary"][name]["r14_band_hz"] = list(R14_BAND_HZ)
    # ---- interface files
    for name, fname in IF_FILES.items():
        gg, oo = sc[name]
        A = mc[name]["A"]
        At = mc[name]["At"]
        lo_raw, hi_raw = A.min(axis=0), A.max(axis=0)
        lot_raw, hit_raw = At.min(axis=0), At.max(axis=0)
        extra_cols = {}
        if oo.gap == "open":                      # bracket: matched (absorbing walls) .. channel (rigid empty channel)
            Ac, Act = mc["as_built_channel"]["A"], mc["as_built_channel"]["At"]
            lo_raw, hi_raw = np.minimum(lo_raw, Ac.min(axis=0)), np.maximum(hi_raw, Ac.max(axis=0))
            lot_raw, hit_raw = np.minimum(lot_raw, Act.min(axis=0)), np.maximum(hit_raw, Act.max(axis=0))
            A = np.vstack([A, Ac])
            extra_cols["mag_db_channel"] = [round(float(x), 3) for x in db(scen["as_built_channel"]["H"])]
        lo, hi = widen(f, lo_raw, hi_raw, oo.gap == "open")
        lot, hit = widen(f, lot_raw, hit_raw, oo.gap == "open")
        p05, p95 = np.percentile(A, 5, axis=0), np.percentile(A, 95, axis=0)
        cond = dict(design=name, mesh="none", gasket=("none: open lid-board gap" if oo.gap == "open" else f"sealed duct ID {2 * oo.a_chim / MM:.1f} mm"),
                    board_mm=round(gg.t_board / MM, 3), port_offset_mm=round(gg.offset / MM, 3), bore_mm=[round(2 * gg.a_bore / MM, 3), round(gg.l_bore / MM, 3)],
                    window_depth_mm=round(gg.d_recess / MM, 3), gap_or_chimney_mm=round(gg.h_gap / MM, 3), hole_mm=round(2 * gg.a_hole / MM, 3),
                    pod="L = R (one board, port on the centre line)", mc_draws=n_mc, geometry_src=g.src)
        Habs = transfer(f, gg, oo, mic)
        H1k = transfer(np.array([1e3]), gg, oo, mic)[0]
        extra = dict(mag_db_abs_re_1khz=[round(float(x), 3) for x in db(Habs / H1k)],
                     abs_note="INFORMATIONAL: model p_diaphragm / p_blocked normalised to its own 1 kHz value, with the calibrated 2-parameter mic. "
                              "Do NOT multiply with the datasheet curve (it already contains the mic). Use mag_db with the datasheet curve.",
                     mag_db_min_tight=[round(float(x), 3) for x in lot], mag_db_max_tight=[round(float(x), 3) for x in hit],
                     tight_note="same bands with +-0.075 mm geometry tolerance (drilled bore / NPTH practice, ASSUMED) instead of +-0.2 mm",
                     valid_from_hz=(15000 if oo.gap == "open" else 1000),
                     validity=("open gap: mag_db = infinite-plate (absorbing walls) limit; mag_db_channel = rigid empty channel limit; truth in between "
                               "(parts cover ~44 % of the gap area, lip under-slot, edge leaks): bands cover both + 1.5 dB; < 15 kHz indicative only"
                               if oo.gap == "open" else "sealed duct: plane-wave sections, lumped end corrections; FEM-checked <= 1 dB below 60 kHz, <= 3.2 dB at 60-100 kHz"),
                     level_offset_db=dict(nominal=0.0, range=[0.0, 6.0], note="baffle pressure doubling at the plate (flat, not in the shape)"),
                     bands="mag_db_min/max = Monte Carlo envelope (geometry +-0.2 mm, offset, mesh r_s x0.2..x5, reference-fixture assumption x3"
                           + (", channel size +-10 % / bore position +-0.5 mm, matched AND channel limits" if oo.gap == "open" else "")
                           + f") widened by model-form error {MODEL_FORM_DB} dB" + (f" and +-{PARTS_RESIDUAL_DB} dB parts/leaks" if oo.gap == "open" else ""),
                     **extra_cols)
        write_if_port(OUT / fname, f, scen[name]["H"], lo, hi, p05, p95, cond, extra)
    for stale in ("port_response_chimney_id2.1.json", "port_response_chimney_aligned_id1.0.json"):
        (OUT / stale).unlink(missing_ok=True)
    res["files"] = [str((OUT / v).relative_to(REPO)) for v in IF_FILES.values()]

    # ---- spec s8 / R14 checks
    res["spec_checks"] = {}
    for name in ("as_built", "as_built_channel", "chimney_d1.0", "chimney_d1.0_hole1.0", "gasket_id2.1", "size_s1", "size_s2", "chimney_d1.0+mesh_mouth"):
        gg, oo = sc[name]
        res["spec_checks"][name] = spec_checks(name, gg, oo, scen[name]["H"], f, g.info, res["mc_summary"].get(name))

    res["scenarios"] = {k: {kk: vv for kk, vv in v.items() if kk != "H"} for k, v in scen.items()}
    res["sweeps"] = sweeps
    res["model_form_db"] = MODEL_FORM_DB
    res["wall_s"] = round(time.time() - t0, 2)
    (OUT / "port_results.json").write_text(json.dumps(res, indent=1, default=float))
    if plot:
        plots(g, f, sc, scen, mc, sweeps)
    a = scen["as_built"]
    b = scen["chimney_d1.0"]
    print(json.dumps(dict(wall_s=res["wall_s"], board=g.info.get("board_file"), offset_mm=round(g.offset / MM, 3), warnings=list(g.warnings),
                          as_built=a["feat"], as_built_channel_notch=scen["as_built_channel"]["feat"]["min_20_96_db"], chimney_d1_peaks=b["peaks"],
                          mc_as_built=res["mc_summary"]["as_built"]["mean_20_96_db"], mc_chimney=res["mc_summary"]["chimney_d1.0"]["mean_20_96_db"]), default=float))
    return res


# ------------------------------------------------------------------------------------------------ figures
def plots(g, f, sc, scen, mc, sweeps):
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    import plotstyle
    plotstyle.apply()
    S, T2 = plotstyle.SERIES, plotstyle.TEXT_2
    # 1) response: today vs the two sealed options
    fig, ax = plt.subplots(2, 1, figsize=(9.5, 8.2), sharex=True)
    for name, col, lab in (("as_built", S[1], "today: open gap between lid and board"), ("gasket_id2.1", S[3], "sealed gasket ring ID 2.1 mm"),
                           ("chimney_d1.0", S[2], "sealed straight duct D1.0 mm (recommended)")):
        A = mc[name]["A"]
        lo, hi = A.min(axis=0), A.max(axis=0)
        if name == "as_built":
            Ac = mc["as_built_channel"]["A"]
            lo, hi = np.minimum(lo, Ac.min(axis=0)), np.maximum(hi, Ac.max(axis=0))
        lo, hi = widen(f, lo, hi, name == "as_built")
        ax[0].fill_between(f / 1e3, lo, hi, color=col, alpha=0.13, lw=0)
        ax[0].plot(f / 1e3, db(scen[name]["H"]), color=col, label=f"{lab}  (average {scen[name]['feat']['mean_20_96_db']:+.0f} dB)")
    ax[0].axvspan(20, 96, color=T2, alpha=0.08)
    ax[0].axhline(0, color=T2, lw=0.8, ls=":")
    ax[0].set_xscale("log")
    ax[0].set_ylim(-50, 35)
    ax[0].set_ylabel("loudness at the mic vs a bare mic  [dB]")
    ax[0].set_title("How much the pod's sound path helps or hurts the mic\n(0 dB = mic in the open; shaded = what we can't pin down yet; grey = bat band 20-96 kHz)")
    ax[0].legend(fontsize=8, loc="upper left", frameon=True, facecolor=plotstyle.SURFACE, edgecolor=plotstyle.GRID, framealpha=0.9)
    ax[0].set_xlim(5, 100)
    for name, col, lab in (("as_built_channel", S[0], "today, if the gap's walls reflect fully (resonant limit)"), ("size_s1", S[4], "size-study S1 duct (3.45 mm)"),
                           ("size_s2", S[5], "size-study S2 duct (2.95 mm)"), ("chimney_d1.0_hole1.0", S[6], "sealed D1.0 duct, board hole 1.0")):
        ax[1].plot(f / 1e3, db(scen[name]["H"]), color=col, label=lab)
    ax[1].plot(f / 1e3, db(scen["as_built"]["H"]), color=S[1], lw=1, alpha=0.6, label="today (absorbing-wall limit)")
    ax[1].axvspan(20, 96, color=T2, alpha=0.08)
    ax[1].set_ylim(-50, 35)
    ax[1].set_xlabel("frequency [kHz]")
    ax[1].set_ylabel("dB vs a bare mic")
    ax[1].legend(fontsize=8, loc="upper left", frameon=True, facecolor=plotstyle.SURFACE, edgecolor=plotstyle.GRID, framealpha=0.9)
    fig.tight_layout()
    fig.savefig(OUT / "port_response.png", dpi=110)
    plt.close(fig)
    # 2) sweeps
    fig, ax = plt.subplots(1, 2, figsize=(10.5, 3.9))
    so = sweeps["offset_open_gap"]
    ax[0].plot([r["offset_mm"] for r in so], [r["mean_20_96_db"] for r in so], color=S[1], label="average 20-96 kHz")
    ax[0].plot([r["offset_mm"] for r in so], [r["min_20_96_db"] for r in so], color=S[0], label="deepest dip")
    ax[0].axvline(g.offset / MM, color=T2, ls=":")
    ax[0].set_xlabel("board hole off the lid hole [mm] (dotted = board today)")
    ax[0].set_ylabel("dB vs bare mic (open gap)")
    ax[0].legend(fontsize=8)
    tr = sweeps["tornado_chimney_d1.0"]["rows"]
    y = np.arange(len(tr))
    ax[1].barh(y - 0.18, [r["d_mean_lo"] for r in tr], 0.36, color=S[0], label="low value")
    ax[1].barh(y + 0.18, [r["d_mean_hi"] for r in tr], 0.36, color=S[3], label="high value")
    ax[1].set_yticks(y)
    ax[1].set_yticklabels([r["param"] for r in tr], fontsize=6.5)
    ax[1].invert_yaxis()
    ax[1].set_xlabel("change of the average [dB], sealed D1.0 duct")
    ax[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "port_sweeps.png", dpi=110)
    plt.close(fig)
    # 3) cross-section, to scale (mm), today vs the recommended sealed duct
    fig, axs = plt.subplots(1, 2, figsize=(11, 5.2))
    for ax, name, title in ((axs[0], "as_built", "TODAY: open gap"), (axs[1], "chimney_d1.0", "RECOMMENDED: sealed straight duct")):
        gg, oo = sc[name]
        yb0, yb1 = 0.0, gg.t_board / MM
        yl0 = yb1 + gg.h_gap / MM
        yw = yl0 + gg.l_bore / MM
        yt = yw + (gg.d_recess / MM if oo.recess else 0)
        rb, rh, rw = gg.a_bore / MM, gg.a_hole / MM, gg.a_recess / MM
        xh = gg.offset / MM * math.cos(gg.off_ang)
        wall = plotstyle.GRID
        ax.add_patch(Rectangle((-6, yb0), 12, yb1 - yb0, color="#2f6f4f", alpha=0.9))                 # board (green FR4)
        ax.add_patch(Rectangle((xh - rh, yb0 - 0.01), 2 * rh, yb1 - yb0 + 0.02, color=plotstyle.SURFACE))  # board hole
        ax.add_patch(Rectangle((-1.75, yb0 - 0.98), 3.5, 0.98, color="#6b6f78"))                          # mic body under the board
        ax.add_patch(Rectangle((xh - 0.1625, yb0 - 0.25), 0.325, 0.25, color=plotstyle.SURFACE))          # mic port
        for x0, x1 in ((-6, -rw if oo.recess else -rb), (rw if oo.recess else rb, 6)):
            ax.add_patch(Rectangle((x0, yw), x1 - x0, yt - yw, color=wall))                               # plate / window level
        if oo.recess:
            pass
        for x0, x1 in ((-6, -rb), (rb, 6)):
            ax.add_patch(Rectangle((x0, yl0), x1 - x0, yw - yl0, color=wall))                             # lid wall with the bore
        if oo.gap == "chimney":
            a = oo.a_chim / MM
            for x0, x1 in ((-a - 0.75, -a), (a, a + 0.75)):
                ax.add_patch(Rectangle((x0, yb1), x1 - x0, yl0 - yb1, color=S[3], alpha=0.75))           # gasket / boss ring, 0.75 wall
        lab = dict(color=T2, fontsize=7)
        ax.text(rw + 0.15 if oo.recess else rb + 0.15, yt - 0.15, ("hex window" if oo.recess else ""), va="top", **lab)
        ax.text(rb + 0.15, (yl0 + yw) / 2, f"lid hole D{2 * rb:.1f}", va="center", **lab)
        ax.text(xh + rh + 0.15 + (0.75 if oo.gap == "chimney" else 0), yb1 - 0.12, f"board hole D{2 * rh:.1f}", va="top", **lab)
        ax.text(-1.7, yb0 - 0.75, "mic port D0.325", **lab)
        ax.annotate("", xy=(0, yb0 - 0.6), xytext=(0, yt + 1.0), arrowprops=dict(arrowstyle="->", color=S[0], lw=1.6))
        ax.text(0.15, yt + 0.75, "sound in", color=S[0], fontsize=8)
        ax.text(-5.8, yt - 0.25, "lid + armour plate", color=plotstyle.TEXT, fontsize=7.5, va="top")
        ax.text(-5.8, (yb1 + yl0) / 2, ("open gap: sound leaks sideways\ninto the whole lid space" if oo.gap == "open" else "sealed ring (gasket/boss,\norange): sound can only go down"),
                color=plotstyle.TEXT, fontsize=7.5, va="center")
        ax.text(-5.8, (yb0 + yb1) / 2, "circuit board", color="white", fontsize=7.5, va="center")
        ax.text(1.9, yb0 - 0.5, "microphone", color=plotstyle.TEXT, fontsize=7.5, va="center")
        fe = scen[name]["feat"]
        ax.set_title(f"{title}\naverage {fe['mean_20_96_db']:+.0f} dB vs a bare mic, 20-96 kHz", fontsize=9)
        ax.set_xlim(-6, 6)
        ax.set_ylim(-1.3, yt + 1.3)
        ax.set_aspect("equal")
        ax.set_xlabel("mm")
        ax.grid(False)
    fig.tight_layout()
    fig.savefig(OUT / "port_path.png", dpi=110)
    plt.close(fig)


if __name__ == "__main__":
    main(sys.argv[1:])
