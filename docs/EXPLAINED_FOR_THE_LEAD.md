# Explained for the lead (and how every Claude session should talk to the lead)

- **Written:** 2026-11-17, from the conversations of 16 and 17 November between the lead and the reviewer session (Fable 5.2 / Opus 5.5).
- **Part A** is for every new Claude session: how to talk to the lead. Read it before writing anything to the lead.
- **Parts B to L** are the explanations the lead asked for, in simple words. They hold the numbers of 17 Nov. For the newest state, read `STATUS.md` (top lines). For the full plan, read `docs/PROJECT_GUIDE.md`.

---

## Part A. How to talk to the lead

The lead's first language is not English. The lead types fast, with typos. Read for the meaning ("z score problem" meant the z-fix / slice-spacing problem; "h" often means "hypothesis").

**1. Give a detailed walkthrough, not a short summary, whenever you explain what happened.**
On 17 Nov the lead said: "i feel i detach from the project, i cant remmber the step we do … you only give me short summary, instead of a detail wlakthrough!" After a full walkthrough the lead said: "now thats a good explain!"
- For every step say: what we wanted → what we did → what happened → what it shows → why we decided this → what can go wrong and how we prevent it.
- When the lead seems lost, start from the beginning: the whole story in a few sentences, the words needed, then each stage in order, then where we are, then what is next.

**2. Simple words first, numbers second.** Explain it as to a five-year-old, with a picture or comparison ("five translators", "turning one knob to the middle"), then give the numbers. Define every technical word the first time (a short table of words helps).

**3. Order of every answer:** the result or answer first → the numbers → what you need from the lead → the paths of the files you changed (full paths).

**4. Use tables** for comparisons, results and plans (step | who | what | cost | when).

**5. Be honest, always.**
- Say plainly what failed. Never dress a failure up.
- Say what we did **not** show (for example: "we showed sensitivity, not harm").
- Separate dev (homework) from test (final exam). Dev flatters Sybil.
- If you said something wrong earlier, correct it in the next message, in a "Correction:" line.

**6. Decisions:** give one recommendation and mark the default. Make the lead's choice explicit ("paste unchanged = my recommendation; add this line if you want X"). Write the lead's own words into `docs/EXECUTION_LOG.md`.

**7. Keep working:** the lead wants the work done, with status pushed to GitHub after each step. Do not stop to ask when the next step is clear. Ask only for real decisions (money, rules, test data).

**8. "Wait" means stop.** Deliver the file path and stop.

**9. Never:** put the lead's name, email or project name into a request to an outside service; raise the lead's earlier prostate manuscript; touch the lead's other apps or volumes on any cloud account.

---

## Part B. The whole project in three sentences

1. We wanted to open an AI that reads CT scans, find the "ideas" inside it, and use them to make it better at finding cancer.
2. We tried three kinds of data (CT organs, prostate MRI, lung CT). Only the lung model **Sybil** gave real results.
3. Inside Sybil there are not many small ideas, but a few big directions. Most of them are about the scanner, not the patient, and one of them causes a known error.

| Word | Meaning |
|---|---|
| **Sybil** | A public AI (MIT/MGH). It reads a lung CT and gives a cancer risk for years 1 to 6. It is really **5 small models (members)** whose answers are averaged. |
| **NLST** | The big public US lung screening study. Sybil was trained and tested on it. |
| **Train / dev / test** | Practice book / homework / final exam. Dev may be used freely. Test is opened **once**, after our predictions are written down. |
| **Feature** | One "idea" inside the AI, as one number per scan. |
| **SAE** | A tool that tries to split the AI's inner numbers into many separate features. |
| **Freeze** | Locking predictions and code with fingerprints (hashes) before opening the test. |
| **The form** | A simple model of the radiologist's recorded findings (nodule size, shape, plus age, sex, smoking). |
| **AUROC** | A grade for a risk score: 0.5 = coin flip, 1.0 = perfect. |

