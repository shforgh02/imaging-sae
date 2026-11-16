# Lung L2: frozen hypotheses for the test split (S5)

- **Status:** FROZEN on 2026-11-16 by the executing session, **waiting for the external reviewer's note and the lead's OK**. No test activation, test image measure or test variant has been extracted, and no new outcome analysis of the L1 test scores has been made. The test manifest has not been built.
- **Rules:** `docs/LUNG_L2_PROTOCOL.md` section 10 (hypothesis freeze) and section 11 (test confirmation), amendments A1 to A5 (section 16a).
- **Dev evidence:** `RESULTS_S4_dev.md`; result files in `results/s4/` (S4 code fixed at commit `a536192` before any full-dev run). Gate 9.8: `results/s4/s4_gate_dev.json` and `.md`.
- **Frozen files:** `results/s5/` (thresholds, dictionary, family labels, F+I parameters, secondary combinations), written by `s5_freeze.py`. **Frozen analysis:** `s6_frozen_analysis.py` (reads only the frozen files; refits nothing). Its run on dev as if it were test (`results/s5/s6_dev_as_if_test.json`) reproduces the S4 dev values of all five statistics exactly (difference 0.0).
- **Participants:** 2,493 dev participants in Sybil's split file, 2,492 with a usable exam. Dev: 7,336 exams.

## The family
Five hypotheses, one family. **Holm correction, family-wise α = 0.05, one-sided in the stated direction.** Each statistic: participant bootstrap (2,000 draws, seed 0) for the 95% interval; one-sided p from the Wald statistic (estimate − null) / SD of the bootstrap draws. A hypothesis is confirmed if Holm rejects its null.

