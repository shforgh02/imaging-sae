"""Lung L2, task 5: paper figures from committed result files only (no new analysis; plan docs/FIGURE_PLAN.md). Plain SVG with the helpers and
the validated two-slot palette of s6_figures.py (blue #2a78d6, orange #eb6834; ink and grey from the reference palette).
  fig1_mechanism.svg   (a) schematic of overlapping slices placed at the slice thickness; (b) one public NLST dev exam, coronal, as Sybil sees
                       it and at the true spacing (PNG from fig1_coronal.py, embedded; written OUTSIDE git because it holds CT pixels)
  fig2_flow.svg        study flow from committed counts
  fig5_exposure.svg    how often a chest CT study holds an overlapping series (results/x12), in non-overlapping parts
  fig6_clinical.svg    operating points and threshold transfer on NLST test (results/x9, results/x7, results/s4/s4_u3_dev.json)
usage (venv python): python paper_figures.py <out dir for figures without CT pixels> [--ct-dir <dir with fig1_coronal_*.png and json>]
"""
import argparse
import base64
import json
from pathlib import Path

from s6_figures import BASE, BLUE, GRID, INK, INK2, MUTED, ORANGE, SURF, Svg, ticks

HERE = Path(__file__).resolve().parent


def rect(s, x, y, w, h, fill, stroke="none", sw=0, op=1.0, rx=0):
    s.el.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{fill}" fill-opacity="{op}" stroke="{stroke}" stroke-width="{sw}" rx="{rx}"/>')


