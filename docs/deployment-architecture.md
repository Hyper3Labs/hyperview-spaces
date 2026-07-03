# HyperView Spaces — Deployment Architecture

Status: design accepted July 2026. Constraint: **no infra spend beyond the
existing Cloudflare Workers Paid ($5/mo) plan's included allowances.**
Cloudflare Containers are explicitly out — too expensive; the plan's
generous Workers/KV/static-asset allowances are the target.

Product decision (Matin, 2026-07-04): hosted demos are allowed to be
**read-only**, in the style of the FiftyOne and Rerun examples galleries.
A visitor explores a fully interactive client-side workspace (pan/zoom,
panels, selection, neighbor browsing, curated queries) but cannot mutate
server state — because there is no server. Anyone who wants the mutable
experience runs `pip install hyperview` locally; the demo page says exactly
that. This removes the hardest constraint on Cloudflare hosting: nothing
about the read-only path needs Python at request time.

## The actual problem

Every demo Space is a Docker container that, on cold start, installs nothing
(baked) but **downloads the dataset and re-embeds it with CPU PyTorch** —
the healthcheck allows a 45-minute start period. HF free Spaces sleep after
inactivity, so a prospect clicking a demo from hyper3labs.com can hit a dead
page. Keep-warm pinging treats the symptom. The cause is that we compute at
serve time what should be computed at deploy time.

Fix in two layers:

1. **Keep-warm + status monitoring on Cloudflare** (today, cheap, no HyperView
   changes) — stop demos from being dead links.
2. **Static demo bundles** (after HyperView `hyperview export`, see
   `docs/refactor-plan-2026-07.md` Phase 4) — most demos stop needing a
   server at all, which makes them deployable to HF *and* Cloudflare for
   free, with zero cold start, permanently.

## Layer 1: `warm-worker` (implement now)

One Cloudflare Worker, cron-triggered, driven by `spaces.registry.json`:

- Every 5 minutes: `GET` each registered space's `/__hyperview__/health`
  (falls back to the Space root URL), record `{space_id, status, latency_ms,
  hyperview_version, checked_at}`.
- Write the latest snapshot to KV (`STATUS` namespace); keep a small rolling
  history (last 288 checks) per space.
- Serve `GET /status.json` (all spaces) and `GET /badge/{demo_slug}.svg`
  (tiny status badge, embeddable on hyper3labs.com).
- On transition RUNNING→anything else, the ping itself is the wake-up call
  (requesting a sleeping HF Space triggers rebuild/restart).

Budget check against the $5 plan's included allowances (10M requests/mo,
30M CPU-ms/mo; KV: 10M reads, 1M writes, 1GB):

| Item | Usage | Included |
|---|---|---|
| Cron invocations | 288/day ≈ 8.6k/mo | part of 10M req |
| Subrequests (8 spaces × 288) | ~70k/mo | free (subrequests uncounted) |
| KV writes | ~8.6k/mo | 1M |
| CPU | ms-scale per run | 30M ms |

Two orders of magnitude of headroom. The GitHub Actions
`monitor-hf-spaces.yml` workflow becomes redundant and can be retired once
the worker is live.

Repo layout: `warm-worker/` with `wrangler.toml` (cron trigger `*/5 * * * *`),
`src/index.ts`, reading a build-time copy of `spaces.registry.json`.
Deploy: `npx wrangler deploy` (manual) — no CI secrets needed initially.

## Layer 2: static demo bundles (the real fix)

`hyperview export` (HyperView Phase 4) produces a self-contained bundle:
static frontend + runtime snapshot JSON + materialized collections + sample
records + thumbnails + precomputed layout coordinates + precomputed
embeddings for the demo's samples.

One bundle, three interchangeable free hosts:

| Target | How | Cold start | Cost |
|---|---|---|---|
| **HF static Space** (`sdk: static`) | push bundle to Space repo | none — static Spaces never sleep | free |
| **Cloudflare Workers static assets** | `wrangler deploy` with `assets` dir | none | free/unlimited on any Workers plan |
| (fallback) any static host / GitHub Pages | copy bundle | none | free |

Registry change: each entry gains
`"deploy_targets": ["hf-docker" | "hf-static" | "cf-static"]` and the deploy
workflows dispatch accordingly. Demos stay on `hf-docker` only if they truly
need live Python (agent-driven demos); showcase demos move to static.

### Interactivity budget for static demos

- Browsing, panels, layouts, selection, neighbor exploration: precomputed
  collections + embeddings shipped in the bundle; nearest-neighbor over
  ≤5k samples × 512-d float32 (~10 MB) is a trivial client-side dot product.
- Free-text search (the CLIP text tower) has three options, in order:
  1. **Precomputed query gallery** (default): the demo ships curated queries
     with precomputed embeddings — matches how the demos are actually used
     in sales conversations.
  2. **Client-side text encoder** (flagship demos): ONNX-quantized
     hyper3-clip text tower via transformers.js, cached by the browser.
  3. Never: a paid inference endpoint.

### Custom panels in static bundles

Demos rely on custom/extension panels (readout panels etc.). These already
ship as JS modules loaded by `RuntimeModulePanel`, so they work unchanged in
a static bundle: the export includes the extension panel modules and their
declared `PanelDefinition`s in the snapshot. Panel *state* changes (tab
focus, filters, selected sample) stay client-side and ephemeral — exactly
the read-only contract. Commands that would mutate runtime state are
disabled with a visible "read-only demo — run locally for the full
workbench" affordance, which doubles as the pip-install CTA.

### The demos gallery

One static index page (FiftyOne/Rerun-style examples gallery) listing every
demo with a thumbnail, one-line story, live status badge (from
`warm-worker` for the remaining Docker Spaces; static bundles are always
"live"), and links. Served from the same Cloudflare Worker static assets as
the landing page (e.g. `hyper3labs.com/demos`), generated from
`spaces.registry.json` so the registry stays the single source of truth.

### What stays out of scope

- No Cloudflare Containers / Durable Objects compute for demos (paid paths;
  Containers explicitly rejected on cost).
- LanceDB remains the storage backend for the real product; static bundles
  are an export format, not a storage migration.

## Rollout order

1. `warm-worker` live (Layer 1) — kills dead-demo links this week.
2. HyperView Phase 1 & 4 land `hyperview export`.
3. Port `inat24-tiny` (flagship) to a static bundle; deploy to **both** an HF
   static Space and Workers static assets; verify parity.
4. Port remaining showcase demos; flip hyper3labs.com embeds to the static
   URLs; keep-warm list shrinks to genuinely dynamic Spaces only.
