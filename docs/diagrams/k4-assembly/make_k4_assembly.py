#!/usr/bin/env python3
"""K4 assembly step diagrams -> docs/diagrams/k4-assembly/*.svg (light palette; render.sh darkens). Numbers from hw/mech/dims_k4.py and hw/pod/k4/placement_*.yaml.
    python3 docs/diagrams/k4-assembly/make_k4_assembly.py && for f in docs/diagrams/k4-assembly/*.svg; do systemd-run --user --scope --quiet -p MemoryMax=4G -p MemorySwapMax=0 docs/diagrams/render.sh $f; done
"""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "hw" / "mech"))
import dims_k4 as K

BG, PANEL, INK, MUT = "#fbfaf7", "#ffffff", "#1f2328", "#57606a"
GRN, BLU, ORG, RED, PUR = "#1a7a55", "#2a78d6", "#b8520a", "#e34948", "#4a3aa7"
TG, TB, TO = "#e8f3ec", "#e8f0fb", "#fff4ea"


class S:
    def __init__(s, w, h, title, sub=""):
        s.w, s.h, s.o = w, h, []
        s.o.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" font-family="DejaVu Sans, sans-serif">')
        s.o.append(f'<rect width="{w}" height="{h}" fill="{BG}"/>')
        s.t(24, 36, title, 22, INK, "bold")
        if sub: s.t(24, 58, sub, 13, MUT)
    def t(s, x, y, txt, sz=13, c=INK, wt="normal", anc="start"):
        s.o.append(f'<text x="{x}" y="{y}" font-size="{sz}" fill="{c}" font-weight="{wt}" text-anchor="{anc}">{txt}</text>')
    def r(s, x, y, w, h, fill=PANEL, st=INK, sw=1.5, rx=4):
        s.o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{st}" stroke-width="{sw}"/>')
    def l(s, x1, y1, x2, y2, c=INK, sw=2, dash=""):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        s.o.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{c}" stroke-width="{sw}"{d}/>')
    def c(s, x, y, rad, fill=PANEL, st=INK, sw=1.5):
        s.o.append(f'<circle cx="{x}" cy="{y}" r="{rad}" fill="{fill}" stroke="{st}" stroke-width="{sw}"/>')
    def badge(s, x, y, n, col=ORG):
        s.c(x, y, 13, col, col); s.t(x, y + 5, str(n), 14, "#ffffff", "bold", "middle")
    def arrow(s, x1, y1, x2, y2, c=INK):
        s.l(x1, y1, x2, y2, c, 2.5)
        import math
        a = math.atan2(y2 - y1, x2 - x1)
        p = [(x2, y2), (x2 - 11 * math.cos(a - .4), y2 - 11 * math.sin(a - .4)), (x2 - 11 * math.cos(a + .4), y2 - 11 * math.sin(a + .4))]
        s.o.append(f'<polygon points="{" ".join(f"{a_:.1f},{b_:.1f}" for a_, b_ in p)}" fill="{c}"/>')
    def save(s, name):
        (HERE / name).write_text("\n".join(s.o + ["</svg>"]))


# ---------- 01 stack section
def d01():
    s = S(1320, 520, "K4 stack, side section (y up toward the lid)", "From dims_k4.py. Layer thickness x 70 for readability; mm in the labels.")
    k = 70; x0, x1 = 130, 560
    layers = [("Lid, flat", K.LID_T, "#ddd4b4", INK), ("Ledge 0.70 + VHB 0.25 on the ledge tip", K.F_GAP, TO, ORG),
              ("Board M 0.8: lid face has SW1 + wire pads J5 J4 J7 J8", .8, "#e8f3ec", GRN),
              ("BM28 gap 0.6: M parts hang in here (mic U2, U3, U4)", .6, TB, BLU),
              ("Board P 0.8: inner Q1 Q2; outer U1 chip, L1 coil", .8, "#e8f3ec", GRN),
              ("Floor clearance 0.65 (0.16 worst case), then tub floor", .65, PANEL, MUT)]
    y = 90
    for name, th, fill, col in layers:
        hh = max(th * k, 14) if name.startswith(("Lid", "Floor")) else th * k
        s.r(x0, y, x1 - x0, hh, fill, col, 1.5, 2)
        s.t(x1 + 14, y + min(hh, 30) / 2 + 5, f"{name}", 12.5, INK)
        y += hh
    s.t(x0, y + 40, "Pods are glued stack-to-lid. The lid carries the stack (hangs from it); the tub holds the cell.", 13, INK)
    s.t(x0, y + 62, "Seam (tub | lid) is at the flat lid underside, y 9.7. Tongue 0.35 high in the tub, groove in the lid.", 13, MUT)
    s.badge(70, 120, "A"); s.t(88, 150, "lid side", 12, MUT, anc="middle")
    s.badge(70, y - 20, "B"); s.t(88, y + 8, "belly side", 12, MUT, anc="middle")
    s.t(x0, y + 100, f"Stack {K.STACK_L} x {K.STACK_H} mm, total thickness {K.STACK_T} mm.  Cell {K.CELL_SPEC['T']} thick, front end at pod x {K.CELL_X0}.", 13, INK)
    s.save("01-stack-section.svg")