def fig1(ct_dir, out):
    """blue = Sybil's reading (SliceThickness), orange = the true spacing (ImagePositionPatient), in both panels. Panel (b) is drawn at TRUE
    physical proportions: Sybil resizes every slice to 256 columns, so one column = resampled pixel x DICOM columns / 256 (1.41 mm here, not the
    0.70 mm in Sybil's volume header; Neon's review), one row = 2.5 mm (Sybil's z voxel; true for the z-fix, 1.25 mm of anatomy for main)."""
    info = json.loads((ct_dir / "fig1_coronal.json").read_text()); s = Svg(1130, 660)
    s.text(20, 28, "Figure 1. Sybil places overlapping slices at the slice thickness, so the chest is stretched along the body axis", 15, weight="bold")
    # (a) schematic: orange = true positions, blue = Sybil
    s.text(20, 62, "a", 14, weight="bold"); s.text(40, 62, "Slices 2.5 mm thick, reconstructed every 1.25 mm (50% overlap)", 12, INK2)
    x0, y0, mm = 60, 92, 9.0                                                   # 9 px per mm
    for xc, step, lab, col in ((x0, 1.25, "True positions (ImagePositionPatient)", ORANGE), (x0 + 200, 2.5, "Where Sybil places them (SliceThickness)", BLUE)):
        s.text(xc - 20, y0 - 10, lab, 11, INK2)
        for k in range(8): rect(s, xc + (k % 2) * 14, y0 + k * step * mm, 110, 2.5 * mm, col, op=0.25, stroke=col, sw=1)
        c0, c1 = y0 + 1.25 * mm, y0 + (7 * step + 1.25) * mm                  # first and last slice centres
        s.line(xc - 10, c0, xc - 10, c1, col, 2); s.text(xc - 14, c1 + 18, f"centre to centre: {7 * step:g} mm", 11, INK)
    s.text(x0 - 20, 322, "The slice step doubles (1.25 -> 2.5 mm), so the anatomy is", 11, INK); s.text(x0 - 20, 338, "stretched 2-fold along the body axis for this protocol.", 11, INK)
    # (b) true physical proportions
    vs = info["sybil_voxel_spacing_after_resample_mm"]; colmm = vs[0] * info["dicom_columns"] / 256; W = 230.0; H = W * (200 * vs[2]) / (256 * colmm)
    s.text(450, 62, "b", 14, weight="bold")
    s.text(470, 62, f"One NLST exam, coronal, Sybil's 200-slice input box ({200 * vs[2]:.0f} mm), drawn at true proportions", 12, INK2)
    yb, flip = 96, info["positions_increase_with_index"]                       # volume index 0 = feet -> flip so the head is up
    ry = lambda r_: (yb + H - (r_ + 0.5) * H / 200) if flip else (yb + (r_ + 0.5) * H / 200)   # noqa: E731
    panels = [(470, "fig1_coronal_main.png", "As Sybil reads it", BLUE, None, info["lung_rows_main"]), (770, "fig1_coronal_zfix.png", "At the true spacing (z-fix)", ORANGE, info["padded_rows_zfix"], info["lung_rows_zfix"])]
    for x, png, title, col, pad, lung in panels:
        b64 = base64.b64encode((ct_dir / png).read_bytes()).decode("ascii")
        tr = f' transform="translate(0,{2 * yb + H:.1f}) scale(1,-1)"' if flip else ""
        s.el.append(f'<image x="{x}" y="{yb}" width="{W:.1f}" height="{H:.1f}" preserveAspectRatio="none" href="data:image/png;base64,{b64}"{tr}/>')
        rect(s, x, yb, W, H, "none", col, 2); s.text(x, yb + H + 20, title, 12, INK, weight="bold")
        if lung: s.line(x - 8, ry(lung[0]), x + W + 8, ry(lung[0]), col, 1.5); s.text(x - 10, ry(lung[0]) + 4, "lung base", 9, INK2, "end")
        if pad:
            rows = sorted(pad); bands, start = [], rows[0]
            for a_, b_ in zip(rows, rows[1:] + [None]):
                if b_ != a_ + 1: bands.append((start, a_)); start = b_
            for r0, r1 in bands:
                ya, yb2 = min(ry(r0), ry(r1)) - H / 400, max(ry(r0), ry(r1)) + H / 400
                s.line(x + W + 8, ya, x + W + 8, yb2, ORANGE, 4); s.text(x + W + 14, (ya + yb2) / 2 + 4, f"{r1 - r0 + 1} padded", 10, INK2)
    tm, tz, nl = info["T_resampled_main"], info["T_resampled_zfix"], info["lung_rows_zfix"]
    s.text(470, yb + H + 36, f"Chest spread over {tm} slices = {tm * vs[2]:.0f} mm as Sybil", 11, INK2)
    s.text(470, yb + H + 51, f"reads it; the box holds {200 * vs[2]:.0f} mm, so {tm - 200} slices", 11, INK2); s.text(470, yb + H + 66, "are cut off (here the lung apex).", 11, INK2)
    s.text(770, yb + H + 36, f"Chest = {tz} slices = {tz * vs[2]:.0f} mm; lungs about {(nl[1] - nl[0] + 1) * vs[2]:.0f} mm;", 11, INK2)
    s.text(770, yb + H + 51, f"{len(info['padded_rows_zfix'])} slices of Sybil's mid-grey padding.", 11, INK2)
    # L-shaped 100 mm x 100 mm scale bar
    sx, sy = 1110, yb + H; s.line(sx, sy, sx - 100 / colmm * W / 256, sy, INK, 2); s.line(sx, sy, sx, sy - 100 / vs[2] * H / 200, INK, 2); s.text(sx - 4, sy - 100 / vs[2] * H / 200 - 6, "100 mm", 10, INK, "end")
    s.text(470, yb + H + 92, f"DICOM: SliceThickness {info['thickness_mm']:g} mm  ·  spacing of ImagePositionPatient {info['true_spacing_mm']:g} mm  ·  ratio {info['ratio']:.2f}  ·  "
                             f"{info['maker']} {info['model']}  ·  {info['n_images']} images", 10, INK)
    for i, t in enumerate(("Cropping is typical (627 of 759 stretched test exams), but the score drop is as large without it (-0.42 uncropped vs -0.36 cropped);",
                           "GE, Philips and Siemens show the same distortion (supplement). The exam is the first of the dev list, chosen without reading any outcome or model output.",
                           "Public NLST series (Imaging Data Commons, CC BY 4.0); coronal plane through the posterior lungs, Sybil's own intensity scale; no model output is shown.")):
        s.text(20, 610 + i * 14, t, 9.5, MUTED)
    s.save(out / "fig1_mechanism.svg")


def ci(s, x1, y1, x2, y2, col, w=1.0, op=0.65):
    s.el.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{col}" stroke-width="{w}" stroke-opacity="{op}"/>')


NAMES = {"lidc_idri": "LIDC-IDRI", "cptac_lscc": "CPTAC-LSCC", "cptac_luad": "CPTAC-LUAD", "covid_19_ny_sbu": "COVID-19-NY-SBU", "cmb_lca": "CMB-LCA"}


