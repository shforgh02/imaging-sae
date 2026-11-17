# Project guide: the whole story in simple words, and the plan from here

- **Written:** 2026-11-16, by Fable 5.2, for the lead and for any agent that continues the work.
- **Sources:** `docs/EXECUTION_LOG.md` (every step, in order), `STATUS.md`, the result files named in each part, and the S5 review `docs/REVIEW_S5_L2.md`. Every number here comes from those files.
- **How to use it:**
  - The lead: read parts 1, 2, 6, 7 and 10. They need about 15 minutes.
  - An agent: read parts 3, 7, 8 and 9 before doing anything. Then do the next open step of part 8, and nothing else.
- **Left out on purpose:** the lead's earlier prostate manuscript. The lead handles it elsewhere (rule of 2026-11-13). It is not part of this project.

---

## 1. The project like you are five

**The robot.** There is a robot called **Sybil**. You show it a picture of a person's lungs (a CT scan). It says one number: "how likely is lung cancer". It was built by a famous group and is being tried in hospitals.

**The doctor's notes.** When a doctor looks at the same picture, the doctor writes notes on a form: "there is a lump, it is 9 mm, it has spiky edges". We call these notes **the form**.

**What we wanted.** We wanted to open the robot's head and look at the small parts inside. We hoped to find parts like "this part looks at lumps", "this part looks at damaged lung", "this part is fooled by the scanner machine". Then we wanted to use these parts to make the robot better: fewer false alarms and fewer missed cancers.

**The tool.** The tool for finding small parts is called a **sparse autoencoder (SAE)**. Think of it as a sorting machine: you pour in the robot's thoughts, and it sorts them into small boxes, one idea per box.

