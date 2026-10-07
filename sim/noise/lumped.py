"""Lumped R/L/C extraction of selected nets of a board, a linear AC solver, and a SPICE writer.

One element list is the single source of truth: `Network.to_spice()` writes it for ngspice and
`Network.ac()` solves it (MNA, numpy), so the two can be cross-checked (budget.py --selfcheck).

Model (quasi-static, valid to a few MHz on a 34 x 13 mm board, see docs/sim/layout-noise.yaml `limits`):
  trace segment : R_dc = rho*l/(w*t)  +  loop L = L'(w,h)*l, L' = Z0air(w,h)/c (Hammerstad microstrip, air),
                  h = dielectric height to the In1 plane. Return assumed directly beneath (HF image regime).
  via barrel    : R = rho*h/(pi*(d+t_plate)*t_plate), L = mu0/(2 pi) h [ln(4h/d)+1] per layer step.
  GND plane     : DC resistive mesh (plane.py) Kron-reduced to the GND via ports (low-f / spreading regime).
Not modelled: skin effect (< 30 % on R at 4 MHz for 35 um Cu), proximity/mutual L between series segments,
plane slot detours at HF, trace-to-plane C (see couple.py for coupling C).
"""
from __future__ import annotations

import math
import re
from collections import defaultdict

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spl

from pcbgeom import COPPER, height_to_plane, seg_dist

MU0 = 4e-7 * math.pi
C0 = 299792458.0
RHO_CU = 1.72e-8  # ohm m, annealed Cu at 20 C. Plated barrels/foils are somewhat higher: +10 % is within the model error


def lprime_nH_per_mm(w: float, h: float, t: float = 0.0) -> float:
    """Loop inductance per mm of a trace (width w, height h over a plane), nH/mm. Hammerstad air-microstrip Z0 / c."""
    if t > 0:  # Wheeler/Hammerstad effective width for finite thickness
        dw = (t / math.pi) * (1 + math.log(4 * math.pi * w / t)) if w / h < 1 / (2 * math.pi) else (t / math.pi) * (1 + math.log(2 * h / t))
        w = w + dw
    u = w / h
    z0 = 60 * math.log(8 / u + u / 4) if u <= 1 else 120 * math.pi / (u + 1.393 + 0.667 * math.log(u + 1.444))
    return z0 / C0 * 1e6


def via_rl(h_mm: float, drill_mm: float, t_plate_um: float = 20.0):
    h, d, t = h_mm * 1e-3, drill_mm * 1e-3, t_plate_um * 1e-6
    R = RHO_CU * h / (math.pi * (d + t) * t)
    L = MU0 / (2 * math.pi) * h * (math.log(4 * h / d) + 1)
    return R, L


def parse_si(s: str) -> float | None:
    """'100n' '2u2' '4k7' '0.1' '1M' '22u' '15p' -> float. None if not a plain value."""
    s = s.strip().replace("µ", "u")
    m = re.fullmatch(r"(\d+)([pnumkKMR])(\d+)", s)  # 2u2 style
    mult = {"p": 1e-12, "n": 1e-9, "u": 1e-6, "m": 1e-3, "k": 1e3, "K": 1e3, "M": 1e6, "R": 1.0}
    if m:
        return float(f"{m.group(1)}.{m.group(3)}") * mult[m.group(2)]
    m = re.fullmatch(r"([0-9.]+)([pnumkKMR]?)", s)
    if m:
        return float(m.group(1)) * mult.get(m.group(2), 1.0)
    return None


def read_bom(path: str) -> dict[str, tuple[str, str]]:
    """hw/pod/bom_jlc.csv -> {ref: (comment, footprint)}"""
    import csv
    out = {}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            for ref in row["Designator"].replace('"', "").split(","):
                out[ref.strip()] = (row["Comment"], row["Footprint"])
    return out


class UF:
    def __init__(self): self.p = {}
    def find(self, a):
        self.p.setdefault(a, a)
        while self.p[a] != a:
            self.p[a] = self.p[self.p[a]]
            a = self.p[a]
        return a
    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[rb] = ra


