#!/usr/bin/env python3
"""Lower-bound board-area model for Phase-2 miniaturization (PRELIMINARY research, read-only on the design).

    source tools/env.sh && systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 \
        python3 sim/mini/area_model.py [--json sim/mini/out/area_model.json]

What it does (no board/schematic edit; reads the .kicad_pcb files and KiCad stock footprints only):
  1. MEASURE the routed Rev F board (hw/pod/draft_r1/pod_r1_routed.kicad_pcb) and, for calibration, the older dense
     routed board (hw/pod/draft/pod_routed.kicad_pcb, Rev C/D netlist, 20.05 x 11.55, 0 unconnected, commit 6e93246):
     courtyard area per face (raw sum, union, and NORMALISED: every footprint re-courtyarded by one rule so lcsc/pod
     footprints and stock footprints are comparable), per block, utilisation, routing overhead (track channels and vias
     outside courtyards, per copper layer).
  2. PREDICT the minimum outline for scenarios a-f by swapping package courtyards (taken from KiCad 10 stock footprints
     in /usr/share/kicad/footprints, or body + clearance where no stock footprint exists) and dividing by a utilisation U.
     Outline = A_face / H_usable with the height fixed by the cell (12.0 mm board, size study SIZ-01).

Model (per face f):   A_board >= ( C_f / U  +  K_f ) ,  K_f = fixed keep-outs (mic seal ring, locating holes, VHB spots,
                      SW1 back-stop), plus an edge band e * perimeter.   2-face: A = max over faces (as assigned) and the
                      balanced bound (C_F + C_B)/(2U) + mean K.   1-face: A = (C_F + C_B)/U + K_F + K_B.
Limits are printed with the result; they are real (see docs/research/mini/area-model.md).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parents[2]
REVF = ROOT / "hw/pod/draft_r1/pod_r1_routed.kicad_pcb"
OLD = ROOT / "hw/pod/draft/pod_routed.kicad_pcb"
KIFP = Path("/usr/share/kicad/footprints")
MM = pcbnew.FromMM(1)

# ---------------------------------------------------------------- block map: docs/system/integration-map.md §2 (generated, 2026-10-02)
BLOCKS = {
    "MCU": "U1 C1 C2 C3 C4 C5 C6 C7 C10 R1", "CORE_SMPS": "L1 C8 C9", "CLOCK": "Y1 C11 C12", "MIC": "U2 R2 C13",
    "BRIDGE": "Q1 Q2 R3 R4 R5 R6 C14", "SELFTEST": "R21 R22 C22", "ARM_PADS": "J1 J2 J7 J8",
    "DOCK_USB": "J3 J4 J10 J11 J12 D4 D5 U6 R18 R12 R13 C15", "CHARGER": "U3 C16 C21 RT1 J9 R15 R16", "CELL_PADS": "J5",
    "VBAT_SENSE": "R8 R9 C19", "LDO": "U4 C17 C18 R20", "UI": "SW1 R10 R14", "DEBUG": "TP1 TP2 TP3 TP4 TP5 TP6 TP7 TP8 TP9 TP10",
}
REF2BLK = {r: b for b, refs in BLOCKS.items() for r in refs.split()}

# ---------------------------------------------------------------- body sizes (mm, L x W) for footprints whose courtyard is NOT
# drawn to the KiCad convention (lcsc: easyeda2kicad imports; pod: hand-drawn). Source = footprint name / part_heights.yaml rows.
BODY = {
    "DSBGA-8_L1.6-W0.9-R2-C4-P0.40-BL": (1.6, 0.9),        # U3 TI BQ25180 charger, 8-ball 0.4 mm chip-scale
    "X2SON-4_L1.0-W1.0-P0.65-TL-EP": (1.0, 1.0),            # U4 TI TPS7A2030 LDO
    "SOT-553-5_L1.6-W1.2-P0.50-LS1.6-TL-1": (1.6, 1.2),     # U6 TI TPD2E2U06 2-ch ESD
    "X1SON-2_L1.0-W0.6-P0.65-BI-1": (1.0, 0.6),             # D5 TI TPD1E10B06 1-ch ESD
    "SW-SMD_4P-L3.0-W2.6-P1.85-LS3.4": (3.0, 2.6),          # SW1 C&K KMT022 IP68 tact switch
    "FC-135R_L3.2-W1.5": (3.2, 1.5),                        # Y1 Epson FC-135 32.768 kHz crystal
    "L0806": (2.0, 1.6),                                    # L1 Murata DFE201610E 2.2 uH (2016 metric)
    "Knowles_LGA-5_3.5x2.65mm_Port0.6": (3.5, 2.65),        # U2 Knowles/Syntiant SPH0641LU4H-1 PDM mic
    "Nexperia_SOT1216_DFN1010B-6": (1.1, 1.0),              # Q1/Q2 Nexperia PMCXB290UE complementary MOSFET pair
}


def clr_for(body_max: float) -> float:
    """Courtyard clearance by the KiCad stock convention, MEASURED from stock footprints by measure_stock_rule():
    0.15 mm for parts <= ~1.1 mm (0402-class), 0.25 mm otherwise."""
    return 0.15 if body_max <= 1.15 else 0.25


def load_fp(lib: str, name: str):
    return pcbnew.FootprintLoad(str(KIFP / f"{lib}.pretty"), name)


def cy_area(fp, layer=None) -> float:
    layer = layer if layer is not None else (pcbnew.F_CrtYd if fp.GetLayer() == pcbnew.F_Cu else pcbnew.B_CrtYd)
    try:
        return fp.GetCourtyard(layer).Area() / MM / MM
    except Exception:
        return 0.0


def pad_span(fp):
    """Pad extent in the footprint's own (unrotated) frame, mm (x, y)."""
    xs, ys = [], []
    for p in fp.Pads():
        pos = p.GetFPRelativePosition()
        sz = p.GetSize(pcbnew.F_Cu) if hasattr(p, "GetSize") else p.GetSize()
        ang = p.GetFPRelativeOrientation().AsDegrees() % 180
        w, h = sz.x / MM, sz.y / MM
        if abs(ang - 90) < 1:
            w, h = h, w
        xs += [pos.x / MM - w / 2, pos.x / MM + w / 2]
        ys += [pos.y / MM - h / 2, pos.y / MM + h / 2]
    return (max(xs) - min(xs), max(ys) - min(ys)) if xs else (0.0, 0.0)


