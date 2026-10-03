"""Print the headline numbers of the last acoustics run (reads sim/acoustics/out/*.json; no computation)."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "out"
sc = json.loads((OUT / "selfcheck.json").read_text())
p = json.loads((OUT / "port_results.json").read_text())
b = json.loads((OUT / "bone_results.json").read_text())
print("selfcheck", sc["verdict"], "wall", sc["wall_s"], "s")
print("board", p["geometry_info"].get("board_file"), "| port offset", p["geometry"]["offset"], "mm | warnings", p["warnings"])
for n in ("as_built", "as_built_channel", "chimney_d1.0", "gasket_id2.1", "size_s1", "size_s2"):
    s = p["scenarios"][n]
    f = s["feat"]
    mc = p["mc_summary"].get(n, {}).get("mean_20_96_db")
    pk = ", ".join(f"{x['f_hz'] / 1e3:.1f}k {x['db']:+.1f}dB Q{x['q']}" for x in s["peaks"][:4])
    print(f"{n:17s} mean {f['mean_20_96_db']:+6.1f} dB" + (f" (MC p05..p95 {mc['p05']:+.1f}..{mc['p95']:+.1f})" if mc else "")
          + f" | deepest {f['min_20_96_db']:+.1f} @ {f['f_min_hz'] / 1e3:.1f} kHz | ratio peaks: {pk}")
for r in p["sweeps"]["quarter_wave"]:
    print(f"quarter-wave L {r['L_mm']} mm: c/4L {r['c_over_4L_khz']} kHz | model resonances (abs, re 1 kHz):",
          [(x["f_khz"], x["db_re_1k"], x["q"]) for x in r["abs_peaks"][:3]])
for fk in ("1500Hz", "2500Hz", "4000Hz"):
    h = b["headline_per_volt"][fk]
    print(f"bone {fk}, 1 V rms bridge drive: {h['F_per_V_mN']:.1f} mN rms ({h['F_level_db_re_1uN_per_V']:.1f} dB re 1 uN); "
          f"5-95 % {h['p05']:.1f}..{h['p95']:.1f}; min-max {h['min']:.1f}..{h['max']:.1f}; V_terminal at threshold {h['V_terminal_at_threshold_mV_measured_nom']:.2f} mV")
t = b["t6_shaped_noise"]
print("T6 shaped PWM noise, max SL per ERB 1.5-4 kHz: front-thr nominal", t["SL_max_measured_front_nominal_1.5_4k"]["db"],
      "dB | norm-20 thr, loudest-5 % exciter", t["SL_max_norm_minus20_p95_1.5_4k"]["db"], "dB")
