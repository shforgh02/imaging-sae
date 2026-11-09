# Protocol (lean, DRAFT for Zenodo registration after a Phase 1 GO)

Study: are sparse-autoencoder features of medical imaging foundation models valid?
Registration: Zenodo DOI + git tag `p2-lock`, before any confirmation data are encoded.
This draft is completed from Phase 1 development results only, by the rules below. It is not tuned to any confirmation result.

## 1. Hypotheses
Holm over 4 primaries, familywise α = 0.05.

| ID | Estimand | Data / encoder | Decision |
|---|---|---|---|
| H1 proxy | θ = AUROC of twin score t_f for validity (V2 ∧ V3) among V0 single-fit features, frequency/magnitude-adjusted | TotalSegmentator confirmation, CT-FM | adequate if LB ≥ 0.70; inadequate if UB < 0.75 |
| H2 baselines | Δ normalised area under C(τ) (gated anat+path), consensus − strongest baseline (locked in Phase 1) | same | superiority, LB > 0 (Nadeau–Bengio t, J = 10) |
| H3 consensus vs single | Δ area under C(τ) | same | non-inferiority, margin 0.05; key secondary R1 superiority |
| H4 clinical | (SAE score-set csPCa AUROC increment over PSAD + age + volume) − (texture-baseline increment) | PI-CAI confirmation half, DINOv3 2.5D | non-inferiority, margin 0.03 (paired patient bootstrap) |

Secondaries:
- H1–H3 on DINOv3-TotalSegmentator.
- Matryoshka vs plain consensus.
- On PI-CAI: R1, lesion selectivity/AUROC, shortcut share, and the lesion-size threshold (P8).

Predictions P1–P8 with falsifiers are as in IMAGING_SAE_LEAN_v1.md.

## 2. Locked from Phase 1 (filled in by script from data/p1)
- Spacing and token size (`data/p1/spacing.json`).
- s\*, n_eff, M\*, k (`concepts.json`).
- Eligible and gated concepts and the beyond-HU tier (`gates.json`). Gating is recomputed on confirmation with the same rule.
- Strongest baseline (`decision.json`).
- Thresholds, set by rule:
  - t_f cut = max(0.7, the 99th percentile of the random-code twin score);
  - r_pert cut = the 5th percentile of organ positive-control probe directions;
  - selectivity 0.7 and AUROC 0.80, with sweeps reported.

## 3. Data roles
- TotalSegmentator v2: Phase 1 development (150, `p1_dev_ids.txt`) and confirmation (555, `p2_conf_ids.txt`). Hashes in `imgsae/data/SHA256SUMS`.
- PI-CAI: 50/50 split by patient, stratified by centre × csPCa, seed 0, hashed before download.
  - Lesion labels: human_expert/resampled (220 positives) + Pooch25 (205 positives).
  - Clinical reference: PSAD + age + volume.

## 4. Analysis
- Patient is the unit. J = 10 (TotalSegmentator) or J = 5 (PI-CAI) patient-grouped half replicates, with new seeds each time.
- Cross-fitted scoring.
- R1 and areas: Nadeau–Bengio corrected t. Fixed-model metrics: patient-cluster bootstrap (2,000 draws).
- Sensitivity analyses: threshold sweeps; not-evaluable features counted as fails; leaf-level atlas.

## 5. Blinding and deviations
- Jobs come only from a sealed job list.
- Only metric-blind crash fixes are allowed. Every deviation goes in EXECUTION_LOG.md.
- No scan is excluded after scoring. Post-hoc improvements are allowed only if disclosed and applied as rules.

## 6. Human rung (V4)
- 40 features: 20 consensus, 10 sparse varimax, 10 null.
- 2 readers × 3 region-matched intruder trials (chance 1/6), on a static HTML page.
- Pass at ≥ 4/6 correct with the name matching the V2 concept.
- If no readers are available, this is reported as not done.
