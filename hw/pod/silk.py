"""Silkscreen pass for the pod board: post-route, idempotent, never touches copper.

    source tools/env.sh && python3 hw/pod/silk.py [board.kicad_pcb]

Owner 2026-10-02: "Make sure the silkscreen looks pretty. I'm still toying with the idea of a translucent material for
parts of the case." The top face (lid side) can be seen; the bottom face sits against the cell.
JLC legend rules (jlcpcb.com/capabilities/pcb-capabilities, read 2026-10-02): line >= 0.15 mm, text height >= 1.0 mm,
width:height 1:6, pad-to-silkscreen 0.15 mm. On a 34 x 13 mm board 52 reference designators at 1.0 mm cannot sit
legibly, so they move to the Fab layers (assembly drawing; tools/board_map.py is the owner's map). The silkscreen
keeps only what a person or the assembler needs: pin-1 / polarity marks, the mic-port keep-clear motif, the name.
The board's own project rules are raised to the JLC numbers so DRC enforces them (silk_* / text_* checks).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pcbnew

MM = pcbnew.FromMM
LINE = 0.15                    # JLC minimum legend line
TEXT_H, TEXT_W = 1.0, 0.17     # JLC minimum height; stroke >= h/6
# parts whose silk carries orientation the assembler or a rework needs (pin 1, cathode, port); the rest is clutter
KEEP_MARKS = {"U1", "U2", "U3", "U4", "U6", "D4", "Q1", "Q2"}
KEEP_FRAME = {"U1"}            # if a library pin-1 mark has to go, these keep their corner frame; small parts go to a dot only
# parts whose library pin-1 mark sits within 0.15 mm of a pad (found by this script on Rev F): they get a dot instead.
# Fixed list so a re-run (marks already on Fab) still draws the dots; a new offender stops the script.
DOT_PARTS = {"U1", "U3", "U4", "U6"}
PORT = (3.9, 6.5)              # mic port (U2 NPTH 0.6 mm, through the board); keep-clear motif drawn around it
NAME_ZONE = (23.7, 30.9)       # top face, part-free between SW1's pads and the rear pad field (tented vias only)
PAD_CLR, DOT_CLR = 0.15, 0.2   # JLC pad-to-legend; a pin-1 dot keeps a little more


def seg(board, layer, a, b):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(pcbnew.VECTOR2I(MM(a[0]), MM(a[1])))
    s.SetEnd(pcbnew.VECTOR2I(MM(b[0]), MM(b[1])))
    s.SetLayer(layer)
    s.SetWidth(MM(LINE))
    board.Add(s)


def arc(board, layer, c, r, a0, a1):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_ARC)
    pt = lambda a: pcbnew.VECTOR2I(MM(c[0] + r * math.cos(math.radians(a))), MM(c[1] - r * math.sin(math.radians(a))))  # noqa: E731
    s.SetArcGeometry(pt(a0), pt((a0 + a1) / 2), pt(a1))
    s.SetLayer(layer)
    s.SetWidth(MM(LINE))
    board.Add(s)


def circle(board, layer, c, r):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_CIRCLE)
    s.SetCenter(pcbnew.VECTOR2I(MM(c[0]), MM(c[1])))
    s.SetEnd(pcbnew.VECTOR2I(MM(c[0] + r), MM(c[1])))
    s.SetLayer(layer)
    s.SetWidth(MM(LINE))
    board.Add(s)


def text(board, layer, s, x, y, w=0.72, h=TEXT_H, t=TEXT_W, angle=0.0, just="c"):
    tx = pcbnew.PCB_TEXT(board)
    tx.SetText(s)
    tx.SetLayer(layer)
    tx.SetTextSize(pcbnew.VECTOR2I(MM(w), MM(h)))
    tx.SetTextThickness(MM(t))
    tx.SetTextAngleDegrees(angle)
    tx.SetHorizJustify({"l": pcbnew.GR_TEXT_H_ALIGN_LEFT, "c": pcbnew.GR_TEXT_H_ALIGN_CENTER, "r": pcbnew.GR_TEXT_H_ALIGN_RIGHT}[just])
    tx.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
    if layer == pcbnew.B_SilkS:
        tx.SetMirrored(True)
    board.Add(tx)
    return tx


def side_pads(board, cu):
    return [p for f in board.GetFootprints() for p in f.Pads() if p.IsOnLayer(cu)]


def hits_pad(item, pads, cu, clr=PAD_CLR):
    sh = item.GetEffectiveShape()
    return any(sh.Collide(p.GetEffectiveShape(cu), MM(clr)) for p in pads)


def bodies(board, fab):
    """Package outlines (Fab-layer shapes, union bbox per part) on one side: a dot printed there would sit under a part."""
    out = []
    for f in board.GetFootprints():
        bb = None
        for g in f.GraphicalItems():
            if g.GetLayer() == fab and g.GetClass() == "PCB_SHAPE":
                if bb is None:
                    bb = g.GetBoundingBox()
                else:
                    bb.Merge(g.GetBoundingBox())
        if bb is not None:
            out.append(tuple(pcbnew.ToMM(v) for v in (bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom())))
    return out


def pin1_dot(board, fp, pads, cu, silk):
    """A 0.3 mm dot beside pad 1, pushed outward from the part centre until it clears every pad and stays on the board."""
    p1 = next(p for p in fp.Pads() if p.GetNumber() in ("1", "A1"))
    px, py = pcbnew.ToMM(p1.GetPosition().x), pcbnew.ToMM(p1.GetPosition().y)
    cx, cy = pcbnew.ToMM(fp.GetPosition().x), pcbnew.ToMM(fp.GetPosition().y)
    edge = board.GetBoardEdgesBoundingBox()
    lo_x, lo_y, hi_x, hi_y = (pcbnew.ToMM(v) for v in (edge.GetLeft(), edge.GetTop(), edge.GetRight(), edge.GetBottom()))
    base = math.atan2(py - cy, px - cx)
    fab = pcbnew.B_Fab if fp.IsFlipped() else pcbnew.F_Fab
    under = bodies(board, fab)
    r = 0.15 + 0.1                                                    # dot radius + margin
    for k in [x / 10 for x in range(4, 21)]:
        for da in (0, 25, -25, 50, -50, 75, -75, 100, -100):
            a = base + math.radians(da)
            x, y = px + k * math.cos(a), py + k * math.sin(a)
            if not (lo_x + 0.3 < x < hi_x - 0.3 and lo_y + 0.3 < y < hi_y - 0.3):
                continue
            if any(l - r < x < rt + r and t - r < y < b + r for l, t, rt, b in under):
                continue
            d = pcbnew.PCB_SHAPE(board)
            d.SetShape(pcbnew.SHAPE_T_CIRCLE)
            d.SetCenter(pcbnew.VECTOR2I(MM(x), MM(y)))
            d.SetEnd(pcbnew.VECTOR2I(MM(x + 0.075), MM(y)))
            d.SetFilled(True)
            d.SetWidth(MM(LINE))
            d.SetLayer(silk)
            others = [g for f in board.GetFootprints() for g in f.GraphicalItems() if g.GetLayer() == silk and g.GetClass() == "PCB_SHAPE"]
            others += [g for g in board.GetDrawings() if g.GetLayer() == silk]
            sh = d.GetEffectiveShape()
            if not hits_pad(d, pads, cu, DOT_CLR) and not any(sh.Collide(g.GetEffectiveShape(), MM(0.1)) for g in others):
                board.Add(d)
                return (round(x, 2), round(y, 2))
    raise SystemExit(f"silk: no clear spot for the pin-1 dot of {fp.GetReference()}")


def strip(board):
    """Refs and non-essential footprint silk -> Fab; remove our own earlier board-level silk (idempotent)."""
    for d in list(board.GetDrawings()):
        if d.GetLayer() in (pcbnew.F_SilkS, pcbnew.B_SilkS):
            board.Remove(d)
    for fp in board.GetFootprints():
        fab = pcbnew.B_Fab if fp.IsFlipped() else pcbnew.F_Fab
        silk = pcbnew.B_SilkS if fp.IsFlipped() else pcbnew.F_SilkS
        ref = fp.Reference()
        ref.SetLayer(fab)
        ref.SetTextSize(pcbnew.VECTOR2I(MM(0.5), MM(0.5)))
        ref.SetTextThickness(MM(0.08))
        ref.SetVisible(True)
        ref.SetPosition(fp.GetPosition())
        cu = pcbnew.B_Cu if fp.IsFlipped() else pcbnew.F_Cu
        pads = side_pads(board, cu)
        lost = False
        for it in fp.GraphicalItems():
            if it.GetLayer() != silk:
                continue
            if fp.GetReference() in KEEP_MARKS and it.GetClass() == "PCB_SHAPE":
                if it.GetWidth() < MM(LINE):
                    it.SetWidth(MM(LINE))
                if hits_pad(it, pads, cu):         # library silk that a JLC 0.15 mm legend would print onto copper
                    it.SetLayer(fab)
                    lost = True
            else:
                it.SetLayer(fab)
        if lost and fp.GetReference() not in DOT_PARTS:
            raise SystemExit(f"silk: {fp.GetReference()} library marks hit a pad; add it to DOT_PARTS")
        if fp.GetReference() in DOT_PARTS:
            if fp.GetReference() not in KEEP_FRAME:              # a broken outline reads as damage: dot only
                for it in fp.GraphicalItems():
                    if it.GetLayer() == silk:
                        it.SetLayer(fab)
            print(f"silk: {fp.GetReference()} library marks too close to pads; pin-1 dot at {pin1_dot(board, fp, pads, cu, silk)}")


def art(board):
    F = pcbnew.F_SilkS
    # mic port: keep-clear ring + two sound arcs each side ("(( o ))"); ring clears the 0.6 mm hole by 0.35 mm, the outer
    # right arc stays 0.45 mm off Y1's pads
    cx, cy = PORT
    circle(board, F, PORT, 0.72)
    for r in (1.2, 1.65):
        arc(board, F, PORT, r, 140, 220)
        arc(board, F, PORT, r, -40, 40)
    # name block, condensed caps between the button and the rear pads; a hairline rule, then the revision
    x0, x1 = NAME_ZONE
    xm = (x0 + x1) / 2
    text(board, F, "STEREO", xm, 5.15, w=0.86)
    text(board, F, "ULTRASOUND", xm, 6.75, w=0.62)        # 0.62 wide: KiCad caps the stroke at w/4, JLC wants >= 0.15
    seg(board, F, (x0 + 0.9, 7.95), (x1 - 0.9, 7.95))            # short of SW1 pad 4
    text(board, F, "REV F", xm, 9.15, w=0.66)
    # bottom face: one orientation word for whoever turns the board over (the cell side)
    B = pcbnew.B_SilkS
    text(board, B, "CELL SIDE", 13.0, 12.15, w=0.62)


def project_rules(board_path: Path):
    pro = board_path.with_suffix(".kicad_pro")
    if not pro.exists():
        return
    d = json.loads(pro.read_text())
    r = d["board"]["design_settings"]["rules"]
    r.update(min_silk_clearance=0.15, min_text_height=1.0, min_text_thickness=0.15)
    pro.write_text(json.dumps(d, indent=2) + "\n")


def main():
    path = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent / "draft_r1/pod_r1_routed.kicad_pcb")
    board = pcbnew.LoadBoard(str(path))
    strip(board)
    art(board)
    for cu, silk in ((pcbnew.F_Cu, pcbnew.F_SilkS), (pcbnew.B_Cu, pcbnew.B_SilkS)):
        pads = side_pads(board, cu)
        bad = [d for d in board.GetDrawings() if d.GetLayer() == silk and hits_pad(d, pads, cu)]
        if bad:
            raise SystemExit(f"silk: {len(bad)} art item(s) on {board.GetLayerName(silk)} within {PAD_CLR} mm of a pad")
    board.Save(str(path))
    project_rules(path)
    print(path)


if __name__ == "__main__":
    main()
