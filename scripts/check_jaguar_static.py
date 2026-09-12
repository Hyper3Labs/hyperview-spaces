"""Verify the exported Jaguar artifact against the frozen research inputs."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from huggingface_hub import snapshot_download
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "demos/jaguar-multigeometry"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def verify(bundle: Path) -> dict:
    snapshot = read_json(SOURCE / "research-snapshot.json")
    manifest = read_json(bundle / "hyperview-static.json")
    assert manifest["static"] is True and manifest["kind"] == "hyperview-static-space"
    assert manifest["warnings"] == []
    assert manifest["capabilities"]["text_search"] is False
    assert manifest["capabilities"]["sample_similarity"] is True
    assert manifest["capabilities"]["similarity_k"] == 100
    originals = {row["id"]: row for row in snapshot["samples"]}
    index = read_json(bundle / "api/samples/index.json")
    samples = {}
    for shard in index["shards"]:
        for row in read_json(bundle / "api/samples" / shard["path"])["samples"]:
            assert row["id"] not in samples
            samples[row["id"]] = row
    assert set(samples) == set(originals) and len(samples) == 1895
    media_count = 0
    for sample_id, row in samples.items():
        original = originals[sample_id]
        for field in ("label", "metadata", "width", "height"):
            assert row[field] == original[field], (sample_id, field)
        for field in ("media_url", "thumbnail_url"):
            path = bundle / row[field].lstrip("/")
            assert path.is_file(), path
            with Image.open(path) as image:
                image.verify()
            media_count += 1
        local = SOURCE / "demo_data/media" / original["filename"]
        if local.exists():
            assert (
                hashlib.sha256(local.read_bytes()).digest()
                == hashlib.sha256((bundle / row["media_url"].lstrip("/")).read_bytes()).digest()
            )
    layouts = manifest["restore"]["layouts"]
    assert len(layouts) == 3
    for layout in layouts:
        original = next(
            item for item in snapshot["layouts"] if item["layout_key"] == layout["layout_key"]
        )
        exported = read_json(bundle / layout["coords"])
        source_coords = dict(zip(original["ids"], original["coords"], strict=True))
        assert set(exported["ids"]) == set(source_coords)
        assert exported["geometry"] == original["geometry"]
        expected = np.asarray([source_coords[i] for i in exported["ids"]], dtype=np.float32)
        assert np.array_equal(np.asarray(exported["coords"], dtype=np.float32), expected)
    assets = Path(
        snapshot_download(
            snapshot["space_id"], repo_type="space", revision=snapshot["space_revision"]
        )
    )
    asset_manifest = read_json(assets / "assets/manifest.json")
    assert len(manifest["restore"]["spaces"]) == 3
    for space in manifest["restore"]["spaces"]:
        model = next(
            item for item in asset_manifest["models"] if item["space_key"] == space["space_key"]
        )
        original_space = next(
            item
            for item in snapshot["dataset"]["spaces"]
            if item["space_key"] == space["space_key"]
        )
        assert space["config"] == original_space["config"]
        with np.load(assets / "assets" / model["embeddings_path"], allow_pickle=False) as original:
            with np.load(bundle / space["vectors"], allow_pickle=False) as exported:
                positions = {str(i): n for n, i in enumerate(original["ids"])}
                assert set(exported["ids"].astype(str)) == set(positions)
                expected = original["vectors"][[positions[str(i)] for i in exported["ids"]]]
                assert np.array_equal(exported["vectors"], expected)
    similarity = bundle / "api/search/similar"
    neighbors = {}
    for key, space in read_json(similarity / "index.json")["spaces"].items():
        assert space["metric"] == "cosine"
        queries = {}
        for shard in space["shards"]:
            payload = read_json(similarity / shard["path"])
            assert payload["metric"] == "cosine"
            assert not set(queries).intersection(payload["queries"])
            queries.update(payload["queries"])
        assert set(queries) == set(originals)
        for sample_id, query in queries.items():
            results = query["results"]
            assert len(results) == 100
            ids = {row["sample_id"] for row in results}
            assert len(ids) == 100 and sample_id not in ids and ids <= set(originals)
            distances = np.array([row["distance"] for row in results])
            assert np.isfinite(distances).all() and np.all(np.diff(distances) >= 0)
        neighbors[key] = queries
    assert len(neighbors) == 3
    for check in snapshot["neighbor_checks"]:
        results = neighbors[check["space_key"]][check["sample_id"]]["results"]
        expected = check["results"]
        assert np.allclose(
            [row["distance"] for row in results],
            [row["distance"] for row in expected],
            atol=2e-6,
            rtol=2e-5,
        )
        # Every changed ID must be a floating-point tie at the top-100 boundary.
        actual_ids = {row["sample_id"] for row in results}
        boundary = results[-1]["distance"]
        assert all(
            row["id"] in actual_ids or abs(row["distance"] - boundary) < 2e-6 for row in expected
        )
    ui = read_json(bundle / "api/runtime.json")["workspace"]["ui"]
    assert ui["active_panel_id"] == "jaguar-spherical"
    return {
        "status": "passed",
        "hyperview_version": manifest["hyperview_version"],
        "samples": len(samples),
        "verified_media_files": media_count,
        "vector_sets_exact": 3,
        "layout_coordinate_sets_exact": 3,
        "neighbor_queries": sum(len(rows) for rows in neighbors.values()),
        "neighbors_per_query": 100,
        "legacy_neighbor_checks": len(snapshot["neighbor_checks"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = verify(args.bundle.resolve())
    payload = json.dumps(report, indent=2) + "\n"
    if args.report:
        args.report.write_text(payload)
    print(payload)


if __name__ == "__main__":
    main()
