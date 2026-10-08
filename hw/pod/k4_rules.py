"""Persist the JLC 6-layer design rules (place_k4.fine_rules + route clearance 0.09) into routed_P/M.kicad_pro, so a plain
`kicad-cli pcb drc` (and the fab release) checks the boards against the rules they were routed to. Without the .kicad_pro,
kicad-cli falls back to KiCad defaults (0.2 clearance) and reports ~1000 false violations (found 2026-10-08).

    source tools/env.sh && python3 hw/pod/k4_rules.py
"""
import sys
from pathlib import Path

import pcbnew

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import place_k4 as K  # noqa: E402

for bd in "PM":
    p = HERE / "k4" / f"routed_{bd}.kicad_pcb"
    b = pcbnew.LoadBoard(str(p))
    K.fine_rules(b)
    b.GetDesignSettings().m_NetSettings.GetDefaultNetclass().SetClearance(pcbnew.FromMM(0.09))
    pcbnew.SaveBoard(str(p), b)
    print(bd, (p.with_suffix(".kicad_pro")).exists())
