FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libssl-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 user
USER user

ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR $HOME/app

RUN pip install --upgrade pip

ARG HYPERVIEW_PACKAGE="hyperview[ml]==1.0.0"
# Pinned explicitly, not left to hyperview[ml]'s `hyper-models[ml]>=0.3.1`. The
# floor would let a future model release change this demo's vectors on a rebuild,
# and the embeddings are what the demo is showing.
ARG HYPER_MODELS_VERSION=0.3.1

# Install CPU-only PyTorch first so the CPU Space does not pull CUDA wheels.
RUN pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

RUN echo "Installing ${HYPERVIEW_PACKAGE} with hyper-models==${HYPER_MODELS_VERSION}" \
    && pip install "${HYPERVIEW_PACKAGE}" "hyper-models[ml]==${HYPER_MODELS_VERSION}" \
    && python - <<'PY'
import inspect
import hyperview as hv

print("hyperview", hv.__version__, inspect.signature(hv.launch))
PY

COPY --chown=user . .

# Only POST/PATCH/DELETE under /api/ are token-gated -- media GETs stay open
# either way. This marks the server public so viewer commands run without the
# token, while provider.register, extension.install, tools and compute get 403.
ENV HYPERVIEW_NO_AUTH=1
ENV HYPERVIEW_HOST=0.0.0.0 \
    HYPERVIEW_PORT=7860 \
    HYPERVIEW_WORKSPACE_ID=logo-brand-search-clip-hyper3clip-hf-live-v4 \
    HYPERVIEW_DATASET_NAME=logo_brand_search_clip_hyper3clip_hf_live_v4 \
    HYPERVIEW_DATASETS_DIR=/home/user/app/demo_data/datasets \
    HYPERVIEW_MEDIA_DIR=/home/user/app/demo_data/logo_images

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=10s --start-period=20m --retries=3 \
    CMD curl -f http://localhost:7860/__hyperview__/health || exit 1

CMD ["python", "demo.py"]
