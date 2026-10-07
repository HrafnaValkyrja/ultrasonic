#!/usr/bin/env python3
"""Interface checks: do BOTH sides of each interface say the same thing? (disagreement, not change)

    source tools/env.sh
    python3 tools/checks/interfaces.py [--board PATH] [--root DIR] [--json] [-v|-vv] [--strict] [--no-selftest]
                                       [--baseline FILE | --write-baseline FILE]
    (--contract --budget --heights --netlist --ecr-dir --mech-dir override one input each; --root re-bases all of them)

Layout-agnostic and read-only. Default inputs = the current design in hw/current.yaml (tools/current.py, 2026-10-07): Phase 2 =
hw/pod/draft_r2/out/routed.kicad_pcb, hw/pod/pod_mz2.net, the SKiDL circuit built with POD_PACKAGES=mz2 (hw/pod/system_map.py
build(): gen.build() + gen.apply_packages()), and the shell facts from hw/mech/dims_r2.py (CAD-free constants of shell_r2.py,
imported). env ULTRASONIC_DESIGN=revg checks the Rev G/F reference: hw/pod/draft_r1/pod_r1_routed.kicad_pcb, hw/pod/pod.net and
hw/mech/shell_r1.py (parsed with ast, never imported: importing it pulls in the CAD kernel). Always read: frame.py, pod.py (imported, CAD-free), ST's open
pin data (tools/data/stm32_open_pin_data) and three tables kept next to the thing they describe. It never edits any of them and
moves nothing on the board. One line per check, "PASS|WARN|FAIL <id> <message>"; exit 1 if any FAIL (2 if the tool environment
is missing: run `source tools/env.sh`). -v adds detail lines under each non-PASS result, -vv under every result, --json prints
machine-readable results, --strict turns WARN into FAIL (release gate). About 3 s (SKiDL build + board loads): fit for a git
pre-commit hook. Every WARN has a stable id (--json "warnings"); `--write-baseline F` records the accepted ones and
`--baseline F` fails on any WARN id not in F, so a new warning cannot hide behind an old one.

Why: the PLM tracker (tools/plm.py) detects CHANGE, not DISAGREEMENT (docs/research/methodology.md). Two defects went through
review by hand: the mic's port hole 0.77 mm off the lid port (ECR-0011), and 315 mA of bridge peak on a 300 mA LDO (ECR-0005).
Each check below reads the two sides of one interface and compares them.

Checks
  mic-port     U2's acoustic hole (its drilled pad) lands inside the lid port, with the project's tolerance stack added to the
               nominal offset; the hole sits where the mic datasheet puts the port; U2 on B
  switch       SW1's actuator centre is within the plunger-bore clearance of the plunger axis, with the same stack; SW1 on F
  outline      board outline == the shell's PCB x/z extents (-0.05 / +0.00), >= 0.3 mm to the cavity, board thickness
  inside       every part (courtyard and pads; J and TP pads by their copper) lies inside the board outline
  clamp-bands  revg: no part (courtyard or pad, either face; J wire pads with their solder) within 0.6 mm of the long edges the
               lid ribs press; only TP probe pads are exempt. Phase 2 (no ribs: the board hangs from the lid on full-face VHB): every
               F-face part sits in a VHB cut-out (SW1 in the lid pocket, TP pads in the test-pad cut-out); WARN when the cut-outs
               leave less than VHB_MIN_BOND of the VHB outline bonded (ASSUMED threshold)
  heights      every part's maximum height fits the band of its face (tools/checks/part_heights.yaml, from datasheets): revg 1.2 / 1.2;
               Phase 2 B 1.4 (gap to the cell), F 0.30 (VHB gap), SW1 0.90 in the lid pocket
  board-nets   the board's pad-to-net wiring == the circuit's, for every pad of every part; same parts on both sides
  pins         every functional net on U1 sits on a pin that provides its signal (docs/system/pin-contract.yaml vs ST's data);
               the netlist's pin numbers match the package; hw/pod/pod.net (what the placer reads) matches the SKiDL circuit;
               every I/O net and power pin has a contract row (deleting rows is a FAIL); what a used pin does besides its job
               (dead-battery pull-down, reset pull-up, boot-ROM drive) warns citing ECR-0013
  rails        declared rail loads vs ratings (docs/system/rail-budget.yaml), resistive loads computed from the schematic's
               values; D11 (one switching regulator, the MCU's) enforced on the whole circuit; open overloads WARN, cite
               their ECR and stay under the waiver's ceiling
  frame        the mechanical constant files (frame.py, pod.py; imported, CAD-free) vs the live shell (dims_r2.py | shell_r1.py) on the shared facts (ECR-0001)
  selftest     each rule above must fire on a deliberately broken copy (and stay quiet on a harmless one: a board dragged to
               another KiCad origin, rails listed in another order, a loosely formatted ECR status)

Board <-> pod frame (checked 2026-10-02 against hw/mech/shell_r1.py and docs/system/physical.md "Coordinate frame"; Phase 2 uses
the same two mappings: dims_r2.bpt is pod z = PCB z0 + board y, its mirror pod z = PCB z1 - board y)
  The board file may sit anywhere in KiCad's sheet: every board coordinate is measured from the outline's min corner (the
  corner's file position is shown in the outline details), so a select-all drag or a new origin changes nothing.
  x     pod x = PCB["x0"] + board x. Board x 0 is the front (mic) edge, on both pods. The outline is (0, 0)-(34, 13).
  z     board y 0 is the TOP edge of the KiCad view. Left pod:  pod z = PCB["z1"] - board y  (physical.md: 4.4 - y).
        Right pod: pod z = PCB["z0"] + board y (the same board turned over about its long axis; physical.md: y - 8.6).
        shell_r1.py holds no mapping: its only z facts are the centre line (MIC, SWITCH at ZC = -2.1 = PCB z centre) and the
        symmetric clamp ribs. The two mappings agree only on the centre line, board y 6.5, so every position is evaluated under
        both and the worse is used. That also enforces "one board fits both pods" (O16-5): a feature off the centre line fails.
  y     the F face (lid side, outside) is pod y > PCB["y1"]; the B face (cell side) is pod y < PCB["y0"].
Tolerances: the outline check is a design-intent check, one-sided (the 0.3 mm cavity clearance cannot absorb oversize); the
fabricator's own outline tolerance is separate and is not read here. The lateral stack on the mic port and the switch (board
0.1 + lid 0.1) is the project's own figure from docs/build/tolerances.md (stated there for the plunger stack; applying it
sideways is an assumption, kept in STACK_MM).
Known open issues are WARN and cite their ECR (or the doc issue where no ECR exists yet: DOC_ISSUES); once the ECR is closed or
rejected they become FAIL. Waivers have ceilings, so a bigger overload than the one the ECR describes is a FAIL.
"""
from __future__ import annotations

import argparse
import ast
import contextlib
import copy
import dataclasses
import datetime as dt
import importlib.util
import json
import math
import os
import re
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

try:
    import yaml
except ImportError:                                                 # reported by ensure_env()
    yaml = None

REPO = Path(__file__).resolve().parents[2]
TODAY = dt.date.today()

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"
EPS = 1e-6
MIC_REF, SWITCH_REF = "U2", "SW1"
OUTLINE_UNDER = 0.05            # board may be this much SMALLER than the shell's PCB; oversize has no tolerance
CAVITY_CLEARANCE = 0.3          # board to cavity wall (physical.md Clearances: 0.3 front / top / bottom)
CLAMP_BAND = 0.6                # fallback: the shell's rib width (read from shell_r1.py when it can be)
STACK_MM = 0.10 + 0.10          # docs/build/tolerances.md, Housing table 'Plunger stem' row: board +-0.1, lid +-0.1
INSIDE_TOL = 0.001              # parts may not poke past the outline by more than a rounding error
NS = "{http://dummy.com}"       # ST's XML namespace
OPEN_ECR = ("proposed", "approved", "implemented")
POWER_PIN = re.compile(r"^(VDD\w*|VCC\w*|VIN\w*|VBAT|VBUS|VSYS|IN|SYS|BAT|OUT|VLX\w*)$")    # an IC pin that takes a supply
SWITCH_PIN = re.compile(r"^(SW|LX|VLX|PH)\w*$")                  # an IC pin that is a switching node
READ_ONCE = []                  # set once the circuit has been built in this process
VENV = Path(os.environ.get("ULTRA_VENV", "/opt/ultrasonic-tools/venv"))
NEEDED_MODULES = ("pcbnew", "skidl", "yaml")

# Known open issues that have no ECR yet (a doc issue only). Set "ecr" when one is opened and the issue then follows that ECR:
# WARN while it is open, FAIL once it is closed. "max_mm" (stack-up) is the worst case the issue describes; worse FAILs.
DOC_ISSUES = {
    "stackup": {"doc": "reg-board.md issue 2", "ecr": None, "max_mm": 1.6},
    "locating": {"doc": "reg-pod-body.md issue 2", "ecr": None},
}
VHB_MIN_BOND = 0.5              # Phase 2: fraction of the VHB outline that must stay bonded after the cut-outs (ASSUMED, no source)

sys.path.insert(0, str(REPO / "tools"))
try:                                                                # the ONE design pointer (hw/current.yaml)
    from current import apply_env, current
    DESIGN = apply_env(current())                                   # POD_PACKAGES for gen.py (system_map.build applies it)
except ImportError:                                                 # yaml missing before the venv re-exec (ensure_env)
    DESIGN = None


# ------------------------------------------------------------------------------------------- configuration
class Config:
    """Where every input lives. Defaults sit under `root`; each can be overridden (CLI: --root, --board, --contract, ...)."""
    DEFAULTS = dict(board=DESIGN.rel["board"] if DESIGN else "hw/current.yaml", netlist=DESIGN.rel["netlist"] if DESIGN else "hw/current.yaml",
                    shell=DESIGN.rel["shell_dims"] if DESIGN else "hw/current.yaml", mech="hw/mech",
                    heights="tools/checks/part_heights.yaml", contract="docs/system/pin-contract.yaml",
                    budget="docs/system/rail-budget.yaml", ecr_dir="docs/system/plm/ecr")

    def __init__(self, root=REPO, **over):
        self.root = Path(root).resolve()                            # absolute: the circuit build changes directory
        for key, rel in self.DEFAULTS.items():
            setattr(self, key, Path(over[key]).resolve() if over.get(key) else self.root / rel)


CFG = Config()


def use(cfg):
    global CFG
    CFG = cfg


# ------------------------------------------------------------------------------------------- plumbing
class Result:
    def __init__(self, cid, status, msg, details=(), wids=()):
        self.id, self.status, self.msg, self.details, self.wids = cid, status, msg, list(details), list(wids)

    def as_dict(self):
        return {"id": self.id, "status": self.status, "message": self.msg, "details": self.details, "warnings": self.wids}


class Findings:
    """Collects the PASS/WARN/FAIL lines of one check; the check's status is the worst of them.

    Every WARN carries a short phrase for the one-line headline (default: its first 70 characters), a `kind` (the headline
    counts kinds separately) and a stable id for the --baseline ratchet (`key`, default: the short phrase).
    """
    KINDS = {"hazard": "known hazard(s) on used pins", "warning": "warning(s)"}

    def __init__(self, cid):
        self.cid, self.status, self.lines, self.warns, self.fails = cid, PASS, [], [], []

    def add(self, level, text, short=None, key=None, kind="warning"):
        self.status = worst(self.status, level)
        self.lines.append(f"{level} {text}")
        if level == FAIL:
            self.fails.append(short or text)
        if level == WARN:
            short = short or (text if len(text) <= 70 else text[:67] + "...")
            self.warns.append(dict(wid=f"{self.cid}:{key or short}", short=short, kind=kind))

    def of(self, level):
        return [x[len(level) + 1:] for x in self.lines if x.startswith(level + " ")]

    def wids(self):
        return [w["wid"] for w in self.warns]

    def warn_headline(self, limit=6):
        """'3 known hazard(s) on used pins, 1 warning(s): short; short; ... (+k more, -v)': every WARN is counted and named."""
        kinds = Counter(w["kind"] for w in self.warns)
        counts = ", ".join(f"{n} {self.KINDS.get(k, k)}" for k, n in kinds.items())
        shorts = [w["short"] for w in self.warns]
        return f"{counts}: " + "; ".join(shorts[:limit]) + (f" (+{len(shorts) - limit} more, -v)" if len(shorts) > limit else "")

    def result(self, ok, noun, warn_lead=""):
        """The check's one-line Result: first FAIL, else every WARN, else `ok`."""
        if self.fails:
            return Result(self.cid, FAIL, f"{len(self.fails)} {noun} violation(s); first: {self.fails[0]}", self.lines, self.wids())
        if self.warns:
            return Result(self.cid, WARN, warn_lead + self.warn_headline(), self.lines, self.wids())
        return Result(self.cid, PASS, ok, self.lines)


def worst(*statuses):
    return FAIL if FAIL in statuses else WARN if WARN in statuses else PASS


STATUS_LINE = re.compile(r"^\s*status:\s*[*_`]*([a-z]+)", re.I | re.M)


def ecr_state(ecr, ecr_dir=None):
    """Lower-case status word of ECR-nnnn ('proposed', 'implemented', 'closed', ...), or None when the file or line is missing.

    Tolerates `Status: **Proposed.**`, `status: proposed (note)` and a backticked word. tools/plm.py and tools/checks/vcrm.py
    keep their own, stricter parsers and count `implemented` as closed: both should import this one.
    """
    f = Path(ecr_dir or CFG.ecr_dir) / f"{ecr}.md"
    m = STATUS_LINE.search(f.read_text()) if f.exists() else None
    return m[1].lower() if m else None


def ecr_open(ecr):
    return ecr_state(ecr) in OPEN_ECR


def known(ecr):
    """(status, tag) for a known open issue: WARN while its ECR is open, FAIL once it is closed or gone."""
    s = ecr_state(ecr)
    return (WARN, f"{ecr} {s}") if s in OPEN_ECR else (FAIL, f"{ecr} {s or 'missing'}")


def known_issue(key):
    """(status, tag) of a DOC_ISSUES entry: its ECR's state when it has one, else WARN citing the doc issue."""
    i = DOC_ISSUES[key]
    return known(i["ecr"]) if i["ecr"] else (WARN, f"{i['doc']}, no ECR yet")


@contextlib.contextmanager
def quiet_stderr():
    """KiCad's wx asserts spam stderr at import and load; silence them at the fd level."""
    sys.stderr.flush()
    saved, null = os.dup(2), os.open(os.devnull, os.O_WRONLY)
    try:
        os.dup2(null, 2)
        yield
    finally:
        os.dup2(saved, 2)
        os.close(saved)
        os.close(null)


def nat(ref):
    m = re.match(r"([A-Za-z]+)(\d+)$", ref)
    return (m[1], int(m[2])) if m else (ref, 0)


def refs_str(refs, limit=10):
    refs = sorted(refs, key=nat)
    return ",".join(refs[:limit]) + (f" (+{len(refs) - limit} more)" if len(refs) > limit else "")


def pins_str(pins, limit=4):
    pins = sorted(pins, key=lambda t: (nat(t[0]), t[1]))
    return ",".join(f"{r}.{n}" for r, n in pins[:limit]) + (f" (+{len(pins) - limit})" if len(pins) > limit else "") if pins else "nothing"


def ohms(value):
    """Resistance in ohms from a schematic value ('2k2', '100k', '1M', '33', '4R7', '0.1'); ValueError if it is not one."""
    s = str(value).strip().replace("Ω", "").replace(" ", "")
    mult = {"R": 1.0, "k": 1e3, "K": 1e3, "M": 1e6}
    if m := re.fullmatch(r"(\d+)([RkKM])(\d*)", s):
        return float(f"{m[1]}.{m[3] or 0}") * mult[m[2]]
    if m := re.fullmatch(r"(\d*\.?\d+)([RkKM]?)", s):
        return float(m[1]) * mult.get(m[2], 1.0)
    raise ValueError(f"cannot read {value!r} as a resistance")


def load_yaml(path):
    return yaml.safe_load(Path(path).read_text())


