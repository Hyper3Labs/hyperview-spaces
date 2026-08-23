---
title: HyperView DeepFashion Text Search
emoji: 👖
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# HyperView — DeepFashion typed-search audit

This demo is designed for an ecommerce search or merchandising lead asking two
questions: **does an attribute-heavy shopper request put the exact SKU on the
first results screen, and does the model organize the broader catalog into
coherent product categories?**

It presents three prepared shopper requests from a bounded DeepFashion
text-to-image probe. The compact query panel controls a native ranked Samples
panel, while a native Hyper3-CLIP scatter shows the full 741-product catalog
topology with standard pan, zoom, lasso, and shared selection.

The aggregate result is intentionally framed as modest: across 180
metadata-generated queries and 1,120 candidate images, Hit@1 is 24.4% vs 23.3%
and Hit@10 is 57.2% vs 55.0%. Hyper3 has 13 strong wins under the documented
cutoff and CLIP has 9. The selected case illustrates a real failure mode; it is
not evidence of a universal text-search advantage.

## Static behavior

The static export keeps the full HyperView shell and allows visitors to switch
among three prepared requests, compare the stored Hyper3-CLIP and CLIP Top 6,
browse the catalog, inspect exact targets, and explore the catalog topology. It
does not show an arbitrary text box because running a new query requires model
inference in a hosted HyperView Space.

The workspace uses the persisted 741-row demo catalog. The custom panel uses
normal JSX and public `HyperViewPanelSDK` hooks to orchestrate native panels;
it does not reimplement result grids or scatter controls.

## Run locally

From the HyperView repository:

```bash
uv run python hyperview-spaces/demos/fashion-deepfashion-text-search-clip-hyper3clip/demo.py
```

Use `HYPERVIEW_PORT=<port>` to choose another local port.

To run the full Live Space with arbitrary shopper text instead of the prepared
model-comparison walkthrough:

```bash
uv run python hyperview-spaces/demos/fashion-deepfashion-text-search-clip-hyper3clip/live_demo.py
```

The native Samples panel discovers text-capable indexes from the runtime and
routes new queries only to providers that can actually encode text.

## Claim boundary

- Dataset: `Marqo/deepfashion-inshop`, split `data`.
- Corpus: 1,120 images from 260 products.
- Query set: 180 queries generated from dataset metadata and visual attributes,
  not real shopper logs.
- Positive: any image view with the same DeepFashion product key.
- This comparison does not include newer SigLIP, OpenCLIP, Jina-CLIP, NV-CLIP,
  or Gemini baselines.

## Deploy source

This folder is intended to deploy to
`hyper3labs/HyperView-DeepFashion-Text-Search` from the `hyperview-spaces`
deployment repository.
