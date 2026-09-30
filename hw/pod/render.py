"""Whole-board views of the draft pod board for review.

    source tools/env.sh && python3 hw/pod/render.py    # -> hw/pod/draft/view_*.png

3D renders of both sides at full-board zoom (reference text shrunk to 0.35 mm so it doesn't bury
a 20 x 10 mm board), plus flat copper plots per side.
"""
import subprocess
from pathlib import Path

import pcbnew

HERE = Path(__file__).resolve().parent
D = HERE / "draft"
mm = pcbnew.FromMM


def run(*a):
    subprocess.run(list(a), check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=600)


def main():
    b = pcbnew.LoadBoard(str(D / "pod_routed.kicad_pcb"))
    for fp in b.GetFootprints():
        for t in (fp.Reference(), fp.Value()):
            t.SetTextSize(pcbnew.VECTOR2I(mm(0.35), mm(0.35)))
            t.SetTextThickness(mm(0.05))
        fp.Value().SetVisible(False)
    view = D / "pod_view.kicad_pcb"
    pcbnew.SaveBoard(str(view), b)
    for side in ("top", "bottom"):
        run("kicad-cli", "pcb", "render", "--output", str(D / f"view_3d_{side}.png"), "--side", side,
            "--width", "1600", "--height", "900", "--zoom", "0.9", "--quality", "high",
            "--background", "transparent", str(view))
    for name, layers in (("front", "F.Cu,F.Silkscreen,Edge.Cuts"), ("back", "B.Cu,B.Silkscreen,Edge.Cuts"),
                         ("inner", "In1.Cu,In2.Cu,Edge.Cuts")):
        svg = D / f"view_{name}.svg"
        run("kicad-cli", "pcb", "export", "svg", "--layers", layers, "--page-size-mode", "2",
            "--exclude-drawing-sheet", "--mode-single", "--output", str(svg), str(view))
        run("rsvg-convert", "-w", "1600", "-b", "white", str(svg), "-o", str(D / f"view_{name}.png"))


if __name__ == "__main__":
    main()
