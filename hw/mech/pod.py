"""Right-side pod, swept transducer arm and pad: parametric first cut (spec §8 v0.9, D1, D18).

    python3 hw/mech/pod.py         # -> hw/mech/out/*.step|stl, renders, mass/balance table

Frame: x = rearward from the hinge along the temple arm, y = outward (lateral, away from the
head), z = up. 0 = the temple arm's centreline at the hinge; the temple arm's inner face is y = 0.
All positions are [Low] until the owner's ruler photo (E9) sets the scale; everything is a
parameter here so the fit can be redone in one run.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
from build123d import Box, Cylinder, Pos, Rot, export_step, export_stl, fillet, Axis

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "tools"))
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)

# ---------------------------------------------------------------- parameters (mm)
TEMPLE_T, TEMPLE_H = 2.5, 5.0     # temple-arm section; typical acetate, MEASURE on her frame (E9)
VISION_X = 29.5                   # pod may not start forward of this (spec §8 v0.9: pupil + 18 mm)
POD_L, POD_W, POD_H = 35.0, 9.0, 14.0   # length (x), thickness (y, outward), height (z)
POD_ZC = -2.0                     # pod centre sits a little below the temple arm (hides under the brow line)
WALL = 0.8                        # PA12 MJF minimum sensible wall
CELL = (30.0, 4.0, 12.0)          # ~105 mAh LiPo (x, y, z), e.g. 401230 class (B4)
PCB = (20.0, 0.8, 11.5)           # 4-layer, 0.8 mm (acoustic port rule, §8)
PCB_PARTS = 1.2                   # tallest part each side (MCU 0.55, crystal 0.8, inductor ~1.0)
SWEEP_DEG = 30.0                  # owner's swept-back arm, 25-35 deg (§8)
PIVOT = (VISION_X + POD_L - 4.0, 0.5, POD_ZC - POD_H / 2 + 1.5)   # rear-lower corner, inside the shell
PAD_DROP = 25.0                   # temple arm to pad centre (ear-open-fit.md, owner's photos)
SKIN_Y = -3.0                     # pre-tragal skin relative to the temple's inner face (E9 rear-oblique photo)
XDCR = (12.6, 4.0, 6.0)           # RC-BC02 per its larger listing: 12.6 x 6 x 4 mm (D7, E1 measures)
PAD_HOUSING_WALL = 0.8
ARM_SECTION = (3.0, 2.0)          # rigid arm (option A): width x thickness

RHO = {"PA12": 1.01e-3, "steel": 7.9e-3}   # g/mm^3; PA12 MJF 1.01 g/cm^3 (JLC material page, check)
MASS_FIXED = {"cell": 3.0, "pcb_assembly": 0.9, "transducer": 1.2, "spring+pin": 0.15, "wires": 0.2}
# cell: 401230-class 105 mAh ~3 g (vendor listings); transducer mass unknown ([Low], E1 weighs it)


def rounded_box(l, w, h, r):
    b = Box(l, w, h)
    return fillet(b.edges(), r) if r > 0 else b


def build():
    parts = {}
    pod_c = (VISION_X + POD_L / 2, TEMPLE_T + POD_W / 2, POD_ZC)
    outer = Pos(*pod_c) * rounded_box(POD_L, POD_W, POD_H, 1.6)
    inner = Pos(*pod_c) * rounded_box(POD_L - 2 * WALL, POD_W - 2 * WALL, POD_H - 2 * WALL, 0.8)
    shell = outer - inner
    # clip: two lips wrap the temple arm's top and bottom edges and hook its inner face
    for zs in (+1, -1):
        z = zs * (TEMPLE_H / 2 + WALL / 2)
        lip = Pos(VISION_X + POD_L / 2, (TEMPLE_T - WALL) / 2, z) * Box(POD_L - 6, TEMPLE_T + WALL, WALL)
        hook = Pos(VISION_X + POD_L / 2, -WALL / 2, zs * (TEMPLE_H / 2 - 0.3)) * Box(POD_L - 6, WALL, 1.4)
        shell = shell + lip + hook
    # mic port through the outer wall at the front, 1.0 mm (§8 acoustic rules)
    mic_xz = (VISION_X + 5.0, POD_ZC + 1.0)
    shell = shell - Pos(mic_xz[0], TEMPLE_T + POD_W - WALL / 2, mic_xz[1]) * Rot(90, 0, 0) * Cylinder(0.5, 3)
    parts["pod_shell"] = (shell, "PA12")

    # contents: cell against the inner wall, PCB outboard (the mic ports outward through it)
    y_cell = TEMPLE_T + WALL + CELL[1] / 2
    parts["cell"] = (Pos(VISION_X + WALL + 0.5 + CELL[0] / 2, y_cell, POD_ZC) * rounded_box(*CELL, 0.8), None)   # pouch cells have ~1 mm rounded edges
    y_pcb = TEMPLE_T + WALL + CELL[1] + 0.2 + PCB_PARTS + PCB[1] / 2
    parts["pcb"] = (Pos(VISION_X + WALL + 0.5 + PCB[0] / 2, y_pcb, POD_ZC) * Box(*PCB), None)
    parts["pcb_parts_envelope"] = (Pos(VISION_X + WALL + 0.5 + PCB[0] / 2, y_pcb, POD_ZC)
                                   * Box(PCB[0] - 1, PCB[1] + 2 * PCB_PARTS, PCB[2] - 1), None)

    # arm: from the pivot, down and back at SWEEP_DEG, and inward to the skin
    px, py, pz = PIVOT
    pad_z = -PAD_DROP
    drop = pz - pad_z
    pad_x = px + drop * math.tan(math.radians(SWEEP_DEG))
    pad_y = SKIN_Y + XDCR[1] / 2 + PAD_HOUSING_WALL          # housing centre; its face touches the skin
    v = np.array([pad_x - px, pad_y - py, pad_z - pz])
    L = float(np.linalg.norm(v))
    # orient a bar along v: rotate about y (sweep) then about x (inward lean)
    sweep = math.degrees(math.atan2(v[0], -v[2]))
    lean = math.degrees(math.atan2(v[1], math.hypot(v[0], v[2])))
    arm = Box(ARM_SECTION[0], ARM_SECTION[1], L)
    arm = Pos(*(np.array(PIVOT) + v / 2)) * Rot(lean, 0, 0) * Rot(0, -sweep, 0) * arm
    parts["arm"] = (arm, "PA12")
    parts["pivot_boss"] = (Pos(*PIVOT) * Rot(0, 90, 0) * Cylinder(2.8, 6.0), "PA12")

    # pad housing around the transducer, long axis ALONG the arm (keeps its top end clear of the
    # Ear (open) hook junction; vertical would come within ~2 mm of it, see tragus-arm.md)
    hx, hy, hz = XDCR[2] + 2 * PAD_HOUSING_WALL, XDCR[1] + 2 * PAD_HOUSING_WALL, XDCR[0] + 2 * PAD_HOUSING_WALL
    housing = Pos(pad_x, pad_y, pad_z) * Rot(0, -sweep, 0) * rounded_box(hx, hy, hz, 1.5)
    parts["pad_housing"] = (housing, "PA12")
    parts["transducer"] = (Pos(pad_x, pad_y, pad_z) * Rot(0, -sweep, 0) * Box(XDCR[2], XDCR[1], XDCR[0]), None)
    # silicone contact pad, 8 x 10 mm oval approximated by a cylinder on the inner face
    parts["silicone_pad"] = (Pos(pad_x, SKIN_Y + 0.4, pad_z) * Rot(90, 0, 0) * Cylinder(4.5, 0.8), None)
    temple = Pos(55, TEMPLE_T / 2, 0) * Box(110, TEMPLE_T, TEMPLE_H)
    geom = {"pad_centre": (pad_x, SKIN_Y, pad_z), "arm_length": L, "sweep_deg": sweep}
    return parts, temple, geom


def masses(parts):
    rows, tot, mx = [], 0.0, 0.0
    for name, (shape, mat) in parts.items():
        if mat is None:
            continue
        m = shape.volume * RHO[mat]
        rows.append((name, m, shape.center().X))
    c = {k: v for k, v in ((n, (s, m)) for n, (s, m) in parts.items())}
    fixed_pos = {"cell": c["cell"][0].center().X, "pcb_assembly": c["pcb"][0].center().X,
                 "transducer": c["transducer"][0].center().X, "spring+pin": PIVOT[0],
                 "wires": PIVOT[0]}
    for k, m in MASS_FIXED.items():
        rows.append((k, m, fixed_pos[k]))
    tot = sum(m for _, m, _ in rows)
    mx = sum(m * x for _, m, x in rows) / tot
    return rows, tot, mx


def render(parts, temple, geom):
    sys.path.insert(0, str(REPO / "tools"))
    import plotstyle
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    plt = plotstyle.apply()
    colours = {"pod_shell": ("#d9d6cc", 0.35), "cell": (plotstyle.SERIES[3], 1.0), "pcb": (plotstyle.SERIES[5], 1.0),
               "pcb_parts_envelope": (plotstyle.SERIES[5], 0.25), "arm": ("#8a8676", 1.0), "pivot_boss": ("#8a8676", 1.0),
               "pad_housing": ("#d9d6cc", 0.5), "transducer": (plotstyle.SERIES[1], 1.0),
               "silicone_pad": (plotstyle.SERIES[0], 0.45)}
    light = np.array([0.4, 0.6, 0.7])
    light /= np.linalg.norm(light)
    views = [("Side view from outside (face is to the right)", (0, 90)),
             ("3/4 view from behind, outside", (22, 130)),
             ("From behind (head is to the left)", (0, 0))]
    fig = plt.figure(figsize=(13, 5))
    for i, (title, (el, az)) in enumerate(views):
        ax = fig.add_subplot(1, 3, i + 1, projection="3d", proj_type="ortho" if i != 1 else "persp")
        items = [("temple", temple, (plotstyle.TEXT_2, 0.25))] + [(n, s, colours[n]) for n, (s, _) in parts.items()]
        for name, shape, (col, alpha) in items:
            vs, tris = shape.tessellate(0.05)
            V = np.array([[p.X, p.Y, p.Z] for p in vs])
            T = np.array(tris)
            n = np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]])
            n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
            shade = 0.45 + 0.55 * np.abs(n @ light)
            base = np.array(matplotlib_to_rgb(col))
            fc = np.clip(base[None, :] * shade[:, None], 0, 1)
            pc = Poly3DCollection(V[T], facecolors=np.c_[fc, np.full(len(fc), alpha)], edgecolors="none")
            ax.add_collection3d(pc)
        ax.set_xlim(25, 80)
        ax.set_ylim(-20, 20)
        ax.set_zlim(-35, 10)
        ax.set_box_aspect((55, 40, 45))
        for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
            axis.set_pane_color(plotstyle.SURFACE)
        ax.view_init(elev=el, azim=az)
        ax.set_title(title)
        if i == 0:
            ax.plot([VISION_X] * 2, [TEMPLE_T + POD_W] * 2, [-30, 8], color=plotstyle.SERIES[7], lw=1.2)
            ax.text(VISION_X, TEMPLE_T + POD_W, 9, "vision limit", color=plotstyle.SERIES[7], fontsize=7)
        ax.set_xlabel("x back (mm)")
        ax.set_ylabel("y out")
        ax.set_zlabel("z up")
    fig.savefig(OUT / "pod_views.png")


def matplotlib_to_rgb(c):
    from matplotlib.colors import to_rgb
    return to_rgb(c)


def main():
    parts, temple, geom = build()
    for name, (shape, _) in parts.items():
        export_step(shape, str(OUT / f"{name}.step"))
        if name in ("pod_shell", "arm", "pad_housing", "pivot_boss"):
            export_stl(shape, str(OUT / f"{name}.stl"))
    rows, tot, mx = masses(parts)
    L_EAR = 100.0
    nose, ear = tot * (1 - mx / L_EAR), tot * mx / L_EAR
    # collisions: contents must sit inside the shell cavity without touching each other
    clash = {}
    for a, b in (("cell", "pcb_parts_envelope"), ("cell", "pod_shell"), ("pcb_parts_envelope", "pod_shell")):
        clash[f"{a}/{b}"] = round((parts[a][0] & parts[b][0]).volume, 2)
    summary = {"geometry": {k: (np.round(v, 1).tolist() if isinstance(v, tuple) else round(v, 1)) for k, v in geom.items()},
               "masses_g": {n: round(m, 2) for n, m, _ in rows}, "total_g": round(tot, 2),
               "centre_of_mass_x_mm": round(mx, 1), "nose_g": round(nose, 2), "ear_g": round(ear, 2),
               "interference_mm3": clash}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    render(parts, temple, geom)


if __name__ == "__main__":
    main()
