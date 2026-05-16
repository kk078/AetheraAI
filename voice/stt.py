"""
Aethera AI - Speech-to-Text Service

FastAPI-based STT service using Whisper (faster-whisper or openai-whisper).
Supports multiple audio formats, language auto-detection, and streaming transcription.
Falls back to HuggingFace Whisper API when local model is unavailable.
"""

import asyncio
import io
import logging
import os
import tempfile
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional

import aiohttp
from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

logger = logging.getLogger("aethera.stt")

WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base")
HF_API_TOKEN = os.getenv("HF_TOKEN", "")
HF_WHISPER_URL = "https://api-inference.huggingface.co/models/openai/whisper-base"
SUPPORTED_FORMATS = {"wav", "mp3", "webm", "flac", "ogg", "m4a", "opus"}
MAX_AUDIO_SECONDS = int(os.getenv("MAX_AUDIO_SECONDS", "300"))
STREAM_CHUNK_DURATION_MS = int(os.getenv("STREAM_CHUNK_DURATION_MS", "2000"))
STREAM_SAMPLE_RATE = int(os.getenv("STREAM_SAMPLE_RATE", "16000"))

app = FastAPI(title="Aethera STT Service", version="1.0.0")


# ---------------------------------------------------------------------------
# Transcription result models
# ---------------------------------------------------------------------------

class TranscriptionSegment(BaseModel):
    start: float
    end: float
    text: str


class TranscriptionResult(BaseModel):
    text: str
    language: str
    language_probability: float
    duration: float
    segments: List[TranscriptionSegment] = []


class StreamTranscriptionChunk(BaseModel):
    session_id: str
    text: str
    is_final: bool
    language: Optional[str] = None
    confidence: float = 0.0


# ---------------------------------------------------------------------------
# Whisper engine abstraction
# ---------------------------------------------------------------------------

