#!/usr/bin/env python
"""Ledger-backed visual review-queue evidence in HyperView.

Multi-panel workspace for a trust-and-safety review-operations lead:
- native Samples owns Hyper3 and CLIP prepared review queues
- compact extension panel owns scoreboard, threshold rationale, and
  representative disagreement case selection
"""

from __future__ import annotations

import hashlib
import html
import json
import os
from pathlib import Path
from typing import Any

import hyperview as hv

SPACE_DIR = Path(__file__).resolve().parent
SPACE_HOST = os.environ.get("HYPERVIEW_HOST", "127.0.0.1")
SPACE_PORT = int(os.environ.get("HYPERVIEW_PORT", "6275"))
WORKSPACE_ID = os.environ.get("HYPERVIEW_WORKSPACE_ID", "visual-safety-review-queue-evidence-v3")
DATASET_NAME = os.environ.get("HYPERVIEW_DATASET_NAME", "openimages_visual_proxy_evidence_v3")
EXTENSION_DIR = SPACE_DIR / ".hyperview" / "extensions" / "safety-readout"
BENCHMARK_FILE = SPACE_DIR / "benchmark.json"
ASSET_DIR = SPACE_DIR / "demo_assets" / "images"
DEFAULT_CASE_ID = "knife"
HYPER3_SAMPLES_PANEL_ID = "samples"
CLIP_SAMPLES_PANEL_ID = "visual-safety-clip-queue"
AUDIT_PANEL_ID = "visual-safety-readout"

CASE_SPECS = (
    {
        "id": "knife",
        "sample_id": "openimages_000_needs_review_e0c0a275bf9cdbff",
        "label": "Knife",
        "context": "Kitchen and utility blades",
    },
    {
        "id": "alcohol",
        "sample_id": "openimages_001_needs_review_58edc439809229e6",
        "label": "Alcohol",
        "context": "Beer and wine listings",
    },
    {
        "id": "weapon",
        "sample_id": "openimages_083_needs_review_0c4b629e801e8181",
        "label": "Weapon",
        "context": "Handguns and related items",
    },
    {
        "id": "hard-case",
        "sample_id": "openimages_104_needs_review_b053b1f12641af60",
        "label": "Hard case",
        "context": "A subtle wine scene",
    },
)


