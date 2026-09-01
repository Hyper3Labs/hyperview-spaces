# Prepared demo data does not reach a deployed Space

Three demos open a dataset that was prepared ahead of time instead of building
one at cold start. That is the right direction — it is what removes the
45-minute start period described in
[deployment-architecture.md](deployment-architecture.md). It is also, right
now, why one Space is down.

## What the three demos require

| Demo | Rows required | Local `demo_data/` |
| --- | --- | --- |
| `fashion-deepfashion-text-search-clip-hyper3clip` | 741 | 7.7M |
| `geospatial-eurosat-clip-hyper3clip` | 60 | 5.8M |
| `logo-brand-search-clip-hyper3clip` | 160 | 5.2M |

Each `main()` opens `hv.Dataset(DATASET_NAME)` and validates immediately. There
is no ingest or embedding path in any of them. Against an empty store they
raise, for example:

```text
Fashion workspace requires 741 persisted samples; found 0
Dataset '...' must contain 60 evidence rows; found 0
Logo workspace requires 160 persisted samples; found 0
```

## Why the data cannot get there

Two independent exclusions, either of which is sufficient:

1. `.gitignore:16` ignores `demos/*/demo_data/`, so the data is not in the
   repository. `deploy-hf-space-reusable.yml` uploads from a fresh
   `actions/checkout`, which therefore never contains it.
2. Every affected demo's `.dockerignore` lists `demo_data/`, so even when the
   directory is present in the Space repo it is excluded from the build
   context and never lands in the image.

The dataset itself is worse than the media: it lives in HyperView's own store,
not under `demo_data/` at all, so uploading that directory would not be enough
either.

## How this looks in production today

| Space | Deployed by | Deployed code | Status |
| --- | --- | --- | --- |
| `hyper3labs/HyperView-DeepFashion-Text-Search` | CI, current `main` | requires prepared data | `RUNTIME_ERROR` |
| `mnm-matin/HyperView-EuroSAT-Geospatial` | manual, older revision | builds data at boot | `RUNNING` |
| `mnm-matin/HyperView-Logo-Brand-Search` | manual, older revision | builds data at boot | `RUNNING` |

Verified by fetching `demo.py` from each Space: the two running Spaces still
call `dataset.compute_embeddings(...)`, which the current source no longer
does. **They are running only because they are stale.** The next manual deploy
of either one reproduces the DeepFashion failure.

This is not a regression from any unpushed commit — `origin/main` already
requires prepared data in all three.

## What has to be decided

The demos need a data path that works from a clean CI checkout. The options,
roughly in order of how well they fit what the repo already does:

1. **Publish each prepared dataset as a Hugging Face dataset** and have the
   demo pull it at boot. Cheap on repo size, keeps CI stateless, and matches
   how the ABO demo already sources its mirror. Cold start becomes a download
   rather than a re-embed.
2. **Commit the prepared artifacts via Git LFS.** Self-contained and
   reproducible, at the cost of repo weight and LFS bandwidth on every build.
3. **Bake at image build time** (`RUN python -c "from demo import
   build_dataset; build_dataset()"`), which means restoring a build path to
   demos that deliberately removed one.

Option 1 is the recommendation. Until one is implemented, DeepFashion cannot
serve live text search, and the Fashion, GeoSpatial, and Logo demos should be
treated as not deployable from CI.
