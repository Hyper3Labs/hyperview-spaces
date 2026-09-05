# Anatomy of a demo folder

A folder under `demos/<slug>/` is the single canonical source for one use case.
It is deployed as a Live Space and exported as a Static Space without forking.

## Required files

`check_spaces.py` fails the run if any of these is missing:

| File | Purpose |
| --- | --- |
| `README.md` | Hugging Face Space page. Frontmatter must contain `sdk: docker`. |
| `Dockerfile` | Live Space build. Must pin `hyperview` explicitly. |
| `demo.py` | Builds the dataset, computes embeddings and layouts, composes the UI, launches. Container `CMD`. |

## Optional files, by convention

| File | Purpose |
| --- | --- |
| `.dockerignore` | Keeps `__pycache__`, local caches, and stray artifacts out of the image. |
| `.hyperview/extensions/<name>/` | A demo-local extension: `extension.toml` + `panel.jsx`. Discovered from the nearest `.hyperview/extensions` directory. |
| `demo_data/` | Prepared datasets and media the container serves (`HYPERVIEW_DATASETS_DIR`, `HYPERVIEW_MEDIA_DIR`). When exporting a Static Space from a build-then-export run, prefer one fresh `HYPERVIEW_HOME` so the workspace registry is not shared with earlier runs. |
| `demo_assets/` | Static assets referenced by panels. |
| `evidence_cases.json` | Prepared query/result cases the demo replays. |
| `PHOTO_EVIDENCE.md` | The claim the demo makes, with the numbers behind it. |
| `live_demo.py` | A live variant of `demo.py` for a runtime-backed Space that accepts typed queries. |
| `vendor/*.whl` | Temporary escape hatch for unreleased HyperView features. Remove once the version is on PyPI. |

## The constants block

Everything a copier needs to change lives at the top of `demo.py`, above any
function definition. From `demos/inat24-tiny-clip-hycoclip/demo.py`:

```python
SPACE_HOST = "0.0.0.0"
SPACE_PORT = 7860

DATASET_NAME = "inat24_tiny_geometry_showcase"
HF_DATASET = "evendrow/inat24_tiny"
HF_SPLIT = "train"
SAMPLE_SEED = 42

TARGET_SUPERCATEGORY_COUNTS = {"plants": 50, "insects": 50, ...}
SAMPLE_COUNT = sum(TARGET_SUPERCATEGORY_COUNTS.values())
IMAGE_MAX_SIZE = (768, 768)

EMBEDDING_LAYOUTS = [
    {
        "name": "CLIP",
        "provider": "embed-anything",
        "model": "openai/clip-vit-base-patch32",
        "layouts": ["euclidean:3d", "spherical"],
    },
    {
        "name": "HyCoCLIP",
        "provider": "hyper-models",
        "model": "hycoclip-vit-s",
        "layouts": ["poincare"],
    },
]
```

Keep Docker args, runtime environment variables, and script constants in sync
from this one place so an agent editing a copy does not have to coordinate three
files.

One constant belongs in every demo, not just a copied one:

```python
# Build the workspace and exit instead of serving it. This is how a Static
# Space is produced: build, exit, export.
BUILD_ONLY = os.environ.get("HYPERVIEW_BUILD_ONLY", "").lower() in {
    "1",
    "true",
    "yes",
} or "--build-only" in sys.argv[1:]
```

`main()` then launches with `block=False`, returns early when `BUILD_ONLY` is
set, and calls `session.wait()` otherwise. The container gets the serving
behaviour it has always had; an export or a build check gets a process that
finishes.

## Composing the workspace

A demo describes the workspace it wants and hands the description to HyperView.
The API for that is small, and each call replaces something a demo used to do by
reaching into the running runtime.

```python
session = hv.launch(
    dataset,
    workspace_id=WORKSPACE_ID,
    block=False,
    extensions=[EXTENSION_DIR],      # registered before any view names its panel
)

shortlist = session.create_collection(  # durable; a static export keeps it
    ordered_result_ids(case, "hyper3"),
    name="Denim leggings · Hyper3-CLIP · Top 6",
    workspace_id=WORKSPACE_ID,
)

layout_key = dataset.find_layout(       # described, not pinned
    model="hyper3-clip-v0.5",
    provider="hyper-models",
    modality="multimodal",
    geometry="poincare",
    dimension=2,
)
if layout_key is None:
    raise RuntimeError("This workspace has no 2D Poincare Hyper3 layout.")

session.ui.apply_view(
    hv.ui.View(
        hv.ui.Samples(
            id="samples",
            mode="results",             # typed keywords for the documented props
            collection_id=shortlist,
            label_field="title",
        ),
        hv.ui.Scatter(id="map", layout_key=layout_key, geometry="poincare"),
        hv.ui.ExtensionPanel(
            id="readout",
            extension="fashion-search-readout",
            panel="fashion-comparison",
            props={"cases": cases},     # raw props stay open for custom ones
            state={"activeCaseId": "denim"},  # opening state, no patch after
        ),
    ),
    workspace_id=WORKSPACE_ID,
)
```

Four things to carry away:

