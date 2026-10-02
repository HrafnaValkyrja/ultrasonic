#!/usr/bin/env python3
"""Routing-congestion map of a KiCad board: where the router ran out of room.

One panel per routing layer (F.Cu, In2.Cu, B.Cu; In1 is the GND plane and is skipped), stacked.
Each panel shows the board outline, a heat map of track density (track length per 0.5 mm cell,
lightly smoothed), the tracks at true width, vias as rings, and (on the outer layers) that face's
pads and courtyards. The unrouted connections from the DRC report are drawn on every panel as red
dashed airlines, labelled with their net. Dark theme from tools/plotstyle.py.

    source tools/env.sh
    systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 \
        python3 docs/diagrams/routing_congestion.py [BOARD.kicad_pcb] [DRC.json] [OUT.png] [--title T]

Defaults: the rev-1 baseline draft (hw/pod/draft_r1/baseline/) -> docs/diagrams/routing-congestion.png.
Make the DRC report with: kicad-cli pcb drc --format json --schematic-parity -o drc.json BOARD
Coordinates are board millimetres with y pointing down, as in KiCad; the B.Cu panel is seen through
the board from the F side (not mirrored), so all three panels line up.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import plotstyle  # noqa: E402

plt = plotstyle.apply()
import matplotlib.patheffects as pe  # noqa: E402
from matplotlib.collections import LineCollection, PatchCollection  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Circle, Polygon  # noqa: E402
from scipy.ndimage import gaussian_filter  # noqa: E402

import pcbnew  # noqa: E402

S = plotstyle
RED = S.SERIES[7]            # unrouted airlines: the only red on the page
VIA_C = S.SERIES[2]          # via rings
TRACK_C = S.TEXT             # tracks: light neutral over the coloured heat map
PAD_C = S.TEXT_2             # pads: grey
CRT_C = "#5a5e66"            # courtyards: faint
HEAT = LinearSegmentedColormap.from_list("heat", [S.SURFACE, "#2b2550", "#5a4cb0", S.SERIES[6], "#c3bbff"])

CELL = 0.5                   # mm, heat-map bin
SMOOTH = 0.7                 # gaussian sigma, in cells
DPI = 150

# Key parts labelled on their face: (label, refs). A group label points at the group's centroid.
KEY_PARTS = [
    ("U1 MCU", ["U1"]), ("U2 mic", ["U2"]), ("U3 charger", ["U3"]), ("U4 LDO", ["U4"]),
    ("Q1·Q2 bridge", ["Q1", "Q2"]), ("SW1 switch", ["SW1"]), ("L1 inductor", ["L1"]),
    ("J wire pads", [f"J{i}" for i in range(1, 30)]), ("TP pads", [f"TP{i}" for i in range(1, 30)]),
]
LAYERS = [("F.Cu", "F.Cu (top, faces the lid)", "F"),
          ("In2.Cu", "In2.Cu (inner signal layer)", None),
          ("B.Cu", "B.Cu (bottom, faces the cell; seen through the board, not mirrored)", "B")]


# ----------------------------------------------------------------------------- board extraction
def mm(v):
    return pcbnew.ToMM(v)


def poly_pts(ps):
    """Outer contours of a SHAPE_POLY_SET as lists of (x, y) mm."""
    out = []
    for i in range(ps.OutlineCount()):
        ch = ps.Outline(i)
        out.append([(mm(ch.CPoint(k).x), mm(ch.CPoint(k).y)) for k in range(ch.PointCount())])
    return out


def via_diameter(v):
    try:
        return mm(v.GetWidth(pcbnew.F_Cu))
    except TypeError:
        return mm(v.GetWidth())


def load_board(path):
    b = pcbnew.LoadBoard(str(path))
    out = {"outline": [], "pads": {"F": [], "B": []}, "crt": {"F": [], "B": []},
           "tracks": {}, "vias": [], "parts": {}}
    ps = pcbnew.SHAPE_POLY_SET()
    try:
        b.GetBoardPolygonOutlines(ps, False)           # KiCad 10: (poly, aInferOutlineIfNecessary)
    except TypeError:
        b.GetBoardPolygonOutlines(ps)
    out["outline"] = poly_pts(ps)
    bb = b.GetBoardEdgesBoundingBox()
    out["bbox"] = (mm(bb.GetX()), mm(bb.GetY()), mm(bb.GetRight()), mm(bb.GetBottom()))
    err = pcbnew.FromMM(0.005)
    for f in b.GetFootprints():
        side = "B" if f.IsFlipped() else "F"
        p = f.GetPosition()
        out["parts"][f.GetReference()] = (mm(p.x), mm(p.y), side)
        for pad in f.Pads():
            q = pad.GetPosition()
            out.setdefault("padpos", []).append((f.GetReference(), pad.GetNumber(), pad.GetNetname(), mm(q.x), mm(q.y)))
        f.BuildCourtyardCaches()
        crt = f.GetCourtyard(pcbnew.B_CrtYd if side == "B" else pcbnew.F_CrtYd)
        out["crt"][side] += poly_pts(crt)
        for pad in f.Pads():
            for s, lay in (("F", pcbnew.F_Cu), ("B", pcbnew.B_Cu)):
                if pad.IsOnLayer(lay):
                    pps = pcbnew.SHAPE_POLY_SET()
                    pad.TransformShapeToPolygon(pps, lay, 0, err, pcbnew.ERROR_INSIDE)
                    out["pads"][s] += poly_pts(pps)
    for t in b.GetTracks():
        cls = t.GetClass()
        if cls == "PCB_VIA":
            p = t.GetPosition()
            out["vias"].append((mm(p.x), mm(p.y), via_diameter(t), mm(t.GetDrillValue()), t.GetNetname()))
            continue
        lay = b.GetLayerName(t.GetLayer())
        w = mm(t.GetWidth())
        if cls == "PCB_ARC":                       # sample the arc into short chords
            c, r = t.GetCenter(), mm(t.GetRadius())
            a0 = math.atan2(mm(t.GetStart().y) - mm(c.y), mm(t.GetStart().x) - mm(c.x))
            a1 = math.atan2(mm(t.GetEnd().y) - mm(c.y), mm(t.GetEnd().x) - mm(c.x))
            da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
            n = max(2, int(abs(da) * r / 0.1) + 1)
            pts = [(mm(c.x) + r * math.cos(a0 + da * k / n), mm(c.y) + r * math.sin(a0 + da * k / n)) for k in range(n + 1)]
            segs = list(zip(pts[:-1], pts[1:]))
        else:
            segs = [((mm(t.GetStart().x), mm(t.GetStart().y)), (mm(t.GetEnd().x), mm(t.GetEnd().y)))]
        for s in segs:
            out["tracks"].setdefault(lay, []).append((s, w, t.GetNetname()))
    out["plane_nets"] = {z.GetNetname() for z in b.Zones()}
    return out


# ----------------------------------------------------------------------------- DRC unrouted list
ITEM_RE = re.compile(r"^(?P<kind>Pad|Track|Via)\s*(?P<num>\S+)?\s*\[(?P<net>[^\]]*)\](?: of (?P<ref>\S+))?(?: on (?P<lay>[^,]+))?")


def item_name(desc, pos, padpos):
    """'U1.27' for a pad; for a track or via, the same-net pad it hangs off ('Q2.2 stub'), else 'B.Cu track'."""
    m = ITEM_RE.match(desc)
    if not m:
        return desc.split(",")[0], "", 1
    if m["kind"] == "Pad":
        return f"{m['ref']}.{m['num']}", m["net"], 0
    near = [(math.dist(pos, (x, y)), r, n) for r, n, net, x, y in padpos if net == m["net"]]
    if near and min(near)[0] < 1.0:
        _d, r, n = min(near)
        return f"{r}.{n} stub", m["net"], 1
    return f"{(m['lay'] or '').strip()} {m['kind'].lower()}", m["net"], 2


def load_unrouted(path, padpos):
    d = json.loads(Path(path).read_text())
    out = []
    for u in d.get("unconnected_items", []):
        ends = []
        for it in u["items"][:2]:
            pos = (it["pos"]["x"], it["pos"]["y"])
            name, net, rank = item_name(it["description"], pos, padpos)
            ends.append((rank, name, pos, net))
        ends.sort(key=lambda e: e[0])                  # pads first
        out.append({"net": ends[0][3] or ends[1][3], "a": ends[0][2], "b": ends[1][2],
                    "ends": f"{ends[0][1]} → {ends[1][1]}"})
    return out


# ----------------------------------------------------------------------------- drawing helpers
def density(tracks, x0, y0, x1, y1):
    xe = np.arange(x0, x1 + CELL, CELL)
    ye = np.arange(y0, y1 + CELL, CELL)
    xs, ys, ws = [], [], []
    for (p, q), _w, _n in tracks:
        L = math.dist(p, q)
        n = max(1, int(L / 0.05))
        t = (np.arange(n) + 0.5) / n
        xs.append(p[0] + (q[0] - p[0]) * t)
        ys.append(p[1] + (q[1] - p[1]) * t)
        ws.append(np.full(n, L / n))
    if not xs:
        return np.zeros((len(ye) - 1, len(xe) - 1)), xe, ye
    H, _, _ = np.histogram2d(np.concatenate(xs), np.concatenate(ys), bins=[xe, ye], weights=np.concatenate(ws))
    return gaussian_filter(H.T, SMOOTH, mode="constant"), xe, ye


def spread(targets, widths, lo, hi, gap=0.5):
    """1-D label placement: keep each label near its target x without overlaps."""
    order = sorted(range(len(targets)), key=lambda i: targets[i])
    xs = [targets[i] for i in order]
    ws = [widths[i] for i in order]
    for _ in range(50):
        moved = False
        for k in range(1, len(xs)):
            need = (ws[k - 1] + ws[k]) / 2 + gap
            if xs[k] - xs[k - 1] < need:
                push = (need - (xs[k] - xs[k - 1])) / 2
                xs[k - 1] -= push; xs[k] += push; moved = True
        for k in range(len(xs)):
            xs[k] = min(max(xs[k], lo + ws[k] / 2), hi - ws[k] / 2)
        if not moved:
            break
    res = [0.0] * len(targets)
    for k, i in enumerate(order):
        res[i] = xs[k]
    return res


HALO = [pe.withStroke(linewidth=4, foreground=S.SURFACE)]


def draw_panel(ax, bd, unrouted, lay, title, side, vmax, mm_to_pt, ylims, char_mm):
    x0, y0, x1, y1 = bd["bbox"]
    tracks = bd["tracks"].get(lay, [])
    H, xe, ye = density(tracks, x0, y0, x1, y1)
    ax.imshow(H, extent=(xe[0], xe[-1], ye[-1], ye[0]), cmap=HEAT, vmin=0, vmax=vmax,
              interpolation="bilinear", zorder=0)
    for pts in bd["outline"]:
        ax.add_patch(Polygon(pts, closed=True, fill=False, ec=S.TEXT_2, lw=1.6, zorder=6))
    if side:
        ax.add_collection(PatchCollection([Polygon(p, closed=True) for p in bd["crt"][side]],
                                          facecolor="none", edgecolor=CRT_C, lw=0.7, linestyle=(0, (2, 2)), zorder=1))
        ax.add_collection(PatchCollection([Polygon(p, closed=True) for p in bd["pads"][side]],
                                          facecolor=PAD_C, edgecolor="none", alpha=0.55, zorder=2))
    if tracks:
        ax.add_collection(LineCollection([s for s, _w, _n in tracks], colors=TRACK_C, alpha=0.9,
                                         linewidths=[max(0.4, w * mm_to_pt) for _s, w, _n in tracks],
                                         capstyle="round", zorder=3))
    ax.add_collection(PatchCollection([Circle((x, y), d / 2) for x, y, d, _dr, _n in bd["vias"]],
                                      facecolor=S.SURFACE, edgecolor=VIA_C, lw=1.3, zorder=4))
    # unrouted airlines: GND thin with a small in-place tag, signals thick with labels in the bottom margin
    sig = [u for u in unrouted if u["net"] not in bd["plane_nets"]]
    for u in unrouted:
        is_sig = u in sig
        (ax_, ay), (bx, by) = u["a"], u["b"]
        ax.plot([ax_, bx], [ay, by], color=RED, lw=2.6 if is_sig else 1.5, ls=(0, (4, 2)) if is_sig else (0, (2, 2)),
                zorder=8, solid_capstyle="round")
        ax.plot([ax_, bx], [ay, by], "o", color=RED, ms=5 if is_sig else 3.5, zorder=9)
        if not is_sig:
            ax.text((ax_ + bx) / 2, (ay + by) / 2 - 0.15, u["net"], color=RED, fontsize=8.5, ha="center", va="bottom",
                    alpha=0.9, zorder=7, path_effects=[pe.withStroke(linewidth=2.5, foreground=S.SURFACE)])
    if sig:
        mids = [((u["a"][0] + u["b"][0]) / 2, (u["a"][1] + u["b"][1]) / 2) for u in sig]
        widths = [max(len(u["net"]), len(u["ends"]) * 0.72) * char_mm * 1.05 for u in sig]
        lx = spread([m[0] for m in mids], widths, x0, x1)
        ly = y1 + 1.0
        for u, (mx, my), x in zip(sig, mids, lx):
            ax.annotate("", xy=(mx, my), xytext=(x, ly), zorder=7,
                        arrowprops=dict(arrowstyle="-", color=RED, lw=0.9, alpha=0.8, shrinkA=0, shrinkB=2))
            ax.text(x, ly, u["net"], color=RED, fontsize=16, fontweight="bold", ha="center", va="top", zorder=10,
                    path_effects=HALO)
            ax.text(x, ly + 1.05, u["ends"], color=S.TEXT_2, fontsize=11.5, ha="center", va="top", zorder=10,
                    path_effects=HALO)
    # key-part labels in the top margin, leader to the part (group: its centroid)
    if side:
        labs = []
        for text, refs in KEY_PARTS:
            pts = [bd["parts"][r][:2] for r in refs if r in bd["parts"] and bd["parts"][r][2] == side]
            if pts:
                labs.append((text, float(np.mean([p[0] for p in pts])), float(np.mean([p[1] for p in pts]))))
        lx = spread([l[1] for l in labs], [len(l[0]) * char_mm * 1.15 for l in labs], x0, x1)
        ly = y0 - 1.0
        for (text, px, py), x in zip(labs, lx):
            ax.annotate("", xy=(px, py), xytext=(x, ly), zorder=5,
                        arrowprops=dict(arrowstyle="-", color=S.TEXT, lw=0.9, alpha=0.7, shrinkA=0, shrinkB=0))
            ax.plot([px], [py], "o", ms=4.5, mfc=S.SURFACE, mec=S.TEXT, zorder=5)
            ax.text(x, ly, text, color=S.TEXT, fontsize=15, fontweight="bold", ha="center", va="bottom", zorder=10,
                    path_effects=HALO)
    L = sum(math.dist(*s) for s, _w, _n in tracks)
    ax.set_title(f"{title}   ·   {L:.0f} mm of track", loc="left", fontsize=17, color=S.TEXT, pad=6)
    ax.set_xlim(x0 - 0.6, x1 + 0.6)
    ax.set_ylim(*ylims)
    ax.set_aspect("equal")
    ax.grid(False)
    ax.set_xticks(np.arange(math.ceil(x0), x1 + 0.01, 2))
    ax.set_yticks(np.arange(math.ceil(y0), y1 + 0.01, 2))
    ax.tick_params(labelsize=12)
    for s in ("left", "bottom"):
        ax.spines[s].set_bounds(*((x0, x1) if s == "bottom" else (y0, y1)))
    return H.max()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("board", nargs="?", default=str(ROOT / "hw/pod/draft_r1/baseline/pod_r1_routed.kicad_pcb"))
    ap.add_argument("drc", nargs="?", default=str(ROOT / "hw/pod/draft_r1/baseline/drc.json"))
    ap.add_argument("out", nargs="?", default=str(ROOT / "docs/diagrams/routing-congestion.png"))
    ap.add_argument("--title", default=None)
    a = ap.parse_args()

    bd = load_board(a.board)
    unrouted = load_unrouted(a.drc, bd.get("padpos", []))
    x0, y0, x1, y1 = bd["bbox"]
    title = a.title or f"Rev-1 draft: where routing jams ({Path(a.board).parent.name}, {len(unrouted)} unrouted)"

    ylims = (y1 + 3.4, y0 - 2.3)                         # inverted: y grows downward like KiCad
    fig_w = 12.4
    ax_w_in = fig_w * 0.94
    ax_h_in = ax_w_in * (ylims[0] - ylims[1]) / (x1 - x0 + 1.2)
    fig_h = 3 * (ax_h_in + 0.55) + 2.35
    fig = plt.figure(figsize=(fig_w, fig_h), dpi=DPI)
    mm_to_pt = ax_w_in * 72 / (x1 - x0 + 1.2)            # points per board mm
    char_mm = 0.58 * 15 / mm_to_pt                       # rough width of one 15 pt character, in mm

    # shared colour scale: the busiest cell on any layer
    vmax = max(density(bd["tracks"].get(l, []), x0, y0, x1, y1)[0].max() for l, _t, _s in LAYERS) or 1.0
    top = 1 - 2.0 / fig_h
    ph = (top - 0.55 / fig_h) / 3
    axes = []
    for i, (lay, ttl, side) in enumerate(LAYERS):
        ax = fig.add_axes([0.045, top - (i + 1) * ph + 0.45 / fig_h, 0.94, ph - 0.55 / fig_h])
        draw_panel(ax, bd, unrouted, lay, ttl, side, vmax, mm_to_pt, ylims, char_mm)
        axes.append(ax)

    fig.text(0.045, 1 - 0.25 / fig_h, title, fontsize=24, fontweight="bold", color=S.TEXT, va="top")
    n_sig = sum(u["net"] not in bd["plane_nets"] for u in unrouted)
    fig.text(0.045, 1 - 0.78 / fig_h,
             f"{n_sig} signal + {len(unrouted) - n_sig} plane-net ({', '.join(sorted(bd['plane_nets']))}) connections unrouted. "
             f"Purple glow = track length per {CELL} mm cell. Board mm, y down.",
             fontsize=13, color=S.TEXT_2, va="top")
    handles = [Line2D([], [], color=TRACK_C, lw=2.5, label="track (true width)"),
               Line2D([], [], marker="o", ls="none", mfc=S.SURFACE, mec=VIA_C, mew=1.5, ms=9, label="via"),
               Line2D([], [], marker="s", ls="none", mfc=PAD_C, mec="none", alpha=0.6, ms=9, label="pad (this face)"),
               Line2D([], [], color=CRT_C, lw=1.2, ls=(0, (2, 2)), label="courtyard"),
               Line2D([], [], color=RED, lw=2.6, ls=(0, (4, 2)), marker="o", ms=5, label="unrouted signal"),
               Line2D([], [], color=RED, lw=1.5, ls=(0, (2, 2)), label="unrouted GND")]
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.04, 1 - 1.05 / fig_h), ncol=6, fontsize=12.5,
               handlelength=2.2, columnspacing=1.4, frameon=False, labelcolor=S.TEXT)
    cax = fig.add_axes([0.62, 0.12 / fig_h, 0.33, 0.13 / fig_h])
    sm = plt.cm.ScalarMappable(cmap=HEAT, norm=plt.Normalize(0, vmax))
    cb = fig.colorbar(sm, cax=cax, orientation="horizontal")
    cb.ax.tick_params(labelsize=11, colors=S.TEXT_2)
    cb.outline.set_visible(False)
    fig.text(0.61, 0.185 / fig_h, f"mm of track per {CELL} × {CELL} mm cell (smoothed)", fontsize=12, color=S.TEXT_2,
             ha="right", va="center")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(a.out, dpi=DPI, bbox_inches=None)
    print(f"wrote {a.out}  ({int(fig_w * DPI)} x {int(fig_h * DPI)} px), {len(unrouted)} unrouted, {n_sig} signal")


if __name__ == "__main__":
    main()
