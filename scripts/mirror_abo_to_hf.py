#!/usr/bin/env python
"""Build and optionally upload a Hugging Face metadata mirror for ABO.

The mirror keeps official Amazon Berkeley Objects metadata as the source of
truth and adds convenience columns for hierarchy-aware retrieval demos.
Images and 3D assets are referenced by official S3 URLs rather than duplicated
as binary files.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import re
import shutil
import tarfile
import urllib.request
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq


ABO_BASE = "https://amazon-berkeley-objects.s3.amazonaws.com"
DEFAULT_REPO_ID = "hyper3labs/amazon-berkeley-objects"


def download_if_missing(url: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size > 0:
        return

    print(f"Downloading {url} -> {path}", flush=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    urllib.request.urlretrieve(url, tmp)
    tmp.replace(path)


def first_value(values: Any, *, prefer_english: bool = True) -> str | None:
    if not isinstance(values, list):
        return None
    if prefer_english:
        for item in values:
            if isinstance(item, dict) and str(item.get("language_tag", "")).startswith("en_"):
                value = item.get("value")
                if value:
                    return str(value).strip()
    for item in values:
        if isinstance(item, dict) and item.get("value"):
            return str(item["value"]).strip()
    return None


def product_type(obj: dict[str, Any]) -> str | None:
    values = obj.get("product_type") or []
    if values and isinstance(values[0], dict) and values[0].get("value"):
        return str(values[0]["value"]).strip()
    return None


def readable_product_type(label: str | None) -> str | None:
    if not label:
        return None
    text = label.replace("_", " ").replace("-", " ").lower()
    return re.sub(r"\s+", " ", text).strip()


def node_paths(obj: dict[str, Any]) -> list[str]:
    paths = []
    for node in obj.get("node") or []:
        if isinstance(node, dict) and node.get("node_name"):
            paths.append(str(node["node_name"]))
    return paths


def parse_department(paths: list[str]) -> str | None:
    skip = {"categories", "departments"}
    for path in paths:
        if not path.startswith("/"):
            continue
        parts = [part.strip() for part in path.split("/") if part.strip()]
        parts = [part for part in parts if part.lower() not in skip]
        if not parts:
            continue
        if parts[0] == "Home & Garden" and len(parts) > 1:
            return parts[1]
        return parts[0]
    return None


def image_url(path: str | None, size: str = "small") -> str | None:
    if not path:
        return None
    return f"{ABO_BASE}/images/{size}/{path}"


def load_image_map(images_csv_gz: Path) -> dict[str, dict[str, str]]:
    image_map: dict[str, dict[str, str]] = {}
    with gzip.open(images_csv_gz, "rt", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            image_id = row.get("image_id")
            if image_id:
                image_map[image_id] = dict(row)
    return image_map


def listing_row(obj: dict[str, Any], image_map: dict[str, dict[str, str]]) -> dict[str, Any]:
    main_image_id = obj.get("main_image_id")
    main_image = image_map.get(str(main_image_id)) if main_image_id else None
    main_image_path = main_image.get("path") if main_image else None
    paths = node_paths(obj)
    ptype = product_type(obj)
    ptype_readable = readable_product_type(ptype)
    department = parse_department(paths)
    hierarchy_path = " > ".join(part for part in (department, ptype_readable) if part)

    return {
        "item_id": obj.get("item_id"),
        "country": obj.get("country"),
        "marketplace": obj.get("marketplace"),
        "domain_name": obj.get("domain_name"),
        "title": first_value(obj.get("item_name"), prefer_english=True),
        "brand": first_value(obj.get("brand"), prefer_english=True),
        "color": first_value(obj.get("color"), prefer_english=True),
        "style": first_value(obj.get("style"), prefer_english=True),
        "product_type": ptype,
        "product_type_readable": ptype_readable,
        "node_paths": paths,
        "department": department,
        "hierarchy_path": hierarchy_path or None,
        "main_image_id": main_image_id,
        "main_image_path": main_image_path,
        "main_image_url": image_url(main_image_path, "small"),
        "raw_listing_json": json.dumps(obj, ensure_ascii=False, sort_keys=True),
    }


def write_parquet(rows: list[dict[str, Any]], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist(rows)
    pq.write_table(table, destination, compression="zstd")
    print(f"Wrote {destination} ({len(rows)} rows)", flush=True)


def build_images_table(images_csv_gz: Path, output_dir: Path) -> None:
    rows = []
    with gzip.open(images_csv_gz, "rt", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            path = row.get("path")
            rows.append(
                {
                    **row,
                    "small_image_url": image_url(path, "small"),
                    "original_image_url": image_url(path, "original"),
                }
            )
    write_parquet(rows, output_dir / "data" / "images" / "images.parquet")


def build_spins_table(spins_csv_gz: Path, output_dir: Path) -> None:
    rows = []
    with gzip.open(spins_csv_gz, "rt", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            path = row.get("path")
            rows.append(
                {
                    **row,
                    "spin_image_url": f"{ABO_BASE}/spins/original/{path}" if path else None,
                }
            )
    write_parquet(rows, output_dir / "data" / "spins" / "spins.parquet")


def build_3dmodels_table(models_csv_gz: Path, output_dir: Path) -> None:
    rows = []
    with gzip.open(models_csv_gz, "rt", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            path = row.get("path")
            rows.append(
                {
                    **row,
                    "model_url": f"{ABO_BASE}/3dmodels/original/{path}" if path else None,
                }
            )
    write_parquet(rows, output_dir / "data" / "3dmodels" / "3dmodels.parquet")


def build_listings_tables(
    cache_dir: Path,
    output_dir: Path,
    image_map: dict[str, dict[str, str]],
    listing_shards: list[str],
) -> None:
    listing_count = len(listing_shards)
    for shard_number, shard in enumerate(listing_shards):
        path = cache_dir / "listings" / "metadata" / f"listings_{shard}.json.gz"
        rows = []
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            for line in handle:
                rows.append(listing_row(json.loads(line), image_map))
        write_parquet(
            rows,
            output_dir / "data" / "listings" / f"listings-{shard_number:05d}-of-{listing_count:05d}.parquet",
        )


def write_dataset_card(output_dir: Path, repo_id: str) -> None:
    card = f"""---
