"""Full exploded view of the CURRENT K4 pod (K4_RELIEF=lift default): tub, lid, cell, real routed boards P + M, switch puck + skin, VHB/tape, dock magnets + M tab,
battery/arm wires, plus the r2 strut arm + transducer pad CAD (out/k4final); tub/lid from out/k4s_lift_soft (needs K4_SPINE=soft K4_RELIEF=lift shell_k4.py). Explode along the stack axis (pod Y = thickness, shown vertical).
    systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 ~/.claude-shared/board/tools/blender-safe.sh --timeout 900 -- -b -P hw/mech/render_k4_exploded.py
Needs hw/mech/out/k4r_lift (shell_k4.py + k4_real_boards.py). -> docs/diagrams/k4-review/exploded-full.png (labels composited with PIL).
"""
import sys, json, math
from pathlib import Path
HERE = Path(__file__).resolve().parent if "__file__" in globals() else Path("hw/mech")
sys.path.insert(0, str(HERE)); sys.path.insert(0, "/home/hrafnavalkyrja/Desktop/blender-skills/tools")
import dims_k4 as K
OUT = HERE.parent.parent / "docs" / "diagrams" / "k4-review" / "exploded-full.png"
D = HERE / "out" / ("k4r_lift" if K.RELIEF == "lift" else "k4r")
FIN = HERE / "out" / "k4final"          # r2 strut + pad CAD in the K4 frame
DS = HERE / "out" / "k4s_lift_soft"       # restored exterior: shell_k4 K4_SPINE=soft
W, Hh = 2600, 2000
# explode offsets along pod +Y (mm); cell, wires ride with M so their joints stay readable
OFF = dict(tub=0, dock_mags=9, m_tab=15, board_P=22, ctape=24, board_M=30, cell=30, bat_wires=30, arm_wires=30, vhb=37, lid=45, puck=51, skin=57, strut=-9, xdcr=-16)
HEX = dict(tub="#4a4d55", lid="#8d7ff0", board_M="#5b9ff2", board_P="#52d39e", cell="#f28c3f", bat_wires="#e8e8e5", arm_wires="#ff6d6c", dock_mags="#a4a9b0",
           m_tab="#a19d8d", vhb="#f58a5c", ctape="#f58a5c", skin="#a19d8d", puck="#a4a9b0", strut="#a4a9b0", xdcr="#35b535")

def srgb(h):
    h = h.lstrip("#"); return tuple(((int(h[i:i + 2], 16) / 255) ** 2.2) for i in (0, 2, 4)) + (1,)

