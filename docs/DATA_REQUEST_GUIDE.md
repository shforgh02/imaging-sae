# How to get more data (and whether to add more models): a step-by-step guide for the lead

- **Written:** 2026-11-18, after the test results (`imgsae/exploratory/lung_l2/RESULTS_L2.md`).
- **Who does what:** every request below must be sent **by the lead**, with the lead's own name and email. No agent sends a request or puts the lead's name into an outside service.
- **Rule before any new data is opened:** when access is granted, we first write and freeze the hypotheses for the new data (as for NLST), the lead gives an OK, and only then the data are downloaded. This keeps the new data a true test.

## 1. Which data, in which order
| Priority | Data | What it adds to the paper | What you must do | Cost |
|---|---|---|---|---|
| **1 (do now)** | **Duke Lung Cancer Screening (DLCS)**, Zenodo, 3 parts | an outside, modern clinical screening cohort (Duke, 2015 to 2021): 1,613 CTs, **144 cancer patients** confirmed by pathology and follow-up, **the radiologists' Lung-RADS category**, smoking status. Tests: is the slice-spacing problem there too (modern scanners), and does Sybil add to Lung-RADS? | a free Zenodo account and 3 online request forms | free to request; scoring about $4 to $6 in the cloud (needs a new budget line, see 4) |
| 2 (if you have an institution) | **Full NLST clinical data** through NCI CDAS | the variables the public NLST package lacks (for example family history and smoking pack-years), so we can add the two standard risk models (Brock for nodules, PLCOm2012 for smoking history) as comparators on the same test set | a CDAS project with a **Principal Investigator and a Signing Official of an institution**; NCI review, 1 to 4 weeks | free; analysis on the PC |
| 3 (optional) | **Pamplona P-ELCAP ("Lung Ambition")**, Zenodo | a small European cohort (about 211 people, 67 cancers, case-control, with proteomics) | access "upon the signing of the institutional agreement" (project page) | free to request; small |

Not useful as an outside test: LUNA25 (it is made from NLST), LIDC-IDRI (no cancer outcomes).

## 2. DLCS, step by step
1. **Make a Zenodo account:** go to https://zenodo.org and choose "Sign up". Use your **university or work email** if you have one (owners trust it more), or sign in with ORCID. Confirm the email.
2. **Open the three records** (each part has its own request form):
   - Part 1 (subsets 1 to 7, metadata, annotations): https://zenodo.org/records/13799069
   - Part 2 (subsets 8 and 9, CT image information): https://zenodo.org/records/12784601
   - Part 3 (subset 10): https://zenodo.org/records/14659131
