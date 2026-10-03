"""Stage models for the end-to-end chain (mic -> exciter -> perceptual proxy).

Contract: docs/sim/e2e-chain.yaml (stages, interfaces, units). Every stage is a Stage subclass with
process(Sig, Ctx) -> Sig. `status` says how far the model can be trusted:
    real  = existing repo model, used as is (sim/dsp/pipeline.py)
    model = new physics/behaviour model with sourced parameters
    stub  = placeholder where an INTERFACE from another sim or an E-item measurement is missing;
            metrics that depend on a stub report WARN, never PASS.
Swap a stage by registering another class with the same id (firmware-in-the-loop: DspStage).
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import yaml
from scipy import signal

REPO = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(REPO / "sim/dsp"), str(REPO / "tools")]
import pipeline as pl  # noqa: E402

# One source for values shared between sims (exciter, PSRR scenarios, thresholds, clocks): docs/sim/shared-params.yaml
SHARED = yaml.safe_load((REPO / "docs/sim/shared-params.yaml").read_text())
_EX = SHARED["exciter"]

FS_AC = pl.FS_IN        # 400 kS/s: air pressure and mic analog output (Nyquist 200 kHz)
FS_PCM = pl.FS          # 200 kS/s: ADF1 output (hardware: 200.02 kS/s = HCLK/400, A3 plan s2)
FS_DSP = pl.FS_OUT      # 12.5 kS/s: algorithm output
FS_PWM = 200_000        # PWM period rate: one duty value per period (TIM1 ARR 200, centre-aligned)
FS_CLK_MIC = int(SHARED["clocks"]["fs_pdm_hz"])  # PDM clock 4,000,450 Hz = HCLK/20 (A3 plan s2); bitstream self-test + CIC model
VDD = 3.0
P_REF = pl.P_REF


@dataclass
class Sig:
    x: np.ndarray
    fs: float
    unit: str
    meta: dict = field(default_factory=dict)

    @property
    def t(self):
        return np.arange(len(self.x)) / self.fs


@dataclass
class Ctx:
    p: dict                                   # parameters (see DEFAULT_PARAMS)
    rng: np.random.Generator
    side: dict = field(default_factory=dict)  # side outputs one stage leaves for another (supply current, ...)
    inject: Sig | None = None                 # supply-noise injection at the mic VDD pin, volts @ FS_AC


DEFAULT_PARAMS = dict(
    # acoustic path (IF-ACOUSTIC-PORT stub): list of (f0_hz, q, gain_db) peaks/notches; None = flat
    port_bands=None, port_json=None,
    # mic (D13, datasheet Rev B-1): sensitivity -26 dBFS @ 94 dB SPL, +-1 dB unit spread
    mic_sens_db=0.0, mic_noise_scale=1.0, noise_cal="matched",   # matched | nominal
    # supply path (IF-MIC-VDD-NOISE): scenarios = docs/sim/shared-params.yaml#psrr
    psrr_mode="flat55",            # flat55 (nominal) | pess35 (pessimistic) | rolloff (worst); datasheet gives 55 dBV/FS at 1 kHz only
    ext_ripple_mv=0.0,             # external ripple at the mic VDD pin, mV rms, white 1-100 kHz
    h_mic_ohm=0.1,                 # scalar stub: volts at the mic VDD pin per ampere of bridge supply current (was z_rail_ohm, renamed:
                                   # the provider's z_rail is the BRIDGE rail; the mic transfer is h_ibridge_to_micvdd)
    mic_vdd_json=None,             # path to sim/noise/out/IF-MIC-VDD-NOISE.json: complex h(f) on i_sup + background lines/PSD
    loopback=False,                # feed bridge supply current back to the mic (2nd pass)
    # ADF1 decimation: D1 = CIC5/5 + RSFLT/4 (A3 plan s1.2, recommended); D2 = CIC5/10 + CPU half-band (pipeline.py)
    adf_mode="D1",
    # DSP (spec s5): algorithm and knobs
    algo="B", transient_only=True, volume_db=0.0, ceiling_dbfs=-12.0,
    # output shaper (D6)
    pwm_levels=201, interp="ideal", squelch_dbfs=-68.0, squelch_reset=True, shaper_order=3,
    # bridge (D6, C3 s5; PMCXB290UE unmodelled: DMC2400UV stand-in numbers)
    dead_time_ns=12.5, dt_overlap_ns=10.5, vdd=VDD, r_pair=1.22, r_wire=0.2, r_shunt=0.1,
    # exciter: nominal from docs/sim/shared-params.yaml#exciter (same as sim/acoustics/bone.py); bl given -> motional RLC derived
    r_exc=_EX["r_e_ohm"]["nom"], l_exc=_EX["l_e_h"]["nom"], f0=_EX["f0_hz"]["nom"], qm=_EX["q_m"]["nom"],
    bl=_EX["bl_n_per_a"]["nom"], m_eff=_EX["m_m_kg"]["nom"], rm_pk=None,   # rm_pk (old stub) used only if bl is None
    mech="flat",                   # flat | blocked_housing  (IF-BONE-TF stub)
    # perceptual proxy (thresholds: docs/sim/shared-params.yaml#thresholds)
    tragus_gain_db=20.0, owner_offset_db=0.0, owner_offset_above_hz=8000.0,
    thr_convention="retfl_minus_tragus",   # retfl_minus_tragus (low threshold: conservative for T6) | front_measured
)
PEAK_CORNER = dict(r_exc=_EX["corners"]["peak_current_and_ripple"]["r_e_ohm"], l_exc=_EX["corners"]["peak_current_and_ripple"]["l_e_h"])
# pseudo-stages: assumptions that decide a metric although no stage object carries them (metric deps name them -> WARN)
PSEUDO_STATUS = {"mic_ein": "stub",      # mic ultrasonic noise floor: flat EIN extrapolation (E3)
                 "fet_model": "stub",    # bridge FETs: DMC2400UV stand-in, PMCXB290UE unmodelled (sub-output issue 7)
                 "psrr": "stub"}         # mic PSRR above 1 kHz unspecified (shared-params#psrr)


class Stage:
    id = "?"
    status = "stub"
    in_unit = out_unit = "?"

    def process(self, s: Sig, ctx: Ctx) -> Sig:  # pragma: no cover
        raise NotImplementedError


# ------------------------------------------------------------------------------------------------
# helpers
def _fir_from_db(f_hz, gain_db, fs, taps=511):
    """Linear-phase FIR from a magnitude curve (dB) given on f_hz (Hz), 0..fs/2."""
    f, g = np.asarray(f_hz, float), np.asarray(gain_db, float)
    if f[0] > 0:
        f, g = np.concatenate([[0.0], f]), np.concatenate([[g[0]], g])
    if f[-1] < fs / 2:
        f, g = np.concatenate([f, [fs / 2]]), np.concatenate([g, [g[-1]]])
    return signal.firwin2(taps, f, 10 ** (g / 20), fs=fs)


def _apply_fir(x, h):
    return signal.fftconvolve(x, h, mode="same")


# ------------------------------------------------------------------------------------------------
class AcousticPort(Stage):
    """Free-field pressure at the lid -> pressure at the MEMS diaphragm.  STUB (flat) until the
    acoustics sim delivers IF-ACOUSTIC-PORT. Peaks stand in for the duct/lid/mesh resonances
    (spec D13 L232: the 25 kHz +14.7 dB fixture peak will be reshaped; R14)."""
    id, in_unit, out_unit = "acoustic_path", "Pa @400k", "Pa @400k"

    def __init__(self):
        self.status = "stub"

    def curve_db(self, f, p):
        g = np.zeros_like(f)
        if p.get("port_json"):
            d = __import__("json").loads(Path(p["port_json"]).read_text())
            self.status = "model"
            return np.interp(f, d["f_hz"], d["mag_db"])
        for f0, q, gdb in (p.get("port_bands") or []):
            g += gdb / (1 + (q * (f / f0 - f0 / np.maximum(f, 1))) ** 2)
        return g

    def process(self, s, ctx):
        f = np.linspace(100, FS_AC / 2, 800)
        g = self.curve_db(f, ctx.p)
        if not np.any(g):
            return Sig(s.x.copy(), s.fs, "Pa", s.meta)
        return Sig(_apply_fir(s.x, _fir_from_db(f, g, FS_AC)), s.fs, "Pa", s.meta)


class Microphone(Stage):
    """SPH0641LU4H-1 ultrasonic mode: sensitivity, datasheet response, flat-EIN self-noise (existing
    pipeline.microphone). Ultrasonic noise floor is UNKNOWN (E3); the flat-EIN assumption stands."""
    id, in_unit, out_unit, status = "mic", "Pa @400k", "FS-peak @400k", "model"

    def process(self, s, ctx):
        gain = 10 ** (ctx.p["mic_sens_db"] / 20)
        x = pl.microphone(s.x * gain, seed=int(ctx.rng.integers(1 << 30)), noise_scale=ctx.p["mic_noise_scale"])
        return Sig(x, FS_AC, "FS", dict(s.meta))


class SupplyInject(Stage):
    """Adds supply-borne noise at the mic through its PSRR. INTERFACE IF-MIC-VDD-NOISE from the
    layout-noise sim (volts at the VDD pin vs time). Stub: external white ripple + optional loopback
    of the bridge supply current through z_rail. PSRR above 1 kHz is not in the datasheet (55 dBV/FS
    @1 kHz only): flat55 is optimistic, rolloff is -20 dB/dec from 1 kHz (pessimistic guess)."""
    id, in_unit, out_unit, status = "supply_inject", "FS @400k + V", "FS @400k", "stub"

    @staticmethod
    def psrr_db(f, mode):
        """Shared scenarios (docs/sim/shared-params.yaml#psrr): flat55 nominal, pess35 pessimistic, rolloff worst."""
        f = np.asarray(f, float)
        if mode == "rolloff":
            return np.maximum(55 - 20 * np.log10(np.maximum(f, 1000) / 1000), 5)
        if mode == "pess35":
            return np.where(f >= 20e3, 35.0, 55.0)
        return np.full_like(f, 55.0)

    @staticmethod
    def load_if(path):
        """IF-MIC-VDD-NOISE (sim/noise/budget.export_if): complex h_ibridge_to_micvdd(f) + background lines/PSD."""
        import json  # noqa: PLC0415
        d = json.loads(Path(path).read_text())
        f = np.asarray(d["f_hz"], float)
        h = np.asarray(d["h_ibridge_to_micvdd_ohm"]["re"]) + 1j * np.asarray(d["h_ibridge_to_micvdd_ohm"]["im"])
        return d, f, h

    @staticmethod
    def background_v(d, n, fs, rng):
        """Time series (V at the mic VDD pin) of the provider's background lines (random phase) + noise PSD."""
        t = np.arange(n) / fs
        v = np.zeros(n)
        for ln in d.get("background_lines_1k_100k", []):
            v += np.sqrt(2) * ln["v_rms"] * np.sin(2 * np.pi * ln["f_hz"] * t + rng.uniform(0, 2 * np.pi))
        for bn in d.get("background_noise", []):
            fb, psd = np.asarray(bn["f_hz"]), np.asarray(bn["psd_v2_per_hz"])
            W = np.fft.rfft(rng.standard_normal(n))
            ff = np.fft.rfftfreq(n, 1 / fs)
            amp = np.sqrt(np.interp(ff, fb, psd, left=0.0, right=0.0) * fs / 2)   # one-sided PSD -> white-normalised shaping
            v += np.fft.irfft(W * amp, n) / np.sqrt(1.0)
        return v

    def process(self, s, ctx):
        n = len(s.x)
        v = np.zeros(n)
        if ctx.p.get("mic_vdd_json"):
            d, _, _ = self.load_if(ctx.p["mic_vdd_json"])
            v += self.background_v(d, n, FS_AC, ctx.rng)
            self.status = "model"
        if ctx.p["ext_ripple_mv"] > 0:
            w = ctx.rng.standard_normal(n)
            sos = signal.butter(4, [1e3, 100e3], "bp", fs=FS_AC, output="sos")
            w = signal.sosfilt(sos, w)
            v += w / np.std(w) * ctx.p["ext_ripple_mv"] * 1e-3
        if ctx.inject is not None:
            m = min(n, len(ctx.inject.x))
            v[:m] += ctx.inject.x[:m]
        ctx.side["mic_vdd_noise_v_rms"] = float(np.std(v))
        if not np.any(v):
            return Sig(s.x, s.fs, "FS", s.meta)
        f = np.linspace(100, FS_AC / 2, 400)
        h = _fir_from_db(f, -self.psrr_db(f, ctx.p["psrr_mode"]), FS_AC, taps=255)
        inj = _apply_fir(v, h)
        ctx.side["mic_inj_fs_rms"] = float(np.std(inj))
        return Sig(s.x + inj, s.fs, "FS", s.meta)


# ---- ADF1 decimation ------------------------------------------------------------------------
def cic5_db(f, fs_in=FS_CLK_MIC, r=5):
    """CIC (sinc^5) magnitude for decimation r at input rate fs_in (exact formula)."""
    f = np.asarray(f, float)
    num = np.sin(np.pi * f * r / fs_in)
    den = r * np.sin(np.pi * f / fs_in)
    with np.errstate(divide="ignore", invalid="ignore"):
        h = np.where(np.abs(den) < 1e-12, 1.0, num / den)
    return 5 * 20 * np.log10(np.maximum(np.abs(h), 1e-12))


def rsflt_stub_db(f, edge=88.8e3, stop=120e3, stop_db=-70.0):
    """RSFLT reshape filter: coefficients unpublished (A3 plan s1.2, R18). STUB: flat to the 0.111*Fs
    edge, raised-cosine to -70 dB at 120 kHz (A3: ~-70 dB above ~120 kHz); passband ripple not modelled."""
    f = np.asarray(f, float)
    t = np.clip((f - edge) / (stop - edge), 0, 1)
    return stop_db * 0.5 * (1 - np.cos(np.pi * t))


class AdfDecimator(Stage):
    """400 kS/s analog -> 200 kS/s PCM. D2 = repo pipeline half-band (real). D1 = CIC5 droop x RSFLT stub
    (the plan of record, spec D14 L258): magnitude-only FIR at 400 kS/s then /2."""
    id, in_unit, out_unit = "adf", "FS @400k", "FS @200k"

    def __init__(self, mode="D1"):
        self.mode = mode
        self.status = "real" if mode == "D2" else "stub"

    def process(self, s, ctx):
        mode = ctx.p.get("adf_mode", self.mode)
        self.status = "real" if mode == "D2" else "stub"
        if mode == "D2":
            return Sig(pl.decimate_to_fs(s.x), FS_PCM, "FS", s.meta)
        f = np.linspace(0, FS_AC / 2, 1024)
        g = cic5_db(f) + rsflt_stub_db(f)
        y = _apply_fir(s.x, _fir_from_db(f[1:], g[1:], FS_AC, taps=255))
        return Sig(y[::2], FS_PCM, "FS", s.meta)


def pdm_bitstream_selftest(f_tone=40e3, dbfs=-26.0, dur=0.02, order=2):
    """Validation of the ADF1 CIC5 model with a true 1-bit sigma-delta at 4 MHz (python loop, <= 50 ms).
    Returns dict(tone_db_bitstream, tone_db_model, err_db). Modulator = 2nd-order CIFB; the real mic's
    modulator order/NTF is unpublished, so only the tone gain is compared (not the noise floor)."""
    fs_b = 4_000_000
    n = int(dur * fs_b)
    t = np.arange(n) / fs_b
    amp = 10 ** (dbfs / 20)
    x = amp * np.sin(2 * np.pi * f_tone * t)
    i1 = i2 = 0.0
    y = 1.0
    bits = np.empty(n)
    xl = x.tolist()
    for k in range(n):
        i1 += 0.5 * (xl[k] - y)
        i2 += 0.5 * (i1 - y)
        y = 1.0 if i2 >= 0 else -1.0
        bits[k] = y
    # CIC5 /5 -> 800 kS/s : 5 cascaded boxcars (exact sinc^5), then /4 via FIR magnitude (RSFLT stub)
    box = np.ones(5)
    h = box
    for _ in range(4):
        h = np.convolve(h, box)
    c = signal.fftconvolve(bits, h / h.sum(), mode="same")[::5]          # 800 kS/s
    f = np.linspace(0, 400e3, 1024)
    d = _apply_fir(c, _fir_from_db(f[1:], rsflt_stub_db(f[1:]), 800e3, taps=255))[::4]  # 200 kS/s
    d = d[100:-100]
    n2 = len(d)
    w = np.hanning(n2)
    spec = np.abs(np.fft.rfft(d * w)) * 2 / w.sum()
    fr = np.fft.rfftfreq(n2, 1 / 200e3)
    tone = 20 * np.log10(spec[np.argmin(np.abs(fr - f_tone))] + 1e-20)
    model = dbfs + float(cic5_db(f_tone)) + float(rsflt_stub_db(f_tone))
    return dict(tone_db_bitstream=float(tone), tone_db_model=float(model), err_db=float(tone - model))


# ---- DSP (spec s5): wraps the existing pipeline ------------------------------------------------
class DspStage(Stage):
    """200 kS/s PCM -> 12.5 kS/s output signal (1.0 = full-scale duty). status 'real': pipeline.algo_b / algo_a.
    FIRMWARE-IN-THE-LOOP INTERFACE (replace this class, same id 'dsp'):
        in : int32[128] ADF1 samples per hop (24-bit left-aligned in DR[31:8]), 200.02 kS/s, 0.64 ms/hop
        out: uint16[128] TIM1 CCR values (0..200) per hop, one per 5 us PWM period
    The existing model is batch float64; it fixes the numerical reference the firmware is compared to."""
    id, in_unit, out_unit, status = "dsp", "FS @200k", "duty-FS @12.5k", "real"
    _noise_cache: dict = {}

    def process(self, s, ctx):
        p = ctx.p
        cfg = pl.BConfig(transient_only=p["transient_only"], ceiling_dbfs=p["ceiling_dbfs"],
                         gain_db=30.0 + p["volume_db"])
        # per-unit noise calibration (pipeline.calibrate_noise: 'the firmware stores this at production test').
        # matched = calibrated on this unit's own noise; nominal = calibrated on the nominal EIN, then the unit's noise differs.
        ns = p["mic_noise_scale"] if p.get("noise_cal", "matched") == "matched" else 1.0
        key = (cfg.n_bands, cfg.nfft, round(ns, 4))
        if key not in self._noise_cache:
            x = pl.decimate_to_fs(pl.microphone(np.zeros(int(0.5 * FS_AC)), seed=99, noise_scale=ns))
            c = pl.BConfig(**{**cfg.__dict__, "transient_only": False, "noise_band": None})
            self._noise_cache[key] = pl.algo_b(x, c)[1]["band_energy"].mean(axis=0)
        cfg.noise_band = self._noise_cache[key]
        if p["algo"] == "A":
            y = pl.algo_a(s.x, gain_db=30.0 + p["volume_db"], ceiling_dbfs=p["ceiling_dbfs"])
            info = {}
        else:
            y, info = pl.algo_b(s.x, cfg)
        ctx.side["dsp_info"] = info
        ctx.side["dsp_latency_sim_s"] = 0.0
        return Sig(y, FS_DSP, "duty", dict(s.meta, algo=p["algo"]))


# ---- output shaper ---------------------------------------------------------------------------
class PwmShaper(Stage):
    """x16 interpolation + 3rd-order error-feedback shaper (DC zero + pair at 13 kHz) + TPDF dither,
    201 levels (D6 L155-178). Squelch forces exact zero and dither off (D6 L178: silence is an exact
    50 % square wave). The interpolator filter and the squelch threshold are NOT in the spec: knobs."""
    id, in_unit, out_unit, status = "shaper", "duty @12.5k", "duty-quantised @200k", "model"

    def process(self, s, ctx):
        p = ctx.p
        y = s.x
        if p["interp"] == "linear":
            n = len(y) * 16
            x = np.interp(np.arange(n) / 16.0, np.arange(len(y)), y)
        elif p["interp"] == "zoh":
            x = np.repeat(y, 16)
        else:
            x = signal.resample_poly(y, 16, 1, window=("kaiser", 9.0))
        # squelch: 5 ms rms below threshold for 20 ms -> hard zero, dither off
        w = int(0.005 * FS_DSP)
        env = np.sqrt(np.convolve(y ** 2, np.ones(w) / w, "same"))
        quiet = (env < 10 ** (p["squelch_dbfs"] / 20)).astype(float)
        hold = np.convolve(quiet, np.ones(int(0.02 * FS_DSP)) / int(0.02 * FS_DSP), "same") >= 0.999
        mask = np.repeat(hold, 16)[: len(x)]
        x = np.where(mask, 0.0, x)
        ctx.side["squelched_frac"] = float(mask.mean())
        ctx.side["x_interp_peak"] = float(np.max(np.abs(x)))     # true peak after x16 interpolation (pre-quantiser)
        ctx.side["x_sample_peak"] = float(np.max(np.abs(y)))
        n = len(x)
        step = 2.0 / (p["pwm_levels"] - 1)
        if p["shaper_order"] == 3:
            wz = 2 * np.pi * 13e3 / FS_PWM
            ntf = np.convolve([1, -1], [1, -2 * np.cos(wz), 1])
        else:
            ntf = np.array([1.0, -2.0, 1.0])
        h = list(ntf[1:]) + [0.0] * (3 - len(ntf[1:]))
        h1, h2, h3 = h
        r = ctx.rng.random((2, n))
        dith = ((r[0] - r[1]) * step * (~mask)).tolist()
        xl = x.tolist()
        ml = mask.tolist()
        reset = bool(p.get("squelch_reset", True))
        out = np.empty(n)
        e1 = e2 = e3 = 0.0
        floor = np.floor
        for i in range(n):
            if reset and ml[i]:           # firmware zeroes the shaper state while squelched; without it the
                e1 = e2 = e3 = 0.0        # 3rd-order loop keeps a limit cycle alive at zero input (see yaml, R21)
            v = xl[i] + h1 * e1 + h2 * e2 + h3 * e3
            q = floor((v + dith[i]) / step + 0.5) * step
            if q > 1.0:
                q = 1.0
            elif q < -1.0:
                q = -1.0
            e3, e2, e1 = e2, e1, q - v
            out[i] = q
        ctx.side["ccr_stream_peak"] = float(np.max(np.abs(out))) if n else 0.0   # |2*CCR/ARR-1| peak (FWSIM-R15 CCR bound)
        return Sig(out, FS_PWM, "duty", dict(s.meta, levels=p["pwm_levels"]))


# ---- bridge + exciter ---------------------------------------------------------------------------
class Exciter(Stage):
    """Electrical model of the exciter plus loop resistance: series R_tot, L, and the motional branch
    (parallel RLC from f0, Qm, Rm_pk, m_eff). V (volts) -> coil current (A).  Parameters are placeholders
    until E1 (LCR) and the |Z| sweep (F4): status 'stub'. Bl derived from Rm_pk, f0, Qm, m_eff."""
    id, in_unit, out_unit, status = "exciter", "V @200k", "A @200k", "stub"

    def derive(self, p):
        """Motional parallel RLC from (bl, m, f0, Qm): c = m w0/Q, k = m w0^2, Rm = Bl^2/c, Lm = Bl^2/k, Cm = m/Bl^2.
        Old stub path (bl None): Bl from rm_pk."""
        m, w0 = p["m_eff"], 2 * np.pi * p["f0"]
        k, c = m * w0 ** 2, m * w0 / p["qm"]
        if p.get("bl") is not None:
            bl = float(p["bl"])
            rm = bl ** 2 / c
        else:
            rm = p["rm_pk"]
            bl = np.sqrt(rm * c)
        return dict(k=k, c=c, bl=bl, rm=rm, cm=m / bl ** 2, lm=bl ** 2 / k)

    def r_total(self, p):
        return p["r_exc"] + p["r_pair"] + p["r_wire"] + p["r_shunt"]

    def sos(self, p):
        d = self.derive(p)
        rm, lm, cm = d["rm"], d["lm"], d["cm"]
        nm, dm = np.array([lm * rm, 0.0]), np.array([lm * rm * cm, lm, rm])
        nz = np.polyadd(np.polymul([p["l_exc"], self.r_total(p)], dm), nm)
        z, pl_, kk = signal.tf2zpk(dm, nz)
        zd, pd, kd = signal.bilinear_zpk(z, pl_, kk, FS_PWM)
        return signal.zpk2sos(zd, pd, kd)

    def current(self, v, p):
        return signal.sosfilt(self.sos(p), v)

    def process(self, s, ctx):
        i = self.current(s.x, ctx.p)
        return Sig(i, FS_PWM, "A", s.meta)

    def zmag(self, f, p):
        d = self.derive(p)
        s_ = 2j * np.pi * np.asarray(f)
        zm = 1 / (1 / d["rm"] + 1 / (s_ * d["lm"]) + s_ * d["cm"])
        return np.abs(self.r_total(p) + s_ * p["l_exc"] + zm)


class Bridge(Stage):
    """Discrete H-bridge, AD modulation, behavioural switch-level (averaged per PWM period).
    V = Vdd*duty + dead-time error. Error = -Vdd*4*td_eff*f_pwm*g(i), g = clip(i/I_ripple_pk, -1, 1):
    the 2-level edges cancel while |i| < I_ripple_pk = Vdd/(4 L f) (D6 L167-168), saturate above it.
    td_eff = max(td - t_overlap, 0): t_overlap (10.5 ns) calibrates the model to the DMC2400UV SPICE
    result THD+N -52 dB at -12 dBFS, 12.5 ns. Validated 2026-10-02 (chain.py --scenario spice): -51.0 vs -51.9 dB at
    12.5 ns; pessimistic by 3.6 dB at 25 and 37.5 ns; no dead-time term at -40 dBFS (SPICE -61/-48/-44 dB), so valid at
    the 12.5 ns design point only. PMCXB290UE is NOT modelled: E7 / the Nexperia SPICE model close that. status 'model'."""
    id, in_unit, out_unit, status = "bridge", "duty @200k", "V @200k", "model"
    SHOOT_MA = {12.5: 0.32, 25.0: 0.0, 37.5: 0.0}     # C3 s5 idle bus 0.49 vs ripple-only 0.17 mA
    GATE_MA, PULL_MA = 0.28, 0.06                      # SPICE gate drive; power.py gate pulls

    def __init__(self, exciter: Exciter):
        self.exc = exciter

    def process(self, s, ctx):
        p = ctx.p
        vdd = p["vdd"]
        v0 = vdd * s.x
        i0 = self.exc.current(v0, p)
        ripple_pk = vdd / (4 * p["l_exc"] * FS_PWM)
        g = np.clip(i0 / ripple_pk, -1, 1)
        td_eff = max(p["dead_time_ns"] - p["dt_overlap_ns"], 0.0) * 1e-9
        v = v0 - vdd * 4 * td_eff * FS_PWM * g
        # supply current and bridge average draw (used by S-pwr and the rail-noise loopback)
        i = self.exc.current(v, p)
        i_sup = i * (v / vdd)
        r_tot = self.exc.r_total(p)
        i_rip_rms = ripple_pk / np.sqrt(3)
        shoot = self.SHOOT_MA.get(round(p["dead_time_ns"], 1), 0.0) * 1e-3
        ctx.side.update(i_ripple_pk=float(ripple_pk),
                        i_sup=Sig(i_sup, FS_PWM, "A"),
                        i_sup_avg_ma=float((np.mean(i_sup) + i_rip_rms ** 2 * r_tot / vdd + shoot) * 1e3
                                           + self.GATE_MA + self.PULL_MA),
                        bridge_peak_a=float(np.max(np.abs(i))),
                        coil_i=Sig(i, FS_PWM, "A"))
        return Sig(v, FS_PWM, "V", s.meta)


class MechBone(Stage):
    """Coil current -> force on the skin (N): F = Bl*i*H(f). H = 1 ('flat') is a STUB: the pad/skin/
    cartilage coupling is INTERFACE IF-BONE-TF from the acoustics sim (E2 measures loudness at the
    tragus). 'blocked_housing' adds the mass-spring high-pass (k + c s)/(m s^2 + c s + k)."""
    id, in_unit, out_unit, status = "mech_bone", "A @200k", "N @200k", "stub"

    def process(self, s, ctx):
        p = ctx.p
        d = Exciter().derive(p)
        f = d["bl"] * s.x
        if p["mech"] == "blocked_housing":
            m = p["m_eff"]
            b, a = [d["c"], d["k"]], [m, d["c"], d["k"]]
            bd, ad = signal.bilinear(b, a, FS_PWM)
            f = signal.lfilter(bd, ad, f)
        ctx.side["bl_n_per_a"] = float(d["bl"])
        return Sig(f, FS_PWM, "N", s.meta)


# ---- firmware-in-the-loop ABI ------------------------------------------------------------------------
def pcm_to_adf_words(x_fs):
    """Float PCM (1.0 = full scale) -> ADF1 DR words: 24-bit signed, left-aligned in DR[31:8] (A3 plan s1.1)."""
    q = np.round(np.clip(np.asarray(x_fs, float), -1.0, 1.0 - 2.0 ** -23) * 2 ** 23).astype(np.int64)
    return (q << 8).astype(np.int32)


def adf_words_to_pcm(w):
    return (np.asarray(w, np.int64) >> 8) / 2.0 ** 23


def ccr_to_duty(ccr, arr=200):
    """TIM1 CCR (0..ARR) -> differential duty in [-1, 1]. Convention: CCR/ARR = leg A high fraction, leg B is the
    complement (AD, D6 L166), so V_diff/Vdd = 2*CCR/ARR - 1."""
    return 2.0 * np.asarray(ccr, float) / arr - 1.0


class FirmwareDspShaperStage(Stage):
    """Drop-in for BOTH 'dsp' and 'shaper' (in firmware they are one unit: algorithm -> x16 interpolate ->
    shaper -> TIM1 CCR, spec s5 + D6). hop_fn(int32[128]) -> uint16[128]: one 0.64 ms hop in, 128 CCR values out
    (one per 5 us PWM period). Wire a host build (gcc -shared + ctypes) or an emulator behind hop_fn.
    Scenarios that read taps['dsp'] / ctx.side['x_interp_peak'] need the firmware to export them (TODO)."""
    id, in_unit, out_unit, status = "fw_dsp_shaper", "FS @200k", "duty @200k", "real"

    def __init__(self, hop_fn, hop=128):
        self.hop_fn, self.hop = hop_fn, hop

    def process(self, s, ctx):
        w = pcm_to_adf_words(s.x)
        n = len(w) // self.hop
        ccr = np.concatenate([np.asarray(self.hop_fn(w[i * self.hop:(i + 1) * self.hop]), np.uint16) for i in range(n)])
        return Sig(ccr_to_duty(ccr), FS_PWM, "duty", dict(s.meta, fw=True))


def default_chain(fw: "FirmwareDspShaperStage | None" = None):
    exc = Exciter()
    ch = [AcousticPort(), Microphone(), SupplyInject(), AdfDecimator(), DspStage(), PwmShaper(),
          Bridge(exc), exc, MechBone()]
    if fw is not None:
        ch[4:6] = [fw]
    return ch
