#!/usr/bin/env python3
"""Validate that live-spaces.registry.json agrees with demos, workflows, and docs."""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "live-spaces.registry.json"
DEMOS_DIR = ROOT / "demos"
SCRIPTS_DIR = ROOT / "scripts"
WORKFLOWS_DIR = ROOT / ".github" / "workflows"
README_PATH = ROOT / "README.md"
VALID_STATUSES = {"live", "draft", "local"}
VALID_DEPLOY_TARGETS = {"hf-docker", "hf-static", "cf-static"}
LEGACY_PANEL_SDK_TOKENS = {
    "usePanelCommands": "usePanelCommands",
    "usePanelProps": "usePanelProps",
    "usePanelRuntimeState": "usePanelRuntimeState",
    "usePanelSamples": "usePanelSamples",
    "usePanelSelection": "usePanelSelection",
}


def error(message: str, errors: list[str]) -> None:
    errors.append(message)
    print(f"ERROR: {message}")


def warning(message: str) -> None:
    print(f"WARNING: {message}")


def panel_sdk_surface(errors: list[str]) -> dict[str, Any] | None:
    """The SDK contract, read from the installed HyperView rather than copied here.

    A hand-maintained hook list drifts the moment the shell adds a hook, and the
    drift only shows up as a demo panel this checker refuses for no reason.
    """

    try:
        import hyperview
    except ImportError:
        error(
            "HyperView is not importable, so the panel SDK surface cannot be read: "
            "install hyperview (or run this with the HyperView virtualenv)",
            errors,
        )
        return None
    reader = getattr(hyperview, "panel_sdk_surface", None)
    if reader is None:
        error(
            f"installed HyperView {getattr(hyperview, '__version__', '?')} is too old: "
            "it does not expose panel_sdk_surface(); upgrade hyperview",
            errors,
        )
        return None
    return reader()


def yaml_scalar(text: str) -> str:
    value = text.split("#", 1)[0].strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def workflow_values(path: Path) -> tuple[str, str] | None:
    text = path.read_text(encoding="utf-8")
    source_match = re.search(r"^\s+source_dir:\s*(.+?)\s*$", text, re.MULTILINE)
    space_match = re.search(r"^\s+space_id:\s*(.+?)\s*$", text, re.MULTILINE)
    if not source_match or not space_match:
        return None
    return yaml_scalar(source_match.group(1)), yaml_scalar(space_match.group(1))


