"""Close short unrouted gaps the autorouter left: straight segments (and a via where the two ends sit on different faces),
only where they clear every other net's copper. Each accepted edit is kept only if DRC errors do not rise.

    source tools/env.sh && systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 \
        python3 hw/pod/close_gaps.py BOARD.kicad_pcb [--max-len 4.0]

Lead-only tool (edits the board in place; run on a committed board so git can undo). Phase 2, 2026-10-03.
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

import pcbnew

mm, MM = pcbnew.FromMM, pcbnew.ToMM
TRACK_W, VIA_D, VIA_DRILL, CLR = 0.1, 0.35, 0.15, 0.11
OUTER = (pcbnew.F_Cu, pcbnew.B_Cu)


def drc(path):
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as t:
        out = t.name
    subprocess.run(["kicad-cli", "pcb", "drc", "--format", "json", "--severity-error", "--output", out, str(path)],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    d = json.loads(Path(out).read_text())
    return len(d.get("violations", [])), d.get("unconnected_items", [])


def anchors(item):
    """(x, y, layers) points where a new segment may attach to this item."""
    c = item.GetClass()
    if c == "PCB_TRACK":
        return [(MM(p.x), MM(p.y), {item.GetLayer()}) for p in (item.GetStart(), item.GetEnd())]
    if c == "PCB_VIA":
        p = item.GetPosition()
        return [(MM(p.x), MM(p.y), set(OUTER))]
    if c == "PAD":
        p = item.GetPosition()
        return [(MM(p.x), MM(p.y), {l for l in OUTER if item.IsOnLayer(l)})]
    return []


def clear(board, net, layer, shape, extra=CLR):
    for t in board.GetTracks():
        if t.GetNetCode() == net or not t.IsOnLayer(layer):
            continue
        if t.GetEffectiveShape(layer).Collide(shape, mm(extra)):
            return False
    for f in board.GetFootprints():
        for p in f.Pads():
            if p.GetNetCode() == net or not p.IsOnLayer(layer):
                continue
            if p.GetEffectiveShape(layer).Collide(shape, mm(extra)):
                return False
    return True


def try_segment(board, net, layer, a, b):
    seg = pcbnew.SHAPE_SEGMENT(pcbnew.VECTOR2I(mm(a[0]), mm(a[1])), pcbnew.VECTOR2I(mm(b[0]), mm(b[1])), mm(TRACK_W))
    if not clear(board, net, layer, seg):
        return None
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(pcbnew.VECTOR2I(mm(a[0]), mm(a[1])))
    t.SetEnd(pcbnew.VECTOR2I(mm(b[0]), mm(b[1])))
    t.SetWidth(mm(TRACK_W))
    t.SetLayer(layer)
    t.SetNetCode(net)
    board.Add(t)
    return [t]


def try_via(board, net, at):
    circ = pcbnew.SHAPE_CIRCLE(pcbnew.VECTOR2I(mm(at[0]), mm(at[1])), mm(VIA_D / 2))
    if not all(clear(board, net, l, circ) for l in OUTER):
        return None
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pcbnew.VECTOR2I(mm(at[0]), mm(at[1])))
    v.SetWidth(mm(VIA_D))
    v.SetDrill(mm(VIA_DRILL))
    v.SetNetCode(net)
    board.Add(v)
    return [v]


def find_items(board, desc_pos):
    """The board items behind one DRC unconnected entry (matched by position and kind)."""
    out = []
    for desc, x, y in desc_pos:
        best, bd = None, 1e9
        cands = list(board.GetTracks()) + [p for f in board.GetFootprints() for p in f.Pads()]
        for it in cands:
            kind = "Via" if it.GetClass() == "PCB_VIA" else "Track" if it.GetClass() == "PCB_TRACK" else "Pad"
            if not desc.startswith(kind):
                continue
            pts = anchors(it)
            if it.GetClass() == "PCB_TRACK":   # DRC reports a track by a point on it
                d = it.GetEffectiveShape().Collide(pcbnew.VECTOR2I(mm(x), mm(y)), mm(0.01))
                dist = 0 if d else 1e9
            else:
                dist = math.hypot(MM(it.GetPosition().x) - x, MM(it.GetPosition().y) - y)
            if dist < bd:
                best, bd = it, dist
        out.append(best)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("board")
    ap.add_argument("--max-len", type=float, default=4.0)
    a = ap.parse_args()
    path = Path(a.board)
    base_err, unconn = drc(path)
    print(f"start: {base_err} DRC errors, {len(unconn)} unconnected")
    fixed = 0
    for u in unconn:
        board = pcbnew.LoadBoard(str(path))
        items = find_items(board, [(i["description"], i["pos"]["x"], i["pos"]["y"]) for i in u["items"]])
        if None in items or len(items) != 2:
            print("  skip (items not found):", [i["description"] for i in u["items"]])
            continue
        net = items[0].GetNetCode()
        best = None
        for pa, pb in itertools.product(anchors(items[0]), anchors(items[1])):
            d = math.hypot(pa[0] - pb[0], pa[1] - pb[1])
            if d > a.max_len:
                continue
            common = pa[2] & pb[2]
            plan = [("seg", l) for l in common] or [("via_a", None), ("via_b", None)]
            for kind, l in plan:
                if best is None or d < best[0]:
                    best = (d, kind, l, pa, pb)
        if best is None:
            print("  skip (no anchors within max-len):", [i["description"] for i in u["items"]])
            continue
        d, kind, layer, pa, pb = best
        added = None
        if kind == "seg":
            added = try_segment(board, net, layer, pa[:2], pb[:2])
        else:   # different faces: a via at one end, then a segment on the other end's face
            for at, other in ((pa, pb), (pb, pa)):
                v = try_via(board, net, at[:2])
                if v:
                    l = next(iter(other[2]))
                    s = try_segment(board, net, l, at[:2], other[:2]) if math.hypot(at[0] - other[0], at[1] - other[1]) > 1e-3 else []
                    if s is not None:
                        added = v + s
                        break
                    board.Remove(v[0])
        if not added:
            print(f"  no clear path ({d:.2f} mm):", [i["description"] for i in u["items"]])
            continue
        tmp = path.with_suffix(".try.kicad_pcb")
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())
        pcbnew.SaveBoard(str(tmp), board)
        err, un2 = drc(tmp)
        if err <= base_err and len(un2) < len(unconn) - fixed:
            tmp.replace(path)
            fixed += 1
            print(f"  closed ({kind}, {d:.2f} mm):", [i["description"] for i in u["items"]])
        else:
            tmp.unlink()
            print(f"  rejected by DRC ({err} errors, {len(un2)} unconnected):", [i["description"] for i in u["items"]])
    err, un = drc(path)
    print(f"end: {err} DRC errors, {len(un)} unconnected")


if __name__ == "__main__":
    main()
