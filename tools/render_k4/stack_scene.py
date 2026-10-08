"""Blender (headless, Cycles CPU) scene of the mated K4 stack from kicad-cli GLBs (P.glb, M.glb, origin = file 0,0, metres).
    blender -b -P tools/render_k4/stack_scene.py -- GLBDIR OUTDIR [view ...]
views: iso, exploded, scale, side, under.  Stack frame = M's file frame (x right, y = -file_y, z up = M inner face up);
P rotated 180 deg about x (flipped across its long axis), y offset -H; P inner (file F) face at M inner face + GAP."""
import sys, math, bpy, mathutils
from bpy_extras.object_utils import world_to_camera_view
A = sys.argv[sys.argv.index("--") + 1:]
GLB, OUT = A[0], A[1]; VIEWS = A[2:] or ["iso", "exploded", "scale", "side"]
H, GAP, EXP = 12.0, 0.6, 4.0
import os
Q = float(os.environ.get('QUICK', '1'))      # QUICK=0.4 -> test render
W_PX = int(2000 * Q)
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
roots, zr, kids = {}, {}, {}
for n in "PM":
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=f"{GLB}/{n}.glb")
    new = [o for o in bpy.data.objects if o not in before]
    r = bpy.data.objects.new(f"root_{n}", None); sc.collection.objects.link(r)
    for o in new:
        if o.parent is None: o.parent = r
    kids[n] = new
    r.scale = (1000, 1000, 1000); roots[n] = r
    bpy.context.view_layer.update()
    pcb = max([o for o in new if o.type == "MESH" and o.dimensions.x > 14.9], key=lambda o: o.dimensions.z)
    zs = [(pcb.matrix_world @ mathutils.Vector(c)).z for c in pcb.bound_box]
    zr[n] = (min(zs), max(zs))                              # board slab z range in mm
    zr[n] = (zr[n][0] - 0.03, zr[n][1] + 0.03)   # copper + mask on each face
    print(n, "slab", zr[n])
# M: inner (F) face up, F surface at z = 0. P: flipped, F surface at GAP
roots["M"].location = (0, 0, -zr["M"][1])
def place_P(extra):
    roots["P"].rotation_euler = (math.pi, 0, 0)
    roots["P"].location = (0, -H, zr["P"][1] + GAP + extra)   # after rot, F surface (old z max) lands at z = GAP+extra
place_P(0)
bpy.context.view_layer.update()
def bounds(objs):
    pts = [o.matrix_world @ mathutils.Vector(c) for o in objs if o.type == "MESH" for c in o.bound_box]
    return [min(p[i] for p in pts) for i in range(3)], [max(p[i] for p in pts) for i in range(3)]
allm = [o for o in bpy.data.objects if o.type == "MESH"]
lo, hi = bounds(allm)
print("STACK bbox mm", [round(x, 3) for x in lo], [round(x, 3) for x in hi], "height", round(hi[2] - lo[2], 3))
FLOOR = lo[2]
# --- materials
def mat(name, col, metal=0.0, rough=0.4, emit=None):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*col, 1); b.inputs["Metallic"].default_value = metal; b.inputs["Roughness"].default_value = rough
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1); b.inputs["Emission Strength"].default_value = 6
    return m
for m in bpy.data.materials:                                     # soften mirror-like KiCad PBR
    if m.use_nodes:
        b = m.node_tree.nodes.get("Principled BSDF")
        if b and b.inputs["Metallic"].default_value < 0.5: b.inputs["Roughness"].default_value = max(b.inputs["Roughness"].default_value, 0.35)
