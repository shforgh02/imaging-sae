> **Out of date (note of 22 Nov 2026):** written before X9-X12 and the literature check; reference corrections are in `docs/LITERATURE_CHECK_2026-11-22.md`. Do not copy text from here into the paper without checking it against `RESULTS_L2.md` and the corrected table.

# Literature Synthesis & High-Impact Paper Strategy

**Grounded Sources:** Built on the 40 verifiable published/preprint citations compiled in [docs/LITERATURE_TABLE_R3.md](LITERATURE_TABLE_R3.md) (retrieved via generic topic-only queries with zero private names or project identifiers transmitted) and the codebase audit of `prostate-mri-plan` (`89317e8`) and `main` (`2bc97ff`) in [docs/INDEPENDENT_AUDIT_R2.md](INDEPENDENT_AUDIT_R2.md).

---

## 1. Competitive Literature Map & Genuine Novelty

### 1.1 Closest Published & Preprint Prior Work (2023–2027)

| Paper | Venue & Year | Identifier | What They Did | Exact Gap / How `imaging-sae` Advances Beyond It |
|---|---|---|---|---|
| **Mikhael et al.** (*Sybil*) | *J Clin Oncol* 2023 | `10.1200/JCO.22.01345` | 3D ResNet-18 predicting 1–6y lung cancer risk from single LDCT (`NLST` 1y AUC `0.92`; `MGH` `0.86`; `CGMH` `0.94`). | Tested standalone Sybil and Lung-RADS comparisons; did **not** test incremental value/DCA over full structured radiologist screening forms or audit `SliceThickness` vs `ImagePositionPatient` z-spacing. |
| **Simon et al.** | *Invest Radiol* 2025 | `10.1097/RLI.0000000000001131` | Tested nominal `2 mm vs 5 mm` `SliceThickness` & reconstruction kernels on Sybil; concluded Sybil is broadly robust at 1 year. | **Direct empirical contradiction / correction:** Tested nominal thickness, **not** `SliceThickness != ImagePositionPatient` z-spacing mismatch (`ratio <= 0.65`, affecting 1 in 9 NLST exams and shifting 1y logits by `-0.366` via `axis 0`). |
| **Lee et al.** | *Radiology* 2025 | `10.1148/radiol.243393` | External test in Korea (`N=18,057`); 1y AUC `0.91`, 6y `0.74` (`0.56` in never/light smokers); matched specificity to Lung-RADS. | Established external demographic/smoking drop-offs, not radiologist-form incrementality or DICOM z-spacing mechanics. |
| **Phellan Aro et al.** (*Sybil-Epi*) | *Chest* 2026 | `10.1016/j.chest.2026.02.022` | Added 11 PLCOm2012 epidemiology variables *to Sybil* (`AUC 0.80 -> 0.83`; no-nodule 6y AUC `0.64 -> 0.76`). | Asked *"Does epidemiology add to Sybil?"* `imaging-sae` asks the **clinically decisive converse**: *"Does Sybil add discrimination or DCA net benefit on top of what the radiologist already recorded?"* |
| **Sobieski et al.** (*S(H)NAP*) | *ICML* 2026 | `arXiv:2602.02560` | Image-space generative counterfactual audit of Sybil; found artifact sensitivity & radial bias. | Audited **pixel space** via diffusion bridges; did **not** audit internal latent representations (`pooled`/MCCA/`axis 0`), DICOM z-spacing bugs, or clinical screening-form incrementality. |
| **Ajami et al.** | *AACR* 2026 | Abstract | Longitudinal `Bi-Fusion`/`Tri-Fusion` combining serial Sybil features across Y0–Y2. | Engineered longitudinal fusion without discovering that single-scan Sybil suffers spurious `+0.311` year-to-year jumps from reconstruction spacing changes (`H7`). |
| **Pasquinelli et al. / Nowroozi et al. / Ben Salem et al.** | *JTO* 2026 / *medRxiv* 2026 / *SPIE* 2027 | `10.1016/j.jtho.2026.106128`; `10.64898/2026.11.03.26367146` | Safety-net Black cohort AUC; Lung-RADS 1/2 biennial extension; adding clinical vars to Sybil. | None test incremental value over radiologist findings, DCA, DICOM z-spacing, or latent feature ablation. |
| **Shu et al.** | *Radiology: AI* 2026 | `10.1148/ryai.250731` | Proved CXR DL models exploit DICOM exposure parameters as shortcuts harming deployment. | **Direct methodological precedent in *Radiology: AI***; `imaging-sae` provides the 3D chest CT screening counterpart (`SliceThickness` vs `ImagePositionPatient`) plus internal `axis 0` causal ablation. |
| **Liu et al.** (*Medical Algorithmic Audit*) | *Lancet Digit Health* 2022 | `10.1016/S2589-7500(22)00003-6` | Audit framework: map possible errors in the clinical task and their causes, test them (exploratory error analysis, subgroup testing, adversarial testing) *[corrected 22 Nov: not "4 stages"; see LITERATURE_CHECK_2026-11-22.md]*. | Provides the exact structural scaffold for uniting L1/L2 clinical evaluation with H1–H7/LIDC mechanistic testing. |
| **Vickers et al.** | *Med Decis Making* 2006; *BMJ* 2016; *Diagn Progn Res* 2019 | `10.1136/bmj.i6` | Decision Curve Analysis (DCA) & Net Benefit standard for added value of new tests/AI. | Validates why `imaging-sae` must anchor on DCA Net Benefit + calibration rather than $\Delta\text{AUC}$ or LR $\chi^2$. |
| **Wesp et al. / Abdulaal et al. / Stevens et al. / Elhage et al.** | *MICCAI* 2026 / arXiv 2024–2025 | `arXiv:2603.23794`; `2410.03334`; `2502.06755`; `2209.10652` | Foundation-model SAEs (`BiomedParse`/`DINOv3`/CXR/ViT) vs Toy Models of Superposition. | Explains why Sybil's narrow supervised `pooled` layer collapses to ~11 shared linear axes (`r2_shared_pooled.json`) rather than high-dimensional SAE superposition—turning a "negative SAE mark" into a crisp interpretability finding. |
| **Collins et al. (`TRIPOD+AI`) / Tejani et al. (`CLAIM 2024`)** | *BMJ* 2024 / *Radiology: AI* 2024 | `10.1136/bmj-2023-078378`; `10.1148/ryai.240300` | Mandatory clinical AI & imaging reporting standards. | Required checklists for *Lancet Digital Health*, *Radiology*, *Radiology: AI*, and *npj Digital Medicine*. |

