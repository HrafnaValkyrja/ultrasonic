#!/usr/bin/env python3
"""Which files are the current pod design: the ONE loader for hw/current.yaml (single source of truth, 2026-10-07).

    from current import current            # sys.path: <repo>/tools
    d = current()                          # d.board, d.netlist, d.bom, d.shell, ... are absolute Paths; d.id == "phase2"
    d = current("revg")                    # the reference design (Rev G schematic / Rev F board)
    python3 tools/current.py               # print the resolved pointer (respects ULTRASONIC_DESIGN)
    python3 tools/current.py board         # print one path (for shell scripts)

Selection: argument > env ULTRASONIC_DESIGN > the top block of hw/current.yaml.
Accepted names: the top block's id (e.g. phase2), "current"; the reference block's id (revg), "reference", "revf".
Every tool that needs a default design file must take it from here, never from a hard-coded path.
Pure stdlib + PyYAML; no CAD or KiCad import.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace

REPO = Path(__file__).resolve().parents[1]
POINTER = REPO / "hw/current.yaml"
ENV = "ULTRASONIC_DESIGN"
PATH_KEYS = ("board", "board_placed", "placement", "netlist", "bom", "shell", "shell_dims", "shell_out")
OPT_PATH_KEYS = ("board_p", "netlist_p", "bom_p")      # second board of a two-board design (K4: P); None when absent
META_KEYS = ("id", "name", "ecr", "owner_decision", "packages", "generate", "acoustic_scenario")


def _load(path=POINTER):
    import yaml
    data = yaml.safe_load(Path(path).read_text())
    if not isinstance(data, dict) or "reference" not in data:
        raise ValueError(f"{path}: needs the current design's keys and a `reference` block")
    variants = {k: v for k, v in data.items() if k != "reference" and isinstance(v, dict) and v.get("id")}
    top = {k: v for k, v in data.items() if k != "reference" and k not in variants}
    return top, data["reference"], variants


def current(design=None, root=None):
    """The selected design as a namespace: path keys -> absolute Path (under `root`, default the repo), meta keys as read.

    Also: .rel (repo-relative strings of the path keys), .is_reference (bool), .root.
    Raises ValueError for an unknown design name or a missing key (a broken pointer must fail loudly, never fall back)."""
    root = Path(root or REPO).resolve()
    top, ref, variants = _load(root / "hw/current.yaml" if (root / "hw/current.yaml").exists() else POINTER)
    want = (design or os.environ.get(ENV) or "").strip().lower()
    if want in ("", "current", str(top.get("id", "")).lower()):
        block, is_ref = top, False
    elif want in ("reference", "revf", str(ref.get("id", "")).lower()):
        block, is_ref = ref, True
    elif want in {str(v["id"]).lower() for v in variants.values()}:      # NON-DEFAULT variants (e.g. k1, 2026-10-07)
        block, is_ref = next(v for v in variants.values() if str(v["id"]).lower() == want), False
    else:
        raise ValueError(f"{ENV}={want!r}: unknown design (use {top.get('id')!r}/current, {ref.get('id')!r}/reference"
                         f" or a variant: {', '.join(str(v['id']) for v in variants.values())})")
    missing = [k for k in PATH_KEYS if not block.get(k)]
    if missing:
        raise ValueError(f"hw/current.yaml ({block.get('id')}): missing {', '.join(missing)}")
    ns = SimpleNamespace(root=root, is_reference=is_ref, rel={k: block[k] for k in PATH_KEYS})
    for k in PATH_KEYS:
        setattr(ns, k, root / block[k])
    for k in OPT_PATH_KEYS:
        setattr(ns, k, root / block[k] if block.get(k) else None)
    for k in META_KEYS:
        setattr(ns, k, block.get(k))
    return ns


def apply_env(d=None):
    """Make hw/pod/gen.py (imported in-process) build the selected design's package set: sets POD_PACKAGES unless set."""
    d = d or current()
    if d.packages:
        os.environ.setdefault("POD_PACKAGES", str(d.packages))
    return d


def describe(d=None):
    d = d or current()
    return f"design {d.id}{' (reference)' if d.is_reference else ''}: board {d.rel['board']}, netlist {d.rel['netlist']}, bom {d.rel['bom']}, shell {d.rel['shell']}"


if __name__ == "__main__":
    d = current()
    if len(sys.argv) > 1:
        key = sys.argv[1]
        v = getattr(d, key, None)
        if v is None:
            sys.exit(f"unknown key {key!r}; keys: {', '.join(PATH_KEYS + META_KEYS)}")
        print(v)
    else:
        print(describe(d))
        for k in PATH_KEYS:
            p = getattr(d, k)
            print(f"  {k:13s} {d.rel[k]}{'' if p.exists() else '   (MISSING)'}")
        for k in META_KEYS:
            print(f"  {k:13s} {getattr(d, k)}")
