#!/usr/bin/env python3
"""sim/fw/l2.py: comparison level L2 (FWSIM-R7, R13, R14): sim/e2e scenarios with the firmware DSP + output stage in the loop.

The host firmware build (sim/fw/fwlib.py) replaces stages.DspStage ('dsp') and stages.PwmShaper ('shaper'): FwDsp runs fw_hop on
the ADF1 words (stages.pcm_to_adf_words of the AdfDecimator D1 output) with injected time (power-on hold included) and exports the
12.5 kS/s tap as 'dsp'; FwShaper returns the firmware CCR stream as duty. Scenarios that feed the shaper directly
(chain.image_tone_test) get the firmware output stage alone (fw_dsp_out). Then every metric of the scenario is computed exactly as
for the Python chain. Runs the Python reference too and prints both, with 'no WARN-would-pass may become FAIL' as the gate.

  python3 sim/fw/l2.py [--variants py B slim A] [--scenarios T1 T2 T3 T6 D17 lat R15] [--json PATH]
Fenced: systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 python3 sim/fw/l2.py
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path[:0] = [str(HERE), str(REPO / "sim/e2e"), str(REPO / "sim/dsp")]
import chain as ch  # noqa: E402
import fwlib  # noqa: E402
import pipeline as pl  # noqa: E402
import stages as sg  # noqa: E402

OUT = REPO / "sim/out/fw"
_ORIG_CHAIN, _ORIG_SHAPER = sg.default_chain, sg.PwmShaper
VARIANT_KNOBS = {"B": {"algo": 2, "b_variant": 0}, "slim": {"algo": 2, "b_variant": 1}, "A": {"algo": 1}}
STATE = {"variant": "B", "t0_us": 0}
POWER_ON_SCENES = ("T6",)          # scenes that score the power-on itself; elsewhere the pod was switched on long before (t0 = 1 s)
_NOISE: dict = {}


def knobs_from(p):
    v = STATE["variant"]
    k = dict(VARIANT_KNOBS[v], transient_only=int(bool(p["transient_only"])), volume_cdb=int(round(p["volume_db"] * 100)),
             ceiling_cdb=int(round(p["ceiling_dbfs"] * 100)), squelch_cdb=int(round(p["squelch_dbfs"] * 100)))
    return k


def noise_for(p):
    """stages.DspStage calibration (matched: the unit's own noise scale) for the variant's band layout."""
    if STATE["variant"] == "A":
        return None
    nb, hop = (16, 256) if STATE["variant"] == "slim" else (28, 128)
    ns = p["mic_noise_scale"] if p.get("noise_cal", "matched") == "matched" else 1.0
    key = (nb, hop, round(ns, 4))
    if key not in _NOISE:
        x = pl.decimate_to_fs(pl.microphone(np.zeros(int(0.5 * sg.FS_AC)), seed=99, noise_scale=ns))
        c = pl.BConfig(n_bands=nb, hop=hop, transient_only=False, noise_band=None)
        _NOISE[key] = pl.algo_b(x, c)[1]["band_energy"].mean(axis=0)
    return _NOISE[key]


class FwDsp(sg.Stage):
    id, in_unit, out_unit, status = "dsp", "FS @200k", "duty-FS @12.5k", "real"

    def process(self, s, ctx):
        fw = fwlib.Firmware(knobs_from(ctx.p), noise=noise_for(ctx.p))
        r = fw.run(sg.pcm_to_adf_words(s.x), t0_us=STATE["t0_us"])
        ctx.side["fw_res"] = r
        ctx.side["dsp_latency_sim_s"] = 8 / sg.FS_DSP
        return sg.Sig(r["dsp"].astype(float), sg.FS_DSP, "duty", dict(s.meta, algo=STATE["variant"], fw=True))


class FwShaper(sg.Stage):
    id, in_unit, out_unit, status = "shaper", "duty @12.5k", "duty-quantised @200k", "real"

    def process(self, s, ctx):
        r = ctx.side.pop("fw_res", None)
        if r is None:                                    # shaper fed directly (image_tone_test): firmware output stage alone
            fw = fwlib.Firmware(knobs_from(ctx.p))
            ccr, peak, sqp = fw.out_stage(s.x)
            sq_frac = float(sqp.sum()) / max(len(ccr), 1)
        else:
            ccr, peak = r["ccr"], r["peak"]
            sq_frac = float(np.mean(r["sq"]))
        duty = sg.ccr_to_duty(ccr)
        ctx.side.update(squelched_frac=sq_frac, x_interp_peak=float(np.max(peak)) if len(peak) else 0.0,
                        x_sample_peak=float(np.max(np.abs(s.x))) if len(s.x) else 0.0, ccr_stream_peak=float(np.max(np.abs(duty))) if len(duty) else 0.0)
        return sg.Sig(duty, sg.FS_PWM, "duty", dict(s.meta, levels=201, fw=True))


def fw_chain(fw=None):
    ch_ = _ORIG_CHAIN()
    return [FwDsp() if st.id == "dsp" else FwShaper() if st.id == "shaper" else st for st in ch_]


@dataclasses.dataclass
class SlimBConfig(pl.BConfig):
    """slim B in the Python reference: 16 bands, 256-sample hop (no overlap); V4-cycles.yaml B_slim1"""
    hop: int = 256
    n_bands: int = 16


_ORIG_BCFG = pl.BConfig
PY_OVER = {"py": {}, "py_slim": {}, "py_A": {"algo": "A"}}


def use(variant):
    pl.BConfig = SlimBConfig if variant == "py_slim" else _ORIG_BCFG
    if variant.startswith("py"):
        sg.default_chain, sg.PwmShaper = _ORIG_CHAIN, _ORIG_SHAPER
    else:
        STATE["variant"] = variant
        sg.default_chain, sg.PwmShaper = fw_chain, FwShaper


SCN = {"T1": ch.scn_T1, "T2": ch.scn_T2, "T3": ch.scn_T3, "T6": ch.scn_T6, "D17": ch.scn_D17, "lat": ch.scn_lat, "R15": ch.scn_R15}


def run(variants, scenarios, seed=1):
    out = {}
    for v in variants:
        use(v)
        for sc in scenarios:
            t0 = time.time()
            STATE["t0_us"] = 0 if sc in POWER_ON_SCENES else 1_000_000
            M, info, taps, ctx, st = SCN[sc](seed=seed, over=dict(PY_OVER.get(v, {})))
            del taps
            for m in M:
                d = m.as_dict(st)
                out.setdefault(m.id, {})[v] = dict(value=d["value"], status=d["status"], would_pass=d["would_pass"], op=m.op, thr=m.thr)
            print(f"  {v:5s} {sc:4s} {time.time() - t0:6.1f} s", flush=True)
    use("py")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--variants", nargs="*", default=["py", "B", "py_slim", "slim", "py_A", "A"])
    ap.add_argument("--scenarios", nargs="*", default=list(SCN))
    ap.add_argument("--json", type=Path, default=OUT / "l2.json")
    a = ap.parse_args(argv)
    res = run(a.variants, a.scenarios)
    regress = []
    print(f"\n{'metric':36s} {'need':>12s} " + " ".join(f"{v:>16s}" for v in a.variants))
    for mid, by in res.items():
        r0 = next(iter(by.values()))
        cells = []
        for v in a.variants:
            x = by.get(v)
            cells.append("-" if x is None else f"{x['value']:9.2f} {'ok' if x['would_pass'] else 'NO':>2s} {x['status'][:4]}")
            ref = {"B": "py", "slim": "py_slim", "A": "py_A"}.get(v)
            if ref and x and ref in by and by[ref]["would_pass"] and not x["would_pass"]:
                regress.append(f"{mid} [{v}]: {ref} {by[ref]['value']} -> fw {x['value']} (need {r0['op']} {r0['thr']})")
        print(f"{mid:36s} {r0['op']:>2s} {r0['thr']:<9g} " + " ".join(f"{c:>16s}" for c in cells))
    print("\nregressions (would-pass in Python, would-fail with firmware):", regress or "none")
    a.json.parent.mkdir(parents=True, exist_ok=True)
    a.json.write_text(json.dumps({"metrics": res, "regressions": regress, "variants": a.variants}, indent=1, default=float) + "\n")
    return 0 if not regress else 1


if __name__ == "__main__":
    sys.exit(main())
