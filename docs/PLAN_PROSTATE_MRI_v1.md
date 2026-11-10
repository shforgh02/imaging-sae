# Plan: clinically meaningful SAE features in prostate MRI (PI-CAI), v1, revision 2

**Status:** DRAFT, revision 2 (2026-11-10), for the lead's review. Nothing has been run. No images have been downloaded; only the PI-CAI clinical sheet (metadata) was read, to check the review's numbers.

**Revision 2** adopts the colleague review `docs/REVIEW_PLAN_PROSTATE_MRI_v1.md` (R1–R6) with refinements. The point-by-point reply, with an independent recomputation, is in `docs/RESPONSE_REVIEW_PLAN_PROSTATE_MRI_v1.md`.

Changes from revision 1:
- **New primary clinical population: the biopsy cohort.** These are men with a suspicious MRI (PI-RADS ≥ 3) who had a biopsy: 884 studies, of which 467 (53%) had no significant cancer. Every case is biopsy-proven, and PI-RADS is not part of how the outcome was decided. This removes the bias raised in R1 and matches a real clinical decision: who can safely skip a biopsy.
- **The M3 gate compares against controls (R2).** The comparison is with simple intensity features and texture features, at equal capacity (each score uses at most 5 features).
- **Token rules (R3):** partial-occupancy tokens are excluded; the token size is chosen so that ≥ 90% of lesions are captured; AUROCs weight each patient equally, with cluster bootstrap; a "clean normal tissue" sensitivity analysis is added.
- **Centre (R4):** within-centre and leave-one-centre-out results.
- **Wording and fairness (R5):** the same validity rule for every method, a rule fixed in advance for when to say "SAE features", and the centred smoothing control from the start.
- **PSA density (R6, extended):** recomputed as PSA ÷ volume for every study. The reported value is rounded and missing for 99% of one centre.

**Reviewers:** the background is in `docs/BRIEFING_FOR_REVIEWERS.md`.

## Why this plan
**The lead's decision (2026-11-10):** the goal is a clinical finding, not a methods result, so the CT confirmation is stopped. The reasons:
- TotalSegmentator has no tumour masks, only a scan-level "tumor" tag: 136 of the 555 sealed scans, at many sites.
- In Phase 1, CT-FM's scan-level tumour probe was at chance: 0.53, against 0.70 for simple HU features.

The 555 scans stay sealed.

**What carries over from CT (Stage 1a):**
- the tuned SAE and the fair baselines;
- the stability, reproducibility and shortcut checks;
- the statistics (corrected t, Holm, cluster bootstrap);
- the discipline: rules fixed before running, sanity rows, a sealed half, registration.

## 0. Decisions
| ID | Question | Recommendation / status |
|---|---|---|
| P1 | Data source | **Decided: a fresh download from the original sources.** The Modal volume `picai-dataset-vol` (another project) is not used: it holds processed images (`t2_norm`, `adc_norm`, no HBV), an `ai_heatmap` from another model, and undocumented steps |
| P2 | Encoders to try in M1 | DINOv3 ViT-L/16. Also MRI-CORE, but only if M0 confirms public weights and pretraining data that exclude PI-CAI and ProstateX. ProFound and Triad are excluded (leak) |
| P3 | Radiologists | Later (M4): 2 readers, about 1.5 h each |
| P4 | Modal budgets for M0–M1 (§6) | Approve: caps $4.10, expected about $2 |
| P5 | Licence | PI-CAI is CC BY-NC 4.0 (research use). DINOv3 is gated: the lead accepts its licence on Hugging Face |
| P6 (new) | Primary clinical population | **The biopsy cohort** (verified, PI-RADS ≥ 3; §2). All verified studies and all studies are secondary. Needs the lead's OK |

## 1. Clinical question and claims
**Primary clinical question.** Among men with a suspicious MRI (PI-RADS ≥ 3) who had a biopsy, does a feature score from the foundation model add information about significant cancer (csPCa, ISUP ≥ 2)? "Add" means beyond PSA density, age, prostate volume and PI-RADS. In PI-CAI, 467 of these 884 biopsies (53%) found no csPCa.

**Feature-level question.** Does the model's representation, split into sparse features, contain features that mark csPCa lesions, are stable and reproducible, and are not scanner or hospital shortcuts?

**Possible claims.** Each is made only if its test, fixed in advance, passes on the sealed half:

