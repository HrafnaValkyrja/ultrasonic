#!/usr/bin/env python3
"""fw/bench/budget.py - turn the static kernel counts (out/cycles.json) into per-scenario MHz needed
and % of the B1 (55 MHz, Range 3) and B3 (24 MHz, Range 4) clock budgets. ESTIMATE, not measurement.

Memory timing (RM0456 Rev 7, March 2026, local text, read 2026-10-07):
  Table 47 SRAM wait states: 0 WS up to 55 MHz in Range 3; Range 4: 0 WS <= 16 MHz, 1 WS <= 25 MHz.
  Table 54 flash: Range 3 <= 55 MHz 2 WS; Range 4 <= 25 MHz 1 WS. ICACHE: 0 WS on hits.
  => 55 MHz: +0 per data access; 24 MHz: +1 cycle per SRAM data access (counted words, 'mem').
  Code assumed resident in the 8 KB ICACHE (all kernels together < 3.5 KB); cold-refill envelope
  printed separately.
Overhead (assumption): fixed 0.5 MHz (ADF + TIM1 DMA ISRs ~2 x 100 cyc/hop, SysTick 1 kHz, kernel
  calls ~100 cyc/hop) + 3 % (lo) / 8 % (hi) for DMA bus contention and stray ICACHE misses. USB is
  off while worn (VBUS absent, FWSIM-R28).
Verdict (FWSIM-R48 margin rule): fits if hi <= 80 % of the clock; doesn't fit if lo > 85 %;
  otherwise tight.
"""
import json
import sys

HOPS = 200.02e3 / 128                  # 1562.65 hops/s; PCM kept at ~200 kS/s at every clock (assumption)
CMSIS_RFFT256 = (14285, 16534)         # f32 256-pt real FFT on Cortex-M4F: Lorenser 2016 (ARM white paper) /
                                       # Stenzel FFT4CM4F on STM32F446 (via docs/research/C2-cpu-budget.md, 2026-09-30)
FIXED_MHZ = 0.5
OVH = (0.03, 0.08)
BUDGETS = {"B1_55MHz_R3": (55.0, 0), "B3_24MHz_R4": (24.0, 1)}   # clock, SRAM wait states


def k(c, var, name, ws):
    d = c[var]["kernels"][name]
    return d["lo"] + ws * d["mem"], d["hi"] + ws * d["mem"]


def fft(c, var, ws, which):
    own = [k(c, var, n, ws) for n in ("bitrev128", "cfft128", "rsplit256")]
    lo, hi = sum(o[0] for o in own), sum(o[1] for o in own)
    if which == "own":
        return lo, hi
    mem = sum(c[var]["kernels"][n]["mem"] for n in ("bitrev128", "cfft128", "rsplit256"))
    return CMSIS_RFFT256[0] + ws * mem, CMSIS_RFFT256[1] + ws * mem   # own access count as WS proxy (upper)


def add(*xs):
    return sum(x[0] for x in xs), sum(x[1] for x in xs)


def scale(x, f):
    return x[0] * f, x[1] * f