def load_benchmark() -> dict[str, Any]:
    payload = json.loads(BENCHMARK_FILE.read_text(encoding="utf-8"))
    expected = payload.get("sha256")
    canonical_payload = {key: value for key, value in payload.items() if key != "sha256"}
    actual = hashlib.sha256(
        json.dumps(canonical_payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    if actual != expected:
        raise ValueError(
            f"Visual Safety evidence hash mismatch: expected {expected}, computed {actual}"
        )
    return payload


def image_id(sample_id: str) -> str:
    return sample_id.rsplit("_", 1)[-1]


def review_group(label: str) -> str:
    normalized = label.casefold()
    if normalized in {"knife", "kitchen knife"}:
        return "knife"
    if normalized in {"beer", "wine", "alcoholic beverage"}:
        return "alcohol"
    if normalized in {"weapon", "handgun", "rifle"}:
        return "weapon"
    if normalized in {"cigar", "cigarette"}:
        return "tobacco"
    return normalized


def batch_sample_id(case_id: str, model: str, rank: int) -> str:
    return f"visual-safety-{case_id}-{model}-{rank:02d}"


def evidence_samples(payload: dict[str, Any]) -> list[hv.Sample]:
    samples: list[hv.Sample] = []
    rows_by_id = {str(row["sampleId"]): row for row in payload["ledger"]}
    for row in payload["ledger"]:
        path = ASSET_DIR / f"{image_id(row['sampleId'])}.jpg"
        if not path.exists():
            raise FileNotFoundError(f"Missing Visual Safety evidence image: {path}")
        clip = row["models"]["clip"]
        hyper3 = row["models"]["hyper3"]
        samples.append(
            hv.Sample(
                id=row["sampleId"],
                filepath=str(path),
                label=(
                    "Proxy positive" if row["proxyLabel"] == "proxy_positive" else "Proxy negative"
                ),
                metadata={
                    "proxy_label": row["proxyLabel"],
                    "source_label": row["sourceLabel"],
                    "source_title": html.unescape(row.get("sourceTitle") or ""),
                    "source_url": row["sourceUrl"],
                    "license": row["license"],
                    "evidence_artifact": payload["artifactId"],
                    "clip_queued": bool(clip["queued"]),
                    "hyper3_queued": bool(hyper3["queued"]),
                    "clip_votes": int(clip["positiveVotes"]),
                    "hyper3_votes": int(hyper3["positiveVotes"]),
                },
            )
        )
    for spec in CASE_SPECS:
        anchor = rows_by_id[spec["sample_id"]]
        anchor_group = review_group(str(anchor["sourceLabel"]))
        for model in ("hyper3", "clip"):
            for rank, neighbor_id in enumerate(anchor["models"][model]["neighborIds"], start=1):
                neighbor = rows_by_id[str(neighbor_id)]
                exact_label = str(neighbor["sourceLabel"]).casefold() == str(anchor["sourceLabel"]).casefold()
                if exact_label:
                    tag = "Exact label"
                elif review_group(str(neighbor["sourceLabel"])) == anchor_group:
                    tag = "Related label"
                elif neighbor["proxyLabel"] == "proxy_positive":
                    tag = "Other flagged item"
                else:
                    tag = "Check manually"
                samples.append(
                    hv.Sample(
                        id=batch_sample_id(str(spec["id"]), model, rank),
                        filepath=str(ASSET_DIR / f"{image_id(str(neighbor_id))}.jpg"),
                        label=f"{tag} · {neighbor['sourceLabel']}",
                        metadata={
                            "role": "review_batch_result",
                            "anchor_id": anchor["sampleId"],
                            "source_sample_id": neighbor["sampleId"],
                            "review_tag": tag,
                            "source_label": neighbor["sourceLabel"],
                            "model": model,
                            "rank": rank,
                        },
                    )
                )
    return samples


def prepare_dataset(dataset: hv.Dataset, payload: dict[str, Any]) -> None:
    samples = evidence_samples(payload)
    existing_ids = {sample.id for sample in dataset.samples}
    dataset.add_samples(samples, skip_existing=False)
    added = sum(sample.id not in existing_ids for sample in samples)
    print(
        f"Prepared {len(samples)} Visual Safety evidence samples "
        f"({added} added, {len(samples) - added} refreshed).",
        flush=True,
    )


def panel_cases(
    payload: dict[str, Any],
    *,
    collection_ids: dict[str, dict[str, str]] | None = None,
) -> list[dict[str, Any]]:
    ledger = {str(row["sampleId"]): row for row in payload["ledger"]}
    cases: list[dict[str, Any]] = []
    for spec in CASE_SPECS:
        row = ledger.get(spec["sample_id"])
        if row is None:
            raise ValueError(f"Evidence case is absent from ledger: {spec['sample_id']}")
        anchor_group = review_group(str(row["sourceLabel"]))
        models: dict[str, Any] = {}
        for model in ("hyper3", "clip"):
            neighbors = [ledger[str(sample_id)] for sample_id in row["models"][model]["neighborIds"]]
            same_category = sum(
                str(neighbor["sourceLabel"]).casefold() == str(row["sourceLabel"]).casefold()
                for neighbor in neighbors
            )
            related = sum(
                str(neighbor["sourceLabel"]).casefold() != str(row["sourceLabel"]).casefold()
                and review_group(str(neighbor["sourceLabel"])) == anchor_group
                for neighbor in neighbors
            )
            relevant = sum(neighbor["proxyLabel"] == "proxy_positive" for neighbor in neighbors)
            models[model] = {
                "sameCategory": same_category,
                "relatedCategory": related,
                "otherFlagged": max(0, relevant - same_category - related),
                "manualReview": 7 - relevant,
                "collectionId": (collection_ids or {}).get(str(spec["id"]), {}).get(model),
                "resultIds": [
                    batch_sample_id(str(spec["id"]), model, rank)
                    for rank in range(1, 8)
                ],
            }
        cases.append(
            {
                "id": spec["id"],
                "label": spec["label"],
                "context": spec["context"],
                "sampleId": row["sampleId"],
                "sourceLabel": row["sourceLabel"],
                "sourceTitle": html.unescape(row.get("sourceTitle") or "Untitled source image"),
                "models": models,
            }
        )
    return cases


def materialize_batch_collections(
    session: hv.Session,
    payload: dict[str, Any],
) -> dict[str, dict[str, str]]:
    collection_ids: dict[str, dict[str, str]] = {}
    for spec in CASE_SPECS:
        case_id = str(spec["id"])
        collection_ids[case_id] = {}
        for model in ("hyper3", "clip"):
            ordered_ids = [batch_sample_id(case_id, model, rank) for rank in range(1, 8)]
            result = session.ui.show_samples(
                ordered_ids,
                workspace_id=WORKSPACE_ID,
                focus=False,
                source=f"{spec['label']} review batch · {'Hyper3-CLIP' if model == 'hyper3' else 'OpenAI CLIP'}",
            )
            collection_id = result.get("collection_id")
            if not collection_id:
                raise RuntimeError(f"HyperView did not return a collection for {case_id}/{model}")
            collection_ids[case_id][model] = str(collection_id)
    return collection_ids


def batch_metrics(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    ledger = {str(row["sampleId"]): row for row in payload["ledger"]}
    positives = [row for row in payload["ledger"] if row["proxyLabel"] == "proxy_positive"]
    metrics: dict[str, dict[str, Any]] = {}
    for model in ("hyper3", "clip"):
        relevant = 0
        same_category = 0
        clean_batches = 0
        for anchor in positives:
            neighbors = [ledger[str(sample_id)] for sample_id in anchor["models"][model]["neighborIds"]]
            relevant_count = sum(neighbor["proxyLabel"] == "proxy_positive" for neighbor in neighbors)
            relevant += relevant_count
            same_category += sum(
                str(neighbor["sourceLabel"]).casefold() == str(anchor["sourceLabel"]).casefold()
                for neighbor in neighbors
            )
            clean_batches += relevant_count == 7
        denominator = len(positives) * 7
        metrics[model] = {
            "relevantRate": relevant / denominator,
            "sameCategoryRate": same_category / denominator,
            "cleanBatches": clean_batches,
            "anchorCount": len(positives),
            "auroc": payload["metrics"][model]["auroc"],
            "queued": payload["metrics"][model]["queued"],
            "fp": payload["metrics"][model]["fp"],
            "fn": payload["metrics"][model]["fn"],
            "precision": payload["metrics"][model]["precision"],
            "recall": payload["metrics"][model]["recall"],
            "threshold": payload["metrics"][model]["threshold"],
        }
    return metrics


def readout_props(
    payload: dict[str, Any],
    *,
    collection_ids: dict[str, dict[str, str]],
    collection_id: str | None,
) -> dict[str, Any]:
    return {
        "initialCaseId": DEFAULT_CASE_ID,
        "hyper3SamplesPanelId": HYPER3_SAMPLES_PANEL_ID,
        "clipSamplesPanelId": CLIP_SAMPLES_PANEL_ID,
        "collectionId": collection_id,
        "metrics": batch_metrics(payload),
        "cases": panel_cases(payload, collection_ids=collection_ids),
        "models": {"clip": "OpenAI CLIP", "hyper3": "Hyper3-CLIP v0.5"},
    }


def build_demo_view(
    payload: dict[str, Any],
    *,
    collection_ids: dict[str, dict[str, str]],
    collection_id: str | None,
) -> hv.ui.View:
    default_collections = collection_ids[DEFAULT_CASE_ID]
    hyper3_queue = hv.ui.Samples(
        id=HYPER3_SAMPLES_PANEL_ID,
        title="The batch · Hyper3-CLIP",
        props={
            "mode": "results",
            "collectionId": default_collections["hyper3"],
        },
        layout=hv.ui.PanelLayout(min_width=200, min_height=240),
    )
    clip_queue = hv.ui.Samples(
        id=CLIP_SAMPLES_PANEL_ID,
        title="The batch · OpenAI CLIP",
        props={
            "mode": "results",
            "collectionId": default_collections["clip"],
        },
        layout=hv.ui.PanelLayout(min_width=200, min_height=240),
    )
    audit = hv.ui.ExtensionPanel(
        id=AUDIT_PANEL_ID,
        title="Review batch walkthrough",
        extension="safety-readout",
        panel="safety-comparison",
        position="right",
        layout=hv.ui.PanelLayout(
            width=400,
            min_width=320,
            max_width=520,
            min_height=260,
        ),
        props=readout_props(
            payload,
            collection_ids=collection_ids,
            collection_id=collection_id,
        ),
    )
    return hv.ui.View(
        hv.ui.Horizontal(hyper3_queue, clip_queue, shares=[1, 1]),
        audit,
        active_panel=AUDIT_PANEL_ID,
    )


def launch_demo(dataset: hv.Dataset, payload: dict[str, Any]) -> hv.Session:
    session = hv.launch(
        dataset,
        host=SPACE_HOST,
        port=SPACE_PORT,
        open_browser=False,
        workspace_id=WORKSPACE_ID,
        block=False,
    )
    print("Installing Visual Safety evidence extension...", flush=True)
    session.ui.add_extension(EXTENSION_DIR, workspace_id=WORKSPACE_ID)
    session.ui.reset_samples(workspace_id=WORKSPACE_ID, focus=False)
    samples_state = session.ui.get_panel_state("samples", workspace_id=WORKSPACE_ID)
    collection_id = dict(samples_state.get("state") or {}).get("collection_id")
    print("Materializing review batches...", flush=True)
    collection_ids = materialize_batch_collections(session, payload)
    session.ui.reset_samples(workspace_id=WORKSPACE_ID, focus=False)
    session.ui.apply_view(
        build_demo_view(
            payload,
            collection_ids=collection_ids,
            collection_id=str(collection_id) if collection_id else None,
        ),
        workspace_id=WORKSPACE_ID,
    )
    session.ui.patch_panel_state(
        AUDIT_PANEL_ID,
        {"activeCaseId": DEFAULT_CASE_ID},
        workspace_id=WORKSPACE_ID,
        replace_state=True,
    )
    session.ui.show_samples(
        [batch_sample_id(DEFAULT_CASE_ID, "hyper3", rank) for rank in range(1, 8)],
        workspace_id=WORKSPACE_ID,
        focus=False,
        source="Knife · Hyper3-CLIP review batch",
    )
    session.ui.set_selection([CASE_SPECS[0]["sample_id"]], workspace_id=WORKSPACE_ID)
    print(f"\nHyperView Visual Safety demo is running at {session.url}", flush=True)
    print(
        "   Two review batches and the workflow walkthrough are ready.",
        flush=True,
    )
    return session


def main() -> None:
    payload = load_benchmark()
    dataset = hv.Dataset(DATASET_NAME)
    prepare_dataset(dataset, payload)
    launch_demo(dataset, payload).wait()


if __name__ == "__main__":
    main()