class Network:
    """Linear R/L/C network with named nodes. Node '0' is the AC reference."""

    def __init__(self):
        self.elems: list[dict] = []
        self.nodes: dict[str, int] = {"0": 0}

    def node(self, name: str) -> int:
        if name not in self.nodes:
            self.nodes[name] = len(self.nodes)
        return self.nodes[name]

    def add(self, kind: str, n1: str, n2: str, val: float, **tag):
        assert kind in "RLC" and val > 0, (kind, n1, n2, val, tag)
        self.node(n1); self.node(n2)
        self.elems.append(dict(kind=kind, n1=n1, n2=n2, val=val, **tag))

    # ---- AC solve --------------------------------------------------------------------------------
    def _arrays(self):
        a = np.array([self.nodes[e["n1"]] for e in self.elems])
        b = np.array([self.nodes[e["n2"]] for e in self.elems])
        v = np.array([e["val"] for e in self.elems])
        k = np.array(["RLC".index(e["kind"]) for e in self.elems])
        return a, b, v, k

    def admittances(self, f: float, arr=None):
        a, b, v, k = arr or self._arrays()
        w = 2 * math.pi * f
        y = np.empty(len(v), dtype=complex)
        y[k == 0] = 1.0 / v[k == 0]
        y[k == 1] = 1.0 / (1j * w * v[k == 1])
        y[k == 2] = 1j * w * v[k == 2]
        return y

    def ac(self, freqs, port_pairs, probes, gmin=1e-12, want_currents=False):
        """Transimpedance. For each (plus,minus) in `port_pairs` inject 1 A (plus -> minus through the source),
        return {pair_index: {probe_index: complex array over freqs}} where a probe is (node_a, node_b) volts a-b.
        With want_currents also return element currents per pair and frequency (complex array [n_elem])."""
        arr = self._arrays()
        a, b, _, _ = arr
        n = len(self.nodes)
        res = {i: {j: np.zeros(len(freqs), dtype=complex) for j in range(len(probes))} for i in range(len(port_pairs))}
        cur = {i: [] for i in range(len(port_pairs))} if want_currents else None
        pidx = [(self.nodes[p], self.nodes[m]) for p, m in port_pairs]
        qidx = [(self.nodes[p], self.nodes[m]) for p, m in probes]
        for fi, f in enumerate(freqs):
            y = self.admittances(f, arr)
            rows = np.r_[a, b, a, b]
            cols = np.r_[a, b, b, a]
            vals = np.r_[y, y, -y, -y]
            Y = sp.coo_matrix((vals, (rows, cols)), shape=(n, n)).tocsc()
            Y = Y + sp.identity(n, dtype=complex, format="csc") * gmin
            Yr = Y[1:, 1:].tocsc()  # node 0 is the reference
            lu = spl.splu(Yr)
            I = np.zeros((n - 1, len(pidx)), dtype=complex)
            for j, (p, m) in enumerate(pidx):
                if p > 0: I[p - 1, j] += 1.0
                if m > 0: I[m - 1, j] -= 1.0
            V = np.vstack([np.zeros((1, len(pidx)), dtype=complex), lu.solve(I)])
            for j in range(len(pidx)):
                for q, (pa, pb) in enumerate(qidx):
                    res[j][q][fi] = V[pa, j] - V[pb, j]
                if want_currents:
                    cur[j].append((V[a, j] - V[b, j]) * y)
        if want_currents:
            return res, {j: np.array(c) for j, c in cur.items()}
        return res

    # ---- SPICE -----------------------------------------------------------------------------------
    def to_spice(self, name: str, ports: list[str] | None = None, select=None, header: str = "") -> str:
        """Write elements (optionally filtered by select(elem)->bool) as a .subckt (with ports) or a flat deck."""
        lines = [f"* {name}" + (f": {header}" if header else ""), "* generated by sim/noise/lumped.py; node 0 is the reference"]
        if ports is not None:
            lines.append(f".subckt {name} " + " ".join(ports))
        cnt = defaultdict(int)
        for e in self.elems:
            if select and not select(e):
                continue
            cnt[e["kind"]] += 1
            lines.append(f'{e["kind"]}{cnt[e["kind"]]} {e["n1"]} {e["n2"]} {e["val"]:.6g}')
        if ports is not None:
            lines.append(".ends")
        return "\n".join(lines) + "\n"


# ---- graph builder ------------------------------------------------------------------------------------
def _key(layer, x, y):
    return (layer, round(x * 1000), round(y * 1000))


