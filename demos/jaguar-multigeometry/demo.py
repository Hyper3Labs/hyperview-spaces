"""Reproduce the paper-facing Jaguar views and export them without a backend.

Only public HyperView APIs are used. Frozen layouts are imported, never recomputed.
The Dataset subclass preserves the legacy app's cosine-neighbor contract, including
for its Lorentz vectors; this is deliberately not canonical Lorentz retrieval.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path

import numpy as np
from datasets import load_dataset
from huggingface_hub import snapshot_download

import hyperview as hv

HERE = Path(__file__).resolve().parent
SPACE_ID = "hyper3labs/jaguar-hyperview-multigeometry"
SPACE_REVISION = "214644d68ee4f10d7a5dbc768ed76af00febe62c"
DATASET_REPO = "hyper3labs/jaguar-hyperview-demo"
DATASET_REVISION = "28110bb140951f84f11f23073d76412b367f65e4"
DATASET_NAME = "jaguar_core_claims_demo"
WORKSPACE_ID = "jaguar-multigeometry"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text())


class JaguarDataset(hv.Dataset):
    """Public Dataset specialization retaining the published cosine rankings."""

    def prepare_neighbors(self, spaces: dict[str, tuple[list[str], np.ndarray]]) -> None:
        self.neighbor_tables = {}
        self.samples_by_id = {sample.id: sample for sample in self.samples}
        for key, (ids, vectors) in spaces.items():
            values = np.asarray(vectors, dtype=np.float64)
            norms = np.linalg.norm(values, axis=1, keepdims=True)
            if not np.isfinite(values).all() or np.any(norms == 0):
                raise ValueError(f"Invalid vectors in {key}")
            normalized = values / norms
            distances = np.clip(1 - normalized @ normalized.T, 0, 2)
            np.fill_diagonal(distances, np.inf)
            order = np.argsort(distances, axis=1, kind="stable")[:, :100]
            self.neighbor_tables[key] = (
                ids,
                {value: i for i, value in enumerate(ids)},
                distances,
                order,
            )

    def find_similar(self, sample_id, k=10, space_key=None, *, layout_key=None):
        if layout_key is not None:
            layout = next(item for item in self.list_layouts() if item.layout_key == layout_key)
            if space_key is not None and space_key != layout.space_key:
                raise ValueError("space_key does not match layout_key")
            space_key = layout.space_key
        key = space_key or next(iter(self.neighbor_tables))
        ids, indices, distances, order = self.neighbor_tables[key]
        anchor = indices[sample_id]
        if not 1 <= k <= 100:
            raise ValueError("The paper demo supports 1–100 precomputed neighbors")
        return [
            (self.samples_by_id[ids[i]], float(distances[anchor, i])) for i in order[anchor, :k]
        ]


def build_dataset() -> tuple[JaguarDataset, dict]:
    snapshot = read_json(HERE / "research-snapshot.json")
    if (
        snapshot["space_revision"] != SPACE_REVISION
        or snapshot["dataset_revision"] != DATASET_REVISION
    ):
        raise ValueError("Research snapshot revisions do not match the pinned inputs")
    assets = Path(snapshot_download(SPACE_ID, repo_type="space", revision=SPACE_REVISION))
    manifest = read_json(assets / "assets/manifest.json")
    rows = load_dataset(DATASET_REPO, name="default", split="train", revision=DATASET_REVISION)
    original = {row["id"]: row for row in snapshot["samples"]}
    if len(rows) != 1895 or len(original) != 1895:
        raise ValueError("Expected exactly 1,895 original samples")
    media = HERE / "demo_data/media"
    media.mkdir(parents=True, exist_ok=True)
    samples = []
    for row in rows:
        sample_id = str(row["sample_id"])
        source = original[sample_id]
        if (
            str(row["label"]) != source["label"]
            or row["split_tag"] != source["metadata"]["split_tag"]
        ):
            raise ValueError(f"Published sample metadata changed: {sample_id}")
        path = media / f"{Path(sample_id).stem}.jpg"
        if not path.exists():
            row["image"].convert("RGB").save(path, format="JPEG", quality=90, optimize=True)
        samples.append(
            hv.Sample(
                id=sample_id,
                filepath=str(path),
                label=source["label"],
                metadata=source["metadata"],
                width=source["width"],
                height=source["height"],
            )
        )
    if {sample.id for sample in samples} != set(original):
        raise ValueError("Dataset IDs differ from the published app")
    dataset = JaguarDataset(DATASET_NAME, persist=False)
    dataset.add_samples(samples)
    spaces = {}
    hashes = {}
    for model in manifest["models"]:
        path = assets / "assets" / model["embeddings_path"]
        hashes[model["space_key"]] = hashlib.sha256(path.read_bytes()).hexdigest()
        with np.load(path, allow_pickle=False) as payload:
            ids = payload["ids"].astype(str).tolist()
            vectors = np.asarray(payload["vectors"], dtype=np.float32)
        if set(ids) != set(original) or len(ids) != len(original):
            raise ValueError(f"Embedding sample set changed: {model['space_key']}")
        source = next(
            item
            for item in snapshot["dataset"]["spaces"]
            if item["space_key"] == model["space_key"]
        )
        if vectors.shape != (1895, source["dim"]):
            raise ValueError(f"Unexpected embedding shape: {vectors.shape}")
        dataset.register_embeddings(
            model["space_key"], model["model_key"], ids, vectors, config=source["config"]
        )
        spaces[model["space_key"]] = (ids, vectors)
    for layout in snapshot["layouts"]:
        source = next(
            item
            for item in snapshot["dataset"]["layouts"]
            if item["layout_key"] == layout["layout_key"]
        )
        dataset.register_layout(
            layout["layout_key"],
            source["space_key"],
            layout["ids"],
            layout["coords"],
            method=source["method"],
            geometry=source["geometry"],
            params=source["params"],
        )
    dataset.prepare_neighbors(spaces)
    # Old LanceDB float32 cosine results may order ties differently. Verify each
    # recorded distance, top-k boundary and non-tied ordering, not arbitrary ties.
    max_distance_error = 0.0
    for check in snapshot["neighbor_checks"]:
        ids, indices, distances, order = dataset.neighbor_tables[check["space_key"]]
        anchor = indices[check["sample_id"]]
        expected = check["results"]
        actual = distances[anchor, order[anchor, : len(expected)]]
        reported = np.array([item["distance"] for item in expected])
        by_id = np.array([distances[anchor, indices[item["id"]]] for item in expected])
        error = float(np.max(np.abs(by_id - reported)))
        max_distance_error = max(max_distance_error, error)
        if not np.allclose(actual, reported, atol=2e-6, rtol=2e-5) or error > 2e-6:
            raise ValueError(
                f"Legacy neighbors changed: {check['space_key']} / {check['sample_id']}"
            )
    report = {
        "space_revision": SPACE_REVISION,
        "dataset_revision": DATASET_REVISION,
        "sample_count": len(dataset),
        "label_count": len(dataset.labels),
        "layouts_recomputed": False,
        "neighbor_metric": "cosine",
        "neighbor_checks": len(snapshot["neighbor_checks"]),
        "max_legacy_neighbor_distance_error": max_distance_error,
        "embedding_asset_sha256": hashes,
        "snapshot_sha256": hashlib.sha256(
            (HERE / "research-snapshot.json").read_bytes()
        ).hexdigest(),
    }
    return dataset, report


def build_view(dataset: hv.Dataset) -> hv.ui.View:
    titles = {
        "euclidean": "Euclidean · Triplet T0",
        "spherical": "Sphere 3D · ArcFace O0",
        "poincare": "Poincare · Lorentz O1",
    }
    panels = []
    for geometry, title in titles.items():
        layout = dataset.find_layout(geometry=geometry)
        if layout is None:
            raise ValueError(f"Missing research layout: {geometry}")
        panels.append(hv.ui.Scatter(f"jaguar-{geometry}", title=title, layout_key=layout))
    return hv.ui.View(
        hv.ui.Horizontal(
            hv.ui.Tabs(*panels, active_tab="jaguar-spherical"),
            hv.ui.Tabs(
                hv.ui.Samples(
                    "samples",
                    title="Jaguar images · cosine neighbors",
                    show_text_search=False,
                    layout=hv.ui.PanelLayout(min_width=280),
                ),
                hv.ui.Explorer("jaguar-identities", title="Identities"),
                active_tab="samples",
            ),
            shares=[7, 3],
        ),
        active_panel="jaguar-spherical",
    )


def export_bundle(session: hv.Session, out: Path, report: dict) -> dict:
    result = session.export(out, workspace_id=WORKSPACE_ID, similarity_k=100)
    if result.get("warnings"):
        raise ValueError(f"Export warnings: {result['warnings']}")
    # The public exporter correctly calls our Dataset.find_similar override,
    # but derives metric *labels* from source geometry. Correct those labels to
    # the actual legacy cosine metric, without changing any exported rankings.
    similarity = out / "api/search/similar"
    for path in similarity.rglob("*.json"):
        payload = read_json(path)
        if "metric" in payload:
            payload["metric"] = "cosine"
        for space in payload.get("spaces", {}).values():
            space["metric"] = "cosine"
        path.write_text(json.dumps(payload, separators=(",", ":")) + "\n")
    provenance = out / "research"
    provenance.mkdir()
    shutil.copy2(HERE / "research-snapshot.json", provenance / "legacy-snapshot.json")
    (provenance / "migration-report.json").write_text(json.dumps(report, indent=2) + "\n")
    shutil.copy2(HERE / "SPACE_README.md", out / "README.md")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export", type=Path)
    parser.add_argument("--port", type=int, default=6277)
    args = parser.parse_args()
    os.environ.setdefault("HYPERVIEW_DATASETS_DIR", str(HERE / "demo_data/datasets"))
    dataset, report = build_dataset()
    print(json.dumps(report, indent=2), flush=True)
    session = hv.launch(
        dataset,
        workspace_id=WORKSPACE_ID,
        view=build_view(dataset),
        host="127.0.0.1",
        port=args.port,
        open_browser=False,
        reuse_server=False,
        block=False,
    )
    if args.export:
        try:
            print(
                json.dumps(export_bundle(session, args.export.resolve(), report), indent=2),
                flush=True,
            )
        finally:
            session.stop()
    elif os.environ.get("HYPERVIEW_BUILD_ONLY") == "1":
        session.stop()
    else:
        session.wait()


if __name__ == "__main__":
    main()
