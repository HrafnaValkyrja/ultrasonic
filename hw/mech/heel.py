"""Heel: the NiTi arm's root, under the rear of the pod (Blade style, resin, rev 1 = the prototype).

    python3 hw/mech/heel.py          # -> hw/mech/out/parts/heel/*.step|stl, checks.json, heel_views.png

The integrator builds the tub as   tub = tub + heel_add() - heel_cut()   (print STL: heel_cut(undersize=True)).

What it is (all numbers from frame.py; units mm; x back, y outward, z up):
- A raked keel hanging under the adapter, inboard of the pod's inner face (y 0.3..4.3), fused to the
  tub's inner-lower corner. Its front face is raked parallel to the wire (28.6 deg from vertical).
- A cylindrical "pivot boss" (axis along x, r 2.8, like the old coil-spring pivot_boss) forms the
  rounded underside around the wire root. The NiTi still does all the flexing; nothing pivots.
- Blind socket Ø SOCKET_D (0.85, reamed) running UP from the mouth E along -A_E, HEEL_SOCKET_DEPTH
  deep (full diameter), plus the 118 deg drill point beyond it.
- Below E the bore opens into a trumpet flare (R 8, tangent to the bore at E) and then a 0.4 mm lip
  round onto the LAND: a flat facet perpendicular to the wire, ~1.2 mm below E. The strut's top end
  (pad cap) sits >= SHROUD_CLEARANCE under the land in every state; behind it a short rear spur.
- One M1.4 x 3 set screw on the socket's FRONT side (-b: front-down), through a captured brass DIN 934
  nut slid in from the INBOARD face, landing on a flat filed on the wire. The flat faces the bend's
  neutral axis, so it costs no bending strength. Key access: the boss's front disc / raked front face.
- A Ø1.0 channel for the 4 pad conductors: square out of the land 2.25 mm behind the wire, up 2.4 mm,
  bend (R 0.8), rearward inside the heel, bend, then out through the tub's inner wall (necked to Ø0.8 over
  its last 1.3 mm, reamed) into the 1.1 mm rear gap behind the cell (exit x 66.20, z -5.50: hole
  65.80-66.60, 0.20 behind the cell's rear plane, 0.36 from the cell's corner across the 0.3 VHB gap). Two bends: thread it with a fish wire.
  From the exit the bundle rises diagonally up the rear gap, turns forward over the cell (R 1.0) into the
  stowage zone behind the board and fans out to J1/J7/J2/J8 on the board's B face: wire_route(), checked
  in checks()['wire_route'] (2026-10-07, reg-arm issue 1).
Owner notes: hw/mech/notes/heel.md. Checks: hw/mech/out/parts/heel/checks.json.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
from build123d import (Box, Cone, Cylinder, Location, Plane, Polygon, Pos, Rot, Sphere, Vertex,
                       chamfer, export_step, export_stl, extrude, revolve, Axis)

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import frame as F  # noqa: E402
import blade  # noqa: E402  (prism helpers, adapter(), shell())

OUT = HERE / "out" / "parts" / "heel"

# ----------------------------------------------------------------------------- local frame at the mouth E
E = F.E.astype(float)
A = F.A_E / np.linalg.norm(F.A_E)              # down the wire (free state)
N = F.N_BEND / np.linalg.norm(F.N_BEND)        # bend direction (outward, ~+y)
B = np.cross(A, N)                             # bend-plane normal: rear-up (0.879, 0, 0.478)
R_WIRE = F.NITI_D / 2
R_SOCK = F.SOCKET_D / 2


def W(b=0.0, n=0.0, h=0.0):
    """World point from local coords: b along B (rear-up), n along N (outward), h along A (down) from E."""
    return E + b * B + n * N + h * A


def local(p):
    d = np.asarray(p, float) - E
    return float(d @ B), float(d @ N), float(d @ A)


def _loc(origin, z_dir, x_dir):
    return Location(Plane(origin=tuple(map(float, origin)), x_dir=tuple(map(float, x_dir)),
                          z_dir=tuple(map(float, z_dir))))


def _cyl(p0, p1, r):
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    v = p1 - p0
    L = float(np.linalg.norm(v))
    z = v / L
    x = np.cross(z, [0.0, 0.0, 1.0]) if abs(z[2]) < 0.9 else np.cross(z, [1.0, 0.0, 0.0])
    return _loc((p0 + p1) / 2, z, x) * Cylinder(r, L)


def _lbox(b0, b1, n0, n1, h0, h1):
    """Box with faces normal to B, N, A (bounds in local coords)."""
    c = W((b0 + b1) / 2, (n0 + n1) / 2, (h0 + h1) / 2)
    return _loc(c, A, B) * Box(b1 - b0, n1 - n0, h1 - h0)


# ----------------------------------------------------------------------------- parameters
FLARE_R = 8.0                 # trumpet radius at the mouth (brief: >= ~8). Wrap strain cap d/2R = 5 %
LIP_R = 0.4                   # convex round where the flare meets the land (no knife edge)
LAND_MARGIN = 0.10            # extra over SHROUD_CLEARANCE when placing the land
Y_INB = 0.3                   # heel's inboard face (temple inner face is y = 0; blade heel used 0.7)
Y_OUTB = 5.0                  # keel runs into the tub's inner wall (clipped by the cavity)
TOP_Z = -4.3                  # under the adapter plate (its underside is -3.9)
CROWN_Z, CROWN_Y0, CROWN_Y1 = -3.78, 2.1, 2.7   # local crown over the socket's blind end, under the clip lip (-3.3)
SET = F.FASTENERS["M1.4_set"]
NUT = F.FASTENERS["M1.4_nut"]
SET_H = 2.0                   # set-screw axis: 2.0 mm above E, up the socket
SET_LEN = 3.0                 # M1.4 x 3 (frame lists 2 and 3): 4 threads in the nut, top 0.1 under the face
FLAT_DEPTH = 0.15             # filed on the wire: flat surface 0.25 from the wire axis
FLAT_FROM_END = 2.6           # file the flat from the wire's top end down to 2.6 mm (shoulder below the screw)
SCREW_CLEAR_D = 1.5           # through the 0.8 wall between nut and socket (no resin thread: the nut holds)
NUT_T0 = R_SOCK + 0.80        # nut pocket inner face, from the socket axis along -B (0.8 wall)
NUT_POCKET_T = NUT["m"] + 0.10
NUT_T1 = NUT_T0 + NUT_POCKET_T
ACCESS_D = 1.6                # key/screw access bore, nut -> front face
FRONT_T = NUT_T1 + 0.80       # raked front face, from the socket axis along -B (0.8 behind the nut)
BOSS_R, BOSS_YC, BOSS_ZC = 2.8, 2.6, -7.25      # "pivot boss" barrel along x (old pivot_boss r 2.8)
BOSS_X0, BOSS_X1, BOSS_CH = 56.0, 64.8, 0.4      # front disc pokes out under the raked keel face
CH_D = 1.0                    # conductor channel inside the heel: bare 4 x 0.21 litz bundle (~0.5 mm); static
CH_CBORE_D, CH_CBORE_L = 1.6, 1.0   # mouth counterbore on the land: seats the end of the shrink tube that
                                    # protects the bundle through the flex joint (owner 2026-10-01)
CH_B0, CH_N0 = 2.25, 0.55     # channel entry on the land (local b, n)
CH_C1_H = -1.30               # 1st corner: straight up from the land (local h), 2.45 above it
CH_C2 = np.array([65.85, 2.75, -5.60])     # 2nd corner: after running rearward inside the heel
CH_EXIT = np.array([66.20, 5.15, -5.50])   # out through the tub's inner wall (face y 5.1) into the 1.1 rear gap (2026-10-07;
                                           # was 65.75, 5.30, -5.62: the hole straddled the cell's rear end x 65.6).
                                           # x 66.20: Ø0.8 hole 65.80-66.60 keeps 0.6 outer wall to the tub's 1 mm corner chamfer
CH_NECK_D = 0.8               # exit neck: Ø0.8 through the inner wall (y 3.85 -> exit), reamed 0.8 from the cavity side.
CH_NECK_Y0, CH_NECK_CONE = 3.85, 0.3      # neck starts at y 3.85 after a 0.3 mm cone (no shoulder to snag the fish)
CH_BEND = 0.8                 # centreline bend radius (0.3 mm PTFE wire bends far tighter)
STRUT_LEN = 6.0
STATES = ("free", "jaw_open_1.5", "worn_3.5", "jaw_closed_5.5")
SCREW_KEY = f"set_screw_M1.4x{SET_LEN:g}"
PRINT_UNDERSIZE = {"socket_d": F.SOCKET_D - 0.15, "screw_clear_d": 1.3}   # ream: 0.85 drill, 1.5 drill


# ----------------------------------------------------------------------------- the strut (pad agent's), for clearances
def _pad_module():
    """pad.py (parallel agent) if it imports cleanly; the heel never depends on it to build."""
    try:
        import pad as P  # noqa: F401
        return P
    except Exception:
        return None


_P = _pad_module()
# strut top sections in the strut frame (b' lateral = a_T x n', n' outward), (b_lo, b_hi, n_lo, n_hi)
STRUT_SECTIONS = {"3.2x2.4": (-1.6, 1.6, -1.2, 1.2), "2.4x3.2": (-1.2, 1.2, -1.6, 1.6)}
if _P is not None and all(hasattr(_P, k) for k in ("STRUT_B2", "STRUT_B1_LO", "STRUT_B1_HI_TOP")):
    STRUT_SECTIONS["pad.py"] = (_P.STRUT_B2[0], _P.STRUT_B2[1], _P.STRUT_B1_LO, _P.STRUT_B1_HI_TOP)
else:                        # pad.py draft numbers, 2026-09-30
    STRUT_SECTIONS["pad.py"] = (-2.90, 1.30, -1.45, 1.90)


def _strut_frames():
    """Worn-state strut top frames for both centrings: on the pad-socket line, or on the wire at s=3."""
    T, aT = F.pad_socket_axis("worn_3.5")
    P3, _ = F.wire(F.STRUT_START, "worn_3.5")
    yv = np.array([0.0, 1.0, 0.0])
    n_ = yv - (yv @ aT) * aT
    n_ /= np.linalg.norm(n_)
    b_ = np.cross(aT, n_)
    line_top = T + ((P3 - T) @ aT) * aT
    return {"on_line": (line_top, aT, b_, n_), "on_wire": (P3, aT, b_, n_)}


def strut_poses():
    """{(centring, section, state): (top centre, axis down, b', n', extents)} in each state.
    pad.py's own strut is centred on the pad-socket line, so it is only checked that way."""
    out = {}
    for cname, (top, ax, b_, n_) in _strut_frames().items():
        for sname, ext in STRUT_SECTIONS.items():
            if sname == "pad.py" and cname != "on_line":
                continue
            for st in STATES:
                Rm, t = F.pad_pose(st)
                out[(cname, sname, st)] = (Rm @ top + t, Rm @ ax, Rm @ b_, Rm @ n_, ext)
    return out


