#!/usr/bin/env python3
"""Draw docs/diagrams/simplification.svg from synthesis.json (light palette; render.sh darkens it).

    python3 docs/research/simplify/make_diagram.py && bash docs/diagrams/render.sh docs/diagrams/simplification.svg

Style follows docs/diagrams/schematic-rev1.svg. Colours are only the palette values mapped by docs/diagrams/darken.py.
Each square in the matrix is one placed part of the pod board (hw/pod/bom_jlc.csv, block map of integration-map.md section 2).
"""
import json
from html import escape
from pathlib import Path

HERE = Path(__file__).parent
REPO = HERE.parents[2]
_J = json.load(open(HERE / "synthesis.json"))
S = _J["pkg"]
V = _J["var"]
IDS = json.load(open(HERE / "ecr-ids.json"))

BLOCKS = {
    "MCU": "U1 C1 C2 C3 C4 C5 C6 C7 C10 C20 R1 R11", "Core SMPS": "L1 C8 C9", "Clock (crystal)": "Y1 C11 C12", "Mic": "U2 R2 C13",
    "Bridge": "Q1 Q2 R3 R4 R5 R6 C14", "Self-test": "R21 R22 C22", "Dock / USB": "D4 D3 U6 R18 R19 R12 R13 C15",
    "Charger": "U3 C16 C21 RT1 R15 R16 R17", "VBAT sense": "R8 R9 C19", "LDO": "U4 C17 C18 R20", "UI (button, LED)": "SW1 R10 R14",
}
BLOCKS = {k: v.split() for k, v in BLOCKS.items()}
KEYS = list("TABCD")
W, H = 1520, 1090
X0, CW, GAP = 226, 250, 6                     # first column x, column width, gap
LABELW = 190

INK, MUTED, SURF, PANEL_B, PANEL_G, PANEL_O, BAND = "#1f2328", "#57606a", "#fbfaf7", "#e8f0fb", "#e8f3ec", "#fff4ea", "#f3f1ea"
BLUE, GREEN, ORANGE, RED, OLIVE = "#2a78d6", "#1a7a55", "#b8520a", "#e34948", "#8a8676"

o = []


def t(x, y, s, size=12, weight=None, fill=INK, anchor=None):
    a = f' text-anchor="{anchor}"' if anchor else ""
    w = f' font-weight="{weight}"' if weight else ""
    o.append(f'<text x="{x}" y="{y}" font-size="{size}"{w} fill="{fill}"{a}>{escape(s)}</text>')


def wrap(s, width_px, size=11):
    cw = size * 0.53
    n = max(8, int(width_px / cw))
    words, lines, cur = s.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > n and cur:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        lines.append(cur)
    return lines


def para(x, y, s, width_px, size=11, fill=INK, lh=14, weight=None):
    for i, ln in enumerate(wrap(s, width_px, size)):
        t(x, y + i * lh, ln, size, weight, fill)


def colx(i):
    return X0 + i * (CW + GAP)


def delta_fill(txt):
    if txt.startswith("+"):
        return ORANGE
    if txt.startswith("-") or txt.startswith("−"):
        return GREEN
    return INK


o.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" font-family="Helvetica, Arial, sans-serif" '
         f'aria-label="Today versus three simplification packages for one pod board. Package B, recommended, goes from 56 to 49 placed parts, '
         f'30 to 27 BOM lines per order, pod 7.80 to 6.83 cubic centimetres, arm wires 4 to 2, hand wires 12 to 9, with the 3 volt rail peak '
         f'falling from 326 to about 92 milliamps. Package A only removes 4 parts. Package C swaps the charger. Package D is a ceiling with 41 parts.">')
o.append(f'<rect width="{W}" height="{H}" rx="14" fill="{SURF}"/>')
t(36, 40, "Simplification study: today vs three packages, one pod board (rev 1 is the final device)", 20, "700")
t(36, 62, "Each square is one placed part, grouped by function. 2026-10-02. Numbers computed by docs/research/simplify/synthesis.py from "
          "hw/pod/bom_jlc.csv (56 parts), sim/checks/size_budget.py and the JLC parts API.", 13, fill=MUTED)

