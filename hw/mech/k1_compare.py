#!/usr/bin/env python3
"""Phase-2 vs K1 (no plate) vs K1p (plate kept), to scale, dark: end section (y-z, T x H) and plan (x-z, L x H).

    python3 hw/mech/k1_compare.py      # -> docs/diagrams/k1-vs-phase2.png (+ .svg) and sim/out/mech/k1_compare.json

Every number is read from the dims modules (dims_r2.py; dims_k1.py per variant) and the shell/heel/mass/acoustic
outputs written by the K1 runs (hw/mech/out/{r2,k1,k1p}/checks.json, out/parts/heel*/checks.json,
sim/out/mech/pod_mass*.json, sim/out/aco_*/port_results.json); nothing is re-derived here. Packet Q1 (owner decision).
"""
import importlib.util
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "sim" / "checks"))
import plotstyle  # noqa: E402

plotstyle.apply()
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, Rectangle  # noqa: E402

# (design, dims file, out folder, title, K1_DUCT, duct_options row (lid, option))
DESIGNS = [("phase2", "dims_r2.py", "r2", "Phase 2 (today): 175 mAh, lid 0.8 + plate 0.7", "", ("ref_phase2_lid1.5", "as_k1")),
           ("k1", "dims_k1.py", "k1_rec", "K1 'rec': 130 mAh, plate OFF, lid 1.0, seat 0.3", "rec", ("lid1.0", "seat0.3")),
           ("k1p", "dims_k1.py", "k1p", "K1p: 130 mAh, plate kept (lid 0.8 + 0.7)", "", ("ref_phase2_lid1.5", "as_k1")),
           ("k1t", "dims_k1.py", "k1t", "K1t: walls 0.6 + lid 0.6 (T 8.5 study)", "", ("lid0.6", "flush0.1"))]
DUCT_ROWS = {(r["lid"], r["option"]): r for r in json.loads((ROOT / "sim/out/mech/duct_options.json").read_text())["rows"] if r.get("feasible")}


def load(design, fname, duct=""):
    os.environ["ULTRASONIC_DESIGN"] = design
    os.environ["K1_DUCT"] = duct
    spec = importlib.util.spec_from_file_location(f"cmp_{design}{duct}", HERE / fname)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def jload(p):
    p = ROOT / p
    return json.loads(p.read_text()) if p.exists() else None


def facts(d, D, out, duct_row):
    c = jload(f"hw/mech/out/{out}/checks.json")
    heel = jload(f"hw/mech/out/parts/{'heel' if d == 'phase2' else 'heel_' + d}/checks.json")
    mass = jload(f"sim/out/mech/{'pod_mass.json' if d == 'phase2' else 'pod_mass_' + d + '.json'}")
    ar = DUCT_ROWS[duct_row]["nomesh"]          # sim/acoustics/duct_options.py (same model + MC as run_port.py)
    env = c["envelope"]
    clashes = sum(1 for k, v in c.items() if k.startswith(("clash", "corridor")) and v > 1e-3)
    w = heel["wire_route"]["bundle"] if heel else {}
    return dict(design=d, T=env["T"], H=env["H"], L=env["L"], volume_mm3=env["total_mm3"], size_model_mm3=env["size_model_live"],
                vs_phase2_pct=None, mass_worn_g=mass["total_worn_g"] if mass else None,
                cell=getattr(D, "CELL_SPEC", dict(part="Renata ICP501233PA-02", mAh=175)),
                clashes=clashes, printable=all(v["solids"] == 1 and v["valid"] for v in c["printable"].values()),
                stowage_mm3=c["stowage"]["total_mm3"], stowage_need=c["stowage"]["need_mm3"],
                duct_worst=c["duct"]["worst_with_gauge_pin"], duct_limit=c["duct"]["limit_R_ACO_P5"],
                puck_L=c["SW1_pocket"]["puck_L"], puck_bore_len=round(D.SKIN_FLOOR - D.POCKET["top"], 2),
                mic_bore_len=round(D.Y_TOP - D.Y_LID_IN - D.HEX_DEPTH, 2),
                wire_pass=heel["wire_route"]["pass_0.3"] and heel["wire_route_left_pod"]["pass_0.3"] if heel else None,
                wire_bend_R=w.get("bend_radii"), strand_strain_pct=w.get("strand_bend_strain_pct"), fan_room=w.get("fan_room_behind_board"),
                duct_peak=dict(f_khz=ar["f_peak_khz"], db=ar["peak_db"], mean_20_96=ar["mean_20_96_db"], r14=ar["R14_peak"],
                               mc_r14_all_pass=ar["mc_r14_all_pass"], mc_peak_p95=ar["mc_in_pod_peak_p95"],
                               mesh_mc_r14_all_pass=DUCT_ROWS[duct_row]["mesh_floor"]["mc_r14_all_pass"]),
                puck_feasible=c["SW1_pocket"].get("puck_feasible", True), pocket_breaks_outer_face=c["SW1_pocket"].get("pocket_breaks_outer_face", False),
                off_temple=round(1.8 + env["T"], 2))


