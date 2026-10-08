"""K4 dock option A: magnet pull vs pogo spring force (Coulomb surface-charge model, coaxial identical discs, N52 Br 1.45 T).
Model: pole density sigma = Br on each flat face; F = sum over face pairs sigma^2/(4 pi mu0) * dA dA / r^2 * cos. [A] Idealised (no demag, no offset);
real pull is ~0.7-0.9x of this for L/D<0.5 discs. Gap = belly skin + head shell [T].  Run: python3 sim/checks/dock_pull.py"""
import numpy as np
MU0 = 4e-7 * np.pi
BR = 1.45

def disc_pts(d, n=60):
    g = (np.arange(n) + 0.5) / n * 2 - 1
    X, Y = np.meshgrid(g * d / 2, g * d / 2)
    m = X**2 + Y**2 <= (d / 2) ** 2
    return X[m], Y[m], (d / n) ** 2

def pull(d, t, gap, dx=0.0):
    """attraction (N) between two coaxial discs d x t (mm), face-to-face gap (mm), lateral offset dx (mm) -> returns (F_axial N)"""
    x, y, dA = disc_pts(d)
    zs1 = [(0.0, +1), (t, -1)]                        # pod magnet: faces at z=0 (toward head, N) and z=-t (S)
    F = 0.0
    for z1, s1 in [(0.0, +1), (-t, -1)]:
        for z2, s2 in [(gap, -1), (gap + t, +1)]:      # head magnet facing opposite pole toward the pod = attraction
            dz = (z2 - z1) * 1e-3
            X1, Y1 = x[:, None] * 1e-3, y[:, None] * 1e-3
            X2, Y2 = x[None, :] * 1e-3 + dx * 1e-3, y[None, :] * 1e-3
            r2 = (X1 - X2) ** 2 + (Y1 - Y2) ** 2 + dz**2
            f = (dz / r2**1.5).sum() * (dA * 1e-6) ** 2
            F += -s1 * s2 * f * BR**2 / (4 * np.pi * MU0)
    return F * -1 if F < 0 else F

if __name__ == "__main__":
    SPRING = 4 * 0.294                                 # 4 pins x 30 gf (YZP0048 listing) = 1.18 N at full stroke [T: stroke unknown]
    print("spring push-off (4 x 30 gf) = %.2f N" % (4 * 0.294))
    for d, t in ((2, 0.5), (3, 0.5), (3, 1.0), (4, 1.0), (4, 1.5)):
        for gap in (0.3, 0.5):
            f = pull(d, t, gap)
            print(f"D{d} x {t}  gap {gap}: one pair {f:.2f} N, two {2*f:.2f} N, net after spring {2*f-4*0.294:+.2f} N, 0.5mm lateral offset one pair {pull(d,t,gap,0.5):.2f} N")
