# Prior art: agent swarms for physical engineering

**Date:** 2026-10-01 · **Status:** research synthesis. It proposes; the owner decides (spec §0 rule 4). Nothing here changes the spec, `docs/system/` or any tool.

## Bottom line (read this first)

- **Is it new? Mostly no. The combination is, and that is the hard part.** Each ingredient has prior art, some of it 30 years old: hardware defined as code; an AI agent that writes a design, runs a checker (a program that says pass or fail, such as ERC/DRC, a testbench or a simulation with limits) and repairs from the errors; a lead agent spawning parallel sub-agents; 1990s agents that wrap engineering tools and share a design record; change-impact tracking. **Not found in about 100 opened works:** agent teams across electronics, mechanics and firmware on one physical product, with change control down to a net, a part or a CAD symbol, check-out conflict flags between teams, ECRs (engineering change requests) and one human approver.
- **The frontier is integration and verification across domains, not generation.** Every documented agent loop is exactly as good as its checker. Exact, localising checkers give 94-96 % (digital logic) and 0.65 board completion (PCB routing with DRC after every step). Checkers that merely run give "88 % executable, 2 of 15 valid" (FEABench), and an autonomous lab's "41 new materials" turned out not to be new (A-Lab).
- **Two frontiers we have not crossed.** (1) The loop through physical test: rev 1 is still ahead. (2) "Generative design" in the optimiser sense: today our numbers are agent-written and checker-verified, not optimised.
- **Biggest dangers, with evidence.** Parallel teams on coupled work lose (-39 % to -70 % on sequential planning). Same-model verifiers share blind spots (60 % shared wrong answers on one dataset). Our check-outs are advisory and have never run. Our checkers print numbers but almost never assert them (1 of 14 `sim/checks` scripts).
- **Do first (all "now", about 4-5 agent-days):** L1 falsifiers and asserts, L2 serialise coupled work, L3 audit the checkers, L4 one git worktree per team with a gated merge, L5 one geometry source plus a real-board clash check, L6 a SKiDL rule checker built on the MIT-licensed PCBSchemaGen v2 verifier, L7 decorrelated verifiers.
- **Limit:** web search ran out early, so commercial and industrial agent systems (Flux, Quilter, JITX, Siemens, PTC, Synopsys) were not seen. "Not found" means not found in what we opened.

**Question (owner, 2026-10-01):** what prior art exists for running "agentic swarms" (many AI agents working in parallel under a lead) on physical engineering? Her framing: we combine *generative design*, *generative project management* and *logic-to-hardware*, at the edge of a frontier. Is it new? What can we borrow, across domains?

**Picture:** [`docs/diagrams/prior-art-map.png`](../diagrams/prior-art-map.png). It puts each prior-art cluster against the stage of our pipeline it informs, and tags each cluster with the lessons (L1–L15) below.

![Prior art mapped onto our pipeline](../diagrams/prior-art-map.png)

**How this was made.**
- Four research lenses each wrote a notes file in [`prior-art/`](prior-art/):
  - [`llm-design-agents.md`](prior-art/llm-design-agents.md): LLM agents for circuits, PCBs, CAD and FEA, 2023–26.
  - [`classic-concurrent-engineering.md`](prior-art/classic-concurrent-engineering.md): the pre-LLM precedent, 1968–2022.
  - [`generative-design-hw-as-code.md`](prior-art/generative-design-hw-as-code.md): generative design and hardware as code.
  - [`agentic-pm-orchestration.md`](prior-art/agentic-pm-orchestration.md): multi-agent orchestration and generated project management.
- An independent fact-checker re-opened every cited work and licence. Its corrections are applied here and summarised in section 6; where this note and a lens note disagree, this note wins.
- About 100 works were opened in total. Every citation below carries its URL, its access date and how much of it was read (full text, abstract only, README). Anything seen only as metadata is labelled **unverified**.
- **Coverage limit, stated up front:** the web-search budget was exhausted early. Discovery went through arXiv, Hugging Face Papers, OpenAlex, Semantic Scholar, CrossRef and direct fetches. Commercial and industrial agent systems (Flux, Quilter, JITX, Zoo, Siemens, PTC, Synopsys) were **not** seen. "Nobody has done X" below means "not found in what we opened", not "proven first".

**Terms used throughout** (each also glossed where it first matters):
- **Agent / multi-agent system:** an LLM (large language model) that runs tools in a loop; several of them, each with a role, coordinated by a script or a lead agent.
- **Oracle / checker:** the program that decides whether an output is right (a testbench, ERC, DRC, a simulation with pass limits).
- **ERC / DRC:** electrical rules check (schematic) and design rules check (PCB geometry).
- **PLM:** product lifecycle management: tracking items, their interfaces and their changes. Ours is `tools/plm.py`.
- **ECR:** engineering change request, a proposed change with its computed impact, approved by the owner.
- **ICD:** interface control document: the agreed values and tolerances at an interface, signed by both sides.
- **DSM:** design structure matrix: a square table, one row and one column per item; a mark means "this item depends on that one". Clustering it finds tightly coupled groups.
- **SBCE:** set-based concurrent engineering (Toyota): teams carry *ranges* of feasible values, not single choices, and narrow them late.
- **Blackboard:** a shared workspace that independent specialists read and write; a *monitor* decides who acts next. Our `docs/system/` plus the repo is one.

---

## 1. Is this new? The evidence

**Mostly no, and the part that is new is the hardest part.** Every *ingredient* has prior art, much of it 30 years old. The *combination* has none that we found.

| Piece of our setup | Done before? | Best evidence |
|---|---|---|
| Hardware defined as code (SKiDL schematics, build123d CAD) | **Yes, mature.** | SKiDL (2016 on), Polymorphic Blocks [PolyBlocks] 2020, atopile, circuit-synth [CircuitSynth] (which even ships Claude Code agents), build123d / CadQuery. |
| An agent generates a design in one domain, a tool checks it, the agent repairs it | **Yes, crowded.** Success tracks the checker. | Digital logic: 94–96 % on VerilogEval v2 [VerilogCoder, MAGE]. SKiDL schematics with a rule verifier [PCBSchemaGen]. PCB routing with DRC after each step [PCBWorld]. CAD with executable tests [CADTests]. FEA set-up [FEABench]. |
| A lead agent spawning parallel subagents | **Yes, in software and research.** | Anthropic's research system [Anthropic-MA]; CAID [CAID] (worktrees plus a test-gated merge); MetaGPT [MetaGPT]. |
| Agents wrapping engineering tools, coordinating through a shared design record with change notification | **Yes, 1993–97.** | PACT [PACT], SHADE [SHADE], Redux/Next-Link [Redux]. The line faded (§1.2). |
| Where-used impact, suspect links, change propagation | **Yes, established.** | Steward's DSM (1981) [Steward]; the Change Prediction Method [CPM]; Doorstop; Teamcenter-style PLM. |
| A human chief engineer narrowing agent-explored options | **Yes, two precedents.** | Toyota's chief engineer and SBCE [Sobek99]; an agentic set-based design team with a human manager, one physics domain (airfoils) [BrownSBD]. |
| Agents going from spec to a fabricable artefact end-to-end | **Yes, within one domain.** | Design Conductor reports a 219-word spec → tape-out-ready chip layout (GDSII) in 12 h, autonomously [DesignConductor] (abstract only, company report). ASIC-Agent [ASICAgent] integrates inside one domain. |
| Agent teams across **electronics + mechanics + firmware** on one physical product, with generated change control at the granularity of a net, a part reference or a CAD symbol, check-out conflict flags between concurrent agent teams, ECRs, and one human approver | **Not found.** | Nearest: Makatura et al.'s quadcopter, where humans gave the low-level mounting instructions [Makatura]; Text2Robot, which hard-coded the electronics bay into its geometry generator [Text2Robot]; Circuitron, a SKiDL multi-agent tool, electronics only [Circuitron]; CAID, Claim Plane and Relic, software only. |
| Generative project management: agents operating change control | **Not found.** | The LLM-PM literature is single-shot GPT-4 planning and risk studies from 2023 [Barcaui23, RiskGPT23]. |
| Closing the loop through physical test | **Narrow, and it is where automated loops have failed.** | Lipson–Pollack evolved robots, fabricated (2000) [LipsonPollack]; NASA's evolved ST5 antenna, flown 2006 [ST5, ST5launch]; A-Lab's autonomous materials lab, whose "41 new compounds" a re-analysis found were not new [ALab, ALabCritique]. **We have not crossed this yet.** |

### 1.1 Where exactly the frontier is

**The frontier is integration and verification across domains, not generation.** Generating a schematic, a CAD part or firmware from a prompt is a crowded field. Keeping an electrical, a mechanical and a firmware design *mutually consistent* while several agent teams change them, with one human deciding, has no precedent we found.

What we have built for that:
- **The bookkeeping:** `plm.py` watches on nets, part references and Python CAD symbols; SUSPECT/STALE flags; check-outs; ECRs.
- **The generated integration map** from the netlist (`docs/system/integration-map.md`).

That bookkeeping is the genuinely novel part. Doorstop-style stamps are not new; their *granularity across ECAD, MCAD and docs*, and check-outs for agent teams, are.

