#!/usr/bin/env python
"""Live Fashion catalog search using HyperView's native text retrieval UI."""

from __future__ import annotations

import os

from demo import DATASET_NAME, SPACE_HOST, load_evidence, repair_media_paths, validate_dataset

import hyperview as hv

WORKSPACE_ID = os.environ.get("HYPERVIEW_WORKSPACE_ID", "fashion-live-catalog-search")
SPACE_PORT = int(os.environ.get("HYPERVIEW_PORT", "6266"))
CLIP_MODEL = "openai/clip-vit-base-patch32"
CLIP_PROVIDER = "embed-anything"


def main() -> None:
    dataset = hv.Dataset(DATASET_NAME)
    repair_media_paths(dataset)
    validate_dataset(dataset, load_evidence())

    # The map opens on the image-only CLIP space. Layout keys carry a content
    # hash, so describe the layout instead of pinning its key.
    clip_layout_key = dataset.find_layout(
        model=CLIP_MODEL,
        provider=CLIP_PROVIDER,
        modality="image",
        geometry="euclidean",
        dimension=2,
    )
    if clip_layout_key is None:
        raise RuntimeError(
            f"Live Fashion search needs a 2D euclidean {CLIP_MODEL} image layout; "
            f"{dataset.name} has none."
        )

    session = hv.launch(
        dataset,
        host=SPACE_HOST,
        port=SPACE_PORT,
        open_browser=False,
        workspace_id=WORKSPACE_ID,
        block=False,
    )
    search = hv.ui.Samples(
        id="samples",
        title="Live catalog search",
        position="center",
        mode="auto",
        layout=hv.ui.PanelLayout(min_width=420, min_height=420),
    )
    catalog_map = hv.ui.Scatter(
        id="fashion-live-catalog-map",
        title="Catalog map",
        layout_key=clip_layout_key,
        position="right",
        reference_panel_id=search.id,
        direction="right",
        layout=hv.ui.PanelLayout(width=480, min_width=320, min_height=420),
    )
    session.ui.apply_view(
        hv.ui.View(search, catalog_map, active_panel=search.id),
        workspace_id=WORKSPACE_ID,
    )
    session.ui.reset_samples(workspace_id=WORKSPACE_ID, focus=True)
    print(f"\nHyperView Live Fashion Search is running at {session.url}", flush=True)
    print("Type any shopper request in the native Samples search box.", flush=True)
    session.wait()


if __name__ == "__main__":
    main()
