# NEXT 5 (ranked by value/effort; rebuilt each beat; 2026-10-08 16:3x ET)
GitHub Issues migration is pending: creating issues was denied by this session's permission check (external write), so the owner has to allow it. The draft issue list is in docs/brief/issues-draft.yaml; IDs below are local until then.

1. N-K4-TOOLS (running): merge the 3 helper patches with phase2 still the default, hook green; the K4 flip is then one line after the ruling. ~30 min.
2. N-K1T-RELEASE (guess, model both): release package for the phase-2 board (gerber/drill/BOM/CPL/gate via build_release.py), like .pcba-workflow/k4-release. ~1.5 h.
3. N-6L-STACKUP: re-check JLC's published 6-layer 0.8 mm stack-up (K4 gate B4), dated source. ~15 min.
4. N-K1T-DUCT (guess): mic duct R14 on the 0.6 lid fails nominally; acoustic re-run of the options, fenced. ~1 h.
5. N-K1T-BUTTON (guess): KMT022 breaks the 0.6 lid; fix A = metal dome on new F pads (board edit + re-route, serial heavy job) or C = proud skin. ~1.5 h. Next after #4 (one heavy job at a time).
Done today: N-K1T-PARITY (327bf77), N-PENTEST-CARD (a4df5b8), N-POST-GAP (9e03771: post+epoxy carries it; bench-test the fill).
Note: the parity doc reads K4 L 53.65 / X0 13.85 from out/k4s; ECR-0024 says 49.85 / 17.65. Check which output is current.

Ruling-needed (hers, not ranked): A-K4-VISION (pen test), A-TODAY-BODY-MEASURE, A-IDLE-TRADE, A-6L-QUOTE (optional), A-CAP-CURVES (optional). Orders/payments: owner-only, never guessed.
