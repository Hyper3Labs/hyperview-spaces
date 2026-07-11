#!/usr/bin/env python
"""Open Images visual safety moderation demo for CLIP vs hyper3-clip."""

from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from huggingface_hub import hf_hub_download
import hyperview as hv
from hyperview.core.sample import Sample


SPACE_DIR = Path(__file__).resolve().parent
SPACE_HOST = os.environ.get("HYPERVIEW_HOST", "127.0.0.1")
SPACE_PORT = int(os.environ.get("HYPERVIEW_PORT", "6262"))
WORKSPACE_ID = os.environ.get("HYPERVIEW_WORKSPACE_ID", "visual-safety-content-clip-hyper3clip")
DATASET_NAME = os.environ.get("HYPERVIEW_DATASET_NAME", "openimages_visual_safety_marketplace_triage_assets_v1")
EXTENSION_DIR = SPACE_DIR / ".hyperview" / "extensions" / "safety-readout"
SAMPLES_PER_BUCKET = int(os.environ.get("SAFETY_SAMPLES_PER_BUCKET", "60"))
ASSET_MANIFEST_PATH = os.environ.get("SAFETY_ASSET_MANIFEST", "demo_assets/manifest.json")
ASSET_REPO_ID = os.environ.get("SAFETY_ASSET_REPO_ID") or os.environ.get("SPACE_ID")
ASSET_REPO_TYPE = os.environ.get("SAFETY_ASSET_REPO_TYPE", "space")
ASSET_REVISION = os.environ.get("SAFETY_ASSET_REVISION") or None
ASSET_LOCAL_ROOT = Path(os.environ.get("SAFETY_ASSET_LOCAL_ROOT", str(SPACE_DIR)))

DEMO_SCENARIOS = (
    {
        "labels": ("Knife", "Kitchen knife"),
        "title": "Kitchen knife upload",
        "step": "1",
        "decision": "Route to policy review",
        "business_value": "Catches listings that may be allowed in some contexts but need marketplace policy checks before broad distribution.",
        "inspect": "A useful model should pull nearby knives/tools into the same neighborhood instead of mixing them with ordinary kitchenware.",
    },
    {
        "labels": ("Beer", "Wine", "Alcoholic beverage"),
        "title": "Alcohol listing",
        "step": "2",
        "decision": "Restrict or age-gate",
        "business_value": "Separates regulated goods from normal shopping content so the queue can apply the correct country and age policy.",
        "inspect": "Look for alcohol examples grouped together, not scattered across safe food or glassware listings.",
    },
    {
        "labels": ("Shoe", "Clothing", "Dress", "Toy", "Chair"),
        "title": "Normal seller upload",
        "step": "3",
        "decision": "Approve without review",
        "business_value": "Avoids false positives that slow down legitimate sellers and create unnecessary moderator load.",
        "inspect": "A useful model keeps ordinary listings away from the needs-review neighborhood.",
    },
)

SMOKE_METRICS = {
    "dataset": "Open Images V7 validation safety proxy",
    "nImages": 120,
    "classBalance": "60 safe / 60 needs review",
    "clip": {
        "accuracy": 0.758,
        "auroc": 0.865,
        "apReview": 0.870,
        "f1Review": 0.768,
        "reviewRecall": 0.800,
        "reviewPrecision": 0.738,
        "safeRecall": 0.717,
    },
    "candidate": {
        "accuracy": 0.725,
        "auroc": 0.839,
        "apReview": 0.812,
        "f1Review": 0.752,
        "reviewRecall": 0.833,
        "reviewPrecision": 0.685,
        "safeRecall": 0.617,
    },
    "readout": (
        "CLIP is stronger overall on the first zero-shot smoke test. hyper3-clip catches slightly more "
        "review items, which is useful for moderation triage but creates more false positives."
    ),
}

