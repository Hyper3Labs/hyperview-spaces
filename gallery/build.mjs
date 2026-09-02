#!/usr/bin/env node
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const registryPath = resolve(__dirname, "../live-spaces.registry.json");
const staticRegistryPath = resolve(__dirname, "../static-spaces.registry.json");
const outPath = resolve(__dirname, "out/index.html");

const registry = JSON.parse(await readFile(registryPath, "utf8"));
if (!registry || !Array.isArray(registry.spaces)) {
  throw new Error("live-spaces.registry.json must contain a spaces array");
}

const staticRegistry = JSON.parse(await readFile(staticRegistryPath, "utf8"));
if (!staticRegistry || !Array.isArray(staticRegistry.static_spaces)) {
  throw new Error("static-spaces.registry.json must contain a static_spaces array");
}

const warmWorkerUrl = normalizeBaseUrl(process.env.WARM_WORKER_URL ?? "");
// The two registries do not share a slug: a Static Space is named for its
// bundle ("precision-regions") and a Live Space for its demo
// ("precision-region-search"). The demo folder is what they agree on.
const liveByFolder = new Map(
  registry.spaces.map((space) => [space.folder, space]),
);
const cards = registry.spaces.map(renderCard).join("\n");
const staticCards = staticRegistry.static_spaces.map(renderStaticCard).join("\n");

const html = `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>hyper3labs demos</title>
  <style>
    :root {
      color-scheme: light dark;
      --bg: #f7f7f4;
      --panel: #ffffff;
      --text: #191a1d;
      --muted: #666b75;
      --border: #dfddd7;
      --accent: #2563eb;
      --accent-2: #099268;
      --shadow: 0 1px 2px rgba(15, 23, 42, 0.05), 0 12px 34px rgba(15, 23, 42, 0.07);
    }

    @media (prefers-color-scheme: dark) {
      :root {
        --bg: #111214;
        --panel: #191b1f;
        --text: #f4f1ec;
        --muted: #a7adb8;
        --border: #30333a;
        --accent: #74a7ff;
        --accent-2: #4dd4ac;
        --shadow: 0 1px 2px rgba(0, 0, 0, 0.24), 0 18px 44px rgba(0, 0, 0, 0.26);
      }
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      background:
        linear-gradient(180deg, color-mix(in srgb, var(--accent) 7%, transparent), transparent 280px),
        var(--bg);
      color: var(--text);
      font: 15px/1.5 Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    a {
      color: inherit;
      text-decoration: none;
    }

    a:hover {
      color: var(--accent);
    }

    .page {
      width: min(1180px, calc(100% - 40px));
      margin: 0 auto;
      padding: 34px 0 28px;
    }

    header {
      display: flex;
      align-items: end;
      justify-content: space-between;
      gap: 24px;
      padding: 18px 0 34px;
    }

    .section-header {
      border-top: 1px solid var(--border);
      margin-top: 56px;
      padding-top: 40px;
    }

    .wordmark {
      font-size: 17px;
      font-weight: 760;
      letter-spacing: 0;
    }

    h1 {
      max-width: 760px;
      margin: 18px 0 0;
      font-size: clamp(32px, 6vw, 72px);
      line-height: 0.96;
      letter-spacing: 0;
    }

    .lede {
      max-width: 500px;
      margin: 0;
      color: var(--muted);
      font-size: 16px;
    }

    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(min(100%, 320px), 1fr));
      gap: 18px;
      align-items: stretch;
    }

    .card {
      min-height: 250px;
      display: flex;
      flex-direction: column;
      padding: 20px;
      border: 1px solid var(--border);
      border-radius: 8px;
      background: color-mix(in srgb, var(--panel) 94%, transparent);
      box-shadow: var(--shadow);
    }

    .card::before {
      content: "";
      display: block;
      width: 100%;
      height: 5px;
      margin-bottom: 20px;
      border-radius: 999px;
      background: linear-gradient(90deg, var(--accent), var(--accent-2));
    }

    .card-top {
      display: flex;
      align-items: start;
      justify-content: space-between;
      gap: 14px;
    }

    .slug {
      overflow-wrap: anywhere;
      color: var(--muted);
      font: 12px/1.35 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    }

    .badge {
      width: auto;
      height: 20px;
      flex: none;
      margin-top: 1px;
    }

    .registry-status {
      display: inline-flex;
      align-items: center;
      min-height: 20px;
      padding: 2px 8px;
      border: 1px solid var(--border);
      border-radius: 999px;
      color: var(--muted);
      font-size: 11px;
      font-weight: 700;
      line-height: 1;
      text-transform: uppercase;
    }

    h2 {
      margin: 14px 0 10px;
      font-size: 21px;
      line-height: 1.18;
      letter-spacing: 0;
    }

    .description {
      margin: 0 0 24px;
      color: var(--muted);
    }

    .links {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: auto;
      padding-top: 8px;
    }

    .link {
      display: inline-flex;
      align-items: center;
      min-height: 34px;
      padding: 7px 11px;
      border: 1px solid var(--border);
      border-radius: 7px;
      background: color-mix(in srgb, var(--panel) 70%, var(--bg));
      font-size: 13px;
      font-weight: 650;
    }

    .link.primary {
      border-color: color-mix(in srgb, var(--accent) 34%, var(--border));
      color: var(--accent);
    }

    footer {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      margin-top: 34px;
      padding-top: 22px;
      border-top: 1px solid var(--border);
      color: var(--muted);
      font-size: 13px;
    }

    @media (max-width: 720px) {
      .page {
        width: min(100% - 28px, 1180px);
        padding-top: 20px;
      }

      header,
      footer {
        display: block;
      }

      h1 {
        margin-bottom: 18px;
      }

      .lede {
        max-width: none;
      }

      footer p {
        margin: 0 0 8px;
      }
    }
  </style>
</head>
<body>
  <main class="page">
    <header>
      <div>
        <div class="wordmark">hyper3labs</div>
        <h1>Live Spaces</h1>
      </div>
      <p class="lede">Runtime-connected HyperView demos for new queries, model jobs, computed layouts, and editable workspace state.</p>
    </header>

    <section class="grid" aria-label="Live Spaces">
${cards}
    </section>

    <header class="section-header">
      <div>
        <h1>Static Spaces</h1>
      </div>
      <p class="lede">Read-only bundles served as plain files. No runtime, no cold start: prepared cases, pan/zoom/lasso, precomputed similarity and materialized search results, with every image served from the bundle itself.</p>
    </header>

    <section class="grid" aria-label="Static Spaces">
${staticCards}
    </section>

    <footer>
      <p>Generated from live-spaces.registry.json.</p>
    </footer>
  </main>
</body>
</html>
`;

