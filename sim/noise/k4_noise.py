"""K4 post-route layout-noise check: two 6L boards (P upper: U1 + SMPS + bridge; M lower: mic) on the REAL routed geometry.

sim/noise extract.py/budget.py/pcbgeom.py are 4-layer, one-board tools (pcbgeom asserts 4 copper layers; the MIC_VDD network spans the BM28 and
two boards). This script reuses their field-coupling kernels (couple.mutual_nH, couple.mutual_cap_fF) and the SAME aggressors/victims
(aggressors.yaml F01 bridge OUT_A/OUT_B, F02 SMPS VLXSMPS, victims MIC_VDD/MIC_DATA/MIC_CLK), on a global 3-D stack (P over M, gap g), and reports
the CHANGE in coupling vs today's board (draft_r2, same function, same method). The dB change is applied to today's budget.json l2 margins
(sim/noise/out_r2). NOT covered (stated in the report): conduction (the L1 network with the BM28 contact R/L and the second board's planes), the
victim current distribution (uniform current along the net, both boards), acoustic coupling.
    systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 python3 sim/noise/k4_noise.py [--gap 1.3] [--out DIR]
Metrics: dB_signed = signed vector sum (the budget's convention); dB_abs = sum of |pair terms| (no sign cancellation, pessimistic). Margins = today's budget.json l2 margin minus the dB change at the dominant line.
Model (per aggressor piece a, victim piece v, global z):
  M_free  = Neumann filament sum; M_im = M_free - (victim image about the victim board's own GND plane In1) if both on the same side of that plane else 0
  T_own   = 1/sqrt(1+(f/fc)^2), fc = Rs/(pi mu0 0.3 mm) (couple.f_cross, = 0.955 MHz) - same as couple.run_l2
  T_btw   = (cross-board pairs only) product over the AGGRESSOR board's planes (In1 GND, In2 +3V0) strictly between a and v, fc_i = Rs/(pi mu0 d_i), d_i = a to plane
  M_eff   = M_im + T (M_free - M_im), T = T_own*T_btw; cross-board T floored at --floor (edge/aperture leakage). Today's board = couple.run_l2 convention exactly
Electric (E-field) is NOT computed here: bound = today's electric margins minus the full Cm_free/Cm_image ratio (budget.json l2_pairs, ~30 dB), i.e. as if no plane screened the aggressor.
"""
from __future__ import annotations
import argparse, json, math, sys
from collections import defaultdict, deque
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(REPO / "tools"))
from current import current  # noqa: E402  (hw/current.yaml: the design under test = K4 P/M boards; baseline = the phase2 variant)
import pcbnew  # noqa: E402
_orig = pcbnew.BOARD.GetCopperLayerCount
pcbnew.BOARD.GetCopperLayerCount = lambda s: 4          # pcbgeom's 4L assert; we use only its segment/pad/via reader
import budget, couple, pcbgeom  # noqa: E402