class WhisperEngine:
    """
    Abstraction over Whisper backends: faster-whisper > openai-whisper > HuggingFace API.
    """

    def __init__(self, model_size: str = WHISPER_MODEL_SIZE):
        self.model_size = model_size
        self._engine_type: Optional[str] = None
        self._model = None
        self._initialize()

    def _initialize(self):
        """Try engines in priority order."""
        try:
            from faster_whisper import WhisperModel  # noqa: F811

            logger.info("Initializing faster-whisper with model=%s", self.model_size)
            self._model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
            self._engine_type = "faster_whisper"
            logger.info("faster-whisper initialized successfully")
            return
        except ImportError:
            logger.debug("faster-whisper not available, falling back")
        except Exception as exc:
            logger.warning("faster-whisper init failed: %s", exc)

        try:
            import whisper  # noqa: F811

            logger.info("Initializing openai-whisper with model=%s", self.model_size)
            self._model = whisper.load_model(self.model_size)
            self._engine_type = "openai_whisper"
            logger.info("openai-whisper initialized successfully")
            return
        except ImportError:
            logger.debug("openai-whisper not available, falling back")
        except Exception as exc:
            logger.warning("openai-whisper init failed: %s", exc)

        self._engine_type = "huggingface_api"
        logger.info("Using HuggingFace Whisper API fallback")

    @property
    def engine_type(self) -> str:
        return self._engine_type or "unavailable"

    def transcribe(self, audio_path: str, language: Optional[str] = None) -> Dict:
        """
        Transcribe an audio file.

        Returns dict with keys: text, language, language_probability, duration, segments
        """
        if self._engine_type == "faster_whisper":
            return self._transcribe_faster_whisper(audio_path, language)
        elif self._engine_type == "openai_whisper":
            return self._transcribe_openai_whisper(audio_path, language)
        elif self._engine_type == "huggingface_api":
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, self._transcribe_hf_api(audio_path))
                return future.result()
        else:
            raise RuntimeError("No Whisper engine available")

    def transcribe_sync(self, audio_path: str, language: Optional[str] = None) -> Dict:
        """Synchronous wrapper for transcribe."""
        return self.transcribe(audio_path, language)

    def _transcribe_faster_whisper(self, audio_path: str, language: Optional[str] = None) -> Dict:
        from faster_whisper import WhisperModel

        segments_iter, info = self._model.transcribe(
            audio_path,
            language=language,
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
        )

        segments = []
        for seg in segments_iter:
            segments.append({
                "start": seg.start,
                "end": seg.end,
                "text": seg.text.strip(),
            })

        full_text = " ".join(s["text"] for s in segments)

        return {
            "text": full_text,
            "language": info.language,
            "language_probability": info.language_probability,
            "duration": info.duration,
            "segments": segments,
        }

    def _transcribe_openai_whisper(self, audio_path: str, language: Optional[str] = None) -> Dict:
        import whisper

        options = {}
        if language:
            options["language"] = language

        result = self._model.transcribe(audio_path, **options)

        segments = []
        for seg in result.get("segments", []):
            segments.append({
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"].strip(),
            })

        detected_lang = result.get("language", language or "unknown")

        return {
            "text": result["text"].strip(),
            "language": detected_lang,
            "language_probability": result.get("language_probability", 0.0),
            "duration": result.get("segments", [{}])[-1].get("end", 0.0) if segments else 0.0,
            "segments": segments,
        }

    async def _transcribe_hf_api(self, audio_path: str) -> Dict:
        """Transcribe via HuggingFace Inference API."""
        if not HF_API_TOKEN:
            raise HTTPException(
                status_code=503,
                detail="No local Whisper model and no HF_TOKEN configured for API fallback",
            )

        with open(audio_path, "rb") as f:
            audio_bytes = f.read()

        headers = {
            "Authorization": f"Bearer {HF_API_TOKEN}",
            "Content-Type": "audio/wav",
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                HF_WHISPER_URL, headers=headers, data=audio_bytes, timeout=aiohttp.ClientTimeout(total=60)
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise HTTPException(
                        status_code=502,
                        detail=f"HuggingFace API error ({resp.status}): {error_text}",
                    )
                data = await resp.json()

        text = data.get("text", "").strip()
        return {
            "text": text,
            "language": data.get("language", "unknown"),
            "language_probability": data.get("language_probability", 0.0),
            "duration": 0.0,
            "segments": [],
        }

    def transcribe_bytes(self, audio_bytes: bytes, suffix: str = ".wav", language: Optional[str] = None) -> Dict:
        """
        Transcribe raw audio bytes by writing to a temp file.
        """
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            return self.transcribe(tmp_path, language)
        finally:
            os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# Audio format conversion
# ---------------------------------------------------------------------------

def convert_audio(input_path: str, target_format: str = "wav", sample_rate: int = 16000) -> str:
    """
    Convert audio to WAV 16kHz mono using ffmpeg.
    Returns path to converted file.
    """
    output_path = input_path.rsplit(".", 1)[0] + f"_converted.{target_format}"

    try:
        import subprocess

        result = subprocess.run(
            [
                "ffmpeg", "-y", "-i", input_path,
                "-ar", str(sample_rate),
                "-ac", "1",
                "-f", target_format,
                output_path,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg conversion failed: {result.stderr}")
        return output_path
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="ffmpeg not installed; cannot convert audio format")


def detect_format(filename: str) -> Optional[str]:
    """Extract format extension from filename."""
    ext = Path(filename).suffix.lstrip(".").lower()
    if ext in SUPPORTED_FORMATS:
        return ext
    # Map common aliases
    alias_map = {"mpeg": "mp3", "m4a": "m4a", "oga": "ogg"}
    return alias_map.get(ext)


# ---------------------------------------------------------------------------
# Global engine instance
# ---------------------------------------------------------------------------

_engine: Optional[WhisperEngine] = None


def get_engine() -> WhisperEngine:
    global _engine
    if _engine is None:
        _engine = WhisperEngine()
    return _engine


# ---------------------------------------------------------------------------
# REST endpoint: POST /stt
# ---------------------------------------------------------------------------

@app.post("/stt", response_model=TranscriptionResult)
async def transcribe_audio(
    file: UploadFile = File(...),
    language: Optional[str] = None,
):
    """
    Transcribe an uploaded audio file.

    Accepts wav, mp3, webm, flac, ogg, m4a, opus.
    Auto-detects language if not specified.
    Falls back to HuggingFace Whisper API if local model unavailable.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    audio_format = detect_format(file.filename)
    if audio_format is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format. Supported: {', '.join(sorted(SUPPORTED_FORMATS))}",
        )

    audio_bytes = await file.read()
    if len(audio_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty audio file")

    suffix = f".{audio_format}"

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    converted_path = None
    try:
        # Convert non-wav formats to wav for consistent processing
        if audio_format != "wav":
            try:
                converted_path = convert_audio(tmp_path)
                process_path = converted_path
            except HTTPException:
                # If ffmpeg not available, try with original format
                process_path = tmp_path
        else:
            process_path = tmp_path

        engine = get_engine()
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, engine.transcribe, process_path, language)

        return TranscriptionResult(
            text=result["text"],
            language=result["language"],
            language_probability=result["language_probability"],
            duration=result["duration"],
            segments=[TranscriptionSegment(**s) for s in result.get("segments", [])],
        )
    finally:
        os.unlink(tmp_path)
        if converted_path and os.path.exists(converted_path):
            os.unlink(converted_path)


# ---------------------------------------------------------------------------
# WebSocket endpoint: /stt/stream
# ---------------------------------------------------------------------------

@app.websocket("/stt/stream")
async def stt_stream(websocket: WebSocket):
    """
    Streaming STT via WebSocket.

    Protocol:
    - Client sends binary audio chunks (raw PCM 16-bit 16kHz mono)
    - Client may send JSON control messages: {"action": "finalize"} or {"action": "abort"}
    - Server sends JSON TranscriptionResult chunks as transcription proceeds
    - Server sends final result with is_final=True when client finalizes or
      silence is detected after a timeout
    """
    await websocket.accept()

    session_id = str(uuid.uuid4())
    engine = get_engine()
    audio_buffer = bytearray()
    last_transcription_time = time.time()
    silence_timeout = 5.0  # seconds of silence before auto-finalize

    logger.info("STT stream session started: %s", session_id)

    try:
        while True:
            message = await asyncio.wait_for(websocket.receive(), timeout=silence_timeout + 1.0)

            if message["type"] == "websocket.disconnect":
                break

            if message["type"] == "text":
                # JSON control message
                try:
                    import json
                    control = json.loads(message["text"])
                    action = control.get("action", "")

                    if action == "finalize":
                        # Process remaining buffer and send final result
                        if len(audio_buffer) > 0:
                            result = await _process_buffer(engine, bytes(audio_buffer), session_id)
                            result["is_final"] = True
                            await websocket.send_json(result)
                        else:
                            await websocket.send_json({
                                "session_id": session_id,
                                "text": "",
                                "is_final": True,
                                "language": None,
                                "confidence": 0.0,
                            })
                        audio_buffer.clear()
                        break

                    elif action == "abort":
                        audio_buffer.clear()
                        break

                except Exception as exc:
                    logger.warning("Error parsing control message: %s", exc)
                continue

            if message["type"] == "bytes":
                chunk = message.get("bytes", b"")
                audio_buffer.extend(chunk)

                # Process buffer when we have enough data (~2 seconds at 16kHz 16-bit mono)
                chunk_size = STREAM_SAMPLE_RATE * 2 * (STREAM_CHUNK_DURATION_MS / 1000.0)
                if len(audio_buffer) >= chunk_size:
                    result = await _process_buffer(engine, bytes(audio_buffer), session_id)
                    result["is_final"] = False
                    await websocket.send_json(result)
                    audio_buffer.clear()
                    last_transcription_time = time.time()

    except asyncio.TimeoutError:
        # Silence timeout: finalize with whatever we have
        if len(audio_buffer) > 0:
            result = await _process_buffer(engine, bytes(audio_buffer), session_id)
            result["is_final"] = True
            await websocket.send_json(result)
    except WebSocketDisconnect:
        logger.info("STT stream client disconnected: %s", session_id)
    except Exception as exc:
        logger.error("STT stream error: %s", exc)
        try:
            await websocket.send_json({"error": str(exc), "session_id": session_id})
        except Exception:
            pass
    finally:
        logger.info("STT stream session ended: %s", session_id)


async def _process_buffer(engine: WhisperEngine, audio_bytes: bytes, session_id: str) -> Dict:
    """Process an audio buffer and return transcription result dict."""
    loop = asyncio.get_event_loop()

    try:
        result = await loop.run_in_executor(None, engine.transcribe_bytes, audio_bytes, ".wav", None)
        return {
            "session_id": session_id,
            "text": result.get("text", ""),
            "language": result.get("language"),
            "confidence": result.get("language_probability", 0.0),
        }
    except Exception as exc:
        logger.error("Buffer transcription error: %s", exc)
        return {
            "session_id": session_id,
            "text": "",
            "language": None,
            "confidence": 0.0,
            "error": str(exc),
        }


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    engine = get_engine()
    return {
        "status": "healthy",
        "engine": engine.engine_type,
        "model_size": WHISPER_MODEL_SIZE,
    }


@app.on_event("startup")
async def startup():
    logging.basicConfig(level=logging.INFO)
    # Pre-warm the engine
    get_engine()
    logger.info("Aethera STT service started (engine=%s)", get_engine().engine_type)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8501)