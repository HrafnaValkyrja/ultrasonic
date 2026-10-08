#!/usr/bin/env python3
"""K4-HEIGHTS (2026-10-08): real part heights on each face of the K4 board pair vs the shell cavity, worst-case + RSS, and the P-F x M-F gap.

    source tools/env.sh && systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 python3 sim/checks/k4_heights.py [--json]

Physical stack, from the lid down (y outward from the temple; dims_k4 frame; verified in place_k4.py docstring + shell_k4.py):
  lid inner 9.7 | VHB 0.25 | M file-B face (LID face: SW1 in the lid pocket, R30/C21/R20/..., wire pads) | M 0.8 | M file-F face (inner: mic U2, U3, D4/D5, U4, J20)
  | BM28 mated gap 0.6 | P file-F face (inner: Q1, 0201s, J21; notch over the mic) | P 0.8 | P file-B face (OUTER, toward the temple floor: U1, L1, Y1, C4/C7/C14) | floor 4.9.
Heights = package max from the datasheet (named in H_SRC); [T] = inferred, not read. Tolerances: board 0.8 +-0.1 (JLC FAQ, read 2026-10-07/08), VHB 0.25 +-15 % (3M TDS 2024-09),
BM28 mated 0.6 +-0.05 [T], cavity (floor/lid print) +-0.1 [T: docs/build/tolerances.md 'lid +-0.1'], printed lid VHB seat.
"""
import json, math, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "hw/mech"))
import dims_k4 as K
import pcbnew

