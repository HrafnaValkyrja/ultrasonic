#!/usr/bin/env python3
"""sim/fw/gen_vectors.py: golden vectors (FWSIM-R8) + comparison levels L0/L1 (FWSIM-R7) for the firmware DSP chain.

Vectors are generated from the numeric reference only: sim/e2e sources (chain.house_walk, chain.bats, chain.burst_train, tones)
-> sim/e2e stages AcousticPort, Microphone, SupplyInject, AdfDecimator (D1 stub) -> stages.pcm_to_adf_words (PDM-free) ->
int32 ADF1 words; reference taps from sim/dsp/pipeline.py algo_b (spec B, slim B) and algo_a's pre-gate signal. Stored in
sim/fw/vectors/<name>.npz with sha256 per array + scenario + seed + sim commit in sim/fw/vectors/manifest.yaml.

  gen_vectors.py            check: regenerate in memory, FAIL on any sha drift (no rewrite); then L1 (firmware vs reference taps,
                            thresholds fw/test/l1_thresholds.yaml) and L0 (host gcc -O2 vs clang-18 -O2 vs gcc -O0: bit-exact)
  gen_vectors.py --bless    rewrite vectors + manifest, print the L1 metric deltas old -> new
  gen_vectors.py --freeze   write fw/test/l1_thresholds.yaml from the measured L1 errors (first comparison only; then frozen)
  --json PATH               result rows for fw/tools/fwsim.py (stage dsp)
Run fenced (CLAUDE.md): systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 python3 sim/fw/gen_vectors.py
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import io
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import yaml
from scipy import signal

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path[:0] = [str(HERE), str(REPO / "sim/e2e"), str(REPO / "sim/dsp")]
import chain as ch  # noqa: E402
import fwlib  # noqa: E402
import pipeline as pl  # noqa: E402
import stages as sg  # noqa: E402

VEC = HERE / "vectors"
MANIFEST = VEC / "manifest.yaml"
THRESH = REPO / "fw/test/l1_thresholds.yaml"
OUTJ = REPO / "sim/out/fw/l1.json"
SWEEP_F = np.geomspace(22e3, 83e3, 12)
SEG_S = 0.06
DELAY = {"B": 8, "slim": 8, "A": 17}          # firmware 12.5 kS/s sample n = reference n - DELAY (dsp.h)
FW_KNOBS = {"B": {"algo": 2, "b_variant": 0}, "slim": {"algo": 2, "b_variant": 1}, "A": {"algo": 1, "transient_only": 0}}
SQ_LAG = 125                                   # 10 ms at 12.5 kS/s: half the reference's centred 20 ms hold window
HOLD_HOPS = 470                                # power-on hold 300 ms = 469 hops of 0.64 ms (squelch forced; excluded from squelch agreement)

# name: (source builder, seed, transient_only, front end, variants compared)
SCENES = {
    "sweep": ("sweep", 11, 0, "D1", ("B", "slim", "A")),
    "bats": ("bats", 2, 1, "D1", ("B", "slim")),
    "house": ("house", 1, 1, "D1", ("B", "slim")),
    "silence": ("silence", 4, 1, "D1", ("B", "slim")),
    "loud": ("loud", 5, 1, "D1", ("B", "slim")),
    "bats_d2": ("bats", 3, 1, "D2", ("B",)),
}


def sim_commit():
    p = subprocess.run(["git", "-C", str(REPO), "log", "-1", "--format=%h %cs", "--", "sim/dsp", "sim/e2e"], capture_output=True, text=True)
    return p.stdout.strip() or "?"


def source(kind, seed):
    fs = ch.FS
    if kind == "sweep":
        seg = int(SEG_S * fs)
        t = np.arange(seg) / fs
        x = np.concatenate([np.sin(2 * np.pi * f * t) * np.hanning(seg) ** 0.1 for f in SWEEP_F])
        return ch.lvl(x, 60.0)
    if kind == "bats":
        return ch.bats(0.8, seed, 70.0)[0]
    if kind == "house":
        return ch.house_walk(2.0, seed, 0.0)[0][: int(1.6 * fs)]        # bursts 0.2-0.9 s, keys 1.2-1.5 s
    if kind == "silence":
        return np.zeros(int(0.8 * fs))
    if kind == "loud":
        n = int(0.6 * fs)
        return ch.lvl(ch.burst_train(40e3, np.arange(0.05, 0.55, 0.06), 8, n), 105)
    raise KeyError(kind)


def front(src_pa, seed, front_end):
    """Pa @400k -> ADF words: D1 = 200 kS/s after the AdfDecimator D1 stub; D2 = 400 kS/s words (firmware half-band)."""
    p = ch.make_params({"adf_mode": "D1"})
    ctx = sg.Ctx(p, np.random.default_rng(seed))
    s = sg.Sig(src_pa, ch.FS, "Pa")
    for st in (sg.AcousticPort(), sg.Microphone(), sg.SupplyInject()):
        s = st.process(s, ctx)
    if front_end == "D2":
        return sg.pcm_to_adf_words(s.x)
    return sg.pcm_to_adf_words(sg.AdfDecimator("D1").process(s, ctx).x)


_NOISE = {}


def noise_band(nb, hop):
    """stages.DspStage calibration (nominal mic, seed 99, 0.5 s, D2 decimation): the same numbers fw/gen/dsp_tables.h holds."""
    if (nb, hop) not in _NOISE:
        x = pl.decimate_to_fs(pl.microphone(np.zeros(int(0.5 * pl.FS_IN)), seed=99, noise_scale=1.0))
        c = pl.BConfig(n_bands=nb, hop=hop, transient_only=False, noise_band=None)
        _NOISE[(nb, hop)] = pl.algo_b(x, c)[1]["band_energy"].mean(axis=0)
    return _NOISE[(nb, hop)]


def floor_of(E, cfg):
    hop_s = cfg.hop / pl.FS
    a_up, a_dn = np.exp(-hop_s / cfg.floor_up_s), np.exp(-hop_s / cfg.floor_down_s)
    fl = E[0].copy()
    out = np.empty_like(E)
    for h, e in enumerate(E):
        fl = np.where(e > fl, a_up * fl + (1 - a_up) * e, a_dn * fl + (1 - a_dn) * e)
        out[h] = fl
    return out


def algo_a_base(x, f_lo=38e3, bw=3000.0, out_center=2750.0):
    """pipeline.algo_a up to the gate, verbatim (algo_a exports no pre-gate tap)."""
    t = np.arange(len(x)) / pl.FS
    mixed = x * np.cos(2 * np.pi * f_lo * t) * 2
    b = signal.firwin(255, out_center + bw / 2, fs=pl.FS)
    base = signal.fftconvolve(mixed, b, mode="same")
    hp = signal.butter(2, max(out_center - bw / 2, 300), "hp", fs=pl.FS, output="sos")
    base = signal.sosfilt(hp, base)
    return signal.resample_poly(base, 1, 16)


def reference(words, front_end, transient, variants):
    if front_end == "D2":
        pcm = pl.decimate_to_fs(sg.adf_words_to_pcm(words))
        pcm = np.concatenate([np.zeros(7), pcm])[: len(pcm)]       # firmware causal half-band: PCM delayed 7 samples (dsp.c)
    else:
        pcm = sg.adf_words_to_pcm(words)
    ref = {}
    for v in variants:
        if v == "A":
            ref["A_y"] = (algo_a_base(pcm) * 10 ** 1.5).astype(np.float32)
            continue
        nb, hop = (16, 256) if v == "slim" else (28, 128)
        cfg = pl.BConfig(n_bands=nb, hop=hop, transient_only=bool(transient), ceiling_dbfs=100.0, noise_band=noise_band(nb, hop))
        y, info = pl.algo_b(pcm, cfg)
        ref[f"{v}_y"] = y.astype(np.float32)
        ref[f"{v}_band"] = info["band_energy"].astype(np.float32)
        ref[f"{v}_floor"] = floor_of(info["band_energy"], cfg).astype(np.float32)
    return ref


def sha(a):
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def generate():
    out = {}
    for name, (kind, seed, tr, fe, variants) in SCENES.items():
        words = front(source(kind, seed), seed, fe)
        hop_in = 256 if fe == "D2" else 128
        words = words[: len(words) // hop_in * hop_in]
        arrays = {"words": words, **reference(words, fe, tr, variants)}
        meta = dict(scenario=kind, seed=seed, transient_only=tr, front=fe, variants=list(variants), n_words=int(len(words)),
                    sha256={k: sha(v) for k, v in arrays.items()})
        out[name] = (arrays, meta)
    return out


# ------------------------------------------------------------------------------------------------ L1 / L0
def ref_squelch_mask(y, thr_db=-68.0, fs=12500):
    """stages.PwmShaper squelch on the 12.5 kS/s stream (5 ms rms below threshold for 20 ms, centred windows)."""
    w = int(0.005 * fs)
    env = np.sqrt(np.convolve(y ** 2, np.ones(w) / w, "same"))
    quiet = (env < 10 ** (thr_db / 20)).astype(float)
    k = int(0.02 * fs)
    return np.convolve(quiet, np.ones(k) / k, "same") >= 0.999


def db_err(fw, ref, rel_floor_db=-60.0):
    """|10 log10(fw/ref)| over entries within rel_floor_db of the frame maximum (p99, max)."""
    m = (ref > ref.max(axis=1, keepdims=True) * 10 ** (rel_floor_db / 10)) & (ref > 1e-20)
    if not m.any():
        return 0.0, 0.0, 0
    e = np.abs(10 * np.log10(np.maximum(fw[m], 1e-30) / ref[m]))
    return float(np.percentile(e, 99)), float(e.max()), int(m.sum())


def l1_one(arrays, meta, v, fw_res):
    d = DELAY[v]
    y = fw_res["dsp"].astype(float)
    ref_y = arrays[f"{v}_y"].astype(float)
    n = min(len(y) - d, len(ref_y))
    skip = 600 if v == "A" else 0                                 # A: the reference's zero-phase filters start non-causally
    err = y[d + skip:d + n] - ref_y[skip:n]
    rms = np.sqrt(np.mean(ref_y[skip:n] ** 2)) + 1e-30
    r = {"dsp_out_err_db": float(20 * np.log10(np.sqrt(np.mean(err ** 2)) / rms + 1e-30)), "ref_rms_dbfs": float(20 * np.log10(rms * np.sqrt(2)))}
    if v in ("B", "slim"):
        nb = 16 if v == "slim" else 28
        Eref, Fref = arrays[f"{v}_band"].astype(float), arrays[f"{v}_floor"].astype(float)
        hops = np.arange(len(Eref)) * (2 if v == "slim" else 1) + 1
        ok = hops < len(fw_res["band"])
        Efw = fw_res["band"][hops[ok], :nb].astype(float)
        Ffw = fw_res["floor"][hops[ok], :nb].astype(float)
        r["band_db_err_p99"], r["band_db_err_max"], r["band_n"] = db_err(Efw, Eref[ok])
        r["floor_db_err_p99"], r["floor_db_err_max"], _ = db_err(Ffw, Fref[ok])
        # squelch decisions per hop (after the power-on hold): reference mask at the hop's last output sample. The reference
        # uses centred windows (non-causal); the firmware's causal 20 ms hold sees the same quiet span 10 ms later: compare at lag 10 ms
        mask = ref_squelch_mask(ref_y)
        hh = np.arange(HOLD_HOPS, len(fw_res["sq"]))
        idx = hh * 8 + 7 - d - SQ_LAG
        ok2 = (idx >= 0) & (idx < len(mask))
        r["squelch_agree"] = float(np.mean(fw_res["sq"][hh[ok2]].astype(bool) == mask[idx[ok2]])) if ok2.any() else 1.0
    if meta["scenario"] == "sweep" and v in ("B", "slim"):
        nb = 16 if v == "slim" else 28
        cfg = pl.BConfig(n_bands=nb)
        band_w = np.log(cfg.out_hi / cfg.out_lo) / nb
        worst = 0.0
        seg = int(SEG_S * 12500)
        for i, f in enumerate(SWEEP_F):
            a, b = i * seg + d + seg // 3, (i + 1) * seg + d - seg // 6
            x = y[a:b] * np.hanning(b - a)
            X = np.abs(np.fft.rfft(x, 1 << 14))
            fo = np.fft.rfftfreq(1 << 14, 1 / 12500)[np.argmax(X)]
            worst = max(worst, abs(np.log(fo / pl.map_freq(f, cfg))) / band_w)
        r["sweep_map_err_bands"] = float(worst)
    return r


def run_fw(arrays, meta, v, cc="gcc", opt="-O2"):
    fw = fwlib.Firmware(dict(FW_KNOBS[v], **({} if v == "A" else {"transient_only": meta["transient_only"]})), cc=cc, opt=opt)
    return fw.run(arrays["words"], d2=meta["front"] == "D2")


def l1_all(vecs):
    res = {}
    for name, (arrays, meta) in vecs.items():
        for v in meta["variants"]:
            res[f"{name}.{v}"] = l1_one(arrays, meta, v, run_fw(arrays, meta, v))
    return res


def l0_all(vecs):
    """Bit-exact: every tap and CCR word identical across host gcc -O2, clang-18 -O2 and gcc -O0 (UB / FP-contract reliance)."""
    bad, n = [], 0
    for name, (arrays, meta) in vecs.items():
        for v in meta["variants"]:
            base = run_fw(arrays, meta, v)
            for cc, opt in (("clang-18", "-O2"), ("gcc", "-O0")):
                other = run_fw(arrays, meta, v, cc, opt)
                n += 1
                for k in base:
                    if not np.array_equal(base[k], other[k]):
                        bad.append(f"{name}.{v} {cc} {opt}: {k} differs")
    return bad, n


def load():
    man = yaml.safe_load(MANIFEST.read_text()) if MANIFEST.exists() else {"vectors": {}}
    out = {}
    for name, meta in man["vectors"].items():
        z = np.load(VEC / f"{name}.npz")
        out[name] = ({k: z[k] for k in z.files}, meta)
    return out, man


def check_thresholds(l1, th):
    rows = []
    for key, mets in sorted(l1.items()):
        v = key.split(".")[1]
        for m, val in mets.items():
            t = th.get("thresholds", {}).get(v, {}).get(m)
            if t is None:
                continue
            op, lim = t["op"], t["thr"]
            ok = val <= lim if op == "<=" else val >= lim
            rows.append(dict(id=f"L1.{key}.{m}", value=round(val, 5), op=op, thr=lim, status="PASS" if ok else "FAIL"))
    return rows


def freeze(l1):
    """Thresholds from the first measured comparison (architecture.comparison_levels L1): measured worst + margin, never looser
    than needed to pass today; the proposed starting values are kept where they hold."""
    worst = {}
    for key, mets in l1.items():
        v = key.split(".")[1]
        for m, val in mets.items():
            if m in ("band_n", "ref_rms_dbfs"):
                continue
            w = worst.setdefault(v, {}).get(m)
            better_low = m != "squelch_agree"
            worst[v][m] = val if w is None else (max(w, val) if better_low else min(w, val))
    prop = {"band_db_err_p99": 0.1, "dsp_out_err_db": -60.0, "squelch_agree": 0.999}
    th = {}
    for v, mets in worst.items():
        th[v] = {}
        for m, val in mets.items():
            if m == "squelch_agree":
                lim = min(prop[m], round(val - 0.005, 3))
                th[v][m] = {"op": ">=", "thr": lim, "measured": round(val, 5)}
            elif m.endswith("_db") and m.startswith("dsp_out"):
                lim = max(prop[m], round(val + 3.0, 1))
                th[v][m] = {"op": "<=", "thr": lim, "measured": round(val, 2)}
            elif m == "sweep_map_err_bands":
                th[v][m] = {"op": "<=", "thr": 1.0, "measured": round(val, 3), "src": "FWSIM-R13: tone sweep maps within one band"}
            else:
                lim = max(prop.get(m, 0.0), round(val * 1.5 + 0.005, 3))
                th[v][m] = {"op": "<=", "thr": lim, "measured": round(val, 4)}
    doc = {"meta": {"what": "FWSIM-R7 L1 thresholds (firmware host build vs sim/dsp float64 reference on the golden vectors)",
                    "frozen": str(datetime.date.today()), "by": "sim/fw/gen_vectors.py --freeze (measured worst + margin; proposed starting values kept where they hold)",
                    "proposed": "band energy <= 0.1 dB steady state; 12.5 kS/s output error <= -60 dB re signal rms; squelch decisions equal on >= 99.9 % of hops",
                    "squelch_agree_why": "the reference squelch (stages.PwmShaper) uses centred 5 ms / 20 ms windows (non-causal); the firmware's causal rule is compared at a 10 ms lag and still differs around transitions, so 0.999 cannot hold",
                    "rule": "changing a value needs a stated reason in docs/sim/firmware-emulation.yaml change_log"},
           "thresholds": th}
    THRESH.write_text(yaml.safe_dump(doc, sort_keys=False, width=200))
    return doc


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--bless", action="store_true")
    ap.add_argument("--freeze", action="store_true")
    ap.add_argument("--no-l0", action="store_true")
    ap.add_argument("--json", type=Path)
    a = ap.parse_args(argv)
    rows = []
    fresh = generate()
    old, man = load()
    drift = []
    for name, (arrays, meta) in fresh.items():
        om = man["vectors"].get(name)
        if om is None:
            drift.append(f"{name}: new vector")
            continue
        for k, h in meta["sha256"].items():
            if om["sha256"].get(k) != h:
                drift.append(f"{name}.{k}: sha256 {om['sha256'].get(k, 'missing')[:12]} -> {h[:12]}")
    drift += [f"{n}: vector removed" for n in man["vectors"] if n not in fresh]
    if a.bless:
        l1_old = l1_all(old) if old else {}
        VEC.mkdir(parents=True, exist_ok=True)
        for f in VEC.glob("*.npz"):
            if f.stem not in fresh:
                f.unlink()
        for name, (arrays, meta) in fresh.items():
            buf = io.BytesIO()
            np.savez_compressed(buf, words=arrays["words"])          # inputs only; reference taps are regenerated and sha-pinned
            (VEC / f"{name}.npz").write_bytes(buf.getvalue())
        doc = {"meta": {"what": "FWSIM-R8 golden vectors: inputs (ADF1 words) + reference taps; regenerate with sim/fw/gen_vectors.py --bless",
                        "generated": str(datetime.date.today()), "sim_commit": sim_commit(),
                        "chain": "sim/e2e AcousticPort -> Microphone -> SupplyInject -> AdfDecimator D1 stub (D2: 400 kS/s words) -> stages.pcm_to_adf_words",
                        "reference": "sim/dsp/pipeline.py algo_b (B: 28 bands hop 128; slim: 16 bands hop 256; ceiling +100 dBFS = pre-limiter), algo_a pre-gate x 10^1.5",
                        "alignment": "firmware 12.5 kS/s sample n = reference n - 8 (B, slim) or n - 17 (A); fw hop k = ref frame k-1 (B), fw hop 2h+1 = ref frame h (slim)"},
               "vectors": {n: m for n, (_, m) in fresh.items()}}
        MANIFEST.write_text(yaml.safe_dump(doc, sort_keys=False, width=200))
        vecs = {n: (arr, m) for n, (arr, m) in fresh.items()}
        l1_new = l1_all(vecs)
        print("bless: wrote", len(fresh), "vectors;", "drift was:", drift or "none")
        for k in sorted(l1_new):
            for m, v in l1_new[k].items():
                o = l1_old.get(k, {}).get(m)
                print(f"  {k:16s} {m:22s} {'' if o is None else f'{o:10.4f} ->'} {v:10.4f}")
        drift = []
    else:
        stored_ok = all(name in old and np.array_equal(old[name][0]["words"], arrays["words"]) for name, (arrays, _) in fresh.items())
        if not stored_ok:
            drift.append("stored words (npz) differ from the regenerated ones")
        vecs = {n: (arr, m) for n, (arr, m) in fresh.items()} if not drift else {}
        l1_new = l1_all(vecs) if vecs else {}
    rows.append(dict(id="R8.vectors_sha", value=len(drift), op="==", thr=0, status="PASS" if not drift and vecs else "FAIL",
                     detail=drift or None, basis=f"{len(fresh)} vectors regenerated from sim/dsp + sim/e2e vs manifest sha256"))
    if a.freeze:
        freeze(l1_new)
    th = yaml.safe_load(THRESH.read_text()) if THRESH.exists() else {}
    rows += check_thresholds(l1_new, th)
    if not a.no_l0 and vecs:
        bad, n = l0_all(vecs)
        rows.append(dict(id="L0.host_gcc_clang_O0", value=len(bad), op="==", thr=0, status="PASS" if not bad else "FAIL", detail=bad or None,
                         basis=f"{n} runs: CCR + taps bit-exact, gcc -O2 vs clang-18 -O2 vs gcc -O0"))
    status = "PASS" if rows and all(r["status"] == "PASS" for r in rows) else "FAIL"
    res = {"status": status, "rows": rows, "l1": l1_new}
    OUTJ.parent.mkdir(parents=True, exist_ok=True)
    OUTJ.write_text(json.dumps(res, indent=1) + "\n")
    if a.json:
        a.json.write_text(json.dumps(res, indent=1) + "\n")
    for r in rows:
        print(f"{r['status']:4} {r['id']:44s} {r['value']} {r['op']} {r['thr']}")
        if r["status"] != "PASS" and r.get("detail"):
            print("     ", r["detail"])
    print("gen_vectors:", status)
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
