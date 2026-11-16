## Scores (9.1)
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

## Q1a: composition by known groups (9.7)

| target | exams, participants | CV R² ridge | CV R² boosting | N | B | D | I | T | unexplained |
|---|---|---|---|---|---|---|---|---|---|
| lbar1_all | 7,336, 2,492 | 0.307 | 0.323 | 0.207 [0.158, 0.245] | 0.037 [0.027, 0.046] | 0.015 [0.008, 0.023] | 0.031 [0.022, 0.040] | 0.016 [0.008, 0.024] | 0.693 |
| lbar6_baseline | 2,484, 2,484 | 0.328 | 0.288 | 0.251 [0.204, 0.296] | 0.033 [0.019, 0.047] | 0.013 [0.005, 0.021] | 0.022 [0.013, 0.031] | 0.009 [-0.001, 0.019] | 0.672 |
| lbar1_never_cancer | 7,014, 2,343 | 0.245 | 0.265 | 0.137 | 0.042 | 0.013 | 0.032 | 0.020 | 0.755 |
| lbar6_baseline_never_cancer | 2,338, 2,338 | 0.249 | 0.224 | 0.157 | 0.039 | 0.012 | 0.023 | 0.018 | 0.751 |

## Decomposition arms, K = 64 (9.4, 9.5)

| arm | V1 r (y1/y6) | V1 dAUROC (y1/y6) | V1 | V2 (median r / share) | V3 families | V4 (half corr / label agree) | valid | named replicated | labels |
|---|---|---|---|---|---|---|---|---|---|
| raw | 0.999 / 0.997 | -0.0002 / -0.0001 | pass | pass — / — | pass 56 | pass 0.706 / 0.850 | **valid** | 40 | {"N": 34, "mixed": 16, "T": 6} |
| pca | 0.999 / 0.998 | -0.0003 / -0.0015 | pass | pass — / — | **FAILED** 3 | **FAILED** 0.642 / 1.000 | not valid | 2 | {"unnamed": 1, "T": 1, "N": 1} |
| ica | 0.999 / 0.998 | -0.0003 / -0.0015 | pass | pass 0.999 / 0.994 | **FAILED** 2 | **FAILED** 0.565 / 0.000 | not valid | 0 | {"unnamed": 2} |
| nmf | 0.869 / 0.858 | -0.0003 / -0.0018 | **FAILED** | pass 0.998 / 0.965 | **FAILED** 8 | **FAILED** 0.596 / 0.667 | not valid | 3 | {"unnamed": 5, "N": 2, "T": 1} |
| kmeans | 0.980 / 0.979 | -0.0010 / -0.0085 | **FAILED** | pass 0.892 / 0.667 | **FAILED** 0 | **FAILED** — / 0.000 | not valid | 0 | {} |
| sae | 0.716 / 0.732 | -0.0228 / -0.0087 | **FAILED** | pass 0.941 / 0.829 | **FAILED** 8 | pass 0.838 / 0.750 | not valid | 4 | {"unnamed": 3, "N": 3, "mixed": 1, "T": 1} |

## Decomposition arms, K = 128 (9.4, 9.5)

| arm | V1 r (y1/y6) | V1 dAUROC (y1/y6) | V1 | V2 (median r / share) | V3 families | V4 (half corr / label agree) | valid | named replicated | labels |
|---|---|---|---|---|---|---|---|---|---|
| raw | 1.000 / 1.000 | -0.0000 / -0.0000 | pass | pass — / — | pass 102 | pass 0.720 / 0.829 | **valid** | 76 | {"N": 55, "mixed": 26, "T": 21} |
| pca | 1.000 / 0.999 | -0.0001 / -0.0003 | pass | pass — / — | **FAILED** 3 | **FAILED** 0.642 / 1.000 | not valid | 2 | {"unnamed": 1, "T": 1, "N": 1} |

