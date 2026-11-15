# Review of `docs/PLAN_L2_NEXT_v1.md`

- **Reviewer:** Fable 5.2. **Date:** 2026-11-15.
- **Verdict: APPROVE WITH EDITS.**
- **What I read:** the plan, the protocol, the progress report, `STATUS.md`, the execution log from 2026-11-13, the reviewer brief, and the code named in the review prompt (`budget.py`, `launch.py`, `collect.py`, `drive_runs.py`, `drive_plan.py`, `reconcile_billing.py`, `l2_sybil_modal.py`, `l2_data.py`, `l2_form.py`, the `s4_*.py` files).
- **What I did not do:** no Modal or cloud command that runs anything, no change to `ledger.json`, no test data, no analysis on dev data, no code change. I ran one help text (`modal app list --help`) to check that an option exists.
- **A limit of this review:** it ran in the same chat in which the plan was drafted, because the chat was not cleared first. So it is less independent than a review in a fresh session. To make up for that, I checked every point against the files, not against the chat.

## Summary for the lead
- **The plan is sound.** Its order, gates and stop points are right. The test split stays protected.
- **I made 15 edits.**
  - The two that matter most for money and safety: a spending limit for this project on `armanfo`, and keeping the cloud volumes instead of deleting them.
  - The two that matter most for the science: a cleaner "form + image measures" baseline, and the direct test "does Sybil add to it".
- **Three questions need your answer** (the last section). Each has a default, so the work is not blocked.

## 1. Facts: does the plan agree with the protocol and the files?
**Checked and correct:**
- Dev counts: D1 2,484, D2 2,442, D3 2,410, D4 500, z-fix expected 908 (`results/s1_manifest.json`).
- Dev cancers: 88 one-year, of which 38 at baseline; 137 six-year at baseline (`results/s0_dev_counts.json`).
- F: F1 fitted on 29,752 train screens with 452 cancers, F6 on 9,009 with 707 (`results/l2_form_info.json`).
- Money: task $7.67, project $33.06, November $28.17 on the main account (`budget.py status` output in the log; the ledger runs 031 to 037).
- Arithmetic of the money table: S3 total 5.72 + 0.40 + 14.50 = $20.62 of $22.00; task after P3 $22.57.
- The list of S4 scripts that exist and that are missing.

**Errors and gaps found (all fixed in the plan, or listed for the executor):**

| # | Finding | Where fixed |
|---|---|---|
| F1 | The smoke step writes 3 D1 series into root `dev` on the volume (`smoke()` calls `_rows("D1", 0, 3)` with root `dev`). On `armanfo` these files would collide with the saved D1 files. The plan's merge "refuses any overwrite", so it would have stopped on them. | P2 item 3, P3 item 3 |
| F2 | Three places in the driver are not account-aware: `precheck` (single `cap_usd`), `lag_extra` (all accounts), and the fixed copy destination with `--force`. The plan's P1 list did not name them. | P1 item 4 |
| F3 | `budget.py status` writes into `ledger.json` on every call. Proof: the working tree has an uncommitted 6-line change in `ledger.json` from a read-only status call on 15 Nov. A chat session and a running driver could write the file at the same time. | P1 item 4 (atomic save, no-log mode) |
| F4 | Protocol section 9.1 asks for check P1 (Spearman of ℓ̄ and s ≥ 0.98) and for the share of hazard units that are on. No S4 script does this, and the plan's list missed it. | P4 item 3 (`s4_scores.py`) |
| F5 | The P6 money (≈ $15.50 to $18.40) uses the protocol's $0.0023 per series. The billed S3 rate was $0.0025 to $0.0028. With T4 and T5 the test step can reach about $22, against about $22.40 left in the task. | P5 item 4, money table |
| F6 | The protocol's first lines still say "DRAFT, waiting for the lead's OK", but the lead approved it on 2026-11-13 (log). | For the executor: correct the status line when A3 to A5 are entered in section 16a |
| F7 | Dev participants: 2,493 in the protocol (split file), 2,492 in the manifest. Not an error: one participant has no usable exam. | For the executor: state both numbers in the S4 results |
| F8 | The uncommitted change in `ledger.json` (see F3) is still in the working tree. I did not commit it. | For the executor: commit it with the P1 ledger change |