# --- material overrides by mesh name (KiCad GLB drops STEP colours on my simple models; mask must be black)
OV = {"soldermask": ((0.0025, 0.0025, 0.0028), 0, 0.30), "silkscreen": ((0.55, 0.55, 0.55), 0, 0.6), "PCB": ((0.003, 0.003, 0.0035), 0, 0.32),
      "can": ((0.72, 0.73, 0.75), 1, 0.28), "substrate": ((0.05, 0.12, 0.07), 0, 0.5), "mark": ((0.1, 0.1, 0.1), 0, 0.5),
      "frame": ((0.7, 0.71, 0.73), 1, 0.3), "cap": ((0.04, 0.04, 0.045), 0, 0.4), "btn": ((0.16, 0.16, 0.18), 0, 0.35),
      "term": ((0.85, 0.65, 0.22), 1, 0.3), "lcp": ((0.04, 0.04, 0.045), 0, 0.4), "au": ((0.85, 0.65, 0.22), 1, 0.3),
      "tab": ((0.7, 0.71, 0.73), 1, 0.3), "pad": ((0.85, 0.65, 0.22), 1, 0.28), "via": ((0.85, 0.65, 0.22), 1, 0.28), "xt_body": ((0.5, 0.47, 0.4), 0, 0.5), "blade": ((0.05, 0.05, 0.055), 0, 0.4)}
for o in bpy.data.objects:
    if o.type != "MESH": continue
    base = o.name.split(".")[0]; key = next((k for k in OV if base == k or base.endswith("_" + k)), None)
    if key is None and o.dimensions.x > 14.9 and o.dimensions.z > 0.5: key = "PCB"
    if key:
        c, mt, rg = OV[key]; o.data.materials.clear(); m_ = mat("ov_" + key, c, mt, rg); o.data.materials.append(m_)
        if key in ("soldermask", "PCB"): m_.node_tree.nodes["Principled BSDF"].inputs["Specular IOR Level"].default_value = 0.35
# --- GLB names are "=>[0:1:1:NN]" so the name map above misses the board layers: recolour by source material colour.
# big (board-sized) meshes: grey 0.5 = silkscreen, gold = ENIG, anything else (0.035 mask, green core/edge) = black satin mask.
BLK = mat("mask_black", (0.0025, 0.0025, 0.0028), 0, 0.30); BLK.node_tree.nodes["Principled BSDF"].inputs["Specular IOR Level"].default_value = 0.35
for o in bpy.data.objects:
    if o.type != "MESH" or o.dimensions.x <= 14.0: continue
    for i, sl in enumerate(o.data.materials):
        if sl is None or sl.name in ("ov_PCB", "ov_soldermask", "mask_black") or not sl.use_nodes: continue
        b = sl.node_tree.nodes.get("Principled BSDF")
        if b is None: continue
        r, g, bl = b.inputs["Base Color"].default_value[:3]
        silk = abs(r - g) < 0.02 and abs(g - bl) < 0.02 and r > 0.3; gold = r > 0.5 and bl < 0.2 or b.inputs["Metallic"].default_value > 0.5
        if not (silk or gold): o.data.materials[i] = BLK
# --- world + floor + lights
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
bg = w.node_tree.nodes["Background"]; bg.inputs[0].default_value = (0.004, 0.004, 0.005, 1); bg.inputs[1].default_value = 1.0
fl = bpy.data.objects.new("floor", bpy.data.meshes.new("floor")); sc.collection.objects.link(fl)
import bmesh
bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=400); bm.to_mesh(fl.data); bm.free()
fl.data.materials.append(mat("floor", (0.006, 0.006, 0.007), 0.0, 0.3)); fl.location = (0, 0, FLOOR - 0.001)
def area(name, loc, size, energy, col=(1, 1, 1)):
    d = bpy.data.lights.new(name, "AREA"); d.size = size; d.energy = energy; d.color = col
    o = bpy.data.objects.new(name, d); sc.collection.objects.link(o); o.location = loc
    c = o.constraints.new("TRACK_TO"); c.target = tgt; c.track_axis = "TRACK_NEGATIVE_Z"; c.up_axis = "UP_Y"
