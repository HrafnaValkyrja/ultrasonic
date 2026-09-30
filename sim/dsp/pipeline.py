"""Phase-1 model of one side's signal chain (spec §5), float64 reference implementation.

mic (pressure -> dBFS, datasheet ultrasonic response, self-noise)
  -> 400 kS/s (stands in for the MDF/DFSDM sinc output) -> half-band /2 -> 200 kS/s
  -> algorithm B: 256-pt FFT analysis (hop 128) -> log bands -> mic EQ -> floor/gate -> oscillator bank @ 12.5 kS/s
  or algorithm A: heterodyne (LO) -> low-pass -> 12.5 kS/s
  -> fixed volume -> soft ceiling -> output (dBFS at the PWM)
plus the idle-listening detector that decides when the full chain may sleep.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy import signal

REPO = Path(__file__).resolve().parents[2]
FS_IN = 400_000
FS = 200_000
FS_OUT = 12_500
P_REF = 20e-6

# ---------------------------------------------------------------- microphone
MIC_SENS_DBFS_AT_94 = -26.0          # SPH0641LU4H-1, 94 dB SPL @ 1 kHz -> -26 dBFS
MIC_EIN_DBSPL_20K = 29.7             # 94 - 64.3 dB(A) SNR, audio band; treated as flat density
_resp = json.loads((REPO / "sim/data/sph0641_ultrasonic_response.json").read_text())
_RF, _RDB = np.array(_resp["f_khz"]) * 1e3, np.array(_resp["db_re_1k"])


def mic_response_db(f):
    """Datasheet ultrasonic response re 1 kHz; below 10 kHz assume 0 dB; above 80 kHz hold."""
    f = np.asarray(f, float)
    return np.where(f < 10e3, np.interp(f, [0, 10e3], [0, _RDB[0]]), np.interp(f, _RF, _RDB))


def microphone(p_pa, seed=0, noise_scale=1.0):
    """Pressure (Pa, at FS_IN) -> digital full-scale units (1.0 = 0 dBFS sine peak ~ 0 dBFS rms*sqrt2)."""
    n = len(p_pa)
    fsc = 10 ** (MIC_SENS_DBFS_AT_94 / 20) / (P_REF * 10 ** (94 / 20))   # dBFS-rms per Pa-rms
    # frequency response as a linear-phase FIR
    taps = 255
    f = np.linspace(0, FS_IN / 2, 513)
    h = signal.firwin2(taps, f, 10 ** (mic_response_db(f) / 20), fs=FS_IN)
    x = signal.fftconvolve(p_pa, h, mode="same") * fsc
    # self-noise: EIN density spread flat to 100 kHz (ultrasonic self-noise unknown; E3 measures it)
    rng = np.random.default_rng(seed)
    ein_rms = P_REF * 10 ** (MIC_EIN_DBSPL_20K / 20) * np.sqrt(100e3 / 20e3) * noise_scale
    noise = rng.standard_normal(n) * ein_rms * fsc * np.sqrt(FS_IN / 2 / 100e3)
    return np.sqrt(2) * (x + noise)          # rms -> peak scaling: a 0 dBFS sine has peak 1.0


def decimate_to_fs(x):
    """400 -> 200 kS/s: 31-tap half-band (passband to 80 kHz)."""
    h = signal.remez(31, [0, 80e3, 120e3, FS_IN / 2], [1, 0], fs=FS_IN)
    return signal.fftconvolve(x, h, mode="same")[::2]


# ---------------------------------------------------------------- algorithm B
@dataclass
class BConfig:
    nfft: int = 256
    hop: int = 128
    f_lo: float = 20e3          # band floor (D10 sets this from the owner's hearing test)
    f_hi: float = 85e3
    n_bands: int = 28
    out_lo: float = 1500.0
    out_hi: float = 4000.0
    floor_up_s: float = 3.0     # floor rises slowly (steady tones become "floor")
    floor_down_s: float = 0.3   # and falls fast
    gate_db: float = 6.0        # transient mode: only energy this far above the floor passes
    transient_only: bool = True
    gain_db: float = 30.0       # fixed volume (D3): ~70 dB SPL bat -> ~-23 dBFS; volume steps are +-4 dB
    ceiling_dbfs: float = -12.0 # output soft ceiling (D17)
    eq: bool = True
    attack_ms: float = 1.5      # per-band envelope: fast enough for 1.5 ms buzz calls, slow enough not to click
    release_ms: float = 15.0
    noise_band: np.ndarray | None = None   # mic self-noise per band (from calibrate_noise); full mode gates on it
    noise_margin_db: float = 6.0


def band_edges(cfg: BConfig):
    return np.geomspace(cfg.f_lo, cfg.f_hi, cfg.n_bands + 1)


def map_freq(f, cfg: BConfig):
    """Log compression: 20-85 kHz -> 1.5-4 kHz, octaves keep their share."""
    u = np.log(np.clip(f, cfg.f_lo, cfg.f_hi) / cfg.f_lo) / np.log(cfg.f_hi / cfg.f_lo)
    return cfg.out_lo * (cfg.out_hi / cfg.out_lo) ** u


def algo_b(x, cfg: BConfig = BConfig()):
    """x at FS (200 kS/s, dBFS peak units). Returns (y at FS_OUT, info)."""
    win = np.hanning(cfg.nfft)
    wsum = win.sum()
    freqs = np.fft.rfftfreq(cfg.nfft, 1 / FS)
    edges = band_edges(cfg)
    band_of_bin = np.digitize(freqs, edges) - 1
    valid = (band_of_bin >= 0) & (band_of_bin < cfg.n_bands)
    eqg = 10 ** (-mic_response_db(freqs) / 20) if cfg.eq else np.ones_like(freqs)
    n_hops = (len(x) - cfg.nfft) // cfg.hop
    out_per_hop = cfg.hop * FS_OUT // FS            # 8 output samples per 0.64 ms hop
    hop_s = cfg.hop / FS
    a_up = np.exp(-hop_s / cfg.floor_up_s)
    a_dn = np.exp(-hop_s / cfg.floor_down_s)
    floor = None                                     # initialised from the first frame (power-on)
    a_att = 1 - np.exp(-hop_s / (cfg.attack_ms * 1e-3))
    a_rel = 1 - np.exp(-hop_s / (cfg.release_ms * 1e-3))
    env = np.zeros(cfg.n_bands)
    amp_prev = np.zeros(cfg.n_bands)
    f_prev = map_freq(np.sqrt(edges[:-1] * edges[1:]), cfg)
    phase = np.zeros(cfg.n_bands)
    y = np.zeros(n_hops * out_per_hop)
    band_energy_log = np.zeros((n_hops, cfg.n_bands))
    for h in range(n_hops):
        seg = x[h * cfg.hop: h * cfg.hop + cfg.nfft] * win
        mag = np.abs(np.fft.rfft(seg)) * 2 / wsum * eqg          # peak amplitude per bin
        p = mag ** 2
        e = np.bincount(band_of_bin[valid], weights=p[valid], minlength=cfg.n_bands)
        fc = np.bincount(band_of_bin[valid], weights=(p * freqs)[valid], minlength=cfg.n_bands)
        centroid = np.where(e > 0, fc / np.maximum(e, 1e-30), np.sqrt(edges[:-1] * edges[1:]))
        # asymmetric floor tracker: slow up, fast down
        if floor is None:
            floor = e.copy()
        floor = np.where(e > floor, a_up * floor + (1 - a_up) * e, a_dn * floor + (1 - a_dn) * e)
        if cfg.transient_only:
            thr = floor * 10 ** (cfg.gate_db / 10)
            if cfg.noise_band is not None:      # never open on the mic's own hiss fluctuations
                thr = np.maximum(thr, cfg.noise_band * 10 ** (cfg.noise_margin_db / 10))
            e_out = np.clip(e - thr, 0, None)
        else:
            # full mode: steady tones pass; only the mic's own hiss (calibrated per band) is removed
            nb = cfg.noise_band if cfg.noise_band is not None else np.zeros(cfg.n_bands)
            e_out = np.clip(e - nb * 10 ** (cfg.noise_margin_db / 10), 0, None)
        target = np.sqrt(e_out) * 10 ** (cfg.gain_db / 20)
        env += np.where(target > env, a_att, a_rel) * (target - env)
        amp = env.copy()
        band_energy_log[h] = e
        f_new = map_freq(centroid, cfg)
        # synthesis: amplitude and frequency ramp across the hop, phase-continuous per band
        k = np.arange(1, out_per_hop + 1) / out_per_hop
        A = amp_prev[None, :] + (amp - amp_prev)[None, :] * k[:, None]
        F = f_prev[None, :] + (f_new - f_prev)[None, :] * k[:, None]
        ph = phase[None, :] + 2 * np.pi * np.cumsum(F, axis=0) / FS_OUT
        y[h * out_per_hop:(h + 1) * out_per_hop] = np.sum(A * np.sin(ph), axis=1)
        phase = ph[-1] % (2 * np.pi)
        amp_prev, f_prev = amp, f_new
    return limiter(y, FS_OUT, cfg.ceiling_dbfs), {"band_energy": band_energy_log, "edges": edges}


def calibrate_noise(cfg: BConfig, seconds=0.5, seed=99):
    """Mean band energy of the mic's self-noise alone (the firmware stores this at production test)."""
    x = decimate_to_fs(microphone(np.zeros(int(seconds * FS_IN)), seed=seed))
    c = BConfig(**{**cfg.__dict__, "transient_only": False, "noise_band": None})
    _, info = algo_b(x, c)
    return info["band_energy"].mean(axis=0)


