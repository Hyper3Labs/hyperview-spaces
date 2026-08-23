#!/usr/bin/env python
"""RESISC45 aerial neighbourhood audit workspace for archive / imagery QA leads.

Answers:
1. From an anchor tile, do retrieved neighbours preserve land-use identity and
   avoid operationally costly confusions?
2. Do Hyper3-CLIP and CLIP organize the 60-tile archive into coherent,
   inspectable topology (outliers and drift)?
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import hyperview as hv

SPACE_DIR = Path(__file__).resolve().parent
SPACE_HOST = os.environ.get("HYPERVIEW_HOST", "127.0.0.1")
SPACE_PORT = int(os.environ.get("HYPERVIEW_PORT", "6264"))
WORKSPACE_ID = os.environ.get(
    "HYPERVIEW_WORKSPACE_ID", "geospatial-resisc45-retrieval-evidence-v2"
)
DATASET_NAME = os.environ.get(
    "HYPERVIEW_DATASET_NAME", "resisc45_clip_hyper3clip_curated_side_by_side"
)
EXTENSION_DIR = SPACE_DIR / ".hyperview" / "extensions" / "geospatial-readout"
EVIDENCE_FILE = SPACE_DIR / "evidence_cases.json"
DEFAULT_CASE_ID = os.environ.get("GEOSPATIAL_DEFAULT_CASE_ID", "airplane-win")
EXPECTED_SAMPLE_COUNT = 60
NEIGHBOUR_K = 10

# Explicit layouts matching the versioned evidence embedding spaces.
HYPER3_SPACE_KEY = "hyper-models__hyper3-clip-v0_5__42052c955756"
CLIP_SPACE_KEY = "embed-anything__openai_clip-vit-base-patch32__8da42c3ae90c"
HYPER3_LAYOUT_KEY = (
    f"{HYPER3_SPACE_KEY}__poincare_umap__2d_1a6bcbc4"
)
CLIP_LAYOUT_KEY = (
    f"{CLIP_SPACE_KEY}__euclidean_umap__2d_1a6bcbc4"
)

HYPER3_SAMPLES_ID = "hyper3-neighbours"
CLIP_SAMPLES_ID = "clip-neighbours"
HYPER3_SCATTER_ID = "hyper3-map"
CLIP_SCATTER_ID = "clip-map"
READOUT_ID = "geospatial-retrieval-readout"

CASE_CONSEQUENCES: dict[str, dict[str, str]] = {
    "airplane-win": {
        "hyper3": (
            "Transport-family neighbours dominate; aircraft and airfield "
            "infrastructure stay together for follow-up review."
        ),
        "clip": (
            "Exact aircraft hits collapse; residential and meadow tiles enter "
            "the shortlist and raise false-positive cost."
        ),
        "comparison": (
            "Hyper3 keeps the operational transport cluster; CLIP drifts into "
            "unrelated land use that would waste analyst time."
        ),
    },
    "forest-win": {
        "hyper3": (
            "Vegetation stays coherent: forest plus meadow/farmland parents "
            "with minimal residential leakage."
        ),
        "clip": (
            "Half the neighbourhood leaves the vegetation parent; sparse "
            "residential tiles create costly confusions."
        ),
        "comparison": (
            "Hyper3 is safer for vegetation-identity QA; CLIP pulls built "
            "environment into the forest neighbourhood."
        ),
    },
    "storage-tank-win": {
        "hyper3": (
            "All four available same-class tank tiles are recovered; circular "
            "farmland still occupies the remaining shortlist positions."
        ),
        "clip": (
            "Circular farmland competes with tanks early; industrial identity "
            "is harder to trust from the shortlist alone."
        ),
        "comparison": (
            "Both confuse tanks with circular farmland, but Hyper3 recovers "
            "more exact industrial matches before drift."
        ),
    },
    "airport-regression": {
        "hyper3": (
            "Exact and parent transport hits drop; rectangular farmland "
            "enters the neighbourhood earlier than desired."
        ),
        "clip": (
            "Stronger exact airport hits and broader transport-parent "
            "coverage on this prepared probe."
        ),
        "comparison": (
            "Explicit regression: CLIP wins exact and parent quality here; "
            "use it to pressure-test Hyper3 airfield topology."
        ),
    },
}


def load_evidence() -> dict[str, Any]:
    return json.loads(EVIDENCE_FILE.read_text(encoding="utf-8"))


def model_counts(model: dict[str, Any]) -> dict[str, int]:
    exact = int(model["exactHits"])
    parent = int(model["parentHits"])
    return {
        "exactHits": exact,
        "parentHits": parent,
        "offGroupHits": max(0, NEIGHBOUR_K - parent),
    }


def prepare_cases(payload: dict[str, Any]) -> list[dict[str, Any]]:
    prepared: list[dict[str, Any]] = []
    for case in payload["cases"]:
        case_id = str(case["id"])
        consequences = CASE_CONSEQUENCES.get(case_id, {})
        models: dict[str, Any] = {}
        for model_key in ("hyper3", "clip"):
            source = case["models"][model_key]
            counts = model_counts(source)
            models[model_key] = {
                "spaceKey": source["spaceKey"],
                "layoutKey": (
                    HYPER3_LAYOUT_KEY if model_key == "hyper3" else CLIP_LAYOUT_KEY
                ),
                **counts,
                "resultIds": list(source["resultIds"]),
                "consequence": consequences.get(model_key, ""),
            }
        prepared.append(
            {
                "id": case_id,
                "title": case["title"],
                "kind": case["kind"],
                "question": case["question"],
                "anchorSampleId": case["anchorSampleId"],
                "exactClass": case["exactClass"],
                "parentGroup": case["parentGroup"],
                "sourceImageId": case["sourceImageId"],
                "comparison": consequences.get("comparison", ""),
                "models": models,
            }
        )
    return prepared


def require_prepared_dataset(payload: dict[str, Any]) -> hv.Dataset:
    dataset = hv.Dataset(DATASET_NAME)
    media_dir = SPACE_DIR / "demo_data" / "media" / DATASET_NAME
    repaired: list[hv.Sample] = []
    for sample in dataset.samples:
        expected = media_dir / f"{sample.id}.jpg"
        if not expected.exists():
            raise RuntimeError(f"GeoSpatial media is missing: {expected}")
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
        print(f"Repaired {len(repaired)} GeoSpatial media paths.", flush=True)
    samples = list(dataset.samples)
    if len(samples) != EXPECTED_SAMPLE_COUNT:
        raise RuntimeError(
            f"Dataset {DATASET_NAME!r} must contain {EXPECTED_SAMPLE_COUNT} "
            f"evidence rows; found {len(samples)}."
        )

    sample_ids = {sample.id for sample in samples}
    required_ids = {
        case["anchorSampleId"]
        for case in payload["cases"]
    }
    required_ids.update(
        sample_id
        for case in payload["cases"]
        for model in case["models"].values()
        for sample_id in model["resultIds"]
    )
    missing_samples = sorted(required_ids - sample_ids)
    if missing_samples:
        raise RuntimeError(
            f"Dataset {DATASET_NAME!r} is missing {len(missing_samples)} prepared "
            "evidence samples. Prepare the RESISC45 evidence dataset before launching."
        )

    space_keys = {space.space_key for space in dataset.list_spaces()}
    required_spaces = {
        model["spaceKey"]
        for case in payload["cases"]
        for model in case["models"].values()
    }
    required_spaces.update({HYPER3_SPACE_KEY, CLIP_SPACE_KEY})
    missing_spaces = sorted(required_spaces - space_keys)
    if missing_spaces:
        raise RuntimeError(
            "The versioned evidence requires prepared embedding spaces that are not "
            f"present in {DATASET_NAME!r}: {', '.join(missing_spaces)}"
        )

    layouts = {layout.layout_key: layout for layout in dataset.list_layouts()}
    for layout_key, space_key, geometry in (
        (HYPER3_LAYOUT_KEY, HYPER3_SPACE_KEY, "poincare"),
        (CLIP_LAYOUT_KEY, CLIP_SPACE_KEY, "euclidean"),
    ):
        layout = layouts.get(layout_key)
        if layout is None:
            raise RuntimeError(
                f"Required layout {layout_key!r} is missing from {DATASET_NAME!r}."
            )
        if layout.space_key != space_key:
            raise RuntimeError(
                f"Layout {layout_key!r} is bound to {layout.space_key!r}, "
                f"expected {space_key!r}."
            )
        if getattr(layout, "geometry", None) != geometry:
            raise RuntimeError(
                f"Layout {layout_key!r} geometry is "
                f"{getattr(layout, 'geometry', None)!r}, expected {geometry!r}."
            )
        if int(layout.count) != EXPECTED_SAMPLE_COUNT:
            raise RuntimeError(
                f"Layout {layout_key!r} covers {layout.count} samples, "
                f"expected {EXPECTED_SAMPLE_COUNT}."
            )

    return dataset


def ranked_samples_props(
    *,
    layout_key: str,
    anchor_sample_id: str,
    model_label: str,
) -> dict[str, Any]:
    return {
        "mode": "ranked",
        "rank": {
            "anchorSampleId": anchor_sample_id,
            "layoutKey": layout_key,
            "k": NEIGHBOUR_K,
            "source": f"{model_label} · aerial neighbours",
            "showDistance": False,
        },
    }


def panel_props(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifactId": payload["artifactId"],
        "protocol": payload["protocol"],
        "aggregate": payload["aggregate"],
        "models": {
            "hyper3": "Hyper3-CLIP v0.5",
            "clip": "OpenAI CLIP ViT-B/32",
        },
        "layouts": {
            "hyper3": {
                "layoutKey": HYPER3_LAYOUT_KEY,
                "spaceKey": HYPER3_SPACE_KEY,
                "geometry": "poincare",
                "title": "Hyper3 multimodal topology",
            },
            "clip": {
                "layoutKey": CLIP_LAYOUT_KEY,
                "spaceKey": CLIP_SPACE_KEY,
                "geometry": "euclidean",
                "title": "CLIP multimodal topology",
            },
        },
        "panelIds": {
            "hyper3Samples": HYPER3_SAMPLES_ID,
            "clipSamples": CLIP_SAMPLES_ID,
            "hyper3Scatter": HYPER3_SCATTER_ID,
            "clipScatter": CLIP_SCATTER_ID,
        },
        "neighbourK": NEIGHBOUR_K,
        "workspaceSampleCount": EXPECTED_SAMPLE_COUNT,
        "initialCaseId": DEFAULT_CASE_ID,
        "cases": prepare_cases(payload),
        "businessQuestions": [
            (
                "From an anchor tile, do retrieved neighbours preserve land-use "
                "identity and avoid operationally costly confusions?"
            ),
            (
                "Do the two embedding models organize the full archive into "
                "coherent, inspectable topology, outliers, and drift?"
            ),
        ],
    }


def build_demo_view(payload: dict[str, Any]) -> hv.ui.View:
    cases = prepare_cases(payload)
    default_case = next(
        (case for case in cases if case["id"] == DEFAULT_CASE_ID),
        cases[0],
    )
    anchor = str(default_case["anchorSampleId"])

    hyper3_samples = hv.ui.Samples(
        id=HYPER3_SAMPLES_ID,
        title="Hyper3-CLIP · Ranked neighbours",
        position="center",
        props=ranked_samples_props(
            layout_key=HYPER3_LAYOUT_KEY,
            anchor_sample_id=anchor,
            model_label="Hyper3-CLIP v0.5",
        ),
        layout=hv.ui.PanelLayout(min_width=220, min_height=240),
    )
    clip_samples = hv.ui.Samples(
        id=CLIP_SAMPLES_ID,
        title="CLIP B/32 · Ranked neighbours",
        position="center",
        reference_panel_id=HYPER3_SAMPLES_ID,
        direction="right",
        props=ranked_samples_props(
            layout_key=CLIP_LAYOUT_KEY,
            anchor_sample_id=anchor,
            model_label="OpenAI CLIP ViT-B/32",
        ),
        layout=hv.ui.PanelLayout(min_width=220, min_height=240),
    )
    hyper3_scatter = hv.ui.Scatter(
        id=HYPER3_SCATTER_ID,
        title="Archive topology · Hyper3 multimodal",
        layout_key=HYPER3_LAYOUT_KEY,
        geometry="poincare",
        layout_dimension=2,
        position="center",
        reference_panel_id=HYPER3_SAMPLES_ID,
        direction="within",
        layout=hv.ui.PanelLayout(min_width=220, min_height=240),
    )
    clip_scatter = hv.ui.Scatter(
        id=CLIP_SCATTER_ID,
        title="Archive topology · CLIP multimodal",
        layout_key=CLIP_LAYOUT_KEY,
        geometry="euclidean",
        layout_dimension=2,
        position="center",
        reference_panel_id=CLIP_SAMPLES_ID,
        direction="within",
        layout=hv.ui.PanelLayout(min_width=220, min_height=240),
    )
    audit = hv.ui.ExtensionPanel(
        id=READOUT_ID,
        title="Aerial identity audit",
        extension="geospatial-readout",
        panel="geospatial-comparison",
        position="right",
        layout=hv.ui.PanelLayout(width=380, min_width=360, max_width=410),
        props=panel_props(payload),
    )
    return hv.ui.View(
        hv.ui.Horizontal(
            hv.ui.Tabs(
                hyper3_samples,
                hyper3_scatter,
                active_tab=hyper3_samples.id,
            ),
            hv.ui.Tabs(
                clip_samples,
                clip_scatter,
                active_tab=clip_samples.id,
            ),
            shares=[1, 1],
        ),
        audit,
        active_panel=audit.id,
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
    print("Installing GeoSpatial aerial audit extension...", flush=True)
    session.ui.add_extension(EXTENSION_DIR, workspace_id=WORKSPACE_ID)
    session.ui.apply_view(build_demo_view(payload), workspace_id=WORKSPACE_ID)
    session.ui.patch_panel_state(
        READOUT_ID,
        {"activeCaseId": DEFAULT_CASE_ID},
        workspace_id=WORKSPACE_ID,
        replace_state=True,
    )
    default_case = next(
        (case for case in payload["cases"] if case["id"] == DEFAULT_CASE_ID),
        payload["cases"][0],
    )
    session.ui.set_selection(
        [default_case["anchorSampleId"]], workspace_id=WORKSPACE_ID
    )
    session.ui.set_active_layout(HYPER3_LAYOUT_KEY, workspace_id=WORKSPACE_ID)
    print(f"\nHyperView GeoSpatial demo is running at {session.url}", flush=True)
    print(
        "   Dual ranked Samples + dual topology maps + right-side aerial identity audit.",
        flush=True,
    )
    return session


def main() -> None:
    payload = load_evidence()
    dataset = require_prepared_dataset(payload)
    launch_demo(dataset, payload).wait()


if __name__ == "__main__":
    main()
