---
title: HyperView
emoji: 🔮
colorFrom: purple
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# HyperView Hello World

This is the main HyperView starter Space, served at
[hyper3labs/HyperView](https://huggingface.co/spaces/hyper3labs/HyperView). It shows the same higher-resolution,
taxonomy-backed image sample through three geometric views and includes a small
custom introduction panel built with the public HyperView panel SDK:

- CLIP (`openai/clip-vit-base-patch32`) in Euclidean 3D
- CLIP (`openai/clip-vit-base-patch32`) in spherical 3D
- Hyper3-CLIP (`hyper3-clip-v1`) in hyperbolic Poincaré 2D

The sample is drawn from `evendrow/inat24_tiny`, a compact iNaturalist 2024
subset with 1,000 images, 100 species, and taxonomy metadata. The visible label
is the broad `supercategory`, while sample metadata keeps common name, species,
kingdom, phylum, class, order, family, genus, location fields, license, and
rights holder.

Built with `hyperview==1.2.0` and `hyper-models[ml]==0.4.0`.

## Dataset

The default stratified sample contains 300 images:

| Label | Samples |
| --- | ---: |
| plants | 50 |
| insects | 50 |
| birds | 42 |
| arachnids | 36 |
| amphibians | 30 |
| reptiles | 26 |
| fungi | 26 |
| mammals | 20 |
| fish | 10 |
| mollusks | 10 |

This keeps the demo small enough for Hugging Face CPU Spaces while preserving a
real biological hierarchy for geometry comparison. Images are resized only
when they exceed 1024 × 1024, avoiding the tiny 32 × 32 appearance of CIFAR.

## Build and deploy

The Space does not compute anything at startup. It serves an exported bundle,
so it boots in seconds and needs no dataset download, model download or
`HF_TOKEN` secret.

```bash
uv venv -p 3.11 && uv pip install "hyperview==1.2.0" "hyper-models[ml]==0.4.0" "datasets>=4.5" "Pillow>=12"
python demo.py --build-only                      # builds the `hello-world` workspace
hyperview export hello-world --out ../../static-spaces/hello-world --similarity-k 10
```

`hyper3-clip-v1` is gated on Hugging Face: accept its terms and log in with
`hf auth login` before the first build.

Commit `static-spaces/hello-world/` to `main`. That redeploys spaces.hyper3labs.com
and the `Deploy HF Space - HyperView Hello World` workflow, which publishes the
bundle with `hyperview publish --mode live`; the Space runs
`hyperview serve --from <bundle> --public`.

## Reuse this template

1. Edit the constants block at the top of [demo.py](demo.py).
2. Update the stratification labels and target counts.
3. Change `WORKSPACE_ID` and register the new bundle in `static-spaces.registry.json`.
