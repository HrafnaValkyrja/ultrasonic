"""Check the redrawn PMCXB290UE footprint against Nexperia's land pattern and the old EasyEDA one.

New: hw/lib/pod.pretty/Nexperia_SOT1216_DFN1010B-6.kicad_mod
Old: hw/lib/lcsc/lcsc.pretty/SOT1216_L1.1-W1.0-P0.35-BL-EP.kicad_mod (EasyEDA, fetched via C552750)

Source of the expected numbers (accessed 2026-10-01):
  Nexperia PMCXB290UE data sheet v.1, 30 May 2023, Fig. 32 "Reflow soldering footprint for
  DFN1010B-6 (SOT1216)", issue 17-03-31, https://assets.nexperia.com/documents/data-sheet/PMCXB290UE.pdf
  (same figure as Fig. 2 of the SOT1216 package information, 8 Sep 2022,
  https://assets.nexperia.com/documents/outline-drawing/SOT1216.pdf)
  Lands 0.20 x 0.25 at pitch 0.35, rows 0.6 apart (outer 1.1); paste 0.20 x 0.35 (outer 1.2);
  resist 0.30 x 0.35; occupied area 1.35 x 1.30. No land for the exposed drain pads 7/8.

Checks: every pad number sits at the same physical place in old and new (so the schematic pin map
in hw/pod/gen.py carries over), the Fig. 32 numbers, and the minimum copper / resist / paste gaps.

Run:  source tools/env.sh && python3 sim/checks/sot1216_footprint.py
      (writes docs/diagrams/sot1216-footprint.png)
"""
import itertools
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import pcbnew  # noqa: E402
import plotstyle  # noqa: E402

NEW = (os.path.join(ROOT, "hw/lib/pod.pretty"), "Nexperia_SOT1216_DFN1010B-6")
OLD = (os.path.join(ROOT, "hw/lib/lcsc/lcsc.pretty"), "SOT1216_L1.1-W1.0-P0.35-BL-EP")
ROLE = {"1": "S_N (S1)", "2": "G_N (G1)", "3": "D_P (D2)", "4": "S_P (S2)",
        "5": "G_P (G2)", "6": "D_N (D1)", "7": "D_N (D1 pad)", "8": "D_P (D2 pad)"}
mm = pcbnew.ToMM


def rect(p, grow=0.0):
    """Axis-aligned (x0, y0, x1, y1) in mm of a rect pad (0/90/180/270 deg), grown by `grow`."""
    bb = p.GetBoundingBox()
    return (mm(bb.GetLeft()) - grow, mm(bb.GetTop()) - grow, mm(bb.GetRight()) + grow, mm(bb.GetBottom()) + grow)


def gap(a, b):
    dx = max(b[0] - a[2], a[0] - b[2], 0.0)
    dy = max(b[1] - a[3], a[1] - b[3], 0.0)
    return (dx * dx + dy * dy) ** 0.5


def load(lib, name):
    fp = pcbnew.FootprintLoad(lib, name)
    assert fp is not None, f"cannot load {lib}:{name}"
    cu, mask, paste = {}, {}, []
    for p in fp.Pads():
        ls = p.GetLayerSet()
        if ls.Contains(pcbnew.F_Cu):
            cu[p.GetNumber()] = rect(p)
            if ls.Contains(pcbnew.F_Mask):
                mask[p.GetNumber()] = rect(p, mm(p.GetLocalSolderMaskMargin() or 0))
            if ls.Contains(pcbnew.F_Paste):
                paste.append(rect(p, mm(p.GetLocalSolderPasteMargin() or 0)))
        elif ls.Contains(pcbnew.F_Paste):
            paste.append(rect(p))
    pts = [mm(v) for g in fp.GraphicalItems() if g.GetLayer() == pcbnew.F_CrtYd
           for q in (g.GetStart(), g.GetEnd()) for v in (q.x, q.y)]
    xs, ys = pts[0::2], pts[1::2]
    crt = (min(xs), min(ys), max(xs), max(ys))          # courtyard line centres
    return fp, cu, mask, paste, crt


def min_gap(rects):
    pairs = [(gap(a[1], b[1]), a[0], b[0]) for a, b in itertools.combinations(rects, 2)]
    return min(pairs)


def centre(r):
    return ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)


def size(r):
    return (r[2] - r[0], r[3] - r[1])


