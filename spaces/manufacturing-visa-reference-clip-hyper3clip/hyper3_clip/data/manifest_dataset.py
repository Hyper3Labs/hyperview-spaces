from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

import torch
from PIL import Image
from torch.utils.data import Dataset, get_worker_info

from hyper3_clip.data.collators import collate_grounded as collate_grounded
from hyper3_clip.data.transforms import build_train_transform
from hyper3_clip.data.types import GroundedParent, GroundedRecord


__all__ = ["GroundedManifestDataset", "collate_grounded"]
PART_SAMPLING_MODES = {"random_one", "all"}


class GroundedManifestDataset(Dataset):
    """Manifest dataset with one full image/caption and one or more grounded parents per row."""

    def __init__(
        self,
        manifests: list[str] | str | Path,
        image_size: int,
        seed: int,
        manifest_weights: list[float] | None = None,
        part_sampling: str = "random_one",
        max_parts: int | None = None,
        train_transform: str = "wide_random_crop",
        image_normalization: str = "imagenet",
    ) -> None:
        manifest_paths = [str(manifests)] if isinstance(manifests, str | Path) else manifests
        self.records: list[GroundedRecord] = []
        source_records: list[list[GroundedRecord]] = []
        for manifest_path in manifest_paths:
            rows: list[GroundedRecord] = []
            with Path(manifest_path).open("r", encoding="utf-8") as handle:
                for line in handle:
                    if line.strip():
                        rows.append(GroundedRecord.from_json(json.loads(line)))
            source_records.append(rows)

        if manifest_weights is None:
            for rows in source_records:
                self.records.extend(rows)
        else:
            if len(manifest_weights) != len(source_records):
                raise ValueError("manifest_weights must match manifests length")
            max_len = max(len(rows) for rows in source_records if rows)
            for rows, weight in zip(source_records, manifest_weights):
                if not rows or weight <= 0.0:
                    continue
                target_len = max(1, int(round(max_len * weight)))
                for idx in range(target_len):
                    self.records.append(rows[idx % len(rows)])

        self.seed = seed
        if part_sampling not in PART_SAMPLING_MODES:
            raise ValueError(f"part_sampling must be one of {sorted(PART_SAMPLING_MODES)}, got {part_sampling!r}")
        if max_parts is not None and max_parts <= 0:
            raise ValueError("max_parts must be positive when set")
        self.part_sampling = part_sampling
        self.max_parts = max_parts
        self.transform = build_train_transform(image_size, preset=train_transform, normalization=image_normalization)

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, index: int) -> dict[str, Any]:
        record = self.records[index]
        parents = self._select_parents(index, record.parents)
        return {
            "image": self._load_image(record.image_path),
            "part_images": [self._load_parent_image(record.image_path, parent) for parent in parents],
            "caption": record.caption,
            "part_texts": [parent.text for parent in parents],
        }

    def _select_parents(self, index: int, parents: tuple[GroundedParent, ...]) -> tuple[GroundedParent, ...]:
        if self.part_sampling == "all":
            if self.max_parts is None or len(parents) <= self.max_parts:
                return parents
            worker = get_worker_info()
            worker_id = worker.id if worker is not None else 0
            rng = random.Random(self.seed + index + 1_000_003 * worker_id)
            parent_indices = sorted(rng.sample(range(len(parents)), k=self.max_parts))
            return tuple(parents[parent_index] for parent_index in parent_indices)
        worker = get_worker_info()
        worker_id = worker.id if worker is not None else 0
        rng = random.Random(self.seed + index + 1_000_003 * worker_id)
        return (parents[rng.randrange(len(parents))],)

    def _load_image(self, path: Path) -> torch.Tensor:
        with Image.open(path) as image:
            return self.transform(image.convert("RGB"))

    def _load_parent_image(self, image_path: Path, parent: GroundedParent) -> torch.Tensor:
        source_path = parent.image_path or image_path
        with Image.open(source_path) as image:
            rgb = image.convert("RGB")
            if parent.bbox is not None:
                rgb = _crop_bbox(rgb, parent.bbox)
            return self.transform(rgb)


def _crop_bbox(image: Image.Image, bbox: tuple[float, float, float, float]) -> Image.Image:
    width, height = image.size
    left, top, right, bottom = bbox
    crop_box = (
        max(0, min(width, int(round(left)))),
        max(0, min(height, int(round(top)))),
        max(0, min(width, int(round(right)))),
        max(0, min(height, int(round(bottom)))),
    )
    if crop_box[2] <= crop_box[0] or crop_box[3] <= crop_box[1]:
        return image
    return image.crop(crop_box)
