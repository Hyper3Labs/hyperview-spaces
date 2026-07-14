#!/usr/bin/env python3
"""Create and synchronize a Docker Space using the local Hugging Face token."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from huggingface_hub import HfApi


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--space-id", required=True, help="Hugging Face Space ID: owner/name")
    parser.add_argument("--source-dir", required=True, type=Path, help="Local Space folder")
    parser.add_argument(
        "--commit-message",
        default=None,
        help="Optional Hugging Face commit message",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_dir = args.source_dir.resolve()
    required = ("README.md", "Dockerfile", "demo.py")

    if not source_dir.is_dir():
        raise SystemExit(f"source directory does not exist: {source_dir}")
    missing = [name for name in required if not (source_dir / name).is_file()]
    if missing:
        raise SystemExit(f"source directory is missing: {', '.join(missing)}")
    if "/" not in args.space_id or args.space_id.startswith("/") or args.space_id.endswith("/"):
        raise SystemExit("--space-id must use the owner/name form")

    token = os.environ.get("HF_TOKEN")
    api = HfApi(token=token) if token else HfApi()
    api.create_repo(
        repo_id=args.space_id,
        repo_type="space",
        space_sdk="docker",
        exist_ok=True,
    )
    message = args.commit_message or f"Deploy {args.space_id} from {source_dir.name}"
    commit = api.upload_folder(
        repo_id=args.space_id,
        repo_type="space",
        folder_path=source_dir,
        commit_message=message,
        delete_patterns=["*"],
    )
    print(f"Deployed {args.space_id}: {commit.oid}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
