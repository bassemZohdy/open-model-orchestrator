# syntax=docker/dockerfile:1
FROM python:3.12-slim-bookworm@sha256:782412e85d0f0984994c290652577d4018aff08145c85b262bb63dc0c7522254 AS build
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential cmake ninja-build && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv==0.12.11
ENV UV_PROJECT_ENVIRONMENT=/app/.venv \
    CC=gcc CXX=g++ CMAKE_BUILD_PARALLEL_LEVEL=2 \
    CMAKE_ARGS="-DGGML_NATIVE=OFF -DGGML_BLAS=OFF -DGGML_OPENMP=OFF -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF" \
    UV_PYTHON_DOWNLOADS=never
COPY pyproject.toml uv.lock build-constraints.txt ./
RUN uv sync --locked --no-dev --no-install-project
COPY src ./src
RUN uv sync --locked --no-dev --no-editable

FROM python:3.12-slim-bookworm@sha256:782412e85d0f0984994c290652577d4018aff08145c85b262bb63dc0c7522254 AS runtime
WORKDIR /app
# Debian DLA-4772-1: fix the PCRE2 findings in the pinned base without a
# mutable whole-distribution upgrade. Remaining scan findings still gate release.
RUN apt-get update && apt-get install -y --no-install-recommends --only-upgrade libpcre2-8-0=10.42-1+deb12u1 && rm -rf /var/lib/apt/lists/*
COPY --from=build /app/.venv /app/.venv
ENV PATH=/app/.venv/bin:$PATH PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    OMO_HOST=127.0.0.1 OMO_MODEL_PATH=/app/models/embedded.gguf \
    OMO_MODEL_MANIFEST=/app/models/manifest.json OMO_REGISTRY_PATH=/app/config/registry.yaml
COPY config ./config
COPY models/manifest.json ./models/manifest.json
COPY scripts/container_smoke.py ./scripts/container_smoke.py
COPY LICENSE NOTICE ./
RUN groupadd -g 10001 omo && useradd -u 10001 -g omo -M -s /usr/sbin/nologin omo
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=30s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready',timeout=2)"
ENTRYPOINT ["omo"]

FROM runtime AS slim
# Mount a pre-provisioned, checksum-matching model read-only at /app/models/embedded.gguf.

FROM python:3.12-slim-bookworm@sha256:782412e85d0f0984994c290652577d4018aff08145c85b262bb63dc0c7522254 AS model-artifact
WORKDIR /artifacts
COPY models/manifest.json ./models/manifest.json
COPY scripts/download_model.py ./download_model.py
RUN python download_model.py

FROM runtime AS bundled
COPY --from=model-artifact /artifacts/models/embedded.gguf /app/models/embedded.gguf
