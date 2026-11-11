# Briefing for reviewers (2026-11-10): from CT organs to prostate MRI

> **Update 2026-11-11:** the prostate MRI plan below has since been run up to M1, and its gate failed. The project is paused while we look for a better clinical question. See [`PAUSE_NOTE_2026-11-11.md`](PAUSE_NOTE_2026-11-11.md). This briefing is kept for the CT story and the reasoning behind the MRI plan.

**Please read this first.** It explains what the CT work showed, why we stop it before the confirmation run, and what comes next. It also lists what we would like you to review. Every number here comes from the committed result files; links are at the end.

## 1. In short
- **The project's goal is a clinical finding.** We want sparse autoencoder (SAE) features of an imaging foundation model that mark disease, starting with prostate cancer on MRI.
- **The CT work was the test bench for the method.** It used CT-FM on TotalSegmentator, normal organs, and 150 development scans. It worked: we now have a tuned SAE, fair baselines, and checks for stability, reproducibility and shortcuts.
- **We do not run the CT confirmation on the 555 sealed scans.** Normal-organ features have no clinical use, and this dataset has no tumour outlines.
- **Next is prostate MRI (PI-CAI).** The plan is in `docs/PLAN_PROSTATE_MRI_v1.md`. Nothing has been run or downloaded for it yet. **This plan is what we ask you to review.**

## 2. What the CT work showed (exploratory, 150 dev scans)
| Step | Result |
|---|---|
| Phase 1 (pre-registered, lean plan v1) | **NO-GO**, caused by design faults, not by the SAE: the chimera rule counted 'other' tissue as foreign, the SAE size rule was too dense, and gate S ran on organs that simple features already saturate (`DECISION_MEMO_P1.md`) |
| Stage A (diagnostics) | The faults were fixed one at a time; a tuned SAE (M 1,024, k 6, 12,000 steps) works |
| Stage 1a (protocol fixed before running, gate G1) | **G1 passed.** The supervised reference covers 21.7 of 32 organ concepts |

**Fair result, after the colleague review.** Comparing like for like, the single SAE beats the best equally tuned single baseline (k-means, ICA, dictionary learning, raw channels, varimax) in coverage area:
- **+0.104** overall (+0.090 / +0.122 / +0.100 across the 3 replicates);
- that is about 3 more of the 32 concepts.

**Correction.** We first reported +0.25. That was inflated: the consensus has only about 400 features, so it escaped the 425-feature subsampling that every other method got. Your colleague's review found this; see `REVIEW_PROTOCOL_v2.md` and `RESPONSE_REVIEW_PROTOCOL_v2.md`.

**The consensus** (5 SAE fits) keeps the coverage (+0.019 at all features) with about 39% of the features, and it is more reproducible (R1 0.51 vs 0.20).

**Where the SAE wins:** mainly stability, because its features survive a half-token shift. Against ICA it is also reproducibility: median twin score 0.55 vs 0.19 (wording corrected after the review of the MRI plan).
- Area using selectivity and stability only: 0.79, against 0.52 for k-means and 0.54 for ICA.
- On selectivity alone it is only a bit ahead: 0.89 vs 0.83 and 0.81.

**Beyond physics:** small. An SAE on simple HU, texture and position features is nearly as good on organs: CT-FM is ahead by only +0.044.

**Single-feature probing:** no SAE advantage on vertebral level or lung lobes (−0.007 and −0.040 against the best baseline).

## 3. Why we stop the CT work
1. **Organ identity in normal CT is not a clinical question.** Simple HU + position already recognises organs: probe AUROC 0.997, against 0.999 for CT-FM.
2. **TotalSegmentator has no tumour outlines.** It has only a scan-level "tumor" tag (32 of 150 dev scans, 136 of 555 sealed), at many different body sites. We checked the metadata only; no sealed scan was opened.
   - CT-FM's scan-level tumour probe was at chance in Phase 1: 0.53, against 0.70 for simple HU features.
   - Kidney cysts, the only lesions with masks, occur in 5 dev patients.
   - So no tumour feature can be found or checked here.
3. **A confirmation would cost about $16 and 1–2 weeks,** and it would mainly confirm a methods result that is not the project's goal.

**What is kept:**
- the 555 scans stay sealed and unused;
- the CT confirmation protocol (revision 2, `SAE_PROTOCOL_v2.md`) is archived, not registered;
- the Stage 1a results serve as method evidence;
- all the code carries over to MRI.

## 4. The prostate MRI plan in short
**Question.** Does a foundation model's prostate MRI, split into SAE features, contain features that:
1. mark clinically significant cancer;
2. are stable, and not scanner or hospital shortcuts;
3. add information beyond PSA density, age, prostate volume and the radiologist's PI-RADS;
4. radiologists recognise?