def norm_cy(fp) -> tuple[float, str]:
    """Normalised courtyard area (mm2) + rule used. Stock-library footprints keep their courtyard (KiCad convention);
    BODY-listed footprints get (max(pad span, body) + 2*clearance) per axis; copper pads get pad + solder margin."""
    name = fp.GetFPID().GetLibItemName().wx_str() if hasattr(fp.GetFPID().GetLibItemName(), "wx_str") else str(fp.GetFPID().GetLibItemName())
    lib = str(fp.GetFPID().GetLibNickname())
    if name in BODY:
        bl, bw = BODY[name]
        px, py = pad_span(fp)
        # pads are in the footprint frame; body (L along x) assumed aligned with the longer pad axis
        if (px >= py) != (bl >= bw):
            bl, bw = bw, bl
        c = clr_for(max(bl, bw))
        return (max(px, bl) + 2 * c) * (max(py, bw) + 2 * c), f"body+pads+{c}"
    return cy_area(fp), f"as drawn ({lib})"


def measure_stock_rule() -> list[dict]:
    """Courtyard clearance actually used by KiCad 10 stock footprints (the rule norm_cy imitates)."""
    out = []
    for lib, name, body in (("Resistor_SMD", "R_0201_0603Metric", (0.6, 0.3)), ("Resistor_SMD", "R_0402_1005Metric", (1.0, 0.5)),
                            ("Capacitor_SMD", "C_0603_1608Metric", (1.6, 0.8)), ("Resistor_SMD", "R_1206_3216Metric", (3.2, 1.6)),
                            ("Package_DFN_QFN", "QFN-48-1EP_7x7mm_P0.5mm_EP5.6x5.6mm", (7.0, 7.0)),
                            ("Package_CSP", "ST_WLCSP-90_4.2x3.95mm_Layout18x10_P0.4mm_Stagger", (4.2, 3.95)),
                            ("Crystal", "Crystal_SMD_2012-2Pin_2.0x1.2mm", (2.0, 1.2))):
        fp = load_fp(lib, name)
        bb = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
        cx, cyy = bb.GetWidth() / MM, bb.GetHeight() / MM
        px, py = pad_span(fp)
        out.append(dict(fp=name, courtyard=(round(cx, 3), round(cyy, 3)), pads=(round(px, 3), round(py, 3)), body=body,
                        clearance_x=round((cx - max(px, body[0])) / 2, 3), clearance_y=round((cyy - max(py, body[1])) / 2, 3),
                        area=round(cx * cyy, 3)))
    return out


