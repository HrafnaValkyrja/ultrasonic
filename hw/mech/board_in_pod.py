#!/usr/bin/env python3
"""The routed board (KiCad 3D models) placed in BOTH pods (reg-board issue 9, physical issue 5).

kicad-cli exports the routed board to STL (full, board-only, and fiducial parts SW1/Q1); the STL frame is
x = board x, y = -board y, z = 0 at the B face (KiCad builds the body as thickness minus outer copper: 0..0.71,
surfaces at -0.045 / 0.755+0.045). Placement (dims_r2.bpt): pod x = PCB x0 + bx, pod y = Y_B + z + 0.045,
pod z = PCB z0 + by (right pod) or PCB z0 + 12 - by (left pod: the same board flipped in the mirrored shell).
Checks per pod: SW1 under the puck axis, SW1 on F inside the pocket, Q1 (off-centre, board y 9.0) at the expected
height, every B-side model above the cell top (B gap), every F-side model (except SW1) below the lid inner face.
Writes hw/mech/out/board3d/board_in_pod.json and sim/out/mech/board_in_pod.png (dark).
Run (fenced): systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 python3 hw/mech/board_in_pod.py
"""
import json
import struct
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import dims as D  # noqa: E402  (selected design: dims_r2 | dims_k1)

OUT = HERE / "out" / ("board3d" if D.DESIGN.id in ("phase2", "revg") else f"board3d_{D.DESIGN.id}")   # K1 etc.: own folder
BOARD = ROOT / "hw/pod/draft_r2/out/routed.kicad_pcb"
CU = 0.045


# CHK-MODELS (2026-10-07): the board's embedded footprints still name the old models until the next library sync;
# export from a scratch copy with the datasheet placeholders (hw/lib/make_placeholder_models.py) substituted.
MODEL_SUBST = {"${KICAD10_3DMODEL_DIR}/Sensor_Audio.3dshapes/Knowles_LGA-5_3.5x2.65mm.step": "hw/lib/lcsc/lcsc.3dshapes/SPH0641LU4H-1_placeholder.step",
               "hw/lib/lcsc/lcsc.3dshapes/SW-SMD_4P-L3.0-W2.6-P1.85-LS3.4.wrl": "hw/lib/lcsc/lcsc.3dshapes/KMT022NGJLHS_placeholder.step"}


def export():
    OUT.mkdir(parents=True, exist_ok=True)
    txt = BOARD.read_text()
    for a_, b_ in MODEL_SUBST.items():
        txt = txt.replace(f'(model "{a_}"', f'(model "{ROOT / b_}"')
    src = OUT / "_board_models_substituted.kicad_pcb"
    src.write_text(txt)
    jobs = {"full": [], "board": ["--board-only"], "SW1": ["--no-board-body", "--component-filter", "SW1"],
            "Q1": ["--no-board-body", "--component-filter", "Q1"]}
    for n, a in jobs.items():
        f = OUT / f"{n}.stl"
        subprocess.run(["kicad-cli", "pcb", "export", "stl", *a, "-f", "-o", str(f), str(src)], check=True, capture_output=True)


def tris(p):
    b = p.read_bytes()
    if b[:5] == b"solid" and b"facet" in b[:400]:
        v = np.array([list(map(float, ln.split()[1:4])) for ln in b.decode().splitlines() if ln.strip().startswith("vertex")])
        return v.reshape(-1, 3, 3)
    n = struct.unpack("<I", b[80:84])[0]
    rec = np.frombuffer(b[84:84 + n * 50], dtype=np.dtype([("n", "<3f4"), ("v", "<9f4"), ("a", "<u2")]))
    return rec["v"].reshape(-1, 3, 3).astype(float)


def to_pod(t, pod):
    x = D.PCB["x0"] + t[..., 0]
    by = -t[..., 1]
    z = D.PCB["z0"] + (by if pod == "right" else 12.0 - by)
    y = D.Y_B + t[..., 2] + CU
    return np.stack([x, y, z], -1)


