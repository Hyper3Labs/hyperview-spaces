from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time

import torch
from torch import nn
from torch.optim import AdamW, Optimizer
from torch.nn.parallel import DistributedDataParallel
from torch.utils.data import DataLoader, DistributedSampler, IterableDataset
from torch.amp import GradScaler

from hyper3_clip.data import (
    GroundedManifestDataset,
    MixedGroundedIterableDataset,
    ProcessedGritDataset,
    collate_grounded,
)
from hyper3_clip.models.hyper3_clip import Hyper3CLIP
from hyper3_clip.training.checkpointing import latest_checkpoint, load_checkpoint, save_checkpoint
from hyper3_clip.training.distributed import (
    barrier,
    destroy_distributed,
    get_local_rank,
    get_rank,
    get_world_size,
    init_distributed,
    is_main_process,
)
from hyper3_clip.training.logging import JsonlLogger
from hyper3_clip.utils.io import ensure_dir, save_yaml, set_seed

try:
    from hypercluster.hooks import RunControl
except ImportError:  # pragma: no cover - hypercluster is only present in cluster allocations.
    RunControl = None


class CosineWithWarmup:
    def __init__(self, optimizer: torch.optim.Optimizer, warmup_steps: int, total_steps: int, base_lr: float) -> None:
        self.optimizer = optimizer
        self.warmup_steps = warmup_steps
        self.total_steps = total_steps
        self.base_lr = base_lr

    def step(self, step_idx: int) -> None:
        if step_idx < self.warmup_steps:
            lr = self.base_lr * float(step_idx + 1) / float(max(1, self.warmup_steps))
        else:
            progress = float(step_idx - self.warmup_steps) / float(max(1, self.total_steps - self.warmup_steps))
            lr = self.base_lr * 0.5 * (1.0 + torch.cos(torch.tensor(progress * torch.pi)).item())
        for group in self.optimizer.param_groups:
            group["lr"] = lr

    def state_dict(self) -> dict[str, int | float]:
        return {"warmup_steps": self.warmup_steps, "total_steps": self.total_steps, "base_lr": self.base_lr}

    def load_state_dict(self, state: dict[str, int | float]) -> None:
        self.warmup_steps = int(state["warmup_steps"])
        self.total_steps = int(state["total_steps"])
        self.base_lr = float(state["base_lr"])


def _build_optimizer(model: nn.Module, cfg: dict) -> AdamW:
    no_decay_names = set(cfg.get("optimizer", {}).get("no_decay_params", []))
    decay_params = []
    no_decay_params = []

    for name, param in model.named_parameters():
        if not param.requires_grad:
            continue
        leaf_name = name.split(".")[-1]
        if param.ndim < 2 or leaf_name in no_decay_names or leaf_name == "bias" or "norm" in name.lower():
            no_decay_params.append(param)
        else:
            decay_params.append(param)

    return AdamW(
        [
            {"params": decay_params, "weight_decay": cfg["training"]["weight_decay"]},
            {"params": no_decay_params, "weight_decay": 0.0},
        ],
        lr=cfg["training"]["lr"],
        betas=tuple(cfg["training"]["betas"]),
    )


