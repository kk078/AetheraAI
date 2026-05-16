FROM python:3.11-slim

WORKDIR /app

# Create non-root user first (ffmpeg creates a 'voice' group, so use -g voice)
RUN useradd --no-create-home --shell /bin/bash --gid voice voice 2>/dev/null || useradd --no-create-home --shell /bin/bash voice

# Install runtime dependencies: espeak-ng for Piper TTS, ffmpeg for audio processing,
# curl for healthcheck, libsndfile1 for soundfile library
RUN apt-get update && apt-get install -y --no-install-recommends \
    espeak-ng-espeak \
    espeak-ng-data \
    libespeak-ng1 \
    ffmpeg \
    curl \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=voice:voice . .

USER voice

EXPOSE 8500

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8500/api/health || exit 1

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8500"]