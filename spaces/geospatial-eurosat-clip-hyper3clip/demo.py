#!/usr/bin/env python
"""Geospatial scene-retrieval comparison demo for CLIP vs Hyper3-CLIP in HyperView."""

from __future__ import annotations

import os
import re
from collections import Counter
from pathlib import Path
from typing import Any

from datasets import load_dataset
from PIL import Image, ImageOps

import hyperview as hv

SPACE_DIR = Path(__file__).resolve().parent
SPACE_HOST = os.environ.get("HYPERVIEW_HOST", "127.0.0.1")
SPACE_PORT = int(os.environ.get("HYPERVIEW_PORT", "6262"))
WORKSPACE_ID = os.environ.get(
    "HYPERVIEW_WORKSPACE_ID", "geospatial-resisc45-clip-hyper3clip"
)
DATASET_NAME = os.environ.get(
    "HYPERVIEW_DATASET_NAME", "resisc45_clip_hyper3clip_side_by_side"
)
EXTENSION_DIR = SPACE_DIR / ".hyperview" / "extensions" / "geospatial-readout"

HF_DATASET = os.environ.get(
    "GEOSPATIAL_HF_DATASET", os.environ.get("EUROSAT_HF_DATASET", "tanganke/resisc45")
)
HF_SPLIT = os.environ.get(
    "GEOSPATIAL_HF_SPLIT", os.environ.get("EUROSAT_HF_SPLIT", "test")
)
DATASET_LABEL = os.environ.get("GEOSPATIAL_DATASET_LABEL", "NWPU-RESISC45")
SAMPLE_SEED = int(
    os.environ.get(
        "GEOSPATIAL_SAMPLE_SEED", os.environ.get("EUROSAT_SAMPLE_SEED", "42")
    )
)
SAMPLES_PER_CLASS = int(
    os.environ.get(
        "GEOSPATIAL_SAMPLES_PER_CLASS", os.environ.get("EUROSAT_SAMPLES_PER_CLASS", "5")
    )
)
TOP_EXAMPLES = int(os.environ.get("GEOSPATIAL_TOP_EXAMPLES", "3"))
MIN_EXAMPLE_CLASS_DELTA = int(os.environ.get("GEOSPATIAL_MIN_EXAMPLE_CLASS_DELTA", "3"))
MIN_EXAMPLE_PARENT_DELTA = int(
    os.environ.get("GEOSPATIAL_MIN_EXAMPLE_PARENT_DELTA", "4")
)
IMAGE_MAX_SIZE = (512, 512)
FORCE_SAMPLE_REFRESH = os.environ.get(
    "HYPERVIEW_GEOSPATIAL_FORCE_REFRESH",
    os.environ.get("HYPERVIEW_EUROSAT_FORCE_REFRESH", ""),
).lower() in {
    "1",
    "true",
    "yes",
}
ALLOW_CANDIDATE_FALLBACK = os.environ.get(
    "HYPERVIEW_ALLOW_CANDIDATE_FALLBACK", "1"
).lower() in {
    "1",
    "true",
    "yes",
}
RUNTIME_WARNINGS: list[str] = []

BENCHMARK_CLAIMS = {
    "dataset": "NWPU-RESISC45",
    "task": "same-class remote-sensing scene retrieval",
    "headline": "Hyper3-CLIP retrieves cleaner scene neighborhoods than CLIP-B/32.",
    "rows": [
        {"metric": "mAP", "hyper3": "0.5033", "clip": "0.4606", "delta": "+4.27 pts"},
        {
            "metric": "Precision@10",
            "hyper3": "0.7563",
            "clip": "0.7458",
            "delta": "+1.05 pts",
        },
        {
            "metric": "Parent P@10",
            "hyper3": "0.9133",
            "clip": "0.8974",
            "delta": "+1.59 pts",
        },
    ],
    "caveat": "Claim scope: beats OpenAI CLIP-B/32 on this bounded retrieval probe; SigLIP-B/16 is stronger in the internal ledger.",
}