def run_training(config: dict) -> None:
    init_distributed()
    set_seed(config["seed"] + get_rank())
    ensure_dir(config["output_dir"])
    started_at = utc_timestamp()
    if is_main_process():
        save_yaml(Path(config["output_dir"]) / "config.yaml", config)
        write_metadata(config, status="running", started_at=started_at)

    if torch.cuda.is_available():
        if "LOCAL_RANK" in os.environ:
            device = torch.device(f"cuda:{get_local_rank()}")
            torch.cuda.set_device(device)
        else:
            device = torch.device("cuda")
    else:
        device = torch.device("cpu")
    if device.type == "cuda":
        torch.cuda.reset_peak_memory_stats()
        torch.backends.cudnn.benchmark = bool(config["training"].get("cudnn_benchmark", False))

    raw_model = Hyper3CLIP(**config["model"]).to(device)
    channels_last = str(config["training"].get("memory_format", "")).lower() == "channels_last"
    if channels_last:
        raw_model = raw_model.to(memory_format=torch.channels_last)
    model: nn.Module = raw_model
    if get_world_size() > 1:
        device_ids = [get_local_rank()] if device.type == "cuda" else None
        model = DistributedDataParallel(
            raw_model,
            device_ids=device_ids,
            broadcast_buffers=False,
            find_unused_parameters=bool(config["training"].get("find_unused_parameters", False)),
        )
    dataset = _build_dataset(config["data"], config["seed"])
    sampler = _build_sampler(dataset)
    local_batch_size = _local_batch_size(config["training"])
    num_workers = config["data"].get("num_workers", config["training"].get("num_workers", 4))
    dataloader_kwargs = {}
    if num_workers > 0:
        dataloader_kwargs["persistent_workers"] = bool(
            config["data"].get("persistent_workers", config["training"].get("persistent_workers", False))
        )
        prefetch_factor = config["data"].get("prefetch_factor", config["training"].get("prefetch_factor"))
        if prefetch_factor is not None:
            dataloader_kwargs["prefetch_factor"] = int(prefetch_factor)
    beta_clip_data_config = config["data"].get("beta_clip", {})
    dataloader = DataLoader(
        dataset,
        batch_size=local_batch_size,
        sampler=sampler,
        shuffle=sampler is None and not isinstance(dataset, IterableDataset),
        num_workers=num_workers,
        pin_memory=bool(config["data"].get("pin_memory", True)),
        drop_last=True,
        collate_fn=lambda x: collate_grounded(
            x,
            tokenizer=raw_model.text_encoder.tokenizer,
            max_text_length=config["data"]["max_text_length"],
            beta_clip_queries=bool(beta_clip_data_config.get("enabled", False)),
            beta_clip_max_sentences=int(beta_clip_data_config.get("max_sentences", 5)),
            beta_clip_max_phrases=int(beta_clip_data_config.get("max_phrases", 30)),
            beta_clip_max_queries_per_image=beta_clip_data_config.get("max_queries_per_image"),
            beta_clip_use_part_texts=bool(beta_clip_data_config.get("use_part_texts", True)),
        ),
        **dataloader_kwargs,
    )

    optimizer = _build_optimizer(model=raw_model, cfg=config)
    scheduler = CosineWithWarmup(
        optimizer=optimizer,
        warmup_steps=config["training"]["warmup_steps"],
        total_steps=config["training"]["total_steps"],
        base_lr=config["training"]["lr"],
    )
    scaler = GradScaler(device.type, enabled=config["training"]["amp"])
    start_step = _resume_step(config, raw_model, optimizer, scheduler, scaler, device)
    run_control = RunControl.from_env() if RunControl is not None else None

    logger = JsonlLogger(Path(config["output_dir"]) / "train_log.jsonl")

    model.train()
    step = start_step
    micro_step = 0
    grad_accum_steps = max(1, int(config["training"].get("grad_accum_steps", 1)))
    non_blocking_transfer = bool(config["training"].get("non_blocking_transfer", True))
    micro_batch_global_size = local_batch_size * get_world_size()
    effective_global_batch_size = micro_batch_global_size * grad_accum_steps
    last_step_time = time.perf_counter()
    optimizer.zero_grad(set_to_none=True)
    while step < config["training"]["total_steps"]:
        if sampler is not None:
            sampler.set_epoch(step)
        for batch in dataloader:
            if step >= config["training"]["total_steps"]:
                break

            if micro_step % grad_accum_steps == 0:
                optimizer.zero_grad(set_to_none=True)
                scheduler.step(step)

            batch = {k: v.to(device, non_blocking=non_blocking_transfer) for k, v in batch.items()}
            if channels_last:
                batch["image"] = batch["image"].contiguous(memory_format=torch.channels_last)
                batch["part_images"] = batch["part_images"].contiguous(memory_format=torch.channels_last)

            with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=config["training"]["amp"]):
                out = model(**batch, step=step)
                loss = out["loss"] / grad_accum_steps

            scaler.scale(loss).backward()
            micro_step += 1
            if micro_step % grad_accum_steps != 0:
                continue

            if config["training"]["max_grad_norm"] > 0:
                scaler.unscale_(optimizer)
                grad_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), config["training"]["max_grad_norm"])
            else:
                grad_norm = None
            scaler.step(optimizer)
            scaler.update()

            completed_steps = step + 1
            now = time.perf_counter()
            step_time_seconds = now - last_step_time
            last_step_time = now

            if completed_steps == 1 or completed_steps % config["training"]["log_interval"] == 0:
                remaining_steps = config["training"]["total_steps"] - completed_steps
                row = {
                    "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                    "step": completed_steps,
                    "loss": float(out["loss"].detach().cpu().item()),
                    "contrastive_loss": float(out["contrastive_loss"].detach().cpu().item()),
                    "entailment_loss": float(out["entailment_loss"].detach().cpu().item()),
                    "part_count": int(out["part_count"].detach().cpu().item()),
                    "kappa": float(out["kappa"].detach().cpu().item()),
                    "lr": optimizer.param_groups[0]["lr"],
                    "grad_norm": None if grad_norm is None else float(grad_norm.detach().cpu().item()),
                    "step_time_seconds": step_time_seconds,
                    "steps_per_second": 1.0 / max(step_time_seconds, 1e-12),
                    "samples_per_second": effective_global_batch_size / max(step_time_seconds, 1e-12),
                    "samples_seen": completed_steps * effective_global_batch_size,
                    "progress": completed_steps / config["training"]["total_steps"],
                    "eta_seconds": remaining_steps * step_time_seconds,
                    "rank": get_rank(),
                    "world_size": get_world_size(),
                    "local_batch_size": local_batch_size,
                    "micro_batch_global_size": micro_batch_global_size,
                    "global_batch_size": effective_global_batch_size,
                    "grad_accum_steps": grad_accum_steps,
                }
                if device.type == "cuda":
                    row["cuda_max_memory_allocated_mb"] = torch.cuda.max_memory_allocated() / (1024**2)
                for key, value in out.items():
                    if key in row or key == "loss":
                        continue
                    if torch.is_tensor(value) and value.numel() == 1:
                        row[key] = _scalar_log_value(value)
                if is_main_process():
                    logger.write(row)
                    print(_format_log_row(row), flush=True)

            if is_main_process() and completed_steps > 0 and completed_steps % config["training"]["ckpt_interval"] == 0:
                ckpt_path = str(Path(config["output_dir"]) / f"checkpoint_step_{completed_steps}.pt")
                save_checkpoint(ckpt_path, completed_steps, raw_model, optimizer, scheduler, scaler, config)

            step = completed_steps
            if run_control is not None and run_control.should_pause():
                ckpt_path = str(Path(config["output_dir"]) / f"checkpoint_step_{completed_steps}.pt")
                if is_main_process():
                    save_checkpoint(ckpt_path, completed_steps, raw_model, optimizer, scheduler, scaler, config)
                    (Path(config["output_dir"]) / "latest_checkpoint.txt").write_text(f"{ckpt_path}\n", encoding="utf-8")
                    run_control.report_checkpoint(ckpt_path)
                    write_metadata(config, status="paused", started_at=started_at, ended_at=utc_timestamp(), final_step=completed_steps)
                barrier()
                destroy_distributed()
                raise SystemExit(run_control.PAUSED_EXIT_CODE)

    barrier()
    if is_main_process():
        final_ckpt = str(Path(config["output_dir"]) / "checkpoint_final.pt")
        save_checkpoint(final_ckpt, step, raw_model, optimizer, scheduler, scaler, config)
        write_metadata(config, status="completed", started_at=started_at, ended_at=utc_timestamp(), final_step=step)
    barrier()
    destroy_distributed()


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_metadata(
    config: dict,
    *,
    status: str,
    started_at: str,
    ended_at: str | None = None,
    final_step: int | None = None,
) -> None:
    metadata = {
        "run_id": config["project"]["experiment"],
        "experiment_name": config["project"]["name"],
        "status": status,
        "start_time": started_at,
        "end_time": ended_at,
        "final_step": final_step,
        "tags": {
            "data": config.get("data", {}).get("type", "unknown"),
            "model": config.get("model", {}).get("vision_backbone", "unknown"),
            "objective": config.get("model", {}).get("objective", "hycoclip"),
        },
        "job": {
            "job_id": os.environ.get("JOB_ID") or os.environ.get("SCHEDULER_JOB_ID") or os.environ.get("SLURM_JOB_ID"),
            "partition": os.environ.get("JOB_PARTITION")
            or os.environ.get("SCHEDULER_PARTITION")
            or os.environ.get("SLURM_JOB_PARTITION"),
            "num_nodes": os.environ.get("NUM_NODES") or os.environ.get("SLURM_JOB_NUM_NODES"),
            "node_list": os.environ.get("NODE_LIST") or os.environ.get("SLURM_JOB_NODELIST"),
            "gpus": os.environ.get("GPU_DEVICES") or os.environ.get("SLURM_JOB_GPUS") or os.environ.get("SLURM_GPUS"),
        },
        "env": {
            "hostname": os.environ.get("HOSTNAME"),
            "world_size": str(get_world_size()),
            "rank": str(get_rank()),
        },
    }
    path = Path(config["output_dir"]) / "metadata.json"
    path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _build_dataset(data_config: dict, seed: int) -> GroundedManifestDataset | ProcessedGritDataset | MixedGroundedIterableDataset:
    data_type = data_config.get("type")
    if data_type is None:
        data_type = "processed_grit" if data_config.get("tarfiles") else "manifest"
    if data_type == "manifest":
        manifests = data_config.get("manifests") or data_config.get("manifest")
        if manifests is None:
            raise ValueError("Manifest training requires data.manifests or data.manifest")
        return GroundedManifestDataset(
            manifests=manifests,
            image_size=data_config["image_size"],
            seed=seed,
            manifest_weights=data_config.get("manifest_weights"),
            part_sampling=data_config.get("part_sampling", "random_one"),
            max_parts=data_config.get("max_parts"),
            train_transform=data_config.get("train_transform", "wide_random_crop"),
            image_normalization=data_config.get("image_normalization", "imagenet"),
        )
    if data_type == "processed_grit":
        return ProcessedGritDataset(
            tarfiles=data_config["tarfiles"],
            image_size=data_config["image_size"],
            seed=seed,
            shuffle_buffer=data_config.get("shuffle_buffer", 4000),
            part_sampling=data_config.get("part_sampling", "random_one"),
            max_parts=data_config.get("max_parts"),
            train_transform=data_config.get("train_transform", "wide_random_crop"),
            image_normalization=data_config.get("image_normalization", "imagenet"),
            deterministic_transforms=data_config.get("deterministic_transforms", False),
        )
    if data_type == "mixed_processed_grit_manifest":
        manifest_config = data_config.get("manifest_data", {})
        manifests = manifest_config.get("manifests") or manifest_config.get("manifest") or data_config.get("manifests")
        if manifests is None:
            raise ValueError("Mixed GRIT+manifest training requires data.manifest_data.manifests")
        primary = ProcessedGritDataset(
            tarfiles=data_config["tarfiles"],
            image_size=data_config["image_size"],
            seed=seed,
            shuffle_buffer=data_config.get("shuffle_buffer", 4000),
            part_sampling=data_config.get("part_sampling", "random_one"),
            max_parts=data_config.get("max_parts"),
            train_transform=data_config.get("train_transform", "wide_random_crop"),
            image_normalization=data_config.get("image_normalization", "imagenet"),
            deterministic_transforms=data_config.get("deterministic_transforms", False),
        )
        auxiliary = GroundedManifestDataset(
            manifests=manifests,
            image_size=manifest_config.get("image_size", data_config["image_size"]),
            seed=seed + 47,
            manifest_weights=manifest_config.get("manifest_weights"),
            part_sampling=manifest_config.get("part_sampling", data_config.get("manifest_part_sampling", "all")),
            max_parts=manifest_config.get("max_parts", data_config.get("manifest_max_parts")),
            train_transform=manifest_config.get("train_transform", data_config.get("train_transform", "wide_random_crop")),
            image_normalization=manifest_config.get("image_normalization", data_config.get("image_normalization", "imagenet")),
        )
        return MixedGroundedIterableDataset(
            primary=primary,
            auxiliary=auxiliary,
            auxiliary_probability=float(data_config.get("manifest_probability", 0.15)),
            seed=seed,
        )
    raise ValueError(f"Unsupported data.type {data_type!r}")