| Claim | Meaning |
|---|---|
| C1. Lesion features | At least one feature reliably marks csPCa lesions, is stable, and is not a shortcut |
| C2. Beyond intensity, token level | These features carry lesion information beyond simple T2, ADC and HBV intensity features plus position |
| C3. Clinical increment (biopsy cohort) | The feature score improves csPCa prediction beyond PSA density + age + volume + PI-RADS. It is then compared with the same-capacity intensity score and texture score: **C3a** "at least as informative as known intensity signs" (non-inferiority), or **C3b** "beyond known intensity signs" (superiority; tested only if the M3 rule below allows it) |
| C4. Readers | Radiologists recognise the features |

**Wording (R5).** We say "SAE features" only if the SAE beats the best baseline decomposition like for like, by the M2 rule. Otherwise we say "foundation-model features". The rule is fixed before M2 runs.

**Not claimed:**
- AI benchmark accuracy. The organisers note that the public set is convenience-sampled.
- Better detection than specialist AI: the PI-CAI AI scored AUROC 0.91 against 0.86 for radiologists in the reader-study subset (Saha et al. 2024).

**Expectations:**
- The features will probably match known signs (low ADC, a dark T2 spot, high HBV). C3a would show that.
- C3b, a finding beyond known signs, is a higher bar.
- On the sealed biopsy cohort (about 440 studies, about 210 positive), a difference in added value is confirmable only if it is about **0.04 AUROC** or larger (§4, M5).
- On CT, single SAE features had no advantage over the baselines. So in M2 we expect parity on lesion AUROC; any edge is more likely to be in stability.

## 2. Data
**Images.** PI-CAI Public Training and Development Dataset, Zenodo DOI 10.5281/zenodo.6624726 (v2.0):
- 1,500 biparametric MRI studies of 1,476 patients, from 3 Dutch centres, 2012–2021;
- `.mha` files, with axial T2W (plus sagittal and coronal), ADC and HBV;
- about 30 GB in 5 zip files.

Sizes and checksums are recorded when the fetch runs on Modal; Zenodo did not answer from the laptop.

**Labels.** `github.com/DIAGNijmegen/picai_labels`, pinned to commit `ce4a4723d7c46d882a6cbaacb40ed6c4be86282f` (2026-07-13). The clinical sheet `marksheet.csv` has SHA256 `23EAB237…72CF0AE`.
- **csPCa delineations:** `human_expert/resampled` (1,295 cases, 220 positive) plus `human_expert/Pooch25` (205 positives). Together they give expert labels for all 425 positives. Citing Pooch et al. 2025 is required.
- **Whole-gland masks:** AI-made (Bosma22b). Some are wrong, so they get a visual check.
- **ISUP-1 lesions are not masked.** 282 studies have an ISUP-1 lesion (228 of them csPCa-negative), so ISUP-1 cancer sits inside "normal" tissue.

**The clinical sheet**, checked independently on 2026-11-10:

| Item | Count |
|---|---|
| Studies / patients | 1,500 / 1,476 (23 patients with > 1 study) |
| csPCa positive (ISUP ≥ 2) | 425, all verified by biopsy or prostatectomy |
| Verified (has histopathology) | 1,032 (425 positive, 607 negative). By type: targeted biopsy 580, systematic 217, both 210, prostatectomy 25 |
| Unverified negatives | 468: no histology, highest PI-RADS ≤ 2 (425 with PI-RADS 2, 43 with PI-RADS 1). That is 44% of all negatives, decided by the radiologist's own read |
| **Biopsy cohort** (verified, PI-RADS ≥ 3) | **884**: 417 positive, 467 negative (prevalence 0.47). PCNN 248 (105 positive), RUMC 477 (234), ZGT 159 (78) |
| PI-RADS 3 only (verified) | 151, of which 19 positive (descriptive only; too few positives) |
| Centres: n, verified share, prevalence | PCNN 350, 100%, 0.31; RUMC 800, 61%, 0.29; ZGT 350, 56%, 0.23 |
| PI-RADS (highest per study) | Complete: 1: 137, 2: 479, 3: 151, 4: 352, 5: 381 |
| PSA / volume / PSAD missing | 2.7% / 1.8% / 30.1%. PSAD is missing for 99% of PCNN |

**PSA density (R6, extended).**
- PSAD is recomputed as PSA ÷ prostate volume for **every** study, so one definition is used throughout.
- The reported values are rounded to 2 decimals: only 73% are within 5% of PSA ÷ volume, and the reported value is missing for almost all of PCNN.
- 3.5% of studies still have no PSAD, because PSA or volume is missing. They are left out of the models that need PSAD (complete-case analysis), and the count is reported by centre.
- The reported PSAD is used as a sensitivity analysis.

