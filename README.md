# hyperview-spaces

This folder is intended to be a **standalone repository** for Hugging Face Space deployments. Our demo at https://huggingface.co/spaces/hyper3labs/HyperView follows the template described here. 

Recommended GitHub repository name:

- `hyperview-spaces`

## Purpose

- Keep Space deployment logic separate from the core HyperView codebase
- Reuse one template pattern for multiple Space demos
- Deploy each demo folder to a different Hugging Face Space via GitHub Actions

## Intended reuse flow

This repo is meant to be easy to hand to an external coding agent.

The happy path is:

1. Copy one folder from `spaces/`
2. Edit the constants block at the top of that folder's `demo.py`
3. Update the Space `README.md`
4. Add or retarget one deploy workflow

Both official examples install released packages from PyPI. Keep custom Space
logic in `demo.py` and Space-local files so contributors can copy a folder,
change their dataset settings, and open a PR without carrying an internal
source snapshot.

The current iNat24 Tiny example is the main HyperView geometry showcase. It
keeps the editable dataset/model choices in one place so agents do not need to
coordinate Docker args, runtime environment variables, and Python script flags.

## Create Your Own Hugging Face Space

Use the iNat24 Tiny example as a copyable starter.

1. Create a new Space at https://huggingface.co/new-space.
2. Choose a distinct Space name such as `yourproject-HyperView` or `HyperView-yourproject`.
3. Select `Docker` as the Space SDK.
4. Create the Space. Hugging Face will initialize it as a git-backed Docker Space with `sdk: docker` in `README.md`.
5. In this repository, copy `spaces/inat24-tiny-clip-hycoclip` to a new folder such as `spaces/yourproject-hyperview`.
6. Edit `spaces/yourproject-hyperview/demo.py` and change the constants block at the top of the file.
7. Edit `spaces/yourproject-hyperview/README.md` and rename the copied example from `HyperView` to your own project name.
8. Keep the Space name consistent across the Hugging Face Space ID, the README frontmatter `title`, and the Markdown H1. Good patterns are `yourproject-HyperView` and `HyperView-yourproject`.
9. Copy `.github/workflows/deploy-hf-space-hyperview.yml` to a new workflow file and update `name`, `concurrency`, `paths`, `source_dir`, and `space_id`.
10. Configure the GitHub Actions secrets `HF_USERNAME` and `HF_TOKEN`. The token must have write access to the target Hugging Face Space.
11. Push to `main` or run the workflow manually with `workflow_dispatch`.
12. Keep the Dockerfile on current released PyPI packages such as `hyperview==0.4.2` and `hyper-models==0.2.0` instead of vendoring `hyperview` into the Space folder.
13. Check the Hugging Face Space logs to confirm the Docker image built and the container started on port `7860`.

### Optional Local Test

From the `hyperview-spaces` repository root:

```bash
docker build -t yourproject-hyperview spaces/yourproject-hyperview
docker run --rm -p 7860:7860 yourproject-hyperview
```

Then open `http://127.0.0.1:7860`.

## Contribute Your Space Back

If you want your Space to appear in this repository as a community example:

1. Fork this repository or create a branch if you already have write access.
2. Add your Space folder under `spaces/<your-slug>`.
3. Rename the copied `HyperView` title and heading to your own project name such as `yourproject-HyperView` or `HyperView-yourproject`.
4. Add or update a deploy workflow for your folder if this repository should deploy it.
5. Add a row for your Space in the community table below.
6. Open a pull request describing the Hugging Face Space ID, dataset source, embedding models, and whether the deploy workflow is expected to run from this repository.

Important: deployment workflows in this repository use the shared `HF_USERNAME` and `HF_TOKEN` GitHub secrets. A contributed workflow will only deploy successfully if that token has write access to the target Space.

## Community Contributed Spaces

Add one row here when you contribute a new Space.

| Space | Hugging Face Space ID | Folder | Maintainer | Status | Notes |
| --- | --- | --- | --- | --- | --- |
| HyperView - iNat24 Tiny | `hyper3labs/HyperView` | `spaces/inat24-tiny-clip-hycoclip` | Hyper3Labs | Main demo | CLIP Euclidean 3D, CLIP spherical 3D, and HyCoCLIP Poincare on a stratified taxonomy sample |
| HyperView - Jaguar Re-ID | `hyper3labs/HyperView-Jaguar-ReID` | `archived-spaces/jaguar-reid-megadescriptor-spherical` | Hyper3Labs | Archived | Superseded by `hyper3labs/jaguar-hyperview-multigeometry` |

## Repository layout

```text
.
├── .github/workflows/
├── spaces/
│   ├── README.md
│   └── inat24-tiny-clip-hycoclip/
│       ├── README.md
│       ├── Dockerfile
│       ├── .dockerignore
│       └── demo.py
├── archived-spaces/
│   └── jaguar-reid-megadescriptor-spherical/
└── .gitignore
```

## About precomputed Lance data

Yes, you can ship precomputed LanceDB artifacts with the image. There are two valid options:

1. **Build-time precompute**
   - `RUN python -c "from demo import build_dataset; build_dataset()"`
   - Artifacts are baked into the Docker image layers
2. **Commit precomputed artifacts into this repo**
   - Useful when startup determinism is critical
   - Usually requires careful size control (and potentially Git LFS)

For now, this repo builds the dataset at first startup so Hugging Face CPU
Spaces do not reopen LanceDB artifacts from slow Docker overlay layers.
