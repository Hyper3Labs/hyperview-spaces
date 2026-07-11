#!/usr/bin/env python
"""DeepFashion text-search comparison demo for CLIP vs Hyper3-CLIP in HyperView."""

from __future__ import annotations

import os
import re
import time
from collections import Counter
from pathlib import Path
from typing import Any

from datasets import load_dataset
from PIL import Image, ImageOps

import hyperview as hv
from hyperview.core.sample import Sample

SPACE_DIR = Path(__file__).resolve().parent
SPACE_HOST = os.environ.get("HYPERVIEW_HOST", "127.0.0.1")
SPACE_PORT = int(os.environ.get("HYPERVIEW_PORT", "6262"))
WORKSPACE_ID = os.environ.get("HYPERVIEW_WORKSPACE_ID", "fashion-retail-search-v062-samples-visible")
DATASET_NAME = os.environ.get("HYPERVIEW_DATASET_NAME", "deepfashion_text_search_clip_hyper3clip")
EXTENSION_DIR = SPACE_DIR / ".hyperview" / "extensions" / "fashion-search-readout"

HF_DATASET = os.environ.get("DEEPFASHION_HF_DATASET", "Marqo/deepfashion-inshop")
HF_SPLIT = os.environ.get("DEEPFASHION_HF_SPLIT", "data")
SAMPLES_PER_CATEGORY = int(os.environ.get("DEEPFASHION_SAMPLES_PER_CATEGORY", "45"))
MAX_SAMPLES = int(os.environ.get("DEEPFASHION_MAX_SAMPLES", "700"))
IMAGE_MAX_SIZE = (768, 768)
FORCE_SAMPLE_REFRESH = os.environ.get("HYPERVIEW_DEEPFASHION_FORCE_REFRESH", "").lower() in {
    "1",
    "true",
    "yes",
}
ENABLE_CONTEXT_MAPS = os.environ.get("FASHION_ENABLE_CONTEXT_MAPS", "1").lower() in {
    "1",
    "true",
    "yes",
}
EMBEDDING_MAX_ATTEMPTS = max(1, int(os.environ.get("HYPERVIEW_EMBEDDING_MAX_ATTEMPTS", "4")))
EMBEDDING_RETRY_DELAY_SECONDS = float(os.environ.get("HYPERVIEW_EMBEDDING_RETRY_DELAY_SECONDS", "15"))
DEFAULT_EXAMPLE_ID = os.environ.get("FASHION_DEFAULT_EXAMPLE_ID", "light-denim-leggings")

MODEL_SPECS = [
    {
        "key": "clip",
        "display_name": os.environ.get("FASHION_BASELINE_DISPLAY_NAME", "CLIP"),
        "button_label": os.environ.get("FASHION_BASELINE_BUTTON_LABEL", "Inspect CLIP neighbors"),
        "provider": os.environ.get("FASHION_BASELINE_PROVIDER", "embed-anything"),
        "model": os.environ.get("FASHION_BASELINE_MODEL", "openai/clip-vit-base-patch32"),
        "layout": os.environ.get("FASHION_BASELINE_LAYOUT", "euclidean:2d"),
        "geometry": os.environ.get("FASHION_BASELINE_GEOMETRY", "euclidean"),
        "layout_dimension": int(os.environ.get("FASHION_BASELINE_LAYOUT_DIMENSION", "2")),
        "metric": os.environ.get("FASHION_BASELINE_METRIC", "cosine"),
        "panel_title": os.environ.get("FASHION_BASELINE_PANEL_TITLE", "CLIP - Fashion Catalog Map"),
    },
    {
        "key": "candidate",
        "display_name": os.environ.get("FASHION_CANDIDATE_DISPLAY_NAME", "Hyper3-CLIP"),
        "button_label": os.environ.get("FASHION_CANDIDATE_BUTTON_LABEL", "Inspect Hyper3-CLIP neighbors"),
        "provider": os.environ.get("FASHION_CANDIDATE_PROVIDER", "hyper-models"),
        "model": os.environ.get("FASHION_CANDIDATE_MODEL", "hyper3-clip-v0.5"),
        "layout": os.environ.get("FASHION_CANDIDATE_LAYOUT", "poincare:2d"),
        "geometry": os.environ.get("FASHION_CANDIDATE_GEOMETRY", "poincare"),
        "layout_dimension": int(os.environ.get("FASHION_CANDIDATE_LAYOUT_DIMENSION", "2")),
        "metric": os.environ.get("FASHION_CANDIDATE_METRIC", "cosine"),
        "panel_title": os.environ.get("FASHION_CANDIDATE_PANEL_TITLE", "Hyper3-CLIP - Fashion Catalog Map"),
    },
]