def strut_solid(pose):
    top, ax, b_, n_, (b0, b1, n0, n1) = pose
    c = top + ax * STRUT_LEN / 2 + (b0 + b1) / 2 * b_ + (n0 + n1) / 2 * n_
    return _loc(c, ax, b_) * Box(b1 - b0, n1 - n0, STRUT_LEN)


def strut_corners(pose):
    top, ax, b_, n_, (b0, b1, n0, n1) = pose
    return [top + bb * b_ + nn * n_ for bb in (b0, b1) for nn in (n0, n1)]


def pad_strut_actual():
    """pad.py's lofted strut (worn pose) moved rigidly into each state, or None."""
    if _P is None or not hasattr(_P, "build_strut"):
        return None
    try:
        s = _P.build_strut()
        L0 = Location(Plane(origin=tuple(map(float, _P.T_W)), x_dir=tuple(map(float, _P.B1_W)),
                            z_dir=tuple(map(float, _P.A_W))))
        out = {}
        for st in STATES:
            Rm, t = F.pad_pose(st)
            L1 = Location(Plane(origin=tuple(map(float, Rm @ _P.T_W + t)), x_dir=tuple(map(float, Rm @ _P.B1_W)),
                                z_dir=tuple(map(float, Rm @ _P.A_W))))
            out[st] = L1 * L0.inverse() * s
        return out
    except Exception:
        return None


def _land_geometry():
    """Land height below E (local h) and its rear edge (local b), from the strut corners in all states."""
    hs, bs = [], []
    for pose in strut_poses().values():
        for c in strut_corners(pose):
            b_, _, h = local(c)
            hs.append(h)
            bs.append(b_)
    h_land = min(hs) - F.SHROUD_CLEARANCE - LAND_MARGIN
    b_rear = max(bs) + F.SHROUD_CLEARANCE + LAND_MARGIN
    return h_land, b_rear, min(hs)


H_LAND, B_LAND, STRUT_TOP_H = _land_geometry()


# ----------------------------------------------------------------------------- flare profile (r, h)
def _flare_profile():
    """Points (r, h) of the cavity wall from the bore at E down to the land, h along A."""
    sphi = (H_LAND - LIP_R) / (FLARE_R - LIP_R)
    phi1 = math.asin(sphi)
    pts = []
    for k in range(13):
        ph = phi1 * k / 12
        pts.append((R_SOCK + FLARE_R * (1 - math.cos(ph)), FLARE_R * math.sin(ph)))
    P1 = np.array(pts[-1])
    C = P1 + LIP_R * np.array([math.cos(phi1), -math.sin(phi1)])
    a0 = math.atan2(P1[1] - C[1], P1[0] - C[0])          # start angle on the lip round
    a1 = math.pi / 2                                    # tangent to the land (h = H_LAND)
    for k in range(1, 9):
        t = a0 + (a1 - a0) * k / 8
        pts.append((C[0] + LIP_R * math.cos(t), C[1] + LIP_R * math.sin(t)))
    return pts, phi1, float(C[0])


FLARE_PTS, FLARE_PHI, MOUTH_R = _flare_profile()


def flare_radius(h):
    """Cavity radius at depth h below E (h <= H_LAND); bore radius above E."""
    if h <= 0:
        return R_SOCK
    rs, hs = zip(*FLARE_PTS)
    return float(np.interp(h, hs, rs))


def _revolve_local(profile_rh, origin, axis_down):
    """Revolve a closed (r, h) polygon about the local axis (h along axis_down) placed at origin."""
    face = Rot(90, 0, 0) * Polygon(*profile_rh, align=None)   # (r, h, 0) -> (r, 0, h)
    sol = revolve(face, Axis.Z, 360)
    x = np.cross(axis_down, [0.0, 0.0, 1.0])
    return _loc(origin, axis_down, x) * sol


def flare_cut():
    prof = [(0.0, -0.3), (R_SOCK, -0.3)] + FLARE_PTS + [(MOUTH_R, H_LAND + 0.6), (0.0, H_LAND + 0.6)]
    return _revolve_local(prof, E, A)


# ----------------------------------------------------------------------------- set screw / nut geometry
Q = W(h=-SET_H)                       # screw axis meets the socket axis here


def _hex_pts(af):
    """Hexagon in a local (u, v) plane: flats facing +-u (u = A), corners on +-v (v = N)."""
    rc = af / math.sqrt(3)
    return [(af / 2, rc / 2), (0.0, rc), (-af / 2, rc / 2), (-af / 2, -rc / 2), (0.0, -rc), (af / 2, -rc / 2)]


def nut_hex():
    """Hex pocket only (flats facing +-A, corners on +-N), t = NUT_T0..NUT_T1 along -B from the socket axis."""
    face = Polygon(*_hex_pts(NUT["pocket_af"]), align=None)       # XY plane: x = u (A), y = v (N)
    prism = extrude(face, amount=NUT_POCKET_T)
    return Location(Plane(origin=tuple(Q - NUT_T0 * B), x_dir=tuple(A), z_dir=tuple(-B))) * prism


def nut_pocket():
    """Hex pocket + insertion slot out through the INBOARD face (-N)."""
    af = NUT["pocket_af"]
    slot = _lbox(-NUT_T1, -NUT_T0, -6.0, 0.0, -SET_H - af / 2, -SET_H + af / 2)
    return nut_hex() + slot


def screw_cuts(undersize=False):
    d_clear = PRINT_UNDERSIZE["screw_clear_d"] if undersize else SCREW_CLEAR_D
    clear = _cyl(Q - 0.15 * B, Q - (NUT_T0 + 0.05) * B, d_clear / 2)
    access = _cyl(Q - (NUT_T1 - 0.05) * B, Q - (FRONT_T + 4.0) * B, ACCESS_D / 2)   # runs out through the boss's front disc
    return clear + access


# ----------------------------------------------------------------------------- socket
def socket_cut(undersize=False):
    d = PRINT_UNDERSIZE["socket_d"] if undersize else F.SOCKET_D
    depth = F.HEEL_SOCKET_DEPTH
    bore = _cyl(W(h=0.35), W(h=-depth), d / 2)
    hc = (d / 2) / math.tan(math.radians(59))            # 118 deg drill point beyond the full depth
    x = np.cross(-A, [0.0, 0.0, 1.0])
    cone = _loc(W(h=-depth - hc / 2), -A, x) * Cone(d / 2, 0.0, hc)
    return bore + cone


# ----------------------------------------------------------------------------- conductor channel
def channel_path(n_arc=10):
    """Centreline of the conductor channel: up from the land (square to it), bend, rearward inside the
    heel, bend, straight outboard through the tub's inner wall (square to it). Returns
    (points, total bend in degrees, segment labels per point: 'in', 'arc', 'mid', 'out')."""
    wps = [W(CH_B0, CH_N0, H_LAND + 0.5), W(CH_B0, CH_N0, CH_C1_H), CH_C2, CH_EXIT]
    pts, labels, total = [wps[0]], ["in"], 0.0
    for i in range(1, len(wps) - 1):
        P = wps[i]
        d1 = (P - wps[i - 1]) / np.linalg.norm(P - wps[i - 1])
        d2 = (wps[i + 1] - P) / np.linalg.norm(wps[i + 1] - P)
        th = math.acos(float(np.clip(d1 @ d2, -1, 1)))
        total += th
        tl = CH_BEND * math.tan(th / 2)
        S1 = P - d1 * tl
        nrm = d2 - (d2 @ d1) * d1
        nrm /= np.linalg.norm(nrm)
        Cc = S1 + CH_BEND * nrm
        for k in range(n_arc + 1):
            ang = th * k / n_arc
            pts.append(Cc - CH_BEND * nrm * math.cos(ang) + CH_BEND * d1 * math.sin(ang))
            labels.append("arc")
        labels[-n_arc - 1] = "in" if i == 1 else "mid"     # arc start belongs to the incoming leg
    pts.append(wps[-1])
    labels.append("out")
    return [np.asarray(p, float) for p in pts], math.degrees(total), labels


