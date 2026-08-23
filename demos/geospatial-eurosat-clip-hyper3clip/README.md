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

# GeoSpatial aerial identity audit

Business user: remote-sensing archive / imagery QA lead.

This HyperView demo answers two questions:

1. **From an anchor tile, do retrieved neighbours preserve land-use identity
   and avoid operationally costly confusions?**
2. **Do Hyper3-CLIP and CLIP organize the full archive into coherent,
   inspectable topology, outliers, and drift?**

## Workspace layout

The full HyperView shell stays intact. The demo composes:

| Panel | Role |
| --- | --- |
| **Hyper3 Samples** (ranked) | Anchor + ordered Top-10 neighbours in Hyper3-CLIP space |
| **CLIP Samples** (ranked) | Same anchor + ordered Top-10 neighbours in CLIP space |
| **Hyper3 Scatter** | Explicit Hyper3 multimodal 2D layout (Poincaré) over all 60 tiles |
| **CLIP Scatter** | Explicit CLIP multimodal 2D layout (Euclidean) over all 60 tiles |
| **Right audit panel** (360–410px) | Anchor-case controls, exact / parent / off-group counts, consequences, model comparison |

Native Samples own imagery and ranking. Scatter owns pan / zoom / lasso /
selection. The custom audit panel does **not** render result image grids; it
drives both ranked Samples panels through public `updateProps` and sets shared
selection when the anchor case changes.

Four versioned probes cover two clear wins, a built-environment case, and an
explicit regression. Aggregate P@10 above them covers all 60 queries in the
bounded 12-class, five-per-class subset.

This is a neighborhood-quality probe, not a specialist remote-sensing
benchmark or classifier. Exact model repository revisions were not captured in
the original persisted run; that limitation is visible in the audit panel and
in `evidence_cases.json`.

## Run locally

The demo opens the persisted, versioned evidence run and does not download
RESISC45 or recompute embeddings/layouts on launch:

```bash
HYPERVIEW_PORT=6264 uv run python \
  hyperview-spaces/demos/geospatial-eurosat-clip-hyper3clip/demo.py
```

Prepared dataset: `resisc45_clip_hyper3clip_curated_side_by_side` (60 rows).
Launch validates sample IDs, embedding-space keys, and the two explicit
layouts used by the ranked Samples + Scatter pairs against `evidence_cases.json`.

## Static export

Export with a similarity index so ranked Samples panels can resolve
anchor-neighbour order offline:

```bash
uv run hyperview export geospatial-resisc45-retrieval-evidence-v2 \
  --similarity-k 10 \
  --out dist/landing-demos/geospatial
```

The resulting directory is self-contained. Case switching updates both ranked
Samples props and shared selection without a backend. No image upload,
arbitrary text search, inference, or recomputation controls are exposed.
