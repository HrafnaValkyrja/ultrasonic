export const meta = {
  name: 'adversarial-methodology-audit',
  description: 'Adversarial audit of the pod design process: per-area auditors, independent re-derivations, 3-lens verification, completeness critic, synthesis',
  phases: [
    { title: 'Audit', detail: '10 adversarial auditors, one per area of the work' },
    { title: 'Verify', detail: 'each finding attacked by skeptics; each "passed" check attacked for false comfort' },
    { title: 'Reproduce', detail: 'independent from-scratch re-derivations (N-version checks)' },
    { title: 'Gaps', detail: 'completeness critic, then auditors for anything missed' },
    { title: 'Synthesize', detail: 'report for the owner' },
  ],
}

// Portable: paths come from args so the same audit runs in any workspace.
//   args = { repo: '/path/to/ultrasonic', scratch: '/path/to/ultrasonic-scratch', date: 'YYYY-MM-DD',
//            done: { '<agent label>': <result>, ... } }   // results already finished elsewhere are reused
// Build `done` with: python3 .claude/workflows/export_done.py <journal.jsonl> > done.json
const A = args || {}
const REPO = A.repo || '${REPO}'
const SCR = A.scratch || (REPO + '/../ultrasonic-scratch')
const AUD = A.audit_dir || (SCR + '/audit')
const DATE = A.date || '2026-09-30'
const DONE = A.done || {}
async function run(prompt, opts) {
  if (opts && opts.label && DONE[opts.label] !== undefined && DONE[opts.label] !== null) {
    log('reusing finished result: ' + opts.label)
    return DONE[opts.label]
  }
  return agent(prompt, opts)
}

const CONTEXT = `
CONTEXT (read carefully; you have no other context).
Project: "Stereo Ultrasound", a glasses-mounted wearable that hears 20-85 kHz ultrasound and plays it back shifted to 1.5-4 kHz by bone conduction. Repo: ${REPO} (git). The owner (an engineer with RF/analogue/digital-packets/CAD/device-physics background, new to MCU boards and 4-layer PCBs) was shocked that another Claude session designed a full PCB and wants PROOF that the process, test methods and stated confidence hold up before reviewing the design. YOU ARE AN ADVERSARIAL AUDITOR. Do not trust any prior work. Your job: find where the methodology, tests, numbers or confidence are wrong or unproven, AND record what genuinely holds up with exactly how you verified it.

Key artefacts:
- docs/spec.md (source of truth; §1 is owner-locked), docs/research/*.md (A3-u575-plan.md = MCU pin/clock/SMPS plan, B-parts-selection.md = parts, C3-output-stage.md = H-bridge incl. §5 SPICE results, tragus-arm.md, bone-conduction.md, C2-cpu-budget.md, ear-open-fit.md), docs/design-review-v1.md (the design review given to the owner).
- Schematic source of truth: hw/pod/gen.py (SKiDL) -> hw/pod/pod.net (KiCad netlist) and hw/pod/bom_jlc.csv. Sourcing lock: .pcba-workflow/sourcing-lock.csv.
- Draft board: hw/pod/kicad-draft/pod.kicad_pcb (KiCad 10, self-contained; LCSC footprints/symbols/3D in that folder); placement/route script hw/pod/place.py; draft outputs hw/pod/draft/ (summary.json, drc.json).
- Sims: sim/dsp/{corpus,pipeline,run_phase1}.py; sim/checks/{bridge_spice,power,tragus_spring,pwm_noise,ntf_compare,deadtime_switching,balance,bridge_fet_compare}.py; SPICE models sim/spice/models/ (DMC2400UV.lib original from Diodes, DMC2400UV_ng.lib = convergence-patched copy). CAD: hw/mech/pod.py.
- Tools: run "source ${REPO}/tools/env.sh" first (ngspice 42, kicad-cli 10 + pcbnew python API, SKiDL, build123d, scikit-fem, python venv). pymupdf is in the harness venv (import pymupdf, or the older name fitz). tools/jlc.py queries JLC stock. tools/spice.py runs ngspice and returns numpy arrays.
- CURRENT ST documents supplied by the owner - USE THESE for the STM32U575, not the older Rev 8 copy: ${SCR}/st_new/Updated Datasheets/ (DS13737 Rev 10 datasheet, ES0499 Rev 12 errata, RM0456 Rev 7 reference manual, AN5373 Rev 7 hardware guide), with extracted text in ${SCR}/st_new/ds10.txt, es12.txt, rm7.txt, an5373.txt. What changed since Rev 8 and what was already concluded is in docs/research/datasheet-provenance.md (read it; verify rather than trust it).
- Local primary sources (text already extracted): ${SCR}/ds/*.txt and *.pdf (u575.txt = STM32U575 datasheet DS13737, pmcxb290ue.txt, tps7a20.txt, mcp73831.txt, DMC2400UV.txt, fc135.txt, dfe201610e.txt, eemb401230.txt ...), ${SCR}/u575.txt, ${SCR}/u5/ (ST docs mirror incl. possibly RM0456/ES0499), ${SCR}/sph0641_sq.pdf.txt and sph0641_synt.pdf (mic datasheets), ${SCR}/henry2007.txt, mcbride2005.pdf, stanley2006.txt (bone conduction papers), ${SCR}/t5838_v10.txt. Web access is available (load WebFetch/WebSearch via ToolSearch); record URL + access date ${DATE} for anything you use.

HARD RULES:
- Do NOT modify any tracked file in ${REPO} and do NOT git commit. Do NOT run hw/pod/gen.py, hw/pod/place.py, hw/pod/render.py or docs/learn/make_board_parts.py (they rewrite tracked files). Scripts under sim/ only write to sim/out (git-ignored) and are OK to run. For your own experiments, work in ${AUD}/<your-area>/ (create it).
- Every finding needs concrete evidence: file:line, a command you ran and its output, or a quoted primary source with location. Say explicitly whether you REPRODUCED something or are REASONING about it.
- Severity: critical = the board/device would not work, would be unsafe, or a headline claim is invalid; major = a materially wrong number/method that could mislead a decision; minor = real but low impact; info = observation.
- Be adversarial but fair: do not invent problems; if something holds up, put it in checks_passed with how you verified it.
`

