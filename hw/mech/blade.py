"""Blade exterior, rev 2 (owner picked "blade" 2026-09-30), with a removable frame adapter.

    python3 hw/mech/blade.py      # -> hw/mech/out/styles/blade2*/ STLs + parts.json entries + fit check
    blender -b -P hw/mech/render_styles.py -- blade2 blade2_chrome blade2_exploded

Changes from the concept (hw/mech/styles.py):
- No UV/glow prints (owner). The circuit trace stays as an engraved groove (airbrush chrome if wanted).
- Dorsal fin: a tapered wedge that grows out of the armour plate's top edge (sloped sides, raked
  concave profile), not a flat slab stuck on a box. A matching heel under the rear holds the arm's
  anchor and curved root support, so the arm grows out of the shell too.
- Frame adapter is a SEPARATE print: a plate with the temple-arm clip lips, sliding onto a dovetail
  rail on the pod's inner face and held by a printed snap latch. New frames = reprint the adapter
  only (parametric in TEMPLE_T / TEMPLE_H). Costs 1.8 mm of stand-off between temple and pod.
- Pad: hex housing; its ring is either a clear light-guide lit by an 0402 LED (docs/research/pad-led.md)
  or airbrushed chrome.
Printing: body + armour + fin + heel are ONE print (split here only for render materials).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
from build123d import (Axis, Box, Cylinder, Polygon, Pos, Rot, RegularPolygon, Spline, chamfer,
                       export_stl, extrude, make_face, Polyline, Wire, Plane)

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pod  # noqa: E402
from styles import plate, slot  # noqa: E402

OUT = HERE / "out" / "styles"
ADAPT_T = 1.8                       # adapter plate thickness (temple face -> pod inner face)
RAIL_H, RAIL_W0, RAIL_W1 = 1.0, 5.0, 6.4   # dovetail: height, width at the pod face, width at its top
RAIL_X = (36.0, 62.0)               # rail runs along x on the pod's inner face
FIT = 0.15                          # sliding clearance per side (MJF/resin; FDM wants ~0.25)

X0, X1 = pod.F.X0, pod.F.X1         # the selected design body (phase2: VISION_X 29.5 .. 67.5; K1 starts behind the limit)
ZC = pod.POD_ZC
Z0, Z1 = ZC - pod.POD_H / 2, ZC + pod.POD_H / 2
Y_IN = pod.TEMPLE_T + ADAPT_T       # pod inner face (4.3)
Y_OUT = Y_IN + pod.POD_W            # pod outer face (14.3)
MIC = (pod.VISION_X + 5.0, ZC + 1.0)
ANCHOR = (60.5, 2.3, -7.5)          # arm root, inside the heel, under the adapter
PAD_C = (70.6, pod.SKIN_Y + pod.XDCR[1] / 2 + pod.PAD_HOUSING_WALL, -25.0)   # unchanged (anatomy)


def _wind(pts, ccw):
    """build123d extrudes along the face normal, which flips with the point order: fix the order."""
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
    return list(pts) if (area > 0) == ccw else list(reversed(pts))


def prism_xz(pts, y0, y1):
    pts = _wind(pts, ccw=False)
    f = extrude(Polygon(*pts, align=None), amount=y1 - y0)       # z in [0, t]
    s = Pos(0, y0, 0) * Rot(90, 0, 0) * f                       # t -> +y (checked in styles.plate)
    return s


def prism_yz(pts, x0, x1):
    """Prism from a (y, z) polygon between x0 and x1."""
    pts = _wind(pts, ccw=True)
    f = extrude(Polygon(*pts, align=None), amount=x1 - x0)       # 2D (u=y, v=z), extruded along +Z
    return Pos(x0, 0, 0) * Rot(0, 90, 0) * Rot(0, 0, 90) * f


def prism_xy(pts, z0, z1):
    pts = _wind(pts, ccw=True)
    return Pos(0, 0, z0) * extrude(Polygon(*pts, align=None), amount=z1 - z0)


LATCH_Z = (-8.9, -8.0)              # tooth/bump band, below the adapter plate, on the pod's inner face
BUMP_X = (X0 + 1.9, X0 + 3.4)       # ramp faces the front (adapter slides on front -> rear); phase2 31.4-32.9, follows the pod front (K1)


def catch_bump():
    """Ramp on the pod's inner face: the adapter's tooth rides over it and drops in behind it."""
    return prism_xy([(BUMP_X[0], Y_IN), (BUMP_X[1], Y_IN), (BUMP_X[1], Y_IN - 0.45)], *LATCH_Z)


def check_prism_yz():
    s = prism_yz([(0, 0), (2, 0), (2, 1), (0, 1)], 10, 13)
    b = s.bounding_box()
    return (round(b.min.X, 3), round(b.max.X, 3), round(b.min.Y, 3), round(b.max.Y, 3), round(b.min.Z, 3), round(b.max.Z, 3))


def fin(z1=None, y_out=None):
    """Tapered dorsal fin: raked side profile intersected with a sloped-wall cross-section. z1/y_out: body top and
    outer face (default: the current pod, pod.py; hw/mech/shell.py passes its pre-rev-1 body)."""
    Z1 = globals()["Z1"] if z1 is None else z1
    Y_OUT = globals()["Y_OUT"] if y_out is None else y_out
    side = [(46.0, Z1 - 0.6), (50.0, Z1 + 0.25), (55.0, Z1 + 0.8), (60.0, Z1 + 1.5), (64.2, Z1 + 2.4),
            (66.6, Z1 + 2.3), (67.5, Z1 + 0.6), (67.5, Z1 - 0.6)]
    s = prism_xz(side, Y_IN + 3.0, Y_OUT + 1.2)
    sec = [(Y_OUT + 0.8, Z1 - 0.6), (Y_OUT + 0.8, Z1), (Y_OUT - 1.2, Z1 + 2.6), (Y_OUT - 1.9, Z1 + 2.6),
           (Y_OUT - 4.6, Z1), (Y_OUT - 4.6, Z1 - 0.6)]
    w = prism_yz(sec, 45.0, 68.0)
    return s & w


def heel():
    """Keel under the rear: carries the arm anchor inboard, under the adapter; chamfered wedge."""
    side = [(51.0, Z0 + 1.2), (60.0, Z0 - 0.4), (65.2, Z0 - 0.9), (67.0, Z0 - 0.1), (67.5, -6.2), (66.3, -4.9), (57.0, -4.9)]
    s = prism_xz(side, ANCHOR[1] - 1.6, Y_IN + 2.0)
    sec = [(ANCHOR[1] - 1.6, -6.5), (ANCHOR[1] + 0.3, -4.9), (Y_IN + 2.0, -4.9), (Y_IN + 2.0, Z0 - 1.0),
           (ANCHOR[1] + 0.4, Z0 - 1.0), (ANCHOR[1] - 1.6, Z0 + 1.0)]
    w = prism_yz(sec, 50.0, 68.0)
    return chamfer((s & w).edges().filter_by(Axis.X), 0.3) if False else (s & w)


def rail(zc=None):
    """Male dovetail on the pod's inner face (part of the pod print). zc: the body's centre height; default = pod.POD_ZC,
    the CURRENT design's body centre (Phase 2: -2.45; was the Rev F/rev-2 constant -2.0 until ECR-0001, 2026-10-07)."""
    zc = ZC if zc is None else zc
    sec = [(Y_IN, zc - RAIL_W0 / 2), (Y_IN, zc + RAIL_W0 / 2), (Y_IN - RAIL_H, zc + RAIL_W1 / 2),
           (Y_IN - RAIL_H, zc - RAIL_W1 / 2)]
    return prism_yz(sec, *RAIL_X) + catch_bump()