def add_nets(net: Network, geom: dict, nets: set[str], plane_red: dict | None = None, plane_net: str = "GND",
             t_plate_um: float = 20.0, plane_r_max: float = 0.5, tag_prefix: str = "", planes: list | None = None):
    """Add R/L elements for every track, via and pad-join of `nets`; a Kron-reduced plane network per plane.

    planes: [{net, layer, red}] (2026-10-07: Phase 2 has In1 GND and In2 +3V0). The old single-plane arguments
    (plane_red, plane_net on In1.Cu) still work and mean planes=[{net: plane_net, layer: "In1.Cu", red: plane_red}].

    Returns info dict: pad_node {ref.num -> node}, floating_pads, counts, per-net totals.
    """
    st = geom["stackup"]
    cu = {k: v / 1000.0 for k, v in st["copper_um"].items()}  # mm
    uf = UF()
    segs = [dict(s) for s in geom["segments"] if s["net"] in nets]
    vias = [dict(v, gi=gi) for gi, v in enumerate(geom["vias"]) if v["net"] in nets]
    pads = [p for p in geom["pads"] if p["net"] in nets]

    # points that may land on a segment's interior (T-junctions): endpoints, via centres, pad centres
    pts_by = defaultdict(list)  # (net, layer) -> [(x, y)]
    for s in segs:
        pts_by[(s["net"], s["layer"])] += [(s["x1"], s["y1"]), (s["x2"], s["y2"])]
    for v in vias:
        for L in COPPER:
            if COPPER.index(v["top"]) <= COPPER.index(L) <= COPPER.index(v["bot"]):
                pts_by[(v["net"], L)].append((v["x"], v["y"]))
    for p in pads:
        for L in (COPPER if p["thru"] else [p["layer"]]):
            pts_by[(p["net"], L)].append((p["x"], p["y"]))
    split = []
    for s in segs:
        if s["arc"]:
            split.append(s); continue
        ts = []
        for (px, py) in pts_by[(s["net"], s["layer"])]:
            d, t = seg_dist(px, py, s)
            if d < 0.5 * s["w"] and 1e-3 < t < 1 - 1e-3 and min(math.hypot(px - s["x1"], py - s["y1"]), math.hypot(px - s["x2"], py - s["y2"])) > 5e-3:
                ts.append(t)
        ts = sorted(set(round(t, 4) for t in ts))
        cuts = [0.0] + ts + [1.0]
        for t0, t1 in zip(cuts[:-1], cuts[1:]):
            q = dict(s)
            q["x1"], q["y1"] = s["x1"] + t0 * (s["x2"] - s["x1"]), s["y1"] + t0 * (s["y2"] - s["y1"])
            q["x2"], q["y2"] = s["x1"] + t1 * (s["x2"] - s["x1"]), s["y1"] + t1 * (s["y2"] - s["y1"])
            q["length"] = s["length"] * (t1 - t0)
            split.append(q)
    segs = split

    # via nodes on each layer, barrel links, pad merges
    pad_names = {}
    for p in pads:
        for L in (COPPER if p["thru"] else [p["layer"]]):
            pad_names.setdefault(_key(L, p["x"], p["y"]), f'{p["ref"]}_{p["num"]}')
    for v in vias:
        i0, i1 = COPPER.index(v["top"]), COPPER.index(v["bot"])
        for L in COPPER[i0:i1 + 1]:
            uf.find(_key(L, v["x"], v["y"]))
    for s in segs:
        uf.find(_key(s["layer"], s["x1"], s["y1"])); uf.find(_key(s["layer"], s["x2"], s["y2"]))
    allkeys = list(uf.p)
    for p in pads:  # join endpoints / vias that sit inside a pad's copper to the pad node
        x0, y0, x1, y1 = p["bbox"]
        for L in (COPPER if p["thru"] else [p["layer"]]):
            pk = _key(L, p["x"], p["y"])
            uf.find(pk)
            for k in allkeys:
                if k[0] == L and x0 - 1e-3 <= k[1] / 1000 <= x1 + 1e-3 and y0 - 1e-3 <= k[2] / 1000 <= y1 + 1e-3:
                    uf.union(pk, k)

    # canonical node names: pad name if the component holds a pad, else generated
    comp_name, alias = {}, {}
    for k, nm in sorted(pad_names.items(), key=lambda kv: kv[1]):
        r = uf.find(k)
        if r not in comp_name:
            comp_name[r] = nm
        alias[nm] = comp_name[r]
    gen = [0]

    def nname(k):
        r = uf.find(k)
        if r not in comp_name:
            gen[0] += 1
            comp_name[r] = f"n{gen[0]}"
        return comp_name[r]

    nseg = 0
    seg_edges, via_edges = [], []
    tot = defaultdict(lambda: dict(R=0.0, L=0.0, segs=0))
    for s in segs:
        a, b = nname(_key(s["layer"], s["x1"], s["y1"])), nname(_key(s["layer"], s["x2"], s["y2"]))
        ln = s["length"]
        if a == b or ln <= 1e-6:
            continue
        seg_edges.append(dict(a=a, b=b, net=s["net"], layer=s["layer"], w=s["w"], x1=s["x1"], y1=s["y1"], x2=s["x2"], y2=s["y2"]))
        h, _ = height_to_plane(st, s["layer"])
        t = cu[s["layer"]]
        R = RHO_CU * (ln * 1e-3) / (s["w"] * 1e-3 * t * 1e-3)
        Lh = lprime_nH_per_mm(s["w"], h, t) * ln * 1e-9
        mid = f"m{nseg}"
        tag = dict(kind_="trace", net=s["net"], layer=s["layer"], w=s["w"], len=round(ln, 4),
                   xy=(round(s["x1"], 3), round(s["y1"], 3), round(s["x2"], 3), round(s["y2"], 3)))
        net.add("R", a, mid, R, **tag)
        net.add("L", mid, b, Lh, **tag)
        tot[s["net"]]["R"] += R; tot[s["net"]]["L"] += Lh; tot[s["net"]]["segs"] += 1
        nseg += 1

    if planes is None:
        planes = [dict(net=plane_net, layer="In1.Cu", red=plane_red)] if plane_red is not None else []
    ports = {}
    pl_ports = [dict() for _ in planes]
    nvia = 0
    for v in vias:
        vi = v["gi"]
        i0, i1 = COPPER.index(v["top"]), COPPER.index(v["bot"])
        for La, Lb in zip(COPPER[i0:i1], COPPER[i0 + 1:i1 + 1]):
            a, b = nname(_key(La, v["x"], v["y"])), nname(_key(Lb, v["x"], v["y"]))
            ia, ib = COPPER.index(La), COPPER.index(Lb)
            gap = st["dielectric_mm"][ia] + (cu[La] + cu[Lb]) / 2
            R, L = via_rl(gap, v["drill"], t_plate_um)
            tag = dict(kind_="via", net=v["net"], layer=f"{La}-{Lb}", xy=(round(v["x"], 3), round(v["y"], 3)))
            if a != b:
                via_edges.append((a, b, v["net"]))
                net.add("R", a, f"vm{vi}_{ia}", R, **tag)
                net.add("L", f"vm{vi}_{ia}", b, L, **tag)
            nvia += 1
        for k, pl in enumerate(planes):
            li = COPPER.index(pl["layer"])
            if v["net"] == pl["net"] and COPPER.index(v["top"]) <= li <= COPPER.index(v["bot"]):
                pl_ports[k][f"PL{vi}"] = (v["x"], v["y"], nname(_key(pl["layer"], v["x"], v["y"])))
    if planes:
        ports = pl_ports[0]

    nplane = 0
    for pl, pp in zip(planes, pl_ports):
        if pl["red"] is None or not pp:
            continue
        names = pl["red"]["names"]
        G = pl["red"]["G"]
        # red was built with port names as given by the caller (see plane_ports()); map them to nodes
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                g = -G[i, j]
                if g > 1.0 / plane_r_max:
                    net.add("R", pp[names[i]][2], pp[names[j]][2], 1.0 / g,
                            kind_="plane", net=pl["net"], layer=pl["layer"], xy=(*pp[names[i]][:2], *pp[names[j]][:2]))
                    nplane += 1
    pad_node = {f'{p["ref"]}.{p["num"]}': alias.get(f'{p["ref"]}_{p["num"]}', f'{p["ref"]}_{p["num"]}') for p in pads}
    floating = [k for k, n in pad_node.items() if not any(e["n1"] == n or e["n2"] == n for e in net.elems)]
    return dict(pad_node=pad_node, floating_pads=floating, n_segments=nseg, n_vias=nvia, n_plane_links=nplane,
                totals={k: dict(R_ohm=round(v["R"], 4), L_nH=round(v["L"] * 1e9, 3), segs=v["segs"]) for k, v in tot.items()},
                plane_ports=ports, all_plane_ports=pl_ports, seg_edges=seg_edges, via_edges=via_edges)


def plane_ports(geom: dict, plane_net: str = "GND", plane_layer: str = "In1.Cu"):
    """{port name: (x, y)} for every plane-net via that crosses the plane layer. Name = PL<global via index>."""
    k = COPPER.index(plane_layer)
    return {f"PL{gi}": (v["x"], v["y"]) for gi, v in enumerate(geom["vias"])
            if v["net"] == plane_net and COPPER.index(v["top"]) <= k <= COPPER.index(v["bot"])}
