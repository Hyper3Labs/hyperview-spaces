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

This demo opens the persisted Amazon Berkeley Objects catalog in the full
HyperView shell. It answers two business questions: can a prepared shopper
description retrieve the intended product, and do image-neighbourhoods preserve
useful product families under each model?

The workspace combines native ranked Samples panels, two native scatter panels,
a native prepared-results panel, and a compact right-side question panel:

- CLIP ViT-B/32 in a Euclidean 2D layout
- Hyper3-CLIP `hyper3-clip-v0.5` from `hyper-models` in a Poincare 2D layout

The right-side panel offers three prepared text-to-product searches and three
prepared image anchors. Static visitors can switch cases and models, inspect
ordered results, pan/zoom/lasso both maps, and share selection across panels.
Arbitrary text inference remains a live-Space capability and is not shown as a
functional-looking input in the static export.

The demo loads the full ABO metadata mirror from
`hyper3labs/amazon-berkeley-objects`, then deterministically selects a balanced
subset for the live comparison and always includes the fixed walkthrough query
samples. Local `demo_data` is only a runtime cache for downloaded images,
HyperView dataset state, embeddings, and layouts.

Run locally from the HyperView repo:

```bash
uv run python hyperview-spaces/demos/abo-catalog-clip-hycoclip/demo.py
```

Useful overrides:

```bash
HYPERVIEW_PORT=6263 ABO_MAX_PRODUCT_TYPES=12 ABO_SAMPLES_PER_PRODUCT_TYPE=20 \
  uv run python hyperview-spaces/demos/abo-catalog-clip-hycoclip/demo.py
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

The Dockerfile installs `hyperview==1.1.0` and `hyper-models[ml]==0.3.1` from
PyPI. The released HyperView wheel includes the built frontend assets, so this
Space does not carry a local `static/` bundle or copy frontend files into the
installed package.

Hyper3-CLIP weights are loaded through the `hyper-models` catalog entry for the
gated `hyper3labs/hyper3-clip-v0.5` model repository at runtime. The Space needs
an `HF_TOKEN` secret with access to that model.
