#!/usr/bin/env python3
"""fw/tools/fwsim.py: the firmware gate (FWSIM-R51 entry; this foundation runs the tier S + H stages).

  source tools/env.sh
  systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 python3 fw/tools/fwsim.py all

Stages (each a row in fw/out/summary.json, schema {id, op, thr, last, status, basis, src} as sim/e2e metrics):
  gen        fw/gen is what fw/tools/gen.py makes now (pins gate: interfaces [pins] must not FAIL)       FWSIM-R5
  lint       include / absolute-address / HAL-surface rules, with planted-violation self-test            FWSIM-R1, R2
  host_gcc   gcc 15, strict warnings -Werror, host tests                                                 FWSIM-R1, R11
  host_clang clang-18, same                                                                              FWSIM-R1, R11
  asan_ubsan gcc ASan+UBSan, host tests, no recover                                                      FWSIM-R11
  msan       clang-18 MSan (uninitialised reads), host tests                                             FWSIM-R11
  analyzer   gcc -fanalyzer on core + port_host, -Werror                                                 FWSIM-R11
  variants   every fw/variants.yaml matrix row: host build + tests, ARM build                            FWSIM-R5, R64
  arm        arm-none-eabi-gcc Cortex-M33 ELF from the SAME core sources; size                           FWSIM-R1
  no_malloc  no allocator symbol in the ARM ELF or in core/port objects; no libm transcendental in core  FWSIM-R11, R4 (part)
  stack      worst-case stack from -fstack-usage + -fcallgraph-info <= 50 % of the linker stack region   FWSIM-R11
  dsp        golden vectors sha-pinned (R8), L1 vs sim/dsp per variant (R7, R13), L0 gcc/clang/-O0 bit-exact (R7),
             ceiling property 1.36e6 hops (R15), static cycles_hop per variant (R10, R47),
             L0 ARM (QEMU mps2-an505 Cortex-M33) vs host bit-exact                                       FWSIM-R7, R8, R13, R15
Exit 0 only if every row is PASS.  Subcommands: all | host | arm | lint | gen  (host/arm/lint/gen run a subset).
"""
import argparse
import concurrent.futures as cf
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import yaml

FW = Path(__file__).resolve().parents[1]
REPO = FW.parent
OUT = FW / "out"
REL = lambda p: str(Path(p).relative_to(REPO))  # noqa: E731

CORE = sorted((FW / "core").glob("*.c"))
HOST_PORT = sorted((FW / "port_host").glob("*.c"))
TESTS = sorted((FW / "test").glob("*.c"))
ARM_PORT = sorted((FW / "port_u575").glob("*.c"))
LD = FW / "port_u575/u575.ld"
INC = [f"-I{FW / d}" for d in ("hal", "core", "gen")]
INC_HOST = INC + [f"-I{FW / 'port_host'}", f"-I{FW / 'test'}"]
WARN = ["-Wall", "-Wextra", "-Wconversion", "-Wshadow", "-Wdouble-promotion", "-Werror"]
HOST_FLAGS = ["-std=c11", "-O2", "-msse2", "-mfpmath=sse", "-mno-fma", "-ffp-contract=off", "-fexcess-precision=standard", "-fno-math-errno"]
ARM_FLAGS = ["-std=c11", "-O2", "-mcpu=cortex-m33", "-mthumb", "-mfloat-abi=hard", "-mfpu=fpv5-sp-d16", "-ffp-contract=off", "-fno-math-errno",
             "-fno-tree-loop-distribute-patterns", "-ffunction-sections", "-fdata-sections"]