# footprint-name pattern -> (max height mm, source). Heights are PACKAGE MAX; the KiCad 3D models here are placeholders (0.4 for several) and are not used.
H = [
 ("QFN-48", 0.60, "ST DS13737 UFQFPN48 7x7 A max 0.60 [T: from memory of the package table, datasheet not fetched]"),
 ("Knowles_LGA-5", 1.08, "V9 heights_mm mic_U2 1.08 [V] (docs/system/reg-board.md; Knowles SPH0641LU4H-1 3.5x2.65x0.98 typ)"),
 ("L0806", 1.00, "hw/lib/lcsc 3D name H1.0; V9 heights_mm L1 1.0 [V]"),
 ("Crystal_SMD_2012", 0.60, "C99009 32.768k 2.0x1.2: typical height 0.5-0.6 [T]"),
 ("SW-SMD_4P", 0.65, "KMT022NGJLHS height 0.65 (dims_k4.SW1 h; C&K KMT0 TDS)"),
 ("DSBGA-8", 0.50, "TI BQ25180YBG DSBGA max 0.5 (lib name H0.5) [T]"),
 ("SOT1216", 0.40, "Nexperia DFN1010B-6 / SOT1216 max 0.40 (lib name H0.4; project note 0.37 typ)"),
 ("X2SON-4", 0.40, "TI TPS7A20 DQN X2SON max 0.40 [T]"),
 ("X1SON-2", 0.40, "TI TPD1E10B06 DPY X1SON max 0.40 [T]"),
 ("D_SOD-882", 0.50, "Nexperia SOD882 max 0.50 [T]"),
 ("SOT-553", 0.60, "TI DRL SOT-5X3 max 0.60 [T]"),
 ("BM28B0.6-30D", 0.00, "BM28 pair: handled as the 0.6 mated gap, body inside the gap"),
 ("C_0603", 0.90, "Samsung CL10A106/226 0603 10-22 uF T 0.8 +-0.1 [T: from memory, datasheet not fetched]"),
 ("C_0402", 0.55, "0402 MLCC 1-4.7 uF T 0.5 +0.05 [T]"),
 ("R_0402", 0.40, "0402 thick-film R max 0.40 (Uni-Royal ds V.3 2019 0402: 0.35 +0.05)"),
 ("C_0201", 0.33, "Murata GRM033 0201 T 0.30 +-0.03 = 0.33 (LCSC C76934 datasheet, 2026-10-08)"),
 ("R_0201", 0.26, "Uni-Royal 0201 R T 0.23 +-0.03 = 0.26 (LCSC C473508 datasheet, 2026-10-08)"),
 ("D_SOD-923", 0.50, "[T]"),
 ("WirePad", 0.40, "wire solder dome on the pad [T] (0.21 mm wire + solder)"),
 ("TestPoint", 0.00, "bare pad, no part (a probe wire/solder if used: not modelled)"),
 ("TestDot", 0.00, "bare pad"),
]
# ECR-0022 / K4-HEIGHTS (2026-10-08): per-reference MAX heights read from datasheets / spec sheets (lcsc.com datasheet PDFs fetched 2026-10-08, pdftotext). Overrides the footprint table.
# Samsung catalog (CL05A475MP5NRNC datasheet C23733) lists T per part: 4.7u/10V 0.65, 1u/25V 0.60, 10u/10V 0402 0.70 (spec sheet CL05A106MP5NUNC: 0.50 +-0.20); 2.2u/10V CL05A225KP5NSN not listed: 0.60 [T, KO5 sibling].
REF_H = {
 "C16": (0.39, "Samsung CL03A225MP3CRNC 2.2u 10V X5R 0201 T 0.30 +-0.09 = 0.39 max (Samsung spec sheet LCSC C318539, 2026-10-08); ECR-0022 gap swap, was 4.7u 0402 0.65"),
 "C17": (0.39, "Samsung CL03A105MO3NRNC 1u 16V X5R 0201 T 0.30 +-0.09 = 0.39 max (Samsung spec sheet LCSC C318540, 2026-10-08); ECR-0022 gap swap, was 1u 25V 0402 0.60"), "C18": (0.60, "same as C17"),
 "C21": (0.70, "Samsung CL05A106MP5NUNC 10u 10V 0402 T 0.50 +-0.20 = 0.70 max (Samsung spec sheet C315248, 2026-10-08)"),
 "C15": (0.55, "Murata GRM155R61E475ME15D 4.7u 25V 0402: T code 5 = 0.50 +0.05 [T: Murata catalog row not extractable]"),
 "C9": (0.39, "Samsung CL03A225MP3CRNC 2.2u 10V X5R 0201 0.39 max (C318539, 2026-10-08); ECR-0022 gap swap"), "C8": (0.60, "Samsung CL05A225KP5NSN 2.2u 10V 0402 code 5: 0.60 [T: sibling KO5 row 0.60]; outer face, not in the gap"),
 "U1": (0.60, "ST DS13737 Table 154 UFQFPN48 A max 0.600 (LCSC C5271013 datasheet, read 2026-10-08)"),
 "Y1": (0.60, "Seiko Epson X1A0000610006 2.0x1.2 '0.6 Max.' (LCSC C99009 datasheet, 2026-10-08)"),
 "U4": (0.40, "TI TPS7A20 DQN X2SON package drawing '0.4 MAX' (LCSC C5220164 datasheet, 2026-10-08)"),
 "U6": (0.60, "TI TPD2E2U06 DRL 'SOT - 0.6 mm max height' (LCSC C1972959 datasheet, 2026-10-08)"),
 "D4": (0.50, "Nexperia PMEG3005EL SOD882 outline 0.50/0.46 (LCSC C282565 datasheet, 2026-10-08)"),
 "D5": (0.45, "TI TPD1E10B06 DPY0002A 'X1SON - 0.45 mm max height' (TI datasheet pp.19-29, fetched 2026-10-08)"),
 "U3": (0.50, "TI BQ25180 YBG0008-C01 'DSBGA - 0.5 mm max height' (TI SLUSE99C Jan 2023 p.53, read 2026-10-08)"),
 "L1": (1.00, "Murata DFE201610E-2R2M: 2.0x1.6x1.0 max (name H1.0; V9 [V]); datasheet text has no T row"),
 "R21": (0.40, "Panasonic ERJ2BSFR10X 0402 0.33-ish; kept 0.40 (Uni-Royal 0402 R T 0.35 +-0.05 for siblings)"),
 "R30": (0.40, "Uni-Royal 0402WGF330JTCE T 0.35 +-0.05 = 0.40"), "R20": (0.40, "Uni-Royal 0402WGF0000TCE T 0.35 +-0.05 = 0.40"),
}
def hmax(name, ref=None):
    if ref in REF_H:
        return REF_H[ref]
    for k, h, s in H:
        if name.startswith(k) or k in name:
            return h, s
    raise KeyError(name)

MARGIN_LID = 0.10   # ECR-0022 target: worst-case clearance >= 0.1 mm on every side
TOL = dict(board=0.10, vhb=0.15 * K.VHB_T, bm28=0.05, cavity=0.10)   # per-item tolerance (+-)
def tol_stack(items):
    return sum(items), math.sqrt(sum(i * i for i in items))