tgt = bpy.data.objects.new("tgt", None); sc.collection.objects.link(tgt); tgt.location = (7.8, -6, 0.8)
area("key", (-45, -75, 80), 70, 3.0e5, (1.0, 0.96, 0.9)); area("fill", (90, -40, 50), 80, 8e4, (0.8, 0.88, 1.0))
area("rim", (40, 70, 45), 50, 1.5e5, (0.9, 0.95, 1.0)); area("top", (8, -6, 120), 90, 4e4)
# --- camera
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.lens = 85; cam.data.sensor_width = 36; cam.data.clip_start = 1; cam.data.clip_end = 5000
ct = cam.constraints.new("TRACK_TO"); ct.target = tgt; ct.track_axis = "TRACK_NEGATIVE_Z"; ct.up_axis = "UP_Y"
def aim(center, az, el, radius, ortho=False, frac=1.0):
    tgt.location = center
    cam.data.type = "ORTHO" if ortho else "PERSP"
    d = radius / math.sin(math.atan(18 / 85)) * frac if not ortho else 400
    if ortho: cam.data.ortho_scale = radius * 2 * frac
    a, e = math.radians(az), math.radians(el)
    cam.location = center + mathutils.Vector((d * math.cos(e) * math.sin(a), -d * math.cos(e) * math.cos(a), d * math.sin(e)))
    bpy.context.view_layer.update()
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = int(160 * Q) if Q < 1 else 160; sc.cycles.use_denoising = True
sc.render.resolution_x = W_PX; sc.render.film_transparent = False
sc.render.threads = 16; sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "None"; sc.view_settings.exposure = 0.0
def render(name, h_px):
    sc.render.resolution_y = int(h_px * Q); sc.render.filepath = f"{OUT}/{name}.png"; bpy.ops.render.render(write_still=True); print("wrote", name)
cx = 7.8
cen = lambda zc: mathutils.Vector((cx, -6.0, zc))
extras = []
def clear():
    for o in extras: bpy.data.objects.remove(o, do_unlink=True)
    extras.clear()
def tube(a, b, r, m):
    a, b = mathutils.Vector(a), mathutils.Vector(b); d = b - a
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=d.length, location=(a + b) / 2, vertices=12)
    o = bpy.context.object; o.rotation_euler = d.to_track_quat("Z", "Y").to_euler(); o.data.materials.append(m); extras.append(o); return o