def fig5(out):
    """exposure in non-overlapping parts (Neon's assessments): strong overlap without a contiguous alternative, strong overlap with a contiguous
    series in the same study (the series choice decides), moderate overlap only (0.65-0.85; hatched; not in the pre-registered tests); interval of
    the strong total; per-collection series shares on the SAME 0-40% axis (stacked dots)."""
    import csv
    d = json.loads((HERE / "results" / "x12" / "x12_overlap_prevalence.json").read_text())["sets"]
    rows = [("NLST (2002-2004 scanners)", "nlst"), ("Modern scanner models (2013 or later)", "modern_scanner_models"), ("Public chest CT collections (2015 or later)", "modern_collections_2015_on")]
    s = Svg(960, 640); s.text(20, 28, "Figure 5. How often a chest CT study holds an overlapping series (public data, DICOM headers only)", 15, weight="bold")
    s.el.append(f'<defs><pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="6" height="6" fill="{SURF}"/>'
                f'<line x1="0" y1="0" x2="0" y2="6" stroke="{MUTED}" stroke-width="2"/></pattern></defs>')
    px, pw, xmax, top, rh = 330, 520, 0.40, 76, 74
    X = lambda v: px + v / xmax * pw   # noqa: E731
    for tt in ticks(0, xmax, 4):
        s.line(X(tt), top - 14, X(tt), top + 3 * rh - 10, GRID); s.text(X(tt), top + 3 * rh + 4, f"{tt * 100:.0f}%", 10, MUTED, "middle")
    s.text(px, top + 3 * rh + 20, "share of studies", 10, MUTED)
    for ri, (lab, key) in enumerate(rows):
        v = d[key]; y = top + ri * rh; h = 22
        s.text(20, y + 14, lab, 11, INK); s.text(20, y + 29, f"{v['studies']:,} studies, {v['patients']:,} people", 10, MUTED)
        strong, both, mod = v["studies_any_le_0p65"]["share"], v["studies_both_le_0p65_and_contiguous"]["share"], v["studies_any_le_0p85"]["share"] - v["studies_any_le_0p65"]["share"]
        x = px
        for w, fill, stroke in ((strong - both, BLUE, SURF), (both, "#86b6ef", SURF), (mod, "url(#hatch)", MUTED)):
            ww = w / xmax * pw
            if ww > 0: rect(s, x, y, ww, h, fill, stroke, 1)
            x += ww
        lo, hi = v["studies_any_le_0p65"]["lo"], v["studies_any_le_0p65"]["hi"]; yi = y + h + 7
        s.line(X(lo), yi, X(hi), yi, INK, 1.5); s.line(X(lo), yi - 3, X(lo), yi + 3, INK, 1.5); s.line(X(hi), yi - 3, X(hi), yi + 3, INK, 1.5)
        s.text(X(strong) + 4, y - 5, f"strong {strong * 100:.1f}% ({(strong - both) * 100:.1f}% + {both * 100:.1f}%)", 10, INK2)
        s.text(X(strong + mod) + 6, y + 15, f"+ moderate only {mod * 100:.1f}%", 10, MUTED)
    ly = top + 3 * rh + 42
    for i_, (lab, fill, stroke) in enumerate((("strong overlap (spacing / thickness <= 0.65), no contiguous series in the study", BLUE, None),
                                              ("strong overlap, a contiguous series also present (which series is sent to Sybil decides)", "#86b6ef", None),
                                              ("moderate overlap only (0.65 to 0.85): not part of the pre-registered tests (exploratory check only)", "url(#hatch)", MUTED))):
        rect(s, 20, ly + i_ * 18 - 9, 14, 10, fill, stroke or "none", 1 if stroke else 0); s.text(40, ly + i_ * 18, lab, 10, INK2)
    s.text(660, ly, "black line: 95% interval of the strong total", 10, MUTED)
    # per-collection strip on the same axis, stacked dots
    cols = [r_ for r_ in csv.DictReader(open(HERE / "results" / "x12" / "x12_per_collection.csv", encoding="utf-8")) if int(r_["patients"]) >= 20 and r_["collection_id"] != "nlst"]
    sy = ly + 150; s.text(20, sy - 96, f"Each public chest CT collection with 20 or more people ({len(cols)}; NLST excluded): share of its series with strong overlap (all acquisition years)", 10, INK2)
    s.line(px, sy + 4, px + pw, sy + 4, BASE, 1)
    for tt in ticks(0, xmax, 4): s.text(X(tt), sy + 20, f"{tt * 100:.0f}%", 10, MUTED, "middle")
    stack = {}
    for r_ in sorted(cols, key=lambda q: float(q["le_0p65"])):
        v = float(r_["le_0p65"]); b = round(v / 0.005); n = stack.get(b, 0); stack[b] = n + 1
        s.dot(X(min(v, xmax)), sy - 2 - n * 5.5, BLUE, 2.8)
    n0 = sum(1 for r_ in cols if float(r_["le_0p65"]) == 0); s.text(X(0) - 6, sy - 2, f"{n0} at 0%", 9, INK2, "end")
    for j_, r_ in enumerate(sorted(cols, key=lambda q: -float(q["le_0p65"]))[:3]):
        v = float(r_["le_0p65"]); yl = sy - 14 - j_ * 13; s.line(X(v), sy - 6, X(v), yl + 3, BASE, 1)
        s.text(X(v) + 3, yl, f"{NAMES.get(r_['collection_id'], r_['collection_id'])} {v * 100:.0f}%", 9, INK2)
    s.text(20, 620, "Header-only audit of Imaging Data Commons (mostly diagnostic and oncology CT, not screening). Top: study-level shares; strip: series-level shares.", 9, MUTED)
    s.text(20, 633, "Intervals by bootstrap over patients do not capture clustering by site; collections differ widely (strip). Filters and set definitions: Methods and supplement.", 9, MUTED)
    s.save(out / "fig5_exposure.svg")


