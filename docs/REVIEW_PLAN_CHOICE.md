# Independent Review of Plan Choice (`docs/PROMPT_REVIEW_PLAN_CHOICE.md`)

**Branch & Commit Inspected:** `prostate-mri-plan` (`89317e8`; read-only inspection of all frozen files, scripts, and committed outputs — no code, data, ledger, or test outputs modified).  
**Companion Reports:** [docs/INDEPENDENT_AUDIT_R2.md](INDEPENDENT_AUDIT_R2.md) (technical, statistical, and reproducibility audit), [docs/LITERATURE_AND_PAPER_STRATEGY_R3.md](LITERATURE_AND_PAPER_STRATEGY_R3.md) (high-impact publication strategy), and [docs/LITERATURE_TABLE_R3.md](LITERATURE_TABLE_R3.md) (40-paper verified bibliography).  
**Format:** Follows `docs/EXPLAINED_FOR_THE_LEAD.md` Part A (short plain sentences, tables, ranked plan first, reasons with numbers, copy-pasteable lead decisions, full paths).

---

## 1. Ranked Plan (What First, What Later, What to Drop)

**Bottom line:** Run **O2a + O2b** in December (expanded with free secondary checks on the exact same inference arrays), finish the free parts of **O1** + post-hoc exploratory sensitivity checks right now while waiting for December credits, post a **medRxiv preprint (O5)** and **tell Sybil's authors (O4)** on the same day, submit as **one unified clinical + mechanistic audit paper (O6)**, and **drop O2c and O3**.

