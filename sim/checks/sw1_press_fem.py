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

K4 (2026-10-08, K4-SW1-PRESS): SW1_BOARD=k4 python3 sim/checks/sw1_press_fem.py  -> M board 14.0 x 12.0 x 0.8 (6L; routed_M.kicad_pcb), SW1 at M (5.325, 6.025),
VHB bonded over the stack footprint (x 0.2..STACK_L 11, or all 14 with SW1_VHB_X=14), cut-outs: SW1 pocket, mic duct, TP6. P hangs 0.6 below on the BM28
(J20 at M (9.825, 6.025), ~7.0 x 2.6): extra cases report the BM28 plug rotation under the press (pry of the 0.35 mm contacts) and a worst case where P rests on the
floor (BM28 as a stiff column, [A]). Writes sw1_press_fem_k4.json/.png.
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
import os  # noqa: E402
K4 = os.environ.get("SW1_BOARD", "").strip().lower() == "k4"
if K4:
    import dims_k4 as K          # numpy-free; the K4 shell numbers
    TAG = "_k4" + ("_vhb14" if os.environ.get("SW1_VHB_X") == "14" else "")
    BW, BH, T = float(K.STACK_L), 12.0, K.PCB_T   # follows the router (was 14.0)
    VHB_T = K.VHB_T
    SW_XY = (5.325, 6.025)       # routed_M.kicad_pcb, board origin = outline corner
    POCKET = (K.POCKET["dx"], K.POCKET["dz"])
    BODY = K.SW1["body"]
    MIC_XY, DUCT_R = (1.775, 5.275), K.DUCT_D / 2
    TP_R = 1.0 / 2 + 0.4
    F_PADS = {"TP6": (1.905, 2.905)}
    BOND_X1 = float(os.environ.get("SW1_VHB_X") or K.STACK_L)     # VHB over the stack footprint (11) unless told all 14
    BM28 = dict(c=(9.825, 6.025), L=7.0, W=2.6)                  # J20 courtyard [E]
    B_MARGIN = round(K.STACK_Y0 - K.CAV["y0"], 3)                # P to the cavity floor: 0.2 free
    TRAVEL = (0.05, 0.15, 0.25)
    POST_W = K.POST_W
    LEDGE = os.environ.get("SW1_LEDGE", "1") != "0"   # ECR-0022: VHB only on the notched ledge tip (default); SW1_LEDGE=0 = old full-face bond
    if LEDGE:
        TAG = "_k4_ledge" + ("_vhb14" if os.environ.get("SW1_VHB_X") == "14" else "")
        import shell_k4 as SK         # build123d; rects are M lid-face courtyards in board coords (x from front edge, z from the low edge)
        _rects, (LB, HB) = SK._m_lid_face_rects()
        LRECTS = [r for r in _rects if r[0] not in ("U2", "SW1")]
else:
    TAG = "" if D.DESIGN.id == "phase2" else f"_{D.OUT_DIR.name}"   # variants write their own outputs (e.g. _k1t_dome)
    BW, BH, T = 30.0, 12.0, D.PCB_T if hasattr(D, "PCB_T") else 0.8
    VHB_T = D.VHB_T                    # 0.25
    SW_XY = (18.5, 6.0)
    POCKET = (D.POCKET["dx"], D.POCKET["dz"])
    BODY = D.SW1["body"]              # 3.0 x 2.6
    MIC_XY, DUCT_R = D.MIC_XY, D.DUCT_D / 2
    TP_R = D.TP_PAD_D / 2 + D.TP_CUT_MARGIN
    F_PADS = D.F_PADS
    BOND_X1, BM28 = BW, None
    B_MARGIN = round(D.B_GAP - D.B_MAX, 3)        # 0.32: tallest B part to the cell plane
    TRAVEL = D.SW1["travel"]
