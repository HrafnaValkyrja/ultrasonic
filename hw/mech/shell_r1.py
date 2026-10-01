"""Rev-1 pod shell (owner decisions O12/O15/O16, 2026-10-01): bonded, screwless, bigger for testing.

    python3 hw/mech/shell_r1.py      # -> hw/mech/out/r1/<concept>/*.stl + parts.json, checks printed

What changed from hw/mech/shell.py (round-1 agent, screwed lid):
- NO screws in the housing. The lid locates on a 0.5 mm lip inside the tub opening and is taped for
  testing, then bonded (MS-polymer / neutral RTV). An outer V-groove marks the seam as a cut line.
- Cell Renata ICP501233PA-02 (35 x 12 x 5.3, PCM inside); PCB rev 1 = 28 x 13 x 0.8.
- 'Belly' under the front 25 mm holds the magnetic dock target (Xinyangze YZT0675, 21.2 x 6.86 x
  2.8, LCSC C5126848) flush in the floor; its rear step face is where a sealed USB-C (Same Sky UJ32,
  6.75 x 8.55 x 2.76) would open if the magnetic part fails (keep-out reserved). The rear stays
  shallow so the NiTi strut keeps its clearance.
- Mic port and IP68 switch (C&K KMT022) on the board centre line, so one board fits both pods.
  The switch is pressed through a printed plunger under a bonded silicone skin (sealing).
- The heel (NiTi root) is hw/mech/heel.py, unioned as before; pad parts are unchanged.
- TOP/FIN: four interchangeable concepts (owner: "completely redesign the top and the fin ...
  based on similar fictional cyberware"). Non-functional, printed as part of the lid.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from build123d import (Axis, Box, Cylinder, Pos, Rot, RegularPolygon, chamfer, export_stl, extrude,
                       import_step, Polygon)

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import blade  # noqa: E402
import frame as F  # noqa: E402
from styles import plate, slot  # noqa: E402

OUT = HERE / "out" / "r1"
X0, X1 = 29.5, 67.5
Y_IN, Y_SPLIT, Y_OUT = 4.3, 14.4, 15.4
Z1, Z0, Z_BELLY, X_BELLY = 5.5, -9.7, -13.2, 55.0
W = 0.8
CAV = dict(x0=X0 + W, x1=X1 - W, y0=Y_IN + W, z0=Z0 + W, z1=Z1 - W)            # main cavity
BAY = dict(x0=X0 + W, x1=X_BELLY - W, z0=Z_BELLY + W, z1=CAV["z0"])            # connector bay
ZC = (CAV["z0"] + CAV["z1"]) / 2                                               # board centre line
CELL = dict(x0=30.6, x1=65.6, y0=5.4, y1=10.7, z0=ZC - 6.0, z1=ZC + 6.0)
PCB = dict(x0=30.6, x1=58.6, y0=12.1, y1=12.9, z0=ZC - 6.5, z1=ZC + 6.5)
PARTS = [dict(y0=10.9, y1=12.1), dict(y0=12.9, y1=14.1)]
MIC = (34.5, ZC)
SWITCH = (52.6, ZC)          # board x 22.0 (hw/pod/place_r1.py): clear of the MCU
DOCK = dict(x0=31.5, x1=52.7, y0=9.75 - 3.43, y1=9.75 + 3.43, z0=Z_BELLY, z1=Z_BELLY + 2.8)
USBC_KEEPOUT = dict(x0=47.9, x1=X_BELLY, y0=9.75 - 4.3, y1=9.75 + 4.3, z0=BAY["z0"], z1=BAY["z0"] + 2.8)


def box(x0, x1, y0, y1, z0, z1):
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(x1 - x0, y1 - y0, z1 - z0)


def outer_body():
    main = chamfer(box(X0, X1, Y_IN, Y_OUT, Z0, Z1).edges(), 1.0)
    belly = chamfer(box(X0, X_BELLY, Y_IN, Y_OUT, Z_BELLY, Z0 + 1.5).edges(), 1.0)
    return main + belly


def cavity():
    return box(CAV["x0"], CAV["x1"], CAV["y0"], Y_SPLIT + 1, CAV["z0"], CAV["z1"]) + \
        box(BAY["x0"], BAY["x1"], CAV["y0"], Y_SPLIT + 1, BAY["z0"], BAY["z1"] + 0.01)


def seam_groove():
    """0.4 x 0.4 V-ish groove around the outside at the seam: the cut line for reopening."""
    band = box(X0 - 1, X1 + 1, Y_SPLIT - 0.2, Y_SPLIT + 0.2, Z_BELLY - 1, Z1 + 1)
    return band - box(X0 + 0.4, X1 - 0.4, Y_SPLIT - 0.3, Y_SPLIT + 0.3, Z0 + 0.4, Z1 - 0.4) - box(X0 + 0.4, X_BELLY - 0.4, Y_SPLIT - 0.3, Y_SPLIT + 0.3, Z_BELLY + 0.4, Z0 + 1.0)


def tub(heel_mod=None):
    t = outer_body() & box(X0 - 1, X1 + 1, Y_IN - 1, Y_SPLIT, Z_BELLY - 1, Z1 + 1)
    t = t + blade.rail()
    if heel_mod is not None:
        t = t + heel_mod.heel_add()
    t = t - cavity()
    if heel_mod is not None:
        t = t - heel_mod.heel_cut()
    t = t - box(DOCK["x0"] - 0.1, DOCK["x1"] + 0.1, DOCK["y0"] - 0.1, DOCK["y1"] + 0.1, Z_BELLY - 1, DOCK["z1"])  # dock window
    # strut relief (2026-10-01): the NiTi strut passes 0.65 mm from the inner-bottom rear edge. Fill the
    # cavity's corner there (the cell's corner clears it by ~0.07 mm on the tape side), then cut the outside
    # corner back on the line y + z = -3.65, keeping 0.6 mm of wall. Local to x 62-68, outboard of the
    # NiTi socket (y >= 3.9), so the heel's socket and wire channel are untouched.
    cz = CAV["z0"]
    t = t + blade.prism_yz([(CAV["y0"], cz), (CAV["y0"] + 1.0, cz), (CAV["y0"], cz + 1.0)], 62.0, CAV["x1"])
    t = t - blade.prism_yz([(3.9, -12.5), (3.9, -3.65 - 3.9), (-3.65 + 12.5, -12.5)], 62.0, 68.5)
    return t - seam_groove()


def lid_base():
    l = outer_body() & box(X0 - 1, X1 + 1, Y_SPLIT, Y_OUT + 1, Z_BELLY - 1, Z1 + 1)
    lip_o = box(CAV["x0"] + 0.15, CAV["x1"] - 0.15, Y_SPLIT - 0.8, Y_SPLIT, CAV["z0"] + 0.15, CAV["z1"] - 0.15)
    lip_i = box(CAV["x0"] + 0.65, CAV["x1"] - 0.65, Y_SPLIT - 0.9, Y_SPLIT, CAV["z0"] + 0.65, CAV["z1"] - 0.65)
    l = l + (lip_o - lip_i)
    # armour face plate + circuit trace (Blade language, re-proportioned for rev 1)
    pts = [(31.8, 4.0), (46.0, 4.0), (47.8, 5.0), (66.2, 5.0), (66.2, -8.2), (61.0, -9.3), (55.0, -9.3),
           (53.5, -12.4), (34.5, -12.4), (31.8, -10.0)]
    l = l + plate(pts, Y_OUT, 0.7, 0.3)
    trace = [(36.5, -11.0), (51.0, -11.0), (55.5, -6.0), (63.8, -6.0), (63.8, 2.6)]
    l = l - slot(trace, Y_OUT + 0.7, 0.7, 0.45)
    l = l - Pos(MIC[0], Y_OUT, MIC[1]) * Rot(90, 0, 0) * Cylinder(0.5, 6.0)                 # mic port
    l = l - Pos(MIC[0], Y_OUT + 0.7, MIC[1]) * Rot(90, 0, 0) * extrude(RegularPolygon(1.9, 6), amount=0.8, both=True)
    l = l - Pos(SWITCH[0], Y_OUT, SWITCH[1]) * Rot(90, 0, 0) * Cylinder(1.6, 6.0)           # plunger bore
    l = l - Pos(SWITCH[0], Y_OUT + 0.7, SWITCH[1]) * Rot(90, 0, 0) * Cylinder(2.6, 0.5)     # skin recess
    # board retention (no screws): two ribs press the board's outer-face clamp bands (no parts within
    # 0.6 mm of its top/bottom edges); foam strips on the cell push it up against them
    for zb in (PCB["z1"] - 0.6, PCB["z0"]):
        l = l + box(PCB["x0"] + 0.5, PCB["x1"] - 0.5, PCB["y1"] + 0.05, Y_SPLIT + 0.01, zb, zb + 0.6)
    return l


def plunger():
    head = Pos(SWITCH[0], Y_OUT + 0.25, SWITCH[1]) * Rot(90, 0, 0) * Cylinder(1.45, 0.9)
    stem = Pos(SWITCH[0], (14.2 + Y_OUT) / 2, SWITCH[1]) * Rot(90, 0, 0) * Cylinder(0.6, Y_OUT - 14.2)
    return head + stem


# ----------------------------------------------------------------------------- top/fin concepts
TOP_Y0, TOP_Y1 = 8.5, Y_OUT + 0.7      # footprint across the top face (outer half, flush with the plate)


def concept_spine():
    """'Spine': vertebra-like segments stepping up toward the rear on a low rail (Sandevistan-style
    spinal cyberware)."""
    s = chamfer(box(44.0, 66.8, 10.5, 14.6, Z1, Z1 + 0.6).edges().group_by(Axis.Z)[-1], 0.3)
    for i, x in enumerate((46.0, 49.4, 52.8, 56.2, 59.6, 63.0)):
        h = 0.9 + 0.32 * i
        seg = box(x, x + 2.4, 10.2, 14.9, Z1 + 0.6, Z1 + 0.6 + h)
        seg = chamfer(seg.edges().group_by(Axis.Z)[-1], min(0.5, h * 0.45))
        s = s + seg
    return s


def concept_blade():
    """'Blade': a single swept knife edge leaning outward, raked trailing edge, bevelled flank
    (forearm-blade housings)."""
    prof = [(45.0, Z1), (60.0, Z1 + 1.6), (66.4, Z1 + 3.1), (67.3, Z1 + 1.2), (67.3, Z1)]
    f = blade.prism_xz(prof, 12.3, 14.1)
    bevel = blade.prism_yz([(12.3, Z1 + 0.9), (12.3, Z1 + 4.0), (13.0, Z1 + 4.0)], 44.0, 68.0)
    return (f - bevel) + chamfer(box(44.0, 67.0, 11.0, 15.0, Z1, Z1 + 0.5).edges().group_by(Axis.Z)[-1], 0.25)


def concept_radiator():
    """'Radiator': thin transverse fins stepping in height, like a cyberdeck heatsink."""
    r = box(46.0, 66.6, 9.6, 15.0, Z1, Z1 + 0.4)
    for i, x in enumerate(range(47, 66, 2)):
        h = 0.8 + 0.12 * i
        r = r + chamfer(box(x, x + 0.7, 9.8, 14.8, Z1 + 0.4, Z1 + 0.4 + h).edges().group_by(Axis.Z)[-1], 0.2)
    return r


def concept_scales():
    """'Scales': three overlapping armour plates stepping back, each tilted (layered augment armour)."""
    s = None
    for i, (xa, xb) in enumerate(((44.5, 53.0), (51.0, 59.5), (57.5, 66.8))):
        h0, h1 = 0.4 + 0.5 * i, 1.0 + 0.6 * i
        pl = blade.prism_xz([(xa, Z1), (xb, Z1), (xb, Z1 + h1), (xa + 1.2, Z1 + h0)], 9.4 + 0.4 * i, 15.0)
        pl = chamfer(pl.edges().filter_by(Axis.Y), 0.2)
        s = pl if s is None else s + pl
    return s


CONCEPTS = {"spine": concept_spine, "blade": concept_blade, "radiator": concept_radiator, "scales": concept_scales}


def placeholders():
    return {
        "cell": box(CELL["x0"], CELL["x1"], CELL["y0"], CELL["y1"], CELL["z0"], CELL["z1"]),
        "pcb": box(PCB["x0"], PCB["x1"], PCB["y0"], PCB["y1"], PCB["z0"], PCB["z1"]),
        "parts_in": box(PCB["x0"] + 0.5, PCB["x1"] - 0.5, PARTS[0]["y0"], PARTS[0]["y1"], PCB["z0"] + 0.6, PCB["z1"] - 0.6),
        "parts_out": box(PCB["x0"] + 0.5, PCB["x1"] - 0.5, PARTS[1]["y0"], PARTS[1]["y1"], PCB["z0"] + 0.6, PCB["z1"] - 0.6)
        - box(SWITCH[0] - 1.6, SWITCH[0] + 1.6, 12.8, 14.2, SWITCH[1] - 1.6, SWITCH[1] + 1.6),
        "switch": box(SWITCH[0] - 1.5, SWITCH[0] + 1.5, 12.9, 13.55, SWITCH[1] - 1.3, SWITCH[1] + 1.3),
        "dock": box(DOCK["x0"], DOCK["x1"], DOCK["y0"], DOCK["y1"], DOCK["z0"], DOCK["z1"]),
        # 1.5 mm closed-cell foam strips under the board's inner-face clamp bands, compressed to 1.4
        "foam_top": box(PCB["x0"] + 1.0, PCB["x1"] - 1.0, CELL["y1"], PCB["y0"], PCB["z1"] - 0.6, PCB["z1"]),
        "foam_bot": box(PCB["x0"] + 1.0, PCB["x1"] - 1.0, CELL["y1"], PCB["y0"], PCB["z0"], PCB["z0"] + 0.6),
    }


def main():
    import heel
    t = tub(heel)
    ph = placeholders()
    checks = {}
    lid0 = lid_base()
    for k, s in ph.items():
        for name, part in (("tub", t), ("lid", lid0)):
            v = (part & s).volume
            if k == "dock" and name == "tub":
                continue
            checks[f"{name}/{k}"] = round(v, 3)
    checks["tub/lid"] = round((t & lid0).volume, 3)
    print(json.dumps(checks, indent=1))
    pad = HERE / "out/parts/pad"
    common = {"tub": (t, "body", (0, 0, 0)), "plunger": (plunger(), "metal", (0, 12, 0)),
              **{k: (v, {"cell": "cell", "pcb": "pcb", "parts_in": "chips", "parts_out": "chips",
                          "switch": "metal", "dock": "metal", "foam_top": "silicone", "foam_bot": "silicone"}[k], (0, {"cell": 5, "dock": -8}.get(k, 9), 0))
                 for k, v in ph.items()}}
    steps = {"pad_cup": ("pad_cup.step", "body", (0, -6, 0)), "transducer": ("ref_transducer_RC-BC02.step", "transducer", (0, -2, 0)),
             "pad_board": ("pad_board_led.step", "pcb", (0, 2, 0)), "pad_cap": ("pad_cap_strut.step", "armour", (0, 5, 0)),
             "diffuser": ("pad_diffuser_epoxy.step", "glow", (0, 7, 0)), "contact": ("pad_contact_silicone.step", "silicone", (0, -9, 0))}
    for k, (f, m, off) in steps.items():
        common[k] = (import_step(pad / f), m, off)
    common["niti"] = (import_step(HERE / "out/parts/heel/niti_root_worn.step"), "niti", (0, 0, 0))
    common["adapter"] = (blade.adapter(), "adapter", (0, -4, 0))
    common["temple"] = (Pos(40, F.TEMPLE_T / 2, 0) * chamfer(Box(130, F.TEMPLE_T, F.TEMPLE_H).edges(), 0.6), "temple", (0, -4, 0))
    for cname, fn in CONCEPTS.items():
        d = OUT / cname
        d.mkdir(parents=True, exist_ok=True)
        info = {}
        lid = lid0 + fn()
        for k, (s, m, off) in {**common, "lid": (lid, "armour", (0, 14, 0))}.items():
            export_stl(s, str(d / f"{k}.stl"), tolerance=0.01, angular_tolerance=0.1)
            info[k] = {"mat": m, "explode": off}
        (d / "parts.json").write_text(json.dumps(info, indent=1))
    (OUT / "checks.json").write_text(json.dumps(checks, indent=1))


if __name__ == "__main__":
    main()