ARM_LINK = ["-T", str(LD), "-nostartfiles", "--specs=nano.specs", "-Wl,--gc-sections"]
GCC, CLANG, ARMCC = "gcc", "clang-18", "arm-none-eabi-gcc"
ALLOC_SYMS = {"malloc", "calloc", "realloc", "free", "_malloc_r", "_free_r", "_calloc_r", "_realloc_r", "_sbrk", "_sbrk_r", "aligned_alloc", "posix_memalign"}
TRANSCENDENTALS = {f + s for f in ("sin", "cos", "tan", "exp", "exp2", "log", "log2", "log10", "pow", "atan", "atan2", "tanh", "sinh", "cosh", "asin", "acos") for s in ("", "f")}
STACK_FRACTION_MAX = 0.50
EXC_FRAME_BYTES = 104   # Cortex-M33 extended (FPU) exception frame: 26 words


def run(cmd, timeout=300, env=None):
    t0 = time.monotonic()
    p = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, timeout=timeout, env=env)
    return p.returncode, p.stdout, p.stderr, time.monotonic() - t0


def row(rid, status, last, thr, op="==", basis="", src="", detail=None, wall=None):
    r = {"id": rid, "op": op, "thr": thr, "last": last, "status": status, "basis": basis, "src": src}
    if detail:
        r["detail"] = detail
    if wall is not None:
        r["wall_s"] = round(wall, 2)
    return r


def tail(text, n=12):
    return "\n".join(text.strip().splitlines()[-n:])


# ------------------------------------------------------------------------------------------- host builds + tests
def host_build_and_test(name, cc, flags, defines=(), env=None, req="FWSIM-R1, FWSIM-R11"):
    d = OUT / name
    d.mkdir(parents=True, exist_ok=True)
    exe = d / "fw_tests"
    rc, so, se, w1 = run([cc, *flags, *WARN, *defines, *INC_HOST, *CORE, *HOST_PORT, *TESTS, "-lm", "-o", exe])
    if rc != 0:
        return row(f"{name}.build", "FAIL", "error", "clean", basis="compile+link -Werror", src=req, detail=tail(se), wall=w1), None
    rc, so, se, w2 = run([exe], timeout=600, env=env)
    lines = [json.loads(x) for x in so.splitlines() if x.startswith("{")]
    tests = [x for x in lines if "test" in x]
    total = next((x for x in lines if "total_checks" in x), {"total_checks": 0, "total_fails": -1, "tests_failed": -1})
    ok = rc == 0 and total["tests_failed"] == 0 and tests
    detail = None if ok else tail(se + "\n" + so, 20)
    return (row(f"{name}.tests", "PASS" if ok else "FAIL", f"{len(tests) - total['tests_failed']}/{len(tests)} tests, {total['total_checks']} checks",
                "all pass", basis=f"{cc} {' '.join(flags[:3])}... {' '.join(defines)}".strip(), src=req, detail=detail, wall=w1 + w2), tests)


def stage_host(cfg):
    jobs = {
        "host_gcc": (GCC, HOST_FLAGS, (), None),
        "host_clang": (CLANG, HOST_FLAGS, (), None),
        "asan_ubsan": (GCC, ["-std=c11", "-O1", "-g", "-fno-omit-frame-pointer", "-fsanitize=address,undefined", "-fno-sanitize-recover=all"], (),
                       dict(os.environ, ASAN_OPTIONS="detect_leaks=1:abort_on_error=1", UBSAN_OPTIONS="print_stacktrace=1:halt_on_error=1")),
        "msan": (CLANG, ["-std=c11", "-O1", "-g", "-fno-omit-frame-pointer", "-fsanitize=memory", "-fsanitize-memory-track-origins=2"], (), None),
    }
    rows, tests = [], {}
    with cf.ThreadPoolExecutor(max_workers=cfg.jobs) as ex:
        futs = {ex.submit(host_build_and_test, n, *j): n for n, j in jobs.items()}
        for f in cf.as_completed(futs):
            r, t = f.result()
            rows.append(r)
            if t:
                tests[futs[f]] = t
    rows.append(stage_analyzer())
    return sorted(rows, key=lambda r: r["id"]), tests


