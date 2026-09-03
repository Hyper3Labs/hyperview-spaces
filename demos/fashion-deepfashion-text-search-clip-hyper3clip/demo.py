#!/usr/bin/env python
"""Business-facing DeepFashion text-to-product workspace in HyperView."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

import hyperview as hv

SPACE_DIR = Path(__file__).resolve().parent
SPACE_HOST = os.environ.get("HYPERVIEW_HOST", "127.0.0.1")
SPACE_PORT = int(os.environ.get("HYPERVIEW_PORT", "6265"))
WORKSPACE_ID = os.environ.get(
    "HYPERVIEW_WORKSPACE_ID", "fashion-typed-search-business-evidence-v3"
)
DATASET_NAME = os.environ.get(
    "HYPERVIEW_DATASET_NAME", "deepfashion_text_search_clip_hyper3clip"
)
EXTENSION_DIR = SPACE_DIR / ".hyperview" / "extensions" / "fashion-search-readout"
CASE_FILE = SPACE_DIR / "evidence_cases.json"
DEFAULT_CASE_ID = os.environ.get("FASHION_DEFAULT_EXAMPLE_ID", "light-denim-leggings")
DEFAULT_PHOTO_CASE_ID = "patterned-romper"
EXPECTED_SAMPLE_COUNT = 741
RESULT_SAMPLE_PREFIX = "fashion-evidence-"

# The catalog map is the Hyper3 multimodal space, not the older image-only one.
HYPER3_MODEL = "hyper3-clip-v0.5"
HYPER3_PROVIDER = "hyper-models"

# Build the workspace and exit instead of serving it. This is how a Static
# Space is produced: build, exit, export.
BUILD_ONLY = os.environ.get("HYPERVIEW_BUILD_ONLY", "").lower() in {
    "1",
    "true",
    "yes",
} or "--build-only" in sys.argv[1:]


def load_evidence() -> dict[str, Any]:
    payload = json.loads(CASE_FILE.read_text(encoding="utf-8"))
    projection = {
        "photoBenchmark": payload["photoBenchmark"],
        "photoCases": payload["photoCases"],
    }
    actual = hashlib.sha256(
        json.dumps(projection, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    expected = str(payload["photoArtifact"]["sha256"])
    if actual != expected:
        raise ValueError(
            f"Fashion photo evidence hash mismatch: expected {expected}, computed {actual}"
        )
    return payload


def prepared_sample_ids(payload: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for case in payload["photoCases"]:
        ids.add(str(case["anchorSampleId"]))
        for model in ("hyper3", "clip"):
            ids.update(str(result["sampleId"]) for result in case["results"][model])
    for case in payload["cases"]:
        ids.add(str(case["target"]["sampleId"]))
        for model in ("hyper3", "clip"):
            ids.update(str(result["sampleId"]) for result in case["results"][model])
    return ids


def repair_media_paths(dataset: hv.Dataset) -> None:
    media_dir = SPACE_DIR / "demo_data" / "media" / DATASET_NAME
    repaired: list[hv.Sample] = []
    for sample in dataset.samples:
        if sample.id.startswith(RESULT_SAMPLE_PREFIX):
            continue
        expected = media_dir / f"{sample.id}.jpg"
        if not expected.exists():
            raise RuntimeError(f"Fashion media is missing: {expected}")
        if Path(str(sample.filepath)).expanduser() == expected:
            continue
        repaired.append(
            hv.Sample(
                id=sample.id,
                filepath=str(expected),
                label=sample.label,
                text=sample.text,
                metadata=dict(sample.metadata),
                modality=sample.modality,
            )
        )
    if repaired:
        dataset.add_samples(repaired, skip_existing=False)
        print(f"Repaired {len(repaired)} Fashion media paths.", flush=True)


def resolve_layout_key(dataset: hv.Dataset) -> str:
    """Find the catalog map by describing it rather than pinning its key.

    A layout key carries a content hash of the embedding and projection
    parameters, so it is only knowable after the layout is computed and a
    constant copied into this file goes stale the next time the space is
    rebuilt.
    """

    layout_key = dataset.find_layout(
        model=HYPER3_MODEL,
        provider=HYPER3_PROVIDER,
        modality="multimodal",
        geometry="poincare",
        dimension=2,
    )
    if layout_key is None:
        available = "\n  ".join(record.describe() for record in dataset.list_layouts())
        raise RuntimeError(
            f"Fashion workspace needs a 2D Poincare layout over the {HYPER3_MODEL} "
            f"multimodal space; {dataset.name} has none. Layouts present:\n  "
            + (available or "(none)")
        )
    return layout_key


def validate_dataset(dataset: hv.Dataset, payload: dict[str, Any]) -> str:
    samples = [
        sample for sample in dataset.samples if not sample.id.startswith(RESULT_SAMPLE_PREFIX)
    ]
    if len(samples) != EXPECTED_SAMPLE_COUNT:
        raise RuntimeError(
            f"Fashion workspace requires {EXPECTED_SAMPLE_COUNT} persisted samples; "
            f"found {len(samples)} in {dataset.name}."
        )

    sample_by_id = {sample.id: sample for sample in samples}
    missing_ids = sorted(prepared_sample_ids(payload) - set(sample_by_id))
    if missing_ids:
        raise RuntimeError("Fashion dataset is missing prepared evidence rows: " + ", ".join(missing_ids))

    missing_media = [
        sample.id
        for sample in samples
        if sample.filepath and not Path(str(sample.filepath)).expanduser().exists()
    ]
    if missing_media:
        preview = ", ".join(missing_media[:5])
        raise RuntimeError(f"Fashion dataset has missing local media: {preview}")

    layout_key = resolve_layout_key(dataset)
    layout = next(record for record in dataset.list_layouts() if record.key == layout_key)
    if int(layout.sample_count) != EXPECTED_SAMPLE_COUNT:
        raise RuntimeError(
            f"Fashion layout covers {layout.sample_count} samples, "
            f"expected {EXPECTED_SAMPLE_COUNT}."
        )
    return layout_key


def result_sample_id(mode: str, case_id: str, model: str, rank: int) -> str:
    return f"{RESULT_SAMPLE_PREFIX}{mode}-{case_id}-{model}-{rank:02d}"


def is_same_product(case: dict[str, Any], sample_id: str) -> bool:
    product_key = str(case["target"]["productKey"])
    return sample_id.startswith(f"{product_key}_")


def prepare_result_samples(dataset: hv.Dataset, payload: dict[str, Any]) -> None:
    base_samples = {
        sample.id: sample
        for sample in dataset.samples
        if not sample.id.startswith(RESULT_SAMPLE_PREFIX)
    }
    evidence_samples: list[hv.Sample] = []
    for mode, cases in (("photo", payload["photoCases"]), ("text", payload["cases"])):
        for case in cases:
            case_id = str(case["id"])
            for model in ("hyper3", "clip"):
                for result in case["results"][model]:
                    rank = int(result["rank"])
                    source_id = str(result["sampleId"])
                    source = base_samples[source_id]
                    match = is_same_product(case, source_id)
                    tag = "Same product" if match else "Different product"
                    evidence_samples.append(
                        hv.Sample(
                            id=result_sample_id(mode, case_id, model, rank),
                            filepath=source.filepath,
                            label=f"{tag} · {source.label}",
                            text=source.text,
                            metadata={
                                **dict(source.metadata),
                                "role": "fashion_result_evidence",
                                "source_sample_id": source_id,
                                "same_product": match,
                                "case_id": case_id,
                                "model": model,
                                "rank": rank,
                            },
                            modality=source.modality,
                        )
                    )
    dataset.add_samples(evidence_samples, skip_existing=False)
    print(f"Refreshed {len(evidence_samples)} labelled Fashion result rows.", flush=True)


def readout_props(
    payload: dict[str, Any],
    *,
    collection_ids: dict[str, dict[str, dict[str, str]]],
    collection_id: str | None,
) -> dict[str, Any]:
    def panel_case(mode: str, case: dict[str, Any]) -> dict[str, Any]:
        case_id = str(case["id"])
        return {
            **case,
            "collectionIds": collection_ids[mode][case_id],
            "results": {
                model: [
                    {
                        **result,
                        "sampleId": result_sample_id(
                            mode, case_id, model, int(result["rank"])
                        ),
                    }
                    for result in case["results"][model]
                ]
                for model in ("hyper3", "clip")
            },
        }

    return {
        **payload,
        "photoCases": [panel_case("photo", case) for case in payload["photoCases"]],
        "cases": [panel_case("text", case) for case in payload["cases"]],
        "initialPhotoCaseId": DEFAULT_PHOTO_CASE_ID,
        "initialTextCaseId": DEFAULT_CASE_ID,
        "hyper3SamplesPanelId": "samples",
        "clipSamplesPanelId": "fashion-clip-results",
        "collectionId": collection_id,
        "workspaceSampleCount": EXPECTED_SAMPLE_COUNT,
    }


def build_demo_view(
    payload: dict[str, Any],
    *,
    layout_key: str,
    collection_ids: dict[str, dict[str, dict[str, str]]],
    collection_id: str | None,
) -> hv.ui.View:
    defaults = collection_ids["photo"][DEFAULT_PHOTO_CASE_ID]
    default_photo = next(
        case for case in payload["photoCases"] if str(case["id"]) == DEFAULT_PHOTO_CASE_ID
    )
    hyper3_samples = hv.ui.Samples(
        id="samples",
        title="Hyper3-CLIP · Product matches",
        position="center",
        mode="auto",
        collection_id=defaults["hyper3"],
        anchor_sample_id=default_photo["anchorSampleId"],
        show_text_search=True,
        layout=hv.ui.PanelLayout(min_width=240, min_height=340),
    )
    clip_samples = hv.ui.Samples(
        id="fashion-clip-results",
        title="OpenAI CLIP · Product matches",
        position="center",
        reference_panel_id=hyper3_samples.id,
        direction="right",
        mode="results",
        collection_id=defaults["clip"],
        anchor_sample_id=default_photo["anchorSampleId"],
        layout=hv.ui.PanelLayout(min_width=240, min_height=340),
    )
    catalog_map = hv.ui.Scatter(
        id="fashion-catalog-map",
        title="Catalog similarity map",
        layout_key=layout_key,
        geometry="poincare",
        layout_dimension=2,
        position="center",
        reference_panel_id=hyper3_samples.id,
        direction="within",
        layout=hv.ui.PanelLayout(min_width=240, min_height=300),
    )
    decision = hv.ui.ExtensionPanel(
        id="fashion-search-readout",
        title="Catalog search walkthrough",
        extension="fashion-search-readout",
        panel="fashion-comparison",
        position="right",
        layout=hv.ui.PanelLayout(width=380, min_width=320, max_width=420),
        props=readout_props(
            payload,
            collection_ids=collection_ids,
            collection_id=collection_id,
        ),
        # The panel opens on the photo tab; there is no patch step afterwards.
        state={
            "activeMode": "photo",
            "activePhotoCaseId": DEFAULT_PHOTO_CASE_ID,
            "activeTextCaseId": DEFAULT_CASE_ID,
        },
    )
    return hv.ui.View(
        hv.ui.Horizontal(
            hv.ui.Tabs(
                hyper3_samples,
                catalog_map,
                active_tab=hyper3_samples.id,
            ),
            clip_samples,
            shares=[1, 1],
        ),
        decision,
        active_panel=decision.id,
    )


def ordered_result_ids(mode: str, case: dict[str, Any], model: str) -> list[str]:
    return [
        result_sample_id(mode, str(case["id"]), model, int(result["rank"]))
        for result in sorted(case["results"][model], key=lambda result: int(result["rank"]))
    ]


def materialize_result_collections(
    session: hv.Session,
    payload: dict[str, Any],
) -> dict[str, dict[str, dict[str, str]]]:
    """Store each case's ranked result list as a durable workspace collection."""

    collection_ids: dict[str, dict[str, dict[str, str]]] = {"photo": {}, "text": {}}
    for mode, cases in (("photo", payload["photoCases"]), ("text", payload["cases"])):
        for case in cases:
            case_id = str(case["id"])
            collection_ids[mode][case_id] = {
                model: session.create_collection(
                    ordered_result_ids(mode, case, model),
                    name=(
                        f"{case['label']} · "
                        f"{'Hyper3-CLIP' if model == 'hyper3' else 'OpenAI CLIP'} · Top 6"
                    ),
                    workspace_id=WORKSPACE_ID,
                )
                for model in ("hyper3", "clip")
            }
    return collection_ids


