"""Read the mic-port geometry from the sources of truth, without executing CAD.

Which design: hw/current.yaml via tools/current.py (2026-10-07). Phase 2 (default): duct stack from hw/mech/dims_r2.py
(the CAD-free constants shell_r2.py builds from; imported, never AST-parsed) and U2's hole on the Phase-2 routed board.
Reference (env ULTRASONIC_DESIGN=revg): the Rev F path below, unchanged.
 * lid / shell:  hw/mech/shell_r1.py  (revg; AST: module constants + lid_base() bore / hex-window / lip / rib calls)
 * board hole:   the NPTH pad of footprint U2 in a .kicad_pcb (pcbnew, read-only) -> position, drill, board thickness;
                 F-side footprints inside the lid-board gap (obstacles, reported only)
 * mic port:     datasheet constants (D0.325 +-0.05) and assumptions marked ASSUMED

Layout-agnostic: nothing here is hard-wired except fall-backs; every field records where it came from
(Geom.src) and a fall-back is flagged in Geom.warnings.  Re-run after ANY change to the shell (dims_r2.py) or the board.
Board choice: --board / env ACO_BOARD, else hw/current.yaml `board` (no candidate list, no mtime guess).
All lengths in this module's output are metres.
"""
from __future__ import annotations

import ast
import math
import os
from dataclasses import dataclass, field, replace
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MM = 1e-3

SHELL = REPO / "hw/mech/shell_r1.py"          # the revg (reference) shell; Phase 2 reads current().shell_dims


def design(name=None):
    """hw/current.yaml through tools/current.py (env ULTRASONIC_DESIGN=revg selects the reference)."""
    import sys  # noqa: PLC0415
    if str(REPO / "tools") not in sys.path:
        sys.path.insert(0, str(REPO / "tools"))
    from current import current  # noqa: PLC0415
    return current(name)


@dataclass(frozen=True)
class Geom:
    # lid (shell_r1.py lid_base)
    a_recess: float = 1.7263e-3        # equivalent-circle radius of the hex window (area-equal)
    hex_circum_r: float = 1.9e-3
    d_recess: float = 0.8e-3           # window depth from the outer face
    a_bore: float = 0.5e-3
    l_bore: float = 0.9e-3             # lid inner face to window floor
    # gap
    h_gap: float = 1.5e-3              # lid inner face to board outer face
    # board
    t_board: float = 0.8e-3
    a_hole: float = 0.3e-3
    offset: float = 0.0                # lateral distance bore axis -> board hole axis (magnitude)
    off_ang: float = math.pi           # direction of the offset in the gap plane (rad; pi = towards the near x wall)
    # gap channel as a rectangle (lid lip inner faces in x, clamp-rib inner faces in z); bore axis inside it
    cav_lx: float = 35.1e-3
    cav_lz: float = 11.8e-3
    bore_cx: float = 3.55e-3
    bore_cz: float = 5.9e-3
    # mic (datasheet p.9: AP D0.325 +-0.05; others ASSUMED)
    a_port: float = 0.1625e-3
    l_port: float = 0.25e-3            # ASSUMED package port length (substrate), not in the datasheet
    a_ring: float = 0.5125e-3          # footprint copper ring ID 1.025
    t_standoff: float = 0.06e-3        # ASSUMED reflowed solder / paste standoff mic-to-board
    src: dict = field(default_factory=dict, compare=False)
    warnings: tuple = field(default_factory=tuple, compare=False)
    info: dict = field(default_factory=dict, compare=False)

    def with_(self, **kw):
        return replace(self, **kw)

    @property
    def hole_cx(self):
        return self.bore_cx + self.offset * math.cos(self.off_ang)

    @property
    def hole_cz(self):
        return self.bore_cz + self.offset * math.sin(self.off_ang)


