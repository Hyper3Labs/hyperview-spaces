# Fashion photo-matching evidence

This readout documents `deepfashion-same-product-persisted-spaces-2026-08-12`,
the photo-to-photo evidence shown by the Fashion Products Space.

- Dataset: the persisted 741-image DeepFashion catalog used by this workspace.
- Gallery: all 741 catalog photos.
- Queries: 710 photos whose DeepFashion product key has at least one other view.
- Positive: another photo with the same DeepFashion product key.
- Self-match: excluded.
- Metrics: first matching-product rank, recall at 1 and 10, and average precision.
- Case selection: the largest first-match rank gap in each direction, so the
  walkthrough includes both a Hyper3-CLIP win and an OpenAI CLIP win.

The canonical JSON projection `{photoBenchmark, photoCases}` has SHA-256
`958017f729f73990b392530b37cbdbe8812c923141573077dbdc0c3f65213c4b`.
`demo.py` recomputes and validates this hash before launching.

This 741-image catalog probe is separate from the 1,120-image typed-search
benchmark in the same Space. Their numbers are not interchangeable.
