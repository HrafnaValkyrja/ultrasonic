#!/usr/bin/env python3
"""0.6 mm wall print coupon (round 11, packet Q2; owner prints by hand, resin). Owner notes: hw/mech/notes/coupon_wall06.md.

    source tools/env.sh && systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 python3 hw/mech/coupon_wall06.py
    # -> hw/mech/out/coupon_wall06/{tub,lid}.stl, checks.json, coupon.png (dark)

Two parts, 22 x 14 mm, using the shell's REAL features (constants from dims_r2.py / shell_r2.py, not re-typed):
- TUB: open box, floor 0.6. Left half walls 0.6 (K1-thin), right half walls 0.8 (Phase 2 reference), so every test
  compares the two side by side. Outer corners: front-left 1.0 chamfer (the shell's), back-left 0.6 chamfer (the option
  that keeps 0.42 at a 0.6 corner), right corners 1.0 at 0.8 walls (as Phase 2). Tongue TONGUE_W x TONGUE_H on the rim
  (stopped CORNER_KEEP short of the corners), seam rebate REBATE_D x REBATE_H on the outside below the rim.
- LID: plate with a skirt that takes the tongue in a groove (TONGUE_W + GROOVE_CL wide). Plate zones: 0.6 (left: K1-thin,
  mesh seat 0.1 + bore) and 1.0 (right: K1 'rec' stack: hex seat R1.9 x 0.3 + D1.0 bore, skin recess D4.6 x 0.1 + puck bore
  D2.6 + SW1 pocket 4.3 x 3.1 x 0.6 from the inside). Bores print at D0.9 to be reamed with the 1.0 drill (as the shell).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from build123d import Box, Cylinder, Pos, RegularPolygon, Rot, export_stl, extrude

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import dims_r2 as D  # noqa: E402  (Phase-2 constants: tongue, groove, hex seat, pocket, skin, bore)

OUT = HERE / "out" / "coupon_wall06"
REBATE_D, REBATE_H = 0.2, 0.4          # = shell_r2.REBATE_D/H (shell_r2 imports CAD; kept equal by check below)
LX, LZ, HY = 22.0, 14.0, 6.0           # coupon footprint x, z and tub height y
XM = LX / 2                            # 0.6 | 0.8 boundary
W6, W8 = 0.6, 0.8
SKIRT = 1.2                            # lid skirt height below the plate
BORE_PRINT = 0.9                       # printed undersize, reamed to D.DUCT_D (1.0)


def box(x0, x1, y0, y1, z0, z1):
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(x1 - x0, y1 - y0, z1 - z0)


def ycyl(x, z, d, y0, y1):
    return Pos(x, (y0 + y1) / 2, z) * Rot(90, 0, 0) * Cylinder(d / 2, y1 - y0)


def corner_chamfer(solid, x, z, c, y0, y1):
    """Cut a 45 deg chamfer of leg c off the vertical (y) outer edge at (x, z)."""
    sx = 1 if x > LX / 2 else -1
    sz = 1 if z > LZ / 2 else -1
    cut = Pos(x, (y0 + y1) / 2, z) * Rot(0, 45, 0) * Box(c * math.sqrt(2), y1 - y0 + 2, c * math.sqrt(2))
    return solid - cut if c > 0 else solid


def wall_t(x):
    return W6 if x < XM else W8


def tub():
    outer = box(0, LX, 0, HY, 0, LZ)
    # cavity: floor 0.6 (y 0..0.6), walls 0.6 left / 0.8 right
    cav = box(W6, XM, W6, HY + 1, W6, LZ - W6) + box(XM - 0.01, LX - W8, W6, HY + 1, W8, LZ - W8)
    t = outer - cav
    for (x, z, c) in ((0, 0, 1.0), (0, LZ, 0.6), (LX, 0, 1.0), (LX, LZ, 1.0)):
        t = corner_chamfer(t, x, z, c, -1, HY + 1)
    # tongue on the rim, inner edge, stopped CORNER_KEEP short of each corner (as shell_r2.tongue)
    k, tw, th = D.CORNER_KEEP, D.TONGUE_W, D.TONGUE_H
    runs = [(k, XM, W6, W6 + tw), (XM, LX - k, W8, W8 + tw),                       # front (z low) run
            (k, XM, LZ - W6 - tw, LZ - W6), (XM, LX - k, LZ - W8 - tw, LZ - W8),   # back run
            ]
    for x0, x1, z0, z1 in runs:
        t = t + box(x0, x1, HY - 0.01, HY + th, z0 - (0.0 if z0 < LZ / 2 else 0.0), z1)
    t = t + box(W6, W6 + tw, HY - 0.01, HY + th, k, LZ - k) + box(LX - W8 - tw, LX - W8, HY - 0.01, HY + th, k, LZ - k)
    # seam rebate round the outside just below the rim
    band = box(-1, LX + 1, HY - REBATE_H, HY + 0.01, -1, LZ + 1) - box(REBATE_D, LX - REBATE_D, HY - REBATE_H - 0.1, HY + 0.1, REBATE_D, LZ - REBATE_D)
    return t - band


def lid():
    """Upside-down cap: skirt (y 0..SKIRT) then plate; plate thickness 0.6 left, 1.0 right (outer face flat)."""
    y_out = SKIRT + 1.0
    l = box(0, LX, 0, y_out, 0, LZ)
    l = l - box(W6, XM, -1, SKIRT + 0.4, W6, LZ - W6) - box(XM - 0.01, LX - W8, -1, SKIRT, W8, LZ - W8)   # left plate 0.6, right 1.0
    for (x, z, c) in ((0, 0, 1.0), (0, LZ, 0.6), (LX, 0, 1.0), (LX, LZ, 1.0)):
        l = corner_chamfer(l, x, z, c, -1, y_out + 1)
    g = D.TONGUE_W + D.GROOVE_CL
    gh = D.TONGUE_H + D.GROOVE_CL
    for x0, x1, z0, z1, w in ((0, XM, W6, W6 + g, W6), (XM, LX, W8, W8 + g, W8), (0, XM, LZ - W6 - g, LZ - W6, W6), (XM, LX, LZ - W8 - g, LZ - W8, W8)):
        l = l - box(x0, x1, -0.01, gh, z0, z1)
    l = l - box(W6, W6 + g, -0.01, gh, 0, LZ) - box(LX - W8 - g, LX - W8, -0.01, gh, 0, LZ)
    # left zone (0.6 plate): mesh seat 0.1 + bore
    xa, za = XM / 2, LZ / 2
    l = l - ycyl(xa, za, BORE_PRINT, SKIRT, y_out + 0.1)
    l = l - Pos(xa, y_out - 0.05, za) * Rot(90, 0, 0) * extrude(RegularPolygon(D.HEX_R, 6), amount=0.05, both=True)
    # right zone (1.0 plate): K1 'rec' stack - hex R1.9 x 0.3 + bore; skin recess D4.6 x 0.1 + D2.6 puck bore + pocket 0.6
    xb, xs = XM + 2.4, LX - 3.2          # seat (hex to x 15.3) and skin recess (from 16.5) kept apart
    l = l - ycyl(xb, za, BORE_PRINT, SKIRT - 0.1, y_out + 0.1)
    l = l - Pos(xb, y_out - 0.15, za) * Rot(90, 0, 0) * extrude(RegularPolygon(D.HEX_R, 6), amount=0.15, both=True)
    l = l - box(xs - D.POCKET["dx"] / 2, xs + D.POCKET["dx"] / 2, SKIRT - 0.1, SKIRT + 0.6, za - D.POCKET["dz"] / 2, za + D.POCKET["dz"] / 2)
    l = l - ycyl(xs, za, D.BORE_D, SKIRT + 0.5, y_out + 0.1)
    l = l - ycyl(xs, za, D.SKIN_D, y_out - 0.1, y_out + 0.1)
    return l


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    t, l = tub(), lid()
    corner = lambda w, c: round(w * math.sqrt(2) - c / math.sqrt(2), 3)   # noqa: E731  material left at a chamfered outer corner
    c = dict(
        date="2026-10-07", src="hw/mech/coupon_wall06.py",
        tub=dict(solids=len(t.solids()), valid=bool(t.is_valid), volume_mm3=round(t.volume, 1)),
        lid=dict(solids=len(l.solids()), valid=bool(l.is_valid), volume_mm3=round(l.volume, 1)),
        corner_material_mm={"0.6 wall, 1.0 chamfer (shell today)": corner(W6, 1.0), "0.6 wall, 0.6 chamfer": corner(W6, 0.6),
                            "0.8 wall, 1.0 chamfer (Phase 2)": corner(W8, 1.0)},
        lid_outer_lip_after_groove_mm={"0.6": round(W6 - D.TONGUE_W - D.GROOVE_CL, 3), "0.8": round(W8 - D.TONGUE_W - D.GROOVE_CL, 3)},
        tub_wall_at_rebate_mm={"0.6": round(W6 - REBATE_D, 3), "0.8": round(W8 - REBATE_D, 3)},
        resin_min_wall=0.6, resin_min_feature=0.3,
        press_estimate_5N=dict(note="[A] clamped plate ~12 x 20, point load, E 2 GPa resin, Roark alpha 0.07 / beta 1.0: order of magnitude only",
                               w06_mm=round(0.07 * 5 * 12.0 ** 2 / (2000 * W6 ** 3), 3), w08_mm=round(0.07 * 5 * 12.0 ** 2 / (2000 * W8 ** 3), 3),
                               stress06_MPa=round(1.0 * 5 / W6 ** 2, 1), stress08_MPa=round(1.0 * 5 / W8 ** 2, 1)))
    print(json.dumps(c, indent=1))
    (OUT / "checks.json").write_text(json.dumps(c, indent=1))
    export_stl(t, str(OUT / "tub.stl"), tolerance=0.01, angular_tolerance=0.1)
    export_stl(l, str(OUT / "lid.stl"), tolerance=0.01, angular_tolerance=0.1)
    figure(t, l, c)


def figure(t, l, c):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    sys.path.insert(0, str(ROOT / "tools"))
    import plotstyle
    plotstyle.apply()
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.2))

    def sect(ax, solid, axis, val, uv, col, title):
        half = {"Z": box(-5, LX + 5, -5, 20, -5, val), "Y": box(-5, LX + 5, -5, val, -5, LZ + 5), "X": box(-5, val, -5, 20, -5, LZ + 5)}[axis]
        cut = solid & half
        for f in cut.faces():
            if abs(getattr(f.center(), axis) - val) < 1e-5:
                vs, tris = f.tessellate(0.01, 0.2)
                ax.add_collection(PolyCollection([[(getattr(vs[i], uv[0]), getattr(vs[i], uv[1])) for i in tri] for tri in tris],
                                                 facecolors=col, edgecolors="face"))
        ax.set_aspect("equal")
        ax.autoscale()
        ax.set_title(title, fontsize=9)
    sect(axes[0], t, "Z", LZ / 2, ("X", "Y"), "#9aa3b2", "TUB section z mid: 0.6 walls left | 0.8 right, tongue on the rim")
    sect(axes[1], l, "Z", LZ / 2, ("X", "Y"), "#5b9ff2", "LID section z mid: plate 0.6 (mesh seat 0.1) | 1.0 ('rec' seat 0.3, puck stack)")
    sect(axes[2], t, "Y", 3.0, ("X", "Z"), "#9aa3b2", "TUB plan at mid height: corner chamfers 1.0 / 0.6")
    cm = c["corner_material_mm"]
    fig.suptitle(f"0.6 wall coupon: corner left {cm['0.6 wall, 1.0 chamfer (shell today)']} mm (1.0 chamfer) vs {cm['0.6 wall, 0.6 chamfer']} (0.6 chamfer); "
                 f"lid lip after groove {c['lid_outer_lip_after_groove_mm']['0.6']} mm; tub at rebate {c['tub_wall_at_rebate_mm']['0.6']} mm (resin min 0.6)", fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT / "coupon.png", dpi=130)


if __name__ == "__main__":
    main()