def channel_cut(path=None, r=CH_D / 2, neck=True):
    """Union of cylinders + joint spheres along the centreline; the last (exit) segment necks to CH_NECK_D
    through a CH_NECK_CONE long cone ending at y = CH_NECK_Y0."""
    pts = path if path is not None else channel_path()[0]
    s = None
    for i, (p0, p1) in enumerate(zip(pts[:-1], pts[1:])):
        last = i == len(pts) - 2
        if last and neck and p0[1] < CH_NECK_Y0 - CH_NECK_CONE:
            d = (p1 - p0) / np.linalg.norm(p1 - p0)
            pa = p0 + d * ((CH_NECK_Y0 - CH_NECK_CONE - p0[1]) / d[1])
            pb = p0 + d * ((CH_NECK_Y0 - p0[1]) / d[1])
            x = np.cross(d, [0.0, 0.0, 1.0])
            cone = _loc((pa + pb) / 2, d, x) * Cone(r, CH_NECK_D / 2, float(np.linalg.norm(pb - pa)))
            seg = _cyl(p0, pa, r) + cone + _cyl(pb, p1, CH_NECK_D / 2)
        else:
            seg = _cyl(p0, p1, r)
        s = seg if s is None else s + seg
    for p in pts[1:-1]:
        s = s + Pos(*p) * Sphere(r)
    return s


# ----------------------------------------------------------------------------- wires in the cavity (rear gap -> stowage -> pads)
WIRE_OD, BUNDLE_D = 0.21, 0.51       # 7/44 served litz; 4 of them as a loose round bundle (reg-arm Conductors)
ROUTE_R_GAP, ROUTE_R_TOP, ROUTE_R_FAN = 2.0, 1.0, 1.0   # centreline bend radii (static; see notes/heel.md wire_route)
FAN = np.array([62.3, 11.60, 0.80])  # bundle ends, the 4 wires fan out (behind the board's rear edge x 60.55)
EDGE_Y = 11.55                       # each wire passes under the board's rear edge at this y (B face 12.1)


def _pads():
    """J1/J7/J2/J8 centres on the board's B face (pod frame), from the routed board via dims_r2/frame.PCB."""
    import re
    f = HERE.parents[1] / "hw/pod/draft_r2/out/routed.kicad_pcb"
    txt = f.read_text()
    out = {}
    for ref, net in (("J1", "OUT_A"), ("J7", "LED_A"), ("J2", "OUT_B"), ("J8", "LED_K")):
        i = txt.index(f'"Reference" "{ref}"')
        blk = txt[txt.rfind("(footprint ", 0, i):i]
        bx, by = (float(v) for v in re.search(r"\(at ([\d.\-]+) ([\d.\-]+)", blk).groups())
        out[ref] = dict(net=net, board=(bx, by), pod=np.array([F.PCB["x0"] + bx, F.PCB["y0"], F.PCB["z0"] + by]))
    return out


def _fillet_poly(wps, R):
    """Polyline through waypoints with every corner replaced by an arc of radius R (R may be a list per corner)."""
    wps = [np.asarray(w, float) for w in wps]
    Rs = R if isinstance(R, (list, tuple)) else [R] * (len(wps) - 2)
    pts = [wps[0]]
    for i in range(1, len(wps) - 1):
        P, r = wps[i], Rs[i - 1]
        d1 = (P - wps[i - 1]) / np.linalg.norm(P - wps[i - 1])
        d2 = (wps[i + 1] - P) / np.linalg.norm(wps[i + 1] - P)
        th = math.acos(float(np.clip(d1 @ d2, -1, 1)))
        if th < 1e-6:
            pts.append(P)
            continue
        tl = r * math.tan(th / 2)
        S1 = P - d1 * tl
        nrm = d2 - (d2 @ d1) * d1
        nrm /= np.linalg.norm(nrm)
        Cc = S1 + r * nrm
        for k in range(13):
            ang = th * k / 12
            pts.append(Cc - r * nrm * math.cos(ang) + r * d1 * math.sin(ang))
    pts.append(wps[-1])
    return pts


def wire_route():
    """Centrelines in the cavity, pod frame. 'bundle': exit -> diagonal up the rear gap (against the rear wall,
    x 66.40) -> turn forward over the cell's rear-top edge at the board-B level -> FAN. One per pad: FAN -> pad,
    dropping under the board edge (EDGE_Y at x 60.55) and lying on the pad at the end. Closed-lid geometry."""
    y_pad = F.PCB["y0"] - WIRE_OD / 2
    bundle = _fillet_poly([np.array([CH_EXIT[0], F.CAV["y0"], CH_EXIT[2]]), np.array([66.40, 6.30, CH_EXIT[2]]),
                           np.array([66.40, 11.55, 0.80]), np.array([64.0, 11.60, 0.80]), FAN],
                          [ROUTE_R_GAP, ROUTE_R_TOP, ROUTE_R_FAN])
    wires = {}
    for ref, p in _pads().items():
        pad = p["pod"]
        z = pad[2]
        # pass the neighbouring pad column at the pad's own height: J2 above J1, J8 between J1 and J7
        wps = [FAN, np.array([61.4, 11.58, (FAN[2] + z) / 2]), np.array([F.PCB["x1"], EDGE_Y, z]),
               np.array([pad[0] + 0.5, y_pad, z]), np.array([pad[0], y_pad, z])]
        wires[ref] = dict(net=p["net"], pts=_fillet_poly(wps, [ROUTE_R_FAN, ROUTE_R_FAN, 0.5]), pad=pad)
    return bundle, wires


def _plen(pts):
    return float(sum(np.linalg.norm(b - a) for a, b in zip(pts[:-1], pts[1:])))


def route_checks():
    """Clearances (mm, surface to surface) of the wires in the cavity, closed lid. The bundle may touch the tub's
    rear wall (it is laid against it); the wire ends touch their own pads (soldered)."""
    bundle, wires = wire_route()
    rb, rw = BUNDLE_D / 2, WIRE_OD / 2
    cell, pcb, cav = F.CELL, F.PCB, F.CAV

    def box_d(p, b):
        dx = max(b["x0"] - p[0], 0, p[0] - b["x1"])
        dy = max(b["y0"] - p[1], 0, p[1] - b["y1"])
        dz = max(b["z0"] - p[2], 0, p[2] - b["z1"])
        return math.sqrt(dx * dx + dy * dy + dz * dz)

    def dense(pts, n=6):
        out = []
        for a, b in zip(pts[:-1], pts[1:]):
            out += [a + t * (b - a) for t in np.linspace(0, 1, n, endpoint=False)]
        return out + [pts[-1]]

    seam = lambda p: math.hypot(p[0] - cav["x1"], p[1] - F.Y_SPLIT)       # rear tub|lid joint line (along z)
    res = {}
    bp = dense(bundle)
    gap_pts = [p for p in bp if p[1] <= F.CELL["y1"] + 0.05]
    res["bundle"] = {"d": BUNDLE_D, "length_mm": round(_plen(bundle), 2),
                     "to_cell": round(min(box_d(p, cell) for p in bp) - rb, 3),
                     "to_cell_in_rear_gap": round(min(box_d(p, cell) for p in gap_pts) - rb, 3),
                     "to_board": round(min(box_d(p, pcb) for p in bp) - rb, 3),
                     "to_lid_inner": round(min(cav["y1"] - p[1] for p in bp) - rb, 3),
                     "to_rear_seam": round(min(seam(p) for p in bp) - rb, 3),
                     "to_rear_wall": round(min(cav["x1"] - p[0] for p in bp) - rb, 3),
                     "to_cavity_top": round(min(cav["z1"] - p[2] for p in bp) - rb, 3),
                     "bend_radii": [ROUTE_R_GAP, ROUTE_R_TOP, ROUTE_R_FAN],
                     "strand_bend_strain_pct": round(100 * 0.05 / (2 * min(ROUTE_R_GAP, ROUTE_R_TOP, ROUTE_R_FAN, 0.8)), 2)}
    pads = _pads()
    wres = {}
    for ref, w in wires.items():
        pts = dense(w["pts"])
        free = [p for p in pts if p[0] >= pcb["x1"] - 1e-6]                   # behind the board's rear edge
        other = [q["pod"] for k, q in pads.items() if k != ref]
        pad_cl = min(math.hypot(p[0] - q[0], p[2] - q[2]) for p in pts for q in other) - 0.5 - rw
        wres[ref] = {"net": w["net"], "length_mm": round(_plen(w["pts"]), 2),
                     "to_cell": round(min(box_d(p, cell) for p in pts) - rw, 3),
                     "to_board_behind_edge": round(min(box_d(p, pcb) for p in free) - rw, 3),
                     "at_board_edge_below_B": round(pcb["y0"] - EDGE_Y - rw, 3),
                     "to_other_pads_copper": round(pad_cl, 3),
                     "to_lid_inner": round(min(cav["y1"] - p[1] for p in pts) - rw, 3)}
    res["wires"] = wres
    # lid opened 180 deg about the rear seam edge (x X1, y Y_SPLIT): pads land mirrored behind the pod, B face up.
    # Path: exit -> up the gap to the seam -> over the edge -> straight (x-z) to the mirrored pad.
    x_h = F.X1
    open_len = {}
    for ref, p in pads.items():
        q = p["pod"]
        qm = np.array([2 * x_h - q[0], q[1], q[2]])
        up = F.Y_SPLIT - CH_EXIT[1]
        open_len[ref] = round(up + (x_h - 66.40) + math.hypot(qm[0] - x_h, qm[2] - CH_EXIT[2]), 2)
    closed = {ref: round(res["bundle"]["length_mm"] + wres[ref]["length_mm"], 2) for ref in wires}
    need = max(open_len[k] - closed[k] for k in closed)
    res["service"] = {"closed_exit_to_pad_mm": closed, "lid_open_180_exit_to_pad_mm": open_len,
                      "extra_needed_mm": round(need, 2), "service_loop_mm": round(math.ceil(need + 2.0), 1),
                      "cut_length_exit_to_pad_mm": {k: round(closed[k] + math.ceil(need + 2.0), 1) for k in closed},
                      "loop_stowed": "one U toward the cavity top behind the board (x 61-66, z 0.8..3.5), R >= 1.5"}
    res["pass_0.3"] = all(v >= 0.3 - 1e-3 for k, v in res["bundle"].items()
                          if k.startswith("to_") and k != "to_rear_wall") and \
        all(v >= 0.3 - 1e-3 for w in wres.values() for k, v in w.items() if k.startswith(("to_", "at_")))
    return res


