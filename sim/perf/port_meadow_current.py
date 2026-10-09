#!/usr/bin/env python3
"""sim/perf/port_meadow_current.py: physical bridge current on the Port Meadow scene, for reconciling with docs/proof/electrical/d17-cost.md.
Bridge mean current = 0.327 A x mean|x| (x = duty fraction, d17-cost.md), x = |CCR-centre|/max|CCR-centre| x peak_ref (peak_ref = the config's max true peak).
Reports mean over all hops, over awake hops, and the call-active-hop fraction. Run: systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 python3 sim/perf/port_meadow_current.py"""
import sys, json
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import port_meadow as pm

real, _ = pm.scenes(54)
out = {}
for cfg in ["today", "A", "A+loud12"]:
    knobs, loud = pm.CONFIGS[cfg]
    S = A = H = AH = 0.0; mx = 0.0; pk = 0.0; rows = []; 
    for _, words, calls, t0 in real:
        r = pm.run_cfg(knobs, loud, words)
        n = len(r["mode"]); k0 = int(t0 / pm.HOP_S)
        cc = r["ccr"].reshape(n, -1).astype(float)
        c = np.bincount(r["ccr"]).argmax()
        dev = np.abs(cc - c).mean(axis=1)[k0:]
        a = ((r["mode"] & 0xFF) != pm.IDLE_ST)[k0:]
        sqm = (r["sq"][k0:] != 0); rows.append((dev, a, sqm)); mx = max(mx, np.abs(cc - c).max()); pk = max(pk, float(r["peak"][k0:].max()))
    dev = np.concatenate([d for d, _, _ in rows]); a = np.concatenate([x for _, x, _ in rows]); sqm = np.concatenate([q for _, _, q in rows])
    xs = dev / 128.0   # 128 = ARR/2 counts per unit duty (today: 32 counts = peak 0.251)
    out[cfg] = dict(sq_frac_all=round(float(sqm.mean()), 4), sq_frac_awake=round(float(sqm[a].mean()), 4), dev_sq=round(float(dev[sqm].mean()) if sqm.any() else -1, 3), dev_unsq=round(float(dev[~sqm].mean()), 3), peak=round(pk, 3), mean_x_all=round(float(xs.mean()), 5), bridge_mA_all=round(0.327e3 * float(xs.mean()), 3),
                    bridge_mA_awake_only=round(0.327e3 * float(xs[a].mean()), 3), awake_frac=round(float(a.mean()), 3))
    print(cfg, out[cfg], flush=True)
