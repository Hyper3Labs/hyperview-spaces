FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    libssl-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 user
USER user

ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    HF_HOME=/home/user/.cache/huggingface \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR $HOME/app

RUN pip install --upgrade pip

ARG HYPERVIEW_PACKAGE=git+https://github.com/Hyper3Labs/HyperView.git@13963ffd1a1de669eb2d4dfab52f2313d644faaa
ARG HYPER_MODELS_VERSION=0.2.0

# Install CPU-only PyTorch first so the Space does not pull the default CUDA bundle.
RUN pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
RUN pip install "${HYPERVIEW_PACKAGE}" && python -c "import hyperview; print('hyperview', hyperview.__version__)"
RUN pip install "hyper-models==${HYPER_MODELS_VERSION}" && python -c "import hyper_models; print('hyper_models', hyper_models.__version__)"
RUN pip install "datasets>=4.5.0" "Pillow>=12.0.0"

COPY --chown=user . .

RUN python - <<'PY'
from pathlib import Path
import shutil

import hyperview.server.app as app

destination = Path(app.__file__).parent / "static"
if destination.exists():
    shutil.rmtree(destination)
shutil.copytree("static", destination)
print("Installed HyperView static frontend at", destination)
PY

ENV HYPERVIEW_HOST=0.0.0.0 \
    HYPERVIEW_PORT=7860 \
    HYPERVIEW_WORKSPACE_ID=abo-catalog-clip-hycoclip \
    HYPERVIEW_DATASETS_DIR=/home/user/app/demo_data/datasets \
    HYPERVIEW_MEDIA_DIR=/home/user/app/demo_data/media

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=10s --start-period=600s --retries=3 \
    CMD curl -f http://localhost:7860/__hyperview__/health || exit 1

CMD ["python", "demo.py"]
