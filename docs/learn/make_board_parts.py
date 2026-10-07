"""Draw every part on the pod board, colour-coded by job, with a legend: docs/learn/04-board-parts.svg

    source tools/env.sh && python3 docs/learn/make_board_parts.py && docs/diagrams/render.sh docs/learn/04-board-parts.svg

Positions come from the draft board (hw/pod/draft/pod_routed.kicad_pcb), so the picture stays true
to the real footprints. The bottom face is drawn as seen from below (flipped left-right).
"""
from pathlib import Path
from xml.sax.saxutils import escape

import pcbnew

REPO = Path(__file__).resolve().parents[2]
BOARD = REPO / "hw/pod/draft/pod_routed.kicad_pcb"
OUT = REPO / "docs/learn/04-board-parts.svg"
W_MM, H_MM = 20.0, 11.5
S = 30.0                                     # px per mm

# group -> (colour, title, one-line job)
GROUPS = {
    "brain":  ("#2a78d6", "1 · Brain", "the MCU and the parts that keep it stable"),
    "clock":  ("#4a3aa7", "2 · Clock", "the timing reference for everything"),
    "core":   ("#008300", "3 · Core power", "the MCU's own 1.1 V switching supply"),
    "ears":   ("#1baf7a", "4 · Ears", "the ultrasonic mic"),
    "voice":  ("#e34948", "5 · Voice", "the H-bridge that drives the transducer"),
    "charge": ("#eda100", "6 · Battery + charging", "fills and holds the cell"),
    "rail":   ("#eb6834", "7 · 3.0 V rail", "the clean supply for everything else"),
    "senses": ("#e87ba4", "8 · Button + battery gauge", "your input, and how full the cell is"),
    "debug":  ("#8a8676", "9 · Programming pads", "how firmware gets in"),
}