# ---------------------------------------------------------------- measurement of a routed board
def board_area(b) -> tuple[float, float, float]:
    ps = pcbnew.SHAPE_POLY_SET()
    b.GetBoardPolygonOutlines(ps, True)
    bb = b.GetBoardEdgesBoundingBox()
    return ps.Area() / MM / MM, bb.GetWidth() / MM, bb.GetHeight() / MM


def measure(path: Path) -> dict:
    b = pcbnew.LoadBoard(str(path))
    area, w, h = board_area(b)
    faces = {"F": dict(raw=0.0, norm=0.0, union=None, n=0, pads=0.0), "B": dict(raw=0.0, norm=0.0, union=None, n=0, pads=0.0)}
    parts, blocks = [], {}
    unions = {"F": pcbnew.SHAPE_POLY_SET(), "B": pcbnew.SHAPE_POLY_SET()}
    for fp in b.GetFootprints():
        f = "F" if fp.GetLayer() == pcbnew.F_Cu else "B"
        ref = fp.GetReference()
        raw = cy_area(fp)
        nrm, rule = norm_cy(fp)
        name = str(fp.GetFPID().GetLibItemName())
        is_pad = name.startswith(("TestPoint", "TestDot", "WirePad"))
        faces[f]["raw"] += raw
        faces[f]["norm"] += nrm
        faces[f]["n"] += 1
        if is_pad:
            faces[f]["pads"] += nrm
        try:
            unions[f].BooleanAdd(fp.GetCourtyard(pcbnew.F_CrtYd if f == "F" else pcbnew.B_CrtYd))
        except Exception:
            pass
        blk = REF2BLK.get(ref, "OTHER")
        blocks.setdefault(blk, {"F": 0.0, "B": 0.0})[f] += nrm
        parts.append(dict(ref=ref, face=f, fp=name, raw=round(raw, 3), norm=round(nrm, 3), rule=rule, block=blk, pad=is_pad))
    for f in faces:
        faces[f]["union"] = unions[f].Area() / MM / MM
    # routing: track channels (width + min space) and via squares (dia + min space), outside courtyards, per layer
    space = 0.09                                   # JLC 4-layer min track/space 0.09/0.09 mm (capabilities page, read 2026-10-02)
    layers = {}
    via_n, via_d, via_h = 0, [], []
    names = {pcbnew.F_Cu: "F.Cu", pcbnew.In1_Cu: "In1.Cu", pcbnew.In2_Cu: "In2.Cu", pcbnew.B_Cu: "B.Cu"}
    widths = {}
    for t in b.GetTracks():
        if t.GetClass() == "PCB_VIA":
            via_n += 1
            via_d.append(t.GetWidth(pcbnew.F_Cu) / MM if hasattr(t, "GetWidth") else 0)
            via_h.append(t.GetDrillValue() / MM)
            continue
        ln = names.get(t.GetLayer(), str(t.GetLayer()))
        L = t.GetLength() / MM
        wd = t.GetWidth() / MM
        widths[round(wd, 3)] = widths.get(round(wd, 3), 0) + L
        # fraction of this track outside the courtyard union of the matching outer face
        f = "F" if t.GetLayer() == pcbnew.F_Cu else ("B" if t.GetLayer() == pcbnew.B_Cu else None)
        out_frac = 1.0
        if f is not None and L > 0:
            s, e = t.GetStart(), t.GetEnd()
            k = max(2, int(L / 0.05))
            inside = 0
            for i in range(k):
                p = pcbnew.VECTOR2I(int(s.x + (e.x - s.x) * (i + 0.5) / k), int(s.y + (e.y - s.y) * (i + 0.5) / k))
                if unions[f].Contains(p):
                    inside += 1
            out_frac = 1 - inside / k
        d = layers.setdefault(ln, dict(len=0.0, chan=0.0, chan_out=0.0))
        d["len"] += L
        d["chan"] += L * (wd + space)
        d["chan_out"] += L * (wd + space) * out_frac
    vd = sum(via_d) / len(via_d) if via_d else 0.0
    vh = sum(via_h) / len(via_h) if via_h else 0.0
    via_sq = via_n * (vd + space) ** 2
    vias_out = {}
    for f in ("F", "B"):
        n_out = sum(1 for t in b.GetTracks() if t.GetClass() == "PCB_VIA" and not unions[f].Contains(t.GetPosition()))
        vias_out[f] = n_out
    zones = {}
    for z in b.Zones():
        for lid in z.GetLayerSet().Seq():
            zones.setdefault(names.get(lid, str(lid)), []).append(z.GetNetname())
    pins = sum(len(fp.Pads()) for fp in b.GetFootprints())
    return dict(file=str(path.relative_to(ROOT)), area=area, w=w, h=h, faces=faces, blocks=blocks, parts=parts, layers=layers,
                via_n=via_n, via_d=vd, via_h=vh, via_area_all_layers=via_sq, vias_outside_cy=vias_out, widths=widths,
                zones=zones, pins=pins, n_fp=len(parts))


