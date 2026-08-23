#!/usr/bin/env python
"""ABO product-catalog comparison demo for CLIP vs Hyper3-CLIP in HyperView."""

from __future__ import annotations

import os
import re
import shutil
import urllib.request
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any

from datasets import load_dataset
from PIL import Image, ImageOps

import hyperview as hv

SPACE_DIR = Path(__file__).resolve().parent
SPACE_HOST = os.environ.get("HYPERVIEW_HOST", "127.0.0.1")
SPACE_PORT = int(os.environ.get("HYPERVIEW_PORT", "6262"))
WORKSPACE_ID = os.environ.get("HYPERVIEW_WORKSPACE_ID", "abo-catalog-clip-hyper3clip-split")
DATASET_NAME = os.environ.get("HYPERVIEW_DATASET_NAME", "abo_catalog_clip_hyper3clip_side_by_side")
EXTENSION_DIR = SPACE_DIR / ".hyperview" / "extensions" / "abo-catalog-readout"

HF_ABO_DATASET = os.environ.get("ABO_HF_DATASET", "hyper3labs/amazon-berkeley-objects")
HF_ABO_CONFIG = os.environ.get("ABO_HF_CONFIG", "listings")
HF_ABO_SPLIT = os.environ.get("ABO_HF_SPLIT", "train")

MAX_PRODUCT_TYPES = int(os.environ.get("ABO_MAX_PRODUCT_TYPES", "20"))
SAMPLES_PER_PRODUCT_TYPE = int(os.environ.get("ABO_SAMPLES_PER_PRODUCT_TYPE", "4"))
MIN_PRODUCT_TYPE_COUNT = int(os.environ.get("ABO_MIN_PRODUCT_TYPE_COUNT", "10"))
IMAGE_MAX_SIZE = (768, 768)
IMAGE_DOWNLOAD_TIMEOUT_SEC = int(os.environ.get("ABO_IMAGE_DOWNLOAD_TIMEOUT_SEC", "20"))
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
        "provider": os.environ.get("ABO_BASELINE_PROVIDER", "embed-anything"),
        "model": os.environ.get("ABO_BASELINE_MODEL", "openai/clip-vit-base-patch32"),
        "layout": os.environ.get("ABO_BASELINE_LAYOUT", "euclidean:2d"),
        "geometry": os.environ.get("ABO_BASELINE_GEOMETRY", "euclidean"),
        "layout_dimension": int(os.environ.get("ABO_BASELINE_LAYOUT_DIMENSION", "2")),
        "metric": os.environ.get("ABO_BASELINE_METRIC", "cosine"),
        "panel_title": os.environ.get("ABO_BASELINE_PANEL_TITLE", "CLIP product neighborhood"),
    },
    {
        "key": "candidate",
        "display_name": os.environ.get("ABO_CANDIDATE_DISPLAY_NAME", "Hyper3-CLIP"),
        "provider": os.environ.get("ABO_CANDIDATE_PROVIDER", "hyper-models"),
        "model": os.environ.get("ABO_CANDIDATE_MODEL", "hyper3-clip-v0.5"),
        "layout": os.environ.get("ABO_CANDIDATE_LAYOUT", "poincare:2d"),
        "geometry": os.environ.get("ABO_CANDIDATE_GEOMETRY", "poincare"),
        "layout_dimension": int(os.environ.get("ABO_CANDIDATE_LAYOUT_DIMENSION", "2")),
        "metric": os.environ.get("ABO_CANDIDATE_METRIC", "cosine"),
        "panel_title": os.environ.get(
            "ABO_CANDIDATE_PANEL_TITLE", "Hyper3-CLIP product neighborhood"
        ),
    },
]

