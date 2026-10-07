"""Printable ENVELOPE DUMMIES of the pod size concepts (verification item V7, docs/research/drastic/synthesis.md §3).

    source tools/env.sh && systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 \
        python3 hw/mech/dummies.py      # -> hw/mech/out/dummies/*.stl + dummies.json; docs/diagrams/size-dummies.png

Why: owner rule O27 (thin first, then height, length last) is judged in the hand on her glasses, not on paper.
What each dummy is: the OUTER envelope only (solid), in the same pod frame as hw/mech/shell_r2.py
(x fwd->rear from X0 29.5, y out from the adapter face Y_IN 4.3, z up from the bottom Z0 -9.7), same 1.0 mm edge
chamfers, dock belly under the front, and the SAME glasses interface as shell_r2: blade.rail() (male dovetail on
the inner face, x 36-62) + its catch bump, so the existing frame adapter (blade.adapter()) slides on and latches.
Not modelled: heel / NiTi arm / pad (outside the envelope, same for every concept), the r1 'spine' top
(styling, 160 mm3, not in any concept's T/H), seam, ports, switch.
Two STLs per concept: <id>.stl (solid, size feel only) and <id>_ballast.stl (an open-bottom pocket where the cell
sits; fill with steel shot / M2 nuts until the scale reads the engraved pod mass, seal with tape or a glue drop).
Engraved on the inner face (under the adapter): concept + T on the line above the rail; target pod mass below it.

Sources (read 2026-10-07): synthesis.md §1/§2 tables (T/H/L, env mm3, mass incl. pad 2.19 g + adapter 417 mm3);
sim/checks/size_budget.py (thin-dock belly 2.0 + 0.75 tails - (wall + 0.8 slack), length 24.0; pad/adapter masses);
hw/mech/dims_r2.py (MZ-2 cell box). Cell boxes for K1-K3/OU4 follow the size_budget stack (wall | tape 0.3 | cell).
"""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

import numpy as np
from build123d import Box, Plane, Pos, Text, chamfer, export_stl, extrude

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "tools"))
import blade  # noqa: E402
import dims as D  # noqa: E402  (selected design: dims_r2 | dims_k1)

OUT = HERE / "out" / "dummies"
PNG = ROOT / "docs" / "diagrams" / "size-dummies.png"

X0, Y_IN, Z0, CH = D.X0, D.Y_IN, D.Z0, 1.0
RHO_RESIN = 1.18e-3            # g/mm3, solid resin print (size_budget RHO)
RHO_BALLAST = 4.5e-3           # g/mm3, loose steel shot / M2 nuts (~57 % of steel 7.85) [A]
POCKET_MARGIN = 1.4            # pocket volume x 1.4: room for a lighter print or a looser fill
PAD_G, ADAPTER_G = 2.19, round(417.0 * RHO_RESIN, 2)    # size_budget.scenario parts list (not on the dummy)
THIN_BELLY = dict(L=24.0, d=lambda wall: round(2.0 + 0.75 - (wall + 0.8), 2))   # DOCKS['thin'], s_fixed 0.8

# total_g = synthesis §2 'mass' (whole pod on the glasses incl. pad + adapter); pod_g = total - pad - adapter
# cell = (x0, len, y-thick, z-height); cell sits wall+0.3 in from the front and the inner face, 0.8 slack under it
CONCEPTS = [
    dict(id="MZ2", name="Phase-2 MZ-2", T=10.40, H=14.5, L=38.0, env=6259, total_g=11.92, wall=0.8, real=True,
         cell=dict(x0=D.CELL["x0"], L=35.0, T=5.3, H=12.0), cell_name="175 mAh ICP501233PA-02",
         src="synthesis §2 row 1; shell_r2.outer_body + armour plate (the real exterior)"),
    dict(id="K1", name="K1 right-size", T=8.5, H=14.8, L=33.6, env=4544, total_g=10.0, wall=0.6,
         cell=dict(front=True, L=31.0, T=4.5, H=12.7), cell_name="130 mAh ICP401230UPR", src="synthesis §2 K1"),
    dict(id="K2", name="K2 thin cell, stacked", T=7.3, H=14.1, L=33.1, env=3691, total_g=8.4, wall=0.6,
         cell=dict(front=True, L=30.5, T=3.3, H=10.2), cell_name="68 mAh ICP281029HPG", src="synthesis §2 K2"),
    dict(id="K3", name="K3 end-to-end", T=5.6, H=14.9, L=40.1, env=3563, total_g=7.5, wall=0.6,
         cell=dict(front=True, L=21.0, T=3.7, H=12.8), cell_name="50 mAh ICP331319PM (front; rear is equally possible)",
         src="synthesis §2 K3 (env excludes wire stowage ~+100-140)"),
    dict(id="OU4", name="OU4 over-under", T=5.6, H=19.2, L=38.0, env=4272, total_g=8.9, wall=0.8,
         cell=dict(front=True, L=30.5, T=3.3, H=10.2), cell_name="68 mAh ICP281029HPG (board strip above)",
         src="synthesis §1 run OU4; mass [E Claude 2026-10-07: K2 8.4 + walls 0.8 on a larger shell +0.72 - board 35x6 vs 30x12 0.22]"),
]