def scenarios(c, ws):
    def B(frame_var, out_var, fftk, frames_per_hop):
        frame = add(k(c, frame_var, "in_window", ws), fft(c, frame_var, ws, fftk),
                    k(c, frame_var, "b_bands", ws), k(c, frame_var, "b_update", ws))
        return add(scale(frame, frames_per_hop), k(c, frame_var, "b_synth", ws), k(c, out_var, "out_hop", ws))

    def A(out_var):
        return add(k(c, "base", "a_mix", ws), k(c, "base", "a_decim", ws), k(c, "base", "a_post", ws),
                   k(c, out_var, "out_hop", ws))

    def Aq(out_var):
        return add(k(c, "base", "a_mix_q15", ws), k(c, "base", "a_decim_q15", ws), k(c, "base", "a_post", ws),
                   k(c, out_var, "out_hop_q15", ws))

    def Bq(frame_var, out_var, frames_per_hop):
        frame = add(k(c, frame_var, "in_window", ws), fft(c, frame_var, ws, "cmsis"),
                    k(c, frame_var, "b_bands", ws), k(c, frame_var, "b_update", ws))
        return add(scale(frame, frames_per_hop), k(c, frame_var, "b_synth", ws), k(c, out_var, "out_hop_q15", ws))

    return {
        "B_spec_ownFFT (32 bands, hop 128, TPP 8, own radix-2 FFT)": B("base", "base", "own", 1.0),
        "B_spec_cmsisFFT (32 bands, hop 128, TPP 8, CMSIS f32 FFT)": B("base", "base", "cmsis", 1.0),
        "B_28bands_cmsisFFT (28 bands = pipeline.py default)": B("b28", "base", "cmsis", 1.0),
        "B_slim1 (16 bands, hop 256 = no overlap, TPP 8, CMSIS FFT)": B("slim", "base", "cmsis", 0.5),
        "B_slim2 (16 bands, hop 256, TPP 4 [23 dB images], CMSIS FFT)": B("slim", "slim", "cmsis", 0.5),
        "A_spec (mix + 16/40-tap decimators + HP + squelch, TPP 8)": A("base"),
        "A_slim (TPP 4 [23 dB images])": A("slim"),
        "A_hq (TPP 12 [58 dB images])": A("hq"),
        "B_q15out (32 bands, hop 128, CMSIS FFT, q15 output path TPP 8)": Bq("base", "base", 1.0),
        "B_slim1_q15out (16 bands, hop 256, CMSIS FFT, q15 output TPP 8)": Bq("slim", "base", 0.5),
        "A_q15 (q15 mix + SMLAD decimators, float HP/squelch, q15 output TPP 8)": Aq("base"),
        "A_q15_hq (as A_q15, q15 output TPP 12 [58 dB images])": Aq("hq"),
        "out_only_q15_TPP8": k(c, "base", "out_hop_q15", ws),
        "out_only_q15_TPP12": k(c, "hq", "out_hop_q15", ws),
        "out_only_TPP8 (x16 interp + limiter + 3rd-order shaper)": k(c, "base", "out_hop", ws),
        "out_only_TPP4": k(c, "slim", "out_hop", ws),
        "out_only_TPP12": k(c, "hq", "out_hop", ws),
        "D2_halfband_addon (only if ADF D1 is not used)": k(c, "base", "halfband_d2", ws),
    }


def mhz(cyc):
    return (cyc[0] * HOPS * (1 + OVH[0]) / 1e6 + FIXED_MHZ, cyc[1] * HOPS * (1 + OVH[1]) / 1e6 + FIXED_MHZ)


def verdict(lo_pct, hi_pct):
    if hi_pct <= 80:
        return "fits"
    if lo_pct > 85:
        return "doesn't fit"
    return "tight"


if __name__ == "__main__":
    c = json.load(open(sys.argv[1]))
    code = sum(v["code_bytes"] for v in c["base"]["kernels"].values())
    out = {}
    for bname, (clk, ws) in BUDGETS.items():
        print(f"== {bname}: SRAM {ws} WS; overhead {FIXED_MHZ} MHz + {OVH[0]*100:.0f}-{OVH[1]*100:.0f} %")
        for sname, cyc in scenarios(c, ws).items():
            m = mhz(cyc) if not sname.startswith(("out_only", "D2")) else (cyc[0] * HOPS / 1e6, cyc[1] * HOPS / 1e6)
            p = (100 * m[0] / clk, 100 * m[1] / clk)
            v = verdict(*p) if not sname.startswith(("out_only", "D2")) else "-"
            out.setdefault(sname, {})[bname] = {"cyc_hop": [round(cyc[0]), round(cyc[1])],
                                                "MHz": [round(m[0], 1), round(m[1], 1)],
                                                "pct": [round(p[0]), round(p[1])], "verdict": v}
            print(f"  {sname:66s} {cyc[0]:7.0f}-{cyc[1]:7.0f} cyc/hop  {m[0]:5.1f}-{m[1]:5.1f} MHz  {p[0]:4.0f}-{p[1]:4.0f} %  {v}")
    for clk_name, ws_flash in (("55 MHz", 2), ("24 MHz", 1)):
        lines = code / 16
        cold = lines * 4 * (1 + ws_flash) * HOPS / 1e6
        print(f"cold-ICACHE envelope at {clk_name}: all {code} B of kernel code refilled every hop "
              f"({lines:.0f} lines x 4 words x {1+ws_flash} cyc) = +{cold:.1f} MHz (worst case; warm cache = 0)")
    json.dump(out, open(sys.argv[1].replace("cycles.json", "budget.json"), "w"), indent=1)
