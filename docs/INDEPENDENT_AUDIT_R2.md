# Independent Project Audit — `imaging-sae`

**Repository:** `https://github.com/shforgh02/imaging-sae`  
**Branches Inspected:** `main` (`2bc97ff`) and `prostate-mri-plan` (`89317e8`)  
**Scope:** Independent technical, statistical, experimental, data-handling, reproducibility, and documentation audit going beyond `docs/PROMPT_REVIEW_PLAN_CHOICE.md`. All Section 7 prohibitions were strictly enforced (no unseen NLST outcomes or images read, no new test-output scripts run, no frozen files, scripts, results, or ledger modified).

---

## Executive Summary

The `Lung L2` pre-registration workflow (`c593005` → `c3578c3`, 36 verified input hashes in `s6_input_checks_pre.json`, commit-before-read discipline in `EXECUTION_LOG.md`) shows **exceptionally high confirmatory integrity** for its primary frozen hypotheses (`H1`–`H7`). However, independent code and output inspection uncovered **7 high/medium technical, statistical, and methodological vulnerabilities** that were either overlooked or understated in the repository documentation:

1. **Missing calibration validation on DCA & clinical probabilities (High).**
2. **H7 linear confounding: asymmetry, `ratio == 0` misclassification, `90%` GE dominance, and `73%` simultaneous scanner-model switches (High).**
3. **Censoring exclusion (`12%` at 6y), global-median demographic imputation, work-up bias (`83/86` `E1` cancers vs `E2` baseline `+0.026` gain), non-clustered inference in `M3`/`M4`/`M6`, and in-sample `U3` thresholding (High).**
4. **SAE/NMF failure framing omits `k=16` pass on `pooled` (with scouting `V2` caveats) and misattributes uncentered NMF $R^2 = -2.83$ (Medium).**
5. **`zfix` couples true z-resampling with `CropOrPad` un-cropping (`-600 HU` zero-padding) and ignores gantry tilt (`ImageOrientationPatient`) (Medium).**
6. **Severe reproducibility & repo hygiene debt (`D:\Shayan` hardcoded paths, gitignored `imgsae_data/`, lockfile mismatch, 5,412 committed raw JSONs) (Medium).**
7. **Unverified or inconsistently reported secondary claims (`age_scan` causality, mixed L1/L2 headline numbers, incomplete N8 checklists) (Low–Medium).**

---

## 1. Code Correctness & Slice-Spacing ("z-fix") Mechanism

| ID | Finding | Exact Citation (`prostate-mri-plan`) | Impact & Evidence |
|---|---|---|---|
| **C1** | **`zfix` couples z-resampling with `CropOrPad` un-cropping and `-600 HU` padding** | `imgsae/exploratory/lung_l2/cloud/l2_sybil_modal.py:128-138,204-233`; `imgsae/exploratory/lung_l2/cloud/image_measures.py:3-5,27` | `_volume()` sets `vs[2] = float(z_spacing)` and runs `s.resample_transform` + `s.padding_transform` (`CropOrPad((256,256,200))`). Normalized `0.0` padding equals raw value `128.1722` (~`-600 HU`, parenchyma density), not `-1000 HU` air. Shrinking z both un-crops apical/basal slices (`shp[3] > 200`) and adds `-600 HU` padded slices (`shp[3] < 200`). Although `RESULTS_L2.md:89` confirms H6 persists when `lung_cut_z == 0` (`+0.357` vs `+0.418`), the paper must explicitly separate pure resampling from `CropOrPad` boundary effects. |
| **C2** | **`slice_positions` ignores gantry tilt / oblique orientation** | `l2_sybil_modal.py:216`; `assemble_test.json:122` | True spacing uses `np.median(np.abs(np.diff(s._meta.slice_positions)))`, which reads `ImagePositionPatient[2]` only rather than projecting along the `ImageOrientationPatient` slice normal. `T_tilt == 0` on NLST test (`assemble_test.json`), but external clinical CT cohorts (e.g., LIDC or future datasets) can contain gantry-tilted scans. |
| **C3** | **Duplicate-slice scans (`ratio == 0`) misclassified as stretched in H7** | `l2_sybil_modal.py:225`; `s6_frozen_analysis.py:184,201-202`; `s6_test.json` | `l2_sybil_modal.py:225` (`want_zfix ... and spacing > 0`) skips `zfix` when `median(dz) == 0`. Yet primary H7 (`s6_frozen_analysis.py:184`) defines `st = (E2.ratio <= 0.65)`, tagging `ratio == 0` scans as stretched. Sensitivity `b_ratio0_not_stretched` (`0.295 [0.167, 0.422]` vs `0.311`) shows impact is modest on test, but `O2b` must fix `st = (ratio > 0) & (ratio <= 0.65)`. |
| **C4** | **`x4_code_audit.md` was static inspection only** | `imgsae/exploratory/lung_l2/results/x4_code_audit.md` | Static inspection of 5 open-source tools (`Sybil`, `grt123`, `juliandewit`, `MONAI`, `pylidc`) plus 1 closed repo (`LungEvaty`, uncheckable). No dynamic test harness was executed across those tools. |
| **C5** | **Missing IDC metadata handled gracefully** | `manifest_test.csv` (e.g., Siemens UID `...355713`); `l2_sybil_modal.py:225` | Blank `vg_slice_spacing_mm` / `ratio_idc` in IDC metadata are bypassed because `zfix` triggers from live DICOM headers—good engineering, but requires noting that IDC metadata tables undercount or misestimate some DICOM spacings slightly vs runtime headers. |