def parts(b):
    pcb = pcbnew.LoadBoard(str(ROOT / f"hw/pod/k4/routed_{b}.kicad_pcb"))
    out = []
    for f in pcb.GetFootprints():
        name = str(f.GetFPID().GetLibItemName())
        face = "B" if f.IsFlipped() else "F"
        cy = f.GetCourtyard(pcbnew.B_CrtYd if face == "B" else pcbnew.F_CrtYd)
        bb = cy.BBox() if cy.OutlineCount() else f.GetBoundingBox(False)
        h, src = hmax(name, f.GetReference())
        out.append(dict(ref=f.GetReference(), fp=name, face=face, h=h, src=src,
                        box=tuple(round(pcbnew.ToMM(v), 3) for v in (bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom()))))
    return out

def overlap(a, b):
    return min(a[2], b[2]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[1], b[1])

def main():
    Pp, Mp = parts("P"), parts("M")
    R = {}
    # per face max heights (P file B = outer toward floor; P file F = inner; M file F = inner; M file B = lid face)
    def top(ps, face, skip=()):
        c = [p for p in ps if p["face"] == face and p["ref"] not in skip and p["h"] > 0]
        return sorted(c, key=lambda p: -p["h"])
    R["faces"] = {n: [(p["ref"], p["fp"][:22], p["h"]) for p in top(ps, fc)[:6]] for n, ps, fc in (("P_outer(file B, floor)", Pp, "B"), ("P_inner(file F)", Pp, "F"), ("M_inner(file F)", Mp, "F"), ("M_lid(file B)", Mp, "B"))}
    h_po = top(Pp, "B")[0]
    # 1. floor side: lid -> VHB -> M -> gap -> P -> parts -> floor
    nom = K.Y_LID_IN - K.LID_STANDOFF - K.VHB_T - K.PCB_T - 0.6 - K.PCB_T - h_po["h"] - K.CAV["y0"]
    items = [TOL["vhb"], TOL["board"], TOL["bm28"], TOL["board"], TOL["cavity"], TOL["cavity"]]
    lin, rss = tol_stack(items)
    R["floor_side"] = dict(tallest=h_po["ref"] + " " + h_po["fp"][:20], h=h_po["h"], nominal_clear=round(nom, 3), worst=round(nom - lin, 3), rss3=round(nom - 3 * rss / 3 * 1.0 - 0, 3),
                           rss_1sigma_equiv=round(nom - rss, 3), tolerance_items=items, note="worst = all tolerances adverse (linear); rss = root-sum-square (items treated as +-3 sigma limits -> 3 sigma value = nominal - rss)",
                           lin=round(lin, 3), rss=round(rss, 3))
    R["floor_side"]["rss3"] = round(nom - rss, 3)
    del R["floor_side"]["rss_1sigma_equiv"]
    # 2. lid side: M file-B parts under the lid. VHB gap 0.25 - tol. SW1 sits in the lid pocket (pocket dz/dx) and the mic duct is a bore.
    gap_lid_nom = K.VHB_T + K.LID_STANDOFF
    lin_l, rss_l = tol_stack([TOL["vhb"], TOL["cavity"]])
    lid = []
    for p in top(Mp, "B"):
        if p["ref"] == "SW1":
            continue
        lid.append(dict(ref=p["ref"], fp=p["fp"][:22], h=p["h"], clear_nom=round(gap_lid_nom - p["h"], 3), clear_worst=round(gap_lid_nom - p["h"] - lin_l, 3)))
    R["lid_side_M_fileB"] = dict(vhb=K.VHB_T, tol_lin=round(lin_l, 3), tol_rss=round(rss_l, 3), parts=lid, tallest=lid[0]["ref"] if lid else None,
                                 n_fail_nominal=sum(1 for p in lid if p["clear_nom"] < 0), n_fail_worst=sum(1 for p in lid if p["clear_worst"] < 0), n_below_margin=sum(1 for p in lid if p["clear_worst"] < MARGIN_LID), min_worst=min(p["clear_worst"] for p in lid), n=len(lid),
                                 required_gap_for_all=round(max(p["h"] for p in lid) + MARGIN_LID + lin_l, 3),
                                 note="a flat lid and a 0.25 VHB sheet leave NO room for any M file-B part above ~0.2: 0201s only. SW1 is in its lid pocket (dz 3.1, top y %.1f), the mic port is a bore." % K.POCKET["top"])
    # 3. inner gap 0.6 +-0.05. Align both files on their Edge.Cuts min corner; P is mirrored across the long axis in the stack (place_k4: P (x, y) -> (x, H - y)).
    def outline(b):
        pcb = pcbnew.LoadBoard(str(ROOT / f"hw/pod/k4/routed_{b}.kicad_pcb"))
        ps = pcbnew.SHAPE_POLY_SET()
        pcb.GetBoardPolygonOutlines(ps, False)
        bb = pcb.GetBoardEdgesBoundingBox()
        return ps, (pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetTop()), pcbnew.ToMM(bb.GetRight()), pcbnew.ToMM(bb.GetBottom()))
    psP, bP = outline("P"); psM, bM = outline("M")
    H = bP[3] - bP[1]
    def toS(box, b, flip):
        x0, y0, x1, y1 = box
        x0 -= b[0]; x1 -= b[0]; y0 -= b[1]; y1 -= b[1]
        return (x0, H - y1, x1, H - y0) if flip else (x0, y0, x1, y1)
    def on_P_board(sbox):
        """True if any sample point of the stack-frame box lies on P copper/board (P outline mapped to stack frame)."""
        x0, y0, x1, y1 = sbox
        x0, y0, x1, y1 = x0 + 0.03, y0 + 0.03, x1 - 0.03, y1 - 0.03     # courtyard edge may coincide with the notch edge
        n = 6
        for i in range(n + 1):
            for j in range(n + 1):
                x, y = x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * j / n
                # stack (x, y) -> P file (x + bP0, (H - y) + bP1)
                v = pcbnew.VECTOR2I(pcbnew.FromMM(x + bP[0]), pcbnew.FromMM(H - y + bP[1]))
                if psP.Collide(v, 0):
                    return True
        return False
    def on_M_board(sbox):
        x0, y0, x1, y1 = sbox
        x0, y0, x1, y1 = x0 + 0.03, y0 + 0.03, x1 - 0.03, y1 - 0.03     # courtyard edge may coincide with the notch edge
        n = 6
        for i in range(n + 1):
            for j in range(n + 1):
                v = pcbnew.VECTOR2I(pcbnew.FromMM(x0 + (x1 - x0) * i / n + bM[0]), pcbnew.FromMM(y0 + (y1 - y0) * j / n + bM[1]))
                if psM.Collide(v, 0):
                    return True
        return False
    gap = []
    for pm in top(Mp, "F"):
        sb = toS(pm["box"], bM, False)
        under_P = on_P_board(sb)
        pp_hit = [pp for pp in top(Pp, "F") if not pp["ref"].startswith("J21") and overlap(sb, toS(pp["box"], bP, True))]
        hp = max([pp["h"] for pp in pp_hit], default=0.0)
        gap.append(dict(m=pm["ref"], hm=pm["h"], under_P_board=under_P, p_overlap=[pp["ref"] for pp in pp_hit], hp=hp,
                        clear_nom=round(0.6 - pm["h"] - hp, 3) if under_P else None, clear_worst=round(0.6 - TOL["bm28"] - pm["h"] - hp, 3) if under_P else None))
    for pp in top(Pp, "F"):
        sb = toS(pp["box"], bP, True)
        if pp["ref"].startswith("J21"):
            continue
        over_M = on_M_board(sb)
        mh = max([pm["h"] for pm in top(Mp, "F") if overlap(sb, toS(pm["box"], bM, False))], default=0.0)
        gap.append(dict(p=pp["ref"], hp=pp["h"], over_M_board=over_M, m_overlap_h=mh, clear_nom=round(0.6 - pp["h"] - mh, 3) if over_M else None, clear_worst=round(0.6 - TOL["bm28"] - pp["h"] - mh, 3) if over_M else None))
    chk = [g for g in gap if g["clear_worst"] is not None]
    R["inner_gap"] = dict(gap=0.6, tol=TOL["bm28"], outline_P=[round(v, 3) for v in bP], outline_M=[round(v, 3) for v in bM], rows=sorted(chk, key=lambda g: g["clear_worst"])[:14],
                          n_checked=len(chk), n_below_margin=sum(1 for g in chk if g["clear_worst"] < MARGIN_LID), n_fail_worst=sum(1 for g in chk if g["clear_worst"] < 0), n_fail_nominal=sum(1 for g in chk if g["clear_nom"] < 0),
                          mic_notch=[g for g in gap if g.get("m") == "U2"],
                          note="stack frame: both Edge.Cuts min corners at 0, P mirrored on y. A part under/over the other board's copper has 0.6 - h (- overlapped part h) to the board face; parts over a notch or past the outline have no limit.")
    # 4. whole board in the cavity: z/x extent vs cavity (already K4-SHELLCHK); here only the thickness chain.
    _t = K.Y_LID_IN - K.LID_STANDOFF - K.VHB_T
    chain = dict(M_lid_face=_t, M_inner=_t - K.PCB_T, P_inner=_t - K.PCB_T - 0.6, P_outer=_t - 2 * K.PCB_T - 0.6)
    R["chain_y"] = {k: round(v, 3) for k, v in chain.items()}
    R["chain_y"]["floor"] = K.CAV["y0"]
    R["chain_y"]["dims_k4_STACK_Y0_placeholder"] = round(K.STACK_Y0, 3)
    R["chain_y"]["real_stack_T_without_P_outer_parts"] = round(K.VHB_T * 0 + 2 * K.PCB_T + 0.6, 3)
    # 5. fix sizing: lid-side ledge. delta = how far the stack drops from the lid; lid-face gap = VHB + delta
    need = R["lid_side_M_fileB"]["required_gap_for_all"]
    delta = max(0.0, need - K.VHB_T - K.LID_STANDOFF)
    fl = R["floor_side"]
    R["fix_ledge"] = dict(delta_down=round(delta, 3), lid_gap=round(K.VHB_T + delta, 3), floor_clear_nominal_after=round(fl["nominal_clear"] - delta, 3),
                          floor_clear_rss_after=round(fl["rss3"] - delta, 3), floor_clear_worst_after=round(fl["worst"] - delta, 3),
                          note="stack hangs on a printed lid ledge frame (height delta, ~0.5 wide, on the board perimeter where no part sits) with the VHB on its tip; pod T unchanged. SW1 puck +delta, mic duct gets a printed tube delta long.")
    # 6. feasibility of the "swap parts, no lid change" route at a 0.1 mm worst-case margin target (2026-10-08)
    MARG = 0.10
    lid_allow = K.VHB_T + K.LID_STANDOFF - R["lid_side_M_fileB"]["tol_lin"] - MARG
    gap_allow = 0.6 - TOL["bm28"] - MARG
    lidp = [p for p in top(Mp, "B") if p["ref"] != "SW1"]
    R["swap_route"] = dict(margin_target=MARG, lid_face_max_part_h=round(lid_allow, 3), n_lid_parts_over=sum(1 for p in lidp if p["h"] > lid_allow),
                           gap_max_part_h=round(gap_allow, 3), gap_over=[g.get("m") or g.get("p") for g in chk if g["clear_worst"] < MARG],
                           verdict=("INFEASIBLE: no SMD part is <= %.3f mm, so a flat lid + 0.25 VHB takes zero components on M file B; the gap side needs <= %.2f mm (0201/0402-0.4 only)" % (lid_allow, gap_allow)) if lid_allow < 0.2 else "feasible")
    # 7. ECR-0023 floor post under P on the U1 top: footprint vs the routed P floor-face parts, tolerance chain, fit window, never-negative rule
    px0, px1 = K.POST_X - K.POST_W / 2, K.POST_X + K.POST_W / 2
    pz0, pz1 = 6.0 - K.POST_W / 2, 6.0 + K.POST_W / 2                 # board y = centre line (SW1/BM28/mic 6.0)
    pbox = (px0 + bP[0], H - pz1 + bP[1], px1 + bP[0], H - pz0 + bP[1])       # stack frame -> P file frame (P mirrored on y)
    def inside(a, b, m=0.0):
        return a[0] >= b[0] + m and a[1] >= b[1] + m and a[2] <= b[2] - m and a[3] <= b[3] - m
    u1 = next(p for p in Pp if p["ref"] == "U1")
    # U1 body 7 x 7 centred on its courtyard box (courtyard = body + 0.675 each side, ST DS13737 UFQFPN48 7x7); pin-1 dot / lead pads are at the body edge, keep the post 0.5 inside
    cx, cy = (u1["box"][0] + u1["box"][2]) / 2, (u1["box"][1] + u1["box"][3]) / 2
    ubody = (cx - 3.5, cy - 3.5, cx + 3.5, cy + 3.5)
    others = [p["ref"] for p in Pp if p["face"] == "B" and p["ref"] != "U1" and overlap(pbox, p["box"])]
    items = [TOL["vhb"], TOL["board"], TOL["bm28"], TOL["board"], TOL["cavity"], TOL["cavity"], K.U1_H_TOL]
    lin_p, rss_p = tol_stack(items)
    j21 = next(p for p in Pp if p["ref"] == "J21")
    meas_err = 0.02
    R["floor_post"] = dict(
        post_board_x=[round(px0, 2), round(px1, 2)], post_board_y=[round(pz0, 2), round(pz1, 2)], p_file_box=[round(v, 2) for v in pbox], u1_body_p_file=[round(v, 2) for v in ubody],
        inside_u1_body_with_0p5_edge_margin=inside(pbox, ubody, 0.5), other_p_floor_face_parts_hit=others, in_bm28_x_span=bool(j21["box"][0] <= pbox[0] and pbox[2] <= j21["box"][2]),
        lever_post_to_bm28_centre_mm=round(abs((px0 + px1) / 2 - (j21["box"][0] + j21["box"][2]) / 2 + bP[0] * 0), 2), lever_sw1_to_post_mm=round(abs(5.3 - K.POST_X), 2),
        chain_items=items, chain_lin=round(lin_p, 3), chain_rss=round(rss_p, 3), nominal_gap=K.POST_GAP,
        as_printed_gap_range_lin=[round(K.POST_GAP - lin_p, 3), round(K.POST_GAP + lin_p, 3)], as_printed_gap_range_rss=[round(K.POST_GAP - rss_p, 3), round(K.POST_GAP + rss_p, 3)],
        fixed_height_post_verdict="FAIL as a fixed-height part: as-printed gap spans %.2f..%.2f mm linear (%.2f..%.2f RSS), i.e. up to %.2f mm of PRELOAD on the BM28/ledge VHB; a 0.05 nominal rigid post cannot be both effective and never-negative" % (K.POST_GAP - lin_p, K.POST_GAP + lin_p, K.POST_GAP - rss_p, K.POST_GAP + rss_p, lin_p - K.POST_GAP),
        fit=dict(method="measure with the stack bonded to the lid, before the lid goes on: depth of U1 top below the lid seam plane vs post top below the tub seam plane (caliper depth / micrometer); add PET or Kapton shim (0.025/0.05/0.1) or trim the post top to the fitted gap",
                 target_gap=K.POST_GAP, measurement_error=meas_err, fitted_gap_range=[round(K.POST_GAP - meas_err, 3), round(K.POST_GAP + meas_err, 3)], never_negative=K.POST_GAP - meas_err >= 0,
                 shim_or_trim_lin=[round(-lin_p, 3), round(lin_p, 3)], shim_or_trim_rss=[round(-rss_p, 3), round(rss_p, 3)]),
        load_on_u1_top_MPa=dict(N2=round(2.0 / (K.POST_W ** 2), 3), N10=round(10.0 / (K.POST_W ** 2), 3)),
        note="P floor face under the whole BM28 line (J21 x %.2f-%.2f) is U1; a post on a part-free spot (x < 4 or the y 9-11.5 row) would load the plug as a couple (2 N x ~3-7 mm) and tip P. Post height above the floor as printed %.2f." % (j21["box"][0], j21["box"][2], K.POST_TOP_Y - K.CAV["y0"]))
    R["floor_post"]["pass"] = bool(R["floor_post"]["inside_u1_body_with_0p5_edge_margin"] and not others and R["floor_post"]["in_bm28_x_span"] and R["floor_post"]["fit"]["never_negative"])
    print(json.dumps(R, indent=1, default=str) if "--json" in sys.argv else json.dumps({k: R[k] for k in R if k != "faces"} | {"faces": R["faces"]}, indent=1, default=str))
    (ROOT / "sim/out").mkdir(exist_ok=True)
    (ROOT / "sim/out/k4_heights.json").write_text(json.dumps(R, indent=1, default=str))

main()
