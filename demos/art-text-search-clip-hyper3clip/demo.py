#!/usr/bin/env python
"""Artwork text-search comparison demo for CLIP vs Hyper3-CLIP in HyperView."""

from __future__ import annotations

import os
import re
import time
from collections import Counter
from itertools import islice
from pathlib import Path
from typing import Any

from datasets import load_dataset
from PIL import Image, ImageOps

import hyperview as hv

SPACE_DIR = Path(__file__).resolve().parent
SPACE_HOST = os.environ.get("HYPERVIEW_HOST", "127.0.0.1")
SPACE_PORT = int(os.environ.get("HYPERVIEW_PORT", "6262"))
WORKSPACE_ID = os.environ.get("HYPERVIEW_WORKSPACE_ID", "art-marketplace-search-v062")
DATASET_NAME = os.environ.get("HYPERVIEW_DATASET_NAME", "art_text_search_clip_hyper3clip")
EXTENSION_DIR = SPACE_DIR / ".hyperview" / "extensions" / "art-search-readout"

HF_DATASET = os.environ.get("ART_HF_DATASET", "Artificio/WikiArt")
HF_SPLIT = os.environ.get("ART_HF_SPLIT", "train")
HF_STREAMING = os.environ.get("ART_HF_STREAMING", "1").lower() in {"1", "true", "yes"}
MAX_SAMPLES = int(os.environ.get("ART_MAX_SAMPLES", "1200"))
MAX_SCAN_ROWS = int(os.environ.get("ART_MAX_SCAN_ROWS", "18000"))
SAMPLES_PER_GENRE = int(os.environ.get("ART_SAMPLES_PER_GENRE", "120"))
SAMPLES_PER_STYLE = int(os.environ.get("ART_SAMPLES_PER_STYLE", "90"))
IMAGE_MAX_SIZE = (768, 768)
FORCE_SAMPLE_REFRESH = os.environ.get("HYPERVIEW_ART_FORCE_REFRESH", "").lower() in {
    "1",
    "true",
    "yes",
}
ENABLE_CONTEXT_MAPS = os.environ.get("ART_ENABLE_CONTEXT_MAPS", "1").lower() in {
    "1",
    "true",
    "yes",
}
EMBEDDING_MAX_ATTEMPTS = max(1, int(os.environ.get("HYPERVIEW_EMBEDDING_MAX_ATTEMPTS", "4")))
EMBEDDING_RETRY_DELAY_SECONDS = float(os.environ.get("HYPERVIEW_EMBEDDING_RETRY_DELAY_SECONDS", "15"))
DEFAULT_EXAMPLE_ID = os.environ.get("ART_DEFAULT_EXAMPLE_ID", "blue-ship-hill")

ALLOWED_GENRES = {
    "animal painting",
    "battle painting",
    "cityscape",
    "figurative",
    "flower painting",
    "genre painting",
    "interior",
    "landscape",
    "marina",
    "mythological painting",
    "portrait",
    "religious painting",
    "sketch and study",
    "still life",
    "symbolic painting",
}

MODEL_SPECS = [
    {
        "key": "clip",
        "display_name": os.environ.get("ART_BASELINE_DISPLAY_NAME", "CLIP"),
        "button_label": os.environ.get("ART_BASELINE_BUTTON_LABEL", "Inspect CLIP neighborhood"),
        "provider": os.environ.get("ART_BASELINE_PROVIDER", "embed-anything"),
        "model": os.environ.get("ART_BASELINE_MODEL", "openai/clip-vit-base-patch32"),
        "layout": os.environ.get("ART_BASELINE_LAYOUT", "euclidean:2d"),
        "geometry": os.environ.get("ART_BASELINE_GEOMETRY", "euclidean"),
        "layout_dimension": int(os.environ.get("ART_BASELINE_LAYOUT_DIMENSION", "2")),
        "metric": os.environ.get("ART_BASELINE_METRIC", "cosine"),
        "panel_title": os.environ.get("ART_BASELINE_PANEL_TITLE", "CLIP - Artwork Search Map"),
    },
    {
        "key": "candidate",
        "display_name": os.environ.get("ART_CANDIDATE_DISPLAY_NAME", "Hyper3-CLIP"),
        "button_label": os.environ.get("ART_CANDIDATE_BUTTON_LABEL", "Inspect Hyper3-CLIP neighborhood"),
        "provider": os.environ.get("ART_CANDIDATE_PROVIDER", "hyper-models"),
        "model": os.environ.get("ART_CANDIDATE_MODEL", "hyper3-clip-v0.5"),
        "layout": os.environ.get("ART_CANDIDATE_LAYOUT", "poincare:2d"),
        "geometry": os.environ.get("ART_CANDIDATE_GEOMETRY", "poincare"),
        "layout_dimension": int(os.environ.get("ART_CANDIDATE_LAYOUT_DIMENSION", "2")),
        "metric": os.environ.get("ART_CANDIDATE_METRIC", "cosine"),
        "panel_title": os.environ.get("ART_CANDIDATE_PANEL_TITLE", "Hyper3-CLIP - Artwork Search Map"),
    },
]

