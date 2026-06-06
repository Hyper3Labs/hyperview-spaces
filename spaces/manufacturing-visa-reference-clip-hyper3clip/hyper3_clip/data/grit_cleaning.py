from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass
from typing import Any

import numpy as np
from PIL import Image


SPACE_RE = re.compile(r"\s+")
URL_RE = re.compile(r"(https?://|www\.|\.com\b|\.net\b|\.org\b)", re.IGNORECASE)
EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w.-]+\.\w+\b")
HTML_RE = re.compile(r"<[^>]+>")
TOKEN_RE = re.compile(r"[a-z0-9]+(?:[-'][a-z0-9]+)?")

LEADING_DETERMINERS = {
    "a",
    "an",
    "the",
    "this",
    "that",
    "these",
    "those",
    "his",
    "her",
    "its",
    "their",
    "my",
    "our",
    "your",
}

QUANTITY_WORDS = {
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "many",
    "several",
    "some",
    "few",
    "group",
    "pair",
}

VISUAL_MODIFIERS = {
    "big",
    "small",
    "large",
    "little",
    "old",
    "young",
    "new",
    "red",
    "blue",
    "green",
    "yellow",
    "white",
    "black",
    "brown",
    "gray",
    "grey",
    "orange",
    "pink",
    "purple",
    "colorful",
    "colourful",
    "wooden",
    "metal",
    "plastic",
    "striped",
}

NON_VISUAL_HEADS = {
    "background",
    "foreground",
    "caption",
    "copyright",
    "credit",
    "item",
    "edge",
    "image",
    "left",
    "logo",
    "method",
    "middle",
    "number",
    "photo",
    "photograph",
    "picture",
    "place",
    "right",
    "scene",
    "side",
    "statement",
    "stock",
    "text",
    "thing",
    "view",
    "watermark",
}

NON_VISUAL_PHRASES = {
    "available at",
    "all rights reserved",
    "click here",
    "copyright",
    "getty images",
    "istock",
    "shutterstock",
    "stock photo",
}

ACTION_SPLITS = (
    " standing ",
    " sitting ",
    " lying ",
    " walking ",
    " running ",
    " flying ",
    " eating ",
    " holding ",
    " wearing ",
    " playing ",
)

PREPOSITION_SPLITS = (
    " next to ",
    " in front of ",
    " on top of ",
    " inside ",
    " outside ",
    " with ",
    " without ",
    " near ",
    " beside ",
    " behind ",
    " under ",
    " over ",
    " from ",
    " into ",
    " across ",
    " around ",
    " at ",
    " on ",
    " in ",
    " of ",
)

CANONICAL_REWRITES = {
    "aeroplane": "airplane",
    "aircraft": "airplane",
    "bike": "bicycle",
    "cell phone": "phone",
    "mobile phone": "phone",
    "motorbike": "motorcycle",
    "plant pot": "potted plant",
    "tv": "television",
}

TOKEN_SYNONYMS = {
    "airplane": {"airplane", "aeroplane", "aircraft", "plane"},
    "bicycle": {"bicycle", "bike"},
    "motorcycle": {"motorcycle", "motorbike"},
    "person": {"person", "people", "man", "woman", "boy", "girl", "teenager", "teenagers"},
    "people": {"person", "people", "man", "woman", "men", "women", "children", "teenager", "teenagers"},
    "phone": {"phone", "cell", "mobile", "telephone"},
    "television": {"television", "tv"},
}

HUMAN_GROUP_WORDS = {
    "adults",
    "boys",
    "children",
    "crowd",
    "girls",
    "kids",
    "men",
    "people",
    "teenagers",
    "teens",
    "women",
}

HUMAN_SINGULAR_WORDS = {
    "adult",
    "baby",
    "boy",
    "child",
    "girl",
    "kid",
    "man",
    "person",
    "teenager",
    "woman",
}