def materialize_case_visuals(session: hv.Session, payload: dict[str, Any]) -> str:
    """One collection holding every tile the readout panel renders itself.

    The panel shows the starting photo of a photo case and the target product
    of a typed case, so it needs those rows loaded without opening the whole
    catalog.
    """

    visual_ids = [str(case["anchorSampleId"]) for case in payload["photoCases"]]
    visual_ids += [str(case["target"]["sampleId"]) for case in payload["cases"]]
    return session.create_collection(
        list(dict.fromkeys(visual_ids)),
        name="Fashion case visuals",
        workspace_id=WORKSPACE_ID,
    )


def launch_demo(dataset: hv.Dataset, payload: dict[str, Any], layout_key: str) -> hv.Session:
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
            layout_key=layout_key,
            collection_ids=collection_ids,
            collection_id=materialize_case_visuals(session, payload),
        ),
        workspace_id=WORKSPACE_ID,
    )
    # The Samples panel already opens on the default case's collection, so the
    # only thing left is to mark the starting photo as selected.
    default_case = next(
        case for case in payload["photoCases"] if case["id"] == DEFAULT_PHOTO_CASE_ID
    )
    session.ui.set_selection([str(default_case["anchorSampleId"])], workspace_id=WORKSPACE_ID)
    print(f"\nHyperView Fashion Products demo is running at {session.url}", flush=True)
    print(
        "   Side-by-side photo matching and shopper-request evidence are ready.",
        flush=True,
    )
    return session


def main() -> None:
    payload = load_evidence()
    dataset = hv.Dataset(DATASET_NAME)
    repair_media_paths(dataset)
    layout_key = validate_dataset(dataset, payload)
    prepare_result_samples(dataset, payload)
    session = launch_demo(dataset, payload, layout_key)
    if BUILD_ONLY:
        print("Workspace built; stopping before serving (build-only).", flush=True)
        return
    session.wait()


if __name__ == "__main__":
    main()
