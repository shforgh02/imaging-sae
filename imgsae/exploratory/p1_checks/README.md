# Phase 1 exploratory checks (post hoc)

**Date:** 2026-11-08 · **Status:** done · **Requested by:** user, after the Phase 1 NO-GO memo (`docs/DECISION_MEMO_P1.md`).

These checks are **post hoc and exploratory**. They do **not** change the pre-written Phase 1 verdict (NO-GO), the plan, the main code
or the main results. Everything here only reads `imgsae/data/p1/` and imports the unchanged production scripts. Every check first
reproduces the official run number exactly (sanity row), then changes one thing.

## Bottom line
1. **The NO-GO stands.** Checks 1 and 2 each find a measurement problem, but neither flips the SAE result: with the problem
   removed, the SAEs still lose to simple baselines (soft k-means, raw sparse coordinates).
2. **The chimera rule, as coded, is what made the result "degenerate"** (≈ 0 validated features for every method). It counts the
   'other' class (fat / unlabelled tissue, 45% of tokens) as a foreign concept, so 80–100% of all features are rejected. Treating
   'other' as neutral removes the degeneracy, but the ranking of methods stays the same.
3. **Gate S fails because of position, not because of the label leak.** CT-FM is no better than the reference as long as the reference
   has *any* position (even label-free body x/y). Without position, CT-FM is ahead on 4 concepts (gate S would pass).
4. **Several gate-S concepts rest on very few tokens** (esophagus 3, clavicula 2, iliac vessels 2 in the 60 k probe sample).
   Esophagus AUROC 0.30 is small-sample noise, not a feature bug.

## Check 1 — why ≈ 0 validated features for every method (`c1_ladder_funnel.py`, `c1b_chimera_other.py`)
- `c1`: per-feature funnel from the saved run tables (`data/p1/fit/*.csv`): the chimera step removes 79–100% of V0 features for **every**
  method (`results/c1_ladder_funnel.csv`).
- `c1b`: refits replicate 0 with the unchanged `p1_fit.py` code and seeds; scores each feature with the chimera rule as run ("orig") and
  with 'other' adjacent to all concepts ("neutral"). 'orig' areas equal the run's areas exactly for all 9 methods.

| method | area (run) | area, 'other' neutral | chimeric share orig → neutral | chimera flags caused by 'other' |
|---|---|---|---|---|
| soft_kmeans (baseline) | 0.042 | **0.273** | 0.79 → 0.05 | 98% |
| raw_sparse (baseline) | 0.005 | **0.217** | 0.96 → 0.10 | 99% |
| sparse_varimax (baseline) | 0.000 | 0.095 | 0.96 → 0.11 | 98% |
| sae_single (CT-FM) | 0.007 | 0.066 | 0.89 → 0.08 | 97% |
| null_enc_cons (random-init encoder) | 0.003 | 0.031 | 0.84 → 0.05 | 95% |
| hu_sae_cons (reference features) | 0.000 | 0.016 | 0.92 → 0.05 | 94% |
| pca | 0.000 | 0.002 | 1.00 → 0.04 | 100% |
| varimax | 0.000 | 0.000 | 1.00 → 0.11 | 100% |
| **sae_cons (CT-FM, 5-fit consensus)** | 0.000 | **0.000** | 0.86 → 0.04 | 100% |

- With the neutral rule ≥ 2 methods have C(0.7) > 0 → the degeneracy check would pass; D1 would still fail (SAEs below soft k-means).
- The consensus SAE has only 34–38 consensus features; they are reproducible (median t 0.80) and perturbation-stable (median r 0.92)
  but **none is organ-selective** (median sel 0.31, need ≥ 0.7) — they look like broad tissue-type features (e.g. bone, soft tissue)
  spread over several organ groups.
- Not explained here: single-fit SAE R1 is 0.04–0.07 (consensus 0.56). Worth a seed-stability check if the SAE line continues.

## Check 2 — does gate S depend on the label-derived position? (`c2_probe_position.py`)
Same probe, same 60 k tokens, same CT-FM out-of-fold probabilities; only the reference input changes. Sanity row reproduces `gates.json` exactly.

| reference | features | gated | beyond-HU | gate S | median reference AUROC |
|---|---|---|---|---|---|
| HU + context + position (as run; z = vertebral level from masks) | 83 | 32 | 0 | fail | 0.998 |
| HU + context + label-free x/y position (no z) | 74 | 32 | 0 | fail | 0.995 |
| HU + context, no position | 56 | 32 | **4** | **pass** | 0.966 |

Beyond-HU without position: iliac_vessels, prostate, small_bowel, urinary_bladder (iliac vessels on 2 tokens, prostate on 8).
Reading: CT-FM's advantage over intensity alone is mostly *where the token is*; a body-relative x/y coordinate recovers it. The
label leak in the z position is real but is not what decides gate S. The plan's reference includes position by design.

## Check 3 — esophagus AUROC 0.30 (`c3_esophagus.py`, `results/c3_concept_counts.txt`)
- Esophagus has 47 core tokens (occupancy ≥ 0.8) in all 1.02 M rows — it is thinner than a 16 mm token — and **3 tokens from 2 patients**
  in the 60 k probe sample. 3 of 5 CV folds have no positive; the AUROC is computed on 3 tokens. Direct one-vs-rest probe: CT-FM 0.56, reference 0.88.
- The probe sample is a uniform draw, 68% 'other'. 11 of 33 concepts have ≤ 15 sample tokens; clavicula and iliac_vessels are "gated" on 2.
  Eligibility counts patients on all rows (≥ 10), the probe then sees far fewer. A concept-stratified sample would make gate S statistics reliable.

## Files
| file | what |
|---|---|
| `c1_ladder_funnel.py` → `results/c1_ladder_funnel.csv` | funnel per method / rep / half from the run tables |
| `c1b_chimera_other.py` → `results/c1b_chimera_rep0.json`, `results/c1b_<method>_rep0_<half>.csv` | refit rep 0, chimera orig vs neutral |
| `c2_probe_position.py` → `results/c2_probe_position.json` | gate S with 3 reference variants |
| `c3_esophagus.py` → `results/c3_esophagus.json`; `results/c3_concept_counts.txt` | esophagus diagnosis; tokens per concept |
| `logs/` | run logs (c2 log contains harmless lbfgs convergence warnings for the reference variants) |

Run from this folder: `..\..\.venv\Scripts\python <script>.py`. Runtime: c1 seconds, c1b ~75 min (GPU), c2 ~25 min, c3 ~10 min (CPU).
