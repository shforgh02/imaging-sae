# Lung L2, S4 on dev: results (discovery only)

- **Date:** 2026-11-16. **Protocol:** `docs/LUNG_L2_PROTOCOL.md` section 9 (with amendments A1 to A5, section 16a). **Plan step:** P4b of `docs/PLAN_L2_NEXT_v1.md`.
- **Analysis code fixed before any full-dev run:** commit `a536192` ("S4 analysis code fixed"). No script was changed after its full-dev result was seen.
- **What these numbers are:** dev results are discovery. None is a confirmed claim. Dev was used by Sybil's authors for model selection (protocol C6), so **Sybil's dev accuracy is optimistic**: on dev, Sybil's 1-year AUROC is 0.969, while on test L1 measured 0.914 (all screens) and 0.927 (baseline).
- **Participants:** 2,493 dev participants in Sybil's split file; 2,492 have a usable exam (S1 manifest).
- **Data:** 7,336 dev exams (2,484 baseline, 2,442 year 1, 2,410 year 2), 998 z-fix variants, 500 soft-kernel partners; S3 gate passed on all 8,834 files (`results/s3_checks_all.json`). Image measures present for 97.5% of exams (rule A2 applied), air noise for 95.1%; no empty variable.
- **Number tables:** generated from the result files by `s4_report.py` and appended at the end (section "Tables"). Result files: `lung_l2/results/s4/`.

