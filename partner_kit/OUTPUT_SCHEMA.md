# The returned file: `TO_RETURN/aggregate_report.json`

Every value is an aggregate. Counts below `min_cell` appear as the text `"<min_cell"`; withheld rates appear as `null` with `"note": "withheld: small cell"`.

- `kit_version`, `compare.site` (the site label you chose, for example "A"), `compare.min_cell`, `compare.cells_suppressed`.
- `compare.missing_share_by_item`: share of exams with each form item missing (0 to 1).
- `compare.endpoints.<E1_1year_all_screens | E2_1year_baseline | E4_6years_baseline>`:
  - `counts`: exams, participants, cancers, controls; `dropped_incomplete_items`; `censored_share`; `status` when not analysed.
  - `auroc.<sybil | P | sybil_plus_demographics_crossfit | P_plus_sybil_crossfit | lung_rads>`: `est`, `lo`, `hi`, `se`.
  - `logit_auroc.<same>`: the same on the logit scale (for meta-analysis).
  - `differences.<a>_minus_<b>`: paired AUROC differences with `est`, `lo`, `hi`, `se`; `bootstrap_correlation_auroc_sybil_P`.
  - `auroc_ipcw`: censoring-weighted AUROC of Sybil and P (only when more than 5% are censored).
  - `sybil_coefficient_given_P`: logistic coefficient of logit(Sybil) adjusted for P, with interval.
  - `calibration.<sybil | P>`: `observed_over_expected`, `calibration_intercept`, `calibration_slope`, `brier`, each with interval and SE.
  - `measures_at_cuts.<label>`: `sensitivity`, `specificity`, `ppv`, `false_alarms_per_1000`, `missed_per_1000` (each with interval and SE), and the cut's `threshold`, `rule`, `source` or `note`.
- `compare.case_mix`: exams, participants, age mean and SD, female share, current-smoker share, baseline share, share with a nodule ≥ 4 mm, follow-up median (days), Lung-RADS ≥ 3 share, Lung-RADS 0 count.
- `geometry` (if run): `attrition` (files, unreadable, CT series, axial series kept), `transfer_syntax_counts`, `enhanced_multiframe_series`, `all_axial_series` and `by_maker` (GE, SIEMENS, PHILIPS, CANON/TOSHIBA, OTHER/UNKNOWN) counts by ratio class (slice spacing / slice thickness: ≤ 0.65, 0.65–0.85, 0.85–0.95, 0.95–1.05, > 1.05, 0 or irregular), `studies` (n, with both an overlapping and a contiguous series), `series_sent_to_sybil` and `consecutive_screen_pairs` (only with `--series-manifest`).