E_PCB, NU = 20e3, 0.15            # N/mm2
INSET = 0.2
E_VHB = (0.15, 0.5, 2.0, 10.0)                # MPa
FORCES = (2.0, 10.0)                          # N


def bonded(x, y):
    """1 where the VHB is bonded (board coords, mm), else 0."""
    m = (x > INSET) & (x < BOND_X1 - INSET) & (y > INSET) & (y < BH - INSET)
    if K4 and LEDGE:
        W, I = K.LEDGE_W, K.LEDGE_INSET
        m = (x > I) & (x < LB - I) & (y > I) & (y < HB - I) & ~((x > I + W) & (x < LB - I - W) & (y > I + W) & (y < HB - I - W))
        for _r, rx0, rz0, rx1, rz1 in LRECTS:      # same notch rule as shell_k4.ledge_ring (courtyards already carry the 0.1 clear)
            m &= ~((x > rx0) & (x < rx1) & (y > rz0) & (y < rz1))
        if os.environ.get("SW1_POCKET_RING"):      # candidate fix: extra 0.5 wide ledge ring round the SW1 pocket (0.2 clear), notched for courtyards
            hx, hz = POCKET[0] / 2 + 0.2, POCKET[1] / 2 + 0.2
            ring = (np.abs(x - SW_XY[0]) < hx + W) & (np.abs(y - SW_XY[1]) < hz + W) & ~((np.abs(x - SW_XY[0]) < hx) & (np.abs(y - SW_XY[1]) < hz))
            for _r, rx0, rz0, rx1, rz1 in LRECTS:
                ring &= ~((x > rx0) & (x < rx1) & (y > rz0) & (y < rz1))
            m |= ring
        m |= (x - MIC_XY[0]) ** 2 + (y - MIC_XY[1]) ** 2 < (K.DUCT_TUBE_D / 2) ** 2     # duct tube ring (bore cut below)
    m &= ~((np.abs(x - SW_XY[0]) < POCKET[0] / 2) & (np.abs(y - SW_XY[1]) < POCKET[1] / 2))
    m &= ~((x - MIC_XY[0]) ** 2 + (y - MIC_XY[1]) ** 2 < DUCT_R ** 2)
    for px, py in F_PADS.values():
        m &= ~((np.abs(x - px) < TP_R) & (np.abs(y - py) < TP_R))
    return m.astype(float)


def load_area(x, y):
    return ((np.abs(x - SW_XY[0]) < BODY[0] / 2) & (np.abs(y - SW_XY[1]) < BODY[1] / 2)).astype(float)


