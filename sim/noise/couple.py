"""L2: magnetic (mutual inductance) and electric (mutual capacitance) coupling between nets, from the board geometry.

Quasi-static filament model. Every trace segment is cut into pieces <= STEP mm placed at its layer's height above
the In1 plane (z = 0). Two limits bound the answer (the plane is a thin 15 um sheet: it screens B only above f_c = R_s / (pi mu0 d) ~ 1 MHz,
see docs/sim/layout-noise.yaml `limits`). M(f) = M_img + T(f) (M_free - M_img), T = 1/sqrt(1+(f/f_c)^2): T = 1 is the
no-plane limit (low f), T -> 0 the perfect-plane limit (high f). An engineering interpolation, not a field solve.
  image : perfect plane, return directly under each trace (valid f >> f_c): M = mu0/4pi * sum dl_i.dl_j (1/r - 1/r'),
          same side of the plane only; opposite-side pairs are shielded (0). Capacitance likewise, images in the plane.
  free  : no plane (valid f << f_c): M = mu0/4pi * sum dl_i.dl_j / r, all pairs; capacitance in free homogeneous dielectric.
Capacitance always uses the image model (a 15 um sheet screens E fields at any frequency; only B leaks at f < f_c).
Currents in an aggressor net are taken UNIFORM along the whole net (an upper bound on branches), directed away from a root pad.
Vias, pads and the exciter wires are not in the field model.

    from couple import run_l2;  rows = run_l2(geom, info_l1, net_l1, params, agg, log=print)
"""
from __future__ import annotations

import math
from collections import defaultdict, deque

import numpy as np

import alias
import lumped
from budget import lines, spur_dbfs
from pcbgeom import COPPER, height_to_plane

MU0 = 4e-7 * math.pi
EPS0 = 8.8541878128e-12
STEP = 0.25  # mm


def layer_z(st: dict, layer: str) -> float:
    cu = {k: v / 1000.0 for k, v in st["copper_um"].items()}
    d = st["dielectric_mm"]
    return {"F.Cu": d[0] + cu["F.Cu"] / 2, "In1.Cu": 0.0, "In2.Cu": -(d[1] + cu["In2.Cu"] / 2),
            "B.Cu": -(d[1] + cu["In2.Cu"] + d[2] + cu["B.Cu"] / 2)}[layer]


def orient(info: dict, net: str, root_node: str):
    """Segments of `net` re-oriented away from root_node (BFS over segments and via links; a cycle's closing segment is dropped)."""
    adj = defaultdict(list)
    for e in info["seg_edges"]:
        if e["net"] == net:
            adj[e["a"]].append((e["b"], e, False))
            adj[e["b"]].append((e["a"], e, True))
    for a, b, n in info["via_edges"]:
        if n == net:
            adj[a].append((b, None, False))
            adj[b].append((a, None, False))
    seen, out, q = {root_node}, [], deque([root_node])
    while q:
        u = q.popleft()
        for v, e, rev in adj[u]:
            if v in seen:
                continue
            seen.add(v)
            q.append(v)
            if e is not None:
                o = dict(e)
                if rev:
                    o["x1"], o["y1"], o["x2"], o["y2"] = e["x2"], e["y2"], e["x1"], e["y1"]
                out.append(o)
    return out


def pieces(segs: list[dict], st: dict, step: float = STEP):
    P = []
    for s in segs:
        L = math.hypot(s["x2"] - s["x1"], s["y2"] - s["y1"])
        n = max(1, int(math.ceil(L / step)))
        z = layer_z(st, s["layer"])
        for i in range(n):
            t0, t1 = i / n, (i + 1) / n
            x0, y0 = s["x1"] + t0 * (s["x2"] - s["x1"]), s["y1"] + t0 * (s["y2"] - s["y1"])
            x1, y1 = s["x1"] + t1 * (s["x2"] - s["x1"]), s["y1"] + t1 * (s["y2"] - s["y1"])
            P.append((0.5 * (x0 + x1), 0.5 * (y0 + y1), z, x1 - x0, y1 - y0, s["w"], s["layer"]))
    if not P:
        return dict(n=0)
    a = np.array([p[:6] for p in P], float)
    return dict(n=len(P), pos=a[:, :3], dl=np.c_[a[:, 3:5], np.zeros(len(P))], w=a[:, 5], layer=[p[6] for p in P])


