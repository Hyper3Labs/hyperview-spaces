---
title: HyperView DeepFashion Text Search
emoji: 👖
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# HyperView - DeepFashion Text Search Comparison

This demo loads a curated DeepFashion In-Shop subset into HyperView and compares:

- CLIP ViT-B/32 in a Euclidean 2D layout
- Hyper3-CLIP `hyper3-clip-v0.5` in a Poincare 2D layout

The main readout is built for a retail search buyer. It shows fixed text-to-image examples where a shopper-style query asks for a specific item and the exact target product appears much earlier under Hyper3-CLIP than under CLIP.

## Business Story

The demo is not "another embedding map." The buyer-facing story is:

- Product search often fails by returning almost-right variants.
- Fashion queries combine color, fit, fabric, cut, and construction details.
- In the DeepFashion text-to-image probe, Hyper3-CLIP has a small aggregate edge and concrete examples where the exact item appears on the first screen while CLIP buries it.
- The best example is a query for light denim leggings with skinny fit, zipper details, five-pocket construction, and pockets: Hyper3 ranks the exact target first; CLIP first surfaces it at rank 32.

Use the ranked result strips first. The Samples panel then shows the selected catalog item and nearest neighbors, while the smaller context maps show the same item in the actual CLIP and Hyper3-CLIP embedding layouts. The text-search ranks are precomputed from the bounded DeepFashion probe; the maps provide visual neighborhood context for the same fashion items.

## What Is In The Demo

- Three shopper-style query examples with ranked CLIP vs Hyper3-CLIP image results.
- Exact-target rank readouts for each model.
- Clickable result cards that select the product in the active HyperView map.
- A compact benchmark footer for traceability, with text-to-image numbers separated from the older image-to-image retrieval check.

This is a demo probe, not a broad production benchmark. It is meant to show the failure mode: specific text-to-image product search where exact-item rank matters.

## Run Locally

From the HyperView repository:

```bash
uv run python hyperview-spaces/spaces/fashion-deepfashion-text-search-clip-hyper3clip/demo.py
```

Useful overrides:

```bash
HYPERVIEW_PORT=6265 DEEPFASHION_SAMPLES_PER_CATEGORY=30 \
  uv run python hyperview-spaces/spaces/fashion-deepfashion-text-search-clip-hyper3clip/demo.py
```

## Benchmark Context

Landing-page-safe wording:

> On a bounded DeepFashion text-to-image probe, Hyper3-CLIP has a small aggregate top-10 edge over CLIP-B/32 and produces concrete typed-search wins. In one query for light denim leggings with specific construction details, Hyper3 ranks the target product first while CLIP does not surface it until rank 32.

Do not present this as a broad claim against every modern multimodal embedding model. We have not yet added SigLIP, Jina-CLIP, NV-CLIP, or Gemini Embedding 2 to this demo.

## Deploy Source

This folder is intended to deploy to `hyper3labs/HyperView-DeepFashion-Text-Search` from the `hyperview-spaces` deployment repository.
