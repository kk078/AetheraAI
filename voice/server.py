"""
Aethera AI - Voice Server

FastAPI server for the voice subsystem (STT/TTS).
Routes to production STT/TTS engines when available,
falls back to legacy stt_tts module.
"""
import os
import tempfile
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(title="Aethera Voice", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
VOICE_DATA_DIR = os.getenv("VOICE_DATA_DIR", "/data/voice")

_stt_engine = None
_tts_engine = None


def _get_stt():
    global _stt_engine
    if _stt_engine is None:
        try:
            from stt import WhisperEngine
            _stt_engine = WhisperEngine()
        except Exception:
            try:
                from stt_tts import get_stt
                _stt_engine = get_stt(ollama_url=OLLAMA_URL)
            except Exception:
                pass
    return _stt_engine


def _get_tts():
    global _tts_engine
    if _tts_engine is None:
        try:
            from tts import PiperEngine
            _tts_engine = PiperEngine(output_dir=VOICE_DATA_DIR)
        except Exception:
            try:
                from stt_tts import get_tts
                _tts_engine = get_tts(output_dir=VOICE_DATA_DIR)
            except Exception:
                pass
    return _tts_engine


class TTSRequest(BaseModel):
    text: str
    voice: str = "default"


@app.get("/api/health")
async def health():
    stt = _get_stt()
    tts = _get_tts()
    return {
        "status": "healthy",
        "service": "voice",
        "stt_engine": getattr(stt, "engine_type", "unavailable"),
        "tts_engine": "piper" if tts and hasattr(tts, "_piper_available") else "legacy",
    }


@app.post("/stt")
async def stt_transcribe(audio: UploadFile = File(...)):
    """Transcribe an uploaded audio file to text."""
    stt = _get_stt()
    if stt is None:
        raise HTTPException(status_code=503, detail="STT engine not available")

    suffix = Path(audio.filename or "audio.wav").suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await audio.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        import asyncio
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, stt.transcribe, tmp_path)
        if isinstance(result, dict):
            return result
        return {"text": str(result), "filename": audio.filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@app.post("/api/stt/transcribe")
async def stt_transcribe_legacy(audio: UploadFile = File(...)):
    """Legacy endpoint — delegates to /stt."""
    return await stt_transcribe(audio)


@app.post("/tts")
async def tts_synthesize(request: TTSRequest):
    """Synthesize text to speech."""
    tts = _get_tts()
    if tts is None:
        raise HTTPException(status_code=503, detail="TTS engine not available")

    try:
        if hasattr(tts, "synthesize"):
            result = tts.synthesize(request.text, voice_id=request.voice)
            if isinstance(result, dict) and result.get("audio_path"):
                return FileResponse(
                    result["audio_path"],
                    media_type="audio/wav",
                    filename=Path(result["audio_path"]).name,
                )
            return result
        return {"text": request.text, "voice": request.voice, "status": "synthesized"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tts/stream_audio")
async def tts_stream_audio(request: TTSRequest):
    """Stream synthesized audio directly."""
    from fastapi.responses import StreamingResponse

    tts = _get_tts()
    if tts is None:
        raise HTTPException(status_code=503, detail="TTS engine not available")

    try:
        if hasattr(tts, "synthesize_to_bytes"):
            audio_bytes = tts.synthesize_to_bytes(request.text, voice_id=request.voice)
            return StreamingResponse(
                iter([audio_bytes]),
                media_type="audio/wav",
            )
        return await tts_synthesize(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tts/voices")
async def list_voices():
    """List available TTS voices."""
    tts = _get_tts()
    if tts and hasattr(tts, "list_voices"):
        try:
            return {"voices": tts.list_voices()}
        except Exception:
            pass
    return {
        "voices": [
            {"id": "default", "name": "Default", "language": "en"},
        ]
    }


@app.get("/tts/audio/{filename}")
async def serve_audio(filename: str):
    """Serve generated audio files."""
    audio_path = Path(VOICE_DATA_DIR) / filename
    if audio_path.exists():
        return FileResponse(audio_path, media_type="audio/wav")
    raise HTTPException(status_code=404, detail="Audio file not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8500)