"""Pod with the REAL routed boards: STEP of routed_P/M (hw/pod/k4/review_boards.py -> out/k4review/{P,M}.step) placed in the K4 stack frame
of shell_k4.py, replacing its placeholder pcb_top/stack_body/u2_mic/sw1 -> hw/mech/out/k4r (STL + parts.json).
    systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 python3 hw/mech/k4_real_boards.py
Mapping (board STEP: x right, y up = -KiCad y, z = F side up, slab z 0..0.8):
  M (board next to the lid: its B face carries SW1 + the mic port and faces the lid features, F face down, J20/U2 hang below): X=STACK_X0+xs, Y=Y_F-zs, Z=ZC+ys+6
  P (far board, F up toward M, U1 on its outer B face): X=STACK_X0+xs, Y=Y_B-1.4+zs, Z=ZC-ys-6  (long-axis flip). BM28 mated gap 0.6 (was 1.88-0.8=1.08, a bug) -> P F face at Y_B-0.6.
"""
import json, shutil, sys
from pathlib import Path
from build123d import import_step, Location, Matrix, export_stl, Compound
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dims_k4 as K
SRC, DST = ((HERE / "out" / "k4s", HERE / "out" / "k4r") if K.RELIEF == "len" else (HERE / "out" / "k4s_lift", HERE / "out" / "k4r_lift"))
DST.mkdir(exist_ok=True)
info = json.loads((SRC / "parts.json").read_text())
for n in info:
    if n not in ("pcb_top", "stack_body", "u2_mic", "sw1"):
        shutil.copy(SRC / f"{n}.stl", DST / f"{n}.stl")
    else:
        info[n] = None
info = {k: v for k, v in info.items() if v}
def place(b, m, tx, ty, tz):
    s = import_step(str(HERE / "out" / "k4review" / f"{b}.step"))
    # rows: new = M * old + t
    s = s.moved(Location()) if False else s
    from OCP.gp import gp_Trsf, gp_GTrsf, gp_Mat, gp_XYZ
    g = gp_GTrsf(gp_Mat(*m), gp_XYZ(tx, ty, tz))
    from OCP.BRepBuilderAPI import BRepBuilderAPI_GTransform
    t = BRepBuilderAPI_GTransform(s.wrapped, g, True); t.Build()
    from build123d import Shape
    return Shape.cast(t.Shape())
Mm = place("M", (1,0,0, 0,0,-1, 0,1,0), K.STACK_X0, K.Y_F, K.ZC + 6)
Pm = place("P", (1,0,0, 0,0,1, 0,-1,0), K.STACK_X0, K.Y_B - 1.4, K.ZC - 6)
for n, s in (("board_M", Mm), ("board_P", Pm)):
    export_stl(s, str(DST / f"{n}.stl"), tolerance=0.01, angular_tolerance=0.1)
    info[n] = {"mat": "pcb", "explode": [0, 0, 0]}
    print(n, s.bounding_box().min, s.bounding_box().max)
(DST / "parts.json").write_text(json.dumps(info, indent=1))
