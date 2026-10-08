#!/usr/bin/env bash
# Continuity keepalive (owner rule 2026-10-07: one session with this project's continuous context must always be working).
# Run by a systemd user timer every 5 min (tools/systemd/ultrasonic-keepalive.timer), outside Claude, so it survives the
# session dying. If no live `claude` process has its working directory in this repo, it restarts the project session
# in tmux, memory-fenced, with `claude --resume <session id>` (same conversation = continuous context) and Remote Control on and a wake prompt that
# rebuilds the session-only heartbeat and the watchdog. It never touches another project's processes.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG="$HOME/.claude-shared/board/keepalive-ultrasonic.log"
alive=""
for pid in $(pgrep -x claude || true); do
  cwd=$(readlink "/proc/$pid/cwd" 2>/dev/null || true)
  [[ "$cwd" == "$REPO"* ]] && alive="$pid" && break
done
if [ -n "$alive" ]; then exit 0; fi
if tmux -L ultrasonic has-session -t ultrasonic 2>/dev/null; then
  # no claude runs here: if nobody is attached, the tmux is only the leftover shell (claude-session.sh ends in `exec bash`)
  # after a crash or exit -> recycle it; if the owner is attached, leave it to her (owner OK 2026-10-08)
  if [ -n "$(tmux -L ultrasonic list-clients -t ultrasonic 2>/dev/null)" ]; then
    echo "$(date -Is) no live claude in $REPO, tmux has an attached client: leaving it for the owner" >> "$LOG"
    exit 0
  fi
  echo "$(date -Is) no live claude in $REPO, detached leftover tmux: recycling it" >> "$LOG"
  tmux -L ultrasonic kill-session -t ultrasonic 2>/dev/null || true
fi
echo "$(date -Is) no live claude in $REPO: restarting via tools/claude-session.sh (claude --resume <session id>, remote control, fenced, tmux)" >> "$LOG"
WAKE="KEEPALIVE RESTART: this session was restarted automatically by tools/keepalive.sh because no ultrasonic Claude was running. Read memory resume-now.md and autonomous-standing-orders.md, run CronList first and create only the crons that are missing (the 2 h heartbeat at :17 with the standing-orders checklist), relaunch tools/memwatch.sh in the background, run tools/board_checkin.sh, then continue the plan. Log the restart in the progress log."
cd "$REPO"
CLAUDE_WAKE_PROMPT="$WAKE" setsid -f tools/claude-session.sh --detached >/dev/null 2>&1 < /dev/null
