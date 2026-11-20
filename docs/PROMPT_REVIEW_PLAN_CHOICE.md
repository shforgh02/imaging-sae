# Prompt for an outside review: which plan comes next? (Lung L2, after the test and the LIDC replication)

> **Corrections (20 Nov, after the review `docs/REVIEW_PLAN_CHOICE.md`; the text below is kept as it was sent):**
> - **Correction:** O2a, dev flag changes: 38 lost and 31 gained over **924** exams (7.6 per 1,000), not 998 (998 included 74 pilot scans with ratio 0.65 to 0.95).
> - **Correction:** H2 on test is **−0.366**, not −0.367.
> - **Correction:** the L1 numbers in the first table row (0.914 vs 0.945) are L1's all-screens analysis A3, which was **not** an L1 primary endpoint. L1's primary endpoints were A1 (1 year, baseline: 0.927 vs 0.929) and A2 (6 years, baseline: 0.724 vs 0.745).
> - **Correction:** "SAE, NMF: failed the validity marks" is true for the SAE. NMF at `pooled` passed the four marks and was rejected only because it rebuilt the vector worse than the dev mean (`RESULTS_R_dev.md`).

**How to use it (for the lead):**
- **AI reviewer:** use a **fresh session** that did not do this work (working folder `D:\Shayan`; Fable 5.2 or Opus 5.5, effort high or xhigh). Paste everything below the line, or give the short prompt: "Read `docs/PROMPT_REVIEW_PLAN_CHOICE.md` and do what it says below its line."
- **Human reviewer** (a methodologist, a radiologist or a senior AI researcher): the GitHub repository is **private**. Add the person as a collaborator (GitHub: repository Settings → Collaborators), then send the link to this file on branch `prostate-mri-plan`: `https://github.com/shforgh02/imaging-sae/blob/prostate-mri-plan/docs/PROMPT_REVIEW_PLAN_CHOICE.md`. A human reviewer can just answer the questions of section 5 by email; the lead (or a session) copies the answer into `docs/REVIEW_PLAN_CHOICE.md`.

---

You are an outside reviewer of a research project. You did not do this work. Your task is to **help the lead choose the next plan**, with the goal of a high-impact paper, and to say honestly where the work is weak. Repository `D:\Shayan` (also `github.com/shforgh02/imaging-sae`, branch `prostate-mri-plan`). The project is a feature-level audit of the open lung-screening AI **Sybil** (Mikhael et al., *J Clin Oncol* 2023) on public NLST data ("Lung L2"). Sections 1 to 4 are the executor's summary. Check them against the files in section 6; do not trust them blindly.

## 1. The decision
Choose among options O1 to O6 (section 4), or propose a better one. Give a ranked plan (what first, what later, what to drop), with reasons and the chance that each step helps the paper. Answer questions Q1 to Q8 (section 5).

## 2. What is done (status of each finding)
"Frozen" = a hypothesis fixed and committed before the data were opened, with the test split opened once. "Exploratory" = plan committed before running, output committed before reading, but not confirmatory.