TEXT_SEARCH_EXAMPLES = [
    {
        "id": "blue-ship-hill",
        "title": "Blue ship on a hill",
        "family": "Object + color + improbable setting",
        "query": "blue ship on a hill",
        "anchor_genres": ["marina", "landscape"],
        "anchor_styles": ["Romanticism", "Post-Impressionism", "Impressionism"],
    },
    {
        "id": "red-horse-snow",
        "title": "Red horse in snow",
        "family": "Animal + color + weather",
        "query": "red horse standing in white snow",
        "anchor_genres": ["animal painting", "landscape"],
        "anchor_styles": ["Expressionism", "Realism", "Romanticism"],
    },
    {
        "id": "gold-boat-moon",
        "title": "Gold boat under moon",
        "family": "Object + material/color + night setting",
        "query": "gold boat under a pale moon on dark water",
        "anchor_genres": ["marina", "landscape"],
        "anchor_styles": ["Symbolism", "Romanticism", "Impressionism"],
    },
    {
        "id": "white-dress-garden",
        "title": "White dress in garden",
        "family": "Clothing + color + outdoor setting",
        "query": "woman in a white dress standing in a green garden",
        "anchor_genres": ["portrait", "genre painting"],
        "anchor_styles": ["Impressionism", "Realism", "Post-Impressionism"],
    },
    {
        "id": "black-cat-window",
        "title": "Black cat by window",
        "family": "Animal + color + interior setting",
        "query": "black cat sitting by a bright window",
        "anchor_genres": ["animal painting", "interior", "genre painting"],
        "anchor_styles": ["Realism", "Expressionism", "Art Nouveau (Modern)"],
    },
    {
        "id": "yellow-flowers-blue-vase",
        "title": "Yellow flowers, blue vase",
        "family": "Object group + colors",
        "query": "yellow flowers in a blue vase on a table",
        "anchor_genres": ["flower painting", "still life"],
        "anchor_styles": ["Post-Impressionism", "Impressionism", "Realism"],
    },
    {
        "id": "small-red-house-forest",
        "title": "Small red house in forest",
        "family": "Architecture + color + landscape",
        "query": "small red house surrounded by a dark forest",
        "anchor_genres": ["landscape", "cityscape"],
        "anchor_styles": ["Expressionism", "Realism", "Post-Impressionism"],
    },
    {
        "id": "silver-armored-figure",
        "title": "Silver armor in battle",
        "family": "Material + figure + action",
        "query": "silver armored figure in a crowded battle scene",
        "anchor_genres": ["battle painting", "mythological painting"],
        "anchor_styles": ["Baroque", "Romanticism", "Northern Renaissance"],
    },
    {
        "id": "orange-sky-trees",
        "title": "Orange sky behind trees",
        "family": "Color + setting",
        "query": "orange sunset sky behind tall dark trees",
        "anchor_genres": ["landscape"],
        "anchor_styles": ["Impressionism", "Expressionism", "Romanticism"],
    },
    {
        "id": "green-bottle-white-cloth",
        "title": "Green bottle, white cloth",
        "family": "Still-life composition",
        "query": "green glass bottle on a white cloth with fruit",
        "anchor_genres": ["still life"],
        "anchor_styles": ["Cubism", "Realism", "Post-Impressionism"],
    },
    {
        "id": "child-red-hat",
        "title": "Child with red hat",
        "family": "Person + attribute",
        "query": "child wearing a red hat in a portrait",
        "anchor_genres": ["portrait", "genre painting"],
        "anchor_styles": ["Realism", "Impressionism", "Expressionism"],
    },
    {
        "id": "white-church-mountain",
        "title": "White church near mountain",
        "family": "Architecture + color + setting",
        "query": "white church below a blue mountain",
        "anchor_genres": ["landscape", "cityscape"],
        "anchor_styles": ["Symbolism", "Realism", "Romanticism"],
    },
    {
        "id": "pink-clouds-river",
        "title": "Pink clouds over river",
        "family": "Color + landscape element",
        "query": "pink clouds reflected in a winding river",
        "anchor_genres": ["landscape", "marina"],
        "anchor_styles": ["Impressionism", "Romanticism", "Post-Impressionism"],
    },
    {
        "id": "brown-dog-blue-room",
        "title": "Brown dog in blue room",
        "family": "Animal + color + interior",
        "query": "brown dog lying in a blue room",
        "anchor_genres": ["animal painting", "interior", "genre painting"],
        "anchor_styles": ["Realism", "Expressionism"],
    },
    {
        "id": "gold-halo-dark-background",
        "title": "Gold halo, dark background",
        "family": "Religious attribute + contrast",
        "query": "saint with a gold halo against a dark background",
        "anchor_genres": ["religious painting"],
        "anchor_styles": ["Baroque", "Northern Renaissance", "Byzantine"],
    },
    {
        "id": "blue-coat-city-street",
        "title": "Blue coat on city street",
        "family": "Clothing + color + urban setting",
        "query": "person in a blue coat walking on a city street",
        "anchor_genres": ["cityscape", "genre painting"],
        "anchor_styles": ["Impressionism", "New Realism", "Realism"],
    },
    {
        "id": "white-sail-storm",
        "title": "White sail in storm",
        "family": "Object + color + weather",
        "query": "white sailboat in stormy gray waves",
        "anchor_genres": ["marina"],
        "anchor_styles": ["Romanticism", "Realism"],
    },
    {
        "id": "purple-mountain-lake",
        "title": "Purple mountain and lake",
        "family": "Color + landscape",
        "query": "purple mountain reflected in a calm lake",
        "anchor_genres": ["landscape"],
        "anchor_styles": ["Symbolism", "Expressionism", "Romanticism"],
    },
    {
        "id": "red-umbrella-rain",
        "title": "Red umbrella in rain",
        "family": "Object + color + weather",
        "query": "red umbrella on a rainy street",
        "anchor_genres": ["cityscape", "genre painting"],
        "anchor_styles": ["Impressionism", "Realism", "Expressionism"],
    },
    {
        "id": "glass-cup-lemons",
        "title": "Glass cup and lemons",
        "family": "Material + object group",
        "query": "clear glass cup beside yellow lemons on a table",
        "anchor_genres": ["still life"],
        "anchor_styles": ["Realism", "Post-Impressionism", "Cubism"],
    },
]


