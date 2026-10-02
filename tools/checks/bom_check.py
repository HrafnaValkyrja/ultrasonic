#!/usr/bin/env python3
"""BOM / board / schematic agreement: do the two sides of every part-identity interface say the same thing?

    source tools/env.sh        # optional: the script re-executes itself under the harness venv if skidl/pcbnew are missing
    python3 tools/checks/bom_check.py [--board PATH | --no-board] [--json] [-v] [--strict] [--no-selftest]

Layout-agnostic and read-only: it reads whatever board exists (default: the newest hw/pod/*/pod_*_placed.kicad_pcb),
the SKiDL circuit (hw/pod/system_map.py build(), which runs gen.build()), hw/pod/pod.net, hw/pod/bom_jlc.csv,
docs/build/bom.py, .pcba-workflow/sourcing-lock.csv and the footprint libraries in hw/lib. It never edits them.
One line per check, "PASS|WARN|FAIL <id> <message>" (200 characters at most); exit 1 if any FAIL, exit 2 if no board
could be found (an explicit --board that does not exist, or none in hw/pod; --no-board opts out). -v adds detail lines
under each non-PASS result, --json prints machine-readable results, --strict turns WARN into FAIL (release gate).
Runs in a few seconds (SKiDL build, one board load, one kicad-cli call, the selftest), so it is fit for a pre-commit hook.

Why: the PLM tracker detects CHANGE, not DISAGREEMENT (docs/research/methodology.md). Two defects went through
by hand-review only: the mic port 0.77 mm off the lid port, and wrong "LCSC Part" properties baked into
EasyEDA-imported footprints (ECR-0012; Q1/Q2 would have ordered C552750 instead of C19654206).

Checks
  refs          placed-board refs == SKiDL refs (copper-only pads included); no extras, missing or duplicates;
                board-only footprints (fiducials, holes: excluded from BOM and position files) are allowed
  netlist       hw/pod/pod.net (what the placer reads) == SKiDL: refs, values, footprints, LCSC, DNP_BOM and every pin's net
  footprints    board footprint name == the schematic's footprint field; known-bad footprints WARN with their ECR
  fp-library    every schematic footprint and every hw/lib footprint loads; board pad geometry == library geometry
                (pad count, numbers, drill, type, layers: FAIL; position, size, shape: WARN)
  values        board Value field == schematic value (a footprint-name placeholder is a WARN, a different value FAIL)
  nets          every board pad's net == the SKiDL net of that pin
  assembly-tier JLC assembly tier from sides, IC pitch and BGA pitch == the tier the cost model assumes (Standard)
  identity      part identity lives in the schematic only: no LCSC number or identity property in a hw/lib footprint
                (FAIL), none on a board footprint that disagrees with the schematic (a pre-cleanup copy of the ECR-0012
                property is a WARN naming the ref); every LCSC on the schematic is checked against LCSC_IDENTITY, an
                offline table from the JLC API (value and package for R/C, MPN for the rest) and against the lock's MPNs
  jlc-bom       bom_jlc.csv == the schematic per ref (value, footprint, LCSC; none empty); DNP and pads absent; board
                DNP / exclude flags and footprint types fit; BOM refs == the refs of a real `kicad-cli pcb export pos`
  cost-bom      docs/build/bom.py ITEMS agree with the schematic on LCSC (FAIL) and on quantities (WARN)
  stock-lock    fitted LCSC numbers with no lock row and no dated lookup; lock age, status, stock (0 FAIL, <100 WARN)
  lock-drift    RECOMMENDED lock rows the schematic no longer uses; lock notes that cite a part the schematic uses
  selftest      each check above must give the expected result on a deliberately broken copy (see selftest_cases)
Known open issues are WARN and cite their ECR (ISSUE_ECR); once that ECR leaves proposed/approved/implemented they are FAIL.
Not covered: structured rating checks (only the lock-note hit on C8/C9), live stock (the lock and dated notes are read offline).
"""
from __future__ import annotations

import argparse
import contextlib
import copy
import csv
import datetime as dt
import functools
import importlib.util
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BOARD_GLOB = "hw/pod/*/pod_*_placed.kicad_pcb"
NETLIST = REPO / "hw/pod/pod.net"
JLC_BOM = REPO / "hw/pod/bom_jlc.csv"
COST_BOM = REPO / "docs/build/bom.py"
COST_CSV = REPO / "docs/build/bom.csv"
LOCK = REPO / ".pcba-workflow/sourcing-lock.csv"
SYMBOLS = REPO / "hw/lib/lcsc/lcsc.kicad_sym"
LIB_ROOT = REPO / "hw/lib"                                                           # every *.pretty below it is a project library
LEGACY_ROOT = REPO / "hw/pod/kicad-draft"                                            # superseded copies of the libraries
ECR_DIR = REPO / "docs/system/plm/ecr"
KICAD_FP = Path(os.environ.get("KICAD10_FOOTPRINT_DIR", "/usr/share/kicad/footprints"))
TODAY = dt.date.today()

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"
MAX_MSG = 200                           # characters per result line; the rest goes to -v
PAD_TOL_NM = 2000                       # board vs library pad geometry
LOCK_MAX_AGE_DAYS = 14                  # a lock row or dated lookup older than this is stale for an order decision
LOW_STOCK = 100                         # stock below this is a supply risk for a one-off buy
OPEN_ECR = {"proposed", "approved", "implemented"}       # an ECR in one of these states still tracks a live issue
DNP_KINDS = {"", "dnp", "pad"}          # gen.py's DNP_BOM: fitted, do-not-place, copper-only pad
STD_FIELDS = {"Reference", "Value", "Datasheet", "Description"}
LCSC_NUM = re.compile(r"(?<![A-Za-z0-9])C[1-9]\d{3,}(?![A-Za-z0-9])")           # the shape of an LCSC part number
ID_NAME = re.compile(r"lcsc|jlc|mpn|manufactur|mfr|supplier|digi-?key|mouser|vendor|^part[ _-]?(no|num|number)?\b", re.I)
NOT_ID = re.compile(r"offset|rotation|position|orient|correction", re.I)         # JLC placement-fix fields are not identity
MPN_NAME = re.compile(r"mpn|mfr[ _-]?part|manufacturer[ _-]?part|part[ _-]?(no|num|number)\b", re.I)
WARNING_WORDS = re.compile(r"\b(only|not|never|cannot|reject\w*|avoid|insufficient|too|fail\w*|wrong|lacks?|below|but)\b|<", re.I)
SI = {"p": 1e-12, "n": 1e-9, "u": 1e-6, "µ": 1e-6, "m": 1e-3, "k": 1e3, "M": 1e6, "R": 1.0}
ECON_IC_PITCH, ECON_BGA_PITCH = 0.40, 0.50   # JLC Economic PCBA limits (mm; single side only), jlcpcb.com/capabilities/pcb-assembly-capabilities, read 2026-10-02
ASSUMED_TIER = "Standard"               # the tier the cost model uses (sim/checks/assembly_fees.py: the only tier this board can use)
LOCK_COLUMNS = {"ref_role", "mpn", "lcsc", "stock", "queried_utc", "status", "notes"}

# "LCSC Part" removed from each hw/lib/lcsc/lcsc.pretty footprint by the ECR-0012 cleanup (git 779872e;
# docs/research/footprint-lcsc-cleanup.md). A board copy that still carries one predates the cleanup.
STALE_LCSC = {
    "DSBGA-8_L1.6-W0.9-R2-C4-P0.40-BL": "C3682423", "FC-135R_L3.2-W1.5": "C32346", "L0806": "C337891",
    "SOD-882_L1.0-W0.6-BI": "C84374", "SOD-923_L0.8-W0.6-LS1.0-RD": "C87910",
    "SOT-553-5_L1.6-W1.2-P0.50-LS1.6-TL-1": "C1972959", "SOT-563_L1.6-W1.2-P0.50-LS1.6-BL": "C177025",
    "SOT1216_L1.1-W1.0-P0.35-BL-EP": "C552750", "SW-SMD_4P-L3.0-W2.6-P1.85-LS3.4": "C221708",
    "SW-SMD_L3.0-W2.0-LS3.5": "C221821", "X2SON-4_L1.0-W1.0-P0.65-TL-EP": "C5220164",
}
# footprints known to be wrong: footprint -> (ECR that tracks it, what is wrong)
KNOWN_FOOTPRINT = {
    "lcsc:SOT1216_L1.1-W1.0-P0.35-BL-EP": ("ECR-0004", "EasyEDA lands 0.16 x 0.20 are smaller than Nexperia Fig. 32"),
}
# Issues this checker found and the ECR that tracks each (None: none raised yet, the line says "no ECR yet").
# Keys: values, cost-qty, lock-gaps, lock-unused, lock-note:<LCSC>, stock:<LCSC>. Set the ECR here once it exists.
ISSUE_ECR = {"stock:C5271013": "ECR-0008", "stale-lcsc": "ECR-0012"}

# LCSC number -> (MPN, package, value): an offline second source for what each LCSC number is, so gen.py's own numbers are
# checked against something that does not derive from gen.py. From the JLC parts API via tools/jlc.py, queried
# 2026-10-02T05:40Z (package and value for R/C only; stock and price are in the lock, they change daily). A new LCSC number
# on the schematic is a WARN here until it gets a row.
LCSC_IDENTITY = {
    "C1525": ("CL05B104KO5NNNC", "0402", "100n"), "C1548": ("0402CG150J500NT", "0402", "15p"),
    "C11702": ("0402WGF1001TCE", "0402", "1k"), "C12530": ("CL05A225MQ5NSNC", "0402", "2u2"),
    "C15195": ("CL05B103KB5NNNC", "0402", "10n"), "C17168": ("0402WGF0000TCE", "0402", "0"),
    "C19702": ("CL10A106KP8NNNC", "0603", "10u"), "C23733": ("CL05A475MP5NRNC", "0402", "4u7"),
    "C25105": ("0402WGF330JTCE", "0402", "33"), "C25334": ("1206W4F100LT5E", "1206", "0.1"),
    "C2858031": ("GRM155R61E475ME15D", "0402", "4u7 25V"), "C48260": ("TPD1E10B06DPYR", None, None),
    "C25741": ("0402WGF1003TCE", "0402", "100k"), "C25744": ("0402WGF1002TCE", "0402", "10k"),
    "C25879": ("0402WGF2201TCE", "0402", "2k2"), "C25905": ("0402WGF5101TCE", "0402", "5k1"),
    "C26083": ("0402WGF1004TCE", "0402", "1M"), "C52923": ("CL05A105KA5NQNC", "0402", "1u"),
    "C59461": ("CL10A226MQ8NRNC", "0603", "22u"), "C77131": ("NCP15XH103F03RC", "0402", "10k"),
    "C84374": ("PESD5V0S1BL,315", None, None), "C87910": ("ESD9X5.0ST5G", None, None),
    "C191023": ("1N5819WS", None, None), "C337891": ("DFE201610E-2R2M=P2", None, None),
    "C221707": ("KMT022NGJLHS", None, None), "C32346": ("Q13FC13500004", None, None),
    "C1972959": ("TPD2E2U06DRLR", None, None), "C2879853": ("SPH0641LU4H-1", None, None),
    "C3682423": ("BQ25180YBGR", None, None), "C5220164": ("TPS7A2030PDQNR", None, None),
    "C5271013": ("STM32U575CIU6Q", None, None), "C19654206": ("PMCXB290UEZ", None, None),
}


