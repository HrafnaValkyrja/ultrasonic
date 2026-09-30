"""Shared interface for the buildable pod: coordinates, stack-up, fasteners, tolerances, handoffs.

Every part module (shell.py, heel.py, pad.py) builds against THIS file so they can be designed in
parallel and still fit. Change a number here, not in a part module. (2026-09-30, owner decisions:
rev 1 is the prototype; resin printing; straight pre-set superelastic NiTi, direction set by
angled sockets, no heat-setting; Blade exterior; removable frame adapter; LED ring on the pad.)

Frame: x = rearward from the glasses hinge along the temple arm, y = outward (away from the head),
z = up. Temple arm inner face y = 0. Units mm.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent

# ----------------------------------------------------------------------------- pod envelope
# (same numbers as blade.py; the pod sits on a 1.8 mm removable frame adapter)
TEMPLE_T, TEMPLE_H = 2.5, 5.0
ADAPT_T = 1.8
X0, X1 = 29.5, 67.5                  # pod front (vision limit) .. rear
Z0, Z1, ZC = -9.5, 5.5, -2.0          # pod bottom, top, centre
Y_IN = TEMPLE_T + ADAPT_T             # 4.3 pod inner face (touches the adapter)
Y_OUT = Y_IN + 10.0                   # 14.3 pod outer face (armour plate adds 0.8 on top)
WALL = 0.8
Y_SPLIT = 13.4                        # tub | lid seam: the lid is the outer face, 0.9 thick
EDGE_CHAMFER = 1.0

# cavity inside the tub
CAV = dict(x0=X0 + WALL, x1=X1 - WALL, y0=Y_IN + WALL, y1=Y_SPLIT, z0=Z0 + WALL, z1=Z1 - WALL)
# = x 30.3..66.7, y 5.1..13.4, z -8.7..4.7

# ----------------------------------------------------------------------------- stack-up (inner -> outer)
TAPE = 0.3                            # double-sided foam tape, cell to inner wall
CELL = dict(x0=30.6, x1=61.6, y0=5.4, y1=9.7, z0=-8.25, z1=4.25)      # LP401230 MAX envelope
PCM = dict(x0=61.8, x1=64.8, y0=5.4, y1=9.7, z0=-8.25, z1=4.25)       # cell protection board [Low]
PCB = dict(x0=30.6, x1=50.6, y0=11.1, y1=11.9, z0=-7.75, z1=3.75)     # 20 x 11.5 x 0.8, 4-layer
PARTS_IN = dict(y0=9.9, y1=11.1)      # tallest parts on the PCB's inner face (1.2)
PARTS_OUT = dict(y0=11.9, y1=13.1)    # tallest parts on the outer face (1.2); lid inner face 13.4
PCB_CLAMP_BAND = 0.6                  # no parts within 0.6 mm of the PCB's top/bottom edges (ribs clamp there)
PCB_END_KEEPOUT = 0.5                 # no parts within 0.5 mm of the front/rear edges
# wire pads: one row on the PCB's OUTER face along its REAR edge (x 49.2..50.4), top to bottom
WIRE_PADS = ["OUT_A", "OUT_B", "LED+", "LED-", "BAT+", "BAT-", "VBUS", "GND_CHG"]
WIRE_PAD = dict(x0=49.2, x1=50.4, z_top=3.0, pitch=1.3, h=1.0)      # pad k at z_top - k*pitch
# rear free space: behind the PCB in the PCB layer (x 50.6..66.7, y 9.9..13.4): lid bosses, wire loop
MIC_PORT = dict(x=34.5, z=-1.0, d_pcb=0.6, d_lid=1.0)                 # mic on PCB inner face, ports outward
MIC_SEAL = dict(chimney_od=2.6, chimney_id=1.0, washer_od=3.0, washer_t=0.8, keepout_r=1.6)
BUTTON = dict(x=42.5, z=1.9, body=(3.0, 2.0), height=0.6, travel=0.25, force_n=1.6)   # KXT321LHS on outer face
LID_SCREWS = [(60.8, 2.7), (60.8, -6.4)]    # (x, z) on the outer face; into captured brass nuts
LID_HOOK = dict(z0=-5.0, z1=1.0)             # front edge tongue under a notch in the front wall

# ----------------------------------------------------------------------------- fasteners & materials
# Resin printing (owner). No heat-set inserts in resin: captured nuts or self-tapping screws.
FASTENERS = {
    "M1.4_pan": dict(d=1.4, head_d=2.6, head_h=0.9, clear=1.6, pilot=1.1, note="eyeglass/micro screw"),
    "M1.2_pan": dict(d=1.2, head_d=2.2, head_h=0.8, clear=1.4, pilot=0.95, note="eyeglass screw"),
    "M1.4_nut": dict(s=3.0, m=1.2, pocket_af=3.1, note="brass DIN 934, solderable"),
    "M1.4_set": dict(d=1.4, lengths=(2, 3), key_af=0.7, pilot=1.1, note="cup point; lands on a filed flat"),
}
RESIN = dict(min_wall=0.6, pref_wall=0.8, slide_fit=0.15, hole_over=0.1, min_slot=0.3, min_feature=0.3,
             note="tough/ABS-like resin; ream critical holes with a pin-vise drill after printing")

# ----------------------------------------------------------------------------- NiTi arm (worn state)
NITI_D = 0.80                         # nominal; buy 0.75 / 0.80 / 0.85 and pick on the bench (T5)
SOCKET_D = NITI_D + 0.05              # printed undersize, reamed to this
HEEL_SOCKET_DEPTH = 4.0               # blind depth above E, along -a_E
PAD_SOCKET_DEPTH = 3.5
E = np.array([61.3, 2.0, -8.3])       # heel socket MOUTH: bending starts here
PAD_CONTACT = np.array([70.6, -3.0, -25.0])     # centre of the contact face, on the skin
SET_DELTA = 3.5                       # free pad sits 3.5 mm inside the skin (owner's "angle in slightly")
FLEX_ZONE = 3.0                       # s = 0..3 mm below E: exposed flex zone under the heel's pivot shroud
STRUT_START = 3.0                     # the strut (part of the pad cap) covers the wire from s = 3 mm down
STRUT_CLEARANCE_TOP = 0.9             # radial clearance wire<->strut channel at its top (worn 0.54, jaw x1.6)
STRUT_CLEARANCE_BOTTOM = 0.15
SHROUD_CLEARANCE = 1.4                # heel shroud <-> strut top end, any state

# pad frame: transducer long axis along the arm (30 deg sweep), face parallel to the skin
SWEEP_DEG = 30.0
E1 = np.array([math.cos(math.radians(SWEEP_DEG)), 0.0, math.sin(math.radians(SWEEP_DEG))])   # width
E2 = np.array([0.0, 1.0, 0.0])                                                               # outward
E3 = np.array([-math.sin(math.radians(SWEEP_DEG)), 0.0, math.cos(math.radians(SWEEP_DEG))])  # long axis, up-forward
TRANSDUCER = dict(w=6.0, t=4.0, L=12.6)        # RC-BC02 larger listing (e1, e2, e3); leads UNKNOWN [Low]
PAD_Y = dict(skin=-3.0, contact_inner=-2.0, cup_wall_out=-2.0, cup_wall_in=-1.4, split=2.6,
             board_top=3.4, led_top=3.75, cap_face=4.5)   # world y; contact face = skin
PAD_CENTRE = np.array([PAD_CONTACT[0], (PAD_Y["cup_wall_in"] + PAD_Y["split"]) / 2, PAD_CONTACT[2]])  # transducer centre
PAD_BOARD = dict(w=5.0, L=9.3, t=0.8, e3_0=-4.0, e3_1=5.3, led="Everlight 16-213/BHC-AN1P2 (C131223), 0402, at e3=0")

_GEO = json.loads((HERE / "out" / "arm_geometry.json").read_text())


def _shape(state):
    s = np.array(_GEO["s"])
    w = np.array(_GEO["shapes"][state]["w"]) if state != "free" else np.zeros_like(s)
    return s, w


def _solve_axis():
    """Heel socket axis a_E such that the WORN wire, bent by the model's w(s), ends at the pad
    socket entry T. The pad socket entry sits at the top of the pad on its outer side."""
    T = PAD_CENTRE + 7.6 * E3 + np.array([0.0, 4.6, 0.0])
    s, w = _shape("worn_3.5")
    a_E = (T - E) / np.linalg.norm(T - E)
    for _ in range(20):
        n = E2 - (E2 @ a_E) * a_E
        n /= np.linalg.norm(n)
        chord = T - w[-1] * n - E
        a_E = chord / np.linalg.norm(chord)
    return a_E, n, float(np.linalg.norm(T - w[-1] * n - E)), T


A_E, N_BEND, SPAN, T_WORN = _solve_axis()     # heel socket axis (points DOWN toward the pad), bend normal


def wire(s, state="worn_3.5"):
    """Point and unit tangent of the NiTi centreline at arc length s (0 = heel socket mouth E).
    States: 'free', 'jaw_open_1.5', 'worn_3.5', 'jaw_closed_5.5'."""
    sg, w = _shape(state)
    scale = SPAN / sg[-1]                      # model span (x-z) -> true span along a_E
    ws = np.interp(s / scale, sg, w)
    dw = np.gradient(w, sg)
    slope = np.interp(s / scale, sg, dw)
    p = E + s * A_E + ws * N_BEND
    t = A_E + slope * N_BEND
    return p, t / np.linalg.norm(t)


def pad_socket_axis(state="worn_3.5"):
    """Entry point T and direction (pointing INTO the pad, i.e. continuing down the wire)."""
    return wire(SPAN, state)


def pad_pose(state):
    """Rigid transform (R 3x3, t 3) moving pad-side geometry from its WORN pose to `state`.
    The pad (and its strut) is rigid with the wire end, so it follows the end point and tangent.
    Apply as p_state = R @ p_worn + t. build123d: Location from R/t, or transform point lists."""
    T0, a0 = pad_socket_axis("worn_3.5")
    T1, a1 = pad_socket_axis(state)
    v = np.cross(a0, a1)
    c = float(a0 @ a1)
    if np.linalg.norm(v) < 1e-9:
        R = np.eye(3)
    else:
        vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
        R = np.eye(3) + vx + vx @ vx / (1 + c)
    return R, T1 - R @ T0


def summary():
    T, aT = pad_socket_axis()
    return {"E": E.round(3).tolist(), "a_E(down)": A_E.round(4).tolist(), "span_mm": round(SPAN, 2),
            "T_worn": T.round(3).tolist(), "a_T(down, worn)": aT.round(4).tolist(),
            "a_T angle to pad long axis (deg)": round(math.degrees(math.acos(abs(aT @ -E3))), 1),
            "pad_centre": PAD_CENTRE.round(3).tolist(), "contact": PAD_CONTACT.tolist()}


if __name__ == "__main__":
    print(json.dumps(summary(), indent=2))
    for st in ("free", "jaw_open_1.5", "worn_3.5", "jaw_closed_5.5"):
        p, t = wire(SPAN, st)
        print(f"{st:15s} pad-socket entry {p.round(2)} tangent {t.round(3)}")