**The story so far, very short:**
- 6–11 Nov: CT organs (SAE found only brightness), prostate MRI (AI no better than brightness), the lead's own prostate model (too small a gain). Paused.
- 12 Nov, lung L1 (paid, on test): **Sybil equals the form** (1 year: 0.927 vs 0.929; 6 years: 0.724 vs 0.745). Our strongest finished result.
- 13–16 Nov, lung L2: we opened Sybil on dev. The SAE failed. We found the **slice-spacing problem** (the z problem, Part E). Five predictions were frozen; the review found H5 broken and proposed H5′.
- 16–17 Nov, step R: the rescue attempt (Parts C, D, F). Step R2/R3: real follow-up, harm, attention (Parts G, H).

---

## Part C. Inside Sybil: stations, layers, and why we looked where we looked

```
 CT scan (resampled to 200 slices × 256 × 256 pixels)
      │
 Station 1: the "eye" (a 3D ResNet-18, 4 blocks; early blocks see edges and texture, later blocks bigger shapes)
      │
 Station 2: the feature map = 512 numbers at each of 25 × 16 × 16 = 6,400 places (it still knows WHERE)
      │
 Station 3: "pooled" = three summaries of the whole map, joined: 3 × 512 = 1,536 numbers (the WHERE is gone)
      │       summary 1 attention-weighted average; summary 2 a second attention summary (can be negative); summary 3 the maximum
 Station 4: "pre" = a squeeze from 1,536 to 512 numbers
      │
 Station 5: "h" = the same 512 after a switch that sets negatives to 0 (ReLU)
      │
 Station 6: the head: 6 risk scores (cancer within 1 … 6 years)
```
Sybil is **five copies of this whole chain**, trained separately and averaged.

**What was saved for the dev scans:** stations 3 to 6 and the attention maps (where Sybil looks). Not saved: the eye and the feature map (about 240 GB for all dev scans; too big and costly).

**Why S4 used the last layer `h`:** it sits right before the score, so the score can be split exactly into pieces; it is small; and we did not yet know how little it holds.
**Was that bad?** Partly, yes. `h` is the most squeezed place: Sybil was trained for one number and throws away what that number does not need. SAEs work best in the middle of a network. So step R moved one station back, to `pooled`.

| Layer | Numbers | Real directions | Directions two members share |
|---|---|---|---|
| `h` | 512 | 4.5 to 6.4 | 6 |
| `pre` | 512 | 2.5 to 3.7 | 9 |
| `pooled` | 1,536 | 5.7 to 10.8 | 14 |

**Why not the feature map (station 2)?** It was not saved. It needs a new paid run (about $20 for dev) and a lot of storage. It is the only place that knows where in the lung something is, and the only place where an SAE could still work. Planned for after the test (step N9b), with a new budget.

**"Why not each submodel?"** We did use each of the five members separately (S4 fitted every tool inside each member, then looked for the same feature in 3 of 5 members = a **family**). That is exactly where the tools failed: each member speaks its own private language. The fix was to look at all five together (Part D).

---

## Part D. Directions, axes and shared axes

- A scan becomes a list of numbers (512 or 1,536). A **direction** is a recipe that mixes them into one value ("0.3 × number 5 − 0.1 × number 17 + …"). Think of an arrow: moving along it changes one property.
- **Real directions:** people described by height, weight, shoe size and arm length are 4 numbers but mostly 1 real direction ("body size"). Sybil's `h` is 512 numbers but about 5 real directions, and one of them (risk) holds 35% to 44% of all variation.
- An **axis** = a direction we found and numbered. A **shared axis** = a direction on which all five members agree.

**The five translators.** Five people translate the same 7,336 books into five private languages. We cannot read the languages, but we can ask: "is there something all five write more of in the same books?" If all five rise and fall together, book by book, they describe the same real thing.

**How it is found (multiset CCA):** per member, shrink to the 30 main directions; find a recipe per member so that the five values rise and fall together; **check on the other half of the people** (agreement must be at least 0.70 on average over the 10 pairs of members); a shuffle check must give nothing (it gave 0).

**Result in `pooled`: about 11 shared axes** (11 to 12 at the pre-set settings; up to 16 with looser settings). In `h`: only 1.

