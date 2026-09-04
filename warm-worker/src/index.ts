import registry from "../../live-spaces.registry.json";

interface Env {
  STATUS: KVNamespace;
  HEALTH_TIMEOUT_MS?: string;
  HISTORY_LIMIT?: string;
}

interface RegistrySpace {
  space_id: string | null;
  folder: string;
  demo_slug: string;
  demo_name?: string;
  description?: string;
  keep_warm?: boolean;
  status: "live" | "draft" | "local" | (string & {});
  deploy_targets: string[];
}

type WarmableSpace = RegistrySpace & { space_id: string };

interface Registry {
  version: number;
  spaces: RegistrySpace[];
}

interface StatusRecord {
  space_id: string;
  demo_slug: string;
  stage: string;
  http_status: number | null;
  latency_ms: number | null;
  hyperview_version: string | null;
  checked_at: string;
}

interface StatusSnapshot {
  checked_at: string | null;
  count: number;
  spaces: StatusRecord[];
}

interface TimedResponse {
  response: Response;
  latencyMs: number;
}

const typedRegistry = registry as Registry;
const warmSpaces = typedRegistry.spaces.filter(
  (space): space is WarmableSpace =>
    space.keep_warm === true && typeof space.space_id === "string" && space.space_id.length > 0
);

const DEFAULT_TIMEOUT_MS = 4000;
const DEFAULT_HISTORY_LIMIT = 288;

export default {
  async scheduled(_controller, env, _ctx): Promise<void> {
    await checkAndStoreSpaces(env);
  },

  async fetch(request, env): Promise<Response> {
    return handleRequest(request, env);
  }
} satisfies ExportedHandler<Env>;

async function handleRequest(request: Request, env: Env): Promise<Response> {
  const url = new URL(request.url);

  if (request.method !== "GET") {
    return new Response("Method Not Allowed", { status: 405 });
  }

  if (url.pathname === "/status.json") {
    const snapshot = await readLatestSnapshot(env);
    return jsonResponse(snapshot);
  }

  if (url.pathname.startsWith("/badge/") && url.pathname.endsWith(".svg")) {
    const demoSlug = decodeURIComponent(url.pathname.slice("/badge/".length, -".svg".length));
    const snapshot = await readLatestSnapshot(env);
    const record = snapshot.spaces.find((space) => space.demo_slug === demoSlug);
    return svgResponse(renderBadge(record));
  }

  if (url.pathname === "/status") {
    const snapshot = await readLatestSnapshot(env);
    return htmlResponse(renderStatusPage(snapshot));
  }

  if (url.pathname === "/") {
    // The demo gallery moved to the landing site; this Worker is status-only.
    return Response.redirect("https://hyper3labs.com/spaces/", 302);
  }

  return new Response("Not Found", { status: 404 });
}

async function checkAndStoreSpaces(env: Env): Promise<StatusSnapshot> {
  const checkedAt = new Date().toISOString();
  const records = await Promise.all(
    warmSpaces.map((space) => checkSpace(space, env, checkedAt))
  );
  const snapshot: StatusSnapshot = {
    checked_at: checkedAt,
    count: records.length,
    spaces: records
  };

  await Promise.all([
    env.STATUS.put("latest", JSON.stringify(snapshot)),
    ...records.map((record) => appendHistory(env, record))
  ]);

  return snapshot;
}

