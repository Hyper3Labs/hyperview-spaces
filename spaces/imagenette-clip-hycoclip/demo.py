#!/usr/bin/env python
"""HyperView Hugging Face Space demo: CLIP + HyCoCLIP on Imagenette.

Usage:
  python demo.py --precompute   # run during Docker build
  python demo.py                # run as app entrypoint
"""

from __future__ import annotations

import os
import sys

import hyperview as hv

HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "7860"))

DATASET_NAME = os.environ.get("DEMO_DATASET", "imagenette_clip_hycoclip")
HF_DATASET = os.environ.get("DEMO_HF_DATASET", "Multimodal-Fatima/Imagenette_validation")
HF_SPLIT = os.environ.get("DEMO_HF_SPLIT", "validation")
HF_IMAGE_KEY = os.environ.get("DEMO_HF_IMAGE_KEY", "image")
HF_LABEL_KEY = os.environ.get("DEMO_HF_LABEL_KEY", "label")
NUM_SAMPLES = int(os.environ.get("DEMO_SAMPLES", "300"))

CLIP_MODEL_ID = os.environ.get("DEMO_CLIP_MODEL", "openai/clip-vit-base-patch32")
HYPER_MODEL_ID = os.environ.get("DEMO_HYPER_MODEL", "hycoclip-vit-s")


def _truthy_env(name: str, default: bool = True) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off", ""}


def _ensure_demo_ready(dataset: hv.Dataset) -> None:
    if len(dataset) == 0:
        print(f"Loading samples from {HF_DATASET} ({HF_SPLIT})...")
        dataset.add_from_huggingface(
            HF_DATASET,
            split=HF_SPLIT,
            image_key=HF_IMAGE_KEY,
            label_key=HF_LABEL_KEY,
            max_samples=NUM_SAMPLES,
            shuffle=True,
        )

    spaces = dataset.list_spaces()

    clip_space = next(
        (
            space
            for space in spaces
            if getattr(space, "provider", None) == "embed-anything"
            and getattr(space, "model_id", None) == CLIP_MODEL_ID
        ),
        None,
    )

    if clip_space is None:
        print(f"Computing CLIP embeddings ({CLIP_MODEL_ID})...")
        dataset.compute_embeddings(model=CLIP_MODEL_ID, provider="embed-anything", show_progress=True)
        spaces = dataset.list_spaces()
        clip_space = next(
            (
                space
                for space in spaces
                if getattr(space, "provider", None) == "embed-anything"
                and getattr(space, "model_id", None) == CLIP_MODEL_ID
            ),
            None,
        )

    if clip_space is None:
        raise RuntimeError("Failed to create CLIP embedding space")

    compute_hyperbolic = _truthy_env("DEMO_COMPUTE_HYPERBOLIC", default=True)
    hyper_space = next(
        (
            space
            for space in spaces
            if getattr(space, "provider", None) == "hyper-models"
            and getattr(space, "model_id", None) == HYPER_MODEL_ID
        ),
        None,
    )

    if compute_hyperbolic and hyper_space is None:
        try:
            print(f"Computing hyperbolic embeddings ({HYPER_MODEL_ID})...")
            dataset.compute_embeddings(model=HYPER_MODEL_ID, provider="hyper-models", show_progress=True)
            spaces = dataset.list_spaces()
            hyper_space = next(
                (
                    space
                    for space in spaces
                    if getattr(space, "provider", None) == "hyper-models"
                    and getattr(space, "model_id", None) == HYPER_MODEL_ID
                ),
                None,
            )
        except Exception as exc:
            print(f"WARNING: hyperbolic embeddings failed ({type(exc).__name__}: {exc})")

    layouts = dataset.list_layouts()
    geometries = {getattr(layout, "geometry", None) for layout in layouts}

    if "euclidean" not in geometries:
        print("Computing euclidean layout...")
        dataset.compute_visualization(space_key=clip_space.space_key, geometry="euclidean")

    if "poincare" not in geometries:
        print("Computing poincaré layout...")
        poincare_space_key = hyper_space.space_key if hyper_space is not None else clip_space.space_key
        dataset.compute_visualization(space_key=poincare_space_key, geometry="poincare")


def main() -> None:
    dataset = hv.Dataset(DATASET_NAME)

    if len(dataset) == 0 or not dataset.list_layouts():
        print("Preparing demo dataset...")
        _ensure_demo_ready(dataset)
    else:
        print(
            f"Loaded cached dataset '{DATASET_NAME}' with "
            f"{len(dataset.list_spaces())} spaces and {len(dataset.list_layouts())} layouts"
        )

    if "--precompute" in sys.argv:
        print("Precompute complete")
        return

    print(f"Starting HyperView on {HOST}:{PORT}")
    hv.launch(dataset, host=HOST, port=PORT, open_browser=False)


if __name__ == "__main__":
    main()