PARENT_GROUPS = {
    "airplane": "transport",
    "airport": "transport",
    "bridge": "transport",
    "freeway": "transport",
    "intersection": "transport",
    "overpass": "transport",
    "railway": "transport",
    "railway station": "transport",
    "roundabout": "transport",
    "runway": "transport",
    "ship": "transport",
    "baseball diamond": "sports_recreation",
    "basketball court": "sports_recreation",
    "golf course": "sports_recreation",
    "ground track field": "sports_recreation",
    "stadium": "sports_recreation",
    "tennis court": "sports_recreation",
    "beach": "water_coastal",
    "harbor": "water_coastal",
    "island": "water_coastal",
    "lake": "water_coastal",
    "river": "water_coastal",
    "sea ice": "water_coastal",
    "wetland": "water_coastal",
    "circular farmland": "agriculture_vegetation",
    "forest": "agriculture_vegetation",
    "meadow": "agriculture_vegetation",
    "rectangular farmland": "agriculture_vegetation",
    "terrace": "agriculture_vegetation",
    "church": "built_environment",
    "commercial area": "built_environment",
    "dense residential": "built_environment",
    "industrial area": "built_environment",
    "medium residential": "built_environment",
    "mobile home park": "built_environment",
    "palace": "built_environment",
    "parking lot": "built_environment",
    "sparse residential": "built_environment",
    "storage tank": "built_environment",
    "thermal power station": "built_environment",
    "chaparral": "natural_terrain",
    "cloud": "natural_terrain",
    "desert": "natural_terrain",
    "mountain": "natural_terrain",
    "snowberg": "natural_terrain",
}

PREFERRED_EXAMPLES = [
    ("airplane", "Transport"),
    ("runway", "Transport"),
    ("storage tank", "Built environment"),
    ("industrial area", "Built environment"),
    ("harbor", "Water / coastal"),
    ("dense residential", "Built environment"),
]


def env_value(name: str, legacy_name: str, default: str) -> str:
    """Read the geospatial env name while preserving old EuroSAT aliases."""
    return os.environ.get(name, os.environ.get(legacy_name, default))


def env_int(name: str, legacy_name: str, default: str) -> int:
    return int(env_value(name, legacy_name, default))


MODEL_SPECS = [
    {
        "key": "clip",
        "display_name": env_value(
            "GEOSPATIAL_BASELINE_DISPLAY_NAME", "EUROSAT_BASELINE_DISPLAY_NAME", "CLIP"
        ),
        "button_label": env_value(
            "GEOSPATIAL_BASELINE_BUTTON_LABEL",
            "EUROSAT_BASELINE_BUTTON_LABEL",
            "Inspect CLIP neighbors",
        ),
        "provider": env_value(
            "GEOSPATIAL_BASELINE_PROVIDER",
            "EUROSAT_BASELINE_PROVIDER",
            "embed-anything",
        ),
        "model": env_value(
            "GEOSPATIAL_BASELINE_MODEL",
            "EUROSAT_BASELINE_MODEL",
            "openai/clip-vit-base-patch32",
        ),
        "layout": env_value(
            "GEOSPATIAL_BASELINE_LAYOUT", "EUROSAT_BASELINE_LAYOUT", "euclidean:2d"
        ),
        "geometry": env_value(
            "GEOSPATIAL_BASELINE_GEOMETRY", "EUROSAT_BASELINE_GEOMETRY", "euclidean"
        ),
        "layout_dimension": env_int(
            "GEOSPATIAL_BASELINE_LAYOUT_DIMENSION",
            "EUROSAT_BASELINE_LAYOUT_DIMENSION",
            "2",
        ),
        "metric": env_value(
            "GEOSPATIAL_BASELINE_METRIC", "EUROSAT_BASELINE_METRIC", "cosine"
        ),
        "panel_title": env_value(
            "GEOSPATIAL_BASELINE_PANEL_TITLE",
            "EUROSAT_BASELINE_PANEL_TITLE",
            "CLIP - Euclidean Scene Map",
        ),
    },
    {
        "key": "candidate",
        "display_name": env_value(
            "GEOSPATIAL_CANDIDATE_DISPLAY_NAME",
            "EUROSAT_CANDIDATE_DISPLAY_NAME",
            "Hyper3-CLIP",
        ),
        "button_label": env_value(
            "GEOSPATIAL_CANDIDATE_BUTTON_LABEL",
            "EUROSAT_CANDIDATE_BUTTON_LABEL",
            "Inspect Hyper3-CLIP neighbors",
        ),
        "provider": env_value(
            "GEOSPATIAL_CANDIDATE_PROVIDER", "EUROSAT_CANDIDATE_PROVIDER", "hyper3-clip"
        ),
        "model": env_value(
            "GEOSPATIAL_CANDIDATE_MODEL",
            "EUROSAT_CANDIDATE_MODEL",
            "hyper3labs/hyper3-clip-v0.5",
        ),
        "layout": env_value(
            "GEOSPATIAL_CANDIDATE_LAYOUT", "EUROSAT_CANDIDATE_LAYOUT", "poincare:2d"
        ),
        "geometry": env_value(
            "GEOSPATIAL_CANDIDATE_GEOMETRY", "EUROSAT_CANDIDATE_GEOMETRY", "poincare"
        ),
        "layout_dimension": env_int(
            "GEOSPATIAL_CANDIDATE_LAYOUT_DIMENSION",
            "EUROSAT_CANDIDATE_LAYOUT_DIMENSION",
            "2",
        ),
        "metric": env_value(
            "GEOSPATIAL_CANDIDATE_METRIC", "EUROSAT_CANDIDATE_METRIC", "cosine"
        ),
        "panel_title": env_value(
            "GEOSPATIAL_CANDIDATE_PANEL_TITLE",
            "EUROSAT_CANDIDATE_PANEL_TITLE",
            "Hyper3-CLIP - Poincare Scene Map",
        ),
    },
]


