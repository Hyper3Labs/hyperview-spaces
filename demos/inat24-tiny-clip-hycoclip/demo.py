#!/usr/bin/env python
"""HyperView main Hugging Face Space geometry demo."""

from __future__ import annotations

import os
import re
from collections import Counter
from pathlib import Path

from datasets import load_dataset
from PIL import Image, ImageOps

import hyperview as hv

SPACE_HOST = "0.0.0.0"
SPACE_PORT = 7860

DATASET_NAME = "inat24_tiny_geometry_showcase"
HF_DATASET = "evendrow/inat24_tiny"
HF_SPLIT = "train"
SAMPLE_SEED = 42

TARGET_SUPERCATEGORY_COUNTS = {
    "plants": 50,
    "insects": 50,
    "birds": 42,
    "arachnids": 36,
    "amphibians": 30,
    "reptiles": 26,
    "fungi": 26,
    "mammals": 20,
    "fish": 10,
    "mollusks": 10,
}
SAMPLE_COUNT = sum(TARGET_SUPERCATEGORY_COUNTS.values())
IMAGE_MAX_SIZE = (768, 768)

EMBEDDING_LAYOUTS = [
    {
        "name": "CLIP",
        "provider": "embed-anything",
        "model": "openai/clip-vit-base-patch32",
        "layouts": ["euclidean:3d", "spherical"],
    },
    {
        "name": "HyCoCLIP",
        "provider": "hyper-models",
        "model": "hycoclip-vit-s",
        "layouts": ["poincare"],
    },
]

METADATA_FIELDS = (
    "common_name",
    "id",
    "width",
    "height",
    "license",
    "rights_holder",
    "date",
    "latitude",
    "longitude",
    "location_uncertainty",
    "category_id",
    "supercategory",
    "kingdom",
    "phylum",
    "class",
    "order",
    "family",
    "genus",
    "specific_epithet",
)


def media_root() -> Path:
    root = Path(os.environ.get("HYPERVIEW_MEDIA_DIR", "./demo_data/media"))
    path = root / DATASET_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_sample_id(row: dict, index: int) -> str:
    raw_id = row.get("id", index)
    normalized = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(raw_id)).strip("_")
    return f"inat24_{normalized}"


def species_name(row: dict, features) -> str:
    label = row.get("label")
    if label is None:
        return "unknown"
    return features["label"].int2str(label)


def save_image(row: dict, destination: Path) -> None:
    if destination.exists():
        return

    image = row["image"]
    if not isinstance(image, Image.Image):
        raise TypeError(f"Expected a PIL image, got {type(image)!r}")

    image = ImageOps.exif_transpose(image).convert("RGB")
    image.thumbnail(IMAGE_MAX_SIZE, Image.Resampling.LANCZOS)
    image.save(destination, format="JPEG", quality=90, optimize=True)


def existing_label_counts(dataset: hv.Dataset) -> Counter[str]:
    return Counter(sample.label for sample in dataset.samples if sample.label)


def target_reached(counts: Counter[str]) -> bool:
    return all(
        counts[group] >= quota
        for group, quota in TARGET_SUPERCATEGORY_COUNTS.items()
    )