const FINDINGS = {
  type: 'object',
  properties: {
    area: { type: 'string' },
    summary: { type: 'string', description: '3-6 sentences: overall verdict on this area' },
    area_confidence: { type: 'string', enum: ['high', 'medium', 'low'], description: 'your confidence that this area of the work is sound' },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          title: { type: 'string' },
          severity: { type: 'string', enum: ['critical', 'major', 'minor', 'info'] },
          kind: { type: 'string', enum: ['design_defect', 'method_flaw', 'unverified_claim', 'overconfidence', 'documentation'] },
          claim_examined: { type: 'string' },
          evidence: { type: 'string' },
          reproduced: { type: 'boolean' },
          impact: { type: 'string' },
          recommendation: { type: 'string' },
        },
        required: ['id', 'title', 'severity', 'kind', 'claim_examined', 'evidence', 'reproduced', 'impact', 'recommendation'],
      },
    },
    checks_passed: {
      type: 'array',
      items: {
        type: 'object',
        properties: { check: { type: 'string' }, how_verified: { type: 'string' } },
        required: ['check', 'how_verified'],
      },
    },
  },
  required: ['area', 'summary', 'area_confidence', 'findings', 'checks_passed'],
}

const VERDICT = {
  type: 'object',
  properties: {
    verdict: { type: 'string', enum: ['confirmed', 'partly', 'refuted'] },
    corrected_severity: { type: 'string', enum: ['critical', 'major', 'minor', 'info', 'not_an_issue'] },
    reasoning: { type: 'string' },
    evidence: { type: 'string' },
  },
  required: ['verdict', 'corrected_severity', 'reasoning', 'evidence'],
}

const FALSE_COMFORT = {
  type: 'object',
  properties: {
    unjustified: {
      type: 'array',
      items: {
        type: 'object',
        properties: { check: { type: 'string' }, why_unjustified: { type: 'string' }, evidence: { type: 'string' }, severity: { type: 'string', enum: ['critical', 'major', 'minor', 'info'] } },
        required: ['check', 'why_unjustified', 'evidence', 'severity'],
      },
    },
    upheld: { type: 'array', items: { type: 'string' } },
  },
  required: ['unjustified', 'upheld'],
}

