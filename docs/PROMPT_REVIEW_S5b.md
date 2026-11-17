# Prompt for the re-check of the second freeze (step N2)

Paste everything below the line into a **fresh session** (working folder `D:\Shayan`; Fable 5.2 or Opus 5.5, effort high or xhigh), or give the short prompt: "Read `docs/PROMPT_REVIEW_S5b.md` and do what it says below its line."

**Who must do it.** The reviewer of the first freeze (the Fable 5.2 session of 16 and 17 November) also did steps R, R2 and R3, the exploratory dev work from which H6 and H7 come. So this re-check must be done by **a session that did not do step R** and that reads step R as an outsider. Do not continue that session.

---

You are the reviewer of a hypothesis freeze in a research project. Repository `D:\Shayan`, git branch `prostate-mri-plan` (also on GitHub, `github.com/shforgh02/imaging-sae`, same commit). The project is a feature-level audit of the lung screening model Sybil on public NLST data ("Lung L2"). Discovery was done on Sybil's dev split. **The test split is still closed.** It is opened once, after your note and the lead's OK.

**Your task:** re-check the second freeze (step N1 of `docs/PROJECT_GUIDE.md`). Answer items 1 to 8 of `docs/REVIEWER_BRIEF_L2.md` for the new freeze, plus the extra checks below, and give a verdict: approve / approve with changes / reject. You did not do step R; the session that reviewed the first freeze did. Read step R critically, as an outsider.

