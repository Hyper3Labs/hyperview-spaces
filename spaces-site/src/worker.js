import registry from '../../live-spaces.registry.json';

// Serves every Static Space bundle from one origin, at spaces.hyper3labs.com/<slug>/.
//
// Bundles are location-independent (relative asset URLs), so they need no build-time
// knowledge of the path they are mounted at. What they do need is a not-found fallback
// scoped to their own subtree: a miss under /abo-catalog/ must fall back to
// /abo-catalog/index.html, never to another space's shell. Cloudflare's built-in
// not_found_handling is per-worker, so the scoping happens here instead.

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const segments = url.pathname.split('/').filter(Boolean);

    if (url.pathname === '/status.json') {
      return statusResponse(request, ctx);
    }

    // /abo-catalog -> /abo-catalog/, so relative asset URLs resolve inside the bundle.
    if (segments.length === 1 && !url.pathname.endsWith('/')) {
      const shell = await env.ASSETS.fetch(new URL(`/${segments[0]}/index.html`, url));
      if (shell.ok) {
        url.pathname += '/';
        return Response.redirect(url.toString(), 308);
      }
    }

    const response = await env.ASSETS.fetch(request);
    if (response.status !== 404 || segments.length === 0) {
      return response;
    }

    // Client-side route inside a bundle: hand back that bundle's shell.
    const shell = await env.ASSETS.fetch(new URL(`/${segments[0]}/index.html`, url));
    if (shell.ok) {
      return new Response(shell.body, {
        status: 200,
        headers: shell.headers,
      });
    }

    return response;
  },
};

async function statusResponse(request, ctx) {
  const cache = caches.default;
  const cached = await cache.match(request);
  if (cached) return cached;

  const checkedAt = new Date().toISOString();
  const spaces = await Promise.all(
    registry.spaces
      .filter((space) => typeof space.space_id === 'string' && space.space_id)
      .map((space) => checkSpace(space, checkedAt)),
  );
  const response = new Response(JSON.stringify({ checked_at: checkedAt, spaces }, null, 2), {
    headers: {
      'access-control-allow-origin': '*',
      'cache-control': 'public, max-age=60',
      'content-type': 'application/json; charset=utf-8',
    },
  });
  ctx.waitUntil(cache.put(request, response.clone()));
  return response;
}

async function checkSpace(space, checkedAt) {
  const info = await fetchJson(`https://huggingface.co/api/spaces/${space.space_id}`);
  const rawStage = info.payload?.runtime?.stage || 'UNKNOWN';
  let stage = rawStage;
  let healthStatus = null;

  if (rawStage === 'RUNNING') {
    const health = await fetchJson(
      `${spaceRootUrl(space.space_id)}/__hyperview__/health`,
    );
    healthStatus = health.status;
    if (health.status !== 200 || health.payload?.name !== 'hyperview') {
      stage = 'UNHEALTHY';
    } else if (
      space.expected_dataset &&
      health.payload?.dataset !== space.expected_dataset
    ) {
      stage = 'METADATA_MISMATCH';
    }
  }

  return {
    space_id: space.space_id,
    demo_slug: space.demo_slug,
    declared_status: space.status,
    stage,
    huggingface_stage: rawStage,
    api_status: info.status,
    health_status: healthStatus,
    checked_at: checkedAt,
  };
}

async function fetchJson(url) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 5000);
  try {
    const response = await fetch(url, {
      headers: { 'user-agent': 'hyperview-spaces-status/1' },
      signal: controller.signal,
    });
    let payload = null;
    try {
      payload = await response.json();
    } catch {
      // Status remains useful when the body is not JSON.
    }
    return { status: response.status, payload };
  } catch {
    return { status: null, payload: null };
  } finally {
    clearTimeout(timeout);
  }
}

function spaceRootUrl(spaceId) {
  return `https://${spaceId.replaceAll('/', '-').toLowerCase()}.hf.space`;
}
