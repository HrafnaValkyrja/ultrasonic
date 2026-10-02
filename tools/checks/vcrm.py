#!/usr/bin/env python3
"""Requirement -> verification matrix (VCRM): does every requirement have a way to be proven, and does that way exist?

    python3 tools/checks/vcrm.py [--json] [-v] [--strict] [--no-live] [--board PATH] [--root DIR]
    python3 tools/checks/vcrm.py --hashes        # current spec-block hashes (to refresh a row's spec_hash after a re-review)
    python3 tools/checks/vcrm.py --table         # print the generated tables of docs/system/vcrm.md
    python3 tools/checks/vcrm.py --update-md     # rewrite the generated block of docs/system/vcrm.md
    python3 tools/checks/vcrm.py --update-pins [--refresh-pin PATH|all ...]   # (re)write the evidence_pins block of vcrm.yaml
    python3 tools/checks/vcrm.py --lock          # the section1_lock record for the working tree's section 1
    python3 tools/checks/vcrm.py --baseline      # the stage_c_baseline list for the current rows

Layout-agnostic and read-only apart from the two --update flags (vcrm.md's generated block, vcrm.yaml's pins block). It reads
docs/system/vcrm.yaml, docs/spec.md, docs/system/plm/items.yaml and ecr/, docs/system/integration-map.md, git, and runs
tools/checks/interfaces.py and bom_check.py (--json, about 3-4 s, in parallel) to read the live result of every check a row cites.
PyYAML only; plain python3 works (the two scripts need the harness venv: it finds /opt/ultrasonic-tools/venv itself, and a live
step that cannot run is a WARN, never a PASS). One line per check, "PASS|WARN|FAIL <id> <message>"; exit 1 if any FAIL. A FAIL
prints its detail lines (first 10; -v shows all, and the details of every other result), --json prints machine-readable results,
--strict turns every WARN not listed in the matrix's `acknowledged:` map into a FAIL (release gate), --no-live skips the two
scripts, --root DIR (or $VCRM_ROOT) points the whole checker at another tree (a scratch copy for tests).

Why: the PLM tracker detects change, not disagreement (docs/research/methodology.md, improvement 8). Nothing showed how each
requirement will be proven met, or that the proof exists. Section 1 of the spec is owner-locked, so its text is held against a
git commit (not against the matrix, which anyone can edit in the same change).

Checks
  schema      the file's shape and every row: known keys only, types, required fields, id/kind/spec_block agree, statuses agree
              (done only if every stage is done, and a done row has no open ECR and no known failure), partial/done rows cite
              evidence, open rows say what is missing and what to do next, a row with no stage C says why; duplicate YAML keys fail
  coverage    every section-1 requirement read from the spec and EVERY decision (D<n>) and owner item (O<n>) of the spec has a row,
              a `covers:` entry or a recorded waiver (`not_verifiable:`); numbered/lettered sub-items (O12 a-c, O16 1-7) each
              need a row that cites them; no mvp row points at a requirement the spec does not have
  lock        section 1 of docs/spec.md is byte-identical to the text at the commit recorded in `section1_lock`
              (git is the baseline; a section1_unlock reason downgrades it to a WARN)
  verbatim    each section-1 row's `text` equals the spec text exactly
  artefacts   every artefact resolves: a file (never a directory, '.', or a pattern wider than 12 files, nothing outside the repo,
              never CLAUDE.md, the spec or the matrix itself), an E/S/C item of the spec, an interfaces:/bom_check: id that the
              script's docstring Checks block lists (the script must parse), ERC, DRC
  evidence    every evidence entry is an existing file or commit; partial/done rows have evidence; each file is pinned in
              `evidence_pins` (a hash) and WARNs when it changed since the matrix was reviewed
  tracked     cited files that git does not track (a commit without them leaves the matrix pointing at nothing)
  live        the live status of every cited interfaces:/bom_check: check: FAIL fails; WARN is listed with the rows resting on it;
              a done row may not rest on a non-PASS check
  owners      every owner_items id is an item of docs/system/plm/items.yaml; every function is an F-row of the integration map
  ecrs        every cited ECR exists and has a Status line; open means proposed/approved (tools/plm.py's definition), implemented
              means awaiting owner review, anything else is closed; WARN lists rows waiting on each open ECR, stale citations of
              closed ones, and open ECRs no row cites (unless `ecrs_no_row:` says why)
  spec-drift  decision/owner rows carry a hash of the spec block they summarise; WARN when the block changed since the review
  known-fail  WARN lists rows whose design is known not to meet the requirement today, each with the ECR or doc that tracks it
  summary     rows by stage and status; requirements with no stage C (each states why); a row that left `stage_c_baseline` (stage
              C was started, now is not) is a WARN; scripts no row cites (details with -v)
  md          the generated tables in docs/system/vcrm.md are current (WARN: run --update-md)
"""
from __future__ import annotations

import argparse
import ast
import concurrent.futures
import datetime as dt
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

import yaml

MD_BEGIN, MD_END = "<!-- vcrm:begin", "<!-- vcrm:end -->"
PINS_BEGIN, PINS_END = "# vcrm:pins:begin", "# vcrm:pins:end"
BOARDS = "hw/pod/**/*.kicad_pcb"
ANALYSIS_GLOBS = ("sim/checks/*.py", "sim/dsp/*.py", "tools/checks/*.py")
MAX_GLOB = 12                                         # a cited pattern may match this many files, no more
LIVE_TIMEOUT = 120
TODAY = dt.date.today()

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"
KINDS = {"mvp", "decision", "owner"}
METHODS = {"Test", "Analysis", "Inspection", "Demonstration"}
STAGES = ("C", "D")
STAGE_NAME = {"C": "in a computer, before hardware", "D": "on rev 1: bench, wear, field"}
STATUSES = ("done", "partial", "not-started")
C_ROLES = ("decides", "surrogate")
# plm.py counts an ECR open for these two (tools/plm.py status); 'implemented' waits for the owner; every other word is closed
OPEN_ECR, REVIEW_ECR = {"proposed", "approved"}, {"implemented"}
STATUS_RE = re.compile(r"^[ \t>*-]*status[ \t]*\**[ \t]*[:\-][ \t]*\**[ \t]*([A-Za-z][A-Za-z-]*)", re.I | re.M)
ID_RE = re.compile(r"(S1\.1-goal|S1\.2-C\d+|S1\.3-T\d+|[DO]\d+[a-z]?(-[A-Za-z0-9][\w-]*)?)$")
COVERS_RE = re.compile(r"[DO]\d+[a-z]?(\(\w+\))?$")
# what a row may carry, with the type of each key
KEY_TYPES = {"id": str, "kind": str, "source": str, "spec_block": str, "spec_hash": str, "text": str, "method": list, "stage": list,
             "c_role": str, "c_none_reason": str, "status": str, "status_by_stage": dict, "owner_items": list, "functions": list,
             "artefacts": list, "planned": (list, str), "evidence": list, "ecrs": list, "related": list, "covers": list,
             "next": str, "known_fail": str, "known_fail_ref": str, "gap": str}
REQUIRED_KEYS = ("kind", "source", "text", "method", "stage", "status", "owner_items", "artefacts")
REQUIRED_TOP = ("requirements", "section1_lock", "evidence_pins", "stage_c_baseline")
TOP_TYPES = {"version": int, "updated": (str, dt.date), "requirements": list, "section1_lock": dict, "section1_unlock": str,
             "evidence_pins": dict, "stage_c_baseline": list, "not_verifiable": dict, "ecrs_no_row": dict, "acknowledged": dict}
# cited as a verification artefact or as evidence, these prove nothing: instructions, the spec, the matrix itself
NOT_EVIDENCE = {"CLAUDE.md", "README.md", "docs/spec.md", "docs/system/vcrm.yaml", "docs/system/vcrm.md", "tools/checks/vcrm.py"}


