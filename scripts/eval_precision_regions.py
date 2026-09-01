#!/usr/bin/env python3
"""Reproduce the Precision Regions text-to-region benchmark.

The evaluator intentionally keeps the protocol small and inspectable:

* source: the public ``lmms-lab/RefCOCOg`` ``val`` streaming split;
* selection: take the first ``N`` records in the split's published stream,
  then sort those selected records by numeric ``question_id`` (the default N
  is 180; no random sampling is used, and the recorded seed is 0);
* target text: the first non-empty answer string in each record;
* crop: ``bbox=[x,y,w,h]`` with ``x1=floor(x)``, ``y1=floor(y)``,
  ``x2=ceil(x+w)``, ``y2=ceil(y+h)``, clamped to image bounds;
* pool: one crop per selected referring-expression record, including the
  query's own target crop;
* ranking: cosine distance for OpenAI CLIP and native hyperboloid distance
  (provider curvature) for Hyper3-CLIP.

All embeddings are computed by HyperView's provider layer.  The output JSON
contains aggregate metrics and complete per-query rankings for both models.
"""

from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path
from typing import Any

import hyperview as hv
from hyperview import Sample

DATASET_ID = "lmms-lab/RefCOCOg"
SPLIT = "val"
DEFAULT_LIMIT = 180
DEFAULT_SEED = 0
CLIP_MODEL = "openai/clip-vit-base-patch32"
HYPER3_MODEL = "hyper3-clip-v0.5"


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=root / "results" / "precision_regions_assets",
        help="Directory in which deterministic crop images are cached.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "results" / "precision_regions_benchmark.json",
    )
    parser.add_argument(
        "--hf-retries", type=int, default=5, help="Retries for transient HF errors."
    )
    return parser.parse_args()


def load_records(limit: int, retries: int) -> list[dict[str, Any]]:
    """Read the first *limit* rows from the public streaming split."""
    if limit <= 0:
        raise ValueError("limit must be positive")
    from datasets import load_dataset

    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            stream = load_dataset(DATASET_ID, split=SPLIT, streaming=True)
            records = []
            for row in stream:
                # Materialize only the fields needed later. Keeping the PIL
                # image object here prevents a second HF lookup for selected
                # records and avoids downloading rows beyond the limit.
                records.append(
                    {
                        "question_id": str(row["question_id"]),
                        "image": row["image"],
                        "answer": list(row.get("answer") or []),
                        "bbox": list(row["bbox"]),
                        "file_name": str(row.get("file_name") or ""),
                    }
                )
                if len(records) >= limit:
                    break
            if len(records) < limit:
                raise RuntimeError(
                    f"Requested {limit} rows but the {DATASET_ID}/{SPLIT} stream "
                    f"ended after {len(records)} rows"
                )
            # Numeric sort is stable and makes the chosen pool/order explicit.
            records.sort(key=lambda row: (int(row["question_id"]), row["question_id"]))
            return records
        except Exception as exc:  # pragma: no cover - exercised on transient HF failures
            last_error = exc
            if attempt + 1 >= retries:
                break
            delay = min(60.0, 2.0**attempt)
            print(
                f"HF load attempt {attempt + 1}/{retries} failed: {exc!r}; "
                f"retrying in {delay:g}s",
                flush=True,
            )
            time.sleep(delay)
    assert last_error is not None
    raise RuntimeError(f"Unable to load public {DATASET_ID}/{SPLIT}") from last_error


def crop_records(records: list[dict[str, Any]], work_dir: Path) -> list[dict[str, Any]]:
    work_dir.mkdir(parents=True, exist_ok=True)
    out: list[dict[str, Any]] = []
    for row in records:
        answers = [str(value).strip() for value in row["answer"] if str(value).strip()]
        if not answers:
            raise ValueError(f"Record {row['question_id']} has no non-empty answer")
        image = row["image"]
        width, height = image.size
        x, y, w, h = (float(value) for value in row["bbox"])
        left = max(0, min(width - 1, math.floor(x)))
        top = max(0, min(height - 1, math.floor(y)))
        right = max(left + 1, min(width, math.ceil(x + w)))
        bottom = max(top + 1, min(height, math.ceil(y + h)))
        sample_id = f"refcocog-val-{row['question_id']}"
        path = work_dir / f"{sample_id}.jpg"
        if not path.exists():
            image.crop((left, top, right, bottom)).convert("RGB").save(path, quality=95)
        out.append(
            {
                "sample_id": sample_id,
                "question_id": row["question_id"],
                "expression": answers[0],
                "all_answers": answers,
                "source_image_id": row["file_name"],
                "bbox": [x, y, w, h],
                "crop_box": [left, top, right, bottom],
                "crop_path": str(path),
                "image_size": [width, height],
            }
        )
    return out