const REPRO = {
  type: 'object',
  properties: {
    name: { type: 'string' },
    method: { type: 'string', description: 'exactly what you built/ran, independently' },
    results: { type: 'string', description: 'your numbers/findings' },
    comparison: { type: 'string', description: 'how your results compare with the original work, claim by claim' },
    agreement: { type: 'string', enum: ['agrees', 'mostly_agrees', 'disagrees', 'inconclusive'] },
    discrepancies: { type: 'array', items: { type: 'object', properties: { item: { type: 'string' }, original: { type: 'string' }, independent: { type: 'string' }, likely_cause: { type: 'string' }, severity: { type: 'string', enum: ['critical', 'major', 'minor', 'info'] } }, required: ['item', 'original', 'independent', 'likely_cause', 'severity'] } },
    artefacts: { type: 'string', description: 'paths to files you wrote under the audit dir' },
  },
  required: ['name', 'method', 'results', 'comparison', 'agreement', 'discrepancies', 'artefacts'],
}

const AREAS = [
  { id: 'netlist-mcu', title: 'Schematic vs datasheet: the MCU', prompt: `Parse hw/pod/pod.net and list every U1 (STM32U575CIUxQ, UFQFPN48 SMPS package) pin -> net. Verify against DS13737 for THIS package (the SMPS and non-SMPS UFQFPN48 pinouts differ): pin numbers and names of VLXSMPS/VDDSMPS/VSSSMPS/VDD11/VDD/VSS/VDDA/VSSA/VBAT/NRST/PH3-BOOT0/exposed pad; alternate functions ADF1_CCK0 on PB3 and ADF1_SDI0 on PB4, TIM1_CH1/CH1N/CH2/CH2N on PA8/PA7/PA9/PB0, PA0 wake-up, PA4 ADC channel, PA13/PA14 SWD, PC14/PC15 LSE, PA10 input. Verify the KiCad symbol (MCU_ST_STM32U5:STM32U575CIUxQ) pin numbering matches the datasheet for this package. Check power pin decoupling and SMPS component values against DS13737 (and AN5373 if available) requirements; VDDUSB presence; whether anything required is missing (e.g., a VDDUSB tie, VREF, missing caps). Check the logic of driving the P-channel high-side gate directly from TIM1 CHx (polarity, 3.0 V gate drive, both FETs off at reset with pulls). Check powering the mic from GPIO PA5 against the GPIO current/voltage-drop spec and the mic's supply spec.` },
  { id: 'netlist-other', title: 'Schematic vs datasheets: everything except the MCU', prompt: `Using hw/pod/pod.net and hw/pod/gen.py, verify every non-MCU part against its datasheet: PMCXB290UE custom symbol pin map (gen.py) vs datasheet Table 2 (${SCR}/ds/pmcxb290ue.txt) and the H-bridge topology (P sources to +3V0, N sources to GND, drains to outputs); SPH0641LU4H-1 pin map, SELECT tie, VDD range, clock series resistor, decoupling; MCP73831-2 pin map, PROG formula, STAT, VBAT/VDD caps; TPS7A2030PDQNR: the EasyEDA-generated symbol (hw/pod/kicad-draft/lcsc.kicad_sym) pin numbering vs the TI datasheet DQN pinout (${SCR}/ds/tps7a20.txt), EN handling, capacitor minimums, dropout at the bridge's peak current; ESD9X5.0ST5G orientation (cathode on VBUS) and PESD5V0S1BL; crystal load caps vs FC-135 CL and STM32 LSE gm margin (AN2867 method); battery-sense divider vs ADC input impedance/sampling; button circuit; gate pull values vs FET gate leakage. Evaluate system-level issues: battery protection (relies on the cell's PCM), reverse polarity, what happens when charging while running, LDO dropout vs LiPo discharge curve. Also judge the ERC: gen.py sets net.drive=POWER on some nets to silence warnings and LCSC symbols have untyped pins - did that hide real problems?` },
  { id: 'footprints', title: 'Symbol-to-footprint pad mapping and land patterns', prompt: `For every part in hw/pod/pod.net, check that each symbol pin number lands on the correct physical pad of the footprint used (LCSC footprints: hw/pod/kicad-draft/lcsc.pretty/*.kicad_mod; standard ones under $KICAD10_FOOTPRINT_DIR after sourcing tools/env.sh). Priorities: PMCXB290UE on SOT1216 (pad numbers and sizes vs Nexperia Fig. 32 in ${SCR}/ds/pmcxb290ue.txt / .pdf - render the PDF page with pymupdf if needed); TPS7A2030 X2SON-4 footprint vs TI land pattern and pin numbering; Knowles_LGA-5 footprint vs SPH0641 pad map and port hole size; FC-135 crystal; KXT321LHS switch; SOD-923 and SOD-882 polarity; QFN-48 7x7 EP 5.6x5.6 vs the U575 UFQFPN48 package drawing (EP size, pad size) in DS13737. Use the pcbnew python API to read pad positions/sizes from hw/pod/kicad-draft/pod.kicad_pcb and confirm every pad's net matches pod.net (no netlist drift). Report any mismatch with pad coordinates.` },
  { id: 'spice-bridge', title: 'H-bridge SPICE methodology', prompt: `Audit sim/checks/bridge_spice.py and docs/research/C3-output-stage.md §5. Check: (1) model applicability - DMC2400UV stands in for the chosen PMCXB290UE: compare Ciss/Qg/RDSon at VGS=3 V/Vth/body diode from both datasheets and say how the results would shift; (2) the convergence patch (DMC2400UV_ng.lib adds RS/CJO to the DLIM diode): run original vs patched on a short case that converges with both and quantify any change; (3) measurement correctness: sign/definition of bus current, the gate-current '/2' logic, THD+N computation (window, 10 MHz resampling, band limits, record length after the retry logic, settling time), whether 'duty not quantised' makes the result optimistic; (4) the 100 ps inter-leg skew and the 'stop half a period early' hacks; (5) gate-drive model (30 ohm, 2 ns edges) vs STM32 GPIO output characteristics at 3 V; (6) hand-calculate the expected ripple current, I^2R loss, and shoot-through; (7) re-run the script (source tools/env.sh; python3 sim/checks/bridge_spice.py) and confirm the table reproduces. Is the headline 'dead time 12.5 ns: 0.49 mA idle, -61 dB THD+N at -40 dBFS, -52 dB at -12 dBFS' credible? Also check pwm_noise.py / ntf_compare.py / deadtime_switching.py for the earlier claims they support.` },
  { id: 'dsp', title: 'DSP simulation methodology', prompt: `Audit sim/dsp/corpus.py, pipeline.py, run_phase1.py and the claims in docs/design-review-v1.md §2 and spec §7 (14% awake on a quiet evening with all 4 events caught within 10 ms; output confined to 1.5-4 kHz without clicks; silence ~-80 dBFS; whines removed). Look for: circularity (thresholds tuned on the same scenes they are judged on), corpus realism (levels, bat call shapes, spectra), the microphone noise model (audio-band EIN spread flat to 100 kHz - is SPH0641 ultrasonic self-noise known?), decimation filter adequacy, the log mapping math, attack/release effects on timing, the limiter, whether 'click-free' was measured or only eyeballed, whether the CPU cost is realistic for a Cortex-M33 at 80 MHz. Run the scripts (python3 sim/dsp/run_phase1.py) and confirm the numbers reproduce. Then attack the claims with NEW inputs you write in ${AUD}/dsp/: different seeds; louder speech/footsteps/rain/wind-like broadband noise; a whine that switches on/off or is frequency-modulated (fan/PWM whine); a quiet distant bat at 50 dB SPL; two simultaneous bats; measure awake fraction, event detection latency, false wakes, and output spectrum leakage outside 1.5-4 kHz. Report numbers.` },
  { id: 'power', title: 'Power budget and runtime', prompt: `Audit sim/checks/power.py and spec §7. Verify every current against a primary source with table/figure number: STM32U575 run current at 80 MHz range 2 on SMPS (DS13737 tables; which conditions?), 16 MHz range 3 idle assumption, Stop 2, ADF/peripheral currents; SPH0641 ultrasonic-mode current at 3.0 V/4 MHz; TPS7A2030 Iq; MCP73831 battery drain when not charging; divider; bridge current (compare with C3 §5 SPICE); transducer current (trace where 0.6-1.7 mA came from and whether it is justified); the 85% usable capacity; whether the LDO dropout at the LiPo's low end (TPS7A20 dropout at the real load) limits usable capacity; charger termination. Recompute runtime for 105 mAh independently and say whether '11.9-15 h always awake' is supportable, and what the true uncertainty band is.` },
  { id: 'mech', title: 'Mechanical: NiTi spring model, CAD, balance', prompt: `Audit sim/checks/tragus_spring.py, hw/mech/pod.py, sim/checks/balance.py and docs/research/tragus-arm.md. Check: the NiTi model (moment-curvature with an elastic/flat plateau; SMALL-slope kinematics used for 7-14 mm deflection on a 20 mm arm - quantify the large-deflection error, e.g. with an elastica solve), plateau values and their sources (Confluent SE508 sheet, US 6,706,053), hysteresis treatment, 'force stays ~1 N' claim, strain localisation at the root; the torsion-spring formula (SMI) and stress incl. Wahl factor; the steel-strip 'cannot reach 1 N under fatigue limit' claim; the +-2 mm jaw assumption; the temple-arm reaction/twist estimate; CAD interference check validity (does it catch arm/pad vs pod? pod vs temple?), PA12 density source, masses and centre of mass, and the nose/ear load-split model in balance.py (is the 100 mm lever and statics right?). Recompute the key numbers independently (write your own code in ${AUD}/mech/).` },
  { id: 'layout-drc', title: 'Layout and DRC methodology', prompt: `Audit hw/pod/place.py and the claim 'fully routed, DRC clean at JLC minimums'. Verify JLC 4-layer capabilities from JLC's own capabilities page (date it): min trace/space, min via drill/diameter, hole-to-copper, copper-to-board-edge, and the 0.8 mm 4-layer stackup. Compare with the board's actual rules in hw/pod/kicad-draft/pod.kicad_pcb/.kicad_pro (read them via pcbnew or the file). Run 'kicad-cli pcb drc --severity-all --schematic-parity? (no schematic)' on a COPY of hw/pod/kicad-draft/ in ${AUD}/layout/ and report all errors AND warnings, not just errors. Evaluate: the post-route widening of necked tracks (could it hide violations?), the clearance relaxed to 0.09 mm after routing at 0.1, excluding pad courtyards, missing GND plane, via-in-pad or vias under the QFN, thermal/EP connection, the mic port, SMPS loop length, silkscreen over pads, solder-mask bridges, and whether the draft board's pad nets match hw/pod/pod.net exactly. Is 'DRC clean' an honest description?` },
  { id: 'research-claims', title: 'Do the cited sources say what the docs claim?', prompt: `Pick at least 15 load-bearing factual claims from docs/spec.md and docs/research/*.md and check each against the cited primary source (local copies under ${SCR} and ${SCR}/ds, or the web). Must include: bone conduction at the pre-tragal/cartilage site ~+10 dB and 25-40 dB left/right isolation (bone-conduction.md; papers henry2007, mcbride2005, stanley2006 in ${SCR}); bone-conducted ultrasound thresholds 55-60 dB higher; SPH0641LU4H-1 ultrasonic response (+14.7 dB at 25 kHz etc. vs sim/data/sph0641_ultrasonic_response.json) and 845 uA; STM32U575 current per MHz (19.5 vs 40-45 uA/MHz claims); ADF sinc5 / RSFLT decimation claims; TPS7A20 noise/Iq/dropout; MCP73831 IREG=1000V/RPROG; NiTi plateau stresses; 301 full-hard yield/fatigue; FC-135 CL/ESR and the 'FC-12M fails gm' claim; JLC stock counts (re-query with python3 tools/jlc.py <part>; note today's date). For each: claim, where it appears, cited source, what the source actually says (quote + page), verdict (supported / partly / unsupported / misquoted).` },
  { id: 'meta-process', title: 'Process, self-corrections and confidence calibration', prompt: `Audit the PROCESS, not a component. Read 'git -C ${REPO} log --stat' (all commits), the spec changelog (§15), docs/research/review-2026-09-30.md and C3 §5 'testbench bugs'. Catalogue every error the session caught in its own work (e.g., MCU current overstated ~3-4x, BD vs AD modulation, PWL time precision, THD quantisation artefact, THD aliasing, board outline arcs, courtyard blind spot for LCSC footprints, board height 10->11.5 mm, unstable b/a filter in the corpus, clicks in DSP output, 2012 crystal rejected, and others you find). For each: how it was caught, how late, what would have happened if missed, whether a systematic check would have caught it earlier. Estimate how many errors of similar kind likely remain undetected (reason from the catch pattern). Evaluate the [High]/[Med]/[Low] confidence tags in spec.md against their evidence - list tags that are overconfident. Identify every place where the same author wrote both the model and its test (self-referential validation). List what this process fundamentally cannot verify without hardware. Give an honest assessment of the AI's abilities and failure modes in this domain based on the evidence.` },
]