| Axis | Name | What it follows |
|---|---|---|
| 0 | **z-geometry** (technical) | lung cut off at top or bottom, number of real slices, stretching |
| 1 | field of view and body size (technical) | scan diameter, sex, body area |
| 2 | breathing quality and scanner model (technical) | also separates cancers on dev (0.81): needs a closer look |
| 3 | **cancer risk** | large, spiky nodules |
| 4 | scanner maker (technical) | Siemens against GE |
| 5 | image quality and lung density | |
| 6–10 | weak or no name | |

**Naming:** each axis is compared with about 70 known facts in 5 groups (nodules, background lung, person, image measures, technical); a fair-share rule (Shapley) picks the group; the name must repeat in both halves.

**Proof by experiment.** A name from correlation is weak. The z-fix changes only the slice spacing. It moved axis 0 by **2.74 SD**; the kernel change moved it 0.01 SD; no random direction of 2,000 moved by even 2 SD. So axis 0 really is the z-geometry direction.

**Switch-off (repair) test.** In each member, set axis 0 to its average, keep everything else, run the rest of Sybil. The average z-fix drop of the score (−0.326) becomes +0.08; Sybil's grade stays the same (0.969 → 0.970). A random direction never does this. Limit: each exam still changes (67% → 55% of exams change clearly), so the axis explains the average shift, not all the scatter. It is an explanation, not a repair for hospitals.

**Other tools at `pooled`:** NMF with 64 features passed all four validity marks and found the same themes, but it cannot hold negative numbers and half of summary 2 is negative, so it is supporting evidence only. The SAE came close but always missed one mark.

---

## Part E. The z problem (slice spacing)

- "z" is the head-to-feet direction (the direction the slices are stacked). It has nothing to do with z-scores.
- Each CT slice has a **thickness** (for example 2.5 mm) and a **spacing** (distance to the next slice, for example 1.25 mm). Many scanners make **overlapping** slices.
- **Sybil's code uses the thickness as if it were the spacing.** With overlapping slices it builds the chest up to **twice as tall** as it really is.
- Sybil uses a fixed box of 200 slices × 2.5 mm = 500 mm. A stretched chest (600 to 700 mm) does not fit, so the top and bottom are **cut off**.
- On dev: 44% of scans overlap somewhat; 12.6% (924 exams) are stretched 1.6 to 2× ("D5"); 82% of those have lung cut off.
- **The z-fix** = our corrected run: same images, slices at their true spacing.

**Did the authors make a mistake?** Yes, a real error in the code that prepares the scan, but a common one: for many scanners thickness equals spacing. **Sybil was trained with the same error**, so it is not "broken"; its answer depends on how the scanner made the slices. Not reported in Sybil's public issues. We should tell the authors politely (after the test result).

**Why is the fixed picture not better?** We did not show it is worse: AUROC 0.995 → 0.985 with only 16 cancers is chance. Alarms reshuffle (38 lost, 31 new). Sybil learned on stretched pictures, so the correct picture is new to it (like new glasses after years of reading with the wrong ones). **We showed sensitivity, not harm.**

**Does the cut hide nodules?** Rarely: only 8 of 588 recorded nodules (1.4%) in stretched scans fall in the cut-off part; Sybil caught all 14 one-year cancers in cut scans. The score change under z-fix is the same with and without a cut (0.667 vs 0.671), so the stretch itself, not the cut, is the cause.

**Can we fix it and gain accuracy?** z-fix at test time: no gain. Switching off axis 0: no accuracy gain, but more consistency. Retraining Sybil with correct spacing: maybe, but it needs terabytes of images and many GPU days, far beyond our budget. Even a perfect repair has little room: at 1 year Sybil already catches every cancer in stretched scans.

**It also happens in real life (H7).** Dev has 4,837 pairs of yearly screens of the same person; in 215 the scan changed between stretched and not. Beyond what the form explains, Sybil's 1-year score jumps by **+0.25** [0.13, 0.36] when the scan becomes stretched, and the jump is gone with axis 0 switched off. A patient's risk can jump because of a scanner setting.

---

## Part F. Why the SAE failed, and "only one risk axis"

