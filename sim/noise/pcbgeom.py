"""Read any KiCad board (pcbnew) into plain Python geometry: tracks, vias, pads, zones, stackup.

Layout-agnostic: nothing here knows this project's nets or refs. Units: mm and ohm/henry/farad.
Needs the KiCad python module (`source tools/env.sh`; the venv sees pcbnew).

    geom = load("hw/pod/draft_r1/fanout/pod_r1_routed.kicad_pcb")
    geom["segments"], geom["vias"], geom["pads"], geom["zones"], geom["stackup"], geom["nets"]
"""
from __future__ import annotations

import hashlib
import math
import re
from pathlib import Path

NM = 1e-6  # nm -> mm
COPPER = ["F.Cu", "In1.Cu", "In2.Cu", "B.Cu"]  # top to bottom; 4-layer boards only (asserted)

# JLC 0.8 mm 4-layer stackup as entered in the earlier draft board hw/pod/kicad-draft/pod.kicad_pcb L39-55.
# Not verified against JLC's (JavaScript-rendered) impedance page, 2026-10-02. Used only if the board has none.
DEFAULT_STACKUP = {
    "src": "hw/pod/kicad-draft/pod.kicad_pcb:39-55 (JLC 0.8mm 4L as entered 2026-09-30); unverified vs JLC page",
    "copper_um": {"F.Cu": 35.0, "In1.Cu": 15.2, "In2.Cu": 15.2, "B.Cu": 35.0},
    "dielectric_mm": [0.0994, 0.4804, 0.0994],  # F-In1, In1-In2, In2-B
    "eps_r": [4.05, 4.6, 4.05],
}


def _parse_stackup(text: str):
    """Parse a KiCad `(stackup ...)` block. Returns a stackup dict or None."""
    m = re.search(r"\(stackup(.*?)\n\t\t\)", text, re.S)
    if not m:
        return None
    cu, di, eps = {}, [], []
    for lm in re.finditer(r'\(layer "([^"]+)"\s*\(type "([^"]+)"\)\s*\(thickness ([0-9.eE+-]+)\)([^\n]*)', m.group(1)):
        name, typ, thk, rest = lm.group(1), lm.group(2), float(lm.group(3)), lm.group(4)
        if typ == "copper":
            cu[name] = thk * 1000.0
        elif typ in ("core", "prepreg"):
            di.append(thk)
            e = re.search(r"epsilon_r ([0-9.]+)", rest)
            eps.append(float(e.group(1)) if e else 4.4)
    if len(cu) == 4 and len(di) == 3:
        return {"src": "board file (stackup)", "copper_um": cu, "dielectric_mm": di, "eps_r": eps}
    return None


def height_to_plane(stackup: dict, layer: str, plane: str = "In1.Cu"):
    """Dielectric height (mm) between a copper layer and the reference plane, and the mean eps_r.

    A signal layer with a plane two dielectrics away (B.Cu to In1 across In2) counts In2's copper as void.
    """
    d, e, cu = stackup["dielectric_mm"], stackup["eps_r"], stackup["copper_um"]
    if layer == plane:
        return 0.0, e[0]
    if layer == "F.Cu":
        return d[0], e[0]
    if layer == "In2.Cu":
        return d[1], e[1]
    if layer == "B.Cu":
        h = d[2] + cu["In2.Cu"] / 1000.0 + d[1]
        return h, (d[2] * e[2] + d[1] * e[1]) / (d[2] + d[1])
    raise ValueError(layer)


def load(path: str, stackup: dict | None = None) -> dict:
    """Load a .kicad_pcb. `stackup` overrides; else the file's own; else DEFAULT_STACKUP (flagged)."""
    import pcbnew  # noqa: PLC0415  (import late so the module can be inspected without KiCad)

    path = str(path)
    text = Path(path).read_text()
    board = pcbnew.LoadBoard(path)
    lname = board.GetLayerName
    ncu = board.GetCopperLayerCount()
    if ncu != 4:
        raise SystemExit(f"{path}: {ncu} copper layers; this extractor supports the 4-layer pod board only")
    st = stackup or _parse_stackup(text) or dict(DEFAULT_STACKUP)

    segs, vias, pads = [], [], []
    for t in board.GetTracks():
        cls = t.GetClass()
        if cls == "PCB_VIA":
            p = t.GetPosition()
            vias.append(dict(x=p.x * NM, y=p.y * NM, dia=t.GetWidth() * NM, drill=t.GetDrillValue() * NM,
                             top=lname(t.TopLayer()), bot=lname(t.BottomLayer()), net=t.GetNetname()))
        else:
            a, b = t.GetStart(), t.GetEnd()
            segs.append(dict(x1=a.x * NM, y1=a.y * NM, x2=b.x * NM, y2=b.y * NM, w=t.GetWidth() * NM,
                             layer=lname(t.GetLayer()), net=t.GetNetname(), arc=(cls == "PCB_ARC"),
                             length=t.GetLength() * NM))
    for fp in board.GetFootprints():
        side = lname(fp.GetLayer())
        for pd in fp.Pads():
            if pd.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH or not pd.GetNetname():
                continue
            c = pd.GetPosition()
            bb = pd.GetBoundingBox()
            thru = pd.GetAttribute() == pcbnew.PAD_ATTRIB_PTH
            pads.append(dict(ref=fp.GetReference(), num=pd.GetNumber(), net=pd.GetNetname(),
                             x=c.x * NM, y=c.y * NM, layer=side, thru=thru,
                             bbox=(bb.GetLeft() * NM, bb.GetTop() * NM, bb.GetRight() * NM, bb.GetBottom() * NM)))
    zones = []
    for z in board.Zones():
        for lid in z.GetLayerSet().Seq():
            if not z.IsOnCopperLayer():
                continue
            sp = z.GetFilledPolysList(lid)
            polys = []
            for i in range(sp.OutlineCount()):
                o = sp.Outline(i)
                outer = [(o.CPoint(k).x * NM, o.CPoint(k).y * NM) for k in range(o.PointCount())]
                holes = []
                for j in range(sp.HoleCount(i)):
                    h = sp.Hole(i, j)
                    holes.append([(h.CPoint(k).x * NM, h.CPoint(k).y * NM) for k in range(h.PointCount())])
                polys.append(dict(outer=outer, holes=holes))
            zones.append(dict(net=z.GetNetname(), layer=lname(lid), polys=polys, area_mm2=sp.Area() * NM * NM,
                              min_thickness=z.GetMinThickness() * NM))
    bb = board.GetBoardEdgesBoundingBox()
    refs = {fp.GetReference(): (fp.GetPosition().x * NM, fp.GetPosition().y * NM, lname(fp.GetLayer()),
                                fp.GetOrientationDegrees()) for fp in board.GetFootprints()}
    return dict(path=path, sha256=hashlib.sha256(text.encode()).hexdigest()[:16],
                board_mm=(bb.GetX() * NM, bb.GetY() * NM, bb.GetWidth() * NM, bb.GetHeight() * NM),
                stackup=st, segments=segs, vias=vias, pads=pads, zones=zones, footprints=refs,
                nets=sorted({s["net"] for s in segs} | {p["net"] for p in pads} | {v["net"] for v in vias}))


