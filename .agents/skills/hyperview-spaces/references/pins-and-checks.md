# Version pins and what `check_spaces.py` enforces

```bash
uv run --project ../ python scripts/check_spaces.py
```

Errors print as `ERROR: ...` and fail the run. Warnings print and pass. `INFO:`
lines report what was detected, including the pin spread per package.

## How a hyperview pin is detected

`hyperview_source()` looks, in order:

1. `vendor/*.whl` referenced in the Dockerfile - reported as
   `vendored wheel (<names>)`, accepted. Temporary escape hatch only.
2. `ARG HYPERVIEW_VERSION=<v>` - reported as `PyPI pin <v> (HYPERVIEW_VERSION)`.
3. `ARG HYPERVIEW_PACKAGE=...` containing `hyperview==<v>` - accepted; without a
   `==` it is `unversioned PyPI package` and **fails**.
4. A direct `hyperview==<v>` anywhere in the Dockerfile.
5. A bare `hyperview` mention - `unversioned PyPI package`, **fails**.
6. Nothing - `no hyperview installation found`, **fails**.

`hyper-models` is read from `ARG HYPER_MODELS_VERSION=<v>`, else from a direct
`hyper-models[...]==<v>`.

Prefer the `ARG` form. It puts the pin in one obvious place and lets a build
override it without editing the file.

## Pin rules

**1. Explicit pins only.** A PyPI-installed `hyperview` without `==` fails.

**2. Prose must match the build.** `validate_documented_pins` scans every `*.md`
in the demo folder for `<package>==<version>` and errors on any that disagrees
with that folder's Dockerfile pin:

```
ERROR: demos/foo/README.md:73: documents hyper-models==0.3.0 but the Dockerfile pins 0.3.1
```

Nothing else reads prose, so without this check a wrong version in a README
survives a green run and sends anyone reproducing the Space to the wrong
package.

**3. Demos must agree across the repo.** Every distinct pinned version of a
package is collected; more than one is an error. Two demos on different
`hyper-models` versions silently compute different vectors while both claim to
show the same embedding space. A healthy run prints:

```
INFO: hyper-models pins: 0.3.1
INFO: hyperview pins: 1.0.0
```

## Bumping a pin

1. Confirm the version is actually on PyPI. A pin to an unreleased version
   breaks every Space that rebuilds.
2. Update **every** demo's Dockerfile `ARG` in the same change - a partial bump
   trips the cross-demo agreement check.
3. Update any `*.md` in those folders that names the version, plus the root
   `README.md` and `demos/README.md` example lines.
4. Run `check_spaces.py`.
5. Push only when ready to deploy: touching a demo folder on `main` rebuilds
   that Space.

## Structural checks

| Check | Failure |
| --- | --- |
| Registry entry shape | invalid `folder` / `status` / `deploy_targets` / `space_id`; `keep_warm` with a null `space_id` |
| Registry vs disk | `space folder is missing from registry`, `registry folder does not exist` |
| Duplicates | duplicate registry `folder` |
| Workflow coverage | `hf-docker` target with no workflow whose `source_dir` matches, or more than one |
| Workflow agreement | `space_id mismatch: registry=... workflow=...`, unless recorded in `known_conflicts` |
| Stale exceptions | a `known_conflicts` entry that no longer matches anything |
| Required files | missing `README.md`, `Dockerfile`, or `demo.py` |
| Frontmatter | `README.md` frontmatter must contain `sdk: docker` |
| Root README table | every registry `folder` must appear as `` `demos/<slug>` `` inside the root README's `## Community Contributed Spaces` section |

## Python and panel checks

`validate_public_python_api` parses every `*.py` in the folder:

- A `SyntaxError` is reported with its line number.
- Any `from hyperview.<something> import ...` errors with
  `import HyperView APIs from the top-level public package (import hyperview as hv)`.

`validate_panel_sdk` reads every `.js` / `.jsx` under
`.hyperview/extensions/*/`:

- Must contain the literal guard `sdk.version !== "2"`.
- Must not use a legacy panel SDK token: `sdk.components`, `usePanelCommands`,
  `usePanelProps`, `usePanelRuntimeState`, `usePanelSamples`,
  `usePanelSelection`.
- Every hook destructured as `const { a, b } = hooks;` must be one SDK v2
  exports; an unknown hook name errors. The accepted set is `listTools`,
  `useActiveLayout`, `useCollection`, `useCommandClient`, `useDatasetInfo`,
  `useHostAdapter`, `usePanelActions`, `usePanelInteractions`, `usePanelState`,
  `useQuery`, `useSample`, `useSampleResults`, `useSamples`, `useSelection`,
  `useSimilarSamples`, `useSupportsLassoSelection`, `useSupportsTextSearch`,
  `useSupportsTools`, `useTool`.

## Running everything

```bash
uv run --project ../ python scripts/check_spaces.py
uv run --project ../ python scripts/check_shared_views.py
```

`.github/workflows/check-spaces.yml` runs these on push and pull request. They
are cheap and read-only - run them after any edit to a demo folder, a registry,
or a workflow.