# ----------------------------------------------------------------------------- body
def _section_yz():
    return [(Y_INB, -12.0), (Y_INB, CROWN_Z), (CROWN_Y0, CROWN_Z), (CROWN_Y1, TOP_Z), (Y_OUTB, TOP_Z),
            (Y_OUTB, -12.0)]


def _side_xz():
    """Keel side profile before the raked cuts: flat top, rear raked like the Blade heel, rear spur."""
    return [(50.0, CROWN_Z), (66.6, CROWN_Z), (67.3, -5.2), (67.3, -9.3), (66.4, -10.1), (63.0, -10.1),
            (60.0, -8.4), (50.0, -8.4)]


def cavity_box():
    c = F.CAV
    return Pos((c["x0"] + c["x1"]) / 2, (c["y0"] + c["y1"]) / 2, (c["z0"] + c["z1"]) / 2) * Box(
        c["x1"] - c["x0"], c["y1"] - c["y0"], c["z1"] - c["z0"])


def heel_add():
    """Solid to UNION into the tub (already clipped out of the tub's cavity)."""
    sec = blade.prism_yz(_section_yz(), 50.0, 68.0)
    keel = blade.prism_xz(_side_xz(), Y_INB, Y_OUTB) & sec
    keel = keel - _lbox(-30.0, -FRONT_T, -30.0, 30.0, -30.0, 30.0)          # raked front face (keel only)
    cyl = chamfer(Cylinder(BOSS_R, BOSS_X1 - BOSS_X0).edges(), BOSS_CH)
    boss = Pos((BOSS_X0 + BOSS_X1) / 2, BOSS_YC, BOSS_ZC) * Rot(0, 90, 0) * cyl
    body = keel + (boss & sec)
    body = body - _lbox(-30.0, B_LAND, -30.0, 30.0, H_LAND, 30.0)            # land + notch for the strut
    body = body - cavity_box()
    return body


def heel_cut(undersize=False):
    """Solid to SUBTRACT from the tub: socket (+drill point), flare, set-screw holes, nut pocket+slot,
    conductor channel. undersize=True gives the PRINT version (socket and screw hole to be reamed)."""
    pts = channel_path()[0]
    d = (pts[1] - pts[0]) / np.linalg.norm(pts[1] - pts[0])
    cbore = _cyl(pts[0] - d * 0.6, pts[0] + d * CH_CBORE_L, CH_CBORE_D / 2)
    return socket_cut(undersize) + flare_cut() + screw_cuts(undersize) + nut_pocket() + channel_cut() + cbore


# ----------------------------------------------------------------------------- hardware + reference models
def hardware():
    out = {}
    # NiTi in the socket and flex zone, worn state (centreline chain)
    pts = [W(h=-F.HEEL_SOCKET_DEPTH)] + [F.wire(s, "worn_3.5")[0] for s in np.linspace(0, F.STRUT_START, 7)]
    w = None
    for p0, p1 in zip(pts[:-1], pts[1:]):
        seg = _cyl(p0, p1, R_WIRE)
        w = seg if w is None else w + seg
    for p in pts[1:-1]:
        w = w + Pos(*p) * Sphere(R_WIRE)
    flat = _lbox(-R_WIRE - 0.2, -(R_WIRE - FLAT_DEPTH), -1.0, 1.0, -F.HEEL_SOCKET_DEPTH - 0.1,
                 -F.HEEL_SOCKET_DEPTH + FLAT_FROM_END)
    out["niti_root_worn"] = w - flat
    tip_t = R_WIRE - FLAT_DEPTH
    out[SCREW_KEY] = _cyl(Q - tip_t * B, Q - (tip_t + SET_LEN) * B, SET["d"] / 2)
    hexn = Location(Plane(origin=tuple(Q - (NUT_T1 - NUT["m"]) * B), x_dir=tuple(A), z_dir=tuple(-B))) * \
        extrude(Polygon(*_hex_pts(NUT["s"]), align=None), amount=NUT["m"])
    out["nut_M1.4_brass"] = hexn - _cyl(Q - 0.5 * B, Q - 4.0 * B, SET["d"] / 2 * 0.85)
    act = pad_strut_actual()
    out["strut_ref_worn"] = act["worn_3.5"] if act else strut_solid(strut_poses()[("on_line", "pad.py", "worn_3.5")])
    return out


# ----------------------------------------------------------------------------- checks
def _gap(a, b):
    """Positive = clearance (mm); negative = overlap volume (mm^3)."""
    v = (a & b).volume
    return -round(v, 4) if v > 1e-6 else round(a.distance_to(b), 3)


def _adapter_swept(x_from=0.0, x_to=63.0):
    """Adapter cross-section (constant part, at x = 48) extruded over the x range it sweeps past the
    pod while sliding on from the front. The snap tab (x <= 35.6) never reaches the heel."""
    ad = blade.adapter()
    sl = ad & (Pos(48.0, 0, 0) * Box(0.02, 40, 40))
    face = sorted(sl.faces(), key=lambda f: f.center().X)[0]
    return Pos(x_from - face.center().X, 0, 0) * extrude(face, amount=x_to - x_from, dir=(1, 0, 0))


def tub_plain():
    return blade.shell() - cavity_box()


