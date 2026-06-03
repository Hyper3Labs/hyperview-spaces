#!/usr/bin/env python
"""ABO product-catalog comparison demo for CLIP vs HyCoCLIP in HyperView."""

from __future__ import annotations

import os
import re
import urllib.request
from inspect import signature
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from datasets import load_dataset
from PIL import Image, ImageOps

import hyperview as hv


SPACE_DIR = Path(__file__).resolve().parent
SPACE_HOST = os.environ.get("HYPERVIEW_HOST", "127.0.0.1")
SPACE_PORT = int(os.environ.get("HYPERVIEW_PORT", "6262"))
WORKSPACE_ID = os.environ.get("HYPERVIEW_WORKSPACE_ID", "abo-catalog-clip-hycoclip")
DATASET_NAME = os.environ.get("HYPERVIEW_DATASET_NAME", "abo_catalog_clip_hycoclip_side_by_side")
EXTENSION_DIR = SPACE_DIR / ".hyperview" / "extensions" / "abo-catalog-readout"

HF_ABO_DATASET = os.environ.get("ABO_HF_DATASET", "hyper3labs/amazon-berkeley-objects")
HF_ABO_CONFIG = os.environ.get("ABO_HF_CONFIG", "listings")
HF_ABO_SPLIT = os.environ.get("ABO_HF_SPLIT", "train")

MAX_PRODUCT_TYPES = int(os.environ.get("ABO_MAX_PRODUCT_TYPES", "20"))
SAMPLES_PER_PRODUCT_TYPE = int(os.environ.get("ABO_SAMPLES_PER_PRODUCT_TYPE", "25"))
MIN_PRODUCT_TYPE_COUNT = int(os.environ.get("ABO_MIN_PRODUCT_TYPE_COUNT", "10"))
IMAGE_MAX_SIZE = (768, 768)
FORCE_SAMPLE_REFRESH = os.environ.get("HYPERVIEW_ABO_FORCE_REFRESH", "").lower() in {
    "1",
    "true",
    "yes",
}

ALLOWED_COUNTRIES = set(
    item.strip()
    for item in os.environ.get("ABO_ALLOWED_COUNTRIES", "US,GB,AU,CA,AE,SG,IN").split(",")
    if item.strip()
)

MODEL_SPECS = [
    {
        "key": "clip",
        "display_name": os.environ.get("ABO_BASELINE_DISPLAY_NAME", "CLIP"),
        "button_label": os.environ.get("ABO_BASELINE_BUTTON_LABEL", "CLIP query"),
        "provider": os.environ.get("ABO_BASELINE_PROVIDER", "embed-anything"),
        "model": os.environ.get("ABO_BASELINE_MODEL", "openai/clip-vit-base-patch32"),
        "layout": os.environ.get("ABO_BASELINE_LAYOUT", "euclidean:2d"),
        "geometry": os.environ.get("ABO_BASELINE_GEOMETRY", "euclidean"),
        "layout_dimension": int(os.environ.get("ABO_BASELINE_LAYOUT_DIMENSION", "2")),
        "metric": os.environ.get("ABO_BASELINE_METRIC", "cosine"),
        "panel_title": os.environ.get("ABO_BASELINE_PANEL_TITLE", "CLIP - Euclidean Catalog Map"),
    },
    {
        "key": "candidate",
        "display_name": os.environ.get("ABO_CANDIDATE_DISPLAY_NAME", "HyCoCLIP"),
        "button_label": os.environ.get("ABO_CANDIDATE_BUTTON_LABEL", "HyCoCLIP query"),
        "provider": os.environ.get("ABO_CANDIDATE_PROVIDER", "hyper-models"),
        "model": os.environ.get("ABO_CANDIDATE_MODEL", "hycoclip-vit-s"),
        "layout": os.environ.get("ABO_CANDIDATE_LAYOUT", "poincare:2d"),
        "geometry": os.environ.get("ABO_CANDIDATE_GEOMETRY", "poincare"),
        "layout_dimension": int(os.environ.get("ABO_CANDIDATE_LAYOUT_DIMENSION", "2")),
        "metric": os.environ.get("ABO_CANDIDATE_METRIC", "cosine"),
        "panel_title": os.environ.get("ABO_CANDIDATE_PANEL_TITLE", "HyCoCLIP - Poincare Catalog Map"),
    },
]