# ---------------------------------------------------------------- alternative-package courtyards
def stock(lib, name):
    return cy_area(load_fp(lib, name), pcbnew.F_CrtYd)


def tight(lib, name, body) -> float:
    """Same rule as norm_cy() applied to a KiCad stock footprint: (max(pad span, body) + 2c) per axis."""
    fp = load_fp(lib, name)
    px, py = pad_span(fp)
    bl, bw = body
    if (px >= py) != (bl >= bw):
        bl, bw = bw, bl
    c = clr_for(max(bl, bw))
    return (max(px, bl) + 2 * c) * (max(py, bw) + 2 * c)


def alt_table() -> dict:
    """Courtyard mm2 of the alternative packages. 'stock' = KiCad 10 stock courtyard (its own convention: 1.0 mm for
    BGA/CSP, 0.5 mm for crystals); 'tight' = the one rule used for every Rev F part (pads/body + 0.15/0.25)."""
    t = {
        "R0201": stock("Resistor_SMD", "R_0201_0603Metric"), "C0201": stock("Capacitor_SMD", "C_0201_0603Metric"),
        "R0402": stock("Resistor_SMD", "R_0402_1005Metric"), "C0402": stock("Capacitor_SMD", "C_0402_1005Metric"),
        "C0603": stock("Capacitor_SMD", "C_0603_1608Metric"), "R1206": stock("Resistor_SMD", "R_1206_3216Metric"),
        "XTAL2012_stock": stock("Crystal", "Crystal_SMD_2012-2Pin_2.0x1.2mm"),
        "XTAL2012": tight("Crystal", "Crystal_SMD_2012-2Pin_2.0x1.2mm", (2.0, 1.2)),
        "L_MLZ1608": tight("Inductor_SMD", "L_TDK_MLZ1608", (1.6, 0.8)),
        # same parts on maker-style lands (KiCad stock footprints) instead of the oversized easyeda lands
        "L_DFE2016_land": tight("Inductor_SMD", "L_Murata_DFE201610P", (2.0, 1.6)),
        "XTAL3215_land": tight("Crystal", "Crystal_SMD_3215-2Pin_3.2x1.5mm", (3.2, 1.5)),
        "L_0603gen": stock("Inductor_SMD", "L_0603_1608Metric"),
        "QFN48": stock("Package_DFN_QFN", "QFN-48-1EP_7x7mm_P0.5mm_EP5.6x5.6mm"),
        "WLCSP90_stock": stock("Package_CSP", "ST_WLCSP-90_4.2x3.95mm_Layout18x10_P0.4mm_Stagger"),
        "WLCSP90": tight("Package_CSP", "ST_WLCSP-90_4.2x3.95mm_Layout18x10_P0.4mm_Stagger", (4.2, 3.95)),
        "SOD523": stock("Diode_SMD", "D_SOD-523"), "SOD323": stock("Diode_SMD", "D_SOD-323"),
    }
    # Murata DFE201210U-2R2M=P2 (2.0 x 1.2 x 1.0, C2049745): no stock KiCad footprint; land assumed = the DFE201610P land
    # shortened to the 1.2 body width [estimate]
    fp = load_fp("Inductor_SMD", "L_Murata_DFE201610P"); px, py = pad_span(fp)
    t["L_DFE2012"] = (max(px, 2.0) + 0.5) * (1.2 + 0.5)
    # no stock 2-pad 1610 crystal: Micro Crystal CM9V-T1A body 1.6 x 1.0 (LCSC listing 'SMD1610-2P'); pads assumed within
    # the body length [estimate], clearance 0.25 (body > 1.15)
    t["XTAL1610"] = (1.6 + 0.5) * (1.0 + 0.5)
    return t


# ---------------------------------------------------------------- scenarios
PASSIVE_0402 = lambda p: p["fp"] in ("R_0402_1005Metric", "C_0402_1005Metric")
PASSIVE_0603 = lambda p: p["fp"] == "C_0603_1608Metric"
J_PAD = lambda p: p["ref"].startswith("J")


