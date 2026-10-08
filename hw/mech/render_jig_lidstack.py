"""blender -b -P hw/mech/render_jig_lidstack.py -> docs/diagrams/jig-lidstack.png (assembled) + jig-lidstack-exploded.png.
Needs hw/mech/out/jigs/fit_*.stl from jig_lidstack_fit.py. True black #000000 background; jig grey + cyan clips; lid/M ghosted 40 %."""
import bpy, math, sys
from pathlib import Path
from mathutils import Vector
R = Path(__file__).resolve().parent; J = R / "out/jigs"; D = R.parent.parent / "docs/diagrams"
GREY, CYAN, LID, BOARD = (0.62, 0.64, 0.68, 1), (0.0, 0.85, 0.95, 1), (0.75, 0.85, 1.0, 1), (0.25, 0.9, 0.4, 1)
def build(explode):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    def mat(col, alpha=1.0, emit=0.0):
        m = bpy.data.materials.new("m"); m.use_nodes = True; b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = col; b.inputs["Roughness"].default_value = 0.45; b.inputs["Alpha"].default_value = alpha
        if emit: b.inputs["Emission Color"].default_value = col; b.inputs["Emission Strength"].default_value = emit
        return m
    spec = dict(jig=(GREY, 1, 0, 0), clip1=(CYAN, 1, 0.15, 11), clip2=(CYAN, 1, 0.15, 11), gauge=(CYAN, 1, 0.3, -7),
                lid=(LID, 0.4, 0.5, 0), M=(BOARD, 0.4, 0.5, 6), U2=((0.9, 0.7, 0.2, 1), 0.4, 0, 6))
    for n, (c, a, e, dz) in spec.items():
        bpy.ops.wm.stl_import(filepath=str(J / f"fit_{n}.stl")); o = bpy.context.object; o.data.materials.append(mat(c, a, e))
        if explode: o.location.z += dz
        bpy.ops.object.shade_flat() if False else None
    sc = bpy.context.scene
    w = bpy.data.worlds.new("w"); w.use_nodes = True; w.node_tree.nodes["Background"].inputs[0].default_value = (0, 0, 0, 1); sc.world = w
    sc.view_settings.view_transform = "Standard"; sc.view_settings.look = "None"
    sc.render.engine = "CYCLES"; sc.cycles.samples = 96; sc.cycles.use_denoising = False; sc.cycles.device = "CPU"
    sc.cycles.transparent_max_bounces = 16; sc.render.film_transparent = False
    sc.render.resolution_x, sc.render.resolution_y = 1800, 1100
    for loc, e, sz in (((-40, -60, 90), 60000, 40), ((90, 40, 50), 30000, 40)):
        l = bpy.data.lights.new("l", "AREA"); l.energy = e; l.size = sz; ob = bpy.data.objects.new("l", l); ob.location = loc
        ob.rotation_euler = (Vector((30, 0, 0)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler(); bpy.context.collection.objects.link(ob)
    ctr = Vector((36, -2, 9 if explode else 4)); d = Vector((-0.45, -0.8, 0.62)).normalized()
    c = bpy.data.cameras.new("c"); c.type = "ORTHO"; c.ortho_scale = 52 if explode else 46
    co = bpy.data.objects.new("c", c); co.location = ctr + d * 200; co.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    bpy.context.collection.objects.link(co); sc.camera = co
for ex, name in ((False, "jig-lidstack.png"), (True, "jig-lidstack-exploded.png")):
    build(ex); bpy.context.scene.render.filepath = str(D / name); bpy.ops.render.render(write_still=True)
