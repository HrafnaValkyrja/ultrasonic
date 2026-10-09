#!/usr/bin/env python3
"""Masked-threshold runner (bench-day List B1). Adaptive 2-down-1-up staircase (converges ~70.7 %):
test tone (default 2.5 kHz, 0.5 s) added under a looping street-noise WAV. 'y' = heard it, 'n' = not.
Two heard in a row -> level down; one miss -> level up. Threshold = mean of the last reversals.
Levels are dB re rig setting (0 dB = --amp full scale). Repeat runs (5) with --run N.
  masked_threshold.py --noise street.wav ;  masked_threshold.py --dry-run (WAVs + CSV template)"""
import argparse, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rigcommon import *

class Staircase:
    def __init__(self, start=-20.0, step=4.0, min_step=1.0, reversals=8):
        self.level, self.step, self.min_step, self.need = start, step, min_step, reversals
        self.hits = 0; self.last_dir = 0; self.rev = []
    def update(self, heard):
        d = 0
        if heard:
            self.hits += 1
            if self.hits == 2: d = -1; self.hits = 0
        else:
            self.hits = 0; d = +1
        if d:
            if self.last_dir and d != self.last_dir:
                self.rev.append(self.level); self.step = max(self.min_step, self.step / 2)
            self.last_dir = d; self.level += d * self.step
    @property
    def done(self): return len(self.rev) >= self.need
    def threshold(self, last=6):
        r = self.rev[-last:]; return float(np.mean(r)) if r else float('nan')

def mix(noise, test, level_db, pos):
    out = noise.copy(); g = 10 ** (level_db / 20)
    out[pos:pos + len(test)] += g * test; return out

def synth_noise(dur=30, fs=FS, seed=1):
    """Stand-in street noise: 1/f-ish (pink) noise, for dry-runs only; use a real recording on the bench."""
    r = np.random.default_rng(seed).standard_normal(int(dur * fs)); S = np.fft.rfft(r)
    f = np.maximum(np.fft.rfftfreq(len(r), 1 / fs), 20); x = np.fft.irfft(S / np.sqrt(f), len(r))
    return 0.2 * x / np.std(x) / 4

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--noise'); ap.add_argument('--freq', type=float, default=2500)
    ap.add_argument('--amp', type=float, default=0.5); ap.add_argument('--start', type=float, default=-20)
    ap.add_argument('--run', type=int, default=1); ap.add_argument('--out', default='bench/rig/out')
    ap.add_argument('--device', default=None); ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    csvp = os.path.join(a.out, 'masked_threshold.csv'); hdr = ['run', 'trial', 'level_db_re_rig', 'heard']
    test = tone(a.freq, 0.5, a.amp)
    if a.noise: noise, fs = read_wav(a.noise); noise = noise if noise.ndim == 1 else noise[:, 0]
    else: noise = synth_noise()
    if a.dry_run:
        write_wav(os.path.join(a.out, 'mask_noise.wav'), noise); write_wav(os.path.join(a.out, 'mask_test_tone.wav'), test)
        write_wav(os.path.join(a.out, 'mask_example.wav'), mix(noise, test, a.start, int(1.0 * FS)))
        write_csv(csvp, hdr, [[a.run, i + 1, '', ''] for i in range(12)]); print('dry-run: wrote stimuli + template'); return
    sc = Staircase(a.start); rows = []; n = 0
    while not sc.done and n < 60:
        n += 1; pos = int(np.random.default_rng().uniform(0.5, 1.5) * FS)
        play(mix(noise[:int(3 * FS)] if len(noise) > 3 * FS else noise, test, sc.level, pos), FS, a.device)
        h = input('Trial %d at %.1f dB: heard the tone? [y/n] ' % (n, sc.level)).strip().lower() == 'y'
        rows.append([a.run, n, sc.level, int(h)]); sc.update(h)
    new = not os.path.exists(csvp)
    with open(csvp, 'a') as fh:
        if new: fh.write(','.join(hdr) + '\n')
        for r in rows: fh.write(','.join(map(str, r)) + '\n')
    print('run %d threshold: %.1f dB re rig setting' % (a.run, sc.threshold()))

if __name__ == '__main__':
    main()
