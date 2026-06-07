---
title: HyperView VisA Manufacturing
emoji: 🏭
colorFrom: gray
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# HyperView - VisA Manufacturing Reference Retrieval

This Space builds a balanced subset of the VisA industrial visual anomaly
dataset and opens HyperView with two side-by-side embedding spaces:

- CLIP ViT-B/32 in a Euclidean 2D layout
- Hyper3-CLIP `hyper3-clip-v0.5` from the public `hyper-models` provider in a Poincare 2D layout

The workflow is inspection reference retrieval: given a production-line
inspection image, retrieve the right normal references for the same SKU or
product family. This maps to a real manufacturing QA pain point: engineers need
to compare a questionable camera frame against the correct part library rather
than a visually similar but wrong line or variant.

## Benchmark Context

Fresh local probe on 600 VisA samples, using test inspection images as queries
and train split images as the normal reference library:

| Metric | Hyper3-CLIP | CLIP-B/32 |
|---|---:|---:|
| Same-SKU mAP | 0.9995 | 0.9924 |
| Macaroni2 same-SKU mAP | 1.0000 | 0.9377 |
| Same-SKU P@10 | 1.0000 | 0.9983 |
| Family P@10 | 1.0000 | 0.9997 |
| Off-family leakage@10 | 0.0000 | 0.0003 |

The live Space uses a smaller cached interactive subset by default
(`VISA_SAMPLES_PER_CATEGORY=4` in local smoke runs) so the maps open quickly.
The benchmark table above is the full 600-image protocol.

Keep the claim narrow: this is not defect segmentation or anomaly AUROC. It is
a reference-retrieval workflow for inspection image libraries, where Hyper3-CLIP
keeps same-SKU and same-family references slightly cleaner than CLIP on this
sample.

Pilot framing: two lines, four SKUs, two weeks, using the plant's normal-reference
image library. Success metrics should be wrong-SKU reference retrieval and QA
lookup time, not defect segmentation accuracy.

Suggested acceptance thresholds: 30%+ faster QA reference lookup, 50%+ fewer
wrong-SKU top-10 references versus the current baseline, at least three hard
negative SKU families, and a failure report with abstentions/top misses.

Run locally from the HyperView repo:

```bash
VISA_SAMPLES_PER_CATEGORY=12 HYPERVIEW_PORT=6265 \
  uv run python hyperview-spaces/spaces/manufacturing-visa-reference-clip-hyper3clip/demo.py
```

The Docker image installs the bundled latest HyperView wheel for this repo and
uses HyperView's public dataset, UI, and panel command APIs. Hyper3-CLIP loads
through the public `hyper-models` provider catalog entry for the gated
`hyper3labs/hyper3-clip-v0.5` model repository. The Space needs an `HF_TOKEN`
secret with access to that model. If unavailable, the Space can start with a
clearly labeled CLIP fallback unless `HYPERVIEW_ALLOW_CANDIDATE_FALLBACK=0` is
set.
