# Bone conduction: placement, stereo, contact force, ultrasound perception

**Date:** 2026-09-30 · **Informs:** D1 (site), D2/T3 (stereo), D6/§6 (output noise), E2, R1, R5, R6
**Method:** literature search (PubMed, ARL technical reports on govinfo.gov, HFES proceedings). `[NV]` = seen only in a secondary summary or abstract, not the primary text.

---

## 1. How much of one side's vibration reaches the other ear (transcranial attenuation, TA)

TA is how much quieter the far cochlea hears a bone-conducted signal than the near one. Low TA means each ear hears a lot of the other side's output. That shrinks the left/right loudness difference we rely on for direction.

| Where the vibrator sits | TA at 1–2 kHz | TA at 3–5 kHz | Source |
|---|---|---|---|
| Mastoid (behind the ear) | ~0 dB | ~10 dB (median), spread across people ~40 dB | Stenfelt 2012 (n=28, single-sided deaf) |
| Mastoid, normal hearing | ~0 dB at 1 kHz | 7–17 dB at 8 kHz | Reinfeldt, Stenfelt & Håkansson 2013 |
| Condyle (jaw joint) / mastoid / temple, at 3 kHz | — | ~12 / ~11 / ~7.5 dB (SD 3–6) | Wang et al. 2022 (n=6) |
| **Just in front of the tragus** (commercial headset, ~2 N) | **25–30 dB** | **~37 dB** | Surendran, Prodanovic & Stenfelt 2023 (n=21) |

**The key mechanism:** in front of the tragus, most of what you hear doesn't travel through bone. The vibration shakes the ear-canal cartilage, which radiates sound *into the ear canal*. That path is 20–30 dB stronger than the bone path, and it only reaches the near ear, so isolation is high (Surendran 2023; "cartilage conduction", Hosoi `[NV]`). Isolation drops fast with distance from the canal. Cadaver data show the near cochlea's response is 10–20 dB higher with the vibrator within ~2.5 cm of the canal, while the far side barely changes (Eeg-Olofsson 2008, 2011).

**For us:** D1's site (zygomatic-arch root, 1–1.5 cm in front of the tragus) probably sits on the bone-path side of that boundary. Expect **~10–15 dB** of isolation there, not the 25–40 dB of a headset that touches the tragus area.

## 2. Can people localize sound delivered by stereo bone conduction?

Yes, roughly as well as with headphones, when the stereo is phase-coherent (both channels from one sound card):
- **Condyle placement:** localization "nearly identical" to headphones (MacDonald, Henry & Letowski 2006; error figures `[NV]`).
- **Mean absolute error:** 20.2° headphones, 22.4° mastoid, 23.0° condyle, 25.7° temple. Only the temple was significantly worse. Front/back confusion was 29–35% for every method (Wang 2022, n=9).
- **Mastoid, n=20:** 22.7° vs 19.3° for headphones at 2 kHz (Ren et al. 2025).
- **Lateralization vs level difference:** about the same as headphones, but a 20 dB difference moved the image only ~75% of the way to the side (Stanley & Walker 2006, n=3).

**Warning that applies to our design:** Ren 2025 models the cochlea as seeing the applied level difference cleanly only when TA ≥ 20 dB. At TA 5–10 dB, the near and crossed signals interfere, level and phase interact, and lateralization can even *reverse*. Rowan & Gray 2008 saw the same at 3–6 kHz.

**Why this matters here:** our two units are unlinked (D2), so the relative phase of their outputs is arbitrary and drifts. Ren's suggested fixes (phase-lock the units, or crosstalk cancellation, shown in Mcleod & Culling 2019) both need a link between sides.

My simple two-path model (near signal plus crossed signal at −10 to −15 dB, arbitrary phase) says:
- the **sign** of the left/right difference is preserved, which is what T3 needs;
- its **size** varies with phase.

So T3 (left/right better than chance) is still likely. A stable, precise image is not guaranteed. `[Med]`

## 3. Where on the head is bone conduction most sensitive?

McBride, Letowski & Tran 2005 (ARL-TR-3556, n=12, ~4–5 N contact force):

| Comparison | 1 kHz | 2 kHz | 4 kHz | 8 kHz |
|---|---|---|---|---|
| Condyle vs mastoid | 10 dB better | 5 dB better | 6 dB better | 6 dB worse |
| Condyle vs temple | 14 dB better | 3 dB better | 10 dB better | — |

- The condyle had the lowest mean threshold for every signal tested (McBride 2008, Ergonomics, n=14).
- In front of the tragus, force thresholds are 10–40 dB (typically ~20 dB) better than at the mastoid, for the ear-canal-radiation reason in §1 (Surendran 2023).

**For us:** D1's site beats the temple and mastoid by ~5–10 dB at 1–4 kHz, which confirms D1 over the temple. **Moving closer to the tragus could add ~10 dB more loudness *and* much better isolation**, if the Ear Open pod leaves room. That's the key question for E2.