HUMAN_ROLE_WORDS = {
    "actor",
    "actress",
    "artist",
    "athlete",
    "boss",
    "coach",
    "doctor",
    "lawyer",
    "manager",
    "minister",
    "musician",
    "player",
    "politician",
    "president",
    "singer",
    "teacher",
}

DEFAULT_HYPERNYMS = {
    "airplane": ("aircraft", "vehicle"),
    "apple": ("fruit", "food"),
    "backpack": ("bag", "accessory"),
    "baseball bat": ("bat", "sports equipment"),
    "bear": ("mammal", "animal"),
    "bicycle": ("vehicle",),
    "bird": ("animal",),
    "boat": ("vehicle",),
    "bottle": ("container",),
    "bus": ("vehicle",),
    "car": ("vehicle",),
    "cat": ("mammal", "animal"),
    "chair": ("furniture",),
    "cup": ("container",),
    "dog": ("mammal", "animal"),
    "flower": ("plant",),
    "fork": ("utensil",),
    "horse": ("mammal", "animal"),
    "knife": ("utensil",),
    "lamp": ("light", "furniture"),
    "laptop": ("computer", "electronic device"),
    "person": ("human", "animal"),
    "phone": ("electronic device",),
    "potted plant": ("plant",),
    "shirt": ("clothing",),
    "shoe": ("footwear", "clothing"),
    "skis": ("sports equipment",),
    "spoon": ("utensil",),
    "sports ball": ("ball", "sports equipment"),
    "table": ("furniture",),
    "television": ("electronic device",),
    "train": ("vehicle",),
    "tree": ("plant",),
    "truck": ("vehicle",),
}


@dataclass(frozen=True)
class ImageQuality:
    width: int
    height: int
    brightness: float
    contrast: float
    entropy: float
    black_border_fraction: float


@dataclass(frozen=True)
class ParentCleanDecision:
    original_text: str
    canonical_text: str
    keep: bool
    quality_score: float
    reasons: tuple[str, ...]
    hypernyms: tuple[str, ...]
    image_quality: ImageQuality | None = None


def clean_parent(
    parent_text: str,
    caption: str = "",
    parent_image: Image.Image | None = None,
    min_score: float = 0.45,
    hypernym_map: dict[str, tuple[str, ...]] | None = None,
) -> ParentCleanDecision:
    canonical = canonicalize_parent_text(parent_text)
    reasons: list[str] = []
    fatal = False

    if not canonical:
        reasons.append("empty_after_canonicalization")
        fatal = True
    if looks_like_boilerplate(parent_text):
        reasons.append("boilerplate_or_url")
        fatal = True
    if canonical and is_non_visual_parent(canonical):
        reasons.append("non_visual_parent")
        fatal = True
    if canonical and len(canonical.split()) > 6:
        reasons.append("too_long_for_clean_parent")
    if canonical and caption_duplicates_parent(caption, canonical):
        reasons.append("duplicates_caption")
        fatal = True
    if canonical and not caption_mentions_parent(caption, canonical):
        reasons.append("caption_does_not_mention_parent")

    image_quality = image_quality_stats(parent_image) if parent_image is not None else None
    if image_quality is not None:
        if image_quality.entropy < 1.0 or image_quality.contrast < 3.0:
            reasons.append("low_information_crop")
        if image_quality.black_border_fraction > 0.65:
            reasons.append("mostly_black_border")
        if (
            "caption_does_not_mention_parent" in reasons
            and "low_information_crop" in reasons
            and "mostly_black_border" in reasons
        ):
            reasons.append("text_slide_or_bad_crop")
            fatal = True

    score = parent_quality_score(canonical, reasons, image_quality)
    hmap = DEFAULT_HYPERNYMS if hypernym_map is None else hypernym_map
    hypernyms = tuple(hmap.get(canonical, ()))
    keep = not fatal and score >= min_score
    return ParentCleanDecision(
        original_text=parent_text,
        canonical_text=canonical,
        keep=keep,
        quality_score=score,
        reasons=tuple(reasons),
        hypernyms=hypernyms,
        image_quality=image_quality,
    )


