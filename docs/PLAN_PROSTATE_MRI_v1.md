# Plan: clinically meaningful SAE features in prostate MRI (PI-CAI), v1

**Status:** DRAFT for the lead's and the colleague's review, 2026-11-10. Nothing has been run, and nothing has been downloaded.

## Why this plan
**The lead's decision (2026-11-10):** the goal is a clinical finding, not a methods result, so the CT confirmation is stopped. The reasons:
- TotalSegmentator has no tumour masks. It has only a yes/no "tumor" tag per scan: 136 of the 555 sealed scans, at many different sites.
- In Phase 1, CT-FM's scan-level tumour probe was at chance: 0.53, against 0.70 for simple HU features.

The 555 scans stay sealed. CT protocol revision 2 is archived, unregistered, on branch `protocol-v2-review`.

**What carries over from CT (Stage 1a):**
- the tuned SAE and the fair baselines;
- the stability, reproducibility and shortcut checks;
- the consensus;
- the statistics (corrected t, Holm);
- the discipline: rules fixed before running, sanity rows, a sealed half, registration.

## 0. Decisions
| ID | Question | Recommendation / status |
|---|---|---|
| P1 | Data source | **Decided: a fresh download from the original sources.** The existing Modal volume `picai-dataset-vol` (from another project) is not used. It holds processed images (`t2_norm`, `adc_norm`, no HBV), plus an `ai_heatmap` from another model; its steps are undocumented. It was inspected read-only, by file names only |
| P2 | Encoders to try in M1 | DINOv3 ViT-L/16. Also MRI-CORE, but only if M0 confirms that its weights are public and its pretraining data exclude PI-CAI and ProstateX. ProFound and Triad are excluded (leak, §3.1) |
| P3 | Radiologists | Later (M4): 2 readers, about 1.5 h each |
| P4 | Modal budgets for M0–M1 (§6) | Approve: caps $4.10, expected about $2 |
| P5 | Licence | PI-CAI is CC BY-NC 4.0 (non-commercial): fine for research. DINOv3 is gated on Hugging Face, so the lead accepts its licence with their account |

## 1. Clinical question and claims
**Question.** In biparametric prostate MRI, does a foundation model's image representation, split into sparse SAE features, contain features that:
1. mark clinically significant cancer (csPCa, ISUP ≥ 2);
2. are stable, reproducible, and not scanner or hospital shortcuts;
3. add patient-level information beyond PSA density, age and prostate volume, and beyond the radiologist's PI-RADS;
4. radiologists recognise?

**Possible claims.** Each is made only if its test, fixed in advance, passes on the sealed half:

| Claim | Meaning |
|---|---|
| C1. Lesion features | At least one SAE feature reliably marks csPCa lesions, is stable, and is not a shortcut |
| C2. Beyond intensity | These features carry lesion information beyond simple T2, ADC and HBV intensity features plus position |
| C3. Clinical increment | An SAE feature score improves csPCa prediction beyond PSA density + age + volume, and beyond PI-RADS |
| C4. Readers | Radiologists recognise the features (descriptive, or a test if readers are available) |

**Not claimed:**
- **AI benchmark accuracy.** The PI-CAI organisers note that the public set is convenience-sampled and should not be used to benchmark AI systems. Our results are associations and added value within this cohort, and an external cohort comes later.
- **Better detection than specialist AI.** Supervised detection AI is already strong: in the PI-CAI reader-study subset, AUROC 0.91 against 0.86 for radiologists (Saha et al., Lancet Oncol 2024).

**A realistic expectation.** The SAE will probably find features that match known signs: low ADC, a dark T2 spot, high HBV. That alone is useful, because it shows the model uses what radiologists use. A finding that goes beyond those signs is a higher bar. M1 tells us early whether there is room for it.

## 2. Data
**Images.** PI-CAI Public Training and Development Dataset, Zenodo DOI 10.5281/zenodo.6624726 (v2.0):
- 1,500 biparametric MRI studies of 1,476 patients, from 3 Dutch centres, 2012–2021;
- `.mha` files, with axial T2W (plus sagittal and coronal), ADC and HBV per study;
- about 30 GB in 5 zip files.

