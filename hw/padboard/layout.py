"""Pad board DRAFT layout (pcbnew API, no autorouter): proves the 5.0 x 9.3 mm board holds the LED,
four arm-wire pads and two transducer-lead holes with hand-solderable gaps, then runs DRC.

    F="systemd-run --user --scope --quiet -p MemoryMax=2G -p MemorySwapMax=0"
    source tools/env.sh && cd hw/padboard
    $F python3 layout.py                                      # -> padboard.kicad_pcb (+ .kicad_pro)
    $F kicad-cli pcb drc --format json --severity-all --units mm -o drc.json padboard.kicad_pcb
    $F python3 layout.py --summary                            # -> drc_summary.json

KiCad coordinates (mm, origin = board centre, offset to (100, 100) on the sheet), viewed from the
LED face (the face pointing OUT of the pad, away from the skin):
    KiCad x = -e1 (across the pad; e1 = frame.E1)   KiCad y = -e3 (y negative = the TOP end, where
    the arm wires arrive; e3 = frame.E3, the pad's long axis, up-forward).
Board e3 range is frame.PAD_BOARD e3_0..e3_1 = -4.0..+5.3, so KiCad y = -5.3 (top) .. +4.0 (bottom).
The layout is mirror-symmetric in x, so the SAME board fits the left pad (turned over about its
long axis there; wires follow the silk labels, not the positions). See docs/research/pcb-mech-interface.md.
The owner may redraw this; it is a placement proof, not a release.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pcbnew

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "hw/mech"))
import frame  # noqa: E402

PB = frame.PAD_BOARD
W, E3_0, E3_1, T = PB["w"], PB["e3_0"], PB["e3_1"], PB["t"]
Y_TOP, Y_BOT = -E3_1, -E3_0           # -5.3, +4.0
OX, OY = 100.0, 100.0
mm = pcbnew.FromMM

# ref: (x, y, rot, footprint lib, footprint name, net)
# 2026-09-30 rev: positions agreed with the pad cap (hw/mech/pad.py, pad agent's request):
#  - all four arm pads in ONE row at the top end (KiCad y -4.0), under the strut's channel exit;
#    each SMD lap reaches >= 1.0 mm outside the cap's epoxy dam (r 3.25 = ring 5.3/2 + 0.6 wall);
#  - transducer holes at (+-1.775, 3.275), pad 0.85: inner edge r 3.30 (clears the dam by 0.05)
#    and copper 0.30 from both the long edge and the bottom edge (pad agent asked (+-1.85, 3.25)
#    with a 0.9 pad, which leaves only 0.20 mm to the long edge = JLC's bare minimum).
XDCR_X, XDCR_Y = 1.775, 3.275
PLACE = {
    "J1": (-1.725, -4.0, 0, "padboard", "WirePad_SMD_0.7x1.8mm", "OUT_A"),
    "J2": (+1.725, -4.0, 0, "padboard", "WirePad_SMD_0.7x1.8mm", "OUT_B"),
    "J3": (-0.575, -4.0, 0, "padboard", "WirePad_SMD_0.7x1.8mm", "LED_A"),
    "J4": (+0.575, -4.0, 0, "padboard", "WirePad_SMD_0.7x1.8mm", "LED_K"),
    "J5": (-1.775, +3.275, 0, "padboard", "WirePad_PTH_D0.45mm_Pad0.85mm", "OUT_A"),
    "J6": (+1.775, +3.275, 0, "padboard", "WirePad_PTH_D0.45mm_Pad0.85mm", "OUT_B"),
    "D1": (0.0, 0.0, 180, "LED_SMD", "LED_0402_1005Metric", None),    # pad 1 (K) -> +x, pad 2 (A) -> -x
}
LED_PADS = {"1": "LED_K", "2": "LED_A"}
# silk: arm labels just below their pads (the wire arrives from the top edge); transducer labels inboard
SILK = [("A", -1.725, -2.45), ("B", 1.725, -2.45), ("+", -0.575, -2.45), ("-", 0.575, -2.45),
        ("A", -0.95, 3.275), ("B", 0.95, 3.275)]
# tracks: (net, width, [points])
TRACKS = [
    ("OUT_A", 0.30, [(-1.725, -3.1), (-1.725, 2.95), (-1.775, 3.275)]),
    ("OUT_B", 0.30, [(1.725, -3.1), (1.725, 2.95), (1.775, 3.275)]),
    ("LED_A", 0.20, [(-0.575, -3.1), (-0.575, -0.6), (-0.485, -0.3), (-0.485, 0.0)]),
    ("LED_K", 0.20, [(0.575, -3.1), (0.575, -0.6), (0.485, -0.3), (0.485, 0.0)]),
]
LIBS = {"padboard": str(HERE / "padboard.pretty"), "LED_SMD": "/usr/share/kicad/footprints/LED_SMD.pretty"}


def P(x, y):
    return pcbnew.VECTOR2I(mm(OX + x), mm(OY + y))


def build():
    b = pcbnew.BOARD()
    ds = b.GetDesignSettings()
    ds.SetBoardThickness(mm(T))
    ds.m_CopperEdgeClearance = mm(0.3)     # JLC routed edge minimum is 0.2 mm (capabilities page, 2026-09-30)
    b.SetCopperLayerCount(2)
    nets = {}
    for n in ("OUT_A", "OUT_B", "LED_A", "LED_K"):
        ni = pcbnew.NETINFO_ITEM(b, n)
        b.Add(ni)
        nets[n] = ni
    for ref, (x, y, rot, lib, name, net) in PLACE.items():
        fp = pcbnew.FootprintLoad(LIBS[lib], name)
        fp.SetFPID(pcbnew.LIB_ID(lib, name))
        fp.SetReference(ref)
        fp.Reference().SetVisible(False)
        fp.Value().SetVisible(False)
        b.Add(fp)
        fp.SetPosition(P(x, y))
        fp.SetOrientationDegrees(rot)
        for pad in fp.Pads():
            pad.SetNet(nets[LED_PADS[pad.GetNumber()]] if ref == "D1" else nets[net])
    # outline: 5.0 x 9.3 rectangle
    corners = [(-W / 2, Y_TOP), (W / 2, Y_TOP), (W / 2, Y_BOT), (-W / 2, Y_BOT)]
    for (x0, y0), (x1, y1) in zip(corners, corners[1:] + corners[:1]):
        s = pcbnew.PCB_SHAPE(b)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(P(x0, y0)); s.SetEnd(P(x1, y1))
        s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.05))
        b.Add(s)
    for net, w, pts in TRACKS:
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(P(x0, y0)); t.SetEnd(P(x1, y1))
            t.SetWidth(mm(w)); t.SetLayer(pcbnew.F_Cu); t.SetNet(nets[net])
            b.Add(t)
    for txt, x, y in SILK:
        t = pcbnew.PCB_TEXT(b)
        t.SetText(txt); t.SetPosition(P(x, y)); t.SetLayer(pcbnew.F_SilkS)
        t.SetTextSize(pcbnew.VECTOR2I(mm(0.8), mm(0.8))); t.SetTextThickness(mm(0.15))
        b.Add(t)
    t = pcbnew.PCB_TEXT(b)
    t.SetText("PAD r1"); t.SetPosition(P(0, 0.9)); t.SetLayer(pcbnew.B_SilkS); t.SetMirrored(True)
    t.SetTextSize(pcbnew.VECTOR2I(mm(0.8), mm(0.8))); t.SetTextThickness(mm(0.15))
    b.Add(t)
    return b


def main():
    b = build()
    out = HERE / "padboard.kicad_pcb"
    b.Save(str(out))
    # The two library-parity checks make kicad-cli load EVERY global footprint library (>2 GB RSS,
    # killed by the 2 GB fence on 2026-09-30). This board's footprints come from padboard.pretty and
    # KiCad's LED_SMD, written fresh by this script, so parity is moot: switch those two checks off.
    pro = HERE / "padboard.kicad_pro"
    d = json.loads(pro.read_text())
    rs = d["board"]["design_settings"]["rule_severities"]
    rs["lib_footprint_issues"] = rs["lib_footprint_mismatch"] = "ignore"
    pro.write_text(json.dumps(d, indent=2))
    for lck in HERE.glob("~*.lck"):
        lck.unlink()
    print("saved", out.name, "- now run DRC as its own fenced step (see module docstring)")


def summarize():
    """Read drc.json (written by kicad-cli in a separate fenced process: kicad-cli alone peaks at
    ~2.1 GB RSS on this machine, so it must not share a 2 GB fence with the pcbnew Python process)."""
    rep = json.loads((HERE / "drc.json").read_text())
    viol = [(v["type"], v["severity"], v["description"]) for v in rep.get("violations", [])]
    unc = rep.get("unconnected_items", [])
    summary = {"violations": len(viol), "errors": sum(1 for v in viol if v[1] == "error"),
               "unconnected": len(unc), "types": sorted({v[0] for v in viol})}
    (HERE / "drc_summary.json").write_text(json.dumps({"summary": summary, "violations": viol}, indent=1))
    print(json.dumps(summary))


if __name__ == "__main__":
    summarize() if "--summary" in sys.argv else main()