# ---------------------------------------------------------------------------------------------- AST
def _ev(node, env):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        return env[node.id]
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_ev(node.operand, env)
    if isinstance(node, ast.BinOp):
        a, b = _ev(node.left, env), _ev(node.right, env)
        return {ast.Add: lambda: a + b, ast.Sub: lambda: a - b, ast.Mult: lambda: a * b, ast.Div: lambda: a / b}[type(node.op)]()
    if isinstance(node, ast.Tuple):
        return tuple(_ev(e, env) for e in node.elts)
    if isinstance(node, ast.Subscript):
        return _ev(node.value, env)[_ev(node.slice, env)]
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "dict":
        return {k.arg: _ev(k.value, env) for k in node.keywords}
    raise ValueError(ast.dump(node)[:80])


def _flatten_mult(node):
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
        return _flatten_mult(node.left) + _flatten_mult(node.right)
    return [node]


def _box_args(call, env):
    """box(x0, x1, y0, y1, z0, z1) -> dict, or None."""
    if isinstance(call, ast.Call) and getattr(call.func, "id", "") == "box" and len(call.args) == 6:
        v = [_ev(a, env) for a in call.args]
        return dict(x0=v[0], x1=v[1], y0=v[2], y1=v[3], z0=v[4], z1=v[5])
    return None


def read_shell(path=SHELL):
    """-> dict with module env, bore radius, window circumradius/depth, lid lip inner box, clamp ribs; raises on failure."""
    tree = ast.parse(Path(path).read_text())
    env = {}
    for n in tree.body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1:
            tgt = n.targets[0]
            names = [tgt.id] if isinstance(tgt, ast.Name) else [e.id for e in getattr(tgt, "elts", []) if isinstance(e, ast.Name)]
            try:
                val = _ev(n.value, env)
            except Exception:
                continue
            if isinstance(tgt, ast.Name):
                env[tgt.id] = val
            elif isinstance(val, tuple) and len(val) == len(names):
                env.update(dict(zip(names, val)))
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "lid_base")
    out = {"env": env, "ribs": []}
    for node in ast.walk(fn):
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") in ("lip_i", "lip_o"):
            try:
                out[node.targets[0].id] = _box_args(node.value, env)
            except Exception:                              # noqa: BLE001
                pass
        if isinstance(node, ast.For) and isinstance(node.target, ast.Name):
            try:
                vals = _ev(node.iter, env)
            except Exception:                              # noqa: BLE001
                continue
            for v in vals:
                e2 = dict(env, **{node.target.id: v})
                for sub in ast.walk(ast.Module(body=node.body, type_ignores=[])):
                    if isinstance(sub, ast.Call) and getattr(sub.func, "id", "") == "box":
                        try:
                            b = _box_args(sub, e2)
                        except Exception:                  # noqa: BLE001
                            b = None
                        if b:
                            out["ribs"].append(b)
        if not (isinstance(node, ast.Assign) and isinstance(node.value, ast.BinOp) and isinstance(node.value.op, ast.Sub)):
            continue
        factors = _flatten_mult(node.value.right)
        pos = next((f for f in factors if isinstance(f, ast.Call) and getattr(f.func, "id", "") == "Pos"), None)
        if pos is None or "MIC" not in ast.unparse(pos):
            continue
        y_pos = _ev(pos.args[1], env)
        for f in factors:
            if isinstance(f, ast.Call) and getattr(f.func, "id", "") == "Cylinder":
                out["bore_r"] = _ev(f.args[0], env)
                out["bore_len_drawn"] = _ev(f.args[1], env)
                out["bore_y_centre"] = y_pos
            if isinstance(f, ast.Call) and getattr(f.func, "id", "") == "extrude":
                poly = f.args[0]
                out["hex_R"] = _ev(poly.args[0], env)
                out["hex_n"] = _ev(poly.args[1], env)
                amt = next(k.value for k in f.keywords if k.arg == "amount")
                out["hex_amount"] = _ev(amt, env)
                out["hex_both"] = any(k.arg == "both" and getattr(k.value, "value", False) for k in f.keywords)
                out["hex_y_centre"] = y_pos
    return out


