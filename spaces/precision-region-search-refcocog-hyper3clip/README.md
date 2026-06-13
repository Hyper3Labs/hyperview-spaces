---
title: HyperView Precision Region Search
emoji: 🎯
colorFrom: blue
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# HyperView Precision Region Search

This Space shows how Hyper3-CLIP handles exact crop retrieval on RefCOCOg-style scenes where the question is not "which image is similar?" but "which crop from this source image is the described part?"

The demo uses three operational slices:

- Workspace / Facilities: find a specific couch or fixture in inspection imagery.
- Retail / Tabletop: find a precise product or tabletop item in busy scenes.
- Fleet / Vehicles: transfer the same workflow to vehicle and mobile-asset imagery.

Each slice includes one source scene and eight real crops cut from that same image. The main workspace uses the latest HyperView v0.6.2 ranked Samples mode plus the local runtime-panel fixes needed for stable slice switching: one ranked crop panel is pinned to Hyper3-CLIP distance, the other to CLIP ViT-B/32 distance. Hyper3-CLIP ranks the target crop first; CLIP ranks a distractor higher. The two ranked Samples panels are initialized as the main comparison surface, while the bottom maps remain supporting geometry context and the custom panel only switches source scenes and explains the target phrase.

## Run Locally

From the HyperView repository root:

```bash
HYPERVIEW_PORT=6267 uv run python hyperview-spaces/spaces/precision-region-search-refcocog-hyper3clip/demo.py
```

Then open the URL printed by the launcher.
