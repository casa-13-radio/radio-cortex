# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies apenas para produção
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy pyproject.toml
COPY pyproject.toml .

# Install production dependencies only
RUN pip install --no-cache-dir -e .[production]

# Copy application code
COPY . .

# Create directories
RUN mkdir -p /tmp/hunter_downloads /app/logs

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]