# ---------------------------------------------------------------- algorithm A (fallback)
def algo_a(x, f_lo=38e3, bw=3000.0, out_center=2750.0, gate_db=6.0, ceiling_dbfs=-12.0, gain_db=30.0):
    """Heterodyne: shift [f_lo+out_center-bw/2, ...] down so f_lo+out_center -> out_center."""
    t = np.arange(len(x)) / FS
    lo = np.cos(2 * np.pi * f_lo * t)
    mixed = x * lo * 2
    b = signal.firwin(255, out_center + bw / 2, fs=FS)
    base = signal.fftconvolve(mixed, b, mode="same")
    hp = signal.butter(2, max(out_center - bw / 2, 300), "hp", fs=FS, output="sos")
    base = signal.sosfilt(hp, base)
    y = signal.resample_poly(base, 1, 16)
    # envelope squelch with a slow floor
    env = np.abs(signal.hilbert(y))
    sm = signal.lfilter([0.02], [1, -0.98], env)
    floor = np.minimum.accumulate(np.maximum(sm, 1e-9)) * 0 + np.percentile(sm, 20)
    g = np.clip((sm - floor * 10 ** (gate_db / 20)) / np.maximum(sm, 1e-12), 0, 1)
    return limiter(y * g * 10 ** (gain_db / 20), FS_OUT, ceiling_dbfs)


