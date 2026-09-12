"""Regression tests for static Space monitoring without container health probes."""

import argparse
import unittest
from unittest.mock import patch

import deploy_hf_space
import monitor_spaces


class StaticMonitoringTests(unittest.TestCase):
    def test_static_space_uses_manifest_and_no_runtime(self):
        entry = {
            "space_id": "org/paper",
            "deploy_mode": "static-bundle",
            "keep_warm": False,
            "expected_dataset": "paper-data",
        }
        args = argparse.Namespace(api_timeout=1, health_timeout=1, wake_wait_seconds=60)
        manifest = {
            "kind": "hyperview-static-space",
            "static": True,
            "hyperview_version": "1.1.1",
            "workspace": {"id": "paper", "dataset_name": "paper-data"},
        }
        with patch.object(
            monitor_spaces,
            "request_json",
            side_effect=[
                (
                    200,
                    {"sdk": "static", "sha": "commit", "host": "https://reported.static.hf.space"},
                    None,
                ),
                (200, manifest, None),
            ],
        ) as request:
            result = monitor_spaces.monitor_space(entry, args, None)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["huggingface"]["stage"], "STATIC")
        urls = [call.args[0] for call in request.call_args_list]
        self.assertEqual(
            urls,
            [
                "https://huggingface.co/api/spaces/org/paper",
                "https://reported.static.hf.space/hyperview-static.json",
            ],
        )

    def test_static_probe_rejects_wrong_or_missing_artifact(self):
        for payload in (
            {},
            {"static": False},
            {"static": True, "kind": "not-hyperview"},
            {"static": True, "kind": "hyperview-static-space", "workspace": "invalid"},
        ):
            with self.subTest(payload=payload):
                with patch.object(
                    monitor_spaces, "request_json", return_value=(200, payload, None)
                ):
                    result = monitor_spaces.probe_health(
                        "https://example.test", timeout=1, token=None, static=True
                    )
                self.assertFalse(result["ok"])

    def test_fallback_hosts_distinguish_static_from_docker(self):
        self.assertEqual(monitor_spaces.hf_space_url("Org/Paper"), "https://org-paper.hf.space")
        self.assertEqual(
            monitor_spaces.hf_space_url("Org/Paper", static=True),
            "https://org-paper.static.hf.space",
        )

    def test_static_space_rejects_wrong_sdk_or_dataset(self):
        args = argparse.Namespace(api_timeout=1, health_timeout=1, wake_wait_seconds=0)
        entry = {
            "space_id": "org/paper",
            "deploy_mode": "static-bundle",
            "keep_warm": False,
            "expected_dataset": "paper-data",
        }
        for sdk, dataset, status in (
            ("docker", "paper-data", "unknown"),
            ("static", "wrong-data", "metadata_mismatch"),
        ):
            with self.subTest(sdk=sdk, dataset=dataset):
                manifest = {
                    "kind": "hyperview-static-space",
                    "static": True,
                    "workspace": {"dataset_name": dataset},
                }
                with patch.object(
                    monitor_spaces,
                    "request_json",
                    side_effect=[(200, {"sdk": sdk}, None), (200, manifest, None)],
                ):
                    result = monitor_spaces.monitor_space(entry, args, None)
                self.assertEqual(result["status"], status)


class DeploymentGuardTests(unittest.TestCase):
    def test_docker_publisher_rejects_static_and_archived_targets(self):
        for space_id, reason in (
            ("hyper3labs/jaguar-hyperview-multigeometry", "is static"),
            ("hyper3labs/HyperView-ABO-Catalog", "is archived"),
        ):
            with self.subTest(space_id=space_id):
                with patch.object(
                    deploy_hf_space,
                    "parse_args",
                    return_value=argparse.Namespace(space_id=space_id),
                ):
                    with patch.object(deploy_hf_space, "HfApi") as api:
                        with self.assertRaisesRegex(SystemExit, reason):
                            deploy_hf_space.main()
                        api.assert_not_called()


if __name__ == "__main__":
    unittest.main()
