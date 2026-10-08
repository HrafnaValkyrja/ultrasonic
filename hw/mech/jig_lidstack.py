"""Printable alignment jig for K4 build step 7 (stack onto lid). docs/proof/buildability/README.md, Alt A.

    python3 hw/mech/jig_lidstack.py   # -> hw/mech/out/jigs/jig_lidstack.stl, jig_lidstack.json; render: --render (blender, headless)

Lid sits OUTER face down in a pocket (inner face flush with the jig top). Board M goes on the VHB, F face down. Two pins hang from
two bridges that rise OUTSIDE the lid outline and stop two M edges (front edge X, lower edge Z); the 3rd locating point is the
0.60 gauge pin, which goes up from underneath through a D1.2 jig hole, the lid bore (D1.0) and M's mic hole (0.65).
Axes: jig u = pod x, jig w = pod z, v = up (= pod -y). All numbers from dims_k4 / shell_k4. Print: 0.1 layer, PETG/PLA, pins in-plane.
"""
import json, sys
from pathlib import Path
from build123d import Box, Cylinder, Pos, export_stl, Align
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dims_k4 as K

CL = 0.15                # cradle clearance per side (FDM)
PIN_D, PIN_CL = 1.0, 0.05
BASE = 3.0
LID_T = K.LID_T          # 1.0: pocket depth, lid face flush with jig top
VHB, PCB = K.VHB_T, K.PCB_T
x0, x1, z0, z1 = K.X0, K.X1, K.Z0, K.Z1
bx0, bz0 = K.STACK_X0, K.STACK_Z0            # M board front / lower edges (pod frame)
mx, mz = K.MIC
V_LID = BASE + LID_T                          # lid inner face height
V_PIN_BOT = V_LID + VHB + 0.15                # pin tip: engages 0.65 of M's 0.8
V_ARM = V_LID + VHB + PCB + 2.0               # arm underside clears the board by 2.0
def blk(xa, xb, za, zb, va, vb):
    return Pos((xa + xb) / 2, (za + zb) / 2, (va + vb) / 2) * Box(xb - xa, zb - za, vb - va)
def cyl(x, z, d, va, vb):
    return Pos(x, z, (va + vb) / 2) * Cylinder(d / 2, vb - va)

M = 3.0                                       # wall around the pocket
jig = blk(x0 - CL - M, x1 + CL + M, z0 - CL - M, z1 + CL + M, 0, V_LID)
jig -= blk(x0 - CL, x1 + CL, z0 - CL, z1 + CL, BASE, V_LID + 1)
jig -= cyl(mx, mz, 1.2, -1, BASE + 1)                       # clear path for the 0.60 pin (to 1.2: 0.6 of side play, no snagging)
jig -= cyl(mx, mz, 2.4, -0.01, 0.6)                         # lead-in cone substitute: counterbore under the hole
jig -= blk(x0 + 6, x1 - 6, z0 + 3, z1 - 3, -1, BASE - 1.2)  # lightening pocket underneath (keeps 1.2 floor)
# bridge 1: front-edge stop, column in the front wall, arm reaches in +x over the lid margin
px = bx0 - PIN_D / 2 - PIN_CL
col_x0, col_x1 = x0 - CL - M, x0 - CL - 0.2
zc = (bz0 + K.STACK_Z1) / 2 - 3                             # pin on the M edge, 3 mm below the board mid-line (off the mic/button)
jig += blk(col_x0, col_x1, zc - 1.5, zc + 1.5, 0, V_ARM + 1.2)
jig += blk(col_x0, px + PIN_D / 2, zc - 1.5, zc + 1.5, V_ARM, V_ARM + 1.2)
jig += cyl(px, zc, PIN_D, V_PIN_BOT, V_ARM)
# bridge 2: lower-edge stop
pz = bz0 - PIN_D / 2 - PIN_CL
xc = bx0 + 9.0
row_z0, row_z1 = z0 - CL - M, z0 - CL - 0.2
jig += blk(xc - 1.5, xc + 1.5, row_z0, row_z1, 0, V_ARM + 1.2)
jig += blk(xc - 1.5, xc + 1.5, row_z0, pz + PIN_D / 2, V_ARM, V_ARM + 1.2)
jig += cyl(xc, pz, PIN_D, V_PIN_BOT, V_ARM)
# NB the M tail (stack rear) stays free; wires and cell leads are soldered later (step 9).
out = HERE / "out" / "jigs"; out.mkdir(parents=True, exist_ok=True)
export_stl(jig, str(out / "jig_lidstack.stl"))
bb = jig.bounding_box()
info = dict(size_mm=[round(bb.size.X, 1), round(bb.size.Y, 1), round(bb.size.Z, 1)], volume_mm3=round(jig.volume),
            mic_uw=[round(mx, 3), round(mz, 3)], pin_front=[round(px, 3), round(zc, 3)], pin_low=[round(xc, 3), round(pz, 3)],
            m_edge_x=round(bx0, 3), m_edge_z=round(bz0, 3), v_lid_face=V_LID, pin_tip_v=V_PIN_BOT)
(out / "jig_lidstack.json").write_text(json.dumps(info, indent=1)); print(info)
