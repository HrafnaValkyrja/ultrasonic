#!/usr/bin/env python3
"""K4-CONDUCT (2026-10-08): what the Hirose BM28 contact resistance does to (a) the +3V0 rail DC drop and (b) mic-supply noise from conducted aggressor current.

    source tools/env.sh && systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 python3 sim/checks/k4_conduct.py [--json]

Topology (hw/pod/k4/gen.py BM28_PINS, ECR-0020 rev 4): LDO U4 + cell charger are on M; +3V0 crosses the BM28 to P on pins 15, 30 and the 4 tab contacts 31-34
(V9 counts 3 +3V0 contacts: two signal pins + the power tab pair); GND returns on 15 signal pins (2,4,...,28 even + 16,17,18). C4 10 uF + C14 22 uF sit on P
(local decoupling). MIC_VDD comes from PA5 on P, filtered on M by R30 33 ohm + C13 (listed K4 filter, not credited here).
Contact R (Hirose BM28 catalog Aug 2019, fetched 2026-10-08, V9 k4_bm28_ds): signal <= 100 mohm max, power <= 30 mohm max (20 mV, 1 kHz, 1 mA). Typical not printed.
Method: the SAME aggressor lines as sim/noise/aggressors.yaml; the current that crosses the connector makes V = I * (R_3V0 + R_GND) in the loop
(bound: series sum, ignores that the mic sees only part of it). Two cases: BOUND = all line current crosses the connector (zero credit for P decoupling);
DIVIDER = only the share that the P-side caps (C4 10 uF + C14 22 uF, 50 % DC-bias derate, ESL 0.4 nH each) do not take: I_c = I * Zloc / (Zloc + R_loop).
Spur = mic PSRR chain exactly as sim/noise/budget.spur_dbfs / alias.chain (nominal, pessimistic = +20 dB), limit = tone_limit_dbfs (floor - 10 dB).
Not modelled: contact inductance (BM28 ~0.3-0.5 nH/contact [T], 3 contacts parallel: 0.15 nH = 0.4 mohm at 400 kHz, 3.8 mohm at 4 MHz, small vs R), crosstalk via the pins.
"""
import json, math, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "sim/noise"))
import budget, alias  # noqa: E402

def par(*r): return 1 / sum(1 / x for x in r)
CASES = {   # contact R per pin (ohm), count of +3V0 contacts of each kind, count of GND contacts carrying current
    "max_spec_all":   dict(r3_sig=0.100, n3_sig=2, r3_pwr=0.030, n3_pwr=2, rg=0.100, ng=15),
    "max_spec_nopwr": dict(r3_sig=0.100, n3_sig=2, r3_pwr=None,  n3_pwr=0, rg=0.100, ng=15),   # power tabs carry nothing (shield tabs, bad solder)
    "gnd_poor_4":     dict(r3_sig=0.100, n3_sig=2, r3_pwr=0.030, n3_pwr=2, rg=0.100, ng=4),    # only 4 GND pins near the sink share the return
}
def loop_r(c):
    r3 = par(*([c["r3_sig"]] * c["n3_sig"] + ([c["r3_pwr"]] * c["n3_pwr"] if c["r3_pwr"] else [])))
    return r3, c["rg"] / c["ng"]

def zloc(f):
    ys = [1 / (1 / (1j * 2 * math.pi * f * cap) + 1j * 2 * math.pi * f * 0.4e-9 + 0.01) for cap in (10e-6 * .5, 22e-6 * .5)]
    return abs(1 / sum(ys))

def main():
    params = budget.load_yaml(ROOT / "sim/noise/params.yaml"); agg = budget.load_yaml(ROOT / "sim/noise/aggressors.yaml")
    fl = budget.mic_floor(params, "white"); lim = fl["tone_limit_dbfs"]
    out = dict(limit_dbfs=round(lim, 1), floor_bin_dbfs=round(fl["bin_dbfs"], 1), cases={})
    # DC
    i_pk, i_mean = 0.326, 0.10    # sub-power: bridge peak 326 mA (R20 check PWR-I6), mean < 0.1 A (gen.py current budget)
    for cn, c in CASES.items():
        r3, rg = loop_r(c)
        d = dict(R_3V0_mohm=round(r3 * 1e3, 1), R_GND_mohm=round(rg * 1e3, 1), drop_peak_mV=round(i_pk * (r3 + rg) * 1e3, 1),
                 drop_mean_mV=round(i_mean * (r3 + rg) * 1e3, 1), worst_contact_A=round(i_pk / (c["n3_sig"] + c["n3_pwr"]), 3))
        # AC lines
        rows = {"bound": [], "divider": []}
        for a in agg["aggressors"]:
            w = a["wave"]
            if a["id"] == "A07_USB_FS": continue          # docked only, D+/D- not on the +3V0/GND return
            if w["kind"] == "band_noise":
                f_list = [(50e3, w["i_rms_a"] * math.sqrt(2))]
            else:
                f_list = budget.lines(w)
            for mode in ("bound", "divider"):
                best = None
                for f, amp in f_list:
                    fo, att, dc = alias.chain(f)
                    if (a.get("sync") and dc) or not (20e3 <= fo <= 96e3) or f > params["model"]["f_max_net_hz"]: continue
                    ic = amp if mode == "bound" else amp * zloc(f) / (zloc(f) + r3 + rg)
                    vr = ic / math.sqrt(2) * (r3 + rg)
                    sp_n = budget.spur_dbfs(vr, f, att, params, "nominal"); sp_p = budget.spur_dbfs(vr, f, att, params, "pessimistic")
                    r = dict(agg=a["id"], f_hz=round(f), f_out_hz=round(fo), v_uV=round(vr * 1e6, 2), spur_nom=round(sp_n, 1), spur_pes=round(sp_p, 1),
                             margin_nom=round(lim - sp_n, 1), margin_pes=round(lim - sp_p, 1))
                    if best is None or r["margin_pes"] < best["margin_pes"]: best = r
                if best: rows[mode].append(best)
        for m in rows: rows[m].sort(key=lambda r: r["margin_pes"])
        d["worst_bound"] = rows["bound"][0] if rows["bound"] else None
        d["worst_divider"] = rows["divider"][0] if rows["divider"] else None
        d["all_divider"] = rows["divider"]
        # wanted-signal term: 0.32 A FS bridge current (params bridge.i_fs_a) at 50 kHz through the same loop; coherent with the transmit tone (NOT noise): mic hears the tx acoustically anyway
        vt = params["bridge"]["i_fs_a"] / math.sqrt(2) * (r3 + rg)
        d["tx_coherent_term"] = dict(v_mV=round(vt * 1e3, 2), spur_nom_dbfs=round(budget.spur_dbfs(vt, 50e3, 0.0, params, "nominal"), 1))
        out["cases"][cn] = d
    if "--json" in sys.argv: print(json.dumps(out, indent=1))
    else:
        print(f"limit {out['limit_dbfs']} dBFS/tone, floor/bin {out['floor_bin_dbfs']}")
        for cn, d in out["cases"].items():
            print(cn, {k: v for k, v in d.items() if k not in ("all_divider",)})
    (ROOT / "sim/out").mkdir(exist_ok=True); (ROOT / "sim/out/k4_conduct.json").write_text(json.dumps(out, indent=1))
main()