**Analysis populations:**
- **biopsy cohort** (primary for M3);
- **all verified studies** (primary for model (b) per R1, here secondary);
- **all studies** (sensitivity).

M1 and M3 results are reported for each.

**Overlap.** PI-CAI contains 328 ProstateX cases. So any model pretrained on ProstateX is excluded, and ProstateX cannot serve as an external test set.

**Split:**
- 50/50 by patient (all studies of a patient go to the same half), seed 0;
- stratified by **centre × outcome group** (csPCa / verified negative / unverified negative), so the biopsy cohort is balanced between the halves;
- made from the clinical sheet only, then written and hashed before any image is downloaded.

**Our own preprocessing.** It is documented, version-controlled, and the same for every method:
1. Read the `.mha` files (SimpleITK). Resample ADC, HBV and any labels not on the T2W grid to the axial T2W grid: linear for images, nearest for masks.
2. Prepare intensities:
   - ADC keeps its physical units for the reference features;
   - for model input, fixed ADC windows and per-scan percentile scaling for T2W and HBV.
   - These are fixed in M0, before any probe runs.
3. Crop a prostate-centred box of fixed physical size, taken from the gland mask.
4. Define tokens:
   - **Labels:** lesion (expert-mask occupancy ≥ 0.5, with its ISUP grade); normal prostate (inside the gland, occupancy 0); outside the prostate.
   - **Excluded:** tokens with 0 < lesion occupancy < 0.5 are counted as neither lesion nor normal (R3a).
   - **Token size (R3c):** the candidates are 8, 6 and 4 mm in-plane, one slice deep. The largest size is used at which ≥ 90% of dev csPCa lesions (connected parts of the expert mask) have at least one token with occupancy ≥ 0.5. If none reaches 90%, 4 mm is used and the recall is reported.
   - This choice uses the dev masks only, before any model is run. Sizes below the native pixel size are reached by resampling the input; the patch size stays 16 pixels.

**Only the dev half is preprocessed and opened before registration.**

## 3. Methods
### 3.1 Encoders (candidates; M1 picks one on dev data only)
| Encoder | Input | Notes |
|---|---|---|
| DINOv3 ViT-L/16 (natural images, LVD-1689M; 1,024-d) | Slice by slice. Mode A: each sequence encoded on its own, tokens joined (3 × 1,024). Mode B: T2W, ADC and HBV as the three colour channels (1,024) | Leak-free; gated licence |
| MRI-CORE | Slice by slice | Only if M0 confirms its weights and leak-free data |
| Untrained network | As DINOv3 | Null |
| Intensity reference R | Per-token T2W, ADC and HBV histograms, mean ADC, 3 × 3 context, position within the gland | Label-free "physics" comparator |

**Leak rule.** An encoder is eligible only if its pretraining data list is published and excludes PI-CAI and ProstateX. ProFound (pretrained on PI-CAI) and Triad (TriadMR-131K includes PI-CAI and ProstateX) are excluded.

### 3.2 Decompositions
- **SAE:** BatchTopK, on a small grid on dev rep 0.
- **Baselines:** k-means, ICA, nonnegative dictionary learning, raw channels, sparse varimax, with equal tuning. The untrained network goes through the same pipeline as a null.
- **Comparisons:** single fit vs single fit, same feature count and same selection, at matched features and at all features. Key numbers are recomputed from the per-feature tables.
- **One validity rule** (M2) for every method and for the null (R5).

### 3.3 Patient scores (equal capacity; R2)
Every method's patient score is built the same way:
1. Token-level logistic regression on at most **5 features** of that method, chosen on the fit half (L1 path until 5 features are non-zero).
2. Patient score = the highest token score inside the gland. The mean of the 3 highest tokens is a sensitivity analysis.

The methods scored this way are: the SAE; the best baseline decomposition, chosen on dev by the M2 rule; R (intensity); and texture (vectorised filters, as in v1). Capacity is equal, so no score wins by having more features.

## 4. Stages and gates
Each stage gets a short protocol, with its gate fixed before it runs. The default numbers below go into that protocol unless the lead changes them.

**Common to all stages (R3d, R4):**
- Token AUROCs give each patient equal weight per class, with patient-cluster bootstrap CIs (2,000 draws).
- Folds are grouped by patient and stratified by centre × outcome group.
- Within-centre AUROCs and leave-one-centre-out results are reported. They are descriptive and do not gate.

