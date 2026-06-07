---
title: HyperView RESISC45 Geospatial
emoji: 🛰️
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
models:
- hyper3labs/hyper3-clip-v0.5
- openai/clip-vit-base-patch32
datasets:
- tanganke/resisc45
tags:
- hyperview
- geospatial
- image-retrieval
- remote-sensing
---

# HyperView - RESISC45 Geospatial Retrieval Comparison

This demo builds a balanced NWPU-RESISC45 remote-sensing subset and opens
HyperView with two pinned scatter panels plus a compact scene-retrieval readout:

- CLIP ViT-B/32 in a Euclidean 2D layout
- Hyper3-CLIP `hyper3labs/hyper3-clip-v0.5` in a Poincare 2D layout

The readout panel ranks live query examples by where Hyper3-CLIP improves the
top-10 neighborhood over CLIP. The demo is designed around remote-sensing review
workflows: semantic search over aerial/satellite tiles, scene-neighborhood
inspection, and label-QA for coarse operational groups such as transport,
built environment, agriculture/vegetation, water/coastal, sports/recreation,
and natural terrain.

## Industry Story

Use this as the non-retail proof point for Hyper3-CLIP. The buyer-facing story
is not generic satellite classification; it is retrieval QA for large imagery
archives:

- Search for one scene tile and inspect whether its nearest neighbors stay in
  the same exact scene class and broader operational group.
- Compare CLIP and Hyper3-CLIP on the same query to surface scene drift,
  mixed neighborhoods, and coarse-label leakage.
- Map the workflow to geospatial search, agriculture monitoring, insurance and
  risk review, infrastructure analytics, and remote-sensing dataset QA.

The demo should be positioned as a hierarchy-sensitive retrieval probe for
remote-sensing imagery, not as a replacement for specialist remote-sensing
classifiers.

The runtime sample is drawn from `tanganke/resisc45`, using the `test` split by
default and selecting a balanced number of images per RESISC45 class.

Run locally from the HyperView repo:

```bash
uv run python hyperview-spaces/spaces/geospatial-eurosat-clip-hyper3clip/demo.py
```

Useful overrides:

```bash
HYPERVIEW_PORT=6264 GEOSPATIAL_SAMPLES_PER_CLASS=5 \
  uv run python hyperview-spaces/spaces/geospatial-eurosat-clip-hyper3clip/demo.py
```

## Benchmark Context

Internal lightweight retrieval runs currently show Hyper3-CLIP above OpenAI
CLIP-B/32 on NWPU-RESISC45 same-class retrieval and coarse parent grouping.
Keep the public claim narrow: this is a positive geospatial retrieval probe
against OpenAI CLIP-B/32, not a claim that Hyper3-CLIP beats every
remote-sensing model.

## Deploy Source

This folder is intended to deploy to `hyper3labs/HyperView-EuroSAT-Geospatial`
from the `hyperview-spaces` deployment repository.

Hyper3-CLIP weights are loaded from the gated
`hyper3labs/hyper3-clip-v0.5` model repository at runtime. The Space needs an
`HF_TOKEN` secret with access to that model.

If that secret is missing or lacks gated-model access, the Space starts with a
clearly labeled CLIP fallback for the Hyper3-CLIP panel instead of exiting
during startup. Set `HYPERVIEW_ALLOW_CANDIDATE_FALLBACK=0` to make candidate
model failures hard errors again.