# ------------------------------------------------------------------------------------------- paths
def set_root(root):
    """Every path the checker reads hangs off one root, so a scratch copy of the repo can be checked (tests)."""
    global REPO, SPEC, VCRM, VCRM_MD, ITEMS, ECR_DIR, INTEGRATION_MAP, SCRIPTS, ERC_SOURCE
    REPO = Path(root).resolve()
    SPEC, VCRM, VCRM_MD = REPO / "docs/spec.md", REPO / "docs/system/vcrm.yaml", REPO / "docs/system/vcrm.md"
    ITEMS, ECR_DIR = REPO / "docs/system/plm/items.yaml", REPO / "docs/system/plm/ecr"
    INTEGRATION_MAP = REPO / "docs/system/integration-map.md"
    SCRIPTS = {"interfaces": REPO / "tools/checks/interfaces.py", "bom_check": REPO / "tools/checks/bom_check.py"}
    ERC_SOURCE = REPO / "hw/pod/gen.py"
    have_git.cache_clear()


# ------------------------------------------------------------------------------------------- plumbing
class LoadError(Exception):
    pass


class Result:
    def __init__(self, cid, status, msg, details=(), keys=()):
        self.id, self.status, self.msg, self.details, self.keys = cid, status, msg, list(details), list(keys)

    def as_dict(self):
        return {"id": self.id, "status": self.status, "message": self.msg, "details": self.details, "keys": self.keys}


def worst(*statuses):
    return FAIL if FAIL in statuses else WARN if WARN in statuses else PASS


def one_line(e, n=240):
    return " ".join(str(e).split())[:n]


def ids_str(ids, limit=10):
    ids = list(ids)
    return ", ".join(ids[:limit]) + (f" (+{len(ids) - limit} more)" if len(ids) > limit else "")


def norm_id(s):
    return str(s).replace("_", "-")


def lst(r, key):
    """A row's list field, or [] when it is missing or the wrong type (schema reports that)."""
    v = r.get(key)
    return list(v) if isinstance(v, list) else []


def rel(p):
    return Path(p).resolve().relative_to(REPO).as_posix()


def stage_status(row, stage):
    sbs = row.get("status_by_stage")
    return (sbs.get(stage) if isinstance(sbs, dict) else None) or row.get("status")


def overall_status(statuses):
    s = set(statuses)
    return "done" if s == {"done"} else "not-started" if s == {"not-started"} else "partial"


def row_stages(r):
    return [s for s in lst(r, "stage") if s in STAGES]


# ------------------------------------------------------------------------------------------- git
@lru_cache(maxsize=None)
def have_git():
    return git("rev-parse", "--git-dir")[0] == 0


def git(*args):
    """(return code, stdout); (None, '') when git cannot be run at all."""
    try:
        p = subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None, ""
    return p.returncode, p.stdout


def commit_state(h):
    """ok | missing | nogit. A short or ambiguous hash that git cannot resolve to one commit counts as missing."""
    if not have_git():
        return "nogit"
    rc, _ = git("rev-parse", "--verify", "--quiet", f"{h}^{{commit}}")
    return "ok" if rc == 0 else "missing"


set_root(Path(__file__).resolve().parents[2])


def tracked_files():
    if not have_git():
        return None
    rc, out = git("ls-files", "-z")
    return set(out.split("\0")) - {""} if rc == 0 else None


# ------------------------------------------------------------------------------------------- the spec
def spec_section(lines, start_re, level):
    """The lines under the first heading matching start_re, up to the next heading of that level or higher."""
    i = next((n for n, line in enumerate(lines) if re.match(start_re, line)), None)
    out = []
    for line in lines[i + 1:] if i is not None else []:
        if re.match(rf"#{{1,{level}}} ", line):
            break
        out.append(line)
    return out


def section1_slice(text):
    """The raw text of spec section 1, heading included, up to the next level-2 heading."""
    lines = text.replace("\r\n", "\n").split("\n")
    i = next((n for n, line in enumerate(lines) if line.startswith("## 1. MVP")), None)
    if i is None:
        return ""
    j = next((n for n in range(i + 1, len(lines)) if lines[n].startswith("## ")), len(lines))
    return "\n".join(lines[i:j]).strip()


def slice_sha(s):
    return hashlib.sha256(s.encode()).hexdigest()[:16]


def parse_section1(lines):
    """Spec section 1 as written: {row id: text} for the goal, each owner constraint, each success test, and anything else in it."""
    out, sub, last, n_bullet = {}, None, None, 0
    for line in spec_section(lines, r"## 1\. MVP", 2):
        text = line.strip()
        if m := re.match(r"### (1\.\d+)", line):
            sub, last = m[1], None
        elif not text or text == "---":
            last = None if not text else last
        elif sub == "1.1":
            out["S1.1-goal"] = out["S1.1-goal"] + "\n" + line if "S1.1-goal" in out else line
        elif sub == "1.2" and (m := re.match(r"(\d+)\. (.+)$", line)):
            last = f"S1.2-C{m[1]}"
            out[last] = m[2]
        elif sub == "1.3" and (m := re.match(r"- (\*\*(T\d+)\b.*)$", line)):
            out[f"S1.3-{m[2]}"] = m[1]
            last = f"S1.3-{m[2]}"
        elif sub == "1.3" and (m := re.match(r"- (.+)$", line)):
            n_bullet += 1
            last = f"S1.3-bullet{n_bullet}"
            out[last] = m[1]
        elif sub in ("1.2", "1.3") and last:
            out[last] += "\n" + line                      # a continuation line belongs to the item above
        elif sub:
            last = f"S{sub}-text"
            out[last] = out[last] + "\n" + line if last in out else line
    return out


def parse_blocks(lines):
    """{D17: text of its ### block, O12: its table row} for the decision and owner items."""
    blocks, cur = {}, None
    for line in lines:
        if m := re.match(r"### (D\d+)\.", line):
            cur = m[1]
            blocks[cur] = [line]
        elif re.match(r"(#{1,3} |---$)", line):
            cur = None
        elif cur:
            blocks[cur].append(line)
        if m := re.match(r"\|\s*(?:~~)?\**(O\d+[a-z]?)\**(?:~~)?\s*\|", line):
            blocks[m[1]] = [line]
    return {k: "\n".join(v).strip() for k, v in blocks.items()}


def sub_items(item, text):
    """The numbered (1)(2).. or lettered (a)(b).. sub-requirements of an owner item, in order."""
    if not item.startswith("O"):
        return []
    for pat, one, two in ((r"\((\d+)\)", "(1)", "(2)"), (r"\(([a-z])\)", "(a)", "(b)")):
        if one in text and two in text:
            return list(dict.fromkeys(re.findall(pat, text)))
    return []


def parse_tasks(lines):
    """Item ids of spec 12.E (E), 12.C (C) and the section 10 stages (S)."""
    def ids(section_lines, pat):
        return {m[1] for line in section_lines if (m := re.match(pat, line))}
    return {"E": ids(spec_section(lines, r"### E\. ", 3), r"\| (E\d+) \|"),
            "C": ids(spec_section(lines, r"### C\. ", 3), r"\| (C\d+) \|"),
            "S": ids(lines, r"\| \*\*(S\d+)\b")}


def block_hash(text):
    return hashlib.sha256(" ".join(text.split()).encode()).hexdigest()[:10]


def file_pin(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:10]


class UniqueKeyLoader(yaml.SafeLoader):
    """safe_load that refuses a key written twice in one mapping (the second would silently win)."""

    def construct_mapping(self, node, deep=False):
        seen = set()
        for k, _ in node.value:
            key = self.construct_object(k, deep=True)
            if key in seen:
                raise yaml.constructor.ConstructorError(None, None, f"duplicate key {key!r}", k.start_mark)
            seen.add(key)
        return super().construct_mapping(node, deep)


def load():
    """(doc, spec). Raises LoadError with a one-line reason for a missing file, a YAML error or a duplicate key."""
    try:
        spec_lines = SPEC.read_text().splitlines()
    except OSError as e:
        raise LoadError(f"cannot read {SPEC.relative_to(REPO)}: {e.strerror}")
    spec = {"s1": parse_section1(spec_lines), "blocks": parse_blocks(spec_lines), "tasks": parse_tasks(spec_lines)}
    try:
        doc = yaml.load(VCRM.read_text(), Loader=UniqueKeyLoader)
    except OSError as e:
        raise LoadError(f"cannot read {VCRM.relative_to(REPO)}: {e.strerror}")
    except yaml.YAMLError as e:
        raise LoadError(f"{VCRM.relative_to(REPO)} is not valid YAML: {one_line(e)}")
    return doc, spec


