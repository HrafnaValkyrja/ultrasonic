# The big picture: living system documents

The pod is one system. A change in one place (a part swap, a moved component, a lid feature, a firmware
pin) can break something three domains away. These documents keep the whole picture in one place, so
every change is checked against it **before** it is made. Owner rule, 2026-10-01: Claude and every
agent use this set for every design change.

## The rule

1. **Before** any design change (schematic, layout, mechanics, firmware architecture, part choice):
   read `00-whole.md`, `integration-map.md`, and the doc of every subsystem and region the change touches.
   Walk the change through the cross-check in `integration-map.md` §10 (functions, nets, pins, rails,
   off-board, mechanical, firmware, cross-domain dependencies). Run `python3 tools/plm.py impact <file|ref:X|net:X|item>`
   to list every interface and doc the change touches. A change bigger than a typo gets an ECR
   (`plm.py ecr new`); the owner approves ECRs that touch her decisions.
2. **After** the change, in the same commit: update every doc it touched: status line, interfaces, key
   numbers, open issues, change log. Regenerate the integration map when the schematic changes:
   `source tools/env.sh && python3 hw/pod/system_map.py`. Then `plm.py status`: every SUSPECT relation and
   STALE item it reports must be checked and re-baselined (`plm.py review <id> --by ... --note ...`) before
   the work counts as done.
3. **Agents** get this set as mandatory context and must return the cross-check with every proposal.
   A team (agent or person) that edits an item checks it out first (`plm.py checkout <item> --by <team>`);
   a CONFLICT FLAG means a related item is held by another team: coordinate before editing.
4. **Authority:** `docs/spec.md` wins. These docs summarise and link; they never override the spec or the
   source-of-truth files (`hw/pod/gen.py`, the KiCad board, `hw/mech/*.py`). If a doc disagrees with a
   source file, the doc is wrong: fix it. If the spec looks wrong, raise it with the owner.
5. **Staleness is a bug.** A doc whose status line is older than the last change to its source files is
   out of date. Fix it before relying on it.

## Index

| Doc | Kind | Covers |
|---|---|---|
| [00-whole.md](00-whole.md) | whole | The product on one page: functions, block and physical diagrams, key numbers, status of every part of the system, decision index |
| [integration-map.md](integration-map.md) | integration (generated) | Every block, inter-block net, MCU pin, rail load, off-board wire, mechanical keep-out, firmware dependency; the cross-check protocol |
| [physical.md](physical.md) | physical integration | Coordinate frame, stack-up through the pod, clearances, sealing paths, assembly order (test build vs final bonded build) |
| [sub-power.md](sub-power.md) | subsystem | Cell, charger, power path, LDO, rails, temperature-safe charging, battery sensing, power budget |
| [sub-audio-in.md](sub-audio-in.md) | subsystem | Ultrasonic mic, acoustic port path, PDM/ADF1 capture |
| [sub-processing.md](sub-processing.md) | subsystem | MCU, core SMPS, clocks, memory, firmware architecture and algorithms, low-power modes |
| [sub-output.md](sub-output.md) | subsystem | H-bridge, PWM, exciter, arm wiring to it, self-test current sense |
| [sub-dock-usb.md](sub-dock-usb.md) | subsystem | Magnetic dock, USB FS, DFU, ESD, dock detect |
| [sub-ui.md](sub-ui.md) | subsystem | Button (switch, plunger, skin), power LED |
| [sub-debug-test.md](sub-debug-test.md) | subsystem | SWD, test pads, test hooks, snap-off test frame, self-test over USB, bring-up plan |
| [reg-pod-body.md](reg-pod-body.md) | region | Housing (tub, lid, spine top), board retention, dock bay, sealing, adapter to the temple |
| [reg-board.md](reg-board.md) | region | The PCB: outline, faces, floorplan regions, layer stack, keep-outs, height bands, routing state |
| [reg-arm.md](reg-arm.md) | region | NiTi arm, heel, strut cover, joint, wire path through it |
| [reg-pad.md](reg-pad.md) | region | Transducer cup, contact face, pad board and LED |

## Relation tracking (`tools/plm.py`, PLM-style)

Items (these docs), relations (the interfaces between them, each watching the exact things that carry the
interface: nets, parts, placement entries, CAD symbols, spec lines), baselines, check-outs and ECRs live in
`docs/system/plm/`. A relation turns **SUSPECT** when anything it watches changes after its last review; an
item turns **STALE** when its sources change after its doc was last reviewed; a watch that no longer resolves
is **BROKEN** (re-model the relation). `plm.py graph` draws the whole web (`docs/diagrams/plm-relations.png`).
Idea sources: Teamcenter-style where-used / change management; Doorstop's suspect-link stamps.

## Template (every subsystem and region doc)

```
# <Name>
Status: <revision / state>, updated <date> · Source of truth: <files> · Owner decisions: <O-items>

## Purpose            what it must do; which functions (F-rows in integration-map.md) it carries
## Big picture        a diagram (PNG in docs/diagrams, dark mode) + 5-10 lines of how it works
## Elements           parts / features, each glossed (part number = what it is), with LCSC/refs
## Interfaces         to every other subsystem/region: nets and MCU pins (names exactly as in
                      integration-map.md), mechanical contacts, firmware dependencies
## Constraints        spec decisions (D-items), owner decisions (O-items), physics/process limits
## Key numbers        with source and date
## Open issues        and risks, each with what would close it
## Before you change this, check   the specific other docs and invariants a change here can break
## Change log         dated one-liners
```

## Change log
- 2026-10-01: set created (owner rule). `integration-map.md` generated from gen.py Rev E.
- 2026-10-01: doc set completed (00-whole, physical, 7 subsystem and 4 region docs, diagrams `system-overview-physical` and `board-regions`), then inspected and corrected in one editor pass: interfaces name the doc on the other side, 00-whole gains the status table, "Design-level cross-domain risks" and "Fixes waiting in source files"; ECR-0008/0009 and two relations in `items.yaml` amended.
