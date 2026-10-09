import os, sys, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import imp_sweep, force_sweep, ab_2k5_4k, masked_threshold as mt
from rigcommon import *

def test_impedance_recovers_f0_q():
    for f0, Q in [(1200, 4), (2500, 3)]:
        v1, v2 = imp_sweep.synth(10., f0=f0, Q=Q)
        f, z = imp_sweep.impedance(v1, v2, 10., FS)
        g0, gq, _, _ = imp_sweep.f0_q(f, z)
        assert abs(g0 - f0) / f0 < 0.03
        assert 0.6 * Q < gq < 1.6 * Q   # Qms estimate vs total-Q of synthetic branch

def test_force_gain():
    assert force_sweep.gains([-40, -38, -35]) == [0, 2, 5]
    assert abs(force_sweep.level_db(0.5 * np.sin(np.arange(48000) * .1)) + 9.03) < 0.1

def test_ab_balanced_and_tally():
    a, b = ab_2k5_4k.make_pair()
    assert abs(dbfs(a) - dbfs(b)) < 0.05
    o = ab_2k5_4k.plan(2000, 3); assert abs(sum(f == '2500' for f, s in o) - 1000) < 100
    assert ab_2k5_4k.tally([('2500', '4000', 1), ('4000', '2500', 1), ('2500', '4000', 2)]) == {'2500': 1, '4000': 2}

def test_staircase_converges_on_threshold():
    rng = np.random.default_rng(0); true = -32.0
    sc = mt.Staircase(-10)
    for _ in range(200):
        if sc.done: break
        sc.update(sc.level > true + rng.normal(0, 0.5))
    assert sc.done and abs(sc.threshold() - true) < 3
