#!/usr/bin/env python3
"""sim/checks/runtime_fw.py: D18 runtime re-run with the firmware's measured-on-QEMU DSP load (2026-10-07).

Round 10 (2026-10-07): the MCU now runs at the REAL register-level clock plan of each variant (fw/port_u575/hal_u575_sys.c, FWSIM-R25;
every plan is an integer x 400 kHz so PWM and PCM stay exact): spec B P112 = 112.012 MHz Range 1 (Range 2 ends at 110 MHz), alternative
P104 = 104.011 MHz Range 2; slim B P72 = 72.008 MHz Range 2 + booster; A P52 = 52.006 MHz Range 3. Run and Sleep currents per range are
read from DS13737 Rev 10 (July 2024) Table 39 (Run, SMPS, ICACHE on, 3.0 V, 25 C typ, p.165) and Table 46 (Sleep, SMPS, p.172), linearly
interpolated inside the range's own rows (P112 R1 is extrapolated 8 MHz below the 120 MHz row [E]); the booster's own current is not
separated in the datasheet (characterised with it on above 55 MHz) [T].

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
# DS13737 Rev 10 Table 39 (Run) / Table 46 (Sleep), SMPS, 3.0 V, 25 C typ: {range: [(MHz, run mA, sleep mA)]}
DS_ROWS = {"R1": [(120, 5.80, 2.05), (140, 6.35, 2.25), (160, 7.15, 2.50)],
           "R2": [(64, 2.80, 1.20), (72, 3.05, 1.30), (110, 4.40, 1.95)],
           "R3": [(32, 1.40, 0.70), (55, 2.20, 0.92)]}
PLANS = {"P112": (112.012, "R1"), "P104": (104.011, "R2"), "P72": (72.008, "R2"), "P52": (52.006, "R3"), "P64": (64.007, "R2"), "P110_old": (110, "R2"),
         "P55_old": (55, "R3")}
VARIANT_PLAN = {"spec B": "P112", "spec B (alt P104)": "P104", "slim B": "P72", "A": "P52", "A (alt P64)": "P64"}
VARIANT_KEY = {"spec B": "B", "spec B (alt P104)": "B", "slim B": "slim", "A": "A", "A (alt P64)": "A"}


def ds_current(f, rng):
    """(run, sleep) mA at f MHz in range rng: linear in the range's own datasheet rows (extrapolated past the ends)."""
    r = DS_ROWS[rng]
    a, b = (r[0], r[1]) if f <= r[1][0] else (r[-2], r[-1])
    for i in range(len(r) - 1):
        if r[i][0] <= f <= r[i + 1][0]:
            a, b = r[i], r[i + 1]
    t = (f - a[0]) / (b[0] - a[0])
    return a[1] + t * (b[1] - a[1]), a[2] + t * (b[2] - a[2])
B1 = {   # power-cell.md s1 blocks, B1 (firmware levers), [low, nom, high] mA
    "mic": (1.1, 1.35, 2.15), "bridge (25 ns dead time)": (0.3, 0.47, 0.7), "gate pulls": (0.06, 0.06, 0.06),
    "exciter (guess, PWR-04)": (0.4, 1.1, 2.5), "ldo/misc": (0.03, 0.05, 0.08)}
B1_MCU, B1_PERIPH = (1.6, 1.85, 2.3), (0.3, 0.4, 0.6)
IDLE = (1.23, 1.60, 2.58)
LED = (0.03, 0.08, 0.15)
CELLS = {"PH2 175 mAh (Renata ICP501233PA-02)": 175, "K1 130 mAh (Renata ICP401230UPR)": 130}


def mcu(load_lo, load_hi, plan):
    f, rng = PLANS[plan]
    irun, islp = ds_current(f, rng)
    lo = min(load_lo / f, 1.0) * irun + (1 - min(load_lo / f, 1.0)) * islp + 0.08
    hi = min(load_hi / f, 1.0) * irun + (1 - min(load_hi / f, 1.0)) * islp + 0.08
    per = tuple(x * f / 55 for x in B1_PERIPH)
    return f, rng, (lo, (lo + hi) / 2, hi), per, (irun, islp)


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
    assert abs(ds_current(110, "R2")[0] - 4.40) < 1e-9 and abs(ds_current(55, "R3")[1] - 0.92) < 1e-9
    for v, plan in VARIANT_PLAN.items():
        lo, hi = q[VARIANT_KEY[v]]["MHz_qemu_corrected_V4ovh"]
        f, rng, m, per, (irun, islp) = mcu(lo, hi, plan)
        aw = awake(m, per)
        res[v] = {"load_MHz": [lo, hi], "clock": f"{plan} {f} MHz {rng}", "load_frac_hi": round(hi / f, 3), "fits_80pct": hi <= 0.8 * f,
                  "ds_run_sleep_mA": [round(irun, 3), round(islp, 3)], "mcu_mA": [round(x, 2) for x in m], "periph_mA": [round(x, 2) for x in per],
                  "awake_mA": [round(x, 2) for x in aw], "worst_mA": round(aw[2] + LED[2], 2),
                  "hours_worst_design_expected": {c: hours(mah, aw) for c, mah in CELLS.items()}}
    # awake fraction measured on the e2e scenes with the firmware idle detector driving IDLE (sim/fw/awake.py), nominal currents,
    # 0.85 usable: hours per scene if the whole day looked like that scene
    aw = REPO / "sim/out/fw/awake.json"
    if aw.exists():
        sc = json.loads(aw.read_text())
        res["scenes_awake_fraction"] = {n: v["awake_frac_after_3s"] for n, v in sc.items()}
        for v in VARIANT_PLAN:
            a_nom = res[v]["awake_mA"][1]
            res[v]["hours_by_scene_nominal"] = {c: {n: round(mah * 0.85 / (f * a_nom + (1 - f) * IDLE[1] + LED[1]), 1)
                                                    for n, f in res["scenes_awake_fraction"].items()} for c, mah in CELLS.items()}
    print(json.dumps(res, indent=1))
    if a.json:
        a.json.write_text(json.dumps(res, indent=1) + "\n")


if __name__ == "__main__":
    main()
