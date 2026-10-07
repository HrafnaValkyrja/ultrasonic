#!/usr/bin/env python3
"""Waterproof membrane vs open mesh in the mic duct (reg-pod-body issue 5, docs/research/sealing-and-service.md).

A non-porous hydrophobic membrane (ePTFE acoustic vent class) acts as a limp mass: modelled as r 5 rayl + specific
inertance = its surface density (2/5/10/20 g/m2 [A: typical vent range]) at the window mouth or the hex-seat floor of
the current duct (port.Opt.m_mesh). Prints the change of the 20-96 kHz mean and at 25/40/60/80/96 kHz vs no cover.
Run (fenced): systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 python3 sim/checks/membrane_loss.py
"""
import sys
from dataclasses import replace
import numpy as np
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "sim/acoustics"))
from geometry import design, load as load_geom
from port import F_GRID, calibrate_mic, db, ratio, scenarios
g = load_geom(None); gg, oo = scenarios(g)[design().acoustic_scenario]; mic = calibrate_mic(g, "ideal"); f = F_GRID
cap = (f >= 20e3) & (f <= 96e3); d0 = db(ratio(f, gg, oo, mic, "ideal"))
for place in ("mouth", "floor"):
    for gsm in (2, 5, 10, 20):
        H = ratio(f, gg, replace(oo, mesh=place, r_mesh=5.0, m_mesh=gsm / 1000.0), mic, "ideal"); d = db(H)
        i = [int(np.argmin(abs(f - x))) for x in (25e3, 40e3, 60e3, 80e3, 96e3)]
        print(place, gsm, "g/m2 mean d", round(float(d[cap].mean() - d0[cap].mean()), 1), "dB; d at 25/40/60/80/96k", [round(float(d[k] - d0[k]), 1) for k in i])