# ---- column headers
heads = {
    "T": ("Today (Rev E)", "gen.py as drawn, 34 x 13 board", None),
    "A": ("A  Cleanups", "the floor: four 0402 parts out, shunt shrinks, ECR-0005 closed in firmware; size unchanged", IDS["A"]["id"]),
    "B": ("B  Final-size integration", "A + bridge and self-test cuts, CC out, LED on the lid, lid-hung 28 x 12 board", IDS["B"]["id"]),
    "C": ("C  B + BQ25186", "B with the charger swapped for a hand-reworkable WSON: robustness, not simplification", IDS["C"]["id"]),
    "D": ("D  Ceiling", "reference only: no crystal, no LED, no I2C pull-ups, plate off, thin walls", "no ECR"),
}
for i, k in enumerate(KEYS):
    x, y, w, h = colx(i), 88, CW, 78
    fill = {"T": BAND, "A": PANEL_B, "B": PANEL_G, "C": PANEL_B, "D": BAND}[k]
    stroke = {"T": OLIVE, "A": BLUE, "B": GREEN, "C": BLUE, "D": OLIVE}[k]
    sw = 3 if k == "B" else 1.5
    dash = ' stroke-dasharray="6 4"' if k == "D" else ""
    o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{dash}/>')
    t(x + 10, y + 20, heads[k][0], 14, "700")
    para(x + 10, y + 36, heads[k][1], w - 20, 11, MUTED)
    if heads[k][2]:
        t(x + w - 10, y + 20, heads[k][2], 11, "700", GREEN if k == "B" else MUTED, "end")
t(colx(2) + CW / 2, 82, "RECOMMENDED", 11, "700", GREEN, "middle")

# ---- dot matrix
Y_M = 184
RH = 28
SQ, SG = 14, 4
t(36, Y_M - 8, "Placed parts by function", 13, "700")
for r, (blk, refs) in enumerate(BLOCKS.items()):
    y = Y_M + r * RH
    if r % 2 == 0:
        o.append(f'<rect x="30" y="{y - 2}" width="{W - 60}" height="{RH}" fill="{BAND}" opacity="0.65"/>')
    t(36, y + 17, f"{blk}", 12)
    t(X0 - 14, y + 17, str(len(refs)), 11, fill=MUTED, anchor="end")
    for i, k in enumerate(KEYS):
        s = S[k]
        info = s["blocks"][blk if blk in s["blocks"] else {"Clock (crystal)": "Clock", "UI (button, LED)": "UI"}.get(blk, blk)]
        x = colx(i) + 8
        kept = [rf for rf in refs if rf not in s["removed"]]
        removed = [rf for rf in refs if rf in s["removed"]]
        n = 0
        for rf in kept:
            sw = rf in s["swap"]
            o.append(f'<rect x="{x + n * (SQ + SG)}" y="{y + 4}" width="{SQ}" height="{SQ}" rx="2" fill="{PANEL_O if sw else PANEL_B}" '
                     f'stroke="{ORANGE if sw else BLUE}" stroke-width="{2 if sw else 1.4}"/>')
            n += 1
        for rf in removed:
            o.append(f'<rect x="{x + n * (SQ + SG)}" y="{y + 4}" width="{SQ}" height="{SQ}" rx="2" fill="none" stroke="{RED}" '
                     f'stroke-width="1.2" stroke-dasharray="3 2"/>')
            o.append(f'<path d="M{x + n * (SQ + SG) + 3},{y + 7} L{x + n * (SQ + SG) + SQ - 3},{y + 4 + SQ - 3} M{x + n * (SQ + SG) + SQ - 3},{y + 7} '
                     f'L{x + n * (SQ + SG) + 3},{y + 4 + SQ - 3}" stroke="{RED}" stroke-width="1"/>')
            n += 1
        if info.get("added"):
            o.append(f'<rect x="{x + n * (SQ + SG)}" y="{y + 4}" width="{SQ}" height="{SQ}" rx="2" fill="{PANEL_G}" stroke="{GREEN}" stroke-width="2"/>')
            o.append(f'<path d="M{x + n * (SQ + SG) + 7},{y + 7} v8 M{x + n * (SQ + SG) + 3},{y + 11} h8" stroke="{GREEN}" stroke-width="1.6"/>')
            n += 1
        if k == "D" and blk == "UI (button, LED)":
            pass
# totals row
y = Y_M + len(BLOCKS) * RH + 6
o.append(f'<line x1="30" y1="{y - 2}" x2="{W - 30}" y2="{y - 2}" stroke="{INK}" stroke-width="1.2"/>')
t(36, y + 24, "Placed parts, pod board", 14, "700")
for i, k in enumerate(KEYS):
    s = S[k]
    d = s["placements"] - S["T"]["placements"]
    t(colx(i) + 8, y + 26, str(s["placements"]), 24, "700")
    if d:
        t(colx(i) + 54, y + 26, f"{d:+d}".replace("-", "−"), 16, "700", delta_fill(f"{d:+d}"))
y_after = y + 40

# ---- KPI table
rows = []


def vol(s):
    return round(s["size"]["vol"] / 1000 + 1e-9, 2)


