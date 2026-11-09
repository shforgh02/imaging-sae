"""TotalSegmentator v2 concept atlas (fixed before any fit): 117 leaf structures -> 43 group concepts (primary level).
Classes: 'path' for kidney cysts (voxel-level pathology), 'anat' for everything else. Tokens with no structure >= 0.2 are 'other' (not scored
as a concept). Adjacency for the chimera rule is data-driven from masks only (see adjacency()).
"""
from __future__ import annotations

import re

import numpy as np

LEAVES = ("spleen kidney_right kidney_left gallbladder liver stomach pancreas adrenal_gland_right adrenal_gland_left lung_upper_lobe_left "
          "lung_lower_lobe_left lung_upper_lobe_right lung_middle_lobe_right lung_lower_lobe_right esophagus trachea thyroid_gland small_bowel "
          "duodenum colon urinary_bladder prostate kidney_cyst_left kidney_cyst_right sacrum vertebrae_S1 vertebrae_L5 vertebrae_L4 vertebrae_L3 "
          "vertebrae_L2 vertebrae_L1 vertebrae_T12 vertebrae_T11 vertebrae_T10 vertebrae_T9 vertebrae_T8 vertebrae_T7 vertebrae_T6 vertebrae_T5 "
          "vertebrae_T4 vertebrae_T3 vertebrae_T2 vertebrae_T1 vertebrae_C7 vertebrae_C6 vertebrae_C5 vertebrae_C4 vertebrae_C3 vertebrae_C2 "
          "vertebrae_C1 heart aorta pulmonary_vein brachiocephalic_trunk subclavian_artery_right subclavian_artery_left common_carotid_artery_right "
          "common_carotid_artery_left brachiocephalic_vein_left brachiocephalic_vein_right atrial_appendage_left superior_vena_cava "
          "inferior_vena_cava portal_vein_and_splenic_vein iliac_artery_left iliac_artery_right iliac_vena_left iliac_vena_right humerus_left "
          "humerus_right scapula_left scapula_right clavicula_left clavicula_right femur_left femur_right hip_left hip_right spinal_cord "
          "gluteus_maximus_left gluteus_maximus_right gluteus_medius_left gluteus_medius_right gluteus_minimus_left gluteus_minimus_right "
          "autochthon_left autochthon_right iliopsoas_left iliopsoas_right brain skull rib_left_1 rib_left_2 rib_left_3 rib_left_4 rib_left_5 "
          "rib_left_6 rib_left_7 rib_left_8 rib_left_9 rib_left_10 rib_left_11 rib_left_12 rib_right_1 rib_right_2 rib_right_3 rib_right_4 "
          "rib_right_5 rib_right_6 rib_right_7 rib_right_8 rib_right_9 rib_right_10 rib_right_11 rib_right_12 sternum costal_cartilages").split()

RULES = [(r"lung_.*_left", "lung_left"), (r"lung_.*_right", "lung_right"), (r"kidney_cyst_.*", "kidney_cyst"), (r"kidney_(left|right)", "kidney"),
         (r"adrenal_gland_.*", "adrenal"), (r"vertebrae_C\d", "spine_cervical"), (r"vertebrae_T\d+", "spine_thoracic"), (r"vertebrae_L\d", "spine_lumbar"),
         (r"(sacrum|vertebrae_S1)", "sacrum"), (r"rib_.*", "ribs"), (r"atrial_appendage_left", "heart"),
         (r"(brachiocephalic_trunk|subclavian_artery_.*|common_carotid_artery_.*)", "arch_vessels"),
         (r"(brachiocephalic_vein_.*|superior_vena_cava|inferior_vena_cava)", "great_veins"), (r"iliac_(artery|vena)_.*", "iliac_vessels"),
         (r"(humerus|scapula|clavicula|femur|hip)_(left|right)", None), (r"gluteus_.*", "gluteal"), (r"autochthon_.*", "autochthon"),
         (r"iliopsoas_.*", "iliopsoas")]
PATH_GROUPS = {"kidney_cyst"}


def group_of(leaf):
    for pat, g in RULES:
        if re.fullmatch(pat, leaf): return g if g else leaf.rsplit("_", 1)[0]
    return leaf


GROUPS = sorted({group_of(l) for l in LEAVES})
G_INDEX = {g: i for i, g in enumerate(GROUPS)}
LEAF_TO_GROUP = np.array([G_INDEX[group_of(l)] for l in LEAVES])


def group_occupancy(occ_leaf):
    """(n x 117) leaf occupancy -> (n x G) group occupancy (sum, clipped at 1)."""
    G = np.zeros((occ_leaf.shape[0], len(GROUPS)), np.float32); np.add.at(G.T, LEAF_TO_GROUP, occ_leaf.T.astype(np.float32)); return np.minimum(G, 1)


def partition(occ_group, core=.8, other=.2):
    """per token: dominant group index (or -1 = 'other' background, -2 = partial, not scored) and core flag."""
    mx = occ_group.max(1); arg = occ_group.argmax(1); lab = np.full(len(mx), -2)
    lab[mx >= core] = arg[mx >= core]; lab[occ_group.sum(1) <= other] = -1; return lab


def adjacency(occ_group, frac=.05):
    """data-driven adjacency: groups a, b adjacent if >= frac of tokens containing a (occupancy > 0) also contain b, or vice versa."""
    P = occ_group > 0; n = P.sum(0).astype(float); C = (P.T.astype(np.float32) @ P.astype(np.float32))
    A = (C / np.maximum(n[:, None], 1) >= frac) | (C / np.maximum(n[None, :], 1) >= frac); np.fill_diagonal(A, False)
    return {GROUPS[i]: {GROUPS[j] for j in np.flatnonzero(A[i])} for i in range(len(GROUPS))}
