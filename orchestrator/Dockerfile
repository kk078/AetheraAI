# Aethera AI - Orchestrator Docker Image
# Multi-stage build for optimized size

# =============================================================================
# BUILD STAGE
# =============================================================================
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libsqlcipher-dev \
    sqlcipher \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# =============================================================================
# RUNTIME STAGE
# =============================================================================
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies (curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && adduser --disabled-password --gecos '' aethera

# Copy installed packages from builder
COPY --from=builder /root/.local /home/aethera/.local

# Copy sqlcipher shared library from builder stage
COPY --from=builder /usr/lib/x86_64-linux-gnu/libsqlcipher* /usr/lib/x86_64-linux-gnu/

# Copy application code into orchestrator subdirectory so that
# `from orchestrator.router import...` resolves correctly
COPY --chown=aethera:aethera . ./orchestrator/

# Switch to non-root user
USER aethera

# Set PATH
ENV PATH=/home/aethera/.local/bin:$PATH

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "orchestrator.main:app", "--host", "0.0.0.0", "--port", "8000"]