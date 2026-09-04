# HyperView Spaces — Deployment Architecture

Status: design accepted July 2026; Layer 3 (bundle-backed Live Spaces)
shipped September 2026. Constraint: **no infra spend beyond the
existing Cloudflare Workers Paid ($5/mo) plan's included allowances.**
Cloudflare Containers are explicitly out — too expensive; the plan's
generous Workers/KV/static-asset allowances are the target.

## Current operational layout (September 2026)

- `live-spaces.registry.json` is the canonical inventory for every source demo,
  its Hugging Face target, desired lifecycle state, and gallery copy.
- `static-spaces.registry.json` attaches reviewed exported bundles to that
  inventory. It is not a second marketing catalog.
- `spaces.hyper3labs.com/<slug>/` is already deployed as one Cloudflare Worker
  with Static Assets. The custom domain is declared in
  `spaces-site/wrangler.jsonc`; all bundles share that one deployment.
- `hyper3labs.com/spaces/` is the collection page. Its catalog JSON is generated
  from both registries, and it refreshes runtime stages from
  `https://spaces.hyper3labs.com/status.json`. Paused and broken entries remain
  visible with an explicit status.
- `.github/workflows/monitor-hf-spaces.yml` checks the registered Live Spaces
  hourly. The Worker status endpoint is the low-latency public view; Actions is
  the independent failing CI signal.
- `.github/workflows/deploy-cloudflare-spaces.yml` assembles the six reviewed
  bundles from `Hyper3Labs/hyper3labs.github.io`, validates the Worker upload,
  and deploys after loading Cloudflare credentials from Infisical with GitHub
  OIDC. Until `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` exist in the
  Infisical `prod` environment and the two public identity/project variables
  are configured, it deliberately stops after a green dry-run.

The intended URL contract is therefore:

| URL | Responsibility |
| --- | --- |
| `hyper3labs.com/spaces/` | Branded collection and status-aware catalog |
| `spaces.hyper3labs.com/<slug>/` | Canonical Static Space artifacts |
| `<owner>-<space>.hf.space` | Live HyperView runtime when the use case needs one |

Cloudflare is the canonical home for Static Spaces: one custom domain, no cold
starts, one deploy, and a status API. Hugging Face is the right home for Live
Spaces because it runs the Python/Docker runtime and is useful for ecosystem
discovery. An HF Static Space can be a mirror, but making it the primary static
fleet would duplicate repositories and deployment state.

## Hugging Face Trusted Publisher recovery

`invalid_grant` is an exchange failure, not a generic application error. For
each org-owned Space, remove and recreate the Trusted Publisher with exact
claims:

1. Repository: `Hyper3Labs/hyperview-spaces`.
2. Branch: `main`.
3. Workflow: the exact per-Space caller filename, for example
   `deploy-hf-space-hyperview.yml`—not the reusable workflow filename.
4. GitHub job permission: `id-token: write`.
5. Environment: `HF_OIDC_RESOURCE=spaces/<owner>/<Space>` and
   `huggingface_hub>=1.19`.

Then rerun only that Space's `workflow_dispatch`. If the exchange still fails,
confirm the target repo exists, the org account is writable/not plan-blocked,
and the account is not locked. The emergency path is a narrowly scoped
`HF_TOKEN` injected from Infisical; it should not become a GitHub secret or a
file in either repository. A deployment token only writes the Space repository.
A gated runtime model such as `hyper3-clip-v0.5` separately needs an `HF_TOKEN`
configured as a Hugging Face Space secret, or the model and embeddings must be
prepared in a bundle before deployment.

Product decision (Matin, 2026-07-04): hosted demos are allowed to be
**read-only**, in the style of the FiftyOne and Rerun examples galleries.
A visitor explores a fully interactive client-side workspace (pan/zoom,
panels, selection, neighbor browsing, curated queries) but cannot mutate
server state — because there is no server. Anyone who wants the mutable
experience runs `pip install hyperview` locally; the demo page says exactly
that. This removes the hardest constraint on Cloudflare hosting: nothing
about the read-only path needs Python at request time.

## The actual problem

A demo Space is a Docker container that, on cold start, installs nothing
(baked) but **downloads the dataset and re-embeds it with CPU PyTorch** —
the healthcheck allows a 45-minute start period. HF free Spaces sleep after
inactivity, so a prospect clicking a demo from hyper3labs.com can hit a dead
page. Keep-warm pinging treats the symptom. The cause is that we compute at
serve time what should be computed at deploy time.

The Fashion, GeoSpatial, and Logo demos have since moved off that path: they
open a dataset prepared ahead of time rather than building one at boot. That
is the right direction, but it is not finished — see
[prepared-demo-data.md](prepared-demo-data.md).

Fix in two layers:

1. **Keep-warm + status monitoring on Cloudflare** (today, cheap, no HyperView
   changes) — stop demos from being dead links.
2. **Static Spaces** (after HyperView `hyperview export`, see
   `docs/refactor-plan-2026-07.md` Phase 4) — most demos stop needing a
   server at all, which makes them deployable to HF *and* Cloudflare for
   free, with zero cold start, permanently.

## Layer 1: `warm-worker` (implement now)

One Cloudflare Worker, cron-triggered, driven by `live-spaces.registry.json`:

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
`src/index.ts`, reading a build-time copy of `live-spaces.registry.json`.
Deploy: `npx wrangler deploy` (manual) — no CI secrets needed initially.

## Layer 2: Static Spaces (the real fix)

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

### Interactivity budget for a Static Space

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

### Custom panels in a Static Space