## 4. Contact force

- **At 2–5.4 N:** thresholds change ≤ ±2 dB (Toll, Emanuel & Letowski 2011, n=40). A bone-anchored hearing-aid headband's output rose ≤3 dB from 2 to 5 N (Hodgetts 2006).
- **Below 2 N:** no modern threshold study found `[NV]`.
- **Békésy 1939** (via Henry & Letowski 2007, ARL-TR-4138):
  - with a constant-*amplitude* driver, going from ~1 N to ~5 N raised transmission ~23 dB at 1 kHz, ~18 dB at 3 kHz and ~5 dB at 5 kHz;
  - with a constant-*force* driver, the skin loss at 1 N was only ~2 dB.
  - Our transducer is an inertial (force-type) exciter, so the second case applies.
- **Contact limit:** the pad starts to lose contact when vibration force exceeds static force. At 0.3 N that caps clean output near ~106 dB re 1 µN, still ~75 dB above the bone-conduction threshold at 2–3 kHz `[NV, derived]`.

**For us:** aim for **≥1 N static force through a compliant, well-seated pad**. Expect a few dB of loss at ~1 N, and more, less repeatable, at 0.3–0.5 N. Measure on a real head (E2).

## 5. Can you hear ultrasound through bone? (sets how strict the PWM-noise spec must be)

- **Bone-conduction thresholds above 13 kHz:**
  - flat to ~13 kHz, then **55–60 dB higher at 20–30 kHz** and ~70 dB higher at 35 kHz (Ito & Nakagawa, in Nakagawa 2020);
  - above 10 kHz, thresholds rise ~50 dB/octave to 20 kHz, then ~18 dB/octave to 100 kHz (Corso 1963 `[NV]`);
  - bone-conducted ultrasound is always heard at a fixed pitch of ~10–14 kHz and has only ~18 dB of usable range (Nakagawa 2020; Nishimura 2003, 2011).
- **At the zygomatic process, 8–16 kHz:** bone-conduction thresholds track air conduction (air–bone gap −7.2 ± 6.7 dB; Popelka, Telukuntla & Puria 2010). So for someone with good high-frequency hearing, **8–16 kHz energy from the transducer *is* potentially audible.**

**For us:** PWM residue and shaped noise in 20–40 kHz only need to stay a long way below in-band levels. The 55–60 dB threshold jump is a large safety margin. The band that matters for T6 is **up to ~16–20 kHz**.

---

## Citations
- Stenfelt S. 2012. Otol Neurotol 33:105. PMID 22193619.
- Reinfeldt S, Stenfelt S, Håkansson B. 2013. Hear Res 299:19. PMID 23422311.
- Wang J, Lu X, Sang J, Cai J, Zheng C. 2022. Trends Hear 26. PMID 35491731.
- Surendran S, Prodanovic S, Stenfelt S. 2023. Trends Hear 27. PMID 37083055.
- Eeg-Olofsson M et al. 2008. Int J Audiol 47:761. PMID 19085400; Eeg-Olofsson, Stenfelt, Granström 2011. Otol Neurotol 32:192. PMID 21131884.
- MacDonald JA, Henry PP, Letowski TR. 2006. Int J Audiol 45:595. PMID 17062501.
- Stanley R, Walker BN. 2006. Proc HFES 50:1571. http://sonify.psych.gatech.edu/publications/pdfs/2006HFES-StanleyWalker.pdf
- McBride M et al. 2015. Hum Factors 57:1443. PMID 26224085.
- Ren LJ, Yu Y et al. 2025. Adv Sci. PMID 40492360.
- Rowan D, Gray M. 2008. Int J Audiol 47:404. PMID 18574778.
- Mcleod RJ, Culling JF. 2019. JASA 146:3295. PMID 31795671.
- McBride M, Letowski T, Tran P. 2008. Ergonomics 51:702. PMID 18432447; ARL-TR-3556 (2005), govinfo.gov.
- Dobrev I et al. 2016. Int J Audiol 55:439. PMID 27139310.
- Toll LE, Emanuel DC, Letowski T. 2011. Int J Audiol 50:632. PMID 21506894.
- Hodgetts WE, Scollie SD, Swain R. 2006. Int J Audiol 45:301. PMID 16717021.
- Henry P, Letowski T. 2007. ARL-TR-4138, govinfo.gov.
- Khanna SM, Tonndorf J, Queller JE. 1976. JASA 60:139. PMID 956521.
- Corso JF. 1963. JASA 35:1738.
- Nakagawa S. 2020. Acoust Sci Tech 41:851.
- Nishimura T et al. 2003. Hear Res 175:171. PMID 12527135; 2011. Hear Res 277:176. PMID 21238563.
- Lenhardt ML et al. 1991. Science 253:82. PMID 2063208.
- Popelka GR, Telukuntla G, Puria S. 2010. Hear Res 263:85. PMID 19900526.
