# Project paused (2026-11-11): where we are, and why we stop for now

**For colleagues.** This note says in plain words what we did, what we found, and why we are pausing to find a better clinical question before spending more. Every number comes from committed result files (links at the end). Nothing is running, and no sealed test data has been opened.

## 1. In short
- **Goal (unchanged):** use sparse autoencoders (SAEs) to find image features a clinician can use. For example, a feature that marks cancer *beyond* what the radiologist's score already says.
- **What we tested:** two settings.
  - **CT (normal organs):** a test bench for the method. The method works, but normal organs are not a clinical question.
  - **Prostate MRI (PI-CAI):** the first clinical target.
- **Why we pause:** none of the model and data combinations open to us gives an AI that clearly knows *more than the doctor* in a way we could prove. Without that gap, an SAE can only rediscover what doctors already see.
- **Next:** we look for a setting that meets all four conditions in section 3 before spending any money. One candidate (breast cancer risk from mammograms) is being checked; see section 4.

## 2. What we did and learned

### 2.1 CT (test bench; stopped 2026-11-10)
- **The method works.** The SAE beats equally tuned alternatives (k-means, ICA, dictionary learning) by +0.10 in feature coverage (6.4 standard deviations), mainly because its features are more stable.
- **But it isn't clinical.** Simple HU values and position already recognise organs (AUROC 0.997, against 0.999 for the foundation model CT-FM), and the dataset has no tumours.
- **What we kept back:** the 555 sealed CT scans were never used.
- **Details:** `imgsae/exploratory/v2_ct/RESULTS_S1A.md`, `docs/BRIEFING_FOR_REVIEWERS.md`.

### 2.2 Prostate MRI, frozen foundation models (M0-M1; gate failed 2026-11-10)
- **Data:**
  - fresh, checksum-verified download of the PI-CAI public set (1,500 studies);
  - split by patient into a development half (753 studies used) and a sealed half (746 studies, never opened).
- **The M1 question:** does any MRI foundation model know cancer better than simple intensity?
  - The test: 4 mm tissue cells inside the prostate, each called cancer or normal.
  - The simple reference R has 66 features: T2W, ADC and DWI brightness, position, zone.
- **Answer: no.**

| Model | AUROC |
|---|---|
| R (simple intensity reference) | 0.912 |
| MRI-CORE (best model) | 0.909 |
| untrained random network | 0.894 |
| SAM | 0.879-0.894 |
| ProFound | 0.882 |

  - The fixed gate needed the model to beat R by ≥ 0.03. It came out at −0.022 [−0.038, −0.007].
  - Post hoc checks found no bug. MRI-CORE carries only a small extra signal of about +0.01.
- **Per patient** (biopsied men with PI-RADS ≥ 3): both models score AUROC 0.66, below the radiologist's PI-RADS (0.72).
- **Why:** at this scale, cancer is mostly "dark on ADC, bright on DWI", which simple intensity already captures.
- **Details:** `imgsae/mri/RESULTS_M1.md`.

### 2.3 A model trained for cancer (the lead's SegResNet; checked 2026-11-11)
- **The idea:** a model trained to find cancer should know more than a general one.
- **The model:** the lead's earlier PI-CAI model (3D SegResNet, trained on PI-CAI folds 0-2), scored on cases it did not train on (folds 3 and 4).
- **Result** (357 biopsied PI-RADS ≥ 3 men, 168 with csPCa):
  - It adds **+0.022 AUROC** over PI-RADS + PSA density + age (p = 0.0002), and almost the same after the lesion's ADC, DWI and size.
  - Real, but small. It is also unstable: +0.04 to +0.05 in one fold, about 0 in the other.
- **On the UCLA cohort** (the lead's earlier work: different scanners and coil): this kind of PI-CAI model falls to about AUROC 0.66 with sensitivity near 70%, below the radiologists.
- **Conclusion:** the gap over doctors is too small to explain with an SAE and too small to confirm with the patients available. Training a new model would cost money for a likely null result.
- **Details:** `docs/EXECUTION_LOG.md`, entries of 2026-11-11.

### 2.4 Feasibility scan of two other settings (2026-11-11, no compute)
- **Lung cancer risk from low-dose CT (Sybil on NLST): blocked.**
  - Sybil's NLST training split is not published, so we cannot find clean test cases.
  - For cancers without a visible nodule, Sybil is weak (AUROC 0.56-0.69 across studies).
- **Breast cancer risk from mammograms (Mirai on EMBED): the best fit, with two caveats.**
  - Mirai is open, was never trained on EMBED, and clearly beats clinical risk scores (5-year AUROC about 0.71-0.75, against 0.62 for Tyrer-Cuzick).
  - **Caveat 1:** part of the "why" is published. Breast asymmetry (AsymMirai, 2024) explains much of it, and a 2025 preprint (Mammo-FM) already uses an SAE on risk, though only as case examples.
  - **Caveat 2:** access needs a data-use agreement with Emory through an academic institution.
- **Details:** `docs/FEASIBILITY_SCAN_breast_lung.md`.

## 3. What a better idea must have (all four)
1. **A clear gap:** an AI model that clearly beats the clinical standard on a real outcome (not +0.02).
2. **An open question:** nobody yet knows why it beats the standard.
3. **Enough patients:** enough outcomes to find a feature and then confirm it, usually thousands.
4. **Clean data:** data the model never trained on, and on which it still works (no scanner or coil shift).

Prostate MRI with the data we have fails 1, 3 and 4.

## 4. Where we stand and what would restart the work
- **Breast (Mirai on EMBED):** restarts if the lead's institution can sign the EMBED data agreement. The question would be "what drives Mirai's risk beyond density and asymmetry?", under a written protocol and budget before any spending.
- **Lung (Sybil):** reopens only if the Sybil authors share their NLST split.
- **Ideas from colleagues are very welcome.** Especially a setting with unique data (our own centre's cases with outcomes), which avoids racing larger groups on public data.

## 5. What we keep
- **Code:**
  - SAE and consensus fitting;
  - the validity checks (stability, reproducibility, shortcuts);
  - the MRI pipeline (fetch, preprocessing, encoders, probes, statistics);
  - cloud launch with budget checks.
  - All of it is tested and reusable.
- **Data:** a verified PI-CAI copy, with its **sealed half unopened**, so it can still serve a future confirmatory test. The 555 sealed CT scans are also untouched.
- **Spend:** the whole project has used **$12.86** of Modal compute (CT $7.74, MRI $5.12). No run is open.

## 6. Document map
| What | File |
|---|---|
| This note | `docs/PAUSE_NOTE_2026-11-11.md` |
| Current state, short | `STATUS.md` |
| Every decision, in order | `docs/EXECUTION_LOG.md` |
| Prostate M0 / M1 results | `imgsae/mri/RESULTS_M0.md`, `imgsae/mri/RESULTS_M1.md` |
| Prostate plan and its three reviews | `docs/PLAN_PROSTATE_MRI_v1.md`, `docs/REVIEW*_PLAN_PROSTATE_MRI_v1.md`, `docs/RESPONSE_REVIEW*_PLAN_PROSTATE_MRI_v1.md` |
| Prostate M0-M1 protocol | `docs/MRI_M0M1_PROTOCOL.md` |
| Feasibility scan (breast, lung) | `docs/FEASIBILITY_SCAN_breast_lung.md` |
| CT results and briefing | `imgsae/exploratory/v2_ct/RESULTS_S1A.md`, `docs/BRIEFING_FOR_REVIEWERS.md` |
