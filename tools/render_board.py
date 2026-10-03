"""Photo-style 3D renders of a pod board, in a chosen solder-mask colour, on the dark chat background.

    source tools/env.sh && python3 tools/render_board.py [board.kicad_pcb] [--out DIR] [--masks Green,Black,...]
        [--views top,bottom,iso] [--grid]

Renders a scratch copy, never the board itself: the copy gets (a) 3D model paths that resolve here (KiCad's library
models live in a user cache, ~/.cache/ultrasonic/kicad3d, fetched from gitlab.com/kicad/libraries/kicad-packages3D,
CC-BY-SA 4.0 + design exception, see SOURCE.md there; lcsc models are made absolute), and (b) a 4-layer 0.8 mm stackup
block with the mask colour and an ENIG finish, so `--use-board-stackup-colors` shows the board as ordered.
Each kicad-cli call runs inside a 3 GB memory fence (~0.45 GB, ~6 s each at 2400 px, measured 2026-10-02).
--grid also writes masks.png: the top view in every colour, side by side, one scale.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parents[1]
CACHE = Path.home() / ".cache/ultrasonic/kicad3d"
SUBST = {   # library footprint model names with no file of that name in kicad-packages3D; same body, other variant
    "QFN-48-1EP_7x7mm_P0.5mm_EP5.6x5.6mm.step": "QFN-48-1EP_7x7mm_P0.5mm_EP5.15x5.15mm.step",
    "Knowles_LGA-5_3.5x2.65mm.step": "Knowles_SPH0645LM4H-6_3.5x2.65mm.step",
}
SILK_ON = {"White": "Black"}        # white mask takes black legend
BG = (20, 21, 24)                   # #141518, render.sh dark background
BG_FOR = {"Black": (58, 61, 68)}    # a black board vanishes on the dark page: lift its backdrop
VIEWS = {"top": ["--side", "top"], "bottom": ["--side", "bottom"],
         "iso": ["--side", "top", "--rotate", "-38,0,-22", "--perspective"]}


def stackup(mask: str) -> str:
    silk = SILK_ON.get(mask, "White")
    lay = lambda name, typ, extra="": f'(layer "{name}" (type "{typ}") {extra})'  # noqa: E731
    return ("(stackup "
            + lay("F.SilkS", "Top Silk Screen", f'(color "{silk}")') + lay("F.Paste", "Top Solder Paste")
            + lay("F.Mask", "Top Solder Mask", f'(color "{mask}") (thickness 0.01)') + lay("F.Cu", "copper", "(thickness 0.035)")
            + lay("dielectric 1", "prepreg", '(thickness 0.1) (material "FR4") (epsilon_r 4.5) (loss_tangent 0.02)')
            + lay("In1.Cu", "copper", "(thickness 0.0152)")
            + lay("dielectric 2", "core", '(thickness 0.45) (material "FR4") (epsilon_r 4.5) (loss_tangent 0.02)')
            + lay("In2.Cu", "copper", "(thickness 0.0152)")
            + lay("dielectric 3", "prepreg", '(thickness 0.1) (material "FR4") (epsilon_r 4.5) (loss_tangent 0.02)')
            + lay("B.Cu", "copper", "(thickness 0.035)")
            + lay("B.Mask", "Bottom Solder Mask", f'(color "{mask}") (thickness 0.01)') + lay("B.Paste", "Bottom Solder Paste")
            + lay("B.SilkS", "Bottom Silk Screen", f'(color "{silk}")')
            + '(copper_finish "ENIG") (dielectric_constraints no))')


def scratch_copy(board: Path, mask: str, tmp: Path) -> Path:
    s = board.read_text()
    for a, b in SUBST.items():
        s = s.replace(a, b)
    s = re.sub(r'\(model "hw/', f'(model "{REPO}/hw/', s)
    s = re.sub(r"\(stackup.*?\(dielectric_constraints (?:yes|no)\)\s*\)", "", s, flags=re.S)
    s = s.replace("(setup", "(setup " + stackup(mask), 1)
    out = tmp / f"{board.stem}_{mask.replace(' ', '_')}.kicad_pcb"
    out.write_text(s)
    pro = board.with_suffix(".kicad_pro")
    if pro.exists():
        out.with_suffix(".kicad_pro").write_text(pro.read_text())
    return out


def render(pcb: Path, view: str, png: Path, zoom: float):
    env = dict(os.environ, KICAD10_3DMODEL_DIR=str(CACHE))
    cmd = ["systemd-run", "--user", "--scope", "--quiet", "-p", "MemoryMax=3G", "-p", "MemorySwapMax=0",
           "kicad-cli", "pcb", "render", "--quality", "high", "--use-board-stackup-colors", "--background", "transparent",
           "--width", "2400", "--height", "1200", "--zoom", str(zoom), *VIEWS[view], "-o", str(png), str(pcb)]
    subprocess.run(cmd, check=True, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def on_dark(png: Path, pad: int = 40, bg=BG) -> Image.Image:
    im = Image.open(png).convert("RGBA")
    box = im.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox() or (0, 0, *im.size)
    im = im.crop((max(box[0] - pad, 0), max(box[1] - pad, 0), min(box[2] + pad, im.width), min(box[3] + pad, im.height)))
    bg = Image.new("RGBA", im.size, tuple(bg) + (255,))
    bg.alpha_composite(im)
    return bg.convert("RGB")


def label(im: Image.Image, text: str) -> Image.Image:
    font = ImageFont.truetype("DejaVuSans.ttf", 34)
    out = Image.new("RGB", (im.width, im.height + 60), BG)
    out.paste(im, (0, 60))
    ImageDraw.Draw(out).text((20, 12), text, fill=(214, 216, 220), font=font)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("board", nargs="?", default=str(REPO / "hw/pod/draft_r1/pod_r1_routed.kicad_pcb"))
    ap.add_argument("--out", default=str(REPO / "docs/diagrams/renders"))
    ap.add_argument("--masks", default="Black")       # owner 2026-10-02: black mask (spec O23)
    ap.add_argument("--views", default="top,bottom,iso")
    ap.add_argument("--zoom", type=float, default=1.8)
    ap.add_argument("--grid", action="store_true")
    a = ap.parse_args()
    board, out = Path(a.board).resolve(), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    tops = []
    with tempfile.TemporaryDirectory() as td:
        for mask in a.masks.split(","):
            pcb = scratch_copy(board, mask, Path(td))
            for view in a.views.split(","):
                raw = Path(td) / f"{mask}_{view}.png"
                render(pcb, view, raw, a.zoom if view != "iso" else a.zoom * 0.8)
                im = on_dark(raw, bg=BG_FOR.get(mask, BG))
                dst = out / f"{board.stem}_{mask.lower().replace(' ', '_')}_{view}.png"
                im.save(dst)
                print(dst)
                if view == "top":
                    tops.append((mask, im))
    if a.grid and tops:
        w, h = max(i.width for _, i in tops), max(i.height for _, i in tops) + 60
        cols = 2
        rows = (len(tops) + cols - 1) // cols
        grid = Image.new("RGB", (w * cols, h * rows), BG)
        for k, (mask, im) in enumerate(tops):
            grid.paste(label(im, f"{mask} mask, {SILK_ON.get(mask, 'white').lower()} lettering, gold (ENIG) pads"), ((k % cols) * w, (k // cols) * h))
        dst = out / f"{board.stem}_masks.png"
        grid.save(dst)
        print(dst)


if __name__ == "__main__":
    main()