# ------------------------------------------------------------------------------------------- mechanical side (ast, never import)
def module_constants(path):
    """Module-level constants of a mechanical script, evaluated in order with no builtins but dict().

    Anything that is not plain numbers (HERE = Path(...), np.array(...)) is skipped, so nothing runs and no CAD kernel loads.
    Returns (constants, ast tree, source text).
    """
    src = Path(path).read_text()
    tree = ast.parse(src)
    env, safe = {}, {"__builtins__": {}, "dict": dict}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        try:
            val = eval(compile(ast.Expression(node.value), str(path), "eval"), safe, env)
        except Exception:
            continue
        tgt = node.targets[0]
        if isinstance(tgt, ast.Name):
            env[tgt.id] = val
        elif isinstance(tgt, ast.Tuple) and all(isinstance(t, ast.Name) for t in tgt.elts):
            env.update({t.id: v for t, v in zip(tgt.elts, val)})
    return env, tree, src


def cylinder_diameters(tree, env, func, anchor):
    """(assignment target, diameter, height) of every Cylinder(r, h) in the statements of `func` that mention constant `anchor`."""
    fn = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == func), None)
    out = []
    for stmt in (fn.body if fn else []):
        if anchor not in {n.id for n in ast.walk(stmt) if isinstance(n, ast.Name)}:
            continue
        tgt = stmt.targets[0].id if isinstance(stmt, ast.Assign) and isinstance(stmt.targets[0], ast.Name) else None
        for c in (n for n in ast.walk(stmt) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "Cylinder"):
            r, h = (eval(compile(ast.Expression(a), "shell_r1.py", "eval"), {"__builtins__": {}}, env) for a in c.args[:2])
            out.append((tgt, 2 * r, h))
    return out


def read_shell():
    """The shell facts the board interfaces rest on: a CAD-free dims module (Phase 2, hw/mech/dims_r2.py: interface_facts()) or
    shell_r1.py by ast (revg). Raises ValueError so a refactor of the shell fails loudly."""
    if CFG.shell.name != "shell_r1.py":
        return read_dims(CFG.shell)
    return read_shell_r1(CFG.shell)


def read_dims(path):
    """Phase 2: import the dims module by path (numpy only) and take its interface_facts()."""
    spec = importlib.util.spec_from_file_location(Path(path).stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not hasattr(mod, "interface_facts"):
        raise ValueError(f"{Path(path).name}: no interface_facts()")
    sh = mod.interface_facts()
    missing = [n for n in ("PCB", "CAV", "MIC", "SWITCH", "ZC", "mic_port_d", "switch_bore_d", "plunger_head_d", "bands", "pocket", "vhb") if n not in sh]
    if missing:
        raise ValueError(f"{Path(path).name}: interface_facts() lacks {', '.join(missing)}")
    do = mod.duct_offsets()
    sh.update(name=Path(path).name, design="phase2", env=dict(sh), clamp_band=None,
              cavity_clearance=do["tolerances"]["outline_to_hole"], cavity_clearance_src=f"{Path(path).name}:duct_offsets outline_to_hole (walls never fight the gauge pin)",
              locating=dict(method="stepped gauge pin through the reamed bore into the board hole while bonding", worst=do["worst_with_gauge_pin"],
                            limit=do["limit_R_ACO_P5"], ok=bool(do["worst_with_gauge_pin_pass"]), src=f"{Path(path).name}:duct_offsets ([A] tolerances)"))
    return sh


def read_shell_r1(path):
    env, tree, src = module_constants(path)
    missing = [n for n in ("PCB", "CAV", "PARTS", "MIC", "SWITCH", "ZC") if n not in env]
    if missing:
        raise ValueError(f"shell_r1.py: cannot read {', '.join(missing)}")
    mic = cylinder_diameters(tree, env, "lid_base", "MIC")
    bore = cylinder_diameters(tree, env, "lid_base", "SWITCH")
    head = [c for c in cylinder_diameters(tree, env, "plunger", "SWITCH") if c[0] == "head"]
    if not (mic and bore and head):
        raise ValueError("shell_r1.py: cannot find the mic port, plunger bore or plunger head Cylinder() calls")
    band = re.search(r'PCB\["z1"\]\s*-\s*([0-9.]+)', src)
    sh = {k: env[k] for k in ("PCB", "CAV", "PARTS", "MIC", "SWITCH", "ZC")}
    sh.update(name=Path(path).name, design="revg", cavity_clearance=CAVITY_CLEARANCE, cavity_clearance_src="physical.md Clearances", env=env, mic_port_d=max(mic, key=lambda c: c[2])[1], switch_bore_d=max(bore, key=lambda c: c[2])[1],
              plunger_head_d=head[0][1], clamp_band=float(band[1]) if band else CLAMP_BAND)
    sh["bands"] = face_bands(sh)
    return sh


def face_bands(sh):
    """Face -> part height band (mm), found by adjacency to the board's two surfaces (not by list order)."""
    pcb, bands = sh["PCB"], {}
    for p in sh["PARTS"]:
        if abs(p["y1"] - pcb["y0"]) < EPS:
            bands["B"] = p["y1"] - p["y0"]
        elif abs(p["y0"] - pcb["y1"]) < EPS:
            bands["F"] = p["y1"] - p["y0"]
    if set(bands) != {"F", "B"}:
        raise ValueError("shell_r1.py: PARTS bands do not touch the two faces of PCB")
    return bands


def pod_xz(sh, bx, by):
    """Board (x, y) in mm, from the outline corner -> pod (x, z) for each pod. See the frame in the module docstring."""
    pcb = sh["PCB"]
    x = pcb["x0"] + bx
    return {"left": (x, pcb["z1"] - by), "right": (x, pcb["z0"] + by)}


def worst_offset(sh, bx, by, target):
    """Distance in mm from a board point to a pod-frame target, under the pod mapping where it is worse; plus both."""
    off = {pod: math.hypot(x - target[0], z - target[1]) for pod, (x, z) in pod_xz(sh, bx, by).items()}
    return max(off.values()), off


def free_play(sh):
    """(x, z) mm the board can move in the cavity: front + rear clearance, top + bottom clearance (shell_r1.py PCB and CAV)."""
    pcb, cav = sh["PCB"], sh["CAV"]
    return (pcb["x0"] - cav["x0"]) + (cav["x1"] - pcb["x1"]), (cav["z1"] - pcb["z1"]) + (pcb["z0"] - cav["z0"])


# ------------------------------------------------------------------------------------------- board side (pcbnew)
@dataclasses.dataclass(frozen=True)
class Pad:
    num: str
    attr: str           # PTH SMD CONN NPTH
    x: float
    y: float
    drill: float
    w: float
    h: float
    box: tuple = ()     # (x0, y0, x1, y1) of the pad's copper or hole, rotation included
    net: str = ""       # net name on the board ('' = none)


@dataclasses.dataclass(frozen=True)
class Fp:
    ref: str
    name: str           # footprint item name, no library nickname
    face: str           # F or B
    x: float
    y: float
    pads: tuple
    courtyard: tuple    # (x0, y0, x1, y1) of the courtyard on the part's own face, or None
    copper_only: bool   # a pad with no body (TestPoint footprints)


@dataclasses.dataclass(frozen=True)
class Brd:
    outline: tuple      # (x0, y0, x1, y1) of the Edge.Cuts line centres, or None. Always (0, 0, w, h): see `origin`
    thickness: float
    fps: dict
    origin: tuple = (0.0, 0.0)      # where the outline's min corner sits in the file; all coordinates are relative to it


def import_pcbnew():
    with quiet_stderr():
        import pcbnew                                               # noqa: E402
    return pcbnew


def read_board(path):
    pcbnew = import_pcbnew()
    mm = pcbnew.ToMM
    with quiet_stderr():
        board = pcbnew.LoadBoard(str(path))
    if board is None:
        raise OSError("pcbnew could not load the file (truncated or being rewritten?)")
    xs, ys = [], []
    for d in board.GetDrawings():
        if d.GetLayer() == pcbnew.Edge_Cuts:
            bb, hw = d.GetBoundingBox(), d.GetWidth() / 2           # the box includes half the line width on every side
            xs += [mm(bb.GetLeft() + hw), mm(bb.GetRight() - hw)]
            ys += [mm(bb.GetTop() + hw), mm(bb.GetBottom() - hw)]
    attrs = {pcbnew.PAD_ATTRIB_PTH: "PTH", pcbnew.PAD_ATTRIB_SMD: "SMD", pcbnew.PAD_ATTRIB_CONN: "CONN", pcbnew.PAD_ATTRIB_NPTH: "NPTH"}
    fps, seen = {}, Counter()
    for f in board.GetFootprints():
        seen[f.GetReference()] += 1
        face = "B" if f.IsFlipped() else "F"
        poly = f.GetCourtyard(pcbnew.B_CrtYd if face == "B" else pcbnew.F_CrtYd)
        pts = [(mm(poly.CVertex(i).x), mm(poly.CVertex(i).y)) for i in range(poly.FullPointCount())] if poly.OutlineCount() else []
        name = str(f.GetFPID().GetLibItemName())
        pads = []
        for p in f.Pads():
            bb = p.GetBoundingBox()
            pads.append(Pad(p.GetNumber(), attrs.get(p.GetAttribute(), "?"), mm(p.GetX()), mm(p.GetY()), mm(p.GetDrillSizeX()), mm(p.GetSizeX()), mm(p.GetSizeY()),
                            (mm(bb.GetLeft()), mm(bb.GetTop()), mm(bb.GetRight()), mm(bb.GetBottom())), p.GetNetname()))
        crt = (min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)) if pts else None
        fps[f.GetReference()] = Fp(f.GetReference(), name, face, mm(f.GetX()), mm(f.GetY()), tuple(pads), crt, name.startswith("TestPoint"))
    dup = {r: n for r, n in seen.items() if n > 1}
    if dup:                                                         # a dict would keep the last one: the result would depend on file order
        raise OSError("duplicate reference " + ", ".join(f"{r} x{n}" for r, n in sorted(dup.items(), key=lambda kv: nat(kv[0]))))
    brd = Brd((min(xs), min(ys), max(xs), max(ys)) if xs else None, mm(board.GetDesignSettings().GetBoardThickness()), fps)
    return shift_board(brd, -brd.outline[0], -brd.outline[1], origin=brd.outline[:2]) if brd.outline else brd


def shift_fp(f, dx, dy):
    """A copy of a footprint translated by (dx, dy)."""
    box = lambda b: tuple(v + (dx, dy)[i % 2] for i, v in enumerate(b)) if b else b
    pads = tuple(dataclasses.replace(p, x=p.x + dx, y=p.y + dy, box=box(p.box)) for p in f.pads)
    return dataclasses.replace(f, x=f.x + dx, y=f.y + dy, pads=pads, courtyard=box(f.courtyard))


def shift_board(brd, dx, dy, origin=None):
    """A copy of the board with everything translated; the outline becomes (0, 0, w, h) when `origin` says it was normalised."""
    o = brd.outline
    return dataclasses.replace(brd, fps={r: shift_fp(f, dx, dy) for r, f in brd.fps.items()}, origin=origin or brd.origin,
                               outline=None if o is None else (o[0] + dx, o[1] + dy, o[2] + dx, o[3] + dy))


def moved(brd, ref, dx=0.0, dy=0.0):
    """A copy of the board model with one footprint translated (self-test only; no file is touched)."""
    return dataclasses.replace(brd, fps={**brd.fps, ref: shift_fp(brd.fps[ref], dx, dy)})


def is_test_pad(ref):
    return bool(re.match(r"TP\d", ref))


def is_wire_pad(f):
    return f.copper_only and bool(re.match(r"J\d", f.ref))


def extent(f, solder=0.0):
    """(x0, y0, x1, y1) of what a footprint physically occupies: courtyard and pads together. A copper-only pad has no body,
    so it is its pad boxes; a J wire pad grows by `solder` on every side (the hand-soldered blob the lid rib presses)."""
    boxes = [p.box for p in f.pads if p.box]
    if f.copper_only:
        g = solder if is_wire_pad(f) else 0.0
        boxes = [(b[0] - g, b[1] - g, b[2] + g, b[3] + g) for b in boxes]
    elif f.courtyard:
        boxes.append(f.courtyard)
    if not boxes:
        return (f.x, f.y, f.x, f.y)
    return (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))


# ------------------------------------------------------------------------------------------- schematic side (SKiDL)
@dataclasses.dataclass
class Sch:
    parts: dict         # ref -> {value, footprint, lcsc, dnp, pins: {num: (name, net or None)}}
    nets: dict          # net -> [(ref, pin num, pin name)]


def read_schematic():
    """The circuit from gen.py, built in a scratch directory (SKiDL writes its .erc/.log files to the cwd)."""
    pod = str(CFG.root / "hw/pod")
    for mod in ("system_map", "gen", "gen_sklib"):                  # a different --root must not reuse an earlier import
        loaded = sys.modules.get(mod)
        if loaded is not None and not str(getattr(loaded, "__file__", "")).startswith(pod):
            del sys.modules[mod]
    sys.path.insert(0, pod)
    cwd = os.getcwd()
    with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as tmp:
        os.chdir(tmp)
        try:
            import system_map                                       # noqa: E402
            if READ_ONCE:                                           # gen.build() adds to SKiDL's default circuit: a second read must start clean
                import builtins
                builtins.default_circuit.reset()
            READ_ONCE.append(True)
            circ = system_map.build()
        finally:
            os.chdir(cwd)
            sys.path.remove(pod)
    parts, nets = {}, defaultdict(list)
    for p in circ.parts:
        pins = {}
        for pin in p.pins:
            ns = [n.name for n in pin.nets if n.name and not n.name.startswith("__NOCONNECT")]
            pins[str(pin.num)] = (pin.name, ns[0] if ns else None)
            for n in ns:
                nets[n].append((p.ref, str(pin.num), pin.name))
        parts[p.ref] = dict(value=str(p.value), footprint=p.footprint or "", lcsc=p.fields.get("LCSC", ""), dnp=p.fields.get("DNP_BOM", ""), pins=pins)
    return Sch(parts, dict(nets))


