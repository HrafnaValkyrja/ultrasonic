#!/usr/bin/env python3
"""Relation tracking for the pod design: a small, git-native PLM (Teamcenter-style ideas, Doorstop-style stamps).

    source tools/env.sh
    python3 tools/plm.py status                 # suspect relations, stale docs, broken watches, check-outs, open ECRs
    python3 tools/plm.py impact <target>        # where-used: item id, file path, net:X, ref:U3, block:BRIDGE, sym:...
    python3 tools/plm.py review <id>... --by NAME --note "what was checked"   # re-baseline after checking both sides
    python3 tools/plm.py checkout <item> --by TEAM --intent "..."              # claim an item; flags related claims
    python3 tools/plm.py checkin <item> --by TEAM
    python3 tools/plm.py ecr new --title "..." --items A,B --by NAME [--body FILE]   # change request + impact
    python3 tools/plm.py ecr list
    python3 tools/plm.py graph                  # docs/diagrams/plm-relations.png (suspect = red, stale = amber)

Model (docs/system/plm/items.yaml, hand-kept):
  item      a subsystem / region / integration doc. `owns` = the watches that define its content; `doc` = its
            big-picture doc. If what it owns changes after its last review, the item is STALE (doc out of date).
  relation  an interface between two items, with `watch` expressions on the things that carry the interface.
            If any watched thing changes after the relation's last review, the relation is SUSPECT: both sides'
            owners must check it, fix what broke, update the docs, then `review` it. A watch that no longer
            resolves (renamed symbol, removed part or net) is BROKEN: the relation itself must be re-modelled.
  checkout  a team (agent or person) claims an item before editing it. Claiming an item that is related to an
            item another team holds raises a CONFLICT flag naming the relation, so the two coordinate.
  ECR       engineering change request: proposed change + computed impact (relations, items, docs, owners);
            the owner approves; commits that implement it cite its id; closing it requires the suspect
            relations it caused to be reviewed.
Watches:
  file:PATH                 whole file content
  glob:PATTERN              all matching files
  sym:PATH::NAME            a top-level Python assignment / def / class (NAME as written, e.g. PCB, P.W, tub)
  sym:PATH::NAME[KEY]       one entry of a top-level dict literal (e.g. PLACE[U3])
  grep:PATH::REGEX          the lines matching REGEX
  yaml:PATH::KEY            one top-level key of a YAML file (e.g. yaml:hw/pod/draft_r2/placement.yaml::U2), 2026-10-07
  net:NAME | ref:REF | block:NAME   from the SKiDL schematic (hw/pod/gen.py via hw/pod/system_map.py), built for the
                            current design's package set (hw/current.yaml `packages`, tools/current.py apply_env)
impact <target> also matches a directory: every watch under it (impact hw/pod/draft_r2).
Baselines live in docs/system/plm/baseline.json (commit it). The SKiDL build costs a few seconds.
"""
from __future__ import annotations

import argparse
import ast
import datetime as dt
import fnmatch
import glob as globmod
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
PLM = REPO / "docs/system/plm"
ITEMS = PLM / "items.yaml"
BASE = PLM / "baseline.json"
CHECKOUTS = PLM / "checkouts.json"
LOG = PLM / "log.md"
ECR_DIR = PLM / "ecr"
TODAY = dt.date.today().isoformat()


class Broken(Exception):
    pass


# ----------------------------------------------------------------------------------------- watches
_circuit = None


def circuit():
    global _circuit
    if _circuit is None:
        sys.path.insert(0, str(REPO / "tools"))
        from current import apply_env                       # noqa: E402  (hw/current.yaml: POD_PACKAGES of the current design)
        apply_env()
        sys.path.insert(0, str(REPO / "hw/pod"))
        import system_map                                   # noqa: E402
        circ = system_map.build()
        nets, parts = {}, {}
        for p in circ.parts:
            pins = []
            for pin in p.pins:
                for n in pin.nets:
                    if n.name and not n.name.startswith("__NOCONNECT"):
                        nets.setdefault(n.name, []).append(f"{p.ref}.{pin.num}({pin.name})")
                        pins.append(f"{pin.num}({pin.name})={n.name}")
            parts[p.ref] = f"value={p.value} fp={p.footprint} lcsc={p.fields.get('LCSC', '')} dnp={p.fields.get('DNP_BOM', '')} " + " ".join(sorted(pins))
        _circuit = (nets, parts, system_map.BLOCKS)
    return _circuit