## 2. The amendments
### A3 (two simple references): APPROVE WITH EDITS
- **R-size:** approved as written. It is correctly marked "partly seen" (L0 computed it on test), so it can never be a hypothesis.
- **F+I:** approved with three edits.
  1. **Measures.** The primary model uses the 5 patient measures (lung volume, emphysema %, lung p15, lung mean HU, body area).
     - Air noise and lung z-extent are technique-dependent (dose, kernel, the crop of a stretched scan).
     - The plan itself says technical factors must stay out of the outcome model. With all 7 measures it would break its own rule.
     - The 7-measure model and a "lung not cut" subset are sensitivity runs.
  2. **The missing test.** Two AUROCs side by side (Sybil, F+I) do not answer the question the baseline was added for. I added the direct test: does `logit(s_t)` add to the F+I logit (ΔAUROC with interval, likelihood-ratio test)? This is the same form as the protocol's Q1b test.
  3. **A stated limit.** Emphysema % is scanner-dependent (Toshiba offset). F+I is also reported by maker.
- **Fair to Sybil?** Yes.
  - F+I is cross-validated on dev by participant, and Sybil is not refitted.
  - On dev, Sybil has a small advantage (dev was used for its model selection, protocol C6).
  - On test, both are frozen.
- **Leakage?** None found.
  - F is fitted on train only and hashed.
  - The dev fit of F+I has about 7 coefficients and is cross-fitted.
  - The test version is one frozen dev fit.
- **Timing.** The amendment is made before any dev outcome analysis. Git shows no S4 result file. So it is a clean pre-specification.

### A4 (second Modal account): APPROVE WITH EDITS
- **Can it overspend?**
  - Not past the account cap, if P1 is done as written and the three driver places of F2 are fixed.
  - But the cap alone would let this project use all of the lead's remaining `armanfo` credit. I added a **project limit on `armanfo` of $17.00** as a fourth guard test (expected use about $14.90).
- **Can it use the wrong account?**
  - The design is right: profile per command, stored per run, never `modal profile activate`.
  - Two additions: the driver refuses to start if its environment's profile differs from `--profile`, and the `.cmd` wrapper sets the profile itself.
  - Note for the executor: the CLI also has a `--profile` option on each command. Use it where it exists; it is more direct than the environment variable.
- **Can it touch the lead's other work?**
  - No command in the plan touches another app or volume.
  - The app check was too strict: "no running app" would block for ever if the lead keeps an idle deployed app. I changed it to "no other app with running containers".
- **Is the identity gate enough?**
  - Yes: 20 series + the 3 smoke series + the demo case + the checkpoint and head-weight hashes.
  - Earlier checks gave 0.0 between runs and 7e-7 between GPU types, so a pass mark of 1e-4 is safe and still strict.

### A5 (unattended driver as executor): APPROVE
- It worked for D1, and it removes the usage-limit failure.
- It still goes through the guard on every launch, and it has clear stop rules.
- The ledger-safety edit (F3) belongs with it.

## 3. Science
- **Will this give the strongest honest paper?** Yes, within the data.
  - The plan keeps the three possible outcomes open and does not bet on the sparse autoencoder.
  - The most robust candidates are the outcome-free ones (z-stretch, kernel pairs). The feature-level results are the higher-impact and higher-risk part.