def canonicalize_parent_text(text: str) -> str:
    text = normalize_text(text)
    if not text:
        return ""
    text = strip_boilerplate_tail(text)
    for marker in ACTION_SPLITS:
        if marker in text:
            text = text.split(marker, maxsplit=1)[0].strip()
            break
    human = canonicalize_human_text(text)
    if human:
        return human
    for marker in PREPOSITION_SPLITS:
        if marker in text:
            text = text.split(marker, maxsplit=1)[0].strip()
            break
    tokens = TOKEN_RE.findall(text)
    while tokens and (tokens[0] in LEADING_DETERMINERS or tokens[0] in QUANTITY_WORDS):
        tokens.pop(0)
    if len(tokens) > 2:
        while tokens and tokens[0] in VISUAL_MODIFIERS:
            tokens.pop(0)
    candidate = " ".join(tokens).strip()
    candidate = CANONICAL_REWRITES.get(candidate, candidate)
    if candidate.endswith("s") and candidate[:-1] in DEFAULT_HYPERNYMS:
        candidate = candidate[:-1]
    return candidate


def canonicalize_human_text(text: str) -> str:
    tokens = TOKEN_RE.findall(text)
    if not tokens:
        return ""
    token_set = set(tokens)
    if token_set.intersection(HUMAN_GROUP_WORDS):
        return "people"
    for word in ("baby", "woman", "man", "girl", "boy", "child", "teenager", "person"):
        if word in token_set:
            return word
    if token_set.intersection(HUMAN_ROLE_WORDS):
        return "person"
    return ""


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", str(text))
    text = HTML_RE.sub(" ", text)
    text = text.replace("_", " ").replace("/", " ")
    text = text.strip().lower()
    text = text.strip(" \t\r\n\"'.,;:!?()[]{}")
    return SPACE_RE.sub(" ", text)


def strip_boilerplate_tail(text: str) -> str:
    for marker in (" - available at ", " available at ", " | ", " © ", " copyright "):
        if marker in text:
            text = text.split(marker, maxsplit=1)[0]
    return text.strip()


def looks_like_boilerplate(text: str) -> bool:
    normalized = normalize_text(text)
    if URL_RE.search(normalized) or EMAIL_RE.search(normalized):
        return True
    return any(phrase in normalized for phrase in NON_VISUAL_PHRASES)


def is_non_visual_parent(canonical: str) -> bool:
    tokens = canonical.split()
    if not tokens:
        return True
    if canonical in NON_VISUAL_HEADS:
        return True
    if tokens[-1] in NON_VISUAL_HEADS:
        return True
    if all(token.isdigit() for token in tokens):
        return True
    return False


def caption_mentions_parent(caption: str, canonical_parent: str) -> bool:
    if not caption or not canonical_parent:
        return True
    caption_tokens = set(TOKEN_RE.findall(normalize_text(caption)))
    parent_tokens = TOKEN_RE.findall(canonical_parent)
    if not parent_tokens:
        return False
    for token in parent_tokens:
        synonyms = TOKEN_SYNONYMS.get(token, {token})
        if not caption_tokens.intersection(synonyms):
            return False
    return True


def caption_duplicates_parent(caption: str, canonical_parent: str) -> bool:
    if not caption or not canonical_parent:
        return False
    caption_tokens = TOKEN_RE.findall(normalize_text(caption))
    parent_tokens = TOKEN_RE.findall(canonical_parent)
    if len(parent_tokens) < 6 or not caption_tokens:
        return False
    caption_set = set(caption_tokens)
    parent_set = set(parent_tokens)
    overlap = len(caption_set.intersection(parent_set))
    return overlap / max(len(parent_set), 1) >= 0.85 and overlap / max(len(caption_set), 1) >= 0.65


