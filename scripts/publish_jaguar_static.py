"""Publish the verified Jaguar bundle without deleting original research files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from check_jaguar_static import SOURCE, verify
from huggingface_hub import HfApi

ROLLBACK_TAG = "pre-static-2026-09-12"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--parent-commit", required=True)
    parser.add_argument("--apply", action="store_true", help="Actually tag and upload")
    args = parser.parse_args()
    bundle = args.bundle.resolve()
    report = verify(bundle)
    snapshot = json.loads((SOURCE / "research-snapshot.json").read_text())
    repo_id = snapshot["space_id"]
    original_revision = snapshot["space_revision"]
    if (bundle / "README.md").read_bytes() != (SOURCE / "SPACE_README.md").read_bytes():
        raise SystemExit("Bundle Space card differs from the reviewed source")
    if json.loads((bundle / "research/artifact-verification.json").read_text()) != report:
        raise SystemExit("Re-run the artifact validator and write its report before publishing")
    api = HfApi()
    current = api.space_info(repo_id)
    if current.sha != args.parent_commit:
        raise SystemExit(
            f"Remote revision changed: expected {args.parent_commit}, got {current.sha}"
        )
    original_files = set(
        api.list_repo_files(repo_id, repo_type="space", revision=original_revision)
    )
    bundle_files = {
        path.relative_to(bundle).as_posix() for path in bundle.rglob("*") if path.is_file()
    }
    overlap = original_files & bundle_files
    if overlap != {"README.md"}:
        raise SystemExit(f"Unexpected overlap with original research files: {sorted(overlap)}")
    tags = api.list_repo_refs(repo_id, repo_type="space").tags
    tag = next((item for item in tags if item.name == ROLLBACK_TAG), None)
    # Annotated tags expose the tag-object SHA; resolve the actual commit.
    if tag is not None and api.space_info(repo_id, revision=ROLLBACK_TAG).sha != original_revision:
        raise SystemExit("Existing rollback tag does not point to the original revision")
    print(
        json.dumps(
            {
                "repo_id": repo_id,
                "parent_commit": current.sha,
                "rollback_tag": ROLLBACK_TAG,
                "files": len(bundle_files),
                "deletions": 0,
                "verification": report,
            },
            indent=2,
        ),
        flush=True,
    )
    if not args.apply:
        return
    if tag is None:
        api.create_tag(
            repo_id,
            repo_type="space",
            tag=ROLLBACK_TAG,
            revision=original_revision,
            tag_message="Original paper-facing Docker app before verified static migration",
        )
    commit = api.upload_folder(
        repo_id=repo_id,
        repo_type="space",
        folder_path=bundle,
        parent_commit=args.parent_commit,
        commit_message="Migrate Jaguar to static hosting; preserve paper vectors, layouts and URL",
        # Deliberately omit delete_patterns: original scripts/assets remain in place.
    )
    print(json.dumps({"commit": commit.oid, "url": commit.commit_url}), flush=True)


if __name__ == "__main__":
    main()
