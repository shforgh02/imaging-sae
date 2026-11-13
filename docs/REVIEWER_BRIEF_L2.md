# Brief for the external reviewer: Lung L2 (feature-level audit of Sybil)

Repository: `github.com/shforgh02/imaging-sae`, branch `prostate-mri-plan`. Everything you need is in the repository. Raw activations and scan metadata are kept on the project PC (too large for git); every summary you need is committed as JSON, CSV or Markdown.

## What the study is
Sybil is a public lung cancer risk model for low-dose CT. On its own NLST test split, it matches a simple model of the radiologists' recorded findings (L1, done: `imgsae/exploratory/lung_l1/RESULTS_L1.md`). L2 asks what Sybil's score is made of, why it is wrong, and whether its internal features can be used. Discovery happens on Sybil's dev split. Confirmation happens once on the test split, under hypotheses frozen in advance.

## Your role
You are the second reviewer named in the protocol (section 10). Your main task comes at step S5: before any test-split activation is extracted, check the frozen hypothesis file. You may also comment on the protocol now; comments before S5 are welcome and will be logged.

## Read, in this order
1. `docs/LUNG_L2_PROTOCOL.md`: the fixed rules (questions, data roles, saves, pass marks, analyses, gates, budget, what is not allowed). Section 1 lists the changes from the plan.
2. `docs/PLAN_SYBIL_AUDIT_v1.md`: the plan the protocol executes.
3. `imgsae/exploratory/lung_l1/RESULTS_L1.md` and `imgsae/exploratory/lung_l1/posthoc/`: what has already been seen on the test split. The post hoc numbers there were computed on test. They cannot be "confirmed" on test (protocol rule C10).
4. `docs/EXECUTION_LOG.md`, entries from 2026-11-13 on: every decision, deviation and result, in order.
5. At S5: `imgsae/exploratory/lung_l2/HYPOTHESES_L2.md`, its frozen-thresholds JSON, the frozen analysis script, and the dev evidence files it cites (`imgsae/exploratory/lung_l2/results/s4_*`).

## What to check at S5 (please answer each with yes / no / comment)
1. **At most five hypotheses.** Each states its statistic, population (exams, horizon), direction, margin, null value and test.
2. **Dev only.** Each hypothesis and every threshold comes from dev results that are committed before the freeze commit. Check with `git log` that no test-split activation file, test image measure or new test outcome analysis appears before the freeze. Test rows can be recognised by the `root` value `test` in run files and in `imgsae/exploratory/lung_l2/results/runs/`; the ledger (`imgsae/exploratory/p1b_sanity/cloud/ledger.json`) lists every paid run.
3. **New quantity.** Each hypothesis involves at least one quantity never computed on test: a feature activation, a group contribution, an image measure, a kernel-pair or z-fix change, or a feature-based rule. At most one hypothesis is computable from the L1 test scores and the form alone, and it is labelled "partly seen".
4. **Multiplicity.** Holm correction across the family, one-sided in the stated direction, family-wise α = 0.05; participant bootstrap with 2,000 draws.
5. **Frozen means frozen.** The SHA-256 values in `HYPOTHESES_L2.md` match the committed files (`Get-FileHash` or `sha256sum`). The frozen script reads only the frozen thresholds and dictionaries, and refits nothing on test.
6. **Honest dev evidence.** For each hypothesis, the cited dev numbers are in the committed files and match what `HYPOTHESES_L2.md` says, including the number of exams, participants and cancers. The dev evidence met the gate of protocol section 9.8: right direction, 95% interval excluding the null, and the same sign in both dev halves.
7. **Fair comparisons.** If a feature-based hypothesis is included, the decomposition arm passed all validity marks (section 9.5). The comparison arms used the same number of features and the same selection rule.
8. **Anything else** that would let a reader doubt that the test result is a clean, single confirmation.

## What not to do
- Do not open or analyse test-split data yourself. The lead approves the freeze after your review; only then is test data extracted, and the frozen analysis runs once.

## How to reply
A short note to the lead: one line per item (1 to 8), then any other comment. If an item fails, say which hypothesis and why. The note and the answers to it are logged in `docs/EXECUTION_LOG.md`.
