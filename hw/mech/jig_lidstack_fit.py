"""Fit check for jig_lidstack: real shell_k4.lid() in the cradle + board M at its bonded position. -> out/jigs/jig_lidstack_fit.json, parts STLs for render.
    python3 hw/mech/jig_lidstack_fit.py     (jig frame: u=pod x, w=pod z, v=up=-pod y)"""
import json, sys, io, contextlib
from pathlib import Path
from build123d import Box, Cylinder, Pos, Rot, export_stl
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
with contextlib.redirect_stdout(io.StringIO()):
    import jig_lidstack as J
import dims_k4 as K, shell_k4 as S
OUT = HERE / "out" / "jigs"
def to_jig(p):                                   # pod (x,y,z) -> jig (x, z, BASE + Y_OUT - y)
    return Pos(0, 0, J.BASE + K.Y_OUT) * (Rot(-90, 0, 0) * p)
lid = to_jig(S.lid())
yF, yB = K.Y_F, K.Y_F - K.PCB_T
vF, vB = J.BASE + K.Y_OUT - yF, J.BASE + K.Y_OUT - yB
mx, mz = K.MIC
M = J.blk(K.STACK_X0, K.STACK_X1, K.STACK_Z0, K.STACK_Z1, vF, vB) - J.cyl(mx, mz, K.MIC_HOLE_D, vF - 1, vB + 1)
U2 = J.blk(mx - 2.65 / 2, mx + 2.65 / 2, mz - 3.5 / 2, mz + 3.5 / 2, vB, vB + 1.08) - J.cyl(mx, mz, K.MIC_HOLE_D, vB - 1, vB + 2)
gauge = J.cyl(mx, mz, 0.60, -0.5, vB + 1.08 + 0.6)
vol = lambda a, b: round((a & b).volume, 5)
r = dict(v_M_Fface=round(vF, 3), v_M_Bface=round(vB, 3), v_pin_tip=round(J.V_PIN_BOT, 3), v_lid_inner=J.V_LID, ledge_top_v=round(J.BASE + K.Y_OUT - (K.Y_LID_IN - K.LID_STANDOFF), 3))
r["interf_lid_jig"] = vol(lid, J.jig + J.clip1 + J.clip2); r["interf_M_jig"] = vol(M, J.jig + J.clip1 + J.clip2); r["interf_M_lid"] = vol(M, lid)
r["interf_U2_jig"] = vol(U2, J.jig + J.clip1 + J.clip2); r["interf_U2_lid"] = vol(U2, lid); r["interf_gauge_jig"] = vol(gauge, J.jig)
r["interf_gauge_lid"] = vol(gauge, lid); r["interf_gauge_M"] = vol(gauge, M); r["interf_gauge_U2"] = vol(gauge, U2)
_c = J.clip1 + J.clip2
r["interf_clips_lid"] = vol(_c, lid); r["interf_clips_M_U2"] = vol(_c, M + U2); r["interf_clips_body"] = vol(_c, J.jig); r["interf_gauge_clips"] = vol(gauge, _c)
r["gap_lid_cradle_per_side_mm"] = J.CL; r["lid_bbox_u"] = [round(lid.bounding_box().min.X, 3), round(lid.bounding_box().max.X, 3)]
r["lid_bbox_w"] = [round(lid.bounding_box().min.Y, 3), round(lid.bounding_box().max.Y, 3)]
# M edge to pins
pxf, zcf, xcl, pzl = J.px, J.zc, J.xc, J.pz
r["M_front_edge_to_pin1_face_mm"] = round(K.STACK_X0 - (pxf + J.PIN_D / 2), 3)
r["M_lower_edge_to_pin2_face_mm"] = round(K.STACK_Z0 - (pzl + J.PIN_D / 2), 3)
r["pin1_tip_above_lid_inner_mm"] = round(J.V_PIN_BOT - J.V_LID, 3)
r["pin_tip_vs_M_Fface_mm"] = round(vF - J.V_PIN_BOT, 3)
r["mic_path_radial_mm"] = dict(gauge_r=0.30, jig_hole=0.60 - 0.30, lid_bore=K.DUCT_D / 2 - 0.30, M_hole=K.MIC_HOLE_D / 2 - 0.30)
# removal: (1) clips pulled straight up clear of everything; (2) lid+M lifted out of the body, 0.25 steps to 20 mm
clips = J.clip1 + J.clip2; worst = 0.0
for i in range(1, 80):
    s_ = i * 0.25; worst = max(worst, vol(Pos(0, 0, s_) * clips, J.jig + lid + M + U2))
r["clip_pull_overlap_mm3_max"] = worst; worst = 0.0; bad = None
asm = lid + M + U2
for i in range(1, 80):
    s_ = i * 0.25; v = vol(Pos(0, 0, s_) * asm, J.jig)
    if v > 1e-4: worst, bad = max(worst, v), s_
r["lid_lift_overlap_mm3_max"] = worst; r["lid_lift_first_blocked_at_mm"] = bad
(OUT / "jig_lidstack_fit.json").write_text(json.dumps(r, indent=1)); print(json.dumps(r, indent=1))
for n, p in dict(jig=J.jig, clip1=J.clip1, clip2=J.clip2, lid=lid, M=M, U2=U2, gauge=gauge).items(): export_stl(p, str(OUT / f"fit_{n}.stl"))
