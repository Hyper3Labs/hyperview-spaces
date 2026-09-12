# Jaguar: preserve the paper URL during static migration

Migration date: 2026-09-12. The paper-facing repository remains at
https://huggingface.co/spaces/hyper3labs/jaguar-hyperview-multigeometry
with the new static application URL
https://hyper3labs-jaguar-hyperview-multigeometry.static.hf.space/.
The old direct Docker `.hf.space` host returns 404. The canonical Hugging Face
Space page is preserved, but papers embedding or linking directly to the old
app host must update that direct URL. Hugging Face reports the correct app URL
in the Space API's `host` field; monitors must use that instead of assuming the
Docker hostname.

## Same repository, same link

Hugging Face selects the SDK from the repository README frontmatter. A tested
static export can replace the application within this **same** repository using
`sdk: static` and `app_file: index.html`. Do not rename, delete, or recreate the
repository: retaining its owner/name retains the paper-facing Space URL. The
direct app host changes from `.hf.space` to `.static.hf.space`; it is not the
same URL as the stable repository page.

Reference: https://huggingface.co/docs/hub/spaces-sdks-static

## Preserved research inputs

- Source revision: `214644d68ee4f10d7a5dbc768ed76af00febe62c`.
- Dockerfile pins HyperView `0.3.1`; the legacy health payload reports `0.1.0`.
- Dataset: `hyper3labs/jaguar-hyperview-demo`, config `default`, split `train`.
- Asset manifest: `assets/manifest.json`, generated 2026-04-05.
- 1,895 foreground-only images, with train/validation tags and identity labels.
- Triplet T0/MSV3 seed 43: 2,152-dimensional embeddings, Euclidean 2D view.
- ArcFace O0/MSV3 seed 44: 2,152-dimensional embeddings, spherical 3D view.
- Lorentz O1/MSV3 seed 44: 257-dimensional embeddings, Poincare 2D view.
- All three embedding arrays are already committed under `assets/models/`;
  no model training or new GPU inference is needed for a static migration.

## Implementation and verification

The legacy app used private storage APIs, computed UMAP at boot, and patched a
specific frontend JavaScript chunk. The canonical source now lives in
`demos/jaguar-multigeometry/`, uses public HyperView APIs, and exports with
released HyperView `1.1.1`. No GPU inference, training, or layout recomputation
is performed. The original vectors and published coordinate arrays are imported.

- Original HF revision: `214644d68ee4f10d7a5dbc768ed76af00febe62c`.
- Dataset revision: `28110bb140951f84f11f23073d76412b367f65e4`.
- Rollback tag: `pre-static-2026-09-12`, pointing to the original HF revision.
- Published static revision: `6ebedced27990f1492ffe1442cb6f60a2a392c5a`
  ([HF commit](https://huggingface.co/spaces/hyper3labs/jaguar-hyperview-multigeometry/commit/6ebedced27990f1492ffe1442cb6f60a2a392c5a)).
- Frozen snapshot SHA256:
  `3b6b88cbda110b26bfb569c134099f357758ce3df23d85304080b7fc8d499fd1`.
- Artifact verification: 1,895 exact sample IDs/metadata; 3,790 readable image
  and thumbnail files; three exactly equal vector sets and coordinate sets;
  5,685 neighbor queries with 100 valid neighbors each; 93 legacy result checks.
- Maximum recorded legacy neighbor-distance error: `3.6272495218536704e-07`.
- Browser checks: spherical default, all three geometry tabs, side-by-side
  image grid, image inspection, neighbor browsing, identity filtering (Abril:
  21 samples), no application errors, and no backend requests.
- Production verification: static manifest, runtime state and both research
  reports match the tested local files by SHA256; all 17 original non-README
  repository files retain their original Git blob IDs. The monitor reports
  Jaguar `ok / STATIC` and Hello World/DeepFashion `ok / RUNNING`.

The UI shell is modernized rather than pixel-identical to the old patch.
Cosine distance is deliberately retained for **all** neighbor sets, including
Lorentz vectors; these must not be presented as canonical Lorentz retrieval
scores. Floating-point ties can reorder. A public `Dataset.find_similar`
specialization and corrected static metric labels preserve this contract.

## Rebuild and publish

Follow the pinned build/validation commands in
[`demos/jaguar-multigeometry/README.md`](../demos/jaguar-multigeometry/README.md).
The registry export driver invokes that demo's `--export` path, not a generic
reopened dataset that would switch the neighbor metric.

```bash
# Read the current HF revision, review it, then pass that exact value below.
hf spaces info hyper3labs/jaguar-hyperview-multigeometry
uv run --project ../ python scripts/publish_jaguar_static.py \
  static-spaces/jaguar-multigeometry --parent-commit <current-HF-SHA>
# Add --apply after reviewing the plan and browser-testing the bundle.
```

The publisher verifies the artifact and reviewed Space card, protects the
rollback tag, and uses an optimistic parent-commit guard. It uploads in one
commit, changes `README.md` to static, and **does not delete unmatched files**.
Only README overlaps the original tree; original Dockerfile, demo, asset files,
and generation scripts remain. The generic Docker publisher rejects this target.
HyperView's standard static publish dry-run was also checked, but its generated
card does not retain the research caveats, so the reviewed card is uploaded intact.

Jaguar is an HF-only static registry target. Cloudflare bundle collection skips
it while the gallery links to its existing HF URL. Both Python monitoring and
the pending Cloudflare status Worker validate its static manifest and dataset;
neither tries to wake a Python runtime. Rebuilds/publishing remain reviewed
manual operations; no Jaguar auto-deploy workflow is installed.

## Rollback

Verify the current HF revision, download `README.md` from
`pre-static-2026-09-12`, and upload that single file to the same Space with
`HfApi.upload_file(..., parent_commit=<current-HF-SHA>)`. That restores
`sdk: docker` and the original app settings. All original code/assets remain
in place; leave the extra static files untouched. Check the rebuilt runtime's
health, sample count and paper views, then restore the registry mode and its
corresponding monitor behavior. Do not rename or recreate the repository.

## Other rollout work

Cloudflare's six static demo pages already serve successfully at
`spaces.hyper3labs.com/<slug>/`. Deploying the registry-driven inventory/status
updates is separate: `/status.json` still returns 404, and the Cloudflare CI
deployment is gated by missing `INFISICAL_IDENTITY_ID` and
`INFISICAL_PROJECT_SLUG` repository variables (checked 2026-09-12).