def media_root() -> Path:
    root = Path(os.environ.get("HYPERVIEW_MEDIA_DIR", str(SPACE_DIR / "demo_data" / "media")))
    path = root / DATASET_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("_", " ")).strip()


def safe_sample_id(index: int, title: str) -> str:
    title_part = re.sub(r"[^A-Za-z0-9_.-]+", "_", safe_text(title).lower()).strip("_")[:56]
    return f"art_{index:06d}_{title_part or 'untitled'}"


def save_image(image: Any, destination: Path) -> None:
    if destination.exists() and destination.stat().st_size > 0 and not FORCE_SAMPLE_REFRESH:
        return
    if not isinstance(image, Image.Image):
        image = Image.open(image)
    tmp_path = destination.with_suffix(destination.suffix + ".tmp")
    image = ImageOps.exif_transpose(image).convert("RGB")
    image.thumbnail(IMAGE_MAX_SIZE, Image.Resampling.LANCZOS)
    image.save(tmp_path, format="JPEG", quality=92, optimize=True)
    tmp_path.replace(destination)


def normalized_genre(row: dict[str, Any]) -> str:
    return safe_text(row.get("genre") or "unknown").lower()


def normalized_style(row: dict[str, Any]) -> str:
    return safe_text(row.get("style") or "unknown")


