# Demo evidence: what each one can actually back up

The README tells a reader that every Shared View "shows the per-case evidence
for both, including the cases CLIP wins." That is the right promise. It is not
currently true of every demo.

## Case selection

| Demo | Cases shipped | Shows a CLIP win |
| --- | --- | --- |
| fashion-deepfashion | `light-denim-leggings` (1 vs 32), `patterned-romper` (1 vs 138), `ampersand-tee` (12 vs **1**) | yes |
| geospatial-eurosat | 3 `*-win` cases plus `airport-regression` | yes |
| precision-region-search | `facilities` (1 vs 20), `retail` (1 vs 12), `fleet` (1 vs 4) | **no — 3 of 3 are wins** |

Precision Regions is the problem. Its own benchmark reports `clipHit1: 50.6%`
against `hyper3Hit1: 55.0%` — a near-even split. Shipping three cases that
hyper3-clip wins, and none it loses, describes a 55/50 result as a sweep. A
prospect who reads the benchmark line and then counts the cases will notice.

This demo is live at `/spaces/precision-regions/`.

### Measured: the split is 62/47/71, not 3/0

`scripts/eval_precision_regions.py` now reproduces the benchmark from public
data. Over the same 180 queries:

| | hyper3-clip wins | CLIP wins | Ties |
| --- | ---: | ---: | ---: |
| Queries | 62 | 47 | 71 |

CLIP ranks the target strictly better on **47 of 180 queries — 26%**. The demo
ships three cases and none of them is one of those 47. Concrete candidates,
worst gap first:

| Expression | CLIP | hyper3 | Gap |
| --- | ---: | ---: | ---: |
| The back of someone to the upper right corner of the picture | 38 | 73 | 35 |
| the chair the man in the red shirt is sitting in | 23 | 56 | 33 |
| A leg with jeans on next to a woman | 7 | 29 | 22 |
| A man getting ready to cut a cake. | 6 | 20 | 14 |

`A man getting ready to cut a cake.` is the most presentable: both models find
it, CLIP at 6 and hyper3-clip at 20, so it reads as a real ranking difference
rather than a freak miss. The two largest-gap cases are both spatial-relational
phrases ("upper right corner", "the chair the man ... is sitting in"), which is
itself the more interesting finding — that is where this model is weaker.

## Reproducibility

`fashion-deepfashion` states `photoBenchmark.queryCount: 710` over
`candidateCount: 741`, and it ships a 741-sample dataset. The numbers line up
with an artifact that exists.

`precision-region-search` states `benchmark.queryCount: 180`, but the dataset
it ships (`refcocog_text_region_evidence_v3`) holds **32 samples and zero
embedding spaces** — source scenes and result crops for display, with the
per-case `results` lists hand-authored as text.

`scripts/eval_precision_regions.py` closes that gap: it pulls `lmms-lab/RefCOCOg`
val unauthenticated, builds a deterministic 180-query crop pool, embeds it with
both models through HyperView's own provider layer, and writes the metrics and
per-query ranks. It does not reproduce the shipped numbers exactly:

| Metric | Claimed h3 | Measured h3 | Claimed CLIP | Measured CLIP |
| --- | ---: | ---: | ---: | ---: |
| Hit@1 | 55.0% | 52.8% | 50.6% | 48.3% |
| Hit@10 | 90.0% | 90.6% | 87.8% | **83.9%** |
| MRR | 0.669 | 0.662 | 0.633 | 0.615 |

Both models measure lower than claimed, CLIP more so — its Hit@10 is 3.9 points
below the published figure. Note this makes the *gap* wider than advertised,
not narrower, so nothing here flatters hyper3-clip less. But the shipped
numbers cannot currently be regenerated, and the original protocol did not
record its row selection, answer-field choice, or crop rounding, so there is no
way to tell whether the difference is a protocol detail or something else.

Either restate the benchmark from this script's output, or commit the protocol
that produced the original figures. A number a customer cannot reproduce is not
doing the work a number is supposed to do.

## What to do

1. **Add a losing case to Precision Regions.** This requires re-running the
   RefCOCOg text-to-region ranking for both models over the evaluation crop
   pool and picking a query where CLIP ranks the target higher. Until then the
   README's "including the cases CLIP wins" does not hold for this demo.
2. **Commit the eval that produces the 180-query benchmark**, or restate the
   claim in terms of what ships. Preferably the former — the honest posture
   these demos take is only worth anything if the numbers are checkable.

Neither is a hedge. The demos are strongest when the losses are visible: the
Fashion demo already shows `ampersand-tee`, where CLIP ranks the target first
and hyper3-clip ranks it twelfth, and it is more convincing for it.