def main():
    new, old = load(*NEW), load(*OLD)
    ok = True
    for tag, (fp, cu, mask, paste, crt) in (("OLD", old), ("NEW", new)):
        print(f"\n{tag}  {fp.GetFPID().GetLibItemName()}")
        print(f"  {'pad':>3} {'role':<13} {'x':>7} {'y':>7} {'w':>5} {'h':>5}   resist w x h   on")
        for n in sorted(cu):
            (x, y), (w, h) = centre(cu[n]), size(cu[n])
            m = f"{size(mask[n])[0]:.2f} x {size(mask[n])[1]:.2f}" if n in mask else "covered     "
            print(f"  {n:>3} {ROLE[n]:<13} {x:7.3f} {y:7.3f} {w:5.2f} {h:5.2f}   {m}   "
                  f"{'Cu+mask' if n in mask else 'Cu only (under resist)'}")
        print(f"  paste apertures: {len(paste)}, sizes {sorted({tuple(round(v, 3) for v in size(r)) for r in paste})}")
        g, a, b = min_gap(list(cu.items()))
        print(f"  min copper gap  {g:.3f} mm ({a}-{b})")
        if mask:
            g, a, b = min_gap(list(mask.items()))
            print(f"  min resist web  {g:.3f} mm ({a}-{b})")
        g, _, _ = min_gap(list(enumerate(paste)))
        print(f"  min paste gap   {g:.3f} mm")
        print(f"  courtyard       {crt[2] - crt[0]:.2f} x {crt[3] - crt[1]:.2f} mm")

    # 1. same pad numbers, same physical spot (tolerance 0.01 mm)
    print("\nPin-to-position correspondence (old -> new):")
    _, cu_o, *_ = old
    _, cu_n, mask_n, paste_n, crt_n = new
    assert set(cu_o) == set(cu_n) == set(ROLE), (sorted(cu_o), sorted(cu_n))
    for n in sorted(cu_n):
        (xo, yo), (xn, yn) = centre(cu_o[n]), centre(cu_n[n])
        d = ((xo - xn) ** 2 + (yo - yn) ** 2) ** 0.5
        flag = "ok" if d <= 0.01 else "MISMATCH"
        ok &= d <= 0.01
        print(f"  pad {n} {ROLE[n]:<13} old ({xo:6.3f},{yo:6.3f})  new ({xn:6.3f},{yn:6.3f})  moved {d:.3f}  {flag}")

    # 2. Fig. 32 numbers
    def near(a, b):
        return abs(a - b) < 1e-3
    lands = [cu_n[n] for n in "123456"]
    checks = {
        "land 0.20 x 0.25": all(near(size(r)[0], 0.20) and near(size(r)[1], 0.25) for r in lands),
        "pitch 0.35, outer x 0.9": near(max(r[2] for r in lands) - min(r[0] for r in lands), 0.90),
        "rows: inner 0.6, outer 1.1": near(min(r[1] for r in lands if r[1] > 0) * 2, 0.6)
        and near(max(r[3] for r in lands) - min(r[1] for r in lands), 1.1),
        "resist 0.30 x 0.35": all(near(size(mask_n[n])[0], 0.30) and near(size(mask_n[n])[1], 0.35) for n in "123456"),
        "paste 0.20 x 0.35, outer 1.2, inner 0.5": len(paste_n) == 6
        and all(near(size(r)[0], 0.20) and near(size(r)[1], 0.35) for r in paste_n)
        and near(max(r[3] for r in paste_n) - min(r[1] for r in paste_n), 1.2)
        and near(min(r[1] for r in paste_n if r[1] > 0) * 2, 0.5),
        "drain pads 7/8 not soldered (no resist opening, no paste)": "7" not in mask_n and "8" not in mask_n,
        "courtyard encloses occupied area 1.35 x 1.30": crt_n[2] - crt_n[0] >= 1.35 and crt_n[3] - crt_n[1] >= 1.30,
    }
    print("\nNexperia Fig. 32:")
    for k, v in checks.items():
        ok &= v
        print(f"  {'PASS' if v else 'FAIL'}  {k}")

    draw(old, new)
    print("\nRESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def draw(old, new):
    plt = plotstyle.apply()
    from matplotlib.patches import Rectangle
    C_CU, C_MASK, C_PASTE, C_CRT, C_BODY = plotstyle.SERIES[3], plotstyle.SERIES[0], plotstyle.SERIES[2], plotstyle.SERIES[4], plotstyle.TEXT_2
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.8))
    titles = ("Old: EasyEDA SOT1216 (via C552750)", "New: Nexperia Fig. 32 land pattern")
    for ax, title, (fp, cu, mask, paste, crt) in zip(axes, titles, (old, new)):
        ax.add_patch(Rectangle((-0.55, -0.5), 1.1, 1.0, fill=False, ec=C_BODY, ls="--", lw=1))
        ax.add_patch(Rectangle((crt[0], crt[1]), crt[2] - crt[0], crt[3] - crt[1], fill=False, ec=C_CRT, lw=1))
        for r in mask.values():
            ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fill=False, ec=C_MASK, ls="-.", lw=1))
        for n, r in cu.items():
            under = n not in mask
            ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fc=C_CU, alpha=0.25 if under else 0.85,
                                   ec=C_CU, lw=0.8, hatch="//" if under else None))
            x, y = centre(r)
            ax.text(x, y, n, ha="center", va="center", fontsize=9, color=plotstyle.SURFACE if not under else plotstyle.TEXT,
                    fontweight="bold")
            if n in "123456":
                ax.text(x, y + (0.21 if y > 0 else -0.21), ROLE[n].split()[0], ha="center", va="center", fontsize=6.5,
                        color=plotstyle.TEXT)
        for r in paste:
            ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fill=False, ec=C_PASTE, lw=1.2))
        ax.plot([-0.75], [0.425], "o", color=plotstyle.TEXT, ms=5)
        ax.set_title(title)
        ax.set_xlim(-0.95, 0.95); ax.set_ylim(0.95, -0.95)   # KiCad: y down
        ax.set_aspect("equal"); ax.set_xlabel("x (mm), top view, pin 1 = dot")
    axes[0].set_ylabel("y (mm)")
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    handles = [Patch(fc=C_CU, ec=C_CU, label="copper land (soldered)"),
               Patch(fc=C_CU, alpha=0.25, ec=C_CU, hatch="//", label="copper under resist (7/8: drain pads, not soldered)"),
               Line2D([], [], color=C_MASK, ls="-.", label="resist opening"),
               Line2D([], [], color=C_PASTE, label="paste aperture"),
               Line2D([], [], color=C_BODY, ls="--", label="body 1.1 x 1.0"),
               Line2D([], [], color=C_CRT, label="courtyard")]
    fig.legend(handles=handles, loc="lower center", ncol=3, fontsize=7.5, labelcolor=plotstyle.TEXT)
    fig.subplots_adjust(bottom=0.24)
    out = os.path.join(ROOT, "docs/diagrams/sot1216-footprint.png")
    fig.savefig(out)
    print("wrote", out)


if __name__ == "__main__":
    sys.exit(main())