def select_art_records() -> list[dict[str, Any]]:
    print(f"Streaming artwork split {HF_SPLIT!r} from {HF_DATASET}...", flush=True)
    source = load_dataset(HF_DATASET, split=HF_SPLIT, streaming=HF_STREAMING)
    if not HF_STREAMING and hasattr(source, "shuffle"):
        source = source.shuffle(seed=42)

    selected: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    genre_counts: Counter[str] = Counter()
    style_counts: Counter[str] = Counter()

    for index, row in islice(enumerate(source), MAX_SCAN_ROWS):
        genre = normalized_genre(row)
        style = normalized_style(row)
        title = safe_text(row.get("title") or "")
        artist = safe_text(row.get("artist") or "")
        image = row.get("image")
        if not image or not title:
            continue
        if genre not in ALLOWED_GENRES:
            continue
        if genre_counts[genre] >= SAMPLES_PER_GENRE:
            continue
        if style_counts[style] >= SAMPLES_PER_STYLE:
            continue
        dedupe_key = f"{artist}::{title}".lower()
        if dedupe_key in seen_keys:
            continue

        selected.append({"source_index": index, **row})
        seen_keys.add(dedupe_key)
        genre_counts[genre] += 1
        style_counts[style] += 1
        if len(selected) >= MAX_SAMPLES:
            break

    if not selected:
        raise RuntimeError(f"No artwork records selected from {HF_DATASET}. Check dataset schema and filters.")
    print(f"Selected {len(selected)} artwork images by genre: {dict(genre_counts)}", flush=True)
    return selected


