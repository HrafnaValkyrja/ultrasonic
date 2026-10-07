#!/usr/bin/env python3
"""SW1 press reaction through the board + VHB (sub-ui issue 2, reg-pod-body issue 17, 00-whole risk 12).

Phase 2: the 30 x 12 x 0.8 board hangs from the lid on a full-face 0.25 mm VHB 4914 layer (shell_r2.vhb()):
inset 0.2 from the board edge, cut out round SW1 (pocket 4.3 x 3.1), the mic duct (D1.0) and each bare F test
pad (TP1-TP6, square 2 x 0.9). A finger press goes puck -> SW1 -> board (pushed away from the lid, toward the cell)
-> VHB (tension/peel round the pocket) -> lid. Nothing rigid backs SW1 on B.

Model: Kirchhoff plate (scikit-fem Morley triangles) on a Winkler foundation k = E_vhb / t_vhb over the bonded area
only; lid rigid (it is 0.8 resin + 0.7 armour plate, ~5x the board's bending stiffness is NOT assumed: a lid that
gives only lowers the VHB stress); press as uniform pressure on SW1's 3.0 x 2.6 body at board (18.5, 6.0).
Outputs per (E_vhb, F): SW1 deflection toward the cell, max deflection anywhere, peak VHB tension and compression,
peak board surface strain (curvature x t/2). Compared with: B-part margin to the cell 0.32 mm (interfaces.py
[heights]: U2 1.08 in the 1.40 band), KMT022 travel 0.15 +- 0.1 mm, VHB stress vs the 3M figures below.

Material inputs (all [A] = assumed, sources named so a reader can check):
- FR4 4-layer 0.8 mm: E 20 GPa, nu 0.15 ([A] typical laminate flexural modulus 18-24 GPa; copper planes stiffen it).
- VHB 4914 effective normal modulus swept 0.15 / 0.5 / 2 / 10 MPa: 0.15 = quasi-static neo-Hookean fits of VHB
  4910 (dielectric-elastomer literature, mu ~ 45-50 kPa) [A]; 0.5-2 = press-rate (~0.1 s) viscoelastic stiffening [A];
  10 = thin confined layer (nu ~ 0.49, shape factor) [A]. The sweep brackets the answer instead of picking one.
- Press: KMT022 operating force 2.0 N (sub-ui); abuse 10 N (hard thumb jab) [A].
Run (fenced): systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 python3 sim/checks/sw1_press_fem.py
Writes sim/out/mech/sw1_press_fem.json (+ .png plot of the soft case).
"""
import json
import sys
from pathlib import Path

import numpy as np
from skfem import Basis, BilinearForm, ElementTriMorley, LinearForm, MeshTri, asm, solve
from skfem.helpers import dd, ddot, eye, trace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "hw/mech"))
import dims as D  # noqa: E402  (selected design: dims_r2 | dims_k1)
TAG = "" if D.DESIGN.id == "phase2" else f"_{D.OUT_DIR.name}"   # variants write their own outputs (e.g. _k1t_dome)

BW, BH, T = 30.0, 12.0, D.PCB_T if hasattr(D, "PCB_T") else 0.8
E_PCB, NU = 20e3, 0.15            # N/mm2
VHB_T = D.VHB_T                    # 0.25
INSET = 0.2
SW_XY = (18.5, 6.0)
POCKET = (D.POCKET["dx"], D.POCKET["dz"])
BODY = D.SW1["body"]              # 3.0 x 2.6
MIC_XY, DUCT_R = D.MIC_XY, D.DUCT_D / 2
TP_R = D.TP_PAD_D / 2 + D.TP_CUT_MARGIN
F_PADS = D.F_PADS
B_MARGIN = round(D.B_GAP - D.B_MAX, 3)        # 0.32: tallest B part to the cell plane
E_VHB = (0.15, 0.5, 2.0, 10.0)                # MPa
FORCES = (2.0, 10.0)                          # N


def bonded(x, y):
    """1 where the VHB is bonded (board coords, mm), else 0."""
    m = (x > INSET) & (x < BW - INSET) & (y > INSET) & (y < BH - INSET)
    m &= ~((np.abs(x - SW_XY[0]) < POCKET[0] / 2) & (np.abs(y - SW_XY[1]) < POCKET[1] / 2))
    m &= ~((x - MIC_XY[0]) ** 2 + (y - MIC_XY[1]) ** 2 < DUCT_R ** 2)
    for px, py in F_PADS.values():
        m &= ~((np.abs(x - px) < TP_R) & (np.abs(y - py) < TP_R))
    return m.astype(float)


def load_area(x, y):
    return ((np.abs(x - SW_XY[0]) < BODY[0] / 2) & (np.abs(y - SW_XY[1]) < BODY[1] / 2)).astype(float)


