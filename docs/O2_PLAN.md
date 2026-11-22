# O2: the slice-spacing tests on NLST participants Sybil never used (December 2026)

**Status:** FROZEN on 2026-11-20, before any O2 scan is scored and before any outcome of these participants is read. The freeze is the commit that adds this file. **Amendment A1 (22 Nov 2026, also before any O2 scan is scored or any outcome of these participants is read): section 9; where section 9 and the sections above differ, section 9 holds.** Lead's go: "do all" (20 Nov; budget $24, task `o2_unseen`). Plan choice: `docs/REVIEW_PLAN_CHOICE.md` (O2a + O2b), with the six changes of my reaction (log, 20 Nov), and the lead's wish to do the form again on these people (O2c, small and descriptive).

## 0. In simple words
- **Who:** 11,226 NLST participants with CT in the public archive whom Sybil's makers never used (no train, dev or test). Sybil has never seen them.
- **What:** the same frozen tests as on the test split, on many more stretched scans (4,298 candidates, 2,095 people), and the real-follow-up test with enough pairs **outside GE** scanners for the first time.
- **What it cannot do:** test accuracy well. Sybil's makers took almost every cancer, so only 34 of these people had a lung cancer (29 one-year cancer exams). The form check (O2c) is therefore small and only descriptive.
- **Cost:** about $20 to $23 as measured, December credits. **When:** from 1 December (the November credits are almost used up).

## 1. Lists (`imgsae/exploratory/lung_l2/o2_manifest.py`)
- **Selection** (as `x6_unseen_metadata.py`): CT-arm participants in IDC that are in none of Sybil's splits; the dev series rule (`series_rule.BEST_RULE`), one series per participant and screen year, years 0 to 2; a year with two chosen series is dropped. 28,661 exams.
- **U1, stretched candidates (public metadata only):** IDC ratio (slice spacing / thickness) ≤ 0.70: **4,298 exams, 2,095 participants** (GE 2,215, Philips 1,699, Siemens 384), 492.5 GB. The job's own DICOM geometry decides the z-fix (ratio ≤ 0.65, as frozen). Fixed random order of the participants (seed 0).
- **U2, partners (public metadata only):** the exams that are not in U1 and are the year neighbour of a U1 exam (the other scan of a pair that changes stretch status): **811 exams**, 84.6 GB. 2,964 consecutive pairs will have both scans scored.
- **Not included:** 876 exams with a blank IDC ratio (3%; scoring them would cost about $2.6). In the test split, the IDC metadata missed 14 of 759 stretched exams (2%), so O2 misses about 2% of the stretched exams. This depends on metadata only, never on an outcome.
- **U3, the form sample (O2c), added only after this freeze** with `o2_manifest.py --add-u3 <tables>`: every exam (years 0 to 2) of a never-used participant with a lung cancer diagnosis (NLST `candx_days`; the only outcome read for the lists), plus a random sample of **800 exams** (seed 1; drawn now, from the whole selection, before any outcome is read; SHA-256 of its sorted UIDs `dbb8ee46…`; 152 of them are already in U1 or U2). The U1 and U2 rows must stay byte-identical when U3 is added.

## 2. Scoring
- The frozen cloud job `cloud/l2_sybil_modal.py` as used for the test and LIDC runs. **Only changes (logged):** root `unseen` reads `results/manifest_unseen.csv.gz` (tiers U*), and its runs are booked to task `o2_unseen`; the same two lines in `cloud/drive_runs.py`. Main run (Sybil as published) for every row; z-fix run when the DICOM ratio is ≤ 0.65 (`--zfix-max 0.65`); smoke with Sybil's own volume check on.
- **Order and accounts** (each launch through the guard `budget.py`, `MODAL_PROFILE` set per command, the unattended driver `drive_runs.py`):
  1. Smoke on each account: `--step smoke --n-series 3 --tier U1 --root unseen --zfix-max 0.65` (demo case equal to the published scores; U1 rows 0 to 2 with the volume check).
  2. `armanfo`: U1 rows 0 to 2,148; `forghanishayan`: U1 rows 2,149 to 4,297 (about $8 to $9 each).
  3. `shforghani2002`: U2 (811 rows, about $2 to $3).
  4. U3 (about $2 to $2.5), only if the task budget left covers the guard's worst case. If not: stop and ask the lead (about +$2).
