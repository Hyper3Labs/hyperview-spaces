from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class GroundedParent:
    text: str
    image_path: Path | None = None
    bbox: tuple[float, float, float, float] | None = None


@dataclass(frozen=True)
class GroundedRecord:
    image_path: Path
    caption: str
    parents: tuple[GroundedParent, ...]

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> "GroundedRecord":
        parents_payload = payload.get("parents")
        if parents_payload is None:
            parents_payload = [
                {
                    "text": payload.get("box_text", ""),
                    "image_path": payload.get("box_image_path"),
                    "bbox": payload.get("bbox"),
                }
            ]

        parents: list[GroundedParent] = []
        for parent_payload in parents_payload:
            text = str(parent_payload.get("text") or parent_payload.get("box_text") or "").strip()
            image_path = parent_payload.get("image_path") or parent_payload.get("box_image_path")
            bbox_payload = parent_payload.get("bbox")
            bbox = None
            if bbox_payload is not None:
                if len(bbox_payload) != 4:
                    raise ValueError(f"Expected four bbox values, got {bbox_payload!r}")
                bbox = tuple(float(value) for value in bbox_payload)
            parents.append(GroundedParent(text=text, image_path=Path(image_path) if image_path else None, bbox=bbox))

        if not parents:
            raise ValueError("Grounded records must include at least one parent")

        return cls(image_path=Path(payload["image_path"]), caption=str(payload["caption"]), parents=tuple(parents))