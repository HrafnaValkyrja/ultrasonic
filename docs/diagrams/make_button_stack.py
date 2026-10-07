#!/usr/bin/env python3
"""Dimensioned button-stack section (sub-ui issue 10) generated from hw/mech/dims_r2.py, so it follows the CAD.

    python3 docs/diagrams/make_button_stack.py      # -> docs/diagrams/button-stack.svg (then render.sh for the PNG)

Section through SW1's axis (pod x-y plane, lid up). Scale 110 px/mm vertically and horizontally.
Colours are the docs/diagrams palette that darken.py maps for dark mode.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "hw/mech"))
import dims_r2 as D  # noqa: E402

S = 110.0                  # px per mm
X0, YB = 500.0, 440.0      # svg x of the switch axis; svg y of board B face (pod y = Y_B)
INK, MUTED, BLUE, ORANGE, GREEN, RED = "#1f2328", "#57606a", "#2a78d6", "#b8520a", "#1a7a55", "#e34948"


def sy(y):                 # pod y (mm) -> svg y
    return YB - (y - D.Y_B) * S


def box(x0, x1, y0, y1, fill, stroke, extra=""):
    return (f'<rect x="{X0 + x0 * S:.1f}" y="{sy(y1):.1f}" width="{(x1 - x0) * S:.1f}" height="{(y1 - y0) * S:.1f}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="1.5" {extra}/>')


def label(x, y, text, col=INK, size=14, anchor="start", weight="normal"):
    return f'<text x="{x:.1f}" y="{y:.1f}" fill="{col}" font-size="{size}" text-anchor="{anchor}" font-weight="{weight}">{text}</text>'


def dim(y0, y1, x, text, col=MUTED):
    a, b = sy(y0), sy(y1)
    return (f'<line x1="{x}" y1="{a:.1f}" x2="{x}" y2="{b:.1f}" stroke="{col}" stroke-width="1"/>'
            f'<line x1="{x - 6}" y1="{a:.1f}" x2="{x + 6}" y2="{a:.1f}" stroke="{col}"/>'
            f'<line x1="{x - 6}" y1="{b:.1f}" x2="{x + 6}" y2="{b:.1f}" stroke="{col}"/>'
            + label(x + 10, (a + b) / 2 + 5, text, col, 13))


def main():
    ss = D.switch_stack()
    sw_top = D.Y_F + D.SW1["h"]
    puck_bot, puck_top = sw_top + ss["nominal_gap"] * 0 + 0.0, sw_top + D.PUCK_L
    W = 4.0   # half width shown (mm)
    e = []
    # cell + board + parts
    e.append(box(-W, W, D.Y_B - D.B_GAP - 0.4, D.Y_B - D.B_GAP, "#f3f1ea", MUTED))
    e.append(label(X0 - W * S + 8, sy(D.Y_B - D.B_GAP - 0.2) + 5, "cell (pouch)", MUTED, 13))
    e.append(box(-W, W, D.Y_B, D.Y_F, "#e8f3ec", GREEN))
    e.append(label(X0 - W * S + 8, sy(D.Y_B + 0.4) + 5, "board 0.8 (JLC ±0.1)", GREEN, 13))
    for xc in (-1.6, 0.4, 1.7):   # B parts under SW1 (R21, R10, R4, L1 class), symbolic
        e.append(box(xc - 0.3, xc + 0.3, D.Y_B - 0.55, D.Y_B, "#f3f1ea", MUTED))
    e.append(label(X0 + 2.2 * S, sy(D.Y_B - 0.3) + 5, "B parts (R21, R10, R4, L1)", MUTED, 12))
    # VHB with pocket cut-out
    px = D.POCKET["dx"] / 2
    e.append(box(-W, -px, D.Y_F, D.Y_F + D.VHB_T, "#fff4ea", ORANGE))
    e.append(box(px, W, D.Y_F, D.Y_F + D.VHB_T, "#fff4ea", ORANGE))
    e.append(label(X0 + (px + 0.1) * S, sy(D.Y_F + 0.12) + 5, "VHB 0.25 ±15 %", ORANGE, 12))
    # lid with pocket and bore, plate, skin recess
    br, rr = D.BORE_D / 2, D.SKIN_D / 2
    e.append(box(-W, -px, D.Y_LID_IN, D.Y_OUT, "#e8f0fb", BLUE))
    e.append(box(px, W, D.Y_LID_IN, D.Y_OUT, "#e8f0fb", BLUE))
    e.append(box(-px, -br, D.POCKET["top"], D.Y_OUT, "#e8f0fb", BLUE))
    e.append(box(br, px, D.POCKET["top"], D.Y_OUT, "#e8f0fb", BLUE))
    e.append(box(-W, -rr, D.Y_OUT, D.Y_TOP, "#e8f0fb", BLUE))
    e.append(box(rr, W, D.Y_OUT, D.Y_TOP, "#e8f0fb", BLUE))
    e.append(box(-rr, -br, D.Y_OUT, D.SKIN_FLOOR, "#e8f0fb", BLUE))
    e.append(box(br, rr, D.Y_OUT, D.SKIN_FLOOR, "#e8f0fb", BLUE))
    e.append(label(X0 - W * S + 8, sy(D.Y_LID_IN + 0.4) + 5, "lid 0.8", BLUE, 13))
    e.append(label(X0 - W * S + 8, sy(D.Y_OUT + 0.35) + 5, "armour plate 0.7", BLUE, 13))
    # skin
    e.append(box(-rr, rr, D.SKIN_FLOOR, D.Y_TOP, "#f3f1ea", RED))
    e.append(label(X0 - rr * S, sy(D.Y_TOP) - 10, f"silicone skin {D.SKIN_T} in the Ø{D.SKIN_D} recess (seal + spring)", RED, 12))
    # SW1
    e.append(box(-D.SW1["body"][0] / 2, D.SW1["body"][0] / 2, D.Y_F, sw_top, "#f3f1ea", INK))
    e.append(label(X0, sy(D.Y_F + 0.3) + 5, "SW1 KMT022 0.65", INK, 12, "middle"))
    # puck + nub
    e.append(box(-D.NUB_D / 2, D.NUB_D / 2, sw_top, sw_top + D.NUB_H, "#fff4ea", ORANGE))
    e.append(box(-D.PUCK_D / 2, D.PUCK_D / 2, sw_top + D.NUB_H, puck_top, "#fff4ea", ORANGE))
    e.append(label(X0, sy(sw_top + 0.5) + 5, f"puck Ø{D.PUCK_D} (kit {D.PUCK_KIT[0]}-{D.PUCK_KIT[-1]})", ORANGE, 12, "middle"))
    # dimensions on the right
    xr = X0 + W * S + 25
    e.append(dim(D.Y_B, D.Y_F, xr, "board 0.80"))
    e.append(dim(D.Y_F, D.Y_LID_IN, xr, f"F gap 0.30 (VHB 0.25; slack 0.05, worst 0.0125)"))
    e.append(dim(sw_top, D.POCKET["top"], xr, f"pocket ceiling {ss['pocket_ceiling_clear_nominal']} nom / {ss['pocket_ceiling_clear_worst']} worst"))
    e.append(dim(puck_top, D.SKIN_FLOOR, xr, f"puck top → skin {D.PRE_GAP} nom; selective fit {ss['selective_fit'][0]}-{ss['selective_fit'][1]}"))
    e.append(dim(D.Y_B - D.B_GAP, D.Y_B, xr, "B gap 1.4 (tallest B part U2 1.08, margin 0.32)"))
    head = [label(30, 38, "Button stack (Phase 2): skin → puck → SW1 → board → VHB → lid", INK, 22, weight="bold"),
            label(30, 62, f"section through SW1's axis, to scale ({S:.0f} px/mm), generated from hw/mech/dims_r2.py by docs/diagrams/make_button_stack.py", MUTED, 13),
            label(30, 82, f"fixed-length puck worst {ss['fixed_worst'][0]}..{ss['fixed_worst'][1]} mm (pre-presses: why the 5-length kit exists); press of 2 N moves SW1 ≤ 20 µm (sw1_press_fem.py)", MUTED, 13),
            label(30, 690, "Fit: physical.md assembly step 9 (gauge depth, pick puck = depth − 0.07, unbonded click test, bond, retest). Nub Ø1.0 = C&amp;K minimum (UI-3, owner feel call).", MUTED, 13)]
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1500 710" font-family="DejaVu Sans, Arial, sans-serif">'
           f'<rect width="1500" height="710" fill="#fbfaf7"/>' + "".join(head + e) + "</svg>\n")
    (HERE / "button-stack.svg").write_text(svg)
    print("wrote", HERE / "button-stack.svg")


if __name__ == "__main__":
    main()
