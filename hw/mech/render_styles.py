"""Blender (Cycles, CPU) renders of the style concepts from hw/mech/styles.py.

    blender -b -P hw/mech/render_styles.py -- [concept ...]    # -> hw/mech/out/styles/<concept>_<view>.png

Lighting: REAL (owner, 2026-09-30): an HDRI environment from Blender's bundled studio lights plus
one soft window-style key, neutral table. The old coloured neon rims are kept only as NEON=1.
Device: Cycles on the GPU (OptiX) when available - owner allowed it; this only USES the card, it
changes no driver or graphics setting. Falls back to CPU. Units: STL in mm, imported at 0.001 so
Blender works in metres. Frame: x = back along the temple, y = outward, z = up.
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
OUT = HERE / "out" / "styles"
INFO = json.loads((OUT / "parts.json").read_text())
GLOW = {"blue": (0.0, 0.18, 1.0), "cyan": (0.0, 0.85, 1.0), "magenta": (1.0, 0.05, 0.55), "amber": (1.0, 0.45, 0.02)}
RIM = {"blue": ((0.0, 0.7, 1.0), (1.0, 0.1, 0.6)), "cyan": ((0.0, 0.7, 1.0), (1.0, 0.1, 0.6)), "magenta": ((1.0, 0.1, 0.6), (0.1, 0.6, 1.0)),
       "amber": ((1.0, 0.5, 0.1), (0.2, 0.5, 1.0))}


def mat(name, base, metallic=0.0, rough=0.5, emit=None, strength=0.0, transmission=0.0, coat=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*base, 1)
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Roughness"].default_value = rough
    if coat:
        b.inputs["Coat Weight"].default_value = coat
    if transmission:
        b.inputs["Transmission Weight"].default_value = transmission
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = strength
    return m


def materials(glow, concept):
    body = (0.018, 0.018, 0.02) if concept != "heatsink" else (0.05, 0.052, 0.058)
    return {
        "body": mat("body", body, 0.0, 0.62),
        "armour": mat("armour", (0.06, 0.065, 0.075), 0.85, 0.32) if concept.startswith("blade") else mat("fins", (0.02, 0.02, 0.022), 0.9, 0.4),
        "chrome": mat("chrome", (0.9, 0.9, 0.92), 1.0, 0.07),
        "paint": mat("chrome_paint", (0.8, 0.8, 0.82), 1.0, 0.22),
        "adapter": mat("adapter", (0.03, 0.03, 0.034), 0.0, 0.5),
        "metal": mat("metal", (0.55, 0.56, 0.6), 1.0, 0.25),
        "glow": mat("glow", GLOW[glow], 0.0, 0.4, GLOW[glow], 18.0 if glow != "blue" else 3.0),
        "sleeve": mat("sleeve", (0.01, 0.01, 0.012), 0.0, 0.55),
        "silicone_pad": mat("pad", (0.12, 0.12, 0.13), 0.0, 0.45),
        "pad_housing": mat("housing", body, 0.0, 0.62),
        "anchor": mat("anchor", (0.35, 0.36, 0.4), 1.0, 0.2),
        "temple": mat("acetate", (0.004, 0.004, 0.005), 0.0, 0.08, coat=1.0),
    }


def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def look_at(obj, target):
    d = Vector(target) - obj.location
    obj.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def area(name, loc, target, size, power, colour):
    L = bpy.data.lights.new(name, "AREA")
    L.size, L.energy, L.color = size, power, colour
    o = bpy.data.objects.new(name, L)
    bpy.context.collection.objects.link(o)
    o.location = loc
    look_at(o, target)


import os
NEON = os.environ.get("NEON") == "1"
HDRI = "/usr/lib/blender/datafiles/studiolights/world/interior.exr"


def real_world(c):
    w = bpy.data.worlds.new("w")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    env = nt.nodes.new("ShaderNodeTexEnvironment")
    env.image = bpy.data.images.load(HDRI)
    bg = nt.nodes["Background"]
    bg.inputs["Strength"].default_value = 0.45
    nt.links.new(env.outputs["Color"], bg.inputs["Color"])
    area("key", (0.02, 0.16, 0.12), c, 0.12, 0.9, (1.0, 0.97, 0.92))     # soft window light
    area("bounce", (0.12, -0.05, 0.02), c, 0.1, 0.15, (0.95, 0.97, 1.0))


def scene(concept, floor=True):
    clear()
    info = INFO[concept]
    mats = materials(info["glow"], concept)
    for stl in sorted((OUT / concept).glob("*.stl")):
        bpy.ops.wm.stl_import(filepath=str(stl), global_scale=0.001)
        o = bpy.context.selected_objects[0]
        o.name = stl.stem
        o.data.materials.append(mats.get(stl.stem, mats["body"]))
        bpy.ops.object.shade_auto_smooth(angle=math.radians(35))
    # glossy dark floor for neon reflections
    c = (0.049, 0.004, -0.008)
    if not NEON:
        if floor:
            bpy.ops.mesh.primitive_plane_add(size=1.0, location=(0.05, 0.0, -0.045))
            bpy.context.object.data.materials.append(mat("table", (0.42, 0.40, 0.37), 0.0, 0.55))
        real_world(c)
        if concept.endswith("exploded"):
            bpy.data.objects["adapter"].data.materials[0] = mat("adapter_hi", (0.45, 0.47, 0.5), 0.0, 0.45)
            c = (0.062, 0.002, -0.004)
        return c
    if floor:
        bpy.ops.mesh.primitive_plane_add(size=1.0, location=(0.05, 0.0, -0.045))
        bpy.context.object.data.materials.append(mat("floor", (0.01, 0.011, 0.014), 0.0, 0.18))
    w = bpy.data.worlds.new("w")
    bpy.context.scene.world = w
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.004, 0.005, 0.009, 1)
    c = (0.049, 0.004, -0.008)
    r1, r2 = RIM[info["glow"]]
    area("key", (0.03, 0.14, 0.09), c, 0.08, 0.5, (0.9, 0.92, 1.0))
    area("rim1", (0.13, 0.06, 0.03), c, 0.05, 1.2, r1)
    area("rim2", (-0.03, -0.02, 0.05), c, 0.05, 0.9, r2)
    area("fill", (0.05, 0.10, -0.04), c, 0.1, 0.12, (0.6, 0.65, 0.8))
    if concept.endswith("exploded"):
        area("inb", (0.06, -0.14, -0.06), c, 0.08, 0.12, (0.85, 0.9, 1.0))     # technical view: neutral studio light, adapter in light grey
        c = (0.062, 0.002, -0.004)
        area("s1", (0.05, -0.12, -0.09), c, 0.12, 1.6, (1.0, 1.0, 1.0))
        area("s2", (0.10, -0.10, 0.08), c, 0.12, 1.0, (0.9, 0.95, 1.0))
        bpy.data.objects["adapter"].data.materials[0] = mat("adapter_hi", (0.45, 0.47, 0.5), 0.0, 0.45)
    return c


def camera(c, loc, lens=85, fstop=16):
    cam = bpy.data.cameras.new("cam")
    cam.lens = lens
    cam.dof.use_dof = True
    cam.dof.aperture_fstop = fstop
    o = bpy.data.objects.new("cam", cam)
    bpy.context.collection.objects.link(o)
    o.location = loc
    look_at(o, c)
    cam.dof.focus_distance = (Vector(loc) - Vector(c)).length
    bpy.context.scene.camera = o
    return o


def render(path, samples=128):
    s = bpy.context.scene
    s.render.engine = "CYCLES"
    s.cycles.device = "CPU"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        for kind in ("OPTIX", "CUDA"):
            try:
                prefs.compute_device_type = kind
            except TypeError:
                continue            # this Blender build lacks that backend (Ubuntu's has no OptiX)
            prefs.get_devices()
            gpus = [d for d in prefs.devices if d.type == kind]
            if gpus:
                for d in prefs.devices:
                    d.use = d.type == kind
                s.cycles.device = "GPU"
                break
    except Exception as e:  # no GPU backend: CPU is fine
        print("GPU unavailable:", e)
    print("Cycles device:", s.cycles.device, bpy.context.preferences.addons["cycles"].preferences.compute_device_type)
    s.cycles.samples = samples
    s.cycles.use_denoising = True
    s.render.resolution_x, s.render.resolution_y = 1400, 900
    s.view_settings.view_transform = "AgX"
    s.view_settings.look = "AgX - Punchy" if NEON else "None"
    s.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


VIEWS = {"hero": ((0.16, 0.15, 0.055), 70, 14), "side": ((0.052, 0.22, -0.006), 80, 32),
         "under": ((0.085, -0.17, -0.075), 50, 22), "inboard": ((0.03, -0.17, 0.03), 70, 16)}
VIEWS_FOR = {"blade2_exploded": ("under",)}


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for concept in (argv or list(INFO)):
        for view in VIEWS_FOR.get(concept, ("hero", "side")):
            loc, lens, fstop = VIEWS[view]
            c = scene(concept, floor=view not in ("under", "inboard"))
            camera(c, loc, lens, fstop)
            render(OUT / f"{concept}_{view}.png")


main()
