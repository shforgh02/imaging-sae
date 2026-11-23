# Step R: can we rescue the feature extraction? (dev only, exploratory)

**Who and when:** the reviewer session (Fable 5.2), 2026-11-16 and 17, on the lead's instruction ("before I give anything to Opus, can you yourself test various methods? see if we can rescue extraction").
**Status of this work:** discovery on dev. No test data. No cloud. No money. No frozen file is changed (`results/s5/`, `HYPOTHESES_L2.md`, all `s4_*`, `s5_*`, `s6_*` scripts are untouched). New files only: `r1_arms.py` to `r6_candidate.py`, `run_r_dev.ps1`, `results/r/`, this file.
**Note on independence:** I was the reviewer of the first freeze. Here I did analysis work. If anything of step R enters the new freeze, the re-check (N2) must say so and should be done by a session that did not do this work.

## Short answer for the lead

1. **The SAE is not rescued.** Function kept for k = 4, 8, 16, 32 active features: 0.72, 0.83, 0.978, 0.88 (mark 0.98). The best setting (k = 16) still fails, and no setting finds more than 9 shared families (16 needed). The reason is Sybil, not our settings.
2. **The last layer `h` cannot be rescued by any method.** Every method finds the same 3 shared directions there: the risk score, "lung cut off in z", and one without a name. The 56 valid raw-unit families of S4 are all copies of the risk score (0 of 56 are anything else).
3. **The earlier layer `pooled` can be read, with a different tool.** All five Sybil members share **11 directions** there ("shared axes"). They repeat in both halves of dev. A shuffle check gives 0. Only 1 of the 11 is the cancer-risk direction. The clearest others are technical: z-geometry (lung cut off in z, number of slices), field of view and body size, scanner maker, breathing and image quality.
4. **One name is now proven by an experiment, not only by correlation.** The spacing fix (z-fix) moves the "z-geometry" axis by 2.74 SD. The kernel change does not move it (0.01 SD). No random axis out of 2,000 moves by 2 SD. **Note 23 Nov:** X11 (`RESULTS_L2.md` section 3j) showed that this axis reads whether a thick slab of Sybil's own padding is in its 200-slice box, not the anatomical stretch. "z-geometry" is kept in this file as the dev name.
5. **This axis explains a known result.** S4 found that the z-fix lowers the 1-year score on average (−0.326; hypothesis H2). If we switch this one axis off in every member, the average drop is gone (+0.08), and the AUROC on dev stays the same (0.9685 → 0.9699). A random axis never does this (0 of 200; and 1 of 2,000 in the stricter test).
5b. **New (17 Nov, later): a dictionary method other than raw units passes all four S4 marks at layer `pooled`.** NMF with K = 64 (the K of S4, planned before any run) is valid: 16 families, 14 of them not copies of the risk score; names T 7, N 3, mixed 3, unnamed 3; the same themes as the shared axes (z-geometry, field of view and body size, scanner maker, risk). K = 24 and 32 (added after seeing K = 16) are valid too, with 8 families. **But there is a defect the four marks do not see:** NMF cannot hold negative numbers, and half of the values in the second part of `pooled` are negative. So NMF keeps Sybil's score (r 0.997) but its rebuilt vector is worse than the plain dev mean (R² −2.8). It is a faithful copy of the function, not of the layer. Also, V2 was checked on 2 members only (the check on all five is running), and V3 is exactly at the mark (16 of 16 needed). The SAE comes close at `pooled` (K = 64, k = 16: passes V1, V2, V4; 12 families, 16 needed) and on `h` with K = 16 (passes V1, V2, V3; fails V4 by label agreement 0.67, 2 of 3 named families). **My reading:** this supports the shared-axes result (a second method finds the same themes); it is not strong enough to replace it or to build a hypothesis on.
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
| SAE k = 32 | 64 | 0.884 / 0.847 F | P | 9 F | 0.75 / 0.75 P | no | 2 |
| SAE k = 4 | 16 | 0.983 / 0.984 P (AUROC −0.004) | P | 4 P | 0.69 / 0.67 F | no (near) | 2 |
| SAE k = 8 | 16 | 0.988 / 0.985 P | P | 4 P | 0.76 / 0.67 F (2 of 3 named agree) | no (near) | – |
| SAE, K = 8 | | (running) | | | | | |

