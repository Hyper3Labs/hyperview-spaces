---
title: HyperView RESISC45 Geospatial
emoji: 🛰️
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
models:
- hyper3labs/hyper3-clip-v1
- openai/clip-vit-base-patch32
tags:
- hyperview
- geospatial
- image-retrieval
- remote-sensing
---

# Compare aerial tiles

[Open the prepared viewer](https://spaces.hyper3labs.com/geospatial/).
Choose Aircraft, Forest, Storage tanks, or Airport and compare the same tile's
10 nearest neighbours from **Hyper3-CLIP V1** and **OpenAI CLIP ViT-B/32**.
The two ranked panels show the images; the right panel compares same-class,
same-group and other-group counts. Archive-map tabs show all 60 tiles.

This is a small curated NWPU-RESISC45 retrieval probe: 12 classes, five tiles
per class, all 60 anchors evaluated, self-matches excluded. There are only four
other same-class tiles per query, so same-class P@10 has a 40% ceiling.
Group counts include same-class matches. Hyper3 neighbours use hyperbolic
distance; CLIP uses cosine distance. The 2D maps are projections, not the
space used for ranking. The airport example preserves a case where CLIP wins.

Aggregate P@10 and model/source details are under **Evaluation scope & results**.
The viewer provides saved neighbours and maps; it does not run arbitrary text
queries or new inference.

## Artifact provenance

`evidence_cases.json` records the cases, aggregate metrics, model revision,
checkpoint hash and all 60 image hashes. `results/geospatial_v1_rankings.json`
records both models' complete top-10 results for all 60 anchors.

Hyper3-CLIP V1 is pinned to `hyper3labs/hyper3-clip-v1` revision
`12a8d89022cec75a3fbac91047683231cbc0fa82`, encoded with `hyper-models` 0.4.0.
The October 9 V1 rebuild reproduced the original candidate vectors exactly;
the old v0.5 space names were legacy identifiers. The scores and four examples
are unchanged. The original CLIP baseline vectors are retained; their checkpoint
revision was not recorded.

The original upstream mirror/split of the 60 selected tiles remains unrecorded.
The former `tanganke/resisc45` test-split declaration cannot reproduce the
selection; see `dataset_manifest.json` and `docs/demo-evidence-integrity.md`.
The committed images and their hashes define the corpus for this rebuild.
This probe does not establish performance on a full remote-sensing benchmark.

## Rebuild and export

Run from the parent HyperView checkout. The evaluation uses the committed
bundle's images and frozen CLIP vectors, the public HyperView and hyper-models
APIs, and the pinned V1 checkpoint. It downloads only that checkpoint if absent.

```bash
uv run --with 'hyper-models[ml]==0.4.0' python hyperview-spaces/scripts/eval_geospatial.py
HYPERVIEW_BUILD_ONLY=1 uv run python hyperview-spaces/demos/geospatial-eurosat-clip-hyper3clip/demo.py
uv run python hyperview-spaces/scripts/export_static_spaces.py geospatial
uv run python hyperview-spaces/scripts/test_geospatial_artifact.py
```

Prepared dataset: `resisc45_geospatial_v1` (60 rows).
Workspace: `geospatial-resisc45-v1-2026-10-09`.
Launch validates the cases against the model spaces and explicit 2D layouts.
It uses the persisted dataset; it does not recompute embeddings on each launch.

```bash
HYPERVIEW_PORT=6264 uv run python hyperview-spaces/demos/geospatial-eurosat-clip-hyper3clip/demo.py
```

Both result panels, case selection and the narrow-screen default use public
runtime-managed UI state. The comparison panel opens first in the compact tab
layout; selecting a case updates both ranked panels and shared selection.