def box(x0, x1, y0, y1, z0, z1):
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(x1 - x0, y1 - y0, z1 - z0)


def frame_of(c):
    """Outer-envelope extents in the pod frame + belly + cell box for one concept."""
    x1, y1, z1 = X0 + c["L"], Y_IN + c["T"], Z0 + c["H"]
    if c.get("real"):
        belly = dict(d=D.BELLY_D, L=D.X_BELLY - X0)
        cell = dict(x0=D.CELL["x0"], x1=D.CELL["x1"], y0=D.CELL["y0"], y1=D.CELL["y1"], z0=D.CELL["z0"], z1=D.CELL["z1"])
    else:
        w = c["wall"]
        belly = dict(d=THIN_BELLY["d"](w), L=THIN_BELLY["L"])
        k = c["cell"]
        cx0 = X0 + w + 0.3
        cell = dict(x0=cx0, x1=cx0 + k["L"], y0=Y_IN + w + 0.3, y1=Y_IN + w + 0.3 + k["T"], z0=Z0 + w + 0.8, z1=Z0 + w + 0.8 + k["H"])
    return dict(x1=x1, y1=y1, z1=z1, belly=belly, cell=cell)


def envelope(c, f):
    if c.get("real"):
        import shell_r2 as S
        from styles import plate
        return S.outer_body() + plate(S.PLATE_PTS, D.Y_OUT, D.PLATE_T, 0.3)
    main = chamfer(box(X0, f["x1"], Y_IN, f["y1"], Z0, f["z1"]).edges(), CH)
    b = f["belly"]
    belly = chamfer(box(X0, X0 + b["L"], Y_IN, f["y1"], Z0 - b["d"], Z0 + 1.5).edges(), CH)
    return main + belly


def engrave(c, f, pod_g):
    """Text cut 0.3 deep into the inner face, readable from the temple side (viewer looks along +y)."""
    def line(s, xc, zc, size):
        pl = Plane(origin=(xc, Y_IN - 0.01, zc), x_dir=(1, 0, 0), z_dir=(0, -1, 0))
        return extrude(pl * Text(s, font_size=size), amount=-0.31)
    xc = (blade.RAIL_X[0] + min(blade.RAIL_X[1], f["x1"] - 1.5)) / 2
    z_top_band = (blade.ZC + blade.RAIL_W1 / 2 + f["z1"] - CH) / 2          # between rail top and the top chamfer
    z_bot_band = (Z0 + CH + blade.ZC - blade.RAIL_W1 / 2) / 2               # between bottom chamfer and rail
    size_top = min(1.8, (f["z1"] - CH - (blade.ZC + blade.RAIL_W1 / 2)) - 0.5)
    return (line(f"{c['id']} T{c['T']:.1f}", xc, z_top_band, size_top)
            + line(f"{pod_g:.1f} g", xc, z_bot_band, 2.0))


def pocket(c, f, body, vol_needed):
    """Open-bottom pocket in the cell's footprint (>= 1.0 to the inner face and outer face, >= 1.5 to the ends).
    Height solved so pocket & body = vol_needed."""
    k = f["cell"]
    x0, x1 = max(k["x0"], X0 + 1.5), min(k["x1"], f["x1"] - 1.5)
    y0, y1 = max(k["y0"], Y_IN + 1.0), min(k["y1"], f["y1"] - 1.0)
    zb = Z0 - f["belly"]["d"] - 1.0
    lo, hi = Z0 + 0.3, min(k["z1"], f["z1"] - 1.0)
    full = (box(x0, x1, y0, y1, zb, hi) & body).volume
    if full < vol_needed:
        lo = hi
    for _ in range(30):
        if hi - lo < 0.02:
            break
        m = (lo + hi) / 2
        if (box(x0, x1, y0, y1, zb, m) & body).volume < vol_needed:
            lo = m
        else:
            hi = m
    zt = hi
    return box(x0, x1, y0, y1, zb, zt), dict(x=[round(x0, 2), round(x1, 2)], y=[round(y0, 2), round(y1, 2)],
                                            z_top=round(zt, 2), width_y=round(y1 - y0, 2), capped=full < vol_needed)