license: cc-by-4.0
pretty_name: Amazon Berkeley Objects
tags:
- computer-vision
- image-retrieval
- product-catalog
- hierarchy
- 3d
configs:
- config_name: listings
  data_files:
  - split: train
    path: data/listings/*.parquet
- config_name: images
  data_files:
  - split: train
    path: data/images/*.parquet
- config_name: spins
  data_files:
  - split: train
    path: data/spins/*.parquet
- config_name: 3dmodels
  data_files:
  - split: train
    path: data/3dmodels/*.parquet
---

# Amazon Berkeley Objects

This is a Hugging Face metadata mirror of the Amazon Berkeley Objects dataset
for reproducible research and HyperView demos. The original dataset is provided
by Amazon.com and UC Berkeley.

This mirror stores metadata tables and official S3 asset URLs. It does not
duplicate catalog images, turntable images, or 3D models as binary files.

## Load

```python
from datasets import load_dataset

listings = load_dataset("{repo_id}", "listings", split="train")
images = load_dataset("{repo_id}", "images", split="train")
spins = load_dataset("{repo_id}", "spins", split="train")
models = load_dataset("{repo_id}", "3dmodels", split="train")
```

## Tables

- `listings`: all product listings with normalized hierarchy columns and
  `raw_listing_json` preserving the original listing object.
- `images`: full image metadata with official small and original image URLs.
- `spins`: full spin / 360-degree view metadata with official image URLs.
- `3dmodels`: full 3D model metadata with official GLB URLs.

## Added convenience columns

The `listings` table adds:

- `title`
- `brand`
- `color`
- `style`
- `product_type`
- `product_type_readable`
- `node_paths`
- `department`
- `hierarchy_path`
- `main_image_path`
- `main_image_url`

## License

Amazon Berkeley Objects is licensed under Creative Commons Attribution 4.0
International (CC BY 4.0).

Users must read and comply with the original ABO license and attribution
requirements before using the data.

Official dataset page:
https://amazon-berkeley-objects.s3.amazonaws.com/index.html

AWS Open Data Registry:
https://registry.opendata.aws/amazon-berkeley-objects/

## Attribution

Credit for the data, including all images and 3D models, must be given to
Amazon.com.

Credit for building the dataset, archives, and benchmark sets must be given to
Matthieu Guillaumin, Thomas Dideriksen, Kenan Deng, Himanshu Arora, Jasmine
Collins, and Jitendra Malik, with the complete author list in the ABO paper and
official documentation.
"""
    (output_dir / "README.md").write_text(card, encoding="utf-8")


def copy_notice_files(cache_dir: Path, output_dir: Path) -> None:
    for name in ("README.md", "LICENSE-CC-BY-4.0.txt"):
        source = cache_dir / name
        if source.exists():
            shutil.copy2(source, output_dir / f"ORIGINAL_{name}")


def extract_listing_archive(cache_dir: Path) -> None:
    archive_path = cache_dir / "archives" / "abo-listings.tar"
    download_if_missing(f"{ABO_BASE}/archives/abo-listings.tar", archive_path)
    marker = cache_dir / "listings" / ".archive-extracted"
    if marker.exists():
        return
    print(f"Extracting {archive_path}", flush=True)
    with tarfile.open(archive_path) as archive:
        archive.extractall(cache_dir, filter="data")
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text("ok\n", encoding="utf-8")


def discover_local_listing_shards(cache_dir: Path) -> list[str]:
    shards = []
    pattern = cache_dir / "listings" / "metadata" / "listings_*.json.gz"
    for path in sorted(pattern.parent.glob(pattern.name)):
        match = re.fullmatch(r"listings_([0-9a-f]+)\.json\.gz", path.name)
        if match:
            shards.append(match.group(1))
    if not shards:
        raise RuntimeError("No ABO listing metadata shards found in extracted archive.")
    return shards


def download_sources(cache_dir: Path) -> tuple[Path, Path, Path, list[str]]:
    extract_listing_archive(cache_dir)
    listing_shards = discover_local_listing_shards(cache_dir)
    print(f"Found {len(listing_shards)} ABO listing shards: {listing_shards}", flush=True)
    images_path = cache_dir / "images" / "metadata" / "images.csv.gz"
    download_if_missing(f"{ABO_BASE}/images/metadata/images.csv.gz", images_path)
    spins_path = cache_dir / "spins" / "metadata" / "spins.csv.gz"
    download_if_missing(f"{ABO_BASE}/spins/metadata/spins.csv.gz", spins_path)
    models_path = cache_dir / "3dmodels" / "metadata" / "3dmodels.csv.gz"
    download_if_missing(f"{ABO_BASE}/3dmodels/metadata/3dmodels.csv.gz", models_path)
    download_if_missing(f"{ABO_BASE}/README.md", cache_dir / "README.md")
    download_if_missing(f"{ABO_BASE}/LICENSE-CC-BY-4.0.txt", cache_dir / "LICENSE-CC-BY-4.0.txt")
    return images_path, spins_path, models_path, listing_shards


def build(cache_dir: Path, output_dir: Path, repo_id: str) -> None:
    images_path, spins_path, models_path, listing_shards = download_sources(cache_dir)
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)
    image_map = load_image_map(images_path)
    build_images_table(images_path, output_dir)
    build_spins_table(spins_path, output_dir)
    build_3dmodels_table(models_path, output_dir)
    build_listings_tables(cache_dir, output_dir, image_map, listing_shards)
    write_dataset_card(output_dir, repo_id)
    copy_notice_files(cache_dir, output_dir)


def upload(output_dir: Path, repo_id: str, private: bool) -> None:
    from huggingface_hub import HfApi

    api = HfApi()
    api.create_repo(repo_id=repo_id, repo_type="dataset", private=private, exist_ok=True)
    api.upload_folder(
        repo_id=repo_id,
        repo_type="dataset",
        folder_path=str(output_dir),
        path_in_repo=".",
        commit_message="Add Amazon Berkeley Objects metadata mirror",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-id", default=DEFAULT_REPO_ID)
    parser.add_argument("--cache-dir", type=Path, default=Path(".cache/abo-official"))
    parser.add_argument("--output-dir", type=Path, default=Path("build/amazon-berkeley-objects-hf"))
    parser.add_argument("--upload", action="store_true")
    parser.add_argument("--private", action="store_true")
    args = parser.parse_args()

    build(args.cache_dir, args.output_dir, args.repo_id)
    print(f"Dataset mirror built at {args.output_dir}", flush=True)
    if args.upload:
        upload(args.output_dir, args.repo_id, args.private)
        print(f"Uploaded {args.repo_id}", flush=True)


if __name__ == "__main__":
    main()