- **A layout key is a content hash.** It is only knowable after the layout is
  computed, so a constant in `demo.py` goes stale on the next rebuild.
  `find_layout` returns `None` when nothing matches and raises with the
  candidates listed when more than one does. One model often has both an
  image-only and a multimodal embedding space in the same dataset, and
  `modality=` is the only criterion that tells their layouts apart.
- **`create_collection` is how a result list survives.** Building one by calling
  `show_samples` and reading the reply's `collection_id` leaves a transient
  collection that a static export drops, so the exported Space opens on the
  whole dataset instead of the six products the demo chose.
- **`state=` replaces `patch_panel_state(..., replace_state=True)`.** The panel
  opens in the right place instead of flickering through a default first.
- **`extensions=[...]` on `launch` replaces `add_extension` between `launch` and
  `apply_view`.** `apply_view` validates every panel type, so an extension that
  is not registered yet fails loudly rather than opening an empty workspace.

Typed keywords (`mode`, `collection_id`, `anchor_sample_id`, `label_field`,
`show_text_search`, `rank`, `preset`) cover the documented props; `props={...}`
stays open for anything a custom panel understands.

## Import rule

```python
import hyperview as hv          # correct

from hyperview.runtime import X # hard error in check_spaces.py
```

`validate_public_python_api` walks the AST of every `*.py` in the folder and
errors on any `ImportFrom` whose module starts with `hyperview.`. Demo folders
double as the public-API contract test: if a demo needs a private module, the
API is missing something and HyperView should export it.

## Dockerfile shape

```dockerfile
FROM python:3.11-slim
# build deps, non-root user 1000, HOME=/home/user, WORKDIR $HOME/app

ARG HYPERVIEW_VERSION=1.0.0
ARG HYPER_MODELS_VERSION=0.3.1

# CPU-only torch first, or pip pulls the full CUDA bundle into a CPU Space
RUN pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
RUN pip install "hyperview==${HYPERVIEW_VERSION}" \
    && python -c "import hyperview as hv; print('hyperview', hv.__version__)"
RUN pip install "hyper-models[ml]==${HYPER_MODELS_VERSION}" "datasets>=4.5.0" "Pillow>=12.0.0"

COPY --chown=user . .

ENV HYPERVIEW_HOST=0.0.0.0 \
    HYPERVIEW_PORT=7860 \
    HYPERVIEW_WORKSPACE_ID=<workspace-id> \
    HYPERVIEW_DATASETS_DIR=/home/user/app/demo_data/datasets \
    HYPERVIEW_MEDIA_DIR=/home/user/app/demo_data/media

EXPOSE 7860
HEALTHCHECK --interval=30s --timeout=10s --start-period=2700s --retries=3 \
    CMD curl -f http://localhost:7860/__hyperview__/health || exit 1
CMD ["python", "demo.py"]
```

Notes:

- The long `--start-period` is deliberate. A CPU Space that builds its dataset
  and downloads model weights on first boot needs tens of minutes before the
  health endpoint answers; a short grace period restarts the container in a
  loop and it never finishes.
- `ARG HYPERVIEW_VERSION` / `ARG HYPER_MODELS_VERSION` are the pin form
  `check_spaces.py` reads first. A direct `pip install hyperview==1.1.1` also
  works; an unpinned `pip install hyperview` is an error.
- The build-time `import hyperview` print is an install smoke test: it fails the
  image build rather than the container start if the wheel is broken.

## Panel extensions

A demo-local panel lives at `.hyperview/extensions/<name>/panel.jsx` and must
target Panel SDK v2:

```jsx
if (sdk.version !== "2") { /* refuse to render */ }
const { useHostState, useSampleQuery, ... } = hooks;
```

`validate_panel_sdk` errors if the file does not contain the literal
`sdk.version !== "2"` guard, if it uses a legacy SDK API, or if it destructures
a hook that SDK v2 does not export. Authoring guidance for the panel itself is
in the `hyperview-cli` skill's `references/panel-modules.md`.

The SDK also ships the chrome the built-in panels are made of, so a panel does
not have to hand-roll its own shell:

```jsx
const { React, components, hooks } = sdk;
const { Panel } = components;   // also PanelHeader, PanelToolbar,
                                // PanelToolbarButton, PanelToolbarIconButton

return (
  <Panel>
    <div className="fs-root">…</div>
  </Panel>
);
```

`Panel` is the full-height flex column with hidden overflow that a demo panel
otherwise writes out in inline CSS. Its scrolling body should take the remaining
space - `flex: 1; min-height: 0` - rather than asking for `height: 100%` inside
a flex parent. Reach for `PanelHeader` and the toolbar components when a panel
wants the workspace's own chrome; a panel with an editorial header of its own
design should keep it.

## Static vs live variants

Some demos ship both `demo.py` (prepared evidence, works in a static export) and
`live_demo.py` (accepts typed queries against a running runtime). The live
variant imports its constants and helpers from `demo.py` so the two cannot
drift:

```python
from demo import DATASET_NAME, SPACE_HOST, load_evidence, repair_media_paths, validate_dataset
```

Only `demo.py` is the container `CMD`. Point the Dockerfile at `live_demo.py`
only for a Space that is meant to serve live queries, and only when the runtime
can afford to load the text tower.