**Data:**
- PI-CAI public set: 1,500 MRI studies, 1,476 patients, 3 centres.
- Expert outlines exist for all 425 cancers, and the clinical sheet includes PI-RADS.
- It is downloaded fresh from the original sources. An existing preprocessed copy from another project is not used: its intensities are normalised, it lacks one sequence, and it contains another model's output.
- Split 50/50 by patient; one half is sealed.

**Models:**
- **ProFound,** a 3D prostate MRI model. It saw the PI-CAI images during self-supervised pretraining, but no labels. That is allowed with disclosure, but needs an external test cohort.
- **MRI-CORE,** a general MRI model trained on Duke data only. It never saw PI-CAI.
- **SAM ViT-B,** MRI-CORE's natural-image starting point. It is the comparison that shows what MRI training adds.
- **DINOv3** was dropped: Meta rejected the access request. **Triad** is the fallback if ProFound cannot be used.
- See plan revision 3, §3.1 (two-level leak rule).

**Stages.** Each has a gate fixed before it runs:

| Stage | What | Gate |
|---|---|---|
| M0 | Download, split, preprocessing, visual check of 20 cases | Counts and quality match |
| M1 | Does the model know cancer? Token-level probes against simple T2, ADC and HBV intensity features | The model must beat them by ≥ 0.03 AUROC, otherwise stop early |
| M2 | SAE + fair baselines; lesion features | ≥ 1 valid lesion feature: held-out AUROC ≥ 0.80, stable, reproducible, not a shortcut, and adds over the intensity features |
| M3 | Clinical value in the **biopsy cohort** (PI-RADS ≥ 3, biopsied: 884 studies, 53% without csPCa) | Increment over PSA density + age + volume + PI-RADS, lower CI > 0, and non-inferior to same-capacity intensity and texture scores (plan revision 2) |
| M4 | Radiologists name the features | When readers are available |
| M5 | Registered confirmation on the sealed half, run once | Holm over the claims |

**Not claimed:** AI benchmark accuracy. The PI-CAI organisers note that the public set is convenience-sampled.

**Cost:** about $4 for M0–M1 (caps $6.60). The whole plan takes about 3–5 weeks.

## 5. What we would like you to review
1. **The M1 gate.** Is "beat the intensity reference by ≥ 0.03 AUROC at token level" the right go/no-go? Is the reference fair: T2W, ADC and HBV histograms, mean ADC, 3 × 3 context, position in the gland?
2. **The M2 validity rule for a lesion feature:** held-out AUROC ≥ 0.80, r_pert ≥ 0.70, twin score ≥ 0.70, shortcut AUROC < 0.80, and ≥ 0.02 over the reference. Too strict, or too loose?
3. **M3 clinical models:** the endpoint (csPCa, ISUP ≥ 2), the baselines (PSAD + age + volume; then + PI-RADS), and the rule for missing PI-RADS.
4. **Encoders:** is the two-level leak rule right (label exposure excludes; image exposure is disclosed and needs an external test)? Is there any other MRI foundation model we should test in M1?
5. **Preprocessing:** token size, crop size, intensity scaling, and the MRI perturbations used for stability.
6. **External validation later:** which cohort, given that ProstateX overlaps PI-CAI?
7. **Anything we missed,** especially any comparison that is not like for like (§2 shows why we now check this).

Comments are welcome directly on the pull request for branch `prostate-mri-plan`.

## 6. Document map
| Document | What |
|---|---|
| [PLAN_PROSTATE_MRI_v1.md](PLAN_PROSTATE_MRI_v1.md) | **The plan to review** |
| [../STATUS.md](../STATUS.md) | Current state |
| [EXECUTION_LOG.md](EXECUTION_LOG.md) | Every decision and deviation, in order |
| [IMAGING_SAE_LEAN_v1.md](IMAGING_SAE_LEAN_v1.md), [DECISION_MEMO_P1.md](DECISION_MEMO_P1.md) | Original plan; Phase 1 verdict |
| [SANITY_PLAN_v1.md](SANITY_PLAN_v1.md), [SAE_v2_REVIEW_PACKET.md](SAE_v2_REVIEW_PACKET.md) | Stage A plan; plan v2 review packet |
| [REVIEW_AND_PROPOSAL_v2.md](REVIEW_AND_PROPOSAL_v2.md), [STAGE1A_PROTOCOL.md](STAGE1A_PROTOCOL.md) | Review of plan v2; Stage 1a protocol |
| [../imgsae/exploratory/v2_ct/RESULTS_S1A.md](../imgsae/exploratory/v2_ct/RESULTS_S1A.md) | Stage 1a results (G1 as read; see the correction above) |
| [SAE_PROTOCOL_v2.md](SAE_PROTOCOL_v2.md) | CT confirmation protocol, revision 2 (archived, not registered) |
| [REVIEW_PROTOCOL_v2.md](REVIEW_PROTOCOL_v2.md), [RESPONSE_REVIEW_PROTOCOL_v2.md](RESPONSE_REVIEW_PROTOCOL_v2.md) | Colleague review of the CT protocol, and our reply with the recomputation |
