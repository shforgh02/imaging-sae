"""Partner kit v1.0: a synthetic dataset for --selftest (random numbers only; no real person). Deterministic (seed 0).
make(folder) -> (exams.csv with a nodule table, nodules.csv, exams_only.csv with awkward codings, dicom folder, series manifest).
nodules.csv also holds volume-only rows (diameter blank), calcified nodules larger than the largest non-calcified one (to be left out) and
spelled-out lobes ("Right Upper Lobe", "left upper", "lingula"). exams_only.csv uses 1/0 with blanks, spelled-out nodule types ("part solid",
"ground glass"), numeric and suffixed Lung-RADS ("4AS ", "4B C", "0") and blank cells, to test the input coding. The DICOM files hold headers
only: an overlapping series (2.5 / 1.25 mm), a contiguous one (1.25 / 1.25), a moderate one (1.0 / 0.75), a scout that must be excluded, an
Enhanced multi-frame CT series with its geometry in the shared group (2.0 / 1.0) and one with it in the per-frame groups (1.5 / 1.5).
"""
from pathlib import Path

import numpy as np
import pandas as pd


def make(folder):
    folder = Path(folder); folder.mkdir(parents=True, exist_ok=True); rng = np.random.default_rng(0)
    rows, nods, rows2 = [], [], []
    for i in range(1500):
        age, sex, smk, emph = int(rng.integers(55, 75)), str(rng.choice(["M", "F"])), str(rng.choice(["Y", "N"])), str(rng.choice(["Y", "N"], p=[0.3, 0.7]))
        risk = rng.normal(-5.0, 1.0); k_rounds = int(rng.integers(1, 4))
        for r in range(k_rounds):
            ex = f"X{i:05d}_{r}"; has = rng.random() < 0.45; d = float(np.round(rng.gamma(2.0, 3.0) + 2, 1)) if has else 0.0
            lp = risk + (0.25 * d if has else 0) + (0.5 if smk == "Y" else 0); p = 1 / (1 + np.exp(-lp)); ca = rng.random() < p * 3
            fu = float(rng.integers(200, 2600)); dca = float(rng.integers(30, 2400)) if ca else np.nan
            if ca and dca > fu: fu = dca
            s1 = float(np.clip(1 / (1 + np.exp(-(lp + rng.normal(0, 0.8)))), 0, 1)); s6 = float(np.clip(1 / (1 + np.exp(-(lp + 1.2 + rng.normal(0, 0.8)))), 0, 1))
            lr = "1" if not has else ("2" if d < 6 else ("3" if d < 8 else ("4A" if d < 15 else "4B")))
            rows.append(dict(participant_id=f"P{i:05d}", exam_id=ex, screen_round=r, age=age + r, sex=sex, current_smoker=smk, emphysema=emph,
                             sybil_1yr=round(s1, 6), sybil_6yr=round(s6, 6), days_to_cancer=dca, days_to_last_followup=fu, lung_rads=lr))
            typ, spic, lobe = str(rng.choice(["solid", "part-solid", "ground-glass"], p=[0.8, 0.1, 0.1])), str(rng.choice(["Y", "N"], p=[0.1, 0.9])), str(rng.choice(["RUL", "RML", "RLL", "LUL", "lingula", "LLL"]))
            grow, new = ("Y" if (r > 0 and has and rng.random() < 0.1) else "N"), ("Y" if (r > 0 and has and rng.random() < 0.1) else "N")
            if has:
                lobe_txt = {"RUL": "Right Upper Lobe", "LUL": "left upper"}.get(lobe, lobe) if rng.random() < 0.3 else lobe
                for j in range(int(rng.integers(1, 3))):
                    dj = d if j == 0 else float(np.round(rng.uniform(2, d), 1)); vol_only = rng.random() < 0.05
                    nods.append(dict(exam_id=ex, diameter_mm="" if vol_only else dj, volume_mm3=round(np.pi / 6 * dj ** 3, 3) if vol_only else "", type=typ if j == 0 else "solid",
                                     spiculated=spic if j == 0 else "N", lobe=lobe_txt if j == 0 else "RLL", calcified="N", growth=grow if j == 0 else "N", new=new if j == 0 else "N"))
                if rng.random() < 0.05:   # a calcified granuloma larger than every non-calcified nodule: must be left out
                    nods.append(dict(exam_id=ex, diameter_mm=d + 5, volume_mm3="", type="solid", spiculated="N", lobe="RLL", calcified="Y", growth="N", new="N"))
            # the same exam in an exam-only table with awkward codings
            yn10 = lambda v: "" if rng.random() < 0.02 else ("1" if v == "Y" else "0")   # noqa: E731
            lr2 = {"4A": "4AS ", "4B": "4B C"}.get(lr, lr) if rng.random() < 0.5 else lr
            if rng.random() < 0.01: lr2 = "0"
            rows2.append(dict(participant_id=f"P{i:05d}", exam_id=ex, screen_round=r, age=age + r, sex={"M": "male", "F": "Female"}[sex] if rng.random() < 0.3 else sex,
                              current_smoker=yn10(smk), emphysema=yn10(emph), max_diameter_mm=d if has else (float(np.round(rng.uniform(1, 3.9), 1)) if rng.random() < 0.2 else 0),
                              nodule_type={"solid": "Solid", "part-solid": "part solid", "ground-glass": "ground glass"}[typ] if has else "",
                              spiculated=yn10(spic) if has else "", upper_lobe=("1" if lobe in ("RUL", "LUL") else "0") if has else "",
                              n_nodules_ge4mm=(1 if has else 0), growth=(yn10(grow) if has else ""), new_nodule=(yn10(new) if has else ""),
                              sybil_1yr=round(s1, 6), sybil_6yr=round(s6, 6), days_to_cancer=dca, days_to_last_followup=fu, lung_rads=lr2))
    ex_p, no_p, ex2_p = folder / "exams.csv", folder / "nodules.csv", folder / "exams_only.csv"
    pd.DataFrame(rows).to_csv(ex_p, index=False, lineterminator="\n"); pd.DataFrame(nods).to_csv(no_p, index=False, lineterminator="\n")
    pd.DataFrame(rows2).to_csv(ex2_p, index=False, lineterminator="\n", encoding="utf-8-sig")
    dc = folder / "dicom"; _dicom(dc)
    man = folder / "series_manifest.csv"
    pd.DataFrame(dict(series_uid=["1.2.826.0.1.3680043.10.999.1", "1.2.826.0.1.3680043.10.999.2"], participant_id=["S1", "S1"], screen_round=[0, 1])).to_csv(man, index=False, lineterminator="\n")
    return ex_p, no_p, ex2_p, dc, man


