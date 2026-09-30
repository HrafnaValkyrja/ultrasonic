"""B1: compare complementary MOSFET pairs for the D6 H-bridge at 3.0 V gate drive.

What it computes, per candidate pair (two pairs = four FETs in the bridge):
  - gate-drive current from the 3.0 V rail:  I = f_pwm * 2 * (QgN + QgP) at Vgs = 3.0 V
  - on-path resistance: one P (high side) + one N (low side) in series with the transducer
  - gain lost to that resistance into an 8 ohm transducer: 20*log10(8 / (8 + Rn + Rp))

Sources (datasheet typicals, Tj = 25 C; queried 2026-09-30, see docs/research/B-parts-selection.md):
  Rds(on) at 3.0 V is linearly interpolated between the datasheet's 2.5 V and 4.5 V typical rows.
  Qg at 3.0 V = Qg(4.5 V) * 0.62. The 0.62 ratio comes from the DMC2400UV manufacturer model
  (sim/spice/dmc2400uv_rds_qg.cir: 0.243 nC at 3.0 V vs 0.393 nC at 4.5 V, Vds = 3 V), and is
  applied to the others as an estimate [Low] until their own models or curves are checked.

Run:  python3 sim/checks/bridge_fet_compare.py   (writes docs/diagrams/B1-mosfet-compare.png)
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tools"))
import plotstyle  # noqa: E402

F_PWM = 200e3
R_LOAD = 8.0
QG_RATIO_3V = 0.243 / 0.393  # from the DMC2400UV model

# name: (Rn@2.5, Rn@4.5, Rp@2.5, Rp@4.5, QgN@4.5 nC, QgP@4.5 nC, package, footprint mm2)
PAIRS = {
    "DMC2400UV (Diodes)": (0.45, 0.35, 0.90, 0.70, 0.5, 0.5, "SOT-563", 1.6 * 1.6),
    "PMCXB290UE (Nexperia)": (0.36, 0.27, 0.98, 0.59, 0.6, 0.6, "DFN1010B-6", 1.1 * 1.0),
    "NTZD3155C (onsemi)": (0.50, 0.40, 0.60, 0.50, 1.5, 1.7, "SOT-563", 1.6 * 1.6),
    "PMCXB900UEL (Nexperia)": (0.62, 0.47, 1.27, 1.02, 0.4, 1.19, "DFN1010B-6", 1.1 * 1.0),
}


# label offsets (points) so the two close bubbles don't collide
OFFSETS = {"DMC2400UV (Diodes)": (-20, 16), "PMCXB290UE (Nexperia)": (12, -14)}


def at3v(r25, r45):
    return r25 + (r45 - r25) * (3.0 - 2.5) / (4.5 - 2.5)


def main():
    rows = []
    for name, (rn25, rn45, rp25, rp45, qn, qp, pkg, area) in PAIRS.items():
        rn, rp = at3v(rn25, rn45), at3v(rp25, rp45)
        i_gate_ma = F_PWM * 2 * (qn + qp) * QG_RATIO_3V * 1e-9 * 1e3
        loss_db = 20 * math.log10(R_LOAD / (R_LOAD + rn + rp))
        rows.append((name, rn, rp, i_gate_ma, loss_db, pkg, area))
        print(f"{name:24s} Rn={rn:.2f}  Rp={rp:.2f}  path={rn + rp:.2f} ohm  "
              f"gate-drive={i_gate_ma:.2f} mA  gain={loss_db:+.2f} dB  {pkg} {area:.2f} mm2")

    plotstyle.apply()
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(6.4, 4.0), dpi=150)
    for i, (name, rn, rp, ig, loss, pkg, area) in enumerate(rows):
        ax.scatter(ig, rn + rp, s=area * 220, color=plotstyle.SERIES[i], alpha=0.85,
                   edgecolor=plotstyle.TEXT_2, linewidth=0.5, zorder=3)
        ax.annotate(f"{name}\n{pkg}, {loss:+.1f} dB into 8 ohm", (ig, rn + rp),
                    textcoords="offset points", xytext=OFFSETS.get(name, (12, -4)), fontsize=7.5,
                    color=plotstyle.TEXT)
    ax.set_xlabel("Gate-drive current, 4 FETs at 200 kHz, Vgs = 3.0 V (mA)  - lower is better")
    ax.set_ylabel("On-path resistance P + N at 3.0 V (ohm)  - lower is better")
    ax.set_title("H-bridge MOSFET pairs: battery cost vs loudness cost (bubble area = footprint)")
    ax.set_xlim(0, 1.3)
    ax.set_ylim(0.8, 2.0)
    out = os.path.join(os.path.dirname(__file__), "..", "..", "docs", "diagrams", "B1-mosfet-compare.png")
    fig.tight_layout()
    fig.savefig(out)
    print("wrote", os.path.normpath(out))


if __name__ == "__main__":
    main()
