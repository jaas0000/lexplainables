# Build vanaf de repo-root: docker build -f tools/bwb-import/Dockerfile -t bwb-import .
# CI (bwb-import-docker-publish.yml) pusht de image naar GHCR; Portainer pullt :latest
# (deploy/graphdb/ blijft de kennisgraaf zelf — deze image is de importservice ernaast).

# ── Builder ──────────────────────────────────────────────────────────────────
# uv leeft alléén in deze stage; de .venv die het bouwt komt mee naar runtime, uv zelf niet.
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.6 /uv /bin/uv

# Forceer de systeem-Python van de base-image, zodat de .venv-symlinks in de runtime-stage
# (identieke base-image) geldig blijven.
ENV UV_PYTHON_PREFERENCE=only-system

WORKDIR /app

# Eerst alleen de dependency-manifesten -> betere layer-caching.
COPY tools/bwb-import/pyproject.toml tools/bwb-import/uv.lock ./
RUN uv sync --frozen --no-dev

# ── Runtime ──────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# OS-pakketten patchen: de base-image loopt vaak achter op Debian-security-updates
# (util-linux/libblkid-CVE's o.a.) — spiegelt de aanpak in wetsanalyse-ai's api/Dockerfile.
# Zonder dit blokkeert de Trivy-gate in bwb-import-docker-publish.yml elke publish.
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Applicatiecode en de officiële XSD's (schemas/ is data, geen code — geen apart .dockerignore-uitzondering nodig).
COPY tools/bwb-import/app ./app
COPY tools/bwb-import/schemas ./schemas

EXPOSE 8000

CMD ["uvicorn", "app.service:app", "--host", "0.0.0.0", "--port", "8000"]
