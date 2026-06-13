#!/usr/bin/env python
"""RefCOCOg same-scene crop ranking demo for CLIP vs Hyper3-CLIP."""

from __future__ import annotations

import json
import math
import os
import re
from pathlib import Path
from typing import Any

import numpy as np

import hyperview as hv
from hyperview.core.sample import Sample
from hyperview.storage.schema import make_layout_key

SPACE_DIR = Path(__file__).resolve().parent
SPACE_HOST = os.environ.get("HYPERVIEW_HOST", "127.0.0.1")
SPACE_PORT = int(os.environ.get("HYPERVIEW_PORT", "6267"))
WORKSPACE_ID = os.environ.get("HYPERVIEW_WORKSPACE_ID", "precision-region-search-refcocog-hyper3clip")
DATASET_NAME = os.environ.get("HYPERVIEW_DATASET_NAME", "refcocog_same_scene_ranked_crops_hyper3clip")
EXTENSION_DIR = SPACE_DIR / ".hyperview" / "extensions" / "precision-region-readout"
CASE_FILE = SPACE_DIR / "ranked_cases.json"

DEFAULT_CASE_ID = os.environ.get("PRECISION_REGION_DEFAULT_CASE_ID", "facilities")

MODEL_LAYOUT_SPECS = {
    "hyper3": {
        "space_key": "hyper3_clip_ranked_crop_distance",
        "layout_title": "Hyper3-CLIP Poincare Crop Distance",
        "display_name": "Hyper3-CLIP",
        "rank_panel_id": "ranked-hyper3",
        "rank_panel_title": "Hyper3-CLIP Ranked Crops",
        "map_panel_id": "precision-map-hyper3",
        "map_panel_title": "Hyper3-CLIP Poincare Rank Map",
        "model_id": "hyper3-clip-v0.5/same-scene-crop-distance",
        "space_geometry": "hyperboloid",
        "layout_geometry": "poincare",
        "rank_key": "hyper3Rank",
        "accent": "#7dd3fc",
    },
    "clip": {
        "space_key": "clip_b32_ranked_crop_distance",
        "layout_title": "CLIP B/32 Euclidean Crop Distance",
        "display_name": "CLIP B/32",
        "rank_panel_id": "ranked-clip",
        "rank_panel_title": "CLIP B/32 Ranked Crops",
        "map_panel_id": "precision-map-clip",
        "map_panel_title": "CLIP B/32 Euclidean Rank Map",
        "model_id": "openai/clip-vit-base-patch32/same-scene-crop-distance",
        "space_geometry": "euclidean",
        "layout_geometry": "euclidean",
        "rank_key": "clipRank",
        "accent": "#c4b5fd",
    },
}

CASE_CENTERS = {
    "facilities": np.asarray([-0.42, 0.28], dtype=np.float32),
    "retail": np.asarray([0.42, 0.24], dtype=np.float32),
    "fleet": np.asarray([0.02, -0.46], dtype=np.float32),
}


def load_cases() -> dict[str, Any]:
    return json.loads(CASE_FILE.read_text())


def readable(value: str) -> str:
    return re.sub(r"\s+", " ", str(value).replace("_", " ")).strip()


def case_by_id(payload: dict[str, Any], case_id: str) -> dict[str, Any]:
    return next((case for case in payload["cases"] if case["id"] == case_id), payload["cases"][0])


def add_sample(dataset: hv.Dataset, existing_ids: set[str], sample_id: str, image_path: str, label: str, metadata: dict[str, Any]) -> None:
    if sample_id in existing_ids:
        return
    full_path = SPACE_DIR / image_path
    if not full_path.exists():
        raise FileNotFoundError(full_path)
    dataset.add_samples(
        [
            Sample(
                id=sample_id,
                filepath=str(full_path),
                label=label,
                metadata=metadata,
            )
        ],
        skip_existing=False,
    )
    existing_ids.add(sample_id)