## The short answer (for the lead)
1. **Sybil's score is mostly not explained by known factors.** Recorded findings, demographics, image measures and technical factors together explain 31% of the variation of its 1-year logit (CV R² 0.307; 7,336 exams, 2,492 participants) and 33% of the 6-year logit on baseline screens (2,484 exams). Nodule findings carry most of that (Shapley share 0.21 and 0.25). Technical factors carry little: 0.016 [0.008, 0.024] at 1 year, and 0.009 [−0.001, 0.019] at 6 years (the second interval includes 0).
2. **The slice-spacing error is real and large.** In the 924 dev exams whose spacing is at most 0.65 of the slice thickness (424 participants), placing the slices at their true spacing lowers Sybil's mean member 1-year logit by 0.33 [0.28, 0.37] (about 0.32 of its between-exam SD). 67% [64%, 70%] of these exams move by at least 0.25 SD at 6 years. The τ90 flag changes in 7.5% [5.6%, 9.7%]. Same in both dev halves. This holds with and without a lung cut by the crop. U1b's dev qualification is met (share ≥ 30%).
3. **The kernel matters little.** In 500 sharp/soft pairs of the same acquisition (500 participants), the sharp kernel gives a slightly higher logit (+0.03 [0.01, 0.05]), the between-kernel SD is 0.21 of the between-exam SD (ICC 0.98), and the τ90 flag changes in 1.8% [0.8%, 3.0%].
4. **Only the simplest decomposition is valid.** At K = 64, raw units are the only arm that passes all four validity marks (56 families replicated across members, 40 named). The sparse autoencoder **fails** V1 (it does not keep Sybil's function: logit correlation 0.72 and 0.73, AUROC change −0.023) and V3 (8 families; 16 needed). PCA and ICA keep the function but **fail** V3 (3 and 2 families replicate across the five members) and V4. NMF and k-means **fail** V1, V3 and V4. By the protocol's rule, raw units is the primary arm. At K = 128 (check, finished 2026-11-16), raw units is again the only valid arm (102 families, 76 named). The SAE now passes V3 (35 families, 24 named) but still **fails** V1 (logit correlation 0.83 and 0.86, AUROC change −0.029 at 1 year) and **fails** V4 (label agreement between halves 0.25). PCA and ICA again fail V3 and V4; NMF and k-means again fail V1, V3 and V4.
5. **Most of Sybil's named features are nodule-type risk units.** Of the 56 raw-unit families, 34 are named N (nodule findings), 6 T (technical), 16 mixed. Nearly all of them track Sybil's own risk (family AUROC for y1 about 0.96 to 0.97, or the mirror value). The six T families are risk units whose activation is mainly explained by technical factors: lower when the lung is cut by Sybil's 200-slice crop (rank-biserial −0.75 to −0.90), in slices thicker than 2.5 mm, with z-stretch, and on one Philips model (Mx8000). They carry 5.0% of the variance of the 1-year logit.
6. **Use of the features: no candidate passes.** Technical removal (U1a) keeps the AUROC (−0.001 and −0.002) and lowers the false-alarm spread across scanner groups from 0.023 to 0.007 (ratio 0.31), but the bootstrap interval of the ratio is [0.34, 1.36] and the two dev halves disagree (1.43 and 0.63): **gate 9.8 fails**. Sybil plus the form at the radiologists' sensitivity (U3) lowers false alarms from 60 to 42 per 1,000 screens (ratio 0.70), but the interval [0.35, 1.05] includes 1: **gate 9.8 fails**. The fixed reliability flag (U2, R-fixed) goes the wrong way (−0.032 [−0.051, −0.013]); the learned flag (R-learned) "works" (+0.378) only because it flags exams with high Sybil scores, so it is not a reliability flag.
7. **Simple image measures add nothing to the form.** F+I (the form's logit plus 5 patient measures) is not better than F: −0.005 [−0.015, 0.004] at 1 year, −0.013 [−0.026, −0.002] at 6 years. On dev, Sybil adds to F+I (+0.050 and +0.104), but on test L1 found that Sybil adds almost nothing to the recorded findings (+0.000 at 1 year all screens, +0.011 at 6 years). So the dev gain is most likely the C6 selection effect.
8. **Gate 9.8: something holds → go to S5.** The strongest candidates that hold are technical and outcome-free (z-fix magnitude and direction, the kernel shift) and the feature-level technical share. 344 of 354 listed candidates "hold", but about 320 of them are near-automatic (see "Cautions").

## Details by question
### Scores (9.1)
- Check P1 **passed**: Spearman(ℓ̄_t, s_t) 0.991 at t = 1 and 0.997 at t = 6 (all 7,336 dev exams). Sybil's published score has ties (step-like calibrator): s1 takes 227 distinct values and 16.3% of exams have s1 = 0; the rank correlation of ℓ̄_1 with the uncalibrated mean member probability is 0.998.
- Hazard units: on in 5.6% of (exam, member, unit) cases; only in members 0 and 4 (13% and 15%), only units for years 2 and 3. Members 1, 2, 3 give the same logit for all six years.
- Dev AUROC (participant bootstrap, 2,000 draws): Sybil 0.969 [0.949, 0.985] for y1 (7,289 exams, 2,492 participants, 88 cancers), 0.926 [0.882, 0.963] for y2 (2,470 baseline exams, 65 cancers), 0.851 [0.816, 0.885] for y6 (2,180 baseline exams, 135 cancers). F: 0.928 [0.893, 0.959] (y1), 0.779 [0.737, 0.821] (y6). Radiologists' call (y1): sensitivity 0.909, specificity 0.657.

### Q1a composition (9.7)
- See point 1 above and the table. For non-cancer exams the explained share is lower (0.245 at 1 year, 7,014 exams, 2,343 participants; 0.249 at 6 years, 2,338 baseline exams).

### Decomposition (9.4, 9.5) and features (Q1b, Q1c)
- Validity table: see the tables. **The sparse autoencoder is not the best arm; it is not valid.** This is reported as it is (protocol 9.5).
- Group shares of ℓ̄_1 with raw units (exact split, 7,336 exams): N-named families 0.446, mixed 0.205, T 0.050, unreplicated units 0.133, residual 0.166. ℓ̄_6 (2,484 baseline exams): N 0.485, mixed 0.212, T 0.053, unreplicated 0.148, residual 0.147, intercept −0.046.
- U = the part of ℓ̄_t not explained by the known groups. **U adds to F** on dev: +0.041 [0.020, 0.067] at 1 year (88 cancers), +0.094 [0.062, 0.127] at 6 years (135 cancers); LR tests p < 1e-30. Same caution as point 7 (C6; L1 test).
- Stable part (Q1c, 2,435 participants with baseline and year-1 exams): r(ℓ̄_1, T0 to T1) 0.725 [0.692, 0.758]. The stable part is split like the score itself (N 0.44, mixed 0.21, T 0.05). Without cancer within 2 years of T0 (2,394 participants): r 0.719.

### Q1d / U1b technical changes (9.7)
- z-fix (D5, 924 exams, 424 participants, 16 one-year cancers): see point 2. By stretch: 1.6 (333 exams) mean Δℓ̄_6 −0.19, share ≥ 0.25 SD 0.60; 2.0 (591 exams) −0.25, 0.71. Lung cut (756 exams) −0.22, 0.67; not cut (168 exams) −0.29, 0.67. AUROC in D5 (descriptive, 16 and 27 cancers): main 0.995 / 0.874, z-fix 0.985 / 0.859 (y1 / y6): correcting the geometry does not raise Sybil's AUROC. Which terms carry the z-fix change of ℓ̄_1: mixed families −0.20 on average, residual −0.10, T families −0.06. The pilot's 74 extra z-fix rows (ratio 0.65 to 0.95; not D5) move less (mean −0.11).
- Kernel pairs (500): by maker, sharp minus soft +0.052 (GE, 236 pairs), +0.017 (Philips, 50), +0.007 (Siemens, 195), −0.034 (Toshiba, 19).

### Q2 errors (9.7)
- τ90 = 0.0180 (specificity reached 0.888 because of ties), τ_rad = 0.0040. At τ90 among 7,201 exams with y1 = 0: Sybil-only false alarms 564 (367 participants), shared 246 (200), form-only 475 (428), true negatives 5,916 (2,264).
- Image and technical variables (SMD against true negatives, q < 0.05): Sybil-only false alarms have larger lungs (+0.19 [0.08, 0.31]), lower tube current (−0.14 [−0.24, −0.05]) and more real slices (+0.16). Shared false alarms have more emphysema (+0.25), larger and longer lungs, fewer thick-slice scans (−0.21). Form-only false alarms have sharper kernels (+0.17) and higher tube current (+0.15). Larger lungs appear in all three classes, and tube current goes in opposite directions for Sybil-only and form-only false alarms, so these associations look partly like site and protocol mixes.
- Family and group-term SMDs are very large (up to 5 to 7), but they are near-automatic: the families are Sybil's own risk units, and the false-alarm classes are defined by Sybil's score.
- Misses (descriptive only): 6 of 88 one-year cancers missed at τ90 (4 of 10 small-cell); 10 of 65 at 2 years; 54 of 135 at 6 years on baseline screens: small-cell 16 of 19, central 11 of 14, stage IV 22 of 30, diagnosed 4 to 6 years later 26 of 34 (claims only for subgroups with at least 10 cancers; exact intervals in `s4_q2_dev.json`).

### Use (9.7)
- U1a, U2, U3: see point 6. U4 references (CV AUROC): the linear probe on all 2,560 numbers of h gives 0.970 [0.953, 0.984] (y1) and 0.874 [0.839, 0.905] (y6), against Sybil 0.969 and 0.851; the raw-unit family model 0.972 and 0.864; SAE families 0.956 and 0.830; PCA 0.966 and 0.843; NMF 0.950 and 0.800; ICA 0.535 and 0.553.

### Simple references (amendment A3)
- R-size (largest nodule diameter, no fitting; partly seen, a reference only): 0.874 [0.825, 0.922] (y1), 0.662 [0.607, 0.714] (y6).
- F+I with 5 measures: 0.924 (y1), 0.766 (y6); with 7 measures: 0.919, 0.767; lung not cut (6,516 exams, 74 cancers; 1,902 baseline exams, 111 cancers): 0.909, 0.757. In every run F+I is not better than F. At the radiologists' sensitivity, F+I gives 241 false alarms per 1,000 screens (F 193, Sybil 60, C 42, radiologists 339). Limit: emphysema % depends on the scanner (Toshiba air about 38 HU low); F+I by maker is in `s4_refs_dev.json`.
- F+I parameters fitted on all dev, for freezing at S5: `results/s4/s4_refs_FI_params_dev.json`.

## Failed marks and negative results (as they are)
- Decomposition, K = 64: SAE V1 and V3 failed; PCA, ICA V3 and V4 failed; NMF, k-means V1, V3 and V4 failed. Only raw units valid.
- Decomposition, K = 128 (check): SAE V1 and V4 failed (V3 passed); PCA, ICA V3 and V4 failed; NMF, k-means V1, V3 and V4 failed. Only raw units valid.
- U1a: gate 9.8 failed (spread-ratio interval includes 1; halves disagree), although its point qualification is met.
- U3: gate 9.8 failed (interval includes 1).
- U2 R-fixed: wrong direction (−0.032).
- z-fix flag change 0.075: below its 0.10 margin (U1b still qualifies through the 30% share).
- Kernel pairs: share moved ≥ 0.25 SD 0.18 and flag change 0.018, both below the margins carried over from U1b.
- Q1a technical share of ℓ̄_6: interval includes 0.
- F+I does not beat F.

## Cautions
- **C6 optimism:** every dev number that uses Sybil's discrimination is optimistic. L1 on test: Sybil 0.914 (1 year, all screens) and 0.724 (6 years), and Sybil plus findings minus findings +0.000 and +0.011.
- **Near-automatic candidates:** in the gate table, the 114 family-covariance candidates (Q1b), the group and family SMDs of Q2, the Q1b and Q1c group shares, and U2 R-learned hold almost by construction, because raw units are the units that make Sybil's score and the classes are defined by that score. They will not be used as hypotheses.
- **Ties:** τ90 reaches 88.8% specificity, not 90%, because many exams share the same published score.
- **Multiplicity:** BH q within each table; the gate counts 354 candidates; S5 will freeze at most 5 hypotheses with Holm correction.
- **Order change (logged):** the K = 128 check ran in parallel with the later steps, which read only K = 64 outputs.

## Tables (generated from the result files by `s4_report.py`; the K = 128 check finished on 2026-11-16 and all its rows are in)

### Scores (9.1)
- Exams 7,336 exams, 2,492 participants. 2,493 dev participants in Sybil's split file; 2,492 have a usable exam (S1 manifest).
- Check P1 (Spearman of lbar_t with s_t >= 0.98, all dev exams): t1 0.9914, t6 0.9967 -> pass; t6 on baseline 0.9967.
- Diagnostics: t1: Spearman with the mean member probability 0.9980, 227 distinct values of s, 16.3% at the minimum 0.0000; t6: Spearman with the mean member probability 0.9986, 524 distinct values of s, 2.1% at the minimum 0.0000
- Hazard units on: overall 0.0559; by member [0.13316, 0.0, 0.0, 0.0, 0.14645]; by unit [0.0, 0.17571, 0.15973, 5e-05, 0.0, 3e-05].

| horizon | population | Sybil s_t | Sybil lbar_t | F | Sybil − F |
|---|---|---|---|---|---|
| y1 | 7,289 exams, 2,492 participants, 88 cancers | 0.969 [0.949, 0.985] | 0.969 [0.947, 0.985] | 0.928 [0.893, 0.959] | 0.041 [0.017, 0.070] |
| y2 | 2,470 exams, 2,470 participants, 65 cancers | 0.926 [0.882, 0.963] | 0.926 [0.881, 0.963] | — | — |
| y6 | 2,180 exams, 2,180 participants, 135 cancers | 0.851 [0.816, 0.885] | 0.851 [0.817, 0.885] | 0.779 [0.737, 0.821] | 0.072 [0.027, 0.118] |

- Radiologists' call, y1 (7,289 exams, 2,492 participants, 88 cancers): sensitivity 0.909, specificity 0.657, positive 0.350.
- Sybil's dev numbers are mildly optimistic: dev was used for Sybil's model selection (protocol C6). Test is clean.

### Q1a: composition by known groups (9.7)

| target | exams, participants | CV R² ridge | CV R² boosting | N | B | D | I | T | unexplained |
|---|---|---|---|---|---|---|---|---|---|
| lbar1_all | 7,336, 2,492 | 0.307 | 0.323 | 0.207 [0.158, 0.245] | 0.037 [0.027, 0.046] | 0.015 [0.008, 0.023] | 0.031 [0.022, 0.040] | 0.016 [0.008, 0.024] | 0.693 |
| lbar6_baseline | 2,484, 2,484 | 0.328 | 0.288 | 0.251 [0.204, 0.296] | 0.033 [0.019, 0.047] | 0.013 [0.005, 0.021] | 0.022 [0.013, 0.031] | 0.009 [-0.001, 0.019] | 0.672 |
| lbar1_never_cancer | 7,014, 2,343 | 0.245 | 0.265 | 0.137 | 0.042 | 0.013 | 0.032 | 0.020 | 0.755 |
| lbar6_baseline_never_cancer | 2,338, 2,338 | 0.249 | 0.224 | 0.157 | 0.039 | 0.012 | 0.023 | 0.018 | 0.751 |

### Decomposition arms, K = 64 (9.4, 9.5)

| arm | V1 r (y1/y6) | V1 dAUROC (y1/y6) | V1 | V2 (median r / share) | V3 families | V4 (half corr / label agree) | valid | named replicated | labels |
|---|---|---|---|---|---|---|---|---|---|
| raw | 0.999 / 0.997 | -0.0002 / -0.0001 | pass | pass — / — | pass 56 | pass 0.706 / 0.850 | **valid** | 40 | {"N": 34, "mixed": 16, "T": 6} |
| pca | 0.999 / 0.998 | -0.0003 / -0.0015 | pass | pass — / — | **FAILED** 3 | **FAILED** 0.642 / 1.000 | not valid | 2 | {"unnamed": 1, "T": 1, "N": 1} |
| ica | 0.999 / 0.998 | -0.0003 / -0.0015 | pass | pass 0.999 / 0.994 | **FAILED** 2 | **FAILED** 0.565 / 0.000 | not valid | 0 | {"unnamed": 2} |
| nmf | 0.869 / 0.858 | -0.0003 / -0.0018 | **FAILED** | pass 0.998 / 0.965 | **FAILED** 8 | **FAILED** 0.596 / 0.667 | not valid | 3 | {"unnamed": 5, "N": 2, "T": 1} |
| kmeans | 0.980 / 0.979 | -0.0010 / -0.0085 | **FAILED** | pass 0.892 / 0.667 | **FAILED** 0 | **FAILED** — / 0.000 | not valid | 0 | {} |
| sae | 0.716 / 0.732 | -0.0228 / -0.0087 | **FAILED** | pass 0.941 / 0.829 | **FAILED** 8 | pass 0.838 / 0.750 | not valid | 4 | {"unnamed": 3, "N": 3, "mixed": 1, "T": 1} |

### Decomposition arms, K = 128 (9.4, 9.5)

| arm | V1 r (y1/y6) | V1 dAUROC (y1/y6) | V1 | V2 (median r / share) | V3 families | V4 (half corr / label agree) | valid | named replicated | labels |
|---|---|---|---|---|---|---|---|---|---|
| raw | 1.000 / 1.000 | -0.0000 / -0.0000 | pass | pass — / — | pass 102 | pass 0.720 / 0.829 | **valid** | 76 | {"N": 55, "mixed": 26, "T": 21} |
| pca | 1.000 / 0.999 | -0.0001 / -0.0003 | pass | pass — / — | **FAILED** 3 | **FAILED** 0.642 / 1.000 | not valid | 2 | {"unnamed": 1, "T": 1, "N": 1} |
| ica | 1.000 / 0.999 | -0.0001 / -0.0003 | pass | pass 0.998 / 0.954 | **FAILED** 7 | **FAILED** 0.208 / 0.000 | not valid | 0 | {"unnamed": 7} |
| nmf | 0.907 / 0.901 | -0.0000 / -0.0002 | **FAILED** | pass 0.999 / 0.953 | **FAILED** 10 | **FAILED** 0.675 / 1.000 | not valid | 4 | {"unnamed": 5, "T": 3, "mixed": 1, "N": 1} |
| kmeans | 0.983 / 0.982 | -0.0007 / -0.0050 | **FAILED** | pass 0.906 / 0.742 | **FAILED** 0 | **FAILED** — / 0.000 | not valid | 0 | {} |
| sae | 0.833 / 0.855 | -0.0290 / -0.0031 | **FAILED** | pass 0.948 / 0.940 | pass 35 | **FAILED** 0.833 / 0.250 | not valid | 24 | {"N": 21, "unnamed": 11, "T": 3} |

### Q1b (9.7)
- Primary arm: **raw**.
- U adds to F, y1 (7,289 exams, 2,492 participants, 88 cancers): AUROC F 0.926 [0.890, 0.959], F + U 0.967 [0.941, 0.988], difference 0.041 [0.020, 0.067], halves 0.059 / 0.028, LR test chi² 182.32, p 0.0000.
- U adds to F, y6 (2,180 exams, 2,180 participants, 135 cancers): AUROC F 0.775 [0.730, 0.817], F + U 0.868 [0.837, 0.898], difference 0.094 [0.062, 0.127], halves 0.066 / 0.117, LR test chi² 138.83, p 0.0000.
- Group shares of lbar1 (raw): intercept 0.000 [-0.000, 0.000]; residual 0.166 [0.164, 0.168]; N 0.446 [0.442, 0.449]; mixed 0.205 [0.202, 0.208]; unreplicated 0.133 [0.131, 0.134]; T 0.050 [0.050, 0.051] (sum 1.0000).
- Group shares of lbar6 (raw): intercept -0.046 [-0.047, -0.044]; residual 0.147 [0.141, 0.153]; N 0.485 [0.481, 0.489]; mixed 0.212 [0.206, 0.217]; unreplicated 0.148 [0.145, 0.151]; T 0.053 [0.053, 0.054] (sum 1.0000).

### Q1c: stable part, T0 and T1 (9.7)
- all: 2,435 participants; r(lbar1) 0.725 [0.692, 0.758], r(lbar6) 0.722 [0.687, 0.757].
  - stable shares of lbar1: intercept -0.000 [-0.000, 0.000]; residual 0.162 [0.159, 0.164]; N 0.438 [0.432, 0.444]; mixed 0.213 [0.209, 0.218]; unreplicated 0.136 [0.134, 0.138]; T 0.051 [0.050, 0.052]
  - stable shares of lbar6: intercept -0.048 [-0.050, -0.045]; residual 0.132 [0.128, 0.137]; N 0.478 [0.473, 0.483]; mixed 0.226 [0.221, 0.232]; unreplicated 0.156 [0.153, 0.160]; T 0.054 [0.053, 0.055]
- no_cancer_within_2y_of_T0: 2,394 participants; r(lbar1) 0.719 [0.684, 0.751], r(lbar6) 0.716 [0.680, 0.749].
  - stable shares of lbar1: intercept 0.000 [-0.000, 0.000]; residual 0.161 [0.159, 0.163]; N 0.435 [0.429, 0.440]; mixed 0.216 [0.212, 0.220]; unreplicated 0.137 [0.135, 0.139]; T 0.051 [0.050, 0.052]
  - stable shares of lbar6: intercept -0.047 [-0.049, -0.044]; residual 0.129 [0.125, 0.134]; N 0.475 [0.469, 0.480]; mixed 0.229 [0.224, 0.235]; unreplicated 0.158 [0.155, 0.162]; T 0.054 [0.053, 0.055]

### Q1d / U1b: technical changes inside one exam (9.7)
- tau90 = 0.0180; SD lbar1 1.028, SD lbar6 all 0.930, baseline 0.960.
- z-fix, D5 (924 exams, 424 participants, 16 cancers): t6 mean -0.231, SD 0.454, ICC 0.870, share |Δ| ≥ 0.25 SD 0.670, flag change 0.075; U1b qualifies: yes. Intervals: share_ge_quarter_sd_lbar6 0.670 [0.638, 0.701] (halves 0.669 / 0.671); share_flag_changed 0.075 [0.056, 0.097] (halves 0.074 / 0.075); mean_delta_lbar1 -0.326 [-0.366, -0.282] (halves -0.320 / -0.332); mean_delta_lbar6 -0.231 [-0.267, -0.192] (halves -0.227 / -0.235)
- Kernel pairs (500 exams, 500 participants, 8 cancers): t1 mean 0.028, t6 mean 0.025, SD ratio t6 0.204, ICC t6 0.979, flag change 0.018. Intervals: share_ge_quarter_sd_lbar6 0.184 [0.152, 0.218]; share_flag_changed 0.018 [0.008, 0.030]; mean_delta_lbar1 0.028 [0.009, 0.049]; mean_delta_lbar6 0.025 [0.008, 0.042]

### Q2: false alarms and misses (9.7)
- tau90 0.0180 (specificity reached 0.888), tau90_F -3.968, tau_rad 0.0040.
- Classes at tau90: sybil_only 564 exams (367 participants); shared 246 exams (200 participants); form_only 475 exams (428 participants); true_negative 5,916 exams (2,264 participants)
  - sybil_only: 65 variables with q < 0.05; largest: fam29_N 5.45; fam7_N 5.37; fam46_N 4.90; fam43_N 4.79; fam32_N 4.70; fam31_N 4.56; fam52_N 4.27; fam51_N 4.18
  - shared: 71 variables with q < 0.05; largest: fam29_N 7.18; fam7_N 6.68; fam43_N 6.47; fam46_N 6.23; fam31_N 6.21; fam32_N 5.64; fam55_N 5.28; fam52_N 5.13
  - form_only: 71 variables with q < 0.05; largest: G_N 0.62; fam41_N 0.61; fam0_N 0.60; fam30_N 0.60; fam18_N 0.60; G_unreplicated 0.59; fam12_N 0.59; fam21_N 0.58
- Misses y1 (all screens, 7,289 exams, 2,492 participants, 88 cancers): missed 6, caught 82 (descriptive).
- Misses y2 (baseline, 2,470 exams, 2,470 participants, 65 cancers): missed 10, caught 55 (descriptive).
- Misses y6 (baseline, 2,180 exams, 2,180 participants, 135 cancers): missed 54, caught 81 (descriptive).

### U1a: technical removal (9.7)
- dAUROC y1 -0.0010 [-0.0032, 0.0007] (7,289 exams, 2,492 participants, 88 cancers); y6 -0.0020 [-0.0079, 0.0035] (2,180 exams, 2,180 participants, 135 cancers).
- False-alarm spread over 7 maker × kernel groups: before 0.0228, after 0.0071, ratio 0.310 [0.337, 1.360]; F 0.0199.
- Qualification: {"dauroc_y1_ok": true, "dauroc_y6_ok": true, "ratio_ok": true, "sybil_spread_gt_F": true, "qualifies": true}.

### U2: reliability flag (9.7)
- R-fixed: flagged 0.357 of y1 = 0; statistic -0.032 [-0.051, -0.013] (halves -0.043 / -0.020); Sybil sensitivity flagged 0.926 (n 27) vs unflagged 0.934 (n 61).
- R-learned: flagged 0.200 of y1 = 0; statistic 0.378 [0.340, 0.413] (halves 0.388 / 0.368); Sybil sensitivity flagged 0.986 (n 71) vs unflagged 0.706 (n 17).
- Rule that can be frozen: R-learned.

### U3: Sybil plus the form at the radiologists' sensitivity (9.7; partly seen)
- 7,289 exams, 2,492 participants, 88 cancers; target sensitivity 0.909 (tables 0.909).
- False alarms per 1,000 screens: sybil 60.1 (sens 0.909); form_F 192.8 (sens 0.909); combined_C 42.0 (sens 0.909); radiologists 338.6 (sens 0.909)
- Ratio C / better of Sybil and F: 0.699 [0.352, 1.049]; qualifies (≤ 0.80): yes.

### U4: references (9.7)
- y1 (7,289 exams, 2,492 participants, 88 cancers): Sybil 0.969 [0.949, 0.985]; probe on h 0.970 [0.953, 0.984]; family models: raw 0.972 [0.948, 0.990] (56 fam.); pca 0.966 [0.942, 0.984] (3 fam.); ica 0.535 [0.444, 0.622] (2 fam.); nmf 0.950 [0.915, 0.978] (8 fam.); sae 0.956 [0.922, 0.982] (8 fam.)
- y6 (2,180 exams, 2,180 participants, 135 cancers): Sybil 0.851 [0.816, 0.885]; probe on h 0.874 [0.839, 0.905]; family models: raw 0.864 [0.831, 0.895] (56 fam.); pca 0.843 [0.806, 0.878] (3 fam.); ica 0.553 [0.487, 0.618] (2 fam.); nmf 0.800 [0.750, 0.843] (8 fam.); sae 0.830 [0.791, 0.868] (8 fam.)

### Simple references (amendment A3)
- R-size, y1 (7,289 exams, 2,492 participants, 88 cancers): 0.874 [0.825, 0.922] (partly seen; reference only).
- R-size, y6 (2,180 exams, 2,180 participants, 135 cancers): 0.662 [0.607, 0.714] (partly seen; reference only).
- F+I primary_5_measures, y1 (7,289 exams, 2,492 participants, 88 cancers): F+I 0.924 [0.886, 0.957], F 0.928 [0.893, 0.959], Sybil 0.969 [0.949, 0.985]; F+I − F -0.005 [-0.015, 0.004]; Sybil adds to F+I 0.050 [0.025, 0.080] (halves 0.063 / 0.039), LR p 0.0000.
- F+I primary_5_measures, y6 (2,180 exams, 2,180 participants, 135 cancers): F+I 0.766 [0.722, 0.810], F 0.779 [0.737, 0.821], Sybil 0.851 [0.816, 0.885]; F+I − F -0.013 [-0.026, -0.002]; Sybil adds to F+I 0.104 [0.067, 0.143] (halves 0.077 / 0.124), LR p 0.0000.
- F+I sensitivity_7_measures, y1 (7,289 exams, 2,492 participants, 88 cancers): F+I 0.919 [0.879, 0.955], F 0.928 [0.893, 0.959], Sybil 0.969 [0.949, 0.985]; F+I − F -0.009 [-0.021, 0.001]; Sybil adds to F+I 0.054 [0.026, 0.089] (halves 0.068 / 0.042), LR p 0.0000.
- F+I sensitivity_7_measures, y6 (2,180 exams, 2,180 participants, 135 cancers): F+I 0.767 [0.722, 0.810], F 0.779 [0.737, 0.821], Sybil 0.851 [0.816, 0.885]; F+I − F -0.013 [-0.028, 0.002]; Sybil adds to F+I 0.103 [0.066, 0.142] (halves 0.074 / 0.122), LR p 0.0000.
- F+I sensitivity_lung_not_cut, y1 (6,516 exams, 2,350 participants, 74 cancers): F+I 0.909 [0.861, 0.951], F 0.921 [0.880, 0.956], Sybil 0.966 [0.945, 0.984]; F+I − F -0.012 [-0.033, 0.002]; Sybil adds to F+I 0.061 [0.030, 0.101] (halves 0.040 / 0.078), LR p 0.0000.
- F+I sensitivity_lung_not_cut, y6 (1,902 exams, 1,902 participants, 111 cancers): F+I 0.757 [0.700, 0.809], F 0.783 [0.733, 0.829], Sybil 0.851 [0.814, 0.888]; F+I − F -0.025 [-0.042, -0.010]; Sybil adds to F+I 0.106 [0.062, 0.151] (halves 0.076 / 0.149), LR p 0.0000.
- U3 table, F+I: 240.6 false alarms per 1,000 at sensitivity 0.909.
- emphysema % depends on the scanner (Toshiba air about 38 HU low); F+I by maker is descriptive.

### Gate 9.8
- 354 candidates; 344 hold 9.8; 344 eligible (with valid arm and qualification); 344 not partly seen. Any valid arm: yes; primary arm raw.
- Leak check: pass; data check: pass. Decision: **go to S5**.
- Full table: `results/s4/s4_gate_dev.md`.


