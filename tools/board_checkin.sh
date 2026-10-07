#!/usr/bin/env bash
# Keep this session's entry on the shared Valhalla board current (~/.claude-shared/board/README.md).
#   tools/board_checkin.sh ["what heavy job is running now"]      run at every heartbeat (cron :17/:47)
# Also prints requests addressed to this project so the heartbeat can act on them.
set -euo pipefail
B="$HOME/.claude-shared/board"
mkdir -p "$B/sessions" "$B/requests" "$B/locks"
heavy="${1:-none}"
wd=$(pgrep -f '^bash tools/memwatch\.sh' >/dev/null && echo "tools/memwatch.sh alive: stops only this repo's python/java/kicad/blender jobs below 3.5 GB free" || echo "DOWN")
# record the session's claude process (walk up the process tree), not the throwaway shell that runs this script
CLAUDE_PID=$PPID; p=$$
while [ "$p" -gt 1 ]; do
  [ "$(cat /proc/$p/comm 2>/dev/null)" = claude ] && { CLAUDE_PID=$p; break; }
  p=$(awk '{print $4}' /proc/$p/stat 2>/dev/null || echo 1)
done
cat > "$B/sessions/ultrasonic.json" <<JSON
{
 "project": "Stereo Ultrasound / PCB + CAD (/home/hrafnavalkyrja/Desktop/ultrasonic)",
 "pid": $CLAUDE_PID,
 "updated": "$(date -Iseconds)",
 "mem_budget_gb": 8,
 "session_fence": "MemoryMax 8G (owner-set 2026-10-07, until reboot)",
 "heavy_now": "$heavy",
 "gpu": false,
 "watchdog": "$wd; every heavy job fenced with systemd-run --user --scope -p MemoryMax=3-4G -p MemorySwapMax=0; >8 GB or GPU jobs take locks/heavy.lock"
}
JSON
ls "$B/requests" 2>/dev/null | grep -i '^ultrasonic--' || true

# portal status card (valhalla-meta #1; Accretion bridges board/status/*.json to valkyrja.me)
python3 "$(dirname "$0")/status_publish.py" >/dev/null 2>&1 || true
