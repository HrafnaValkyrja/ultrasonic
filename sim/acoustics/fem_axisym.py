"""Axisymmetric Helmholtz FEM of the mic port (scikit-fem, bilinear quads on a structured grid) - cross-check of the
lumped model in port.py.  ALIGNED designs only (any bore-hole offset breaks axisymmetry: that needs the 3-D heavy runs H-A2 / H-A4,
see docs/sim/acoustics.yaml heavy_runs).

Domain (z from the diaphragm outward): front volume (loss eta) | mic port tube | solder-standoff ring | board hole |
gap (open: slit disc to r_gap with an absorbing edge) or chimney (tube) | lid bore | hex window (equivalent circle) |
exterior half-space with an absorbing boundary.  Narrow tubes and the slit carry an effective density / compressibility
from the same Kirchhoff expressions as the lumped model (narrow.tube_eff / slit_eff), so the two differ only by the
plane-wave / lumped-end-correction / gap-quadrature approximations - which is what is being checked.
Incident wave: plane, normal incidence, total field = blocked field 2 p0 cos(k (z - z_plate)) + radiated (first-order
absorbing boundary for the radiated part).  Output: p_diaphragm / (2 p0) = the ratio transfer() returns.
Memory/time: h = 25 um, ~60 k elements, ~0.4 s per frequency, < 0.5 GB.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "2")
import numpy as np  # noqa: E402
import scipy.sparse as sps  # noqa: E402
import scipy.sparse.linalg as spla  # noqa: E402
from skfem import Basis, BilinearForm, ElementQuad0, ElementQuad1, FacetBasis, LinearForm, MeshQuad, asm  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from narrow import AIR, slit_eff, tube_eff  # noqa: E402

MM = 1e-3


@dataclass
class Design:
    """All lengths in mm."""
    gap: str = "chimney"       # open | chimney
    a_ch: float = 0.5
    r_gap: float = 10.0
    a_bore: float = 0.5
    l_bore: float = 0.9
    a_rec: float = 1.725
    d_rec: float = 0.8
    h_gap: float = 1.5
    t_board: float = 0.8
    a_hole: float = 0.3
    t_standoff: float = 0.05
    a_ring: float = 0.5
    a_port: float = 0.15
    l_port: float = 0.25
    r_front: float = 0.5
    h_front: float = 1.0
    eta: float = 0.11
    h_ext: float = 3.0
    r_ext: float = 6.0
    h_mesh: float = 0.025
    recess: bool = True


def regions(d: Design):
    z = 0.0
    R = []

    def add(name, r, th, medium):
        nonlocal z
        R.append(dict(name=name, r=r * MM, z0=z * MM, z1=(z + th) * MM, medium=medium))
        z += th
    add("front", d.r_front, d.h_front, ("eta", d.eta))
    add("port", d.a_port, d.l_port, ("tube", d.a_port * MM))
    add("ring", d.a_ring, d.t_standoff, ("air",))
    add("hole", d.a_hole, d.t_board, ("tube", d.a_hole * MM))
    if d.gap == "open":
        add("gap", d.r_gap, d.h_gap, ("slit", d.h_gap * MM))
    else:
        add("chim", d.a_ch, d.h_gap, ("tube", d.a_ch * MM))
    add("bore", d.a_bore, d.l_bore, ("tube", d.a_bore * MM))
    if d.recess and d.d_rec > 0:
        add("recess", d.a_rec, d.d_rec, ("tube", d.a_rec * MM))
    z_plate = z * MM
    add("ext", d.r_ext, d.h_ext, ("air",))
    return R, z_plate


def solve(d: Design, freqs, air=AIR):
    """-> complex p_diaphragm/(2 p0) for each frequency, plus a small info dict."""
    h = d.h_mesh * MM
    R, z_plate = regions(d)
    z_top = R[-1]["z1"]
    r_max = max(x["r"] for x in R)
    nr, nz = int(round(r_max / h)), int(round(z_top / h))
    mesh0 = MeshQuad.init_tensor(np.linspace(0, nr * h, nr + 1), np.linspace(0, nz * h, nz + 1))

    def labels(mesh):
        c = mesh.p[:, mesh.t].mean(axis=1)
        lab = np.full(c.shape[1], -1)
        for i, x in enumerate(R):
            lab[(c[0] < x["r"]) & (c[1] > x["z0"]) & (c[1] < x["z1"])] = i
        return lab
    mesh = mesh0.remove_elements(np.where(labels(mesh0) < 0)[0])
    label = labels(mesh)
    basis = Basis(mesh, ElementQuad1(), intorder=3)
    basis0 = Basis(mesh, ElementQuad0(), intorder=3)

    @BilinearForm
    def K(u, v, w):
        return w.ind * (u.grad[0] * v.grad[0] + u.grad[1] * v.grad[1]) * w.x[0]

    @BilinearForm
    def M(u, v, w):
        return w.ind * u * v * w.x[0]

    @BilinearForm
    def B(u, v, w):
        return u * v * w.x[0]

    Ks, Ms = [], []
    for i in range(len(R)):
        ind = basis0.interpolate((label == i).astype(float))
        Ks.append(asm(K, basis, ind=ind))
        Ms.append(asm(M, basis, ind=ind))
    fm = mesh.p[:, mesh.facets].mean(axis=1)
    bf = mesh.boundary_facets()
    r_ext = R[-1]["r"]
    top = bf[np.abs(fm[1, bf] - z_top) < 1e-12]
    side = bf[(np.abs(fm[0, bf] - r_ext) < 1e-12) & (fm[1, bf] > z_plate)]
    gapf = np.array([], int)
    if d.gap == "open":
        rg = next(x for x in R if x["name"] == "gap")
        gapf = bf[(np.abs(fm[0, bf] - rg["r"]) < 1e-12) & (fm[1, bf] > rg["z0"]) & (fm[1, bf] < rg["z1"])]
    fb = lambda fac: FacetBasis(mesh, ElementQuad1(), facets=fac, intorder=3)  # noqa: E731
    Babs = asm(B, fb(np.concatenate([top, side])))
    if len(gapf):
        Babs = Babs + asm(B, fb(gapf))

    zero_nodes = np.where(np.abs(mesh.p[1]) < 1e-12)[0]
    zero_nodes = zero_nodes[mesh.p[0, zero_nodes] <= d.r_front * MM + 1e-12]
    w_avg = (mesh.p[0, zero_nodes] + 1e-12)
    w_avg = w_avg / w_avg.sum()
    out = []
    for f in np.atleast_1d(freqs):
        w = 2 * np.pi * f
        k = w / air.c
        A = sps.csr_matrix((basis.N, basis.N), dtype=complex)
        for i, x in enumerate(R):
            med = x["medium"]
            if med[0] == "tube":
                rho_e, C_e, _ = tube_eff(f, med[1], air)
            elif med[0] == "slit":
                rho_e, C_e = slit_eff(f, med[1], air)
            elif med[0] == "eta":
                rho_e, C_e = air.rho, (1 - 1j * med[1]) / (air.rho * air.c ** 2)
            else:
                rho_e, C_e = air.rho, 1 / (air.rho * air.c ** 2)
            A = A + (air.rho / rho_e) * Ks[i] - (k * k * C_e * air.rho * air.c ** 2) * Ms[i]
        A = A + 1j * k * Babs

        # scattered-field absorbing condition on top / side of the exterior: dp/dn + jk p = dpb/dn + jk pb, pb = 2 cos(k (z - zp))
        def rhs_vec(fac, is_top):
            fbasis = fb(fac)

            @LinearForm
            def re(v, w_):
                zr = w_.x[1] - z_plate
                dpb = (-2 * k * np.sin(k * zr)) if is_top else 0.0 * zr
                return dpb * v * w_.x[0]

            @LinearForm
            def im(v, w_):
                zr = w_.x[1] - z_plate
                return k * 2 * np.cos(k * zr) * v * w_.x[0]
            return asm(re, fbasis) + 1j * asm(im, fbasis)
        b = rhs_vec(top, True) + rhs_vec(side, False)
        p = spla.spsolve(A.tocsc(), b)
        out.append((w_avg @ p[zero_nodes]) / 2.0)             # p_d / blocked pressure (2 p0, p0 = 1)
    info = dict(nel=int(mesh.t.shape[1]), ndof=int(basis.N), h_um=d.h_mesh * 1e3)
    return np.array(out), info


if __name__ == "__main__":
    pass
