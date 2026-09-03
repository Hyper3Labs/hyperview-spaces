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
    HF_HOME=/home/user/.cache/huggingface \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR $HOME/app

RUN pip install --upgrade pip

ARG HYPERVIEW_VERSION=1.1.0
ARG HYPER_MODELS_VERSION=0.3.1

# Install CPU-only PyTorch first so the Space does not pull the default CUDA bundle.
RUN pip install torch==2.9.1+cpu torchvision==0.24.1+cpu --index-url https://download.pytorch.org/whl/cpu
RUN echo "Installing hyperview==${HYPERVIEW_VERSION}" \
    && pip install "hyperview==${HYPERVIEW_VERSION}" \
    && python - <<'PY'
import inspect
import hyperview as hv

print("hyperview", hv.__version__, inspect.signature(hv.launch))
PY
RUN pip install \
    "hyper-models[ml]==${HYPER_MODELS_VERSION}" \
    "datasets>=4.5.0" \
    "Pillow>=12.0.0" \
    "timm>=1.0.0" \
    "transformers>=5.0.0,<6.0" \
    "safetensors>=0.4.0" \
    "pyyaml>=6.0.0" \
    "sentencepiece>=0.2.0" \
    "protobuf>=4.25.0"

COPY --chown=user . .

# Only POST/PATCH/DELETE under /api/ are token-gated -- media GETs stay open
# either way. This marks the server public so viewer commands run without the
# token, while provider.register, extension.install, tools and compute get 403.
ENV HYPERVIEW_NO_AUTH=1
ENV HYPERVIEW_HOST=0.0.0.0 \
    HYPERVIEW_PORT=7860 \
    HYPERVIEW_WORKSPACE_ID=manufacturing-visa-reference-clip-hyper3clip \
    HYPERVIEW_DATASETS_DIR=/home/user/app/demo_data/datasets \
    HYPERVIEW_MEDIA_DIR=/home/user/app/demo_data/media

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=10s --start-period=600s --retries=3 \
    CMD curl -f http://localhost:7860/__hyperview__/health || exit 1

CMD ["python", "demo.py"]