- Same root cause: Sybil is a **one-number machine**. It packs all cancer information into one main direction and keeps little else.
- An SAE needs **many separate ideas, each scan using only a few**. In `h` there are about 5 directions and every scan uses all of them, so there is nothing to cut. We tried 4, 8, 16 and 32 active features: the best (16) kept 0.978 of Sybil's score (0.98 needed) and never found more than 9 shared families (16 needed). **The failure is Sybil, not our settings.**
- At `pooled` the SAE came close (3 of 4 marks).
- **3 of 5 members instead of all 5:** each group of 3 agrees on 11 to 13 axes; the extra ones are weak and technical (one is kernel sharpness). More axes ≠ more meaning. Also, Sybil's score is the average of all five, so a direction only 3 use matters less, and searching 10 groups finds more noise.

---

## Part G. Harm: can it be tested?

- Harm (worse care for patients) is the most important clinical question. It needs cancers. Test will have only **about 12** stretched one-year cancers (dev: 18, all caught). With 12 of 12 caught, the 95% interval of sensitivity is 74% to 100%. **Only a very large harm could be seen.**
- On dev there is **no sign of harm**: false alarms 10.9% (stretched) vs 11.3% (other); Sybil-only false alarms 9.1% vs 7.6% (chance); the z-fix reshuffles them (80 → 75).
- **A trap we caught:** "does the stretch make Sybil look away from the nodule?" First answer: yes (27% vs 40%). But random nodule positions gave the same pattern: it was the geometry of the box. After correction: no harm sign. **Always compare with a random or shuffled baseline** (the lesson of the old H5).
- **What we do:** on test, harm is a pre-stated **measurement** (with the detectable size written down before), not a hypothesis. A real harm test needs **an outside dataset** with hundreds of cancers and overlapping-slice scans, ideally both reconstructions of the same scan. That needs the lead's name for the data request.

---

## Part H. Where Sybil looks

Sybil has built-in attention maps (as far as we know the authors used these, not Grad-CAM, and trained them partly with radiologist boxes; check their paper before writing this). NLST records the slice and lobe of every reported nodule. On dev (held-out half):

| Exams | Attention near the nodule's slice | Chance (random positions) | On the correct lung side |
|---|---|---|---|
| Cancer within 1 year | 72% | 26% | 88% |
| No cancer, nodule ≥ 8 mm | 51% | 22% | 77% |
| No cancer, nodule 4–8 mm | 32% | 23% | – |

The maps are coarse (cells about 2 cm). Good for paper figures; a real helper for radiologists needs exact nodule coordinates and a separate study. Idea for later: false alarms where Sybil looks at no recorded nodule.

---

## Part I. The predictions for the test set (H1 to H7)

**Update (17 Nov, second freeze `c3578c3`): H5′ is no longer a prediction.** It reproduced on dev (−0.057), but 59.7% of random sets of 6 units also pass its −0.02 line, so it could not fail (the old H5 mistake again). The lead chose to move it to the secondary list. **The frozen family is six: H1, H2, H3, H4, H6, H7.** H7 is labelled "partly seen" (a rough version could have been computed from the L1 test scores; nobody did). Details: `imgsae/exploratory/lung_l2/HYPOTHESES_L2.md`. The table below is the version of 17 Nov before the freeze.

| | Claim | Dev | Line to beat | If it passes | If it fails |
|---|---|---|---|---|---|
| H1 | z-fix changes the 6-year score clearly in > 30% of stretched exams | 67% | 30% | strong spacing sensitivity (core finding) | smaller on test |
| H2 | z-fix lowers the 1-year score on average | −0.33 | −0.10 | the direction: stretch raises risk | direction not stable |
| H3 | z-fix changes the alarm in > 5% of stretched exams | 7.5% | 5% | reaches the clinical decision | too small to change alarms (weakest, about 60% chance) |
| H4 | kernel change flips the alarm in < 5% | 1.8% | 5% | control: not every technical change matters | Sybil also kernel-sensitive |
| H5′ | technical-named units react to the z-fix | −0.057 | −0.02 | the "technical" label is real | unit labels unreliable |
| H6 | the shared z-geometry axis carries the z-fix drop | 0.41 | 0.20 | the mechanism, inside Sybil | mechanism held on dev only |
| H7 | in real yearly screening the score jumps when the reconstruction changes | +0.25 | +0.10 | real-world evidence (about 70% chance) | effect not seen in real follow-up |