def shape_problems(doc):
    """What must hold before any check can read the matrix at all."""
    if not isinstance(doc, dict):
        return ["the file is not a mapping"]
    p = [f"unknown top-level key {k!r}" for k in doc if k not in TOP_TYPES]
    p += [f"missing top-level key {k!r}" for k in REQUIRED_TOP if k not in doc]
    p += [f"top-level {k!r} has the wrong type ({type(v).__name__})" for k, v in doc.items()
          if k in TOP_TYPES and not isinstance(v, TOP_TYPES[k])]
    rows = doc.get("requirements")
    if isinstance(rows, list):
        if not rows:
            p.append("requirements is empty: 0 rows")
        for n, r in enumerate(rows, 1):
            if not isinstance(r, dict) or not isinstance(r.get("id"), str):
                p.append(f"requirements entry {n} is not a mapping with a string id")
    return p


# ------------------------------------------------------------------------------------------- ECR
def ecr_state(ecr):
    """The first word of the ECR's Status line (lower case); 'missing' when no such file; 'none' when it has no Status line."""
    f = ECR_DIR / f"{ecr}.md"
    if not f.is_file():
        return "missing"
    m = STATUS_RE.search("\n".join(f.read_text().splitlines()[:14]))
    return m[1].lower() if m else "none"


def ecr_class(state):
    return "open" if state in OPEN_ECR else "review" if state in REVIEW_ECR else "closed"


def all_ecrs():
    return {p.stem: ecr_state(p.stem) for p in sorted(ECR_DIR.glob("ECR-*.md"))} if ECR_DIR.is_dir() else {}


def row_ecrs(r):
    """ECR ids a row cites: its ecrs list and any ECR named in known_fail_ref."""
    return [str(e) for e in lst(r, "ecrs")] + re.findall(r"ECR-\d+", str(r.get("known_fail_ref") or ""))


# ------------------------------------------------------------------------------------------- script check ids
@lru_cache(maxsize=None)
def script_check_ids(path):
    """(ids, problem): the check ids in the Checks block of the script's docstring ('  <id>  <text>' lines)."""
    try:
        tree = ast.parse(Path(path).read_text())
    except (OSError, SyntaxError, ValueError) as e:
        return set(), f"{rel(path)} does not parse: {one_line(e, 100)}"
    doc = ast.get_docstring(tree, clean=False) or ""
    ids, inside = set(), False
    for line in doc.splitlines():
        if line.strip() == "Checks" and not line.startswith(" "):
            inside = True
        elif inside and line and not line.startswith(" "):
            break
        elif inside and (m := re.match(r"  ([a-z][\w-]*)\s+\S", line)):
            ids.add(norm_id(m[1]))
    return ids, (None if ids else f"{rel(path)} has no 'Checks' block in its docstring")


def check_refs(rows):
    """{(script, id): [row ids]} for every interfaces:<id> / bom_check:<id> artefact."""
    refs = defaultdict(list)
    for r in rows:
        for a in lst(r, "artefacts"):
            if m := re.fullmatch(r"(interfaces|bom_check):([\w-]+)", str(a)):
                refs[(m[1], norm_id(m[2]))].append(r["id"])
    return refs


# ------------------------------------------------------------------------------------------- path resolution
def resolve_path(a, allow_glob=True):
    """(files, problem): the repo files a path (or pattern) names. A directory, '.', an escape or a wide pattern is a problem."""
    a = str(a).split("#", 1)[0].strip()                      # 'docs/spec.md#d3' cites the file
    if not a:
        return [], "empty path"
    if os.path.isabs(a):
        return [], "absolute path"
    p = REPO / a
    try:
        p.resolve().relative_to(REPO)
    except ValueError:
        return [], "path leaves the repository"
    if p.exists():                                           # a name with [] in it is a file before it is a pattern
        return ([], "is a directory: cite the files in it") if p.is_dir() else ([p], None)
    if allow_glob and re.search(r"[*?\[]", a):
        hits = [Path(h) for h in glob.glob(str(REPO / a), recursive=True) if Path(h).is_file()]
        if len(hits) > MAX_GLOB:
            return [], f"pattern matches {len(hits)} files (limit {MAX_GLOB}): cite the files"
        return (hits, None) if hits else ([], "no such path")
    return [], "no such path"


def is_path_ref(a):
    a = str(a)
    return not (re.fullmatch(r"[ESC]\d+", a) or re.fullmatch(r"(interfaces|bom_check):[\w-]+", a) or a in ("ERC", "DRC"))


def is_commit(e):
    return bool(re.fullmatch(r"[0-9a-f]{7,40}", str(e)))


# ------------------------------------------------------------------------------------------- checks
def kind_of(rid):
    return "mvp" if rid.startswith("S1.") else "decision" if rid.startswith("D") else "owner" if rid.startswith("O") else None


def row_problems(r, spec, seen):
    rid = str(r.get("id"))
    p = []
    if rid in seen:
        p.append("duplicate id")
    seen.add(rid)
    if not ID_RE.match(rid):
        p.append("id is not S1.1-goal / S1.2-C<n> / S1.3-T<n> / <D|O item>[-aspect]")
    p += [f"unknown key {k!r} (a misspelt key is ignored silently otherwise)" for k in r if k not in KEY_TYPES]
    p += [f"{k} must be {getattr(t, '__name__', 'a list or a string')} (got {type(r[k]).__name__}); quote values YAML would turn into numbers"
          for k, t in KEY_TYPES.items() if k in r and not isinstance(r[k], t)]
    p += [f"missing {k}" for k in REQUIRED_KEYS if r.get(k) in (None, "", [])]
    kind, stages = r.get("kind"), row_stages(r)
    if kind not in KINDS:
        p.append(f"kind {kind!r}")
    elif kind_of(rid) and kind != kind_of(rid):
        p.append(f"kind {kind} does not fit the id (S1.* is mvp, D<n> decision, O<n> owner)")
    if bad_m := {str(m) for m in lst(r, "method")} - METHODS:
        p.append(f"method {sorted(bad_m)}")
    if not stages or {str(s) for s in lst(r, "stage")} - set(STAGES):
        p.append(f"stage {r.get('stage')!r} (use C and/or D)")
    sbs = r.get("status_by_stage")
    if len(stages) > 1 and not sbs:
        p.append("two stages need status_by_stage")
    if isinstance(sbs, dict) and ({str(k) for k in sbs} != set(stages) or {str(v) for v in sbs.values()} - set(STATUSES)):
        p.append("status_by_stage keys must equal stage, values done|partial|not-started")
    if "C" in stages and r.get("c_role") not in C_ROLES:
        p.append("c_role must be decides or surrogate when stage includes C")
    if "C" not in stages and not r.get("c_none_reason"):
        p.append("no stage C: say why in c_none_reason (a requirement nothing can check before hardware is a rev-1 discovery, O18)")
    status = r.get("status")
    if status not in STATUSES:
        p.append(f"status {status!r}")
    elif status != overall_status(stage_status(r, s) for s in stages):
        p.append("status disagrees with status_by_stage (done only if all stages are done, not-started only if none started)")
    if status in ("done", "partial") and not lst(r, "evidence"):
        p.append(f"status {status} needs evidence")
    if status != "done" and not (r.get("gap") and r.get("next")):
        p.append("an open row needs gap and next")
    if status == "done":
        if r.get("known_fail"):
            p.append("status done contradicts known_fail")
        if open_e := [e for e in row_ecrs(r) if ecr_class(ecr_state(e)) in ("open", "review")]:
            p.append(f"status done while {', '.join(open_e)} is still open or awaiting review")
    if r.get("known_fail") and not r.get("known_fail_ref"):
        p.append("known_fail needs known_fail_ref: the ECR or doc that tracks it (say 'none' with the reason when nothing does)")
    for e in lst(r, "ecrs"):
        if not re.fullmatch(r"ECR-\d{4}", str(e)):
            p.append(f"ecrs entry {e!r} is not ECR-<4 digits>")
    p += [f"covers entry {c!r} is not D<n>, O<n> or O<n>(<sub>)" for c in lst(r, "covers") if not COVERS_RE.match(str(c))]
    if kind in ("decision", "owner"):
        block = r.get("spec_block")
        if block not in spec["blocks"]:
            p.append(f"spec_block {block!r} not found in the spec")
        elif block != rid.split("-")[0]:
            p.append(f"spec_block {block} is not the row's item {rid.split('-')[0]} (the row would track the wrong spec block)")
        elif not re.fullmatch(r"[0-9a-f]{10}", str(r.get("spec_hash") or "")):
            p.append("spec_hash missing or not 10 hex digits, quoted (python3 tools/checks/vcrm.py --hashes)")
    return p


