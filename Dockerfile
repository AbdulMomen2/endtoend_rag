# ==========================================
# Multi-stage build for optimized production image
# ==========================================
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Build ALL wheels including transitive dependencies
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /build/wheels -r requirements.txt

# ==========================================
# Production image
# ==========================================
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install from pre-built wheels (includes all transitive deps)
COPY --from=builder /build/wheels /wheels
RUN pip install --no-cache --no-index --find-links=/wheels /wheels/*.whl \
    && rm -rf /wheels

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/vector_db /app/models && \
    chown -R appuser:appuser /app

USER appuser

# Copy application code
COPY --chown=appuser:appuser core/ ./core/
COPY --chown=appuser:appuser ingestion/ ./ingestion/
COPY --chown=appuser:appuser inference/ ./inference/
COPY --chown=appuser:appuser api/ ./api/
COPY --chown=appuser:appuser guardrails/ ./guardrails/

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--log-level", "info"]