def adapter(zc=None):
    """zc: the rail centre it mates (default pod.POD_ZC, the current design's body centre, as rail()). Separate print: plate + temple clip lips, female dovetail (closed at the rear = end stop),
    and a snap tab hanging below the plate. Slide on from the front; the tooth rides over the pod's
    ramp and drops in behind it. Release: push the tab's foot toward the head with a fingernail
    (0.45 mm) and slide forward. Tab 5 mm x 0.6 mm: ~1.6% bending strain at release (PA12/PETG ok)."""
    ZC_ = ZC if zc is None else zc
    T, Hh = pod.TEMPLE_T, pod.TEMPLE_H
    zt, zb = Hh / 2 + 1.4, -Hh / 2 - 1.4
    x0, x1 = RAIL_X[0] - 3.0, RAIL_X[1] + 1.0
    body = Pos((x0 + x1) / 2, T + ADAPT_T / 2, (zt + zb) / 2) * Box(x1 - x0, ADAPT_T, zt - zb)
    body = chamfer(body.edges().filter_by(Axis.X), 0.4)
    for zs in (+1, -1):     # lips over the temple's top/bottom edges, hooking its inner face
        z = zs * (Hh / 2 + 0.4)
        lip = Pos((x0 + x1) / 2, T / 2 + 0.2, z) * Box(x1 - x0 - 4, T + 0.4, 0.8)
        hook = Pos((x0 + x1) / 2, -0.4, zs * (Hh / 2 - 0.25)) * Box(x1 - x0 - 4, 0.8, 1.3)
        body = body + lip + hook
    sec = [(Y_IN + 0.01, ZC_ - RAIL_W0 / 2 - FIT), (Y_IN + 0.01, ZC_ + RAIL_W0 / 2 + FIT),
           (Y_IN - RAIL_H - FIT, ZC_ + RAIL_W1 / 2 + FIT), (Y_IN - RAIL_H - FIT, ZC_ - RAIL_W1 / 2 - FIT)]
    body = body - prism_yz(sec, x0 - 0.01, RAIL_X[1] + FIT)
    tx = BUMP_X[1] + 0.1
    tab = prism_xy([(tx, Y_IN - 1.05), (tx + 2.6, Y_IN - 1.05), (tx + 2.6, Y_IN - 0.45), (tx, Y_IN - 0.45)],
                   LATCH_Z[0] - 0.3, zb + 0.4)
    tooth = prism_xy([(tx, Y_IN - 0.45), (tx + 1.2, Y_IN - 0.45), (tx + 1.2, Y_IN - 0.05), (tx, Y_IN - 0.05)],
                     *LATCH_Z)
    return body + tab + tooth


