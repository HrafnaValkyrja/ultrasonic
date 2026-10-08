# Safety check: cell, charger, dock (A-SAFETY-REVIEW)

![safety](../diagrams/safety-explainer.png)

Five yes/no calls for the owner, all recommended yes. The picture is the whole brief.

1. Cap charging at about 65 mA (cell's "normal"; max is 130 mA). The docs still say 170 mA, which was sized for the old 175 mAh cell.
2. First charge on the bench, fire-safe spot, cell and chip temperature logged.
3. Accept measuring charger-chip heat on that first charge.
4. Ask Renata what the cell's guard board cuts off at.
5. Allow quiet self-test sound (-12 dBFS) while docked, self-test mode only (ECR-0009 option a).

<!-- NOTES (hidden; verified 2026-10-08)
Datasheet: BQ25180 SLUSE99C Rev C Jan 2023, SHA-256 prefix c2008f613723fec3 (copy re-read this session; text extracted with pdftotext).
- Card 1: ICHG reset 0x05 = 10 mA, code>35 mA => 40+(code-31)*10 mA (sec 8.5.1.5, p.32): 170 mA = code 44, 130 = code 40, 60 = code 33. Cell: docs/research/drastic/V2-cells.yaml ICP401230UPR: 130 mAh, normal 65 mA, max 130 mA (1C), CV 4.2 V, PCM present but no thresholds listed, charge 0-45 C. ECR-0013 F1 and sub-power still say 170 mA = DOC GAP (175 mAh cell era); K4 gen.py comment line 275 same. Safety timer: sec 7.5 tMAXCHG 180-720 min; default 6 h (sec 8.5.1.9 p.36, audit-datasheet-claims g). VBATREG default 4.20 V (sec 8.5.1.4). Safety-timer behaviour sec 8.3.7.6 p.19.
- Card 2: TS/JEITA sec 8.3.13 p.23, thresholds 0/10/45/60 C sec 7.5 + 8.5.1.12 (sub-power U3_TS); default hot trip 60 C vs cell 45 C = sub-power PWR-I2, ECR-0013. Watchdog (160 s) reverts registers to defaults sec 8.3.7.6 / audit claim 3.
- Card 3: 0.3 W / +31 C at 107.1 C/W JEDEC: sec 7.3 p.5, sec 8.3.7.7 p.20 (PDISS = PSYS+PBAT; TREG 100 C typ THERM_REG=00; TSHUT 150 C rising / 135 C falling, sec 7.5). 0.3 W figure is ECR-0013/ECR-0009 note for 170 mA; "less at 65 mA" is my inference (PBAT=(4.5-VBAT)*I scales with I), not computed in repo.
- Card 4: VIN_OVP 5.5/5.7/5.9 V sec 7.5 p.6; input OVP action sec 8.3.7.1; SYS short retry sec 8.3.7.4; battery overcurrent hiccup then off until VIN returns sec 8.3.7.5; BUVLO sec 8.3.7.2. Renata PCM thresholds not listed: V2-cells.yaml notes lines 14, 79.
- Card 5: ECR-0009 items 1 and open conflict (a)/(b); decision field still blank (status proposed). O32 (docs/spec.md): owner "no" to docking while worn. Exemption cap -12 dBFS per sub-output issue 12 / sub-power PWR-I5.
- Board naming: U3 charger placement M vs P differs between V9 lines 22 and 102; backlog says M; picture says "on the pod" to avoid it.
- Not checked: ECR-0013 S3 cap rating, C21 10 V vs 25 V (PWR-I14, open).
-->