| Stage | What | Gate (default) | If it fails |
|---|---|---|---|
| **M0. Setup** | Fetch on Modal (checksums); labels pinned; split; PSAD recomputed; dev-half preprocessing; visual QC of 20 dev cases; token size by the lesion-recall rule; leak check for MRI-CORE; check of external cohorts (Prostate158; QIN-Prostate-Repeatability for test–retest): overlap and licence | 1,500 studies read. Label counts as in §2. Split balanced. QC passes. A gland-mask rule (fix or exclude) is fixed from the QC alone. Lesion recall reported | Fix (metric-blind) and repeat |
| **M1. Does the model know cancer?** (dev half; 5-fold cross-validation) | Token probes: lesion vs normal prostate, for each encoder and mode, against R and the untrained network. Descriptive: a patient-level probe in the biopsy cohort against R; a clean-normal sensitivity (normal tokens only from studies with no ISUP-1 lesion and PI-RADS ≤ 2; R3b) | The best encoder beats R by **≥ 0.03 AUROC with lower CI > 0**, and the untrained network by ≥ 0.05. This must hold **both on all studies and on verified studies**. It also picks the encoder and mode | **Stop and report.** An SAE could then only rediscover ADC and T2 signs. The lead decides |
| **M2. Find features** (dev half; J = 3 patient halves) | All decompositions with equal tuning. Per feature: k = 1 lesion AUROC (chosen on the fit half among 425 random candidates, tested on the other half), selectivity, twin score t, stability r_pert (half-token shift with the centred smoothing control from CT; extra noise; T2W and HBV intensity scaling; a smooth bias field), and a shortcut audit (centre, scanner, b-value) | **Valid lesion feature,** the same rule for all methods: held-out lesion AUROC ≥ 0.80, r_pert ≥ 0.70, t ≥ 0.70, shortcut AUROC < 0.80, and token-level ΔAUROC over R ≥ 0.02. Gate: ≥ 1 valid feature in each of the 3 replicates. **Wording rule:** "SAE features" only if the SAE's best matched held-out lesion AUROC beats the best baseline's with CI > 0 (paired over replicates and patients); otherwise "foundation-model features" | Stop and report |
| **M3. Clinical value** (dev half, biopsy cohort) | Base model: PSAD + age + volume + PI-RADS. Increment of each patient score (§3.3) over the base, cross-fitted. Secondary: all verified studies; all studies; the base without PI-RADS; within-centre and leave-one-centre-out; biopsies avoided at 95% csPCa sensitivity; decision curve; PI-RADS 3 subgroup; studies with systematic biopsy or prostatectomy | (i) The feature score's increment over the base has lower CI > 0. (ii) Its increment minus R's, and minus texture's, has lower CI > −0.03 (non-inferior; v1's H4 margin. With dev precision (SE about 0.015), a margin of 0.02 would fail even for truly equal scores). If (i) and (ii) pass **and** the difference to R is ≥ +0.02, M5 also tests C3b (superiority over R) | Report; the lead decides |
| **M4. Readers** (when available) | 2 radiologists look at the top lesion features plus controls: intruder test plus naming (as v1 V4) | Descriptive, or a pre-set pass rule | Reported as is |
| **M5. Confirmation** (sealed half) | A registered protocol, run once: C1–C3 (and C4 if readers) | Holm over the claims. J = 5 patient halves for feature-level claims; patient bootstrap for fixed models | No claim |

**Power for M5.** The sealed biopsy cohort has about 440 studies (about 210 positive). There, the SE of a single AUROC is about 0.023, and of a paired difference about 0.013–0.017. So a difference in added value is confirmable (one-sided α 0.025, 80% power) only if it is about **0.035–0.045 AUROC** or larger. Smaller real effects would be missed.

## 5. Quality rules (lessons from CT and from the reviews)
1. **Fair comparisons:** same feature count, same selection and same model capacity for every arm; matched and all-feature versions; key numbers recomputed from the tables; an outside review before registration.
2. **Probe before SAE (M1).**
3. **Data provenance:** fresh original files, a pinned label commit and checksums; our own preprocessing only, documented and hashed.
4. **Leak rule** for encoders.
5. **Verification:** PI-RADS helped decide the reference standard for 468 negatives, so clinical results lead with the biopsy cohort (R1).
6. **Centre:** stratified folds, within-centre and leave-one-centre-out results, and a shortcut audit (R4).
7. **Patients weighted equally** in token AUROCs, with cluster bootstrap (R3d).
8. **The sealed half stays closed** until registration. The split uses only the clinical sheet.
9. **Every long job saves each finished unit.** Modal runs detached, with a budget per task.