# ref -> (group, what it is, why it's needed)
PARTS = {
    "U1": ("brain", "STM32U575 microcontroller", "runs everything: filters the mic, does the FFT, makes the tones, times the PWM"),
    "C1": ("brain", "100 nF", "decoupling: a charge reservoir right at a supply pin, so current spikes don't dip the supply"),
    "C2": ("brain", "100 nF", "decoupling for another VDD pin (one per pin: each pin's spikes are local)"),
    "C3": ("brain", "100 nF", "decoupling for the third VDD pin"),
    "C4": ("brain", "4.7 µF", "bulk store for the whole chip: covers slower dips the 100 nF ones can't"),
    "C5": ("brain", "1 µF", "VDDA (the analog supply): smooths it for the battery-voltage ADC"),
    "C6": ("brain", "100 nF", "VDDA high-frequency decoupling"),
    "C10": ("brain", "100 nF", "on NRST (reset): stops noise from resetting the chip"),
    "R1": ("brain", "10 kΩ", "holds BOOT0 low so the chip starts our program, not ST's bootloader"),
    "Y1": ("clock", "32.768 kHz crystal", "the accurate reference the 80 MHz clock is locked to: both ears then agree on pitch"),
    "C11": ("clock", "15 pF", "crystal load capacitor: sets the exact oscillation frequency"),
    "C12": ("clock", "15 pF", "the other load capacitor"),
    "L1": ("core", "2.2 µH inductor", "the energy store of the chip's built-in buck converter (3.0 → 1.1 V)"),
    "C7": ("core", "10 µF", "buck input capacitor: supplies its 3 MHz current pulses locally"),
    "C8": ("core", "2.2 µF", "buck output capacitor: smooths the 1.1 V core supply"),
    "C9": ("core", "2.2 µF", "second output capacitor (ST requires two)"),
    "U2": ("ears", "SPH0641 MEMS mic", "hears 20–85 kHz; outputs a 1-bit stream at 4 MHz; ports through a hole in the board"),
    "C13": ("ears", "100 nF", "the mic's decoupling: a clean supply means a quiet mic"),
    "R2": ("ears", "33 Ω", "in series with the 4 MHz mic clock: softens its edges so it radiates less"),
    "Q1": ("voice", "PMCXB290UE N+P pair", "one half of the H-bridge: switches transducer end A between 3.0 V and ground"),
    "Q2": ("voice", "PMCXB290UE N+P pair", "the other half: end B. A and B in antiphase = ±3 V across the coil"),
    "R3": ("voice", "100 kΩ", "gate pull-up: keeps Q1's P-FET off while the MCU boots (its pins float at reset)"),
    "R4": ("voice", "100 kΩ", "gate pull-down: keeps Q1's N-FET off at reset (no shoot-through at power-up)"),
    "R5": ("voice", "100 kΩ", "same for Q2's P-FET"),
    "R6": ("voice", "100 kΩ", "same for Q2's N-FET"),
    "D1": ("voice", "ESD diode", "protects the bridge from static on the transducer wire (it touches your skin)"),
    "D2": ("voice", "ESD diode", "same, other wire"),
    "C14": ("voice", "22 µF", "local reservoir for the bridge's current peaks, so they don't pull the 3.0 V rail down"),
    "J1": ("voice", "wire pad", "transducer wire A"),
    "J2": ("voice", "wire pad", "transducer wire B"),
    "U3": ("charge", "MCP73831 charger", "charges the LiPo safely: constant current, then constant 4.2 V, then stops"),
    "R7": ("charge", "22 kΩ", "sets the charge current: 1000 V / 22 kΩ = 45 mA (gentle for a 105 mAh cell)"),
    "C15": ("charge", "4.7 µF", "charger input capacitor"),
    "C16": ("charge", "4.7 µF", "charger output / battery-side capacitor"),
    "D3": ("charge", "ESD / TVS diode", "clamps static and reverse polarity on the exposed charge contacts"),
    "J3": ("charge", "wire pad", "charge contact + (5 V from the dock)"),
    "J4": ("charge", "wire pad", "charge contact − (ground)"),
    "J5": ("charge", "wire pad", "battery +"),
    "J6": ("charge", "wire pad", "battery −"),
    "U4": ("rail", "TPS7A2030 LDO", "turns 3.3–4.2 V from the cell into a steady 3.0 V, very quietly (7 µV noise)"),
    "C17": ("rail", "1 µF", "LDO input capacitor"),
    "C18": ("rail", "1 µF", "LDO output capacitor: it needs one to stay stable"),
    "R8": ("senses", "1 MΩ", "top of a divider: halves the battery voltage so the ADC can read it"),
    "R9": ("senses", "1 MΩ", "bottom of the divider (2 µA total drain)"),
    "C19": ("senses", "100 nF", "holds the divider's voltage steady while the ADC samples it"),
    "SW1": ("senses", "push button", "volume, mode, wake from sleep"),
    "R10": ("senses", "2.2 kΩ", "holds the button line low until pressed, so it never reads a phantom press"),
    "TP1": ("debug", "SWDIO pad", "debug data line: program and single-step the chip"),
    "TP2": ("debug", "SWCLK pad", "debug clock"),
    "TP3": ("debug", "NRST pad", "reset, for the programmer"),
    "TP4": ("debug", "3V0 pad", "lets the programmer sense the supply"),
    "TP5": ("debug", "GND pad", "common ground for the programmer"),
}


def rect(x, y, w, h, fill, op=1.0, stroke="none", sw=0, rx=0):
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}" fill-opacity="{op}" stroke="{stroke}" stroke-width="{sw}"/>'


def draw_side(fps, bottom, ox, oy):
    """Return SVG for one face. Bottom is mirrored left-right (seen from below)."""
    out = [rect(ox, oy, W_MM * S, H_MM * S, "#1f4a33", rx=S)]
    X = (lambda x: ox + (W_MM - x) * S) if bottom else (lambda x: ox + x * S)
    Y = lambda y: oy + y * S
    for f in fps:
        if f.IsFlipped() != bottom:
            continue
        ref = f.GetReference()
        grp = PARTS[ref][0]
        col = GROUPS[grp][0]
        la = pcbnew.B_CrtYd if bottom else pcbnew.F_CrtYd
        cy = f.GetCourtyard(la)
        bb = cy.BBox() if cy.OutlineCount() else f.GetBoundingBox(False)
        x0, x1 = sorted((X(pcbnew.ToMM(bb.GetX())), X(pcbnew.ToMM(bb.GetRight()))))
        y0, y1 = Y(pcbnew.ToMM(bb.GetY())), Y(pcbnew.ToMM(bb.GetBottom()))
        out.append(rect(x0, y0, x1 - x0, y1 - y0, col, 0.55, col, 1.5, 3))
        for p in f.Pads():
            if p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                continue                      # holes are drawn last, on both faces
            pb = p.GetBoundingBox()
            px0, px1 = sorted((X(pcbnew.ToMM(pb.GetX())), X(pcbnew.ToMM(pb.GetRight()))))
            out.append(rect(px0, Y(pcbnew.ToMM(pb.GetY())), px1 - px0, pcbnew.ToMM(pb.GetHeight()) * S, "#d9b36a", 0.9))
        c = f.GetPosition()
        fs = 15 if ref == "U1" else 11
        out.append(f'<text x="{X(pcbnew.ToMM(c.x)):.1f}" y="{Y(pcbnew.ToMM(c.y)) + 4:.1f}" font-size="{fs}" font-weight="700" '
                   f'text-anchor="middle" fill="#ffffff" stroke="#000000" stroke-width="2.6" paint-order="stroke">{ref}</text>')
    for f in fps:                             # through-holes (the mic port) show on both faces
        for p in f.Pads():
            if p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                c = p.GetPosition()
                out.append(f'<circle cx="{X(pcbnew.ToMM(c.x)):.1f}" cy="{Y(pcbnew.ToMM(c.y)):.1f}" r="{0.4 * S:.1f}" fill="#000000" stroke="#ffffff" stroke-width="1.5"/>')
    return "\n".join(out)


