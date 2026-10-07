#!/usr/bin/env python3
"""Render docs/build/bringup.yaml (agent source of truth) into docs/build/bringup.md (owner-facing).

    python3 docs/build/make_bringup.py          # writes bringup.md
    python3 docs/build/make_bringup.py --check  # exit 1 if bringup.md is stale or a step lacks a field
"""
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
SRC, DST = HERE / "bringup.yaml", HERE / "bringup.md"
FIELDS = ("what", "tools", "expect", "pass", "on_fail")


def render(d):
    steps = [s for st in d["stages"] for s in st["steps"]]
    out = [
        "# Bring-up plan (ECR-0010)",
        "",
        f"Generated from `docs/build/bringup.yaml` by `docs/build/make_bringup.py` ({d['date']}). Edit the YAML, not this file.",
        "",
        "**How to use it.** Work top to bottom. Each step has what to do, the tools, the value our models predict "
        "(with tolerance), the pass line and what to do on a fail. Write every reading into the board's log "
        "(board 1 becomes the reference for boards 2-3). A red **gate** means: stop here until the step before it passed.",
        "",
        "![sequence](../diagrams/bringup-sequence.png)",
        "",
        f"{len(d['stages'])} stages, {len(steps)} steps. `[A]` = assumed tolerance, refine on board 1.",
        "",
        "## Gates (never skip)",
        "",
    ]
    out += [f"- **{k}**: {v}" for k, v in d["gates"].items()]
    out += ["", "## Tools", "", "- **Have:** " + "; ".join(d["tools"]["have"]),
            "- **Buy with the freeze order (O21):** " + "; ".join(d["tools"]["buy_at_freeze_O21"]),
            "- **Software:** " + "; ".join(d["tools"]["software"]), ""]
    for st in d["stages"]:
        out += [f"## Stage {st['id']}: {st['name']}", ""]
        for s in st["steps"]:
            out += [f"### {s['id']}. {s['what']}", "",
                    "| | |", "|---|---|",
                    f"| Tools | {', '.join(s['tools']) if s['tools'] else '-'} |",
                    f"| Expect | {s['expect']} |",
                    f"| Pass | {s['pass']} |",
                    f"| On fail | {s['on_fail']} |",
                    f"| Closes | {', '.join(s['closes']) if s['closes'] else '-'} |",
                    f"| Source | {s['src']} |", ""]
    cl = sorted({c for s in steps for c in s["closes"]})
    out += ["## Backlog items this plan closes", "", ", ".join(cl), ""]
    return "\n".join(out)


def main():
    d = yaml.safe_load(SRC.read_text())
    bad = [(s["id"], f) for st in d["stages"] for s in st["steps"] for f in FIELDS if not s.get(f) and f != "tools"]
    if bad:
        print("missing fields:", bad)
        sys.exit(1)
    md = render(d)
    if "--check" in sys.argv:
        ok = DST.exists() and DST.read_text() == md
        print("bringup.md", "current" if ok else "STALE")
        sys.exit(0 if ok else 1)
    DST.write_text(md)
    print(f"wrote {DST} ({sum(len(st['steps']) for st in d['stages'])} steps)")


if __name__ == "__main__":
    main()