Demos rely on custom/extension panels (readout panels etc.). These already
ship as JS modules loaded by `RuntimeModulePanel`, so they work unchanged in
a Static Space: the export includes the extension panel modules and their
declared `PanelDefinition`s in the snapshot. Panel *state* changes (tab
focus, filters, selected sample) stay client-side and ephemeral — exactly
the read-only contract. Commands that would mutate runtime state are
disabled with a visible "read-only demo — run locally for the full
workbench" affordance, which doubles as the pip-install CTA.

### The demos index

The landing site `/spaces` page (hyper3labs.github.io) lists every
demo with a thumbnail, one-line story, live status badge (from
`warm-worker` for the remaining Docker Spaces; Static Spaces are always
"live"), and links. Served from the same Cloudflare Worker static assets as
the landing page (e.g. `hyper3labs.com/demos`), generated from
`live-spaces.registry.json` so the registry stays the single source of truth.

### What stays out of scope

- No Cloudflare Containers / Durable Objects compute for demos (paid paths;
  Containers explicitly rejected on cost).
- LanceDB remains the storage backend for the real product; Static Spaces
  are an export format, not a storage migration.

## Layer 3: one bundle, two hosts (shipped September 2026)

Layer 2 assumed a demo was either a Live Space *or* a Static Space. In practice
the split fell differently: the export turned out to be restore-capable, so
`hyperview serve --from <bundle>` brings the whole prepared workspace back up
behind a real server. The bundle is therefore the unit of delivery for both
hosts — the site serves it as files, and a container serves it as a Live Space.

That closes the failure Layer 2 did not: a demo whose data was curated locally
(DeepFashion, Logo, GeoSpatial) has nothing to rebuild from inside a container.
`demo.py` fails at boot and the Space sits in `RUNTIME_ERROR` — which is
exactly where DeepFashion was. Deploying the bundle instead of the folder means
the container restores prepared data rather than recomputing data it does not
have.

`live-spaces.registry.json` now records which of the two paths each Space takes:

| `deploy_mode` | Uploaded to the Space | Image | First boot |
| --- | --- | --- | --- |
| `docker-folder` | `demos/<slug>/` | The demo's own `Dockerfile`; `CMD python demo.py` | Downloads and re-embeds the corpus — tens of minutes |
| `live-bundle` | The exported bundle plus a generated `Dockerfile` and Space README | `pip install hyperview[...]`, then `hyperview serve --from bundle --public` | Restores the bundle — seconds |

A `live-bundle` entry also carries `bundle_slug`, the slug of the
`static-spaces.registry.json` entry whose `live_space_id` is this Space. The
two registries have to agree, and `check_spaces.py` fails the build if they do
not: one bundle, two hosts, named the same way on both sides.

Both modes still produce an HF **Docker** Space, so `deploy_targets` keeps
`hf-docker` either way. What changed is who writes the Dockerfile — the demo
folder, or `hyperview publish --mode live`.

### Where the bundle comes from

The exported bundles are committed to the landing site repository
(`Hyper3Labs/hyper3labs.github.io`, `public/spaces/<slug>/`), because the site
serves them as Static Spaces. Rather than keep a second copy here, the deploy
job checks that repository out and publishes from it.

The consequence is that the two repositories are coupled by a manual step: a
re-exported bundle committed on the site does not deploy itself. Re-mount the
bundle on the site, then trigger the Space's workflow here — `workflow_dispatch`
by hand, or a `static-bundle-published` repository dispatch from an automation
that has a token for this repository.

Authentication is unchanged from Layer 1's workflows and deliberately so:
`id-token: write` plus `HF_OIDC_RESOURCE=spaces/<owner>/<name>` lets
huggingface_hub exchange the GitHub Actions OIDC id token for a short-lived,
Space-scoped Hugging Face token, and `hyperview publish` picks it up through
the ordinary `HfApi()` token resolution. No long-lived secret, and no caller
workflow was renamed — the Trusted Publisher on each Space is keyed to the
caller's *filename*, so a rename silently breaks the deploy until the Space's
entry is updated to match.

Before the upload, the job runs `hyperview publish --dry-run`, which renders
the Dockerfile and the Space README without touching the network. A bundle that
cannot be read, or a pin pip could never resolve, fails there rather than
half-way through replacing a working Space.

### The cap that actually binds

The `hyper3labs` org runs **at most three concurrent `cpu-basic` Spaces**. A
fourth will not start, whatever the registry says. `keep_warm` and `status`
describe intent — which Spaces should be warm, which are real — and neither the
workflows nor `check_spaces.py` enforce the cap, because the cap is an account
property rather than a repository one. Turning a Space on therefore means
turning one off first.

`live-bundle` does not raise the cap, but it makes each slot cheaper to give
up: a bundle-backed Space comes back in seconds instead of rebuilding its
corpus, so parking one is no longer a decision to be avoided.

## Rollout order

1. `warm-worker` live (Layer 1) — kills dead-demo links this week.
2. HyperView Phase 1 & 4 land `hyperview export`.
3. Port `inat24-tiny` (flagship) to a Static Space; deploy to **both** an HF
   static Space and Workers static assets; verify parity.
4. Port remaining showcase demos; flip hyper3labs.com embeds to the static
   URLs; keep-warm list shrinks to genuinely dynamic Spaces only.
5. Switch the org-owned Spaces that have a bundle to `deploy_mode:
   live-bundle` (Layer 3), so the Live Space and the Static Space are the same
   export. DeepFashion first — it was the one in `RUNTIME_ERROR` — then ABO
   Catalog.
