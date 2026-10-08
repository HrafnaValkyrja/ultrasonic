"""K4 review snapshots of the boards -> docs/diagrams/k4-review/ (PNGs gitignored).
  systemd-run --user --scope --quiet -p MemoryMax=4G -p MemorySwapMax=0 python3 hw/pod/k4/review_boards.py
Makes: board renders (top/bottom P,M + stacked iso), copper layer plots (dark), BOM tables, STEPs for the pod render.
"""
import csv, subprocess, io, os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = ROOT / "docs/diagrams/k4-review"
TMP = ROOT / "hw/mech/out/k4review"
OUT.mkdir(parents=True, exist_ok=True); TMP.mkdir(parents=True, exist_ok=True)
BG = (20, 22, 27)
F = lambda n, b=False: ImageFont.truetype(f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'-Bold' if b else ''}.ttf", n)
def run(*a): subprocess.run(list(map(str, a)), check=True, capture_output=True)

def nolabels(b):
    """Copy of the board with reference/value text hidden (3D render only; the source file is untouched)."""
    import pcbnew
    bd = pcbnew.LoadBoard(str(HERE / f"routed_{b}.kicad_pcb"))
    for fp in bd.GetFootprints():
        fp.Reference().SetVisible(False); fp.Value().SetVisible(False)
    q = TMP / f"nl_{b}.kicad_pcb"; bd.Save(str(q)); return q

def dark(p):
    im = Image.open(p).convert("RGBA"); bg = Image.new("RGBA", im.size, BG + (255,))
    Image.alpha_composite(bg, im).convert("RGB").save(p, optimize=True)

def renders():
    for b in "PM":
        pcb = nolabels(b)
        for side in ("top", "bottom"):
            run("kicad-cli", "pcb", "render", "-o", OUT / f"board_{b}_{side}.png", "--side", side, "--quality", "high",
                "--background", "transparent", "--width", 2000, "--height", 1500, "--zoom", 0.9, pcb)
            dark(OUT / f"board_{b}_{side}.png")
        run("kicad-cli", "pcb", "render", "-o", OUT / f"board_{b}_iso.png", "--quality", "high", "--background", "transparent",
            "--width", 2000, "--height", 1500, "--rotate", "-45,0,25", "--perspective", pcb)
        dark(OUT / f"board_{b}_iso.png")
        run("kicad-cli", "pcb", "export", "step", "--subst-models", "--force", "-o", TMP / f"{b}.step", HERE / f"routed_{b}.kicad_pcb")

def layers():
    L = ["F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu"]
    for b in "PM":
        pcb = HERE / f"routed_{b}.kicad_pcb"
        tiles = []
        for l in L:
            svg = TMP / f"{b}_{l}.svg"
            run("kicad-cli", "pcb", "export", "svg", "-o", svg, "-l", f"{l},Edge.Cuts", "--mode-single", "--page-size-mode", 2,
                "--exclude-drawing-sheet", "--theme", "KiCad Classic", pcb)
            png = TMP / f"{b}_{l}.png"
            run("rsvg-convert", "-w", 1200, "-b", "black", "-o", png, svg)
            tiles.append(Image.open(png).convert("RGB"))
        w, h = tiles[0].size
        cv = Image.new("RGB", (w * 2, (h + 70) * 3 + 90), BG)
        d = ImageDraw.Draw(cv); d.text((20, 15), f"K4 board {b}: copper layers (kicad-cli, 6L)", fill=(235, 235, 240), font=F(40, True))
        for i, (l, t) in enumerate(zip(L, tiles)):
            x, y = (i % 2) * w, 90 + (i // 2) * (h + 70)
            d.text((x + 20, y + 10), l, fill=(120, 200, 255), font=F(34))
            cv.paste(t, (x, y + 60))
        cv.save(OUT / f"layers_{b}.png", optimize=True)

def bom():
    cv = Image.new("RGB", (2200, 1700), BG); d = ImageDraw.Draw(cv); y0 = 20
    for b in "PM":
        rows = list(csv.reader(open(HERE / f"bom_jlc_{b}.csv")))
        d.text((30, y0), f"K4 board {b}: JLC BOM ({len(rows)-1} lines)", fill=(235, 235, 240), font=F(36, True)); y0 += 60
        cols = [0, 380, 880, 1500, 1780, 1900]
        for r_i, r in enumerate(rows):
            for c, x in zip(r, cols):
                d.text((30 + x, y0), c[:44], fill=(120, 200, 255) if r_i == 0 else (215, 215, 220), font=F(24, r_i == 0))
            y0 += 33
        y0 += 40
    cv.crop((0, 0, 2200, y0)).save(OUT / "bom.png", optimize=True)

if __name__ == "__main__":
    renders(); layers(); bom()
