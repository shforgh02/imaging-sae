# Lung L2: frozen hypotheses for the test split (S5, second freeze)

- **Status:** SECOND FREEZE on 2026-11-17 (step N1) by the executing session (Opus 5.5). It replaces the first freeze (commit `c593005`, 2026-11-16). **Waiting for the re-check by a fresh session (step N2, `docs/PROMPT_REVIEW_S5b.md`) and the lead's OK (step N3).** No test activation, test image measure or test variant has been extracted; no new analysis of the L1 test scores has been made; the test manifest has not been built (`s6_manifest_test.py` was run on dev only).
- **Rules:** `docs/LUNG_L2_PROTOCOL.md` section 10 (hypothesis freeze) and section 11 (test confirmation), amendments A1 to A6 (section 16a). Amendment A6 (2026-11-17) allows the extra dev work of steps R to R3 and the two hypotheses H6 and H7 that came from it.
- **Dev evidence:** `RESULTS_S4_dev.md` and `results/s4/` (S4 code fixed at `a536192` before any full-dev run); `RESULTS_R_dev.md` and `results/r/` (step R, reviewer session; rerun and checked by the executor in step F, 0 differences); `results/s5/s5_h5prime_dev.json` (H5′).
- **Frozen files:** `results/s5/` (thresholds, dictionary, family labels, F+I parameters, secondary combinations, **shared axes of `pooled`**), written by `s5_freeze.py` and `s5_axes_freeze.py`. **Frozen analysis:** `s6_frozen_analysis.py` (reads only the frozen files; refits nothing; refuses to run if a frozen file or Sybil's head weights or calibrator changed) and, for one descriptive item, `s6_attention.py`. **Test list:** `s6_manifest_test.py` (tested on dev; it refuses to build the test list without the lead's OK).
- **Dev as if test** (`results/s5/s6_dev_as_if_test.json`): H1 to H4 equal the first freeze exactly (estimates, intervals, p-values, counts); H6 and H7 equal step R to 10 digits; the secondary references equal the first freeze.
- **Participants:** 2,493 dev participants in Sybil's split file, 2,492 with a usable exam. Dev: 7,336 exams.

## The family: six hypotheses
**Holm correction, family-wise α = 0.05, one-sided in the stated direction.** Each statistic: participant bootstrap (2,000 draws, seed 0) for the 95% interval; one-sided p from the Wald statistic (estimate − null) / SD of the bootstrap draws; if that SD is 0, p = 0 when the estimate is on the stated side of the null, else p = 1 (review change 3). A hypothesis is confirmed if Holm rejects its null. A hypothesis that cannot be evaluated keeps its place in the family (m = 6) and counts as not confirmed.

Each hypothesis uses a quantity never computed on test: a z-fix change (H1, H2, H3, H6), a kernel-pair change (H4), a shared axis of Sybil's `pooled` layer (H6), or Sybil's member logits of consecutive screens (H7). **H7 is labelled "partly seen"** (protocol 10; the only one in the family): an approximate version could be computed from the L1 test scores (logit of the published score instead of the member logits), the form and the public scan metadata. Nobody computed it: no L1 script reads spacing, thickness or stretch, and the L1 test scores have not been analysed since L1. L1 post hoc saw only the overall correlation of the test logits between a participant's T0 and T1 (r = 0.61), not split by stretch.

Frozen values (`results/s5/frozen_thresholds_L2.json`): τ90 = 0.017993675 (90th percentile of the published 1-year score s1 among dev exams with y1 = 0, all screens); SD reference of ℓ̄_6 = 0.92957453 (all 7,336 dev main exams); z-fix population = spacing/thickness ≤ 0.65; τ90 of s6 = 0.12394902 (90th percentile of s6 among dev baseline exams with y6 = 0; harm estimates only); shared axes: `frozen_axes_pooled.npz` (11 axes of layer `pooled`, 30 PCs per member; dev SD of axis 0 = 0.998124).

Notation: ℓ̄_t = mean of the five member logits for year t; s1 = Sybil's published (calibrated) 1-year score; flag = s1 ≥ τ90; Δ = z-fix minus main (H1 to H3, H6), sharp minus soft (H4), later minus earlier screen (H7).