TEXT_SEARCH_EXAMPLES = [
    {
        "id": "light-denim-leggings",
        "title": "Light denim leggings",
        "targetItemId": "WOMEN_Leggings_id_00001867_02_3_back",
        "targetProduct": "WOMEN_Leggings_id_00001867_02",
        "targetTitle": "women's light denim leggings",
        "family": "Specific typed product search",
        "query": "women's light denim leggings with skinny fit, zipper details, five-pocket construction, pockets",
        "hyper3Rank": 1,
        "clipRank": 32,
        "hyper3Text": "Exact target is the first result.",
        "clipText": "Top results drift to dark denim, black, and similar blue leggings before the exact item appears.",
    },
    {
        "id": "olive-navy-pants",
        "title": "Olive and navy drawstring pants",
        "targetItemId": "MEN_Pants_id_00001468_03_6_flat",
        "targetProduct": "MEN_Pants_id_00001468_03",
        "targetTitle": "men's olive and navy drawstring pants",
        "family": "Specific typed product search",
        "query": "men's olive and navy pants with drawstring waist, pockets, striped pattern, knit fabric",
        "hyper3Rank": 1,
        "clipRank": 56,
        "hyper3Text": "Exact target is the first result.",
        "clipText": "CLIP ranks burgundy pants and visually similar pants before the requested product.",
    },
    {
        "id": "cream-blue-halter-blouse",
        "title": "Cream and blue halter blouse",
        "targetItemId": "WOMEN_Blouses_Shirts_id_00007161_02_1_front",
        "targetProduct": "WOMEN_Blouses_Shirts_id_00007161_02",
        "targetTitle": "cream and blue halter blouse",
        "family": "Attribute-heavy apparel search",
        "query": "women's cream and blue blouse with halter neckline, floral pattern, striped pattern, tribal print",
        "hyper3Rank": 4,
        "clipRank": 33,
        "hyper3Text": "Target views appear in the top 10.",
        "clipText": "CLIP retrieves broadly similar tops but misses the exact blouse in the first screen.",
    },
]

DEMO_RESULT_ITEM_IDS = {
    "MEN_Pants_id_00001468_03_6_flat",
    "MEN_Pants_id_00001468_04_6_flat",
    "MEN_Pants_id_00004045_03_2_side",
    "MEN_Pants_id_00004045_04_1_front",
    "MEN_Pants_id_00004045_09_3_back",
    "MEN_Pants_id_00004045_11_1_front",
    "MEN_Pants_id_00004045_11_2_side",
    "MEN_Pants_id_00004045_12_1_front",
    "MEN_Pants_id_00004045_12_2_side",
    "MEN_Pants_id_00004045_12_3_back",
    "MEN_Pants_id_00004045_12_7_additional",
    "MEN_Shirts_Polos_id_00007027_01_6_flat",
    "MEN_Sweaters_id_00005177_03_2_side",
    "MEN_Sweaters_id_00005177_03_3_back",
    "MEN_Sweaters_id_00005177_03_4_full",
    "WOMEN_Blouses_Shirts_id_00003641_01_1_front",
    "WOMEN_Blouses_Shirts_id_00006345_01_7_additional",
    "WOMEN_Blouses_Shirts_id_00007049_01_7_additional",
    "WOMEN_Blouses_Shirts_id_00007161_02_1_front",
    "WOMEN_Cardigans_id_00000521_02_3_back",
    "WOMEN_Denim_id_00000152_04_1_front",
    "WOMEN_Denim_id_00000152_04_2_side",
    "WOMEN_Denim_id_00002338_02_7_additional",
    "WOMEN_Denim_id_00002338_03_1_front",
    "WOMEN_Denim_id_00002338_03_3_back",
    "WOMEN_Denim_id_00002338_03_7_additional",
    "WOMEN_Denim_id_00005673_02_3_back",
    "WOMEN_Dresses_id_00006961_02_1_front",
    "WOMEN_Leggings_id_00001412_01_2_side",
    "WOMEN_Leggings_id_00001867_02_3_back",
    "WOMEN_Leggings_id_00002130_02_2_side",
    "WOMEN_Leggings_id_00003850_01_2_side",
    "WOMEN_Leggings_id_00003908_07_2_side",
    "WOMEN_Leggings_id_00003908_08_2_side",
    "WOMEN_Leggings_id_00004562_01_3_back",
    "WOMEN_Pants_id_00000053_02_1_front",
    "WOMEN_Pants_id_00001574_02_3_back",
    "WOMEN_Rompers_Jumpsuits_id_00004432_02_3_back",
    "WOMEN_Rompers_Jumpsuits_id_00004653_02_2_side",
    "WOMEN_Rompers_Jumpsuits_id_00005484_01_3_back",
    "WOMEN_Sweaters_id_00003304_01_1_front",
    "WOMEN_Sweaters_id_00003304_01_2_side",
    "WOMEN_Tees_Tanks_id_00000676_01_1_front",
    "WOMEN_Tees_Tanks_id_00000676_01_2_side",
}