Three blunt qualifiers:
1. **Being first means there is no proven recipe.** Every failure mode the prior art documents applies to us. We have no benchmark that tells us our pipeline works.
2. **Our bookkeeping detects change, not disagreement.** `methodology.md` §1 already found this: a hash watch can't see that the two sides of an interface disagree. The two live defects (mic port 0.75 mm off; bridge peaks on a 300 mA LDO) were found by hand. The prior art's loudest single finding (§3, L1) is that **agent loops are exactly as good as their checker**.
3. **"Generative design" is a stretch today.** In the usual (Autodesk) sense, an optimiser grows a shape from loads and goals. We do *agent-authored, checker-verified* design: nearly every number is written by an agent and checked, not optimised. L13 is how to earn the word.

### 1.2 Why the 1990s agent-engineering line faded, and what that means now

PACT (1993), SHADE (1993), Redux (1995) and DIDE (1995–97) were our architecture, 30 years early: tool-wrapping agents coordinating through a shared design record. The line got little documented industrial uptake for design coordination.

**What the sources actually say:**
- Shen, Hao & Li 2008 (full text) [Shen08]: the agents built "are actually not very 'intelligent'"; progress on shared ontologies (formal shared vocabularies) "has not been satisfactory", listed as an open challenge; industry adopted PDM/PLM.
- Whitfield et al. 2000 (full text) [Whitfield00]: PACT broadcast every design change to every agent, which caused "excessive unnecessary communication"; SHADE added content-directed routing to fix it.

**Our reading** (a synthesis, not a claim either paper makes) of why it faded:
- weak agents;
- the cost of agreeing ontologies (KQML/KIF, 1990s agent message and knowledge formats) [KQML];
- a hand-built wrapper for every legacy tool;
- PLM offered a simpler, centralised alternative.

**What has changed for us:**
- LLMs read native files and prose, so no ontology layer is needed.
- Our tools are code-native (SKiDL, `pcbnew`, build123d, `kicad-cli`), so there are no wrappers to build.
- Agents write their rationale as a side effect, at near-zero cost.

**What has not changed, and is still ours:**
- *Control:* which agent acts next. Nii 1986 [Nii86]: "there is no control component specified in the blackboard model". Control was then studied heavily (BB1, agenda-based and goal-directed control, the termination problem) [CarverLesser], but there is no cheap general answer for open-ended design.
- *Notification overload:* PACT's broadcast; our flat ECR impact lists.
- *Convergence on tightly coupled decisions:* Klein et al. 2003 [Klein03].
- *Keeping the dependency model true:* Brahma & Wynn's review of change-propagation work (2022) [BrahmaWynn] found **no paper reporting ongoing industrial use**. 70 of the 143 publications they classified were demonstrated only on the authors' own examples.

---

## 2. Map: prior art by lens → our process

The picture above shows the same mapping. Strength of precedent: **strong** = proven method to copy; **partial** = weak or transferred evidence; **warning** = failure evidence to guard against.

| Our piece | Closest prior art | What it showed | Strength | Lessons |
|---|---|---|---|---|
| **Owner gate** (O-items, ECRs, orders) | Toyota chief engineer and SBCE [Ward95, Sobek99]; Magentic-UI [MagenticUI]; agentic set-based design [BrownSBD]; Chip-Chat [ChipChat] | Narrow late; co-plan; ask rarely and where it matters. Chip-Chat taped out an AI-written CPU with a human setting constraints throughout. | strong | L12, L14 |
| **Lead AI** (area manager, monitor) | Blackboard control [Nii86, CarverLesser]; Contract Net [ContractNet]; LLM blackboards [HanZhang25, Salemi25]; Anthropic lead + subagents [Anthropic-MA] | A shared record plus a monitor works. Post-and-volunteer allocation is Smith's 1980 Contract Net, re-found in 2025 (13–57 % relative gains over strong baselines, non-engineering tasks). | partial | L2 |
| **Explore: parallel domain teams** | Kim et al. scaling study [KimScale]; CooperBench [CooperBench]; MAST [MAST]; Klein 2003 [Klein03]; mirroring [Sosa04, MacCormack12, Conway68] | Parallel agents win on decomposable work and lose on coupled work. Team boundaries that cut coupling cost convergence. | **warning** | L2, L10 |
| **Per-domain generation** inside each team | [VerilogCoder, MAGE, PCBSchemaGen, PCBWorld, CADTests, AnalogCoder, EmbedAgent] | Near-saturation with an exact, localising checker; small gains with a weak one; 0 % completion on large boards. | strong (single domain) | L1, L6 |
| **Adversarial verify + audit** | Knight & Leveson N-version [KnightLeveson]; self-correction [HuangSC, CRITIC, Kamoi]; correlated errors [KimCorr]; self-preference [Panickssery]; debate [Khan24, ZhangMAD, Bertalanic]; voting [SelfConsistency, MoreAgents] | Same-model checks are correlated. Self-correction needs outside feedback. A judge between two sides works; voting after debate fails; independent voting helps. | **warning** | L1, L3, L7 |
| **Integrate (serial merge) + synthesize** | CAID [CAID]; Claim Plane [ClaimPlane]; Relic [Relic]; Contracts [Contracts26]; NASA interface management [NASA63]; Croto [Croto] | Worktree isolation plus a test-gated merge beats "soft" file assignment. Executable rules beat written ones. Interfaces need every required side's sign-off. Prune options before synthesis. | partial (software only) | L4, L9 |
| **Blackboard + PLM tracker** (`docs/system`, `plm.py`) | PACT/SHADE/Redux; Steward DSM [Steward]; CPM [CPM]; Brahma & Wynn [BrahmaWynn]; margins [Eckert19]; Doorstop | Our watches are SHADE subscriptions; SUSPECT is Redux's dependency-directed notification. Later work added ranking, margins and DSM clustering. | partial | L8, L9, L10 |
| **Agent context** (CLAUDE.md, workflow prompts, skills) | AGENTS.md evaluation [Gloaguen]; STALE [STALE]; Agent READMEs [AgentREADMEs]; Repo2Skill-Evo [Repo2Skill] | Context files bring no general gain and +20 % cost. Agents notice stale memory about 55 % of the time. Skills go stale silently. | **warning** | L11 |
| **Code-defined hardware + sim checks** | Polymorphic Blocks; atopile; KiCad StepUp; FEABench; CADTests; SPhyR [SPhyR]; BikeBench [BikeBench] | Typed electrical limits, assertions and real-board-in-shell clash checks are standard practice. "It runs" ≠ "it is right". LLMs can't eyeball physics. | strong tools, **warning** on checks | L3, L5, L6, L13 |
| **Rev-1 physical test** | Lipson–Pollack; NASA ST5; Matthews et al. 2023 [Matthews23]; A-Lab and its critique; OpenHTF; multi-fidelity review [MFBO] | Loops close only where the evaluator is trusted. An unreliable automated checker sank A-Lab's headline. | partial | L3, L15 |

---

## 3. Lessons, ranked

**Ranking:** value × urgency, for a one-shot rev-1 order (O20) built by hand (O19). "Now" means before the next parallel design-team run and the rev-1 re-size. "Soon" means before the sourcing lock and the joint layout session (O14). "Later" means before the order or the first build. Effort is in agent hours.

Several lessons **independently confirm** the ranked improvements in [`methodology.md`](methodology.md) §2 (marked M1–M10) and its §5 team rules. Where they overlap, do it once, the methodology way. **New in this note:** L1's falsifier rule, L3, L5, L6, L7, L11, L12, L13, L14.

| # | Lesson | Priority | Effort | Overlaps |
|---|---|---|---|---|
| L1 | Verifiers return falsifiers; every check asserts spec numbers and rejects defaults | **now** | 2 h + ~0.5 h per script | M1 |
| L2 | Serialise coupled design; parallelise only decomposable work | **now** | 1–2 h | §5.6 |
| L3 | Audit the checker: mutation tests; owner reviews automated physical pass/fail | **now** | ~3 h, then 15 min per new check | — |
| L4 | One git worktree per team; merge through an executable gate | **now** | 3–4 h | M4, §5.3 |
| L5 | One shared geometry source; real-board STEP clash check | **now** | ~1 day + an owner install | M1, M2 |
| L6 | SKiDL rule checker built on the PCBSchemaGen v2 verifier | **now** | ~1 day | M1 |
| L7 | Decorrelate verifiers; never vote after debate | **now** | 1–2 h | — |
| L8 | Machine-readable margins on relations | soon | 2–3 h | M6, M7 |
| L9 | Two-sided interface sign-off; drop `review ALL` for relations | soon | 2–3 h | M6 |
| L10 | DSM clusters set team scopes; rank change impact | soon | 4–6 h | M5, M7 |
| L11 | Agent-facing text: lean, under PLM watches, MAST-linted | soon | 2 h | — |
| L12 | Owner gate tiered by reversibility; co-plan; one advocate per option | soon | 2–3 h | §5.1 |
| L13 | Agents pick structure, solvers pick numbers; Pareto + sensitivity | soon | 0.5–1 day | — |
| L14 | Set-based exchange for open trade-offs, in CAD and simulation only | later | 2–4 h per decision | — |
| L15 | Close the loop through physical test; calibrate the models | later | ~4 h + 15 min per build | M8, M10 |

### Multi-agent failure modes at a glance

Percentages are MAST's [MAST] per-failure-mode shares of 1,600+ annotated traces (7 frameworks, mostly software tasks). MAST's category totals are not quoted: they could not be found in the paper's text.

