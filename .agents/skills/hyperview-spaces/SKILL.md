---
name: hyperview-spaces
description: Author, validate, and ship HyperView demos from the hyperview-spaces repo - add a demo folder, deploy it as a Hugging Face Live Space, export it as a static Shared View bundle, keep the live-spaces and shared-views registries consistent, and satisfy the check_spaces / check_shared_views CI gates.
license: MIT
compatibility: Requires the hyperview-spaces checkout, Python 3.10-3.13, and a HyperView install (`uv run --project ../` from inside the repo, or `uv tool install hyperview`). Deployment needs a Hugging Face account; export needs a locally built workspace.
metadata:
  homepage: https://github.com/Hyper3Labs/hyperview-spaces
---

# HyperView Spaces

`hyperview-spaces` holds the demo sources for HyperView and ships each one in
two delivery modes. Work in this repo means editing a demo folder, then keeping
the registries, workflows, and version pins that describe it consistent.

## The two delivery modes

| | Live Space | Shared View |
| --- | --- | --- |
| What it is | Docker container running a Python HyperView runtime on Hugging Face | Self-contained read-only static bundle |
| Can do | New text queries, new embeddings, recomputed layouts, mutated workspace state | Prepared interactions, pan/zoom/lasso/selection, precomputed similarity, materialized text-search results |
| Cannot do | - | Anything that needs the backend: live embedding of a typed query, new providers |
| Registry | `live-spaces.registry.json` | `shared-views.registry.json` |
| Produced by | Docker build of `demos/<slug>/` | `hyperview export` via `scripts/export_shared_views.py` |
| Hosted at | `huggingface.co/spaces/<owner>/<name>` | Any static host, mounted at `/spaces/<slug>` |

Both come from **one** canonical source under `demos/<slug>/`. There is no
forked "static demo" implementation - if you find yourself writing one, stop and
change the demo folder instead.

## When to use this skill

- Add a new demo, or change an existing one's dataset, models, panels, or copy.
- Deploy or redeploy a Live Space to Hugging Face.
- Regenerate a Shared View bundle after a demo's workspace or panels changed.
- Bump a `hyperview` or `hyper-models` version pin across demos.
- Diagnose a red `check-spaces.yml` run or an unhealthy Space.

## Repository layout

```text
demos/                        canonical source; one folder per use case
shared-views/                 generated read-only bundles (gitignored)
archived-spaces/              retired examples, outside the active registry
scripts/                      registry checks and maintenance tools
gallery/                      registry-generated static gallery
warm-worker/                  registry-driven monitoring worker
docs/                         deployment architecture, data delivery, evidence audit
results/                      reproducible eval output backing demo benchmarks
live-spaces.registry.json     runtime deployments and local runtime demos
shared-views.registry.json    reviewed static artifacts and mount paths
.github/workflows/            per-space deploy, reusable deploy, checks, monitor
```

## Core workflow: add a demo

1. Copy an existing folder: `demos/inat24-tiny-clip-hycoclip` for a geometry
   showcase, `demos/fashion-deepfashion-text-search-clip-hyper3clip` for a
   text-search demo with a custom panel.
2. Edit the constants block at the top of the new `demo.py` (dataset name, HF
   dataset, sample plan, `EMBEDDING_LAYOUTS`). Keep everything editable in that
   one block.
3. Rewrite `README.md`: YAML frontmatter (`title`, `emoji`, `sdk: docker`,
   `app_port: 7860`) plus the H1 and the prose describing what the demo shows.
4. Keep the `Dockerfile` on released PyPI pins. See
   [references/pins-and-checks.md](references/pins-and-checks.md).
5. Register it in `live-spaces.registry.json` (every folder on disk must have an
   entry, and vice versa) **and** add a row for it to the root `README.md`
   community table - both are checked.
6. Add a per-space deploy workflow only for a Hyper3Labs-owned Space; personal
   Spaces deploy manually.
7. Run `uv run --project ../ python scripts/check_spaces.py` until it passes.

Full detail: [references/demo-folder.md](references/demo-folder.md).

## Core workflow: ship a Shared View

```bash
# 1. Build the workspace locally (the exporter reads the local runtime state)
uv run --project ../ python demos/<slug>/demo.py

# 2. Export registered bundles into shared-views/<slug>/
uv run --project ../ python scripts/export_shared_views.py <slug>

# 3. Validate, including the generated bundles
uv run --project ../ python scripts/check_shared_views.py --require-bundles
```

`export_shared_views.py` takes positional slugs; with no arguments it exports
every registered Shared View. The exporter validates its own output, so a green
run means the bundle is a real static export with no backend-only text search
left in it. Detail: [references/shared-views.md](references/shared-views.md).

## Core workflow: deploy a Live Space

Hyper3Labs-owned Spaces deploy from GitHub Actions on a push to `main` that
touches the demo folder, or via `workflow_dispatch`. Authentication is a Hugging
Face **Trusted Publisher** (OIDC) - no long-lived GitHub secret.

Personal-account Spaces are deliberately excluded from deploy CI:

```bash
uv run --project ../ python scripts/deploy_hf_space.py \
  --space-id mnm-matin/HyperView-Logo-Brand-Search \
  --source-dir demos/logo-brand-search-clip-hyper3clip
```

Detail: [references/deployment.md](references/deployment.md).

## Validation

Run both before opening a PR. `check-spaces.yml` runs them in CI.

```bash
uv run --project ../ python scripts/check_spaces.py
uv run --project ../ python scripts/check_shared_views.py
```

`check_spaces.py` enforces registry/disk/workflow agreement, required files,
`sdk: docker` frontmatter, explicit version pins, agreement between a demo's
prose and its Dockerfile pins, cross-demo pin agreement, public-API-only
HyperView imports, and Panel SDK v2 conformance. Every rule and its failure
message: [references/pins-and-checks.md](references/pins-and-checks.md).

## Rules that are easy to get wrong

- **A push to `main` deploys.** Per-space workflows are path-scoped to their
  demo folder. Do not push a pin bump to an unreleased version - the Space will
  rebuild and fail on a PyPI package that does not exist yet.
- **Import HyperView from the top level only.** `from hyperview.something
  import ...` is a hard error; use `import hyperview as hv`. Demo folders are
  the public-API contract test.
- **Versions in prose are checked.** Any `package==version` in a demo's `*.md`
  must match that demo's Dockerfile pin.
- **Demos sharing a model catalog must share its version.** Two demos on
  different `hyper-models` pins silently compute different vectors while both
  claim the same embedding space.
- **`shared-views/` is gitignored.** Bundles are generated artifacts; commit the
  registry entry, never the bundle.
- **`mount_path` must be exactly `/spaces/<slug>`.** The exporter rebases asset
  URLs against it; a mismatch produces a bundle that 404s its own media.
- **A Live Space Dockerfile must set `HYPERVIEW_NO_AUTH=1`.** HyperView 1.0
  mints a session token and rejects unauthenticated runtime commands. A public
  Space has no way to hand visitors that token, so the container starts, the
  healthcheck passes, Hugging Face reports RUNNING, and every visitor gets 401s
  on panel creation and media. The container is the trust boundary here.
- **Do not remove `.hyperview/extensions/` from a copied folder** unless you
  also remove the panel it backs from `demo.py`.
- **A benchmark a demo prints must be regenerable, and its cases must come from
  the same run.** Ship the eval under `scripts/`, point `benchmark.source` at
  it, and include at least one case the baseline wins - a demo whose cases are
  all wins next to a near-even table tells two different stories. See
  [../../../docs/demo-evidence-integrity.md](../../../docs/demo-evidence-integrity.md).
