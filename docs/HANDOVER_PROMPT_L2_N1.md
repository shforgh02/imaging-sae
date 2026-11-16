# Execution prompt: more feature work on dev (step NF) and the new freeze (step N1)

For a fresh session: **Opus 5.5, effort xhigh**, working folder `D:\Shayan`. Paste everything below the line. Pasting it gives the lead's OK for what it contains. If the lead does not want step F, delete the block marked "STEP F" before pasting.

---

You are the executing session of a research project. Repository `D:\Shayan`, git branch `prostate-mri-plan` (also on GitHub, same commit). The project is a feature-level audit of the lung screening model Sybil on public NLST data ("Lung L2"). Discovery is on Sybil's dev split. **The test split is closed.** It is opened once, later, under frozen hypotheses. You do not open it in this session.

## Read first, in this order
1. `docs/PROJECT_GUIDE.md`: parts 6b, 7, 8 and 9 (the state, the plan, the rules).
2. `docs/REVIEW_S5_L2.md`: the review of the first freeze. It holds the changes you must make.
3. `imgsae/exploratory/lung_l2/HYPOTHESES_L2.md` and `results/s5/`: the first freeze (commit `c593005`).
4. `docs/LUNG_L2_PROTOCOL.md`: sections 9 (9.4 arms, 9.5 validity marks, 9.6 naming, 9.8 gate), 10, 11, 14, 16a.
5. `imgsae/exploratory/lung_l2/RESULTS_S4_dev.md` and the S4 code (`s4_common.py`, `s4_core.py`, `s4_decomp.py`, `s4_q1d.py`, `s5_freeze.py`, `s5_hashes.py`, `s6_frozen_analysis.py`).
6. `docs/EXECUTION_LOG.md`, entries from 2026-11-16.

## The lead's OK (given by pasting this prompt; lead's words of 2026-11-16: "we do all you ask, put in plan, push and give prompt")
1. **H5 is replaced by H5′** (review, section "What I propose instead").
2. **A new freeze commit** with the four small changes of the review (wording of H3 and H4 with the flag numbers; `wald()` with SD 0; the test-list script and its hash; LF hashes of the three text inputs).
3. **S6 in December** on account `shforghani2002`, with the thin margin and the frozen fallbacks. Not in this session.
4. **Amendment A6** (step F below): more feature work on dev before the test opens.

## Step 0 (free)
1. `git status` and `git log -3`: the branch must equal `origin/prostate-mri-plan` and the tree must be clean.
2. Write the lead's OK into `docs/EXECUTION_LOG.md` (date, the four points).
3. Add **amendment A6** to `docs/LUNG_L2_PROTOCOL.md` section 16a, with the text of step F below, marked "exploratory on dev; made after the first freeze `c593005`; approved by the lead on the date of this session". Commit and push.

## STEP F: more feature work on dev (free, PC only, no cloud). Time limit: finished by 2026-11-26
**Why:** the reviewer found that Sybil's vector `h` has only about 5 to 7 real dimensions, and that the earlier saved layer `pooled` has more shared directions (about 14 against 6; dev, 2,500 exams, no outcomes). The lead asks whether another layer or another method can give usable features. The test cannot run before 1 December, so this time is free.

**Rules for step F:**
- Dev data only. `s4_common.load` already refuses other data.
- **Write and test all F code first** (synthetic data and the 300-exam pilot, as in P4a). Commit it as "F code fixed" and push. Only then run on all dev data. Do not change an F script after its full-dev result is seen; a needed fix is a logged deviation.
- Same fairness rules as S4: same K, same consensus rule, same validity marks for every arm.
- Everything from F is discovery. Report every failed mark as failed.

