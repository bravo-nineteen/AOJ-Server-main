# Multi-stage build for AOJ Command OS

# ============================================
# Stage 1: Python backend builder
# ============================================
FROM python:3.11-slim AS backend-builder

WORKDIR /app/backend
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ============================================
# Stage 2: Frontend builder
# ============================================
FROM node:18-slim AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend .
RUN chmod +x node_modules/.bin/vite && npm run build

# ============================================
# Stage 3: Runtime image
# ============================================
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libopenblas-dev \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=backend-builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy backend code (all files live under backend/app/)
COPY backend/app ./backend/app
COPY backend/alembic ./backend/alembic
COPY backend/alembic.ini ./backend/alembic.ini
COPY backend/requirements.txt ./backend/requirements.txt

# Copy frontend build from builder
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Create data directories
RUN mkdir -p backend/data/uploads backend/backups backend/assets/piper_voices

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Default environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend \
    HOST=0.0.0.0 \
    PORT=8000 \
    LOG_LEVEL=INFO

EXPOSE 8000

# Run the backend (entry point is backend/app/main.py)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
