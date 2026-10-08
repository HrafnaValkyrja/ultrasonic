"""K4 dock tab (M board strip with the 4 castellated pads) - is it fragile? (backlog K4-DOCK-STRIP, 2026-10-08)
Geometry from hw/mech/dims_k4.py: tab x width TAB_X (pads 4 x 2.5 pitch + window + 0.3 each side), board thickness 0.8 (y),
strip length beyond the stack ~1.8 mm in the pogo direction z (k4-dock.yaml zero_growth). Pogos push along z = IN the tab plane,
so the 1.18 N spring push-off is a column load, not bending. Bending only comes from a tilted/knocked head (y), or handling.
[A] FR4 flexural strength 200 MPa (conservative; data sheets 300-450 MPa along the warp), E 20 GPa; no copper credit.
Run: python3 sim/checks/dock_strip.py"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "hw", "mech"))
try:
    import dims_k4 as d
    W = d.TAB_X[1] - d.TAB_X[0]
except Exception as e:
    W = 9.4
T = 0.8                 # board thickness (y) [spec: 6L 0.8]
SIG = 200.0             # MPa [A]
E = 20000.0             # MPa [A]
F_PUSH = 1.18           # N, 4 x 30 gf at full stroke (k4-dock.yaml)
print(f"tab width W={W:.2f} mm, T={T} mm")
print(f"column stress from push-off: {F_PUSH/(W*T):.2f} MPa (vs {SIG:.0f})")
I = W * T**3 / 12
print(f"{'L mm':>6} {'F_fail N (y tip load)':>22} {'defl um @1N':>12} {'sigma MPa @1N':>14}")
for L in (1.8, 3.0, 4.0, 6.0):
    Ff = SIG * I / (T / 2 * L)
    print(f"{L:6.1f} {Ff:22.0f} {1.0*L**3/(3*E*I)*1e3:12.1f} {1.0*L*(T/2)/I:14.1f}")
# castellation pull-out: barrel shear area, plated half-hole d 0.9 mm, Cu 25 um, 4 pads; [A] Cu yield 70 MPa
Acu = 4 * 3.14159 * 0.9 / 2 * 0.025
print(f"barrel Cu section (4 half-holes, 25 um): {Acu:.3f} mm2 -> {Acu*70:.1f} N at 70 MPa [A]; margin vs 1.18 N push {Acu*70/1.18:.0f}x")
print("verdict: strip bending failure needs >100 N at 1.8 mm (>30 N even at 6 mm); weak links are pad lift-off in the half-hole (needs the 0.15 mm annular ring, k4-dock.yaml) and panel handling - not bending.")