MU0 = couple.MU0
LAYERS6 = ["F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu"]
CU6 = {"F.Cu": 35, "In1.Cu": 15.2, "In2.Cu": 15.2, "In3.Cu": 15.2, "In4.Cu": 15.2, "B.Cu": 35}   # um; JLC 6L copper 0.035 / 0.0152 (impedance page, read 2026-10-08)
# K4-STACK6 (2026-10-08, headless Chromium, https://jlcpcb.com/impedance "6-Layer Impedance Control Stackup" and
# https://jlcpcb.com/resources/6-layer-pcbs + /capabilities): JLC orders 6L at 0.8 mm (resources page: 0.8/1.0/1.2/1.6/2.0; FR4 0.4..2.0, tol +-0.1 mm
# below 1.0 mm) but PUBLISHES 6L impedance stack-ups only for 1.2 / 1.6 / 2.0 mm (page tabs). Smallest published (1.2 mm) examples, all Cu 0.035 outer /
# 0.0152 inner: JLC06161H-1080 = 1080 0.0764 / core 0.55 / 7628 0.2104 / core 0.55 / 1080 0.0764; JLC06161H-2116B = 2116 0.1164 / core 0.5 / 1080x2 0.1528 /
# core 0.5 / 2116 0.1164. eps: core 4.6, prepreg 7628 4.4, 3313 4.1, 1080 3.91, 2116 4.16. NO 0.8 mm 6L build is published -> the dielectric split below is
# unknown: 0.8 - 0.131 Cu = 0.669 mm over 5 layers. Two bounding models: "uniform" (0.134 each) and "thin_outer" (outer prepregs 0.0764 = 1080, the other
# three 0.172). The total (0.8 +-0.1) and the gap are what matter at 3 MHz; the split only moves plane-to-trace distances inside one board.
STACK_DIEL = {"uniform": [0.1338] * 5, "thin_outer": [0.0764, 0.1724, 0.1724, 0.1724, 0.0764]}
AGG_ROOT = {"OUT_A": ("Q1", "3"), "OUT_B": ("Q2", "3"), "VLXSMPS": ("U1", "20"), "MIC_VDD": ("U1", "15"), "MIC_CLK": ("R2", "2"), "MIC_DATA": ("U2", "1")}
FIELD_AGG = [("F01_BRIDGE_OUT", {"OUT_A": 1.0, "OUT_B": -1.0}, (0.2e6, 0.6e6, 2e6)), ("F02_SMPS_LX", {"VLXSMPS": 1.0}, (3e6, 6e6, 9e6, 27e6))]
VICTIMS = [("FV1_MIC_VDD", "MIC_VDD"), ("FV2_MIC_DATA", "MIC_DATA"), ("FV3_MIC_CLK", "MIC_CLK")]


STACK = {"mode": "uniform"}


def zstack(top: float, flip: bool = False) -> dict:
    """layer centre z (mm, up) of a 0.8 mm board whose top face is at `top`. flip: the file's B.Cu is the top face (board P: its file F is the inner face
    that looks at M, place_k4.py header), else F.Cu is the top face."""
    cu = sum(CU6.values()) / 1000.0
    dd = STACK_DIEL[STACK["mode"]]
    d = [x * (0.8 - cu) / sum(dd) for x in dd]
    z, out = top, {}
    for i, L in enumerate(reversed(LAYERS6) if flip else LAYERS6):
        t = CU6[L] / 1000.0
        out[L] = z - t / 2
        z -= t + (d[i] if i < 5 else 0)
    return out


def zstack4(top: float) -> dict:
    st = pcbgeom.DEFAULT_STACKUP
    cu = {k: v / 1000 for k, v in st["copper_um"].items()}
    d = st["dielectric_mm"]
    z, out = top, {}
    seq = ["F.Cu", "In1.Cu", "In2.Cu", "B.Cu"]
    for i, L in enumerate(seq):
        out[L] = z - cu[L] / 2
        z -= cu[L] + (d[i] if i < 3 else 0)
    return out


def load(path):
    return pcbgeom.load(path, stackup=pcbgeom.DEFAULT_STACKUP)


def orient(geom, net, root_xy):
    """BFS orientation of the net's segments away from root (xy nodes; vias/pads join layers). Returns list of (seg, x1,y1,x2,y2)."""
    key = lambda x, y: (round(x, 2), round(y, 2))
    adj = defaultdict(list)
    for s in geom["segments"]:
        if s["net"] != net:
            continue
        adj[key(s["x1"], s["y1"])].append((key(s["x2"], s["y2"]), s, False))
        adj[key(s["x2"], s["y2"])].append((key(s["x1"], s["y1"]), s, True))
    if not adj:
        return []
    r = min(adj, key=lambda k: math.hypot(k[0] - root_xy[0], k[1] - root_xy[1]))
    seen, seenseg, out, q = {r}, set(), [], deque([r])
    while q:
        u = q.popleft()
        for v, s, rev in adj[u]:
            if id(s) in seenseg:
                continue
            seenseg.add(id(s))
            out.append(dict(s, x1=s["x2"], y1=s["y2"], x2=s["x1"], y2=s["y1"]) if rev else s)
            if v not in seen:
                seen.add(v); q.append(v)
    return out


