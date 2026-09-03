---
name: hyperview-spaces
description: Author, validate, and ship HyperView demos from the hyperview-spaces repo - add a demo folder, deploy it as a Hugging Face Live Space, export it as a Static Space bundle, keep the live-spaces and static-spaces registries consistent, and satisfy the check_spaces / check_static_spaces CI gates.
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

| | Live Space | Static Space |
| --- | --- | --- |
| What it is | Docker container running a Python HyperView runtime on Hugging Face | Self-contained read-only bundle served as plain files |
| Can do | New text queries, new embeddings, recomputed layouts, mutated workspace state | Prepared interactions, pan/zoom/lasso/selection, precomputed similarity, materialized text-search results |
| Cannot do | - | Anything that needs the backend: live embedding of a typed query, new providers |
| Registry | `live-spaces.registry.json` | `static-spaces.registry.json` |
| Produced by | Docker build of `demos/<slug>/` | `hyperview export` via `scripts/export_static_spaces.py` |
| Hosted at | `huggingface.co/spaces/<owner>/<name>` | Any static host, at any path |

Both come from **one** canonical source under `demos/<slug>/`. There is no
forked "Static Space" implementation - if you find yourself writing one, stop and
change the demo folder instead.

## When to use this skill

- Add a new demo, or change an existing one's dataset, models, panels, or copy.
- Deploy or redeploy a Live Space to Hugging Face.
- Regenerate a Static Space bundle after a demo's workspace or panels changed.
- Bump a `hyperview` or `hyper-models` version pin across demos.
- Diagnose a red `check-spaces.yml` run or an unhealthy Space.

## Repository layout

```text
demos/                        canonical source; one folder per use case
static-spaces/                generated read-only bundles (gitignored)
archived-spaces/              retired examples, outside the active registry
scripts/                      registry checks and maintenance tools
warm-worker/                  registry-driven monitoring worker
docs/                         deployment architecture, data delivery, evidence audit
results/                      reproducible eval output backing demo benchmarks
live-spaces.registry.json     runtime deployments and local runtime demos
static-spaces.registry.json   reviewed static artifacts
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

## How a demo composes its workspace

A demo says what it wants once, up front, and lets HyperView apply it. Five
calls cover almost everything:

| To do this | Use | Not |
| --- | --- | --- |
| Pin a result list a panel opens on | `session.create_collection(ids, name=...)` | `show_samples(...)` and reading `collection_id` back out of the reply |
| Name a layout | `dataset.find_layout(model=..., modality=..., geometry=...)` | a layout key written down as a constant |
| Open a panel in a particular state | `state=` on the panel | `patch_panel_state(..., replace_state=True)` after `apply_view` |
| Install an extension | `hv.launch(..., extensions=[EXTENSION_DIR])` | `add_extension` squeezed between `launch` and `apply_view` |
| Set a documented panel prop | the typed keyword: `mode=`, `collection_id=`, `rank=`, `label_field=` | a raw camelCase `props={...}` entry |

Two of these are about durability rather than taste. A collection made by
`create_collection` lives in workspace state, so a static export keeps it; the
transient one a `show_samples` call leaves behind does not, and the exported
Space opens on the whole dataset instead of the shortlist the demo authored. And
a layout key carries a content hash of the embedding and projection parameters,
so it cannot be known before the layout is computed - a constant copied into
`demo.py` is correct until the next rebuild and silently wrong after it.
`find_layout` returns `None` when nothing matches and raises when more than one
does, so describe the layout until one is left. One model routinely has both an
image-only and a multimodal space in the same dataset; `modality=` is the only
thing that separates them.

## Core workflow: ship a Static Space

```bash
# 1. Build the workspace locally (the exporter reads the local runtime state)
HYPERVIEW_BUILD_ONLY=1 uv run --project ../ python demos/<slug>/demo.py

# 2. Export registered bundles into static-spaces/<slug>/
uv run --project ../ python scripts/export_static_spaces.py <slug>

# 3. Validate, including the generated bundles
uv run --project ../ python scripts/check_static_spaces.py --require-bundles
```

`HYPERVIEW_BUILD_ONLY=1` (or the `--build-only` flag) is what makes step 1
finish. Without it every `demo.py` builds its workspace and then serves it
forever, which is right for a container and wrong for an export: the shell
never comes back. With it the demo builds, prints, and exits, leaving exactly
the durable workspace the exporter reads.

`export_static_spaces.py` takes positional slugs; with no arguments it exports
every registered Static Space. The exporter validates its own output, so a green
run means the bundle is a real static export with no backend-only text search
left in it. Detail: [references/static-spaces.md](references/static-spaces.md).

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
uv run --project ../ python scripts/check_static_spaces.py
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
- **`static-spaces/` is gitignored.** Bundles are generated artifacts; commit the
  registry entry, never the bundle.
- **Bundles are location-independent.** They reference assets relatively and
  resolve API and media from the document URL, so the same files work at any
  path. A bundle that records a `mount_path` predates this and must be
  re-exported.
- **A Live Space Dockerfile must set `HYPERVIEW_NO_AUTH=1`.** HyperView 1.0
  mints a session token and rejects unauthenticated runtime commands. A public
  Space has no way to hand visitors that token, so the container starts, the
  healthcheck passes, Hugging Face reports RUNNING, and every visitor gets 401s
  on panel creation. The flag marks the server public rather than open:
  visitors keep the viewer commands (panels, selection, retrieval,
  collections), while provider registration, extension install, tool execution
  and compute answer 403. A demo that needs one of those on a public Space is
  a demo to rethink, not a reason to widen the allowlist.
- **Every `demo.py` must exit under `HYPERVIEW_BUILD_ONLY=1`.** A demo that
  serves anyway cannot be exported or build-checked without a server left
  running behind it.
- **Do not remove `.hyperview/extensions/` from a copied folder** unless you
  also remove the panel it backs from `demo.py`.
- **A benchmark a demo prints must be regenerable, and its cases must come from
  the same run.** Ship the eval under `scripts/`, point `benchmark.source` at
  it, and include at least one case the baseline wins - a demo whose cases are
  all wins next to a near-even table tells two different stories. See
  [../../../docs/demo-evidence-integrity.md](../../../docs/demo-evidence-integrity.md).
