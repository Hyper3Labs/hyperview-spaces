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

COPY --chown=user vendor/*.whl /tmp/hyperview-wheel/

RUN echo "Installing bundled HyperView wheel" \
    && pip install /tmp/hyperview-wheel/*.whl \
    && python - <<'PY'
import inspect
import hyperview as hv

print("hyperview", hv.__version__, inspect.signature(hv.launch))
PY

COPY --chown=user . .

ENV HYPERVIEW_HOST=0.0.0.0 \
    HYPERVIEW_PORT=7860 \
    HYPERVIEW_WORKSPACE_ID=precision-region-search-refcocog-hyper3clip \
    HYPERVIEW_DATASETS_DIR=/home/user/app/demo_data/datasets \
    HYPERVIEW_MEDIA_DIR=/home/user/app/demo_data/media

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD curl -f http://localhost:7860/__hyperview__/health || exit 1

CMD ["python", "demo.py"]
