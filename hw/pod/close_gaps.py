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


def net_islands(board, net):
    """Copper items of one net grouped into connected islands (shapes touching on a shared layer; vias join all)."""
    items = [t for t in board.GetTracks() if t.GetNetCode() == net]
    items += [pd for f in board.GetFootprints() for pd in f.Pads() if pd.GetNetCode() == net]
    parent = list(range(len(items)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for i, j in itertools.combinations(range(len(items)), 2):
        for l in OUTER + (pcbnew.In1_Cu, pcbnew.In2_Cu):
            if items[i].IsOnLayer(l) and items[j].IsOnLayer(l) and \
               items[i].GetEffectiveShape(l).Collide(items[j].GetEffectiveShape(l), 0):
                parent[find(i)] = find(j)
                break
    groups = {}
    for i, it in enumerate(items):
        groups.setdefault(find(i), []).append(it)
    return list(groups.values())


def l_paths(a, b):
    yield [a, b]
    yield [a, (b[0], a[1]), b]
    yield [a, (a[0], b[1]), b]


def via_spots(board, net, anc, radii=(0.0, 0.45, 0.6, 0.8, 1.0, 1.2, 1.5), n_ang=16):
    """Legal (via + stub) spots near an anchor, as ((x, y), needs_via, stub_layer)."""
    out = []
    for r in radii:
        for k in range(n_ang if r else 1):
            a = 2 * math.pi * k / n_ang
            pt = (anc[0] + r * math.cos(a), anc[1] + r * math.sin(a))
            if r == 0 and pcbnew.F_Cu in anc[2]:
                out.append((pt, False, None))
                continue
            circ = pcbnew.SHAPE_CIRCLE(pcbnew.VECTOR2I(mm(pt[0]), mm(pt[1])), mm(VIA_D / 2))
            if not all(clear(board, net, l, circ) for l in OUTER):
                continue
            lay = next(iter(anc[2]))
            if r:
                seg = pcbnew.SHAPE_SEGMENT(pcbnew.VECTOR2I(mm(anc[0]), mm(anc[1])), pcbnew.VECTOR2I(mm(pt[0]), mm(pt[1])), mm(TRACK_W))
                if not clear(board, net, lay, seg):
                    continue
            out.append((pt, True, lay if r else None))
    return out


def try_f_bridge(board, net, isl_a, isl_b, max_len):
    """Hop over on F (the nearly empty lid face): legal via spots near the nearest anchors of each island, then a straight
    or L path on F between a spot pair. Spots are screened first so the path search stays small."""
    ca = [p for it in isl_a for p in anchors(it)]
    cb = [p for it in isl_b for p in anchors(it)]
    pairs = sorted(((math.hypot(x[0] - y[0], x[1] - y[1]), x, y) for x in ca for y in cb), key=lambda t: t[0])
    seen = set()
    for d, x, y in pairs[:12]:
        if d > max_len or (x[:2], y[:2]) in seen:
            continue
        seen.add((x[:2], y[:2]))
        sa, sb = via_spots(board, net, x), via_spots(board, net, y)
        cands = sorted(((math.hypot(u[0][0] - w[0][0], u[0][1] - w[0][1]), u, w) for u in sa for w in sb), key=lambda t: t[0])
        for _, u, w in cands[:200]:
            for path in l_paths(u[0], w[0]):
                segs, ok = [], True
                for q, r in zip(path, path[1:]):
                    if math.hypot(q[0] - r[0], q[1] - r[1]) < 1e-3:
                        continue
                    sg = try_segment(board, net, pcbnew.F_Cu, q, r)
                    if sg is None:
                        ok = False
                        break
                    segs += sg
                if not ok:
                    for t in segs:
                        board.Remove(t)
                    continue
                added = list(segs)
                for spot, anc in ((u, x), (w, y)):
                    if spot[1]:
                        v = try_via(board, net, spot[0])
                        if not v:
                            ok = False
                            break
                        added += v
                        if spot[2] is not None:
                            st = try_segment(board, net, spot[2], anc[:2], spot[0])
                            if st is None:
                                ok = False
                                break
                            added += st
                if ok:
                    return added
                for t in added:
                    board.Remove(t)
    return None

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
        added = None
        kind, d = "f-bridge", 0.0
        if best is not None:
            d, kind, layer, pa, pb = best
        if best is None:
            pass
        elif kind == "seg":
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
        if not added:                                    # fall back: hop over on the F face between the two islands
            isl = net_islands(board, net)
            ia = next((g for g in isl if any(items[0] is it or (it.m_Uuid.AsString() == items[0].m_Uuid.AsString()) for it in g)), None)
            ib = next((g for g in isl if any(it.m_Uuid.AsString() == items[1].m_Uuid.AsString() for it in g)), None)
            if ia is not None and ib is not None and ia is not ib:
                added = try_f_bridge(board, net, ia, ib, a.max_len * 3)
                kind = "f-bridge"
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
