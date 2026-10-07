"""Publish this project's status card for the owner's private portal (valkyrja.me, bridged by the Accretion session).

    python3 tools/status_publish.py            # -> ~/.claude-shared/board/status/ultrasonic.json (schema 1)

Called by tools/board_checkin.sh at every heartbeat. Status-level only: no secrets, no personal names. Sources:
docs/brief/queue.yaml (needs_owner = open tier-A items), memory resume-now.md (headline/next), git log (recent),
tools/plm.py status (tracker health), the session's own health facts. Schema agreed with Accretion 2026-10-07
(valhalla-meta issue #1).
"""
from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
OUT = Path.home() / ".claude-shared/board/status/ultrasonic.json"


def sh(*cmd):
    return subprocess.run(cmd, capture_output=True, text=True, cwd=REPO).stdout.strip()


def main():
    q = yaml.safe_load((REPO / "docs/brief/queue.yaml").read_text())
    items = q.get("items", q) if isinstance(q, dict) else q
    items = items if isinstance(items, list) else []
    needs = [{"id": i["id"], "question": re.sub(r"\s+", " ", i.get("one_line", ""))[:220], "rec": str(i.get("rec", ""))[:140]}
             for i in items if isinstance(i, dict) and i.get("tier") == "A"
             and str(i.get("status", "")).split()[0] in ("open", "blocked")]
    recent = [{"date": l[:10], "what": l[11:][:160]} for l in sh("git", "log", "-8", "--date=short", "--format=%ad %s").splitlines()]
    oom = sh("bash", "-c", "journalctl -k --since -2h 2>/dev/null | grep -c 'Killed process' || true") or "0"
    plm = sh("python3", "tools/plm.py", "status").splitlines()
    status = {
        "schema": 1,
        "project": "Stereo Ultrasound",
        "updated": datetime.now().astimezone().isoformat(timespec="seconds"),
        "phase": "Phase 2: miniaturization (internals); owner review of the layout due ~mid-October",
        "headline": "One-face 30 x 12 mm board fully routed (DRC clean) + Phase-2 shell; size research done, battery decision waits on the runtime rule (D18)",
        "progress": [
            {"item": "Phase 1 logical simplification (Rev F/G)", "state": "done", "pct": 100},
            {"item": "Phase 2 board layout (draft_r2)", "state": "fully routed, DRC clean; owner review pending", "pct": 95},
            {"item": "Phase 2 shell (shell_r2)", "state": "first model; duct re-check after mic move", "pct": 60},
            {"item": "Stage-C sims on the Phase-2 board", "state": "noise model needs the +3V0 plane", "pct": 40},
            {"item": "Drastic size options K1/K2'", "state": "researched; owner call D18", "pct": 30},
            {"item": "Firmware", "state": "not started (DSP findings logged)", "pct": 0},
        ],
        "needs_owner": needs[:6],
        "health": {"session": "alive", "watchdog": "alive" if sh("pgrep", "-f", r"^bash tools/memwatch\.sh") else "down",
                   "last_heartbeat": datetime.now().astimezone().isoformat(timespec="seconds"), "oom_2h": int(oom),
                   "tracker": plm[-1] if plm else ""},
        "recent": recent,
        "links": [{"name": "GitHub branch", "url": "https://github.com/HrafnaValkyrja/ultrasonic/tree/claude/clever-mayer-s5rxuw"},
                  {"name": "Coordination issues", "url": "https://github.com/HrafnaValkyrja/valhalla-meta/issues"}],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".tmp")
    tmp.write_text(json.dumps(status, indent=1))
    tmp.replace(OUT)          # atomic: the bridge never reads a half-written file
    print(OUT)


if __name__ == "__main__":
    main()
