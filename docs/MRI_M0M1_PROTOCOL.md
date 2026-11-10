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
   - **5b. ProFound input** (added 2026-11-10 before any run, because ProFound needs a larger, isotropic field of view): a 1 mm isotropic grid of 64 × 256 × 256 mm (z × y × x), in the T2W direction, centred on the physical centre of the gland mask. T2W, HBV and ADC (in that channel order) are resampled onto it in one step from the originals (linear), and the gland mask by nearest neighbour. It is stored as float16 in `<key>_pf.npz`. Both crops' physical origins are recorded, so features can be mapped onto the common grid in physical coordinates.
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
**Weights**, with SHA256 recorded. Code details were read from the repositories before any encoder ran, and are corrected here (2026-11-10):
- **MRI-CORE:** code `mazurowski-lab/mri_foundation`, commit `0f4f452`.
  - Weights: `MRI_CORE_vitb.pth` from the README's Google Drive link.
  - Built with its own `build_sam_vit_b(args, checkpoint=…)`: ViT-B, 16-pixel patches, 768-d, a 256-channel neck, window 14, global attention at blocks 2, 5, 8 and 11, and `use_rel_pos=False`.
  - Features = `model.image_encoder(x)`, with x in [0, 1] (its README).
  - Its loader uses `strict=False`, so the load message is recorded. **Every image-encoder key must load** (no missing encoder keys); otherwise the arm is unusable.
  - The licence is stated as Apache 2.0 in the README; the repository has no LICENSE file. This is recorded.
- **SAM ViT-B:** `sam_vit_b_01ec64.pth`, loaded with **Meta's official `segment_anything` code** (`sam_model_registry["vit_b"]`), not MRI-CORE's builder.
  - Reason: MRI-CORE's builder sets `use_rel_pos=False` and loads with `strict=False`, so SAM's relative position embeddings would be silently dropped.
  - Input: SAM's own preprocessing, (255·x − pixel mean) / pixel std, with SAM's constants.
  - So SAM and MRI-CORE differ in weights and in this architectural detail, and the comparison is reported as MRI-CORE vs SAM as each was trained.
- **Untrained network:** the official SAM ViT-B architecture with random weights (`torch.manual_seed(0)`), with the same input as SAM.
- **ProFound:** code `pipiwang/ProFound`, branch `demo`, commit `6c37140`. The `main` branch has only a README.
  - **ViT variant** (`mae_vit_base_patch16`): input 64 × 256 × 256 (D × H × W), **patch 16 × 32 × 32**, 768-d. At 1 mm isotropic, a token is about **16 × 32 × 32 mm**.
  - Features = `forward_encoder` with mask ratio 0, CLS token dropped. They are mapped onto the common grid by linear interpolation (coarser than the grid).
  - **Preprocessing** (its `dataset.py`): channels in the order T2W, high-b (HBV), ADC; z-score per channel over non-zero voxels; no co-registration. Its pretraining code does not resample, while the paper states 1 mm isotropic, so we resample to 1 mm isotropic. The input is a 64 × 256 × 256 mm crop centred on the gland.
  - **Conv variant** (`convnextv2_tiny`, used in its downstream code): if the released ProFound-alpha weights include it, we use the stage feature map whose stride is closest to the common-grid size without being coarser. Both ProFound variants are then ProFound arms, and rule S compares the best ProFound arm with the best unexposed arm.
  - **Weights:** ProFound-alpha, pretrained, from the README's SharePoint folder (`rmapyhu…`). The demo weights folder contains fine-tuned checkpoints and is **not used** (leak rule 1). If the link cannot be downloaded without a login, the lead downloads the file in a browser. If ProFound is unusable, it is logged, and the fallback (Triad) needs a new decision.

**Correction after the first encoder check** (mri_m1_encode-014, 2026-11-10, before M1). The checkpoints were inspected with torch's safe loader; see `docs/EXECUTION_LOG.md`.
- **MRI-CORE runs as trained.**
  - Its checkpoint is a DINOv2 **teacher ViT-B/16**: class token, a 14 × 14 position embedding (trained at 224 px), final norm, chunked blocks, no layer scale, **no SAM neck**.
  - The repository's SAM-shaped loader would put the features through a **randomly initialised neck** and **drop the trained position embedding** (its loader saves it under the wrong key, and `strict=False` hides this). That path does not represent the trained model.
  - We therefore build a standard timm ViT-B/16 (global attention) and load the 150 backbone tensors strictly (chunk index removed). Every tensor is checked equal to the checkpoint, and the position embedding is resampled bicubically from 14 × 14 to 30 × 30.
  - **Input:** 480 × 480 px for the 120 mm crop, so the 30 × 30 patch tokens are exactly the 4 mm common grid. Normalisation: ImageNet mean and standard deviation, DINOv2's default. The training configuration is not released.
  - **Features:** the final-norm patch tokens, 768-d in mode B and 3 × 768 = 2,304-d in mode A.
  - **Sensitivity (descriptive):** [0, 1] input without ImageNet normalisation, as in the repository README.
- **ProFound-alpha is the ConvNeXt V2-tiny variant,** not the ViT. Its checkpoint `args` say `model = convnext`, `input_size = (64, 224, 224)`, epoch 799, mask ratio 0.6, no labels.
  - Built with its own `convnextv2_tiny` and `remap_checkpoint_keys`. Only the final pooled-output norm may be missing.
  - **Input:** the centre 64 × 224 × 224 of our 64 × 256 × 256 mm grid at 1 mm (an exact sub-crop, no resampling), with its z-score normalisation.
  - **Features (the rule above):** stage 0, stride 4 mm, 96-d, mapped onto the common grid by linear interpolation (same cell size). Stages 1–3 (8, 16 and 16 mm) are recorded and may be reported descriptively; they are not candidate arms.

**Input for MRI-CORE, SAM and the untrained network:**
- **Scaling:** ADC: `clip(ADC / 3000, 0, 1)`. T2W and HBV: `clip((x − p0.5) / (p99.5 − p0.5), 0, 1)`, with that study's percentiles (§3.6).
- **Size:** each 240 × 240 crop slice is resized to 1024 × 1024 (bilinear), so one native feature cell is 1.875 mm.
- **Mode A:** each sequence alone, copied to 3 channels; features joined (T2W, ADC, HBV).
- **Mode B:** (T2W, ADC, HBV) as the 3 channels.
- **Normalisation:** each encoder then gets its own documented input normalisation: [0, 1] direct for MRI-CORE, SAM's pixel mean and standard deviation for SAM and the untrained network.

**ProFound:** its native preprocessing, as above.

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
- MRI-CORE A (2,304-d), MRI-CORE B (768-d), SAM A (768-d), SAM B (256-d);
- ProFound stage 0 (96-d), if usable.

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
