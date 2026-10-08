"""Dimension marks on the side render. python3 tools/render_k4/annotate_side.py OUTDIR (reads side_px.json from stack_scene.py)"""
import json, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
O = Path(sys.argv[1]); d = json.load(open(O / "side_px.json")); im = Image.open(O / "stack_side_section.png").convert("RGB"); dr = ImageDraw.Draw(im)
try: f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 30)
except Exception: f = ImageFont.load_default()
C = (120, 220, 255)
def bracket(x, y0, y1, text, side=1):
    dr.line([(x, y0), (x, y1)], fill=C, width=3)
    for y in (y0, y1): dr.line([(x - 14, y), (x + 14, y)], fill=C, width=3)
    tw = dr.textlength(text, font=f)
    dr.text((x + 24 if side > 0 else x - 24 - tw, (y0 + y1) / 2 - 16), text, fill=C, font=f)
bracket(1950, d["top"], d["bottom"], "", -1)
dr.text((1620, d["top"] - 52), f"{d['h']:.2f} mm overall", fill=C, font=f)
bracket(1650, d["pinner"], d["mtop"], "0.60 mated gap", 1)
Wd = d["W"]
ppm = d["ppm"]
dr.text((60, 8), "Side view. Boards 0.79 mm each, mated gap 0.60 mm", fill=(200, 205, 215), font=f)
im.save(O / "stack_side_view_dims.png"); print("annotated")
