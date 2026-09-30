#!/usr/bin/env bash
# tools/setup.sh: idempotent installer for the ultrasonic engineering-simulation harness.
#
#   tools/setup.sh            install anything missing, verify, write a stamp (then a fast no-op)
#   tools/setup.sh --smoke    ...and run every smoke test (tools/smoke/run_all.py)
#   tools/setup.sh --check    verify only, install nothing; exit 1 if something is missing
#   tools/setup.sh --force    ignore the stamp and re-run every install step
#   tools/setup.sh --with-3d  also install KiCad's 3D model library (3.2 GB installed, 267 MB download)
#   tools/setup.sh --quiet    one-line output (the SessionStart hook uses this)
#
# Installs (details, versions, sizes: tools/README.md):
#   apt   ngspice; gcc-arm-none-eabi + newlib; KiCad 10.0 (official KiCad PPA, key pinned in
#         tools/keys/) + symbol and footprint libraries; OpenJDK 25 JRE (FreeRouting >= 2.2 needs
#         it; the system default `java` is left alone); librsvg2-bin; python3.12-venv; cmake; ninja
#   venv  $ULTRA_VENV: Python 3.12 with --system-site-packages, so KiCad's pcbnew module imports;
#         packages from tools/requirements.txt pinned by tools/constraints.txt
#   jar   FreeRouting, pinned version and SHA-256, in $ULTRA_TOOLS_HOME/freerouting
#   npm   @mermaid-js/mermaid-cli (pinned) in $ULTRA_TOOLS_HOME/mermaid, driving the preinstalled
#         Playwright Chromium (/opt/pw-browsers) instead of downloading its own
set -Eeuo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=tools/env.sh
. "$REPO/tools/env.sh"

KICAD_SERIES=10.0
FR_VERSION=2.4.1
FR_SHA256=251101c3eeac22d7e7dfcf6796603279e5d1000283eb82d8f093780f7afc6aa9
FR_URL="https://github.com/freerouting/freerouting/releases/download/v${FR_VERSION}/freerouting-${FR_VERSION}.jar"
# The venv must run the interpreter KiCad's pcbnew bindings are built against: the distro's
# python3 (Ubuntu 24.04 -> 3.12, 26.04 -> 3.14). Detected, not pinned; see sys_python().
NEWLIB_HARDFP=/usr/lib/arm-none-eabi/newlib/thumb/v7e-m+fp/hard/libc.a
MMDC_VERSION=11.17.0

MODE=install QUIET=0 FORCE=0 SMOKE=0 WITH_3D=0
for arg in "$@"; do
  case "$arg" in
    --check) MODE=check ;;
    --smoke) SMOKE=1 ;;
    --force) FORCE=1 ;;
    --with-3d) WITH_3D=1 ;;
    -q|--quiet) QUIET=1 ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "setup.sh: unknown option '$arg' (try --help)" >&2; exit 2 ;;
  esac
done

APT_PKGS=(ngspice gcc-arm-none-eabi binutils-arm-none-eabi libnewlib-arm-none-eabi
          kicad kicad-symbols kicad-footprints openjdk-25-jre-headless
          librsvg2-bin python3.12-venv cmake ninja-build)
if [ "$WITH_3D" = 1 ]; then APT_PKGS+=(kicad-packages3d); fi

SUDO=()
if [ "$(id -u)" -ne 0 ]; then SUDO=(sudo -n); fi

STAMP="$ULTRA_TOOLS_HOME/.setup-stamp"
VERSIONS="$ULTRA_TOOLS_HOME/versions.txt"
LOG="$ULTRA_TOOLS_HOME/setup.log"

say()  { if [ "$QUIET" = 0 ]; then echo "[setup] $*"; fi; }
fail() { echo "[setup] ERROR: $*" >&2; exit 1; }

stamp_hash() {
  { cat "$REPO/tools/setup.sh" "$REPO/tools/env.sh" "$REPO/tools/requirements.txt" \
        "$REPO/tools/constraints.txt" "$REPO/tools/keys/kicad-ppa.asc"; } | sha256sum | cut -c1-16
}

dpkg_ok() { dpkg-query -W -f='${Status}' "$1" 2>/dev/null | grep -q 'install ok installed'; }

# Cheap presence checks (no Python imports): the fast path's only work besides hashing.
quick_check() {
  local c
  for c in ngspice kicad-cli arm-none-eabi-gcc rsvg-convert; do
    command -v "$c" >/dev/null 2>&1 || return 1
  done
  [ -x "$ULTRA_VENV/bin/python" ] && [ -f "$FREEROUTING_JAR" ] && [ -x "$FREEROUTING_JAVA" ] \
    && [ -f "$KICAD10_SYMBOL_DIR/Device.kicad_sym" ] \
    && [ -d "$KICAD10_FOOTPRINT_DIR/Resistor_SMD.pretty" ] \
    && [ -f "$NEWLIB_HARDFP" ] && [ -x "$MMDC" ] && [ -f "$MMDC_PUPPETEER_CONFIG" ] \
    && { [ "$WITH_3D" = 0 ] || [ -d "$KICAD10_3DMODEL_DIR/Resistor_SMD.3dshapes" ]; }
}