def main():
    b = pcbnew.LoadBoard(str(BOARD))
    fps = list(b.GetFootprints())
    assert set(f.GetReference() for f in fps) == set(PARTS), "legend and board disagree"
    Wpx = 1500
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {Wpx} 1560" font-family="Helvetica, Arial, sans-serif" '
             f'role="img" aria-label="Every part on the pod board, colour-coded by function, on both faces, with a legend explaining what each part is and why it is needed.">',
             rect(0, 0, Wpx, 1560, "#fbfaf7", rx=14),
             '<text x="36" y="42" font-size="22" font-weight="700" fill="#1f2328">Every part on the pod board, and why it is there</text>',
             '<text x="36" y="68" font-size="14" fill="#57606a">20 × 11.5 mm, drawn 30× from the draft board file. Colour = job. Gold = copper pads. '
             'Front of the pod (toward your eye) is on the left of the outer face and the right of the inner face.</text>']
    oy = 110
    parts.append('<text x="60" y="100" font-size="15" font-weight="700" fill="#1f2328">Outer face (toward the pod wall)</text>')
    parts.append('<text x="800" y="100" font-size="15" font-weight="700" fill="#1f2328">Inner face (toward the cell), seen from below</text>')
    parts.append(draw_side(fps, False, 60, oy))
    parts.append(draw_side(fps, True, 800, oy))
    parts.append('<text x="1400" y="512" font-size="12" text-anchor="end" fill="#57606a">black dot, both faces = the mic sound port: a hole straight through the board</text>')
    # legend, 3 columns of groups
    cols = [["brain", "clock", "core"], ["ears", "voice"], ["charge", "rail", "senses", "debug"]]
    colx = [36, 530, 1010]
    colw = [470, 460, 470]
    for ci, glist in enumerate(cols):
        y = 548
        for g in glist:
            col, title, job = GROUPS[g]
            parts.append(rect(colx[ci], y - 14, 16, 16, col, 0.8, rx=3))
            parts.append(f'<text x="{colx[ci] + 24}" y="{y}" font-size="14.5" font-weight="700" fill="#1f2328">{escape(title)}</text>')
            parts.append(f'<text x="{colx[ci] + 24}" y="{y + 18}" font-size="12" fill="#57606a">{escape(job)}</text>')
            y += 40
            for ref, (gg, what, why) in PARTS.items():
                if gg != g:
                    continue
                parts.append(f'<text x="{colx[ci] + 24}" y="{y}" font-size="12" fill="#1f2328"><tspan font-weight="700">{ref}</tspan>  {escape(what)}</text>')
                # wrap the "why" to the column width
                words, line, lines = why.split(), "", []
                for w_ in words:
                    if len(line) + len(w_) + 1 > colw[ci] // 6.4:
                        lines.append(line); line = w_
                    else:
                        line = (line + " " + w_).strip()
                lines.append(line)
                for ln in lines:
                    y += 15
                    parts.append(f'<text x="{colx[ci] + 40}" y="{y}" font-size="11.5" fill="#57606a">{escape(ln)}</text>')
                y += 19
            y += 10
    parts.append("</svg>")
    OUT.write_text("\n".join(parts))
    print(OUT)


if __name__ == "__main__":
    main()
