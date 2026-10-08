"""Real-light Blender renders: K4 end-to-end (out/k4) vs K1-thin stacked (out/k1t), same temple, same camera, 3 views.

    python3 hw/mech/k4_concept.py && ULTRASONIC_DESIGN=k1t python3 hw/mech/shell_r2.py   # STLs
    systemd-run --user --scope --quiet -p MemoryMax=4G -p MemorySwapMax=0 blender -b -P hw/mech/render_k4_vs_k1t.py
    python3 hw/mech/render_k4_vs_k1t.py --compose        # -> docs/diagrams/k4-vs-k1t-{iso,top,section}.png (A left, B right)
Frame: STL mm imported at 0.001; X along arm, Y outward, Z up. Temple/adapter from out/final. Transparent renders composited on dark.
"""
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
DOCS = HERE.parent.parent / "docs" / "diagrams"
PODS = {"A": OUT / "k1t", "B": OUT / "k4"}
LABEL = {"A": ("A  K1-thin stacked", "T 8.5   L 33.6   H 14.1 mm", "130 mAh cell on top of the board"),
         "B": ("B  K4 end-to-end", "T 6.4   L 51.1   H 14.8 mm", "same cell beside a 17 mm board, along the arm")}
VIEWS = ("iso", "top", "section")
CUT_Z = -2.3
C = (41.5, 8.0, -2.3)   # common look-at point, mm


def compose():
    from PIL import Image, ImageDraw, ImageFont
    try:
        f1 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 44)
        f2 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 34)
    except OSError:
        f1 = f2 = ImageFont.load_default()
    for v in VIEWS:
        ims = [Image.open(OUT / "k4cmp" / f"{k}_{v}.png").convert("RGBA") for k in "AB"]
        w, h = ims[0].size
        W, top = 2 * w + 30, 190
        cv = Image.new("RGB", (W, h + top), (14, 15, 18))
        d = ImageDraw.Draw(cv)
        for i, k in enumerate("AB"):
            x = i * (w + 30)
            bg = Image.new("RGBA", (w, h), (20, 22, 27, 255))
            cv.paste(Image.alpha_composite(bg, ims[i]).convert("RGB"), (x, top))
            a, b, c = LABEL[k]
            d.text((x + 30, 20), a, fill=(235, 235, 240), font=f1)
            d.text((x + 30, 80), b, fill=(120, 200, 255), font=f2)
            d.text((x + 30, 130), c, fill=(150, 150, 160), font=f2)
        cv = cv.resize((cv.width * 4 // 5, cv.height * 4 // 5), Image.LANCZOS)
        DOCS.mkdir(parents=True, exist_ok=True)
        p = DOCS / f"k4-vs-k1t-{v}.png"
        cv.save(p, optimize=True)
        print(p, p.stat().st_size // 1024, "KB")


def render_all():
    import bpy
    from mathutils import Vector
    MATS = {"body": ((0.06, 0.06, 0.07), 0.0, 0.5), "armour": ((0.10, 0.105, 0.12), 0.6, 0.35), "cell": ((0.8, 0.62, 0.2), 0.3, 0.4),
            "pcb": ((0.05, 0.3, 0.12), 0.0, 0.35), "chips": ((0.04, 0.04, 0.04), 0.0, 0.4), "metal": ((0.7, 0.7, 0.72), 1.0, 0.25),
            "silicone": ((0.16, 0.16, 0.17), 0.0, 0.6), "temple": ((0.02, 0.02, 0.025), 0.0, 0.2), "adapter": ((0.05, 0.05, 0.055), 0.0, 0.5)}

    def mat(n):
        c, m, r = MATS[n]
        mt = bpy.data.materials.new(n)
        mt.use_nodes = True
        b = mt.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (*c, 1)
        b.inputs["Metallic"].default_value, b.inputs["Roughness"].default_value = m, r
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

    (OUT / "k4cmp").mkdir(exist_ok=True)
    for pod, D in PODS.items():
        for view in VIEWS:
            bpy.ops.wm.read_factory_settings(use_empty=True)
            info = json.loads((D / "parts.json").read_text())
            items = [(D / f"{n}.stl", v["mat"]) for n, v in info.items()]
            items += [(OUT / "final" / "temple.stl", "temple"), (OUT / "final" / "adapter.stl", "adapter")]
            objs = []
            for p, m in items:
                bpy.ops.wm.stl_import(filepath=str(p), global_scale=0.001)
                o = bpy.context.selected_objects[0]
                o.data.materials.append(mat(m))
                bpy.ops.object.shade_auto_smooth(angle=math.radians(35))
                objs.append(o)
            if view == "section":
                bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.04, 0.02, (CUT_Z + 0.05) * 0.001 + 0.05))
                cut = bpy.context.object
                cut.scale = (0.3, 0.3, 0.1)
                for o in objs:
                    md = o.modifiers.new("cut", "BOOLEAN")
                    md.operation, md.object, md.solver = "DIFFERENCE", cut, "EXACT"
                cut.hide_render = True
            s = bpy.context.scene
            w = bpy.data.worlds.new("w")
            s.world = w
            w.use_nodes = True
            env = w.node_tree.nodes.new("ShaderNodeTexEnvironment")
            env.image = bpy.data.images.load("/usr/lib/blender/datafiles/studiolights/world/interior.exr")
            w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.4
            w.node_tree.links.new(env.outputs["Color"], w.node_tree.nodes["Background"].inputs["Color"])
            c = tuple(x * 0.001 for x in C)
            cam = bpy.data.cameras.new("cam")
            if view == "top":
                cam.type, cam.ortho_scale = "ORTHO", 0.072
                loc = (c[0], c[1], 0.30)
                light("key", (c[0] - 0.05, c[1] + 0.05, 0.2), c, 0.15, 1.2)
            elif view == "iso":
                cam.lens = 60
                loc = (c[0] - 0.075, c[1] + 0.095, c[2] + 0.075)
                light("key", (c[0] - 0.05, c[1] + 0.15, c[2] + 0.15), c, 0.15, 1.3)
            else:
                cam.lens = 80
                loc = (c[0] - 0.02, c[1] + 0.07, c[2] + 0.17)
                light("key", (c[0], c[1] + 0.1, c[2] + 0.2), c, 0.2, 1.5)
            light("fill", (c[0] + 0.12, c[1] + 0.05, c[2] + 0.05), c, 0.15, 0.3)
            co = bpy.data.objects.new("cam", cam)
            bpy.context.collection.objects.link(co)
            co.location = loc
            look_at(co, c)
            if view == "top":
                co.rotation_euler = (0, 0, 0)       # looking down -Z, +X right, +Y up
            s.camera = co
            s.render.engine = "CYCLES"
            s.cycles.device = "CPU"
            s.cycles.samples = 64
            s.cycles.use_denoising = True
            s.render.film_transparent = True
            s.render.resolution_x, s.render.resolution_y = 1400, 1000
            s.view_settings.view_transform = "AgX"
            s.render.filepath = str(OUT / "k4cmp" / f"{pod}_{view}.png")
            bpy.ops.render.render(write_still=True)


if "--compose" in sys.argv:
    compose()
elif "bpy" in sys.modules or __name__ != "__main__" or True:
    try:
        import bpy  # noqa: F401
        render_all()
    except ImportError:
        print("run with blender -b -P, or --compose")
