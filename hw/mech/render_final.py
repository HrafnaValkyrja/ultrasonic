"""Real-light Blender renders of the current assembly (STLs from hw/mech/out/final/, see parts.json).

    blender -b -P hw/mech/render_final.py       # -> hw/mech/out/final/{assembled,open,exploded}.png
CPU Cycles (Ubuntu's Blender has no working GPU backend here). Units: mm STL imported at 0.001.
"""
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector

D = Path(__file__).resolve().parent / "out" / "final"
INFO = json.loads((D / "parts.json").read_text())
HDRI = "/usr/lib/blender/datafiles/studiolights/world/interior.exr"
MATS = {  # base colour, metallic, roughness, extra
    "body": ((0.025, 0.025, 0.028), 0.0, 0.55), "armour": ((0.07, 0.075, 0.085), 0.8, 0.35),
    "cell": ((0.75, 0.62, 0.25), 0.3, 0.4), "pcm": ((0.1, 0.35, 0.15), 0.0, 0.5),
    "pcb": ((0.05, 0.3, 0.12), 0.0, 0.35), "chips": ((0.05, 0.05, 0.05), 0.0, 0.4),
    "metal": ((0.7, 0.7, 0.72), 1.0, 0.25), "transducer": ((0.55, 0.2, 0.08), 0.2, 0.5),
    "glow": ((0.05, 0.25, 1.0), 0.0, 0.3), "silicone": ((0.16, 0.16, 0.17), 0.0, 0.6),
    "niti": ((0.6, 0.6, 0.62), 1.0, 0.3), "adapter": ((0.04, 0.04, 0.045), 0.0, 0.5),
    "temple": ((0.004, 0.004, 0.005), 0.0, 0.1),
}


def mat(name):
    (c, m, r) = MATS[name]
    mt = bpy.data.materials.new(name)
    mt.use_nodes = True
    b = mt.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*c, 1)
    b.inputs["Metallic"].default_value = m
    b.inputs["Roughness"].default_value = r
    if name == "glow":
        b.inputs["Emission Color"].default_value = (*c, 1)
        b.inputs["Emission Strength"].default_value = 3.0
    if name == "temple":
        b.inputs["Coat Weight"].default_value = 1.0
    return mt


def look_at(o, t):
    o.rotation_euler = (Vector(t) - o.location).to_track_quat("-Z", "Y").to_euler()


def light(name, loc, t, size, power):
    L = bpy.data.lights.new(name, "AREA")
    L.size, L.energy = size, power
    o = bpy.data.objects.new(name, L)
    bpy.context.collection.objects.link(o)
    o.location = loc
    look_at(o, t)


def scene(mode):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for name, v in INFO.items():
        if mode == "open" and name in ("lid",):
            continue
        bpy.ops.wm.stl_import(filepath=str(D / f"{name}.stl"), global_scale=0.001)
        o = bpy.context.selected_objects[0]
        o.name = name
        o.data.materials.append(mat(v["mat"]))
        bpy.ops.object.shade_auto_smooth(angle=math.radians(35))
        if mode == "exploded":
            dx, dy, dz = v["explode"]
            o.location = (dx * 0.001, dy * 0.001, dz * 0.001)
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=(0.05, 0.0, -0.05))
    t = bpy.context.object
    tm = bpy.data.materials.new("table")
    tm.use_nodes = True
    tm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.42, 0.40, 0.37, 1)
    t.data.materials.append(tm)
    w = bpy.data.worlds.new("w")
    bpy.context.scene.world = w
    w.use_nodes = True
    env = w.node_tree.nodes.new("ShaderNodeTexEnvironment")
    env.image = bpy.data.images.load(HDRI)
    w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.45
    w.node_tree.links.new(env.outputs["Color"], w.node_tree.nodes["Background"].inputs["Color"])
    c = (0.052, 0.004, -0.010)
    light("key", (0.02, 0.17, 0.12), c, 0.12, 0.9)
    light("fill", (0.13, -0.06, 0.03), c, 0.10, 0.2)
    return c


def shoot(c, loc, lens, out):
    cam = bpy.data.cameras.new("cam")
    cam.lens = lens
    o = bpy.data.objects.new("cam", cam)
    bpy.context.collection.objects.link(o)
    o.location = loc
    look_at(o, c)
    s = bpy.context.scene
    s.camera = o
    s.render.engine = "CYCLES"
    s.cycles.device = "CPU"
    s.cycles.samples = 96
    s.cycles.use_denoising = True
    s.render.resolution_x, s.render.resolution_y = 1500, 1000
    s.view_settings.view_transform = "AgX"
    s.render.filepath = str(out)
    bpy.ops.render.render(write_still=True)


for mode, loc, lens in (("assembled", (0.15, 0.15, 0.05), 62), ("open", (0.11, 0.16, 0.04), 62),
                        ("exploded", (0.17, 0.19, 0.06), 50)):
    shoot(scene(mode), loc, lens, D / f"{mode}.png")
