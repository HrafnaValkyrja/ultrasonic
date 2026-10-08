# NEXT 5 (ranked by value/effort; rebuilt each beat; 2026-10-08 16:3x ET)
GitHub Issues migration is pending: creating issues was denied by this session's permission check (external write), so the owner has to allow it. The draft issue list is in docs/brief/issues-draft.yaml; IDs below are local until then.

1. N-K4-TOOLS: merge the 3 helper patches (K4-aware clamp/ledge + heights checks, 9 selftest rules, tools default via tools/current.py, per-board bom_check) with phase2 still the default, so the hook passes; the K4 flip is then one line after the ruling. ~30 min.
2. N-K1T-PARITY (guess): bring the K1-thin option (phase2 board + 130 mAh cell, T 8.5) to K4's level: shell checks, mass, vision pass, renders, release status. The pen test then only picks one. ~1 h.
3. N-PENTEST-CARD: printable pen-test card (true-scale ruler from the hinge, marks at 12.6 mm (K4 OK) and 29.5 mm (current estimate), steps in 3 lines). Makes A-K4-VISION a 2-min job. ~20 min.
4. N-POST-GAP: the K4 ledge VHB alone gives 104 kPa vs the 85 kPa limit under a 2 N press; it passes only with the floor post gap ≤0.03 mm. Add a tolerance check (print ±) or widen the ledge VHB; the fix must not need the post. ~40 min.
5. N-6L-STACKUP: re-check JLC's published 6-layer 0.8 mm stack-up (gate blocker B-stackup), dated source. ~15 min.

Ruling-needed (hers, not ranked): A-K4-VISION (pen test), A-TODAY-BODY-MEASURE, A-IDLE-TRADE, A-6L-QUOTE (optional), A-CAP-CURVES (optional). Orders/payments: owner-only, never guessed.
