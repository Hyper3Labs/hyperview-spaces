#!/usr/bin/env python
"""HyperView Jaguar Re-ID Hugging Face Space."""

from __future__ import annotations

SPACE_HOST = "0.0.0.0"
SPACE_PORT = 7860

DATASET_NAME = "jaguar_reid_megadescriptor_spherical_space"
HF_DATASET = "hyper3labs/jaguar-re-id"
HF_CONFIG = "default"
HF_SPLIT = "train"
HF_IMAGE_KEY = "image"
HF_LABEL_KEY = "label"
SAMPLE_COUNT = 200
MODEL_ID = "hf-hub:BVRA/MegaDescriptor-L-384"
BATCH_SIZE = 4

import hyperview as hv


def build_dataset() -> hv.Dataset:
    dataset = hv.Dataset(DATASET_NAME)

    if len(dataset) == 0:
        print(f"Loading {SAMPLE_COUNT} samples from {HF_DATASET} [{HF_CONFIG}] ({HF_SPLIT})...")
        dataset.add_from_huggingface(
            HF_DATASET,
            config=HF_CONFIG,
            split=HF_SPLIT,
            image_key=HF_IMAGE_KEY,
            label_key=HF_LABEL_KEY,
            max_samples=SAMPLE_COUNT,
        )

    print(f"Ensuring MegaDescriptor embeddings ({MODEL_ID})...")
    space_key = dataset.compute_embeddings(
        model=MODEL_ID,
        provider="timm-image",
        batch_size=BATCH_SIZE,
        show_progress=True,
    )

    print("Ensuring spherical layout...")
    dataset.compute_visualization(space_key=space_key, layout="spherical")

    return dataset


def main() -> None:
    dataset = build_dataset()
    print(f"Starting HyperView on {SPACE_HOST}:{SPACE_PORT}")
    hv.launch(dataset, host=SPACE_HOST, port=SPACE_PORT, open_browser=False)


if __name__ == "__main__":
    main()