def _py_symbol(path, name):
    tree = ast.parse((REPO / path).read_text())
    m = re.fullmatch(r"(.+?)\[(.+)\]", name)
    base, key = (m.group(1), m.group(2)) if m else (name, None)
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name == base and key is None:
            return ast.unparse(node)
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            names = []
            for t in targets:
                names += [ast.unparse(e) for e in t.elts] if isinstance(t, ast.Tuple) else [ast.unparse(t)]
            if base not in names:
                continue
            if key is None:
                return ast.unparse(node)
            if isinstance(node.value, ast.Dict):
                for k, v in zip(node.value.keys, node.value.values):
                    if isinstance(k, ast.Constant) and str(k.value) == key:
                        return ast.unparse(v)
            raise Broken(f"key {key} not in {base}")
    raise Broken(f"symbol {name} not found")


def watch_text(w):
    kind, _, arg = w.partition(":")
    try:
        if kind == "file":
            return (REPO / arg).read_bytes().decode(errors="replace")
        if kind == "glob":
            files = sorted(globmod.glob(str(REPO / arg), recursive=True))
            if not files:
                raise Broken("no files match")
            return "".join(f"== {Path(f).relative_to(REPO)}\n" + Path(f).read_bytes().decode(errors="replace") for f in files)
        if kind == "sym":
            path, _, name = arg.partition("::")
            return _py_symbol(path, name)
        if kind == "grep":
            path, _, rx = arg.partition("::")
            lines = [ln for ln in (REPO / path).read_text().splitlines() if re.search(rx, ln)]
            if not lines:
                raise Broken("no matching lines")
            return "\n".join(lines)
        if kind == "yaml":
            path, _, key = arg.partition("::")
            data = yaml.safe_load((REPO / path).read_text())
            if not isinstance(data, dict) or key not in data:
                raise Broken(f"key {key} not in {path}")
            return json.dumps(data[key], sort_keys=True)
        if kind in ("net", "ref", "block"):
            nets, parts, blocks = circuit()
            if kind == "net":
                if arg not in nets:
                    raise Broken("net not in schematic")
                return " ".join(sorted(nets[arg]))
            if kind == "ref":
                if arg not in parts:
                    raise Broken("part not in schematic")
                return parts[arg]
            if arg not in blocks:
                raise Broken("block not in system_map.BLOCKS")
            refs = blocks[arg].split()
            return "\n".join(f"{r}: {parts.get(r, 'MISSING')}" for r in refs)
    except FileNotFoundError:
        raise Broken("file missing")
    except SyntaxError as e:
        raise Broken(f"python syntax error: {e}")
    raise Broken(f"unknown watch kind {kind!r}")


def stamp(watches):
    out = {}
    for w in watches:
        try:
            out[w] = hashlib.sha256(watch_text(w).encode()).hexdigest()[:16]
        except Broken as e:
            out[w] = f"BROKEN: {e}"
    return out


# ----------------------------------------------------------------------------------------- model
def load():
    model = yaml.safe_load(ITEMS.read_text())
    base = json.loads(BASE.read_text()) if BASE.exists() else {"items": {}, "relations": {}}
    return model, base


def save_base(base):
    BASE.write_text(json.dumps(base, indent=1, sort_keys=True) + "\n")


def log(line):
    if not LOG.exists():
        LOG.write_text("# PLM review / check-out log\n\n")
    with LOG.open("a") as f:
        f.write(f"- {dt.datetime.now().strftime('%Y-%m-%d %H:%M')} {line}\n")


