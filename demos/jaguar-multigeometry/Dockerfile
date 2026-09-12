FROM python:3.12-slim
ARG HYPERVIEW_VERSION=1.1.1
RUN pip install --no-cache-dir "hyperview==${HYPERVIEW_VERSION}"
WORKDIR /app
COPY demo.py research-snapshot.json README.md SPACE_README.md ./
ENV HYPERVIEW_NO_AUTH=1
CMD ["python", "demo.py", "--export", "/output/jaguar-multigeometry"]
