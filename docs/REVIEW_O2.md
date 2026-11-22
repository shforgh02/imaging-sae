# Re-check of the O2 plan before the first launch

- **Date:** 2026-11-22. **Reviewer:** a fresh Claude session (Opus 5.5) that did not write the plan. Prompt: `docs/PROMPT_REVIEW_O2.md`, with the caller's changes (no commit, no push, no log entry: another session logs and commits this file).
- **Plan checked:** `docs/O2_PLAN.md`, frozen in commit `f39e1bb` (20 Nov). No file of the plan has changed since that commit.
- **Limits kept:** no cloud command; `ledger.json` only read; no `--add-u3`; my own code read no NLST table row of the never-used participants (only the committed public-metadata list, the IDC metadata file and Sybil's split file). The two allowed dry runs (`--dry-dev`) call `nlst_l0.build`, which loads the whole public NLST tables into memory, as the plan's own dry check did; they use only dev rows. No repository file was changed except this one. All outputs are in a scratch folder (list at the end).

## 1. Verdict: APPROVE WITH CHANGES

The plan is careful and the code does what the plan says. The hashes match. The dry runs give the same bytes as the committed files. The O2 statistics equal the frozen S6 statistics exactly (difference 0.0) on the same dev rows.

**One change is about science, not code:** O2-H7x does not test what its sentence says. It is meant to show the follow-up jump "outside GE scanners". But in half of its changed pairs (133 of 274) the stretched scan is a GE scan, and in 222 of 274 the scanner maker changes at the same time as the stretch. On dev and on test, the positive part of this group came from pairs that include a GE scan; pairs with no GE scan gave a negative b both times. A rejection of O2-H7x as written could therefore be read as "outside GE" when it is mostly GE. Change: test H7x on pairs where **neither** scan is GE (74 changed pairs, balanced 37 / 37).

The other changes are cheap safety rules (order of steps, fallbacks, guards in the code, text fixes). Together they need one amendment commit, a new dry run and a log line, all before 1 December and before any O2 scan is scored. Cost: $0.

## 2. Words used here

| Word | Meaning |
|---|---|
| stretched | the job's DICOM ratio (slice spacing / slice thickness) is above 0 and at most 0.65 |
| pair | two consecutive yearly screens of one person, both scored |
| changed pair | one scan of the pair is stretched, the other is not |
| one-GE pair | one scan on a GE scanner, the other on Philips or Siemens |
| neither-GE pair | both scans on Philips or Siemens |
| b | the follow-up jump: how much Sybil's 1-year logit moves when the stretch status changes, after the radiologist's findings (F1) |
| U1, U2, U3 | the O2 lists: stretched candidates; their year partners; the form sample (added later, the only list step that reads an outcome) |

## 3. Findings, most serious first

| # | Level | Where | What I found (evidence) | Change |
|---|---|---|---|---|
| R1 | **Serious (science)** | `docs/O2_PLAN.md:39`, `:53`; `o2_analysis.py:144`, `:146` | O2-H7x uses pairs "not both GE". From the committed list (public metadata, IDC ratio as stand-in for the DICOM ratio): 274 changed pairs = 200 one-GE + 74 neither-GE. In the 200 one-GE pairs the stretched scan is GE in 133 (GE → Siemens) and Philips in 67 (Philips → GE); 194 go stretched → not, only 6 the other way. Maker changes with the stretch in 222 of 274. Dev dry run: one-GE b +0.246 [+0.064, +0.396] (44 changed: 41 / 3), neither-GE −0.179 [−0.544, +0.134] (20 changed). Test (`RESULTS_L2.md:89`): one-GE +0.214 (33 changed), neither-GE −0.318 (13 changed). So a rejection would mostly reflect GE stretched scans and scanner changes, not "the jump outside GE". | **Default:** O2-H7x = the same b on neither-GE pairs (`nge == 0`), null 0, one-sided. Wording: rejected → "the follow-up jump is also seen in pairs scanned only on Philips or Siemens scanners"; not rejected → "on pairs without a GE scanner we cannot show the jump (b and its interval)". Keep "never 'GE only' unless the interval excludes small positive values". Move the present "not both GE" b to the secondary list, and add the one-GE b split by the maker of the stretched scan. **Alternative** (if the lead wants the larger group): keep the population, rename it "pairs that include a non-GE scan", and change the wording so it never says "outside GE". |
| R2 | Moderate (order) | `O2_PLAN.md:16`, `:24`, `:46` | `o2_manifest.py --add-u3` reads `candx_days` of the never-used participants. Nothing in the plan says it must wait until the O2a + O2b output is committed. The analysis is scripted, so the risk is about appearance, but it is free to remove. | Add: "`o2_analysis.py` is run on U1 + U2 and its output committed before `o2_manifest.py --add-u3` is run." |
| R3 | Moderate (outcome-free claim) | `nlst_l0.py:105`; `o2_analysis.py:61-64`, `:135-136`; `O2_PLAN.md:28` | `nlst_l0.build` removes exams taken after a lung cancer diagnosis (`ex = ex[~(ex.dt < 0)]`). O2 takes F1 from that table and drops pairs without F1, and writes the count `F1_missing`. So which pairs enter H7 depends, very slightly, on an outcome. Expected effect: tiny (34 never-used participants have a lung cancer; dev dry run: `F1_missing` 0). I did not count it, because that needs the outcome rows of these participants. No outcome column is used or written. | Say it in section 3 of the plan; label `F1_missing` "includes exams after a lung cancer diagnosis and inadequate screens; not an outcome-free number". Do not edit `nlst_l0.py` (frozen). |
| R4 | Moderate (run rules) | `O2_PLAN.md:20-25`; `LUNG_L2_PROTOCOL.md:250`; `HYPOTHESES_L2.md:120`, `:125-126`; `drive_runs.py:184`; `drive_plan.py:19`; `l2_sybil_modal.py:258` | (a) The protocol allows at most 4 containers at once across all accounts; the plan has three accounts and does not say "one after another" (S6 did, in `run_s6.cmd`). (b) "Rows 0 to 2,148" is inclusive, but the job's `--lo/--hi` is half-open; `drive_runs.py` defaults to 3 launches, `drive_plan.py` to 4; S6 used 6. (c) S6 had a cross-account identity check; O2 has none, although every smoke scores U1 rows 0 to 2 on its own account. `o2_analysis.load_files` keeps the first copy it finds (line 45). (d) No fallbacks (S6 had them): what if part of U1, or all of U2, is not scored? (e) The stop rules "G2b/G2c failure" and "an outcome column in the input" are not enforced: `o2_analysis.py:85` computes and writes the whole family even if G2 fails. | (a) Accounts one after another, with `wait_idle.py` between them. (b) A committed launch file, like `run_s6.cmd`, with `U1:0:2149` (armanfo), `U1:2149:4298` (forghanishayan), `U2:0:811` (shforghani2002), `--root unseen --zfix-max 0.65 --max-launches 6`. (c) Before the analysis, U1 rows 0 to 2 must agree across the three accounts (S6 identity rule), else stop; fix the `--copies` order. (d) Part of U1 missing: O2a on the scored rows (a random set of participants by design), with the count. U2 missing, or fewer than 30 changed pairs: O2-H7 and O2-H7x not evaluated, count as not rejected, family size stays 6. (e) `o2_analysis.py` refuses (SystemExit) before the family if G2 fails or an outcome column is present. |
| R5 | Moderate (U3 safety) | `o2_manifest.py:86-94`, `:82`; `o2_form.py:39`, `:53-54`; `O2_PLAN.md:16` | (a) "U1 and U2 rows must stay byte-identical when U3 is added": true with the present code (my simulation, below), but nothing checks it. (b) `o2_form.py` checks the rebuilt random sample against `o2_manifest.json`, but `--add-u3` rewrites that file from the same draw, so the check is circular. The plan gives only the prefix `dbb8ee46…`. | (a) `--add-u3` refuses unless the first 5,110 lines equal the frozen list (SHA-256 `fb625265…`). (b) `o2_form.py` compares with the full frozen hash `dbb8ee4651ae032af900b77ec0d966b02ceb5ae5e3057b10e4c1947d22a44e34`, which is also written into the plan. |
| R6 | Minor (text) | `O2_PLAN.md:57`, `:52`, `:66-75` | (a) "H2 −0.324 (−0.326 with ratio 0)" is mislabelled: the 8 dev z-fix exams that the dry run leaves out have a **blank IDC ratio** (their DICOM ratio is 0.5 for 7 and 0.2 for 1). Dev T5 has no ratio-0 exam, because the job makes no z-fix when the spacing is 0 (`l2_sybil_modal.py:234`). So the "ratio > 0" rule changes H7 only. (b) The wording rule treats H1 to H6 as one block. H3 failed on test (4.5%), so if O2-H3 is rejected, "replicates" is wrong for H3; and if only some are rejected, each needs its own sentence. (c) `r10_att_harm.py`, `s2_pilot_checks.py` and `s7_added_value.py` are imported by O2 but not in the hash table (they have not changed since the freeze). | (a) "−0.326 on all 924 dev z-fix exams; the 8 left out by the IDC-based list have a blank IDC ratio". (b) One sentence per hypothesis; for H3: "on these people the flag changed in x% of stretched exams (test 4.5%)". (c) Add the three files to the table. |
| N1 | Note | `reconcile_billing.py:22`, `:45` | It reconciles only `lung_l2_audit` runs, so O2 runs (task `o2_unseen`) stay at measured cost in the ledger. This matters for the U3 decision ("only if the task budget left covers the guard's worst case"). | Extend it to `o2_unseen`, or check billing by hand before U3. |
| N2 | Note | `o2_analysis.py:93` | GE is found by the substring "GE". This is correct for the makers present (GE MEDICAL SYSTEMS, Philips, SIEMENS; one TOSHIBA on dev). | Exact match is safer (optional). |
| N3 | Note | `s6_frozen_analysis.py:110` | In a bootstrap draw with no pair of one direction, the OLS has no unique answer and `lstsq` returns a minimum-norm b, not None. This affects only small secondary groups (e.g. one-GE pairs: 6 pairs go not → stretched, so about 0.25% of draws). | None for the family; mention it with the small groups. |
| N4 | Note (no action) | `drive_runs.py:69`; `l2_sybil_modal.py:332-334` | The copy pulls the whole `l2` folder with `--force`, including `run_info/heads.npz`, which every smoke rewrites. The file is byte-stable: the copies from three separate smokes all have the frozen hash (`ba2d6d85…`). If it ever changed, `load_frozen` would refuse (safe failure). | None. |
| N5 | Note (no action) | PC | No old December task is scheduled (`imgsae_l2_dec` absent; `run_dec.cmd` is superseded and fails on purpose). Nothing starts by itself on 1 December. | None. |

## 4. Answers to the questions

### Q1. Do the hashes of section 8 match the files?
**Yes, 6 of 6.**
- What I did: SHA-256 of the committed blob (`git cat-file blob HEAD:<path>`, and at `f39e1bb`), as section 8 says ("committed content, LF line ends").
- What happened: all six equal, at HEAD and at the freeze commit. No blob contains a CRLF. The working-tree files give the same values.
- Frozen NLST files (last row of section 8): all 36 files in the hash table of `HYPOTHESES_L2.md` match their committed content. `load_frozen` passed in my dry run, so `results/s5/`, `heads.npz` and the calibrator match too.
- No module that O2 imports has changed since the freeze (`git log f39e1bb..HEAD` is empty for them).
- Also: the gzip copy of the list decompresses to exactly the committed CSV bytes.

### Q2. Does `o2_analysis.py` compute O2-H1, H2, H3, H6 and H7 exactly as the frozen definitions, apart from the stated changes? Any bug?
**Yes. No bug in the family statistics.**
- What I did: I re-ran the dry run (byte-identical to the committed JSON). Then I recomputed the six statistics a second way: the S6 code path (assembled dev tables, `s6_frozen_analysis` functions), on the same 916 exams and 701 pairs.
- What happened: H1 0.66921, H2 −0.32421, H3 0.07533, H6 0.40753, H7 0.20540, H7x 0.06710 in both ways. Difference 0.0 for all six.
- The stated changes are the only ones: ratio > 0 (it matters only for H7, see R6a); pairs only within U1 and U2; H7x with null 0. One more filter, not stated: a pair needs F1 on both scans (dev: 0 missing; see R3).
- Bootstrap, Wald p from the bootstrap SD, and Holm are the frozen functions (`boot_stat`, `wald`, `holm`), with the frozen nulls and directions.
- Small points: N2, N3.

### Q3. Is `o2_analysis.py` really outcome-free? Is U3 kept out of O2a/O2b?
**No outcome column is used or written. U3 is kept out. Two caveats.**
- Columns: every outcome column in the NLST exam table (`candx_days`, `canc_free_days`, `dt`, `fu`, `y1`, `y2`, `y6`) is in the drop list (`o2_analysis.py:37`) and dropped before use (`:62`). Only F1 is used (findings, age, sex, smoking), plus the nodule slice for attention.
- Caveat 1: `nlst_l0.build` reads the outcome columns into memory before they are dropped (allowed by the plan's wording).
- Caveat 2: the row filter on exams after a diagnosis (R3).
- U3: `manifest_rows` keeps only U1 and U2 (`:54`), and the file lists are filtered to those rows (`:76`). U3 files on the same volume are ignored. Only the order of steps is not fixed (R2).

### Q4. Is the random sample fixed before any outcome is read, and does `o2_form.py` rebuild and check it?
**Yes for both, with one weak point.**
- The sample is drawn in `o2_manifest.py:70` from the metadata selection only (IDC metadata and Sybil's split file; no NLST table). Its hash is in `o2_manifest.json` in the freeze commit, before U3 exists.
- I rebuilt the list from metadata (without `--add-u3`) into scratch. The CSV, the gzip copy and `o2_manifest.json` are byte-identical to the committed files. The sample hash `dbb8ee46…` is reproduced.
- `o2_form.py:50-54` rebuilds the draw and refuses if its hash differs. The metadata path is hard-coded (`:53`); it is the file I used, and it matches.
- Weak point: the check compares with a file that `--add-u3` rewrites (R5b).

### Q5. Are the cloud changes limited to reading the new list and booking the task? Could they change how dev, test or LIDC were scored?
**Yes, limited. No, they cannot change dev, test or LIDC.**
- The diff in `f39e1bb` does three things. (1) It adds `manifest_unseen.csv.gz` to the image and to the gzip check. (2) It maps root `unseen` to that file, with tier prefix U. (3) It books root `unseen` to task `o2_unseen`, in the job and in the driver (and so in `drive_plan.py`, which uses the driver).
- No scoring line changed: `_prepare`, `_volume`, `_forward`, `_save`, `_rows` and `_done` are untouched. For roots dev, test and LIDC, the task and list are the same as before.
- Side effect: every launch, for any root, now also checks the new gzip file (and refuses if it is missing). This is a safe failure.
- The dev, test and LIDC runs are finished, and their files are not touched by code. The frozen hashes still match (Q1).

### Q6. Is the H7 design with only U1 and U2 scored sound? Is the null 0 for O2-H7x reasonable?
**H7: yes. Null 0: yes. The H7x group: no (R1).**
- H7 design: the unchanged pairs are almost all "both stretched" (by IDC metadata, 1 pair is "both not stretched"). So b compares the two directions of change with the year-to-year drift of stretched pairs.
- On dev, this design gives +0.205. All dev pairs (ratio > 0) give +0.227, and changed pairs only give +0.216. The shift is small (about −0.02), so the frozen null +0.10 still fits.
- Power: O2 has about 823 changed pairs (dev with this design 202; test 134). The bootstrap SD should be about half of dev's 0.055 (roughly 0.03). If b is near +0.2, H7 has good power.
- Note: in the dev dry run H7 was not rejected (p 0.030 against Holm's 0.025), with 4 times fewer changed pairs.
- Scanner changes remain the main doubt. 601 of the 823 changed pairs keep the maker, and 239 keep the scanner model. The same-model secondary now has real power (Q8, A2).
- Null 0 for H7x: reasonable as a "is there any jump" test, because the interval is wide (about ±0.12 for the present group; ±0.18 to ±0.23 for neither-GE pairs). A rejection then means "a positive jump", not "as large as on GE". The wording already says so.
- Holm: H7x is the weakest test. When it fails, H7 is tested at α/2, as on test. This costs H7 little at O2's size.

### Q7. Anything that should change before the first launch?
**Yes: R1 to R6, in one amendment commit before 1 December** (plan text, `o2_analysis.py`, `o2_manifest.py`, `o2_form.py`, a launch file). Then re-run both dry runs, write the new hash table, add a log line. N1 is advised, not required. All of it is free and touches no frozen file.

### Q8. Additions that clearly raise the value without risk to the frozen tests
All are outcome-free, cost $0, and stay **outside** the Holm family (pre-stated secondaries; never "confirmed").

| # | Addition | Why it is worth it | What the December data allow that test could not |
|---|---|---|---|
| A1 | **The z-fix change by maker, with intervals:** mean Δℓ̄_1, H6 and the ¼-SD share for GE, Philips and Siemens, each with a participant-bootstrap interval. Today `by_maker` gives only point means (`o2_analysis.py:126-127`). | LIDC suggested the drop is mostly GE (Philips −0.01, Siemens +0.18, on 46 and 17 scans). NLST dev says it is not (Philips −0.28). O2 can settle this. | About 1,699 Philips and 384 Siemens stretched exams (LIDC: 46 and 17). |
| A2 | **H7 on the same scanner model as a key secondary**, with a fixed sentence: "on pairs with the same scanner model, b = x [interval]". The code already computes it (`:153-154`); only the label and the wording are new. | It is the main check against "the jump is a scanner change". | About 239 changed pairs on the same model (GE 190, Philips 26, Siemens 23); dev had 52. |
| A3 | **b when stretched exams use their z-fix score** (main score for not-stretched exams). Reported as an estimate, two-sided, no claim direction. | It asks the practical question: does using the true spacing make Sybil's yearly scores consistent? It completes "b with axis 0 off". | Every stretched O2 exam has a z-fix run; 823 changed pairs. |
| A4 | (Part of R1.) The present "not both GE" b, and the one-GE b split by the maker of the stretched scan, as secondaries with counts. | It keeps the information without the misleading label. | 200 one-GE changed pairs. |

**Additions I would NOT make, and why:**

| Not add | Why |
|---|---|
| Any new member of the Holm family (for example a Philips H2, A2 or A3 as hypotheses) | Every extra test lowers every Holm level. These ideas are chosen now, after dev and test were seen. Keep them secondary. |
| Changing H3's null or dropping H3 | H3 failed on test. Moving its margin now would look like moving the goalpost. Keep the frozen retest. |
| Scoring the "both not stretched" pairs (full H7 design) | Thousands of extra exams (many dollars) to move b by about 0.02. |
| Adding the 876 exams with a blank IDC ratio | About +$2.6 for about 2% more stretched exams, while U3's budget is already tight. |
| The outcome-based H7 check "pairs without cancer" (as in S6) | It would read outcomes of about 2,000 never-used participants. With only 34 cancers in this group, the number would hardly move. |
| A stretch-size (dose) test in follow-up | 740 of 823 changed pairs are 2.0× stretches; only 77 are 1.6×. Too little spread. |
| Missed-cancer harm, or more O2c controls | About 29 one-year cancers. The cases limit the precision; more controls barely help. |
| Phantom or synthetic-stretch work inside O2 | That is task 2 (dev scans and phantoms). Keep O2 a clean replication. |
| Local CPU scoring, or a tuned form | The lead chose the cloud and "no tuned form". |

## 5. What I could not check
- Anything on the cloud: the smoke, the image build in December (pandas, scipy and idc-index are not pinned in the image; the smoke's demo check guards the scores), real run time and real cost.
- How many exams of the never-used participants come after a lung cancer diagnosis (R3). It needs their outcome rows.
- How well the IDC ratio agrees with the job's DICOM ratio for these participants. All my pair counts use the IDC ratio as a stand-in; the job's own geometry decides in the real run. On test, 745 stretched exams by IDC against 759 by DICOM.
- The numbers 34 participants with cancer and 29 one-year cancer exams (they need outcomes).
- `o2_form.py` outside the dry run (it needs U3). I checked its random-sample rebuild separately.
- `budget.py` arithmetic. I only saw that `ledger.json` holds the task `o2_unseen` ($24).
- I did not re-derive the cost estimates.

## 6. Outputs (scratch only; nothing in `results\`)
| File | What |
|---|---|
| `C:\Users\Arman\AppData\Local\Temp\claude\5cb39bed92095523\007a94e4-7e60-4ff8-8534-45da7cf489ad\scratchpad\o2_review_dry\o2_analysis_dry_dev.json` | dry run (156 s); byte-identical to `results/o2/o2_analysis_dry_dev.json` |
| `C:\Users\Arman\AppData\Local\Temp\claude\5cb39bed92095523\007a94e4-7e60-4ff8-8534-45da7cf489ad\scratchpad\o2_review_dry\o2_form_dry_dev.json` | dry run (150 s); byte-identical to `results/o2/o2_form_dry_dev.json` |
| `C:\Users\Arman\AppData\Local\Temp\claude\5cb39bed92095523\007a94e4-7e60-4ff8-8534-45da7cf489ad\scratchpad\o2_review_dry\manifest_rebuild\` | U1 + U2 list rebuilt from metadata; CSV, gzip and JSON byte-identical |
| `C:\Users\Arman\AppData\Local\Temp\claude\5cb39bed92095523\007a94e4-7e60-4ff8-8534-45da7cf489ad\scratchpad\o2_review_dry\u3_sim\sim_with_u3.csv` | U3 simulated with the 648 random-sample rows only (17 with a blank IDC ratio): the first 5,110 lines stay identical |
| `C:\Users\Arman\AppData\Local\Temp\claude\5cb39bed92095523\007a94e4-7e60-4ff8-8534-45da7cf489ad\scratchpad\o2_review_scripts\indep_check_dev.py` | S6-path recomputation of the six statistics on the dry-run rows |
| `C:\Users\Arman\AppData\Local\Temp\claude\5cb39bed92095523\007a94e4-7e60-4ff8-8534-45da7cf489ad\scratchpad\o2_review_scripts\u3_bytes_sim.py` | U3 byte check |

Repository file written: `D:\Shayan\docs\REVIEW_O2.md` (this file) only.
