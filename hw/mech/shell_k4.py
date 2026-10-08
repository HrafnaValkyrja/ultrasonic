"""K4 end-to-end pod shell (owner O33; numbers in hw/mech/dims_k4.py). Parametric tub + flat lid, placeholder board stack.

    systemd-run --user --scope --quiet -p MemoryMax=4G -p MemorySwapMax=0 python3 hw/mech/shell_k4.py     # -> hw/mech/out/k4s/*.stl, parts.json, checks.json
    K4_RELIEF=lift python3 hw/mech/shell_k4.py                                                             # -> out/k4s_lift (cell to x 65.8, H +0.45)

Reused from shell_r2: seam tongue/groove, rebate, heel (arm mount: socket, keel, conductor channel), dovetail rail, strut relief,
VHB-hung board (board F face on the lid, mic duct = lid bore + VHB hole + board hole), KMT022 pocket + puck + skin, K1_DUCT=rec numbers.
Dock option A (k4-dock.yaml option_A_design): 4 belly windows over the M pad tab + 2 bossed magnet pockets (dock_add/dock_cut). Dropped: the YZT0675 bay (6.86 > T 6.4), belly-step witness groove (no step: the rebate is continuous).

Hand assembly (order; every fixing is glue/VHB, nothing screwed except the M1.4 set screw in the heel):
 1 tub on the bench, inner face down.  2 arm anchor + set screw in the heel socket (heel.py), arm wires out of the channel (x 64, z -8.6).
 3 VHB 0.25 on the cavity floor, cell pressed on (x 31..62); cell leads fold forward to the 0.8 gap.
 4 stack on its VHB to the lid inner face (F face up there: mic duct registered by the gauge pin as in r2), SW1 in the pocket, puck in the bore.
 5 solder 2 cell leads + 4 arm wires to the stack rear pads (x 34.4..), wires run in the 0.9 channel under the cell and the 0.8 gap, then stow.
 6 lid with the hanging stack down onto the tongue (cell and board share the cavity), bond the seam; skin over the button last.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from build123d import Box, Cylinder, Pos, Rot, RegularPolygon, export_stl, extrude, fillet

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "sim" / "checks"))
import dims_k4 as K  # noqa: E402
from dims_k4 import *  # noqa: E402,F401,F403
import blade  # noqa: E402
import heel  # noqa: E402

OUT = HERE / "out" / ("k4s" if RELIEF == "len" else "k4s_lift")


def box(x0, x1, y0, y1, z0, z1):
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(x1 - x0, y1 - y0, z1 - z0)


def ycyl(x, z, d, y0, y1):
    return Pos(x, (y0 + y1) / 2, z) * Rot(90, 0, 0) * Cylinder(d / 2, y1 - y0)


def outer_body():
    return fillet(box(X0, X1, Y_IN, Y_OUT, Z0, Z1).edges(), 1.0)


def cavity():
    c = box(CAV["x0"], CAV["x1"], CAV["y0"], CAV["y1"] + 0.01, CAV["z0"], CAV["z1"])
    top = CAV["y1"] + 0.01
    es = [e for e in c.edges() if e.bounding_box().min.Y < top - 1e-3]      # leave the open top edges sharp
    return fillet(es, 0.5)         # keeps the 1.0 outer round from thinning the wall at the corners (0.6 -> 0.64 min)


def tongue(g=0.0):
    t, k, y0, y1 = TONGUE_W + g, CORNER_KEEP, Y_SPLIT - 0.01, Y_SPLIT + TONGUE_H + g
    c = CAV
    runs = [(X0 + k, X1 - k, c["z1"] - g, c["z1"] + t), (X0 + k, X1 - k, c["z0"] - t, c["z0"] + g),
            (c["x1"] - g, c["x1"] + t, Z0 + k, Z1 - k), (c["x0"] - t, c["x0"] + g, Z0 + k, Z1 - k)]
    s = None
    for xa, xb, za, zb in runs:
        r = box(xa, xb, y0, y1, za, zb)
        s = r if s is None else s + r
    return s


def _over_cell_top():
    """top (z1) edge strip over the cell: the cell hangs 0.1 under the cavity top, so no inward ridge there; the rebate is left out there instead."""
    return box(CELL_X0 - 0.3, CELL_X1 + 0.3, Y_SPLIT - REBATE_H - 0.2, Y_SPLIT + 0.2, CAV["z1"] - 0.25, Z1 + 1)


def seam_rebate():
    band = box(X0 - 1, X1 + 1, Y_SPLIT - REBATE_H, Y_SPLIT + 0.01, Z0 - 1, Z1 + 1)
    band = band - box(X0 + REBATE_D, X1 - REBATE_D, Y_SPLIT - REBATE_H - 0.1, Y_SPLIT + 0.1, Z0 + REBATE_D, Z1 - REBATE_D)
    return band - _over_cell_top()


def seam_ridge():
    """K4-SHELLCHK: the rebate (0.1 x 0.4) on a 0.6 wall left 0.5 < 0.6 min wall. Inward ridge of the same size on the cavity wall opposite the rebate:
    wall 0.6 + 0.1 = 0.7 -> residual 0.6, outside size unchanged (0 L/H/T cost). Omitted where the cell hangs under the cavity top."""
    band = box(CAV["x0"] - 0.01, CAV["x1"] + 0.01, Y_SPLIT - REBATE_H, Y_SPLIT, CAV["z0"] - 0.01, CAV["z1"] + 0.01)
    band = band - box(CAV["x0"] + REBATE_D, CAV["x1"] - REBATE_D, Y_SPLIT - REBATE_H - 0.1, Y_SPLIT + 0.1, CAV["z0"] + REBATE_D, CAV["z1"] - REBATE_D)
    return band - _over_cell_top()


def tub_add():
    """heel keel + rail (+ strut relief fill) on the outer body, before the cavity is cut."""
    return blade.rail(zc=(Z0 + Z1) / 2) + heel.heel_add()


def dock_add():
    """inward bosses around the two magnet pockets (belly wall 0.6 is too thin for a 1.0 disc + 0.2 skin)."""
    z0 = CAV["z0"] - 0.05
    bs = [Pos(x, DOCK_YC, (z0 + BOSS_TOP) / 2) * Cylinder(BOSS_D / 2, BOSS_TOP - z0) for x in (MAG_X_FRONT, MAG_X_REAR)]
    return (bs[0] + bs[1]) & box(X0 - 1, X1 + 1, Y_IN - 1, Y_SPLIT, Z0 - 1, Z1 + 1)     # clipped at the seam: with the pads at M's mid-plane the boss would reach into the lid


def dock_cut():
    """2 magnet pockets (insert from the cavity side before the cell goes in, 0.2 skin outside) + 4 belly windows for the pads."""
    zp = Z0 + MAG_SKIN
    cut = None
    for x in (MAG_X_FRONT, MAG_X_REAR):
        c = Pos(x, DOCK_YC, (zp + BOSS_TOP + 0.01) / 2) * Cylinder(POCKET_D / 2, BOSS_TOP + 0.01 - zp)
        cut = c if cut is None else cut + c
    for x in PAD_X:
        cut = cut + box(x - WIN_W / 2, x + WIN_W / 2, DOCK_YC - WIN_H / 2, DOCK_YC + WIN_H / 2, Z0 - 0.1, CAV["z0"] + 0.02)
    return cut


def post():
    """ECR-0023: floor post under P (bears on the U1 top, gap filled by a bonded epoxy dab at assembly (add.2)); printed short by POST_PRINT_GAP."""
    return box(STACK_X0 + POST_X - POST_W / 2, STACK_X0 + POST_X + POST_W / 2, CAV["y0"] - 0.01, POST_TOP_Y, SW[1] - POST_W / 2, SW[1] + POST_W / 2)


def tub(with_post=True):
    t = outer_body() & box(X0 - 1, X1 + 1, Y_IN - 2, Y_SPLIT, Z0 - 1, Z1 + 1)
    t = t + tub_add()
    t = t - cavity()
    t = t + (seam_ridge() & outer_body())
    cz, y0 = CAV["z0"], CAV["y0"]
    t = t + blade.prism_yz([(y0, cz), (y0 + 1.4, cz), (y0, cz + 1.4)], 62.0, CAV["x1"])    # relief fill: legs 1.4 keep >= 0.6 normal wall (r2: 1.0 at y0 5.1)
    t = t - blade.prism_yz([(3.9, -12.5), (3.9, -3.65 - 3.9), (-3.65 + 12.5, -12.5)], 62.0, 68.5)
    t = t - heel.heel_cut()        # after the relief fill: the conductor channel / socket must stay open through it
    t = t + (tongue() & outer_body())
    if with_post:
        t = t + post()
    t = t + (dock_add() & outer_body())
    t = t - dock_cut()
    return t - seam_rebate()


def _m_lid_face_rects(expand=0.1):
    """M lid-face (file B) courtyards from routed_M.kicad_pcb as stack-frame rects (x from the outline corner, z from the top edge) grown by `expand`, plus the outline size."""
    import pcbnew
    b = pcbnew.LoadBoard(str(Path(__file__).resolve().parents[2] / "hw/pod/k4/routed_M.kicad_pcb"))
    bb = b.GetBoardEdgesBoundingBox(); x0, y0 = pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetTop())
    out = []
    for f in b.GetFootprints():
        if not f.IsFlipped():          # file F = inner face; the lid face is file B
            continue
        cy = f.GetCourtyard(pcbnew.B_CrtYd); r = cy.BBox() if cy.OutlineCount() else f.GetBoundingBox(False)
        out.append((f.GetReference(), pcbnew.ToMM(r.GetLeft()) - x0 - expand, pcbnew.ToMM(r.GetTop()) - y0 - expand,
                    pcbnew.ToMM(r.GetRight()) - x0 + expand, pcbnew.ToMM(r.GetBottom()) - y0 + expand))
    return out, (pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight()))


def ledge_ring(y0, y1):
    """ECR-0022: perimeter ledge frame (LEDGE_W wide, LEDGE_INSET in from the board edge) + a tube round the mic port bore, between y0 and y1.
    Notched (0.1 clear) wherever an M lid-face courtyard (wire pads, TP, NTC) sits on the band; the notched frame is what is printed and where the VHB goes."""
    xa, xb, za, zb = STACK_X0 + LEDGE_INSET, STACK_X1 - LEDGE_INSET, STACK_Z0 + LEDGE_INSET, STACK_Z1 - LEDGE_INSET
    ring = box(xa, xb, y0, y1, za, zb) - box(xa + LEDGE_W, xb - LEDGE_W, y0 - 1, y1 + 1, za + LEDGE_W, zb - LEDGE_W)
    rects, (Lb, Hb) = _m_lid_face_rects()
    for ref, rx0, rz0, rx1, rz1 in rects:
        if ref in ("U2", "SW1"):
            continue
        ring = ring - box(STACK_X0 + rx0, STACK_X0 + rx1, y0 - 1, y1 + 1, STACK_Z0 + rz0, STACK_Z0 + rz1)
    ring = ring + ycyl(MIC[0], MIC[1], DUCT_TUBE_D, y0, y1)
    return ring - ycyl(MIC[0], MIC[1], DUCT_D, y0 - 1, y1 + 1)


def ledge_check():
    """Notched ledge vs the M lid-face courtyards: which parts force a notch, how much of the band centre line is kept, shortest kept run, duct-tube clash."""
    rects, (Lb, Hb) = _m_lid_face_rects()
    xa, xb, za, zb = LEDGE_INSET + LEDGE_W / 2, Lb - LEDGE_INSET - LEDGE_W / 2, LEDGE_INSET + LEDGE_W / 2, Hb - LEDGE_INSET - LEDGE_W / 2
    pts, n = [], 0
    step = 0.05
    path = [(xa + i * step, za) for i in range(int((xb - xa) / step) + 1)] + [(xb, za + i * step) for i in range(1, int((zb - za) / step) + 1)] \
        + [(xb - i * step, zb) for i in range(1, int((xb - xa) / step) + 1)] + [(xa, zb - i * step) for i in range(1, int((zb - za) / step))]
    notch_parts = set()
    keep = []
    for (x, z) in path:
        hit = [r[0] for r in rects if r[0] not in ("U2", "SW1") and r[1] - LEDGE_W / 2 < x < r[3] + LEDGE_W / 2 and r[2] - LEDGE_W / 2 < z < r[4] + LEDGE_W / 2]
        keep.append(not hit); notch_parts.update(hit)
    runs, cur = [], 0
    for k in keep + [False]:
        if k:
            cur += 1
        elif cur:
            runs.append(cur * step); cur = 0
    mic = (MIC[0] - STACK_X0, MIC[1] - ZC + Hb / 2)
    tube_hits = []
    for ref, x0, z0, x1, z1 in rects:
        cx, cz = max(x0, min(mic[0], x1)), max(z0, min(mic[1], z1))
        if ref != "U2" and math.hypot(cx - mic[0], cz - mic[1]) < DUCT_TUBE_D / 2 + 0.1:
            tube_hits.append(ref)
    L_total = len(path) * step
    return dict(band=dict(inset=LEDGE_INSET, width=LEDGE_W, height=LID_STANDOFF), notched_for=sorted(notch_parts), kept_fraction=round(sum(keep) / len(keep), 3),
                kept_length_mm=round(sum(keep) * step, 1), band_area_kept_mm2=round(sum(keep) * step * LEDGE_W, 1), n_runs=len(runs), shortest_run_mm=round(min(runs), 2) if runs else 0,
                longest_run_mm=round(max(runs), 2) if runs else 0, duct_tube_clash=tube_hits, outline=[round(Lb, 3), round(Hb, 3)],
                note="band centre line sampled every 0.05 mm; a sample is dropped if a lid-face courtyard (+0.1 clear, + half band) covers it; VHB only on the kept ledge tip")


def lid():
    l = outer_body() & box(X0 - 1, X1 + 1, Y_SPLIT, Y_OUT + 1, Z0 - 1, Z1 + 1)
    l = l - tongue(GROOVE_CL)
    l = l + (ledge_ring(Y_LID_IN - LID_STANDOFF, Y_LID_IN + 0.01) & outer_body())
    l = l - ycyl(MIC[0], MIC[1], DUCT_D, Y_LID_IN - 0.01, Y_OUT + 0.01)
    l = l - Pos(MIC[0], Y_OUT - HEX_DEPTH / 2, MIC[1]) * Rot(90, 0, 0) * extrude(RegularPolygon(HEX_R, 6), amount=HEX_DEPTH / 2, both=True)
    l = l - box(SW[0] - POCKET["dx"] / 2, SW[0] + POCKET["dx"] / 2, Y_LID_IN - 0.01, POCKET["top"], SW[1] - POCKET["dz"] / 2, SW[1] + POCKET["dz"] / 2)
    l = l - ycyl(SW[0], SW[1], BORE_D, POCKET["top"] - 0.01, Y_OUT + 0.01)
    l = l - ycyl(SW[0], SW[1], SKIN_D, SKIN_FLOOR, Y_OUT + 0.01)
    return l


def puck():
    y_sw = Y_F + SW1["h"]
    return ycyl(SW[0], SW[1], NUB_D, y_sw, y_sw + NUB_H + 0.01) + ycyl(SW[0], SW[1], PUCK_D, y_sw + NUB_H, y_sw + PUCK_L)


def cell_edges(b):
    ce = CELL_EDGE_CHAMFER
    for z, sg in ((CELL_Z1, -1), (CELL_Z0, 1)):
        b = b - blade.prism_yz([(CELL_Y0 - 0.01, z + sg * ce), (CELL_Y0 - 0.01, z - sg * 0.01), (CELL_Y0 + ce, z - sg * 0.01)], CELL_X0 - 0.01, CELL_X1 + 0.01)
    return b


def placeholders():
    top = box(STACK_X0, STACK_X1, Y_B, Y_F, STACK_Z0, STACK_Z1) - ycyl(MIC[0], MIC[1], MIC_HOLE_D, Y_B - 0.1, Y_F + 0.1)
    body = box(STACK_X0 + 0.3, STACK_X1 - 0.3, STACK_Y0, Y_B - 1.08, STACK_Z0 + 0.3, STACK_Z1 - 0.3)   # lower board + parts + power board: PLACEHOLDER (V9 B+)
    vhb = ledge_ring(Y_LID_IN - LID_STANDOFF - VHB_T, Y_LID_IN - LID_STANDOFF)           # VHB only on the ledge tip (ECR-0022)
    vhb = vhb - ycyl(MIC[0], MIC[1], DUCT_D, Y_LID_IN - 1, Y_LID_IN + 1)
    vhb = vhb - box(SW[0] - POCKET["dx"] / 2, SW[0] + POCKET["dx"] / 2, Y_LID_IN - 1, Y_LID_IN + 1, SW[1] - POCKET["dz"] / 2, SW[1] + POCKET["dz"] / 2)
    cell = box(CELL_X0, CELL_X1, CELL_Y0, CELL_Y1, CELL_Z0, CELL_Z1)
    # CELL_EDGE_CHAMFER (both y0 long edges; the bottom one clears the strut-relief fill, 0.005 mm3): the cell's tape-side/top long edge sits in the cavity's R0.5 fillet (0.145 mm3 clash at a sharp corner); a 0.15 edge break clears it
    # (corner 0.57 from the fillet centre vs R0.5). Wall untouched (>= 0.6). Open: confirm the ICP401230 case edge radius >= 0.15 on the first cell (assembly check).
    cell = cell_edges(cell)
    ctape = box(CELL_X0, CELL_X1, CAV["y0"], CELL_Y0, CELL_Z0 + 0.4, CELL_Z1 - 0.4)   # tape narrower than the cell: clears the cavity corner round
    u2 = box(U2["c"][0] - U2["dx"] / 2, U2["c"][0] + U2["dx"] / 2, Y_B - U2["h"], Y_B, U2["c"][1] - U2["dz"] / 2, U2["c"][1] + U2["dz"] / 2)
    sw1 = box(SW[0] - SW1["body"][0] / 2, SW[0] + SW1["body"][0] / 2, Y_F, Y_F + SW1["h"], SW[1] - SW1["body"][1] / 2, SW[1] + SW1["body"][1] / 2)
    skin = ycyl(SW[0], SW[1], SKIN_D - 0.1, SKIN_FLOOR, Y_OUT)
    # wire paths (rendered as 0.35 square runs): cell leads front end -> stack rear pads; arm bundle stack rear -> heel channel mouth under the cell
    wr = K.wire_routes()

    def run(nets, r):
        acc = None
        for n in nets:
            for p0, p1 in zip(wr[n][:-1], wr[n][1:]):
                if p0 != p1:
                    c = heel._cyl(p0, p1, r)
                    acc = c if acc is None else acc + c
        return acc
    bat = run(("BAT+", "GND", "NTC"), WIRE_OD / 2)
    arm = run(ARM_NETS, WIRE_OD / 2)
    if DOCK == "front" or TAB_X[1] <= STACK_X1:
        tab = box(TAB_X[0], TAB_X[1], DOCK_YC - 0.4, DOCK_YC + 0.4, TAB_Z_BOTTOM, STACK_Z0 + 0.3)           # M board tab carrying the pads (placeholder)
    else:                                                                                                  # strip continues under the cell, in the wire channel
        tab = box(TAB_X[0], STACK_X1, DOCK_YC - 0.4, DOCK_YC + 0.4, TAB_Z_BOTTOM, STACK_Z0 + 0.3) + box(STACK_X1 - 0.01, TAB_X[1], DOCK_YC - 0.4, DOCK_YC + 0.4, TAB_Z_BOTTOM, TAB_STRIP_TOP)
    mags = [Pos(x, DOCK_YC, Z0 + MAG_SKIN + MAG_T / 2) * Cylinder(MAG_D / 2, MAG_T) for x in (MAG_X_FRONT, MAG_X_REAR)]
    mag = mags[0] + mags[1]
    return dict(m_tab=tab, dock_mags=mag, cell=cell, ctape=ctape, pcb_top=top, stack_body=body, vhb=vhb, u2_mic=u2, sw1=sw1, skin=skin, bat_wires=bat, arm_wires=arm)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    t, l, pk, ph = tub(), lid(), puck(), placeholders()
    t_np = tub(False)      # clash/corridor checks run without the post: it bears on U1 inside the crude stack_body placeholder by design (checked in c['post'])
    c = {}
    for k in ("cell", "ctape", "pcb_top", "stack_body", "vhb", "u2_mic", "sw1", "bat_wires", "arm_wires", "dock_mags"):
        for n, p in (("tub", t_np), ("lid", l)):
            c[f"clash/{n}/{k}"] = round((p & ph[k]).volume, 4)
    c["clash/tub/lid"] = round((t & l).volume, 4)
    c["ledge"] = ledge_check()
    c["post"] = dict(x=[round(STACK_X0 + POST_X - POST_W / 2, 2), round(STACK_X0 + POST_X + POST_W / 2, 2)], z=[round(SW[1] - POST_W / 2, 2), round(SW[1] + POST_W / 2, 2)], height_above_floor_printed=round(POST_TOP_Y - CAV["y0"], 3),
                     u1_top_y=round(U1_TOP_Y, 3), fitted_top_y=round(U1_TOP_Y - POST_GAP, 3), print_air_gap=POST_PRINT_GAP, fit_gap=POST_GAP, chain_lin=round(POST_CHAIN_LIN, 3),
                     shim_add_or_trim=[-round(POST_CHAIN_LIN, 3), round(POST_CHAIN_LIN, 3)],
                     overlap_stack_placeholder_by_design=round((post() & ph["stack_body"]).volume, 4), overlap_pcb_top=round((post() & ph["pcb_top"]).volume, 4), post_mm3=round(post().volume, 3),
                     note="printed at the nominal fit gap; fit range +-chain_lin (linear worst case): + = add PET/Kapton shim on the post top, - = trim the top. overlap with the crude stack_body placeholder is the U1 volume the post bears on (checked against the routed P in k4_heights post section)")
    c["clash/cell/m_tab"] = round((ph["cell"] & ph["m_tab"]).volume, 4)
    c["clash/m_tab/stack_body_overlap_is_intended"] = round((ph["m_tab"] & ph["stack_body"]).volume, 4)
    c["clash/tub/m_tab"] = round((t & ph["m_tab"]).volume, 4)
    c["clash/cell/dock_boss"] = round((ph["cell"] & dock_add()).volume, 4)
    c["clash/stack_body/dock_boss"] = round((ph["stack_body"] & dock_add()).volume, 4)
    c["clash/arm_wires/dock_boss"] = round((ph["arm_wires"] & dock_add()).volume, 4)
    c["clash/ctape/dock_boss"] = round((ph["ctape"] & dock_add()).volume, 4)
    c["clash/cell/stack"] = round((ph["cell"] & ph["stack_body"]).volume, 4)
    c["clash/puck/lid"] = round((pk & l).volume, 4)
    c["clash/puck/sw1"] = round((pk & ph["sw1"]).volume, 4)
    # drop-in corridors: cell falls along -y into the tub, lid + hanging stack come down along -y
    c["corridor/cell_drop_in"] = round((t & cell_edges(box(CELL_X0, CELL_X1, CELL_Y0, Y_SPLIT + 1, CELL_Z0, CELL_Z1))).volume, 4)
    c["corridor/stack_drop_in"] = round((t_np & box(STACK_X0, STACK_X1, STACK_Y0, Y_SPLIT + 3, STACK_Z0, STACK_Z1)).volume, 4)
    # wall minimum: grow the cavity by w and see how much sticks out of the outer body (+ keel/rail) below the seam; 0 = every wall >= w
    outer_all = (outer_body() + tub_add()) & box(X0 - 1, X1 + 1, Y_IN - 3, Y_SPLIT, Z0 - 3, Z1 + 3)
    walls = {}
    from build123d import offset
    for w in (0.55, 0.6):
        try:
            g = offset(cavity(), amount=w - 0.005) & box(X0 - 3, X1 + 3, Y_IN - 3, Y_SPLIT - 0.02, Z0 - 3, Z1 + 3)
            walls[f"cavity+{w}_outside_body_mm3"] = round((g - outer_all).volume, 3)
        except Exception as e:      # noqa: BLE001
            walls[f"cavity+{w}"] = f"offset failed: {e}"
    c['wires'] = dict(length_mm=K.wire_lengths(), lane_z=round(LANE_Z, 2), lane_y=LANE_Y0, stack_L=STACK_L, stack_L_src=STACK_L_SRC)
    walls.update(nominal=WALL, lid=LID_T, floor=WALL, rebate_residual=round(WALL + REBATE_D - REBATE_D, 2), lid_over_groove=round(LID_T - (TONGUE_H + GROOVE_CL), 2),
                 puck_guide=round(SKIN_FLOOR - POCKET["top"], 2), min_resin=0.6, src="frame.RESIN min_wall 0.6")
    c["walls"] = walls
    bb = ph["cell"].bounding_box()
    c["cell"] = dict(x=[round(bb.min.X, 2), round(bb.max.X, 2)], lid_clear=round(Y_LID_IN - CELL_Y1, 3), under_channel=round(CH_UNDER, 2),
                     rear_dead_zone=round(CAV["x1"] - CELL_X1, 2), relief=RELIEF)
    c["stack"] = dict(x=[round(STACK_X0, 2), round(STACK_X1, 2)], T=STACK_T, floor_clear=round(STACK_Y0 - CAV["y0"], 2), front_gap=X_STOP_GAP,
                      side_gap_z=round((CAV["z1"] - CAV["z0"] - STACK_H) / 2, 2), mic=MIC, button=SW)
    c["button"] = dict(puck_L=round(PUCK_L, 3), puck_feasible=PUCK_L > NUB_H + 0.02, guide_bore=round(SKIN_FLOOR - POCKET["top"], 3), gap_nominal=PRE_GAP)
    mt = {i: round(((t & box(x - WIN_W / 2 + 0.01, x + WIN_W / 2 - 0.01, DOCK_YC - WIN_H / 2 + 0.01, DOCK_YC + WIN_H / 2 - 0.01, Z0 - 1, 0)).volume), 4) for i, x in enumerate(PAD_X)}
    dk = dict(DOCK_FIT)
    dk.update(pad_x=[round(x, 2) for x in PAD_X], mag_x=[MAG_X_FRONT, round(MAG_X_REAR, 2)], head_mag_pitch_T=HEAD_MAG_PITCH, yc=DOCK_YC, window_open_resin_mm3=mt,
              pocket_edge_front=round(MAG_X_FRONT - POCKET_D / 2, 2), belly_round_start=round(X0 + 1.0, 2), pocket_edge_to_pod_end=round(MAG_X_FRONT - POCKET_D / 2 - X0, 2),
              tab_x=[round(v, 2) for v in TAB_X], tab_to_cell=round(CELL_X0 - TAB_X[1], 2), tab_to_front_boss=round(PAD_X[0] - WIN_W / 2 - 0.3 - (MAG_X_FRONT + BOSS_D / 2), 2),
              tab_to_rear_boss=round((MAG_X_REAR - BOSS_D / 2) - TAB_X[1], 2), tab_past_stack=round(TAB_X[1] - STACK_X1, 2), skin=MAG_SKIN, boss_to_cell=round(CELL_Z0 - BOSS_TOP, 3), boss_to_Mtab=round(STACK_Z0 - BOSS_TOP, 3),
              pad_recess=round(TAB_Z_BOTTOM - Z0, 2), cell_shift=DOCK_SHIFT, mode=DOCK, tab_strip_to_cell_z=round(CELL_Z0 - TAB_STRIP_TOP, 2), tab_under_cell_x=round(max(0.0, TAB_X[1] - CELL_X0), 2))
    c["dock"] = dk
    ev = outer_body().volume
    c["envelope"] = dict(T=round(Y_OUT - Y_IN, 2), L=round(L, 2), H=round(H, 2), env_mm3=round(ev, 1), x=[round(X0, 2), X1], z=[Z0, round(Z1, 2)])
    c["volumes"] = dict(tub=round(t.volume, 1), lid=round(l.volume, 1), puck=round(pk.volume, 3))
    c["printable"] = {n: dict(solids=len(s.solids()), valid=bool(s.is_valid)) for n, s in (("tub", t), ("lid", l), ("puck", pk))}
    c["mass"] = mass(t, l, pk, ph)
    print(json.dumps(c, indent=1))
    (OUT / "checks.json").write_text(json.dumps(c, indent=1))
    mats = dict(cell="cell", ctape="silicone", pcb_top="pcb", stack_body="chips", vhb="silicone", u2_mic="chips", sw1="metal", skin="silicone",
                bat_wires="metal", arm_wires="metal", m_tab="pcb", dock_mags="metal")
    parts = {"tub": (t, "body"), "lid": (l, "armour"), "puck": (pk, "metal"), **{k: (v, mats[k]) for k, v in ph.items()}}
    info = {}
    for k, (s, m) in parts.items():
        export_stl(s, str(OUT / f"{k}.stl"), tolerance=0.01, angular_tolerance=0.1)
        info[k] = {"mat": m, "explode": [0, 0, 0]}
    (OUT / "parts.json").write_text(json.dumps(info, indent=1))


def mass(t, l, pk, ph):
    """Pod body roll-up with sim/checks/pod_mass.py's densities and its [A] ranges (cell 3.5 g datasheet is the only sourced heavy item)."""
    import pod_mass as M
    r = M.rng
    area = STACK_L * STACK_H
    items = {
        "tub (resin, incl. heel + rail)": r(t.volume, M.RESIN), "lid (resin)": r(l.volume, M.RESIN), "puck": r(pk.volume, M.RESIN),
        "skin (silicone)": r(ph["skin"].volume, M.SILICONE), "VHB stack-to-lid": r(ph["vhb"].volume, M.VHB), "VHB cell tape": r(ph["ctape"].volume, M.VHB),
        "cell ICP401230UPR": (3.5, 3.5),
        "2 bare boards FR-4 11x12x0.8 [A]": r(2 * area * PCB_T, M.FR4),
        "copper, 2 boards x 4 layers [A]": (2 * area * 0.1 * 0.5 * 8.96 / 1000, 2 * area * 0.1 * 0.8 * 8.96 / 1000),
        "components + BM28 B2B (r2 74-part range) [A]": (0.20, 0.40),
        "wires + solder + potting [A]": (0.10, 0.27),
    }
    lo, hi = sum(a for a, _ in items.values()), sum(b for _, b in items.values())
    return dict(items_g={k: [round(a, 3), round(b, 3)] for k, (a, b) in items.items()}, pod_body_g=[round(lo, 2), round(hi, 2)],
                excludes="adapter clip, arm, pad, exciter, NiTi (as pod_mass pod_body_only); dock = 2 N52 2.5x1 discs (0.04 g) + M tab, not in the roll-up", target_g=8.0)


if __name__ == "__main__":
    main()
