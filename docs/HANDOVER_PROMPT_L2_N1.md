# Execution prompt: check step R, freeze the shared axis, and make the new freeze (step N1)

For a fresh session: **Opus 5.5, effort xhigh**, working folder `D:\Shayan`. Paste everything below the line. Pasting it gives the lead's OK for what it contains.

**One choice for the lead before pasting (version of 2026-11-17, after step R):**
- **Default in this prompt (the reviewer's recommendation):** the new feature-level hypothesis enters as **H6** and **H2 stays**. Six hypotheses, Holm over six.
- If you want to keep five hypotheses, add one line at the top when you paste: "H6 replaces H2; H2 goes to the secondary list."
(On 2026-11-16 the plan said "at most one new hypothesis, in place of H2". The recommendation changed because H6 explains H2, so the two belong together. The effects on dev are large, so six instead of five costs almost no power.)

---

You are the executing session of a research project. Repository `D:\Shayan`, git branch `prostate-mri-plan` (also on GitHub, same commit). The project is a feature-level audit of the lung screening model Sybil on public NLST data ("Lung L2"). Discovery is on Sybil's dev split. **The test split is closed.** It is opened once, later, under frozen hypotheses. You do not open it in this session.

## Read first, in this order
1. `docs/PROJECT_GUIDE.md`: parts 6b, 7, 8 and 9 (the state, the plan, the rules).
2. `docs/REVIEW_S5_L2.md`: the review of the first freeze. It holds the changes you must make.
3. **`imgsae/exploratory/lung_l2/RESULTS_R_dev.md`: step R (2026-11-16 and 17). The reviewer session did the extra feature work on dev. Read all of it.**
4. `imgsae/exploratory/lung_l2/HYPOTHESES_L2.md` and `results/s5/`: the first freeze (commit `c593005`).
5. `docs/LUNG_L2_PROTOCOL.md`: sections 9 (9.4 arms, 9.5 validity marks, 9.6 naming, 9.8 gate), 10, 11, 14, 16a.
6. The code: `s4_common.py`, `s4_core.py`, `s4_decomp.py`, `s4_q1d.py`, `s5_freeze.py`, `s5_hashes.py`, `s6_frozen_analysis.py`, and the step R scripts `r1_arms.py`, `r2_shared.py`, `r4_axes_audit.py`, `r5_repair.py`, `r6_candidate.py`.
7. `docs/EXECUTION_LOG.md`, entries from 2026-11-16.

## The lead's OK (given by pasting this prompt)
1. **H5 is replaced by H5′** (review, section "What I propose instead").
2. **A new freeze commit** with the four small changes of the review (wording of H3 and H4 with the flag numbers; `wald()` with SD 0; the test-list script and its hash; LF hashes of the three text inputs).
3. **S6 in December** on account `shforghani2002`, with the thin margin and the frozen fallbacks. Not in this session.
4. **Amendment A6:** extra feature work on dev before the test opens. It is done (step R). Its result enters the freeze as **H6** (candidate C2 of `RESULTS_R_dev.md`, section 6), with C1 and the other axis numbers as secondary items.

## Step 0 (free)
1. `git status` and `git log -3`: the branch must equal `origin/prostate-mri-plan` and the tree must be clean.
2. Write the lead's OK into `docs/EXECUTION_LOG.md` (date, the four points, and the lead's choice of six or five hypotheses).
3. Add **amendment A6** to `docs/LUNG_L2_PROTOCOL.md` section 16a: "Step R: exploratory feature work on dev after the first freeze `c593005` (shared axes of the five members in layer `pooled`; plan and code commit `68f4637`; three steps added after seeing results, each logged before its run); approved by the lead; one hypothesis from it (H6) under the four conditions below." Commit and push.

## STEP F: check step R and freeze the axis (free, PC only, no cloud)
Step R was done by the session that reviewed the first freeze. **You are its first independent reader. Check it; do not trust it.**

