# Shared Views: export, registry, and mounting

A Shared View is a generated read-only bundle of a HyperView workspace. It keeps
the full HyperView shell and the demo's prepared interactions, and it is served
as ordinary static files with no Python and no container.

## What is in a bundle

`hyperview export` writes a self-contained directory:

- Paged collections and sharded sample records
- Sample media and thumbnails **baked in as files** - a bundle makes no external
  fetches, so it does not depend on the dataset it came from still being online
- Optional precomputed similarity (`similarity_k` nearest neighbors per sample)
- Materialized text-search results for the demo's prepared queries
- A manifest declaring static mode, export warnings, and the panels present
- Mount-path rebasing so the bundle can be served from a subdirectory

The tradeoff: a Shared View can replay the queries that were materialized at
export time. It cannot embed a query typed by the visitor - that needs a text
tower, which needs the Python runtime, which means a Live Space.

## Registry entry

`shared-views.registry.json` holds one entry per bundle:

```json
{
  "slug": "abo-catalog",
  "name": "ABO Catalog",
  "source_folder": "demos/abo-catalog-clip-hycoclip",
  "workspace_id": "abo-catalog-clip-hyper3clip-split",
  "walkthrough_panel_id": "catalog-hierarchy-readout",
  "bundle_folder": "shared-views/abo-catalog",
  "live_space_id": "hyper3labs/HyperView-ABO-Catalog",
  "live_url": "https://hyper3labs-hyperview-abo-catalog.hf.space",
  "similarity_k": 10
}
```

Field rules enforced by `check_shared_views.py`:

- `slug` unique and non-empty; `source_folder` unique and pointing at a real
  `demos/` folder
- `bundle_folder` must be `shared-views/<slug>`
- the bundle must not record a `mount_path`; bundles reference their assets
  relatively and resolve API and media from the document URL, so one that pins
  a prefix came from an old HyperView and needs re-exporting
- `workspace_id` and `walkthrough_panel_id` non-empty strings
- `live_space_id` / `live_url` may be null for a static-only view

## Export

```bash
# Build or refresh the workspace first - the exporter reads local runtime state,
# so a stale workspace exports a stale bundle with no warning.
uv run --project ../ python demos/<slug>/demo.py

# All registered views, or just the named slugs
uv run --project ../ python scripts/export_shared_views.py
uv run --project ../ python scripts/export_shared_views.py abo-catalog fashion-products
```

The script runs `hyperview export <workspace_id>` into `shared-views/<slug>`
for each entry, then calls `check_shared_views.py` on the results. Passing an
unknown slug is an error, not a silent no-op.

## Validate

```bash
uv run --project ../ python scripts/check_shared_views.py                    # registry only
uv run --project ../ python scripts/check_shared_views.py --require-bundles  # registry + generated output
```

Without `--require-bundles` a missing bundle is tolerated, which is what CI
wants: `shared-views/` is gitignored, so a clean checkout has no bundles to
check. Use `--require-bundles` locally after an export, and in any job that
actually generates them.

Bundle-level checks, each one a distinct failure message:

| Check | Why it exists |
| --- | --- |
| Manifest identifies a HyperView static export | Catches an empty or wrong output directory |
| Manifest declares static mode | A bundle exported in the wrong mode still expects a backend |
| No export warnings | Warnings mean content was dropped or degraded |
| No backend-only text search exposed | The bundle would show a search box that cannot answer |
| `walkthrough_panel_id` present in the bundle | The panel carrying the demo's narrative silently vanished |

## Hosting

Bundles are plain static files, and location-independent - the same files work
at a domain root or at any path inside a containing site:

- Cloudflare Workers Static Assets - `hyperview export` writes a
  `wrangler.jsonc`, so `npx wrangler deploy` from the bundle directory works
- Any static host or CDN. The site convention is `/spaces/<slug>`, but nothing
  in the bundle depends on it
- Locally, any static file server rooted at the directory holding `spaces/`

`gallery/build.mjs` generates the static gallery from the registries; it is the
index page over the exported bundles.

## Choosing a mode

Use a **Shared View** when the demo replays prepared evidence: fixed queries,
fixed comparisons, a walkthrough panel telling the story. This is the default -
it costs nothing to run, cannot go down, and starts instantly.

Use a **Live Space** only when the interaction genuinely requires the runtime:
a visitor typing their own query, a provider being registered, layouts being
recomputed. Each Live Space is a container that has to stay warm, cold-starts
slowly on CPU hardware, and can be observed broken.