None of the five is "partly seen": none can be computed from the L1 test scores and the form. Each uses a quantity never computed on test (z-fix change, kernel-pair change, a group contribution of frozen features). Four are outcome-free (they describe Sybil's behaviour); H5 is feature-based and uses the valid primary arm (raw units).

Frozen values (from `results/s5/frozen_thresholds_L2.json`): τ90 = 0.017993675 (90th percentile of the published 1-year score s1 among dev exams with y1 = 0, all screens); SD reference of ℓ̄_6 = 0.92957453 (all 7,336 dev main exams); z-fix population = spacing/thickness ≤ 0.65.

Notation: ℓ̄_t = mean of the five member logits for year t; s1 = Sybil's published (calibrated) 1-year score; flag = s1 ≥ τ90.

| | Statistic | Population (test) | Direction, null (= margin) | Dev estimate [95% CI]; halves | Dev counts | Chance on test (mine) |
|---|---|---|---|---|---|---|
| **H1** z-fix moves the score materially | share of exams with \|ℓ̄_6(zfix) − ℓ̄_6(main)\| ≥ 0.25 × 0.92957 | T5: z-fix variants of T1 to T3 series with spacing/thickness ≤ 0.65 | > 0.30 | 0.670 [0.638, 0.701]; 0.669 / 0.671 | 924 exams, 424 participants, 16 one-year cancers | 0.98 |
| **H2** z-fix lowers the score | mean of ℓ̄_1(zfix) − ℓ̄_1(main) | T5 | < −0.10 | −0.326 [−0.366, −0.282]; −0.320 / −0.332 | same | 0.97 |
| **H3** z-fix changes the screening flag | share of exams whose flag differs between main and zfix | T5 | > 0.05 | 0.0747 [0.0558, 0.0971]; 0.0741 / 0.0753 | same | 0.60 |
| **H4** the kernel rarely changes the flag | share of sharp/soft pairs whose flag differs | T4: 500 soft-kernel partners of T1 exams and their main series | < 0.05 | 0.018 [0.008, 0.030]; 0.028 / 0.008 | 500 pairs, 500 participants | 0.92 |
| **H5** technical-named features carry part of the score | Cov(G_T, ℓ̄_1) / Var(ℓ̄_1), G_T = exact contribution of the 6 T-named raw-unit families (frozen dictionary and labels) | all scored test main exams (T1 to T3) | > 0.03 | 0.0505 [0.0501, 0.0509]; 0.0504 / 0.0506 | 7,336 exams, 2,492 participants | 0.93 |

## Each hypothesis in words, with its dev evidence and my reasons
### H1, H2, H3: Sybil's slice-spacing error (protocol C2; U1b; Q1d ii)
- **What:** Sybil places slices at the DICOM slice thickness, not at their real spacing. Where the spacing is at most 0.65 of the thickness, the chest is stretched along z (1.5× to 2×). "z-fix" runs the same images with the true spacing.
- **Dev evidence** (`results/s4/s4_q1d_dev.json`, section `zfix.D5`; 924 dev exams from all three screening rounds, 424 participants): H1 0.670 (protocol U1b qualification: ≥ 30%); H2 −0.326 logits (0.32 of the between-exam SD of ℓ̄_1); H3 0.075. The same in both stretch classes (1.6: 333 exams, mean −0.28, share 0.60, flag change 0.072; 2.0: 591 exams, −0.35, 0.71, 0.076) and with or without a lung cut by the crop. AUROC in these exams (descriptive): z-fix does not raise it.
- **Chances:** H1 and H2 test a mechanical property of Sybil and of the scan geometry. The test series come from the same trial, scanners and protocols (about 743 test series with spacing/thickness ≤ 0.65 expected, protocol section 7), so I expect almost the same values: 0.98 and 0.97. H3 is the weakest: the dev lower bound (0.056) is close to the null 0.05, test has fewer such exams (about 743 against 924), and the flag depends on where the scores of these exams fall around τ90. With an expected value near 0.075 and a standard error near 0.012, the chance that its one-sided test passes is about 0.60 to 0.70; I state 0.60.
- **Margins:** H1's margin is the protocol's (U1b). H2's margin (−0.10) and H3's margin (0.05) are set now, from dev. **Disclosure:** in the S4 gate list (my own pre-specification, written before the full-dev run), the flag-change statistic had the U1b margin 0.10 and **failed** it (0.075). H3 uses a lower margin chosen after seeing dev.

### H4: the reconstruction kernel rarely changes Sybil's flag (Q1d i)
- **What:** the same acquisition reconstructed with a sharp and a soft kernel. Simon et al. (*Invest Radiol* 2025) found no AUROC difference between kernels; the within-exam effect on Sybil's decision is not published.
- **Dev evidence** (`results/s4/s4_q1d_dev.json`, section `kernel_pairs`; 500 pairs, 500 participants, 8 one-year cancers): flag change 0.018; sharp minus soft ℓ̄_1 +0.028 [0.009, 0.049]; SD of the change 0.21 of the between-exam SD; ICC 0.98.
- **Chance 0.92:** test pairs are drawn the same way (500 soft-kernel partners of baseline exams, seed 0, stratified by maker). The null 0.05 is more than five standard errors above the dev value.
- **Disclosure:** the S4 gate list had this statistic with the opposite direction ("the kernel changes the flag in more than 10%"), which **failed**. H4 is the robustness statement the dev data support, chosen now.

### H5: technical-named features carry a part of Sybil's score (Q1b; feature-level)
- **What:** raw units is the only decomposition arm that passed all four validity marks (V1 to V4) at K = 64 (`results/s4/s4_decomp_dev_raw_K64.json`); the sparse autoencoder, PCA, ICA, NMF and k-means did not. Of its 56 replicated families, 6 are named T: risk units whose activation is mainly explained by technical factors (lower when the lung is cut by Sybil's 200-slice crop, thick slices, z-stretch, one Philips model; `results/s4/s4_families_dev_raw_K64.csv`). Their exact contribution carries 5.05% of the variance of ℓ̄_1.
- **Dev evidence** (`results/s4/s4_q1b_u_dev.json`, `group_shares.lbar1.T`; 7,336 exams, 2,492 participants): 0.0505 [0.0501, 0.0509], halves 0.0504 / 0.0506. K = 128 check (`results/s4/s4_decomp_dev_raw_K128.json`): raw units is again valid, with 21 T-named families carrying 0.109.
- **Chance 0.93:** the share depends only on the frozen dictionary and on the distribution of test `h`, which should be close to dev. The risk is a different mix of scan geometry in test.
- **What it does and does not show:** it confirms that this fixed set of internal units carries a part of the score on new data. It does not re-test their technical label on test (that would need a refit).

## Considered and not frozen (with reasons)
- **U1a technical removal** (`s4_u1a_dev.json`): its point values qualify (ratio 0.31, AUROC change −0.001 and −0.002), but the bootstrap interval of the spread ratio is [0.34, 1.36] and the halves disagree (1.43, 0.63): gate 9.8 **failed**.
- **U3 Sybil + form at the radiologists' sensitivity** (partly seen): ratio 0.70 [0.35, 1.05]: gate 9.8 **failed**.
- **"U adds to F" and "Sybil adds to F+I"** (dev +0.04 to +0.10, gate holds): on test, L1 already found that Sybil adds almost nothing to the recorded findings (+0.000 at 1 year all screens, +0.011 at 6 years baseline). These hypotheses would be close to partly seen, and my chance estimate is about 0.15 to 0.25. They are reported in S6 as secondary references (A3 F+I combination), not confirmed.
- **Q2 image and technical variables in false alarms** (e.g. larger lungs in Sybil-only false alarms, SMD 0.19): small, and the pattern across false-alarm classes suggests site and protocol mixes.
- **Q2 family and group-term SMDs, Q1b family covariances with U, Q1c stable shares, U2 R-learned:** near-automatic (raw units are Sybil's own risk units; the classes are defined by Sybil's score).
- **Kernel mean shift** (+0.028): holds on dev, but it is tiny; H4 states what matters for screening.
- **Q1a technical share** (0.016 at 1 year): small; H5 covers the technical part at the feature level.

## Secondary references at S6 (outside the Holm family; labelled secondary)
From `frozen_thresholds_L2.json` → `secondary`: AUROC of Sybil (s1 for y1 all screens; s6 for y6 baseline), F, R-size, F+I (frozen parameters); the frozen A3 combination (F+I + Sybil) minus F+I; the frozen U3 table (false alarms per 1,000 at the radiologists' test sensitivity for the call, Sybil, F, the frozen combination C and F+I); descriptive z-fix and kernel statistics and all group shares. Everything else at S6 is exploratory (protocol 11).

## S6 run plan (fixed now)
- **Account:** `shforghani2002`, December 2026 (amendment A4: S6 stays on the main account). Every launch through the guard; the unattended driver (A5).
- **Before any test launch:** the lead's OK of this file is logged; only then is the test manifest built and the job changed to read it (protocol 11; plan P6). A smoke run on the test path comes first.
- **Tiers and order:** T1 baseline (2,279) → T2 year 1 (2,243) → T4 (500 soft-kernel partners of T1 exams, seed 0, stratified by maker) → T3 year 2 (2,193). All main runs with `--zfix-max 0.65`: the T5 z-fix variants are made in the same job as their main series, so T5 grows with T1, T2 and T3. All five tiers are used (H1 to H3 need T5, H4 needs T4, H5 needs T1 to T3).
- **Fallbacks (fixed now):** if T3 is not scored, H1 to H3 use the T5 rows of T1 and T2, and H5 uses T1 and T2; if T4 is not scored, H4 is "not evaluated" and counts as not confirmed; if no T5 row exists, H1 to H3 are "not evaluated".
- **Checks before the analysis (protocol 11):** G2a demo; failures < 5% per tier; G2b and G2c on every file; identity: calibrated scores of the re-extracted main series equal the L1 scores within 1e-4 for ≥ 99% of the 5,412 L1 series.
- **Cost projection** (billed S3 rates, which include preemption restarts; not the protocol's older $0.0023): main rows with z-fix variants $0.0026 per row (D1 rest billed $0.00262, D2 to D4 $0.00254), pair rows $0.0023. T1 to T3: 6,715 × $0.0026 = $17.46; T4: 500 × $0.0023 = $1.15; smoke and image rebuild about $0.30. **Total ≈ $18.9**; with a 10% preemption reserve ≈ $20.8.
- **Against the budget:** task `lung_l2_audit` has $45.00 − $21.70 = $23.30 left; minus $1.00 = **$22.30**. The projection ($18.9, or $20.8 with the reserve) is below it, so no extra decision is needed. The margin is thin (about $1.5 with the reserve). S6 allocation in the protocol: $20.00 (stop rule +10%: $22.00). Project after S6 ≈ $66 of $72.

## What I ask the external reviewer to check
The brief `docs/REVIEWER_BRIEF_L2.md` (items 1 to 8). In particular: the disclosures on the margins of H2 to H4 (set at S5 from dev; H3 and H4 failed my provisional S4 margins), and whether a family with four outcome-free hypotheses and one feature-level hypothesis is the right confirmatory set.

## SHA-256 of the frozen and analysis files

| File (path from `imgsae/exploratory/lung_l2/`) | SHA-256 (committed content) | git blob id |
|---|---|---|
| `results/s5/frozen_thresholds_L2.json` | `3d4908bd46d49538806f29570cc762e598a5790bbe0bfe00b3dc8cb4f87af047` | `629dd496e6442da1da7338b3cd0eae4b876e56c3` |
| `results/s5/frozen_raw_arm_K64.npz` | `635d8bf6bce56b2ad9f2691a2ee0fdd1e1b8a5235250b289c783a7c9f61af967` | `e2b73fac87517158cd1550d511fa7d31c12447a5` |
| `results/s5/frozen_families_raw_K64.json` | `467af4904ef0cea363cdc2a18e7a33ce289008b89da5b957ea612bdff2788018` | `87052b68a46a2943896c3353c58740021cf279ad` |
| `results/s5/frozen_FI_params.json` | `09a05e98ef088d4c88a80de0d899827504dc0ad89a0f3580f4bee78ba3e6cfc3` | `5a0fa23b957e276ac20b953fa156f720da858f9b` |
| `results/s5/frozen_combinations.json` | `db04367288a9e45000990e56382a9e9007db15b2878a910361eb9f6aa110b778` | `73fe89387bb8d2514f3e7882f6b6f6ea045887db` |
| `results/s5/s6_dev_as_if_test.json` | `3af6d19179b8f9cfbc6e5a63522134df2e1ce1cd91270180ad28431c844b2f5a` | `12641da202e02817a3f4b748178252f3f2ea4fc2` |
| `s6_frozen_analysis.py` | `dd29a7e40722a47104dd698fbc47bf744bdb1bb5be43a0faef659da1bd6f6106` | `052676b42ba620d4a307aef7d7c47b4d2eacf317` |
| `s5_freeze.py` | `b6466463430ec3597dcdb06cfa2e40588d33aa5540d3cfd1c22733b8aa7a013e` | `8257a7d861ea18a6d2d724dc268be4cd4a1f0019` |
| `s5_hashes.py` | `5b5fe3d7ec8874b6ccc2455b802355102b4e1031061aa7343498416810624723` | `0a63ef38f9b330e8ef1a9de4340aa5ea7d916aff` |
| `s4_common.py` | `ab4467268a8b8dcda476f52b5f3335bfefc7a9cd75a206d3e35153813ebbb9c0` | `9cb8640a874013d40fa56a04257e235e029e4240` |
| `s4_core.py` | `637493e1fdcf2251dbb296e90a47be174e2a47495533902f7f4499a8a9f6e40b` | `f90dfc0aa7cf7edf1d16bef58b474bbbaaab6590` |
| `s4_q1a.py` | `9c22e96ef7b67aa104906033ab729e9568c411faedec1da91c8866eccfce53e7` | `13e9e8deed8650fcadd3a9329b0c245de8bfe685` |
| `s4_q1d.py` | `f7418d5a376628dc8b67e128a6de43876fc6b01be022acdf9c6e26a50a6c4d63` | `72bf8442b4dba0dfc6e1a95b1ad6865bdbfadc98` |
| `s4_refs.py` | `e3d32dc5b3dae24f057e01d1865af8aeab57a81d6a9bd522d6b9251d634d3e0b` | `fd64546ab340e1df5d30a031b4ebf5ce55397450` |
| `s4_u3.py` | `65b12656af6b25678c3fc7260327603fde9884b1b19243e43c20bcdca47683f5` | `cf6fafad0dbc58c39ac53afa948e11d332bd82a3` |
| `l2_data.py` | `7af12f02a0c89be188ab61e41820dccd99f3bc3f10c850c62976050c2605fb30` | `5f484c4cacfe3a058a1b655261ca9d5f4e41e439` |
| `l2_form.py` | `934d862a92114c70dd1b94c29e975eebf32496322a2fa07254ca731dd14c8548` | `41b33594517ca1e83342745fecfaae2d89ee8fba` |
| `../lung_l0/nlst_l0.py` | `135689f2ee76fed51ba99fde88580c9559f03ca7fb9b4d7b46dac7bde5369e7f` | `d8b87fa7a0fc47d8270d677c7741c0d0df254b1a` |
| `results/l2_form_params.json` | `02ec7c2dda14450ce06a9bc3b127d572ed9c8d6472cf37d550b68ec6283f8034` | `97d086b6e9a23caff3990f67a54c2ed31771d635` |
| `results/manifest_dev.csv` | `8fe372a690c551767e6a9a6eedae9e48439dc14009f07ba201bff8b9dea4b2ac` | `f44823a71faca9d4a1312a755af9a9bfa96a1cec` |
| `lung_l2_vol/l2/run_info/heads.npz` under `imgsae_data/` (PC only: Sybil's head weights or calibrator, saved by the cloud job) | `ba2d6d85d330cc6c99360c557647460ba4fa7ab738abba9be79c1d26b8009bac` | — |
| `lung_l2_vol/l2/run_info/sybil_ensemble_simple_calibrator.json` under `imgsae_data/` (PC only: Sybil's head weights or calibrator, saved by the cloud job) | `74cedae39715fa1ca29ebad881790432639d39fd0a3cf811529ebce9a767393a` | — |

Text files are hashed on their committed content (LF line endings). The frozen folder `results/s5/` is stored byte-exact (`-text` in `.gitattributes`), so `Get-FileHash` or `sha256sum` on a checkout gives these values. For the other text files on Windows with `core.autocrlf`, use `git show HEAD:<path> | sha256sum` or compare the git blob ids (`git ls-tree HEAD <path>`). The commit that freezes this file is logged in `docs/EXECUTION_LOG.md`. In P6 the cloud job `cloud/l2_sybil_modal.py` changes only to read the test manifest (protocol 11); that change is logged and touches no analysis file.
