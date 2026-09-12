"""Capture the paper-facing Jaguar runtime without mutating it."""

from __future__ import annotations

import argparse
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

SPACE_ID = "hyper3labs/jaguar-hyperview-multigeometry"
REVISION = "214644d68ee4f10d7a5dbc768ed76af00febe62c"
BASE_URL = "https://hyper3labs-jaguar-hyperview-multigeometry.hf.space"
DATASET_REVISION = "28110bb140951f84f11f23073d76412b367f65e4"


def get_json(url: str) -> dict:
    with urlopen(url, timeout=60) as response:
        return json.load(response)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Refusing to overwrite an existing research snapshot")
    info = get_json(f"https://huggingface.co/api/spaces/{SPACE_ID}")
    if info["sha"] != REVISION or info["sdk"] != "docker":
        raise SystemExit("Published source changed; review before capturing")
    dataset = get_json(f"{BASE_URL}/api/dataset")
    layouts = []
    for entry in dataset["layouts"]:
        payload = get_json(
            f"{BASE_URL}/api/embeddings?{urlencode({'layout_key': entry['layout_key']})}"
        )
        assert payload["layout_key"] == entry["layout_key"]
        assert len(payload["ids"]) == dataset["num_samples"] == 1895
        layouts.append(payload)
    samples = []
    for offset in range(0, dataset["num_samples"], 500):
        page = get_json(f"{BASE_URL}/api/samples?offset={offset}&limit=500")
        for row in page["samples"]:
            row.pop("thumbnail", None)
            samples.append(row)
    assert len({row["id"] for row in samples}) == dataset["num_samples"]
    # Check one anchor per identity in every space, including validation records.
    anchors = {}
    for row in samples:
        anchors.setdefault(row["label"], row["id"])
    requests = [
        (space["space_key"], sample_id)
        for space in dataset["spaces"]
        for sample_id in anchors.values()
    ]

    def capture_neighbors(item: tuple[str, str]) -> dict:
        space_key, sample_id = item
        query = urlencode({"space_key": space_key, "k": 100})
        result = get_json(f"{BASE_URL}/api/search/similar/{sample_id}?{query}")
        return {
            "space_key": space_key,
            "sample_id": sample_id,
            "results": [
                {"id": row["id"], "distance": row["distance"]} for row in result["results"]
            ],
        }

    with ThreadPoolExecutor(max_workers=4) as pool:
        neighbors = list(pool.map(capture_neighbors, requests))
    assert get_json(f"https://huggingface.co/api/spaces/{SPACE_ID}")["sha"] == REVISION
    snapshot = {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "space_id": SPACE_ID,
        "space_revision": REVISION,
        "dataset_revision": DATASET_REVISION,
        "dataset": dataset,
        "layouts": layouts,
        "samples": samples,
        "neighbor_checks": neighbors,
        "neighbor_metric": "cosine",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(snapshot, separators=(",", ":"), ensure_ascii=False) + "\n").encode()
    args.output.write_bytes(payload)
    print(
        json.dumps(
            {
                "path": str(args.output),
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "samples": len(samples),
                "layouts": len(layouts),
                "neighbor_checks": len(neighbors),
            }
        )
    )


if __name__ == "__main__":
    main()
