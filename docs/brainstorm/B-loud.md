# B-loud: blind design, loud on a 70 dBA street (2026-10-08)
Read only BRIEF-blind.md. Source tags: [B]=brief/spec cite; [W]=web, checked 2026-10-08; [M]=my recall of a public standard/datasheet, NOT re-verified (web search returned no table); [A]=my assumption. Loudness has +-8 dB error until a bench measurement (section 6).

## 1. Choice
Output = cartilage/bone conduction at the tragus, via a pad on an arm from the pod (D1 [B]). Tragus drive also radiates into the canal: "the cartilage acts like a loudspeaker diaphragm", canal SPL rises when the transducer touches the tragus [W: encyclopedia.pub/entry/10630]. So it is hybrid in effect, no separate air path (air from 40 mm away loses ~25 dB [A], rejected).
Options: A) moving-coil/moving-magnet exciter, 3 V bridge (recommended); B) piezo bimorph (cartilage-conduction type): same force at 1/10 the current, but needs 15-60 V = a boost converter: stretches D11; keep as fallback; C) air receiver: rejected.
Why A: runs from the existing 3.0 V linear rail + H-bridge, no new switcher, resonance tuned to ~2.5 kHz inside the 1.5-4 kHz band [B].

## 2. Target, with calculation
Ambient 70 dBA. Brief wants alert 10-15 dB over it: take 12 dB, literal broadband => 82 dB SPL-equivalent at the ear (worst case, flat spectrum).
Street noise is low-frequency; at 2.5 kHz the 1/3-octave level is ~52 dB [A, typical traffic spectrum]; a tone is masked within a ~350 Hz critical band [M]. So 82 dB at 2.5 kHz is ~30 dB over the masked threshold: a deliberate margin.
Force needed: mastoid threshold at 2-3 kHz ~30.5 dB re 1 uN [M, ISO 389-3:2016 RETVFL]; air threshold at 2.5 kHz ~0 dB SPL [M, ISO 226]. Sensation level 82 dB => 30.5+82-10 (tragus is ~10 dB better than mastoid, D1 [B]) = **102.5 dB re 1 uN = 0.13 N rms**.
Exciter delivers: bridge 3.0 V square, fundamental 4/pi*3.0/sqrt2 = 2.7 V rms; 6 ohm coil => I = 0.45 A max, but the coil is inductive/resonant, take 0.34 A rms (derated 25%); Bl = 0.6 N/A [A, 10 mm class exciter] => F = 0.20 N rms = 106 dB re 1 uN.
=> equivalent level at 2.5 kHz = 106-30.5+10 = **~85.5 dB SPL-eq** (3.5 dB headroom over 82 = 15.5 dB over 70 dBA). Alert ceiling 85 dB-eq at 3.0 V is the hardware limit; no step-up needed.
Reaction check: 0.2 N on a 1 g moving mass = 200 m/s2, 0.8 um at 2.5 kHz (a/w^2); the 8 g pod is clamped to a ~30 g frame, so the pod barely moves [A]. Contact force: 1 N static (E2 [B]) keeps the pad coupled.

## 3. Drive electronics
Existing chain kept (mic -> decimate -> DSP -> 200 kHz noise-shaped PWM -> H-bridge [B]). Changes: bridge rail 3.0 V linear (not on cell) [B]; add 2x 47 uF polymer + 100 nF at the bridge; coil is the filter (L ~0.1 mH [A] resonance rolls off 200 kHz). Exciter impedance self-test retained [B]. Burst storage: not needed: peak 0.8 W / 3.0 V / 0.85 eff = 0.31 A from a 175 mAh cell (1.8C [A]; sag at 0.3 ohm = 0.09 V, inside LDO headroom 3.7-3.0 V; at 3.3 V empty cell the LDO would drop out => floor the cell cut-off at 3.4 V). A 0.1 F supercap would add 3 mm and ~1 g to fix a problem that does not exist. Loudness is limited by the transducer, not energy.

## 4. Cell, mass, size, runtime
Cell: 175 mAh protected pouch (O16 [B]), ~4x12x30 mm, ~3.4 g [A: 190 Wh/kg => 0.65 Wh]. Charge <=0.5C = 87 mA, NTC/JEITA gating, no output when docked [B].
Mass per side [A]: cell 3.4, exciter+pad arm 1.3, PCB+parts 1.2, shell 1.8, clasp/adapter 0.6, wires 0.2 = **8.5 g** (inside the 7.3-8.8 g band [B]). Nose/ear split from the spec balance table (~3.1-3.7 / 4.2-5.1 g [B]) holds with the cell back along the arm.
Size: pod **T 6.5 x H 15 x L 48 mm**, start 30 mm from hinge (>=29.5 vision line [B]); trades length (O27 order) for thinness: the cell lies flat on its 4 mm axis.
Current [A]: mic 0.9 + MCU/DSP 3.5 + bridge/LDO quiescent 1.1 = 5.5 mA floor. Normal day (bats sparse, mean output 55 dB-eq, alerts 1%): +1 mA => 6.5 mA => 175*0.9/6.5 = **24 h**. Worst day (continuous 65 dB-eq, alerts 1% of time at 0.31 A): 5.5+3+3 = 11.5 mA => **13.7 h** (>=8 h [B]). Sustained 75 dB-eq all day: ~33 mA => 4.8 h: that FAILS 8 h, and is not a use case. Aged cell at 80% capacity: 11 h worst.

## 5. Safety ceiling
Continuous/playback: firmware limiter at **<=80 dB SPL-eq** (NIOSH REL 85 dBA/8 h, 3 dB exchange [M, NIOSH 98-126]; 5 dB under it for the unmeasured +-8 dB error). Alerts: **<=88 dB-eq, <=0.5 s, <=60/h** => dose 0.5*60 s/h at 88 dB = equivalent 9 min/8h-limit allowance 85 dB x2.0 => <2% of daily dose [calc, 3 dB rule]. Hardware: rail 3.0 V + 6 ohm coil caps current at 0.5 A => a fault cannot exceed ~89 dB-eq. D17 fixed soft-clip stays, identical both sides. Dock: bridge disabled [B]. Skin: 0.8 um, 0.7 W peak at 1% duty => no heating. Pressure 1 N on 80 mm2 pad ~12 kPa, below T5 pain [A].

## 6. What loses, what must be proven
- Against the brief: +0 mm thickness vs cell (cell-limited), runtime 13.7 h worst vs 8 h req.
- Part count: +3 caps; no new IC. Hard no's stretched: none (piezo option B would stretch D11).
- Proof needed (before trusting 85.5 dB-eq): artificial mastoid / force gauge: >=0.15 N rms at 2.5 kHz at 3.0 V bridge; probe mic in her canal during tragus contact (target >=78 dB SPL at 2.5 kHz at 80% of full code); masking test with 70 dBA street recording over a speaker. If measured force <0.1 N (-6 dB): switch to option B or accept 79 dB-eq (9 dB over street) and drop the "12 dB" claim.
