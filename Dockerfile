# Dockerfile
# Builds the AI Code Reviewer application image.
#
# Multi-stage build:
#   Stage 1 (builder): installs dependencies in an isolated layer
#   Stage 2 (final):   copies only what's needed → smaller, safer image
#
# Why multi-stage?
# The builder stage has compilers and build tools (heavy).
# The final stage only has the runtime (lean).

# ─────────────────────────────────────────────
# Stage 1 — Builder
# ─────────────────────────────────────────────
FROM python:3.11-slim AS builder

# Set working directory inside the container
WORKDIR /build

# Install system build dependencies
# (needed to compile some Python packages like chromadb)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first — Docker caches this layer
# so pip install only re-runs when requirements.txt changes
COPY requirements.txt .

# Install all Python dependencies into a separate directory
# --no-cache-dir: don't cache downloads (keeps image smaller)
# --prefix: install into /install so we can copy it to final stage
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt


# ─────────────────────────────────────────────
# Stage 2 — Final Runtime Image
# ─────────────────────────────────────────────
FROM python:3.11-slim AS final

# Labels (appear in Docker Hub and registries)
LABEL maintainer="AI Code Reviewer"
LABEL version="1.0.0"
LABEL description="AI-powered code review system"

# Set working directory
WORKDIR /app

# Install only runtime system dependencies (not build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder stage
COPY --from=builder /install /usr/local

# Copy application source code
COPY backend/app/ ./app/

# Copy startup scripts
COPY backend/scripts/ ./scripts/

# Make scripts executable
RUN chmod +x ./scripts/*.sh

# Create directories that the app needs at runtime
RUN mkdir -p /app/chroma_db /app/uploads /app/logs

# Create a non-root user for security
# Running as root inside Docker is a security risk
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --shell /bin/bash --create-home appuser

# Give the app user ownership of required directories
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Tell Docker this container listens on port 8000s
EXPOSE 8000

# Health check — Docker will restart the container if this fails
# --interval: check every 30 seconds
# --timeout:  fail if no response within 10 seconds
# --retries:  restart after 3 consecutive failures
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command — can be overridden in docker-compose.yml
CMD ["./scripts/start.sh"]