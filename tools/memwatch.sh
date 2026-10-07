#!/usr/bin/env bash
# Memory watchdog for shared-machine safety (docs/incidents/2026-09-30-oom.md).
#   tools/memwatch.sh [WARN_MB] [KILL_MB] [LOG]     run it in the background; it exits on the first intervention
# Polls MemAvailable every 5 s. Below WARN_MB (default 7000): logs a warning with the top consumers.
# Below KILL_MB (default 3500): kills the single largest of THIS user's compute jobs (python3, blender, java,
# kicad-cli, pcbnew, ngspice, freerouting) and exits 3, so a background-task notification fires. It never touches
# claude, the desktop session, games or anything else. Fenced jobs (systemd-run scopes) normally die first.
# SHARED MACHINE (2026-10-07): other projects run as the same user (Accretion game-dev). A victim must have its working
# directory inside THIS repo (PROJECT_ROOT), so this watchdog never stops another project's processes
# (~/.claude-shared/board/README.md etiquette).
WARN="${1:-7000}"; KILL="${2:-3500}"; LOG="${3:-/tmp/memwatch.log}"
VICTIMS='^(python3|python|blender|java|kicad-cli|pcbnew|ngspice|freerouting)$'
PROJECT_ROOT="${PROJECT_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
ours() { local cwd; cwd=$(readlink "/proc/$1/cwd" 2>/dev/null) || return 1; [[ "$cwd" == "$PROJECT_ROOT"* ]]; }
echo "$(date -Is) memwatch start warn=${WARN}MB kill=${KILL}MB" >> "$LOG"
last_warn=0
while sleep 5; do
  avail=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)
  if [ "$avail" -lt "$KILL" ]; then
    pid=""; rss=0; comm=""
    while read -r p r c; do
      if ours "$p"; then pid=$p; rss=$((r / 1024)); comm=$c; break; fi
    done < <(ps -u "$USER" -o pid=,rss=,comm= --sort=-rss | awk -v re="$VICTIMS" '$3 ~ re {print $1, $2, $3}')
    echo "$(date -Is) KILL avail=${avail}MB -> pid=${pid:-none} ${comm:-} rss=${rss:-0}MB" >> "$LOG"
    if [ -z "$pid" ]; then                              # memory is low but none of it is ours: warn, don't kill, keep watching
      echo "$(date -Is) LOW avail=${avail}MB but no process of this project to stop; not touching other projects" >> "$LOG"
      sleep 25; continue
    fi
    kill "$pid"
    echo "memwatch: avail ${avail} MB < ${KILL}; killed ${comm:-nothing} (pid ${pid:-none}, ${rss:-0} MB). See $LOG"
    exit 3
  elif [ "$avail" -lt "$WARN" ] && [ $(( $(date +%s) - last_warn )) -gt 60 ]; then
    last_warn=$(date +%s)
    echo "$(date -Is) WARN avail=${avail}MB top: $(ps -u "$USER" -o rss=,comm= --sort=-rss | head -4 | awk '{printf "%dMB %s; ",$1/1024,$2}')" >> "$LOG"
  fi
done