def sexp(text):
    stack = [[]]
    for t in re.findall(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()"]+', text):
        if t == "(":
            stack.append([])
        elif t == ")":
            done = stack.pop()
            stack[-1].append(done)
        else:
            stack[-1].append(t[1:-1] if t[0] == '"' else t)
    return stack[0]


def netlist_connectivity(path):
    """{(ref, pin): frozenset of the other (ref, pin) on its net} from a KiCad netlist; names are ignored (unnamed nets differ)."""
    root = sexp(Path(path).read_text())[0]
    nets = next(x for x in root if isinstance(x, list) and x[:1] == ["nets"])
    conn = {}
    for net in nets[1:]:
        nodes = [(next(v[1] for v in n if v[0] == "ref"), next(v[1] for v in n if v[0] == "pin")) for n in net if isinstance(n, list) and n[:1] == ["node"]]
        for a in nodes:
            conn[a] = frozenset(nodes) - {a}
    return conn


def schematic_connectivity(sch):
    return {(r, n): frozenset((r2, n2) for r2, n2, _ in members) - {(r, n)} for members in sch.nets.values() for r, n, _ in members}


def board_connectivity(brd):
    """The same map from the board's pad nets: a pad is on the net its copper carries; pads of one net see each other."""
    by_net = defaultdict(set)
    for f in brd.fps.values():
        for p in f.pads:
            if p.net and p.num:
                by_net[p.net].add((f.ref, p.num))
    return {a: frozenset(members) - {a} for members in by_net.values() for a in members}


def load_table():
    t = load_yaml(CFG.heights)
    if not isinstance(t, dict) or not all(isinstance(v, dict) and isinstance(v.get("max_mm"), (int, float)) for sec in ("by_lcsc", "by_footprint")
                                         for v in (t.get(sec) or {}).values()):
        raise ValueError("part_heights.yaml: every by_lcsc / by_footprint row needs a numeric max_mm")
    return t


# ------------------------------------------------------------------------------------------- [mic-port]
def fit_stack(nominal, limit):
    """(status, short, long) of a lateral fit: the nominal offset plus the project's tolerance stack against the geometric limit.

    PASS needs nominal + stack <= limit; WARN when only the nominal fits (`long` says by how much the stack overshoots); FAIL when even the nominal does not.
    """
    worst_case = nominal + STACK_MM
    margin = limit - worst_case
    short = f"margin {margin:+.3f} mm at the worst-case stack ({nominal:.3f} + {STACK_MM:.2f} board 0.1 + lid 0.1, tolerances.md)" if margin < -EPS \
        else f"margin {max(margin, 0.0):.2f} mm at the worst-case stack ({nominal:.3f} + {STACK_MM:.2f})"
    if nominal > limit + EPS:
        return FAIL, short, f"{nominal:.2f} mm off (limit {limit:.2f})"
    if margin < -EPS:
        return WARN, short, f"worst-case stack exceeds the limit {limit:.2f} mm by {-margin:.3f} mm although the nominal {nominal:.3f} mm fits: tighten the fit or the tolerances"
    return PASS, short, ""


def locating_warning(sh):
    """The WARN every nominal alignment result carries while nothing locates the board in the cavity (DOC_ISSUES['locating']).
    Phase 2: the gauge pin locates board and VHB to the reamed bore; PASS while its worst residual fits the duct limit."""
    if sh.get("locating"):
        lo = sh["locating"]
        if lo["ok"]:
            return PASS, "", f"located by the {lo['method']}: worst {lo['worst']:.3f} mm <= {lo['limit']:.2f} ({lo['src']})"
        return WARN, "gauge pin", f"gauge pin locating residual {lo['worst']:.3f} mm exceeds the duct limit {lo['limit']:.2f} ({lo['src']})"
    px, pz = free_play(sh)
    level, tag = known_issue("locating")
    return level, tag, f"nominal only: nothing locates the board in the cavity (free play {px:.1f} mm in x, {pz:.1f} in z), known open issue {tag}"


def expected_port(u2, spec):
    """Where the datasheet puts the acoustic port, from the footprint's own pads: (x, y) in board mm, or None if pads are missing."""
    pads = {p.num: p for p in u2.pads if p.num}
    rows = [[pads.get(str(n)) for n in row] for row in spec["rows"]]
    if any(p is None for row in rows for p in row):
        return None
    c1, c2 = (tuple(sum(c) / len(row) for c in zip(*[(p.x, p.y) for p in row])) for row in rows)
    d = math.hypot(c2[0] - c1[0], c2[1] - c1[1])
    ux, uy = ((c2[0] - c1[0]) / d, (c2[1] - c1[1]) / d) if d > EPS else (1.0, 0.0)
    return c1[0] + spec["along_mm"] * ux - spec.get("across_mm", 0.0) * uy, c1[1] + spec["along_mm"] * uy + spec.get("across_mm", 0.0) * ux


def check_mic(sh, brd, table, sch):
    u2 = brd.fps.get(MIC_REF)
    if u2 is None:
        return Result("mic-port", FAIL, f"{MIC_REF} (the mic) is not on the board")
    holes = [p for p in u2.pads if p.attr == "NPTH" and p.drill > 0]
    if not holes:
        return Result("mic-port", FAIL, f"{MIC_REF} has no drilled port pad: the acoustic hole through the board is missing")
    hole = max(holes, key=lambda p: p.drill)
    lid, lid_d = sh["MIC"], sh["mic_port_d"]
    tol = (lid_d - hole.drill) / 2
    bad, off = worst_offset(sh, hole.x, hole.y, lid)
    origin = math.hypot(hole.x - u2.x, hole.y - u2.y)
    d = [f"board hole D{hole.drill:.2f} at board ({hole.x:.3f}, {hole.y:.3f}); {MIC_REF} origin at ({u2.x:.3f}, {u2.y:.3f}), {origin:.2f} mm from the port",
         f"lid port D{lid_d:.2f} at pod (x {lid[0]:.3f}, z {lid[1]:.3f}) = {sh.get('name', 'shell')} MIC; offset left pod {off['left']:.3f}, right pod {off['right']:.3f} mm"]
    fails, warns, wids = [], [], []
    if u2.face != "B":
        fails.append(f"{MIC_REF} is on {u2.face}: the mic must be on B (bottom port through the board, cell side)")
    if lid_d < hole.drill - EPS:
        fails.append(f"lid port D{lid_d:.1f} is smaller than the board hole D{hole.drill:.1f}: the lid is the restriction")
        status, short, long = FAIL, "", ""
    else:
        status, short, long = fit_stack(bad, tol)
        if status == FAIL:
            fails.append(f"port hole is {bad:.2f} mm off the lid port (limit {tol:.2f} = (D{lid_d:.1f} - D{hole.drill:.1f}) / 2): the holes no longer overlap fully")
        elif status == WARN:
            warns.append(long)
            wids.append("mic-port:stack")
    spec = ((table.get("by_lcsc") or {}).get(sch.parts.get(MIC_REF, {}).get("lcsc")) or {}).get("port")
    ap_txt = ""
    if spec is None:
        warns.append(f"no datasheet port position for {MIC_REF} in part_heights.yaml: the hole is checked against the lid only")
        wids.append("mic-port:no-port-data")
    elif (exp := expected_port(u2, spec)) is None:
        fails.append(f"{MIC_REF} lacks pads {spec['rows']} that locate the datasheet port: footprint no longer matches the datasheet pattern")
    else:
        ap_off = math.hypot(hole.x - exp[0], hole.y - exp[1])
        slack = (hole.drill - (spec["d_mm"] + spec["d_tol_mm"])) / 2
        d.append(f"datasheet port at board ({exp[0]:.3f}, {exp[1]:.3f}) from the footprint's own pads; hole is {ap_off:.3f} mm from it; D{hole.drill:.2f} hole leaves "
                 f"{slack:.4f} mm radial slack round the port's D{spec['d_mm'] + spec['d_tol_mm']:.3f} maximum; {spec['note']} ({spec['source']})")
        if slack < -EPS:
            fails.append(f"board hole D{hole.drill:.2f} is smaller than the mic's port D{spec['d_mm'] + spec['d_tol_mm']:.3f} maximum")
        elif ap_off > slack + EPS:
            fails.append(f"board hole is {ap_off:.3f} mm from the datasheet port position (slack {slack:.3f} mm): the hole no longer clears the mic's own port")
        ap_txt = f"; {ap_off:.3f} mm from the datasheet port (slack {slack:.3f})"
    if fails:
        return Result("mic-port", FAIL, "; ".join(fails), d)
    level, tag, text = locating_warning(sh)
    if level != PASS:
        warns.append(text)
        wids.append("mic-port:locating")
    else:
        d.append(text)
    x, z = pod_xz(sh, hole.x, hole.y)["left"]
    msg = (f"{MIC_REF} on B, port hole D{hole.drill:.1f} at pod ({x:.2f}, {z:.2f}) is {bad:.3f} mm from the lid port D{lid_d:.1f} (limit {tol:.2f}); "
           f"{short}{ap_txt}; the footprint origin is {origin:.2f} mm away, so the PORT is what is placed (ECR-0011)")
    if warns:
        return Result("mic-port", WARN, msg + "; " + "; ".join(warns), d, wids)
    return Result("mic-port", PASS, msg, d)


# ------------------------------------------------------------------------------------------- [switch]
def check_switch(sh, brd):
    sw = brd.fps.get(SWITCH_REF)
    if sw is None:
        return Result("switch", FAIL, f"{SWITCH_REF} (the button) is not on the board")
    # KMT0 drawing (C&K datasheet p.B-10, 21 Mar 2018): the actuator is the circle at the centre of the body and the four pads
    # are symmetric about it, so the actuator sits at the centre of the pad bounding box.
    boxes = [p.box for p in sw.pads if p.box]
    if not boxes:
        return Result("switch", FAIL, f"{SWITCH_REF} has no pads: cannot locate the actuator")
    cx, cy = (min(b[0] for b in boxes) + max(b[2] for b in boxes)) / 2, (min(b[1] for b in boxes) + max(b[3] for b in boxes)) / 2
    tol = (sh["switch_bore_d"] - sh["plunger_head_d"]) / 2
    bad, off = worst_offset(sh, cx, cy, sh["SWITCH"])
    origin = math.hypot(cx - sw.x, cy - sw.y)
    d = [f"actuator centre (pad bbox centre) board ({cx:.3f}, {cy:.3f}); footprint origin ({sw.x:.3f}, {sw.y:.3f}), {origin:.3f} mm apart",
         f"plunger axis pod (x {sh['SWITCH'][0]:.3f}, z {sh['SWITCH'][1]:.3f}) = {sh.get('name', 'shell')} SWITCH; offset left pod {off['left']:.3f}, right pod {off['right']:.3f} mm; "
         f"limit {tol:.2f} = (bore D{sh['switch_bore_d']:.1f} - plunger head D{sh['plunger_head_d']:.1f}) / 2"]
    fails, warns, wids = [], [], []
    if sw.face != "F":
        fails.append(f"{SWITCH_REF} is on {sw.face}: the button must be on F, under the lid plunger")
    status, short, long = fit_stack(bad, tol)
    if status == FAIL:
        fails.append(f"actuator is {bad:.2f} mm off the plunger axis (limit {tol:.2f})")
    elif status == WARN:
        warns.append(long)
        wids.append("switch:stack")
    if fails:
        return Result("switch", FAIL, "; ".join(fails), d)
    if origin > 0.05:
        warns.append(f"the footprint origin is {origin:.2f} mm off the pad-box centre: check the footprint against the KMT0 drawing")
        wids.append("switch:origin")
    level, tag, text = locating_warning(sh)
    if level != PASS:
        warns.append(text)
        wids.append("switch:locating")
    x, z = pod_xz(sh, cx, cy)["left"]
    msg = f"{SWITCH_REF} on F, actuator at pod ({x:.2f}, {z:.2f}) is {bad:.3f} mm from the plunger axis (limit {tol:.2f}); {short}"
    return Result("switch", WARN, msg + "; " + "; ".join(warns), d, wids) if warns else Result("switch", PASS, msg, d)


# ------------------------------------------------------------------------------------------- [outline]
def check_outline(sh, brd):
    if brd.outline is None:
        return Result("outline", FAIL, "no Edge.Cuts outline on the board")
    pcb, cav = sh["PCB"], sh["CAV"]
    ox0, oy0, ox1, oy1 = brd.outline
    w, h = ox1 - ox0, oy1 - oy0
    exp_w, exp_h = pcb["x1"] - pcb["x0"], pcb["z1"] - pcb["z0"]
    msgs = []
    for what, got, want in (("wide", w, exp_w), ("tall", h, exp_h)):
        if got > want + EPS:
            msgs.append(f"outline is {got:.2f} mm {what}, {got - want:.2f} mm over the shell's PCB {want:.2f}: oversize has no tolerance, the {sh['cavity_clearance']} mm cavity clearance cannot absorb it")
        elif got < want - OUTLINE_UNDER - EPS:
            msgs.append(f"outline is {got:.2f} mm {what}, {sh.get('name', 'shell')} PCB is {want:.2f} (undersize allowed {OUTLINE_UNDER} mm)")
    z_all = [z for by in (oy0, oy1) for _, z in pod_xz(sh, 0, by).values()]            # both pods, both long edges
    clear = {"front": pcb["x0"] + ox0 - cav["x0"], "rear": cav["x1"] - (pcb["x0"] + ox1), "top": cav["z1"] - max(z_all), "bottom": min(z_all) - cav["z0"]}
    lim = sh["cavity_clearance"]
    d = [f"clearance to the cavity (pod, {sh.get('name', 'shell')} CAV): " + ", ".join(f"{k} {v:.2f}" for k, v in clear.items())
         + f" mm (limit {lim}: {sh['cavity_clearance_src']}; the rear is the wire gap)"]
    if abs(brd.origin[0]) > EPS or abs(brd.origin[1]) > EPS:
        d.append(f"the outline's corner sits at ({brd.origin[0]:.2f}, {brd.origin[1]:.2f}) in the file; every check measures from it")
    tight = [f"{k} {v:.2f}" for k, v in clear.items() if v < lim - EPS]
    if tight:
        msgs.append(f"board is closer than {lim} mm to the cavity wall: {', '.join(tight)}")
    want = pcb["y1"] - pcb["y0"]
    stack_i = DOC_ISSUES["stackup"]
    thick_bad = brd.thickness < want - 0.01 or brd.thickness > stack_i["max_mm"] + 0.01
    if thick_bad:
        msgs.append(f"board file is {brd.thickness:.2f} mm thick, the shell and the mic port need {want:.2f} mm and the known issue covers up to {stack_i['max_mm']:.2f} mm")
    if msgs:
        return Result("outline", FAIL, "; ".join(msgs), d)
    base = f"outline {w:.2f} x {h:.2f} mm = shell PCB (-{OUTLINE_UNDER} / +0.00), min clearance to the cavity {min(clear.values()):.2f} mm"
    if abs(brd.thickness - want) > 0.01:
        level, tag = known_issue("stackup")
        d.append(f"board file thickness {brd.thickness:.2f} mm, {sh.get('name', 'shell')} PCB y {pcb['y0']}-{pcb['y1']} = {want:.2f} mm")
        return Result("outline", level, f"{base}; but the board file says {brd.thickness:.2f} mm thick and the shell and the mic port need {want:.2f} "
                      f"({brd.thickness / want:.1f}x): known open issue {tag}; set the stack-up before release", d, [f"outline:thickness {tag}"])
    return Result("outline", PASS, f"{base}, {brd.thickness:.2f} mm thick", d)


# ------------------------------------------------------------------------------------------- [inside]
def solder_margin(table):
    return float(table.get("solder_margin_mm", 0.25))


def check_inside(sh, brd, table):
    if brd.outline is None:
        return Result("inside", FAIL, "no Edge.Cuts outline to measure from")
    if not brd.fps:
        return Result("inside", FAIL, "the board has no footprints")
    x0, y0, x1, y1 = brd.outline
    out, closest = [], None
    for f in brd.fps.values():
        e = extent(f, solder_margin(table))
        over = {"front": x0 - e[0], "top": y0 - e[1], "rear": e[2] - x1, "bottom": e[3] - y1}
        margin = -max(over.values())
        if closest is None or margin < closest[1]:
            closest = (f.ref, margin)
        if margin < -INSIDE_TOL:
            side, v = max(over.items(), key=lambda kv: kv[1])
            out.append((f.ref, f"{f.ref} ({f.face}) is {v:.2f} mm past the {side} edge (extent {e[0]:.2f},{e[1]:.2f} to {e[2]:.2f},{e[3]:.2f}; outline {x0:.2f},{y0:.2f} to {x1:.2f},{y1:.2f})"))
    if out:
        return Result("inside", FAIL, f"{len(out)} part(s) outside the board outline: {refs_str([o[0] for o in out])}; first: {out[0][1]}", [o[1] for o in out])
    return Result("inside", PASS, f"all {len(brd.fps)} parts (courtyards and pads) lie inside the {x1 - x0:.2f} x {y1 - y0:.2f} mm outline; closest to an edge is {closest[0]} at {closest[1]:.2f} mm")


# ------------------------------------------------------------------------------------------- [clamp-bands]
def vhb_cutouts(sh):
    """Phase 2 VHB cut-outs in board mm (x0, y0, x1, y1, what), as dims_r2/shell_r2 vhb() cuts them: SW1 pocket, one box round
    each bare F pad (one square per pad, 2026-10-07), and the duct hole (as its bounding square, for area only)."""
    pcb, v, pk = sh["PCB"], sh["vhb"], sh["pocket"]
    bx, by = pk["centre"][0] - pcb["x0"], pk["centre"][1] - pcb["z0"]
    cuts = [(bx - pk["dx"] / 2, by - pk["dz"] / 2, bx + pk["dx"] / 2, by + pk["dz"] / 2, f"{pk['ref']} pocket")]
    if v["f_pads"]:
        r = v["tp_cut_r"]
        for ref in sorted(v["f_pads"], key=nat):
            x, y = v["f_pads"][ref]
            cuts.append((x - r, y - r, x + r, y + r, f"{ref} cut-out"))
    mx, mz = sh["MIC"][0] - pcb["x0"], sh["MIC"][1] - pcb["z0"]
    cuts.append((mx - v["duct_d"] / 2, mz - v["duct_d"] / 2, mx + v["duct_d"] / 2, mz + v["duct_d"] / 2, "duct hole"))
    return cuts


def bonded_fraction(sh, cuts, pitch=0.05):
    """Fraction of the VHB outline (board inset by vhb.inset) left after the cut-outs, by a 0.05 mm raster (union of boxes)."""
    pcb, ins = sh["PCB"], sh["vhb"]["inset"]
    w, h = pcb["x1"] - pcb["x0"] - 2 * ins, pcb["z1"] - pcb["z0"] - 2 * ins
    nx, ny = int(round(w / pitch)), int(round(h / pitch))
    kept = 0
    for i in range(nx):
        x = ins + (i + 0.5) * pitch
        col = [c for c in cuts if c[0] <= x <= c[2]]
        for j in range(ny):
            y = ins + (j + 0.5) * pitch
            kept += not any(c[1] <= y <= c[3] for c in col)
    return kept / (nx * ny)


def check_vhb(sh, brd, table):
    """Phase 2 replacement of the clamp bands: nothing presses the long edges; the board hangs on full-face VHB, so every F part
    must sit in a VHB cut-out, and the cut-outs must leave enough tape bonded."""
    if brd.outline is None:
        return Result("clamp-bands", FAIL, "no Edge.Cuts outline to measure the VHB face from")
    if not brd.fps:
        return Result("clamp-bands", FAIL, "the board has no footprints")
    cuts = vhb_cutouts(sh)
    inside = lambda e, c: e[0] >= c[0] - EPS and e[1] >= c[1] - EPS and e[2] <= c[2] + EPS and e[3] <= c[3] + EPS  # noqa: E731
    bad, ok_ = [], []
    for f in sorted(brd.fps.values(), key=lambda f: nat(f.ref)):
        if f.face != "F":
            continue
        e = extent(f, solder_margin(table))
        allowed = cuts[:1] if f.ref == sh["pocket"]["ref"] else cuts[:-1]     # the switch body needs its pocket, pads any cut-out
        hit = next((c for c in allowed if inside(e, c)), None)
        if hit is None and f.ref == sh["pocket"]["ref"]:
            bad.append((f.ref, f"{f.ref} (F) extent {e[0]:.2f},{e[1]:.2f} to {e[2]:.2f},{e[3]:.2f} is not inside its lid pocket {cuts[0][0]:.2f},{cuts[0][1]:.2f} to {cuts[0][2]:.2f},{cuts[0][3]:.2f}"))
        elif hit is None:
            bad.append((f.ref, f"{f.ref} (F) extent {e[0]:.2f},{e[1]:.2f} to {e[2]:.2f},{e[3]:.2f} lies under the VHB (no cut-out holds it)"))
        else:
            ok_.append(f"{f.ref} in the {hit[4]}")
    frac = bonded_fraction(sh, cuts)
    d = [b[1] for b in bad] + ok_ + [f"cut-out {c[4]}: board x {c[0]:.2f}-{c[2]:.2f}, y {c[1]:.2f}-{c[3]:.2f}" for c in cuts] + \
        [f"VHB bonded after the cut-outs: {100 * frac:.0f} % of the {sh['vhb']['t']} mm tape outline (threshold {100 * VHB_MIN_BOND:.0f} %, ASSUMED)"]
    nf = sum(f.face == "F" for f in brd.fps.values())
    if bad:
        return Result("clamp-bands", FAIL, f"{len(bad)} F-face part(s) under the full-face VHB, outside every cut-out: {refs_str([b[0] for b in bad])}", d)
    head = f"Phase 2 (no clamp ribs; board on full-face VHB): all {nf} F-face parts sit in VHB cut-outs; {100 * frac:.0f} % of the VHB stays bonded"
    if frac < VHB_MIN_BOND:
        return Result("clamp-bands", WARN, head + f" (< {100 * VHB_MIN_BOND:.0f} % ASSUMED threshold: "
                      f"{len(cuts)} cut-outs; shrink or regroup them)", d, ["clamp-bands:vhb-bond"])
    return Result("clamp-bands", PASS, head, d)


def check_clamp(sh, brd, table):
    if sh.get("vhb"):
        return check_vhb(sh, brd, table)
    band = sh["clamp_band"]
    if brd.outline is None:
        return Result("clamp-bands", FAIL, "no Edge.Cuts outline to measure the bands from")
    if not brd.fps:
        return Result("clamp-bands", FAIL, "the board has no footprints")
    y0, y1 = brd.outline[1], brd.outline[3]
    bad, closest, exempt, nocrt = [], None, [], []
    for f in brd.fps.values():
        if is_test_pad(f.ref):
            exempt.append(f.ref)
            continue
        if f.courtyard is None and not f.copper_only:
            nocrt.append(f.ref)
        e = extent(f, solder_margin(table))
        gap = min(e[1] - y0, y1 - e[3])                             # courtyard or pad, whichever reaches further, to the nearer long edge
        if closest is None or gap < closest[1]:
            closest = (f.ref, gap, f.face)
        if gap < band - EPS:
            bad.append((f.ref, f"{f.ref} ({f.face}) {'pad and solder' if is_wire_pad(f) else 'body'} is {gap:.2f} mm from the edge"))
    d = [b[1] for b in bad] + ([f"no courtyard, measured from its pads only: {refs_str(nocrt)}"] if nocrt else [])
    if bad:
        return Result("clamp-bands", FAIL, f"{len(bad)} part(s) inside the {band} mm clamp bands the lid ribs and foam press: {refs_str([b[0] for b in bad])}", d)
    n = len(brd.fps) - len(exempt)
    where = f"closest is {closest[0]} ({closest[2]}) at {closest[1]:.2f} mm" if closest else "no parts"
    if nocrt:
        return Result("clamp-bands", WARN, f"{n} parts on both faces clear of the {band} mm bands ({where}); {len(nocrt)} without a courtyard measured from their pads only",
                      d, ["clamp-bands:no-courtyard"])
    return Result("clamp-bands", PASS, f"{n} parts (courtyards, pads and J solder) on both faces clear of the {band} mm bands ({where}); {len(exempt)} TP probe pads exempt", d)


# ------------------------------------------------------------------------------------------- [heights]
def part_height(f, sch, table):
    """(max height mm, what it came from) for a board footprint: schematic LCSC number first, then footprint name; None if unknown."""
    lcsc = sch.parts.get(f.ref, {}).get("lcsc")
    if lcsc in (table.get("by_lcsc") or {}):
        return table["by_lcsc"][lcsc]["max_mm"], f"{lcsc} {table['by_lcsc'][lcsc].get('part', '')}"
    if f.name in (table.get("by_footprint") or {}):
        return table["by_footprint"][f.name]["max_mm"], f"footprint {f.name}"
    return None, None


def band_of(sh, f):
    """Height band (mm) of a footprint: its face's band, or the lid pocket's when the part's footprint body lies inside the pocket
    outline (Phase 2 SW1; position-based, so a switch moved out of its pocket meets the 0.30 mm F gap)."""
    pk = sh.get("pocket")
    if pk and f.face == "F" and f.courtyard:
        c = vhb_cutouts(sh)[0]
        e = f.courtyard
        if e[0] >= c[0] - EPS and e[1] >= c[1] - EPS and e[2] <= c[2] + EPS and e[3] <= c[3] + EPS:
            return pk["band"]
    return sh["bands"][f.face]


def check_heights(sh, brd, sch, table):
    if not brd.fps:
        return Result("heights", FAIL, "the board has no footprints")
    tall, over, unknown = {}, [], []
    for f in brd.fps.values():
        h, src = part_height(f, sch, table)
        if h is None:
            unknown.append((f.ref, f"unknown height: {f.ref} ({f.name}, LCSC {sch.parts.get(f.ref, {}).get('lcsc') or 'none'})"))
            continue
        band = band_of(sh, f)
        if h > band + EPS:
            over.append((f.ref, f"{f.ref} ({f.face}) is {h:.2f} mm tall, band {band:.2f} mm ({src})"))
        if f.face not in tall or band - h < tall[f.face][2]:
            tall[f.face] = (f.ref, h, band - h, band)
    summ = "; ".join(f"{face} tightest {tall[face][0]} {tall[face][1]:.2f} mm (band {tall[face][3]:.2f}, margin {tall[face][2]:.2f})"
                     for face in ("F", "B") if face in tall) or "no part with a known height"
    d = [o[1] for o in over] + [u[1] for u in unknown]
    if over:
        return Result("heights", FAIL, f"{len(over)} part(s) taller than the band of their face: {refs_str([o[0] for o in over])}; {summ}", d)
    if unknown:
        return Result("heights", WARN, f"{len(unknown)} part(s) with no height in part_heights.yaml ({refs_str([u[0] for u in unknown])}); the rest fit: {summ}", d,
                      [f"heights:unknown {u[0]}" for u in unknown])
    return Result("heights", PASS, f"all {len(brd.fps)} parts fit their face's height band: {summ}")


# ------------------------------------------------------------------------------------------- [board-nets]
def check_board_nets(brd, sch):
    """The fabricated artefact against the circuit: the same parts, and every pad on the net the circuit says."""
    missing, extra = sorted(set(sch.parts) - set(brd.fps), key=nat), sorted(set(brd.fps) - set(sch.parts), key=nat)
    d, bad = [], []
    if missing:
        d.append(f"circuit parts not on the board: {refs_str(missing, 30)}")
    if extra:
        d.append(f"board footprints not in the circuit: {refs_str(extra, 30)}")
    common = set(sch.parts) & set(brd.fps)
    want, got = schematic_connectivity(sch), board_connectivity(brd)
    names = {(r, n): net for net, members in sch.nets.items() for r, n, _ in members}
    for key in sorted({k for k in set(want) | set(got) if k[0] in common}, key=lambda k: (nat(k[0]), k[1])):
        w = frozenset(m for m in want.get(key, ()) if m[0] in common)
        g = frozenset(m for m in got.get(key, ()) if m[0] in common)
        if w != g:
            bad.append(f"board {key[0]} pad {key[1]} is on the net of {pins_str(g)}, circuit says {pins_str(w)} (net {names.get(key, 'none')})")
    if missing or extra or bad:
        parts = ([f"board has {len(common)} of {len(sch.parts)} circuit parts (missing {refs_str(missing)})"] if missing else []) \
            + ([f"{len(extra)} board footprint(s) not in the circuit ({refs_str(extra)})"] if extra else []) \
            + ([f"{len(bad)} pad(s) wired differently from the circuit; first: " + bad[0]] if bad else [])
        return Result("board-nets", FAIL, "; ".join(parts), d + bad)
    n = sum(1 for f in brd.fps.values() for p in f.pads if p.num)
    return Result("board-nets", PASS, f"all {len(brd.fps)} board parts are in the circuit and all {n} numbered pads sit on the circuit's nets (checked against the pad's net name)")


# ------------------------------------------------------------------------------------------- [pins]
@dataclasses.dataclass
class PinData:
    pins: dict          # position -> {name, port, type, signals, modes}
    af: dict            # port -> signal -> set of AF numbers


def port_token(name):
    m = re.match(r"P[A-K]\d+", name)
    return m[0] if m else name


def validate_contract(c):
    """Problems that make the contract itself unusable, each naming its row. An empty contract must not read as 'nothing to check'."""
    if not isinstance(c, dict):
        return ["pin-contract.yaml is not a mapping"]
    bad = [f"missing top-level key `{k}`" for k in ("mcu", "power_pins", "signals", "hazards", "hazards_tracked_by") if k not in c]
    mcu = c.get("mcu") or {}
    bad += [f"mcu: missing `{k}`" for k in ("ref", "package", "mcu_xml", "gpio_xml", "exposed_pad") if k not in mcu]
    if not c.get("signals"):
        bad.append("`signals` is empty: a contract with no rows checks nothing")
    if not c.get("power_pins"):
        bad.append("`power_pins` is empty: every power pin would pass unchecked")
    for i, e in enumerate(c.get("signals") or []):
        what = e.get("id", f"row {i + 1}") if isinstance(e, dict) else f"row {i + 1}"
        if not isinstance(e, dict) or "signal" not in e or "id" not in e or ("net" not in e and "via" not in e):
            bad.append(f"signals {what}: needs id, signal and net (or via)")
    return bad


def read_pin_data(contract):
    pins = {}
    for p in ET.parse(CFG.root / contract["mcu"]["mcu_xml"]).getroot().findall(f"{NS}Pin"):
        sigs = p.findall(f"{NS}Signal")
        pins[int(p.get("Position"))] = dict(name=p.get("Name"), port=port_token(p.get("Name")), type=p.get("Type"), signals={s.get("Name") for s in sigs},
                                            modes={m for s in sigs if s.get("Name") == "GPIO" for m in (s.get("IOModes") or "").split(",")})
    af = {}
    for g in ET.parse(CFG.root / contract["mcu"]["gpio_xml"]).getroot().findall(f"{NS}GPIO_Pin"):
        sig = af.setdefault(port_token(g.get("Name")), {})
        for s in g.findall(f"{NS}PinSignal"):
            nums = {int(m[1]) for v in s.iter(f"{NS}PossibleValue") if (m := re.match(r"GPIO_AF(\d+)_", v.text or ""))}
            sig.setdefault(s.get("Name"), set()).update(nums)
    if not pins:
        raise ValueError(f"{contract['mcu']['mcu_xml']}: no <Pin> elements")
    return PinData(pins, af)


def provides(spec, pin):
    """The ST signals on `pin` that satisfy `spec` (as written in docs/system/pin-contract.yaml); empty if none."""
    if spec == "GPIO":
        return ["GPIO"] if "GPIO" in pin["signals"] else []
    if spec == "NRST":
        return ["NRST"] if pin["type"] == "Reset" else []
    if spec == "BOOT0":
        return ["BOOT0"] if "BOOT0" in pin["name"] else []
    if spec.startswith("re:"):
        return sorted(s for s in pin["signals"] if re.fullmatch(spec[3:], s))
    return [spec] if spec in pin["signals"] else []


def resolve_net(entry, sch):
    """(net name, None, False) or (None, reason, gone) for a contract entry, following `via` through the named part.

    `gone` is True when the part or net no longer exists (what an ECR that removes it does), False when it exists but is wired differently.
    """
    if "net" in entry:
        return (entry["net"], None, False) if entry["net"] in sch.nets else (None, f"net {entry['net']} is not in the schematic", True)
    via = entry["via"]
    part = sch.parts.get(via["ref"])
    if part is None:
        return None, f"{via['ref']} is not in the schematic", True
    nets = {n for _, n in part["pins"].values() if n}
    if via["from_net"] not in nets:
        return None, f"{via['ref']} is not on net {via['from_net']}", False
    others = nets - {via["from_net"]}
    return (next(iter(others)), None, False) if len(others) == 1 else (None, f"{via['ref']} has {len(others)} other nets, expected 1", False)


def package_findings(F, contract, data, names, nets):
    """The netlist symbol's pin numbers and power pins against the package pinout."""
    for pos, p in sorted(data.pins.items()):
        have = names.get(str(pos), "")
        if port_token(have) != p["port"] and have != p["name"]:
            F.add(FAIL, f"pin {pos} is {have!r} in the symbol, ST has {p['port']}")
    ep = contract["mcu"]["exposed_pad"]
    if nets.get(str(ep["pin"])) != ep["net"]:
        F.add(FAIL, f"exposed pad (pin {ep['pin']}) is on {nets.get(str(ep['pin']))}, must be on {ep['net']} ({ep['source']})")
    for pos, p in sorted(data.pins.items()):
        if p["type"] != "Power":
            continue
        want, have = contract["power_pins"].get(p["name"]), nets.get(str(pos))
        if want is None:
            F.add(FAIL, f"power pin {pos} {p['name']} has no rail in the contract: add it under power_pins")
        elif have != want:
            F.add(FAIL, f"power pin {pos} {p['name']} is on {have}, must be on {want}")


def entry_signal(F, e, pin, pos, net, data):
    """The signal of `e` that `pin` provides (primary or an alternate), or None after adding the finding."""
    options = [(e["signal"], e.get("af"), None)] + [(a["signal"], a.get("af"), a["ecr"]) for a in e.get("alternates", [])]
    for spec, af, ecr in options:
        got = provides(spec, pin)
        if not got:
            continue
        if "modes" in e and not set(e["modes"]) <= pin["modes"]:
            F.add(FAIL, f"{e['id']}: pin {pos} {pin['port']} is a GPIO but ST lists modes {sorted(pin['modes'])}, need {e['modes']}")
            return None
        have_af = data.af.get(pin["port"], {}).get(got[0], set())
        if af is not None and af not in have_af:
            F.add(FAIL, f"{e['id']}: {pin['port']} {got[0]} is AF{sorted(have_af) or 'none'} in ST's table, the contract says AF{af}")
            return None
        if ecr:
            level, tag = known(ecr)
            F.add(level, f"{e['id']}: net {net} is on {pin['port']} providing {got[0]}, the contract's alternate for {tag}: update the contract when that ECR lands",
                  f"{e['id']} on {pin['port']} is the {ecr} alternate [{tag}]", key=f"alternate {e['id']} {ecr}")
        return got[0]
    F.add(FAIL, f"{e['id']}: net {net} is on pin {pos} {pin['port']}, which cannot provide {e['signal']} "
                f"(ST lists {sorted(s for s in pin['signals'] if s != 'GPIO') or 'GPIO only'})")
    return None


def entry_findings(F, contract, sch, data, nets):
    """Every contract entry against the pin its net sits on. Returns {entry id: signal}, {pin: [entry ids]}, {entry id: (port, net)}."""
    chosen, taken, placed = {}, defaultdict(list), {}
    for e in contract["signals"]:
        net, why, gone = resolve_net(e, sch)
        if net is None:
            ecr = e.get("absent_ecr")
            if gone and ecr and ecr_open(ecr):                      # only the part's or net's removal is waived, never a wrong connection
                F.add(WARN, f"{e['id']}: {why}; contract entry kept while {ecr} ({ecr_state(ecr)}) removes it",
                      f"{e['id']}: {why} [{ecr} {ecr_state(ecr)}]", key=f"absent {e['id']} {ecr}")
            else:
                F.add(FAIL, f"{e['id']}: {why}")
            continue
        pos = [num for num, n in nets.items() if n == net]
        if len(pos) != 1:
            F.add(FAIL, f"{e['id']}: net {net} is on {len(pos)} pins of {contract['mcu']['ref']}, expected exactly 1")
            continue
        taken[pos[0]].append(e["id"])
        pin = data.pins.get(int(pos[0]))
        if pin is None:
            F.add(FAIL, f"{e['id']}: pin {pos[0]} does not exist on the {contract['mcu']['package']} package")
            continue
        placed[e["id"]] = (pin["port"], net)
        if sig := entry_signal(F, e, pin, pos[0], net, data):
            chosen[e["id"]] = sig
    return chosen, taken, placed


def pair_findings(F, contract, chosen):
    """Complementary PWM: the N output must be CHxN of the same timer and channel as its P partner."""
    for e in contract["signals"]:
        mate = e.get("complement_of")
        if not mate or e["id"] not in chosen or mate not in chosen:
            continue
        a, b = (re.fullmatch(r"(TIM\d+)_CH(\d)(N?)", chosen[k]) for k in (mate, e["id"]))
        if not (a and b and a[1] == b[1] and a[2] == b[2] and not a[3] and b[3]):
            F.add(FAIL, f"{e['id']} ({chosen[e['id']]}) is not the complementary output of {mate} ({chosen[mate]}): dead-time PWM needs CHx / CHxN of one timer")


def hazard_findings(F, contract, data, nets, placed):
    """What a used pin does besides its job (reset pulls, dead-battery pull-downs, boot-ROM drive), each tied to its ECR."""
    tracker = contract.get("hazards_tracked_by")
    if not contract.get("hazards") and tracker and ecr_open(tracker):
        F.add(FAIL, f"`hazards` is empty while {tracker} ({ecr_state(tracker)}) is still open: the pin hazards it tracks cannot have vanished")
    for h in contract.get("hazards", []):
        hit = [(i, net) for i, (port, net) in placed.items() if port == h["port"]]
        cleared = h.get("cleared_by")
        if hit and cleared and any(p["port"] == cleared["pin"] and nets.get(str(pos)) == cleared["net"] for pos, p in data.pins.items()):
            F.add(PASS, f"{h['port']}: hazard cleared, {cleared['pin']} is on {cleared['net']}")
            continue
        level, tag = known(h["ecr"])
        if h.get("mitigation") == "firmware" and ecr_state(h["ecr"]) in ("closed", "verified"):
            level, tag = PASS, f"handled in firmware, {h['ecr']} {ecr_state(h['ecr'])}"
        for i, net in hit:
            F.add(level, f"{i}: net {net} on {h['port']}: {h['note']} [{tag}; {h['source']}]", f"{i} on {h['port']} [{tag}]", key=f"hazard {i} {h['port']}", kind="hazard")


def netlist_findings(F, sch):
    """hw/pod/pod.net is what the placer reads: its U1 connectivity must be the SKiDL circuit's."""
    path = CFG.netlist
    if not path.exists():
        F.add(WARN, f"{path.name} is missing: cannot confirm the placer reads the same U1 connections", key="netlist missing")
        return
    got, want = netlist_connectivity(path), schematic_connectivity(sch)
    diff = sorted({k for k in set(got) | set(want) if k[0] == "U1" and got.get(k) != want.get(k)}, key=lambda k: int(k[1]))
    for ref, pin in diff[:6]:
        F.add(FAIL, f"{path.name} is stale: U1 pin {pin} connects to {refs_str({r for r, _ in got.get((ref, pin), ())} or {'nothing'})}, "
                    f"gen.py has {refs_str({r for r, _ in want.get((ref, pin), ())} or {'nothing'})} (regenerate: python3 hw/pod/gen.py)")


def check_pins(contract, sch, data):
    F = Findings("pins")
    problems = validate_contract(contract)
    if problems:
        return Result("pins", FAIL, f"pin-contract.yaml is unusable: {problems[0]}" + (f" (+{len(problems) - 1} more)" if len(problems) > 1 else ""), problems)
    ref = contract["mcu"]["ref"]
    if ref not in sch.parts:
        return Result("pins", FAIL, f"{ref} is not in the schematic")
    names = {num: name for num, (name, _) in sch.parts[ref]["pins"].items()}
    nets = {num: net for num, (_, net) in sch.parts[ref]["pins"].items()}
    package_findings(F, contract, data, names, nets)
    chosen, taken, placed = entry_findings(F, contract, sch, data, nets)
    pair_findings(F, contract, chosen)
    hazard_findings(F, contract, data, nets, placed)
    for pos, ids in taken.items():
        if len(ids) > 1:
            F.add(FAIL, f"pin {pos} carries {len(ids)} contract jobs: {', '.join(ids)}")
    covered = {resolve_net(e, sch)[0] for e in contract["signals"]} | set(contract["power_pins"].values()) | set(contract.get("unconstrained") or [])
    for num, n in sorted(nets.items(), key=lambda kv: int(kv[0])):
        pin = data.pins.get(int(num))
        if n and pin and pin["type"] == "I/O" and n not in covered:
            F.add(FAIL, f"pin {num} {pin['port']} net {n} has no row in docs/system/pin-contract.yaml: declare the signal it needs (or list the net under `unconstrained`)")
    netlist_findings(F, sch)
    n_io = sum(1 for pos in taken if data.pins[int(pos)]["type"] == "I/O")
    return F.result(f"{len(contract['signals'])} contract nets ({n_io} I/O pins + NRST) sit on pins that provide their signal and AF number; the symbol's pin numbers, "
                    f"power pins and exposed pad match ST's {contract['mcu']['package']} pinout; every I/O net has a row; pod.net matches the circuit", "pin-contract",
                    warn_lead="every net sits on a pin that provides its signal; ")


# ------------------------------------------------------------------------------------------- [rails]
def validate_budget(b):
    if not isinstance(b, dict) or not b.get("rails"):
        return ["rail-budget.yaml has no `rails`"]
    bad = [f"missing top-level key `{k}`" for k in ("smps_allowed",) if k not in b]
    for i, r in enumerate(b["rails"]):
        what = r.get("id", f"rail {i + 1}") if isinstance(r, dict) else f"rail {i + 1}"
        if not isinstance(r, dict) or "id" not in r or "net" not in r:
            bad.append(f"{what}: needs id and net")
            continue
        for ld in r.get("loads", []):
            if "name" not in ld or not any(k in ld for k in ("avg_ma", "from_rail", "sum_of", "calc")):
                bad.append(f"{r['id']}: load {ld.get('name', '?')!r} needs avg_ma, calc, from_rail or sum_of")
        for rt in r.get("ratings", []):
            if "name" not in rt:
                bad.append(f"{r['id']}: a rating has no name")
    return bad


def rail_needs(rail):
    return {ld["from_rail"] for ld in rail.get("loads", []) if "from_rail" in ld} | {ld["sum_of"]["rail"] for ld in rail.get("loads", []) if "sum_of" in ld}


def rail_order(rails, F):
    """The rails in dependency order (a rail that draws from another comes after it), whatever order the file lists them in."""
    by_id, order, state = {r["id"]: r for r in rails}, [], {}

    def visit(rid, trail):
        if state.get(rid) == "done":
            return
        if state.get(rid) == "busy":
            F.add(FAIL, f"rails draw from each other in a loop: {' -> '.join(trail + [rid])}")
            return
        state[rid] = "busy"
        for need in sorted(rail_needs(by_id[rid])):
            if need not in by_id:
                F.add(FAIL, f"{rid} draws from rail {need}, which is not in the budget")
            else:
                visit(need, trail + [rid])
        state[rid] = "done"
        order.append(by_id[rid])

    for r in rails:
        visit(r["id"], [])
    return order


def calc_ma(calc, sch):
    """mA from a resistor expression on the schematic's own values: V over each of `parallel`, or V over the sum of `series`."""
    v = float(calc["volts"])
    vals = [ohms(sch.parts[r]["value"]) for r in calc.get("parallel") or calc["series"]]
    if any(x <= 0 for x in vals):
        raise ValueError("a zero resistance")
    return 1000 * (sum(v / x for x in vals) if "parallel" in calc else v / sum(vals))


def assumption_findings(F, rid, row, sch):
    """A typed number derived from schematic values must say which: FAIL when the schematic has moved on."""
    for ref, want in (row.get("assumes") or {}).items():
        have = sch.parts.get(ref, {}).get("value")
        try:
            same = have is not None and math.isclose(ohms(have), ohms(want), rel_tol=1e-9, abs_tol=1e-12)
        except ValueError:
            same = str(have) == str(want)
        if not same:
            F.add(FAIL, f"{rid}: '{row.get('name', '?')[:40]}' was derived with {ref} = {want}, the schematic has {have}: re-derive the row", f"{rid} row derived with {ref}={want}, schematic has {have}")


def load_row(ld, totals, rows, sch, F, rid):
    """(avg low, avg high, peak) mA of one declared load."""
    assumption_findings(F, rid, ld, sch)
    if "from_rail" in ld:
        t = totals[ld["from_rail"]]
        return t["avg_lo"], t["avg_hi"], t["peak"]
    if "sum_of" in ld:
        src = rows.get(ld["sum_of"]["rail"], {})
        picked = [src[i] for i in ld["sum_of"]["rows"] if i in src]
        if len(picked) != len(ld["sum_of"]["rows"]):
            F.add(FAIL, f"{rid}: '{ld['name'][:40]}' sums rows {ld['sum_of']['rows']} of {ld['sum_of']['rail']}, which are not all there")
        return tuple(sum(x[k] for x in picked) for k in range(3))
    a, b = ld.get("avg_ma", (0.0, 0.0))
    c = ld.get("peak_ma", b)
    if "calc" in ld:
        try:
            x = calc_ma(ld["calc"], sch)
        except (KeyError, ValueError) as e:
            F.add(FAIL, f"{rid}: '{ld['name'][:40]}' cannot be computed from the schematic: {type(e).__name__}: {e}")
            return a, b, c
        c = x
        if ld["calc"].get("into", "both") == "both":
            a = b = x
    return a, b, c


def rail_totals(budget, sch, F=None):
    """{rail id: {avg_lo, avg_hi, peak}} and the per-row figures, for every rail except the exclusive ones (computed in dependency order)."""
    F = F or Findings("rails")
    totals, rows = {}, {}
    for rail in rail_order(budget["rails"], F):
        if "exclusive_to" in rail:
            continue
        lo = hi = pk = 0.0
        rows[rail["id"]] = {}
        for ld in rail.get("loads", []):
            try:
                a, b, c = load_row(ld, totals, rows, sch, F, rail["id"])
            except KeyError:
                F.add(FAIL, f"{rail['id']}: load '{ld.get('name', '?')[:40]}' draws from a rail that has no totals yet")
                continue
            lo, hi, pk = lo + a, hi + b, pk + c
            if "id" in ld:
                rows[rail["id"]][ld["id"]] = (a, b, c)
        totals[rail["id"]] = dict(avg_lo=lo, avg_hi=hi, peak=pk)
    return totals, rows


def topology_findings(F, rail, sch):
    """The declared loads against the parts that are really on the rail's net."""
    rid, net = rail["id"], rail["net"]
    on_net = {r for r, _, _ in sch.nets[net]}
    declared = set(rail.get("source_refs", []))
    for ld in rail.get("loads", []):
        declared |= set(ld.get("refs", []))
        gone = [r for r in ld.get("refs", []) if r not in on_net and "via" not in ld]
        if gone:
            F.add(FAIL, f"{rid}: load '{ld['name'][:40]}' declares {refs_str(gone)} which are not on net {net} (add `via` if they reach it another way)")
        missing = [r for r in ld.get("refs", []) if r not in sch.parts]
        if missing:
            F.add(FAIL, f"{rid}: load '{ld['name'][:40]}' names {refs_str(missing)}, not in the schematic")
    unbudgeted = [r for r in on_net if re.match(r"(R|U|Q|D|L|Y|SW)\d", r) and r not in declared and not sch.parts[r]["dnp"]]
    if unbudgeted:
        F.add(WARN, f"{rid}: {refs_str(unbudgeted)} on net {net} but in no declared load: unbudgeted", f"{rid}: {refs_str(unbudgeted)} unbudgeted", key=f"unbudgeted {rid} {refs_str(unbudgeted)}")


def rating_limits(rt, sch):
    """(continuous mA, peak mA) of a rating: typed, or derived from the part's own value (`derive: {power_w, ref}` = sqrt(P / R))."""
    if "derive" in rt:
        dv = rt["derive"]
        lim = 1000 * math.sqrt(float(dv["power_w"]) / ohms(sch.parts[dv["ref"]]["value"]))
        return lim, lim
    return rt.get("continuous_ma"), rt.get("peak_ma")


def rating_findings(F, rail, avg, peak, margin, sch):
    """Average and peak against every rating; an overload is waived only by an open ECR, up to the waiver's ceiling."""
    rid = rail["id"]
    for rt in rail["ratings"]:
        try:
            cont, pk_lim = rating_limits(rt, sch)
        except (KeyError, ValueError) as e:
            F.add(FAIL, f"{rid}: rating '{rt['name']}' cannot be derived from the schematic: {type(e).__name__}: {e}")
            continue
        for kind, val, lim in (("average", avg, cont), ("peak", peak, pk_lim)):
            head = f"{rid} {kind} {val:.1f} mA vs {rt['name']}"
            what = rt.get("short", rt["name"])
            if lim is None:
                F.add(WARN, f"{head}: rating not recorded ({rt.get('source', 'no source')})", f"{rid} {kind} vs {what}: no rating recorded", key=f"no-rating {rid} {kind} {rt['name']}")
            elif val > lim + EPS:
                waiver = next((w for w in rail.get("waivers", []) if w.get("covers") in (kind, "both")), None)
                hard_lim = rt.get("hard_limit_ma")
                over = f"{rid} {kind} {val:.0f} mA > {what} {lim:.0f} mA"
                if hard_lim is not None and val > hard_lim + EPS:
                    F.add(FAIL, f"{head} {lim:.0f} mA: {val:.1f} mA is beyond its {hard_lim} mA minimum current limit, out of range: no waiver can cover it", f"{over}, beyond its {hard_lim} mA current limit")
                elif waiver and waiver.get("max_ma") is not None and val > waiver["max_ma"] + EPS:
                    F.add(FAIL, f"{head} {lim:.0f} mA: {val:.1f} mA is above the {waiver['ecr']} waiver ceiling {waiver['max_ma']} mA: the ECR describes a smaller overload",
                          f"{over}, above the {waiver['ecr']} waiver ceiling {waiver['max_ma']} mA")
                elif waiver and ecr_open(waiver["ecr"]):
                    hard = f"; below its {hard_lim} mA minimum current limit: out of rating, not out of range" if hard_lim is not None else ""
                    F.add(WARN, f"{head} {lim:.0f} mA: over by {val - lim:.1f} mA, waived by {waiver['ecr']} ({ecr_state(waiver['ecr'])}){hard}",
                          f"{over} [{waiver['ecr']} {ecr_state(waiver['ecr'])}]", key=f"over {rid} {kind} {rt['name']} {waiver['ecr']}")
                elif waiver:
                    F.add(FAIL, f"{head} {lim:.0f} mA: over by {val - lim:.1f} mA and the waiver {waiver['ecr']} is {ecr_state(waiver['ecr']) or 'missing'}: fix the load or the rating",
                          f"{over}, waiver {waiver['ecr']} {ecr_state(waiver['ecr']) or 'missing'}")
                else:
                    F.add(FAIL, f"{head} {lim:.0f} mA: over by {val - lim:.1f} mA with no ECR waiver", f"{over}, no ECR waiver")
            elif val > lim * (1 - margin):
                cite = f" (see {', '.join(rail['related_ecrs'])})" if rail.get("related_ecrs") else ""
                F.add(WARN, f"{head} {lim:.0f} mA: {100 * val / lim:.0f} % of the rating, inside the {margin * 100:.0f} % margin{cite}",
                      f"{rid} {kind} {val:.0f} mA is {100 * val / lim:.0f} % of {what} {lim:.0f} mA" + (f" [{rail['related_ecrs'][0]}]" if rail.get("related_ecrs") else ""),
                      key=f"margin {rid} {kind} {rt['name']}")


def d11_findings(F, budget, sch):
    """D11 on the whole circuit: the MCU's core SMPS is the one switching regulator. Any other inductor, ferrite, or switching-node pin is a FAIL."""
    smps = budget["smps_allowed"]
    allowed = set(smps["refs"])
    for ref, p in sorted(sch.parts.items(), key=lambda kv: nat(kv[0])):
        if ref in allowed:
            continue
        why = None
        if re.match(r"(L|FB)\d", ref):
            why = f"{ref} ({p['value']}) is an inductor / ferrite"
        elif re.search(r"(?i)\d\s*[uµn]H\b", p["value"]):
            why = f"{ref} has the inductor value {p['value']}"
        elif ref.startswith("U") and (sw := [n for n, _ in p["pins"].values() if SWITCH_PIN.match(n)]):
            why = f"{ref} has switching-node pin(s) {', '.join(sorted(set(sw)))}"
        if why:
            F.add(FAIL, f"D11: {why}; only {', '.join(smps['refs'])} may switch ({smps['source']})", f"D11: {why}")


def unmodelled_findings(F, budget, sch):
    """Every net that feeds an IC power pin must be a budgeted rail or be listed (with a reason) under `unmodelled`."""
    known_nets = {r["net"] for r in budget["rails"]} | set(budget.get("unmodelled") or {})
    for net, members in sorted(sch.nets.items()):
        pins = sorted({(r, n) for r, _, n in members if r.startswith("U") and POWER_PIN.match(n)}, key=lambda t: (nat(t[0]), t[1]))
        if pins and net not in known_nets:
            F.add(FAIL, f"net {net} feeds power pin(s) {', '.join(f'{r}.{n}' for r, n in pins)} but has no rail row and is not listed under `unmodelled` in rail-budget.yaml: "
                        "budget it or say why it is not modelled", f"net {net} feeds {pins[0][0]}.{pins[0][1]} with no rail row")


def check_rails(budget, sch):
    F = Findings("rails")
    problems = validate_budget(budget)
    if problems:
        return Result("rails", FAIL, f"rail-budget.yaml is unusable: {problems[0]}" + (f" (+{len(problems) - 1} more)" if len(problems) > 1 else ""), problems)
    margin = budget.get("margin_warn", 0.10)
    totals, _ = rail_totals(budget, sch, F)
    for rail in rail_order(budget["rails"], Findings("order")):
        rid, net = rail["id"], rail["net"]
        if net not in sch.nets:
            F.add(FAIL, f"{rid}: net {net} is not in the schematic")
            continue
        if "exclusive_to" in rail:
            for r in sorted({r for r, _, _ in sch.nets[net]} - set(rail["exclusive_to"]), key=nat):
                if r.startswith("C"):
                    F.add(WARN, f"{rid}: capacitor {r} added on the MCU's SMPS output: check the datasheet's output-capacitance window ({rail['exclusive_source']})",
                          f"{rid}: capacitor {r} added on the SMPS output", key=f"smps-cap {rid} {r}")
                else:
                    F.add(FAIL, f"{rid}: {r} hangs on the MCU core SMPS output; only {', '.join(rail['exclusive_to'])} may ({rail['exclusive_source']})")
            F.add(PASS, f"{rid}: {', '.join(rail['exclusive_to'])} are the only parts on the net ({rail['exclusive_source'].split(':')[0]})")
            continue
        t = totals.get(rid)
        if t is None:
            continue
        topology_findings(F, rail, sch)
        rating_findings(F, rail, t["avg_hi"], t["peak"], margin, sch)
        F.add(PASS, f"{rid}: average {t['avg_lo']:.1f}-{t['avg_hi']:.1f} mA, peak {t['peak']:.1f} mA over {len(rail['loads'])} declared loads" + "".join(f"; note: {n}" for n in rail.get("notes", [])))
    d11_findings(F, budget, sch)
    unmodelled_findings(F, budget, sch)
    return F.result(f"{len(budget['rails'])} rails within their ratings, D11 holds on the whole circuit", "rail", warn_lead=f"{len(budget['rails'])} rails; ")


# ------------------------------------------------------------------------------------------- [frame]
FRAME_FACTS = (       # (what, shell fact, same fact in frame.pod_facts(), same fact in pod.py)
    ("pod centre z", lambda s: s["ZC"], lambda f: f["ZC"], lambda p: p["POD_ZC"]),   # pod.py feeds blade.py: the rail and adapter
    ("pod bottom z", lambda s: s["Z0"], lambda f: f["Z0"], None),
    ("pod front x", lambda s: s["X0"], lambda f: f["X0"], None),
    ("pod rear x", lambda s: s["X1"], lambda f: f["X1"], None),
    ("board x0, x1", lambda s: (s["PCB"]["x0"], s["PCB"]["x1"]), lambda f: (f["PCB"]["x0"], f["PCB"]["x1"]), None),
    ("board y0, y1", lambda s: (s["PCB"]["y0"], s["PCB"]["y1"]), lambda f: (f["PCB"]["y0"], f["PCB"]["y1"]), None),
    ("board z0, z1", lambda s: (s["PCB"]["z0"], s["PCB"]["z1"]), lambda f: (f["PCB"]["z0"], f["PCB"]["z1"]), None),
    ("cell x1", lambda s: s["CELL"]["x1"], lambda f: f["CELL"]["x1"], None),
    ("mic port x, z", lambda s: s["MIC"], lambda f: (f["MIC_PORT"]["x"], f["MIC_PORT"]["z"]), None),
    ("button x, z", lambda s: s["SWITCH"], lambda f: (f["BUTTON"]["x"], f["BUTTON"]["z"]), None),
)


def frame_pod_facts(design=None):
    """What heel.py, pad.py and blade.py actually build against: frame.pod_facts() and pod.py's body constants, imported
    (both CAD-free since ECR-0001, 2026-10-07; frame.py's pod names resolve from the selected design's shell dims)."""
    if str(CFG.mech) not in sys.path:
        sys.path.insert(0, str(CFG.mech))
    import frame as fr
    import pod as pd
    return fr.pod_facts(design), dict(POD_ZC=pd.POD_ZC, POD_H=pd.POD_H, POD_L=pd.POD_L, POD_W=pd.POD_W)


def check_frame(sh, frame=None, pod=None):
    """frame.py and pod.py are what heel.py, pad.py and blade.py build against; they must agree with the live shell.
    frame/pod: injected facts (selftest); default = the imported modules for the shell's design."""
    if frame is None or pod is None:
        f0, p0 = frame_pod_facts(sh.get("design"))
        frame, pod = frame if frame is not None else f0, pod if pod is not None else p0
    shell = sh["env"]
    rows = []
    rnd = lambda v: tuple(round(x, 3) for x in v) if isinstance(v, tuple) else round(v, 3)
    for what, fs, ff, fp in FRAME_FACTS:
        try:
            a, others = fs(shell), [("frame.py", ff(frame))] + ([("pod.py", fp(pod))] if fp else [])
        except KeyError:
            rows.append(f"{what}: constant not readable")
            continue
        flat = lambda v: v if isinstance(v, tuple) else (v,)
        diff = [f"{n} {rnd(v)}" for n, v in others if any(abs(x - y) > 0.01 for x, y in zip(flat(a), flat(v)))]
        if diff:
            rows.append(f"{what}: {sh.get('name', 'shell')} {rnd(a)}; " + "; ".join(diff))
    if not rows:
        return Result("frame", PASS, f"frame.py and pod.py agree with {sh.get('name', 'the shell')} on all {len(FRAME_FACTS)} shared facts")
    level, tag = known("ECR-0001")
    return Result("frame", level, f"frame.py / pod.py disagree with {sh.get('name', 'the shell')} on {len(rows)} of {len(FRAME_FACTS)} shared facts "
                  f"({tag}): since ECR-0001 both derive from the current design's shell dims, so a difference means someone re-hard-coded a pod "
                  "constant in frame.py/pod.py; heel.py's clearance checks read frame.PCB and CELL, blade.py's rail and adapter read pod.POD_ZC",
                  rows, [f"frame:{tag}"] if level == WARN else [])


# ------------------------------------------------------------------------------------------- [selftest]
@dataclasses.dataclass
class Case:
    """One rule, one broken (or harmless) input: `run()` must give `expect`, and the finding text must contain `marker`."""
    name: str
    run: object
    expect: str = FAIL
    marker: str = None


def copy_sch(sch):
    return Sch(copy.deepcopy(sch.parts), {k: list(v) for k, v in sch.nets.items()})


def rewire(sch, ref, pin, net):
    """A copy of the circuit with one pin moved to another net (None = open)."""
    new = copy_sch(sch)
    name, old = new.parts[ref]["pins"][pin]
    if old:
        new.nets[old] = [t for t in new.nets[old] if not (t[0] == ref and t[1] == pin)]
    new.parts[ref]["pins"][pin] = (name, net)
    if net:
        new.nets.setdefault(net, []).append((ref, pin, name))
    return new


def add_part(sch, ref, value, pins):
    """A copy of the circuit with one more part; pins = {num: (name, net)}."""
    new = copy_sch(sch)
    new.parts[ref] = dict(value=value, footprint="", lcsc="", dnp="", pins=pins)
    for num, (name, net) in pins.items():
        new.nets.setdefault(net, []).append((ref, num, name))
    return new


def pin_of(sch, ref, net):
    return next(num for num, (_, n) in sch.parts[ref]["pins"].items() if n == net)


def pin_named(sch, ref, name):
    return next(num for num, (n, _) in sch.parts[ref]["pins"].items() if n == name)


def broken_pin(contract, sch, data):
    """A copy of the circuit with one contract net moved onto a free U1 pin that cannot provide its signal."""
    u1 = contract["mcu"]["ref"]
    pins = sch.parts[u1]["pins"]
    for e in (e for e in contract["signals"] if "net" in e and e["signal"] not in ("GPIO", "NRST", "BOOT0")):
        old = next((num for num, (_, n) in pins.items() if n == e["net"]), None)
        specs = [e["signal"]] + [a["signal"] for a in e.get("alternates", [])]
        for q, pin in sorted(data.pins.items()):
            if old and pin["type"] == "I/O" and pins.get(str(q), (None, "x"))[1] is None and not any(provides(s, pin) for s in specs):
                return f"pins: {e['id']} moved from {pins[old][0]} to the free pin {pins[str(q)][0]}, which cannot provide {e['signal']}", \
                    rewire(rewire(sch, u1, old, None), u1, str(q), e["net"])
    raise LookupError("no contract net can be moved to a free pin that breaks it")


@contextlib.contextmanager
def ecr_states(**states):
    """Run with a temporary copy of the ECR folder in which ECR_0013='closed' (underscore for the dash) rewrites that status line."""
    with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as tmp:
        for f in CFG.ecr_dir.glob("ECR-*.md"):
            shutil.copy(f, tmp)
        for key, status in states.items():
            ecr = key.replace("_", "-")
            (Path(tmp) / f"{ecr}.md").write_text(f"# test copy\n\nStatus: {status}\n")
        saved, CFG.ecr_dir = CFG.ecr_dir, Path(tmp)
        try:
            yield
        finally:
            CFG.ecr_dir = saved


@contextlib.contextmanager
def other_netlist(edit):
    """Run with hw/pod/pod.net replaced by a temporary copy that `edit(text)` has changed (edit=None: no netlist at all)."""
    with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as tmp:
        p = Path(tmp) / "pod.net"
        if edit:
            p.write_text(edit(CFG.netlist.read_text()))
        saved, CFG.netlist = CFG.netlist, p
        try:
            yield
        finally:
            CFG.netlist = saved


def board_round_trip(path, edit):
    """Edit a copy of the board file with pcbnew, save, and read it back through read_board(): the file path, not the dataclass."""
    pcbnew = import_pcbnew()
    with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as tmp:
        out = Path(tmp) / "copy.kicad_pcb"
        with quiet_stderr():
            board = pcbnew.LoadBoard(str(path))
            edit(board, pcbnew)
            pcbnew.SaveBoard(str(out), board)
        try:
            return read_board(out), None
        except OSError as e:
            return None, str(e)


def shift_in_file(dx_mm, dy_mm):
    def edit(board, pcbnew):
        v = pcbnew.VECTOR2I(pcbnew.FromMM(dx_mm), pcbnew.FromMM(dy_mm))
        for f in board.GetFootprints():
            f.Move(v)
        for d in board.GetDrawings():
            d.Move(v)
    return edit


def pins_without_netlist(contract, sch, data):
    """check_pins with no pod.net: a circuit copy is not in step with the real netlist, and that FAIL must not hide the rule under test."""
    with other_netlist(None):
        return check_pins(contract, sch, data)


def selftest_cases(ctx):
    """Case list. A case that needs a part the design no longer has is reported as skipped (LookupError), never a crash."""
    sh, brd, sch, table, contract, data, budget = (ctx[k] for k in ("sh", "brd", "sch", "table", "contract", "data", "budget"))
    ox0, oy0, ox1, oy1 = brd.outline
    cases = []
    first = lambda prefix: next(f for r, f in sorted(brd.fps.items(), key=lambda kv: nat(kv[0])) if re.match(prefix + r"\d", r) and not f.copper_only)

    def add(build):
        try:
            cases.append(build())
        except (LookupError, KeyError, StopIteration, ValueError) as e:
            cases.append(Case(f"skipped: {build.__name__} ({e or 'part not in the design'})", None))

    def mic_origin():
        u2 = brd.fps[MIC_REF]
        port = max((p for p in u2.pads if p.attr == "NPTH" and p.drill > 0), key=lambda p: p.drill)
        dx = (sh["MIC"][0] - sh["PCB"]["x0"]) - u2.x               # the footprint ORIGIN put at the lid-port x: the ECR-0011 defect
        return Case(f"mic-port: footprint origin at the lid port (hole at board x {port.x + dx:.2f}, the ECR-0011 defect)", lambda: check_mic(sh, moved(brd, MIC_REF, dx=dx), table, sch), FAIL, "off the lid port")

    def mic_stack():
        return Case("mic-port: 0.10 mm off the lid port: inside the 0.20 limit, but not with the tolerance stack", lambda: check_mic(sh, moved(brd, MIC_REF, dx=0.10), table, sch), WARN, "worst-case stack exceeds")

    def mic_lid():
        return Case("mic-port: lid port D0.5 narrower than the board hole D0.6", lambda: check_mic({**sh, "mic_port_d": 0.5}, brd, table, sch), FAIL, "smaller than the board hole")

    def mic_face():
        f = brd.fps[MIC_REF]
        return Case("mic-port: U2 on the F face", lambda: check_mic(sh, dataclasses.replace(brd, fps={**brd.fps, MIC_REF: dataclasses.replace(f, face="F")}), table, sch), FAIL, "must be on B")

    def mic_ap():
        u2 = brd.fps[MIC_REF]

        def run():
            hole = max((p for p in u2.pads if p.attr == "NPTH" and p.drill > 0), key=lambda p: p.drill)
            shifted = tuple(dataclasses.replace(p, x=p.x + 0.12, box=(p.box[0] + 0.12, p.box[1], p.box[2] + 0.12, p.box[3])) if p is hole else p for p in u2.pads)
            return check_mic(sh, dataclasses.replace(brd, fps={**brd.fps, MIC_REF: dataclasses.replace(u2, pads=shifted)}), table, sch)
        return Case("mic-port: the hole 0.12 mm off the datasheet port (still inside the lid port)", run, FAIL, "datasheet port")

    def mic_locating():
        if sh.get("locating"):                                     # Phase 2: the gauge pin locates; a pin residual over the limit must warn
            bad = {**sh, "locating": {**sh["locating"], "worst": sh["locating"]["limit"] + 0.05, "ok": False}}
            return Case("mic-port: gauge-pin locating residual 0.05 mm over the duct limit", lambda: check_mic(bad, brd, table, sch), WARN, "gauge pin")
        return Case("mic-port: a perfectly placed mic still warns while nothing locates the board in the cavity", lambda: check_mic(sh, brd, table, sch), WARN, "nothing locates the board")

    def mic_located():
        if not sh.get("locating"):
            raise LookupError("revg: nothing locates the board")
        return Case("mic-port: a perfectly placed mic on a gauge-pin-located board passes", lambda: check_mic(sh, brd, table, sch), PASS)

    def switch_locating():
        brd.fps[SWITCH_REF]
        if sh.get("locating"):
            bad = {**sh, "locating": {**sh["locating"], "worst": sh["locating"]["limit"] + 0.05, "ok": False}}
            return Case("switch: the same gauge-pin warning", lambda: check_switch(bad, brd), WARN, "gauge pin")
        return Case("switch: the same locating warning", lambda: check_switch(sh, brd), WARN, "nothing locates the board")

    def switch_off():
        brd.fps[SWITCH_REF]
        return Case("switch: SW1 0.30 mm off the plunger axis", lambda: check_switch(sh, moved(brd, SWITCH_REF, dx=0.30)), FAIL, "off the plunger axis")

    def switch_stack():
        brd.fps[SWITCH_REF]
        return Case("switch: 0.00 mm nominal, but the worst-case stack exceeds the 0.15 limit", lambda: check_switch(sh, brd), WARN, "worst-case stack exceeds")

    def outline_wide():
        return Case("outline: board 0.20 mm wider than the shell", lambda: check_outline(sh, dataclasses.replace(brd, outline=(ox0, oy0, ox1 + 0.20, oy1))), FAIL, "over the shell")

    def outline_tall():
        return Case("outline: board 0.04 mm taller than the shell (inside the old +-0.05, but oversize has no tolerance)", lambda: check_outline(sh, dataclasses.replace(brd, outline=(ox0, oy0, ox1, oy1 + 0.04))), FAIL, "oversize has no tolerance")

    def outline_thick():
        return Case("outline: a 3.0 mm board (worse than the known 1.6 mm stack-up issue)", lambda: check_outline(sh, dataclasses.replace(brd, thickness=3.0)), FAIL, "known issue covers up to")

    def outline_drag():
        base = {c: fn(*a).status for c, fn, a in ((c, f, a) for c, f, a in drag_checks)}

        def run():
            moved_brd, err = board_round_trip(ctx["board_path"], shift_in_file(100, 80))
            if err:
                return Result("selftest", FAIL, f"the dragged copy could not be read back: {err}")
            got = {c: fn(*(moved_brd if x is brd else x for x in a)).status for c, fn, a in drag_checks}
            same = got == base
            return Result("selftest", PASS if same else FAIL, "same results on a board dragged by (+100, +80) mm" if same else f"a dragged board changes results: {base} vs {got}")
        return Case("outline: the whole board dragged to another KiCad origin (file round trip) must change nothing", run, PASS)

    drag_checks = (("mic-port", check_mic, (sh, brd, table, sch)), ("switch", check_switch, (sh, brd)), ("outline", check_outline, (sh, brd)),
                   ("inside", check_inside, (sh, brd, table)), ("clamp-bands", check_clamp, (sh, brd, table)), ("board-nets", check_board_nets, (brd, sch)))

    def round_trip_mic():
        def run():
            b2, err = board_round_trip(ctx["board_path"], lambda board, pcbnew: board.FindFootprintByReference(MIC_REF).Move(pcbnew.VECTOR2I(pcbnew.FromMM(0.77), 0)))
            return check_mic(sh, b2, table, sch) if b2 else Result("mic-port", FAIL, err)
        return Case("mic-port: U2 moved 0.77 mm in a written copy of the board file, read back through read_board()", run, FAIL, "off the lid port")

    def dup_ref():
        def run():
            def edit(board, pcbnew):
                d = board.FindFootprintByReference(MIC_REF).Duplicate(False).Cast()
                board.Add(d)
                d.SetReference(MIC_REF)
            b2, err = board_round_trip(ctx["board_path"], edit)
            return Result("board", FAIL, err) if err else Result("board", PASS, "duplicate accepted")
        return Case("board: two footprints with the reference U2", run, FAIL, "duplicate reference")

    def inside_far():
        f = first("R")
        return Case(f"inside: {f.ref} 30 mm off the board", lambda: check_inside(sh, moved(brd, f.ref, dx=30), table), FAIL, "outside the board outline")

    def inside_rear():
        f = max((f for f in brd.fps.values() if not f.copper_only), key=lambda f: extent(f)[2])
        dx = (ox1 + 1.5) - extent(f)[2]
        return Case(f"inside: {f.ref} hanging 1.5 mm past the rear edge", lambda: check_inside(sh, moved(brd, f.ref, dx=dx), table), FAIL, "past the rear edge")

    def vhb_flip():
        if not sh.get("vhb"):
            raise LookupError("revg: clamp ribs, no VHB face")
        v = next(f for r, f in sorted(brd.fps.items(), key=lambda kv: nat(kv[0])) if f.face == "B" and not f.copper_only and f.courtyard)
        return Case(f"clamp-bands: {v.ref} turned onto the F face, under the VHB", lambda: check_clamp(sh, dataclasses.replace(brd, fps={**brd.fps, v.ref: dataclasses.replace(v, face="F")}), table),
                    FAIL, "under the vhb")

    def vhb_pocket():
        if not sh.get("vhb"):
            raise LookupError("revg: no SW1 pocket")
        return Case(f"clamp-bands: {SWITCH_REF} moved 2.5 mm, out of its lid pocket", lambda: check_clamp(sh, moved(brd, SWITCH_REF, dx=2.5), table), FAIL, SWITCH_REF)

    def vhb_bond():
        if not sh.get("vhb"):
            raise LookupError("revg: no VHB")
        big = {**sh, "vhb": {**sh["vhb"], "tp_cut_r": 6.0}}     # per-pad cut-outs blown up to 12 x 12 mm (board is 12 tall): most of the tape gone
        return Case("clamp-bands: test-pad cut-outs grown to 12 mm squares: too little VHB left", lambda: check_clamp(big, brd, table), WARN, "stays bonded")

    def clamp_body():
        if sh.get("vhb"):
            raise LookupError("Phase 2: no clamp bands")
        v = next(f for f in brd.fps.values() if not f.copper_only and f.courtyard and not is_test_pad(f.ref))   # TPs are exempt by rule
        return Case(f"clamp-bands: {v.ref} dragged into the top band", lambda: check_clamp(sh, moved(brd, v.ref, dy=0.3 - (extent(v)[1] - oy0)), table), FAIL, "clamp bands")

    def clamp_tiny():
        if sh.get("vhb"):
            raise LookupError("Phase 2: no clamp bands")
        v = max((f for f in brd.fps.values() if not f.copper_only and f.courtyard), key=lambda f: extent(f)[3] - extent(f)[1])

        def run():
            m = shift_fp(v, 0, 0.43 - (min(p.box[1] for p in v.pads) - oy0))
            tiny = dataclasses.replace(m, courtyard=(m.x - 0.05, m.y - 0.05, m.x + 0.05, m.y + 0.05))
            return check_clamp(sh, dataclasses.replace(brd, fps={**brd.fps, v.ref: tiny}), table)
        return Case(f"clamp-bands: {v.ref} with a 0.1 mm courtyard but its pads 0.43 mm from the edge", run, FAIL, "clamp bands")

    def clamp_wire_pad():
        if sh.get("vhb"):
            raise LookupError("Phase 2: no clamp bands")
        j = next(f for f in brd.fps.values() if is_wire_pad(f))
        dy = (oy1 - 0.2) - max(p.box[3] for p in j.pads)
        return Case(f"clamp-bands: wire pad {j.ref} 0.2 mm from the long edge", lambda: check_clamp(sh, moved(brd, j.ref, dy=dy), table), FAIL, "clamp bands")

    def heights():
        f = max((f for f in brd.fps.values() if part_height(f, sch, table)[0] is not None), key=lambda f: part_height(f, sch, table)[0])
        tall, lcsc = copy.deepcopy(table), sch.parts.get(f.ref, {}).get("lcsc")
        section, key = ("by_lcsc", lcsc) if lcsc in table.get("by_lcsc", {}) else ("by_footprint", f.name)
        tall[section][key]["max_mm"] = band_of(sh, f) + 0.1
        return Case(f"heights: {f.ref} {band_of(sh, f) + 0.1:.2f} mm tall, 0.10 mm over its band", lambda: check_heights(sh, brd, sch, tall), FAIL, "taller than the band")

    def heights_pocket():
        if not sh.get("pocket"):
            raise LookupError("revg: no lid pocket")
        sw = brd.fps[SWITCH_REF]
        return Case(f"heights: {SWITCH_REF} moved 2.5 mm out of its lid pocket meets the 0.30 mm F gap", lambda: check_heights(sh, moved(brd, sw.ref, dx=2.5), sch, table), FAIL, SWITCH_REF)

    def heights_empty():
        return Case("heights: a board with no footprints", lambda: check_heights(sh, dataclasses.replace(brd, fps={}), sch, table), FAIL, "no footprints")

    def nets_swap():
        a, b = (pin_of(sch, "U1", n) for n in ("GA_P", "GB_P"))

        def run():
            u1 = brd.fps["U1"]
            na, nb = (next(p.net for p in u1.pads if p.num == n) for n in (a, b))
            pads = tuple(dataclasses.replace(p, net=nb if p.num == a else na if p.num == b else p.net) for p in u1.pads)
            return check_board_nets(dataclasses.replace(brd, fps={**brd.fps, "U1": dataclasses.replace(u1, pads=pads)}), sch)
        return Case(f"board-nets: U1 pads {a} and {b} (GA_P and GB_P) swapped on the board", run, FAIL, "board U1 pad")

    def nets_missing():
        ref = first("R").ref
        return Case(f"board-nets: {ref} missing from the board", lambda: check_board_nets(dataclasses.replace(brd, fps={r: f for r, f in brd.fps.items() if r != ref}), sch), FAIL, "missing")

    def pin_wrong():
        name, bad = broken_pin(contract, sch, data)
        return Case(name, lambda: pins_without_netlist(contract, bad, data), FAIL, "cannot provide")

    def pair():
        c = copy.deepcopy(contract)
        next(e for e in c["signals"] if e["id"] == "GA_N")["complement_of"] = "GB_P"
        return Case("pins: GA_N declared the complement of GB_P (CH1N is not CH2's partner)", lambda: check_pins(c, sch, data), FAIL, "complementary output")

    def power_pin():
        bad = rewire(sch, "U1", pin_named(sch, "U1", "VDDA"), "GND")
        return Case("pins: VDDA on GND", lambda: pins_without_netlist(contract, bad, data), FAIL, "power pin")

    def ep():
        ep_pin = str(contract["mcu"]["exposed_pad"]["pin"])
        bad = rewire(sch, "U1", ep_pin, None)
        return Case("pins: exposed pad open", lambda: pins_without_netlist(contract, bad, data), FAIL, "exposed pad")

    def netlist():
        def edit(text):
            i = text.index('(ref "U1")', text.index("(node"))
            j = text.index("(pin ", i)
            k = text.index(")", j)
            return text[:j] + '(pin "99"' + text[k:]

        def run():
            with other_netlist(edit):
                return check_pins(contract, sch, data)
        return Case("pins: pod.net out of step with the circuit (one U1 pin changed)", run, FAIL, "stale")

    def hazard_expired():
        # Rev F cleared PA15 in hardware (PB5 strap) and the rest are firmware-mitigated, so make one hazard un-mitigated
        c2 = copy.deepcopy(contract)
        for h in c2["hazards"]:
            if h["port"] == "PB4":
                h.pop("mitigation", None)

        def run():
            with ecr_states(ECR_0013="closed"):
                return check_pins(c2, sch, data)
        return Case("pins: ECR-0013 closed while an un-mitigated hazard is still on a used pin", run, FAIL, "closed")

    def hazard_mitigated_closed():
        def run():
            with ecr_states(ECR_0013="closed"):
                return check_pins(contract, sch, data)
        return Case("pins: ECR-0013 closed with only firmware-mitigated hazards left (they clear)", run, PASS, "")

    def rows_deleted():
        c = copy.deepcopy(contract)
        gone = {"USB_DM", "USB_DP", "SWDIO", "SWCLK", "I_SENSE"}
        c["signals"] = [e for e in c["signals"] if e["id"] not in gone]
        return Case("pins: the USB, SWD and I_SENSE rows deleted from the contract", lambda: check_pins(c, sch, data), FAIL, "no row")

    def contract_empty():
        c = copy.deepcopy(contract)
        c["signals"] = []
        return Case("pins: `signals: []`", lambda: check_pins(c, sch, data), FAIL, "no rows")

    def power_rows_deleted():
        c = copy.deepcopy(contract)
        c["power_pins"].pop("VDDA")
        return Case("pins: the VDDA row deleted from power_pins", lambda: check_pins(c, sch, data), FAIL, "no rail in the contract")

    def unconstrained():
        c = copy.deepcopy(contract)
        c["signals"] = [e for e in c["signals"] if e["id"] != "I_SENSE"]
        c["unconstrained"] = {"I_SENSE": "test: deliberately without a row"}
        return Case("pins: a deleted I_SENSE row with an explicit `unconstrained` listing is accepted (hazard WARNs only)", lambda: check_pins(c, sch, data), WARN)

    def budget_unusable():
        b = copy.deepcopy(budget)
        del b["rails"][0]["net"]
        return Case("rails: a rail row without a net", lambda: check_rails(b, sch), FAIL, "unusable")

    def budget_no_d11():
        b = copy.deepcopy(budget)
        del b["smps_allowed"]
        return Case("rails: rail-budget.yaml without `smps_allowed` (D11 would go unenforced)", lambda: check_rails(b, sch), FAIL, "smps_allowed")

    def hazards_deleted():
        c = copy.deepcopy(contract)
        c["hazards"] = []
        return Case("pins: `hazards: []` while ECR-0013 is open", lambda: check_pins(c, sch, data), FAIL, "hazards")

    def absent_wrong():
        e = next(e for e in contract["signals"] if e.get("absent_ecr") and "via" in e)
        ref, net = e["via"]["ref"], e["via"]["from_net"]
        bad = rewire(sch, ref, pin_of(sch, ref, net), "GND")
        return Case(f"pins: {ref} moved from {net} to GND (wrong wiring, not the ECR's removal)", lambda: pins_without_netlist(contract, bad, data), FAIL, "is not on net")

    def absent_removed():
        e = next(e for e in contract["signals"] if e.get("absent_ecr") and "via" in e)
        ref = e["via"]["ref"]
        bad = copy_sch(sch)
        for num, (_, n) in list(bad.parts[ref]["pins"].items()):
            if n:
                if n != e["via"]["from_net"]:                      # the pin the part fed goes with it, as in ECR-0003
                    bad = rewire(bad, "U1", pin_of(bad, "U1", n), None)
                bad = rewire(bad, ref, num, None)
        del bad.parts[ref]

        return Case(f"pins: {ref} removed, as {e['absent_ecr']} proposes (a WARN, not a FAIL; pod.net is regenerated after the ECR lands)",
                    lambda: pins_without_netlist(contract, bad, data), WARN, e["absent_ecr"])

    def ecr_format():
        def run():
            with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as tmp:
                for n, line in enumerate(("Status: **Proposed.**", "status: `approved`", "Status: implemented (awaiting owner review)", "  Status:   PROPOSED")):
                    (Path(tmp) / f"ECR-{n}.md").write_text(f"# t\n\n{line}\n")
                bad = [n for n in range(4) if not ecr_open_in(f"ECR-{n}", tmp)]
            return Result("ecr", FAIL, f"ECR status format {bad} read as closed") if bad else Result("ecr", PASS, "all four formats read as open")
        return Case("ecr: **Proposed.**, `approved`, lower-case and padded Status lines all count as open", run, PASS)

    def waiver_removed():
        rail = next(r for r in budget["rails"] if r.get("waivers"))
        bare = copy.deepcopy(budget)
        for r in bare["rails"]:
            r.pop("waivers", None)
        return Case(f"rails: the {rail['waivers'][0]['ecr']} waiver removed from {rail['id']}", lambda: check_rails(bare, sch), FAIL, "no ECR waiver")

    def waiver_expired():
        rail = next(r for r in budget["rails"] if r.get("waivers"))

        def run():
            with ecr_states(**{rail["waivers"][0]["ecr"].replace("-", "_"): "closed"}):
                return check_rails(budget, sch)
        return Case(f"rails: the {rail['waivers'][0]['ecr']} waiver's ECR closed", run, FAIL, "waiver")

    def overload():
        rail = next(r for r in budget["rails"] if "ratings" in r and any("avg_ma" in ld for ld in r["loads"]))
        big = copy.deepcopy(budget)
        for r in big["rails"]:
            r.pop("waivers", None)
            if r["id"] == rail["id"]:
                ld = next(ld for ld in r["loads"] if "avg_ma" in ld)
                ld["peak_ma"] = 10 * max(rt.get("peak_ma") or 0 for rt in r["ratings"])
        return Case(f"rails: {rail['id']} given a load ten times its rating, no waiver", lambda: check_rails(big, sch), FAIL, "no ECR waiver")

    def waiver_ceiling():
        rail = next(r for r in budget["rails"] if any(w.get("max_ma") for w in r.get("waivers", [])))
        big = copy.deepcopy(budget)
        for r in big["rails"]:
            for rt in r.get("ratings", []):
                rt.pop("hard_limit_ma", None)                      # leave only the waiver's own ceiling
            for w in r.get("waivers", []):
                w["max_ma"] = 310
        return Case(f"rails: {rail['id']} peak above the waiver ceiling (no hard limit in play)", lambda: check_rails(big, sch), FAIL, "waiver ceiling")

    def hard_limit():
        rail = next(r for r in budget["rails"] if any("hard_limit_ma" in rt for rt in r.get("ratings", [])))
        big = copy.deepcopy(budget)
        for r in big["rails"]:
            for w in r.get("waivers", []):
                w.pop("max_ma", None)                              # leave only the part's own current limit
            if r["id"] == rail["id"]:
                next(ld for ld in r["loads"] if "avg_ma" in ld)["peak_ma"] = 500
        return Case(f"rails: {rail['id']} peak beyond the part's current limit (waiver without a ceiling)", lambda: check_rails(big, sch), FAIL, "current limit")

    def assumes():
        ref = next(iter(next(ld for r in budget["rails"] for ld in r.get("loads", []) if ld.get("assumes"))["assumes"]))
        bad = copy_sch(sch)
        bad.parts[ref]["value"] = "220R"
        return Case(f"rails: {ref} changed in the circuit under a budget row derived with the old value", lambda: check_rails(budget, bad), FAIL, ref)

    def derive():
        rt = next(rt for r in budget["rails"] for rt in r.get("ratings", []) if "derive" in rt)
        bad = copy_sch(sch)
        bad.parts[rt["derive"]["ref"]]["value"] = "3"
        return Case(f"rails: {rt['derive']['ref']} 3R instead of its value: the derived power rating falls with it", lambda: check_rails(budget, bad), FAIL, "BRIDGE_RTN peak")

    def calc_moves():
        ref = next(r for ld in (ld for rl in budget["rails"] for ld in rl.get("loads", []) if "calc" in ld) for r in ld["calc"].get("parallel") or ld["calc"]["series"])
        bad = copy_sch(sch)
        bad.parts[ref]["value"] = "100R"

        def run():
            before, after = rail_totals(budget, sch)[0], rail_totals(budget, bad)[0]
            moved_ = any(abs(before[k]["peak"] - after[k]["peak"]) > 0.5 for k in before)
            return Result("rails", PASS if moved_ else FAIL, f"changing {ref} moves the budget" if moved_ else f"changing {ref} left every rail total unchanged")
        return Case(f"rails: {ref} changed to 100R: the computed resistive loads must follow it", run, PASS)

    def rail_order_():
        rev = copy.deepcopy(budget)
        rev["rails"].reverse()
        base = check_rails(budget, sch).status
        return Case("rails: the same budget with its rails listed in reverse order must give the same status", lambda: check_rails(rev, sch), base)

    def d11_inductor():
        bad = add_part(sch, "L2", "2u2", {"1": ("1", "VSYS"), "2": ("2", "N$99")})
        return Case("rails: an inductor L2 added on VSYS (a second switching regulator)", lambda: check_rails(budget, bad), FAIL, "may switch")

    def d11_vdd11():
        bad = add_part(sch, "R50", "1k", {"1": ("1", "VDD11"), "2": ("2", "GND")})
        return Case("rails: R50 hung on the MCU core SMPS output (VDD11)", lambda: check_rails(budget, bad), FAIL, "VDD11")

    def new_rail():
        bad = add_part(sch, "U7", "BOOST", {"1": ("VIN", "VSYS"), "2": ("VOUT", "PLUS5V"), "3": ("GND", "GND")})
        bad = add_part(bad, "U8", "LOAD", {"1": ("VDD", "PLUS5V")})
        return Case("rails: a new +5V net feeding an IC power pin, in no rail row", lambda: check_rails(budget, bad), FAIL, "PLUS5V")

    def topology():
        c = copy.deepcopy(budget)
        rail = next(r for r in c["rails"] if r.get("loads") and r["net"] in sch.nets)
        stranger = next(r for r in sch.parts if r not in {x for x, _, _ in sch.nets[rail["net"]]} and r.startswith("R"))
        next(ld for ld in rail["loads"] if "refs" in ld)["refs"].append(stranger)
        return Case(f"rails: a load naming {stranger}, which is not on net {rail['net']}", lambda: check_rails(c, sch), FAIL, "not on net")

    def frame_expired():
        def run():
            f0, p0 = frame_pod_facts(sh.get("design"))
            stale = dict(f0, ZC=f0["ZC"] + 0.45)              # a pod constant re-hard-coded in frame.py (the pre-ECR-0001 state)
            with ecr_states(ECR_0001="closed"):
                return check_frame(sh, frame=stale, pod=p0)
        return Case("frame: frame.py's pod centre re-hard-coded 0.45 mm off the shell, ECR-0001 closed", run, FAIL, "ECR-0001")

    for build in (mic_origin, mic_stack, mic_lid, mic_face, mic_ap, mic_locating, mic_located, switch_locating, switch_off, switch_stack, outline_wide, outline_tall, outline_thick, outline_drag, round_trip_mic,
                  dup_ref, inside_far, inside_rear, clamp_body, clamp_tiny, clamp_wire_pad, vhb_flip, vhb_pocket, vhb_bond, heights, heights_pocket, heights_empty, nets_swap, nets_missing,
                  pin_wrong, pair, power_pin, ep, netlist, hazard_expired, hazard_mitigated_closed, rows_deleted, contract_empty, power_rows_deleted, unconstrained, budget_unusable, budget_no_d11, hazards_deleted, absent_wrong, absent_removed,
                  ecr_format, waiver_removed, waiver_expired, overload, waiver_ceiling, hard_limit, assumes, derive, calc_moves, rail_order_, d11_inductor, d11_vdd11,
                  new_rail, topology, frame_expired):
        add(build)
    return cases


def ecr_open_in(ecr, ecr_dir):
    return ecr_state(ecr, ecr_dir) in OPEN_ECR


def selftest(ctx):
    """Every rule must fire on a deliberately broken copy of its inputs (and stay quiet on a harmless one): a check that cannot fail proves nothing."""
    ran, skipped, missed = [], [], []
    for c in selftest_cases(ctx):
        if c.run is None:
            skipped.append(c.name)
            continue
        try:
            got = c.run()
        except Exception as e:                                      # noqa: BLE001
            got = Result("selftest", "CRASH", f"{type(e).__name__}: {e}")
        fail_lines = [d for d in got.details if d.startswith("FAIL ")]
        text = " ".join(fail_lines if c.expect == FAIL and fail_lines else [got.msg, *got.details]).lower()   # a marker must sit in a FAIL line, not a WARN
        ok = got.status == c.expect and (c.marker is None or c.marker.lower() in text)
        ran.append((c.name, got.status, ok))
        if not ok:
            missed.append(f"{c.name} -> {got.status} (wanted {c.expect}{f' with {c.marker!r}' if c.marker else ''}): {got.msg[:140]}")
    d = [f"caught: {n} -> {s}" for n, s, ok in ran if ok] + [f"NOT CAUGHT: {m}" for m in missed] + skipped
    if missed:
        return Result("selftest", FAIL, f"{len(missed)} of {len(ran)} rule checks went wrong: {missed[0]}", d)
    if skipped:
        return Result("selftest", WARN, f"{len(ran)} rule checks behave as they must; {len(skipped)} skipped because the design no longer has what they break", d, ["selftest:skipped"])
    return Result("selftest", PASS, f"{len(ran)} of {len(ran)} rule checks behave as they must (each rule fires on a broken copy; a dragged board, reordered rails and loose ECR status formats stay quiet)", d)


# ------------------------------------------------------------------------------------------- driver
def attempt(fn, *args):
    """(value, None) or (None, 'ErrorType: message'): an unreadable input must not become a traceback."""
    try:
        return fn(*args), None
    except Exception as e:                                          # noqa: BLE001
        return None, f"{type(e).__name__}: {e}"


def safely(cid, fn, *args):
    """Run one check; a crash becomes that check's FAIL so the others still report."""
    try:
        return fn(*args)
    except Exception as e:                                          # noqa: BLE001
        return Result(cid, FAIL, f"the check crashed: {type(e).__name__}: {e}")


def run(cfg, do_selftest=True):
    use(cfg)
    inputs, errs = {}, {}
    for key, label, fn, args in (("sh", "shell constants", read_shell, ()), ("sch", "circuit (gen.py)", read_schematic, ()),
                                 ("table", "part_heights.yaml", load_table, ()), ("contract", "pin-contract.yaml", lambda: load_yaml(cfg.contract), ()),
                                 ("budget", "rail-budget.yaml", lambda: load_yaml(cfg.budget), ())):
        inputs[key], err = attempt(fn, *args)
        errs[key] = f"{label}: {err}" if err else None
    problems = validate_contract(inputs["contract"]) if inputs["contract"] is not None else []
    if problems:
        inputs["data"], errs["data"] = None, f"pin-contract.yaml is unusable: {problems[0]}" + (f" (+{len(problems) - 1} more)" if len(problems) > 1 else "")
    elif inputs["contract"] is not None:
        inputs["data"], err = attempt(read_pin_data, inputs["contract"])
        errs["data"] = f"ST pin data: {err}" if err else None
    else:
        inputs["data"], errs["data"] = None, errs["contract"]
    brd, why = None, f"board: no board at {cfg.board}"
    if cfg.board.exists():
        brd, err = attempt(read_board, cfg.board)
        why = f"board: cannot read {cfg.board.name}: {err}" if err else None
    inputs["brd"], errs["brd"] = brd, why
    plan = (("mic-port", check_mic, ("sh", "brd", "table", "sch")), ("switch", check_switch, ("sh", "brd")), ("outline", check_outline, ("sh", "brd")),
            ("inside", check_inside, ("sh", "brd", "table")), ("clamp-bands", check_clamp, ("sh", "brd", "table")), ("heights", check_heights, ("sh", "brd", "sch", "table")),
            ("board-nets", check_board_nets, ("brd", "sch")), ("pins", check_pins, ("contract", "sch", "data")), ("rails", check_rails, ("budget", "sch")),
            ("frame", check_frame, ("sh",)))
    out = []
    for cid, fn, names in plan:
        blocked = [errs[n] or f"{n} unavailable" for n in names if inputs[n] is None]
        out.append(Result(cid, FAIL, "cannot run, input unreadable: " + "; ".join(blocked)) if blocked else safely(cid, fn, *[inputs[n] for n in names]))
    if do_selftest:
        blocked = [errs[n] or f"{n} unavailable" for n in ("sh", "brd", "sch", "table", "contract", "data", "budget") if inputs[n] is None]
        ctx = dict(inputs, board_path=cfg.board)
        out.append(Result("selftest", FAIL, "not run, input unreadable: " + "; ".join(blocked)) if blocked else safely("selftest", selftest, ctx))
    return out


def ensure_env():
    """The tool stack (pcbnew, skidl, yaml) lives in the venv: re-run under it when it exists, else say what to do (exit 2)."""
    missing = [m for m in NEEDED_MODULES if importlib.util.find_spec(m) is None]
    if not missing:
        return
    py = VENV / "bin/python3"
    if py.exists() and Path(sys.prefix).resolve() != VENV.resolve() and not os.environ.get("INTERFACES_REEXEC"):
        os.environ["INTERFACES_REEXEC"] = "1"
        env_sh = REPO / "tools/env.sh"                              # the KiCad library paths SKiDL needs live there
        if env_sh.exists():
            os.execv("/bin/bash", ["bash", "-c", 'source "$0" >/dev/null 2>&1; exec "$@"', str(env_sh), str(py), *sys.argv])
        os.execv(str(py), [str(py), *sys.argv])
    msg = f"{', '.join(missing)} not importable: run `source tools/env.sh` (venv {VENV})"
    print(json.dumps({"checks": [{"id": "env", "status": FAIL, "message": msg}]}) if "--json" in sys.argv else f"FAIL env {msg}")
    sys.exit(2)


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--board", type=Path, help="placed or routed .kicad_pcb to check (default: hw/current.yaml board)")
    ap.add_argument("--root", type=Path, default=REPO, help="re-base every input (a copy of the repo tree) instead of this checkout")
    for key in ("contract", "budget", "heights", "netlist", "shell", "ecr-dir", "mech-dir"):
        ap.add_argument(f"--{key}", type=Path, help=f"override the {key.replace('-', ' ')} input")
    ap.add_argument("--json", action="store_true", help="machine-readable results")
    ap.add_argument("-v", "--verbose", action="count", default=0, help="-v: detail lines under each non-PASS result; -vv: under every result")
    ap.add_argument("--strict", action="store_true", help="treat WARN as FAIL (release gate)")
    ap.add_argument("--no-selftest", action="store_true", help="skip the deliberately-broken-input proofs")
    ap.add_argument("--baseline", type=Path, help="JSON list of accepted WARN ids; any other WARN is a FAIL")
    ap.add_argument("--write-baseline", type=Path, help="write every current WARN id to this file and exit 0")
    return ap


def main(argv=None):
    ensure_env()
    args = build_parser().parse_args(argv)
    cfg = Config(args.root, board=args.board, contract=args.contract, budget=args.budget, heights=args.heights, netlist=args.netlist, shell=args.shell,
                 ecr_dir=args.ecr_dir, mech=args.mech_dir)
    results = run(cfg, not args.no_selftest)
    warn_ids = sorted({w for r in results for w in r.wids})
    if args.write_baseline:
        args.write_baseline.write_text(json.dumps({"written": TODAY.isoformat(), "accepted": warn_ids}, indent=2) + "\n")
        print(f"wrote {len(warn_ids)} accepted warning id(s) to {args.write_baseline}")
        return 0
    if args.baseline:
        try:
            accepted = set(json.loads(args.baseline.read_text())["accepted"])
            new = [w for w in warn_ids if w not in accepted]
            results.append(Result("baseline", FAIL, f"{len(new)} warning(s) not in {args.baseline.name}: " + "; ".join(new[:6]) + (f" (+{len(new) - 6} more)" if len(new) > 6 else ""), new)
                           if new else Result("baseline", PASS, f"all {len(warn_ids)} warning id(s) are in {args.baseline.name}"))
        except (OSError, KeyError, ValueError) as e:
            results.append(Result("baseline", FAIL, f"cannot read {args.baseline}: {type(e).__name__}: {e}"))
    if args.strict:
        for r in results:
            if r.status == WARN:
                r.status, r.msg = FAIL, r.msg + " [--strict]"
    if args.json:
        counts = {s: sum(r.status == s for r in results) for s in (PASS, WARN, FAIL)}
        print(json.dumps({"date": TODAY.isoformat(), "design": getattr(DESIGN, "id", None), "board": str(cfg.board), "netlist": str(cfg.netlist), "shell": str(cfg.shell), "counts": counts, "checks": [r.as_dict() for r in results]}, indent=2))
    else:
        rel_ = lambda p: str(p.relative_to(cfg.root)) if p.is_relative_to(cfg.root) else str(p)  # noqa: E731
        print(f"INFO design {getattr(DESIGN, 'id', '?')}: board {rel_(cfg.board)}, netlist {rel_(cfg.netlist)}, shell {rel_(cfg.shell)}")
        for r in results:
            print(f"{r.status} {r.id} {r.msg}")
            if args.verbose >= 2 or (args.verbose and r.status != PASS):
                for line in r.details:
                    print(f"     - {line}")
    return 1 if any(r.status == FAIL for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
