# M0–M1 protocol: prostate MRI (PI-CAI), fixed before running

**Fixed:** 2026-11-10, before any PI-CAI image is downloaded. It is committed to git before the first job.

**Plan:** `docs/PLAN_PROSTATE_MRI_v1.md`, revision 4, approved by the lead on 2026-11-10 ("OK"), including P6 (biopsy cohort primary) and the M0–M1 budgets.

**Scope:** M0 (setup and checks) and M1 ("does the model know cancer?"), on the dev half only. Nothing here is confirmatory.

**Code:** `imgsae/mri/`. **Volume:** Modal volume `imgsae-picai` (account shforghani2002).

## 1. Split (M0.1, laptop, clinical sheet only)
**Input:** `picai_labels` at commit `ce4a4723d7c46d882a6cbaacb40ed6c4be86282f`, file `clinical_information/marksheet.csv`. The script downloads it and checks SHA256 `23EAB23790886258440B4AF2842733332003F2C59F0A007B1E7B6B44572CF0AE`; on a mismatch it stops.

**Patient table:**
- **Outcome group:** csPCa if any of the patient's studies has `case_csPCa = YES`; else "verified negative" if any study has a `histopath_type`; else "unverified negative".
- **Centre:** must be the same for all of a patient's studies; if not, stop.

**Strata:** centre × outcome group, which gives 9 strata.

**Rule** (the same as `p1_fit.halves`):
- `rng = numpy.random.default_rng(0)`.
- For each stratum, in sorted order, permute the sorted patient IDs with `rng.permutation`.
- The first `(n + rng.integers(0, 2)) // 2` patients go to **dev**; the rest are **sealed**.

**Output:** `imgsae/mri/data/split.json` (patients and studies per half, counts per stratum), its SHA256 in `imgsae/mri/data/SHA256SUMS`. Both are committed **before** the fetch job starts.

**Check:** dev and sealed patient counts differ by ≤ 1 in every stratum.

## 2. Fetch (M0.2, Modal CPU, task `mri_fetch`)
**Images:** Zenodo record 6624726.
- The job reads the record's file list (names, sizes, MD5) from the Zenodo API and downloads every file to `/raw/zenodo/`, checking each file's MD5.
- A file already present with the right MD5 is skipped. Each finished file is committed to the volume at once.
- The manifest goes to `/raw/zenodo/manifest.json`.

**Labels:** the GitHub archive of `picai_labels` at the commit above, with its SHA256 recorded. It is extracted to `/raw/labels/`.

**No image is opened.** Zip central directories are read only to index member names.

**Checks:**
- every MD5 matches;
- the index has T2W, ADC and HBV for all 1,500 studies;
- `marksheet.csv` in the archive has the SHA256 of §1.

## 3. Preprocessing (M0.3, Modal CPU, task `mri_prep`, dev studies only)
Each study is processed on its own and saved at once to `/prep/dev/<patient>_<study>.npz`, with a small JSON. A study already saved is skipped.

1. **Read** T2W (axial), ADC and HBV. Each `.mha` is extracted from its zip to local temporary disk, read with SimpleITK, then deleted. Spacing, size, origin and direction are recorded.
2. **Masks:**
   - **Lesion:** `human_expert/resampled/<key>.nii.gz` if present, else `human_expert/Pooch25/<key>.nii.gz`. Positives have exactly one of the two; negatives have the resampled one, which is empty.
   - **Gland:** `whole_gland/AI/Bosma22b` and `Guerbet23`.
   - **Zones:** `zonal_pz_tz/AI/HeviAI23` and `Yuan23` (1 = PZ, 2 = TZ).
   - Any mask not on the T2W grid is resampled onto it (nearest neighbour). Each mask's unique values, and whether it was resampled, are recorded.
   - Lesion voxels are those with value ≥ 1 after resampling. Lesion grades are not taken from voxel values, because Pooch25's coding is not documented. Grades come from `case_ISUP` in the clinical sheet.
3. **Final grid:** the T2W slices, at 0.5 × 0.5 mm in-plane.
4. **One-step resampling:** T2W, ADC, HBV and every mask are resampled onto the final grid in physical coordinates (linear for images, nearest for masks, default value 0). So ADC and HBV are interpolated once, not first onto T2W and then again in-plane.
5. **Crop:** 120 × 120 mm in-plane (240 × 240 pixels), centred on the in-plane centroid of the Bosma22b gland mask over all its slices.
   - Slices run from the first to the last gland slice, plus one slice on each side (clipped to the volume).
   - Pixels outside the image are set to 0 and marked in a validity mask.
   - If Bosma22b is empty, Guerbet23 is used. If both are empty, the study is excluded and logged.
6. **Intensity statistics** (label-blind):
   - ADC percentiles 1, 50 and 99 inside the gland;
   - T2W and HBV percentiles 0.5 and 99.5 inside the crop's valid pixels.

   They are stored; the scaling itself is applied at encode time (§5).