def stl_check(path):
    """Binary STL: closed 2-manifold (every edge shared by exactly 2 facets) and consistent orientation."""
    b = Path(path).read_bytes()
    n = struct.unpack("<I", b[80:84])[0]
    a = np.frombuffer(b[84:84 + 50 * n], dtype=np.dtype([("n", "<3f4"), ("v", "<9f4"), ("a", "<u2")]))
    v = np.round(a["v"].reshape(-1, 3).astype(float), 4)
    _, idx = np.unique(v, axis=0, return_inverse=True)
    t = idx.reshape(-1, 3)
    e = np.concatenate([t[:, [0, 1]], t[:, [1, 2]], t[:, [2, 0]]])
    und = np.sort(e, axis=1)
    _, cnt = np.unique(und, axis=0, return_counts=True)
    _, dcnt = np.unique(e, axis=0, return_counts=True)
    return dict(facets=int(n), manifold=bool((cnt == 2).all()), oriented=bool((dcnt == 1).all()))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for c in CONCEPTS:
        f = frame_of(c)
        env = envelope(c, f)
        env_v = env.volume
        pod_g = round(c["total_g"] - PAD_G - ADAPTER_G, 2)
        solid = env + blade.rail() - engrave(c, f, pod_g)
        print_g = solid.volume * RHO_RESIN
        need_g = pod_g - print_g
        v_need = max(0.0, need_g) / (RHO_BALLAST - RHO_RESIN) * POCKET_MARGIN
        res = dict(id=c["id"], name=c["name"], T=c["T"], H=c["H"], L=c["L"], belly_d=f["belly"]["d"], belly_L=f["belly"]["L"],
                   env_doc_mm3=c["env"], env_dummy_mm3=round(env_v), total_g_doc=c["total_g"], pod_g_target=pod_g,
                   solid_print_g=round(print_g, 2), ballast_g_nominal=round(max(0, need_g), 2), cell=c["cell_name"], src=c["src"])
        files = {f"{c['id']}.stl": solid}
        if v_need > 0:
            cut, info = pocket(c, f, env, v_need)
            bal = solid - cut
            res["pocket"] = dict(info, vol_mm3=round((cut & env).volume), holds_g_steel=round((cut & env).volume * RHO_BALLAST, 2))
            files[f"{c['id']}_ballast.stl"] = bal
        bb = env.bounding_box()
        res["bbox_check"] = dict(T=round(bb.max.Y - bb.min.Y, 2), L=round(bb.max.X - bb.min.X, 2), H_with_belly=round(bb.max.Z - bb.min.Z, 2))
        res["files"] = {}
        for fn, s in files.items():
            p = OUT / fn
            export_stl(s, str(p), tolerance=0.01, angular_tolerance=0.1)
            res["files"][fn] = dict(solids=len(s.solids()), valid=bool(s.is_valid), volume=round(s.volume), **stl_check(p))
        res["frame"] = dict(x=[X0, round(f["x1"], 2)], y=[Y_IN, round(f["y1"], 2)], z=[round(Z0 - f["belly"]["d"], 2), round(f["z1"], 2)],
                            cell=f["cell"])
        rows.append(res)
        print(json.dumps({k: res[k] for k in ("id", "T", "H", "L", "env_dummy_mm3", "pod_g_target", "solid_print_g", "files")}))
    ok = all(v["solids"] == 1 and v["valid"] and v["manifold"] and v["oriented"] for r in rows for v in r["files"].values())
    (OUT / "dummies.json").write_text(json.dumps(dict(date="2026-10-07", all_one_valid_solid=ok, rows=rows), indent=1))
    print("ALL ONE VALID SOLID:", ok)
    plot(rows)
    return 0 if ok else 1


def _chamfered(u0, u1, v0, v1, ch=CH):
    return [(u0 + ch, v0), (u1 - ch, v0), (u1, v0 + ch), (u1, v1 - ch), (u1 - ch, v1), (u0 + ch, v1), (u0, v1 - ch), (u0, v0 + ch)]


