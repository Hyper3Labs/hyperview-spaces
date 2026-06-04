---
title: HyperView ABO Catalog
emoji: 🛒
colorFrom: gray
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# HyperView - ABO Catalog Model Comparison

This demo builds a small Amazon Berkeley Objects product-catalog subset and opens
HyperView with two pinned scatter panels plus a comparison readout:

- CLIP ViT-B/32 in a Euclidean 2D layout
- HyCoCLIP `hycoclip-vit-s` in a Poincare 2D layout

The right-side panel uses fixed product examples to compare nearest-neighbor
behavior for the same query under each model.

The demo loads the full ABO metadata mirror from
`hyper3labs/amazon-berkeley-objects`, then deterministically selects a balanced
subset for the live comparison. Local `demo_data` is only a runtime cache for
downloaded images, HyperView dataset state, embeddings, and layouts.

Run locally from the HyperView repo:

```bash
uv run python hyperview-spaces/spaces/abo-catalog-clip-hycoclip/demo.py
```

Useful overrides:

```bash
HYPERVIEW_PORT=6263 ABO_MAX_PRODUCT_TYPES=12 ABO_SAMPLES_PER_PRODUCT_TYPE=20 \
  uv run python hyperview-spaces/spaces/abo-catalog-clip-hycoclip/demo.py
```

## Swap the comparison model

The model choices live in the `MODEL_SPECS` block near the top of
[demo.py](demo.py). To swap the candidate model, update these environment
variables or edit the second entry in `MODEL_SPECS`:

```bash
ABO_CANDIDATE_DISPLAY_NAME="New Model" \
ABO_CANDIDATE_PROVIDER="hyper-models" \
ABO_CANDIDATE_MODEL="new-model-id" \
ABO_CANDIDATE_LAYOUT="poincare:2d" \
ABO_CANDIDATE_GEOMETRY="poincare" \
python demo.py
```

The panel reads model labels, layout keys, and fixed examples from props passed
by `demo.py`, so model swaps should not require editing the extension
JavaScript.

## Deploy source

This folder is intended to deploy to `hyper3labs/HyperView-ABO-Catalog` from
the `hyperview-spaces` deployment repository.

The Dockerfile installs `hyperview==0.6.0` from PyPI. The released HyperView
wheel includes the built frontend assets, so this Space should not carry a
local `static/` bundle or copy frontend files into the installed package.