def checks():
    res = {}
    add, cut = heel_add(), heel_cut()
    tub = tub_plain()
    part = (tub + add) - cut                      # tub with the heel, as built (reamed)
    heel_only = add - cut
    bb = add.bounding_box()
    res["heel_bbox"] = {k: round(v, 2) for k, v in zip(("x0", "y0", "z0", "x1", "y1", "z1"),
                                                     (bb.min.X, bb.min.Y, bb.min.Z, bb.max.X, bb.max.Y, bb.max.Z))}
    res["land"] = {"h_below_E": round(H_LAND, 3), "rear_edge_b": round(B_LAND, 3),
                   "strut_top_min_h": round(STRUT_TOP_H, 3), "mouth_radius": round(MOUTH_R, 3),
                   "flare_wrap_deg": round(math.degrees(FLARE_PHI), 2)}

    # 1. socket walls: socket (+ drill point) vs the outside and every OTHER cavity. Excluded by design:
    #    the mouth (it continues into the flare) and the set-screw window (the screw must reach the wire).
    big = Pos(60, 3, -6) * Box(40, 30, 30)
    solid_all = tub + add
    access = _cyl(Q - (NUT_T1 - 0.05) * B, Q - (FRONT_T + 4.0) * B, ACCESS_D / 2)
    ext_sock = big - (solid_all - nut_pocket() - channel_cut() - access)
    sock = socket_cut()
    sock_upper = sock - _lbox(-3, 3, -3, 3, -0.35, 3.0)
    sock_upper = sock_upper - _cyl(Q + 3 * B, Q - 3 * B, SCREW_CLEAR_D / 2 + 0.02)
    wall, p_s, p_x = sock_upper.distance_to_with_closest_points(ext_sock)
    top_z = sock.bounding_box().max.Z
    res["socket"] = {"d": F.SOCKET_D, "depth_full": F.HEEL_SOCKET_DEPTH,
                     "drill_point_extra": round((R_SOCK) / math.tan(math.radians(59)), 3),
                     "highest_point_z": round(top_z, 3), "min_wall": round(wall, 3),
                     "min_wall_at": [round(c, 2) for c in tuple(p_s)],
                     "wall_to_crown_top": round(CROWN_Z - top_z, 3),
                     "pass_min_0.6": wall >= F.RESIN["min_wall"] - 1e-3,
                     "pass_pref_0.8": wall >= F.RESIN["pref_wall"] - 1e-3}

    # 2. wire vs flare: centreline points s in [0, FLEX_ZONE] for each state; clearance = gap - r_wire
    flare_res = {}
    for st in STATES:
        worst, worst_s = 9.0, None
        for s in np.linspace(0.0, F.FLEX_ZONE, 31):
            p, _ = F.wire(float(s), st)
            if part.is_inside(tuple(p)):
                worst, worst_s = -1.0, float(s)
                break
            g = part.distance_to(Vertex(*p)) - R_WIRE
            if g < worst:
                worst, worst_s = g, float(s)
        flare_res[st] = {"min_clearance": round(worst, 4), "at_s": round(worst_s, 2)}
    res["wire_vs_flare"] = flare_res
    res["wire_vs_flare_pass"] = all(v["min_clearance"] >= -1e-3 for v in flare_res.values())
    # analytic cross-check with the model's root-slope artefact removed (socket forces w'(0)=0)
    ana = {}
    for st in STATES:
        worst = 9.0
        p0, t0 = F.wire(0.0, st)
        for s in np.linspace(0.0, H_LAND, 25):
            p, _ = F.wire(float(s), st)
            b_, n_, h_ = local(p)
            r_raw = math.hypot(b_, n_)
            worst = min(worst, flare_radius(h_) - r_raw - R_WIRE)
        ana[st] = round(worst, 4)
    res["wire_vs_flare_analytic_raw_model"] = ana
    res["root_slope_artefact_deg"] = {st: round(math.degrees(math.acos(float(np.clip(F.wire(0.0, st)[1] @ A, -1, 1)))), 2)
                                     for st in STATES}

    # 3. set screw: engagement in the brass nut; tip on the flat; access face
    tip_t = R_WIRE - FLAT_DEPTH
    screw_top = tip_t + SET_LEN
    nut_in, nut_out = NUT_T1 - NUT["m"], NUT_T1         # nut pushed outward under load
    eng = max(0.0, min(screw_top, nut_out) - nut_in)
    res["set_screw"] = {"size": f"M1.4x{SET_LEN:g}", "axis_above_E": SET_H, "direction": "-B (front-down)",
                        "B": B.round(4).tolist(), "tip_from_wire_axis": round(tip_t, 3),
                        "screw_top_from_axis": round(screw_top, 3), "front_face_from_axis": round(FRONT_T, 3),
                        "recess_below_keel_face": round(FRONT_T - screw_top, 3),
                        "nut_engagement_mm": round(eng, 3), "threads_engaged": round(eng / 0.3, 1),
                        "pass_>=3_threads": eng / 0.3 >= 3.0,
                        "nut_to_socket_wall": round(NUT_T0 - R_SOCK, 3),
                        "nut_outer_wall": round(FRONT_T - NUT_T1, 3),
                        "access_face": "front disc of the pivot boss (x 56), bore axis +B: the key goes in from "
                                       "front-below, rising 28.6 deg toward the rear",
                        "key": "0.7 mm hex (L-key); reachable on or off the adapter, glasses off the head"}
    t_exit = FRONT_T
    while part.is_inside(tuple(Q - (t_exit + 0.85) * B)) or part.is_inside(tuple(Q - t_exit * B + 0.85 * A)):
        t_exit += 0.05
    res["set_screw"]["bore_exit_from_axis"] = round(t_exit, 2)
    res["set_screw"]["key_depth_to_screw"] = round(t_exit - screw_top, 2)
    res["set_screw"]["bore_exit_world"] = (Q - t_exit * B).round(2).tolist()
    # key path: a 0.7 mm key (as a Ø0.9 rod) from the face out to 15 mm must hit nothing
    key = _cyl(Q - (FRONT_T + 0.05) * B, Q - (FRONT_T + 15.0) * B, 0.45)
    ad = blade.adapter()
    temple = Pos(40, F.TEMPLE_T / 2, 0) * Box(130, F.TEMPLE_T, F.TEMPLE_H)
    res["set_screw"]["key_path_gap"] = {"pod+heel": _gap(key, part), "adapter": _gap(key, ad),
                                        "temple": _gap(key, temple)}
    # nut pocket walls: hex only, its inboard half dropped (that side is the insertion slot by design);
    # the screw holes are not subtracted (they are meant to join the pocket to the socket and the face)
    hex_half = nut_hex() - _lbox(-10, 10, -10, -0.3, -10, 10)
    ext_nut = big - (solid_all - socket_cut() - flare_cut() - channel_cut())
    nw, p_n, _ = hex_half.distance_to_with_closest_points(ext_nut)
    res["set_screw"]["nut_pocket_wall_min"] = round(nw, 3)
    res["set_screw"]["nut_pocket_wall_at"] = [round(c, 2) for c in tuple(p_n)]
    res["set_screw"]["pass_nut_walls_0.6"] = nw >= 0.6 - 1e-3

    # 4. conductor channel: wall = distance from centreline samples to the outside / other cavities - r.
    #    Skipped by design: the entry leg's last 0.8 mm (it opens through the land) and the exit through
    #    the tub's inner wall into the rear gap.
    path, bend_deg, labels = channel_path()
    ext_ch = big - (solid_all - socket_cut() - flare_cut() - nut_pocket() - screw_cuts())
    samples = []
    for (p0, p1, lab) in zip(path[:-1], path[1:], labels[:-1]):
        for t in np.linspace(0, 1, 8, endpoint=False):
            samples.append((p0 + t * (p1 - p0), lab))
    worst, worst_p = 9.0, None
    skip = CH_D / 2 + 0.65            # the hole's own mouth is not a wall
    for p, lab in samples:
        lh = local(p)[2]
        if (lab == "in" and lh > H_LAND - skip) or p[1] > F.CAV["y0"] - skip:
            continue
        g = -CH_D / 2 if ext_ch.is_inside(tuple(p)) else ext_ch.distance_to(Vertex(*p)) - CH_D / 2
        if g < worst:
            worst, worst_p = g, p
    ch_wall = worst
    entry_lateral = CH_B0 - MOUTH_R - CH_D / 2            # to the flare lip, on the land
    ch = channel_cut(path)
    boxes = {k: Pos((v["x0"] + v["x1"]) / 2, (v["y0"] + v["y1"]) / 2, (v["z0"] + v["z1"]) / 2) *
             Box(v["x1"] - v["x0"], v["y1"] - v["y0"], v["z1"] - v["z0"]) for k, v in
             (("cell", F.CELL), ("pcb", F.PCB))}     # the current design's cell and board (frame.pod_facts(); no PCM since rev 1)
    r_exit = CH_NECK_D / 2
    exit_ok = F.CELL["x1"] < CH_EXIT[0] - r_exit and CH_EXIT[0] + r_exit < F.CAV["x1"] and CH_EXIT[2] > F.CAV["z0"]
    # exit neck's wall to the true outside (tub + heel + cavity counted as 'not outside'), wall part only (y <= CAV y0)
    outside = big - (solid_all + cavity_box())
    pn = CH_EXIT - np.array([0.0, CH_EXIT[1] - CH_NECK_Y0, 0.0])
    neck_wall = _cyl(pn, CH_EXIT - np.array([0.0, CH_EXIT[1] - F.CAV["y0"], 0.0]), r_exit)
    exit_outer = neck_wall.distance_to(outside)
    res["channel"] = {"d": CH_D, "total_bend_deg": round(bend_deg, 1), "bend_radius": CH_BEND,
                      "entry_world": W(CH_B0, CH_N0, H_LAND).round(3).tolist(), "exit_world": CH_EXIT.tolist(),
                      "length_mm": round(sum(float(np.linalg.norm(p1 - p0)) for p0, p1 in zip(path[:-1], path[1:])), 2),
                      "min_wall": round(ch_wall, 3), "min_wall_at": worst_p.round(2).tolist(),
                      "min_wall_at_local_bnh": [round(v, 2) for v in local(worst_p)],
                      "entry_to_flare_lip_wall": round(entry_lateral, 3),
                      "pass_wall_0.6": ch_wall >= 0.6 - 1e-3 and entry_lateral >= 0.6,
                      "exit_in_rear_gap": bool(exit_ok),
                      "exit_neck_d": CH_NECK_D, "exit_hole_x": [round(CH_EXIT[0] - r_exit, 3), round(CH_EXIT[0] + r_exit, 3)],
                      "exit_hole_to_cell_rear_plane_x": round(CH_EXIT[0] - r_exit - F.CELL["x1"], 3),
                      "exit_rim_to_cell_corner_3d": round(math.hypot(CH_EXIT[0] - r_exit - F.CELL["x1"], F.CELL["y0"] - F.CAV["y0"]), 3),
                      "exit_hole_to_rear_wall_plane_x": round(F.CAV["x1"] - CH_EXIT[0] - r_exit, 3),
                      "exit_neck_outer_wall": round(exit_outer, 3),
                      "pass_exit_outer_wall_0.6": exit_outer >= 0.6 - 1e-3,
                      "gap_to": {k: _gap(ch, v) for k, v in boxes.items()},
                      "bundle_fill": round(4 * 0.3 ** 2 / CH_D ** 2, 3)}
    res["channel"]["pass_clear_of_cell_pcb"] = all(g >= 0.2 for g in res["channel"]["gap_to"].values())
    res["wire_route"] = route_checks()

    # 5. shroud / boss / land vs the strut top, all states: generic boxes (two centrings, two
    #    orientations), pad.py's section as a box, and pad.py's actual lofted strut when it imports.
    #    Two targets: the heel alone (what this module owns) and the plain shell (its inner-lower edge
    #    near x 63-64.5 is not heel geometry and cannot be relieved: the shell's 1 mm chamfer already
    #    leaves 0.42 mm at the cavity corner).
    act = pad_strut_actual()
    solids = {"|".join(k): strut_solid(pz) for k, pz in strut_poses().items()}
    if act:
        solids.update({f"pad.py_actual|{st}": sol for st, sol in act.items()})
    hcases = {k: _gap(v, heel_only) for k, v in solids.items()}
    tcases = {k: _gap(v, tub) for k, v in solids.items()}

    def by_model(cases):
        models = sorted({k.rsplit("|", 1)[0] for k in cases})
        return {m: min(v for k, v in cases.items() if k.rsplit("|", 1)[0] == m) for m in models}

    worst = min(hcases.values())
    res["strut_clearance"] = {"min": worst, "required": F.SHROUD_CLEARANCE,
                              "pass": worst >= F.SHROUD_CLEARANCE - 1e-3, "min_by_model": by_model(hcases),
                              "pad_py_actual_checked": bool(act), "cases": hcases}
    res["strut_clearance_to_shell_edge"] = {
        "min": min(tcases.values()), "pass": min(tcases.values()) >= F.SHROUD_CLEARANCE - 1e-3,
        "min_by_model": by_model(tcases), "cases": tcases,
        "note": "plain blade.shell() WITHOUT the strut relief: a preview, not the build; the governing number is strut_clearance_to_r2_tub"}
    # 5b. the real tub (shell_r2.tub with this heel: strut relief, tongue, rebate) - reg-arm issue 6 (2026-10-07)
    try:
        import shell_r2 as SR
        r2 = SR.tub(sys.modules[__name__])
        rcases = {k: _gap(v, r2) for k, v in solids.items()}
        act_min = min((v for k, v in rcases.items() if k.startswith("pad.py_actual")), default=None)
        res["strut_clearance_to_r2_tub"] = {
            "min_pad_py_actual": act_min, "min_all_models": min(rcases.values()), "required": F.SHROUD_CLEARANCE,
            "pass_pad_py_actual": act_min is not None and act_min >= F.SHROUD_CLEARANCE - 1e-3,
            "min_by_model": by_model(rcases), "cases": rcases,
            "binding_surface": "strut-relief chamfer y + z = -3.65 at x ~65.7 (shell_r2.tub); moving it 0.22 thins the wall to 0.375 < RESIN min_wall 0.6"}
    except Exception as ex:  # noqa: BLE001
        res["strut_clearance_to_r2_tub"] = {"error": repr(ex)[:200]}

    # 6. adapter / temple / cavity
    swept = _adapter_swept()
    res["adapter"] = {"as_placed_gap": _gap(add, ad), "swept_from_front_gap": _gap(add, swept),
                      "swept_any_direction_gap_(no_tab)": _gap(add, _adapter_swept(0.0, 90.0)),
                      "temple_gap": _gap(add, temple)}
    top_under_plate = (add & Pos(50, (2.7 + 4.3) / 2, 0) * Box(40, 1.6, 20)).bounding_box().max.Z
    top_crown = (add & Pos(50, (Y_INB + 2.1) / 2, 0) * Box(40, 2.1 - Y_INB, 20)).bounding_box().max.Z
    res["adapter"].update({"top_z_y2.7..4.3": round(top_under_plate, 3), "top_z_crown_y<=2.1": round(top_crown, 3),
                           "pass_top_<=-4.3_under_plate": top_under_plate <= TOP_Z + 1e-3,
                           "note": "crown to -3.78 only inboard of y 2.1, under the clip lip (underside -3.3)"})
    res["cavity_intrusion_mm3"] = round((add & cavity_box()).volume, 4)
    res["inboard_min_y"] = round(bb.min.Y, 3)
    res["volume_mm3"] = round(heel_only.volume, 2)
    res["mass_g_resin_1.15"] = round(heel_only.volume * 1.15e-3, 3)
    return res, {"heel_add": add, "heel_cut": cut, "part_reamed": part, "heel_only": heel_only, "tub": tub}


