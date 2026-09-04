#!/usr/bin/env python3
"""Assemble every registered Static Space bundle into one deployable origin.

Reads static-spaces.registry.json and runs `hyperview publish <bundle> --to dir:`
into spaces-site/public/<slug> for each entry, then writes the index page and the
asset-ignore list that the worker in spaces-site/ serves.

The bundles themselves are produced by export_static_spaces.py; this script only
collects them. Run the exporter first when a demo's workspace or panels changed.

Usage:
  uv run --project ../ python scripts/build_spaces_site.py [slug ...]

With no arguments every registered Static Space is collected; passing slugs
limits the run to those entries. Deploy the result with:

  npx wrangler deploy --config spaces-site/wrangler.jsonc
"""

from __future__ import annotations

import html
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "static-spaces.registry.json"
LIVE_REGISTRY_PATH = ROOT / "live-spaces.registry.json"
PUBLIC_DIR = ROOT / "spaces-site" / "public"

# Only files the worker or Cloudflare needs at the origin root; everything else
# under public/ is bundle content and must be uploaded verbatim.
ASSETSIGNORE = """.assetsignore
*/wrangler.jsonc
*/.assetsignore
"""

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>HyperView Static Spaces</title>
<style>
  :root {{
    color-scheme: dark;
    --bg: #090d16;
    --fg: #f8fafc;
    --muted: #64748b;
    --accent: #93c5fd;
    --line: rgb(248 250 252 / 0.10);
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    padding: 4rem 1.5rem;
    background: var(--bg);
    color: var(--fg);
    font: 15px/1.6 ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
  }}
  main {{ max-width: 58rem; margin: 0 auto; }}
  h1 {{ font-size: 2rem; font-weight: 650; margin: 0 0 .5rem; letter-spacing: -0.03em; }}
  p.lede {{ color: var(--muted); margin: 0 0 2.5rem; }}
  ul {{ list-style: none; margin: 0; padding: 0; }}
  li {{ border-top: 1px solid var(--line); }}
  li:last-child {{ border-bottom: 1px solid var(--line); }}
  .space {{ display: grid; gap: .65rem; padding: 1.2rem .25rem; }}
  .space-head {{ display: flex; align-items: center; gap: .7rem; }}
  .name {{ font-weight: 600; }}
  .status {{ margin-left: auto; padding: .18rem .5rem; border: 1px solid var(--line); border-radius: 999px; color: var(--muted); font: .68rem ui-monospace, SFMono-Regular, Menlo, monospace; text-transform: uppercase; }}
  .status[data-stage="RUNNING"] {{ color: #86efac; border-color: rgb(134 239 172 / .25); }}
  .status[data-stage="PAUSED"], .status[data-stage="UNHEALTHY"], .status[data-stage="METADATA_MISMATCH"] {{ color: #fda4af; border-color: rgb(253 164 175 / .25); }}
  .description {{ margin: 0; color: var(--muted); font-size: .9rem; }}
  .links {{ display: flex; flex-wrap: wrap; gap: .5rem; }}
  .links a {{ padding: .35rem .65rem; border: 1px solid var(--line); border-radius: .45rem; color: var(--fg); text-decoration: none; font-size: .78rem; }}
  .links a:hover {{ color: var(--accent); border-color: rgb(147 197 253 / .35); }}
  footer {{ margin-top: 3rem; color: var(--muted); font-size: .8125rem; }}
  footer a {{ color: var(--muted); }}
</style>
</head>
<body>
<main>
  <h1>HyperView Static Spaces</h1>
  <p class="lede">The registry-backed catalog for every HyperView demo. Static exports run entirely in the browser; Live Spaces expose the runtime.</p>
  <ul>
{items}
  </ul>
  <footer><a href="https://hyper3labs.com">hyper&#179;labs</a></footer>
</main>
<script>
fetch('/status.json').then(r => r.ok ? r.json() : Promise.reject()).then(data => {{
  for (const item of data.spaces || []) {{
    const node = document.querySelector(`[data-space-id="${{CSS.escape(item.space_id)}}"]`);
    if (!node) continue;
    node.textContent = String(item.stage || 'UNKNOWN').toLowerCase().replaceAll('_', ' ');
    node.dataset.stage = item.stage || 'UNKNOWN';
  }}
}}).catch(() => {{}});
</script>
</body>
</html>
"""


def main() -> int:
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    entries = registry.get("static_spaces")
    if not isinstance(entries, list):
        print("ERROR: static-spaces.registry.json must contain a static_spaces list")
        return 1
    live_registry = json.loads(LIVE_REGISTRY_PATH.read_text(encoding="utf-8"))
    live_entries = live_registry.get("spaces")
    if not isinstance(live_entries, list):
        print("ERROR: live-spaces.registry.json must contain a spaces list")
        return 1
    external_bundles = os.environ.get("HYPERVIEW_STATIC_SPACES_ROOT")
    bundles_root = Path(external_bundles).resolve() if external_bundles else None
    hyperview_command = shutil.which("hyperview")
    if hyperview_command is None:
        print("ERROR: hyperview is not on PATH; install the pinned release before building")
        return 1

    wanted = set(sys.argv[1:])
    unknown = wanted - {entry.get("slug") for entry in entries}
    if unknown:
        print(f"ERROR: unknown slugs: {', '.join(sorted(unknown))}")
        return 1

    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)

    for entry in entries:
        slug = entry["slug"]
        if wanted and slug not in wanted:
            continue
        source = (
            bundles_root / slug
            if bundles_root is not None
            else ROOT / entry["bundle_folder"]
        )
        if not (source / "hyperview-static.json").is_file():
            print(f"ERROR: {slug} has no bundle at {source}; run export_static_spaces.py first")
            return 1
        destination = PUBLIC_DIR / slug
        # publish --to dir: refuses to write over an existing tree.
        shutil.rmtree(destination, ignore_errors=True)
        print(f"==> {slug}: collecting {source} -> {destination}")
        result = subprocess.run(
            [
                hyperview_command,
                "publish",
                str(source),
                "--to",
                f"dir:{destination}",
            ],
            cwd=ROOT,
        )
        if result.returncode != 0:
            print(f"ERROR: collect failed for {slug}")
            return result.returncode

    collected = sorted(p.name for p in PUBLIC_DIR.iterdir() if (p / "hyperview-static.json").is_file())
    static_by_source = {entry["source_folder"]: entry for entry in entries}
    item_rows: list[str] = []
    for entry in live_entries:
        static = static_by_source.get(entry.get("folder"))
        static_slug = static.get("slug") if static else None
        space_id = entry.get("space_id")
        links: list[str] = []
        if static_slug in collected:
            links.append(f'<a href="/{html.escape(static_slug)}/">Open Static Space</a>')
        if space_id:
            live_url = f"https://{space_id.replace('/', '-').lower()}.hf.space"
            links.append(
                f'<a href="{html.escape(live_url)}" target="_blank" rel="noopener">Open Live Space</a>'
            )
        stage = "checking" if space_id else entry.get("status", "not deployed")
        status_attribute = (
            f' data-space-id="{html.escape(space_id)}"' if space_id else ""
        )
        item_rows.append(
            '    <li class="space">'
            '<div class="space-head">'
            f'<span class="name">{html.escape(entry.get("demo_name", entry.get("demo_slug", "Space")))}</span>'
            f'<span class="status"{status_attribute}>{html.escape(stage)}</span>'
            '</div>'
            f'<p class="description">{html.escape(entry.get("description", ""))}</p>'
            f'<div class="links">{"".join(links) or "Not deployed yet"}</div>'
            '</li>'
        )
    items = "\n".join(item_rows)
    (PUBLIC_DIR / "index.html").write_text(PAGE.format(items=items), encoding="utf-8")
    (PUBLIC_DIR / ".assetsignore").write_text(ASSETSIGNORE, encoding="utf-8")

    files = sum(1 for p in PUBLIC_DIR.rglob("*") if p.is_file())
    print(f"Collected {len(collected)} Static Space(s), {files} files, into {PUBLIC_DIR}")
    print("Deploy with: npx wrangler deploy --config spaces-site/wrangler.jsonc")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
