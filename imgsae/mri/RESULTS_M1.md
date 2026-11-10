# MRI M1 results: does the model know cancer beyond intensity? **Gate FAILED**

- **Date:** 2026-11-10.
- **Data:** dev half only (753 studies, 737 patients); the sealed half was not opened.
- **Protocol:** `docs/MRI_M0M1_PROTOCOL.md` §6, with its implementation notes written before any result.
- **Code:**
  - encode: `cloud/m1_encode_modal.py`, `m1_lib.py`, `encoders_lib.py`;
  - analysis: `m1_analysis.py`;
  - post hoc checks: `m1_diagnostics.py`.
- **Result files:** `results/m1_results.json`, `results/m1_diagnostics.json`.

## 1. Outcome

**The fixed gate failed, on all studies and on verified studies.**

| Nested 5-fold CV | Δ AUROC vs intensity reference R | Δ vs untrained network | Needed to pass |
|---|---|---|---|
| all studies | **−0.022** [−0.038, −0.007] | −0.005 [−0.020, +0.010] | Δ vs R ≥ +0.03 with lower bound > 0, and Δ vs untrained ≥ +0.05 |
| verified studies | **−0.023** [−0.039, −0.007] | −0.004 [−0.019, +0.011] | same |

In plain words: tissue is cut into 4 mm cells and each cell is called cancer or normal gland. For that task, a simple reference does at least as well as every frozen MRI foundation model. The reference R has 66 features: intensity histograms, local context, position in the gland and zone.

The extra cancer information in the best model (MRI-CORE) is small: about +0.01 AUROC, in post hoc checks (§4). An SAE on these tokens would therefore mostly rediscover intensity (dark ADC, bright high-b DWI), not a new clinical feature. **Per the protocol, M1 stops here and the lead decides.**

## 2. Data

- **Probe tokens:** 164,116 (13,516 lesion, 150,600 normal gland), from 753 studies of 737 patients.
- **Excluded:** 11050_1001070 (M0 QC).
- **Encode:** 753/753 studies, 0 errors. Modal cost $3.85 (task `mri_m1_encode` at $4.45 of $5.00); the analysis ran on the laptop.

## 3. Results under the fixed protocol

### 3.1 Every arm

Full dev 5-fold CV, patient-weighted token AUROC, protocol probe (C = 1).

| Arm | AUROC |
|---|---|
| **R** (intensity reference, 66 features) | **0.912** |
| MRI-CORE B (768-d) | 0.909 |
| MRI-CORE B, per-slice min–max input (side check) | 0.907 |
| MRI-CORE A (2,304-d) | 0.903 |
| MRI-CORE B, no ImageNet normalisation (side check) | 0.902 |
| untrained SAM ViT-B (null) | 0.894 |
| SAM A | 0.894 |
| ProFound stage 0 (image exposure to PI-CAI) | 0.882 |
| SAM B | 0.879 |

### 3.2 Rule S inside the nested folds

| Outer fold | Chosen | Δ (chosen − R) on inner CV | ProFound − U [95% CI] |
|---|---|---|---|
| 0 | MRI-CORE B | +0.002 | −0.029 [−0.048, −0.010] |
| 1 | MRI-CORE A | −0.006 | −0.032 [−0.055, −0.008] |
| 2 | MRI-CORE B | +0.007 | −0.032 [−0.051, −0.013] |
| 3 | MRI-CORE B | −0.012 | −0.018 [−0.036, −0.001] |
| 4 | SAM A | −0.010 | −0.024 [−0.040, −0.008] |

- **ProFound** was below the best unexposed model in every fold. It was never chosen.
- **Selection on the full dev CV** would have been MRI-CORE B (Δ vs R −0.003). This is moot now that the gate failed.
- **The pooled nested Δ (−0.022) is partly a pooling effect.** Two folds chose a weaker arm, and pooling scores from different models costs AUROC. The mean of the per-fold Δs is −0.015, chosen vs untrained +0.001, and MRI-CORE B alone −0.003. Every version is far below +0.03.

### 3.3 Descriptive outputs

All rows are MRI-CORE B − R on full-CV scores, unless stated.