def add_inat24_samples(dataset: hv.Dataset) -> None:
    counts = existing_label_counts(dataset)
    if target_reached(counts):
        print(f"Dataset already has the target stratified sample ({len(dataset)} samples).")
        return

    existing_ids = {sample.id for sample in dataset.samples}
    print(
        f"Building a stratified {SAMPLE_COUNT}-sample iNat24 Tiny subset from {HF_DATASET}...",
        flush=True,
    )
    print(f"Current counts: {dict(counts)}", flush=True)

    source = load_dataset(HF_DATASET, split=HF_SPLIT)
    source = source.shuffle(seed=SAMPLE_SEED)
    root = media_root()

    for index, row in enumerate(source):
        group = row.get("supercategory")
        if group not in TARGET_SUPERCATEGORY_COUNTS:
            continue
        if counts[group] >= TARGET_SUPERCATEGORY_COUNTS[group]:
            continue

        sample_id = safe_sample_id(row, index)
        if sample_id in existing_ids:
            continue

        image_path = root / f"{sample_id}.jpg"
        save_image(row, image_path)

        metadata = {field: row.get(field) for field in METADATA_FIELDS}
        metadata["scientific_name"] = species_name(row, source.features)
        metadata["source_dataset"] = HF_DATASET
        metadata["sample_strategy"] = "stratified_by_inat24_supercategory"

        dataset.add_sample(
            hv.Sample(
                id=sample_id,
                filepath=str(image_path),
                label=group,
                metadata=metadata,
            ),
        )
        counts[group] += 1
        existing_ids.add(sample_id)

        loaded = sum(
            min(counts[group], quota)
            for group, quota in TARGET_SUPERCATEGORY_COUNTS.items()
        )
        if loaded == 1 or loaded % 25 == 0 or target_reached(counts):
            print(f"Loaded {loaded}/{SAMPLE_COUNT} samples: {dict(counts)}", flush=True)

        if target_reached(counts):
            break

    if not target_reached(counts):
        missing = {
            group: quota - counts[group]
            for group, quota in TARGET_SUPERCATEGORY_COUNTS.items()
            if counts[group] < quota
        }
        raise RuntimeError(f"Could not build the target iNat24 Tiny sample. Missing: {missing}.")


def build_dataset() -> tuple[hv.Dataset, dict[str, str]]:
    dataset = hv.Dataset(DATASET_NAME)
    add_inat24_samples(dataset)

    # Layout keys carry a content hash, so they are only knowable after the
    # layout is computed. Collect them here and hand them to the view rather
    # than pinning them as constants that a rebuild would invalidate.
    layout_keys: dict[str, str] = {}
    for embedding in EMBEDDING_LAYOUTS:
        print(f"Ensuring {embedding['name']} embeddings ({embedding['model']})...", flush=True)
        space_key = dataset.compute_embeddings(
            model=embedding["model"],
            provider=embedding["provider"],
            show_progress=True,
        )

        for layout in embedding["layouts"]:
            print(f"Ensuring {embedding['name']} {layout} layout...", flush=True)
            layout_keys[f"{embedding['name']}:{layout}"] = dataset.compute_visualization(
                space_key=space_key, layout=layout
            )

    return dataset, layout_keys


def build_demo_view(layout_keys: dict[str, str]) -> hv.ui.View:
    """Open the showcase on its three geometries, side by side.

    Without an explicit view the workspace launches with no active layout, so
    the embeddings panel renders "No 2D embeddings layout available" even
    though three layouts exist -- the one thing this demo is here to show.
    """

    panels: list[hv.ui.Scatter | hv.ui.Samples] = []
    previous_id: str | None = None
    for label, layout_key in layout_keys.items():
        name, layout = label.split(":", 1)
        panel = hv.ui.Scatter(
            id=f"map-{layout.replace(':', '-')}",
            title=f"{name} · {layout}",
            layout_key=layout_key,
            position="center",
            reference_panel_id=previous_id,
            direction="right" if previous_id else None,
            layout=hv.ui.PanelLayout(min_width=220, min_height=260),
        )
        panels.append(panel)
        previous_id = panel.id

    panels.append(
        hv.ui.Samples(
            id="samples",
            title="iNat24 Tiny · 300 observations",
            position="bottom",
            layout=hv.ui.PanelLayout(height=260, min_height=180),
        )
    )
    return hv.ui.View(*panels, active_panel=panels[0].id)


def main() -> None:
    dataset, layout_keys = build_dataset()
    print(f"Starting HyperView on {SPACE_HOST}:{SPACE_PORT}", flush=True)
    hv.launch(
        dataset,
        host=SPACE_HOST,
        port=SPACE_PORT,
        open_browser=False,
        view=build_demo_view(layout_keys),
    )


if __name__ == "__main__":
    main()
