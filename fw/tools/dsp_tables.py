"""fw/tools/dsp_tables.py: fw/gen/dsp_tables.h for the DSP chain (FWSIM-R13, R14; determinism rules: tables, not libm).
Called by fw/tools/gen.py (output dsp_tables.h). Every filter is designed here, ONCE, from the numeric reference
(sim/dsp/pipeline.py, sim/e2e/stages.py) and written as exact float32 hex literals. Audience: Claude instances.

  hann + eq2        algo_b analysis: Hann(256) x 2^-31 (DR word -> FS), (2/sum(win) x 10^(-mic_response_db/20))^2 per bin
  noise_band        pipeline.calibrate_noise as stages.DspStage does it (nominal mic, seed 99, 0.5 s, D2 decimation), per variant
  sin               1024-entry sine + guard (oscillator bank, algorithm-A LO); linear interpolation error 4.7e-6 (-106 dB)
  fft               bit-reverse pairs + twiddles of the 256-pt real FFT (128-pt complex radix-2 + real split)
  interp            x16 polyphase interpolator (remez, 16*TPP-1 taps + 1 zero), pass 0-4.25 kHz, stop 8.25-100 kHz (e2e F5: >= 67 dB)
  hb                pipeline.decimate_to_fs 31-tap half-band (D2 front end)
  a_*               algorithm A = pipeline.algo_a_base: mix -> 16-tap /4 -> 40-tap /4 -> butter(2) HP at 12.5 kS/s (lead decision 2026-10-07)
  ntf               3rd-order error-feedback shaper: (1 - z^-1)(1 - 2cos(wz) z^-1 + z^-2), zero pair at 13 kHz (stages.PwmShaper), per PWM rate
"""
import math
import struct
import sys
from pathlib import Path

import numpy as np
from scipy import signal

FW = Path(__file__).resolve().parents[1]
REPO = FW.parent
INTERP_TPP = (8, 10, 12)
INTERP_WEIGHT = 30.0        # stopband weight: TPP 10 -> ~70 dB images in 8.25-16 kHz (>= 67 dB, e2e F5)
FS, FS_OUT, NFFT = 200_000, 12_500, 256


def hexf(x):
    f = struct.unpack("<f", struct.pack("<f", float(x)))[0]
    return "0x0p+0f" if f == 0.0 else float.hex(f) + "f"


def arr(name, vals, per=6, ctype="float"):
    vals = list(vals)
    out = [f"#define {name}_N {len(vals)}u", f"#define {name}_INIT {{ \\"]
    for i in range(0, len(vals), per):
        chunk = vals[i:i + per]
        out.append("    " + ", ".join(hexf(v) if ctype == "float" else (f"{int(v)}" if ctype == "i16" else f"{int(v)}u") for v in chunk) + ", \\")
    out.append("}")
    return out


def interp_proto(tpp):
    h = signal.remez(16 * tpp - 1, [0, 4250, 8250, FS / 2], [1, 0], weight=[1, INTERP_WEIGHT], fs=FS)
    h = np.append(h, 0.0) * 16.0                       # x16 zero-stuffing gain; even length for the polyphase split
    w, H = signal.freqz(h / 16.0, worN=1 << 15, fs=FS)
    g = 20 * np.log10(np.abs(H) / abs(H[0]) + 1e-15)
    rej = float(-g[(w >= 8250) & (w <= 16000)].max())
    return h, rej


def a_filters():
    sys.path.insert(0, str(REPO / "sim/dsp"))
    import pipeline as pl                                               # noqa: E402
    h1, h2 = pl.a_decimators()
    hp = signal.butter(2, 1250.0, "hp", fs=FS_OUT, output="sos")[0]     # pipeline.algo_a_base HP at 12.5 kS/s
    return hp, h1, h2


def noise_bands():
    sys.path.insert(0, str(REPO / "sim/dsp"))
    import pipeline as pl                                               # noqa: E402
    x = pl.decimate_to_fs(pl.microphone(np.zeros(int(0.5 * pl.FS_IN)), seed=99, noise_scale=1.0))
    out = {}
    for name, nb, hop in (("SPEC", 28, 128), ("SLIM", 16, 256)):
        c = pl.BConfig(n_bands=nb, hop=hop, transient_only=False, noise_band=None)
        out[name] = pl.algo_b(x, c)[1]["band_energy"].mean(axis=0)
    return out


