#!/usr/bin/env python
"""Materialize the bounded visual proxy review-queue evidence ledger."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import hyperview as hv

DATASET_NAME = "openimages_visual_safety_marketplace_triage_assets_v1"
NEIGHBORS = 7
QUEUE_VOTES = 5
SPACE_KEYS = {
    "clip": "embed-anything__openai_clip-vit-base-patch32__8da42c3ae90c",
    "hyper3": "hyper-models__hyper3-clip-v0_5__42052c955756",
}


def average_precision(labels: list[int], scores: list[float]) -> float:
    positives = sum(labels)
    if not positives:
        return 0.0
    grouped: dict[float, list[int]] = {}
    for score, label in zip(scores, labels, strict=True):
        grouped.setdefault(score, []).append(label)
    tp = 0
    fp = 0
    previous_recall = 0.0
    result = 0.0
    for score in sorted(grouped, reverse=True):
        group = grouped[score]
        tp += sum(group)
        fp += len(group) - sum(group)
        recall = tp / positives
        precision = tp / (tp + fp)
        result += (recall - previous_recall) * precision
        previous_recall = recall
    return result


def auroc(labels: list[int], scores: list[float]) -> float:
    positive = [score for score, label in zip(scores, labels, strict=True) if label]
    negative = [score for score, label in zip(scores, labels, strict=True) if not label]
    wins = sum(
        1.0 if pos > neg else 0.5 if pos == neg else 0.0
        for pos in positive
        for neg in negative
    )
    return wins / (len(positive) * len(negative))


def model_metrics(rows: list[dict[str, Any]], model: str) -> dict[str, Any]:
    labels = [int(row["proxyLabel"] == "proxy_positive") for row in rows]
    scores = [float(row["models"][model]["score"]) for row in rows]
    decisions = [bool(row["models"][model]["queued"]) for row in rows]
    tp = sum(label and decision for label, decision in zip(labels, decisions, strict=True))
    fp = sum(not label and decision for label, decision in zip(labels, decisions, strict=True))
    fn = sum(label and not decision for label, decision in zip(labels, decisions, strict=True))
    tn = sum(not label and not decision for label, decision in zip(labels, decisions, strict=True))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {
        "threshold": f"at least {QUEUE_VOTES} of {NEIGHBORS} positive neighbours",
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "queued": tp + fp,
        "queueRate": (tp + fp) / len(rows),
        "precision": precision,
        "recall": recall,
        "auroc": auroc(labels, scores),
        "averagePrecision": average_precision(labels, scores),
    }


def build_ledger(dataset: hv.Dataset) -> list[dict[str, Any]]:
    label_by_id = {
        sample.id: int(sample.label == "needs_review") for sample in dataset.samples
    }
    rows: list[dict[str, Any]] = []
    for sample in dataset.samples:
        row: dict[str, Any] = {
            "sampleId": sample.id,
            "proxyLabel": (
                "proxy_positive" if label_by_id[sample.id] else "proxy_negative"
            ),
            "sourceLabel": sample.metadata.get("primary_label"),
            "sourceTitle": sample.metadata.get("title"),
            "sourceUrl": sample.metadata.get("source_url"),
            "license": sample.metadata.get("license"),
            "models": {},
        }
        for model, space_key in SPACE_KEYS.items():
            neighbors = dataset.find_similar(
                sample.id, k=NEIGHBORS, space_key=space_key
            )
            positive_votes = sum(label_by_id[result.id] for result, _ in neighbors)
            row["models"][model] = {
                "spaceKey": space_key,
                "positiveVotes": positive_votes,
                "score": positive_votes / NEIGHBORS,
                "queued": positive_votes >= QUEUE_VOTES,
                "neighborIds": [result.id for result, _ in neighbors],
            }
        rows.append(row)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    dataset = hv.Dataset(DATASET_NAME)
    rows = build_ledger(dataset)
    payload: dict[str, Any] = {
        "schemaVersion": 1,
        "artifactId": "openimages-visual-proxy-knn-ledger-2026-07-22",
        "protocol": {
            "dataset": "Open Images V7 validation",
            "subset": "120 curated public images; 60 proxy-positive and 60 proxy-negative",
            "proxyPositiveLabels": [
                "Alcoholic beverage",
                "Beer",
                "Cigar",
                "Cigarette",
                "Handgun",
                "Kitchen knife",
                "Knife",
                "Rifle",
                "Weapon",
                "Wine",
            ],
            "method": "leave-one-out 7-nearest-neighbour vote in each persisted image-embedding space",
            "operatingPoint": "queue when at least 5 of 7 neighbours are proxy-positive",
            "thresholdRationale": "The same fixed supermajority rule is applied to both models; no threshold was fit to maximize a metric.",
            "claimBoundary": "Object-label proxy only; not a production content-policy classifier or prevalence estimate.",
            "models": {
                "clip": "openai/clip-vit-base-patch32",
                "hyper3": "hyper3-clip-v0.5",
            },
        },
        "metrics": {},
        "ledger": rows,
    }
    payload["metrics"] = {
        model: model_metrics(rows, model) for model in ("clip", "hyper3")
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    payload["sha256"] = hashlib.sha256(canonical).hexdigest()
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "out": str(args.out),
                "sha256": payload["sha256"],
                "metrics": payload["metrics"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