def pieces(segs, zmap, step=0.25, dz=0.0):
    P = []
    for s in segs:
        L = math.hypot(s["x2"] - s["x1"], s["y2"] - s["y1"])
        n = max(1, int(math.ceil(L / step)))
        z = zmap[s["layer"]] + dz
        for i in range(n):
            t0, t1 = i / n, (i + 1) / n
            x0, y0 = s["x1"] + t0 * (s["x2"] - s["x1"]), s["y1"] + t0 * (s["y2"] - s["y1"])
            x1, y1 = s["x1"] + t1 * (s["x2"] - s["x1"]), s["y1"] + t1 * (s["y2"] - s["y1"])
            P.append((0.5 * (x0 + x1), 0.5 * (y0 + y1), z, x1 - x0, y1 - y0, s["w"], s["layer"]))
    if not P:
        return dict(n=0)
    a = np.array([p[:6] for p in P], float)
    return dict(n=len(P), pos=a[:, :3], dl=np.c_[a[:, 3:5], np.zeros(len(P))], w=a[:, 5], layer=[p[6] for p in P])


def sub(Pc, mask):
    if Pc["n"] == 0 or not mask.any():
        return dict(n=0)
    return dict(n=int(mask.sum()), pos=Pc["pos"][mask], dl=Pc["dl"][mask], w=Pc["w"][mask], layer=[l for l, m in zip(Pc["layer"], mask) if m])


def concat(*Ps):
    Ps = [p for p in Ps if p["n"]]
    if not Ps:
        return dict(n=0)
    return dict(n=sum(p["n"] for p in Ps), pos=np.vstack([p["pos"] for p in Ps]), dl=np.vstack([p["dl"] for p in Ps]),
                w=np.concatenate([p["w"] for p in Ps]), layer=sum([p["layer"] for p in Ps], []))


def l1_body(geom, zmap, face_dir, h=0.5):
    """L1 winding as one filament between its pad centres, h above the board face it sits on (face_dir -1: body hangs below the B face)."""
    p = [q for q in geom["pads"] if q["ref"] == "L1"]
    if len(p) < 2:
        return dict(n=0)
    zb = zmap["B.Cu"] + face_dir * h
    seg = dict(x1=p[0]["x"], y1=p[0]["y"], x2=p[1]["x"], y2=p[1]["y"], w=1.0, layer="B.Cu")
    # direction: away from the SW pin (VLXSMPS side = pad 1)
    Pc = pieces([seg], {"B.Cu": zb}, 0.25)
    return Pc


def filter_att(f, args):
    """voltage divider R30 (series) into the C13 node: |Zc| / |R + Zc|, Zc = ESR + j(wL - 1/wC) (0201 100 nF: ESR 50 mohm, ESL 0.4 nH [T]); floored at -filter_floor_db."""
    if args.filter_r <= 0:
        return 1.0
    w = 2 * math.pi * f
    zc = complex(0.05, w * 0.4e-9 - 1.0 / (w * args.filter_c_nf * 1e-9))
    a = abs(zc) / abs(args.filter_r + zc)
    return max(a, 10 ** (-args.filter_floor_db / 20))


def T(f, fc):
    return 1.0 / math.sqrt(1.0 + (f / fc) ** 2)


def planes_between(za, zv, planes):
    lo, hi = min(za, zv), max(za, zv)
    return [p for p in planes if lo < p["z"] < hi]