def check_schema(doc, spec):
    rows, seen, bad = doc["requirements"], set(), []
    for r in rows:
        if p := row_problems(r, spec, seen):
            bad.append(f"{r['id']}: " + "; ".join(p))
    for key in ("not_verifiable", "ecrs_no_row", "acknowledged"):
        bad += [f"{key}.{k}: the reason must be a non-empty string" for k, v in (doc.get(key) or {}).items() if not (isinstance(v, str) and v.strip())]
    bad += [f"evidence_pins.{k}: the pin must be a quoted 10-digit hex string" for k, v in doc["evidence_pins"].items()
            if not re.fullmatch(r"[0-9a-f]{10}", str(v)) or not isinstance(v, str)]
    if bad:
        return Result("schema", FAIL, f"{len(bad)} problem(s) in the matrix", bad)
    return Result("schema", PASS, f"{len(rows)} rows well-formed ({len(seen)} unique ids), known keys only, kinds, spec blocks and statuses agree")


def covered_by(rows, item):
    return [r["id"] for r in rows if r["id"] == item or r["id"].startswith(item + "-") or item in map(str, lst(r, "covers"))
            or any(str(c).startswith(item + "(") for c in lst(r, "covers"))]


def claimed_subs(rows):
    claims = set()
    for r in rows:
        claims |= set(re.findall(r"\b([OD]\d+[a-z]?)\((\w+)\)", str(r.get("source") or "") + " " + " ".join(map(str, lst(r, "covers")))))
    return claims


def check_coverage(doc, spec):
    rows, s1, blocks = doc["requirements"], spec["s1"], spec["blocks"]
    ids = {r["id"] for r in rows}
    waived = doc.get("not_verifiable") or {}
    missing = [f"{i}: section-1 requirement in the spec has no row" for i in s1 if i not in ids]
    orphans = [f"{r['id']}: mvp row for a requirement the spec does not have" for r in rows if r.get("kind") == "mvp" and r["id"] not in s1]
    if not s1.get("S1.1-goal") or not any(i.startswith("S1.2-C") for i in s1) or not any(i.startswith("S1.3-T") for i in s1):
        missing.append("could not read section 1 of the spec (goal, constraints or tests missing)")
    sort_key = lambda x: (x[0], int(re.sub(r"\D", "", x) or 0), x)
    n_row = n_waived = 0
    claimed = claimed_subs(rows)
    for item in sorted(blocks, key=sort_key):
        has_row = covered_by(rows, item)
        if has_row and item in waived:
            orphans.append(f"{item}: has a row ({has_row[0]}) and a not_verifiable waiver: keep one")
        elif item in waived:
            n_waived += 1
        elif not has_row:
            missing.append(f"{item}: spec item with no row, covers: entry or not_verifiable waiver")
        else:
            n_row += 1
            missing += [f"{item}({m}): sub-requirement no row cites (put {item}({m}) in a row's source or covers)"
                        for m in sub_items(item, blocks[item]) if (item, m) not in claimed]
    orphans += [f"not_verifiable.{k}: not an item of the spec" for k in waived if k not in blocks]
    orphans += [f"{r['id']}: covers {c} is not an item of the spec" for r in rows for c in map(str, lst(r, "covers"))
                if re.match(r"[DO]\d", c) and c.split("(")[0] not in blocks]
    if missing or orphans:
        return Result("coverage", FAIL, f"{len(missing)} requirement(s) without a row or waiver, {len(orphans)} orphan or conflicting entr(ies)",
                      missing + orphans)
    n_c = sum(i.startswith("S1.2-C") for i in s1)
    n_t = sum(i.startswith("S1.3-T") for i in s1)
    subs = sorted(f"{i}({sub_items(i, blocks[i])[0]}-{sub_items(i, blocks[i])[-1]})" for i in blocks if sub_items(i, blocks[i]) and i not in waived)
    return Result("coverage", PASS, f"section 1 (goal, {n_c} constraints, {n_t} tests) and all {len(blocks)} spec D/O items: {n_row} have rows, "
                  f"{n_waived} are waived with a reason (not_verifiable); sub-items {' '.join(subs)} each cited ({len(rows)} rows)")


def first_diff(a, b, la="matrix", lb="spec"):
    n = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
    return f"first difference at character {n}: {la} {a[max(0, n - 20):n + 25]!r} vs {lb} {b[max(0, n - 20):n + 25]!r}"


def check_lock(doc):
    lock = doc["section1_lock"]
    commit, sha = str(lock.get("commit") or ""), str(lock.get("sha256") or "")
    if not is_commit(commit) or not re.fullmatch(r"[0-9a-f]{16}", sha):
        return Result("lock", FAIL, "section1_lock needs commit (a hash, quoted) and sha256 (16 hex digits, quoted): python3 tools/checks/vcrm.py --lock")
    work = section1_slice(SPEC.read_text())
    base_text = git("show", f"{commit}:docs/spec.md")[1] if have_git() else ""
    base = section1_slice(base_text) if base_text else None
    if base is not None and slice_sha(base) != sha:
        return Result("lock", FAIL, f"section1_lock is inconsistent: commit {commit[:9]} holds section 1 with sha {slice_sha(base)}, "
                      f"the matrix records {sha}")
    want = slice_sha(base) if base is not None else sha
    if slice_sha(work) == want:
        if base is None:
            return Result("lock", WARN, f"section 1 matches the sha recorded in vcrm.yaml, but commit {commit[:9]} cannot be read here "
                          f"(no git history): the baseline is the matrix itself", keys=["lock:no-git"])
        return Result("lock", PASS, f"section 1 of docs/spec.md is identical to the owner-locked text (commit {commit[:9]}, sha {sha})")
    detail = [first_diff(work, base, "spec now", f"commit {commit[:9]}")] if base is not None else []
    unlock = str(doc.get("section1_unlock") or "").strip()
    if unlock:
        return Result("lock", WARN, f"section 1 differs from the lock (commit {commit[:9]}); unlocked in vcrm.yaml: {unlock}", detail, ["lock:unlocked"])
    return Result("lock", FAIL, f"docs/spec.md section 1 differs from the owner-locked text (commit {commit[:9]}): revert docs/spec.md section 1. "
                  f"If the owner changed it: commit that change, record it (vcrm.py --lock) in section1_lock and copy the new text into the mvp rows", detail)


def check_verbatim(doc, spec):
    by_id = {r["id"]: r for r in doc["requirements"]}
    bad = []
    for rid, want in spec["s1"].items():
        row = by_id.get(rid)
        if row is None:
            continue                                                  # coverage reports the missing row
        got = str(row.get("text", ""))
        if got.strip() != want.strip():
            bad.append(f"{rid}: {first_diff(got.strip(), want.strip())}")
    if bad:
        return Result("verbatim", FAIL, f"{len(bad)} section-1 text(s) differ from docs/spec.md: if the owner did not change section 1, "
                      "revert docs/spec.md (see lock); if she did, copy the new text into the row", bad)
    return Result("verbatim", PASS, f"all {len(spec['s1'])} section-1 texts match docs/spec.md exactly")


