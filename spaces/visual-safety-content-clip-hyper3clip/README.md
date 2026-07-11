---
title: HyperView Visual Safety
emoji: 🛡️
colorFrom: yellow
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
---

# HyperView - Open Images Visual Safety Demo

This demo shows a marketplace-style visual moderation workflow without showing
explicit NSFW material.

It loads a small curated Open Images V7 validation subset from the Space assets
and builds the HyperView dataset at startup with two buckets:

- **Safe**: ordinary marketplace/public-image objects such as clothing, shoes,
  furniture, toys, books, fruit, laptops, and mobile phones.
- **Needs review**: public-displayable but policy-relevant objects such as
  alcohol, cigarettes, knives, and firearms-related labels.

HyperView computes embeddings and opens two pinned maps at startup:

- CLIP ViT-B/32 in a Euclidean 2D layout
- hyper3-clip `hyper3-clip-v0.5` from `hyper-models` in a Poincare 2D layout

The right-hand panel includes the measured 120-image zero-shot smoke test:
CLIP is stronger overall on this first proxy, while hyper3-clip catches slightly
more review-class items at the cost of more false positives.

Run locally from the HyperView repo:

```bash
uv run python hyperview-spaces/spaces/visual-safety-content-clip-hyper3clip/demo.py
```

Useful overrides:

```bash
HYPERVIEW_PORT=6265 SAFETY_SAMPLES_PER_BUCKET=40 \
  uv run python hyperview-spaces/spaces/visual-safety-content-clip-hyper3clip/demo.py
```

## Dataset And Rights

The demo uses a checked-in public Open Images V7 validation subset under
`demo_assets/`:

- Dataset: https://storage.googleapis.com/openimages/web/index.html
- Images are loaded through Hugging Face Hub asset resolution when the Space
  runs on Hugging Face.
- Individual source licenses are preserved in sample metadata.

This is a public demo proxy for marketplace moderation triage, not a claim that
either model is a production safety classifier.

## Deploy Source

This folder is intended to deploy to `mnm-matin/HyperView-Visual-Safety` from
the `hyperview-spaces` deployment repository. The org Space
`hyper3labs/HyperView-Visual-Safety` is kept commit-synced but paused.

hyper3-clip weights are loaded through the `hyper-models` catalog entry for the
gated `hyper3labs/hyper3-clip-v0.5` model repository at runtime. The Space needs
an `HF_TOKEN` secret with access to that model.

If that secret is missing or the gated model cannot be loaded, startup fails;
the demo does not substitute CLIP results for the hyper3-clip panel.