# ---------------------------------------------------------------- idle detector
def idle_detector(x, n_bands=4, block=128, up_s=3.0, down_s=0.3, thresh_db=8.0, hang_s=0.3):
    """Cheap wake detector for the idle-listening mode (C9).

    Four one-pole band energies (20-30, 30-45, 45-65, 65-85 kHz) on the 200 kS/s stream, each
    with the same slow floor tracker as algorithm B; 'active' when any band exceeds its floor by
    thresh_db, held for hang_s. Returns boolean per block and the active fraction.
    """
    edges = [20e3, 30e3, 45e3, 65e3, 85e3]
    energies = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        sos = signal.butter(2, [lo, hi], "bp", fs=FS, output="sos")
        yb = signal.sosfilt(sos, x)
        nb = len(yb) // block
        energies.append(np.mean(yb[:nb * block].reshape(nb, block) ** 2, axis=1))
    E = np.array(energies).T
    hop_s = block / FS
    a_up, a_dn = np.exp(-hop_s / up_s), np.exp(-hop_s / down_s)
    floor = E[0].copy()
    active = np.zeros(len(E), bool)
    hang = 0
    for i, e in enumerate(E):
        floor = np.where(e > floor, a_up * floor + (1 - a_up) * e, a_dn * floor + (1 - a_dn) * e)
        hit = np.any(e > floor * 10 ** (thresh_db / 10))
        hang = int(hang_s / hop_s) if hit else max(hang - 1, 0)
        active[i] = hang > 0
    return active, active.mean()


