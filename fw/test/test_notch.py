"""SAI-13 mic-port notch (fw/variants.yaml mic_notch, fw/tools/dsp_tables.py): K4 cut is -10.8 dB at 44.4 kHz and flat at 26 kHz.
Run: python3 fw/test/test_notch.py (exit 0 = pass). Also checks the committed fw/gen header carries the active design's constants."""
import math, os, re, sys
from pathlib import Path
FW = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(FW / "tools"))
os.environ["ULTRASONIC_DESIGN"] = "k4"
import dsp_tables as dt                                              # noqa: E402

def db(p): return 10 * math.log10(float(p))

n = dt.mic_notch()
assert n["design"] == "k4" and n["f0_hz"] == 44400.0, n
at_f0 = db(dt.notch_power(44400.0, n["f0_hz"], n["q"], n["depth_db"]))
at_26 = db(dt.notch_power(26000.0, n["f0_hz"], n["q"], n["depth_db"]))
at_63 = db(dt.notch_power(63000.0, n["f0_hz"], n["q"], n["depth_db"]))
print(f"K4 notch: 44.4 kHz {at_f0:+.3f} dB (want -{n['depth_db']}), 26 kHz {at_26:+.3f} dB, 63 kHz {at_63:+.3f} dB")
assert abs(at_f0 + n["depth_db"]) < 0.05
assert abs(at_26) < 0.5 and abs(at_63) < 1.5
os.environ["ULTRASONIC_DESIGN"] = ""
r2 = dt.mic_notch(); assert r2["design"] == "r2" and r2["f0_hz"] == 63000.0
hdr = (FW / "gen/dsp_tables.h").read_text()
m = float(re.search(r"FW_DSP_NOTCH_F0_HZ ([\d.]+)f", hdr).group(1))
assert m in (44400.0, 63000.0), m
print("test_notch: PASS")
