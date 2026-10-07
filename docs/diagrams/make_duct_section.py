#!/usr/bin/env python3
"""Dimensioned mic-duct section (sub-audio-in issue 12), generated from hw/mech/dims_r2.py so it follows the CAD.

    python3 docs/diagrams/make_duct_section.py      # -> docs/diagrams/duct-section.svg (render.sh for the PNG)

Section through the duct axis (pod x horizontal, pod y up = toward the outside), to scale. Palette = darken.py's.
Path: hex mesh seat in the armour plate -> reamed bore D1.0 through the lid -> D1.0 hole in the VHB (the annulus seals
on the board's F face) -> board NPTH (D0.6 today; D0.65 + press-fit decided, SAI-15D) -> SPH0641 port on B.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "hw/mech"))
import dims_r2 as D  # noqa: E402

S = 120.0
X0, YB = 560.0, 520.0
INK, MUTED, BLUE, ORANGE, GREEN, RED, PURPLE = "#1f2328", "#57606a", "#2a78d6", "#b8520a", "#1a7a55", "#e34948", "#4a3aa7"


def sy(y):
    return YB - (y - D.Y_B) * S


def box(x0, x1, y0, y1, fill, stroke):
    return (f'<rect x="{X0 + x0 * S:.1f}" y="{sy(y1):.1f}" width="{(x1 - x0) * S:.1f}" height="{(y1 - y0) * S:.1f}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>')


def label(x, y, text, col=INK, size=14, anchor="start", weight="normal"):
    return f'<text x="{x:.1f}" y="{y:.1f}" fill="{col}" font-size="{size}" text-anchor="{anchor}" font-weight="{weight}">{text}</text>'


def dim(y0, y1, x, text, col=MUTED):
    a, b = sy(y0), sy(y1)
    return (f'<line x1="{x}" y1="{a:.1f}" x2="{x}" y2="{b:.1f}" stroke="{col}"/>'
            f'<line x1="{x - 6}" y1="{a:.1f}" x2="{x + 6}" y2="{a:.1f}" stroke="{col}"/>'
            f'<line x1="{x - 6}" y1="{b:.1f}" x2="{x + 6}" y2="{b:.1f}" stroke="{col}"/>' + label(x + 10, (a + b) / 2 + 5, text, col, 13))


def main():
    W = 3.2
    r_d, r_h, r_hex = D.DUCT_D / 2, D.MIC_HOLE_D / 2, D.HEX_R
    y_hex = D.Y_TOP - D.HEX_DEPTH
    y_vhb_bot = D.Y_LID_IN - D.VHB_T
    e = []
    # mic on B (body 3.50 along x since U2 is rotated 90 deg; max height 1.08)
    e.append(box(-1.75, 1.75, D.Y_B - 1.08, D.Y_B, "#f3f1ea", INK))
    e.append(label(X0, sy(D.Y_B - 0.6) + 5, "SPH0641 mic (B face, 1.08 max), port up", INK, 13, "middle"))
    # board with hole
    e.append(box(-W, -r_h, D.Y_B, D.Y_F, "#e8f3ec", GREEN))
    e.append(box(r_h, W, D.Y_B, D.Y_F, "#e8f3ec", GREEN))
    e.append(label(X0 - W * S + 8, sy(D.Y_B + 0.4) + 5, "board 0.8", GREEN, 13))
    # VHB with hole (on the F face; 0.05 slack to the lid is the F gap minus tape)
    e.append(box(-W, -r_d, y_vhb_bot, D.Y_LID_IN, "#fff4ea", ORANGE))
    e.append(box(r_d, W, y_vhb_bot, D.Y_LID_IN, "#fff4ea", ORANGE))
    e.append(label(X0 + (r_d + 0.15) * S, sy(D.Y_LID_IN - 0.1) + 5, "VHB annulus seals on the F face", ORANGE, 12))
    # lid with bore
    e.append(box(-W, -r_hex, D.Y_LID_IN, D.Y_OUT, "#e8f0fb", BLUE))
    e.append(box(r_hex, W, D.Y_LID_IN, D.Y_OUT, "#e8f0fb", BLUE))
    e.append(box(-r_hex, -r_d, D.Y_LID_IN, min(y_hex, D.Y_OUT), "#e8f0fb", BLUE))     # the seat floor cuts into the lid
    e.append(box(r_d, r_hex, D.Y_LID_IN, min(y_hex, D.Y_OUT), "#e8f0fb", BLUE))
    e.append(label(X0 - W * S + 8, sy(D.Y_LID_IN + 0.45) + 5, "lid 0.8", BLUE, 13))
    # plate with bore below the hex seat and the hex window above
    e.append(box(-W, -r_hex, D.Y_OUT, D.Y_TOP, "#e8f0fb", BLUE))
    e.append(box(r_hex, W, D.Y_OUT, D.Y_TOP, "#e8f0fb", BLUE))
    e.append(label(X0 - W * S + 8, sy(D.Y_OUT + 0.4) + 5, "armour plate 0.7", BLUE, 13))
    # mesh on the hex-seat floor
    e.append(box(-r_hex, r_hex, y_hex, y_hex + 0.046, "#f3f1ea", PURPLE))
    e.append(label(X0, sy(y_hex + 0.3) + 5, "Acoustex 042 mesh on the seat floor (SAI-3)", PURPLE, 12, "middle"))
    # air path arrow
    e.append(f'<line x1="{X0}" y1="{sy(D.Y_TOP + 0.35):.1f}" x2="{X0}" y2="{sy(D.Y_B + 0.05):.1f}" stroke="{RED}" stroke-width="2" stroke-dasharray="6 4"/>')
    e.append(label(X0 + 10, sy(D.Y_TOP + 0.3) + 5, "sound in", RED, 13))
    xr = X0 + W * S + 25
    e.append(dim(y_hex, D.Y_TOP, xr, f"hex window R{D.HEX_R} x {D.HEX_DEPTH} (mesh seat)"))
    e.append(dim(D.Y_LID_IN, y_hex, xr, f"bore D{D.DUCT_D} reamed, {y_hex - D.Y_LID_IN:.1f} long"))
    e.append(dim(D.Y_F, D.Y_LID_IN, xr, f"F gap {D.F_GAP}: VHB {D.VHB_T} (hole D{D.DUCT_D})"))
    e.append(dim(D.Y_B, D.Y_F, xr, f"board hole D{D.MIC_HOLE_D} (-> D0.65 press-fit, SAI-15D)"))
    off = D.duct_offsets()
    head = [label(30, 38, "Mic duct (Phase 2): hex mesh seat → bore D1.0 → VHB hole → board hole → mic", INK, 22, weight="bold"),
            label(30, 62, f"section through the duct axis, to scale ({S:.0f} px/mm), generated from hw/mech/dims_r2.py by docs/diagrams/make_duct_section.py", MUTED, 13),
            label(30, 84, f"axis offset: nominal {off['nominal']}, worst with the gauge pin {off['worst_with_gauge_pin']} ≤ {off['limit_R_ACO_P5']} (walls only {off['worst_walls_only']}); "
                          f"keep-out: no F copper / via within r 1.6 (R-ACO-P6)", MUTED, 13),
            label(30, 700, "Acoustics: sealed duct +5.6 dB mean 20-96 kHz, duct peak +14.3 dB at ~56 kHz with the floor mesh (mesh_pick.py); firmware EQ notch from a bench sweep (sub-audio-in 13).", MUTED, 13)]
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1500 720" font-family="DejaVu Sans, Arial, sans-serif">'
           f'<rect width="1500" height="720" fill="#fbfaf7"/>' + "".join(head + e) + "</svg>\n")
    (HERE / "duct-section.svg").write_text(svg)
    print("wrote", HERE / "duct-section.svg")


if __name__ == "__main__":
    main()
