# Next actions (updated 2026-09-30 evening, after the autonomous audit-fix run)

## 0. Owner decisions waiting (spec v0.14)
- **O7b, tragus arm:** A (20 mm on the plateau, 1.0–2.3 N) vs **B (30 mm elastic, 0.7–1.3 N, 54° sweep; recommended)** vs C (pivot + torsion spring). Pictures: `hw/mech/out/pod_sketches.png`, `sim/out/niti/o7b_force.png`.
- **O5, pod size:** CAD rev 2 needs 38 × 10 × 15 mm (was 35 × 9 × 14) to fit the cell's maximum envelope.
- **MCP73832 swap:** applied in schematic Rev B as recommended; revert if she prefers another fix for NM-1.
- **PWM rate (D6/MP-01):** no decision now; the bench measures the coupling first.

(Resuming the audit below is now LOW priority: the saved results were synthesised by hand and the design fixes applied. Never run it while the owner is away.)



**Read `docs/incidents/2026-09-30-oom.md` first.** The cron poke is disabled. The audit script is now capped at 5 live agents and fences its sims; resume it only from a session started with `tools/claude-session.sh`.

## 1. Resume the adversarial audit (low priority, owner present only)
It was running when the window ran low. Finished agents are cached in the run journal.
```
Workflow({scriptPath: ".claude/workflows/adversarial-methodology-audit.js",
          resumeFromRunId: "wf_ee079196-84c"})
```
Same `args` as before: `{repo, scratch, date, done:{}}` with repo `/home/hrafnavalkyrja/Desktop/ultrasonic`,
scratch `/home/hrafnavalkyrja/Desktop/ultrasonic-scratch`.
Journal: `~/.claude/projects/-home-hrafnavalkyrja-Desktop-ultrasonic/759e00a7-*/subagents/workflows/wf_ee079196-84c/journal.jsonl`

## 2. Better listening test (owner request, 2026-09-30)
Her verdict on the first set: heterodyne = informative but aesthetically poor (fallback only,
confirms D12 leaning); transient-only = good for noisy places; full = acceptable; the audible
reference was "just noise" because it was synthetic band-limited noise.

**Build a scene from REAL wide-spectrum recordings** (need >= ~192 kHz sample rate so there is
genuine 20-85 kHz content). Candidate open sources, all to be licence-checked and dated:
- Zenodo 22079773 - AudioMoth bat flypast, 192 kHz, CC-BY-4.0
- Zenodo 4996412 - on-board tag + array, 250 kHz (2.5 GB)
- Zenodo 19420408 - human-verified bat calls + noise (AudioMoth)
- Zenodo 3877572 - SONOZOTZ echolocation library
- freesound.org CC0 for audible-band ambience (nature, city) if a full-spectrum source lacks it
Prefer ONE full-spectrum field recording that already contains ambience + bats: it keeps the
audible and ultrasonic parts naturally coherent. Otherwise mix audible ambience (48 kHz,
upsampled) under a 192-250 kHz ultrasonic recording.

**Deliver 7 WAVs of the same scene** (owner's lettering):
- A: audible band only (what she hears today)
- B: full mode only, transient-only mode only (2 files, processed output alone)
- C: heterodyne only
- D-F: each of the three modes MIXED WITH the audible band = what wearing it actually sounds like
Keep true relative levels between the processed output and the audible band; say what mix ratio
was assumed (bone-conduction loudness vs ambient is not yet measured - E1/E2).

## 3. Go headless (after the audit)
Use the fenced launcher (tmux + memory fence), from the repo:
```
tools/claude-session.sh
```
Then Konsole is disposable. NOTE: `disown` alone did NOT make this session safe - it is still in
the terminal's foreground process group (`Sl+` on pts/1) and catches SIGHUP.

## 4. Cron poke
`crontab -l` fires at 3:35/8:35/13:35/18:35/23:35 local into session_01Wg997D6KFs8bxoAH56jZZJ.
**Update that session id whenever a new session starts**, or the poke goes nowhere.
