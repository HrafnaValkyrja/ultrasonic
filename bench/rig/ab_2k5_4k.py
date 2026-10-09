#!/usr/bin/env python3
"""I-028 A/B listening: 2.5 kHz vs 4 kHz carrier, matched drive (equal RMS; optional --tilt-db per tone
for a loudness correction you measured), randomised order, answers logged.
Asks which pair member is 'more audible / more pleasant' (--question). Prints the tally.
  ab_2k5_4k.py --trials 20 ;  ab_2k5_4k.py --dry-run (WAVs + CSV template)"""
import argparse, os, random, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rigcommon import *

def make_pair(amp=0.1, dur=1.5, tilt_db=0.0):
    a = tone(2500, dur, amp); b = tone(4000, dur, amp * 10 ** (tilt_db / 20))
    return a, b

def plan(trials, seed):
    rng = random.Random(seed); order = []
    for _ in range(trials): order.append(rng.choice([('2500', '4000'), ('4000', '2500')]))
    return order

def tally(rows):
    """rows: (first, second, chosen_position 1|2) -> counts of chosen frequency."""
    c = {'2500': 0, '4000': 0}
    for f, s, p in rows: c[f if p == 1 else s] += 1
    return c

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--trials', type=int, default=20); ap.add_argument('--seed', type=int, default=None)
    ap.add_argument('--amp', type=float, default=0.1); ap.add_argument('--tilt-db', type=float, default=0.0)
    ap.add_argument('--question', default='more audible'); ap.add_argument('--out', default='bench/rig/out')
    ap.add_argument('--device', default=None); ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    t25, t4 = make_pair(a.amp, tilt_db=a.tilt_db)
    gap = np.zeros(int(0.5 * FS))
    write_wav(os.path.join(a.out, 'ab_2500.wav'), t25); write_wav(os.path.join(a.out, 'ab_4000.wav'), t4)
    csvp = os.path.join(a.out, 'ab_2k5_4k.csv'); hdr = ['trial', 'first_hz', 'second_hz', 'chosen_pos', 'chosen_hz', 'question']
    seed = a.seed if a.seed is not None else random.SystemRandom().randrange(1 << 30)
    order = plan(a.trials, seed)
    if a.dry_run:
        write_wav(os.path.join(a.out, 'ab_example_pair.wav'), np.concatenate([t25, gap, t4]))
        write_csv(csvp, hdr, [[i + 1, f, s, '', '', a.question] for i, (f, s) in enumerate(order)])
        print('dry-run: wrote tone WAVs, example pair, template (seed %d)' % seed); return
    tones = {'2500': t25, '4000': t4}; rows = []
    for i, (f, s) in enumerate(order):
        play(np.concatenate([tones[f], gap, tones[s]]), FS, a.device)
        while (p := input('Trial %d: which is %s, 1 or 2? ' % (i + 1, a.question)).strip()) not in ('1', '2'): pass
        rows.append((f, s, int(p)))
    write_csv(csvp, hdr, [[i + 1, f, s, p, f if p == 1 else s, a.question] for i, (f, s, p) in enumerate(rows)])
    print('tally (picks):', tally(rows), 'seed', seed)

if __name__ == '__main__':
    main()