def main():
    export()
    T = {n: tris(OUT / f"{n}.stl") for n in ("full", "board", "SW1", "Q1")}
    res = {"date": "2026-10-07", "board": str(BOARD.relative_to(ROOT)), "mapping": "pod x = x0 + bx; y = Y_B + z + 0.045; z = z0 + by (right) / z0 + 12 - by (left)"}
    for pod in ("right", "left"):
        P = {n: to_pod(t, pod) for n, t in T.items()}
        sw = P["SW1"].reshape(-1, 3)
        q1 = P["Q1"].reshape(-1, 3)
        allv = P["full"].reshape(-1, 3)
        comp = allv[(allv[:, 1] < D.Y_B - 0.01) | (allv[:, 1] > D.Y_F + 0.01)]       # outside the board body = parts
        b_side = comp[comp[:, 1] < D.Y_B]
        f_side = comp[comp[:, 1] > D.Y_F]
        in_pocket = (np.abs(f_side[:, 0] - D.SW[0]) <= D.POCKET["dx"] / 2) & (np.abs(f_side[:, 2] - D.SW[1]) <= D.POCKET["dz"] / 2)
        swc = (sw.min(0) + sw.max(0)) / 2
        q1c = (q1.min(0) + q1.max(0)) / 2
        r = {"SW1_axis_offset_xz": round(float(np.hypot(swc[0] - D.SW[0], swc[2] - D.SW[1])), 3),
             "SW1_on_F": bool(sw[:, 1].min() >= D.Y_F - 0.05), "SW1_top_y": round(float(sw[:, 1].max()), 3),
             "SW1_below_pocket_ceiling": round(float(D.POCKET["top"] - sw[:, 1].max()), 3),
             "Q1_centre_z": round(float(q1c[2]), 3), "Q1_expected_z": round(D.PCB["z0"] + (9.0 if pod == "right" else 3.0), 3),
             "Q1_on_B": bool(q1[:, 1].max() <= D.Y_B + 0.01),
             "B_parts_min_y": round(float(b_side[:, 1].min()), 3), "B_clear_to_cell_top": round(float(b_side[:, 1].min() - D.CELL["y1"]), 3),
             "F_parts_outside_pocket_max_y": round(float(f_side[~in_pocket][:, 1].max()) if (~in_pocket).any() else D.Y_F, 3),
             "F_clear_to_lid_outside_pocket": round(float(D.Y_LID_IN - (f_side[~in_pocket][:, 1].max() if (~in_pocket).any() else D.Y_F)), 3)}
        r["pass"] = (r["SW1_axis_offset_xz"] <= 0.01 and r["SW1_on_F"] and r["SW1_below_pocket_ceiling"] >= 0 and r["Q1_on_B"]
                     and abs(r["Q1_centre_z"] - r["Q1_expected_z"]) <= 0.01 and r["B_clear_to_cell_top"] >= 0 and r["F_clear_to_lid_outside_pocket"] >= 0)
        res[pod] = r
        res.setdefault("_P", {})[pod] = P
    P_all = res.pop("_P")
    (OUT / "board_in_pod.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))
    try:
        sys.path.insert(0, str(ROOT / "tools"))
        import plotstyle
        plotstyle.apply()
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.collections import PolyCollection
        from matplotlib.patches import Circle, Rectangle
        fig, axs = plt.subplots(2, 1, figsize=(11, 9))
        for ax, pod in zip(axs, ("right", "left")):
            P = P_all[pod]
            full = P["full"]
            col = np.where(full[:, :, 1].mean(1) > D.Y_F, "#5b9ff2", np.where(full[:, :, 1].mean(1) < D.Y_B, "#f28c3f", "#35b535"))
            sel = np.arange(len(full))
            ax.add_collection(PolyCollection(full[sel][:, :, [0, 2]], facecolors=col[sel], edgecolors="none", alpha=0.35))
            c = D.CELL
            ax.add_patch(Rectangle((c["x0"], c["z0"]), c["x1"] - c["x0"], c["z1"] - c["z0"], fc="none", ec="#a4a9b0", lw=0.8, ls=":", label="cell (under the board)"))
            cv = D.CAV
            ax.add_patch(Rectangle((cv["x0"], cv["z0"]), cv["x1"] - cv["x0"], cv["z1"] - cv["z0"], fc="none", ec="#e8e8e5", lw=0.8, label="cavity"))
            ax.add_patch(Circle(D.MIC, D.DUCT_D / 2, fc="none", ec="#ff6d6c", lw=1.5, label="lid duct D1.0"))
            ax.add_patch(Circle(D.SW, D.PUCK_D / 2, fc="none", ec="#8d7ff0", lw=1.5, label="puck D2.3"))
            ax.plot([66.2], [-5.5], "x", color="#ff6d6c", ms=8, label="heel wire exit")
            ax.annotate("Q1", (P["Q1"][:, :, 0].mean(), P["Q1"][:, :, 2].mean()), color="#e8e8e5", fontsize=8)
            ax.set_xlim(29, 68)
            ax.set_ylim(-10.5, 5.5)
            ax.set_aspect("equal")
            ax.set_title(f"{pod} pod, seen through the lid (x-z): F parts blue, B parts orange; checks {'PASS' if res[pod]['pass'] else 'FAIL'}")
            ax.set_xlabel("pod x (mm, front -> rear)")
            ax.set_ylabel("pod z (mm, up)")
        axs[0].legend(fontsize=7, loc="lower left", ncol=3, labelcolor="#e8e8e5", facecolor="#1e2025")
        fig.tight_layout()
        od = ROOT / "sim/out/mech"
        od.mkdir(parents=True, exist_ok=True)
        fig.savefig(od / ("board_in_pod.png" if OUT.name == "board3d" else f"board_in_pod_{D.DESIGN.id}.png"), dpi=120)
    except Exception as e:  # noqa: BLE001
        print("plot skipped:", e)


if __name__ == "__main__":
    main()
