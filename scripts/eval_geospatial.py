#!/usr/bin/env python3
"""Rebuild the bounded GeoSpatial V1 probe from its committed 60 tiles.

Uses the public HyperView API and a pinned Hyper3-CLIP checkpoint. Retains
the original CLIP vectors as the comparison baseline; their original model
revision and the upstream tile-selection provenance remain unrecorded.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from collections import Counter
from importlib.metadata import version
from pathlib import Path

import hyper_models
import numpy as np
from huggingface_hub import snapshot_download
from PIL import Image

import hyperview as hv

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "demos/geospatial-eurosat-clip-hyper3clip"
BUNDLE = ROOT / "static-spaces/geospatial"
DATASET = "resisc45_geospatial_v1"
MODEL_REPO = "hyper3labs/hyper3-clip-v1"
MODEL_REVISION = "12a8d89022cec75a3fbac91047683231cbc0fa82"
CLIP_SPACE = "embed-anything__openai_clip-vit-base-patch32__8da42c3ae90c"
K = 10


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def vector_digest(ids: list[str], vectors: np.ndarray) -> str:
    digest = hashlib.sha256()
    for sample_id, vector in sorted(zip(ids, vectors)):
        digest.update(sample_id.encode() + b"\0")
        digest.update(np.asarray(vector, dtype="<f4").tobytes())
    return digest.hexdigest()


def main() -> None:
    evidence_path = DEMO / "evidence_cases.json"
    evidence = json.loads(evidence_path.read_text())
    manifest = json.loads((DEMO / "dataset_manifest.json").read_text())
    rows = json.loads((BUNDLE / "api/samples/shards/000000.json").read_text())["samples"]
    assert {r["id"] for r in rows} == {r["id"] for r in manifest["samples"]}
    assert len(rows) == 60 and set(Counter(r["label"] for r in rows).values()) == {5}

    dataset = hv.Dataset(DATASET)
    media_dir = DEMO / "demo_data/media" / DATASET
    media_dir.mkdir(parents=True, exist_ok=True)
    samples = []
    image_hashes = {}
    for row in rows:
        image = BUNDLE / "api/samples" / row["id"] / "content"
        target = media_dir / f"{row['id']}.jpg"
        shutil.copyfile(image, target)
        image_hashes[row["id"]] = sha256(target)
        metadata = {
            **row["metadata"],
            "source_dataset": "NWPU-RESISC45",
            "split": "prepared-subset",
            "source_provenance": "original mirror/split unrecorded",
        }
        samples.append(
            hv.Sample(
                id=row["id"],
                filepath=str(target),
                label=row["label"],
                metadata=metadata,
                modality="image",
            )
        )
    dataset.add_samples(samples, skip_existing=False)

    baseline_path = BUNDLE / "restore/spaces" / CLIP_SPACE / "vectors.npz"
    baseline = np.load(baseline_path, allow_pickle=False)
    baseline_info = next(
        s
        for s in json.loads((BUNDLE / "api/dataset.json").read_text())["spaces"]
        if s["space_key"] == CLIP_SPACE
    )
    dataset.register_embeddings(
        CLIP_SPACE,
        baseline_info["model_id"],
        baseline["ids"].tolist(),
        baseline["vectors"],
        config=baseline_info["config"],
    )
    checkpoint_dir = Path(
        snapshot_download(
            MODEL_REPO,
            revision=MODEL_REVISION,
            allow_patterns=["config.yaml", "model.safetensors"],
        )
    )
    checkpoint = checkpoint_dir / "model.safetensors"
    encoder = hyper_models.load("hyper3-clip-v1", local_path=checkpoint)
    vectors = []
    for sample in samples:
        with Image.open(sample.filepath) as image:
            vectors.append(encoder.encode_images([image.convert("RGB")])[0])
    vectors = np.asarray(vectors, dtype=np.float32)
    assert vectors.shape == (60, 513) and np.isfinite(vectors).all()
    # Lorentz vectors satisfy t² − ||x||² = 1/c. Record the curvature
    # inferred from these vectors, as the runtime embedding pipeline does.
    values = vectors.astype(np.float64)
    curvature = float(1 / np.median(values[:, 0] ** 2 - (values[:, 1:] ** 2).sum(axis=1)))
    hyper3_space = f"hyper-models__hyper3-clip-v1__{MODEL_REVISION[:12]}"
    dataset.register_embeddings(
        hyper3_space,
        "hyper3-clip-v1",
        [s.id for s in samples],
        vectors,
        config={
            "provider": "hyper-models",
            "model_id": "hyper3-clip-v1",
            "model_repo": MODEL_REPO,
            "model_revision": MODEL_REVISION,
            "checkpoint_sha256": sha256(checkpoint),
            "modality": "multimodal",
            "geometry": "hyperboloid",
            "dim": 513,
            "spatial_dim": 512,
            "params": {"curvature": curvature},
            "params_source": {"curvature": "inferred"},
        },
    )
    for space, geometry in [(hyper3_space, "poincare"), (CLIP_SPACE, "euclidean")]:
        dataset.compute_visualization(
            space_key=space,
            layout=geometry,
            n_neighbors=20,
            min_dist=0.08,
        )

    rankings = {}
    totals = {}
    for model, space in [("hyper3", hyper3_space), ("clip", CLIP_SPACE)]:
        rankings[model] = {}
        exact_total = parent_total = 0
        for sample in samples:
            neighbours = [
                s
                for s, _ in dataset.find_similar(sample.id, k=K + 1, space_key=space)
                if s.id != sample.id
            ][:K]
            assert len(neighbours) == K
            exact = sum(s.label == sample.label for s in neighbours)
            parent = sum(
                s.metadata["parent_group"] == sample.metadata["parent_group"] for s in neighbours
            )
            rankings[model][sample.id] = {
                "spaceKey": space,
                "exactHits": exact,
                "parentHits": parent,
                "resultIds": [s.id for s in neighbours],
            }
            exact_total += exact
            parent_total += parent
        totals[model] = {"exactP10": exact_total / (60 * K), "parentP10": parent_total / (60 * K)}
    totals["delta"] = {
        metric: totals["hyper3"][metric] - totals["clip"][metric]
        for metric in ("exactP10", "parentP10")
    }
    evidence["artifactId"] = "resisc45-geospatial-v1-2026-10-09"
    evidence["protocol"].update(
        {
            "dataset": "NWPU-RESISC45",
            "split": "prepared 60-tile subset",
            "candidateModel": "hyper3-clip-v1",
            "modelRevisionCaveat": "Hyper3-CLIP V1 is pinned; the original CLIP checkpoint revision was not recorded.",
            "sourceCaveat": "The original upstream source and split of this tile selection were not recorded. The committed tiles and their hashes define this probe.",
            "claimBoundary": "A small curated retrieval probe, not a full remote-sensing benchmark.",
            "metricDefinition": "P@10 is matching neighbours divided by 10, averaged over all 60 anchors. Self-matches are excluded; only four same-class neighbours are available, so same-class P@10 is capped at 40%. Group counts include same-class matches.",
        }
    )
    evidence["aggregate"] = totals
    for case in evidence["cases"]:
        case["models"] = {m: rankings[m][case["anchorSampleId"]] for m in rankings}
        case["question"] = {
            "airplane-win": "Do aircraft stay with airfield infrastructure?",
            "forest-win": "Do forests stay with vegetation and farmland?",
            "storage-tank-win": "Do tanks stay distinct from circular farmland?",
            "airport-regression": "Do airports stay with transport infrastructure?",
        }[case["id"]]
    evidence["provenance"] = {
        "source": "scripts/eval_geospatial.py",
        "hyper3": {
            "repo": MODEL_REPO,
            "revision": MODEL_REVISION,
            "checkpointSha256": sha256(checkpoint),
            "provider": "hyper-models",
            "providerVersion": version("hyper-models"),
            "vectorsSha256": vector_digest([s.id for s in samples], vectors),
        },
        "clip": {
            "model": baseline_info["model_id"],
            "revision": None,
            "note": "Original frozen CLIP baseline vectors retained.",
            "vectorsSha256": vector_digest(baseline["ids"].tolist(), baseline["vectors"]),
        },
        "imageSha256": image_hashes,
    }
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n")
    output = ROOT / "results/geospatial_v1_rankings.json"
    output.write_text(
        json.dumps(
            {
                "artifactId": evidence["artifactId"],
                "protocol": evidence["protocol"],
                "rankings": rankings,
            },
            indent=2,
        )
        + "\n"
    )
    print(
        json.dumps(
            {
                "dataset": DATASET,
                "aggregate": totals,
                "cases": [{"id": c["id"], "models": c["models"]} for c in evidence["cases"]],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
