---
title: Jaguar Multi-Geometry — source build
emoji: 🐆
sdk: docker
app_port: 7860
---

# Jaguar Multi-Geometry

Canonical source for the paper-facing [Jaguar Space](https://huggingface.co/spaces/hyper3labs/jaguar-hyperview-multigeometry),
published as a **Static Space**, not a live Docker runtime. The Dockerfile here
is only a reproducible build environment. `SPACE_README.md` is the published
static Space card.

Build and export from `hyperview-spaces/`:

```bash
HYPERVIEW_NO_AUTH=1 uv run --no-project --with 'hyperview==1.1.1' --python 3.12 python demos/jaguar-multigeometry/demo.py \
  --export static-spaces/jaguar-multigeometry
uv run --project ../ python scripts/check_jaguar_static.py static-spaces/jaguar-multigeometry \
  --report static-spaces/jaguar-multigeometry/research/artifact-verification.json
```

`demo.py` uses public `Dataset.register_embeddings`, `register_layout`, and
`Session.export` APIs. Every dataset/embedding download is pinned. The committed
`research-snapshot.json` captures the original production metadata, coordinates,
and representative neighbor results; it is not regenerated during a build.

The public `JaguarDataset.find_similar` specialization deliberately preserves
legacy cosine scoring for all models, even Lorentz. Export calls that method;
the build corrects the generated metric labels to `cosine` afterward. Always
export with this recipe (or the registry exporter), not a bare export of a
reopened dataset, which would use current HyperView's geometry-aware scoring.

The original 1,895 images, labels, split tags, three model vectors and projection
coordinates must remain unchanged. Neighbor checks tolerate float32 rounding
and permutations of distance ties, not changed neighborhoods.

Source/assets from the original HF revision stay in the HF cache; generated
media and local workspace files are under ignored `demo_data/`. The ignored
bundle goes under `static-spaces/jaguar-multigeometry/`. No GPU is required.

## Publish

Use `scripts/publish_jaguar_static.py <bundle> --parent-commit <current-HF-SHA>`
to verify and show the plan; add `--apply` to upload. The script preserves the
original files, keeps a rollback tag, and rejects a concurrent remote change.
Use a local `hf auth` login or `HF_TOKEN` injected by Infisical. This is a
reviewed manual deployment, not a Docker workflow triggered by a source push.
See [the migration record](../../docs/jaguar-static-migration.md) for validation
evidence and rollback instructions.
