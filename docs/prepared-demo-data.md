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

## The demo itself is fine — verified

Run against the local prepared dataset, on HyperView `1.0.1.dev2+g384f629b2`
(current `main`) and `hyper-models 0.3.1`, `live_demo.py` serves working live
text search. Three queries typed into the native Samples box:

| Query | Top 8 |
| --- | --- |
| a long sleeve knit cardigan sweater | 7 cardigans, 1 blouses |
| a floral summer romper with short sleeves | rompers dominant, dresses adjacent |
| a pleated denim skirt | leggings dominant, 2 skirts |

Distances rank correctly and the three result sets are distinct, so the v0.5
text tower is doing real retrieval — this is the 0.3.1 behaviour, not 0.3.0's
random-weight noise. The third query is a genuine weakness worth keeping in
the demo rather than hiding: a denim skirt request surfaces leggings first.

So nothing is wrong with the demo code or the model. The gap is only in how
the prepared dataset reaches a container.

## Root cause: there is no primitive for this

`hyperview dataset create` builds a dataset from a Hugging Face dataset or a
local image directory — it re-embeds, which regenerates the content-hash layout
keys that the demos pin as constants (`HYPER3_LAYOUT_KEY`, `CLIP_LAYOUT_KEY`).
Rebuilding at boot therefore does not reproduce the same workspace.

`hyperview export` produces a read-only static Shared View, not a live dataset
that can be opened with `hv.Dataset(name)`.

Neither ships a prepared live dataset. The demos adopted an architecture that
v1 has no supported way to deliver, which is why the data ended up as an
untracked local directory.

## What has to be decided

The demos need a data path that works from a clean CI checkout. The options,
roughly in order of how well they fit what the repo already does:

1. **Publish each prepared dataset as a Hugging Face dataset** and have the
   demo pull and restore it at boot. Cheap on repo size, keeps CI stateless,
   and matches how the ABO demo already sources its mirror. Cold start becomes
   a download rather than a re-embed. DeepFashion is 9.6M of dataset plus 7.7M
   of media, so the download is small. Needs a `hyper3labs` write token.
2. **Commit the prepared artifacts via Git LFS.** Self-contained and
   reproducible, at the cost of repo weight and LFS bandwidth on every build.
   Roughly 45M across the three demos.
3. **Bake at image build time**, which means restoring a build path to demos
   that deliberately removed one — and pinning the regenerated layout keys,
   since they will not match the current constants.

Option 1 is the recommendation. Options 1 and 2 both want the same missing
piece: a supported way to serialise a prepared dataset and restore it by name.
That is worth building into HyperView rather than scripting per demo.

Until one is implemented, DeepFashion cannot serve live text search from a
deployed Space, and the Fashion, GeoSpatial, and Logo demos should be treated
as not deployable from CI. This does not block the PyPI release of `hyperview`
or `hyper-models`; it blocks the Space deployments that consume them.