---

## 2. Data Handling, Splitting & Leakage

| ID | Finding | Exact Citation (`prostate-mri-plan`) | Impact & Evidence |
|---|---|---|---|
| **D1** | **In-sample test thresholding in `U3_table` & denominator inconsistency** | `s6_frozen_analysis.py:240-242`; `s4_u3.py:26-27,30-32`; `s7_added_value.py:137` | `U3_table` sets the `94.19%` sensitivity target and operating cut **in-sample on the test split** (`np.sort(score[y==1])[::-1][k-1]`), reporting `F` (`151.8` FA/1000) vs `Sybil` (`342.1`) vs radiologists (`363.5`). Furthermore, `s4_u3.py:32` divides false alarms by `len(y)` (all exams), whereas `s7_added_value.py:137` divides by `n0 = (~c).sum()` (non-cancers). In-sample `U3` cannot be presented as an out-of-sample operating comparison. |
| **D2** | **Censoring / competing-risk exclusion shrinks 6-year baseline by 12%** | `imgsae/exploratory/lung_l0/nlst_l0.py:110`; `l2_data.py:86` | `ex[f"y{y}"] = np.where(pos, 1.0, np.where(ex.fu >= YEAR * y, 0.0, np.nan))` drops participants with follow-up `< y` years (`2,278 -> 2,002` baseline exams at 6y, `-12.1%`). Without IPCW or Uno's C-index, 6-year AUROC is not directly comparable to Mikhael et al.'s survival C-index (`0.81`/`0.75`). |
| **D3** | **Global-median demographic imputation before split** | `nlst_l0.py:152` (`X[demo] = X[demo].fillna(X[demo].median())`) | Computes demographic medians across `train + dev + test + unseen` jointly prior to splitting (minor leak, easy to fix). Also `nlst_l0.py:116` fills missing `sct_long_dia` with `4.0` mm (`sct_perp_dia` filled near `:121`). |
| **D4** | **Work-up bias in `E1` vs `E4/E5` & unaddressed `E2` baseline `+0.026` gain** | `s7_added_value_test.json:35-38`; `nlst_l0.py:74-78,139-145`; `RESULTS_L2.md:126` | `RESULTS_L2.md` claims removing `res1..6`/`iso_pos` (`C2`) eliminates work-up bias. Yet **`83 of 86` (`96.5%`)** 1y cancers in `E1` were screen-detected (`can_scr == 1`), triggered by findings in `C2`. Even `E4` (`81/131`, `61.8%`) and `E5` (`22/51`, `43.1%`; `27/51` `can_scr == 4`) contain screen-detected cases, though far less immediate work-up bias (`Sybil 0.724 / 0.580` vs `C2 0.747 / 0.637`). Conversely, in **`E2` (1y baseline, `41` cancers, no `ctabc` prior-scan comparisons `gw*`/`pre*`/`att*` from `nlst_l0.py:74-78,139-145`)**, cross-fitted `M3 C1+Sybil` adds **`+0.0256 [+0.0004, +0.0544]`** (`0.927 -> 0.949`, LR `p = 1.37e-10`), which the manuscript must explicitly distinguish from `E1`/`E4`/`E5`. |
| **D5** | **Series-rule selection on test half A & unseen count divergence** | `series_rule.py:69,80`; `RESULTS_L0.md:32`; `x6_unseen_metadata.json` | `BEST_RULE = "sharp_thin"` was selected using half A of test metadata (`s0_series_rule.json`, metadata only, no outcomes). Separately, `RESULTS_L0.md` counts `11,432` unseen participants (`30,888` exams) in clinical tables vs `11,226` selected (`28,661` exams) in `x6_unseen_metadata.json` (IDC series filter). `x6_unseen_metadata.py:19-33` was verified to read zero outcome columns. |

---

