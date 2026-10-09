# Static Spaces

A **Static Space** is a portable, read-only HyperView workspace. It preserves the
full HyperView shell, prepared data, media, layouts, selections, and custom
panels, but it does not offer actions that require a Python runtime.

The canonical demo source lives in `../demos/`. Each folder here is the
committed bundle exported from that source's workspace, and it is what
spaces.hyper3labs.com and the Live Spaces serve. Re-export with the current
HyperView release after any change, then commit:

```bash
hyperview export <workspace-id> --out static-spaces/<slug>
python scripts/check_static_spaces.py --require-bundles
```

Jaguar is the exception: its bundle lives in its Hugging Face Space repository.

`../static-spaces.registry.json` maps every reviewed Static Space to its canonical
source, workspace ID, public mount path, and optional Live Space.

Use a **Live Space** when someone needs to load new data, run a new query,
execute a model/provider, recompute an embedding or layout, or mutate shared
workspace state. Use a **Static Space** to publish and collaborate around prepared
evidence at ordinary static-hosting cost.
