"""Readable KiCad schematic of the pod board, generated from the netlist (gen.py stays the source of truth).

    source tools/env.sh && python3 hw/pod/sch.py            # -> hw/pod/sch/*.kicad_sch, pod.pdf, png/*.png
    python3 hw/pod/sch.py --check                            # regenerate + netlist export + exact connectivity proof

Why generated: gen.py (SKiDL) emits a netlist, not a drawing. This script lays the same netlist out on five functional
A4 sheets (dock, power, MCU, mic, output), with real KiCad library symbols, power symbols on the rails, short wires
where the parts sit side by side and net labels only where a wire would cross something. Every run proves the
drawing is the same circuit: kicad-cli exports the schematic's netlist and
.claude/skills/schematic-humanizer/scripts/compare_connectivity.py must report it identical to hw/pod/pod.net
(components, values, footprints, every net name and every ref/pin). Plain-language boxes on each sheet explain each
block for a non-engineer. Owner 2026-10-02: "we do want schematics too" (next to the block flowchart).
Placement tables (SHEETS) are hand-authored on the 1.27 mm grid; everything else is computed.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
OUT = HERE / "sch"
NETLIST = HERE / "pod.net"
KSYM = Path("/usr/share/kicad/symbols")
LIBS = {"Device": KSYM / "Device.kicad_sym", "Connector": KSYM / "Connector.kicad_sym",
        "MCU_ST_STM32U5": KSYM / "MCU_ST_STM32U5.kicad_sym", "Sensor_Audio": KSYM / "Sensor_Audio.kicad_sym",
        "power": KSYM / "power.kicad_sym", "lcsc": REPO / "hw/lib/lcsc/lcsc.kicad_sym"}
FENCE = ["systemd-run", "--user", "--scope", "--quiet", "-p", "MemoryMax=3G", "-p", "MemorySwapMax=0"]
G = 1.27
NS = uuid.UUID("6b1f4c2e-3d1a-4f0b-9b7e-2a5c0d9e8f11")


def uid(*parts) -> str:
    return str(uuid.uuid5(NS, "/".join(map(str, parts))))


# ------------------------------------------------------------------ S-expressions
class Q(str):
    """A quoted string atom."""


_TOK = re.compile(r'\s*(?:(\()|(\))|"((?:[^"\\]|\\.)*)"|([^\s()"]+))')


def sparse(text: str):
    stack = [[]]
    for m in _TOK.finditer(text):
        o, c, q, a = m.groups()
        if o:
            stack.append([])
        elif c:
            x = stack.pop()
            stack[-1].append(x)
        elif q is not None:
            stack[-1].append(Q(q.replace('\\"', '"').replace("\\\\", "\\")))
        elif a is not None:
            stack[-1].append(a)
    return stack[0][0]


def sdump(x, ind=0) -> str:
    if isinstance(x, Q):
        return '"' + x.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        return fmt(x)
    if not isinstance(x, list):
        return str(x)
    if all(not isinstance(y, list) for y in x):
        return "(" + " ".join(sdump(y) for y in x) + ")"
    head = [sdump(y) for y in x[:1]]
    i = 1
    while i < len(x) and not isinstance(x[i], list):
        head.append(sdump(x[i]))
        i += 1
    pad = "\t" * (ind + 1)
    body = "".join("\n" + pad + sdump(y, ind + 1) for y in x[i:])
    return "(" + " ".join(head) + body + "\n" + "\t" * ind + ")"


def fmt(v: float) -> str:
    v = round(float(v), 4)
    return str(int(v)) if v == int(v) else f"{v:.4f}".rstrip("0").rstrip(".")


def kids(node, tag):
    return [x for x in node if isinstance(x, list) and x and x[0] == tag]


def kid(node, tag):
    k = kids(node, tag)
    return k[0] if k else None


# ------------------------------------------------------------------ netlist
@dataclass
class Comp:
    ref: str
    value: str
    footprint: str
    lib: str
    part: str
    fields: dict


def load_netlist(path=NETLIST):
    t = sparse(path.read_text())
    comps = {}
    for c in kids(kid(t, "components"), "comp"):
        ref = kid(c, "ref")[1]
        ls = kid(c, "libsource")
        flds = {kid(f, "name")[1]: (f[2] if len(f) > 2 else "") for f in kids(kid(c, "fields") or [], "field")}
        comps[ref] = Comp(ref, kid(c, "value")[1], kid(c, "footprint")[1] if kid(c, "footprint") else "",
                          kid(ls, "lib")[1], kid(ls, "part")[1], flds)
    nets = {}
    for n in kids(kid(t, "nets"), "net"):
        nets[kid(n, "name")[1]] = [(kid(x, "ref")[1], kid(x, "pin")[1]) for x in kids(n, "node")]
    return comps, nets


def canonical(comps, nets) -> dict:
    return {"schema": "schematic-connectivity-v1",
            "components": [{"ref": r, "value": c.value, "footprint": c.footprint, "device": f"{c.lib}:{c.part}"}
                           for r, c in sorted(comps.items())],
            "nets": [{"name": n, "pins": [{"ref": r, "pin": p} for r, p in sorted(ps)]} for n, ps in sorted(nets.items())]}


# ------------------------------------------------------------------ symbols
_LIBCACHE: dict = {}


def lib_symbols(lib: str) -> dict:
    if lib not in _LIBCACHE:
        t = sparse(LIBS[lib].read_text())
        _LIBCACHE[lib] = {x[1]: x for x in kids(t, "symbol")}
    return _LIBCACHE[lib]


def fet_pair_symbol():
    """PMCXB290UE (gen.py defines it in SKiDL, no library symbol): one box, P half on top, N half below, pins as the
    datasheet names them; drains of each half stacked (D_P 3+8, D_N 6+7)."""
    def pin(num, name, x, y, ang, hide=False):
        p = ["pin", "passive", "line", ["at", x, y, ang], ["length", 2.54],
             ["name", Q(name), ["effects", ["font", ["size", 1.016, 1.016]]]],
             ["number", Q(num), ["effects", ["font", ["size", 1.016, 1.016]]]]]
        if hide:
            p.insert(3, ["hide", "yes"])
        return p
    body = ["symbol", Q("PMCXB290UE_0_1"),
            ["rectangle", ["start", -5.08, 7.62], ["end", 5.08, -7.62], ["stroke", ["width", 0.254], ["type", "default"]],
             ["fill", ["type", "background"]]],
            ["polyline", ["pts", ["xy", -5.08, -1.27], ["xy", 5.08, -1.27]], ["stroke", ["width", 0.1524], ["type", "dash"]], ["fill", ["type", "none"]]]]
    pins = ["symbol", Q("PMCXB290UE_1_1"),
            pin("4", "S_P", 0, 10.16, 270), pin("5", "G_P", -7.62, 2.54, 0), pin("3", "D_P", 7.62, 2.54, 180),
            pin("8", "D_P", 7.62, 2.54, 180, hide=True), pin("2", "G_N", -7.62, -5.08, 0), pin("6", "D_N", 7.62, -5.08, 180),
            pin("7", "D_N", 7.62, -5.08, 180, hide=True), pin("1", "S_N", 0, -10.16, 90)]
    prop = lambda k, v, y, hide=False: ["property", Q(k), Q(v), ["at", 0, y, 0],  # noqa: E731
                                        ["effects", ["font", ["size", 1.27, 1.27]]] + ([["hide", "yes"]] if hide else [])]
    return ["symbol", Q("PMCXB290UE"), ["pin_names", ["offset", 0.508]], ["exclude_from_sim", "no"], ["in_bom", "yes"],
            ["on_board", "yes"], prop("Reference", "Q", 11.43), prop("Value", "PMCXB290UE", -11.43),
            prop("Footprint", "", 0, True), prop("Datasheet", "", 0, True),
            prop("Description", "Nexperia 20 V complementary N+P MOSFET pair, DFN1010B-6", 0, True), body, pins]


def get_symbol(lib: str, name: str):
    """Flattened library symbol (resolves `extends`) as an S-expression list."""
    if lib == "NO_LIB" and name == "PMCXB290UE":
        return fet_pair_symbol()
    syms = lib_symbols(lib)
    s = syms[name]
    ext = kid(s, "extends")
    if ext is None:
        return s
    parent = get_symbol(lib, ext[1])
    out = [x for x in s if not (isinstance(x, list) and x and x[0] == "extends")]
    for u in kids(parent, "symbol"):
        u2 = list(u)
        u2[1] = Q(u[1].replace(ext[1], name, 1))
        out.append(u2)
    return out


@dataclass
class LibPin:
    num: str
    name: str
    etype: str
    x: float
    y: float
    ang: float
    length: float


def unit_ok(uname: str) -> bool:
    m = re.search(r"_(\d+)_(\d+)$", uname)
    return m is None or (m.group(1) in ("0", "1") and m.group(2) in ("0", "1"))


def sym_pins(sym) -> list[LibPin]:
    out = []
    for u in kids(sym, "symbol"):
        if not unit_ok(u[1]):
            continue
        for p in kids(u, "pin"):
            at = kid(p, "at")
            out.append(LibPin(kid(p, "number")[1], kid(p, "name")[1], p[1], float(at[1]), float(at[2]),
                              float(at[3]) if len(at) > 3 else 0.0, float(kid(p, "length")[1])))
    return out


def sym_body(sym):
    """Bounding box of the drawn body (lib coords, y up), pins excluded."""
    xs, ys = [], []
    for u in kids(sym, "symbol"):
        if not unit_ok(u[1]):
            continue
        for g in u:
            if not isinstance(g, list) or not g:
                continue
            if g[0] == "rectangle":
                for k in ("start", "end"):
                    xs.append(float(kid(g, k)[1]))
                    ys.append(float(kid(g, k)[2]))
            elif g[0] in ("polyline", "bezier"):
                for xy in kids(kid(g, "pts"), "xy"):
                    xs.append(float(xy[1]))
                    ys.append(float(xy[2]))
            elif g[0] == "circle":
                cx, cy, r = float(kid(g, "center")[1]), float(kid(g, "center")[2]), float(kid(g, "radius")[1])
                xs += [cx - r, cx + r]
                ys += [cy - r, cy + r]
            elif g[0] == "arc":
                for k in ("start", "mid", "end"):
                    xs.append(float(kid(g, k)[1]))
                    ys.append(float(kid(g, k)[2]))
    if not xs:
        return (0.0, 0.0, 0.0, 0.0)
    return (min(xs), min(ys), max(xs), max(ys))


def xf(px, py, rot, mirror):
    """lib (y up) -> schematic offset (y down) for a symbol at angle `rot` (deg, CCW on screen), mirror 'x'|'y'|None."""
    a = math.radians(rot)
    rx = px * math.cos(a) - py * math.sin(a)
    ry = -(px * math.sin(a) + py * math.cos(a))
    if mirror == "y":                      # KiCad mirrors after rotating (verified with a netlist export, 2026-10-02)
        rx = -rx
    elif mirror == "x":
        ry = -ry
    return (round(rx, 4), round(ry, 4))


def dir_angle(d) -> int:
    """Schematic direction vector -> label angle (0 right, 90 up, 180 left, 270 down)."""
    dx, dy = d
    if abs(dx) > abs(dy):
        return 0 if dx > 0 else 180
    return 270 if dy > 0 else 90


@dataclass
class Placed:
    ref: str
    lib_id: str
    sym: list
    at: tuple
    rot: int = 0
    mirror: str | None = None
    value: str = ""
    footprint: str = ""
    fields: dict = field(default_factory=dict)
    power: bool = False
    ref_at: tuple | None = None      # (dx, dy, justify) override, relative to `at`
    val_at: tuple | None = None
    val_hide: bool = False

    def pins(self):
        out = []
        for p in sym_pins(self.sym):
            ox, oy = xf(p.x, p.y, self.rot, self.mirror)
            a = math.radians(p.ang)
            dx, dy = xf(-math.cos(a), -math.sin(a), self.rot, self.mirror)
            inner = xf(p.x + p.length * math.cos(a), p.y + p.length * math.sin(a), self.rot, self.mirror)
            out.append((p, (round(self.at[0] + ox, 3), round(self.at[1] + oy, 3)), (round(dx), round(dy)),
                        (round(self.at[0] + inner[0], 3), round(self.at[1] + inner[1], 3))))
        return out

    def body(self):
        x0, y0, x1, y1 = sym_body(self.sym)
        pts = [xf(x, y, self.rot, self.mirror) for x in (x0, x1) for y in (y0, y1)]
        xs = [self.at[0] + p[0] for p in pts]
        ys = [self.at[1] + p[1] for p in pts]
        return (min(xs), min(ys), max(xs), max(ys))


def effects(size=1.27, justify=None, hide=False, bold=False):
    font = ["font", ["size", size, size]]
    if bold:
        font.append(["bold", "yes"])
    e = ["effects", font]
    if justify:
        e.append(["justify", *justify.split()])
    if hide:
        e.append(["hide", "yes"])
    return e


@dataclass
class Sheet:
    key: str
    name: str
    page: int
    parts: list = field(default_factory=list)
    wires: list = field(default_factory=list)
    labels: list = field(default_factory=list)       # (text, x, y, angle, kind)
    nocon: list = field(default_factory=list)
    junctions: list = field(default_factory=list)
    notes: list = field(default_factory=list)        # (x, y, w, h, title, body)
    texts: list = field(default_factory=list)        # (text, x, y, size)

    @property
    def file(self):
        return f"{self.key}.kicad_sch"

    def sexp(self, root_uuid: str, sheet_uuid: str, title: str, date: str):
        u = uid(self.key)
        libs, seen = [], set()
        for p in self.parts:
            if p.lib_id in seen:
                continue
            seen.add(p.lib_id)
            s = list(p.sym)
            s[1] = Q(p.lib_id)
            libs.append(s)
        out = ["kicad_sch", ["version", 20250114], ["generator", Q("pod-sch.py")], ["generator_version", Q("10.0")],
               ["uuid", Q(u)], ["paper", Q("A4")],
               ["title_block", ["title", Q(title)], ["date", Q(date)], ["rev", Q("F")], ["company", Q("Stereo Ultrasound")],
                ["comment", 1, Q("Generated by hw/pod/sch.py from hw/pod/pod.net (gen.py). Do not edit by hand.")],
                ["comment", 2, Q("Plain-language boxes explain each block; part numbers and values are on the symbols.")]],
               ["lib_symbols", *libs]]
        for (x1, y1), (x2, y2) in self.wires:
            out.append(["wire", ["pts", ["xy", x1, y1], ["xy", x2, y2]], ["stroke", ["width", 0], ["type", "default"]],
                        ["uuid", Q(uid(self.key, "w", x1, y1, x2, y2))]])
        for (x, y) in self.junctions:
            out.append(["junction", ["at", x, y], ["diameter", 0], ["color", 0, 0, 0, 0], ["uuid", Q(uid(self.key, "j", x, y))]])
        for (x, y) in self.nocon:
            out.append(["no_connect", ["at", x, y], ["uuid", Q(uid(self.key, "nc", x, y))]])
        for (text, x, y, ang, kind) in self.labels:
            just = "right" if ang in (180, 270) else "left"     # 90 reads upward from the anchor, 270 downward
            if kind == "global":
                out.append(["global_label", Q(text), ["shape", "bidirectional"], ["at", x, y, ang], ["fields_autoplaced", "yes"],
                            effects(justify=just), ["uuid", Q(uid(self.key, "gl", text, x, y))],
                            ["property", Q("Intersheetrefs"), Q("${INTERSHEET_REFS}"), ["at", x, y, 0], effects(justify=just, hide=True)]])
            else:
                out.append(["label", Q(text), ["at", x, y, ang], effects(justify=just + " bottom"), ["uuid", Q(uid(self.key, "l", text, x, y))]])
        for (text, x, y, size) in self.texts:
            out.append(["text", Q(text), ["exclude_from_sim", "no"], ["at", x, y, 0], effects(size=size, justify="left bottom", bold=True),
                        ["uuid", Q(uid(self.key, "t", text))]])
        for (x, y, w, h, head, body) in self.notes:
            out.append(["text_box", Q(f"{head}\n{body}" if body else head), ["exclude_from_sim", "no"], ["at", x, y, 0], ["size", w, h],
                        ["margins", 0.9525, 0.9525, 0.9525, 0.9525],
                        ["stroke", ["width", 0], ["type", "default"]], ["fill", ["type", "color"], ["color", 255, 248, 225, 1]],
                        effects(size=1.524, justify="left top"), ["uuid", Q(uid(self.key, "tb", head))]])
        for p in self.parts:
            out.append(self.symbol_inst(p, root_uuid, sheet_uuid))
        out.append(["embedded_fonts", "no"])
        return out

    def symbol_inst(self, p: Placed, root_uuid, sheet_uuid):
        x, y = p.at
        s = ["symbol", ["lib_id", Q(p.lib_id)], ["at", x, y, p.rot]]
        if p.mirror:
            s.append(["mirror", p.mirror])
        s += [["unit", 1], ["exclude_from_sim", "no"], ["in_bom", "no" if p.power else "yes"], ["on_board", "yes"],
              ["dnp", "no"], ["uuid", Q(uid(self.key, "sym", p.ref))]]
        fa = 90 if p.rot in (90, 270) else 0       # KiCad shows a field at (its angle + the symbol's): this keeps text level

        def fld(txt, off):
            dx, dy, j = off if off else (0, 0, None)
            if j and (fa or p.mirror or p.rot == 180):   # rotated/mirrored symbols transform justification: centre instead
                w = len(txt) * CH
                dx += w / 2 if j == "left" else -w / 2
                j = None
            return x + dx, y + dy, j
        rx, ry, rj = fld(p.ref, p.ref_at)
        vx, vy, vj = fld(p.value, p.val_at)
        s.append(["property", Q("Reference"), Q(p.ref), ["at", rx, ry, fa], effects(justify=rj, hide=p.power)])
        s.append(["property", Q("Value"), Q(p.value), ["at", vx, vy, fa], effects(justify=vj, hide=p.val_hide)])
        s.append(["property", Q("Footprint"), Q(p.footprint), ["at", x, y, fa], effects(hide=True)])
        s.append(["property", Q("Datasheet"), Q(""), ["at", x, y, fa], effects(hide=True)])
        for k, v in p.fields.items():
            s.append(["property", Q(k), Q(v), ["at", x, y, 0], effects(hide=True)])
        for pin, *_ in p.pins():
            s.append(["pin", Q(pin.num), ["uuid", Q(uid(self.key, p.ref, "pin", pin.num))]])
        s.append(["instances", ["project", Q("pod"), ["path", Q(f"/{root_uuid}/{sheet_uuid}"), ["reference", Q(p.ref)], ["unit", 1]]]])
        return s


def write_root(sheets, title, date):
    root = uid("root")
    out = ["kicad_sch", ["version", 20250114], ["generator", Q("pod-sch.py")], ["generator_version", Q("10.0")], ["uuid", Q(root)],
           ["paper", Q("A4")], ["title_block", ["title", Q(title)], ["date", Q(date)], ["rev", Q("F")], ["company", Q("Stereo Ultrasound")]],
           ["lib_symbols"]]
    for i, sh in enumerate(sheets):
        x, y = 25.4 + (i % 3) * 88.9, 40.64 + (i // 3) * 63.5
        su = uid("sheet", sh.key)
        out.append(["sheet", ["at", x, y], ["size", 76.2, 38.1], ["exclude_from_sim", "no"], ["in_bom", "yes"], ["on_board", "yes"],
                    ["dnp", "no"], ["fields_autoplaced", "yes"], ["stroke", ["width", 0.1524], ["type", "solid"]],
                    ["fill", ["color", 0, 0, 0, 0.0]], ["uuid", Q(su)],
                    ["property", Q("Sheetname"), Q(f"{sh.page - 1} {sh.name}"), ["at", x, y - 0.7, 0], effects(size=1.524, justify="left bottom")],
                    ["property", Q("Sheetfile"), Q(sh.file), ["at", x, y + 38.7, 0], effects(justify="left top")],
                    ["instances", ["project", Q("pod"), ["path", Q(f"/{root}"), ["page", Q(str(sh.page))]]]]])
    note = ("HOW TO READ THIS\n"
            "Each box above is one page. Power arrives on page 1 (the dock), is stored and cleaned on page 2, and feeds the "
            "brain on page 3. Sound comes in on page 4 (the microphone) and goes out on page 5 (the speaker driver).\n"
            "Flag-shaped labels with the same name are the same wire, even on different pages. Arrow and bar symbols "
            "(+3V0, VSYS, VBAT, GND) are power rails. Yellow boxes explain each block in plain words.")
    out.append(["text_box", Q(note), ["exclude_from_sim", "no"], ["at", 25.4, 160.0, 0], ["size", 152.4, 22.86],
                ["margins", 0.9525, 0.9525, 0.9525, 0.9525], ["stroke", ["width", 0], ["type", "default"]],
                ["fill", ["type", "color"], ["color", 255, 248, 225, 1]], effects(size=1.524, justify="left top"),
                ["uuid", Q(uid("root", "note"))]])
    out.append(["sheet_instances", ["path", Q("/"), ["page", Q("1")]]])
    out.append(["embedded_fonts", "no"])
    return root, out


# ------------------------------------------------------------------ geometry helpers
EPS = 0.05
CH = 1.05            # approx. width of one 1.27 mm stroke-font character, mm


def snap(v):
    return round(round(v / G) * G, 3)


def rect_hit_seg(r, a, b, inflate=0.2):
    """Axis-aligned segment a-b passes through the interior of rect r (inflated)."""
    x0, y0, x1, y1 = r[0] - inflate, r[1] - inflate, r[2] + inflate, r[3] + inflate
    (ax, ay), (bx, by) = a, b
    if abs(ay - by) < EPS:
        lo, hi = sorted((ax, bx))
        return y0 < ay < y1 and lo < x1 and hi > x0
    lo, hi = sorted((ay, by))
    return x0 < ax < x1 and lo < y1 and hi > y0


def on_seg(p, a, b, interior=True):
    (px, py), (ax, ay), (bx, by) = p, a, b
    if abs(ay - by) < EPS and abs(py - ay) < EPS:
        lo, hi = sorted((ax, bx))
        return (lo + EPS < px < hi - EPS) if interior else (lo - EPS <= px <= hi + EPS)
    if abs(ax - bx) < EPS and abs(px - ax) < EPS:
        lo, hi = sorted((ay, by))
        return (lo + EPS < py < hi - EPS) if interior else (lo - EPS <= py <= hi + EPS)
    return False


def same(p, q):
    return abs(p[0] - q[0]) < EPS and abs(p[1] - q[1]) < EPS


def seg_relation(a, b, c, d):
    """'none' | 'cross' (perpendicular, interiors) | 'touch' (any shared point otherwise) | 'overlap' (collinear)."""
    ah = abs(a[1] - b[1]) < EPS
    ch = abs(c[1] - d[1]) < EPS
    if ah == ch:
        if ah and abs(a[1] - c[1]) < EPS:
            lo1, hi1 = sorted((a[0], b[0]))
            lo2, hi2 = sorted((c[0], d[0]))
        elif not ah and abs(a[0] - c[0]) < EPS:
            lo1, hi1 = sorted((a[1], b[1]))
            lo2, hi2 = sorted((c[1], d[1]))
        else:
            return "none"
        ov = min(hi1, hi2) - max(lo1, lo2)
        if ov > EPS:
            return "overlap"
        return "touch" if ov > -EPS else "none"
    h1, h2, v1, v2 = (a, b, c, d) if ah else (c, d, a, b)
    x, y = v1[0], h1[1]
    lo_h, hi_h = sorted((h1[0], h2[0]))
    lo_v, hi_v = sorted((v1[1], v2[1]))
    if not (lo_h - EPS <= x <= hi_h + EPS and lo_v - EPS <= y <= hi_v + EPS):
        return "none"
    if lo_h + EPS < x < hi_h - EPS and lo_v + EPS < y < hi_v - EPS:
        return "cross"
    return "touch"


def text_rect(text, x, y, ang, size=1.27, pad=0.12, kind="global"):
    """Rect a label's text occupies, given its connection point and angle (global labels add the flag outline).
    Widths measured on KiCad 10's rendering: ~1.22 mm/char + 2.6 mm of flag for a global label, ~1.1 mm/char local."""
    w = len(text) * 1.22 + 2.6 if kind == "global" else len(text) * 1.1 + 0.6
    h = size + 0.6
    if ang == 0:
        return (x, y - h / 2 - pad, x + w, y + h / 2 + pad)
    if ang == 180:
        return (x - w, y - h / 2 - pad, x, y + h / 2 + pad)
    if ang == 90:
        return (x - h / 2 - pad, y - w, x + h / 2 + pad, y)
    return (x - h / 2 - pad, y, x + h / 2 + pad, y + w)


