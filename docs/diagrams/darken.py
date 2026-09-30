"""Map this project's light diagram palette to dark mode (owner preference, 2026-09-30).

    python3 docs/diagrams/darken.py in.svg out.svg

render.sh calls this by default (LIGHT=1 renders the original light version). Colours not in
the table pass through unchanged, so new diagrams should stick to these palette values.
"""
import re
import sys

MAP = {
    # surfaces
    "#fbfaf7": "#141518", "#fcfcfb": "#141518", "#ffffff": "#1e2025", "#f3f1ea": "#2a2c31",
    # tinted panels
    "#e8f3ec": "#15301f", "#e8f0fb": "#172539", "#fff4ea": "#3a2615",
    # ink
    "#1f2328": "#e8e8e5", "#0b0b0b": "#e8e8e5", "#57606a": "#a4a9b0", "#52514e": "#a4a9b0", "#8a8676": "#a19d8d",
    # accents (lifted for contrast on dark)
    "#1a7a55": "#52d39e", "#1baf7a": "#2fc98f", "#b8520a": "#f28c3f", "#2a78d6": "#5b9ff2",
    "#e34948": "#ff6d6c", "#4a3aa7": "#8d7ff0", "#008300": "#35b535", "#eb6834": "#f58a5c",
    # PCB cross-section materials
    "#ece5cd": "#3b3727", "#ddd4b4": "#4b4533", "#e9e2c9": "#3b3727", "#d8cfae": "#4b4533",
    "#2f2f33": "#0a0a0c", "#c9c5b8": "#4a4d55",
}


def darken(svg: str) -> str:
    # white *text* (labels on dark chips, badge numbers) must stay white: only surfaces go dark
    def keep_white_text(m):
        return m.group(0).replace("#ffffff", "#f5f5f2").replace("#FFFFFF", "#f5f5f2")
    svg = re.sub(r"<(?:text|tspan)\b[^>]*>|<g\b[^>]*font-[^>]*>", keep_white_text, svg)

    def sub(m):
        c = m.group(0).lower()
        return MAP.get(c, m.group(0))
    return re.sub(r"#[0-9a-fA-F]{6}\b", sub, svg)


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    open(dst, "w").write(darken(open(src).read()))
