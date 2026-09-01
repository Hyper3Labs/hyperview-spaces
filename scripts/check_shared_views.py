#!/usr/bin/env python3
"""Validate Shared View metadata and any locally generated bundles."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "shared-views.registry.json"
LIVE_REGISTRY_PATH = ROOT / "live-spaces.registry.json"


def read_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--require-bundles",
        action="store_true",
        help="Fail when an ignored local Shared View bundle has not been generated.",
    )
    args = parser.parse_args()

    errors: list[str] = []
    registry = read_object(REGISTRY_PATH)
    entries = registry.get("shared_views")
    if not isinstance(entries, list):
        print("ERROR: shared-views.registry.json must contain a shared_views list")
        return 1

    live_registry = read_object(LIVE_REGISTRY_PATH)
    live_by_id = {
        entry.get("space_id"): entry
        for entry in live_registry.get("spaces", [])
        if isinstance(entry, dict) and entry.get("space_id")
    }
    seen_slugs: set[str] = set()
    seen_sources: set[str] = set()

    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f"entry {index} is not an object")
            continue

        slug = entry.get("slug")
        source_folder = entry.get("source_folder")
        bundle_folder = entry.get("bundle_folder")
        workspace_id = entry.get("workspace_id")
        walkthrough_panel_id = entry.get("walkthrough_panel_id")
        mount_path = entry.get("mount_path")
        live_space_id = entry.get("live_space_id")

        if not isinstance(slug, str) or not slug:
            errors.append(f"entry {index} has an invalid slug")
            continue
        if slug in seen_slugs:
            errors.append(f"duplicate Shared View slug: {slug}")
        seen_slugs.add(slug)

        if (
            not isinstance(source_folder, str)
            or not source_folder.startswith("demos/")
            or not (ROOT / source_folder / "demo.py").is_file()
        ):
            errors.append(f"{slug}: invalid source_folder {source_folder!r}")
        elif source_folder in seen_sources:
            errors.append(f"{slug}: duplicate source_folder {source_folder!r}")
        else:
            seen_sources.add(source_folder)

        if bundle_folder != f"shared-views/{slug}":
            errors.append(
                f"{slug}: bundle_folder must be 'shared-views/{slug}', got {bundle_folder!r}"
            )
        if mount_path != f"/spaces/{slug}":
            errors.append(f"{slug}: mount_path must be '/spaces/{slug}', got {mount_path!r}")
        if not isinstance(workspace_id, str) or not workspace_id:
            errors.append(f"{slug}: workspace_id must be a non-empty string")
        if not isinstance(walkthrough_panel_id, str) or not walkthrough_panel_id:
            errors.append(f"{slug}: walkthrough_panel_id must be a non-empty string")
        if live_space_id is not None and live_space_id not in live_by_id:
            errors.append(
                f"{slug}: live_space_id {live_space_id!r} is absent from live-spaces.registry.json"
            )

        bundle = ROOT / str(bundle_folder)
        manifest_path = bundle / "hyperview-static.json"
        if not manifest_path.is_file():
            message = f"{slug}: local Shared View bundle has not been generated"
            if args.require_bundles:
                errors.append(message)
            else:
                print(f"INFO: {message}")
            continue

        manifest = read_object(manifest_path)
        capabilities = manifest.get("capabilities")
        if manifest.get("kind") != "hyperview-static-space":
            errors.append(f"{slug}: bundle is not a HyperView static export")
        if manifest.get("static") is not True:
            errors.append(f"{slug}: bundle does not declare static mode")
        if manifest.get("warnings") != []:
            errors.append(f"{slug}: bundle has export warnings: {manifest.get('warnings')!r}")
        if not isinstance(capabilities, dict) or capabilities.get("text_search") is not False:
            errors.append(f"{slug}: bundle exposes backend-only text search")
        # The registry field alone proves nothing: the exporter rebases asset
        # URLs against the mount path it was given, so a bundle built without
        # one serves /_next/... and 404s everything once published under
        # /spaces/<slug>/. Compare what the bundle was actually built for.
        bundle_mount_path = manifest.get("mount_path")
        if bundle_mount_path != mount_path:
            errors.append(
                f"{slug}: bundle was built for mount_path {bundle_mount_path!r}, "
                f"but the registry mounts it at {mount_path!r}; "
                f"re-export with --mount-path {mount_path}"
            )
        manifest_workspace = manifest.get("workspace")
        manifest_workspace_id = (
            manifest_workspace.get("id")
            if isinstance(manifest_workspace, dict)
            else manifest_workspace
        )
        if manifest_workspace_id != workspace_id:
            errors.append(
                f"{slug}: manifest workspace {manifest_workspace_id!r} "
                f"does not match {workspace_id!r}"
            )

        runtime_path = bundle / "api" / "runtime.json"
        if runtime_path.is_file() and isinstance(walkthrough_panel_id, str):
            runtime = read_object(runtime_path)
            workspace = runtime.get("workspace")
            ui = workspace.get("ui") if isinstance(workspace, dict) else None
            panels = ui.get("custom_panels") if isinstance(ui, dict) else None
            walkthrough = next(
                (
                    panel
                    for panel in panels or []
                    if isinstance(panel, dict) and panel.get("id") == walkthrough_panel_id
                ),
                None,
            )
            if walkthrough is None:
                errors.append(f"{slug}: walkthrough panel {walkthrough_panel_id!r} is absent")
            elif walkthrough.get("position") != "right":
                errors.append(
                    f"{slug}: walkthrough panel must be positioned right, "
                    f"got {walkthrough.get('position')!r}"
                )

    for message in errors:
        print(f"ERROR: {message}")
    if errors:
        print(f"FAILED: {len(errors)} error(s)")
        return 1
    print(f"PASS: {len(entries)} Shared View entries are valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
