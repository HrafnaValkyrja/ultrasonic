"""Right-side pod, swept transducer arm and pad: rev 2 (spec §8, D1, D18; audit mech/CAD findings).

    python3 hw/mech/pod.py         # -> hw/mech/out/*.step|stl, renders, mass/balance, clearances

Rev 2 (2026-09-30): cell at the EEMB LP401230 spec-sheet MAXIMUM envelope plus its protection
board (the audit found the nominal box hid a clash); pod grown to fit; arm modelled as the real
NiTi wire (owner O7) in two variants: A = today's 20 mm arm on the plateau, B = 30 mm elastic
arm (sim/checks/niti_closed_form.py), anchored further forward so the pad stays where it was;
minimum-gap checks between every pair of parts.

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

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(HERE))
import frame as F  # noqa: E402  (CAD-free; build123d is imported inside the build functions, so tools can read this module)
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)

# ---------------------------------------------------------------- parameters (mm)
TEMPLE_T, TEMPLE_H = F.TEMPLE_T, F.TEMPLE_H   # temple-arm section 2.5 x 5.0; typical acetate, MEASURE on her frame (E9)
VISION_X = 29.5                   # pod may not start forward of this (spec §8 v0.9: pupil + 18 mm)
# pod body = the CURRENT design (frame.pod_facts(), ECR-0001 2026-10-07); blade.py builds its rail, adapter, shell() on these.
# Phase 2: 38.0 x 9.7 x 14.5, centre z -2.45 (was the rev-2 sketch's 38 x 10 x 15 at -2.0, still used by build() below).
POD_L, POD_W, POD_H = F.X1 - F.X0, F.Y_OUT - F.Y_IN, F.Z1 - F.Z0
POD_ZC = (F.Z0 + F.Z1) / 2        # body centre (Phase 2 = the board/cavity centre line)
assert abs(F.X0 - VISION_X) < 1e-9, "the pod front moved off the vision limit: re-check blade.py X0"

# ---- rev-2 sketch (2026-09-30, pre-rev-1): build() below is kept as the historical arm-variant study and keeps its own
# envelope and contents. NOT the current pod (cell, board and body come from frame.pod_facts()).
REV2_POD = (38.0, 10.0, 15.0, -2.0)   # L, W, H, centre z (was 35 x 9 x 14; grown for the max cell + PCM + clearances)
CLR = 0.3                         # assembly clearance to walls (MJF +-0.2 mm)
WALL = 0.8                        # PA12 MJF minimum sensible wall
CELL = (31.0, 4.3, 12.5)          # LP401230 MAX envelope (EEMB spec ZJQM-RD-SPC-H2294, 2022-10-19)
PCM = (3.0, 4.3, 12.5)            # protection board on the cell's end [Low]: typical, MEASURE (B4)
PCB = (20.0, 0.8, 11.5)           # 4-layer, 0.8 mm (acoustic port rule, §8)
PCB_PARTS = 1.2                   # tallest part each side (MCU 0.55, crystal 0.8, inductor ~1.0)
SWEEP_DEG = 30.0                  # owner's swept-back arm, 25-35 deg (§8), variant A
# the pad location is anatomy, so it is fixed from rev 1 (35 x 14 pod, anchor 4 mm from its rear)
PIVOT = (VISION_X + 35.0 - 4.0, 0.5, -2.0 - 14.0 / 2 + 1.5)
SLEEVE_D = 1.8                    # sleeve over the NiTi wire (wire: frame.NITI_D)
                                  # sleeve also carries the two transducer wires (docs/diagrams/arm-wiring.svg)
ARM_L = {"A": None, "B": 30.0}    # free length; None = straight from PIVOT at SWEEP_DEG (~20 mm)
PAD_DROP = 25.0                   # temple arm to pad centre (ear-open-fit.md, owner's photos)
SKIN_Y = -3.0                     # pre-tragal skin relative to the temple's inner face (E9 rear-oblique photo)
XDCR = (12.6, 4.0, 6.0)           # RC-BC02 per its larger listing: 12.6 x 6 x 4 mm (D7, E1 measures)
PAD_HOUSING_WALL = 0.8

RHO = {"PA12": 1.01e-3, "steel": 7.9e-3, "silicone": 1.1e-3}   # g/mm^3; PA12 MJF 1.01 g/cm^3 (JLC material page, check)
MASS_FIXED = {"cell": 2.2, "pcb_assembly": 0.9, "transducer": 1.2, "wire+sleeve": 0.2, "wires": 0.2}
# cell: 401230-class 105 mAh ~3 g (vendor listings); transducer mass unknown ([Low], E1 weighs it)


def rounded_box(l, w, h, r):
    from build123d import Box, fillet
    b = Box(l, w, h)
    return fillet(b.edges(), r) if r > 0 else b


def build(variant="A"):
    from build123d import Box, Cylinder, Pos, Rot
    POD_L, POD_W, POD_H, POD_ZC = REV2_POD
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
    y_cell = TEMPLE_T + WALL + CLR + CELL[1] / 2
    x0 = VISION_X + WALL + CLR
    parts["cell"] = (Pos(x0 + CELL[0] / 2, y_cell, POD_ZC) * rounded_box(*CELL, 0.8), None)   # pouch cells have ~1 mm rounded edges
    parts["pcm"] = (Pos(x0 + CELL[0] + 0.2 + PCM[0] / 2, y_cell, POD_ZC) * rounded_box(*PCM, 0.5), None)   # PCM is wrapped in tape with the tabs: rounded
    y_pcb = TEMPLE_T + WALL + CLR + CELL[1] + 0.2 + PCB_PARTS + PCB[1] / 2
    parts["pcb"] = (Pos(VISION_X + WALL + 0.5 + PCB[0] / 2, y_pcb, POD_ZC) * Box(*PCB), None)
    parts["pcb_parts_envelope"] = (Pos(VISION_X + WALL + 0.5 + PCB[0] / 2, y_pcb, POD_ZC)
                                   * Box(PCB[0] - 1, PCB[1] + 2 * PCB_PARTS, PCB[2] - 1), None)

    # arm: from the pivot, down and back at SWEEP_DEG, and inward to the skin
    px, py, pz = PIVOT
    pad_z = -PAD_DROP
    drop = pz - pad_z
    pad_x = px + drop * math.tan(math.radians(SWEEP_DEG))
    pad_y = SKIN_Y + XDCR[1] / 2 + PAD_HOUSING_WALL          # housing centre; its face touches the skin
    # wire ends at the housing's upper edge, not its centre
    end = np.array([pad_x, pad_y, pad_z])
    if ARM_L[variant]:   # slide the anchor forward along the pod floor until the free length is ARM_L
        dy, dz = end[1] - py, end[2] - pz
        px = end[0] - math.sqrt(ARM_L[variant] ** 2 - dy ** 2 - dz ** 2)
    anchor = (px, py, pz)
    v = end - np.array(anchor)
    L = float(np.linalg.norm(v))
    # orient a bar along v: rotate about y (sweep) then about x (inward lean)
    sweep = math.degrees(math.atan2(v[0], -v[2]))
    lean = math.degrees(math.atan2(v[1], math.hypot(v[0], v[2])))
    # the sleeve stops short of both ends so the gap checks see only the free span
    arm = Cylinder(SLEEVE_D / 2, L - 7.0)
    arm = Pos(*(np.array(anchor) + v / 2)) * Rot(lean, 0, 0) * Rot(0, -sweep, 0) * arm
    parts["arm"] = (arm, "silicone")
    # anchor boss on the pod floor with the curved root support (strain relief, tragus-arm.md)
    parts["anchor_boss"] = (Pos(*anchor) * Rot(0, 90, 0) * Cylinder(2.2, 5.0), "PA12")

    # pad housing around the transducer, long axis ALONG the arm (keeps its top end clear of the
    # Ear (open) hook junction; vertical would come within ~2 mm of it, see tragus-arm.md)
    hx, hy, hz = XDCR[2] + 2 * PAD_HOUSING_WALL, XDCR[1] + 2 * PAD_HOUSING_WALL, XDCR[0] + 2 * PAD_HOUSING_WALL
    housing = Pos(pad_x, pad_y, pad_z) * Rot(0, -sweep, 0) * rounded_box(hx, hy, hz, 1.5)
    parts["pad_housing"] = (housing, "PA12")
    parts["transducer"] = (Pos(pad_x, pad_y, pad_z) * Rot(0, -sweep, 0) * Box(XDCR[2], XDCR[1], XDCR[0]), None)
    # silicone contact pad, 8 x 10 mm oval approximated by a cylinder on the inner face
    parts["silicone_pad"] = (Pos(pad_x, SKIN_Y + 0.4, pad_z) * Rot(90, 0, 0) * Cylinder(4.5, 0.8), None)
    temple = Pos(55, TEMPLE_T / 2, 0) * Box(110, TEMPLE_T, TEMPLE_H)
    geom = {"variant": variant, "pad_centre": (pad_x, SKIN_Y, pad_z), "arm_length": L, "sweep_deg": sweep,
            "anchor_x": px}
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
                 "transducer": c["transducer"][0].center().X, "wire+sleeve": c["arm"][0].center().X,
                 "wires": c["anchor_boss"][0].center().X}
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
               "pcb_parts_envelope": (plotstyle.SERIES[5], 0.25), "arm": ("#8a8676", 1.0), "anchor_boss": ("#8a8676", 1.0), "pcm": (plotstyle.SERIES[4], 1.0),
               "pad_housing": ("#d9d6cc", 0.5), "transducer": (plotstyle.SERIES[1], 1.0),
               "silicone_pad": (plotstyle.SERIES[0], 0.45)}
    light = np.array([0.4, 0.6, 0.7])
    light /= np.linalg.norm(light)
    views = [("Side view from outside (face is to the right)", (0, 90)),
             ("3/4 view from behind, outside", (22, 130)),
             ("From behind (head is to the left)", (0, 0))]
    POD_W = REV2_POD[1]
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
    L = geom["arm_length"]
    fig.suptitle(f"Pod rev 2, arm variant {geom['variant']}: NiTi wire {L:.0f} mm free length, "
                 f"{geom['sweep_deg']:.0f} deg sweep", color=plotstyle.TEXT, fontsize=12)
    fig.savefig(OUT / f"pod_views_{geom['variant']}.png")


def matplotlib_to_rgb(c):
    from matplotlib.colors import to_rgb
    return to_rgb(c)


def sketch_sheet(builds):
    """2 x 2 dark 'sketch' sheet: variants A and B, side view and 3/4 view, axes hidden, labelled."""
    import plotstyle
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    plt = plotstyle.apply()
    col = {"pod_shell": ("#d9d6cc", 0.22), "cell": (plotstyle.SERIES[3], 0.95), "pcm": (plotstyle.SERIES[4], 0.95),
           "pcb": (plotstyle.SERIES[5], 1.0), "pcb_parts_envelope": (plotstyle.SERIES[5], 0.2),
           "arm": ("#b8b4a4", 1.0), "anchor_boss": ("#8a8676", 1.0), "pad_housing": ("#d9d6cc", 0.45),
           "transducer": (plotstyle.SERIES[1], 1.0), "silicone_pad": (plotstyle.SERIES[0], 0.5)}
    light = np.array([0.3, 0.7, 0.65]); light /= np.linalg.norm(light)
    POD_L, POD_W, POD_H, POD_ZC = REV2_POD
    fig = plt.figure(figsize=(14, 10))
    for r, (variant, (parts, temple, geom)) in enumerate(builds.items()):
        for c, (title, el, az, persp) in enumerate((("side, from outside", 0, -90, False),
                                                     ("3/4 from behind and outside", 18, -135, True))):
            ax = fig.add_subplot(2, 2, 2 * r + c + 1, projection="3d", proj_type="persp" if persp else "ortho")
            items = [("temple", temple, (plotstyle.TEXT_2, 0.18))] + [(n, sh, col[n]) for n, (sh, _) in parts.items()]
            for name, shape, (cc, alpha) in items:
                vs, tris = shape.tessellate(0.03)
                V = np.array([[p.X, p.Y, p.Z] for p in vs]); T = np.array(tris)
                nrm = np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]])
                nrm /= np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-12
                shade = 0.4 + 0.6 * np.abs(nrm @ light)
                fc = np.clip(np.array(matplotlib_to_rgb(cc))[None, :] * shade[:, None], 0, 1)
                ax.add_collection3d(Poly3DCollection(V[T], facecolors=np.c_[fc, np.full(len(fc), alpha)], edgecolors="none"))
            ax.set_xlim(26, 80); ax.set_ylim(-20, 20); ax.set_zlim(-33, 9)
            ax.set_box_aspect((54, 40, 42))
            ax.view_init(elev=el, azim=az)
            ax.set_axis_off()
            if c == 0:
                ax.plot([VISION_X] * 2, [0, 0], [-31, 8], color=plotstyle.SERIES[7], lw=1.2)
                ax.text(VISION_X - 1, 0, -32, "vision\nlimit", color=plotstyle.SERIES[7], fontsize=8, ha="right")
                px, _, pz = geom["pad_centre"]
                ax.text(px + 4, 0, pz - 8, "tragus pad\n(transducer)", color=plotstyle.SERIES[1], fontsize=8)
                ax.text(VISION_X + POD_L / 2, 0, POD_ZC + POD_H / 2 + 2.5,
                        f"pod {POD_L:.0f} x {POD_W:.0f} x {POD_H:.0f} mm: cell (max) + PCM | board 20 x 11.5",
                        color=plotstyle.TEXT, fontsize=8, ha="center")
                ax.text(VISION_X + 2, 0, -24, "<- toward the face", color=plotstyle.TEXT_2, fontsize=8)
            L = geom["arm_length"]
            label = {"A": "A: today's arm, 20 mm, rides the NiTi plateau\n1.0-2.3 N depending on jaw history, 4-7 % strain",
                     "B": "B: 30 mm elastic arm, anchor moved forward\n0.7-1.3 N, linear, ~1.3 % strain, no hysteresis"}[variant]
            ax.set_title(f"{label}\n({title})" if c == 0 else title, fontsize=10, color=plotstyle.TEXT)
    fig.suptitle("Pod rev 2: 3D sketches. Same pad position; two NiTi arm options (O7 reopened)",
                 fontsize=13, color=plotstyle.TEXT)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.9, bottom=0.02, wspace=0.02, hspace=0.12)
    fig.savefig(OUT / "pod_sketches.png", dpi=130)


GAP_PAIRS = [("cell", "pod_shell"), ("pcm", "pod_shell"), ("pcb_parts_envelope", "pod_shell"),
             ("cell", "pcb_parts_envelope"), ("pcm", "pcb_parts_envelope"), ("pad_housing", "pod_shell"),
             ("arm", "pod_shell"), ("pad_housing", "anchor_boss")]
MIN_GAP = 0.2        # mm: MJF tolerance ~+-0.2 (JLC), so anything under this is a clash in practice


def main():
    from build123d import export_step, export_stl
    out, builds = {}, {}
    for variant in ("A", "B"):
        parts, temple, geom = build(variant)
        builds[variant] = (parts, temple, geom)
        for name, (shape, _) in parts.items():
            export_step(shape, str(OUT / f"{name}_{variant}.step"))
            if name in ("pod_shell", "pad_housing", "anchor_boss"):
                export_stl(shape, str(OUT / f"{name}_{variant}.stl"))
        rows, tot, mx = masses(parts)
        L_EAR = 100.0
        gaps = {}
        for a, b in GAP_PAIRS:
            inter = (parts[a][0] & parts[b][0]).volume
            gaps[f"{a}/{b}"] = -round(inter, 2) if inter > 1e-3 else round(parts[a][0].distance_to(parts[b][0]), 2)
        bad = {k: g for k, g in gaps.items() if g < MIN_GAP}
        out[variant] = {"geometry": {k: (np.round(v, 1).tolist() if isinstance(v, tuple) else (round(v, 1) if isinstance(v, float) else v))
                                     for k, v in geom.items()},
                        "masses_g": {n: round(m, 2) for n, m, _ in rows}, "total_g": round(tot, 2),
                        "centre_of_mass_x_mm": round(mx, 1), "nose_g": round(tot * (1 - mx / L_EAR), 2),
                        "ear_g": round(tot * mx / L_EAR, 2),
                        "min_gap_mm (negative = overlap volume mm3)": gaps, "under_min_gap": bad}
        render(parts, temple, geom)
    (OUT / "summary.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
    sketch_sheet(builds)


if __name__ == "__main__":
    main()