def main():
    nx, ny = int(round(BW / 0.125)) + 1, 97   # h = 0.125 mm
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

    @BilinearForm
    def conn(u, v, w):
        return conn_area(w.x[0], w.x[1]) * u * v

    def conn_area(x, y):
        return ((np.abs(x - BM28["c"][0]) < BM28["L"] / 2) & (np.abs(y - BM28["c"][1]) < BM28["W"] / 2)).astype(float)

    K = asm(plate, ib)
    M = asm(found, ib)
    Mc = asm(conn, ib) if BM28 else None
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
            if BM28:
                wn = w[ib.nodal_dofs[0]]
                px, py = mesh.p
                def wat(x, y):
                    return float(wn[np.argmin((px - x) ** 2 + (py - y) ** 2)])
                cx, cy = BM28["c"]
                wa, wb = wat(cx - BM28["L"] / 2, cy), wat(cx + BM28["L"] / 2, cy)
                r["bm28_end_w_um"] = [round(1e3 * wa, 2), round(1e3 * wb, 2)]
                r["bm28_plug_tilt_urad"] = round(1e6 * abs(wb - wa) / BM28["L"], 1)
                r["bm28_end_to_end_lift_um"] = round(1e3 * abs(wb - wa), 2)
                r["p_floor_gap_mm"] = B_MARGIN
                # P rests on the floor with zero gap: BM28 as a stiff column (3 GPa housing walls ~10 % of the footprint over the 0.6 mated height) [A]
                kc = 0.10 * 3000.0 / 0.6      # N/mm3
                w2 = solve(A + kc * Mc, (F / a_load) * P)
                reac_c = float(kc * (ib.dx * conn_area(xq[0], xq[1]) * ib.interpolate(w2).value).sum())
                r["p_bottomed_bm28_share_N"] = round(reac_c, 3)
                r["p_bottomed_w_sw1_um"] = round(1e3 * float((ib.interpolate(w2).value * la).sum() / max(la.sum(), 1)), 2)
            if BM28 and os.environ.get("SW1_POST", "1") != "0":
                # ECR-0023 floor post: press path M -> BM28 housing -> P -> U1 top -> post -> floor, closing after a fitted gap g. Series stiffness [A]:
                # BM28 housing column 500 N/mm3 x footprint (as above), P through-thickness 0.8 mm E_z 3 GPa over 2x the post area, post 1.0 mm resin 2 GPa over 2.4 x 2.4. Unilateral: the
                # support acts only where w > g (rhs term kc*g), checked after the solve.
                A_b, A_p = BM28["L"] * BM28["W"], POST_W ** 2
                k_abs = 1.0 / (1.0 / (500.0 * A_b) + 0.8 / (3000.0 * 2 * A_p) + 1.0 / (2000.0 * A_p))
                kc_p = k_abs / A_b
                px_, py_ = mesh.p

                @LinearForm
                def conn_g(v, w):
                    return conn_area(w.x[0], w.x[1]) * v
                Pg = asm(conn_g, ib)
                rp = {}
                for g in (0.0, 0.01, 0.02, 0.03, 0.05, 0.10):
                    w3 = solve(A + kc_p * Mc, (F / a_load) * P + kc_p * g * Pg)
                    wv3 = ib.interpolate(w3).value
                    wsw = float((wv3 * la).sum() / max(la.sum(), 1))
                    wc = float((wv3 * conn_area(xq[0], xq[1])).sum() / max(conn_area(xq[0], xq[1]).sum(), 1))
                    sig3 = k * wv3 * bq
                    Fp = float(kc_p * (ib.dx * conn_area(xq[0], xq[1]) * (wv3 - g)).sum()) if wc > g else 0.0
                    if wc <= g:       # post not reached: the free (ledge-only) solution is the answer
                        wsw, sig3 = r["w_sw1_mm"], k * ib.interpolate(w).value * bq
                        vsh = float(k * (ib.dx * ib.interpolate(w).value * bq).sum())
                    else:
                        wsw, vsh = wsw, float(k * (ib.dx * wv3 * bq).sum())
                    rp[f"gap{int(round(g * 1e3))}um"] = dict(w_sw1_um=round(1e3 * wsw, 1), post_N=round(Fp, 2), active=wc > g, vhb_tension_peak_kPa=round(1e3 * float(sig3.max()), 1), vhb_share_N=round(vsh, 3))
                r["post"] = dict(k_post_N_per_mm=round(k_abs), **rp)
            results.append(r)
            if ev == E_VHB[0] and F == FORCES[0]:
                plot_case = (w, k)
    out = dict(src="sim/checks/sw1_press_fem.py", date="2026-10-08" if K4 else "2026-10-07", model="Kirchhoff plate (Morley) on Winkler VHB over the bonded area; lid rigid",
               inputs=dict(board=[BW, BH, T], E_pcb_MPa=E_PCB, nu=NU, vhb_t=VHB_T, inset=INSET, pocket=list(POCKET), sw1_body=list(BODY),
                           sw_xy=list(SW_XY), mic=list(MIC_XY), tp_cut_half=TP_R, mesh=[nx, ny], bond_x1=BOND_X1, k4=K4),
               limits=dict(b_part_margin_to_cell_mm=B_MARGIN, kmt022_travel_mm=list(TRAVEL)),
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
