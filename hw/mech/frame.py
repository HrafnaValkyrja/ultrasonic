"""Shared interface for the buildable pod: coordinates, stack-up, fasteners, tolerances, handoffs.

Every part module (heel.py, pad.py, blade.py via pod.py, the shells) builds against THIS file so they can be designed in
parallel and still fit. Arm, pad, anatomy, fasteners and the glasses interface are owned here; the pod body (X0..Z1, CAV,
CELL, PCB, MIC_PORT, BUTTON) is read from the current design's shell dims (pod_facts(), ECR-0001, 2026-10-07). (2026-09-30, owner decisions:
rev 1 is the prototype; resin printing; straight pre-set superelastic NiTi, direction set by
angled sockets, no heat-setting; Blade exterior; removable frame adapter; LED ring on the pad.)

Frame: x = rearward from the glasses hinge along the temple arm, y = outward (away from the head),
z = up. Temple arm inner face y = 0. Units mm.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent

# ----------------------------------------------------------------------------- glasses interface (all designs)
TEMPLE_T, TEMPLE_H = 2.5, 5.0
ADAPT_T = 1.8
Y_IN = TEMPLE_T + ADAPT_T             # 4.3 pod inner face (touches the adapter)

# ----------------------------------------------------------------------------- the pod body: from the CURRENT design (ECR-0001)
# These names are not stored here. They resolve on first use (module __getattr__) from the selected design's shell dims
# (hw/current.yaml `shell_dims` via tools/current.py): Phase 2 -> hw/mech/dims_r2.py (imported; numpy only);
# ULTRASONIC_DESIGN=revg -> hw/mech/shell_r1.py (ast-read, never imported). Until 2026-10-07 this block held the pre-rev-1
# pod (PCB 20 x 11.5, LP401230 + PCM, KXT321 button, lid screws, mic chimney); those values now live only in hw/mech/shell.py
# (the pre-rev-1 shell, PRE_R1), the one script that still builds that pod.
POD_NAMES = ("X0", "X1", "Z0", "Z1", "ZC", "Y_OUT", "Y_SPLIT", "WALL", "TAPE", "CAV", "CELL", "PCB", "MIC_PORT", "BUTTON")
_POD_CACHE: dict = {}


def _ast_constants(path):
    """Module-level plain-number/dict constants of a CAD script, evaluated in order without running it (no CAD kernel)."""
    import ast
    env, safe = {}, {"__builtins__": {}, "dict": dict}
    for node in ast.parse(Path(path).read_text()).body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        try:
            val = eval(compile(ast.Expression(node.value), str(path), "eval"), safe, env)
        except Exception:      # noqa: BLE001  (Path(...), function calls: not constants)
            continue
        t = node.targets[0]
        if isinstance(t, ast.Name):
            env[t.id] = val
        elif isinstance(t, ast.Tuple) and all(isinstance(e, ast.Name) for e in t.elts):
            env.update({e.id: v for e, v in zip(t.elts, val)})
    return env


def pod_facts(design=None):
    """The pod body of the selected design (argument > env ULTRASONIC_DESIGN > hw/current.yaml) in this file's frame, mm.
    Keys: POD_NAMES. CAV/CELL/PCB are x0..x1, y0..y1, z0..z1 boxes; ZC is the board (= cavity) centre line;
    MIC_PORT is the lid port axis (x, z) with the board hole d_pcb and lid bore d_lid; BUTTON is the switch axis (x, z)."""
    import copy
    if str(HERE.parents[1] / "tools") not in sys.path:
        sys.path.insert(0, str(HERE.parents[1] / "tools"))
    from current import current
    d = current(design)
    if d.id not in _POD_CACHE:
        path = d.shell_dims
        if path.name == "shell_r1.py":                       # revg: Rev-1 shell, constants only
            e = _ast_constants(path)
            cav = dict(e["CAV"], y1=e["Y_SPLIT"])            # r1 lid is the outer 1.0 mm above the split
            f = dict(X0=e["X0"], X1=e["X1"], Z0=e["Z0"], Z1=e["Z1"], ZC=e["ZC"], Y_OUT=e["Y_OUT"], Y_SPLIT=e["Y_SPLIT"],
                     WALL=e["W"], CAV=cav, CELL=dict(e["CELL"]), PCB=dict(e["PCB"]),
                     MIC_PORT=dict(x=e["MIC"][0], z=e["MIC"][1]), BUTTON=dict(x=e["SWITCH"][0], z=e["SWITCH"][1], ref="SW1"))
        else:                                                # Phase 2+: a CAD-free dims module
            import importlib.util
            D = sys.modules.get(path.stem)
            if D is None or Path(getattr(D, "__file__", "")).resolve() != path.resolve():
                spec = importlib.util.spec_from_file_location(path.stem, path)
                D = importlib.util.module_from_spec(spec)
                sys.modules[path.stem] = D
                try:
                    spec.loader.exec_module(D)
                except Exception:
                    sys.modules.pop(path.stem, None)
                    raise
            f = dict(X0=D.X0, X1=D.X1, Z0=D.Z0, Z1=D.Z1, ZC=(D.PCB["z0"] + D.PCB["z1"]) / 2, Y_OUT=D.Y_OUT, Y_SPLIT=D.Y_SPLIT,
                     WALL=D.W, CAV=dict(D.CAV), CELL=dict(D.CELL), PCB=dict(D.PCB),
                     MIC_PORT=dict(x=D.MIC[0], z=D.MIC[1], d_pcb=D.MIC_HOLE_D, d_lid=D.DUCT_D),
                     BUTTON=dict(x=D.SW[0], z=D.SW[1], ref="SW1", body=D.SW1["body"], height=D.SW1["h"], travel=D.SW1["travel"]))
        f["TAPE"] = round(f["CELL"]["y0"] - Y_IN - f["WALL"], 6)     # cell-to-inner-wall gap (VHB): 0.3 in r1 and r2
        f["design"] = d.id
        _POD_CACHE[d.id] = f
    return copy.deepcopy(_POD_CACHE[d.id])


def __getattr__(name):
    """frame.X0, frame.PCB, ... (POD_NAMES): the current design's value, see pod_facts()."""
    if name in POD_NAMES:
        return pod_facts()[name]
    raise AttributeError(f"module 'frame' has no attribute {name!r}")


# ----------------------------------------------------------------------------- fasteners & materials
# Resin printing (owner). No heat-set inserts in resin: captured nuts or self-tapping screws.
FASTENERS = {
    "M1.4_pan": dict(d=1.4, head_d=2.6, head_h=0.9, clear=1.6, pilot=1.1, note="eyeglass/micro screw"),
    "M1.2_pan": dict(d=1.2, head_d=2.2, head_h=0.8, clear=1.4, pilot=1.0, note="eyeglass screw; pilot 1.0 = ~74 % engagement (0.95 = 92 %, splits resin; hardware.md, 2026-10-07)"),
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
