# 2026-10-11 K4 shell dropped the owner-approved exterior

```yaml
id: INC-2026-10-11-K4-EXTERIOR
found: 2026-10-11 19:14 ET (owner: "It already HAS a casing design ... hand-approved ... serious failure")
audit_src: spec.md O-table (l.625-672) + v0.14 exterior (l.442-468); DIRECTION.md l.148; hw/mech/shell_k4.py, dims_k4.py; docs/system/plm/items.yaml:65-69
root_cause: "K4 shell was cloned from the r2/K1 tub+lid (cavity, seam, heel, rail) and only the STRUCTURE was carried; the exterior (spine top, fin, trace, Night City) lived in a separate function top_concept() in shell_r2.py and in styles.py, which no K4 file imports; PLM tracks the exterior only as files owned by REG-POD-BODY (shell_r2/blade/styles), with no exterior->shell relation, so changing to shell_k4 raised no suspect."
evidence:
  - "grep -i 'spine|top_concept|fin' hw/mech/shell_k4.py -> 0 hits; shell_r2.py:220-232 lid = lid0 + top_concept()"
  - "shell_k4.py:202-210 lid() = flat outer_body & box minus bores: no spine, fin, trace groove"
  - "items.yaml:69 REG-POD-BODY owns shell_r2.py, dims_r2.py, blade.py, styles.py; shell_k4/dims_k4 not owned; reg-pod-body.md:12 still says Spine carried (r2 only)"
  - "O34a 'K4 look on glasses: Approve' was a packet on the plain K4 look; it did not retire O17/O29 (no text says so)"
impact: "K4 renders/exploded views show a plain slab; every hand-approved look ruling (O17 Spine, O29 engraved trace, fin/heel exterior, Night City) is absent from the current design. Structure/electronics work unaffected. Owner trust cost."
prevention:
  - "PLM: add item EXT-NIGHTCITY (kind: region, owns shell_r2.top_concept, blade.py, styles.py, and the K4 exterior function) and relations EXT-NIGHTCITY <-> REG-POD-BODY and SPEC(O17,O29,v0.14 exterior) <-> EXT-NIGHTCITY; plm status must show suspect when shell_k4.py changes without the exterior being re-checked."
  - "Rule: a shell variant is not 'done' until a look-parity check (spine, trace, fin, heel, no-UV/glow, hex ring) is in its checks dict; ECR template gets a line 'owner-approved look carried? (O-ids)'."
  - "Decisions audit (this table) re-run at each shell fork; superseding a look ruling requires an explicit owner O-item."
```

## Audit table

| O-id | Ruling (short) | Applied in K4? | Evidence | Fix action |
|---|---|---|---|---|
| O17 | Top/fin = "Spine" (vertebra steps up to rear), carry the theme everywhere | **dropped** | shell_k4.py:202-210 lid has no spine; r2 had shell_r2.py:220-232 | Port `top_concept()` onto K4 lid (re-anchor to K4 Y_OUT/Z1); check T/height budget vs O27 |
| v0.14 exterior (Night City / Blade) | Cyberpunk, not a brick; plate+trace groove, tapered dorsal fin, heel; one print | **dropped** (heel kept structurally) | spec.md:455-468; shell_k4.py:96 heel+rail only | Adapt blade fin + trace onto K4 outer_body; keep heel (done) |
| O29 | Drop armour plate; lid 1.0 mm carries the engraved circuit trace | **dropped** (plate gone, trace missing) | shell_k4.py lid(): no groove; dims_k4.py no trace param | Add engraved trace on K4 lid (styles.slot / blade trace path) |
| (v0.14) | No UV/glow prints; black | **yes (nothing glows)**, black colour not encoded anywhere in K4 | no glow parts in shell_k4.py | Add print-colour note (black) to shell_k4 docstring + reg-pod-body |
| O23 | Black solder mask | n/a to shell; board spec | spec.md:650 | none |
| O11 | Arm cover = printed rectangular strut (coil-spring look), silicone contact | **partly** | pad.py:1-19 strut exists (r2 arm, unchanged); not re-verified vs K4 heel/pad | Run arm/strut render on K4 and show it in the exploded view |
| O8 | Solid blue LED in pad ring | **partly** | dims_k4.py:168 LED+/LED- wire pads exist; hex window is mic only (shell_k4.py:207) | Confirm pad ring in K4 exploded view |
| O27 | Thin > short > long | **yes** (T 10.7; K1 9.6) but superseded for height by O34b | dims_k4.py:27; spec.md:661 | Re-budget spine height inside thin priority; ask owner only if T grows |
| O34a | K4 look on glasses: Approve | **yes** but approved WITHOUT exterior | spec.md:661 | Re-ask look approval after spine/trace added |
| O34b/O33 | Taller 15.25 / shorter 3.8; end-to-end | yes | spec.md:660-661 | none |
| O10 | Test then final build, cut-openable | yes | shell_k4.py:10-11 | none |
| O12 | IPX4/5, magnetic dock | yes | shell_k4.py dock windows | none |
| O16/O31 | No custom connector; USB-C dropped | yes | spec.md:643,659 | none |
| O19/O20 | Personal, comfort, final-size rev 1 | yes | whole design | none |
| O24 | Mic port duct | yes | shell_k4.py:206 duct bore | none |
| O28/O30 | Runtime B; thinner study | yes | spec.md:652-653 | none |
| O26 | Adapter fits two frames, deferred | yes (rail kept) | shell_k4.py:96 | none |
| Others (O1-O7b, O9, O13-O15, O18, O21-O22, O25, O32) | power, arm geometry, process, budget | not exterior; no K4 conflict found | spec.md:625-657 | none |

Counts (exterior/look rulings): dropped 3 (O17, O29, v0.14 Night City/fin/trace), partly 3 (O11, O8, black colour), yes elsewhere.

Not audited line-by-line: decisions-log.yaml (only one hit on audit grep) and the spec §12 A-Z task list; DIRECTION.md has no earlier ultrasonic look rulings beyond line 148.

## Addendum (lead, 2026-10-11): decisions-log.yaml check
- decisions-log.yaml line 32 / spec O34(a) (2026-10-08): she tapped **"K4 look on glasses: Approve"** in review packet 3. No K4 file imports the Spine/trace code (see root cause above), so that render most likely showed a plain K4 shell. Not verified: the packet artifact's image has not been re-checked.
- If so, the packet asked her to approve a look that had already lost her approved exterior, and it never said so. Her approval covered K4's proportions (O34 b: taller 15.25 mm, 3.8 mm shorter), not dropping the Spine.
- Prevention addition: any look/approval packet must list which approved exterior rulings (O11, O17, O29, Night City) are shown, and flag any that are missing.
- Mask colour (decisions-log line 14: Black or Purple at order time) still stands; no K4 conflict.
