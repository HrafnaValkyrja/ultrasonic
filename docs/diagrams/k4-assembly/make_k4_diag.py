#!/usr/bin/env python3
"""K4-DIAG: stack section (P over M, BM28, ledge, glue post, lid), dock section, BM28 pin map -> docs/diagrams/k4-*.svg (light palette; render.sh darkens).
Numbers: hw/mech/dims_k4.py; BM28 map parsed from hw/pod/k4/gen.py BM28_PINS.
    python3 docs/diagrams/k4-assembly/make_k4_diag.py && for f in docs/diagrams/k4-{stack-section,dock-section,bm28-map}.svg; do systemd-run --user --scope --quiet -p MemoryMax=4G -p MemorySwapMax=0 docs/diagrams/render.sh $f; done"""
import re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
import make_k4_assembly as A
from make_k4_assembly import S, INK, MUT, GRN, BLU, ORG, RED, PUR, TG, TB, TO, PANEL, K
OUT = HERE.parent

def save(s, name):
    (OUT / name).write_text("\n".join(s.o + ["</svg>"]))

def d_stack():
    s = S(1280, 700, "K4 stack, side section: lid at the top, tub floor at the bottom", "dims_k4.py, 2026-10-08 (ECR-0020..0023). Thickness x 60; mm in the labels. Boards are 15.5 mm long, mated by one BM28 pair.")
    k = 60; x0, x1 = 120, 700
    def band(y, th, fill, col, label, sub=""):
        h = max(th * k, 18)
        s.r(x0, y, x1 - x0, h, fill, col, 1.5, 2)
        s.t(x1 + 16, y + h / 2 + 5, label, 13, INK)
        if sub: s.t(x1 + 16, y + h / 2 + 22, sub, 11.5, MUT)
        return y + h
    y = 90
    y_lid = y
    y = band(y, K.LID_T, TO, INK, f"Lid {K.LID_T} (flat underside = seam, y {K.Y_LID_IN})")
    y_led = y
    y = band(y, K.F_GAP, TO, ORG, f"Lid ledge 0.70 + VHB 0.25 = {K.F_GAP:.2f}", "ledge band 0.5 wide, 0.2 in from the board edge; clear of M lid-face parts")
    # lid-face parts on M poking into the ledge zone (SW1 etc)
    y_m = y; y = band(y, 0.8, TG, GRN, "Board M 0.8 (lid face = file B)", "lid face: SW1, wire pads J4 J5 J7 J8; inner face (file F): mic U2 (port through M to the lid), U3, U4")
    y_bm = y
    y = band(y, 0.6, TB, BLU, "BM28 mated gap 0.6", "M parts hang in here (mic U2 port through the lid duct)")
    y_p = y; y = band(y, 0.8, TG, GRN, "Board P 0.8 (file F.Cu = inner face)", "inner: Q1 Q2 (0.37 high); outer: U1 chip, L1 coil")
    y_pe = y
    s.r(x0, y_pe, x1 - x0, 50, PANEL, MUT, 1, 2); s.t(x1 + 16, y_pe + 16, "Floor clearance 0.65 nominal (0.16 worst case), then the tub floor", 13, INK)
    # BM28 pair
    bx = x0 + 70
    s.r(bx, y_bm - 2, 70, 0.6 * k + 4, PANEL, BLU, 2, 2)
    s.t(bx + 35, y_bm + 0.3 * k + 5, "BM28", 12, BLU, "bold", "middle")
    s.t(bx + 90, y_bm + 0.3 * k + 5, "30-pin + 4 power tabs", 11.5, BLU, anc="start")
    # glue post
    px = x0 + 330
    ph = 34
    s.r(px, y_pe + 26, 70, 24, TB, PUR, 2, 2)
    s.r(px + 10, y_pe + 2, 50, 14, PANEL, INK, 1.2, 1)
    s.t(px + 35, y_pe + 13, "U1", 11, INK, "bold", "middle")
    s.t(px - 10, y_pe + 24, "gap (not to scale)", 10.5, MUT, anc="end")
    s.t(px + 85, y_pe + 70, f"Glue post, printed short by {K.POST_PRINT_GAP:.4f}", 12.5, PUR, "bold")
    s.t(px + 85, y_pe + 88, "epoxy dab on the Kapton over U1 fills it: lid -> M -> BM28 -> P -> U1 -> post is one rigid column (ECR-0023 add.2)", 11.5, MUT)
    s.t(px + 85, y_pe + 104, f"post pad {K.POST_W} x {K.POST_W} on U1 top, at board x {K.POST_X}", 11.5, MUT)
    # direction cues
    s.badge(70, y_lid + 20, "A"); s.t(70, y_lid + 50, "lid side", 12, MUT, anc="middle")
    s.badge(70, y_pe + 8, "B"); s.t(70, y_pe + 38, "belly side", 12, MUT, anc="middle")
    s.t(x0, 560, f"Total board stack {K.STACK_T} mm; stack {K.STACK_L} x {K.STACK_H}. The lid carries the stack on VHB; P hangs from M through BM28 and rests on nothing.", 13, INK)
    s.t(x0, 584, "Dock pads and magnets sit under the cell, not in this section: see k4-dock-section.", 13, MUT)
    s.t(x0, 612, "Pinch the pair only at the post: the dab stops lid push (SW1 press) from loading the BM28 contacts.", 13, MUT)
    save(s, "k4-stack-section.svg")