def mark(s, shape, x, y, fill, r=5, hollow=False):
    f, st = (SURF, fill) if hollow else (fill, SURF)
    if shape == "circle": s.el.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{f}" stroke="{st}" stroke-width="{2 if hollow else 1.5}"/>')
    elif shape == "square": s.el.append(f'<rect x="{x - r:.1f}" y="{y - r:.1f}" width="{2 * r}" height="{2 * r}" fill="{f}" stroke="{st}" stroke-width="{2 if hollow else 1.5}"/>')
    elif shape == "diamond": s.el.append(f'<path d="M{x:.1f},{y - r - 1:.1f} L{x + r + 1:.1f},{y:.1f} L{x:.1f},{y + r + 1:.1f} L{x - r - 1:.1f},{y:.1f} Z" fill="{f}" stroke="{st}" stroke-width="{2 if hollow else 1.5}"/>')
    else: s.el.append(f'<path d="M{x:.1f},{y - r - 1:.1f} L{x + r + 1:.1f},{y + r:.1f} L{x - r - 1:.1f},{y + r:.1f} Z" fill="{f}" stroke="{st}" stroke-width="{2 if hollow else 1.5}"/>')


SCORES = [("sybil", "Sybil", BLUE, "circle"), ("form", "Form (radiologists' findings + age, sex, smoking; fitted on NLST train)", ORANGE, "square"),
          ("brock", "Brock (published; no family history in the public data)", MUTED, "triangle"), ("rule", "Fixed rule: Lung-RADS >= 4A (L4), >= 3 (L3), radiologists' call (R)", INK, "diamond")]
SHORT = {"sybil": "Sybil", "form": "Form", "brock": "Brock"}
RULE = {"L4": "lung_rads_4A", "L3": "lung_rads_3", "R": "radiologists_call"}
RULE_NAME = {"L4": "Lung-RADS >= 4A", "L3": "Lung-RADS >= 3", "R": "call"}