def resolve_artefact(a, spec):
    """(status, problem or None): PASS if it resolves, WARN if it cannot be checked yet, FAIL if it does not."""
    a = str(a)
    if m := re.fullmatch(r"([ESC])(\d+)", a):
        return (PASS, None) if a in spec["tasks"][m[1]] else (FAIL, f"{a} is not in the spec ({ {'E': '12.E', 'S': 'section 10', 'C': '12.C'}[m[1]] })")
    if m := re.fullmatch(r"(interfaces|bom_check):([\w-]+)", a):
        path = SCRIPTS[m[1]]
        if not path.exists():
            return WARN, f"{a}: {rel(path)} does not exist yet"
        ids, problem = script_check_ids(path)
        if problem:
            return FAIL, f"{a}: {problem}"
        return (PASS, None) if norm_id(m[2]) in ids else (FAIL, f"{a}: {rel(path)} lists no check '{m[2]}' (it lists: {', '.join(sorted(ids))})")
    if a == "ERC":
        return (PASS, None) if ERC_SOURCE.exists() else (FAIL, "ERC: hw/pod/gen.py is missing")
    if a == "DRC":
        return (PASS, None) if glob.glob(str(REPO / BOARDS), recursive=True) else (FAIL, f"DRC: no board file under {BOARDS}")
    files, problem = resolve_path(a)
    if problem:
        return FAIL, f"{a}: {problem}"
    if bad := [rel(f) for f in files if rel(f) in NOT_EVIDENCE or rel(f).startswith(".claude/")]:
        return FAIL, f"{a}: {bad[0]} is not a verification artefact (instructions, the spec or the matrix itself)"
    return PASS, None


def check_artefacts(doc, spec):
    fails, pending, n = [], {}, 0                                    # pending: check id -> rows that cite it
    for r in doc["requirements"]:
        for a in lst(r, "artefacts"):
            n += 1
            status, problem = resolve_artefact(a, spec)
            if status == FAIL:
                fails.append(f"{r['id']}: {problem}")
            elif status == WARN:
                pending.setdefault(str(a), []).append(r["id"])
    details = [f"{a} (cited by {ids_str(v, 6)})" for a, v in sorted(pending.items())]
    if fails:
        return Result("artefacts", FAIL, f"{len(fails)} artefact reference(s) do not resolve", fails + details)
    if pending:
        tools = sorted({rel(SCRIPTS[a.split(":")[0]]) for a in pending})
        return Result("artefacts", WARN, f"{n - len(pending)} references resolve, but {len(pending)} check id(s) cannot be verified until "
                      f"{', '.join(tools)} exists: {ids_str(sorted(pending))}", details, [f"artefacts:{a}" for a in pending])
    return Result("artefacts", PASS, f"all {n} artefact references resolve (files, E/S/C items, check ids listed by the scripts, ERC, DRC)")


def evidence_files(rows):
    """{path: [row ids]} for the file entries of every row's evidence."""
    out = defaultdict(list)
    for r in rows:
        for e in lst(r, "evidence"):
            if not is_commit(e):
                out[str(e)].append(r["id"])
    return out


def check_evidence(doc):
    rows, pins = doc["requirements"], doc["evidence_pins"]
    fails, stale, n, commits_nogit = [], [], 0, []
    for r in rows:
        for e in map(str, lst(r, "evidence")):
            n += 1
            if is_commit(e):
                state = commit_state(e)
                if state == "missing":
                    fails.append(f"{r['id']}: evidence commit {e} does not exist (or is ambiguous)")
                elif state == "nogit":
                    commits_nogit.append(e)
                continue
            files, problem = resolve_path(e, allow_glob=False)
            if problem:
                fails.append(f"{r['id']}: evidence {e}: {problem}")
            elif rel(files[0]) in NOT_EVIDENCE or rel(files[0]).startswith(".claude/"):
                fails.append(f"{r['id']}: evidence {e} is not evidence (instructions, the spec or the matrix itself)")
    files = evidence_files(rows)
    for path, ids in sorted(files.items()):
        f = REPO / path
        if not f.is_file():
            continue                                                  # reported above
        if path not in pins:
            fails.append(f"{path}: no pin in evidence_pins (cited by {ids_str(ids, 4)}): review the file, then python3 tools/checks/vcrm.py --update-pins")
        elif str(pins[path]) != file_pin(f):
            stale.append(f"{path}: changed since the matrix was reviewed (pin {pins[path]}, now {file_pin(f)}); re-read {ids_str(ids, 6)}, "
                         f"then --update-pins --refresh-pin {path}")
    unused = sorted(set(pins) - set(files))
    if fails:
        return Result("evidence", FAIL, f"{len(fails)} evidence problem(s)", fails + stale)
    notes = stale + [f"pin for {p}: no row cites it (python3 tools/checks/vcrm.py --update-pins prunes it)" for p in unused]
    if commits_nogit:
        notes.append(f"cannot verify {len(commits_nogit)} evidence commit(s) here (no git repository): {ids_str(commits_nogit, 4)}")
    if notes:
        return Result("evidence", WARN, f"{n} evidence references resolve; {len(stale)} file(s) changed since the matrix was reviewed, "
                      f"{len(unused)} unused pin(s), {len(commits_nogit)} commit(s) unverifiable here", notes,
                      [f"evidence:{s.split(':')[0]}" for s in stale] + ["evidence:pins"] * len(unused) + ["evidence:no-git"] * bool(commits_nogit))
    return Result("evidence", PASS, f"all {n} evidence references resolve; {len(files)} files and {n - sum(map(len, files.values()))} commits, "
                  "every file unchanged since its pin")


def check_tracked(doc, tracked):
    if tracked is None:
        return Result("tracked", WARN, "cannot tell which cited files git tracks here (no git repository)", keys=["tracked:no-git"])
    untracked = defaultdict(list)
    for r in doc["requirements"]:
        refs = [a for a in lst(r, "artefacts") + lst(r, "evidence") if is_path_ref(a) and not is_commit(a)]
        refs += [rel(SCRIPTS[m[1]]) for a in lst(r, "artefacts") if (m := re.match(r"(interfaces|bom_check):", str(a)))]
        for a in refs:
            for f in resolve_path(a)[0]:
                if rel(f) not in tracked and r["id"] not in untracked[rel(f)]:
                    untracked[rel(f)].append(r["id"])
    if untracked:
        rows = {i for v in untracked.values() for i in v}
        return Result("tracked", WARN, f"{len(untracked)} cited file(s) are not tracked by git ({ids_str(sorted(untracked), 4)}): rows {ids_str(sorted(rows), 4)} "
                      "would point at files a commit does not contain; git add them with the matrix",
                      [f"{p} (cited by {ids_str(v, 5)})" for p, v in sorted(untracked.items())], [f"tracked:{p}" for p in sorted(untracked)])
    return Result("tracked", PASS, "every cited file is tracked by git")


# ------------------------------------------------------------------------------------------- live results of the cited checks
def live_python():
    py = Path(os.environ.get("ULTRA_VENV") or "/opt/ultrasonic-tools/venv") / "bin/python3"
    return str(py) if py.exists() else sys.executable


def run_script(script, extra):
    """{'checks': {id: result}} from `script --json`, or {'error': why}."""
    try:
        p = subprocess.run([live_python(), str(script), "--json", "--no-selftest", *extra], cwd=REPO, capture_output=True, text=True,
                           timeout=LIVE_TIMEOUT)
    except subprocess.TimeoutExpired:
        return {"error": f"timed out after {LIVE_TIMEOUT} s"}
    except OSError as e:
        return {"error": one_line(e)}
    try:
        data = json.loads(p.stdout)
        return {"checks": {norm_id(c["id"]): c for c in data["checks"]}}
    except (ValueError, KeyError, TypeError):
        tail = (p.stderr.strip().splitlines() or [""])[-1]
        return {"error": f"exit {p.returncode}, no JSON on stdout ({one_line(tail, 120)})"}


def start_live(args):
    """Start both scripts at once; returns {name: future}, or None when --no-live."""
    if args.no_live:
        return None
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=len(SCRIPTS))
    extra = ["--board", args.board] if args.board else []
    return {n: pool.submit(run_script, p, extra) if p.exists() else None for n, p in SCRIPTS.items()}


