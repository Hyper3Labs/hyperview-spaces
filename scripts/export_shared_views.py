#!/usr/bin/env python3
"""Export every registered Shared View bundle from the local HyperView runtime.

Reads shared-views.registry.json and runs `hyperview export <workspace_id>`
into shared-views/<slug> for each entry, then validates the results with
check_shared_views.py. Workspaces must already exist locally (run the demo's
demo.py first when a workspace or its panel content changed).

Usage:
  uv run --project ../ python scripts/export_shared_views.py [slug ...]

With no arguments every registered Shared View is exported; passing slugs
limits the run to those entries.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "shared-views.registry.json"
HYPERVIEW_ROOT = ROOT.parent


def main() -> int:
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    entries = registry.get("shared_views")
    if not isinstance(entries, list):
        print("ERROR: shared-views.registry.json must contain a shared_views list")
        return 1

    wanted = set(sys.argv[1:])
    unknown = wanted - {entry.get("slug") for entry in entries}
    if unknown:
        print(f"ERROR: unknown slugs: {', '.join(sorted(unknown))}")
        return 1

    exported = 0
    for entry in entries:
        slug = entry["slug"]
        if wanted and slug not in wanted:
            continue
        workspace_id = entry["workspace_id"]
        destination = ROOT / entry["bundle_folder"]
        command = [
            "uv",
            "run",
            "hyperview",
            "export",
            workspace_id,
            "--out",
            str(destination),
        ]
        # Without this the exporter emits root-relative asset URLs, so a bundle
        # published under /spaces/<slug>/ 404s its own JS, CSS and media. The
        # registry already records where each bundle is mounted; pass it.
        mount_path = entry.get("mount_path")
        if mount_path:
            command += ["--mount-path", str(mount_path)]
        similarity_k = entry.get("similarity_k")
        if similarity_k is not None:
            command += ["--similarity-k", str(similarity_k)]
        print(f"==> {slug}: exporting workspace {workspace_id} -> {destination}")
        result = subprocess.run(command, cwd=HYPERVIEW_ROOT)
        if result.returncode != 0:
            print(f"ERROR: export failed for {slug}")
            return result.returncode
        exported += 1

    print(f"Exported {exported} Shared View bundle(s); validating…")
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_shared_views.py"), "--require-bundles"],
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