DEMO_EXAMPLES = [
    {
        "id": "lighting",
        "mode": "image-neighborhood",
        "title": "Lighting fixture",
        "family": "Lighting",
        "guide": "Look for category drift: the same fixture should retrieve lights and lamps, not jewelry, shoes, or office products.",
        "queryId": "B07HK5WXQP_510lSNJKiyL",
        "queryLabel": "LIGHT_FIXTURE",
        "summaries": {
            "clip": {
                "hits": 4,
                "text": "Also returns earrings, sandals, office products, table, and sofa.",
            },
            "candidate": {
                "hits": 8,
                "text": "Mostly returns light fixtures and lamps.",
            },
        },
    },
    {
        "id": "chandelier",
        "mode": "image-neighborhood",
        "title": "Chandelier-style fixture",
        "family": "Lighting",
        "guide": "Look for hierarchy consistency: a chandelier-like fixture should stay inside the lighting neighborhood.",
        "queryId": "B07MF1RNWQ_51Vei4EHzBL",
        "queryLabel": "LIGHT_FIXTURE",
        "summaries": {
            "clip": {
                "hits": 4,
                "text": "Also returns earrings, accessories, office products, sofa, and home.",
            },
            "candidate": {
                "hits": 9,
                "text": "Mostly returns light fixtures and lamps.",
            },
        },
    },
    {
        "id": "footwear",
        "mode": "image-neighborhood",
        "title": "Sandal",
        "family": "Footwear",
        "guide": "Look for product-family boundaries: a sandal query should stay with sandals and shoes instead of handbags or home goods.",
        "queryId": "B07WHRRNQK_61_LTvw9qDL",
        "queryLabel": "SANDAL",
        "summaries": {
            "clip": {
                "hits": 3,
                "text": "Also returns handbags, jewelry, home goods, and accessories.",
            },
            "candidate": {
                "hits": 8,
                "text": "Mostly returns sandals, shoes, and boots.",
            },
        },
    },
    {
        "id": "grey-velvet-sofa",
        "mode": "text-to-product",
        "title": "Grey velvet sofa",
        "family": "Furniture / sofa",
        "query": "a product photo of grey velvet sofa: Frederick Mid-Century Modern Tufted Velvet Sofa Couch 77.5 W Grey, with metal, brass finish, wood, velvet upholstery, tufted",
        "targetTitle": "Rivet Frederick Mid-Century Modern Tufted Velvet Sofa Couch, 77.5 W, Grey",
        "targetSampleId": "B082VLTCM4_816VP-arPsL",
        "summaries": {
            "clip": {
                "rank": 20,
                "typePrecision": 0.7,
                "text": "CLIP stays in the sofa family, but the exact grey velvet target first appears at rank 20.",
            },
            "candidate": {
                "rank": 1,
                "typePrecision": 1.0,
                "text": "Hyper3 ranks the exact grey velvet target first and keeps the sofa set coherent.",
            },
        },
        "results": {
            "candidate": [
                {"id": "B082VLTCM4_816VP-arPsL", "rank": 1, "target": True},
                {"id": "B075X4VM73_81oPx1e8s_L", "rank": 2},
                {"id": "B07B4DBBPG_81dwblf8ogL", "rank": 3},
                {"id": "B07B4N29DG_81f4K_PGY-L", "rank": 4},
                {"id": "B075X2X4GY_81RzuSu3GLL", "rank": 5},
                {"id": "B082VLYCPC_71pzr1IKkIL", "rank": 6},
            ],
            "clip": [
                {"id": "B075X4VM73_81oPx1e8s_L", "rank": 1},
                {"id": "B082VLYCPC_71pzr1IKkIL", "rank": 2},
                {"id": "B075X4F56V_81Oy-OJ68KL", "rank": 3},
                {"id": "B07J2Z2BS5_81xPV3Ey1kL", "rank": 4},
                {"id": "B07J2R9TVF_A1cLonmKWvL", "rank": 5},
                {"id": "B075X4N4W9_81Z8ICQ9dUL", "rank": 6},
            ],
        },
    },
    {
        "id": "chrome-clear-glass-lamp",
        "mode": "text-to-product",
        "title": "Chrome clear-glass lamp",
        "family": "Home / lamp",
        "query": "a product photo of chrome with clear glass lamp: Ravenna Home Modern Round Table Lamp With LED Light Bulb - Chrome with Clear Glass, with table lamp, shade, metal, chrome finish, glass",
        "targetTitle": "Ravenna Home Modern Round Table Lamp With LED Light Bulb, Chrome with Clear Glass",
        "targetSampleId": "B07DBHB6B5_41SHn0jzPOL",
        "summaries": {
            "clip": {
                "rank": 31,
                "typePrecision": 0.7,
                "text": "CLIP recognizes lamps, but loses the requested chrome and clear-glass variant.",
            },
            "candidate": {
                "rank": 3,
                "typePrecision": 0.9,
                "text": "Hyper3 keeps the requested material and finish in the first few results.",
            },
        },
        "results": {
            "candidate": [
                {"id": "B001CD1GC0_71oh4KcBXJS", "rank": 1},
                {"id": "B07DBK2P2G_41TnBzn9tFL", "rank": 2},
                {"id": "B07DBHB6B5_41SHn0jzPOL", "rank": 3, "target": True},
                {"id": "B07DBJQC4S_41Jv3-wdZ3L", "rank": 4},
                {"id": "B07DTFBDTL_414HtkR3QZL", "rank": 5},
                {"id": "B0742DR7C2_81jtRdRtkPL", "rank": 6},
            ],
            "clip": [
                {"id": "B0742DR7C2_81jtRdRtkPL", "rank": 1},
                {"id": "B07374K538_71XEFMKYAGL", "rank": 2},
                {"id": "B001CD1GFM_61lepTd-EmS", "rank": 3},
                {"id": "B07DBK2P2G_41TnBzn9tFL", "rank": 4},
                {"id": "B07HKF59YX_41yzx8pNH6L", "rank": 5},
                {"id": "B07DT153M1_418DZS6SpTL", "rank": 6},
            ],
        },
    },
    {
        "id": "silver-mid-century-chair",
        "mode": "text-to-product",
        "title": "Silver mid-century chair",
        "family": "Furniture / chair",
        "query": "a product photo of silver mid-century modern chair: Logan Mid-Century Modern Dining Chair Set of 2 20.1 W Silver, with metal, silver tone, wood, mid-century style, modern style",
        "targetTitle": "Rivet Logan Mid-Century Modern Dining Chair, Set of 2, 20.1 W, Silver",
        "targetSampleId": "B0853L3W72_81mvF2gJy5L",
        "summaries": {
            "clip": {
                "rank": 28,
                "typePrecision": 0.3,
                "text": "CLIP drifts across nearby furniture and misses the exact silver chair until rank 28.",
            },
            "candidate": {
                "rank": 2,
                "typePrecision": 0.8,
                "text": "Hyper3 brings the requested chair variant to rank 2 while preserving product type.",
            },
        },
        "results": {
            "candidate": [
                {"id": "B0746HFVWY_91-Pi95Hy9L", "rank": 1},
                {"id": "B0853L3W72_81mvF2gJy5L", "rank": 2, "target": True},
                {"id": "B0853KZW7Z_71LY8AELiuL", "rank": 3},
                {"id": "B07B7B244W_71DNWOd-5bL", "rank": 4},
                {"id": "B07B7B3RVS_7196wQbG7KL", "rank": 5},
                {"id": "B075YN3HN9_81Rub8QQCvL", "rank": 6},
            ],
            "clip": [
                {"id": "B075YPTG2Q_710tYWSG8SL", "rank": 1},
                {"id": "B07HSB4WV6_71k4-giCqJL", "rank": 2},
                {"id": "B075YP3C53_81tDegaK7zL", "rank": 3},
                {"id": "B07HSLKKXG_81MUeTeLXVL", "rank": 4},
                {"id": "B07HSK3534_81WypZMR_2L", "rank": 5},
                {"id": "B0853KZW7Z_71LY8AELiuL", "rank": 6},
            ],
        },
    },
]