## Q1b (9.7)
- Primary arm: **raw**.
- U adds to F, y1 (7,289 exams, 2,492 participants, 88 cancers): AUROC F 0.926 [0.890, 0.959], F + U 0.967 [0.941, 0.988], difference 0.041 [0.020, 0.067], halves 0.059 / 0.028, LR test chi² 182.32, p 0.0000.
- U adds to F, y6 (2,180 exams, 2,180 participants, 135 cancers): AUROC F 0.775 [0.730, 0.817], F + U 0.868 [0.837, 0.898], difference 0.094 [0.062, 0.127], halves 0.066 / 0.117, LR test chi² 138.83, p 0.0000.
- Group shares of lbar1 (raw): intercept 0.000 [-0.000, 0.000]; residual 0.166 [0.164, 0.168]; N 0.446 [0.442, 0.449]; mixed 0.205 [0.202, 0.208]; unreplicated 0.133 [0.131, 0.134]; T 0.050 [0.050, 0.051] (sum 1.0000).
- Group shares of lbar6 (raw): intercept -0.046 [-0.047, -0.044]; residual 0.147 [0.141, 0.153]; N 0.485 [0.481, 0.489]; mixed 0.212 [0.206, 0.217]; unreplicated 0.148 [0.145, 0.151]; T 0.053 [0.053, 0.054] (sum 1.0000).

## Q1c: stable part, T0 and T1 (9.7)
- all: 2,435 participants; r(lbar1) 0.725 [0.692, 0.758], r(lbar6) 0.722 [0.687, 0.757].
  - stable shares of lbar1: intercept -0.000 [-0.000, 0.000]; residual 0.162 [0.159, 0.164]; N 0.438 [0.432, 0.444]; mixed 0.213 [0.209, 0.218]; unreplicated 0.136 [0.134, 0.138]; T 0.051 [0.050, 0.052]
  - stable shares of lbar6: intercept -0.048 [-0.050, -0.045]; residual 0.132 [0.128, 0.137]; N 0.478 [0.473, 0.483]; mixed 0.226 [0.221, 0.232]; unreplicated 0.156 [0.153, 0.160]; T 0.054 [0.053, 0.055]
- no_cancer_within_2y_of_T0: 2,394 participants; r(lbar1) 0.719 [0.684, 0.751], r(lbar6) 0.716 [0.680, 0.749].
  - stable shares of lbar1: intercept 0.000 [-0.000, 0.000]; residual 0.161 [0.159, 0.163]; N 0.435 [0.429, 0.440]; mixed 0.216 [0.212, 0.220]; unreplicated 0.137 [0.135, 0.139]; T 0.051 [0.050, 0.052]
  - stable shares of lbar6: intercept -0.047 [-0.049, -0.044]; residual 0.129 [0.125, 0.134]; N 0.475 [0.469, 0.480]; mixed 0.229 [0.224, 0.235]; unreplicated 0.158 [0.155, 0.162]; T 0.054 [0.053, 0.055]

## Q1d / U1b: technical changes inside one exam (9.7)
- tau90 = 0.0180; SD lbar1 1.028, SD lbar6 all 0.930, baseline 0.960.
- z-fix, D5 (924 exams, 424 participants, 16 cancers): t6 mean -0.231, SD 0.454, ICC 0.870, share |Δ| ≥ 0.25 SD 0.670, flag change 0.075; U1b qualifies: yes. Intervals: share_ge_quarter_sd_lbar6 0.670 [0.638, 0.701] (halves 0.669 / 0.671); share_flag_changed 0.075 [0.056, 0.097] (halves 0.074 / 0.075); mean_delta_lbar1 -0.326 [-0.366, -0.282] (halves -0.320 / -0.332); mean_delta_lbar6 -0.231 [-0.267, -0.192] (halves -0.227 / -0.235)
- Kernel pairs (500 exams, 500 participants, 8 cancers): t1 mean 0.028, t6 mean 0.025, SD ratio t6 0.204, ICC t6 0.979, flag change 0.018. Intervals: share_ge_quarter_sd_lbar6 0.184 [0.152, 0.218]; share_flag_changed 0.018 [0.008, 0.030]; mean_delta_lbar1 0.028 [0.009, 0.049]; mean_delta_lbar6 0.025 [0.008, 0.042]

