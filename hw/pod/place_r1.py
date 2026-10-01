"""Rev-1 board ROUGH DRAFT: 28 x 13 mm, 4 layers, parts on both faces, from pod.net (Rev E).

    source tools/env.sh && systemd-run --user --scope --quiet -p MemoryMax=4G -p MemorySwapMax=0 \
        python3 hw/pod/place_r1.py [--no-route]      # -> hw/pod/draft_r1/*

A first pass to prove fit and get a picture of the layout; the real 4-layer board is laid out
together with the owner (spec O14). Floorplan: docs/diagrams/pcb-floorplan-rev1.svg.
Coordinates: x = 0 at the front (mic end) running back; y = 0 at the top edge; centre line y = 6.5.
F (top) faces the lid (outer wall), B faces the cell. Layer 2 (In1) is a solid GND plane.
Mic port (board x 3.9) and switch (board x 22.0) are on the centre line so one board fits both pods;
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
P.W, P.H, P.CORNER = 28.0, 13.0, 1.0           # outline() reads these module globals
OUT = HERE / "draft_r1"
OUT.mkdir(exist_ok=True)
mm = pcbnew.FromMM

PLACE = {
    # ================= F (outer face): MCU in the middle, quiet strip at the front, SMPS + switch behind it
    "U1": (13.0, 6.5, 0, "F"),
    "Y1": (6.6, 4.2, 90, "F"), "C11": (8.3, 3.28, 90, "F"), "C12": (8.3, 5.58, 90, "F"),
    "C10": (8.3, 7.88, 90, "F"), "C5": (8.3, 10.18, 90, "F"), "C6": (7.3, 10.18, 90, "F"), "C1": (7.3, 7.88, 90, "F"),
    "C20": (9.6, 1.6, 0, "F"),
    "C3": (17.6, 3.51, 90, "F"), "C4": (18.8, 3.51, 90, "F"), "C7": (18.0, 6.5, 90, "F"),
    "C2": (17.6, 9.49, 90, "F"), "C8": (17.6, 11.5, 0, "F"), "L1": (20.4, 10.64, 0, "F"), "C9": (20.3, 8.57, 0, "F"),
    "R1": (17.0, 1.6, 0, "F"),
    "C22": (10.6, 11.6, 0, "F"), "R22": (12.6, 11.6, 0, "F"),   # 16 kHz I_SENSE filter right under PA6 (pin 16)
    "SW1": (22.0, 6.5, 0, "F"), "R10": (23.0, 9.5, 0, "F"),
    # test pads along the top edge (outside the 0.6 mm clamp band), wire pads in two rear columns
    "TP1": (20.6, 1.4, 0, "F"), "TP2": (22.0, 1.4, 0, "F"), "TP3": (23.4, 1.4, 0, "F"),
    "TP4": (24.8, 1.4, 0, "F"), "TP5": (26.2, 1.4, 0, "F"),
    # Rev E test pads in the free front strip (clear of the mic port at x 3.9, y 6.5); mic pads by the mic
    "TP6": (1.6, 1.4, 0, "F"), "TP7": (3.1, 1.4, 0, "F"), "TP10": (4.6, 1.4, 0, "F"),
    "TP8": (1.6, 11.6, 0, "F"), "TP9": (3.1, 11.6, 0, "F"), "TP11": (4.6, 11.6, 0, "F"),
    "J3": (24.9, 3.4, 0, "F"), "J4": (24.9, 5.0, 0, "F"), "J10": (24.9, 6.6, 0, "F"),
    "J11": (24.9, 8.2, 0, "F"), "J12": (24.9, 9.8, 0, "F"), "J9": (24.9, 11.4, 0, "F"),
    "J5": (26.6, 3.4, 0, "F"), "J6": (26.6, 5.0, 0, "F"), "J1": (26.6, 6.6, 0, "F"),
    "J2": (26.6, 8.2, 0, "F"), "J7": (26.6, 9.8, 0, "F"), "J8": (26.6, 11.4, 0, "F"),
    # ================= B (inner face, toward the cell)
    "U2": (3.9, 6.5, 90, "B"), "R2": (6.6, 8.0, 90, "B"), "C13": (6.6, 5.0, 90, "B"),
    "R8": (10.0, 2.0, 90, "B"), "R9": (11.0, 2.0, 90, "B"), "C19": (12.0, 2.0, 90, "B"),
    "R11": (10.5, 11.2, 90, "B"), "R15": (12.0, 11.2, 90, "B"), "R16": (13.5, 11.2, 90, "B"), "R17": (15.0, 11.2, 90, "B"),
    # charger + LDO + dock protection: rear, near the wire pads
    "U3": (17.0, 3.0, 0, "B"), "C15": (15.3, 2.2, 90, "B"), "C16": (18.7, 2.2, 90, "B"), "C21": (17.0, 4.9, 0, "B"),
    "RT1": (19.8, 4.6, 90, "B"),
    "R20": (21.4, 10.1, 0, "B"),                     # LDO -> 3V0 link
    "U4": (21.4, 7.4, 0, "B"), "C17": (21.4, 5.9, 0, "B"), "C18": (21.4, 8.9, 0, "B"),
    "R12": (23.0, 2.2, 90, "B"), "R13": (24.0, 2.2, 90, "B"),
    "D3": (23.6, 4.6, 0, "B"), "D4": (24.2, 6.4, 0, "B"), "U6": (23.8, 8.6, 0, "B"),
    "R18": (23.0, 10.4, 90, "B"), "R19": (24.4, 10.4, 90, "B"), "R14": (23.7, 11.8, 0, "B"),
    # H-bridge: rear-middle, far from the mic
    "Q1": (15.8, 8.0, 0, "B"), "Q2": (18.6, 8.0, 0, "B"),
    "R3": (15.5, 6.6, 0, "B"), "R4": (15.5, 9.4, 0, "B"), "R5": (18.9, 6.6, 0, "B"), "R6": (18.9, 9.4, 0, "B"),
    "R21": (17.2, 8.0, 90, "B"),                     # 0.33R low-side shunt between the legs
    "C14": (17.3, 11.4, 0, "B"), "D1": (16.0, 10.3, 0, "B"), "D2": (19.6, 10.3, 0, "B"),
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


def build(inset=0.0):
    P.PLACE = PLACE
    b, fps = P.build(inset)
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