## 3. Statistical Methods, Metrics, & Baselines

| ID | Finding | Exact Citation (`prostate-mri-plan`) | Impact & Evidence |
|---|---|---|---|
| **S1** | **Zero calibration checks despite prevalence shift (`1.52% -> 1.29%`)** | `s7_added_value.py:99-112`; code search across `lung_l1`, `lung_l2` | `decision_curve` (`M5`) compares Sybil's **dev-calibrated `s1`** against **uncalibrated train-fitted `sigmoid(C1_1)`** (`train` 1y prevalence `452/29,752 = 1.52%` vs `test` `86/6,674 = 1.29%`). Zero Brier score, calibration slope/intercept, or ECE checks exist anywhere in `lung_l1` or `lung_l2`. Uncalibrated probabilities directly distort Decision Curve Analysis Net Benefit. |
| **S2** | **Unclustered inference in `M4`, `M6`, and non-refit OOF bootstrap in `M3`** | `s7_added_value.py:88-94,124`; `s6_explore_test.py:34`; `l1_analysis.py:60-84` | (a) `M3_crossfit` runs 10-fold CV once on test and bootstraps fixed OOF predictions without refitting; (b) `M4_lr_sybil_given_c` uses 1-df `chi2` LR tests assuming `6,674` independent exams across `2,346` participants; (c) `M6` `removed_ci` and `s6_explore_test.py` use exam-level Clopper-Pearson intervals ignoring repeat screens per person. |
| **S3** | **H7 linear symmetry & severe vendor/scanner-model confounding** | `s6_frozen_analysis.py:110,184,201-202`; `s6_test.json:247-275`; `RESULTS_L2.md:90` | `ols_b` enforces symmetric slope `b * dst` for `dst in {-1, 0, +1}`, masking strong asymmetry: `stretched -> not` mean `-0.200` (`n=92`), `unchanged` `+0.045` (`n=4,219`), `not -> stretched` `+0.426` (`n=42`). Worse, `121/134` (`90.3%`) changed pairs involve GE, and **`98/134` (`73.1%`) simultaneously changed `tag_model`**. Although `same_scanner_model` (`n=36`) stays positive (`b = +0.347 [0.099, 0.566]`), non-GE pairs (`n=13`, `b = -0.318`) cannot be tested. |
| **S4** | **Wald p-value float64 underflow & LIDC H2 vendor heterogeneity** | `s6_frozen_analysis.py:77,80-82`; `s6_test.json:55`; `x5_lidc.json:82,104-118` | `norm.sf(...)` underflows to `0.0` in `s6_test.json` and `x5_lidc.json` (replace with `log_sf` or `< 1e-300`). In LIDC X5 (`197` scans), while H6 (`+0.395`) and `axis 0` (`-2.76 SD`) replicate across GE/Philips/Siemens, H2 is strongly vendor-dependent (`GE -0.280`, `Philips -0.006`, `Siemens +0.177`), showing non-axis-0 scanner interactions exist on clinical scans. |
| **S5** | **Sybil step-function calibrator artifact** | `EXECUTION_LOG.md` (Nov 16); `s4_u3_dev.json` | Published calibrator clamps low 1y predictions to `0.0` (`16.3%` ties at `0.000` in dev; `227` distinct `s1` values in `7,336` scans), inducing non-smoothness at `τ90 = 0.01799` (11.2% actual dev FP vs `τ_rad = 0.03389`, 6.0% dev FP). |

---

## 4. Experimental Design: SAE / NMF / Dictionary Learning

