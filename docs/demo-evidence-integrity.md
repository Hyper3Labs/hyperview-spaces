# Demo evidence: what each one can actually back up

The README tells a reader that every Shared View "shows the per-case evidence
for both, including the cases CLIP wins." That is the right promise. It was not
true of every demo; this page is the audit that closed the gap, and what is
still open.

## Case selection

| Demo | Cases shipped | Shows a CLIP win |
| --- | --- | --- |
| fashion-deepfashion | `light-denim-leggings` (1 vs 32), `patterned-romper` (1 vs 138), `ampersand-tee` (12 vs **1**) | yes |
| geospatial-eurosat | 3 `*-win` cases plus `airport-regression` | yes |
| precision-region-search | `facilities` (1 vs 20), `retail` (1 vs 12), `fleet` (1 vs 4), `bench` (**9** vs 1) | yes — fixed, see below |

Precision Regions was the problem. It shipped three cases hyper3-clip wins and
none it loses, against its own benchmark reporting a near-even split — which
describes a 55/50 result as a sweep. A prospect who read the benchmark line and
then counted the cases would notice.

Both halves of that are now fixed: the demo ships a fourth case the baseline
wins, and the benchmark it prints is the one `scripts/eval_precision_regions.py`
reproduces.

This demo is live at `/spaces/precision-regions/`.

### Measured: the split is 62/47/71, not 3/0

`scripts/eval_precision_regions.py` now reproduces the benchmark from public
data. Over the same 180 queries:

| | hyper3-clip wins | CLIP wins | Ties |
| --- | ---: | ---: | ---: |
| Queries | 62 | 47 | 71 |

CLIP ranks the target strictly better on **47 of 180 queries — 26%**. The demo
shipped three cases and none of them was one of those 47. Candidates considered,
worst gap first:

| Expression | CLIP | hyper3 | Gap |
| --- | ---: | ---: | ---: |
| The back of someone to the upper right corner of the picture | 38 | 73 | 35 |
| the chair the man in the red shirt is sitting in | 23 | 56 | 33 |
| A leg with jeans on next to a woman | 7 | 29 | 22 |
| A man getting ready to cut a cake. | 6 | 20 | 14 |

None of those four is displayable, though. The panel shows each model's top five
and marks the target inside them, so a case only reads correctly when the winning
model ranks the target in its top five — and in all four above, CLIP's best is
rank 6. Restricting to `clipRank <= 3` leaves exactly two candidates:

| Expression | CLIP | hyper3 | Sample |
| --- | ---: | ---: | --- |
| An empty seat at on a bench. | 1 | 9 | `refcocog-val-2061563` |
| A white tabletop. | 2 | 10 | `refcocog-val-1620331` |

**`An empty seat at on a bench.` ships as the `bench` case.** CLIP ranks it
first; hyper3-clip returns five plausible chairs — an office chair, a bleacher,
a wicker chair — before reaching the annotated bench seat at rank 9. It is the
better of the two because the near-misses are coherent rather than random
(the `A white tabletop.` loss returns scissors, donuts and a muffin), and
because it mirrors the `facilities` case in the same furniture domain with the
opposite outcome. The expression keeps RefCOCOg's own wording, typo included,
since that is the string the eval actually ranked.

The two largest-gap cases are both spatial-relational phrases ("upper right
corner", "the chair the man ... is sitting in"), which remains the more
interesting finding — that is where this model is weaker — but neither can be
rendered in the top-five panel.

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
numbers could not be regenerated, and the original protocol did not record its
row selection, answer-field choice, or crop rounding, so there was no way to
tell whether the difference was a protocol detail or something else.

**`evidence_cases.json` now carries the measured column.** The demo prints
52.8/48.3, 90.6/83.9 and 0.662/0.615, and records
`benchmark.source: "scripts/eval_precision_regions.py"` so the figures name the
thing that regenerates them. The `bench` case ranks come from the same run, so
the table and the examples cannot drift apart. A number a customer cannot
reproduce is not doing the work a number is supposed to do.

## GeoSpatial's stated source cannot rebuild its dataset

Same class of problem, found while trying to fix the deployment blocker.

`evidence_cases.json` declares the protocol as `tanganke/resisc45`, split
`test`, "60 curated tiles; 12 scene classes; 5 tiles per class". The 60 sample
ids are recorded in
`demos/geospatial-eurosat-clip-hyper3clip/dataset_manifest.json`, extracted
from the local prepared dataset.

That declared source cannot regenerate them:

- `tanganke/resisc45` exposes only `{image, label}`. There is **no filename or
  image-id field**, so an id like `resisc45_airport_358` has nothing to match.
- Its `test` split holds 6300 rows — 140 per class. The manifest contains class
  indices of 358, 327, 297, 230, 174. Those cannot be row indices into a
  140-row-per-class split.
- Resolving all 60 by row-order-within-class against that split recovers
  **39 of 60**.

So the ids are original RESISC45 filename numbers (1–700 per class), and the
tiles were drawn from the full dataset or from a mirror that preserves
filenames. Which one is not recorded. The manifest keeps the 60 ids — they were
previously written down nowhere — but is marked `provenance_status:
"unresolved"` until the actual source is identified.

This matters beyond tidiness: it is the reason the demo cannot be converted to
build-at-boot the way `art-text-search-clip-hyper3clip` does. A rebuild needs a
source that can resolve these ids, and the declared one cannot.

## What to do

1. ~~Add a losing case to Precision Regions.~~ **Done** — `bench` ships, drawn
   from the reproducible run. The README's "including the cases CLIP wins" now
   holds for this demo.
2. ~~Commit the eval that produces the 180-query benchmark.~~ **Done** —
   `scripts/eval_precision_regions.py` ships and the demo prints its output.
3. **Still open: GeoSpatial's provenance**, above. Its 60 tile ids cannot be
   resolved against the source the demo declares.

Neither of the first two is a hedge. The demos are strongest when the losses are
visible: the
Fashion demo already shows `ampersand-tee`, where CLIP ranks the target first
and hyper3-clip ranks it twelfth, and it is more convincing for it.
