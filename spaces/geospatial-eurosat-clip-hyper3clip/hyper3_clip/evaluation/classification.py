from __future__ import annotations

from pathlib import Path

import torch
from torch.utils.data import DataLoader
from torch.utils.data import Subset
from torchvision import datasets

from hyper3_clip.data.transforms import build_eval_transform

from hyper3_clip.models.hyper3_clip import Hyper3CLIP


IMAGENET_PROMPTS = (
    "i took a picture : itap of a {}.",
    "pics : a bad photo of the {}.",
    "pics : a origami {}.",
    "pics : a photo of the large {}.",
    "pics : a {} in a video game.",
    "pics : art of the {}.",
    "pics : a photo of the small {}.",
)


@torch.inference_mode()
def evaluate_imagenet_zero_shot(
    model: Hyper3CLIP,
    imagenet_val_root: str | Path,
    device: torch.device,
    batch_size: int = 128,
    image_size: int = 224,
    max_text_length: int = 77,
    max_items: int | None = None,
    prompts: tuple[str, ...] = IMAGENET_PROMPTS,
) -> dict[str, float]:
    model.eval()
    dataset = datasets.ImageFolder(str(imagenet_val_root), transform=build_eval_transform(image_size))
    class_names = _imagenet_prompt_names(dataset.classes, Path(imagenet_val_root))
    classifier = _build_text_classifier(model, class_names, prompts, device, max_text_length)
    eval_dataset = Subset(dataset, range(min(max_items, len(dataset)))) if max_items is not None else dataset
    loader = DataLoader(eval_dataset, batch_size=batch_size, num_workers=4, pin_memory=device.type == "cuda")
    correct = 0
    total = 0
    per_class_correct = torch.zeros(len(dataset.classes), dtype=torch.float64)
    per_class_total = torch.zeros(len(dataset.classes), dtype=torch.float64)
    for images, targets in loader:
        images = images.to(device, non_blocking=True)
        targets = targets.to(device, non_blocking=True)
        predictions = model.similarity_scores(model.encode_image(images), classifier).argmax(dim=1)
        matches = predictions == targets
        correct += int(matches.sum().item())
        total += targets.numel()
        per_class_correct.scatter_add_(0, targets.cpu(), matches.cpu().double())
        per_class_total.scatter_add_(0, targets.cpu(), torch.ones_like(targets.cpu(), dtype=torch.float64))

    observed_classes = per_class_total > 0
    mean_per_class = (per_class_correct[observed_classes] / per_class_total[observed_classes]).mean().item()
    top1 = correct / max(total, 1)
    return {"top1": top1, "top1_pct": 100.0 * top1, "mean_per_class_acc_pct": 100.0 * mean_per_class}


def _build_text_classifier(
    model: Hyper3CLIP,
    class_names: list[str],
    prompts: tuple[str, ...],
    device: torch.device,
    max_text_length: int,
) -> torch.Tensor:
    class_embeddings: list[torch.Tensor] = []
    for class_name in class_names:
        readable_name = class_name.replace("_", " ")
        texts = [prompt.format(readable_name) for prompt in prompts]
        tokenized = model.tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=max_text_length,
            return_tensors="pt",
        ).to(device)
        attention_mask = (
            tokenized.attention_mask if "attention_mask" in tokenized else torch.ones_like(tokenized.input_ids)
        )
        tangent = model.encode_text(tokenized.input_ids, attention_mask, project=False).float().mean(dim=0, keepdim=True)
        class_embeddings.append(model.project_text_features(tangent).squeeze(0))
    return torch.stack(class_embeddings, dim=0)


def _imagenet_prompt_names(class_names: list[str], imagenet_val_root: Path) -> list[str]:
    if len(class_names) == 1000 and all(_looks_like_wnid(class_name) for class_name in class_names):
        from torchvision.models._meta import _IMAGENET_CATEGORIES

        label_index = imagenet_val_root / "imagenet_label_to_wnid.tsv"
        if label_index.exists():
            wnid_to_label: dict[str, int] = {}
            for line in label_index.read_text(encoding="utf-8").splitlines():
                label, wnid = line.split("\t", maxsplit=1)
                wnid_to_label[wnid] = int(label)
            return [_IMAGENET_CATEGORIES[wnid_to_label[class_name]] for class_name in class_names]
        return list(_IMAGENET_CATEGORIES)
    return class_names


def _looks_like_wnid(class_name: str) -> bool:
    return len(class_name) == 9 and class_name.startswith("n") and class_name[1:].isdigit()
