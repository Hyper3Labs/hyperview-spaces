# Deploying and monitoring Live Spaces

## Registry entry

`live-spaces.registry.json` (`version: 2`) holds a `spaces` list and a
`known_conflicts` list. One entry per demo folder:

```json
{
  "space_id": "hyper3labs/HyperView-ABO-Catalog",
  "folder": "demos/abo-catalog-clip-hycoclip",
  "demo_slug": "abo-catalog",
  "demo_name": "HyperView - ABO Catalog",
  "description": "Inspect product-catalog neighborhoods across CLIP and Hyper3-CLIP embeddings.",
  "expected_dataset": "abo_catalog_clip_hyper3clip_side_by_side",
  "keep_warm": true,
  "status": "live",
  "deploy_targets": ["hf-docker"]
}
```

- `folder` must start with `demos/`, be unique, and exist on disk. Every folder
  on disk must have an entry - adding a demo folder without registering it fails
  CI.
- `space_id` is a non-empty string, or `null` for a demo with no Space yet.
- `status` is one of `live`, `draft`, `local`.
- `deploy_targets` is a list drawn from `hf-docker`, `hf-static`, `cf-static`.
  Only `hf-docker` requires a matching deploy workflow.
- `keep_warm: true` requires a non-null `space_id` - you cannot ping nothing.
- `expected_dataset` is the dataset name the monitor expects the Space to serve.

### known_conflicts

When a registry `space_id` legitimately differs from the one its workflow
deploys to, record it as a `space_id_mismatch` entry with a `reason` and it
downgrades to a warning. A conflict entry that no longer matches reality is
itself an error, so stale exceptions cannot accumulate.

## Ownership decides the deploy path

| Owner | Deploy | Registered | Monitored |
| --- | --- | --- | --- |
| `hyper3labs/*` | GitHub Actions workflow, Trusted Publisher | yes | yes |
| Personal account (`mnm-matin/*`) | `scripts/deploy_hf_space.py`, manual | yes | yes |

Personal Spaces are deliberately excluded from deploy CI. Do not add a
long-lived Hugging Face token as a GitHub secret to work around this.

## Org-owned: the workflow pair

A per-space workflow watches one folder and calls the reusable one:

```yaml
name: Deploy HF Space - HyperView ABO Catalog
on:
  push:
    branches: [main]
    paths:
      - demos/abo-catalog-clip-hycoclip/**
      - .github/workflows/deploy-hf-space-abo-catalog.yml
      - .github/workflows/deploy-hf-space-reusable.yml
  workflow_dispatch:
concurrency:
  group: deploy-hf-space-abo-catalog
  cancel-in-progress: false
jobs:
  deploy:
    permissions: { contents: read, id-token: write }
    uses: ./.github/workflows/deploy-hf-space-reusable.yml
    with:
      source_dir: demos/abo-catalog-clip-hycoclip
      space_id: hyper3labs/HyperView-ABO-Catalog
```

To add one, copy `deploy-hf-space-hyperview.yml` and update `name`,
`concurrency.group`, `paths`, `source_dir`, and `space_id`. `check_spaces.py`
requires exactly one workflow per `hf-docker` folder, and its `space_id` must
match the registry's.

The reusable workflow installs `huggingface_hub>=1.19`, asserts the source
folder has a `README.md` and a `Dockerfile`, and syncs the folder to the Space
root. `id-token: write` plus `HF_OIDC_RESOURCE=spaces/<owner>/<name>` is what
lets Hugging Face issue a short-lived, repo-scoped token - **no long-lived
GitHub secret is required**.

### Trusted Publisher setup

On the Hugging Face Space, add a Trusted Publisher for:

- Repository `Hyper3Labs/hyperview-spaces`
- Branch `main`
- The **exact** caller workflow filename, e.g.
  `deploy-hf-space-abo-catalog.yml`

Renaming the workflow file breaks the trust relationship until the Space's
Trusted Publisher entry is updated to match.

## Personal-account: manual deploy

```bash
uv run --project ../ python scripts/deploy_hf_space.py \
  --space-id mnm-matin/HyperView-Logo-Brand-Search \
  --source-dir demos/logo-brand-search-clip-hyper3clip
```

Requires `huggingface_hub` and a local login with write access to the Space. It
creates the Docker Space if it does not exist, then synchronizes the folder.

## Deploy triggers are a hazard

A push to `main` touching a demo folder rebuilds that Space immediately. Before
pushing:

- Do not bump a pin to a version that is not on PyPI yet. The Space will rebuild
  and fail on `pip install hyperview==<unreleased>`.
- Publish the package first, then push the pin bump.
- To stage changes without deploying, keep them on a branch. `check-spaces.yml`
  runs on branches; the deploy workflows are `main`-only.

## Monitoring and keep-warm

```bash
uv run --project ../ python scripts/monitor_spaces.py --fail-on-unhealthy
```

| Flag | Default | Meaning |
| --- | --- | --- |
| `--registry` | `live-spaces.registry.json` | Registry to read |
| `--output` | `space-status.json` | Where the status report is written |
| `--api-timeout` | `10.0` | Seconds for the HF API call |
| `--health-timeout` | `10.0` | Seconds for `/__hyperview__/health` |
| `--wake-wait-seconds` | `60.0` | Grace period for a sleeping Space to wake |
| `--fail-on-unhealthy` | off | Exit nonzero unless every monitored Space wakes and passes |

`monitor-hf-spaces.yml` runs this on a schedule; `warm-worker/` is the
registry-driven worker that keeps `keep_warm: true` Spaces from sleeping. The
monitor covers personal Spaces even though it does not deploy them.

## First-boot cost

A CPU Space builds its dataset and downloads model weights on first start.
Expect tens of minutes before the health endpoint answers, which is why the
Dockerfile `HEALTHCHECK` uses `--start-period=2700s`. Two ways to shorten it,
both documented in the repo README:

1. Precompute at build time (`RUN python -c "from demo import build_dataset;
   build_dataset()"`), baking LanceDB artifacts into image layers.
2. Commit precomputed artifacts, with size control and probably Git LFS.

The repo currently builds at first startup instead, so Hugging Face CPU Spaces
do not reopen LanceDB artifacts through slow Docker overlay layers.
