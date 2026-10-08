"""K4 board stack only (real routed P + M STEP, placed by k4_real_boards.py): exploded 3 mm iso (P far from the lid, M lid side), and a BM28 cut close-up
-> docs/diagrams/k4-review/stack-iso.png, stack-section.png; prints the mic-port / SW1 alignment offsets vs the shell features (dims_k4.MIC / SW).
    systemd-run --user --scope --quiet -p MemoryMax=4G -p MemorySwapMax=0 blender -b -P hw/mech/render_k4_stack.py
"""
import math, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dims_k4 as K
OUT = HERE.parent.parent / "docs" / "diagrams" / "k4-review"
D = HERE / "out" / "k4r"
EXPL = 3.0
BG = (14, 15, 18)

def align():
    """KiCad file coords: M U2 port NPTH (1.75, 6.0), SW1 (5.3, 6.0); stack -> pod X = STACK_X0 + x, Z = ZC + (y - 6)."""
    r = {}
    for n, (bx, by), tgt in (("mic port", (1.75, 6.0), K.MIC), ("SW1", (5.3, 6.0), K.SW)):
        x, z = K.STACK_X0 + bx, K.ZC + (by - 6.0)
        r[n] = (round(x - tgt[0], 3), round(z - tgt[1], 3))
    return r

def labels(im, lines):
    from PIL import Image, ImageDraw, ImageFont
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 26)
    cv = Image.new("RGB", (im.width, im.height + 110), BG); cv.paste(im, (0, 110), im)
    d = ImageDraw.Draw(cv)
    for i, (t, c) in enumerate(lines): d.text((24, 12 + 40 * i), t, fill=c, font=f)
    return cv

def render():
    import bpy
    from mathutils import Vector
    from PIL import Image
    for view in ("iso", "section"):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        objs = {}
        for n in ("M", "P"):
            bpy.ops.wm.stl_import(filepath=str(D / f"board_{n}.stl"), global_scale=0.001)
            o = bpy.context.selected_objects[0]
            m = bpy.data.materials.new(n); m.use_nodes = True
            b = m.node_tree.nodes["Principled BSDF"]
            b.inputs["Base Color"].default_value = ((0.1, 0.45, 0.2, 1) if n == "P" else (0.2, 0.35, 0.8, 1)); b.inputs["Roughness"].default_value = 0.4
            o.data.materials.append(m); objs[n] = o
        # exploded: P moves away from M, i.e. -Y (far from the lid)
        if view == "iso":
            objs["P"].location.y -= EXPL * 0.001
        c = Vector((K.STACK_X0 + 7.75, 8.2 - (EXPL / 2 if view == "iso" else 0), K.ZC)) * 0.001
        if view == "section":
            cut = bpy.data.objects.new("c", None)
            bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.04, 0.02, (K.ZC + 0.02) * 0.001 + 0.05)); cut = bpy.context.object
            cut.scale = (0.3, 0.3, 0.1); cut.hide_render = True
            for o in objs.values():
                md = o.modifiers.new("cut", "BOOLEAN"); md.operation, md.object, md.solver = "DIFFERENCE", cut, "EXACT"
        s = bpy.context.scene
        L = bpy.data.lights.new("k", "AREA"); L.energy, L.size = 1.2, 0.15
        lo = bpy.data.objects.new("k", L); bpy.context.collection.objects.link(lo)
        cam = bpy.data.cameras.new("cam")
        if view == "iso":
            cam.lens = 70; loc = c + Vector((-0.05, 0.075, 0.07))
        else:
            cam.type, cam.ortho_scale = "ORTHO", 0.020 if False else 0.018; loc = c + Vector((0, 0, 0.2))
            c = Vector((K.STACK_X0 + 11.0, 8.2, K.ZC)) * 0.001; loc = c + Vector((0, 0, 0.2))
        lo.location = loc + Vector((0, 0.05, 0.05)); lo.rotation_euler = (c - lo.location).to_track_quat("-Z", "Y").to_euler()
        co = bpy.data.objects.new("cam", cam); bpy.context.collection.objects.link(co); co.location = loc
        co.rotation_euler = (0, 0, 0) if view == "section" else (c - loc).to_track_quat("-Z", "Y").to_euler()
        s.camera = co; s.render.engine = "CYCLES"; s.cycles.samples = 64; s.cycles.use_denoising = True
        s.world = bpy.data.worlds.new("w"); s.world.use_nodes = True
        s.world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.5, 0.5, 0.55, 1); s.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6
        s.render.film_transparent = True; s.render.resolution_x, s.render.resolution_y = 1400, 1000
        s.render.filepath = str(OUT / f"_{view}.png"); bpy.ops.render.render(write_still=True)
        im = Image.open(s.render.filepath).convert("RGBA")
        a = align()
        if view == "iso":
            ls = [("K4 board stack, exploded 3 mm: P (green, MCU on its outer face) over M (blue, lid side)", (235, 235, 240)),
                  ("lid features at the top of the lid side of M; P is toward the cell floor", (140, 200, 255))]
        else:
            ls = [("Cut at z = %.1f (mic/SW1/BM28 plane), M blue over P green, gap 0.6" % K.ZC, (235, 235, 240)),
                  ("BM28 has no 3D model in the STEP (gap only). Offsets vs shell: mic port %s, SW1 %s mm" % (a["mic port"], a["SW1"]), (140, 200, 255))]
        labels(im, ls).save(OUT / f"stack-{view}.png", optimize=True)
        (OUT / f"_{view}.png").unlink()
if __name__ == "__main__":
    print("align", align())
    try:
        import bpy; render()
    except ImportError:
        pass
