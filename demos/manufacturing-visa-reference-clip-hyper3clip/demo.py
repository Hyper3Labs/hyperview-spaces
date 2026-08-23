#!/usr/bin/env python
"""VisA manufacturing reference-retrieval demo for CLIP vs Hyper3-CLIP."""

from __future__ import annotations

import io
import json
import os
import re
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps

import hyperview as hv

SPACE_DIR = Path(__file__).resolve().parent
SPACE_HOST = os.environ.get("HYPERVIEW_HOST", "127.0.0.1")
SPACE_PORT = int(os.environ.get("HYPERVIEW_PORT", "6265"))
WORKSPACE_ID = os.environ.get("HYPERVIEW_WORKSPACE_ID", "manufacturing-visa-reference-clip-hyper3clip")
DATASET_NAME = os.environ.get("HYPERVIEW_DATASET_NAME", "visa_manufacturing_reference_clip_hyper3clip")
EXTENSION_DIR = SPACE_DIR / ".hyperview" / "extensions" / "manufacturing-readout"

SAMPLES_PER_CATEGORY = int(os.environ.get("VISA_SAMPLES_PER_CATEGORY", "4"))
TRAIN_FRACTION = float(os.environ.get("VISA_TRAIN_FRACTION", "0.5"))
IMAGE_MAX_SIZE = (640, 640)
VISA_DATASET_ID = "BrachioLab/visa"
VISA_DATASET_REVISION = "d185c42584b49f1df81fe12bde627559ed88d483"
FORCE_SAMPLE_REFRESH = os.environ.get("HYPERVIEW_VISA_FORCE_REFRESH", "").lower() in {
    "1",
    "true",
    "yes",
}
DATASET_SERVER_UNAVAILABLE = False
VISA_CATEGORIES = (
    "candle",
    "capsules",
    "cashew",
    "chewinggum",
    "fryum",
    "macaroni1",
    "macaroni2",
    "pcb1",
    "pcb2",
    "pcb3",
    "pcb4",
    "pipe_fryum",
)

FAMILY_BY_CATEGORY = {
    "candle": "molded_goods",
    "capsules": "packaged_consumer_goods",
    "cashew": "food_processing",
    "chewinggum": "packaged_consumer_goods",
    "fryum": "food_processing",
    "pipe_fryum": "food_processing",
    "macaroni1": "pasta_line",
    "macaroni2": "pasta_line",
    "pcb1": "pcb_assembly",
    "pcb2": "pcb_assembly",
    "pcb3": "pcb_assembly",
    "pcb4": "pcb_assembly",
}

PREFERRED_EXAMPLES = [
    ("fryum", "food-processing variant"),
    ("macaroni2", "pasta line benchmark win"),
    ("candle", "molded goods line"),
    ("pipe_fryum", "food-processing line"),
]

MODEL_SPECS = [
    {
        "key": "clip",
        "display_name": os.environ.get("VISA_BASELINE_DISPLAY_NAME", "CLIP"),
        "button_label": os.environ.get("VISA_BASELINE_BUTTON_LABEL", "Show CLIP neighbors"),
        "provider": os.environ.get("VISA_BASELINE_PROVIDER", "embed-anything"),
        "model": os.environ.get("VISA_BASELINE_MODEL", "openai/clip-vit-base-patch32"),
        "layout": os.environ.get("VISA_BASELINE_LAYOUT", "euclidean:2d"),
        "geometry": os.environ.get("VISA_BASELINE_GEOMETRY", "euclidean"),
        "layout_dimension": int(os.environ.get("VISA_BASELINE_LAYOUT_DIMENSION", "2")),
        "metric": os.environ.get("VISA_BASELINE_METRIC", "cosine"),
        "panel_title": os.environ.get("VISA_BASELINE_PANEL_TITLE", "CLIP - Inspection Reference Map"),
    },
    {
        "key": "candidate",
        "display_name": os.environ.get("VISA_CANDIDATE_DISPLAY_NAME", "Hyper3-CLIP"),
        "button_label": os.environ.get("VISA_CANDIDATE_BUTTON_LABEL", "Show Hyper3 neighbors"),
        "provider": os.environ.get("VISA_CANDIDATE_PROVIDER", "hyper-models"),
        "model": os.environ.get("VISA_CANDIDATE_MODEL", "hyper3-clip-v0.5"),
        "layout": os.environ.get("VISA_CANDIDATE_LAYOUT", "poincare:2d"),
        "geometry": os.environ.get("VISA_CANDIDATE_GEOMETRY", "poincare"),
        "layout_dimension": int(os.environ.get("VISA_CANDIDATE_LAYOUT_DIMENSION", "2")),
        "metric": os.environ.get("VISA_CANDIDATE_METRIC", "cosine"),
        "panel_title": os.environ.get("VISA_CANDIDATE_PANEL_TITLE", "Hyper3-CLIP - Inspection Reference Map"),
    },
]


