from __future__ import annotations

import random
from collections.abc import Iterator
from typing import Any

from torch.utils.data import Dataset, IterableDataset, get_worker_info

from hyper3_clip.training.distributed import get_rank, get_world_size


class MixedGroundedIterableDataset(IterableDataset):
    """Infinite stream that mixes a primary stream with a finite grounded dataset.

    This is intended for cleaned processed-GRIT plus explicit taxonomy hierarchy
    manifests. The primary stream remains the pacing dataset, while auxiliary
    examples are sampled with a fixed probability.
    """

    def __init__(
        self,
        primary: IterableDataset,
        auxiliary: Dataset,
        auxiliary_probability: float,
        seed: int,
    ) -> None:
        if not 0.0 <= auxiliary_probability <= 1.0:
            raise ValueError("auxiliary_probability must be in [0, 1]")
        if len(auxiliary) == 0:
            raise ValueError("auxiliary dataset must not be empty")
        self.primary = primary
        self.auxiliary = auxiliary
        self.auxiliary_probability = auxiliary_probability
        self.seed = seed

    def __iter__(self) -> Iterator[dict[str, Any]]:
        worker = get_worker_info()
        worker_id = worker.id if worker is not None else 0
        num_workers = worker.num_workers if worker is not None else 1
        rank = get_rank()
        world_size = get_world_size()
        rng = random.Random(self.seed + 1_000_003 * rank + 9_176 * worker_id)
        primary_iter = iter(self.primary)
        auxiliary_iter = self._iter_auxiliary_indices(rng, rank, world_size, worker_id, num_workers)

        while True:
            if rng.random() < self.auxiliary_probability:
                yield self.auxiliary[next(auxiliary_iter)]
            else:
                yield next(primary_iter)

    def _iter_auxiliary_indices(
        self,
        rng: random.Random,
        rank: int,
        world_size: int,
        worker_id: int,
        num_workers: int,
    ) -> Iterator[int]:
        indices = list(range(len(self.auxiliary)))
        indices = indices[rank::world_size]
        indices = indices[worker_id::num_workers]
        if not indices:
            indices = list(range(len(self.auxiliary)))
        while True:
            shuffled = list(indices)
            rng.shuffle(shuffled)
            yield from shuffled
