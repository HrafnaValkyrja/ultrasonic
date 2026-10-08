"""blender -b -P hw/mech/render_jig_lidstack.py -> docs/diagrams/jig-lidstack.png (dark, headless)."""
import bpy, math
from pathlib import Path
R = Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.stl_import(filepath=str(R / "out/jigs/jig_lidstack.stl"))
o = bpy.context.object
m = bpy.data.materials.new("m"); m.diffuse_color = (0.55, 0.62, 0.75, 1); o.data.materials.append(m)
w = bpy.data.worlds.new("w"); w.use_nodes = True; w.node_tree.nodes["Background"].inputs[0].default_value = (0.04, 0.045, 0.06, 1)
bpy.context.scene.world = w
for loc, e in (((30, -40, 60), 4), ((-20, 30, 40), 2)):
    l = bpy.data.lights.new("l", "SUN"); l.energy = e; ob = bpy.data.objects.new("l", l); bpy.context.collection.objects.link(ob)
    ob.rotation_euler = (math.radians(45), 0, math.radians(30))
c = bpy.data.cameras.new("c"); c.type = "ORTHO"; c.ortho_scale = 68
co = bpy.data.objects.new("c", c); bpy.context.collection.objects.link(co)
co.location = (42, -55, 45); co.rotation_euler = (math.radians(55), 0, math.radians(0)); bpy.context.scene.camera = co
s = bpy.context.scene; s.render.resolution_x, s.render.resolution_y = 1400, 800
s.render.engine = "BLENDER_WORKBENCH"; s.display.shading.light = "STUDIO"; s.display.shading.color_type = "MATERIAL"
s.render.filepath = str(R.parent.parent / "docs/diagrams/jig-lidstack.png"); bpy.ops.render.render(write_still=True)