def stage_analyzer():
    d = OUT / "analyzer"
    d.mkdir(parents=True, exist_ok=True)
    errs, wall = [], 0.0
    for src in CORE + HOST_PORT:
        rc, _, se, w = run([GCC, "-std=c11", "-O1", "-fanalyzer", *WARN, *INC_HOST, "-c", src, "-o", d / (src.stem + ".o")])
        wall += w
        if rc != 0:
            errs.append(f"{REL(src)}: {tail(se, 6)}")
    return row("analyzer", "PASS" if not errs else "FAIL", f"{len(errs)} file(s) with findings / {len(CORE + HOST_PORT)}", 0, basis="gcc -fanalyzer -Werror (core + port_host)",
               src="FWSIM-R11", detail="\n".join(errs) or None, wall=wall)


# ------------------------------------------------------------------------------------------- ARM build, sizes, stack
def arm_build(name, defines=(), stack=False):
    d = OUT / name
    if d.exists():
        shutil.rmtree(d)
    (d / "obj").mkdir(parents=True)
    objs, errs, wall = [], [], 0.0
    extra = ["-fstack-usage", "-fcallgraph-info=su"] if stack else []
    for src in CORE + ARM_PORT:
        o = d / "obj" / f"{src.parent.name}_{src.stem}.o"
        rc, _, se, w = run([ARMCC, *ARM_FLAGS, *WARN, *defines, *INC, *extra, "-c", src, "-o", o])
        wall += w
        objs.append(o)
        if rc != 0:
            errs.append(f"{REL(src)}: {tail(se, 8)}")
    if errs:
        return {"ok": False, "err": "\n".join(errs), "wall": wall}
    elf = d / "fw.elf"
    rc, _, se, w = run([ARMCC, *ARM_FLAGS, *objs, *ARM_LINK, f"-Wl,-Map={d / 'fw.map'}", "-o", elf])
    wall += w
    if rc != 0:
        return {"ok": False, "err": tail(se), "wall": wall}
    _, so, _, _ = run(["arm-none-eabi-size", "-A", elf])
    sec = {m[1]: int(m[2]) for m in re.finditer(r"^(\.\S+)\s+(\d+)\s+\d+", so, re.M)}
    flash = sum(sec.get(s, 0) for s in (".isr_vector", ".text", ".ARM.exidx", ".data"))
    ram = sum(sec.get(s, 0) for s in (".data", ".bss", ".noinit"))
    return {"ok": True, "elf": elf, "dir": d, "objs": objs, "flash": flash, "ram_static": ram, "stack_region": sec.get(".stack", 0), "sections": sec, "wall": wall}


def stage_arm(cfg):
    b = arm_build("arm", stack=True)
    if not b["ok"]:
        return [row("arm.build", "FAIL", "error", "clean", basis="arm-none-eabi-gcc -Werror", src="FWSIM-R1", detail=b["err"], wall=b["wall"])], b
    rows = [row("arm.build", "PASS", f"flash {b['flash']} B, RAM static {b['ram_static']} B + stack {b['stack_region']} B", "builds", op="",
                basis="arm-none-eabi-gcc 14.2 -mcpu=cortex-m33 -mfloat-abi=hard -O2, same core sources as host", src="FWSIM-R1", wall=b["wall"])]
    rows.append(stage_stack(b))
    return rows, b


def callgraph(dirpath):
    """{fn: own stack bytes}, {fn: set(callees)}, set(fns with dynamic/unbounded stack) from .ci (VCG) files."""
    own, edges, dyn = {}, {}, set()
    for ci in sorted(Path(dirpath).glob("*.ci")):
        text = ci.read_text()
        text = text.replace(str(REPO) + "/", "")
        for m in re.finditer(r'node: \{ title: "([^"]+)" label: "([^"]*)"', text):
            name, label = m[1], m[2]
            s = re.search(r"\\n(\d+) bytes \((\w+(?:,\w+)*)\)", label)
            if s:
                own[name] = int(s[1])
                if "dynamic" in s[2]:
                    dyn.add(name)
        for m in re.finditer(r'edge: \{ sourcename: "([^"]+)" targetname: "([^"]+)"', text):
            edges.setdefault(m[1], set()).add(m[2])
    return own, edges, dyn