def media_root() -> Path:
    root = Path(os.environ.get("HYPERVIEW_MEDIA_DIR", str(SPACE_DIR / "demo_data" / "media")))
    path = root / DATASET_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_sample_id(category: str, split_name: str, index: int, label: int) -> str:
    raw = f"visa_{category}_{split_name}_{index:04d}_label{label}"
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", raw).strip("_")[:96]


def readable(value: str) -> str:
    return value.replace("_", " ").replace("-", " ").title()


def fetch_rows(split: str, count: int) -> list[dict[str, Any]]:
    global DATASET_SERVER_UNAVAILABLE

    params = urllib.parse.urlencode(
        {
            "dataset": VISA_DATASET_ID,
            "config": "default",
            "split": split,
            "offset": 0,
            "length": min(count, 100),
        }
    )
    url = f"https://datasets-server.huggingface.co/rows?{params}"
    last_error: Exception | None = None
    if not DATASET_SERVER_UNAVAILABLE:
        for attempt in range(1, 5):
            try:
                with urllib.request.urlopen(url, timeout=60) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                rows = [item["row"] for item in payload["rows"]]
                if len(rows) < count:
                    raise RuntimeError(f"Split {split} returned {len(rows)} rows for requested count {count}")
                return rows[:count]
            except Exception as exc:
                last_error = exc
                if attempt < 4:
                    time.sleep(1.5 * attempt)
        DATASET_SERVER_UNAVAILABLE = True
        print(
            f"VisA dataset-server rows unavailable ({type(last_error).__name__}: {last_error}); "
            "falling back to the pinned Hub dataset.",
            flush=True,
        )

    try:
        from datasets import load_dataset

        stream = load_dataset(
            VISA_DATASET_ID,
            split=split,
            revision=VISA_DATASET_REVISION,
            streaming=True,
        )
        rows = []
        for row in stream:
            rows.append(row)
            if len(rows) >= count:
                break
    except Exception as exc:
        raise RuntimeError(f"Could not fetch pinned VisA split {split} from the Hub") from exc
    if len(rows) < count:
        raise RuntimeError(f"Split {split} returned {len(rows)} rows for requested count {count}") from last_error
    return rows


def local_records(category: str, split_type: str, count: int) -> list[dict[str, Any]]:
    records = []
    prefix = f"visa_{category}_{category}.{split_type}_"
    pattern = re.compile(rf"^{re.escape(prefix)}(?P<index>\d+)_label(?P<label>\d+)\.jpg$")
    for path in sorted(media_root().glob(f"{prefix}*_label*.jpg")):
        match = pattern.match(path.name)
        if match is None:
            continue
        records.append(
            {
                "row_index": int(match.group("index")),
                "image_url": None,
                "local_path": path,
                "category": category,
                "family": FAMILY_BY_CATEGORY[category],
                "split_name": f"{category}.{split_type}",
                "split_type": "normal_reference" if split_type == "train" else "inspection_query",
                "defect_label": int(match.group("label")),
            }
        )
    return records[:count]


def save_image(source: Any, destination: Path) -> None:
    if destination.exists() and destination.stat().st_size > 0:
        return
    if isinstance(source, str):
        with urllib.request.urlopen(source, timeout=60) as response:
            image = Image.open(io.BytesIO(response.read()))
    elif isinstance(source, Image.Image):
        image = source
    else:
        raise TypeError(f"Unsupported VisA image source: {type(source).__name__}")
    image = ImageOps.exif_transpose(image).convert("RGB")
    image.thumbnail(IMAGE_MAX_SIZE, Image.Resampling.LANCZOS)
    tmp_path = destination.with_suffix(destination.suffix + ".tmp")
    image.save(tmp_path, format="JPEG", quality=92, optimize=True)
    tmp_path.replace(destination)


def select_visa_records() -> list[dict[str, Any]]:
    train_count = max(0, min(SAMPLES_PER_CATEGORY, round(SAMPLES_PER_CATEGORY * TRAIN_FRACTION)))
    test_count = SAMPLES_PER_CATEGORY - train_count
    records = []
    for category in VISA_CATEGORIES:
        for split_type, count in (("train", train_count), ("test", test_count)):
            if count <= 0:
                continue
            cached = local_records(category, split_type, count)
            if len(cached) >= count:
                records.extend(cached)
                continue
            split_name = f"{category}.{split_type}"
            rows = fetch_rows(split_name, count)
            for row_index, row in enumerate(rows):
                image = row["image"]
                records.append(
                    {
                        "row_index": row_index,
                        "image_source": image["src"] if isinstance(image, dict) else image,
                        "local_path": None,
                        "category": category,
                        "family": FAMILY_BY_CATEGORY[category],
                        "split_name": split_name,
                        "split_type": "normal_reference" if split_type == "train" else "inspection_query",
                        "defect_label": int(row.get("label", 0)),
                    }
                )
    counts = Counter(record["category"] for record in records)
    print(f"Selected {len(records)} VisA inspection samples: {dict(counts)}", flush=True)
    return records


