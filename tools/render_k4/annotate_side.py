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
zhi, zlo = d["zhi"], d["zlo"]
pt, mb = 0.761 + 0.6, -0.79
bracket(1950, d["top"], d["bottom"], "", -1)
dr.text((1500, d["top"] - 52), f"{d['h']:.2f} mm overall (render models)", fill=C, font=f)
bracket(1650, d["ptop"], d["pinner"], f"P board 0.8", 1)
bracket(1650, d["pinner"], d["mtop"], "0.6 mated gap", 1)
bracket(1650, d["mtop"], d["mbot"], "M board 0.8", 1)
bracket(1450, d["top"], d["ptop"], f"P outer parts {zhi - pt:.2f}", -1)
bracket(1450, d["mbot"], d["bottom"], f"M lid parts {mb - zlo:.2f}", -1)
dr.text((60, 8), "Side view. Boards 0.8 + gap 0.6 + 0.8 = 2.2 mm bare stack; parts add the outer-face heights", fill=(200, 205, 215), font=f)
dr.text((60, 48), f"{d['h']:.2f} = 2.2 + {zhi - pt:.2f} + {mb - zlo:.2f}. Datasheet max (k4_heights.py): P outer L1 1.0, M lid C21 0.7 -> 3.9", fill=(200, 205, 215), font=f)
im.save(O / "stack_side_view_dims.png"); print("annotated")
