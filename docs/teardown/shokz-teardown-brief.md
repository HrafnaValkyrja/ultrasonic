# Shokz teardown brief (for a fresh Claude Code session)

Written 2026-10-03 by the lead session for a future session in this repo (`/home/hrafnavalkyrja/Desktop/ultrasonic`).
The owner drops this file into a new session when she has the hardware on the bench. Read `CLAUDE.md` first; its
rules apply (memory fences, FOSS-only installs, no orders, owner decides).

## 0. What this is and why

- **Project:** "Stereo Ultrasound", two glasses-mounted pods. Each pod hears ultrasound (20-96 kHz) with a PDM MEMS mic,
  shifts it to 1.5-4 kHz on an STM32U575, and plays it by **bone conduction at the tragus** through a tiny exciter
  (RC-BC02) on an ear pad at the end of a NiTi arm. The spec is `docs/spec.md` (§1 is owner-locked).
- **Hardware:** a broken pair of Shokz bone-conduction headphones the owner owns (model unknown until you identify it).
  The teardown is destructive, for **education** (personal hobby project, not a product).
- **Why it matters:** our riskiest unknowns are physical. The answers below can't come from simulation:
  1. **How a real bone-conduction transducer is built and driven.** Our exciter has never been measured (spec E1/E2,
     ECR-0007).
  2. **How a real product makes a thin, light pod.** Owner rule O27: thin first, then short (height), length last.
     Today's pod is ~10.4 mm thick; the target is far thinner. See `docs/research/drastic/` and
     `docs/research/miniaturization-prelim.md`.
  3. **How they seal magnetic charging contacts, mic ports and buttons.** This is our 5-contact dock, sealed mic duct
     and IP68 button: `docs/system/sub-dock-usb.md`, `docs/sim/acoustics.yaml`, `docs/system/sub-ui.md`.
  4. **What chips they use.** This feeds `docs/research/drastic/silicon.md` (integrated chargers, smart amps, low-power
     SoCs).
- **Not the goal:** copying their design, or reusing their battery.

## 1. Safety (do this before anything is opened)

- **The lithium cell is the hazard.** It is likely a thin pouch in the back band or in a pod. Locate it first, from
  public internal photos (§2) if possible.
  - Use plastic spudgers only near it. Never pry, cut, drill or heat toward it.
  - Keep a metal tin or a bowl of sand within reach, and work somewhere ventilated.
  - If it is **puffy, dented, hot or smells sweet**: stop, isolate it in the tin, and recycle it. Do not continue near it.
  - **Never charge it**, and **never reuse it** in the project. It has no datasheet, unknown wear, and the wrong shape
    for O27. If it is intact and flat it may power the original electronics once, for the listening test (§6), and
    nothing else.
- Cut housings with a fine saw or rotary tool **away from the cell area**. Wear eye protection when cutting or prying.

## 2. Before you open it (non-destructive, do in this order)

1. **Identify the model.** Find the label and the model number (e.g. OpenRun, OpenMove, Aeropex) and the **FCC ID**.
   The FCC filing's **internal photos** are public (fcc.report or fccid.io: search the FCC ID). They often show the
   board, cell and chip markings without opening anything. Save the URLs and the read date.
2. **Function test.** Does either side power on, pair and play over Bluetooth? Record what works and what is broken.
   If it plays, run the listening test (§6) **before** the teardown.
3. **Clamping force (do this before disassembly).** Hold the headband open to the width of the owner's head at the
   transducer positions, and measure the closing force with a kitchen scale (grams × 9.81 = mN). Compare it with our
   spec of ≥ 1 N at the tragus. Note how the force changes with opening width (3 widths if possible).
4. **Whole-device numbers:** total mass (kitchen scale or letter scale), and the pod/transducer housing dimensions with
   calipers (L × W × T). Note which dimension is the "thickness off the head".

## 3. What to measure during the teardown (ranked)

Record every number in the sheet (§4). Photograph each step with a scale reference (a ruler or calipers in frame).

**A. Transducer** (most valuable)
- DC coil resistance (multimeter, ohms) of each side.
- Outer dimensions, mass, magnet type and size, coil size.
- Suspension: how the moving part vibrates without driving the housing (springs, membrane, foam, decoupling).
- Contact face: shape, area (mm²), material, durometer if known (soft or hard silicone, plastic plate).
- Optional: cut the transducer in half to section it. Photograph the section with a scale.

**B. Packaging for thinness (O27)**
- Battery: location, dimensions (L × W × T), printed capacity/voltage/model, mounting (foam, tape, bracket), tab
  connection (soldered, connector), protection board.
- Housing: wall thickness at several points; material layers (rigid shell + soft-touch overmold?). A **saw section**
  through the transducer housing shows the layers best.
- Board(s): rigid or flex or rigid-flex, size, thickness, layer count if visible at a cut edge, smallest passive size
  (0201? 01005?), shielding cans, stiffeners.
- How the parts are held together: screws, clips, adhesive, ultrasonic welds. Our rule O16 is no screws in the housing.