def mutual_nH(A: dict, V: dict, mode: str, signs: np.ndarray | None = None):
    """Pairwise mutual inductance matrix (na x nv), nH. mode 'free' or 'image'."""
    if A["n"] == 0 or V["n"] == 0:
        return np.zeros((A["n"], V["n"]))
    pa, pv = A["pos"], V["pos"]
    d = pa[:, None, :] - pv[None, :, :]
    r = np.sqrt((d ** 2).sum(-1) + 0.05 ** 2)               # mm, 50 um floor ~ conductor GMD
    dot = A["dl"] @ V["dl"].T                                # mm^2
    k = MU0 / (4 * math.pi) * 1e-3                           # mm*mm/mm -> m: dot/r is in mm; *1e-3 -> m
    M = k * dot / r
    if mode == "image":
        pv_i = pv.copy(); pv_i[:, 2] *= -1
        di = pa[:, None, :] - pv_i[None, :, :]
        ri = np.sqrt((di ** 2).sum(-1) + 0.05 ** 2)
        M = M - k * dot / ri
        same = (pa[:, None, 2] * pv[None, :, 2]) > 0
        M = np.where(same, M, 0.0)
    return M * 1e9


def mutual_cap_fF(A: dict, V: dict, st: dict, mode: str, eps_eff: dict) -> float:
    """Mutual capacitance (fF) between conductor A (all pieces) and V, charge-based filament model."""
    if A["n"] == 0 or V["n"] == 0:
        return 0.0
    pos = np.vstack([A["pos"], V["pos"]])
    dl = np.vstack([A["dl"], V["dl"]])
    w = np.r_[A["w"], V["w"]]
    layers = A["layer"] + V["layer"]
    n = len(pos)
    ell = np.hypot(dl[:, 0], dl[:, 1]) * 1e-3                # m
    eps = np.array([EPS0 * eps_eff[l] for l in layers])
    d = (pos[:, None, :] - pos[None, :, :])
    r = np.sqrt((d ** 2).sum(-1)) * 1e-3
    pi_ = pos.copy(); pi_[:, 2] *= -1
    di = pos[:, None, :] - pi_[None, :, :]
    ri = np.sqrt((di ** 2).sum(-1)) * 1e-3
    em = 0.5 * (eps[:, None] + eps[None, :])
    P = np.zeros((n, n))
    with np.errstate(divide="ignore"):
        P = (1.0 / (4 * math.pi * em)) * (1.0 / np.where(r > 0, r, np.inf))
    a_eq = np.maximum(w * 1e-3 / 4, 5e-6)
    selfp = (1.0 / (4 * math.pi * eps * ell)) * 2 * np.arcsinh(ell / (2 * a_eq))
    P[np.arange(n), np.arange(n)] = selfp
    if mode == "image":
        same = (pos[:, None, 2] * pos[None, :, 2]) > 0
        Pimg = (1.0 / (4 * math.pi * em)) / np.where(ri > 0, ri, np.inf)
        P = P - np.where(same, Pimg, 0.0)
        P = np.where(same | np.eye(n, dtype=bool), P, 0.0)   # cross-side shielded
        # keep P positive definite when a side has pieces of only one conductor: fine (block diagonal)
    B = np.zeros((n, 2)); B[:A["n"], 0] = 1; B[A["n"]:, 1] = 1
    X = np.linalg.solve(P, B)
    C = B.T @ X
    return float(-C[0, 1] * 1e15)


def eps_eff_by_layer(st: dict) -> dict:
    """Effective dielectric constant of a microstrip (Hammerstad, w/h = 1) on each layer's dielectric stack."""
    out = {L: height_to_plane(st, L)[1] for L in ("F.Cu", "In2.Cu", "B.Cu")}
    out["In1.Cu"] = out["F.Cu"]
    return {k: (v + 1) / 2 + (v - 1) / 2 * (1 + 12) ** -0.5 for k, v in out.items()}


def f_cross(rs: float, d_mm: float = 0.3) -> float:
    return rs / (math.pi * MU0 * d_mm * 1e-3)


def transmission(f: float, fc: float) -> float:
    return 1.0 / math.sqrt(1.0 + (f / fc) ** 2)


def m_eff(m_free, m_img, f: float, fc: float):
    t = transmission(f, fc)
    return m_img + t * (m_free - m_img)


