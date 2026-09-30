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
W, H, CORNER = 20.0, 10.0, 1.0

# (ref, x, y, rotation deg, side). Grouped by function; the bridge sits at the rear, far from the mic.
PLACE = {
    # ---- F (outer face): MCU square in the middle (a 45-degree QFN would be 10.7 mm tall)
    "U1": (10.0, 5.0, 0, "F"),
    # left strip: crystal on PC14/PC15 (pins 3/4), NRST, VDDA, VDD48 decoupling, SWD pads
    "Y1": (3.6, 3.0, 90, "F"), "C11": (5.3, 2.2, 90, "F"), "C12": (5.3, 4.2, 90, "F"),
    "C10": (5.3, 6.2, 90, "F"), "C5": (5.3, 8.2, 90, "F"), "C6": (4.3, 8.2, 90, "F"), "C1": (4.3, 6.2, 90, "F"),
    "TP1": (1.0, 1.0, 0, "F"), "TP2": (1.0, 2.6, 0, "F"), "TP3": (1.0, 4.2, 0, "F"),
    "TP4": (1.0, 5.8, 0, "F"), "TP5": (2.5, 5.9, 0, "F"),          # all 5 SWD pads together for a pogo jig
    # right strip: VDD25/VDD36 decoupling, SMPS (pins 20-23 at the bottom-right corner), button
    "C3": (14.6, 2.4, 90, "F"), "C4": (15.6, 2.4, 90, "F"), "C7": (15.0, 5.0, 90, "F"),
    "C2": (14.6, 7.6, 90, "F"), "C8": (14.6, 9.35, 0, "F"), "L1": (16.8, 8.6, 0, "F"), "C9": (17.3, 6.8, 0, "F"),
    "SW1": (18.3, 3.3, 90, "F"), "R1": (16.9, 1.0, 0, "F"),
    # ---- B (inner face, toward the cell)
    # front: mic, ports outward through the board; nothing on F over its port
    "U2": (2.2, 7.6, 90, "B"), "R2": (4.9, 8.6, 90, "B"), "C13": (4.9, 6.2, 90, "B"),
    # middle: charger, LDO, battery sense, pads
    "U3": (7.4, 3.0, 0, "B"), "C15": (4.8, 2.0, 90, "B"), "C16": (10.0, 2.0, 90, "B"), "R7": (7.4, 5.4, 0, "B"),
    "D3": (6.4, 7.2, 0, "B"),
    "U4": (11.2, 5.6, 0, "B"), "C17": (11.2, 3.9, 0, "B"), "C18": (11.2, 7.1, 0, "B"),
    "R8": (12.4, 1.6, 90, "B"), "R9": (13.4, 1.6, 90, "B"), "C19": (11.4, 1.6, 90, "B"),
    "J3": (6.9, 9.0, 0, "B"), "J4": (8.5, 9.0, 0, "B"), "J5": (10.1, 9.0, 0, "B"), "J6": (11.7, 9.0, 0, "B"),
    # rear: bridge, far from the mic
    "Q1": (15.6, 4.8, 0, "B"), "Q2": (18.4, 4.8, 0, "B"),
    "R3": (15.6, 3.2, 0, "B"), "R4": (15.6, 6.3, 0, "B"), "R5": (18.4, 3.2, 0, "B"), "R6": (18.4, 6.3, 0, "B"),
    "C14": (14.4, 8.9, 0, "B"), "D1": (16.9, 7.6, 0, "B"), "D2": (18.7, 7.6, 0, "B"),
    "J1": (17.2, 9.1, 0, "B"), "J2": (18.8, 9.1, 0, "B"),
    "R10": (17.0, 1.5, 0, "B"),
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


def outline(b):
    """Rounded rectangle on Edge.Cuts."""
    r = CORNER
    segs = [((r, 0), (W - r, 0)), ((W, r), (W, H - r)), ((W - r, H), (r, H)), ((0, H - r), (0, r))]
    for (x1, y1), (x2, y2) in segs:
        s = pcbnew.PCB_SHAPE(b); s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetLayer(pcbnew.Edge_Cuts)
        s.SetStart(pcbnew.VECTOR2I(mm(x1), mm(y1))); s.SetEnd(pcbnew.VECTOR2I(mm(x2), mm(y2))); s.SetWidth(mm(0.05))
        b.Add(s)
    for cx, cy, sx, sy in ((r, r, 0, r), (W - r, r, W - r, 0), (W - r, H - r, W, H - r), (r, H - r, r, H)):
        a = pcbnew.PCB_SHAPE(b); a.SetShape(pcbnew.SHAPE_T_ARC); a.SetLayer(pcbnew.Edge_Cuts)
        a.SetCenter(pcbnew.VECTOR2I(mm(cx), mm(cy))); a.SetStart(pcbnew.VECTOR2I(mm(sx), mm(sy)))
        a.SetArcAngleAndEnd(pcbnew.EDA_ANGLE(-90, pcbnew.DEGREES_T), True); a.SetWidth(mm(0.05))
        b.Add(a)


def rules(b):
    """JLC 4-layer capability with margin: 0.1 mm track/space, 0.3/0.15 mm vias (JLC min 0.25/0.15)."""
    b.SetCopperLayerCount(4)
    ds = b.GetDesignSettings()
    ds.m_TrackMinWidth = mm(0.09); ds.m_MinClearance = mm(0.09)
    ds.m_ViasMinSize = mm(0.3); ds.m_MinThroughDrill = mm(0.15); ds.m_ViasMinAnnularWidth = mm(0.075)
    nc = ds.m_NetSettings.GetDefaultNetclass()
    nc.SetTrackWidth(mm(0.1)); nc.SetClearance(mm(0.1)); nc.SetViaDiameter(mm(0.3)); nc.SetViaDrill(mm(0.15))


def build():
    comps, nets = parse_netlist(HERE / "pod.net")
    b = pcbnew.BOARD()
    rules(b)
    outline(b)
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


def main():
    b, fps = build()
    b.BuildConnectivity()
    ov = [o for o in courtyard_overlaps(fps) if not (o[0][0] in "JT" and o[1][0] in "JT")]   # pad-pad courtyards: 2 mm rings on 1 mm pads
    print("courtyard overlaps (mm^2):", ov or "none")
    pcb, dsn, ses = OUT / "pod_placed.kicad_pcb", OUT / "pod.dsn", OUT / "pod.ses"
    pcbnew.SaveBoard(str(pcb), b)
    assert pcbnew.ExportSpecctraDSN(b, str(dsn))
    subprocess.run([os.environ["FREEROUTING_JAVA"], "-jar", os.environ["FREEROUTING_JAR"], "-de", str(dsn),
                    "-do", str(ses), "-mp", "40", "--gui.enabled=false"], check=True, timeout=900,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    b = pcbnew.LoadBoard(str(pcb))
    assert pcbnew.ImportSpecctraSES(b, str(ses))
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
               "unconnected": len(d.get("unconnected_items", [])), "courtyard_overlaps": ov}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    for side in ("top", "bottom"):
        subprocess.run(["kicad-cli", "pcb", "render", "--output", str(OUT / f"render_{side}.png"), "--side", side,
                        "--width", "1400", "--height", "800", "--zoom", "3.2", "--quality", "high",
                        "--background", "opaque", str(routed)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=300)


if __name__ == "__main__":
    main()
