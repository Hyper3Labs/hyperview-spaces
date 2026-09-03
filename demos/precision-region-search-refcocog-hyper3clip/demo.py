#!/usr/bin/env python
"""Business-facing RefCOCOg text-to-region retrieval evidence in HyperView."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import hyperview as hv

SPACE_DIR = Path(__file__).resolve().parent
SPACE_HOST = os.environ.get("HYPERVIEW_HOST", "127.0.0.1")
SPACE_PORT = int(os.environ.get("HYPERVIEW_PORT", "6267"))
WORKSPACE_ID = os.environ.get(
    "HYPERVIEW_WORKSPACE_ID", "precision-region-search-business-evidence-v3"
)
DATASET_NAME = os.environ.get("HYPERVIEW_DATASET_NAME", "refcocog_text_region_evidence_v3")
EXTENSION_DIR = SPACE_DIR / ".hyperview" / "extensions" / "precision-region-readout"
CASE_FILE = SPACE_DIR / "evidence_cases.json"
ASSET_DIR = SPACE_DIR / "demo_assets" / "evidence"
DEFAULT_CASE_ID = os.environ.get("PRECISION_REGION_DEFAULT_CASE_ID", "facilities")

# Build the workspace and exit instead of serving it. This is how a Static
# Space is produced: build, exit, export.
BUILD_ONLY = os.environ.get("HYPERVIEW_BUILD_ONLY", "").lower() in {
    "1",
    "true",
    "yes",
} or "--build-only" in sys.argv[1:]


def load_cases() -> dict[str, Any]:
    return json.loads(CASE_FILE.read_text(encoding="utf-8"))


def source_sample_id(case_id: str) -> str:
    return f"precision-{case_id}-source"


def target_sample_id(case_id: str) -> str:
    return f"precision-{case_id}-target"


def result_sample_id(case_id: str, model: str, rank: int) -> str:
    return f"precision-{case_id}-{model}-{rank:02d}"


def evidence_samples(payload: dict[str, Any]) -> list[hv.Sample]:
    samples: list[hv.Sample] = []
    shared_provenance = {
        "source_dataset": payload["dataset"],
        "split": payload["split"],
        "evaluation_protocol": payload["protocol"],
        "hyper3_model": payload["models"]["hyper3"],
        "baseline_model": payload["models"]["clip"],
    }
    for case in payload["cases"]:
        case_id = str(case["id"])
        case_dir = ASSET_DIR / case_id
        shared_case = {
            **shared_provenance,
            "case_id": case_id,
            "operational_slice": case["label"],
            "text_query": case["query"],
            "business_question": case["business"],
        }
        samples.extend(
            [
                hv.Sample(
                    id=source_sample_id(case_id),
                    filepath=str(case_dir / "target_full.jpg"),
                    label=f"{case['shortLabel']} source scene",
                    metadata={**shared_case, "role": "source_scene"},
                ),
                hv.Sample(
                    id=target_sample_id(case_id),
                    filepath=str(case_dir / "target_crop.jpg"),
                    label=f"TARGET · {case['query']}",
                    metadata={
                        **shared_case,
                        "role": "ground_truth_region",
                        "is_target": True,
                        "hyper3_rank": case["target"]["hyper3Rank"],
                        "clip_rank": case["target"]["clipRank"],
                    },
                ),
            ]
        )
        for model in ("hyper3", "clip"):
            for result in case["results"][model]:
                # The ground-truth crop is one canonical sample, added above.
                # Reusing its id in ranked collections keeps selection and
                # inspection tied to the tile the user can actually see, so
                # every sample built here is a non-target result.
                if bool(result.get("isTarget")):
                    continue
                rank = int(result["rank"])
                samples.append(
                    hv.Sample(
                        id=result_sample_id(case_id, model, rank),
                        filepath=str(case_dir / f"{model}_{rank}.jpg"),
                        label=f"#{rank} · {result['text']}",
                        metadata={
                            **shared_case,
                            "role": "ranked_region_result",
                            "model": payload["models"][model],
                            "model_key": model,
                            "rank": rank,
                            "is_target": False,
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
        f"Prepared {len(samples)} Precision Regions evidence samples "
        f"({added} added, {len(samples) - added} refreshed).",
        flush=True,
    )


def panel_cases(
    payload: dict[str, Any],
    *,
    collection_ids: dict[str, dict[str, str]] | None = None,
) -> list[dict[str, Any]]:
    prepared: list[dict[str, Any]] = []
    for case in payload["cases"]:
        case_id = str(case["id"])
        prepared.append(
            {
                **case,
                "sourceSampleId": source_sample_id(case_id),
                "targetSampleId": target_sample_id(case_id),
                "collectionIds": dict((collection_ids or {}).get(case_id) or {}),
                "results": {
                    model: [
                        {
                            **result,
                            "sampleId": (
                                target_sample_id(case_id)
                                if bool(result.get("isTarget"))
                                else result_sample_id(case_id, model, int(result["rank"]))
                            ),
                        }
                        for result in case["results"][model]
                    ]
                    for model in ("hyper3", "clip")
                },
            }
        )
    return prepared


def readout_props(
    payload: dict[str, Any],
    *,
    collection_id: str | None = None,
    collection_ids: dict[str, dict[str, str]] | None = None,
) -> dict[str, Any]:
    return {
        "dataset": payload["dataset"],
        "split": payload["split"],
        "protocol": payload["protocol"],
        "models": payload["models"],
        "benchmark": payload["benchmark"],
        "initialCaseId": DEFAULT_CASE_ID,
        "cases": panel_cases(payload, collection_ids=collection_ids),
        "collectionId": collection_id,
    }


def build_demo_view(
    payload: dict[str, Any],
    *,
    collection_id: str | None,
    collection_ids: dict[str, dict[str, str]],
) -> hv.ui.View:
    default_collections = collection_ids[DEFAULT_CASE_ID]
    readout = hv.ui.ExtensionPanel(
        id="precision-region-readout",
        title="Find the exact region",
        extension="precision-region-readout",
        panel="precision-region-comparison",
        position="right",
        layout=hv.ui.PanelLayout(
            width=400,
            min_width=320,
            max_width=520,
            min_height=300,
        ),
        props=readout_props(
            payload,
            collection_id=collection_id,
            collection_ids=collection_ids,
        ),
        # The panel opens on the default case; there is no patch step after.
        state={"activeCaseId": DEFAULT_CASE_ID},
    )
    hyper3_results = hv.ui.Samples(
        id="samples",
        title="Hyper3-CLIP · Top 5 regions",
        position="center",
        mode="results",
        collection_id=default_collections["hyper3"],
        layout=hv.ui.PanelLayout(min_width=180, min_height=220),
    )
    clip_results = hv.ui.Samples(
        id="precision-clip-results",
        title="OpenAI CLIP · Top 5 regions",
        position="center",
        reference_panel_id=hyper3_results.id,
        direction="right",
        mode="results",
        collection_id=default_collections["clip"],
        layout=hv.ui.PanelLayout(min_width=180, min_height=220),
    )
    return hv.ui.View(
        hyper3_results,
        clip_results,
        readout,
        active_panel="samples",
    )


def ordered_result_ids(case: dict[str, Any], model: str) -> list[str]:
    """The model's result sample ids for one case, best rank first."""

    return [
        str(result["sampleId"])
        for result in sorted(case["results"][model], key=lambda result: int(result["rank"]))
    ]