def shell():
    b = Pos((X0 + X1) / 2, (Y_IN + Y_OUT) / 2, ZC) * Box(pod.POD_L, pod.POD_W, pod.POD_H)
    return chamfer(b.edges(), 1.0)


def armour_and_trace(y_out=None, z1=None, mic=None):
    """Armour plate + trace groove + hex mic window (defaults: the current pod; hw/mech/shell.py passes its pre-rev-1 body)."""
    Z1 = globals()["Z1"] if z1 is None else z1
    MIC = globals()["MIC"] if mic is None else mic
    y = Y_OUT if y_out is None else y_out
    pts = [(31.8, 4.3), (46.0, 4.3), (47.8, Z1 - 0.1), (66.2, Z1 - 0.1), (66.2, -7.2), (61, -8.6), (37, -8.6), (31.8, -3.6)]
    arm = plate(pts, y, 0.8, 0.35)
    upper = plate([(34.5, 3.6), (44.0, 3.6), (41.8, 1.3), (34.5, 1.3)], y + 0.8, 0.45, 0.2)
    trace = [(38.5, -6.8), (51, -6.8), (55.2, -2.6), (63.8, -2.6), (63.8, 3.0)]
    groove = slot(trace, y + 0.8, 0.7, 0.5)
    hexwin = Pos(MIC[0], y + 0.8, MIC[1]) * Rot(90, 0, 0) * extrude(RegularPolygon(1.9, 6), amount=2.0, both=True)
    armour = (arm - groove - hexwin) + (upper - hexwin)
    paint = slot(trace, y + 0.42, 0.6, 0.12)        # airbrushed chrome in the groove floor (optional)
    return armour, paint


