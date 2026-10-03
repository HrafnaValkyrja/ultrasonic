#!/usr/bin/env python3
"""End-to-end chain: ultrasonic source -> acoustic path -> mic -> ADF1 -> DSP -> PWM shaper -> bridge ->
exciter -> bone/mech proxy -> audibility proxy.  Contract and requirements: docs/sim/e2e-chain.yaml.

    systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 \
        python3 sim/e2e/chain.py                       # S-T1, 2 s, writes sim/out/e2e/T1.{json,png}
    ... chain.py --scenario all --no-plot              # T1 T2 T3 T6 D17 lat pwr selftest R15 (steady state: 6 s pre-roll)
    ... chain.py --scenario T6 --set ext_ripple_mv=1 psrr_mode=rolloff
    ... chain.py --scenario spice                      # behavioural bridge vs ngspice, ~15 s, ~0.5 GB
    ... chain.py --sweep exciter|mic|port|supply

Prints PASS / FAIL / WARN per metric. WARN = a stub stage (acoustic path, supply noise, exciter, bone
coupling, RSFLT) makes the metric not meaningful; the line says what it would be.
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy import signal
from scipy.io import wavfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path[:0] = [str(HERE), str(REPO / "sim/dsp"), str(REPO / "sim/checks"), str(REPO / "tools")]
import corpus  # noqa: E402
import metrics as mx  # noqa: E402
import pipeline as pl  # noqa: E402
import plotstyle  # noqa: E402
import stages as sg  # noqa: E402
from metrics import Metric  # noqa: E402
from stages import Ctx, Sig  # noqa: E402

OUT = REPO / "sim/out/e2e"
OUT.mkdir(parents=True, exist_ok=True)
FS = sg.FS_AC
FS_PCM_ = sg.FS_PCM
PM_DIR = REPO.parent / "ultrasonic-scratch/rec/extracts"
N_STARTUP = 6     # power-on realisations scored in T6 (the burst depends on the mic-noise realisation: +5..-21 dB SL seen 2026-10-02)
PREROLL_S = 6.0   # >= 2x the DSP floor tracker's 3 s rise (pipeline.BConfig.floor_up_s): metrics read steady state only (skeptic 2026-10-02)


# ================================================================================================ sources
def lvl(sig, db):
    """Scale so the rms over the non-zero samples equals `db` dB SPL (same convention as sim/dsp/corpus.py)."""
    nz = np.abs(sig) > 1e-9
    r = np.sqrt(np.mean(sig[nz] ** 2)) if nz.any() else 1.0
    return sig / r * corpus.db_spl_to_pa_rms(db)


def burst_train(f, t0s, cycles=8, n=0):
    b = np.sin(2 * np.pi * f * np.arange(int(cycles / f * FS)) / FS)
    x = np.zeros(n)
    for t0 in t0s:
        i = int(t0 * FS)
        m = min(len(b), n - i)
        if m > 0:
            x[i:i + m] += b[:m]
    return x


def house_walk(dur=2.0, seed=1, preroll=0.0):
    """S-T1 source: HC-SR04-like 40 kHz bursts (85 dB), a keys cluster (65 dB), steady charger/LED whines
    (40/35 dB), speech-band noise (60 dB). Levels as sim/dsp/corpus.py (rough, synthetic). The steady background
    (whines + speech) runs through a `preroll` before the events so the DSP floor tracker is settled."""
    if dur < 2.0:
        raise ValueError("S-T1 windows need dur >= 2.0 s")
    rng = np.random.default_rng(seed)
    P = preroll
    n = int((dur + P) * FS)
    t = np.arange(n) / FS
    hc = burst_train(40e3, P + np.arange(0.2, 0.9, 0.06), 8, n)
    keys = np.zeros(n)
    for t0 in P + rng.uniform(1.2, 1.5, 25):
        i, L = int(t0 * FS), int(0.004 * FS)
        m = min(L, n - i)
        f = rng.uniform(20e3, 70e3)
        keys[i:i + m] += np.sin(2 * np.pi * f * np.arange(m) / FS) * np.exp(-np.arange(m) / (0.0008 * FS)) * rng.uniform(0.4, 1)
    whine = np.sin(2 * np.pi * 25e3 * t) + 0.3 * np.sin(2 * np.pi * 50e3 * t)
    led = np.sin(2 * np.pi * 33.3e3 * t)
    sp = corpus._filt(corpus._bandpass(200, 6000), rng.standard_normal(n)) * (0.5 + 0.5 * np.sin(2 * np.pi * 3 * t)) ** 2
    mix = lvl(hc, 85) + lvl(keys, 65) + lvl(whine, 40) + lvl(led, 35) + lvl(sp, 60)
    # background = the last 3 s of the pre-roll (floor tracker settled, 3 s of steady whines + speech) when there is a pre-roll;
    # post = after the events (only 0.35 s: too short for steady state, informational)
    return mix, dict(hc=(P + 0.2, P + 0.9), keys=(P + 1.2, P + 1.5),
                     background=(max(0.0, P - 3.0), P) if P >= 3.0 else (P + 1.6, P + dur - 0.05), post=(P + 1.6, P + dur - 0.05))


def self_noise(dur=4.0, seed=8, preroll=0.0, us_db=40.0, speech_db=75.0, chew_db=55.0, hair_db=35.0):
    """S-R15 source (spec R15 L609): the wearer's own speech with fricative ultrasound, chewing clicks, hair rustle,
    no external ultrasound. ALL ultrasonic levels are ASSUMED (no recording of the owner exists; S1 retires them):
    fricative bursts 20-45 kHz at `us_db` dB SPL (rms over the burst), speech band 200-6000 Hz at `speech_db`,
    chewing clicks 20-90 kHz at `chew_db` (burst rms), hair rustle 20-90 kHz at `hair_db`, slowly modulated."""
    rng = np.random.default_rng(seed)
    n = int((dur + preroll) * FS)
    t = np.arange(n) / FS
    syl = (0.5 + 0.5 * np.sin(2 * np.pi * 4.0 * t + rng.uniform(0, 6.28))) ** 2
    sp = corpus._filt(corpus._bandpass(200, 6000), rng.standard_normal(n)) * syl
    us = signal.sosfilt(signal.butter(6, [20e3, 45e3], "bp", fs=FS, output="sos"), rng.standard_normal(n))
    gate = np.zeros(n)
    for t0 in np.arange(0.1, dur + preroll - 0.2, 0.5) + rng.uniform(0, 0.2, len(np.arange(0.1, dur + preroll - 0.2, 0.5))):
        i, L = int(t0 * FS), int(rng.uniform(0.08, 0.15) * FS)
        gate[i:i + L] = np.hanning(len(gate[i:i + L]))
    fric = us * gate
    clicks = np.zeros(n)
    for t0 in np.sort(rng.uniform(0, dur + preroll, int(3 * (dur + preroll)))):
        i, L = int(t0 * FS), int(0.002 * FS)
        m = min(L, n - i)
        clicks[i:i + m] += rng.standard_normal(m) * np.exp(-np.arange(m) / (0.0004 * FS))
    clicks = signal.sosfilt(signal.butter(4, [20e3, 90e3], "bp", fs=FS, output="sos"), clicks)
    hair = signal.sosfilt(signal.butter(4, [20e3, 90e3], "bp", fs=FS, output="sos"), rng.standard_normal(n))
    hair *= 0.6 + 0.4 * np.sin(2 * np.pi * 0.7 * t)
    mix = lvl(sp, speech_db) + lvl(fric, us_db) + lvl(clicks, chew_db) + lvl(hair, hair_db)
    return mix, dict(measure=(preroll, preroll + dur))


def bats(dur=2.0, seed=2, spl=70.0):
    """Synthetic big-brown-like FM call train (55->26 kHz, 6 ms, 9/s) at `spl` dB SPL. Returns (Pa, call starts)."""
    rng = np.random.default_rng(seed)
    n = int(dur * FS)
    x = np.zeros(n)
    starts = list(np.arange(0.2, dur - 0.1, 0.11))
    for t0 in starts:
        s, _ = corpus.fm_call(t0, 0.006, 55e3, 26e3, 0, n, rng)
        x += s
    return lvl(x, spl), starts


def port_meadow_tiled(total, spl=75.0):
    """The 3.0 s Port Meadow clip repeated to `total` s (a stationary dusk scene) so the measured window follows a pre-roll."""
    x3, c3 = port_meadow(3.0, spl)
    if x3 is None:
        return None, []
    L = len(x3) / FS
    k = int(np.ceil(total / L))
    x = np.tile(x3, k)[: int(total * FS)]
    calls = [c + j * L for j in range(k) for c in c3 if c + j * L < total - 0.05]
    return x, calls


def port_meadow(dur=2.0, spl=75.0, clip="20251021_172626/receiver_3.wav", ev="20251021_172626/events_3.csv"):
    """Real AudioMoth recording (Port Meadow, Zenodo 22079773, CC-BY-4.0). Scaled so the loudest 10 ms
    ultrasonic window is `spl` dB SPL (nature_demo.py convention; true calibration unknown). None if absent."""
    f = PM_DIR / clip
    if not f.exists():
        return None, []
    fs, y = wavfile.read(f)
    y = y.astype(float) / 32768.0
    y = y[: int(dur * fs)]
    u = signal.sosfilt(signal.butter(6, [20e3, 90e3], "bp", fs=fs, output="sos"), y)
    win = int(0.01 * fs)
    peak = np.sqrt(np.max(np.convolve(u ** 2, np.ones(win) / win, "valid")))
    pa = y * (corpus.db_spl_to_pa_rms(spl) / peak)
    x = signal.resample_poly(pa, 25, 12)                      # 192 -> 400 kS/s
    calls = []
    for line in (PM_DIR / ev).read_text().splitlines()[1:]:
        c = line.split(",")
        if len(c) >= 4 and float(c[1]) >= 0.5 and float(c[2]) < dur - 0.05:
            calls.append(float(c[2]))
    return x, calls


# ================================================================================================ runner
def make_params(over=None):
    p = dict(sg.DEFAULT_PARAMS)
    p.update(over or {})
    return p


def run_stages(chain, src, ctx):
    taps = {"src": src}
    s = src
    for st in chain:
        t0 = time.time()
        s = st.process(s, ctx)
        ctx.side["t_" + st.id] = round(time.time() - t0, 2)
        taps[st.id] = s
    return taps


def run_chain(src_pa, over=None, seed=1):
    p = make_params(over)
    if "z_rail_ohm" in p:   # renamed 2026-10-02: the mic transfer is h_ibridge_to_micvdd, not the bridge-rail z_rail
        p["h_mic_ohm"] = p.pop("z_rail_ohm")
    chain = sg.default_chain()
    ctx = Ctx(p, np.random.default_rng(seed))
    taps = run_stages(chain, Sig(src_pa, FS, "Pa"), ctx)
    if p["loopback"]:   # 2nd pass: bridge supply current x (bridge current -> mic VDD transfer) -> mic VDD ripple
        i_sup = ctx.side["i_sup"].x
        if p.get("mic_vdd_json"):   # IF-MIC-VDD-NOISE: |h(f)| as a linear-phase FIR at 200 kS/s (phase ignored: one path only)
            _, fh, h = sg.SupplyInject.load_if(p["mic_vdd_json"])
            ff = np.concatenate([[0.0], fh[fh < sg.FS_PWM / 2], [sg.FS_PWM / 2]])
            gg = np.abs(np.concatenate([[h[0]], h[fh < sg.FS_PWM / 2], [np.interp(sg.FS_PWM / 2, fh, np.abs(h))]]))
            v200 = signal.fftconvolve(i_sup, signal.firwin2(511, ff, gg, fs=sg.FS_PWM), mode="same")
        else:
            v200 = i_sup * p["h_mic_ohm"]
        v = signal.resample_poly(v200, 2, 1)
        side0 = {k: v_ for k, v_ in ctx.side.items() if k.startswith("t_")}
        ctx = Ctx(p, np.random.default_rng(seed), inject=Sig(v, FS, "V"))
        ctx.side.update(side0)
        taps = run_stages(chain, Sig(src_pa, FS, "Pa"), ctx)
    status = {st.id: st.status for st in chain}
    status.update(sg.PSEUDO_STATUS)
    return taps, ctx, status


def frames_in(t, a, b, half=0.0):
    """Frames whose whole span [t-half, t+half] lies inside [a, b). half = frame length / 2 (spectrogram t = centres)."""
    return (t - half >= a) & (t + half < b)


HALF = 0.5 * 8192 / mx.FS_FORCE


def window_dbfs(sig, a, b):
    m = frames_in(sig.t, a, b)
    return mx.dbfs_rms_peakref(sig.x[m])


def sl_of(taps, p):
    return mx.sensation_level(taps["mech_bone"].x, p)


def sl_alt(taps, p):
    """SL under the other threshold convention (docs/sim/shared-params.yaml#thresholds.conventions)."""
    other = "front_measured" if p.get("thr_convention", "retfl_minus_tragus") == "retfl_minus_tragus" else "retfl_minus_tragus"
    return mx.sensation_level(taps["mech_bone"].x, dict(p, thr_convention=other)), other


def win_frames(t, a, b):
    return frames_in(t, a, b, HALF)


# ================================================================================================ scenarios
def scn_T1(dur=2.0, seed=1, over=None, preroll=PREROLL_S):
    """S-T1 house walk: electronics ultrasound in a noisy house. Transient-only is the indoor default (D12).
    Steady background (whines 25/33.3/50 kHz + speech-band noise) runs `preroll` s first; metrics read the last `dur` s."""
    src, w = house_walk(dur, seed, preroll)
    taps, ctx, st = run_chain(src, over, seed)
    dsp, p = taps["dsp"], ctx.p
    ev = min(window_dbfs(dsp, *w["hc"]), window_dbfs(dsp, *w["keys"]))
    bg = window_dbfs(dsp, *w["background"])
    hc_db = window_dbfs(dsp, *w["hc"])
    sl, t, nl = sl_of(taps, p)
    (sla, _, _), conv_alt = sl_alt(taps, p)
    ev_sl = float(np.percentile(np.max(sl[win_frames(t, *w["hc"])], axis=1), 90))
    bg_sl = float(np.max(sl[win_frames(t, *w["background"])]))
    bg_sl_alt = float(np.max(sla[win_frames(t, *w["background"])]))
    sh = taps["shaper"]
    bgm = (sh.t >= w["background"][0]) & (sh.t < w["background"][1])
    M = [
        Metric("T1.background_suppression_db", "T1", hc_db - bg, "dB", ">=", 20.0,
               "spec D12 L220 (steady tones suppressed), T1 L38 (tolerable); background = whines + speech-band noise, steady state", "assumed", []),
        Metric("T1.event_out_dbfs", "T1", ev, "dBFS", ">=", -35.0,
               "spec T1 L38 (hears the sources); level at the fixed D3 volume", "assumed", ["acoustic_path"]),
        Metric("T1.event_sl_p90_db", "T1", ev_sl, "dB SL", ">=", 10.0,
               "spec T1 L38; sensation level re owner's threshold (proxy)", "assumed", ["acoustic_path", "exciter", "mech_bone"]),
        Metric("T1.background_sl_max_db", "T1", bg_sl, "dB SL", "<=", 0.0,
               "spec D12 L220 + T1 L38 + R15 L609: the steady background (whines + speech) must not be audible after the floor settles",
               "assumed", ["acoustic_path", "mic_ein", "exciter", "mech_bone"], note=f"{conv_alt}: {bg_sl_alt:.1f} dB SL"),
    ]
    info = dict(windows_s=w, window_dbfs_dsp=dict(hc=round(hc_db, 1), keys=round(window_dbfs(dsp, *w["keys"]), 1), background=round(bg, 1),
                                                  post=round(window_dbfs(dsp, *w["post"]), 1)),
                background_active_frac=round(float(np.mean(sh.x[bgm] != 0)), 3), preroll_s=preroll,
                squelched_frac=round(ctx.side["squelched_frac"], 3), i_sup_avg_ma=round(ctx.side["i_sup_avg_ma"], 3),
                bridge_peak_ma=round(ctx.side["bridge_peak_a"] * 1e3, 1), loudness_proxy_peak=round(float(nl.max()), 2),
                renamed="T1.whine_* -> T1.background_* (2026-10-02): the window holds whines AND speech-band noise")
    return M, info, taps, ctx, st


def _recall(env, fs, starts, win=0.020, thr_dbfs=-50.0):
    thr = 10 ** (thr_dbfs / 20)
    hit = [env[int(t0 * fs): int((t0 + win) * fs)].max() >= thr if int(t0 * fs) < len(env) else False for t0 in starts]
    return float(np.mean(hit)) if hit else float("nan")


def scn_T2(dur=2.0, seed=2, over=None, preroll=PREROLL_S):
    """S-T2 nature: bats. Port Meadow clip (tiled behind a pre-roll) if present, else the synthetic call train."""
    total = dur + preroll
    x, calls = port_meadow_tiled(total)
    src_name = "port_meadow (3.0 s clip tiled)"
    if x is None:
        x, calls = bats(total, seed)
        src_name = "synthetic_bats"
    n = int(total * FS)
    x = np.pad(x, (0, max(0, n - len(x))))[:n]
    calls = [c for c in calls if c >= preroll]
    taps, ctx, st = run_chain(x, over, seed)
    dsp, p = taps["dsp"], ctx.p
    md = dsp.t >= preroll
    env = mx.envelope(dsp.x, dsp.fs, 0.001)
    rec = _recall(env, dsp.fs, calls)
    i = taps["exciter"]
    mi = i.t >= preroll
    band = mx.band_power_ratio(dsp.x[md], dsp.fs, (1200, 4500), (100, None))
    f, P = signal.welch(i.x[mi], i.fs, nperseg=8192)
    cent = float((f[(f > 200) & (f < 16000)] * P[(f > 200) & (f < 16000)]).sum() / P[(f > 200) & (f < 16000)].sum())
    sl, t, nl = sl_of(taps, p)
    (sla, _, _), conv_alt = sl_alt(taps, p)
    k = win_frames(t, preroll, total)
    act = np.max(sl[k], axis=1)
    comfort = float(np.percentile(act, 99))
    comfort_alt = float(np.percentile(np.max(sla[k], axis=1), 99))
    prot = [list(mx.THIRD_OCT).index(fc) for fc in (8000, 10000, 12500, 16000)]
    prot_sl = float(max(np.percentile(sl[k][:, b], 99) for b in prot))
    prot_sl_alt = float(max(np.percentile(sla[k][:, b], 99) for b in prot))
    prot_by_band = {int(mx.THIRD_OCT[b]): round(float(np.percentile(sl[k][:, b], 99)), 1) for b in prot}
    M = [
        Metric("T2.call_recall_20ms", "T2", rec, "frac", ">=", 0.80,
               f"spec T2 L39 (bats come through); idle-detector benchmark 0.955 (spec L411); src {src_name}", "assumed", ["acoustic_path"]),
        Metric("T2.out_band_frac_1.2_4.5k", "T2", band, "frac", ">=", 0.95,
               "spec D9 L203 (output band ~1.5-4 kHz)", "derived", []),
        Metric("T2.ceiling_true_peak_dbfs", "T2", 20 * np.log10(ctx.side["x_interp_peak"] + 1e-12), "dBFS", "<=", p["ceiling_dbfs"] + 0.5,
               "spec D17 L294 (fixed ceiling): invariant = the configured ceiling (-12 dBFS, assumed number) holds as a TRUE peak after x16 interpolation", "derived", []),
        Metric("T2.protect_band_sl_p99_db", "T2", prot_sl, "dB SL", "<=", 0.0,
               "spec s6 L348 (8-16 kHz is the band to protect; owner hears high): worst p99 SL of the 8/10/12.5/16 kHz third-octaves (replaces the image-rejection ratio)",
               "derived", ["exciter", "mech_bone"], note=f"{conv_alt}: {prot_sl_alt:.1f} dB SL; per band {prot_by_band}"),
        Metric("T2.out_centroid_hz", "T2", cent, "Hz", "<=", 4000.0,
               "spec D9 L203-205 (1.5-4 kHz); T2 L39 non-shrill", "derived", ["exciter"]),
        Metric("T2.comfort_sl_p99_db", "T2", comfort, "dB SL", "<=", 60.0,
               "spec T2 L39 (comfortable, non-shrill); 60 dB SL is a proposed comfort limit", "assumed", ["acoustic_path", "exciter", "mech_bone"],
               note=f"{conv_alt}: {comfort_alt:.1f} dB SL"),
    ]
    info = dict(source=src_name, n_calls=len(calls), preroll_s=preroll, loudness_proxy_peak=round(float(nl.max()), 2),
                i_sup_avg_ma=round(ctx.side["i_sup_avg_ma"], 3), peak_coil_ma=round(ctx.side["bridge_peak_a"] * 1e3, 1))
    return M, info, taps, ctx, st


def scn_T3(dur=0.6, seed=3, over=None):
    """S-T3 stereo: two independent chains (D2), a level cue (ILD) at the input -> output ILD with unit
    spread, then perceived ILD with crosstalk (isolation TA) and random relative phase. Head shadow is a
    stub (the level offset is applied directly). Unit spread (assumed): mic +-1 dB (D13 L227), exciter R +-10 %."""
    n = int(dur * FS)
    starts = np.arange(0.1, dur - 0.1, 0.06)
    base = burst_train(40e3, starts, 8, n)
    rows, last = [], None
    for hi_spl, ild in ((70, 0), (70, 6), (70, 12), (90, 6)):
        A = []
        for k, (spl, sens, rex) in enumerate(((hi_spl, +1.0, 7.2), (hi_spl - ild, -1.0, 8.8))):   # worst-case bias
            o = dict(over or {}, mic_sens_db=sens, r_exc=rex)
            taps, ctx, st = run_chain(lvl(base, spl), o, seed + k)
            A.append(float(np.sqrt(np.mean(taps["mech_bone"].x ** 2))))
            last = (taps, ctx, st)
        rows.append(dict(hi_spl=hi_spl, ild_in=ild, ild_out_db=round(float(20 * np.log10(A[0] / A[1])), 2)))
    r0 = next(r for r in rows if r["hi_spl"] == 70 and r["ild_in"] == 0)
    bias = r0["ild_out_db"]
    comp = max(abs(r["ild_out_db"] - bias - r["ild_in"]) for r in rows if r["hi_spl"] == 70)
    clip = next(r for r in rows if r["hi_spl"] == 90)
    kept = clip["ild_out_db"] - bias
    r6 = next(r for r in rows if r["hi_spl"] == 70 and r["ild_in"] == 6)
    ta_stats = {}
    for ta in (10, 20, 30):
        d = mx.ild_percept(10 ** (r6["ild_out_db"] / 20), 1.0, ta, seed=ta)
        ta_stats[ta] = float(np.mean(d > 0))
    M = [
        Metric("T3.ild_sign_agree_ta20", "T3", ta_stats[20], "frac", ">=", 0.95,
               "spec D2 L113-115 + bone-conduction.md s2 (sign preserved at TA>=20 dB); 6 dB ILD, worst-case unit spread", "derived", ["exciter", "mech_bone"]),
        Metric("T3.ild_sign_agree_ta10", "T3", ta_stats[10], "frac", ">=", 0.95,
               "spec D2 L112-114 (fallback site: ~10-15 dB isolation); informational", "derived", ["exciter", "mech_bone"]),
        Metric("T3.ild_bias_matched_db", "T3", abs(bias), "dB", "<=", 3.0,
               "spec R7 L600 (L/R mismatch biases direction; trim at calibration, D3 L122-125); +-1 dB mic, +-10% exciter R", "assumed", ["exciter", "mech_bone"]),
        Metric("T3.ild_compression_err_db", "T3", comp, "dB", "<=", 1.5,
               "spec T3 L40 (level cue must survive the chain); bias removed; loud side 70 dB SPL (below the ceiling)", "assumed", ["exciter", "mech_bone"]),
        Metric("T3.ild_kept_at_ceiling_db", "T3", kept, "dB", ">=", 3.0,
               "spec D17 L294 vs T3 L40: a ceiling that limits both sides erases the level cue (6 dB in, loud side 90 dB SPL)", "assumed", ["exciter", "mech_bone"]),
    ]
    info = dict(ild_table=rows, bias_db=bias, sign_agree_by_ta=ta_stats)
    return M, info, last[0], last[1], last[2]


def scn_T6(dur=10.0, seed=4, over=None):
    """S-T6 silence: no ultrasound at the mic (mic self-noise only) -> output. 10 s: the start-up window (0-0.3 s) AND the
    steady state after the 3 s floor tracker settles (6 s-end) are both scored."""
    n = int(dur * FS)
    taps, ctx, st = run_chain(np.zeros(n), over, seed)
    p = ctx.p
    sh, dsp = taps["shaper"], taps["dsp"]
    band_sos = signal.butter(4, [200, 20e3], "bp", fs=sh.fs, output="sos")
    inb = mx.dbfs_rms_peakref(signal.sosfilt(band_sos, sh.x)[int(0.1 * sh.fs):])
    sl, t, nl = sl_of(taps, p)
    cur = taps["exciter"]
    f, P = signal.welch(taps["mech_bone"].x, sg.FS_PWM, nperseg=8192)
    m = (f >= 20e3) & (f < 85e3)
    f_noise = float(np.sqrt(P[m].sum() * (f[1] - f[0])))
    ein = pl.P_REF * 10 ** (pl.MIC_EIN_DBSPL_20K / 20) * np.sqrt(65e3 / 20e3)
    leak_max = (ein * 10 ** (-6 / 20)) / max(f_noise, 1e-18)
    wn = int(0.005 * dsp.fs)
    env = np.sqrt(np.convolve(dsp.x ** 2, np.ones(wn) / wn, "same"))
    idle_env_db = 20 * np.log10(np.percentile(env[int(0.3 * dsp.fs):], 99.9) + 1e-12)
    k0 = frames_in(t, 0.0, 0.3, HALF)
    startup_sl_main = float(np.max(sl[k0])) if k0.any() else float("nan")
    # power-on burst is one random realisation of the mic noise: score the worst of N_STARTUP short power-ons (0.6 s each)
    starts = [startup_sl_main]
    for j in range(N_STARTUP - 1):
        tp, cp, _ = run_chain(np.zeros(int(0.6 * FS)), over, seed + 101 + j)
        s_j, t_j, _ = mx.sensation_level(tp["mech_bone"].x, cp.p)
        k_j = frames_in(t_j, 0.0, 0.3, HALF)
        starts.append(float(np.max(s_j[k_j])) if k_j.any() else float("nan"))
    startup_sl = float(np.nanmax(starts))
    body = frames_in(t, 0.3, dur, HALF)
    (sla, _, _), conv_alt = sl_alt(taps, p)
    steady = frames_in(t, min(6.0, dur / 2), dur, HALF)
    steady_sl = float(np.max(sl[steady])) if steady.any() else float("nan")
    M = [
        Metric("T6.shaper_inband_dbfs", "T6", inb, "dBFS", "<=", -90.0,
               "spec s6 L346 / D6 L177 (noise ~-90 dB re FS across 0.2-20 kHz, zero when squelched)", "spec", []),
        Metric("T6.squelched_frac", "T6", ctx.side["squelched_frac"], "frac", ">=", 0.95,
               "spec D6 L178-181 (silence = exact 50% square wave); 95% is a proposed floor", "assumed", ["mic_ein", "adf"]),
        Metric("T6.squelch_margin_db", "T6", p["squelch_dbfs"] - idle_env_db, "dB", ">=", 6.0,
               "spec T6 L43 + R21 L614: squelch threshold above the DSP idle output (mic self-noise leaking through the gate); 6 dB proposed. "
               "Depends on the flat-EIN assumption (+3 dB mic noise -> 4.7 dB, finding F3)", "assumed", ["mic_ein", "adf"]),
        Metric("T6.idle_sl_max_db", "T6", float(np.max(sl[body])) if body.any() else float("nan"), "dB SL", "<=", 0.0,
               "spec T6 L43 (inaudible to her, no hiss, no whine); D11 L211; 0.3 s-end", "spec", ["mic_ein", "exciter", "mech_bone"],
               note=f"{conv_alt}: {float(np.max(sla[body])) if body.any() else float('nan'):.1f} dB SL; steady (6 s-end) {steady_sl:.1f}"),
        Metric("T6.startup_sl_max_db", "T6", startup_sl, "dB SL", "<=", 0.0,
               f"spec T6 L43 + D17 L295 (no click or burst at power-on); first 0.3 s: the DSP floor tracker initialises on the first frame; worst of {N_STARTUP} power-ons", "spec",
               ["mic_ein", "exciter", "mech_bone"], note=f"per power-on {[round(x, 1) for x in starts]}; main run {conv_alt}: {float(np.max(sla[k0])) if k0.any() else float('nan'):.1f} dB SL"),
    ]
    info = dict(dsp_idle_env_dbfs_rms=round(float(idle_env_db), 1), dsp_out_dbfs_peakref=round(mx.dbfs_rms_peakref(dsp.x), 1), mic_band_force_noise_n_rms=f_noise, max_leak_pa_per_n_for_6db_below_mic_floor=leak_max,
                mic_floor_pa_20_85k=float(ein), psrr_mode=p["psrr_mode"],
                mic_vdd_noise_v_rms=ctx.side.get("mic_vdd_noise_v_rms", 0.0), mic_inj_fs_rms=ctx.side.get("mic_inj_fs_rms", 0.0))
    return M, info, taps, ctx, st


def _tone_duty(f, dbfs, dur, rng, over=None, quantise=True):
    p = make_params(over)
    n = int(dur * sg.FS_DSP)
    y = 10 ** (dbfs / 20) * np.sin(2 * np.pi * f * np.arange(n) / sg.FS_DSP)
    ctx = Ctx(p, rng)
    return y, ctx, p


def _bridge_thdn(f, dbfs, over=None, quantise=False, dur=0.1, seed=7):
    """Distortion added after the DSP: duty -> bridge -> exciter vs the ideal linear exciter response."""
    rng = np.random.default_rng(seed)
    y, ctx, p = _tone_duty(f, dbfs, dur, rng, over)
    exc = sg.Exciter()
    if quantise:
        d = sg.PwmShaper().process(Sig(y, sg.FS_DSP, "duty"), ctx).x
    else:
        d = signal.resample_poly(y, 16, 1, window=("kaiser", 9.0))
    ref = exc.current(p["vdd"] * d if not quantise else p["vdd"] * signal.resample_poly(y, 16, 1, window=("kaiser", 9.0)), p)
    br = sg.Bridge(exc)
    br.process(Sig(d, sg.FS_PWM, "duty"), ctx)
    i = ctx.side["coil_i"].x
    return mx.inband_error_db(i, ref, sg.FS_PWM, (200, 16e3)), ctx


def switch_level(m_all, td=12.5e-9, L=0.3e-3, R=9.52, vdd=3.0, t_start=0.0):
    """Exact switch-level AD bridge into R+L (per period, diode clamp in dead time, like
    sim/checks/deadtime_switching.py but for any duty sequence and any start phase). Returns the
    per-period mean coil current (A). Validation hook for the averaged Bridge model."""
    import deadtime_switching as dts
    T = dts.T_PWM
    i, out = 0.0, np.empty(len(m_all))
    for n, m in enumerate(m_all):
        dA = (1 + m) / 2
        sA0, eA = dts.leg_edges(dA, inverted=False)
        sB0, eB = dts.leg_edges(dA, inverted=True)
        pts = {0.0, T}
        for t, _ in eA + eB:
            pts.add(t)
            pts.add(min(t + td, T))
        pts = sorted(pts)
        acc = 0.0
        for t0, t1 in zip(pts[:-1], pts[1:]):
            if n == 0:
                t0 = max(t0, t_start)
            dt = t1 - t0
            if dt <= 0:
                continue
            sA, dA_ = dts.leg_state(sA0, eA, t0 + 1e-15, td)
            sB, dB_ = dts.leg_state(sB0, eB, t0 + 1e-15, td)
            vA = (0.0 if i > 0 else vdd) if dA_ else sA * vdd
            vB = (vdd if i > 0 else 0.0) if dB_ else sB * vdd
            i_inf = (vA - vB) / R
            dec = np.exp(-R * dt / L)
            c = i - i_inf
            acc += i_inf * dt + c * (L / R) * (1 - dec)
            i = i_inf + c * dec
        out[n] = acc / T
    return out


def thd_spice_like(i, fs, f_sig, t0=300e-6):
    """THD+N exactly as sim/checks/bridge_spice.thd defines it: 0.3-16 kHz excluding +-800 Hz around the tone, re the tone."""
    y = i[int(t0 * fs):]
    n = len(y) - len(y) % int(fs / f_sig)
    y = (y[:n] - np.mean(y[:n])) * np.hanning(n)
    Y = np.abs(np.fft.rfft(y))
    f = np.fft.rfftfreq(n, 1 / fs)
    fund = Y[np.argmin(np.abs(f - f_sig))]
    band = (f > 300) & (f < 16e3) & (np.abs(f - f_sig) > 800)
    return float(20 * np.log10(np.sqrt(np.sum(Y[band] ** 2)) / fund))


def behavioural_thd(td_ns, amp, over=None, f=2000.0, n=380):
    """Behavioural bridge in the SPICE testbench configuration: R 8 ohm, L 0.3 mH, no motional branch, no wire/shunt."""
    p = make_params(dict(over or {}, dead_time_ns=td_ns, l_exc=0.3e-3, r_exc=8.0, r_wire=0.0, r_shunt=0.0,
                         bl=None, rm_pk=1e-3, m_eff=0.6e-3, f0=800.0, qm=3.0))   # motional branch off, as in the SPICE testbench
    m = amp * np.sin(2 * np.pi * f * (np.arange(n) + 0.5) * 5e-6)
    ctx = Ctx(p, np.random.default_rng(0))
    sg.Bridge(sg.Exciter()).process(Sig(m, sg.FS_PWM, "duty"), ctx)
    return thd_spice_like(ctx.side["coil_i"].x, sg.FS_PWM, f)


def scn_spice(over=None):
    """Validation of the behavioural Bridge against ngspice (DMC2400UV stand-in model). ~5 s and ~450 MB per case
    (measured 2026-10-02); NOT part of `all`."""
    import bridge_spice as bs
    rows = {}
    for td in (12.5, 25.0):
        r = bs.run_case(td * 1e-9, 0.251, 0.3e-3, n_per=380)
        v, _, _ = bs.thd(r["t"], r["i_load"], 2000.0, 300e-6)
        rows[td] = dict(spice_db=round(float(v), 1), model_db=round(behavioural_thd(td, 0.251, over), 1))
    d = abs(rows[12.5]["spice_db"] - rows[12.5]["model_db"])
    d25 = abs(rows[25.0]["spice_db"] - rows[25.0]["model_db"])
    M = [Metric("spice.validation_delta_25ns_db", "spice", d25, "dB", "<=", 3.0,
                "C3 s5 / bridge_spice.py (DMC2400UV, -12 dBFS, 25 ns, 0.3 mH): OUT-OF-SAMPLE point (the model is fitted at 12.5 ns); 3 dB tolerance assumed",
                "assumed", ["fet_model"], note=f"calibration residual at the fitted 12.5 ns point: {d:.2f} dB (not a validation)")]
    return M, dict(cases=rows, calib_residual_12p5ns_db=round(d, 2),
                   note="fitted at 12.5 ns (dt_overlap 10.5 ns); 25 ns is out of sample; at -40 dBFS the model has no dead-time term (SPICE -61/-48/-44 dB at 12.5/25/37.5 ns). H3 grid adds L 1.26 mH and -40 dBFS points.")


def pop_sl(t_start, over=None, n_per=9000):
    p = make_params(over)
    exc = sg.Exciter()
    i = switch_level(np.zeros(n_per), td=p["dead_time_ns"] * 1e-9, L=p["l_exc"], R=exc.r_total(p), vdd=p["vdd"], t_start=t_start)
    bl = exc.derive(p)["bl"]
    sl, t, _ = mx.sensation_level(bl * i, p)
    return float(np.max(sl)), float(np.mean(i) * 1e3), float(np.max(np.abs(i)) * 1e3)


def image_tone_test(over=None, f=2400.0, dur=0.5, seed=9):
    """Interpolator images into the protected 8-16 kHz band: one tone AT the ceiling through x16 interpolation + shaper
    + bridge + exciter + force -> SL per third-octave. Also the image rejection in the duty domain (tone vs strongest image
    line at 12.5 kHz +- f, 25 kHz - f ...) so the firmware gets a number (FWSIM-R14)."""
    p = make_params(over)
    rng = np.random.default_rng(seed)
    n = int(dur * sg.FS_DSP)
    y = 10 ** (p["ceiling_dbfs"] / 20) * np.sin(2 * np.pi * f * np.arange(n) / sg.FS_DSP)
    ctx = Ctx(p, rng)
    d = sg.PwmShaper().process(Sig(y, sg.FS_DSP, "duty"), ctx)
    exc = sg.Exciter()
    sg.Bridge(exc).process(d, ctx)
    force = exc.derive(p)["bl"] * ctx.side["coil_i"].x
    sl, t, _ = mx.sensation_level(force, p)
    k = t > 0.1
    bands = [list(mx.THIRD_OCT).index(fc) for fc in (8000, 10000, 12500, 16000)]
    sl_img = float(max(np.max(sl[k][:, b]) for b in bands))
    x = d.x[int(0.1 * sg.FS_PWM):]
    w = np.hanning(len(x))
    X = np.abs(np.fft.rfft(x * w))
    fr = np.fft.rfftfreq(len(x), 1 / sg.FS_PWM)
    tone = X[np.argmin(np.abs(fr - f))]
    imgs = {fi: X[np.argmin(np.abs(fr - fi))] for fi in (12500 - f, 12500 + f) if 8000 <= fi <= 16000}
    rej = float(20 * np.log10(tone / max(max(imgs.values()), 1e-30)))
    return sl_img, rej, ctx.side["ccr_stream_peak"], ctx.side["x_interp_peak"]


def hf_split(over=None):
    """Who makes the 8-16 kHz SL of a ceiling tone: total, without the dead-time error (images + shaped noise only), and the
    interpolator rejection needed if images alone had to stay below threshold (from a linear-interpolation run)."""
    o = dict(over or {})
    tot, rej, ccr, xi = image_tone_test(o)
    no_dt = image_tone_test(dict(o, dead_time_ns=o.get("dt_overlap_ns", 10.5)))[0]
    sl_lin, rej_lin, _, _ = image_tone_test(dict(o, interp="linear", dead_time_ns=o.get("dt_overlap_ns", 10.5)))
    return dict(total_sl=tot, no_deadtime_sl=no_dt, image_rejection_db=rej, ccr_peak=ccr, x_interp_peak=xi,
                interp_need_db=rej_lin + max(sl_lin, 0.0), linear_sl=sl_lin, linear_rejection_db=rej_lin)


def scn_D17(dur=1.0, seed=5, over=None):
    """S-D17: ceiling under a very loud source, bridge distortion vs C3/SPICE, pop-free start, interpolator images.
    Runs at the exciter's peak-current corner (R 8 ohm, L 0.3 mH: docs/sim/shared-params.yaml#exciter.corners) unless overridden."""
    n = int(dur * FS)
    over = dict(sg.PEAK_CORNER, **(over or {}))
    src = lvl(burst_train(40e3, np.arange(0.1, dur - 0.1, 0.06), 8, n), 105)       # HC-SR04 at ~10 cm
    taps, ctx, st = run_chain(src, over, seed)
    p = ctx.p
    dsp = taps["dsp"]
    pk = float(np.max(np.abs(dsp.x)))
    peak_ma = ctx.side["bridge_peak_a"] * 1e3
    th12, _ = _bridge_thdn(2400.0, -12.0, over, quantise=False)
    th12_25, _ = _bridge_thdn(2400.0, -12.0, dict(over, dead_time_ns=25.0), quantise=False)
    th40, _ = _bridge_thdn(2400.0, -40.0, over, quantise=True)
    sl_clean, mean_clean, pk_clean = pop_sl(0.0, over)
    sl_bad, mean_bad, pk_bad = pop_sl(1.25e-6, over)
    hf = hf_split(over)
    sl_img, rej, ccr_pk, xi_pk = hf["total_sl"], hf["image_rejection_db"], hf["ccr_peak"], hf["x_interp_peak"]
    ceil = p["ceiling_dbfs"]
    M = [
        Metric("D17.ceiling_sample_peak_dbfs", "D17", 20 * np.log10(pk + 1e-12), "dBFS", "<=", ceil + 0.5,
               "spec D17 L294 (fixed ceiling): invariant = the configured ceiling holds; 12.5 kS/s sample peak (pipeline.limiter backstop = ceiling + 3 dB)", "derived", []),
        Metric("D17.ceiling_true_peak_dbfs", "D17", 20 * np.log10(ctx.side["x_interp_peak"] + 1e-12), "dBFS", "<=", ceil + 0.5,
               "spec D17 L294: invariant = the configured ceiling holds as a TRUE peak after the x16 interpolation (pre-quantiser tap, docs/sim/shared-params.yaml#ceiling)", "derived", []),
        Metric("D17.peak_coil_ma", "D17", peak_ma, "mA", "<=", 300.0,
               "sub-power.md: U4 TPS7A2030 rated 300 mA (ECR-0005); peak-current corner R 8 ohm, L 0.3 mH", "derived", ["exciter"]),
        Metric("D17.bridge_only_thdn_m12_db", "D17", th12, "dB", "<=", -46.0,
               "spec D6 L173 / C3 s5: SPICE -52 dB at the ceiling, 12.5 ns; +6 dB tolerance. Model is CALIBRATED to this point", "derived", ["fet_model"]),
        Metric("D17.bridge_only_thdn_m12_25ns_db", "D17", th12_25, "dB", "<=", -46.0,
               "spec D6 L170 allows 1-2 ticks (12.5-25 ns); SPICE itself gives -38 dB at 25 ns (spec L173): 2 ticks needs dead-time compensation (S2)", "derived", ["fet_model"]),
        Metric("D17.chain_thdn_m40_db", "D17", th40, "dB", "<=", -45.0,
               "spec D6 L173 (-61 dB at -40 dBFS, bridge only) + shaper floor ~-90 dBFS vs a -40 dBFS tone = -50 dB; 5 dB margin", "derived", ["fet_model"]),
        Metric("D17.tone_hf_sl_max_db", "D17", sl_img, "dB SL", "<=", 0.0,
               "spec s6 L348 + R9 L602 (8-16 kHz protected): a 2.4 kHz tone at the ceiling leaves nothing audible in the 8-16 kHz third-octaves "
               "(interpolator images + bridge dead-time harmonics + shaped noise)", "derived", ["exciter", "mech_bone", "fet_model"],
               note=(f"without the dead-time error {hf['no_deadtime_sl']:.1f} dB SL (so the excess is bridge harmonics); duty-domain image rejection "
                     f"{rej:.1f} dB (interp={p['interp']}); linear interp {hf['linear_rejection_db']:.1f} dB -> {hf['linear_sl']:.1f} dB SL; "
                     f"interpolator needs >= {hf['interp_need_db']:.0f} dB image rejection at this proxy")),
        Metric("D17.pop_clean_start_sl_db", "D17", sl_clean, "dB SL", "<=", 0.0,
               "spec D17 L295 + D6 L180-181 (no click at start); TIM1 started at counter 0, d=50%", "spec", ["exciter", "mech_bone"]),
    ]
    info = dict(corner=sg.PEAK_CORNER, ccr_stream_peak=round(ccr_pk, 4), x_interp_peak_tone=round(xi_pk, 4),
                ccr_bound_fwsim_r15_old=round(10 ** (ceil / 20) + 1 / 200, 4), ccr_bound_shared=round(10 ** (ceil / 20) + 7.67 * 1.5 * 2 / 200, 4),
                image_rejection_duty_db=round(rej, 1), hf_split={k: round(float(v), 2) for k, v in hf.items()}, thdn_m12_25ns_db=round(th12_25, 1),
                pop_bad_start_sl_db=round(sl_bad, 1), pop_bad_start_peak_ma=round(pk_bad, 1),
                pop_clean_mean_ma=round(mean_clean, 3),
                peak_coil_ma_at_ceiling_signal=round(peak_ma, 1),
                note="bad start = bridge enabled a quarter period late (first A-high pulse full width): a +12.5 mA ripple offset that decays with L/R. Clean start = counter 0, d=50%, ripple centred (sub-output.md: OSSI/OISx before MOE).")
    return M, info, taps, ctx, st


def scn_R15(dur=4.0, seed=8, over=None, preroll=PREROLL_S):
    """S-R15 self-noise (spec R15 L609): own speech with fricative ultrasound, chewing clicks, hair rustle; no external
    ultrasound. Transient-only must stay (mostly) silent. Levels ASSUMED (param r15_us_db, default 40 dB SPL)."""
    o = dict(over or {})
    lv = dict(us_db=float(o.pop("r15_us_db", 40.0)), speech_db=float(o.pop("r15_speech_db", 75.0)),
              chew_db=float(o.pop("r15_chew_db", 55.0)), hair_db=float(o.pop("r15_hair_db", 35.0)))   # -200 drops a part
    us = lv["us_db"]
    src, w = self_noise(dur, seed, preroll, **lv)
    taps, ctx, st = run_chain(src, o, seed)
    p = ctx.p
    sh, dsp = taps["shaper"], taps["dsp"]
    a, b = w["measure"]
    m = (sh.t >= a) & (sh.t < b)
    active = float(np.mean(sh.x[m] != 0))
    sl, t, nl = sl_of(taps, p)
    (sla, _, _), conv_alt = sl_alt(taps, p)
    k = win_frames(t, a, b)
    sl90 = float(np.percentile(np.max(sl[k], axis=1), 90))
    sl90_alt = float(np.percentile(np.max(sla[k], axis=1), 90))
    M = [
        Metric("R15.active_frac", "R15", active, "frac", "<=", 0.10,
               "spec R15 L609 (self-noise makes transient mode busy): with only the wearer's own noise the output is active <= 10 % of the time (proposed)",
               "assumed", ["acoustic_path", "mic_ein"]),
        Metric("R15.sl_p90_db", "R15", sl90, "dB SL", "<=", 0.0,
               "spec R15 L609 + T1 L38: own speech/chewing/hair inaudible 90 % of the time (proposed)", "assumed",
               ["acoustic_path", "mic_ein", "exciter", "mech_bone"], note=f"{conv_alt}: {sl90_alt:.1f} dB SL"),
    ]
    info = dict(levels_db_spl=lv, preroll_s=preroll,
                dsp_out_dbfs=round(window_dbfs(dsp, a, b), 1), levels="ASSUMED: no recording of the owner (S1 retires)")
    return M, info, taps, ctx, st


def scn_lat(seed=6, over=None):
    """S-lat: 40 kHz burst onset to output onset (DSP out and coil current), plus budgeted firmware latency."""
    dur = 0.6
    n = int(dur * FS)
    t0 = 0.25
    k = (np.arange(n) / FS >= t0) & (np.arange(n) / FS < t0 + 0.2)
    src = lvl(np.sin(2 * np.pi * 40e3 * np.arange(n) / FS) * k, 80)
    taps, ctx, st = run_chain(src, dict(over or {}, transient_only=False), seed)
    out = {}
    for name in ("dsp", "exciter"):
        s = taps[name]
        e = mx.envelope(s.x, s.fs, 0.0005)
        plateau = np.percentile(e[int((t0 + 0.05) * s.fs): int((t0 + 0.15) * s.fs)], 50)
        idx = np.argmax(e[int((t0 - 0.05) * s.fs):] >= 0.5 * plateau) + int((t0 - 0.05) * s.fs)
        out[name] = (idx / s.fs - t0) * 1e3
    budget = dict(frame_complete_ms=1.28, dma_hop_ms=0.64, compute_ms=0.64, ccr_fifo_ms=0.64)
    total = out["exciter"] + sum(budget.values())
    M = [Metric("lat.total_ms", "lat", total, "ms", "<=", 20.0,
                "spec s5.3 L337 (<= 20 ms end to end); sim measured + budgeted firmware terms", "spec", ["exciter"])]
    info = dict(sim_dsp_out_onset_ms=round(out["dsp"], 2), sim_coil_onset_ms=round(out["exciter"], 2), budget_ms=budget,
                note="algo_b stamps hop h's output at the frame START; a causal firmware emits it after the frame (1.28 ms) ends: the budget adds that back. Compute and DMA terms are derived, unmeasured (S3 cycle counter).")
    return M, info, taps, ctx, st


def scn_pwr(taps_ctx=None, seed=1):
    """S-pwr: sim-derived bridge + exciter draw for the house-walk scene, folded into sim/checks/power.py's table."""
    import power as pw
    if taps_ctx is None:
        _, _, taps, ctx, st = scn_T1(2.0, seed)        # was scn_T1(1.0): house_walk needs >= 2 s (fixed 2026-10-02)
    else:
        taps, ctx, st = taps_ctx
    sim_ma = ctx.side["i_sup_avg_ma"]
    keep = [k for k in pw.ACTIVE if not k.startswith("bridge") and not k.startswith("transducer") and not k.startswith("gate pull")]
    rt = {}
    for j, lab in enumerate(("low", "nominal", "high")):
        tot = sum(pw.ACTIVE[k][j] for k in keep) + sim_ma
        rt[lab] = dict(total_ma=round(tot, 2), runtime_h=round(175 * pw.USABLE[j] / tot, 1))
    budget_high = pw.ACTIVE["bridge gate charge + ripple"][2] + pw.ACTIVE["transducer, listening level"][2] + pw.ACTIVE["gate pull resistors (4 x 100k)"][2]
    M = [
        Metric("pwr.bridge_exciter_ma", "pwr", sim_ma, "mA", "<=", budget_high,
               "sim/checks/power.py high column (bridge 1.0 + pulls 0.06 + transducer 2.5); spec s7 L408", "derived", ["exciter", "mech_bone"]),
        Metric("pwr.runtime_h_pessimistic", "pwr", rt["high"]["runtime_h"], "h", ">=", 8.0,
               "spec D18 L297-298 (>= 8 h, 175 mAh per O16, 75% usable); always awake", "spec", ["exciter"]),
    ]
    info = dict(sim_bridge_exciter_ma=round(sim_ma, 3), power_py_bridge_exciter_nominal_ma=round(0.77 + 0.06 + 1.1, 2), runtime=rt,
                idle_ma=dict(low=sum(v[0] for v in pw.IDLE.values()), nominal=sum(v[1] for v in pw.IDLE.values()),
                             high=sum(v[2] for v in pw.IDLE.values())),
                note="idle mode (bridge stopped) is not simulated here: the idle current is power.py's.")
    return M, info


def scn_selftest():
    """PDM bitstream vs behavioural ADF: tone gain through a true 1-bit 4 MHz stream and CIC5/5."""
    r = sg.pdm_bitstream_selftest(40e3, -26.0, 0.02)
    x = np.sin(2 * np.pi * 40e3 * np.arange(4096) / FS_PCM_) * 0.5
    rt = np.max(np.abs(sg.adf_words_to_pcm(sg.pcm_to_adf_words(x)) - x)) * 2 ** 23
    fw = sg.FirmwareDspShaperStage(lambda w: np.full(128, 100, np.uint16))
    duty = fw.process(Sig(x, FS_PCM_, "FS"), Ctx(make_params(), np.random.default_rng(0))).x
    M = [Metric("mic.pdm_cic5_tone_err_db", "selftest", abs(r["err_db"]), "dB", "<=", 1.0,
                "A3 plan s1.2 (CIC5 droop -0.78 dB at 85 kHz); 1 dB tolerance is assumed", "assumed", ["adf"]),
         Metric("fw_abi.roundtrip_lsb", "selftest", float(rt), "LSB24", "<=", 0.5,
                "A3 plan s1.1 (ADF1 DR: 24-bit left-aligned in DR[31:8]); firmware-in-the-loop ABI", "derived", []),
         Metric("fw_abi.centre_ccr_duty", "selftest", float(np.max(np.abs(duty))), "FS", "<=", 1e-9,
                "spec D6 L166 (CCR 100 of ARR 200 = 50 % = zero differential)", "spec", [])]
    r = dict(r, fw_abi_hops=len(duty) // 128)
    return M, r


# ================================================================================================ plots / output
PLOT_SPAN_S = 2.5   # plotted seconds: a 10 s run plotted whole pushed 'all' to ~3.1 GB RSS (2026-10-02); 2.5 s keeps it < 1.5 GB


def plot_chain(taps, ctx, path, title, t0=0.0, span=PLOT_SPAN_S):
    """Dark proxy plot of [t0, t0+span) only (the measured window; T6: the power-on)."""
    taps = {k: Sig(v.x[int(t0 * v.fs): int((t0 + span) * v.fs)], v.fs, v.unit, v.meta) for k, v in taps.items()}
    plt = plotstyle.apply()
    fig, axs = plt.subplots(5, 1, figsize=(10, 12), sharex=True, gridspec_kw={"height_ratios": [2.4, 2.4, 2, 2, 2]})
    rows = [("src", 1024, 100, "air pressure at the lid (Pa) -> spectrogram, 0-100 kHz"),
            ("adf", 512, 100, "ADF1 PCM at 200 kS/s, 0-100 kHz (mic + EQ-free, after CIC5/RSFLT model)"),
            ("dsp", 256, 6, "DSP output 12.5 kS/s, 0-6 kHz (algorithm B)")]
    for ax, (k, nps, fmax, ttl) in zip(axs[:3], rows):
        s = taps[k]
        f, t, S = signal.spectrogram(s.x, s.fs, nperseg=nps, noverlap=int(nps * 0.75))
        Sd = 10 * np.log10(S + 1e-18)
        vmax = np.percentile(Sd, 99.9)
        ax.pcolormesh(t, f / 1e3, Sd, vmin=vmax - 70, vmax=vmax, cmap="magma", shading="auto")
        ax.set_ylim(0, fmax)
        ax.set_ylabel("kHz")
        ax.set_title(ttl, loc="left")
    i = taps["exciter"]
    f, t, S = signal.spectrogram(i.x, i.fs, nperseg=4096, noverlap=3072)
    Sd = 10 * np.log10(S + 1e-24)
    vmax = np.percentile(Sd, 99.9)
    axs[3].pcolormesh(t, f / 1e3, Sd, vmin=vmax - 80, vmax=vmax, cmap="magma", shading="auto")
    axs[3].set_ylim(0, 20)
    axs[3].set_ylabel("kHz")
    axs[3].set_title("coil current after shaper + bridge + exciter (stub exciter), 0-20 kHz", loc="left")
    sl, ts, nl = sl_of(taps, ctx.p)
    im = axs[4].pcolormesh(ts, mx.THIRD_OCT / 1e3, sl.T, vmin=-30, vmax=70, cmap="magma", shading="auto")
    axs[4].set_yscale("log")
    axs[4].set_ylabel("kHz")
    axs[4].set_title("sensation level re the owner's threshold, dB (STUB exciter force + threshold table: not meaningful yet)",
                     loc="left", color=plotstyle.SERIES[3])
    axs[4].set_xlabel("seconds")
    fig.suptitle(title, color=plotstyle.TEXT, fontsize=11)
    fig.savefig(path)
    plt.close(fig)


def report(name, M, info, status, t_run, ctx=None, extra=None):
    print(f"\n=== {name} ({t_run:.1f} s) ===")
    for m in M:
        print(m.line(status))
    rows = [m.as_dict(status) for m in M]
    import resource
    return dict(scenario=name, runtime_s=round(t_run, 1), peak_rss_mb=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024),
                stage_status=status, metrics=rows, info=info,
                params={k: v for k, v in (ctx.p.items() if ctx else []) if v != sg.DEFAULT_PARAMS.get(k)})


def jdump(o):
    def conv(x):
        if isinstance(x, (np.floating, np.integer)):
            return float(x)
        if isinstance(x, np.ndarray):
            return x.tolist()
        raise TypeError(type(x))
    return json.dumps(o, indent=2, default=conv)


# ================================================================================================ sweeps
def sweep(name, seed=1):
    rows = []
    if name == "exciter":
        for r in (8.0, 10.0, 12.0):
            for L in (0.3e-3, 1.26e-3):
                o = dict(r_exc=r, l_exc=L)
                n = int(0.5 * FS)
                src = lvl(burst_train(40e3, np.arange(0.05, 0.4, 0.06), 8, n), 105)
                taps, ctx, st = run_chain(src, o, seed)
                th, _ = _bridge_thdn(2400.0, -12.0, o)
                rows.append(dict(r_ohm=r, l_mh=L * 1e3, peak_ma=round(ctx.side["bridge_peak_a"] * 1e3, 1),
                                 ripple_pk_ma=round(ctx.side["i_ripple_pk"] * 1e3, 2), thdn_m12_db=round(th, 1),
                                 sup_avg_ma=round(ctx.side["i_sup_avg_ma"], 2)))
    elif name == "mic":
        for s_db in (-1.0, 0.0, 1.0):
            M, info, taps, ctx, st = scn_T1(2.0, seed, dict(mic_sens_db=s_db))
            rows.append(dict(mic_sens_db=s_db, **{m.id: round(m.value, 1) for m in M}))
    elif name == "port":
        profiles = {"flat": None, "25k +10 dB Q5": [(25e3, 5, 10.0)], "25k -10 dB Q5": [(25e3, 5, -10.0)],
                    "60k +6 dB Q3": [(60e3, 3, 6.0)], "40k -12 dB Q8 (notch)": [(40e3, 8, -12.0)]}
        n = int(0.4 * FS)
        t = np.arange(n) / FS
        for pname, bands in profiles.items():
            lv = {}
            for f in (25e3, 40e3, 60e3, 80e3):
                src = lvl(np.sin(2 * np.pi * f * t) * (t > 0.05), 55)     # below the ceiling so the EQ/port effect is visible
                taps, ctx, st = run_chain(src, dict(port_bands=bands, transient_only=False), seed)
                lv[f"{int(f / 1e3)}k"] = round(window_dbfs(taps["dsp"], 0.25, 0.38), 1)
            rows.append(dict(profile=pname, **lv))
    elif name == "supply":
        n = int(0.6 * FS)
        for mode in ("flat55", "pess35", "rolloff"):          # shared-params#psrr: nominal | pessimistic | worst
            for mv in (0.0, 0.1, 0.3, 1.0, 3.0, 10.0):
                taps, ctx, st = run_chain(np.zeros(n), dict(psrr_mode=mode, ext_ripple_mv=mv), seed)
                rows.append(dict(psrr=mode, ripple_mv=mv, inj_fs_rms_db=round(20 * np.log10(ctx.side.get("mic_inj_fs_rms", 1e-9) + 1e-12), 1),
                                 dsp_out_dbfs=round(mx.dbfs_rms_peakref(taps["dsp"].x[int(0.05 * 12500):]), 1),
                                 squelched=round(ctx.side["squelched_frac"], 2)))
    else:
        raise SystemExit(f"unknown sweep {name}")
    print(f"\n=== sweep {name} ===")
    keys = list(rows[0])
    print(" | ".join(f"{k:>16s}" for k in keys))
    for r in rows:
        print(" | ".join(f"{str(r[k]):>16s}" for k in keys))
    (OUT / f"sweep_{name}.json").write_text(jdump(rows))
    return rows


# ================================================================================================ main
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scenario", default="T1", choices=["T1", "T2", "T3", "T6", "D17", "lat", "pwr", "selftest", "spice", "R15", "all"])
    ap.add_argument("--dur", type=float, default=None, help="measured seconds for T1/T2/R15 (after the pre-roll) and T6 total; default per scenario")
    ap.add_argument("--preroll", type=float, default=PREROLL_S, help="pre-roll seconds before the measured window (T1/T2/R15)")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--set", nargs="*", default=[], help="param overrides, key=value (python literal)")
    ap.add_argument("--sweep", default=None, choices=["exciter", "mic", "port", "supply"])
    ap.add_argument("--no-plot", action="store_true")
    a = ap.parse_args(argv)
    over = {}
    for kv in a.set:
        k, v = kv.split("=", 1)
        try:
            over[k] = ast.literal_eval(v)
        except (ValueError, SyntaxError):      # bare word or path (psrr_mode=rolloff, port_json=sim/...): keep as text
            over[k] = v
    t00 = time.time()
    if a.sweep:
        sweep(a.sweep, a.seed)
        return 0
    todo = ["T1", "T2", "T3", "T6", "D17", "lat", "pwr", "selftest", "R15"] if a.scenario == "all" else [a.scenario]
    results, t1_pack = [], None
    for sc in todo:
        t0 = time.time()
        if sc == "pwr":
            M, info = scn_pwr(t1_pack, a.seed)
            r = report("pwr", M, info, {"exciter": "stub", "mech_bone": "stub"}, time.time() - t0)
        elif sc == "spice":
            M, info = scn_spice(over)
            r = report("spice", M, info, {}, time.time() - t0)
        elif sc == "selftest":
            M, info = scn_selftest()
            r = report("selftest", M, info, {"adf": "stub"}, time.time() - t0)
        else:
            fn = dict(T1=scn_T1, T2=scn_T2, T3=scn_T3, T6=scn_T6, D17=scn_D17, lat=scn_lat, R15=scn_R15)[sc]
            kw = dict(over=over, seed=a.seed)
            if sc in ("T1", "T2", "T6", "R15") and a.dur is not None:
                kw["dur"] = a.dur
            if sc in ("T1", "T2", "R15"):
                kw["preroll"] = a.preroll
            M, info, taps, ctx, st = fn(**kw)
            if sc == "T1":
                t1_pack = (None, ctx, st)      # pwr needs only ctx.side (keeps memory flat in 'all')
            r = report(sc, M, info, st, time.time() - t0, ctx)
            r["stage_timing_s"] = {k[2:]: v for k, v in ctx.side.items() if k.startswith("t_")}
            if not a.no_plot:
                plot_chain(taps, ctx, OUT / f"{sc}_spectrogram.png", f"S-{sc}: end-to-end chain (dark proxy plot, measured window; stubs: "
                           + ", ".join(k for k, v in st.items() if v == "stub") + ")", t0=kw.get("preroll", 0.0))
            del taps
        print("   info:", json.dumps(info, default=float)[:400])
        (OUT / f"{sc}.json").write_text(jdump(r))
        results.append(r)
    allm = [m for r in results for m in r["metrics"]]
    cnt = {s: sum(1 for m in allm if m["status"] == s) for s in ("PASS", "WARN", "OPEN", "FAIL")}
    print(f"\nsummary: {cnt}  total {time.time() - t00:.1f} s  -> {OUT}")
    if a.scenario == "all":
        (OUT / "summary.json").write_text(jdump(dict(counts=cnt, runtime_s=round(time.time() - t00, 1), scenarios=results)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
