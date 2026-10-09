"""Owner-facing loudness choice (issue #2). Writes d17-choice.svg; render: docs/diagrams/render.sh.
Margins: docs/proof/electrical/audibility-reconciled.md (median, worst call, dB over masked threshold).
Dot rule: worst>0 all heard; median>0 most heard; median>-4 faint lost; else lost."""
import pathlib
BG, PANEL, TX, T2, CY, PK, GR = "#000000", "#141518", "#e8e8e5", "#a4a9b0", "#5fd8ff", "#f09bbd", "#2c2e34"
cols = [("B", "today", False), ("A", "limiter", False), ("A + L", "RECOMMENDED", True), ("A + X + L", "bigger exciter", False)]
sub = ["quiet-street level; no limiter", "safe volume ceiling", "A plus a Loud mode (+12 dB)", "A + heavier exciter + Loud mode"]
# (median, worst) per scene: quiet street(office NC-35), day street, traffic, cafe, car
M = {
 0: [(11,-6),(8,-9),(-2,-19),(-3.6,-20.4),(-6,-23)],
 1: [(17,1),(14,-3),(4,-13),(2.5,-14.1),(0,-17)],
 2: [(23,13),(20,9),(10,-1),(8.6,-2.1),(6,-5)],
 3: [(31,20),(28,17),(18,7),(16.2,5.5),(14,3)],
}
rows = ["Quiet street", "Day street", "Heavy traffic", "Cafe", "Car"]
def state(m, w):
    if w > 0: return 0
    if m > 0: return 1
    if m > -4: return 2
    return 3
W, H = 1400, 980
x0, cw, top = 250, 280, 190
o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="DejaVu Sans, Arial, sans-serif">',
     f'<rect width="{W}" height="{H}" fill="{BG}"/>']
def t(x, y, s, sz=18, c=TX, a="start", b=False):
    o.append(f'<text x="{x}" y="{y}" font-size="{sz}" fill="{c}" text-anchor="{a}"{" font-weight=\"bold\"" if b else ""}>{s}</text>')
t(40, 52, "Which loudness do we ship?", 32, TX, b=True)
t(40, 84, "Can you hear every bat call, wherever you walk? Pick a column.", 18, T2)
for i, (n, tag, rec) in enumerate(cols):
    x = x0 + i * cw
    o.append(f'<rect x="{x+6}" y="{top-62}" width="{cw-12}" height="{H-top-110}" rx="14" fill="{PANEL}" stroke="{CY if rec else GR}" stroke-width="{4 if rec else 1.5}"/>')
    t(x+cw/2, top-26, n, 30, CY if rec else TX, "middle", True)
    t(x+cw/2, top-4, tag, 14, CY if rec else T2, "middle", rec)
    t(x+cw/2, top+18, sub[i], 12, T2, "middle")
def dot(cx, cy, s):
    if s == 0: o.append(f'<circle cx="{cx}" cy="{cy}" r="15" fill="{CY}"/>')
    elif s == 1: o.append(f'<circle cx="{cx}" cy="{cy}" r="15" fill="none" stroke="{CY}" stroke-width="3"/><circle cx="{cx}" cy="{cy}" r="8" fill="{CY}"/>')
    elif s == 2: o.append(f'<circle cx="{cx}" cy="{cy}" r="15" fill="none" stroke="{PK}" stroke-width="3"/><circle cx="{cx}" cy="{cy}" r="4" fill="{PK}"/>')
    else: o.append(f'<circle cx="{cx}" cy="{cy}" r="15" fill="{PK}"/><path d="M{cx-7} {cy-7}L{cx+7} {cy+7}M{cx+7} {cy-7}L{cx-7} {cy+7}" stroke="{BG}" stroke-width="3.5"/>')
word = ["every call heard", "most heard", "faint calls lost", "lost"]
y = top + 62
t(40, y-8, "HEARING", 14, T2, b=True)
for r, name in enumerate(rows):
    yy = y + r * 62 + 22
    t(40, yy + 6, name, 20)
    for i in range(4):
        m, w = M[i][r]
        s = state(m, w)
        cx = x0 + i * cw + 46
        dot(cx, yy, s)
        t(cx + 28, yy + 6, word[s], 15, PK if s >= 2 else TX)
    if r < 4: o.append(f'<line x1="40" y1="{yy+31}" x2="{x0+4*cw-6}" y2="{yy+31}" stroke="{GR}"/>')
yb = y + 5 * 62 + 28
o.append(f'<line x1="40" y1="{yb-14}" x2="{x0+4*cw-6}" y2="{yb-14}" stroke="{T2}" stroke-width="1.5"/>')
def row(label, vals, yy, sz=22, note=None):
    t(40, yy, label, 20)
    for i, v in enumerate(vals):
        c = PK if (isinstance(v, tuple) and v[1]) else TX
        t(x0 + i * cw + cw/2, yy, v[0] if isinstance(v, tuple) else v, sz, c, "middle", True)
row("Battery, dense calls", ["12.3 h", "12.1 h", "9.5 h", "~9.3 h"], yb + 22)
row("Battery, quiet dusk", ["32 h", "32 h", "28 h", "~27 h"], yb + 58)
t(40, yb + 94, "Battery, loud music", 20)
for i, v in enumerate(["(not tested)", "(not tested)", "4 h", "4 h"]):
    t(x0 + i*cw + cw/2, yb + 94, v, 20 if v[0] != "(" else 14, PK if v == "4 h" else T2, "middle", v[0] != "(")
o.append(f'<line x1="40" y1="{yb+112}" x2="{x0+4*cw-6}" y2="{yb+112}" stroke="{GR}"/>')
t(40, yb + 148, "Weight at the ear", 20)
for i, v in enumerate(["1.2 g", "1.2 g", "1.2 g", "12.8 g"]):
    t(x0 + i*cw + cw/2, yb + 148, v, 26, PK if i == 3 else TX, "middle", True)
t(x0 + 3*cw + cw/2, yb + 172, "10x heavier", 14, PK, "middle")
# legend
ly = H - 74
lx = 40
for s, lab in enumerate(["every call heard", "most heard, the faintest missed", "faint calls lost", "lost"]):
    dot(lx + 15, ly, s); t(lx + 40, ly + 6, lab, 15, T2); lx += 40 + 9 * len(lab) + 50
t(40, H - 40, "Sources: 2969b65, 31fba64 (hearing); 3414ce5, b944df6 (loud-mode battery); cea34fe (real-use battery).", 12, T2)
t(40, H - 22, "Dense = calls 81% of the time, dusk = 18%; loud music = nonstop; A+X+L battery scaled +2%. Call level 75 dB assumed.", 12, T2)
o.append('</svg>')
pathlib.Path(__file__).with_name("d17-choice.svg").write_text("\n".join(o))
