#!/usr/bin/env python3
"""sim/checks/runtime_fw.py: D18 runtime re-run with the firmware's measured-on-QEMU DSP load (2026-10-07).

Model = docs/research/drastic/power-cell.md budget B1 (pc.py, 2026-10-03; the script itself lived in a session scratchpad and is gone,
so the B1 block table is re-entered here from the .md and reproduces its totals: awake 3.79/5.26/8.39, worst 8.54 mA) with ONLY the MCU
and peripheral rows replaced: the clock is the lowest DS13737 Run/SMPS point that keeps the QEMU-corrected worst load <= 80 % of the
clock (FWSIM-R48 PASS rule), MCU = busy x I_run + (1 - busy) x I_sleep + 0.08 (MSI/PLL), busy = load / clock, I_sleep = 0.42 x I_run
(the 55 MHz R3 ratio 0.92/2.20, applied to other points [E]); peripherals scale with clock from B1's 55 MHz row. Loads: fw/out/dsp_icount.json
(FMAC build, MHz incl. V4 overhead, QEMU-corrected [lo, hi]). Policies as power-cell.md: worst = always awake, every block high,
LED high, 75 % usable; design = 50 % awake, nominal, 0.85 x 0.8 (end of life); expected = 18 % awake, nominal, 0.85.
    python3 sim/checks/runtime_fw.py [--json PATH]
"""
import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RUN_SMPS = [(55, 2.20, "R3"), (64, 2.80, "R2"), (72, 3.05, "R2"), (110, 4.40, "R2"), (160, 7.15, "R1")]   # DS13737 Rev 8 via power-cell.md
SLEEP_RATIO = 0.92 / 2.20
B1 = {   # power-cell.md s1 blocks, B1 (firmware levers), [low, nom, high] mA
    "mic": (1.1, 1.35, 2.15), "bridge (25 ns dead time)": (0.3, 0.47, 0.7), "gate pulls": (0.06, 0.06, 0.06),
    "exciter (guess, PWR-04)": (0.4, 1.1, 2.5), "ldo/misc": (0.03, 0.05, 0.08)}
B1_MCU, B1_PERIPH = (1.6, 1.85, 2.3), (0.3, 0.4, 0.6)
IDLE = (1.23, 1.60, 2.58)
LED = (0.03, 0.08, 0.15)
CELLS = {"PH2 175 mAh (Renata ICP501233PA-02)": 175, "K1 130 mAh (Renata ICP401230UPR)": 130}


def mcu(load_lo, load_hi):
    f, irun, rng = next(r for r in RUN_SMPS if load_hi <= 0.8 * r[0])
    lo = min(load_lo / f, 1.0) * irun + (1 - min(load_lo / f, 1.0)) * irun * SLEEP_RATIO + 0.08
    hi = min(load_hi / f, 1.0) * irun + (1 - min(load_hi / f, 1.0)) * irun * SLEEP_RATIO + 0.08
    per = tuple(x * f / 55 for x in B1_PERIPH)
    return f, rng, (lo, (lo + hi) / 2, hi), per


def awake(m, per):
    return tuple(sum(v[i] for v in B1.values()) + m[i] + per[i] for i in range(3))


def hours(mah, a):
    worst = mah * 0.75 / (a[2] + LED[2])
    design = mah * 0.85 * 0.8 / (0.5 * a[1] + 0.5 * IDLE[1] + LED[1])
    expected = mah * 0.85 / (0.18 * a[1] + 0.82 * IDLE[1] + LED[1])
    return round(worst, 1), round(design, 1), round(expected, 1)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", type=Path)
    a = ap.parse_args(argv)
    q = json.loads((REPO / "fw/out/dsp_icount.json").read_text())
    check = awake(B1_MCU, B1_PERIPH)
    assert abs(check[1] - 5.26) < 0.03 and abs(check[2] + LED[2] - 8.54) < 0.01, check   # reproduces power-cell.md B1
    res = {"model": "power-cell.md B1 with MCU/peripherals from the firmware load (this file's docstring)",
           "B1_reference": {"awake_mA": [round(x, 2) for x in check], "worst_hours_130": hours(130, check)[0]}}
    for v, key in (("spec B", "B"), ("slim B", "slim"), ("A", "A")):
        lo, hi = q[key]["MHz_qemu_corrected_V4ovh"]
        f, rng, m, per = mcu(lo, hi)
        aw = awake(m, per)
        res[v] = {"load_MHz": [lo, hi], "clock": f"{f} MHz {rng}", "mcu_mA": [round(x, 2) for x in m], "periph_mA": [round(x, 2) for x in per],
                  "awake_mA": [round(x, 2) for x in aw], "worst_mA": round(aw[2] + LED[2], 2),
                  "hours_worst_design_expected": {c: hours(mah, aw) for c, mah in CELLS.items()}}
    print(json.dumps(res, indent=1))
    if a.json:
        a.json.write_text(json.dumps(res, indent=1) + "\n")


if __name__ == "__main__":
    main()
