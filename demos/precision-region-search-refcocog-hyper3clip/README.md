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

It replays three prepared RefCOCOg validation cases—facilities, retail, and
fleet—inside the full HyperView shell. Each case shows:

- the source scene with the ground-truth region boxed;
- the exact ground-truth crop;
- aligned Top-5 text-to-region results for Hyper3-CLIP and CLIP B/32;
- the target rank for each model, including ranks below the visible Top-5;
- a separately labelled slice Hit@1 metric with validation-query count.

The two models use the same evaluation crop pool. The examples and slice metrics
are deliberately kept separate: a prepared example explains a failure mode,
while a slice metric summarizes its bounded evaluation subset. The fleet case
also exposes an aggregate tie even though Hyper3-CLIP wins the displayed example.

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
