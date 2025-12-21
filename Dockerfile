FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

# Label ensures we can identify and prune only this project's images
LABEL com.cyber.project="true"

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV UV_LINK_MODE=copy

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    ca-certificates \
    gosu \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
# Use Bind Mounts to avoid copying files for the dependency layer
# Use Cache Mount to persist downloaded packages
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=/app/uv.lock \
    --mount=type=bind,source=pyproject.toml,target=/app/pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Copy the application source code
COPY . .

# Install the project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Setup Entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
RUN chmod +x /app/start.sh

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

ENTRYPOINT ["/entrypoint.sh"]

# Run migrations and start the server.
CMD ["/app/start.sh"]