Exact sizes and checksums are recorded when the fetch job runs. Zenodo did not answer from the laptop on 2026-11-10, so the fetch runs on Modal.

**Labels:** `github.com/DIAGNijmegen/picai_labels`, pinned to one commit and recorded.
- **csPCa delineations:**
  - `human_expert/resampled`: 1,295 cases (220 positive, 1,075 empty);
  - plus `human_expert/Pooch25`: the 205 positives that earlier had only AI labels;
  - together that is expert labels for all 1,500 studies, 425 of them positive.
  - Expert labels carry the ISUP grade (2–5). Citing Pooch et al. 2025 is required.
- **Whole-gland masks:** AI-made (Bosma22b) and known to contain errors (for example `11050_1001070`). They get a visual check (§4, M0).
- **Clinical sheet** (`marksheet.csv`): patient_id, study_id, mri_date, patient_age, psa, prostate_volume, psad, histopath_type, lesion_PIRADS, lesion_GS, center.
  - A missing psa, volume, psad or PI-RADS means "not reported" or "no suspicious lesion". This is handled by a rule fixed in M0.

**Overlap with ProstateX.** PI-CAI contains 328 ProstateX cases. So any model pretrained on ProstateX is excluded too, and ProstateX cannot serve as an external test set.

**Unit and split:**
- **Unit:** the patient. All studies of a patient go to the same half.
- **Split:** 50/50 by patient, stratified by centre × csPCa (a patient counts as positive if any of their studies is positive), seed 0.
- The split is made from the clinical sheet only, then written and hashed before any image is downloaded (the v1 rule).
- One half is for development (about 738 patients) and the other is sealed for the final test.

**Our own preprocessing.** It is documented, version-controlled, and the same for every method:
1. Read the `.mha` files (SimpleITK). Resample ADC and HBV to the axial T2W grid: linear for images, nearest for masks. Labels that are not on the T2W grid are resampled the same way.
2. Prepare intensities:
   - ADC keeps its physical units for the reference features;
   - for model input, fixed windows (ADC) and per-scan percentile scaling (T2W, HBV).
   - These are set in M0 before any probe runs.
3. Crop a prostate-centred box of fixed physical size, taken from the gland mask.
4. Define tokens: one per image patch, with a fixed physical size, set once in M0. Each token gets a label from the masks:
   - lesion, if its lesion occupancy is ≥ 0.5 (with its ISUP grade);
   - normal prostate, if it is inside the gland and has no lesion;
   - outside the prostate.

**Only the dev half is preprocessed and opened before registration.** The sealed half is processed after registration, with the frozen code.

## 3. Methods
### 3.1 Encoders (candidates; M1 picks one on dev data only)
| Encoder | Input | Notes |
|---|---|---|
| DINOv3 ViT-L/16 (natural images, LVD-1689M; 1,024-d) | Slice by slice. Mode A: each sequence encoded on its own, with the tokens joined (3 × 1,024, the v1 design). Mode B: T2W, ADC and HBV as the three colour channels (1,024) | Leak-free; gated licence |
| MRI-CORE (MRI, about 6.9 million slices, 18 body regions) | Slice by slice | Only if M0 confirms that the weights are public and the pretraining data exclude PI-CAI and ProstateX |
| Untrained network | As DINOv3 | Null: shows what the architecture alone gives |
| Intensity reference R | Per-token T2W, ADC and HBV histograms, mean ADC, 3 × 3 context, position within the gland | Label-free; the "physics" comparator |

**Leak rule.** An encoder is eligible only if its pretraining data list is published and excludes PI-CAI and ProstateX.
- ProFound is excluded: it was pretrained on PI-CAI plus private trial data.
- Triad is excluded: TriadMR-131K lists PI-CAI and ProstateX.
- Any other model is checked the same way before use.

