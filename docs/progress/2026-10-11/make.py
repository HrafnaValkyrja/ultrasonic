"""Progress page 2026-10-11 (one composite, true black). Run: systemd-run --user --scope -p MemoryMax=3G python3 make.py"""
from PIL import Image, ImageDraw, ImageFont
import os
R = os.path.join(os.path.dirname(__file__), "..", "..", "..")
BLK, PANEL, INK, DIM = (0,0,0), (20,21,24), (232,232,229), (164,169,176)
GRN, AMB, BLU, RED = (82,211,158), (242,140,63), (91,159,242), (255,109,108)
F = "/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf"
def f(s, b=False): return ImageFont.truetype(F % ("-Bold" if b else ""), s)
W, H = 2400, 1700
im = Image.new("RGB", (W, H), BLK); d = ImageDraw.Draw(im)
def T(x, y, s, sz=26, c=INK, b=False): d.text((x, y), s, font=f(sz, b), fill=c)
def card(x, y, w, h): d.rounded_rectangle((x, y, x+w, y+h), 16, fill=PANEL, outline=(42,44,49), width=2)
T(60, 36, "Where the project stands, 11 Oct 2026", 54, INK, True)
T(60, 108, "Everything below is SIMULATED or CHECKED ON PAPER. Nothing has been measured on hardware yet.", 28, AMB)
# left: pod render
card(60, 170, 1000, 860)
pod = Image.open(R+"/docs/diagrams/k4-review/pod-iso.png").convert("RGB").crop((0, 150, 1120, 800)).resize((940, 546))
im.paste(pod, (90, 200))
T(90, 770, "The pod (K4): 6.4 thick, 49.8 long, 15.25 tall, in mm", 30, INK, True)
T(90, 815, "Simulated geometry check: it clears every part and", 24, DIM)
T(90, 850, "tolerance (0 clashes, 37 part heights pass).", 24, DIM)
T(90, 905, "Still open: the 6-layer 0.8 mm board stack at the fab,", 24, AMB)
T(90, 940, "and the epoxy post that holds the lid.", 24, AMB)
# right: four proofs
T(1100, 180, "The four proofs (paper and simulation)", 36, INK, True)
rows = [("Electrical", AMB, "Boards connect, rules clean.", "Full-drive peak 326 mA is over the cell's 260 mA.", "Firmware cap of 208 mA passes (costs 3.6 dB of loudness)."),
        ("Thermal", GRN, "Charger 52 C (limit 100). Cell 43.5 C docked (limit 45).", "Worn and charging runs too warm: charge on the dock only,", "never on the head. Awake use is about 39 C at the shell."),
        ("Physical", GRN, "Everything fits with room; no part touches another.", "", "Open: fab stack and epoxy post (left)."),
        ("Buildable", GRN, "You can build it by hand. Two steps are hard", "(fine wires to pads) and each has a cheap fix.", "JLC places every small part; you do wires and closing.")]
y = 240
for n, c, a, b2, c2 in rows:
    card(1100, y, 1240, 190)
    d.ellipse((1125, y+25, 1155, y+55), fill=c)
    T(1175, y+18, n, 32, c, True)
    T(1175, y+68, a, 25); T(1175, y+101, b2, 25); T(1175, y+134, c2, 25, DIM)
    y += 205
# bottom row
yb = 1060
card(60, yb, 760, 590)
T(90, yb+20, "Loudness we propose: A + Loud mode", 30, BLU, True)
lo = [("Quiet street, day street", "every bat call heard", GRN), ("Heavy traffic, cafe, car", "most heard, faintest missed", BLU),
      ("Battery, calls all day", "8.8 h (12 h without Loud)", INK), ("Battery, quiet dusk", "26 h", INK),
      ("Battery, loud music", "4 h", RED), ("Weight at the ear", "1.2 g", INK)]
yy = yb+85
for a, b2, c in lo:
    T(90, yy, a, 24, DIM); T(90, yy+30, b2, 28, c, True); yy += 78
card(850, yb, 740, 590)
T(880, yb+20, "Firmware (simulated on a PC)", 30, BLU, True)
fw = [("Fits the chip", "58 KB flash, 31 KB RAM + 8 KB stack", GRN),
      ("Tests", "All committed test programs pass", GRN),
      ("Speed", "CPU fixed: 112 MHz plan (78% load), done", GRN),
      ("Not yet", "Real chip, real audio: none", RED)]
yy = yb+85
for a, b2, c in fw:
    if a: T(880, yy, a, 24, DIM); yy += 30
    T(880, yy, b2, 26, c, True); yy += 52 if a else 40
card(1620, yb, 720, 590)
T(1650, yb+20, "Bench day: ready, not done", 30, BLU, True)
for i, s in enumerate(["Pen test: does the pod front", "  stand in your vision line?", "Arm caliper: real glasses arm size",
                       "Body photos for the pod fit", "Listening test on the Shokz", "  (tragus, real loudness)", "Only needs what you already own"]):
    T(1650, yb+85+i*40, s, 25, INK if not s.startswith("  ") else DIM)
T(1650, yb+395, "Still unknown", 30, RED, True)
for i, s in enumerate(["Does the pod block your view?", "How loud it really is on the tragus", "Anything measured on hardware"]):
    T(1650, yb+445+i*40, s, 25, INK)
T(60, H-36, "Sources: proofs 2026-10-08; loudness 2026-10-07; firmware and CPU 2026-10-11.", 20, DIM)
im.save(os.path.join(os.path.dirname(__file__), "progress.png"))