def fig6(out):
    """clinical context (exploratory, all NLST test exams): operating points at dev-matched false-alarm levels (broken x axis so L4 and L3 do not
    collide), 1 year all screens and 6 years baseline, with cancers caught at every level; threshold transfer dev -> test with the dev false
    alarms of the dev-cancer cuts (results/s4/s4_u3_dev.json). Caption facts from the same files (step offsets, 1-year baseline summary)."""
    X9 = {sp: json.loads((HERE / "results" / "x9" / f"x9_rules_thresholds_{sp}.json").read_text())["thresholds"] for sp in ("dev", "test")}
    P5 = json.loads((HERE / "results" / "x7" / "x7_sensitivity_test.json").read_text())["P5_harm_at_dev_cuts"]
    U3 = json.loads((HERE / "results" / "s4" / "s4_u3_dev.json").read_text())["table"]
    s = Svg(1060, 880); s.text(20, 28, "Figure 6. Clinical context on the NLST test split (exploratory): the same false-alarm levels, and cuts set on development data", 14, weight="bold")

    def get(T, key): return T["table"][key]

    def key_of(k, lvl): return RULE[lvl] if k == "rule" else f"{k}@OP_{lvl}"
    for pi, (E, lab, ylo, yhi) in enumerate((("E1", "1 year, all screens", 0.6, 1.0), ("E4", "6 years, baseline screens", 0.2, 0.9))):
        T = X9["test"][E]; c = T["counts"]; px, py, pw, ph = 90 + pi * 510, 96, 400, 290
        if pi == 0: s.text(20, py - 36, "a", 14, weight="bold")
        s.text(px, py - 36, f"{lab}: {c['exams']:,} exams, {c['cancers']} cancers ({c['prevalence'] * 100:.1f}%)", 12, INK)

        def X(v):   # broken axis: 0-175 | 310-420 (the gap is compressed)
            if v <= 175: return px + v / 175 * 0.58 * pw
            if v < 310: return px + (0.58 + (v - 175) / 135 * 0.06) * pw
            return px + (0.64 + (min(v, 420) - 310) / 110 * 0.36) * pw
        Y = lambda v: py + ph - (min(max(v, ylo), yhi) - ylo) / (yhi - ylo) * ph   # noqa: E731
        for tt in (0, 50, 100, 150, 325, 350, 375, 400): s.line(X(tt), py, X(tt), py + ph, GRID); s.text(X(tt), py + ph + 14, str(tt), 10, MUTED, "middle")
        gx = X(242); s.line(gx - 6, py + ph + 4, gx - 2, py + ph - 4, INK2, 1.5); s.line(gx + 2, py + ph + 4, gx + 6, py + ph - 4, INK2, 1.5)
        for tt in ticks(ylo, yhi, 4): s.line(px, Y(tt), px + pw, Y(tt), GRID); s.text(px - 6, Y(tt) + 4, f"{tt * 100:.0f}%", 10, MUTED, "end")
        s.text(px + pw / 2, py + ph + 30, "false alarms per 1,000 exams (axis broken between 175 and 310)", 10, INK2, "middle"); s.text(px - 58, py - 12, "sensitivity", 10, INK2)
        for lvl in ("L4", "L3", "R"):
            xs = []
            for key, name, col, shp in SCORES:
                r_ = get(T, key_of(key, lvl)); se, fa = r_["sensitivity"], r_["fa_per_1000_exams"]
                ci(s, X(fa["lo"]), Y(se["est"]), X(fa["hi"]), Y(se["est"]), col); ci(s, X(fa["est"]), Y(se["lo"]), X(fa["est"]), Y(se["hi"]), col)
                mark(s, shp, X(fa["est"]), Y(se["est"]), col); xs.append(fa["est"])
            s.text(X(sum(xs) / len(xs)), py - 10, lvl, 11, INK2, "middle", "bold")
        for li, lvl in enumerate(("L4", "L3", "R")):
            parts = [f"{SHORT[k]} {get(T, key_of(k, lvl))['counts']['tp']}" for k in ("sybil", "form", "brock")] + [f"{RULE_NAME[lvl]} {get(T, RULE[lvl])['counts']['tp']}"]
            s.text(px, py + ph + 50 + li * 14, f"{lvl}, cancers caught of {c['cancers']}: " + ", ".join(parts), 10, INK2)
    for i_, (key, name, col, shp) in enumerate(SCORES): mark(s, shp, 40 + (i_ % 2) * 510, 508 + (i_ // 2) * 18, col); s.text(52 + (i_ % 2) * 510, 512 + (i_ // 2) * 18, name, 10, INK2)

    def step(E):   # Sybil's achieved dev false-alarm share at R vs the target (its score has steps)
        r_ = get(X9["dev"][E], "sybil@OP_R")["counts"]; return 100 * r_["fp"] / (r_["fp"] + r_["tn"]), 100 * X9["dev"][E]["operating_points"]["OP_R"]["dev_false_alarm_share"]
    (a1, t1), (a4, t4) = step("E1"), step("E4"); E2 = X9["test"]["E2"]; c2 = E2["counts"]["cancers"]
    tp2 = lambda k: get(E2, k)["counts"]["tp"]; fa2 = lambda k: get(E2, k)["fa_per_1000_exams"]["est"]   # noqa: E731
    notes = ["Levels: cuts set on cancer-free DEV exams to the dev false-alarm share of Lung-RADS >= 4A (L4), >= 3 (L3) and the radiologists' call (R). Lines: 95% participant-bootstrap intervals.",
             f"Sybil's score has steps: at R its dev false-alarm share was {a1:.1f}% (target {t1:.1f}%) at 1 year and {a4:.1f}% (target {t4:.1f}%) at 6 years, part of its lower false alarms there.",
             "1 year: the form and the fixed rules use the radiologists' reads, which also triggered the work-up (not blind to the outcome). 6 years at baseline avoids the prior-scan advantage and",
             "reduces 1-year work-up bias, but Lung-RADS and Brock score nodules only: 55 of the 131 six-year cancers (7 of 86 one-year) had no nodule >= 4 mm on the scan.",
             "Lung-RADS and Brock were reconstructed from the NLST forms (part-solid size assumed; Brock without family history).",
             f"1 year, baseline screens only ({c2} cancers): at L3 Sybil {tp2('sybil@OP_L3')}, form {tp2('form@OP_L3')}, Lung-RADS >= 3 {tp2('lung_rads_3')}; at R Sybil {tp2('sybil@OP_R')} "
             f"({fa2('sybil@OP_R'):.0f} false alarms per 1,000), form {tp2('form@OP_R')} ({fa2('form@OP_R'):.0f}), call {tp2('radiologists_call')} ({fa2('radiologists_call'):.0f})."]
    for i_, n_ in enumerate(notes): s.text(20, 556 + i_ * 13, n_, 9, MUTED)
    # (b) threshold transfer, 1 year all screens
    s.text(20, 660, "b", 14, weight="bold"); s.text(40, 660, "Threshold transfer, 1 year, all screens: development (hollow) -> test (filled)", 12, INK)
    g1 = "cut set on cancer-free dev exams (L3): false alarms transfer; dev sensitivity was inflated for Sybil"
    g2 = "cut matched on dev CANCERS (to the radiologists' dev sensitivity): false alarms not matched; Sybil's sensitivity collapses"
    rows = []
    for key, nm, col, shp in (("sybil", "Sybil", BLUE, "circle"), ("form", "Form", ORANGE, "square"), ("rule", "Lung-RADS >= 3", INK, "diamond")):
        d_, t_ = get(X9["dev"]["E1"], key_of(key, "L3")), get(X9["test"]["E1"], key_of(key, "L3"))
        rows.append((g1, nm, col, shp, d_["sensitivity"]["est"], t_["sensitivity"]["est"], d_["fa_per_1000_exams"]["est"], t_["fa_per_1000_exams"]["est"], t_["counts"]["tp"]))
    for nm, col, shp, tk, uk in (("Sybil", BLUE, "circle", "sybil", "sybil"), ("Form", ORANGE, "square", "C1_form", "form_F")):
        r_ = P5["rad"]["table"][tk]; rows.append((g2, nm, col, shp, U3[uk]["sensitivity"], r_["sensitivity"], U3[uk]["fa_per_1000"], r_["fa_per_1000_exams"], r_["cancers_caught"]))
    rows.append((g2, "Radiologists' call", INK, "diamond", U3["radiologists"]["sensitivity"], P5["radiologists_test_sensitivity"], U3["radiologists"]["fa_per_1000"], P5["radiologists_fa_per_1000_exams"],
                 round(P5["radiologists_test_sensitivity"] * 86)))
    bx, bw, by = 330, 300, 676; Xb = lambda v: bx + (v - 0.5) / 0.5 * bw   # noqa: E731
    ys, grp, y = [], None, by
    for g, *_ in rows:
        if g != grp: y += 18; grp = g
        ys.append(y); y += 19
    bottom = ys[-1] + 10
    for tt in (0.5, 0.6, 0.7, 0.8, 0.9, 1.0): s.line(Xb(tt), by + 8, Xb(tt), bottom, GRID); s.text(Xb(tt), bottom + 13, f"{tt * 100:.0f}%", 10, MUTED, "middle")
    s.text(bx + bw / 2, bottom + 26, "sensitivity", 10, INK2, "middle"); s.text(bx + bw + 24, by + 10, "false alarms per 1,000, dev -> test; cancers caught on test", 10, INK2)
    grp = None
    for i_, (g, nm, col, shp, sd, st, fd, ft, tp) in enumerate(rows):
        y = ys[i_]
        if g != grp: s.text(20, y - 15, g, 10, INK2, weight="bold"); grp = g
        s.text(200, y + 4, nm, 10, INK); s.line(Xb(sd), y, Xb(st), y, col, 2); mark(s, shp, Xb(sd), y, col, 5, hollow=True); mark(s, shp, Xb(st), y, col, 5)
        s.text(bx + bw + 24, y + 4, f"{fd:.0f} -> {ft:.0f};  sensitivity {sd * 100:.0f}% -> {st * 100:.0f}%  ({tp}/86)", 10, INK2)
    s.text(20, 872, "Dev results flatter Sybil: Sybil's developers selected the model on this split, so its dev sensitivity is optimistic and a cut tuned to dev cancers sits too high on new data.", 9, MUTED)
    s.save(out / "fig6_clinical.svg")


def fig3(out):
    """the six pre-registered hypotheses (test = confirmatory, blue; dev = discovery, grey) with the exploratory external LIDC-IDRI replication
    (orange) on H1, H2, H6; H3 drawn as not confirmed; H7 tagged partly seen. Sources: results/s6/s6_test.json, results/s5/s6_dev_as_if_test.json,
    results/x5/x5_lidc.json."""
    from s6_figures import fmt
    T = {h["id"]: h for h in json.loads((HERE / "results" / "s6" / "s6_test.json").read_text())["hypotheses"]}
    D = {h["id"]: h for h in json.loads((HERE / "results" / "s5" / "s6_dev_as_if_test.json").read_text())["hypotheses"]}
    L = {h["id"]: h for h in json.loads((HERE / "results" / "x5" / "x5_lidc.json").read_text())["replication"]["hypotheses"]}
    names = dict(H1=("H1  the z-fix moves the score", "share of exams moving >= 1/4 SD (test: > 30%)"), H2=("H2  the z-fix lowers the score", "mean change of the 1-year logit (test: < -0.1)"),
                 H3=("H3  the z-fix changes the alarm", "share of exams whose alarm changes (test: > 5%)"), H4=("H4  a kernel change rarely changes the alarm", "share of kernel pairs whose alarm changes (test: < 5%)"),
                 H6=("H6  shared axis 0 carries the drop", "logit carried by axis 0 (test: > 0.2)"), H7=("H7  follow-up jump when the stretch changes", "b, consecutive yearly screens (test: > 0.1)"))
    s = Svg(1000, 560); s.text(20, 28, "Figure 3. The six pre-registered hypotheses (Holm over six, one-sided) and the external replication on LIDC-IDRI", 15, weight="bold")
    for i_, (lab, col) in enumerate((("NLST test (confirmatory)", BLUE), ("NLST dev (discovery)", MUTED), ("LIDC-IDRI, 7 centres (exploratory replication)", ORANGE))):
        s.dot(30 + i_ * 250, 52, col); s.text(40 + i_ * 250, 56, lab, 11, INK2)
    for k, hid in enumerate(("H1", "H2", "H3", "H4", "H6", "H7")):
        t, d = T[hid], D[hid]; x0, y0, w = 20 + (k % 3) * 325, 84 + (k // 3) * 220, 305
        rows = [("test", t["est"], *t["ci95"], BLUE), ("dev", d["est"], *d["ci95"], MUTED)] + ([("LIDC-IDRI", L[hid]["est"], *L[hid]["ci95"], ORANGE)] if hid in L else [])
        ok = t["confirmed_holm"]
        if not ok:
            s.el.append(f'<rect x="{x0 - 8}" y="{y0 - 18}" width="{w + 6}" height="200" fill="none" stroke="{MUTED}" stroke-width="1.5" stroke-dasharray="5,4" rx="6"/>')
        s.text(x0, y0, names[hid][0], 12, INK if ok else MUTED, weight="bold"); s.text(x0, y0 + 15, names[hid][1], 10, INK2)
        vals = [v for r_ in rows for v in r_[1:4]] + [t["null"]]; a, b = min(vals), max(vals); pad = (b - a) * 0.15 or 0.1; a, b = a - pad, b + pad
        lx, rx = x0 + 80, x0 + w - 10; Xh = lambda v: lx + (v - a) / (b - a) * (rx - lx)   # noqa: E731
        top = y0 + 34; rh = 26; bot = top + rh * len(rows) + 6
        for tt in ticks(a, b): s.line(Xh(tt), top, Xh(tt), bot, GRID); s.text(Xh(tt), bot + 14, fmt(tt), 10, MUTED, "middle")
        s.line(Xh(t["null"]), top - 4, Xh(t["null"]), bot, INK2, 1.5); s.text(Xh(t["null"]), top - 7, f"null {fmt(t['null'])}", 10, INK2, "middle")
        for i_, (lab, est, cl, ch, col) in enumerate(rows):
            y = top + rh * i_ + rh / 2 + 2; s.text(x0, y + 4, lab, 11, INK2); s.line(Xh(cl), y, Xh(ch), y, col, 2); s.dot(Xh(est), y, col)
        pv = t["p_one_sided"]; ptxt = "p < 0.001" if pv < 0.001 else f"p = {pv:.3f}"
        res = (f"confirmed (Holm), one-sided {ptxt}" if ok else f"NOT CONFIRMED (one-sided p = {pv:.2f})")
        s.text(x0, bot + 32, res, 10, INK if ok else MUTED, weight="bold" if not ok else "normal")
        if hid == "H7": s.text(x0, bot + 46, "partly seen before the freeze; 121 of the 134 changed pairs involve GE", 9, MUTED)
        if hid == "H3": s.text(x0, bot + 46, "alarm discordance 4.5%; the z-fix loses more alarms than it adds", 9, MUTED)
    s.text(20, 535, "Test: 759 z-fix exams (342 participants) for H1-H3 and H6; 500 kernel pairs for H4; 4,353 consecutive-screen pairs (134 changed) for H7. LIDC-IDRI: 197 scans,", 9.5, MUTED)
    s.text(20, 549, "one per patient (GE 134, Philips 46, Siemens 17), no cancer outcome, Holm over its three tests, exploratory. Intervals: 95% participant bootstrap.", 9.5, MUTED)
    s.save(out / "fig3_hypotheses.svg")


def box(s, x, y, w, lines, edge=BASE, head=None, h=None):
    hh = h or 16 * len(lines) + 14; rect(s, x, y, w, hh, SURF, edge, 1.5, rx=6)
    for i, (t, size, col, wt) in enumerate(lines): s.text(x + 10, y + 20 + i * 16, t, size, col, weight=wt)
    return hh


def arrow(s, x1, y1, x2, y2):
    s.line(x1, y1, x2, y2, INK2, 1.5); s.el.append(f'<path d="M{x2:.1f},{y2:.1f} l-4,-8 l8,0 Z" fill="{INK2}"/>' if x1 == x2 else "")


def fig2(out):
    """study flow from committed counts: lung_l0/results/l0_results.json, results/s6/assemble_test.json, the dev assemble record (logged),
    results/manifest_unseen.csv tiers, results/manifest_lidc.csv (X5)."""
    L0 = json.loads((HERE.parent / "lung_l0" / "results" / "l0_results.json").read_text()); P = L0["participants"]; C = L0["counts_all_screens"]
    AT = json.loads((HERE / "results" / "s6" / "assemble_test.json").read_text())
    import csv
    U = list(csv.DictReader(open(HERE / "results" / "manifest_unseen.csv", encoding="utf-8")))
    u1 = [r_ for r_ in U if r_["tier"] == "U1"]; u2 = [r_ for r_ in U if r_["tier"] == "U2"]
    nl = sum(1 for _ in csv.DictReader(open(HERE / "results" / "manifest_lidc.csv", encoding="utf-8")))
    s = Svg(1060, 560); s.text(20, 28, "Figure 2. Study flow", 15, weight="bold")
    B, I, M = (INK, "bold"), (INK2, "normal"), (MUTED, "normal")
    box(s, 300, 50, 420, [(f"NLST, CT arm (public tables, IDC): {P['ct_arm_in_public_table']:,} participants", 12, *B),
                          ("CT images and DICOM headers from IDC; outcomes from the NLST tables", 10, *I)])
    arrow(s, 510, 98, 510, 128); s.line(130, 128, 930, 128, INK2, 1.5)
    cols = [(20, "Sybil's train split", [f"{P['by_group']['train']:,} participants, {C['train']['exams']:,} exams", "Sybil was trained here (by its developers)", "we fit only the radiologists' forms (F, P) here"], BASE),
            (280, "Sybil's dev split", [f"{P['by_group']['dev']:,} participants; 7,336 series scored", "Sybil's model selection split: in-sample", "our discovery work; X11 (mechanism, no outcome)"], BASE),
            (540, "Sybil's test split (held out)", [f"{P['by_group']['test']:,} participants; {AT['n_main']:,} series scored", f"+ {AT['n_zfix']} z-fix runs, {AT['n_pair']} kernel pairs", f"1-year outcome: {AT['outcomes']['y1']['pos'] + AT['outcomes']['y1']['neg']:,} exams, {AT['outcomes']['y1']['pos']} cancers",
                                                   "six pre-registered tests; exploratory X1-X10"], BLUE),
            (800, "Never used by Sybil (O2)", [f"{P['by_group']['unseen']:,} participants, {C['unseen']['exams']:,} exams", f"lists: U1 {len(u1):,} series, U2 {len(u2):,} series", "pre-registered; scoring from 1 Dec 2026", f"(cancer-poor: {C['unseen']['participants_with_later_cancer']} with a later cancer)"], ORANGE)]
    for x, title, lines, edge in cols:
        arrow(s, x + 120, 128, x + 120, 150)
        box(s, x, 150, 240, [(title, 11, *B)] + [(t, 10, *I) for t in lines], edge=edge)
    s.text(20, 290, "All NLST groups are the same trial (33 US centres, 2002-2004 enrolment): every NLST result is internal testing, including O2.", 10, INK2)
    box(s, 20, 320, 480, [("LIDC-IDRI (7 US academic centres; clinical CT, not screening)", 11, *B),
                          (f"{nl} scans with overlapping slices (one per patient; GE 134, Philips 46, Siemens 17)", 10, *I),
                          ("external replication of the mechanism only (no cancer outcome)", 10, *I)], edge=BLUE)
    box(s, 540, 320, 480, [("Imaging Data Commons, all chest CT (DICOM headers only)", 11, *B),
                           ("how common overlapping series are today (X12); no model run", 10, *I),
                           ("NLST collection licence CC BY 4.0; LIDC-IDRI CC BY 3.0", 10, *M)])
    s.text(20, 430, "Selection rules, exclusions at each step and the cut-offs are in the protocol (section 5), O2_PLAN.md and RESULTS_L2.md 3d, 3i.", 10, MUTED)
    s.text(20, 446, "Blue edge: confirmatory results (test) and the external mechanism replication; orange edge: pre-registered, not yet run.", 10, MUTED)
    s.save(out / "fig2_flow.svg")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("out"); ap.add_argument("--ct-dir"); a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    fig2(out); fig3(out); fig5(out); fig6(out)
    if a.ct_dir: fig1(Path(a.ct_dir), Path(a.ct_dir))                          # Figure 1 holds CT pixels: written next to the PNGs, outside git
    print("figures written")


if __name__ == "__main__":
    main()
