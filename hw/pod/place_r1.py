"""Rev-1 board ROUGH DRAFT: 34 x 13 mm (grown rearward 2026-10-01; shell_r1 PCB x 30.6-64.6), 4 layers, parts on both faces, from pod.net (Rev F; placement as of 2026-10-02).

    source tools/env.sh && systemd-run --user --scope --quiet -p MemoryMax=4G -p MemorySwapMax=0 \
        python3 hw/pod/place_r1.py [--no-route]      # -> hw/pod/draft_r1/*

A first pass to prove fit and get a picture of the layout; the real 4-layer board is laid out
together with the owner (spec O14). Floorplan: docs/diagrams/pcb-floorplan-rev1.svg.
Coordinates: x = 0 at the front (mic end) running back; y = 0 at the top edge; centre line y = 6.5.
F (top) faces the lid (outer wall), B faces the cell. Layer 2 (In1) is a solid GND plane.
Mic PORT HOLE (board x 3.9; the footprint origin is 0.77 mm away, ECR-0011) and switch (board x 22.0) are on the centre line so one board fits both pods;
they match hw/mech/shell_r1.py (MIC x 34.5, SWITCH x 52.6 in pod coordinates; board x0 = 30.6).
All hand-soldered pads (J*, TP*) are on F along the top edge / rear, reachable with the lid off.
FreeRouting runs once, fenced, JVM capped (tools/env.sh FREEROUTING_JAVA_OPTS).
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pcbnew

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("place_v0", HERE / "place.py")
P = importlib.util.module_from_spec(spec)
spec.loader.exec_module(P)
P.W, P.H, P.CORNER = 34.0, 13.0, 1.0           # outline() reads these module globals
_fp_lib = P.fp_lib
P.fp_lib = lambda lib: str(HERE.parents[1] / "hw/lib/pod.pretty") if lib == "pod" else _fp_lib(lib)
OUT = HERE / "draft_r1"
OUT.mkdir(exist_ok=True)
mm = pcbnew.FromMM

PLACE = {
    # ================= F (outer face): MCU in the middle, quiet strip at the front, SMPS + switch behind it
    "U1": (13.0, 6.5, 0, "F"),
    "Y1": (6.6, 4.2, 90, "F"), "C11": (8.3, 3.28, 90, "F"), "C12": (8.3, 5.58, 90, "F"),
    "C10": (8.3, 7.88, 90, "F"), "C5": (8.3, 10.18, 90, "F"), "C6": (7.3, 10.18, 90, "F"), "C1": (9.4, 1.85, 90, "F"),
    
    "C3": (17.6, 3.51, 90, "F"), "C4": (18.8, 3.51, 90, "F"), "C7": (18.0, 6.5, 90, "F"),
    "C2": (17.6, 9.49, 90, "F"), "C8": (17.6, 11.5, 0, "F"), "L1": (20.4, 10.64, 0, "F"), "C9": (20.3, 8.57, 0, "F"),
    "R1": (17.0, 1.6, 0, "F"),
    "C22": (10.6, 11.6, 0, "F"), "R22": (12.6, 11.6, 0, "F"),   # 16 kHz I_SENSE filter right under PA6 (pin 16)
    "SW1": (22.0, 6.5, 0, "F"), "R10": (23.0, 9.5, 0, "F"),
    # test pads: one 1.27 mm-pitch row along the top edge (P50 pogo jig), outside the 0.6 mm clamp band
    **{f"TP{i + 1}": (24.4 + 1.27 * i, 1.3, 0, "F") for i in range(6)},
    # wire pads: two columns at the rear edge, where the arm wires come up behind the board
    "J3": (31.4, 3.0, 0, "F"), "J4": (31.4, 5.1, 0, "F"), "J10": (33.0, 3.0, 0, "F"),
    "J11": (33.0, 4.6, 0, "F"), "J12": (33.0, 6.2, 0, "F"), "J9": (31.4, 8.8, 0, "F"),
    "J5": (31.4, 7.2, 0, "F"), "J1": (33.0, 7.8, 0, "F"),
    "J2": (33.0, 9.4, 0, "F"), "J7": (31.4, 10.4, 0, "F"), "J8": (33.0, 11.0, 0, "F"),
    # Rev F: D5 ESD at the J3 contact; TP7 printf dot by PB6 (pin 42), reachable with the lid off
    # C1 (100 nF) serves VDD pin 48 AND VBAT pin 1 (Rev F PER-06): +3V0 pad 0.42 mm from pin 48, 1.02 mm from pin 1 (both <= 1.5)
    "D5": (29.9, 3.2, 90, "F"), "TP7": (13.2, 1.5, 0, "F"),
    # ================= B (inner face, toward the cell)
    # Rev F: MDF mic-fallback dots by the mic on B (TP8 PB8 -> R2's mic-side pad, TP9 PB1 -> TP10 MIC_DATA)
    "TP8": (8.7, 9.4, 0, "B"), "TP9": (8.7, 3.6, 0, "B"), "TP10": (7.3, 3.0, 0, "B"),
    "U2": (4.67, 6.5, 90, "B"), "R2": (7.3, 8.0, 90, "B"), "C13": (7.3, 5.0, 90, "B"),   # ECR-0011: the PORT (0.77 mm off the origin) at (3.9, 6.5) under the lid port
    "R8": (10.0, 2.0, 90, "B"), "R9": (11.0, 2.0, 90, "B"), "C19": (12.0, 2.0, 90, "B"),
    "R15": (20.0, 4.75, 270, "B"), "R16": (18.8, 4.75, 270, "B"), 
    # charger + LDO + dock protection: rear, near the wire pads. Rev F: charger cluster shifted +2.5 mm in x so the MCU's
    # top-right pins (26-38) get a via field between the MCU edge (x 16.5) and U3 instead of landing among its 0.4 mm balls
    "U3": (19.5, 3.0, 0, "B"), "C15": (21.2, 2.2, 90, "B"), "C16": (17.8, 2.2, 90, "B"), "C21": (23.25, 2.0, 0, "B"),
    "RT1": (22.3, 4.3, 90, "B"),
    "R20": (23.4, 11.4, 0, "B"),                     # LDO -> 3V0 link
    "U4": (24.2, 7.4, 0, "B"), "C17": (24.2, 5.9, 0, "B"), "C18": (24.2, 8.9, 0, "B"),
    "R12": (25.3, 2.2, 90, "B"), "R13": (26.9, 2.2, 90, "B"),
    "D4": (27.22, 6.4, 0, "B"), "U6": (26.58, 8.6, 0, "B"),
    "R18": (25.3, 10.4, 90, "B"), "R14": (26.42, 11.8, 0, "B"),
    # H-bridge: rear-middle, far from the mic
    "Q1": (15.8, 8.0, 0, "B"), "Q2": (18.6, 8.0, 0, "B"),
    "R3": (15.5, 6.6, 0, "B"), "R4": (15.5, 9.4, 0, "B"), "R5": (18.9, 6.6, 0, "B"), "R6": (18.9, 9.4, 0, "B"),
    "R21": (21.6, 7.6, 90, "B"),                     # 0.1R 1206 low-side shunt, right behind Q2
    "C14": (17.3, 11.4, 0, "B"), 
}


def gnd_plane(b):
    """Solid GND zone on In1 (layer type 'power' so the Specctra export treats it as a plane)."""
    b.SetLayerType(pcbnew.In1_Cu, pcbnew.LT_POWER)
    net = b.FindNet("GND")
    z = pcbnew.ZONE(b)
    z.SetLayer(pcbnew.In1_Cu)
    z.SetNet(net)
    z.SetLocalClearance(mm(0.2))
    z.SetMinThickness(mm(0.2))
    ol = z.Outline()
    ol.NewOutline()
    for x, y in ((0.3, 0.3), (P.W - 0.3, 0.3), (P.W - 0.3, P.H - 0.3), (0.3, P.H - 0.3)):
        ol.Append(mm(x), mm(y))
    b.Add(z)
    return z


DNP = ()                                             # Rev F: D1/D2 footprints removed (OUT-04)
VIA_D, VIA_DRILL, STUB_W, GAP = 0.35, 0.15, 0.15, 0.12   # mm; GAP = copper clearance kept by the fan-out


def _rect(p):
    bb = p.GetBoundingBox()
    return [pcbnew.ToMM(v) for v in (bb.GetX(), bb.GetY(), bb.GetRight(), bb.GetBottom())]


def _d_rect(x, y, r):
    """Distance from a point to an axis-aligned rectangle (0 inside)."""
    dx = max(r[0] - x, 0, x - r[2]); dy = max(r[1] - y, 0, y - r[3])
    return (dx * dx + dy * dy) ** 0.5


def gnd_fanout(b, fps, inset=0.0):
    """Give every GND pad its own short via down to the In1 plane before routing, so the router never
    spends space on ground. Each via goes outward from its part (then sideways if blocked) and keeps
    GAP from every other net's copper on both faces (vias go through the board) and from other vias.
    The MCU's exposed pad gets a 3 x 3 via grid inside it (thermal + ground). Returns (added, skipped)."""
    gnd = b.FindNet("GND")
    others = [(_rect(p), p) for f in fps.values() for p in f.Pads() if p.GetNetname() != "GND"]   # incl. holes
    vias, added, skipped = [], 0, []
    V = lambda x, y: pcbnew.VECTOR2I(mm(x), mm(y))

    def free(x, y, seg_from=None, layer_pads=None):
        lo = 0.45 + inset
        if not (lo <= x <= P.W - lo and lo <= y <= P.H - lo):
            return False
        if any(((x - vx) ** 2 + (y - vy) ** 2) ** 0.5 < VIA_D + 0.2 for vx, vy in vias):
            return False
        if any(_d_rect(x, y, r) < VIA_D / 2 + GAP for r, _ in others):
            return False
        if seg_from:                                     # the stub track must clear other pads on its layer
            x0, y0 = seg_from
            for k in range(1, 10):
                t = k / 10
                px, py = x0 + (x - x0) * t, y0 + (y - y0) * t
                if any(_d_rect(px, py, r) < STUB_W / 2 + GAP for r, _ in layer_pads):
                    return False
        return True

    def add_via(x, y):
        v = pcbnew.PCB_VIA(b); v.SetPosition(V(x, y)); v.SetWidth(mm(VIA_D)); v.SetDrill(mm(VIA_DRILL))
        v.SetNet(gnd); b.Add(v); vias.append((x, y))

    ep = None
    for p in fps["U1"].Pads():                           # the MCU's exposed pad (GND)
        r = _rect(p)
        if p.GetNetname() == "GND" and min(r[2] - r[0], r[3] - r[1]) > 3:
            ep = r
    for ref, f in fps.items():
        if ref in DNP:
            continue
        fx, fy = (pcbnew.ToMM(c) for c in (f.GetPosition().x, f.GetPosition().y))
        for p in f.Pads():
            if p.GetNetname() != "GND" or p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                continue
            r = _rect(p); cx, cy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
            if ref == "U1" and min(r[2] - r[0], r[3] - r[1]) > 3:        # exposed pad: via grid inside it
                for i in (-1, 0, 1):
                    for j in (-1, 0, 1):
                        add_via(cx + 1.2 * i, cy + 1.2 * j); added += 1
                continue
            layer = pcbnew.B_Cu if f.IsFlipped() else pcbnew.F_Cu
            if ref == "U1" and ep:                       # ring GND pins: straight inward onto the exposed pad
                ex = min(max(cx, ep[0] + 0.3), ep[2] - 0.3); ey = min(max(cy, ep[1] + 0.3), ep[3] - 0.3)
                t = pcbnew.PCB_TRACK(b); t.SetStart(V(cx, cy)); t.SetEnd(V(ex, ey))
                t.SetWidth(mm(STUB_W)); t.SetLayer(layer); t.SetNet(gnd); b.Add(t); added += 1
                continue
            layer_pads = [(rr, pp) for rr, pp in others if pp.IsOnLayer(layer)]
            ox, oy = cx - fx, cy - fy                     # outward from the part's centre
            n = (ox * ox + oy * oy) ** 0.5
            ox, oy = (ox / n, oy / n) if n > 1e-6 else (0.0, 1.0)     # single-pad parts (TP, J): try below first
            dirs = [(ox, oy), (-oy, ox), (oy, -ox), (ox - oy, oy + ox), (ox + oy, oy - ox), (0, -1), (0, 1), (-1, 0), (1, 0)]
            half = max(r[2] - r[0], r[3] - r[1]) / 2
            done = False
            for dx, dy in dirs:
                m = (dx * dx + dy * dy) ** 0.5
                dx, dy = dx / m, dy / m
                for d in (half + VIA_D / 2 + 0.05, half + VIA_D / 2 + 0.25, half + VIA_D / 2 + 0.5):
                    x, y = cx + dx * d, cy + dy * d
                    if free(x, y, (cx, cy), layer_pads):
                        t = pcbnew.PCB_TRACK(b); t.SetStart(V(cx, cy)); t.SetEnd(V(x, y))
                        t.SetWidth(mm(STUB_W)); t.SetLayer(layer); t.SetNet(gnd); b.Add(t)
                        add_via(x, y); added += 1; done = True
                        break
                if done:
                    break
            if not done:
                skipped.append(f"{ref}.{p.GetNumber()}")
    return added, skipped


