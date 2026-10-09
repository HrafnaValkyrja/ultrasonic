#!/usr/bin/env python3
"""K4 pod cardboard dummy template, 1:1 on A4 (ledger I-029). Raw PDF, no deps.
Run: python3 docs/bench/k4_dummy_template.py -> docs/bench/k4-dummy-template.pdf
Dims: 49.85 x 6.4 x 15.25 mm (hw/current.yaml k4 / shell k4s_lift). Print at 100% / Actual size."""
import os, re
K = 72 / 25.4
L, T, H = 49.85, 6.4, 15.25
POS = (17.65, 30.0)
ops = []
def f(v): return f"{v*K:.6f}"
def line(x1, y1, x2, y2, w=0.3, dash=None):
    d = f"[{dash[0]*K:.3f} {dash[1]*K:.3f}] 0 d " if dash else "[] 0 d "
    ops.append(f"{w:.2f} w {d}{f(x1)} {f(y1)} m {f(x2)} {f(y2)} l S")
def rect(x, y, w, h, lw=0.5):
    ops.append(f"{lw} w [] 0 d {f(x)} {f(y)} {f(w)} {f(h)} re S")
def text(x, y, s, size=10, bold=False):
    s = s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    ops.append(f"BT /{'F2' if bold else 'F1'} {size} Tf {f(x)} {f(y)} Td ({s}) Tj ET")

text(15, 285, "K4 pod cardboard dummy, 1:1 (ledger I-029)", 14, True)
text(15, 279, "Print at 100% / Actual size (not Fit to page). Check the bar below with a ruler first.", 9)
# scale bar
bx, by = 15, 268
line(bx, by, bx+10, by, 1.0)
line(bx, by-2, bx, by+2, 1.0); line(bx+10, by-2, bx+10, by+2, 1.0)
text(bx+13, by-1, "= 10.00 mm. If your ruler disagrees, stop: reprint at 100%.", 9)

# box net
x0, y0 = 40, 150
panels = [("glue tab", 6, 0), ("bottom", T, 1), ("back", H, 1), ("top", T, 1), ("front face", H, 1)]
y = y0; ys = []
for n, h, _ in panels:
    ys.append((n, y, h)); y += h
ytop = y
# cut outline: tab trapezoid-free simple rectangle
line(x0, y0, x0+L, y0, 0.7); line(x0, y0, x0, ytop, 0.7); line(x0+L, y0, x0+L, ytop, 0.7)
line(x0, ytop, x0+L, ytop, 0.7)
# folds
for n, yy, h in ys[1:]:
    line(x0, yy, x0+L, yy, 0.3, (2, 1.5))
# end caps on front-face panel (T wide x H tall)
fy = ys[4][1]
for sx in (-T, L):
    rect(x0+sx, fy, T, H, 0.7)
line(x0, fy, x0, fy+H, 0.3, (2, 1.5)); line(x0+L, fy, x0+L, fy+H, 0.3, (2, 1.5))
for n, yy, h in ys:
    text(x0+L/2-8, yy+h/2-1.2, n, 8)
text(x0-T+0.8, fy+H/2-1, "cap", 7); text(x0+L+0.8, fy+H/2-1, "cap", 7)
# dimension notes
text(x0, ytop+4, f"{L} mm long", 8); text(x0+L+10, ys[2][1]+5, f"{H} mm", 8); text(x0+L+10, ys[1][1]+1, f"{T} mm", 8)
text(15, y0-8, "Solid = cut. Dashed = fold. Folded box: 49.85 long x 6.4 thick x 15.25 tall.", 8)

# arm guide strip
ax, ay = 20, 112
line(ax, ay, ax+100, ay, 0.5)
for i in range(0, 101):
    line(ax+i, ay, ax+i, ay+(3 if i % 10 == 0 else 1.5), 0.3)
    if i % 10 == 0: text(ax+i-1.2, ay+4.5, str(i), 7)
line(ax, ay-8, ax, ay+12, 1.2)
text(ax-14, ay-12, "HINGE", 9, True)
text(ax+3, ay-12, "(mm along the arm, measured from the hinge pin)", 8)
for p, nm in zip(POS, ("A  today", "B  slid rearward")):
    xx = ax + p
    line(xx, ay-9, xx, ay+10, 1.0)
    line(xx-2.5, ay-5.5, xx+2.5, ay-0.5, 1.0); line(xx-2.5, ay-0.5, xx+2.5, ay-5.5, 1.0)
    text(xx+1.5, ay-20 if p < 20 else ay-27, f"{nm}: FRONT edge at {p:g} mm", 9, True)
text(ax+60, ay+14, "Pod body runs rearward (right) from its front edge.", 8)
text(15, 80, "Arm guide is 1:1: lay the glasses arm on the line, hinge pin on the HINGE bar.", 8)

# steps
text(15, 62, "Steps", 12, True)
text(15, 55, "1.  Cut out the net, fold along the dashed lines, glue the tab, and tape the caps shut.", 10)
text(15, 48, "2.  Tape the box to the outside of the arm with its FRONT edge on mark A. Wear them. Note comfort and look.", 10)
text(15, 41, "3.  Peel off, retape with the FRONT edge on mark B, and wear again. Tell me which you prefer.", 10)

content = "\n".join(ops).encode("latin-1")
objs = [b"<</Type/Catalog/Pages 2 0 R>>", b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 595.2756 841.8898]/Contents 4 0 R/Resources<</Font<</F1 5 0 R/F2 6 0 R>>>>>>",
        b"<</Length %d>>\nstream\n" % len(content) + content + b"\nendstream",
        b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>", b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica-Bold>>"]
out = b"%PDF-1.4\n"; offs = []
for i, o in enumerate(objs, 1):
    offs.append(len(out)); out += b"%d 0 obj\n" % i + o + b"\nendobj\n"
xr = len(out)
out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs)+1) + b"".join(b"%010d 00000 n \n" % o for o in offs)
out += b"trailer<</Size %d/Root 1 0 R>>\nstartxref\n%d\n%%%%EOF\n" % (len(objs)+1, xr)
dst = os.path.join(os.path.dirname(os.path.abspath(__file__)), "k4-dummy-template.pdf")
open(dst, "wb").write(out)
# verify scale bar: first stroke in content is the bar
m = re.search(rb"([\d.]+) ([\d.]+) m ([\d.]+) ([\d.]+) l S", content.split(b"\n")[2])
print("scale bar mm:", (float(m.group(3)) - float(m.group(1))) / K)
