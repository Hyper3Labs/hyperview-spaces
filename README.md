# hyperview-spaces

This folder is intended to be a **standalone repository** for Hugging Face Space deployments. Our demo at https://huggingface.co/spaces/hyper3labs/HyperView follows the template described here. 

Recommended GitHub repository name:

- `hyperview-spaces`

## Purpose

- Keep Space deployment logic separate from the core HyperView codebase
- Reuse one template pattern for multiple Space demos
- Deploy each demo folder to a different Hugging Face Space via GitHub Actions

## Intended reuse flow

This repo is meant to be easy to hand to an external coding agent.

The happy path is:

1. Copy one folder from `spaces/`
2. Edit the constants block at the top of that folder's `demo.py`
3. Update the Space `README.md`
4. Add or retarget one deploy workflow

Most deployable examples install released packages from PyPI. A few spaces use
the temporary vendored-wheel escape hatch documented below when they need
unreleased HyperView features. Keep custom Space logic in `demo.py` and
Space-local files so contributors can copy a folder, change their dataset
settings, and open a PR without carrying an internal source snapshot.

The current iNat24 Tiny example is the main HyperView geometry showcase. It
keeps the editable dataset/model choices in one place so agents do not need to
coordinate Docker args, runtime environment variables, and Python script flags.

## Create Your Own Hugging Face Space

Use the iNat24 Tiny example as a copyable starter.

1. Create a new Space at https://huggingface.co/new-space.
2. Choose a distinct Space name such as `yourproject-HyperView` or `HyperView-yourproject`.
3. Select `Docker` as the Space SDK.
4. Create the Space. Hugging Face will initialize it as a git-backed Docker Space with `sdk: docker` in `README.md`.
5. In this repository, copy `spaces/inat24-tiny-clip-hycoclip` to a new folder such as `spaces/yourproject-hyperview`.
6. Edit `spaces/yourproject-hyperview/demo.py` and change the constants block at the top of the file.
7. Edit `spaces/yourproject-hyperview/README.md` and rename the copied example from `HyperView` to your own project name.
8. Keep the Space name consistent across the Hugging Face Space ID, the README frontmatter `title`, and the Markdown H1. Good patterns are `yourproject-HyperView` and `HyperView-yourproject`.
9. Copy `.github/workflows/deploy-hf-space-hyperview.yml` to a new workflow file and update `name`, `concurrency`, `paths`, `source_dir`, and `space_id`.
10. Configure the GitHub Actions secrets `HF_USERNAME` and `HF_TOKEN`. The token must have write access to the target Hugging Face Space.
11. Push to `main` or run the workflow manually with `workflow_dispatch`.
12. Keep the Dockerfile on current released PyPI packages such as `hyperview==0.6.2` and `hyper-models==0.2.0`; use a vendored wheel only for the temporary development escape hatch described below.
13. Check the Hugging Face Space logs to confirm the Docker image built and the container started on port `7860`.

### Vendored wheels

Some spaces use `vendor/*.whl` when they need unreleased HyperView features.
This is a temporary development escape hatch: once the required HyperView
version is released, the space must switch back to an explicit PyPI version
pin and remove the vendored wheel.

### Optional Local Test

From the `hyperview-spaces` repository root:

```bash
docker build -t yourproject-hyperview spaces/yourproject-hyperview
docker run --rm -p 7860:7860 yourproject-hyperview
```

Then open `http://127.0.0.1:7860`.

## Contribute Your Space Back

If you want your Space to appear in this repository as a community example:

1. Fork this repository or create a branch if you already have write access.
2. Add your Space folder under `spaces/<your-slug>`.
3. Rename the copied `HyperView` title and heading to your own project name such as `yourproject-HyperView` or `HyperView-yourproject`.
4. Add or update a deploy workflow for your folder if this repository should deploy it.
5. Add a row for your Space in the community table below.
6. Open a pull request describing the Hugging Face Space ID, dataset source, embedding models, and whether the deploy workflow is expected to run from this repository.

Important: deployment workflows in this repository use the shared `HF_USERNAME` and `HF_TOKEN` GitHub secrets. A contributed workflow will only deploy successfully if that token has write access to the target Space.

## Community Contributed Spaces

Add one row here when you contribute a new Space.