- **Stop rules** (as S6): guard refusal; a failed call; errors above 5% of the rows of a launch; G2b/G2c failure on the PC copy; any outcome column found in the O2a/O2b input. Each account's volume folder is copied to its own PC folder (`imgsae_data/lung_l2_vol*`).

## 3. O2a + O2b analysis (`o2_analysis.py`; outcome-free)
- **Input:** the job's files of tiers U1 and U2 (from the PC copies of all accounts); the frozen files `results/s5/` (hash-checked); the NLST tables for the radiologists' findings and age, sex and smoking (the frozen form F1, for H7) and the nodule slice (attention). Every outcome column is dropped from the NLST table before use and is never written. U3 is never used here (it was selected with outcomes).
- **Stretched** = the job's DICOM ratio, **0 < ratio ≤ 0.65** (the "ratio > 0" rule; on the test split ratio 0 was counted as stretched in H7).
- **The O2 family (Holm over six, one-sided, α = 0.05; participant bootstrap 2,000, seed 0; Wald p from the bootstrap SD, as frozen):**

| ID | Statistic (frozen definition) | Population | Null |
|---|---|---|---|
| O2-H1 | share of exams with \|Δℓ̄_6\| ≥ 0.25 × 0.92957 (the dev SD) | stretched exams with a z-fix file | > 0.30 |
| O2-H2 | mean Δℓ̄_1 (z-fix minus main) | same | < −0.10 |
| O2-H3 | share of exams whose τ90 flag changes (H3; failed on test at 4.5%: retested with its frozen null) | same | > 0.05 |
| O2-H6 | mean of [Δℓ̄_1 with shared axis 0 set to its dev mean] − [Δℓ̄_1 as is] (frozen axes) | same | > +0.20 |
| O2-H7 | b in Δℓ̄_1 = a + b × Δstretched + c × ΔF1 over consecutive yearly pairs with both scans scored (U1, U2) | pairs | > +0.10 |
| O2-H7x | the same b on pairs that are **not both GE** (maker from the DICOM tag) | pairs not both GE | > 0 |

- **Note on the H7 design:** only U1 and U2 are scored, so unchanged pairs are both stretched (not-stretched pairs are not scored, for cost). b is identified by the two directions of change (stretched → not, not → stretched). The dev dry check with this design gave b = +0.205 (dev, all pairs: +0.227). Expected changed pairs not both GE: about 274 by IDC metadata (interval about ±0.12); neither GE about 74 (±0.23).
- **Secondary (pre-stated, never "confirmed"):** alarm changes at τ90 (0.017994) and at τ_rad (0.033887, Sybil's dev cut matched to the radiologists' dev sensitivity): flagged in each run, lost, gained, discordant share, net change per 1,000 (two-sided estimates); by maker and stretch class (mean Δℓ̄_1, H6, flag change, share ≥ ¼ SD); the axis-0 shift (C1, dev SD units); member agreement on the 11 frozen axes; H7 details (axis 0 off, ratio 0 counted as stretched, changed pairs only, both GE / one GE / neither GE, same scanner model, group means); the z-fix change by crop (main run cropped or not; z-fix padded or not); attention under the z-fix (the R3b rule of `r10_att_harm.py`, without any outcome: nodule outside Sybil's box, share near the nodule, paired difference; "mechanistic displacement", never patient harm); G2b/G2c on every file.
- **Dropped from the reviewer's proposal:** the score-jump cuts \|Δs1\| ≥ 0.01 and "crossing 0.05" (Sybil's calibrated score takes about 200 distinct values; a new cut would be chosen without a reason).