- **Gates and stop points:** right. Gate 9.8 before any test spending is the key one, and it is kept.
- **Order:** one change. The missing S4 scripts should be written and tested while P1 to P3 run, and **committed before the first full-dev outcome run**. This saves days. It also fixes the dev analysis by a commit, which the external reviewer can check.
- **Wasteful steps:** none found. The z-fix and pair data cost little and carry the most certain results.
- **Missing:** check P1 and the gating shares (F4); the "adds to F+I" test (A3).
- **The S4 scripts still to be written:** their one-line definitions in the plan agree with protocol section 9.7. The executor must take the exact numbers from 9.7, not from the plan's short text:
  - U1a qualification: ΔAUROC ≥ −0.01, spread ratio ≤ 0.80.
  - U1b: |Δ| ≥ 0.25 SD in ≥ 30%, or flag change ≥ 10%.
  - U3: C ≤ 0.80 × the better of Sybil and F.
  - U2: 80th and 90th percentiles, top 20%.
  - Q2: no claim under 10 cancers.
- **One caution for the write-up:** with 7,336 exams and 512 inputs, the simple arms (PCA, raw units) may do as well as the sparse autoencoder. The protocol already says this must be reported as it is. The plan keeps that rule.

## 4. Honesty rules
- **Is the test split protected until the S5 approval?** Yes, and also by the code. The cloud image holds only `manifest_dev.csv`, so the job cannot score a test series today. I made this an explicit rule: the test manifest is built only after the OK is logged.
- **Can test information leak into choices?**
  - One real path exists: the L1 test scores are on the PC (`lung_l1/results/scores.csv`). I added the rule that no S4 script reads that file or any test file, and that `s4_gate.py` checks it.
  - The L1 post hoc numbers (15% to 19%, r = 0.61) are known to everyone. Protocol rule C10 already bars them from being "confirmed".
- **The pilot** is real dev data. Tests on it are code tests only. The plan now says so.
- **The "partly seen" rule** is kept (at most one such hypothesis, labelled).

## 5. Risks not covered in the plan's section 9 (now added there)
1. The laptop would hold the only copy of the data after a volume deletion. → Volumes kept.
2. Two programs writing `ledger.json` at once. → Atomic save and a no-log mode.
3. This project using up the lead's `armanfo` credit. → $17.00 limit.
4. Test money running short. → Order and projection fixed at S5.
5. A measure column silently empty (`E.get(...)` in `l2_data.py`). → Non-missing shares in the assemble report.

## List of edits made to the plan (all marked `[Fable edit]`)
| # | Section | Edit |
|---|---|---|
| E1 | Status line | Reviewed, verdict |
| E2 | A3 | F+I uses 5 patient measures; 7-measure and "lung not cut" sensitivity runs |
| E3 | A3 | Test "does Sybil add to F+I"; coefficient count corrected to about 7 |
| E4 | A3 | Scanner limit of emphysema %; F+I by maker |
| E5 | A4 | App check on running containers, not on app state |
| E6 | A4 | $17.00 project limit on `armanfo` |
| E7 | P1 | Three account-blind places in the driver; profile refusal; `.cmd` sets the profile |
| E8 | P1 | Ledger safety (atomic save, no-log status); optional keep-awake |
| E9 | P2 | Identity command shape; the 3 smoke series as a second identity check |
| E10 | P3 | Merge: new files must be D2 to D4; existing files compared and skipped; a different file stops it |
| E11 | P3 | No volume deletion in P3 |
| E12 | P4 | Scripts written during P1 to P3 and committed before the first full-dev run; pilot numbers not used; no S4 script reads test files; non-missing shares |
| E13 | P4 | `s4_scores.py` (check P1, gating shares, dev AUROCs with the C6 note) |
| E14 | P5, money | S6 order and billed-rate projection fixed at S5; the optimistic P6 column explained |
| E15 | P6 | Test manifest only after the OK; smoke on the test path; `--zfix-max 0` if z-fix is not in a hypothesis |

## Open questions for the lead (each has a default, so nothing is blocked)
1. **How much of `armanfo`'s November credit may this project use?** Default: **$17.00** (expected about $14.90). The rest, about $11, stays for your other work there.
2. **Keep the two cloud volumes until the results are final?** Default: **yes**. If you have an external drive, a second copy there would be even safer; tell the executor the path.
3. **F+I with the 5 patient measures as the primary model** (edit E2)? Default: **yes**.

Not blocking, for later: when to tell Sybil's developers about the z-stretch. The plan suggests at submission or after the paper.
