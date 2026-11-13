# Lung L1 results: Sybil against the radiologists' recorded findings (NLST, Sybil's test split)

Protocol: `docs/LUNG_L1_PROTOCOL.md`. Analysis: `l1_analysis.py` (SHA-256 checked before the run: starts 1781679E, ends 2091FC1D), run once, unedited.

## Verdict (as printed)
No evidence that Sybil carries information beyond the recorded findings, at the precision of this test set.

## What ran
- Sybil `sybil_ensemble`, commit `d9fc81b93c1c6239a570c1c570c1f2a2e6266a4a`, on Modal T4 (Python 3.10, torch 1.13.1). Checkpoint hashes are in `results/run_info.json`.
- Images were downloaded per series from NCI IDC (public bucket), scored, and deleted. Scores are one file per series.
- Baseline tier P1: all 2,279 baseline series scored. Tier P2 (T1 and T2): 3,133 of 4,436 series scored (1,584 at T1, 1,549 at T2).
- Total 5,412 series, 2,331 participants. No duplicate participant-year. No train or dev participant scored.
- P2 cut-off: positions 0 to 3,199 of the fixed random order (seed 0) were run. 67 of them were not reached by the last shard before its 50 minute limit. The rest (positions 3,200 to 4,435) were not run because the 13.00 USD rule of section 5 was reached.
- Failures in the final runs: none. Mean seconds per series: download 2.7, loading 4.6, inference 7.4 (download and loading overlapped with inference).

## Gates
| Gate | Result |
|---|---|
| S0 guard checks | passed |
| S1: at least 95% of series in IDC; one series per participant-year | passed: 6,715 of 6,715 found; study years 0/1/2 = 2,279/2,243/2,193; 0 duplicates |
| S2a demo case within 0.005 | passed: max difference 0.0 |
| S2b benchmark, projection | passed: about 7.3 s per series in bulk; full run would not fit under 13.00 USD, so P1 then partial P2 (rule of section 5) |
| S3 P1 complete | passed: 2,279 of 2,279 |
| S4 export | passed: 5,412 rows = 5,412 saved files; 0 duplicate participant-year |
| S5 mapping check | passed: label agreement with split file 0.9987; 0 rows outside the test split |
| S5 sanity check | passed: Sybil AUROC A1 0.9265 (range 0.88 to 0.97), A3 0.9141 (range 0.86 to 0.96) |

## Results (AUROC, with intervals; A1 and A2 are 97.5% intervals, the others 95%)
| | A1 (1 yr, baseline) | A2 (6 yr, baseline) | A3 (1 yr, all screens) | A4 (2 yr, baseline) | A5 (1 to 6 yr after negative baseline) |
|---|---|---|---|---|---|
| exams / positives | 2,278 / 41 | 2,002 / 131 | 5,380 / 72 | 2,270 / 57 | 1,140 / 51 |
| Sybil | 0.9265 (0.8746, 0.9684) | 0.7238 (0.6654, 0.7824) | 0.9141 (0.8664, 0.9522) | 0.8770 (0.8234, 0.9277) | 0.5799 (0.5015, 0.6563) |
| Recorded findings | 0.9293 (0.8646, 0.9741) | 0.7448 (0.6909, 0.7945) | 0.9448 (0.9063, 0.9740) | 0.8911 (0.8424, 0.9335) | 0.6437 (0.5663, 0.7168) |
| Sybil minus findings | -0.0027 (-0.0628, 0.0581) | -0.0210 (-0.0734, 0.0342) | -0.0307 (-0.0722, 0.0077) | -0.0141 (-0.0669, 0.0337) | -0.0638 (-0.1600, 0.0299) |
| Combined (cross-fitted) | 0.9469 (0.8977, 0.9806) | 0.7537 (0.6982, 0.8067) | 0.9441 (0.9003, 0.9779) | 0.9042 (0.8603, 0.9454) | 0.6348 (0.5538, 0.7077) |
| Combined minus findings | +0.0255 (-0.0038, 0.0609) | +0.0105 (-0.0189, 0.0403) | +0.0002 (-0.0297, 0.0210) | +0.0146 (-0.0157, 0.0451) | -0.0075 (-0.0264, 0.0106) |
| Combined minus Sybil | +0.0247 (-0.0139, 0.0690) | +0.0395 (0.0115, 0.0724) | +0.0346 (0.0115, 0.0644) | +0.0300 (0.0054, 0.0563) | +0.0857 (0.0045, 0.1686) |
| LR test, Sybil given findings (chi2, p) | 32.47, 1.2e-8 | 30.77, 2.9e-8 | 38.85, 4.6e-10 | 37.57, 8.8e-10 | 1.14, 0.29 |
| LR test, findings given Sybil (chi2, p) | 43.01, 5.4e-11 | 36.91, 1.2e-9 | 123.53, 1.1e-28 | 40.59, 1.9e-10 | 9.12, 0.0025 |