# ----------------------------------------------------------------------------- figure (owner: visual, dark)
def _section_lines(shape, origin, u, v, normal, n_s=24):
    """Intersect a solid with the plane (origin, normal); return polylines in (u, v) coords."""
    from build123d import Rectangle
    pl = Plane(origin=tuple(map(float, origin)), x_dir=tuple(map(float, u)), z_dir=tuple(map(float, normal)))
    try:
        sec = shape.intersect(pl.location * Rectangle(80, 80))
    except Exception:
        return []
    lines = []
    if sec is None:
        return lines
    for e in sec.edges():
        ps = [e.position_at(t) for t in np.linspace(0, 1, n_s)]
        lines.append([((np.array(tuple(p)) - origin) @ u, (np.array(tuple(p)) - origin) @ v) for p in ps])
    return lines


def figure(parts, res, path):
    sys.path.insert(0, str(HERE.parents[1] / "tools"))
    import plotstyle
    plt = plotstyle.apply()
    S = plotstyle.SERIES
    fig, axs = plt.subplots(1, 2, figsize=(11.5, 6.2))
    # panel 1: plane through the socket axis containing the set screw (u = -B front-down, v = -A up)
    # panel 2: bending plane (u = N outward, v = -A up)
    for ax, (u, title) in zip(axs, ((-B, "Section through socket + set screw (plane A-B)\n"
                                         "right = front-down (toward the key), up = up the socket"),
                                     (N, "Bending plane (A-N): wire in 4 states, strut tops\n"
                                         "right = outward (away from head)"))):
        v = -A
        nrm = np.cross(u, v)
        for shp, col, lw, lab in ((parts["part_reamed"], S[0], 1.3, "tub + heel (reamed)"),
                                  (blade.adapter(), S[6], 1.0, "frame adapter")):
            first = True
            for ln in _section_lines(shp, E, u, v, nrm):
                xs, ys = zip(*ln)
                ax.plot(xs, ys, color=col, lw=lw, label=lab if first else None)
                first = False
        cols = {"free": S[2], "jaw_open_1.5": S[3], "worn_3.5": S[1], "jaw_closed_5.5": S[7]}
        if u is N:
            for st in STATES:
                ws = [F.wire(s, st)[0] for s in np.linspace(-0.0, 6.0, 30)]
                ax.plot([(p - E) @ u for p in ws], [(p - E) @ v for p in ws], color=cols[st], lw=2.2, alpha=0.9,
                        label=f"NiTi {st}")
                pose = strut_poses()[("on_line", "pad.py", st)]
                top, axd, n_lo, n_hi = pose[0], pose[1], pose[4][2], pose[4][3]
                quad = [top + n_lo * pose[3], top + n_hi * pose[3], top + n_hi * pose[3] + axd * 3,
                        top + n_lo * pose[3] + axd * 3]
                ax.fill([(p - E) @ u for p in quad], [(p - E) @ v for p in quad], color=cols[st], alpha=0.12)
        else:
            sx = [(Q - t * B - E) @ u for t in (R_WIRE - FLAT_DEPTH, R_WIRE - FLAT_DEPTH + SET_LEN)]
            sy = [(Q - E) @ v] * 2
            ax.plot(sx, sy, color=S[3], lw=6, alpha=0.8, solid_capstyle="butt", label=f"M1.4x{SET_LEN:g} set screw")
            ax.plot([0, 0], [F.HEEL_SOCKET_DEPTH, -3.0], color=S[1], lw=2.2, alpha=0.9, label="NiTi (free)")
            ax.annotate("0.7 mm hex key\ngoes in here", xy=(FRONT_T + 1.2, SET_H),
                        xytext=(4.2, 5.2), color=S[3], fontsize=8, arrowprops=dict(arrowstyle="->", color=S[3]))
            ax.annotate("brass M1.4 nut\n(slid in from the\ninboard face)", xy=((NUT_T0 + NUT_T1) / 2, SET_H + 1.2),
                        xytext=(2.6, -4.6), color=S[4], fontsize=8, arrowprops=dict(arrowstyle="->", color=S[4]))
            ax.annotate("socket 0.85 x 4.0\n(blind, drill point)", xy=(0.0, F.HEEL_SOCKET_DEPTH - 0.6),
                        xytext=(-7.6, 5.6), color=S[1], fontsize=8, arrowprops=dict(arrowstyle="->", color=S[1]))
            ax.annotate("flare R8 + lip\nonto the land", xy=(-0.7, -H_LAND + 0.1), xytext=(-7.6, -3.4),
                        color=plotstyle.TEXT_2, fontsize=8, arrowprops=dict(arrowstyle="->", color=plotstyle.TEXT_2))
            ax.annotate("conductor channel", xy=(-CH_B0, -H_LAND + 0.3), xytext=(-7.6, -5.2),
                        color=S[2], fontsize=8, arrowprops=dict(arrowstyle="->", color=S[2]))
        ax.axhline(-H_LAND, color=plotstyle.TEXT_2, lw=0.6, ls=":")
        ax.text(-7.5, -H_LAND + 0.15, f"land {H_LAND:.2f} below E", fontsize=7,
                color=plotstyle.TEXT_2)
        ax.plot([0], [0], "o", color=plotstyle.TEXT, ms=3)
        ax.text(0.2, 0.15, "E (mouth)", fontsize=7, color=plotstyle.TEXT)
        ax.set_aspect("equal")
        ax.set_xlim(-8, 8)
        ax.set_ylim(-6.5, 7)
        ax.set_title(title)
        ax.set_xlabel("mm")
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=3, fontsize=7)
    sc = res["strut_clearance"]["min"]
    fig.suptitle(f"Heel (NiTi root) - socket wall {res['socket']['min_wall']:.2f} mm, strut clearance {sc:.2f} mm, "
                 f"set screw {res['set_screw']['threads_engaged']} threads in brass", fontsize=10)
    fig.savefig(path)
    plt.close(fig)