| Failure mode | Evidence | Mitigation here | Lesson |
|---|---|---|---|
| Repeating steps (15.7 %), not knowing when done (12.4 %), disobeying the task spec (11.8 %) | MAST; clearer role specs gave +9.4 % on ChatDev | Termination condition and role spec in every workflow prompt | L11 |
| Missing or superficial verification (incomplete 8.2 %, incorrect 9.1 %) | MAST; an objective-level verification step gave +15.6 %; FEABench: 88 % executable, 2 of 15 valid | Falsifiers, asserted spec numbers, mutation-tested checkers | L1, L3 |
| Misalignment between agents (reasoning-action mismatch 13.2 %, not asking for clarification 6.8 %); two agents 30 % worse than one | MAST; CooperBench [CooperBench] | Freeze interfaces before spawning; a QUESTION escape path; no real-time negotiation between teams | L2, L11 |
| Error amplification and loss on coupled work | Kim et al. [KimScale]: 17.2x independent vs 4.4x central; -39 % to -70 % on sequential planning | Lead integrates one team at a time; parallel only on decomposable work | L2 |
| Interference in a shared workspace | CAID [CAID]: worktrees 63.3 vs soft isolation 55.5 (PaperBench) | One worktree per team; test-gated merge | L4 |
| Correlated or self-favouring verifiers; conformity in debate | Knight & Leveson; 60 % shared wrong answers (one dataset); self-preference; up to 85.5 % conformity | Commit verdicts independently; tool oracles first; a judge between advocates | L7 |
| Written rules not followed by fresh agents | Relic [Relic]: 25.4 % none, 34.6 % text, 41.2 % executable | Executable gates (hook, merge gate), not mandatory reading | L4 |
| Stale agent context and memory | STALE [STALE]: 55.2 % best; ours: workflow says ngspice 42, 45.2 installed | Watches on `CLAUDE.md`, workflow prompts and skills | L11 |
| Cannot tell afterwards who broke what | Who&When [WhoWhen]: agent named 53.5 %, step 14.2 % | `Workflow:` / `Agent:` / `ECR:` commit trailers at change time | L4 |

### L1. Verifiers return falsifiers; checks assert numbers · **now**

**Evidence.**
- **FEABench** [FEABench]: the best agent wrote executable simulation code 88 % of the time but reached a valid answer in 2 of 15 problems. Its one answer inside the strict tolerance was COMSOL's default 20 °C against a true 18.3 °C, so there were zero genuine strict passes.
- **Self-correction** [HuangSC]: models can't reliably fix their own reasoning without outside feedback. CRITIC [CRITIC] shows it works when the critique comes from a tool.
- **MAST** [MAST]: verification failures are a top category (incomplete 8.2 %, incorrect 9.1 %). Adding an objective-level verification step to ChatDev gave +15.6 %.
- **Locating the error:**
  - PCBSchemaGen v1 [PCBSchemaGen]: feedback that names the pin or net was indispensable on hard tasks.
  - PCBWorld [PCBWorld]: with KiCad's DRC after every step, an agent reached 0.65 completion with 1.31 violations per board. Plan-then-execute reached 0.19 with 16.28; writing board text blind, 0.02 with 34.58.

**In our repo:** 1 of the 14 scripts in `sim/checks/` asserts or exits on failure. The rest print numbers.

**Change.**
1. In every workflow prompt, a verifier may return REFUTED only with **a falsifier**: a runnable check that fails, or a primary-source quote with a page number. Otherwise it returns UNVERIFIED, never "looks fine".
2. Every `sim/checks` script asserts three things and exits non-zero on failure:
   - the spec limit;
   - a not-default, not-zero sanity check;
   - an analytic bound (the `niti_closed_form.py` beside `niti_arm_real.py` pattern).
3. Error messages name the pin, net or feature.

**Effort:** 2 h for the workflow rule, about 0.5 h per script.

### L2. Serialise coupled design; parallelise only decomposable work · **now**

**Evidence.**
- **Kim et al.** [KimScale], 260 configurations: multi-agent setups gained up to +80.8 % on decomposable tasks.
  - On sequential planning, *every* multi-agent variant lost 39–70 %, centralised ones included.
  - Errors were amplified 17.2× with independent agents, 4.4× with a central orchestrator.
  - Adding agents had negative returns once one agent already succeeded about 45 % of the time.
  - Their predictive model is weak (cross-validated R² 0.373).
- **CooperBench** [CooperBench]: two coding agents sharing a job scored 30 % lower than one agent doing both halves.
- **Klein et al. 2003** [Klein03]: strong interdependencies make convergence slow and costly (abstract). Applying this to agent teams is our inference.
- **Anthropic** [Anthropic-MA]: multi-agent is a poor fit where agents depend heavily on each other. Token spend explained 80 % of the performance variance, and multi-agent runs used about 15× the tokens of chat.

**Change.**
1. Parallel phases do only research, option generation and audits.
2. Any edit touching a relation in `items.yaml` is integrated by the lead, one team at a time.
3. The tight pod cluster (board outline, shell, cell, arm wire path, routing) goes to one team.
4. Write the lead's dispatch rule into `docs/system/README.md`, since Nii's model leaves control unspecified. Order: highest-risk SUSPECT relations first, then work that bridges two settled areas, then local refinement.
5. Before scaling a workflow, re-run one past task with one agent on the same token budget [Kapoor24], and keep the workflow only where it wins.

**Effort:** 1–2 h.

### L3. Audit the checker · **now**

**Evidence.**
- **A-Lab** [ALab] (Nature 2023) reported 41 novel compounds from an autonomous closed loop in 17 days. A 2024 re-analysis of all 43 products [ALabCritique] concluded that "no new materials have been discovered". It found four common shortfalls in the analysis: "automated Rietveld analysis of powder x-ray diffraction data is not yet reliable", and two-thirds of the claimed materials were likely known, compositionally disordered versions. **The loop ran; its checker was wrong.**
- **CADTests** [CADTests] hardens its test suites by *mutation analysis*: deliberately broken models must fail the suite.
- **FEABench**'s default-value pass (L1) is the same failure in miniature.

**Change.**
1. Every checker (sim check, interface check, `bom_check`, the L6 rule checker) gets a mutation test: break the design on purpose and require a fail. Examples: shift the mic port 0.2 mm, swap two pins, put 400 mA on the LDO.
2. Physical results judged by our own scripts (bring-up, self-test over USB) are not marked passed in the PLM until the owner has looked at the raw data.

**Effort:** about 3 h for the existing checks, then 15 min per new one.

### L4. One worktree per team; merge through an executable gate · **now** (before the next parallel design run)

**Evidence.**
- **CAID** [CAID] (CMU 2026, PaperBench / Commit0-Lite, Claude Sonnet 4.5):

  | Setup | PaperBench | Commit0-Lite |
  |---|---|---|
  | One agent | 57.2 | 53.1 |
  | "Soft" isolation (shared workspace, assigned files) | 55.5 | 56.1 |
  | Own git worktree per agent, test-gated merge | **63.3** | **59.1** |

  Isolation beat soft assignment on both benchmarks, at 2.8–4.3× the cost, with no variance reported. Eight engineers did worse than four.
- **Written vs executable rules:**
  - Relic [Relic]: a fresh agent team followed its protocol correctly 25.4 % of the time with no rules, 34.6 % with rules as text, 41.2 % with executable bindings.
  - Ahn & Kim [Contracts26]: code-owned enforcement blocked all contract violations (120/120). Prompt instructions alone let violations reach the user.
- **Who&When** [WhoWhen]: from logs afterwards, the best method named the responsible agent 53.5 % of the time and the step 14.2 %.
- **Our check-outs** are soft isolation, and they have never run: `docs/system/plm/` holds no `checkouts.json` and no `baseline.json` (checked 2026-10-01).

**Change.** This is `methodology.md` M4 and §5.3, now with evidence.
1. Each team runs in `git worktree add <scratch>/wt/<team> -b team/<team>`.
2. The lead merges one branch at a time through the gate: `plm.py status`, the relevant `sim/checks`, ERC/DRC.
3. A versioned pre-commit hook refuses agent commits that touch checked-out items without a clean status or an ECR id.
4. Agent commits carry `Workflow:`, `Agent:` and `ECR:` trailers (git commit footer lines), so provenance is recorded when the change is made.

The hook installs into this repo's own `.git/hooks`, so it needs the owner's approval.

**Effort:** 3–4 h.

### L5. One shared geometry source; real-board STEP clash check · **now**

**Evidence.**
- **Text2Robot** [Text2Robot] built its servo boxes and electronics channel into the geometry generator; its four physical builds walked with gaits trained in simulation.
- **Makatura et al.** [Makatura] needed humans to give the low-level mounting instructions. They also found that regenerating a design "overlooks elements specified in previous prompts".
- **KiCad StepUp** [StepUp] is the standard FOSS practice: put the real board and its parts inside the enclosure and check collisions.

**Live drift in our repo:**
- `hw/mech/frame.py`, the declared shared interface, still has a 20 × 11.5 mm board (`PCB = dict(x0=30.6, x1=50.6, …)`).
- `hw/mech/shell_r1.py` has the 34 × 13 mm rev-1 board.
- O20 says the board will be re-sized again.

**Catch:** the fact-checker's fenced test export with `kicad-cli pcb export step` lost 47 of 58 component bodies, the MCU and the mic included. The KiCad 3D library is not installed (`tools/setup.sh` defaults to `WITH_3D=0`).