| Rank | Step | Timing & Cost | Chance It Helps the Paper | What It Fixes / Why |
|---|---|---|---|---|
| **1 (Do now — free)** | **Free parts of O1** (`O1` refactor, TRIPOD+AI & CLAIM 2024 checklists, literature synthesis) + **post-hoc exploratory sensitivity checks** (`r1_sensitivity_test.py` on existing dev/test outputs—clearly labeled exploratory per `LUNG_L2_PROTOCOL.md` §11, never pre-registered on opened test data) | Now (late Nov); **$0** | **95%** | Needed for every journal anyway. Refactors `D:\Shayan` paths in imported modules (`s4_common.py`, `s5_axes_freeze.py`, `s7_added_value.py`) so a second person can re-run `s6_frozen_analysis.py`, and adds calibration/IPCW/cluster-robust checks. |
| **2 (Do first on Dec 1)** | **O2a + O2b** on never-used NLST (`4,295` stretched exams + `810` paired scans = `5,105` main + `4,295` z-fix), **upgraded** in `o2_manifest.py` / `o2_frozen_analysis.py` / `o2_att_harm.py` (forked from `r10_att_harm.py` with `P.y1` removed) | December (~2–3 wks); **`$18–21` measured (`$18.90–23.10` billed)** | **85%** | Fixes Reviewer Weakness #2 (**H7 outside GE**: adds `74` neither-GE and `200` one-GE pairs vs `13` on test). Replicates H1/H2/H6 on `2,093` unseen people. Measures total alarm reclassification, `τ90`/`τ_rad` flips, and nodule-box/attention displacement without reading any `y1` outcome. |
| **3 (Optional tiny add-on)** | **Stratified phantom subsample (`N = 80–100` scans)** from open IDC phantoms (e.g., `50` `ct4harmonization_multicentric` + `50` `phantom_fda` across makers/thicknesses; running all `5,444` scans would cost `~$40` at X5's `$0.00736/pair` rate) | December; **`~$0.60–0.75` billed** (omit if staying strictly `<= $20` billed) | **75%** | Proves `axis 0` and z-fix score drops come purely from CT geometry with **zero** patient biology, age, or nodule confounders. Needs no outcomes. |
| **4 (Do after O2)** | **O5 (medRxiv preprint)** + **O4 (notify Sybil authors)** simultaneously at preprint posting | After O2 finishes; **$0** | **90%** | Protects scientific priority while meeting clinical safety ethics (`PROJECT_GUIDE.md` N9c). Allows citing a live GitHub issue/response in journal submission. |
| **5 (Paper structure)** | **O6: One unified paper** (*"Clinical + Mechanistic Algorithmic Audit of Sybil"*), targeting *Radiology: Artificial Intelligence* or *npj Digital Medicine* (stretch *The Lancet Digital Health* / *Radiology* only if a Tier-B co-author joins) | Submit after O5; **$0** | **80%** | Splitting leaves Paper A ("form" on 86/131 cancers) looking underpowered and single-trial, and leaves Paper B looking purely technical. Combined, they follow the *Lancet Digital Health* / *Radiology: AI* algorithmic-audit template. |
| **6 (Drop)** | **O2c** (unseen NLST case-control "form" test, `~29` 1y cancers) | **Drop** (saves **+$7–8**) | **15%** (35% risk of hurting via `±0.10` noise) | `29` cancers in a `0.1%`-prevalence residue yields `±0.08` to `±0.10` CI width on `Sybil - Findings`. Cannot settle the form question and pushes Dec cost to `$26–32` billed. |
| **7 (Drop / conditional)** | **O3** (LIDC diagnostic nodule rating test, `157` patients) | **Drop** unless TCIA unblocks effortlessly (saves **$1–2**) | **20%** | Diagnostic multi-reader malignancy ratings (1–5) on 157 patients are not a screening findings form (`NLST`), and TCIA is currently blocked. |

---

## 2. Fact-Check of Sections 1–4 Against Section 6 Files

Every major claim in `docs/PROMPT_REVIEW_PLAN_CHOICE.md` matches the committed files on `prostate-mri-plan` (`89317e8`), **with two concrete numerical errors and four important nuances**:

| Item in `PROMPT_REVIEW_PLAN_CHOICE.md` | What Prompt Says | What Committed Repo Files Actually Show | Verdict |
|---|---|---|---|
| **O2a dev z-fix flag flips** (§4 O2a) | `dev 38 and 31 (7 per 1,000; 998 exams)` | `imgsae/exploratory/lung_l2/results/s5/s6_dev_as_if_test.json` (`H3_flags`): `lost: 38`, `gained: 31`, over **`924`** D5 exams (`ratio <= 0.65`), which is **`7.6` per 1,000** (`7/924`), NOT `998` (`998` in S3 includes `74` pilot scans with `0.65 < ratio <= 0.95`). | **Error** (denominator `924`, not `998`). |
| **H2 test mean 1-year logit drop** (§2 Row 4) | `−0.367` | `imgsae/exploratory/lung_l2/results/s6/s6_test.json`: `H2.est = -0.36646` (`[-0.4112, -0.3200]`), which rounds to **`-0.366`** (`RESULTS_L2.md` §2.3 writes `-0.366`, while §1 wrote `-0.367`). | **Rounding typo** (`-0.366`). |
| **L1 primary vs secondary labeling** (§2 Row 1) | Bolds L1 `0.914 vs 0.945` (`−0.031`) under "L1 primary" | `imgsae/exploratory/lung_l1/results/l1_results.json`: `0.9141 vs 0.9448` is **A3** (all screens, `5,380` scored, `95% CI`, `"primary": false`). L1's true `"primary": true` endpoints were **A1** (1y baseline: `0.9265 vs 0.9293`, `+0.0255 [-0.0038, +0.0609]` combined) and **A2** (6y baseline: `0.7238 vs 0.7448`). Full-test L2 X1 (`s7_added_value_test.json`, `6,674` exams, `86` cancers) gives `0.914 vs 0.947` (`-0.033 [-0.067, -0.003]`). | **Nuance** (omits A1 and L2 X1's tighter CI excluding 0). |
| **"Never better" in X1/X3** (§2 Row 2) | `never better` | `imgsae/exploratory/lung_l2/results/s8/s8_demographics_test.json`: `E2 M2` (`Sybil+D - C2`) point estimate is **`+0.00287 [-0.04968, +0.05588]`** (noise; cross-fitted `M3` is `-0.00451`). Also in `s7_added_value_test.json`, `E2 M3 C1+Sybil` gives **`+0.0256 [+0.0004, +0.0544]`** (`0.927 -> 0.949`, LR `p = 1.37e-10`) when longitudinal `ctabc` prior-scan comparisons are absent. | **Nuance** (`E2` baseline gain needs explicit handling). |
| **SAE & NMF validity marks** (§2 Row 12) | `Sparse-dictionary features (SAE, NMF): Failed the validity marks` | `RESULTS_S4_dev.md`: At `h`, SAE and NMF failed V1/V3/V4. `RESULTS_R_dev.md`: At `pooled`, SAE failed (`K=64, k=16` passed V1/V2/V4 on member-0 `V2`, failed V3 `12<16`), **but NMF (`K=64`) formally PASSED V1–V4** (`r_y1 = 0.998`, `16` families, `2`-member `V2`) and was rejected only because non-negative clamping gave negative reconstruction $R^2$ (`-2.833`). | **Nuance** (true for SAE, overstated for `pooled` NMF). |
| **Unseen NLST counts** (§4 O2) | `11,226` participants, `28,661` exams; L0 `34` cancers (`29` 1y) | `x6_unseen_metadata.json`: `11,235` unseen with CT, `11,226` selected (`28,661` exams). `RESULTS_L0.md` §2 counted `34` cancers (`29` 1y) on all `11,432` unseen clinical-table participants (`30,888` exams). | **Match with denominator nuance**. |

