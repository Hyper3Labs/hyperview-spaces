#!/usr/bin/env python3
"""Monitor and lightly keep-warm registered HyperView Hugging Face Spaces."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "spaces.registry.json"
DEFAULT_OUTPUT = ROOT / "space-status.json"


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def hf_space_url(space_id: str) -> str:
    return f"https://{space_id.replace('/', '-').lower()}.hf.space"


def request_json(url: str, *, token: str | None, timeout: float) -> tuple[int | None, Any, str | None]:
    headers = {
        "Accept": "application/json",
        "User-Agent": "hyperview-space-monitor/0.1",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", "replace")
            if not raw:
                return response.status, None, None
            return response.status, json.loads(raw), None
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")[:1000]
        return exc.code, None, raw or str(exc)
    except Exception as exc:  # noqa: BLE001 - monitor should record failures, not crash.
        return None, None, str(exc)


def compact_card_data(space_info: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(space_info, dict):
        return None
    card = space_info.get("cardData") or space_info.get("card_data")
    if not isinstance(card, dict):
        return None
    keep = ("title", "sdk", "app_port", "models", "datasets", "tags", "pinned")
    return {key: card.get(key) for key in keep if key in card}


def probe_health(base_url: str, *, timeout: float, token: str | None) -> dict[str, Any]:
    started = time.perf_counter()
    status, payload, error = request_json(
        base_url.rstrip("/") + "/__hyperview__/health",
        token=token,
        timeout=timeout,
    )
    latency_ms = round((time.perf_counter() - started) * 1000)
    return {
        "ok": status == 200 and isinstance(payload, dict) and payload.get("name") == "hyperview",
        "http_status": status,
        "latency_ms": latency_ms,
        "payload": payload if isinstance(payload, dict) else None,
        "error": error,
    }


def summarize_status(
    *,
    runtime: dict[str, Any] | None,
    runtime_error: str | None,
    health: dict[str, Any] | None,
    expected_dataset: str | None,
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    stage = runtime.get("stage") if isinstance(runtime, dict) else None

    if runtime_error:
        reasons.append(f"runtime_error: {runtime_error[:180]}")
        return "unknown", reasons

    if stage == "PAUSED":
        reasons.append("space is paused")
        return "paused", reasons

    if health and health.get("ok"):
        payload = health.get("payload") or {}
        if expected_dataset and payload.get("dataset") != expected_dataset:
            reasons.append(
                f"dataset mismatch: expected {expected_dataset}, got {payload.get('dataset')}"
            )
            return "metadata_mismatch", reasons
        return "ok", reasons

    if stage == "SLEEPING":
        reasons.append("space is sleeping or still waking")
        return "warming", reasons

    if health:
        reasons.append(str(health.get("error") or f"health status {health.get('http_status')}"))
    return "unhealthy", reasons


def monitor_space(entry: dict[str, Any], args: argparse.Namespace, token: str | None) -> dict[str, Any]:
    space_id = entry["space_id"]
    base_url = entry.get("url") or hf_space_url(space_id)

    info_status, info, info_error = request_json(
        f"https://huggingface.co/api/spaces/{space_id}",
        token=token,
        timeout=args.api_timeout,
    )
    runtime_status, runtime, runtime_error = request_json(
        f"https://huggingface.co/api/spaces/{space_id}/runtime",
        token=token,
        timeout=args.api_timeout,
    )

    health: dict[str, Any] | None = None
    if entry.get("keep_warm", True):
        health = probe_health(base_url, timeout=args.health_timeout, token=None)
        if (
            not health.get("ok")
            and args.wake_wait_seconds > 0
            and isinstance(runtime, dict)
            and runtime.get("stage") == "SLEEPING"
        ):
            time.sleep(args.wake_wait_seconds)
            health = probe_health(base_url, timeout=args.health_timeout, token=None)

    status, reasons = summarize_status(
        runtime=runtime if isinstance(runtime, dict) else None,
        runtime_error=runtime_error,
        health=health,
        expected_dataset=entry.get("expected_dataset"),
    )

    health_payload = health.get("payload") if health else None
    return {
        "space_id": space_id,
        "url": base_url,
        "folder": entry.get("folder"),
        "demo_slug": entry.get("demo_slug"),
        "demo_name": entry.get("demo_name"),
        "status": status,
        "reasons": reasons,
        "checked_at": utc_now(),
        "last_ok": utc_now() if status == "ok" else None,
        "latency_ms": health.get("latency_ms") if health else None,
        "huggingface": {
            "info_status": info_status,
            "runtime_status": runtime_status,
            "repo_sha": info.get("sha") if isinstance(info, dict) else None,
            "last_modified": info.get("lastModified") if isinstance(info, dict) else None,
            "card": compact_card_data(info if isinstance(info, dict) else None),
            "stage": runtime.get("stage") if isinstance(runtime, dict) else None,
            "hardware": runtime.get("hardware") if isinstance(runtime, dict) else None,
            "requested_hardware": (
                runtime.get("requested_hardware") if isinstance(runtime, dict) else None
            ),
            "sleep_time": runtime.get("sleep_time") if isinstance(runtime, dict) else None,
            "info_error": info_error,
            "runtime_error": runtime_error,
        },
        "health": health,
        "hyperview": {
            "version": health_payload.get("version") if isinstance(health_payload, dict) else None,
            "workspace_id": (
                health_payload.get("workspace_id") if isinstance(health_payload, dict) else None
            ),
            "dataset": health_payload.get("dataset") if isinstance(health_payload, dict) else None,
            "session_id": (
                health_payload.get("session_id") if isinstance(health_payload, dict) else None
            ),
        },
    }


def print_summary(results: list[dict[str, Any]]) -> None:
    print("| Space | Status | Stage | Health | Latency | HyperView |")
    print("| --- | --- | --- | --- | ---: | --- |")
    for item in results:
        hf = item["huggingface"]
        health = item.get("health") or {}
        hv = item["hyperview"]
        health_status = "ok" if health.get("ok") else health.get("http_status") or "n/a"
        latency = item.get("latency_ms")
        print(
            "| {space} | {status} | {stage} | {health} | {latency} | {version} |".format(
                space=item["space_id"],
                status=item["status"],
                stage=hf.get("stage") or "unknown",
                health=health_status,
                latency=latency if latency is not None else "",
                version=hv.get("version") or "",
            )
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--api-timeout", type=float, default=10.0)
    parser.add_argument("--health-timeout", type=float, default=10.0)
    parser.add_argument("--wake-wait-seconds", type=float, default=60.0)
    parser.add_argument(
        "--fail-on-unhealthy",
        action="store_true",
        help="Exit nonzero unless every registered Space wakes and passes health checks.",
    )
    args = parser.parse_args()

    registry = json.loads(args.registry.read_text())
    token = os.environ.get("HF_TOKEN")
    checked_at = utc_now()
    results = [monitor_space(entry, args, token) for entry in registry.get("spaces", [])]
    payload = {
        "checked_at": checked_at,
        "registry": str(args.registry),
        "results": results,
    }
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    print_summary(results)
    bad_statuses = {"paused", "warming", "unhealthy", "metadata_mismatch", "unknown"}
    if args.fail_on_unhealthy and any(item["status"] in bad_statuses for item in results):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
