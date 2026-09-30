"""Exterior style concepts for the pod ("Night City"), on the rev 2 internal layout.

    python3 hw/mech/styles.py            # -> hw/mech/out/styles/<concept>/*.stl + parts.json
    blender -b -P hw/mech/render_styles.py   # -> hw/mech/out/styles/*.png (Cycles, CPU)

Rules the concepts keep, so the inside (hw/mech/pod.py) doesn't change:
- The 38 x 10 x 15 mm body stays; styling is ADDED outward (plates, fins, ribs) or cut only into
  what was added. Wall, cavity, clip and clearances are pod.py's.
- Nothing forward of the vision limit (x = 29.5). Nothing on the inner (head-side) face.
- The mic port stays short: every raised feature is cut away around it (§8 acoustic rules).
- Arm: owner's call 2026-09-30 - keep 20 mm and the 30 deg sweep; 0.75 mm NiTi, free shape
  angled ~3-4 mm into the skin (sim/checks/niti_closed_form.py). Drawn in its worn position.
Glow parts are separate bodies: print them in UV-reactive or glow filament (no power), or put a
light pipe on a status LED later. Decorative only.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from build123d import (Axis, Box, Cylinder, Polygon, Pos, Rot, RegularPolygon, chamfer, export_stl,
                       extrude, fillet)

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pod  # noqa: E402

OUT = HERE / "out" / "styles"
X0, X1 = pod.VISION_X, pod.VISION_X + pod.POD_L                 # 29.5 .. 67.5
Z0, Z1 = pod.POD_ZC - pod.POD_H / 2, pod.POD_ZC + pod.POD_H / 2  # -9.5 .. 5.5
Y_IN, Y_OUT = pod.TEMPLE_T, pod.TEMPLE_T + pod.POD_W             # 2.5 .. 12.5
MIC = (pod.VISION_X + 5.0, pod.POD_ZC + 1.0)                     # mic port (x, z) on the outer face
PORT_R = 0.5


def body():
    b = Pos((X0 + X1) / 2, (Y_IN + Y_OUT) / 2, pod.POD_ZC) * Box(pod.POD_L, pod.POD_W, pod.POD_H)
    return chamfer(b.edges(), 1.0)


def plate(pts_xz, y0, thick, ch=0.0):
    """Polygon given in (x, z) on the plane y = y0, extruded outward (+y) by thick."""
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts_xz, pts_xz[1:] + pts_xz[:1]))
    if area > 0:            # the extrusion direction follows the winding; keep it clockwise
        pts_xz = list(reversed(pts_xz))
    f = extrude(Polygon(*pts_xz, align=None), amount=thick)       # z in [0, thick]
    s = Pos(0, y0, 0) * Rot(90, 0, 0) * f                          # maps (x, zs, t) -> (x, y0 + t, zs)
    if ch > 0:
        s = chamfer(s.edges().filter_by(Axis.Y, reverse=True).group_by(Axis.Y)[-1], ch)
    return s


def slot(path_xz, y_top, width, depth):
    """Groove following a polyline on the face y = y_top, going depth into -y. Returns the solid."""
    s = None
    for (xa, za), (xb, zb) in zip(path_xz[:-1], path_xz[1:]):
        L = math.hypot(xb - xa, zb - za)
        phi = -math.degrees(math.atan2(zb - za, xb - xa))
        seg = Pos((xa + xb) / 2, y_top - depth / 2, (za + zb) / 2) * Rot(0, phi, 0) * Box(L, depth, width)
        s = seg if s is None else s + seg
    for x, z in path_xz:
        s = s + Pos(x, y_top - depth / 2, z) * Rot(90, 0, 0) * Cylinder(width / 2, depth)
    return s


def port_clear(y_from, y_to, r):
    """Cylinder around the mic port through any added outer features."""
    h = y_to - y_from
    return Pos(MIC[0], y_from + h / 2, MIC[1]) * Rot(90, 0, 0) * Cylinder(r, h)


def port_hole():
    return port_clear(Y_OUT - 1.0, Y_OUT + 3.0, PORT_R)


def arm_and_pad(style):
    parts, _, geom = pod.build("A")
    out = {"sleeve": parts["arm"][0], "silicone_pad": parts["silicone_pad"][0]}
    px, _, pz = geom["pad_centre"]
    py = pod.SKIN_Y + pod.XDCR[1] / 2 + pod.PAD_HOUSING_WALL
    sweep = geom["sweep_deg"]
    hx, hy, hz = (pod.XDCR[2] + 2 * pod.PAD_HOUSING_WALL, pod.XDCR[1] + 2 * pod.PAD_HOUSING_WALL,
                  pod.XDCR[0] + 2 * pod.PAD_HOUSING_WALL)
    place = Pos(px, py, pz) * Rot(0, -sweep, 0)
    if style == "blade":      # hexagonal prism, chamfered, a glow ring on its outer face
        hexp = Rot(90, 0, 0) * extrude(RegularPolygon(hz / 2 + 0.6, 6), amount=hy / 2, both=True)
        hexp = Pos(0, 0, 0) * Rot(0, 0, 0) * hexp
        # stretch: a hex of the long dimension, trimmed to the housing width
        hexp = hexp & Box(hx + 1.0, hy, hz + 2.0)
        out["pad_housing"] = place * chamfer(hexp.edges().group_by(Axis.Y)[-1], 0.5)
        ring = Rot(90, 0, 0) * (Cylinder(2.6, 0.3) - Cylinder(2.1, 0.3))
        out["glow"] = place * Pos(0, hy / 2 + 0.1, 0) * ring
    elif style == "heatsink":  # box with fins across its outer face
        hb = chamfer(Box(hx, hy, hz).edges(), 0.5)
        for k in range(-2, 3):
            hb = hb + Pos(0, hy / 2 + 0.3, k * 2.4) * Box(hx - 1.2, 0.6, 0.8)
        out["pad_housing"] = place * hb
    else:                      # implant: soft capsule, chrome band
        cap = fillet(Box(hx, hy, hz).edges(), 1.6)
        out["pad_housing"] = place * cap
        out["chrome"] = place * (Box(hx + 0.5, hy + 0.5, 1.4) - Box(hx - 0.2, hy - 0.2, 1.4))
    anchor = pod.PIVOT
    collar = Pos(*anchor) * Rot(0, 90, 0) * Cylinder(2.0, 4.0)
    out["anchor"] = collar
    return out, geom


def concept_blade():
    """Layered armour plates with a raked front, a circuit-trace glow line, a tail fin."""
    p = {"body": body()}
    y = Y_OUT
    armour = plate([(31.8, 4.3), (57, 4.3), (66.2, 0.5), (66.2, -7.2), (61, -8.6), (37, -8.6), (31.8, -3.6)], y, 0.8, 0.35)
    upper = plate([(34.5, 3.6), (48, 3.6), (45.5, 1.3), (34.5, 1.3)], y + 0.8, 0.5, 0.25)
    trace = [(38.5, -6.8), (51, -6.8), (55.2, -2.6), (63.8, -2.6), (63.8, 2.2)]
    groove = slot(trace, y + 0.8, 0.7, 0.5)
    hexwin = Pos(MIC[0], y + 0.8, MIC[1]) * Rot(90, 0, 0) * extrude(RegularPolygon(1.9, 6), amount=2.0, both=True)
    p["armour"] = (armour - groove - hexwin) + (upper - hexwin)
    p["glow"] = slot(trace, y + 0.72, 0.62, 0.35)
    fin = plate([(50, Z1 - 0.5), (60, Z1 - 0.5), (67.4, Z1 + 2.6), (63.5, Z1 + 2.6)], (Y_IN + Y_OUT) / 2 - 0.6, 1.2)
    p["armour"] = p["armour"] + fin
    # panel lines across the body's top/bottom faces
    for x in (41.0, 55.0):
        p["body"] = p["body"] - Pos(x, (Y_IN + Y_OUT) / 2 + 3, Z1) * Box(0.5, 4.5, 0.6)
    p["body"] = p["body"] - port_hole()
    return p


def concept_heatsink():
    """Cyberdeck: slanted fins over the outer face, a vertical light bar, exposed screw heads."""
    p = {"body": body() - port_hole()}
    y = Y_OUT
    fins = None
    for k in range(9):
        x = 38.5 + k * 2.6
        f = Pos(x, y + 0.45, -2.0) * Rot(0, 25, 0) * Box(0.8, 0.9, 16.0)
        fins = f if fins is None else fins + f
    keep = Pos(49.5, y + 0.45, -2.0) * Box(21.0, 0.9, 12.6)
    fins = fins & keep
    p["armour"] = fins - port_clear(y, y + 2, 2.2)
    p["glow"] = Pos(63.6, y + 0.35, -2.0) * chamfer(Box(1.0, 0.7, 11.0).edges().group_by(Axis.Y)[-1], 0.2)
    p["glow"] = p["glow"] + Pos(35.0, y + 0.3, 3.4) * Box(3.0, 0.6, 0.6) + Pos(35.0, y + 0.3, 2.3) * Box(2.0, 0.6, 0.6)
    screws = None
    for sx, sz in ((32.0, 4.0), (32.0, -8.0), (66.0, 4.0), (66.0, -8.0)):
        head = Pos(sx, y + 0.25, sz) * Rot(90, 0, 0) * Cylinder(0.8, 0.5)
        sock = Pos(sx, y + 0.45, sz) * Rot(90, 0, 0) * extrude(RegularPolygon(0.35, 6), amount=0.3, both=True)
        screws = (head - sock) if screws is None else screws + (head - sock)
    p["metal"] = screws
    # a mic grille ring (cosmetic, around the real port, no length added)
    p["metal"] = p["metal"] + Pos(MIC[0], y + 0.2, MIC[1]) * Rot(90, 0, 0) * (Cylinder(1.5, 0.4) - Cylinder(0.9, 0.4))
    return p


def concept_implant():
    """Two-tone: matte front, chrome rear cap with a stepped seam that glows amber."""
    p = {"body": body() - port_hole()}
    y = Y_OUT
    cap_pts = [(47.0, 5.0), (66.8, 5.0), (66.8, -9.0), (44.0, -9.0), (44.0, -4.5), (49.5, -4.5), (49.5, 0.5), (47.0, 0.5)]
    cap = plate(cap_pts, y, 0.8, 0.5)
    seam_pts = [(45.95, -9.0), (45.95, -3.4), (51.4, -3.4), (51.4, 1.5), (48.9, 1.5), (48.9, 5.0)]
    p["chrome"] = cap - slot(seam_pts, y + 0.8, 0.9, 0.8)
    p["glow"] = slot(seam_pts, y + 0.5, 0.55, 0.5)
    for k in range(3):
        p["glow"] = p["glow"] + Pos(34.0 + 1.6 * k, y + 0.15, -7.2) * Rot(90, 0, 0) * Cylinder(0.45, 0.3)
    # chrome wraps over the top edge as a spine
    p["chrome"] = p["chrome"] + Pos(57.0, (Y_IN + Y_OUT) / 2 + 1.5, Z1 + 0.3) * chamfer(Box(19.6, 5.0, 0.6).edges().group_by(Axis.Z)[-1], 0.3)
    return p


CONCEPTS = {"blade": (concept_blade, "cyan"), "heatsink": (concept_heatsink, "magenta"),
            "implant": (concept_implant, "amber")}


def main():
    info = {}
    for name, (fn, glow) in CONCEPTS.items():
        d = OUT / name
        d.mkdir(parents=True, exist_ok=True)
        for f in d.glob("*.stl"):
            f.unlink()
        parts = fn()
        extra, geom = arm_and_pad(name if name != "implant" else "implant")
        for k, v in extra.items():
            parts[k] = parts[k] + v if k in parts else v
        temple = Pos(40, pod.TEMPLE_T / 2, 0) * chamfer(Box(130, pod.TEMPLE_T, pod.TEMPLE_H).edges(), 0.6)
        parts["temple"] = temple
        vols = {}
        for k, s in parts.items():
            export_stl(s, str(d / f"{k}.stl"), tolerance=0.01, angular_tolerance=0.1)
            vols[k] = round(s.volume, 1)
        bb = parts["body"].bounding_box()
        added = 0.0
        for k in ("armour", "chrome", "metal", "glow"):
            if k in parts:
                b2 = parts[k].bounding_box()
                added = max(added, b2.max.Y - Y_OUT)
        info[name] = {"glow": glow, "volumes_mm3": vols, "adds_thickness_mm": round(added, 2),
                      "front_x": round(min(bb.min.X, *(parts[k].bounding_box().min.X for k in parts if k not in ("temple",))), 2)}
    (OUT / "parts.json").write_text(json.dumps(info, indent=2))
    print(json.dumps({k: {kk: v[kk] for kk in ("adds_thickness_mm", "front_x")} for k, v in info.items()}, indent=2))


if __name__ == "__main__":
    main()