def add_visa_samples(dataset: hv.Dataset) -> None:
    existing_ids = {sample.id for sample in dataset.samples}
    media_dir = media_root()
    samples: list[hv.Sample] = []
    for record in select_visa_records():
        sample_id = safe_sample_id(record["category"], record["split_name"], record["row_index"], record["defect_label"])
        destination = Path(record["local_path"]) if record.get("local_path") else media_dir / f"{sample_id}.jpg"
        if record.get("image_source") is not None:
            save_image(record["image_source"], destination)
        metadata = {
            "sku": record["category"],
            "product_family": record["family"],
            "hierarchy": f"{readable(record['family'])} -> {readable(record['category'])}",
            "split": record["split_name"],
            "workflow_role": record["split_type"],
            "defect_status": "defect_or_test_item" if record["defect_label"] else "normal_reference",
            "source_dataset": "BrachioLab/visa",
        }
        samples.append(
                hv.Sample(
                id=sample_id,
                filepath=str(destination),
                label=record["category"],
                metadata=metadata,
            )
        )
    upserted, skipped = dataset.add_samples(samples, skip_existing=not FORCE_SAMPLE_REFRESH)
    updated = sum(1 for sample in samples if sample.id in existing_ids) if FORCE_SAMPLE_REFRESH else 0
    added = upserted - updated
    if skipped:
        print(f"Skipped {skipped} existing VisA sample rows.", flush=True)
    print(f"Prepared VisA samples ({added} added, {updated} updated).", flush=True)


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
        layout_key = dataset.compute_visualization(
            space_key=space_key,
            layout=spec["layout"],
            n_neighbors=20,
            min_dist=0.08,
            metric=spec["metric"],
        )
        spec["layout_key"] = layout_key
        layouts[spec["key"]] = layout_key
    return layouts


def build_dataset() -> tuple[hv.Dataset, dict[str, str]]:
    dataset = hv.Dataset(DATASET_NAME)
    add_visa_samples(dataset)
    layouts = ensure_layouts(dataset)
    return dataset, layouts


def model_panel_props(layouts: dict[str, str]) -> list[dict[str, Any]]:
    props = []
    for spec in MODEL_SPECS:
        layout_key = layouts[spec["key"]]
        props.append(
            {
                "key": spec["key"],
                "displayName": spec["display_name"],
                "buttonLabel": spec["button_label"],
                "layoutKey": layout_key,
            }
        )
    return props


def reference_summary(dataset: hv.Dataset, sample_id: str, model_key: str) -> dict[str, Any]:
    spec = next((item for item in MODEL_SPECS if item["key"] == model_key), None)
    if spec is None or spec.get("layout_key") is None:
        return {}
    query = dataset[sample_id]
    query_sku = query.metadata.get("sku")
    query_family = query.metadata.get("product_family")
    neighbors = dataset.find_similar(sample_id, k=10, layout_key=str(spec["layout_key"]))
    sku_hits = sum(1 for sample, _distance in neighbors if sample.metadata.get("sku") == query_sku)
    family_hits = sum(1 for sample, _distance in neighbors if sample.metadata.get("product_family") == query_family)
    normal_refs = sum(1 for sample, _distance in neighbors if sample.metadata.get("workflow_role") == "normal_reference")
    same_sku_normal_hits = 0
    same_sku_normal_precision_sum = 0.0
    ranked_neighbors = []
    for rank, (sample, distance) in enumerate(neighbors, 1):
        sku = sample.metadata.get("sku")
        family = sample.metadata.get("product_family")
        role = sample.metadata.get("workflow_role")
        is_same_sku_normal = sku == query_sku and role == "normal_reference"
        if is_same_sku_normal:
            same_sku_normal_hits += 1
            same_sku_normal_precision_sum += same_sku_normal_hits / rank
        ranked_neighbors.append(
            {
                "rank": rank,
                "id": sample.id,
                "sku": sku,
                "role": role,
                "sameSku": sku == query_sku,
                "sameFamily": family == query_family,
                "sameSkuNormal": is_same_sku_normal,
                "pipeFryumConfusion": query_sku == "fryum" and sku == "pipe_fryum",
                "distance": float(distance),
            }
        )
    same_sku_normal_ap = same_sku_normal_precision_sum / max(1, same_sku_normal_hits)
    pipe_fryum_confusions = sum(1 for item in ranked_neighbors if item["pipeFryumConfusion"])
    return {
        "skuHits": sku_hits,
        "familyHits": family_hits,
        "normalRefs": normal_refs,
        "sameSkuNormalAp10": round(same_sku_normal_ap, 3),
        "pipeFryumConfusions": pipe_fryum_confusions,
        "neighbors": ranked_neighbors,
        "total": len(neighbors),
    }


