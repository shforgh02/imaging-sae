# X4: do other open lung-CT AI tools make Sybil's slice-spacing error? (code audit, 2026-11-20)

Question: where does each tool take the voxel size along z (the slice axis) from when it reads a DICOM series: the `SliceThickness` tag (wrong when slices overlap) or the real distance between slice positions (`ImagePositionPatient`; right)? Read from each tool's public source code on GitHub (current default branch, 2026-11-20). Nothing was run.

| Tool | What it is | z spacing taken from | Verdict |
|---|---|---|---|
| **Sybil** (`reginabarzilaygroup/Sybil`, `sybil/serie.py`, branch `main`) | lung cancer risk 1 to 6 years from one LDCT | `thickness = float(dcm.SliceThickness)`; `voxel_spacing = torch.tensor(pixel_spacing + [thickness, 1])`; slice positions used only to sort | **error present in the current version** |
| grt123, Kaggle Data Science Bowl 2017, 1st place (`lfz/DSB2017`, `preprocessing/step1.py`) | lung cancer probability from CT | `np.abs(slices[0].ImagePositionPatient[2] - slices[1].ImagePositionPatient[2])` (then written into `SliceThickness`) | correct |
| Kaggle DSB 2017, 2nd place (`juliandewit/kaggle_ndsb2017`, `step1_preprocess_ndsb.py`) | lung cancer probability from CT | the same position difference | correct |
| MONAI `PydicomReader` (`Project-MONAI/MONAI`, `monai/data/image_reader.py`) | the most used medical-imaging AI framework | average distance between consecutive `ImagePositionPatient` z values; affine from first and last position | correct |
| MONAI `ITKReader` / ITK / SimpleITK | general readers | ITK computes spacing from positions | correct |
| pylidc (`notmatthancock/pylidc`, `pylidc/Scan.py`) | the standard LIDC-IDRI library | `slice_spacing` = median difference of slice z values; its docstring warns that `slice_thickness` "may not be equal to the `slice_spacing`" | correct, with an explicit warning |
| LungEvaty (2025 preprint, weights on Hugging Face, gated) | lung cancer risk 1 to 6 years | code repository not public at the time of the check | not checkable |

**Reading:** among the open tools checked, the error is specific to Sybil. The common libraries and the best-known earlier lung-cancer models compute the spacing from the slice positions, and the LIDC library warns about exactly this difference. So the finding is "a fixable error in one widely discussed model", not "a common pitfall".
