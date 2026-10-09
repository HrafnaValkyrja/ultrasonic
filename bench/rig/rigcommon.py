"""Shared helpers for the E1 exciter rig scripts (CLI only, no GUI). sounddevice is optional:
without it, scripts need --dry-run (writes stimulus WAVs + CSV template)."""
import csv, os, wave
import numpy as np
FS = 48000

def write_wav(path, x, fs=FS):
    x = np.atleast_2d(np.asarray(x, float).T).T if np.ndim(x) > 1 else np.asarray(x, float)[:, None]
    pk = max(1e-12, np.max(np.abs(x)))
    if pk > 1: x = x / pk
    pcm = (x * 32767).astype('<i2')
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with wave.open(path, 'wb') as w:
        w.setnchannels(x.shape[1]); w.setsampwidth(2); w.setframerate(fs); w.writeframes(pcm.tobytes())

def read_wav(path):
    with wave.open(path) as w:
        fs = w.getframerate(); n = w.getnchannels()
        x = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(float) / 32768
    return (x.reshape(-1, n) if n > 1 else x), fs

def write_csv(path, header, rows=()):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, 'w', newline='') as f:
        w = csv.writer(f); w.writerow(header); w.writerows(rows)

def log_sweep(f1, f2, dur, fs=FS, amp=0.5, fade=0.01):
    t = np.arange(int(dur * fs)) / fs
    k = np.log(f2 / f1)
    x = amp * np.sin(2 * np.pi * f1 * dur / k * (np.exp(t / dur * k) - 1))
    n = int(fade * fs); x[:n] *= np.linspace(0, 1, n); x[-n:] *= np.linspace(1, 0, n)
    return x

def tone(f, dur, amp, fs=FS, ramp=0.02):
    t = np.arange(int(dur * fs)) / fs
    x = amp * np.sin(2 * np.pi * f * t)
    n = int(ramp * fs); x[:n] *= np.linspace(0, 1, n); x[-n:] *= np.linspace(1, 0, n)
    return x

def play_rec(out, fs=FS, channels_in=2, device=None):
    """Play out (N,) or (N,k) and record channels_in channels. Needs sounddevice."""
    try:
        import sounddevice as sd
    except ImportError:
        raise SystemExit("sounddevice missing: pip install sounddevice (or use --dry-run)")
    return sd.playrec(out, fs, channels=channels_in, device=device, blocking=True)

def play(out, fs=FS, device=None):
    try:
        import sounddevice as sd
    except ImportError:
        raise SystemExit("sounddevice missing: pip install sounddevice (or use --dry-run)")
    sd.play(out, fs, device=device); sd.wait()

def dbfs(x):
    return 20 * np.log10(max(1e-12, np.sqrt(np.mean(np.square(x)))))