**C. Electronics**
- Photograph **every IC marking** at macro or microscope magnification, then identify each (BT SoC, amplifier or
  transducer driver, charger/PMIC, mic, flash). The amp/driver and the charger matter most to us.
- Wiring through the band: conductor count and type (litz? fine coax? flex?), how it is strain-relieved.
  This is relevant to our 4 wires up the NiTi arm (`docs/system/reg-arm.md`).
- Microphones (if any, for calls): count, position, port design.

**D. Sealing and the charging interface**
- Magnetic charging contacts: pin count, pitch, diameter, plating colour (gold?), magnet size and position, how the
  pins are sealed to the housing (gasket, potting, overmold).
- Mic ports: membrane or mesh type and how it is bonded.
- Buttons: sealed switch under silicone? Travel? Any LED or light pipe?
- **Failure analysis:** what broke and why (cracked joint, corrosion, fatigued wire, swollen cell, water ingress).
  Photograph it. These are our risks too.

## 4. Measurement sheet (write it as YAML)

Save to `docs/teardown/shokz-results.yaml`. Use AI-facing dense YAML: units, the instrument, and a confidence tag
(`measured` / `estimated` / `read-from-label` / `from-FCC-photo`) on every number.

```yaml
meta: {model: "", fcc_id: "", fcc_photos_url: "", date: "", condition: "", tools: [calipers, multimeter, scale]}
function_test: {powers_on: null, pairs: null, plays_left: null, plays_right: null, notes: ""}
clamp_force_mN: [{opening_mm: null, force_mN: null}]
device: {mass_g: null, pod_LxWxT_mm: [null, null, null], thickness_axis: ""}
transducer: {dcr_ohm: {left: null, right: null}, size_mm: [], mass_g: null, magnet: "", suspension: "", contact_face: {shape: "", area_mm2: null, material: ""}}
battery: {location: "", size_mm: [null, null, null], label: "", capacity_mAh: null, mounting: "", tabs: "", pcm: "", condition: ""}
housing: {wall_mm: [], materials: "", joins: ""}
boards: [{name: "", type: "rigid|flex|rigid-flex", size_mm: [], thickness_mm: null, layers: null, smallest_passive: "", shields: null}]
ics: [{marking: "", identified_as: "", function: "", package: "", photo: ""}]
band_wiring: {conductors: null, type: "", strain_relief: ""}
charging_contacts: {pins: null, pitch_mm: null, plating: "", magnet: "", sealing: ""}
mic_ports: [{position: "", membrane: ""}]
buttons: [{type: "", sealing: ""}]
failure: {what: "", why: "", photo: ""}
lessons_for_pod: []   # each: {area: transducer|thinness|sealing|dock|silicon|arm, finding: "", affects: "doc/ECR/queue id"}
```

## 5. Photos and privacy

- Keep raw photos in `docs/teardown/photos/`. This folder is **gitignored**: create `docs/teardown/photos/.gitignore`
  containing `*` and `!.gitignore`. Ask the owner before committing any photo. The owner's personal photo folders
  (`own/`, `earopen/`, `From Valkyrie/`) are never committed.
- Reference photos by filename in the YAML. Annotated diagrams you draw yourself (SVG in `docs/diagrams/`, rendered
  with `docs/diagrams/render.sh`, dark mode) may be committed.

## 6. Optional: tragus listening test (E2-lite)

Only if a side still plays over Bluetooth (or with a small amp on the bare transducer, owner's call, no purchase).
- **Goal:** a qualitative answer to "do the translated ultrasound sounds work through bone conduction at the tragus?"
  This is spec R19 / E2. It is not exciter calibration: their transducer is larger and made for the cheekbone.
- **Files:** translated audio from `sim/out/nature/` (the nature demo) and the sound-chain scenes
  (`python3 sim/e2e/chain.py --scenario T1|T2`, fenced, see `docs/sim/e2e-chain.yaml`). Make a short playlist with a
  note per file: what the source was (bat call, insect, rangefinder, background).
- **Protocol:**
  - Start at the lowest volume. Press the transducer on the tragus with a gentle, steady force. A ~1 N reference is
    about 100 g on a kitchen scale.
  - Then try the cheekbone, for comparison.
  - Try with ears open, then with the owner's Nothing Ear (open) worn, as in spec E2.
  - Note per file: audible?, pleasant / harsh / muffled, does the direction cue (left vs right) survive?
- Record the results in `docs/teardown/shokz-results.yaml` under `listening_test`, and as a finding against spec R19.

## 7. When done

- Commit `docs/teardown/shokz-results.yaml`, any diagrams, and a short findings file `docs/teardown/shokz-findings.md`
  (AI-facing: findings ranked by how much they change our design, each pointing at the affected doc, ECR or queue id).
- Add a FYI to `docs/brief/queue.yaml` (close `A-SHOKZ-BENCH`) and log autonomous choices in
  `docs/brief/decisions-log.yaml`.
- Run `python3 tools/plm.py status` and review anything flagged.
- Do not change the design (schematic, board, shell) in that session. Hand findings to the lead session as proposals
  (ECRs), unless the owner says otherwise.
