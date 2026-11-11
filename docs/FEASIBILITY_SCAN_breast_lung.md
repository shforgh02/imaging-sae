# Feasibility scan: SAE on cancer-risk models (breast: Mirai; lung: Sybil)

- **Date:** 2026-11-11.
- **Requested by:** the lead, after the prostate route was found too weak (`docs/EXECUTION_LOG.md`, 2026-11-11).
- **Method:** no-cost desk check against primary sources (GitHub READMEs, dataset pages, papers). The public NLST clinical package was downloaded and read.
- **Spend:** no compute.
- **Unverified items** are marked as such.

## Conditions for an SAE study to give a clinical finding

1. A model that clearly beats the clinical standard on a real outcome.
2. The reason it beats the standard is not yet known.
3. Enough patients with outcomes to find, then confirm, a feature.
4. Data the model has not been trained on, and on which it works.

## Lung: Sybil on NLST. **Not recommended now**

- **Model** (verified): MIT licence; checkpoints on GitHub releases and Google Drive. It takes one axial LDCT.
- **Performance:**
  - Paper: 1-year AUC 0.92 / 0.86 / 0.94 (NLST / MGH / CGMH); 6-year C-index 0.75 / 0.81 / 0.80.
  - Without visible nodules the signal is weak:
    - NLST with nodules removed: 6-year AUC 0.69;
    - three screening cohorts, no baseline nodule: 0.65;
    - Sybil-Epi comparison: Sybil 0.64 (CHEST 2026);
    - "future" cancers in an Asian never- or light-smoker cohort: 0.56 (Radiology).
  - Much of what Sybil "predicts" is nodules that radiologists also see. This fails condition 2.
- **Leakage (blocker, condition 4):**
  - Sybil was trained on NLST, and the README and training docs do not publish the train/dev/test split.
  - Any NLST participant may have been in training. The only external sets (MGH, CGMH) are not public.
  - The route reopens only if the authors share the split.
- **Data** (verified):
  - NLST CT is public under CC BY 4.0: 26,254 participants, 73,116 studies, about 11 TB, no application.
  - The public clinical package (`package-nlst-780`) has tables `prsn`, `canc`, `ctab`, `ctabc` and `screen`. They include `candx_days`, `cancyr` and `can_scr` (2,058 lung cancers across both arms) and per-screen abnormalities (size, margins, attenuation, location).
  - Smoking detail is limited to `cigsmok`, so PLCOm2012 needs the CDAS application.
- **Prior SAE work:** none found on Sybil or on lung CT.

## Breast: Mirai on EMBED. **Best fit, with two serious caveats**

- **Model** (verified): MIT licence; weights in the OncoServe Docker container.
  - Validated on Hologic only; needs all four "For Presentation" views (L/R CC and MLO).
  - Trained on MGH data only, so EMBED (Emory) is external.
- **Performance and gap over the clinic:**
  - Paper and multi-site validation: C-index 0.75-0.81.
  - 5-year AUC 0.62 for Tyrer-Cuzick at MGH.
  - Mayo 2026 (JNCI): Mirai C-index 0.71 against 0.59-0.68 for clinical models.
  - On EMBED (AsymMirai paper, 81,824 patients): Mirai 5-year AUC 0.71; AsymMirai 0.66.
  - Condition 1 met: a much larger gap than prostate's +0.02.
- **What is already known about why** (condition 2, partly taken):
  - **AsymMirai** (Radiology 2024): left-right asymmetry reproduces much of Mirai (correlation about 0.69; 5-year AUC 0.66 vs 0.71).
  - **Mammo-FM** (arXiv 2512.00198, Nov 2025 / Apr 2026; Batmanghelich lab with Emory co-authors):
    - trains a Matryoshka SAE on its own mammography foundation model;
    - links the SAE features to a Mirai-distilled risk score with Shapley values;
    - shows case-level heatmaps and report sentences.
    - Not done: no systematic list of risk features, no radiologist review, no external validation of the features. Code and weights are "to be released".
  - **The remaining question:** what in Mirai's risk is not explained by density and asymmetry, and does it replicate?
- **Data** (verified):
  - EMBED open release on AWS: 22,382 patients, 76,373 exams (72% screening), 480,323 images (2D + C-view; no DBT).
  - Hologic 92%, GE 6%, Fujifilm 2%.
  - Longitudinal: all of a patient's exams over time.
  - Pathology outcome `path_severity` (0 invasive cancer, ..., 5 negative).
  - Access through a data-use agreement at data.hitilab.com: non-commercial research, academic or non-profit institutions. AWS egress is waived.
  - The full EMBED (about 110,000 patients) is case-by-case after IRB approval.
  - **Unverified:** the number of future cancers in the open subset, and whether age and BI-RADS density are in the open tables (expected).
- **Caveats:**
  1. **Access:** it needs an agreement with a US institution through your academic institution. Check first whether your institution can sign it.
  2. **Competition:** the EMBED owners' collaborators (Mammo-FM) are working on the same question with about 140,000 patients.
- **Cost:** Mirai inference is cheap; data transfer dominates. To be priced after access, on the screening exams actually needed.

## Bottom line

- **Lung:** blocked by unknown training data, and its beyond-nodule signal is weak.
- **Breast:** the only candidate that meets conditions 1, 3 and 4. Condition 2 is partly taken, so the study must target what lies beyond density and asymmetry.
- **First step:** check the data-use agreement (eligibility of the lead's institution). No money is needed before that.