def media_root() -> Path:
    root = Path(
        os.environ.get("HYPERVIEW_MEDIA_DIR", str(SPACE_DIR / "demo_data" / "media"))
    )
    path = root / DATASET_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_sample_id(label: str, image_id: str, index: int) -> str:
    raw = f"resisc45_{label}_{image_id or index}"
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", raw).strip("_")[:96]


def class_label_name(dataset: Any, value: Any) -> str:
    feature = dataset.features.get("label")
    if hasattr(feature, "int2str"):
        value = feature.int2str(int(value))
    return str(value).replace("_", " ").strip()


def parent_group(label: str) -> str:
    return PARENT_GROUPS.get(label, "other")


def readable_group(label: str) -> str:
    return label.replace("_", " ").replace("-", " ").title()


def save_image(image: Image.Image, destination: Path) -> None:
    if (
        destination.exists()
        and destination.stat().st_size > 0
        and not FORCE_SAMPLE_REFRESH
    ):
        return
    tmp_path = destination.with_suffix(destination.suffix + ".tmp")
    image = ImageOps.exif_transpose(image).convert("RGB")
    image.thumbnail(IMAGE_MAX_SIZE, Image.Resampling.LANCZOS)
    image.save(tmp_path, format="JPEG", quality=92, optimize=True)
    tmp_path.replace(destination)


def select_balanced_records() -> list[dict[str, Any]]:
    print(
        f"Loading {DATASET_LABEL} split {HF_SPLIT!r} from {HF_DATASET}...", flush=True
    )
    source = load_dataset(HF_DATASET, split=HF_SPLIT).shuffle(seed=SAMPLE_SEED)
    counts: Counter[str] = Counter()
    selected: list[dict[str, Any]] = []
    target_labels = list(PARENT_GROUPS)

    for index, row in enumerate(source):
        label = class_label_name(source, row["label"])
        if label not in PARENT_GROUPS or counts[label] >= SAMPLES_PER_CLASS:
            continue
        selected.append(
            {
                "index": index,
                "image": row["image"],
                "image_id": row.get("image_id") or str(index),
                "label": label,
                "parent_group": parent_group(label),
                "source_dataset": HF_DATASET,
                "split": HF_SPLIT,
            }
        )
        counts[label] += 1
        if all(counts[label] >= SAMPLES_PER_CLASS for label in target_labels):
            break

    missing = {
        label: SAMPLES_PER_CLASS - counts[label]
        for label in target_labels
        if counts[label] < SAMPLES_PER_CLASS
    }
    if missing:
        raise RuntimeError(
            f"Could not build balanced {DATASET_LABEL} sample. Missing: {missing}"
        )

    print(f"Selected {len(selected)} {DATASET_LABEL} tiles: {dict(counts)}", flush=True)
    return selected