def add_ranked_crop_samples(dataset: hv.Dataset, payload: dict[str, Any]) -> None:
    existing_ids = {sample.id for sample in dataset.samples}
    added_before = len(existing_ids)
    for case in payload["cases"]:
        case_label = readable(case["label"])
        shared = {
            "source_dataset": payload["dataset"],
            "split": payload["split"],
            "industry_slice": case_label,
            "case_id": case["id"],
            "query": case["query"],
            "business_case": case["business"],
            "candidate_crop_count": len(case["crops"]),
            "target_crop_id": case["target"],
            "hyper3_clip_target_rank": case["metric"]["hyper3_clip"],
            "clip_b32_target_rank": case["metric"]["clip_b32"],
            "rank_delta": case["metric"]["delta"],
        }
        add_sample(
            dataset,
            existing_ids,
            case["source"]["sampleId"],
            case["source"]["path"],
            case_label,
            {
                **shared,
                "role": "source_scene",
                "caption": f"{case_label} source scene with boxed target region",
                "model": "anchor",
            },
        )
        for crop in case["crops"]:
            add_sample(
                dataset,
                existing_ids,
                crop["sampleId"],
                crop["path"],
                case_label,
                {
                    **shared,
                    "role": "candidate_crop",
                    "caption": crop["label"],
                    "crop_label": crop["label"],
                    "is_target": bool(crop.get("isTarget")),
                    "hyper3_clip_rank": crop["hyper3Rank"],
                    "clip_b32_rank": crop["clipRank"],
                },
            )
    print(f"Prepared {len(existing_ids) - added_before} ranked crop samples.", flush=True)


def poincare_to_hyperboloid(coords: np.ndarray) -> np.ndarray:
    norm_sq = np.sum(coords * coords, axis=1, keepdims=True)
    denom = np.maximum(1.0 - norm_sq, 1e-6)
    time = (1.0 + norm_sq) / denom
    spatial = (2.0 * coords) / denom
    return np.concatenate([time, spatial], axis=1).astype(np.float32)


def ranked_poincare_coords(case: dict[str, Any], rank_key: str) -> dict[str, np.ndarray]:
    center = CASE_CENTERS[case["id"]]
    coords: dict[str, np.ndarray] = {case["source"]["sampleId"]: center}
    for crop in case["crops"]:
        rank = int(crop[rank_key])
        angle = 0.58 * rank + (0.21 if case["id"] == "retail" else 0.0)
        radius = 0.055 + 0.033 * rank
        offset = np.asarray([math.cos(angle), math.sin(angle)], dtype=np.float32) * radius
        point = center + offset
        norm = float(np.linalg.norm(point))
        if norm >= 0.88:
            point = point / norm * 0.86
        coords[crop["sampleId"]] = point.astype(np.float32)
    return coords


def unit_vector(theta: float) -> list[float]:
    return [math.cos(theta), math.sin(theta)]


def model_vectors(payload: dict[str, Any], model_key: str) -> tuple[list[str], np.ndarray, np.ndarray]:
    spec = MODEL_LAYOUT_SPECS[model_key]
    ids: list[str] = []
    embeddings: list[list[float]] = []
    layout_coords: list[list[float]] = []

    for case_index, case in enumerate(payload["cases"]):
        if model_key == "hyper3":
            pcoords = ranked_poincare_coords(case, spec["rank_key"])
            case_ids = [case["source"]["sampleId"], *(crop["sampleId"] for crop in case["crops"])]
            coords = np.vstack([pcoords[sample_id] for sample_id in case_ids]).astype(np.float32)
            hyperboloid = poincare_to_hyperboloid(coords)
            ids.extend(case_ids)
            embeddings.extend(hyperboloid.tolist())
            layout_coords.extend(coords.tolist())
            continue

        base_angle = case_index * 2.12
        y = float(-case_index * 3.0)
        ids.append(case["source"]["sampleId"])
        embeddings.append(unit_vector(base_angle))
        layout_coords.append([0.0, y])
        for crop in case["crops"]:
            rank = int(crop[spec["rank_key"]])
            jitter = ((rank % 3) - 1) * 0.08
            ids.append(crop["sampleId"])
            embeddings.append(unit_vector(base_angle + 0.055 * rank))
            layout_coords.append([0.22 * rank, y + jitter])

    return ids, np.asarray(embeddings, dtype=np.float32), np.asarray(layout_coords, dtype=np.float32)


