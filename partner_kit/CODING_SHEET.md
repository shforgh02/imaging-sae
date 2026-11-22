# Coding sheet: the input tables

One row per **screening CT exam** (annual or scheduled screens only; leave out short-interval follow-up scans done within about 8 months of a previous screen). CSV, UTF-8, comma-separated, header row. Values Y/N may also be 1/0 or TRUE/FALSE. Leave a cell empty when it is unknown (never invent a value). Dates are not used: give days.

## `exams.csv` (required)
| Column | Meaning | Values |
|---|---|---|
| `participant_id` | a pseudonymous id, the same for all exams of one person (stays local) | text |
| `exam_id` | unique id of the exam (stays local) | text |
| `screen_round` | 0 = first (baseline) screen, 1 = next annual screen, … (the kit caps it at 2, as in NLST) | integer |
| `age` | age in years at this exam | number |
| `sex` | M or F | M / F |
| `current_smoker` | currently smoking at this exam | Y / N |
| `emphysema` | emphysema reported on this CT | Y / N |
| `sybil_1yr`, `sybil_6yr` | Sybil's published (calibrated) risk of lung cancer within 1 and 6 years for this exam, from the series you actually send to Sybil | 0 to 1 |
| `days_to_cancer` | days from this exam to a lung cancer diagnosis; empty if none | number |
| `days_to_last_followup` | days from this exam to the last date the person is known to be cancer-free or alive (registry linkage preferred) | number |
| `lung_rads` | optional: the reported Lung-RADS category | 0, 1, 2, 3, 4A, 4B, 4X (S/C suffixes allowed) |

If you have **no nodule table**, add for the largest non-calcified nodule of the exam: `max_diameter_mm` (longest axial diameter in mm; **0 if there is no nodule** (nodules < 4 mm count as none); leave it empty only when the size is unknown, which makes every nodule item of that exam unknown), `nodule_type` (solid / part-solid / ground-glass), `spiculated` (Y/N), `upper_lobe` (Y/N; right or left upper lobe; the lingula is not "upper", as in the NLST form), `n_nodules_ge4mm`, and for repeat screens `growth` (Y/N: any nodule grew since the previous screen) and `new_nodule` (Y/N: any new nodule).

## `nodules.csv` (optional; preferred when you have nodule-level records)
One row per recorded nodule: `exam_id`, `diameter_mm` (longest axial diameter in mm) **or** `volume_mm3` (converted in the kit to the sphere-equivalent diameter (6V/π)^(1/3)), `type` (solid / part-solid / ground-glass), `spiculated` (Y/N), `lobe` (RUL, RML, RLL, LUL, lingula, LLL), `calcified` (Y/N; calcified nodules are left out), `growth` (Y/N), `new` (Y/N). The kit keeps nodules ≥ 4 mm, takes the largest as "the" nodule, counts all ≥ 4 mm, and sets growth / new to "no" when an exam has no nodule.

## Notes on matching NLST
- The form was fitted on NLST, where radiologists recorded the **longest** axial diameter of non-calcified nodules **≥ 4 mm**. If your records give only the mean diameter (Lung-RADS v1.1 / v2022) or only volume, say so to the study lead; the kit uses what you give and the difference is analysed centrally.
- Lung-RADS category 0 (incomplete) is counted and not used as a score.
- The kit warns if diameters look like centimetres (median below 2.5).
