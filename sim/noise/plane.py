"""Resistive mesh of a copper plane (the In1 GND zone) and its Kron reduction to a port network.

Why: below ~1 MHz the plane is a RESISTIVE return (current spreads), so shared-ground noise is I*R of the
real zone shape (cut by via antipads and keep-outs). Above that the return hugs the trace and the loop
inductance in lumped.py takes over. This module is DC/low-f only; see docs/sim/layout-noise.yaml limits.

    mesh = Mesh(zone, pitch=0.1, rs=1.13e-3)
    red = mesh.reduce({"v1": (x, y), "v2": (x, y)})   # k x k conductance matrix between the ports
"""
from __future__ import annotations

import numpy as np
import scipy.sparse as sp
import scipy.sparse.csgraph as csg
import scipy.sparse.linalg as spl
from matplotlib.path import Path as MPath


class Mesh:
    def __init__(self, zone: dict, pitch: float = 0.1, rs: float = 1.13e-3):
        self.pitch, self.rs = pitch, rs
        xs = [p[0] for poly in zone["polys"] for p in poly["outer"]]
        ys = [p[1] for poly in zone["polys"] for p in poly["outer"]]
        self.x0, self.y0 = min(xs), min(ys)
        nx = int(np.ceil((max(xs) - self.x0) / pitch)) + 1
        ny = int(np.ceil((max(ys) - self.y0) / pitch)) + 1
        gx, gy = np.meshgrid(self.x0 + (np.arange(nx) + 0.5) * pitch, self.y0 + (np.arange(ny) + 0.5) * pitch)
        pts = np.c_[gx.ravel(), gy.ravel()]
        inside = np.zeros(len(pts), dtype=bool)
        for poly in zone["polys"]:
            # KiCad hands back a fractured outline (holes joined by zero-width slits); winding is nonzero-safe.
            m = MPath(np.array(poly["outer"])).contains_points(pts)
            for h in poly["holes"]:
                m &= ~MPath(np.array(h)).contains_points(pts)
            inside |= m
        self.nx, self.ny, self.pts = nx, ny, pts
        self.mask = inside.reshape(ny, nx)
        self.area_mm2 = float(self.mask.sum()) * pitch * pitch
        self.zone_area_mm2 = zone["area_mm2"]

    def _laplacian(self):
        idx = -np.ones(self.mask.shape, dtype=np.int64)
        idx[self.mask] = np.arange(int(self.mask.sum()))
        g = 1.0 / self.rs
        r, c = [], []
        for a, b in ((idx[:, :-1], idx[:, 1:]), (idx[:-1, :], idx[1:, :])):
            ok = (a >= 0) & (b >= 0)
            r.append(a[ok]); c.append(b[ok])
        r, c = np.concatenate(r), np.concatenate(c)
        n = int(self.mask.sum())
        W = sp.coo_matrix((np.full(len(r), g), (r, c)), shape=(n, n))
        W = W + W.T
        L = sp.diags(np.asarray(W.sum(1)).ravel()) - W
        return idx, L.tocsr(), n

    def reduce(self, ports: dict[str, tuple[float, float]], port_radius: float = 0.175, r_contact: float = 1e-4):
        """Kron-reduce the mesh to the named ports. Each port ties to every cell within `port_radius` (a via land).

        Returns dict(names, G (k x k, siemens, a Laplacian), n_cells, orphan_ports, components_dropped).
        """
        idx, L, n = self._laplacian()
        names = list(ports)
        k = len(names)
        cell_xy = self.pts[self.mask.ravel()]
        rows, cols, orphan = [], [], []
        for j, nm in enumerate(names):
            px, py = ports[nm]
            d = np.hypot(cell_xy[:, 0] - px, cell_xy[:, 1] - py)
            sel = np.where(d <= port_radius)[0]
            if len(sel) == 0:  # port lands in a hole/outside copper: attach to the nearest cell, flag it
                sel = [int(np.argmin(d))]
                if d[sel[0]] > 2 * self.pitch + port_radius:
                    orphan.append(nm)
            rows += [n + j] * len(sel)
            cols += list(sel)
        gc = 1.0 / r_contact
        A = sp.coo_matrix((np.full(len(rows), gc), (rows, cols)), shape=(n + k, n + k))
        A = A + A.T
        # full conductance matrix = mesh Laplacian padded + contact Laplacian
        Lfull = sp.block_diag([L, sp.csr_matrix((k, k))]).tocsr()
        Lfull = Lfull + sp.diags(np.asarray(A.sum(1)).ravel()) - A
        Lfull = Lfull.tocsr()
        # drop connected components that contain no port (floating copper islands)
        ncomp, lab = csg.connected_components(Lfull != 0, directed=False)
        keep = np.isin(lab, np.unique(lab[n:]))
        dropped = int((~keep[:n]).sum())
        ii = np.where(keep[:n])[0]
        sel = np.r_[ii, np.arange(n, n + k)]
        Lk = Lfull[sel][:, sel].tocsc()
        ni = len(ii)
        Gii, Gip, Gpp = Lk[:ni, :ni], Lk[:ni, ni:], Lk[ni:, ni:]
        lu = spl.splu(Gii.tocsc())
        X = lu.solve(Gip.toarray())
        Gred = Gpp.toarray() - Gip.T @ X
        Gred = 0.5 * (Gred + Gred.T)
        return dict(names=names, G=Gred, n_cells=ni, orphan_ports=orphan, cells_dropped=dropped)


def reff(G: np.ndarray, i: int, j: int) -> float:
    """Effective resistance between ports i and j of a reduced Laplacian G (ohm)."""
    k = G.shape[0]
    e = np.zeros(k); e[i], e[j] = 1.0, -1.0
    Gp = np.linalg.pinv(G)
    return float(e @ Gp @ e)


def transfer_resistance(G: np.ndarray, src: int, snk: int, a: int, b: int) -> float:
    """Volts between ports a and b per ampere forced src->snk (ohm). Kelvin-error style metric."""
    k = G.shape[0]
    I = np.zeros(k); I[src], I[snk] = 1.0, -1.0
    V = np.linalg.pinv(G) @ I
    return float(V[a] - V[b])