All other numbers—H1 (`0.657`), H3 (`4.5%`, `27` lost / `7` gained), H4 (`1.8%`, `500` pairs), H6 (`+0.407`, axis-0 off AUROC `0.9163 -> 0.9160`), H7 (`4,353` pairs, `134` changed, `+0.311 [0.185, 0.435]`, `121/134` GE), LIDC X5 (`197` scans, H1 `0.650`, H2 `-0.177`, H6 `+0.395`, axis-0 `-2.76 SD`), X4 code audit, dev rule-out cut (`22/81` cancers lost), and ledger (`$67.81 / $72`, `$4.19` left)—match committed outputs exactly (`s6_test.json`, `s7_added_value_test.json`, `x5_lidc.json`, `x4_code_audit.md`, `ledger.json`).

---

## 3. Answers to Questions Q1–Q8

### Q1. Rank options by chance of a high-impact paper, and match journals
1. **Rank 1 — `O2a + O2b + O1 (free prep + sensitivity checks) + O5 (medRxiv) + O4 (notify at preprint) + O6 (unified paper)` (~80–85% chance of strong peer-reviewed acceptance):**
   - **Best-fit target:** ***Radiology: Artificial Intelligence*** (direct precedent: `Shu et al., Radiology: AI 2026`, `10.1148/ryai.250731` on DICOM exposure shortcuts) or ***npj Digital Medicine*** (`Ong Ly et al., 2024`, `10.1038/s41746-024-01118-4`).
   - **Flagship stretch (only if a Tier-B clinical co-author runs frozen scripts on a modern cohort such as DLCS):** ***The Lancet Digital Health*** (`Liu et al., 2022` *Medical Algorithmic Audit*; `Gichoya et al., 2022`) or ***Radiology*** (`Lee et al., 2025`).
2. **Rank 2 — `O1 + O5 + O4 + O6 (unified)` without O2 (~50–60% chance at top tier; ~75% at *Radiology: AI* / *European Radiology* / *JCO CCI*):**
   - Risk: Reviewers reject H7 as "GE-only (`121/134` pairs)" and cite `9` stretched 1y cancers as "no clinical consequence shown".
3. **Rank 3 — Two-paper split (`O6` A + B) (~40% for Paper A alone, ~70% for Paper B):**
   - Paper A ("Sybil vs NLST form") alone is single-trial, post-2023, and vulnerable to work-up bias critiques.
4. **Drop — `O2c` and `O3`:** Neither raises journal tier; `O2c` risks noisy contradictions.