summary_line() {
  if [ -f "$VERSIONS" ]; then
    # shellcheck disable=SC1090
    ( . "$VERSIONS"
      echo "ngspice ${NGSPICE:-?}, KiCad ${KICAD:-?}, arm-none-eabi-gcc ${ARM_GCC:-?}, FreeRouting ${FREEROUTING:-?} (Java ${FR_JAVA:-?}), venv Python ${VENV_PY:-?}: build123d ${BUILD123D:-?}, scikit-fem ${SKFEM:-?}, SKiDL ${SKIDL:-?}, easyeda2kicad ${EASYEDA2KICAD:-?}, mermaid-cli ${MERMAID:-?}" )
  else
    echo "(versions unknown; run tools/setup.sh --check)"
  fi
}

run_smoke() {
  say "running smoke tests (tools/smoke/run_all.py)"
  "$ULTRA_VENV/bin/python" "$REPO/tools/smoke/run_all.py"
}

# ---------------------------------------------------------------- fast path
HASH="$(stamp_hash)"
if [ "$MODE" = install ] && [ "$FORCE" = 0 ] && [ -f "$STAMP" ] \
   && [ "$(cat "$STAMP" 2>/dev/null)" = "$HASH" ] && quick_check; then
  if [ "$QUIET" = 1 ]; then
    echo "ultrasonic harness ready: $(summary_line). Env: tools/env.sh. Skills: spice-sim, pcb-kicad, jlc-parts, cad-mech, visual-explainer + 8 PCBA skills."
  else
    say "already installed (stamp $HASH): $(summary_line)"
  fi
  if [ "$SMOKE" = 1 ]; then run_smoke; fi
  exit 0
fi

# ---------------------------------------------------------------- verification
verify() {
  local ok=1 tmp
  tmp="$(mktemp)"
  {
    echo "NGSPICE=$(ngspice -v 2>/dev/null | grep -o 'ngspice-[0-9.]*' | head -1 | sed 's/ngspice-//')"
    echo "KICAD=$(kicad-cli version 2>/dev/null | head -1)"
    echo "ARM_GCC=$(arm-none-eabi-gcc -dumpversion 2>/dev/null)"
    echo "FREEROUTING=$(basename "$(readlink -f "$FREEROUTING_JAR" 2>/dev/null)" .jar 2>/dev/null | sed 's/freerouting-//')"
    echo "FR_JAVA=$("$FREEROUTING_JAVA" -version 2>&1 | grep -o 'version "[0-9.]*' | head -1 | sed 's/version "//')"
    echo "MERMAID=$("$MMDC" --version 2>/dev/null | head -1)"
    "$ULTRA_VENV/bin/python" - <<'PY' 2>/dev/null
import importlib.metadata as md, platform
print(f"VENV_PY={platform.python_version()}")
for key, dist in [("BUILD123D", "build123d"), ("SKFEM", "scikit-fem"), ("SKIDL", "skidl"),
                  ("EASYEDA2KICAD", "easyeda2kicad"), ("NUMPY", "numpy"), ("SCIPY", "scipy"),
                  ("MATPLOTLIB", "matplotlib")]:
    try:
        print(f"{key}={md.version(dist)}")
    except md.PackageNotFoundError:
        print(f"{key}=")
try:
    import pcbnew
    print(f"PCBNEW={pcbnew.Version()}")
except Exception:
    print("PCBNEW=")
PY
  } > "$tmp"
  # shellcheck disable=SC1090
  . "$tmp"
  local k
  for k in NGSPICE KICAD ARM_GCC FREEROUTING FR_JAVA MERMAID VENV_PY BUILD123D SKFEM SKIDL EASYEDA2KICAD NUMPY SCIPY MATPLOTLIB PCBNEW; do
    if [ -z "${!k:-}" ]; then echo "[setup] MISSING: $k" >&2; ok=0; fi
  done
  [ -f "$NEWLIB_HARDFP" ] || { echo "[setup] MISSING: newlib hard-float multilib ($NEWLIB_HARDFP)" >&2; ok=0; }
  [ -f "$KICAD10_SYMBOL_DIR/Device.kicad_sym" ] || { echo "[setup] MISSING: KiCad symbol library" >&2; ok=0; }
  [ -d "$KICAD10_FOOTPRINT_DIR/Resistor_SMD.pretty" ] || { echo "[setup] MISSING: KiCad footprint library" >&2; ok=0; }
  command -v rsvg-convert >/dev/null 2>&1 || { echo "[setup] MISSING: rsvg-convert" >&2; ok=0; }
  if [ "$ok" = 1 ] && [ -w "$ULTRA_TOOLS_HOME" ]; then cp "$tmp" "$VERSIONS"; fi
  if [ "$QUIET" = 0 ]; then sed 's/^/[setup]   /' "$tmp"; fi
  rm -f "$tmp"
  [ "$ok" = 1 ]
}

