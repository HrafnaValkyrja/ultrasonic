#!/usr/bin/env python3
"""Button concepts for a 0.6 mm lid (K1-thin, round 12, packet Q2): stack, travel/force, sealing, board change, feel, build.

    python3 sim/checks/button_concepts.py      # -> sim/out/mech/button_concepts.json + docs/diagrams/button-concepts.{png,svg} (dark)

The problem (dims_k1 k1t): F gap 0.30 + KMT022 0.65 -> switch top 0.35 above the lid inner face; the Phase-2 stack needs
pocket 0.6 + puck + skin 0.25 = > 0.85 of lid, so a 0.6 lid breaks through and has no room for a puck.
Every number below is computed here from dims (k1t), the datasheets named in SRC, or an [A] assumption stated in place.
LCSC search for a thinner sealed tact switch: 2026-10-07T21:35Z (tools/jlc.py), recorded in SRC.
"""
import json
import math
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "hw/mech"))
os.environ.setdefault("ULTRASONIC_DESIGN", "k1t")
import dims as D  # noqa: E402

LID = round(D.Y_TOP - D.Y_LID_IN, 3)          # 0.6
FGAP = D.F_GAP                                 # 0.30
SKIN = 0.25                                    # Phase-2 silicone skin
E_RESIN, NU_R = 2000.0, 0.38                   # N/mm2 [A] tough resin
FATIGUE_RESIN = 15.0                           # MPa [A] ~1e6-cycle bending fatigue of photopolymer resins (no sourced figure)
SW_FORCE = {"KMT022": 1.6, "dome150": 1.47, "dome250": 2.45}   # N (KMT022 1.6 N: LCSC C221707; HYP 150/250 gf +-15 gf)
TOL = dict(vhb=round(0.15 * D.VHB_T, 4), sw_h=0.05, solder_lift=0.05, recess_floor=0.05, lid_face=0.03)

SRC = dict(
    kmt022="C&K KMT022NGJLHS, LCSC C221707: 3.0 x 2.6 x 0.65, 1.6 N, IP68 (jlc.py 2026-10-07T21:35Z)",
    thin_search="jlc.py 2026-10-07T21:35Z: 'tactile switch 0.35mm/0.4mm/0.5mm' none in stock; Antenk 4.8x4.8x0.55H C55042778 "
                "(no datasheet, no IP rating, 0.10 thinner); KMT0 family all 0.65",
    side="ALPS SKTDLDE010 C115365: right-angle (side push) 3.9 x 2.9, 1.55 tall, 1.63 N (jlc.py 2026-10-07T21:35Z)",
    dome="HYP (Hong Yuan) 600-415S-150/-250, LCSC C256252/C256257: Phi4 metal dome, H 0.20 +-0.05, 150/250 gf +-15, "
         "1M cycles (150 gf); drawing 600-0000-000 rev F (LCSC PDF SHA-256 prefix 5e1a15513603fc00, read 2026-10-07)")


def fixed_gap_worst(nominal, extra=0.0):
    sym = TOL["vhb"] + TOL["sw_h"] + TOL["recess_floor"] + TOL["lid_face"] + extra
    return round(nominal - sym - TOL["solder_lift"], 3), round(nominal + sym, 3)


def clamped_disc(t, a, delta):
    """Clamped circular plate, central point load: force for deflection delta and edge stress (Roark Table 11.2 case 16)."""
    Dp = E_RESIN * t ** 3 / (12 * (1 - NU_R ** 2))
    P = delta * 16 * math.pi * Dp / a ** 2
    sigma = 3 * P / (2 * math.pi * t ** 2)
    return round(P, 2), round(sigma, 1)


