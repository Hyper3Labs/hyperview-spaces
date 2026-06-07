from __future__ import annotations

import csv
import hashlib
import json
import math
from urllib.parse import urlparse
import urllib.request
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

import torch
from PIL import Image
from torch.utils.data import Dataset

from hyper3_clip.data.transforms import build_eval_transform
from hyper3_clip.models.hyper3_clip import Hyper3CLIP
from hyper3_clip.models.losses import factor_oxy_angle


@dataclass(frozen=True)
class PEPSample:
    image_id: str
    image_path: Path | None
    image_url: str | None
    positive_captions: tuple[str, ...]
    negative_captions: tuple[str, ...] = ()


class PEPEntailmentDataset(Dataset):
    def __init__(
        self,
        annotations_path: str | Path,
        image_root: str | Path | None = None,
        image_size: int = 224,
        max_items: int | None = None,
        image_cache_dir: str | Path | None = None,
        allow_image_download: bool = False,
    ) -> None:
        self.samples, self.global_negative_captions = load_pep_samples(
            annotations_path,
            image_root=image_root,
            max_items=max_items,
        )
        self.transform = build_eval_transform(image_size)
        self.image_cache_dir = Path(image_cache_dir) if image_cache_dir is not None else None
        self.allow_image_download = allow_image_download

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, index: int) -> dict[str, Any]:
        sample = self.samples[index]
        image = _load_sample_image(sample, self.image_cache_dir, self.allow_image_download)
        return {
            "image": self.transform(image.convert("RGB")),
            "image_id": sample.image_id,
            "positive_captions": sample.positive_captions,
            "negative_captions": sample.negative_captions,
        }


@torch.inference_mode()
def evaluate_pep_entailment(
    model: Hyper3CLIP,
    annotations_path: str | Path,
    device: torch.device,
    image_root: str | Path | None = None,
    image_size: int = 224,
    max_text_length: int = 77,
    batch_size: int = 128,
    max_items: int | None = None,
    image_cache_dir: str | Path | None = None,
    allow_image_download: bool = False,
    negative_pool_strategy: str = "annotation",
    max_negatives_per_image: int | None = None,
    pair_batch_size: int = 8192,
) -> dict[str, float]:
    """Evaluate ARGENT-style PEP entailment AUC/AP.

    PEP treats image-caption hierarchy evaluation as binary entailment
    classification. Positives are the hierarchical captions attached to the same
    image. Negatives come either from explicit annotation/global pools, or from
    other samples' finest captions when ``negative_pool_strategy`` is
    ``"all_fine_captions"``.
    """
    if negative_pool_strategy not in {"annotation", "all_fine_captions"}:
        raise ValueError("negative_pool_strategy must be 'annotation' or 'all_fine_captions'")

    model.eval()
    dataset = PEPEntailmentDataset(
        annotations_path,
        image_root=image_root,
        image_size=image_size,
        max_items=max_items,
        image_cache_dir=image_cache_dir,
        allow_image_download=allow_image_download,
    )
    if len(dataset) == 0:
        raise ValueError("PEP evaluation requires at least one sample")

    image_feats = _encode_images(model, dataset, device, batch_size)
    pair_image_indices, pair_captions, labels = _build_pep_pairs(
        dataset.samples,
        dataset.global_negative_captions,
        negative_pool_strategy=negative_pool_strategy,
        max_negatives_per_image=max_negatives_per_image,
    )
    if not any(labels) or all(labels):
        raise ValueError("PEP evaluation requires both positive and negative pairs")

    captions = sorted(set(pair_captions))
    caption_to_index = {caption: index for index, caption in enumerate(captions)}
    text_feats = _encode_texts(model, captions, device, max_text_length, batch_size)
    pair_text_indices = [caption_to_index[caption] for caption in pair_captions]
    scores = _score_pep_pairs(
        model,
        image_feats,
        text_feats,
        pair_image_indices,
        pair_text_indices,
        device,
        pair_batch_size=pair_batch_size,
    )

    auc = _roc_auc_score(labels, scores)
    ap = _average_precision_score(labels, scores)
    positive_scores = [score for score, label in zip(scores, labels) if label == 1]
    negative_scores = [score for score, label in zip(scores, labels) if label == 0]
    return {
        "auc_roc": auc,
        "average_precision": ap,
        "auc_roc_pct": 100.0 * auc,
        "average_precision_pct": 100.0 * ap,
        "num_samples": float(len(dataset.samples)),
        "num_pairs": float(len(labels)),
        "num_positive_pairs": float(sum(labels)),
        "num_negative_pairs": float(len(labels) - sum(labels)),
        "mean_positive_score": float(sum(positive_scores) / len(positive_scores)),
        "mean_negative_score": float(sum(negative_scores) / len(negative_scores)),
    }