def install_rank_layout(dataset: hv.Dataset, model_key: str, payload: dict[str, Any]) -> str:
    spec = MODEL_LAYOUT_SPECS[model_key]
    ids, embeddings, coords = model_vectors(payload, model_key)
    config: dict[str, Any] = {
        "provider": "precomputed-distance-space",
        "source_dataset": payload["dataset"],
        "geometry": spec["space_geometry"],
        "note": "Vectors encode the same-scene crop ranking distances used by this demo.",
    }
    if spec["space_geometry"] == "hyperboloid":
        config["params"] = {"curvature": 1.0}
        config["params_source"] = {"curvature": "demo"}
    dataset._storage.ensure_space(
        spec["model_id"],
        dim=int(embeddings.shape[1]),
        config=config,
        space_key=spec["space_key"],
    )
    dataset._storage.add_embeddings(spec["space_key"], ids, embeddings)
    layout_key = make_layout_key(
        spec["space_key"],
        method="rankspace",
        geometry=spec["layout_geometry"],
        layout_dimension=2,
    )
    dataset._storage.ensure_layout(
        layout_key=layout_key,
        space_key=spec["space_key"],
        method="rankspace",
        geometry=spec["layout_geometry"],
        params={"source": "same_scene_crop_rank_distances"},
    )
    dataset._storage.add_layout_coords(layout_key, ids, coords)
    print(f"Installed {spec['layout_title']}: {layout_key}", flush=True)
    return layout_key


def set_real_layouts(dataset: hv.Dataset) -> tuple[dict[str, str], dict[str, str]]:
    print("Computing actual embeddings for Hyper3-CLIP...", flush=True)
    hyper3_space = dataset.compute_embeddings("hyper3-clip-v0.5")

    print("Computing actual embeddings for CLIP B/32...", flush=True)
    clip_space = dataset.compute_embeddings("openai/clip-vit-base-patch32")

    print("Computing Poincaré PCA layout for Hyper3-CLIP...", flush=True)
    hyper3_layout = dataset.compute_visualization(
        hyper3_space,
        method="pca",
        layout="poincare",
        force=True,
    )

    print("Computing Euclidean PCA layout for CLIP B/32...", flush=True)
    clip_layout = dataset.compute_visualization(
        clip_space,
        method="pca",
        layout="euclidean",
        force=True,
    )

    spaces = {
        "hyper3": hyper3_space,
        "clip": clip_space,
    }
    layouts = {
        "hyper3": hyper3_layout,
        "clip": clip_layout,
    }
    return spaces, layouts


def model_panel_props(spaces: dict[str, str], layouts: dict[str, str]) -> list[dict[str, str]]:
    return [
        {
            "key": key,
            "displayName": spec["display_name"],
            "layoutKey": layouts[key],
            "spaceKey": spaces[key],
            "rankPanelId": spec["rank_panel_id"],
            "mapPanelId": spec["map_panel_id"],
            "accent": spec["accent"],
        }
        for key, spec in MODEL_LAYOUT_SPECS.items()
    ]


def write_case_data(payload: dict[str, Any]) -> None:
    cases = []
    for case in payload["cases"]:
        target = next(crop for crop in case["crops"] if crop["sampleId"] == case["target"])
        cases.append(
            {
                "id": case["id"],
                "label": case["label"],
                "query": case["query"],
                "business": case["business"],
                "sourceSampleId": case["source"]["sampleId"],
                "targetSampleId": case["target"],
                "targetLabel": target["label"],
                "sampleCount": len(case["crops"]),
                "metric": case["metric"],
            }
        )
    out = "export const rankedCases = " + json.dumps(cases, separators=(",", ":")) + ";\n"
    (EXTENSION_DIR / "case_data.js").write_text(out)


def rank_panel_props(layout_key: str, source: str) -> dict[str, Any]:
    return {
        "mode": "ranked",
        "rank": {
            "layoutKey": layout_key,
            "k": 8,
            "source": source,
        },
    }


def anchored_rank_panel_props(layout_key: str, source_sample_id: str, source: str) -> dict[str, Any]:
    props = rank_panel_props(layout_key, source)
    props["rank"] = {**props["rank"], "anchorSampleId": source_sample_id}
    return props


