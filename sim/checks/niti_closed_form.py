"""Closed-form cross-check of the NiTi tragus arm (audit mech-1/2/3/4), independent of both the
original sim/checks/tragus_spring.py and the auditor's elastica model.

    python3 sim/checks/niti_closed_form.py

Once the root of a superelastic wire sits on its transformation plateau, the bending moment it can
carry saturates at the fully-plastic value of a solid circle, Mp = sigma * d^3 / 6, so the pad force
is F = Mp / L whatever the deflection. The loading (upper) and unloading (lower) plateaus differ,
so the force the skin feels depends on the direction of the last motion: that is hysteresis, and it
is intrinsic to superelastic NiTi, not a modelling artefact.

Plateau data: upper (loading) >= 380 MPa at 3% strain at room temperature (Confluent SE508 data
sheet, accessed 2026-09-30); ~450 MPa assumed near skin temperature. The LOWER (unloading) plateau
is NOT in any source on file (audit RC-01/mech-4), so it is swept.
"""
d, L = 0.85, 20.0          # mm: wire diameter and arm length (tragus-arm.md)
r = d / 2


def force(sigma):
    return sigma * d ** 3 / 6 / L


print("Pad force when the wire's root is on a plateau (F = sigma d^3 / 6L, d 0.85 mm, L 20 mm):")
print(f"  loading plateau 450 MPa -> {force(450):.2f} N   (putting the glasses on; jaw pushing in)")
for lo in (150, 200, 250):
    print(f"  unloading plateau {lo} MPa -> {force(lo):.2f} N   (jaw letting the pad out)")
print("  => with jaw motion the force swings between the two: ~1.0 to 2.3 N at 200 MPa,")
print("     and falls below the 1 N target if the real unloading plateau is under ~195 MPa.")
print(f"  (the auditor's elastica model: 1.05-2.37 N, agreeing with this within 3%)")

print("\nRoot strain. Past the plateau the bend localises at the root like a hinge; strain = r * kappa.")
for theta_deg, hinge in ((27.3, 3.0), (27.3, 5.0)):
    import math
    k = math.radians(theta_deg) / hinge
    print(f"  tip rotation {theta_deg} deg taken over a {hinge} mm hinge -> {r * k * 100:.1f} % strain")
print("  Recovery limit for SE508 is ~6-8% (permanent set <= 0.3% after 6%). Fatigue-rated")
print("  designs stay nearer 2-4%. A curved root form of radius R caps strain at r/R:")
for eps in (0.06, 0.04, 0.02):
    print(f"    {eps * 100:.0f}% max strain needs R >= {r / eps:.1f} mm of support radius")

# ---- Redesign options. The swing comes from riding the plateau; the only way out of hysteresis
# is to stay ELASTIC (root strain under ~1%), i.e. a longer or thinner arm. Linear cantilever:
# F = 3 E I delta / L^3, root strain = 3 delta r / L^2. Nominal delta 7 mm, jaw motion +-2 mm.
import math
print("\nRedesign options (nominal 7 mm deflection, jaw +-2 mm):")
print(f"  {'option':38s} {'F at 5/7/9 mm (N)':>20s} {'max strain':>10s}")
print(f"  {'A today: NiTi 0.85 x 20 mm, on plateau':38s} {'1.0-2.3 (path-dep.)':>20s} {'4-7 %':>10s}")
for lab, E, d_, L_ in (("B NiTi 0.85 x 30 mm, elastic", 50e3, 0.85, 30.0),
                       ("C spring steel 0.60 x 30 mm", 200e3, 0.60, 30.0),
                       ("D NiTi 0.70 x 25 mm, elastic", 50e3, 0.70, 25.0)):
    I_ = math.pi * d_ ** 4 / 64
    Fs = [3 * E * I_ * dl / L_ ** 3 for dl in (5, 7, 9)]
    eps = 3 * 9 * (d_ / 2) / L_ ** 2
    print(f"  {lab:38s} {' / '.join(f'{f:.2f}' for f in Fs):>20s} {eps * 100:9.1f} %")
print("  NiTi's elastic modulus is itself strain- and temperature-dependent (30-80 GPa quoted):")
print("  B and D carry +-30% force uncertainty until a coupon is bent on the bench.")