## Key commits
- `c593005`: the first freeze (five hypotheses), reviewed in `docs/REVIEW_S5_L2.md` (approve with changes).
- `68f4637`, `52b5e83`: plan and code commits of step R and R2 (exploratory dev work after the first freeze; amendment A6).
- `5cc5e5e`: the lead's OK recorded; amendment A6 in the protocol.
- `292fd3a`: step F (the executor reran step R: 0 differences; the shared axes frozen; H5′ evidence).
- **`c3578c3`: the second freeze commit. Review this commit** (log entry "2026-11-17: step N1 done: second freeze"). Check with `git diff --stat c3578c3 HEAD` that later commits touch no frozen or analysis file. Note: `git diff c593005 c3578c3` also shows the ledger change of commit `96d3c12` (the lead's money decision of 17 Nov, made by the reviewer session), the step R files, and the plan documents.

## Read, in this order
1. `docs/REVIEWER_BRIEF_L2.md` (items 1 to 8) and `docs/REVIEW_S5_L2.md` (the first review and its changes 1 to 6).
2. `imgsae/exploratory/lung_l2/HYPOTHESES_L2.md`: six hypotheses (H1 to H4, H6, H7), the section "Changes after the first freeze", the secondary items, the S6 run plan on two accounts, the hash table.
3. `docs/LUNG_L2_PROTOCOL.md`: sections 9.5, 9.8, 10, 11, and 16a (amendments A1 to A6).
4. `imgsae/exploratory/lung_l2/RESULTS_R_dev.md` (step R: all of it) and `results/r/`.
5. `docs/EXECUTION_LOG.md`, entries of 2026-11-16 and 2026-11-17 (step R notes 1 to 7, R2, R3; the executor's step F and N1 entries).
6. Code: `s5_axes_freeze.py`, `s5_freeze.py`, `s5_h5prime_dev.py`, `s6_frozen_analysis.py`, `s6_attention.py`, `s6_manifest_test.py`; and the step R scripts behind H6 and H7: `r1_arms.py` (`load`), `r2_shared.py` (`Shared`), `r4_axes_audit.py` (`remove`), `r5_repair.py`, `r6_candidate.py`, `r7_more.py`, `r9_attention.py`.

## Extra checks for this freeze
1. **Hashes.** Every row of the table at the end of `HYPOTHESES_L2.md` matches the committed files (`results/s5/` is byte-exact: `Get-FileHash`; other text files: compare git blob ids with `git ls-tree <freeze> -- <path>`; do not pipe `git show` into a hash in PowerShell). The three PC-only inputs (`heads.npz`, the calibrator, `r2_shared_pooled.pkl`) with `Get-FileHash`. In `frozen_thresholds_L2.json`, the three text inputs are now hashed on their LF bytes (review change 5).
2. **Dev as if test.** Rerun the frozen analysis on dev into a temporary folder (never over the committed file) and compare with `results/s5/s6_dev_as_if_test.json` (expect byte-identical): H1 to H4 must equal the first freeze (`git show c593005:imgsae/exploratory/lung_l2/results/s5/s6_dev_as_if_test.json`); H6 must equal `results/r/r6_candidate_pooled.json` (C2) and H7 `results/r/r7_more_pooled.json` (A, all pairs).
3. **The frozen axes.** Do the numbers in `frozen_axes_pooled.npz` equal the pickle `D:\Shayan\imgsae_data\lung_l2\r\r2_shared_pooled.pkl`? Were the axes fitted on dev main runs only (never z-fix, never test)? Does `remove()` change only the one direction? Is H6's code in `s6_frozen_analysis.py` the same computation as `r6_candidate.py`?
4. **H7.** Pairs, the stretched rule (a recorded ratio of 0 counts as stretched; see the step F log, item 6), the frozen form model, the bootstrap unit. Is the label "partly seen" right (an approximate version can be computed from the L1 test scores, the form and public metadata; nobody computed it)? Is one partly-seen hypothesis acceptable here?
5. **H5′.** `s5_h5prime_dev.py` and `results/s5/s5_h5prime_dev.json`: H5′ reproduces the review (−0.0566) but 59.7% of random sets of 6 families also pass its null. The lead moved H5′ to the secondary list. Is the random-choice test fair? Is the decision recorded?
6. **Step R as an outsider.** Steps were added after seeing results (plan table of `RESULTS_R_dev.md`). Do the four conditions of A6 hold for H6 and H7 (gate 9.8; random-choice or permutation test below 5%; no refit on test; honest chance ≥ 0.5)? Is anything fished? Are the chance estimates (H6 0.90, H7 0.65, H3 0.55) honest?
7. **Harm and attention items.** Pre-stated as secondary, with the size of harm the test can detect, before any test data. Is anything there a hidden hypothesis or a hidden use of outcomes before the primary result is saved?
8. **The test-list script.** `s6_manifest_test.py`: no outcome read (only the split name and the series UIDs of the split file); the pair rule, seed and quota of `s1_manifest.py`; its dev check reproduces `manifest_dev.csv` byte for byte (`results/s6_manifest_devcheck.json`). You may rerun the dev check into a temporary folder (`--root dev`). **Never run it with `--root test`.**
9. **The diff from `c593005`.** `git diff --stat c593005 <freeze>`: only the changes listed in "Changes after the first freeze"; the statistics, populations, nulls and thresholds of H1 to H4 unchanged.

## Commands (all local and free; venv python, 4 BLAS threads)
- `$env:OMP_NUM_THREADS=4; $env:MKL_NUM_THREADS=4; $env:OPENBLAS_NUM_THREADS=4; cd D:\Shayan\imgsae\exploratory\lung_l2`
- Dev as if test (about 4 minutes): `D:\Shayan\imgsae\.venv\Scripts\python.exe s6_frozen_analysis.py D:\Shayan\imgsae_data\lung_l2\dev dev results\s5 D:\Shayan\imgsae_data\lung_l2_vol\l2\run_info <temp>\s6_check.json`
- Attention (dev): `... s6_attention.py D:\Shayan\imgsae_data\lung_l2\dev D:\Shayan\imgsae_data\lung_l2_vol\l2\dev\main D:\Shayan\imgsae_data\nlst_public\tables dev <temp>\att.json` (add `--dev-check results\r\r9_attention_dev.json` to compare with step R3 on half B).
- Test-list dev check: `... s6_manifest_test.py D:\Shayan\imgsae_data\idc_index_25.0.5\nlst_series_meta.csv "D:\Shayan\imgsae_data\nlst_public\Shetty_et_al(Google)_data_splits.p" <temp> --root dev`
- Frozen axes: `... s5_axes_freeze.py D:\Shayan\imgsae_data\lung_l2\dev D:\Shayan\imgsae_data\lung_l2_vol\l2\run_info\heads.npz <temp>` writes a new copy into `<temp>` (an npz has time stamps, so compare the arrays with `np.load`, not the bytes).
- H5′ evidence: `... s5_h5prime_dev.py D:\Shayan\imgsae_data\lung_l2\dev results\s5 D:\Shayan\imgsae_data\lung_l2_vol\l2\run_info\heads.npz <temp>\h5p.json`
- To rerun a step R script, set `$env:L2_S4_DATA` to a temporary folder first and run `r2_shared.py` there first (otherwise the saved pickle is overwritten).

## What you may do
- Append a dated section "Re-check of the second freeze" to `docs/REVIEW_S5_L2.md`: the verdict; one line per brief item 1 to 8 and per extra check 1 to 9; other comments; any change you propose; what the lead must decide.
- Add one entry to `docs/EXECUTION_LOG.md`. Commit only these two files and push to `origin prostate-mri-plan`.

## What you must not do
- Do not change `HYPOTHESES_L2.md`, any file in `results/s5/` or `results/r/`, or any analysis script. Do not run `s5_freeze.py` or `s5_hashes.py` in the repository (they rewrite frozen files). If something must change, propose it; the executor makes a new freeze commit after the lead's OK.
- **No test data:** do not open, extract, list or analyse any test-split file; do not run the test-list script on test; no new analysis of the L1 test scores.
- No Modal or cloud command; no change to `ledger.json`; no package install.
- Do not touch the lead's other apps or volumes on any account.
- Keep `New report .txt` and `imgsae/exploratory/ucla_audit/` out of git. Privacy: no name, email or project name in any request to an outside service.

## Environment and how to write
- Windows, PowerShell (not Bash). Scripts: `D:\Shayan\imgsae\.venv\Scripts\python.exe`.
- Read `docs/EXPLAINED_FOR_THE_LEAD.md`, Part A. The lead's first language is not English: short plain sentences; the verdict first, then the reasons with numbers, then what the lead must decide, then the full paths of the files you changed.