def limiter(y, fs, ceiling_dbfs, attack_ms=0.5, release_ms=60.0):
    """Output ceiling (D17) as a gain limiter: turns the gain down smoothly instead of squaring
    off the waveform (which would splatter clicks across the whole band). tanh stays as a backstop
    3 dB above the ceiling for the few samples the 0.5 ms attack lets through."""
    c = 10 ** (ceiling_dbfs / 20)
    need = np.minimum(1.0, c / np.maximum(np.abs(y), 1e-12))
    a_a, a_r = 1 - np.exp(-1 / (fs * attack_ms * 1e-3)), 1 - np.exp(-1 / (fs * release_ms * 1e-3))
    g = np.empty_like(y)
    gi = 1.0
    for i, n in enumerate(need):
        gi += (a_a if n < gi else a_r) * (n - gi)
        g[i] = gi
    return soft_ceiling(y * g, ceiling_dbfs + 3)


def idle_detector_fft(x, hop_ms=5.0, nfft=256, f_lo=20e3, f_hi=85e3, n_bands=4, up_s=3.0,
                      down_s=0.3, thresh_db=15.0, hang_s=0.3, peak_db=10.0, bin_up_s=3.0, bin_down_s=1.0,
                      smooth_bins=1):
    """Idle-listening wake detector, rev 2 (after audit dsp-1/dsp-8).

    Instead of four IIR band filters running on every sample (~10 Mcycle/s, and their 2nd-order
    skirts let audible speech wake the chain), take one 256-point Hann-windowed FFT snapshot every
    hop_ms and sum band energies from its bins, reusing algorithm B's FFT. Hann leakage from speech
    at <= 6 kHz into bins >= 20 kHz is about -90 dB, so speech no longer wakes it.
    Cost at 5 ms: 200 FFTs/s x ~17 kcycles = ~3.4 Mcycle/s, fits a 16 MHz idle clock.
    Limit: with 1.28 ms snapshots every 5 ms, a single call shorter than ~3.7 ms can fall between
    snapshots; bat calls come in trains, and the look-back buffer covers the wake-up.
    Returns (active per hop, active fraction, hop seconds).
    """
    hop = int(round(FS * hop_ms / 1000))
    win = np.hanning(nfft)
    freqs = np.fft.rfftfreq(nfft, 1 / FS)
    edges = np.geomspace(f_lo, f_hi, n_bands + 1)
    idx = np.digitize(freqs, edges) - 1
    ok = (idx >= 0) & (idx < n_bands)
    n = (len(x) - nfft) // hop + 1
    hop_s = hop / FS
    a_up, a_dn = np.exp(-hop_s / up_s), np.exp(-hop_s / down_s)
    floor = None
    band_bins = np.nonzero((freqs >= f_lo) & (freqs < f_hi))[0]
    b_up, b_dn = np.exp(-hop_s / bin_up_s), np.exp(-hop_s / bin_down_s)
    bfloor = None
    active = np.zeros(n, bool)
    hang = 0
    for i in range(n):
        seg = x[i * hop: i * hop + nfft] * win
        p = np.abs(np.fft.rfft(seg)) ** 2
        e = np.bincount(idx[ok], weights=p[ok], minlength=n_bands)
        if floor is None:
            floor = e.copy()
        floor = np.where(e > floor, a_up * floor + (1 - a_up) * e, a_dn * floor + (1 - a_dn) * e)
        if peak_db is None:
            hit = np.any(e > floor * 10 ** (thresh_db / 10))
        else:
            # Narrowband test: bat calls light up a few bins; broadband lifts (speech leakage,
            # rustle, the mic's own noise) raise every bin together. Compare each bin to its own
            # slow floor, then require the best bin to stand out from the band's median bin.
            pb = p[band_bins]
            if smooth_bins > 1:        # average neighbouring bins: tames single-bin chi-square scatter
                pb = np.convolve(pb, np.ones(smooth_bins) / smooth_bins, 'same')
            if bfloor is None:
                bfloor = pb.copy() + 1e-30
            r = pb / bfloor
            bfloor = np.where(pb > bfloor, b_up * bfloor + (1 - b_up) * pb, b_dn * bfloor + (1 - b_dn) * pb)
            hit = (r.max() > 10 ** (thresh_db / 10)) and (r.max() / np.median(r) > 10 ** (peak_db / 10))
        hang = int(hang_s / hop_s) if hit else max(hang - 1, 0)
        active[i] = hang > 0
    return active, active.mean(), hop_s


def soft_ceiling(y, ceiling_dbfs):
    c = 10 ** (ceiling_dbfs / 20)
    return c * np.tanh(y / c)


def dbfs(x):
    return 20 * np.log10(np.sqrt(np.mean(np.square(x))) * np.sqrt(2) + 1e-20)
