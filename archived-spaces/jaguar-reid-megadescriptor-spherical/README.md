---
title: HyperView-Jaguar-ReID
emoji: 🐆
colorFrom: yellow
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

# HyperView - Jaguar Re-ID (MegaDescriptor + Sphere)

Archived: this Space was superseded by
`hyper3labs/jaguar-hyperview-multigeometry`, the paper-facing Jaguar geometry
comparison demo.

This Space runs the Jaguar Re-ID dataset through the MegaDescriptor timm
backbone and renders the result with HyperView's spherical 3D layout.

This example now installs the released `hyperview[ml]==0.3.1` package from
PyPI, which includes the `timm-image` provider and spherical 3D layout support
required by this demo.

This demo uses:

- Hugging Face dataset `hyper3labs/jaguar-re-id`
- Config `default`
- Split `train`
- Image field `image`
- Label field `label`
- Sample count `200`
- Embedding model `hf-hub:BVRA/MegaDescriptor-L-384`
- Layout `spherical` (3D)

## Build model

The Dockerfile precomputes the dataset, embeddings, and layout during image
build so the runtime container only needs to launch HyperView.

Because MegaDescriptor inference runs during Docker build on CPU, this Space
keeps the sample count modest and uses a smaller batch size than the local demo
script to stay within typical Hugging Face build limits.

## Reuse this example

If you need a simple starter, copy `spaces/inat24-tiny-clip-hycoclip` first.
If your own Space needs a timm backbone or a spherical 3D layout, copy this
folder instead and change the constants block at the top of [demo.py](demo.py).

When contributing your own Space back to this repository, add a row to the
community table in the root `README.md` and include your Hugging Face Space ID
in the pull request description.

## Deploy source

This folder is synchronized to Hugging Face Spaces by GitHub Actions from the
`hyperview-spaces` deployment repository.
