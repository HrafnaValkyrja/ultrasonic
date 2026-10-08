#!/usr/bin/env python3
"""ECR-0023 rev: compressible floor pad (Poron / silicone foam) instead of the shim-fitted rigid post. Dated 2026-10-08.

Reuses sw1_press_fem.py (K4 ledge mode) plate + Winkler VHB model; the pad is a nonlinear unilateral spring under the BM28 line (path lid-M-BM28-P-U1-pad-floor).
Per corner of the floor tolerance chain: initial interference d0 = pad_t*(1+tp) - (U1 top above floor) +- chain, solve pad force Fp(d) with the board compliance:
  preload (F=0): d = d0 - Fp*c_cc ; press: d = d0 + w_c(F) - Fp*c_cc ;  SW1 board motion = w_sw(F) - (Fp - Fp_pre)*c_sc   (w>0 = away from the lid)
Pad curve: foam CFD at 25 % from the datasheet (Poron 4701-30 20 lb: 21/35/55 kPa min/typ/max, Rogers PDS 0723-PDF Pub 17-006, 2023; BISCO HT-800: typ 67 kPa, Rogers PDS)
times a normalised stress-strain shape [A] (the Rogers sheets give only the 25 % point; shape = generic closed-cell foam with densification, swept by the CFD range).
Run fenced: SW1_BOARD=k4 systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 python3 sim/checks/sw1_pad_fem.py
"""
import itertools, json, os, sys
os.environ["SW1_BOARD"] = "k4"
import numpy as np
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import sw1_press_fem as S
from skfem import Basis, BilinearForm, ElementTriMorley, LinearForm, MeshTri, asm, solve
from skfem.helpers import dd, ddot, eye, trace
K = S.K
T = S.T
nx, ny = int(round(S.BW / 0.125)) + 1, 97
mesh = MeshTri.init_tensor(np.linspace(0, S.BW, nx), np.linspace(0, S.BH, ny))
ib = Basis(mesh, ElementTriMorley(), intorder=4)

@BilinearForm
def plate(u, v, w):
    C = lambda Tn: S.E_PCB / (1 + S.NU) * (Tn + S.NU / (1 - S.NU) * eye(trace(Tn), 2))
    return T ** 3 / 12.0 * ddot(C(dd(u)), dd(v))
@BilinearForm
def found(u, v, w):
    return S.bonded(w.x[0], w.x[1]) * u * v
@LinearForm
def press(v, w):
    return S.load_area(w.x[0], w.x[1]) * v
@LinearForm
def connl(v, w):
    return S.conn_area_(w.x[0], w.x[1]) * v if hasattr(S, "conn_area_") else ((np.abs(w.x[0] - S.BM28["c"][0]) < S.BM28["L"] / 2) & (np.abs(w.x[1] - S.BM28["c"][1]) < S.BM28["W"] / 2)).astype(float) * v
Kp, M, P, Pc = asm(plate, ib), asm(found, ib), asm(press, ib), asm(connl, ib)
xq = ib.global_coordinates().value
la = S.load_area(xq[0], xq[1])
cm = ((np.abs(xq[0] - S.BM28["c"][0]) < S.BM28["L"] / 2) & (np.abs(xq[1] - S.BM28["c"][1]) < S.BM28["W"] / 2)).astype(float)
a_load, a_b = S.BODY[0] * S.BODY[1], S.BM28["L"] * S.BM28["W"]
mean = lambda w, m: float((ib.interpolate(w).value * m).sum() / max(m.sum(), 1))

# normalised foam curve: stress / stress@25 % vs strain [A]
EPS = [0, .10, .25, .40, .50, .60, .70, .80, .90]
REL = [0, .45, 1.0, 1.7, 2.4, 3.8, 6.5, 14., 40.]
def sig(eps, s25):          # kPa
    return s25 * float(np.interp(min(max(eps, 0), .9), EPS, REL))
def pad_force(d, t, s25, area):   # N ; d interference mm, t free thickness
    return sig(d / t, s25) * 1e-3 * area      # kPa*mm2 -> mN -> N: kPa=1e-3 N/mm2