def rects_overlap(r, s, gap=0.0):
    return r[0] < s[2] + gap and s[0] < r[2] + gap and r[1] < s[3] + gap and s[1] < r[3] + gap


# ------------------------------------------------------------------ builder: placement, power symbols, routing, labels
POWER = {"GND": ("GND", True), "+3V0": ("+3V0", False), "VBUS": ("VBUS", False),
         "VSYS": ("VCC", False), "VBAT": ("VCC", False), "DOCK_VBUS": ("VCC", False)}   # net -> (power-lib symbol, is-ground)
PIN_POWER = {"GND", "+3V0"}      # a symbol at every pin; the other rails are wired on each sheet and named by one symbol
_PWR_N = [0]


@dataclass
class PinRec:
    ref: str
    num: str
    name: str
    pt: tuple
    out: tuple
    inner: tuple
    net: str | None


class Builder:
    def __init__(self, sheet: Sheet, comps, pin_net, cross_nets, warn):
        self.sh, self.comps, self.pin_net, self.cross, self.warn = sheet, comps, pin_net, cross_nets, warn
        self.pins: list[PinRec] = []
        self.rects: list[tuple] = []          # (rect, tag)
        self.wires: list[tuple] = []          # (a, b, net)
        self.lab_rects: list[tuple] = []
        self.named: dict[str, int] = {}
        self.label_only: set = set()          # "REF" or "REF.PIN": never wired, always named by a label of its own
        self.text_keep: list[tuple] = []      # pin numbers along IC pins: labels keep off them, wires may pass

    # ---------------- placement
    def place(self, ref, gx, gy, rot=0, mirror=None, ref_at=None, val_at=None):
        c = self.comps[ref]
        sym = get_symbol(c.lib, c.part)
        p = Placed(ref, f"{c.lib}:{c.part}", sym, (round(gx * G, 3), round(gy * G, 3)), rot, mirror, c.value, c.footprint,
                   {k: v for k, v in c.fields.items() if k in ("LCSC",)})
        bx0, by0, bx1, by1 = p.body()
        cx = (bx0 + bx1) / 2
        two_pin = len({pr.num for pr, *_ in p.pins()}) <= 2
        if ref_at is None:
            if two_pin and (by1 - by0) > (bx1 - bx0):                    # vertical 2-pin: text to the right
                ref_at = (bx1 - p.at[0] + 1.0, -0.6, "left")
                val_at = val_at or (bx1 - p.at[0] + 1.0, 1.9, "left")
            elif two_pin:                                                # horizontal 2-pin: text above / below
                ref_at = (cx - p.at[0], by0 - p.at[1] - 1.6, None)
                val_at = val_at or (cx - p.at[0], by1 - p.at[1] + 1.9, None)
            else:                                                        # IC: above / below the body
                ref_at = (bx0 - p.at[0], by0 - p.at[1] - 1.4, "left")
                val_at = val_at or (bx0 - p.at[0], by1 - p.at[1] + 2.2, "left")
        p.ref_at, p.val_at = ref_at, val_at or (0, 2.5, None)
        self.sh.parts.append(p)
        self.rects.append(((bx0, by0, bx1, by1), f"body {ref}"))
        for txt, (dx, dy, j) in ((ref, p.ref_at), (c.value, p.val_at)):
            self.rects.append((self._field_rect(txt, p.at[0] + dx, p.at[1] + dy, j), f"text {ref}"))
        for pr, pt, out, inner in p.pins():
            self.pins.append(PinRec(ref, pr.num, pr.name, pt, out, inner, self.pin_net.get((ref, pr.num))))
            if not two_pin:
                x0, x1 = sorted((pt[0], inner[0]))
                y0, y1 = sorted((pt[1], inner[1]))
                self.text_keep.append((x0 - (1.1 if out[0] == 0 else -0.3), y0 - (1.1 if out[1] == 0 else -0.3),
                                       x1 + (1.1 if out[0] == 0 else -0.3), y1 + (1.1 if out[1] == 0 else -0.3)))
        return p

    @staticmethod
    def _field_rect(txt, x, y, j):
        w = len(txt) * CH
        x0 = x if j == "left" else (x - w if j == "right" else x - w / 2)
        return (x0, y - 0.8, x0 + w, y + 0.8)

    def note(self, gx, gy, gw, gh, head, body=""):
        r = (gx * G, gy * G, (gx + gw) * G, (gy + gh) * G)
        self.sh.notes.append((r[0], r[1], gw * G, gh * G, head, body))
        self.rects.append((r, "note"))

    def title(self, text, gx, gy, size=2.0):
        self.sh.texts.append((text, gx * G, gy * G, size))
        self.rects.append(((gx * G, gy * G - size - 0.3, gx * G + len(text) * CH * size / 1.27 * 1.05, gy * G + 0.3), "title"))

    # ---------------- validity
    def seg_ok(self, a, b, net, ends, allow_cross=True):
        if same(a, b):
            return True
        for r, tag in self.rects + self.lab_rects:
            if rect_hit_seg(r, a, b):
                return False
        for pr in self.pins:
            atend = any(same(pr.pt, e) for e in ends)
            rel = seg_relation(a, b, pr.pt, pr.inner)
            if rel == "overlap" or rel == "cross":
                return False
            if rel == "touch":
                hit_pt = pr.pt if (on_seg(pr.pt, a, b, interior=False)) else None
                if not (atend and hit_pt is not None and (same(pr.pt, a) or same(pr.pt, b))):
                    return False
        for (c, d, n) in self.wires:
            rel = seg_relation(a, b, c, d)
            if rel == "none":
                continue
            if n != net:
                if rel != "cross" or not allow_cross:
                    return False
                continue
            if rel != "touch":
                return False
            touch_ok = any(same(e, x) for e in ends for x in (a, b)) and any(on_seg(e, c, d, interior=False) for e in ends)
            if not touch_ok:
                return False
        return True

    def route_ok(self, pts, net):
        ends = (pts[0], pts[-1])
        return all(self.seg_ok(pts[i], pts[i + 1], net, ends) for i in range(len(pts) - 1))

    def wire_ends_at(self, p):
        return sum(1 for (c, d, n) in self.wires if same(c, p) or same(d, p))

    def add_route(self, pts, net):
        end = pts[-1]
        for i, (c, d, n) in enumerate(list(self.wires)):          # T onto a wire interior: split it there
            if n == net and on_seg(end, c, d, interior=True):
                self.wires[i] = (c, end, n)
                self.wires.append((end, d, n))
                break
        for i in range(len(pts) - 1):
            if not same(pts[i], pts[i + 1]):
                self.wires.append((pts[i], pts[i + 1], net))

    # ---------------- power symbols
    def power_symbols(self):
        done = set()
        by_part: dict = {}
        for pr in self.pins:
            if pr.net in PIN_POWER:
                by_part.setdefault((pr.ref, pr.net, pr.out), []).append(pr)
        for (ref, net, out), prs in by_part.items():
            pts = []
            for pr in prs:
                if not any(same(pr.pt, q) for q in pts):
                    pts.append(pr.pt)
            pts.sort()
            # adjacent pins on one edge share a bar and one symbol
            groups, cur = [], [pts[0]]
            for q in pts[1:]:
                prev = cur[-1]
                adj = (abs(q[0] - prev[0]) < 2.6 * G and abs(q[1] - prev[1]) < EPS) if out[1] != 0 else \
                      (abs(q[1] - prev[1]) < 2.6 * G and abs(q[0] - prev[0]) < EPS)
                if adj:
                    cur.append(q)
                else:
                    groups.append(cur)
                    cur = [q]
            groups.append(cur)
            for grp in groups:
                self._power_group(grp, net, out)
                done.add((ref, net))

    def _power_group(self, grp, net, out):
        is_gnd = POWER[net][1]
        q0 = grp[0]
        dense = any(same(pr.pt, q0) and pr.ref in self.label_only for pr in self.pins) or \
            sum(1 for pr in self.pins if pr.out == out and not same(pr.pt, q0)
                    and abs((pr.pt[1] - q0[1]) if out[1] == 0 else (pr.pt[0] - q0[0])) < 2.6 * G
                    and abs((pr.pt[0] - q0[0]) if out[1] == 0 else (pr.pt[1] - q0[1])) < EPS) > 0
        want = (0, 1) if is_gnd else (0, -1)                    # GND hangs down, rails stand up
        cands = []
        if len(grp) == 1:
            q = grp[0]
            mv = lambda p, d, k: (round(p[0] + d[0] * k * G, 3), round(p[1] + d[1] * k * G, 3))  # noqa: E731
            if out == want:
                cands += [([], q, out)] + [([(q, mv(q, out, k))], mv(q, out, k), out) for k in (2, 3, 4)]
            elif out[1] == 0 and not dense:
                for k in (2, 3, 4, 6):
                    a = mv(q, out, k)
                    for j in (2, 3):
                        b = mv(a, want, j)
                        cands.append(([(q, a), (a, b)], b, want))
            cands += [([(q, mv(q, out, k))], mv(q, out, k), out) for k in (2, 3, 4, 6)]
        else:
            for k in (2, 3, 4):
                ends = [(round(q[0] + out[0] * k * G, 3), round(q[1] + out[1] * k * G, 3)) for q in grp]
                segs = [(q, e) for q, e in zip(grp, ends)] + [(ends[i], ends[i + 1]) for i in range(len(ends) - 1)]
                cands.append((segs, ends[len(ends) // 2], out))
        self.power_at(net, cands, f"{grp[0]}")

    def power_at(self, net, cands, where):
        """Place one power symbol for `net` using the first clash-free candidate (wire segments, anchor, direction)."""
        lib_name, is_gnd = POWER[net]
        pick = None
        for segs, anchor, d in cands:
            sym = self._power_placed(net, lib_name, is_gnd, anchor, d)
            b = sym.body()
            srect = (b[0] - 0.05, b[1] - 0.05, b[2] + 0.05, b[3] + 0.05)
            vrect = self._power_value_rect(sym, net, is_gnd)
            clash = any(rects_overlap(srect, r) or (vrect and rects_overlap(vrect, r)) for r, _ in self.rects + self.lab_rects)
            clash = clash or any(rect_hit_seg(srect, c, dd, 0) for (c, dd, n) in self.wires if n != net)
            if not clash and all(self.seg_ok(a, bb, net, (a, bb)) for a, bb in segs):
                pick = (segs, sym, srect, vrect)
                break
        if pick is None:                                    # last resort: symbol on the pin itself, no stub
            segs, anchor, d = cands[0]
            anchor = segs[0][0] if segs else anchor
            segs = []
            sym = self._power_placed(net, lib_name, is_gnd, anchor, d)
            b = sym.body()
            pick = (segs, sym, b, self._power_value_rect(sym, net, is_gnd))
            self.warn.append(f"{self.sh.key}: power symbol {net} near {where} placed with a clash")
        segs, sym, srect, vrect = pick
        for a, bb in segs:
            if not same(a, bb):
                self.wires.append((a, bb, net))
        sym.val_hide = is_gnd
        self.sh.parts.append(sym)
        self.rects.append((srect, f"pwr {net}"))
        if vrect:
            self.rects.append((vrect, f"pwrtext {net}"))
        return pick is not None

    def _power_placed(self, net, lib_name, is_gnd, anchor, out):
        _PWR_N[0] += 1
        # rotation so the symbol points away from the pin (GND graphic hangs below its pin, rails stand above)
        rot = {(0, 1): 0, (0, -1): 180, (1, 0): 90, (-1, 0): 270}[out] if is_gnd else {(0, -1): 0, (0, 1): 180, (1, 0): 270, (-1, 0): 90}[out]
        sym = get_symbol("power", lib_name)
        p = Placed(f"#PWR{_PWR_N[0]:03d}", f"power:{lib_name}", sym, anchor, rot, None, net, "", {}, power=True)
        far = xf(0, -3.81 if is_gnd else 3.6, rot, None)
        just = None if out[0] == 0 else ("left" if out[0] > 0 else "right")
        if out[0] != 0:
            far = (far[0] + (0.8 if out[0] > 0 else -0.8), far[1])
        p.ref_at = (0, 0, None)
        p.val_at = (far[0], far[1], just)
        return p

    def _power_value_rect(self, sym, net, is_gnd):
        if is_gnd:
            return None
        return self._field_rect(net, sym.at[0] + sym.val_at[0], sym.at[1] + sym.val_at[1], sym.val_at[2])

    def finish_power_values(self):
        for p in self.sh.parts:
            if p.power and p.value == "GND":
                p.val_hide = True

    # ---------------- signal routing
    def _lonely(self, pr):
        return pr.ref in self.label_only or f"{pr.ref}.{pr.num}" in self.label_only

    def route_net(self, net, kind):
        pts, solo = [], []
        for pr in self.pins:
            if pr.net == net and not any(same(pr.pt, q) for q in pts + solo):
                (solo if self._lonely(pr) else pts).append(pr.pt)
        if not pts:
            return [[q] for q in solo]
        trees = [[pts[0]]]
        remaining = pts[1:]
        while remaining:
            best = None
            tree = trees[-1]
            verts = list(tree) + [e for (c, d, n) in self.wires if n == net for e in (c, d)]
            segs = [(c, d) for (c, d, n) in self.wires if n == net]
            for p in remaining:
                for route in self._candidates(p, verts, segs):
                    end = route[-1]
                    if self.wire_ends_at(end) >= 3:
                        continue
                    if not self.route_ok(route, net):
                        continue
                    length = sum(abs(route[i][0] - route[i + 1][0]) + abs(route[i][1] - route[i + 1][1]) for i in range(len(route) - 1))
                    score = length + 6 * (len(route) - 2) + self._out_penalty(route, net)
                    if best is None or score < best[0]:
                        best = (score, p, route)
            if best is None:
                trees.append([remaining.pop(0)])             # start another island; it will carry its own label
                continue
            _, p, route = best
            self.add_route(route, net)
            tree.append(p)
            remaining.remove(p)
        return trees + [[q] for q in solo]

    def _out_penalty(self, route, net):
        pen = 0
        for end, nxt in ((route[0], route[1]), (route[-1], route[-2])):
            for pr in self.pins:
                if pr.net == net and same(pr.pt, end):
                    d = (nxt[0] - end[0], nxt[1] - end[1])
                    if (d[0] * pr.out[0] + d[1] * pr.out[1]) <= 0:
                        pen += 8
                    break
        return pen

    @staticmethod
    def _candidates(p, verts, segs):
        out = []
        near = sorted(verts, key=lambda v: abs(v[0] - p[0]) + abs(v[1] - p[1]))[:8]
        for v in near:
            if same(v, p):
                continue
            if abs(v[0] - p[0]) < EPS or abs(v[1] - p[1]) < EPS:
                out.append([p, v])
                continue
            out.append([p, (v[0], p[1]), v])
            out.append([p, (p[0], v[1]), v])
            mxs = [snap(p[0] + (v[0] - p[0]) * k) for k in (0.25, 0.5, 0.75)]
            mys = [snap(p[1] + (v[1] - p[1]) * k) for k in (0.25, 0.5, 0.75)]
            sx = 1 if v[0] >= p[0] else -1
            sy = 1 if v[1] >= p[1] else -1
            mxs += [round(v[0] + sx * k * G, 3) for k in (2, 3, 4, 6)] + [round(p[0] - sx * k * G, 3) for k in (2, 3, 4, 6)]
            mys += [round(v[1] + sy * k * G, 3) for k in (2, 3, 4, 6, 9)] + [round(p[1] - sy * k * G, 3) for k in (2, 3, 4, 6, 9)]
            for mx in mxs:
                out.append([p, (mx, p[1]), (mx, v[1]), v])
            for my in mys:
                out.append([p, (p[0], my), (v[0], my), v])
        for (c, d) in segs:                                  # perpendicular drop onto a wire of the same net
            if abs(c[1] - d[1]) < EPS and min(c[0], d[0]) + EPS < p[0] < max(c[0], d[0]) - EPS:
                out.append([p, (p[0], c[1])])
            if abs(c[0] - d[0]) < EPS and min(c[1], d[1]) + EPS < p[1] < max(c[1], d[1]) - EPS:
                out.append([p, (c[0], p[1])])
        return out

    # ---------------- labels
    def label_component(self, net, kind, comp_pts):
        """Name one connected island of `net`: a local label sitting on a horizontal wire; else a label (or, for a
        rail, its power symbol) at the end of a short stub from a pin; else on a short branch off one of its wires."""
        mv = lambda p, d, k: (round(p[0] + d[0] * k * G, 3), round(p[1] + d[1] * k * G, 3))  # noqa: E731
        island = [(c, d) for (c, d, n) in self.wires if n == net and any(self._wire_in(c, d, q) for q in comp_pts[:1])]
        if kind == "local":
            for (c, d) in sorted(island, key=lambda w: -abs(w[0][0] - w[1][0])):
                if abs(c[1] - d[1]) > EPS:
                    continue
                lo, hi = sorted((c[0], d[0]))
                x = snap(lo + G)
                while x < hi - G:
                    r = (x, c[1] - 2.2, x + len(net) * CH + 0.4, c[1] - 0.15)
                    if self._rect_free(r, net):
                        self.sh.labels.append((net, x, c[1], 0, "local"))
                        self.lab_rects.append((r, f"label {net}"))
                        return True
                    x = snap(x + G)
        starts = []                                            # (from point, direction) for a stub
        for q in comp_pts:
            prs = [pr for pr in self.pins if same(pr.pt, q)]
            if prs:
                starts.append((q, prs[0].out))
        pin_pts = [pr.pt for pr in self.pins]
        for (c, d) in island:
            for q in (c, d):
                if any(same(q, x) for x in pin_pts) or any(same(q, x[0]) for x in starts):
                    continue
                for dd in ((1, 0), (-1, 0), (0, -1), (0, 1)):
                    nxt = (q[0] + dd[0] * G, q[1] + dd[1] * G)
                    if not any(on_seg(nxt, a, bb, interior=False) for (a, bb, n) in self.wires if n == net):
                        starts.append((q, dd))
        for (c, d) in island:
            horiz = abs(c[1] - d[1]) < EPS
            lo, hi = sorted((c[0], d[0])) if horiz else sorted((c[1], d[1]))
            v = snap(lo + 2 * G)
            while v < hi - 2 * G + EPS:
                q = (v, c[1]) if horiz else (c[0], v)
                if self.wire_ends_at(q) == 0:
                    for dd in (((0, -1), (0, 1)) if horiz else ((1, 0), (-1, 0))):
                        starts.append((q, dd))
                v = snap(v + G)
        if kind in ("local", "global"):                    # level text reads better: horizontal exits first
            starts.sort(key=lambda st: st[1][0] == 0)
        for q, out in starts:
            for stub in (2, 3, 4, 6, 8):
                e = mv(q, out, stub)
                if kind == "flag":
                    f = flag_symbol(e, out)
                    bb = f.body()
                    r = (bb[0] - 0.3, bb[1] - 0.3, bb[2] + 0.3, bb[3] + 0.3)
                    if self.seg_ok(q, e, net, (q, e), False) and self._rect_free(r, net):
                        self._split_at(q, net)
                        self.wires.append((q, e, net))
                        self.sh.parts.append(f)
                        self.rects.append((r, f"flag {net}"))
                        return True
                    _PWR_N[0] -= 1
                    continue
                if kind == "power":
                    if self.seg_ok(q, e, net, (q, e), False) and self._try_power(net, q, e, out):
                        return True
                    continue
                ang = dir_angle(out)
                r = text_rect(net, e[0], e[1], ang, kind=kind)
                if self.seg_ok(q, e, net, (q, e), False) and self._rect_free(r, net):
                    self._split_at(q, net)
                    self.wires.append((q, e, net))
                    self.sh.labels.append((net, e[0], e[1], ang, kind))
                    self.lab_rects.append((r, f"label {net}"))
                    return True
        if kind == "flag":
            return False
        q, out = starts[0]                                  # last resort: at the pin itself (connects nothing else)
        if kind == "power":
            self.power_at(net, [([], q, out)], str(q))
        else:
            self.sh.labels.append((net, q[0], q[1], dir_angle(out), kind))
            self.lab_rects.append((text_rect(net, q[0], q[1], dir_angle(out), kind=kind), f"label {net}"))
        self.warn.append(f"{self.sh.key}: name for {net} at {q} placed with a clash")
        return False

    def _try_power(self, net, q, e, out):
        before = len(self.warn)
        n_wires = len(self.wires)
        lib_name, is_gnd = POWER[net]
        sym = self._power_placed(net, lib_name, is_gnd, e, out)
        b = sym.body()
        srect = (b[0] - 0.05, b[1] - 0.05, b[2] + 0.05, b[3] + 0.05)
        vrect = self._power_value_rect(sym, net, is_gnd)
        if any(rects_overlap(srect, r) or (vrect and rects_overlap(vrect, r)) for r, _ in self.rects + self.lab_rects):
            return False
        if any(rect_hit_seg(srect, c, d, 0) for (c, d, n) in self.wires if n != net):
            return False
        self._split_at(q, net)
        self.wires.append((q, e, net))
        self.sh.parts.append(sym)
        self.rects.append((srect, f"pwr {net}"))
        if vrect:
            self.rects.append((vrect, f"pwrtext {net}"))
        return True

    def _split_at(self, q, net):
        for i, (c, d, n) in enumerate(list(self.wires)):
            if n == net and on_seg(q, c, d, interior=True):
                self.wires[i] = (c, q, n)
                self.wires.append((q, d, n))
                return

    def _wire_in(self, c, d, q):
        """Is wire c-d part of the island that contains point q (walk the same-net wire graph)."""
        net = next(n for (a, b, n) in self.wires if same(a, c) and same(b, d))
        seen, todo = set(), [q]
        while todo:
            p = todo.pop()
            key = (round(p[0], 2), round(p[1], 2))
            if key in seen:
                continue
            seen.add(key)
            for (a, b, n) in self.wires:
                if n != net:
                    continue
                if same(a, p) or same(b, p) or on_seg(p, a, b):
                    if (same(a, c) and same(b, d)):
                        return True
                    todo += [a, b]
        return False

    def _rect_free(self, r, net):
        if any(rects_overlap(r, s) for s, _ in self.rects + self.lab_rects):
            return False
        if any(rects_overlap(r, s) for s in self.text_keep):
            return False
        for (c, d, n) in self.wires:
            if n != net and (rect_hit_seg(r, c, d, inflate=0.0)):
                return False
        for pr in self.pins:
            if r[0] - EPS <= pr.pt[0] <= r[2] + EPS and r[1] - EPS <= pr.pt[1] <= r[3] + EPS and pr.net != net:
                return False
        return True

    # ---------------- finish
    def no_connects(self):
        for pr in self.pins:
            if pr.net is None and not any(same(pr.pt, q) for q in self.sh.nocon):
                self.sh.nocon.append(pr.pt)

    def junctions(self):
        cnt: dict = {}
        for (c, d, n) in self.wires:
            for e in (c, d):
                k = (round(e[0], 3), round(e[1], 3))
                cnt[k] = cnt.get(k, 0) + 1
        pin_pts = {(round(pr.pt[0], 3), round(pr.pt[1], 3)) for pr in self.pins}
        for k, n in cnt.items():
            if n >= 3 or (n >= 2 and k in pin_pts):
                if n >= 3:
                    self.sh.junctions.append(k)

    def build(self, sheet_nets):
        self.no_connects()
        self.power_symbols()
        order = sorted(sheet_nets, key=lambda n: (-sum(1 for pr in self.pins if pr.net == n), n))   # deterministic
        kind_of = lambda n: "power" if n in POWER else ("global" if n in self.cross else "local")  # noqa: E731
        islands, done = {}, set()
        # lone pins first (a net with one point on this sheet, or a label-only pin): their labels claim space before
        # any wire is routed, so wires go around them rather than through the label zone
        for net in order:
            if net in PIN_POWER:
                continue
            prs = [pr for pr in self.pins if pr.net == net]
            pts = []
            for pr in prs:
                if not any(same(pr.pt, q) for q in pts):
                    pts.append(pr.pt)
            wired = [q for q in pts if not any(same(pr.pt, q) and self._lonely(pr) for pr in prs)]
            for q in pts:
                lone = q not in wired or len(wired) == 1
                if lone:
                    self.label_component(net, kind_of(net), [q])
                    done.add((net, q))
        for net in order:
            if net in PIN_POWER:
                continue
            islands[net] = self.route_net(net, kind_of(net))
        for net, trees in islands.items():
            for tree in trees:
                if len(tree) == 1 and (net, tree[0]) in done:
                    continue
                self.label_component(net, kind_of(net), tree)
        for net in NET_FLAGS.get(self.sh.key, ()):
            tree = max(islands[net], key=len)
            if not self.label_component(net, "flag", tree):
                self.warn.append(f"{self.sh.key}: no room for the PWR_FLAG on {net}")
        self.junctions()
        self.sh.wires = [(a, b) for (a, b, n) in self.wires]


# ------------------------------------------------------------------ the five sheets (positions in 1.27 mm grid units)
def lay_dock(b: Builder):
    b.title("Dock contacts and protection", 8, 12)
    for ref, gy in (("J3", 40), ("J4", 58), ("J10", 78), ("J11", 100), ("J12", 116)):
        b.place(ref, 20, gy, 90, ref_at=(-4.9, -0.2, "right"), val_at=(-4.9, 2.2, "right"))
    b.place("D5", 40, 47, 270)
    b.place("D4", 60, 40, 180)
    b.place("C15", 72, 46)
    b.place("R12", 86, 48)
    b.place("R13", 86, 58)
    b.place("U6", 50, 89, 270, ref_at=(7.5, -2.0, "left"), val_at=(7.5, 0.6, "left"))
    b.place("R18", 34, 119)
    b.note(110, 18, 60, 12, "THE DOCK", "Five gold pads touch the magnetic charging dock: 5 V power (VBUS), ground, the two "
           "USB data lines (D+ / D-) and CC, the line that tells a USB-C charger 'I am a device, send 5 V'.")
    b.note(110, 34, 60, 10, "SPARK GUARD  D5", "Soaks up static zaps right where they land, on the exposed power contact.")
    b.note(110, 47, 60, 10, "ONE-WAY VALVE  D4", "Lets dock power in but stops it flowing backwards if the pod is docked the wrong way.")
    b.note(110, 60, 60, 10, "DOCK DETECT  R12 / R13", "Halves the dock voltage so the brain can safely see 'I am docked'.")
    b.note(110, 73, 60, 10, "USB GUARD  U6", "Spark protection for the two USB data lines on their way to the brain.")
    b.note(110, 86, 60, 10, "SMOOTHING  C15", "A small reservoir that steadies the incoming dock power (rated 25 V for margin).")


def lay_power(b: Builder):
    b.title("Charger, battery and the 3.0 V supply", 8, 12)
    b.place("U3", 70, 60, 0, "y", ref_at=(-8.9, -7.9, "left"), val_at=(-8.9, 9.0, "left"))
    b.place("J5", 16, 59, 90, ref_at=(-4.9, -0.2, "right"), val_at=(-4.9, 2.2, "right"))
    b.place("C16", 30, 64)
    b.place("J9", 46, 66, 180, ref_at=(1.6, 2.6, "left"), val_at=(1.6, 5.0, "left"))
    b.place("RT1", 54, 69)
    b.place("R15", 92, 51, 180)
    b.place("R16", 86, 51, 180)
    b.place("C21", 92, 67)
    b.place("C17", 98, 71)
    b.place("U4", 112, 64, 0, "y", ref_at=(-6.4, -6.6, "left"), val_at=(-6.4, 9.2, "left"))
    b.place("C18", 126, 67)
    b.place("R20", 134, 64, 90)
    b.place("R8", 24, 89)
    b.place("R9", 24, 99)
    b.place("C19", 16, 99)
    b.note(150, 16, 70, 13, "BATTERY CHARGER  U3", "Fills the battery safely, refuses to charge when too hot or cold, and while "
           "docked runs the pod straight from the dock. The brain sets it up over two wires (SCL / SDA).")
    b.note(150, 33, 70, 10, "TEMPERATURE CHECK  RT1 / J9", "A heat-sensitive resistor (or one taped to the cell via J9) "
           "tells the charger the battery temperature.")
    b.note(150, 47, 70, 10, "QUIET 3.0 V SUPPLY  U4", "Turns battery voltage (3.0-4.2 V) into a steady, clean 3.0 V. "
           "No switching noise near the microphone.")
    b.note(150, 61, 70, 8, "R20  0 OHM LINK", "Cut or lift it to measure the whole pod's current with a meter.")
    b.note(150, 73, 70, 10, "BATTERY GAUGE  R8 / R9", "Halves the battery voltage so the brain can read how full it is "
           "(1 M each: almost no drain).")
    b.note(150, 87, 70, 8, "BATTERY  J5", "Battery + wire. Battery - shares the ground pad J4 on the dock sheet.")


def lay_mcu(b: Builder):
    b.title("The brain: STM32U575 microcontroller", 8, 12)
    b.place("U1", 100, 84, ref_at=(-20.3, -37.5, "left"), val_at=(-20.3, 38.2, "left"))
    for i, ref in enumerate(("C1", "C2", "C3", "C4", "C5", "C6", "C7")):
        b.place(ref, 14 + 7 * i, 32)
    b.place("L1", 66, 66, 180)
    b.place("C8", 112, 44)
    b.place("C9", 118, 44)
    b.place("C10", 48, 65)
    b.place("Y1", 64, 84, 270, ref_at=(-2.8, -1.0, "right"), val_at=(-2.8, 1.6, "right"))
    b.place("C11", 48, 83)
    b.place("C12", 58, 91)
    b.place("R1", 74, 74, 270)
    b.place("R2", 63, 108, 270)
    b.place("SW1", 136, 52, ref_at=(-2.6, -3.6, "left"), val_at=(9.0, 0.5, "left"))
    b.place("R10", 146, 58)
    for i, ref in enumerate(("TP1", "TP2", "TP3", "TP4", "TP5")):
        b.place(ref, 16, 116 + 5 * i, 90, ref_at=(-4.9, -0.2, "right"), val_at=(-4.9, 2.2, "right"))
    for i, ref in enumerate(("TP6", "TP7", "TP8", "TP9", "TP10")):
        b.place(ref, 54, 116 + 5 * i, 90, ref_at=(-4.9, -0.2, "right"), val_at=(-4.9, 2.2, "right"))
    b.label_only |= {f"TP{i}" for i in range(1, 11)} | {"L1.2"}
    b.note(8, 16, 56, 9, "DECOUPLING  C1-C7", "Tiny local energy stores beside the chip's power pins; they keep 3.0 V steady "
           "when the chip draws sudden gulps.")
    b.note(156, 16, 64, 13, "THE BRAIN  U1", "Hears the microphone, shifts ultrasound down into hearing range, drives the "
           "speaker, and runs the button, light, battery checks and USB updates. Right-side flags name where each pin goes.")
    b.note(156, 33, 64, 10, "OWN POWER CONVERTER  L1, C8, C9", "The chip's built-in efficient supply for its core (1.1 V); "
           "the only switching supply in the pod.")
    b.note(156, 47, 64, 9, "BUTTON  SW1, R10", "Press = 3.0 V reaches PA0 and wakes the brain; R10 holds it low otherwise.")
    b.note(156, 59, 64, 9, "CLOCK  Y1, C11, C12", "A 32.768 kHz crystal: the chip's accurate time base.")
    b.note(156, 70, 64, 10, "BOOT AND RESET  R1, C10", "R1 makes the chip start its own program; C10 keeps the reset line "
           "quiet.")
    b.note(82, 120, 60, 13, "TEST PADS  TP1-TP10", "Gold dots for a programmer (SWDIO, SWCLK, NRST) or a probe. TP7 prints "
           "debug text; TP8-TP10 are a hand-wire fallback for the microphone clock.")


def lay_mic(b: Builder):
    b.title("Ultrasonic microphone", 8, 12)
    b.place("U2", 60, 60, ref_at=(-7.6, -6.0, "left"), val_at=(1.5, 11.0, "left"))
    b.place("C13", 44, 60)
    b.note(100, 18, 70, 14, "ULTRASONIC MICROPHONE  U2", "Listens through a 0.6 mm pinhole in the board and a mesh-covered "
           "hole in the lid. It sends sound to the brain as a fast stream of 1s and 0s (PDM) timed by MIC_CLK.")
    b.note(100, 36, 70, 10, "POWER SWITCH", "The brain powers the mic from a pin (MIC_VDD), so it is fully off when the pod "
           "is off. C13 steadies that supply.")
    b.note(100, 50, 70, 8, "SEL TIED TO GROUND", "Picks which clock edge the mic answers on.")


def lay_output(b: Builder):
    b.title("Speaker driver, self-check and ear-pad wires", 8, 12)
    b.place("Q1", 70, 60, ref_at=(-4.8, -11.0, "left"), val_at=(6.0, -9.0, "left"))
    b.place("Q2", 140, 60, ref_at=(-4.8, -11.0, "left"), val_at=(6.0, -9.0, "left"))
    b.place("R3", 58, 51, 180)
    b.place("R4", 58, 69)
    b.place("R5", 128, 51, 180)
    b.place("R6", 128, 69)
    b.place("J1", 90, 61, 270, ref_at=(4.9, -0.2, "left"), val_at=(4.9, 2.2, "left"))
    b.place("J2", 160, 61, 270, ref_at=(4.9, -0.2, "left"), val_at=(4.9, 2.2, "left"))
    b.place("R21", 100, 82)
    b.place("R22", 112, 86, 90)
    b.place("C22", 122, 92)
    b.place("C14", 30, 40)
    b.place("R14", 40, 112, 90)
    b.place("J7", 60, 112, 270, ref_at=(4.9, -0.2, "left"), val_at=(4.9, 2.2, "left"))
    b.place("J8", 60, 124, 270, ref_at=(4.9, -0.2, "left"), val_at=(4.9, 2.2, "left"))
    b.note(176, 16, 50, 17, "SPEAKER DRIVER  Q1, Q2", "Each chip is one P + one N switch. Together they flip the speaker's "
           "voltage back and forth 200,000 times a second; the speaker only follows the slow sound part.")
    b.note(176, 37, 50, 12, "SAFE OFF  R3-R6", "Hold every switch OFF while the brain is starting up or resetting.")
    b.note(176, 53, 50, 13, "SELF-CHECK  R21, R22, C22", "A 0.1 ohm resistor measures speaker current, so the pod can "
           "test its own speaker.")
    b.note(176, 70, 50, 9, "C14  22 uF", "Local reservoir for the speaker's current peaks.")
    b.note(80, 108, 70, 13, "EAR-PAD WIRES  J1, J2, J7, J8", "Four thin wires run up the glasses arm: two to the "
           "bone-conduction speaker (J1/J2), two to the status light (J7/J8, current set by R14).")


SHEETS = [("dock", "Dock and USB protection", lay_dock), ("power", "Charger, battery, 3.0 V", lay_power),
          ("mcu", "Microcontroller", lay_mcu), ("mic", "Microphone", lay_mic), ("output", "Speaker driver and ear pad", lay_output)]
FLAGS = {"power": ("GND", "+3V0", "VSYS", "VBAT", "VBUS"), "dock": ("DOCK_VBUS",)}   # rail markers per sheet
NET_FLAGS = {"mcu": ("VLXSMPS", "VDD11"), "mic": ("MIC_VDD",)}
# PWR_FLAG = KiCad's "this net is powered" marker for ERC, not a part. The rails get one each; VLXSMPS/VDD11 (the MCU's
# own SMPS: ST's symbol calls both pins power inputs) and MIC_VDD (a GPIO powers the mic) get one where they are drawn.


def flag_symbol(at, d):
    _PWR_N[0] += 1
    rot = {(0, -1): 0, (0, 1): 180, (1, 0): 270, (-1, 0): 90}[d]
    f = Placed(f"#FLG{_PWR_N[0]:03d}", "power:PWR_FLAG", get_symbol("power", "PWR_FLAG"), at, rot, None, "PWR_FLAG", "", {},
               power=True)
    f.ref_at, f.val_at, f.val_hide = (0, 0, None), (0, 0, None), True
    return f


def add_flags(b: Builder, gx0, gy0):
    nets = FLAGS.get(b.sh.key, ())
    if not nets:
        return
    b.title("Rail markers (drawing aids for the checker, not parts)", gx0 - 6, gy0 - 8, size=1.27)
    for i, net in enumerate(nets):
        gx, gy = gx0 + 12 * i, gy0
        lib_name, is_gnd = POWER[net]
        at = (round(gx * G, 3), round(gy * G, 3))
        sym = b._power_placed(net, lib_name, is_gnd, at, (0, 1) if is_gnd else (0, -1))
        b.sh.parts.append(sym)
        b.sh.parts.append(flag_symbol(at, (0, -1) if is_gnd else (0, 1)))
        for part in (sym,):
            bb = part.body()
            b.rects.append(((bb[0] - 1, bb[1] - 3, bb[2] + 1, bb[3] + 3), "flag"))


# ------------------------------------------------------------------ main
DATE = "2026-10-02"


def generate():
    comps, nets = load_netlist()
    pin_net = {(r, p): n for n, ps in nets.items() for r, p in ps}
    warn: list[str] = []
    builders = []
    for i, (key, name, lay) in enumerate(SHEETS):
        b = Builder(Sheet(key, name, i + 2), comps, pin_net, set(), warn)
        lay(b)
        builders.append(b)
    placed = [p.ref for b in builders for p in b.sh.parts if not p.power]
    missing = sorted(set(comps) - set(placed))
    dup = sorted({r for r in placed if placed.count(r) > 1})
    if missing or dup:
        raise SystemExit(f"sch: unplaced {missing}, placed twice {dup}")
    sheet_of = {p.ref: b.sh.key for b in builders for p in b.sh.parts if not p.power}
    cross = {n for n, ps in nets.items() if len({sheet_of[r] for r, _ in ps}) > 1}
    for b in builders:
        b.cross = cross
        add_flags(b, *{"power": (14, 124), "dock": (20, 140)}.get(b.sh.key, (0, 0)))
        sheet_nets = {pr.net for pr in b.pins if pr.net}
        b.build(sheet_nets)
    OUT.mkdir(exist_ok=True)
    sheets = [b.sh for b in builders]
    root, rs = write_root(sheets, "Pod board Rev F: schematic (generated from gen.py)", DATE)
    (OUT / "pod.kicad_sch").write_text(sdump(rs) + "\n")
    for sh in sheets:
        (OUT / sh.file).write_text(sdump(sh.sexp(root, uid("sheet", sh.key), f"Pod board Rev F: {sh.name}", DATE)) + "\n")
    (OUT / "sym-lib-table").write_text('(sym_lib_table\n\t(version 7)\n\t(lib (name "lcsc") (type "KiCad") '
                                       '(uri "${KIPRJMOD}/../../lib/lcsc/lcsc.kicad_sym") (options "") (descr ""))\n)\n')
    (OUT / "fp-lib-table").write_text('(fp_lib_table\n\t(version 7)\n'
                                      '\t(lib (name "lcsc") (type "KiCad") (uri "${KIPRJMOD}/../../lib/lcsc/lcsc.pretty") (options "") (descr ""))\n'
                                      '\t(lib (name "pod") (type "KiCad") (uri "${KIPRJMOD}/../../lib/pod.pretty") (options "") (descr ""))\n)\n')
    pro = OUT / "pod.kicad_pro"
    if not pro.exists():
        pro.write_text(json.dumps({"meta": {"filename": "pod.kicad_pro", "version": 3}}, indent=2) + "\n")
    (OUT / "pod.canonical.json").write_text(json.dumps(canonical(comps, nets), indent=1) + "\n")
    return warn


def kicad(*args):
    return subprocess.run(FENCE + ["kicad-cli", *args], capture_output=True, text=True)


def normalize_export(xml_path: Path, out_json: Path):
    """KiCad prefixes local-label nets with the sheet path ('/2 Dock/CC') and lists unconnected pins as their own
    'unconnected-(...)' nets; strip the prefix and drop those, so the names compare with gen.py's."""
    import xml.etree.ElementTree as ET
    r = ET.parse(xml_path).getroot()
    comps = []
    for c in r.findall("./components/comp"):
        ls = c.find("libsource")
        comps.append({"ref": c.get("ref"), "value": (c.findtext("value") or "").strip(),
                      "footprint": (c.findtext("footprint") or "").strip(), "device": f"{ls.get('lib')}:{ls.get('part')}"})
    nets = []
    for n in r.findall("./nets/net"):
        name = n.get("name")
        nodes = n.findall("node")
        if name.startswith("unconnected-") and len(nodes) == 1:
            continue
        if name.startswith("/"):
            name = name.rsplit("/", 1)[-1]
        nets.append({"name": name, "pins": [{"ref": x.get("ref"), "pin": x.get("pin")} for x in nodes]})
    out_json.write_text(json.dumps({"schema": "schematic-connectivity-v1", "components": comps, "nets": nets}, indent=1) + "\n")


def prove():
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="pod-sch-"))
    xml = tmp / "export.xml"
    res = kicad("sch", "export", "netlist", "--format", "kicadxml", "-o", str(xml), str(OUT / "pod.kicad_sch"))
    if res.returncode:
        raise SystemExit(f"netlist export failed: {res.stderr}")
    normalize_export(xml, OUT / "export.canonical.json")
    cmp = subprocess.run([sys.executable, str(REPO / ".claude/skills/schematic-humanizer/scripts/compare_connectivity.py"),
                          str(OUT / "pod.canonical.json"), str(OUT / "export.canonical.json")], capture_output=True, text=True)
    print(cmp.stdout.strip() or cmp.stderr.strip())
    erc = tmp / "erc.json"
    kicad("sch", "erc", "--format", "json", "--severity-all", "-o", str(erc), str(OUT / "pod.kicad_sch"))
    counts: dict = {}
    if erc.exists():
        d = json.loads(erc.read_text())
        for sh in d.get("sheets", []):
            for v in sh.get("violations", []):
                k = (v.get("severity"), v.get("type"))
                counts[k] = counts.get(k, 0) + 1
    summary = ", ".join(f"{s}/{t} {n}" for (s, t), n in sorted(counts.items())) or "clean"
    print("ERC:", summary)
    (OUT / "proof.txt").write_text(f"connectivity vs hw/pod/pod.net: {cmp.stdout.strip().splitlines()[-1] if cmp.stdout.strip() else cmp.stderr.strip()}\n"
                                   f"ERC: {summary}\n"
                                   "Known warnings: pin_to_pin = easyeda2kicad symbols (lcsc lib) mark pins 'unspecified'; "
                                   "lib_symbol_issues Q1/Q2 = PMCXB290UE is defined in gen.py (SKiDL), no library; "
                                   "lib_symbol_mismatch L1 = embedded copy of the lcsc inductor differs only in KiCad's arc "
                                   "normalisation.\n")
    return cmp.returncode, counts


def render():
    pdf = OUT / "pod.pdf"
    kicad("sch", "export", "pdf", "-o", str(pdf), str(OUT / "pod.kicad_sch"))
    png = OUT / "png"
    png.mkdir(exist_ok=True)
    for f in png.glob("*.png"):
        f.unlink()
    subprocess.run(["pdftoppm", "-r", "170", "-png", str(pdf), str(png / "sheet")], check=True)
    return pdf, sorted(png.glob("*.png"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-render", action="store_true")
    a = ap.parse_args()
    warn = generate()
    for w in warn:
        print("WARN", w)
    rc, _ = prove()
    if not a.no_render:
        pdf, pngs = render()
        print(pdf)
        for p in pngs:
            print(p)
    sys.exit(rc)


if __name__ == "__main__":
    main()
