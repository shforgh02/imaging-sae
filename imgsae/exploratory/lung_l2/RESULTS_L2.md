# Lung L2: results on the test split (S6, steps N4 to N6)

- **Written:** 2026-11-18, early morning (UTC), by the executing session (Opus 5.5), after the lead's OK of the freeze `c3578c3` (N3, 17 Nov) and the lead's go for N4 ("start N4 … do your job, fix error … make best decision and continue").
- **Frozen analysis output:** `results/s6/s6_test.json` (SHA-256 `e51c2308d5dd1f8d8e868c40573bdb28f15d47e706cb87b40071973d9290f793`), **run once and committed before it was read** (commit `1c93259`). Everything in sections 1 and 2 comes from that file.
- **Rules:** `HYPOTHESES_L2.md` (frozen family of six, Holm, one-sided, α = 0.05), protocol sections 10 and 11, the four run rules of N3 (`docs/EXECUTION_LOG.md`, entry "step N3 done").
- **Dev vs test:** dev is Sybil's own development split (it was used to build and tune Sybil, so it flatters Sybil; caution C6). Test is Sybil's held-out test split, opened once.
- **Population:** 6,715 test exams (one series per exam, the series of Sybil's split file), 2,347 participants; 86 cancers within 1 year (all screens), 131 cancers within 6 years (baseline screens). Z-fix population T5: 759 exams, 342 participants, 9 one-year cancers. Kernel pairs T4: 500 pairs, 500 participants.
- **Corrections (20 Nov, after the outside review `docs/REVIEW_PLAN_CHOICE.md` and `docs/INDEPENDENT_AUDIT_R2.md`; no number in any result file changed):**
  - **Correction:** H2 on test is **−0.366** (−0.36646), not −0.367 (sections 1 and 3d; a rounding typo).
  - **Correction:** section 3b point 1 said that removing the radiologist's call shows that work-up bias does not explain the result. That was wrong. In NLST, a nodule of 4 mm or more made the screen positive, so the findings themselves carry most of the call (83 of the 86 one-year cancers were found after a positive screen). Section 3b is corrected; section 3e tests it.
  - **Correction (label):** the "radiologists' sensitivity" row of section 2.1 uses a cut matched on test (94.2%), so it is descriptive. The dev-fixed cut is in section 3e.

## 0. In simple words
1. **Five of the six frozen predictions came true on new data. One failed (H3).**
2. **The slice-spacing problem is real on the test scans.** When we give Sybil the true slice spacing, its score falls (H2), and two scans in three move by a clear amount (H1). The kernel hardly matters for the alarm (H4).
3. **We found where the problem sits inside Sybil, and it held on new scans (H6).** One shared direction ("axis 0") in Sybil's `pooled` layer carries the whole average drop. Switch that one direction off, and the z-fix drop goes from −0.37 to +0.04. This is the feature-level result of the project. **What axis 0 reads (X11, 23 Nov, exploratory, section 3j):** whether Sybil's 200-slice box holds a thick slab of Sybil's own grey padding (about −600 HU). An overlapping scan read with the wrong spacing fills the box, so the slab disappears and the score rises. The frozen protocol calls axis 0 "z-geometry"; that name was too broad.
4. **The same thing happens in real screening, without any intervention by us (H7).** When a person's yearly scan changes between stretched and not stretched, Sybil's score jumps, beyond what the radiologist's findings explain. With axis 0 switched off, the jump is gone. **But almost all of it comes from GE scanners** (121 of 134 changed pairs).
5. **H3 failed.** We predicted that the z-fix changes the alarm in more than 5% of exams. On test it was 4.5% [2.9%, 6.3%]. The z-fix mostly *removed* alarms on test (27 lost, 7 gained), unlike dev (38 lost, 31 gained).
6. **Dev flattered Sybil a lot.** On dev, Sybil looked much better than the radiologists' recorded findings. On test it is not better: 1-year AUROC 0.914 (Sybil) against 0.947 (the form built from everything the radiologist recorded, including the screening call; section 2.1b), and adding Sybil to the form plus image measures adds nothing (−0.004 [−0.029, +0.020]).
7. **Harm was not shown, and could not be shown.** Of the 9 one-year cancers in the stretched exams, the main and the z-fix run catch the same 7. "No difference" here does not mean "no harm" (too few cancers, as stated before the test).

## 1. The six frozen hypotheses on test (primary; Holm over six)
| | Statement | Null (direction) | Dev | **Test** [95% CI] | One-sided p | **Holm** | Test counts |
|---|---|---|---|---|---|---|---|
| H1 | the z-fix moves the score materially (share with \|Δℓ̄_6\| ≥ 0.25 dev SD) | > 0.30 | 0.670 | **0.657 [0.620, 0.695]** | 7e-80 | **confirmed** | 759 exams, 342 participants, 9 one-year cancers |
| H2 | the z-fix lowers the score (mean Δℓ̄_1) | < −0.10 | −0.326 | **−0.366 [−0.411, −0.320]** | 1e-29 | **confirmed** | same |
| H3 | the z-fix changes the screening flag (share of exams) | > 0.05 | 0.075 | **0.045 [0.029, 0.063]** | 0.72 (corrected 23 Nov from 0.73; exact 0.72497) | **not confirmed (failed)** | same |
| H4 | the kernel changes the flag in fewer than 5% of exams | < 0.05 | 0.018 | **0.018 [0.008, 0.030]** | 3e-8 | **confirmed** | 500 pairs, 500 participants |
| H6 | shared axis 0 of `pooled` carries the z-fix drop (Δℓ̄_1 with axis 0 off minus Δℓ̄_1) | > +0.20 | +0.408 | **+0.407 [0.401, 0.411]**; halves 0.407 / 0.406 | < 1e-15 | **confirmed** | 759 exams, 342 participants |
| H7 | in real follow-up, the score jumps with a change of stretch status (OLS b, adjusted for ΔF1) — **partly seen** | > +0.10 | +0.246 | **+0.311 [0.185, 0.435]**; halves 0.419 / 0.226 | 0.0004 | **confirmed** | 4,353 pairs, 2,224 participants, 134 changed (92 stretched → not, 42 not → stretched) |

- **5 of 6 confirmed.** Holm order: H6, H1, H2, H4 (each p far below its level), H7 (p 0.0004 against α/2 = 0.025), H3 (p 0.72 against 0.05: not rejected; corrected 23 Nov from 0.73).
- **Run rules of N3:** rule 1 (NaN guard) passed before the run (0 missing values in `ratio`, `F1`, `s1`, `v_l1`, `v_l6`; 0 non-finite numbers); all six estimates and p-values are finite, so all six are "evaluated". Rule 2: the attention script ran only after the primary output was committed. Rule 3: the 36 hash-table files were untouched since `c3578c3`; form hash `b4cba3aa…`; ℓ̄_1 rebuilt from `pooled` within 2.7e-7 (limit 5e-3). Rule 4: the wording below.
- **H4 note (a real coincidence, checked):** the test numbers equal the dev numbers to three digits. Both have 9 changed flags of 500 (6 lost, 3 gained), but the flags themselves differ (test 61 and 58 flagged; dev 64 and 61), and none of the 1,000 test series is a dev series. With 500 different participants and 9 discordant pairs, the bootstrap interval depends only on that count.

## 2. Pre-stated secondary numbers (outside the Holm family; never called confirmed)
### 2.1 References (first freeze, unchanged): Sybil against the recorded findings
| | Dev | **Test** |
|---|---|---|
| 1-year cancer, all screens: AUROC Sybil (s1) | 0.969 | **0.914 [0.876, 0.947]** (6,674 exams, 2,346 participants, 86 cancers) |
| … the form F (recorded findings, frozen dev fit) | 0.928 | **0.947 [0.916, 0.971]** |
| … nodule size only | 0.874 | 0.900 [0.858, 0.937] |
| … form + image measures (FI, frozen) | 0.928 | 0.946 [0.915, 0.971] |
| … FI + Sybil minus FI (frozen combination) | +0.044 | **−0.004 [−0.029, +0.020]** |
| 6-year cancer, baseline screens: AUROC Sybil (s6) | 0.851 | **0.724 [0.674, 0.774]** (2,002 exams, 131 cancers) |
| … F / size only / FI | 0.780 / 0.662 / 0.785 | 0.742 / 0.653 / 0.752 |
| … FI + Sybil minus FI | +0.084 | **+0.001 [−0.030, +0.033]** |
| False alarms per 1,000 exams at the radiologists' sensitivity (1-year; test 94.2%, dev 90.9%): radiologists / Sybil / F / frozen combination / FI | 339 / 60 / 193 / 42 / 238 | **364 / 342 / 152 / 258 / 154** |

- These agree with the L1 test result (L1, all screens: Sybil 0.914, recorded findings 0.945). **Dev flattered Sybil:** its large dev advantage over the form is gone on test. Sybil's own paper reported a test 1-year AUROC of 0.92, which we reproduce; the dev numbers above are our discovery data, not a claim of Sybil's authors.

### 2.1b What the form F contains (added 18 Nov after the lead's question; no number changed)
- **Built by** `lung_l0/nlst_l0.py` (`build`: items from the public NLST tables `ctab`, `ctabc`, `prsn`) and **fitted by** `lung_l2/l2_form.py` (standardise + logistic regression, C = 0.3) **on Sybil's train participants only** (F1: 29,752 exams, 452 one-year cancers, all screens; F6: 9,009 baseline exams, 707 six-year cancers). Committed on 13 Nov (`81f6d97`), before S4; parameters `results/l2_form_params.json`, in the frozen hash table (LF `02ec7c2d…`); never refit on dev or test.
- **Items (F1, 43):** largest nodule ≥ 4 mm: longest diameter, log diameter, perpendicular diameter, spiculated or poorly defined margin, soft-tissue, ground-glass or mixed attenuation, upper lobe; all nodules: number, sum of diameters, any spiculated; other findings ticked by the radiologist (codes 52 to 63: micronodules, benign calcified nodules, atelectasis, pleural thickening or effusion, hilar or mediastinal adenopathy, chest-wall abnormality, consolidation, emphysema, fibrosis or scar, 6 or more non-suspicious nodules, other abnormality above the diaphragm); **comparison with the earlier scan** (interval growth, pre-existing, suspicious change of attenuation); **the radiologist's official screening result** (`res1` to `res6`: negative 1 to 3, positive 4 to 6) and the positive "isolation read" (`iso_pos`); age, sex, current smoking, screening year. **F6 (30 items)** drops everything that needs an earlier scan (and `study_yr`), but keeps `res1` to `res4`.
- **What this means for the claim:** F is not a "simple form" of measurements; it is everything the trial radiologist recorded, including the final call. In NLST a positive call (4 to 6) sent the participant to diagnostic work-up, so many cancers diagnosed within 1 year were found *because of* that call; the 1-year comparison therefore favours F (work-up bias). For later screens F also sees the earlier scan; Sybil sees one scan. The fairer comparisons are baseline screens and later cancers: L1 A2 (6 years, baseline) Sybil 0.724 against 0.745 (−0.021 [−0.073, +0.034]); L1 A5 (cancers 1 to 6 years after a negative baseline, 51 cancers) 0.580 against 0.644. Correct wording: **"On its own held-out test split, Sybil did not add information beyond what the trial radiologists recorded, including their screening call (no large gap; small differences cannot be excluded)."** Not: "Sybil is worse than a simple form." At the radiologists' own sensitivity, Sybil raised slightly fewer false alarms than the radiologists' actual calls (342 against 364 per 1,000), in line with Sybil's paper (lower false-positive rate than Lung-RADS).

### 2.2 The z-fix (T5)
- **Flags in both directions:** 85 flagged in the main run, 65 in the z-fix run; 27 lost, 7 gained; 34 changed; 37% of the 92 exams flagged in either run are flagged in one only (dev: 112 → 105, 38 lost, 31 gained, 48%).
- **By stretch class:** 1.6: 345 exams, mean Δℓ̄_1 −0.339, share ≥ 0.25 SD 0.652, flag change 0.035; 2.0: 414 exams, −0.390, 0.662, 0.053.
- **Terms of the change of ℓ̄_1 (frozen raw-unit dictionary):** T −0.059 (16% of the mean shift), N −0.012, mixed −0.207 (57%), unreplicated +0.019, residual −0.107 (29%). **H5′ (secondary, failed its random-choice test on dev): −0.0585 [−0.0611, −0.0558]**, never called confirmed. Old H5 (share of Var ℓ̄_1 carried by T families): 0.0506 [0.0502, 0.0510] (dev 0.0505).
- **Harm (T5; pre-stated, with what the test can detect):** 1 year (754 exams, 9 cancers): main 7 of 9 (0.78 [0.40, 0.97]), z-fix 7 of 9; 0 caught by one run only; AUROC 0.921 and 0.897 (difference −0.024 [−0.097, +0.020]). 6 years, baseline (264 exams, 17 cancers): main 6 of 17 (0.35 [0.14, 0.62]), z-fix 5 of 17 (0.29 [0.10, 0.56]); 1 caught by the main run only, 0 by the z-fix only; AUROC 0.699 and 0.686 (−0.013 [−0.057, +0.034]). **Fewer stretched cancers than expected (9, not 11 to 12). No harm was shown, and none could be shown.**

### 2.3 H6 details (the shared axes)
- **C1 (axis 0 under the z-fix):** −2.729 SD [−2.757, −2.698], halves −2.731 / −2.728 (dev −2.740).
- **The whole drop passes through axis 0:** mean Δℓ̄_1 from `pooled` −0.366; with axis 0 off **+0.040** (dev −0.326 → +0.081). 97.9% of the 759 exams are above the null +0.20 one by one.
- **The frozen axes fit the test scans:** agreement of the five members on the 11 frozen axes in test: 0.995, 0.965, 0.944, 0.940, 0.908, 0.865, 0.851, 0.830, 0.802, 0.770, 0.738 (all 11 ≥ 0.70).
- **Axis 0 under the kernel change:** +0.009 SD (dev +0.009). The kernel does not move it.
- **Share of exams moving ≥ 0.25 SD (ℓ̄_6):** 0.657 plain, 0.545 [0.507, 0.583] with axis 0 off (dev 0.670 and 0.550): the axis removes the average drop, not the exam-by-exam scatter.
- **AUROC with axis 0 off (all test exams):** 1 year 0.9163 → 0.9160 (difference −0.0003 [−0.0046, +0.0035]); 6 years 0.7287 → 0.7300 (+0.0013 [−0.0059, +0.0083]). Switching the axis off neither helps nor hurts discrimination.

### 2.4 H7 details (real follow-up)
- **With axis 0 off: b = −0.046 [−0.175, +0.078]** (dev −0.094): the jump disappears. Axis 0 itself jumps 2.39 SD [2.28, 2.50] per change of stretch status (dev 2.29).
- **Group means of Δℓ̄_1:** stretched → not −0.200 (92 pairs); unchanged +0.045 (4,219); not → stretched +0.426 (42). Flag flips 7.6%, 8.7%, 16.7%.
- **Same scanner model:** +0.347 [0.099, 0.566] (3,205 pairs, 36 changed). **Ratio 0 counted as not stretched:** +0.295 [0.167, 0.422] (dev +0.227). **Both screens without cancer within 1 year** (uses outcomes; written after the primary file): +0.322 [0.191, 0.438] (4,275 pairs, 130 changed).

### 2.5 Where Sybil looks (`results/s6/s6_attention_test.json`; descriptive; conventions frozen from dev)
| Group (test) | Exams | Slice attention within ±1 bin of the largest nodule | Shuffled median (97.5th) | Dev |
|---|---|---|---|---|
| cancer within 1 year | 78 | **73%** | 27% (35%) | 71% |
| no cancer, nodule ≥ 8 mm | 813 | 46% | 21% (23%) | 51% |
| no cancer, nodule 4 to 8 mm | 1,957 | 32% | 22% (23%) | 31% |

In-plane, at the nodule's slice bin: 89% of attention on the nodule's lung side (cancer, 78 exams; dev 90%), 75% (≥ 8 mm, 808; dev 76%). The maps are coarse (one bin is 20 mm of Sybil's box).

## 3. Exploratory (N6; `results/s6/s6_explore_test.json`; script committed before the frozen run; not hypotheses)
- **Misses at the frozen dev τ90, 1-year cancers, all screens (86 cancers):** Sybil 14 of 86 (16%; dev 6 of 88), the radiologists 5 of 86, the form 9 of 86; 3 missed by both Sybil and the radiologists. By histology: adeno 5 of 45, squamous 4 of 20, small-cell 1 of 8, other 4 of 13 (subgroups under 10 cancers: no claim).
- **6-year cancers, baseline screens (131 cancers):** Sybil missed 70 of 131 (53% [45%, 62%]; dev 54 of 135). Small-cell 10 of 15, central 10 of 13, stage IV 17 of 25, squamous 24 of 33; by time to diagnosis 5 of 41 (within 1 year), 8 of 16 (1 to 2 years), 24 of 34 (2 to 4), 33 of 40 (4 to 6). The same pattern as dev: Sybil's long-range score mostly misses cancers that appear late, central and small-cell cancers.
- **Z-fix by subgroup (T5):** H6 per exam +0.39 (class 1.6) and +0.42 (2.0); GE +0.42 (352 exams), Philips +0.39 (353), Siemens +0.41 (54); years 0, 1, 2: +0.405, +0.408, +0.407; with or without a lung cut: +0.418 / +0.357. Mean Δℓ̄_1 between −0.28 (Siemens) and −0.42 (no lung cut).
- **H7 by scanner maker of the pair:** both screens GE: b +0.407 [0.280, 0.531] (2,183 pairs, 88 changed); one GE: +0.214 [−0.118, +0.536] (89 pairs, 33 changed); neither GE: −0.318 [−0.852, +0.263] (2,081 pairs, 13 changed); all pairs except both-GE: +0.114 [−0.175, +0.393] (46 changed). **121 of the 134 changed pairs involve a GE scanner** (dev 195 of 215). Outside GE the test cannot say anything.

## 3b. Plan X1: the added value of Sybil beyond the radiologists' record (EXPLORATORY; 18 Nov)
Plan written and committed before it ran on test (`0d39e6a`; log 18 Nov); script `s7_added_value.py` and its dev check committed before the test run (`1bdb0be`); test output committed before reading (`352670c`): `results/s7/s7_added_value_test.json` (dev: `s7_added_value_dev.json`). Comparators fitted on Sybil's **train** participants only (or not fitted); combination weights and scenario cuts from dev. Every cell is in the file; about 140 cells, so some nominal intervals that exclude 0 are expected by chance.

**Comparators:** C1 the frozen form (all the radiologist recorded, including the call); C2 findings only (no call); C3 the call only; C4 gradient boosting on findings only; C5 largest nodule size.

**AUROC on test (Sybil minus comparator, 95% CI):**
| Endpoint (test) | Cancers | Sybil | C1 full form | C2 findings only | C3 call only | C4 boosted findings | C5 size |
|---|---|---|---|---|---|---|---|
| E1 1 year, all screens | 86 | 0.914 | 0.947 (−0.033 [−0.067, −0.003]) | 0.938 (−0.023 [−0.062, +0.011]) | 0.881 (+0.034 [−0.004, +0.067]) | 0.950 (−0.036) | 0.900 (+0.014) |
| E2 1 year, baseline | 41 | 0.927 | 0.927 (0.000 [−0.055, +0.053]) | 0.925 (+0.001) | 0.771 (**+0.155** [0.103, 0.201]) | 0.935 (−0.009) | 0.908 (+0.019) |
| E3 2 years, baseline | 57 | 0.877 | 0.882 (−0.005) | 0.889 (−0.012) | 0.738 (**+0.139**) | 0.898 (−0.021) | 0.840 (+0.037) |
| E4 6 years, baseline | 131 | 0.724 | 0.742 (−0.019 [−0.061, +0.028]) | 0.747 (−0.024 [−0.069, +0.023]) | 0.592 (**+0.132**) | 0.757 (−0.033) | 0.653 (**+0.071**) |
| E5 1–6 years after a negative baseline | 51 | 0.580 | 0.625 (−0.045) | 0.637 (−0.057) | 0.505 (+0.075) | 0.632 (−0.052) | 0.497 (**+0.083**) |
| E6 1 year after a negative call | 5 | (no claim: 5 cancers) | | | | | |
| E7 1 year after a positive call | 81 | 0.896 | 0.936 (−0.039 [−0.078, −0.005]) | 0.931 (−0.034) | 0.740 (**+0.157**) | 0.944 (−0.047) | 0.860 (+0.036) |

**Does adding Sybil help? (AUROC of comparator + Sybil minus comparator)**
| | E1 | E2 | E4 | E5 |
|---|---|---|---|---|
| C1 + Sybil, weights from dev (M2) | −0.005 [−0.030, +0.018] | +0.017 [−0.024, +0.060] | +0.005 [−0.026, +0.038] | −0.019 |
| C1 + Sybil, cross-fitted on test (M3) | +0.002 [−0.020, +0.019] | +0.026 [0.000, +0.054] | +0.013 [−0.011, +0.038] | −0.005 |
| C2 + Sybil (M2 / M3) | +0.003 / +0.007 | +0.019 / +0.026 | +0.004 / +0.013 | −0.017 / −0.004 |
| C3 + Sybil (M2 / M3) | **+0.056 / +0.080** | **+0.165 / +0.217** | **+0.133 / +0.145** | +0.058 / **+0.138** |
| C5 + Sybil (M2 / M3) | +0.021 / +0.035 | +0.029 / +0.039 | **+0.070 / +0.079** | **+0.086 / +0.123** |

Likelihood-ratio tests of Sybil given each comparator are very small p in E1 to E4 and E7 (Sybil carries some statistically detectable extra signal), but the gain in discrimination over C1, C2 and C4 stays within ±0.03.

**Decision curve (E1, 6,674 exams, 86 cancers; net benefit per 1,000 exams):** at risk thresholds 0.5% to 5%, form + Sybil minus form between −0.78 and +0.06 (all intervals include 0); Sybil alone minus the form −0.8 to −2.4 (intervals exclude 0 at 0.5%, 1%, 3%, 5%). Adding Sybil gives no net benefit.

**Scenarios (cuts fixed on dev):**
- **Rule-out among positive calls** (2,507 exams, 81 one-year cancers, 2,426 false-positive calls): Sybil's dev cut (keeping 95% of dev cancers) removes 88% of the false-positive calls on test but **loses 22 of 81 cancers (27%)**; the dev cut does not transfer (dev flatters Sybil). The findings-only model at its dev cut removes **57% [55%, 59%] of the false-positive calls and loses 1 of 81 cancers**. (Known context: Lung-RADS applied to NLST also lowered the false-positive rate; this is a re-weighting of what the radiologist recorded, not new imaging information.)
- **Rule-in among negative calls:** 1 year (E6): 5 cancers, no claim (Sybil flagged 2, findings 0). Cancers 1 to 6 years after a negative baseline (E5, 1,140 exams, 51 cancers): Sybil flags 6, the findings model 7, **none by both** (13 of 51 by either); false alarms per 1,000: Sybil 62, findings 101.

**What X1 shows (exploratory):**
1. **Sybil carries about the same information as the radiologists' structured findings, not more.** Removing the radiologist's final call from the form changes little (E1 0.947 → 0.938; E4 0.742 → 0.747). **Correction (20 Nov):** this does *not* rule out work-up bias. In NLST, a nodule of 4 mm or more made the screen positive, so the findings still carry most of the call; 83 of the 86 E1 cancers were found after a positive screen (E4 81 of 131; E5 22 of 51). The cleaner comparisons are later cancers (E4, E5) and cancers not found by a positive screen (section 3e). At 1 year on baseline screens (E2), cross-fitted form + Sybil adds +0.026 [0.000, +0.054]: a small gain at baseline, where the form has no earlier scan, cannot be excluded.
2. **Sybil is much better than the coarse screening call and than nodule size alone** (+0.13 to +0.16 over the call at baseline; +0.07 over size at 6 years) and adds to them. This is where an AI's advantage shows when the comparator is a category (as Lung-RADS in Sybil's paper).
3. **Thresholds tuned on dev are unsafe on test:** the rule-out cut lost 27% of the cancers it was set to keep at 5%.
4. **Sybil and the findings catch different late cancers** (no overlap in E5), but both catch few; with 51 cancers this is a hint, not a result.

## 3c. Plan X3: do age, sex and smoking change Sybil's added value? (EXPLORATORY; 19 Nov)
Plan committed before the test run (`dcfba8f`), script and dev check (`8120231`), test output committed before reading (`474696d`): `results/s8/s8_demographics_test.json`. Models fitted on train only; combinations weighted on dev (M2) or cross-fitted on test (M3).

| Test, AUROC | Demographics only | Sybil | Sybil + demographics (M2 / M3) | Findings only (no call, no demographics) | Findings + demographics | Full form |
|---|---|---|---|---|---|---|
| E1 1 year, all screens (86 cancers) | 0.607 | 0.914 | 0.914 / 0.909 | 0.939 | 0.938 | 0.947 |
| E2 1 year, baseline (41) | 0.584 | 0.927 | 0.928 / 0.921 | 0.929 | 0.925 | 0.927 |
| E4 6 years, baseline (131) | 0.623 | 0.724 | 0.745 / 0.741 | 0.727 | 0.747 | 0.742 |
| E5 1–6 years after a negative baseline (51) | 0.590 | 0.580 | 0.592 / 0.576 | 0.659 | 0.637 | 0.625 |

- **Adding age, sex and smoking to Sybil:** no change at 1 year (+0.000 [−0.004, +0.005]); +0.022 [+0.002, +0.042] at 6 years (M3 +0.026 [+0.007, +0.047]). Sybil's ranking barely moves (Spearman 0.985 at 1 year, 0.91 at 6 years). Sybil's score already correlates with age (Spearman 0.24). Sybil sees only the image, so this link comes through the image; which image features carry it is not known (wording softened 20 Nov after the outside audit).
- **Like for like (Sybil + demographics against findings + demographics):** 1 year −0.023 [−0.060, +0.010]; baseline 1 year +0.003; 6 years −0.002 [−0.036, +0.034]; late cancers −0.044 (M3 −0.061 [−0.105, −0.017]). **With the same demographics on both sides, Sybil equals the radiologists' findings and is never better.**
- **Sybil against the findings alone (no call, no demographics):** −0.025 (1 year), −0.002 (baseline 1 year), −0.003 (6 years), −0.079 (late). The radiologists' findings, without their decision and without any personal data, are as good as Sybil.
- Demographics alone are weak in NLST (0.58 to 0.62): everyone was a heavy smoker aged 55 to 74.

## 3d. Plan X5: the slice-spacing tests repeated on LIDC-IDRI (EXPLORATORY external replication; 20 Nov)
Plan committed before scoring (`41ca595`); list, job change and analysis script committed before the run (`05aea53`); output committed before reading (`d6b3d53`): `results/x5/x5_lidc.json`. LIDC-IDRI: an open collection from 7 US academic centres (clinical CT, not screening), different from NLST. 197 stretched scans (one per patient; GE 134, Philips 46, Siemens 17; mostly 1.25 mm slices), 0 errors; Sybil's own volume check equal for 197 of 197; G2b and G2c pass; cost $1.45 measured.

| | Null | NLST test | **LIDC** [95% CI] | Holm over 3 |
|---|---|---|---|---|
| H1 share of exams moving ≥ ¼ SD | > 0.30 | 0.657 | **0.650 [0.584, 0.716]** | rejected |
| H2 mean change of ℓ̄_1 | < −0.10 | −0.366 | **−0.177 [−0.260, −0.095]** (p 0.037) | rejected, weakly |
| H6 axis 0 carries the drop | > +0.20 | +0.407 | **+0.395 [0.387, 0.403]** | rejected |
| C1 axis-0 shift under the z-fix (dev SD) | (secondary) | −2.729 | **−2.760 [−2.797, −2.717]** | — |

- **The mechanism replicates almost exactly at other centres:** the z-fix moves axis 0 by −2.76 SD (NLST −2.73), and axis 0 carries +0.40 of the 1-year logit (NLST +0.41); 98% of the LIDC exams are above +0.20 one by one. The frozen axes fit LIDC (member agreement 0.72 to 0.94; axis 0 0.80).
- **The size of the score change replicates (H1, 65%); its average direction is weaker:** mean −0.18 (NLST −0.37), driven by GE (−0.28, 134 scans); Philips −0.01 (46), Siemens +0.18 (17). With axis 0 off, the remaining z-fix change is +0.22 in LIDC: other parts of Sybil move the other way in these clinical scans.
- Alarms at the frozen τ90 (descriptive): 64 → 61 flagged; 19 of 197 exams (9.6%) change their alarm (11 lost, 8 gained); in LIDC most exams have known nodules.
- No outcome and no annotation was used. The "Sybil against the radiologists' findings" test is not possible on LIDC from here (its diagnosis file is on the TCIA website, which refuses the connection from this PC).

## 3e. Plan X7: free checks after the outside review (EXPLORATORY, post hoc; 20 Nov)
Plan committed before anything was computed (`413dc07`); scripts and dev check (`59b8d7c`; the dev check reproduces the dev U3 table, the dev z-fix flags and R3b exactly); test output committed before reading (`749720e`): `results/x7/x7_sensitivity_test.json`, `results/x7/x7_att_zfix_test.json`. **Post hoc:** the checks were chosen after the outside review, which had read the test results. Participant bootstrap 2,000, seed 0. Comparators as X1 (fitted on Sybil's train participants only).

**1. Work-up bias (the form's weak point).** Form against Sybil where the radiologist's record did not lead to the diagnosis:
| Test | Cancers | Sybil | Form (C1) | Findings only (C2) | Sybil − form | Findings + Sybil − findings (cross-fitted) |
|---|---|---|---|---|---|---|
| W1 6 years, baseline; only cancers 1 to 6 years after the scan | 90 | 0.629 | 0.669 | 0.669 | −0.040 [−0.102, +0.020] | +0.006 [−0.022, +0.035] |
| W2 6 years, baseline; only cancers **not** found after a positive screen | 50 | 0.573 | 0.620 | 0.621 | −0.047 [−0.131, +0.036] | −0.006 [−0.030, +0.014] |
| W3 after a negative baseline; not found after a positive screen | 29 | 0.534 | 0.586 | 0.586 | −0.052 [−0.174, +0.074] | −0.008 [−0.060, +0.037] |

1 year, all screens: 83 of 86 cancers were found after a positive screen, 3 after a negative one (no claim). **Reading:** where the record did not lead to the diagnosis, the radiologists' record still scores higher than Sybil (by 0.04 to 0.05), and Sybil adds nothing to it. The intervals include 0 (50 and 29 cancers): work-up bias does not explain the form result away, but small differences in either direction cannot be excluded.

**2. Censoring at 6 years (audit D2).** 277 of 2,279 baseline exams (12.2%) have less than 6 years of follow-up; their median follow-up is 5.84 years (almost all end just short of 6 years). IPCW: Sybil 0.721, form 0.735, findings 0.740; Sybil − form −0.014 [−0.061, +0.033]. Censored counted as cancer-free: −0.017 [−0.063, +0.030]. Unchanged from the complete-case result (0.724 vs 0.742).

**3. Calibration and decision curves with calibrated scores (audit S1).** As given, on test all three predict about 15% too many 1-year cancers (O/E: Sybil 0.86, form 0.84, findings 0.85). Calibration slope at 1 year: Sybil 0.84 [0.73, 1.04], form 1.10 [0.99, 1.24]; at 6 years Sybil 0.77 [0.63, 0.93] (scores too spread), form 0.86 [0.72, 1.03]. Recalibrating on dev makes Sybil's slope worse (0.64: dev flatters Sybil). Decision curve with every score recalibrated on dev, net benefit per 1,000 exams: **E1** form + Sybil minus form −0.1 to −0.8 (all intervals include 0); Sybil alone minus form −0.9 to −2.4 (intervals exclude 0 at 1% to 5%). **E2** (baseline, 41 cancers): form + Sybil minus form −1.2 to +0.1 (all include 0). The small AUROC gain at baseline (+0.026, section 3b) gives no net benefit.

**4. Repeated screens of one person (audit S2).** With participant-clustered intervals, Sybil's coefficient given the form is 0.44 [0.27, 0.64] (p 3e-6; given findings only 0.46): Sybil carries some extra statistical signal, as X1's LR test said, but it brings no gain in AUROC or net benefit. Rule-out among positive calls with clustered intervals: Sybil's dev cut removes 88% [87%, 90%] of false-positive calls but loses **27% [18%, 38%] of the cancers** (22 of 81); the findings model removes 57% [55%, 59%] and loses **1.2% [0%, 4.2%]** (1 of 81); difference in cancers lost 26 points [17, 36].

**5. Harm at cuts fixed on dev (audit D1; replaces the in-sample row of section 2.1 as the harm comparison).** 1-year cancer, all screens (6,674 exams, 86 cancers):
| Test | Cut | Cancers caught | Sensitivity | False alarms per 1,000 exams |
|---|---|---|---|---|
| Radiologists' call | (their actual call) | 81 | 94.2% | 364 |
| Sybil | dev cut matched to the radiologists' dev sensitivity (τ_rad) | **61** | **70.9%** | 65 |
| Form | the same rule, dev | **82** | **95.3%** | **215** |
| Findings only (no call) | the same rule, dev | 82 | 95.3% | 280 |
| Sybil | frozen τ90 | 72 | 83.7% | 115 |
| Form | frozen τ90 | 77 | 89.5% | 113 |

**Reading:** the cut chosen on dev to give Sybil the radiologists' sensitivity catches only 61 of 86 cancers on test (25 missed; the radiologists missed 5): Sybil − radiologists −23 points [−34, −13]. The form's dev cut transfers: the radiologists' sensitivity (82 vs 81 caught) with 148 fewer false alarms per 1,000 exams; findings only: +1.2 points [0.0, +3.9] sensitivity and −83 [−94, −73] false alarms per 1,000 against the radiologists. At τ90, Sybil and the form raise the same number of false alarms (115 vs 113), and Sybil catches 5 fewer cancers (−5.8 points [−14.4, +2.4]).

**6. Z-fix alarm changes on test (outcome-free; the measure planned for O2a).** At τ90: 27 alarms lost, 7 gained; net −26 per 1,000 stretched exams [−44, −10] (the stretch adds about 26 alarms per 1,000 stretched exams). At τ_rad: 14 lost, 5 gained; net −12 [−25, 0]; discordant 2.5% [1.4%, 3.8%].

**7. Attention under the z-fix on test (audit 6.4; the dev analysis R3b repeated).** 301 stretched exams with a recorded nodule of 4 mm or more: share of attention within ±1 bin of the nodule **30.8% (as published) → 40.6% (z-fix), +9.8 points [+7.0, +12.5]** (dev +6.3 [+3.8, +8.8]); nodule outside Sybil's box 11 → 0; attention peak at the nodule 34% → 45%; nodules ≥ 8 mm 42% → 54%. Stretched exams draw less attention to the nodule than other exams (−7.1 points [−12.4, −2.0]). The stretch moves Sybil's attention away from the nodule: a mechanism, not shown harm.

**8. Crop and pad (audit C1).** Sybil pads every z-fix exam (759 of 759), and also 99.9% of ordinary test scans (5,946 of 5,952). The drop is −0.36 [−0.41, −0.30] when the main run was cropped (627 exams) and −0.42 [−0.50, −0.34] when it was not (132). So cropping does not explain the drop, and the z-fix puts stretched scans into the same crop/pad state as ordinary scans. The padding itself cannot be separated with these data.

**9. Data notes (audit D3, S5).** Missing age, sex or smoking on test: 0. Sybil's calibrated 1-year score takes 209 distinct values on test, and 1,098 of 6,715 exams (16%) tie at 0.0; at τ90, 11.6% of cancer-free test exams are flagged (nominal 10%).

**What X7 shows (exploratory):**
1. **The form result holds** under the work-up check, the censoring check, calibration and clustered intervals: Sybil is never better than the radiologists' record, also where the record did not lead to the diagnosis (by 0.04 to 0.05; intervals include 0).
2. **The clearest harm is in the thresholds:** Sybil's dev-chosen cut misses 25 of 86 cancers on test, against 5 for the radiologists and 4 for the form's dev cut (which also raises 148 fewer false alarms per 1,000 than the radiologists).
3. **The stretch moves Sybil's attention away from the nodule** (replicated on test) and adds about 26 alarms per 1,000 stretched exams at τ90.

## 3f. Plan X8: Sybil against published rules that we did not fit (EXPLORATORY, post hoc; 21 Nov)
- **Corrections (22 Nov, after two independent reviews; log 22 Nov; the corrected numbers are in section 3g; no number in the X8 files changed):**
  - **Correction:** the Brock rows of table 2 are not valid: the −99 filler for exams without a nodule went straight into a linear model. Corrected: +0.011 [−0.021, +0.041] at 1 year, +0.036 [+0.001, +0.075] at 6 years (3g).
  - **Correction:** the Lung-RADS gains of table 2 pooled categories 1 and 2, which weakened the rule alone (0.868 instead of 0.880). Corrected: +0.050 [+0.005, +0.094] at 1 year, +0.064 [+0.011, +0.117] at 6 years (3g).
  - **Correction:** "at 6 years Sybil is clearly better than both rules" holds for Lung-RADS (+0.085) but not clearly for Brock: 55 of the 131 six-year cancers are in exams without a nodule, which published Brock does not score; with one dev-fitted level for them, Sybil − Brock is +0.019 [−0.023, +0.061] (3g).
  - **Correction:** point 4 below ("the threshold harm replicates; misses 21 more cancers") compares two different false-alarm levels (28 vs 100 per 1,000). At the same false-alarm level Sybil catches 69 and Lung-RADS 68. The finding is "a cut set on dev cancers does not transfer", not "Sybil misses more cancers than Lung-RADS".
  - **Correction:** point 3 below (the form's edge comes from combining the full record) was not tested; it is a possible reading only.
  - **Correction:** the code check cannot confirm the coding: the Sybil splits have about 1.4 times more positive NLST calls than the whole trial, and Pinsky applied Lung-RADS v1.0. The 0.81 and 0.83 in table 2's note came from an unlogged check; X9 writes the cross-fitted numbers to its file. The plan sentence "unchanged in v2022" is wrong (v2022 changed the management of stable 4A nodules). Smaller coding errors (4X on the top nodule only; growth "unable to determine" coded stable; attenuation change not used) change 17 test exams (3g). Family history is missing from the IDC tables only.
- **Why:** the strongest objection to the form is "you fitted it yourselves on NLST". X8 uses two published rules with **no fitting by us**: **Lung-RADS** (v1.1 rules) and **Brock** (PanCan full model with spiculation), both built from the NLST records. Plan in `docs/EXECUTION_LOG.md` (21 Nov, commit `06a8eef`, before anything was computed); script `x8_fixed_rules.py`; dev check `806188a`; test run once, output committed before reading (`c02538c`): `results/x8/x8_fixed_rules_{dev,test}.json`.
- **Code check (dev):** our Lung-RADS ≥ 3 calls 14.2% of cancer-free baseline exams positive and 6.0% after baseline; Pinsky et al. 2015 (whole NLST) found 12.8% and 5.3%. Test: 15.7% and 7.3%; sensitivity 78.0% and 80.0% (Pinsky 84.9%, 78.6%).
- **Limits:** this is Lung-RADS **reconstructed from the NLST forms**, not the radiologists' own Lung-RADS reading. NLST does not record the solid part of part-solid nodules (two assumptions; they change 60 of 6,715 test exams and the AUROC by at most 0.008). Brock without family history (not in the public tables).

**1. AUROC on test (participant bootstrap; Sybil s1 for 1 year, s6 for 6 years):**
| Endpoint (cancers) | Sybil | Lung-RADS | Lung-RADS + size | Brock | Size alone | Form (C1) | Findings only (C2) |
|---|---|---|---|---|---|---|---|
| E1 1 year, all screens (86) | 0.914 | 0.880 | 0.905 | 0.906 | 0.900 | **0.947** | 0.938 |
| E2 1 year, baseline (41) | 0.927 | 0.870 | 0.900 | 0.915 | 0.908 | 0.927 | 0.925 |
| E4 6 years, baseline (131) | 0.724 | 0.638 | 0.650 | 0.658 | 0.653 | 0.742 | 0.747 |
| W2 E4 without cancers after a positive screen (50) | 0.573 | 0.521 | 0.521 | 0.513 | 0.511 | 0.620 | 0.621 |

| Sybil minus … | Lung-RADS | Brock | Form (C1) |
|---|---|---|---|
| E1 | +0.034 [−0.012, +0.081] | +0.008 [−0.031, +0.047] | −0.033 [−0.067, −0.003] |
| E2 | +0.057 [−0.009, +0.125] | +0.011 [−0.047, +0.074] | −0.000 [−0.055, +0.053] |
| E4 | **+0.086 [+0.040, +0.137]** | **+0.066 [+0.020, +0.113]** | −0.019 [−0.061, +0.028] |
| W2 | +0.052 [−0.036, +0.143] | +0.060 [−0.022, +0.145] | −0.047 [−0.131, +0.036] |

E6 (exams called negative): 5 cancers, no claim.

**2. Does Sybil add to the rule? (combination fitted on dev, applied to test; X1 M2):**
| | Rule alone | Rule + Sybil | Gain |
|---|---|---|---|
| E1, Lung-RADS (categories) | 0.868 | 0.929 | **+0.061 [+0.019, +0.104]** |
| E1, Brock | 0.906 | 0.923 | +0.017 [−0.018, +0.052] |
| E4, Lung-RADS | 0.644 | 0.720 | **+0.076 [+0.032, +0.119]** |
| E4, Brock | 0.658 | 0.725 | **+0.067 [+0.015, +0.118]** |

- Sybil's coefficient given the rule (E1): 0.57 [0.40, 0.78] (Lung-RADS), 0.78 [0.63, 0.95] (Brock).
- The cross-fitted gains in the file (+0.09 to +0.14) are inflated: refitting the rule fold by fold lowers the rule's own AUROC (Lung-RADS 0.868 → 0.81; Brock 0.906 → 0.83; checked after the run, no new analysis), so the dev-fitted gain above is the fair number.
- For comparison: the form alone (0.947) is above Lung-RADS + Sybil (0.929).

**3. Harm at cuts fixed on dev (E1; 86 cancers, 6,588 cancer-free exams):**
| Rule on test | Cancers caught | False alarms per 1,000 exams |
|---|---|---|
| Radiologists' NLST call | 81 (94.2%) | 364 |
| Lung-RADS ≥ 3 (no cut to choose) | 68 (79.1%) | 100 |
| Lung-RADS ≥ 4A | 67 (77.9%) | 64 |
| Sybil, cut set on dev to Lung-RADS ≥ 3's **dev sensitivity** (76.1%) | **47 (54.7%)** | 28 |
| Sybil, cut set on dev to Lung-RADS ≥ 3's **dev false-alarm rate** | 69 (80.2%) | 91 |

- At the same false-alarm level as Lung-RADS, Sybil catches about the same cancers: +1.2 points [−8.4, +10.3], −9.4 false alarms per 1,000 [−20.2, +0.9]. On dev the same cut caught 92% (81 of 88): dev flatters Sybil again.
- Lung-RADS itself transfers (76.1% on dev, 79.1% on test); Sybil's sensitivity-matched cut does not (77.3% on dev, 54.7% on test).

**What X8 shows (exploratory):**
1. **Against published rules that nobody fitted on NLST, Sybil is not worse.** At 1 year it is about equal to Brock and to Lung-RADS with size, and slightly above plain Lung-RADS (interval includes 0). At 6 years it is clearly better than both (+0.07 to +0.09).
2. **Sybil adds to Lung-RADS** (+0.06 at 1 year, +0.08 at 6 years). So the form message must be stated precisely: Sybil adds nothing beyond **the radiologists' full record combined by a model fitted on the same trial**; it does add beyond the **coarse clinical rule**.
3. **The form's edge comes from combining the full record** (call, comparison with prior scans, other findings), not from any single standard rule. Whether such a fitted model transfers to other hospitals is not known; only an outside dataset can answer this.
4. **The threshold harm replicates:** Sybil's cut chosen on dev misses 21 more cancers on test than Lung-RADS (47 vs 68), while Lung-RADS needs no cut and holds its sensitivity. (See the corrections at the top of 3f: points 1, 2 and 4 are corrected in 3g.)

## 3g. Plan X9: corrected rules and measures beyond AUROC (EXPLORATORY, post hoc; 22 Nov)
- **Why:** two independent reviews of X8 (a fresh Claude agent that re-ran X8; Gemini 4 Neon, read-only) found the coding errors listed at the top of 3f; the lead asked: "auc is not always whats matter, sens, apc, npv, ppv, nlr, plr". Plan `96453cc` (before anything was computed); script and dev check `3bde287` (one tie rule fixed on dev before the test run); test run once, output committed before reading (`4076a40`): `results/x9/x9_rules_thresholds_{dev,test}.json`.
- **Operating points:** cuts for Sybil, the form, findings only and Brock are set on **cancer-free dev exams only** (dev cancers flatter Sybil), to the dev false-alarm share of Lung-RADS ≥ 3 ("L3", about 10% of cancer-free exams), of Lung-RADS ≥ 4A ("L4", about 6%), of the radiologists' call ("R", about 35%), and at 10% ("90"). Sybil's score has steps, so its achieved dev share is up to 0.02 off the target; the file gives every cut and its achieved share. The corrections change the Lung-RADS category of 17 of 6,715 test exams.

**1. AUROC on test (corrected rules):**
| Endpoint (cancers) | Sybil | Lung-RADS | Brock (published; no nodule = lowest) | Brock (no-nodule level fitted on dev) | Form (C1) |
|---|---|---|---|---|---|
| E1 1 year, all screens (86) | 0.914 | 0.879 | 0.905 | 0.914 | **0.947** |
| E2 1 year, baseline (41) | 0.927 | 0.869 | 0.915 | 0.910 | 0.927 |
| E4 6 years, baseline (131) | 0.724 | 0.639 | 0.658 | 0.705 | 0.742 |
| W2 E4 without cancers after a positive screen (50) | 0.573 | 0.522 | 0.515 | 0.565 | 0.620 |

| Sybil minus … | Lung-RADS | Brock (published) | Brock (dev level) | Form |
|---|---|---|---|---|
| E1 | +0.035 [−0.011, +0.082] | +0.009 [−0.030, +0.048] | −0.000 [−0.037, +0.035] | −0.033 [−0.067, −0.003] |
| E2 | +0.058 [−0.008, +0.126] | +0.012 [−0.046, +0.074] | +0.016 [−0.044, +0.076] | −0.000 [−0.055, +0.053] |
| E4 | **+0.085 [+0.040, +0.136]** | **+0.066 [+0.019, +0.113]** | +0.019 [−0.023, +0.061] | −0.019 [−0.061, +0.028] |
| W2 | +0.051 [−0.037, +0.143] | +0.058 [−0.027, +0.144] | +0.008 [−0.082, +0.096] | −0.047 [−0.131, +0.036] |

Exams without a nodule ≥ 4 mm hold 7 of 86 one-year cancers and 55 of 131 six-year cancers.

**2. Does Sybil add to the rule? (dev-fitted; Lung-RADS with all categories; Brock with a "no nodule" indicator)**
| | Rule alone (unfitted) | Rule + Sybil | Gain over the dev-fitted rule | Gain over the unfitted rule |
|---|---|---|---|---|
| E1, Lung-RADS | 0.879 | 0.929 | **+0.050 [+0.005, +0.094]** | +0.050 [+0.005, +0.094] |
| E1, Brock | 0.905 | 0.925 | +0.011 [−0.021, +0.041] | +0.019 [−0.015, +0.055] |
| E4, Lung-RADS | 0.639 | 0.712 | **+0.064 [+0.011, +0.117]** | +0.074 [+0.018, +0.131] |
| E4, Brock | 0.658 | 0.741 | +0.036 [+0.001, +0.075] | +0.083 [+0.033, +0.134] |

Cross-fitted rule alone (now in the file): Lung-RADS 0.839 (E1) and 0.603 (E4), Brock 0.895 and 0.666; the cross-fitted gains (+0.035 to +0.112) stay above the dev-fitted ones because the refitted rule loses AUROC.

**3. Measures at fixed cuts (E1, 1 year, all screens: 86 cancers, 6,588 cancer-free exams; prevalence 1.3%):**
| Level | Score | Cancers caught | Sensitivity | Specificity | PPV | NPV | LR+ | LR− | False alarms per 1,000 |
|---|---|---|---|---|---|---|---|---|---|
| L3 | Lung-RADS ≥ 3 | 68 | 79.1% | 89.7% | 9.1% | 99.70% | 7.7 | 0.23 | 101 |
| L3 | Sybil | 69 | 80.2% | 90.7% | 10.1% | 99.72% | 8.7 | 0.22 | 92 |
| L3 | Form | **77** | **89.5%** | 89.7% | 10.2% | 99.85% | 8.7 | **0.12** | 102 |
| L3 | Brock | 70 | 81.4% | 89.9% | 9.5% | 99.73% | 8.1 | 0.21 | 99 |
| L4 | Lung-RADS ≥ 4A | 67 | 77.9% | 93.4% | 13.3% | 99.69% | 11.8 | 0.24 | 65 |
| L4 | Sybil | 61 | 70.9% | 93.5% | 12.4% | 99.60% | 10.8 | 0.31 | 65 |
| L4 | Form | **73** | **84.9%** | 92.9% | 13.5% | 99.79% | 12.0 | **0.16** | 70 |
| R | Radiologists' call | 81 | 94.2% | 63.2% | 3.2% | 99.88% | 2.6 | 0.09 | 364 |
| R | Sybil | 82 | 95.3% | 65.3% | 3.5% | 99.91% | 2.8 | 0.07 | **342** |
| R | Form | 83 | 96.5% | 63.4% | 3.3% | 99.93% | 2.6 | 0.06 | 361 |

- Sybil − form, sensitivity: L3 −9.3 points [−18.1, −1.1]; L4 −14.0 [−24.4, −4.5]; R −1.2 [−6.5, +3.9], with 19 fewer false alarms per 1,000 [3, 37]. Sybil − Lung-RADS ≥ 3: +1.2 points [−8.4, +10.3]. Form − Lung-RADS ≥ 3: **+10.5 points [+4.7, +16.9]** at the same false alarms. Sybil − the radiologists' call at R: 21 fewer false alarms per 1,000 [3, 42], same sensitivity.
- **E2 (1 year, baseline; 41 cancers):** L3: Sybil 36, form 37, Lung-RADS 32, with 32 fewer false alarms per 1,000 for Sybil than the form [15, 48] (partly because Sybil's step puts its dev share at 12.1% against the 14.2% target). R: 39 of 41 for Sybil, the form and the call alike; Sybil **52 fewer false alarms per 1,000** than the form [27, 76] and 50 fewer than the call [26, 74].
- **E4 (6 years, baseline; 131 cancers):** L3: Sybil 63, form 59, Brock 59, Lung-RADS 54 (Sybil − Lung-RADS +6.9 points [0.0, +13.8]). R: form 100, Sybil 86 (−10.7 points [−19.7, −2.2]) with 36 fewer false alarms per 1,000 for Sybil [12, 62].

**4. AUPRC (average precision; a score with no skill gets the prevalence):**
| | Prevalence | Sybil | Form | Findings only | Brock | Lung-RADS | Lung-RADS + size | Size | Call |
|---|---|---|---|---|---|---|---|---|---|
| E1 | 0.013 | 0.320 | **0.419** | 0.391 | 0.256 | 0.160 | 0.297 | 0.206 | 0.031 |
| E2 | 0.018 | 0.418 | 0.391 | 0.388 | 0.368 | 0.161 | 0.357 | 0.336 | 0.039 |
| E4 | 0.065 | 0.289 | 0.275 | 0.280 | 0.256 | 0.161 | 0.251 | 0.237 | 0.081 |

Sybil − form: E1 −0.099 [−0.212, +0.017]; E2 +0.027 [−0.120, +0.175]; E4 +0.014 [−0.049, +0.074]. Sybil − Lung-RADS: +0.160 [+0.070, +0.264], +0.257 [+0.129, +0.399], +0.128 [+0.069, +0.190].

**What X9 shows (exploratory):**
1. **Against the clinical rules (corrected):** Sybil ≈ Lung-RADS and ≈ Brock at 1 year; at 6 years better than Lung-RADS (+0.085), but not clearly better than Brock (depends on how exams without a nodule are scored). Sybil adds to Lung-RADS (+0.05 at 1 year, +0.06 at 6 years), little to Brock.
2. **Against the form, at the same false-alarm level (all 1-year screens):** the form catches 8 to 12 more of the 86 cancers than Sybil at the clinical cut levels (L3, L4), and rules out better (LR− 0.12 vs 0.22). At a high-sensitivity level (R) all catch 81 to 83 and Sybil raises about 20 fewer false alarms per 1,000.
3. **On baseline screens (the form has no earlier scan):** Sybil matches the form's sensitivity and raises fewer false alarms at the high-sensitivity level (52 fewer per 1,000; 41 cancers). This is the clearest place where Sybil helps. (**Correction, 22 Nov:** the R level is matched to the radiologists' dev false-alarm share; Sybil's step put its dev share 1.0 point below the form's, so about 10 of the 52 come from the steps, not from transfer.)
4. **PPV is low for every score** (3% to 14% at 1 year) because only 1.3% of exams have a cancer within a year; **NPV is above 99.6% for every score**, so NPV cannot separate them. Likelihood ratios and false alarms per 1,000 are the more useful numbers here.
5. **Cuts set on cancer-free dev exams transfer to test** (test false-alarm shares at most 3.4 points above dev; the fixed rules themselves rise by up to 3.2 points, because test has more positive calls); cuts set on dev cancers do not (X7, X8).

## 3h. Plan X10: a reduced "portable" form for outside partners (EXPLORATORY; 22 Nov)
- **Corrections (22 Nov, after an independent review by Gemini 4 Neon, read-only; each point checked against the files; no number in the X10 files changed):**
  - **Correction (label):** "OP R" / "R" is matched to the radiologists' **dev false-alarm share**, not to their sensitivity. Point 3 below ("at the radiologists' sensitivity") is wrong in that word.
  - **Correction:** Sybil's stepped score misses its dev target, and part of its "fewer false alarms" comes from that, not from transfer: E2 L3 Sybil 12.1% vs 14.2% target (about 21 of the 32 fewer per 1,000); E2 R 37.2% vs 38.3% (about 11 of the 53); E4 R 36.5% vs 38.4% (about 20 of the 30, and part of why Sybil caught 86 instead of 96). E1 R is the other way (Sybil 36.0% vs 34.3% on dev, yet 26 fewer on test).
  - **Correction:** "ranks cancers as well as Sybil" is too strong (section 4 rule): Sybil − P is 0.000 [−0.040, +0.041] at 1 year, so a gap of up to about 0.04 in either direction is not excluded. Correct wording: "Sybil was not better than the 14-item form; no difference was detected." Sybil + P minus P reaches +0.048 at the upper end, so "adds little" cannot exclude a gain of about 0.04. At 1 year, P − Lung-RADS (+5.8 points [0.0, +12.0]) is borderline; at 6 years it is clear (+9.2 [+1.8, +16.8]).
  - **Correction:** at 6 years P leaves out **19** items of F6 (30 − 11), not 29; and on dev the 6-year loss is larger (F − P +0.031 [+0.008, +0.054]) than on test (+0.008). The split of the 1-year F − P (+0.034) can be read from the reported AUROCs (arithmetic, not a test): findings only (C2) 0.938, so about +0.024 from the dropped non-call items and about +0.009 from the six-level call.
  - **Correction (not for partners):** P + call at 6 years has a sign flip (positive call −1.15, log diameter +1.34) because an NLST positive screen nearly means "any nodule ≥ 4 mm"; it must not be given to partners. "P + call within 0.004 of P" should read 0.005 (E4).
  - **Coding traps for partners (a coding sheet must go with the file):** the screening round must be capped at NLST's 0 to 2 (its weight is large and negative); sex is coded 1 male / 2 female; diameter is the longest diameter in mm of non-calcified nodules ≥ 4 mm and `log_dia` = ln(1 + diameter); "growth" and "new" come from any comparison record of the exam; "upper lobe" excludes the lingula (as in F). Raw age, sex and smoking are complete in train, dev and test (checked 22 Nov: 0 missing), so the all-group median filling in `nlst_l0.build` has no effect.
- **Why:** other screening sites do not record NLST's 43 form items. The lead: "creat it in train set ... first testing in dev and test set we have". Plan `39f3f7a` (before anything was computed); script, dev check and **frozen parameter file** `results/x10/x10_portable_form_params.json` (SHA-256 `106da977…`, stored byte-exact) `1cba113`/`bd4f8d8`; test run once, output committed before reading (`c474463`).
- **The portable form P (a strict subset of F; same model, penalty and train rows as F; never refit):** largest nodule ≥ 4 mm: longest diameter and its log, ground-glass, part-solid, spiculated, upper lobe; number of nodules; emphysema; age, sex, current smoking; repeat screens only: growth, new abnormality, screening round. P1 (1 year, all screens) 14 items; P6 (6 years, baseline) 11 items. Secondary: P + the screening call (positive or negative).

**1. AUROC and AUPRC on test:**
| Endpoint (cancers) | Sybil | Full form F (43 items) | **Portable P** | P + call | Lung-RADS | Brock |
|---|---|---|---|---|---|---|
| E1 1 year, all screens (86) | 0.914 | 0.947 | **0.914** | 0.915 | 0.879 | 0.905 |
| E2 1 year, baseline (41) | 0.927 | 0.927 | **0.909** | 0.911 | 0.869 | 0.915 |
| E4 6 years, baseline (131) | 0.724 | 0.742 | **0.735** | 0.739 | 0.639 | 0.658 |
| W2 E4 without cancers after a positive screen (50) | 0.573 | 0.620 | **0.623** | 0.622 | 0.522 | 0.515 |
| AUPRC E1 (prevalence 0.013) | 0.320 | 0.419 | 0.313 | 0.312 | 0.160 | 0.256 |

| | Sybil − P | F − P (what the 29 dropped items add) |
|---|---|---|
| E1 | 0.000 [−0.040, +0.041] | **+0.034 [+0.011, +0.060]** |
| E2 | +0.018 [−0.043, +0.083] | +0.018 [+0.002, +0.041] |
| E4 | −0.011 [−0.059, +0.039] | +0.008 [−0.009, +0.026] |
| W2 | −0.050 [−0.143, +0.043] | −0.003 [−0.039, +0.033] |

**2. At fixed cuts (set on cancer-free dev exams; X9 rule):**
| Level | Endpoint | Lung-RADS ≥ 3 or call | Sybil | F | **P** |
|---|---|---|---|---|---|
| L3 (about 10% false alarms) | E1 (86) | 68 | 69 | 77 | **73** (false alarms 101 per 1,000; P − Lung-RADS +5.8 points [0.0, +12.0]) |
| L3 | E2 (41) | 32 | 36 (32 fewer false alarms per 1,000 than P [16, 49]) | 37 | 36 |
| L3 | E4 (131) | 54 | 63 | 59 | 66 (P − Lung-RADS +9.2 points [+1.8, +16.8]) |
| R (radiologists' level) | E1 (86) | 81 | 82 (26 fewer false alarms per 1,000 than P [7, 46]) | 83 | 79 |
| R | E2 (41) | 39 | 39 (53 fewer per 1,000 than P [28, 78]) | 39 | 38 |
| R | E4 (131) | 78 | 86 | 100 | 96 |

**3. Does Sybil add to P? (weights fitted on dev; cross-fitted in brackets):** E1 +0.017 [−0.015, +0.048] (+0.020 [−0.005, +0.042]); E4 +0.011 [−0.026, +0.047] (+0.021 [−0.007, +0.048]). The call adds nothing to P (P + call within 0.004 of P everywhere).

**What X10 shows (exploratory):**
1. **A 14-item form that most screening programmes can fill ranks cancers as well as Sybil** on the NLST test split: equal at 1 year (0.914 vs 0.914), slightly above at 6 years (0.735 vs 0.724; intervals wide), and Sybil adds little to it.
2. **The full form's 1-year edge over Sybil comes from the 29 items P leaves out** (+0.034 [+0.011, +0.060]); at 6 years P keeps almost all of F's information (−0.008). Which of the dropped items matter was not tested.
3. **P beats the clinical rule at the same false alarms** (1 year: 73 vs 68 cancers; 6 years: 66 vs 54). Sybil raises fewer false alarms than P at the radiologists' sensitivity, most clearly on baseline screens (53 fewer per 1,000).
4. **For outside partners:** the honest expectation is "a simple record-based model about equals Sybil", not "beats Sybil". P is NLST-fitted; whether it transfers is untested until a partner runs it. The frozen file is what partners would receive.

## 3i. Plan X12: how common are overlapping reconstructions in modern chest CT? (EXPLORATORY; metadata only; 22 Nov)
- **Why:** the reviewer question "is overlapping reconstruction a 2002–2004 NLST relic?". Plan `2b88e20` (after Neon's assessment of the draft); first run `934e27d`; Neon's review of that run found coding errors of mine in the filters (log 22 Nov; for example "DOSE" removed real low-dose series and whole chest-abdomen-pelvis stacks counted as chest); corrected run `b7bae94`, committed before it was read. All numbers below are from the corrected run.
- **Data:** the public IDC index (v25.0.5), CT series only; no image, no outcome. Primary axial chest series in Sybil's thickness range (≤ 3 mm): 135,199 chest series after the attrition in the file (phantoms, analysis results, irregular volumes, scouts, MIPs, reformats, secondary and post-processing series, small matrices, coverage outside 150–450 mm removed). "Modern" = scanner models first sold in 2013 or later (dates are shifted by de-identification: 95% of StudyDates fall before 2006, so dates cannot be used), or collections acquired from 2015 on (COVID-19 collections and the Cancer Moonshot Biobank).

| Chest CT (≤ 3 mm), public IDC | Studies | Patients | Studies with a strongly overlapping series (ratio ≤ 0.65; the z-fix regime) | … moderate or strong (≤ 0.85) | … only overlapping series (≤ 0.65) | … both an overlapping (≤ 0.65) and a contiguous series |
|---|---|---|---|---|---|---|
| NLST (2002–2007) | 67,184 | 24,707 | 8.9% [8.6, 9.3] | 34.6% | 5.4% | 0.3% |
| Other collections (all eras) | 4,287 | 3,570 | 8.7% [7.8, 9.7] | 18.7% | 7.0% | 1.7% |
| Scanner models first sold 2013+ | 189 | 144 | **3.7% [0.6, 7.9]** | **19.0% [11.9, 26.2]** | 0.5% | 3.2% |
| Collections acquired 2015+ | 1,146 | 756 | **6.2% [4.3, 8.2]** | 12.3% | 1.3% | 4.8% |

- **Clustered by site and protocol:** in the 2015+ collections the strong-overlap share ranges from 0% (most collections) to 32% (`covid_19_ar`, 19 patients); the Mayo low-dose CT collection (2016–2020, 50 patients) has every series moderately overlapping (≤ 0.85) and none at ≤ 0.65. The strongly overlapping modern series are ratio-0.5 protocols (2.0/1.0, 2.5/1.25, 3.0/1.5 mm) on current Siemens and GE scanners; the moderate ones are mostly 1.0/0.75, 1.0/0.8, 1.25/1.0 and 3.0/2.0 mm. Interval lower bounds are by patient and understate site-to-site variation.
- **Sensitivities:** including "SOMATOM Definition Edge" (launched 2012) gives 3.6% and 17.5%; ImageType ORIGINAL only gives the same numbers for the 2015+ collections.

**What X12 shows (exploratory):**
1. **Strong overlap (the regime the frozen tests measured) is uncommon in public modern chest CT**: about 4–6% of studies, against about 9% in NLST. It is not an NLST-only relic, but it must not be described as a large fixed share of modern CT.
2. **Moderate overlap (ratio 0.65 to 0.85) is common** (12–19% of modern studies; every series of the modern low-dose collection). **Update 23 Nov (X11, dev, exploratory; section 3j):** a stretch of 1.25 (ratio 0.8) moves axis 0 by +0.81 SD and the 1-year logit by +0.16 [0.07, 0.24]. What matters is how much padding remains in Sybil's box, not the ratio itself.
3. **Exposure depends on site protocol and on which series is sent to Sybil:** most modern studies with a strongly overlapping series also hold a contiguous one (3–5% of studies hold both), so the choice of series, or a change of that choice between yearly screens (H7), decides whether Sybil sees a stretched chest; Sybil gives no warning either way.
4. Current screening and nodule-volumetry guidance allows or recommends overlapping intervals: QIBA 2023 ("overlap of 50% may provide better accuracy and precision compared to contiguous slice reconstruction"), ACR–STR 2024 ("reconstruction intervals equal to or less than the slice thickness"), ESTI ("Slice Interval ≤ slice width … Overlapping reconstructions are not mandatory"). Checked word for word in the original documents on 22 Nov (task 6; `docs/LITERATURE_CHECK_2026-11-22.md` section 3).

## 3j. Plan X11: what shared axis 0 reads inside Sybil (EXPLORATORY; dev exams only; no outcome read; 23 Nov)
- **Why:** H6 showed on test that one shared direction of `pooled` (axis 0) carries the z-fix drop. On dev it was named "z-geometry" from correlations: lung cut at the box edge +0.98, real slices +0.93, stretch +0.79. Neon pointed out that these three move together, so the stretch could not be separated from how full Sybil's 200-slice box is. X11 changes the input on purpose to separate them.
- **How:** plan `2a624b5`, scoring amendment A1, analysis R1 (all before any estimate; Neon verified the script). 111 dev exams on the local CPU with the frozen job's own functions:
  - **Arm A:** 63 real overlapping scans (ratio ≤ 0.65; GE 24, Philips 27, Siemens 12; weighted to the dev maker mix).
  - **Arm B:** 48 contiguous scans (12 per maker: GE, Philips, Siemens, Toshiba) stretched on purpose.
  - Output committed before it was read (`ff52d5b`); all gates passed. Neon's review of the result: log 23 Nov.
- **Background:** Sybil fills the empty part of its 200-slice box with 0 after its normalisation. That is a uniform grey of about −600 HU, the centre of Sybil's lung window, not air (`cloud/image_measures.py` lines 3–5). A normal chest scan is shorter than the box (500 mm at 2.5 mm), so it is padded at both ends. An overlapping scan read with the wrong spacing is twice as long, so it fills the box.

| Pre-set criterion | Result (dev; mean [95% interval]) | Verdict |
|---|---|---|
| A1 padding value | z-fix with **air** instead of Sybil's padding (both runs): keeps **14.6% [14.0, 15.2]** of the axis-0 shift (−2.79 SD → −0.41); 1-year logit change −0.285 → **−0.038 [−0.168, +0.100]** | the padding value is a primary driver |
| A2 padding amount | box filling 97.8%; the stretch at equal filling **2.2% [1.9, 2.6]** | box filling drives |
| A3 constant slab | mirrored anatomy instead of padding removes **97.4%** | the constant slab drives it |
| A4 real non-overlapping series | every second slice of the same scans, **unmodified Sybil**: **1.003 [1.002, 1.003]** times the z-fix shift (36 exams; 1-year logit −0.276 vs −0.266 for the z-fix on the same exams) | the effect is reproduced with unmodified Sybil; the overlap itself does not matter |
| B1, B2 stretch dose | f = 1.25 / 1.5 / 2.0: axis 0 **+0.81 / +2.41 / +2.83 SD**, 1-year logit +0.16 / +0.39 / +0.39 [0.23, 0.54]; axis 0 and its logit part A0 rise in all four makers (the total logit not in Philips: +0.06 [−0.32, +0.43]) | met |
| B3, B4 | f = 2 at equal filling keeps 2.8%; f = 2.5 − f = 2.0 +0.08 SD (box already full) | box filling dominates; saturation |
| B5 | the true scan with air padding, no stretch: axis 0 **+2.41 SD**, 1-year logit **+0.245 [0.226, 0.265]** (+0.23 to +0.27 in each maker) | the padding value drives the stretch effect |

- **Where it sits:**
  - The z-fix shift lies in the max-pool part of `pooled` (−2.71 of −2.79 SD); the two attention parts give −0.08.
  - Sybil's slice attention puts 0.7% of its weight on padded slices.
- **Value-specific:** absolute axis 0 (dev SD) by what fills the box ends:
  - Sybil's padding −0.57;
  - air +1.85;
  - mirrored anatomy +2.14;
  - nothing (box full) +2.20.
  - So the axis reacts to a thick slab of Sybil's own −600 HU value. A slab of air, which looks like the air around every body, barely moves it.
- **Follow-up check (free; planned in `330e387`; output `0c497f0`, `results/x11/x11_padcurve_dev.json`):** axis 0 of all 7,336 dev main runs against the padded slices in Sybil's box. It follows **one curve, whatever the reason the slab is thin**:
  - padded slices > 64: about −0.6;
  - 49–64: −0.45;
  - 33–48: +0.28;
  - 25–32: +1.14;
  - 17–24: +1.64;
  - ≤ 16: +2.1 to +2.25.
  - In each bin the stretched, contiguous and other scans agree (for example 17–24: +1.63 and +1.64).
  - Ordinary contiguous NLST scans (270–363 mm, 5th–95th percentile) almost never reach the steep part: median 74 padded slices; only 0.2% have ≤ 32.
  - Among the 2,274 "other" dev scans (ratio 0.65–0.95 or > 1.05), 419 (18%) have ≤ 32 padded slices (bin means of axis 0 +1.1 to +2.2).

**What X11 shows (exploratory):**
1. **Axis 0 is a padding axis.** It reads whether Sybil's 200-slice box holds a thick slab of Sybil's own padding value, mostly through max pooling. It does not read the anatomical stretch. The frozen name "z-geometry" (H6) is kept only when the protocol is quoted.
2. **The test-confirmed results stand, and the mechanism is now concrete.** Misreading the spacing of an overlapping scan doubles its length in Sybil's eyes, fills the box and removes the padding slab. Axis 0 rises by about 2.8 SD and the 1-year logit by about 0.4. Reading the true spacing returns these scans to the axis-0 range of contiguous scans (−0.57 vs −0.58).
3. **Unmodified Sybil gives two reconstructions of the same scan different scores** (A4): the every-second-slice series reproduces the z-fix change.
4. **Sybil's score depends on a preprocessing constant.** On contiguous scans, air instead of Sybil's padding raises the 1-year logit by 0.245 with no stretch at all. This is an intervention on the model's input, so it is causal for the score. It says nothing about accuracy: Sybil was trained with this padding.
5. **Moderate overlap (X12: common in modern CT) also moves the axis when it thins the slab enough.** Stretch 1.25 (ratio 0.8): axis 0 +0.81, 1-year logit +0.16 [0.07, 0.24]. What matters is the padding left in the box, not the ratio itself.

**Cannot say (X11):**
- that air padding fixes Sybil. With air on both sides the exam-by-exam scatter stays: the 6-year logit moves ≥ 1/4 SD in 73.5% vs 76.0%. Air also moves ordinary scans out of their axis-0 range;
- that Sybil's padding lowers accuracy (no outcome read);
- that long scans such as chest–abdomen–pelvis behave the same (not tested; the curve only suggests it);
- that the logit rose in every maker (axis 0 and A0 did);
- anything from the pad-matched logits (+0.55, −0.42, +0.53): pad-matching also cuts off about half of the lung.
- **Not used:** `estimates.B.f20_air` (its reference is the Sybil-padded scan, so it equals `f20`).
- **Decisions:**
  - no air-padding arm in O2 (29 one-year cancers cannot test discrimination; it would need a second amendment of the frozen O2 files);
  - the NLST test split is not used again for these questions.

## 4. What the results allow us to say, and what not (run rule 4)
**Can say (test, frozen, Holm):**
- Sybil's output depends on its slice-spacing step: in about 1 test exam in 9 the chest is stretched along z (759 of 6,715); giving Sybil the true spacing lowers its 1-year logit by 0.37 on average and moves 66% of these exams by at least a quarter SD (H1, H2).
- The reconstruction kernel changes Sybil's alarm in fewer than 5% of exams (1.8%; H4).
- **Feature level (H6, allowed by amendment A6; outside the six dictionary arms of protocol 9.4):** one shared direction of Sybil's `pooled` layer, found on dev and frozen, carries at least 0.20 logit of the z-fix drop on test (in fact all of it: +0.41 against a drop of 0.37). The dictionary mark V1 does not apply, because H6 edits Sybil's real vector in one direction; the marks that apply hold for axis 0 (member agreement 0.995 on test).
- **Real follow-up (H7; observational; partly seen):** a change of reconstruction between yearly screens moves Sybil's score beyond the radiologist's findings (+0.31 logit), **mostly on GE scanners**, and the move goes through the same axis.
- Six hypotheses are about three findings: the z-fix (H1, H2, H6; H3 failed), the kernel (H4), real follow-up (H7).

**Cannot say:**
- "The z-fix changes many alarms" (H3 failed: 4.5%).
- "The spacing step harms patients" or "makes Sybil less accurate" (not shown; too few cancers; AUROC differences within noise).
- "Our feature improves Sybil" (switching axis 0 off changes AUROC by less than 0.002).
- "Air padding fixes Sybil" or "Sybil's padding lowers accuracy" (X11, section 3j: dev, exploratory, no outcome; with air the exam-level scatter stays).
- "This holds for all scanners" (H7 is a GE result; the z-fix itself holds on GE, Philips and Siemens).
- "Sybil equals the form": no large gap in either direction, with 86 and 131 cancers.

## 5. Extraction and checks (N4)
- Test list `results/manifest_test.csv` (SHA-256 `677ad548…`): 6,715 split-file series + 500 kernel partners; built after N3 from metadata and split names only.
- Cloud runs (`armanfo`: smoke 045, T1 047 + 048, T4 049 + 050; `forghanishayan`: smoke 046, T2 051 + 052, T3 053 + 054): **7,215 rows and 759 z-fix variants, 0 errors.** Smoke on both accounts: demo case equal to the published scores (0.0). Identity across accounts: all arrays equal (0.0).
- Gate (`results/s6/s6_checks_test.json`): 0 failures in every tier; z-fix 759 of 759; G2b and G2c on all 7,974 files; **identity with L1: 5,412 of 5,412 series within 1e-4** (largest 9.1e-7).
- **Cost:** S6 $19.27 as booked after the billing reconcile (measured $17.63, billed $19.15; `armanfo` $7.66, `forghanishayan` $11.61); allowed $22.30. Task `lung_l2_audit` $40.97 of $45; project $66.36 of $72.

## 6. Toward the paper (N7 draft; the lead and a clinical co-author judge)
**Working title:** "Auditing a deployed lung-screening AI at the feature level, with rules fixed in advance: a slice-spacing shortcut inside Sybil."

**Main messages (each with its test evidence):**
1. On its own held-out NLST test split, Sybil did not add information beyond what the trial radiologists recorded (L1 primary; L2 frozen secondary; section 2.1b), also when the radiologists' final call is removed from the comparator (section 3b, exploratory; work-up bias favours the radiologists' record at 1 year, so the later-cancer endpoints and section 3e carry this message); it does beat the coarse screening call and nodule size, the kind of comparator used in Sybil's own paper (**Correction, 21 Nov:** against nodule size only at 6 years, +0.071 [+0.026, +0.118]; at 1 year +0.014 [−0.023, +0.053], interval includes 0; section 3f). Its dev-tuned thresholds do not transfer (a rule-out cut lost 27% of cancers). **Scope (X8, 21 Nov, exploratory; section 3f):** against published rules that we did not fit (Lung-RADS, Brock, built from the NLST records), Sybil is about equal at 1 year and better at 6 years, and it adds to Lung-RADS; so "no added value" holds against the full record combined by a model fitted on NLST, not against the coarse clinical rule. **Correction, 22 Nov (X9, section 3g):** with the corrected rules Sybil is about equal to Lung-RADS and Brock at 1 year; at 6 years it beats Lung-RADS (+0.085) but not clearly Brock; it adds to Lung-RADS (+0.05 at 1 year, +0.06 at 6 years, not +0.06 and +0.08). "No added value beyond the form" means no meaningful gain in AUROC or net benefit; Sybil does carry a small, statistically detectable extra signal (coefficient 0.44 [0.27, 0.64], section 3b). At the same false alarms the form catches more 1-year cancers (77 vs 69 of 86); on baseline screens Sybil gives fewer false alarms at the same sensitivity. *Lesson: a development split used for tuning, and a categorical comparator, both give a misleading picture of an AI's added value.*
2. A preprocessing step of Sybil (slices placed at the slice thickness, not the true spacing) stretches the chest in about 1 exam in 9; correcting it lowers the score in a large majority of these exams (H1, H2). The alarm changes less than predicted (H3 failed: 4.5%).
3. The effect is localised: one direction shared by all five ensemble members (axis 0; frozen name "z-geometry axis") carries the whole average change, on new scans (H6), and the same axis carries the score jump in real yearly screening when the reconstruction changes (H7, mostly GE). **Mechanism (X11, dev, exploratory; section 3j):** axis 0 is a padding axis. Sybil's max pooling registers whether a thick slab of its own −600 HU padding is in the 200-slice box, and its risk head adds about 0.4 logit when the slab is missing. Misreading the spacing fills the box. Unmodified Sybil on a true non-overlapping series of the same scan reproduces the z-fix. *Lesson for any 3D model with a fixed input box: a constant pad value read by global max pooling becomes a hidden input.*
4. The kernel matters little (H4). On dev, the sparse dictionaries gave no valid and useful features (the SAE failed the validity marks; NMF at `pooled` passed them but rebuilt the vector worse than the dev mean; S4 and step R): Sybil's last layers are close to one risk dial plus a few shared technical axes.
5. What we did not find: no harm shown (too few cancers), no improvement from any feature-level edit.

**Figures:** drafts made from the committed result files only (`s6_figures.py`, plain SVG, validated colours): `results/s6/figures/fig1_hypotheses.svg` (the six hypotheses, dev and test, nulls, Holm result), `fig2_axis0.svg` (z-fix drop as is and with axis 0 off, dev and test; real follow-up group means with and without axis 0), `fig3_auroc.svg` (Sybil, form, form + image on dev and test). Still to make: study flow (dev discovery → freeze → test once); per-exam z-fix change; H7 by maker; attention near the nodule.

**Target journal (my suggestion, the lead decides):** *Radiology: Artificial Intelligence* (audit of a public imaging AI, pre-registered hypotheses, NLST; fits its "model evaluation" papers). Stronger alternatives if a clinical co-author and an outside dataset join: *The Lancet Digital Health* or *npj Digital Medicine* (they value independent audits of deployed models; an outside dataset, step N9a, would raise the chance a lot). Reasons: the main finding is a mechanism inside a widely used open model, shown with frozen hypotheses on held-out data, plus a clear negative (dev flatters, no gain over recorded findings).

**Before submission (N8):** TRIPOD+AI and CLAIM checklists; the hash table and the frozen files in the supplement; a second person re-runs `s6_frozen_analysis.py` from the repository; tell Sybil's authors about the spacing step (N9c).

## 7. Files
- Primary: `results/s6/s6_test.json`, `results/s6/s6_test_h7_no_cancer_sensitivity.json`, `results/s6/s6_test_stdout.txt`.
- Checks: `results/s6/s6_checks_test.json`, `s6_input_checks_pre.json`, `s6_input_checks_post.json`, `assemble_test.json`, `s6_merge_armanfo.json`, `s6_merge_forghanishayan.json`, `results/s6_identity_accounts.json`, `results/s6_manifest_test.json`.
- Secondary and exploratory: `results/s6/s6_attention_test.json`, `results/s6/s6_explore_test.json`.
- Scripts used at S6: `s6_manifest_test.py`, `s6_identity_accounts.py`, `s6_merge_test.py`, `s6_checks_test.py`, `l2_data.py`, `s6_input_checks.py`, `s6_frozen_analysis.py`, `s6_attention.py`, `s6_explore_test.py`; cloud: `cloud/l2_sybil_modal.py`, `cloud/drive_runs.py`, `cloud/drive_plan.py`, `cloud/run_s6.cmd`, `cloud/wait_idle.py`.