def probe_board(board_path, port_xy_hint=None, gap_box=None):
    """pcbnew read-only: U2 NPTH pad position (board mm), drill (mm), thickness setting (mm), footprint pose,
    and the F-side footprints (bounding boxes) as obstacles in the gap."""
    import pcbnew  # noqa: PLC0415  (optional: absent => fall back)
    b = pcbnew.LoadBoard(str(board_path))
    fp = b.FindFootprintByReference("U2")
    pads = [p for p in fp.Pads() if p.GetDrillSize().x > 0]
    p = pads[0]
    px, py = p.GetPosition().x / 1e6, p.GetPosition().y / 1e6
    edge = b.GetBoardEdgesBoundingBox()
    fparts, near = 0.0, []
    for f in b.GetFootprints():
        if f.GetLayerName() != "F.Cu":
            continue
        bb = f.GetBoundingBox(False)
        x0, y0 = bb.GetX() / 1e6, bb.GetY() / 1e6
        x1, y1 = x0 + bb.GetWidth() / 1e6, y0 + bb.GetHeight() / 1e6
        fparts += (x1 - x0) * (y1 - y0)
        d = math.hypot(max(x0 - px, 0, px - x1), max(y0 - py, 0, py - y1))
        near.append((round(d, 2), f.GetReference(), str(f.GetFPID().GetLibItemName())[:40]))
    near.sort()
    # gasket seat (sealed-duct option): what crosses the F face within r 1.6 mm of the port (sub-audio-in issue 2 keep-out)
    seat = []
    for t in b.GetTracks():
        is_via = t.GetClass() == "PCB_VIA"
        if not is_via and t.GetLayerName() != "F.Cu":
            continue
        if is_via:
            d = math.hypot(t.GetPosition().x / 1e6 - px, t.GetPosition().y / 1e6 - py) - t.GetWidth(pcbnew.F_Cu) / 2e6
        else:
            ax_, ay_, bx_, by_ = t.GetStart().x / 1e6, t.GetStart().y / 1e6, t.GetEnd().x / 1e6, t.GetEnd().y / 1e6
            L2 = (bx_ - ax_) ** 2 + (by_ - ay_) ** 2
            u = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax_) * (bx_ - ax_) + (py - ay_) * (by_ - ay_)) / L2))
            d = math.hypot(ax_ + u * (bx_ - ax_) - px, ay_ + u * (by_ - ay_) - py) - t.GetWidth() / 2e6
        if d < 1.6:
            seat.append(("via" if is_via else "F track", t.GetNetname(), round(d, 2)))
    seat.sort(key=lambda r: r[2])
    return dict(gasket_seat_r1p6=seat[:8],port_xy=(px, py), drill=p.GetDrillSize().x / 1e6,
                body_xy=(fp.GetPosition().x / 1e6, fp.GetPosition().y / 1e6), rot=fp.GetOrientationDegrees(),
                layer=fp.GetLayerName(), thickness_setting=b.GetDesignSettings().GetBoardThickness() / 1e6,
                board_wh=(edge.GetWidth() / 1e6, edge.GetHeight() / 1e6),
                f_side_bbox_area_mm2=round(fparts, 1), f_side_nearest=near[:4])


def find_board(explicit=None, d=None):
    if explicit:
        return explicit if Path(explicit).exists() else None
    if os.environ.get("ACO_BOARD"):
        return os.environ["ACO_BOARD"]
    b = (d or design()).board
    return str(b) if b.exists() else None