DEMO_EXAMPLES = [
    {
        "id": "lighting",
        "title": "Lighting fixture",
        "family": "Lighting",
        "queryId": "B07HK5WXQP_510lSNJKiyL",
        "queryLabel": "LIGHT_FIXTURE",
        "summaries": {
            "clip": {
                "hits": 2,
                "text": "Also returns earrings, home decor, bedding, kitchen, sandals.",
            },
            "candidate": {
                "hits": 10,
                "text": "Returns fixtures and lamps.",
            },
        },
    },
    {
        "id": "chandelier",
        "title": "Chandelier-style fixture",
        "family": "Lighting",
        "queryId": "B07MF1RNWQ_51Vei4EHzBL",
        "queryLabel": "LIGHT_FIXTURE",
        "summaries": {
            "clip": {
                "hits": 2,
                "text": "Also returns earrings, necklace-like jewelry, table.",
            },
            "candidate": {
                "hits": 10,
                "text": "Returns light fixtures first, then lamps.",
            },
        },
    },
    {
        "id": "footwear",
        "title": "Sandal",
        "family": "Footwear",
        "queryId": "B07WHRRNQK_61_LTvw9qDL",
        "queryLabel": "SANDAL",
        "summaries": {
            "clip": {
                "hits": 6,
                "text": "Also returns accessories, handbags.",
            },
            "candidate": {
                "hits": 10,
                "text": "Returns sandals with nearby shoes.",
            },
        },
    },
]


def media_root() -> Path:
    root = Path(os.environ.get("HYPERVIEW_MEDIA_DIR", str(SPACE_DIR / "demo_data" / "media")))
    path = root / DATASET_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def readable_product_type(label: str | None) -> str:
    if not label:
        return ""
    text = label.replace("_", " ").replace("-", " ").lower()
    return re.sub(r"\s+", " ", text).strip()


def safe_sample_id(item_id: str, image_id: str) -> str:
    raw = f"{item_id}_{image_id}"
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", raw).strip("_")[:96]


