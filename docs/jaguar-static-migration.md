# Jaguar: preserve the paper URL during static migration

Checked 2026-09-11. The production Space remains running and unchanged at
https://huggingface.co/spaces/hyper3labs/jaguar-hyperview-multigeometry
with application URL
https://hyper3labs-jaguar-hyperview-multigeometry.hf.space/.

## Same repository, same link

Hugging Face selects the SDK from the repository README frontmatter. A tested
static export can replace the application within this **same** repository using
`sdk: static` and `app_file: index.html`. Do not rename, delete, or recreate the
repository: retaining its owner/name retains the paper-facing Space URL. Verify
the existing application URL and any paper deep links after the SDK switch.

Reference: https://huggingface.co/docs/hub/spaces-sdks-static

## What exists today

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

## Migration work required before switching production

This is not an SDK-only edit. The current application builds a runtime dataset,
uses private storage APIs to install the embeddings, computes UMAP layouts, and
patches a specific frontend JavaScript chunk for its initial spherical panel.
Its repository does not contain an exported static workspace.

1. Pin the current Space, dataset, and embedding asset revisions; preserve the
   existing published source as a rollback tag before any production change.
2. Port ingestion and precomputed embedding import to the current public
   HyperView API. Preserve sample IDs, identity labels, split tags, foreground
   images, vector values, model names, and geometry metadata.
3. Preserve the existing layout coordinates where accessible. If layouts must
   be regenerated, compare them against the published view and explicitly
   record that the projection changed; do not imply a byte-identical paper view.
4. Declare the three panels and initial spherical view in runtime workspace
   state rather than patching frontend code. Export a candidate static bundle.
5. Verify every sample/media asset, all three geometries, selection and neighbor
   browsing, and the same train/validation subset. Preserve the Space card's
   caveat that the old runtime's cosine neighbor scores are not canonical
   Lorentz-distance retrieval scores.
6. Test the candidate before uploading it to the existing HF repository as a
   Static HTML Space. Verify both existing URLs and restore the old revision if
   the published app is not equivalent.

The archive operation deliberately does not alter Jaguar's repository, runtime,
or keep-warm policy. Complete and verify this migration before changing the
paper-facing application.