**F1. Reproduce.** Run on dev: `r2_shared.py` (layer `pooled`), then `r4_axes_audit.py`, `r5_repair.py`, `r6_candidate.py` (outputs to a scratch folder, then compare with `results/r/`). These must come out again:
- shared axes in `pooled`: 12 and 11 in the two halves; shuffle null 0;
- axis 0 under z-fix: **−2.740 SD [−2.765, −2.714]**, halves −2.763 / −2.718; kernel +0.009;
- nothing removed: z-fix share 0.670, mean Δℓ̄_1 −0.326 (the S4 numbers);
- axis 0 removed: mean Δℓ̄_1 **+0.081 [0.042, 0.125]**; share 0.550; AUROC 0.9699 / 0.8496;
- C2: **+0.408 [0.403, 0.412]**, halves 0.412 / 0.404; random-choice 1 of 2,000 above +0.20.
If a number differs, stop and tell the lead.

**F2. Read the code with a critical eye.** At least: `Shared.fit` and `variates` in `r2_shared.py` (is the "other half" really untouched by the fit?); `remove` in `r4_axes_audit.py` (does it change only the one direction?); the D5 selection (ratio ≤ 0.65, same rows as S4); the SD reference; that the final axes are fitted on all dev and never see z-fix data. Write what you find into the log. A real error: stop and tell the lead.

**F3. Freeze the axes.** New script `s5_axes_freeze.py`: from `D:\Shayan\imgsae_data\lung_l2\r\r2_shared_pooled.pkl` write `results/s5/frozen_axes_pooled.npz`: per member the mean, SD, live mask, the 30 PCA directions, the scales, and the weight vectors of the 11 axes; plus the dev SD of each axis activation. Check: activations computed from this file equal the pickle's within 1e-9. Add the file, the script, and `run_info/heads.npz` (needed for `hidden_fc`) to the hash table.

**F4. H6 (from C2), exactly:**
- Population: T5 (the test z-fix exams, spacing/thickness ≤ 0.65), as H5′.
- Statistic: mean over exams of [Δℓ̄_1 with axis 0 set to the dev mean in every member] − [Δℓ̄_1 as Sybil gives it], where Δ = z-fix minus main, and ℓ̄_1 is the mean of the five member logits computed from the saved `pooled` through Sybil's own `hidden_fc`, ReLU and head. Frozen dev axis, no refit, no outcomes.
- Direction `>`, null **+0.20**. Dev: +0.408 [0.403, 0.412].
- Secondary (reported, never called confirmed): C1 (axis 0 shift, dev −2.74 SD); for each of the 11 frozen axes the agreement of the five members in test (how many reach 0.70) and the z-fix and kernel changes; the share of exams moving ≥ 0.25 SD with axis 0 off (dev 0.550); AUROC with axis 0 off (with the C6 caution).
- The four conditions (gate 9.8; random-choice test; no refit on test; honest chance) are met on dev: see `RESULTS_R_dev.md`, section 6. Copy the evidence into the hypothesis file.

**F5. No new discovery.** Do not search for more axes, features or hypotheses. If you see something interesting, write it down as "exploratory, after the test". The SAE and the other arms stay "not valid"; the paper reports that as a result.