Reading against the rules: A1 and A2 "beats" needs a difference of +0.03 or more with the lower bound above 0: not met (A1 -0.003, A2 -0.021). "Adds" needs combined minus findings of +0.02 or more with the lower bound above 0: A1 gives +0.026 but its lower bound is -0.004, A2 gives +0.011: not met. The likelihood-ratio tests are very significant in A1 to A4 in both directions, but they are not the verdict rule and the cross-fitted AUROC gain over the findings stays within noise. The set has few cancers (41 and 131), so a true gap under about 0.03 to 0.04 can be missed: this means "no large gap", not "equal". Because only 3,133 of 4,436 follow-up series were scored, A3 uses fewer follow-up exams than the plan intended (A1, A2, A4, A5 use baseline scans only and are not affected; 2,278 of the 2,279 baseline series have a known 1-year label).

## Cost (ledger, task `lung_l1_sybil`, cap 15.00)
Total measured 12.53 USD (project share under the 13.00 line set for scoring). Per run:

| Run | What | USD |
|---|---|---|
| 018 | S1 index join (CPU) | 0.11 |
| 019 | smoke, failed (non-DICOM files in demo zip) | 0.25 (estimate) |
| 020 | smoke, hung, stopped by hand | 0.57 (estimate) |
| 021 | smoke, demo only, passed | 0.15 |
| 022 | download test, hung | 0.13 (estimate) |
| 023 | download test, passed | 0.11 |
| 024 | benchmark, 20 baseline series | 0.22 |
| 025 | P1 first 800 positions, 4 containers | 1.00 |
| 026 | P1 all positions | 2.70 |
| 027 | P1 last 187 series | 0.73 |
| 028 | P2 positions 0 to 1,599 | 3.24 |
| 029 | P2 positions 1,600 to 3,199 | 3.21 |
| 030 | export call, timed out | 0.12 (estimate) |

Runs 019, 020, 022 and 030 were closed by hand with conservative estimates, as the call failed and returned no container time.

## Deviations from the protocol
1. Image build: Sybil's `setup.cfg` pins `torch==1.13.1+cu117`, which the package mirror does not have. Installed torch 1.13.1 and the other pinned dependencies from PyPI, then Sybil at the pinned commit with `--no-deps`. Model code and checkpoints are unchanged.
2. Smoke attempt 1 (run 019) failed: the demo zip contains two non-DICOM files. Fixed by keeping only files pydicom can read (194 of 196). This is a file filter, not a change of preprocessing.
3. Smoke attempt 2 (run 020) hung after loading the model (runner heartbeat timeout). I stopped the app by hand. Cause: the download step of the 20 series, see 4. Run 021 (demo only, with logging) passed with a difference of 0.0.
4. Download test (runs 022, 023): idc-index `download_from_selection` hangs when two calls run in threads. Replaced by direct `s5cmd` calls to the same public bucket (same files). This was a second failure of the same step after one diagnosis; the cause was found and fixed rather than stopping, and the cost was small.
5. The 20-series benchmark was run as a normal tier job on the first 20 baseline series by order (not a random pick); those scores are part of the final set.
6. Loading of the next series was moved into a prefetch thread to overlap with GPU inference (lower cost; same inputs and model).
7. Run 025: shards 2 and 3 failed on every series with a KeyError (a reused container kept an old address map). Fixed by rebuilding the map at the start of each call; the series were scored later in runs 026 and 027. Stale error files remain on the deleted volume only; none concern a scored series' result.
8. P2 covers 3,133 of 4,436 series (see above), by the budget rule. Two interruptions of my session by an API rate limit happened between launches; no job was affected and nothing was repeated.
9. Run 026 and 027 wrote the same result file name; the earlier one was kept as `results/run_P1_0_2279_run026.json` and the later one as `run_P1_0_2279_run027.json` (`run_P1_0_2279.json` is a copy of 026).
10. Export through a cloud call (run 030) timed out; scores were fetched with `modal volume get` and joined locally into `scores.csv` (same columns).

## Files
`results/scores.csv`, `results/l1_results.json`, `results/analysis_stdout.txt`, `results/run_info.json`, `results/scores_raw/` (per-series files), `results/manifest_series.csv`, `results/s1_index.json`, `results/smoke.json`, `results/dl_test.json`, run result files, `cloud/` scripts, `logs/runs/`.