def main():
    import bpy
    from mathutils import Vector
    from bpy_extras.object_utils import world_to_camera_view
    from bpyhelp import safe
    safe.assert_version(); safe.reset_scene()
    s = bpy.context.scene
    root = bpy.data.objects.new("root", None); bpy.context.collection.objects.link(root); root.rotation_euler = (math.pi / 2, 0, 0)
    objs, bbox = {}, {}
    def mat(name, hexc, rough=0.45, metal=0.0):
        m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = srgb(hexc); b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
        return m
    def reg(n, o, hexc, **kw):
        o.name = n; o.data.materials.append(mat(n, hexc, **kw)); o.parent = root
        o.location.y += OFF.get(n, 0) * 0.001
        bpy.context.view_layer.update(); vs = [o.matrix_local @ Vector(c) for c in o.bound_box]
        bbox[n] = (Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs))), Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs))))
        objs[n] = o
    def imp(path):
        bpy.ops.wm.stl_import(filepath=str(path), global_scale=0.001); return bpy.context.selected_objects[0]
    for n in OFF:
        if n in ("strut", "xdcr"): continue
        o = imp((DS if n in ("tub", "lid") else D) / f"{n}.stl")
        m = {"dock_mags": 0.35, "puck": 0.35}.get(n, 0.45)
        reg(n, o, HEX[n], rough=m, metal=0.8 if n in ("dock_mags", "puck") else 0.0)
        o.data.polygons.foreach_set("use_smooth", [False] * len(o.data.polygons))
    hx, hy, hz = K.HEEL_EXIT
    # r2 strut arm (niti.stl, O11) + r2 transducer pad (hex/ring pad CAD, O8), same K4-frame files as exterior-old-vs-new.png
    reg("strut", imp(FIN / "niti.stl"), HEX["strut"], rough=0.3, metal=0.9)
    PADP = dict(pad_cup="#4a4d55", pad_cap="#8d7ff0", contact="#3a3a3f", diffuser="#9fd6ff", transducer="#35b535", pad_board="#52d39e")
    lo_, hi_ = None, None
    for k, hc in PADP.items():
        o = imp(FIN / f"{k}.stl"); o.name = k; o.data.materials.append(mat(k, hc, 0.4)); o.parent = root; o.location.y += OFF["xdcr"] * 0.001; objs[k] = o
    bpy.context.view_layer.update()
    vs = [objs[k].matrix_local @ Vector(c) for k in PADP for c in objs[k].bound_box]
    bbox["xdcr"] = (Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs))), Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs))))
    # assembly tie lines (home -> exploded) through each part's bbox centre, plus the arm-wire joints
    def line(a, b, hexc="#a4a9b0", r=0.00011):
        a, b = Vector(a), Vector(b); d = b - a
        bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=d.length, location=(a + b) / 2)
        o = bpy.context.object; o.rotation_mode = "QUATERNION"; o.rotation_quaternion = d.to_track_quat("Z", "Y"); o.parent = root
        o.data.materials.append(mat("tie", hexc, 0.8)); return o
    for n, off in OFF.items():
        if off == 0 or n in ("bat_wires", "arm_wires", "skin"): continue
        lo, hi = bbox[n]; c = (lo + hi) / 2
        line((c.x, c.y - off * 0.001, c.z), (c.x, c.y, c.z))
    lo, hi = bbox["skin"]; c = (lo + hi) / 2; line((c.x, bbox["puck"][0].y + 0.006 - 0.0, c.z), (c.x, c.y, c.z))
    # arm wires: P pads (rear of stack) down to P F face; wire end down to heel mouth
    import numpy as np
    aw = objs["arm_wires"]; vs = np.array([(aw.matrix_local @ v.co)[:] for v in aw.data.vertices])
    print("arm_wires local bbox", vs.min(0), vs.max(0))
    p_end = vs[vs[:, 0] < vs[:, 0].min() + 0.0006]; pe = p_end.mean(0)
    line((pe[0], bbox["board_P"][1].y, pe[2]), (pe[0], pe[1], pe[2]), "#ff6d6c", 0.00014)
    he = vs[vs[:, 0] > vs[:, 0].max() - 0.0006].mean(0)
    line((he[0], hy * 0.001, he[2]), (he[0], he[1], he[2]), "#ff6d6c", 0.00014)
    # lighting + camera (black world, Standard view transform)
    s.world = bpy.data.worlds.new("w"); s.world.use_nodes = True
    bg = s.world.node_tree.nodes["Background"]; bg.inputs["Color"].default_value = (0, 0, 0, 1); bg.inputs["Strength"].default_value = 0.0
    s.view_settings.view_transform = "Standard"; s.view_settings.look = "None"
    bpy.context.view_layer.update()
    allv = [root.matrix_world @ v for lo_hi in bbox.values() for v in lo_hi]
    ctr = sum(allv, Vector()) / len(allv)
    def light(name, loc, e, size, col=(1, 1, 1)):
        L = bpy.data.lights.new(name, "AREA"); L.energy, L.size, L.color = e, size, col
        o = bpy.data.objects.new(name, L); bpy.context.collection.objects.link(o); o.location = loc
        o.rotation_euler = (ctr - o.location).to_track_quat("-Z", "Y").to_euler()
    light("key", ctr + Vector((-0.10, -0.16, 0.14)), 0.9, 0.12); light("fill", ctr + Vector((0.14, -0.12, 0.02)), 0.35, 0.12, (0.8, 0.88, 1.0))
    light("rim", ctr + Vector((0.0, 0.14, 0.10)), 0.5, 0.12, (0.9, 0.85, 1.0)); light("top", ctr + Vector((0.0, -0.02, 0.2)), 0.4, 0.14)
    cam = bpy.data.cameras.new("cam"); cam.type = "ORTHO"; co = bpy.data.objects.new("cam", cam); bpy.context.collection.objects.link(co)
    d = Vector((0.30, -1.0, 0.62)).normalized()
    co.location = ctr + d * 0.5; co.rotation_euler = (ctr - co.location).to_track_quat("-Z", "Y").to_euler()
    s.camera = co; s.render.resolution_x, s.render.resolution_y = W, Hh
    cam.ortho_scale = 0.2
    def proj(p):
        q = world_to_camera_view(s, co, p); return Vector((q.x * W, (1 - q.y) * Hh))
    bpy.context.view_layer.update()
    pts = [proj(v) for v in allv]
    xs = [p.x for p in pts]; ys = [p.y for p in pts]
    for _ in range(2):   # fit the pod into the central ~52 % of the width, ~84 % of the height
        ex, ey = (max(xs) - min(xs)) / W, (max(ys) - min(ys)) / Hh
        cam.ortho_scale *= max(ex / 0.50, ey / 0.82)
        bpy.context.view_layer.update()
        pts = [proj(v) for v in allv]; xs = [p.x for p in pts]; ys = [p.y for p in pts]
        sh = ((min(xs) + max(xs)) / 2 - W / 2) / W; shy = ((min(ys) + max(ys)) / 2 - Hh / 2) / Hh
        cam.shift_x += sh * (1.0); cam.shift_y -= shy * (Hh / W)
        bpy.context.view_layer.update(); pts = [proj(v) for v in allv]; xs = [p.x for p in pts]; ys = [p.y for p in pts]
    s.render.engine = "CYCLES"; s.cycles.samples = 128; s.cycles.use_denoising = True
    try: safe.enable_gpu_cycles()
    except Exception as e: print("gpu", e)
    s.render.film_transparent = False; tmp = str(OUT.parent / "_exploded_raw.png"); s.render.filepath = tmp
    bpy.ops.render.render(write_still=True)
    # anchors (pod mm, exploded) -> screen px
    def A(n, x, y, z): return proj(root.matrix_world @ Vector((x, (y + OFF.get(n, 0)), z)) * 0.001) if False else proj(root.matrix_world @ (Vector((x, y + OFF.get(n, 0), z)) * 0.001))
    bm, bp = bbox["board_M"], bbox["board_P"]
    def dims(n):
        lo, hi = bbox[n]; return [(hi.x - lo.x) * 1000, (hi.y - lo.y) * 1000, (hi.z - lo.z) * 1000]
    sx, sy, sz = dims("strut"); qx, qy, qz = dims("xdcr")
    mL, mT, mH = dims("board_M"); pL, pT, pH = dims("board_P")
    L = [
        ("1  Tub (printed resin shell)", f"outer {K.L:.1f} x {K.T:.1f} x {K.H:.2f} mm (L x T x H), wall {K.WALL}", A("tub", 52, 10.0, K.Z1 - 0.3)),
        ("2  Lid (1.0 mm) + plate, trace, hex boss, soft spine", f"duct bore D{K.DUCT_D}, tube D{K.DUCT_TUBE_D}; switch pocket {K.POCKET['dx']}x{K.POCKET['dz']}", A("lid", 40, 10.2, 4.8)),
        ("3  Switch skin (silicone) over puck", "sealed button cap, outer face of lid", A("skin", 24, 10.65, -2.1)),
        ("4  Plunger puck (metal)", f"L {K.PUCK_L:.2f}, head D{K.PUCK_D}; presses SW1 on M", A("puck", 23.8, 10.0, -2.1)),
        ("5  VHB ring (tape)", f"{K.VHB_T} mm, bonds M to lid ledge tip", A("vhb", 26, 8.9, 1.8)),
        ("6  Board M (real routed STEP)", f"{mL:.1f} x {mH:.1f} mm, 0.8 thick; carries SW1, mic U2, pads", A("board_M", 29, 8.9, 3.0)),
        ("7  Mic U2 + port", f"port bore D{K.MIC_HOLE_D}, at pod x {K.MIC[0]:.2f}, z {K.MIC[1]:.2f}", A("board_M", K.MIC[0], 7.2, K.MIC[1])),
        ("8  Switch SW1 (on M)", f"actuator at pod x {K.SW[0]:.2f}, z {K.SW[1]:.2f}", A("board_M", K.SW[0], 9.5, K.SW[1])),
        ("9  Board P (real routed STEP)", f"{pL:.1f} x {pH:.1f} mm; MCU U1 on outer face, BM28 board-to-board to M", A("board_P", 26, 7.2, -3.5)),
        ("10  Cell Renata ICP401230UPR", f"130 mAh, {K.CELL_SPEC['L']:.1f} x {K.CELL_SPEC['W']:.1f} x {K.CELL_SPEC['T']:.1f} mm, 3.5 g", A("cell", 52, 9.5, 4.8)),
        ("11  Cell tape (transfer, 0.1)", "peel to swap the cell", A("ctape", 50, 5.0, 4.4)),
        ("12  Battery leads (AWG30)", "BAT+/GND/NTC: M pads to cell front", A("bat_wires", 28, 7.5, 2.9)),
        ("13  Arm wires x4 (OUT_A/B, LED+/-)", f"OD {K.WIRE_OD}, lane under stack and cell, to heel channel", A("arm_wires", 50, 5.2, -8.85)),
        ("14  Dock magnets (x2) + M pad tab", "charging dock; tab runs under the cell", A("dock_mags", 25, 9.6, -9.0)),
        ("15  NiTi spring arm (r2 CAD, O11)", f"{sx:.1f} x {sy:.1f} x {sz:.1f} mm; the printed strut is part of the pad cap (16)", A("strut", 61.2, 2.0, -8.0)),
        ("16  Transducer pad (r2 CAD, O8 ring)", f"{qx:.1f} x {qy:.1f} x {qz:.1f} mm; cup, cap, ring diffuser, contact, transducer", A("xdcr", 70.5, 3.0, -22.0)),
    ]
    # fix label 14 anchor to the tab / magnets (m_tab offset differs)
    L[13] = (L[13][0], L[13][1], A("dock_mags", 22.5, 9.0, -9.0))
    json.dump(dict(L=[(t, sb, a.x, a.y) for t, sb, a in L], tmp=tmp, pts=[(p.x, p.y) for p in pts]), open(str(OUT.parent / "_exploded_lbl.json"), "w"))

