#!/usr/bin/env bash
# Render an SVG diagram to a PNG for inline display in chat (the owner's client shows PNGs
# inline; SVG files only appear as file cards).
#   docs/diagrams/render.sh <file.svg> [out.png]
# Size comes from the SVG's viewBox; output is rendered at 2x for crisp text.
set -euo pipefail
svg="$1"; out="${2:-${svg%.svg}.png}"
read -r w h < <(grep -o 'viewBox="[^"]*"' "$svg" | head -1 | tr -d '"' | awk '{print $3, $4}')
chrome=""
for c in /opt/pw-browsers/chromium_headless_shell-*/chrome-linux/headless_shell \
         /opt/pw-browsers/chromium-*/chrome-linux/chrome; do
  [ -x "$c" ] && { chrome="$c"; break; }
done
[ -n "$chrome" ] || { echo "render.sh: no headless Chromium found under /opt/pw-browsers" >&2; exit 1; }
"$chrome" --no-sandbox --hide-scrollbars --force-device-scale-factor=2 \
  --window-size="${w},${h}" --screenshot="$(realpath -m "$out")" "file://$(realpath "$svg")" >/dev/null 2>&1
echo "$out"
