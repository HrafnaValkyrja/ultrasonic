---
name: cad-mech
description: Mechanical design for the glasses-mounted pods - parametric CAD in build123d (clasps, battery bay, transducer spring arm, acoustic port), mass properties and centre of mass for weight balance, STL/STEP export for 3D printing, and FEM with scikit-fem for spring force and stiffness. Use for any question about size, weight, balance, fit, force or printable parts.
---

# CAD and mechanics

Setup: `source tools/env.sh`. Units are **mm**, grams, newtons, MPa.

## Parametric parts (build123d 0.13)
```python
from build123d import Box, Cylinder, Pos, export_stl, export_step
pod = Pos(20, 5, 3) * Box(40, 10, 6) - Pos(8, 5, 3) * Cylinder(0.5, 6)   # e.g. bay with a port hole
print(pod.volume, pod.center())                                          # mm^3, centroid (mm)
export_stl(pod, "out/pod.stl"); export_step(pod, "out/pod.step")
```
- Keep every dimension a named parameter at the top of the script (`hw/mech/<part>.py`), with
  its source: spec section, datasheet, or E9 photo measurement.
- Mass = volume x density. Material densities used here must cite a source; e.g. JLC MJF
  PA12 nylon ~1.01 g/cm^3 (verify on JLC's material page when it matters).
- Look at the part: tessellate and plot with matplotlib (`tools/plotstyle.py`), or export an
  SVG projection, then send the PNG inline (visual-explainer skill).

## Balance
`sim/checks/balance.py` splits added weight between nose pads and ears from part masses and
positions. Feed it CAD masses and centroids instead of estimates once parts exist.

## Springs and force (scikit-fem 12)
The smoke test `tools/smoke/run_all.py` (t_scikit_fem) solves a cantilever in plane stress and
matches beam theory to 0.1%; start the transducer-arm model from it. Targets from the spec:
>= 1 N at the pad through jaw motion, compliant, deflects away from the Ear (open) (D1, §8,
`docs/research/ear-open-fit.md`). Report force vs deflection curves, not single numbers.

## Fit
The keep-out geometry around the Nothing Ear (open) comes from `docs/research/ear-open-fit.md`
and the owner's E9 photos. Never design to one reviewer's ear.
