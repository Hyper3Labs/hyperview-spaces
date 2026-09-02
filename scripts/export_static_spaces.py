#!/usr/bin/env python3
"""Export every registered Static Space bundle from the local HyperView runtime.

Reads static-spaces.registry.json and runs `hyperview export <workspace_id>`
into static-spaces/<slug> for each entry, then validates the results with
check_static_spaces.py. Workspaces must already exist locally (run the demo's
demo.py first when a workspace or its panel content changed).

Usage:
  uv run --project ../ python scripts/export_static_spaces.py [slug ...]

With no arguments every registered Static Space is exported; passing slugs
limits the run to those entries.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "static-spaces.registry.json"
HYPERVIEW_ROOT = ROOT.parent


def main() -> int:
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    entries = registry.get("static_spaces")
    if not isinstance(entries, list):
        print("ERROR: static-spaces.registry.json must contain a static_spaces list")
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
        similarity_k = entry.get("similarity_k")
        if similarity_k is not None:
            command += ["--similarity-k", str(similarity_k)]
        print(f"==> {slug}: exporting workspace {workspace_id} -> {destination}")
        result = subprocess.run(command, cwd=HYPERVIEW_ROOT)
        if result.returncode != 0:
            print(f"ERROR: export failed for {slug}")
            return result.returncode
        exported += 1

    print(f"Exported {exported} Static Space bundle(s); validating…")
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_static_spaces.py"), "--require-bundles"],
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
