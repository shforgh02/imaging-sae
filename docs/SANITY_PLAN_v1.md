# Sanity-check pivot: plan v1 (2026-11-08)

## Context
Phase 1 ended NO-GO (`docs/DECISION_MEMO_P1.md`). Two of the post-hoc checks (`imgsae/exploratory/p1_checks/README.md`) suggest a different paper:
- **Check 2.** On 16 mm organ tokens, CT-FM is not detectably better than HU + context + position: 0 of 32 concepts are beyond-HU.
- **Check 1b.** With 'other' treated as neutral, soft k-means (0.273) and raw sparse channels (0.217) beat the SAEs (single 0.066, consensus 0.000).

Gemini suggests turning this into a "double sanity check" paper: CT foundation models don't beat physics + position, and SAEs don't beat clustering. The goal of this plan is to find out, cheaply and honestly, which version of that story the data supports. After that we freeze the analysis and confirm it on held-out scans before writing anything.

## My assessment of the Gemini idea
**Agree.**
- A baseline/sanity-check paper is a better use of Phase 1 than stopping, and it fits your SAE reality-check line of work.
- Its two "15-minute" checks are good and cheap:
  - a token-level probe on the random-init CT-FM (already encoded as `X_null`);
  - k-means on the reference features.
- Most of the new work runs on the CPU.

**Disagree / must fix before any claim:**
1. **This is a ceiling effect, not a tie.** Median AUROC is 0.998 for CT-FM and 0.998 for the reference. The probe only scores clean interior tokens: partial tokens, label −2, are dropped by `atlas.partition`. So this shows the *benchmark* is saturated. It does not show that the FM "adds nothing". "Explains 99.5% of what the FM knows" misreads AUROC.
2. **Gemini's feature counts are invented.** The real blocks are:
   - 28 local features: 22-bin HU histogram, mean, SD, and 4 texture filters;
   - 28 context features: the same 28 averaged over 3×3×3 tokens, i.e. 48 mm;
   - 18 x/y position features;
   - 9 z position features (`tokens.ref_features`, `tokens.position_features`).

   The texture filters are already inside the 56.
3. **SAE vs k-means is not a fair fight yet.**
   - The sparse baselines ran at L0 = 6; the single SAE ran at L0 = 27.
   - Feature counts differ: about 35 consensus features against 425–1,024 for the baselines. C(τ) counts any feature ≥ τ, so more features means more chances.
   - The SAE is *undercomplete*: M = 425 < d = 512, trained for 3,000 steps.
   - The 0.273 and 0.217 values come from a rule changed after looking at the results, on rep 0 only.

   A reviewer would say "untuned SAE".
4. **Gemini's Fig. 3 claim contradicts our data.** It says acquisition shortcuts "monopolise" SAE features, but our shortcut share is 0.01.
5. **The pathology labels are circular.** Steatosis, osteopenia and emphysema are defined by HU thresholds, so "HU beats FM" on them proves nothing.
6. **Fig. 4B is not possible in one week.** It needs internal Heart CTA data, which requires ethics approval. Fig. 4A (DINOv3) needs the Hugging Face licence and GPU time at 210 MHz.
7. **We have now looked at all 150 dev scans many times.** Any headline claim needs a frozen plan and a held-out run. The 555 confirmation IDs are untouched.
8. **"Refutes Wesp et al."** cannot be claimed without replicating their setup.

## Rules for all new work
- New code goes only in `imgsae/exploratory/p1b_sanity/`. Production `scripts/` and `imgsae/` stay unchanged.
- Each script first reproduces an official number as a sanity row (as in p1_checks).
- Every deviation and decision goes into `docs/EXECUTION_LOG.md`. `STATUS.md` is kept current.
- One GPU job at a time. CPU jobs can run alongside it.

## Step 0 — save the plan (5 min)
- Copy this plan to `docs/SANITY_PLAN_v1.md`.
- Add a "Phase 1b: sanity-check pivot" entry to `docs/EXECUTION_LOG.md`.
- Update `STATUS.md`.

## Stage A — exploratory, dev data only (≈ 1 day wall, mostly unattended)

### A0. Novelty check (30 min, while jobs run)
Search the web for prior work and write the result to `p1b_sanity/NOVELTY.md`:
- random-init CNN baselines in medical imaging;
- CT foundation models vs radiomics baselines;
- SAE evaluations on CT-FM, Merlin and DINOv3 (Wesp; MedConcept 2604.11868; Sparse Concept Channels 2607.20993).

### A1. Probe ladder (`a1_probe_ladder.py`, CPU, ~3–4 h)
**Reused code:**
- `p1_probe.oof_proba` and `p1_probe.boot_auc` (same probe and bootstrap);
- `p1_assemble.prep`;
- the ref/pos rebuild from `data/p1/scans/*.npz` and `Z_COLS`, as in `c2_probe_position.py`.

**Feature sets.** All label-free except "run":

| Set | Contents | Features |
|---|---|---|
| R0 | HU statistics (histogram, mean, SD) | 24 |
| R1 | + texture | 28 |
| R2 | + 48 mm context | 56 |
| R3 | + x/y body coordinates | 74 |
| R4 | + scan-relative z (from `gidx` and body extent) | 83 |
| run | as run, with z from the vertebra masks (leaky; shown for reference only) | 83 |

