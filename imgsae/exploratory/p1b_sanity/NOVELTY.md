# A0 — novelty check (2026-11-09, web search; abstracts only, full texts not read)

## Closest prior work
- **Wesp, Holland, Sideri-Lampretsa, Gatidis — "Sparse Autoencoders for Interpretable Medical Image Representation Learning"** (MICCAI 2026; arXiv 2603.23794; code github.com/pwesp/sail).
  - Setup: Matryoshka SAEs on **2D slice** embeddings from BiomedParse (1536-d) and DINOv3 (1024-d), on 909,873 CT/MRI slices from TotalSegmentator.
  - Claims: reconstruction R² up to 0.941; 87.8% of downstream performance with 10 features; features describable in language by LLM-based auto-interpretation; language-driven retrieval.
  - The abstract mentions **no simple baselines** (PCA, k-means, raw channels, random-init encoder) and no label-grounded validity check. A reviewer comment on the MICCAI page says the interpretability evidence is partly proxy-based and suggests 3D CT FMs (CT-CLIP, Merlin, SPECTRE).
  - → Our angle is not covered: 3D token-level CT-FM features, label-grounded validity (masks), matched-sparsity baselines, untrained-encoder control.
- **SAEs on a pathology FM** (NeurIPS 2025, "Evaluating the Utility of Sparse Autoencoders for Interpreting a Pathology Foundation Model"): SAE dimensions correlate with cell-type counts; the features are specific to the pathology-pretrained model. This is the positive counterpart to test against.
- MedConcept (2604.11868) and Sparse Concept Channels (2607.20993) were already reviewed in the lean plan (#9). Both are probe- or LLM-judge based, with no seed or baseline controls.

## FM vs simple baselines in CT (the genre exists — "radiomics competes" alone is not new)
- CT-FM paper (Pai et al., arXiv 2501.09001): beats random initialisation and is comparable to SUPREM on its downstream tasks (fine-tuning, not token probes).
- nnFoundation (arXiv 2609.26924): self-supervised gains are largest at very small training sets. → Our T4 (few labels) is the right place to look for an FM advantage.
- Renal lesion benchmark (arXiv 2605.07749): the radiomics baseline significantly outperforms the best deep model on external testing.
- Lung CT, FM vs radiomics (arXiv 2607.01001): radiomics dominates the top configurations.
- Head and neck, RADCURE (arXiv 2607.26276): FM embeddings 0.791 vs radiomics 0.772 AUC; not significant against the best combined model.
- I found no CT study that puts a linear probe of a pretrained FM, the same network **untrained**, and label-free physical features in one table at token level.

## Implication for framing
- "FM ≈ radiomics on some task" is known. What is new would be:
  1. the **untrained-encoder control**, at token level;
  2. showing that **organ-label concept validation is saturated** by trivial features. This matters because SAE interpretability papers validate against organ labels.
  3. **SAE vs simple decompositions at matched sparsity and feature count** on label-grounded validity.
- Claims about Wesp et al. must be limited to "different setup (2D, LLM-judged)". We cannot claim to refute them without running their pipeline (code is public: Stage D option).

Sources: [MICCAI 2026 page](https://papers.miccai.org/miccai-2026/0976-Paper4497.html) · [arXiv 2603.23794](https://arxiv.org/abs/2603.23794v1) · [SAIL code](https://github.com/pwesp/sail) · [NeurIPS 2025 pathology SAE](https://neurips.cc/virtual/2025/128786) · [CT-FM arXiv 2501.09001](https://arxiv.org/pdf/2501.09001) · [nnFoundation 2609.26924](https://arxiv.org/html/2609.26924v1) · [renal 2605.07749](https://arxiv.org/pdf/2605.07749) · [lung 2607.01001](https://arxiv.org/pdf/2607.01001) · [H&N 2607.26276](https://arxiv.org/abs/2607.26276)