def read_frontmatter(path: Path) -> str | None:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    try:
        end = next(index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---")
    except StopIteration:
        return None
    return "\n".join(lines[1:end])


def hyperview_source(folder: Path) -> tuple[str, bool]:
    dockerfile = (folder / "Dockerfile").read_text(encoding="utf-8")
    version_arg = re.search(
        r"^ARG\s+HYPERVIEW_VERSION\s*=\s*['\"]?([^\s'\"]+)", dockerfile, re.MULTILINE
    )
    if version_arg:
        return f"PyPI pin {version_arg.group(1)} (HYPERVIEW_VERSION)", True

    package_arg = re.search(
        r"^ARG\s+HYPERVIEW_PACKAGE\s*=\s*['\"]?([^\n'\"]+)", dockerfile, re.MULTILINE
    )
    if package_arg:
        package = package_arg.group(1).strip()
        version = re.search(r"\bhyperview(?:\[[^]]+\])?==([^\s]+)", package)
        if version:
            return f"PyPI pin {version.group(1)} (HYPERVIEW_PACKAGE)", True
        return f"unversioned PyPI package ({package})", False

    direct_pin = re.search(r"\bhyperview(?:\[[^]]+\])?==([A-Za-z0-9_.+-]+)", dockerfile)
    if direct_pin:
        return f"PyPI pin {direct_pin.group(1)}", True

    if re.search(r"\bhyperview(?:\[[^]]+\])?\b", dockerfile):
        return "unversioned PyPI package", False
    return "no hyperview installation found", False


def dockerfile_pins(folder: Path) -> dict[str, str]:
    """The package versions a demo's Docker build actually installs."""

    dockerfile = (folder / "Dockerfile").read_text(encoding="utf-8")
    pins: dict[str, str] = {}

    arg = re.search(
        r"^ARG\s+HYPER_MODELS_VERSION\s*=\s*['\"]?([^\s'\"]+)", dockerfile, re.MULTILINE
    )
    direct = re.search(r"\bhyper-models(?:\[[^]]+\])?==([A-Za-z0-9_.+-]+)", dockerfile)
    if arg:
        pins["hyper-models"] = arg.group(1)
    elif direct:
        pins["hyper-models"] = direct.group(1)

    source, valid = hyperview_source(folder)
    version = re.search(r"PyPI pin ([A-Za-z0-9_.+-]+)", source) if valid else None
    if version:
        pins["hyperview"] = version.group(1)
    return pins


def validate_documented_pins(folder: Path, pins: dict[str, str], errors: list[str]) -> None:
    """Prose that names a version must name the one the Dockerfile installs.

    A README claiming `hyper-models==0.3.0` while the build pins 0.3.1 sends
    anyone reproducing the Space to the wrong package, and nothing else here
    reads prose, so the drift survives a green run.
    """

    for doc in sorted(folder.glob("*.md")):
        text = doc.read_text(encoding="utf-8")
        for package, pinned in pins.items():
            pattern = rf"\b{re.escape(package)}(?:\[[^]]+\])?==([A-Za-z0-9_.+-]+)"
            for match in re.finditer(pattern, text):
                if match.group(1) != pinned:
                    line = text.count("\n", 0, match.start()) + 1
                    error(
                        f"{doc.relative_to(ROOT)}:{line}: documents {package}=={match.group(1)} "
                        f"but the Dockerfile pins {pinned}",
                        errors,
                    )


def validate_public_python_api(folder: Path, errors: list[str]) -> None:
    for path in sorted(folder.glob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            error(f"{path.relative_to(ROOT)}:{exc.lineno}: invalid Python: {exc.msg}", errors)
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("hyperview."):
                error(
                    f"{path.relative_to(ROOT)}:{node.lineno}: import HyperView APIs from the "
                    "top-level public package (`import hyperview as hv`)",
                    errors,
                )


def validate_panel_sdk(folder: Path, surface: dict[str, Any], errors: list[str]) -> None:
    sdk_version = str(surface["version"])
    sdk_hooks = set(surface["hooks"])
    extension_root = folder / ".hyperview" / "extensions"
    for path in sorted(extension_root.glob("*/*")):
        if path.suffix not in {".js", ".jsx"}:
            continue
        source = path.read_text(encoding="utf-8")
        relative = path.relative_to(ROOT)
        if f'sdk.version !== "{sdk_version}"' not in source:
            error(f"{relative}: panel must require HyperViewPanelSDK v{sdk_version}", errors)
        for token, label in LEGACY_PANEL_SDK_TOKENS.items():
            if token in source:
                error(f"{relative}: legacy panel SDK API is not supported: {label}", errors)
        for match in re.finditer(r"const\s*\{(?P<hooks>[^}]+)\}\s*=\s*hooks\s*;", source):
            hooks = {
                item.strip().split(":", 1)[0].strip()
                for item in match.group("hooks").split(",")
                if item.strip()
            }
            for hook in sorted(hooks - sdk_hooks):
                error(
                    f"{relative}: hook is not exported by HyperViewPanelSDK "
                    f"v{sdk_version}: {hook}",
                    errors,
                )


def main() -> int:
    errors: list[str] = []
    sdk_surface = panel_sdk_surface(errors)
    if sdk_surface is None:
        print(f"FAILED: {len(errors)} error(s)")
        return 1
    print(
        f"INFO: HyperViewPanelSDK v{sdk_surface['version']} exposes "
        f"{len(sdk_surface['hooks'])} hooks and "
        f"{len(sdk_surface.get('components', []))} components"
    )
    registry: dict[str, Any] = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    spaces = registry.get("spaces")
    if not isinstance(spaces, list):
        error("live-spaces.registry.json must contain a spaces list", errors)
        return 1

    registry_by_folder: dict[str, dict[str, Any]] = {}
    for index, space in enumerate(spaces):
        if not isinstance(space, dict):
            error(f"registry entry {index} is not an object", errors)
            continue
        folder = space.get("folder")
        if not isinstance(folder, str) or not folder.startswith("demos/"):
            error(f"registry entry {index} has invalid folder: {folder!r}", errors)
            continue
        if folder in registry_by_folder:
            error(f"duplicate registry folder: {folder}", errors)
        registry_by_folder[folder] = space

        status = space.get("status")
        if status not in VALID_STATUSES:
            error(
                f"{folder}: status must be one of {sorted(VALID_STATUSES)}, got {status!r}", errors
            )
        targets = space.get("deploy_targets")
        if not isinstance(targets, list) or any(
            target not in VALID_DEPLOY_TARGETS for target in targets
        ):
            error(
                f"{folder}: deploy_targets must be a list drawn from {sorted(VALID_DEPLOY_TARGETS)}",
                errors,
            )
        space_id = space.get("space_id")
        if space_id is not None and (not isinstance(space_id, str) or not space_id.strip()):
            error(f"{folder}: space_id must be a non-empty string or null", errors)
        if space.get("keep_warm") and space_id is None:
            error(f"{folder}: keep_warm cannot be true when space_id is null", errors)

    disk_folders = {
        path.relative_to(ROOT).as_posix()
        for path in DEMOS_DIR.iterdir()
        if path.is_dir() and not path.name.startswith(".")
    }
    registry_folders = set(registry_by_folder)
    for folder in sorted(disk_folders - registry_folders):
        error(f"space folder is missing from registry: {folder}", errors)
    for folder in sorted(registry_folders - disk_folders):
        error(f"registry folder does not exist: {folder}", errors)

    # package -> pinned version -> folders installing it
    pins_by_package: dict[str, dict[str, list[str]]] = {}

    workflows_by_source: dict[str, list[tuple[Path, str]]] = {}
    for workflow in sorted(WORKFLOWS_DIR.glob("deploy-hf-space-*.yml")):
        if workflow.name == "deploy-hf-space-reusable.yml":
            continue
        values = workflow_values(workflow)
        if values is None:
            continue
        source_dir, space_id = values
        workflows_by_source.setdefault(source_dir, []).append((workflow, space_id))

    known_conflicts: dict[tuple[str, str | None, str], dict[str, Any]] = {}
    for conflict in registry.get("known_conflicts", []):
        if not isinstance(conflict, dict) or conflict.get("type") != "space_id_mismatch":
            error(f"invalid known_conflicts entry: {conflict!r}", errors)
            continue
        key = (
            conflict.get("folder"),
            conflict.get("registry_space_id"),
            conflict.get("workflow_space_id"),
        )
        if key in known_conflicts:
            error(f"duplicate known conflict: {key}", errors)
        known_conflicts[key] = conflict

    used_conflicts: set[tuple[str, str | None, str]] = set()
    for folder, space in sorted(registry_by_folder.items()):
        targets = space.get("deploy_targets", [])
        if "hf-docker" not in targets:
            continue
        workflows = workflows_by_source.get(folder, [])
        if not workflows:
            error(
                f"{folder}: deploy_targets includes hf-docker but no workflow has source_dir {folder}",
                errors,
            )
            continue
        if len(workflows) > 1:
            names = ", ".join(path.name for path, _ in workflows)
            error(f"{folder}: multiple deploy workflows match source_dir ({names})", errors)
            continue
        workflow, workflow_space_id = workflows[0]
        registry_space_id = space.get("space_id")
        if workflow_space_id != registry_space_id:
            key = (folder, registry_space_id, workflow_space_id)
            if key in known_conflicts:
                used_conflicts.add(key)
                warning(
                    f"known space_id conflict for {folder}: registry={registry_space_id!r}; "
                    f"workflow {workflow.name}={workflow_space_id!r}. "
                    f"{known_conflicts[key].get('reason', '')}".rstrip()
                )
            else:
                error(
                    f"{folder}: space_id mismatch: registry={registry_space_id!r}; "
                    f"workflow {workflow.name}={workflow_space_id!r}",
                    errors,
                )

    for key in sorted(set(known_conflicts) - used_conflicts, key=str):
        error(f"stale known conflict no longer matches registry/workflow values: {key}", errors)

    for folder in sorted(disk_folders):
        path = ROOT / folder
        for required in ("README.md", "Dockerfile", "demo.py"):
            if not (path / required).is_file():
                error(f"{folder}: missing {required}", errors)
        readme = path / "README.md"
        if readme.is_file():
            frontmatter = read_frontmatter(readme)
            if frontmatter is None or not re.search(
                r"^sdk:\s*docker\s*$", frontmatter, re.MULTILINE
            ):
                error(f"{folder}: README.md frontmatter must contain sdk: docker", errors)
        dockerfile = path / "Dockerfile"
        if dockerfile.is_file():
            source, valid = hyperview_source(path)
            print(f"INFO: {folder}: hyperview source: {source}")
            if not valid:
                error(
                    f"{folder}: PyPI-installed hyperview must have an explicit version pin", errors
                )
            pins = dockerfile_pins(path)
            for package, pinned in pins.items():
                pins_by_package.setdefault(package, {}).setdefault(pinned, []).append(folder)
            validate_documented_pins(path, pins, errors)
        validate_public_python_api(path, errors)
        validate_panel_sdk(path, sdk_surface, errors)

    # The repo's own tooling is held to the contract it enforces on demos: a
    # script reaching into hyperview internals breaks on the next release just
    # as loudly as a demo would.
    validate_public_python_api(SCRIPTS_DIR, errors)

    # Spaces sharing a model catalog must share its version, or two demos claiming
    # the same embedding space quietly compute different vectors.
    for package, versions in sorted(pins_by_package.items()):
        print(f"INFO: {package} pins: {', '.join(sorted(versions))}")
        if len(versions) > 1:
            spread = "; ".join(
                f"{version}: {', '.join(folders)}" for version, folders in sorted(versions.items())
            )
            error(f"demos disagree on the {package} pin -- {spread}", errors)

    root_readme = README_PATH.read_text(encoding="utf-8")
    table_match = re.search(
        r"^## Community Contributed Spaces\s*$([\s\S]*?)(?=^##\s|\Z)",
        root_readme,
        re.MULTILINE,
    )
    if not table_match:
        error("root README is missing the Community Contributed Spaces section", errors)
    else:
        table = table_match.group(1)
        for folder in sorted(registry_folders):
            if f"`{folder}`" not in table:
                error(f"root README community table is missing registry folder: {folder}", errors)

    if errors:
        print(f"FAILED: {len(errors)} error(s), {len(used_conflicts)} allowed conflict warning(s)")
        return 1
    print(
        f"PASS: {len(registry_by_folder)} registry entries match space folders, workflows, "
        f"Docker metadata, and README rows; {len(used_conflicts)} allowed conflict warning(s)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