| | Statistic | Population (test) | Direction, null (= margin) | Dev estimate [95% CI]; halves | Dev counts | Chance on test (mine) |
|---|---|---|---|---|---|---|
| **H1** z-fix moves the score materially | share of exams with \|Δℓ̄_6\| ≥ 0.25 × 0.92957 | T5: z-fix variants of T1 to T3 main series with spacing/thickness ≤ 0.65 | > 0.30 | 0.670 [0.638, 0.701]; 0.669 / 0.671 | 924 exams, 424 participants, 16 one-year cancers | 0.98 |
| **H2** z-fix lowers the score | mean of Δℓ̄_1 | T5 | < −0.10 | −0.326 [−0.366, −0.282]; −0.320 / −0.332 | same | 0.97 |
| **H3** z-fix changes the screening flag, in both directions | share of exams whose flag differs between main and z-fix | T5 | > 0.05 | 0.0747 [0.0558, 0.0971]; 0.0741 / 0.0753 (flags 112 → 105: 38 lost, 31 gained) | same | 0.55 |
| **H4** the kernel changes the flag in fewer than 5% of exams | share of sharp/soft pairs whose flag differs | T4: 500 soft-kernel partners of T1 exams and their main series | < 0.05 | 0.018 [0.008, 0.030]; 0.028 / 0.008 (flags 64 and 61: 6 lost, 3 gained) | 500 pairs, 500 participants | 0.92 |
| **H6** the shared z-geometry axis carries the z-fix drop | mean of [Δℓ̄_1 with shared axis 0 of `pooled` set to its dev mean in every member] − [Δℓ̄_1 as Sybil gives it] | T5 | > +0.20 | +0.408 [0.403, 0.412]; 0.412 / 0.404 | 924 exams, 424 participants | 0.90 |
| **H7** in real follow-up the score jumps when a screen changes between stretched and not stretched (**partly seen**) | b in the OLS fit Δℓ̄_1 = a + b × Δstretched + c × ΔF1 over consecutive yearly screens | test participants with two consecutive yearly screens among the T1 to T3 main runs | > +0.10 | +0.246 [0.134, 0.355]; 0.222 / 0.272 | 4,837 pairs (215 changed), 2,441 participants | 0.65 |

Halves: the dev halves of H1 to H3 and of H5′ quoted here use the S4 convention (two participant folds drawn on the exams of the statistic); those of H6 and H7 use the step R convention (folds of all participants of the root, restricted). At S6 the frozen analysis reports the halves of H5′, H6 and H7 with the step R convention. Halves are reported, never tested.

## Each hypothesis in words, with its dev evidence and my reasons
### H1, H2, H3: Sybil's handling of slice spacing (protocol C2; U1b; Q1d ii) (unchanged from the first freeze, except the wording of H3)
- **What:** Sybil places slices at the DICOM slice thickness, not at their real spacing. Where the spacing is at most 0.65 of the thickness, the chest is stretched along z (1.5× to 2×). "z-fix" runs the same images with the true spacing.
- **Dev evidence** (`results/s4/s4_q1d_dev.json`, section `zfix.D5`; 924 dev exams from all three screening rounds, 424 participants): H1 0.670 (protocol U1b qualification: ≥ 30%); H2 −0.326 logits (0.32 of the between-exam SD of ℓ̄_1); H3 0.075. The same in both stretch classes (1.6: 333 exams, mean −0.28, share 0.60, flag change 0.072; 2.0: 591 exams, −0.35, 0.71, 0.076) and with or without a lung cut by the crop.
- **The flag changes in both directions (review comment 2):** 112 exams flagged in the main run, 105 in the z-fix run; 38 flags lost and 31 gained; of the 143 exams flagged in either run, 48% are flagged in one run only. The z-fix **reshuffles** the alarms; it does not simply remove them.
- **Chances:** H1 and H2 test a mechanical property of Sybil and of the scan geometry; the test series come from the same trial, scanners and protocols (about 743 test series with spacing/thickness ≤ 0.65 expected, protocol section 7): 0.98 and 0.97. H3 is the weakest: the dev lower bound (0.056) is close to the null 0.05, test has fewer such exams (about 743 against 924), and the flag depends on where these scores fall around τ90. The first freeze stated 0.60. With six hypotheses, if H7 fails before H3 in the Holm order, H3 is tested at a stricter level; so I now state **0.55**.
- **Margins:** H1's margin is the protocol's (U1b). H2's margin (−0.10) and H3's margin (0.05) were set at S5 from dev. **Disclosure:** in the S4 gate list (written before the full-dev run), the flag-change statistic had the U1b margin 0.10 and **failed** it (0.075). H3 uses a lower margin chosen after seeing dev.
- **Population detail:** 8 dev exams have a recorded ratio of 0 (each slice position recorded twice) and no z-fix row; they are not in T5. The same rule applies on test.

### H4: the reconstruction kernel changes Sybil's flag in fewer than 5% of exams (Q1d i) (renamed; statistic unchanged)
- **What:** the same acquisition reconstructed with a sharp and a soft kernel. Simon et al. (*Invest Radiol* 2025) found no AUROC difference between kernels; the within-exam effect on Sybil's decision is not published.
- **Dev evidence** (`results/s4/s4_q1d_dev.json`, section `kernel_pairs`; 500 pairs, 500 participants, 8 one-year cancers): flag change 0.018; flagged 64 (sharp) and 61 (soft), 9 differ (6 lost, 3 gained); of the 67 flagged in either, 13% differ, so about one flagged exam in seven changes; sharp minus soft ℓ̄_1 +0.028 [0.009, 0.049]; SD of the change 0.21 of the between-exam SD; ICC 0.98. The old name "rarely" was too strong (review change 2).
- **Chance 0.92:** test pairs are drawn the same way (`s6_manifest_test.py`: the pair rule and quota of `s1_manifest.py`, seed 0; on dev it reproduces all 500 D4 pairs of `manifest_dev.csv` and the whole file byte for byte). The null 0.05 is more than five standard errors above the dev value.
- **Disclosure:** the S4 gate list had this statistic with the opposite direction ("the kernel changes the flag in more than 10%"), which **failed**. H4 is the robustness statement the dev data support, chosen at S5. In 1.1% of test exams the split file's series is not the series the dev rule would pick, so a T1 main series can be soft and its partner sharp; the flag statistic does not depend on which one is sharp.

