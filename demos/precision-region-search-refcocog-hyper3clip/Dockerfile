FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
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

ARG HYPERVIEW_VERSION=1.0.0
ARG HYPER_MODELS_VERSION=0.3.0

# Install CPU-only PyTorch first so the Space does not pull the default CUDA bundle.
RUN pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
RUN echo "Installing hyperview==${HYPERVIEW_VERSION}" \
    && pip install "hyperview==${HYPERVIEW_VERSION}" \
    && python - <<'PY'
import inspect
import hyperview as hv

print("hyperview", hv.__version__, inspect.signature(hv.launch))
PY
RUN pip install "hyper-models[ml]==${HYPER_MODELS_VERSION}"

COPY --chown=user . .

ENV HYPERVIEW_HOST=0.0.0.0 \
    HYPERVIEW_PORT=7860 \
    HYPERVIEW_WORKSPACE_ID=precision-region-search-business-evidence-v3 \
    HYPERVIEW_DATASETS_DIR=/home/user/app/demo_data/datasets \
    HYPERVIEW_MEDIA_DIR=/home/user/app/demo_data/media

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD curl -f http://localhost:7860/__hyperview__/health || exit 1

CMD ["python", "demo.py"]
