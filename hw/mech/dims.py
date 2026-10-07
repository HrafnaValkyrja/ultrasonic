"""The SELECTED design's CAD-free dims module (hw/current.yaml `shell_dims` via tools/current.py; 2026-10-07).

    import dims as D          # phase2 -> dims_r2; ULTRASONIC_DESIGN=k1/k1p -> dims_k1; revg -> dims_r2 (r1 has no dims module)

Tools that used `import dims_r2 as D` import this instead, so a variant (K1) runs through the same checks.
"""
import importlib
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
for _p in (_HERE, _HERE.parents[1] / "tools"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
from current import current  # noqa: E402

DESIGN = current()
_path = DESIGN.shell_dims
MODULE = _path.stem if _path.stem.startswith("dims_") else "dims_r2"
_m = importlib.import_module(MODULE)
globals().update({k: v for k, v in vars(_m).items() if not k.startswith("__")})
OUT_DIR = DESIGN.shell_out.with_name(DESIGN.shell_out.name + getattr(_m, "OUT_TAG", ""))   # phase2: out/r2; k1 + K1_DUCT=x: out/k1_x
