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
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "static-spaces.registry.json"
HYPERVIEW_ROOT = ROOT.parent
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
  main {{ max-width: 46rem; margin: 0 auto; }}
  h1 {{ font-size: 1.5rem; font-weight: 600; margin: 0 0 .5rem; letter-spacing: -0.01em; }}
  p.lede {{ color: var(--muted); margin: 0 0 2.5rem; }}
  ul {{ list-style: none; margin: 0; padding: 0; }}
  li {{ border-top: 1px solid var(--line); }}
  li:last-child {{ border-bottom: 1px solid var(--line); }}
  a.space {{
    display: flex; align-items: baseline; gap: 1rem;
    padding: 1rem .25rem; color: inherit; text-decoration: none;
  }}
  a.space:hover {{ background: rgb(248 250 252 / 0.03); }}
  a.space:hover .name {{ color: var(--accent); }}
  .name {{ font-weight: 500; }}
  .slug {{ color: var(--muted); font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .8125rem; margin-left: auto; }}
  footer {{ margin-top: 3rem; color: var(--muted); font-size: .8125rem; }}
  footer a {{ color: var(--muted); }}
</style>
</head>
<body>
<main>
  <h1>HyperView Static Spaces</h1>
  <p class="lede">Read-only, self-contained exports of HyperView workspaces. Each one runs entirely in the browser.</p>
  <ul>
{items}
  </ul>
  <footer><a href="https://hyper3labs.com">hyper&#179;labs</a></footer>
</main>
</body>
</html>
"""


def main() -> int:
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    entries = registry.get("static_spaces")
    if not isinstance(entries, list):
        print("ERROR: static-spaces.registry.json must contain a static_spaces list")
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
        source = ROOT / entry["bundle_folder"]
        if not (source / "hyperview-static.json").is_file():
            print(f"ERROR: {slug} has no bundle at {source}; run export_static_spaces.py first")
            return 1
        destination = PUBLIC_DIR / slug
        # publish --to dir: refuses to write over an existing tree.
        shutil.rmtree(destination, ignore_errors=True)
        print(f"==> {slug}: collecting {source} -> {destination}")
        result = subprocess.run(
            [
                "uv",
                "run",
                "hyperview",
                "publish",
                str(source),
                "--to",
                f"dir:{destination}",
            ],
            cwd=HYPERVIEW_ROOT,
        )
        if result.returncode != 0:
            print(f"ERROR: collect failed for {slug}")
            return result.returncode

    collected = sorted(p.name for p in PUBLIC_DIR.iterdir() if (p / "hyperview-static.json").is_file())
    names = {entry["slug"]: entry.get("name", entry["slug"]) for entry in entries}
    items = "\n".join(
        '    <li><a class="space" href="/{slug}/">'
        '<span class="name">{name}</span>'
        '<span class="slug">/{slug}</span></a></li>'.format(
            slug=html.escape(slug), name=html.escape(names.get(slug, slug))
        )
        for slug in collected
    )
    (PUBLIC_DIR / "index.html").write_text(PAGE.format(items=items), encoding="utf-8")
    (PUBLIC_DIR / ".assetsignore").write_text(ASSETSIGNORE, encoding="utf-8")

    files = sum(1 for p in PUBLIC_DIR.rglob("*") if p.is_file())
    print(f"Collected {len(collected)} Static Space(s), {files} files, into {PUBLIC_DIR}")
    print("Deploy with: npx wrangler deploy --config spaces-site/wrangler.jsonc")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