def end_section(ax, D, title):
    """y-z end view at the board centre (x through the cell): wall | tape | cell | B gap | board | F gap | lid | plate."""
    yi, yo, yt = D.Y_IN, D.Y_OUT, D.Y_TOP
    ax.add_patch(Rectangle((yi, D.Z0), yo - yi, D.Z1 - D.Z0, fc="#2a2c31", ec="#a4a9b0", lw=1.0))
    ax.add_patch(Rectangle((D.CAV["y0"], D.CAV["z0"]), D.CAV["y1"] - D.CAV["y0"], D.CAV["z1"] - D.CAV["z0"], fc="#141518", ec="none"))
    if D.PLATE_T > 0:
        ax.add_patch(Rectangle((yo, D.Z0 + 0.5), D.PLATE_T, D.Z1 - D.Z0 - 1.0, fc="#4a3aa7", ec="#8d7ff0", lw=0.8, label="armour plate"))
    ax.add_patch(Rectangle((D.Y_IN, D.Z_BELLY), yo - yi, D.Z0 - D.Z_BELLY + 0.8, fc="#2a2c31", ec="#a4a9b0", lw=0.6))
    ax.add_patch(Rectangle((D.CELL["y0"], D.CELL["z0"]), D.CELL["y1"] - D.CELL["y0"], D.CELL["z1"] - D.CELL["z0"], fc="#f28c3f", alpha=0.55, ec="#f28c3f", label="cell"))
    ax.add_patch(Rectangle((D.PCB["y0"], D.PCB["z0"]), D.PCB_T, D.PCB_H, fc="#2fc98f", ec="#52d39e", label="board 30x12 (unchanged)"))
    ax.add_patch(Rectangle((D.Y_B - D.B_MAX, D.PCB["z0"] + 0.3), D.B_MAX, D.PCB_H - 0.6, fc="#5b9ff2", alpha=0.35, ec="none", label="B parts (1.08 max)"))
    ax.add_patch(Rectangle((D.Y_LID_IN - D.VHB_T, D.PCB["z0"] + 0.2), D.VHB_T, D.PCB_H - 0.4, fc="#ff6d6c", alpha=0.6, ec="none", label="VHB"))
    ax.annotate("", xy=(yi, D.Z1 + 0.9), xytext=(yt, D.Z1 + 0.9), arrowprops=dict(arrowstyle="<->", color="#e8e8e5", lw=0.9))
    ax.text((yi + yt) / 2, D.Z1 + 1.2, f"T {yt - yi:.1f}", ha="center", color="#e8e8e5", fontsize=10, weight="bold")
    ax.annotate("", xy=(yt + 0.7, D.Z0), xytext=(yt + 0.7, D.Z1), arrowprops=dict(arrowstyle="<->", color="#e8e8e5", lw=0.9))
    ax.text(yt + 0.9, (D.Z0 + D.Z1) / 2, f"H {D.H:.1f}", rotation=90, va="center", color="#e8e8e5", fontsize=10, weight="bold")
    ax.axvline(D.Y_IN, color="#a4a9b0", lw=0.5, ls=":")
    ax.text(D.Y_IN - 0.15, D.Z_BELLY + 0.2, "temple side", rotation=90, color="#a4a9b0", fontsize=7, ha="right")
    ax.set_xlim(2.5, 17.0)
    ax.set_ylim(-12.5, 7.5)
    ax.set_aspect("equal")
    ax.set_title(title, fontsize=10)
    ax.set_xlabel("y (mm, out from the temple)")