## 6. Compute and budget
These are rough figures. A small benchmark measures each step first.

| Task (Modal) | Container | Timeout | Worst case | Expected | Budget |
|---|---|---|---|---|---|
| `mri_fetch`: download about 30 GB, verify checksums, unzip | CPU 4 cores, 8 GiB ($0.25/h) | 120 min | $0.62 | $0.2–0.4 | **$0.80** |
| `mri_prep`: preprocessing, token-size rule and QC images, dev half only | CPU 8 cores, 16 GiB ($0.51/h) | 75 min | $0.76 | $0.3 | **$0.80** |
| `mri_m1_encode`: DINOv3 (2 modes), untrained network, MRI-CORE if eligible; dev half | L4, 4 cores, 16 GiB ($1.12/h) | 60 min per launch | $1.27 per launch | $1.0 (up to about $2 if 4 mm tokens are chosen) | **$2.50** |
| **M0–M1 total** | | | | **about $2** | **$4.10** |

- **On the laptop:** the M1 probes, M2 baselines and M3 models run on the CPU.
- **Later stages:** the M2 SAE fits (about $3–5) and M5 (about $5–10) are budgeted in their own protocols.
- **Storage:** a new volume `imgsae-picai`, about 40 GB, at about $3–4 per month at the `cloud/README.md` rate; check `modal billing` first. Delete it at the end.
- **Account:** shforghani2002 has $7.74 committed, leaving $21.26 under the all-time check. That covers M0–M3; M5 may need the second account or a relaxed check (the lead decides then).

**Time:** about 3–5 weeks in total, with readers fitted in when available.

## 7. Risks
| Risk | What we do |
|---|---|
| The model adds nothing beyond ADC and T2 (M1 fails) | Stop early; try MRI-CORE, or report the negative finding |
| Verification bias (PI-RADS defined 468 negatives) | The biopsy cohort is primary; other populations are reported |
| Targeted-only biopsies (580) can miss cancer elsewhere in the gland | Sensitivity analysis on systematic biopsy or prostatectomy; stated as a limitation |
| Centre confounding (verification and prevalence differ) | Within-centre and leave-one-centre-out results; shortcut audit |
| AI gland masks are wrong | Visual QC; a fix-or-exclude rule fixed from the gland check alone |
| Small lesions lost in large tokens | The token-size rule (≥ 90% lesion recall) |
| ISUP-1 cancer inside "normal" tissue | Clean-normal sensitivity analysis (R3b) |
| Too little power for small clinical differences | The ≥ 0.04 AUROC limit is stated in advance; no claim from a non-significant difference |
| Convenience sampling | No benchmark claims; external validation later (candidates checked in M0) |
| Encoder pretraining leak | The leak rule |

## 8. Next steps (need the lead's OK)
1. Approve revision 2, including P6 (biopsy cohort primary), and the M0–M1 budgets ($4.10 in caps).
2. The token: DINOv3 licence plus a Hugging Face read token stored as the Modal secret `imgsae-hf`.
3. Then I write the M0–M1 protocol, with fixed numbers, and the code. M0 runs first, then I stop and show you the QC before M1.

## Sources
- PI-CAI public dataset, Zenodo: https://zenodo.org/records/6624726
- PI-CAI labels (commit `ce4a472`; delineations, Pooch25, marksheet, licence, ProstateX overlap, 2026 note): https://github.com/DIAGNijmegen/picai_labels
- Saha et al., Lancet Oncol 2024 (PI-CAI AI vs radiologists): https://pure.eur.nl/en/publications/artificial-intelligence-and-radiologists-in-prostate-cancer-detec/
- ProFound (pretrained on PI-CAI): https://arxiv.org/abs/2603.03961
- Triad (TriadMR-131K): https://arxiv.org/html/2502.14064v1
- MRI-CORE: https://arxiv.org/abs/2506.12186
- DINOv3 ViT-L/16 model card: https://huggingface.co/facebook/dinov3-vitl16-pretrain-lvd1689m
- Wesp et al. (SAEs on BiomedParse and DINOv3; no prostate or lesion concepts): https://arxiv.org/abs/2603.23794
