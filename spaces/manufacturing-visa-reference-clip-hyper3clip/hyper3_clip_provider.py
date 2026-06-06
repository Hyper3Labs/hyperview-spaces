"""HyperView embedding provider for the Hyper3-CLIP v0.5 HF checkpoint."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import numpy as np
import torch
import yaml
from huggingface_hub import snapshot_download
from lancedb.embeddings import EmbeddingFunction
from pydantic import PrivateAttr
from safetensors.torch import load_file


class Hyper3ClipEmbeddings(EmbeddingFunction):
    """Image embeddings from Hyper3-CLIP v0.5 in Lorentz/hyperboloid space."""

    name: str = "hyper3labs/hyper3-clip-v0.5"
    batch_size: int = 8
    device: str = "cpu"

    _model: Any = PrivateAttr(default=None)
    _transform: Any = PrivateAttr(default=None)

    @property
    def geometry(self) -> str:
        return "hyperboloid"

    @property
    def curvature(self) -> float:
        self._ensure_model()
        return float(self._model._kappa().detach().cpu().reshape(-1)[0].item())

    def ndims(self) -> int:
        return 513

    def _ensure_model(self) -> None:
        if self._model is not None:
            return

        from hyper3_clip import Hyper3CLIP
        from torchvision import transforms

        token = os.environ.get("HF_TOKEN")
        local_dir = snapshot_download(
            self.name,
            allow_patterns=["config.yaml", "model.safetensors"],
            token=token,
        )
        root = Path(local_dir)
        config = yaml.safe_load((root / "config.yaml").read_text(encoding="utf-8"))

        model = Hyper3CLIP(**config["model"])
        state = load_file(root / "model.safetensors", device="cpu")
        state = _normalize_checkpoint_keys(state, model)
        model.load_state_dict(state)
        model.to(torch.device(self.device))
        model.eval()

        self._model = model
        image_size = int(config.get("data", {}).get("image_size", 224))
        self._transform = transforms.Compose(
            [
                transforms.Resize(image_size, interpolation=transforms.InterpolationMode.BICUBIC),
                transforms.CenterCrop(image_size),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=(0.485, 0.456, 0.406),
                    std=(0.229, 0.224, 0.225),
                ),
            ]
        )

    def compute_source_embeddings(
        self,
        inputs: Any,
        *args: Any,
        **kwargs: Any,
    ) -> list[np.ndarray | None]:
        from PIL import Image
        from hyperview.core.sample import Sample

        self._ensure_model()
        device = torch.device(self.device)
        images = []
        for item in self.sanitize_input(inputs):
            if isinstance(item, Sample):
                with item.load_image() as img:
                    images.append(img.convert("RGB"))
            elif isinstance(item, str):
                with Image.open(item) as img:
                    images.append(img.convert("RGB"))
            elif isinstance(item, Image.Image):
                images.append(item.convert("RGB"))
            else:
                raise TypeError(f"Unsupported input type: {type(item)}")

        outputs: list[np.ndarray | None] = []
        with torch.inference_mode():
            for start in range(0, len(images), self.batch_size):
                batch = images[start:start + self.batch_size]
                tensor = torch.stack([self._transform(image) for image in batch]).to(device)
                encoded = self._model.encode_image(tensor).detach().cpu().numpy().astype(np.float32)
                outputs.extend(encoded)
        return outputs

    def compute_query_embeddings(
        self,
        query: Any,
        *args: Any,
        **kwargs: Any,
    ) -> list[np.ndarray | None]:
        return self.compute_source_embeddings([query], *args, **kwargs)


def _normalize_checkpoint_keys(state: dict[str, torch.Tensor], model: torch.nn.Module) -> dict[str, torch.Tensor]:
    """Handle CLIPTextModel wrapper key drift between training and Space runtime."""
    model_keys = set(model.state_dict())
    old_prefix = "text_encoder.backbone.text_model."
    new_prefix = "text_encoder.backbone."
    if not any(key.startswith(old_prefix) for key in state):
        return state
    if any(key.startswith(old_prefix) for key in model_keys):
        return state

    normalized: dict[str, torch.Tensor] = {}
    for key, value in state.items():
        candidate = new_prefix + key[len(old_prefix):] if key.startswith(old_prefix) else key
        normalized[candidate if candidate in model_keys else key] = value
    return normalized