### Q2. One paper or two (O6)? What should the main message be?
- **Recommendation: ONE unified paper**, structured along *The Medical Algorithmic Audit* (`Liu et al., Lancet Digit Health 2022`).
- **Why one paper wins:** Literature precedents (`DeGrave et al., Nat Mach Intell 2021`; `Gichoya et al., Lancet Digit Health 2022`; `Shu et al., Radiology: AI 2026`) achieve high impact because they connect **clinical failure** ("adds no net benefit across all screens or 6-year endpoints beyond structured radiologist findings; dev rule-out cuts fail") to **mechanistic root cause** ("single internal direction `axis 0` encodes an undisclosed DICOM `SliceThickness` vs `ImagePositionPatient` bug causing scan-to-scan jumps").
- **Main message (one sentence, strictly compliant with `RESULTS_L2.md` §4 and protocol separation):** *"In a pre-registered test-split and multi-center feature audit of Sybil (`L1`, `H1–H4, H6–H7`) paired with exploratory added-value analyses (`X1`, `X3`, `X5`), Sybil adds no net benefit beyond structured radiologist screening findings across all screens or 6-year horizons, and harbors a DICOM `SliceThickness` vs `ImagePositionPatient` bug localized to a single internal direction (`axis 0`) that shifts risk logits (`-0.366`) and drives `+0.311` longitudinal jumps across reconstructions (though binary `>5%` alarm flips `H3` failed at `4.5%`)."*

### Q3. Is O2 worth $18.90–23.10 billed and ~3 weeks? Which parts? Will `τ90` false alarms convince reviewers?
- **Yes — `O2a + O2b` (`$18–21` measured / `$18.90–23.10` billed) is worth it; `O2c` is NOT.**
- **Why `O2b` (+`$2–3`) has the highest ROI in the project:** `823` changed pairs including **`74` neither-GE** and **`200` one-GE** pairs (`x6_unseen_metadata.json`) definitively settles whether H7 is a universal Sybil failure or a GE quirk.
- **Critical warning on `O2a` false alarms (`τ90`):** **A single dev threshold `τ90 = 0.01799` alone will NOT convince clinical reviewers**, for three reasons discovered in the repository:
  1. **Near-zero-cancer prevalence trap (`~0.1%` vs `1.29%`):** Because Sybil's sample took almost all NLST cancers (`RESULTS_L0.md`: only `29` 1y cancers in `30,888` unseen exams), far fewer unseen scans sit near `τ90`. Net alarm shift `(lost - gained)/N` may shrink near zero (`~5–15` per `1,000`), just as dev (`7.6/1,000` on `924` D5 exams) and LIDC (`15.2/1,000`) were smaller than test (`26.4/1,000`), even if discordant flips `(lost + gained)/N` remain substantial (`5–7%`).
  2. **Calibrator step-function artifact (`EXECUTION_LOG.md` Nov 16):** Sybil's published calibrator clamps low scores to `0.0` (`16.3%` ties at `0.000` in dev; only `227` distinct `s1` values across `7,336` dev exams), making any single low cutoff noisy.
  3. **Clinical interpretability:** Reviewers want thresholds tied to **clinical action**, not only an arbitrary dev 90th percentile.
- **Exact endpoints to pre-register in `o2_frozen_analysis.py` + `o2_att_harm.py`:**
  1. **Primary alarm-instability endpoint:** **Total discordant reclassification rate** `(lost + gained) / N` alongside net alarm change `(lost - gained) / N` at frozen **`τ90 = 0.01799`** (`frozen_thresholds_L2.json`, `10%` nominal / `11.2%` actual dev FP), **plus** frozen **`τ_rad = 0.03389`** (dev radiologist-sensitivity-matched cut from `s4_u3_dev.json`, `90.9%` dev sensitivity, `60.1` FA/1,000 / `6.0%` dev FP).
  2. **Clinically meaningful risk-tier jump:** Proportion with `|Δs1| >= 0.01` or crossing `s1 >= 0.05` high-risk, plus continuous logit drop (`H2`).
  3. **Outcome-free mechanistic attention displacement (`o2_att_harm.py`):** Forked from `r10_att_harm.py` with **`P.y1` (`line 57`) completely stripped**, merging only `ctab` `sct_long_dia >= 4 mm` (zero outcome columns read), reporting `nodule_outside_box` and `share_near_nodule` as *mechanistic attention displacement* (never patient harm). (Optionally also run `r10_att_harm` exploratorily on already-saved S6 test `zfix` arrays at `$0`.)