def probabilistic_entailment_score(
    specific: torch.Tensor,
    general: torch.Tensor,
    kappa: torch.Tensor,
) -> torch.Tensor:
    angles = factor_oxy_angle(specific=specific, general=general, kappa=kappa)
    if angles.dim() == 2:
        angles = angles.mean(dim=-1)
    return torch.clamp(1.0 - (2.0 * angles / math.pi), min=0.0, max=1.0)


def load_pep_samples(
    annotations_path: str | Path,
    image_root: str | Path | None = None,
    max_items: int | None = None,
) -> tuple[list[PEPSample], tuple[str, ...]]:
    path = Path(annotations_path)
    if path.suffix.lower() == ".jsonl":
        samples = [_sample_from_mapping(json.loads(line), image_root) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        return _limit_samples(samples, max_items), ()
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        samples_payload = payload.get("samples", payload.get("data", [])) if isinstance(payload, dict) else payload
        global_negatives = _caption_tuple(
            payload.get("negative_captions") or payload.get("global_negative_captions") or payload.get("negative_pool")
        ) if isinstance(payload, dict) else ()
        samples = [_sample_from_mapping(item, image_root) for item in samples_payload]
        return _limit_samples(samples, max_items), global_negatives
    if path.suffix.lower() in {".csv", ".tsv"}:
        return _load_csv_samples(path, image_root, max_items)
    raise ValueError(f"Unsupported PEP annotations format {path.suffix!r}; expected .json, .jsonl, .csv, or .tsv")


def _load_csv_samples(
    path: Path,
    image_root: str | Path | None,
    max_items: int | None,
) -> tuple[list[PEPSample], tuple[str, ...]]:
    delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter=delimiter))
    if not rows:
        return [], ()

    has_pair_labels = "caption" in rows[0] and "label" in rows[0]
    if has_pair_labels:
        grouped: dict[str, dict[str, Any]] = {}
        for row in rows:
            key = _image_key(row)
            item = grouped.setdefault(key, {**row, "positive_captions": [], "negative_captions": []})
            if _truthy_label(row["label"]):
                item["positive_captions"].append(row["caption"])
            else:
                item["negative_captions"].append(row["caption"])
        samples = [_sample_from_mapping(item, image_root) for item in grouped.values()]
        return _limit_samples(samples, max_items), ()

    samples = [_sample_from_mapping(row, image_root) for row in rows]
    return _limit_samples(samples, max_items), ()


def _sample_from_mapping(item: dict[str, Any], image_root: str | Path | None) -> PEPSample:
    positives = _extract_positive_captions(item)
    if not positives:
        raise ValueError(f"PEP sample {item.get('id', item.get('image_id', '<unknown>'))!r} has no positive captions")
    image_path = _extract_image_path(item, image_root)
    image_url = _first_present(item, ("image_url", "url"))
    if image_path is None and not image_url:
        raise ValueError(f"PEP sample {item.get('id', item.get('image_id', '<unknown>'))!r} has no image path or URL")
    image_id = str(_first_present(item, ("image_id", "id", "uid")) or image_path or image_url)
    negatives = _caption_tuple(_first_present(item, ("negative_captions", "negatives", "negative_pool")))
    return PEPSample(
        image_id=image_id,
        image_path=image_path,
        image_url=str(image_url) if image_url else None,
        positive_captions=positives,
        negative_captions=negatives,
    )


def _extract_positive_captions(item: dict[str, Any]) -> tuple[str, ...]:
    raw = _first_present(item, ("positive_captions", "hierarchical_captions", "caption_hierarchy", "captions"))
    captions = _caption_tuple(raw)
    if captions:
        return captions
    caption = item.get("caption")
    return (str(caption).strip(),) if caption else ()