The encoders are probed in four ways:
- CT-FM (512);
- random-init CT-FM (512);
- random-init + R3;
- CT-FM + R3. This last one is the incremental test: does the FM add anything to the reference?

**Tasks:**
- **T1 — group concepts, clean tokens.**
  - (a) The uniform 60 k sample: the sanity row must reproduce `gates.json`.
  - (b) A concept-stratified sample: ≤ 2,000 tokens per concept and 20,000 'other'. This fixes the small-N problem found in c3.
- **T2 — boundary tokens.** Tokens with label −2 whose maximum group occupancy is ≥ 0.5, labelled by that group.
- **T3 — fine-grained leaf tasks.** Each task uses tokens where the dominant leaf has occupancy ≥ 0.5. A class is kept if it has ≥ 10 patients. Tasks: vertebra level, rib index, lung lobe, and left vs right for paired structures.
- **T4 — few labels.** Probes are trained on 3, 10, 30 or all training-fold patients (3 draws) and tested on held-out-fold patients, for T1(b) and T3.

**Output:**
- per concept, the AUROC with patient-cluster bootstrap CIs;
- Δ(CT-FM − best label-free ref);
- Δ(CT-FM − random-init);
- Δ(CT-FM+R3 − R3).

Results go to `results/a1_*.json`.

### A2. SAE adequacy and size sweep (`a2_sae_audit.py`, GPU, ~2 h; runs in parallel with A1)
**Setup.** Rep-0 halves (`p1_fit.halves`, `eval_rows`).

**Run config** (M 425, k 27, 3,000 steps). Report:
- reconstruction R² on held-out tokens (`sae.recon_r2`);
- dead share (`sae.alive`);
- L0;
- R1 between halves (`sae.act_match`);
- R1 within a half (2 seeds). This separates seed noise from data noise.

**Sweep:**
- grid M ∈ {425, 1024, 2048} × k ∈ {6, 27} at 3,000 steps;
- also 12,000 steps for M = 1024;
- a 5-fit consensus at the best config only.

Every config is scored with `p1_fit.feature_table` under both chimera rules (reusing `c1b_chimera_other.chimera_both`).

### A3. Fair decomposition comparison (`a3_decomp_fair.py`, CPU + GPU, ~3 h, after A2)
**Setup:**
- reps 0–2, both chimera rules;
- `p1_fit.Model`, `feature_table`, `load_perturb` and `ladder.coverage_curve`.

**Methods:**
- soft k-means, raw sparse and sparse varimax at **matched L0 ∈ {6, 27}**;
- the SAE at the run config and at the best A2 config;
- **new:** soft k-means and raw sparse on `X_ref` (no FM) and on `X_null` (untrained FM).

**Metrics.** Areas are reported raw and **feature-count matched**: random subsets of 425 features, 20 draws.

### A4. Read-out (`a4_summarize.py` → `p1b_sanity/README.md`)
The reading rules are fixed now, before any results:
- **R-sat (benchmark saturated).** On T1(b), the medians for CT-FM, random-init and R3 are all ≥ 0.97, and |CT-FM − R3| ≤ 0.01.
- **R-fm (FM adds on harder tasks).** In T2, T3 or T4, CT-FM beats the best label-free reference by ΔAUROC ≥ 0.05 (lower CI > 0) on ≥ 1/3 of classes. It must *also* beat random-init by the same margin; otherwise the gain comes from the architecture, not the pretraining.
- **R-sae (simple beats SAE).** The best simple baseline is above the best SAE config in all 3 reps, under both chimera rules, at matched L0 and feature count. If not, the claim is dropped.

How the outcomes map to papers:

| Outcome | Paper |
|---|---|
| R-sat and not R-fm and R-sae | Gemini's double sanity check (with ceiling wording) |
| R-sat and R-fm | "Organ probes are saturated; harder probes show where FMs help" |
| not R-sae | No SAE-vs-clustering claim |

**STOP here.** I report the results and you choose the framing.

## Later stages (each one only after you say go)
- **B. Frozen protocol.** `docs/SANITY_PROTOCOL_v1.md` fixes the tasks, feature sets, sampling, the primary chimera rule, the SAE configs, the decision rules and N. Zenodo registration is your call.
- **C. Held-out confirmation.**
  - 150 scans from `data/p2_conf_ids.txt`, picked by seed and the same stratification as `p1_select.py`. The other 405 stay sealed.
  - Fetch: about 1 h.
  - Encodes: CT-FM + null, about 10 h overnight; perturbations on 20 scans, about 4.7 h.
  - Then `p1_assemble` with `IMGSAE_P1=data/c1`, and the frozen A1–A3 run once.
  - Disk: about 20 GB of 136 GB free.
- **D. Optional DINOv3 2D arm.** Needs your HF licence. Time is estimated from a 2-scan benchmark first.
- **E. Write-up.** Figures and manuscript. A realistic timeline is 2–3 weeks to a preprint, not 1.

## Verification
- **Sanity rows.** A1 T1(a) reproduces `gates.json` exactly. A3 "orig" areas reproduce `fit/summary.json` and the c1b "neutral" values for rep 0. A2 at the run config reproduces the run's sae_single R1 (0.04) to within seed tolerance.
- **Smoke run first.** Each script gets `--quick` (5 k tokens, 1 fold, 1 rep) before the full run.
- **Logs and results.** Logs go to `p1b_sanity/logs/`. The JSON results are what the README tables are built from, with no hand-copied numbers.
