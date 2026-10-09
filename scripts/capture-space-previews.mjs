#!/usr/bin/env node
/**
 * Regenerate the gallery preview cards in spaces-site/previews/.
 *
 * Build and serve the site first, then point this at it:
 *
 *   python scripts/build_spaces_site.py
 *   npx --prefix spaces-site wrangler dev --config spaces-site/wrangler.jsonc
 *   node scripts/capture-space-previews.mjs --base http://localhost:8787
 *
 * Each Space is opened at 1280x720, given time for the HyperView shell to
 * mount its sample grid and walkthrough panel, and captured to
 * spaces-site/previews/<slug>.png. A Space that renders an error state or a
 * "Panel unavailable" message is reported and its existing PNG is left alone.
 *
 * Playwright is not a dependency of this repo. It resolves out of the parent
 * HyperView checkout, or set NODE_PATH to it:
 *
 *   NODE_PATH=../node_modules node scripts/capture-space-previews.mjs
 */

import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import fs from 'node:fs';

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, '..');
const outDir = path.join(repoRoot, 'spaces-site', 'previews');

const argv = process.argv.slice(2);
const readArg = (name, fallback) => {
  const i = argv.indexOf(`--${name}`);
  return i !== -1 && argv[i + 1] ? argv[i + 1] : fallback;
};

const baseUrl = (readArg('base', process.env.PREVIEW_BASE_URL || 'http://localhost:8787')).replace(/\/$/, '');
const onlySlugs = readArg('slugs', '').split(',').map((s) => s.trim()).filter(Boolean);

const VIEWPORT = { width: 1280, height: 720 };
const SETTLE_MS = Number(readArg('settle', '2500'));

// Playwright lives in the parent HyperView checkout.
const require = createRequire(import.meta.url);
const candidates = [
  'playwright',
  path.join(repoRoot, '..', 'node_modules', 'playwright'),
];
let chromium = null;
for (const candidate of candidates) {
  try {
    ({ chromium } = require(candidate));
    break;
  } catch {
    /* try the next resolution root */
  }
}
if (!chromium) {
  console.error('Could not resolve playwright. Install it, or run with NODE_PATH pointed at ../node_modules.');
  process.exit(1);
}

// Every Static Space served from spaces.hyper3labs.com, straight from the registry.
function readSlugs() {
  const registry = JSON.parse(fs.readFileSync(path.join(repoRoot, 'static-spaces.registry.json'), 'utf8'));
  const slugs = registry.static_spaces
    .filter((entry) => (entry.deploy_targets ?? ['cf-static']).includes('cf-static'))
    .map((entry) => entry.slug);
  if (slugs.length === 0) throw new Error('No cf-static entries in static-spaces.registry.json');
  return slugs;
}

// Headless Chromium has no GPU; SwiftShader gives the scatter panel a real
// WebGL context so the canvas is not captured blank.
const CHROMIUM_ARGS = [
  '--use-gl=swiftshader',
  '--enable-webgl',
  '--ignore-gpu-blocklist',
  '--enable-unsafe-swiftshader',
];

/**
 * The sibling checkout's Playwright pins a browser revision that may not be
 * the one actually downloaded into the shared ms-playwright cache. Fall back
 * to the newest full Chromium sitting in that cache rather than forcing a
 * fresh `playwright install` on every machine.
 */
function resolveChromiumExecutable() {
  if (process.env.PREVIEW_CHROMIUM_PATH) return process.env.PREVIEW_CHROMIUM_PATH;
  const cache =
    process.env.PLAYWRIGHT_BROWSERS_PATH ||
    path.join(process.env.HOME || '', 'Library', 'Caches', 'ms-playwright');
  let entries;
  try {
    entries = fs.readdirSync(cache);
  } catch {
    return undefined;
  }
  const builds = entries
    .filter((name) => /^chromium-\d+$/.test(name))
    .sort((a, b) => Number(b.split('-')[1]) - Number(a.split('-')[1]));
  const relativeBinaries = [
    'chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing',
    'chrome-mac/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing',
    'chrome-linux/chrome',
    'chrome-win/chrome.exe',
  ];
  for (const build of builds) {
    for (const relative of relativeBinaries) {
      const candidate = path.join(cache, build, relative);
      if (fs.existsSync(candidate)) return candidate;
    }
  }
  return undefined;
}

async function main() {
  const slugs = onlySlugs.length ? onlySlugs : readSlugs();
  fs.mkdirSync(outDir, { recursive: true });

  const launchOptions = { args: CHROMIUM_ARGS };
  let browser;
  try {
    browser = await chromium.launch(launchOptions);
  } catch (error) {
    const executablePath = resolveChromiumExecutable();
    if (!executablePath) throw error;
    console.warn(`Playwright's pinned browser is missing; using ${executablePath}`);
    browser = await chromium.launch({ ...launchOptions, executablePath });
  }
  const context = await browser.newContext({
    viewport: VIEWPORT,
    deviceScaleFactor: 1,
  });

  const captured = [];
  const skipped = [];

  for (const slug of slugs) {
    const url = `${baseUrl}/${slug}/`;
    const page = await context.newPage();
    const consoleErrors = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') consoleErrors.push(msg.text());
    });

    try {
      const response = await page.goto(url, { waitUntil: 'networkidle', timeout: 90_000 });
      if (response && !response.ok()) {
        throw new Error(`HTTP ${response.status()}`);
      }

      // Wait for the shell to actually paint content: a WebGL/scatter canvas,
      // or a decoded thumbnail in the sample grid.
      await page.waitForFunction(
        () => {
          const canvas = [...document.querySelectorAll('canvas')].some(
            (c) => c.clientWidth > 0 && c.clientHeight > 0,
          );
          const image = [...document.querySelectorAll('img')].some((i) => i.naturalWidth > 0);
          return canvas || image;
        },
        undefined,
        { timeout: 90_000 },
      );

      await page.waitForTimeout(SETTLE_MS);

      const text = await page.evaluate(() => document.body.innerText || '');
      const broken = /Panel unavailable|Something went wrong|Failed to load|Application error/i.test(text);
      if (broken) {
        const line = text.split('\n').find((l) => /Panel unavailable|Something went wrong|Failed to load|Application error/i.test(l));
        skipped.push({ slug, reason: `error state on page: ${line?.trim()}` });
        console.error(`SKIP ${slug}: ${line?.trim()}`);
        await page.close();
        continue;
      }

      const target = path.join(outDir, `${slug}.png`);
      await page.screenshot({ path: target, fullPage: false });
      captured.push(slug);
      console.log(`OK   ${slug} -> spaces-site/previews/${slug}.png`);
    } catch (error) {
      skipped.push({ slug, reason: error.message });
      console.error(`SKIP ${slug}: ${error.message}`);
    } finally {
      if (!page.isClosed()) await page.close();
    }
  }

  await browser.close();

  console.log(`\ncaptured ${captured.length}/${slugs.length}`);
  if (skipped.length) {
    for (const { slug, reason } of skipped) console.log(`  not written: ${slug} (${reason})`);
    process.exitCode = 1;
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