def _caption_tuple(raw: Any) -> tuple[str, ...]:
    if raw is None:
        return ()
    if isinstance(raw, str):
        stripped = raw.strip()
        if not stripped:
            return ()
        if stripped.startswith("["):
            try:
                parsed = json.loads(stripped)
                return _caption_tuple(parsed)
            except json.JSONDecodeError:
                pass
        separator = "=>" if "=>" in stripped else "||" if "||" in stripped else None
        values = stripped.split(separator) if separator else [stripped]
        return tuple(value.strip() for value in values if value.strip())
    if isinstance(raw, (list, tuple)):
        return tuple(str(value).strip() for value in raw if str(value).strip())
    return (str(raw).strip(),)


def _extract_image_path(item: dict[str, Any], image_root: str | Path | None) -> Path | None:
    raw = _first_present(item, ("image_path", "path", "file_name", "filename"))
    if raw is None:
        image_url = _first_present(item, ("image_url", "url"))
        if image_url is None or image_root is None:
            return None
        return _url_to_local_image_path(str(image_url), Path(image_root))
    path = Path(str(raw))
    if not path.is_absolute() and image_root is not None:
        path = Path(image_root) / path
    return path


def _url_to_local_image_path(url: str, image_root: Path) -> Path:
    url_path = Path(urlparse(url).path)
    filename = url_path.name
    if not filename:
        raise ValueError(f"Cannot infer image filename from URL {url!r}")
    candidates = [image_root / filename]
    if url_path.parent.name:
        candidates.append(image_root / url_path.parent.name / filename)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def _first_present(item: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = item.get(key)
        if value not in (None, ""):
            return value
    return None


def _image_key(row: dict[str, Any]) -> str:
    return str(_first_present(row, ("image_id", "id", "image_path", "path", "file_name", "filename", "image_url", "url")))


def _truthy_label(raw: Any) -> bool:
    return str(raw).strip().lower() in {"1", "true", "yes", "positive", "pos"}


def _limit_samples(samples: list[PEPSample], max_items: int | None) -> list[PEPSample]:
    return samples[:max_items] if max_items is not None else samples


def _load_sample_image(sample: PEPSample, image_cache_dir: Path | None, allow_image_download: bool) -> Image.Image:
    if sample.image_path is not None:
        with Image.open(sample.image_path) as image:
            return image.convert("RGB")
    if not sample.image_url:
        raise ValueError(f"PEP sample {sample.image_id!r} has no image path or URL")
    if not allow_image_download:
        raise ValueError("PEP sample uses image_url; set allow_image_download=true and image_cache_dir to evaluate it")
    if image_cache_dir is None:
        with urllib.request.urlopen(sample.image_url, timeout=30) as response:
            return Image.open(BytesIO(response.read())).convert("RGB")
    image_cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = image_cache_dir / _url_cache_name(sample.image_url)
    if not cache_path.exists():
        urllib.request.urlretrieve(sample.image_url, cache_path)
    with Image.open(cache_path) as image:
        return image.convert("RGB")


def _url_cache_name(url: str) -> str:
    suffix = Path(url.split("?", maxsplit=1)[0]).suffix or ".jpg"
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    return f"{digest}{suffix}"


def _encode_images(
    model: Hyper3CLIP,
    dataset: PEPEntailmentDataset,
    device: torch.device,
    batch_size: int,
) -> torch.Tensor:
    feats: list[torch.Tensor] = []
    batch: list[torch.Tensor] = []
    for index in range(len(dataset)):
        batch.append(dataset[index]["image"])
        if len(batch) == batch_size or index == len(dataset) - 1:
            images = torch.stack(batch).to(device)
            feats.append(model.encode_image(images).cpu())
            batch = []
    return torch.cat(feats)


def _encode_texts(
    model: Hyper3CLIP,
    captions: list[str],
    device: torch.device,
    max_text_length: int,
    batch_size: int,
) -> torch.Tensor:
    feats: list[torch.Tensor] = []
    for start in range(0, len(captions), batch_size):
        batch = captions[start : start + batch_size]
        tokenized = model.tokenizer(
            batch,
            padding=True,
            truncation=True,
            max_length=max_text_length,
            return_tensors="pt",
        ).to(device)
        attention_mask = (
            tokenized.attention_mask if "attention_mask" in tokenized else torch.ones_like(tokenized.input_ids)
        )
        feats.append(model.encode_text(tokenized.input_ids, attention_mask).cpu())
    return torch.cat(feats)


def _build_pep_pairs(
    samples: list[PEPSample],
    global_negative_captions: tuple[str, ...],
    negative_pool_strategy: str,
    max_negatives_per_image: int | None,
) -> tuple[list[int], list[str], list[int]]:
    fine_caption_pool = tuple(sample.positive_captions[-1] for sample in samples)
    pair_image_indices: list[int] = []
    pair_captions: list[str] = []
    labels: list[int] = []
    for image_index, sample in enumerate(samples):
        positives = set(sample.positive_captions)
        for caption in sample.positive_captions:
            pair_image_indices.append(image_index)
            pair_captions.append(caption)
            labels.append(1)

        negatives = sample.negative_captions or global_negative_captions
        if not negatives and negative_pool_strategy == "all_fine_captions":
            negatives = tuple(caption for idx, caption in enumerate(fine_caption_pool) if idx != image_index)
        negatives = tuple(caption for caption in negatives if caption not in positives)
        if max_negatives_per_image is not None:
            negatives = negatives[:max_negatives_per_image]
        for caption in negatives:
            pair_image_indices.append(image_index)
            pair_captions.append(caption)
            labels.append(0)
    return pair_image_indices, pair_captions, labels


def _score_pep_pairs(
    model: Hyper3CLIP,
    image_feats: torch.Tensor,
    text_feats: torch.Tensor,
    pair_image_indices: list[int],
    pair_text_indices: list[int],
    device: torch.device,
    pair_batch_size: int,
) -> list[float]:
    kappa = model._kappa().detach().to(device)
    scores: list[torch.Tensor] = []
    for start in range(0, len(pair_image_indices), pair_batch_size):
        image_index = torch.tensor(pair_image_indices[start : start + pair_batch_size], dtype=torch.long)
        text_index = torch.tensor(pair_text_indices[start : start + pair_batch_size], dtype=torch.long)
        batch_images = image_feats.index_select(0, image_index).to(device)
        batch_texts = text_feats.index_select(0, text_index).to(device)
        scores.append(probabilistic_entailment_score(batch_images, batch_texts, kappa).cpu())
    return torch.cat(scores).tolist()


def _roc_auc_score(labels: list[int], scores: list[float]) -> float:
    positives = sum(labels)
    negatives = len(labels) - positives
    if positives == 0 or negatives == 0:
        raise ValueError("ROC AUC requires both positive and negative labels")

    sorted_pairs = sorted(zip(scores, labels), key=lambda pair: pair[0])
    rank_sum_pos = 0.0
    rank = 1
    index = 0
    while index < len(sorted_pairs):
        end = index + 1
        while end < len(sorted_pairs) and sorted_pairs[end][0] == sorted_pairs[index][0]:
            end += 1
        avg_rank = (rank + rank + (end - index) - 1) / 2.0
        rank_sum_pos += avg_rank * sum(label for _, label in sorted_pairs[index:end])
        rank += end - index
        index = end
    return (rank_sum_pos - positives * (positives + 1) / 2.0) / (positives * negatives)


def _average_precision_score(labels: list[int], scores: list[float]) -> float:
    positives = sum(labels)
    if positives == 0:
        raise ValueError("Average precision requires at least one positive label")

    sorted_pairs = sorted(zip(scores, labels), key=lambda pair: pair[0], reverse=True)
    true_positives = 0
    false_positives = 0
    previous_recall = 0.0
    ap = 0.0
    index = 0
    while index < len(sorted_pairs):
        end = index + 1
        while end < len(sorted_pairs) and sorted_pairs[end][0] == sorted_pairs[index][0]:
            end += 1
        true_positives += sum(label for _, label in sorted_pairs[index:end])
        false_positives += (end - index) - sum(label for _, label in sorted_pairs[index:end])
        recall = true_positives / positives
        precision = true_positives / (true_positives + false_positives)
        ap += (recall - previous_recall) * precision
        previous_recall = recall
        index = end
    return ap