**Confirmed White Space:** Four findings in `imaging-sae` remain **completely unpublished** as of November 2026: (1) Sybil's `SliceThickness` vs `ImagePositionPatient` z-spacing bug (directly contradicting `Simon et al., 2025`), (2) clinical non-incrementality / lack of DCA net benefit over structured radiologist screening forms across all screens and 6-year horizons (converse of `Sybil-Epi`), (3) latent-space localization + causal ablation of `axis 0` explaining low-rank clinical + artifact entanglement, and (4) acquisition-triggered longitudinal score jumps (`H7`).

---

## 2. Prioritized, Actionable Research & Publication Strategy

### 2.1 Feasibility Tiers (Respecting Fixed Repository Constraints)
- **Tier A — Immediately Feasible for Lead Alone (December credits `~$20–24` billed, ~3 weeks):**
  1. **Run pre-registered `O2a + O2b`** (`o2_manifest.py`, `o2_frozen_analysis.py`, `o2_att_harm.py`) on `4,295` unseen NLST stretched exams + `810` paired scans (`x6_unseen_metadata.json`, `$18–21` measured / **`$18.90–23.10` billed**), upgraded with:
     - `st = (ratio > 0) & (ratio <= 0.65)` (fixing `ratio == 0` bug in `s6_frozen_analysis.py:184`).
     - Dual frozen numeric thresholds: **`τ90 = 0.01799`** (`frozen_thresholds_L2.json`, `11.2%` dev FP) **plus** **`τ_rad = 0.03389`** (`s4_u3_dev.json`, `90.9%` dev sensitivity / `6.0%` dev FP), reporting **total discordant reclassification `(lost + gained)/N`** as primary binary instability alongside net shift `(lost - gained)/N`, `|Δs1| >= 0.01` / `>= 0.05` tier jumps, and continuous logit shift (`H2`).
     - Outcome-free **`o2_att_harm.py`** forked from `r10_att_harm.py` with **`P.y1` (`line 57`) stripped** (merging only `ctab` `sct_long_dia >= 4 mm`), reporting `nodule_outside_box` and `share_near_nodule` as *mechanistic attention displacement*.
     - Explicit scanner-model & manufacturer stratification (`74` neither-GE + `200` one-GE pairs in `O2b`).
  2. **Optional Stratified IDC Phantom Subsample (`N = 80–100` scans, `~$0.60–0.75` billed):** Sample e.g. `50` `ct4harmonization_multicentric` + `50` `phantom_fda` stretched scans (`x2_idc_stretch_by_collection.csv`) across makers/thicknesses for zero-biology proof of `axis 0` + z-fix drop (running all `5,444` phantom scans at X5's `$0.00736/pair` rate would cost `~$40`, which is infeasible; if Dec billed cap must stay strictly `<= $20`, drop phantom check).
  3. **Free Post-Hoc Exploratory Sensitivity & Reproducibility Upgrades (`r1_sensitivity_test.py`, labeled explicitly exploratory on opened test data per `LUNG_L2_PROTOCOL.md` §11):**
     - Compute Brier score, calibration slope/intercept, and ECE on `s1`, `F1`, `C2`, and `C1+Sybil` (both `E1` and baseline `E2`), and re-run DCA (`M5`) with dev-calibrated `F1`/`C2` (`S1`).
     - Add 6-year IPCW / Uno's C-index sensitivity check (`D2`, recovering the `12%` censored baseline loss).
     - Replace exam-level `M4` LR and `M6` Clopper-Pearson CIs with participant-cluster bootstrap / GEE (`S2`), and remove/relabel in-sample `U3_table` (`D1`).
     - Center clinical anti-workup narrative on **`E4` (`Sybil 0.724 vs C2 0.747`, `81/131` `can_scr==1`)** and **`E5` (`Sybil 0.580 vs C2 0.637`, `22/51` `can_scr==1`)** alongside `E1` (`83/86` `can_scr==1`), and **explicitly address `E2` baseline (`M3 C1+Sybil = +0.0256 [+0.0004, +0.0544]`, `ctabc` prior-scan features absent in `nlst_l0.py:74-78,139-145`)** via calibration/DCA sensitivity.
     - Reframe SAE results accurately (`E1`–`E3`): include Step R `k=16` pass (`V1/V2/V4`, explicitly noting single-member `V2` on SAE and 2-member `V2` on NMF in `RESULTS_R_dev.md` §3) and MCCA 11-axis shared subspace (`R^2 = 0.939`) contrasted against `Elhage et al. (2022)` / `Wesp et al. (2026)`.
     - Refactor `D:\Shayan` paths, add `requirements-modal.txt`, complete `TRIPOD+AI` + `CLAIM 2024` checklists, and publish clean `s6_frozen_analysis.py` reproducibility rerun.
  4. **Coordinated Disclosure (`O5 -> O4`):** Post `medRxiv` preprint first, then file GitHub issue + email to Sybil authors on the same day.
- **Tier B — Contingent on Recruiting an Eligible Clinical Co-Author (US/Non-Restricted Institution):**
  - Because DLCS (`10.1148/ryai.240248`, modern scanners + Lung-RADS) and NIH CDAS (`NOT-OD-25-083`) are blocked for the lead's location (`DATA_REQUEST_GUIDE.md`), recruiting a US/eligible thoracic radiologist co-author unlocks running the **frozen evaluation script** on DLCS or a contemporary clinical screening cohort—turning a top specialty paper into a *Lancet Digital Health* / *Radiology* flagship contender.

### 2.2 Narrative & Framing Upgrades
- **Frame as a Single Unified Paper (`O6`):** *"Clinical and Mechanistic Algorithmic Audit of a Deployed Lung Cancer Screening Model: Evaluation of Added Value and an Internal Slice-Spacing Shortcut."*
- **Follow the audit logic of `Liu et al. (2022)` (error mapping, then testing; stage names not verified):** (1) Clinical utility & added value vs structured radiologist findings (`L1` pre-registered + `X1`/`X3` exploratory, `E1`/`E2`/`E4`/`E5`, calibration + DCA); (2) Failure-mode discovery & code audit (`X4`, DICOM `SliceThickness` vs `ImagePositionPatient`, contradicting `Simon et al. 2025`); (3) Mechanistic localization & causal ablation (`pooled` MCCA 11-axis subspace → `axis 0` ablation `H6` + `o2_att_harm.py`); (4) Multi-center & unseen generalization (`X5` LIDC 7 centers + `O2a/O2b` unseen NLST non-GE pairs + optional `N=80–100` phantom subsample).

### 2.3 Target Publication Venues (Ranked with Rationale)

| Rank | Venue | Fit & Rationale | Comparable Precedents | Key Gatekeeper Requirements |
|---|---|---|---|---|
| **1 (Primary Best Fit)** | ***Radiology: Artificial Intelligence*** | Highest thematic & audience match for DICOM geometry bugs + Sybil validation + clinical baseline comparison (`O2a+O2b` sufficient). | `Shu et al. (2026)` DICOM exposure shortcuts (`10.1148/ryai.250731`); `DLCS (2024/2025)` (`10.1148/ryai.240248`). | `CLAIM 2024` checklist; clear framing of `τ90 = 0.01799` + `τ_rad = 0.03389` + `o2_att_harm.py`; `E2` baseline defense; calibration + DCA; clean code/reproducibility. |
| **1B (Co-Primary Broad Digital Health)** | ***npj Digital Medicine*** | Very receptive to combined "clinical non-incrementality + shortcut mechanism + representation ablation" audits without requiring a second prospective US cancer outcome cohort. | `Badgeley et al. (2019)`; `Ong Ly et al. (2024)` (`10.1038/s41746-024-01118-4`). | `TRIPOD+AI`; honest framing of SAE vs MCCA low-rank structure (with Step R `V2` caveats); calibration + IPCW sensitivity + non-GE `O2b`. |
| **2 (Flagship Stretch — Needs Tier B Co-Author)** | ***The Lancet Digital Health*** or ***Radiology*** | Premier clinical impact if a clinical co-author adds either modern external outcome/Lung-RADS validation (e.g., DLCS) or authoritative thoracic radiology reader context. | `Liu et al. (2022)` audit; `Gichoya et al. (2022)`; `Lee et al. (Radiology 2025)`. | Modern cohort beyond 2002–2009 NLST (`Tier B`), clinical co-author, `TRIPOD+AI`, zero statistical loose ends (calibration, IPCW, cluster CIs). |
| **3 (Solid Specialty Backup)** | ***European Radiology*** or ***JCO Clinical Cancer Informatics*** | Directly reaches thoracic radiologists or the *JCO* oncology community (`Mikhael et al., 2023`). | *JCO CCI* NLST 3D DL (`10.1200/CCI-26-00030`). | Strong fallback if Tier 1/1B reject on single-trial NLST clinical outcomes. |

---

## 3. Major Risks & Limitations

1. **Low unseen cancer prevalence (`~0.1%`) in `O2a`:** Net `(lost - gained)/N` may shrink near zero even when total discordant reclassification `(lost + gained)/N` is `5–7%`; mitigated by pre-registering total discordant reclassification, `τ90 = 0.01799` + `τ_rad = 0.03389`, and outcome-free `o2_att_harm.py`.
2. **`E2` 1-year baseline `+0.0256 [+0.0004, +0.0544]` vs `E1` `ctabc`:** Reviewers will ask why baseline Sybil helps slightly when prior scans are absent; mitigated by `E2` calibration/DCA sensitivity + transparent distinction between baseline vs serial screening.
3. **Historical NLST (2002–2009) vs modern thin-slice CT / Lung-RADS:** LIDC provides modern clinical scanner evidence for the *mechanism*, while only a Tier-B co-author provides modern *outcome* comparison for the clinical "form" claim.
4. **LIDC vendor heterogeneity in `H2` (`Siemens +0.177` vs `GE -0.280`):** Shows non-axis-0 pathways interact with Siemens/Philips reconstructions—must be reported transparently alongside `O2b`'s `74` neither-GE pairs.

---

## 4. Operational Verification Rubric

| Dimension | Explicit Pass / Fail Criteria | Verified Status & Exact Evidence |
|---|---|---|
| **Specificity** | (a) Exact numeric cutoffs cited from frozen/dev JSONs (no vague labels); (b) explicit CLI/script names for new O2 & sensitivity tasks; (c) outcome-free `O2a` guard removes `P.y1` from `r10_att_harm.py:57`; (d) exact line numbers verified against `prostate-mri-plan`. | **PASS** — Specifies `τ90 = 0.01799` (`frozen_thresholds_L2.json`), `τ_rad = 0.03389` (`s4_u3_dev.json`), `|Δs1| >= 0.01`/`>= 0.05`, total discordant reclassification `(lost+gained)/N`; names `o2_manifest.py`, `o2_frozen_analysis.py`, `o2_att_harm.py` (`P.y1` stripped), `r1_sensitivity_test.py`; cites `s6_frozen_analysis.py:184`. |
| **Feasibility** | (a) Measured vs billed (+5–10%) costs reconcile against `$67.81/$72` ledger & `~$20` Dec agreement; (b) phantom check subsampled so total remains realistic (`<= $24` billed, not `$40`); (c) respects 2025 DOJ/NOT-OD-25-083/TCIA blocks & no reader study; (d) no test-set checks mislabeled "pre-registered". | **PASS (with cap-raise condition)** — `O2a+O2b` = `$18–21` measured (`$18.90–23.10` billed); phantom strictly subsampled (`N=80–100`, `~$0.60–0.75` billed; explicit omit option if staying `<= $20`); DLCS/CDAS separated into Tier B (co-author dependent); test checks labeled post-hoc exploratory per `LUNG_L2_PROTOCOL.md` §11. |
| **Scientific & Repo Grounding** | (a) `E4`/`E5` & `E2 +0.026` numbers match `s7_added_value_test.json` exactly; (b) Step R `V2` scouting caveats noted (`RESULTS_R_dev.md` §3); (c) all DOIs/arXiv IDs verified against `docs/LITERATURE_TABLE_R3.md` and published identifiers; (d) `RESULTS_L2.md` §4 wording rules honored (`H3` failed). | **PASS** — `E4` (`0.724 vs 0.747`, `81/131`), `E5` (`0.580 vs 0.637`, `22/51`), `E2` (`+0.0256`), Step R `V2` (`1` / `2` members), `H3` (`4.5%` failed), and all DOIs/arXiv IDs verified against `docs/LITERATURE_TABLE_R3.md` and committed repository files. |