# ------------------------------------------------------------------------------------------- plumbing
class Result:
    def __init__(self, cid, status, msg, details=()):
        self.id, self.status = cid, status
        self.details = [str(x) for x in details if str(x).strip() and not str(x).rstrip().endswith(":")]
        if len(msg) > MAX_MSG:
            self.details.insert(0, msg)
            msg = msg[:MAX_MSG - 3].rstrip() + "..."
        self.msg = msg

    def as_dict(self):
        return {"id": self.id, "status": self.status, "message": self.msg, "details": self.details}


class Findings:
    """Collects the headline and detail lines of one check; the worst status wins."""

    def __init__(self):
        self.status, self.heads, self.lines = PASS, [], []

    def add(self, status, head, lines=()):
        self.status = worst(self.status, status)
        self.heads.append((status, head))
        self.lines += list(lines)

    def result(self, cid, ok_msg):
        heads = [h for _, h in sorted(self.heads, key=lambda sh: (sh[0] != FAIL, sh[0] != WARN))]    # FAIL first, then WARN
        return Result(cid, self.status, "; ".join(heads), self.lines) if heads else Result(cid, PASS, ok_msg)


def worst(*statuses):
    return FAIL if FAIL in statuses else WARN if WARN in statuses else PASS


def rel(path):
    try:
        return str(Path(path).relative_to(REPO))
    except ValueError:
        return str(path)


def nat(ref):
    m = re.match(r"([A-Za-z]+)(\d+)$", ref)
    return (m[1], int(m[2])) if m else (ref, 0)


def refs_str(refs, limit=12):
    refs = sorted(refs, key=nat)
    return ",".join(refs[:limit]) + (f" (+{len(refs) - limit} more)" if len(refs) > limit else "")


def ecr_status(ecr):
    """(state, problem): the first word of the ECR's Status line, lower case; problem says why there is none."""
    f = ECR_DIR / f"{ecr}.md"
    if not f.exists():
        return None, f"{f.name} not found"
    m = re.search(r"^\W*Status\W*:\W*([A-Za-z]+)", f.read_text(encoding="utf-8", errors="replace"), re.M | re.I)
    return (m[1].lower(), None) if m else (None, f"no Status: line in {f.name}")


def known(ecr):
    """(status, tag) for a known issue: WARN while its ECR is open, FAIL once the ECR says it is done or is unreadable."""
    state, problem = ecr_status(ecr)
    if problem:
        return FAIL, f"{ecr}: {problem}"
    return (WARN, f"{ecr} {state}") if state in OPEN_ECR else (FAIL, f"{ecr} {state}: the defect should be gone")


def issue(key):
    ecr = ISSUE_ECR.get(key)
    return known(ecr) if ecr else (WARN, "no ECR yet")


def parse_date(text):
    try:
        return dt.date.fromisoformat(str(text).strip()[:10])
    except ValueError:
        return None


def parse_value(text):
    """'4u7' -> 4.7e-6, '10k B3435' -> 1e4, '0.1' -> 0.1, '100n' -> 1e-7; None if it does not start with a plain value."""
    m = re.match(r"(\d+)([pnuµmkMR])(\d*)(?:\s|$)", text.strip())
    if m:
        return float(f"{m[1]}.{m[3] or 0}") * SI[m[2]]
    m = re.match(r"(\d+(?:\.\d+)?)(?:\s|$)", text.strip())
    return float(m[1]) if m else None


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def mpn_match(mpn, name):
    """One contains the other, ignoring punctuation and case; an 'x' in a symbol name stands for any character."""
    a, b = norm(mpn), norm(name)
    return bool(a and b and (a in b or b in a or re.search(re.escape(b).replace("x", "."), a)))


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


@contextlib.contextmanager
def patched(**names):
    """Point module-level paths at a scratch copy for the duration of a selftest case."""
    old = {k: globals()[k] for k in names}
    globals().update(names)
    try:
        yield
    finally:
        globals().update(old)


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


def ensure_env():
    """Set what tools/env.sh would; re-execute under the harness venv if skidl/pcbnew are missing. Returns an error text or None."""
    sym, fpd = os.environ.get("KICAD10_SYMBOL_DIR", "/usr/share/kicad/symbols"), os.environ.get("KICAD10_FOOTPRINT_DIR", "/usr/share/kicad/footprints")
    for v in ("KICAD10", "KICAD", "KICAD6", "KICAD7", "KICAD8", "KICAD9"):
        os.environ.setdefault(f"{v}_SYMBOL_DIR", sym)
        os.environ.setdefault(f"{v}_FOOTPRINT_DIR", fpd)
    os.environ.setdefault("TMPDIR", str(Path.home() / ".cache/ultrasonic-tmp"))
    with contextlib.suppress(OSError):
        Path(os.environ["TMPDIR"]).mkdir(parents=True, exist_ok=True)
    cwd = os.getcwd()
    try:
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as tmp:      # SKiDL opens its .log/.erc files in the cwd at import
            os.chdir(tmp)
            try:
                import skidl                                        # noqa: F401
                with quiet_stderr():
                    import pcbnew                                   # noqa: F401
            finally:
                os.chdir(cwd)
    except ImportError as e:
        venv = Path(os.environ.get("ULTRA_VENV", "/opt/ultrasonic-tools/venv"))
        py = venv / "bin/python"
        if py.exists() and Path(sys.prefix).resolve() != venv.resolve() and not os.environ.get("BOM_CHECK_REEXEC"):
            os.environ["BOM_CHECK_REEXEC"] = "1"
            os.execv(str(py), [str(py), str(Path(__file__).resolve()), *sys.argv[1:]])
        return f"tools/env.sh not sourced or the venv is missing: {e}"
    return None


# ------------------------------------------------------------------------------------------- sources
_SCHEMATIC = None


def pin_net(pin):
    ns = [n.name for n in pin.nets if n.name and not n.name.startswith("__NOCONNECT")]
    return ns[0] if ns else None


def read_schematic():
    """ref -> part, from the SKiDL circuit (built once per process, in a scratch directory: SKiDL writes logs to the cwd)."""
    global _SCHEMATIC
    if _SCHEMATIC is not None:
        return _SCHEMATIC
    sys.path.insert(0, str(REPO / "hw/pod"))
    cwd = os.getcwd()
    with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as tmp:
        os.chdir(tmp)
        try:
            import system_map                                       # noqa: E402
            circ = system_map.build()
        finally:
            os.chdir(cwd)
    parts = {}
    for p in circ.parts:
        fp = p.footprint or ""
        parts[p.ref] = dict(ref=p.ref, value=str(p.value), name=str(p.name), footprint=fp, lib=fp.rpartition(":")[0],
                            fp_name=fp.rpartition(":")[2], lcsc=p.fields.get("LCSC", ""), dnp=p.fields.get("DNP_BOM", ""),
                            pins={str(pin.num): pin_net(pin) for pin in p.pins})
    _SCHEMATIC = parts
    return parts


def sch_pin_nets(sch):
    return {(r, n): net for r, p in sch.items() for n, net in p["pins"].items() if net}


def import_pcbnew():
    with quiet_stderr():
        import pcbnew                                               # noqa: E402
    return pcbnew


def load_board(pcbnew, path):
    with quiet_stderr():
        try:
            board = pcbnew.LoadBoard(str(path))
        except Exception as e:                                      # noqa: BLE001  (pcbnew raises on a truncated file)
            raise ValueError(f"{type(e).__name__}: {str(e).strip()[:100]}") from e
    if board is None:
        raise ValueError("not a KiCad board file, or truncated")
    return board


def board_facts(pcbnew, board):
    """ref -> footprint facts (plus the live footprint for pad geometry); duplicates listed separately."""
    parts, dups = {}, []
    text_cls = getattr(pcbnew, "PCB_TEXT", ())
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        if ref in parts:
            dups.append(ref)
            continue
        fpid = fp.GetFPID()
        texts = [(f.GetName(), f.GetText()) for f in fp.GetFields()] + [("library description", fp.GetLibDescription()), ("keywords", fp.GetKeywords())]
        texts += [("text", g.GetText()) for g in fp.GraphicalItems() if text_cls and isinstance(g, text_cls)]
        parts[ref] = dict(ref=ref, fp=fp, nick=str(fpid.GetLibNickname()), name=str(fpid.GetLibItemName()), value=fp.GetValue(),
                          fields={f.GetName(): f.GetText() for f in fp.GetFields() if f.GetName() not in STD_FIELDS}, texts=texts,
                          dnp=fp.IsDNP(), no_bom=fp.IsExcludedFromBOM(), no_pos=fp.IsExcludedFromPosFiles(), board_only=fp.IsBoardOnly(),
                          flipped=fp.IsFlipped(), attr=fp.GetAttributes())
    return parts, dups


def board_pad_nets(brd, refs):
    """{(ref, pad number): net name} for every pad that has a net, on the footprints in refs."""
    out = {}
    for ref in refs:
        for pad in brd[ref]["fp"].Pads():
            net = pad.GetNetname().lstrip("/")
            if net:
                key = (ref, pad.GetNumber())
                out[key] = "|".join(sorted(set(out.get(key, "").split("|")) - {""} | {net}))
    return out