def import_dims(path):
    """Import a CAD-free dims module (hw/mech/dims_r2.py) by path; it puts hw/mech on sys.path itself (frame.py)."""
    import importlib.util  # noqa: PLC0415
    spec = importlib.util.spec_from_file_location(Path(path).stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_r2(d, board=None) -> Geom:
    """Phase 2 (ECR-0018): reamed D1.0 lid bore + hex window (mesh seat) -> D1.0 hole in the 0.25 VHB across the 0.30 F gap
    (sealed) -> board hole D0.6 through 0.8. Numbers from d.shell_dims (dims_r2.py); offset from U2's NPTH on the board."""
    src, warn, info = {}, [], {"design": d.id}
    D = import_dims(d.shell_dims)
    rel = lambda p: str(Path(p).resolve().relative_to(REPO))  # noqa: E731
    area = 6 / 2 * D.HEX_R ** 2 * math.sin(2 * math.pi / 6)
    floor_y = D.Y_TOP - D.HEX_DEPTH
    g = Geom().with_(a_recess=math.sqrt(area / math.pi) * MM, hex_circum_r=D.HEX_R * MM, d_recess=D.HEX_DEPTH * MM,
                     a_bore=D.DUCT_D / 2 * MM, l_bore=(floor_y - D.Y_LID_IN) * MM, h_gap=D.F_GAP * MM, t_board=D.PCB_T * MM,
                     a_hole=D.MIC_HOLE_D / 2 * MM,
                     # no open channel in Phase 2 (VHB fills the F gap); the rectangle is the VHB outline, used only by open-gap what-ifs
                     cav_lx=(D.PCB_L - 0.4) * MM, cav_lz=(D.PCB_H - 0.4) * MM,
                     bore_cx=(D.MIC[0] - D.PCB["x0"] - 0.2) * MM, bore_cz=(D.MIC[1] - D.PCB["z0"] - 0.2) * MM)
    src["lid"] = (f"{d.rel['shell_dims']} (shell {d.rel['shell']}): bore D{D.DUCT_D} reamed, lid inner face y {D.Y_LID_IN:.2f} -> window floor "
                  f"y {floor_y:.2f} (bore {floor_y - D.Y_LID_IN:.2f}), hex R {D.HEX_R} x {D.HEX_DEPTH} deep, sealed VHB duct {D.F_GAP} (F gap), "
                  f"PCB y {D.PCB['y0']:.2f}-{D.PCB['y1']:.2f}, MIC ({D.MIC[0]:.2f}, {D.MIC[1]:.2f})")
    src["gap_channel"] = "Phase 2: none (VHB full-face bond, D1.0 duct hole); open-gap scenarios use the VHB outline as a what-if"
    do = D.duct_offsets()
    info["duct_locating"] = dict(method="stepped gauge pin through the reamed bore into the board hole during bonding (shell_r2 duct_offsets)",
                                 worst_mm=do["worst_with_gauge_pin"], limit_mm=do["limit_R_ACO_P5"], walls_only_worst_mm=do["worst_walls_only"],
                                 src=f"{d.rel['shell_dims']}:duct_offsets [A] tolerances")
    bpath = find_board(board, d)
    try:
        if bpath is None:
            raise FileNotFoundError(f"no board at {d.rel['board']}")
        pr = probe_board(bpath)
        px, py = pr["port_xy"]
        dx = D.PCB["x0"] + px - D.MIC[0]
        # one board, two pods (O16-5): board +y = pod +z in one pod (dims_r2.bpt), -z in the mirrored one; take the worse
        dz = max([D.PCB["z0"] + py - D.MIC[1], D.PCB["z1"] - py - D.MIC[1]], key=abs)
        off = math.hypot(dx, dz)
        g = g.with_(offset=off * MM, off_ang=(math.atan2(dz, dx) if off > 1e-6 else math.pi), a_hole=pr["drill"] / 2 * MM)
        import time as _t
        src["board"] = (f"{rel(bpath)} (mtime {_t.strftime('%Y-%m-%d %H:%M', _t.localtime(os.path.getmtime(bpath)))}): U2 NPTH D{pr['drill']} at board "
                        f"{pr['port_xy']} (pcbnew), U2 origin {pr['body_xy']}, rot {pr['rot']}, {pr['layer']}; port-to-duct offset dx {dx:+.2f} dz {dz:+.2f} mm "
                        f"(dims_r2 MIC is read from {d.rel['board']}, so the routed board gives 0 by construction; another board shows its real offset)")
        info.update(gasket_seat_items_within_r1p6_mm=pr["gasket_seat_r1p6"], board_thickness_setting_mm=pr["thickness_setting"],
                    f_side_bbox_area_mm2=pr["f_side_bbox_area_mm2"], board_area_mm2=round(pr["board_wh"][0] * pr["board_wh"][1], 1),
                    f_side_nearest_to_port=pr["f_side_nearest"], board_file=rel(bpath))
        if abs(pr["thickness_setting"] - D.PCB_T) > 0.05:
            warn.append(f"board file general thickness {pr['thickness_setting']} mm != shell PCB {D.PCB_T:.2f} mm: the fab order must say the shell value")
        if off > do["limit_R_ACO_P5"] + 1e-9:
            warn.append(f"board port is {off:.2f} mm from the duct axis (limit {do['limit_R_ACO_P5']:.2f} = r_duct - r_hole; ECR-0011 class)")
    except Exception as e:                                # noqa: BLE001
        warn.append(f"board not probed ({e!r}): port offset = 0 (duct follows the hole by construction), D{D.MIC_HOLE_D} hole")
        src["board"] = f"FALLBACK offset 0, D{D.MIC_HOLE_D} hole"
    src["mic"] = "datasheet Rev B-1 p.9: AP D0.325 +-0.05; port length, standoff ASSUMED"
    return replace(g, src=src, warnings=tuple(warn), info=info)


def load(board=None, quiet=True, design_name=None) -> Geom:
    """Geometry of the selected design (hw/current.yaml; env ULTRASONIC_DESIGN=revg for the Rev F reference)."""
    d = design(design_name)
    if not d.is_reference:
        return load_r2(d, board)
    src, warn, info = {}, [], {"design": d.id}
    g = Geom()
    pcb = dict(x0=30.6, x1=64.6, y0=12.1, y1=12.9, z0=-8.6, z1=4.4)
    mic_x, mic_z = 34.5, -2.1
    try:
        sh = read_shell()
        env = sh["env"]
        R, n = sh["hex_R"], sh["hex_n"]
        area = n / 2 * R * R * math.sin(2 * math.pi / n)
        depth = sh["hex_amount"]                        # 'both=True' extrudes +-amount about the plate top: depth = amount
        floor_y = sh["hex_y_centre"] - sh["hex_amount"]
        y_split = env["Y_SPLIT"]
        pcb = env["PCB"]
        mic_x, mic_z = env["MIC"]
        cav = env.get("CAV")
        if cav:   # free travel of the board in its cavity (00-whole risk 8: no x stop); feeds the sealed-duct tolerance stack
            info["board_slide_mm"] = dict(x_minus=round(pcb["x0"] - cav["x0"], 3), x_plus=round(cav["x1"] - pcb["x1"], 3),
                                          z_minus=round(pcb["z0"] - cav["z0"], 3), z_plus=round(cav["z1"] - pcb["z1"], 3),
                                          src=f"{SHELL.relative_to(REPO)}: CAV vs PCB (AST); no x stop modelled")
        g = g.with_(a_recess=math.sqrt(area / math.pi) * MM, hex_circum_r=R * MM, d_recess=depth * MM,
                    a_bore=sh["bore_r"] * MM, l_bore=(floor_y - y_split) * MM,
                    h_gap=(y_split - pcb["y1"]) * MM, t_board=(pcb["y1"] - pcb["y0"]) * MM)
        src["lid"] = (f"{SHELL.relative_to(REPO)}: lid_base() AST (bore r {sh['bore_r']}, hex R {R}, window floor y {floor_y:.2f}, "
                      f"Y_SPLIT {y_split}, PCB y {pcb['y0']}-{pcb['y1']}, MIC ({mic_x}, {mic_z:.2f}))")
        # gap channel: x between the lid lip inner faces, z between the clamp-rib inner faces (ribs span the gap height)
        lip = sh.get("lip_i")
        ribs = [r for r in sh["ribs"] if r["y1"] >= y_split - 1e-6 and r["y0"] <= pcb["y1"] + 0.2]
        if lip and len(ribs) >= 2:
            zr_lo = max(r["z1"] for r in ribs if r["z1"] <= mic_z)
            zr_hi = min(r["z0"] for r in ribs if r["z0"] >= mic_z)
            g = g.with_(cav_lx=(lip["x1"] - lip["x0"]) * MM, cav_lz=(zr_hi - zr_lo) * MM,
                        bore_cx=(mic_x - lip["x0"]) * MM, bore_cz=(mic_z - zr_lo) * MM)
            src["gap_channel"] = (f"lip_i x {lip['x0']:.2f}..{lip['x1']:.2f} (lip hangs {y_split - sh.get('lip_o', lip)['y0']:.1f} of the {y_split - pcb['y1']:.1f} mm gap), "
                                  f"clamp ribs inner faces z {zr_lo:.2f}..{zr_hi:.2f} (full gap height); bore at ({mic_x - lip['x0']:.2f}, {mic_z - zr_lo:.2f}) in it")
        else:
            warn.append("lid lip / clamp ribs not parsed: gap channel = last-known 35.1 x 11.8 mm")
            src["gap_channel"] = "FALLBACK 35.1 x 11.8 mm (2026-10-02)"
    except Exception as e:                                # noqa: BLE001
        warn.append(f"shell_r1.py not parsed ({e!r}): lid dimensions are the last-known constants (2026-10-02)")
        src["lid"] = "FALLBACK constants (shell_r1.py 2026-10-02)"
    bpath = find_board(board, d)
    try:
        if bpath is None:
            raise FileNotFoundError("no .kicad_pcb")
        pr = probe_board(bpath)
        bh = pcb["z1"] - pcb["z0"]
        dx = pcb["x0"] + pr["port_xy"][0] - mic_x
        zc = (pcb["z0"] + pcb["z1"]) / 2
        # one board, two pods (O16-5): board y maps to +z in one pod and -z in the other; take the worse pod
        dz_cands = [zc + (pr["port_xy"][1] - bh / 2) - mic_z, zc - (pr["port_xy"][1] - bh / 2) - mic_z]
        dz = max(dz_cands, key=abs)
        off = math.hypot(dx, dz)
        g = g.with_(offset=off * MM, off_ang=(math.atan2(dz, dx) if off > 1e-6 else math.pi), a_hole=pr["drill"] / 2 * MM)
        mt = os.path.getmtime(bpath)
        import time as _t
        src["board"] = (f"{Path(bpath).resolve().relative_to(REPO)} (mtime {_t.strftime('%Y-%m-%d %H:%M', _t.localtime(mt))}): U2 NPTH D{pr['drill']} at board "
                        f"{pr['port_xy']} (pcbnew), U2 origin {pr['body_xy']}, rot {pr['rot']}, {pr['layer']}; port-to-lid-bore offset dx {dx:+.2f} dz {dz:+.2f} mm")
        info.update(gasket_seat_items_within_r1p6_mm=pr["gasket_seat_r1p6"], board_thickness_setting_mm=pr["thickness_setting"], f_side_bbox_area_mm2=pr["f_side_bbox_area_mm2"],
                    board_area_mm2=round(pr["board_wh"][0] * pr["board_wh"][1], 1), f_side_nearest_to_port=pr["f_side_nearest"],
                    board_file=str(Path(bpath).resolve().relative_to(REPO)))
        if abs(pr["thickness_setting"] - g.t_board / MM) > 0.05:
            warn.append(f"board file general thickness {pr['thickness_setting']} mm != shell PCB {g.t_board / MM:.2f} mm: "
                        "the fab order must say the shell value; a 1.6 mm board doubles the hole length (tornado 'board thickness')")
        if off > 0.2:
            warn.append(f"board port is {off:.2f} mm from the lid bore axis (spec s8 L511 'opening directly over the hole'; ECR-0011 class)")
    except Exception as e:                                # noqa: BLE001
        warn.append(f"board not probed ({e!r}): port offset = 0 (Rev F placement, 2026-10-02), D0.6 hole")
        src["board"] = "FALLBACK offset 0, D0.6 hole"
    src["mic"] = "datasheet Rev B-1 p.9: AP D0.325 +-0.05; port length, standoff ASSUMED"
    return replace(g, src=src, warnings=tuple(warn), info=info)


if __name__ == "__main__":
    g = load()
    for k, v in g.__dict__.items():
        if k not in ("src", "warnings", "info", "off_ang"):
            print(f"{k:14s} {v / MM:8.4f} mm")
    print("off_ang", round(math.degrees(g.off_ang), 1), "deg")
    print(g.src)
    print(g.info)
    print(g.warnings)
