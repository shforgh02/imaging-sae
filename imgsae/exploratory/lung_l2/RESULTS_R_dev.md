# Step R: can we rescue the feature extraction? (dev only, exploratory)

**Who and when:** the reviewer session (Fable 5.2), 2026-11-16 and 17, on the lead's instruction ("before I give anything to Opus, can you yourself test various methods? see if we can rescue extraction").
**Status of this work:** discovery on dev. No test data. No cloud. No money. No frozen file is changed (`results/s5/`, `HYPOTHESES_L2.md`, all `s4_*`, `s5_*`, `s6_*` scripts are untouched). New files only: `r1_arms.py` to `r6_candidate.py`, `run_r_dev.ps1`, `results/r/`, this file.
**Note on independence:** I was the reviewer of the first freeze. Here I did analysis work. If anything of step R enters the new freeze, the re-check (N2) must say so and should be done by a session that did not do this work.

## Short answer for the lead

1. **The SAE is not rescued.** With more active features it comes closer (function kept 0.72 → 0.83 → 0.978 for k = 4, 8, 16), but it still fails. The reason is Sybil, not our settings.
2. **The last layer `h` cannot be rescued by any method.** Every method finds the same 3 shared directions there: the risk score, "lung cut off in z", and one without a name. The 56 valid raw-unit families of S4 are all copies of the risk score (0 of 56 are anything else).
3. **The earlier layer `pooled` can be read, with a different tool.** All five Sybil members share **11 directions** there ("shared axes"). They repeat in both halves of dev. A shuffle check gives 0. Only 1 of the 11 is the cancer-risk direction. The clearest others are technical: z-geometry (lung cut off in z, number of slices), field of view and body size, scanner maker, breathing and image quality.
4. **One name is now proven by an experiment, not only by correlation.** The spacing fix (z-fix) moves the "z-geometry" axis by 2.74 SD. The kernel change does not move it (0.01 SD). No random axis out of 2,000 moves by 2 SD.
5. **This axis explains a known result.** S4 found that the z-fix lowers the 1-year score on average (−0.326; hypothesis H2). If we switch this one axis off in every member, the average drop is gone (+0.08), and the AUROC on dev stays the same (0.9685 → 0.9699). A random axis never does this (0 of 200; and 1 of 2,000 in the stricter test).
6. **Limits, said plainly.** (a) The 11 axes are a set of readings, not a full dictionary: rebuilt from them alone, Sybil's score is kept at r 0.95, below the 0.98 mark. (b) Switching the axis off removes the average drop, but only part of the exam-by-exam change (share of exams moving ≥ 0.25 SD: 0.67 → 0.55). (c) All of this is dev. (d) It does not improve cancer prediction.

**What it means for the paper:** we now have a real feature-level result. It is not "SAE features of Sybil". It is "five separately trained Sybil members agree on a small set of directions; most are technical; one of them carries the model's systematic reaction to slice spacing, shown by intervention". Two candidate hypotheses for the test set pass the gate and the random-choice test (section 6).

## The question
In S4 only "raw units" passed all four validity marks. The SAE, PCA, ICA, NMF and k-means failed. Is that the fault of our settings (layer, number of features K, sparsity k, per-member fitting), or of Sybil itself?

## Plan (fixed before any run on all dev; commit `68f4637`)
The marks are the same as S4 (protocol 9.5), from the same code (`s4_core.py`, `s4_decomp.py`, imported, not changed):
- **V1** function kept: logits from the rebuilt vector correlate ≥ 0.98 with Sybil's own, AUROC change ≤ 0.005.
- **V2** seed stability. (Scouting simplification: members 0 and 1 only; member 0 only for the SAE. S4 used all five. V2 was never the problem.)
- **V3** at least K/4 families found in ≥ 3 of the 5 members.
- **V4** naming repeats in the two halves (≥ 0.70 both ways).
- New, descriptive only: **how many families are not copies of the risk score** (|r| with ℓ̄_6 below 0.5).