def add_geospatial_samples(dataset: hv.Dataset) -> None:
    existing_ids = {sample.id for sample in dataset.samples}
    media_dir = media_root()
    image_rows: list[dict[str, Any]] = []
    records = select_balanced_records()

    for record in records:
        sample_id = safe_sample_id(record["label"], record["image_id"], record["index"])
        destination = media_dir / f"{sample_id}.jpg"
        save_image(record["image"], destination)

        metadata = {
            "scene_class": record["label"],
            "parent_group": record["parent_group"],
            "hierarchy": f"{readable_group(record['parent_group'])} -> {record['label']}",
            "image_id": record["image_id"],
            "source_dataset": record["source_dataset"],
            "split": record["split"],
        }
        image_rows.append(
            {
                "filepath": str(destination),
                "label": record["label"],
                "metadata": metadata,
                "sample_id": sample_id,
            }
        )

    if hasattr(dataset, "add_images"):
        upserted, skipped_existing = dataset.add_images(
            image_rows,
            skip_existing=not FORCE_SAMPLE_REFRESH,
        )
        updated = (
            sum(1 for row in image_rows if str(row["sample_id"]) in existing_ids)
            if FORCE_SAMPLE_REFRESH
            else 0
        )
    else:
        upserted = 0
        skipped_existing = 0
        updated = 0
        for row in image_rows:
            sample_id = str(row["sample_id"])
            exists = sample_id in existing_ids
            if exists and not FORCE_SAMPLE_REFRESH:
                skipped_existing += 1
                continue
            dataset.add_image(
                row["filepath"],
                label=row["label"],
                metadata=row["metadata"],
                sample_id=sample_id,
            )
            upserted += 1
            updated += int(exists)

    added = upserted - updated
    if skipped_existing:
        print(f"Skipped {skipped_existing} existing {DATASET_LABEL} sample rows.", flush=True)

    print(
        f"Prepared {DATASET_LABEL} samples ({added} added, {updated} updated).",
        flush=True,
    )


def ensure_layouts(dataset: hv.Dataset) -> dict[str, str]:
    layouts: dict[str, str] = {}
    for spec in MODEL_SPECS:
        print(f"Ensuring {spec['display_name']} embeddings...", flush=True)
        try:
            space_key = dataset.compute_embeddings(
                model=spec["model"],
                provider=spec["provider"],
                batch_size=32,
                show_progress=True,
            )
        except Exception as exc:
            if (
                spec["key"] == "candidate"
                and ALLOW_CANDIDATE_FALLBACK
                and "clip" in layouts
            ):
                warning = (
                    f"Hyper3-CLIP embeddings are unavailable ({type(exc).__name__}: {exc}). "
                    "Showing the CLIP layout as a clearly labeled fallback so the Space can start."
                )
                print(warning, flush=True)
                RUNTIME_WARNINGS.append(warning)
                spec.update(
                    {
                        "display_name": os.environ.get(
                            "EUROSAT_CANDIDATE_FALLBACK_DISPLAY_NAME",
                            "Hyper3-CLIP unavailable (CLIP fallback)",
                        ),
                        "button_label": os.environ.get(
                            "EUROSAT_CANDIDATE_FALLBACK_BUTTON_LABEL",
                            "CLIP fallback query",
                        ),
                        "geometry": MODEL_SPECS[0]["geometry"],
                        "layout_dimension": MODEL_SPECS[0]["layout_dimension"],
                        "panel_title": os.environ.get(
                            "EUROSAT_CANDIDATE_FALLBACK_PANEL_TITLE",
                            "Hyper3-CLIP unavailable - showing CLIP fallback",
                        ),
                        "fallback": True,
                        "space_key": MODEL_SPECS[0].get("space_key"),
                    }
                )
                layouts[spec["key"]] = layouts["clip"]
                continue
            raise
        spec["space_key"] = space_key
        print(f"Ensuring {spec['display_name']} layout...", flush=True)
        layouts[spec["key"]] = dataset.compute_visualization(
            space_key=space_key,
            layout=spec["layout"],
            n_neighbors=20,
            min_dist=0.08,
            metric=spec["metric"],
        )
    return layouts