def scenario_parts(parts: list[dict], alt: dict, steps: set[str]) -> tuple[list[dict], list[str]]:
    """New part list with package swaps applied (areas only) + a swap log."""
    out, log = [], []
    for p in parts:
        q = dict(p)
        a = p["norm"]
        if "0201" in steps and PASSIVE_0402(p) and p["ref"] not in ("C15",):
            a = alt["R0201"] if p["fp"].startswith("R_") else alt["C0201"]
        if "0201" in steps and PASSIVE_0603(p):
            a = alt["C0402"]                       # 10 uF / 22 uF 0603 -> 0402 (no 0201 at these values; notes §alt)
        if "lands" in steps:
            if p["ref"] == "Y1":
                a = alt["XTAL3215_land"]
            if p["ref"] == "L1":
                a = alt["L_DFE2016_land"]
        if "small_xlr" in steps:
            if p["ref"] == "Y1":
                a = alt["XTAL1610"] if "xtal1610" in steps else alt["XTAL2012"]
            if p["ref"] == "L1":
                a = alt["L_DFE2012"]
            if p["ref"] == "R21":
                a = alt["R0402"]
            if p["ref"] == "D4" and "sod523" in steps:
                a = alt["SOD523"]
        if "wlcsp" in steps and p["ref"] == "U1":
            a = alt["WLCSP90_stock"] if "wlcsp_stock" in steps else alt["WLCSP90"]
        if "pads_off" in steps and J_PAD(p):
            a = 0.0
        if "pads_trim" in steps and J_PAD(p):
            a = 1.27 * 1.27 * (2 if p["fp"].startswith("WirePad") else 1)   # 1.27 mm-pitch cells (SIZ-10); J4 = 2 cells
        if "padsB" in steps and (p["ref"].startswith("J") or p["ref"] in ("TP1", "TP2", "TP3", "TP4", "TP5", "TP6")):
            q["face"] = "B"                       # ASM-09 / sim-study IB-07: every post-bond hand pad on B
        if abs(a - p["norm"]) > 1e-6:
            log.append(f"{p['ref']}:{p['norm']:.2f}->{a:.2f}")
        q["norm"] = a
        out.append(q)
    return out, log


def keepouts(pkgB: bool) -> dict:
    """Fixed per-face keep-outs (mm2) that hold no part. [estimate] unless a source is named."""
    k = {"F": 0.0, "B": 0.0, "items": []}
    a = math.pi * 1.6 ** 2          # mic seal: sub-audio-in issue 2 'keep vias out of r1.6 around the port' (F, the lid side)
    k["F"] += a
    k["items"].append(("mic seal ring D3.2 on F (sub-audio-in #2, physical #1)", "F", round(a, 2)))
    if pkgB:
        a = 2 * math.pi * 0.8 ** 2  # SIZ-02: 2 NPTH D0.9 (sim-study §5 lid row) + 0.35 ring -> D1.6, both faces
        k["F"] += a; k["B"] += a
        k["items"].append(("2 locating NPTH D0.9 + ring -> D1.6, both faces (SIZ-02)", "F+B", round(a, 2)))
        a = 4 * 1.5 * 1.5           # 4 VHB spots on F: size given nowhere [estimate 1.5 x 1.5]
        k["F"] += a
        k["items"].append(("4 VHB spots 1.5x1.5 on F [estimate, size TBD]", "F", a))
        a = 3.0 * 2.6               # SW1 back-stop zone on B (sim-study §4.4: keep B parts out from under SW1)
        k["B"] += a
        k["items"].append(("SW1 back-stop zone 3.0x2.6 on B (sim-study §4.4)", "B", a))
    return k


def placeable(L: float, H: float, e_long: float, e_short: float) -> float:
    return (H - 2 * e_long) * (L - 2 * e_short)


def solve_L(c: float, k: float, U: float, H: float, e_long: float, e_short: float) -> float:
    """Smallest board length L with  U * (placeable - k) >= c."""
    return (c / U + k) / (H - 2 * e_long) + 2 * e_short


def route_bound(D0: float, A0: float, U_out: float, eta: float, n_inner_sig: int) -> float:
    """Global routing-capacity lower bound [estimate]: channel demand D(A) = D0 * sqrt(A/A0) (wirelength ~ linear size,
    same netlist) must fit in eta * (free outer area on 2 faces + inner signal layers). Solves for A."""
    cap_per_A = eta * (2 * (1 - U_out) + n_inner_sig)
    # D0 * sqrt(A/A0) <= cap_per_A * A  ->  sqrt(A) >= D0 / (cap_per_A * sqrt(A0))
    return (D0 / (cap_per_A * math.sqrt(A0))) ** 2