def composite():
    import random
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    j = json.load(open(str(OUT.parent / "_exploded_lbl.json"))); tmp = j["tmp"]
    im = Image.open(tmp).convert("RGB"); d = ImageDraw.Draw(im)
    f = lambda sz, b=False: ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf" % ("-Bold" if b else ""), sz)
    a_ = np.asarray(im).max(2) > 14                      # geometry mask (black world)
    cols = np.where(a_.any(0))[0]; gx0, gx1 = int(cols.min()), int(cols.max())
    colL, colR = gx0 - 40, gx1 + 40                      # all text stays outside [colL, colR]; leaders start at the column edge
    wl, wr = colL - 40, im.width - colR - 40
    def wrap(txt, fnt, w):
        out, cur = [], ""
        for wd in txt.split():
            t = (cur + " " + wd).strip()
            if d.textlength(t, fnt) <= w or not cur: cur = t
            else: out.append(cur); cur = wd
        return out + [cur]
    items = []
    for t, sb, x, y in j["L"]:
        items.append(dict(t=t, sb=sb, a=(x, y)))
    def block(it, w):
        tl = wrap(it["t"], f(27, True), w); sl = wrap(it["sb"], f(21), w)
        return tl, sl, len(tl) * 33 + len(sl) * 27 + 8
    def layout(assign):                                  # assign: (left list, right list) of item idx, in slot order
        res = {}
        for side, lst in zip("lr", assign):
            w = wl if side == "l" else wr
            hs = [block(items[i], w)[2] for i in lst]; top, bot = 170, im.height - 60
            gap = min(34, (bot - top - sum(hs)) / max(len(lst) - 1, 1)); y = top
            for i, h in zip(lst, hs):
                res[i] = (side, y, h); y += h + gap
        return res
    def leaders(res):
        L = {}
        for i, (side, y, h) in res.items():
            tl, sl, _ = block(items[i], wl if side == "l" else wr)
            L[i] = ((colL if side == "l" else colR), y + 16, items[i]["a"])
        return L
    def inter(p, q, r, s_):
        def o(a, b, c): return (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
        return o(p, q, r) * o(p, q, s_) < 0 and o(r, s_, p) * o(r, s_, q) < 0
    def cost(assign):
        res = layout(assign)
        if any(y + h > im.height - 20 for _, y, h in res.values()): return 1e12
        L = leaders(res); ks = list(L); c = 0
        for m in range(len(ks)):
            (x0, y0, a0) = L[ks[m]]; c += ((a0[0]-x0)**2 + (a0[1]-y0)**2) ** 0.5
            for n in range(m + 1, len(ks)):
                (x1, y1, a1) = L[ks[n]]
                if inter((x0, y0), a0, (x1, y1), a1): c += 1e6
        return c
    mid = (gx0 + gx1) / 2
    left = sorted([i for i, it in enumerate(items) if it["a"][0] < mid], key=lambda i: items[i]["a"][1])
    right = sorted([i for i, it in enumerate(items) if it["a"][0] >= mid], key=lambda i: items[i]["a"][1])
    best = (left, right); bc = cost(best); rnd = random.Random(3)
    for _ in range(30000):
        l, r = list(best[0]), list(best[1]); k = rnd.random()
        if k < 0.5 and len(l) > 1: i, jx = rnd.sample(range(len(l)), 2); l[i], l[jx] = l[jx], l[i]
        elif k < 0.8 and len(r) > 1: i, jx = rnd.sample(range(len(r)), 2); r[i], r[jx] = r[jx], r[i]
        else:
            if rnd.random() < 0.5 and l: v = l.pop(rnd.randrange(len(l))); r.insert(rnd.randrange(len(r) + 1), v)
            elif r: v = r.pop(rnd.randrange(len(r))); l.insert(rnd.randrange(len(l) + 1), v)
        c = cost((l, r))
        if c < bc: best, bc = (l, r), c
    print("leader cost", bc, "crossings", int(bc // 1e6), "geometry x", gx0, gx1)
    res = layout(best); L = leaders(res); OR = (242, 140, 63)
    for i, (side, y, h) in res.items():
        tl, sl, _ = block(items[i], wl if side == "l" else wr); yy = y
        xr = colL if side == "l" else colR
        for ln in tl:
            tx = (colL - d.textlength(ln, f(27, True))) if side == "l" else colR; d.text((tx, yy), ln, fill=(232, 232, 229), font=f(27, True)); yy += 33
        for ln in sl:
            tx = (colL - d.textlength(ln, f(21))) if side == "l" else colR; d.text((tx, yy), ln, fill=(164, 169, 176), font=f(21)); yy += 27
        x0, y0, a = L[i]
        d.line([(x0 + (8 if side == "l" else -8), y0), a], fill=OR, width=2); d.ellipse([a[0]-6, a[1]-6, a[0]+6, a[1]+6], outline=OR, width=3)
    d.text((40, 30), "K4 pod, exploded along the stack axis (pod thickness, shown vertical). Current design: K4_RELIEF=lift", fill=(232, 232, 229), font=f(36, True))
    for k, ln in enumerate(["Real routed boards P + M (STEP). Shell + lid carry the restored exterior (plate, trace, hex boss, soft spine). NiTi arm and pad (with its printed strut) are the r2 CAD placed at the K4 heel.",
                            "STILL APPROXIMATE: cell, cell tape and M tab are box placeholders; battery/arm wires are routed paths; the pad is shown assembled (6 sub-parts) and not re-fitted to K4. Grey lines = assembly paths. All dims mm."]):
        d.text((40, 82 + 32 * k), ln, fill=(164, 169, 176), font=f(22))
    im.save(OUT, optimize=True); Path(tmp).unlink(); Path(OUT.parent / "_exploded_lbl.json").unlink()

if __name__ == "__main__" and "--composite" in sys.argv:
    composite()
else:
    try:
        import bpy
    except ImportError:
        bpy = None
    if bpy:
        main()
        import subprocess; subprocess.run(["/usr/bin/python3", str(Path(__file__).resolve()), "--composite"], check=True)
