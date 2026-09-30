"""How does the transducer arm hold >= 1 N on the pre-tragal skin while the jaw moves?

    python3 sim/checks/tragus_spring.py      # prints the table, writes sim/out/mech/tragus_spring.png

Geometry (spec §8 v0.9, ear-open-fit.md): the arm leaves the pod's rear-lower corner (~9 mm below
the temple arm) and sweeps back 30 deg to the pad, which sits ~25 mm below the temple arm.
So the pad is ~16 mm below the pivot/root and the arm is ~20 mm long along its length.

Requirement (D1, E2): >= 1 N at the pad through jaw motion, and not much more (comfort, T5).
The pre-tragal skin moves with the jaw; we assume +-2 mm normal to the skin until the owner's
mouth-open photo (E9) measures it. Every series compliance (temple-arm bending and twist, pad
foam) eats spring travel too, so a SOFT spring with a LARGE preload is the robust answer.

Three ways to build it:
  A  rigid arm on a pivot + preloaded music-wire torsion spring inside the pod
  B  one-piece superelastic NiTi wire arm (the Ear (open) hook uses the same material)
  C  one-piece stainless (301 full-hard) flat strip - the obvious choice, shown to fail

Material data (all [Med]; sources and dates in docs/research/tragus-arm.md):
  301 FH strip: E 200 GPa, yield >= 965 MPa, fatigue ~552 MPa (ATI/Ulbrich/UPMET datasheets)
  NiTi SE508: E 41-75 GPa, loading plateau >= 380 MPa @ 3% (room temp; +~6.5 MPa/degC toward
     skin temperature), unloading plateau ~200 MPa (Confluent Medical data sheet; US 6,706,053)
  Music wire A228, d 0.55 mm: E 207 GPa, tensile ~2,300 MPa; torsion-spring bending stress
     allowed ~0.75 x tensile static, we design to <= 0.5 x for cycling
"""
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
import plotstyle  # noqa: E402

OUT = REPO / "sim/out/mech"
OUT.mkdir(parents=True, exist_ok=True)

L_ARM = 20.0     # mm, root to pad centre along the arm (one-piece arms B, C)
R_PIV = 16.0     # mm, pivot to pad centre, measured perpendicular to the pivot axis (arm A)
JAW = 2.0        # mm, +- skin travel normal to the skin with jaw motion (assumed; E9 measures)
F_MIN = 1.0      # N


# ---------------------------------------------------------------- A: pivot + torsion spring
def torsion_spring(d=0.65, D=4.5, n=7, E=207e3, preload_rad=0.795):
    """Music-wire torsion spring. Rate per radian ~ E d^4 / (67.9 D n) (SMI form incl. ~6% friction)."""
    k = E * d ** 4 / (67.9 * D * n)                       # N*mm/rad
    delta = np.linspace(0, 8, 200)                       # pad travel from the preload stop (mm)
    T = k * (preload_rad + delta / R_PIV)
    F = T / R_PIV
    Ki = (4 * (D / d) ** 2 - (D / d) - 1) / (4 * (D / d) * ((D / d) - 1))   # Wahl bending correction
    sigma = Ki * 32 * T / (np.pi * d ** 3)
    return delta, F, sigma, k


# ---------------------------------------------------------------- B: superelastic NiTi round wire
def niti_wire(d=0.85, L=L_ARM, E=50e3, plateau=450.0, n_s=200):
    """Cantilever with an elastic-perfectly-flat (plateau) material, small-slope kinematics.

    Moment-curvature of a round section is integrated numerically; deflection = int kappa (L - s) ds.
    Run once with the loading plateau (putting the glasses on) and once with the unloading plateau
    (what the skin feels once settled); real jaw cycling sits between the two.
    """
    r = d / 2
    yy = np.linspace(-r, r, 401)
    width = 2 * np.sqrt(np.maximum(r ** 2 - yy ** 2, 0))
    dy = yy[1] - yy[0]
    kap_grid = np.linspace(0, 0.2, 2000)                 # 1/mm (surface strain up to 8.5%)
    M_grid = np.array([np.sum(np.clip(E * k * yy, -plateau, plateau) * yy * width) * dy for k in kap_grid])
    s = np.linspace(0, L, n_s)
    Fs = np.linspace(0.01, 3.0, 300)
    delta, eps_max = [], []
    for F in Fs:
        M = F * (L - s)
        if M[0] > M_grid[-1]:
            break
        kap = np.interp(M, M_grid, kap_grid)
        delta.append(np.trapezoid(kap * (L - s), s))
        eps_max.append(kap[0] * r)
    n = len(delta)
    # past the last point the section is fully on the plateau: force stays flat while travel grows
    # (curvature piles up at the root - a real part needs a curved root support, see tragus-arm.md)
    delta = np.append(delta, 20.0)
    return delta, np.append(Fs[:n], Fs[n - 1]), np.append(eps_max, np.nan)