def media_root() -> Path:
    root = Path(os.environ.get("HYPERVIEW_MEDIA_DIR", str(SPACE_DIR / "demo_data" / "media")))
    path = root / DATASET_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def product_key(item_id: str) -> str:
    return re.sub(r"_\d+_[A-Za-z]+$", "", str(item_id))


def safe_sample_id(item_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(item_id)).strip("_")[:96]


def readable(value: Any) -> str:
    text = str(value or "").replace("_", " ").replace("-", " ")
    return re.sub(r"\s+", " ", text).strip()


def save_image(image: Image.Image, destination: Path) -> None:
    if destination.exists() and destination.stat().st_size > 0 and not FORCE_SAMPLE_REFRESH:
        return
    tmp_path = destination.with_suffix(destination.suffix + ".tmp")
    image = ImageOps.exif_transpose(image).convert("RGB")
    image.thumbnail(IMAGE_MAX_SIZE, Image.Resampling.LANCZOS)
    image.save(tmp_path, format="JPEG", quality=92, optimize=True)
    tmp_path.replace(destination)


def select_deepfashion_records() -> list[dict[str, Any]]:
    print(f"Loading DeepFashion split {HF_SPLIT!r} from {HF_DATASET}...", flush=True)
    source = load_dataset(HF_DATASET, split=HF_SPLIT)
    required_products = {example["targetProduct"] for example in TEXT_SEARCH_EXAMPLES}
    required_item_ids = {example["targetItemId"] for example in TEXT_SEARCH_EXAMPLES} | DEMO_RESULT_ITEM_IDS
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    category_counts: Counter[str] = Counter()

    for index, row in enumerate(source):
        item_id = str(row["item_ID"])
        category = str(row.get("category2") or "unknown")
        product = product_key(item_id)
        required = product in required_products or item_id in required_item_ids
        balanced = category_counts[category] < SAMPLES_PER_CATEGORY and len(selected) < MAX_SAMPLES
        if not required and not balanced:
            continue
        if item_id in seen:
            continue
        selected.append({"index": index, **row})
        seen.add(item_id)
        category_counts[category] += 1

    missing = sorted(required_item_ids - seen)
    if missing:
        raise RuntimeError(f"Missing required demo items from DeepFashion: {missing}")
    print(f"Selected {len(selected)} DeepFashion images: {dict(category_counts)}", flush=True)
    return selected


def add_deepfashion_samples(dataset: hv.Dataset) -> None:
    existing_ids = {sample.id for sample in dataset.samples}
    media_dir = media_root()
    added = 0
    updated = 0
    skipped_existing = 0
    records = select_deepfashion_records()
    samples: list[Sample] = []

    for record in records:
        item_id = str(record["item_ID"])
        sample_id = safe_sample_id(item_id)
        existed = sample_id in existing_ids
        if existed and not FORCE_SAMPLE_REFRESH:
            skipped_existing += 1
            continue

        destination = media_dir / f"{sample_id}.jpg"
        save_image(record["image"], destination)
        category = readable(record.get("category2") or "unknown").lower()
        color = readable(record.get("color") or "unknown")
        metadata = {
            "item_id": item_id,
            "product_key": product_key(item_id),
            "gender": readable(record.get("category1") or "unknown"),
            "category": category,
            "subcategory": readable(record.get("category3") or "unknown"),
            "color": color,
            "description": readable(record.get("description") or ""),
            "text": readable(record.get("text") or ""),
            "source_dataset": HF_DATASET,
            "split": HF_SPLIT,
        }
        samples.append(
            Sample(
                id=sample_id,
                filepath=str(destination),
                label=category,
                metadata=metadata,
            )
        )
        if existed:
            updated += 1
        else:
            existing_ids.add(sample_id)
            added += 1

    dataset.add_samples(samples, skip_existing=False)

    if skipped_existing:
        print(f"Skipped {skipped_existing} existing DeepFashion sample rows.", flush=True)
    print(f"Prepared DeepFashion samples ({added} added, {updated} updated).", flush=True)