def plan(ax, D, f):
    """x-z plan (seen through the lid): body + belly, cell, board, dock, mic duct, SW1, heel anchor."""
    ax.add_patch(Rectangle((D.X0, D.Z0), D.X1 - D.X0, D.Z1 - D.Z0, fc="#2a2c31", ec="#a4a9b0", lw=1.0))
    ax.add_patch(Rectangle((D.X0, D.Z_BELLY), D.X_BELLY - D.X0, D.Z0 - D.Z_BELLY + 0.5, fc="#2a2c31", ec="#a4a9b0", lw=0.8))
    ax.add_patch(Rectangle((D.CELL["x0"], D.CELL["z0"]), D.CELL["x1"] - D.CELL["x0"], D.CELL["z1"] - D.CELL["z0"], fc="#f28c3f", alpha=0.3, ec="#f28c3f"))
    ax.add_patch(Rectangle((D.PCB["x0"], D.PCB["z0"]), D.PCB_L, D.PCB_H, fc="none", ec="#52d39e", lw=1.2))
    ax.add_patch(Rectangle((D.DOCK["x0"], D.DOCK["z0"]), D.DOCK["x1"] - D.DOCK["x0"], 1.2, fc="#a19d8d", alpha=0.6, ec="none"))
    ax.add_patch(Circle(D.MIC, 0.5, fc="#5b9ff2", ec="none"))
    ax.add_patch(Circle(D.SW, 1.3, fc="none", ec="#8d7ff0", lw=1.0))
    ax.add_patch(Rectangle((D.PCB["x1"], D.CAV["z0"]), D.CAV["x1"] - D.PCB["x1"], D.CAV["z1"] - D.CAV["z0"], fc="#ff6d6c", alpha=0.15, ec="none"))
    ax.text(D.PCB["x1"] + 0.1, D.CAV["z1"] - 1.2, f"stowage\n{f['stowage_mm3']:.0f} mm3", color="#ff6d6c", fontsize=7)
    ax.axvline(29.5, color="#e34948", lw=0.7, ls="--")
    ax.text(29.6, 6.6, "vision limit x 29.5", color="#ff6d6c", fontsize=7)
    ax.axvline(67.5, color="#a4a9b0", lw=0.5, ls=":")
    ax.annotate("", xy=(D.X0, D.Z_BELLY - 0.9), xytext=(D.X1, D.Z_BELLY - 0.9), arrowprops=dict(arrowstyle="<->", color="#e8e8e5", lw=0.9))
    ax.text((D.X0 + D.X1) / 2, D.Z_BELLY - 2.2, f"L {D.X1 - D.X0:.1f} (rear fixed: heel + rail)", ha="center", color="#e8e8e5", fontsize=9)
    ax.set_xlim(27.5, 69.5)
    ax.set_ylim(-15.0, 7.5)
    ax.set_aspect("equal")
    ax.set_xlabel("x (mm, front -> rear)")


def main():
    mods, F = {}, {}
    for d, fname, out, _, duct, row in DESIGNS:
        mods[d] = load(d, fname, duct)
        F[d] = facts(d, mods[d], out, row)
    os.environ.pop("ULTRASONIC_DESIGN", None)
    os.environ.pop("K1_DUCT", None)
    for d in F:
        F[d]["vs_phase2_pct"] = round(100 * (F[d]["volume_mm3"] / F["phase2"]["volume_mm3"] - 1), 1)
    from size_budget import scenario
    thin = scenario("K1-thin (walls + lid 0.6, no plate; synthesis K1)", cell_L=31.0, cell_T=4.5, cell_H=12.7, cell_g=3.5, board_H=12.0,
                    board_L=30.0, y_bgap=1.4, y_fgap=0.30, lid_wall=0.6, wall=0.6, plate=0.0, s_fixed=0.8, dock="flat_tails")
    fig = plt.figure(figsize=(21, 10.5))
    gs = fig.add_gridspec(2, 4, height_ratios=[1.15, 1.0])
    for i, (d, _, _, title, _, _) in enumerate(DESIGNS):
        f, D = F[d], mods[d]
        ax = fig.add_subplot(gs[0, i])
        end_section(ax, D, title)
        if i == 0:
            ax.set_ylabel("z (mm, up)")
            ax.legend(loc="lower right", fontsize=7, frameon=False)
        ax2 = fig.add_subplot(gs[1, i])
        plan(ax2, D, f)
        ok = lambda b: "PASS" if b else "FAIL"    # noqa: E731
        txt = (f"{f['volume_mm3']:.0f} mm3 ({f['vs_phase2_pct']:+.0f} %) | {f['mass_worn_g'][0]:.1f}-{f['mass_worn_g'][1]:.1f} g worn | "
               f"{f['off_temple']} mm off temple\nclash {f['clashes']} | print {ok(f['printable'])} | wires {ok(f['wire_pass'])} "
               f"(R {min(f['wire_bend_R'])}, strain {f['strand_strain_pct']} %) | duct pin {f['duct_worst']}/{f['duct_limit']}\n"
               f"duct peak {f['duct_peak']['f_khz']} kHz {f['duct_peak']['db']:+.1f} dB, R14 {f['duct_peak']['r14']}, MC pass {f['duct_peak']['mc_r14_all_pass']} | "
               f"mic bore {f['mic_bore_len']} | puck guide {f['puck_bore_len']}" + ("" if f["puck_feasible"] else " -> NO PUCK, pocket breaks the lid"))
        ax2.set_title(txt, fontsize=7.5, loc="left")
        if i == 0:
            ax2.set_ylabel("z (mm, up)")
    fig.suptitle("Packet Q1/Q2: Phase 2 vs K1 variants, same board, to scale (end section through the cell; plan through the lid). "
                 f"T 8.5 = K1t: 0.6 walls + 0.6 lid (needs the coupon, and the SW1 button does not fit a 0.6 lid)", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    od = ROOT / "docs/diagrams"
    fig.savefig(od / "k1-vs-phase2.png", dpi=130)
    fig.savefig(od / "k1-vs-phase2.svg")
    res = dict(date="2026-10-07", src="hw/mech/k1_compare.py", designs=F, k1_thin_size_model=thin)
    (ROOT / "sim/out/mech").mkdir(parents=True, exist_ok=True)
    (ROOT / "sim/out/mech/k1_compare.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