def plot(rows):
    import plotstyle
    plt = plotstyle.apply()
    from matplotlib.patches import Polygon as MP, Rectangle
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(15, 8.2), gridspec_kw=dict(width_ratios=[1.7, 1.3]))
    gap_side, gap_end = 26.0, 15.0
    for i, r in enumerate(rows):
        col = plotstyle.SERIES[i]
        fr = r["frame"]
        dz = -i * gap_side
        x0, x1 = fr["x"]
        zb, z1 = Z0, fr["z"][1]
        # side view (x-z), seen from outside: front (hinge) at left
        a1.add_patch(MP(_chamfered(x0, x1, zb + dz, z1 + dz), closed=True, fc=col, ec=col, alpha=0.30, lw=1.4))
        a1.add_patch(MP(_chamfered(x0, x0 + r["belly_L"], zb - r["belly_d"] + dz, zb + 1.5 + dz), closed=True, fc=col, ec=col, alpha=0.30, lw=1.4))
        c = fr["cell"]
        a1.add_patch(Rectangle((c["x0"], c["z0"] + dz), c["x1"] - c["x0"], c["z1"] - c["z0"], fill=False, ec=plotstyle.TEXT_2, ls="--", lw=0.8))
        a1.add_patch(Rectangle((blade.RAIL_X[0], blade.ZC - blade.RAIL_W0 / 2 + dz), blade.RAIL_X[1] - blade.RAIL_X[0], blade.RAIL_W0,
                               fill=False, ec=plotstyle.GRID, lw=0.8, hatch="////"))
        a1.text(x1 + 2.0, (zb + z1) / 2 + dz + 5.0, r["name"], color=col, fontsize=10, weight="bold", va="center")
        a1.text(x1 + 2.0, (zb + z1) / 2 + dz - 1.5,
                f"T {r['T']:.1f} | H {r['H']:.1f} (+belly {r['belly_d']:.2f}) | L {r['L']:.1f} mm\n"
                f"{r['env_doc_mm3'] / 1000:.2f} cm³ (dummy {r['env_dummy_mm3'] / 1000:.2f}) | pod {r['pod_g_target']:.1f} g",
                color=plotstyle.TEXT, fontsize=8.5, va="center", linespacing=1.5)
        # end view (y-z) from the front: temple (0..2.5) + adapter (2.5..4.3) at left, pod outward to the right
        u = i * gap_end
        a2.add_patch(MP(_chamfered(Y_IN + u, fr["y"][1] + u, zb, z1), closed=True, fc=col, ec=col, alpha=0.30, lw=1.4))
        a2.add_patch(MP(_chamfered(Y_IN + u, fr["y"][1] + u, zb - r["belly_d"], zb + 0.99, ch=min(CH, r["belly_d"] / 2))[:4] + [(fr["y"][1] + u, zb + 1), (Y_IN + u, zb + 1)], closed=True, fc=col, ec=col, alpha=0.30, lw=1.4))
        a2.add_patch(Rectangle((0 + u, -2.5), 2.5, 5.0, fc=plotstyle.TEXT_2, ec="none", alpha=0.6))
        a2.add_patch(Rectangle((2.5 + u, -3.9), 1.8, 7.8, fc=plotstyle.GRID, ec=plotstyle.TEXT_2, lw=0.6))
        a2.text(u + (Y_IN + fr["y"][1]) / 2, 11.2, f"{r['id']}\nT {r['T']:.1f}", color=col, ha="center", fontsize=9, weight="bold")
        a2.text(u + (Y_IN + fr["y"][1]) / 2, -13.0, f"{fr['y'][1] - 2.5:.1f} off\ntemple*", color=plotstyle.TEXT_2, ha="center", fontsize=7.5, va="top")
    a1.set_title("Side view, outer face (front / hinge at left). Dashed = cell, hatched = dovetail rail (same on all)")
    a2.set_title("End view from the front: temple (grey) | adapter | pod", pad=34)
    for a in (a1, a2):
        a.set_aspect("equal")
        a.autoscale_view()
        a.grid(True)
        a.set_xlabel("mm")
    a1.set_xlim(26, 112)
    a1.set_ylim(-len(rows) * gap_side + 8, 12)
    a1.set_yticks([])
    a2.set_xlim(-1, len(rows) * gap_end + 1)
    a2.set_ylim(-17, 14.5)
    a2.set_yticks([])
    fig.suptitle("V7 size dummies, to scale (1 grid = 10 mm side / 5 mm end). O27: thin first, then height, length last",
                 color=plotstyle.TEXT, fontsize=11)
    fig.text(0.5, 0.01, "* mm from the temple's outer face incl. the 1.8 adapter, = y of the pod's outer face. "
             "Volumes: synthesis §2 envelope (incl. 160 mm³ spine), dummy = what prints (no spine). "
             "pod g = synthesis mass - pad 2.19 - adapter 0.49. OU4 mass [E].", color=plotstyle.TEXT_2, ha="center", fontsize=7.5)
    a2.xaxis.set_major_locator(plt.MultipleLocator(5))
    a1.xaxis.set_major_locator(plt.MultipleLocator(10))
    PNG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(PNG)
    print("wrote", PNG)


if __name__ == "__main__":
    sys.exit(main())
