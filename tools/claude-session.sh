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
CMD="claude --continue; exec bash"
if [ -n "${CLAUDE_WAKE_PROMPT:-}" ]; then
  printf '%s' "$CLAUDE_WAKE_PROMPT" > "$PWD/.claude-wake-prompt"
  CMD='claude --continue "$(cat .claude-wake-prompt)"; rm -f .claude-wake-prompt; exec bash'
fi

MAX="${CLAUDE_MEM_MAX:-18G}"
HIGH="${CLAUDE_MEM_HIGH:-14G}"
exec systemd-run --user --scope --quiet \
  -p MemoryHigh="$HIGH" -p MemoryMax="$MAX" -p MemorySwapMax=2G \
  tmux -L "$SOCK" new-session $DETACHED -s ultrasonic -c "$PWD" "$CMD"