3. **Log in**, scroll down to "Request access". Read the conditions shown there. If they ask for something not listed here (for example a signed agreement or an institutional email), tell me before you send.
4. **Fill in the form:** your full name, your email, and the message below (change the parts in [brackets]). Tick the box that you accept the conditions.
5. **Send the same request for Parts 1, 2 and 3.**
6. **Wait for the email** from Zenodo. If nothing comes in 2 weeks, write to the dataset team: cvit-inquire@duke.edu (same text, short).
7. **When access is granted: do not download anything.** Tell me. I will (a) read the metadata file first (to check that the scans keep the slice spacing and thickness we need), (b) write the frozen plan for DLCS for your OK, and (c) download the scans **directly in the cloud** (the laptop's upload is too slow, and the data do not need to be on the laptop).

**Message to paste (change the brackets):**
> Dear DLCS team,
> I am [full name], [position, for example "independent researcher" or "PhD student"] at [institution, or "no institution"]. I would like to request access to the Duke Lung Cancer Screening dataset (Parts 1 to 3) for non-commercial academic research.
> Purpose: an independent external evaluation of a published open-source lung-cancer risk model (Sybil; Mikhael et al., J Clin Oncol 2023). We study how the model's output depends on CT reconstruction geometry (slice spacing and slice thickness) and how much it adds to the radiologists' Lung-RADS assessment. The analyses were pre-specified and tested on the public NLST data; we want to repeat them on an independent clinical cohort.
> Use of the data: research only; no commercial use; no redistribution of the data or of images derived from them; no attempt to identify any person. The data will be processed in a private, access-controlled cloud computing account and on a password-protected computer, used only by me [and named collaborators], and deleted at the end of the project. Results will be reported only in aggregate, and every publication will cite the DLCS paper (Radiology: Artificial Intelligence, doi 10.1148/ryai.240248) and the Zenodo records, following the CC BY-NC-ND 4.0 licence.
> Thank you for considering this request.
> [full name], [email]

Be honest in the form: the text says the data will be processed in the cloud, because they will be.

## 3. Full NLST data through CDAS (only if you have an institution)
1. Go to https://cdas.cancer.gov and read "NLST", then "Instructions".
2. Create an account. Start a **new NLST project**, type **"Data-Only"**.
3. You must name your **institution**, a **Principal Investigator** (PI; can be you if your institution allows it), a **Signing Official** (a person at the institution's research office who signs agreements) and the project staff.
4. Describe the project (the same purpose as above), and ask for: the participant dataset (demographics, smoking, family history, medical history), the CT abnormality datasets, and the lung cancer dataset.
5. The PI submits; NCI reviews (1 to 4 weeks); then the **Data Transfer and Use Agreement** is signed and the data are delivered (CSV or SAS).
6. Tell me when it arrives. Everything after that runs free on the PC, and is labelled exploratory (the NLST test is already open).

## 4. Money for the outside dataset
- After the NLST test the project has **$66.36 of $72** used and the task `lung_l2_audit` **$40.97 of $45**. Scoring DLCS (about 1,613 scans, plus the z-fix variants of the stretched ones) costs about $4 to $6. **It needs your OK for a new budget line** (for example a new task of $8 and a higher project cap). The monthly free credit of each account renews on 1 December.

## 5. Should we add more AI models (for example Google's)?
**Short answer: not now. The outside dataset gives much more impact than a second model.**
| Model | Available? | Worth it? |
|---|---|---|
| Google's NLST model (Ardila et al., *Nat Med* 2019) | **No.** Code and weights were never released (Sybil's authors could not compare with it either). | not possible |
| LungEvaty (2025, a transformer from one CT; weights on Hugging Face after accepting conditions; the authors compare with Sybil on Sybil's test split) | Yes, with conditions | **Maybe later.** It would show whether "no added value beyond the radiologists' findings" holds for a second model. It needs a new full NLST test extraction (about $10 to $20) and its own frozen plan. First check its licence and that it never trained on Sybil's test people. |
| Older open models (for example the 2017 Kaggle winner) | code public | **No.** Its training data may overlap with NLST; a reviewer would not trust it. |
| General "foundation" CT models | yes | **No.** They must be trained for the task first, so they are not a fair comparison with a ready model. |

**Why not now:**
1. The slice-spacing problem is a **bug in Sybil's own code** (it uses the thickness instead of the true spacing). For another model, first read its code (free). If it uses the true spacing, the problem does not apply, and one sentence in the paper says so.
2. Reviewers and clinical journals value **an independent external cohort, frozen hypotheses and a clinical co-author** more than a longer list of models.

## 6. The best high-impact path (my recommendation)
1. **Today:** send the three DLCS requests (section 2). If you have an institution, also start the CDAS project (section 3).
2. **This week:** find a clinical co-author, ideally a chest radiologist. The paper's message is clinical (thresholds, added value, a software bug in a deployed model).
3. **Meanwhile (me, free):** the manuscript draft, the remaining figures and the checklists (TRIPOD+AI, CLAIM), and a polite report of the slice-spacing bug to Sybil's authors (when you decide).
4. **When DLCS access comes:** the frozen DLCS plan (H1, H2, H6 again, plus Sybil against Lung-RADS), your OK, the budget, then one run.
5. **Journal:** with DLCS and a clinical co-author: *The Lancet Digital Health* or *npj Digital Medicine*; without: *Radiology: Artificial Intelligence*.