def a_noise_sm():
    """mean of algorithm A's gate envelope (|y| pi/2, one-pole 0.02) on the mic self-noise alone (same calibration input as
    noise_bands): the A gate never opens below noise_margin x this (mirrors B's noise_band rule; e2e F12/F14)"""
    sys.path.insert(0, str(REPO / "sim/dsp"))
    import pipeline as pl                                               # noqa: E402
    x = pl.decimate_to_fs(pl.microphone(np.zeros(int(0.5 * pl.FS_IN)), seed=99, noise_scale=1.0))
    y = pl.algo_a_base(x)
    sm = signal.lfilter([0.02], [1, -0.98], np.abs(y) * np.pi / 2)
    return float(np.mean(sm[len(sm) // 4:]))


def mic_notch():
    """SAI-13 notch of the active design (ULTRASONIC_DESIGN=k4 -> k4, anything else -> r2) from fw/variants.yaml."""
    import os
    import yaml
    d = "k4" if os.environ.get("ULTRASONIC_DESIGN", "").strip().lower() == "k4" else "r2"
    v = yaml.safe_load((REPO / "fw/variants.yaml").read_text())["mic_notch"][d]
    return {"design": d, **{k: float(v[k]["val"]) for k in ("f0_hz", "q", "depth_db")}}


def notch_power(f, f0, q, depth_db):
    """|H|^2 of the analog peaking-EQ cut (gain -depth_db at f0, bandwidth f0/q)."""
    a = 10 ** (-depth_db / 40)
    s = 1j * np.asarray(f, float) / f0
    h = (s * s + s * a / q + 1) / (s * s + s / (a * q) + 1)
    return np.abs(h) ** 2


def generate(hdr):
    sys.path.insert(0, str(REPO / "sim/dsp"))
    import pipeline as pl                                               # noqa: E402
    o = [hdr, "#ifndef FW_GEN_DSP_TABLES_H\n#define FW_GEN_DSP_TABLES_H\n"]
    win = np.hanning(NFFT)
    freqs = np.fft.rfftfreq(NFFT, 1 / FS)
    eq2 = (2.0 / win.sum() * 10 ** (-pl.mic_response_db(freqs) / 20)) ** 2
    nt = mic_notch()
    eq2 = eq2 * notch_power(freqs, nt["f0_hz"], nt["q"], nt["depth_db"])
    o.append("/* algo_b analysis window: np.hanning(256) x 2^-31 (DR word = s24 << 8 -> FS) */")
    o += arr("FW_DSP_HANN", win * 2.0 ** -31)
    o.append("/* per-bin power scale (2/sum(win) x 10^(-mic_response_db(f)/20))^2, pipeline.algo_b eq=True, bins 0..128 */")
    o += arr("FW_DSP_EQ2", eq2)
    o.append(f"/* mic-port resonance notch folded into FW_DSP_EQ2 (variants.yaml mic_notch.{nt['design']}) */")
    o.append(f"#define FW_DSP_NOTCH_F0_HZ {nt['f0_hz']:.1f}f\n#define FW_DSP_NOTCH_Q {nt['q']:.2f}f\n#define FW_DSP_NOTCH_DEPTH_DB {nt['depth_db']:.2f}f")
    nbt = noise_bands()
    o.append("/* mic self-noise band energy (stages.DspStage calibration: nominal EIN, seed 99, 0.5 s); default until a unit calibration is loaded */")
    o += arr("FW_DSP_NOISE_SPEC", nbt["SPEC"])
    o += arr("FW_DSP_NOISE_SLIM", nbt["SLIM"])
    o.append("/* default-knob band centres sqrt(e_b e_b+1) and pipeline.map_freq of them, float64 -> float32 (runtime math has ~1e-7 error,\n"
             " * which drifts the phase of steady tones; the tables are used when band_lo/hi and out_lo/hi are at their defaults) */")
    for name, nb in (("SPEC", 28), ("SLIM", 16)):
        cfg = pl.BConfig(n_bands=nb)
        e = pl.band_edges(cfg)
        g = np.sqrt(e[:-1] * e[1:])
        o += arr(f"FW_DSP_GEO_{name}", g)
        o += arr(f"FW_DSP_MAPGEO_{name}", pl.map_freq(g, cfg))
    o.append("#define FW_DSP_MAP_DEFAULTS(lo, hi, olo, ohi) ((lo) == %d && (hi) == %d && (olo) == %d && (ohi) == %d)" % (20000, 85000, 1500, 4000))
    o.append("/* sin(2 pi i / 1024), i = 0..1024 (guard) */")
    o += arr("FW_DSP_SIN", np.sin(2 * np.pi * np.arange(1025) / 1024))
    # FFT tables: 128-pt complex, bit-reversal pairs (i < rev(i))
    rev = [int(f"{i:07b}"[::-1], 2) for i in range(128)]
    pairs = [(i, rev[i]) for i in range(128) if i < rev[i]]
    o.append(f"/* 7-bit bit-reversal swap pairs ({len(pairs)}) */")
    o += arr("FW_DSP_BITREV", [v for p in pairs for v in p], per=16, ctype="u8")
    tw = np.exp(-2j * np.pi * np.arange(64) / 128)
    twr = np.exp(-2j * np.pi * np.arange(64) / 256)
    o.append("/* exp(-2 pi i m / 128), m < 64, interleaved re, im */")
    o += arr("FW_DSP_TW128", np.column_stack([tw.real, tw.imag]).ravel())
    o.append("/* exp(-2 pi i k / 256), k < 64, interleaved re, im (real split) */")
    o += arr("FW_DSP_TWR256", np.column_stack([twr.real, twr.imag]).ravel())
    # interpolator
    o.append("/* x16 polyphase interpolator: prototype remez(16*TPP-1, pass 0-4250, stop 8250-100000 Hz, weight 1:%g) + 1 zero, x16;\n"
             " * phase p, tap t = h[16 t + p]; group delay (16 TPP - 2)/2 samples at 200 kS/s */" % INTERP_WEIGHT)
    o.append("#ifndef FW_INTERP_TPP\n#define FW_INTERP_TPP 10\n#endif")
    first = True
    for tpp in INTERP_TPP:
        h, rej = interp_proto(tpp)
        poly = np.array([[h[16 * t + p] for t in range(tpp)] for p in range(16)])
        o.append(f"{'#if' if first else '#elif'} FW_INTERP_TPP == {tpp}   /* image rejection 8.25-16 kHz: {rej:.1f} dB */")
        o.append(f"#define FW_INTERP_REJ_DB_X10 {int(rej * 10)}")
        o += arr("FW_DSP_INTERP", poly.ravel())
        q = np.clip(np.round(poly * 32768.0), -32768, 32767)
        assert np.max(np.abs(poly)) < 32767 / 32768, "FMAC coefficients need a 2^-R pre-scale"
        o.append("/* the same phases as FMAC q1.15 coefficients (round), R = 0; kappa = max_p sum_t |h_p[t]| (worst-case overshoot) */")
        o += arr("FW_DSP_INTERP_Q15", q.ravel(), per=16, ctype="i16")
        o += arr("FW_DSP_INTERP_KAPPA", [float(np.max(np.sum(np.abs(poly), axis=1)))])
        first = False
    o.append("#else\n#error \"FW_INTERP_TPP: 8, 10 or 12\"\n#endif")
    # half-band D2
    hb = signal.remez(31, [0, 80e3, 120e3, 200e3], [1, 0], fs=400e3)
    o.append("/* D2 front end: pipeline.decimate_to_fs remez(31, [0, 80k, 120k, 200k]) at 400 kS/s */")
    o += arr("FW_DSP_HB", hb)
    hp, h1, h2 = a_filters()
    o.append("/* algorithm A HP: butter(2, 1250 Hz, hp, fs 12.5k) sos b0 b1 b2 a1 a2 (a0 = 1), pipeline.algo_a_base */")
    o += arr("FW_DSP_A_HP", [hp[0], hp[1], hp[2], hp[4], hp[5]])
    o.append("/* algorithm A decimators (pipeline.a_decimators): 16-tap /4 at 200k, 40-tap /4 at 50k */")
    o += arr("FW_DSP_A_H1", h1)
    o += arr("FW_DSP_A_H2", h2)
    o.append("/* algorithm A: mean gate envelope of the mic self-noise (nominal mic, LO 38 kHz), pre-gain FS units */")
    o += arr("FW_DSP_A_NOISE_SM", [a_noise_sm()])
    o.append("/* shaper NTF zero pair at 13 kHz: 2 cos(2 pi 13000 / f_pwm) for 200, 400, 800 kHz */")
    o += arr("FW_DSP_NTF_2COS", [2 * math.cos(2 * math.pi * 13e3 / f) for f in (200e3, 400e3, 800e3)])
    o.append("\n#endif\n")
    return "\n".join(o)