for v in VIEWS:
    clear(); place_P(0); fl.location.x = 0
    if v == "iso":
        aim(cen((lo[2] + hi[2]) / 2), 35, 32, 11.5, frac=0.95); render("stack_iso_34", 1250)
        aim(cen((lo[2] + hi[2]) / 2), -145, 28, 11.5, frac=0.95); render("stack_iso_rear", 1250)
    elif v == "under":
        pass
    elif v == "exploded":
        place_P(EXP); bpy.context.view_layer.update()
        lo2, hi2 = bounds([o for o in bpy.data.objects if o.type == "MESH" and o.name != "floor"])
        zmid = (lo2[2] + hi2[2]) / 2
        lm = mat("line", (0.2, 0.9, 1.0), 0, 0.5, (0.2, 0.9, 1.0))
        for x in (9.8 - 2.85, 9.8 + 2.85, 9.8):
            tube((x, -6.0, 0.35), (x, -6.0, GAP + EXP - 0.25), 0.035, lm)
        aim(cen(zmid), 38, 24, 12.5, frac=0.95); render("stack_exploded_4mm", 1400)
    elif v == "scale":
        qm = mat("coin", (0.72, 0.73, 0.75), 1.0, 0.3)
        bpy.ops.mesh.primitive_cylinder_add(radius=12.13, depth=1.75, location=(-24, -4, FLOOR + 0.875), vertices=128)
        q = bpy.context.object; q.data.materials.append(qm); extras.append(q)
        bpy.ops.mesh.primitive_torus_add(major_radius=11.2, minor_radius=0.25, location=(-24, -4, FLOOR + 1.76)); t = bpy.context.object; t.data.materials.append(qm); extras.append(t)
        rm = mat("ruler", (0.7, 0.71, 0.72), 1.0, 0.35); km = mat("tick", (0.02, 0.02, 0.02), 0, 0.6)
        bpy.ops.mesh.primitive_cube_add(size=1, location=(7.8 + 5, -34, FLOOR + 0.25)); r = bpy.context.object; r.scale = (80, 14, 0.5); r.data.materials.append(rm); extras.append(r)
        x0 = 7.8 + 5 - 40 + 3
        for i in range(0, 71):
            L = 5 if i % 10 == 0 else (3.2 if i % 5 == 0 else 2)
            bpy.ops.mesh.primitive_cube_add(size=1, location=(x0 + i, -34 + 7 - L / 2, FLOOR + 0.52)); k = bpy.context.object; k.scale = (0.12, L, 0.05); k.data.materials.append(km); extras.append(k)
            if i % 10 == 0:
                bpy.ops.object.text_add(location=(x0 + i - 0.8 * (1 if i < 100 else 2), -34 + 7 - 9.5, FLOOR + 0.52)); tx = bpy.context.object
                tx.data.body = str(i // 10); tx.data.size = 3.2; tx.data.materials.append(km); extras.append(tx)
        aim(mathutils.Vector((-3, -14, 1.0)), 18, 42, 40, frac=0.9); render("stack_scale_coin_ruler", 1200)
    elif v == "side":
        d = bpy.data.lights.new("front", "AREA"); d.size = 80; d.energy = 2.5e4
        fo = bpy.data.objects.new("front", d); sc.collection.objects.link(fo); fo.location = (cx, -140, 6); extras.append(fo)
        fo.rotation_euler = (math.radians(90), 0, 0)
        aim(cen((lo[2] + hi[2]) / 2), 24, 9, 9.5, frac=0.9); render("stack_side_low", 800)
        zc = (lo[2] + hi[2]) / 2
        aim(mathutils.Vector((cx, -6, zc)), 0, 0, 9.0, ortho=True, frac=0.95);         render("stack_side_section", 700)
        import json
        wc = world_to_camera_view; ppm = (wc(sc, cam, mathutils.Vector((cx, -6, 1))).y - wc(sc, cam, mathutils.Vector((cx, -6, 0))).y) * sc.render.resolution_y
        py = lambda z: (1 - wc(sc, cam, mathutils.Vector((cx, -6, z))).y) * sc.render.resolution_y
        json.dump({"top": py(hi[2]), "bottom": py(lo[2]), "mtop": py(0.0), "pinner": py(GAP), "ptop": py(0.761 + GAP), "mbot": py(-0.79), "ppm": ppm,
                   "h": hi[2] - lo[2], "zhi": hi[2], "zlo": lo[2], "W": W_PX, "H": sc.render.resolution_y}, open(f"{OUT}/side_px.json", "w"))
    elif v == "boards":
        for n, other in (("P", "M"), ("M", "P")):
            for o in kids[other]: o.hide_render = True
            for o in kids[n]: o.hide_render = False
            for face in ("up_F", "up_B"):
                r = roots[n]; flipped = face == "up_B"
                r.rotation_euler = (math.pi if flipped else 0, 0, 0); r.location = (0, -H if flipped else 0, 0); bpy.context.view_layer.update()
                blo, bhi = bounds([o for o in kids[n] if o.type == "MESH"]); r.location.z -= blo[2]; fl.location.z = -0.001; bpy.context.view_layer.update()
                blo, bhi = bounds([o for o in kids[n] if o.type == "MESH"])
                nm = {"P_up_B": "board_P_outer_top_MCU", "P_up_F": "board_P_inner_face_plug", "M_up_F": "board_M_inner_face_mic", "M_up_B": "board_M_belly_dock_button"}[f"{n}_{face}"]
                aim(mathutils.Vector((7.75, -6, 0.5)), 12, 52, 10.2, frac=1.12); render(nm, 1250)
        for o in kids["M"] + kids["P"]: o.hide_render = False
