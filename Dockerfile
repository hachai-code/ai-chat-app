# Backend image for the FastAPI app.
# Pattern: uv-managed, deps cached in their own layer, run as the uvicorn binary
# from the synced venv so signals propagate cleanly.

FROM python:3.12-slim

# Install uv (single static binary).
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Skip dev deps (pytest, ruff) in the production image.
# Copy (don't link) so the image is portable across overlay filesystems.
ENV UV_NO_DEV=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

# Install deps first for layer caching. Bind-mount the lockfiles instead of
# copying so we don't keep them as a layer.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --locked --no-install-project

# App code (changes most often → copy last).
COPY backend/ ./backend/

# Render injects $PORT (default 10000); container must bind to 0.0.0.0.
# `exec` replaces the shell so uvicorn receives SIGTERM directly.
CMD ["sh", "-c", "exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
