# hyperview-spaces

This folder is intended to be a **standalone repository** for Hugging Face Space deployments.

Recommended GitHub repository name:

- `hyperview-spaces`

## Purpose

- Keep Space deployment logic separate from the core HyperView codebase
- Reuse one template pattern for multiple Space demos
- Deploy each demo folder to a different Hugging Face Space via GitHub Actions

## Repository layout

```text
.
├── .github/workflows/
├── spaces/
│   ├── README.md
│   └── imagenette-clip-hycoclip/
│       ├── README.md
│       ├── Dockerfile
│       ├── .dockerignore
│       └── demo.py
└── .gitignore
```

## About precomputed Lance data

Yes, you can ship precomputed LanceDB artifacts with the image. There are two valid options:

1. **Build-time precompute** (current default)
   - `RUN python demo.py --precompute`
   - Artifacts are baked into the Docker image layers
2. **Commit precomputed artifacts into this repo**
   - Useful when startup determinism is critical
   - Usually requires careful size control (and potentially Git LFS)

For now, this repo uses option 1.
