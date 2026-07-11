#!/usr/bin/env python
"""Logo brand-search comparison demo for CLIP vs Hyper3-CLIP in HyperView."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any

from datasets import load_dataset
from PIL import Image

import hyperview as hv
from hyperview.core.sample import Sample

SPACE_DIR = Path(__file__).resolve().parent
SPACE_HOST = os.environ.get("HYPERVIEW_HOST", "127.0.0.1")
SPACE_PORT = int(os.environ.get("HYPERVIEW_PORT", "6272"))
WORKSPACE_ID = os.environ.get("HYPERVIEW_WORKSPACE_ID", "logo-brand-search-clip-hyper3clip-hf-live-v4")
DATASET_NAME = os.environ.get("HYPERVIEW_DATASET_NAME", "logo_brand_search_clip_hyper3clip_hf_live_v4")
EXTENSION_DIR = SPACE_DIR / ".hyperview" / "extensions" / "logo-brand-readout"
CASE_FILE = SPACE_DIR / "cases.json"
DEFAULT_CASE_ID = os.environ.get("LOGO_BRAND_DEFAULT_CASE_ID", "01-barber-franchise")
HF_DATASET = os.environ.get("LOGO_BRAND_HF_DATASET", "logo-wizard/modern-logo-dataset")
HF_SPLIT = os.environ.get("LOGO_BRAND_HF_SPLIT", "train[:160]")
HF_REVISION = os.environ.get("LOGO_BRAND_HF_REVISION") or None
IMAGE_DIR = Path(os.environ.get("LOGO_BRAND_IMAGE_DIR", SPACE_DIR / "demo_data" / "logo_images"))
FORCE_IMAGE_REFRESH = os.environ.get("LOGO_BRAND_FORCE_IMAGE_REFRESH", "0").lower() in {
    "1",
    "true",
    "yes",
}

MODEL_SPECS = [
    {
        "key": "clip",
        "display_name": "CLIP B/32",
        "provider": os.environ.get("LOGO_BRAND_BASELINE_PROVIDER", "embed-anything"),
        "model": os.environ.get("LOGO_BRAND_BASELINE_MODEL", "openai/clip-vit-base-patch32"),
        "layout": os.environ.get("LOGO_BRAND_BASELINE_LAYOUT", "euclidean:2d"),
        "geometry": os.environ.get("LOGO_BRAND_BASELINE_GEOMETRY", "euclidean"),
        "layout_dimension": int(os.environ.get("LOGO_BRAND_BASELINE_LAYOUT_DIMENSION", "2")),
        "metric": os.environ.get("LOGO_BRAND_BASELINE_METRIC", "cosine"),
        "batch_size": int(os.environ.get("LOGO_BRAND_BASELINE_BATCH_SIZE", "32")),
        "panel_title": os.environ.get("LOGO_BRAND_BASELINE_PANEL_TITLE", "CLIP B/32 Actual Embeddings"),
    },
    {
        "key": "hyper3",
        "display_name": "Hyper3-CLIP",
        "provider": os.environ.get("LOGO_BRAND_CANDIDATE_PROVIDER", "hyper-models"),
        "model_id": "hyper3-clip-v0.5",
        "model": os.environ.get("LOGO_BRAND_CANDIDATE_MODEL", "hyper3-clip-v0.5"),
        "layout": os.environ.get("LOGO_BRAND_CANDIDATE_LAYOUT", "poincare:2d"),
        "geometry": os.environ.get("LOGO_BRAND_CANDIDATE_GEOMETRY", "poincare"),
        "layout_dimension": int(os.environ.get("LOGO_BRAND_CANDIDATE_LAYOUT_DIMENSION", "2")),
        "metric": os.environ.get("LOGO_BRAND_CANDIDATE_METRIC", "cosine"),
        "batch_size": int(os.environ.get("LOGO_BRAND_CANDIDATE_BATCH_SIZE", "8")),
        "panel_title": os.environ.get("LOGO_BRAND_CANDIDATE_PANEL_TITLE", "Hyper3-CLIP Actual Embeddings"),
    },
]


def load_cases() -> dict[str, Any]:
    return json.loads(CASE_FILE.read_text())


def sample_id_for_index(index: int) -> str:
    return f"logo_{index:04d}"


def row_path(index: int) -> Path:
    return IMAGE_DIR / f"{sample_id_for_index(index)}.jpg"


def image_to_data_uri(path: Path) -> str:
    import base64

    return "data:image/jpeg;base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def save_logo_image(image: Image.Image, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    rgb = image.convert("RGB")
    rgb.thumbnail((768, 768), Image.Resampling.LANCZOS)
    rgb.save(destination, format="JPEG", quality=88, optimize=True)


def load_hf_rows(payload: dict[str, Any]):
    dataset_name = os.environ.get("LOGO_BRAND_HF_DATASET", payload.get("dataset", HF_DATASET))
    split = os.environ.get("LOGO_BRAND_HF_SPLIT", payload.get("split", HF_SPLIT))
    print(f"Loading {dataset_name} {split} from Hugging Face...", flush=True)
    return load_dataset(dataset_name, split=split, revision=HF_REVISION)


def extract_logo_category(text: str) -> str:
    value = text.strip().strip('"')
    prefix = "a logo of "
    if value.lower().startswith(prefix):
        value = value[len(prefix) :]
    return value.split(",", 1)[0].strip().title() or "Logo"


def enrich_sample(sample: dict[str, Any]) -> dict[str, Any]:
    row_index = int(sample["hfIndex"])
    path = row_path(row_index)
    enriched = {
        **sample,
        "sampleId": sample_id_for_index(row_index),
        "path": str(path.relative_to(SPACE_DIR)),
        "image": image_to_data_uri(path),
    }
    return enriched


def add_logo_samples(dataset: hv.Dataset, samples: list[Sample]) -> tuple[int, int]:
    return dataset.add_samples(samples, skip_existing=True)


def prepare_logo_rows(dataset: hv.Dataset, payload: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    hf_rows = load_hf_rows(payload)
    if FORCE_IMAGE_REFRESH and IMAGE_DIR.exists():
        shutil.rmtree(IMAGE_DIR)
    sample_ids: list[str] = []
    samples: list[Sample] = []
    for row_index, row in enumerate(hf_rows):
        sample_id = sample_id_for_index(row_index)
        sample_ids.append(sample_id)
        destination = row_path(row_index)
        if FORCE_IMAGE_REFRESH or not destination.exists():
            save_logo_image(row["image"], destination)
        text = str(row["text"])
        width, height = Image.open(destination).size
        samples.append(
            Sample(
                id=sample_id,
                filepath=str(destination),
                label=extract_logo_category(text),
                metadata={
                    "source_dataset": payload["dataset"],
                    "split": payload["split"],
                    "hf_index": row_index,
                    "caption": text,
                    "role": "candidate_logo",
                },
                width=width,
                height=height,
            )
        )
    added, skipped = add_logo_samples(dataset, samples)
    print(f"Prepared {len(sample_ids)} HF logo candidates ({added} added, {skipped} existing).", flush=True)
    enriched = enrich_case_payload(payload)
    write_case_data_js(enriched)
    return enriched, sample_ids


def enrich_case_payload(payload: dict[str, Any]) -> dict[str, Any]:
    cases = []
    for case in payload["cases"]:
        cases.append(
            {
                **case,
                "target": enrich_sample(case["target"]),
                "hyper3Results": [enrich_sample(result) for result in case["hyper3Results"]],
                "clipResults": [enrich_sample(result) for result in case["clipResults"]],
                **(
                    {"clipTargetProof": enrich_sample(case["clipTargetProof"])}
                    if case.get("clipTargetProof")
                    else {}
                ),
            }
        )
    return {**payload, "cases": cases}


def write_case_data_js(payload: dict[str, Any]) -> None:
    EXTENSION_DIR.mkdir(parents=True, exist_ok=True)
    metrics = {
        **payload["metrics"],
        "sample_count": payload["cases"][0]["sampleCount"] if payload["cases"] else 0,
        "dataset": payload["dataset"],
    }
    js = (
        "export const logoCases = "
        + json.dumps(payload["cases"], separators=(",", ":"))
        + ";\nexport const logoMetrics = "
        + json.dumps(metrics, separators=(",", ":"))
        + ";\n"
    )
    (EXTENSION_DIR / "case_data.js").write_text(js)
    print("Generated logo brand-search extension case data.", flush=True)


def ensure_layouts(dataset: hv.Dataset, sample_ids: list[str]) -> dict[str, str]:
    layouts: dict[str, str] = {}
    for spec in MODEL_SPECS:
        print(f"Computing {spec['display_name']} embeddings...", flush=True)
        space_key = dataset.compute_embeddings(
            model=spec["model"],
            provider=spec["provider"],
            batch_size=spec["batch_size"],
            sample_ids=sample_ids,
            show_progress=True,
        )
        print(f"Computing {spec['display_name']} layout...", flush=True)
        layouts[spec["key"]] = dataset.compute_visualization(
            space_key=space_key,
            layout=spec["layout"],
            n_neighbors=20,
            min_dist=0.08,
            metric=spec["metric"],
            force=True,
        )
    return layouts


def build_demo_view(payload: dict[str, Any], layouts: dict[str, str]) -> hv.ui.View:
    contents = []
    contents.append(
        hv.ui.Samples(
            id="grid",
            title="Samples",
            position="center",
            layout=hv.ui.PanelLayout(
                height=int(os.environ.get("LOGO_BRAND_SAMPLES_HEIGHT", "470")),
                min_height=260,
            ),
            props={"mode": "browse"},
        )
    )
    map_layout = hv.ui.PanelLayout(
        height=int(os.environ.get("LOGO_BRAND_MAP_HEIGHT", "260")),
        min_height=180,
    )
    hyper3_map = hv.ui.Scatter(
        id="logo-embedding-map-hyper3",
        title=next(spec["panel_title"] for spec in MODEL_SPECS if spec["key"] == "hyper3"),
        layout_key=layouts["hyper3"],
        position="center",
        reference_panel_id="grid",
        direction="below",
        geometry=next(spec["geometry"] for spec in MODEL_SPECS if spec["key"] == "hyper3"),
        layout_dimension=next(spec["layout_dimension"] for spec in MODEL_SPECS if spec["key"] == "hyper3"),
        layout=map_layout,
    )
    clip_map = hv.ui.Scatter(
        id="logo-embedding-map-clip",
        title=next(spec["panel_title"] for spec in MODEL_SPECS if spec["key"] == "clip"),
        layout_key=layouts["clip"],
        position="center",
        reference_panel_id="logo-embedding-map-hyper3",
        direction="right",
        geometry=next(spec["geometry"] for spec in MODEL_SPECS if spec["key"] == "clip"),
        layout_dimension=next(spec["layout_dimension"] for spec in MODEL_SPECS if spec["key"] == "clip"),
        layout=map_layout,
    )
    results_panel = hv.ui.ExtensionPanel(
        id="logo-brand-results",
        title="Logo Brand Search",
        extension="logo-brand-readout",
        panel="logo-brand-comparison",
        position="right",
        layout=hv.ui.PanelLayout(
            width=int(os.environ.get("LOGO_BRAND_PANEL_WIDTH", "320")),
            min_width=260,
        ),
        props={
            "dataset": payload["dataset"],
            "split": payload["split"],
            "initialCaseId": DEFAULT_CASE_ID,
        },
    )
    return hv.ui.View(*contents, results_panel, hyper3_map, clip_map, active_panel="logo-brand-results")


def launch_demo(dataset: hv.Dataset, payload: dict[str, Any], layouts: dict[str, str]) -> hv.Session:
    session = hv.launch(
        dataset,
        host=SPACE_HOST,
        port=SPACE_PORT,
        open_browser=False,
        workspace_id=WORKSPACE_ID,
        block=False,
    )
    print("Installing logo brand-search extension...", flush=True)
    session.ui.add_extension(EXTENSION_DIR, workspace_id=WORKSPACE_ID)
    print("Applying logo brand-search demo view...", flush=True)
    session.ui.apply_view(build_demo_view(payload, layouts), workspace_id=WORKSPACE_ID)
    session.ui.clear_similarity(workspace_id=WORKSPACE_ID)
    session.ui.set_selection([], workspace_id=WORKSPACE_ID)
    print(f"\nHyperView logo brand-search demo is running at {session.url}", flush=True)
    print("   Images are loaded from Hugging Face and embeddings are computed at startup.", flush=True)
    return session


def main() -> None:
    payload = load_cases()
    dataset = hv.Dataset(DATASET_NAME)
    payload, sample_ids = prepare_logo_rows(dataset, payload)
    layouts = ensure_layouts(dataset, sample_ids)
    session = launch_demo(dataset, payload, layouts)
    session.wait()


if __name__ == "__main__":
    main()