**F1. The six arms on the `pooled` layer.**
- Input: `pooled` (1,536 numbers per member) from `arrays_dev_main.npz`; each dimension z-scored with dev mean and SD.
- First check: `hidden_fc` applied to the saved `pooled` gives the saved `pre` within 1e-3, for every member (weights in `run_info/heads.npz`). If not, stop.
- Arms: the same six as protocol 9.4, K = 64 (K = 128 only if time allows), same seeds and consensus rule.
- Raw-unit rule at this layer (label-free): with each exam's own ReLU pattern and hazard gating fixed, the logit is exactly linear in `pooled`. The contribution of unit j is its effective weight times (pooled_j − dev mean). Take the K units with the largest SD of contribution to ℓ_{m,6}.
- Validity marks V1 to V4 as protocol 9.5. For V1 the reconstruction goes through the real network: `hidden_fc` → ReLU → Sybil's head.
- Families, naming and group shares as 9.6 and 9.2 (with the exact per-exam linear weights above).

**F1b. SAE sparsity check on `h` (a sensitivity check; it does not change the primary-arm rule).**
- The same SAE arm as S4, K = 64, with k = 8, 16 and 32 active features (S4 used k = 4). Report V1 to V4 for each.
- Purpose: to show whether the SAE failed because of its sparsity setting or because of Sybil's representation.

