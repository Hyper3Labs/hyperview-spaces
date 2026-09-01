# iNat24 static export runbook

This produces the read-only iNat24 Tiny flagship as a self-contained static
bundle. It uses the static-export implementation from the parent HyperView
checkout, not the released `hyperview==0.6.2` wheel. Panel state is browser-local
and ephemeral; the bundle has no Python server or live text-query inference.

## Regenerate

Run from the `hyperview-spaces` repository. The output and persistent build data
stay outside both Git repositories.

```bash
export SPACES_REPO="$PWD"
export HYPERVIEW_REPO="$(cd .. && pwd)"
export SCRATCH="/private/tmp/claude-501/-Users-matin-hyperview-org-HyperView/f7346073-26ff-4faa-85e8-f42c5932e582/scratchpad"
export VENV="$SCRATCH/inat-static-venv"
export STATIC_DATA="$SCRATCH/static-inat24-data"
export OUT="$SCRATCH/static-inat24"

python3.12 -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade pip
"$VENV/bin/python" -m pip install \
  "hyperview==1.0.0" \
  "hyper-models[ml]==0.3.1" \
  "datasets>=4.5.0" \
  "Pillow>=12.0.0"

mkdir -p "$STATIC_DATA"
PYTHONPATH="$HYPERVIEW_REPO/src" \
HYPERVIEW_DATASETS_DIR="$STATIC_DATA/datasets" \
HYPERVIEW_MEDIA_DIR="$STATIC_DATA/media" \
HF_HOME="$STATIC_DATA/hf" \
PYTHONUNBUFFERED=1 \
"$VENV/bin/python" - <<'PY'
import json
import os
import runpy
from pathlib import Path

space = runpy.run_path(
    str(Path(os.environ["SPACES_REPO"]) / "demos/inat24-tiny-clip-hycoclip/demo.py")
)
dataset = space["build_dataset"]()
session = space["hv"].launch(
    dataset,
    host="127.0.0.1",
    port=17861,
    open_browser=False,
    block=False,
)
try:
    result = session.export(Path(os.environ["OUT"]))
    print(json.dumps(result, indent=2, sort_keys=True))
finally:
    session.stop()
PY
```

The verified 300-sample export was made with a pre-1.0 development build,
HyperView `0.6.3.dev0+g1ddcd10b5.d20260613`. It contains 643 files, 3 layouts, and 600
media/thumbnail files. `Session.export()` reported **24,789,132 bytes (23.64
MiB)**; `du -sh` reports **25M**. This is far below the 1 GB caution threshold
for Hugging Face static Spaces and Cloudflare static assets.

## Verify

Run the exporter tests without writing pytest caches into the parent checkout:

```bash
"$VENV/bin/python" -m pip install pytest pytest-asyncio
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$HYPERVIEW_REPO/src" \
  "$VENV/bin/python" -m pytest -p no:cacheprovider -q \
  "$HYPERVIEW_REPO/tests/test_static_export.py"
```

Serve and spot-check the bundle:

```bash
du -sh "$OUT"
find "$OUT" -type f | wc -l
(cd "$OUT" && python3 -m http.server 18080)

curl -fI http://127.0.0.1:18080/
curl -fI http://127.0.0.1:18080/_next/static/chunks/f29dd35a99c216ea.js
curl -fI http://127.0.0.1:18080/api/runtime.json
curl -fI http://127.0.0.1:18080/api/dataset.json
curl -fI http://127.0.0.1:18080/api/samples/index.json
curl -fI http://127.0.0.1:18080/api/samples/shards/000000.json
curl -fI http://127.0.0.1:18080/api/embeddings/default.json
curl -fI http://127.0.0.1:18080/hyperview-static.json
```

Chunk filenames are frontend-build-specific; after a later HyperView build,
take the replacement path from `index.html`. A successful export also has
`window.__HYPERVIEW_STATIC__ = true;` in `index.html`, schema version 1 in
`hyperview-static.json`, and `not_found_handling` set to
`single-page-application` in `wrangler.jsonc`.

## Deploy manually

No deployment command in this section is run by repository automation.

### Hugging Face static Space

1. Matin creates a new public Space in the Hugging Face UI with the Static SDK.
2. Clone that new Space repository locally.
3. Keep a root `README.md` whose YAML front matter includes:

   ```yaml
   ---
   title: HyperView iNat24 Static
   sdk: static
   app_file: index.html
   ---
   ```

4. Copy the bundle to the Space repository while preserving its `.git` folder
   and README, then review, commit, and push:

   ```bash
   rsync -a --delete --exclude '.git/' --exclude README.md "$OUT/" /path/to/hf-space/
   git -C /path/to/hf-space status --short
   git -C /path/to/hf-space add .
   git -C /path/to/hf-space commit -m "deploy iNat24 static export"
   git -C /path/to/hf-space push
   ```

5. Open the Space and spot-check the same manifest, sample shard, layout, media,
   and thumbnail paths used in local verification.

### Cloudflare Workers static assets

The export already includes a static-assets-only `wrangler.jsonc`. Matin should
change its generated worker name (`hyperview-default`) to the intended stable
name, authenticate Wrangler, and deploy from the bundle directory:

```bash
cd "$OUT"
npx wrangler deploy --config wrangler.jsonc
```

After deployment, repeat the HTTP checks against the assigned `workers.dev` or
custom-domain URL. No Worker script or server component is required.

## Registry

`live-spaces.registry.json` remains unchanged. Its current checker contract requires
every registry entry to map to a Docker space folder and deployment workflow;
adding an `hf-static` or `cf-static` entry before that schema is extended would
break `scripts/check_spaces.py` semantics.
