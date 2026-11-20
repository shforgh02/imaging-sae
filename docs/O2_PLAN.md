# O2: the slice-spacing tests on NLST participants Sybil never used (December 2026)

**Status:** FROZEN on 2026-11-20, before any O2 scan is scored and before any outcome of these participants is read. The freeze is the commit that adds this file. Lead's go: "do all" (20 Nov; budget $24, task `o2_unseen`). Plan choice: `docs/REVIEW_PLAN_CHOICE.md` (O2a + O2b), with the six changes of my reaction (log, 20 Nov), and the lead's wish to do the form again on these people (O2c, small and descriptive).

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