def build_dataset() -> tuple[hv.Dataset, dict[str, str]]:
    dataset = hv.Dataset(DATASET_NAME)
    add_geospatial_samples(dataset)
    layouts = ensure_layouts(dataset)
    return dataset, layouts


def model_panel_props(layouts: dict[str, str]) -> list[dict[str, Any]]:
    props = []
    for spec in MODEL_SPECS:
        layout_key = layouts[spec["key"]]
        props.append(
            {
                "key": spec["key"],
                "displayName": spec["display_name"],
                "buttonLabel": spec["button_label"],
                "layoutKey": layout_key,
            }
        )
    return props


def neighbor_summary(
    dataset: hv.Dataset, sample_id: str, model_key: str
) -> dict[str, Any]:
    spec = next((item for item in MODEL_SPECS if item["key"] == model_key), None)
    if spec is None:
        return {}

    query = dataset[sample_id]
    query_parent = query.metadata.get("parent_group")
    space_key = spec.get("space_key")
    if space_key is None:
        return {}

    neighbors = dataset.find_similar(sample_id, k=10, space_key=str(space_key))
    parent_hits = sum(
        1
        for sample, _distance in neighbors
        if sample.metadata.get("parent_group") == query_parent
    )
    class_hits = sum(
        1 for sample, _distance in neighbors if sample.label == query.label
    )
    total = len(neighbors)
    return {
        "hits": parent_hits,
        "parentHits": parent_hits,
        "classHits": class_hits,
        "sameClassHits": class_hits,
        "offParent": total - parent_hits,
        "total": total,
    }


def collect_neighbor_summaries(
    dataset: hv.Dataset,
) -> dict[str, dict[str, dict[str, Any]]]:
    summaries: dict[str, dict[str, dict[str, Any]]] = {}
    for sample in dataset.samples:
        summaries[sample.id] = {
            "clip": neighbor_summary(dataset, sample.id, "clip"),
            "candidate": neighbor_summary(dataset, sample.id, "candidate"),
        }
    return summaries


def build_examples(
    dataset: hv.Dataset,
    summaries: dict[str, dict[str, dict[str, Any]]],
) -> list[dict[str, Any]]:
    ranked: list[tuple[float, str, Any, dict[str, Any], dict[str, Any]]] = []
    seen_labels: set[str] = set()
    for sample in dataset.samples:
        clip_summary = summaries.get(sample.id, {}).get("clip") or {}
        candidate_summary = summaries.get(sample.id, {}).get("candidate") or {}
        if not clip_summary or not candidate_summary:
            continue
        class_delta = candidate_summary["sameClassHits"] - clip_summary["sameClassHits"]
        parent_delta = candidate_summary["parentHits"] - clip_summary["parentHits"]
        if (
            class_delta < MIN_EXAMPLE_CLASS_DELTA
            or parent_delta < MIN_EXAMPLE_PARENT_DELTA
        ):
            continue
        score = class_delta * 10 + parent_delta
        ranked.append(
            (score, str(sample.label), sample, clip_summary, candidate_summary)
        )

    examples = []
    ordered = sorted(ranked, key=lambda item: item[0], reverse=True)
    preferred_labels = {label for label, _family in PREFERRED_EXAMPLES}
    ordered.extend(item for item in ranked if item[1] in preferred_labels)

    for score, label, sample, clip_summary, candidate_summary in ordered:
        if label in seen_labels:
            continue
        parent = readable_group(parent_group(label))
        class_delta = candidate_summary["sameClassHits"] - clip_summary["sameClassHits"]
        parent_delta = candidate_summary["parentHits"] - clip_summary["parentHits"]
        examples.append(
            {
                "id": label.lower(),
                "title": f"{readable_group(label)} query",
                "family": parent,
                "queryId": sample.id,
                "queryLabel": label,
                "score": score,
                "classDelta": class_delta,
                "parentDelta": parent_delta,
                "summaries": {
                    "clip": clip_summary,
                    "candidate": candidate_summary,
                },
            }
        )
        seen_labels.add(label)
        if len(examples) >= TOP_EXAMPLES:
            break
    return examples


