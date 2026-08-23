---
title: HyperView Visual Safety
emoji: 🛡️
colorFrom: yellow
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
---

# HyperView Visual Safety — review-queue trade-off

This demo answers one bounded operations question for a trust-and-safety
review-operations lead:

> On a curated 120-image Open Images label proxy, is Hyper3-CLIP's one
> additional caught proxy-positive worth five additional false reviews and a
> six-item larger queue versus CLIP?

It is a fixed, auditable image-neighbour ledger—not a production content-policy
classifier. Object labels are only proxies, and scores are neighbour-vote
fractions, not calibrated safety probabilities.

## Workspace layout

The full HyperView shell hosts three panels:

1. **Hyper3-CLIP · Review queue** — native Samples result panel over a prepared
   Hyper3 queue collection.
2. **CLIP ViT-B/32 · Review queue** — native Samples result panel over a prepared
   CLIP queue collection.
3. **Review-queue trade-off audit** — compact bottom extension panel with the
   operational scoreboard, fixed-threshold explanation, prepared queue-slice
   toggles, and four representative disagreement selectors.

Native Samples owns queue browsing, media, and selection. The custom panel does
not render a result grid or evidence image. Geometry/Scatter is intentionally
omitted: the claim is about queue composition, not embedding layout, and this
ledger has no trustworthy layout artifact.

Prepared queue slices (full queues, disagreements, false reviews, misses) are
materialized once at launch through public `session.ui.show_samples` and
switched via documented panel props. There is no runtime mutation of durable
workspace data.

## Evidence protocol

- Dataset: 120 public Open Images V7 validation images, 60 proxy-positive and
  60 proxy-negative.
- Models: OpenAI CLIP ViT-B/32 and Hyper3-CLIP v0.5 image embeddings.
- Scoring: leave-one-out vote among seven nearest neighbours in each persisted
  image-embedding space.
- Operating point: queue at least five proxy-positive neighbours, applying the
  same fixed supermajority rule to both models without fitting a threshold.
- Reproducibility: `benchmark.json` contains the complete 120-row prediction
  ledger, neighbour IDs, metrics, protocol, and content hash.
- Audit cases: one candidate gain, one candidate-only false review, one residual
  miss, and one shared false review, selected from that same ledger.

At this operating point CLIP queues 62/120 with 58 TP, 4 FP, 2 FN, and 56 TN.
Hyper3-CLIP queues 68/120 with 59 TP, 9 FP, 1 FN, and 51 TN. CLIP is also
stronger on this proxy's AUROC and average precision. The visible decision is
therefore a real workload/recall trade-off, not a candidate-model victory.

## Run and export

From the HyperView repository:

```bash
HYPERVIEW_PORT=18248 uv run python \
  hyperview-spaces/demos/visual-safety-content-clip-hyper3clip/demo.py
```

Then export the prepared workspace:

```bash
uv run hyperview export visual-safety-review-queue-evidence-v3 \
  --out dist/landing-demos/visual-safety-v3
```

The static export retains the full HyperView shell and supports prepared queue
browsing, slice switching, case selection, and sample selection. It does not
expose inference, threshold tuning, policy actions, model recomputation, or
Scatter geometry.

## Data and rights

The checked-in `demo_assets/` subset preserves every image's Open Images source
URL and CC BY 2.0 license in dataset metadata and the ledger. This bounded
demonstration does not cover production prevalence, contextual policy, sexual
content, hate, self-harm, jurisdiction, or seller metadata.