### Q4. O2c: do it, keep descriptive, or drop?
- **Drop O2c** (`saves +$7–8`). With `~29` 1y cancers in a case-control draw from `28,661` cancer-depleted exams, `Sybil - Findings` AUROC has a `95% CI` of roughly `±0.08` to `±0.10`, cannot measure calibration or DCA net benefit without artificial reweighting, and pushes December billed spend to `$26–32`.

### Q5. How can the "form" finding be made stronger without new outcome data (honestly)?
Use five strictly honest, **post-hoc exploratory sensitivity analyses** (`r1_sensitivity_test.py`) on existing test data (explicitly labeled exploratory per `LUNG_L2_PROTOCOL.md` §11, never pre-registered on already-opened test data):
1. **Center `E4` (`y6` baseline, `2,002` exams, `131` cancers) and `E5` (negative baseline, `1,140` exams, `51` cancers) alongside `E1`, and address `E2` honestly:** In `E1`, `83/86` (`96.5%`) 1y cancers had `can_scr == 1` (`s7_added_value_test.json`), so work-up bias persists even when removing `res1..6` (`C2`). `E4` (`81/131` `can_scr == 1`) and `E5` (`22/51` `can_scr == 1`) sharply reduce immediate work-up bias and show **Sybil (`0.724` / `0.580`) clearly underperforms `C2` (`0.747` / `0.637`)** at 6 years. **Crucial defense for `E2` (1y baseline, `2,278` exams, `41` cancers):** Acknowledge openly that in `E2` (where `ctabc` prior-scan comparisons `gw*`/`pre*`/`att*` in `nlst_l0.py:74-78,139-145` are absent), cross-fitted `M3 C1+Sybil` adds **`+0.0256 [+0.0004, +0.0544]`** (`0.927 -> 0.949`, LR `p = 1.37e-10`; L1 `A1` `+0.0255 [-0.0038, +0.0609]`), whereas in `E1` (once prior-scan comparisons exist) Sybil adds `-0.005` (`M2`) / `+0.002` (`M3`). Run `E2` calibration + DCA sensitivity in `r1_sensitivity_test.py` so the claim is scoped accurately (*"adds no net benefit across all screens `E1` or at 6y `E4`/`E5`, and modest baseline `E2` gain `+0.026` diminishes once prior-scan comparison is available"*).
2. **Add calibration & reclassification analyses (`M5` prerequisite):** Neither `lung_l1` nor `lung_l2` computes Brier score, calibration slope/intercept, or ECE (`s7_added_value.py` compares dev-calibrated `s1` against uncalibrated train `C1_1` across `1.52% -> 1.29%` prevalence shift). Checking calibration and re-running DCA with dev-calibrated `F1`/`C2` makes the zero-net-benefit conclusion rigorous (`Vickers et al., BMJ 2016`).
3. **Explain the "LR χ² significant (`p = 7e-12`) yet AUROC `Δ = -0.004` and DCA `Δ = 0`" paradox via `RESULTS_S4_dev.md` Q1a:** `69.3%` of Sybil's logit variance is orthogonal to `N+B+D+I+T`, yet carries minimal clinical utility beyond `C2`—explaining why large sample `χ²` does not translate into DCA net benefit.
4. **Fix clustering in `M4` and `M6` CIs:** Replace exam-level `chi2` LR tests and Clopper-Pearson CIs in `s7_added_value.py` with participant-cluster bootstrap / GEE Wald tests (`22/81` cancers lost vs `1/81` for `C2`).
5. **Run a 6-year IPCW / competing-risk sensitivity check (`nlst_l0.py:110`):** Show that dropping the `12.1%` censored baseline exams (`2,278 -> 2,002`) does not alter `Sybil vs C2` at 6 years.

