#!/usr/bin/env python3
"""Phase-2 pod MCU diagrams (DIAG / PROC-10): clock tree and QFN48 pin map. Facts only from repo sources:
fw/port_u575/hal_u575_sys.c (plans table, PLL1 M=3/MBOOST/N/R), fw/hal/hal_clock.h, docs/research/A3-u575-plan.md (ADF
dividers), docs/system/sub-processing.md (clock block, pin groups), docs/system/integration-map.md §4 (pin -> net).
    python3 docs/diagrams/make_u575_maps.py  -> docs/diagrams/u575-clock-tree.svg, u575-pin-map.svg (then render.sh)
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import plotstyle  # noqa: E402

plotstyle.apply()
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Rectangle  # noqa: E402

S = plotstyle.SERIES
TXT, MUT = plotstyle.TEXT, plotstyle.TEXT_2
plt.rcParams["svg.fonttype"] = "none"


def box(ax, x, y, w, h, text, c, fs=9, ls="-"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.12", fc=c + "33", ec=c, lw=1.3, ls=ls))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", color=TXT, fontsize=fs, linespacing=1.35)


def arrow(ax, x0, y0, x1, y1, label="", c=MUT, dy=0.13, ls="-"):
    ax.annotate("", (x1, y1), (x0, y0), arrowprops=dict(arrowstyle="-|>", color=c, lw=1.3, ls=ls))
    if label:
        ax.text((x0 + x1) / 2, (y0 + y1) / 2 + dy, label, ha="center", va="bottom", color=c, fontsize=8)


# ------------------------------------------------------------------ 1. clock tree
fig, ax = plt.subplots(figsize=(15, 8.4))
ax.set_xlim(0, 30); ax.set_ylim(-2.0, 16.8); ax.axis("off")
ax.text(0.2, 16.4, "STM32U575 clock tree (Phase-2 pod, U1) - firmware plans, default P80", color=TXT, fontsize=14, weight="bold", va="top")
ax.text(0.2, 15.75, "sources: fw/port_u575/hal_u575_sys.c, fw/hal/hal_clock.h, A3-u575-plan.md, sub-processing.md  |  dashed = not fitted / not used",
        color=MUT, fontsize=8.5, va="top")
# sources
box(ax, 0.6, 11.6, 4.6, 1.3, "LSE  32.768 kHz\nY1 FC-12M (PC14/PC15)", S[0])
box(ax, 0.6, 9.3, 4.6, 1.3, "HSE  not fitted\n(PH0/PH1 free, NC)", MUT, ls="--")
box(ax, 0.6, 7.0, 4.6, 1.3, "HSI16  16 MHz\n(I2C2 kernel clock only)", S[2])
box(ax, 0.6, 4.7, 4.6, 1.3, "HSI48  48 MHz\n+ CRS trim", S[3])
box(ax, 6.2, 11.6, 5.4, 1.3, "MSIS  range 0 = 48 MHz\nPLL mode: locked to LSE\n1465 x 32.768k = 48.005 MHz", S[1], fs=8)
arrow(ax, 5.2, 12.25, 6.2, 12.25, "", S[0])
ax.text(5.7, 12.45, "lock", color=S[0], fontsize=8, ha="center")
box(ax, 12.4, 11.6, 4.2, 1.3, "PLL1 input: / M=3\n= 16.0017 MHz\n(MBOOST /4 -> 12 MHz)", S[1], fs=8)
arrow(ax, 11.6, 12.25, 12.4, 12.25, "", S[1])
box(ax, 17.2, 11.6, 4.0, 1.3, "VCO = 16.0017 x N\nP80: N=20 -> 320.03 MHz", S[1], fs=8)
arrow(ax, 16.6, 12.25, 17.2, 12.25)
box(ax, 21.8, 11.6, 2.6, 1.3, "PLL1R divider\nP80: R=4", S[1], fs=8)
arrow(ax, 21.2, 12.25, 21.8, 12.25)
box(ax, 25.2, 11.45, 4.5, 1.6, "SYSCLK = HCLK\nP80 = 80.009 MHz\nCFGR1.SW = 11 (PLL1)", S[5], fs=9)
arrow(ax, 24.4, 12.25, 25.2, 12.25)
ax.annotate("", (27.0, 13.05), (9.0, 12.95), arrowprops=dict(arrowstyle="-|>", color=S[1], lw=1.2, ls="--", connectionstyle="arc3,rad=-0.18"))
ax.text(18.0, 15.15, "P48: PLL off, SW = MSIS direct, 48.005 MHz", color=S[1], fontsize=8, ha="center")
# HCLK bus
ax.plot([27.4, 27.4], [11.45, 9.9], color=S[5], lw=1.3)
ax.text(27.55, 10.6, "HCLK", color=S[5], fontsize=8)
ax.plot([15.5, 27.4], [9.9, 9.9], color=S[5], lw=1.3)
box(ax, 24.2, 7.0, 5.5, 1.8, "TIM1  (PA8/PA7, PA10/PB15)\ncentre-aligned, ARR = 200\nPWM = 80.009M / 400 = 200.02 kHz\ndead-time tick 12.5 ns", S[2], fs=8)
arrow(ax, 27.0, 9.9, 27.0, 8.8, "", S[5])
box(ax, 14.0, 8.0, 3.0, 1.5, "ADF1 kernel\n= HCLK", S[0], fs=8.5)
arrow(ax, 15.5, 9.9, 15.5, 9.5, "", S[5])
box(ax, 13.6, 5.6, 3.8, 1.4, "/ PROCDIV+1 = 2\nproc_ck 40 MHz", S[0], fs=8.5)
arrow(ax, 15.5, 8.0, 15.5, 7.0)
box(ax, 18.2, 5.6, 4.4, 1.4, "/ CCKDIV+1 = 10\nmic clock 4.0004 MHz\n(= HCLK / 20)", S[0], fs=8.5)
arrow(ax, 17.4, 6.3, 18.2, 6.3)
box(ax, 23.2, 5.4, 4.2, 1.3, "CIC5 /5 -> 800 kS/s\nRSFLT /4 -> 200.02 kS/s", S[0], fs=8)
arrow(ax, 22.6, 6.05, 23.4, 6.05)
box(ax, 17.6, 3.7, 5.0, 1.3, "PB3 ADF1_CCK0 -> R2 33R\n-> MIC_CLK (mic U2)", S[0], fs=8)
arrow(ax, 20.4, 5.6, 20.4, 5.0)
box(ax, 23.6, 3.7, 3.8, 1.3, "PB4 ADF1_SDI0\n= MIC_DATA (PDM in)", S[0], fs=8)
arrow(ax, 23.6, 4.35, 22.6, 4.35)
arrow(ax, 25.5, 5.0, 25.5, 5.4)
box(ax, 7.0, 4.7, 4.6, 1.3, "USB FS 48 MHz\nPA11 DM / PA12 DP\nCRS-trimmed HSI48", S[3], fs=8.5)
arrow(ax, 5.2, 5.35, 7.0, 5.35, "", S[3])
box(ax, 7.0, 7.0, 4.6, 1.3, "I2C2 kernel (HSI16)\nPB13 SCL / PB14 SDA\n(CCIPR1 I2C2SEL = 10)", S[2], fs=8.5)
arrow(ax, 5.2, 7.65, 7.0, 7.65, "", S[2])
box(ax, 0.6, 2.3, 4.6, 1.3, "RTC / backup domain\non LSE (4.25 uA in Stop 2)", S[0], fs=8.5)
ax.plot([0.25, 0.25], [12.25, 3.0], color=S[0], lw=1.2, ls=":")
ax.plot([0.25, 0.6], [12.25, 12.25], color=S[0], lw=1.2, ls=":")
arrow(ax, 0.25, 3.0, 0.6, 3.0, "", S[0])
box(ax, 7.0, 2.3, 4.8, 1.5, "Internal SMPS 3 MHz (own RC)\nVLXSMPS -> L1 -> VDD11\nnot lockable to HCLK (RM0456 Rev 7)", MUT, fs=8, ls="--")
# plans table (columns = plans)
ax.text(12.4, 3.15, "PLL1 plans (hal_u575_sys.c plans[]):", color=MUT, fontsize=8)
cols = ["P80", "P160", "P64", "P48", "P112", "P104", "P72", "P52"]
tab = {"SYSCLK MHz": ["80.009", "160.018", "64.007", "48.005", "112.012", "104.011", "72.008", "52.006"],
       "N (VCO x)": ["20", "20", "24", "-", "28", "26", "18", "13"], "R": ["4", "2", "6", "-", "4", "4", "4", "4"],
       "voltage range": ["2", "1", "2", "3", "1", "2", "2", "3"], "flash WS": ["2", "4", "2", "2", "3", "3", "2", "2"]}
for j, c in enumerate(cols):
    ax.text(16.0 + j * 1.75, 2.75, c, color=TXT, fontsize=8.5, weight="bold", family="monospace", ha="center")
for i, (k, v) in enumerate(tab.items()):
    ax.text(12.4, 2.3 - i * 0.42, k, color=MUT, fontsize=8, family="monospace")
    for j, x in enumerate(v):
        ax.text(16.0 + j * 1.75, 2.3 - i * 0.42, x, color=TXT, fontsize=8.5, family="monospace", ha="center")
ax.text(0.3, -0.35, "All rates are integer ratios of HCLK: mic CCK = HCLK/20, PCM = HCLK/400, PWM = HCLK/400 -> bridge leakage folds to 0 Hz (D14).", color=TXT, fontsize=9)
ax.text(0.3, -0.95, "Other plans keep CCK at 4.0004 MHz via PROCDIV/CCKDIV (P160: 4/10, P64: 2/8, P48: 1/12). A plan change restarts ADF1 (firmware: only with TIM1 and ADF1 stopped).", color=MUT, fontsize=8.5)
ax.text(0.3, -1.55, "No SAI is used in the firmware or on the pod; the output is TIM1 PWM. Mic start-up runs the CCK at 2.0 MHz (PROCDIV+1 doubled), >= 50 ms.", color=MUT, fontsize=8.5)
fig.savefig(HERE / "u575-clock-tree.svg", bbox_inches="tight")
plt.close(fig)

# ------------------------------------------------------------------ 2. pin map
net = {}
for ln in (ROOT / "docs/system/integration-map.md").read_text().splitlines():
    m = re.match(r"\| (\d+) \| (\S+) \| (\S+) \| (.*?) \|$", ln)
    if m:
        net[int(m[1])] = (m[2], m[3], m[4])
net = {k: v for k, v in net.items() if 1 <= k <= 49}
FREE = {2: "PC13", 5: "PH0", 6: "PH1", 13: "PA3", 18: "PB0", 30: "PA9"}
for k, v in FREE.items():
    net[k] = (v, "free (NC)", "")
G = {"pwr": ("supply / ground", MUT), "clk": ("clock, reset, boot", S[1]), "mic": ("mic ADF1 (AF3)", S[0]), "br": ("bridge TIM1 (AF1)", S[2]),
     "an": ("analog sense", S[3]), "chg": ("charger I2C2 / int", S[4]), "usb": ("USB, SWD, button, LED", S[6]),
     "dbg": ("debug dots / strap", S[7]), "free": ("free, not connected", "#555a62")}
FN = {1: ("pwr", "VBAT = +3V0"), 3: ("clk", "LSE in"), 4: ("clk", "LSE out"), 7: ("clk", "reset"), 44: ("clk", "BOOT0 (R1 tack -> DFU)"),
      15: ("mic", "mic supply (GPIO)"), 39: ("mic", "ADF1_CCK0, 4.0004 MHz"), 40: ("mic", "ADF1_SDI0 PDM in"),
      29: ("br", "TIM1_CH1"), 17: ("br", "TIM1_CH1N"), 31: ("br", "TIM1_CH3"), 28: ("br", "TIM1_CH3N"),
      11: ("an", "VBUS sense (ADC)"), 12: ("an", "NTC (ADC)"), 14: ("an", "VBAT sense ADC4"), 16: ("an", "ADC1_IN11 bridge I"),
      26: ("chg", "I2C2_SCL"), 27: ("chg", "I2C2_SDA"), 38: ("chg", "EXTI15 charger int"),
      32: ("usb", "USB FS D-"), 33: ("usb", "USB FS D+"), 34: ("usb", "SWDIO"), 37: ("usb", "SWCLK"), 10: ("usb", "PA0 WKUP1 button"), 43: ("usb", "TIM4_CH2 LED, open-drain"),
      42: ("dbg", "USART1_TX printf"), 45: ("dbg", "MDF1_CCK0 (fallback)"), 19: ("dbg", "MDF1_SDI0 (fallback)"), 41: ("dbg", "strap to GND (UCPD)"),
      8: ("pwr", "GND"), 9: ("pwr", "VDDA"), 20: ("pwr", "SMPS switch node"), 21: ("pwr", "SMPS supply"), 22: ("pwr", "GND"), 23: ("pwr", "core 1.1-1.2 V"),
      24: ("pwr", "GND"), 25: ("pwr", "VDD"), 35: ("pwr", "GND"), 36: ("pwr", "VDD"), 46: ("pwr", "core 1.1-1.2 V"), 47: ("pwr", "GND"), 48: ("pwr", "VDD"), 49: ("pwr", "GND (exposed pad)")}
for k in FREE:
    FN[k] = ("free", "")
fig, ax = plt.subplots(figsize=(15, 13.2))
ax.set_xlim(-14, 14); ax.set_ylim(-13.8, 14.4); ax.set_aspect("equal"); ax.axis("off")
ax.text(-13.8, 14.2, "STM32U575CIU6Q (U1) pin map - UFQFN48 7x7, Phase-2 pod, top view", color=TXT, fontsize=14, weight="bold", va="top")
ax.text(-13.8, 13.5, "pin  NAME -> net -> function  (integration-map §4 + sub-processing.md pins; 42 of 48 used)", color=MUT, fontsize=9, va="top")
H = 4.2
ax.add_patch(Rectangle((-H, -H), 2 * H, 2 * H, fc="#1c1e24", ec=TXT, lw=1.5))
ax.text(0, 0.4, "U1\nSTM32U575\nCIU6Q", ha="center", va="center", color=TXT, fontsize=13, weight="bold")
ax.text(0, -1.6, "pin 1 top-left, counter-clockwise\nEP (49) = GND", ha="center", va="center", color=MUT, fontsize=8.5)
ax.plot(-H + 0.5, H - 0.5, "o", color=TXT, ms=4)
p = 2 * H / 12


def pos(n):   # (x, y, side)
    i = (n - 1) % 12
    if n <= 12:
        return -H, H - p * (i + 0.5), "L"
    if n <= 24:
        return -H + p * (i + 0.5), -H, "B"
    if n <= 36:
        return H, -H + p * (i + 0.5), "R"
    return H - p * (i + 0.5), H, "T"


for n in range(1, 49):
    name, nt, other = net[n]
    g, f = FN[n]
    c = G[g][1]
    x, y, side = pos(n)
    lab = f"{n}  {name} -> {nt}" + (f" -> {f}" if f else "")
    if side == "L":
        ax.plot([x - 1.0, x], [y, y], color=c, lw=2.2)
        ax.text(x - 1.1, y, lab, ha="right", va="center", color=c, fontsize=8)
    elif side == "R":
        ax.plot([x, x + 1.0], [y, y], color=c, lw=2.2)
        ax.text(x + 1.1, y, lab, ha="left", va="center", color=c, fontsize=8)
    elif side == "B":
        ax.plot([x, x], [y - 1.0, y], color=c, lw=2.2)
        ax.text(x, y - 1.1, lab, ha="right", va="center", color=c, fontsize=8, rotation=90, rotation_mode="anchor")
    else:
        ax.plot([x, x], [y, y + 1.0], color=c, lw=2.2)
        ax.text(x, y + 1.1, lab, ha="left", va="center", color=c, fontsize=8, rotation=90, rotation_mode="anchor")
for i, (k, (t, c)) in enumerate(G.items()):
    ax.add_patch(Rectangle((-13.8 + (i % 5) * 5.4, -13.0 - (i // 5) * 0.8), 0.5, 0.4, fc=c, ec="none"))
    ax.text(-13.1 + (i % 5) * 5.4, -12.8 - (i // 5) * 0.8, t, color=TXT, fontsize=8.5, va="center")
fig.savefig(HERE / "u575-pin-map.svg", bbox_inches="tight")
plt.close(fig)

# matplotlib writes width/height in pt but the viewBox in pt units too; render.sh sizes the window from the viewBox, so make
# the root size px == viewBox (otherwise Chromium crops the screenshot)
for n in ("u575-clock-tree", "u575-pin-map"):
    f = HERE / f"{n}.svg"
    t = f.read_text()
    vb = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', t)
    t = re.sub(r'width="[\d.]+pt" height="[\d.]+pt"', f'width="{vb[1]}" height="{vb[2]}"', t, count=1)
    f.write_text(t)
