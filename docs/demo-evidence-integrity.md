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

## Reproducibility

`fashion-deepfashion` states `photoBenchmark.queryCount: 710` over
`candidateCount: 741`, and it ships a 741-sample dataset. The numbers line up
with an artifact that exists.

`precision-region-search` states `benchmark.queryCount: 180`, but the dataset
it ships (`refcocog_text_region_evidence_v3`) holds **32 samples and zero
embedding spaces** — source scenes and result crops for display, with the
per-case `results` lists hand-authored as text. Nothing in the repository can
regenerate the 180-query numbers. The eval that produced them lives somewhere
else.

That is not evidence of anything being wrong with the numbers. It does mean
the strongest claim on the page cannot be checked by anyone who clones this
repo, which is the same thing as not being checkable by a customer.

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
