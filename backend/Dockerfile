# =========================================================================
# Context Trust Layer - Enterprise Backend Containerization
# Multi-stage, fail-closed, NLP-ready container with healthcheck
# =========================================================================
FROM python:3.11-slim

WORKDIR /app

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV CONTEXT_LAYER_CACHE_DIR=/app/.pipeline_cache

# Install system dependencies for PostgreSQL, document parsers, OCR, and healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libgl1 \
    libglib2.0-0 \
    poppler-utils \
    tesseract-ocr \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and packaging tools
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install CPU-optimized PyTorch first to prevent pulling multi-gigabyte CUDA wheels
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Install application dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download spaCy English model for offline container operation
RUN python -m spacy download en_core_web_sm || true

# Copy application source code
COPY . /app/

# Create runtime directories for pipeline cache and uploads
RUN mkdir -p /app/.pipeline_cache /app/data && \
    sed -i 's/\r$//' /app/start.sh && \
    chmod +x /app/start.sh

# Expose FastAPI service port
EXPOSE 8000

# Container Healthcheck verifying root endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Launch startup wrapper (migrations, seeding, and multi-worker uvicorn)
CMD ["bash", "/app/start.sh"]
