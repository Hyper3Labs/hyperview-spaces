#!/usr/bin/env python3
"""Build spaces.hyper3labs.com: the HyperView Spaces gallery plus every bundle.

Reads both registries, collects each committed Static Space bundle from
static-spaces/<slug> into spaces-site/public/<slug> with
`hyperview publish --to dir:`, copies the gallery previews, and writes the
gallery page that the worker in spaces-site/ serves at the origin root.

A Space is listed only when visitors can open it: a bundle served here, a
Static Space hosted on Hugging Face, or a Live Space with no bundle.

Usage:
  python scripts/build_spaces_site.py
  npx --prefix spaces-site wrangler dev --config spaces-site/wrangler.jsonc    # preview
  npx --prefix spaces-site wrangler deploy --config spaces-site/wrangler.jsonc
"""

from __future__ import annotations

import html
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "static-spaces.registry.json"
LIVE_REGISTRY_PATH = ROOT / "live-spaces.registry.json"
SITE_DIR = ROOT / "spaces-site"
PUBLIC_DIR = SITE_DIR / "public"
PREVIEWS_DIR = SITE_DIR / "previews"
SOURCE_TREE = "https://github.com/Hyper3Labs/hyperview-spaces/tree/main"
DOCS_URL = "https://hyper3labs.github.io/"