def build_examples(dataset: hv.Dataset) -> list[dict[str, Any]]:
    by_category: dict[str, Any] = {}
    for sample in dataset.samples:
        if sample.metadata.get("workflow_role") == "inspection_query":
            by_category.setdefault(sample.label, sample)
    examples = []
    for category, family_title in PREFERRED_EXAMPLES:
        sample = by_category.get(category)
        if sample is None:
            continue
        examples.append(
            {
                "id": category,
                "title": f"{readable(category)} inspection image",
                "family": family_title,
                "queryId": sample.id,
                "queryLabel": category,
                "summaries": {
                    "clip": {
                        "text": "Baseline: check whether visually similar wrong-line references enter the top neighborhood.",
                        **reference_summary(dataset, sample.id, "clip"),
                    },
                    "candidate": {
                        "text": "Inspect whether normal references and same-SKU examples stay ahead of wrong-line neighbors.",
                        **reference_summary(dataset, sample.id, "candidate"),
                    },
                },
            }
        )
    return examples


def category_strength_rows(dataset: hv.Dataset) -> list[dict[str, str]]:
    rows = []
    for category in VISA_CATEGORIES:
        queries = [
            sample
            for sample in dataset.samples
            if sample.metadata.get("workflow_role") == "inspection_query" and sample.metadata.get("sku") == category
        ]
        if not queries:
            continue
        clip_scores = [reference_summary(dataset, sample.id, "clip").get("sameSkuNormalAp10", 0.0) for sample in queries]
        candidate_scores = [
            reference_summary(dataset, sample.id, "candidate").get("sameSkuNormalAp10", 0.0) for sample in queries
        ]
        clip = sum(float(score) for score in clip_scores) / len(clip_scores)
        candidate = sum(float(score) for score in candidate_scores) / len(candidate_scores)
        delta = candidate - clip
        if delta <= 0:
            continue
        rows.append(
            {
                "category": category,
                "hyper3": f"{candidate:.3f}",
                "clip": f"{clip:.3f}",
                "delta": f"+{delta:.3f}",
            }
        )
    return sorted(rows, key=lambda row: float(row["delta"]), reverse=True)[:3]


def build_demo_view(dataset: hv.Dataset, layouts: dict[str, str]) -> hv.ui.View:
    scatter_panels = [
        hv.ui.Scatter(
            id=f"{spec['key']}-manufacturing-map",
            title=spec["panel_title"],
            layout_key=layouts[spec["key"]],
            geometry=spec["geometry"],
            layout_dimension=spec["layout_dimension"],
        )
        for spec in MODEL_SPECS
    ]
    return hv.ui.View(
        hv.ui.Horizontal(*scatter_panels),
        hv.ui.ExtensionPanel(
            id="manufacturing-reference-readout",
            extension="manufacturing-readout",
            panel="manufacturing-comparison",
            position="right",
            layout=hv.ui.PanelLayout(width=340, min_width=300),
            props={
                "models": model_panel_props(layouts),
                "examples": build_examples(dataset),
                "strengthRows": category_strength_rows(dataset),
            },
        ),
        hv.ui.Samples(
            id="manufacturing-neighbors",
            title="Step 2 - Retrieved References",
            position="bottom",
            layout=hv.ui.PanelLayout(height=220, min_height=180),
        ),
    )


def launch_demo(dataset: hv.Dataset, layouts: dict[str, str]) -> hv.Session:
    session = hv.launch(
        dataset,
        host=SPACE_HOST,
        port=SPACE_PORT,
        open_browser=False,
        workspace_id=WORKSPACE_ID,
        block=False,
    )
    print("Installing VisA demo extension...", flush=True)
    session.ui.add_extension(EXTENSION_DIR, workspace_id=WORKSPACE_ID)
    print("Applying VisA side-by-side demo view...", flush=True)
    session.ui.apply_view(build_demo_view(dataset, layouts), workspace_id=WORKSPACE_ID)
    session.ui.set_active_layout(layouts["clip"], workspace_id=WORKSPACE_ID)
    session.ui.set_selection([], workspace_id=WORKSPACE_ID)
    print(f"\nHyperView VisA manufacturing demo is running at {session.url}", flush=True)
    return session


def main() -> None:
    dataset, layouts = build_dataset()
    print("Layouts:", flush=True)
    for spec in MODEL_SPECS:
        print(f"  {spec['display_name']}: {layouts[spec['key']]}", flush=True)
    session = launch_demo(dataset, layouts)
    session.wait()


if __name__ == "__main__":
    main()