def compute_embeddings_with_retry(dataset: hv.Dataset, spec: dict[str, Any]) -> str:
    for attempt in range(1, EMBEDDING_MAX_ATTEMPTS + 1):
        try:
            return dataset.compute_embeddings(
                model=spec["model"],
                provider=spec["provider"],
                batch_size=32,
                show_progress=True,
            )
        except BaseException as exc:
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            if attempt >= EMBEDDING_MAX_ATTEMPTS:
                raise
            delay = EMBEDDING_RETRY_DELAY_SECONDS * attempt
            print(
                f"Embedding load failed for {spec['display_name']} "
                f"({type(exc).__name__}: {exc}). Retrying in {delay:.0f}s "
                f"({attempt + 1}/{EMBEDDING_MAX_ATTEMPTS})...",
                flush=True,
            )
            time.sleep(delay)
    raise RuntimeError(f"Failed to compute embeddings for {spec['display_name']}")


def ensure_layouts(dataset: hv.Dataset) -> dict[str, str]:
    layouts: dict[str, str] = {}
    for spec in MODEL_SPECS:
        print(f"Ensuring {spec['display_name']} embeddings...", flush=True)
        space_key = compute_embeddings_with_retry(dataset, spec)
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
    add_deepfashion_samples(dataset)
    if ENABLE_CONTEXT_MAPS:
        layouts = ensure_layouts(dataset)
    else:
        layouts = {}
    return dataset, layouts


def model_panel_props(layouts: dict[str, str]) -> list[dict[str, Any]]:
    props = []
    for spec in MODEL_SPECS:
        layout_key = layouts.get(spec["key"])
        props.append(
            {
                "key": spec["key"],
                "displayName": spec["display_name"],
                "buttonLabel": spec["button_label"],
                "layoutKey": layout_key,
            }
        )
    return props


def neighbor_summary(dataset: hv.Dataset, sample_id: str, model_key: str) -> dict[str, Any]:
    spec = next((item for item in MODEL_SPECS if item["key"] == model_key), None)
    if spec is None:
        return {}
    query = dataset[sample_id]
    layout_key = spec.get("layout_key")
    if layout_key is None:
        return {}
    neighbors = dataset.find_similar(sample_id, k=10, layout_key=str(layout_key))
    query_product = query.metadata.get("product_key")
    query_category = query.metadata.get("category")
    product_hits = sum(1 for sample, _distance in neighbors if sample.metadata.get("product_key") == query_product)
    category_hits = sum(1 for sample, _distance in neighbors if sample.metadata.get("category") == query_category)
    return {"productHits": product_hits, "categoryHits": category_hits, "total": len(neighbors)}


def build_examples(dataset: hv.Dataset) -> list[dict[str, Any]]:
    examples = []
    for item in TEXT_SEARCH_EXAMPLES:
        sample_id = safe_sample_id(item["targetItemId"])
        if sample_id not in {sample.id for sample in dataset.samples}:
            continue
        examples.append(
            {
                "id": item["id"],
                "title": item["title"],
                "family": item["family"],
                "query": item["query"],
                "queryId": sample_id,
                "targetTitle": item["targetTitle"],
                "summaries": {
                    "clip": {
                        "rank": item["clipRank"],
                        "text": item["clipText"],
                        **neighbor_summary(dataset, sample_id, "clip"),
                    },
                    "candidate": {
                        "rank": item["hyper3Rank"],
                        "text": item["hyper3Text"],
                        **neighbor_summary(dataset, sample_id, "candidate"),
                    },
                },
            }
        )
    return examples


