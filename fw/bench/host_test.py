#!/usr/bin/env python3
"""Compare host_test output (the counted FFT kernels) with numpy.fft.rfft. Exit 1 on mismatch."""
import sys

import numpy as np

lines = open(sys.argv[1]).read().split("\n")
np_pairs = int(lines[0].split()[1])
X = np.array([[float(v) for v in l.split()[1:]] for l in lines[1:129]])
Z = X[:, 0] + 1j * X[:, 1]
i = np.arange(256)
v = 0.5 * np.sin(2 * np.pi * 40e3 * i / 200.02e3) + 0.25 * np.sin(2 * np.pi * 61e3 * i / 200.02e3 + 1.0)
v = np.round(v * 8388607.0) / 8388608.0 * (0.5 - 0.5 * np.cos(2 * np.pi * i / 256))
ref = np.fft.rfft(v)
got = Z.copy()
nyq = Z[0].imag
got[0] = Z[0].real
err = max(np.max(np.abs(got - ref[:128])), abs(nyq - ref[128].real))
bhop = [l for l in lines if l.startswith("bhop_bad")][0]
ok = err < 1e-4 * np.max(np.abs(ref)) and np_pairs == 56 and bhop.split()[1] == "0"
print(f"rfft256 max |err| = {err:.2e} (peak {np.max(np.abs(ref)):.1f}); bitrev pairs {np_pairs}; {bhop}; {'PASS' if ok else 'FAIL'}")
sys.exit(0 if ok else 1)
