#!/usr/bin/env python3
"""Pick the mic-duct mesh (sub-audio-in issue 3, task D2): real Saatifil Acoustex products in the current duct.

Candidates: thin (<= 50 um), <= 60 rayl (the S8 'thin mesh' rule and the acoustics.yaml B option: mouth mesh <= 60 rayl).
Data: Saatifil Acoustex technical data sheet (marianinc.com copy, PDF modified 2024-09-26, SHA-256 dba5071d3a0dfcb1):
specific airflow resistance (MKS rayl), open area, thickness. These are DC/low-frequency numbers.
Ultrasonic extension (both [A], swept so they bracket the answer):
- inertance m_s = rho * (t + 1.7 * a) / open_area  (perforate end correction 0.85 a per side, a = pore radius)
- viscous resistance rises above DC once the boundary layer (8.7 um at 63 kHz) approaches the pore radius:
  r(f) swept x1 and x2 of the sheet value.
Places: 'mouth' (the hex window, ~9.4 mm2) and 'floor' (bore floor, D1.0). Scenario = hw/current.yaml acoustic_scenario.
Reports per candidate: change of the 20-96 kHz mean vs no mesh, the in-band peak (level, frequency) vs no mesh.
Run (fenced): systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 python3 sim/checks/mesh_pick.py
"""
import json
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "sim/acoustics"))
from geometry import MM, design, load as load_geom  # noqa: E402
from port import F_GRID, calibrate_mic, db, ratio, scenarios  # noqa: E402

RHO = 1.2
# name: (rayl, open area, thickness um, pore um or None) - Acoustex sheet; performance grades list no pore size
CANDS = {
    "Acoustex 026": (26, 0.37, 45, 45),
    "Acoustex 030 (performance)": (30, 0.32, 43, None),
    "Acoustex 042 (performance)": (42, 0.29, 46, None),
    "Acoustex 020": (20, 0.38, 62, 68),
    "Acoustex 065": (65, 0.24, 60, 30),
}
PORE_ASSUMED = 35.0   # um, performance grades [A] (between the 026 and 065 standard pores)


def main():
    g = load_geom(None)
    scen = design().acoustic_scenario
    gg, oo = scenarios(g)[scen]
    mic = calibrate_mic(g, "ideal")
    f = F_GRID
    cap = (f >= 20e3) & (f <= 96e3)
    H0 = ratio(f, gg, oo, mic, "ideal")
    d0 = db(H0)
    k0 = int(np.argmax(np.where(cap, d0, -1e9)))
    base = dict(mean_20_96=round(float(d0[cap].mean()), 2), peak_db=round(float(d0[k0]), 2), peak_khz=round(f[k0] / 1e3, 1))
    rows = []
    for name, (r, phi, t, pore) in CANDS.items():
        a = (pore if pore else PORE_ASSUMED) * 1e-6 / 2
        m_s = RHO * (t * 1e-6 + 1.7 * a) / phi
        for place in ("mouth", "floor"):
            for rf in (1.0, 2.0):
                H = ratio(f, gg, replace(oo, mesh=place, r_mesh=float(r * rf), m_mesh=m_s), mic, "ideal")
                d = db(H)
                k = int(np.argmax(np.where(cap, d, -1e9)))
                rows.append(dict(mesh=name, place=place, r_rayl=r * rf, m_s_kg_m2=round(m_s, 6),
                                 d_mean_20_96_db=round(float(d[cap].mean() - d0[cap].mean()), 2),
                                 peak_db=round(float(d[k]), 2), d_peak_db=round(float(d[k] - d0[k0]), 2), peak_khz=round(f[k] / 1e3, 1)))
            # resistance-only (the old model) for comparison
            H = ratio(f, gg, replace(oo, mesh=place, r_mesh=float(r), m_mesh=0.0), mic, "ideal")
            d = db(H)
            k = int(np.argmax(np.where(cap, d, -1e9)))
            rows.append(dict(mesh=name, place=place, r_rayl=r, m_s_kg_m2=0.0, d_mean_20_96_db=round(float(d[cap].mean() - d0[cap].mean()), 2),
                             peak_db=round(float(d[k]), 2), d_peak_db=round(float(d[k] - d0[k0]), 2), peak_khz=round(f[k] / 1e3, 1), note="resistance only"))
    out = dict(src="sim/checks/mesh_pick.py", date="2026-10-07", scenario=scen, no_mesh=base, rows=rows,
               data="Saatifil Acoustex TDS (marianinc copy, mod 2024-09-26, SHA-256 dba5071d3a0dfcb1)")
    od = ROOT / "sim/out/acoustics"
    od.mkdir(parents=True, exist_ok=True)
    (od / "mesh_pick.json").write_text(json.dumps(out, indent=1))
    print("scenario", scen, "no mesh:", base)
    for x in rows:
        print(x)


if __name__ == "__main__":
    main()