# ---------- 02 pad map (plan of M lid face and P)
def plan_board(s, ox, oy, sc, label, pads, parts, col):
    L, W = K.STACK_L, 12.0
    s.r(ox, oy, L * sc, W * sc, PANEL, col, 2, 3)
    s.t(ox + 4, oy - 8, label, 14, col, "bold")
    for n, bx, by, c2, side in pads:
        s.c(ox + bx * sc, oy + by * sc, 8, c2, INK, 1.2)
        s.t(ox + bx * sc + (60 if "J2" in n else -30), oy + by * sc + (26 if "J2" in n else -12), n, 11, INK, "bold", "middle")
    for n, bx, by, w_, h_ in parts:
        s.r(ox + (bx - w_ / 2) * sc, oy + (by - h_ / 2) * sc, w_ * sc, h_ * sc, "#f3f1ea", MUT, 1, 2)
        s.t(ox + bx * sc, oy + by * sc + 4, n, 10.5, MUT, anc="middle")


def d02():
    s = S(1000, 600, "Where every wire lands (plan view, board file coordinates)", "Cell, LED and exciter joints. mm from the board's front (mic) edge. Pads read from placement_M.yaml / placement_P.yaml.")
    sc = 28
    plan_board(s, 40, 120, sc, "Board M, LID face (looking at the pads)",
               [("J5 BAT+", 10.55, 10.9, RED, ""), ("J4 GND", 10.55, 8.5, "#a4a9b0", ""), ("J8 LED-", 12.68, 6.98, BLU, ""), ("J7 LED+", 3.78, 8.68, ORG, ""), ("J9 NTC", 1.48, 1.18, "#fbfaf7", "")],
               [("SW1", 5.3, 6.0, 3.0, 2.6), ("U2 port", 1.75, 5.25, 1.0, 1.0)], GRN)
    plan_board(s, 40, 440 - 100 + 100, sc, "", [], [], PANEL) if False else None
    plan_board(s, 540, 120, sc, "Board P, as drawn in its file",
               [("J1 OUT_A", 2.28, 3.58, ORG, ""), ("J2 OUT_B inner face", 1.68, 3.58 + 0.0, RED, "")],
               [("U1 chip", 9.8, 4.8, 7.0, 7.0), ("L1", 4.53, 2.73, 2.0, 1.6)], BLU)
    s.t(40, 500 + 0, "Colour key:  red = battery plus   grey = ground   orange = exciter OUT_A / LED plus   blue = LED minus / second exciter wire.", 13, INK)
    s.t(40, 524, "J9 NTC stays EMPTY: the thermistor RT1 is on M (the charger reads one or the other, never both).", 13, MUT)
    s.t(40, 548, "J2 sits on P's INNER face, which ends up inside the 0.6 mm gap. Solder it before P is mated, and see 'Open items' in the guide.", 13, RED)
    s.save("02-pad-map.svg")


