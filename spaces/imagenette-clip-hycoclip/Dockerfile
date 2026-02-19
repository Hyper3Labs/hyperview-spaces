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

# Install latest releases from PyPI.
# For reproducible builds, pin versions here:
# RUN pip install --upgrade hyperview==0.1.1 hyper-models==0.1.0
RUN pip install --upgrade hyperview hyper-models

COPY --chown=user demo.py ./demo.py

ARG DEMO_SAMPLES=300

ENV HYPERVIEW_DATASETS_DIR=/home/user/app/demo_data/datasets \
    HYPERVIEW_MEDIA_DIR=/home/user/app/demo_data/media \
    DEMO_SAMPLES=${DEMO_SAMPLES}

RUN python demo.py --precompute

ENV HOST=0.0.0.0 \
    PORT=7860

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:7860/__hyperview__/health || exit 1

CMD ["python", "demo.py"]
