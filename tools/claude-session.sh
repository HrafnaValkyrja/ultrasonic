#!/usr/bin/env bash
# Start (or reattach to) this project's Claude Code session: inside tmux, so closing the terminal
# can't kill it, and inside a memory fence, so nothing it runs can freeze the machine.
#   tools/claude-session.sh          # start, or reattach if it's already running
#
# Why (2026-09-30, docs/incidents/2026-09-30-oom.md): parallel audit agents ran seven ngspice and
# six FreeRouting processes at once, exhausted 30 GB RAM + 8 GB swap, and froze Valhalla for 7 h.
# With the fence, the kernel kills the offending process inside it instead of starving the desktop.
#
# The limits leave ~12 GB for the owner's desktop, games and other agents. Override per launch:
#   CLAUDE_MEM_MAX=22G tools/claude-session.sh
# The session runs with no DISPLAY/WAYLAND_DISPLAY, so nothing in it can open a window on the owner's screen (RULES.md
# "Never steal her screen", 2026-10-08); KiCad/Blender run CLI-only, Remote Control needs no display.
# A dedicated tmux socket (-L ultrasonic) matters: a session created on an already-running default
# tmux server would be spawned by that server, outside the fence.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

SOCK=ultrasonic
DETACHED=""; [ "${1:-}" = "--detached" ] && DETACHED="-d"     # keepalive restarts it without a terminal
if tmux -L "$SOCK" has-session -t ultrasonic 2>/dev/null; then
  [ -n "$DETACHED" ] && exit 0
  exec tmux -L "$SOCK" attach -t ultrasonic
fi
# optional first prompt (tools/keepalive.sh passes a wake prompt so the resumed session rebuilds its heartbeat)
# Resume THIS project's conversation by id (--continue picks whatever ran last in the folder) with Remote Control on,
# so the owner can steer from her phone (owner OK 2026-10-08).
SID="${CLAUDE_SESSION_ID:-759e00a7-254c-4cd3-926a-efbece430ab6}"
CMD="claude --resume $SID --remote-control 'Ultrasonic Local Valhalla'; exec bash"
if [ -n "${CLAUDE_WAKE_PROMPT:-}" ]; then
  printf '%s' "$CLAUDE_WAKE_PROMPT" > "$PWD/.claude-wake-prompt"
  CMD="claude --resume $SID --remote-control 'Ultrasonic Local Valhalla' \"\$(cat .claude-wake-prompt)\"; rm -f .claude-wake-prompt; exec bash"
fi

MAX="${CLAUDE_MEM_MAX:-8G}"     # owner-set session fence 8G (2026-10-07), permanent since 2026-10-08
HIGH="${CLAUDE_MEM_HIGH:-7G}"
exec env -u DISPLAY -u WAYLAND_DISPLAY systemd-run --user --scope --quiet \
  -p MemoryHigh="$HIGH" -p MemoryMax="$MAX" -p MemorySwapMax=2G \
  tmux -L "$SOCK" new-session $DETACHED -s ultrasonic -c "$PWD" "$CMD"
