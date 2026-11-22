"""Partner kit v1.0: a synthetic dataset for --selftest (random numbers only; no real person). Deterministic (seed 0).
make(folder) -> (exams.csv, nodules.csv, dicom folder). The DICOM files hold headers only (no pixel data) and test the geometry audit:
one overlapping series (2.5 / 1.25 mm), one contiguous (1.25 / 1.25), one moderate (1.0 / 0.75), and one scout that must be excluded.
"""
from pathlib import Path

import numpy as np
import pandas as pd


def make(folder):
    folder = Path(folder); folder.mkdir(parents=True, exist_ok=True); rng = np.random.default_rng(0)
    n_part = 1500; rows, nods = [], []
    for i in range(n_part):
        age, sex, smk, emph = int(rng.integers(55, 75)), rng.choice(["M", "F"]), rng.choice(["Y", "N"]), rng.choice(["Y", "N"], p=[0.3, 0.7])
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
            if has:
                for j in range(int(rng.integers(1, 3))):
                    nods.append(dict(exam_id=ex, diameter_mm=d if j == 0 else float(np.round(rng.uniform(2, d), 1)), type=rng.choice(["solid", "part-solid", "ground-glass"], p=[0.8, 0.1, 0.1]),
                                     spiculated=rng.choice(["Y", "N"], p=[0.1, 0.9]), lobe=rng.choice(["RUL", "RML", "RLL", "LUL", "lingula", "LLL"]), calcified="N",
                                     growth=("Y" if (r > 0 and rng.random() < 0.1) else "N"), new=("Y" if (r > 0 and rng.random() < 0.1) else "N")))
    ex_p, no_p = folder / "exams.csv", folder / "nodules.csv"
    pd.DataFrame(rows).to_csv(ex_p, index=False, lineterminator="\n"); pd.DataFrame(nods).to_csv(no_p, index=False, lineterminator="\n")
    dc = folder / "dicom"; _dicom(dc)
    return ex_p, no_p, dc


def _dicom(dc):
    import pydicom
    from pydicom.dataset import FileDataset, FileMetaDataset
    from pydicom.uid import ExplicitVRLittleEndian
    specs = [("1.2.826.0.1.3680043.10.999.1", "GE MEDICAL SYSTEMS", 2.5, 1.25, ["ORIGINAL", "PRIMARY", "AXIAL"]),
             ("1.2.826.0.1.3680043.10.999.2", "SIEMENS", 1.25, 1.25, ["ORIGINAL", "PRIMARY", "AXIAL"]),
             ("1.2.826.0.1.3680043.10.999.3", "Philips", 1.0, 0.75, ["ORIGINAL", "PRIMARY", "AXIAL"]),
             ("1.2.826.0.1.3680043.10.999.4", "SIEMENS", 1.0, 1.0, ["ORIGINAL", "PRIMARY", "LOCALIZER"])]
    for s_uid, maker, thick, step, itype in specs:
        d_ = dc / s_uid[-1]; d_.mkdir(parents=True, exist_ok=True)
        for k in range(40):
            meta = FileMetaDataset(); meta.TransferSyntaxUID = ExplicitVRLittleEndian; meta.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.1.1.2"
            meta.MediaStorageSOPInstanceUID = f"{s_uid}.{k + 1}"
            ds = FileDataset(str(d_ / f"{k:03d}.dcm"), {}, file_meta=meta, preamble=b"\0" * 128)
            ds.Modality = "CT"; ds.SeriesInstanceUID = s_uid; ds.StudyInstanceUID = "1.2.826.0.1.3680043.10.999.0" if s_uid[-1] in "12" else "1.2.826.0.1.3680043.10.999.9"
            ds.SOPInstanceUID = meta.MediaStorageSOPInstanceUID; ds.SOPClassUID = meta.MediaStorageSOPClassUID; ds.Manufacturer = maker; ds.ImageType = itype
            ds.SliceThickness = thick; ds.ImageOrientationPatient = [1, 0, 0, 0, 1, 0]; ds.ImagePositionPatient = [0.0, 0.0, -k * step]
            ds.is_little_endian = True; ds.is_implicit_VR = False; ds.save_as(str(d_ / f"{k:03d}.dcm"), write_like_original=False)
