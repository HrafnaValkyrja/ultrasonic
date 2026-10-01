"""Hand-solder wire-pad footprints for the pad board and (proposed) for the pod board's J1..J8.

    source tools/env.sh && python3 hw/padboard/footprints.py     # -> hw/padboard/padboard.pretty/*.kicad_mod

Why custom: the pod board's J1..J8 use TestPoint_Pad_D1.0mm, a 1.0 mm round test pad. A round
1 mm pad gives a 0.25-0.3 mm wire only ~1 mm of lap, and at the frame's 1.3 mm pitch leaves a
0.3 mm gap: easy to bridge by hand, easy to peel. These pads are long in the wire's direction,
keep paste on them (JLC's reflow pre-tins them, so a wire is tacked with no extra solder), and
carry a silk tick at the end the wire comes from. docs/research/pcb-mech-interface.md section 4.
"""
from __future__ import annotations

import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIB = HERE / "padboard.pretty"


def _u():
    return str(uuid.uuid4())


def _prop(name, value, y, layer, hide=False):
    h = "\n\t\t(hide yes)" if hide else ""
    return f"""	(property "{name}" "{value}"
		(at 0 {y:.3f} 0)
		(layer "{layer}"){h}
		(uuid "{_u()}")
		(effects (font (size 0.5 0.5) (thickness 0.08)))
	)
"""


def _line(x0, y0, x1, y1, layer, w):
    return f"""	(fp_line (start {x0:.3f} {y0:.3f}) (end {x1:.3f} {y1:.3f})
		(stroke (width {w}) (type solid)) (layer "{layer}") (uuid "{_u()}"))
"""


def _rect(x0, y0, x1, y1, layer, w):
    return f"""	(fp_rect (start {x0:.3f} {y0:.3f}) (end {x1:.3f} {y1:.3f})
		(stroke (width {w}) (type solid)) (fill no) (layer "{layer}") (uuid "{_u()}"))
"""


def footprint(name, descr, pad, courtyard, silk="", smd=True):
    attr = "(attr smd exclude_from_bom)" if smd else "(attr through_hole exclude_from_bom)"
    cx0, cy0, cx1, cy1 = courtyard
    return f"""(footprint "{name}"
	(version 20260206)
	(generator "padboard_footprints.py")
	(generator_version "10.0")
	(layer "F.Cu")
	(descr "{descr}")
	(tags "wire pad hand solder")
{_prop("Reference", "REF**", cy0 - 0.45, "F.SilkS")}{_prop("Value", name, cy1 + 0.45, "F.Fab")}	{attr}
{_rect(cx0, cy0, cx1, cy1, "F.CrtYd", 0.05)}{silk}{pad}	(embedded_fonts no)
)
"""


def smd_wire_pad(w, L, tick=True):
    """Wire runs along -y (it arrives from the top of the footprint). Pad w (across) x L (along)."""
    name = f"WirePad_SMD_{w:.1f}x{L:.1f}mm"
    pad = f"""	(pad "1" smd roundrect
		(at 0 0)
		(size {w} {L})
		(layers "F.Cu" "F.Mask" "F.Paste")
		(roundrect_rratio 0.25)
		(uuid "{_u()}")
	)
"""
    silk = _line(-w / 2 - 0.15, -L / 2 - 0.15, w / 2 + 0.15, -L / 2 - 0.15, "F.SilkS", 0.1) if tick else ""
    m = 0.1
    descr = (f"Hand-soldered wire pad {w} x {L} mm, long axis along the wire; paste kept so reflow pre-tins it. "
             f"Silk tick = the end the wire arrives from.")
    return name, footprint(name, descr, pad, (-w / 2 - m, -L / 2 - 0.3, w / 2 + m, L / 2 + m), silk)


def pth_wire_pad(drill, dia):
    name = f"WirePad_PTH_D{drill:.2f}mm_Pad{dia:.2f}mm"
    pad = f"""	(pad "1" thru_hole circle
		(at 0 0)
		(size {dia} {dia})
		(drill {drill})
		(layers "*.Cu" "*.Mask")
		(remove_unused_layers no)
		(uuid "{_u()}")
	)
"""
    r = dia / 2 + 0.1
    descr = (f"Plated wire/lead hole, drill {drill} mm, pad {dia} mm (annular {(dia - drill) / 2:.2f} mm; "
             f"JLC min 0.15, recommended 0.20). Lead goes through and is soldered on the far side.")
    return name, footprint(name, descr, pad, (-r, -r, r, r), smd=False)


def probe_pad(w, L):
    """SWD pogo-probe landing for a 1.27 mm pitch probe: no paste (keeps the pad flat for a pogo tip)."""
    name = f"ProbePad_{w:.1f}x{L:.1f}mm"
    pad = f"""	(pad "1" smd roundrect
		(at 0 0)
		(size {w} {L})
		(layers "F.Cu" "F.Mask")
		(roundrect_rratio 0.25)
		(uuid "{_u()}")
	)
"""
    descr = f"Pogo-probe landing {w} x {L} mm, no paste (flat ENIG/HASL surface), for a 1.27 mm pitch probe row."
    return name, footprint(name, descr, pad, (-w / 2 - 0.1, -L / 2 - 0.1, w / 2 + 0.1, L / 2 + 0.1))


FOOTPRINTS = {
    # pad board (this folder's gen.py)
    "arm": smd_wire_pad(0.7, 1.8),            # 4 arm conductors, 0.25-0.3 mm OD PTFE wire
    # transducer leads: up through the board from below, soldered on top. 0.85 pad / 0.45 drill so the
    # pad clears the pad cap's epoxy dam (r 3.25, hw/mech/pad.py) AND keeps 0.3 mm copper to the edge
    "xdcr": pth_wire_pad(0.45, 0.85),
    # pod board proposals for J1..J8 (docs/research/pcb-mech-interface.md section 4)
    "pod_P1": smd_wire_pad(0.9, 1.9),         # single column at 1.3 mm pitch, 0.4 mm gap
    "pod_P2": smd_wire_pad(1.0, 1.6),         # two staggered columns, 2.6 mm pitch per column (recommended)
    "pod_P3": pth_wire_pad(0.45, 0.90),       # two staggered rows of plated holes (strongest)
    "swd": probe_pad(0.8, 1.4),               # TP1..TP5 at 1.27 mm pitch
}


def main():
    LIB.mkdir(exist_ok=True)
    keep = {f"{name}.kicad_mod" for name, _ in FOOTPRINTS.values()}
    for f in LIB.glob("*.kicad_mod"):          # drop footprints this script no longer defines
        if f.name not in keep:
            f.unlink()
    for name, text in FOOTPRINTS.values():
        (LIB / f"{name}.kicad_mod").write_text(text)
    (HERE / "fp-lib-table").write_text(
        '(fp_lib_table\n\t(version 7)\n\t(lib (name "padboard")(type "KiCad")(uri "${KIPRJMOD}/padboard.pretty")'
        '(options "")(descr "hand-solder wire pads"))\n)\n')
    print("wrote", sorted(n for n, _ in FOOTPRINTS.values()))


if __name__ == "__main__":
    main()