const REPRODUCTIONS = [
  { id: 'repro-bridge', prompt: `INDEPENDENT N-VERSION CHECK. Without reading sim/checks/bridge_spice.py or C3-output-stage.md §5 until you have your own numbers, write your own ngspice testbench from scratch in ${AUD}/repro-bridge/: a full H-bridge of two DMC2400UV complementary pairs (model: ${REPO}/sim/spice/models/DMC2400UV.lib; if convergence fails, you may regularise it yourself and must document how), 3.0 V supply with realistic decoupling, load 8 ohm + 0.3 mH, 2-level (AD) PWM at 200 kHz generated your own way (e.g. comparator vs triangle or PWL), dead times 0, 12.5, 25 ns. Measure: idle supply current, shoot-through current, and in-band (0.3-16 kHz) THD+N of the coil current for a 2 kHz tone at -12 dBFS and -40 dBFS (modulation index 0.251 and 0.01). Only AFTER you have results, read bridge_spice.py and C3 §5 and compare claim by claim. Explain every discrepancy.` },
  { id: 'repro-netlist', prompt: `INDEPENDENT N-VERSION CHECK OF THE SCHEMATIC. Without reading hw/pod/gen.py or hw/pod/pod.net first, derive from the spec (docs/spec.md), docs/research/A3-u575-plan.md (pin map), docs/research/B-parts-selection.md and the datasheets what every connection on the pod board SHOULD be: write your own expected netlist in ${AUD}/repro-netlist/expected.json (for each part/pin: the net). Then compare it with hw/pod/pod.net programmatically and list every difference, and for each difference decide who is right using the datasheet.` },
  { id: 'repro-power', prompt: `INDEPENDENT N-VERSION CHECK OF RUNTIME. Without reading sim/checks/power.py or spec §7 first, compute from primary datasheets only (STM32U575 DS13737 in ${SCR}/ds/u575.txt, SPH0641 in ${SCR}, TPS7A20, MCP73831, bridge/transducer assumptions you justify) the per-side battery current when the processing chain is fully active (80 MHz, FFT+oscillators ~55-80% busy, mic in ultrasonic mode, bridge switching at 200 kHz into 8 ohm + 0.3 mH at a modest listening level) and when idle-listening (16 MHz, band detectors, bridge off), and the runtime on a 105 mAh LiPo at 0%, 14%, 50%, 100% awake. Only then read sim/checks/power.py and spec §7 and compare claim by claim.` },
  { id: 'proper-sim', prompt: `The owner said: "if the design works in a proper sim, I guess that speaks for itself". Determine what a 'proper simulation' of THIS board can and cannot be with available tools. Research (web, dated): Renode and QEMU support for STM32U5 (incl. ADF/MDF, TIM1, GPDMA) - could the firmware run in emulation?; ngspice / KiCad simulator for the analog subcircuits (LDO + charger + bridge + transducer + mic supply) from the real netlist - try to actually build a SPICE deck of the power path (battery -> TPS7A20 behavioural or vendor model -> bridge load step) in ${AUD}/proper-sim/ and run it; PDN/SI tools (openEMS, KiCad's field solvers) for the 4-layer board; mechanical FEM. For each: what it would prove, what it cannot, effort. Then propose a concrete verification ladder from here to first power-on and first sound, stating which risks each rung retires. Be blunt about what no simulation can prove for this device (e.g. bone-conduction loudness, comfort, SMPS audibility).` },
]

