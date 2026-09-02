#!/usr/bin/env python3
"""Deploy a Hugging Face Space with the local Hugging Face login.

The manual counterpart to `.github/workflows/deploy-hf-space-reusable.yml`, for
the personal-account Spaces that are deliberately kept out of deploy CI. It
offers the same two modes:

    folder       Create the Docker Space if needed and sync a demos/<slug>/
                 folder to its root; the Space builds that Dockerfile and
                 `demo.py` rebuilds the workspace at boot.
    live-bundle  Hand an exported HyperView bundle to `hyperview publish
                 --mode live`, which generates the Dockerfile that runs
                 `hyperview serve --from <bundle> --public` and uploads both.
                 The bundle is the same artifact the landing site serves as a
                 Static Space.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from huggingface_hub import HfApi
from huggingface_hub.utils import HfHubHTTPError


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--space-id", required=True, help="Hugging Face Space ID: owner/name")
    parser.add_argument(
        "--mode",
        choices=["folder", "live-bundle"],
        default="folder",
        help="folder syncs a demo folder; live-bundle publishes an exported bundle.",
    )
    parser.add_argument("--source-dir", type=Path, help="folder mode: local Space folder")
    parser.add_argument(
        "--bundle",
        type=Path,
        help="live-bundle mode: directory written by `hyperview export`",
    )
    parser.add_argument(
        "--extra-pip",
        action="append",
        default=None,
        metavar="PKG==VERSION",
        help="live-bundle mode: extra pinned requirement for the image. Repeatable.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="live-bundle mode: render the plan without uploading anything.",
    )
    parser.add_argument(
        "--commit-message",
        default=None,
        help="Optional Hugging Face commit message",
    )
    return parser.parse_args()


def deploy_folder(args: argparse.Namespace) -> int:
    source_dir = args.source_dir.resolve()
    required = ("README.md", "Dockerfile", "demo.py")

    if not source_dir.is_dir():
        raise SystemExit(f"source directory does not exist: {source_dir}")
    missing = [name for name in required if not (source_dir / name).is_file()]
    if missing:
        raise SystemExit(f"source directory is missing: {', '.join(missing)}")

    token = os.environ.get("HF_TOKEN")
    api = HfApi(token=token) if token else HfApi()
    try:
        api.repo_info(repo_id=args.space_id, repo_type="space")
    except HfHubHTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else None
        if status_code != 404:
            raise
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


def deploy_live_bundle(args: argparse.Namespace) -> int:
    """Shell out to `hyperview publish` rather than reimplementing it.

    Publishing a Live Space means rendering a Dockerfile and a Space README from
    the bundle manifest. HyperView owns those, and a second copy here would
    drift from the one CI deploys.
    """

    bundle = args.bundle.resolve()
    if not bundle.is_dir():
        raise SystemExit(f"bundle directory does not exist: {bundle}")
    if not (bundle / "hyperview-static.json").is_file():
        raise SystemExit(f"not a HyperView bundle (no hyperview-static.json): {bundle}")

    # Prefer the CLI that belongs to the interpreter running this script, so a
    # venv-run deploy does not silently publish through a different HyperView.
    candidate = Path(sys.executable).with_name("hyperview")
    executable = str(candidate) if candidate.is_file() else shutil.which("hyperview")
    if executable is None:
        raise SystemExit(
            "the hyperview CLI is not on PATH: install it with "
            "`pip install 'hyperview[publish]'` and rerun"
        )
    command = [
        executable,
        "publish",
        str(bundle),
        "--to",
        f"hf:{args.space_id}",
        "--mode",
        "live",
    ]
    for requirement in args.extra_pip or ():
        command += ["--extra-pip", requirement]
    command += [
        "--commit-message",
        args.commit_message or f"Publish {args.space_id} from the {bundle.name} bundle",
    ]

    # A dry run first: a bundle that cannot be read, or a pin pip could never
    # resolve, fails before anything reaches the Space.
    print(f"$ {' '.join(command)} --dry-run")
    subprocess.run([*command, "--dry-run"], check=True)
    if args.dry_run:
        return 0
    print(f"$ {' '.join(command)}")
    subprocess.run(command, check=True)
    return 0


def main() -> int:
    args = parse_args()
    if "/" not in args.space_id or args.space_id.startswith("/") or args.space_id.endswith("/"):
        raise SystemExit("--space-id must use the owner/name form")

    if args.mode == "folder":
        if args.source_dir is None:
            raise SystemExit("--mode folder needs --source-dir")
        if args.bundle is not None:
            raise SystemExit("--bundle applies to --mode live-bundle only")
        return deploy_folder(args)

    if args.bundle is None:
        raise SystemExit("--mode live-bundle needs --bundle")
    if args.source_dir is not None:
        raise SystemExit("--source-dir applies to --mode folder only")
    return deploy_live_bundle(args)


if __name__ == "__main__":
    raise SystemExit(main())
