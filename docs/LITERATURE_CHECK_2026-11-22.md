# Literature and guideline check (task 6), 22 November 2026

**In simple words.** Neon (Gemini 4 Neon, read-only, web search) checked all 40 references of `LITERATURE_TABLE_R3.md` and 13 more papers the project relies on. I then checked Neon's most important corrections myself in primary sources: PubMed records, publisher abstracts, the official checklists and the guideline PDFs themselves. **6 references were wrong and are now corrected** in `LITERATURE_TABLE_R3.md` (marked "corrected 22 Nov"). **The three guideline sentences we quote are now checked word for word in the original documents** (before, we had search excerpts only). Both reporting checklists (TRIPOD+AI, CLAIM 2024) were read from the official sources; the item-by-item map to this project is in `docs/CHECKLISTS_TRIPOD_AI_CLAIM.md`.

Neon's full report: `<scratchpad>/gemini_review/gemini_task6_report.txt`. No name, email or project name was sent in any query.

## 1. References that were wrong (now corrected in the table)

| # | What was wrong | Correct | Checked by me in |
|---|---|---|---|
| 1 | Author order: Barzilay, Sequist, Fintelmann listed 4th to 6th | Mikhael PG, Wohlwend J, Yala A, Karstens L, Xiang J, Takigami AK, … Sequist LV, Fintelmann FJ, Barzilay R (17 authors) | author list of the JCO 2023 paper |
| 4 | Wrong PMID (40081014 is a physics review by Pimenta and Costa) and a changed title | PMID 41833807; title "Integrating Deep Learning of Low-Dose CT Imaging With Clinical Data for Lung Cancer Risk Prediction"; *Chest* 2026;170(3):962–974; 14 authors, last Hung RJ | PubMed records of both PMIDs; DOI search |
| 5 | 13 of 21 authors dropped without "et al."; numbers mixed with an earlier conference abstract | Pasquinelli MM, Durney CH, Hill T, … Weinberg F (21 authors); PMID 42805462; 5,883 LDCTs, 3,177 participants (2014–2025), 64.9% Black, 105 cancers; baseline AUROC 0.91 at 1 year to 0.82 at 6 years, similar in Black and non-Black people | PubMed abstract |
| 18 | Called a "4-stage" framework with invented stage names | Framework: consider possible errors in the clinical task, map the parts that can cause them, foresee their consequences; tests: exploratory error analysis, subgroup testing, adversarial testing; joint responsibility of users and developers; adapted from internal algorithmic auditing (Raji et al.) | PubMed abstract (PMID 35396183). The stage names (scoping, mapping, artefact collection, testing, reflection) are Neon's reading and **not verified** by me (full text blocked, 403) |
| 22 | Claim not supported: the paper is not about site or scanner confounders | Models that predict molecular biomarkers from histology learn confounded signals: co-dependent biomarkers and routine pathology features (for example tumour grade) carry much of the accuracy, which varies with them (shortcut learning) | Oxford and Warwick pages, news coverage of the paper, DOI |
| 38 | Placeholder authors and a short title | Wang AJ, Tushar FI, Harowicz MR, Tong BC, Lafata KJ, Tailor TD, Lo JY. "The Duke Lung Cancer Screening (DLCS) Dataset: A Reference Dataset of Annotated Low-Dose Screening Thoracic CT." *Radiol Artif Intell* 2025;7(4):e240248 | Duke Scholars and CVIT pages |

## 2. To qualify or complete before submission (not wrong, but imprecise)

