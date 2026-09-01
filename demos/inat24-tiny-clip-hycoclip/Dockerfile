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

ARG HYPERVIEW_VERSION=1.0.0
ARG HYPER_MODELS_VERSION=0.3.1

# Install CPU-only PyTorch first so the Space does not pull the default CUDA bundle,
# then pin released HyperView packages so Docker cache cannot hold an older release.
RUN pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
RUN pip install "hyperview==${HYPERVIEW_VERSION}" && python -c "import hyperview; print('hyperview', hyperview.__version__)"
RUN pip install "hyper-models[ml]==${HYPER_MODELS_VERSION}" && python -c "import hyper_models; print('hyper_models', hyper_models.__version__)"

COPY --chown=user demo.py ./demo.py

# HyperView 1.0 mints a session token and rejects unauthenticated runtime
# commands. A public Space has no way to hand visitors that token, so panel
# creation and case switching 401 without this. It marks the server public:
# visitors get the viewer commands and nothing else, so provider registration,
# extension install, tool execution and compute stay closed.
ENV HYPERVIEW_NO_AUTH=1
ENV HYPERVIEW_DATASETS_DIR=/home/user/app/demo_data/datasets \
    HYPERVIEW_MEDIA_DIR=/home/user/app/demo_data/media

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=10s --start-period=600s --retries=3 \
    CMD curl -f http://localhost:7860/__hyperview__/health || exit 1

# Dataset is built at first startup (model download + embedding computation).
# Precomputing at Docker build time causes LanceDB to be stored in overlay
# filesystem layers, which are extremely slow to reopen on free-tier CPUs.
CMD ["python", "demo.py"]