def check_live(doc, futures):
    if futures is None:
        return Result("live", WARN, "the live results of the cited checks were skipped (--no-live)", keys=["live:skipped"])
    rows = {r["id"]: r for r in doc["requirements"]}
    refs = check_refs(doc["requirements"])
    results = {n: (f.result() if f else {"error": "the script does not exist"}) for n, f in futures.items()}
    unavailable = [f"{n}: {res['error']} (rows citing it are unchecked: {ids_str(sorted({i for (s, _), v in refs.items() if s == n for i in v}), 5)})"
                   for n, res in results.items() if "error" in res and any(s == n for s, _ in refs)]
    fails, warns, notrun, counts = [], [], [], Counter()
    for (script, cid), ids in sorted(refs.items()):
        ids = list(dict.fromkeys(ids))
        if "error" in results.get(script, {}):
            continue
        c = results[script]["checks"].get(cid)
        if c is None:
            notrun.append(f"{script}:{cid} is not in the live output (cited by {ids_str(ids, 4)})")
            continue
        st, msg = c["status"], " ".join(str(c.get("message", "")).split())
        counts[(script, st)] += 1
        if st == FAIL:
            fails.append(f"{script}:{cid} is FAIL now (cited by {ids_str(ids, 4)}): {msg[:170]}")
        elif st == WARN:
            hint = sorted(set(re.findall(r"ECR-\d+", json.dumps(c))))
            lacking = [i for i in ids if hint and not set(hint) & set(row_ecrs(rows[i]))]
            warns.append((f"{script}:{cid}", f"{script}:{cid} is WARN (rows {ids_str(ids, 5)}): {msg[:150]}"
                          + (f" [the check cites {', '.join(hint)}; {ids_str(lacking, 3)} list none of them]" if lacking else "")))
        if st != PASS:
            fails += [f"{i}: status done but rests on {script}:{cid}, which is {st}" for i in ids if rows[i].get("status") == "done"]
    per = "; ".join(f"{s} " + ", ".join(f"{counts[(s, st)]} {st}" for st in (PASS, WARN, FAIL) if counts[(s, st)])
                    for s in SCRIPTS if any(counts[(s, st)] for st in (PASS, WARN, FAIL)))
    msg = f"{sum(counts.values())} cited checks read live ({per or 'none'})"
    if unavailable or notrun:
        msg += f"; {len(unavailable) + len(notrun)} could not be read"
    status = FAIL if fails else WARN if warns or unavailable or notrun else PASS
    return Result("live", status, msg, fails + [w for _, w in warns] + unavailable + notrun,
                  [f"live:{k}" for k, _ in warns] + ["live:unavailable"] * len(unavailable) + ["live:not-run"] * len(notrun))


# ------------------------------------------------------------------------------------------- more checks
def check_owners(doc):
    rows = doc["requirements"]
    try:
        items = set((yaml.safe_load(ITEMS.read_text()) or {}).get("items") or {})
    except (OSError, yaml.YAMLError, AttributeError) as e:
        return Result("owners", FAIL, f"cannot read {ITEMS.relative_to(REPO)}: {one_line(e, 100)}")
    row_ids = {q["id"] for q in rows}
    funcs = set(re.findall(r"^\| (F\d+) ", INTEGRATION_MAP.read_text(), re.M)) if INTEGRATION_MAP.exists() else set()
    bad = [f"{r['id']}: owner item {i} is not in docs/system/plm/items.yaml" for r in rows for i in lst(r, "owner_items") if i not in items]
    bad += [f"{r['id']}: function {f} is not an F-row of integration-map.md" for r in rows for f in lst(r, "functions") if f not in funcs]
    bad += [f"{r['id']}: related row {x} does not exist" for r in rows for x in lst(r, "related") if x not in row_ids]
    if bad:
        return Result("owners", FAIL, f"{len(bad)} owner/function/related reference(s) do not resolve", bad)
    used = {i for r in rows for i in lst(r, "owner_items")}
    return Result("owners", PASS, f"owner_items resolve to {len(used)} of {len(items)} plm items; functions and related rows resolve")


def check_ecrs(doc):
    rows = doc["requirements"]
    states, no_row = all_ecrs(), doc.get("ecrs_no_row") or {}
    cited = defaultdict(list)
    for r in rows:
        for e in dict.fromkeys(row_ecrs(r)):
            cited[e].append(r["id"])
    missing = [f"{ids_str(v, 4)}: {e} not found in docs/system/plm/ecr/" for e, v in sorted(cited.items()) if e not in states and not (ECR_DIR / f"{e}.md").is_file()]
    missing += [f"{ids_str(v, 4)}: {e} has no Status line (expected 'Status: <word>')" for e, v in sorted(cited.items()) if states.get(e) == "none"]
    missing += [f"ecrs_no_row.{e}: no such ECR" for e in no_row if e not in states]
    if missing:
        return Result("ecrs", FAIL, f"{len(missing)} ECR reference(s) do not resolve", missing)
    waiting = {e: v for e, v in cited.items() if ecr_class(states[e]) == "open"}
    review = {e: v for e, v in cited.items() if ecr_class(states[e]) == "review"}
    stale = [f"{e} is {states[e]} (cited by {ids_str(v, 4)}); re-review those rows" for e, v in sorted(cited.items()) if ecr_class(states[e]) == "closed"]
    uncited = sorted(e for e, s in states.items() if ecr_class(s) == "open" and e not in cited and e not in no_row)
    waived = [f"ecrs_no_row.{e}: waiver is stale ({'cited by a row' if e in cited else 'ECR is ' + states[e]})" for e in no_row
              if e in cited or ecr_class(states[e]) != "open"]
    details = [f"{e} ({states[e]}) holds {len(v)} row(s): {ids_str(v, 6)}" for e, v in sorted(waiting.items())]
    details += [f"{e} ({states[e]}, awaiting owner review) is cited by {len(v)} row(s): {ids_str(v, 6)}" for e, v in sorted(review.items())]
    details += stale + [f"{e} is open ({states[e]}) and no row cites it: add it to the rows it changes, or ecrs_no_row: {{{e}: reason}}" for e in uncited] + waived
    if not details:
        return Result("ecrs", PASS, "no row waits on an ECR, and every open ECR is cited")
    parts = [f"{len(waiting)} open ECR(s) hold {len({i for v in waiting.values() for i in v})} row(s) ({', '.join(sorted(waiting))})"] if waiting else []
    parts += [f"{len(review)} awaiting owner review ({', '.join(sorted(review))})"] if review else []
    parts += [f"{len(stale)} stale citation(s)"] if stale else []
    parts += [f"{len(uncited)} open ECR(s) no row cites ({', '.join(uncited)})"] if uncited else []
    parts += [f"{len(waived)} stale ecrs_no_row waiver(s)"] if waived else []
    return Result("ecrs", WARN, "; ".join(parts), details,
                  [f"ecrs:{e}" for e in {*waiting, *review}] + [f"ecrs:stale:{s.split()[0]}" for s in stale] + [f"ecrs:uncited:{e}" for e in uncited] + ["ecrs:waiver"] * len(waived))


def check_spec_drift(doc, spec):
    rows = [r for r in doc["requirements"] if r.get("kind") in ("decision", "owner")]
    drift = [f"{r['id']}: spec block {r['spec_block']} changed (row hash {r['spec_hash']}, spec now {block_hash(spec['blocks'][r['spec_block']])}); "
             f"re-read it, update the row, then refresh spec_hash" for r in rows
             if r.get("spec_block") in spec["blocks"] and r.get("spec_hash")
             and str(r["spec_hash"]) != block_hash(spec["blocks"][r["spec_block"]])]
    n = sum(1 for r in rows if r.get("spec_hash"))
    if drift:
        return Result("spec-drift", WARN, f"{len(drift)} row(s) summarise a spec block that changed since the row was reviewed "
                      f"(matrix updated {doc.get('updated')})", drift, [f"spec-drift:{d.split(':')[0]}" for d in drift])
    return Result("spec-drift", PASS, f"{n} decision/owner rows still match the spec blocks they were reviewed against")


def ref_label(r):
    ecrs = sorted(set(re.findall(r"ECR-\d+", str(r.get("known_fail_ref") or ""))))
    return ", ".join(ecrs) if ecrs else "no ECR"