| Finding | Data | Status | Key numbers (test unless said) |
|---|---|---|---|
| **Sybil adds nothing beyond what the trial radiologists recorded** (the "form": nodule findings, other findings, comparison with the earlier scan, the screening call, age, sex, smoking; fitted on Sybil's train participants only) | NLST, Sybil's own held-out test split | **L1 primary (pre-registered)**; L2 frozen secondary | L1, 1 year, all screens: Sybil 0.914 vs findings 0.945 (−0.031 [−0.072, +0.008]); Sybil + findings vs findings +0.000; 6 years, baseline: 0.724 vs 0.745. L2: Sybil 0.914 vs form 0.947; form + image measures + Sybil vs without −0.004 [−0.029, +0.020] |
| … also when the radiologist's final call is removed from the form; also with age, sex and smoking on both sides | NLST test | Exploratory (X1, X3) | Findings only (no call) 0.938; like for like (Sybil + demographics vs findings + demographics) −0.023 [−0.060, +0.010]; never better. Sybil does beat the call alone (+0.13 to +0.16 at baseline) and nodule size (+0.07 at 6 years). No net benefit on the decision curve |
| Dev flattered Sybil; dev-tuned cuts do not transfer | dev vs test | Secondary / exploratory | Dev: Sybil 0.969 vs form 0.928; test 0.914 vs 0.947. A rule-out cut set on dev to keep 95% of cancers lost 22 of 81 on test |
| **Slice-spacing error:** Sybil places slices at the DICOM slice thickness, not the true spacing; in 1 test exam in 9 the chest is stretched along z; the true spacing ("z-fix") lowers the score | NLST test, 759 exams | **Frozen: H1, H2 confirmed** | H1 65.7% of exams move ≥ ¼ SD (null 30%); H2 mean 1-year logit −0.367 (null −0.10) |
| The z-fix changes the alarm in > 5% of exams | same | **Frozen: H3 failed** | 4.5% [2.9%, 6.3%] (27 alarms lost, 7 gained) |
| The kernel hardly changes the alarm | 500 kernel pairs | Frozen: H4 confirmed | 1.8% |
| **One shared direction inside Sybil ("axis 0" of the `pooled` layer) carries the whole z-fix drop** | NLST test | **Frozen: H6 confirmed** | +0.407 (null +0.20); drop −0.37 → +0.04 with axis 0 off; AUROC unchanged |
| In real yearly screening, the score jumps when the reconstruction changes between stretched and not stretched | NLST test, 4,353 consecutive pairs (134 changed) | Frozen: H7 confirmed, "partly seen" | +0.311 [0.185, 0.435] logit beyond the findings; gone with axis 0 off; **121 of 134 changed pairs involve GE**; outside GE (13 pairs) nothing can be said |
| The mechanism replicates at 7 other centres | LIDC-IDRI, 197 stretched clinical scans | Exploratory external replication (X5) | H1 0.650; H2 −0.177 (weaker; GE −0.28, Philips −0.01, Siemens +0.18); H6 +0.395; axis-0 shift −2.76 SD (NLST −2.73) |
| The error is specific to Sybil among open tools | Public code (X4) | Descriptive | grt123, the DSB 2017 2nd place, MONAI, ITK and pylidc compute z correctly |
| Harm (missed cancers from the stretch) | NLST test | Pre-stated secondary | **Not shown; not testable:** 9 stretched 1-year cancers, 7 of 9 caught by both runs |
| Sparse-dictionary features (SAE, NMF) | dev | Failed the validity marks | Sybil's last layers ≈ one risk dial plus a few shared technical axes |

What the results do **not** allow: "the spacing step harms patients", "our feature improves Sybil", "this holds for all scanners", "Sybil equals the form" (no large gap either way with 86 and 131 cancers). Full wording rules: `RESULTS_L2.md` section 4.

## 3. Constraints (fixed; please plan within them)
- **Data access.** DLCS (Duke) declined because of the 2025 US data rule for the lead's country; the full NLST through NIH CDAS is very likely closed too (NOT-OD-25-083); the TCIA website refuses connections from this PC (treated as a block; **not** worked around). What works: the open IDC buckets (NLST images, LIDC-IDRI images) and the public NLST clinical tables already on the PC. Open non-US chest CT collections have almost no stretched scans (`results/x2_idc_stretch_by_collection.csv`). Local hospital data: the lead judges it poor (spacing often unknown). **A reader study is not feasible** (no radiologists available).
- **Money.** The lead's cloud cap for the whole project is $72: **$67.81 committed, $4.19 left** (after the billing check of 20 Nov). Account credits renew monthly (December). Raising the cap is the lead's decision; the lead agreed in principle to about $20 for December.
- **People and time.** The lead (a medical doctor) and AI sessions; a clinical co-author is not yet named in the repository.
- **Rules.** Any new outcome analysis needs a plan committed before it runs and its output committed before it is read. Sybil's test split was opened once for the frozen family; anything new on it is exploratory.
- **The lead's views:** the "form" finding is one of the greatest findings and must be built on; harm matters more than score changes; no manuscript draft right now.

## 4. Options
**O1. Write the paper now with what exists.** No new data. Cost $0; about 2 to 3 weeks (figures, a full literature search, TRIPOD+AI and CLAIM checklists, a second person re-running `s6_frozen_analysis.py` from the repository). Leaves three weak points open: no harm shown, H7 is a GE result, the "form" result comes from one trial.

**O2. A December study on the NLST participants Sybil never used** (CT-arm participants in none of Sybil's splits; public images in IDC). Counts from public metadata only (`results/x6/x6_unseen_metadata.json`; no image, no outcome read): 11,226 participants, 28,661 exams (years 0 to 2); **4,295 stretched exams** (2,093 participants; GE 2,214, Philips 1,699, Siemens 382); **823 consecutive pairs that change stretch status** (both GE 549, one GE 200, **neither GE 74**; the test had 88, 33 and 13). L0 (`lung_l0/RESULTS_L0.md`): only **34 participants with a later cancer** (29 exams with cancer within 1 year), because Sybil's sample took almost every CT-arm cancer; so this group cannot test accuracy. It would be pre-registered (plan, script, thresholds), re-checked by a fresh session, and approved by the lead before any scan is scored. Run: one night on two accounts. Parts:
- **O2a. Z-fix replication and a false-alarm measure.** H1, H2, H6 with the frozen definitions on 4,295 exams of people Sybil never saw; plus a new harm measure that needs no cancers: the **net change in Sybil's alarms** (as published vs with the true spacing; alarm = s1 ≥ the frozen τ90, the 90th percentile of s1 among cancer-free dev exams) per 1,000 stretched exams. Precision: about ±1 percentage point (±10 per 1,000). **The direction is uncertain:** test 27 alarms lost and 7 gained with the z-fix (the stretch added 26 alarms per 1,000), dev 38 and 31 (7 per 1,000; 998 exams), LIDC 11 and 8 (3 of 197). So the harm result may well be small. Cost about $16 to $18.
- **O2b. H7 on 823 changed pairs** (plus 810 not-stretched partner scans): the follow-up jump on people never seen, and for the first time with enough pairs outside GE (74 neither-GE, 200 one-GE). Cost about +$2 to $3.
- **O2c. A small "form" test:** a case-control sample (all exams of the cancer participants plus about 3,000 random cancer-free exams). With about 29 one-year cancers the interval of "Sybil minus findings" would be about ±0.10: supportive at best, and a noisy result can be misread. Cost about +$7 to $8.
- **Cost note (Correction):** the 20 Nov log estimate (about $11; $15 to $20 with the pairs) was too low. Recomputed from the cost per GB of S6 and LIDC: O2a about $16 to $18, O2a + O2b about $18 to $21, all three about $25 to $29 (measured; billed about 5% to 10% more).

**O3. A LIDC "form-like" test.** Needs the TCIA diagnosis file (157 of about 1,010 LIDC patients with a diagnosis at patient level: benign, primary or metastatic; part by biopsy, part by 2-year stability). LIDC has no screening findings form; the comparator would be the four LIDC readers' annotations (nodule size, malignancy rating 1 to 5): a different question ("Sybil vs readers' suspicion ratings"), small, supportive only. Access: only if TCIA's help desk says the file may be shared; no workaround. Cost about $1 to $2.

**O4. Tell Sybil's authors about the spacing error** (a GitHub issue or an e-mail): before a preprint, at submission, or after publication. For: research ethics, credibility, perhaps their confirmation. Against: they could fix and publish it first. Outward-facing: the lead decides.

**O5. A preprint first** (medRxiv) after O1, then O2 as a revision or a second paper.

**O6. One paper or two.** (A) A clinical paper: "Sybil vs the trial radiologists' recorded findings on its own test split" (L1, X1, X3). (B) A mechanism paper: the slice-spacing shortcut found at the feature level (H1 to H7, LIDC, code audit, O2). Or one combined "audit" paper (current outline: `RESULTS_L2.md` section 6, working title "Auditing a deployed lung-screening AI at the feature level, with rules fixed in advance").

Not available: a reader study; an outside cohort with outcomes; good local data.

## 5. Questions
- **Q1.** Rank the options by their chance of producing a high-impact paper. Which journal fits each path (current suggestion: *Radiology: Artificial Intelligence*; stretch *The Lancet Digital Health* or *npj Digital Medicine*)?
- **Q2.** One paper or two (O6)? What should the main message be?
- **Q3.** Is O2 worth about $18 to $29 and about three weeks? Which parts? Will journal reviewers accept "extra false alarms in people without cancer, at a threshold set on dev" as a harm? Which threshold would convince them?
- **Q4.** O2c: do it, keep it descriptive only, or drop it?
- **Q5.** How can the "form" finding be made stronger without new outcome data, honestly (no post-hoc confirmatory claims)?
- **Q6.** What are the three biggest weaknesses a journal reviewer will raise, and which option (if any) fixes each?
- **Q7.** Timing of O4 and O5.
- **Q8.** What did we miss? (Open data with outcomes reachable through IDC; analyses of existing outputs; framing.)

## 6. Read, in this order
1. `STATUS.md` (top block) and `imgsae/exploratory/lung_l2/RESULTS_L2.md` (all; sections 0, 1, 2.1b, 3b, 3c, 3d, 4 and 6 matter most).
2. `imgsae/exploratory/lung_l1/RESULTS_L1.md` and `imgsae/exploratory/lung_l0/RESULTS_L0.md` (the pre-registered "form" comparison; the unseen group).
3. `docs/EXECUTION_LOG.md`, entries of 18 to 20 November.
4. `docs/DATA_REQUEST_GUIDE.md` sections 0 and 7 (data access); `imgsae/exploratory/lung_l2/results/x4_code_audit.md`; `results/x2_idc_stretch_by_collection.csv`; `results/x6/x6_unseen_metadata.json` and `x6_unseen_metadata.py`.
5. If needed: `imgsae/exploratory/lung_l2/HYPOTHESES_L2.md` (the frozen family), `docs/LUNG_L2_PROTOCOL.md`, `docs/PROJECT_GUIDE.md` (steps N7 to N9), `results/s7/`, `results/s8/`, `results/x5/x5_lidc.json`.

## 7. What you may and must not do
- **May:** write `docs/REVIEW_PLAN_CHOICE.md` (your verdict and answers); add one entry to `docs/EXECUTION_LOG.md`; commit only these two files and push to `origin prostate-mri-plan`. Free local checks of committed files are fine (re-run a script into a temporary folder, never over a committed file).
- **Must not:** read any outcome or image of the never-used participants (no NLST table rows of those participants, no scoring), so that O2 can still be pre-registered cleanly; run any new analysis of the test outputs; run any cloud command or change `ledger.json`; change frozen files or analysis scripts; contact anyone outside (no e-mail, no GitHub issue); work around the TCIA block; put a name, e-mail or project name in any request to an outside service. Keep `New report .txt` and `imgsae/exploratory/ucla_audit/` out of git.

## 8. How to write
Read `docs/EXPLAINED_FOR_THE_LEAD.md`, Part A. The lead's first language is not English: short plain sentences; tables. Order: your ranked plan first; then the reasons with numbers; then what the lead must decide; then the full paths of the files you changed.

## 9. The executor's own view (read it only after you have formed yours)
- **Ranking:** (1) O2a + O2b in December, pre-registered; (2) meanwhile, the free parts of O1 that do not depend on O2 (figures, full literature search, checklists, a reproducibility re-run); (3) O4 at the preprint; (4) O3 only if TCIA says yes; (5) O2c dropped, or descriptive only.
- **Why:** O2a + O2b attack two of the three weak points (harm, and H7 being GE-only) on people Sybil never saw, for about $20. O2c cannot settle the "form" question with 29 to 34 cancers; the "form" finding rests on Sybil's own test split (L1 pre-registered, X1 and X3 consistent) and is best strengthened by framing and by the fair comparators already run (baseline screens, findings without the call, demographics on both sides).
- **One paper:** "an audit of a deployed lung-screening AI with rules fixed in advance": (1) it does not add to what the radiologists recorded; (2) a preprocessing shortcut inside it moves its score, found and localised at the feature level, replicated at other centres. I am not sure about this; two papers may suit two audiences better.
- **Main risk:** the false-alarm measure may come out near zero (dev and LIDC were close to balanced). Then the paper reports "the stretch moves the score a lot but changes few alarms", which is honest but weaker on harm.
