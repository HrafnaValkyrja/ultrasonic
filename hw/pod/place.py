"""Feasibility placement + autoroute of the pod board: does everything fit on 20 x 10 mm and route?

    source tools/env.sh && python3 hw/pod/place.py      # -> hw/pod/draft/*.kicad_pcb, drc.json, renders

This is a DRAFT to prove fit and routability. It is not the layout: the owner lays the real board
out in KiCad from pod.net (CLAUDE.md). Coordinates: x = 0 at the pod's front (mic end), running back
along the temple arm; y = 0 at the board's top edge. F (top) faces the pod's outer wall; B faces
the cell. The mic sits on B and ports outward through the board (§8 acoustic rules).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

import pcbnew

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
OUT = HERE / "draft"
OUT.mkdir(exist_ok=True)
mm = pcbnew.FromMM
W, H, CORNER = 20.0, 11.5, 1.0   # 11.5 mm: the pod's inner height is 12.4 mm (hw/mech/pod.py); 10 mm starved the QFN's escape

# (ref, x, y, rotation deg, side). Grouped by function; the bridge sits at the rear, far from the mic.
PLACE = {
    # ---- F (outer face): MCU square in the middle (a 45-degree QFN would be 10.7 mm tall)
    "U1": (10.0, 5.75, 0, "F"),
    # left strip: crystal on PC14/PC15 (pins 3/4), NRST, VDDA, VDD48 decoupling, SWD pads
    "Y1": (3.6, 3.45, 90, "F"), "C11": (5.3, 2.53, 90, "F"), "C12": (5.3, 4.83, 90, "F"),
    "C10": (5.3, 7.13, 90, "F"), "C5": (5.3, 9.43, 90, "F"), "C6": (4.3, 9.43, 90, "F"), "C1": (4.3, 7.13, 90, "F"),
    "TP1": (1.0, 1.15, 0, "F"), "TP2": (1.0, 2.99, 0, "F"), "TP3": (1.0, 4.83, 0, "F"),
    "TP4": (1.0, 6.67, 0, "F"), "TP5": (2.5, 6.79, 0, "F"),          # all 5 SWD pads together for a pogo jig
    # right strip: VDD25/VDD36 decoupling, SMPS (pins 20-23 at the bottom-right corner), button
    "C3": (14.6, 2.76, 90, "F"), "C4": (15.6, 2.76, 90, "F"), "C7": (15.0, 5.75, 90, "F"),
    "C2": (14.6, 8.74, 90, "F"), "C8": (14.6, 10.75, 0, "F"), "L1": (17.4, 9.89, 0, "F"), "C9": (17.3, 7.82, 0, "F"),
    "SW1": (18.3, 3.79, 90, "F"), "R1": (15.8, 0.92, 0, "F"),
    # ---- B (inner face, toward the cell)
    # front: mic, ports outward through the board; nothing on F over its port
    "U2": (2.2, 8.74, 90, "B"), "R2": (4.9, 9.89, 90, "B"), "C13": (4.9, 7.13, 90, "B"),
    # middle: charger, LDO, battery sense, pads
    "U3": (7.4, 3.45, 0, "B"), "C15": (4.8, 2.30, 90, "B"), "C16": (10.0, 2.30, 90, "B"), "R7": (7.4, 6.21, 0, "B"),
    "D3": (6.4, 8.28, 0, "B"),
    "U4": (11.2, 6.44, 0, "B"), "C17": (11.2, 4.49, 0, "B"), "C18": (11.2, 8.16, 0, "B"),
    "R8": (12.4, 1.84, 90, "B"), "R9": (13.4, 1.84, 90, "B"), "C19": (11.4, 1.84, 90, "B"),
    "J3": (6.9, 10.35, 0, "B"), "J4": (8.5, 10.35, 0, "B"), "J5": (10.1, 10.35, 0, "B"), "J6": (11.7, 10.35, 0, "B"),
    # rear: bridge, far from the mic
    "Q1": (15.6, 5.52, 0, "B"), "Q2": (18.4, 5.52, 0, "B"),
    "R3": (15.6, 3.68, 0, "B"), "R4": (15.6, 7.25, 0, "B"), "R5": (18.4, 3.68, 0, "B"), "R6": (18.4, 7.25, 0, "B"),
    "C14": (14.4, 10.24, 0, "B"), "D1": (16.9, 8.74, 0, "B"), "D2": (18.7, 8.74, 0, "B"),
    "J1": (17.2, 10.46, 0, "B"), "J2": (18.8, 10.46, 0, "B"),
    "R10": (17.0, 1.73, 0, "B"),
}


def _sexpr(txt):
    """Minimal S-expression reader for KiCad netlists: returns nested lists of strings."""
    toks = re.findall(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+', txt)
    stack = [[]]
    for t in toks:
        if t == "(":
            stack.append([])
        elif t == ")":
            done = stack.pop(); stack[-1].append(done)
        else:
            stack[-1].append(t[1:-1] if t.startswith('"') else t)
    return stack[0][0]


def _find(node, key):
    return [c for c in node if isinstance(c, list) and c and c[0] == key]


def parse_netlist(path):
    root = _sexpr(Path(path).read_text())
    comps, nets = {}, {}
    for comp in _find(_find(root, "components")[0], "comp"):
        comps[_find(comp, "ref")[0][1]] = _find(comp, "footprint")[0][1]
    for net in _find(_find(root, "nets")[0], "net"):
        name = _find(net, "name")[0][1]
        nets[name] = [(_find(n, "ref")[0][1], _find(n, "pin")[0][1]) for n in _find(net, "node")]
    return comps, nets


def fp_lib(lib):
    if lib == "lcsc":
        return str(REPO / "hw/lib/lcsc/lcsc.pretty")
    return os.path.join(os.environ["KICAD10_FOOTPRINT_DIR"], f"{lib}.pretty")


def outline(b, inset=0.0):
    """Rounded rectangle on Edge.Cuts; `inset` shrinks it (routing only: FreeRouting ignores KiCad's
    copper-to-edge rule, so it routes inside an outline pulled in by that clearance)."""
    import math
    x0, y0, x1, y1, r = inset, inset, W - inset, H - inset, CORNER - inset
    V = lambda x, y: pcbnew.VECTOR2I(mm(x), mm(y))
    for (xa, ya), (xb, yb) in (((x0 + r, y0), (x1 - r, y0)), ((x1, y0 + r), (x1, y1 - r)),
                               ((x1 - r, y1), (x0 + r, y1)), ((x0, y1 - r), (x0, y0 + r))):
        s = pcbnew.PCB_SHAPE(b); s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetLayer(pcbnew.Edge_Cuts)
        s.SetStart(V(xa, ya)); s.SetEnd(V(xb, yb)); s.SetWidth(mm(0.05)); b.Add(s)
    k = r * (1 - math.sqrt(0.5))
    for st, mid, en in (((x0, y0 + r), (x0 + k, y0 + k), (x0 + r, y0)),
                        ((x1 - r, y0), (x1 - k, y0 + k), (x1, y0 + r)),
                        ((x1, y1 - r), (x1 - k, y1 - k), (x1 - r, y1)),
                        ((x0 + r, y1), (x0 + k, y1 - k), (x0, y1 - r))):
        a = pcbnew.PCB_SHAPE(b); a.SetShape(pcbnew.SHAPE_T_ARC); a.SetLayer(pcbnew.Edge_Cuts)
        a.SetArcGeometry(V(*st), V(*mid), V(*en)); a.SetWidth(mm(0.05)); b.Add(a)


def rules(b, clearance=0.1):
    """JLC 4-layer capability with margin: route at 0.1 mm track/space, 0.35/0.15 mm vias.
    The finished board is checked at JLC's real minimum spacing (0.09 mm): FreeRouting's 45-degree
    segments land a few um under their 0.1 mm target."""
    b.SetCopperLayerCount(4)
    ds = b.GetDesignSettings()
    ds.m_TrackMinWidth = mm(0.09); ds.m_MinClearance = mm(0.09)
    ds.m_ViasMinSize = mm(0.3); ds.m_MinThroughDrill = mm(0.15); ds.m_ViasMinAnnularWidth = mm(0.075)
    ds.m_HoleClearance = mm(0.2); ds.m_CopperEdgeClearance = mm(0.2)      # JLC capability page
    nc = ds.m_NetSettings.GetDefaultNetclass()
    nc.SetTrackWidth(mm(0.1)); nc.SetClearance(mm(clearance)); nc.SetViaDiameter(mm(0.35)); nc.SetViaDrill(mm(0.15))


def build(inset=0.0):
    comps, nets = parse_netlist(HERE / "pod.net")
    b = pcbnew.BOARD()
    rules(b)
    outline(b, inset)
    fps = {}
    for ref, fpid in comps.items():
        lib, name = fpid.split(":")
        fp = pcbnew.FootprintLoad(fp_lib(lib), name)
        assert fp is not None, f"footprint {fpid} not found"
        fp.SetReference(ref)
        x, y, rot, side = PLACE[ref]
        fp.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
        fp.SetOrientationDegrees(rot)
        b.Add(fp)
        if side == "B":
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        fps[ref] = fp
    missing = set(PLACE) ^ set(comps)
    assert not missing, f"placement table and netlist disagree: {missing}"
    for name, nodes in nets.items():
        ni = pcbnew.NETINFO_ITEM(b, name); b.Add(ni)
        for ref, pin in nodes:
            for p in fps[ref].Pads():
                if p.GetNumber() == pin:
                    p.SetNet(ni)
    return b, fps


def courtyard_overlaps(fps):
    """Pairs of same-side footprints whose courtyards overlap (a fit check before routing)."""
    bad = []
    items = list(fps.items())
    for i, (ra, a) in enumerate(items):
        for rb, bb in items[i + 1:]:
            if a.IsFlipped() != bb.IsFlipped():
                continue
            la = pcbnew.B_CrtYd if a.IsFlipped() else pcbnew.F_CrtYd
            ca, cb = a.GetCourtyard(la), bb.GetCourtyard(la)
            if ca.OutlineCount() and cb.OutlineCount():
                inter = ca.CloneDropTriangulation()
                inter.BooleanIntersection(cb)
                if inter.Area() > mm(0.02) * mm(1):
                    bad.append((ra, rb, round(inter.Area() / 1e12, 3)))
    return bad


def pad_clashes(fps, gap=0.12):
    """Copper pads of different footprints on the same side closer than `gap` mm (the imported
    LCSC footprints draw their courtyard round the body only, so courtyards miss pad collisions)."""
    items = []
    for ref, f in fps.items():
        for p in f.Pads():
            if p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                continue
            bb = p.GetBoundingBox()
            items.append((ref, f.IsFlipped(), p.GetNetname(), [pcbnew.ToMM(v) for v in (bb.GetX(), bb.GetY(), bb.GetRight(), bb.GetBottom())]))
    bad = set()
    for i, (ra, sa, na, a) in enumerate(items):
        for rb, sb, nb, c in items[i + 1:]:
            if ra == rb or sa != sb or (na and na == nb):
                continue
            if a[0] - gap < c[2] and c[0] - gap < a[2] and a[1] - gap < c[3] and c[1] - gap < a[3]:
                bad.add(tuple(sorted((ra, rb))))
    return sorted(bad)


def main():
    b, fps = build()
    b.BuildConnectivity()
    ov = [o for o in courtyard_overlaps(fps) if not (o[0][0] in "JT" and o[1][0] in "JT")]   # pad-pad courtyards: 2 mm rings on 1 mm pads
    clashes = pad_clashes(fps)
    print("courtyard overlaps (mm^2):", ov or "none", "| pad clashes:", clashes or "none")
    pcb, dsn, ses = OUT / "pod_placed.kicad_pcb", OUT / "pod.dsn", OUT / "pod.ses"
    pcbnew.SaveBoard(str(pcb), b)
    br, _ = build(inset=0.2)                                   # routing copy, outline pulled in 0.2 mm
    assert pcbnew.ExportSpecctraDSN(br, str(dsn))
    subprocess.run([os.environ["FREEROUTING_JAVA"], "-jar", os.environ["FREEROUTING_JAR"], "-de", str(dsn),
                    "-do", str(ses), "-mp", "150", "--gui.enabled=false"], check=True, timeout=2400,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    b = pcbnew.LoadBoard(str(pcb))
    assert pcbnew.ImportSpecctraSES(b, str(ses))
    necked = 0
    for t in b.GetTracks():                                   # FreeRouting necks some tracks to 0.05-0.075 mm
        if t.GetClass() == "PCB_TRACK" and t.GetWidth() < mm(0.1):
            t.SetWidth(mm(0.1)); necked += 1
    print("necked-down tracks widened to 0.1 mm:", necked)
    b.GetDesignSettings().m_NetSettings.GetDefaultNetclass().SetClearance(mm(0.09))   # DRC at JLC minimum
    routed = OUT / "pod_routed.kicad_pcb"
    pcbnew.SaveBoard(str(routed), b)
    drc = OUT / "drc.json"
    subprocess.run(["kicad-cli", "pcb", "drc", "--format", "json", "--severity-error", "--output", str(drc), str(routed)],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    d = json.loads(drc.read_text())
    viol = d.get("violations", [])
    kinds = {}
    for v in viol:
        kinds[v["type"]] = kinds.get(v["type"], 0) + 1
    tracks = [t for t in b.GetTracks()]
    vias = sum(1 for t in tracks if t.GetClass() == "PCB_VIA")
    summary = {"tracks": len(tracks) - vias, "vias": vias, "drc_errors": len(viol), "by_type": kinds,
               "unconnected": len(d.get("unconnected_items", [])), "courtyard_overlaps": ov, "pad_clashes": clashes}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    for side in ("top", "bottom"):
        subprocess.run(["kicad-cli", "pcb", "render", "--output", str(OUT / f"render_{side}.png"), "--side", side,
                        "--width", "1400", "--height", "800", "--zoom", "3.2", "--quality", "high",
                        "--background", "opaque", str(routed)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=300)


if __name__ == "__main__":
    main()
