# The returned file: `TO_RETURN/aggregate_report.json`

Every value is an aggregate. Counts below `min_cell` appear as the text `"<min_cell"`; shares appear only when both the count and its complement reach `min_cell` (else `"withheld"`); withheld rates appear as `null` with `"note": "withheld: small cell"`; an endpoint with fewer cancers or controls than `min_cell` reports no count. Geometry counts are rounded to a multiple of 5. A worked example made from the synthetic self-test data is in `examples/`.

- `kit_version`, `compare.site` (the site label you chose, for example "A"), `compare.min_cell`, `compare.cells_suppressed`.
- `compare.site_metadata`: `lung_rads_version`, `nodule_diameter_type`, `cancer_ascertainment` (as given on the command line, else "not stated"), `input` ("nodule table" or "exam table only").
- `compare.form_P1_evaluated`, `compare.form_P6_evaluated` (the 14-item and 11-item forms; false when an item is < 80% complete where it applies) and `compare.form_P1_items_missing_where_applicable`, `compare.form_P6_items_missing_where_applicable`: per item, `"none"` or the share missing among the exams where the item applies (or `"withheld"`; `"<0.01"` for a positive share that rounds to 0).
- `compare.endpoints.<E1_1year_all_screens | E2_1year_baseline | E4_6years_baseline>`:
  - `P_evaluated`; `counts`: exams, participants, cancers, controls; `dropped_incomplete_P_items`; `censored_share`; `status` when not analysed. If E2's numbers could reveal a small count by subtraction from E1 or E4, E2's `counts`, `dropped_incomplete_P_items`, `censored_share` and `measures_at_cuts` are replaced by a `note` (its AUROCs, differences and calibration stay).
  - `auroc.<sybil | P | sybil_plus_demographics_crossfit | P_plus_sybil_crossfit | lung_rads>`: `est`, `lo`, `hi`, `se`.
  - `logit_auroc.<same>`: the same on the logit scale (for meta-analysis).
  - `differences.<a>_minus_<b>`: paired AUROC differences with `est`, `lo`, `hi`, `se`; `bootstrap_correlation_auroc_sybil_P`.
  - `auroc_ipcw`: censoring-weighted AUROC of Sybil and P (only when more than 5% are censored).
  - `sybil_coefficient_given_P`: logistic coefficient of logit(Sybil) adjusted for P, with interval.
  - `calibration.<sybil | P>`: `observed_over_expected`, `log_observed_over_expected`, `calibration_intercept`, `calibration_slope`, `brier`, each with interval and SE.
  - `measures_at_cuts.<label>`: `sensitivity`, `specificity`, `ppv`, `false_alarms_per_1000`, `missed_per_1000` (each with interval and SE), and the cut's `threshold`, `rule`, `source` or `note`.
- `compare.case_mix`: exams and participants (rounded to a multiple of 5), and (only with at least `min_cell` exams, and `min_cell` known values) age mean and SD (one decimal), follow-up median and inter-quartile range (whole days); female share, current-smoker share, baseline share, share with a nodule ≥ 4 mm, Lung-RADS ≥ 3 share and Lung-RADS 0 share.
- `geometry` (if run): `attrition` (files, unreadable, CT series, axial series kept, CT files without a series UID, and series excluded as scout or reformat, fewer than 30 slices, no orientation or thickness, not axial), `transfer_syntax_counts`, `enhanced_multiframe_series`, `all_axial_series` and `by_maker` (GE, SIEMENS, PHILIPS, CANON/TOSHIBA, OTHER/UNKNOWN) counts by ratio class (slice spacing / slice thickness: ≤ 0.65, 0.65–0.85, 0.85–0.95, 0.95–1.05, > 1.05, 0 or irregular), `studies` (n, with both an overlapping and a contiguous series), `series_sent_to_sybil` and `consecutive_screen_pairs` (only with `--series-manifest`), `cells_suppressed`, `note` (the rounding rule; these are counts of CT series and studies, not of people).
- Self-test only: `unit_checks` (known-answer checks of the input coding and the numerics); blocks `compare`, `compare_exam_table_only`, `compare_no_margin_column` and an unrounded `geometry`.

- Phase 2 (v1.1, not in this version): aggregate z-fix results (mean change of the 1-year and 6-year logit, alarm changes) for overlapping series; the fields will be added here before v1.1 is used.