def views(parts, path):
    """Four orthographic shaded views of the heel corner of the tub (matplotlib, dark)."""
    sys.path.insert(0, str(HERE.parents[1] / "tools"))
    import plotstyle
    plt = plotstyle.apply()
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    clip = Pos(61.0, 3.0, -7.0) * Box(14.5, 8.6, 7.6)            # x 53.75..68.25, y -1.3..7.3, z -10.8..-3.2
    hw = parts["hw"]
    shapes = [(parts["part_reamed"] & clip, "#8f96a3"), (hw["niti_root_worn"], "#e6e6e6"),
              (hw[SCREW_KEY], "#f2b632"), (hw["nut_M1.4_brass"], "#c98f2e"),
              (hw["strut_ref_worn"], "#5b9ff2"), (blade.adapter() & clip, "#8d7ff0")]
    tess = []
    for shp, col in shapes:
        vs, tris = shp.tessellate(0.02, 0.2)
        P = np.array([tuple(v) for v in vs])
        tess.append((P, np.array([list(t) for t in tris]), np.array(matplotlib_rgb(col))))
    fig = plt.figure(figsize=(11, 9.5))
    views_ = ((0, -90, "head side (from -y): keel, nut slot, arm root"),
              (0, 180, "front (from -x): pivot-boss disc, key hole"),
              (-90, -90, "underside (from -z): land, flare mouth, channel"),
              (-25, -140, "below / front / inboard"))
    for k, (elev, azim, ttl) in enumerate(views_):
        ax = fig.add_subplot(2, 2, k + 1, projection="3d")
        ax.set_proj_type("ortho")
        cam = np.array([math.cos(math.radians(elev)) * math.cos(math.radians(azim)),
                        math.cos(math.radians(elev)) * math.sin(math.radians(azim)), math.sin(math.radians(elev))])
        light = cam + np.array([0.25, 0.15, 0.45])
        light /= np.linalg.norm(light)
        polys, cols = [], []
        for P, T, base in tess:
            tri = P[T]
            nrm = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
            ln = np.linalg.norm(nrm, axis=1)
            ln[ln == 0] = 1
            sh = 0.30 + 0.70 * np.abs(nrm @ light) / ln
            polys.extend(list(tri))
            cols.extend(list(np.clip(base[None, :] * sh[:, None], 0, 1)))
        ax.add_collection3d(Poly3DCollection(polys, facecolors=cols, edgecolors="none"))
        ax.set_xlim(54.0, 68.0)
        ax.set_ylim(-3.0, 11.0)
        ax.set_zlim(-13.5, 0.5)
        ax.set_box_aspect((1, 1, 1), zoom=1.5)
        ax.view_init(elev=elev, azim=azim)
        ax.set_title(ttl)
        ax.set_axis_off()
    fig.suptitle("Heel corner of the tub. grey = tub + heel (one resin print), gold = M1.4 set screw + brass nut, "
                 "white = NiTi (worn), blue = strut (pad agent, worn, reference), violet = frame adapter",
                 fontsize=9)
    fig.savefig(path)
    plt.close(fig)


def route_figure(path, tub_r2=None):
    """Dark 3-panel diagram of the arm-wire path (2026-10-07): x-y section through the exit, the rear gap seen
    from behind (y-z), and the plan from outside (x-z) with the pads, fan-out, service loop and the build order."""
    sys.path.insert(0, str(HERE.parents[1] / "tools"))
    import plotstyle
    from matplotlib.patches import Rectangle as Rect, Polygon as MPoly
    plt = plotstyle.apply()
    S, T2 = plotstyle.SERIES, plotstyle.TEXT_2
    cell, pcb, cav = F.CELL, F.PCB, F.CAV
    bundle, wires = wire_route()
    chan = channel_path()[0]
    rc = route_checks()
    ch = None
    if tub_r2 is None:
        import shell_r2 as SR
        tub_r2 = SR.tub(sys.modules[__name__])
    fig, axs = plt.subplots(1, 3, figsize=(17.5, 7.4), gridspec_kw=dict(width_ratios=[1.05, 1.0, 1.25]))
    wc = {"J1": S[1], "J2": S[7], "J7": S[3], "J8": S[4]}

    # (a) section z = exit z, looking down (-z): x right (rearward), y up (outward)
    ax = axs[0]
    z0 = float(CH_EXIT[2])
    o = np.array([62.0, 7.0, z0])
    for ln in _section_lines(tub_r2, o, np.array([1.0, 0, 0]), np.array([0, 1.0, 0]), np.array([0, 0, 1.0])):
        xs, ys = zip(*ln)
        ax.plot([x + o[0] for x in xs], [y + o[1] for y in ys], color=S[0], lw=1.2)
    ax.add_patch(Rect((cell["x0"], cell["y0"]), cell["x1"] - cell["x0"], cell["y1"] - cell["y0"], fc=S[1], alpha=0.18, ec=S[1], lw=1.0))
    ax.text(59.0, 8.0, "cell\n(Renata 5.3 x 12 x 35)", color=S[1], fontsize=8)
    ax.add_patch(Rect((pcb["x0"], pcb["y0"]), pcb["x1"] - pcb["x0"], pcb["y1"] - pcb["y0"], fc=S[2], alpha=0.35, ec=S[2], lw=1.0))
    ax.text(58.2, 12.25, "board (hangs from the lid)", color=S[2], fontsize=7.5)
    ax.axhline(F.Y_SPLIT, color=T2, lw=0.7, ls="--")
    ax.text(58.1, 14.75, "dashed: seam y 12.1 (tub below, lid above)", color=T2, fontsize=7)
    ax.add_patch(Rect((57.8, cav["y1"]), cav["x1"] - 57.8, 0.8, fc=S[0], alpha=0.25, ec=S[0], lw=0.8))
    ax.text(58.1, 13.35, "lid", color=S[0], fontsize=7)
    ax.add_patch(Rect((pcb["x1"], cell["y1"]), cav["x1"] - pcb["x1"], cav["y1"] - cell["y1"], fc=S[3], alpha=0.10, ec="none"))
    ax.add_patch(Rect((cell["x1"], cav["y0"]), cav["x1"] - cell["x1"], cell["y1"] - cav["y0"], fc=S[3], alpha=0.10, ec="none"))
    ax.text(61.0, 12.55, "stowage zone", color=S[3], fontsize=8)
    ax.plot([p[0] for p in chan], [p[1] for p in chan], color=S[5], lw=2.0, label="heel channel D1.0 (neck D0.8)")
    ax.plot([p[0] for p in bundle], [p[1] for p in bundle], color=S[6], lw=4.0, alpha=0.9, solid_capstyle="round", label="4-wire bundle D0.51")
    for ref, w in wires.items():
        ax.plot([p[0] for p in w["pts"]], [p[1] for p in w["pts"]], color=wc[ref], lw=1.3)
    c = rc
    ax.annotate(f"exit hole D0.8, x {CH_EXIT[0]-0.4:.2f}-{CH_EXIT[0]+0.4:.2f}\n0.20 behind the cell's rear plane,\n"
                f"0.36 to its corner (0.3 VHB gap)", xy=(CH_EXIT[0], cav["y0"]), xytext=(58.2, 2.2), color=S[5], fontsize=7.5,
                arrowprops=dict(arrowstyle="->", color=S[5]))
    ax.annotate(f"bundle laid on the rear wall:\n{c['bundle']['to_cell']:.2f} to the cell", xy=(66.4, 8.5), xytext=(66.9, 6.6),
                color=S[6], fontsize=7.5, arrowprops=dict(arrowstyle="->", color=S[6]))
    ax.annotate(f"turn R1.0 over the cell's\nrear-top edge", xy=(65.7, 11.45), xytext=(62.6, 9.4), color=S[6], fontsize=7.5,
                arrowprops=dict(arrowstyle="->", color=S[6]))
    ax.set_xlim(57.8, 68.6)
    ax.set_ylim(0.0, 15.2)
    ax.set_aspect("equal")
    ax.set_xlabel("x (mm, rearward)")
    ax.set_ylabel("y (mm, outward from the head)")
    ax.set_title(f"(a) Section at z {z0:.2f} (through the exit), seen from above\nheel + tub section in blue", fontsize=9)
    ax.legend(loc="lower left", fontsize=7, labelcolor=plotstyle.TEXT)

    # (b) the rear gap seen from behind (looking forward, -x): y right (outward), z up
    ax = axs[1]
    ax.add_patch(Rect((cell["y0"], cell["z0"]), cell["y1"] - cell["y0"], cell["z1"] - cell["z0"], fc=S[1], alpha=0.18, ec=S[1], lw=1.0))
    ax.text(6.2, -7.6, "cell's rear end\n(x 65.6, in front\nof the wires)", color=S[1], fontsize=7.5)
    ax.add_patch(Rect((pcb["y0"], pcb["z0"]), pcb["y1"] - pcb["y0"], pcb["z1"] - pcb["z0"], fc=S[2], alpha=0.35, ec=S[2], lw=1.0))
    ax.text(12.15, -9.4, "board\nrear edge\n(x 60.55)", color=S[2], fontsize=7)
    ax.add_patch(Rect((F.Y_IN, cav["z0"] - 0.8), cav["y0"] - F.Y_IN, cav["z1"] - cav["z0"] + 1.6, fc=S[0], alpha=0.25, ec=S[0], lw=0.8))
    ax.text(3.0, 4.4, "tub inner wall", color=S[0], fontsize=7)
    ax.add_patch(Rect((cav["y1"], cav["z0"] - 0.8), 0.8, cav["z1"] - cav["z0"] + 1.6, fc=S[0], alpha=0.25, ec=S[0], lw=0.8))
    ax.text(13.3, 4.4, "lid", color=S[0], fontsize=7)
    ax.axvline(F.Y_SPLIT, color=T2, lw=0.7, ls="--")
    ax.add_patch(MPoly([(cav["y0"], cav["z0"]), (cav["y0"] + 1.0, cav["z0"]), (cav["y0"], cav["z0"] + 1.0)], fc=S[0], alpha=0.35, ec="none"))
    ax.plot([CH_EXIT[1] - 0.05], [CH_EXIT[2]], "o", ms=9, mfc="none", mec=S[5], mew=2)
    ax.plot([p[1] for p in bundle], [p[2] for p in bundle], color=S[6], lw=4.0, alpha=0.9, solid_capstyle="round")
    for ref, w in wires.items():
        ax.plot([p[1] for p in w["pts"]], [p[2] for p in w["pts"]], color=wc[ref], lw=1.3)
        ax.plot([w["pad"][1]], [w["pad"][2]], "s", ms=5, color=wc[ref])
    ax.annotate("exit (heel channel\nends here, D0.8)", xy=(CH_EXIT[1], CH_EXIT[2]), xytext=(5.6, -2.0), color=S[5], fontsize=7.5,
                arrowprops=dict(arrowstyle="->", color=S[5]))
    ax.annotate("bundle climbs the 1.1 gap\ndiagonally (bend R2.0),\nflat on the rear wall", xy=(8.6, -2.4), xytext=(8.1, -6.2),
                color=S[6], fontsize=7.5, arrowprops=dict(arrowstyle="->", color=S[6]))
    ax.set_xlim(2.5, 15.0)
    ax.set_ylim(-10.5, 5.5)
    ax.set_aspect("equal")
    ax.set_xlabel("y (mm, outward)")
    ax.set_ylabel("z (mm, up)")
    ax.set_title("(b) Rear gap x 65.6-66.7, seen from behind\n(the rear wall removed)", fontsize=9)

    # (c) plan from outside (through the lid): x right (rearward), z up
    ax = axs[2]
    ax.add_patch(Rect((cav["x0"], cav["z0"]), cav["x1"] - cav["x0"], cav["z1"] - cav["z0"], fc="none", ec=S[0], lw=1.0))
    ax.add_patch(Rect((cell["x0"], cell["z0"]), cell["x1"] - cell["x0"], cell["z1"] - cell["z0"], fc=S[1], alpha=0.12, ec=S[1], lw=0.8, ls=":"))
    ax.add_patch(Rect((pcb["x0"], pcb["z0"]), pcb["x1"] - pcb["x0"], pcb["z1"] - pcb["z0"], fc=S[2], alpha=0.15, ec=S[2], lw=1.0))
    ax.add_patch(Rect((pcb["x1"], cav["z0"]), cav["x1"] - pcb["x1"], cav["z1"] - cav["z0"], fc=S[3], alpha=0.10, ec="none"))
    ax.text(pcb["x1"] + 0.3, cav["z0"] + 0.3, "stowage\n(dock + cell\nwires: lower\nhalf)", color=S[3], fontsize=7)
    import re
    txt = (HERE.parents[1] / "hw/pod/draft_r2/out/routed.kicad_pcb").read_text()
    for ref in ("J3", "J4", "J5", "J9", "J10", "J11", "J12"):
        i = txt.index(f'"Reference" "{ref}"')
        bx, by = (float(v) for v in re.search(r"\(at ([\d.\-]+) ([\d.\-]+)", txt[txt.rfind("(footprint ", 0, i):i]).groups())
        ax.add_patch(plt.Circle((pcb["x0"] + bx, pcb["z0"] + by), 0.5, fc="none", ec=T2, lw=0.7))
        ax.text(pcb["x0"] + bx - 0.5, pcb["z0"] + by - 1.1, ref, color=T2, fontsize=6)
    ax.plot([p[0] for p in bundle], [p[2] for p in bundle], color=S[6], lw=4.0, alpha=0.9, solid_capstyle="round", label="4-wire bundle")
    for ref, w in wires.items():
        ax.plot([p[0] for p in w["pts"]], [p[2] for p in w["pts"]], color=wc[ref], lw=1.5, label=f"{ref} {w['net']}")
        ax.add_patch(plt.Circle((w["pad"][0], w["pad"][2]), 0.5, fc=wc[ref], alpha=0.5, ec=wc[ref]))
    lp = rc["service"]["service_loop_mm"]
    th = np.linspace(0, math.pi, 30)
    ax.plot(64.2 + 0.9 * np.cos(th), 1.0 + 1.4 * np.sin(th) + 0.9, color=S[6], lw=2.0, ls="--")
    ax.plot([63.3, 63.3], [0.8, 1.9], color=S[6], lw=2.0, ls="--")
    ax.plot([65.1, 65.1], [0.8, 1.9], color=S[6], lw=2.0, ls="--")
    ax.annotate(f"service loop +{lp:.0f} mm (one U,\nR >= 0.9): lets the lid\nopen 180 deg about its\nrear edge for cell swap", xy=(64.2, 3.3),
                xytext=(45.0, 4.4), color=S[6], fontsize=7.5, arrowprops=dict(arrowstyle="->", color=S[6]))
    ax.plot([CH_EXIT[0]], [CH_EXIT[2]], "o", ms=9, mfc="none", mec=S[5], mew=2)
    ax.text(CH_EXIT[0] - 2.6, CH_EXIT[2] - 1.0, "heel exit", color=S[5], fontsize=7.5)
    steps = ("Build order (arm wires)\n"
             "1 cap + strut done, pre-shrunk tube on\n"
             "2 fish 4 ends land -> exit, tub EMPTY\n"
             "3 solder J1 J7 J2 J8 (B face), board\n   loose, BEFORE the lid VHB bond\n"
             "4 bond board to lid (step 3-5 shell_r2)\n"
             "5 lay bundle on the rear wall, RTV dot\n   at the exit, let it skin\n"
             "6 cell drops in (y-), bundle stays\n   behind it in the 1.1 gap\n"
             "7 fold the loop, lower the lid")
    ax.text(44.3, -17.6, steps, color=plotstyle.TEXT, fontsize=7.2, va="bottom",
            bbox=dict(boxstyle="round", fc=plotstyle.SURFACE, ec=T2, lw=0.6))
    ax.set_xlim(44.0, 67.5)
    ax.set_ylim(-18.0, 7.5)
    ax.set_aspect("equal")
    ax.set_xlabel("x (mm, rearward)")
    ax.set_ylabel("z (mm, up)")
    ax.set_title("(c) Plan from outside, through the lid (board on top, cell below it)\npads on the board's B face (toward the cell)", fontsize=9)
    ax.legend(loc="lower right", fontsize=6.8, ncol=1, labelcolor=plotstyle.TEXT)
    b = rc["bundle"]
    fig.suptitle(f"Arm wires: heel exit -> rear gap -> stowage -> J1/J7/J2/J8 (right pod; left = mirror). Clearances: bundle-cell "
                 f"{b['to_cell']:.2f}, -seam {b['to_rear_seam']:.2f}, -lid {b['to_lid_inner']:.2f}; wires under the board edge "
                 f"{min(w['at_board_edge_below_B'] for w in rc['wires'].values()):.2f}, wire-other pad "
                 f"{min(w['to_other_pads_copper'] for w in rc['wires'].values()):.2f} mm", fontsize=9.5, color=plotstyle.TEXT)
    fig.savefig(path)
    plt.close(fig)