MAT = {"Poron 4701-30 20lb": (21., 35., 55.), "BISCO HT-800": (41., 67., 97.)}
def run(mat, t0, area_w, forces=(2.0, 10.0), ev_list=(0.15, 0.5, 2.0), u1_up=None):
    u1_h = K.P_OUT_Y - K.U1_H - K.CAV["y0"]          # U1 nominal top above the floor
    area = area_w ** 2
    rows = []
    chain = K.POST_CHAIN_LIN                          # +-0.537
    for ev in ev_list:
        k = ev / K.VHB_T
        A = Kp + k * M
        wp = {F: solve(A, (F / a_load) * P) for F in forces}
        wu = solve(A, (1.0 / a_b) * Pc)                # unit upward... load toward the cell (+w) of 1 N on the BM28 line
        c_cc, c_sc = mean(wu, cm), mean(wu, la)      # mm/N (pad pushes toward the lid: -1 N)
        bq = S.bonded(xq[0], xq[1])
        for s25, tp, ch in itertools.product(mat, (-0.10, 0, 0.10), (-chain, 0, chain)):
            d0 = t0 * (1 + tp) - u1_h + ch           # interference with the stack at its nominal position
            t = t0 * (1 + tp)
            # preload: d = d0 - Fp*c_cc
            lo, hi = 0.0, 60.0
            if d0 <= 0: Fp = 0.0
            else:
                for _ in range(60):
                    Fp = .5 * (lo + hi)
                    if pad_force(max(d0 - Fp * c_cc, 0), t, s25, area) > Fp: lo = Fp
                    else: hi = Fp
            shift_um = 1e3 * Fp * c_sc               # SW1 board moved toward the lid (closes PRE_GAP)
            pre_sig = k * np.abs(ib.interpolate(wu).value) * bq * Fp          # VHB compression under preload (kPa*1e-3.. N/mm2)
            for F in forces:
                wc, ws = mean(wp[F], cm), mean(wp[F], la)
                lo, hi = 0.0, 80.0
                for _ in range(60):
                    Fq = .5 * (lo + hi)
                    if pad_force(max(d0 + wc - Fq * c_cc, 0), t, s25, area) > Fq: lo = Fq
                    else: hi = Fq
                if d0 + wc <= 0: Fq = 0.0
                wsw = ws - (Fq - Fp) * c_sc          # board motion at SW1 from the preloaded position
                wfull = wp[F] - (Fq) * wu             # tension peak field
                ten = 1e3 * k * float(np.max(ib.interpolate(wfull).value * bq))
                rows.append(dict(E=ev, cfd25=s25, tp=tp, chain=round(ch, 3), F=F, d0=round(d0, 3), contact=d0 > 0, preload_N=round(Fp, 3), preload_MPa_U1=round(Fp / area, 3), preload_shift_um=round(shift_um, 1),
                                 pad_N_at_press=round(Fq, 2), sw1_um=round(1e3 * wsw, 1), vhb_tension_kPa=round(ten, 1), strain_max=round(min(max(d0 + wc - Fq * c_cc, 0) / t, 9), 2)))
    return rows

if __name__ == "__main__":
    out = {}
    for mname, mat in MAT.items():
        for t0 in (1.57, 2.36):
            for aw in (1.5, 2.4):
                r = run(mat, t0, aw, forces=(2.0,), ev_list=(0.5,))
                two = [x for x in r if x["F"] == 2.0]
                ok_c = all(x["contact"] for x in r)
                s = dict(contact_all_corners=ok_c, d0_range=[min(x["d0"] for x in r), max(x["d0"] for x in r)],
                         preload_N_max=max(x["preload_N"] for x in r), preload_MPa_U1_max=max(x["preload_MPa_U1"] for x in r), preload_shift_um_max=max(x["preload_shift_um"] for x in r),
                         sw1_um_2N_worst=max(x["sw1_um"] for x in two), vhb_tension_2N_worst=max(x["vhb_tension_kPa"] for x in two),
                         strain_max=max(x["strain_max"] for x in r),
                         sw1_um_2N_worst_in_contact=max([x["sw1_um"] for x in two if x["contact"]] or [0]))
                key = f"{mname}|t{t0}|{aw}sq"
                out[key] = dict(summary=s, rows=r)
                print(key, s)
    Path(S.ROOT / "sim/out/mech/sw1_pad_fem.json").write_text(json.dumps(out, indent=1))
