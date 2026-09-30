"""Synthetic ultrasonic test corpus, in pascals at the microphone, sampled at 400 kS/s.

Levels are rough real-world figures (dB SPL re 20 uPa at the mic):
  big brown bat FM call at ~10 m     ~70 dB    (source ~115-120 dB at 10 cm, spreading + absorption)
  eastern red bat, ~15 m              ~62 dB
  katydid stridulation, ~2 m          ~60 dB
  switch-mode charger whine, ~1 m     ~40 dB    (steady tone, the owner hears these)
  LED driver whine                    ~35 dB
  keys jingling, ~0.5 m               ~65 dB    (broadband clicks)
  HC-SR04 rangefinder bursts, ~1 m    ~85 dB    (40 kHz, 8 cycles every 60 ms)
  speech, ~1 m                        ~60 dB    (audible band; must be removed by the band floor)
All sources are synthetic stand-ins for Phase 1; real recordings replace them (C1, S1).
"""
import numpy as np

FS = 400_000
P_REF = 20e-6


def db_spl_to_pa_rms(db):
    return P_REF * 10 ** (db / 20)


def _norm_rms(x):
    r = np.sqrt(np.mean(x ** 2))
    return x / r if r > 0 else x


def fm_call(t0, dur, f_start, f_end, level_db, n, rng, shape="hyperbolic"):
    """Bat-like FM sweep with a Hann envelope, starting at t0 (s)."""
    t = np.arange(int(dur * FS)) / FS
    if shape == "hyperbolic":          # big-brown-like: steep then flattening
        k = (f_start / f_end - 1) / dur
        phase = 2 * np.pi * f_start / k * np.log1p(k * t)
    else:                              # linear sweep
        phase = 2 * np.pi * (f_start * t + 0.5 * (f_end - f_start) / dur * t ** 2)
    sig = np.sin(phase) * np.hanning(len(t))
    sig += 0.25 * np.sin(2 * phase) * np.hanning(len(t))       # 2nd harmonic
    out = np.zeros(n)
    i = int(t0 * FS)
    seg = sig[: max(0, min(len(sig), n - i))]
    out[i:i + len(seg)] = seg
    return out, level_db


def scene(duration=6.0, seed=1):
    """Return dict name -> (signal in Pa, description) and the mixed scene."""
    rng = np.random.default_rng(seed)
    n = int(duration * FS)
    t = np.arange(n) / FS
    parts = {}

    # Bats: search-phase call trains (~8-10 calls/s), plus an approach buzz for the big brown.
    bb = np.zeros(n)
    for k, t0 in enumerate(np.arange(0.30, 2.6, 0.11)):
        s, _ = fm_call(t0, 0.006, 55e3, 26e3, 0, n, rng)
        bb += s
    for t0 in np.arange(2.6, 2.9, 0.012):             # feeding buzz: short, fast calls
        s, _ = fm_call(t0, 0.0015, 45e3, 25e3, 0, n, rng)
        bb += 0.6 * s
    parts["big_brown_bat"] = (bb, 70, "FM 55->26 kHz, 6 ms calls at 9/s, then a feeding buzz")
    rb = np.zeros(n)
    for t0 in np.arange(3.2, 5.6, 0.10):
        s, _ = fm_call(t0, 0.008, 48e3, 36e3, 0, n, rng, shape="linear")
        rb += s
    parts["red_bat"] = (rb, 62, "shallow FM 48->36 kHz, 8 ms calls")

    # Katydid: pulse trains of broadband-ish buzz centred ~25-35 kHz.
    kd = np.zeros(n)
    carrier = rng.standard_normal(n)
    carrier = _filt(_bandpass(22e3, 38e3), carrier)
    gate = ((t % 0.5) < 0.25) & (((t * 180) % 1) < 0.5)            # 180 Hz chirp rate in bursts
    kd = carrier * gate * ((t > 1.0) & (t < 4.5))
    parts["katydid"] = (kd, 58, "buzz 22-38 kHz, 180 Hz pulse trains, 1-4.5 s")

    # Steady electronics whines (the thing Transient-only mode must suppress).
    parts["charger_whine"] = (np.sin(2 * np.pi * 25_000 * t) + 0.3 * np.sin(2 * np.pi * 50_000 * t), 40,
                              "steady 25 kHz + 50 kHz harmonic")
    parts["led_driver"] = (np.sin(2 * np.pi * 33_300 * t), 35, "steady 33.3 kHz")

    # Keys jingling: a cluster of decaying broadband clicks around 4.8-5.3 s.
    keys = np.zeros(n)
    for t0 in rng.uniform(4.8, 5.3, 25):
        i = int(t0 * FS)
        L = int(0.004 * FS)
        m = min(L, n - i)
        f = rng.uniform(20e3, 70e3)
        keys[i:i + m] += np.sin(2 * np.pi * f * np.arange(m) / FS) * np.exp(-np.arange(m) / (0.0008 * FS)) * rng.uniform(0.4, 1)
    parts["keys"] = (keys, 65, "metal clicks 20-70 kHz, 4.8-5.3 s")

    # HC-SR04: 8 cycles of 40 kHz every 60 ms, 0.2-0.9 s.
    hc = np.zeros(n)
    burst = np.sin(2 * np.pi * 40e3 * np.arange(int(8 / 40e3 * FS)) / FS)
    for t0 in np.arange(0.2, 0.9, 0.06):
        i = int(t0 * FS)
        hc[i:i + len(burst)] += burst
    parts["hc_sr04"] = (hc, 85, "40 kHz, 8-cycle bursts every 60 ms")

    # Speech-band stand-in (audible band only; the band floor must remove it).
    sp = _filt(_bandpass(200, 6000), rng.standard_normal(n)) * (0.5 + 0.5 * np.sin(2 * np.pi * 3 * t)) ** 2
    parts["speech_band"] = (sp, 60, "0.2-6 kHz noise, syllable-rate modulated (should vanish)")

    mix = np.zeros(n)
    for name, (sig, db, _) in parts.items():
        active = sig != 0
        rms = np.sqrt(np.mean(sig[np.abs(sig) > 1e-9] ** 2)) if np.any(np.abs(sig) > 1e-9) else 1
        mix += sig / rms * db_spl_to_pa_rms(db)
    return parts, mix