if [ "$MODE" = check ]; then
  if verify; then say "check passed"; exit 0; else echo "[setup] check FAILED (run tools/setup.sh to install)" >&2; exit 1; fi
fi

# ---------------------------------------------------------------- install
"${SUDO[@]}" mkdir -p "$ULTRA_TOOLS_HOME"
if [ ! -w "$ULTRA_TOOLS_HOME" ]; then "${SUDO[@]}" chown "$(id -u):$(id -g)" "$ULTRA_TOOLS_HOME"; fi
exec 9>"$ULTRA_TOOLS_HOME/.lock"
flock -w 1800 9 || fail "another setup.sh holds $ULTRA_TOOLS_HOME/.lock"
echo "=== setup.sh $(date -Is) hash=$HASH args=$*" >> "$LOG"

T_ALL=$SECONDS
step() { STEP="$1"; T_STEP=$SECONDS; say "$1 ..."; }
done_step() { say "  done in $((SECONDS - T_STEP)) s"; echo "step '$STEP': $((SECONDS - T_STEP)) s" >> "$LOG"; }
trap 'echo "[setup] FAILED during: ${STEP:-startup} (log: $LOG)" >&2' ERR
# Everything noisy goes to the log; in verbose mode also to the terminal.
run() { if [ "$QUIET" = 1 ]; then "$@" >> "$LOG" 2>&1; else "$@" 2>&1 | tee -a "$LOG"; fi; }

# 1. apt packages ------------------------------------------------------------------------
step "apt packages"
MISSING=()
for p in "${APT_PKGS[@]}"; do dpkg_ok "$p" || MISSING+=("$p"); done
if [ "${#MISSING[@]}" -gt 0 ]; then
  say "  installing: ${MISSING[*]}"
  CODENAME="$(. /etc/os-release && echo "${VERSION_CODENAME:-noble}")"
  PPA_LIST="/etc/apt/sources.list.d/kicad-${KICAD_SERIES}-releases.sources"
  if [ ! -f "$PPA_LIST" ]; then
    "${SUDO[@]}" install -d -m 0755 /etc/apt/keyrings
    "${SUDO[@]}" install -m 0644 "$REPO/tools/keys/kicad-ppa.asc" /etc/apt/keyrings/kicad-ppa.asc
    printf 'Types: deb\nURIs: https://ppa.launchpadcontent.net/kicad/kicad-%s-releases/ubuntu/\nSuites: %s\nComponents: main\nSigned-By: /etc/apt/keyrings/kicad-ppa.asc\n' \
      "$KICAD_SERIES" "$CODENAME" | "${SUDO[@]}" tee "$PPA_LIST" > /dev/null
  fi
  PREV_JAVA="$(readlink -f "$(command -v java 2>/dev/null || true)" 2>/dev/null || true)"
  run "${SUDO[@]}" apt-get -o DPkg::Lock::Timeout=600 update -q
  run "${SUDO[@]}" env DEBIAN_FRONTEND=noninteractive apt-get -o DPkg::Lock::Timeout=600 \
      install -y -q --no-install-recommends "${MISSING[@]}"
  # Installing JDK 25 flips the auto-mode `java` alternative; keep the image's default.
  NOW_JAVA="$(readlink -f "$(command -v java 2>/dev/null || true)" 2>/dev/null || true)"
  if [ -n "$PREV_JAVA" ] && [ "$PREV_JAVA" != "$NOW_JAVA" ] && [ -x "$PREV_JAVA" ]; then
    run "${SUDO[@]}" update-alternatives --set java "$PREV_JAVA"
  fi
  # env.sh picked FREEROUTING_JAVA before JDK 25 existed; re-resolve it now.
  if [ "$FREEROUTING_JAVA" = java ]; then unset FREEROUTING_JAVA; . "$REPO/tools/env.sh"; fi
fi
done_step

# 2. KiCad user library tables (SKiDL and pcbnew resolve "Lib:Name" through these) --------
step "KiCad library tables"
KCFG="${XDG_CONFIG_HOME:-$HOME/.config}/kicad/$KICAD_SERIES"
mkdir -p "$KCFG"
for t in sym-lib-table fp-lib-table; do
  if [ ! -f "$KCFG/$t" ] && [ -f "/usr/share/kicad/template/$t" ]; then cp "/usr/share/kicad/template/$t" "$KCFG/$t"; fi
