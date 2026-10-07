#!/usr/bin/env python3
"""fw/tools/lint.py: static rules of the firmware tree (FWSIM-R1, FWSIM-R2). Exit 1 on any violation.

  includes   fw/core (and fw/hal) include only: fw/hal headers, other fw/core headers, fw/gen headers, and the C library
             headers the determinism rules allow (stdint, stddef, stdbool, string, math). Never a CMSIS / ST / vendor header.
  addresses  no absolute-address constant in fw/core, fw/hal, fw/gen: no integer literal cast to a pointer, no 8-digit hex
             literal inside a Cortex-M33 / STM32U5 address range (flash, SRAM, peripherals, system ROM, PPB). A data table may
             mark a line `fwlint:data` (CRC polynomials look like addresses).
  hal        the HAL surface: every function declared in fw/hal/hal_*.h is defined in fw/port_host/fake.c AND fw/port_u575,
             and listed once in FAKE_HAL_FUNCS (fw/port_host/fake.h); nothing extra is listed.
  python3 fw/tools/lint.py [--json out.json]
"""
import argparse
import json
import re
import sys
from pathlib import Path

FW = Path(__file__).resolve().parents[1]
ALLOWED_SYS = {"stdint.h", "stddef.h", "stdbool.h", "string.h", "math.h"}
# address ranges (inclusive) of the STM32U575 / Cortex-M33 memory map, RM0456 Rev 7 memory map (non-secure + secure aliases)
RANGES = [(0x0800_0000, 0x0FFF_FFFF, "flash / system memory / OTP"), (0x2000_0000, 0x3FFF_FFFF, "SRAM (+ secure alias)"),
          (0x4000_0000, 0x5FFF_FFFF, "peripherals (+ secure alias)"), (0xE000_0000, 0xE00F_FFFF, "Cortex-M33 private peripheral bus")]
HEX8 = re.compile(r"\b0[xX]([0-9A-Fa-f]{8})[uUlL]*\b")
PTR_CAST = re.compile(r"\(\s*(?:const\s+)?(?:volatile\s+)?[A-Za-z_]\w*(?:\s+\w+)*\s*\*+\s*\)\s*\(?\s*(?:0[xX][0-9A-Fa-f]+|\d{4,})")
INCLUDE = re.compile(r'^\s*#\s*include\s*([<"])([^>"]+)[>"]', re.M)
PROTO = re.compile(r"^[A-Za-z_][\w \t\*]*?\b(hal_\w+)\s*\(", re.M)


def strip_comments(text):
    return re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), re.sub(r"//[^\n]*", "", text), flags=re.S)


def lint_includes(errs):
    local = {p.name for d in ("core", "hal", "gen") for p in (FW / d).glob("*.h")}
    for d in ("core", "hal"):
        for f in sorted((FW / d).glob("*.[ch]")):
            for kind, name in INCLUDE.findall(f.read_text()):
                base = Path(name).name
                ok = base in ALLOWED_SYS if kind == "<" else base in local and "/" not in name
                if not ok:
                    errs.append(f"includes: {f.relative_to(FW.parent)} includes {kind}{name}{'>' if kind == '<' else chr(34)}: core/hal may include only fw/hal, fw/core, fw/gen headers and {sorted(ALLOWED_SYS)}")


def lint_addresses(errs):
    for d in ("core", "hal", "gen"):
        for f in sorted((FW / d).glob("*.[ch]")):
            raw = f.read_text().splitlines()
            code = strip_comments(f.read_text()).splitlines()
            for n, line in enumerate(code, 1):
                if "fwlint:data" in raw[n - 1]:
                    continue
                if PTR_CAST.search(line):
                    errs.append(f"addresses: {f.relative_to(FW.parent)}:{n}: integer literal cast to a pointer (register access belongs in fw/port_u575)")
                for h in HEX8.findall(line):
                    v = int(h, 16)
                    for lo, hi, what in RANGES:
                        if lo <= v <= hi:
                            errs.append(f"addresses: {f.relative_to(FW.parent)}:{n}: 0x{h} lies in the {what} range")


def hal_surface():
    names = []
    for f in sorted((FW / "hal").glob("hal_*.h")):
        names += PROTO.findall(strip_comments(f.read_text()))
    return names


def defined(path):
    text = strip_comments("".join(p.read_text() for p in path)) if isinstance(path, list) else strip_comments(path.read_text())
    return set(re.findall(r"^[A-Za-z_][\w \t\*]*?\b(hal_\w+)\s*\([^;{]*\)\s*\{", text, re.M))


def lint_hal(errs):
    surface = hal_surface()
    dup = sorted({n for n in surface if surface.count(n) > 1})
    if dup:
        errs.append(f"hal: declared twice: {dup}")
    fake_h = (FW / "port_host/fake.h").read_text()
    listed = re.findall(r"X\((hal_\w+)\)", fake_h)
    for n in sorted(set(surface) - set(listed)):
        errs.append(f"hal: {n} is not in FAKE_HAL_FUNCS (fw/port_host/fake.h): no fake, no coverage test")
    for n in sorted(set(listed) - set(surface)):
        errs.append(f"hal: FAKE_HAL_FUNCS lists {n}, which no fw/hal header declares")
    for port, files in (("port_host", [FW / "port_host/fake.c"]), ("port_u575", sorted((FW / "port_u575").rglob("*.c")))):
        have = defined(files)
        for n in sorted(set(surface) - have):
            errs.append(f"hal: {n} has no definition in fw/{port}")
    return surface


def selftest():
    """Negative controls: a copy of the tree with planted violations must fail every rule."""
    import shutil
    import tempfile
    global FW
    real = FW
    with tempfile.TemporaryDirectory() as tmp:
        FW = Path(tmp) / "fw"
        for d in ("core", "hal", "gen", "port_host", "port_u575"):
            shutil.copytree(real / d, FW / d)
        (FW / "core/zz_bad.c").write_text('#include "stm32u5xx.h"\n#include <stdlib.h>\nstatic volatile int *p = (volatile int *)0x40021000u;\n')
        (FW / "hal/hal_zz.h").write_text("int hal_zz_new(void);\n")
        errs = []
        lint_includes(errs)
        lint_addresses(errs)
        lint_hal(errs)
        FW = real
    want = ["stm32u5xx.h", "<stdlib.h", "cast to a pointer", "0x40021000", "hal_zz_new is not in FAKE_HAL_FUNCS", "hal_zz_new has no definition in fw/port_host",
            "hal_zz_new has no definition in fw/port_u575"]
    return [w for w in want if not any(w in e for e in errs)]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", type=Path)
    a = ap.parse_args(argv)
    errs = []
    missed = selftest()
    if missed:
        errs.append(f"selftest: planted violations not caught: {missed}")
    lint_includes(errs)
    lint_addresses(errs)
    surface = lint_hal(errs)
    row = {"errors": errs, "hal_functions": len(surface), "hal_surface": surface}
    if a.json:
        a.json.write_text(json.dumps(row, indent=2) + "\n")
    for e in errs:
        print("FAIL " + e)
    print(f"lint: {len(errs)} violation(s); HAL surface {len(surface)} functions")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