def meff(A, V, plane_own_z, planes, board_of_a, board_of_v, f, rs, floor):
    """sum over pairs of M_eff (nH) at frequency f. A, V pieces in global z."""
    if A["n"] == 0 or V["n"] == 0:
        return 0.0, 0.0
    shift = lambda Pc: dict(Pc, pos=Pc["pos"] - np.array([0, 0, plane_own_z]))
    As, Vs = shift(A), shift(V)
    free = couple.mutual_nH(As, Vs, "free")
    im = couple.mutual_nH(As, Vs, "image")      # zeroed for opposite-side pairs
    fc_own = couple.f_cross(rs)
    za, zv = A["pos"][:, 2], V["pos"][:, 2]
    Tm = np.ones_like(free)
    for i in range(A["n"]):
        for j in range(V["n"]):
            t = T(f, fc_own)          # couple.run_l2 convention: one T_own for every pair (also opposite-side pairs of one board)
            if board_of_a != board_of_v:     # cross-board: add the aggressor board's own planes lying between a and v (victim board's planes: ignored, conservative)
                for p in planes_between(za[i], zv[j], [q for q in planes if q["board"] == board_of_a]):
                    d = max(abs(za[i] - p["z"]), 0.05)
                    t *= T(f, rs / (math.pi * MU0 * d * 1e-3))
            if board_of_a != board_of_v:
                t = max(t, floor)
            Tm[i, j] = t
    Me = im + Tm * (free - im)
    return float(Me.sum()), float(np.abs(Me).sum())


