"""Catch a healthy bundle runtime whose fresh Hyper3 queries fail without ML."""

import tempfile
import unittest
from pathlib import Path

from check_spaces import validate_live_bundle_model_deps


class LiveBundleDependencyTests(unittest.TestCase):
    def test_bundle_runtime_retains_source_encoder_dependencies(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / "Dockerfile").write_text(
                'ARG HYPER_MODELS_VERSION=0.4.0\n'
                'RUN pip install "hyper-models[ml]==${HYPER_MODELS_VERSION}"\n'
            )
            for requirements, expected_errors in [
                ("", 1),
                ("hyper-models==0.4.0", 1),
                ("hyper-models[ml]==0.3.2", 1),
                ("hyper-models[ml]==0.4.0", 0),
            ]:
                with self.subTest(requirements=requirements):
                    errors = []
                    validate_live_bundle_model_deps(
                        folder,
                        Path("deploy-test.yml"),
                        {"extra_pip": requirements},
                        errors,
                    )
                    self.assertEqual(len(errors), expected_errors)


if __name__ == "__main__":
    unittest.main()