Joint dictionary on `h` (R1b; "shared" = the five member parts of a feature agree at r ≥ 0.70 on the other half):

| Arm | K | V1′ | V2′ stable | V3′ shared | V4 | Valid |
|---|---|---|---|---|---|---|
| joint PCA | 4 / 8 / 12 / 16 / 32 | 0.948 F / 0.909 F / 0.984 P / 0.995 P / 0.998 P | 3, 3, 3, 4, 4 | **2** at every K | F | no |
| group ICA | 4 / 8 / 12 / 16 | same V1′ | 3, 3, 2, 7 | 1, 0, 0, 0 | F | no |

Shared axes on `h` (R1): 1 axis shared in both halves (2 in one half). It is the z-geometry axis (r 0.98 with `lung_cut_z`; r 0.12 with the risk score; held-out agreement of the members 0.977).

**What this shows.** In `h` the five members agree on about 3 directions: risk, z-geometry, one unnamed. Raw units pass the marks only because they are many copies of the risk direction (effective dimension of the 56 families: 1.5). A less sparse SAE keeps more of the function up to k = 16 (then less again at k = 32), but it never finds more shared families (8, 8, 9, 9). The failure is a property of Sybil's last layer.

## 3. Layer `pooled`, the six arms (R4)

| Arm | K | V1 | V2 | V3 families | V4 | Valid | Not risk (named, stable) |
|---|---|---|---|---|---|---|---|
| raw | 64 | 0.983 / 0.982, AUROC 6 y −0.009 F | P | 46 P | 0.66 / 0.96 F | no | 11 (11, all T) |
| PCA | 64 | 0.998 / 0.998 P | P | 4 F | 0.83 / 1.00 P | no | 3 (2) |
| ICA | 64 | 0.998 / 0.998 P | P | 5 F | 0.56 / 0.50 F | no | 5 (2) |
| k-means | 64 | 0.954 / 0.952 F | P | 0 F | – | no | – |
| raw | 16 | 0.980 / 0.979, AUROC 6 y −0.012 F | P | 15 P | 0.63 / 1.00 F | no | 0 of 15 |
| **PCA** | 16 | r 0.993 / 0.993 but AUROC 6 y **−0.0053** F (mark 0.005) | P | 4 P | 0.83 / 1.00 P | **no, by a hair** | 3 (2) |
| **ICA** | 16 | r 0.993 / 0.993 but AUROC 6 y **−0.0053** F | P | 6 P | 0.81 / 0.83 P | **no, by a hair** | 5 (5) |
| **NMF** | 16 | r 0.993 / 0.992 but AUROC 6 y −0.0078 F | P | 7 P | 0.79 / 1.00 P | no (near) | 5 (4) |
| k-means | 16 | 0.938 / 0.935 F | P | 2 F | 0.83 / 0.50 F | no | 1 |
| **NMF** | **64** (planned) | 0.998 / 0.997 P | P (2 members; all five running) | **16 P** (mark 16) | 0.81 / 0.90 P | **yes** | 14 (8 named, 7 stable) |
| SAE k = 16 | 64 | 0.995 / 0.995 P | P | 12 F | 0.79 / 1.00 P | no (near) | – |
| raw | 24 / 32 (added) | 0.980 / 0.982, AUROC 6 y −0.011 / −0.010 F | P | 20 / 28 P | 0.64 / 0.65 F | no | 1 / 3 |
| PCA | 24 / 32 (added) | 0.996 / 0.997 P | P | 4 / 4 F | 0.83 / 1.00 P | no | 3 |
| ICA | 24 / 32 (added) | 0.996 / 0.997 P | P | 5 / 3 F | 0.84 / 0.80 P; 0.85 / 0.67 F | no | 4 / 3 |
| **NMF** | **24 / 32 (added)** | 0.995 / 0.996 P | P (2 members) | 8 / 8 P | 0.84 / 0.86 P; 0.81 / 0.86 P | **yes** (K chosen after seeing K = 16) | 6 / 6 (5 named, stable) |
| k-means | 24 / 32 (added) | 0.944 / 0.948 F | P | 0 F | – | no | – |

