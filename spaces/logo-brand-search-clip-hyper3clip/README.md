---
title: HyperView Logo Brand Search
colorFrom: blue
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
---

# HyperView Logo Brand Search

This Space shows a brand-asset retrieval workflow where a creative team searches a logo library using detailed visual direction: category, object motifs, palette, background, and style.

The demo compares Hyper3-CLIP against CLIP ViT-B/32 on a bounded `logo-wizard/modern-logo-dataset` text-to-logo probe. In the probe, Hyper3-CLIP improves text-to-logo Hit@1 from 16.3% to 35.6%, Hit@5 from 48.8% to 73.1%, and MRR by 0.207.

Four curated evidence cases are defined as row indices into the first 160 examples of the Hugging Face dataset:

- Barber Franchise Mark: Hyper3 ranks the target #1; CLIP ranks it #30.
- Floral Retail Identity: Hyper3 ranks the target #1; CLIP ranks it #29.
- Construction Brand System: Hyper3 ranks the target #2; CLIP ranks it #17.
- Hospitality Bar Concept: Hyper3 ranks the target #1; CLIP ranks it #17.

On startup the Space loads `logo-wizard/modern-logo-dataset` from Hugging Face, saves the 160 candidate images into the runtime cache, computes CLIP and Hyper3-CLIP embeddings, and builds the two embedding scatter panels from those vectors.

## Run Locally

From the `hyperview-spaces` repository root:

```bash
HYPERVIEW_PORT=6272 uv run \
  --with "hyperview[ml]==0.6.2" \
  python spaces/logo-brand-search-clip-hyper3clip/demo.py
```

Then open the URL printed by the launcher.