def evaluate(model, base):
    """-> list of findings (kind, id, detail)."""
    found = []
    for iid, it in model["items"].items():
        if it.get("doc") and not (REPO / it["doc"]).exists():
            found.append(("MISSING-DOC", iid, it["doc"]))
        cur = stamp(it.get("owns", []))
        for w, h in cur.items():
            if h.startswith("BROKEN"):
                found.append(("BROKEN", iid, f"{w}: {h}"))
        old = base["items"].get(iid, {}).get("stamp")
        if old is None:
            found.append(("UNREVIEWED", iid, "no baseline yet"))
        else:
            changed = [w for w in cur if cur[w] != old.get(w)]
            if changed:
                found.append(("STALE", iid, f"doc {it.get('doc')} predates changes in: {', '.join(changed)}"))
    for rel in model["relations"]:
        cur = stamp(rel["watch"])
        for w, h in cur.items():
            if h.startswith("BROKEN"):
                found.append(("BROKEN", rel["id"], f"{w}: {h}"))
        old = base["relations"].get(rel["id"], {}).get("stamp")
        if old is None:
            found.append(("UNREVIEWED", rel["id"], f"{rel['a']} <-> {rel['b']}"))
        else:
            changed = [w for w in cur if cur[w] != old.get(w)]
            if changed:
                found.append(("SUSPECT", rel["id"], f"{rel['a']} <-> {rel['b']} ({rel['what']}); changed: {', '.join(changed)}"))
    return found


def related(model, iid):
    return [r for r in model["relations"] if iid in (r["a"], r["b"])]


# ----------------------------------------------------------------------------------------- commands
def cmd_status(a):
    model, base = load()
    found = evaluate(model, base)
    order = ["BROKEN", "SUSPECT", "STALE", "MISSING-DOC", "UNREVIEWED"]
    for kind in order:
        rows = [f for f in found if f[0] == kind]
        if rows:
            print(f"\n{kind} ({len(rows)})")
            for _, i, d in rows:
                print(f"  {i}: {d}")
    co = json.loads(CHECKOUTS.read_text()) if CHECKOUTS.exists() else {}
    if co:
        print("\nCHECKED OUT")
        for i, c in co.items():
            print(f"  {i}: {c['by']} since {c['since']} ({c['intent']})")
    open_ecrs = [p for p in sorted(ECR_DIR.glob("ECR-*.md")) if re.search(r"^Status: (proposed|approved)", p.read_text(), re.M)]
    if open_ecrs:
        print("\nOPEN ECRs")
        for p in open_ecrs:
            t = p.read_text()
            print(f"  {p.stem}: {re.search(r'^# (.*)', t, re.M).group(1)} [{re.search(r'^Status: (.*)', t, re.M).group(1)}]")
    bad = [f for f in found if f[0] in ("BROKEN", "SUSPECT", "STALE", "MISSING-DOC")]
    print(f"\n{len(model['items'])} items, {len(model['relations'])} relations: "
          f"{sum(f[0] == 'SUSPECT' for f in found)} suspect, {sum(f[0] == 'STALE' for f in found)} stale, "
          f"{sum(f[0] == 'BROKEN' for f in found)} broken, {sum(f[0] == 'UNREVIEWED' for f in found)} unreviewed")
    return 1 if bad else 0


def _matches(watch, target):
    if watch == target:
        return True
    kind, _, arg = watch.partition(":")
    path = arg.partition("::")[0]
    if kind in ("file", "sym", "grep", "yaml", "glob") and target in (path, f"file:{path}"):
        return True
    if kind in ("file", "sym", "grep", "yaml", "glob") and path.startswith(target.rstrip("/") + "/"):   # a directory target
        return True
    if kind == "glob" and fnmatch.fnmatch(target, arg):
        return True
    if target.startswith("ref:") and kind == "block":
        _, _, blocks = circuit()
        return target[4:] in blocks.get(arg, "").split()
    return False


def cmd_impact(a):
    model, _ = load()
    t = a.target
    direct_items = {iid for iid, it in model["items"].items() if t == iid or any(_matches(w, t) for w in it.get("owns", []))}
    direct_rels = [r for r in model["relations"] if t in (r["a"], r["b"]) or any(_matches(w, t) for w in r["watch"])]
    print(f"IMPACT of {t}")
    print("\nItems that own it (their docs must be updated):")
    for iid in sorted(direct_items):
        print(f"  {iid}: {model['items'][iid].get('doc')}")
    print("\nRelations that watch it (both sides must re-check):")
    for r in direct_rels:
        print(f"  {r['id']}: {r['a']} <-> {r['b']}: {r['what']}")
    second = set()
    for iid in direct_items:
        for r in related(model, iid):
            second |= {r["a"], r["b"]}
    second -= direct_items
    for r in direct_rels:
        second |= {r["a"], r["b"]}
    print("\nItems one relation away (read their docs before changing):")
    for iid in sorted(second - direct_items):
        print(f"  {iid}: {model['items'][iid].get('doc')}")
    return 0


