"""M0 decisions and report (docs/MRI_M0M1_PROTOCOL.md section 4), from results/m0_prep_summary.json (written by cloud/m0_prep_modal.py)
plus the pinned marksheet. Rules applied exactly as fixed: ADC units, token size per outline source (smaller wins), outline
materiality within RUMC (ISUP-grade-matched volume ratio, 0.8-1.25), and the QC flag list. Writes results/m0_decisions.json and RESULTS_M0.md.
usage: D:\\Shayan\\imgsae\\.venv\\Scripts\\python.exe imgsae\\mri\\m0_report.py
"""
import io
import json
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent; RES = HERE / "results"
COMMIT = "ce4a4723d7c46d882a6cbaacb40ed6c4be86282f"
SIZES = (8, 6, 4); RECALL_MIN = 0.90; MAT_LO, MAT_HI = 0.8, 1.25; MIN_PER_GRADE = 5


def marksheet():
    url = f"https://raw.githubusercontent.com/DIAGNijmegen/picai_labels/{COMMIT}/clinical_information/marksheet.csv"
    M = pd.read_csv(io.BytesIO(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "imgsae-m0"}), timeout=120).read()), dtype=str)
    M["key"] = M.patient_id + "_" + M.study_id; return M.set_index("key")


def recall_by_source(S, pos):
    out = {}
    for src in ("Pooch25", "resampled"):
        ks = [k for k in pos if S[k]["source"] == src]
        out[src] = {str(mm): dict(n_lesions=int(sum(S[k]["recall"][str(mm)]["n_lesions"] for k in ks)),
                                  n_captured=int(sum(S[k]["recall"][str(mm)]["n_captured"] for k in ks)),
                                  n_small=int(sum(S[k]["recall"][str(mm)]["n_small"] for k in ks)), n_studies=len(ks)) for mm in SIZES}
        for mm in SIZES:
            d = out[src][str(mm)]; d["recall"] = d["n_captured"] / d["n_lesions"] if d["n_lesions"] else float("nan")
    return out


def token_size(rec):
    """per source: the largest size with recall >= 0.90 (4 mm if none); the smaller of the per-source sizes is used."""
    per = {}
    for src, r in rec.items():
        ok = [mm for mm in SIZES if np.isfinite(r[str(mm)]["recall"]) and r[str(mm)]["recall"] >= RECALL_MIN]
        per[src] = max(ok) if ok else 4
    return min(per.values()), per


def materiality(S, M, pos, seed=0, B=2000):
    """RUMC dev positives: per case_ISUP grade with >= 5 studies per source, ratio of median total lesion volume (Pooch25 / resampled);
    weighted geometric mean (weight = smaller count). Bootstrap CI (studies resampled within source x grade), descriptive."""
    rows = [dict(key=k, src=S[k]["source"], isup=int(M.loc[k, "case_ISUP"]), vol=S[k]["lesion_ml_total"]) for k in pos if M.loc[k, "center"] == "RUMC"]
    D = pd.DataFrame(rows); per = []
    for g, d in D.groupby("isup"):
        a, b = d[d.src == "Pooch25"].vol.to_numpy(), d[d.src == "resampled"].vol.to_numpy()
        per.append(dict(isup=int(g), n_pooch=len(a), n_resampled=len(b),
                        median_pooch=float(np.median(a)) if len(a) else float("nan"), median_resampled=float(np.median(b)) if len(b) else float("nan"),
                        used=bool(len(a) >= MIN_PER_GRADE and len(b) >= MIN_PER_GRADE)))
    used = [p for p in per if p["used"]]

    def wgm(groups):
        w = np.array([min(len(a), len(b)) for a, b in groups], float); r = np.array([np.median(a) / np.median(b) for a, b in groups])
        return float(np.exp((w * np.log(r)).sum() / w.sum()))
    if not used: return dict(per_grade=per, ratio=float("nan"), material=None, note="no ISUP grade with >= 5 studies per source")
    grp = [(D[(D.isup == p["isup"]) & (D.src == "Pooch25")].vol.to_numpy(), D[(D.isup == p["isup"]) & (D.src == "resampled")].vol.to_numpy()) for p in used]
    ratio = wgm(grp); rng = np.random.default_rng(seed)
    bs = [wgm([(rng.choice(a, len(a)), rng.choice(b, len(b))) for a, b in grp]) for _ in range(B)]
    return dict(per_grade=per, ratio=ratio, ci95=[float(np.quantile(bs, .025)), float(np.quantile(bs, .975))],
                material=bool(not (MAT_LO <= ratio <= MAT_HI)), rule=f"material if outside {MAT_LO}-{MAT_HI}")


