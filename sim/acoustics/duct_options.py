#!/usr/bin/env python3
"""Mic-duct options for a THIN lid (plate off): which stack passes R14 again? (round 11, packet Q1/Q2, 2026-10-07)

    ULTRASONIC_DESIGN=k1 python3 sim/acoustics/duct_options.py     # -> sim/out/mech/duct_options.json (+ .png, dark)

Base = the K1 geometry as read by geometry.load (lid 1.0, no plate; Phase 2 with the plate off has the same duct stack:
lid inner face -> window floor -> bore -> sealed D1.0 VHB hole (0.30) -> board hole D0.65). Each option changes only the lid
part of the duct (seat depth d_recess, seat size hex R, bore ID incl. the VHB hole, an OUTER boss that lengthens the bore
locally; an INNER boss is impossible: the board is VHB-bonded flat to the lid inner face). Scored exactly like run_port.py:
spec_checks() on the nominal stack (R14-peak / -notch / -level, in-pod = datasheet x path, 20-85 kHz) and the Monte Carlo
(n 60, seed 7, tol 0.2 mm, offset 0-0.2 mm) in-pod peak p95 and R14 all-pass fraction; also with the floor mesh (mesh_pick:
Acoustex 042 on the seat floor) because the real build has one. Lid 0.6 rows: the 0.6-wall / 0.6-lid study (K1-thin).
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import run_port as R  # noqa: E402
from port import Opt, calibrate_mic, monte_carlo, ratio  # noqa: E402

MM = 1e-3
LIDS = {"ref_phase2_lid1.5": 1.5, "lid1.0": 1.0, "lid0.6": 0.6}   # 1.5 = Phase 2 lid 0.8 + plate 0.7 (reference row only)
# name: (seat depth, hex circum R, bore ID, outer boss height, note)
OPTIONS = {
    "as_k1": (0.8, 1.9, 1.0, 0.0, "today's K1: r1 hex seat 0.8 deep, bore 0.2"),
    "seat0.5": (0.5, 1.9, 1.0, 0.0, "shallower seat 0.5"),
    "seat0.3": (0.3, 1.9, 1.0, 0.0, "shallow seat 0.3 (mesh + adhesive + 0.2 guard)"),
    "flush0.1": (0.1, 1.9, 1.0, 0.0, "mesh ~flush with the outer face: 0.1 counterbore for mesh + PSA"),
    "seatR1.2": (0.8, 1.2, 1.0, 0.0, "smaller seat R1.2, 0.8 deep"),
    "seatR1.2_0.3": (0.3, 1.2, 1.0, 0.0, "smaller seat R1.2, 0.3 deep"),
    "bore0.8": (0.8, 1.9, 0.8, 0.0, "bore ID 0.8 (and VHB hole 0.8)"),
    "bore0.8_seat0.3": (0.3, 1.9, 0.8, 0.0, "bore ID 0.8, seat 0.3"),
    "boss0.5": (0.8, 1.9, 1.0, 0.5, "outer boss +0.5 round the seat (local bump; bore 0.7 = phase2 duct)"),
}


def stack(g0, lid, seat, hex_r, bore_d, boss):
    if seat >= lid + boss - 0.05:
        return None
    area = 6 / 2 * hex_r ** 2 * math.sin(2 * math.pi / 6)
    g = g0.with_(a_recess=math.sqrt(area / math.pi) * MM, hex_circum_r=hex_r * MM, d_recess=seat * MM,
                 l_bore=(lid + boss - seat) * MM, a_bore=bore_d / 2 * MM)
    return g


def score(g, oo, mic, f, info, n_mc):
    H = ratio(f, g, oo, mic, "ideal")
    chk = {c["id"]: c for c in R.spec_checks("x", g, oo, H, f, info)}
    _, A, _ = monte_carlo(g, oo, n=n_mc, seed=7, tol=0.2e-3, offset_range=(0.0, 0.2e-3))
    cap = (f >= 20e3) & (f <= 96e3)
    mb = A[:, cap].mean(axis=1)
    ip = np.interp(f / 1e3, R.DS["f_khz"], R.DS["db_re_1k"])[None, :] + A
    m8 = (f >= 20e3) & (f <= R.R14_BAND_HZ[1])
    ipm = np.median(ip[:, m8], axis=1)
    notch8, peak8 = ip[:, m8].min(axis=1) - ipm, ip[:, m8].max(axis=1) - ipm
    ok = (mb >= -6) & (notch8 >= -10) & (peak8 <= 15)
    feat = R.features(f, H)
    return dict(R14_peak=chk["R14-peak"]["status"], R14_peak_val=chk["R14-peak"]["value"][:60],
                R14_notch=chk["R14-notch"]["status"], R14_level=chk["R14-level"]["status"],
                f_peak_khz=round(feat["f_max_hz"] / 1e3, 1), peak_db=round(feat["max_20_96_db"], 2), mean_20_96_db=round(feat["mean_20_96_db"], 2),
                mc_in_pod_peak_p95=round(float(np.percentile(peak8, 95)), 2), mc_notch_p05=round(float(np.percentile(notch8, 5)), 2),
                mc_mean_p05=round(float(np.percentile(mb, 5)), 2), mc_r14_all_pass=round(float(ok.mean()), 2))


def main():
    n_mc = int(sys.argv[sys.argv.index("--mc") + 1]) if "--mc" in sys.argv else 60
    g0 = R.load_geom(None)
    f = R.F_GRID
    mic = calibrate_mic(g0, "ideal")
    rows = []
    for lname, lid in LIDS.items():
        for name, (seat, hr, bd, boss, note) in OPTIONS.items():
            if lname.startswith("ref") and name != "as_k1":
                continue
            g = stack(g0, lid, seat, hr, bd, boss)
            if g is None:
                rows.append(dict(lid=lname, option=name, note=note, feasible=False, why=f"seat {seat} >= lid {lid} + boss {boss}"))
                continue
            row = dict(lid=lname, option=name, note=note, feasible=True, seat=seat, hex_R=hr, bore_d=bd, boss=boss,
                       bore_len=round(lid + boss - seat, 2), gauge_pin_limit=round(bd / 2 - 0.65 / 2, 3))
            for tag, oo in (("nomesh", Opt(gap="chimney", a_chim=bd / 2 * MM)), ("mesh_floor", Opt(gap="chimney", a_chim=bd / 2 * MM, mesh="floor"))):
                row[tag] = score(g, oo, mic, f, g0.info, n_mc)
            rows.append(row)
            print(lname, name, row["nomesh"]["R14_peak"], row["nomesh"]["f_peak_khz"], row["nomesh"]["mc_in_pod_peak_p95"],
                  row["nomesh"]["mc_r14_all_pass"], "| mesh", row["mesh_floor"]["R14_peak"], row["mesh_floor"]["mc_r14_all_pass"], flush=True)
    od = REPO / "sim/out/mech"
    od.mkdir(parents=True, exist_ok=True)
    out = dict(date="2026-10-07", src="sim/acoustics/duct_options.py", design=g0.info.get("design"), n_mc=n_mc, rows=rows,
               rule="R14-peak: in-pod 20-85 kHz no peak > +15 dB re median (run_port.spec_checks); gauge pin needs worst 0.14 <= bore/2 - 0.325")
    (od / "duct_options.json").write_text(json.dumps(out, indent=1))
    plot(rows)


def plot(rows):
    """docs/diagrams/duct-options.png/.svg (dark): MC R14 all-pass per option, nominal R14-peak and peak frequency."""
    sys.path.insert(0, str(REPO / "tools"))
    import plotstyle
    plotstyle.apply()
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    ref = next(r for r in rows if r["lid"].startswith("ref"))
    fig, axes = plt.subplots(1, 2, figsize=(15, 5.6), sharey=True)
    for ax, lid in zip(axes, ("lid1.0", "lid0.6")):
        rr = [r for r in rows if r["lid"] == lid and r.get("feasible")]
        x = np.arange(len(rr))
        ax.bar(x - 0.2, [r["nomesh"]["mc_r14_all_pass"] for r in rr], 0.4, color="#5b9ff2", label="MC R14 all-pass, no mesh")
        ax.bar(x + 0.2, [r["mesh_floor"]["mc_r14_all_pass"] for r in rr], 0.4, color="#52d39e", label="with floor mesh (Acoustex 042)")
        ax.axhline(ref["nomesh"]["mc_r14_all_pass"], color="#f28c3f", ls="--", lw=1.2, label=f"Phase 2 today ({ref['nomesh']['mc_r14_all_pass']})")
        for i, r in enumerate(rr):
            n = r["nomesh"]
            ax.text(i, 0.02, f"{n['R14_peak']}\n{n['f_peak_khz']:.0f} kHz\nbore {r['bore_len']}", ha="center", fontsize=7,
                    color="#ff6d6c" if n["R14_peak"] == "FAIL" else "#e8e8e5")
        ax.set_xticks(x, [r["option"] for r in rr], rotation=30, ha="right", fontsize=8)
        ax.set_title(f"{lid} (plate off): nominal R14-peak / duct peak / bore under the seat", fontsize=10)
        ax.set_ylim(0, 1.0)
    axes[0].set_ylabel("fraction of 60 tolerance draws passing all R14 rules")
    axes[0].legend(fontsize=8, loc="upper right")
    fig.suptitle("Mic duct with the plate off: a 0.3 seat (bore 0.7) restores R14 and beats today's Phase 2 under tolerances; "
                 "a 0.6 lid fails without the mesh", fontsize=11)
    fig.tight_layout()
    for ext in ("png", "svg"):
        fig.savefig(REPO / "docs/diagrams" / f"duct-options.{ext}", dpi=130)


if __name__ == "__main__":
    main()
