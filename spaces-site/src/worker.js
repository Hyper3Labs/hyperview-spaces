// Serves every Static Space bundle from one origin, at spaces.hyper3labs.com/<slug>/.
//
// Bundles are location-independent (relative asset URLs), so they need no build-time
// knowledge of the path they are mounted at. What they do need is a not-found fallback
// scoped to their own subtree: a miss under /abo-catalog/ must fall back to
// /abo-catalog/index.html, never to another space's shell. Cloudflare's built-in
// not_found_handling is per-worker, so the scoping happens here instead.

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const segments = url.pathname.split('/').filter(Boolean);

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