def _bandpass(lo, hi):
    """Second-order sections: a b/a design with a 200 Hz corner at 400 kS/s is numerically unstable."""
    from scipy import signal
    return signal.butter(4, [lo, hi], btype="band", fs=FS, output="sos")


def _filt(sos, x):
    from scipy import signal
    return signal.sosfilt(sos, x)


def quiet_scene(duration=30.0, seed=2, whines=True):
    """A quiet evening indoors/porch: steady whines + speech all the time, and a few short events.

    Events: two bat passes (~1.2 s each), one burst of keys, one rangefinder burst train (0.4 s).
    About 3.6 s of 30 s (12%) has real ultrasonic events; the idle detector should wake for
    roughly that plus its hang time, not for the whines.
    """
    rng = np.random.default_rng(seed)
    n = int(duration * FS)
    t = np.arange(n) / FS
    ev = np.zeros(n)
    for start in (4.0, 19.0):
        for t0 in np.arange(start, start + 1.2, 0.11):
            s, _ = fm_call(t0, 0.006, 55e3, 26e3, 0, n, rng)
            ev += s
    keys = np.zeros(n)
    for t0 in rng.uniform(11.0, 11.4, 20):
        i, L = int(t0 * FS), int(0.004 * FS)
        m = min(L, n - i)
        f = rng.uniform(20e3, 70e3)
        keys[i:i + m] += np.sin(2 * np.pi * f * np.arange(m) / FS) * np.exp(-np.arange(m) / (0.0008 * FS))
    hc = np.zeros(n)
    burst = np.sin(2 * np.pi * 40e3 * np.arange(int(8 / 40e3 * FS)) / FS)
    for t0 in np.arange(26.0, 26.4, 0.06):
        i = int(t0 * FS)
        hc[i:i + len(burst)] += burst
    whine = np.sin(2 * np.pi * 25_000 * t) + 0.3 * np.sin(2 * np.pi * 50_000 * t)
    led = np.sin(2 * np.pi * 33_300 * t)
    sp = _filt(_bandpass(200, 6000), rng.standard_normal(n)) * (0.5 + 0.5 * np.sin(2 * np.pi * 3 * t)) ** 2
    parts = {"bats": (ev, 66), "keys": (keys, 62), "hc_sr04": (hc, 75),
             "charger_whine": (whine, 40), "led_driver": (led, 35), "speech_band": (sp, 60)}
    if not whines:          # a room with no electronics: exposes detectors that wake on audible speech
        del parts["charger_whine"], parts["led_driver"]
    mix = np.zeros(n)
    for sig, db in parts.values():
        nz = np.abs(sig) > 1e-9
        mix += sig / np.sqrt(np.mean(sig[nz] ** 2)) * db_spl_to_pa_rms(db)
    events = [(4.0, 5.2), (11.0, 11.4), (19.0, 20.2), (26.0, 26.4)]
    return parts, mix, events