def d_dock():
    s = S(1280, 640, "K4 dock: 4 gold pads + 2 magnets on the belly, under the cell", "dims_k4.py (ECR-0022, option A). [T] = inferred, to be calipered on a head sample.")
    sc = 36; ox, oy = 90, 130
    # panel 1: belly plan, x along pod
    L0, L1 = 18.35, 62.0 + 0  # visible span
    xs = lambda x: ox + (x - K.MAG_X_FRONT + 2.3) * sc
    s.t(ox, 100, "Belly view (x along the pod, front left)", 14, INK, "bold")
    belly_w = 6.4 * 28
    s.r(xs(K.X0 if hasattr(K, "X0") else 18.35), oy, (K.CELL_X0 - 18.35 + 7) * sc, belly_w, PANEL, MUT, 1.5, 12)
    cy = oy + belly_w / 2
    for lbl, mx in (("magnet N52 2.5 x 1.0", K.DOCK_CX - 6.6), ("magnet", K.DOCK_CX + 6.6)):
        s.c(xs(mx), cy, 1.25 * sc, TO, ORG, 2); s.t(xs(mx), cy + 4, "N52", 11, ORG, "bold", "middle")
    names = ["pad 1", "pad 2", "pad 3", "pad 4"]
    for i, px in enumerate(K.PAD_X):
        s.r(xs(px) - K.WIN_W / 2 * sc, cy - K.WIN_H / 2 * sc, K.WIN_W * sc, K.WIN_H * sc, TO, ORG, 1.8, 2)
        s.t(xs(px), cy + K.WIN_H / 2 * sc + 18, ["VBUS", "D+", "D-", "GND"][i], 11.5, INK, anc="middle")
    s.t(xs(K.DOCK_CX), cy - 1.25 * sc - 22, f"pad pitch {K.DOCK_PITCH}, magnet pitch {K.HEAD_MAG_PITCH} [T]", 12, MUT, anc="middle")
    s.t(xs(K.DOCK_CX), oy + belly_w + 24, "net order per k4-dock.yaml option_A_design; D+/D- order set by the head cable [T]", 11, MUT, anc="middle")
    # head outline
    hw_ = 21.2 * sc
    s.r(xs(K.DOCK_CX) - hw_ / 2, cy - 6.86 / 2 * 28, hw_, 6.86 * 28, "none", BLU, 2, 12)
    s.o[-1] = s.o[-1].replace('/>', ' stroke-dasharray="6 4"/>')
    s.t(xs(K.DOCK_CX) - hw_ / 2 + 6, cy - 6.86 / 2 * 28 - 8, "charging head 21.2 x 6.86 (overhangs the 6.4 pod by 0.23 each side)", 12, BLU)
    # panel 2: section at pad plane
    sy = 400; s.t(ox, sy - 20, "Section at a pad (looking along x; belly down)", 14, INK, "bold")
    k2 = 60; cx = 640
    pod_w = 6.4 * k2
    s.r(cx - pod_w / 2, sy, pod_w, 160, PANEL, MUT, 1.5, 10)
    s.r(cx - pod_w / 2 + 14, sy + 6, pod_w - 28, 66, TB, BLU, 1.5, 3); s.t(cx, sy + 44, f"cell {K.CELL_SPEC['T']} (above the pad tab)", 12.5, BLU, anc="middle")
    s.r(cx - 70, sy + 82, 140, 0.8 * k2 * 0.6, TG, GRN, 1.5, 2); s.t(cx + pod_w / 2 + 16, sy + 98, "M tab, 0.6 strip in the wire channel", 12, GRN)
    s.r(cx - K.WIN_W * k2 / 2, sy + 130, K.WIN_W * k2, 30, TO, ORG, 1.8, 2); s.t(cx + pod_w / 2 + 16, sy + 150, f"window {K.WIN_W} x {K.WIN_H}; gold half-hole pad", 12, ORG)
    s.r(cx - 105, sy + 162, 210, 22, TB, BLU, 1.8, 3); s.t(cx + pod_w / 2 + 16, sy + 180, "charging head, pogos touch the pads", 12, BLU)
    s.t(ox, 620, f"Magnets sit in bossed pockets, {K.MAG_SKIN} mm skin, boss top {K.BOSS_TOP} (0.15 under the cell/M edge). Dock centre line = M mid-plane.", 12.5, MUT)
    save(s, "k4-dock-section.svg")

