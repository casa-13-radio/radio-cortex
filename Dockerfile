# syntax=docker/dockerfile:1.4

# ============================================================================
# BASE STAGE - Common dependencies
# ============================================================================
FROM python:3.11-slim as base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    libpq-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# ============================================================================
# BUILDER STAGE - Install Python dependencies
# ============================================================================
FROM base as builder

COPY requirements.txt .
RUN pip install --user --no-warn-script-location -r requirements.txt

# ============================================================================
# DEVELOPMENT STAGE
# ============================================================================
FROM base as development

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Install dev dependencies
COPY requirements-dev.txt .
RUN pip install --user --no-warn-script-location -r requirements-dev.txt

# Copy source code
COPY . .

# Create directories
RUN mkdir -p /tmp/hunter_downloads /app/logs

EXPOSE 8000

# Default command (can be overridden in docker-compose)
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ============================================================================
# PRODUCTION STAGE
# ============================================================================
FROM base as production

# Copy only Python dependencies (no dev deps)
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Create non-root user for security
RUN groupadd -r cortex && useradd -r -g cortex cortex

# Copy source code
COPY --chown=cortex:cortex . .

# Create directories with correct permissions
RUN mkdir -p /tmp/hunter_downloads /app/logs && \
    chown -R cortex:cortex /tmp/hunter_downloads /app/logs

# Switch to non-root user
USER cortex

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Use gunicorn for production
CMD ["gunicorn", "api.main:app", \
     "-w", "4", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "-b", "0.0.0.0:8000", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info"]

# ============================================================================
# METADATA
# ============================================================================
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION

LABEL org.opencontainers.image.created=$BUILD_DATE \
      org.opencontainers.image.url="https://github.com/yourusername/radio-cortex" \
      org.opencontainers.image.source="https://github.com/yourusername/radio-cortex" \
      org.opencontainers.image.version=$VERSION \
      org.opencontainers.image.revision=$VCS_REF \
      org.opencontainers.image.vendor="Rádio Casa 13" \
      org.opencontainers.image.title="Radio Cortex" \
      org.opencontainers.image.description="AI-powered curation agents for Creative Commons music" \
      org.opencontainers.image.licenses="MIT"