def aggregate_metrics(
    dataset: hv.Dataset,
    summaries: dict[str, dict[str, dict[str, Any]]],
) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    for spec in MODEL_SPECS:
        class_hits = 0
        parent_hits = 0
        total = 0
        for sample in dataset.samples:
            summary = summaries.get(sample.id, {}).get(spec["key"]) or {}
            if not summary:
                continue
            class_hits += summary["sameClassHits"]
            parent_hits += summary["parentHits"]
            total += summary["total"]
        metrics[spec["key"]] = {
            "sameClassP10": class_hits / total if total else None,
            "parentP10": parent_hits / total if total else None,
            "offParentRate": 1.0 - (parent_hits / total) if total else None,
            "neighborCount": total,
        }
    clip = metrics.get("clip", {})
    candidate = metrics.get("candidate", {})
    if (
        clip
        and candidate
        and clip.get("sameClassP10") is not None
        and candidate.get("sameClassP10") is not None
    ):
        metrics["delta"] = {
            "sameClassP10": candidate["sameClassP10"] - clip["sameClassP10"],
            "parentP10": candidate["parentP10"] - clip["parentP10"],
            "offParentRate": candidate["offParentRate"] - clip["offParentRate"],
        }
    return metrics


def register_hyper3_clip_provider() -> None:
    from hyperview.runtime import ProviderRegistry

    ProviderRegistry().register_python(
        "hyper3-clip",
        "hyper3_clip_provider:Hyper3ClipEmbeddings",
        description="Hyper3-CLIP v0.5 image embeddings from hyper3labs/hyper3-clip-v0.5",
        overwrite=True,
    )


def build_demo_view(dataset: hv.Dataset, layouts: dict[str, str]) -> hv.ui.View:
    summaries = collect_neighbor_summaries(dataset)
    scatter_panels = [
        hv.ui.Scatter(
            id=f"{spec['key']}-geospatial-map",
            title=spec["panel_title"],
            layout_key=layouts[spec["key"]],
            geometry=spec["geometry"],
            layout_dimension=spec["layout_dimension"],
        )
        for spec in MODEL_SPECS
    ]
    return hv.ui.View(
        hv.ui.Horizontal(*scatter_panels),
        hv.ui.ExtensionPanel(
            id="geospatial-retrieval-readout",
            extension="geospatial-readout",
            panel="geospatial-comparison",
            position="right",
            props={
                "datasetLabel": DATASET_LABEL,
                "sampleCount": len(dataset.samples),
                "classCount": len({sample.label for sample in dataset.samples}),
                "task": "Scene-neighborhood retrieval audit",
                "benchmark": BENCHMARK_CLAIMS,
                "aggregate": aggregate_metrics(dataset, summaries),
                "models": model_panel_props(layouts),
                "examples": build_examples(dataset, summaries),
                "warnings": RUNTIME_WARNINGS,
            },
        ),
    )


def launch_demo(dataset: hv.Dataset, layouts: dict[str, str]) -> hv.Session:
    from hyperview.api import Session
    from hyperview.runtime import HyperViewRuntime

    runtime = HyperViewRuntime()
    runtime.attach_dataset_instance(WORKSPACE_ID, dataset, activate_workspace=True)
    session = Session(runtime, SPACE_HOST, SPACE_PORT, dataset)
    print("Installing geospatial demo extension...", flush=True)
    session.ui.add_extension(EXTENSION_DIR, workspace_id=WORKSPACE_ID)
    print("Applying geospatial side-by-side demo view...", flush=True)
    session.ui.apply_view(build_demo_view(dataset, layouts), workspace_id=WORKSPACE_ID)
    session.ui.set_active_layout(None, workspace_id=WORKSPACE_ID)
    session.ui.set_selection([], workspace_id=WORKSPACE_ID)
    session.start(background=True)
    print(f"\nHyperView geospatial demo is running at {session.url}", flush=True)
    return session


def main() -> None:
    register_hyper3_clip_provider()
    dataset, layouts = build_dataset()
    print("Layouts:", flush=True)
    for spec in MODEL_SPECS:
        print(f"  {spec['display_name']}: {layouts[spec['key']]}", flush=True)
    session = launch_demo(dataset, layouts)
    session.wait()


if __name__ == "__main__":
    main()