**What we found.**
1. **The robot is not smarter than the doctor's notes.** A very simple calculator that only reads the doctor's form is as good as the robot. (This was checked on the robot's own final exam.)
2. **Inside the robot's head there are no small boxes to find.** There is mostly **one big dial**: "risk, low to high". The sorting machine had nothing to sort. So the SAE failed, and the other sorting tools failed too.
3. **The robot looks at a stretched picture.** For about 1 scan in 8, the robot's own program stretches the chest to up to twice its height, and cuts off the top and bottom. When we give it the right picture, its number changes a lot, and about half of its alarms change.
4. **Using the parts to make the robot better did not work** on the practice data. Nothing we tried passed our own rules.

**The rule we never broke.** The data are split like school: a **practice book** (train), **homework** (dev), and a **final exam** (test). We may look at the homework as much as we want. The final exam is opened **once**, and only after we write down, in advance, exactly what we expect. This is what makes a result believable. The exam is still closed.

---

## 2. Your goal, and did we reach it?

**Your goal, in your own words (2026-11-13):** open the model with an SAE or another feature extractor, and find *why it is right, why it is wrong, and whether its features can improve prediction or cut false positives and false negatives*. The end goal is a **high-impact paper**, clinical if possible; a methods paper is "better than nothing".

**Honest score on the homework (dev) data:**

| Part of the goal | Reached? | In one line |
|---|---|---|
| Find features with an SAE | **No** | The SAE and four other tools failed our validity rules. Only the model's own raw units passed, and they are mostly copies of one risk dial. |
| Why is the model right? | **Partly** | Most of its score comes from nodule-type units. Known things (form, age, scanner, lung measures) explain only 31% of the score. |
| Why is it wrong? | **Partly, descriptive** | It misses small-cell, central, stage IV and late cancers. For false alarms we found no clean cause. |
| Use features to improve prediction or cut errors | **No** | Three ways were tried. None passed the gate. |
| Something new and solid | **Yes** | The slice-spacing problem. It was not known before. |

**So you are right: the main goal was not reached on dev.** The final exam cannot rescue it. The exam can only *confirm* what held on dev. It cannot turn a failed idea into a result.

**But the project did not fail.** It produced three things that can be published (part 6 and part 10). What it cannot produce is the paper "our features make the AI better".

---

## 3. Words you need

| Word | Simple meaning |
|---|---|
| **AUROC** | A grade for a risk score. 0.5 = coin flip. 1.0 = perfect. A difference of 0.01 is small. |
| **Feature** | One "idea" inside the model, as a number per scan. |
| **SAE** | Sparse autoencoder: a tool that tries to split a model's inner numbers into separate features. |
| **`h`** | The 512 numbers inside Sybil just before it makes its score. This is what we decomposed. |
| **Logit, ℓ̄** | Sybil's raw score before it is turned into a probability. We use the mean of its five member models. |
| **The form, F** | The radiologist's recorded findings, and the simple model (logistic regression) built on them plus age, sex and smoking. |
| **Train / dev / test** | Practice book / homework / final exam. Sybil learned on train, its authors tuned it on dev, test is untouched. |
| **Gate** | A pass mark written **before** a step runs. If it fails, we stop. |
| **Freeze** | Writing down hypotheses, numbers and code, and locking them with fingerprints (hashes), before the test is opened. |
| **Hypothesis, null, margin** | A claim to test ("more than 5% of flags change"). The null is the line it must beat (5%). |
| **95% interval (CI)** | The range where the true value probably is. Made by bootstrap: re-drawing participants 2,000 times. |
| **Holm** | A rule that makes five tests together as strict as one. |
| **Flag, τ90** | Sybil "raises an alarm" when its 1-year score is above τ90. τ90 is set so that about 10% of people without cancer are flagged. |
| **z-fix** | Our corrected run: the same images, but slices placed at their true distance. |
| **Kernel** | The reconstruction filter of the CT scanner: sharp or soft pictures of the same scan. |
| **Family** | The "same" unit found in at least 3 of Sybil's 5 member models. |
| **Modal** | The paid cloud computer. **Ledger and guard:** our money book and the program that refuses a launch that would pass a limit. |

---

## 4. The story before the lung work (6 to 11 November)

Each stage has the same shape: what we wanted, what we did, what went wrong, the result, what it shows, and the decision.

### Stage 1. CT organs, Phase 1 (6 to 8 Nov). Result: NO-GO
- **Wanted:** show that an SAE finds real, stable features in a CT foundation model (CT-FM), on a public dataset with organ masks (TotalSegmentator: 150 dev scans, 555 sealed scans).
- **Did:** moved the work from the Mac to the Windows laptop; encoded 150 scans; fitted SAEs and simple baselines.
- **Problems:** the laptop's GPU is stuck at 10% speed (a broken power sensor; hardware fault). It costs time only; results were checked to be correct.
- **Result:** gate S **failed**. Zero concepts were "beyond simple intensity" (3 were needed). The SAE did not beat soft k-means.
- **What it shows:** organs are easy. Simple brightness numbers already recognise them at 0.98 or more. A test built on organs cannot show that an SAE is useful.
- **Decision:** NO-GO, as the plan's table said. Memo: `docs/DECISION_MEMO_P1.md`.

### Stage 2. Sanity checks, Phase 1b (9 Nov)
- **Wanted:** find out whether the NO-GO was real or caused by unfair settings.
- **Found:** two unfair settings. The SAE and the baselines ran at different sparsity. And the scoring rule counted "other tissue" (45% of tokens) as a wrong concept, which rejected 79% to 100% of all features.
- **Result:** with fair settings, the best SAE beat the best simple baseline in every repeat (0.39 to 0.40 against 0.25 to 0.27).
- **What it shows:** on this CT data the SAE *method* works. But only on organ recognition, which is not a clinical question.
- **Lesson kept as a rule:** every arm gets the same number of features, the same sparsity and the same tuning effort.

### Stage 3. Stage 1a and the CT confirmation protocol (9 to 10 Nov). Stopped by the lead
- **Did:** a fixed protocol with gate G1. G1 passed. A colleague's review then showed that the gain was inflated: +0.25 as first read, **+0.10** when compared like for like. G1 still passed.
- **Drafted:** a confirmation protocol for the 555 sealed scans.
- **Decision (lead, 10 Nov):** stop. The goal is a clinical finding, not a methods result. This CT data has no tumour masks. The 555 scans stay sealed and unused.
- **Lesson kept as a rule:** recompute every claimed gain from the tables, like for like.

### Stage 4. Prostate MRI, M0 and M1 (10 Nov). Result: gate failed
- **Wanted:** a clinical question: can features of an MRI foundation model find prostate cancer? Data: PI-CAI (1,500 public studies), split in two halves; one half sealed.
- **Did:** fresh download with checksums; three plan reviews by a colleague; checked three encoders. Found and fixed two loader bugs in public code (one model would have run with random weights).
- **Result:** gate M1 **failed**. The frozen MRI models were not better than plain intensity numbers: −0.022 (needed +0.03). AUROC 0.909 against 0.912.
- **What it shows:** these frozen models do not "know" cancer better than brightness does. An SAE cannot find what is not there.
- **Decision:** stop this line. The sealed half (746 studies) is unopened.

### Stage 5. The lead's own prostate model (10 to 11 Nov). Result: too small; PAUSE
- **Asked by the lead:** "can't we simply use my model?"
- **Result:** it adds about **+0.02** AUROC over what the clinic already has (PI-RADS, PSA density, age), and the gain differs a lot between folds.
- **What it shows:** real but too small and too unstable to carry a paper.
- **Decision:** project paused on 11 Nov (`docs/PAUSE_NOTE_2026-11-11.md`). Spend so far $12.86.
- **Lesson kept as a rule:** before any "AI beats the doctor" idea, first fit a plain model on what the doctor already recorded, and compare. Do the free check first.

---

## 5. The lung work (12 to 16 November)

### Stage 6a. Lung L0, free (12 Nov)
- **Why lung:** Sybil is public, its data (NLST) are public, and its train/dev/test split turned out to be public too (an earlier note of mine said it was not; that was wrong and was corrected).
- **Did:** no images. Only the public tables. A simple model on the radiologists' form, tested on Sybil's test participants.
- **Result:** the form scores 0.929 (cancer within 1 year) and 0.745 (within 6 years). Sybil's published numbers are 0.93 and 0.75.
- **What it shows:** maybe Sybil is no better than the doctor's notes. But this was not a paired test.
- **A mistake of mine, corrected the same day:** I first said 11,400 other participants could be a test set. They hold only 34 cancers.

### Stage 6b. Lung L1, paid, on the test split (12 Nov). Cost $12.53
- **Wanted:** the paired test. Run Sybil ourselves on its own test scans, and compare with the form on the same people.
- **Did:** protocol and analysis frozen first. A cheaper agent ran it. 5,412 scans scored. Sybil reproduced its published demo scores exactly.
- **Problems:** two failed start-up runs, a hanging download tool (replaced), a stale file map (re-scored), and the money line stopped the follow-up scans at 3,133 of 4,436.
- **Result:**

| Question | Sybil | The form | Sybil adds to the form |
|---|---|---|---|
| Cancer within 1 year, first scan (41 cancers) | 0.927 | 0.929 | +0.026, interval includes 0 |
| Cancer within 6 years, first scan (131 cancers) | 0.724 | 0.745 | +0.011, interval includes 0 |
| Cancer within 1 year, all scans (72 cancers) | 0.914 | 0.945 | +0.000 |

- **What it shows:** on its own exam, Sybil does not beat a 39-variable model of the doctor's notes. The form adds to Sybil, not the other way. With so few cancers this means "no large gap", not "exactly equal".
- **Why this matters:** this is a finished result **on test data**. It is the strongest thing the project has today.

### Stage 7. Lung L2: opening Sybil (13 to 16 Nov). Cost so far $21.70
The lead's direction of 13 Nov: do not only compare with the radiologist; open the model.

**S0. Reading and protocol (free).**
- **Did:** read Sybil's code and the papers; wrote `docs/LUNG_L2_PROTOCOL.md` with all rules before any data.
- **Found in the code:** Sybil places slices at the *slice thickness*, not at the real distance between slices. In 44% of scans the slices overlap, so the chest gets stretched, up to 2×, and the top and bottom are cut off. Nobody had reported this.
- **Why a protocol first:** so that no result can be chosen after seeing it.

**S1. The list of dev scans (free).**
- **Problem:** the public split lists scan series only for test people. For dev we had to choose a series per exam ourselves.
- **Did:** a rule from scanner metadata only (sharp kernel first, then thinnest slices). On test it picks the same series as the split file in 98.9% of exams. Gate (90%) passed.
- **Result:** 7,336 dev exams, 2,492 people.

**S2. Pilot of 300 scans ($1.96).**
- **Why:** test the whole chain cheaply before spending $20.
- **Result:** all exactness checks passed (we can rebuild Sybil's score from the saved numbers to 6 decimals; a repeat run is identical).
- **Problems:** two checks failed *as I had written them*. One was my error in the check (it did not allow for cut lungs). One was a real scanner effect (Toshiba air reads 38 units low).
- **Decision (lead):** keep the z-fix study; add a quality rule. Logged as amendments A1 and A2.

**S3. All dev scans ($19.75).**
- **Did:** 7,336 main runs, 998 z-fix runs, 500 soft-kernel partner runs. Zero failures.
- **Problems and fixes:**
  - The helper agent hit its 5-hour usage limit mid-run. Fix: an unattended driver program that needs no agent.
  - Modal stopped and restarted a container (preemption). No data lost, but it is billed twice. Fix: the ledger is reconciled with Modal's real bill and counts the larger number.
  - November's money on the main account ran out. Fix (lead): use the second account `armanfo`, with a $17 limit and an identity test (results equal to the last digit).
- **Result:** gate passed on all 8,834 files.

**S4. The analysis on dev (free).** The code was committed and locked (`a536192`) **before** any real result was seen. Results: `imgsae/exploratory/lung_l2/RESULTS_S4_dev.md`. Part 6 explains each one.

**S5. The freeze (free).** Five hypotheses, thresholds, the dictionary and the analysis code were locked with hashes (commit `c593005`). File: `imgsae/exploratory/lung_l2/HYPOTHESES_L2.md`.

**S5 review (free, 16 Nov).** `docs/REVIEW_S5_L2.md`. Verdict: approve with changes. H1 to H4 approved. H5 not approved as written. **This is where we are now.**

---

## 6. What each dev result shows

| # | Result on dev | What it shows | How sure |
|---|---|---|---|
| 1 | Known factors explain 31% of Sybil's 1-year score. Nodule findings give 21%, technical factors 1.6%. | Most of what moves Sybil's score is not on the form and not in our simple measures. | Solid on dev. |
| 2 | Sybil's inner vector `h` has only about 5 to 7 real dimensions. Fewer than half of its 512 units are alive. One axis holds 35% to 44%. | Sybil boils each scan down to roughly one risk dial. There are no many separate ideas at this layer. | Solid on dev (reviewer's check). |
| 3 | SAE **failed** validity at both sizes (it does not keep Sybil's function: correlation 0.72 to 0.86; needed 0.98). PCA, ICA, NMF, k-means failed too. | A sorting tool needs many separate ideas. There are none here. This is a property of Sybil, not a bug in our code. | Solid on dev. |
| 4 | Raw units passed: 56 families (34 nodule-named, 6 technical-named, 16 mixed). | They pass, but weakly: the families are mostly copies of the risk dial (median correlation with the score 0.90). | Weak. |
| 5 | z-fix (924 exams, 12.6% of dev): score falls by 0.33; 67% of exams move by a quarter SD or more; 7.5% change their flag. | Sybil's answer depends strongly on how slice spacing is handled. | Solid on dev. To confirm on test (H1 to H3). |
| 6 | z-fix flags: 112 before, 105 after, but 38 lost and 31 new. Of the exams flagged in either run, 48% are flagged in one only. | The fix **reshuffles** the alarms. It does not simply remove alarms. | Solid on dev. |
| 7 | z-fix does not raise the AUROC (0.995 to 0.985). Stretched scans are flagged as often (10.6%) as normal scans (10.4%). | We showed **sensitivity**, not **harm**. We cannot say the stretched picture makes Sybil worse. | Important limit. |
| 8 | Kernel pairs (500): the flag changes in 1.8% of exams (13% of flagged exams). | The kernel matters much less than the spacing. | Solid on dev. To confirm on test (H4). |
| 9 | With z-fix, the technical-named units move strongly (−0.057, in 96% of exams). The nodule-named units do not move (+0.005). | The "technical" label is real: these units answer to a real intervention. This is the one true feature-level finding. | Solid on dev (reviewer's check). Proposed as the new H5. |
| 10 | Technical removal: point value good, but the interval includes "no effect" and the two halves disagree. Sybil + form at the radiologists' sensitivity: 60 → 42 false alarms per 1,000, interval includes "no effect". Reliability flag: wrong direction. | No use of the features passed the gate. | Failed, reported as failed. |
| 11 | On dev Sybil adds +0.04 to +0.10 to the form. On test (L1) it adds about 0. | Dev flatters Sybil, because its authors used dev to pick the model. Never trust a dev accuracy number for Sybil. | Solid. |
| 12 | Missed at 6 years (first scan): small-cell 16 of 19, central 11 of 14, stage IV 22 of 30, found 4 to 6 years later 26 of 34. | Sybil misses fast and central cancers and cancers not yet visible. | Descriptive only (small groups). |

---

## 6b. Why the feature tools failed, and what more we can try

### What "Sybil's own raw units" means
For every scan, Sybil itself computes 512 numbers just before its score (we call them `h`). These are **Sybil's own units**. We did not make them. The "raw units" arm simply takes the 64 units that matter most for the score and calls each one a feature. It is the "do nothing clever" option. The other five tools (SAE, PCA, ICA, NMF, k-means) try to build **new** features out of those 512 numbers.

### Why each tool failed
| Tool | What it assumes | What it met in Sybil | Mark it failed |
|---|---|---|---|
| **SAE** (4 of 64 features active per scan) | Many separate ideas; each scan uses only a few | Few directions (about 5); every scan uses all of them | It could not rebuild Sybil's score (0.72 to 0.86; needed 0.98) |
| **PCA, ICA** | A few main directions | True, and they rebuild the score (0.999). But each of the five member models has its own directions after the first three | Only 2 to 7 features were found again in other members (16 needed) |
| **NMF, k-means** | Parts that add up; or groups of similar scans | One smooth dial, not parts and not groups | Did not rebuild the score, and did not replicate |
| **Raw units** | Nothing | 64 units that are mostly copies of the risk dial | Passed, but tells us little |

**Why is Sybil like this?** It was trained for one job: give one risk number. A network trained this way keeps only what that number needs. And its five members were trained apart, so each has its own inner "language" beyond the main dial.

### A new check (16 Nov; dev, 2,500 random exams, no outcomes; exploratory)
| Saved layer | What it is | Real dimensions | Directions that two members share |
|---|---|---|---|
| `h` | the 512 numbers after the last switch (ReLU) | 4.5 to 6.4 | 6 |
| `pre` | the same 512 numbers before the switch | 2.5 to 3.7 | 9 |
| `pooled` | 1,536 numbers, one layer earlier | 5.7 to 10.8 | **14** |

So the earlier layer holds somewhat more. It is still small and dense, so I do not expect an SAE to work there either. But a method made for "a few shared directions" can work.

### What more can be tried
| What | Cost | When | What I expect |
|---|---|---|---|
| The same six tools on the `pooled` layer (F1) | free, data already on the PC | now, before the freeze | SAE fails again; raw units pass |
| SAE with other sparsity settings (F1b) | free | now | It keeps the score only when it is no longer sparse |
| Shared axes across the five members (F2) | free | now | About 6 axes at `h`, about 14 at `pooled`; some can be named; some move with z-fix |
| Where Sybil looks: attention maps (F3) | free | now | Descriptive pictures for the paper |
| An SAE on the spatial map before pooling (N9b) | new extraction, about the cost of S3 again plus storage; new budget | after the test | The only place where many separate ideas can exist. Uncertain |
| More outcome-free tests on the 11,432 people Sybil never used (old step S7) | paid, new approval | after the test | A second confirmation set for technical findings (it has only 34 cancers) |

### What we found when we tried (step R, 16 to 17 Nov; dev only; full report `imgsae/exploratory/lung_l2/RESULTS_R_dev.md`)
The lead asked the reviewer session to test more methods before the Opus session. Result:

1. **The SAE is not rescued.** With more active features it keeps more of Sybil's score (0.72 → 0.83 → 0.978 for 4, 8, 16 active), but it still fails, and it finds no more shared features (8, 8, 9; 16 needed).
2. **The last layer `h` holds only about 3 shared directions** (risk, "lung cut off in z", one without a name). No method finds more. The 56 valid raw-unit families are all copies of the risk direction.
3. **The earlier layer `pooled` can be read with "shared axes".** Think of five people who each describe the same scan in their own private language. A dictionary made for one person does not fit the others. But we can ask: on which things do all five always agree? Those are the shared axes. There are **11**. They repeat in both halves of dev. A shuffle check gives 0.
4. **Only 1 of the 11 is the cancer-risk direction.** The clearest others are technical: z-geometry (lung cut off, number of slices), field of view and body size, scanner maker, breathing and image quality.
5. **One name is proven by an experiment.** The spacing fix moves the "z-geometry" axis by 2.74 SD; the kernel change does not move it; no random axis out of 2,000 moves by 2 SD.
6. **That axis explains hypothesis H2.** The spacing fix lowers the score on average (−0.326). With this one axis switched off in all five members, the average drop is gone (+0.08), and the AUROC on dev stays the same. A random axis does this in 1 of 2,000 tries.
7. **Limits:** the 11 axes are readings, not a full dictionary (the score rebuilt from them alone: r 0.95, mark 0.98). Switching the axis off removes the average drop, but only part of the exam-by-exam change (0.67 → 0.55). Dev only. It does not improve cancer prediction.

**Why this matters for the goal:** the lead wanted features of the model that mean something. We now have a small set, found by a method that fits Sybil, with one of them tested by intervention. It becomes hypothesis **H6** for the test set.

---

## 7. Where we are today (16 Nov 2026)

- **State (updated 17 Nov):** S5 frozen at `c593005`; reviewed; the lead decided on 16 Nov (step N0 done). Step NF was done on 16 to 17 Nov as "step R" by the reviewer session (part 6b, end). **Next: the executor (Opus 5.5) checks step R, freezes the shared axis and makes the new freeze (N1), with the prompt `docs/HANDOVER_PROMPT_L2_N1.md`.** The test split is closed. No test data exist on the PC or in the cloud.
- **Money:**

| | Used | Limit | Left |
|---|---|---|---|
| Whole project | $47.09 | $72.00 | $24.91 |
| Task `lung_l2_audit` | $21.70 | $45.00 | $23.30 |
| Main account `shforghani2002`, November | $28.17 | $29.00 | $0.83 (used up) |
| Second account `armanfo`, this project | $14.03 | $17.00 | $2.97 |

- **Where the money went:** CT work $7.74; prostate MRI $5.12; lung L1 $12.53; lung L2 $21.70.
- **Next paid step:** the test extraction (S6), about $18.9, or $20.8 with a reserve, against $22.30 allowed. It must wait for **1 December** on the main account, unless the lead decides otherwise.

---

## 8. The plan from here, step by step

**Rule for every agent:** do the next open step only. Each step says who does it, what it costs, why, what to do, when it is done, what can go wrong, how we prevent it, and when to stop and ask. If something is not written here or in the protocol, **stop and ask the lead**.

### N0. The lead decides (free). **DONE on 2026-11-16**
- **The lead's words:** "we do all you ask, put in plan, push and give prompt to give Opus xhigh".
- **Recorded as:** (1) H5 is replaced by H5′; (2) OK for a new freeze with the four small changes; (3) OK for the test extraction in December on the main account with the thin margin and the frozen fallbacks.
- **Still open, only the lead can do them:** (4) the request for an outside dataset (needs the lead's name); (5) the clinical co-author.
- **Added the same day:** the lead asked for more feature work ("other method? other layer?"). It is step NF below. Its OK is given by pasting the execution prompt `docs/HANDOVER_PROMPT_L2_N1.md`.
- **Who:** the lead.
- **Why:** an agent must not choose hypotheses. That is the lead's right.
- **The questions were:**
  1. **H5:** (a) replace it by H5′, the reviewer's advice; or (b) drop it, family of four; or (c) keep it. With (c) H5 stays unapproved.
  2. OK for a new freeze commit with the four small changes of the review.
  3. OK for S6 in December on the main account with the thin money margin.
  4. Optional now or later: request an outside dataset (step N9a); tell Sybil's authors (N9c).
- **Done when:** the answers are written in `docs/EXECUTION_LOG.md` with the date and the lead's words.

### NF. More feature work on dev, before the test opens (free, on the PC; amendment A6). **DONE on 2026-11-17 as "step R"**
- **What happened:** the lead asked the reviewer session (Fable 5.2) to do it at once. Report: `imgsae/exploratory/lung_l2/RESULTS_R_dev.md`. Short result: part 6b, end. F1, F1b and F2 of the list below were done (plus a joint dictionary, a removal test, a repair test and the random-choice tests). F3 (attention maps) was not done; it is descriptive and can be done after the test.
- **What is left for the executor:** rerun the step R scripts and compare; read the code as an outsider; freeze the axes into `results/s5/`; add hypothesis H6. All in the prompt `docs/HANDOVER_PROMPT_L2_N1.md` ("STEP F").
- **Changed since the plan below:** the recommendation is now that H6 enters and **H2 stays** (six hypotheses), because H6 explains H2. The lead chooses when pasting the prompt.
- **The plan as it was written on 16 Nov (kept for the record):**
- **Who:** the executor agent (Opus 5.5, xhigh). Prompt: `docs/HANDOVER_PROMPT_L2_N1.md`.
- **Why now:** the test cannot run before 1 December (money). These two weeks are free. Anything we learn on dev **before** the test opens can still become a hypothesis. After the test opens, it cannot.
- **Why it may help:** part 6b. One layer earlier, Sybil has more shared directions (about 14 against 6). And we never tested whether the SAE failed only because of its sparsity setting.
- **Do (all fixed in the prompt before any run; code committed before the full-dev run):**
  - **F1.** The same six tools and the same four validity marks, on the earlier layer (`pooled`, 1,536 numbers).
  - **F1b.** The SAE on `h` with other sparsity settings (8, 16 and 32 active features instead of 4).
  - **F2.** "Shared axes": the few directions that all five member models agree on, at both layers. Name them, and see which move under z-fix and kernel change.
  - **F3.** Where Sybil looks (its attention maps): descriptive only.
  - **F4.** A report `RESULTS_F_dev.md`, with every failed mark shown.
- **A new hypothesis may come from it only if:** it holds gate 9.8; a random choice of the same size does **not** also pass (the lesson of H5); and it can be computed on test from what S6 saves anyway. At most one. It then takes the place of H2, which becomes a secondary result. The lead can reject this at the stop.
- **Time limit:** if NF is not finished by 26 November, the freeze is made without it, and NF continues as exploratory work.
- **Can go wrong → prevention:** fishing for a result → the list of analyses is fixed first, the test set is the final judge, and the random-choice test is required. The slow laptop GPU → the time limit.
- **My honest expectation:** the SAE will fail again (the space is small and dense at both layers). The shared axes will give a handful of nameable directions. A new outcome-free hypothesis is possible. A feature that improves cancer prediction is unlikely.

### N1. The new freeze (free, on the PC)
- **Who:** the executor agent (Opus 5.5), in a fresh session.
- **Why:** H5 as written cannot fail and tests nothing; the review also found four small things. A hypothesis may only change **before** test data exist, and the change must be visible.
- **Do, in this order:**
  1. **Dev evidence for H5′** (if the lead chose (a)): write a small script `s5_h5prime_dev.py`. It computes, on the 924 D5 exams, the mean of G_T(zfix) − G_T(main) for ℓ̄_1 with the frozen dictionary, its participant bootstrap interval (2,000 draws, seed 0) and the two halves. It must give **−0.0566 [−0.0590, −0.0541], halves −0.0565 / −0.0567**. Also the same for the N, mixed and residual terms. Commit the script and its JSON output.
  2. **`s5_freeze.py`:** change the H5 entry to H5′ (statistic "mean of G_T(zfix) − G_T(main), ℓ̄_1, frozen raw-unit dictionary and labels"; population T5; direction `<`; null −0.02). Rename H4 to "the kernel changes the flag in fewer than 5% of exams". Add to the secondary list: flags lost, flags gained, share of discordant flags among exams flagged in either run (z-fix and kernel); the change of the N, mixed and residual terms; the old H5 share. Hash the three text inputs on their LF bytes.
  3. **`s6_frozen_analysis.py`:** compute H5′ in the z-fix block with `split_by_label` on the z-fix `h` and on the main `h` of the same exams. Fix `wald()`: if the bootstrap SD is 0, p = 0 when the estimate is on the right side of the null, else p = 1. Add the new secondary numbers.
  4. **Test-list script** `s6_manifest_test.py` (new; write it, test it on dev, **do not run it on test yet**): main rows = the split file's 6,715 series, tiers T1, T2, T3 by study year; T4 = 500 soft-kernel partners of T1 exams, with the same pair rule as `s1_manifest.py` (same study, same thickness, other kernel class, slice count within 2%), seed 0, the same quota rule by maker. Metadata and the split file only. It must not read any outcome.
  5. Run `s5_freeze.py`, then the frozen analysis on dev ("dev as if test"). H1 to H4 must equal the old values exactly. H5′ must equal step 1.
  6. **`HYPOTHESES_L2.md`:** rewrite H5; add a section "Changes after the first freeze `c593005`" that says what changed, why, and that H5′ was chosen from dev after the first freeze, on the reviewer's advice. Add comment 3 of the review ("sensitivity, not harm") and the two-direction flag numbers. New hash table (run `s5_hashes.py`), including the two new scripts.
  7. **H6 from step R** (updated 17 Nov): "with shared axis 0 of `pooled` switched off in every member, at least 0.20 of the average z-fix drop of ℓ̄_1 is removed" (dev +0.408 [0.403, 0.412]; random-choice 1 of 2,000). Frozen axes file `results/s5/frozen_axes_pooled.npz`. H2 stays unless the lead says "H6 replaces H2". **H7 from step R2** (added 17 Nov): "in real follow-up, when a person's yearly scan changes between stretched and not stretched, Sybil's 1-year score jumps by more than 0.10 beyond the change of the form" (dev +0.246 [0.134, 0.355]; permutation 2.5%; honest chance about 0.7); enters unless the lead moves it to the secondary list. The hypothesis file says plainly that H6 and H7 come from exploratory dev work by the reviewer session, with the dev evidence and the random-choice or permutation test.
  8. Commit, push, log the new freeze commit, update `STATUS.md`. **Stop.**
- **Done when:** one commit holds all of it, dev-as-if-test reproduces, the hash table matches.
- **Can go wrong → prevention:**
  - A frozen number changes by accident → compare old and new H1 to H4 values; any difference is a stop.
  - Windows line endings change a hash → `results/s5/` is stored byte-exact; write JSON with LF only (the scripts already do).
  - The agent "improves" other things → not allowed; only the listed changes.
- **Stop and ask if:** H5′ does not reproduce; any H1 to H4 value differs; anything about test data is unclear.

### N2. Short re-check of the new freeze (free)
- **Who:** the reviewer (Fable 5.2, fresh session). Prompt: adapt `docs/PROMPT_REVIEW_FABLE_S5.md` to the new commit.
- **Why:** a freeze nobody checked is worth less.
- **Do:** check the hashes, re-run dev as if test, read the H5′ code and the test-list script (no outcome read; same pair rule), read the diff from `c593005`.
- **Done when:** a dated note is added to `docs/REVIEW_S5_L2.md` and logged.

### N3. The lead's OK (free)
- **Who:** the lead.
- **Done when:** "OK for the freeze `<commit>` and for S6" is in the log with the date. **Nothing on test happens before this line exists.**

### N4. Test extraction, S6 part 1 (about $19 to $21; not before 1 December)
- **Who:** the unattended driver (`cloud/drive_plan.py`), started by the executor agent. Account `shforghani2002`.
- **Why:** the hypotheses need Sybil's inner numbers on the test scans.
- **Do:**
  1. Check the date and the budget: `budget.py status --no-log` (miniconda python). The month must be December.
  2. Run `s6_manifest_test.py`; commit `manifest_test.csv` and its hash.
  3. Change `cloud/l2_sybil_modal.py` only so that it can read the test list (root `test`). Log the change. No analysis file changes.
  4. **Smoke run first:** demo case and 3 test series. The demo must equal the published scores (difference ≤ 0.005; we expect 0.0).
  5. Then, by the driver, in this order: **T1** (2,279) → **T2** (2,243) → **T4** (500 pairs) → **T3** (2,193). All main runs with `--zfix-max 0.65`, so the z-fix runs are made with them.
  6. Copy to the PC. Reconcile the bill (`reconcile_billing.py`).
- **Checks before any analysis (all must pass):**
  - failures below 5% in every tier;
  - every file passes the rebuild checks G2b and G2c (`s3_checks_all.py` pattern);
  - **identity:** the new scores equal the L1 scores (`lung_l1/results/scores.csv`) within 0.0001 for at least 99% of the 5,412 L1 series.
- **Can go wrong → prevention:**
  - Money runs out → the guard refuses any launch over a limit; the order puts the needed tiers first; fallbacks are frozen (if T3 is missing, the hypotheses use T1 and T2; if T4 is missing, H4 counts as not confirmed).
  - Preemption doubles a bill → the 10% reserve; the ledger counts the larger of measured and billed.
  - The laptop sleeps or the agent hits its limit → the driver is a Windows task; cloud work is saved one scan at a time; restart skips finished scans.
  - Wrong account → `MODAL_PROFILE` is set per command; the driver refuses a mismatch.
  - Someone looks at test numbers too early → the driver only extracts; nothing is analysed in this step.
- **Stop and ask if:** the guard refuses; a check fails; cost goes above $22.00; identity fails; anything touches another app or volume.

### N5. The frozen analysis, once (free)
- **Who:** the executor agent.
- **Do:** `l2_data.py` for root `test`; then `s6_frozen_analysis.py` **one time**; write `results/s6/s6_test.json`; **commit it before reading or commenting**; then write the result as it is.
- **Why commit first:** so nobody can say the result was edited after it was seen.
- **Can go wrong → prevention:** a code error on test → the same script already ran on dev end to end; a hash mismatch → the script refuses to run.
- **Never:** re-run with a changed setting, drop a hypothesis that failed, or change a margin. A failed hypothesis is reported as failed.

### N6. Extra looks at test (free). Labelled "exploratory"
- **Who:** the executor agent, after N5 is committed.
- **Do:** the secondary references (AUROC of Sybil, form, size-only, form + image measures; Sybil + form at the radiologists' sensitivity), the miss patterns (small-cell, central, stage, time to diagnosis), the z-fix numbers by stretch class and scanner maker.
- **Rule:** every such number carries the word "exploratory" and its counts of exams, people and cancers.

### N7. Results file and paper outline (free)
- **Who:** the executor agent drafts; the lead and a clinical co-author judge.
- **Do:** `imgsae/exploratory/lung_l2/RESULTS_L2.md`; figures; a manuscript outline; a target journal with reasons. Every failed gate and every negative result is written as clearly as a positive one.

### N8. Checklists before submission (free)
- Reporting guides for prediction and imaging AI studies (TRIPOD+AI, CLAIM).
- Public code and frozen files (the repository already holds them); the hash of each frozen file in the supplement.
- A second person re-runs the frozen analysis from the repository.

### N9. Optional steps that raise the value (each needs the lead's own OK and, where paid, a new budget)
- **N9a. An outside dataset (the strongest step).** Why: modern scanners very often make overlapping slices, so the spacing problem may be bigger outside NLST. It would also answer "is this only an NLST thing?". Candidates: Duke DLCS (1,613 scans; restricted; request needed) and P-ELCAP (211 people, 67 cancers; request box). Both need the lead's name. Cost: free to request; a rough guess of $4 to $5 of cloud time to score the larger one (not measured; it needs its own budget line).
- **N9b. An SAE in the right place.** Why: the layer we used is one risk dial. Separate ideas, if they exist, live earlier: in Sybil's spatial map (512 × 25 × 16 × 16 numbers per member) before pooling. What it needs: a new extraction of dev scans, much more storage, a new protocol, and a pilot to measure cost (a rough guess is the cost of S3 again, about $20, plus storage). The payoff is uncertain. Do it only after S6.
- **N9c. Tell Sybil's authors** about the slice spacing (an issue on their public repository, or an email). When: after S6, or at submission. Why: it is fair, and their answer strengthens the paper.

---

## 9. Rules every agent must follow

1. **The test split is closed** until step N3 is logged. No test activation, no test manifest run, no new analysis of the L1 test scores.
2. **Frozen means frozen.** Do not edit `HYPOTHESES_L2.md`, `results/s5/` or the analysis scripts, except in step N1.
3. **Money.** Every launch goes through the guard. Check usage before every launch. Limits: task $45, project $72, main account $29 per month, `armanfo` $29.50 per month and $17 for this project. T4 or L4 GPUs only, at most 4 containers, timeout at most 60 minutes.
4. **Always save.** Detached launches; one saved file per scan; a killed client must lose nothing; copy to the PC and check before any deletion. No cloud volume is deleted.
5. **Fair comparisons.** The same number of features and the same selection rule for every arm. Recompute any claimed gain from the tables.
6. **Honest results.** A failed gate is "failed". No claim goes beyond its test. Every number gives its exams, people and cancers.
7. **Fresh data only.** Original public data, fresh download, checksums.
8. **Environment.** Windows and PowerShell, not Bash. Scripts: `D:\Shayan\imgsae\.venv\Scripts\python.exe`. Budget and Modal tools: `C:\Users\Arman\miniconda3\python.exe`. 4 BLAS threads. No package is installed without telling the lead.
9. **Records.** Every decision, deviation and result goes into `docs/EXECUTION_LOG.md`; the state into `STATUS.md`. Commit and push after every finished step. Keep `New report .txt` and `imgsae/exploratory/ucla_audit/` out of git.
10. **Privacy.** No name, email or project name in any request to an outside service.
11. **Never touched:** the lead's other apps and volumes on both accounts; the third Modal profile; the "reserve" budget.
12. **"Wait" means stop.** At a stop point, give the file path and stop.
13. **Writing to the lead:** short plain sentences; the result first, then the numbers, then what is needed.

---

## 10. How to publish, honestly

### What the paper can say (if the test confirms)
> "An independent audit of a deployed lung-screening AI, with rules fixed in advance. (1) On its own test set the model does not beat a simple model of the radiologists' recorded findings. (2) Its output depends on a slice-spacing step in its own code: in about 1 scan in 8 the chest is stretched, and correcting it changes about half of the positive calls. (3) The reconstruction kernel matters much less. (4) Its inner representation is close to one risk dial; sparse dictionary methods found no valid features, and no feature-based change improved it."

### What the paper cannot say
- "Our features improve cancer prediction." Not found.
- "The spacing step makes Sybil less accurate." Not shown; the fix did not raise accuracy on dev.
- "Sybil is equal to the form." We can say "no large gap" only (41 and 131 cancers).

### Three shapes, decided by the test result
| If the test shows | The paper is | Realistic level |
|---|---|---|
| H1 to H4 and H5′ confirmed | A full audit: baseline parity + spacing sensitivity + a confirmed feature-level label + honest negatives | A good specialist journal for imaging AI or digital medicine |
| Only the spacing and kernel results confirmed | A technical audit plus the L1 result | A specialist imaging journal |
| Nothing confirmed | The L1 paired result with a descriptive technical note | A short paper or research letter |

### What would lift it higher
1. **Outside data (N9a).** A top clinical journal will ask "does this matter outside one old trial?". Today we cannot answer. This is the biggest single step.
2. **A clinical number.** State the effect per 1,000 people screened: how many alarms appear or vanish because of slice handling. Editors and clinicians read this, not AUROC.
3. **The authors' answer (N9c).** "We reported it; the developers confirmed or fixed it" turns a finding into an effect on practice.
4. **Trust.** Fixed rules, frozen hashes, one look at the test set, public code, failed gates reported. Few AI audits have this. Say it in the abstract.
5. **A clinical co-author.** A chest radiologist who reads the draft and judges what matters at the bedside.
6. **Speed.** Post a preprint when the test result is in. Another group already audits Sybil with synthetic nodules.

### My honest view
- With today's results this is a **solid, publishable audit**. I cannot promise a top journal. Two things hold it back: nothing confirmed is about cancer itself, and we showed sensitivity, not harm.
- The most likely road to higher impact is N9a (outside data). N9b (an SAE on the spatial map) is the road back to your first goal, but it is a new project with new cost and no promise.
- A paper that says "we opened a famous AI; inside is one dial; it equals the doctor's notes; and it reads a stretched picture" is a real message. It is not the message you wanted first, but it is true and it is checkable.

---

## 11. Lessons: what went wrong, and how we prevent it now

| What went wrong | When | How we prevent it now |
|---|---|---|
| Unfair settings made the SAE look bad, then a like-for-unlike count made it look too good | Stages 1 to 3 | Same feature count, sparsity and tuning for every arm; recompute gains from the tables |
| We built on models that did not know the clinical answer | Stages 4, 5 | First ask "does the model beat a plain baseline?" with a free or cheap check, before any SAE work |
| I told the lead a wrong fact (a "test set" with 34 cancers; "the split is not public"; "the head is plainly linear") | 11 to 13 Nov | Check each fact at its source before stating it; write corrections into the log the same day |
| A network drop cancelled a cloud job | 10 Nov | Detached spawn; resumable work; one saved unit at a time |
| The helper agent hit its usage limit mid-run | 15 Nov | The unattended driver runs paid work, not an agent |
| Modal restarted a container and billed twice | 15 to 16 Nov | Ledger reconciled with the real bill; a reserve in every cost projection |
| A check was written wrongly and "failed" | 13 Nov (pilot) | Diagnose first; change a check only as a logged amendment with the lead's OK |
| A code bug silently dropped scanner maker and model (pandas 3) | 16 Nov | Synthetic tests with planted effects; a report of empty columns; code locked before real results |
| A frozen file was missing from the freeze commit; line endings changed hashes | 16 Nov | Byte-exact storage for frozen files; a hash check by a second reviewer |
| A hypothesis that could not fail was frozen (H5) | 16 Nov | An outside review before the test is opened; test each hypothesis against "would a random choice also pass?" |
| The laptop GPU runs at 10% speed | since 6 Nov | Hardware fault; results are correct; heavy fits take longer or go to the cloud |
| The laptop holds the only analysis copy | ongoing | Cloud volumes are kept; results and code are in git |

---

## 12. Where things are

| What | Path |
|---|---|
| This guide | `docs/PROJECT_GUIDE.md` |
| The log of everything | `docs/EXECUTION_LOG.md` |
| The current state | `STATUS.md` |
| The lung L2 rules | `docs/LUNG_L2_PROTOCOL.md` |
| The work plan P0 to P8 | `docs/PLAN_L2_NEXT_v1.md` |
| Lung L1 result (test) | `imgsae/exploratory/lung_l1/RESULTS_L1.md` |
| Lung L2 dev results | `imgsae/exploratory/lung_l2/RESULTS_S4_dev.md` |
| The frozen hypotheses | `imgsae/exploratory/lung_l2/HYPOTHESES_L2.md` |
| The frozen files | `imgsae/exploratory/lung_l2/results/s5/` |
| The frozen analysis | `imgsae/exploratory/lung_l2/s6_frozen_analysis.py` |
| The S5 review | `docs/REVIEW_S5_L2.md` |
| The money book and guard | `imgsae/exploratory/p1b_sanity/cloud/ledger.json`, `budget.py` |
| The cloud job and driver | `imgsae/exploratory/lung_l2/cloud/` |
| The data (not in git) | `D:\Shayan\imgsae_data\lung_l2\` and `lung_l2_vol\` |
| Earlier stages | `docs/DECISION_MEMO_P1.md`, `imgsae/exploratory/v2_ct/RESULTS_S1A.md`, `imgsae/mri/RESULTS_M1.md`, `docs/PAUSE_NOTE_2026-11-11.md` |

---

## 13. Open questions for the lead

Answered on 2026-11-16 (step N0): H5 → H5′; the new freeze; the test extraction in December.

Still open:
1. Request an outside dataset now, so it is ready after the test? (Duke DLCS or P-ELCAP; it needs your name.)
2. Who is the clinical co-author?
3. Six hypotheses (H6 enters, H2 stays; my recommendation) or five (H6 replaces H2)? You choose when you paste the prompt `docs/HANDOVER_PROMPT_L2_N1.md`.
4. The re-check of the new freeze (N2) should be done by a fresh session, because the first reviewer did step R.