def d_txt(cur, base, fmt="{}", dfmt="{:+}"):
    return fmt.format(cur) + ("" if cur == base else "  " + dfmt.format(round(cur - base, 2)).replace("-", "−"))


T = S["T"]
rows.append(("BOM lines per JLC order", [d_txt(S[k]["lines"], T["lines"]) for k in KEYS]))
rows.append(("Extended types per order", [d_txt(S[k]["ext"], T["ext"]) for k in KEYS]))
rows.append(("Pod envelope, cm3", [f'{vol(S[k]):.2f}' + ("" if k in "TA" else f'  −{abs(S[k]["size"]["dvol_pct"]):.1f} %') for k in KEYS]))
rows.append(("Height incl. belly, mm", [f'{S[k]["size"]["z"]}' for k in KEYS]))
rows.append(("Hand wires / arm wires", [f'{S[k]["wires"]} / {S[k]["arm"]}' for k in KEYS]))
rows.append(("MCU pins free: listed / clean", [f'{S[k]["spare_listed"]} / {S[k]["spare_clean"]}' for k in KEYS]))
def _rt(s_):
    a, b = s_["rt_typ"], s_["rt_worst"]
    f = lambda x: f"{x[0]:.1f}" if x[0] == x[1] else f"{x[0]:.1f}-{x[1]:.1f}"
    return f"{f(a)} / {f(b)}"
rows.append(("Runtime at 4.20 V, h: typ / worst", [_rt(S[k]) for k in KEYS]))
rows.append(("+3V0 peak (LDO rated 300 mA)", ["326 mA"] + ["~92 mA"] * 4))
rows.append(("$/order change (4 boards)", ["-"] + [f'{S[k]["usd_order_total"]:+.2f}'.replace("-", "−") for k in "ABCD"]))
t(36, y_after + 16, "Totals", 13, "700")
RH2 = 27
for r, (lab, vals) in enumerate(rows):
    yy = y_after + 26 + r * RH2
    if r % 2 == 0:
        o.append(f'<rect x="30" y="{yy - 2}" width="{W - 60}" height="{RH2}" fill="{BAND}" opacity="0.65"/>')
    t(36, yy + 16, lab, 12)
    for i, v in enumerate(vals):
        # colour only the delta part
        parts = v.split("  ")
        t(colx(i) + 8, yy + 16, parts[0], 13, "700" if i == 2 else None)
        if len(parts) > 1:
            t(colx(i) + 8 + len(parts[0]) * 7.6 + 8, yy + 16, parts[1], 12, "700", delta_fill(parts[1]))
        if lab.startswith("Pod envelope") and v:
            bw = 120 * float(parts[0]) / 7.80
            o.append(f'<rect x="{colx(i) + 128}" y="{yy + 6}" width="{bw:.1f}" height="9" rx="2" fill="{GREEN if i in (2, 3) else (BLUE if i == 1 else OLIVE)}" opacity="0.55"/>')
y_strip = y_after + 26 + len(rows) * RH2 + 14

# ---- outside the board strip
o.append(f'<line x1="30" y1="{y_strip - 6}" x2="{W - 30}" y2="{y_strip - 6}" stroke="{INK}" stroke-width="1.2"/>')
t(36, y_strip + 14, "What changes outside the board", 13, "700")
strip = [
    ("Lid and shell", [
        "board floats on foam strips between lid ribs; belly 3.5 mm; F gap 1.5; lid 1.0",
        "no change",
        "board hung from the lid (2 pins + 4 VHB spots) with an SW1 back-stop; belly 2.05 (USB-C fallback spent), F gap 1.25, lid 0.8; LED light pipe; 28 x 12",
        "same as B",
        "B plus plate off, walls 0.7, thin dock, 26 x 12 (all hardware-only)"]),
    ("Arm wires and hand joints", [
        "4 litz (2 audio + 2 LED) and a pad board: 10 hand joints (pod end 4, pad end 6)",
        "unchanged: 4 wires, 10 joints",
        "2 litz (audio only), no pad board: 4 joints (pod end 2, exciter splices 2); LED moves to the lid",
        "same as B",
        "2 litz; no LED at all (no board-alive light)"]),
    ("Firmware", [
        "-",
        "UCPD_DBDIS first, duty clamp, ILIM policy, boot stub (DFU-first), self-test over-current cutoff, wire-health check",
        "A + TRGO2 sampling for self-test, N-pin init order, LED PWM 200.0225 kHz, PB6 printf",
        "B + BQ25186 read-back, VINDPM, SYS_REG tracking",
        "C + HSI16 trim from USB SOF, slow I2C clock"]),
    ("Gates (O21 blocks purchases)", [
        "-",
        "wall-charger ILIM policy; DFU with R11 absent; 322 mA step on the scope",
        "JLCDFM (free); keying, E1, dummies, bond coupon need samples: lift O21 or take B3",
        "B + BQ25186 datasheet re-audit",
        "C + D16 trim, wall and plate coupons"]),
]
RH3 = 66
for r, (lab, vals) in enumerate(strip):
    yy = y_strip + 24 + r * RH3
    if r % 2 == 0:
        o.append(f'<rect x="30" y="{yy - 4}" width="{W - 60}" height="{RH3 - 2}" fill="{BAND}" opacity="0.65"/>')
    t(36, yy + 12, lab, 12)
    for i, v in enumerate(vals):
        para(colx(i) + 8, yy + 12, v, CW - 16, 11, INK if i != 0 else MUTED, 13)