def read_rows(path):
    """(header, rows) of a CSV; utf-8-sig so an Excel-saved file with a byte-order mark still has its first column name."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        return reader.fieldnames or [], rows


def read_csv(path):
    return read_rows(path)[1]


def read_lock():
    return read_csv(LOCK) if LOCK.exists() else None


def lock_status(row):
    return (row.get("status") or "").strip().upper()


def lock_index(rows):
    """lcsc -> the row with the newest queried_utc (later file position breaks a tie), and notes on rows that disagree."""
    groups, notes = {}, []
    for i, r in enumerate(rows):
        groups.setdefault((r.get("lcsc") or "").strip(), []).append((parse_date(r.get("queried_utc", "")) or dt.date.min, i, r))
    by = {}
    for lcsc, g in groups.items():
        g.sort(key=lambda t: (t[0], t[1]))
        by[lcsc] = g[-1][2]
        if len({lock_status(r) for *_, r in g}) > 1:
            notes.append(f"{lcsc} has {len(g)} lock rows with different statuses ({', '.join(lock_status(r) for *_, r in g)}); the newest "
                         f"({g[-1][2].get('queried_utc', '?')}, {lock_status(g[-1][2])}) is used: drop the stale ones")
    return by, notes


@functools.cache
def lib_dirs(root):
    return {d.stem: d for d in sorted(Path(root).rglob("*.pretty"))}


def fp_dir(nick):
    return lib_dirs(LIB_ROOT).get(nick) or KICAD_FP / f"{nick}.pretty"


class Ctx:
    """Everything the checks read, loaded once: the schematic, the lock, and the board (None if there is none)."""

    def __init__(self, sch, lock, pcbnew=None, board=None, board_path=None, why=None):
        self.sch, self.lock, self.pcbnew, self.board, self.board_path, self.why = sch, lock, pcbnew, board, board_path, why
        self.brd, self.dups = board_facts(pcbnew, board) if board is not None else (None, [])
        self._lib = None

    @classmethod
    def load(cls, sch, lock, board_path):
        if board_path is None:
            return cls(sch, lock)
        pcbnew = import_pcbnew()
        try:
            return cls(sch, lock, pcbnew, load_board(pcbnew, board_path), board_path)
        except ValueError as e:
            return cls(sch, lock, why=f"cannot read {rel(board_path)}: {e}")

    @property
    def library(self):
        if self._lib is None and self.pcbnew is not None:
            self._lib = Library(self.pcbnew)
        return self._lib


# ------------------------------------------------------------------------------------------- refs, netlist, footprints
def check_refs(c):
    sch, brd = c.sch, c.brd
    s, b = set(sch), set(brd)
    only = {r for r in b - s if brd[r]["board_only"] and brd[r]["no_bom"] and brd[r]["no_pos"]}
    missing, extra = s - b, (b - s) - only
    dups = set(c.dups)
    if missing or extra or dups:
        said = [f"{w} {refs_str(r, 6)}" for w, r in (("missing", missing), ("extra", extra), ("duplicated", dups)) if r]
        d = [f"missing from the board: {refs_str(missing)}", f"extra on the board: {refs_str(extra)}", f"duplicate refs on the board: {refs_str(dups)}"]
        return Result("refs", FAIL, "board != schematic: " + "; ".join(said), d)
    n = lambda k: sum(1 for p in sch.values() if p["dnp"] == k)                      # noqa: E731
    return Result("refs", PASS, f"{rel(c.board_path) if c.board_path else 'board'}: {len(b) - len(only)} footprints == {len(s)} schematic parts "
                                f"({n('')} placed, {n('dnp')} DNP, {n('pad')} copper-only pads)"
                                + (f"; {len(only)} board-only ignored: {refs_str(only, 4)}" if only else ""))


def read_netlist(path):
    """(parts, pin_nets) from a KiCad netlist: ref -> value/footprint/LCSC/DNP_BOM, and (ref, pin) -> net name."""
    root = sexp(Path(path).read_text(encoding="utf-8"))[0]
    section = lambda name: next(x for x in root if isinstance(x, list) and x[0] == name)[1:]    # noqa: E731
    parts, pin_nets = {}, {}
    for comp in section("components"):
        d = {x[0]: x[1] for x in comp[1:] if len(x) > 1 and isinstance(x[1], str)}
        fields = {f[1][1]: f[2] for f in next((x for x in comp if x[0] == "fields"), [])[1:] if len(f) > 2}
        parts[d["ref"]] = dict(value=d["value"], footprint=d["footprint"], lcsc=fields.get("LCSC", ""), dnp=fields.get("DNP_BOM", ""))
    for net in section("nets"):
        name = next(x[1] for x in net[1:] if isinstance(x, list) and x[0] == "name")
        for node in net[1:]:
            if isinstance(node, list) and node[0] == "node":
                d = {x[0]: x[1] for x in node[1:] if len(x) > 1}
                pin_nets[(d["ref"], d["pin"])] = name
    return parts, pin_nets


def net_diffs(want, have, who):
    """One line per (ref, pin) whose net differs between SKiDL (want) and `who` (have)."""
    keys = sorted(set(want) | set(have), key=lambda k: (nat(k[0]), k[1]))
    return [f"{k[0]}.{k[1]}: {who} net '{have.get(k) or '-'}' != SKiDL '{want.get(k) or '-'}'" for k in keys if want.get(k) != have.get(k)]


def check_netlist(c):
    sch = c.sch
    if not NETLIST.exists():
        return Result("netlist", WARN, f"{rel(NETLIST)} not found: nothing to compare the board source against")
    net, pin_nets = read_netlist(NETLIST)
    diffs = [f"refs only in {where}: {refs_str(refs)}" for where, refs in (("SKiDL", set(sch) - set(net)), ("pod.net", set(net) - set(sch))) if refs]
    for ref in sorted(set(sch) & set(net), key=nat):
        for k in ("value", "footprint", "lcsc", "dnp"):
            if net[ref][k] != sch[ref][k]:
                diffs.append(f"{ref} {k}: pod.net '{net[ref][k]}' != SKiDL '{sch[ref][k]}'")
    nets = net_diffs(sch_pin_nets(sch), pin_nets, "pod.net")
    if diffs or nets:
        return Result("netlist", FAIL, f"pod.net is stale vs gen.py ({len(diffs)} part, {len(nets)} pin-net differences; first: {(diffs + nets)[0]}): "
                      "regenerate with python3 hw/pod/gen.py", diffs + nets)
    return Result("netlist", PASS, f"pod.net == SKiDL for all {len(net)} parts (values, footprints, LCSC, DNP_BOM) and {len(pin_nets)} pin-net assignments")


def check_footprints(c):
    sch, brd = c.sch, c.brd
    bad, flagged = [], {}
    for ref in sorted(set(sch) & set(brd), key=nat):
        s, b = sch[ref], brd[ref]
        if b["name"] != s["fp_name"] or (b["nick"] and b["nick"] != s["lib"]):
            bad.append((ref, f"{ref}: board '{b['nick'] + ':' if b['nick'] else ''}{b['name']}' != schematic '{s['footprint']}'"))
        if s["footprint"] in KNOWN_FOOTPRINT:
            flagged.setdefault(s["footprint"], []).append(ref)
    f = Findings()
    if bad:
        f.add(FAIL, f"{len(bad)} board footprints differ from the schematic's footprint field: {refs_str([r for r, _ in bad], 6)}", [t for _, t in bad])
    for fp, refs in flagged.items():
        ecr, why = KNOWN_FOOTPRINT[fp]
        status, tag = known(ecr)
        f.add(status, f"known-bad footprint {fp.split(':')[1]} on {refs_str(refs, 6)} ({tag})", [f"{refs_str(refs)}: {fp} - {ecr}: {why}"])
    if not any(b["nick"] for b in brd.values()):
        f.lines.append("the board stores bare footprint names (no library nickname): the library is taken from the schematic, pad geometry is the proof")
    return f.result("footprints", f"{len(set(sch) & set(brd))} board footprint names == schematic footprint fields "
                                  f"({len({p['footprint'] for p in sch.values()})} distinct)")


class Library:
    """Loads library footprints through pcbnew; flipped / rotated pad signatures are cached."""

    def __init__(self, pcbnew):
        self.pcbnew, self.scratch, self.cache, self.sigs = pcbnew, pcbnew.BOARD(), {}, {}

    def load_from(self, directory, name):
        key = (str(directory), name)
        if key not in self.cache:
            with quiet_stderr():
                try:
                    self.cache[key] = self.pcbnew.FootprintLoad(str(directory), name)
                except Exception:                                   # noqa: BLE001  (pcbnew raises on bad files)
                    self.cache[key] = None
        return self.cache[key]

    def load(self, nick, name):
        return self.load_from(fp_dir(nick), name)

    def local_sig(self, nick, name, flipped, orient):
        """Pad signature of the library footprint placed at the origin with the board footprint's flip and angle."""
        key = (nick, name, flipped, round(orient, 3))
        if key not in self.sigs:
            fp = self.pcbnew.FootprintLoad(str(fp_dir(nick)), name)  # fresh copy: Flip mutates, and needs a parent board
            self.scratch.Add(fp)
            if flipped:
                fp.Flip(self.pcbnew.VECTOR2I(0, 0), self.pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
            fp.SetOrientationDegrees(orient)
            self.sigs[key] = pad_sig(fp, (0, 0))                      # fp stays on the scratch board, which owns it
        return self.sigs[key]


def pad_sig(fp, origin):
    """(number, centre x, centre y, width, height, drill x, drill y, type, shape, layers) per pad, sorted."""
    sig = []
    for p in fp.Pads():
        bb, c, d = p.GetBoundingBox(), p.GetBoundingBox().GetCenter(), p.GetDrillSize()
        sig.append((p.GetNumber(), c.x - origin[0], c.y - origin[1], bb.GetWidth(), bb.GetHeight(), d.x, d.y,
                    int(p.GetAttribute()), int(p.GetShape()), p.GetLayerSet().FmtHex()))
    return sorted(sig, key=lambda s: (s[0], round(s[1] / 5000), round(s[2] / 5000)))


def sig_diff(a, b):
    """(FAIL|WARN, text) for the worst difference between a board pad signature and its library one, else None."""
    if len(a) != len(b):
        return FAIL, f"{len(a)} pads on the board, {len(b)} in the library"
    if [s[0] for s in a] != [s[0] for s in b]:
        return FAIL, f"pad numbers differ (board {','.join(s[0] or '-' for s in a)}; library {','.join(s[0] or '-' for s in b)})"
    for x, y in zip(a, b):
        n = x[0] or "(unnumbered)"
        if max(abs(x[5] - y[5]), abs(x[6] - y[6])) > PAD_TOL_NM:
            return FAIL, f"pad {n} drill {x[5] / 1e6:.2f} mm, library {y[5] / 1e6:.2f} mm"
        if x[7] != y[7]:
            return FAIL, f"pad {n} type differs (SMD/through-hole/NPTH code {x[7]} vs {y[7]})"
        if x[9] != y[9]:
            return FAIL, f"pad {n} layers differ (paste/mask/copper set changed)"
    shifted = [x for x, y in zip(a, b) if max(abs(x[1] - y[1]), abs(x[2] - y[2])) > PAD_TOL_NM]
    if shifted:
        pa, pb = sorted((s[1], s[2]) for s in a), sorted((s[1], s[2]) for s in b)
        if all(abs(u[0] - v[0]) <= PAD_TOL_NM and abs(u[1] - v[1]) <= PAD_TOL_NM for u, v in zip(pa, pb)):
            return FAIL, f"pad numbers swapped or mirrored (pad {shifted[0][0]} sits where the library has another pad)"
    drift = [(x, y) for x, y in zip(a, b) if max(abs(x[i] - y[i]) for i in range(1, 5)) > PAD_TOL_NM]
    if drift:
        x, y = drift[0]
        return WARN, f"pad {x[0] or '(unnumbered)'} differs by {max(abs(x[i] - y[i]) for i in range(1, 5)) / 1e6:.3f} mm"
    shape = [x for x, y in zip(a, b) if x[8] != y[8]]
    return (WARN, f"pad {shape[0][0]} shape differs") if shape else None


def check_fp_library(c):
    sch, brd, lib = c.sch, c.brd, c.library
    bad, drift = [], []
    for nick, name in sorted({(p["lib"], p["fp_name"]) for p in sch.values()}):
        if lib.load(nick, name) is None:
            bad.append(f"schematic footprint '{nick}:{name}' not found or does not load in {fp_dir(nick)}")
    files = [f for d in lib_dirs(LIB_ROOT).values() for f in sorted(d.glob("*.kicad_mod"))]
    bad += [f"{rel(f)} does not load" for f in files if lib.load_from(f.parent, f.stem) is None]
    for ref in sorted(set(sch) & set(brd), key=nat):
        s, b = sch[ref], brd[ref]
        if lib.load(s["lib"], s["fp_name"]) is None or b["name"] != s["fp_name"]:
            continue
        pos = b["fp"].GetPosition()
        d = sig_diff(pad_sig(b["fp"], (pos.x, pos.y)), lib.local_sig(s["lib"], s["fp_name"], b["flipped"], b["fp"].GetOrientationDegrees()))
        if d:
            drift.append((d[0], ref, f"{ref} {s['footprint']}: {d[1]}"))
    if bad:
        return Result("fp-library", FAIL, f"{len(bad)} footprint(s) missing or unloadable: {bad[0]}", bad)
    if drift:
        status = FAIL if any(s == FAIL for s, _, _ in drift) else WARN
        return Result("fp-library", status, f"{len(drift)} board footprints differ from their library footprint ({'pad count, number, drill, type or layers' if status == FAIL else 'pad position or size'}; "
                      f"library changed after placement, or the board copy was edited): {refs_str([r for _, r, _ in drift], 6)}", [t for _, _, t in drift])
    return Result("fp-library", PASS, f"{len(files)} library footprints load; all {len(set(sch) & set(brd))} board footprints match their library pads "
                                      f"(count, numbers, drill, type, layers; within {PAD_TOL_NM / 1000:.0f} um)")


def check_values(c):
    sch, brd, lib = c.sch, c.brd, c.library
    same, placeholder, wrong = [], [], []
    for ref in sorted(set(sch) & set(brd), key=nat):
        s, b = sch[ref], brd[ref]["value"]
        lf = lib.load(s["lib"], s["fp_name"]) if lib else None
        if b == s["value"]:
            same.append(ref)
        elif b in (s["fp_name"], brd[ref]["name"]) or (lf is not None and b == lf.GetValue()):
            placeholder.append(ref)
        else:
            wrong.append(f"{ref}: board value '{b}' != schematic '{s['value']}'")
    if wrong:
        return Result("values", FAIL, f"{len(wrong)} board values differ from the schematic: {refs_str([w.split(':')[0] for w in wrong], 6)}", wrong)
    if placeholder:
        status, tag = issue("values")
        eg = [f"{r}: board '{brd[r]['value']}' vs schematic '{sch[r]['value']}'" for r in placeholder[:10]] + ([f"(+{len(placeholder) - 10} more)"] if len(placeholder) > 10 else [])
        return Result("values", status, f"{len(placeholder)}/{len(same) + len(placeholder)} board Value fields hold the footprint name, not the schematic value ({tag}); "
                      "JLC files come from gen.py, but a board-based BOM tool would print footprint names", eg)
    return Result("values", PASS, f"{len(same)} board values == schematic values")


def check_nets(c):
    sch, brd = c.sch, c.brd
    refs = sorted(set(sch) & set(brd), key=nat)
    have = board_pad_nets(brd, refs)
    want = {k: v for k, v in sch_pin_nets(sch).items() if k[0] in set(refs)}
    diffs = net_diffs(want, have, "board")
    if diffs:
        return Result("nets", FAIL, f"{len(diffs)} board pad nets differ from gen.py: {diffs[0]}" + (" ..." if len(diffs) > 1 else ""), diffs)
    return Result("nets", PASS, f"all {len(want)} connected pins have the same net on the board as in gen.py ({len(set(want.values()))} nets)")


def assembly_facts(pcbnew, brd):
    """(parts per side, [(ref, pitch mm, is BGA)] for the ICs and transistors) of the fitted parts."""
    smd, circle = pcbnew.PAD_ATTRIB_SMD, pcbnew.PAD_SHAPE_CIRCLE
    sides, pitches = {"F": 0, "B": 0}, []
    for ref, b in brd.items():
        if b["dnp"] or b["no_pos"]:
            continue
        sides["B" if b["flipped"] else "F"] += 1
        pads = [p for p in b["fp"].Pads() if p.GetAttribute() == smd]
        if not ref.startswith(("U", "Q")) or len(pads) < 2:
            continue
        areas = sorted(p.GetSize().x * p.GetSize().y for p in pads)
        keep = [p for p in pads if p.GetSize().x * p.GetSize().y <= 3 * areas[len(areas) // 2]]      # drop an exposed pad
        pts = [(p.GetPosition().x, p.GetPosition().y) for p in keep]
        pitch = min(math.hypot(a[0] - d[0], a[1] - d[1]) for i, a in enumerate(pts) for d in pts[i + 1:]) / 1e6
        grid = len(keep) >= 4 and all(p.GetShape() == circle for p in keep)
        pitches.append((ref, pitch, grid or bool(re.search(r"BGA|CSP", b["name"], re.I))))
    return sides, pitches


def check_assembly_tier(c):
    sides, pitches = assembly_facts(c.pcbnew, c.brd)
    if not (sides["F"] or sides["B"]):
        return Result("assembly-tier", WARN, "no fitted parts on the board: assembly tier not derived")
    why = []
    if sides["F"] and sides["B"]:
        why.append(f"double-sided ({sides['F']} parts F, {sides['B']} B)")
    bga = sorted((r, p) for r, p, g in pitches if g and p < ECON_BGA_PITCH - 1e-6)
    ic = sorted((r, p) for r, p, g in pitches if not g and p < ECON_IC_PITCH - 1e-6)
    if bga:
        why.append(f"BGA {','.join(r for r, _ in bga)} at {min(p for _, p in bga):.2f} mm (Economic needs >= {ECON_BGA_PITCH:.2f})")
    if ic:
        why.append(f"IC pitch {','.join(r for r, _ in ic)} at {min(p for _, p in ic):.2f} mm (Economic needs >= {ECON_IC_PITCH:.2f})")
    tier = "Standard" if why else "Economic"
    details = [f"{r}: smallest pad pitch {p:.2f} mm{' (BGA)' if g else ''}" for r, p, g in sorted(pitches)]
    if tier != ASSUMED_TIER:
        return Result("assembly-tier", WARN, f"the board now qualifies for {tier} PCBA but the cost model assumes {ASSUMED_TIER}: re-run sim/checks/assembly_fees.py", details)
    return Result("assembly-tier", PASS, f"{tier} PCBA needed, as the cost model assumes: " + "; ".join(why or ["single-sided, pitches within the Economic limits"]), details)


# ------------------------------------------------------------------------------------------- identity
def library_identity(root):
    """(file, what, value) for every identity-named property, and every LCSC-shaped number, in a footprint file under root."""
    out = []
    for f in sorted(Path(root).rglob("*.kicad_mod")):
        text = f.read_text(encoding="utf-8", errors="replace")
        for name, val in re.findall(r'\(property\s+"([^"]+)"\s+"([^"]*)"', text):
            if ID_NAME.search(name) and not NOT_ID.search(name):
                out.append((f, name, val))
        seen = {v for g, _, v in out if g == f}
        out += [(f, "(text)", n) for n in dict.fromkeys(LCSC_NUM.findall(text)) if n not in seen]
    return out


def symbol_lcsc():
    """symbol name -> 'LCSC Part' in hw/lib/lcsc/lcsc.kicad_sym (schematic-side identity of the imported symbols)."""
    out = {}
    for block in re.split(r'\n  \(symbol "', SYMBOLS.read_text(encoding="utf-8"))[1:]:
        m = re.search(r'"LCSC Part"\s+"([^"]*)"', block)
        out[block.split('"', 1)[0]] = m[1] if m else ""
    return out


def board_identity(sch, brd):
    """(wrong, stale, agree) from every LCSC number and MPN found on the board footprints, judged against the schematic."""
    wrong, stale, agree = [], [], set()
    for ref in sorted(set(sch) & set(brd), key=nat):
        want, name = sch[ref]["lcsc"], brd[ref]["name"]
        for label, text in brd[ref]["texts"]:
            for num in dict.fromkeys(LCSC_NUM.findall(text or "")):
                if num == want:
                    agree.add(ref)
                elif label == "LCSC Part" and STALE_LCSC.get(name) == num:
                    stale.append((ref, num, want, name))
                else:
                    wrong.append((ref, label, num, want, name))
        row = LCSC_IDENTITY.get(want)
        for label, text in brd[ref]["fields"].items():
            if row and text and MPN_NAME.search(label) and not NOT_ID.search(label) and not mpn_match(row[0], text):
                wrong.append((ref, label, text, row[0], name))
    return wrong, stale, agree


def table_findings(sch, by_lcsc):
    """(wrong, uncovered, covered): the schematic's LCSC numbers against LCSC_IDENTITY, and the lock's MPNs against the table."""
    wrong, uncovered, covered = [], [], 0
    for ref in sorted(sch, key=nat):
        p = sch[ref]
        row = LCSC_IDENTITY.get(p["lcsc"])
        if not p["lcsc"]:
            continue
        if row is None:
            uncovered.append(ref)
            continue
        covered += 1
        mpn, pkg, val = row
        if val is not None:
            have = parse_value(p["value"])
            if have is None or not math.isclose(have, parse_value(val), rel_tol=1e-6, abs_tol=1e-15):
                wrong.append(f"{ref}: gen.py value '{p['value']}', but {p['lcsc']} is {mpn} ({val})")
            elif pkg not in p["fp_name"]:
                wrong.append(f"{ref}: gen.py footprint {p['fp_name']}, but {p['lcsc']} is {mpn} in {pkg}")
        elif not any(mpn_match(mpn, x) for x in (p["name"], p["value"]) if x):
            wrong.append(f"{ref}: gen.py names '{p['name']}' / '{p['value']}', but {p['lcsc']} is {mpn}")
    for lcsc, row in sorted(by_lcsc.items()):
        t = LCSC_IDENTITY.get(lcsc)
        if t and not mpn_match(t[0], row.get("mpn", "")):
            wrong.append(f"lock row {lcsc} says {row.get('mpn')}, LCSC_IDENTITY says {t[0]}")
    return wrong, uncovered, covered


def check_identity(c):
    sch, brd = c.sch, c.brd or {}
    by_lcsc = lock_index(c.lock or [])[0]
    f = Findings()
    baked = library_identity(LIB_ROOT)                                                  # 1. library footprints carry no identity
    if baked:
        f.add(FAIL, f"{len({x[0] for x in baked})} library footprints carry part identity: " + ", ".join(f"{g.name}[{n}={v}]" for g, n, v in baked[:3]),
              [f"{rel(g)}: {n} = {v}" for g, n, v in baked])
    wrong, stale, agree = board_identity(sch, brd)                                      # 2. board footprints
    if wrong:
        f.add(FAIL, f"{len(wrong)} board footprint fields disagree with the schematic: " + ", ".join(f"{r} {n} {v} != {w}" for r, n, v, w, _ in wrong[:3]),
              [f"{r}: {n} = {v}, schematic says {w} (footprint {s})" for r, n, v, w, s in wrong])
    if stale:
        status, tag = known(ISSUE_ECR["stale-lcsc"])
        f.add(status, f"{len(stale)} board footprints carry the pre-cleanup 'LCSC Part' ({tag}): "
              + "; ".join(f"{refs_str([r for r, *_ in g], 4)} {g[0][1]} != {g[0][2]}" for g in group(stale)),
              [f"{r}: LCSC Part = {n}, schematic LCSC {w}, from library file {s}.kicad_mod: WRONG, would order the wrong part" for r, n, w, s in stale])
    legacy = library_identity(LEGACY_ROOT)
    if legacy:
        f.add(WARN, f"{len(legacy)} more in superseded {rel(LEGACY_ROOT)} (outside ECR-0012's cleanup: clean or delete it)",
              [f"{rel(g)}: {n} = {v}" for g, n, v in legacy])
    sym = symbol_lcsc()                                                                 # 3. imported symbols vs gen.py
    mism = [f"{p['ref']}: symbol {p['name']} 'LCSC Part' {sym[p['name']]} != gen.py LCSC {p['lcsc']}"
            for p in sch.values() if p["name"] in sym and sym[p["name"]] and sym[p["name"]] != p["lcsc"]]
    if mism:
        f.add(FAIL, f"{len(mism)} symbols disagree with gen.py: " + mism[0], mism)
    bad, uncovered, covered = table_findings(sch, by_lcsc)                              # 4. the offline identity table
    if bad:
        f.add(FAIL, f"{len(bad)} LCSC numbers are not the part gen.py says: {bad[0]}", bad)
    if uncovered:
        f.add(WARN, f"{len(uncovered)} parts have an LCSC number with no row in LCSC_IDENTITY ({refs_str(uncovered, 6)}): identity unchecked, add the rows")
    n_lib = sum(1 for _ in Path(LIB_ROOT).rglob("*.kicad_mod"))
    used_sym = sum(1 for p in sch.values() if p["name"] in sym)
    ok = (f"no identity in {n_lib} library footprints; board: no disagreeing field ({len(agree)} agreeing); {covered} of "
          f"{covered + len(uncovered)} LCSC parts match the offline table; {used_sym} symbol parts agree with gen.py")
    if f.heads:
        f.lines.insert(0, f"coverage: {ok}")
    return f.result("identity", ok)


def group(rows):
    out = {}
    for r in rows:
        out.setdefault((r[1], r[2], r[3]), []).append(r)
    return list(out.values())


# ------------------------------------------------------------------------------------------- jlc bom, cost bom
def cpl_refs(board_path):
    """(refs, problem): the Ref column of a real `kicad-cli pcb export pos` (the project's command, no --smd-only)."""
    exe = shutil.which("kicad-cli")
    if not exe or board_path is None:
        return None, "kicad-cli not found" if not exe else "no board file"
    with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as tmp:
        out = Path(tmp) / "pos.csv"
        run = subprocess.run([exe, "pcb", "export", "pos", "--format", "csv", "--units", "mm", "--exclude-dnp", "-o", str(out), str(board_path)],
                             capture_output=True, text=True, timeout=60)
        if run.returncode != 0 or not out.exists():
            return None, f"kicad-cli pos failed ({run.returncode}): {run.stderr.strip()[:80]}"
        return {r["Ref"] for r in read_csv(out)}, None


def board_flags(sch, brd):
    out = []
    for ref in sorted(set(sch) & set(brd), key=nat):
        kind, b = sch[ref]["dnp"], brd[ref]
        have = f"DNP={b['dnp']} noBOM={b['no_bom']} noPos={b['no_pos']}"
        if kind == "" and (b["dnp"] or b["no_bom"] or b["no_pos"]):
            out.append(f"{ref} is fitted in the schematic but the board drops it from assembly files ({have})")
        elif kind == "dnp" and not (b["dnp"] and b["no_bom"] and b["no_pos"]):
            out.append(f"{ref} is DNP in the schematic (DNP_BOM=dnp) but the board marks it {have}: it would be placed")
        elif kind == "pad" and not (b["no_bom"] and b["no_pos"]):
            out.append(f"{ref} is a copper-only pad (DNP_BOM=pad) but the board marks it {have}: it would be in the BOM/CPL")
    return out


def check_jlc_bom(c):
    sch, brd = c.sch, c.brd or {}
    if not JLC_BOM.exists():
        return Result("jlc-bom", FAIL, f"{rel(JLC_BOM)} not found")
    header, rows = read_rows(JLC_BOM)
    lacking = {"Comment", "Designator", "Footprint", "LCSC Part #", "Qty"} - set(header)
    if lacking:
        return Result("jlc-bom", FAIL, f"{rel(JLC_BOM)} lacks column(s) {', '.join(sorted(lacking))} (header: {', '.join(header)})")
    placed = {r for r, p in sch.items() if p["dnp"] == ""}
    in_csv, d, dup, degraded = {}, [], [], False
    for row in rows:
        refs = [x.strip() for x in row["Designator"].split(",") if x.strip()]
        if row["Qty"].strip() != str(len(refs)):
            d.append(f"line {row['Comment']} {row['Designator']}: Qty {row['Qty']} != {len(refs)} designators")
        for r in refs:
            if r in in_csv:
                dup.append(r)
            in_csv.setdefault(r, row)
    d += [f"{r} has DNP_BOM='{p['dnp']}' in the schematic: not one of {sorted(DNP_KINDS - {''})} and not fitted" for r, p in sorted(sch.items(), key=lambda kv: nat(kv[0])) if p["dnp"] not in DNP_KINDS]
    d += [f"{r} is placed but has no LCSC in the schematic: JLC cannot source it" for r in sorted(placed, key=nat) if not sch[r]["lcsc"]]
    d += [f"{r} appears in more than one BOM line" for r in sorted(set(dup), key=nat)]
    d += [f"{r} is placed in the schematic but missing from the BOM" for r in sorted(placed - set(in_csv), key=nat)]
    d += [f"{r} is {'DNP/copper-only (DNP_BOM=' + sch[r]['dnp'] + ')' if r in sch else 'not in the schematic'} but is in the BOM" for r in sorted(set(in_csv) - placed, key=nat)]
    for r in sorted(placed & set(in_csv), key=nat):
        row, p = in_csv[r], sch[r]
        for col, have, want in (("LCSC Part #", row["LCSC Part #"], p["lcsc"]), ("Comment", row["Comment"], p["value"]), ("Footprint", row["Footprint"], p["fp_name"])):
            if have != want:
                d.append(f"{r}: BOM {col} '{have}' != schematic '{want or '(none)'}'")
    d += board_flags(sch, brd)
    note = "board not read"
    if brd:
        d += [f"{r} is fitted but its footprint type is neither SMD nor through-hole: --smd-only position files would drop it"
              for r in sorted(placed & set(brd), key=nat) if not brd[r]["attr"] & (c.pcbnew.FP_SMD | c.pcbnew.FP_THROUGH_HOLE)]
        bom = {r for r, b in brd.items() if not b["no_bom"]}
        if bom != set(in_csv):
            d.append(f"BOM refs != board BOM (not excluded from BOM): only in BOM {refs_str(set(in_csv) - bom) or '-'}; only on board {refs_str(bom - set(in_csv)) or '-'}")
        cpl, problem = cpl_refs(c.board_path)
        if cpl is None:
            cpl, degraded, note = {r for r, b in brd.items() if not b["no_pos"]}, True, f"no real CPL, refs inferred from board flags ({problem})"
        else:
            note = "BOM refs == the refs of kicad-cli pcb export pos"
        if cpl != set(in_csv):
            d.append(f"BOM refs != CPL refs: only in BOM {refs_str(set(in_csv) - cpl) or '-'}; only in CPL {refs_str(cpl - set(in_csv)) or '-'}")
    if d:
        return Result("jlc-bom", FAIL, f"{len(d)} disagreement(s): " + d[0] + (" ..." if len(d) > 1 else ""), d)
    return Result("jlc-bom", WARN if degraded else PASS, f"bom_jlc.csv: {len(rows)} lines, {len(placed)} parts == schematic placed parts (value, footprint, LCSC); DNP/pads absent; {note}")


@functools.cache
def load_cost_items(path):
    spec = importlib.util.spec_from_file_location("cost_bom", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.ITEMS


def check_cost_bom(c):
    sch = c.sch
    items = load_cost_items(COST_BOM)
    fitted = {r: p for r, p in sch.items() if not p["dnp"]}
    named, d_fail, d_warn, generic = set(), [], [], []
    for _blk, part, ref, src, qty, _unit, status, _note in items:
        lcsc = re.search(r"\bC\d{4,}\b", src)
        lcsc = lcsc[0] if lcsc else None
        refs = [r for r in re.findall(r"\b[A-Z]{1,2}\d+\b", ref) if r in sch]
        if qty == 0 and re.search(r"removed|old|alt|option", f"{status} {ref}", re.I) and not (refs and "dnp" in status.lower()):
            continue                                                  # documents a part that is not on the pod board
        if not refs:
            if re.fullmatch(r"[A-Z]\*", ref):
                generic.append((ref[0], part, qty))
            continue
        named.update(refs)
        for r in refs:
            if lcsc and sch[r]["lcsc"] and sch[r]["lcsc"] != lcsc:
                d_fail.append(f"bom.py '{part}' ({ref}) says {lcsc}, the schematic has {sch[r]['lcsc']} on {r}")
        want = sum(1 for r in refs if r in fitted and sch[r]["lcsc"])
        if lcsc and want != qty:
            d_warn.append(f"bom.py '{part}' ({ref}) qty {qty}, the schematic fits {want}")
    for prefix, part, qty in generic:
        want = sum(1 for r in fitted if re.fullmatch(prefix + r"\d+", r) and r not in named)
        if want != qty:
            d_warn.append(f"bom.py '{part}' ({prefix}*) qty {qty}, the schematic fits {want} {prefix}* parts not itemised elsewhere")
    covered = {g[0] for g in generic}
    d_warn += [f"{r} ({p['lcsc']}) is fitted but has no cost line in bom.py" for r, p in sorted(fitted.items(), key=lambda kv: nat(kv[0]))
               if p["lcsc"] and r not in named and not (re.fullmatch(r"[A-Z]\d+", r) and r[0] in covered)]
    if COST_CSV.exists():
        csv_rows = [(r["part"], r["ref"], r["source"], r["qty_per_pod"]) for r in read_csv(COST_CSV)]
        if csv_rows != [(i[1], i[2], i[3], str(i[4])) for i in items]:
            d_warn.append("docs/build/bom.csv is stale vs bom.py ITEMS: run python3 docs/build/bom.py")
    if d_fail:
        return Result("cost-bom", FAIL, f"{len(d_fail)} LCSC number(s) in docs/build/bom.py disagree with the schematic: " + d_fail[0], d_fail + d_warn)
    if d_warn:
        status, tag = issue("cost-qty")
        return Result("cost-bom", status, f"LCSC numbers agree, but {len(d_warn)} quantity/coverage mismatch(es) ({tag}): " + d_warn[0], d_warn)
    return Result("cost-bom", PASS, f"docs/build/bom.py: {len(items)} items; LCSC numbers and per-pod quantities agree with the schematic")


# ------------------------------------------------------------------------------------------- lock
STOCK_AFTER = [re.compile(p, re.I) for p in (r"(\d[\d,]*)\*{0,2}\s+in stock", r"(\d[\d,]*)\*{0,2}\s*[|·,]\s*\$", r"stock[: ]+(\d[\d,]*)")]


def stock_near(line, start):
    """The stock figure written right after an LCSC number (which ends at `start`) on a docs line, up to the next LCSC number, or None."""
    nxt = LCSC_NUM.search(line, start)
    seg = line[start:nxt.start() if nxt else len(line)]
    for rx in STOCK_AFTER:
        m = rx.search(seg)
        if m:
            return int(m[1].replace(",", ""))
    return None


def lookup_evidence(lcsc_codes):
    """lcsc -> (where, date, stock or None) for the newest dated JLC lookup on record (a docs line with the number, a date and stock/price words)."""
    files = [REPO / "docs/spec.md"] + sorted((REPO / "docs/system").glob("*.md")) + sorted((REPO / "docs/system/plm/ecr").glob("*.md")) \
        + sorted((REPO / "docs/research").glob("*.md"))
    files = [f for f in files if "methodology" not in f.name]
    found = {}
    for f in files:
        for n, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            m = re.search(r"20\d\d-\d\d-\d\d", line)
            if m and re.search(r"stock|\$\d|price|JLC|API", line):
                for num in LCSC_NUM.finditer(line):
                    if num[0] in lcsc_codes and (num[0] not in found or m[0] > found[num[0]][1]):
                        found[num[0]] = (f"{rel(f)}:{n}", m[0], stock_near(line, num.end()))
    m = re.search(r"20\d\d-\d\d-\d\d", COST_BOM.read_text(encoding="utf-8"))                # bom.py prices: dated in its docstring
    for _, _, _, src, _, unit, *_ in load_cost_items(COST_BOM):
        if m and unit is not None and src in lcsc_codes and src not in found:
            found[src] = (f"{rel(COST_BOM)} (price only)", m[0], None)
    return found


def stock_findings(code, where, stock, date):
    """(status, line) for one LCSC number's stock and the age of the lookup; None if fine."""
    out = []
    age = (TODAY - parse_date(date)).days if parse_date(date) else None
    if age is None:
        out.append((WARN, f"{where}: lookup date '{date}' is unreadable"))
    elif age > LOCK_MAX_AGE_DAYS:
        out.append((WARN, f"{where}: lookup is {age} days old ({date})"))
    if stock is not None and stock == 0:
        out.append((FAIL, f"{where}: stock 0 at {date}"))
    elif stock is not None and stock < LOW_STOCK:
        status, tag = issue(f"stock:{code}")
        out.append((status, f"{where}: stock {stock} at {date} ({tag})"))
    return out


def check_stock_lock(c):
    sch, lock = c.sch, c.lock
    if not lock:
        return Result("stock-lock", FAIL, f"sourcing lock missing or empty: {rel(LOCK)}")
    if LOCK_COLUMNS - set(lock[0]):
        return Result("stock-lock", FAIL, f"{rel(LOCK)} lacks column(s) {', '.join(sorted(LOCK_COLUMNS - set(lock[0])))}")
    by_lcsc, notes = lock_index(lock)
    use = {}
    for p in sch.values():
        if p["lcsc"]:
            use.setdefault(p["lcsc"], []).append(p["ref"])
    missing = sorted(set(use) - set(by_lcsc))
    ev = lookup_evidence(missing)
    undated = [x for x in missing if x not in ev]
    f = Findings()
    other = []                                                          # issues other than "no lock row"
    for code, row in sorted(by_lcsc.items()):
        if code not in use:
            continue
        where = f"{code} ({refs_str(use[code], 4)}, {row['mpn']})"
        status = lock_status(row)
        if status == "REJECTED":
            other.append((FAIL, f"{where} is REJECTED in the lock"))
        elif status != "RECOMMENDED":
            other.append((WARN, f"{where} is only {status or '(no status)'} in the lock"))
        stock = int(row["stock"]) if (row.get("stock") or "").strip().isdigit() else None
        if stock is None:
            other.append((WARN, f"{where}: stock '{row.get('stock')}' is not a number"))
        other += stock_findings(code, where, stock, row.get("queried_utc", ""))
    other += [(WARN, n) for n in notes if n.split()[0] in use]
    for code in missing:
        if code in ev:
            where, date, stock = ev[code]
            other += stock_findings(code, f"{code} ({refs_str(use[code], 4)}) per {where}", stock, date)
    bom_rows = read_csv(JLC_BOM) if JLC_BOM.exists() else []
    for row in bom_rows:
        code, label = row.get("LCSC Part #", ""), row.get("In sourcing lock", "")
        if (label == "yes") != (code in by_lcsc):
            other.append((WARN, f"bom_jlc.csv labels {code} '{label}' but it {'is' if code in by_lcsc else 'is not'} in the lock: regenerate with gen.py"))
    lines = [t for _, t in other] + [f"{x} ({refs_str(use[x], 6)}): no lock row; " + (f"dated lookup {ev[x][1]} in {ev[x][0]}" if x in ev else "NO dated lookup on record") for x in missing]
    for status, text in other:
        if status == FAIL:
            f.add(FAIL, text)
    if missing:
        status, tag = issue("lock-gaps")
        f.add(status, f"{len(missing)} of {len(use)} LCSC numbers have no lock row ({len(undated)} undated{': ' + ', '.join(undated) if undated else ''}; {tag}); add with tools/jlc.py")
    soft = sorted((t for s, t in other if s == WARN), key=lambda text: " stock " not in text)       # supply risks first
    if soft:
        f.add(WARN, f"{len(soft)} other lock issue(s): {soft[0]}")
    f.lines = lines
    return f.result("stock-lock", f"all {len(use)} LCSC numbers on the schematic are in the lock, RECOMMENDED, queried within {LOCK_MAX_AGE_DAYS} days")


def check_lock_drift(c):
    sch, lock = c.sch, c.lock
    if not lock:
        return Result("lock-drift", WARN, f"no sourcing lock to compare the schematic against ({rel(LOCK)}: see stock-lock)")
    by_lcsc, _ = lock_index(lock)
    used = {p["lcsc"] for p in sch.values() if p["lcsc"]}                     # DNP parts count: they keep their identity
    unused = [r for r in by_lcsc.values() if lock_status(r) == "RECOMMENDED" and r["lcsc"] not in used]
    cites = []
    for r in by_lcsc.values():
        for clause in re.split(r";|\.\s", r.get("notes", "")):
            for code in sorted(set(re.findall(r"\bC\d{4,}\b", clause)) - {r["lcsc"]}):
                if code in used and WARNING_WORDS.search(clause):
                    cites.append((code, f"lock row {r['lcsc']} ({r['ref_role']}) says of {code}, which the schematic uses on "
                                        f"{refs_str([p['ref'] for p in sch.values() if p['lcsc'] == code], 4)}: '{clause.strip()}'"))
    f = Findings()
    if unused:
        status, tag = issue("lock-unused")
        f.add(status, f"{len(unused)} RECOMMENDED lock rows name parts the schematic does not use ({', '.join(r['lcsc'] for r in unused)}; {tag})",
              [f"RECOMMENDED but unused: {r['lcsc']} {r['mpn']} ({r['ref_role']})" for r in unused])
    for code, text in cites:
        status, tag = issue(f"lock-note:{code}")
        f.add(status, f"a lock note warns about {code}, which the schematic uses ({tag}): {text.split(': ', 1)[1][:80]}", [text])
    return f.result("lock-drift", "every RECOMMENDED lock row is used by the schematic; no lock note cites a used part")


# ------------------------------------------------------------------------------------------- selftest
_KEEP = []                              # pcbnew objects added to a board: a freed Python wrapper corrupts the board (KiCad 10 SWIG)


def keep(obj):
    _KEEP.append(obj)
    return obj


class Workspace:
    """A scratch copy of everything the checks read, plus a freshly loaded board, so a case can break any of it."""

    def __init__(self, c):
        self.pcbnew, self.sch, self.dropped = c.pcbnew, copy.deepcopy(c.sch), set()
        self.dir = Path(tempfile.mkdtemp(prefix="bom_check_", dir=os.environ.get("TMPDIR")))
        self.paths = dict(NETLIST=self.dir / "pod.net", JLC_BOM=self.dir / "bom_jlc.csv", LOCK=self.dir / "lock.csv",
                          LIB_ROOT=self.dir / "lib", ECR_DIR=self.dir / "ecr", LEGACY_ROOT=self.dir / "legacy")
        for k, src in (("NETLIST", NETLIST), ("JLC_BOM", JLC_BOM), ("LOCK", LOCK)):
            if src.exists():
                shutil.copy(src, self.paths[k])
        for src in LIB_ROOT.rglob("*.kicad_mod"):
            dest = self.paths["LIB_ROOT"] / src.relative_to(LIB_ROOT)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(src, dest)
        self.paths["ECR_DIR"].mkdir()
        self.paths["LEGACY_ROOT"].mkdir()
        for src in ECR_DIR.glob("*.md"):
            shutil.copy(src, self.paths["ECR_DIR"] / src.name)
        self.board = load_board(c.pcbnew, c.board_path)

    def fp(self, ref):
        return next(f for f in self.board.GetFootprints() if f.GetReference() == ref)

    def pads(self, ref):
        return list(self.fp(ref).Pads())

    def set_field(self, ref, name, text):
        fp = self.fp(ref)
        if fp.HasField(name):
            fp.GetField(name).SetText(text)
        else:
            field = keep(self.pcbnew.PCB_FIELD(fp, fp.GetNextFieldOrdinal(), name))
            field.SetText(text)
            fp.Add(field)

    def drop(self, ref):
        """Take a footprint out of the facts the checks see (Board.Remove would orphan a wrapper)."""
        self.fp(ref)
        self.dropped.add(ref)

    def edit(self, key, fn):
        p = self.paths[key]
        p.write_text(fn(p.read_text(encoding="utf-8")), encoding="utf-8")

    def edit_lib(self, name, fn):
        p = next(self.paths["LIB_ROOT"].rglob(f"{name}.kicad_mod"))
        p.write_text(fn(p.read_text(encoding="utf-8")), encoding="utf-8")

    def set_ecr(self, ecr, line):
        p = self.paths["ECR_DIR"] / f"{ecr}.md"
        p.write_text(re.sub(r"^.*Status.*$", line, p.read_text(encoding="utf-8"), count=1, flags=re.M) if line is not None
                     else re.sub(r"^.*Status.*\n", "", p.read_text(encoding="utf-8"), count=1, flags=re.M), encoding="utf-8")

    def evaluate(self, *ids):
        with patched(**self.paths):
            board_path = None
            if "jlc-bom" in ids:
                board_path = self.dir / "board.kicad_pcb"
                with quiet_stderr():
                    self.pcbnew.SaveBoard(str(board_path), self.board)
            ctx = Ctx(self.sch, read_lock(), self.pcbnew, self.board, board_path)
            for ref in self.dropped:
                ctx.brd.pop(ref)
            return {r.id: r for r in run_checks(ctx, only=set(ids))}

    def close(self):
        shutil.rmtree(self.dir, ignore_errors=True)


def move_node(text, ref, pin, to_net):
    node = re.search(rf'\s*\(node\s*\(ref "{ref}"\)\s*\(pin "{pin}"\)\s*\(pintype "[^"]*"\)\)', text)
    text = text.replace(node[0], "", 1)
    head = re.search(rf'\(net\s*\(code \d+\)\s*\(name "{re.escape(to_net)}"\)\s*\(class "[^"]*"\)', text)
    return text[:head.end()] + node[0] + text[head.end():]


def selftest_cases():
    """(what is broken, [(check, statuses it may give)], how to break it): the failures a past review missed, plus the false alarms to avoid."""
    F, P, W, OK = {FAIL}, {PASS}, {WARN}, {PASS, WARN}
    sch_set = lambda ref, **kv: lambda w: w.sch[ref].update(kv)                       # noqa: E731
    # Rev F: Q1/Q2 moved to the clean pod:Nexperia footprint, so the pre-cleanup copy is exercised on SW1 (lcsc footprint)
    stale_q1 = lambda w: w.set_field("SW1", "LCSC Part", "C221708")                  # noqa: E731

    def duplicate(w):
        w.board.Add(keep(w.pcbnew.Cast_to_FOOTPRINT(w.fp("R3").Duplicate(False))))

    def fiducial(w):
        fid = keep(w.pcbnew.FOOTPRINT(w.board))
        fid.SetReference("FID1")
        fid.SetBoardOnly(True)
        fid.SetExcludedFromBOM(True)
        fid.SetExcludedFromPosFiles(True)
        w.board.Add(fid)

    def extra(w):
        fid = keep(w.pcbnew.FOOTPRINT(w.board))
        fid.SetReference("X1")
        w.board.Add(fid)

    def renamed_fp(w):
        w.fp("R3").SetFPID(w.pcbnew.LIB_ID("", "R_0603_1608Metric"))

    def drill(w):
        next(p for p in w.pads("U2") if p.GetAttribute() == w.pcbnew.PAD_ATTRIB_NPTH).SetDrillSize(w.pcbnew.VECTOR2I(200000, 200000))

    def no_paste(w):
        for p in w.pads("U3"):
            ls = p.GetLayerSet()
            ls.RemoveLayer(w.pcbnew.F_Paste)
            ls.RemoveLayer(w.pcbnew.B_Paste)
            p.SetLayerSet(ls)

    def swapped(w):
        a, b = w.pads("R3")
        a.SetNumber("2")
        b.SetNumber("1")

    def pad_grow(w):
        p = w.pads("R3")[0]
        p.SetSizeX(p.GetSize().x + 3000)

    def pad_move(w):
        p = w.pads("R3")[0]
        p.SetPosition(w.pcbnew.VECTOR2I(p.GetPosition().x + 500000, p.GetPosition().y))

    def net_moved(w):
        w.pads("R3")[1].SetNet(w.board.FindNet("GND") if w.pads("R3")[1].GetNetname() != "GND" else w.board.FindNet("+3V0"))

    def flags(**kv):
        return lambda w: [getattr(w.fp("R3"), f"Set{k}")(v) for k, v in kv.items()]

    def csv_edit(fn):
        return lambda w: w.edit("JLC_BOM", fn)

    def lock_edit(fn):
        return lambda w: w.edit("LOCK", fn)

    def lock_rows(fn):
        def go(w):
            rows = read_csv(w.paths["LOCK"])
            rows = fn(rows)
            with open(w.paths["LOCK"], "w", newline="", encoding="utf-8") as f:
                out = csv.DictWriter(f, fieldnames=list(rows[0]))
                out.writeheader()
                out.writerows(rows)
        return go

    def lock_row(code, **kv):
        def go(rows):
            return [dict(r, **kv) if r["lcsc"] == code else r for r in rows]
        return go

    def two_rows(order):
        def go(rows):
            base = next(r for r in rows if r["lcsc"] == "C19654206")
            old, new = dict(base, status="REJECTED", queried_utc="2026-09-01T00:00Z"), dict(base, status="RECOMMENDED", queried_utc="2026-09-30T00:00Z")
            return [r for r in rows if r is not base] + ([old, new] if order else [new, old])
        return go

    def drop_board_side(w):
        for ref, b in board_facts(w.pcbnew, w.board)[0].items():
            if b["flipped"] or ref in ("U3", "Q1", "Q2"):
                w.drop(ref)

    def bench_lib(w):
        d = w.paths["LIB_ROOT"] / "bench.pretty"
        d.mkdir()
        shutil.copy(next(w.paths["LIB_ROOT"].rglob("L0806.kicad_mod")), d / "Bench.kicad_mod")
        w.sch["R3"].update(footprint="bench:Bench", lib="bench", fp_name="Bench")

    def known_bad_fp(w):
        w.sch["Q1"].update(footprint="lcsc:SOT1216_L1.1-W1.0-P0.35-BL-EP", lib="lcsc", fp_name="SOT1216_L1.1-W1.0-P0.35-BL-EP")
        w.fp("Q1").SetFPID(w.pcbnew.LIB_ID("", "SOT1216_L1.1-W1.0-P0.35-BL-EP"))

    def ecr(ecr_id, line):
        return lambda w: (stale_q1(w), w.set_ecr(ecr_id, line))

    def ecr_fp(line):
        return lambda w: (known_bad_fp(w), w.set_ecr("ECR-0004", line))

    return [
        ("a footprint removed", [("refs", F, "missing R3")], lambda w: w.drop("R3")),
        ("a footprint duplicated", [("refs", F, "duplicated R3")], duplicate),
        ("a footprint renamed", [("refs", F, "extra R99")], lambda w: w.fp("R3").SetReference("R99")),
        ("an unexcluded extra footprint", [("refs", F, "extra X1")], extra),
        ("a board-only fiducial (excluded from BOM and pos)", [("refs", P), ("jlc-bom", P)], fiducial),
        ("a footprint swapped for another", [("footprints", F, "R3: board")], renamed_fp),
        ("a value changed on the board", [("values", F, "R3: board value")], lambda w: w.fp("R3").SetValue("1Meg")),
        ("a fitted part marked DNP", [("jlc-bom", F, "R3 is fitted in the schematic but")], flags(DNP=True)),
        ("a fitted part excluded from position files", [("jlc-bom", F, "R3 is fitted in the schematic but")], flags(ExcludedFromPosFiles=True)),
        ("a fitted part with no SMD/THT type", [("jlc-bom", F, "R3 is fitted but its footprint type")], lambda w: w.fp("R3").SetAttributes(0)),
        ("known-bad footprint, ECR-0004 open", [("footprints", W, "ECR-0004 proposed")], known_bad_fp),
        ("known-bad footprint, ECR-0004 'closed.'", [("footprints", F, "ECR-0004 closed")], ecr_fp("Status: closed.")),
        ("wrong LCSC in field 'Vendor PN'", [("identity", F, "Q1 Vendor PN C552750")], lambda w: w.set_field("Q1", "Vendor PN", "C552750")),
        ("wrong LCSC in field 'PN'", [("identity", F, "SW1 PN C221708")], lambda w: w.set_field("SW1", "PN", "C221708")),
        ("wrong LCSC in the description", [("identity", F, "Q1 library description")], lambda w: w.fp("Q1").SetLibDescription("PMCXB290UE LCSC C552750")),
        ("wrong LCSC in a footprint text item", [("identity", F, "R3 text")], lambda w: w.fp("R3").Add(_text(w, "C552750"))),
        ("wrong 'LCSC' field on a resistor", [("identity", F, "R3 LCSC C25744")], lambda w: w.set_field("R3", "LCSC", "C25744")),
        ("correct 'LCSC Part' written back by the placer", [("identity", OK)], lambda w: w.set_field("R3", "LCSC Part", w.sch["R3"]["lcsc"])),
        ("JLC rotation offset field (not identity)", [("identity", OK)], lambda w: (w.set_field("U2", "JLCPCB Rotation Offset", "180"), w.set_field("U3", "JLCPCB Position Offset", "0.1,0"))),
        ("pre-cleanup 'LCSC Part', ECR-0012 proposed", [("identity", W, "ECR-0012 proposed")], stale_q1),
        ("pre-cleanup 'LCSC Part', ECR-0012 implemented", [("identity", W, "ECR-0012 implemented")], ecr("ECR-0012", "Status: implemented (awaiting owner review)")),
        ("pre-cleanup 'LCSC Part', ECR-0012 'closed.'", [("identity", F, "ECR-0012 closed")], ecr("ECR-0012", "Status: closed.")),
        ("pre-cleanup 'LCSC Part', ECR-0012 'verified, 2026-10-03'", [("identity", F, "ECR-0012 verified")], ecr("ECR-0012", "Status: verified, 2026-10-03")),
        ("pre-cleanup 'LCSC Part', ECR-0012 '**Status:** closed'", [("identity", F, "ECR-0012 closed")], ecr("ECR-0012", "**Status:** closed")),
        ("pre-cleanup 'LCSC Part', ECR-0012 has no Status line", [("identity", F, "no Status: line in ECR-0012.md")], ecr("ECR-0012", None)),
        ("a pad drill shrunk", [("fp-library", F, "U2")], drill),
        ("paste layers removed from a part's pads", [("fp-library", F, "U3")], no_paste),
        ("pad numbers 1 and 2 swapped", [("fp-library", F, "R3")], swapped),
        ("a pad enlarged by 3 um", [("fp-library", W, "R3")], pad_grow),
        ("a pad moved by 0.5 mm", [("fp-library", W, "R3")], pad_move),
        ("a pad on the wrong net", [("nets", F, "R3.2")], net_moved),
        ("pod.net: a pin moved to another net", [("netlist", F, "R3.2")], lambda w: w.edit("NETLIST", lambda t: move_node(t, "R3", "2", "GND" if w.sch["R3"]["pins"]["2"] != "GND" else "+3V0"))),
        ("pod.net: a net renamed", [("netlist", F, "GND_X")], lambda w: w.edit("NETLIST", lambda t: t.replace('(name "GND")', '(name "GND_X")'))),
        ("pod.net: a value changed", [("netlist", F, "R3 value")], lambda w: w.edit("NETLIST", lambda t: re.sub(r'(\(ref "R3"\)\s*\(value ")[^"]*', r"\g<1>1Meg", t, count=1))),
        ("1M resistors given the 10k LCSC everywhere", [("identity", F, "R8: gen.py value '1M'")], lambda w: [w.sch[r].update(lcsc="C25744") for r in ("R8", "R9")]),
        ("every 100n capacitor given the 10u 0603 LCSC", [("identity", F, "gen.py value '100n'")], lambda w: [p.update(lcsc="C19702") for p in w.sch.values() if p["value"] == "100n"]),
        ("a part with an LCSC the table does not know", [("identity", W, "no row in LCSC_IDENTITY")], sch_set("R3", lcsc="C99999")),
        ("a placed part with no LCSC", [("jlc-bom", F, "C2 is placed but has no LCSC")], lambda w: (w.sch["C2"].update(lcsc=""), w.edit("JLC_BOM", lambda t: t.replace(",C1525,", ",,", 1)))),
        ("an unknown DNP_BOM kind", [("jlc-bom", F, "DNP_BOM='maybe'")], sch_set("R3", dnp="maybe")),
        ("BOM csv with a byte-order mark", [("jlc-bom", P)], csv_edit(lambda t: "\ufeff" + t)),
        ("BOM csv designators with spaces", [("jlc-bom", P)], csv_edit(lambda t: t.replace('"C1,C10,C13', '"C1, C10, C13', 1))),
        ("BOM csv group split over two rows", [("jlc-bom", P)], csv_edit(lambda t: t.replace('"C1,C10,C13,C19,C2,C3,C6",C_0402_1005Metric,C1525,7,yes', '"C1,C10,C13,C19",C_0402_1005Metric,C1525,4,yes\n100n,"C2,C3,C6",C_0402_1005Metric,C1525,3,yes', 1))),
        ("BOM csv with a wrong LCSC", [("jlc-bom", F, "R3: BOM LCSC Part #")], csv_edit(lambda t: t.replace(",C25741,", ",C25744,", 1))),
        ("BOM csv with a renamed header", [("jlc-bom", F, "lacks column")], csv_edit(lambda t: t.replace("LCSC Part #", "LCSC", 1))),
        ("sourcing lock deleted", [("stock-lock", F, "missing or empty"), ("lock-drift", W, "no sourcing lock")], lambda w: w.paths["LOCK"].unlink()),
        ("a lock row with an empty queried_utc", [("stock-lock", W, "unreadable")], lock_rows(lock_row("C25741", queried_utc=""))),
        ("a lock row with stock 0", [("stock-lock", F, "stock 0")], lock_rows(lock_row("C25741", stock="0"))),
        ("a lock row with stock n/a", [("stock-lock", W, "not a number")], lock_rows(lock_row("C25741", stock="n/a"))),
        ("a lock row with status 'rejected'", [("stock-lock", F, "REJECTED")], lock_rows(lock_row("C25741", status="rejected"))),
        ("an older REJECTED row before a newer RECOMMENDED one", [("stock-lock", W, "different statuses")], lock_rows(two_rows(True))),
        ("an older REJECTED row after a newer RECOMMENDED one", [("stock-lock", W, "different statuses")], lock_rows(two_rows(False))),
        ("a lock MPN swapped", [("identity", F, "lock row C25741")], lock_rows(lock_row("C25741", mpn="0402WGF2202TCE"))),
        ("a library footprint with a 'Vendor PN' property", [("identity", F, "Vendor PN")], lambda w: w.edit_lib("L0806", lambda t: t.replace("(layer F.Cu)", '(layer F.Cu)\n  (property "Vendor PN" "C337891")', 1))),
        ("a library footprint with an LCSC number in its description", [("identity", F, "(text)")], lambda w: w.edit_lib("L0806", lambda t: t.replace("(layer F.Cu)", '(layer F.Cu)\n  (descr "LCSC C337891")', 1))),
        ("a library footprint with a JLC offset property", [("identity", OK)], lambda w: w.edit_lib("L0806", lambda t: t.replace("(layer F.Cu)", '(layer F.Cu)\n  (property "JLCPCB Rotation Offset" "90")', 1))),
        ("a new project library (hw/lib/bench.pretty)", [("fp-library", OK)], bench_lib),
        ("a single-sided board with wide pitches", [("assembly-tier", W, "Economic")], drop_board_side),
    ]


def _text(w, content):
    t = keep(w.pcbnew.PCB_TEXT(w.board))
    t.SetText(content)
    return t


def driver_cases():
    """(what is broken, whether the driver reacted correctly): board lookup and crash containment."""
    with patched(BOARD_GLOB="no/such/dir/*.kicad_pcb"):
        none_found = resolve_board(None, False)
    crashed = safe("x", lambda c: 1 / 0, None)
    return [("no placed board anywhere in hw/pod", none_found[0] is None and "no placed board" in (none_found[1] or "")),
            ("an explicit --board that does not exist", resolve_board(Path("/no/such.kicad_pcb"), False)[1] is not None),
            ("--no-board", resolve_board(None, True) == (None, None)),
            ("a check that raises", crashed.status == FAIL and "check crashed" in crashed.msg)]


def selftest(c, results):
    base = {r.id: r.status for r in results}
    ran, wrong, skipped = 0, [], []
    for name, wants, mutate in selftest_cases():
        if any(base.get(want[0]) == FAIL for want in wants):
            skipped.append(f"'{name}': the unmodified {'/'.join(want[0] for want in wants)} already FAILs")
            continue
        w = Workspace(c)
        try:
            mutate(w)
            got = w.evaluate(*{want[0] for want in wants})
        except StopIteration:
            skipped.append(f"'{name}': the design no longer has what it breaks")
            continue
        except Exception as e:                                       # noqa: BLE001
            wrong.append(f"'{name}': the case crashed: {type(e).__name__}: {e}")
            continue
        finally:
            w.close()
        ran += 1
        for check, allowed, *needle in wants:
            res = got.get(check)
            text = f"{res.msg} {' '.join(res.details)}" if res else ""
            if res is None or res.status not in allowed or "crashed" in res.msg or (needle and needle[0] not in text):
                wrong.append(f"'{name}': {check} gave {res.status + ' ' + res.msg[:90] if res else 'nothing'}, wanted {'/'.join(sorted(allowed))}"
                             + (f" mentioning '{needle[0]}'" if needle else ""))
    for name, ok in driver_cases():
        ran += 1
        if not ok:
            wrong.append(f"'{name}': the driver did not behave")
    if wrong:
        return Result("selftest", FAIL, f"{len(wrong)} of {ran} mutated inputs gave the wrong result: {wrong[0]}", wrong)
    if skipped:
        return Result("selftest", WARN, f"{ran} mutated inputs give the expected result; {len(skipped)} skipped: {skipped[0]}", skipped)
    return Result("selftest", PASS, f"{ran} of {ran} mutated inputs (broken copies of the board, pod.net, BOM, lock, libraries, ECRs, schematic) give the expected result")


# ------------------------------------------------------------------------------------------- driver
CHECKS = [("refs", check_refs), ("netlist", check_netlist), ("footprints", check_footprints), ("fp-library", check_fp_library),
          ("values", check_values), ("nets", check_nets), ("assembly-tier", check_assembly_tier), ("identity", check_identity),
          ("jlc-bom", check_jlc_bom), ("cost-bom", check_cost_bom), ("stock-lock", check_stock_lock), ("lock-drift", check_lock_drift)]
BOARD_ONLY = {"refs", "footprints", "fp-library", "values", "nets", "assembly-tier"}      # these need a readable board


def safe(cid, fn, *args):
    """Run one check; a crash becomes that check's FAIL so the others still report."""
    try:
        return fn(*args)
    except Exception as e:                                          # noqa: BLE001
        return Result(cid, FAIL, f"check crashed: {type(e).__name__}: {e}", traceback.format_exc().splitlines()[-6:])


def run_checks(c, only=None):
    return [safe(cid, fn, c) for cid, fn in CHECKS if (only is None or cid in only) and not (cid in BOARD_ONLY and c.brd is None)]


def resolve_board(arg, no_board):
    """(path, error): an explicit --board must exist; otherwise the newest placed board under hw/pod."""
    if no_board:
        return None, None
    if arg:
        return (arg, None) if arg.is_file() else (None, f"no such board file: {arg}")
    found = sorted(REPO.glob(BOARD_GLOB), key=lambda p: p.stat().st_mtime)
    return (found[-1], None) if found else (None, f"no placed board found ({BOARD_GLOB}); pass --board PATH, or --no-board to skip the board checks")


def run(board_path, board_err, do_selftest=True):
    sch = read_schematic()
    c = Ctx.load(sch, read_lock(), board_path)
    out = []
    if board_err:
        out.append(Result("board", FAIL, board_err))
    elif board_path is None:
        out.append(Result("board", WARN, "board checks skipped (--no-board): the placed board is not being compared"))
    elif c.board is None:
        out.append(Result("board", FAIL, f"{c.why}; the board checks did not run"))
    out += run_checks(c)
    if do_selftest and c.board is not None:
        out.append(safe("selftest", selftest, c, out))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--board", type=Path, help="placed or routed .kicad_pcb to check (default: the newest hw/pod/*/pod_*_placed.kicad_pcb)")
    ap.add_argument("--no-board", action="store_true", help="skip the board checks (a WARN says so)")
    ap.add_argument("--json", action="store_true", help="machine-readable results")
    ap.add_argument("-v", "--verbose", action="store_true", help="print detail lines under each non-PASS result")
    ap.add_argument("--strict", action="store_true", help="treat WARN as FAIL (release gate)")
    ap.add_argument("--no-selftest", action="store_true", help="skip the deliberately-broken-input proofs")
    args = ap.parse_args(argv)
    env_error = ensure_env()
    path, board_err = (None, None) if env_error else resolve_board(args.board, args.no_board)
    results = [Result("env", FAIL, env_error)] if env_error else run(path, board_err, not args.no_selftest)
    if args.strict:
        for r in results:
            if r.status == WARN:
                r.status, r.msg = FAIL, r.msg + " [--strict]"
    if args.json:
        counts = {s: sum(r.status == s for r in results) for s in (PASS, WARN, FAIL)}
        print(json.dumps({"date": TODAY.isoformat(), "board": str(path) if path else None, "counts": counts, "checks": [r.as_dict() for r in results]}, indent=2))
    else:
        for r in results:
            print(f"{r.status} {r.id} {r.msg}")
            if args.verbose and r.status != PASS:
                for line in r.details:
                    print(f"     - {line}")
    return 2 if board_err else 1 if any(r.status == FAIL for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
