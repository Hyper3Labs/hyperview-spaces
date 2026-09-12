---
title: "HyperView: Jaguar Embedding Geometry Comparison"
emoji: 🐆
colorFrom: green
colorTo: yellow
sdk: static
app_file: index.html
pinned: false
datasets:
  - hyper3labs/jaguar-hyperview-demo
---

# HyperView Jaguar Core Claims Demo

This paper-facing Space compares three checkpoint families on **1,895
foreground-only jaguar images**, with the original 31 identity labels and
train/validation tags:

1. Euclidean 2D — `triplet:T0:msv3`, seed 43 (2,152-dimensional vectors).
2. Hyperspherical 3D — `arcface:O0:msv3`, seed 44 (2,152-dimensional vectors).
3. Hyperbolic Poincare 2D — `lorentz:O1:msv3`, seed 44 (257-dimensional vectors).

The spherical panel opens first. Switch tabs to compare geometries, filter
identities, select points, and browse image neighbors. All assets and up to 100
neighbors per sample are included: there is no Python server to wake up.
New embeddings, recomputed projections, and arbitrary inference are unavailable.

## Research compatibility

The static migration preserves the published embedding vectors, sample IDs,
labels, split tags, and all three layout coordinate sets. **No training,
embedding inference, or UMAP recomputation was performed.** The modern HyperView
shell replaces the old frontend patch; its controls and panel chrome differ.

**Neighbor browsing still uses cosine distance in every model, including the
Lorentz vectors, matching the original application. These are not canonical
Lorentz-distance retrieval scores.** Floating-point ties may have a different
order; the migration checks the original neighbors and distances.

The owner, repository name, and paper-facing Space URL are unchanged.
Hugging Face serves static apps from a different host:
[open the static app](https://hyper3labs-jaguar-hyperview-multigeometry.static.hf.space/).
Old direct links to the Docker `.hf.space` host no longer work; use the stable
`huggingface.co/spaces/hyper3labs/jaguar-hyperview-multigeometry` URL for citations.
The original Docker source and GPU asset-generation scripts are retained in
this repository and at the `pre-static-2026-09-12` rollback tag.

## Reproducibility

- Original Space revision: `214644d68ee4f10d7a5dbc768ed76af00febe62c`.
- HF dataset revision: `28110bb140951f84f11f23073d76412b367f65e4`.
- Original asset manifest: `assets/manifest.json`, generated 2026-04-05.
- Frozen source layout/metadata snapshot: `research/legacy-snapshot.json`.
- Verification counts and input hashes: `research/migration-report.json`.
- Independent artifact checks: `research/artifact-verification.json`.
- Canonical build recipe: [hyperview-spaces/demos/jaguar-multigeometry](https://github.com/Hyper3Labs/hyperview-spaces/tree/main/demos/jaguar-multigeometry).

Original ranking/source-of-truth anchors remain:

- `reports/summaries_of_findings/core_claims_axis12_paper_facing_tables_2026_03_16_102311/axis1_primary_ranking.csv`
- `paper_draft/second_draft/sources_of_truth.md`

The old Docker environment variables and frontend cache-key patch no longer
control the static app. Rebuild the canonical source and export its workspace
to make a reviewed change.
