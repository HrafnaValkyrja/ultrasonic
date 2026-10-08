# Brainstorm ledger (Iterative Improvement mode; process: ~/.claude-shared/board/howto/ITERATIVE-IMPROVEMENT.md)
Owner's plan 2026-10-08. One row per idea; the judge pass re-ranks each cycle and kills weak ones with a reason. Merit = evidence or a calculation + moves a spec metric meaningfully (or removes a hard build step or a risk) + a stated cost. Rows with merit go to the owner as a packet (recommendation first, "let's talk" option). Nothing is ordered; changes to the committed design go through her.

Tracks: D = deeper (main), R = rabbit trail (research swarm), X = step back (informed radical), B = blind designer (requirements brief only: BRIEF-blind.md).
Metrics (spec): thickness T, height H, length L, worn mass, vision clearance, runtime h, charge time, loudness margin (dB over ambient+12.5), mic noise margin dB, build difficulty (max step), build hours, part count, cost, risk.

| ID | Track | Idea | Metric moved (est.) | Evidence / calc | Cost + risk | Rank | Status | Judge note |
|---|---|---|---|---|---|---|---|---|
| I-001 | D | Alert tones at 2-3 kHz + look-ahead limiter at the R64 clamp (fw knobs alert_hz, lim_lookahead) | alert margin +4.5 dB (quiet +6.1->+10.6, office -8.9->-4.4, street -28.9->-24.4; p05) | loudness.md before/after, fbfb38b | free; limiter raises max output past the -12 dBFS D17 ceiling: needs owner re-sign of D17 + golden re-bless | 1 | built, limiter OFF pending owner (D17) | - |
| I-002 | D | Pad stiffness / exciter resonance at 2-3 kHz | loudness +4-10 dB | loudness.md levers; needs E1/E2 | bench time, pad parts | - | bench day | - |

## Judge log (newest first)
(none yet)