def worst_path(fn, own, edges, unknown, stack=()):
    if fn in stack:
        return float("inf"), [fn, "(recursion)"]
    if fn not in own:
        unknown.add(fn)
        return 64, [f"{fn}?"]                       # library leaf without stack info (memcpy, memset): 64 B allowance
    best, path = 0, []
    for c in sorted(edges.get(fn, ())):
        v, p = worst_path(c, own, edges, unknown, stack + (fn,))
        if v > best:
            best, path = v, p
    return own[fn] + best, [fn] + path


def stage_stack(b):
    own, edges, dyn = callgraph(b["dir"] / "obj")
    unknown = set()
    main_v, main_p = worst_path("Reset_Handler", own, edges, unknown)
    handlers = [n for n in own if n.endswith("_Handler") and n != "Reset_Handler"]
    isr_v, isr_p = max((worst_path(h, own, edges, unknown) for h in handlers), default=(0, []))
    worst = main_v + EXC_FRAME_BYTES + isr_v
    region = b["stack_region"]
    frac = worst / region if region else float("inf")
    indirect = sorted(n for n in edges if any("indirect" in c for c in edges[n]))
    ok = frac <= STACK_FRACTION_MAX and not dyn and worst != float("inf")
    detail = {"main_path": main_p, "main_bytes": main_v, "isr_path": isr_p, "isr_bytes": isr_v, "exception_frame": EXC_FRAME_BYTES,
              "dynamic_stack": sorted(dyn), "unknown_leaves_64B_each": sorted(unknown), "indirect_callers": indirect,
              "note": "one exception nesting level assumed (priorities not configured yet); indirect calls not followed"}
    return row("stack.worst_case_fraction", "PASS" if ok else "FAIL", round(frac, 4), STACK_FRACTION_MAX, op="<=",
               basis=f"{worst} B worst case / {region} B linker stack region (-fstack-usage + -fcallgraph-info=su)", src="FWSIM-R11", detail=detail)


# ------------------------------------------------------------------------------------------- symbol checks
def stage_symbols(arm):
    d = OUT / "nm_host"
    d.mkdir(parents=True, exist_ok=True)
    bad, core_und = [], set()
    for src in CORE + HOST_PORT:
        o = d / f"{src.parent.name}_{src.stem}.o"
        rc, _, se, _ = run([GCC, *HOST_FLAGS, *INC_HOST, "-c", src, "-o", o])
        if rc != 0:
            bad.append(f"{REL(src)} does not compile: {tail(se, 3)}")
            continue
        _, so, _, _ = run(["nm", "-u", o])
        und = {ln.split()[-1] for ln in so.splitlines() if ln.strip()}
        for s in und & ALLOC_SYMS:
            bad.append(f"{REL(src)} references {s}")
        if src in CORE:
            core_und |= und
            for s in und & TRANSCENDENTALS:
                bad.append(f"{REL(src)} calls libm {s} (determinism rules: tables, not transcendentals)")
    if arm.get("ok"):
        _, so, _, _ = run(["arm-none-eabi-nm", arm["elf"]])
        syms = {ln.split()[-1] for ln in so.splitlines() if ln.strip()}
        for s in syms & ALLOC_SYMS:
            bad.append(f"ARM ELF contains {s}")
        for s in syms & TRANSCENDENTALS:
            bad.append(f"ARM ELF contains libm {s}")
        for o in arm["objs"]:
            if o.name.startswith("core_"):
                _, so, _, _ = run(["arm-none-eabi-nm", "-u", o])
                for s in {ln.split()[-1] for ln in so.splitlines() if ln.strip()} & (ALLOC_SYMS | TRANSCENDENTALS):
                    bad.append(f"ARM {o.name} references {s}")
    else:
        bad.append("ARM ELF missing (arm stage failed)")
    return row("no_malloc_no_transcendentals", "PASS" if not bad else "FAIL", len(bad), 0, basis="nm -u on host core/port objects + arm-none-eabi-nm on the ELF and core objects",
               src="FWSIM-R11; determinism_rules (nm check)", detail="\n".join(bad) or {"core_external_symbols": sorted(core_und)})


