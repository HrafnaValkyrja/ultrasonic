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
    "mic, ultrasonic mode": (0.9, 1.0, 1.1),          # SPH0641LU4H-1: 845 uA typ; more at 3.0 V and 4 MHz
    "MCU, algo B, 80 MHz on SMPS": (0.9, 1.3, 1.6),   # 44-65 Mcycle/s (C2) x 19.5 uA/MHz (DS13737 Tab.37) + sleep
    "peripherals (TIM1, MDF, DMA)": (0.6, 0.8, 1.0),
    "bridge gate charge + ripple": (0.4, 0.5, 0.6),   # 4 FETs x ~0.5 nC x 200 kHz (B1)
    "transducer, listening level": (0.6, 1.1, 1.7),   # tragus site (D1); E4 measures
    "LDO, crystal, protection": (0.03, 0.05, 0.08),
}
IDLE = {     # nothing ultrasonic: band detectors only, bridge stopped
    "mic, ultrasonic mode": (0.9, 1.0, 1.1),          # stays on: the detector needs the band
    "MCU, detectors at 16 MHz on SMPS": (0.25, 0.4, 0.6),
    "peripherals (MDF, DMA)": (0.25, 0.35, 0.5),
    "LDO, crystal, protection": (0.03, 0.05, 0.08),
}
USABLE = 0.85          # usable fraction of rated capacity (cut-off above the knee, ageing)


def total(d, i):
    return sum(v[i] for v in d.values())


def runtime_h(mah, duty, i):
    return mah * USABLE / (duty * total(ACTIVE, i) + (1 - duty) * total(IDLE, i))


def main():
    for name, d in (("ACTIVE", ACTIVE), ("IDLE", IDLE)):
        print(f"{name}: {total(d, 0):.2f} / {total(d, 1):.2f} / {total(d, 2):.2f} mA (low / nominal / high)")
    print(f"\n{'cell':>8s} {'duty':>6s}  runtime h (pessimistic .. nominal)")
    for mah in (80, 105, 150):
        for duty in (0.14, 0.5, 1.0):
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
    for x, lab in ((14, "quiet evening\n(simulated)"), (93, "busy scene\n(simulated)")):
        ax.axvline(x, color=plotstyle.SERIES[7], lw=0.8)
        ax.text(x + 1, 55, lab, fontsize=8, color=plotstyle.SERIES[7], va="top")
    ax.set_xlabel("time the full chain is awake (%)")
    ax.set_ylabel("runtime per charge (h)")
    ax.set_ylim(0, 60)
    ax.set_xlim(0, 100)
    ax.set_title("Runtime per side: STM32U575 on its SMPS + idle-listening mode")
    ax.legend(loc="upper right")
    fig.savefig(OUT / "runtime.png")


if __name__ == "__main__":
    main()