# Mic-noise separation floor [estimate]: switching parts (bridge Q1/Q2 + R21, L1) >= 10 mm from the mic port (sim-study IB-10;
# reg-board 'rear half, away from U2'; sub-output: bridge ~12 mm today, LN-M01 pass 23.1 dB). Port x >= 3.1 (centre line, O16(5)).
# Straight line: 3.1 + 10 + bridge strip ~2.5 + edge 0.3 ~= 16 mm. Diagonal (bridge at the long edge, dy ~5): 3.1 + 8.7 + 2.5 + 0.3
# ~= 14.6 mm. Use (14.6, 16.0); valid until the layout-noise sim (docs/sim/, sim/noise) is re-run at a shorter separation.
GEOM_FLOOR = (14.6, 16.0)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=str(ROOT / "sim/mini/out/area_model.json"))
    ap.add_argument("--H", type=float, default=12.0, help="board height, mm (cell-limited, size study SIZ-01 / sim-study B)")
    ap.add_argument("--edge", type=float, default=0.3, help="courtyard-to-edge band, mm (JLC copper-to-routed-edge >= 0.2 + 0.1)")
    ap.add_argument("--clamp", type=float, default=0.6, help="clamp band on the long edges when the board is NOT lid-hung, mm")
    args = ap.parse_args(argv)

    rule = measure_stock_rule()
    revf, old = measure(REVF), measure(OLD)
    alt = alt_table()

    def summ(m, e_long):
        F, B = m["faces"]["F"], m["faces"]["B"]
        P = placeable(m["w"], m["h"], e_long, args.edge)
        return dict(file=m["file"], outline=f"{m['w']:.2f} x {m['h']:.2f}", area=round(m["area"], 1), placeable=round(P, 1),
                    edge_long=e_long, n_fp=m["n_fp"], pins=m["pins"],
                    F_raw=round(F["raw"], 1), B_raw=round(B["raw"], 1), F_norm=round(F["norm"], 1), B_norm=round(B["norm"], 1),
                    F_union=round(F["union"], 1), B_union=round(B["union"], 1),
                    U_F=round(F["norm"] / P, 3), U_B=round(B["norm"] / P, 3), U_mean=round((F["norm"] + B["norm"]) / (2 * P), 3),
                    U_mean_board=round((F["norm"] + B["norm"]) / (2 * m["area"]), 3),
                    pads_norm=round(F["pads"] + B["pads"], 1),
                    via_n=m["via_n"], via=f"{m['via_d']:.2f}/{m['via_h']:.2f}", vias_outside_cy=m["vias_outside_cy"],
                    via_sq_per_layer_mm2=round(m["via_area_all_layers"], 1),
                    layers={k: {kk: round(vv, 1) for kk, vv in v.items()} for k, v in sorted(m["layers"].items())},
                    track_widths={str(k): round(v, 1) for k, v in sorted(m["widths"].items())}, zones=m["zones"])

    S_revf, S_old = summ(revf, args.clamp), summ(old, args.edge)   # Rev F has 0.6 mm clamp bands; the old board did not
    for S, m in ((S_revf, revf), (S_old, old)):
        ro = {}
        for f, ln in (("F", "F.Cu"), ("B", "B.Cu")):
            chan = m["layers"].get(ln, {}).get("chan_out", 0.0)
            vsq = m["vias_outside_cy"][f] * (m["via_d"] + 0.09) ** 2
            ro[f] = dict(chan_out=round(chan, 1), via_out=round(vsq, 1), frac_of_board=round((chan + vsq) / m["area"], 3),
                         free_frac=round(1 - m["faces"][f]["union"] / m["area"], 3))
        S["route_overhead"] = ro
        S["chan_total_mm2"] = round(sum(v["chan"] for v in m["layers"].values()), 1)
        n_sig = 1 if "In1.Cu" in m["zones"] else 2
        S["eta_used"] = round(S["chan_total_mm2"] / (m["area"] * (2 * (1 - S["U_mean"]) + n_sig)), 3)
        S["inner_use_frac"] = {ln: round(m["layers"].get(ln, {}).get("chan", 0.0) / m["area"], 3) for ln in ("In1.Cu", "In2.Cu")}

    blocks = {b: {f: round(v, 2) for f, v in d.items()} for b, d in sorted(revf["blocks"].items(), key=lambda kv: -sum(kv[1].values()))}

    # ---------------- scenarios: Rev F logic, package/mechanics changes only. U_central: the figure the notes use.
    SC = [
        ("a",   "Rev F parts as-is, today's mechanics (0.6 mm clamp bands, no lid-hung keep-outs)", set(), False, 0.50),
        ("a+B", "Rev F as-is + Package-B mechanics (lid-hung: no clamp bands; pins/VHB/back-stop keep-outs; hand pads to B)", {"padsB"}, True, 0.50),
        ("a0",  "a+B + maker lands for Y1 (FC-135) and L1 (DFE201610E): same parts", {"padsB", "lands"}, True, 0.50),
        ("b",   "a0 + 0201 passives (0402 -> 0201 except C15 25 V; 0603 bulk caps -> 0402)", {"padsB", "lands", "0201"}, True, 0.50),
        ("c",   "b + crystal FC-12M 2012, L1 DFE201210U 2012, R21 1206 -> 0402", {"padsB", "0201", "small_xlr"}, True, 0.50),
        ("c+",  "c + crystal 1610 (CM9V-T1A) + D4 SOD-323 -> SOD-523", {"padsB", "0201", "small_xlr", "xtal1610", "sod523"}, True, 0.50),
        ("d",   "c + U1 UFQFPN48 -> WLCSP90 (tight courtyard) + via-in-pad, 0.2/0.1 vias", {"padsB", "0201", "small_xlr", "wlcsp"}, True, 0.60),
        ("d_ks", "d with KiCad's stock WLCSP courtyard (1.0 mm BGA clearance) = conservative", {"padsB", "0201", "small_xlr", "wlcsp", "wlcsp_stock"}, True, 0.60),
        ("e",   "d + J wire pads off the board faces (castellated rear edge or flex tail)", {"padsB", "0201", "small_xlr", "wlcsp", "pads_off"}, True, 0.60),
        ("e'",  "d + J pads kept, trimmed to 1.27 mm-pitch cells (SIZ-10)", {"padsB", "0201", "small_xlr", "wlcsp", "pads_trim"}, True, 0.60),
        ("e0",  "a0 + J pads off-board only (no package change)", {"padsB", "lands", "pads_off"}, True, 0.50),
        ("c_e'", "c + J pads trimmed (no WLCSP, through vias)", {"padsB", "0201", "small_xlr", "pads_trim"}, True, 0.50),
    ]
    U_SET = [0.43, 0.50, 0.55, 0.60, 0.65]
    D0, A0 = S_revf["chan_total_mm2"], revf["area"]
    out_sc = []
    for sid, desc, steps, pkgB, Uc in SC:
        parts, log = scenario_parts(revf["parts"], alt, steps)
        cF = sum(p["norm"] for p in parts if p["face"] == "F")
        cB = sum(p["norm"] for p in parts if p["face"] == "B")
        K = keepouts(pkgB)
        e_long = args.edge if pkgB else args.clamp
        row = dict(id=sid, what=desc, U_central=Uc, C_F=round(cF, 1), C_B=round(cB, 1), C_tot=round(cF + cB, 1),
                   K_F=round(K["F"], 1), K_B=round(K["B"], 1), keepouts=K["items"], e_long=e_long, swaps=log, by_U={})
        for U in U_SET:
            LF = solve_L(cF, K["F"], U, args.H, e_long, args.edge)
            LB = solve_L(cB, K["B"], U, args.H, e_long, args.edge)
            Lbal = solve_L((cF + cB) / 2, (K["F"] + K["B"]) / 2, U, args.H, e_long, args.edge)
            # one face: all parts on B except SW1 (and its R10) which must face the lid; F keeps the mic seal ring only
            sw = sum(p["norm"] for p in parts if p["ref"] in ("SW1",))
            # (F then holds SW1 alone, in a lid pocket; F keep-outs no longer cost part area, B keep-outs do)
            L1 = solve_L(cF + cB - sw, K["B"], U, args.H, e_long, args.edge)
            row["by_U"][str(U)] = dict(
                two_face_as_assigned=dict(L=round(max(LF, LB), 1), area=round(max(LF, LB) * args.H), limiting="F" if LF >= LB else "B"),
                two_face_balanced=dict(L=round(Lbal, 1), area=round(Lbal * args.H)),
                one_face=dict(L=round(L1, 1), area=round(L1 * args.H)))
        row["route_bound_mm2"] = round(route_bound(D0, A0, Uc, 0.30, 1), 0)
        v = row["by_U"][str(Uc)]
        # channel efficiency the predicted 2-face board would NEED: D(A) / (A * (2(1-U) + 1 inner signal layer))
        A2 = max(v["two_face_as_assigned"]["L"], GEOM_FLOOR[0]) * args.H
        row["eta_required_2f"] = round(D0 * math.sqrt(A2 / A0) / (A2 * (2 * (1 - Uc) + 1)), 3)
        Lr = row["route_bound_mm2"] / args.H
        row["predicted"] = dict(U=Uc,
            two_face=dict(L=round(max(v["two_face_as_assigned"]["L"], Lr, GEOM_FLOOR[0]), 1), L_area=v["two_face_as_assigned"]["L"],
                          L_balanced=v["two_face_balanced"]["L"],
                          binding=("area" if v["two_face_as_assigned"]["L"] >= max(Lr, GEOM_FLOOR[0]) else
                                   ("mic-noise floor" if GEOM_FLOOR[0] >= Lr else "routing"))),
            one_face=dict(L=round(max(v["one_face"]["L"], Lr, GEOM_FLOOR[0]), 1), L_area=v["one_face"]["L"]))
        out_sc.append(row)

    res = dict(read="2026-10-02", H=args.H, edge=args.edge, clamp=args.clamp, stock_courtyard_rule=rule,
               alt_courtyards={k: round(v, 3) for k, v in alt.items()},
               revF=S_revf, old_dense=S_old, blocks_revF_norm=blocks,
               parts_revF=sorted(revf["parts"], key=lambda p: -p["norm"]), scenarios=out_sc)
    Path(args.json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.json).write_text(json.dumps(res, indent=1))

    print("stock courtyard rule (bbox incl. ~0.05 line width):", [(r["fp"], r["clearance_x"], r["clearance_y"]) for r in rule])
    for k in ("revF", "old_dense"):
        S = res[k]
        print(f"\n[{k}] {S['file']}  {S['outline']} = {S['area']} mm2 (placeable {S['placeable']}, long-edge band {S['edge_long']}), {S['n_fp']} fp, {S['pins']} pads")
        print(f"  courtyards raw F {S['F_raw']} B {S['B_raw']} | norm F {S['F_norm']} B {S['B_norm']} | union F {S['F_union']} B {S['B_union']}")
        print(f"  U (norm / placeable): F {S['U_F']} B {S['U_B']} mean {S['U_mean']} (norm/board {S['U_mean_board']}); pads {S['pads_norm']} mm2")
        print(f"  vias {S['via_n']} ({S['via']}), outside courtyards F {S['vias_outside_cy']['F']} B {S['vias_outside_cy']['B']}, via squares/layer {S['via_sq_per_layer_mm2']}")
        print(f"  route overhead {S['route_overhead']}  channels total {S['chan_total_mm2']}  inner {S['inner_use_frac']}  eta used {S['eta_used']}")
        print(f"  layers {S['layers']}  widths {S['track_widths']}  zones {S['zones']}")
    print("\nblocks (Rev F, normalised mm2):", blocks)
    print("\nalt courtyards:", res["alt_courtyards"])
    print(f"\nscenarios (H {args.H}, edge {args.edge}; L in mm at board height {args.H}):")
    for r in out_sc:
        print(f" {r['id']:5s} C_F {r['C_F']:6.1f} C_B {r['C_B']:5.1f} tot {r['C_tot']:6.1f} K {r['K_F']:4.1f}/{r['K_B']:4.1f} Uc {r['U_central']} route>= {r['route_bound_mm2']}")
        for u, v in r["by_U"].items():
            a2, b2, o1 = v["two_face_as_assigned"], v["two_face_balanced"], v["one_face"]
            print(f"        U{u}: 2f {a2['L']:5.1f} ({a2['area']:4d}, {a2['limiting']})  bal {b2['L']:5.1f} ({b2['area']:4d})  1f {o1['L']:5.1f} ({o1['area']:4d})")
    print("\npredicted (U_central; L = max(area, routing, mic-noise floor 14.6)):")
    for r in out_sc:
        pr = r["predicted"]
        print(f" {r['id']:5s} U {pr['U']}: 2-face {pr['two_face']['L']:5.1f} x {args.H:.0f} (area {pr['two_face']['L_area']}, bal {pr['two_face']['L_balanced']}, binding {pr['two_face']['binding']})"
              f" | 1-face {pr['one_face']['L']:5.1f} x {args.H:.0f} | eta needed {r['eta_required_2f']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
