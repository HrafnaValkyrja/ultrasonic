"""Pad board: schematic source of truth (SKiDL 2.3, KiCad 10 mode). One per pad, same board both sides.

    source tools/env.sh && python3 hw/padboard/footprints.py   # footprint library (once)
    source tools/env.sh && python3 hw/padboard/gen.py          # -> padboard.net, bom_jlc.csv, erc.txt

What it is (owner O8, docs/research/pad-led.md; frame.PAD_BOARD): a 5.0 x 9.3 x 0.8 mm board that
sits on top of the transducer inside the pad's cap. It is the junction where the four arm wires
meet the transducer's two leads, and it carries the power-indicator LED.

  arm wire OUT_A  -> J1 --+-- J5 -> transducer lead A
  arm wire OUT_B  -> J2 --+-- J6 -> transducer lead B
  arm wire LED+   -> J3 ----- D1 anode     (R14 2k2 from VBAT sits on the POD board, not here)
  arm wire LED-   -> J4 ----- D1 cathode   (to PB7 on the pod board)

D1 = Everlight 16-213/BHC-AN1P2/3T: a blue 0402 (1.0 x 0.5 x 0.45 mm) chip LED, InGaN die
(datasheet DSE-0008890 Rev 3, 29 May 2013). JLC C131223, Extended, 25,783 in stock, $0.0291
(JLC parts API, 2026-10-01T00:01Z). ESD rating only 150 V HBM: handle the arm wires grounded.
Polarity: KiCad's LED symbol/footprint use pad 1 = cathode (K), pad 2 = anode (A); the Everlight
drawing numbers the anode "1". Check the cathode mark against the footprint's pad 1 in JLC's
placement preview. Pads J1..J6 are copper only (no BOM line). Change this file, never the netlist.
"""
from __future__ import annotations

import builtins
import csv
from pathlib import Path

import skidl
from skidl import Net, Part, generate_netlist

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
skidl.set_default_tool(skidl.KICAD10)

ARM_FP = "padboard:WirePad_SMD_0.7x1.8mm"
XDCR_FP = "padboard:WirePad_PTH_D0.45mm_Pad0.85mm"
LED_FP = "LED_SMD:LED_0402_1005Metric"

# ref, label (silkscreen), net, footprint. Positions live in layout.py (x across, y along the board).
PADS = [
    ("J1", "OUT_A", "OUT_A", ARM_FP),
    ("J2", "OUT_B", "OUT_B", ARM_FP),
    ("J3", "LED+", "LED_A", ARM_FP),
    ("J4", "LED-", "LED_K", ARM_FP),
    ("J5", "XDCR_A", "OUT_A", XDCR_FP),
    ("J6", "XDCR_B", "OUT_B", XDCR_FP),
]
LED = dict(ref="D1", lcsc="C131223", mpn="16-213/BHC-AN1P2/3T", value="BLUE_0402")


def build():
    nets = {n: Net(n) for n in ("OUT_A", "OUT_B", "LED_A", "LED_K")}
    for ref, label, net, fp in PADS:
        p = Part("Connector", "TestPoint", value=label, footprint=fp, ref=ref, tag=ref)
        p.fields["DNP_BOM"] = "pad"            # copper only, nothing to place
        nets[net] += p[1]
    d = Part("Device", "LED", value=LED["value"], footprint=LED_FP, ref=LED["ref"], tag=LED["ref"])
    d.fields["LCSC"] = LED["lcsc"]
    d.fields["MPN"] = LED["mpn"]
    nets["LED_A"] += d["A"]
    nets["LED_K"] += d["K"]
    return nets


def bom():
    rows = {}
    for p in builtins.default_circuit.parts:
        if "DNP_BOM" in p.fields:
            continue
        rows.setdefault((p.value, p.footprint, p.fields.get("LCSC", "")), []).append(p.ref)
    with open(HERE / "bom_jlc.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #", "Qty"])
        for (val, fp, lcsc), refs in sorted(rows.items()):
            w.writerow([val, ",".join(sorted(refs)), fp.split(":")[-1], lcsc, len(refs)])
    return sum(len(v) for v in rows.values())


def connectivity():
    """Return {net: sorted pin list}, read back from the circuit (used by layout.py and checks)."""
    out = {}
    for n in builtins.default_circuit.nets:
        pins = sorted(f"{p.part.ref}.{p.num}" for p in n.pins)
        if pins:
            out[n.name] = pins
    return out


if __name__ == "__main__":
    build()
    skidl.ERC()
    generate_netlist(file_=str(HERE / "padboard.net"))
    n = bom()
    conn = connectivity()
    for k in sorted(conn):
        print(f"  {k:6s} {' '.join(conn[k])}")
    print(f"BOM: {n} placed part(s); pads: {len(PADS)}")