# ------------------------------------------------------------------------------------------- variants
def stage_variants(cfg):
    v = yaml.safe_load((FW / "variants.yaml").read_text())
    rows = []

    def one(m):
        tag = f"{m['cell']}_{m['exemption']}"
        defs = (f"-DFW_CELL=FW_CELL_{m['cell']}", f"-DFW_SELFTEST_EXEMPTION=FW_EXEMPTION_{m['exemption']}")
        r, _ = host_build_and_test(f"var_{tag}", GCC, HOST_FLAGS, defs, req="FWSIM-R5, FWSIM-R64")
        a = arm_build(f"var_{tag}_arm", defs)
        ra = row(f"var_{tag}_arm.build", "PASS" if a["ok"] else "FAIL", f"flash {a.get('flash', '-')} B" if a["ok"] else "error", "builds", op="",
                 basis="arm-none-eabi-gcc " + " ".join(defs), src="FWSIM-R5", detail=None if a["ok"] else a["err"], wall=a["wall"])
        rows_ = [r, ra]
        if a["ok"]:   # FWSIM-R19: variant (b) has no exemption code at all (nm), variant (a) has it
            _, so, _, _ = run(["arm-none-eabi-nm", a["elf"]])
            has = "fw_selftest_hop" in so
            want = m["exemption"] == "a"
            rows_.append(row(f"var_{tag}_arm.selftest_symbol", "PASS" if has == want else "FAIL", "present" if has else "absent",
                             "present" if want else "absent", basis="arm-none-eabi-nm: fw_selftest_hop (ECR-0009 exemption path)", src="FWSIM-R19"))
        return rows_

    with cf.ThreadPoolExecutor(max_workers=cfg.jobs) as ex:
        for rs in ex.map(one, v["matrix"]):
            rows += rs
    return rows