## Q2: false alarms and misses (9.7)
- tau90 0.0180 (specificity reached 0.888), tau90_F -3.968, tau_rad 0.0040.
- Classes at tau90: sybil_only 564 exams (367 participants); shared 246 exams (200 participants); form_only 475 exams (428 participants); true_negative 5,916 exams (2,264 participants)
  - sybil_only: 65 variables with q < 0.05; largest: fam29_N 5.45; fam7_N 5.37; fam46_N 4.90; fam43_N 4.79; fam32_N 4.70; fam31_N 4.56; fam52_N 4.27; fam51_N 4.18
  - shared: 71 variables with q < 0.05; largest: fam29_N 7.18; fam7_N 6.68; fam43_N 6.47; fam46_N 6.23; fam31_N 6.21; fam32_N 5.64; fam55_N 5.28; fam52_N 5.13
  - form_only: 71 variables with q < 0.05; largest: G_N 0.62; fam41_N 0.61; fam0_N 0.60; fam30_N 0.60; fam18_N 0.60; G_unreplicated 0.59; fam12_N 0.59; fam21_N 0.58
- Misses y1 (all screens, 7,289 exams, 2,492 participants, 88 cancers): missed 6, caught 82 (descriptive).
- Misses y2 (baseline, 2,470 exams, 2,470 participants, 65 cancers): missed 10, caught 55 (descriptive).
- Misses y6 (baseline, 2,180 exams, 2,180 participants, 135 cancers): missed 54, caught 81 (descriptive).

## U1a: technical removal (9.7)
- dAUROC y1 -0.0010 [-0.0032, 0.0007] (7,289 exams, 2,492 participants, 88 cancers); y6 -0.0020 [-0.0079, 0.0035] (2,180 exams, 2,180 participants, 135 cancers).
- False-alarm spread over 7 maker × kernel groups: before 0.0228, after 0.0071, ratio 0.310 [0.337, 1.360]; F 0.0199.
- Qualification: {"dauroc_y1_ok": true, "dauroc_y6_ok": true, "ratio_ok": true, "sybil_spread_gt_F": true, "qualifies": true}.

## U2: reliability flag (9.7)
- R-fixed: flagged 0.357 of y1 = 0; statistic -0.032 [-0.051, -0.013] (halves -0.043 / -0.020); Sybil sensitivity flagged 0.926 (n 27) vs unflagged 0.934 (n 61).
- R-learned: flagged 0.200 of y1 = 0; statistic 0.378 [0.340, 0.413] (halves 0.388 / 0.368); Sybil sensitivity flagged 0.986 (n 71) vs unflagged 0.706 (n 17).
- Rule that can be frozen: R-learned.

## U3: Sybil plus the form at the radiologists' sensitivity (9.7; partly seen)
- 7,289 exams, 2,492 participants, 88 cancers; target sensitivity 0.909 (tables 0.909).
- False alarms per 1,000 screens: sybil 60.1 (sens 0.909); form_F 192.8 (sens 0.909); combined_C 42.0 (sens 0.909); radiologists 338.6 (sens 0.909)
- Ratio C / better of Sybil and F: 0.699 [0.352, 1.049]; qualifies (≤ 0.80): yes.

## U4: references (9.7)
- y1 (7,289 exams, 2,492 participants, 88 cancers): Sybil 0.969 [0.949, 0.985]; probe on h 0.970 [0.953, 0.984]; family models: raw 0.972 [0.948, 0.990] (56 fam.); pca 0.966 [0.942, 0.984] (3 fam.); ica 0.535 [0.444, 0.622] (2 fam.); nmf 0.950 [0.915, 0.978] (8 fam.); sae 0.956 [0.922, 0.982] (8 fam.)
- y6 (2,180 exams, 2,180 participants, 135 cancers): Sybil 0.851 [0.816, 0.885]; probe on h 0.874 [0.839, 0.905]; family models: raw 0.864 [0.831, 0.895] (56 fam.); pca 0.843 [0.806, 0.878] (3 fam.); ica 0.553 [0.487, 0.618] (2 fam.); nmf 0.800 [0.750, 0.843] (8 fam.); sae 0.830 [0.791, 0.868] (8 fam.)

## Simple references (amendment A3)
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

## Gate 9.8
- 354 candidates; 344 hold 9.8; 344 eligible (with valid arm and qualification); 344 not partly seen. Any valid arm: yes; primary arm raw.
- Leak check: pass; data check: pass. Decision: **go to S5**.
- Full table: `results/s4/s4_gate_dev.md`.

