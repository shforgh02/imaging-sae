# Lung L0: is there a gap between Sybil and the radiologist's recorded findings? **No**

- **Date:** 2026-11-12. **Cost:** none (public tables only; no images, no Modal).
- **Why:** the feasibility scan called the lung route blocked because Sybil's training split was unpublished. The split is published, so the route was re-checked against the four conditions of the pause note.
- **Code:** `nlst_l0.py`. **Result file:** `results/l0_results.json`.
- **Status:** exploratory. Nothing here was fixed in a protocol beforehand.

## 1. Inputs (public, kept out of git in `imgsae_data/nlst_public/`)

| Input | Source | SHA-256 |
|---|---|---|
| NLST clinical package for IDC (`nlst780.zip`; tables `prsn`, `screen`, `ctab`, `ctabc`, `canc`) | the copy downloaded for the feasibility scan | `11D3D388…09F344F1` |
| Sybil split, `files/Shetty_et_al(Google)_data_splits.p` | branch `train` of `github.com/reginabarzilaygroup/Sybil` | `BF58BC09…4F83B949` |

- The split file is a pickle. It is read with a restricted unpickler that allows only two numpy constructors.
- Sybil's test participants are the test set of Ardila et al. (Nature Medicine 2019, Source Data Fig. 4); the rest were split 80/20 into train and dev (`scripts/data/create_nlst_metadata_json.py` on the same branch).

## 2. Which participants are clean

The public table holds both trial arms (53,452 participants). The CT arm is the 26,453 participants with a spiral-CT screen record.

| Group | Participants | Screening exams | Exams with cancer within 1 year | Participants with a later cancer |
|---|---|---|---|---|
| Sybil train | 10,179 | 29,932 | 452 | 739 |
| Sybil dev | 2,493 | 7,362 | 88 | 149 |
| **Sybil test** | **2,347** | **6,937** | **91** | **154** |
| In no Sybil split ("unseen") | 11,432 | 30,888 | 29 | 34 |

- **The unseen participants are not a usable test set.** Sybil's sample took almost every CT-arm cancer: the unseen group has 34 cancers in 11,432 participants.
- **The clean test data are Sybil's test split:** 154 participants with cancer, 91 exams with cancer within one year.
- **Label check:** the split file lists 6,715 test series, 86 with cancer within one year. Our table-derived labels give 6,937 exams and 91. The difference is exams without a usable image series.

## 3. The radiologists' recorded findings against Sybil's published accuracy

**The comparator.** For every screen, the NLST radiologists recorded each nodule's size, margins, attenuation and location, other abnormalities such as emphysema, and the overall result. A logistic regression on those findings (39 features) plus age, sex and smoking status was fitted on Sybil's train and dev participants and scored on Sybil's test participants. Intervals are participant-bootstrap (1,000 draws).

| Outcome, on Sybil's test participants | Exams (cancers) | Recorded findings, logistic regression | Largest nodule diameter alone | Sybil, as published |
|---|---|---|---|---|
| Cancer within 1 year, baseline scans, single-scan findings | 2,344 (41) | **0.929** [0.879, 0.971] | 0.908 [0.843, 0.958] | 0.93 (Reeves et al. 2026; 2,343 scans, 41 cancers) |
| Cancer within 1 year, all screens, with comparison to earlier scans | 6,894 (91) | **0.950** [0.921, 0.973] | 0.903 [0.863, 0.939] | 0.92 [0.88, 0.95] (Mikhael et al. 2023) |
| Cancer within 2 years, baseline scans | 2,336 (61) | 0.867 [0.811, 0.915] | 0.826 [0.756, 0.888] | not looked up |
| Cancer within 6 years, baseline scans | 2,065 (140) | **0.745** [0.699, 0.790] | 0.642 [0.588, 0.694] | 0.75 [0.72, 0.78] (Mikhael et al. 2023) |
| Negative baseline screen, cancer 1 to 6 years later | 1,175 (56) | 0.666 [0.593, 0.735] | n/a | 0.59 in NLST (JTO 2024 abstract) |

Other rows of the result file:
- Gradient boosting on the same features gives about the same as the logistic regression (0.925, 0.957, 0.879, 0.750).
- Age, sex and smoking status alone: 0.60 to 0.64.
- The radiologist's positive-or-negative call alone: 0.77 to 0.79 at one year.

## 4. Reading

- **Condition 1 fails for lung, as it did for prostate.** At every horizon, a plain model of what the radiologists wrote down matches Sybil's published accuracy on Sybil's own test participants.
- **Limits of this comparison:**
  - It is not paired. Sybil's figures come from the papers, not from scores on exactly these exams. The baseline set does match Reeves et al. almost exactly (2,344 against 2,343 scans; 41 cancers in both).
  - The 6-year row uses baseline scans with at least six cancer-free years for the negatives. Sybil's 6-year figure covers all test scans with its own censoring rule.
  - Equal accuracy does not mean equal information. Whether Sybil adds anything *on top of* the recorded findings needs Sybil's scores on these scans (step L1, a paid run).
- **Not new on its own.** A 2024 conference abstract (JTO, MA18.13) already reported Sybil close to the Brock model (0.796 against 0.786 in nodules above 1.5% risk), and below PLCOm2012 on negative baseline screens.

## 5. Sources
- Sybil repository, branch `train`: https://github.com/reginabarzilaygroup/Sybil/tree/train
- Mikhael et al., J Clin Oncol 2023: https://pubmed.ncbi.nlm.nih.gov/36634294/
- Reeves et al., Radiology: Cardiothoracic Imaging 2026: https://doi.org/10.1148/ryct.260087
- JTO 2024 abstract MA18.13 (Sybil, Brock, PLCOm2012): https://www.jto.org/article/S1556-0864(24)01113-4/fulltext