# ------------------------------------------------------------------------------------------- dsp (group b)
def stage_dsp(cfg):
    rows = []
    j = OUT / "dsp_vectors.json"
    rc, so, se, w = run([sys.executable, REPO / "sim/fw/gen_vectors.py", "--json", j], timeout=900)
    res = json.loads(j.read_text()) if j.exists() and rc in (0, 1) else {"rows": []}
    by = {}
    for r in res["rows"]:
        if r["id"].startswith("L1."):
            by.setdefault("L1", []).append(r)
        else:
            rows.append(row(f"dsp.{r['id']}", r["status"], r["value"], r["thr"], op=r["op"], basis=r.get("basis", ""),
                            src="FWSIM-R8" if r["id"].startswith("R8") else "FWSIM-R7", detail=r.get("detail")))
    l1 = by.get("L1", [])
    bad = [f"{r['id']} {r['value']} {r['op']} {r['thr']}" for r in l1 if r["status"] != "PASS"]
    worst = {}
    for r in l1:
        m = r["id"].split(".")[-1]
        if m in ("dsp_out_err_db", "band_db_err_max", "squelch_agree"):
            worst[m] = r["value"] if m not in worst else (min(worst[m], r["value"]) if m == "squelch_agree" else max(worst[m], r["value"]))
    rows.append(row("dsp.L1", "PASS" if l1 and not bad else "FAIL", f"{len(l1) - len(bad)}/{len(l1)} within fw/test/l1_thresholds.yaml; worst {worst}",
                    "all", basis="sim/fw/gen_vectors.py: firmware host build vs sim/dsp/pipeline.py on 6 golden vectors x {B, slim, A}",
                    src="FWSIM-R7, FWSIM-R13", detail="\n".join(bad) or None, wall=w))
    if rc not in (0, 1) and not res["rows"]:
        rows.append(row("dsp.vectors", "FAIL", f"exit {rc}", "exit 0", src="FWSIM-R8", detail=tail(se + so, 15)))
    # L0 ARM vs host: product-flag ARM objects on QEMU mps2-an505 (Cortex-M33) vs the host build, every CCR word and tap
    j = OUT / "dsp_l0_arm.json"
    rc, so, se, w = run([sys.executable, REPO / "sim/fw/l0_arm.py", "--json", j], timeout=1800)
    if j.exists() and rc in (0, 1):
        r = json.loads(j.read_text())
        rows.append(row("dsp.L0.arm_qemu_vs_host", r["status"], f"{r['runs'] - len(r['mismatches'])}/{r['runs']} runs bit-exact ({r['qemu']})", "all bit-exact",
                        basis="sim/fw/l0_arm.py: fw/core (fwsim ARM_FLAGS) + fw/port_qemu on qemu-system-arm -M mps2-an505 (semihosting) vs sim/fw/fwlib host gcc",
                        src="FWSIM-R7, FWSIM-R4", detail="\n".join(r["mismatches"]) or None, wall=w))
    else:
        rows.append(row("dsp.L0.arm_qemu_vs_host", "FAIL", f"exit {rc}", "all bit-exact", src="FWSIM-R7", detail=tail(se + so, 15), wall=w))
    # FMAC model: C (fw/core/fmac_model.c, what host/QEMU run behind hal_fmac) == Python twin (sim/fw/fmac_model.py), bit-exact
    rc, so, se, w = run([sys.executable, REPO / "sim/fw/fmac_model.py", "--check"], timeout=600)
    rows.append(row("dsp.fmac_model_c_vs_py", "PASS" if rc == 0 else "FAIL", (so.strip().splitlines() or ["?"])[-1], "0 mismatches",
                    basis="200 random banks (taps 2-127, 1-16 phases, R 0-7, extremes incl. accumulator wrap and saturation)", src="FWSIM-R7, FWSIM-R47",
                    detail=None if rc == 0 else tail(se + so), wall=w))
    # A/B build option: CPU float interpolator (FW_INTERP_FMAC=0) passes the host tests too
    r_cpu, _ = host_build_and_test("host_gcc_interp_cpu", GCC, HOST_FLAGS, ("-DFW_INTERP_FMAC=0",), req="FWSIM-R13")
    rows.append(r_cpu)
    # U575 register layer vs RM0456 values (recorded-register fake; QEMU's mps2 has no STM32 peripherals)
    d = OUT / "port_regs"
    d.mkdir(parents=True, exist_ok=True)
    exe = d / "test_regs"
    rc, _, se, w = run([GCC, "-std=c11", "-O2", *WARN, "-DFW_REG_RECORD", *INC, f"-I{FW / 'port_u575'}", f"-I{FW / 'test/port'}",
                        FW / "port_u575/hal_u575_periph.c", *sorted((FW / "test/port").glob("*.c")), "-o", exe])
    if rc == 0:
        rc, so, se, w2 = run([exe])
        w += w2
    rows.append(row("port_u575.regs", "PASS" if rc == 0 else "FAIL", (so.strip().splitlines() or ["?"])[-1] if rc in (0, 1) else f"exit {rc}", "0 fails",
                    basis="fw/test/port/test_regs.c: GPIO + TIM1 PWM/break write sequences and values vs RM0456 Rev 7", src="FWSIM-R16, FWSIM-R65",
                    detail=None if rc == 0 else tail(se), wall=w))
    # FWSIM-R15 ceiling property
    d = OUT / "prop"
    d.mkdir(parents=True, exist_ok=True)
    exe = d / "prop_ceiling"
    rc, _, se, w1 = run([GCC, *HOST_FLAGS, "-D_DEFAULT_SOURCE", *INC_HOST, *CORE, FW / "port_host/fake.c", FW / "test/prop/prop_ceiling.c", "-lm", "-o", exe])
    if rc != 0:
        rows.append(row("dsp.ceiling_property", "FAIL", "build error", 0, src="FWSIM-R15", detail=tail(se)))
    else:
        rc, so, se, w2 = run([exe], timeout=900)
        try:
            p = json.loads(so.strip().splitlines()[-1])
        except Exception:                            # noqa: BLE001
            p = {}
        ok = rc == 0 and p.get("viol_a") == 0 and p.get("viol_b") == 0 and p.get("viol_c") == 0
        rows.append(row("dsp.ceiling_property", "PASS" if ok else "FAIL",
                        f"{p.get('total_hops')} hops: true peak max {p.get('true_peak_max')} (ceiling {p.get('ceiling')}), CCR |amp| max {p.get('ccr_amp_max_arr200')} "
                        f"(bound {p.get('bound_b_arr200')}), R64 clamp hits {p.get('viol_c')}", "0 violations of (a), (b), (c)",
                        basis="fw/test/prop/prop_ceiling.c: adversarial words (FS tones, FS noise, steps, chirps, bursts) x every volume step x B/slim/A x ARR 200/100/50",
                        src="FWSIM-R15", detail=p.get("rows") if ok else (tail(se + so) or p), wall=w1 + w2))
    # static cycles per variant
    j = OUT / "dsp_cycles.json"
    rc, so, se, w = run([sys.executable, FW / "tools/cycles.py", "--json", j], timeout=600)
    if rc == 0:
        c = json.loads(j.read_text())
        rows.append(row("dsp.cycles_hop_static", "PASS", {v: {"cyc": x["cycles_hop"], "MHz": x["MHz_with_V4_overhead"], "V4_MHz": x["v4"]["MHz"]} for v, x in c.items()},
                        "estimate (reported, not gated)", op="", basis="fw/tools/cycles.py: fw/bench/cyccount CPI x gcov line counts on the sweep vector (active path), 0 WS",
                        src="FWSIM-R10, FWSIM-R47", wall=w))
    else:
        rows.append(row("dsp.cycles_hop_static", "FAIL", f"exit {rc}", "runs", src="FWSIM-R47", detail=tail(se + so)))
    # E2 cross-check: per-hop instruction counts on QEMU (-icount) vs the static model's instruction count
    j = OUT / "dsp_icount.json"
    rc, so, se, w = run([sys.executable, REPO / "sim/fw/qemu_icount.py", "--json", j], timeout=900)
    if rc == 0 and j.exists():
        q = json.loads(j.read_text())
        rows.append(row("dsp.insns_hop_qemu", "PASS", {v: {"qemu": x["qemu_insns_hop"], "static": x["static_insns_hop"], "ratio": x["ratio_qemu_static"]} for v, x in q.items()},
                        "reported (static model must not undercount: ratio <= 1.05)", op="", basis="sim/fw/qemu_icount.py: QEMU mps2-an505 -icount shift=0, SysTick around fw_hop, sweep vector hops 600+",
                        src="FWSIM-R47", wall=w))
        if any(x["ratio_qemu_static"] > 1.05 for x in q.values()):
            rows[-1]["status"] = "FAIL"
    else:
        rows.append(row("dsp.insns_hop_qemu", "FAIL", f"exit {rc}", "runs", src="FWSIM-R47", detail=tail(se + so)))
    return rows