def _dicom(dc):
    from pydicom.dataset import Dataset, FileDataset, FileMetaDataset
    from pydicom.sequence import Sequence
    from pydicom.uid import ExplicitVRLittleEndian
    specs = [("1.2.826.0.1.3680043.10.999.1", "GE MEDICAL SYSTEMS", 2.5, 1.25, ["ORIGINAL", "PRIMARY", "AXIAL"]),
             ("1.2.826.0.1.3680043.10.999.2", "SIEMENS", 1.25, 1.25, ["ORIGINAL", "PRIMARY", "AXIAL"]),
             ("1.2.826.0.1.3680043.10.999.3", "Philips", 1.0, 0.75, ["ORIGINAL", "PRIMARY", "AXIAL"]),
             ("1.2.826.0.1.3680043.10.999.4", "SIEMENS", 1.0, 1.0, ["ORIGINAL", "PRIMARY", "LOCALIZER"])]

    def base(path, s_uid, sop_uid, sop_class):
        meta = FileMetaDataset(); meta.TransferSyntaxUID = ExplicitVRLittleEndian; meta.MediaStorageSOPClassUID = sop_class; meta.MediaStorageSOPInstanceUID = sop_uid
        ds = FileDataset(str(path), {}, file_meta=meta, preamble=b"\0" * 128); ds.Modality = "CT"; ds.SeriesInstanceUID = s_uid; ds.SOPInstanceUID = sop_uid; ds.SOPClassUID = sop_class
        ds.is_little_endian = True; ds.is_implicit_VR = False; return ds
    for s_uid, maker, thick, step, itype in specs:
        d_ = dc / s_uid[-1]; d_.mkdir(parents=True, exist_ok=True)
        for k in range(40):
            ds = base(d_ / f"{k:03d}.dcm", s_uid, f"{s_uid}.{k + 1}", "1.2.840.10008.5.1.4.1.1.2")
            ds.StudyInstanceUID = "1.2.826.0.1.3680043.10.999.0" if s_uid[-1] in "12" else "1.2.826.0.1.3680043.10.999.9"
            ds.Manufacturer = maker; ds.ImageType = itype; ds.SliceThickness = thick; ds.ImageOrientationPatient = [1, 0, 0, 0, 1, 0]; ds.ImagePositionPatient = [0.0, 0.0, -k * step]
            ds.save_as(str(d_ / f"{k:03d}.dcm"), write_like_original=False)
    s_uid = "1.2.826.0.1.3680043.10.999.5"; d_ = dc / "5"; d_.mkdir(parents=True, exist_ok=True)
    ds = base(d_ / "enhanced.dcm", s_uid, f"{s_uid}.1", "1.2.840.10008.5.1.4.1.1.2.1"); ds.StudyInstanceUID = "1.2.826.0.1.3680043.10.999.8"; ds.Manufacturer = "SIEMENS"
    ds.ImageType = ["ORIGINAL", "PRIMARY", "AXIAL"]; ds.NumberOfFrames = 40
    sh = Dataset(); pm = Dataset(); pm.SliceThickness = 2.0; pm.PixelSpacing = [0.7, 0.7]; po = Dataset(); po.ImageOrientationPatient = [1, 0, 0, 0, 1, 0]
    sh.PixelMeasuresSequence = Sequence([pm]); sh.PlaneOrientationSequence = Sequence([po]); ds.SharedFunctionalGroupsSequence = Sequence([sh]); frames = []
    for k in range(40):
        fr = Dataset(); pp = Dataset(); pp.ImagePositionPatient = [0.0, 0.0, -k * 1.0]; fr.PlanePositionSequence = Sequence([pp]); frames.append(fr)
    ds.PerFrameFunctionalGroupsSequence = Sequence(frames); ds.save_as(str(d_ / "enhanced.dcm"), write_like_original=False)
    # Enhanced CT with the geometry in the per-frame groups only (thickness 1.5, spacing 1.5)
    s_uid = "1.2.826.0.1.3680043.10.999.6"; d_ = dc / "6"; d_.mkdir(parents=True, exist_ok=True)
    ds = base(d_ / "enhanced_pf.dcm", s_uid, f"{s_uid}.1", "1.2.840.10008.5.1.4.1.1.2.1"); ds.StudyInstanceUID = "1.2.826.0.1.3680043.10.999.7"; ds.Manufacturer = "SIEMENS"
    ds.ImageType = "ORIGINAL\\PRIMARY\\AXIAL"; ds.NumberOfFrames = "40"; ds.SharedFunctionalGroupsSequence = Sequence([Dataset()]); frames = []
    for k in range(40):
        fr = Dataset(); pp = Dataset(); pp.ImagePositionPatient = [0.0, 0.0, -k * 1.5]; pm = Dataset(); pm.SliceThickness = 1.5; po = Dataset(); po.ImageOrientationPatient = [1, 0, 0, 0, 1, 0]
        fr.PlanePositionSequence = Sequence([pp]); fr.PixelMeasuresSequence = Sequence([pm]); fr.PlaneOrientationSequence = Sequence([po]); frames.append(fr)
    ds.PerFrameFunctionalGroupsSequence = Sequence(frames); ds.save_as(str(d_ / "enhanced_pf.dcm"), write_like_original=False)
