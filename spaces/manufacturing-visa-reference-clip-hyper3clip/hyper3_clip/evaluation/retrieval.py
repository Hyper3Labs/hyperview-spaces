from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import torch
from PIL import Image
from torch.utils.data import Dataset

from hyper3_clip.data.transforms import build_retrieval_transform

from hyper3_clip.models.hyper3_clip import Hyper3CLIP


class CocoCaptionRetrieval(Dataset):
    def __init__(
        self,
        root: str | Path,
        image_size: int = 224,
        max_items: int | None = None,
        image_normalization: str = "imagenet",
    ) -> None:
        self.root = Path(root)
        with (self.root / "annotations" / "captions_val2017.json").open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        images = {item["id"]: item["file_name"] for item in payload["images"]}
        captions: dict[int, list[str]] = defaultdict(list)
        for annotation in payload["annotations"]:
            captions[int(annotation["image_id"])].append(str(annotation["caption"]))
        self.items = [
            {"image_id": image_id, "image_path": self.root / "val2017" / images[image_id], "captions": captions[image_id]}
            for image_id in sorted(captions)
        ]
        if max_items is not None:
            self.items = self.items[:max_items]
        self.transform = build_retrieval_transform(image_size, normalization=image_normalization)

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, index: int) -> dict[str, Any]:
        item = self.items[index]
        with Image.open(item["image_path"]) as image:
            tensor = self.transform(image.convert("RGB"))
        return {"image": tensor, "captions": item["captions"], "image_id": item["image_id"]}


class CocoKarpathyCaptionRetrieval(Dataset):
    def __init__(
        self,
        root: str | Path,
        split: str = "test",
        image_size: int = 224,
        max_items: int | None = None,
        image_normalization: str = "imagenet",
    ) -> None:
        self.root = Path(root)
        with (self.root / "karpathy" / "dataset_coco.json").open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        images = [item for item in payload["images"] if item["split"] == split]
        if max_items is not None:
            images = images[:max_items]
        self.items = [
            {
                "image_id": item["imgid"],
                "image_path": self.root / item["filepath"] / item["filename"],
                "captions": [sentence["raw"].strip() for sentence in item["sentences"]],
            }
            for item in images
        ]
        self.transform = build_retrieval_transform(image_size, normalization=image_normalization)

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, index: int) -> dict[str, Any]:
        item = self.items[index]
        with Image.open(item["image_path"]) as image:
            tensor = self.transform(image.convert("RGB"))
        return {"image": tensor, "captions": item["captions"], "image_id": item["image_id"]}


class Flickr30kCaptionRetrieval(Dataset):
    def __init__(
        self,
        root: str | Path,
        split: str = "test",
        image_size: int = 224,
        max_items: int | None = None,
        image_normalization: str = "imagenet",
    ) -> None:
        self.root = Path(root)
        with (self.root / "dataset_flickr30k.json").open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        self.items = []
        for index, image_payload in enumerate(payload["images"]):
            if image_payload.get("split") != split:
                continue
            captions = [str(sentence.get("raw") or " ".join(sentence.get("tokens", []))) for sentence in image_payload["sentences"]]
            self.items.append(
                {
                    "image_id": index,
                    "image_path": self.root / "flickr30k_images" / image_payload["filename"],
                    "captions": captions,
                }
            )
        if max_items is not None:
            self.items = self.items[:max_items]
        self.transform = build_retrieval_transform(image_size, normalization=image_normalization)

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, index: int) -> dict[str, Any]:
        item = self.items[index]
        with Image.open(item["image_path"]) as image:
            tensor = self.transform(image.convert("RGB"))
        return {"image": tensor, "captions": item["captions"], "image_id": item["image_id"]}


