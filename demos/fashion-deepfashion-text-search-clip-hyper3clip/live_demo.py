#!/usr/bin/env python
"""Live Fashion catalog search using HyperView's native text retrieval UI."""

from __future__ import annotations

import os

from demo import DATASET_NAME, SPACE_HOST, load_evidence, repair_media_paths, validate_dataset

import hyperview as hv

WORKSPACE_ID = os.environ.get("HYPERVIEW_WORKSPACE_ID", "fashion-live-catalog-search")
SPACE_PORT = int(os.environ.get("HYPERVIEW_PORT", "6266"))
CLIP_LAYOUT_KEY = (
    "embed-anything__openai_clip-vit-base-patch32__4771034973d8__"
    "euclidean_umap__2d_1a6bcbc4"
)


def main() -> None:
    dataset = hv.Dataset(DATASET_NAME)
    repair_media_paths(dataset)
    validate_dataset(dataset, load_evidence())

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
        props={"mode": "auto"},
        layout=hv.ui.PanelLayout(min_width=420, min_height=420),
    )
    catalog_map = hv.ui.Scatter(
        id="fashion-live-catalog-map",
        title="Catalog map",
        layout_key=CLIP_LAYOUT_KEY,
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