await mkdir(dirname(outPath), { recursive: true });
await writeFile(outPath, html, "utf8");
console.log(`Wrote ${outPath}`);

function renderCard(space) {
  const required = ["demo_slug"];
  for (const key of required) {
    if (typeof space[key] !== "string" || space[key].length === 0) {
      throw new Error(`registry space is missing ${key}`);
    }
  }

  const name = space.demo_name || space.demo_slug;
  const description = space.description || "Explore this HyperView demo workspace.";
  const status = normalizeStatus(space.status);
  const spaceId = typeof space.space_id === "string" && space.space_id.length > 0
    ? space.space_id
    : null;
  const statusMarkup = renderStatus(space.demo_slug, status, spaceId);
  const linksMarkup = renderLinks(status, spaceId);

  return `      <article class="card">
        <div class="card-top">
          <div class="slug">${escapeHtml(space.demo_slug)}</div>
          ${statusMarkup}
        </div>
        <h2>${escapeHtml(name)}</h2>
        <p class="description">${escapeHtml(description)}</p>
        <div class="links">
${linksMarkup}
        </div>
      </article>`;
}

function renderStaticCard(view) {
  if (typeof view.slug !== "string" || view.slug.length === 0) {
    throw new Error("static space is missing slug");
  }
  const live = liveByFolder.get(view.source_folder) ?? {};
  const name = view.name || live.demo_name || view.slug;
  const description =
    live.description || "Explore this HyperView demo as a read-only bundle.";
  const href = `${view.mount_path}/`;

  return `      <article class="card">
        <div class="card-top">
          <div class="slug">${escapeHtml(view.slug)}</div>
          <span class="registry-status">static</span>
        </div>
        <h2>${escapeHtml(name)}</h2>
        <p class="description">${escapeHtml(description)}</p>
        <div class="links">
          <a class="primary" href="${escapeAttribute(href)}">Open Static Space</a>
        </div>
      </article>`;
}

function normalizeStatus(value) {
  return ["live", "draft", "local"].includes(value) ? value : "unknown";
}

function renderStatus(demoSlug, status, spaceId) {
  // The badge is served by the warm worker. With no worker configured the
  // <img> resolves to /badge/... on this host and every card shows a broken
  // image, so fall back to the registry status text.
  if (status === "live" && spaceId && warmWorkerUrl) {
    const badgeSrc = `${warmWorkerUrl}/badge/${encodeURIComponent(demoSlug)}.svg`;
    return `<img class="badge" src="${escapeAttribute(badgeSrc)}" alt="Live status for ${escapeAttribute(demoSlug)}" loading="lazy">`;
  }
  return `<span class="registry-status">${escapeHtml(status)}</span>`;
}

function renderLinks(status, spaceId) {
  const links = [];
  if (status === "live" && spaceId) {
    const liveUrl = `https://${spaceId.replaceAll("/", "-").toLowerCase()}.hf.space`;
    links.push(`<a class="link primary" href="${escapeAttribute(liveUrl)}">Open Live Space</a>`);
  }
  if (spaceId) {
    const hfUrl = `https://huggingface.co/spaces/${spaceId}`;
    links.push(`<a class="link" href="${escapeAttribute(hfUrl)}">Hugging Face</a>`);
  }
  if (links.length === 0) {
    links.push(`<span class="link">Local only</span>`);
  }
  return links.map((link) => `          ${link}`).join("\n");
}

function normalizeBaseUrl(value) {
  const trimmed = value.trim();
  if (!trimmed) {
    return "";
  }

  return trimmed.replace(/\/+$/, "");
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function escapeAttribute(value) {
  return escapeHtml(value);
}