@torch.inference_mode()
def evaluate_caption_retrieval(
    model: Hyper3CLIP,
    dataset: Dataset,
    device: torch.device,
    max_text_length: int = 77,
    batch_size: int = 128,
) -> dict[str, float]:
    model.eval()
    image_feats: list[torch.Tensor] = []
    captions: list[str] = []
    text_feats: list[torch.Tensor] = []
    text_to_image: list[int] = []

    image_batch: list[torch.Tensor] = []
    for item_index in range(len(dataset)):
        item = dataset[item_index]
        image_batch.append(item["image"])
        if len(image_batch) == batch_size or item_index == len(dataset) - 1:
            images = torch.stack(image_batch).to(device)
            image_feats.append(model.encode_retrieval_image(images).cpu())
            image_batch = []
        captions.extend(item["captions"])
        text_to_image.extend([item_index] * len(item["captions"]))

    for start in range(0, len(captions), batch_size):
        caption_batch = captions[start : start + batch_size]
        tokenized = model.tokenizer(
            caption_batch,
            padding=True,
            truncation=True,
            max_length=max_text_length,
            return_tensors="pt",
        ).to(device)
        attention_mask = (
            tokenized.attention_mask if "attention_mask" in tokenized else torch.ones_like(tokenized.input_ids)
        )
        text_feats.append(model.encode_retrieval_text(tokenized.input_ids, attention_mask).cpu())

    images = torch.cat(image_feats).to(device)
    texts = torch.cat(text_feats).to(device)
    scores_i2t = _retrieval_similarity_scores(model, images, texts, chunk_size=max(1, min(batch_size, 64)))
    scores_t2i = scores_i2t.transpose(0, 1)
    target_device = scores_i2t.device
    text_targets = torch.tensor(text_to_image, device=target_device)
    fractions = {
        "image_to_text_r1": _recall_at_k(scores_i2t, _image_to_text_targets(text_to_image, len(dataset), target_device), 1),
        "image_to_text_r5": _recall_at_k(scores_i2t, _image_to_text_targets(text_to_image, len(dataset), target_device), 5),
        "image_to_text_r10": _recall_at_k(scores_i2t, _image_to_text_targets(text_to_image, len(dataset), target_device), 10),
        "text_to_image_r1": _single_target_recall_at_k(scores_t2i, text_targets, 1),
        "text_to_image_r5": _single_target_recall_at_k(scores_t2i, text_targets, 5),
        "text_to_image_r10": _single_target_recall_at_k(scores_t2i, text_targets, 10),
    }
    return {
        **fractions,
        "i2t_r1": 100.0 * fractions["image_to_text_r1"],
        "i2t_r5": 100.0 * fractions["image_to_text_r5"],
        "i2t_r10": 100.0 * fractions["image_to_text_r10"],
        "t2i_r1": 100.0 * fractions["text_to_image_r1"],
        "t2i_r5": 100.0 * fractions["text_to_image_r5"],
        "t2i_r10": 100.0 * fractions["text_to_image_r10"],
    }


def _retrieval_similarity_scores(
    model: Hyper3CLIP, images: torch.Tensor, texts: torch.Tensor, chunk_size: int
) -> torch.Tensor:
    if not getattr(model, "retrieval_requires_chunking", False):
        return model.retrieval_similarity_scores(images, texts)

    chunks: list[torch.Tensor] = []
    for start in range(0, images.shape[0], chunk_size):
        chunk_scores = model.retrieval_similarity_scores(images[start : start + chunk_size], texts)
        chunks.append(chunk_scores.cpu())
    return torch.cat(chunks, dim=0)


def _image_to_text_targets(text_to_image: list[int], num_images: int, device: torch.device) -> list[torch.Tensor]:
    targets: list[list[int]] = [[] for _ in range(num_images)]
    for text_index, image_index in enumerate(text_to_image):
        targets[image_index].append(text_index)
    return [torch.tensor(indices, device=device) for indices in targets]


def _recall_at_k(scores: torch.Tensor, targets: list[torch.Tensor], k: int) -> float:
    topk = scores.topk(k=min(k, scores.shape[1]), dim=1).indices
    hits = [bool(torch.isin(targets[row], topk[row]).any().item()) for row in range(scores.shape[0])]
    return float(sum(hits) / len(hits))


def _single_target_recall_at_k(scores: torch.Tensor, targets: torch.Tensor, k: int) -> float:
    topk = scores.topk(k=min(k, scores.shape[1]), dim=1).indices
    return float((topk == targets[:, None]).any(dim=1).float().mean().item())
