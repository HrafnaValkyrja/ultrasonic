#!/usr/bin/env bash
# Render a diagram to a PNG for inline display in chat (the owner's client shows PNGs
# inline; SVG files only appear as file cards).
#   docs/diagrams/render.sh <file.svg|file.mmd> [out.png]
# Dark mode is the default (owner preference); LIGHT=1 renders the light original.
# SVG: sized from its viewBox, rendered at 2x by the preinstalled headless Chromium.
# Mermaid (.mmd): rendered at 2x by mermaid-cli (installed by tools/setup.sh), white background.
set -euo pipefail
src="$1"; out="${2:-${src%.*}.png}"
case "$src" in
  *.mmd)
    here="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
    # shellcheck source=/dev/null
    . "$here/tools/env.sh"
    [ -x "$MMDC" ] || { echo "render.sh: mermaid-cli missing; run tools/setup.sh" >&2; exit 1; }
    if [ "${LIGHT:-0}" = "1" ]; then theme=(-b white); else theme=(-t dark -b "#141518"); fi
    "$MMDC" -q -p "$MMDC_PUPPETEER_CONFIG" -w 1200 -s 2 "${theme[@]}" -i "$src" -o "$out" ;;
  *.svg)
    if [ "${LIGHT:-0}" != "1" ]; then
      tmp="$(mktemp --suffix=.svg -p "$(dirname "$src")" .dark-XXXX)"
      trap 'rm -f "$tmp"' EXIT
      python3 "$(dirname "${BASH_SOURCE[0]}")/darken.py" "$src" "$tmp"
      src="$tmp"
    fi
    read -r w h < <(grep -o 'viewBox="[^"]*"' "$src" | head -1 | tr -d '"' | awk '{print $3, $4}')
    here="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
    # shellcheck source=/dev/null
    . "$here/tools/env.sh"
    chrome="$(ultra_find_chrome || true)"
    [ -n "$chrome" ] || { echo "render.sh: no Chromium found; install chromium or set ULTRA_CHROME" >&2; exit 1; }
    "$chrome" --no-sandbox --hide-scrollbars --force-device-scale-factor=2 \
      --window-size="${w},${h}" --screenshot="$(realpath -m "$out")" "file://$(realpath "$src")" >/dev/null 2>&1 ;;
  *) echo "render.sh: expected .svg or .mmd, got $src" >&2; exit 2 ;;
esac
echo "$out"
