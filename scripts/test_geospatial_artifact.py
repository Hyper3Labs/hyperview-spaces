"""Verify the exported demo shows the model and retrieval evidence it names."""

import hashlib
import json
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "static-spaces/geospatial"
DEMO = ROOT / "demos/geospatial-eurosat-clip-hyper3clip"


def read(path):
    return json.loads(path.read_text())


def vector_digest(ids, vectors):
    digest = hashlib.sha256()
    for sample_id, vector in sorted(zip(ids, vectors)):
        digest.update(sample_id.encode() + b"\0")
        digest.update(np.asarray(vector, dtype="<f4").tobytes())
    return digest.hexdigest()


class GeospatialArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = read(DEMO / "evidence_cases.json")
        cls.dataset = read(BUNDLE / "api/dataset.json")
        cls.ui = read(BUNDLE / "api/runtime.json")["workspace"]["ui"]
        cls.panels = {p["id"]: p for p in cls.ui["custom_panels"]}
        cls.rows = {r["id"]: r for r in read(BUNDLE / "api/samples/shards/000000.json")["samples"]}

    def test_model_identity_and_pinned_vectors(self):
        self.assertEqual(
            {s["model_id"] for s in self.dataset["spaces"]},
            {"hyper3-clip-v1", "openai/clip-vit-base-patch32"},
        )
        candidate = next(s for s in self.dataset["spaces"] if s["model_id"] == "hyper3-clip-v1")
        self.assertEqual(
            candidate["config"]["model_revision"], self.evidence["provenance"]["hyper3"]["revision"]
        )
        self.assertEqual(
            candidate["config"]["checkpoint_sha256"],
            self.evidence["provenance"]["hyper3"]["checkpointSha256"],
        )
        self.assertNotIn("checkpoint", candidate["config"])
        for model in ("hyper3", "clip"):
            space = self.evidence["cases"][0]["models"][model]["spaceKey"]
            vectors = np.load(BUNDLE / "restore/spaces" / space / "vectors.npz", allow_pickle=False)
            self.assertEqual(
                vector_digest(vectors["ids"], vectors["vectors"]),
                self.evidence["provenance"][model]["vectorsSha256"],
            )
        manifest = read(BUNDLE / "hyperview-static.json")
        self.assertFalse(manifest["capabilities"]["text_search"])

    def test_exported_rankings_and_all_sixty_query_metrics(self):
        prepared = read(ROOT / "results/geospatial_v1_rankings.json")["rankings"]
        self.assertEqual(len(self.rows), 60)
        for sample_id, expected_hash in self.evidence["provenance"]["imageSha256"].items():
            self.assertEqual(
                hashlib.sha256(
                    (BUNDLE / "api/samples" / sample_id / "content").read_bytes()
                ).hexdigest(),
                expected_hash,
            )
        for model in ("hyper3", "clip"):
            space = self.evidence["cases"][0]["models"][model]["spaceKey"]
            neighbours = read(BUNDLE / "api/search/similar" / space / "shards/000000.json")
            self.assertEqual(neighbours["metric"], "hyperboloid" if model == "hyper3" else "cosine")
            total_exact = total_group = 0
            for anchor, result in neighbours["queries"].items():
                ids = [r["sample_id"] for r in result["results"]]
                self.assertEqual(ids, prepared[model][anchor]["resultIds"])
                self.assertEqual(len(ids), 10)
                self.assertNotIn(anchor, ids)
                exact = sum(self.rows[i]["label"] == self.rows[anchor]["label"] for i in ids)
                group = sum(
                    self.rows[i]["metadata"]["parent_group"]
                    == self.rows[anchor]["metadata"]["parent_group"]
                    for i in ids
                )
                self.assertEqual(exact, prepared[model][anchor]["exactHits"])
                self.assertEqual(group, prepared[model][anchor]["parentHits"])
                total_exact += exact
                total_group += group
            self.assertEqual(len(neighbours["queries"]), 60)
            self.assertAlmostEqual(total_exact / 600, self.evidence["aggregate"][model]["exactP10"])
            self.assertAlmostEqual(
                total_group / 600, self.evidence["aggregate"][model]["parentP10"]
            )

    def test_panel_evidence_matches_artifact_and_compact_default(self):
        readout = self.panels["geospatial-retrieval-readout"]
        self.assertTrue(readout["active"])
        self.assertEqual(readout["props"]["models"]["hyper3"], "Hyper3-CLIP V1")
        self.assertEqual(readout["props"]["aggregate"], self.evidence["aggregate"])
        for case in readout["props"]["cases"]:
            recorded = next(c for c in self.evidence["cases"] if c["id"] == case["id"])
            for model in ("hyper3", "clip"):
                shown = case["models"][model]
                self.assertEqual(shown["resultIds"], recorded["models"][model]["resultIds"])
                self.assertEqual(shown["offGroupHits"], 10 - shown["parentHits"])
                layout = next(
                    item
                    for item in self.dataset["layouts"]
                    if item["layout_key"] == shown["layoutKey"]
                )
                self.assertEqual(layout["space_key"], shown["spaceKey"])


if __name__ == "__main__":
    unittest.main()
