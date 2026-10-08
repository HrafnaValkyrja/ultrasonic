"""K4 end-to-end pod concept (CAD-light, honest): shell + lid + 130 mAh cell + 17 mm two-face board, along the arm.

    python3 hw/mech/k4_concept.py     # -> hw/mech/out/k4/*.stl + parts.json (same frame as shell_r2.py / k1t)
Source: docs/research/drastic/V8-thin-long.yaml K4_130mAh_end_to_end (T 6.4, H 14.8, L 51.1, walls 0.6, lid 1.0, no plate).
Frame = shell_r2: X along the arm (rear face fixed at 67.5, front toward hinge), Y outward from the temple (inner face 4.3), Z up.
Board at the FRONT (mic at the hinge, F1), cell behind it. No dock belly, no heel/puck/button: a concept for size, not a design.
"""
import json
from pathlib import Path

from build123d import Box, Pos, export_stl, fillet

OUT = Path(__file__).resolve().parent / "out" / "k4"
X1, L = 67.5, 51.1
X0 = X1 - L
Y_IN, T, WALL, LID = 4.3, 6.4, 0.6, 1.0
Z0, Z1 = -9.7, 5.1                     # H 14.8, same z band as k1t (-9.7 .. 5.1) minus the dock belly
CELL = dict(T=4.5, W=12.7, L=31.0)     # ICP401230UPR envelope max (V2-cells.yaml)
BOARD_L, BOARD_H = 17.0, 12.0


def box(x0, x1, y0, y1, z0, z1):
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(x1 - x0, y1 - y0, z1 - z0)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    y_top, y_split = Y_IN + T, Y_IN + T - LID
    outer = box(X0, X1, Y_IN, y_top, Z0, Z1)
    outer = fillet(outer.edges(), 1.0)
    cav = box(X0 + WALL, X1 - WALL, Y_IN + WALL, y_split + 0.01, Z0 + WALL, Z1 - WALL)
    tub = (outer & box(X0 - 1, X1 + 1, 0, y_split, Z0 - 1, Z1 + 1)) - cav
    lid = outer & box(X0 - 1, X1 + 1, y_split, 20, Z0 - 1, Z1 + 1)
    zc = (Z0 + Z1) / 2
    xb0 = X0 + WALL + 0.4
    xc0 = xb0 + BOARD_L + 0.4
    y_c0 = Y_IN + WALL + 0.0
    cell = box(xc0, xc0 + CELL["L"], y_c0, y_c0 + CELL["T"], zc - CELL["W"] / 2, zc + CELL["W"] / 2)
    yb = y_c0 + CELL["T"] + 0.3 - 1.0       # board sits flush under the lid in the board segment (two-face, thinner than the cell)
    pcb = box(xb0, xb0 + BOARD_L, yb - 0.4, yb + 0.4, zc - BOARD_H / 2, zc + BOARD_H / 2)
    chips = box(xb0 + 1, xb0 + BOARD_L - 1, yb - 1.3, yb - 0.4, zc - 4.5, zc + 4.5) + box(xb0 + 1, xb0 + 14, yb + 0.4, yb + 0.8, zc - 3, zc + 3)
    mic = box(xb0 + 1.5, xb0 + 4.2, yb - 1.1, yb - 0.4, zc - 1.4, zc + 1.4)
    parts = {"tub": (tub, "body"), "lid": (lid, "armour"), "cell": (cell, "cell"), "pcb": (pcb, "pcb"),
             "chips": (chips, "chips"), "u2_mic": (mic, "chips")}
    info = {}
    for k, (s, m) in parts.items():
        export_stl(s, str(OUT / f"{k}.stl"), tolerance=0.01, angular_tolerance=0.1)
        info[k] = {"mat": m, "explode": [0, 0, 0]}
    (OUT / "parts.json").write_text(json.dumps(info, indent=1))
    print("T", round(y_top - Y_IN, 2), "L", round(X1 - X0, 2), "H", round(Z1 - Z0, 2), "cell x", xc0, xc0 + CELL["L"], "cavity free rear", X1 - WALL - xc0 - CELL["L"])


if __name__ == "__main__":
    main()