async function checkSpace(space: WarmableSpace, env: Env, checkedAt: string): Promise<StatusRecord> {
  const timeoutMs = positiveInteger(env.HEALTH_TIMEOUT_MS, DEFAULT_TIMEOUT_MS);
  const healthUrl = `${spaceRootUrl(space.space_id)}/__hyperview__/health`;
  const rootUrl = spaceRootUrl(space.space_id);

  const health = await fetchTimed(healthUrl, timeoutMs);
  const healthCheck = health.ok ? health.value : undefined;
  let spaceCheck = healthCheck;
  if (!healthCheck?.response.ok) {
    const root = await fetchTimed(rootUrl, timeoutMs);
    spaceCheck = root.ok ? root.value : healthCheck;
  }

  const healthJson = health.ok ? await readJsonObject(health.value.response.clone()) : null;
  const stage = await readRuntimeStage(space.space_id, timeoutMs);

  return {
    space_id: space.space_id,
    demo_slug: space.demo_slug,
    stage,
    http_status: spaceCheck?.response.status ?? null,
    latency_ms: spaceCheck?.latencyMs ?? null,
    hyperview_version:
      readStringProperty(healthJson, "version") ?? readStringProperty(healthJson, "hyperview_version"),
    checked_at: checkedAt
  };
}

async function readRuntimeStage(spaceId: string, timeoutMs: number): Promise<string> {
  const apiUrl = `https://huggingface.co/api/spaces/${spaceId
    .split("/")
    .map(encodeURIComponent)
    .join("/")}`;
  const result = await fetchTimed(apiUrl, timeoutMs);
  if (!result.ok || !result.value.response.ok) {
    return "UNKNOWN";
  }

  const payload = await readJsonObject(result.value.response);
  const runtime = readObjectProperty(payload, "runtime");
  return readStringProperty(runtime, "stage") ?? "UNKNOWN";
}

async function fetchTimed(url: string, timeoutMs: number): Promise<{ ok: true; value: TimedResponse } | { ok: false }> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  const startedAt = Date.now();

  try {
    const response = await fetch(url, {
      signal: controller.signal,
      headers: {
        "user-agent": "hyperview-warm-worker/0.1"
      }
    });
    return {
      ok: true,
      value: {
        response,
        latencyMs: Date.now() - startedAt
      }
    };
  } catch {
    return { ok: false };
  } finally {
    clearTimeout(timeout);
  }
}

async function appendHistory(env: Env, record: StatusRecord): Promise<void> {
  const key = historyKey(record.space_id);
  const existing = await env.STATUS.get<StatusRecord[]>(key, "json");
  const history = Array.isArray(existing) ? existing : [];
  history.push(record);

  const limit = positiveInteger(env.HISTORY_LIMIT, DEFAULT_HISTORY_LIMIT);
  const capped = history.slice(-limit);
  await env.STATUS.put(key, JSON.stringify(capped));
}

async function readLatestSnapshot(env: Env): Promise<StatusSnapshot> {
  const latest = await env.STATUS.get<StatusSnapshot>("latest", "json");
  if (latest && Array.isArray(latest.spaces)) {
    return latest;
  }

  return {
    checked_at: null,
    count: 0,
    spaces: []
  };
}

function spaceRootUrl(spaceId: string): string {
  const host = spaceId.replaceAll("/", "-").toLowerCase();
  return `https://${host}.hf.space`;
}

function historyKey(spaceId: string): string {
  return `history:${spaceId}`;
}

async function readJsonObject(response: Response): Promise<Record<string, unknown> | null> {
  try {
    const value = await response.json();
    return isObject(value) ? value : null;
  } catch {
    return null;
  }
}

function readObjectProperty(value: Record<string, unknown> | null, key: string): Record<string, unknown> | null {
  if (!value) {
    return null;
  }

  const property = value[key];
  return isObject(property) ? property : null;
}