done
# SKiDL also loads its KiCad 6-9 tool modules, which warn when their config dirs lack
# library tables; share the KiCad 10 tables with them.
for v in 6.0 7.0 8.0 9.0; do
  mkdir -p "${XDG_CONFIG_HOME:-$HOME/.config}/kicad/$v"
  for t in sym-lib-table fp-lib-table; do
    ln -sfn "../$KICAD_SERIES/$t" "${XDG_CONFIG_HOME:-$HOME/.config}/kicad/$v/$t"
  done
done
done_step

# 3. Python venv ----------------------------------------------------------------------------
step "Python venv ($ULTRA_VENV)"
# Pick the interpreter that can import pcbnew (KiCad drops it in /usr/lib/python3/dist-packages,
# which is on the distro python3's path). Falls back to python3 if KiCad isn't installed yet.
sys_python() {
  local c
  for c in /usr/bin/python3 /usr/bin/python3.1[0-9]; do
    [ -x "$c" ] && "$c" -c 'import pcbnew' 2>/dev/null && { echo "$c"; return 0; }
  done
  [ -x /usr/bin/python3 ] && { echo /usr/bin/python3; return 0; }
  return 1
}
SYS_PY="$(sys_python)" || fail "no /usr/bin/python3 found"
PY_MM="$("$SYS_PY" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
if [ ! -x "$ULTRA_VENV/bin/python" ] || \
   [ "$("$ULTRA_VENV/bin/python" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null)" != "$PY_MM" ]; then
  rm -rf "$ULTRA_VENV"
  run "$SYS_PY" -m venv --system-site-packages "$ULTRA_VENV"
fi
run env PIP_DISABLE_PIP_VERSION_CHECK=1 "$ULTRA_VENV/bin/python" -m pip install -q --no-cache-dir \
    -r "$REPO/tools/requirements.txt" -c "$REPO/tools/constraints.txt"
done_step

# 4. FreeRouting jar ------------------------------------------------------------------------
step "FreeRouting $FR_VERSION"
FR_DIR="$ULTRA_TOOLS_HOME/freerouting"
FR_FILE="$FR_DIR/freerouting-$FR_VERSION.jar"
mkdir -p "$FR_DIR"
if ! { [ -f "$FR_FILE" ] && echo "$FR_SHA256  $FR_FILE" | sha256sum -c --status; }; then
  curl -fsSL --retry 3 --retry-delay 2 -o "$FR_FILE.part" "$FR_URL"
  echo "$FR_SHA256  $FR_FILE.part" | sha256sum -c --status || fail "FreeRouting checksum mismatch ($FR_URL)"
  mv "$FR_FILE.part" "$FR_FILE"
fi
ln -sfn "freerouting-$FR_VERSION.jar" "$FR_DIR/freerouting.jar"
done_step

# 5. Mermaid CLI ---------------------------------------------------------------------------
step "mermaid-cli $MMDC_VERSION"
MM_DIR="$ULTRA_TOOLS_HOME/mermaid"
command -v npm >/dev/null 2>&1 || fail "npm not found (needed for mermaid-cli)"
CHROME="$(ls -d /opt/pw-browsers/chromium_headless_shell-*/chrome-linux/headless_shell \
                 /opt/pw-browsers/chromium-*/chrome-linux/chrome 2>/dev/null | head -1 || true)"
[ -n "$CHROME" ] || fail "no preinstalled Chromium under /opt/pw-browsers (mermaid-cli needs one)"
if [ "$("$MMDC" --version 2>/dev/null | head -1)" != "$MMDC_VERSION" ]; then
  mkdir -p "$MM_DIR"
  run env PUPPETEER_SKIP_DOWNLOAD=1 npm install --prefix "$MM_DIR" --no-audit --no-fund --silent \
      "@mermaid-js/mermaid-cli@$MMDC_VERSION"
fi
printf '{"executablePath":"%s","args":["--no-sandbox"]}\n' "$CHROME" > "$MMDC_PUPPETEER_CONFIG"
done_step

# 6. Verify -------------------------------------------------------------------------------
step "verify"
verify || fail "verification failed (log: $LOG)"
done_step

echo "$HASH" > "$STAMP"
echo "total: $((SECONDS - T_ALL)) s" >> "$LOG"
if [ "$QUIET" = 1 ]; then
  echo "ultrasonic harness installed in $((SECONDS - T_ALL)) s: $(summary_line). Env: tools/env.sh. Skills: spice-sim, pcb-kicad, jlc-parts, cad-mech, visual-explainer + 8 PCBA skills."
else
  say "installed and verified in $((SECONDS - T_ALL)) s"
fi
if [ "$SMOKE" = 1 ]; then run_smoke; fi