| ID | Finding | Exact Citation (`prostate-mri-plan`) | Impact & Evidence |
|---|---|---|---|
| **E1** | **S4 SAE failure driven by restrictive `k = K//16` as well as low rank** | `s4_core.py:76`; `s4_decomp_dev_sae_K64.json`; `results/r/r1_pooled_sae_K64_k16.json`; `RESULTS_R_dev.md` | S4 forced `k=4` (`K=64`) and `k=8` (`K=128`) with Matryoshka prefixes `[M//4, M//2, M]` on `h`, causing V1 failure (`r_y1 = 0.716, 0.833`). When Step R raised `k=16` on `pooled`, SAE **passed** V1 (`r_y1 = 0.995`, `recon_r2 = 0.753`), V2 (**member 0 only** scouting check: `0.852`), and V4 (`1.0`), failing only V3 (`12 < 16` families). |
| **E2** | **NMF at `pooled` formally passed V1–V4; $R^2 = -2.83$ was a clamping artifact** | `results/r/r1_pooled_nmf_K64.json`; `s4_core.py:68-70`; `RESULTS_R_dev.md` §3 | NMF `K=64` on `pooled` passed all 4 S4 criteria (`r_y1 = 0.998`, `16` families; `V2` checked across **2 members only** per `RESULTS_R_dev.md` §3), but failed held-out vector reconstruction (`R^2 = -2.833`) because `49%` of `pooled` part 2 is negative while `s4_core.py:68-70` clamped `np.maximum(h / sd, 0)` with `off = 0`. |
| **E3** | **MCCA establishes true ~11-axis shared subspace in `pooled`** | `results/r/r2_shared_pooled.json`; `r2_shared.py` | 5-member MCCA on top-30 whitened PCs recovers 11 shared axes explaining `R^2 = 0.939` of `lbar1` (`7` stable non-risk named axes). Framing the failure accurately—as **low-rank shared linear subspace (~11 axes) rather than high-dimensional polysemantic superposition** (and noting Step R's single/two-member `V2` scouting simplification)—prevents ML reviewers from attacking `k=4` choices. |

---

## 5. Reproducibility & Repository Hygiene

| ID | Finding | Exact Citation | Impact & Evidence |
|---|---|---|---|
| **R1** | **Out-of-the-box reproduction blocked by local paths & gitignored files** | `s5_hashes.py:16-17`; 15+ scripts in `lung_l1/` and `lung_l2/`; `.gitignore` | `D:\Shayan` is hardcoded in `l1_manifest.py:2`, `l2_form.py:15`, `l2_data.py:16`, `s4_core.py:14`, `s4_common.py:28,34`, `s5_axes_freeze.py:20,23`, `s6_input_checks.py:38,55-56`, `s7_added_value.py:23`, `s8_demographics.py:20`, `test_s4_scripts.py:27`, etc. Core artifacts (`heads.npz`, `sybil_ensemble_simple_calibrator.json`, `r2_shared_pooled.pkl`, `exams_test.csv`) live in gitignored `imgsae_data/`. |
| **R2** | **Lockfile mismatch between local Windows env and Modal GPU env** | `imgsae/requirements-lock.txt` vs `l1_sybil_modal.py:24-27`, `l2_sybil_modal.py:62-66` | `requirements-lock.txt` pins `torch==2.10.0+cu126` / `numpy==2.4.6`, whereas Modal inference uses `torch==1.13.1` / `numpy==1.24.1` / `pydicom==2.3.0` / `torchio==0.18.74` / `Sybil` (`d9fc81b9`) `--no-deps`. |
| **R3** | **Branch divergence & repo bloat** | `main` (`2bc97ff`, 374 files) vs `prostate-mri-plan` (`89317e8`, 6,337 files) | The active Lung Sybil paper lives entirely on a branch named `prostate-mri-plan` containing `5,412` tiny score JSONs (`lung_l1/results/scores_raw/scores/`), prostate MRI planning docs, and gitignored local exclusions (`/New report .txt`, `ucla_audit/`). |
| **R4** | **Incomplete release deliverables** | `docs/PROJECT_GUIDE.md` N8; `s6_test.json` vs `RESULTS_L2.md` | TRIPOD+AI & CLAIM 2024 checklists, standalone clean-env `s6_frozen_analysis.py` rerun, and Sybil GitHub issue/author notification are not yet completed. |

---

## 6. Unverified Claims & Missing Validations Summary

1. **"No net benefit on DCA"** (`RESULTS_L2.md:119`): Unverified for miscalibration (`C1_1` raw train logistic vs dev-calibrated `s1`).
2. **"Part of age is read from the image"** (`RESULTS_L2.md:141`): Based on unadjusted `Spearman(sybil, age_scan) = 0.24`; not conditioned on emphysema, coronary/nodule burden, or smoking history.
3. **"Adding findings without call removes work-up bias"** (`RESULTS_L2.md:126`): Unverified against `83/86` screen-detected 1y cancers in `E1` (`81/131` in `E4`, `22/51` in `E5`), and leaves `E2` baseline `+0.0256 [+0.0004, +0.0544]` (`ctabc` absent) unexplained.
4. **Attention recovery on test (`s6_attention_test.json`):** `r10_att_harm_dev.json` (`nodule_outside_box 4 -> 0`, `+6.3–7.2%` nodule attention recovery) was verified on dev only; `s6_attention_test.json` omitted `zfix` attention, and `r10_att_harm.py:57` reads `P.y1` (must be stripped before any outcome-free `O2a` run).
5. **Inconsistent headline L1 vs L2 reporting** (`PROMPT_REVIEW_PLAN_CHOICE.md` §2): Cites L1 partial A3 (`5,380` exams, `[-0.072, +0.008]`) rather than primary A1 (`0.927 vs 0.929`) and full L2 X1 (`6,674` exams, `-0.033 [-0.067, -0.003]`).