| Analysis | Δ AUROC [95% CI] |
|---|---|
| **By zone** | |
| PZ tokens | −0.006 [−0.022, +0.010] |
| TZ tokens | −0.031 [−0.047, −0.014] |
| **By normal-token subset** | |
| clean normals (no ISUP 1 lesion, PI-RADS ≤ 2) | −0.002 [−0.014, +0.010] |
| verified normals | −0.003 [−0.016, +0.011] |
| **Within each centre** | |
| PCNN | +0.022 [+0.000, +0.048] |
| RUMC | −0.009 [−0.024, +0.005] |
| ZGT | −0.019 [−0.052, +0.016] |
| **RUMC, by outline source** | |
| Pooch25 | −0.012 [−0.031, +0.006] |
| resampled | −0.006 [−0.029, +0.017] |
| **Leave one centre out** (annotation-dependent, see M0) | |
| PCNN held out (54 resampled outlines) | +0.012 [−0.013, +0.038] |
| RUMC held out (67 Pooch25, 51 resampled) | −0.048 [−0.065, −0.028] |
| ZGT held out (40 Pooch25) | −0.040 [−0.068, −0.011] |
| **Other arms** (full-CV) | |
| MRI-CORE − SAM, mode B | **+0.030** [+0.019, +0.041] |
| MRI-CORE − SAM, mode A | +0.009 [−0.004, +0.021] |
| MRI-CORE B input: per-slice min–max − ImageNet-normalised | −0.002 [−0.007, +0.003] |
| MRI-CORE B input: no ImageNet normalisation − ImageNet-normalised | −0.007 [−0.017, +0.003] |

What the table shows:
- **MRI pretraining helps compared with natural-image pretraining** (MRI-CORE vs SAM), but only up to about R's level.
- **The MRI-CORE input scaling does not explain the failure.**
- **R holds up better across centres than the encoders do.**

### 3.4 Patient level

Each study is scored by the highest probe score over all its gland cells.

| Population | Studies (csPCa) | MRI-CORE B | R | Δ [95% CI] | Reference: PI-RADS alone |
|---|---|---|---|---|---|
| Biopsy cohort (verified, PI-RADS ≥ 3) | 437 (206) | 0.658 | 0.656 | +0.003 [−0.053, +0.057] | **0.718** |
| All dev studies | 753 (212) | 0.701 | 0.718 | −0.016 [−0.060, +0.026] | n/a |

- In the biopsy cohort, the csPCa rate is 13% for PI-RADS 3 (78 studies), 40% for PI-RADS 4 (176) and 68% for PI-RADS 5 (183).
- Both image scores fall below the radiologist's PI-RADS.

## 4. Post hoc checks

These are descriptive only and do not change the gate (`m1_diagnostics.py`).

- **D1 alignment (bug check, label-free).** Each arm's features were used to predict the cell's own mean T2W, ADC and HBV, and those of shifted cells.
  - Every arm predicts best at zero shift. In-plane R² falls from 0.96 to 0.82–0.88 one cell away for MRI-CORE, and in-plane alignment is similarly correct for the other arms.
  - ProFound changes little between neighbouring slices (0.79 vs 0.78). That is expected: its 4 mm stage-0 cells are thicker than the 3–3.6 mm slices.
  - **The features are mapped correctly; no bug.**
- **D2 probe regularisation.** The same probe at C = 0.001, 0.01, 0.1 and 1 for every arm, R included.
  - With strong regularisation (C = 0.001), MRI-CORE A rises to 0.928 against R's best of 0.915: **+0.014** [+0.001, +0.026].
  - MRI-CORE B reaches +0.002 [−0.009, +0.013]. All other arms stay below R.
  - The protocol's C = 1 over-fits the 2,304-d arm. The best C sits at the edge of the grid, and picking the best C on the test folds flatters every arm equally.
- **D3 added value.** R + MRI-CORE B against R + untrained network (the control for simply adding more features): **+0.013** [+0.003, +0.022] at C = 0.01, and similar at C = 0.1 and 1.

The two answers agree: **MRI-CORE carries a small, real amount of cancer information beyond intensity, position and zone, about +0.01 AUROC.** That is less than half the gate's pre-set margin of 0.03.

## 5. What this means and the options

Under the fixed rule, M1 failed. The finding is robust:
- the mapping is correct;
- input scaling and probe regularisation do not change it;
- adding the encoder to R gains only about 0.01.

The likely reason: at the 4 mm scale, csPCa tissue in expert outlines is mostly defined by what the radiologist sees in ADC and high-b DWI, which R measures directly. The frozen encoders add little on top.

Options for the lead (my recommendation first):
1. **Stop the frozen-encoder SAE line on PI-CAI (recommended).**
   - M2 would most likely give SAE features that restate intensity, not a new clinical finding.
   - Record the negative result.
   - Spend nothing more until a new question is agreed, ideally with the radiologist colleague.
2. **Move to the clinically hard question, as a short laptop feasibility check before any new plan.**
   - The question: csPCa vs no csPCa among PI-RADS ≥ 3, where radiologists struggle (13% csPCa at PI-RADS 3).
   - The check: does any image representation add to PI-RADS (plus PSAD, once the 11051_1001071 volume issue is handled)?
   - Features already exist for the dev half, so this costs no Modal money.
   - It needs a new written protocol, because it is a different question from M1's.
3. **Continue to M2 anyway, as labelled exploration** with MRI-CORE A at strong regularisation. This overrides the pre-set stop rule; I do not recommend it.