def run(args):
    params = budget.load_yaml(HERE / "params.yaml")
    rs = params["materials"]["rho_cu_ohm_m"] / (15.2e-6)
    res = {}
    # ---- today's board (draft_r2), one board, 4L: same function
    gb = load(Path(args.baseline_board) if args.baseline_board else current("phase2").board)
    zb4 = zstack4(0.0)
    zb4 = {k: v - 0.0 for k, v in zb4.items()}
    planes_b = [dict(z=zb4["In1.Cu"] - 0.0, board="B"), dict(z=zb4["In2.Cu"], board="B")]
    own_b = zb4["In1.Cu"]

    def pads_xy(g, ref, num):
        for p in g["pads"]:
            if p["ref"] == ref and p["num"] == num:
                return (p["x"], p["y"])
        return None

    def net_pieces(g, net, zmap, board, root):
        rxy = root or (0, 0)
        return pieces(orient(g, net, rxy), zmap)

    def build_base(case_l1):
        agg, vic = {}, {}
        for n in ("OUT_A", "OUT_B", "VLXSMPS"):
            agg[n] = net_pieces(gb, n, zb4, "B", pads_xy(gb, *AGG_ROOT[n]))
        if case_l1:
            agg["VLXSMPS"] = concat(agg["VLXSMPS"], l1_body(gb, zb4, -1))
        for _, n in VICTIMS:
            vic[n] = [("B", net_pieces(gb, n, zb4, "B", pads_xy(gb, *AGG_ROOT[n])))]
        return agg, vic, planes_b, {"B": own_b}

    # ---- K4: P upper, M lower, gap g between P's B face and M's F face
    gP = load(Path(args.board_p) if args.board_p else current().board_p)
    gM = load(Path(args.board_m) if args.board_m else current().board)
    flip = not args.legacy_noflip
    if flip:     # P is mirrored across the long axis in the stack (x, y) -> (x, H - y); its file B.Cu is the outer top face
        for g_ in (gP,):
            for q in g_["segments"]:
                q["y1"], q["y2"] = 12.0 - q["y1"], 12.0 - q["y2"]
            for q in g_["vias"] + g_["pads"]:
                q["y"] = 12.0 - q["y"]
    topM = 0.8
    topP = 0.8 + args.gap + 0.8
    zM, zP = zstack(topM), zstack(topP, flip)
    fl_att = lambda f: filter_att(f, args)
    planes_k = [dict(z=zP["In1.Cu"], board="P"), dict(z=zP["In2.Cu"], board="P"), dict(z=zM["In1.Cu"], board="M"), dict(z=zM["In2.Cu"], board="M")]
    own_k = {"P": zP["In1.Cu"], "M": zM["In1.Cu"]}

    def build_k4(case_l1):
        agg, vic = {}, {}
        for n in ("OUT_A", "OUT_B", "VLXSMPS"):
            agg[n] = net_pieces(gP, n, zP, "P", pads_xy(gP, *AGG_ROOT[n]))
        if case_l1:
            agg["VLXSMPS"] = concat(agg["VLXSMPS"], l1_body(gP, zP, +1 if flip else -1))     # L1 on P's file-B face: flipped = outer top, body above it, away from M (legacy: toward M)
        for _, n in VICTIMS:
            vic[n] = []
            if n == "MIC_DATA":    # current runs mic -> MCU: M part first, root U2.1; P part root = connector J21.7
                vic[n].append(("M", net_pieces(gM, n, zM, "M", pads_xy(gM, "U2", "1")), False))
                vic[n].append(("P", net_pieces(gP, n, zP, "P", pads_xy(gP, "J21", "7")), False))
            else:                  # MCU -> mic: P part root at the MCU/R2 pin, M part root at connector J20
                filt = n == "MIC_VDD" and args.filter_r > 0     # PA5 -> BM28 -> R30 on M: everything upstream of the R30/C13 node is filtered
                vic[n].append(("P", net_pieces(gP, n, zP, "P", pads_xy(gP, *AGG_ROOT[n])), filt))
                num = {"MIC_VDD": "6", "MIC_CLK": "3"}[n]
                vic[n].append(("M", net_pieces(gM, n, zM, "M", pads_xy(gM, "J20", num)), filt))
                if filt:   # downstream of R30 (MIC_VDDF, C13 node -> mic pad): NOT attenuated
                    vic[n].append(("M", net_pieces(gM, "MIC_VDDF", zM, "M", pads_xy(gM, "R30", "2")), False))
        return agg, vic, planes_k, own_k

    out = {}
    for label, builder, aboard in (("today_draft_r2", build_base, "B"), ("K4", build_k4, "P")):
        for l1 in (False, True):
            agg, vic, planes, own = builder(l1)
            rows = {}
            for aid, nets, fs in FIELD_AGG:
                for vid, vn in VICTIMS:
                    best = 0.0
                    perf = {}
                    for f in fs:
                        tot = 0.0; tabs = 0.0
                        for ent in vic[vn]:
                            vb, Vp = ent[0], ent[1]
                            att = fl_att(f) if (len(ent) > 2 and ent[2]) else 1.0
                            for na, sgn in nets.items():
                                a_, b_ = meff(agg[na], Vp, own[vb] if label == "K4" else own["B"], planes, aboard, vb if label == "K4" else "B", f, rs, args.floor)
                                tot += sgn * a_ * att; tabs += b_ * att
                        perf[f] = (tot, tabs)
                    rows[(aid, vid)] = perf
            out[(label, l1)] = rows
    return out, gP, gM, gb, (agg, vic)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gap", type=float, default=0.6, help="P inner face to M inner face gap (mm): BM28 mated height 0.6 [T] (place_k4.GAP); c5899c1 used 1.3")
    ap.add_argument("--stack", choices=sorted(STACK_DIEL), default="uniform", help="0.8 mm 6L dielectric split (no JLC 0.8 mm 6L build is published, see STACK_DIEL)")
    ap.add_argument("--legacy-noflip", action="store_true", help="c5899c1 geometry: P NOT mirrored in y, P file F.Cu on top (wrong: place_k4 flips P across the long axis)")
    ap.add_argument("--filter-r", type=float, default=33.0, help="R30 on M, ohm (0 = no filter)")
    ap.add_argument("--filter-c-nf", type=float, default=50.0, help="C13 effective at 3 V, nF (100 nF 0201 X5R, 50 %% derating assumed)")
    ap.add_argument("--filter-floor-db", type=float, default=20.0, help="cap on the filter attenuation, dB (stray coupling past the R/C: pessimistic)")
    ap.add_argument("--floor", type=float, default=0.10, help="cross-board leakage floor on T (A3 of vertical_bplus)")
    ap.add_argument("--board-p", help="override: P board .kicad_pcb (default hw/current.yaml board_p)")
    ap.add_argument("--board-m", help="override: M board .kicad_pcb (default hw/current.yaml board)")
    ap.add_argument("--baseline-board", help="override: single-board baseline (default: the phase2 variant's board in hw/current.yaml)")
    ap.add_argument("--out", default=str(HERE / "out_k4"))
    args = ap.parse_args()
    STACK["mode"] = args.stack
    out, *_ = run(args)
    base = json.load(open(HERE / "out_r2/budget.json"))
    mrows = {(r["aggressor"], r["victim"], r["mechanism"]): r for r in base["l2_rows"] if r.get("kind") in ("tone", "digital")}
    report = {"args": vars(args), "cases": {}}
    if args.filter_r > 0:
        ideal = argparse.Namespace(**{**vars(args), "filter_floor_db": 200.0})
        report["filter"] = {"R_ohm": args.filter_r, "C_eff_nF": args.filter_c_nf, "floor_db": args.filter_floor_db,
                            "att_db_ideal": {f: round(20 * math.log10(filter_att(f, ideal)), 1) for f in (3e6, 6e6, 9e6, 27e6)},
                            "att_db_used": {f: round(20 * math.log10(filter_att(f, args)), 1) for f in (3e6, 6e6, 9e6, 27e6)}}
        print("filter", report["filter"])
    db = lambda a, b: 20 * math.log10(max(abs(a), 1e-6) / max(abs(b), 1e-6))
    for l1 in (False, True):
        t, k = out[("today_draft_r2", l1)], out[("K4", l1)]
        case = {}
        for (aid, vid), perf in t.items():
            per_f = {int(f): dict(M_today=round(mt[0], 4), M_k4=round(k[(aid, vid)][f][0], 4), dB_signed=round(db(k[(aid, vid)][f][0], mt[0]), 1),
                                  abs_today=round(mt[1], 4), abs_k4=round(k[(aid, vid)][f][1], 4), dB_abs=round(db(k[(aid, vid)][f][1], mt[1]), 1)) for f, mt in perf.items()}
            f_dom = 3000000 if aid.startswith("F02") else 2000000
            d = per_f[f_dom]
            ent = dict(f_dominant_hz=f_dom, dB_signed=d["dB_signed"], dB_abs=d["dB_abs"], per_f=per_f)
            for mech_b in [mrows.get((aid, vid, "magnetic"))]:
                if mech_b:
                    m0 = [mech_b.get("margin_nom"), mech_b.get("margin_pes"), mech_b.get("margin_worst")] if mech_b["kind"] == "tone" else [mech_b["margin_nom"]]
                    ent["margin_today"] = [round(x, 1) for x in m0]
                    ent["margin_k4_signed"] = [round(x - d["dB_signed"], 1) for x in m0]
                    ent["margin_k4_absbound"] = [round(x - d["dB_abs"], 1) for x in m0]
            case[f"{aid}|{vid}"] = ent
        report["cases"]["with_L1_body" if l1 else "traces_only"] = case
    Path(args.out).mkdir(parents=True, exist_ok=True)
    (Path(args.out) / "k4_noise.json").write_text(json.dumps(report, indent=1, default=str))
    for c, d in report["cases"].items():
        print("==", c)
        for k_, v in d.items():
            print(k_, {a: b for a, b in v.items() if a != 'per_f'})
            print('     per f:', {f: (x['dB_signed'], x['dB_abs']) for f, x in v['per_f'].items()})


if __name__ == "__main__":
    main()
