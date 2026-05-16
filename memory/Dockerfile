FROM python:3.11-slim

LABEL maintainer="AetheraAI"
LABEL description="Aethera AI Memory Service - Persistent memory, knowledge graph, and health records"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies for SQLCipher and cryptography
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libssl-dev \
    libsqlite3-dev \
    tclsh \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for layer caching
COPY memory/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the memory module
COPY memory/ /app/memory/

# Create data directory for persistent storage
RUN mkdir -p /data

# Health check - verify the module can be imported
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "from memory.knowledge_graph import KnowledgeGraph; from memory.health_records import HealthRecords; from memory.fact_store import FactStore; from memory.contradiction_detector import ContradictionDetector; from memory.learning import LearningStore; from memory.knowledge_gaps import KnowledgeGapStore; print('OK')" || exit 1

# Default entrypoint runs a basic startup check
ENTRYPOINT ["python", "-c"]
CMD ["from memory.knowledge_graph import get_knowledge_graph; from memory.fact_store import get_fact_store; from memory.health_records import get_health_records; from memory.learning import get_learning_store; from memory.knowledge_gaps import get_knowledge_gap_store; print('Aethera Memory Service ready')"]