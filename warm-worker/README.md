# HyperView warm-worker

Cloudflare Worker for Layer 1 of `docs/deployment-architecture.md`: keep registered Hugging Face Spaces warm, publish the latest status snapshot, expose embeddable status badges, and serve the generated demos gallery as static assets.

The Worker imports `../spaces.registry.json` at build time. Wrangler bundles JSON imports, so each deploy contains the registry version present in the repo at deploy time. The gallery is generated from the same registry into `../gallery/out/index.html`.

## Gallery build

From `warm-worker/`:

```sh
npm run build:gallery
```

This runs `node ../gallery/build.mjs`, reads `../spaces.registry.json`, and writes `../gallery/out/index.html`. By default status badges use same-origin URLs such as `/badge/inat24-tiny.svg`. To point badges at another deployed Worker, set `WARM_WORKER_URL`:

```sh
WARM_WORKER_URL=https://hyperview-warm-worker.example.workers.dev npm run build:gallery
```

## One-time setup

1. Install dependencies:

   ```sh
   cd warm-worker
   npm install
   ```

2. Log in to Cloudflare:

   ```sh
   npx wrangler login
   ```

3. Create the KV namespace and preview namespace:

   ```sh
   npx wrangler kv namespace create STATUS
   npx wrangler kv namespace create STATUS --preview
   ```

4. Paste the returned `id` and `preview_id` into `wrangler.toml`, replacing the `00000000000000000000000000000000` placeholders.

## Deploy

From `warm-worker/`:

```sh
npm run build:gallery
npm run deploy
```

The cron trigger runs every 5 minutes:

```toml
crons = ["*/5 * * * *"]
```

## Endpoints

- `GET /status.json` returns the latest KV snapshot with CORS enabled.
- `GET /badge/<demo_slug>.svg` returns a small SVG badge.
- `GET /` serves the generated demos gallery from `../gallery/out`.
- `GET /status` returns a minimal HTML table of all monitored Spaces.

## Replacing the GitHub monitor

Once this Worker is deployed and `/status.json` shows fresh checks, `.github/workflows/monitor-hf-spaces.yml` is redundant. The Worker runs the monitoring loop inside Cloudflare instead of GitHub Actions, writes durable snapshots to KV, and wakes sleeping Spaces by requesting their health or root URL.

## Budget math

On the Workers Paid plan included limits from `docs/deployment-architecture.md`:

- Cron invocations: 288/day, about 8.6k/month, within 10M requests/month.
- Space/API subrequests: 6 current warm Spaces x 2 requests x 288/day, about 104k/month. Worker subrequests are not billed as top-level requests.
- KV writes: one latest snapshot plus one history write per Space per cron, currently 7 x 288/day, about 60k/month, within 1M writes/month.
- KV reads: one history read per Space per cron plus public status reads, well inside 10M reads/month at expected traffic.
- CPU: small JSON parsing and short fetch orchestration per cron, far below the 30M CPU-ms/month included limit.

The per-space history is capped at 288 entries, so KV storage stays small.