MODEL_SPECS = [
    {
        "key": "clip",
        "display_name": os.environ.get("SAFETY_BASELINE_DISPLAY_NAME", "CLIP-B/32"),
        "button_label": os.environ.get("SAFETY_BASELINE_BUTTON_LABEL", "Inspect with CLIP"),
        "provider": os.environ.get("SAFETY_BASELINE_PROVIDER", "embed-anything"),
        "model": os.environ.get("SAFETY_BASELINE_MODEL", "openai/clip-vit-base-patch32"),
        "layout": os.environ.get("SAFETY_BASELINE_LAYOUT", "euclidean:2d"),
        "geometry": os.environ.get("SAFETY_BASELINE_GEOMETRY", "euclidean"),
        "layout_dimension": int(os.environ.get("SAFETY_BASELINE_LAYOUT_DIMENSION", "2")),
        "metric": os.environ.get("SAFETY_BASELINE_METRIC", "cosine"),
        "panel_title": os.environ.get("SAFETY_BASELINE_PANEL_TITLE", "CLIP-B/32 - Safety Review Map"),
    },
    {
        "key": "candidate",
        "display_name": os.environ.get("SAFETY_CANDIDATE_DISPLAY_NAME", "hyper3-clip"),
        "button_label": os.environ.get("SAFETY_CANDIDATE_BUTTON_LABEL", "Inspect with hyper3-clip"),
        "provider": os.environ.get("SAFETY_CANDIDATE_PROVIDER", "hyper-models"),
        "model": os.environ.get("SAFETY_CANDIDATE_MODEL", "hyper3-clip-v0.5"),
        "layout": os.environ.get("SAFETY_CANDIDATE_LAYOUT", "poincare:2d"),
        "geometry": os.environ.get("SAFETY_CANDIDATE_GEOMETRY", "poincare"),
        "layout_dimension": int(os.environ.get("SAFETY_CANDIDATE_LAYOUT_DIMENSION", "2")),
        "metric": os.environ.get("SAFETY_CANDIDATE_METRIC", "cosine"),
        "panel_title": os.environ.get("SAFETY_CANDIDATE_PANEL_TITLE", "hyper3-clip - Safety Review Map"),
    },
]


def resolve_asset(relative_path: str) -> Path:
    if ASSET_REPO_ID:
        return Path(
            hf_hub_download(
                repo_id=ASSET_REPO_ID,
                repo_type=ASSET_REPO_TYPE,
                revision=ASSET_REVISION,
                filename=relative_path,
            )
        )

    local_path = ASSET_LOCAL_ROOT / relative_path
    if not local_path.exists():
        raise FileNotFoundError(
            f"Asset '{relative_path}' was not found locally and SAFETY_ASSET_REPO_ID/SPACE_ID is unset."
        )
    return local_path


def safe_sample_id(record: dict[str, Any]) -> str:
    return f"openimages_{record['index']:03d}_{record['bucket']}_{record['image_id']}"


def choose_records() -> list[dict[str, Any]]:
    manifest_path = resolve_asset(ASSET_MANIFEST_PATH)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records: list[dict[str, Any]] = []
    for item in manifest.get("records", []):
        bucket = item["bucket"]
        if sum(1 for record in records if record["bucket"] == bucket) >= SAMPLES_PER_BUCKET:
            continue
        image_path = resolve_asset(item["asset_path"])
        records.append(
            {
                "index": len(records),
                "image_id": item["image_id"],
                "bucket": bucket,
                "label": item["label"],
                "labels": item["labels"],
                "path": image_path,
                "source_url": item["source_url"],
                "license": item.get("license", ""),
                "title": item.get("title", ""),
            }
        )
        if all(
            sum(1 for record in records if record["bucket"] == bucket_name) >= SAMPLES_PER_BUCKET
            for bucket_name in ("needs_review", "safe")
        ):
            break

    if not records:
        raise RuntimeError("No Open Images records could be prepared.")

    records = order_records_for_demo(records)
    for index, record in enumerate(records):
        record["index"] = index
    counts = Counter(record["bucket"] for record in records)
    print(f"Prepared Open Images safety records: {dict(counts)}", flush=True)
    source = f"Hugging Face {ASSET_REPO_TYPE} '{ASSET_REPO_ID}'" if ASSET_REPO_ID else "local demo_assets"
    print(f"Loaded visual-safety assets from {source}.", flush=True)
    return records


