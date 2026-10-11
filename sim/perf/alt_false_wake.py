"""sim/perf/alt_false_wake.py: false-wake alternatives on Port Meadow with a train/holdout split (docs/sim/alt-false-wake.md).
Even-index clips = train (choose the knob value), odd = holdout (report). Quiet scenes (silence, house walk) count in both.
Knobs: idle_confirm (ALT-1), idle_width_max (ALT-2), idle_adapt_pct (ALT-3); all default 0 = bit-identical to shipping B.
    systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 python3 sim/perf/alt_false_wake.py --json out.json"""
import argparse, json, sys, time
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import port_meadow as pm  # noqa: E402

FRAC = {"dense": 0.81, "walk": 0.40, "dusk": 0.18}
GRID = [("B", {}), ("c2", {"idle_confirm": 2}), ("c3", {"idle_confirm": 3}), ("c4", {"idle_confirm": 4}),
        ("w15", {"idle_width_max": 15}), ("w25", {"idle_width_max": 25}), ("w40", {"idle_width_max": 40}), ("w60", {"idle_width_max": 60}),
        ("a300", {"idle_adapt_pct": 300}), ("a500", {"idle_adapt_pct": 500}), ("a800", {"idle_adapt_pct": 800}), ("a1200", {"idle_adapt_pct": 1200})]
BASEK = {"lim_lookahead": 1, "loud_db": 0}


def agg(scs, knobs):
    t = dict(dur=0, calls=0, wake=0, sound=0, fw=0, fa_hops=0, hops=0, awake_hops=0, awake_sq_hops=0, sq_hops=0, rms_awake=0.0, lat=[], lvl=[])
    for _, w, calls, t0 in scs:
        s = pm.score(pm.run_cfg({**BASEK, **knobs}, False, w), calls, t0)
        for k in t:
            t[k] = t[k] + s[k]
    return t


def metrics(real_t, quiet_t):
    t = {k: real_t[k] + quiet_t[k] for k in real_t if k not in ("lat", "lvl")}
    L = np.array(real_t["lat"] or [np.nan])
    aw = t["awake_hops"] / t["hops"]
    base_a = real_t["awake_hops"] / real_t["hops"]
    rms = real_t["rms_awake"] / max(real_t["awake_hops"], 1)
    sqa = real_t["sq_hops"] / real_t["hops"]
    fa = real_t["fa_hops"] / real_t["hops"]
    m = dict(wake=round(real_t["wake"] / real_t["calls"], 4), fwpm=round((real_t["fw"] + quiet_t["fw"]) / (real_t["dur"] + quiet_t["dur"]) * 60, 2),
             p50=round(float(np.nanmedian(L)), 1), p95=round(float(np.nanpercentile(L, 95)), 1), fa_frac=round(fa, 4), calls=real_t["calls"])
    m["_aw"] = (base_a, rms, sqa, fa)
    return m


def hours(m, ref_fa):
    base_a, rms, sqa, fa = m["_aw"]
    out = {}
    for n, f in FRAC.items():
        f2 = min(1.0, max(0.0, f + (fa - ref_fa)))        # scenario awake fraction shifted by the change in false-awake time
        ma = pm.current(f2, sqa, rms, False)
        out[n] = round(130 * 0.85 / ma, 1)
    out["mA"] = round(pm.current(base_a, sqa, rms, False), 2)
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--json", type=Path); a = ap.parse_args()
    t0 = time.time()
    real, quiet = pm.scenes(54)
    tr, ho = real[0::2], real[1::2]
    qt = agg(quiet, {})  # quiet scenes per config below
    res = {}
    for name, kn in GRID:
        kn = {**kn}
        q = agg(quiet, kn)
        res[name] = {}
        for sp, sc in (("train", tr), ("hold", ho)):
            m = metrics(agg(sc, kn), q)
            res[name][sp] = m
        print(name, {sp: {k: v for k, v in res[name][sp].items() if k != "_aw"} for sp in ("train", "hold")}, flush=True)
    for sp in ("train", "hold"):
        ref = res["B"][sp]["_aw"][3]
        for name in res:
            res[name][sp]["h"] = hours(res[name][sp], ref)
            res[name][sp].pop("_aw")
    res["_runtime_s"] = round(time.time() - t0, 1)
    if a.json:
        a.json.write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))

main()