def build(inset=0.0, fanout=True):
    P.PLACE = PLACE
    b, fps = P.build(inset)
    b.GetDesignSettings().SetBoardThickness(mm(0.8))      # 0.8 mm board (shell PCB y 12.1-12.9, mic port depth; reg-board issue 2)
    for ref in DNP:
        fps[ref].SetDNP(True); fps[ref].SetExcludedFromBOM(True); fps[ref].SetExcludedFromPosFiles(True)
    if fanout:
        added, skipped = gnd_fanout(b, fps, inset)
        if not inset:
            print(f"GND fan-out: {added} vias; no room at: {', '.join(skipped) or 'none'}")
    gnd_plane(b)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    return b, fps


def main(route=True):
    b, fps = build()
    b.BuildConnectivity()
    ov = [o for o in P.courtyard_overlaps(fps) if not (o[0][0] in "JT" and o[1][0] in "JT")]
    clashes = P.pad_clashes(fps)
    print("courtyard overlaps (mm^2):", ov or "none", "| pad clashes:", clashes or "none")
    placed = OUT / "pod_r1_placed.kicad_pcb"
    pcbnew.SaveBoard(str(placed), b)
    summary = {"courtyard_overlaps": ov, "pad_clashes": clashes}
    target = placed
    if route:
        dsn, ses = OUT / "pod_r1.dsn", OUT / "pod_r1.ses"
        br, _ = build(inset=0.2)
        assert pcbnew.ExportSpecctraDSN(br, str(dsn))
        subprocess.run([os.environ["FREEROUTING_JAVA"], *os.environ.get("FREEROUTING_JAVA_OPTS", "-Xmx1g").split(),
                        "-jar", os.environ["FREEROUTING_JAR"], "-de", str(dsn), "-do", str(ses), "-mp", "200",
                        "--gui.enabled=false"], check=True, timeout=3000, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        b = pcbnew.LoadBoard(str(placed))
        assert pcbnew.ImportSpecctraSES(b, str(ses))
        for t in b.GetTracks():
            if t.GetClass() == "PCB_TRACK" and t.GetWidth() < mm(0.1):
                t.SetWidth(mm(0.1))
        pcbnew.ZONE_FILLER(b).Fill(b.Zones())
        b.GetDesignSettings().m_NetSettings.GetDefaultNetclass().SetClearance(mm(0.09))
        target = OUT / "pod_r1_routed.kicad_pcb"
        pcbnew.SaveBoard(str(target), b)
        # silkscreen pass (refs to Fab, pin-1 dots, port motif, name; JLC legend rules): hw/pod/silk.py
        subprocess.run([sys.executable, str(Path(__file__).with_name("silk.py")), str(target)], check=True, stdout=subprocess.DEVNULL)
        drc = OUT / "drc.json"
        subprocess.run(["kicad-cli", "pcb", "drc", "--format", "json", "--severity-error", "--output", str(drc), str(target)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        d = json.loads(drc.read_text())
        kinds = {}
        for v in d.get("violations", []):
            kinds[v["type"]] = kinds.get(v["type"], 0) + 1
        tracks = list(b.GetTracks())
        vias = sum(1 for t in tracks if t.GetClass() == "PCB_VIA")
        summary.update({"tracks": len(tracks) - vias, "vias": vias, "drc_errors": sum(kinds.values()), "by_type": kinds,
                        "unconnected": len(d.get("unconnected_items", []))})
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    for side in ("top", "bottom"):
        subprocess.run(["kicad-cli", "pcb", "render", "--output", str(OUT / f"render_{side}.png"), "--side", side,
                        "--width", "1600", "--height", "900", "--zoom", "2.6", "--quality", "high",
                        "--background", "opaque", str(target)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300)


if __name__ == "__main__":
    main(route="--no-route" not in sys.argv)
