# Step R: can we rescue the feature extraction? (dev only, exploratory)

**Who and when:** the reviewer session (Fable 5.2), 2026-11-16, on the lead's instruction ("before I give anything to Opus, can you yourself test various methods? see if we can rescue extraction").
**Status of this work:** discovery on dev. No test data. No cloud. No money. No frozen file is changed (`results/s5/`, `HYPOTHESES_L2.md`, all `s4_*`, `s5_*`, `s6_*` scripts are untouched). New files only: `r1_arms.py`, `r2_shared.py`, `results/r/`, this file.
**Note on independence:** I was the reviewer of the first freeze. From here I also did analysis work. If anything of step R enters the new freeze, the re-check (N2) must say so, and the lead may want a different reviewer for that part.

## The question
In S4 only "raw units" passed all four validity marks. The SAE, PCA, ICA, NMF and k-means failed. Is that the fault of our settings (layer, number of features K, sparsity k, per-member fitting), or of Sybil itself?

## Plan (fixed before any run on all dev; commit "R plan and code")
The marks are the same as S4 (protocol 9.5), from the same code (`s4_core.py`, `s4_decomp.py`, imported, not changed):
- **V1** function kept: logits from the rebuilt vector correlate ≥ 0.98 with Sybil's own, AUROC change ≤ 0.005.
- **V2** seed stability. (Scouting simplification: members 0 and 1 only. S4 used all five. V2 was never the problem.)
- **V3** at least K/4 families found in ≥ 3 of the 5 members.
- **V4** naming repeats in the two halves (≥ 0.70 both ways).
- New, descriptive only: **how many families are not copies of the risk score** (|r| with ℓ̄_6 below 0.5). In S4 the 56 raw-unit families were mostly copies of one risk axis.

| Step | What is tested | Why | Script |
|---|---|---|---|
| R1 | **Shared axes** of the five members (multiset CCA), layers `h` and `pooled`; shuffle null; function kept; stability between halves; naming | A method made for a small dense space where each member has its own directions | `r2_shared.py` |
| R2 | **SAE less sparse** on `h`: K = 64 with k = 8, 16, 32 active (S4: k = 4) | Did the SAE fail V1 only because k was too small? | `r1_arms.py --sae-k` |
| R3 | **Smaller K** on `h`: K = 8 and 16, all six arms (SAE with k = K/4 and K/2) | `h` has about 5 to 7 real dimensions; K = 64 may ask for too many features | `r1_arms.py --K` |
| R4 | **Earlier layer** `pooled` (1,536 numbers): six arms, K = 64 and 16 (SAE with k = K/16 and K/4) | `pooled` has more shared directions (about 14 against 6) | `r1_arms.py --layer pooled` |
| R5 | Only if R1 to R4 give axes or families that are stable, named and not copies of the risk score: their change under z-fix and kernel change | The audit use of a feature | new script, written after R1 to R4 |

**Rules:** every run is reported, also the failed ones. No setting is added after seeing results without a logged note. A result of step R can become a hypothesis only under the four conditions in `docs/HANDOVER_PROMPT_L2_N1.md` (gate 9.8, random-choice test, no refit on test, honest chance ≥ 0.5).

**Code checks before the full runs:** both scripts run on a part of dev (600 and 1,500 exams) without error; `r1_arms.py` must reproduce the S4 numbers for `h`, K = 64, arms raw and PCA (table below).

## Results
(filled step by step; each step is one commit)
