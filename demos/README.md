# HyperView demo sources

This folder implements a **one-repository** strategy:

- The same repo acts as the **template source**
- One folder is deployed to one Hugging Face Space
- Additional Spaces can be added by creating another folder + workflow

## Structure

```text
demos/
  README.md
  hello-world-inat24-clip-hyper3clip/
    README.md
    Dockerfile
    .dockerignore
    demo.py
```

Each subfolder is the canonical source for a use case and can be deployed as a
Live Space or exported as a Static Space. A deployable root contains at least
`README.md`, `Dockerfile`, and `demo.py`.

## Agent-friendly pattern

The example folders are meant to be easy for external coding agents to edit.
The intended workflow is:

1. Copy `demos/hello-world-inat24-clip-hyper3clip` to a new slug.
2. Edit the constants block at the top of the new `demo.py`.
3. Update the new folder's `README.md` frontmatter and title.
4. Copy and retarget the matching deploy workflow.

The official example installs released PyPI packages. Keep Space-specific code
inside the copied folder and update the pinned HyperView version after a PyPI
release instead of vendoring `hyperview` into the Space.

## Exact Steps

1. Create a new Hugging Face Space at https://huggingface.co/new-space.
2. Name it something distinct like `yourproject-HyperView` or `HyperView-yourproject`.
3. Choose `Docker` as the SDK.
4. Copy `demos/hello-world-inat24-clip-hyper3clip` to `demos/yourproject-hyperview`.
5. Edit the constants block in `demos/yourproject-hyperview/demo.py`.
6. Edit `demos/yourproject-hyperview/README.md` and rename the copied `HyperView` title and H1 to your own project name.
7. Copy `.github/workflows/deploy-hf-space-hyperview.yml` to a new workflow file and update `space_id`, `source_dir`, `paths`, `name`, and `concurrency`.
8. Configure a Hugging Face Trusted Publisher for `Hyper3Labs/hyperview-spaces`, the `main` branch, and the exact deployment workflow filename.
9. Keep the Dockerfile on current released packages such as `hyperview==1.1.1` and `hyper-models==0.3.1`.
10. Push to `main` or trigger `workflow_dispatch`.
11. Verify the Space build logs on Hugging Face.

### Local Docker Smoke Test

```bash
docker build -t yourproject-hyperview demos/yourproject-hyperview
docker run --rm -p 7860:7860 yourproject-hyperview
```

## CI deployment model

- Reusable workflow: `.github/workflows/deploy-hf-space-reusable.yml`
- Per-space workflow(s): `.github/workflows/deploy-hf-space-*.yml`

Each per-space workflow:
1. Watches one space folder
2. Calls the reusable workflow with:
   - `space_id` (e.g. `hyper3labs/HyperView`)
   - `source_dir` (e.g. `demos/hello-world-inat24-clip-hyper3clip`)

## Deployment authentication

No long-lived GitHub secrets are required. The reusable workflow sets
`HF_OIDC_RESOURCE` to `spaces/<owner>/<space-name>` so Hugging Face can issue a
short-lived, repo-scoped deployment token.

## Add a new Space

1. Copy `demos/hello-world-inat24-clip-hyper3clip` to a new slug
2. Edit the constants block in the new `demo.py`
3. Rename the copied `HyperView` title to your own project name such as `yourproject-HyperView` or `HyperView-yourproject`
4. Edit the new folder's `README.md` YAML frontmatter and title
5. Copy `.github/workflows/deploy-hf-space-hyperview.yml` to a new workflow file
6. Update `space_id`, `paths`, and `source_dir` in the new workflow

## Contributing Back

If you open a PR with a new Space folder, also:

1. Add a row to the community table in the root `README.md`
2. State the Hugging Face Space ID in the PR description
3. State whether this repository should deploy the Space or just host the example folder