### Q6. Three biggest weaknesses a journal reviewer will raise (and fixes)
| # | Reviewer Weakness | Impact on Acceptance | Which Option Fixes It? |
|---|---|---|---|
| **1** | **Single historical US trial (NLST, 2002–2009) for the clinical "form" claim & lack of modern Lung-RADS cohort (e.g., DLCS)** | **High** (blocks *Lancet Digital Health* / *Radiology* unless addressed or explicitly bounded) | **Not fixed by O2c or O3.** Mitigated by: (a) recruiting a US/eligible **clinical co-author** to run frozen scripts on DLCS (`10.1148/ryai.240248`) or an institutional LDCT cohort; (b) otherwise bounding scope to NLST (`TRIPOD+AI` limitation), foregrounding `E4/E5` + `E2` nuance, and centering multi-center novelty on **O2a/O2b + LIDC (7 centers)**. |
| **2** | **No patient harm proven & H7 (`+0.311`) is 90% GE-driven (`121/134` pairs) with `73%` (`98/134`) simultaneous scanner-model switches** | **High** (core threat to mechanism + clinical significance) | **Fixed by O2a + O2b** (`74` neither-GE + `200` one-GE pairs; `4,295` stretched scans; total discordant reclassification + `τ90`/`τ_rad` + `o2_att_harm.py` + scanner-model stratification + optional `N=80–100` phantom subsample). |
| **3** | **Statistical/methodological gaps in clinical utility evaluation: no calibration checks on DCA, `12%` 6y censoring drop, unclustered `M4`/`M6` CIs, in-sample `U3` cut (`s6_frozen_analysis.py:240-242`, `s4_u3.py:26-32`), and `E1` work-up bias (`83/86` screen-detected)** | **Medium-High** (easy target for statistical reviewers) | **Fixed by O1 post-hoc exploratory sensitivity analyses** (`r1_sensitivity_test.py`: calibration slope/intercept/Brier, IPCW 6y check, cluster-robust `M4`/`M6`, removing/re-labeling in-sample `U3`, addressing `E2` `+0.026` vs `E4/E5`). |

### Q7. Timing of O4 (tell Sybil authors) and O5 (medRxiv preprint)
- **Sequence:** Complete **O2a + O2b** (~3 weeks) → post **O5 (medRxiv preprint)** with clean code/tables → **immediately notify Sybil's authors (O4)** via GitHub issue + email **on the same day O5 goes live**.
- **Why:** Notifying before preprint risks getting scooped on the `SliceThickness` bug; waiting until after journal acceptance delays fixing an active clinical software bug (`PROJECT_GUIDE.md` N9c).

### Q8. What did we miss?
1. **Unseen NLST `~0.1%` prevalence bias & total reclassification in O2a:** `~29` 1y cancers across `28,661` unseen exams will suppress net `(lost - gained)/N` flips at `τ90`; pre-register **total discordant reclassification `(lost + gained)/N`** as primary binary instability alongside net shift, `τ_rad = 0.03389`, and continuous logit shift (`H2`).
2. **`r10_att_harm.py` was omitted from S6 test (`s6_attention_test.json`) and reads `P.y1` at line 57:** Fork `r10_att_harm.py` into outcome-free `o2_att_harm.py` (`P.y1` stripped; `ctab` `sct_long_dia >= 4 mm` only) for O2a, plus run `r10_att_harm` exploratorily on already-saved S6 test `zfix` arrays at `$0`.
3. **Stratified IDC phantom subsample (`x2_idc_stretch_by_collection.csv`):** A full run of `ct4harmonization_multicentric` (`1,375`) + `phantom_fda` (`4,069`) would cost `~$40` at X5's `$0.00736/pair` rate; a **stratified subsample of `N = 80–100` stretched phantom scans** costs **`~$0.60–0.75` billed** and gives zero-biology causal proof.
4. **Calibrator step-function artifact (`EXECUTION_LOG.md` Nov 16):** `16.3%` of dev scans tie at `0.000` (`s1 < 0.04` clamped), distorting binary alarm flips (`H3`/`O2a`).
5. **`ratio == 0` duplicate-slice bug in `s6_frozen_analysis.py:184`:** Primary H7 classified `ratio == 0` scans (where `zfix` was skipped) as "stretched"; `o2_frozen_analysis.py` must set `st = (ratio > 0) & (ratio <= 0.65)` as primary.
6. **Direct literature white space (`docs/LITERATURE_AND_PAPER_STRATEGY_R3.md`):** `Simon et al. (Invest Radiol 2025)` claimed Sybil is robust to nominal slice thickness (`2 mm vs 5 mm`), and `Phellan Aro et al. (Chest 2026)` tested adding PLCOm2012 to Sybil. This audit directly overturns `Simon et al.` (`SliceThickness` vs `ImagePositionPatient`) and reverses `Phellan Aro et al.`.