def cmd_review(a):
    model, base = load()
    rels = {r["id"]: r for r in model["relations"]}
    ids = list(model["items"]) + list(rels) if a.ids == ["--all"] or "ALL" in a.ids else a.ids
    for i in ids:
        if i in model["items"]:
            base["items"][i] = {"stamp": stamp(model["items"][i].get("owns", [])), "by": a.by, "date": TODAY, "note": a.note}
        elif i in rels:
            base["relations"][i] = {"stamp": stamp(rels[i]["watch"]), "by": a.by, "date": TODAY, "note": a.note}
        else:
            print(f"unknown id {i}")
            return 2
        broken = [w for w, h in (base["items"].get(i) or base["relations"].get(i))["stamp"].items() if h.startswith("BROKEN")]
        if broken:
            print(f"WARNING {i}: reviewed with broken watches {broken}: re-model it in items.yaml")
        log(f"review {i} by {a.by}: {a.note}")
    save_base(base)
    print(f"reviewed {len(ids)}")
    return 0


def cmd_checkout(a):
    model, _ = load()
    if a.item not in model["items"]:
        print(f"unknown item {a.item}")
        return 2
    co = json.loads(CHECKOUTS.read_text()) if CHECKOUTS.exists() else {}
    if a.item in co and co[a.item]["by"] != a.by:
        print(f"REFUSED: {a.item} is checked out by {co[a.item]['by']} ({co[a.item]['intent']})")
        return 1
    conflicts = []
    for r in related(model, a.item):
        other = r["b"] if r["a"] == a.item else r["a"]
        if other in co and co[other]["by"] != a.by:
            conflicts.append(f"{other} held by {co[other]['by']} ({co[other]['intent']}) via {r['id']}: {r['what']}")
    co[a.item] = {"by": a.by, "since": TODAY, "intent": a.intent}
    CHECKOUTS.write_text(json.dumps(co, indent=1) + "\n")
    log(f"checkout {a.item} by {a.by}: {a.intent}")
    print(f"checked out {a.item} to {a.by}")
    for c in conflicts:
        print(f"CONFLICT FLAG: {c}")
    return 3 if conflicts else 0


def cmd_checkin(a):
    co = json.loads(CHECKOUTS.read_text()) if CHECKOUTS.exists() else {}
    if co.get(a.item, {}).get("by") != a.by:
        print(f"{a.item} is not checked out by {a.by}")
        return 1
    del co[a.item]
    CHECKOUTS.write_text(json.dumps(co, indent=1) + "\n")
    model, base = load()
    pending = [f for f in evaluate(model, base) if f[0] in ("SUSPECT", "STALE", "BROKEN") and
               (f[1] == a.item or any(f[1] == r["id"] for r in related(model, a.item)))]
    log(f"checkin {a.item} by {a.by}")
    print(f"checked in {a.item}")
    for f in pending:
        print(f"STILL OPEN: {f[0]} {f[1]}: {f[2]}")
    return 1 if pending else 0


