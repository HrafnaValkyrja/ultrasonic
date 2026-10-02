"""Assembly-domain numbers behind docs/research/simplify/assembly.md (2026-10-02).

    python3 sim/checks/assembly_fees.py fees            # JLC fixed-fee model per order, scenarios S0-S3
    python3 sim/checks/assembly_fees.py faces           # courtyard area per face of the draft board (needs pcbnew; fence it)
    python3 sim/checks/assembly_fees.py plot            # docs/research/simplify/assembly-study.png (fees + faces + height bands)

    systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 python3 sim/checks/assembly_fees.py faces

Fee constants are JLCPCB's own page https://jlcpcb.com/help/article/pcb-assembly-price ("Last updated on Sep 09, 2026"),
read 2026-10-02. They are for STANDARD PCBA, which is the only tier this board can use (Economic: single side only, IC pin
pitch >= 0.4 mm, BGA pitch >= 0.5 mm, 0.8 mm board only as 2-layer HASL: jlcpcb.com/capabilities/pcb-assembly-capabilities,
read 2026-10-02).

What is NOT modelled (no static primary page; the interactive quote form is the only source):
  * PCB fabrication price (5 panels, 4-layer, 0.8 mm, ENIG, different-design and small-via surcharges)
  * shipping and duties
  * the "Pre-reflow Soldering $0.016/joint" line (the page does not say what it applies to; shown as an upper bound)
Reading choices (the page is terse):
  * "Feeder Loading $1.53 Basic/Extend" is taken as one charge per unique part number (BOM line), Basic or Extended.
  * X-ray: "components such as BGA, QFN and other leadless packages". Count per board is shown low (BGA/QFN/LGA only) and
    high (every leadless body: + X2SON, DFN). The fee table is by "component quantity"; the low figure uses the fewest parts
    with the tier price on every piece, the high figure the most parts priced tier by tier.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

# ---- JLC Standard PCBA fee table, 2026-09-09 page, read 2026-10-02 -------------------------------------------------
SETUP = {"single": 25.56, "double": 51.12}
STENCIL = {"single": 8.21, "double": 16.42}
PANEL_MULTI_DESIGN = 8.21            # when the panel holds more than one design
FEEDER_PER_TYPE = 1.53               # Standard: Basic and Extended alike
SMT_PER_JOINT = 0.0016
MANUAL_PER_JOINT = 0.0164
HAND_LABOR_PER_ORDER = 3.58
CONFIRM_PLACEMENT = 0.45
PACKING_BASE, PACKING_PER_CM2 = 0.50, 0.00003
XRAY_TIERS = [(10, 1.64), (50, 0.82), (200, 0.49), (500, 0.33)]
PRE_REFLOW_PER_JOINT = 0.016         # undefined on the page: reported as an upper bound only

JOINTS_PER_BOARD = 186               # 49 two-pad parts x2 + U1 49 + U2 5 + U3 8 + U4 5 + U6 5 + Q1/Q2 6+6 + SW1 4 (draft, 56 parts)
PANEL_AREA_CM2 = 7.0 * 7.0


def xray_tier_wide(n: int) -> float:
    """Reading A: the tier price applies to every piece (cheapest reading)."""
    if n <= 0:
        return 0.0
    return n * next(p for lim, p in XRAY_TIERS if n <= lim)


def xray_incremental(n: int) -> float:
    """Reading B: pieces are priced tier by tier (first 10 at $1.64, the next at $0.82 ...)."""
    fee, left, prev = 0.0, n, 0
    for lim, p in XRAY_TIERS:
        take = min(left, lim - prev)
        fee += take * p
        left -= take
        prev = lim
        if left <= 0:
            break
    return fee


SCENARIOS = {
    # name: sides, BOM types, hidden-joint parts per board (low, high), designs in the panel, manual joints per board
    "S0 Rev E as drawn (double-sided)":                 dict(sides="double", types=29, hid=(3, 6), designs=1, manual=0),
    "S0+ with the pad board in the panel":              dict(sides="double", types=30, hid=(3, 6), designs=2, manual=0),
    "S1 all on one face, SW1 hand-soldered":            dict(sides="single", types=28, hid=(3, 6), designs=1, manual=4),
    "S2 double-sided, this study + OUT/PWR/PER cuts":   dict(sides="double", types=24, hid=(3, 4), designs=1, manual=0),
}


def order_fees(sc: dict, boards: int = 4, panels: int = 2) -> dict:
    lo_n, hi_n = (sc["hid"][0] * boards, sc["hid"][1] * boards)
    x_low = xray_tier_wide(lo_n)          # fewest hidden-joint parts, cheapest reading
    x_high = xray_incremental(hi_n)       # most hidden-joint parts, dearest reading
    smt = JOINTS_PER_BOARD * boards * SMT_PER_JOINT
    manual = sc["manual"] * boards * MANUAL_PER_JOINT + (HAND_LABOR_PER_ORDER if sc["manual"] else 0.0)
    fixed = SETUP[sc["sides"]] + STENCIL[sc["sides"]]
    feeder = sc["types"] * FEEDER_PER_TYPE
    panel = PANEL_MULTI_DESIGN if sc["designs"] > 1 else 0.0
    other = CONFIRM_PLACEMENT + PACKING_BASE + PACKING_PER_CM2 * PANEL_AREA_CM2 * panels
    base = fixed + feeder + panel + smt + manual + other
    return dict(setup_stencil=round(fixed, 2), feeder=round(feeder, 2), panel_design=round(panel, 2), smt_joints=round(smt, 2),
                manual=round(manual, 2), other=round(other, 2), xray_low=round(x_low, 2), xray_high=round(x_high, 2),
                total_low=round(base + x_low, 2), total_high=round(base + x_high, 2),
                per_pod_low=round((base + x_low) / boards, 2), per_pod_high=round((base + x_high) / boards, 2),
                pre_reflow_upper_bound=round(JOINTS_PER_BOARD * boards * PRE_REFLOW_PER_JOINT, 2))


def cmd_fees():
    print("JLC Standard PCBA fixed fees per order, 2 panels assembled = 4 pod boards (2 pods + 2 spares). Source: JLC fee page 2026-09-09, read 2026-10-02")
    print("PCB fabrication, shipping and parts are NOT included (not quotable from a static page).")
    out = {}
    for name, sc in SCENARIOS.items():
        f = order_fees(sc)
        out[name] = f
        print(f"\n{name}")
        for k, v in f.items():
            print(f"   {k:24} {v}")
    print("\nparts for 4 boards at the bom.md price: 4 x $22.90 = $91.60 (excludes cell, exciter, dock head)")
    json.dump(out, open(REPO / "docs/research/simplify/assembly-fees.json", "w"), indent=1)
    print("wrote docs/research/simplify/assembly-fees.json")


# ---- faces ---------------------------------------------------------------------------------------------------------
def measure_faces() -> dict:
    import pcbnew
    mm = pcbnew.ToMM
    b = pcbnew.LoadBoard(str(REPO / "hw/pod/draft_r1/pod_r1_placed.kicad_pcb"))
    res = {"F": dict(parts=0, area=0.0, pads=0, pad_area=0.0), "B": dict(parts=0, area=0.0, pads=0, pad_area=0.0)}
    tall = {"F": [], "B": []}
    for f in b.GetFootprints():
        ref = f.GetReference()
        side = "B" if f.GetLayer() == pcbnew.B_Cu else "F"
        cy = f.GetCourtyard(pcbnew.B_CrtYd if side == "B" else pcbnew.F_CrtYd)
        a = mm(mm(cy.Area())) if cy.OutlineCount() else 0.0
        if ref.startswith(("J", "TP")) and str(f.GetFPID().GetLibItemName()).startswith("TestPoint"):
            res[side]["pads"] += 1
            res[side]["pad_area"] += a
        elif ref in ("D1", "D2"):
            continue                       # DNP footprints
        else:
            res[side]["parts"] += 1
            res[side]["area"] += a
    return res


def cmd_faces():
    r = measure_faces()
    face, band = 34.0 * 13.0, 2 * 0.6 * 34.0
    usable = face - band
    print(f"one face {face:.0f} mm2, minus 0.6 mm clamp bands {usable:.1f} mm2")
    for s in "FB":
        d = r[s]
        print(f"{s}: {d['parts']} parts, courtyards {d['area']:.1f} mm2 ({100*d['area']/usable:.0f} % of usable); "
              f"{d['pads']} hand pads, rings {d['pad_area']:.1f} mm2")
    tot = r["F"]["area"] + r["B"]["area"]
    pads = r["F"]["pad_area"] + r["B"]["pad_area"]
    print(f"all parts on one face: {tot:.1f} mm2 = {100*tot/usable:.0f} % of usable; with the hand-pad rings {tot+pads:.1f} = {100*(tot+pads)/usable:.0f} %")
    json.dump(r, open(REPO / "docs/research/simplify/assembly-faces.json", "w"), indent=1)


HEIGHTS = {   # max body height above the board, mm (tools/checks/part_heights.yaml, datasheet maxima, read 2026-10-02)
    "F": [("L1", 1.00), ("Y1", 0.90), ("C4/C7", 0.90), ("SW1", 0.65), ("U1", 0.60)],
    "B": [("U2 mic", 1.08), ("D4", 1.00), ("C14", 1.00), ("C21", 0.90), ("U3", 0.65), ("R21", 0.65)],
}


def cmd_plot():
    sys.path.insert(0, str(REPO / "tools"))
    import plotstyle
    plt = plotstyle.apply()
    S = plotstyle.SERIES
    faces_json = REPO / "docs/research/simplify/assembly-faces.json"
    r = json.loads(faces_json.read_text()) if faces_json.exists() else measure_faces()
    fees = {n: order_fees(sc) for n, sc in SCENARIOS.items()}

    fig, ax = plt.subplots(1, 3, figsize=(17, 5.6), gridspec_kw=dict(width_ratios=[0.85, 0.95, 1.3], wspace=0.5))

    # (a) face load
    a = ax[0]
    usable = 34 * 13 - 2 * 0.6 * 34
    cats = ["F face", "B face", "all on\none face"]
    parts = [r["F"]["area"], r["B"]["area"], r["F"]["area"] + r["B"]["area"]]
    pads = [r["F"]["pad_area"], r["B"]["pad_area"], r["F"]["pad_area"] + r["B"]["pad_area"]]
    a.bar(cats, parts, color=S[0], label="part courtyards")
    a.bar(cats, pads, bottom=parts, color=S[1], label="hand-pad rings (J, TP)")
    a.axhline(usable, color=plotstyle.TEXT_2, lw=1, ls="--")
    a.text(-0.45, usable + 8, f"usable face {usable:.0f} mm2 (34x13 minus clamp bands)", ha="left", color=plotstyle.TEXT_2, fontsize=8)
    a.axhline(0.5 * usable, color=S[3], lw=1, ls=":")
    a.text(-0.45, 0.5 * usable + 8, "50 % packing (practical limit)", ha="left", color=S[3], fontsize=8)
    for i, (p, q) in enumerate(zip(parts, pads)):
        a.text(i, p + q + 8, f"{p+q:.0f} mm2\n{100*(p+q)/usable:.0f} %", ha="center", fontsize=8.5, color=plotstyle.TEXT)
    a.set_ylim(0, 470)
    a.set_ylabel("courtyard area, mm2")
    a.set_title("Face load of the draft board")
    la = a.legend(loc="upper right")
    [x.set_color(plotstyle.TEXT) for x in la.get_texts()]

    # (b) heights
    b = ax[1]
    ylabels, vals, cols = [], [], []
    for side, col in (("F", S[0]), ("B", S[2])):
        for n, h in HEIGHTS[side]:
            ylabels.append(f"{side}  {n}")
            vals.append(h)
            cols.append(col)
    ypos = list(range(len(vals)))[::-1]
    b.barh(ypos, vals, color=cols)
    b.set_yticks(ypos)
    b.set_yticklabels(ylabels, fontsize=8)
    b.axvline(1.2, color=S[7], lw=1.2, ls="--")
    b.text(1.18, len(vals) - 0.6, "1.2 mm band", color=S[7], fontsize=8, ha="right")
    for y, v in zip(ypos, vals):
        b.text(v + 0.015, y, f"{v:.2f}", va="center", fontsize=8, color=plotstyle.TEXT_2)
    b.set_xlim(0, 1.4)
    b.set_xlabel("max body height, mm (datasheet maxima)")
    b.set_title("Part heights: mic (B) and L1 (F) set the bands")
    b.grid(axis="y", visible=False)

    # (c) fees
    c = ax[2]
    short = {"S0 Rev E as drawn (double-sided)": "S0  Rev E as drawn",
             "S0+ with the pad board in the panel": "S0+ with pad board",
             "S1 all on one face, SW1 hand-soldered": "S1  one face, SW1 by hand",
             "S2 double-sided, this study + OUT/PWR/PER cuts": "S2  with all studies' cuts"}
    names = list(fees)
    mid = {n: (fees[n]["xray_low"] + fees[n]["xray_high"]) / 2 for n in names}
    keys = [("setup_stencil", "setup + stencil", S[0]), ("feeder", "feeder loading, $1.53 per BOM line", S[1]),
            ("xray", "X-ray (mid of range)", S[3]), ("panel_design", "2nd design in panel", S[4]),
            ("smt_joints", "SMT joints", S[5]), ("manual", "hand-solder labour", S[6]), ("other", "confirm + packing", S[7])]
    left = [0.0] * len(names)
    for k, lab, col in keys:
        v = [mid[n] if k == "xray" else fees[n][k] for n in names]
        c.barh(range(len(names)), v, left=left, color=col, label=lab)
        left = [l + x for l, x in zip(left, v)]
    for i, n in enumerate(names):
        c.text(left[i] + 2, i, f"${fees[n]['total_low']:.0f} to {fees[n]['total_high']:.0f}", va="center", fontsize=9, color=plotstyle.TEXT)
    c.set_yticks(range(len(names)))
    c.set_yticklabels([short[n] for n in names], fontsize=8.5)
    c.invert_yaxis()
    c.set_xlim(0, 190)
    c.set_xlabel("USD per order; 4 boards assembled; PCB, shipping and parts not included")
    c.set_title("JLC Standard PCBA fixed fees (fee page of 2026-09-09)")
    lc = c.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=2, fontsize=7.5)
    [x.set_color(plotstyle.TEXT) for x in lc.get_texts()]
    c.grid(axis="y", visible=False)

    out = REPO / "docs/research/simplify/assembly-study.png"
    fig.savefig(out)
    print("wrote", out)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "fees"
    {"fees": cmd_fees, "faces": cmd_faces, "plot": cmd_plot}[cmd]()
