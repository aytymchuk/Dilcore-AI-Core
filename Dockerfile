# Use a Python image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

# Install the project into `/app`
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a separate volume
ENV UV_LINK_MODE=copy

# Install the project's dependencies from the lockfile and pyproject.toml
# Use a cache mount to speed up subsequent builds
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Copy the rest of the source code
COPY . /app

# Install the project itself
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev


# Final image
FROM python:3.12-slim-bookworm

# Create a non-privileged user to run the app
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Install curl for health checks
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Copy the environment from the builder
COPY --from=builder --chown=appuser:appuser /app /app

# Place executables in the path
ENV PATH="/app/.venv/bin:$PATH"

# Set PYTHONPATH to include src so internal imports like 'from api...' work
# This is redundant if using --app-dir with uvicorn, but good for other scripts
ENV PYTHONPATH="/app/src"

# Use the non-privileged user
USER appuser

# Expose the port
EXPOSE 8000

# Health check (Docker internal)
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Run the application
# We use --app-dir src to ensure the 'api', 'shared', etc. packages are found
CMD ["uvicorn", "main:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000"]
