#!/usr/bin/env python3
"""Export finished agent results from a workflow journal so another session can reuse them.

    python3 .claude/workflows/export_done.py <transcript-dir>/journal.jsonl > done.json

Output: {"<agent label>": <result>, ...} for every agent that returned a result. Pass it as
args.done to .claude/workflows/adversarial-methodology-audit.js; those agents are then skipped.
"""
import ast
import json
import sys

labels, done = {}, {}
for line in open(sys.argv[1]):
    j = json.loads(line)
    if j.get("type") == "started":
        labels[j["key"]] = j.get("label")
    elif j.get("type") == "result" and j.get("key") in labels:
        r = j.get("result")
        if isinstance(r, str):
            for parse in (json.loads, ast.literal_eval):
                try:
                    r = parse(r)
                    break
                except Exception:
                    pass
        if r is not None:
            done[labels[j["key"]]] = r
json.dump(done, sys.stdout, indent=1)
print(f"{len(done)} finished results exported", file=sys.stderr)