| # | Fix |
|---|---|
| 2 | Add 60(5):311–318; the study also compared 1.25 vs 2.5 mm |
| 3 | The subgroup AUROCs (0.94 / 0.70 heavy smokers; 0.89 / 0.56 never or light smokers) are for **visible** vs **future** cancers, not simply 1 vs 6 years; check the Lung-RADS-matched wording in the full text before quoting it |
| 7, 9 | Add the exact abstract and proceedings numbers (*Cancer Res* 86(7 Suppl) abstract 6727; SPIE Vol. 14519, paper 14519-29, no DOI yet) |
| 8, 32, 33 | Mark as non-peer-reviewed preprints |
| 19 | Remove "metadata": the race signal came from the pixels (metadata removed) |
| 31 | Published at ICLR 2025 |
| 35, 36 | Cite the secondary annotation datasets separately if used (Renoust et al. 2026; Fedorov et al. 2018) |
| 10–17, 20, 21, 26, 27, 37, 39 | Add volume and article numbers (Neon's list) |

Every other reference: verified by Neon at abstract level (exists, authors, title, journal, year, DOI, claim).

## 3. Guideline sentences, checked word for word in the original documents

| Guideline | Exact wording | Where |
|---|---|---|
| **QIBA**, Small Lung Nodule Volume Assessment and Monitoring in Low Dose CT Screening, Clinically Feasible Profile (19 Dec 2023) | "The Reconstruction Interval should be either contiguous or overlapping (i.e., with an interval that is less than the reconstructed slice thickness). Either method will be consistent with the Profile Claims, though overlap of 50% may provide better accuracy and precision compared to contiguous slice reconstruction (37). Reconstructing datasets with overlap will increase the number of images and may slow down throughput, increase reading time, and increase storage requirements, but has NO effect on radiation exposure. A reconstruction interval that results in gaps between slices is unacceptable as it may "truncate" the spatial extent of the nodule, degrade the identification of nodule boundaries, and confound the precision of measurement for total nodule volumes." | page 25, lines 561–568 (sentence ends on page 26); PDF from qibawiki.rsna.org (images/c/c2/…2023Dec19.pdf) |
| **ACR–STR** Practice Parameter for the Performance and Reporting of Lung Cancer Screening Thoracic CT (revised 2024, Resolution 27) | "The study must include axial images from the lung apices to the costophrenic sulci acquired and viewed at 2.5-mm slice thickness or smaller (preferably at 1.0-mm slice thickness or smaller), with reconstruction intervals equal to or less than the slice thickness [53]." Ref. 53 = Jankowski A, Martinelli T, Timsit JF, et al. *Eur Radiol* 2007;17:3148–56 | page 3; PDF from gravitas.acr.org (DownloadPreviewDocument?DocId=38) |
| **ESTI**, Chest CT for Lung Cancer Screening – Technical Standards | "Reconstructed image width (nominal width of reconstructed image along z-axis): ≤ 1.00 mm; Preferably 0.75 mm or smaller; In very obese 1.25 mm may be necessary". "Slice Interval: ≤ slice width; maximum 0.7 mm; Overlapping reconstructions are not mandatory" | page 3 (table); the date 2019-06-14 is in the file name only, not printed in the document (the table also mentions deep-learning reconstruction, so the file may have been updated after 2019; cite the URL and the access date) |

**What this means for the paper.** All three guidelines allow or recommend overlapping reconstruction (QIBA: 50% overlap may be better; ACR–STR: interval ≤ thickness; ESTI: interval ≤ width, overlap not mandatory). So overlapping series are guideline-conformant input, and a model that mis-reads them is a deployment risk, not an input error of the site.

## 4. Reporting checklists (official sources read)

- **TRIPOD+AI** (Collins et al., *BMJ* 2024;385:e078378): 27 items, 52 sub-items; read from the official full text (PMC11019967, Table 2).
- **CLAIM 2024** (Tejani et al., *Radiol Artif Intell* 2024;6(4):e240300): 44 items; read from the official RSNA checklist page (rsna.github.io/claim/checklist.html). The per-item explanations are in a 2026 elaboration article (*Radiol Artif Intell* 2026;8:e260835), not yet read.
- Item-by-item map to this project: `docs/CHECKLISTS_TRIPOD_AI_CLAIM.md`.