## STEP N1: the new freeze (free)
Follow `docs/PROJECT_GUIDE.md`, part 8, step N1, items 1 to 8. In short:
1. `s5_h5prime_dev.py`: dev evidence for H5′ on the 924 D5 exams. It must give **−0.0566 [−0.0590, −0.0541], halves −0.0565 / −0.0567**. Also the N, mixed and residual terms, and the random-choice test for H5′ (random sets of 6 of the 56 families: how often is their mean z-fix change below −0.02?). Report that number honestly. If 5% or more of the random sets pass, stop and tell the lead before freezing H5′.
2. `s5_freeze.py`: H5 → H5′ (statistic: mean of G_T(zfix) − G_T(main) for ℓ̄_1, frozen raw-unit dictionary and labels; population T5; direction `<`; null −0.02). **H6 as in F4.** H4 renamed "the kernel changes the flag in fewer than 5% of exams". New secondary items: flags lost, flags gained, share of discordant flags among exams flagged in either run (z-fix and kernel); the change of the N, mixed and residual terms; the old H5 share; the H6 secondary items. LF hashes for the three text inputs.
3. `s6_frozen_analysis.py`: H5′ and H6 in the z-fix block (H6 needs `pooled` of the main and the z-fix run, `frozen_axes_pooled.npz` and `heads.npz`); `wald()` returns p = 0 when the SD is 0 and the estimate is on the right side of the null, else 1; the new secondary numbers. Holm over six (or five, by the lead's choice).
4. `s6_manifest_test.py`: **write and test on dev only; do not run it on test.** Main rows = the split file's 6,715 series (tiers T1, T2, T3 by study year). T4 = 500 soft-kernel partners of T1 exams: same pair rule as `s1_manifest.py`, seed 0, same quota rule by maker. Metadata and the split file only; no outcome is read. Test: run its pair logic on dev and reproduce the D4 rows of `manifest_dev.csv`.
5. Check that the S6 extraction saves `pooled` for the main and the z-fix run (it did on dev). Run `s5_freeze.py`, then the frozen analysis on dev. **H1 to H4 must equal the first freeze exactly.** H5′ must equal item 1. H6 must equal F1.
6. `HYPOTHESES_L2.md`: the new H5′ and H6; a section "Changes after the first freeze `c593005`" (what, why, who proposed it, that it was chosen from dev, that H6 comes from exploratory work done by the reviewer session, with the steps that were added after seeing results); the note "the z-fix shows sensitivity, not harm" with the dev numbers; the two-direction flag numbers; the new hash table from `s5_hashes.py`, including the new scripts and files.
7. Update `docs/REVIEWER_BRIEF_L2.md` if file paths changed. Write `docs/PROMPT_REVIEW_S5b.md`: a short prompt for the re-check of the new freeze (hashes, dev as if test, the H5′ and H6 code, the frozen axes file, the test-list script, the diff from `c593005`). **It must say that the reviewer of the first freeze did step R, so the re-check has to be done by a fresh session that reads step R as an outsider.**
8. Commit, push, log the new freeze commit, update `STATUS.md` and the step states in `docs/PROJECT_GUIDE.md`.

## STOP
Stop after step N1. Do not start S6. The next steps are the re-check (N2) and the lead's OK (N3).

## What you must not do
- **No test data:** do not open, extract, list or analyse any test-split file; do not run the test-list script on test; no new analysis of the L1 test scores.
- **No cloud:** no Modal command that runs anything; no change to `ledger.json`. Steps F and N1 are free and local.
- **No package install** without telling the lead first.
- Do not change the meaning of H1 to H4, their statistics, nulls or thresholds.
- Do not change the step R scripts or `results/r/` (a needed fix is a logged deviation, with the old result kept).
- Do not touch the lead's other apps and volumes, the third Modal profile, or the "reserve".
- Keep `New report .txt` and `imgsae/exploratory/ucla_audit/` out of git. Do not raise the lead's earlier prostate manuscript.
- Privacy: no name, email or project name in any request to an outside service.

## Stop and ask the lead when
- a step R number, H5′ or any H1 to H4 value does not reproduce;
- you find an error in the step R code;
- the random-choice test rejects H5′;
- anything is unclear about test data;
- a step needs a package, money, or a rule change.

## Environment
- Windows, PowerShell (not Bash).
- Scripts: `D:\Shayan\imgsae\.venv\Scripts\python.exe`, with `OMP_NUM_THREADS`, `MKL_NUM_THREADS` and `OPENBLAS_NUM_THREADS` = 4.
- `r4_axes_audit.py`, `r5_repair.py` and `r6_candidate.py` each need 15 to 30 minutes on this PC. Start long jobs detached, with a log file.
- The laptop GPU runs at about 10% speed (hardware fault). You do not need it for this prompt.

## Records
- Every decision, deviation and result goes into `docs/EXECUTION_LOG.md`. The state goes into `STATUS.md`.
- Commit and push after every finished step (Step 0; F check and frozen axes; the new freeze).

## How to write to the lead
The lead's first language is not English. Use short, plain sentences. Start with the result, then the numbers, then what you need from the lead. End with the paths of the files you changed.
