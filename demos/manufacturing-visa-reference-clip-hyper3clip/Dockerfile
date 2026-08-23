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

COPY --chown=user vendor/*.whl /tmp/hyperview-wheel/

# Install CPU-only PyTorch first so the Space does not pull the default CUDA bundle.
RUN pip install torch==2.9.1+cpu torchvision==0.24.1+cpu --index-url https://download.pytorch.org/whl/cpu
RUN echo "Installing bundled HyperView wheel" \
    && pip install /tmp/hyperview-wheel/*.whl \
    && python - <<'PY'
import inspect
import hyperview as hv

print("hyperview", hv.__version__, inspect.signature(hv.launch))
PY
RUN pip install \
    "datasets>=4.5.0" \
    "Pillow>=12.0.0" \
    "timm>=1.0.0" \
    "transformers>=5.0.0,<6.0" \
    "safetensors>=0.4.0" \
    "pyyaml>=6.0.0" \
    "sentencepiece>=0.2.0" \
    "protobuf>=4.25.0"

COPY --chown=user . .

ENV HYPERVIEW_HOST=0.0.0.0 \
    HYPERVIEW_PORT=7860 \
    HYPERVIEW_WORKSPACE_ID=manufacturing-visa-reference-clip-hyper3clip \
    HYPERVIEW_DATASETS_DIR=/home/user/app/demo_data/datasets \
    HYPERVIEW_MEDIA_DIR=/home/user/app/demo_data/media

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=10s --start-period=600s --retries=3 \
    CMD curl -f http://localhost:7860/__hyperview__/health || exit 1

CMD ["python", "demo.py"]
