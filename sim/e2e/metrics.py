"""Metrics and the perceptual (audibility / loudness) proxy for the end-to-end chain.

Status words: PASS / FAIL (all stages the metric depends on are real or model) and WARN (a stub stage
makes the value not meaningful: the line shows what it would be). Every Metric carries `src` (spec text
or file) and `basis` (spec = number is in the spec; derived = computed from spec numbers; assumed =
no number exists, proposed here and awaiting the owner).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import yaml
from scipy import signal

# ---- perceptual proxy -------------------------------------------------------------------------
# Bone-conduction thresholds, dB re 1 uN (force level), from the ONE shared table docs/sim/shared-params.yaml#thresholds:
#   retfl_mastoid = ANSI S3.6-1996 = ISO 389-3 mastoid via Henry & Letowski ARL-TR-4138 (2007) Table 8 (opened by the
#   acoustics agent 2026-10-02; was 'recalled, unverified' here), held flat at 40 dB above 8 kHz (assumption: Popelka 2010);
#   front_measured = Surendran 2023 frontal-site medians (digitised). Conventions: retfl_minus_tragus (default) | front_measured.
_TH = yaml.safe_load((Path(__file__).resolve().parents[2] / "docs/sim/shared-params.yaml").read_text())["thresholds"]
RETFL_MASTOID = dict(zip(_TH["retfl_mastoid"]["f_hz"], _TH["retfl_mastoid"]["db"]))
RETFL_MASTOID[16000] = _TH["retfl_mastoid"]["db"][-1]
FRONT_MEASURED = dict(zip(_TH["front_measured"]["f_hz"], _TH["front_measured"]["db"]))
FRONT_MEASURED[16000] = _TH["front_measured"]["db"][-1]
THIRD_OCT = np.array([250, 315, 400, 500, 630, 800, 1000, 1250, 1600, 2000, 2500, 3150, 4000, 5000,
                      6300, 8000, 10000, 12500, 16000], float)
FS_FORCE = 200_000


def threshold_db(fc, tragus_gain_db=20.0, owner_offset_db=0.0, owner_offset_above_hz=8000.0, convention="retfl_minus_tragus"):
    """Force-level threshold (dB re 1 uN) at the tragus site for the owner.
    retfl_minus_tragus: mastoid RETFL minus tragus_gain_db (Surendran 2023, bone-conduction.md s3: ~20 dB, 10-40): LOW
    threshold, conservative for silence (T6). front_measured: Surendran 2023 frontal medians, 20-24 dB higher at 1.5-4 kHz.
    owner_offset_db: her measured hearing minus the norm for fc >= owner_offset_above_hz (E5; she hears high)."""
    tab = FRONT_MEASURED if convention == "front_measured" else RETFL_MASTOID
    f = np.array(sorted(tab))
    v = np.array([tab[k] for k in f])
    thr = np.interp(np.log(fc), np.log(f), v) - (0.0 if convention == "front_measured" else tragus_gain_db)
    return thr + np.where(fc >= owner_offset_above_hz, owner_offset_db, 0.0)


def band_levels(force_n, fs=FS_FORCE, nperseg=8192, hop_s=0.02):
    """1/3-octave force levels (dB re 1 uN rms) per time frame: array [frames, bands], times."""
    nov = nperseg - int(hop_s * fs)
    f, t, S = signal.spectrogram(force_n, fs, window="hann", nperseg=nperseg, noverlap=nov, scaling="density",
                                 detrend=False)
    df = f[1] - f[0]
    out = np.full((len(t), len(THIRD_OCT)), -200.0)
    for b, fc in enumerate(THIRD_OCT):
        m = (f >= fc / 2 ** (1 / 6)) & (f < fc * 2 ** (1 / 6))
        p = S[m].sum(axis=0) * df
        out[:, b] = 10 * np.log10(p / 1e-12 + 1e-20)
    return out, t


def sensation_level(force_n, p, fs=FS_FORCE):
    """Sensation level (dB above the owner's threshold) per frame and band, plus loudness proxy (sone-like):
    N = sum_b 2^((SL_b - 40)/10) over bands with SL_b > 0 (Stevens-style doubling per 10 dB; NOT ISO 532)."""
    L, t = band_levels(force_n, fs)
    thr = threshold_db(THIRD_OCT, p["tragus_gain_db"], p["owner_offset_db"], p["owner_offset_above_hz"], p.get("thr_convention", "retfl_minus_tragus"))
    sl = L - thr[None, :]
    n = np.where(sl > 0, 2 ** ((sl - 40) / 10), 0).sum(axis=1)
    return sl, t, n


# ---- generic signal metrics ---------------------------------------------------------------------
def dbfs_rms_peakref(x):
    """pipeline.dbfs convention: 0 dBFS = sine whose PEAK is 1.0."""
    return 20 * np.log10(np.sqrt(np.mean(np.square(x))) * np.sqrt(2) + 1e-20)


def envelope(x, fs, smooth_s=0.001):
    e = np.abs(signal.hilbert(x))
    n = max(1, int(smooth_s * fs))
    return np.convolve(e, np.ones(n) / n, "same")


def band_power_ratio(x, fs, band, total_band=(20.0, None)):
    f, P = signal.welch(x, fs, nperseg=min(len(x), 4096))
    hi = total_band[1] or fs / 2
    tot = P[(f >= total_band[0]) & (f < hi)].sum()
    m = P[(f >= band[0]) & (f < band[1])].sum()
    return float(m / (tot + 1e-30))


def inband_error_db(x, ref, fs, band=(200.0, 16e3)):
    """Distortion + noise of x vs ref in-band, dB re the fitted signal. x is fitted as a*ref + b*H(ref)
    (H = Hilbert transform), so a pure gain or phase change (a linear impedance error) is NOT counted;
    only distortion, noise and images are. Meant for tone tests (like deadtime_switching.inband_thd_n)."""
    n = min(len(x), len(ref))
    s = slice(n // 8, n)
    x, ref = x[:n][s], ref[:n]
    rh = np.imag(signal.hilbert(ref))[s]
    ref = ref[s]
    A = np.vstack([ref, rh]).T
    coef = np.linalg.lstsq(A, x, rcond=None)[0]
    fit = A @ coef
    w = np.hanning(len(x))
    E = np.abs(np.fft.rfft((x - fit) * w)) ** 2
    S = np.abs(np.fft.rfft(fit * w)) ** 2
    f = np.fft.rfftfreq(len(x), 1 / fs)
    b = (f >= band[0]) & (f < band[1])
    return float(10 * np.log10(E[b].sum() / S[b].sum() + 1e-30))


def ild_percept(a_l, a_r, ta_db, n=4000, seed=0):
    """Perceived ILD (dB) at each ear when each ear also hears the other side's exciter at -TA dB with a
    random relative phase (unlinked clocks, D2 L113-115). Returns the array of ILDs over phase draws."""
    rng = np.random.default_rng(seed)
    eps = 10 ** (-ta_db / 20)
    ph1, ph2 = rng.uniform(0, 2 * np.pi, (2, n))
    el = np.abs(a_l + eps * a_r * np.exp(1j * ph1))
    er = np.abs(a_r + eps * a_l * np.exp(1j * ph2))
    return 20 * np.log10(el / er)


# ---- metric record ----------------------------------------------------------------------------
@dataclass
class Metric:
    id: str
    scenario: str
    value: float
    unit: str
    op: str                     # '<=' or '>='
    thr: float
    src: str
    basis: str                  # spec | derived | assumed
    deps: list = field(default_factory=list)   # stage ids this metric's meaning depends on
    note: str = ""

    def ok(self):
        return self.value <= self.thr if self.op == "<=" else self.value >= self.thr

    def status(self, stage_status: dict):
        """WARN: a stub/pseudo-stub decides it. OPEN: fails, but against an ASSUMED threshold (owner to confirm the number).
        FAIL only against a spec or derived threshold with no stub in the way."""
        stubs = [d for d in self.deps if stage_status.get(d) == "stub"]
        if stubs:
            return "WARN", stubs
        if self.ok():
            return "PASS", []
        return ("OPEN" if self.basis == "assumed" else "FAIL"), []

    def line(self, stage_status):
        st, stubs = self.status(stage_status)
        extra = f"  [stub: {','.join(stubs)}; would {'pass' if self.ok() else 'fail'}]" if stubs else ""
        return (f"{st:4s} {self.id:34s} {self.value:9.2f} {self.unit:8s} (need {self.op} {self.thr:g}; {self.basis}; "
                f"{self.src}){extra}")

    def as_dict(self, stage_status):
        st, stubs = self.status(stage_status)
        return dict(id=self.id, scenario=self.scenario, status=st, value=round(float(self.value), 3), unit=self.unit,
                    op=self.op, thr=self.thr, src=self.src, basis=self.basis, would_pass=bool(self.ok()),
                    stub_deps=stubs, note=self.note)
