"""Adversarial check of ledger I-019: TEAX + 4.4 dB drive vs current driver + 12 dB. Reuses audibility_reconciled.py up to its option loop (no plot/json writes).
    systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 python3 sim/acoustics/teax_drive_check.py"""
import pathlib, numpy as np
here = pathlib.Path(__file__).resolve().parent
src = (here / "audibility_reconciled.py").read_text().split("R = {}; cache = {}")[0].replace("__file__", repr(str(here / "audibility_reconciled.py")))
exec(compile(src, "ar", "exec"))
BASE = np.array([4.6, 5.7, 7.3]); LED = 0.73; CAP = 130.0
fr_act = fr_rms[:n] > fr_rms.max() * .1
def cur(x, gain):
    a = np.abs(x); fa = np.repeat(fr_act, fr)[:len(a)]
    dense = a.mean(); cont = a[:len(fa)][fa].mean(); bg = a[:len(fa)][~fa].mean()
    sparse = .18 * cont + .82 * bg
    return {k: v * 327 * gain for k, v in dict(dense=dense, cont=cont, sparse=sparse).items()}, 327 * gain * a.max()
rows = []
for lab, ex, gain, drv in [("today a", 0, 1, None), ("A idle", 0, 1, 0), ("A+12 (current driver)", 0, 1, 12),
                           ("TEAX+0", 7.6, 1.022, 0), ("TEAX+4.4", 7.6, 1.022, 4.4), ("TEAX+6", 7.6, 1.022, 6), ("TEAX+12", 7.6, 1.022, 12)]:
    base = y / pk0
    x = tp_limit(base * CEIL["a"], CEIL["a"]) if drv is None else lahead(base * CEIL["A"] * 10 ** (drv / 20), CEIL["A"])
    I, pk = cur(x, gain); L = band_levels(x, ex)
    Lev = np.array([L[:, a:b].max(1) for a, b in ev])
    rt = {k: [CAP / (b + v + LED) for b in BASE] for k, v in I.items()}
    mg = {}
    for an, av in amb.items():
        m = (Lev - np.maximum(q, av - 4)[None, :])[:, SEL].max(1); mg[an] = (float(np.median(m)), float(m.min()))
    rows.append((lab, pk, I, rt, mg))
    print("%-22s pk %.0f mA | mean dense/cont/sparse %.1f/%.1f/%.1f | rt nom %.1f/%.1f/%.1f (low-base %.1f cont, high-base %.1f cont)" % (lab, pk, I["dense"], I["cont"], I["sparse"], rt["dense"][1], rt["cont"][1], rt["sparse"][1], rt["cont"][0], rt["cont"][2]))
    print("     median(worst) margin: " + " | ".join("%s %+.1f(%+.1f)" % (a[:10], *v) for a, v in mg.items()))
