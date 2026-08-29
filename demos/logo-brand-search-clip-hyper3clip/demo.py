#!/usr/bin/env python
"""Business-facing logo brand search workspace in HyperView.

Brand/creative operations lead questions:
1. For a prepared creative brief, which logos rank highest under Hyper3-CLIP vs
   CLIP, and where is the known target ranked?
2. How is the full 160-logo catalog organized for visual/style coverage and
   outliers?
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import hyperview as hv

SPACE_DIR = Path(__file__).resolve().parent
SPACE_HOST = os.environ.get("HYPERVIEW_HOST", "127.0.0.1")
SPACE_PORT = int(os.environ.get("HYPERVIEW_PORT", "6272"))
WORKSPACE_ID = os.environ.get(
    "HYPERVIEW_WORKSPACE_ID", "logo-brand-search-clip-hyper3clip-hf-live-v4"
)
DATASET_NAME = os.environ.get(
    "HYPERVIEW_DATASET_NAME", "logo_brand_search_clip_hyper3clip_hf_live_v4"
)
EXTENSION_DIR = SPACE_DIR / ".hyperview" / "extensions" / "logo-brand-readout"
CASE_FILE = SPACE_DIR / "cases.json"
BRIEF_FILE = SPACE_DIR / "case_briefs.json"
DEFAULT_CASE_ID = os.environ.get("LOGO_BRAND_DEFAULT_CASE_ID", "01-barber-franchise")
DEFAULT_MODEL = "hyper3"
EXPECTED_SAMPLE_COUNT = 160
# Hyper3 multimodal embedding space (image+text), not the older image-only layout.
HYPER3_LAYOUT_KEY = (
    "hyper-models__hyper3-clip-v0_5__42052c955756__"
    "poincare_umap__2d_1a6bcbc4"
)
SAMPLES_PANEL_ID = "samples"
TOPOLOGY_PANEL_ID = "logo-style-topology"
DECISION_PANEL_ID = "logo-brand-readout"


def load_evidence() -> tuple[dict[str, Any], dict[str, Any]]:
    return (
        json.loads(CASE_FILE.read_text(encoding="utf-8")),
        json.loads(BRIEF_FILE.read_text(encoding="utf-8")),
    )


def sample_id(index: int) -> str:
    return f"logo_{index:04d}"


def clean_caption(text: str) -> str:
    return re.sub(r"\s+", " ", str(text).strip().strip('"')).strip()


def result_title(text: str) -> str:
    caption = clean_caption(text)
    clauses = [part.strip() for part in caption.split(",") if part.strip()]
    first_clause = clauses[0] if clauses else caption
    first_clause = re.sub(r"^a logo of\s+", "", first_clause, flags=re.IGNORECASE)
    if " with " in first_clause:
        first_clause = first_clause.split(" with ", 1)[1]
    elif len(clauses) > 1:
        first_clause = clauses[1]
    return first_clause[:72].strip().capitalize() or "Logo asset"


def prepared_sample_ids(payload: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for case in payload["cases"]:
        ids.add(sample_id(int(case["target"]["hfIndex"])))
        for model_key in ("hyper3Results", "clipResults"):
            for result in case[model_key]:
                ids.add(sample_id(int(result["hfIndex"])))
        proof = case.get("clipTargetProof") or {}
        if "hfIndex" in proof:
            ids.add(sample_id(int(proof["hfIndex"])))
    return ids


def repair_media_paths(dataset: hv.Dataset) -> None:
    media_dir = Path(
        os.environ.get(
            "HYPERVIEW_MEDIA_DIR",
            str(SPACE_DIR / "demo_data" / "logo_images"),
        )
    )
    repaired: list[hv.Sample] = []
    for sample in dataset.samples:
        expected = media_dir / f"{sample.id}.jpg"
        if not expected.exists():
            raise RuntimeError(f"Logo media is missing: {expected}")
        if Path(str(sample.filepath)).expanduser() == expected:
            continue
        repaired.append(
            hv.Sample(
                id=sample.id,
                filepath=str(expected),
                label=sample.label,
                text=sample.text,
                metadata=dict(sample.metadata),
                modality=sample.modality,
            )
        )
    if repaired:
        dataset.add_samples(repaired, skip_existing=False)
        print(f"Repaired {len(repaired)} Logo Search media paths.", flush=True)


def validate_dataset(dataset: hv.Dataset, payload: dict[str, Any]) -> None:
    samples = dataset.samples
    if len(samples) != EXPECTED_SAMPLE_COUNT:
        raise RuntimeError(
            f"Logo workspace requires {EXPECTED_SAMPLE_COUNT} persisted samples; "
            f"found {len(samples)} in {dataset.name}."
        )

    sample_by_id = {sample.id: sample for sample in samples}
    missing_ids = sorted(prepared_sample_ids(payload) - set(sample_by_id))
    if missing_ids:
        raise RuntimeError(
            "Logo dataset is missing prepared evidence rows: " + ", ".join(missing_ids)
        )

    missing_media = [
        sample.id
        for sample in samples
        if sample.filepath and not Path(str(sample.filepath)).expanduser().exists()
    ]
    if missing_media:
        preview = ", ".join(missing_media[:5])
        raise RuntimeError(f"Logo dataset has missing local media: {preview}")

    layouts = {layout.layout_key: layout for layout in dataset.list_layouts()}
    layout = layouts.get(HYPER3_LAYOUT_KEY)
    if layout is None:
        raise RuntimeError(f"Required Hyper3 multimodal layout is missing: {HYPER3_LAYOUT_KEY}")
    if int(layout.count) != EXPECTED_SAMPLE_COUNT:
        raise RuntimeError(
            f"Hyper3 multimodal layout covers {layout.count} samples, "
            f"expected {EXPECTED_SAMPLE_COUNT}."
        )
    if getattr(layout, "geometry", None) != "poincare":
        raise RuntimeError(
            f"Expected Poincare Hyper3 layout geometry; found {getattr(layout, 'geometry', None)}."
        )

    print(
        f"Validated full catalog dataset {dataset.name}: "
        f"{len(samples)} samples, Hyper3 multimodal layout present, "
        f"{len(prepared_sample_ids(payload))} prepared evidence IDs covered.",
        flush=True,
    )


def panel_cases(payload: dict[str, Any], briefs: dict[str, Any]) -> list[dict[str, Any]]:
    prepared: list[dict[str, Any]] = []
    for case in payload["cases"]:
        brief = briefs[case["id"]]
        target_index = int(case["target"]["hfIndex"])
        prepared.append(
            {
                "id": case["id"],
                "label": case["label"],
                "shortLabel": brief["shortLabel"],
                "business": case["business"],
                "query": clean_caption(case["query"]),
                "attributes": [
                    {"label": label, "value": value}
                    for label, value in brief["attributes"].items()
                ],
                "target": {
                    "sampleId": sample_id(target_index),
                    "hfIndex": target_index,
                    "title": result_title(case["target"]["text"]),
                    "hyper3Rank": int(case["targetRanks"]["hyper3_clip"]),
                    "clipRank": int(case["targetRanks"]["clip_b32"]),
                },
                "modelReadout": {
                    "hyper3": brief["hyper3Readout"],
                    "clip": brief["clipReadout"],
                },
                "results": {
                    model: [
                        {
                            "rank": int(result["rank"]),
                            "sampleId": sample_id(int(result["hfIndex"])),
                            "hfIndex": int(result["hfIndex"]),
                            "title": result_title(result["text"]),
                            "isTarget": bool(result.get("isTarget")),
                        }
                        for result in case[f"{model}Results"]
                    ]
                    for model in ("hyper3", "clip")
                },
            }
        )
    return prepared


def readout_props(payload: dict[str, Any], briefs: dict[str, Any]) -> dict[str, Any]:
    metrics = payload["metrics"]["text_to_logo"]
    return {
        "dataset": payload["dataset"],
        "split": payload["split"],
        "protocol": (
            "160 paired image-caption rows; each dataset caption ranks the same "
            "160 logo images, and only the paired row is an exact positive."
        ),
        "claim": (
            "Four curated wins illustrate retrieval behavior. The aggregate covers "
            "all 160 paired captions; this synthetic/curated probe is not a "
            "production DAM or trademark benchmark."
        ),
        "workspaceBoundary": (
            "The interactive catalog contains all 160 prepared logo assets with a "
            "Hyper3 multimodal style map. Prepared ranks are fixed evidence from the "
            "bounded probe and are not recomputed in static exports."
        ),
        "models": {"hyper3": "Hyper3-CLIP v0.5", "clip": "OpenAI CLIP ViT-B/32"},
        "aggregate": {
            "queryCount": 160,
            "candidateCount": 160,
            "hyper3Hit1": metrics["hyper3_hit1"],
            "clipHit1": metrics["clip_hit1"],
            "hyper3Hit1Count": round(float(metrics["hyper3_hit1"].rstrip("%")) * 1.6),
            "clipHit1Count": round(float(metrics["clip_hit1"].rstrip("%")) * 1.6),
            "hyper3Hit5": metrics["hyper3_hit5"],
            "clipHit5": metrics["clip_hit5"],
            "hyper3Hit5Count": round(float(metrics["hyper3_hit5"].rstrip("%")) * 1.6),
            "clipHit5Count": round(float(metrics["clip_hit5"].rstrip("%")) * 1.6),
            "mrrDelta": metrics["mrr_delta"],
        },
        "initialCaseId": DEFAULT_CASE_ID,
        "initialModelKey": DEFAULT_MODEL,
        "samplesPanelId": SAMPLES_PANEL_ID,
        "topologyPanelId": TOPOLOGY_PANEL_ID,
        "workspaceSampleCount": EXPECTED_SAMPLE_COUNT,
        "cases": panel_cases(payload, briefs),
    }


def build_demo_view(payload: dict[str, Any], briefs: dict[str, Any]) -> hv.ui.View:
    samples = hv.ui.Samples(
        id=SAMPLES_PANEL_ID,
        title="Top 5 of 160 logos",
        position="center",
        props={"mode": "results"},
        layout=hv.ui.PanelLayout(min_width=320, min_height=340),
    )
    topology = hv.ui.Scatter(
        id=TOPOLOGY_PANEL_ID,
        title="Logo style map · Hyper3 multimodal",
        layout_key=HYPER3_LAYOUT_KEY,
        geometry="poincare",
        layout_dimension=2,
        position="center",
        reference_panel_id=samples.id,
        direction="within",
        layout=hv.ui.PanelLayout(min_height=300, min_width=320),
    )
    decision = hv.ui.ExtensionPanel(
        id=DECISION_PANEL_ID,
        title="Creative brief desk",
        extension="logo-brand-readout",
        panel="logo-brand-comparison",
        position="right",
        layout=hv.ui.PanelLayout(width=380, min_width=360, max_width=410),
        props=readout_props(payload, briefs),
    )
    return hv.ui.View(
        hv.ui.Tabs(samples, topology, active_tab=samples.id),
        decision,
        active_panel=decision.id,
    )


def ordered_result_ids(case: dict[str, Any], model: str) -> list[str]:
    return [
        str(result["sampleId"])
        for result in sorted(case["results"][model], key=lambda result: int(result["rank"]))
    ]


def default_case_payload(payload: dict[str, Any], briefs: dict[str, Any]) -> dict[str, Any]:
    cases = panel_cases(payload, briefs)
    return next(case for case in cases if case["id"] == DEFAULT_CASE_ID)


def launch_demo(
    dataset: hv.Dataset, payload: dict[str, Any], briefs: dict[str, Any]
) -> hv.Session:
    session = hv.launch(
        dataset,
        host=SPACE_HOST,
        port=SPACE_PORT,
        open_browser=False,
        workspace_id=WORKSPACE_ID,
        block=False,
    )
    print("Installing Logo Search creative-brief extension...", flush=True)
    session.ui.add_extension(EXTENSION_DIR, workspace_id=WORKSPACE_ID)
    session.ui.apply_view(build_demo_view(payload, briefs), workspace_id=WORKSPACE_ID)
    session.ui.patch_panel_state(
        DECISION_PANEL_ID,
        {"activeCaseId": DEFAULT_CASE_ID, "activeModelKey": DEFAULT_MODEL},
        workspace_id=WORKSPACE_ID,
        replace_state=True,
    )
    default_case = default_case_payload(payload, briefs)
    session.ui.show_samples(
        ordered_result_ids(default_case, DEFAULT_MODEL),
        workspace_id=WORKSPACE_ID,
        focus=False,
        source=f"Hyper3-CLIP · {default_case['label']} · Top 5 of {EXPECTED_SAMPLE_COUNT} logos",
    )
    default_target_is_visible = any(
        bool(result.get("isTarget"))
        for result in default_case["results"][DEFAULT_MODEL]
    )
    session.ui.set_selection(
        [default_case["target"]["sampleId"]] if default_target_is_visible else [],
        workspace_id=WORKSPACE_ID,
    )
    session.ui.set_active_layout(HYPER3_LAYOUT_KEY, workspace_id=WORKSPACE_ID)
    print(f"\nHyperView Logo Search demo is running at {session.url}", flush=True)
    print(
        "   Creative briefs drive native Samples; the Hyper3 map shows full catalog coverage.",
        flush=True,
    )
    return session


def main() -> None:
    payload, briefs = load_evidence()
    dataset = hv.Dataset(DATASET_NAME)
    repair_media_paths(dataset)
    validate_dataset(dataset, payload)
    session = launch_demo(dataset, payload, briefs)
    session.wait()


if __name__ == "__main__":
    main()