### 3.2 Decompositions (the fairness rules from CT)
- **SAE:** BatchTopK, on a small grid on dev rep 0, as A2 did. The consensus is used for reproducibility, not for comparisons.
- **Baselines:** k-means, ICA, nonnegative dictionary learning, raw channels and sparse varimax, with the same number of candidate configs.
- **Fair comparisons:** every comparison between methods is single fit vs single fit, with the same feature count and the same selection. It is computed both at matched features and at all features.
- **At patient level:** a texture (radiomics) baseline, as in v1.
- **Supervised reference:** a linear probe on the same embedding. It is a ceiling, not a competitor.

## 4. Stages and gates
Each stage gets a short protocol, with its gate fixed before it runs. The default thresholds below are written into that protocol unless the lead changes them.

| Stage | What | Gate (default) | If it fails |
|---|---|---|---|
| **M0. Setup** | Fetch on Modal, checked against Zenodo's checksums; labels pinned; split from the clinical sheet; preprocessing of the dev half; visual QC of 20 dev cases (images, gland mask, lesion masks, resampling); leak check for MRI-CORE; DINOv3 licence | 1,500 studies read. Label counts as in the labels repo (425 positives; 1,295 + 205 expert files). Split balanced (centre × csPCa). QC passes. A gland-mask rule is fixed from the QC alone (fix or exclude), without looking at cancer labels | Fix (metric-blind) and repeat |
| **M1. Does the model know cancer?** (dev half; 5-fold cross-validation grouped by patient) | Token-level linear probes: lesion vs normal prostate, for each encoder and input mode, against R and the untrained network. Patient level: the highest probe score in the gland vs csPCa | The best encoder beats R by **≥ 0.03 AUROC (lower CI > 0)** and the untrained network by ≥ 0.05. This also picks the encoder and mode | **Stop and report.** An SAE could then only rediscover ADC and T2 signs. The lead decides: another encoder, or report it as a negative finding |
| **M2. Find features** (dev half; J = 3 patient halves, as Stage 1a) | SAE grid and baselines with equal tuning. Per feature: k = 1 lesion AUROC (chosen on the fit half, tested on the other), lesion selectivity, twin score t, stability r_pert (half-token shift, extra noise, an intensity offset for T2W and HBV), and a shortcut audit (centre, scanner, b-value) | At least 1 valid lesion feature in each of the 3 replicates. Valid means: held-out lesion AUROC ≥ 0.80, r_pert ≥ 0.70, t ≥ 0.70, not a shortcut (scan-mean AUROC for centre or scanner < 0.80). It must also add over R (token-level ΔAUROC ≥ 0.02) | Stop and report |
| **M3. Clinical value** (dev half) | A patient score from the frozen lesion features: the highest value in the gland, or a sparse combination of at most 5 features chosen on the fit half. Cross-fitted models for csPCa: (a) PSAD + age + volume; (b) (a) + PI-RADS. Increments of the SAE score compared with the texture baseline's and R's increments | The SAE increment over (a) has lower CI > 0. Its increment over (b), and its comparison with texture and R, are reported | Report; the lead decides |
| **M4. Readers** (when available) | 2 radiologists look at the top lesion features plus controls on a static web page: intruder test plus naming (as v1 V4) | Descriptive, or a pre-set pass rule (v1: ≥ 4 of 6 trials correct) | Reported as is |
| **M5. Confirmation** | A protocol like `SAE_PROTOCOL_v2`, registered, then run once on the sealed half. Claims C1–C3 (C4 if readers) | Holm over the claims; J = 5 patient halves within the sealed half; patient bootstrap for fixed models | No claim |

**PI-RADS.** `lesion_PIRADS` is given per lesion. Patient PI-RADS = the highest lesion score; a missing score means "no suspicious lesion" only where the sheet allows that reading. If more than 10% of dev patients still have no usable PI-RADS, model (b) becomes secondary.

## 5. Quality rules (lessons from CT)
1. **Fair comparisons:** same feature count and same selection for every arm; matched and all-feature versions; key numbers recomputed from the per-feature tables; an outside review before registration.
2. **Probe before SAE (M1):** never build features from a model that does not know the target.
3. **Data provenance:** fresh original files, pinned label version and checksums; our own preprocessing only, documented and hashed.
4. **Leak rule** for encoders (§3.1).
5. **Shortcut audit** for every feature that is claimed.
6. **The sealed half stays closed** until registration. The split uses only the clinical sheet.
7. **Every long job saves each finished unit.** Modal runs detached, with a budget per task.

