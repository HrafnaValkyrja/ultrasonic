---
name: spice-sim
description: Simulate circuits in ngspice for this project - the H-bridge and its dead time, gate-drive current, MOSFET losses, LDO dropout and ripple, battery sag, charger behaviour, filters, the transducer's R-L(-motional) load. Use when a question depends on circuit behaviour that a back-of-envelope estimate or the numpy checks in sim/checks/ can't settle.
---

# SPICE simulation (ngspice 42)

Setup: `source tools/env.sh` (installs via `tools/setup.sh`). Helper: `tools/spice.py`.

## Workflow
1. Write the netlist in `sim/spice/<topic>.cir` with dot-analyses (`.tran`, `.ac`, `.dc`,
   `.op`, `.noise`), not a `.control` block. First line is the title.
2. Vendor models go in `sim/spice/models/` with a header comment giving the source URL,
   model revision and download date. Never invent model parameters silently; if you must use a
   generic model, say so in the netlist and in every result that depends on it.
3. Run from Python:
   ```python
   import sys; sys.path.insert(0, "tools"); import spice
   res = spice.run("sim/spice/bridge.cir", compat="ps")   # compat for PSpice/LTspice models
   t, v = res.tran["time"], res.tran["v(out)"]
   res.meas["tdead"]                                        # .meas results (second batch pass)
   spice.tavg(t, i, t0, t1), spice.trms(t, i, t0, t1)       # non-uniform time grid aware
   ```
   or the CLI: `python3 tools/spice.py net.cir --plot "v(a),i(v1)" --png out.png`.
4. `.meas` works (the helper re-runs without the rawfile, because ngspice 42 refuses
   `.meas` in `-b -r` mode). Add `.save @m1[id]` etc. for device quantities.
5. Plot with `tools/plotstyle.py`, **look at the PNG**, and send it inline if the owner should
   see it (visual-explainer skill).
6. Record conclusions in `docs/research/<task>.md` with the netlist path, the models used and
   what was *not* modelled.

## Project specifics
- Supply rail 3.0 V (LDO); bridge PWM 200 kHz centre-aligned, 2-level (AD) modulation, dead
  time 12.5-25 ns (spec D6). Transducer placeholder: 8 ohm + 0.3 mH until E1 measures it.
- Compare against the numpy models in `sim/checks/` (dead-time, noise shaping): SPICE adds
  real MOSFET capacitances, body diodes and gate charge; disagreements are findings.
- Timesteps: set a max step (`.tran 1n 200u 0 1n`) when resolving 12.5 ns dead time.

## Limits
A simulation is only as good as its models. Bone coupling, perception and the transducer's
mechanical behaviour are bench questions (spec §10 S2).
