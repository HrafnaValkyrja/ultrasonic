# Environment for the ultrasonic tool harness. Source it; don't execute it.
#   source tools/env.sh
# tools/setup.sh installs everything this file points at. The SessionStart hook
# (.claude/hooks/session-start.sh) sources it for every Bash command in web sessions.
# Written to be safe under `set -euo pipefail` in the caller: no bare failing tests.

export ULTRA_TOOLS_HOME="${ULTRA_TOOLS_HOME:-/opt/ultrasonic-tools}"
export ULTRA_VENV="$ULTRA_TOOLS_HOME/venv"

# Temp files on DISK. On Ubuntu 26.04 /tmp is tmpfs (RAM). ngspice's -r raw output can reach
# ~10 GB, and tmpfs pages can't be reclaimed: that is RAM gone until the file is deleted
# (2026-09-30 incident). Python tempfile, ngspice and kicad-cli all honour TMPDIR.
export TMPDIR="${ULTRA_TMPDIR:-$HOME/.cache/ultrasonic-tmp}"
mkdir -p "$TMPDIR" 2>/dev/null || true

# FreeRouting jar (symlink to the pinned version) and the Java runtime it needs (>= 25).
export FREEROUTING_JAR="$ULTRA_TOOLS_HOME/freerouting/freerouting.jar"
# Cap FreeRouting's JVM heap. Unset, a JVM may claim up to 1/4 of RAM (~7.5 GB here), and six
# concurrent runs helped freeze the host on 2026-09-30. Verified sufficient on the smoke-test board;
# raise it (FREEROUTING_JAVA_OPTS=-Xmx2g) if a full pod-board route runs out of heap.
export FREEROUTING_JAVA_OPTS="${FREEROUTING_JAVA_OPTS:--Xmx1g}"
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
# SKiDL 2.3 looks for libraries under older KiCad names (it runs in KICAD9 mode, which reads
# KiCad 10 libraries fine); point those names at the KiCad 10 libraries.
for _v in KICAD KICAD6 KICAD7 KICAD8 KICAD9; do
  export "${_v}_SYMBOL_DIR=${KICAD10_SYMBOL_DIR}"
  export "${_v}_FOOTPRINT_DIR=${KICAD10_FOOTPRINT_DIR}"
done
unset _v

# `requests` (used by easyeda2kicad) ignores SSL_CERT_FILE and ships its own CA list.
# When a CA bundle is configured (e.g. an egress proxy), point requests at it too.
if [ -z "${REQUESTS_CA_BUNDLE:-}" ] && [ -n "${SSL_CERT_FILE:-}" ]; then
  export REQUESTS_CA_BUNDLE="$SSL_CERT_FILE"
fi

# Matplotlib: never try to open a window.
export MPLBACKEND="${MPLBACKEND:-Agg}"

# Mermaid CLI (flowcharts to PNG), driving the preinstalled Playwright Chromium headlessly.
export MMDC="$ULTRA_TOOLS_HOME/mermaid/node_modules/.bin/mmdc"
export MMDC_PUPPETEER_CONFIG="$ULTRA_TOOLS_HOME/mermaid/puppeteer.json"

# First usable headless Chromium, for mermaid-cli and the SVG renderer. Order: explicit override,
# the cloud image's preinstall, a Playwright/Puppeteer cache, then a browser on PATH. Echoes the
# path and returns 1 if there is none.
ultra_find_chrome() {
  local c
  if [ -n "${ULTRA_CHROME:-}" ] && [ -x "${ULTRA_CHROME}" ]; then printf '%s\n' "$ULTRA_CHROME"; return 0; fi
  for c in /opt/pw-browsers/chromium_headless_shell-*/chrome-linux/headless_shell \
           /opt/pw-browsers/chromium-*/chrome-linux/chrome \
           "$HOME"/.cache/ms-playwright/chromium_headless_shell-*/chrome-linux*/headless_shell \
           "$HOME"/.cache/ms-playwright/chromium-*/chrome-linux*/chrome \
           "$HOME"/.cache/puppeteer/chrome/*/chrome-linux*/chrome; do
    [ -x "$c" ] && { printf '%s\n' "$c"; return 0; }
  done
  for c in chromium chromium-browser google-chrome-stable google-chrome brave-browser; do
    command -v "$c" >/dev/null 2>&1 && { command -v "$c"; return 0; }
  done
  return 1
}

# Put the harness venv first, so `python3`/`pip` are the venv that can import pcbnew.
case ":$PATH:" in
  *":$ULTRA_VENV/bin:"*) ;;
  *) if [ -d "$ULTRA_VENV/bin" ]; then export PATH="$ULTRA_VENV/bin:$PATH"; fi ;;
esac
true
