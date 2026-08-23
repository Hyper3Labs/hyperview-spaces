---
title: HyperView Art Text Search
emoji: 🎨
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

# HyperView - Art Text Search Comparison

This demo loads a bounded artwork subset into HyperView and compares:

- CLIP ViT-B/32 in a Euclidean 2D layout
- Hyper3-CLIP `hyper3-clip-v0.5` in a Poincare 2D layout

The buyer story is art marketplace search. A buyer can type a visual composition such as "blue ship on a hill" and the right painting needs to rank highly even when the artwork title does not describe the visible content.

## Dataset

The default dataset is `Artificio/WikiArt`, streamed from Hugging Face with the `datasets` library. It provides 103k artwork rows with `image`, `title`, `artist`, `date`, `genre`, `style`, and `description` fields, and this Space samples a bounded, balanced slice across visually useful genres and styles.

License note: the Hugging Face dataset card does not declare an SPDX license. Treat this Space as a demo/evaluation scaffold. For a production or commercial marketplace demo, retarget the constants block in `demo.py` to a CC0/open-access museum mirror such as a Metropolitan Museum Open Access derived dataset.

## What Is In The Demo

- A curated gallery of 20 compositional buyer prompts.
- Free-text search through the normal HyperView text search UI.
- Side-by-side CLIP and Hyper3-CLIP context maps.
- A Samples panel for inspecting retrieved paintings and nearest neighbors.

The important failure mode is visual-content retrieval, not title matching. The dataset keeps title, artist, genre, and style as metadata, but the prompt gallery is written around visual attributes that may not appear in titles.

## Run Locally

From the `hyperview-spaces` repository root:

```bash
python3 demos/art-text-search-clip-hyper3clip/demo.py
```

Useful overrides:

```bash
HYPERVIEW_PORT=6266 ART_MAX_SAMPLES=800 ART_SAMPLES_PER_GENRE=80 \
  python3 demos/art-text-search-clip-hyper3clip/demo.py
```

## Swap The Dataset Or Model

The editable constants live at the top of `demo.py`. To use a different artwork dataset:

```bash
ART_HF_DATASET="your-org/your-cc0-art-dataset" \
ART_HF_SPLIT="train" \
ART_MAX_SAMPLES=1200 \
python3 demos/art-text-search-clip-hyper3clip/demo.py
```

The model comparison follows the same `MODEL_SPECS` pattern as the other text-query demos. The baseline defaults to `openai/clip-vit-base-patch32` through `embed-anything`, and the candidate defaults to `hyper3-clip-v0.5` through `hyper-models`.

## Deploy Source

This folder is intended to deploy to `hyper3labs/HyperView-Art-Text-Search` from the `hyperview-spaces` deployment repository.