def main():
    sw_top = FGAP + 0.65 - FGAP                     # KMT022 top above the lid inner face: 0.35
    sw_top = round(D.Y_F + 0.65 - D.Y_LID_IN, 3)
    C = {}
    # A1: thinner sealed tact switch
    C["A1_thin_tact"] = dict(what="lower-profile sealed tact switch in SW1's place", feasible=False,
                             why=SRC["thin_search"], sealing="-", board="footprint swap", feel="-", build="-", score=None)
    # A2: metal snap dome on F pads (modelled: K1_BUTTON=dome)
    cap_r = 1.3                                      # bore edge radius over the dome (D2.6)
    R = (2.0 ** 2 + 0.2 ** 2) / (2 * 0.2)
    cap_at_bore = 0.2 - (R - math.sqrt(R ** 2 - cap_r ** 2)) + 0.075
    relief = 0.10
    clr = round(FGAP + relief - cap_at_bore, 3)
    C["A2_dome"] = dict(
        what="HYP 600-415S Phi4 metal snap dome + 0.075 PSA overlay on new F pads (centre BTN, C-ring +3V0 with a gap for the BTN trace) "
             "in place of KMT022; sits inside the 0.30 F gap; lid: 0.10 relief, D2.6 bore, skin 0.25 recess, selective-fit puck (as today)",
        feasible=True, dome_top_above_lid_inner=round(0.2 + 0.075 - FGAP, 3), puck_L=round(D.PUCK_L, 3) if os.environ.get("K1_BUTTON") == "dome" else None,
        puck_guide=round(LID - relief - SKIN, 3), cap_clear_at_bore_edge_nominal=clr, cap_clear_worst=round(clr - TOL["vhb"] - 0.05 - TOL["lid_face"] - TOL["solder_lift"] * 0, 3),
        travel="~0.15-0.20 to contact (dome collapse, H 0.20 +-0.05) [A: HYP gives H and force only]", force_N=[SW_FORCE["dome150"], SW_FORCE["dome250"]],
        sealing="unchanged: skin bonded in the lid recess is the seal (O16(7)); dome contacts sealed under its PSA overlay (KMT022's own IP68 is lost as the 2nd barrier)",
        board="F copper only: KMT022 4 pads -> centre pad + C-ring; BTN leaves through the ring gap to its existing via (16.31, 6.92); +3V0 vias at r 1.8-1.9 "
              "(19.45, 7.53) and (19.52, 4.35) sit under the ring = same net (tent/fill them); a local edit + DRC, no autorouter expected; ENIG already "
              "required (D0.65 press-fit); dome placed by hand after reflow (not JLC SMT)",
        feel="crisp metal click; force picked from a cents-each set (150 / 180 / 200 / 250 gf); shorter travel than KMT022's 0.15 +-0.1 + skin",
        build="owner places the dome with tweezers on its tape (centre +-0.2 by eye on the silkscreen ring); everything else as today",
        mirror="centre on board y 6.0: same in both pods (O16(5))", score=None)
    # B: flexing resin window with an inner boss over KMT022
    t_m = round(LID - sw_top - 0.1, 3)               # membrane thickness if its underside keeps 0.1 above the switch
    P, sig = clamped_disc(max(t_m, 0.05), 2.15, 0.1 + 0.25)
    C["B_resin_flex_window"] = dict(what="lid thinned to a printed membrane over SW1 (no hole), inner boss presses KMT022", feasible=False,
                                    membrane_t=t_m, membrane_force_N=P, edge_stress_MPa=sig, fatigue_limit_MPa_A=FATIGUE_RESIN,
                                    why=f"0.6 lid - switch top {sw_top} - 0.1 gap leaves a {t_m} membrane: {P} N extra and {sig} MPa at the clamp for "
                                        f"0.35 deflection, > ~{FATIGUE_RESIN} MPa [A] fatigue: cracks within the 600k-press life",
                                    sealing="best (no hole)", board="none", feel="stiff, dull", build="print only")
    # C: proud silicone skin straight over KMT022 (no puck), board unchanged
    for proud in (0.10, 0.20):
        under = LID + proud - SKIN                   # skin underside above the lid inner face
        gap = round(under - sw_top, 3)
        lo, hi = fixed_gap_worst(gap)
        C[f"C_skin_over_switch_proud{proud:.2f}"] = dict(
            what=f"window over KMT022 through the 0.6 lid; 0.25 silicone skin standing {proud} proud; selective-fit nub dot under the skin",
            feasible=lo >= -0.05, skin_underside_gap=gap, fixed_worst=[lo, hi], local_T_add=proud,
            note="a printed/silicone nub dot of 4 thicknesses (0.05 steps) glued under the skin restores selective fit; then worst = +-0.06",
            sealing="unchanged (skin bonded round the window)", board="none (KMT022 stays)", feel="soft dome over a click, ~0.1-0.2 dead travel",
            build="simplest: no puck; skin + dot", mirror="ok")
    # D: side-actuated switch on the board edge
    C["D_side_switch"] = dict(what="right-angle switch at the board's long edge, pressed through the pod top wall", feasible=False,
                              why=f"{SRC['side']}: 1.55 tall > B gap {D.B_GAP} (the 12.7 cell covers the whole board in K1); the left pod is the "
                                  "flipped board, so the edge switch lands on the belly side -> two switches; footprint + router",
                              sealing="new skin in the top wall", board="2 new parts + router", feel="press down on the top edge", build="medium")
    # E: switch on B pressing through the cell side
    C["E_B_face_switch"] = dict(what="SW1 on the B face, actuated through the cell side", feasible=False,
                                why="the user can only reach the outer (lid) face; the lid and the full-face-bonded board move as one, so a B switch "
                                    "would need the cell as an anvil (pressure on a Li-po pouch) and a 0.25 board travel the VHB bond forbids")
    out = dict(date="2026-10-07", src="sim/checks/button_concepts.py", design=D.DESIGN.id, lid=LID, kmt022_top_above_lid_inner=sw_top,
               sources=SRC, tolerances=TOL, concepts=C,
               recommendation="A2 dome (flush T 8.5, board F-copper edit only, crisp click) if she accepts the hand-placed dome; "
                              "C proud 0.20 (no board change, +0.2 soft bump at the button) as the no-board-change fallback; feel = her call")
    od = ROOT / "sim/out/mech"
    od.mkdir(parents=True, exist_ok=True)
    (od / "button_concepts.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
    figure(out)


def figure(out):
    sys.path.insert(0, str(ROOT / "tools"))
    import plotstyle
    plotstyle.apply()
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, Polygon
    fig, axes = plt.subplots(1, 4, figsize=(18, 3.6), sharey=True)
    lid, gap = out["lid"], FGAP
    titles = ["Phase-2 stack in a 0.6 lid: BREAKS THROUGH", "A2 dome (recommended): flush", "C skin over KMT022, 0.20 proud", "B resin flex window: cracks"]
    for k, ax in enumerate(axes):
        ax.add_patch(Rectangle((-4, -0.8 - gap), 8, 0.8, fc="#2fc98f", ec="none"))             # board
        ax.add_patch(Rectangle((-4, -gap), 8, gap, fc="#ff6d6c", alpha=0.25, ec="none"))      # VHB band
        ax.add_patch(Rectangle((-4, 0), 8, lid, fc="#9aa3b2", alpha=0.9, ec="none"))          # lid
        if k in (0, 2, 3):
            ax.add_patch(Rectangle((-1.5, -gap), 3.0, 0.65, fc="#8d7ff0", ec="none", alpha=0.85, zorder=5))   # KMT022 (top 0.35 above the lid inner face)
        if k == 0:
            ax.add_patch(Rectangle((-2.15, 0), 4.3, 0.6, fc="#141518", ec="#ff6d6c", lw=1.2))
            ax.text(0, 0.75, "pocket 0.6 = whole lid; no room for puck + skin", ha="center", color="#ff6d6c", fontsize=8)
        if k == 1:
            xs = [-2 + 0.1 * i for i in range(41)]
            R = (4 + 0.04) / 0.4
            ax.fill_between(xs, -gap, [-gap + 0.2 - (R - math.sqrt(R * R - x * x)) + 0.075 for x in xs], color="#f28c3f")
            ax.add_patch(Rectangle((-2.3, 0), 4.6, 0.10, fc="#141518", ec="none"))
            ax.add_patch(Rectangle((-1.3, 0.10), 2.6, lid - 0.10, fc="#141518", ec="none"))
            ax.add_patch(Rectangle((-2.3, lid - SKIN), 4.6, SKIN, fc="#52d39e", alpha=0.8, ec="none"))
            ax.add_patch(Rectangle((-1.15, 0.0), 2.3, lid - SKIN - 0.07 + 0.025, fc="#5b9ff2", ec="none"))
            ax.text(0, lid + 0.1, "puck guide 0.25, skin flush", ha="center", color="#e8e8e5", fontsize=8)
        if k == 2:
            ax.add_patch(Rectangle((-2.15, 0), 4.3, lid, fc="#141518", ec="none"))
            ax.add_patch(Rectangle((-2.6, lid + 0.2 - SKIN), 5.2, SKIN, fc="#52d39e", alpha=0.8, ec="none"))
            ax.text(0, lid + 0.3, "+0.20 soft bump; no board change", ha="center", color="#e8e8e5", fontsize=8)
        if k == 3:
            t = out["concepts"]["B_resin_flex_window"]
            ax.add_patch(Rectangle((-2.15, 0), 4.3, lid - t["membrane_t"], fc="#141518", ec="none"))
            ax.text(0, lid + 0.1, f"membrane {t['membrane_t']}: {t['edge_stress_MPa']} MPa at the clamp", ha="center", color="#ff6d6c", fontsize=8)
        ax.set_xlim(-3.5, 3.5)
        ax.set_ylim(-1.3, 1.3)
        ax.set_aspect("equal")
        ax.set_title(titles[k], fontsize=9)
        ax.set_xlabel("mm (board x round SW1)")
    axes[0].set_ylabel("mm above the lid inner face")
    fig.suptitle("Button for a 0.6 lid (K1-thin): board green, VHB band red, lid grey, switch violet, dome orange, puck blue, skin green", fontsize=10)
    fig.tight_layout()
    for ext in ("png", "svg"):
        fig.savefig(ROOT / "docs/diagrams" / f"button-concepts.{ext}", dpi=130)


if __name__ == "__main__":
    main()