def build_demo_view(dataset: hv.Dataset, layouts: dict[str, str]) -> hv.ui.View:
    shared_props = {
        "models": model_panel_props(layouts),
        "examples": build_examples(dataset),
        "initialExampleId": DEFAULT_EXAMPLE_ID,
        "metrics": {
            "typedQueryCount": 180,
            "typedCandidateImages": 1120,
            "hit10Hyper3Only": 23,
            "hit10ClipOnly": 19,
            "strongHyper3Wins": 13,
            "strongClipWins": 9,
            "imageRetrievalMapHyper3": 0.407,
            "imageRetrievalMapClip": 0.240,
            "typedHit1Hyper3": 0.244,
            "typedHit1Clip": 0.233,
            "typedHit10Hyper3": 0.572,
            "typedHit10Clip": 0.550,
            "typedCategoryP10Hyper3": 0.594,
            "typedCategoryP10Clip": 0.561,
            "typedMrrHyper3": 0.358,
            "typedMrrClip": 0.344,
        },
    }
    results_panel = hv.ui.ExtensionPanel(
        id="fashion-ranked-results",
        title="Ranked Search Results",
        extension="fashion-search-readout",
        panel="fashion-comparison",
        position="center",
        layout=hv.ui.PanelLayout(
            width=int(os.environ.get("FASHION_RESULTS_WIDTH", "620")),
            min_width=500,
        ),
        props={
            **shared_props,
            "mode": "results",
        },
    )
    samples_panel = hv.ui.Samples(
        id="grid",
        title="Samples",
        position="center",
        reference_panel_id="fashion-ranked-results",
        direction="right",
        layout=hv.ui.PanelLayout(
            width=int(os.environ.get("FASHION_SAMPLES_WIDTH", "660")),
            min_width=420,
            min_height=480,
        ),
    )

    if not ENABLE_CONTEXT_MAPS:
        return hv.ui.View(results_panel, samples_panel, active_panel="fashion-ranked-results")

    clip_spec = MODEL_SPECS[0]
    candidate_spec = MODEL_SPECS[1]
    map_layout = hv.ui.PanelLayout(
        height=int(os.environ.get("FASHION_MAP_HEIGHT", "180")),
        min_height=150,
        min_width=220,
    )
    clip_map = hv.ui.Scatter(
        id="fashion-map-clip",
        title="Context Map: CLIP",
        layout_key=layouts["clip"],
        position="center",
        reference_panel_id="grid",
        direction="below",
        geometry=clip_spec["geometry"],
        layout_dimension=clip_spec["layout_dimension"],
        layout=map_layout,
    )
    candidate_map = hv.ui.Scatter(
        id="fashion-map-hyper3",
        title="Context Map: Hyper3",
        layout_key=layouts["candidate"],
        position="center",
        reference_panel_id="fashion-map-clip",
        direction="right",
        geometry=candidate_spec["geometry"],
        layout_dimension=candidate_spec["layout_dimension"],
        layout=map_layout,
    )
    return hv.ui.View(
        results_panel,
        samples_panel,
        clip_map,
        candidate_map,
        active_panel="fashion-ranked-results",
    )


def initial_target_sample_id() -> str | None:
    example = next(
        (item for item in TEXT_SEARCH_EXAMPLES if item["id"] == DEFAULT_EXAMPLE_ID),
        TEXT_SEARCH_EXAMPLES[0] if TEXT_SEARCH_EXAMPLES else None,
    )
    if example is None:
        return None
    return safe_sample_id(example["targetItemId"])


def launch_demo(dataset: hv.Dataset, layouts: dict[str, str]) -> hv.Session:
    session = hv.launch(
        dataset,
        host=SPACE_HOST,
        port=SPACE_PORT,
        open_browser=False,
        workspace_id=WORKSPACE_ID,
        block=False,
    )
    print("Installing DeepFashion demo extension...", flush=True)
    session.ui.add_extension(EXTENSION_DIR, workspace_id=WORKSPACE_ID)
    print("Applying DeepFashion retail search demo view...", flush=True)
    session.ui.apply_view(build_demo_view(dataset, layouts), workspace_id=WORKSPACE_ID)
    if ENABLE_CONTEXT_MAPS and layouts:
        session.ui.set_active_layout(layouts["clip"], workspace_id=WORKSPACE_ID)
    sample_id = initial_target_sample_id()
    if sample_id:
        session.ui.set_selection([sample_id], workspace_id=WORKSPACE_ID)
    print(f"\nHyperView DeepFashion text-search demo is running at {session.url}", flush=True)
    if ENABLE_CONTEXT_MAPS:
        print("   Samples and nearest neighbors stay visible; scatter maps use the actual CLIP/Hyper3 layouts.", flush=True)
    else:
        print("   Samples stay visible; ranked text-search results are the main demo.", flush=True)
    return session


def main() -> None:
    dataset, layouts = build_dataset()
    if layouts:
        print("Layouts:", flush=True)
        for spec in MODEL_SPECS:
            print(f"  {spec['display_name']}: {layouts[spec['key']]}", flush=True)
    else:
        print("Context maps disabled; skipping embedding/layout startup.", flush=True)
    session = launch_demo(dataset, layouts)
    session.wait()


if __name__ == "__main__":
    main()