def arm_pad(ring):
    a, p = np.array(ANCHOR), np.array(PAD_C)
    v = p - a
    L = float(np.linalg.norm(v))
    sweep = math.degrees(math.atan2(v[0], -v[2]))
    lean = math.degrees(math.atan2(v[1], math.hypot(v[0], v[2])))
    sleeve = Pos(*(a + v / 2)) * Rot(lean, 0, 0) * Rot(0, -sweep, 0) * Cylinder(pod.SLEEVE_D / 2 + 0.1, L - 5.0)
    hx, hy, hz = (pod.XDCR[2] + 2 * pod.PAD_HOUSING_WALL, pod.XDCR[1] + 2 * pod.PAD_HOUSING_WALL,
                  pod.XDCR[0] + 2 * pod.PAD_HOUSING_WALL)
    place = Pos(*PAD_C) * Rot(0, -sweep, 0)
    hexp = Rot(90, 0, 0) * extrude(RegularPolygon(hz / 2 + 0.6, 6), amount=hy / 2, both=True)
    hexp = hexp & Box(hx + 1.0, hy, hz + 2.0)
    housing = chamfer(hexp.edges().group_by(Axis.Y)[-1], 0.5)
    groove = Pos(0, hy / 2, 0) * Rot(90, 0, 0) * (Cylinder(2.7, 0.8) - Cylinder(2.0, 0.8))
    housing = housing - groove
    ringp = Pos(0, hy / 2 - 0.25, 0) * Rot(90, 0, 0) * (Cylinder(2.65, 0.4) - Cylinder(2.05, 0.4))
    silicone = Pos(PAD_C[0], pod.SKIN_Y + 0.4, PAD_C[2]) * Rot(90, 0, 0) * Cylinder(4.5, 0.8)
    return {"sleeve": sleeve, "pad_housing": place * housing, ring: place * ringp, "silicone_pad": silicone,
            "anchor": Pos(*ANCHOR) * Rot(0, 90, 0) * Cylinder(1.6, 3.0)}, L, sweep


def build(ring="glow", explode=0.0):
    body = shell() + fin() + heel() + rail()
    body = body - (Pos(MIC[0], Y_OUT, MIC[1]) * Rot(90, 0, 0) * Cylinder(0.5, 4.0))
    for x in (41.0,):
        body = body - Pos(x, Y_OUT - 2.0, Z1) * Box(0.5, 4.0, 0.6)
    armour, paint = armour_and_trace()
    parts = {"body": body, "armour": armour, "paint": paint}
    ap, L, sweep = arm_pad(ring)
    parts.update(ap)
    if explode:     # the pod slides rearward off the adapter along the dovetail (the real motion)
        parts = {k: Pos(explode, 0, 0) * v for k, v in parts.items()}
    parts["adapter"] = adapter()
    parts["temple"] = Pos(40, pod.TEMPLE_T / 2, 0) * chamfer(Box(130, pod.TEMPLE_T, pod.TEMPLE_H).edges(), 0.6)
    return parts, {"arm_length": round(L, 1), "sweep_deg": round(sweep, 1)}


def fit_checks(parts):
    """Adapter vs pod (must not overlap except nothing), adapter vs temple, heel vs temple."""
    out = {}
    pod_all = parts["body"]
    for a, b in (("adapter", "body"), ("adapter", "temple"), ("body", "temple"), ("sleeve", "adapter")):
        A = parts[a] if a != "body" else pod_all
        B = parts[b] if b != "body" else pod_all
        inter = (A & B).volume
        out[f"{a}/{b}"] = -round(inter, 3) if inter > 1e-3 else round(A.distance_to(B), 3)
    return out


def main():
    info = json.loads((OUT / "parts.json").read_text()) if (OUT / "parts.json").exists() else {}
    for name, ring, ex in (("blade2", "glow", 0.0), ("blade2_chrome", "chrome", 0.0), ("blade2_exploded", "glow", 30.0)):
        d = OUT / name
        d.mkdir(parents=True, exist_ok=True)
        for f in d.glob("*.stl"):
            f.unlink()
        parts, geom = build(ring, ex)
        for k, s in parts.items():
            export_stl(s, str(d / f"{k}.stl"), tolerance=0.01, angular_tolerance=0.1)
        info[name] = {"glow": "blue", "geometry": geom}
        if ex == 0.0:
            info[name]["fit_mm (negative = overlap mm3)"] = fit_checks(parts)
    (OUT / "parts.json").write_text(json.dumps(info, indent=2))
    print(json.dumps({k: v for k, v in info.items() if k.startswith("blade2")}, indent=2))


if __name__ == "__main__":
    if "--check" in sys.argv:
        print(check_prism_yz())
    else:
        main()