def compute_model_rankings(
    dataset: hv.Dataset,
    records: list[dict[str, Any]],
    *,
    model: str,
    provider: str,
) -> tuple[str, list[list[dict[str, Any]]]]:
    space_key = dataset.compute_embeddings(
        model=model,
        provider=provider,
        batch_size=32 if provider == "embed-anything" else 1,
        show_progress=True,
    )
    # Rank the whole pool, not a top-k slice: the metrics below need the
    # target's rank wherever it lands. This is the same retrieval path the
    # demo's search box uses, so the benchmark measures the shipped behaviour
    # rather than a reimplementation of it.
    pool_size = len(dataset)
    rankings: list[list[dict[str, Any]]] = []
    for row in records:
        matches = dataset.find_similar_by_text(
            row["expression"], k=pool_size, space_key=space_key
        )
        rankings.append(
            [
                {
                    "rank": rank,
                    "sample_id": sample.id,
                    "distance": float(distance),
                    "is_target": sample.id == row["sample_id"],
                }
                for rank, (sample, distance) in enumerate(matches, start=1)
            ]
        )
    return space_key, rankings


def rank_of_target(rankings: list[dict[str, Any]], target_id: str) -> int:
    for item in rankings:
        if item["sample_id"] == target_id:
            return int(item["rank"])
    raise RuntimeError(f"Target {target_id} absent from ranking")


def aggregate(records: list[dict[str, Any]], rankings: list[list[dict[str, Any]]]) -> dict[str, float | int]:
    ranks = [rank_of_target(items, row["sample_id"]) for row, items in zip(records, rankings, strict=True)]
    n = len(ranks)
    return {
        "query_count": n,
        "hit_at_1": sum(rank <= 1 for rank in ranks) / n,
        "hit_at_10": sum(rank <= 10 for rank in ranks) / n,
        "mrr": sum(1.0 / rank for rank in ranks) / n,
        "mean_target_rank": sum(ranks) / n,
    }


def main() -> None:
    args = parse_args()
    if args.seed != DEFAULT_SEED:
        print(f"Note: seed={args.seed} is recorded; selection itself is stream-order based.", flush=True)
    records = crop_records(load_records(args.limit, args.hf_retries), args.work_dir)
    dataset = hv.Dataset(f"precision-regions-eval-{args.limit}", persist=False)
    dataset.add_samples(
        [
            Sample(
                id=row["sample_id"],
                filepath=row["crop_path"],
                label=row["expression"],
                metadata={
                    "question_id": row["question_id"],
                    "source_image_id": row["source_image_id"],
                    "bbox": row["bbox"],
                    "crop_box": row["crop_box"],
                },
            )
            for row in records
        ]
    )
    print(f"Prepared deterministic crop pool: {len(records)} samples", flush=True)
    clip_space, clip_rankings = compute_model_rankings(
        dataset, records, model=CLIP_MODEL, provider="embed-anything"
    )
    hyper_space, hyper_rankings = compute_model_rankings(
        dataset, records, model=HYPER3_MODEL, provider="hyper-models"
    )

    per_query = []
    for index, row in enumerate(records):
        per_query.append(
            {
                **{key: row[key] for key in ("sample_id", "question_id", "expression", "all_answers", "source_image_id", "bbox", "crop_box", "image_size")},
                "models": {
                    "clip": {
                        "target_rank": rank_of_target(clip_rankings[index], row["sample_id"]),
                        "ranking": clip_rankings[index],
                    },
                    "hyper3": {
                        "target_rank": rank_of_target(hyper_rankings[index], row["sample_id"]),
                        "ranking": hyper_rankings[index],
                    },
                },
            }
        )
    output = {
        "benchmark": {
            "dataset": DATASET_ID,
            "split": SPLIT,
            "selection": {
                "rule": "first N records in published streaming order, sorted by numeric question_id",
                "limit": args.limit,
                "seed": args.seed,
            },
            "crop_rule": "bbox x,y,w,h -> floor(x),floor(y),ceil(x+w),ceil(y+h), clamped to image bounds",
            "pool_count": len(records),
            "query_count": len(records),
            "protocol": "precomputed text-to-region ranking over the same evaluation crop pool for both models",
        },
        "models": {
            "clip": {"model": CLIP_MODEL, "provider": "embed-anything", "space_key": clip_space, "metric": "cosine"},
            "hyper3": {"model": HYPER3_MODEL, "provider": "hyper-models", "space_key": hyper_space, "metric": "hyperboloid"},
        },
        "aggregate": {
            "clip": aggregate(records, clip_rankings),
            "hyper3": aggregate(records, hyper_rankings),
        },
        "queries": per_query,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output["aggregate"], indent=2), flush=True)
    print(f"Wrote {args.output}", flush=True)


if __name__ == "__main__":
    main()