**F2. Shared axes (for `h` and for `pooled`).**
- Halves: the two participant halves of S4 (`s4_common.halves`). Fit on half A, judge on half B; then swap and report both.
- Per member: z-score, then PCA to 30 components (fit on the fitting half).
- Multiset CCA (MAXVAR: whiten each member's 30 scores, join the five blocks, SVD). An axis is **shared** if, on the other half, the mean pairwise correlation of its five member variates is at least 0.70. Axis activation = the mean of the five member variates.
- Null check: the same with the exam order shuffled inside each member (seed 0). The shuffled data must give no shared axis.
- For each shared axis report: correlation with ℓ̄_1 and ℓ̄_6; the group label by the method of 9.6 and its agreement between halves; the paired change under z-fix (D5) and under kernel change (D4), in SD units, with participant-bootstrap intervals and halves; the within-person correlation T0 to T1; AUROC for y1 and y6 and the added value over F (cross-fitted), always with the C6 caution (dev flatters Sybil).
- Mark the **non-risk axes**: |r| with ℓ̄_1 below 0.5.

**F3. Where Sybil looks (descriptive only; never a hypothesis).**
- From `att_vol1` and `att_vol2` (25 slices): the centre of attention along z and the share of attention in the first and last 3 slices.
- Compare: exams with and without `lung_cut_z`; main against z-fix in D5; cancers by recorded location (upper, middle or lingula, lower), only for groups with at least 10 cancers.

**F4. Report.** `imgsae/exploratory/lung_l2/RESULTS_F_dev.md` and result files in `results/f/`. Start with a short answer for the lead in plain words. Then the validity tables, the shared axes, the candidates and the failed marks.

**When may an F result become a hypothesis? All four must hold:**
1. It meets gate 9.8 (right direction, dev 95% interval excluding the null, same side of the null in both halves), and for a feature-based claim the arm is valid or the axis is shared in both half-directions.
2. **Random-choice test:** draw the same number of units, families or axes at random at least 2,000 times. If 5% or more of the random draws also pass the hypothesis, it is near-automatic and is rejected. (This is the lesson of the first H5.)
3. It can be computed on test from what S6 saves anyway (`h`, `pooled`, variants), with frozen dev axes or dictionaries and no refit.
4. If it uses outcomes, your honest chance estimate on test is at least 0.5, given C6 and the L1 test result.
- **At most one** F hypothesis. If one enters, **H2 moves to the secondary list** (H1 and H3 keep the z-fix magnitude and the flag). Say plainly in the hypothesis file that the lead may reject this at the stop.
- If none qualifies, say so. That is a valid outcome.

**Time limit:** if F is not complete on 2026-11-26, write what is done, make the freeze of step N1 without an F hypothesis, and list the rest of F as exploratory work to finish later.

## STEP N1: the new freeze (free)
Follow `docs/PROJECT_GUIDE.md`, part 8, step N1, items 1 to 8. In short:
1. `s5_h5prime_dev.py`: dev evidence for H5′ on the 924 D5 exams. It must give **−0.0566 [−0.0590, −0.0541], halves −0.0565 / −0.0567**. Also the N, mixed and residual terms, and the random-choice test for H5′ (random sets of 6 of the 56 families: how often is their mean z-fix change below −0.02?). Report that number honestly. If 5% or more of the random sets pass, stop and tell the lead before freezing H5′.
2. `s5_freeze.py`: H5 → H5′ (statistic: mean of G_T(zfix) − G_T(main) for ℓ̄_1, frozen raw-unit dictionary and labels; population T5; direction `<`; null −0.02). H4 renamed "the kernel changes the flag in fewer than 5% of exams". New secondary items: flags lost, flags gained, share of discordant flags among exams flagged in either run (z-fix and kernel); the change of the N, mixed and residual terms; the old H5 share. LF hashes for the three text inputs.
3. `s6_frozen_analysis.py`: H5′ in the z-fix block; `wald()` returns p = 0 when the SD is 0 and the estimate is on the right side of the null, else 1; the new secondary numbers; the F hypothesis if one entered.
4. `s6_manifest_test.py`: **write and test on dev only; do not run it on test.** Main rows = the split file's 6,715 series (tiers T1, T2, T3 by study year). T4 = 500 soft-kernel partners of T1 exams: same pair rule as `s1_manifest.py`, seed 0, same quota rule by maker. Metadata and the split file only; no outcome is read. Test: run its pair logic on dev and reproduce the D4 rows of `manifest_dev.csv`.
5. Run `s5_freeze.py`, then the frozen analysis on dev. **H1 to H4 must equal the first freeze exactly.** H5′ must equal item 1.
6. `HYPOTHESES_L2.md`: the new H5′ (and the F hypothesis, if any); a section "Changes after the first freeze `c593005`" (what, why, who proposed it, that it was chosen from dev); the note "the z-fix shows sensitivity, not harm" with the dev numbers; the two-direction flag numbers; the new hash table from `s5_hashes.py`, including the new scripts.
7. Update `docs/REVIEWER_BRIEF_L2.md` if file paths changed. Write `docs/PROMPT_REVIEW_FABLE_S5b.md`: a short prompt for the reviewer to re-check the new freeze (hashes, dev as if test, the H5′ code, the test-list script, the diff from `c593005`, and the F hypothesis if any).
8. Commit, push, log the new freeze commit, update `STATUS.md` and step states in `docs/PROJECT_GUIDE.md`.

## STOP
Stop after step N1. Do not start S6. The next steps are the reviewer's re-check (N2) and the lead's OK (N3).

## What you must not do
- **No test data:** do not open, extract, list or analyse any test-split file; do not run the test-list script on test; no new analysis of the L1 test scores.
- **No cloud:** no Modal command that runs anything; no change to `ledger.json`. Steps F and N1 are free and local.
- **No package install** without telling the lead first.
- Do not change the meaning of H1 to H4, their statistics, nulls or thresholds.
- Do not touch the lead's other apps and volumes, the third Modal profile, or the "reserve".
- Keep `New report .txt` and `imgsae/exploratory/ucla_audit/` out of git. Do not raise the lead's earlier prostate manuscript.
- Privacy: no name, email or project name in any request to an outside service.

## Stop and ask the lead when
- H5′ or any H1 to H4 value does not reproduce;
- the `hidden_fc` check of F1 fails;
- the random-choice test rejects H5′;
- anything is unclear about test data;
- a step needs a package, money, or a rule change.

## Environment
- Windows, PowerShell (not Bash).
- Scripts: `D:\Shayan\imgsae\.venv\Scripts\python.exe`, with `OMP_NUM_THREADS`, `MKL_NUM_THREADS` and `OPENBLAS_NUM_THREADS` = 4.
- The laptop GPU runs at about 10% speed (hardware fault). SAE fits are slow: plan the order so that F2 and F3 (CPU, fast) come first, then F1, then F1b.
- Long local jobs: start them detached, write progress to a log, save each finished unit at once, and make them resumable.

## Records
- Every decision, deviation and result goes into `docs/EXECUTION_LOG.md`. The state goes into `STATUS.md`.
- Commit and push after every finished step (Step 0; F code fixed; F results; the new freeze).

## How to write to the lead
The lead's first language is not English. Use short, plain sentences. Start with the result, then the numbers, then what you need from the lead. End with the paths of the files you changed.
