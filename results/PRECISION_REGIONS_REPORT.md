# Precision Regions benchmark reproduction

## Outcome

Partly reproduced. The evaluator completed all 180 queries with both HyperView providers and produced complete rankings. Hyper3-CLIP is close to the shipped aggregate; the measured CLIP metrics are materially lower, especially Hit@10.

## Measured versus claimed

| Metric | Claimed Hyper3 | Measured Hyper3 | Claimed CLIP | Measured CLIP |
|---|---:|---:|---:|---:|
| Query count | 180 | 180 | 180 | 180 |
| Hit@1 | 55.0% | 52.8% | 50.6% | 48.3% |
| Hit@10 | 90.0% | 90.6% | 87.8% | 83.9% |
| MRR | 0.669 | 0.661653 | 0.633 | 0.614916 |

The actual values above are read from `precision_regions_benchmark.json`; the run printed the same aggregate:

```text
{
  "clip": {
    "query_count": 180,
    "hit_at_1": 0.48333333333333334,
    "hit_at_10": 0.8388888888888889,
    "mrr": 0.6149163502355226,
    "mean_target_rank": 6.5777777777777775
  },
  "hyper3": {
    "query_count": 180,
    "hit_at_1": 0.5277777777777778,
    "hit_at_10": 0.9055555555555556,
    "mrr": 0.6616532356289716,
    "mean_target_rank": 5.372222222222222
  }
}
```

This does not corroborate the claim exactly. Hyper3-CLIP differs by -2.2 percentage points at Hit@1, +0.6 points at Hit@10, and -0.00735 MRR. CLIP differs by -2.3, -3.9, and -0.01808 respectively.

## Protocol and data source

The script uses the public, unauthenticated `lmms-lab/RefCOCOg` Hugging Face dataset, split `val`. No rate-limit or authentication failure occurred during this run. To avoid downloading the entire streaming split, selection is deterministic: take the first 180 records in the published streaming order, then sort those records by numeric `question_id`. Seed `0` is recorded in the output (there is no random sampling). The first non-empty `answer` string is the query expression.

For each selected row, the `[x,y,w,h]` bbox is converted to `[floor(x), floor(y), ceil(x+w), ceil(y+h)]` and clamped to the source image bounds. The resulting 180 crops form the complete shared pool and each query's target is its own crop. Crops are cached under `results/precision_regions_assets/`.

Embeddings are computed through HyperView's own providers: `embed-anything` with `openai/clip-vit-base-patch32` and `hyper-models` 0.3.1 with `hyper3-clip-v0.5`. Ranking uses cosine distance for CLIP and the provider-configured hyperboloid distance for Hyper3-CLIP.

## CLIP-win case

**Expression:** “A man getting ready to cut a cake.”  
**Source image id:** `COCO_train2014_000000208256_453172.jpg`  
**Target rank:** CLIP **6**, Hyper3-CLIP **20**

Top CLIP results were: “A man in Navy attire pulling something off a large cake.”, “a man in a red shirt”, “Man looking up with a green flannel checkered shirt on.”, “A balding man without a hat eating food.”, and “A boy with blond hair that has a blue tie on.” The target was rank 6. Hyper3-CLIP's top five were “An empty hotdog bun.”, “A utensil with a wooden handle sitting to the right of a pizza.”, “A guy in a white shirt.”, “A man in Navy attire pulling something off a large cake.”, and “A balding man without a hat eating food.”; the target was rank 20.

This is illustrative because the expression combines an actor, an action, and a distinctive cake context. CLIP keeps the cake/person semantics together and places the target near another cake crop, while Hyper3-CLIP's nearest neighbours are dominated by generic food, utensil, and person regions before reaching the target.

## Cleaner Hyper3-CLIP win

**Expression:** “a man flying a colorful kite”  
**Source image id:** `COCO_train2014_000000575971_1720455.jpg`  
**Target rank:** Hyper3-CLIP **7**, CLIP **64**

Hyper3-CLIP's top five were “A man in a red shirt with a baseball cap on backwards is painting an elephant.”, “a man in a red shirt”, “A black-haired male wearing black shorts and a white shirt with a tennis racket in his hand.”, “GREEN COLOR KITE HOLDING THE MAN”, and “A colorful paraglider on the ground.” The target was rank 7. CLIP's top five were “GREEN COLOR KITE HOLDING THE MAN”, “A boy in a pink shirt does a skateboard trick.”, “a man in a red shirt”, “A black-haired male wearing black shorts and a white shirt with a tennis racket in his hand.”, and “A man in a red shirt with a baseball cap on backwards is painting an elephant.”; the target was rank 64.

This is a cleaner complementary win by rank gap (57 places, larger than any shipped case). CLIP locks onto a related kite phrase but apparently the wrong region (the kite rather than the man), then prefers generic people/action crops. Hyper3-CLIP keeps several person/action neighbours and reaches the annotated man-plus-kite region at rank 7. For an exact rank-1 Hyper3 example, “red umprella with man wearing leather coat standing under it” is rank 1 versus CLIP rank 16 (source `COCO_train2014_000000176403_280506.jpg`).

## Files and re-run

- [scripts/eval_precision_regions.py](../scripts/eval_precision_regions.py) — deterministic evaluator.
- [precision_regions_benchmark.json](precision_regions_benchmark.json) — aggregate metrics plus every query's complete 180-item ranking for both models.
- `results/precision_regions_assets/` — cached deterministic crops used by the run.

From the repository root, re-run with:

```bash
/Users/matin/hyperview_org/HyperView/.venv/bin/python scripts/eval_precision_regions.py
```

The script uses no `uv` command. It may be given `--limit N`, `--seed 0`, `--work-dir PATH`, and `--output PATH` for controlled reruns.

## Verification and uncertainty

I re-read the written JSON and recomputed all three metrics from the stored target ranks. Both models have 180 rankings of length 180; stored and recomputed values match exactly. The JSON records the model space keys `embed-anything__openai_clip-vit-base-patch32__8da42c3ae90c` and `hyper-models__hyper3-clip-v0_5__42052c955756`.

The remaining uncertainty is protocol comparability: the original claim does not publish its exact 180-row selection, answer-field choice, crop rounding, or model/provider revisions. This reproduction therefore tests a precise public protocol, not an assertion that its selection is the historical hidden protocol. The Hugging Face stream and both model downloads were available unauthenticated for this run.