# ------------------------------------------------------------------------------------------- gen + lint (python)
def stage_py(rid, script, args, req, basis):
    rc, so, se, w = run([sys.executable, FW / "tools" / script, *args], timeout=300)
    out = (so + se).strip()
    return row(rid, "PASS" if rc == 0 else "FAIL", "ok" if rc == 0 else f"exit {rc}", "exit 0", basis=basis, src=req, detail=None if rc == 0 else tail(out, 15), wall=w)


def versions():
    v = {}
    for name, cmd in (("gcc", [GCC, "--version"]), ("clang", [CLANG, "--version"]), ("arm-none-eabi-gcc", [ARMCC, "--version"])):
        try:
            v[name] = run(cmd)[1].splitlines()[0]
        except Exception as e:                       # noqa: BLE001
            v[name] = f"missing: {e}"
    v["python"] = sys.version.split()[0]
    rc, so, _, _ = run(["git", "-C", REPO, "rev-parse", "--short", "HEAD"])
    v["repo_head"] = so.strip() if rc == 0 else "?"
    return v


def requirement_status(rows, tests):
    """FWSIM-R id -> PASS only if every row and every host test naming it passed."""
    req = {}
    for r in rows:
        for rid in re.findall(r"FWSIM-R\d+", r.get("src", "")):
            req.setdefault(rid, []).append(r["status"])
    for build, ts in tests.items():
        for t in ts:
            req.setdefault(t["req"], []).append("PASS" if t["fails"] == 0 else "FAIL")
    return {k: ("PASS" if all(s == "PASS" for s in v) else "FAIL") for k, v in sorted(req.items(), key=lambda kv: int(kv[0][7:]))}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", nargs="?", default="all", choices=["all", "host", "arm", "lint", "gen", "dsp"])
    ap.add_argument("-j", "--jobs", type=int, default=4, help="parallel compiler processes (default 4; the box is shared)")
    cfg = ap.parse_args(argv)
    OUT.mkdir(exist_ok=True)
    t0 = time.monotonic()
    rows, tests, arm = [], {}, {}
    if cfg.cmd in ("all", "gen"):
        rows.append(stage_py("gen.fresh", "gen.py", ["--check"], "FWSIM-R5",
                             "fw/gen == gen.py output now; gen refuses if interfaces [pins] FAILs (design from hw/current.yaml)"))
    if cfg.cmd in ("all", "lint"):
        rows.append(stage_py("lint", "lint.py", [], "FWSIM-R1, FWSIM-R2", "include + absolute-address + HAL-surface rules, planted-violation self-test"))
    if cfg.cmd in ("all", "host"):
        r, tests = stage_host(cfg)
        rows += r
    if cfg.cmd in ("all", "arm"):
        r, arm = stage_arm(cfg)
        rows += r
    if cfg.cmd == "all":
        rows.append(stage_symbols(arm))
        rows += stage_variants(cfg)
    if cfg.cmd in ("all", "dsp"):
        rows += stage_dsp(cfg)
    wall = time.monotonic() - t0
    status = "PASS" if all(r["status"] == "PASS" for r in rows) else "FAIL"
    summary = {"id": "FWSIM", "cmd": cfg.cmd, "status": status, "rows": rows, "requirements": requirement_status(rows, tests),
               "tests": tests.get("host_gcc", []), "arm": {k: arm[k] for k in ("flash", "ram_static", "stack_region", "sections") if k in arm},
               "tools": versions(), "wall_s": round(wall, 1),
               "scope": "tier S + H: foundation (group a) + DSP chain host behaviour (group b: R7 L0-host/L1, R8, R13, R14, R15); L0 ARM vs host on QEMU mps2-an505 (no STM32 peripheral model: tier E open); port_u575 HAL is stubs (HAL_ENOTIMPL)"}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")
    for r in rows:
        print(f"{r['status']:4} {r['id']:<34} {r['last']}  [{r['src']}]")
        if r["status"] != "PASS" and r.get("detail"):
            print("     " + str(r["detail"]).replace("\n", "\n     "))
    print(f"fwsim {cfg.cmd}: {status} ({len(rows)} rows, {wall:.1f} s) -> {REL(OUT / 'summary.json')}")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
