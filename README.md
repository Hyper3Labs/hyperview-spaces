# hyperview-spaces

Source for the HyperView demos: one folder per use case, shipped either as a
**Static Space** (the exported bundle served as plain files) anyone can open
in a browser, or as a runtime-backed **Live Space** on Hugging Face.

## Open one

Each Static Space is a complete, read-only HyperView workspace over one corpus.
No install, no backend, no account — the ranked results, the embedding topology,
and every underlying sample are there to inspect.

| Space | The question it answers |
| --- | --- |
| [ABO Catalog](https://hyper3labs.github.io/spaces/abo-catalog/) | Does the model find the right product, not just a plausible category match? |
| [Fashion Products](https://hyper3labs.github.io/spaces/fashion-products/) | Does the exact SKU reach the shopper's first screen? |
| [Precision Regions](https://hyper3labs.github.io/spaces/precision-regions/) | Does the exact region reach the operator's first screen? |
| [Logo Search](https://hyper3labs.github.io/spaces/logo-search/) | Which existing logo best satisfies a detailed creative brief? |
| [GeoSpatial](https://hyper3labs.github.io/spaces/geospatial/) | Do retrieved neighbours preserve land-use identity? |
| [Visual Safety](https://hyper3labs.github.io/spaces/visual-safety/) | Is one extra catch worth five false reviews and six more queue slots? |

Each one compares `hyper3-clip-v0.5` against OpenAI CLIP ViT-B/32 on the same
bounded probe and shows the per-case evidence for both, including the cases
CLIP wins.

## Two delivery modes, one source

|  | Live Space | Static Space |
| --- | --- | --- |
| Runtime | Docker container running HyperView on Hugging Face | None — static files |
| Can do | New queries, new embeddings, recomputed layouts, mutated state | Prepared interactions, pan/zoom/lasso/selection, precomputed similarity, materialized text search |
| Registry | `live-spaces.registry.json` | `static-spaces.registry.json` |
| Built by | Docker build of `demos/<slug>/` | `scripts/export_static_spaces.py` |

Both are produced from the same folder under `demos/`. There is no forked
"Static Space" implementation — if you need different behaviour, change the demo.

## Make your own

The happy path is four steps:

1. Copy a folder from `demos/` — `inat24-tiny-clip-hycoclip` for a geometry
   showcase, `fashion-deepfashion-text-search-clip-hyper3clip` for text search
   with a custom panel.
2. Edit the constants block at the top of the new `demo.py` (dataset, models,
   layouts). Everything you need to change lives there.
3. Rewrite the folder's `README.md` — the YAML frontmatter is the Hugging Face
   Space page, and it must keep `sdk: docker`.
4. Register the folder in `live-spaces.registry.json`, add a row to the
   community table below, and run the checks.

```bash
uv run --project ../ python scripts/check_spaces.py
uv run --project ../ python scripts/check_static_spaces.py
```

Test the image locally before deploying anything:

```bash
docker build -t yourproject-hyperview demos/yourproject-hyperview
docker run --rm -p 7860:7860 yourproject-hyperview   # then open http://127.0.0.1:7860
```

**Working here with a coding agent?** Point it at
[`.agents/skills/hyperview-spaces/SKILL.md`](.agents/skills/hyperview-spaces/SKILL.md).
It carries the full contract: the registry field rules, the version-pin rules,
the export pipeline, and every check `check_spaces.py` enforces. For driving
HyperView itself, use the `hyperview-cli` skill shipped with the package
(`hyperview skill install`).

## Deploying

| Owner | How | Auth |
| --- | --- | --- |
| `hyper3labs/*` | Push to `main` touching the demo folder, or `workflow_dispatch` | Hugging Face Trusted Publisher (OIDC) — no long-lived secret |
| Personal account | `scripts/deploy_hf_space.py` | Your local `huggingface-cli` login |

For an org-owned Space, copy `.github/workflows/deploy-hf-space-hyperview.yml`
and update `name`, `concurrency`, `paths`, `source_dir`, and `space_id`, then
add a Trusted Publisher on the Space for `Hyper3Labs/hyperview-spaces`, branch
`main`, and that exact workflow filename.

For a personal Space, deploy manually — these are deliberately excluded from
deploy CI, so do not add a Hugging Face token as a GitHub secret:

```bash
uv run --project ../ python scripts/deploy_hf_space.py \
  --space-id mnm-matin/HyperView-Logo-Brand-Search \
  --source-dir demos/logo-brand-search-clip-hyper3clip
```

> **A push to `main` deploys.** Per-space workflows are path-scoped to their
> demo folder, so bumping a version pin to a package that is not on PyPI yet
> will rebuild the Space and fail. Publish first, then push the pin.

Keep Dockerfiles on released PyPI pins. `check_spaces.py` rejects an unpinned
`hyperview`, and it rejects a version named in a demo's prose that disagrees
with the version its Dockerfile installs.

Monitor what is deployed:

```bash
uv run --project ../ python scripts/monitor_spaces.py --fail-on-unhealthy
```

### Vendored wheels

`vendor/*.whl` is a temporary escape hatch for a Space that needs an unreleased
HyperView feature. Once that version is on PyPI, the Space must go back to an
explicit version pin and the wheel must be deleted.

## Repository layout

```text
.
├── .agents/skills/hyperview-spaces/   # agent skill: the full contract for this repo
├── .github/workflows/                 # per-space deploy, reusable deploy, checks, monitor
├── demos/                             # canonical source; one folder per use case
├── static-spaces/                      # generated read-only bundles (gitignored)
├── archived-spaces/                   # retired examples, outside the active registry
├── build/                             # build and deployment support
├── docs/                              # architecture and operations documentation
├── gallery/                           # registry-generated static gallery
├── scripts/                           # registry checks and maintenance tools
├── warm-worker/                       # registry-driven monitoring worker
├── live-spaces.registry.json          # runtime deployments and local runtime demos
└── static-spaces.registry.json         # reviewed static artifacts and mount paths
```

## Community Contributed Spaces

Add one row here when you contribute a new Space. `check_spaces.py` requires
every registered folder to appear in this table.

| Space | Hugging Face Space ID | Folder | Maintainer | Status | Notes |
| --- | --- | --- | --- | --- | --- |
| HyperView - iNat24 Tiny | `hyper3labs/HyperView` | `demos/inat24-tiny-clip-hycoclip` | Hyper3Labs | `live` | Compare Euclidean, spherical, and Poincare views of iNaturalist species taxonomy. |
| HyperView - ABO Catalog | `hyper3labs/HyperView-ABO-Catalog` | `demos/abo-catalog-clip-hycoclip` | Hyper3Labs | `live` | Inspect product-catalog neighborhoods across CLIP and Hyper3-CLIP embeddings. |
| HyperView - DeepFashion Text Search | `hyper3labs/HyperView-DeepFashion-Text-Search` | `demos/fashion-deepfashion-text-search-clip-hyper3clip` | Hyper3Labs | `live` | Explore shopper-style text-to-image retrieval wins on a curated fashion catalog. |
| HyperView - Art Text Search | `hyper3labs/HyperView-Art-Text-Search` | `demos/art-text-search-clip-hyper3clip` | Hyper3Labs | `draft` | Draft only; no confirmed Hugging Face Space or deployment workflow. |
| HyperView - EuroSAT Geospatial | `mnm-matin/HyperView-EuroSAT-Geospatial` | `demos/geospatial-eurosat-clip-hyper3clip` | mnm-matin | `live` | Monitored personal Space; deploy manually. |
| HyperView - VisA Manufacturing | `hyper3labs/HyperView-VisA-Manufacturing` | `demos/manufacturing-visa-reference-clip-hyper3clip` | Hyper3Labs | `live` | Find same-SKU visual references for manufacturing inspection images. |
| HyperView - Visual Safety | `mnm-matin/HyperView-Visual-Safety` | `demos/visual-safety-content-clip-hyper3clip` | mnm-matin | `live` | Monitored personal Space; deploy manually. |
| HyperView - Logo Brand Search | `mnm-matin/HyperView-Logo-Brand-Search` | `demos/logo-brand-search-clip-hyper3clip` | mnm-matin | `live` | Monitored Hugging Face Space; deployment is managed outside this repository. |
| HyperView - Precision Region Search | — | `demos/precision-region-search-refcocog-hyper3clip` | Hyper3Labs | `local` | Local draft with no confirmed Hugging Face Space or deploy workflow. |
| HyperView - Jaguar Re-ID | `hyper3labs/HyperView-Jaguar-ReID` | `archived-spaces/jaguar-reid-megadescriptor-spherical` | Hyper3Labs | Archived | Superseded by `hyper3labs/jaguar-hyperview-multigeometry` |

When you open a pull request, state the Hugging Face Space ID, the dataset
source, the embedding models, and whether this repository should deploy the
Space or only host the example folder.

## Notes

### Precomputed Lance data

You can ship precomputed LanceDB artifacts with the image, either by
precomputing at build time (`RUN python -c "from demo import build_dataset;
build_dataset()"`) or by committing the artifacts, which usually needs Git LFS.
This repo currently builds the dataset at first startup instead, so Hugging Face
CPU Spaces do not reopen LanceDB artifacts from slow Docker overlay layers. The
tradeoff is a long first boot, which is why the Dockerfiles use a
`--start-period` of 45 minutes.

### Dataset mirrors

The ABO catalog demo expects a Hugging Face metadata mirror at
`hyper3labs/amazon-berkeley-objects`. Build and upload it from the HyperView
repo root:

```bash
uv run --with pyarrow --with huggingface_hub \
  python hyperview-spaces/scripts/mirror_abo_to_hf.py --upload
```

The script writes Parquet configs for `listings`, `images`, `spins`, and
`3dmodels`, preserves the original ABO notices, and stores official S3 asset
URLs rather than duplicating image or model binaries. Upload requires a local
Hugging Face token with write access to the `hyper3labs` org.