## 6. Compute and budget
These are rough figures. A small benchmark measures each step before the full run.

| Task (Modal) | Container | Timeout | Worst case | Expected | Budget |
|---|---|---|---|---|---|
| `mri_fetch`: download about 30 GB, verify checksums, unzip | CPU 4 cores, 8 GiB ($0.25/h) | 120 min | $0.62 | $0.2–0.4 | **$0.80** |
| `mri_prep`: preprocessing and QC images, dev half only | CPU 8 cores, 16 GiB ($0.51/h) | 75 min | $0.76 | $0.3 | **$0.80** |
| `mri_m1_encode`: DINOv3 (2 modes), untrained network, MRI-CORE if eligible; dev half | L4, 4 cores, 16 GiB ($1.12/h) | 60 min per launch | $1.27 per launch | $1.0 | **$2.50** |
| **M0–M1 total** | | | | **about $2** | **$4.10** |

**Not on Modal:**
- the M1 probes, M2 baselines and M3 models run on the laptop CPU;
- the M2 SAE fits run on the L4, at about $3–5, budgeted in the M2 protocol;
- M5 is about $5–10, budgeted in its protocol.

**Storage:** about 30 GB raw plus about 10 GB processed on a new volume `imgsae-picai`. That is about $3–4 per month at the rate in `cloud/README.md`; check `modal billing` first. Delete it at the end of the project.

**Account:** shforghani2002 has $7.74 committed. Under the ledger's all-time $29 check, $21.26 is left. That is enough for M0–M3 (about $5–10). M5 may need the second account, or the all-time check relaxed (the lead decides then).

**Time:** M0 2–3 days; M1 2–3 days; M2 3–5 days; M3 2–3 days; M5 about 1 week. That is about 3–5 weeks, with readers fitted in when available.

## 7. Risks
| Risk | What we do |
|---|---|
| The model adds nothing beyond ADC and T2 intensities (M1 fails) | Stop early (cheap). Try MRI-CORE, or report the negative finding |
| AI gland masks are wrong | Visual QC in M0; a fix-or-exclude rule fixed from the gland check alone |
| PI-RADS is incomplete | The M0 completeness rule; model (b) becomes secondary if needed |
| Convenience sampling | No benchmark claims; external validation later, on a cohort that does not overlap PI-CAI or ProstateX |
| Encoder pretraining leak | The leak rule (§3.1) |
| Several studies per patient | Split by patient |
| Shortcut features (centre, scanner) | The shortcut audit is part of the validity rule |

## 8. Next steps (need the lead's OK)
1. Approve this plan (or edit it), and the M0–M1 budgets ($4.10 in caps).
2. Accept the DINOv3 licence on Hugging Face and provide a read token as a Modal secret.
3. Then I write the M0–M1 protocol, with its gates and fixed numbers, and the code. M0 runs first (fetch, split, dev-half preprocessing, QC), then I stop and show you the QC before M1.

## Sources
- PI-CAI public dataset, Zenodo: https://zenodo.org/records/6624726
- PI-CAI labels (delineations, Pooch25, marksheet, licence, ProstateX overlap, 2026 note): https://github.com/DIAGNijmegen/picai_labels
- Saha et al., Lancet Oncol 2024 (PI-CAI AI vs radiologists): https://pure.eur.nl/en/publications/artificial-intelligence-and-radiologists-in-prostate-cancer-detec/
- ProFound (pretrained on PI-CAI): https://arxiv.org/abs/2603.03961
- Triad (TriadMR-131K): https://arxiv.org/html/2502.14064v1
- MRI-CORE: https://arxiv.org/abs/2506.12186
- DINOv3 ViT-L/16 model card: https://huggingface.co/facebook/dinov3-vitl16-pretrain-lvd1689m
- Wesp et al. (SAEs on BiomedParse and DINOv3, TotalSegmentator slices; no prostate or lesion concepts): https://arxiv.org/abs/2603.23794