def image_quality_stats(image: Image.Image | None) -> ImageQuality | None:
    if image is None:
        return None
    rgb = image.convert("RGB")
    width, height = rgb.size
    gray = np.asarray(rgb.convert("L"), dtype=np.float32)
    brightness = float(gray.mean())
    contrast = float(gray.std())
    hist, _ = np.histogram(gray, bins=64, range=(0, 256), density=True)
    hist = hist[hist > 0]
    entropy = float(-(hist * np.log2(hist)).sum())
    border = _border_pixels(gray)
    black_border_fraction = float((border < 8).mean()) if border.size else 0.0
    return ImageQuality(
        width=width,
        height=height,
        brightness=brightness,
        contrast=contrast,
        entropy=entropy,
        black_border_fraction=black_border_fraction,
    )


def parent_quality_score(canonical: str, reasons: list[str], image_quality: ImageQuality | None) -> float:
    if not canonical:
        return 0.0
    score = 1.0
    penalties = {
        "caption_does_not_mention_parent": 0.20,
        "too_long_for_clean_parent": 0.20,
        "low_information_crop": 0.25,
        "mostly_black_border": 0.15,
        "non_visual_parent": 0.60,
        "boilerplate_or_url": 0.80,
        "duplicates_caption": 0.80,
        "text_slide_or_bad_crop": 0.80,
    }
    for reason in reasons:
        score -= penalties.get(reason, 0.10)
    if image_quality is not None:
        if image_quality.brightness < 8 or image_quality.brightness > 247:
            score -= 0.10
        if image_quality.contrast > 8 and image_quality.entropy > 2:
            score += 0.05
    if canonical in DEFAULT_HYPERNYMS:
        score += 0.05
    return max(0.0, min(1.0, score))


def merge_vlm_decision(
    cheap: ParentCleanDecision,
    vlm_payload: dict[str, Any] | None,
    vlm_can_rescue: bool = False,
) -> ParentCleanDecision:
    if not vlm_payload:
        return cheap
    reasons = list(cheap.reasons)
    canonical = normalize_text(vlm_payload.get("canonical_parent") or cheap.canonical_text)
    if canonical:
        canonical = canonicalize_parent_text(canonical)
    hypernyms = tuple(
        normalize_text(value)
        for value in vlm_payload.get("hypernyms", cheap.hypernyms)
        if normalize_text(value)
    )
    quality_score = float(vlm_payload.get("quality_score", cheap.quality_score))
    keep_payload = vlm_payload.get("keep")
    if keep_payload is False:
        reasons.append("vlm_reject")
        keep = False
    elif keep_payload is True and vlm_can_rescue:
        keep = quality_score >= 0.45 and bool(canonical)
    else:
        keep = cheap.keep and keep_payload is not False
    reject_reason = normalize_text(vlm_payload.get("reject_reason") or "")
    if reject_reason:
        reasons.append(f"vlm:{reject_reason}")
    return ParentCleanDecision(
        original_text=cheap.original_text,
        canonical_text=canonical,
        keep=keep,
        quality_score=max(0.0, min(1.0, quality_score)),
        reasons=tuple(dict.fromkeys(reasons)),
        hypernyms=hypernyms,
        image_quality=cheap.image_quality,
    )


def expand_parent_texts(decision: ParentCleanDecision, add_hypernyms: bool) -> tuple[str, ...]:
    if not decision.keep:
        return ()
    values = [decision.canonical_text]
    if add_hypernyms:
        values.extend(decision.hypernyms)
    return tuple(dict.fromkeys(value for value in values if value))


def _border_pixels(gray: np.ndarray) -> np.ndarray:
    if gray.ndim != 2 or min(gray.shape) < 4:
        return np.asarray([], dtype=np.float32)
    width = max(1, min(gray.shape) // 16)
    top = gray[:width, :].reshape(-1)
    bottom = gray[-width:, :].reshape(-1)
    left = gray[:, :width].reshape(-1)
    right = gray[:, -width:].reshape(-1)
    return np.concatenate([top, bottom, left, right])


def finite_float(value: float) -> float:
    return value if math.isfinite(value) else 0.0
