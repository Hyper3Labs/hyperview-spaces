---
title: HyperView
emoji: 🔮
colorFrom: purple
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# HyperView — Imagenette (CLIP + HyCoCLIP)

This Hugging Face Space runs HyperView with:

- CLIP embeddings (`openai/clip-vit-base-patch32`) for Euclidean layout
- HyCoCLIP embeddings (`hycoclip-vit-s`) for Poincaré layout

The Docker image installs the **latest HyperView from PyPI** and precomputes
embeddings/layouts during build for fast runtime startup.

## Configuration

Environment variables:

- `DEMO_HF_DATASET` (default: `Multimodal-Fatima/Imagenette_validation`)
- `DEMO_HF_SPLIT` (default: `validation`)
- `DEMO_HF_IMAGE_KEY` (default: `image`)
- `DEMO_HF_LABEL_KEY` (default: `label`)
- `DEMO_SAMPLES` (default: `300`)
- `DEMO_CLIP_MODEL` (default: `openai/clip-vit-base-patch32`)
- `DEMO_HYPER_MODEL` (default: `hycoclip-vit-s`)

## Deploy source

This folder is synchronized to Hugging Face Spaces by GitHub Actions from the
`hyperview-spaces` deployment repository.
