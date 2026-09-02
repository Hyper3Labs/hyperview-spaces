# Static Spaces

A **Static Space** is a portable, read-only HyperView workspace. It preserves the
full HyperView shell, prepared data, media, layouts, selections, and custom
panels, but it does not offer actions that require a Python runtime.

The canonical demo source lives in `../demos/`. Do not maintain a second copy of
the demo here. Generate each ignored bundle from its source workspace:

```bash
uv run hyperview export <workspace-id> \
  --out hyperview-spaces/static-spaces/<slug>
```

`../static-spaces.registry.json` maps every reviewed Static Space to its canonical
source, workspace ID, public mount path, and optional Live Space.

Use a **Live Space** when someone needs to load new data, run a new query,
execute a model/provider, recompute an embedding or layout, or mutate shared
workspace state. Use a **Static Space** to publish and collaborate around prepared
evidence at ordinary static-hosting cost.
