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
 ("C_0201", 0.33, "0201 MLCC T 0.3 +0.03 [T]"),
 ("R_0201", 0.28, "0201 R max 0.28 [T]"),
 ("D_SOD-923", 0.50, "[T]"),
 ("WirePad", 0.40, "wire solder dome on the pad [T] (0.21 mm wire + solder)"),
 ("TestPoint", 0.00, "bare pad, no part (a probe wire/solder if used: not modelled)"),
 ("TestDot", 0.00, "bare pad"),
]
def hmax(name):
    for k, h, s in H:
        if name.startswith(k) or k in name:
            return h, s
    raise KeyError(name)

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
        h, src = hmax(name)
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
    nom = K.Y_LID_IN - K.VHB_T - K.PCB_T - 0.6 - K.PCB_T - h_po["h"] - K.CAV["y0"]
    items = [TOL["vhb"], TOL["board"], TOL["bm28"], TOL["board"], TOL["cavity"], TOL["cavity"]]
    lin, rss = tol_stack(items)
    R["floor_side"] = dict(tallest=h_po["ref"] + " " + h_po["fp"][:20], h=h_po["h"], nominal_clear=round(nom, 3), worst=round(nom - lin, 3), rss3=round(nom - 3 * rss / 3 * 1.0 - 0, 3),
                           rss_1sigma_equiv=round(nom - rss, 3), tolerance_items=items, note="worst = all tolerances adverse (linear); rss = root-sum-square (items treated as +-3 sigma limits -> 3 sigma value = nominal - rss)",
                           lin=round(lin, 3), rss=round(rss, 3))
    R["floor_side"]["rss3"] = round(nom - rss, 3)
    del R["floor_side"]["rss_1sigma_equiv"]
    # 2. lid side: M file-B parts under the lid. VHB gap 0.25 - tol. SW1 sits in the lid pocket (pocket dz/dx) and the mic duct is a bore.
    gap_lid_nom = K.VHB_T
    lin_l, rss_l = tol_stack([TOL["vhb"], TOL["cavity"]])
    lid = []
    for p in top(Mp, "B"):
        if p["ref"] == "SW1":
            continue
        lid.append(dict(ref=p["ref"], fp=p["fp"][:22], h=p["h"], clear_nom=round(gap_lid_nom - p["h"], 3), clear_worst=round(gap_lid_nom - p["h"] - lin_l, 3)))
    R["lid_side_M_fileB"] = dict(vhb=K.VHB_T, tol_lin=round(lin_l, 3), tol_rss=round(rss_l, 3), parts=lid, tallest=lid[0]["ref"] if lid else None,
                                 n_fail_nominal=sum(1 for p in lid if p["clear_nom"] < 0), n_fail_worst=sum(1 for p in lid if p["clear_worst"] < 0), n=len(lid),
                                 required_gap_for_all=round(max(p["h"] for p in lid) + 0.05 + lin_l, 3),
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
                          n_checked=len(chk), n_fail_worst=sum(1 for g in chk if g["clear_worst"] < 0), n_fail_nominal=sum(1 for g in chk if g["clear_nom"] < 0),
                          mic_notch=[g for g in gap if g.get("m") == "U2"],
                          note="stack frame: both Edge.Cuts min corners at 0, P mirrored on y. A part under/over the other board's copper has 0.6 - h (- overlapped part h) to the board face; parts over a notch or past the outline have no limit.")
    # 4. whole board in the cavity: z/x extent vs cavity (already K4-SHELLCHK); here only the thickness chain.
    chain = dict(M_lid_face=K.Y_LID_IN - K.VHB_T, M_inner=K.Y_LID_IN - K.VHB_T - K.PCB_T, P_inner=K.Y_LID_IN - K.VHB_T - K.PCB_T - 0.6, P_outer=K.Y_LID_IN - K.VHB_T - 2 * K.PCB_T - 0.6)
    R["chain_y"] = {k: round(v, 3) for k, v in chain.items()}
    R["chain_y"]["floor"] = K.CAV["y0"]
    R["chain_y"]["dims_k4_STACK_Y0_placeholder"] = round(K.STACK_Y0, 3)
    R["chain_y"]["real_stack_T_without_P_outer_parts"] = round(K.VHB_T * 0 + 2 * K.PCB_T + 0.6, 3)
    # 5. fix sizing: lid-side ledge. delta = how far the stack drops from the lid; lid-face gap = VHB + delta
    need = R["lid_side_M_fileB"]["required_gap_for_all"]
    delta = max(0.0, need - K.VHB_T)
    fl = R["floor_side"]
    R["fix_ledge"] = dict(delta_down=round(delta, 3), lid_gap=round(K.VHB_T + delta, 3), floor_clear_nominal_after=round(fl["nominal_clear"] - delta, 3),
                          floor_clear_rss_after=round(fl["rss3"] - delta, 3), floor_clear_worst_after=round(fl["worst"] - delta, 3),
                          note="stack hangs on a printed lid ledge frame (height delta, ~0.5 wide, on the board perimeter where no part sits) with the VHB on its tip; pod T unchanged. SW1 puck +delta, mic duct gets a printed tube delta long.")
    print(json.dumps(R, indent=1, default=str) if "--json" in sys.argv else json.dumps({k: R[k] for k in R if k != "faces"} | {"faces": R["faces"]}, indent=1, default=str))
    (ROOT / "sim/out").mkdir(exist_ok=True)
    (ROOT / "sim/out/k4_heights.json").write_text(json.dumps(R, indent=1, default=str))

main()