### H6: one shared axis of Sybil's `pooled` layer carries the z-fix drop (step R, candidate C2; feature-level)
- **What:** in the layer `pooled` (1,536 numbers per member, one layer before `h`) the five separately trained Sybil members share 11 directions ("shared axes", multiset CCA; held-out agreement 0.995 down to 0.71 in both halves; shuffle null 0). Axis 0 is named "z-geometry" from its correlations (lung cut in z +0.98, number of real slices +0.93, z-stretch +0.79), and the name is confirmed by intervention: the z-fix moves it by −2.74 SD [−2.77, −2.71], the kernel change by +0.01 SD. H6 says that this one axis carries the systematic part of the z-fix change of the score.
- **Statistic, exactly:** for each T5 exam, compute ℓ̄_1 of the main run and of the z-fix run from their saved `pooled` vectors through Sybil's own `hidden_fc`, ReLU and head (heads.npz), once as they are and once with axis 0 set to its dev mean in every member (an orthogonal projection in each member's whitened 30-PC space; only that one direction of each member's vector changes). H6 = mean over exams of (Δℓ̄_1 with axis 0 off) − (Δℓ̄_1 as is). Frozen dev axis (`frozen_axes_pooled.npz`), no refit, no outcome.
- **Dev evidence** (`results/r/r6_candidate_pooled.json`, reproduced by `s6_frozen_analysis.py` on dev): +0.408 [0.403, 0.412], halves 0.412 / 0.404 (924 exams, 424 participants). With axis 0 off, the mean z-fix change of ℓ̄_1 goes from −0.326 to +0.081 [0.042, 0.125]; AUROC on dev 0.9685 → 0.9699 (1 year), 0.8509 → 0.8496 (6 years).
- **The four conditions of amendment A6 (evidence from `RESULTS_R_dev.md` section 6):**
  1. Gate 9.8: estimate, interval and both halves above +0.20. **Holds.**
  2. Random-choice test: 2,000 random axes (one random unit direction in each member's whitened 30-PC space, every direction with unit dev variance): 1 of 2,000 passes +0.20 (0.05%); largest 0.226; middle 95% −0.079 to +0.103. **Holds** (below 5%).
  3. No refit on test: needs only `pooled` of the main and the z-fix runs (S6 saves both, as on dev), the frozen axes and Sybil's heads. **Holds.**
  4. Honest chance: **0.90**. The effect is physical and outcome-free, and the null is half the dev value. The main risk is that the test scanners differ so that the frozen axis fits less well; the secondary number "agreement of the five members on each frozen axis in test" will show it.
- **Limits, said plainly:** the axis removes the average drop, not the exam-by-exam scatter (share of exams moving ≥ 0.25 SD: 0.670 → 0.550). The 11 axes are readings, not a full dictionary (the score rebuilt from them alone: r 0.95, below the 0.98 mark). It is not a repair of Sybil and not a clinical result. The axis was found by the reviewer session in exploratory dev work; the hypothesis was chosen after its z-fix result was seen (disclosed below).

### H7: the slice-spacing effect in real repeated screening (step R2, candidate C3; outcome-free; partly seen)
- **What:** the z-fix is our own experiment. In real screening a person is scanned every year, and sometimes the reconstruction changes between years (stretched one year, not the next). H7 says that Sybil's 1-year score jumps when that happens, beyond what the radiologist's recorded findings explain.
- **Statistic, exactly:** pairs of consecutive yearly screens of one participant (T0→T1 and T1→T2; main runs only). Δ = later minus earlier. stretched = 1 if spacing/thickness ≤ 0.65 as recorded in the series geometry (a recorded ratio of 0, meaning duplicated slice positions, counts as stretched, as on dev), else 0. OLS: Δℓ̄_1 = a + b × Δstretched + c × ΔF1, where ℓ̄_1 is the mean member logit of the main run and F1 the frozen form model's 1-year logit (`results/l2_form_params.json`). Statistic b; participant bootstrap (a participant can give two pairs). No outcome, no refit.
- **Dev evidence** (`results/r/r7_more_pooled.json`, reproduced): b = +0.246 [0.134, 0.355], halves 0.222 / 0.272; 4,837 pairs, 2,441 participants, 215 pairs change stretch status (146 stretched → not, 69 not → stretched). Group means of Δℓ̄_1: stretched → not −0.17; unchanged +0.04; not → stretched +0.22. With axis 0 off: b = −0.094 [−0.208, 0.014]; axis 0 itself jumps 2.29 SD per stretch change.
- **The four conditions of amendment A6 (`RESULTS_R_dev.md` section 9A):**
  1. Gate 9.8: estimate, interval and both halves above +0.10. **Holds.**
  2. Permutation test (in place of the random-choice test, because the claim is about a metadata group, not a feature): 2,000 shuffles of the stretch change give b above +0.10 in 2.5% (largest 0.15). **Holds**, but not by much.
  3. No refit on test: main runs, metadata and the frozen form model; the axis-0-off secondary needs the frozen axes. **Holds.**
  4. Honest chance: **0.65** (the reviewer said about 0.7). The dev lower bound (0.134) is close to the null, the test will have a similar number of changed pairs, and an effect chosen after seeing dev tends to be smaller on new data.
- **Edge case found in step F:** 8 dev exams have a recorded ratio of 0 (each slice position twice; 6 of them are physically stretched in Sybil's box, 2 are small partial scans). They count as stretched, as the dev evidence did. With them counted as not stretched, dev b = +0.227 [0.115, 0.336] (gate still holds). This second count is a frozen secondary number.
- **Limits:** observational. A change of reconstruction can come with other changes (scanner, protocol, site); the same-scanner-model subset agrees but is small (56 changed pairs; +0.216 [−0.057, 0.471]). The form term adjusts only for what the radiologist recorded.

## What the z-fix does and does not show: sensitivity, not harm (review comment 3)
- H1 to H3 and H6 show that Sybil's output depends on how slice spacing is handled. They do **not** show that the published handling makes Sybil worse for patients.
- Dev, in the 924 z-fix exams: AUROC of s1 for 1-year cancer 0.994 (main) and 0.984 (z-fix); the fix does not raise it. Among exams without cancer, stretched exams are flagged as often (10.6%, 906 exams) as exams without stretch (10.4% [9.1%, 11.7%], 4,079 exams). Sybil-only false alarms (Sybil flags, the form does not) in the 906 stretched exams without cancer: 80 → 75 under the z-fix (31 lost, 26 new): a reshuffle, not a reduction. 1-year cancers in the z-fix exams: 16, all 16 flagged by the main run, 15 by the z-fix run.
- The word "error" in any report needs this limit. The paper says "sensitivity to slice spacing", not "harm".

## Changes after the first freeze `c593005` (what, why, who)
| Change | Why | Proposed by | Chosen from |
|---|---|---|---|
| **H5 removed from the family** (now a secondary number) | As frozen it could not fail: any 6 of the 56 families pass its test (review: 100% of 20,000 random sets above 0.03) | the external reviewer (`docs/REVIEW_S5_L2.md`) | dev |
| **H5′ not frozen as a hypothesis** (secondary number) | The reviewer's replacement reproduces on dev (−0.0566 [−0.0590, −0.0541]; halves −0.0565 / −0.0567), but its random-choice test failed: 59.7% of 20,000 random sets of 6 of the 56 families also fall below −0.02 (12.6% fall at least as much); the "mixed" families move more per family (−0.0123) than the T families (−0.0094); only the N families stay still (+0.0002). | the reviewer proposed H5′; the executor ran the random-choice test asked by the lead's prompt; **the lead chose "Move H5′ to secondary" on 2026-11-17** | dev |
| **H6 added** (candidate C2) | Feature-level hypothesis that passes the gate and the random-choice test | step R, by the reviewer session of the first freeze (Fable 5.2), on the lead's instruction; amendment A6 | dev, exploratory work after the first freeze |
| **H7 added** (candidate C3) | Outcome-free evidence of the same effect without our intervention | step R2, same session; amendment A6 | dev, exploratory work after the first freeze |
| H4 renamed; H3 worded with both flag directions; flag numbers in both directions added to the secondary list | review change 2 | reviewer | — |
| `wald()`: p = 0 / 1 when the bootstrap SD is 0 | review change 3 (H4 could count as not confirmed although fully supported) | reviewer | — |
| Test-list script `s6_manifest_test.py` written and hashed | review change 4 (it defines the 500 pairs of H4) | reviewer | dev check only |
| LF hashes of the three text inputs in `frozen_thresholds_L2.json` | review change 5 | reviewer | — |
| New secondary items: harm estimates, attention check, H6 and H7 details, term changes, old H5 | the lead's questions of 17 Nov; step R | lead, reviewer | — |
| S6 on two accounts in November | the lead's money decision of 17 Nov | lead | — |

**Steps of the exploratory work that were added after seeing results** (each logged before it ran; `RESULTS_R_dev.md` plan table; `docs/EXECUTION_LOG.md` 16 and 17 Nov): R1b joint dictionary (after R1 on `h`); R6 repair test and random-choice test (after R5 showed the axis-0 shift); R7 gate numbers for C1 and C2 (after R6); `pooled` with K = 24 and 32 (after K = 16); step R2 (A to D, after the lead's question); R3 and R3b attention (descriptive). The plan and code commits of step R are `68f4637` and `52b5e83`. **The reviewer of the first freeze did this work.** The executor (Opus 5.5) reran all step R scripts behind H6 and H7 (0 differences) and read the code as an outsider (no error; one edge case, H7 above). The re-check of this freeze must be done by a session that did not do step R.

## Considered and not frozen (with reasons)
- **H5** (first freeze) and **H5′**: near-automatic (above). Both reported as secondary numbers.
- **C1** "the z-fix moves axis 0 by more than 2 SD" (dev −2.740 [−2.765, −2.714]; 0 of 2,000 random axes pass): true but says less than H6; secondary.
- **U1a technical removal** (`s4_u1a_dev.json`): point values qualify, but the bootstrap interval of the spread ratio is [0.34, 1.36] and the halves disagree (1.43, 0.63): gate 9.8 **failed**.
- **U3 Sybil + form at the radiologists' sensitivity** (partly seen): ratio 0.70 [0.35, 1.05]: gate 9.8 **failed**.
- **"U adds to F" and "Sybil adds to F+I"** (dev +0.04 to +0.10): on test, L1 already found that Sybil adds almost nothing to the recorded findings; close to partly seen; chance 0.15 to 0.25. Secondary references.
- **Harm hypotheses** (false alarms or misses in stretched exams; step R2 B): no harm signal on dev; misses cannot be tested with about 12 stretched 1-year cancers in test. Pre-stated harm **estimates** instead (below).
- **Technical axes carry Sybil's disagreement with the form** (step R2 D): 33% of random sets of 5 directions do as well: near-automatic.
- **NMF at `pooled`** (valid on the four marks, but its rebuilt vector is worse than the dev mean: R² −2.8) and **axes of 3 of 5 members** (weak technical leftovers): exploratory only.
- **Q2 variables, family SMDs, Q1c, U2, kernel mean shift, Q1a technical share:** as in the first freeze (small, confounded or near-automatic).

## Secondary items at S6 (outside the Holm family; never called confirmed)
From `frozen_thresholds_L2.json` → `secondary` (computed by `s6_frozen_analysis.py`, dev values in `results/s5/s6_dev_as_if_test.json`):
1. The references of the first freeze: AUROC of Sybil, F, R-size, F+I; the frozen A3 combination; the frozen U3 table; z-fix and kernel descriptives; group shares.
2. **Flags in both directions**, z-fix (dev: 112 → 105; 38 lost, 31 gained; 48% of 143 discordant) and kernel (64 and 61; 6 lost, 3 gained; 13% of 67).
3. **Term changes under the z-fix** (dev, ℓ̄_1): T −0.057, N +0.005, mixed −0.197, unreplicated +0.023, residual −0.101; parts of the mean shift 17%, −2%, 60%, −7%, 31%. **H5′ is this T number** (with its failed random-choice test).
4. **Old H5:** share of Var(ℓ̄_1) carried by the T families (dev 0.0505).
5. **H6 details:** C1 (dev −2.740 SD; null −2.0 stated, not tested); for each of the 11 frozen axes the agreement of the five members (dev: all 11 ≥ 0.70, from 0.995 to 0.747), the z-fix change and the kernel change in dev SD units; share of exams moving ≥ 0.25 SD with axis 0 off (dev 0.550 [0.512, 0.588]); AUROC with axis 0 off (dev 0.9699 / 0.8496; caution C6, dev flatters Sybil).
6. **H7 details:** b with axis 0 off (dev −0.094); axis-0 jump per stretch change (dev 2.29 SD); same scanner model (dev +0.216); group means and flag flips by group (dev flips 12.3%, 9.2%, 10.1%); b with ratio 0 counted as not stretched (dev +0.227); "both screens without cancer within 1 year" (uses outcomes; written to a separate file after the primary result is saved; dev +0.279 [0.171, 0.380]).
7. **Harm estimates in T5** (the lead's question of 17 Nov; pre-stated here, before the test):
   - Sensitivity at τ90 (1-year cancers, all screens) and at τ90 of s6 (6-year cancers, baseline screens), main and z-fix run, exact intervals; the paired counts (caught by one run only); a bootstrap interval of the paired difference; AUROC of s_t for both runs and the paired difference.
   - Dev: 1 year, 922 exams, 16 cancers: main 16 of 16 (1.00 [0.79, 1.00]), z-fix 15 of 16 (0.94 [0.70, 1.00]); 1 cancer caught by the main run only, 0 by the z-fix run only; AUROC 0.994 and 0.984 (difference −0.011 [−0.028, +0.000]). 6 years, baseline, 329 exams, 27 cancers: 16 of 27 in both (0.59 [0.39, 0.78]); 1 caught by each run only; AUROC 0.870 and 0.857 (−0.013 [−0.065, +0.036]).
   - **What the test can detect:** about 11 to 12 stretched 1-year cancers are expected in test (dev 18 among all stretched exams, scaled by the series counts, 400 test against 578 dev). With 12 of 12 caught the exact 95% interval of sensitivity is 0.74 to 1.00; with 11 of 12, 0.62 to 1.00. An exact paired (McNemar) test at two-sided 5% needs at least 6 discordant cancers, all in one direction (p = 0.031), so only a harm of about half the stretched cancers could be detected. AUROC differences below about 0.03 (1 year) and 0.05 (6 years) cannot be separated from chance. **A "no difference" here does not show "no harm".**
8. **Where Sybil looks** (`s6_attention.py`; descriptive; conventions frozen from dev: box order reversed, patient right = image left): share of slice attention within ±1 bin of the largest recorded nodule against shuffled nodule bins; peak within 1 bin; in-plane attention on the nodule's lung side. Dev, all exams (`results/s5/s6_attention_dev_as_if_test.json`): cancer within 1 year 71% (76 exams; shuffled median 23%, 97.5th percentile 32%); no cancer, nodule ≥ 8 mm 51% (842; shuffled 22%); 4 to 8 mm 31% (2,032; shuffled 22%); nodule's lung side 90% (cancer) and 76% (≥ 8 mm). The maps are coarse (one bin is 20 mm of the box).

Everything else at S6 is exploratory (protocol 11) and carries its counts of exams, participants and cancers.

## S6 run plan (fixed now; the lead's decision of 17 Nov)
| Account | Order inside the account | Cost | With 10% reserve | Limits that bind |
|---|---|---|---|---|
| `armanfo` | 1. smoke (demo case + 3 test series; demo equal to the published scores, difference ≤ 0.005) → 2. **T1** baseline (2,279 main rows with their z-fix variants) → 3. **T4** (500 soft-kernel partners of T1 exams) | about $7.4 | about $8.1 | project limit on `armanfo` $27.00 ($14.03 used on 17 Nov); month cap $29.50 ($15.69 used) |
| `forghanishayan` | 1. **identity check** (a few series already scored on `armanfo` must give equal numbers to the last digit, as in S3) → 2. **T2** year 1 (2,243 main rows with z-fix variants) → 3. **T3** year 2 (2,193 main rows with z-fix variants) | about $12.0 | about $13.2 | project limit on `forghanishayan` $20.00; month cap $29.50 ($5.02 used on 17 Nov); the lead's deployed app there is never touched |

- **Total** about $19.4 (about $21.3 with the reserve) against $22.30 allowed (task `lung_l2_audit` $23.30 left minus $1.00). Billed S3 rates: main rows with z-fix variants $0.0026 per row, pair rows $0.0023; smoke and image rebuild about $0.30 per account. Project cap $72 ($24.91 left).
- **Rules:** every launch through the guard (`budget.py`), usage checked before every launch, `MODAL_PROFILE` set per command; all main runs with `--zfix-max 0.65` (T5 grows with T1, T2, T3); the unattended driver (A5); T4 or L4 GPUs, at most 4 containers, timeout ≤ 60 minutes.
- **Before any test launch:** the lead's OK of this file is logged (N3); then `s6_manifest_test.py --root test --lead-ok <freeze commit>` builds `manifest_test.csv` (committed with its hash); the cloud job changes only to read it (root `test`; logged).
- **Fallbacks (fixed now):** if T3 is not scored, H1, H2, H3 and H6 use the T5 rows of T1 and T2, and H7 uses the T0→T1 pairs only; if T4 is not scored, H4 is not evaluated; if no T5 row is scored, H1, H2, H3 and H6 are not evaluated; if T2 is not scored (for example the identity check on `forghanishayan` fails), H7 has no consecutive pair and is not evaluated, and the z-fix hypotheses use the T5 rows of T1 (and T3 if scored). A hypothesis that is not evaluated counts as not confirmed and keeps its place in the family.
- **Checks before the analysis (protocol 11):** G2a demo; failures < 5% per tier; G2b and G2c on every file; identity: calibrated scores of the re-extracted main series equal the L1 scores within 1e-4 for ≥ 99% of the 5,412 L1 series (on both accounts).

## What I ask the re-check to check
`docs/PROMPT_REVIEW_S5b.md`: hashes; dev as if test; the H6 and H7 code and the frozen axes file; the H5′ evidence and its random-choice test; the harm and attention items; the test-list script; the "partly seen" label of H7; the diff from `c593005`. It must be done by a fresh session that did not do step R.

## SHA-256 of the frozen and analysis files

| File (path from `imgsae/exploratory/lung_l2/`) | SHA-256 (committed content) | git blob id |
|---|---|---|
| `results/s5/frozen_thresholds_L2.json` | `385b9394340459306e52a7b37d117ef548cef2950f2753c962f4341153465f4c` | `99319a575a0601edb6207fbdd586e4d0d8bd4223` |
| `results/s5/frozen_raw_arm_K64.npz` | `635d8bf6bce56b2ad9f2691a2ee0fdd1e1b8a5235250b289c783a7c9f61af967` | `e2b73fac87517158cd1550d511fa7d31c12447a5` |
| `results/s5/frozen_families_raw_K64.json` | `467af4904ef0cea363cdc2a18e7a33ce289008b89da5b957ea612bdff2788018` | `87052b68a46a2943896c3353c58740021cf279ad` |
| `results/s5/frozen_FI_params.json` | `09a05e98ef088d4c88a80de0d899827504dc0ad89a0f3580f4bee78ba3e6cfc3` | `5a0fa23b957e276ac20b953fa156f720da858f9b` |
| `results/s5/frozen_combinations.json` | `db04367288a9e45000990e56382a9e9007db15b2878a910361eb9f6aa110b778` | `73fe89387bb8d2514f3e7882f6b6f6ea045887db` |
| `results/s5/frozen_axes_pooled.npz` | `4ff8ade34829535e3d9251ad7e4c2397cb5647c6f4345e38fff1182a3f17da45` | `b6c946bc940e1e5a4c77e1252ed92b5c26e7df23` |
| `results/s5/s6_dev_as_if_test.json` | `8ffa4377bdc1f1a4e9dd30c6c809bab0ed417cc9bd3f3ba72fcc46beebeb873a` | `ca1ad59c8ceb51dcfe0c3439f5d02abfc26ac0ad` |
| `results/s5/s6_dev_as_if_test_h7_no_cancer_sensitivity.json` | `8eaf0371111db62a73be4559b77d565d6d3af2765bcc6757da7ab52d2e414259` | `5c6577818628416e83480bdcf74e553fee87dbc7` |
| `results/s5/s6_attention_dev_as_if_test.json` | `4428ac7893ffa64b3ff0514b4519953080f7c4439aafb9a95cd5e6bbbaaf702b` | `a8379d0a46da4bc446b89117f1eb709ee360d8c9` |
| `results/s5/s5_h5prime_dev.json` | `ed29c357bd2f6eb733ca5c68269660e8c20fffa867e7f133725fcada0804bead` | `cb9b97cac6308c32f0613421f4a73214216176e8` |
| `s6_frozen_analysis.py` | `d0fc05e703e1b124f15bad215461a51ccc71d0ab249a44d0ee4cb06105b01754` | `07f3460ff725f58686686868d724063aac48db1f` |
| `s6_attention.py` | `084fb9fa00ebe8b1b93e6742f90fd25efa6ab890cf572278b17bcd6337f470c8` | `ec5c7764734cb1cf2679941f87db72ca8ab7a466` |
| `s6_manifest_test.py` | `210f4ab92985074679b38569132e4f7bd95d0ebedf0673489d7def1484b71914` | `14785d5d3ede589d54bad73e136106a8588e78ac` |
| `s5_freeze.py` | `5d27c0a64d693342dbacf9798b37e0d85158c6da40842a1998e258e7291449ec` | `2b3011ce041d5e00a0fb5c94e7eacdaa328e0db9` |
| `s5_axes_freeze.py` | `6223a56c845134f1ccf8e9dd06afe42d78cf662ce067e2305b2fb97b17781a6d` | `f38497334893a82f039ae3372c4ae8504f7d700e` |
| `s5_h5prime_dev.py` | `1dc20f46ab965dccae520b6bcff4465514a7e49a03f630d208c9cf6e2700c06d` | `5420a0134c85e5853cbf7404d701a942b8b4bf6b` |
| `s5_hashes.py` | `648fa56ff3733761c593254e3f2830ed2d036da0e87258c933dcd43669226b88` | `3055cb0d45c4249c96524abc926179c2de5c2646` |
| `s4_common.py` | `ab4467268a8b8dcda476f52b5f3335bfefc7a9cd75a206d3e35153813ebbb9c0` | `9cb8640a874013d40fa56a04257e235e029e4240` |
| `s4_core.py` | `637493e1fdcf2251dbb296e90a47be174e2a47495533902f7f4499a8a9f6e40b` | `f90dfc0aa7cf7edf1d16bef58b474bbbaaab6590` |
| `s4_q1a.py` | `9c22e96ef7b67aa104906033ab729e9568c411faedec1da91c8866eccfce53e7` | `13e9e8deed8650fcadd3a9329b0c245de8bfe685` |
| `s4_q1d.py` | `f7418d5a376628dc8b67e128a6de43876fc6b01be022acdf9c6e26a50a6c4d63` | `72bf8442b4dba0dfc6e1a95b1ad6865bdbfadc98` |
| `s4_refs.py` | `e3d32dc5b3dae24f057e01d1865af8aeab57a81d6a9bd522d6b9251d634d3e0b` | `fd64546ab340e1df5d30a031b4ebf5ce55397450` |
| `s4_u3.py` | `65b12656af6b25678c3fc7260327603fde9884b1b19243e43c20bcdca47683f5` | `cf6fafad0dbc58c39ac53afa948e11d332bd82a3` |
| `l2_data.py` | `7af12f02a0c89be188ab61e41820dccd99f3bc3f10c850c62976050c2605fb30` | `5f484c4cacfe3a058a1b655261ca9d5f4e41e439` |
| `l2_form.py` | `934d862a92114c70dd1b94c29e975eebf32496322a2fa07254ca731dd14c8548` | `41b33594517ca1e83342745fecfaae2d89ee8fba` |
| `series_rule.py` | `cff3a764f1391acaf54f5ee0f8f381a790daa16b437bee78e7e998354e4d2a2d` | `19bfe82cac7a280cab54ec88b381fad72df8341b` |
| `../lung_l0/nlst_l0.py` | `135689f2ee76fed51ba99fde88580c9559f03ca7fb9b4d7b46dac7bde5369e7f` | `d8b87fa7a0fc47d8270d677c7741c0d0df254b1a` |
| `results/l2_form_params.json` | `02ec7c2dda14450ce06a9bc3b127d572ed9c8d6472cf37d550b68ec6283f8034` | `97d086b6e9a23caff3990f67a54c2ed31771d635` |
| `results/manifest_dev.csv` | `8fe372a690c551767e6a9a6eedae9e48439dc14009f07ba201bff8b9dea4b2ac` | `f44823a71faca9d4a1312a755af9a9bfa96a1cec` |
| `r1_arms.py` | `9dd28089b40d85fb833b9b19ea52e1b6e7e2b6a5b4b0d625c7a7e9c52a04f4aa` | `0ecdb03f226e9ede5a0e3093597979d55d4881c9` |
| `r2_shared.py` | `cb6f06988d6f2e833999e9355e2eff7283e33230e7cb7f5413f7068ef711a596` | `b5dfadbfc3631e66d657d79b3fe26e4e8bfeafc1` |
| `r4_axes_audit.py` | `3382f469ff7a0294c5fb2d59c621466515934a62b34a2195bdafb50e36c8306f` | `ee64bfcdd5048cdb1bd550f0a43430f35c6024bc` |
| `r5_repair.py` | `8f55f97dd3660199a3b9c20f3ab5905a1fe4e2a9652545c16c7bd23f2418aeb3` | `956f7c794b0d5c592821158714c97a581860e388` |
| `r6_candidate.py` | `e73b6d5c59f3e28a6c76592121905d316894944fd525e688f800def5234c3d29` | `20a1ef8cba3cf63de83be4235d447f7f4e457d26` |
| `r7_more.py` | `c28093d39c00a438d5fa7981dda9fbdf8759c42d443919a1a31d055d93d550e0` | `8fac5508689fbed0cb760fb45573adc5d21ceaa2` |
| `r9_attention.py` | `bd0904e3b5e61fa827f21c6c99c57dd71616c17920bf32577778627e73cd62cf` | `10b9d8fb7a12b7d8c8164e09b608bc1b9d3726e5` |
| `lung_l2_vol/l2/run_info/heads.npz` under `imgsae_data/` (PC only: Sybil's head weights (incl. hidden_fc) or calibrator, saved by the cloud job) | `ba2d6d85d330cc6c99360c557647460ba4fa7ab738abba9be79c1d26b8009bac` | — |
| `lung_l2_vol/l2/run_info/sybil_ensemble_simple_calibrator.json` under `imgsae_data/` (PC only: Sybil's head weights (incl. hidden_fc) or calibrator, saved by the cloud job) | `74cedae39715fa1ca29ebad881790432639d39fd0a3cf811529ebce9a767393a` | — |
| `lung_l2/r/r2_shared_pooled.pkl` under `imgsae_data/` (PC only: source of the frozen axes, fitted by r2_shared.py on dev) | `a93cc049fc3d7ed50826180a28c020c8c0543bfb5432fbfcc6a11f776ebb83bc` | — |

Text files are hashed on their committed content (LF line endings). The frozen folder `results/s5/` is stored byte-exact (`-text` in `.gitattributes`), so `Get-FileHash` or `sha256sum` on a checkout gives these values. For the other text files on Windows with `core.autocrlf`, use `git show HEAD:<path> | sha256sum` or compare the git blob ids (`git ls-tree HEAD <path>`). The commit that freezes this file is logged in `docs/EXECUTION_LOG.md`. In S6 (step N4) the cloud job `cloud/l2_sybil_modal.py` changes only to read the test manifest written by `s6_manifest_test.py` (protocol 11); that change is logged and touches no analysis file. The step R scripts (`r*.py`) are listed for provenance only: they made the dev evidence and the frozen axes, and are not run at S6.
