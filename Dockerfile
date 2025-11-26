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

# Criar usuário cortex no BUILDER para instalar dependências no lugar certo
RUN groupadd -r cortex && useradd -r -g cortex -m -d /home/cortex cortex

# Mudar para o usuário cortex
USER cortex

# Copiar apenas pyproject.toml primeiro (melhor cache)
COPY --chown=cortex:cortex pyproject.toml /home/cortex/

WORKDIR /home/cortex

# Instalar dependências de produção no HOME do usuário cortex
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

# Instalar PyTorch CPU + transformers compatíveis
# PyTorch 2.5+ é necessário para transformers 4.46+
RUN pip install --user --no-cache-dir \
    torch==2.5.1 --index-url https://download.pytorch.org/whl/cpu

# Instalar sentence-transformers (vai instalar transformers compatível automaticamente)
RUN pip install --user --no-cache-dir sentence-transformers==5.1.2

# Baixar modelo de embedding com error handling
RUN echo "📦 Downloading embedding model (all-MiniLM-L6-v2 - ~90MB)..." && \
    python -c "\
import sys; \
print('Testing imports...'); \
from sentence_transformers import SentenceTransformer; \
print('✓ Imports OK'); \
print('Downloading model...'); \
model = SentenceTransformer('all-MiniLM-L6-v2'); \
print('✅ Model downloaded and cached successfully'); \
" || (echo "❌ Model download failed - check logs above" && exit 1)

# =============================================================================
# PRODUCTION STAGE - Imagem final
# =============================================================================
FROM base as production

# Criar usuário cortex na imagem final
RUN groupadd -r cortex && useradd -r -g cortex -m -d /home/cortex cortex

# Copiar dependências Python E modelo de embedding do BUILDER
# Tudo já está em /home/cortex/.local e /home/cortex/.cache
COPY --from=builder --chown=cortex:cortex /home/cortex/.local /home/cortex/.local
COPY --from=builder --chown=cortex:cortex /home/cortex/.cache /home/cortex/.cache

# Configurar ambiente para o usuário cortex
ENV PATH=/home/cortex/.local/bin:$PATH \
    HOME=/home/cortex \
    PYTHONPATH=/app

# Mudar para o diretório da aplicação
WORKDIR /app

# Copiar código da aplicação
COPY --chown=cortex:cortex . .

# Criar diretórios necessários
RUN mkdir -p /tmp/hunter_downloads /app/logs && \
    chown -R cortex:cortex /tmp/hunter_downloads /app/logs

# Mudar para usuário não-root
USER cortex

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
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