function auditPrompt(a) {
  return `${CONTEXT}\nYOUR AREA: ${a.title} (id: ${a.id}).\n${a.prompt}\nWork in ${AUD}/${a.id}/. Return structured findings; set area to "${a.id}". Aim for depth over breadth, but do not stop at the first problem: cover the whole area.`
}

const LENSES = {
  reproduce: 'Independently REPRODUCE or re-derive the finding (run the command, redo the calculation, re-read the file). If you cannot reproduce it, say so.',
  source: 'Check the finding against the PRIMARY SOURCE (datasheet, standard, manufacturer page, the actual file). Is the finding\'s reading of the source correct?',
  impact: 'Judge IMPACT and SEVERITY: is it real for this design, already mitigated or documented elsewhere in the repo (grep docs/), and is the severity right?',
}

async function verifyFinding(f, area) {
  const lenses = (f.severity === 'critical' || f.severity === 'major') ? ['reproduce', 'source', 'impact'] : (f.severity === 'minor' ? ['reproduce'] : [])
  if (!lenses.length) return { ...f, area, verdicts: [], survives: true, final_severity: f.severity }
  const votes = await parallel(lenses.map(l => () => run(
    `${CONTEXT}\nYou are a SKEPTIC. Another auditor (area ${area}) reported this finding. Try to REFUTE it. ${LENSES[l]} Default to refuted only if you have evidence it is wrong; if it is right, say confirmed and correct the severity if needed.\nFINDING:\n${JSON.stringify(f, null, 2)}`,
    { phase: 'Verify', label: `verify:${area}:${f.id}:${l}`, schema: VERDICT })))
  const vs = votes.filter(Boolean)
  const refuted = vs.filter(v => v.verdict === 'refuted').length
  const survives = vs.length === 0 ? true : refuted < Math.ceil(vs.length / 2 + 0.01)
  const sevs = vs.filter(v => v.verdict !== 'refuted').map(v => v.corrected_severity)
  const order = ['critical', 'major', 'minor', 'info', 'not_an_issue']
  const final_severity = sevs.length ? sevs.sort((a, b) => order.indexOf(a) - order.indexOf(b))[Math.floor(sevs.length / 2)] : f.severity
  return { ...f, area, verdicts: vs.map((v, i) => ({ lens: lenses[i], ...v })), survives, final_severity }
}