def main():
    P = json.load(open(RES / "m0_prep_summary.json")); S = dict(P["studies"]); M = marksheet()
    qcd = json.load(open(RES / "m0_qc_decisions.json")) if (RES / "m0_qc_decisions.json").exists() else {"excluded": []}
    excluded = sorted(qcd.get("excluded", []))
    for k in excluded: S.pop(k, None)   # QC exclusions (label-blind decisions) apply to every M0 number
    split = json.load(open(HERE / "data" / "split.json")); dev = sorted(split["dev_studies"])
    pos = [k for k in dev if k in S and M.loc[k, "case_csPCa"] == "YES"]
    empty_pos = [k for k in pos if S[k]["lesion_ml_total"] == 0]
    src_pos = pd.Series([S[k]["source"] for k in pos]).value_counts().to_dict()
    src_by_centre = pd.crosstab(pd.Series([M.loc[k, "center"] for k in pos], name="centre"), pd.Series([S[k]["source"] for k in pos], name="source"))
    adc50 = np.array([S[k]["adc_p1_p50_p99_gland"][1] for k in S if np.isfinite(S[k]["adc_p1_p50_p99_gland"][1])])
    adc_med = float(np.median(adc50)); adc_ok = bool(500 <= adc_med <= 3000)
    rec = recall_by_source(S, pos); size, per_src = token_size(rec)
    mat = materiality(S, M, pos)
    dg = np.array([S[k]["dice_gland"] for k in S]); dzn = np.array([S[k]["dice_zone"] for k in S])
    flagged = sorted(k for k in S if S[k].get("flagged"))
    masks = {}
    for k in S:
        for m, info in S[k]["masks"].items():
            key = f"{m}|{S[k]['source']}" if m == "lesion" else m; d = masks.setdefault(key, dict(values=set(), not_on_t2w_grid=0, n=0))
            d["values"].update(info["values"]); d["n"] += 1; d["not_on_t2w_grid"] += int(not info["on_t2w_grid"])
    masks = {k: dict(values=sorted(v["values"]), n=v["n"], not_on_t2w_grid=v["not_on_t2w_grid"]) for k, v in sorted(masks.items())}
    sp = pd.DataFrame([dict(sx=S[k]["geometry"]["t2w"]["spacing"][0], sz=S[k]["geometry"]["t2w"]["spacing"][2], nz=S[k]["n_slices"]) for k in S])
    dec = dict(
        counts=dict(n_dev=P["n_dev"], n_processed=len(P["studies"]), excluded_by_qc=excluded, n_used=len(S), errors=P["errors"], n_dev_positive=len(pos), positives_by_source=src_pos,
                    positives_by_centre_source={c: r.to_dict() for c, r in src_by_centre.iterrows()}, positives_with_empty_mask=empty_pos),
        adc_units=dict(median_gland_p50=adc_med, ok_1e6_mm2_s=adc_ok, window=[0, 3000] if adc_ok else None),
        token_size=dict(chosen_mm=size, per_source_mm=per_src, recall=rec, rule="per source largest size with recall >= 0.90; the smaller wins; 4 mm if none"),
        materiality=mat,
        qc=dict(n_flagged=len(flagged), flagged=flagged, gland_dice_median=float(np.nanmedian(dg)), gland_dice_p05=float(np.nanpercentile(dg, 5)),
                zone_dice_median=float(np.nanmedian(dzn)), zone_dice_p05=float(np.nanpercentile(dzn, 5)), random_qc=P["random_qc"]),
        masks=masks, t2w_geometry=dict(inplane_mm_median=float(sp.sx.median()), inplane_mm_range=[float(sp.sx.min()), float(sp.sx.max())],
                                       slice_mm_median=float(sp.sz.median()), slice_mm_range=[float(sp.sz.min()), float(sp.sz.max())],
                                       crop_slices_median=float(sp.nz.median()), crop_slices_range=[int(sp.nz.min()), int(sp.nz.max())]))
    json.dump(dec, open(RES / "m0_decisions.json", "w"), indent=1, default=float)
    L = ["# M0 results: prostate MRI (PI-CAI), dev half", "", "Protocol `docs/MRI_M0M1_PROTOCOL.md` (fixed before running). Generated by `m0_report.py`.", "",
         "## Counts", f"- Dev studies: {P['n_dev']}; processed: {len(P['studies'])}; errors: {len(P['errors'])}; excluded by the label-blind QC: "
         f"{len(excluded)} {excluded}; used: {len(S)}.",
         f"- Dev csPCa-positive studies: {len(pos)}; by outline source: {src_pos}; positives with an empty lesion mask: {len(empty_pos)}.",
         "- Positives by centre and source:", "", "| Centre | " + " | ".join(src_by_centre.columns) + " |", "|---|" + "---|" * len(src_by_centre.columns),
         *[f"| {c} | " + " | ".join(str(int(v)) for v in r) + " |" for c, r in src_by_centre.iterrows()], "",
         "## ADC units", f"- Median of the gland ADC 50th percentile: {adc_med:.0f} → units 10⁻⁶ mm²/s: **{adc_ok}** (window 0–3,000).", "",
         "## Token size (lesion recall, lesions ≥ 0.02 ml)", "", "| Source | " + " | ".join(f"{mm} mm" for mm in SIZES) + " |", "|---|" + "---|" * len(SIZES)]
    for src, r in rec.items():
        L.append(f"| {src} ({r['8']['n_studies']} studies) | " + " | ".join(f"{r[str(mm)]['recall']:.3f} ({r[str(mm)]['n_captured']}/{r[str(mm)]['n_lesions']})" for mm in SIZES) + " |")
    L += ["", f"- Per source: {per_src} → **chosen: {size} mm**.", "", "## Outline materiality (RUMC dev positives)", "",
          "| ISUP | n Pooch25 | n resampled | median ml Pooch25 | median ml resampled | used |", "|---|---|---|---|---|---|"]
    for p in mat["per_grade"]:
        L.append(f"| {p['isup']} | {p['n_pooch']} | {p['n_resampled']} | {p['median_pooch']:.2f} | {p['median_resampled']:.2f} | {p['used']} |")
    L += ["", f"- Weighted ratio {mat.get('ratio', float('nan')):.2f} (CI {mat.get('ci95')}) → **material: {mat.get('material')}** ({mat.get('rule', mat.get('note'))}).", "",
          "## Gland and zone QC", f"- Gland Dice median {dec['qc']['gland_dice_median']:.3f} (5th pct {dec['qc']['gland_dice_p05']:.3f}); zone Dice median "
          f"{dec['qc']['zone_dice_median']:.3f} (5th pct {dec['qc']['zone_dice_p05']:.3f}).",
          f"- Flagged for the label-blind visual check (gland Dice < 0.8 or zone Dice < 0.7): {len(flagged)}. Decisions: `results/m0_qc_decisions.json`.",
          "- Decisions: " + "; ".join(f"{k}: {v['decision']}" for k, v in qcd.get("decisions", {}).items()) + ".",
          "- Extra label-blind screen (added after M0 ran; AI gland / reported volume outside 0.5–2.0): "
          + "; ".join(f"{k}: {v['decision']} (ratio {v['ratio']})" for k, v in qcd.get("extra_screen", {}).get("decisions", {}).items()) + ".", "",
          "## Masks (values, grids)", "", "| Mask | values | n | not on T2W grid |", "|---|---|---|---|"]
    for k, v in masks.items(): L.append(f"| {k} | {v['values']} | {v['n']} | {v['not_on_t2w_grid']} |")
    g = dec["t2w_geometry"]
    L += ["", "## T2W geometry", f"- In-plane spacing median {g['inplane_mm_median']:.3f} mm (range {g['inplane_mm_range']}); slice spacing median "
          f"{g['slice_mm_median']:.2f} mm (range {g['slice_mm_range']}); crop slices median {g['crop_slices_median']:.0f} (range {g['crop_slices_range']})."]
    if P["errors"]: L += ["", "## Errors", ""] + [f"- {k}: {v}" for k, v in sorted(P["errors"].items())]
    (HERE / "RESULTS_M0.md").write_text("\n".join(L) + "\n", encoding="utf-8"); print("\n".join(L))


if __name__ == "__main__":
    main()