def matplotlib_rgb(c):
    import matplotlib.colors as mc
    return mc.to_rgb(c)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for f in list(OUT.glob("*.step")) + list(OUT.glob("*.stl")):
        f.unlink()
    res, parts = checks()
    hw = hardware()
    parts["hw"] = hw
    export_step(parts["heel_add"], str(OUT / "heel_add.step"))
    export_step(parts["heel_cut"], str(OUT / "heel_cut.step"))
    export_step(heel_cut(undersize=True), str(OUT / "heel_cut_print.step"))
    export_step(parts["part_reamed"], str(OUT / "tub_with_heel_preview.step"))
    try:                                   # the real tub (strut relief etc.) for pad.py's cross-check (reg-arm issue 6)
        import shell_r2 as SR
        export_step(SR.tub(sys.modules[__name__]), str(OUT / "tub_r2_with_heel.step"))
    except Exception as ex:  # noqa: BLE001
        print("r2 tub export failed:", repr(ex))
    export_stl(parts["heel_only"], str(OUT / "heel_only.stl"), tolerance=0.01, angular_tolerance=0.1)
    preview_print = (parts["tub"] + parts["heel_add"]) - heel_cut(undersize=True)
    export_stl(preview_print, str(OUT / "tub_with_heel_print_preview.stl"), tolerance=0.01, angular_tolerance=0.1)
    for k, s in hw.items():
        export_step(s, str(OUT / f"{k}.step"))
    res["outputs"] = sorted(p.name for p in OUT.iterdir() if p.suffix in (".step", ".stl"))
    res["date"] = "2026-10-07"
    res["frame_inputs"] = {"E": E.tolist(), "A_E": A.round(5).tolist(), "N_BEND": N.round(5).tolist(),
                           "SOCKET_D": F.SOCKET_D, "HEEL_SOCKET_DEPTH": F.HEEL_SOCKET_DEPTH,
                           "FLEX_ZONE": F.FLEX_ZONE, "STRUT_START": F.STRUT_START,
                           "SHROUD_CLEARANCE": F.SHROUD_CLEARANCE}
    (OUT / "checks.json").write_text(json.dumps(res, indent=2, default=lambda o: bool(o) if isinstance(o, np.bool_) else str(o)))
    try:
        figure(parts, res, OUT / "heel_sections.png")
        views(parts, OUT / "heel_views.png")
        route_figure(HERE.parents[1] / "docs/diagrams/heel-wire-route.png")
    except Exception as ex:  # figures are a convenience; never block the checks
        print("figure failed:", repr(ex))
    print(json.dumps({k: v for k, v in res.items() if k not in ("outputs",)}, indent=1,
                     default=lambda o: bool(o) if isinstance(o, np.bool_) else str(o)))


if __name__ == "__main__":
    main()
