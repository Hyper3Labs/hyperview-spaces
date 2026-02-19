# HyperView Spaces (single repo pattern)

This folder implements a **one-repository** strategy:

- The same repo acts as the **template source**
- One folder is deployed to one Hugging Face Space
- Additional Spaces can be added by creating another folder + workflow

## Structure

```text
spaces/
  README.md
  imagenette-clip-hycoclip/
    README.md
    Dockerfile
    .dockerignore
    demo.py
```

Each subfolder is a **Space root** (must contain at least `README.md` + `Dockerfile`).

## CI deployment model

- Reusable workflow: `.github/workflows/deploy-hf-space-reusable.yml`
- Per-space workflow(s): `.github/workflows/deploy-hf-space-*.yml`

Each per-space workflow:
1. Watches one space folder
2. Calls the reusable workflow with:
   - `space_id` (e.g. `hyper3labs/HyperView`)
  - `source_dir` (e.g. `spaces/imagenette-clip-hycoclip`)

## Required GitHub secrets

- `HF_USERNAME` — your Hugging Face username
- `HF_TOKEN` — Hugging Face write token for Spaces

## Add a new Space

1. Copy `spaces/imagenette-clip-hycoclip` to a new slug
2. Edit the new folder's `README.md` YAML frontmatter and `demo.py`
3. Copy `.github/workflows/deploy-hf-space-imagenette.yml` to a new workflow file
4. Update `space_id`, `paths`, and `source_dir` in the new workflow
