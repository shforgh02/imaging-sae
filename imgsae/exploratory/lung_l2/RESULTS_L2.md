# Lung L2: results on the test split (S6, steps N4 to N6)

- **Written:** 2026-11-18, early morning (UTC), by the executing session (Opus 5.5), after the lead's OK of the freeze `c3578c3` (N3, 17 Nov) and the lead's go for N4 ("start N4 … do your job, fix error … make best decision and continue").
- **Frozen analysis output:** `results/s6/s6_test.json` (SHA-256 `e51c2308d5dd1f8d8e868c40573bdb28f15d47e706cb87b40071973d9290f793`), **run once and committed before it was read** (commit `1c93259`). Everything in sections 1 and 2 comes from that file.
- **Rules:** `HYPOTHESES_L2.md` (frozen family of six, Holm, one-sided, α = 0.05), protocol sections 10 and 11, the four run rules of N3 (`docs/EXECUTION_LOG.md`, entry "step N3 done").
- **Dev vs test:** dev is Sybil's own development split (it was used to build and tune Sybil, so it flatters Sybil; caution C6). Test is Sybil's held-out test split, opened once.
- **Population:** 6,715 test exams (one series per exam, the series of Sybil's split file), 2,347 participants; 86 cancers within 1 year (all screens), 131 cancers within 6 years (baseline screens). Z-fix population T5: 759 exams, 342 participants, 9 one-year cancers. Kernel pairs T4: 500 pairs, 500 participants.

## 0. In simple words
1. **Five of the six frozen predictions came true on new data. One failed (H3).**
2. **The slice-spacing problem is real on the test scans.** When we give Sybil the true slice spacing, its score falls (H2), and two scans in three move by a clear amount (H1). The kernel hardly matters for the alarm (H4).
3. **We found where the problem sits inside Sybil, and it held on new scans (H6).** One shared direction ("axis 0", the z-geometry axis) in Sybil's `pooled` layer carries the whole average drop. Switch that one direction off, and the z-fix drop goes from −0.37 to +0.04. This is the feature-level result of the project.
4. **The same thing happens in real screening, without any intervention by us (H7).** When a person's yearly scan changes between stretched and not stretched, Sybil's score jumps, beyond what the radiologist's findings explain. With axis 0 switched off, the jump is gone. **But almost all of it comes from GE scanners** (121 of 134 changed pairs).
5. **H3 failed.** We predicted that the z-fix changes the alarm in more than 5% of exams. On test it was 4.5% [2.9%, 6.3%]. The z-fix mostly *removed* alarms on test (27 lost, 7 gained), unlike dev (38 lost, 31 gained).
6. **Dev flattered Sybil a lot.** On dev, Sybil looked much better than the radiologists' recorded findings. On test it is not better: 1-year AUROC 0.914 (Sybil) against 0.947 (the form built from everything the radiologist recorded, including the screening call; section 2.1b), and adding Sybil to the form plus image measures adds nothing (−0.004 [−0.029, +0.020]).
7. **Harm was not shown, and could not be shown.** Of the 9 one-year cancers in the stretched exams, the main and the z-fix run catch the same 7. "No difference" here does not mean "no harm" (too few cancers, as stated before the test).

## 1. The six frozen hypotheses on test (primary; Holm over six)
| | Statement | Null (direction) | Dev | **Test** [95% CI] | One-sided p | **Holm** | Test counts |
|---|---|---|---|---|---|---|---|
| H1 | the z-fix moves the score materially (share with \|Δℓ̄_6\| ≥ 0.25 dev SD) | > 0.30 | 0.670 | **0.657 [0.620, 0.695]** | 7e-80 | **confirmed** | 759 exams, 342 participants, 9 one-year cancers |
| H2 | the z-fix lowers the score (mean Δℓ̄_1) | < −0.10 | −0.326 | **−0.367 [−0.411, −0.320]** | 1e-29 | **confirmed** | same |
| H3 | the z-fix changes the screening flag (share of exams) | > 0.05 | 0.075 | **0.045 [0.029, 0.063]** | 0.73 | **not confirmed (failed)** | same |
| H4 | the kernel changes the flag in fewer than 5% of exams | < 0.05 | 0.018 | **0.018 [0.008, 0.030]** | 3e-8 | **confirmed** | 500 pairs, 500 participants |
| H6 | shared axis 0 of `pooled` carries the z-fix drop (Δℓ̄_1 with axis 0 off minus Δℓ̄_1) | > +0.20 | +0.408 | **+0.407 [0.401, 0.411]**; halves 0.407 / 0.406 | < 1e-15 | **confirmed** | 759 exams, 342 participants |
| H7 | in real follow-up, the score jumps with a change of stretch status (OLS b, adjusted for ΔF1) — **partly seen** | > +0.10 | +0.246 | **+0.311 [0.185, 0.435]**; halves 0.419 / 0.226 | 0.0004 | **confirmed** | 4,353 pairs, 2,224 participants, 134 changed (92 stretched → not, 42 not → stretched) |

- **5 of 6 confirmed.** Holm order: H6, H1, H2, H4 (each p far below its level), H7 (p 0.0004 against α/2 = 0.025), H3 (p 0.73 against 0.05: not rejected).
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
1. On its own held-out NLST test split, Sybil did not add information beyond what the trial radiologists recorded, including their screening call (L1 primary; L2 frozen secondary; section 2.1b for what the form contains and the work-up bias of the 1-year comparison), although our dev data suggested a large gain. *Lesson: a development split used for tuning gives a misleading picture.*
2. A preprocessing step of Sybil (slices placed at the slice thickness, not the true spacing) stretches the chest in about 1 exam in 9; correcting it lowers the score in a large majority of these exams (H1, H2). The alarm changes less than predicted (H3 failed: 4.5%).
3. The effect is localised: one direction shared by all five ensemble members ("z-geometry axis") carries the whole average change, on new scans (H6), and the same axis carries the score jump in real yearly screening when the reconstruction changes (H7, mostly GE).
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