def check_known_fail(doc):
    kf = [r for r in doc["requirements"] if r.get("known_fail")]
    if not kf:
        return Result("known-fail", PASS, "no row records a known failure")
    no_ecr = [r["id"] for r in kf if ref_label(r) == "no ECR"]
    details = [f"{r['id']} [{ref_label(r)}; tracked by: {' '.join(str(r.get('known_fail_ref') or 'nothing').split())}]: {' '.join(str(r['known_fail']).split())}" for r in kf]
    return Result("known-fail", WARN, f"{len(kf)} requirement(s) the design is known not to meet today: "
                  + ", ".join(f"{r['id']} [{ref_label(r)}]" for r in kf) + (f"; {len(no_ecr)} with no ECR, open one if the owner wants it tracked" if no_ecr else ""),
                  details, [f"known-fail:{r['id']}" for r in kf])


def counts(rows):
    by_stage = {s: Counter(stage_status(r, s) for r in rows if s in lst(r, "stage")) for s in STAGES}
    return by_stage, Counter(r.get("status") for r in rows)


def referenced_paths(rows):
    """Paths the rows cite; a check id (interfaces:pins) cites the script that defines it."""
    refs = set()
    for r in rows:
        for a in map(str, lst(r, "artefacts") + lst(r, "evidence")):
            if m := re.match(r"(interfaces|bom_check):", a):
                refs.add(rel(SCRIPTS[m[1]]))
            elif is_path_ref(a) and not is_commit(a):
                refs |= {rel(f) for f in resolve_path(a)[0]}
    return refs


def summary_data(rows):
    by_stage, overall = counts(rows)
    has_c = lambda r: "C" in lst(r, "stage")
    no_c = [r["id"] for r in rows if not has_c(r)]
    surrogate = [r["id"] for r in rows if has_c(r) and r.get("c_role") == "surrogate"]
    decides = [r["id"] for r in rows if has_c(r) and r.get("c_role") == "decides"]
    c_unstarted = [r["id"] for r in rows if has_c(r) and stage_status(r, "C") == "not-started"]
    refs = referenced_paths(rows)
    uncited = sorted(rel(p) for g in ANALYSIS_GLOBS for p in glob.glob(str(REPO / g))
                     if Path(p).name not in ("__init__.py", Path(__file__).name) and rel(p) not in refs)
    return {"by_stage": {s: dict(c) for s, c in by_stage.items()}, "overall": dict(overall), "no_stage_c": no_c,
            "stage_c_surrogate_only": surrogate, "stage_c_decides": decides, "stage_c_not_started": c_unstarted, "uncited_scripts": uncited,
            "stage_c_started": [r["id"] for r in rows if has_c(r) and stage_status(r, "C") in ("partial", "done")]}


def fmt_counts(c):
    return ", ".join(f"{k} {c.get(k, 0)}" for k in STATUSES)


def check_summary(doc):
    rows = doc["requirements"]
    d = summary_data(rows)
    started = set(d["stage_c_started"])
    ids = {r["id"] for r in rows}
    lost = [f"{i}: stage C was started at the baseline (stage_c_baseline), now it is "
            + ("not started" if i in ids else "gone with the row") for i in doc["stage_c_baseline"] if i not in started]
    lines = ["rows by stage and status (a row counts once per stage it lists):"]
    lines += [f"stage {s} ({STAGE_NAME[s]}): {sum(d['by_stage'][s].values())} rows: {fmt_counts(d['by_stage'][s])}" for s in STAGES]
    lines.append(f"rows by overall status: {fmt_counts(d['overall'])}")
    lines.append("no stage-C verification defined (rev 1 must reveal these, O18): " + (ids_str(d["no_stage_c"], 40) or "none"))
    lines.append(f"stage C is a surrogate only, the requirement itself is judged on rev 1 ({len(d['stage_c_surrogate_only'])}): "
                 + (ids_str(d["stage_c_surrogate_only"], 40) or "none"))
    lines.append(f"stage C can decide ({len(d['stage_c_decides'])}): " + (ids_str(d["stage_c_decides"], 40) or "none"))
    lines.append("stage C defined but not started: " + (ids_str(d["stage_c_not_started"], 40) or "none"))
    lines.append("analysis scripts no row cites: " + (ids_str(d["uncited_scripts"], 30) or "none"))
    msg = (f"{len(rows)} rows: {fmt_counts(d['overall'])}; stage C started on {len(started)}, "
           f"{len(d['no_stage_c'])} with no stage C, {len(d['stage_c_surrogate_only'])} settled only on rev 1 (stage C is a surrogate)")
    if lost:
        return Result("summary", WARN, f"{len(lost)} row(s) fell out of the stage-C baseline: {ids_str([x.split(':')[0] for x in lost], 6)}; " + msg,
                      lost + lines, [f"summary:{x.split(':')[0]}" for x in lost])
    return Result("summary", PASS, msg, lines)


# ------------------------------------------------------------------------------------------- generated markdown
def cell(text):
    return " ".join(str(text).split()).replace("|", "/")


def md_tables(doc):
    rows = doc["requirements"]
    d = summary_data(rows)
    out = [f"{MD_BEGIN} (generated by tools/checks/vcrm.py --update-md from docs/system/vcrm.yaml, updated {doc.get('updated')}; do not edit by hand) -->", "",
           "### Summary", "", "| Stage | Rows | done | partial | not-started |", "|---|---|---|---|---|"]
    for s in STAGES:
        c = d["by_stage"][s]
        out.append(f"| {s}: {STAGE_NAME[s]} | {sum(c.values())} | {c.get('done', 0)} | {c.get('partial', 0)} | {c.get('not-started', 0)} |")
    o = d["overall"]
    out += [f"| whole row | {len(rows)} | {o.get('done', 0)} | {o.get('partial', 0)} | {o.get('not-started', 0)} |", "",
            "**No stage-C verification defined (rev 1 must reveal these, O18):** " + (", ".join(f"`{i}`" for i in d["no_stage_c"]) or "none"),
            "", f"**Stage C is a surrogate only; the requirement itself is judged on rev 1 ({len(d['stage_c_surrogate_only'])}):** "
            + (", ".join(f"`{i}`" for i in d["stage_c_surrogate_only"]) or "none"),
            "", f"**Stage C can decide ({len(d['stage_c_decides'])}):** " + (", ".join(f"`{i}`" for i in d["stage_c_decides"]) or "none"),
            "", "**Stage C defined but not started:** " + (", ".join(f"`{i}`" for i in d["stage_c_not_started"]) or "none"), ""]
    for title, kind in (("Section 1 (owner-locked)", "mvp"), ("Decisions", "decision"), ("Owner decisions", "owner")):
        out += [f"### {title}", "", "| Row | Method | C | D | Known fail | ECRs | Next |", "|---|---|---|---|---|---|---|"]
        for r in rows:
            if r.get("kind") == kind:
                out.append("| " + " | ".join([f"`{r['id']}`", ", ".join(map(str, lst(r, "method"))),
                                              f"{stage_status(r, 'C')} ({r.get('c_role')})" if "C" in lst(r, "stage") else "-",
                                              stage_status(r, "D") if "D" in lst(r, "stage") else "-", "yes" if r.get("known_fail") else "",
                                              ", ".join(str(e).replace("ECR-", "") for e in lst(r, "ecrs")), cell(r.get("next", ""))]) + " |")
        out.append("")
    waived = doc.get("not_verifiable") or {}
    out += ["### Spec items with no row (recorded waivers, `not_verifiable`)", "", "| Item | Why nothing verifies it |", "|---|---|"]
    out += [f"| `{k}` | {cell(v)} |" for k, v in sorted(waived.items(), key=lambda kv: (kv[0][0], int(re.sub(r"\D", "", kv[0]) or 0), kv[0]))]
    out.append("")
    return "\n".join(out + [MD_END])


def check_md(doc):
    want = md_tables(doc)
    text = VCRM_MD.read_text() if VCRM_MD.exists() else ""
    m = re.search(re.escape(MD_BEGIN) + r".*?" + re.escape(MD_END), text, re.S)
    if not m:
        return Result("md", WARN, "docs/system/vcrm.md has no generated block (run: python3 tools/checks/vcrm.py --update-md)", keys=["md"])
    if m[0] != want:
        return Result("md", WARN, "the generated tables in docs/system/vcrm.md are out of date (run: python3 tools/checks/vcrm.py --update-md)", keys=["md"])
    return Result("md", PASS, "the generated tables in docs/system/vcrm.md are current")