7. **Cells** for each candidate token size s ∈ {8, 6, 4} mm: s × s mm in-plane cells (16, 12 or 8 pixels) aligned to the crop corner, one slice deep. Per cell we store:
   - lesion occupancy (share of pixels);
   - gland occupancy for each gland mask;
   - PZ and TZ occupancy for each zone model;
   - valid share.
8. **Lesions:** 3D connected components of the lesion mask (26-connectivity). For each component we store:
   - its volume in ml;
   - for each s, whether it is **captured**: at least one cell has lesion occupancy ≥ 0.5 and overlaps this component.

   Components smaller than 0.02 ml (about a sphere of 3.4 mm diameter) are counted and reported, but not used for recall.
9. **QC metrics:**
   - gland Dice of Bosma22b vs Guerbet23;
   - zone Dice = the mean of Dice(PZ) and Dice(TZ) between HeviAI23 and Yuan23.

   Both are on the cropped 0.5 mm grid.
10. **QC images (PNG):**
    - **(a) Random check:** 20 random dev studies (`default_rng(0)` over the sorted dev study keys). Mid-gland slice: T2W, ADC and HBV, with the gland, zone and lesion outlines.
    - **(b) Flagged:** every study with gland Dice < 0.8 or zone Dice < 0.7. T2W with both gland outlines and both zone outlines **only, no lesion outlines**.

## 4. M0 decisions (rules fixed now)
| Decision | Rule |
|---|---|
| ADC units | If the dev median of the gland ADC 50th percentile is between 500 and 3,000, the units are 10⁻⁶ mm²/s and the window is 0–3,000. Otherwise stop and ask the lead |
| Token size | For each source (Pooch25, resampled), over dev positives of that source: the largest s with lesion recall ≥ 0.90. The **smaller** of the two is used. If a source reaches 0.90 at no size, 4 mm |
| Outline materiality | **RUMC dev positives only.** For each `case_ISUP` grade with ≥ 5 studies in each source: the ratio of median total lesion volume per study, Pooch25 / resampled. Materiality ratio = the geometric mean of the per-grade ratios, each weighted by the smaller of its two study counts. **Outside 0.8–1.25** means cross-centre token-level results are labelled "annotation-dependent", and the clinical claim rests on patient-level M3. A bootstrap CI is reported (descriptive) |
| Gland and zone QC | For each flagged study (image (b), no lesion outlines), the visual check decides: **keep Bosma22b, use Guerbet23, or exclude.** Each decision is logged with its reason before M1, for the lead to review |
| Exclusions | Only for: a missing or unreadable sequence, empty gland masks, or the QC decision. Never based on cancer labels |