All seven are outcome-free. None claims harm or better cancer prediction. Plus two pre-stated measurements: harm (with detectable size) and where Sybil looks.

---

## Part J. "Did the project turn into the z-fix and give up on features?"

No. The z-fix is the **tool** that proves what a feature means (the only experiment we have, and it needs no cancers, so the test has power). The features gave: why SAEs cannot work on Sybil's last layer; the 11 shared directions (the feature map of Sybil: mostly technical, one risk); the z-geometry direction proven by experiment (H6) and seen in real screening (H7); attention that follows the radiologist's nodule. What failed: using features to improve cancer prediction.

**The paper, if the test confirms:** (1) on its own test, Sybil equals a simple model of the radiologist's notes; (2) inside, the SAE fails and we show why; (3) the five members agree on about 11 directions, mostly technical; (4) a slice-spacing error changes Sybil's scores through one shared direction, shown by experiment and seen in real yearly screening; (5) no evidence of harm, and the test cannot check small harm.

---

## Part K. Money (17 Nov) and the plan

| Account | Cap | Used this month | Left |
|---|---|---|---|
| `shforghani2002` | $29.00 | $28.17 | $0.83 (resets 1 Dec) |
| `armanfo` | $29.50 | $15.69 | $13.81 (project limit raised to $27) |
| `forghanishayan` | $29.50 | $5.02 (the lead's idle app) | $24.48 (added 17 Nov, project limit $20) |
| Project cap $72 | | $47.09 | $24.91 |

Lead, 17 Nov: "i dont need any other account for my other works, so we can use them all". So the test run moves to November.

| # | Who | What | Cost | When (about) |
|---|---|---|---|---|
| 1 | Lead | paste `docs/HANDOVER_PROMPT_L2_N1.md` into a fresh Opus 5.5 xhigh session | free | 17–18 Nov |
| 2 | Opus | checks step R, freezes the axes, makes the new freeze (H1–H7), stops | free | 18–19 Nov |
| 3 | A fresh session (not the one that did step R) | re-checks the freeze with `docs/PROMPT_REVIEW_S5b.md` | free | 19–20 Nov |
| 4 | Lead | "OK for the freeze `<commit>` and for S6" | free | 20 Nov |
| 5 | Driver | test run: `armanfo` smoke + T1 + T4 (about $8); `forghanishayan` identity check + T2 + T3 (about $13) | about $19–21 | 21–23 Nov |
| 6 | Opus | the frozen analysis, once; saved before anyone reads it | free | 23–24 Nov |
| 7 | Opus and lead | results, paper outline, checklists | free | end of Nov |
| 8 | Lead (optional) | tell Sybil's authors; request an outside dataset; feature-map study (needs a new budget: about $4–6 of the project cap is left after the test) | – | after results |

---

## Part L. Lessons that every session must keep

| Lesson | Rule |
|---|---|
| The old H5 passed for any random choice | Every hypothesis needs a random-choice or shuffle test; ≥ 5% passing = reject |
| The attention "harm" was geometry | Compare every attention or location result with shuffled positions |
| Dev flatters Sybil | Never trust a dev accuracy number for Sybil; only test counts |
| Steps added after seeing results | Write them in the log **before** they run; mark them in the report |
| The reviewer did analysis | The next check must be done by a fresh session |
| A data table repeated a column (z-fix `resampled_T`) | Check geometry and counts against physics before trusting a result |

---

## Part M. The test night (17 to 18 Nov 2026), step by step

**The whole story in three sentences.** We fixed six predictions on dev, then opened the test split once. Five came true and one failed. The strongest result: one shared direction inside Sybil carries the slice-spacing problem, on new scans and in real yearly screening.

**Words you need**
| Word | Meaning |
|---|---|
| test split | the final exam: scans Sybil and we never used for choosing anything |
| frozen | written down and locked (hashes) before the test was opened |
| Holm | a rule that makes six tests together as strict as one test |
| z-fix | the same scan, given to Sybil with the true slice spacing |
| axis 0 | the "z-geometry" direction shared by all five Sybil members |

**Step 1. Build the test list (free).** *Wanted:* the exact scans to score. *Did:* `s6_manifest_test.py`, from metadata and split names only (no outcome). *Happened:* 6,715 scans plus 500 kernel partners, 2,347 people. *Shows:* the list follows the frozen rules.

**Step 2. Small test runs on both accounts ($0.34).** *Wanted:* proof that both accounts compute the same as the main account. *Problem:* the laptop's upload through the VPN was very slow (28 KB/s); Modal gave up uploading the 2 MB list. *Fix:* the job now carries a compressed copy; before every launch it checks that the copy holds exactly the same bytes. *Happened:* the demo case equals the published scores exactly; the two accounts give identical numbers (difference 0.0).

**Step 3. The big run (about $17.6, 5.5 hours, unattended).** *Did:* armanfo scored year 0 and the kernel pairs; then forghanishayan scored years 1 and 2 (never both at once, by our rule of at most 4 machines). *Happened:* 7,215 scans and 759 z-fix scans, **0 errors**. The guard once allowed only 1 machine (its month safety rule); the run simply took a little longer.

**Step 4. Checks before any analysis (free).** All files complete; Sybil's numbers rebuild exactly; **all 5,412 scans that L1 scored give the same score again** (largest difference 0.0000009). The data are clean.

**Step 5. The frozen analysis, once, saved before reading (free).** *Did:* checked again that no frozen file had changed and that no number was missing (your four run rules); ran the frozen script one time; committed the output to GitHub **before** looking at it. Nobody can say we changed it after seeing it.

**Step 6. The result.**
| | Prediction | Test | Result |
|---|---|---|---|
| H1 | the true spacing moves the score in more than 30% of stretched scans | 66% | ✅ |
| H2 | it lowers the score by more than 0.10 | −0.37 | ✅ |
| H3 | it changes the alarm in more than 5% | 4.5% | ❌ failed |
| H4 | the kernel changes the alarm in fewer than 5% | 1.8% | ✅ |
| H6 | axis 0 carries at least 0.20 of the drop | 0.41 (the whole drop) | ✅ |
| H7 | in real yearly screening the score jumps when the stretch changes | +0.31 | ✅ (mostly GE scanners) |

**What it shows, simply.** Think of one knob inside Sybil. When the slices are placed too far apart, the knob turns, and Sybil's score follows. On new scans the knob turned the same way (−2.73, dev −2.74). Put the knob back to the middle, and the whole drop disappears (−0.37 → +0.04). In real screening, when a hospital changed its reconstruction from one year to the next, the same knob turned, and Sybil's score jumped; with the knob in the middle, the jump disappears too.

**What failed or is weak, honestly.**
- H3 failed: the alarm changed in 4.5%, not more than 5%. On test the fix mostly removed alarms (27 lost, 7 gained).
- H7 is a GE result: 121 of the 134 changed pairs involve a GE scanner. Without GE there are only 13 changed pairs: no conclusion.
- No harm shown: only 9 one-year cancers among the stretched scans; both runs catch the same 7. "No difference" does not mean "no harm".
- Dev flattered Sybil: on dev it looked far better than the radiologists' recorded findings; on test it is not better (0.914 against 0.947), and it adds nothing to the findings plus image measures.

**What can go wrong next, and how we prevent it.** A reader may say "you looked many times on dev" → the six were frozen and hashed before the test, and the test was analysed once. A reader may say "this is only NLST and GE" → we say it plainly; an outside dataset (N9a) is the best answer.

**What we need from you.** Read `imgsae/exploratory/lung_l2/RESULTS_L2.md`. Choose the journal (my suggestion: *Radiology: Artificial Intelligence*; higher with an outside dataset and a clinical co-author). Decide on the outside dataset request (needs your name).