def main():
    nx, ny = 241, 97                          # h = 0.125 mm
    mesh = MeshTri.init_tensor(np.linspace(0, BW, nx), np.linspace(0, BH, ny))
    ib = Basis(mesh, ElementTriMorley(), intorder=4)

    @BilinearForm
    def plate(u, v, w):
        def C(Tn):
            return E_PCB / (1 + NU) * (Tn + NU / (1 - NU) * eye(trace(Tn), 2))
        return T ** 3 / 12.0 * ddot(C(dd(u)), dd(v))

    @BilinearForm
    def found(u, v, w):
        return bonded(w.x[0], w.x[1]) * u * v

    @LinearForm
    def press(v, w):
        return load_area(w.x[0], w.x[1]) * v

    K = asm(plate, ib)
    M = asm(found, ib)
    P = asm(press, ib)
    a_load = BODY[0] * BODY[1]

    # sample grid for stresses/deflection (point evaluation via interpolation at quadrature points)
    results = []
    plot_case = None
    for ev in E_VHB:
        k = ev / VHB_T                          # N/mm3
        A = K + k * M
        for F in FORCES:
            w = solve(A, (F / a_load) * P)
            wq = ib.interpolate(w)              # values at quadrature points
            xq = ib.global_coordinates().value
            wv = wq.value
            bq = bonded(xq[0], xq[1])
            # VHB normal stress: sigma = k * w (w > 0 = board away from lid = tape in tension)
            sig = k * wv * bq
            # board surface strain from the Hessian: eps = t/2 * max principal curvature
            H = wq.hess
            kxx, kyy, kxy = H[0, 0], H[1, 1], H[0, 1]
            kmax = np.abs(0.5 * (kxx + kyy)) + np.sqrt((0.5 * (kxx - kyy)) ** 2 + kxy ** 2)
            eps = T / 2 * kmax
            # deflection under SW1 (mean over the body area)
            la = load_area(xq[0], xq[1])
            w_sw = float((wv * la).sum() / max(la.sum(), 1))
            # reaction check: integral of k w over bonded area ~= F
            reac = float(k * (ib.dx * wv * bq).sum())
            # strain away from the SW1 body itself (where parts sit; SW1's own pads see the local peak)
            far = la == 0
            r = dict(E_vhb_MPa=ev, F_N=F, w_sw1_mm=round(w_sw, 4), w_max_mm=round(float(wv.max()), 4),
                     w_min_mm=round(float(wv.min()), 4), vhb_tension_peak_kPa=round(1e3 * float(sig.max()), 1),
                     vhb_compression_peak_kPa=round(-1e3 * float(sig.min()), 1),
                     board_strain_peak_ue=round(1e6 * float(eps.max()), 0),
                     board_strain_peak_off_sw1_ue=round(1e6 * float(eps[far].max()), 0),
                     reaction_N=round(reac, 3))
            results.append(r)
            if ev == E_VHB[0] and F == FORCES[0]:
                plot_case = (w, k)
    out = dict(src="sim/checks/sw1_press_fem.py", date="2026-10-07", model="Kirchhoff plate (Morley) on Winkler VHB over the bonded area; lid rigid",
               inputs=dict(board=[BW, BH, T], E_pcb_MPa=E_PCB, nu=NU, vhb_t=VHB_T, inset=INSET, pocket=list(POCKET), sw1_body=list(BODY),
                           sw_xy=list(SW_XY), mic=list(MIC_XY), tp_cut_half=TP_R, mesh=[nx, ny]),
               limits=dict(b_part_margin_to_cell_mm=B_MARGIN, kmt022_travel_mm=list(D.SW1["travel"])),
               results=results)
    od = ROOT / "sim/out/mech"
    od.mkdir(parents=True, exist_ok=True)
    (od / f"sw1_press_fem{TAG}.json").write_text(json.dumps(out, indent=1))
    for r in results:
        print(r)
    if plot_case is not None:
        try:
            sys.path.insert(0, str(ROOT / "tools"))
            import plotstyle
            plotstyle.apply()
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            w, k = plot_case
            xs, ys = np.meshgrid(np.linspace(0.05, BW - 0.05, 300), np.linspace(0.05, BH - 0.05, 120))
            from skfem import Mesh  # noqa: F401
            # nodal values: Morley vertex DOFs are point values
            wn = w[ib.nodal_dofs[0]]
            fig, ax = plt.subplots(figsize=(9, 4))
            tc = ax.tricontourf(mesh.p[0], mesh.p[1], mesh.t.T, 1e3 * wn, levels=30)
            fig.colorbar(tc, ax=ax, label="board deflection toward the cell (um)")
            bx = bonded(xs, ys)
            ax.contour(xs, ys, bx, levels=[0.5], colors="w", linewidths=0.6)
            ax.set_aspect("equal")
            ax.set_xlabel("board x (mm)")
            ax.set_ylabel("board y (mm)")
            ax.set_title(f"SW1 press 2.0 N, VHB E {E_VHB[0]} MPa (softest case); white = VHB cut-out edges")
            fig.tight_layout()
            fig.savefig(od / f"sw1_press_fem{TAG}.png", dpi=130)
        except Exception as e:  # plotting is a convenience
            print("plot skipped:", e)


if __name__ == "__main__":
    main()