def cmd_ecr(a):
    ECR_DIR.mkdir(parents=True, exist_ok=True)
    if a.action == "list":
        for p in sorted(ECR_DIR.glob("ECR-*.md")):
            t = p.read_text()
            print(f"{p.stem}: {re.search(r'^# (.*)', t, re.M).group(1)} [{re.search(r'^Status: (.*)', t, re.M).group(1)}]")
        return 0
    model, _ = load()
    items = [i.strip() for i in a.items.split(",") if i.strip()]
    for i in items:
        if i not in model["items"]:
            print(f"unknown item {i}")
            return 2
    n = 1 + max([int(p.stem.split("-")[1]) for p in ECR_DIR.glob("ECR-*.md")] or [0])
    rels = [r for r in model["relations"] if r["a"] in items or r["b"] in items]
    near = sorted({x for r in rels for x in (r["a"], r["b"])} - set(items))
    body = Path(a.body).read_text() if a.body else "_(describe the change: what, why, options considered)_\n"
    L = [f"# {a.title}", "", f"Status: proposed", f"Raised: {TODAY} by {a.by}", f"Items changed: {', '.join(items)}", "",
         "## Change", "", body, "",
         "## Impact (computed by tools/plm.py from items.yaml)", "",
         "Relations to re-check (each side's owner signs off by `plm.py review <id>`):", ""]
    L += [f"- [ ] {r['id']}: {r['a']} <-> {r['b']}: {r['what']}" for r in rels]
    L += ["", "Docs to update in the implementing commit:", ""]
    L += [f"- [ ] {model['items'][i]['doc']}" for i in items + near if model["items"][i].get("doc")]
    L += ["", "## Cross-check (docs/system/integration-map.md §10)", "",
          "functions / nets / pins / rails / off-board / mechanical / firmware / depends-on: _(fill in)_", "",
          "## Decision", "", "_(owner: approve / reject / revise, date)_", "",
          "## Implementation", "", "_(commits citing this ECR id)_", ""]
    p = ECR_DIR / f"ECR-{n:04d}.md"
    p.write_text("\n".join(L))
    log(f"ECR-{n:04d} raised by {a.by}: {a.title}")
    print(p.relative_to(REPO))
    return 0


def cmd_graph(a):
    model, base = load()
    found = evaluate(model, base)
    state = {}
    for kind, i, _ in found:
        state.setdefault(i, kind)
    colours = {"SUSPECT": "#d1242f", "BROKEN": "#8250df", "STALE": "#bf8700", "UNREVIEWED": "#8c959f", "MISSING-DOC": "#bf8700"}
    kinds = {"whole": "#ddf4ff", "integration": "#ddf4ff", "physical": "#fff8c5", "subsystem": "#dafbe1", "region": "#fbefff", "requirement": "#ffebe9", "cost": "#f6f8fa"}
    L = ['graph plm {', ' graph [bgcolor="#0d1117", fontname="Helvetica", fontcolor="#e6edf3", label="Design relations (tools/plm.py): red = suspect, amber = stale, grey = unreviewed, purple = broken", labelloc=t, fontsize=16, overlap=false, splines=true, K=1.4];',
         ' node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=11, color="#30363d", fontcolor="#0d1117"];',
         ' edge [fontname="Helvetica", fontsize=8, fontcolor="#8b949e", color="#3fb950", penwidth=1.6];']
    for iid, it in model["items"].items():
        fill = kinds.get(it.get("kind"), "#f6f8fa")
        border = colours.get(state.get(iid), "#30363d")
        L.append(f' "{iid}" [label="{iid}\\n{it.get("title", "")[:34]}", fillcolor="{fill}", color="{border}", penwidth={3 if iid in state else 1}];')
    for r in model["relations"]:
        c = colours.get(state.get(r["id"]), "#3fb950")
        L.append(f' "{r["a"]}" -- "{r["b"]}" [color="{c}", label="{r["id"].replace("R-", "")}"];')
    L.append("}")
    dot = REPO / "docs/diagrams/plm-relations.dot"
    dot.write_text("\n".join(L))
    png = dot.with_suffix(".png")
    subprocess.run(["neato", "-Tpng", "-Gdpi=130", str(dot), "-o", str(png)], check=True)
    print(png.relative_to(REPO))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("status")
    p = sp.add_parser("impact"); p.add_argument("target")
    p = sp.add_parser("review"); p.add_argument("ids", nargs="+"); p.add_argument("--by", required=True); p.add_argument("--note", required=True)
    p = sp.add_parser("checkout"); p.add_argument("item"); p.add_argument("--by", required=True); p.add_argument("--intent", required=True)
    p = sp.add_parser("checkin"); p.add_argument("item"); p.add_argument("--by", required=True)
    p = sp.add_parser("ecr"); p.add_argument("action", choices=["new", "list"]); p.add_argument("--title"); p.add_argument("--items", default="")
    p.add_argument("--by", default="claude"); p.add_argument("--body")
    sp.add_parser("graph")
    a = ap.parse_args()
    return {"status": cmd_status, "impact": cmd_impact, "review": cmd_review, "checkout": cmd_checkout,
            "checkin": cmd_checkin, "ecr": cmd_ecr, "graph": cmd_graph}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
