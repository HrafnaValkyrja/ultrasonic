#!/usr/bin/env python3
"""sim/fw/awake.py: awake fraction of the firmware with the idle detector driving IDLE (spec C9), on the sim/e2e scenes, for the runtime
model (sim/checks/runtime_fw.py). Each scene: sim/e2e sources -> acoustic path, mic, supply, ADF D1 stub -> ADF words -> host firmware
(Transient mode, idle_enable 1, powered on 1 s before the scene). awake = hops not in IDLE (full chain running); IDLE = detector only.
Also checks the firmware detector against the reference pipeline.idle_detector_fft (hop 5.12 ms) on the same PCM: active fractions.
    python3 sim/fw/awake.py [--json PATH]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path[:0] = [str(HERE), str(REPO / "sim/e2e"), str(REPO / "sim/dsp")]
import chain as ch  # noqa: E402
import fwlib  # noqa: E402
import gen_vectors as gv  # noqa: E402
import pipeline as pl  # noqa: E402
import stages as sg  # noqa: E402

IDLE = 3   # FW_ST_IDLE (fw/gen/fsm_table.h order: OFF, FULL, TRANSIENT, IDLE, ...)


def scenes():
    x2, _ = ch.port_meadow_tiled(8.0)
    src2 = "port_meadow" if x2 is not None else "synthetic bats"
    if x2 is None:
        x2 = ch.bats(8.0, 2)[0]
    return {
        "T1_house_walk": (ch.house_walk(2.0, 1, 6.0)[0], 1, "electronics: HC-SR04 bursts, keys, whines, speech"),
        "T2_bats": (x2, 2, src2),
        "R15_self_noise": (ch.self_noise(4.0, 8, 6.0)[0], 8, "own speech/chewing/hair only (levels assumed)"),
        "T6_silence": (np.zeros(int(10.0 * ch.FS)), 4, "quiet room: mic self-noise only"),
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", type=Path, default=REPO / "sim/out/fw/awake.json")
    a = ap.parse_args(argv)
    res = {}
    for name, (src, seed, what) in scenes().items():
        words = gv.front(src, seed, "D1")
        words = words[: len(words) // 128 * 128]
        fw = fwlib.Firmware({"algo": 2, "transient_only": 1, "idle_enable": 1})
        r = fw.run(words, t0_us=1_000_000)
        mode = r["mode"] & 0xFF
        act = (r["mode"] >> 8) & 1
        skip = int(3.0 / 0.00064)                        # after the 3 s floors settle
        awake = float(np.mean(mode[skip:] != IDLE))
        pcm = sg.adf_words_to_pcm(words)
        ref_act, ref_frac, _ = pl.idle_detector_fft(pcm, hop_ms=5.12)
        snap = act[7::8]                                 # firmware snapshots every 8 hops
        k = int(3.0 / 0.00512)
        res[name] = {"what": what, "seconds": round(len(words) / 200000, 1), "awake_frac_after_3s": round(awake, 3),
                     "fw_detector_active_frac": round(float(np.mean(snap[k:])), 3), "ref_detector_active_frac": round(float(np.mean(ref_act[k:])), 3),
                     "idle_entries": int(np.sum((mode[1:] == IDLE) & (mode[:-1] != IDLE)))}
        print(name, res[name])
    a.json.parent.mkdir(parents=True, exist_ok=True)
    a.json.write_text(json.dumps(res, indent=1) + "\n")


if __name__ == "__main__":
    main()
