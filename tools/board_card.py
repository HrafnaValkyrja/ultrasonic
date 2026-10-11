"""Refresh this session's Valhalla board cards (sessions/ultrasonic.json, status/ultrasonic.json): updated time, pid, heavy_now.
Run every heartbeat: python3 tools/board_card.py ["heavy_now text"] ["headline"]"""
import json, os, sys, datetime, pathlib
B = pathlib.Path.home() / ".claude-shared/board"
now = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
s = B / "sessions/ultrasonic.json"
d = json.loads(s.read_text())
d["updated"], d["pid"] = now, os.getppid()
d["heavy_now"] = sys.argv[1] if len(sys.argv) > 1 else "none"
d["session_fence"] = "18 GB session fence (tools/claude-session.sh); heavy jobs fenced 3-4G"
s.write_text(json.dumps(d, indent=1))
t = B / "status/ultrasonic.json"
e = json.loads(t.read_text())
e["updated"] = now
if len(sys.argv) > 2:
    e["headline"] = sys.argv[2]
t.write_text(json.dumps(e, indent=1))
print("card", now)
