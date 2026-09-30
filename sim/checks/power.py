"""Per-side current and runtime with the STM32U575 on its SMPS and the idle-listening mode (C9).

    python3 sim/checks/power.py    # prints the table, writes sim/out/power/runtime.png

Every figure is (low, nominal, high) in mA from the battery, and all are [Low]/[Med] until E4 measures them.
The active fraction comes from sim/dsp/run_phase1.py: 14% awake on the quiet-evening scene
and 93% on the busy test scene. A real day is somewhere between; E4 logs it.
"""
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
import plotstyle  # noqa: E402

OUT = REPO / "sim/out/power"
OUT.mkdir(parents=True, exist_ok=True)

ACTIVE = {   # full chain running (algorithm B)
    # Rev 2 (after audit PWR-02, repro-power): 845 uA is the datasheet point at 1.8 V / 3.072 MHz, unloaded.
    # At our 3.0 V / 4.0 MHz with the data line loaded the independent re-derivation gives 1.1/1.35/2.15.
    "mic, ultrasonic mode": (1.1, 1.35, 2.15),
    # U575 at 80 MHz, Range 2, SMPS: ~40-45 uA/MHz in Ranges 1-3 (DS13737 Rev 8 Table 39, 3.0 V);
    # the 19.5 uA/MHz headline is Range 4 only, which we don't use on the SMPS (A3-u575-plan.md)
    "MCU, algo B, 80 MHz on SMPS": (2.3, 2.7, 3.2),
    "peripherals (TIM1, ADF, DMA)": (0.6, 0.73, 0.8), # audit repro-power (ADF1 + TIM1 + GPDMA + bus)
    # bridge: the project's own SPICE at 12.5 ns dead time = 0.49 mA bus + 0.28 mA gate (audit PWR-03).
    # PWM at 800 kHz (MP-01 option F) would add ~0.8 mA: see sim/checks/pwm_ultrasonic_leak.py.
    "bridge gate charge + ripple": (0.5, 0.77, 1.0),
    "gate pull resistors (4 x 100k)": (0.06, 0.06, 0.06),   # was missing (audit)
    "transducer, listening level": (0.4, 1.1, 2.5),   # UNTRACED GUESS (audit PWR-04) until E1/E4
    "LDO, crystal, protection": (0.03, 0.05, 0.08),
}
IDLE = {     # nothing ultrasonic: band detectors only, bridge stopped
    "mic, ultrasonic mode": (1.1, 1.35, 2.15),        # stays on: the detector needs the band
    # idle detector rev 2: 256-pt FFT every 5 ms = ~3.4 Mcycle/s, ~21% busy at 16 MHz (sim/checks/idle_detector.py)
    "MCU, detectors at 16 MHz, Range 3, SMPS": (0.5, 0.7, 1.0),
    "peripherals (ADF, DMA)": (0.05, 0.1, 0.2),
    "LDO, crystal, protection": (0.03, 0.05, 0.08),
}
# Usable fraction of rated capacity, per scenario (audit PWR-01: the pessimistic case must shrink
# capacity too, not only raise current). 0.75 = an aged, cool cell cut off above the knee.
USABLE = (0.9, 0.85, 0.75)   # paired with current index (low, nominal, high)


def total(d, i):
    return sum(v[i] for v in d.values())


def runtime_h(mah, duty, i):
    return mah * USABLE[i] / (duty * total(ACTIVE, i) + (1 - duty) * total(IDLE, i))


def main():
    for name, d in (("ACTIVE", ACTIVE), ("IDLE", IDLE)):
        print(f"{name}: {total(d, 0):.2f} / {total(d, 1):.2f} / {total(d, 2):.2f} mA (low / nominal / high)")
    print(f"\n{'cell':>8s} {'duty':>6s}  runtime h (pessimistic .. nominal)")
    for mah in (80, 105, 150):
        for duty in (0.18, 0.5, 1.0):
            print(f"{mah:6d}mAh {duty:5.0%}   {runtime_h(mah, duty, 2):5.1f} .. {runtime_h(mah, duty, 1):5.1f}")

    plt = plotstyle.apply()
    fig, ax = plt.subplots(figsize=(8, 4.2))
    duty = np.linspace(0, 1, 101)
    for c, mah in zip(plotstyle.SERIES, (80, 105, 150)):
        ax.fill_between(duty * 100, runtime_h(mah, duty, 2), runtime_h(mah, duty, 1), color=c, alpha=0.18, lw=0)
        ax.plot(duty * 100, runtime_h(mah, duty, 2), color=c, label=f"{mah} mAh (line = pessimistic, band up to nominal)")
    for h, lab in ((8, "8 h minimum"), (12, "12 h target")):
        ax.axhline(h, color=plotstyle.TEXT_2, lw=0.8, ls=":")
        ax.text(101, h, lab, fontsize=8, va="center", color=plotstyle.TEXT_2)
    for x, lab, y, ha, dx in ((18, "quiet room\n(idle detector rev 2, simulated)", 55, "left", 1), (95, "busy scene\n(simulated)", 38, "right", -1)):
        ax.axvline(x, color=plotstyle.SERIES[7], lw=0.8)
        ax.text(x + dx, y, lab, fontsize=8, color=plotstyle.SERIES[7], va="top", ha=ha)
    ax.set_xlabel("time the full chain is awake (%)")
    ax.set_ylabel("runtime per charge (h)")
    ax.set_ylim(0, 60)
    ax.set_xlim(0, 100)
    ax.set_title("Runtime per side: STM32U575 on its SMPS + idle-listening mode")
    ax.legend(loc="upper right")
    fig.savefig(OUT / "runtime.png")


if __name__ == "__main__":
    main()
