from __future__ import annotations

import re
from typing import Any

import torch


def _attention_mask(tokens) -> torch.Tensor:
    if "attention_mask" in tokens:
        return tokens["attention_mask"]
    return torch.ones_like(tokens["input_ids"])


def collate_grounded(
    batch: list[dict[str, Any]],
    tokenizer,
    max_text_length: int,
    *,
    beta_clip_queries: bool = False,
    beta_clip_max_sentences: int = 5,
    beta_clip_max_phrases: int = 30,
    beta_clip_max_queries_per_image: int | None = None,
    beta_clip_use_part_texts: bool = True,
) -> dict[str, torch.Tensor]:
    images = torch.stack([item["image"] for item in batch])
    captions = [item["caption"] for item in batch]
    part_image_rows: list[torch.Tensor] = []
    part_texts: list[str] = []
    part_owner: list[int] = []

    for batch_index, item in enumerate(batch):
        for part_index, part_image in enumerate(item["part_images"]):
            part_image_rows.append(part_image)
            part_texts.append(item["part_texts"][part_index])
            part_owner.append(batch_index)

    text = tokenizer(captions, padding=True, truncation=True, max_length=max_text_length, return_tensors="pt")
    text_attention_mask = _attention_mask(text)
    if part_image_rows:
        part_images = torch.stack(part_image_rows)
        part_text = tokenizer(part_texts, padding=True, truncation=True, max_length=max_text_length, return_tensors="pt")
        part_text_input_ids = part_text["input_ids"]
        part_text_attention_mask = _attention_mask(part_text)
    else:
        part_images = images.new_zeros((0, *images.shape[1:]))
        empty_text_shape = (0, text["input_ids"].shape[1])
        part_text_input_ids = text["input_ids"].new_zeros(empty_text_shape)
        part_text_attention_mask = text_attention_mask.new_zeros(empty_text_shape)

    collated = {
        "image": images,
        "part_images": part_images,
        "part_owner": torch.tensor(part_owner, dtype=torch.long),
        "text_input_ids": text["input_ids"],
        "text_attention_mask": text_attention_mask,
        "part_text_input_ids": part_text_input_ids,
        "part_text_attention_mask": part_text_attention_mask,
    }

    if beta_clip_queries:
        query_texts: list[str] = []
        query_owner: list[int] = []
        query_type: list[int] = []
        query_parent: list[int] = []
        query_weight: list[float] = []
        query_source_part: list[int] = []
        part_offsets = []
        cursor = 0
        for item in batch:
            part_offsets.append(cursor)
            cursor += len(item["part_images"])
        for batch_index, item in enumerate(batch):
            image_queries = _beta_clip_query_items_for_item(
                caption=item["caption"],
                part_texts=item["part_texts"],
                max_sentences=beta_clip_max_sentences,
                max_phrases=beta_clip_max_phrases,
                max_queries=beta_clip_max_queries_per_image,
                use_part_texts=beta_clip_use_part_texts,
            )
            query_offset = len(query_texts)
            for query in image_queries:
                query_texts.append(query["text"])
                query_owner.append(batch_index)
                query_type.append(query["type"])
                local_parent = query["parent"]
                query_parent.append(-1 if local_parent < 0 else query_offset + local_parent)
                query_weight.append(query["weight"])
                local_part = query["source_part"]
                query_source_part.append(-1 if local_part < 0 else part_offsets[batch_index] + local_part)
        query_tokens = tokenizer(query_texts, padding=True, truncation=True, max_length=max_text_length, return_tensors="pt")
        collated.update(
            {
                "beta_query_input_ids": query_tokens["input_ids"],
                "beta_query_attention_mask": _attention_mask(query_tokens),
                "beta_query_owner": torch.tensor(query_owner, dtype=torch.long),
                "beta_query_type": torch.tensor(query_type, dtype=torch.long),
                "beta_query_parent": torch.tensor(query_parent, dtype=torch.long),
                "beta_query_weight": torch.tensor(query_weight, dtype=torch.float32),
                "beta_query_source_part": torch.tensor(query_source_part, dtype=torch.long),
            }
        )

    return collated


def _beta_clip_queries_for_item(
    *,
    caption: str,
    part_texts: list[str],
    max_sentences: int,
    max_phrases: int,
    max_queries: int | None,
    use_part_texts: bool,
) -> list[str]:
    return [
        query["text"]
        for query in _beta_clip_query_items_for_item(
            caption=caption,
            part_texts=part_texts,
            max_sentences=max_sentences,
            max_phrases=max_phrases,
            max_queries=max_queries,
            use_part_texts=use_part_texts,
        )
    ]


def _beta_clip_query_items_for_item(
    *,
    caption: str,
    part_texts: list[str],
    max_sentences: int,
    max_phrases: int,
    max_queries: int | None,
    use_part_texts: bool,
) -> list[dict[str, str | int | float]]:
    queries: list[str] = []
    query_items: list[dict[str, str | int | float]] = []
    seen: set[str] = set()

    def add_query(text: str, *, query_type: int, parent: int = 0, weight: float = 1.0, source_part: int = -1) -> int:
        normalized = " ".join(str(text).strip().split())
        key = normalized.casefold()
        if len(normalized) >= 3 and key not in seen:
            seen.add(key)
            queries.append(normalized)
            query_items.append(
                {
                    "text": normalized,
                    "type": query_type,
                    "parent": parent,
                    "weight": weight,
                    "source_part": source_part,
                }
            )
            return len(queries) - 1
        return -1

    caption_index = add_query(caption, query_type=0, parent=-1, weight=0.0)
    if caption_index < 0:
        caption_index = 0
    sentence_indices: list[int] = []
    for sentence in _split_sentences(caption)[: max(0, max_sentences)]:
        sentence_index = add_query(sentence, query_type=1, parent=caption_index, weight=1.0)
        if sentence_index >= 0:
            sentence_indices.append(sentence_index)
    phrase_parent = sentence_indices[0] if sentence_indices else caption_index

    phrase_count = 0
    if use_part_texts:
        for part_index, part_text in enumerate(part_texts):
            if phrase_count >= max_phrases:
                break
            before = len(queries)
            add_query(part_text, query_type=2, parent=caption_index, weight=0.75, source_part=part_index)
            phrase_count += int(len(queries) > before)

    if phrase_count < max_phrases:
        for phrase in _extract_lightweight_phrases(caption):
            if phrase_count >= max_phrases:
                break
            before = len(queries)
            add_query(phrase, query_type=3, parent=phrase_parent, weight=0.5)
            phrase_count += int(len(queries) > before)

    if max_queries is not None:
        return query_items[: max(1, int(max_queries))]
    return query_items


def _split_sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?;])\s+|\n+", text) if part.strip()]


def _extract_lightweight_phrases(text: str) -> list[str]:
    chunks = re.split(r"[,;:()]|\s+(?:and|with|near|beside|behind|under|above|around|next to)\s+", text, flags=re.I)
    phrases: list[str] = []
    for chunk in chunks:
        words = re.findall(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)?", chunk)
        if 2 <= len(words) <= 8:
            phrases.append(" ".join(words))
        elif len(words) > 8:
            for start in range(0, len(words) - 1, 4):
                phrase = " ".join(words[start : start + 6])
                if len(phrase.split()) >= 2:
                    phrases.append(phrase)
    return phrases
