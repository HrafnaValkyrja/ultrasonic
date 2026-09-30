#!/bin/bash
# SessionStart hook: make every Bash command in the session see the engineering harness
# (venv, KiCad paths, FreeRouting, mermaid) by sourcing tools/env.sh.
# - Local sessions (the project runs on the owner's machine, Valhalla, since 2026-09-30):
#   never installs anything (tools/setup.sh needs sudo); if the harness is missing it says how.
# - Cloud sessions (CLAUDE_CODE_REMOTE=true): installs the harness if missing first. tools/setup.sh
#   is idempotent and a ~1 s no-op once installed. A failed install never blocks the session.
set -uo pipefail

REPO="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
TOOLS="${ULTRA_TOOLS_HOME:-/opt/ultrasonic-tools}"

if [ "${CLAUDE_CODE_REMOTE:-}" = "true" ]; then
  if ! "$REPO/tools/setup.sh" --quiet; then
    echo "ultrasonic harness install failed; see $TOOLS/setup.log and re-run tools/setup.sh" >&2
    exit 0
  fi
elif [ ! -x "$TOOLS/venv/bin/python" ]; then
  echo "ultrasonic harness not installed on this machine: run tools/setup.sh (needs sudo), then start a new session" >&2
  exit 0
fi

if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  echo "source \"$REPO/tools/env.sh\"" >> "$CLAUDE_ENV_FILE"
fi
exit 0