def update_md(doc):
    text = VCRM_MD.read_text()
    new, n = re.subn(re.escape(MD_BEGIN) + r".*?" + re.escape(MD_END), lambda _: md_tables(doc), text, flags=re.S)
    if n != 1:
        raise LoadError("docs/system/vcrm.md needs exactly one generated block (begin and end markers)")
    VCRM_MD.write_text(new)


def update_pins(doc, refresh):
    """Add a pin for every evidence file that has none, drop pins nobody cites, refresh the named ones (or 'all')."""
    files = evidence_files(doc["requirements"])
    pins = {}
    for path in sorted(files):
        if (REPO / path).is_file():
            old = doc["evidence_pins"].get(path)
            pins[path] = file_pin(REPO / path) if old is None or path in refresh or "all" in refresh else str(old)
    block = "\n".join([f"{PINS_BEGIN} (rewritten by tools/checks/vcrm.py --update-pins; the hash of each evidence file when its rows were last reviewed)",
                       "evidence_pins:"] + [f"  {json.dumps(p)}: {json.dumps(h)}" for p, h in pins.items()] + [PINS_END])
    text = VCRM.read_text()
    new, n = re.subn(re.escape(PINS_BEGIN) + r".*?" + re.escape(PINS_END), lambda _: block, text, flags=re.S)
    if n != 1:
        raise LoadError(f"{VCRM.relative_to(REPO)} needs exactly one '{PINS_BEGIN}' ... '{PINS_END}' block")
    VCRM.write_text(new)
    return len(pins)


def lock_record():
    """{'commit', 'sha256'}: the oldest commit in the unbroken run (newest first) that holds the working tree's section 1."""
    sha = slice_sha(section1_slice(SPEC.read_text()))
    commit = None
    for h in git("log", "--format=%H", "--", "docs/spec.md")[1].split():
        if slice_sha(section1_slice(git("show", f"{h}:docs/spec.md")[1])) != sha:
            break
        commit = h
    return {"commit": commit, "sha256": sha}


# ------------------------------------------------------------------------------------------- driver
def guarded(cid, fn, *a):
    try:
        return fn(*a)
    except Exception as e:                                           # a crashing check is a FAIL with a reason, never a traceback
        return Result(cid, FAIL, f"check crashed: {type(e).__name__}: {one_line(e, 200)}")


def run(args):
    """(results, doc, spec); doc is None when the matrix could not be read at all."""
    try:
        doc, spec = load()
    except LoadError as e:
        return [Result("schema", FAIL, f"cannot load: {e}")], None, None
    if problems := shape_problems(doc):
        return [Result("schema", FAIL, f"the matrix cannot be read: {len(problems)} problem(s)", problems)], None, spec
    futures = start_live(args)                                        # the two scripts run while the static checks do
    results = [guarded("schema", check_schema, doc, spec)]
    results += [guarded(cid, fn, *a) for cid, fn, a in (
        ("coverage", check_coverage, (doc, spec)), ("lock", check_lock, (doc,)), ("verbatim", check_verbatim, (doc, spec)),
        ("artefacts", check_artefacts, (doc, spec)), ("evidence", check_evidence, (doc,)),
        ("tracked", check_tracked, (doc, tracked_files())), ("live", check_live, (doc, futures)),
        ("owners", check_owners, (doc,)), ("ecrs", check_ecrs, (doc,)), ("spec-drift", check_spec_drift, (doc, spec)),
        ("known-fail", check_known_fail, (doc,)))]
    if results[0].status == PASS:                                     # the summary and the tables index fields a bad row may lack
        results += [guarded("summary", check_summary, doc), guarded("md", check_md, doc)]
    return results, doc, spec


def apply_strict(results, ack):
    for r in results:
        if r.status == WARN and not (r.keys and all(k in ack for k in r.keys)):
            r.status, r.msg = FAIL, r.msg + " [--strict]"


def matrix_json(doc):
    return [{"id": r.get("id"), "kind": r.get("kind"), "method": lst(r, "method"), "stage": lst(r, "stage"), "status": r.get("status"),
             "status_by_stage": {s: stage_status(r, s) for s in lst(r, "stage")}, "owner_items": lst(r, "owner_items"),
             "ecrs": lst(r, "ecrs"), "known_fail": bool(r.get("known_fail"))} for r in doc["requirements"]]


def emit(results, verbose):
    for r in results:
        print(f"{r.status} {r.id} {r.msg}")
        shown = r.details if verbose else r.details[:10] if r.status == FAIL else []
        for line in shown:
            print(f"     - {line}")
        if r.status == FAIL and not verbose and len(r.details) > 10:
            print(f"     (+{len(r.details) - 10} more, rerun with -v)")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--json", action="store_true", help="machine-readable results")
    ap.add_argument("-v", "--verbose", action="store_true", help="print every detail line (a FAIL prints its first 10 anyway)")
    ap.add_argument("--strict", action="store_true", help="treat WARN as FAIL unless the matrix acknowledges it (release gate)")
    ap.add_argument("--no-live", action="store_true", help="do not run interfaces.py and bom_check.py (the live step is then a WARN)")
    ap.add_argument("--board", help="board file handed to interfaces.py and bom_check.py")
    ap.add_argument("--root", default=os.environ.get("VCRM_ROOT"), help="check another tree (default: the repo this script is in; or $VCRM_ROOT)")
    ap.add_argument("--hashes", action="store_true", help="print the current hash of each spec block a row cites")
    ap.add_argument("--table", action="store_true", help="print the generated markdown tables")
    ap.add_argument("--update-md", action="store_true", help="rewrite the generated block of docs/system/vcrm.md")
    ap.add_argument("--update-pins", action="store_true", help="add missing evidence pins, prune unused ones (rewrites the pins block of vcrm.yaml)")
    ap.add_argument("--refresh-pin", action="append", default=[], metavar="PATH", help="with --update-pins: re-hash this evidence file ('all' for every one)")
    ap.add_argument("--lock", action="store_true", help="print the section1_lock record for the working tree's section 1")
    ap.add_argument("--baseline", action="store_true", help="print the stage_c_baseline list for the current rows")
    args = ap.parse_args(argv)
    if args.root:
        set_root(args.root)
    if args.lock:
        print(json.dumps(lock_record(), indent=2))
        return 0
    if any((args.hashes, args.table, args.update_md, args.update_pins, args.baseline)):
        try:
            doc, spec = load()
            if problems := shape_problems(doc):
                raise LoadError("the matrix cannot be read: " + "; ".join(problems[:3]))
            if args.hashes:
                for b in sorted({r["spec_block"] for r in doc["requirements"] if r.get("spec_block") in spec["blocks"]}, key=lambda x: (x[0], int(re.sub(r"\D", "", x)), x)):
                    print(f"{b} {block_hash(spec['blocks'][b])}")
            elif args.baseline:
                print(json.dumps(summary_data(doc["requirements"])["stage_c_started"]))
            elif args.table:
                print(md_tables(doc))
            else:
                if (bad := check_schema(doc, spec)).status == FAIL:
                    raise LoadError(f"the matrix does not pass the schema check ({bad.msg}); fix it first: {bad.details[0]}")
                if args.update_md:
                    update_md(doc)
                    print(f"updated the generated block of {VCRM_MD.relative_to(REPO)}")
                else:
                    print(f"wrote {update_pins(doc, set(args.refresh_pin))} evidence pins into {VCRM.relative_to(REPO)}")
        except (LoadError, OSError, KeyError, TypeError, ValueError, AttributeError) as e:
            print(f"FAIL schema cannot do that: {one_line(e)}")
            return 1
        return 0
    results, doc, spec = run(args)
    if args.strict:
        apply_strict(results, set((doc or {}).get("acknowledged") or {}))
    if args.json:
        counts_ = {s: sum(r.status == s for r in results) for s in (PASS, WARN, FAIL)}
        ok = doc is not None and not any(r.id == "schema" and r.status == FAIL for r in results)
        print(json.dumps({"date": TODAY.isoformat(), "counts": counts_, "summary": summary_data(doc["requirements"]) if ok else None,
                          "checks": [r.as_dict() for r in results], "matrix": matrix_json(doc) if doc else []}, indent=2))
    else:
        emit(results, args.verbose)
    return 1 if any(r.status == FAIL for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