**The NMF defect (found 17 Nov; not covered by the four marks).** Held-out reconstruction of the layer itself (R² in z-units, all live units): PCA 0.70 to 0.81, ICA 0.70 to 0.81, SAE 0.75, k-means 0.51 to 0.57, raw units 0.01 to 0.04, **NMF −2.83 to −2.93**. Reason: part 2 of `pooled` (convolution + attention pool) is negative in 49% of its values, and NMF works on max(x, 0). On `h` (all values ≥ 0) this problem does not exist. So at `pooled` NMF keeps Sybil's score but not the vector. This is a caveat for any use of the NMF result; I recommend reporting it as supporting evidence only.

The NMF K = 64 families, in short (full table `results/r/r1_pooled_nmf_K64_families.csv`): two risk families (r 0.86 and 0.81 with the 6-year score; nodule size, spiculation, attenuation); two z-geometry families (lung cut in z +1.00; number of real slices −0.95); four field-of-view / body-size families (reconstruction diameter, body area, sex); maker and model families; one breathing / emphysema family (mixed); three unnamed.

Joint dictionary on `pooled` (R1b): joint PCA has 3 to 4 shared features at every K (4 to 32); V1′ passes only at K = 32 (0.990), where V3′ and V4 fail. Group ICA: 0 to 4 shared. Not valid.

**What this shows.**
- At K = 64 the per-member dictionaries do not line up across members (4 to 5 families; 16 needed).
- At K = 16 they do much better: PCA, ICA and NMF pass three marks, with named families that are not copies of the risk score, and miss the fourth mark only by the AUROC change at 6 years (−0.0053 against 0.005). So in `pooled` a small dictionary is almost valid. This agrees with section 4: there are roughly 4 to 7 directions that line up member by member, and about 11 that are shared as a space.
- The members share directions, but each member writes them in its own basis. That is the case the shared-axes method is made for.

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

## 7. Last runs (17 Nov) and what was stopped
- NMF on `pooled`, K = 64, with V2 on **all five members** (`results/r/v2full/`): still valid (V1 0.998 / 0.997, 16 families, V4 0.81 / 0.90). The NMF defect of section 3 stays.
- SAE on `pooled`, K = 64: k = 16 passes V1, V2, V4, fails V3 (12 families of 16); k = 4 fails V1 (AUROC 6 y −0.007) and V3 (11).
- Stopped on 17 Nov to free the PC for the executor (they cannot change sections 4 to 10): SAE on `pooled` at K = 16, SAE on `h` at K = 8.

## 8. What can go wrong, and how it is guarded
| Risk | Guard |
|---|---|
| The axes are an accident of dev | Shared on the held-out half in both directions; shuffle null 0; the test set will show it again or not |
| The name is only a correlation | For axis 0 the name is tested by intervention (z-fix moves it, kernel does not) |
| The hypothesis is near-automatic (the first H5 mistake) | Random-choice test with 2,000 random axes: 0% and 0.05% |
| Steps were added after seeing results | Marked in the plan table and logged before each run; everything is dev; only the test set confirms |
| The reviewer did the analysis | Said at the top; the re-check must be done by a session that did not do this work; the executor reruns the scripts |
| Over-reading the repair test | It removes the average shift, not the scatter; it is not a fix of Sybil and not a clinical result |

## 9. Step R2: more candidate hypotheses (17 Nov; the lead asked "the harm? using the form?")
Plan and code committed before the run (`52b5e83`; scripts `r7_more.py`, `r8_three.py`). Results `results/r/r7_more_pooled.json`, `r8_three_pooled.json`.