def d_bm28():
    src = (ROOT / "hw/pod/k4/gen.py").read_text()
    body = re.search(r"BM28_PINS = \{(.*?)\n\s*\}?\n?\s*(?:\#.*\n)*?.*?34: \"\+3V0\"\}", src, re.S)
    txt = re.search(r"BM28_PINS = \{(.*?34: \"\+3V0\")\}", src, re.S).group(1)
    pins = {int(a): b for a, b in re.findall(r"(\d+): \"([^\"]+)\"", re.sub(r"#.*", "", txt))}
    cls = lambda n: "gnd" if n == "GND" else "pwr" if n == "+3V0" else "sig"
    col = {"gnd": (PANEL, MUT), "pwr": (TO, RED), "sig": (TB, BLU)}
    s = S(1180, 640, "BM28 30-pin map, checkerboard (reversal-safe) + 4 power tabs", "hw/pod/k4/gen.py BM28_PINS, K4-BM28-REV. Pad n faces pad 31-n; a 180-degree reversed mate pairs n with n+/-15.")
    w, h, x0 = 62, 50, 90
    rows = [("pads 1-15", range(1, 16), 120), ("pads 16-30", range(16, 31), 270)]
    def pad(n, x, y):
        c = cls(pins[n]); f, st = col[c]
        s.r(x, y, w - 6, h, f, st, 1.6, 3); s.t(x + (w - 6) / 2, y + 20, str(n), 13, INK, "bold", "middle"); s.t(x + (w - 6) / 2, y + 38, pins[n].replace("_SENSE", "_S"), 9.5, INK, anc="middle")
    for lbl, rng, y in rows:
        s.t(x0, y - 8, lbl, 12.5, MUT)
        for i, n in enumerate(rng): pad(n, x0 + i * w, y)
    # reversed mate partner row
    s.t(x0, 350, "Reversed mate: what each pad of pads 1-15 touches (pad n+15), and the verdict", 14, INK, "bold")
    ok = 0
    for i, n in enumerate(range(1, 16)):
        m = n + 15; a, b = cls(pins[n]), cls(pins[m])
        verdict = "GND-GND" if a == b == "gnd" else "+3V0-+3V0" if a == b == "pwr" else "sig-GND" if {a, b} == {"sig", "gnd"} else "BAD"
        good = verdict != "BAD"; ok += good
        x = x0 + i * w
        s.r(x, 366, w - 6, 56, TG if good else TO, GRN if good else RED, 1.4, 3)
        s.t(x + (w - 6) / 2, 384, f"{n}/{m}", 11.5, INK, "bold", "middle"); s.t(x + (w - 6) / 2, 402, verdict, 9.5, INK, anc="middle"); s.t(x + (w - 6) / 2, 416, "ok" if good else "SHORT", 10, GRN if good else RED, anc="middle")
    # tabs
    s.t(x0, 470, "Power tabs 31-34 (5 A, 30 mohm max [T Hirose catalog]): all +3V0, pair with each other when reversed", 13, INK)
    for i in range(4):
        s.r(x0 + i * 120, 482, 100, 30, TO, RED, 1.6, 3); s.t(x0 + i * 120 + 50, 502, f"tab {31 + i}  +3V0", 12, INK, anc="middle")
    s.r(80, 540, 14, 14, *col["sig"][:1], col["sig"][1]); s.t(100, 552, "signal (GND on both row neighbours and across)", 12, INK)
    s.r(440, 540, 14, 14, col["pwr"][0], col["pwr"][1]); s.t(460, 552, "+3V0 (15/30 self-mate)", 12, INK)
    s.r(700, 540, 14, 14, col["gnd"][0], col["gnd"][1]); s.t(720, 552, "GND", 12, INK)
    s.t(x0, 592, f"Check: {ok}/15 mate pairs safe when reversed (signal-GND, +3V0-+3V0, GND-GND only; never a supply against GND, never a supply into a GPIO).", 13, INK if ok == 15 else RED)
    save(s, "k4-bm28-map.svg")
    return ok

if __name__ == "__main__":
    d_stack(); d_dock(); print("bm28 ok pairs", d_bm28())