def per_net_summary(geom: dict) -> dict:
    """Per net: track length per layer (mm), segment count, min/max width, via count, pad count."""
    out: dict[str, dict] = {}
    for s in geom["segments"]:
        n = out.setdefault(s["net"], dict(len_mm={}, segs=0, w_min=1e9, w_max=0.0, vias=0, pads=0))
        n["len_mm"][s["layer"]] = n["len_mm"].get(s["layer"], 0.0) + s["length"]
        n["segs"] += 1
        n["w_min"], n["w_max"] = min(n["w_min"], s["w"]), max(n["w_max"], s["w"])
    for v in geom["vias"]:
        out.setdefault(v["net"], dict(len_mm={}, segs=0, w_min=0, w_max=0, vias=0, pads=0))["vias"] += 1
    for p in geom["pads"]:
        out.setdefault(p["net"], dict(len_mm={}, segs=0, w_min=0, w_max=0, vias=0, pads=0))["pads"] += 1
    for n in out.values():
        n["len_mm"] = {k: round(v, 3) for k, v in n["len_mm"].items()}
        n["len_total_mm"] = round(sum(n["len_mm"].values()), 3)
        if n["w_min"] == 1e9:
            n["w_min"] = 0
    return out


def seg_dist(px, py, s):
    """Distance from point to segment s, and the projection parameter t in [0,1]."""
    dx, dy = s["x2"] - s["x1"], s["y2"] - s["y1"]
    L2 = dx * dx + dy * dy
    if L2 == 0:
        return math.hypot(px - s["x1"], py - s["y1"]), 0.0
    t = max(0.0, min(1.0, ((px - s["x1"]) * dx + (py - s["y1"]) * dy) / L2))
    return math.hypot(px - (s["x1"] + t * dx), py - (s["y1"] + t * dy)), t


def read_netlist(path: str) -> dict[tuple[str, str], str]:
    """KiCad/SKiDL netlist (.net, s-expression) -> {(ref, pin): net}."""
    text = Path(path).read_text()
    text = text[text.index("(nets"):]
    out = {}
    for blk in re.split(r"\n\s*\(net\s*\n", text)[1:]:
        name = re.search(r'\(name "([^"]*)"\)', blk)
        if not name:
            continue
        for n in re.finditer(r'\(node\s*\(ref "([^"]+)"\)\s*\(pin "([^"]+)"\)', blk):
            out[(n.group(1), n.group(2))] = name.group(1)
    return out


# Board candidates, newest mtime wins (same rule as sim/acoustics/geometry.find_board, minus the unrouted placed board).
# Override with an explicit path or env NOISE_BOARD. A stale board (pad->net map != hw/pod/pod.net) makes results INVALID.
ROUTED_CANDIDATES = ("hw/pod/draft_r1/pod_r1_routed.kicad_pcb", "hw/pod/draft_r1/fanout/pod_r1_routed.kicad_pcb")


def default_board(repo: Path) -> str:
    import os  # noqa: PLC0415
    if os.environ.get("NOISE_BOARD"):
        return os.environ["NOISE_BOARD"]
    cands = [repo / c for c in ROUTED_CANDIDATES if (repo / c).exists()]
    if not cands:
        raise SystemExit(f"no routed board among {ROUTED_CANDIDATES}; pass a .kicad_pcb path")
    return str(max(cands, key=os.path.getmtime))


def netlist_diff(geom: dict, netlist_path: str) -> dict:
    """Compare the board's pad->net map with the schematic netlist. A non-empty `mismatch` means the board is stale."""
    nl = read_netlist(netlist_path)
    bd = {(p["ref"], p["num"]): p["net"] for p in geom["pads"]}
    mism = [(k, bd.get(k), nl.get(k)) for k in sorted(set(nl) | set(bd)) if bd.get(k) != nl.get(k)]
    return dict(netlist=str(netlist_path), pads_netlist=len(nl), pads_board=len(bd), mismatch=mism)
