"""Lung L2, task 5: paper figures from committed result files only (no new analysis; plan docs/FIGURE_PLAN.md). Plain SVG with the helpers and
the validated two-slot palette of s6_figures.py (blue #2a78d6, orange #eb6834; ink and grey from the reference palette).
  fig1_mechanism.svg   (a) schematic of overlapping slices placed at the slice thickness; (b) one public NLST dev exam, coronal, as Sybil sees
                       it and at the true spacing (PNG from fig1_coronal.py, embedded; written OUTSIDE git because it holds CT pixels)
  fig6_exposure.svg    share of studies with a strongly (<= 0.65) or moderately (<= 0.85) overlapping series, and with both an overlapping and
                       a contiguous series (results/x12/x12_overlap_prevalence.json)
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
    info = json.loads((ct_dir / "fig1_coronal.json").read_text()); s = Svg(1010, 740)
    s.text(20, 28, "Figure 1. Sybil places overlapping slices at the slice thickness, so the chest is stretched along the body axis", 15, weight="bold")
    # (a) schematic
    s.text(20, 62, "a", 14, weight="bold"); s.text(40, 62, "Slices 2.5 mm thick, reconstructed every 1.25 mm (overlap 50%)", 12, INK2)
    x0, y0, mm = 70, 90, 9.0                                                   # 9 px per mm
    for col, (xc, step, lab) in enumerate(((x0, 1.25, "True positions (ImagePositionPatient)"), (x0 + 210, 2.5, "Where Sybil places them (SliceThickness)"))):
        s.text(xc - 20, y0 - 8, lab, 11, INK2)
        for k in range(8):
            top = y0 + k * step * mm; rect(s, xc + (k % 2) * 14, top, 110, 2.5 * mm, BLUE if col == 0 else ORANGE, op=0.28, stroke=BLUE if col == 0 else ORANGE, sw=1)
        h = (7 * step + 2.5) * mm; s.line(xc - 10, y0, xc - 10, y0 + h, INK2, 1.5); s.text(xc - 14, y0 + h + 16, f"{7 * step + 2.5:g} mm", 11, INK, "start")
    s.text(x0, 330, "Eight slices cover 11.25 mm of chest, but Sybil spreads them over 20 mm:", 11, INK); s.text(x0, 346, "the anatomy is stretched 2-fold in z for this protocol.", 11, INK)
    # (b) the two coronal images, same scale in Sybil's frame (columns 0.703 mm, rows 2.5 mm as Sybil assumes), head up
    vs = info["sybil_voxel_spacing_after_resample_mm"]; W = 190.0; H = 200 * vs[2] / vs[0] * (W / 256)
    s.text(470, 62, "b", 14, weight="bold"); s.text(490, 62, f"One NLST exam ({info['maker']}, {info['thickness_mm']:g} mm every {info['true_spacing_mm']:g} mm), coronal, Sybil's 200-slice input", 12, INK2)
    bx = [(490, "fig1_coronal_main.png", "As Sybil reads it", f"{info['T_resampled_main']} slices of chest for a 200-slice box:", "lung apex and base cut off", info["padded_rows_main"]),
          (720, "fig1_coronal_zfix.png", "At the true spacing (z-fix)", f"{info['T_resampled_zfix']} slices of chest; {len(info['padded_rows_zfix'])} padded slices", "(Sybil's mid-grey padding)", info["padded_rows_zfix"])]
    yb = 110; flip = info["positions_increase_with_index"]                       # index 0 = feet end -> flip so the head is up
    for x, png, t1, t2, t3, pad in bx:
        b64 = base64.b64encode((ct_dir / png).read_bytes()).decode("ascii")
        tr = f' transform="translate(0,{2 * yb + H:.1f}) scale(1,-1)"' if flip else ""
        s.el.append(f'<image x="{x}" y="{yb}" width="{W:.1f}" height="{H:.1f}" preserveAspectRatio="none" href="data:image/png;base64,{b64}"{tr}/>')
        rect(s, x, yb, W, H, "none", INK2, 1)
        s.text(x, yb + H + 18, t1, 12, INK, weight="bold"); s.text(x, yb + H + 34, t2, 11, INK2); s.text(x, yb + H + 48, t3, 11, INK2)
        if pad:                                                                # bracket the padding bands
            rows = sorted(pad); bands, start = [], rows[0]
            for a_, b_ in zip(rows, rows[1:] + [None]):
                if b_ != a_ + 1: bands.append((start, a_)); start = b_
            for r0, r1 in bands:
                y_a, y_b = (yb + H - (r1 + 1) * H / 200, yb + H - r0 * H / 200) if flip else (yb + r0 * H / 200, yb + (r1 + 1) * H / 200)
                s.line(x + W + 6, y_a, x + W + 6, y_b, ORANGE, 3)
        else:
            for yy in (yb, yb + H): s.line(x - 6, yy, x + W + 6, yy, BLUE, 3)  # the box edges cut the stretched chest
    sb = 100 / vs[2] * H / 200; s.line(950, yb + H, 950, yb + H - sb, INK, 2); s.text(958, yb + H - sb / 2 - 4, "100 mm", 10, INK); s.text(958, yb + H - sb / 2 + 9, "(as Sybil", 9, MUTED)
    s.text(958, yb + H - sb / 2 + 20, "assumes)", 9, MUTED)
    s.text(470, 730, "Orange bars: padded slices. Blue lines: box edges cutting the chest. Public NLST series (IDC); no model output is shown.", 10, MUTED)
    s.save(out / "fig1_mechanism.svg")


def fig6(out):
    d = json.loads((HERE / "results" / "x12" / "x12_overlap_prevalence.json").read_text())["sets"]
    rows = [("NLST (2002-2004 scanners)", "nlst"), ("Modern scanner models (2013 or later)", "modern_scanner_models"), ("Public chest CT collections from 2015", "modern_collections_2015_on")]
    s = Svg(920, 420); s.text(20, 28, "Figure 6. How often a chest CT study holds an overlapping series (public data, header only)", 15, weight="bold")
    panels = [(["Studies with a series of", "slice spacing / thickness"], [("<= 0.65 (strong overlap)", "studies_any_le_0p65", BLUE), ("<= 0.85 (moderate or strong)", "studies_any_le_0p85", ORANGE)], 0.40),
              (["Studies with BOTH a strongly overlapping", "and a contiguous series (series choice decides)"], [("both present", "studies_both_le_0p65_and_contiguous", BLUE)], 0.12)]
    x_lab, top = 20, 80
    for pi, (title, series, xmax) in enumerate(panels):
        px, pw = (300, 270) if pi == 0 else (620, 250)
        s.text(px, top - 24, title[0], 11, INK2); s.text(px, top - 10, title[1], 11, INK2)
        for t in ticks(0, xmax, 3):
            xx = px + t / xmax * pw; s.line(xx, top, xx, top + 3 * 80, GRID); s.text(xx, top + 3 * 80 + 14, f"{t * 100:.0f}%", 10, MUTED, "middle")
        for ri, (lab, key) in enumerate(rows):
            yc = top + 30 + ri * 80
            if pi == 0: s.text(x_lab, yc + 4, lab, 11, INK); s.text(x_lab, yc + 19, f"{d[key]['studies']:,} studies, {d[key]['patients']:,} people", 10, MUTED)
            for si, (slab, k, col) in enumerate(series):
                v = d[key][k]; y = yc - 8 + si * 18 if len(series) == 2 else yc
                s.line(px + v["lo"] / xmax * pw, y, px + min(v["hi"], xmax) / xmax * pw, y, col, 2); s.dot(px + v["share"] / xmax * pw, y, col)
                s.text(px + min(v["hi"], xmax) / xmax * pw + 8, y + 4, f"{v['share'] * 100:.1f}%", 10, INK2)
    for si, (slab, k, col) in enumerate(panels[0][1]): s.dot(310 + si * 200, top + 3 * 80 + 42, col); s.text(320 + si * 200, top + 3 * 80 + 46, slab, 10, INK2)
    s.text(20, 405, "Dots: share of studies; lines: 95% intervals (bootstrap over patients). Series selection, filters and sets as in RESULTS_L2.md 3i.", 10, MUTED)
    s.save(out / "fig6_exposure.svg")


def fig5(out):
    """exposure in non-overlapping parts (Neon's assessment): strong overlap without a contiguous alternative, strong overlap with a contiguous
    series in the same study (the series choice decides), moderate overlap only (0.65-0.85; hatched; tested in X11 only); interval on the strong
    total; a strip of per-collection series shares."""
    import csv
    d = json.loads((HERE / "results" / "x12" / "x12_overlap_prevalence.json").read_text())["sets"]
    rows = [("NLST (2002-2004 scanners)", "nlst"), ("Modern scanner models (2013 or later)", "modern_scanner_models"), ("Public chest CT collections from 2015", "modern_collections_2015_on")]
    s = Svg(940, 470); s.text(20, 28, "Figure 5. How often a chest CT study holds an overlapping series (public data, DICOM headers only)", 15, weight="bold")
    s.el.append(f'<defs><pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="6" height="6" fill="{SURF}"/>'
                f'<line x1="0" y1="0" x2="0" y2="6" stroke="{MUTED}" stroke-width="2"/></pattern></defs>')
    px, pw, xmax, top, rh = 330, 520, 0.40, 70, 70
    for t in ticks(0, xmax, 4):
        xx = px + t / xmax * pw; s.line(xx, top - 6, xx, top + 3 * rh - 10, GRID); s.text(xx, top + 3 * rh + 4, f"{t * 100:.0f}%", 10, MUTED, "middle")
    s.text(px, top + 3 * rh + 20, "share of studies", 10, MUTED)
    for ri, (lab, key) in enumerate(rows):
        v = d[key]; y = top + ri * rh; h = 22
        s.text(20, y + 14, lab, 11, INK); s.text(20, y + 29, f"{v['studies']:,} studies, {v['patients']:,} people", 10, MUTED)
        strong, both, mod = v["studies_any_le_0p65"]["share"], v["studies_both_le_0p65_and_contiguous"]["share"], v["studies_any_le_0p85"]["share"] - v["studies_any_le_0p65"]["share"]
        parts = [(strong - both, BLUE, None), (both, "#86b6ef", None), (mod, "url(#hatch)", MUTED)]; x = px
        for w, fill, stroke in parts:
            ww = w / xmax * pw
            if ww > 0: rect(s, x, y, max(ww - 2, 0.5), h, fill, stroke or "none", 1 if stroke else 0)
            x += ww
        lo, hi = v["studies_any_le_0p65"]["lo"], v["studies_any_le_0p65"]["hi"]; yi = y + h + 7
        s.line(px + lo / xmax * pw, yi, px + hi / xmax * pw, yi, INK2, 1.5)
        s.text(px + strong / xmax * pw + 4, y - 4, f"strong {strong * 100:.1f}%", 10, INK2)
        s.text(px + (strong + mod) / xmax * pw + 6, y + 15, f"+ moderate {mod * 100:.1f}%", 10, MUTED)
    ly = top + 3 * rh + 40
    for i, (lab, fill, stroke) in enumerate((("strong overlap (ratio <= 0.65), no contiguous series in the study", BLUE, None),
                                             ("strong overlap, a contiguous series also present (the series sent to Sybil decides)", "#86b6ef", None),
                                             ("moderate overlap only (0.65 to 0.85): effect tested in X11 only", "url(#hatch)", MUTED))):
        rect(s, 20, ly + i * 18 - 9, 14, 10, fill, stroke or "none", 1 if stroke else 0); s.text(40, ly + i * 18, lab, 10, INK2)
    s.text(560, ly - 2, "black line: 95% interval of the strong total", 10, MUTED)
    # per-collection strip (collections with >= 20 patients; series level)
    cols = [r_ for r_ in csv.DictReader(open(HERE / "results" / "x12" / "x12_per_collection.csv", encoding="utf-8")) if int(r_["patients"]) >= 20 and r_["collection_id"] != "nlst"]
    sy = ly + 78; s.text(20, sy, f"Per collection ({len(cols)} public chest CT collections with >= 20 people, NLST excluded): share of series with strong overlap", 10, INK2)
    for t in (0, 0.25, 0.5):
        xx = px + t / 0.5 * pw; s.text(xx, sy + 34, f"{t * 100:.0f}%", 10, MUTED, "middle")
    s.line(px, sy + 18, px + pw, sy + 18, BASE, 1)
    for r_ in cols: s.dot(px + min(float(r_["le_0p65"]), 0.5) / 0.5 * pw, sy + 18, BLUE, 3.5)
    s.text(20, 462, "Header-only audit of IDC (mostly diagnostic and oncology CT, not screening); study-level shares; intervals by bootstrap over patients. Filters and sets: RESULTS_L2.md 3i.", 9, MUTED)
    s.save(out / "fig5_exposure.svg")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("out"); ap.add_argument("--ct-dir"); a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    fig5(out)
    if a.ct_dir: fig1(Path(a.ct_dir), Path(a.ct_dir))                          # Figure 1 holds CT pixels: written next to the PNGs, outside git
    print("figures written")


if __name__ == "__main__":
    main()
