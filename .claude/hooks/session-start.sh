#!/bin/bash
# SessionStart hook (Claude Code on the web): install the engineering harness if missing,
# then make every Bash command in the session see it (venv, KiCad paths, FreeRouting, mermaid).
# tools/setup.sh is idempotent and a ~1 s no-op once installed; a fresh container takes a
# few minutes. A failed install never blocks the session: it prints how to retry.
set -uo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

REPO="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"

if "$REPO/tools/setup.sh" --quiet; then
  if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
    echo "source \"$REPO/tools/env.sh\"" >> "$CLAUDE_ENV_FILE"
  fi
else
  echo "ultrasonic harness install failed; see /opt/ultrasonic-tools/setup.log and re-run tools/setup.sh" >&2
fi
exit 0