def order_records_for_demo(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Put landing-page-friendly examples first in the Samples panel."""
    used: set[str] = set()
    ordered: list[dict[str, Any]] = []

    def append_unique(items: list[dict[str, Any]]) -> None:
        for item in items:
            if item["image_id"] in used:
                continue
            used.add(item["image_id"])
            ordered.append(item)

    by_label: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        by_label[record["label"]].append(record)

    for scenario in DEMO_SCENARIOS:
        record = next(
            (
                candidate
                for label in scenario["labels"]
                for candidate in by_label.get(label, [])
                if candidate["image_id"] not in used
            ),
            None,
        )
        if record is None:
            continue
        append_unique([record])

    append_unique(sorted(
        (record for record in records if record["bucket"] == "safe" and record["image_id"] not in used),
        key=lambda record: (record["label"], record["image_id"]),
    ))
    append_unique([record for record in records if record["bucket"] == "needs_review" and record["image_id"] not in used])
    append_unique([record for record in records if record["image_id"] not in used])

    return ordered


def add_safety_samples(dataset: hv.Dataset) -> list[dict[str, Any]]:
    existing_ids = {sample.id for sample in dataset.samples}
    records = choose_records()
    samples: list[Sample] = []
    existing_selected_ids = set()

    for record in records:
        sample_id = safe_sample_id(record)
        existing_selected_ids.add(sample_id)
        metadata = {
            "policy_bucket": record["bucket"],
            "open_images_labels": record["labels"],
            "primary_label": record["label"],
            "source_dataset": "Open Images V7 validation",
            "source_url": record["source_url"],
            "license": record.get("license", ""),
            "title": record.get("title", ""),
            "business_use_case": "marketplace listing moderation triage",
            "display_order": record["index"],
        }

        samples.append(
            Sample(
                id=sample_id,
                filepath=str(record["path"]),
                label=record["bucket"],
                metadata=metadata,
            )
        )

    added = len(existing_selected_ids - existing_ids)
    updated = len(existing_selected_ids & existing_ids)
    dataset.add_samples(samples, skip_existing=False)
    print(f"Prepared Open Images safety samples ({added} added, {updated} updated).", flush=True)
    return records


def ensure_layouts(dataset: hv.Dataset) -> dict[str, str]:
    layouts: dict[str, str] = {}
    for spec in MODEL_SPECS:
        print(f"Ensuring {spec['display_name']} embeddings...", flush=True)
        space_key = dataset.compute_embeddings(
            model=spec["model"],
            provider=spec["provider"],
            batch_size=32,
            show_progress=True,
        )
        print(f"Ensuring {spec['display_name']} layout...", flush=True)
        layouts[spec["key"]] = dataset.compute_visualization(
            space_key=space_key,
            layout=spec["layout"],
            n_neighbors=20,
            min_dist=0.08,
            metric=spec["metric"],
        )
    return layouts


def build_dataset() -> tuple[hv.Dataset, dict[str, str], list[dict[str, Any]]]:
    dataset = hv.Dataset(DATASET_NAME)
    records = add_safety_samples(dataset)
    layouts = ensure_layouts(dataset)
    return dataset, layouts, records


def model_panel_props(layouts: dict[str, str]) -> list[dict[str, Any]]:
    show_baseline = os.environ.get("SAFETY_SHOW_BASELINE_BUTTONS", "").lower() in {"1", "true", "yes"}
    props = []
    for spec in MODEL_SPECS:
        if spec["key"] == "clip" and not show_baseline:
            continue
        props.append(
            {
                "key": spec["key"],
                "displayName": spec["display_name"],
                "buttonLabel": spec["button_label"],
                "layoutKey": layouts[spec["key"]],
            }
        )
    return props


def build_examples(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_label: dict[str, dict[str, Any]] = {}
    for record in records:
        by_label.setdefault(record["label"], record)

    examples = []
    for scenario in DEMO_SCENARIOS:
        record = next((by_label.get(label) for label in scenario["labels"] if label in by_label), None)
        if record is None:
            continue
        bucket = record["bucket"]
        examples.append(
            {
                "id": record["image_id"],
                "step": scenario["step"],
                "title": scenario["title"],
                "family": "Needs review" if bucket == "needs_review" else "Safe listing",
                "decision": scenario["decision"],
                "businessValue": scenario["business_value"],
                "inspect": scenario["inspect"],
                "queryId": safe_sample_id(record),
                "queryLabel": record["label"],
                "bucket": bucket,
                "labels": record["labels"],
                "sourceUrl": record["source_url"],
            }
        )
    return examples


def build_demo_view(dataset: hv.Dataset, layouts: dict[str, str], records: list[dict[str, Any]]) -> hv.ui.View:
    primary_spec = next(spec for spec in MODEL_SPECS if spec["key"] == "candidate")
    samples_panel = hv.ui.Samples(
        id="safety-samples",
        title="Samples",
        position="center",
        layout=hv.ui.PanelLayout(min_height=420),
    )
    primary_scatter = hv.ui.Scatter(
        id="hyper3-clip-safety-map-bottom",
        title=primary_spec["panel_title"],
        position="bottom",
        reference_panel_id="safety-samples",
        direction="below",
        layout_key=layouts[primary_spec["key"]],
        geometry=primary_spec["geometry"],
        layout_dimension=primary_spec["layout_dimension"],
        layout=hv.ui.PanelLayout(height=280, min_height=220),
    )
    readout_panel = hv.ui.ExtensionPanel(
        id="visual-safety-readout",
        extension="safety-readout",
        panel="safety-comparison",
        title="Safety triage",
        reference_panel_id="safety-samples",
        direction="right",
        props={
            "models": model_panel_props(layouts),
            "examples": build_examples(records),
            "metrics": SMOKE_METRICS,
            "bucketCounts": dict(Counter(record["bucket"] for record in records)),
        },
        layout=hv.ui.PanelLayout(width=520, min_width=420),
    )
    return hv.ui.View(
        samples_panel,
        readout_panel,
        primary_scatter,
    )


def launch_demo(dataset: hv.Dataset, layouts: dict[str, str], records: list[dict[str, Any]]) -> hv.Session:
    session = hv.launch(
        dataset,
        host=SPACE_HOST,
        port=SPACE_PORT,
        open_browser=False,
        workspace_id=WORKSPACE_ID,
        block=False,
    )
    print("Installing Open Images visual-safety demo extension...", flush=True)
    session.ui.add_extension(EXTENSION_DIR, workspace_id=WORKSPACE_ID)
    print("Applying Open Images visual-safety triage demo view...", flush=True)
    session.ui.apply_view(build_demo_view(dataset, layouts, records), workspace_id=WORKSPACE_ID)
    session.ui.set_active_layout(layouts["candidate"], workspace_id=WORKSPACE_ID)
    session.ui.set_selection([], workspace_id=WORKSPACE_ID)
    print(f"\nHyperView Open Images visual-safety demo is running at {session.url}", flush=True)
    return session


def main() -> None:
    dataset, layouts, records = build_dataset()
    print("Layouts:", flush=True)
    for spec in MODEL_SPECS:
        print(f"  {spec['display_name']}: {layouts[spec['key']]}", flush=True)
    session = launch_demo(dataset, layouts, records)
    session.wait()


if __name__ == "__main__":
    main()