def _build_sampler(dataset: GroundedManifestDataset | ProcessedGritDataset | MixedGroundedIterableDataset) -> DistributedSampler | None:
    if get_world_size() == 1 or isinstance(dataset, IterableDataset):
        return None
    return DistributedSampler(dataset, num_replicas=get_world_size(), rank=get_rank(), shuffle=True, drop_last=True)


def _local_batch_size(training_config: dict) -> int:
    if "batch_size" in training_config:
        return int(training_config["batch_size"])
    global_batch_size = int(training_config["global_batch_size"])
    if global_batch_size % get_world_size() != 0:
        raise ValueError("training.global_batch_size must be divisible by world size")
    return global_batch_size // get_world_size()


def _resume_step(
    config: dict,
    model: nn.Module,
    optimizer: Optimizer,
    scheduler: CosineWithWarmup,
    scaler: GradScaler,
    device: torch.device,
) -> int:
    training_config = config["training"]
    resume_env = training_config.get("resume_from_env", "RESUME_FROM_CHECKPOINT")
    resume_path = os.environ.get(str(resume_env)) if resume_env else None
    if resume_path is None:
        resume_path = training_config.get("resume_from")
    if resume_path is None and training_config.get("resume", False):
        resume_path = latest_checkpoint(config["output_dir"])
    if resume_path is None:
        return 0
    return load_checkpoint(
        resume_path,
        model,
        optimizer,
        scheduler,
        scaler,
        device,
        model_only=bool(training_config.get("resume_model_only", False)),
        strict_model=bool(training_config.get("resume_strict_model", True)),
    )


def _format_log_row(row: dict) -> str:
    return " ".join(f"{key}={value}" for key, value in row.items())


def _scalar_log_value(value: torch.Tensor) -> float | int:
    detached = value.detach().cpu()
    if detached.dtype == torch.bool:
        return int(detached.item())
    if detached.dtype in (torch.int8, torch.int16, torch.int32, torch.int64, torch.uint8):
        return int(detached.item())
    return float(detached.item())