# Gallery order. Entries not listed here follow in registry order.
ORDER = [
    "hello-world",
    "abo-catalog",
    "fashion-products",
    "precision-regions",
    "logo-search",
    "geospatial",
    "visual-safety",
    "jaguar-multigeometry",
]

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
<title>HyperView Spaces</title>
<meta name="description" content="HyperView workspaces you can open in the browser: one image collection in three geometries, product search, region retrieval, remote sensing, trust and safety.">
<link rel="icon" href="/hello-world/icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap">
<style>
  :root {{
    color-scheme: dark;
    --bg: #0a0a0a;
    --fg: #ededed;
    --muted: #9ca3af;
    --dim: #6b7280;
    --line: rgb(255 255 255 / 0.08);
    --card: rgb(255 255 255 / 0.02);
    --accent: #67e8f9;
    --mono: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: var(--bg); color: var(--fg); font: 15px/1.6 Inter, system-ui, sans-serif; }}
  a {{ color: inherit; }}
  header, main, footer {{ max-width: 1400px; margin: 0 auto; padding-left: 16px; padding-right: 16px; }}
  @media (min-width: 640px) {{ header, main, footer {{ padding-left: 24px; padding-right: 24px; }} }}
  header {{ display: flex; align-items: center; gap: 20px; height: 56px; border-bottom: 1px solid var(--line); max-width: none; }}
  header .brand {{ font-weight: 600; text-decoration: none; }}
  header nav {{ display: flex; gap: 16px; margin-left: auto; font-size: 14px; color: var(--muted); }}
  header nav a {{ text-decoration: none; }}
  header nav a:hover {{ color: var(--fg); }}
  .intro {{ max-width: 760px; padding: 48px 0 32px; }}
  h1 {{ margin: 0; font-size: clamp(32px, 6vw, 48px); font-weight: 600; letter-spacing: -0.03em; line-height: 1.1; }}
  .intro p {{ margin: 16px 0 0; color: var(--muted); font-size: 17px; line-height: 1.65; }}
  .intro p a {{ color: var(--fg); text-decoration-color: #4b5563; }}
  .filters {{ display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 24px; }}
  .filters button {{ font: inherit; font-size: 12px; padding: 4px 12px; border-radius: 999px; border: 1px solid var(--line); background: none; color: var(--muted); cursor: pointer; }}
  .filters button:hover {{ color: var(--fg); }}
  .filters button[aria-pressed="true"] {{ border-color: rgb(103 232 249 / .4); background: rgb(103 232 249 / .1); color: #cffafe; }}
  .grid {{ display: grid; gap: 20px; grid-template-columns: 1fr; }}
  @media (min-width: 640px) {{ .grid {{ grid-template-columns: repeat(2, 1fr); }} }}
  @media (min-width: 1024px) {{ .grid {{ grid-template-columns: repeat(3, 1fr); }} }}
  .card {{ display: flex; flex-direction: column; overflow: hidden; border: 1px solid var(--line); border-radius: 12px; background: var(--card); transition: border-color .15s; }}
  .card:hover {{ border-color: rgb(103 232 249 / .3); }}
  .card[hidden] {{ display: none; }}
  .thumb {{ display: block; aspect-ratio: 16 / 9; overflow: hidden; background: #0d1117; border-bottom: 1px solid var(--line); }}
  .thumb img {{ width: 100%; height: 100%; object-fit: cover; object-position: top; display: block; }}
  .body {{ display: flex; flex: 1; flex-direction: column; padding: 16px; }}
  .tags {{ display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; }}
  .tag {{ font: 10px/1.4 var(--mono); padding: 2px 8px; border-radius: 999px; border: 1px solid rgb(255 255 255 / .09); color: var(--muted); }}
  .tag.hf {{ border-color: rgb(252 211 77 / .2); color: rgb(253 230 138 / .8); }}
  h2 {{ margin: 0; font-size: 16px; font-weight: 600; }}
  h2 a {{ text-decoration: none; }}
  h2 a:hover {{ color: #cffafe; }}
  .desc {{ flex: 1; margin: 6px 0 0; color: var(--muted); font-size: 14px; line-height: 1.6; }}
  .modality {{ margin: 12px 0 0; font: 10px/1.4 var(--mono); color: var(--dim); }}
  .links {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 16px; font-size: 12px; }}
  .links a {{ display: inline-flex; align-items: center; gap: 6px; padding: 6px 10px; border-radius: 6px; border: 1px solid rgb(255 255 255 / .1); color: #d1d5db; text-decoration: none; }}
  .links a:hover {{ color: #fff; }}
  .links a.primary {{ background: #fff; color: #0a0a0a; border-color: #fff; font-weight: 500; }}
  .links a.primary:hover {{ background: #cffafe; }}
  .dot {{ width: 6px; height: 6px; border-radius: 50%; background: var(--dim); }}
  .dot[data-stage="RUNNING"] {{ background: #86efac; }}
  .dot[data-stage="SLEEPING"] {{ background: #fcd34d; }}
  .build {{ margin: 56px 0 0; padding: 24px; border: 1px solid var(--line); border-radius: 12px; background: var(--card); }}
  .build h2 {{ font-size: 18px; }}
  .build p {{ max-width: 760px; margin: 8px 0 0; color: var(--muted); font-size: 14px; }}
  .build a {{ color: var(--fg); text-decoration-color: #4b5563; }}
  code {{ font-family: var(--mono); font-size: .92em; color: #d1d5db; }}
  footer {{ display: flex; flex-wrap: wrap; gap: 16px; justify-content: space-between; margin-top: 80px; padding-top: 24px; padding-bottom: 32px; border-top: 1px solid var(--line); color: var(--dim); font-size: 13px; max-width: none; }}
  footer a {{ text-decoration: none; }}
  footer a:hover {{ color: var(--fg); }}
</style>
</head>
<body>
<header>
  <a class="brand" href="/">HyperView Spaces</a>
  <nav>
    <a href="{docs}">Docs</a>
    <a href="https://github.com/Hyper3Labs/HyperView">GitHub</a>
    <a href="https://hyper3labs.com">hyper&#179;labs</a>
  </nav>
</header>
<main>
  <div class="intro">
    <h1>HyperView Spaces</h1>
    <p>Each Space is a complete <a href="https://github.com/Hyper3Labs/HyperView">HyperView</a> workspace that opens in your browser, with no install and no backend. Most compare a hyperbolic model, Hyper3-CLIP, with OpenAI CLIP on the same task, including the cases CLIP wins. Every Space links to the code that built it, so you can point it at your own data.</p>
  </div>
  <div class="filters" role="group" aria-label="Filter Spaces">
{filters}
  </div>
  <div class="grid">
{cards}
  </div>
  <section class="build">
    <h2>Build your own</h2>
    <p>Copy a folder from <a href="https://github.com/Hyper3Labs/hyperview-spaces">hyperview-spaces</a>, change the dataset and models at the top of its <code>demo.py</code>, then export and publish it with <code>hyperview publish</code>. The <a href="{docs}">HyperView docs</a> cover each step.</p>
  </section>
</main>
<footer>
  <span>HyperView is open source under the MIT licence, built by <a href="https://hyper3labs.com">hyper&#179;labs</a>.</span>
  <span><a href="https://demos.hyper3labs.com">More demos</a></span>
</footer>
<script>
for (const button of document.querySelectorAll('.filters button')) {{
  button.addEventListener('click', () => {{
    const pick = button.dataset.workflow;
    for (const b of document.querySelectorAll('.filters button')) b.setAttribute('aria-pressed', String(b === button));
    for (const card of document.querySelectorAll('.card')) card.hidden = pick !== 'All' && card.dataset.workflow !== pick;
  }});
}}
fetch('/status.json').then(r => r.ok ? r.json() : Promise.reject()).then(data => {{
  for (const item of data.spaces || []) {{
    for (const dot of document.querySelectorAll(`.dot[data-space-id="${{CSS.escape(item.space_id)}}"]`)) {{
      dot.dataset.stage = item.stage || 'UNKNOWN';
      dot.title = String(item.stage || 'unknown').toLowerCase();
    }}
  }}
}}).catch(() => {{}});
</script>
</body>
</html>
"""


def read_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return payload


def strip_prefix(name: str) -> str:
    for prefix in ("HyperView - ", "HyperView – ", "HyperView "):
        if name.startswith(prefix):
            return name[len(prefix):]
    return name


def collect(slug: str, source: Path, hyperview_command: str) -> bool:
    destination = PUBLIC_DIR / slug
    # publish --to dir: refuses to write over an existing tree.
    shutil.rmtree(destination, ignore_errors=True)
    print(f"==> {slug}: collecting {source} -> {destination}")
    result = subprocess.run(
        [hyperview_command, "publish", str(source), "--to", f"dir:{destination}"],
        cwd=ROOT,
    )
    return result.returncode == 0


def card(space: dict[str, Any]) -> str:
    e = {key: html.escape(str(value)) for key, value in space.items() if isinstance(value, str)}
    external = space["url"].startswith("http")
    target = ' target="_blank" rel="noopener"' if external else ""
    thumb = (
        f'<img src="{e["preview"]}" alt="" loading="lazy">' if space.get("preview") else ""
    )
    tags = f'<span class="tag">{e["workflow"]}</span>'
    if space["host"] == "huggingface":
        tags += '<span class="tag hf">Hugging Face</span>'
    links = f'<a class="primary" href="{e["url"]}"{target}>Open &#8599;</a>'
    if space.get("live_space_id"):
        space_id = html.escape(space["live_space_id"])
        links += (
            f'<a href="https://huggingface.co/spaces/{space_id}" target="_blank" rel="noopener">'
            f'<span class="dot" data-space-id="{space_id}"></span>Live Space</a>'
        )
    links += f'<a href="{e["source"]}" target="_blank" rel="noopener">Source</a>'
    modality = f'<p class="modality">{e["modality"]}</p>' if space.get("modality") else ""
    return (
        f'    <article class="card" data-workflow="{e["workflow"]}">'
        f'<a class="thumb" href="{e["url"]}"{target} aria-label="Open {e["name"]}">{thumb}</a>'
        f'<div class="body"><div class="tags">{tags}</div>'
        f'<h2><a href="{e["url"]}"{target}>{e["name"]}</a></h2>'
        f'<p class="desc">{e["description"]}</p>{modality}'
        f'<div class="links">{links}</div></div></article>'
    )


def main() -> int:
    static_entries = read_object(REGISTRY_PATH).get("static_spaces")
    live_entries = read_object(LIVE_REGISTRY_PATH).get("spaces")
    if not isinstance(static_entries, list) or not isinstance(live_entries, list):
        print("ERROR: registries must contain static_spaces and spaces lists")
        return 1
    hyperview_command = shutil.which("hyperview")
    if hyperview_command is None:
        print("ERROR: hyperview is not on PATH; install the pinned release before building")
        return 1

    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    live_by_folder = {e["folder"]: e for e in live_entries if isinstance(e, dict) and e.get("folder")}
    spaces: list[dict[str, Any]] = []
    seen_folders: set[str] = set()

    for static in static_entries:
        slug = static["slug"]
        folder = static["source_folder"]
        seen_folders.add(folder)
        live = live_by_folder.get(folder) or {}
        targets = static.get("deploy_targets", ["cf-static"])
        if "cf-static" in targets:
            source = ROOT / static["bundle_folder"]
            if not (source / "hyperview-static.json").is_file():
                print(f"ERROR: {slug} has no bundle at {source}")
                return 1
            if not collect(slug, source, hyperview_command):
                print(f"ERROR: collect failed for {slug}")
                return 1
            url, host = f"/{slug}/", "site"
        elif "hf-static" in targets and static.get("live_space_id"):
            url, host = f"https://huggingface.co/spaces/{static['live_space_id']}", "huggingface"
        else:
            continue
        live_space_id = None
        if (
            live.get("status") == "live"
            and "hf-docker" in live.get("deploy_targets", [])
            and live.get("space_id")
        ):
            live_space_id = live["space_id"]
        gallery = live.get("gallery") or {}
        spaces.append(
            {
                "slug": slug,
                "name": static.get("name") or strip_prefix(live.get("demo_name", slug)),
                "description": live.get("description", ""),
                "workflow": gallery.get("workflow", "Other"),
                "modality": gallery.get("modality", ""),
                "url": url,
                "host": host,
                "live_space_id": live_space_id,
                "source": live.get("source_repository") or f"{SOURCE_TREE}/{folder}",
            }
        )

    # Live-only Spaces (no bundle) appear while the registry says they are live.
    for live in live_entries:
        if not isinstance(live, dict) or live.get("folder") in seen_folders:
            continue
        if live.get("status") != "live" or not live.get("space_id"):
            continue
        gallery = live.get("gallery") or {}
        spaces.append(
            {
                "slug": live["demo_slug"],
                "name": strip_prefix(live.get("demo_name", live["demo_slug"])),
                "description": live.get("description", ""),
                "workflow": gallery.get("workflow", "Other"),
                "modality": gallery.get("modality", ""),
                "url": f"https://huggingface.co/spaces/{live['space_id']}",
                "host": "huggingface",
                "live_space_id": None,
                "source": f"{SOURCE_TREE}/{live['folder']}",
            }
        )

    rank = {slug: i for i, slug in enumerate(ORDER)}
    spaces.sort(key=lambda s: rank.get(s["slug"], len(ORDER)))

    previews_out = PUBLIC_DIR / "previews"
    shutil.rmtree(previews_out, ignore_errors=True)
    previews_out.mkdir()
    for space in spaces:
        preview = PREVIEWS_DIR / f"{space['slug']}.png"
        if preview.is_file():
            shutil.copy2(preview, previews_out / preview.name)
            space["preview"] = f"/previews/{preview.name}"

    workflows = ["All"] + list(dict.fromkeys(s["workflow"] for s in spaces))
    filters = "\n".join(
        f'    <button type="button" data-workflow="{html.escape(w)}" '
        f'aria-pressed="{"true" if w == "All" else "false"}">{html.escape(w)}</button>'
        for w in workflows
    )
    cards = "\n".join(card(space) for space in spaces)
    (PUBLIC_DIR / "index.html").write_text(
        PAGE.format(docs=DOCS_URL, filters=filters, cards=cards), encoding="utf-8"
    )
    (PUBLIC_DIR / ".assetsignore").write_text(ASSETSIGNORE, encoding="utf-8")

    files = sum(1 for p in PUBLIC_DIR.rglob("*") if p.is_file())
    print(f"Listed {len(spaces)} Space(s); {files} files in {PUBLIC_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
