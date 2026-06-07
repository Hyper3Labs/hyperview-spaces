from __future__ import annotations

from pathlib import Path
import random
from typing import Any

import numpy as np
import torch
from torch import nn


def save_checkpoint(
    path: str | Path,
    step: int,
    model: nn.Module,
    optimizer: torch.optim.Optimizer,
    scheduler: Any,
    scaler: Any,
    config: dict,
) -> None:
    checkpoint_path = Path(path)
    tmp_path = checkpoint_path.with_name(f"{checkpoint_path.name}.tmp")
    checkpoint = {
        "step": step,
        "model": model.state_dict(),
        "optimizer": optimizer.state_dict(),
        "scheduler": scheduler.state_dict(),
        "scaler": scaler.state_dict(),
        "config": config,
        "rng": _rng_state(),
    }
    torch.save(checkpoint, tmp_path)
    tmp_path.replace(checkpoint_path)


def load_checkpoint(
    path: str | Path,
    model: nn.Module,
    optimizer: torch.optim.Optimizer,
    scheduler: Any,
    scaler: Any,
    device: torch.device,
    *,
    model_only: bool = False,
    strict_model: bool = True,
) -> int:
    checkpoint = torch.load(path, map_location=device, weights_only=False)
    model.load_state_dict(checkpoint["model"], strict=strict_model)
    if model_only:
        return int(checkpoint["step"])
    optimizer.load_state_dict(checkpoint["optimizer"])
    scheduler.load_state_dict(checkpoint["scheduler"])
    scaler.load_state_dict(checkpoint["scaler"])
    _set_rng_state(checkpoint["rng"])
    return int(checkpoint["step"])


def latest_checkpoint(output_dir: str | Path) -> Path | None:
    paths = sorted(Path(output_dir).glob("checkpoint_step_*.pt"))
    if not paths:
        return None
    return max(paths, key=_checkpoint_step)


def _checkpoint_step(path: Path) -> int:
    return int(path.stem.rsplit("_", 1)[1])


def _rng_state() -> dict[str, Any]:
    state: dict[str, Any] = {
        "python": random.getstate(),
        "numpy": np.random.get_state(),
        "torch": torch.get_rng_state(),
    }
    if torch.cuda.is_available():
        state["cuda"] = torch.cuda.get_rng_state_all()
    return state


def _set_rng_state(state: dict[str, Any]) -> None:
    random.setstate(state["python"])
    np.random.set_state(state["numpy"])
    torch.set_rng_state(_cpu_byte_tensor(state["torch"]))
    if torch.cuda.is_available() and "cuda" in state:
        torch.cuda.set_rng_state_all([_cpu_byte_tensor(cuda_state) for cuda_state in state["cuda"]])


def _cpu_byte_tensor(value: Any) -> torch.ByteTensor:
    if isinstance(value, torch.Tensor):
        return value.detach().to(device="cpu", dtype=torch.uint8)
    return torch.as_tensor(value, dtype=torch.uint8, device="cpu")
