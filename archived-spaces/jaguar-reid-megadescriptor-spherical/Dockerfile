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

ARG HYPERVIEW_VERSION=0.3.1

# Install CPU-only PyTorch first (much smaller than default CUDA bundle),
# then the released HyperView package with the ML extras.
RUN pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
RUN pip install "hyperview[ml]==${HYPERVIEW_VERSION}" \
    && python -c "import hyperview; print('hyperview', hyperview.__version__)"

COPY --chown=user demo.py ./demo.py

ENV HYPERVIEW_DATASETS_DIR=/home/user/app/demo_data/datasets \
    HYPERVIEW_MEDIA_DIR=/home/user/app/demo_data/media

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=10s --start-period=600s --retries=3 \
    CMD curl -f http://localhost:7860/__hyperview__/health || exit 1

# Dataset is built at first startup (model download + embedding computation).
# After startup the data persists in demo_data/.
CMD ["python", "demo.py"]