y_call = y_strip + 24 + len(strip) * RH3 + 4
B3 = V["B3"]
o.append(f'<rect x="30" y="{y_call}" width="{W - 60}" height="50" rx="8" fill="{PANEL_O}" stroke="{ORANGE}" stroke-width="2"/>')
t(42, y_call + 20, "O21 / O22 decision for you", 13, "700", ORANGE)
para(240, y_call + 20, f"B needs a ~$22 sample set (dock pair, exciters, dummy wire) that O21 forbids buying. Lift O21 for it (recommended) or freeze on the defaults, "
     f"B3 = B without PER-01D and PER-07: {B3['placements']} placements, {B3['lines']} BOM lines, {B3['wires']} wires / {B3['pads']} pads, {B3['arm']} arm wires, still "
     f"{round(B3['size']['vol'] / 1000 + 1e-9, 2):.2f} cm3.", W - 290, 12, INK, 15)
y_leg = y_call + 50 + 12

# ---- legend
o.append(f'<line x1="30" y1="{y_leg - 6}" x2="{W - 30}" y2="{y_leg - 6}" stroke="{INK}" stroke-width="1.2"/>')
lx = 36
for kind, label in (("kept", "part kept"), ("swap", "part kept but swapped (R21 to 0402, C14 to 1 uF, U3 to BQ25186 in C)"), ("rm", "part removed"), ("add", "part added (the LED joins the pod board)")):
    if kind == "kept":
        o.append(f'<rect x="{lx}" y="{y_leg + 4}" width="{SQ}" height="{SQ}" rx="2" fill="{PANEL_B}" stroke="{BLUE}" stroke-width="1.4"/>')
    elif kind == "swap":
        o.append(f'<rect x="{lx}" y="{y_leg + 4}" width="{SQ}" height="{SQ}" rx="2" fill="{PANEL_O}" stroke="{ORANGE}" stroke-width="2"/>')
    elif kind == "rm":
        o.append(f'<rect x="{lx}" y="{y_leg + 4}" width="{SQ}" height="{SQ}" rx="2" fill="none" stroke="{RED}" stroke-width="1.2" stroke-dasharray="3 2"/>')
    else:
        o.append(f'<rect x="{lx}" y="{y_leg + 4}" width="{SQ}" height="{SQ}" rx="2" fill="{PANEL_G}" stroke="{GREEN}" stroke-width="2"/>')
    t(lx + 22, y_leg + 16, label, 12)
    lx += 22 + len(label) * 6.3 + 26
para(36, y_leg + 40, "Costs: JLC Standard PCBA charges $1.53 per BOM line (Basic or Extended) plus setup, stencil and X-ray, so lines and hidden-joint packages are the cost drivers, "
     "not Extended types. $/order = parts for 4 boards + line fees + about $10 for not ordering the pad board (derived, unquoted). Money ranks last (spec O19).", W - 72, 11, MUTED, 14)
para(36, y_leg + 72, "No integrated part replaced several cheap ones: nPM1300, BQ25155/50, MAX98357A and 500 mA LDOs fail on size, D11, package fragility, bridge peaks or D14. "
     "Full ranking, ledgers and sources: docs/research/simplification-study.md. ECRs: " + ", ".join(IDS[k]["id"] for k in "ABC") + ".", W - 72, 11, MUTED, 14)

o.append("</svg>")
svg = "\n".join(o)
# size the canvas to the content
need = int(y_leg + 100)
svg = svg.replace(f'viewBox="0 0 {W} {H}"', f'viewBox="0 0 {W} {need}"').replace(f'<rect width="{W}" height="{H}" rx="14"', f'<rect width="{W}" height="{need}" rx="14"')
(REPO / "docs/diagrams/simplification.svg").write_text(svg)
print("wrote docs/diagrams/simplification.svg", W, need)