# ---------------------------------------------------------------- C: stainless flat strip
def steel_strip(t=0.15, w=6.0, L=L_ARM, E=200e3):
    k = E * w * t ** 3 / (4 * L ** 3)
    delta = np.linspace(0, 14, 200)
    F = k * delta
    sigma = 6 * F * L / (w * t ** 2)
    return delta, F, sigma, k


def band(delta, F, nominal):
    lo, hi = np.interp([nominal - JAW, nominal + JAW], delta, F)
    return lo, hi


def main():
    plt = plotstyle.apply()
    fig, ax = plt.subplots(figsize=(9, 5))
    rows = []

    dA, FA, sA, kA = torsion_spring()
    nomA = 4.0
    loA, hiA = band(dA, FA, nomA)
    ax.plot(dA, FA, color=plotstyle.SERIES[0], label="A  pivot + torsion spring (d 0.65 mm, 7 turns, OD 5.2 mm)")
    rows.append(("A pivot + torsion spring", loA, hiA, f"stress {np.interp(nomA + JAW, dA, sA):.0f} MPa (<= ~1150 ok)"))

    dB_l, FB_l, eB_l = niti_wire(plateau=450.0)
    dB_u, FB_u, eB_u = niti_wire(plateau=200.0)
    nomB = 7.0
    loB_u, hiB_u = band(dB_u, FB_u, nomB)
    loB_l, hiB_l = band(dB_l, FB_l, nomB)
    ax.plot(dB_l, FB_l, color=plotstyle.SERIES[1], ls="--", label="B  NiTi wire d 0.85 mm, loading (putting glasses on)")
    ax.plot(dB_u, FB_u, color=plotstyle.SERIES[1], label="B  NiTi wire d 0.85 mm, unloading (settled)")
    knee = dB_u[np.argmax(FB_u > 0.95 * FB_u[-1])]
    rows.append(("B NiTi wire (settled..putting on)", loB_u, hiB_l,
                 f"flat above ~{knee:.1f} mm travel; root strain must be limited by a curved root support"))

    dC, FC, sC, kC = steel_strip()
    ok = sC <= 965
    ax.plot(dC[ok], FC[ok], color=plotstyle.SERIES[2], label="C  301 steel strip 6 x 0.15 mm (ends at yield)")
    fat = np.interp(552, sC, FC)
    ax.plot([np.interp(552, sC, dC)], [fat], "o", color=plotstyle.SERIES[2])
    ax.annotate("fatigue limit", (np.interp(552, sC, dC), fat), textcoords="offset points", xytext=(6, -12), fontsize=8)
    rows.append(("C steel strip (best case)", fat, fat, f"can't exceed {fat:.2f} N below the fatigue limit"))

    ax.axhline(F_MIN, color=plotstyle.TEXT_2, lw=0.8, ls=":")
    ax.text(0.2, F_MIN + 0.03, "1 N minimum (D1)", fontsize=8, color=plotstyle.TEXT_2)
    for nom, c in ((nomA, plotstyle.SERIES[0]), (nomB, plotstyle.SERIES[1])):
        ax.axvspan(nom - JAW, nom + JAW, color=c, alpha=0.08, lw=0)
    ax.set_xlabel("pad pushed out from its free position (mm)")
    ax.set_ylabel("force on the skin (N)")
    ax.set_title("Tragus pad force vs travel. Shaded: +-2 mm jaw motion around each option's fitting point")
    ax.set_ylim(0, 2.6)
    ax.set_xlim(0, 14)
    ax.legend(loc="lower right")
    fig.savefig(OUT / "tragus_spring.png")

    print(f"A: torsion rate {kA:.1f} N*mm/rad; C: strip rate {kC:.3f} N/mm")
    print(f"{'option':36s} {'F over jaw range (N)':>22s}  note")
    for name, lo, hi, note in rows:
        print(f"{name:36s} {lo:9.2f} .. {hi:<9.2f}   {note}")


if __name__ == "__main__":
    main()
