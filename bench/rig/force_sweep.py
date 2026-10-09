#!/usr/bin/env python3
"""I-022 pad-force sweep log. Plays a fixed 2.5 kHz-centred pink-ish band tone burst at each force step
(you press the pad to the gauge reading, press Enter), records the mic/accelerometer on input ch1,
logs RMS level and dB gain vs 0 N. Kill rule: gain < 2 dB at 1.5 N.
  force_sweep.py [--steps 0,0.25,0.5,1,1.5] [--freq 2500]
  force_sweep.py --dry-run     # writes burst WAV + CSV template"""
import argparse, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rigcommon import *

def level_db(x):
    return dbfs(x - np.mean(x))

def gains(levels):
    return [l - levels[0] for l in levels]

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--steps', default='0,0.25,0.5,0.75,1.0,1.25,1.5'); ap.add_argument('--freq', type=float, default=2500)
    ap.add_argument('--amp', type=float, default=0.1); ap.add_argument('--out', default='bench/rig/out')
    ap.add_argument('--device', default=None); ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    steps = [float(s) for s in a.steps.split(',')]
    burst = tone(a.freq, 2.0, a.amp)
    csvp = os.path.join(a.out, 'force_sweep.csv'); hdr = ['force_N', 'level_dbfs', 'gain_db_vs_0N']
    write_wav(os.path.join(a.out, 'force_burst.wav'), burst)
    if a.dry_run:
        write_csv(csvp, hdr, [[s, '', ''] for s in steps]); print('dry-run: wrote burst WAV + template', csvp); return
    lv = []
    for s in steps:
        input('Press pad to %.2f N, hold, Enter to play... ' % s)
        r = play_rec(burst, FS, 1, a.device)[:, 0]
        lv.append(level_db(r[int(0.3 * FS):-int(0.2 * FS)])); print('  %.2f N: %.1f dBFS' % (s, lv[-1]))
    g = gains(lv); write_csv(csvp, hdr, zip(steps, np.round(lv, 2), np.round(g, 2)))
    gm = g[steps.index(1.5)] if 1.5 in steps else g[-1]
    print('gain at cap: %.1f dB ->' % gm, 'DROP (<2 dB)' if gm < 2 else 'keep')

if __name__ == '__main__':
    main()