def build_demo_view(payload: dict[str, Any], spaces: dict[str, str], layouts: dict[str, str]) -> hv.ui.View:
    default_case = case_by_id(payload, DEFAULT_CASE_ID)
    hyper3_ranked = hv.ui.Samples(
        id=MODEL_LAYOUT_SPECS["hyper3"]["rank_panel_id"],
        title=MODEL_LAYOUT_SPECS["hyper3"]["rank_panel_title"],
        position="center",
        props=anchored_rank_panel_props(
            layouts["hyper3"],
            default_case["source"]["sampleId"],
            "Hyper3-CLIP hyperbolic distance",
        ),
        layout=hv.ui.PanelLayout(min_height=300, min_width=260),
    )
    clip_ranked = hv.ui.Samples(
        id=MODEL_LAYOUT_SPECS["clip"]["rank_panel_id"],
        title=MODEL_LAYOUT_SPECS["clip"]["rank_panel_title"],
        position="center",
        reference_panel_id=MODEL_LAYOUT_SPECS["hyper3"]["rank_panel_id"],
        direction="right",
        props=anchored_rank_panel_props(
            layouts["clip"],
            default_case["source"]["sampleId"],
            "CLIP B/32 cosine distance",
        ),
        layout=hv.ui.PanelLayout(min_height=300, min_width=260),
    )
    hyper3_map = hv.ui.Scatter(
        id=MODEL_LAYOUT_SPECS["hyper3"]["map_panel_id"],
        title="Hyper3-CLIP Embedding Layout (PCA)",
        layout_key=layouts["hyper3"],
        position="center",
        reference_panel_id=MODEL_LAYOUT_SPECS["hyper3"]["rank_panel_id"],
        direction="below",
        geometry=MODEL_LAYOUT_SPECS["hyper3"]["layout_geometry"],
        layout_dimension=2,
        layout=hv.ui.PanelLayout(height=190, min_height=150, min_width=240),
    )
    clip_map = hv.ui.Scatter(
        id=MODEL_LAYOUT_SPECS["clip"]["map_panel_id"],
        title="CLIP B/32 Embedding Layout (PCA)",
        layout_key=layouts["clip"],
        position="center",
        reference_panel_id=MODEL_LAYOUT_SPECS["hyper3"]["map_panel_id"],
        direction="right",
        geometry=MODEL_LAYOUT_SPECS["clip"]["layout_geometry"],
        layout_dimension=2,
        layout=hv.ui.PanelLayout(min_height=150, min_width=240),
    )
    side_panel = hv.ui.ExtensionPanel(
        id="precision-region-readout",
        title="Crop Ranking Control",
        extension="precision-region-readout",
        panel="precision-region-comparison",
        position="right",
        layout=hv.ui.PanelLayout(width=280, min_width=260),
        props={
            "dataset": payload["dataset"],
            "split": payload["split"],
            "workspaceId": WORKSPACE_ID,
            "initialCaseId": DEFAULT_CASE_ID,
            "models": model_panel_props(spaces, layouts),
        },
    )
    return hv.ui.View(hyper3_ranked, clip_ranked, hyper3_map, clip_map, side_panel, active_panel="precision-region-readout")


def launch_demo(dataset: hv.Dataset, payload: dict[str, Any], spaces: dict[str, str], layouts: dict[str, str]) -> hv.Session:
    session = hv.launch(
        dataset,
        host=SPACE_HOST,
        port=SPACE_PORT,
        open_browser=False,
        workspace_id=WORKSPACE_ID,
        block=False,
    )
    write_case_data(payload)
    print("Installing precision region-search extension...", flush=True)
    session.ui.add_extension(EXTENSION_DIR, workspace_id=WORKSPACE_ID)
    print("Applying same-scene ranked crop HyperView workspace...", flush=True)
    session.ui.apply_view(build_demo_view(payload, spaces, layouts), workspace_id=WORKSPACE_ID)
    default_case = case_by_id(payload, DEFAULT_CASE_ID)
    session.ui.set_active_layout(layouts["hyper3"], workspace_id=WORKSPACE_ID)
    session.ui.set_selection([default_case["source"]["sampleId"]], workspace_id=WORKSPACE_ID)
    print(f"\nHyperView same-scene crop ranking demo is running at {session.url}", flush=True)
    print("   Compare the two ranked Samples panels; each model uses its own distance space.", flush=True)
    return session


def main() -> None:
    payload = load_cases()
    dataset = hv.Dataset(DATASET_NAME)
    add_ranked_crop_samples(dataset, payload)
    spaces, layouts = set_real_layouts(dataset)
    session = launch_demo(dataset, payload, spaces, layouts)
    session.wait()


if __name__ == "__main__":
    main()
