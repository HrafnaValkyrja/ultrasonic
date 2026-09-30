# Handoff: cloud session → Valhalla (local, i9-14900HX), 2026-09-30

**Owner decision: this project now runs only on Valhalla, with Remote Control. Cloud sessions are retired.** The cloud session `session_016uLR3rVesNK6FmgR7vwByF` is archived once the teleport works.

Written by the cloud session for its local continuation. **Read this first, then `CLAUDE.md` and `docs/spec.md`.**
Branch: `claude/clever-mayer-s5rxuw` (everything below is committed and pushed).

## Why the move
The adversarial audit workflow runs at most (CPU cores − 2) agents at once, capped at 16. The cloud container has 4 cores, so 2 agents ran at a time: about 6–10 h for the whole audit. With the i9-14900HX's 32 threads, 16 run at once.

## First job for the local session
**The owner has downloaded the 20 bundle parts and asked Claude to do the reassembly.** Ask her which folder they're in, then:
```bash
cd <that folder>
cat ultrasonic-scratch.zip.part{00..19} > ultrasonic-scratch.zip
sha256sum ultrasonic-scratch.zip   # must be e47d1e93519f00fdd40d1e1364c22b11b18529978cbd8a378028d7e3102f8b4c
unzip -q ultrasonic-scratch.zip -d <parent of the repo>   # gives <parent>/ultrasonic-scratch
```
If the hash doesn't match, find the bad part by size (every part except part19 is exactly 29,360,128 bytes) and ask her to re-download it.

**How this session got here:** `claude --teleport session_016uLR3rVesNK6FmgR7vwByF`, run from a clean checkout of the repo. That carries the whole cloud conversation over. Paths in that history (`/home/user/ultrasonic`, `/tmp/claude-0/...scratchpad`) are the cloud's; locally they are the repo and `../ultrasonic-scratch`.

## One-time setup on Valhalla
1. **Machine (confirmed 2026-09-30):** native **Ubuntu 26.04.1 LTS** (codename `resolute`), KDE/Wayland, 32 threads, 30 GB RAM. No WSL. Repo at `~/Desktop/ultrasonic`, scratch at `~/Desktop/ultrasonic-scratch`.
   - **Python is 3.14**, and KiCad 10 for 26.04 is built against it, so `tools/setup.sh` detects the interpreter instead of pinning 3.12 (it used to assume the 24.04 cloud image).
   - **sudo needs a password**: `setup.sh` uses `sudo -n`, so authenticate first with `SUDO_ASKPASS=/usr/bin/ksshaskpass sudo -A -v` (pops a KDE dialog) and keep the timestamp alive during long installs.
2. **Clone and set up:**
   ```bash
   git clone <repo> ultrasonic && cd ultrasonic && git checkout claude/clever-mayer-s5rxuw
   tools/setup.sh              # idempotent; needs sudo for apt
   source tools/env.sh && python3 tools/smoke/run_all.py    # all smoke tests must pass
   ```
3. **Scratch workspace:** unzip the bundle so it sits **next to** the repo, as `../ultrasonic-scratch/`. It holds:
   - datasheets and extracted text (`ds/`, `u5/`);
   - the owner's current ST documents (`st_new/`);
   - papers, partial audit outputs (`audit/`);
   - the workflow journal and `done.json`;
   - the full cloud transcript (`session-transcript.jsonl`, backup only).

   `own/` and `earopen/` contain the owner's personal photos. **Never commit them.**
4. **Start the session** by teleporting (above), then **turn on Remote Control**: run `/remote-control` (or `/rc`) inside the session. The owner steers it from the Claude app and claude.ai as well as the terminal.
   - **Make it permanent:** `/config` → **Enable Remote Control for all sessions**, or `"remoteControlAtStartup": true` in `~/.claude/settings.json` (user settings; a project `settings.json` can't turn it on).
   - **Stay awake:** the machine must stay on and the `claude` process running. It reconnects by itself after sleep or a network drop.
   - **After a restart:** `claude --continue` in the repo brings the conversation back; with auto-connect on, Remote Control reconnects too.

## Resume the adversarial audit
- **Script:** `.claude/workflows/adversarial-methodology-audit.js`. It's portable (paths via args), and it skips any agent whose result is in `args.done`.
- **The cloud run was stopped** at the owner's request on 2026-09-30. `../ultrasonic-scratch/done.json` is final. It holds 2 finished results (`audit:netlist-mcu`, `audit:netlist-other`) that the local run reuses; everything else runs fresh. The two audits that were mid-flight (footprints, spice-bridge) left partial notes in `../ultrasonic-scratch/audit/` and transcripts in `workflow-agent-transcripts/`; they rerun from scratch. To regenerate `done.json` from the journal:
  ```bash
  python3 .claude/workflows/export_done.py ../ultrasonic-scratch/workflow-journal.jsonl > ../ultrasonic-scratch/done.json
  ```
- **Run it:** use the Workflow tool with `name: "adversarial-methodology-audit"` and
  `args: {"repo": "<abs path to repo>", "scratch": "<abs path to ultrasonic-scratch>", "date": "<today>", "done": <contents of done.json>}`.
- **Current datasheets:** the audit now points auditors at the owner's current ST documents (`st_new/`: DS13737 Rev 10, ES0499 Rev 12, RM0456 Rev 7, AN5373 Rev 7).
- **What was already done:** results finished in the cloud used DS13737 Rev 8. Rev 8 → Rev 10 changed nothing for the pins or power pins we use (`docs/research/datasheet-provenance.md`), so they stand.

## State of the project (details in `docs/spec.md` v0.13 and `docs/design-review-v1.md`)
- **Design:**
  - STM32U575 on its SMPS; SPH0641 mic on ADF1; H-bridge of two PMCXB290UE, 2-level PWM at 200 kHz;
  - MCP73831 charger and TPS7A2030 LDO; 105 mAh cell;
  - pod 35×9×14 mm; board 20×11.5 mm, 4 layers.
- **Schematic source of truth:** `hw/pod/gen.py`.
- **Draft board** (proof of fit, not a layout to order): `hw/pod/kicad-draft/`.
- **Owner decisions made:**
  - tragus arm = **superelastic NiTi wire** (O7);
  - **dark mode** for every visual;
  - she wants to **understand** the design. Teaching track is `docs/learn/`, pitched at an RF/analogue/digital-packets/CAD/device-physics engineer. Don't explain basics.
- **Open decisions:**
  - O3 bench kit: the staged ~$60–75 list, plus using parts she already has;
  - O4 cell position reading;
  - O5 keep 105 mAh;
  - "final board as the prototype" (option C: the pod board in a snap-off test frame). Recommended, not yet approved.
- **Known fixes to make:**
  - C4 → 10 µF 0603 (AN5373 VDD bulk);
  - the missing ground plane in the draft; vias in the MCU exposed pad;
  - mic port 0.8 mm;
  - redraw the PMCXB290UE footprint from Nexperia Fig. 32;
  - fetch real datasheets for the ESD diodes, KXT321LHS and the passives.
- **Firmware rules from errata (spec D14):**
  - MSI-PLL unlock handler;
  - PLL2/3, HSI48 and SHSI off before Stop 2;
  - no TIM1 ocref_clr.
- **Waiting on the owner:**
  - ruler and mouth-open photos (E9);
  - pen-tip vision test (E10);
  - 100 g temple-arm test (E12).