phase('Audit')
log(`Auditing ${AREAS.length} areas, plus ${REPRODUCTIONS.length} independent reproductions`)

const auditsP = pipeline(
  AREAS,
  a => run(auditPrompt(a), { phase: 'Audit', label: `audit:${a.id}`, schema: FINDINGS }),
  async (res, a) => {
    if (!res) return { area: a.id, missing: true }
    const verified = await parallel(res.findings.map(f => () => verifyFinding(f, a.id)))
    const fc = res.checks_passed.length ? await run(
      `${CONTEXT}\nYou are a FALSE-COMFORT SKEPTIC for area ${a.id}. The auditor claims these checks PASSED. For each, try to show the verification was insufficient, circular, or wrong (re-check the evidence yourself). Only mark unjustified with evidence.\nCHECKS:\n${JSON.stringify(res.checks_passed, null, 2)}`,
      { phase: 'Verify', label: `false-comfort:${a.id}`, schema: FALSE_COMFORT }) : null
    return { ...res, verified: verified.filter(Boolean), false_comfort: fc }
  })

const reprosP = parallel(REPRODUCTIONS.map(r => () => run(`${CONTEXT}\n${r.prompt}\nSet name to "${r.id}".`, { phase: 'Reproduce', label: r.id, schema: REPRO })))