**Change.**
1. Board outline, keep-outs and the positions of connector pads, the button and the mic port live in one Python module, imported by both `hw/pod` placement and `hw/mech`.
2. A script exports the board STEP (the standard 3D CAD exchange format) and imports it into build123d. It intersects the board with tub, lid, plunger, cell and foam and writes a clash table.
3. A PLM watch sits on the exported STEP's hash.
4. Add CADTests-style predicates (executable checks on the solid, each linked to a spec ID): walls, height bands, port bore, button travel.

**Precondition:** the owner runs `tools/setup.sh --with-3d` (needs sudo). The library is CC-BY-SA-4.0 with a design exception, so our files carry no obligation.

**Effort:** about a day.

### L6. A SKiDL rule checker built on the PCBSchemaGen v2 verifier · **now**

**Evidence.**
- **PCBSchemaGen v1** [PCBSchemaGen], 23 tasks, SKiDL output:
  - a blind expert agreed with its verifier at κ (Cohen's agreement statistic) 0.913;
  - its top failure was misreading one pin's function (a Kelvin source);
  - open models degraded above about 20 devices or 70 pins.
- **PCBSchemaGen v2** (June 2026, 227 tasks) ships an **MIT-licensed** deterministic verifier [PCBSchemaGenRepo]:
  - ERC;
  - pin roles (a 32-role schema);
  - per-IC templates;
  - subgraph matching against motifs, half-bridge included;
  - power rules: Kelvin source, decoupling, isolation, gate resistor.

  It names the pin or net in every error. Its datasheet knowledge covers its own benchmark ICs, not ours.
- **Polymorphic Blocks** [PolyBlocks]: typed ports carry voltage and current limits and assertions check them. Its authors say it is "not a design assurance tool".
- **EmbedAgent** [EmbedAgent]: hardware–firmware seams are weak even on toy tasks (50–56 % pass@1, the share solved on the first try).

**In our repo:**
- `hw/pod/gen.py` calls `skidl.ERC()` at line 286, then always writes the netlist.
- It defines no `erc_assert` checks. `erc_assert` is a bare expression hook with no electrical model.

**Change.**
1. Read the v2 verifier and adapt its rule layers. Write pin-role cards for our six ICs: MCU, charger, LDO, bridge pairs, mic, ESD.
2. Add a rails table (net, V min/max, I budget) as `erc_assert`s.
3. Make `gen.py` exit non-zero on any ERC error.
4. Generate the firmware pin map from the netlist.

**Effort:** about a day.

### L7. Decorrelate verifiers; never vote after debate · **now**

**Evidence.**
- **Knight & Leveson 1986** [KnightLeveson]: 27 independently written versions of one program, put through 1 million tests, failed together far more often than independence predicts.
- **Correlated errors** [KimCorr], 350+ LLMs: on one leaderboard dataset, two models agreed on the same wrong answer 60 % of the time when both erred.
- **Self-preference** [Panickssery]: LLM judges recognise and favour their own outputs.
- **Debate:**
  - Homogeneous debate reached up to 85.5 % conformity and overturned sound reasoning (7–8B models) [Bertalanic].
  - A position paper finds debate often fails to beat plain self-consistency (sampling independently, then taking a majority), and that mixing models helps [ZhangMAD].
  - Two sides arguing before a separate judge raised judge accuracy to 76 % (model judges) and 88 % (human judges), against 48 % and 60 % without debate [Khan24].
  - Independent sampling then voting *does* work [SelfConsistency, MoreAgents].

**In our repo:** the audit workflow's "INDEPENDENT N-VERSION CHECK" re-derivations are all one model family.

**Change.**
1. Verifiers commit their verdicts before seeing each other's.
2. They get the claim plus primary sources, not the author's reasoning.
3. Vary their framing and inputs.
4. Count same-model agreement as correlated: worth more than one check, less than N.
5. Prefer a tool oracle wherever one exists.
6. For owner decisions, one advocate argues each option and the owner judges.

**Effort:** 1–2 h.

### L8. Machine-readable margins on relations · soon

**Evidence.**
- **Brahma & Wynn** [BrahmaWynn], full text: margins absorb change, and a component whose margin is used up becomes a *change multiplier* that passes every further change on.
- **Eckert, Isaksson & Earl 2019** [Eckert19] separate a *buffer* (margin held for uncertainty) from *excess* (spare capacity).
- **Whitfield 2000** [Whitfield00]: generic coordination needs domain-specific mechanisms.

**Our case:** the TPS7A2030 (TI's 3.0 V, 300 mA low-dropout linear regulator) is already tracked as ECR-0005.
- At full-scale drive the bridge peaks at about 315–323 mA, against a 300 mA rating and a 360 mA minimum current limit.
- At the assumed −12 dBFS ceiling it peaks at about 85 mA, and C14 (22 µF) buffers the peaks.

It is a multiplier only in the worst case, and the tooling can't see either number.

**Change.** Add an optional `margin: {operating, worst_case, limit, unit, source}` field on relations. `plm.py status` lists any margin ≤ 0 as MULTIPLIER, with the source script that computes it.

**Effort:** 2–3 h.

### L9. Two-sided interface sign-off · soon

**Evidence.**
- **NASA SE Handbook §6.3** [NASA63]: "For interfaces that require approval from all sides, unanimous approval is required."
- **Sosa et al. 2004** [Sosa04]: known design interfaces that no team interaction covered (aircraft engines).
- **Doorstop** clears suspect links one parent at a time [Doorstop].

**In our repo:** `plm.py review` re-baselines on one `--by`, and `ALL`/`--all` re-baselines everything at once (`tools/plm.py` line 288).

**Change.** This is M6.
1. Add an `owner` field per item.
2. A relation stays SUSPECT until both items' owners have reviewed it, as two distinct signatures, each with evidence.
3. Forbid `ALL` for relations.
4. Report cross-team relations that both teams have never reviewed: the "unattended interfaces".

With one human and short-lived teams, the lead signs the unstaffed side, and the owner signs anything that touches an O-item (methodology §6.5).

**Effort:** 2–3 h.

### L10. DSM clusters set team scopes; rank change impact · soon

**Evidence.**
- **Steward 1981** [Steward] describes using the dependency matrix "to determine the consequences of a change in any variable … which engineers must be informed". That is `plm.py impact`, 45 years early.
- **MacCormack, Baldwin & Rusnak 2012** [MacCormack12]: products from loosely coupled organisations had up to 8× lower propagation cost, which is the density of the transitive closure of the dependency graph.
- **CPM** [CPM], "the first and most established" propagation method per Brahma & Wynn, ranks change by likelihood × impact.
- **PACT's broadcast** swamped its agents [Whitfield00].
- **Conway 1968** [Conway68], full text: "a design effort should be organized according to the need for communication".
- **Cataldo et al. 2006** [Cataldo06] make that mismatch computable.

**Change.** This is M5 and M7.
1. A read-only script exports `items.yaml` to a DSM and computes clusters plus propagation cost. Render it dark-mode.
2. The workflow assigns one team per cluster and re-forms teams each cycle; agent teams are cheap to re-form.
3. Add optional `likelihood` and `impact` (1–3) on relations, and sort `impact` and `ecr new` output by their product.
4. Later, replace the hand-set likelihoods with the observed outcomes of our own reviews. Brahma & Wynn warn that elicited models are subjective and frozen in time.

**Tools:** NetworkX (BSD-3-Clause) or RaGraph (GPL-3.0-or-later).

**Effort:** 4–6 h.

### L11. Agent-facing text: lean, under watches, MAST-linted · soon

**Evidence.**
- **AGENTS.md evaluation** [Gloaguen], current v3: "providing context files does not generally improve task success rates", while adding over 20 % inference cost. Repository overviews don't help.
- **STALE** [STALE]: the best model noticed invalidated memories 55.2 % of the time.
- **Repo2Skill-Evo** [Repo2Skill]: every one of 105 release transitions invalidated part of a skill set. Six frontier agents managed only 29.9–69.7 % macro-F1 when updating skills.
- **MAST** [MAST]: step repetition 15.7 %; not recognising completion 12.4 %; failing to ask for clarification 6.8 %. Clearer role specifications gave +9.4 %.
- **Live drift:** `.claude/workflows/adversarial-methodology-audit.js` line 58 tells every agent "ngspice 42". ngspice 45.2 is installed.
- **Classic lesson** [Shen08, KQML]: don't build an ontology layer. Keep anchors concrete and machine-checked: net, part and symbol names, `frame.py` constants.

**Change.**
1. Add an AGENT-CONTEXT item in `items.yaml` that owns `CLAUDE.md`, `.claude/workflows/*.js` and `.claude/skills/*/SKILL.md`, with `grep:` watches on tool versions and paths.
2. Every agent prompt states a termination condition and an escalation path (return QUESTION when unsure). Every return includes an "assumptions made" list, and each assumption becomes an O-item or an ECR.
3. **Owner decision needed:** `docs/system/README.md` rule 3 (owner rule, 2026-10-01) makes the full doc set mandatory agent context.
   - **Option A (recommended):** `00-whole.md` plus the docs that `plm.py impact` lists for the team's items. A/B test it on one task.
   - **Option B:** keep the full set.
   - **Option C:** full set for the lead, scoped for teams.

**Effort:** 2 h.

### L12. Owner gate tiered by reversibility; co-plan; one advocate per option · soon

**Evidence.**
- **Magentic-UI** [MagenticUI]: GAIA task completion went from 30.3 % autonomous to 51.9 % with a simulated user who was asked in 10 % of tasks. That is an upper bound: the simulated user held a human-written plan and supplied the final answer in 18 % of tasks. Several real users found the number of feedback requests excessive.
- **Agentic set-based design** [BrownSBD]: the human manager makes the final, risk-assessed choice from a curated set.
- **Redux** [Redux]: decisions should carry their premises, so a decision is re-opened when a premise changes.
- **Rationale** [Lee97]: rationale systems fail when "the cost bearer is not the same as the beneficiary". With agents the cost is near zero, so the risk flips to an unread flood.

**Change.**
1. **Always ask:** orders and payments, spec §1, D- and O-items, and ECRs touching her decisions.
2. **Never ask:** regenerated files and wording.
3. **The lead decides and logs:** part swaps within an approved option.
4. Before a multi-team run, show her one picture: teams, write scopes, frozen interfaces.
5. O-items get premise watches in `items.yaml`, so `plm.py status` prints "SUSPECT DECISION: O16" when a part or number it assumed changes.
6. ECR and O-item bodies use the MADR headings, capped at about 15 lines.

**Effort:** 2–3 h.

### L13. Agents pick structure, solvers pick numbers · soon

**Evidence.**
- **SPhyR** [SPhyR]: every model, Claude Opus 4 included, got 0 % exact match on full 10 × 10 topology-optimisation layouts (zero-shot, no tools).
- **BikeBench** [BikeBench], a physical design benchmark: hybrid generator-plus-optimiser methods beat LLMs on constraint satisfaction.
- **NASA ST5** [ST5]: "the engineer chooses … the basic form of the antenna", and evolution searched within that form. It cost about 3 person-months against 5 conventionally, and a new antenna was evolved "in a few weeks" when requirements changed.
- **Gallego** [Gallego26] and **Nie et al.** [Nie26] show the same split pays off in non-physical domains. Applying it to hardware is our extrapolation.
- **The CHI'24 design-space tool** [CHI24DSE] plots board-level alternatives as trade-offs.

**Change.**
1. Briefs mark which decisions are the agent's (topology, architecture) and which must come from a script (values).
2. Reviewers reject interface-crossing numbers that no script computed.
3. First Pareto plot (the set of options where improving one goal costs another): NiTi arm force, strain and mass, from `sim/checks/niti_*.py`. Run a SALib sensitivity scan first to see which parameters matter. Fence it at 3–4 G and plot it dark with `tools/plotstyle.py`.

**Effort:** half a day to a day, plus owner approval to install pymoo and SALib.

### L14. Set-based exchange for open trade-offs · later

**Evidence.**
- **Sobek, Ward & Liker 1999** [Sobek99], three principles confirmed from the abstract:
  - map the design space;
  - integrate by intersection;
  - establish feasibility before commitment.
- **Ward et al. 1995** [Ward95] (preview only) argue for delaying decisions. The widely quoted "27 vs 37 months" comparison was not on the page we could open, so it is **unverified**.
- **Shallcross et al. 2020** [Shallcross20], a 122-paper review: use has been limited by complexity, reliance on qualitative methods and a lack of quantitative tools.
- **RAPPID** [RAPPID] (agents plus set-based design, with Toyota's Allen Ward as co-author) is **unverified** (metadata only).

**Change.** For decisions like the exciter drive scheme or arm stiffness:
1. Teams publish feasible *ranges* on shared parameters (board outline, height band, +3V0 current, mass) in a small YAML.
2. The integrator intersects the ranges, and the owner narrows them.
3. Leaving a published range needs an ECR.
4. Keep a conservative fallback in every set.

Sets live only in CAD and simulation, never in fabrication, because every extra print or board is hand work (O19).

**Effort:** 2–4 h per decision.

### L15. Close the loop through physical test; calibrate the models · later

**Evidence.**
- **OpenHTF** [OpenHTF]: each measurement is declared with its limits, and any out-of-spec measurement fails the run.
- **The closed loops that worked** (Lipson–Pollack [LipsonPollack], ST5 [ST5], Matthews et al. 2023 [Matthews23]) all relied on a trusted evaluator and stayed inside its envelope.
- **Multi-fidelity optimisation** [MFBO] combines cheap models with expensive measurements. The reality-gap survey [RealityGap] lists the calibration techniques.
- **O18:** rev 1 must fail informatively.

**Change.** This is M8 and M10.
1. Write a YAML of {F-row or D-item, measurement, limits, method} for rev-1 bring-up: rails, sleep current, exciter |Z| sweep, mic noise floor, NiTi preload.
2. Results land as PLM test relations, so a failed measurement raises an ECR just as a code change does.
3. Each sim model keeps a dated sim-vs-measured delta beside it.

**Effort:** about 4 h, plus 15 min per build.

### Decision for the owner

| Option | What | Cost | Recommendation |
|---|---|---|---|
| **A** | L1–L7 now as one batch, then L8–L13 before the sourcing lock | L1–L7 about 4–5 agent-days, L8–L13 about 2–3 more, plus your approval for 3 installs (3D library, NetworkX, pymoo/SALib) and a git hook | **Recommended.** L1, L3, L4 and L7 are the guards against the failure modes the literature documents, and they cost hours. |
| B | Verification only: L1, L3, L7 | about 1 day | Leaves the live geometry drift (L5) and the soft isolation (L4) in place. |
| C | Note it, change nothing | 0 | The next parallel run repeats documented failure modes. |

---

## 4. FOSS tools

**Rule:** FOSS only, meaning an OSI-approved licence read from the repo's own licence file (spec owner constraint). Licences were checked by the lens researchers and re-checked by the fact-checker on 2026-10-01; I re-read PCBSchemaGen v2's myself.

### Worth trying

| Tool | Licence (file verified) | Use here | Install cost |
|---|---|---|---|
| **PCBSchemaGen v2 verifier** [PCBSchemaGenRepo] | MIT (`LICENSE`: "Copyright (c) 2026 Huanghaohe Zou, …") | Read and adapt its pin-role, template, topology and power-rule layers into a checker over `hw/pod/gen.py` (L6) | Its verifier needs only NetworkX |
| **SKiDL `erc_assert`** [SKiDL] | MIT | Rail and pin-limit assertions in `gen.py` (L6) | Installed (2.3.0) |
| **`kicad-cli pcb export step`** (KiCad 10.0.6) | GPL-3.0-or-later | Real-board STEP into build123d for clash checks (L5) | Needs the KiCad 3D library: `tools/setup.sh --with-3d` (sudo; library CC-BY-SA-4.0 with design exception) |
| **git worktree** | GPL-2.0 (`COPYING`) | One worktree per team (L4) | Installed (git 2.53.0) |
| **CADTests pattern** (CADTestBench) [CADTests] | MIT | Borrow the pattern of requirement-linked, mutation-tested predicates over solids; port to build123d (L3, L5) | None; the pattern only. Its dataset licence was not checked |
| **NetworkX** | BSD-3-Clause | DSM, clustering, propagation cost (L10); dependency of the PCBSchemaGen verifier | Not in the venv; owner approval |
| **pymoo** + **SALib** | Apache-2.0; MIT | Pareto fronts and sensitivity for owner options (L13) | Not in the venv; owner approval |
| **KiCadRoutingTools** [KRT] | MIT | One fenced second-opinion routing trial, run by the lead only with the owner present, **never inside a parallel workflow** (CLAUDE.md). In PCBWorld [PCBWorld] it matched FreeRouting's single-run score on small boards (0.74 vs 0.75 clean pass) but not on larger ones (0.20 vs 0.64) | Not installed |
| **MADR** template | MIT OR CC0-1.0 | Headings for ECR and O-item bodies (L12) | None; template only |
| **RaGraph** | GPL-3.0-or-later (dual-licensed; the GPL option is OSI) | Markov clustering, bus detection, compatibility analysis (L10), if NetworkX is not enough | Separate scratch venv: it would upgrade the project's lxml |

### Watch

- **PCBWorld** (BSD-3-Clause; its engine fork is GPL-3.0): a DRC-in-the-loop agent environment and an objective router evaluator. It is pinned to KiCad 9.0.8; we run 10.
- **LangGraph** (MIT): borrow its interrupt-and-checkpoint pattern for owner-approval pauses. Don't adopt the runtime.
- **atopile** (MIT): constraint-solving part picker; candidate for rev 2. **circuit-synth** (MIT): mine its Claude Code agent patterns.
- **Circuitron** (MIT) [Circuitron]: the closest open SKiDL multi-agent analogue. It depends on the OpenAI Agents SDK, Supabase and Neo4j, so take ideas only.
- **Polymorphic Blocks** (BSD-3-Clause): its typed-port electrical model.
- **OpenHTF** (Apache-2.0): measurement-with-limits pattern (L15).
- **kicad-python** (MIT): the official IPC API binding. KiCad deprecated the SWIG `pcbnew` bindings in 9.0 and plans to remove them in 11.0 [KiCadAPI]; 8 Python files here import `pcbnew`. Pin KiCad 10 for rev 1 and keep board scripting behind one adapter.
- Optimisation and uncertainty: **OpenMDAO** (Apache-2.0), **pyMOTO** (MIT), **emukit** (Apache-2.0), **OpenTURNS** (LGPL-3.0), **SMT** (BSD-3-Clause).
- **Foam-Agent** (MIT): ideas only.
- **KiCad MCP servers**, mixelpixx and lamaalrajih (MIT): licences checked, READMEs not read.
- **Doorstop** (LGPL-3.0): design reference for per-link suspect clearing (L9).
- **OpenROAD** (BSD-3-Clause): the IC world's staged open flow with a sign-off check after each stage, a template for our gen → place → route → DRC → clash → release chain.

### Skip (FOSS, but no fit)

- **Agent frameworks:** CrewAI (MIT; telemetry on by default), AutoGen (MIT code; in maintenance mode), Microsoft Agent Framework (MIT), AG2 (Apache-2.0), MetaGPT (MIT; stagnant), ChatDev (Apache-2.0), CAMEL (Apache-2.0), Letta (Apache-2.0), Agentless (MIT), Magentic-UI (MIT; web-browsing focus). Our scripted workflows already do this.
- **Other:**
  - AnalogCoder (MIT): op-amp benchmark.
  - SysML v2 Pilot (EPL-2.0): the SysTemp result rests on 5 scenarios, but there are fewer than 150 public SysML v2 examples.
  - AbaqusAgent (MIT code, but it needs proprietary Abaqus).
  - OrthoRoute (MIT): backplanes only.
  - tscircuit (MIT): TypeScript stack.
  - labgrid (LGPL-2.1+): Linux board farms.
  - KiBot (AGPL-3.0): duplicates our `kicad-cli` scripts.
  - log4brains (Apache-2.0).
  - BoTorch and Optuna (MIT): pymoo covers us.
  - beso (LGPL-3.0), ToPy (MIT), TopOpt.jl (MIT).
  - CadQuery (Apache-2.0) and OpenSCAD (GPL-2.0): build123d covers us.
  - python-solvespace (GPL-3.0): stale.
  - KiCad StepUp (AGPL-3.0) and FEMbyGEN (LGPL-2.1): FreeCAD GUI workbenches; the owner may use StepUp by hand.
  - kiutils (GPL-3.0) and kicad-skip (LGPL-2.1): stale since early 2024.

### Excluded: not FOSS, or licence unverified

| Tool | Why excluded |
|---|---|
| MAST code / `agentdash` | The repo has no LICENSE file. MIT appears only in the PyPI metadata, which fails the house rule. Use the paper's taxonomy as a checklist. |
| AnalogSAGE | No LICENSE file, and it calls Pinecone, a proprietary hosted service. |
| Relic | PolyForm Noncommercial 1.0.0, not OSI-approved. Idea only. |
| CAID code | No LICENSE file. The pattern needs only git worktree. |
| Cambridge Advanced Modeller (CPM tool) | No OSI licence found (page 404). Re-implement CPM in a few lines with NetworkX. |
| DTU TopOpt codes | Licence not stated. Read them for understanding only. |
| Autodesk Fusion generative design | Proprietary (page not opened). Framing only. |
| COMSOL, Abaqus, Wokwi | Proprietary solvers or simulators used by cited papers (FEABench, AbaqusAgent, EmbedAgent). |

*Correction applied:* the first-pass notes excluded PCBSchemaGen as "repo 404, licence unverified". That was the v1 link. v2's repo is MIT, and it moves to "try".

---

## 5. Risks specific to our setup, and the guards

| Risk | Evidence | Guard we have | Guard we need |
|---|---|---|---|
| **Agents misreporting sources.** Below, "this research" means the four-lens research behind this note. | It found **no fabricated works** among about 100 cited, but its checkers made dozens of corrections, among them: a stale paper version that flipped a licence verdict (PCBSchemaGen); quotes taken from paywalled previews (Ward 1995); a researcher's synthesis attributed to a paper (Shen 2008 "three causes"); accuracy compared with AUC (a different metric; CADTests); v1 and v3 of one paper mixed (AGENTS.md); a single-dataset number stated as general (60 % correlated errors). | Spec §0 rule 3 (primary sources, dated); the fact-check pass. | Every load-bearing number carries a verbatim quote with a locator (page, table, section) and the version read. "Preview only" and "abstract only" labels. Check for the latest version before citing. |
| **Doc drift** | `frame.py` 20 × 11.5 mm vs `shell_r1.py` 34 × 13 mm; the workflow says ngspice 42 (45.2 installed); no PLM baseline exists, so nothing can turn SUSPECT. | `plm.py` watches; "staleness is a bug" (README rule 5). | Baseline now (M2); one geometry source (L5); agent-context watches (L11); generate, don't copy. |
| **Errors compounding across stages** (explore → verify → integrate → synthesize → audit) | 17.2× amplification with independent agents, 4.4× with central control [KimScale]. MAST: misalignment between agents and verification failures dominate. Each stage re-summarises the last. | A lead-integrated pipeline; the fact-check stage. | Falsifiers (L1); an executable merge gate (L4); synthesis links the lens notes, which stay in the repo, so every claim traces back. |
| **False confidence from simulation without bench tests** | FEABench (runs ≠ right); A-Lab (unreliable checker); SPhyR (no physics by eye). Our models leave out NiTi hysteresis, resin creep, skin and bone coupling, bone-conduction loudness and SMPS audibility. | O18 instrumentation; analytic cross-checks (`niti_closed_form.py`); a firmware knob for every uncertain value. | Label each result "model-only until measured"; mutation-test the checkers (L3); a measurement plan with limits; a calibration log (L15). |
| **Monoculture verification** | Knight & Leveson; 60 % shared wrong answers on one dataset; self-preference. The audit's "independent N-version" checks are one model family. | Adversarial-verify step; separate checkers. | Decorrelate (L7); tool oracles first; the owner judges between advocates. |
| **Coupled-cluster thrash** | Klein 2003; Kim et al. −39 % to −70 % on sequential planning. The 34 × 13 mm pod is one tight cluster. | Check-outs (unused). | Serial integration; one team per DSM cluster (L2, L10). |
| **Owner overload, or rubber-stamping** | Users find low-risk approvals excessive [MagenticUI]; the rationale flood [Lee97]; `review ALL`. | The 2–3 options rule. | A tiered gate (L12); two-sided sign-off without `ALL` (L9); ranked impact (L10). |
| **Shared-machine resources** | Multi-agent runs use about 15× chat tokens; any agent can start a simulation; the 2026-09-30 OOM incident. | 5-agent cap; 3 G fences; no autorouter in parallel. | Keep them. Count the fences in the matched-budget benchmark (L2). |
| **Tool churn** | KiCad 11 removes SWIG `pcbnew`; the IPC API is GUI-only on KiCad 9/10; atopile pins Python 3.14 exactly. | Tools pinned by `tools/setup.sh`. | Pin KiCad 10 for rev 1; one `pcbnew` adapter; a future ECR for the KiCad 11 port. |
| **Weak evidence transfer** | All the quantitative multi-agent evidence comes from software and reasoning tasks. Many 2026 sources are preprints. Several key samples are tiny: Claim Plane n = 6, SysTemp n = 5, Toyota a single firm. | — | Treat every borrowed lesson as a hypothesis. Measure it on our own history (L2's matched-budget test; L10's calibrated likelihoods). |
| **The novelty claim itself** | Search budget exhausted; commercial systems unseen. | — | Say "not found in ~100 opened works". Re-check once the search budget allows. |

---

## 6. What the fact-check changed

An independent checker re-opened every cited work and licence on 2026-10-01 (it found no fabricated work). These are the corrections that mattered, all applied above.

- **PCBSchemaGen:** the first notes cited v1 and excluded it as "repo 404, licence unverified". The current v2 (June 2026) has an MIT-licensed repo with a deterministic SKiDL verifier, so it moved to "try" (L6). I re-read its `LICENSE` and the arXiv abstract pages for CAID, Relic, Kim et al. and Design Conductor myself on 2026-10-01 (spot check).
- **CADTests:** venue is an arXiv preprint, not NeurIPS. The "93.8 % agreement" compared an accuracy with an AUC (a different metric), and rests on two annotators; the "81 % best" was on abstract prompts (62.5 % on detailed ones). Only the mutation-testing pattern is used.
- **AGENTS.md study:** the notes mixed v1 and v3. The current v3 says context files give no general gain and add over 20 % cost, not that they lower success (L11).
- **CAID:** "matched single agent" means the same framework, not the same budget (CAID cost 2.8-4.3x). Soft isolation beat the single agent on one of two benchmarks, so "check-outs measurably fail" was dropped; the supported claim is that worktrees beat soft isolation on both (L4).
- **Relic, Magentic-UI:** the CooperBench figure is v1's; the 30.3 to 51.9 % gain came from a simulated user holding a human-written plan, so it is an upper bound (L12).
- **Verification rules:** "never vote" and "N same-model checks count as one" overstated the evidence. Independent sampling plus voting works; voting after debate does not; same-model checks are correlated, so discount them (L7). Self-preference is documented evidence, not an inference.
- **Classic papers:** the "faded without industrial uptake" story and the "three causes" are our synthesis, not claims Shen 2008 or Whitfield 2000 make (Shen mentions industrial applications). Ward 1995 and Sobek 1999 were paywalled previews, so their "27 vs 37 months" and sub-principle details are unverified. Post-and-volunteer allocation is Smith's 1980 Contract Net.
- **Brahma & Wynn:** "0 methods with ongoing industrial use" counts publications; 15 report preliminary industrial evaluation. Quoted as "no paper reports ongoing industrial use".
- **Repo facts:** the STEP clash check is not free (47 of 58 component bodies missing without the KiCad 3D library); `erc_assert` has no electrical model; 8 files import `pcbnew`, not 7; `frame.py` and `shell_r1.py` hold two different boards. The LDO margin issue is already ECR-0005.
- **Novelty claim:** Doorstop-style stamps and suspect links are not new; the narrower claim is watch granularity across ECAD, MCAD and docs, plus check-out flags between agent teams.
- **Licences:** no "try" tool fails FOSS-only. MAST's code is "licence unverified" (MIT only in PyPI metadata), not "not FOSS".

---

## Sources

All accessed **2026-10-01**. Full lens notes, with more works, are in [`prior-art/`](prior-art/); the corrections applied are summarised in section 6. "Read" says how much was opened.

**LLM agents for physical design**

| Key | Work | Year / venue | URL | Read |
|---|---|---|---|---|
| PCBWorld | Song et al., PCBWorld: engine-grounded PCB design automation | 2026, KDD workshop (non-archival) | https://arxiv.org/abs/2607.05915 | HF full text, 2026-10-01 |
| PCBSchemaGen | Zou et al., PCBSchemaGen (v1 "Constraint-Guided…"; v2 "Reward-Guided LLM Code Synthesis…") | 2026, arXiv | https://arxiv.org/abs/2602.00510 | v1 HTML full text; v2 abstract, 2026-10-01 |
| PCBSchemaGenRepo | PCBSchemaGen_v2 repository | 2026 | https://github.com/HZou9/PCBSchemaGen_v2 | LICENSE (MIT), 2026-10-01 |
| CADTests | Text-to-CAD evaluation with CADTests (CADTestBench) | 2026, arXiv preprint | https://arxiv.org/abs/2605.07807 | HTML + README, 2026-10-01 |
| FEABench | FEABench: evaluating LMs on multiphysics reasoning | 2025, NeurIPS'24 workshops | https://arxiv.org/abs/2504.06260 | HF full text, 2026-10-01 |
| MAST | Cemri et al., Why do multi-agent LLM systems fail? | 2025, arXiv v3 | https://arxiv.org/abs/2503.13657 | HTML full text, 2026-10-01 |
| Makatura | Makatura et al., How can LLMs help humans in design and manufacturing? | 2023, arXiv | https://arxiv.org/abs/2307.14377 | PDF §3, 9, 10, 2026-10-01 |
| Text2Robot | Text2Robot: evolutionary robot design from text | 2024, arXiv v3 | https://arxiv.org/abs/2406.19963 | HTML, 2026-10-01 |
| EmbedAgent | EmbedAgent: LLMs in embedded system development | 2025, ICSE 2026 | https://arxiv.org/abs/2506.11003 | HF text, 2026-10-01 |
| VerilogCoder | VerilogCoder (NVIDIA) | 2024, AAAI 2025 | https://arxiv.org/abs/2408.08927 | abstract, 2026-10-01 |
| MAGE | MAGE: multi-agent RTL generation | 2024, arXiv | https://arxiv.org/abs/2412.07822 | abstract, 2026-10-01 |
| AnalogCoder | AnalogCoder | 2024, AAAI 2025 | https://arxiv.org/abs/2405.14918 | abstract + README, 2026-10-01 |
| BrownSBD | Agentic risk-aware set-based engineering design | 2026, arXiv | https://arxiv.org/abs/2604.16687 | HF text, 2026-10-01 |
| ASICAgent | ASIC-Agent | 2025, IEEE ICLAD 2025 | https://arxiv.org/abs/2508.15940 | abstract + intro, 2026-10-01 |
| ChipChat | Chip-Chat: conversational hardware design | 2023, MLCAD workshop | https://arxiv.org/abs/2305.13243 | abstract, 2026-10-01 |
| DesignConductor | Verkor team, Design Conductor | 2026, arXiv | https://arxiv.org/abs/2603.08716 | abstract only, 2026-10-01 |
| Circuitron | Circuitron (SKiDL multi-agent) | 2025–26, repo | https://github.com/Shaurya-Sethi/circuitron | README + LICENSE (MIT), 2026-10-01 |

**Classic concurrent engineering, DSM, change, rationale**

| Key | Work | Year / venue | URL | Read |
|---|---|---|---|---|
| PACT | Cutkosky et al., PACT | 1993, IEEE Computer 26(1) | https://doi.org/10.1109/2.179153 | abstract, 2026-10-01 |
| SHADE | McGuire, Kuokka, Weber, Tenenbaum, Gruber, Olsen, SHADE | 1993, CERA 1(3) | https://doi.org/10.1177/1063293x9300100301 | abstract, 2026-10-01 |
| Redux | Petrie, Webster, Cutkosky, Pareto optimality to coordinate distributed agents | 1995, AI EDAM 9(4) | https://www.cambridge.org/core/product/identifier/S0890060400002821/type/journal_article | abstract, 2026-10-01 |
| Whitfield00 | Whitfield et al., Coordination approaches and systems, Part I | 2000, Res. Eng. Design 12 | https://strathprints.strath.ac.uk/6391/6/strathprints006391.pdf | full text, 2026-10-01 |
| Shen08 | Shen, Hao, Li, Computer supported collaborative design: retrospective and perspective | 2008, Computers in Industry 59(9) | https://nrc-publications.canada.ca/eng/view/accepted/?id=7bea1fe7-935c-4a42-9fe0-97d00295f6b8 | full text, 2026-10-01 |
| KQML | Finin et al., KQML as an agent communication language | 1994, CIKM | https://doi.org/10.1145/191246.191322 | abstract, 2026-10-01 |
| Nii86 | Nii, The blackboard model of problem solving | 1986, AI Magazine 7(2) | https://ojs.aaai.org/aimagazine/index.php/aimagazine/article/view/537 | full text (OCR), 2026-10-01 |
| CarverLesser | Carver & Lesser, The evolution of blackboard control architectures | 1992 TR; ESWA 7(1) 1994 | https://web.cs.umass.edu/publication/docs/1992/UM-CS-1992-071.pdf | abstract (OCR), 2026-10-01 |
| ContractNet | Smith, The Contract Net Protocol | 1980, IEEE Trans. Computers C-29(12) | https://doi.org/10.1109/TC.1980.1675516 | abstract, 2026-10-01 |
| HanZhang25 | Han & Zhang, LLM multi-agent systems on a blackboard architecture | 2025, arXiv | https://arxiv.org/abs/2507.01701 | abstract, 2026-10-01 |
| Salemi25 | Salemi et al., LLM multi-agent blackboard system for data discovery | 2025, arXiv | https://arxiv.org/abs/2510.01285 | abstract, 2026-10-01 |
| Klein03 | Klein, Sayama, Faratin, Bar-Yam, Dynamics of collaborative design | 2003, CERA 11(3) | https://doi.org/10.1177/106329303038029 | abstract, 2026-10-01 |
| Ward95 | Ward, Liker, Cristiano, Sobek, The second Toyota paradox | 1995, Sloan Mgmt Review | https://sloanreview.mit.edu/article/the-second-toyota-paradox-how-delaying-decisions-can-make-better-cars-faster/ | paywalled preview; specific figures unverified, 2026-10-01 |
| Sobek99 | Sobek, Ward, Liker, Toyota's principles of set-based CE | 1999, Sloan Mgmt Review 40(2) | https://sloanreview.mit.edu/article/toyotas-principles-of-setbased-concurrent-engineering/ | preview + abstract (3 principles only), 2026-10-01 |
| Shallcross20 | Shallcross et al., Set-based design: state of practice | 2020, Systems Engineering 23(5) | https://doi.org/10.1002/sys.21549 | abstract, 2026-10-01 |
| RAPPID | Parunak et al., The RAPPID project | 1999, JAAMAS 2(2) | https://doi.org/10.1023/A:1010039424126 | **unverified** (metadata only), 2026-10-01 |
| Steward | Steward, The design structure system | 1981, IEEE TEM 28(3) | https://doi.org/10.1109/TEM.1981.6448589 | abstract, 2026-10-01 |
| CPM | Clarkson, Simons, Eckert, Predicting change propagation | 2004, J. Mech. Design 126(5) | https://doi.org/10.1115/1.1765117 | abstract, 2026-10-01 |
| BrahmaWynn | Brahma & Wynn, Concepts of change propagation analysis | 2022 online; Res. Eng. Design 34(1) 2023 | https://research.chalmers.se/publication/532073/file/532073_Fulltext.pdf | full text, 2026-10-01 |
| Eckert19 | Eckert, Isaksson, Earl, Design margins: a hidden issue in industry | 2019, Design Science 5 | https://doi.org/10.1017/dsj.2019.7 | abstract, 2026-10-01 |
| MacCormack12 | MacCormack, Baldwin, Rusnak, Exploring the duality… (mirroring) | 2012, Research Policy 41(8) | http://nrs.harvard.edu/urn-3:HUL.InstRepos:34403525 | full text, 2026-10-01 |
| Sosa04 | Sosa, Eppinger, Rowles, Misalignment of product architecture and organization | 2004, Management Science 50(12) | https://doi.org/10.1287/mnsc.1040.0289 | abstract, 2026-10-01 |
| Conway68 | Conway, How do committees invent? | 1968, Datamation | https://www.melconway.com/Home/Committees_Paper.html | full text, 2026-10-01 |
| Cataldo06 | Cataldo et al., Identification of coordination requirements | 2006, CSCW | https://doi.org/10.1145/1180875.1180929 | abstract, 2026-10-01 |
| NASA63 | NASA SE Handbook §6.3 Interface Management | Rev 2 (2016), page updated 2023-07-26 | https://www.nasa.gov/reference/6-3-interface-management/ | full page, 2026-10-01 |
| Lee97 | Lee, Design rationale systems: understanding the issues | 1997, IEEE Expert 12(3) | http://www.cs.northwestern.edu/~paritosh/papers/sketch-to-models/LeeDesignRationaleSystems.pdf | full text, 2026-10-01 |
| Doorstop | Doorstop (requirements tool) | repo | https://github.com/doorstop-dev/doorstop | LICENSE (LGPL-3.0) + docs, 2026-10-01 |

**Generative design and hardware as code**

| Key | Work | Year / venue | URL | Read |
|---|---|---|---|---|
| PolyBlocks | Lin et al., Polymorphic Blocks | 2020, UIST | https://doi.org/10.1145/3379337.3415860 | abstract + README, 2026-10-01 |
| CHI24DSE | Lin et al., Design space exploration for board-level circuits | 2024, CHI | https://doi.org/10.1145/3613904.3642009 | abstract, 2026-10-01 |
| CircuitSynth | circuit-synth | repo | https://github.com/circuit-synth/circuit-synth | README + LICENSE (MIT), 2026-10-01 |
| SKiDL | SKiDL | repo | https://github.com/devbisme/skidl | LICENSE (MIT); local `erc_assert` docstring, 2026-10-01 |
| KRT | KiCadRoutingTools | repo | https://github.com/drandyhaas/KiCadRoutingTools | README + LICENSE (MIT), 2026-10-01 |
| StepUp | KiCad StepUp | repo | https://github.com/easyw/kicadStepUpMod | README (AGPL-3.0), 2026-10-01 |
| SPhyR | Siedler, SPhyR | 2025, arXiv v4 2026 | https://arxiv.org/abs/2505.16048 | HF full text (v3), 2026-10-01 |
| BikeBench | Regenwetter et al., BikeBench | 2025, arXiv | https://arxiv.org/abs/2508.00830 | abstract, 2026-10-01 |
| Gallego26 | Gallego, A hybrid nested harness… | 2026, LM4Sci @ COLM | https://arxiv.org/abs/2608.08156 | abstract, 2026-10-01 |
| Nie26 | Nie et al., Challenges in iterative generative optimization with LLMs | 2026, arXiv | https://arxiv.org/abs/2603.23994 | abstract, 2026-10-01 |
| MFBO | Do & Zhang, Multi-fidelity Bayesian optimization: a review | 2025, AIAA J. 63(6) | https://arxiv.org/abs/2311.13050 | abstract, 2026-10-01 |
| LipsonPollack | Lipson & Pollack, Automatic design and manufacture of robotic lifeforms | 2000, Nature 406 | https://doi.org/10.1038/35023115 | abstract (PubMed), 2026-10-01 |
| ST5 | Hornby et al., Automated antenna design with evolutionary algorithms | 2006, AIAA Space | https://ntrs.nasa.gov/citations/20060024675 | abstract, 2026-10-01 |
| ST5launch | Space Technology 5 launch and operations | 2006–07, NTRS | https://ntrs.nasa.gov/citations/20070018186 | abstract (launch 2006-03-22), 2026-10-01 |
| Matthews23 | Matthews et al., Efficient automatic design of robots | 2023, PNAS | https://doi.org/10.1073/pnas.2305180120 | abstract, 2026-10-01 |
| ALab | Szymanski et al., An autonomous laboratory for novel materials | 2023, Nature 624 | https://doi.org/10.1038/s41586-023-06734-w | abstract, 2026-10-01 |
| ALabCritique | Leeman et al., Challenges in high-throughput inorganic materials prediction and autonomous synthesis | 2024, PRX Energy 3 | https://doi.org/10.1103/PRXEnergy.3.011002 | abstract (Semantic Scholar), 2026-10-01 |
| RealityGap | Aljalbout et al., The reality gap in robotics | 2025, arXiv | https://arxiv.org/abs/2510.20808 | abstract, 2026-10-01 |
| OpenHTF | OpenHTF | repo | https://github.com/google/openhtf | README + LICENSE (Apache-2.0), 2026-10-01 |
| KiCadAPI | KiCad developer docs: SWIG deprecation, IPC API | 2024–26 | https://dev-docs.kicad.org/en/apis-and-binding/pcbnew/ | full page, 2026-10-01 |

**Multi-agent orchestration, verification, generated PM**

| Key | Work | Year / venue | URL | Read |
|---|---|---|---|---|
| KimScale | Kim et al., Towards a science of scaling agent systems | 2025, arXiv v3 2026 | https://arxiv.org/abs/2512.08296 | HTML v3, 2026-10-01 |
| CAID | Effective strategies for asynchronous SE agents (CAID) | 2026, arXiv | https://arxiv.org/abs/2603.21489 | HF full text §1–4, 2026-10-01 |
| CooperBench | CooperBench | 2026, arXiv | https://arxiv.org/abs/2601.13295 | abstract, 2026-10-01 |
| ClaimPlane | Nikolaev, Claim Plane | 2026, arXiv | https://arxiv.org/abs/2607.21909 | abstract, 2026-10-01 |
| Relic | Relic | 2026, arXiv v2 | https://arxiv.org/abs/2609.32965 | abstract, 2026-10-01 |
| Contracts26 | Ahn & Kim, From prompts to contracts | 2026, arXiv | https://arxiv.org/abs/2607.08028 | abstract, 2026-10-01 |
| WhoWhen | Which agent causes task failures and when? | 2025, ICML (PMLR 267) | https://arxiv.org/abs/2505.00212 | HF full text, 2026-10-01 |
| MetaGPT | MetaGPT | 2023, arXiv v7 | https://arxiv.org/abs/2308.00352 | HTML, 2026-10-01 |
| Croto | Multi-agent collaboration via cross-team orchestration | 2024, Findings of ACL 2025 | https://arxiv.org/abs/2406.08979 | HTML, 2026-10-01 |
| Anthropic-MA | Anthropic, How we built our multi-agent research system | 2025-06-13, blog | https://www.anthropic.com/engineering/multi-agent-research-system | full post, 2026-10-01 |
| HuangSC | Huang et al., LLMs cannot self-correct reasoning yet | 2023, ICLR 2024 | https://arxiv.org/abs/2310.01798 | abstract, 2026-10-01 |
| CRITIC | Gou et al., CRITIC | 2023, ICLR 2024 | https://arxiv.org/abs/2305.11738 | abstract, 2026-10-01 |
| Kamoi | Kamoi et al., When can LLMs correct their own mistakes? | 2024, TACL 12 | https://arxiv.org/abs/2406.01297 | abstract, 2026-10-01 |
| KnightLeveson | Knight & Leveson, Independence in multiversion programming | 1986, IEEE TSE | https://doi.org/10.1109/tse.1986.6312924 | abstract, 2026-10-01 |
| KimCorr | Kim, Garg, Peng, Garg, Correlated errors in LLMs | 2025, ICML | https://arxiv.org/abs/2506.07962 | abstract, 2026-10-01 |
| Panickssery | Panickssery, Bowman, Feng, LLM evaluators recognize and favor their own generations | 2024, arXiv | https://arxiv.org/abs/2404.13076 | abstract, 2026-10-01 |
| Khan24 | Khan et al., Debating with more persuasive LLMs | 2024, ICML (PMLR v235) | https://arxiv.org/abs/2402.06782 | abstract, 2026-10-01 |
| ZhangMAD | Zhang et al., Stop overvaluing multi-agent debate (position paper) | 2025, arXiv | https://arxiv.org/abs/2502.08788 | abstract, 2026-10-01 |
| Bertalanic | Bertalanič & Fortuna, The cost of consensus | 2026, arXiv | https://arxiv.org/abs/2605.00914 | abstract, 2026-10-01 |
| SelfConsistency | Wang et al., Self-consistency improves chain of thought reasoning | 2022, ICLR 2023 | https://arxiv.org/abs/2203.11171 | abstract, 2026-10-01 |
| MoreAgents | Li et al., More agents is all you need | 2024, TMLR | https://arxiv.org/abs/2402.05120 | abstract, 2026-10-01 |
| Kapoor24 | Kapoor et al., AI agents that matter | 2024, arXiv | https://arxiv.org/abs/2407.01502 | abstract, 2026-10-01 |
| MagenticUI | Magentic-UI | 2025, arXiv (Microsoft) | https://arxiv.org/abs/2507.22358 | HTML eval sections, 2026-10-01 |
| Gloaguen | Gloaguen et al., Evaluating AGENTS.md | 2026, arXiv v3 | https://arxiv.org/abs/2602.11988 | v1 abstract + v3 HTML, 2026-10-01 |
| STALE | STALE | 2026, arXiv | https://arxiv.org/abs/2605.06527 | abstract, 2026-10-01 |
| AgentREADMEs | Chatlatanagulchai et al., Agent READMEs | 2025, arXiv v2 2026 | https://arxiv.org/abs/2511.12884 | HF text, 2026-10-01 |
| Repo2Skill | Duan et al., Repo2Skill-Evo | 2026, arXiv | https://arxiv.org/abs/2608.21964 | abstract, 2026-10-01 |
| Barcaui23 | Barcaui & Monat, Who is better in project planning? | 2023, Project Leadership and Society 4 | https://doi.org/10.1016/j.plas.2023.100101 | abstract, 2026-10-01 |
| RiskGPT23 | Assessing the accuracy of ChatGPT for risk management in construction | 2023, Sustainability 15(22) | https://doi.org/10.3390/su152216071 | abstract, 2026-10-01 |