**M0 checks** (the plan's gate):
- 1,500 studies indexed;
- label counts as in plan §2 (220 resampled-positive and 205 Pooch25-positive overall; the dev counts are reported);
- split balanced;
- QC rule applied;
- lesion recall reported per source;
- materiality decided;
- every encoder loads with its documented output shape (§5).

## 5. Encoders (M0.5, Modal L4, task `mri_m1_encode`)
**Weights**, with SHA256 recorded:
- **MRI-CORE:** `MRI_CORE_vitb.pth` from the README's Google Drive link; code from `mazurowski-lab/mri_foundation` at a pinned commit.
- **SAM ViT-B:** `sam_vit_b_01ec64.pth` from `dl.fbaipublicfiles.com`. It is loaded into the same ViT-B image-encoder code, so SAM and MRI-CORE differ only in weights.
- **Untrained network:** the same architecture with random weights (`torch.manual_seed(0)`).
- **ProFound:** code from `pipiwang/ProFound` at a pinned commit; weights from its README link.
  - We identify the self-supervised encoder checkpoint (leak rule 1), its patch size, its embedding size and its preprocessing from the code.
  - If the link needs a login, the lead downloads the file. If ProFound is unusable, it is logged, and the fallback (Triad) needs a new decision.

**Input for MRI-CORE, SAM and the untrained network:**
- **Scaling:** ADC: `clip(ADC / 3000, 0, 1)`. T2W and HBV: `clip((x − p0.5) / (p99.5 − p0.5), 0, 1)`, with that study's percentiles (§3.6).
- **Size:** each 240 × 240 crop slice is resized to 1024 × 1024 (bilinear), so one native feature cell is 1.875 mm.
- **Mode A:** each sequence alone, copied to 3 channels; features joined (T2W, ADC, HBV).
- **Mode B:** (T2W, ADC, HBV) as the 3 channels.
- **Normalisation:** each encoder then gets its own documented input normalisation, recorded in M0. SAM's ViT-B expects SAM's pixel mean and standard deviation; MRI-CORE documents [0, 1] input.

**ProFound:** its native preprocessing (1 mm isotropic, 3 channels, its normalisation), recorded exactly.

**Common grid:** every feature map is mapped onto the s × s mm cells:
- **Exact area-weighted averaging** where its cells are finer: the overlap fractions per axis give the weights.
- **Linear interpolation** where they are coarser.
- 3D maps (ProFound) are averaged over the T2W slice thickness.

**Storage:** cells with Bosma22b (or the QC-chosen) gland occupancy > 0, dilated by one cell, as float16.

**Benchmark** (the first 10 studies of the random QC list):
- time and peak memory for each arm;
- sanity: shapes as documented, all values finite, no constant channels, and MRI-CORE features ≠ SAM features.

The encode launches for M1 are then sized from the measured times, inside the $5.00 cap.

## 6. M1 (fixed now)
**Tokens:** the common grid at the M0 size s.
- **Lesion:** lesion occupancy ≥ 0.5.
- **Normal:** gland occupancy ≥ 0.5 and lesion occupancy = 0.
- **Excluded:** 0 < lesion occupancy < 0.5.
- Other cells are not used.

**Samples:** all lesion tokens, and up to 200 normal tokens per study, drawn with `default_rng(int(study_id))`.

**Arms** (5 candidates):
- MRI-CORE A (768-d), MRI-CORE B (256-d), SAM A, SAM B;
- ProFound (its native dimension), if usable.

**Comparators:** the untrained network (mode B) and R.

**R (66 features per token):**
- for each of T2W, ADC and HBV: a 16-bin normalised histogram (ADC over 0–3,000; T2W and HBV over the study's [p0.5, p99.5]), plus mean and SD;
- 3 × 3 in-plane context: mean and SD of each channel's cell means over the 8 neighbours;
- position: x and y relative to the gland's bounding box, and slice position relative to the gland's extent;
- zone: one-hot PZ / TZ / uncertain. PZ or TZ only if both zone models give that zone the larger occupancy in the cell; otherwise uncertain.

**Probe**, the same for every arm and for R:
- StandardScaler fitted on the training folds;
- `LogisticRegression(C = 1.0, class_weight = "balanced", max_iter = 1000)`;
- OMP/MKL threads = 4 on the laptop.

**AUROC:**
- **Patient-weighted:** each token's weight = 1 / (the number of tokens of its class for that patient), so each patient counts equally within each class (`roc_auc_score` with `sample_weight`).
- **CIs:** patient-cluster bootstrap, 2,000 draws, percentile.

**Folds:** 5 outer folds at patient level, stratified by centre × outcome group (`StratifiedKFold`, `shuffle = True`, `random_state = 0` on the patient table). Inner folds use the same rule on the training patients.

**Rule S:**
- Δ(arm) = AUROC(arm) − AUROC(R).
- U = the unexposed arm with the highest Δ.
- ProFound is chosen only if Δ(ProFound) − Δ(U) ≥ 0.02 and its 95% cluster-bootstrap lower bound is > 0.

**Nested cross-validation:**
- Rule S is applied inside each outer fold, using its 4 training folds.
- The chosen arm, R and the untrained network are refit on those folds and scored on the held-out fold.
- The scores are pooled over the outer folds.

**Gate:** on the pooled nested scores, Δ(chosen) ≥ 0.03 with lower 95% CI > 0, **and** Δ(chosen vs the untrained network) ≥ 0.05 (point estimate; CI reported). This must hold **both** on all studies and on verified studies. In the verified analysis, normal tokens come only from studies with histopathology; lesion tokens are all verified anyway.

**If the gate fails:** stop and report; the lead decides.

**Arm for M2:** chosen by rule S on the full dev 5-fold cross-validation.

**Descriptive outputs:**
- every arm's AUROC and Δ;
- MRI-CORE vs SAM;
- within-zone AUROCs (PZ, TZ);
- within-centre AUROCs and leave-one-centre-out results, with the outline caveat;
- AUROCs by outline source within RUMC;
- the clean-normal sensitivity (normal tokens only from studies with no ISUP-1 lesion and PI-RADS ≤ 2);
- the per-slice min–max sensitivity for MRI-CORE and SAM;
- a patient-level probe in the biopsy cohort (the highest gland-token probe score vs csPCa, against R).

## 7. Budgets and saving
| Task | Cap | Use |
|---|---|---|
| `mri_fetch` | $0.80 | CPU 4 cores, 8 GiB, timeout 120 min |
| `mri_prep` | $0.80 | CPU 8 cores, 16 GiB: a 5-study smoke run (timeout 15 min), then the full run (timeout 60 min) |
| `mri_m1_encode` | $5.00 | L4, 4 cores, 16 GiB, launches of ≤ 60 min |

- Every launch passes `budget.py check` and uses `modal run --detach`.
- Every finished unit (file, study, encoder batch) is written to the volume at once.
- Ledger runs are closed from the measured container minutes.

## 8. Outputs
- `imgsae/mri/data/split.json`;
- `imgsae/mri/results/m0_*.json`;
- QC images in `imgsae/mri/results/qc/` (PNG, not in git);
- `imgsae/mri/RESULTS_M0.md`;
- an entry in `docs/EXECUTION_LOG.md`.

**After M0 the work stops** for the lead to review the QC, the token size and the materiality decision. M1 runs only after that.
