---
title: HyperView Logo Brand Search
colorFrom: blue
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
---

# HyperView — Logo Search creative-brief audit

This demo is designed for a brand-operations or creative-asset lead asking two
questions:

1. **For a prepared creative brief, which logos are the best retrieval results
   under Hyper3-CLIP versus CLIP, and where is the known target ranked?**
2. **How is the full 160-logo catalog organized, so a reviewer can inspect
   visual/style coverage and outliers?**

The workspace uses the full persisted catalog
`logo_brand_search_clip_hyper3clip_hf_live_v4` (160 samples, four layouts). A
native Samples panel owns the prepared Top results, one native Hyper3 multimodal
scatter shows catalog topology with pan/zoom/lasso and shared selection, and a
compact right decision panel owns prepared briefs, brief attributes, business
interpretation, aggregate evidence, and the model toggle.

The comparison is Hyper3-CLIP v0.5 versus OpenAI CLIP ViT-B/32 on a bounded
160-row slice of `logo-wizard/modern-logo-dataset`. Each dataset caption ranks
the same 160 images and the paired logo is the one exact positive. Aggregate
text-to-logo results are:

- Hit@1: 35.6% (57/160) vs 16.3% (26/160)
- Hit@5: 73.1% (117/160) vs 48.8% (78/160)
- MRR delta: +0.207 for Hyper3-CLIP

Four curated briefs expose different brand-search constraints: barber motifs,
floral composition, construction geometry, and hospitality palette/motif. The UI
labels these as prepared evidence; the aggregate metrics cover the full
160-caption probe.

## Static behavior

The static export keeps the full HyperView shell and supports prepared-brief
switching, model toggles that rewrite native Samples with the exact prepared
ordered IDs, exact-target focus, browse-all, shared selection, and map
exploration. It does not expose arbitrary text search or model inference.

The custom panel uses normal JSX plus public `HyperViewPanelSDK` v2 hooks
(`usePanelState`, `useSampleResults`, `useSelection`). It does not reimplement a
result image grid, call private APIs, or use browser storage/events for
cross-panel coordination.

## Run locally

From the HyperView repository:

```bash
uv run python hyperview-spaces/demos/logo-brand-search-clip-hyper3clip/demo.py
```

Use `HYPERVIEW_PORT=<port>` to choose another local port. The launcher validates
that the full 160-row dataset and all prepared evidence IDs are present before
opening the multi-panel view.

## Claim boundary

The source dataset is small and synthetic/curated. Its detailed paired captions
are not real enterprise DAM queries, and this probe is not a production
trademark benchmark. It demonstrates a promising retrieval behavior that would
need validation against an organization's approved asset archive and real
search logs.

## Deploy source

This folder is intended to deploy from the `hyperview-spaces` repository.