def add_art_samples(dataset: hv.Dataset) -> None:
    existing_ids = {sample.id for sample in dataset.samples}
    media_dir = media_root()
    records = select_art_records()
    samples: list[hv.Sample] = []
    skipped_existing = 0
    added = 0
    updated = 0

    for record in records:
        source_index = int(record["source_index"])
        title = safe_text(record.get("title") or "Untitled")
        sample_id = safe_sample_id(source_index, title)
        existed = sample_id in existing_ids
        if existed and not FORCE_SAMPLE_REFRESH:
            skipped_existing += 1
            continue

        destination = media_dir / f"{sample_id}.jpg"
        save_image(record["image"], destination)
        genre = normalized_genre(record)
        style = normalized_style(record)
        artist = safe_text(record.get("artist") or "Unknown artist")
        date = safe_text(record.get("date") or "")
        description = safe_text(record.get("description") or "")
        metadata = {
            "title": title,
            "artist": artist,
            "date": date,
            "genre": genre,
            "style": style,
            "description": description,
            "marketplace_text": safe_text(f"{artist} / {title} / {style} / {genre} / {date}"),
            "source_dataset": HF_DATASET,
            "source_split": HF_SPLIT,
            "source_index": source_index,
            "license_note": "Hugging Face dataset card does not declare an SPDX license.",
        }
        samples.append(
            hv.Sample(
                id=sample_id,
                filepath=str(destination),
                label=genre,
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
        print(f"Skipped {skipped_existing} existing artwork sample rows.", flush=True)
    print(f"Prepared artwork samples ({added} added, {updated} updated).", flush=True)


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
        spec["space_key"] = space_key
        layouts[spec["key"]] = layout_key
    return layouts


def build_dataset() -> tuple[hv.Dataset, dict[str, str]]:
    dataset = hv.Dataset(DATASET_NAME)
    add_art_samples(dataset)
    if ENABLE_CONTEXT_MAPS:
        layouts = ensure_layouts(dataset)
    else:
        layouts = {}
    return dataset, layouts


def model_panel_props(layouts: dict[str, str]) -> list[dict[str, Any]]:
    props = []
    for spec in MODEL_SPECS:
        props.append(
            {
                "key": spec["key"],
                "displayName": spec["display_name"],
                "buttonLabel": spec["button_label"],
                "layoutKey": layouts.get(spec["key"]),
                "spaceKey": spec.get("space_key"),
            }
        )
    return props


def sample_matches(sample: hv.Sample, genres: list[str], styles: list[str]) -> int:
    genre = safe_text(sample.metadata.get("genre")).lower()
    style = safe_text(sample.metadata.get("style")).lower()
    genre_score = 2 if genre in {item.lower() for item in genres} else 0
    style_score = 1 if style in {item.lower() for item in styles} else 0
    return genre_score + style_score


def anchor_for_example(dataset: hv.Dataset, example: dict[str, Any]) -> hv.Sample | None:
    genres = [safe_text(item).lower() for item in example.get("anchor_genres", [])]
    styles = [safe_text(item).lower() for item in example.get("anchor_styles", [])]
    best_sample: hv.Sample | None = None
    best_score = -1
    for sample in dataset.samples:
        score = sample_matches(sample, genres, styles)
        if score > best_score:
            best_sample = sample
            best_score = score
        if score >= 3:
            break
    return best_sample or (dataset.samples[0] if dataset.samples else None)


def build_examples(dataset: hv.Dataset) -> list[dict[str, Any]]:
    examples = []
    for item in TEXT_SEARCH_EXAMPLES:
        anchor = anchor_for_example(dataset, item)
        if anchor is None:
            continue
        examples.append(
            {
                "id": item["id"],
                "title": item["title"],
                "family": item["family"],
                "query": item["query"],
                "queryId": anchor.id,
                "anchorTitle": anchor.metadata.get("title") or anchor.id,
                "anchorArtist": anchor.metadata.get("artist") or "Unknown artist",
                "anchorGenre": anchor.metadata.get("genre") or "",
                "anchorStyle": anchor.metadata.get("style") or "",
            }
        )
    return examples


def build_demo_view(dataset: hv.Dataset, layouts: dict[str, str]) -> hv.ui.View:
    shared_props = {
        "models": model_panel_props(layouts),
        "examples": build_examples(dataset),
        "initialExampleId": DEFAULT_EXAMPLE_ID,
        "datasetName": HF_DATASET,
        "sampleCount": len(dataset.samples),
        "licenseNote": "HF card does not declare an SPDX license; use a CC0 museum mirror for production.",
    }
    results_panel = hv.ui.ExtensionPanel(
        id="art-query-gallery",
        title="Artwork Query Gallery",
        extension="art-search-readout",
        panel="art-comparison",
        position="center",
        layout=hv.ui.PanelLayout(
            width=int(os.environ.get("ART_RESULTS_WIDTH", "620")),
            min_width=500,
        ),
        props=shared_props,
    )
    samples_panel = hv.ui.Samples(
        id="grid",
        title="Samples",
        position="center",
        reference_panel_id="art-query-gallery",
        direction="right",
        layout=hv.ui.PanelLayout(
            width=int(os.environ.get("ART_SAMPLES_WIDTH", "660")),
            min_width=420,
            min_height=480,
        ),
    )

    if not ENABLE_CONTEXT_MAPS:
        return hv.ui.View(results_panel, samples_panel, active_panel="art-query-gallery")

    clip_spec = MODEL_SPECS[0]
    candidate_spec = MODEL_SPECS[1]
    map_layout = hv.ui.PanelLayout(
        height=int(os.environ.get("ART_MAP_HEIGHT", "180")),
        min_height=150,
        min_width=220,
    )
    clip_map = hv.ui.Scatter(
        id="art-map-clip",
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
        id="art-map-hyper3",
        title="Context Map: Hyper3",
        layout_key=layouts["candidate"],
        position="center",
        reference_panel_id="art-map-clip",
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
        active_panel="art-query-gallery",
    )


def initial_target_sample_id(dataset: hv.Dataset) -> str | None:
    examples = build_examples(dataset)
    example = next(
        (item for item in examples if item["id"] == DEFAULT_EXAMPLE_ID),
        examples[0] if examples else None,
    )
    return str(example["queryId"]) if example else None


def launch_demo(dataset: hv.Dataset, layouts: dict[str, str]) -> hv.Session:
    session = hv.launch(
        dataset,
        host=SPACE_HOST,
        port=SPACE_PORT,
        open_browser=False,
        workspace_id=WORKSPACE_ID,
        block=False,
    )
    print("Installing artwork search demo extension...", flush=True)
    session.ui.add_extension(EXTENSION_DIR, workspace_id=WORKSPACE_ID)
    print("Applying artwork marketplace search demo view...", flush=True)
    session.ui.apply_view(build_demo_view(dataset, layouts), workspace_id=WORKSPACE_ID)
    if ENABLE_CONTEXT_MAPS and layouts:
        session.ui.set_active_layout(layouts["clip"], workspace_id=WORKSPACE_ID)
    sample_id = initial_target_sample_id(dataset)
    if sample_id:
        session.ui.set_selection([sample_id], workspace_id=WORKSPACE_ID)
    print(f"\nHyperView artwork text-search demo is running at {session.url}", flush=True)
    print("   Use the query gallery for compositional buyer prompts, then compare live text search results.", flush=True)
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
