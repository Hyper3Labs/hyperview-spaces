---
title: HyperView
emoji: 🔮
colorFrom: purple
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# HyperView - iNat24 Tiny Geometry Showcase

This is the main HyperView demo Space. It shows the same taxonomy-backed image
sample through multiple geometric views:

- CLIP (`openai/clip-vit-base-patch32`) in Euclidean 3D
- CLIP (`openai/clip-vit-base-patch32`) in spherical 3D
- HyCoCLIP (`hycoclip-vit-s`) in Poincare 2D

The sample is drawn from `evendrow/inat24_tiny`, a compact iNaturalist 2024
subset with 1,000 images, 100 species, and taxonomy metadata. The visible label
is the broad `supercategory`, while sample metadata keeps common name, species,
kingdom, phylum, class, order, family, genus, location fields, license, and
rights holder.

The Docker image installs released packages from PyPI:

- `hyperview==0.6.2`
- `hyper-models[ml]==0.3.0`

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
real biological hierarchy for geometry comparison.

## Reuse This Template

When copying this folder for another dataset:

1. Edit the constants block at the top of [demo.py](demo.py).
2. Update the stratification labels and target counts.
3. Rename the copied Space from `HyperView` to your project name.
4. Point a deploy workflow at the new folder.

## Deploy Source

This folder is synchronized to `hyper3labs/HyperView` by GitHub Actions from
the `hyperview-spaces` deployment repository.