### 9A. Real follow-up: does the slice-spacing effect happen in real repeated screening? (outcome-free) → **candidate C3**
The z-fix is our own experiment. But in real life the same person is screened every year, and sometimes the reconstruction changes between years (stretched one year, not the next). Dev has 4,837 pairs of consecutive yearly screens; in 215 the stretch status changes.
Model: change of ℓ̄_1 (later minus earlier) = a + b × (change of stretch: +1, 0, −1) + c × (change of the form's score F1). The form term removes real changes the radiologist saw (a new or growing nodule).

| | Pairs (changed) | b: score change when a screen becomes stretched | 95% interval | Halves | b with axis 0 switched off |
|---|---|---|---|---|---|
| **all pairs** | 4,837 (215) | **+0.246** | [0.134, 0.355] | 0.222 / 0.272 | **−0.094** [−0.208, 0.014] |
| same scanner model | 3,462 (56) | +0.216 | [−0.057, 0.471] | 0.256 / 0.184 | −0.126 |
| both screens without cancer at 1 y (sensitivity) | 4,743 (205) | +0.279 | [0.171, 0.380] | 0.254 / 0.307 | −0.063 |

- Axis 0 itself jumps by **2.29 SD** [2.14, 2.41] when the stretch status changes between screens (same size as under the z-fix, 2.74).
- Raw group means of Δℓ̄_1: stretched → not −0.17 (146 pairs); unchanged +0.04 (4,622); not → stretched +0.22 (69).
- Flag flips between the two screens: 12.3% (stretched → not), 10.1% (not → stretched), 9.2% (unchanged). Small difference; not tested.
- Permutation test (2,000 shuffles of the stretch change): 2.5% of shuffles give b above +0.10 (largest 0.15). Below the 5% rule, but not by much.
- **What this shows:** in real repeated screening, when the scanner reconstructs a person's scan with overlapping slices one year and not the next, Sybil's 1-year score jumps by about 0.25 logit, beyond what the radiologist's findings explain. With the shared z-geometry axis switched off, the jump is gone. This is our z-fix effect, seen again **without our intervention**, in real data, with the same mechanism.
- **Proposed hypothesis C3:** b > +0.10 (the H2 margin), on test pairs of consecutive screens; needs only the main runs, the metadata, the frozen form model F1; the switched-off version needs the frozen axis. **Honest chance on test: about 0.7** (dev interval lower end 0.134, close to the null; test will have a similar number of pairs).
- Limits: observational (a scanner change can bring other changes; the same-model subset agrees but is small); the form term adjusts only for what the radiologist recorded.

### 9B. Harm through false alarms or misses, with the form → **no harm signal; not testable**
- Sybil's false-alarm rate (people without cancer at 1 year): stretched 10.9%, other 11.3% (difference −0.5 points [−3.1, +2.5]).
- Sybil-only false alarms (Sybil flags, the form does not): stretched 9.1%, other 7.6% (+1.5 points [−0.9, +4.1]). Not different. (The form itself flags fewer stretched exams: 7.2% against 10.4%; the stretched scans come from other sites and scanners.)
- z-fix in the 906 stretched exams without cancer: Sybil-only false alarms 80 → 75 (31 lost, 26 new): a reshuffle, not a reduction.
- Misses at 1 year: stretched 0 of 18 cancers missed; other 6 of 70. Expected stretched 1-year cancers in test: about 12. **No test of harm through misses can have power.**
- **What this shows:** on dev there is no sign that the stretch makes Sybil worse for patients. "Sensitivity, not harm" stays the honest wording. No harm hypothesis is proposed.

### 9D. What Sybil sees beyond the radiologist → **descriptive only (fails the random-choice test)**
- The form explains 19% of the variance of Sybil's 1-year logit. Of the rest ("beyond the radiologist"): the risk axis explains 54%, the five technical axes 14%, the other five axes 7%, all 11 axes 75%.
- Random-choice: 5 random directions explain a median 11%, and 33% of random sets explain as much as the technical axes. So "technical axes carry Sybil's disagreement with the radiologist" would be near-automatic. Not proposed.

### 9C. 3 of 5 members → **few extra axes, weak, technical; not proposed**
- Each of the 10 sets of 3 members has **11 to 13** shared axes (all five members: 11). So a looser rule gives only 0 to 2 more per set.
- Most axes of the 3-member sets are the same as the five-member axes (|r| 0.87 to 1.00 for the first six or seven).
- New axes: 12 groups, 4 of them found in at least 2 sets. All four are near zero with the risk score (|r| ≤ 0.08) and weakly named (technical variables explain 12% to 33%): lung cut / image quality; lung cut / emphysema; scanner model / artefact; **kernel sharpness** (+0.50; found in members 0, 2, 4 and 0, 3, 4 only).
- **What this shows:** the five members agree on about 11 directions, and three members do not agree on many more. "More axes" from a looser rule are weak technical leftovers. The kernel-sharpness axis that only some members have fits H4 (the kernel matters little to the ensemble score).

## 10. Step R3: where Sybil looks (17 Nov; descriptive only; the lead asked "can we show the nodule Sybil sees?")
Data: Sybil's saved attention (25 slice bins of its 200-slice box; 16 × 16 places per bin) and the radiologist's recorded nodules (NLST CT abnormality table: slice number and lobe of each nodule). The slice numbers fit our series (2.4% out of range; upper-lobe nodules at 29% of the scan length, lower-lobe at 58%). Box order and image side were chosen on participant half A and reported on half B.

**10a. Does the stretched box cut off nodules?** Rarely. In stretched exams 8 of 588 recorded nodules (1.4%) fall in the cut-off part; 2 of 112 nodules of 8 mm or more; 1 in an exam with cancer within 1 year. Other exams: 0 of 4,359.

**10b. Does Sybil look at the nodule?** Yes.

| Exams (half B) | Attention within ±1 bin of the nodule | Shuffled nodule positions | Peak within ±1 bin | Attention on the nodule's lung side |
|---|---|---|---|---|
| cancer within 1 year (38) | **72%** | 26% (97.5th 39%) | 74% | **88%** |
| no cancer, nodule ≥ 8 mm (425) | 51% | 22% | 56% | 77% |
| no cancer, nodule 4 to 8 mm (1,033) | 32% | 23% | 35% | – |

The maps are coarse: one bin is 8 resampled slices (20 mm of the box), one place is about 22 mm.

**10c. Harm proxy: does the stretch move attention away from the nodule? → No evidence; the naive answer was an artefact.** (Step R3b, `r10_att_harm.py`, added after 10b and logged before it ran.)
- Naive numbers: stretched 27% against other 40% near the nodule; z-fix raises the stretched exams from 27% to 34% (+0.063 [0.038, 0.088], halves 0.062 / 0.063). This looks like harm repaired by the fix.
- **But it is geometry.** A ±1-bin window covers a different share of the lung in a stretched box (the lung fills twice as many bins). With **shuffled** nodule positions the same comparisons give: z-fix +0.110 [0.089, 0.133]; stretched 0.157 against other 0.237.
- Corrected (attention near the nodule minus the shuffled value): main 0.115 → z-fix 0.068 (same 335 exams); stretched 0.114 against other 0.160 (different exams, sites and nodules: not comparable). So, if anything, Sybil focuses better on the nodule in the stretched picture it was trained on.
- A code error was found and fixed before any result was reported: the z-fix table repeats the main run's `resampled_T`; the z-fix slice count is n_images × true spacing / 2.5.
- **What this shows:** no sign that the stretch makes Sybil look away from nodules. The lesson of H5 again: always compare with a shuffled or random baseline.

## Files
- Scripts: `r1_arms.py`, `r2_shared.py`, `r3_joint.py`, `r4_axes_audit.py`, `r5_repair.py`, `r6_candidate.py`, `r7_more.py`, `r8_three.py`, `r9_attention.py`, `r10_att_harm.py`, `run_r_dev.ps1`
- Results: `results/r/` (`r1_*.json` and family tables, `r2_shared_*.json`, `r2_axes_*.csv`, `r3_joint_*.json`, `r4_axes_audit_pooled.json`, `r4_axes_pooled.csv`, `r5_repair_pooled.json`, `r6_candidate_pooled.json`)
- Fitted axes (outside git): `D:\Shayan\imgsae_data\lung_l2\r\r2_shared_pooled.pkl`
