"""V9 option B+ check: SMPS (F02) and bridge (F01) parts on an UPPER board 2-3 mm directly above the mic region of the LOWER board.

Reuses couple.run_l2 unchanged (same victims, same alias/PSRR/floor chain). Only the geometry hooks are patched:
  - aggressor nets (OUT_A, OUT_B, VLXSMPS) are translated in plane so their centroid sits over the MIC_VDD net centroid (worst alignment)
    and lifted to height h above the victim face (B.Cu of the lower board); victims keep their real routed geometry (draft_r2 routed).
  - magnetic: M = T(f) * M_free(3-D distance). T = max(T1*T2, floor), Ti = 1/sqrt(1+(f/fc_i)^2), fc_i = Rs/(pi mu0 d_i), d_i = source-to-plane distance
    (plane 1 = upper board GND just under the source, plane 2 = lower board GND). floor = edge/aperture leakage (assumption).
  - electric: Cm = leak * Cm_free (planes screen E; leak = BM28 slot, antipads, board edge). In-plane model ratio Cm_image/Cm_free is 0.03.
Run: systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 python3 sim/noise/vertical_bplus.py
"""
from __future__ import annotations
import json, math, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import budget, couple, lumped, pcbgeom, yaml  # noqa: E402

REPO = HERE.parents[1]
AGG_NETS = {"OUT_A", "OUT_B", "VLXSMPS"}
MU0 = 4e-7 * math.pi
CASES = {   # h = height of aggressor above victim face (B.Cu, lower board); d1 = source to its own board's GND plane
    "baseline_in_plane": None,
    "Bplus_trace_h2.2": dict(h=2.2, d1=0.15, floor=0.10, leak=0.03),
    "Bplus_L1_h2.7":    dict(h=2.7, d1=0.65, floor=0.10, leak=0.03),
    "Bplus_L1_h2.7_pess": dict(h=2.7, d1=0.65, floor=0.25, leak=0.10),
    "Bplus_trace_h2.2_pess": dict(h=2.2, d1=0.15, floor=0.25, leak=0.10),
    "Bplus_L1_h2.7_opt": dict(h=2.7, d1=0.65, floor=0.03, leak=0.01),
    "Bplus_L1_h2.7_noplane": dict(h=2.7, d1=0.65, floor=1.0, leak=1.0),   # planes ignored: bound
}

def run(case):
    params = budget.load_yaml(HERE / "params.yaml"); agg = budget.load_yaml(HERE / "aggressors.yaml")
    board = pcbgeom.default_board(REPO)
    geom = pcbgeom.load(board)
    bom = lumped.read_bom(pcbgeom.bom_path(REPO, params))
    net, info, mesh, red = budget.build_l1(geom, params, bom)
    st = geom["stackup"]
    orig = dict(orient=couple.orient, pieces=couple.pieces, m_eff=couple.m_eff, cap=couple.mutual_cap_fF)
    cfg = CASES[case]
    if cfg:
        vp = [p for p in geom["pads"] if p["net"] == "MIC_VDD"]
        cx = np.mean([p["x"] for p in vp]); cy = np.mean([p["y"] for p in vp])
        zv = couple.layer_z(st, "B.Cu")
        u_in1 = -zv                                  # lower GND plane height above the victim face
        d2 = cfg["h"] - u_in1
        rs = info["plane"]["sheet_ohm_sq"]
        fcs = [rs / (math.pi * MU0 * cfg["d1"] * 1e-3), rs / (math.pi * MU0 * d2 * 1e-3)]
        def orient(inf, n, root):
            s = orig["orient"](inf, n, root)
            if n in AGG_NETS:
                for e in s: e["_agg"] = True
            return s
        def pieces(segs, st_, step=couple.STEP):
            P = orig["pieces"](segs, st_, step)
            if segs and segs[0].get("_agg") and P.get("n"):
                P["pos"] = P["pos"].copy()
                P["pos"][:, 0] += cx - P["pos"][:, 0].mean(); P["pos"][:, 1] += cy - P["pos"][:, 1].mean()
                P["pos"][:, 2] = zv + cfg["h"]
            return P
        def m_eff(mf, mi, f, fc):
            T = max(math.prod(1 / math.sqrt(1 + (f / c) ** 2) for c in fcs), cfg["floor"])
            return T * mf
        def cap(A, V, st_, mode, eps):
            if mode == "image":
                return cfg["leak"] * orig["cap"](A, V, st_, "free", eps)
            return orig["cap"](A, V, st_, mode, eps)
        couple.orient, couple.pieces, couple.m_eff, couple.mutual_cap_fF = orient, pieces, m_eff, cap
    try:
        res, _ = budget.analyse(net, info, geom, params, agg, HERE / "out_vert", log=lambda *a: None)
    finally:
        couple.orient, couple.pieces, couple.m_eff, couple.mutual_cap_fF = orig["orient"], orig["pieces"], orig["m_eff"], orig["cap"]
    out = dict(case=case, cfg=cfg, fc_hz=None if not cfg else [round(c) for c in fcs])
    for r in res["l2_rows"]:
        k = f'{r["aggressor"][:3]}|{r["victim"][:3]}|{r["mechanism"][:3]}'
        out[k] = round(r["margin_pes"], 1) if r["kind"] == "tone" else round(r["margin_pes"], 1)
    out["pairs"] = {f'{p["aggressor"][:3]}|{p["victim"][:3]}': (p["M_free_nH"], p["M_image_nH"], p["Cm_free_fF"], p["Cm_image_fF"]) for p in res["l2_pairs"]}
    out["tone_rows"] = [(r["aggressor"][:3], r["mechanism"][:3], round(r["margin_nom"], 1), round(r["margin_pes"], 1), round(r["margin_worst"], 1), r["regime"])
                        for r in res["l2_rows"] if r["kind"] == "tone"]
    return out

if __name__ == "__main__":
    allr = {}
    for c in CASES:
        allr[c] = run(c); print(json.dumps(allr[c], default=float), flush=True)
    (HERE / "out_vert").mkdir(exist_ok=True)
    (HERE / "out_vert" / "bplus.json").write_text(json.dumps(allr, indent=1, default=float))