| Space | Hugging Face Space ID | Folder | Maintainer | Status | Notes |
| --- | --- | --- | --- | --- | --- |
| HyperView - iNat24 Tiny | `hyper3labs/HyperView` | `spaces/inat24-tiny-clip-hycoclip` | Hyper3Labs | `live` | Compare Euclidean, spherical, and Poincare views of iNaturalist species taxonomy. |
| HyperView - ABO Catalog | `hyper3labs/HyperView-ABO-Catalog` | `spaces/abo-catalog-clip-hycoclip` | Hyper3Labs | `live` | Inspect product-catalog neighborhoods across CLIP and Hyper3-CLIP embeddings. |
| HyperView - DeepFashion Text Search | `hyper3labs/HyperView-DeepFashion-Text-Search` | `spaces/fashion-deepfashion-text-search-clip-hyper3clip` | Hyper3Labs | `live` | Explore shopper-style text-to-image retrieval wins on a curated fashion catalog. |
| HyperView - Art Text Search | `hyper3labs/HyperView-Art-Text-Search` | `spaces/art-text-search-clip-hyper3clip` | Hyper3Labs | `draft` | Compare CLIP and Hyper3-CLIP for compositional art marketplace search where titles omit visual content. |
| HyperView - EuroSAT Geospatial | `mnm-matin/HyperView-EuroSAT-Geospatial` | `spaces/geospatial-eurosat-clip-hyper3clip` | Hyper3Labs | `live` | Review remote-sensing scene retrieval and neighborhood drift in aerial imagery. |
| HyperView - VisA Manufacturing | `hyper3labs/HyperView-VisA-Manufacturing` | `spaces/manufacturing-visa-reference-clip-hyper3clip` | Hyper3Labs | `live` | Find same-SKU visual references for manufacturing inspection images. |
| HyperView - Visual Safety | `mnm-matin/HyperView-Visual-Safety` | `spaces/visual-safety-content-clip-hyper3clip` | Hyper3Labs | `live` | Triage public marketplace images into safe and policy-review buckets. |
| HyperView - Logo Brand Search | `mnm-matin/HyperView-Logo-Brand-Search` | `spaces/logo-brand-search-clip-hyper3clip` | mnm-matin | `live` | Monitored Hugging Face Space; deployment is managed outside this repository. |
| HyperView - Precision Region Search | — | `spaces/precision-region-search-refcocog-hyper3clip` | Hyper3Labs | `local` | Local draft with no confirmed Hugging Face Space or deploy workflow. |
| HyperView - Jaguar Re-ID | `hyper3labs/HyperView-Jaguar-ReID` | `archived-spaces/jaguar-reid-megadescriptor-spherical` | Hyper3Labs | Archived | Superseded by `hyper3labs/jaguar-hyperview-multigeometry` |

### Adding your own Space

Spaces may live under any Hugging Face organization or personal account. Copy
an existing space folder, add its `folder`, `space_id`, `status`,
`deploy_targets`, and `keep_warm` values to `spaces.registry.json`, then add a
deploy workflow that calls the reusable workflow and open a PR. The
`check-spaces.yml` CI workflow enforces registry consistency.

## Repository layout

```text
.
├── .github/workflows/
├── spaces/                 # nine registered live, draft, and local spaces
├── archived-spaces/        # retired examples, not part of the active registry
├── build/                  # build and deployment support
├── docs/                   # architecture and operations documentation
├── gallery/                # registry-generated static gallery
├── scripts/                # registry checks and maintenance tools
├── warm-worker/            # registry-driven monitoring worker
├── spaces.registry.json    # source of truth for active and local spaces
└── README.md
```

## About precomputed Lance data

Yes, you can ship precomputed LanceDB artifacts with the image. There are two valid options:

1. **Build-time precompute**
   - `RUN python -c "from demo import build_dataset; build_dataset()"`
   - Artifacts are baked into the Docker image layers
2. **Commit precomputed artifacts into this repo**
   - Useful when startup determinism is critical
   - Usually requires careful size control (and potentially Git LFS)

For now, this repo builds the dataset at first startup so Hugging Face CPU
Spaces do not reopen LanceDB artifacts from slow Docker overlay layers.

## Dataset mirrors

The ABO catalog demo expects a Hugging Face metadata mirror at
`hyper3labs/amazon-berkeley-objects`. Build and upload that mirror from the
HyperView repo root with:

```bash
uv run --with pyarrow --with huggingface_hub \
  python hyperview-spaces/scripts/mirror_abo_to_hf.py --upload
```

The script writes Parquet configs for `listings`, `images`, `spins`, and
`3dmodels`, preserves original ABO notices, and stores official S3 asset URLs
instead of duplicating image/model binaries. Upload requires a local Hugging
Face token with write access to the `hyper3labs` org.
