# Environment for the ultrasonic tool harness. Source it; don't execute it.
#   source tools/env.sh
# tools/setup.sh installs everything this file points at. The SessionStart hook
# (.claude/hooks/session-start.sh) sources it for every Bash command in web sessions.
# Written to be safe under `set -euo pipefail` in the caller: no bare failing tests.

export ULTRA_TOOLS_HOME="${ULTRA_TOOLS_HOME:-/opt/ultrasonic-tools}"
export ULTRA_VENV="$ULTRA_TOOLS_HOME/venv"

# FreeRouting jar (symlink to the pinned version) and the Java runtime it needs (>= 25).
export FREEROUTING_JAR="$ULTRA_TOOLS_HOME/freerouting/freerouting.jar"
if [ -z "${FREEROUTING_JAVA:-}" ]; then
  if [ -x /usr/lib/jvm/java-25-openjdk-amd64/bin/java ]; then
    export FREEROUTING_JAVA=/usr/lib/jvm/java-25-openjdk-amd64/bin/java
  else
    export FREEROUTING_JAVA=java
  fi
fi

# KiCad 10 library locations (KiCad sets these internally; SKiDL and our scripts read them).
export KICAD10_SYMBOL_DIR="${KICAD10_SYMBOL_DIR:-/usr/share/kicad/symbols}"
export KICAD10_FOOTPRINT_DIR="${KICAD10_FOOTPRINT_DIR:-/usr/share/kicad/footprints}"
export KICAD10_3DMODEL_DIR="${KICAD10_3DMODEL_DIR:-/usr/share/kicad/3dmodels}"

# `requests` (used by easyeda2kicad) ignores SSL_CERT_FILE and ships its own CA list.
# When a CA bundle is configured (e.g. an egress proxy), point requests at it too.
if [ -z "${REQUESTS_CA_BUNDLE:-}" ] && [ -n "${SSL_CERT_FILE:-}" ]; then
  export REQUESTS_CA_BUNDLE="$SSL_CERT_FILE"
fi

# Matplotlib: never try to open a window.
export MPLBACKEND="${MPLBACKEND:-Agg}"

# Put the harness venv first, so `python3`/`pip` are the 3.12 venv that can import pcbnew.
case ":$PATH:" in
  *":$ULTRA_VENV/bin:"*) ;;
  *) if [ -d "$ULTRA_VENV/bin" ]; then export PATH="$ULTRA_VENV/bin:$PATH"; fi ;;
esac
true
