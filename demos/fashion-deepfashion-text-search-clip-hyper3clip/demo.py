#!/usr/bin/env python
"""Business-facing DeepFashion text-to-product workspace in HyperView."""

from __future__ import annotations

import hashlib
import json
import os
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
DEFAULT_MODEL = "hyper3"
EXPECTED_SAMPLE_COUNT = 741
RESULT_SAMPLE_PREFIX = "fashion-evidence-"
HYPER3_LAYOUT_KEY = (
    "hyper-models__hyper3-clip-v0_5__42052c955756__"
    "poincare_umap__2d_1a6bcbc4"
)


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


def validate_dataset(dataset: hv.Dataset, payload: dict[str, Any]) -> None:
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

    layouts = {layout.layout_key: layout for layout in dataset.list_layouts()}
    layout = layouts.get(HYPER3_LAYOUT_KEY)
    if layout is None:
        raise RuntimeError(f"Required Fashion layout is missing: {HYPER3_LAYOUT_KEY}")
    if int(layout.count) != EXPECTED_SAMPLE_COUNT:
        raise RuntimeError(
            f"Fashion layout covers {layout.count} samples, expected {EXPECTED_SAMPLE_COUNT}."
        )


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
        props={
            "mode": "auto",
            "collectionId": defaults["hyper3"],
            "anchorSampleId": default_photo["anchorSampleId"],
            "showTextSearch": True,
        },
        layout=hv.ui.PanelLayout(min_width=240, min_height=340),
    )
    clip_samples = hv.ui.Samples(
        id="fashion-clip-results",
        title="OpenAI CLIP · Product matches",
        position="center",
        reference_panel_id=hyper3_samples.id,
        direction="right",
        props={"mode": "results", "collectionId": defaults["clip"], "anchorSampleId": default_photo["anchorSampleId"]},
        layout=hv.ui.PanelLayout(min_width=240, min_height=340),
    )
    catalog_map = hv.ui.Scatter(
        id="fashion-catalog-map",
        title="Catalog similarity map",
        layout_key=HYPER3_LAYOUT_KEY,
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
    collection_ids: dict[str, dict[str, dict[str, str]]] = {"photo": {}, "text": {}}
    for mode, cases in (("photo", payload["photoCases"]), ("text", payload["cases"])):
        for case in cases:
            case_id = str(case["id"])
            collection_ids[mode][case_id] = {}
            for model in ("hyper3", "clip"):
                result = session.ui.show_samples(
                    ordered_result_ids(mode, case, model),
                    workspace_id=WORKSPACE_ID,
                    focus=False,
                    source=f"{case['label']} · {'Hyper3-CLIP' if model == 'hyper3' else 'OpenAI CLIP'} · Top 6",
                )
                collection_id = result.get("collection_id")
                if not collection_id:
                    raise RuntimeError(f"HyperView did not return a collection for {mode}/{case_id}/{model}")
                collection_ids[mode][case_id][model] = str(collection_id)
    return collection_ids


def launch_demo(dataset: hv.Dataset, payload: dict[str, Any]) -> hv.Session:
    session = hv.launch(
        dataset,
        host=SPACE_HOST,
        port=SPACE_PORT,
        open_browser=False,
        workspace_id=WORKSPACE_ID,
        block=False,
    )
    print("Installing Fashion search extension...", flush=True)
    session.ui.add_extension(EXTENSION_DIR, workspace_id=WORKSPACE_ID)
    session.ui.reset_samples(workspace_id=WORKSPACE_ID, focus=False)
    samples_state = session.ui.get_panel_state("samples", workspace_id=WORKSPACE_ID)
    collection_id = dict(samples_state.get("state") or {}).get("collection_id")
    collection_ids = materialize_result_collections(session, payload)
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
        "fashion-search-readout",
        {
            "activeMode": "photo",
            "activePhotoCaseId": DEFAULT_PHOTO_CASE_ID,
            "activeTextCaseId": DEFAULT_CASE_ID,
        },
        workspace_id=WORKSPACE_ID,
        replace_state=True,
    )
    default_case = next(case for case in payload["photoCases"] if case["id"] == DEFAULT_PHOTO_CASE_ID)
    session.ui.show_samples(
        ordered_result_ids("photo", default_case, "hyper3"),
        workspace_id=WORKSPACE_ID,
        focus=False,
        source=f"{default_case['label']} · Hyper3-CLIP · Top 6",
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
    validate_dataset(dataset, payload)
    prepare_result_samples(dataset, payload)
    session = launch_demo(dataset, payload)
    session.wait()


if __name__ == "__main__":
    main()