def select_balanced(records: list[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        grouped[record["product_type"]].append(record)

    eligible = [
        (ptype, items)
        for ptype, items in grouped.items()
        if len(items) >= MIN_PRODUCT_TYPE_COUNT
    ]
    eligible.sort(key=lambda item: (-len(item[1]), item[0]))

    selected: list[dict] = []
    for _ptype, items in eligible[:MAX_PRODUCT_TYPES]:
        selected.extend(items[:SAMPLES_PER_PRODUCT_TYPE])
    return selected


def download_product_image(record: dict, destination: Path) -> bool:
    if destination.exists() and destination.stat().st_size > 0:
        return True

    url = record.get("image_url")
    if not url:
        return False

    raw_path = destination.with_suffix(destination.suffix + ".download")
    tmp_path = destination.with_suffix(destination.suffix + ".tmp")
    try:
        urllib.request.urlretrieve(url, raw_path)
        image = ImageOps.exif_transpose(Image.open(raw_path)).convert("RGB")
        image.thumbnail(IMAGE_MAX_SIZE, Image.Resampling.LANCZOS)
        image.save(tmp_path, format="JPEG", quality=90, optimize=True)
        tmp_path.replace(destination)
        return True
    except Exception as exc:
        print(f"Skipping image {url}: {exc}", flush=True)
        return False
    finally:
        raw_path.unlink(missing_ok=True)
        tmp_path.unlink(missing_ok=True)


def hf_catalog_records() -> list[dict]:
    print(f"Loading ABO listings from Hugging Face dataset {HF_ABO_DATASET}...", flush=True)
    source = load_dataset(HF_ABO_DATASET, HF_ABO_CONFIG, split=HF_ABO_SPLIT)

    records = []
    for row in source:
        if ALLOWED_COUNTRIES and row.get("country") not in ALLOWED_COUNTRIES:
            continue
        if not row.get("title") or not row.get("product_type") or not row.get("main_image_id"):
            continue
        if not row.get("department") or not row.get("main_image_url"):
            continue

        records.append(
            {
                "item_id": row.get("item_id"),
                "title": row.get("title"),
                "product_type": row.get("product_type"),
                "product_type_readable": row.get("product_type_readable")
                or readable_product_type(row.get("product_type")),
                "department": row.get("department"),
                "country": row.get("country"),
                "brand": row.get("brand"),
                "color": row.get("color"),
                "style": row.get("style"),
                "image_id": row.get("main_image_id"),
                "image_url": row.get("main_image_url"),
                "source": HF_ABO_DATASET,
            }
        )
    return records


def prepare_catalog_records() -> list[dict]:
    records = select_balanced(hf_catalog_records())
    print(
        f"Selected {len(records)} ABO products across "
        f"{len({record['product_type'] for record in records})} product types.",
        flush=True,
    )
    return records


def add_abo_samples(dataset: hv.Dataset) -> None:
    existing_ids = {sample.id for sample in dataset.samples}
    media_dir = media_root()
    added = 0
    updated = 0
    skipped = 0
    product_counts: Counter[str] = Counter()
    records = prepare_catalog_records()
    expected_ids = {
        safe_sample_id(str(record["item_id"]), str(record["image_id"])) for record in records
    }
    missing_ids = expected_ids - existing_ids
    missing_media = [
        sample_id for sample_id in expected_ids if not (media_dir / f"{sample_id}.jpg").exists()
    ]

    if not FORCE_SAMPLE_REFRESH and not missing_ids and not missing_media:
        product_counts.update(record["product_type"] for record in records)
        print(
            f"ABO samples already prepared ({len(records)} products). "
            "Set HYPERVIEW_ABO_FORCE_REFRESH=1 to rebuild samples.",
            flush=True,
        )
        print(f"Product-type counts: {dict(product_counts)}", flush=True)
        return

    for index, record in enumerate(records, start=1):
        sample_id = safe_sample_id(str(record["item_id"]), str(record["image_id"]))
        destination = media_dir / f"{sample_id}.jpg"
        if not download_product_image(record, destination):
            skipped += 1
            continue

        sample_exists = sample_id in existing_ids

        metadata = dict(record)
        metadata["hierarchy"] = f"{record['department']} -> {record['product_type_readable']}"

        dataset.add_image(
            str(destination),
            label=record["product_type"],
            metadata=metadata,
            sample_id=sample_id,
        )
        if sample_exists:
            updated += 1
        else:
            existing_ids.add(sample_id)
            added += 1
        product_counts[record["product_type"]] += 1

        if index == 1 or index % 50 == 0 or index == len(records):
            print(
                f"Prepared {index}/{len(records)} products "
                f"({added} added, {updated} updated, {skipped} skipped).",
                flush=True,
            )

    print(f"Product-type counts: {dict(product_counts)}", flush=True)


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


def build_dataset() -> tuple[hv.Dataset, dict[str, str]]:
    dataset = hv.Dataset(DATASET_NAME)
    add_abo_samples(dataset)
    layouts = ensure_layouts(dataset)
    return dataset, layouts


def model_panel_props(layouts: dict[str, str]) -> list[dict[str, Any]]:
    props = []
    for spec in MODEL_SPECS:
        props.append(
            {
                "key": spec["key"],
                "displayName": spec["display_name"],
                "buttonLabel": spec["button_label"],
                "layoutKey": layouts[spec["key"]],
            }
        )
    return props


def supported_kwargs(func: Any, kwargs: dict[str, Any]) -> dict[str, Any]:
    params = signature(func).parameters
    return {key: value for key, value in kwargs.items() if key in params}


def build_demo_view(layouts: dict[str, str]) -> hv.ui.View:
    scatter_panels = [
        hv.ui.Scatter(
            id=f"{spec['key']}-catalog-map",
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
            id="catalog-hierarchy-readout",
            extension="abo-catalog-readout",
            panel="catalog-comparison",
            position="right",
            props={
                "models": model_panel_props(layouts),
                "examples": DEMO_EXAMPLES,
            },
        ),
    )


def launch_demo(dataset: hv.Dataset, layouts: dict[str, str]) -> hv.Session:
    launch_kwargs = {
        "host": SPACE_HOST,
        "port": SPACE_PORT,
        "open_browser": False,
        "workspace_id": WORKSPACE_ID,
        "block": False,
    }

    session = hv.launch(dataset, **supported_kwargs(hv.launch, launch_kwargs))
    print("Installing ABO demo extension...", flush=True)
    session.ui.add_extension(
        EXTENSION_DIR,
        **supported_kwargs(session.ui.add_extension, {"workspace_id": WORKSPACE_ID}),
    )
    print("Applying ABO side-by-side demo view...", flush=True)
    session.ui.apply_view(
        build_demo_view(layouts),
        **supported_kwargs(session.ui.apply_view, {"workspace_id": WORKSPACE_ID}),
    )
    print("Clearing initial query state...", flush=True)
    session.ui.set_active_layout(
        None,
        **supported_kwargs(session.ui.set_active_layout, {"workspace_id": WORKSPACE_ID}),
    )
    session.ui.set_selection(
        [],
        **supported_kwargs(session.ui.set_selection, {"workspace_id": WORKSPACE_ID}),
    )
    print(f"\nHyperView ABO catalog demo is running at {session.url}", flush=True)
    model_names = " and ".join(spec["display_name"] for spec in MODEL_SPECS)
    print(f"   {model_names} pinned scatter panels are added side by side.", flush=True)
    print("   Press Ctrl+C to stop.\n", flush=True)
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