# ---------- 03 order of operations
def d03():
    steps = ["Print + check parts", "Solder joints to M", "Solder joints to P", "Mate P to M", "Bench power-up", "Dock + button test",
             "Cell in tub", "Stack on lid", "Close + seal", "First charge"]
    s = S(1000, 520, "K4 order of operations (hand build)", "Each box = one section of the guide. Red gate = do not go on until its test passes.")
    cols = [GRN, ORG, ORG, ORG, RED, RED, BLU, BLU, BLU, RED]
    for i, n in enumerate(steps):
        x = 40 + (i % 5) * 190; y = 100 + (i // 5) * 170
        s.r(x, y, 170, 100, TG if cols[i] == GRN else (TO if cols[i] == ORG else (TB if cols[i] == BLU else "#fff4ea")), cols[i], 2.5, 6)
        s.badge(x + 20, y + 20, i + 1, cols[i]); s.t(x + 85, y + 62, n, 13.5, INK, "bold", "middle")
        if i % 5 < 4: s.arrow(x + 172, y + 50, x + 188, y + 50)
    s.arrow(890, 205, 130, 275, MUT) if False else None
    s.t(40, 460, "Why M and P get their wires BEFORE they are mated:", 14, INK, "bold")
    s.t(40, 482, "P has no solder window over M, and P's J2 lands inside the 0.6 mm gap. After mating you cannot reach those pads.", 13, MUT)
    s.save("03-order.svg")


# ---------- 04 wiring routes plan
def d04():
    s = S(1000, 560, "Wire routes in the pod (plan, looking at the lid side)", "Model lengths from dims_k4.wire_lengths(); cut each wire 5 mm long and trim at the dry fit.")
    sc = 13.0; ox = 60; oy = 120
    X0, X1 = K.X0, K.X1
    s.r(ox, oy, (X1 - X0) * sc, 14.8 * sc, PANEL, MUT, 2, 14)
    def px(x): return ox + (x - X0) * sc
    s.r(px(K.STACK_X0), oy + 1.4 * sc, K.STACK_L * sc, 12 * sc, TG, GRN, 2, 2); s.t(px(K.STACK_X0) + 5, oy + 1.4 * sc + 16, "stack M+P", 12, GRN, "bold")
    s.r(px(K.CELL_X0), oy + 1.6 * sc, 31 * sc, 12.7 * sc, TB, BLU, 2, 4); s.t(px(K.CELL_X0) + 100, oy + 7 * sc, "cell 130 mAh (in tub)", 13, BLU, "bold")
    s.r(px(K.CELL_X1 + 0.2), oy + 1.4 * sc, (K.CAV['x1'] - K.CELL_X1) * sc, 12 * sc, TO, ORG, 1.5, 2); s.t(px(K.CELL_X1) + 4, oy + 11.5 * sc, "dead zone", 11, ORG)
    yb = oy + 7.4 * sc
    s.l(px(K.STACK_X1), yb, px(K.CELL_X0), yb, RED, 3); s.t(px(K.STACK_X1) + 4, yb - 6, "BAT+ / GND 8 mm", 11, RED)
    s.l(px(K.STACK_X1), yb + 10, px(K.CELL_X1 + 1), yb + 10, ORG, 2.5, "6 3"); s.t(px(K.STACK_X1) + 160, yb + 34, "4 arm litz wires run UNDER the cell, ~50-60 mm", 11.5, ORG)
    s.l(px(K.CELL_X1 + 1), yb + 10, px(66.2), oy + 5.8 * sc, ORG, 2.5, "6 3")
    s.c(px(66.2), oy + 5.8 * sc, 7, PANEL, ORG); s.t(px(66.2) - 10, oy + 5.8 * sc - 14, "heel exit", 11.5, ORG, anc="end")
    s.t(60, 400, "1. Cell leads go forward-to-back: M lid-face pads J5/J4 -> past the stack rear edge -> up to the cell's front lead (8 mm).", 13.5)
    s.t(60, 426, "2. Arm wires: pads J1 J2 J7 J8 -> stack rear -> drop into the 0.9 mm lane under the cell -> dead zone -> heel exit.", 13.5)
    s.t(60, 452, "3. The route under the cell is a drawing, not a proven path (K4 arm route is a placeholder in the repo). Dry-fit with dummies first.", 13.5, RED)
    s.t(60, 478, "Wire OD 0.21 each, bundle 0.51, minimum bend radius 0.5 mm.", 13.5, MUT)
    s.save("04-wire-routes.svg")


# ---------- 05 button + mic duct
def d05():
    s = S(980, 480, "Lid features: mic duct and button puck (section through the lid)", "Numbers from dims_k4.py. The mic hole in M is 0.65; the lid bore is 1.0.")
    sc = 90; ox = 80; oy = 100
    s.r(ox, oy, 760, K.LID_T * sc * 0.9, "#ddd4b4", INK, 1.5, 2); s.t(ox + 5, oy - 8, "lid (1.0 flat)", 12, MUT)
    s.r(ox, oy + 90, 760, 28, TO, ORG, 1.5, 2); s.t(ox + 770, oy + 108, "ledge 0.70 + VHB 0.25", 11.5, ORG)
    s.r(ox, oy + 118, 760, 28, TG, GRN, 1.5, 2); s.t(ox + 770, oy + 136, "board M", 11.5, GRN)
    mx = ox + 120
    s.r(mx - 8, oy, 16, 90, "#fbfaf7", RED, 2, 1); s.t(mx, oy + 170, "mic duct", 12, RED, "bold", "middle"); s.t(mx, oy + 188, "D1.0 bore + VHB ring + D0.65 hole", 11, MUT, "middle")
    s.r(mx - 16, oy + 146, 32, 22, "#ece5cd", INK, 1.5, 2); s.t(mx, oy + 162, "U2", 11, INK, anc="middle")
    bx = ox + 430
    s.r(bx - 20, oy + 4, 40, 86, "#fbfaf7", BLU, 2, 1); s.t(bx, oy + 170, "puck (kit 1.03-1.23)", 12, BLU, "bold", "middle"); s.t(bx, oy + 188, "chosen length ~1.13, under a 0.1 silicone skin", 11, MUT, "middle")
    s.r(bx - 14, oy + 146, 28, 18, "#ece5cd", INK, 1.5, 2); s.t(bx, oy + 160, "SW1", 11, INK, anc="middle")
    s.t(80, 340, "Mic: slide a pin gauge through the lid bore, VHB hole and M's hole while the VHB is pressed. Pull the pin last.", 13.5)
    s.t(80, 366, "Button: measure depth with the skin off, pick the puck, test 10 presses unbonded, then bond the skin.", 13.5)
    s.t(80, 392, "Mesh in the hex seat (R1.9 x 0.3 deep): hydrophobic open mesh, product not chosen yet.", 13.5, RED)
    s.save("05-lid-features.svg")


# ---------- 06 first charge setup
def d06():
    s = S(980, 520, "First charge: bench setup", "Supervised, on a hard non-burning surface, with a log. Stop rule is on the right.")
    s.r(40, 100, 560, 330, "#fff4ea", RED, 2.5, 8); s.t(60, 128, "Fire-safe LiPo bag, open flap, on a ceramic tile", 14, RED, "bold")
    s.r(120, 190, 280, 150, TG, GRN, 2, 6); s.t(260, 270, "Pod (tub + stack,", 13, GRN, "bold", "middle"); s.t(260, 290, "lid taped, NOT bonded)", 13, GRN, "bold", "middle")
    s.c(160, 360, 12, RED, RED); s.t(185, 365, "thermocouple on the cell", 12, INK)
    s.l(160, 348, 190, 300, RED, 2)
    s.r(420, 220, 150, 60, TB, BLU, 2, 4); s.t(495, 255, "dock head + USB", 12.5, BLU, "bold", "middle")
    s.arrow(420, 250, 400, 250, BLU)
    s.t(640, 120, "Stop rules (E6, ECR-0009)", 16, INK, "bold")
    for i, tx in enumerate(["Cell above 45 C: unplug, wait, find why.", "Cell swells, hisses, smells sweet: unplug, bag shut, outdoors.", "Charge current looks wrong (meter in line): stop.", "Never leave it alone. Log every 5 minutes."]):
        s.t(640, 160 + i * 52, f"{i+1}.", 15, RED, "bold"); s.t(662, 160 + i * 52, tx, 13, INK)
    s.t(40, 470, "Log columns: time, cell temp, VBAT (meter), USB current, LED state. Expect charge to end at VBATREG 4.20 V.", 13, MUT)
    s.save("06-first-charge.svg")


# ---------- 07 reopen + mirror
def d07():
    s = S(1000, 520, "Left pod is the mirror of the right pod", "Same two boards, same parts. The shell is mirrored; off-centre things flip.")
    for j, (name, col, flip) in enumerate([("RIGHT pod (CAD as drawn)", GRN, False), ("LEFT pod (mirror shell)", BLU, True)]):
        ox = 40 + j * 480; oy = 110
        s.r(ox, oy, 420, 200, PANEL, col, 2.5, 20); s.t(ox + 10, oy - 10, name, 15, col, "bold")
        s.l(ox + 10, oy + 100, ox + 410, oy + 100, MUT, 1.5, "6 4"); s.t(ox + 415, oy + 104, "centre line", 10.5, MUT, anc="end")
        s.r(ox + 40, oy + 40, 130, 120, TG, GRN, 2, 3)
        for nm, dz, cc in [("J5", -40 if not flip else 40, RED), ("J7", -20 if not flip else 20, ORG), ("J8", 25 if not flip else -25, BLU)]:
            s.c(ox + 150, oy + 100 + dz, 6, cc, INK, 1); s.t(ox + 136, oy + 104 + dz, nm, 11, INK, anc="end")
        s.c(ox + 70, oy + 100, 6, "#fbfaf7", RED, 2); s.t(ox + 70, oy + 125, "mic", 11, RED, anc="middle")
        s.c(ox + 110, oy + 100, 6, "#fbfaf7", BLU, 2); s.t(ox + 110, oy + 125, "SW1", 11, BLU, anc="middle")
    s.t(40, 350, "On the centre line (no change): mic, SW1, BM28.", 14, INK, "bold")
    s.t(40, 376, "Flips up/down: J5 J4 J7 J8 J1 J2 order, arm wire order at the heel, the dock pad order is along x so it stays.", 14, INK)
    s.t(40, 402, "Print the mirrored tub and lid. Re-do the wire dry fit: the repo's left-pod wire route is NOT checked for K4.", 14, RED)
    s.t(40, 428, "Same dock head: the head's 2 magnets key the same way; just fit the magnets as the right pod (check with the compass).", 13, MUT)
    s.save("07-mirror.svg")


for f in (d01, d02, d03, d04, d05, d06, d07): f()
print("ok")
