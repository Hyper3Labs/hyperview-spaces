from __future__ import annotations

import copy
import glob
import hashlib
import random
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any

import torch
import webdataset as wds
from PIL import Image
from torch.utils.data import IterableDataset, get_worker_info

from hyper3_clip.data.transforms import build_train_transform
from hyper3_clip.training.distributed import get_rank, get_world_size


PART_SAMPLING_MODES = {"random_one", "all"}


class ProcessedGritDataset(IterableDataset):
    """Reader for official HyCoCLIP processed GRIT shards."""

    def __init__(
        self,
        tarfiles: Sequence[str],
        image_size: int,
        seed: int,
        shuffle_buffer: int = 4000,
        part_sampling: str = "random_one",
        max_parts: int | None = None,
        train_transform: str = "wide_random_crop",
        image_normalization: str = "imagenet",
        deterministic_transforms: bool = False,
    ) -> None:
        self.tarfiles = _expand_tarfiles(tarfiles)
        if not self.tarfiles:
            raise FileNotFoundError(f"No GRIT processed shards matched {tarfiles!r}")
        rank = get_rank()
        world_size = get_world_size()
        self.tarfiles = self.tarfiles[rank::world_size]
        self.shuffle_buffer = shuffle_buffer
        self.seed = seed
        if part_sampling not in PART_SAMPLING_MODES:
            raise ValueError(f"part_sampling must be one of {sorted(PART_SAMPLING_MODES)}, got {part_sampling!r}")
        if max_parts is not None and max_parts <= 0:
            raise ValueError("max_parts must be positive when set")
        self.part_sampling = part_sampling
        self.max_parts = max_parts
        self.deterministic_transforms = deterministic_transforms
        self.transform = build_train_transform(image_size, preset=train_transform, normalization=image_normalization)

    def __iter__(self) -> Iterator[dict[str, Any]]:
        worker = get_worker_info()
        worker_id = worker.id if worker is not None else 0
        shuffle_rng = random.Random(self.seed + get_rank() * 1_000_003 + worker_id)
        part_rng = random.Random(self.seed + 31_415_926 + get_rank() * 1_000_003 + worker_id)
        pipeline: Any = wds.DataPipeline(
            wds.SimpleShardList(self.tarfiles, seed=self.seed),
            wds.split_by_worker,
            wds.tarfile_to_samples(),
            wds.shuffle(self.shuffle_buffer, initial=self.shuffle_buffer, rng=shuffle_rng),
            wds.decode("pil", handler=wds.warn_and_continue),
        )
        while True:
            pipeline_copy = copy.deepcopy(pipeline)
            for sample in pipeline_copy:
                yield self._decode_sample(sample, part_rng)

    def _decode_sample(self, sample: dict[str, Any], rng: random.Random) -> dict[str, Any]:
        num_parents = int(_as_text(sample["numparents.txt"]))
        parent_indices = self._select_parent_indices(num_parents, rng)
        parent_keys = [f"parent{parent_index:03d}" for parent_index in parent_indices]
        sample_key = _as_text(sample.get("__key__", ""))
        return {
            "image": self._transform_image(sample["child.jpg"], sample_key, "child"),
            "caption": _as_text(sample["child.txt"]),
            "part_images": [
                self._transform_image(sample[f"{parent_key}.jpg"], sample_key, parent_key) for parent_key in parent_keys
            ],
            "part_texts": [_as_text(sample[f"{parent_key}.txt"]) for parent_key in parent_keys],
        }

    def _select_parent_indices(self, num_parents: int, rng: random.Random) -> list[int]:
        if self.part_sampling == "random_one":
            return [rng.randrange(num_parents)]
        parent_indices = list(range(num_parents))
        if self.max_parts is not None and len(parent_indices) > self.max_parts:
            parent_indices = sorted(rng.sample(parent_indices, k=self.max_parts))
        return parent_indices

    def _transform_image(self, value: Any, sample_key: str, role: str) -> torch.Tensor:
        image = _as_image(value)
        if not self.deterministic_transforms:
            return self.transform(image)
        transform_seed = _stable_seed(self.seed, sample_key, role)
        python_random_state = random.getstate()
        try:
            random.seed(transform_seed)
            with torch.random.fork_rng(devices=[]):
                torch.manual_seed(transform_seed)
                return self.transform(image)
        finally:
            random.setstate(python_random_state)


def _expand_tarfiles(tarfiles: Sequence[str]) -> list[str]:
    expanded: list[str] = []
    for pattern in tarfiles:
        matches = sorted(glob.glob(pattern))
        expanded.extend(matches if matches else [pattern])
    return [str(Path(path)) for path in expanded]


def _as_text(value: Any) -> str:
    return value.decode("utf-8") if isinstance(value, bytes) else str(value)


def _as_image(value: Any) -> Image.Image:
    if not isinstance(value, Image.Image):
        raise TypeError(f"Expected PIL image from WebDataset decode, got {type(value)!r}")
    return value.convert("RGB")


def _stable_seed(seed: int, *parts: str) -> int:
    digest = hashlib.blake2b(digest_size=8)
    digest.update(str(seed).encode("utf-8"))
    for part in parts:
        digest.update(b"\0")
        digest.update(part.encode("utf-8"))
    return int.from_bytes(digest.digest(), byteorder="big", signed=False)