def materialize_result_collections(
    session: hv.Session,
    payload: dict[str, Any],
) -> dict[str, dict[str, str]]:
    """Store each case's ranked region list as a durable workspace collection."""

    collection_ids: dict[str, dict[str, str]] = {}
    for case in panel_cases(payload):
        collection_ids[str(case["id"])] = {
            model: session.create_collection(
                ordered_result_ids(case, model),
                name=f"{case['shortLabel']} · {payload['models'][model]} · Top 5",
                workspace_id=WORKSPACE_ID,
            )
            for model in ("hyper3", "clip")
        }
    return collection_ids


def launch_demo(dataset: hv.Dataset, payload: dict[str, Any]) -> hv.Session:
    session = hv.launch(
        dataset,
        host=SPACE_HOST,
        port=SPACE_PORT,
        open_browser=False,
        workspace_id=WORKSPACE_ID,
        block=False,
        extensions=[EXTENSION_DIR],
    )
    collection_ids = materialize_result_collections(session, payload)
    session.ui.apply_view(
        build_demo_view(
            payload,
            # Bind the authored default explicitly. Static exports reconstruct
            # the panel from view props, so using the transient all-items
            # collection here makes the Static Space open on the full dataset.
            collection_id=collection_ids[DEFAULT_CASE_ID]["hyper3"],
            collection_ids=collection_ids,
        ),
        workspace_id=WORKSPACE_ID,
    )
    session.ui.set_selection([target_sample_id(DEFAULT_CASE_ID)], workspace_id=WORKSPACE_ID)
    print(f"\nHyperView Precision Regions demo is running at {session.url}", flush=True)
    print("   Text-to-region examples and the full benchmark are ready.", flush=True)
    return session


def main() -> None:
    payload = load_cases()
    dataset = hv.Dataset(DATASET_NAME)
    prepare_dataset(dataset, payload)
    session = launch_demo(dataset, payload)
    if BUILD_ONLY:
        print("Workspace built; stopping before serving (build-only).", flush=True)
        return
    session.wait()


if __name__ == "__main__":
    main()