DEMO_QUERY_IDS = {example["queryId"] for example in DEMO_EXAMPLES if "queryId" in example}
DEMO_REQUIRED_SAMPLE_IDS = set(DEMO_QUERY_IDS)
for example in DEMO_EXAMPLES:
    target_sample_id = example.get("targetSampleId")
    if target_sample_id:
        DEMO_REQUIRED_SAMPLE_IDS.add(str(target_sample_id))
    for model_results in dict(example.get("results") or {}).values():
        for result in list(model_results or []):
            sample_id = result.get("id")
            if sample_id:
                DEMO_REQUIRED_SAMPLE_IDS.add(str(sample_id))


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
        (ptype, items) for ptype, items in grouped.items() if len(items) >= MIN_PRODUCT_TYPE_COUNT
    ]
    eligible.sort(key=lambda item: (-len(item[1]), item[0]))

    selected: list[dict] = []
    for _ptype, items in eligible[:MAX_PRODUCT_TYPES]:
        selected.extend(items[:SAMPLES_PER_PRODUCT_TYPE])

    selected_ids = {
        safe_sample_id(str(record["item_id"]), str(record["image_id"])) for record in selected
    }
    for record in records:
        sample_id = safe_sample_id(str(record["item_id"]), str(record["image_id"]))
        if sample_id in DEMO_REQUIRED_SAMPLE_IDS and sample_id not in selected_ids:
            selected.append(record)
            selected_ids.add(sample_id)
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
        with urllib.request.urlopen(url, timeout=IMAGE_DOWNLOAD_TIMEOUT_SEC) as response:
            with raw_path.open("wb") as handle:
                shutil.copyfileobj(response, handle)
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
        sample_id = safe_sample_id(str(row.get("item_id")), str(row.get("main_image_id")))
        required_demo_row = sample_id in DEMO_REQUIRED_SAMPLE_IDS
        if (not row.get("department") and not required_demo_row) or not row.get("main_image_url"):
            continue

        records.append(
            {
                "item_id": row.get("item_id"),
                "title": row.get("title"),
                "product_type": row.get("product_type"),
                "product_type_readable": row.get("product_type_readable")
                or readable_product_type(row.get("product_type")),
                "department": row.get("department") or "Catalog",
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
    selected_ids = {
        safe_sample_id(str(record["item_id"]), str(record["image_id"])) for record in records
    }
    missing_demo_ids = sorted(DEMO_REQUIRED_SAMPLE_IDS - selected_ids)
    if missing_demo_ids:
        raise RuntimeError(
            "ABO source is missing required proof rows: " + ", ".join(missing_demo_ids)
        )
    print(
        f"Selected {len(records)} ABO products across "
        f"{len({record['product_type'] for record in records})} product types.",
        flush=True,
    )
    return records


def rebase_cached_media_paths(dataset: hv.Dataset, media_dir: Path) -> int:
    """Keep persisted samples portable when the demo repository moves."""

    updates: list[hv.Sample] = []
    for sample in dataset.samples:
        destination = media_dir / f"{sample.id}.jpg"
        if destination.is_file() and sample.filepath != str(destination):
            updates.append(sample.model_copy(update={"filepath": str(destination)}))
    if updates:
        dataset.add_samples(updates)
    return len(updates)


def add_abo_samples(dataset: hv.Dataset) -> None:
    media_dir = media_root()
    rebased = rebase_cached_media_paths(dataset, media_dir)
    if rebased:
        print(f"Rebased {rebased} cached ABO media paths.", flush=True)
    existing_ids = {sample.id for sample in dataset.samples}
    skipped = 0
    product_counts: Counter[str] = Counter()
    samples: list[hv.Sample] = []
    records = prepare_catalog_records()
    expected_ids = {
        safe_sample_id(str(record["item_id"]), str(record["image_id"])) for record in records
    }
    missing_ids = expected_ids - existing_ids
    missing_media = [
        sample_id for sample_id in expected_ids if not (media_dir / f"{sample_id}.jpg").exists()
    ]

    if not FORCE_SAMPLE_REFRESH and not missing_ids and not missing_media:
        print(
            f"ABO samples already prepared ({len(records)} products). "
            "Existing sample rows will be reused.",
            flush=True,
        )

    for index, record in enumerate(records, start=1):
        sample_id = safe_sample_id(str(record["item_id"]), str(record["image_id"]))
        destination = media_dir / f"{sample_id}.jpg"
        if not download_product_image(record, destination):
            skipped += 1
            continue

        metadata = dict(record)
        metadata["hierarchy"] = f"{record['department']} -> {record['product_type_readable']}"

        samples.append(
            hv.Sample(
                id=sample_id,
                filepath=str(destination),
                label=record["product_type"],
                metadata=metadata,
            )
        )
        product_counts[record["product_type"]] += 1

        if index == 1 or index % 50 == 0 or index == len(records):
            print(
                f"Prepared media for {index}/{len(records)} products ({skipped} skipped).",
                flush=True,
            )

    prepared_ids = {sample.id for sample in samples}
    missing_demo_media = sorted(DEMO_REQUIRED_SAMPLE_IDS - prepared_ids)
    if missing_demo_media:
        raise RuntimeError(
            "Could not prepare media for required ABO proof rows: " + ", ".join(missing_demo_media)
        )

    upserted, skipped_existing = dataset.add_samples(
        samples,
        skip_existing=not FORCE_SAMPLE_REFRESH,
    )
    updated = (
        sum(1 for sample in samples if sample.id in existing_ids) if FORCE_SAMPLE_REFRESH else 0
    )
    added = upserted - updated
    if skipped_existing:
        print(f"Skipped {skipped_existing} existing ABO sample rows.", flush=True)
    print(
        f"Prepared ABO samples ({added} added, {updated} updated, {skipped} media skipped).",
        flush=True,
    )
    print(f"Product-type counts: {dict(product_counts)}", flush=True)


def _find_persisted_layout(
    spec: dict[str, Any],
    *,
    sample_count: int,
    spaces: list[Any],
    layouts: list[Any],
) -> Any | None:
    matching_space_keys = {
        space.space_key
        for space in spaces
        if (
            space.model_id == spec["model"]
            and dict(space.config or {}).get("provider") == spec["provider"]
            and dict(space.config or {}).get("modality") == "image"
            and int(getattr(space, "count", 0) or 0) == sample_count
        )
    }
    candidates = [
        layout
        for layout in layouts
        if layout.space_key in matching_space_keys
        and layout.method == "umap"
        and layout.geometry == spec["geometry"]
        and int(getattr(layout, "count", 0) or 0) == sample_count
        and dict(layout.params or {}).get("n_neighbors") == 20
        and dict(layout.params or {}).get("min_dist") == 0.08
        and dict(layout.params or {}).get("metric") == spec["metric"]
    ]
    candidates.sort(
        key=lambda layout: int(getattr(layout, "created_at", 0) or 0),
        reverse=True,
    )
    return candidates[0] if candidates else None


def ensure_layouts(dataset: hv.Dataset) -> dict[str, str]:
    layouts: dict[str, str] = {}
    sample_count = len(dataset.samples)
    persisted_spaces = dataset.list_spaces()
    persisted_layouts = dataset.list_layouts()

    for spec in MODEL_SPECS:
        persisted_layout = _find_persisted_layout(
            spec,
            sample_count=sample_count,
            spaces=persisted_spaces,
            layouts=persisted_layouts,
        )
        if persisted_layout is not None:
            layouts[spec["key"]] = persisted_layout.layout_key
            print(
                f"Using persisted {spec['display_name']} layout {persisted_layout.layout_key}.",
                flush=True,
            )
            continue

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
        layout_key = layouts[spec["key"]]
        props.append(
            {
                "key": spec["key"],
                "displayName": spec["display_name"],
                "layoutKey": layout_key,
                "rankPanelId": f"{spec['key']}-nearest-neighbours",
            }
        )
    return props


def _same_catalog_family(query_label: str, result_label: str | None) -> bool:
    """Return whether a neighbor belongs to the business-relevant product family."""

    family_labels = {
        "LIGHT_FIXTURE": {"LIGHT_FIXTURE", "LAMP"},
        "SANDAL": {"SANDAL", "SHOES", "BOOT"},
    }
    return result_label in family_labels.get(query_label, {query_label})


def demo_examples(dataset: hv.Dataset, layouts: dict[str, str]) -> list[dict[str, Any]]:
    """Materialize the guided comparison with real neighbors from this dataset."""

    available_ids = {sample.id for sample in dataset.samples}
    missing_demo_ids = sorted(DEMO_REQUIRED_SAMPLE_IDS - available_ids)
    if missing_demo_ids:
        raise RuntimeError(
            "ABO dataset is missing required proof rows: " + ", ".join(missing_demo_ids)
        )

    examples = deepcopy(DEMO_EXAMPLES)
    for example in examples:
        if example["mode"] != "image-neighborhood":
            continue

        example["results"] = {}
        for spec in MODEL_SPECS:
            neighbors = dataset.find_similar(
                example["queryId"],
                k=10,
                layout_key=layouts[spec["key"]],
            )
            rows = [
                {"id": sample.id, "rank": rank}
                for rank, (sample, _distance) in enumerate(neighbors, start=1)
            ]
            hits = sum(
                _same_catalog_family(example["queryLabel"], sample.label)
                for sample, _distance in neighbors
            )
            drift = [
                str(sample.label).replace("_", " ").lower()
                for sample, _distance in neighbors
                if not _same_catalog_family(example["queryLabel"], sample.label)
            ]
            distinct_drift = list(dict.fromkeys(drift))
            summary = example["summaries"][spec["key"]]
            summary["hits"] = hits
            summary["text"] = (
                "Keeps all ten results inside the intended product family."
                if hits == 10
                else f"Keeps {hits} of 10 in-family; drift includes "
                + ", ".join(distinct_drift[:3])
                + "."
            )
            example["results"][spec["key"]] = rows
    return examples


def panel_props(
    dataset: hv.Dataset,
    layouts: dict[str, str],
    *,
    examples: list[dict[str, Any]] | None = None,
    collection_id: str | None = None,
    text_collection_ids: dict[str, dict[str, str]] | None = None,
) -> dict[str, Any]:
    prepared_examples = deepcopy(
        examples if examples is not None else demo_examples(dataset, layouts)
    )
    for example in prepared_examples:
        if example.get("mode") != "text-to-product":
            continue
        example["collectionIds"] = dict(
            (text_collection_ids or {}).get(str(example["id"])) or {}
        )
    image_examples = [
        example for example in prepared_examples if example.get("mode") == "image-neighborhood"
    ]
    text_examples = [
        example for example in prepared_examples if example.get("mode") == "text-to-product"
    ]
    return {
        "models": model_panel_props(layouts),
        "examples": prepared_examples,
        "initialImageCaseId": str(image_examples[0]["id"]) if image_examples else None,
        "initialTextCaseId": str(text_examples[0]["id"]) if text_examples else None,
        "samplesPanelId": "samples",
        "collectionId": collection_id,
    }


def ranked_samples_props(
    spec: dict[str, Any],
    layout_key: str,
    anchor_sample_id: str,
) -> dict[str, Any]:
    return {
        "mode": "ranked",
        "labelField": "title",
        "rank": {
            "anchorSampleId": anchor_sample_id,
            "layoutKey": layout_key,
            "k": 10,
            "source": f"{spec['display_name']} image neighbours",
            "showDistance": False,
        },
    }


def ordered_result_ids(example: dict[str, Any], model_key: str) -> list[str]:
    return [
        str(result["id"])
        for result in sorted(
            example["results"][model_key], key=lambda result: int(result["rank"])
        )
    ]


def materialize_text_result_collections(
    session: hv.Session,
    examples: list[dict[str, Any]],
) -> dict[str, dict[str, str]]:
    collection_ids: dict[str, dict[str, str]] = {}
    for example in examples:
        if example.get("mode") != "text-to-product":
            continue
        case_id = str(example["id"])
        collection_ids[case_id] = {}
        for spec in MODEL_SPECS:
            model_key = str(spec["key"])
            result = session.ui.show_samples(
                ordered_result_ids(example, model_key),
                workspace_id=WORKSPACE_ID,
                focus=False,
                source=f"{spec['display_name']} · {example['title']} · Top 6",
            )
            collection_id = result.get("collection_id")
            if not collection_id:
                raise RuntimeError(
                    f"HyperView did not return a collection for {case_id}/{model_key}"
                )
            collection_ids[case_id][model_key] = str(collection_id)
    return collection_ids


def build_demo_view(
    dataset: hv.Dataset,
    layouts: dict[str, str],
    *,
    readout_props: dict[str, Any] | None = None,
) -> hv.ui.View:
    examples = readout_props.get("examples") if readout_props else None
    configured_examples = examples or panel_props(dataset, layouts)["examples"]
    default_example = next(
        example for example in configured_examples if example["mode"] == "image-neighborhood"
    )
    readout_panel = hv.ui.ExtensionPanel(
        id="catalog-hierarchy-readout",
        extension="abo-catalog-readout",
        panel="catalog-comparison",
        position="right",
        layout=hv.ui.PanelLayout(
            width=400,
            min_width=320,
            max_width=520,
            min_height=220,
        ),
        props=readout_props or panel_props(dataset, layouts),
    )

    ranked_panels = []
    for index, spec in enumerate(reversed(MODEL_SPECS)):
        panel_id = f"{spec['key']}-nearest-neighbours"
        ranked_panels.append(
            hv.ui.Samples(
                id=panel_id,
                title=f"{spec['display_name']} · Product results",
                position="center",
                reference_panel_id=ranked_panels[0].id if index else None,
                direction="right" if index else None,
                props=ranked_samples_props(
                    spec,
                    layouts[spec["key"]],
                    str(default_example["queryId"]),
                ),
                layout=hv.ui.PanelLayout(height=500, min_width=180, min_height=300),
            )
        )

    prepared_results = hv.ui.Samples(
        id="samples",
        title="Catalog browse",
        position="center",
        reference_panel_id=ranked_panels[0].id,
        direction="within",
        props={
            "mode": "results",
            "collectionId": (readout_props or {}).get("collectionId"),
            "labelField": "title",
        },
        layout=hv.ui.PanelLayout(min_width=180, min_height=220),
    )

    scatter_panels = []
    for spec in reversed(MODEL_SPECS):
        panel_id = f"{spec['key']}-catalog-map"
        scatter_panels.append(
            hv.ui.Scatter(
                id=panel_id,
                title=spec["panel_title"],
                layout_key=layouts[spec["key"]],
                geometry=spec["geometry"],
                layout_dimension=spec["layout_dimension"],
                reference_panel_id=f"{spec['key']}-nearest-neighbours",
                direction="within",
                layout=hv.ui.PanelLayout(min_width=180, min_height=300),
            )
        )
    return hv.ui.View(
        hv.ui.Horizontal(
            hv.ui.Tabs(
                ranked_panels[0],
                prepared_results,
                scatter_panels[0],
                active_tab=ranked_panels[0].id,
            ),
            hv.ui.Tabs(
                ranked_panels[1],
                scatter_panels[1],
                active_tab=ranked_panels[1].id,
            ),
            shares=[1, 1],
        ),
        readout_panel,
        active_panel="candidate-nearest-neighbours",
    )


def launch_demo(dataset: hv.Dataset, layouts: dict[str, str]) -> hv.Session:
    examples = demo_examples(dataset, layouts)
    session = hv.launch(
        dataset,
        host=SPACE_HOST,
        port=SPACE_PORT,
        open_browser=False,
        workspace_id=WORKSPACE_ID,
        block=False,
    )
    print("Installing ABO demo extension...", flush=True)
    session.ui.add_extension(EXTENSION_DIR, workspace_id=WORKSPACE_ID)
    session.ui.reset_samples(workspace_id=WORKSPACE_ID, focus=False)
    samples_state = session.ui.get_panel_state("samples", workspace_id=WORKSPACE_ID)
    samples_collection = dict(samples_state.get("state") or {}).get("collection_id")
    text_collection_ids = materialize_text_result_collections(session, examples)
    session.ui.reset_samples(workspace_id=WORKSPACE_ID, focus=False)
    readout_props = panel_props(
        dataset,
        layouts,
        examples=examples,
        collection_id=str(samples_collection) if samples_collection else None,
        text_collection_ids=text_collection_ids,
    )
    print("Applying ABO stacked comparison demo view...", flush=True)
    session.ui.apply_view(
        build_demo_view(dataset, layouts, readout_props=readout_props),
        workspace_id=WORKSPACE_ID,
    )
    default_image_example = next(
        example for example in examples if example["mode"] == "image-neighborhood"
    )
    default_text_example = next(
        example for example in examples if example["mode"] == "text-to-product"
    )
    session.ui.patch_panel_state(
        "catalog-hierarchy-readout",
        {
            "activeSection": "image",
            "activeImageCaseId": str(default_image_example["id"]),
            "activeTextCaseId": str(default_text_example["id"]),
        },
        workspace_id=WORKSPACE_ID,
        replace_state=True,
    )
    print("Presenting the default image-neighbour comparison...", flush=True)
    session.ui.set_active_layout(None, workspace_id=WORKSPACE_ID)
    session.ui.set_selection(
        [str(default_image_example["queryId"])], workspace_id=WORKSPACE_ID
    )
    session.ui.update_panel(
        "candidate-nearest-neighbours",
        workspace_id=WORKSPACE_ID,
        active=True,
    )
    print(f"\nHyperView ABO catalog demo is running at {session.url}", flush=True)
    model_names = " and ".join(spec["display_name"] for spec in MODEL_SPECS)
    print(
        f"   Built-in {model_names} neighbours, catalog maps, and shopper-request results are pinned.",
        flush=True,
    )
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
