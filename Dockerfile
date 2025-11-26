# syntax=docker/dockerfile:1.4

# =============================================================================
# BASE STAGE - Dependências do sistema
# =============================================================================
FROM python:3.11-slim as base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Instalar apenas dependências essenciais
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# =============================================================================
# BUILDER STAGE - Instalar dependências Python
# =============================================================================
FROM base as builder

# Instalar build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar apenas pyproject.toml primeiro (melhor cache)
COPY pyproject.toml ./

# Instalar dependências de produção (SEM dev dependencies)
RUN pip install --user --no-cache-dir \
    fastapi==0.122.0 \
    uvicorn[standard]==0.38.0 \
    gunicorn==23.0.0 \
    pydantic==2.12.4 \
    pydantic-settings==2.12.0 \
    sqlalchemy==2.0.44 \
    alembic==1.17.2 \
    asyncpg==0.31.0 \
    pgvector==0.4.1 \
    httpx==0.28.1 \
    feedparser==6.0.12 \
    beautifulsoup4==4.14.2 \
    lxml==6.0.2 \
    yt-dlp==2025.11.12 \
    groq==0.36.0 \
    mutagen==1.47.0 \
    pyyaml==6.0.3 \
    python-dotenv==1.2.1

# IMPORTANTE: sentence-transformers separado para cache
RUN pip install --user --no-cache-dir sentence-transformers==5.1.2

# =============================================================================
# PRODUCTION STAGE - Imagem final
# =============================================================================
FROM base as production

# Copiar apenas dependências Python (não o código de build)
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Criar usuário não-root
RUN groupadd -r cortex && useradd -r -g cortex cortex

# Copiar código da aplicação
COPY --chown=cortex:cortex . .

# Criar diretórios necessários
RUN mkdir -p /tmp/hunter_downloads /app/logs && \
    chown -R cortex:cortex /tmp/hunter_downloads /app/logs

# Baixar modelo de embedding DURANTE O BUILD (não no runtime!)
# Isso evita download de 500MB toda vez que o container sobe
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')" || true

USER cortex

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Comando padrão
CMD ["gunicorn", "api.main:app", \
     "-w", "2", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "-b", "0.0.0.0:8000", \
     "--timeout", "120", \
     "--graceful-timeout", "30"]

# Metadata
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=0.1.0

LABEL org.opencontainers.image.created=$BUILD_DATE \
      org.opencontainers.image.version=$VERSION \
      org.opencontainers.image.revision=$VCS_REF \
      org.opencontainers.image.title="Radio Cortex" \
      org.opencontainers.image.description="AI-powered CC music curation" \
      org.opencontainers.image.licenses="MIT"