def run_l2(geom, info_l1, net_l1, params, agg, probe_pairs, victims, tone_lim, log=print):
    """Rows (same shape as budget.analyse rows) for magnetic and electric pickup, plus a pair table of M and Cm."""
    st = geom["stackup"]
    fc = f_cross(info_l1["plane"]["sheet_ohm_sq"])
    eps_eff = eps_eff_by_layer(st)
    need = {n for fa in agg["field_aggressors"] for n in fa["nets"]} | {fv["net"] for fv in agg["field_victims"]}
    tmp = lumped.Network()
    tmp_info = lumped.add_nets(tmp, geom, need)
    roots = agg.get("roots", {})
    P = {}
    for n in need:
        pads = [p for p in geom["pads"] if p["net"] == n]
        rp = roots.get(n) or f'{pads[0]["ref"]}.{pads[0]["num"]}'
        P[n] = pieces(orient(tmp_info, n, tmp_info["pad_node"][rp]), st)
    rows, pair_table = [], []
    cache_i, cache_z = {}, {}
    have = {v["id"] for v in victims}
    for fa in agg["field_aggressors"]:
        nets_a = fa["nets"]
        for fv in agg["field_victims"]:
            if fv["in_network"] and fv["probe"] not in have:
                continue
            Pv = P[fv["net"]]
            Mf, top = {}, []
            for m in ("free", "image"):
                Mf[m] = sum(sgn * mutual_nH(P[na], Pv, m).sum() for na, sgn in nets_a.items())
            for na in nets_a:
                Mij = mutual_nH(P[na], Pv, "image")
                if Mij.size:
                    i, j = np.unravel_index(np.argmax(np.abs(Mij)), Mij.shape)
                    top.append(dict(agg_net=na, agg_xy=[round(float(P[na]["pos"][i, 0]), 2), round(float(P[na]["pos"][i, 1]), 2)], agg_layer=P[na]["layer"][i],
                                    vic_xy=[round(float(Pv["pos"][j, 0]), 2), round(float(Pv["pos"][j, 1]), 2)], vic_layer=Pv["layer"][j],
                                    m_pair_nH=round(float(Mij[i, j]), 5)))
            Cm = {m: sum(sgn * mutual_cap_fF(P[na], Pv, st, m, eps_eff) for na, sgn in nets_a.items()) for m in ("free", "image")}
            pair_table.append(dict(aggressor=fa["id"], victim=fv["id"], M_free_nH=round(Mf["free"], 4), M_image_nH=round(Mf["image"], 4),
                                   Cm_free_fF=round(Cm["free"], 4), Cm_image_fF=round(Cm["image"], 4), f_cross_hz=round(fc), top_pieces=top))
            ls_i, ls_v = dict(lines(fa["current"])), dict(lines(fa["voltage"]))
            seg_M = None
            if fv["in_network"]:      # per-victim-segment mutual inductance for the EMF distribution
                segs = [dict(x1=e["xy"][0], y1=e["xy"][1], x2=e["xy"][2], y2=e["xy"][3], layer=e["layer"], w=e["w"], i=idx)
                        for idx, e in enumerate(net_l1.elems) if e.get("kind_") == "trace" and e["net"] == fv["net"] and e["kind"] == "R"]
                seg_M = {m: np.array([sum(sgn * mutual_nH(P[na], pieces([s], st), m).sum() for na, sgn in nets_a.items()) for s in segs]) for m in ("free", "image")}
                vi = next(i for i, v in enumerate(victims) if v["id"] == fv["probe"])
                pp = probe_pairs[vi]
            best = {"magnetic": None, "electric": None}
            for f, ia in ls_i.items():
                va = ls_v.get(f, 0.0)
                tol = fa.get("f_tol_frac", 0.0)
                cands = [f] if (fa.get("sync") or tol == 0) else list(np.linspace(f * (1 - tol), f * (1 + tol), 200))
                for fcand in cands:
                    fo, att, dc = alias.chain(fcand)
                    reg = f"T={transmission(fcand, fc):.2f}"
                    w = 2 * math.pi * fcand
                    C = abs(Cm["image"])    # electric field is screened by the plane at every frequency (only magnetic flux leaks through a 15 um sheet)
                    i_cap = w * C * 1e-15 * va                       # A peak injected by the voltage swing
                    if fv["in_network"]:
                        if (dc and fa.get("sync")) or not (20e3 <= fo <= 96e3) or fcand > params["model"]["f_max_net_hz"]:
                            continue
                        key = round(fcand, 1)
                        if key not in cache_i:
                            res, cur = net_l1.ac(np.array([fcand]), [pp], [pp], want_currents=True)
                            cache_i[key] = (cur[0][0], abs(res[0][0][0]))
                        i_el, z_in = cache_i[key]
                        ik = np.array([i_el[s["i"]] for s in segs])
                        v_mag = abs(1j * w * (m_eff(seg_M["free"], seg_M["image"], fcand, fc) * 1e-9) @ ik) * ia / math.sqrt(2)
                        v_el = i_cap * z_in / math.sqrt(2)
                        for mech, vv in (("magnetic", v_mag), ("electric", v_el)):
                            s_n, s_p = spur_dbfs(vv, fcand, att, params, "nominal"), spur_dbfs(vv, fcand, att, params, "pessimistic")
                            s_w = spur_dbfs(vv, fcand, att, params, "worst")
                            r = dict(aggressor=fa["id"], victim=fv["id"], mechanism=mech, kind="tone", f_hz=fcand, f_out_hz=fo, att_db=att, v_rms=vv,
                                     spur_nom=s_n, spur_pes=s_p, limit=tone_lim, margin_nom=tone_lim - s_n, margin_pes=tone_lim - s_p, regime=reg,
                                     spur_worst=s_w, margin_worst=tone_lim - s_w)
                            if best[mech] is None or r["margin_pes"] < best[mech]["margin_pes"]:
                                best[mech] = r
                    else:
                        z = abs(1.0 / (1.0 / fv["z_node_ohm"] + 1j * w * (fv["c_node_pf"] * 1e-12 + C * 1e-15)))
                        for mech, vv in (("magnetic", w * abs(m_eff(Mf["free"], Mf["image"], fcand, fc)) * 1e-9 * ia), ("electric", i_cap * z)):
                            r = dict(aggressor=fa["id"], victim=fv["id"], mechanism=mech, kind="digital", f_hz=fcand, v_pk=vv, limit_v_pk=0.1, regime=reg)
                            if best[mech] is None or vv > best[mech]["v_pk"]:
                                best[mech] = r
            for mech, r in best.items():
                if r is None:
                    continue
                if r["kind"] == "digital":      # peak-sum over harmonics as a bound
                    tot = 0.0
                    for f, ia in ls_i.items():
                        w = 2 * math.pi * f
                        C = abs(Cm["image"])
                        if mech == "magnetic":
                            tot += w * abs(m_eff(Mf["free"], Mf["image"], f, fc)) * 1e-9 * ia
                        else:
                            z = abs(1.0 / (1.0 / fv["z_node_ohm"] + 1j * w * (fv["c_node_pf"] * 1e-12 + C * 1e-15)))
                            tot += w * C * 1e-15 * ls_v.get(f, 0.0) * z
                    r["v_pk_sum_harmonics"] = tot
                    r["margin_nom"] = r["margin_pes"] = min(200.0, 20 * math.log10(0.1 / max(tot, 1e-18)))
                rows.append(r)
    return rows, pair_table, dict(f_cross_hz=fc, eps_eff=eps_eff)