---

## 4. Comparison With Executor's View (Section 9)

- **Where we agree:** (1) Rank **O2a + O2b** first and **drop O2c**; (2) do free **O1** tasks in parallel; (3) link **O4** with **O5**; (4) `O3` is low-value/blocked; (5) net `τ90` false-alarm difference may shrink toward zero.
- **Where we sharpen or disagree:**
  1. **Unified paper (`O6`) over split:** Section 9 is unsure between one paper and two. Published precedents (*Lancet Digital Health*, *Radiology: AI*, *npj Digital Medicine*) strongly favor **one unified audit paper**; splitting leaves the clinical half weak.
  2. **O2a must NOT rely solely on net `τ90` shift:** Pre-register **total discordant reclassification `(lost + gained)/N`**, **`τ90 = 0.01799` + `τ_rad = 0.03389`**, and **outcome-free `o2_att_harm.py`** (`P.y1` stripped).
  3. **Add `r1_sensitivity_test.py` (calibration, IPCW, cluster CIs, `E2` baseline `+0.026` check) as post-hoc exploratory analyses** before journal submission.
  4. **Scope any IDC phantom check strictly to `N = 80–100` stratified scans (`~$0.60–0.75` billed)**—never the full `5,444` scans (`~$40`).

---

## 5. What the Lead Must Decide (Copy-Pasteable Defaults)

> **[Recommended Defaults — Ready to Approve]**
> 1. **Budget & Scope:** Raise project cap from `$72` to **`$96`** (`$67.81` used + `$18.90–23.10` billed for `O2a + O2b` in Dec + optional `$0.75` for `N=80–100` phantom subsample). **Approve / Decline**
> 2. **Drop `O2c` & `O3`:** Drop `O2c` (saves `$7–8`, avoids `±0.10` noise) and drop `O3` (unless TCIA unblocks without effort). **Approve / Decline**
> 3. **Upgraded `O2a + O2b` Pre-Registration (`o2_manifest.py`, `o2_frozen_analysis.py`, `o2_att_harm.py`):** Fix `st = (ratio > 0) & (ratio <= 0.65)`, pre-register total discordant reclassification + `τ90 = 0.01799` + `τ_rad = 0.03389` + outcome-free `o2_att_harm.py` (`P.y1` stripped) + `O2b` scanner-model stratification. **Approve / Decline**
> 4. **Post-Hoc Exploratory Sensitivity Checks (`r1_sensitivity_test.py`):** Run `$0` calibration/DCA (`E1` & `E2`), 6y IPCW, and cluster-robust `M4`/`M6` checks, labeled exploratory per `LUNG_L2_PROTOCOL.md` §11. **Approve / Decline**
> 5. **Co-Author & Disclosure (`O5 + O4`):** Recruit a clinical thoracic radiology co-author (US/EU-based if modern DLCS `10.1148/ryai.240248` validation is wanted) and post `medRxiv` (`O5`) + notify Sybil authors (`O4`) on the same day after `O2`. **Approve / Decline**

---

## 6. Files Added / Updated on `prostate-mri-plan`

- `docs/REVIEW_PLAN_CHOICE.md` (plan review, fact-check, Q1–Q8, copy-pasteable lead decisions)
- `docs/INDEPENDENT_AUDIT_R2.md` (independent technical, statistical, experimental, and reproducibility audit)
- `docs/LITERATURE_AND_PAPER_STRATEGY_R3.md` (competitive literature synthesis, venue targeting, high-impact paper roadmap)
- `docs/LITERATURE_TABLE_R3.md` (verified 40-paper bibliography table)
- `docs/EXECUTION_LOG.md` (one review log entry appended)
