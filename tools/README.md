# Engineering harness

Tools that let Claude simulate circuits, design and check boards, model mechanics, render
diagrams and cross-compile firmware in the cloud container. One idempotent installer,
one environment file, smoke tests with real answers.

```bash
tools/setup.sh               # install anything missing, verify (a fast no-op once installed)
tools/setup.sh --smoke       # ...then run the smoke tests
tools/setup.sh --check       # verify only
source tools/env.sh          # PATH, venv, KiCad library paths, FreeRouting, mermaid-cli
python3 tools/smoke/run_all.py [--offline] [-k NAME] [--keep DIR]
```
A SessionStart hook runs `tools/setup.sh --quiet` in Claude Code on the web, so a fresh
container installs everything automatically.

## What's installed (2026-09-30)
| Tool | Version | Used for | Skill |
|---|---|---|---|
| ngspice | 42 | Circuit simulation: H-bridge dead time, gate drive, LDO, battery | spice-sim |
| KiCad (`kicad-cli`, `pcbnew` Python) | 10.0.6 (official PPA, key pinned in `keys/`) | ERC/DRC, Gerber/drill/placement export, 3D renders, board scripting | pcb-kicad |
| SKiDL | 2.3.0 | Schematics as code, generating the KiCad netlist | pcb-kicad |
| FreeRouting | 2.4.1 (SHA-256 pinned; OpenJDK 25) | Headless autorouting via Specctra DSN/SES | pcb-kicad |
| easyeda2kicad | 1.0.1 | KiCad symbol, footprint and 3D model by LCSC number | jlc-parts |
| `tools/jlc.py` | — | JLC stock, price, Basic/Extended, with a query timestamp | jlc-parts |
| ARM GCC + newlib | 13.2.1 | Cortex-M4F cross-compiling (hard-float) | — |
| build123d | 0.13.0 | Parametric CAD, mass properties, STL/STEP | cad-mech |
| scikit-fem | 12.0.2 | Finite elements (spring arm force, stiffness) | cad-mech |
| numpy / scipy / matplotlib | 2.5.3 / 1.18.1 / 3.11.2 | DSP models, plots (`tools/plotstyle.py`) | — |
| mermaid-cli | 11.17.0 (uses the preinstalled Chromium) | Flowcharts and mind maps to PNG | visual-explainer |
| headless Chromium | preinstalled (`/opt/pw-browsers`) | SVG diagrams to PNG (`docs/diagrams/render.sh`) | visual-explainer |

Python packages live in a Python 3.12 venv (`$ULTRA_VENV`, with system site packages so
`import pcbnew` works), pinned by `requirements.txt` and `constraints.txt`. Install location
is `/opt/ultrasonic-tools` (`$ULTRA_TOOLS_HOME`).

**Cost:** about 3.4 GB of disk (1.7 GB of apt packages, 1.7 GB of venv and tools). A run with
partly cached apt packages took 107 s. A fully cold install hasn't been timed; expect a few
minutes. The KiCad 3D-model library is optional: `--with-3d` adds 3.2 GB.

## Smoke tests (all passing, 2026-09-30)
| Test | Checks |
|---|---|
| ngspice | RC step response: time constant 1.000 ms (expected 1.000) |
| kicad+freerouting | Build a 2-net board → autoroute → import → DRC 0 errors, 0 unconnected → 25 Gerber files → 3D render |
| skidl | Netlist with parts, nets and footprints |
| arm-gcc | Cortex-M4F object uses the FPU |
| build123d | Exact volume and centroid of a part with a window; STL + STEP |
| scikit-fem | Cantilever tip deflection matches beam theory to 0.1% |
| render | SVG and Mermaid diagrams to PNG |
| easyeda2kicad | Fetches the SPH0641LU4H-1 footprint and symbol (C2879853) — network |
| jlc-api | Live JLC lookup — network |

## Fixed while testing
`tools/spice.py` returned no `.meas` results: ngspice 42 refuses `.meas` in batch mode
when writing a rawfile. Netlists with `.meas` now get a second batch pass without `-r`.

## What this can't do
- **Cycle-accurate Cortex-M4 timing.** There's no free simulator for it; measure on the Nucleo
  with the DWT cycle counter (spec S3).
- **Bone conduction, skin coupling and perception.** These are bench and ear questions (spec §10).
- **The mic's acoustic port above ~20 kHz.** Lumped models are approximate; the S1 acoustic
  coupons decide.
- **EMI and full-wave electromagnetics.** Not installed (openEMS could be added if needed).
- **Accuracy of vendor models.** A simulation is only as good as its models; every result
  names the models it used.