const [audits, repros] = await Promise.all([auditsP, reprosP])

phase('Gaps')
const digest = audits.filter(Boolean).map(a => ({ area: a.area, summary: a.summary, confidence: a.area_confidence, findings: (a.verified || []).map(f => `${f.final_severity}${f.survives ? '' : ' (refuted)'}: ${f.title}`), passed: (a.checks_passed || []).map(c => c.check) }))
const critic = await run(`${CONTEXT}\nYou are the COMPLETENESS CRITIC. Below is a digest of an adversarial audit of this project's design process, and a list of independent reproductions. Identify what was NOT audited or only superficially covered: parts, nets, scripts, claims, docs, failure modes (safety: LiPo, skin contact, ESD; EMC; thermal; manufacturability; firmware feasibility; the mechanical fit data from photos; the parts sourcing/stock risk; the claims made to the owner in docs/design-review-v1.md). Return up to 5 concrete gap areas worth a dedicated auditor, each with a precise prompt.\nDIGEST:\n${JSON.stringify(digest, null, 1)}\nREPRODUCTIONS: ${JSON.stringify(repros.filter(Boolean).map(r => ({ name: r.name, agreement: r.agreement })))}`,
  { phase: 'Gaps', label: 'completeness-critic', schema: { type: 'object', properties: { gaps: { type: 'array', items: { type: 'object', properties: { id: { type: 'string' }, title: { type: 'string' }, prompt: { type: 'string' } }, required: ['id', 'title', 'prompt'] } } }, required: ['gaps'] } })