## 4. O2c, the form check (`o2_form.py`; descriptive secondary)
- Runs **only after the O2a + O2b output is committed.** No hypothesis.
- **Design:** case-control. Cases: scored exams with a lung cancer within 1 year (y1 = 1). Controls: exams of the 800-exam random sample with y1 = 0. Also 6 years on baseline screens (reported only with ≥ 10 cancers).
- **Scores:** Sybil (as published, main run); the frozen form (F1, F6); findings only (X1's C2, fitted on Sybil's train participants only). AUROC of each; Sybil − form, Sybil − findings (participant bootstrap).
- **Expected precision:** about ±0.10 for Sybil − form with about 29 cancers. **Wording fixed now:** "same direction as the test split" (Sybil not above the form) or "not the same direction"; never "confirmed" or "proven". Limitation stated with it: this group is not a random sample of NLST cancers (Sybil's makers took almost all of them; why these 34 were left out is not known).

## 5. Wording rules (fixed now)
- O2-H1 to H6 rejected: "the slice-spacing effect replicates on people Sybil never saw". Not rejected: say so plainly.
- O2-H7x rejected: "the follow-up jump is also seen outside GE scanners". Not rejected: "outside GE we cannot show the jump (b and its interval)". Never "the effect is GE only" unless the interval excludes small positive values.
- Alarm changes: "the stretch adds (or removes) N alarms per 1,000 stretched exams at a dev-set cut"; never "patients were harmed".

## 6. Checks done before this freeze (code checks on dev; not results)
- `o2_analysis.py --dry-dev` (dev files, U1/U2 emulated from the IDC ratio): 916 stretched exams, 701 pairs; reproduces the dev values: H1 0.669 (dev 0.670), H2 −0.324 (−0.326 with ratio 0), H3 0.075 (0.0747), H6 +0.408, C1 −2.74, flags 38 lost and 31 gained, attention +6.2 points (R3b +6.3); G2 pass. `results/o2/o2_analysis_dry_dev.json`.
- `o2_form.py --dry-dev` (800 random dev exams, dev cancers): Sybil 0.968, form 0.931 (full dev: 0.969, 0.928). `results/o2/o2_form_dry_dev.json`.
- The four gzip lists in the image hold exactly their CSV bytes.

## 7. Before the first launch (from 1 December)
1. Recommended: a re-check of this plan by a fresh session (`docs/PROMPT_REVIEW_O2.md`; free; there are 10 days before the credits renew). The lead decides whether to wait for it.
2. Check usage on all three accounts (`budget.py status`); the December month must show near $0.
3. Smoke, then the runs of section 2.

## 8. Hash table (SHA-256 of the committed content, LF line ends)
| File | SHA-256 |
|---|---|
| `imgsae/exploratory/lung_l2/o2_manifest.py` | `265cc5535beb9cb0d8e29a8433068d9e99f2c69a36aad275d43287ace3d9a3cf` |
| `imgsae/exploratory/lung_l2/o2_analysis.py` | `6bc886d1b8ffb824a4484eb4f8a13cf3d7ceaf5cd669c2de805873589ae609fd` |
| `imgsae/exploratory/lung_l2/o2_form.py` | `e7803d24d9d58203b5cc328161fa597b43576ece03e4ed067dcc5ca948fd2f21` |
| `imgsae/exploratory/lung_l2/results/manifest_unseen.csv` (U1 + U2) | `fb62526557c132d3faf92eded8ae24c090f1fb2e1152d081edce501d15abf16a` |
| `imgsae/exploratory/lung_l2/cloud/l2_sybil_modal.py` | `ce872c566e49a39cebe2103934fedcc3ec17269288bcb5cea4db2041d200960f` |
| `imgsae/exploratory/lung_l2/cloud/drive_runs.py` | `39ac51b82269bb07d6230296768edea410a4c010050f2ffd34bf318b58271a8a` |
| Frozen NLST files (`results/s5/`, form parameters) | as in `HYPOTHESES_L2.md` (checked by `s6_frozen_analysis.load_frozen` at run time) |

## 9. Amendment A1 (22 Nov 2026; before any O2 scan is scored; reviews `docs/REVIEW_O2.md` (fresh Claude session) and Gemini 4 Neon (log 22 Nov))
**Why:** two independent re-checks found two genuine bugs (the outcome-based row filter inside the "outcome-free" analysis; billing not reconciled for task `o2_unseen`), one confounded secondary (attention without the geometry control), missing stop guards, and an O2-H7x population that cannot support its sentence. Nothing of O2 has been scored or read.
1. **O2-H7x (family member 6) now uses pairs where neither scan is GE** (`nge == 0`; about 74 changed pairs by IDC metadata, 37 / 37), null 0, one-sided. Wording: rejected → "the follow-up jump is also seen in pairs scanned only on Philips or Siemens scanners"; not rejected → "on pairs without a GE scanner we cannot show the jump (b and its interval)". Never "GE only" unless the interval excludes small positive values. The former population ("not both GE": 200 one-GE + 74 neither-GE changed pairs, the maker changing with the stretch in 222) is kept as a secondary. Reason: the former group is mostly GE stretched scans and scanner changes; the change makes the test stricter (dev and test neither-GE b were negative). Neon advised against changing a family member after test; the reason for the change is recorded in the log.
2. **Outcome-free form table:** F1 (and the largest-nodule size) come from `nlst_l0.build` run on a temporary copy of the tables whose prsn holds only the columns the build needs, with the two outcome columns empty: no outcome value is read and no exam is dropped because of an outcome (before: exams after a diagnosis were dropped through `dt < 0`). `nlst_l0.py` is not edited. On dev the five unchanged family statistics are identical to the frozen dry run (difference 0).
3. **Order of steps:** `o2_analysis.py` on U1 + U2 first; its output `results/o2/o2_analysis_unseen.json` is committed before `o2_manifest.py --add-u3` is run (the script refuses otherwise) and before `o2_form.py` (refuses otherwise).
4. **Launch:** `imgsae/exploratory/lung_l2/cloud/run_o2.cmd` (committed; started by hand): accounts one after the other with `wait_idle.py` between them; half-open rows `U1:0:2149` (armanfo), `U1:2149:4298` (forghanishayan), `U2:0:811` (shforghani2002); `--root unseen --zfix-max 0.65 --max-launches 6`; billing reconciled with `--task o2_unseen`. Before it: (i) usage check on all three accounts (`budget.py status --profile P --no-log`; December near $0); (ii) the three smokes, as in S6 (log 17 Nov): guard check, then `modal run --detach --profile P imgsae/exploratory/lung_l2/cloud/l2_sybil_modal.py --step smoke --n-series 3 --tier U1 --root unseen --zfix-max 0.65`, collected with `wait_collect.ps1`, then copied with `modal volume get imgsae-nlst-l2 l2 <PC copy> --force --profile P` (PC copies: shforghani2002 → `imgsae_data/lung_l2_vol`, armanfo → `lung_l2_vol_armanfo`, forghanishayan → `lung_l2_vol_forghanishayan`); (iii) the identity gate `o2_identity_smoke.py` must print PASS: exactly three copies; each smoke record: demo case within 0.005, demo volume equal, 3 of 3 U1 volumes equal to Sybil's own, no error, head weights `ba2d6d85…`, root `unseen`, tier U1; the same main (3) and z-fix series on every account; across accounts calibrated ≤ 1e-4, logits ≤ 1e-5, pooled ≤ 1e-4, all finite. `drive_plan.py` now passes `--task` to the billing reconcile. Like `run_s6.cmd`, `run_o2.cmd` does not stop on a `wait_idle.py` time-out (bounded by the job's 60-minute container limit).
5. **Stop rules enforced in code:** G2b/G2c failure; ℓ̄_1 rebuilt from `pooled` > 5e-3; an account-to-account logit difference > 1e-5 on any series scored twice; an outcome value in the form table; a non-finite logit, pooled or calibrated array; the form parameters (`results/l2_form_params.json`, LF content `02ec7c2d…8034`) or the X9 cut file (`results/x9/x9_rules_thresholds_dev.json`, LF content `3fc2f781…c6ef`) not matching → no family is computed, the output says why ("STOPPED"), and `--add-u3` and `o2_form.py` refuse to run after a stopped output. `o2_form.py` checks the frozen files of `results/s5`, the heads and the calibrator (`s6_frozen_analysis.load_frozen`) and the form parameters. A non-finite estimate or p → "not evaluated" (counts as not rejected; Holm unchanged).
6. **Fallbacks:** part of U1 not scored → O2a on the scored rows (random participants by design), with the count; fewer than 30 stretched exams with a z-fix file → O2-H1 to H6 not evaluated; fewer than 30 changed pairs in a population → O2-H7 / O2-H7x not evaluated; a bootstrap with fewer than 90% valid draws → not evaluated. In a secondary stratum whose stretch change takes a single value (for example all changed pairs in one direction and no unchanged pair), b is not identified and is not computed; the stratum reports directional means (Δℓ̄_1, Δℓ̄_1 with axis 0 off, axis-0 jump). The family size stays 6.
7. **U3 safety:** `--add-u3` refuses unless the rebuilt U1 + U2 rows equal the frozen list (SHA-256 `fb625265…abf16a`); candx_days read with `pd.to_numeric`. `o2_form.py` checks the rebuilt random sample against the full frozen hash `dbb8ee4651ae032af900b77ec0d966b02ceb5ae5e3057b10e4c1947d22a44e34`, runs G2b/G2c on every file it uses, takes the metadata path as an argument, and refuses if fewer than 95% of the 800 random-sample exams are scored.
8. **Secondaries (pre-stated now; outcome-free; never "confirmed"):** (a) the shuffled-position control for attention (500 shuffles; excess attention near the nodule over shuffled positions, main and z-fix, and their paired difference; the naive difference is kept but is not the readout) and the nodules pushed back into Sybil's box by the z-fix (count, ≥ 8 mm, Δℓ̄_1, τ90 flags); (b) alarm changes at τ90, τ_rad and at the X9 cuts set on cancer-free dev exams (`results/x9/x9_rules_thresholds_dev.json`: Lung-RADS ≥ 3 level, ≥ 4A level, radiologists' level; 6-year cut on baseline exams), and alarm changes by Lung-RADS category (X9 corrected rules, from the CT tables; groups 1–2, 3, 4A, 4B–4X) and by largest-nodule size (none, 4 to < 8 mm, ≥ 8 mm), each at τ90 and at the X9 Lung-RADS ≥ 3 level; (c) by maker and by stretch class with participant-bootstrap intervals (Δℓ̄_1, H6, axis-0 shift, τ90 flag change, ¼-SD share), and maker × class means; (d) H7 strata (all, both GE, not both GE = former H7x, one GE, one GE split by the maker of the stretched scan, neither GE, same scanner model, same model and neither GE), each with b, b with axis 0 off, b minus b with axis 0 off (paired), the axis-0 jump and the symmetric contrast ½(mean Δℓ̄_1 of not → stretched − of stretched → not); same-scanner-model b is the key secondary for "the jump is a scanner change"; (e) b when stretched exams use their z-fix score (two-sided estimate); (f) alarms per 1,000 in the later minus the earlier scan by pair direction (τ90).
9. **Text fixes:** the dry-run note of section 6 should read "H2 −0.324 on 916 exams; −0.326 on all 924 dev z-fix exams; the 8 left out by the IDC-based list have a blank IDC ratio" (not "with ratio 0"). Wording (section 5) is one sentence per hypothesis; for O2-H3: "on these people the flag changed in x% of stretched exams (test 4.5%)". The model name of a scan with no `ManufacturerModelName` is unknown, never equal to another unknown.
10. **Dry runs of the amended code (dev; code checks, not results):** `results/o2/o2_analysis_dry_dev_A1.json` (O2-H1 0.66921, H2 −0.32421, H3 0.07533, H6 0.40753, H7 0.20540: identical to the frozen dry run; O2-H7x not evaluated on dev, 20 changed neither-GE pairs < 30; the former H7x value +0.06710 now under the secondary strata; on dev the one-GE pairs with a GE stretched scan are all one direction (27 of 27), so that stratum reports directional means (a first draft computed a regression there that halved the effect; found by Neon's review of this amendment, fixed before commit); attention excess main 0.116 → z-fix 0.068, as the dev check of 17 Nov); `results/o2/o2_form_dry_dev_A1.json` (Sybil 0.9676, form 0.9314, as before; G2 0 failures on 7,336 files). `o2_manifest.py` rebuilds U1 + U2 byte-identical (`fb625265…`); `--add-u3`, `o2_form.py` (not dry) refuse while the O2a output is not committed.
11. **Hash table after amendment A1** (SHA-256 of the LF content; replaces section 8 for the files listed): section 10.
12. **Reporting order (fixed now, against forking paths):** headline descriptive alarm cuts: τ90 and the X9 Lung-RADS ≥ 3 level; τ_rad equals the X9 Lung-RADS ≥ 4A level; the radiologists'-level cut flags about half of stretched exams and is reported, not headlined. Key H7 secondary: same scanner model, with the sentence "on pairs with the same scanner model, b = x [interval]". The axis-0-carried part (b − b with axis 0 off) is reported next to every b. Every cut and every stratum appears in full tables (supplement). Paper sentence on the H7x change: "Before any O2 scan was scored, two independent reviews of the frozen O2 plan found that the original O2-H7x group ('not both GE') was mostly pairs including a GE scan; one reviewer advised keeping it with narrower wording, the other restricting it to pairs without any GE scan. In a committed amendment before scoring we adopted the stricter group (neither scan GE), and kept the original group as a pre-stated secondary."

## 10. Hash table after amendment A1 (SHA-256 of the LF content; computed 22 Nov before the amendment commit)
| File | SHA-256 |
|---|---|
| `imgsae/exploratory/lung_l2/o2_manifest.py` | `871c574d69b92a3f7ed9845379ebe43b309d8fca8f4c4d3a690000ef2e7ca4be` |
| `imgsae/exploratory/lung_l2/o2_analysis.py` | `b1309bc323b45ae94e6b9ca4a763052d4739ea8e1003d572d7e7468d18ea552d` |
| `imgsae/exploratory/lung_l2/o2_form.py` | `ee48e243af26785c76e12c8ded8bf9ef6073bc38239f0b9da63ecaf8552da34d` |
| `imgsae/exploratory/lung_l2/o2_identity_smoke.py` | `dff5abfa96fb4cf1eb4bc07a417056358488dc5bafac2995649d59579b1dcb98` |
| `imgsae/exploratory/lung_l2/results/manifest_unseen.csv` | `fb62526557c132d3faf92eded8ae24c090f1fb2e1152d081edce501d15abf16a` |
| `imgsae/exploratory/lung_l2/cloud/l2_sybil_modal.py` | `ce872c566e49a39cebe2103934fedcc3ec17269288bcb5cea4db2041d200960f` |
| `imgsae/exploratory/lung_l2/cloud/drive_runs.py` | `39ac51b82269bb07d6230296768edea410a4c010050f2ffd34bf318b58271a8a` |
| `imgsae/exploratory/lung_l2/cloud/drive_plan.py` | `36d5e34ef2ca9d044b9e7ef1cb8e767f15d1edc0d482cd9435d14758e67cf4b5` |
| `imgsae/exploratory/lung_l2/cloud/reconcile_billing.py` | `ce57db74736f25be6dd463899c9606efe5ea8236e4a5375fd5e8519dd0f6eb1a` |
| `imgsae/exploratory/lung_l2/cloud/run_o2.cmd` | `73310e4461bb2cd3105149f739d13b7432a056a5c975fab6cf382095c39c7b1b` |
| `imgsae/exploratory/lung_l2/l2_form.py` | `934d862a92114c70dd1b94c29e975eebf32496322a2fa07254ca731dd14c8548` |
| `imgsae/exploratory/lung_l0/nlst_l0.py` | `135689f2ee76fed51ba99fde88580c9559f03ca7fb9b4d7b46dac7bde5369e7f` |
| `imgsae/exploratory/lung_l2/series_rule.py` | `cff3a764f1391acaf54f5ee0f8f381a790daa16b437bee78e7e998354e4d2a2d` |
| `imgsae/exploratory/lung_l2/s2_pilot_checks.py` | `28947a43cc7f412e74bbb10cd26712faa0d125c04009f956176dac595c1f7a32` |
| `imgsae/exploratory/lung_l2/s4_common.py` | `ab4467268a8b8dcda476f52b5f3335bfefc7a9cd75a206d3e35153813ebbb9c0` |
| `imgsae/exploratory/lung_l2/s5_axes_freeze.py` | `6223a56c845134f1ccf8e9dd06afe42d78cf662ce067e2305b2fb97b17781a6d` |
| `imgsae/exploratory/lung_l2/s6_frozen_analysis.py` | `d0fc05e703e1b124f15bad215461a51ccc71d0ab249a44d0ee4cb06105b01754` |
| `imgsae/exploratory/lung_l2/s7_added_value.py` | `f321c1674fe3901fa00f8ddddc5f5fc3add0d5381784361e0d57bc62995cc658` |
| `imgsae/exploratory/lung_l2/s4_u3.py` | `65b12656af6b25678c3fc7260327603fde9884b1b19243e43c20bcdca47683f5` |
| `imgsae/exploratory/lung_l2/x7_sensitivity.py` | `8692ceb7b93b8aca76e0fb576ef555170dfc3df624e90b33cb7c104b29f51a93` |
| `imgsae/exploratory/lung_l2/x8_fixed_rules.py` | `585770fa8256e3675cd3118121b93afb6e472a260a59e62dd386acc6536b9023` |
| `imgsae/exploratory/lung_l2/x9_rules_thresholds.py` | `230cf84e748853db12028b9146ba91875a678b3b4dc4fd36eeec3d2654991342` |
| `imgsae/exploratory/lung_l2/r10_att_harm.py` | `bed85b02bdebaf60b937e4a3db26ea681e298ded7a6b99e81f31987119037b76` |
| `imgsae/exploratory/lung_l2/r9_attention.py` | `bd0904e3b5e61fa827f21c6c99c57dd71616c17920bf32577778627e73cd62cf` |
| `imgsae/exploratory/lung_l2/results/l2_form_params.json` | `02ec7c2dda14450ce06a9bc3b127d572ed9c8d6472cf37d550b68ec6283f8034` |
| `imgsae/exploratory/lung_l2/results/x9/x9_rules_thresholds_dev.json` | `3fc2f78180c472cdee22cffa5303687f84412efab36b5be47e2a9803804cc6ef` |
| `imgsae/exploratory/lung_l2/results/o2/o2_analysis_dry_dev_A1.json` | `f5c80b44bf1ab6e4794d37f6df0102ad22291cfb6b6543e7e67efe6f39195b95` |
| `imgsae/exploratory/lung_l2/results/o2/o2_form_dry_dev_A1.json` | `ac7bc854edfa048b375b4ce29bba8b6608d748da40815e6273b708f518733e85` |
| Frozen NLST files (`results/s5/`, heads, calibrator) | as in `HYPOTHESES_L2.md` (checked by `s6_frozen_analysis.load_frozen` at run time; the form parameters and the X9 cut file are checked by `o2_analysis.py`) |
