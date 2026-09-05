---
title: HyperView Precision Region Search
emoji: 🎯
colorFrom: blue
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# HyperView Precision Regions

This demo asks one operational question: does the exact region described in
natural language reach the operator's first review screen?

It replays four RefCOCOg validation cases—facilities, retail, fleet, and
bench—inside the full HyperView shell. Each case shows:

- the original COCO source photo with the annotated region boxed;
- the exact ground-truth crop at native resolution;
- aligned Top-5 text-to-region results for Hyper3-CLIP and CLIP B/32;
- the target rank for each model, including ranks below the visible Top-5.

Every image here is produced by `scripts/eval_precision_regions.py`: the query
text and the result captions are the RefCOCOg referring expressions of the
regions shown, the ranked tiles are the very crops the benchmark scored, and
the ranks are read from its output. Both models rank the same shared pool of
180 region crops, so a result tile can come from any image in the pool.

The four cases are diagnostic, not a highlight reel. Facilities and retail show
Hyper3-CLIP surfacing the described region while CLIP B/32 buries it (#1 vs #7,
#2 vs #12); fleet is a narrow case where both models keep the described bus in
the visible shortlist (#1 vs #2); bench is a case the baseline wins outright
(#9 vs #1). Aggregate metrics for the whole 180-query subset are in the panel.

The static export supports prepared case switching and sample selection. It does
not expose a free-text input because new text queries and model inference require
a live HyperView Space. No scatter or nearest-neighbour panel is used: those
contracts would misrepresent this text-conditioned region-ranking task.

## Run locally

From the HyperView repository root:

```bash
HYPERVIEW_PORT=6267 uv run python \
  hyperview-spaces/demos/precision-region-search-refcocog-hyper3clip/demo.py
```

Then open the URL printed by the launcher.

## Claim boundary

This is a bounded RefCOCOg validation probe against CLIP B/32, not a production
inspection benchmark and not evidence that either model is ready to automate an
operations workflow without further evaluation.