| Step | What is tested | Script | Fixed when |
|---|---|---|---|
| R1 | Shared axes of the five members (multiset CCA), layers `h` and `pooled` | `r2_shared.py` | before any run |
| R2 | SAE less sparse on `h`: K = 64, k = 8, 16, 32 (S4: k = 4) | `r1_arms.py` | before any run |
| R3 | Smaller K on `h`: K = 8 and 16, all six arms | `r1_arms.py` | before any run |
| R4 | Earlier layer `pooled`: six arms, K = 64 and 16 | `r1_arms.py` | before any run |
| R5 | Change of the shared axes under z-fix and kernel change; removal test | `r4_axes_audit.py` | planned before; written after R1 |
| R1b | One joint dictionary for the whole ensemble (joint PCA, group ICA) | `r3_joint.py` | **added after R1 on `h` was seen** (log note 1) |
| R6 | Repair test; random-choice test for the axis shift | `r5_repair.py` | **added after R5 was seen** (log note 2) |
| R7 | Gate numbers and random-choice test for two candidate hypotheses | `r6_candidate.py` | **added after R6 was seen** (log note 3) |

Every run is reported, also the failed ones. Steps added after seeing results are marked above and in `docs/EXECUTION_LOG.md`.

## 1. Code check
`r1_arms.py` on `h`, K = 64 gives the S4 numbers again: raw units V1 0.999 / 0.997, 56 families, V4 0.71 / 0.85, labels N 34, mixed 16, T 6 (valid); PCA 3 families (not valid). The saved logits are reproduced from `h` and from `pooled` (through Sybil's own `hidden_fc` and head) within 1e-6. `r5_repair.py` with nothing removed gives the S4 z-fix numbers again (share 0.670, mean Δℓ̄_1 −0.326).

## 2. Layer `h`: nothing more to find (R2, R3, R1b)
P = pass, F = fail. "Families" = found in ≥ 3 of 5 members. "Not risk" = families with |r| to the risk score below 0.5.

| Arm | K | V1 (r 1 y / 6 y) | V2 | V3 families | V4 (corr / agree) | Valid | Not risk |
|---|---|---|---|---|---|---|---|
| raw | 64 | 0.999 / 0.997 P | P | 56 P | 0.71 / 0.85 P | **yes** | **0 of 56** |
| raw | 16 | 0.996 / 0.994 P | P | 16 P | 0.72 / 0.92 P | **yes** | 0 of 16 |
| raw | 8 | 0.987 / 0.985 P | P | 8 P | 0.71 / 0.83 P | **yes** | 0 of 8 |
| PCA | 8 | 0.999 / 0.998 P | P | 3 P | 0.64 / 1.00 F | no | 2 |
| ICA | 8 | 0.999 / 0.998 P | P | 3 P | 0.59 / 1.00 F | no | 2 |
| NMF | 8 | 0.996 / 0.995 P | P | 5 P | 0.75 / 0.67 F | no (near) | 2 |
| k-means | 8 | 0.947 / 0.945 F | P | 1 F | 0.90 / 1.00 P | no | 1 |
| PCA | 16 | 0.996 / 0.990 P | P | 3 F | 0.64 / 1.00 F | no | 2 |
| ICA | 16 | 0.996 / 0.990 P | P | 2 F | 0.26 / 0.00 F | no | 1 |
| NMF | 16 | 0.970 / 0.970 F | P | 5 P | 0.61 / 0.67 F | no | 3 |
| k-means | 16 | 0.970 / 0.967 F | P | 0 F | – | no | – |
| SAE k = 4 (S4) | 64 | 0.716 / 0.732 F | P | 8 F | 0.84 / 0.75 P | no | – |
| SAE k = 8 | 64 | 0.826 / 0.824 F | P | 8 F | 0.77 / 0.75 P | no | 4 |
| SAE k = 16 | 64 | 0.978 / 0.977 F (AUROC −0.007) | P | 9 F | 0.73 / 0.71 P | no | 3 |
| SAE k = 32 | 64 | (running) | | | | | |
| SAE, K = 16 and 8 | | (running) | | | | | |

Joint dictionary on `h` (R1b; "shared" = the five member parts of a feature agree at r ≥ 0.70 on the other half):

| Arm | K | V1′ | V2′ stable | V3′ shared | V4 | Valid |
|---|---|---|---|---|---|---|
| joint PCA | 4 / 8 / 12 / 16 / 32 | 0.948 F / 0.909 F / 0.984 P / 0.995 P / 0.998 P | 3, 3, 3, 4, 4 | **2** at every K | F | no |
| group ICA | 4 / 8 / 12 / 16 | same V1′ | 3, 3, 2, 7 | 1, 0, 0, 0 | F | no |

Shared axes on `h` (R1): 1 axis shared in both halves (2 in one half). It is the z-geometry axis (r 0.98 with `lung_cut_z`; r 0.12 with the risk score; held-out agreement of the members 0.977).

**What this shows.** In `h` the five members agree on about 3 directions: risk, z-geometry, one unnamed. Raw units pass the marks only because they are many copies of the risk direction (effective dimension of the 56 families: 1.5). A less sparse SAE keeps more of the function, but then it finds no more shared families (8, 8, 9). The failure is a property of Sybil's last layer.

## 3. Layer `pooled`, the six arms (R4)

| Arm | K | V1 | V2 | V3 families | V4 | Valid | Not risk (named, stable) |
|---|---|---|---|---|---|---|---|
| raw | 64 | 0.983 / 0.982, AUROC 6 y −0.009 F | P | 46 P | 0.66 / 0.96 F | no | 11 (11, all T) |
| PCA | 64 | 0.998 / 0.998 P | P | 4 F | 0.83 / 1.00 P | no | 3 (2) |
| ICA | 64 | 0.998 / 0.998 P | P | 5 F | 0.56 / 0.50 F | no | 5 (2) |
| NMF, k-means, SAE; K = 16 | | (running) | | | | | |

Joint dictionary on `pooled` (R1b): V2′ and V4 pass at K = 4 to 12, 3 to 4 shared features, but V1′ fails (0.94 to 0.977). Not valid.

**What this shows.** Per-member dictionaries do not line up across members in `pooled` either (4 to 5 families). The members do share directions, but each member writes them in its own basis. That is the case the shared-axes method is made for.

## 4. Layer `pooled`, shared axes (R1): 11 axes
Method: per member z-score, PCA to 30, whiten; multiset CCA (MAXVAR) on one half of the participants; an axis is shared if the five member variates agree at mean pairwise r ≥ 0.70 **on the other half**.

- Shared axes: **12 and 11** (the two directions). Held-out agreement 0.995, 0.96, 0.94, 0.94, 0.90, 0.86, 0.84, 0.83, 0.81, 0.78, 0.75 (0.71).
- Shuffle null (exam order shuffled inside each member): **0** shared axes, largest agreement 0.014.
- Stability: all 11 axes fitted on half A are found again when fitted on half B (r 1.00 to 0.73).
- The 11 axes explain 94% of the variance of the mean logit (1 y and 6 y).
- Function kept from the shared axes alone: r 0.95 (mark 0.98: **fails**); AUROC −0.007 (1 y), −0.024 (6 y).
- Sensitivity: with 50 PCs per member the count is higher (16 in one half; full numbers in `r2_shared_pooled_npc50.json`). So "11" is the count at the pre-set 30 PCs; "at least 11" is the safe reading.
- Naming (same Shapley rule as S4): T 5, I 2, mixed 3, unnamed 1. Naming repeats in the halves: median 0.76, label agreement 1.0 (V4 passes).

| Axis | My plain name (from the top associations) | Label | r with risk (6 y) | Named well? | z-fix moves it (SD) | Kernel moves it (SD) | Removed: exams moving ≥ 0.25 SD | Removed: AUROC 1 y |
|---|---|---|---|---|---|---|---|---|
| 0 | **z-geometry**: lung cut in z +0.98, real slices +0.93, z-stretch +0.79 | T | 0.12 | yes (R² 0.91) | **−2.74** [−2.77, −2.71] | +0.01 | 11.5% | 0.970 |
| 1 | **field of view / body size**: recon diameter −0.77, male −0.67, body area −0.66 | T | −0.17 | yes (0.81) | −0.55 | +0.04 | 13.1% | 0.966 |
| 2 | **breathing quality / scanner model**; AUROC for cancer at 1 y 0.81 | T | 0.30 | yes (0.70) | −0.21 | 0.00 | 38.2% | 0.961 |
| 3 | **risk axis**: spiculated and large nodules | mixed | −0.85 | (0.42) | −0.06 | −0.05 | 69.4% | 0.785 |
| 4 | **scanner maker**: Siemens +0.95, GE −0.86 | T | 0.11 | yes (0.87) | −0.24 | −0.14 | 0.1% | 0.969 |
| 5 | image quality and lung density | I | −0.26 | partly (0.37) | −0.11 | +0.02 | 21.9% | 0.966 |
| 6 | weak (lung cut in xy, artefact) | mixed | 0.03 | no (0.11) | +0.21 | −0.13 | 0.0% | 0.969 |
| 7 | graininess, lung density | I | −0.01 | weak (0.20) | +0.03 | −0.02 | 0.0% | 0.969 |
| 8 | weak | mixed | 0.08 | no | +0.05 | +0.19 | 1.4% | 0.969 |
| 9 | none | unnamed | −0.05 | no | +0.24 | +0.02 | 0.0% | 0.968 |
| 10 | weak technical | T | 0.02 | weak (0.17) | +0.53 | +0.10 | 0.0% | 0.969 |

AUROC before removal: 0.9685 (1 y), 0.851 (6 y). Dev flatters Sybil (caution C6); read the AUROC columns only as "changes or does not change".
Removal baseline: a random direction of the same space moves 0.6% of exams (median; 95th percentile 5.6%).

Sets: the five technical axes removed together: 51% of exams move ≥ 0.25 SD, flags change in 4.3%, AUROC 0.960 / 0.843. The risk axis removed: AUROC 0.785 / 0.712. All 11 removed: AUROC 0.573 / 0.630 (almost all of Sybil's signal passes through the 11 shared axes).

**What this shows.**
- The five members were trained separately, yet they agree on these directions. That is evidence that the directions are real properties of how Sybil reads a scan, not accidents of one training run.
- Most of what the members agree on is technical, not clinical. Only one axis is the risk axis.
- The technical axes are not idle: they feed the score (axes 0, 1, 2 and 5 move 11% to 38% of exams; random: about 1%).
- Axis 2 is a warning: a "technical" axis that also separates cancers on dev (AUROC 0.81). It mixes scanner model, breathing quality and something related to cancer. It needs a closer look before any claim.

## 5. Repair test (R6): one axis carries the systematic z-fix shift
The axis is set to its dev mean in every member, for the main run and for the z-fix run. Only that one direction of each member's vector changes. D5 exams (n = 924, 424 participants).

| What is removed | Mean z-fix change of ℓ̄_1 | Share of exams moving ≥ 0.25 SD (ℓ̄_6) | Flag changes | AUROC 1 y / 6 y (all dev) |
|---|---|---|---|---|
| nothing (= S4) | **−0.326** [−0.366, −0.282] | **0.670** [0.638, 0.701] | 6.2% | 0.9685 / 0.8509 |
| **axis 0** | **+0.081** [0.042, 0.125] | **0.550** [0.511, 0.588] | 5.7% | 0.9699 / 0.8496 |
| the five technical axes | +0.066 [0.027, 0.109] | 0.578 [0.543, 0.612] | 5.4% | 0.9602 / 0.8434 |
| one random direction (200 draws) | −0.43 to −0.21 | 0.61 to 0.72 | 5.2% to 7.6% | – |
| any other single axis (1 to 10) | −0.42 to −0.26 | 0.61 to 0.72 | – | – |

Kernel change (D4, n = 500): removing axis 0 changes nothing (share 0.192 → 0.190).
(The flag here is ℓ̄_1 at its own 90th percentile, an approximation of the S4 flag.)

**What this shows.** The average drop of the score under the spacing fix passes through one direction that all five members share. Without it the drop is gone, and discrimination on dev is unchanged. The exam-by-exam scatter is only partly explained (0.67 → 0.55), so the axis is not the whole story. Removing more technical axes does not help and costs AUROC.

## 6. Two candidate hypotheses for the test set (R7)
Both use only what S6 saves anyway (`pooled` for the main and the z-fix run), the frozen dev axis (no refit), and no outcomes.

| | Statistic (D5 / T5 exams) | Dev estimate | 95% interval | Halves | Proposed null | Gate 9.8 | Random-choice test (2,000 random axes) |
|---|---|---|---|---|---|---|---|
| **C1** | mean change of axis 0 under z-fix, in SD | −2.740 | [−2.765, −2.714] | −2.763 / −2.718 | < −2.0 | passes | **0%** pass (largest −1.84) |
| **C2** | [mean Δℓ̄_1 with axis 0 switched off] − [mean Δℓ̄_1 as Sybil gives it] | +0.408 | [0.403, 0.412] | 0.412 / 0.404 | > +0.20 | passes | **0.05%** pass (largest 0.226) |

Note: with a 1 SD margin C1 would be near-automatic (6% of random axes move by ≥ 1 SD, because the z-fix changes the whole input). That is why the proposed null is −2.0.

**My recommendation:** take **C2** as the one feature-level hypothesis. It says more than C1: not only "the axis moves", but "the axis carries the model's systematic reaction". C1 goes to the secondary list. My honest chance estimate on test for C2: high (about 0.9), because the effect is physical (slice spacing), outcome-free, and four times the random maximum is not needed, only 0.20 against 0.41. The main risk is that the test scanners differ from dev so that the frozen axis fits less well; the secondary number "agreement of the five members on axis 0 in test" will show that.

## 7. What is still running (will be added here)
SAE with k = 32 on `h`; SAE at K = 16 and 8; the remaining arms on `pooled` (NMF, k-means, SAE, K = 16); joint dictionary on `pooled` at K = 16 and 32. None of them can change sections 4 to 6.

## 8. What can go wrong, and how it is guarded
| Risk | Guard |
|---|---|
| The axes are an accident of dev | Shared on the held-out half in both directions; shuffle null 0; the test set will show it again or not |
| The name is only a correlation | For axis 0 the name is tested by intervention (z-fix moves it, kernel does not) |
| The hypothesis is near-automatic (the first H5 mistake) | Random-choice test with 2,000 random axes: 0% and 0.05% |
| Steps were added after seeing results | Marked in the plan table and logged before each run; everything is dev; only the test set confirms |
| The reviewer did the analysis | Said at the top; the re-check must be done by a session that did not do this work; the executor reruns the scripts |
| Over-reading the repair test | It removes the average shift, not the scatter; it is not a fix of Sybil and not a clinical result |

## Files
- Scripts: `r1_arms.py`, `r2_shared.py`, `r3_joint.py`, `r4_axes_audit.py`, `r5_repair.py`, `r6_candidate.py`, `run_r_dev.ps1`
- Results: `results/r/` (`r1_*.json` and family tables, `r2_shared_*.json`, `r2_axes_*.csv`, `r3_joint_*.json`, `r4_axes_audit_pooled.json`, `r4_axes_pooled.csv`, `r5_repair_pooled.json`, `r6_candidate_pooled.json`)
- Fitted axes (outside git): `D:\Shayan\imgsae_data\lung_l2\r\r2_shared_pooled.pkl`
