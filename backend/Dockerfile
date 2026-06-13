# ── Backend Dockerfile ─────────────────────────────────────────────────────
# Multi-stage: builder installs deps, runner is lean production image
# ───────────────────────────────────────────────────────────────────────────

# ── Stage 1: builder ────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        g++ \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install --prefix=/install --no-cache-dir -r requirements.txt

# ── Stage 2: runner ─────────────────────────────────────────────────────────
FROM python:3.11-slim AS runner

WORKDIR /app

# curl is needed for the HEALTHCHECK command
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY backend/  ./backend/
COPY src/       ./src/
COPY dataset/   ./dataset/

# Persistence directories (mounted as volumes)
RUN mkdir -p /app/chroma_db /app/outputs

ENV PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1 \
    OPENROUTER_API_KEY=""

EXPOSE 8000

# Use python instead of curl so it always works (curl added above as backup)
HEALTHCHECK --interval=20s --timeout=10s --start-period=60s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/status')" || exit 1

CMD ["uvicorn", "backend.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1"]