def selftest() -> dict:
    """Closed-form checks of the filament model (run by extract.py --selfcheck): Grover free-space M, image-line M', image-wire Cm."""
    from pcbgeom import DEFAULT_STACKUP as st

    def seg(x1, y1, x2, y2):
        return dict(x1=x1, y1=y1, x2=x2, y2=y2, layer="F.Cu", w=0.1)

    l, d = 10.0, 1.0
    M = mutual_nH(pieces([seg(0, 0, l, 0)], st), pieces([seg(0, d, l, d)], st), "free").sum()
    exact = 2e-7 * (l * 1e-3) * (math.log(l / d + math.sqrt(1 + (l / d) ** 2)) - math.sqrt(1 + (d / l) ** 2) + d / l) * 1e9
    e1 = abs(M / exact - 1)
    l = 40.0
    A, V = pieces([seg(0, 0, l, 0)], st), pieces([seg(0, d, l, d)], st)
    h = layer_z(st, "F.Cu")
    Mi = mutual_nH(A, V, "image").sum()
    Mp = 1e-7 * math.log((d ** 2 + (2 * h) ** 2) / d ** 2) * (l * 1e-3) * 1e9
    e2 = abs(Mi / Mp - 1)
    eps = {"F.Cu": 3.0, "In1.Cu": 3.0, "In2.Cu": 4.0, "B.Cu": 4.0}
    Cm = mutual_cap_fF(A, V, st, "image", eps)
    e0, a, hh = EPS0 * 3.0, 0.1e-3 / 4, h * 1e-3
    P11 = math.log(2 * hh / a) / (2 * math.pi * e0)
    P12 = 0.5 * math.log(((d * 1e-3) ** 2 + 4 * hh ** 2) / (d * 1e-3) ** 2) / (2 * math.pi * e0)
    cm = abs(P12 / (P11 ** 2 - P12 ** 2)) * l * 1e-3 * 1e15
    e3 = abs(Cm / cm - 1)
    assert e1 < 0.01 and e2 < 0.06 and e3 < 0.15, (e1, e2, e3)
    return dict(grover_err=round(e1, 4), image_M_err=round(e2, 4), image_Cm_err=round(e3, 4))