function readStringProperty(value: Record<string, unknown> | null, key: string): string | null {
  if (!value) {
    return null;
  }

  const property = value[key];
  return typeof property === "string" && property.length > 0 ? property : null;
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function positiveInteger(rawValue: string | undefined, fallback: number): number {
  if (!rawValue) {
    return fallback;
  }

  const parsed = Number.parseInt(rawValue, 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

function jsonResponse(value: unknown): Response {
  return new Response(JSON.stringify(value, null, 2), {
    headers: {
      "access-control-allow-origin": "*",
      "content-type": "application/json; charset=utf-8"
    }
  });
}

function svgResponse(svg: string): Response {
  return new Response(svg, {
    headers: {
      "access-control-allow-origin": "*",
      "cache-control": "no-store",
      "content-type": "image/svg+xml; charset=utf-8"
    }
  });
}

function htmlResponse(html: string): Response {
  return new Response(html, {
    headers: {
      "content-type": "text/html; charset=utf-8"
    }
  });
}

function renderBadge(record: StatusRecord | undefined): string {
  const status = badgeStatus(record);
  const label = status.label;
  const color = status.color;
  const textWidth = Math.max(74, label.length * 7 + 14);
  const width = 68 + textWidth;

  return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="20" role="img" aria-label="hyperview: ${escapeAttribute(label)}">
  <linearGradient id="s" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <rect rx="3" width="${width}" height="20" fill="#555"/>
  <rect rx="3" x="68" width="${textWidth}" height="20" fill="${color}"/>
  <rect rx="3" width="${width}" height="20" fill="url(#s)"/>
  <path fill="${color}" d="M68 0h4v20h-4z"/>
  <g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,sans-serif" font-size="11">
    <text x="34" y="15" fill="#010101" fill-opacity=".3">space</text>
    <text x="34" y="14">space</text>
    <text x="${68 + textWidth / 2}" y="15" fill="#010101" fill-opacity=".3">${escapeHtml(label)}</text>
    <text x="${68 + textWidth / 2}" y="14">${escapeHtml(label)}</text>
  </g>
</svg>`;
}

function badgeStatus(record: StatusRecord | undefined): { label: string; color: string } {
  if (!record) {
    return { label: "ERROR", color: "#d73a49" };
  }

  const stage = record.stage.toUpperCase();
  if (stage === "RUNNING" && record.http_status !== null && record.http_status >= 200 && record.http_status < 400) {
    return { label: "RUNNING", color: "#2ea043" };
  }

  if (stage.includes("SLEEP") || stage.includes("BUILD")) {
    return { label: "SLEEPING-BUILDING", color: "#f0883e" };
  }

  return { label: "ERROR", color: "#d73a49" };
}

function renderStatusPage(snapshot: StatusSnapshot): string {
  const rows = snapshot.spaces
    .map((record) => `<tr>
      <td>${escapeHtml(record.demo_slug)}</td>
      <td>${escapeHtml(record.space_id)}</td>
      <td>${escapeHtml(record.stage)}</td>
      <td>${record.http_status ?? ""}</td>
      <td>${record.latency_ms === null ? "" : `${record.latency_ms} ms`}</td>
      <td>${escapeHtml(record.hyperview_version ?? "")}</td>
      <td>${escapeHtml(record.checked_at)}</td>
    </tr>`)
    .join("");

  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>HyperView Space Status</title>
  <style>
    body { margin: 32px; color: #202124; font: 14px/1.45 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    h1 { margin: 0 0 8px; font-size: 24px; }
    p { margin: 0 0 24px; color: #5f6368; }
    table { width: 100%; border-collapse: collapse; }
    th, td { padding: 10px 12px; border-bottom: 1px solid #dadce0; text-align: left; vertical-align: top; }
    th { color: #5f6368; font-size: 12px; text-transform: uppercase; }
    code { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
  </style>
</head>
<body>
  <h1>HyperView Space Status</h1>
  <p>Last check: <code>${escapeHtml(snapshot.checked_at ?? "not checked yet")}</code></p>
  <table>
    <thead>
      <tr>
        <th>Demo</th>
        <th>Space</th>
        <th>Stage</th>
        <th>HTTP</th>
        <th>Latency</th>
        <th>Version</th>
        <th>Checked</th>
      </tr>
    </thead>
    <tbody>${rows || `<tr><td colspan="7">No status snapshot has been written yet.</td></tr>`}</tbody>
  </table>
</body>
</html>`;
}

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function escapeAttribute(value: string): string {
  return escapeHtml(value);
}
