"""Lung L2: series-selection rule for an NLST exam (one CT study), from scan metadata only (IDC index 25.0.5).

The rule is learned to reproduce the split file's choice of test series (Shetty et al. / Ardila et al. 2019), so that dev exams are
represented by the same kind of series as the test exams. It never reads an outcome and never reads Sybil's annotations
(Sybil's own dev rule prefers an annotated series, and annotations exist only for cancers: that would leak the label).

Candidate rules (a small family fixed before evaluation; the one with the best exact agreement on half A of the test participants is
kept and then checked on half B):
  count : most slices, then sharper kernel, then lower series number
  thin  : thinnest slices, then sharper kernel, then most slices, then lower series number
  thin_soft : thinnest, then SOFTER kernel, then most slices (control: shows the kernel preference matters)
  sharp_thin : sharper kernel class, then thinnest, then most slices
  count_thin : most slices, then thinnest, then sharper kernel
Every rule first drops localizers (ImageType contains LOCALIZER) and series with fewer than MIN_SLICES images.
"""
import re

import numpy as np
import pandas as pd

MIN_SLICES = 40          # below this a series cannot be a chest volume at <= 10 mm; Sybil's own min_num_images is not public in the args
COLS = ["PatientID", "StudyInstanceUID", "SeriesInstanceUID", "StudyDate", "Modality", "Manufacturer", "ManufacturerModelName",
        "SeriesDescription", "SeriesNumber", "instanceCount", "ImageType", "SliceThickness", "ConvolutionKernel", "KVP",
        "XRayTubeCurrent_max", "Exposure_max", "ReconstructionDiameter", "PixelSpacing_row_mm", "GantryDetectorTilt",
        "vg_regularly_spaced_3d_volume", "vg_slice_spacing_mm", "series_size_MB", "series_aws_url"]

GE = {"SOFT": 0, "STANDARD": 1, "DETAIL": 2, "BONE": 3, "BONEPLUS": 3, "EDGE": 4, "LUNG": 4}


def kernel_sharpness(manufacturer, kernel):
    """within-vendor sharpness score (higher = sharper). Comparable only inside one study (one scanner)."""
    k = str(kernel).upper().strip()
    mf = str(manufacturer).upper()
    if "GE" in mf:
        return float(GE.get(k, np.nan))
    if "SIEMENS" in mf:
        mm = re.match(r"[BCDHI](\d\d)", k)
        return float(mm.group(1)) / 10 if mm else np.nan
    if "TOSHIBA" in mf:
        mm = re.match(r"FC(\d\d)", k)
        return float(mm.group(1)) / 10 if mm else np.nan
    if "PHILIPS" in mf:
        return float("ABCDEFGHIJKL".index(k[0])) if k[:1] in "ABCDEFGHIJKL" else np.nan
    return np.nan


def kernel_class(manufacturer, kernel):
    """'sharp' or 'soft' (or 'unknown'), the class used for the 'equivalent series' check and as a technical covariate."""
    s = kernel_sharpness(manufacturer, kernel)
    mf = str(manufacturer).upper()
    if np.isnan(s):
        return "unknown"
    cut = {"GE": 3, "SIEMENS": 4.5, "TOSHIBA": 3.0, "PHILIPS": 3}
    for key, c in cut.items():
        if key in mf:
            return "sharp" if s >= c else "soft"
    return "unknown"


def load_meta(path):
    m = pd.read_csv(path, usecols=COLS, dtype={"PatientID": str}, low_memory=False)
    m = m[m.Modality == "CT"].copy()
    m["is_localizer"] = m.ImageType.astype(str).str.upper().str.contains("LOCALIZER")
    m["sharp"] = [kernel_sharpness(a, b) for a, b in zip(m.Manufacturer, m.ConvolutionKernel)]
    m["kclass"] = [kernel_class(a, b) for a, b in zip(m.Manufacturer, m.ConvolutionKernel)]
    m["study_yr"] = pd.to_datetime(m.StudyDate, errors="coerce").dt.year - 1999
    m["thick"] = m.SliceThickness.round(2)
    return m


RULES = {
    "count": [("instanceCount", False), ("sharp", False), ("SeriesNumber", True)],
    "thin": [("thick", True), ("sharp", False), ("instanceCount", False), ("SeriesNumber", True)],
    "thin_soft": [("thick", True), ("sharp", True), ("instanceCount", False), ("SeriesNumber", True)],
    "sharp_thin": [("kclass_sharp", False), ("thick", True), ("instanceCount", False), ("SeriesNumber", True)],
    "count_thin": [("instanceCount", False), ("thick", True), ("sharp", False), ("SeriesNumber", True)],
}


BEST_RULE = "sharp_thin"   # chosen on half A of the test participants on 2026-11-13 (results/s0_series_rule.json); fixed from then on


def candidates(m):
    c = m[~m.is_localizer & (m.instanceCount >= MIN_SLICES)].copy()
    c["kclass_sharp"] = (c.kclass == "sharp").astype(int)
    c["sharp"] = c.sharp.fillna(-1)
    c["SeriesNumber"] = pd.to_numeric(c.SeriesNumber, errors="coerce").fillna(9999)
    return c


def select(m, rule):
    """one series per study by the named rule; returns the chosen rows (one per StudyInstanceUID)."""
    keys = RULES[rule]
    c = candidates(m).sort_values([k for k, _ in keys] + ["SeriesInstanceUID"], ascending=[a for _, a in keys] + [True])
    return c.groupby("StudyInstanceUID", sort=False).head(1)
