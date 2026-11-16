# Review of the S5 freeze (Lung L2)

- **Reviewer:** Fable 5.2, as the external (second) reviewer of protocol section 10. **Date:** 2026-11-16.
- **Freeze reviewed:** commit `c593005` (`HYPOTHESES_L2.md`, `results/s5/`, `s6_frozen_analysis.py`).
- **Verdict: APPROVE WITH CHANGES.** One change is needed (H5). Four changes are small. H1 to H4 can stay as they are.
- **What I did:** read every file named in the review prompt; checked all hashes; re-ran the frozen analysis on dev; ran my own checks on dev data (free, on the PC).
- **What I did not do:** no test data opened, no test manifest, no cloud command, no change to any frozen file, analysis script or the ledger, no package installed.
- **Limit:** my own dev checks were made with two short scripts that are not in the repository (the prompt lets me commit two files only). They are in `C:\Users\Arman\AppData\Local\Temp\claude\5cb39bed92095523\18e76a8d-cb84-406e-be0d-f8659fdd96db\scratchpad\` (`rev_checks.py`, `rev_checks2.py`, output `rev_checks.json`). That folder is temporary. If a number from them is used, the executor must reproduce it with a committed script.

## Summary for the lead
1. **The freeze is clean.** All 22 hashes match. Nothing frozen changed after the freeze. The frozen analysis refits nothing. My dev re-run gives a file that is byte-identical to the committed one. No test data exist anywhere I looked.
2. **H1 to H4 are sound.** They are honest, new on test, and correctly tested. The margins of H2 to H4 were set after dev was seen. This is disclosed, and I accept it.
3. **H5 must change.** As frozen, H5 cannot fail and does not test what its name says. Any 6 of the 56 families pass its test. The 6 "technical" families carry less of the score than an average set of 6 families.
4. **There is a better H5 in the dev data.** When the slice spacing is corrected (z-fix), the "technical" families move strongly and the "nodule" families do not move. This is a real test of the technical label. It costs nothing extra.

## Items 1 to 8 of the brief

| # | Item | Answer |
|---|---|---|
| 1 | At most five hypotheses, each fully stated | **Yes.** Five. Each has its statistic, population, direction, margin, null and test. H1, H2 and H3 are three views of one intervention on the same exams, so the family holds about three independent findings. |
| 2 | Dev only | **Yes.** The folder `results/runs/` has 17 files. The 15 run records have `root` = `dev`, `l4`, `rep` or `xacct` (all are dev D1 series); the 2 smoke files have no `root` value (the log says the smoke runs used 3 dev D1 series and the demo case). None has `test`. The ledger has 14 L2 runs, none on test. The PC data folders hold no test folder (names only read). The S4 results were committed (`86861f4`) before the freeze. |
| 3 | New quantity | **Yes.** H1 to H3 need z-fix runs, H4 needs soft-kernel partners, H5 needs `h`. None was ever computed on test by this project (L1 scored one series per exam and saved scores only). None is partly seen. |
| 4 | Multiplicity | **Yes.** Holm is coded correctly, one-sided, α = 0.05, with 5 in the family even if a hypothesis is not evaluated (this is the strict choice). Participant bootstrap, 2,000 draws, seed 0. One small bug: see change 3. |
| 5 | Frozen means frozen | **Yes.** Details below. Two small points: see changes 4 and 5. |
| 6 | Honest dev evidence | **H1, H2: yes. H3, H4: yes, with the disclosed caveat. H5: no, in substance.** All cited numbers and counts are in the committed files and match. H3 and H4 failed the margins written before the full-dev run and hold only under the S5 margins. H5 holds the gate as written, but the gate proves nothing for it (see below). |
| 7 | Fair comparisons | **Yes, as written.** Raw units passed V1 to V4 at K = 64 and K = 128. H5 compares no arms. Comment: V3 and V4 are weak marks for raw units (see "Other comments", point 1). V4 passes by 0.006 (0.706; needed 0.70). |
| 8 | Anything else | **H5** (main point). Also the wording of H3 and H4, and how "error" is used for the z-fix. See below. |

## Item 5 in detail
- **Hashes:** 20 committed files checked by SHA-256 of the committed bytes and by git blob id, at `c593005` and at `HEAD`: 20 of 20 match. The 6 files of `results/s5/` also match byte for byte in the working copy. The 2 PC-only inputs (`heads.npz`, the calibrator) match. `HYPOTHESES_L2.md` has the same blob at `1b23e45`, `c593005` and `HEAD`.
- **After the freeze:** `git diff c593005 HEAD` touches `STATUS.md`, the log, the review prompt, `RESULTS_S4_dev.md`, its tables file, and six new K = 128 files (SAE, NMF, k-means). No frozen file and no analysis script.
- **The script:** it checks the frozen hashes first and stops if one differs. It has no fitting call. The dictionary is rebuilt from saved numbers. The F+I model and the combinations are applied with frozen coefficients. It refuses a table with rows outside the stated root.
- **Dev as if test:** my re-run output is byte-identical to `results/s5/s6_dev_as_if_test.json`. The five statistics and their intervals equal the S4 dev values (difference 0.0).

## The main point: H5

### Why H5 fails as frozen
- **H5 is a "near-automatic" candidate.** `RESULTS_S4_dev.md` ("Cautions") says that the Q1b group shares hold almost by construction and "will not be used as hypotheses". H5 is exactly the Q1b group share of T (gate row `Q1b_share_T_lbar1`), with the null moved from 0 to 0.03.
- **Any 6 families pass.** I drew 6 of the 56 families at random, 20,000 times (dev, 7,336 exams). The share of Var(ℓ̄_1) was 0.075 on average (95% range 0.053 to 0.100). It was above 0.03 in 100% of the draws. It was above the T value (0.0505) in 98% of the draws.
- **So the T families carry less than an average set of 6 families.** The 56 families together carry 0.70, which is 0.0125 per family.
- **The T term is mostly a copy of the score.** Correlation of G_T with ℓ̄_1: 0.958. The technical variables explain 14% of G_T (out-of-fold ridge). The rest follows the score.
- **The interval shows it.** The dev interval is [0.0501, 0.0509]. A test with such an interval and a null of 0.03 cannot fail unless the test data are broken.
- **The name says more than the test.** "Technical-named features carry a part of Sybil's score" will be read as "5% of Sybil's score is technical". Q1a puts the technical share at 0.016. The S5 file itself says that H5 does not test the technical label on test.

### What I propose instead (H5′)
The dev data hold a real test of the technical label. The file `results/s4/s4_q1d_dev.json` (`zfix.D5.group_change.t1`), committed before the freeze, already has the point values. I added intervals and halves (dev, D5: 924 exams, 424 participants).

| Term | Change with z-fix, mean [95% CI]; halves | Part of the mean shift (−0.326) | Part of Var(ℓ̄_1) |
|---|---|---|---|
| T families (6) | −0.0566 [−0.0590, −0.0541]; −0.0565 / −0.0567 | 17.4% [16.0%, 19.2%] | 5.0% |
| N families (34) | +0.005 [−0.013, +0.025]; +0.007 / +0.003 | about 0 | 44.6% |
| Mixed families (16) | −0.197 [−0.206, −0.187]; −0.195 / −0.199 | 60% | 20.5% |
| Residual | −0.101 [−0.107, −0.094] | 31% | 16.6% |

- The T term falls in 96% of the exams. The activations of the T units rise by 1.3 to 1.8 SD.
- The change is the same with a lung cut by the crop (−0.058, 756 exams) and without (−0.050, 168 exams), and in both stretch classes (−0.060 and −0.051).
- With a kernel change the T term does not move (+0.0004; committed file).
- **Meaning:** the families were named "technical" from correlations between exams. The z-fix is an intervention inside one exam. The technical families answer to it, and the nodule families do not. This is not automatic. It could fail on test if the labels were a dev artefact.

**H5′ (proposed):** statistic = mean of G_T(zfix) − G_T(main) for ℓ̄_1, with the frozen dictionary and labels; population T5; direction <; null −0.02; same test as the others.
- **Why −0.02:** if the z-fix shift were spread over the terms in proportion to their part of the score, the T term would move by 0.0505 × (−0.326) = −0.0165. The null −0.02 is a little stricter than that.
- **Dev:** −0.0566 [−0.0590, −0.0541]; halves −0.0565 / −0.0567. Gate 9.8 holds.
- **Chance on test (mine):** about 0.95.
- **Protocol 10:** it uses a z-fix change and a group contribution, both never computed on test.
- **Cost:** none. T5 is already in the run plan, and the job already saves `h` for z-fix rows. The code is `split_by_label` on the z-fix `h`, as in `s4_q1d.group_change`.
- **Secondary, next to it:** the same change for the N, mixed and residual terms, and the part of the mean shift carried by each.
- **Honest label:** H5′ is chosen at S5 from dev, by the reviewer, after H5 was frozen. The file must say so.

## Other comments
1. **Sybil's vector `h` has few dimensions.** Per member, 213 to 233 of the 512 units are alive. The first principal component holds 35% to 44% of the variance. The effective number of dimensions is 5 to 7. The 56 family activations correlate with each other at a median |r| of 0.78 (64% of pairs at 0.70 or more) and with ℓ̄_1 at a median |r| of 0.90.
   - So matching raw units across members at r ≥ 0.70 is easy, and V3 is a weak mark for this arm. PCA, whose components cannot copy each other, finds only 3 families that replicate.
   - This also explains why the sparse autoencoder fails V1: a dense vector with one main axis cannot be rebuilt from 4 active features.
   - The report should say this plainly. It is a finding, not only a failed mark.
2. **H3 and H4: what the flag numbers mean.** About 12% of exams are flagged at τ90, so a change in 5% of exams is not small.
   - z-fix (924 exams): 112 flagged before, 105 after; 38 flags lost and 31 gained. Of the 143 exams flagged in either run, 48% are flagged in one run only.
   - Kernel (500 pairs): 64 and 61 flagged; 9 differ. Of the 67 flagged in either, 13% differ.
   - So the z-fix **reshuffles** the flags (both directions); it does not simply remove them. And "the kernel rarely changes the flag" is too strong: about one flagged exam in seven changes.
3. **The z-fix shows sensitivity, not harm.** On dev the fix does not raise the AUROC (0.995 to 0.985 at 1 year). Among non-cancers, stretched exams are flagged as often (10.6%, 906 exams) as exams without stretch (10.4% [9.1%, 11.7%], 4,079 exams). H1 to H3 confirm that Sybil's output depends on how slice spacing is handled. They do not show that the published handling makes Sybil worse. The word "error" needs this limit wherever it is used.
4. **H3 is the weak one.** My estimate of its chance is 0.63, close to the executor's 0.60. Its null (0.05) sits just under the dev lower bound (0.056). I accept it because it is disclosed, the test data are new, and H4 uses the same 5% line in the other direction.
5. **H1 to H3 population.** 8 dev exams have a recorded ratio of 0.0 and no z-fix row. The script leaves them out. The same rule will apply on test. No change needed; state it in the report.
6. **Budget.** The projection ($18.9; $20.8 with the reserve) against $22.30 is thin but inside the rules. If H5′ is taken, all five hypotheses need only the T5 rows and the T4 pairs. The full T1 to T3 extraction then serves the secondary references. The frozen fallbacks already cover a missing T3.
7. **None of the five is about cancer.** This is the honest result of the gate: U1a and U3 failed on dev, and "Sybil adds to the form" is doubtful on test after L1. I agree with not freezing them. The paper must say that the confirmed claims are about Sybil's behaviour.

## Changes I propose (a new freeze commit by the executor, after the lead's OK)
1. **H5 → H5′** as above. Or, if the lead prefers, move H5 to the secondary references and run a family of four.
2. **Wording.** H4: "the kernel changes the flag in fewer than 5% of exams" (not "rarely"). H3: add that flags change in both directions. Add to the frozen secondary list: flags lost, flags gained, and the share of discordant flags among exams flagged in either run, for z-fix and for kernel pairs. Add comment 3 to "what it does and does not show".
3. **Small bug in `wald()`.** If the bootstrap SD is 0 (for H4: no pair changes its flag in any draw), p becomes "none" and H4 counts as not confirmed, although the data support it fully. The chance is tiny (about 1 in 10,000 at the dev rate). Fix: p = 0 when the estimate is on the right side of the null and the SD is 0.
4. **Test manifest code.** `s1_manifest.py` works for dev only. The script that builds the test list does not exist yet. It defines which 500 pairs enter H4. Write it, commit it and add its hash before any test launch. Same pair rule, seed 0, same quota rule by maker, metadata only, no outcome.
5. **Three input hashes in `frozen_thresholds_L2.json`** (`l2_form_params.json`, `manifest_dev.csv`, `s4_families_dev_raw_K64.csv`) are hashes of the Windows working copy (CRLF). They differ from the table in `HYPOTHESES_L2.md` (committed bytes, LF). The script does not use them, so nothing is wrong today. On the new freeze, hash the LF bytes so both lists agree.
6. After the changes: run dev as if test again, update the hash table, and log the new freeze commit. A re-check of the diff by the reviewer is enough (hashes, dev run, the H5′ code).

## What the lead must decide
1. **H5:** (a) replace it by H5′ (my advice); (b) drop it from the family and report it as secondary (family of four); (c) keep it as frozen. With (c), I do not approve H5; H1 to H4 stay approved.
2. **OK for a new freeze commit** with changes 2 to 5, and for a short re-check of that commit before test data are extracted.
3. **Budget:** accept the thin margin for S6 on the main account in December, with the frozen fallbacks.