const gapAreas = (critic && critic.gaps) ? critic.gaps.slice(0, 5) : []
if (critic && critic.gaps && critic.gaps.length > 5) log(`Critic proposed ${critic.gaps.length} gaps; auditing the first 5`)
const gapAudits = await pipeline(
  gapAreas,
  g => run(auditPrompt({ id: 'gap-' + g.id, title: g.title, prompt: g.prompt }), { phase: 'Gaps', label: `gap:${g.id}`, schema: FINDINGS }),
  async (res, g) => {
    if (!res) return null
    const verified = await parallel(res.findings.map(f => () => verifyFinding(f, 'gap-' + g.id)))
    return { ...res, verified: verified.filter(Boolean) }
  })

phase('Synthesize')
const allAudits = [...audits, ...gapAudits].filter(Boolean)
const report = await run(`${CONTEXT}\nYou are the SYNTHESIS author. Write the final audit report for the OWNER (engineer: RF/analogue/digital packets/CAD/device physics; new to MCU boards and 4-layer PCBs; blunt, wants proof). Write it as Markdown to ${AUD}/report.md and return the same Markdown as your final text.
Structure:
1. Verdict in one paragraph: can this process be trusted, for what, and where not.
2. What is actually proven, and how (only items with evidence that survived the false-comfort skeptic).
3. Confirmed problems, ranked by final severity (only findings with survives=true; show final severity, what, evidence, fix). Separate DESIGN defects from METHOD/PROCESS flaws. Mention refuted findings briefly in an appendix.
4. Independent reproductions: table of each N-version check, agreement, discrepancies.
5. Confidence calibration: table of the headline claims made to the owner (docs/design-review-v1.md and spec §7/§8 numbers) -> confidence stated -> confidence the audit supports -> why.
6. What no simulation can prove here, and the recommended verification ladder (from the proper-sim reproduction).
7. Methodology changes the process should adopt (concrete).
Be precise, cite file paths, keep it readable (tables where they help), no fluff, no reassurance that isn't earned.
AUDITS (verified):\n${JSON.stringify(allAudits.map(a => ({ area: a.area, summary: a.summary, area_confidence: a.area_confidence, findings: a.verified, checks_passed: a.checks_passed, false_comfort: a.false_comfort })), null, 1)}
REPRODUCTIONS:\n${JSON.stringify(repros.filter(Boolean), null, 1)}`,
  { phase: 'Synthesize', label: 'synthesis' })

return {
  report_path: AUD + '/report.md',
  counts: allAudits.map(a => ({ area: a.area, confidence: a.area_confidence, total: (a.verified || []).length, surviving: (a.verified || []).filter(f => f.survives).map(f => f.final_severity) })),
  repro: repros.filter(Boolean).map(r => ({ name: r.name, agreement: r.agreement, discrepancies: r.discrepancies.length })),
  gaps: gapAreas.map(g => g.title),
}
