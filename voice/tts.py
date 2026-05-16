"""
Aethera AI - Text-to-Speech Service

FastAPI-based TTS service using Piper TTS (CPU-optimized).
Supports multiple voices, streaming synthesis, and fallback to espeak or macOS 'say'.
"""

import asyncio
import io
import logging
import os
import platform
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

logger = logging.getLogger("aethera.tts")

PIPER_MODEL_DIR = os.getenv("PIPER_MODEL_DIR", "/models/piper")
DEFAULT_VOICE = os.getenv("DEFAULT_VOICE", "en_US-lessac-medium")
OUTPUT_DIR = os.getenv("TTS_OUTPUT_DIR", "./data/tts_output")
SAMPLE_RATE = 22050  # Piper default
MAX_TEXT_LENGTH = int(os.getenv("MAX_TEXT_LENGTH", "5000"))

app = FastAPI(title="Aethera TTS Service", version="1.0.0")

Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Request/Response models
# ---------------------------------------------------------------------------

class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = None
    output_format: Optional[str] = "wav"  # wav, mp3, raw


class TTSResult(BaseModel):
    audio_url: str
    voice: str
    duration_estimate: float
    format: str


class VoiceInfo(BaseModel):
    id: str
    name: str
    language: str
    quality: str


class StreamTTSChunk(BaseModel):
    session_id: str
    audio_size: int
    is_final: bool


# ---------------------------------------------------------------------------
# Piper TTS engine
# ---------------------------------------------------------------------------

class PiperEngine:
    """
    Piper TTS engine with fallback to espeak / macOS say.
    Piper is CPU-optimized and runs fast even without GPU.
    """

    def __init__(self, model_dir: str = PIPER_MODEL_DIR, default_voice: str = DEFAULT_VOICE):
        self.model_dir = Path(model_dir)
        self.default_voice = default_voice
        self._piper_binary = self._find_piper()
        self._available_voices = self._discover_voices()
        self._engine_type = self._determine_engine()

    def _find_piper(self) -> Optional[str]:
        """Find piper binary on PATH."""
        try:
            result = subprocess.run(
                ["piper", "--help"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return "piper"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # Check common locations
        candidates = [
            self.model_dir / "piper",
            self.model_dir / "piper.exe",
            Path("/usr/local/bin/piper"),
            Path("/usr/bin/piper"),
        ]
        for candidate in candidates:
            if candidate.exists():
                return str(candidate)

        return None

    def _discover_voices(self) -> Dict[str, Dict]:
        """Discover available Piper voice models from the model directory."""
        voices = {}

        if not self.model_dir.exists():
            return voices

        # Piper models are .onnx + .onnx.json pairs
        for onnx_file in self.model_dir.glob("*.onnx"):
            json_file = onnx_file.with_suffix(".onnx.json")
            if json_file.exists():
                voice_id = onnx_file.stem
                try:
                    import json
                    with open(json_file, "r") as f:
                        meta = json.load(f)

                    voice_name = meta.get("name", voice_id)
                    lang = meta.get("language", {}).get("code_3", "eng")
                    quality = meta.get("quality", "medium")

                    voices[voice_id] = {
                        "id": voice_id,
                        "name": voice_name,
                        "language": lang,
                        "quality": quality,
                        "model_path": str(onnx_file),
                        "config_path": str(json_file),
                    }
                except Exception:
                    voices[voice_id] = {
                        "id": voice_id,
                        "name": voice_id,
                        "language": "eng",
                        "quality": "medium",
                        "model_path": str(onnx_file),
                        "config_path": str(json_file),
                    }

        # If no voices found, register the default
        if not voices:
            voices[self.default_voice] = {
                "id": self.default_voice,
                "name": self.default_voice,
                "language": "eng",
                "quality": "medium",
                "model_path": str(self.model_dir / f"{self.default_voice}.onnx"),
                "config_path": str(self.model_dir / f"{self.default_voice}.onnx.json"),
            }

        return voices

    def _determine_engine(self) -> str:
        """Determine which TTS engine to use."""
        if self._piper_binary and self._available_voices:
            return "piper"
        return self._detect_fallback()

    def _detect_fallback(self) -> str:
        """Detect available fallback TTS engines."""
        system = platform.system()
        if system == "Darwin":
            try:
                subprocess.run(["say", "--help"], capture_output=True, timeout=3)
                return "macos_say"
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass

        try:
            subprocess.run(["espeak", "--help"], capture_output=True, timeout=3)
            return "espeak"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        return "unavailable"

    @property
    def engine_type(self) -> str:
        return self._engine_type

    @property
    def available_voices(self) -> List[VoiceInfo]:
        return [
            VoiceInfo(id=v["id"], name=v["name"], language=v["language"], quality=v["quality"])
            for v in self._available_voices.values()
        ]

    def synthesize(self, text: str, voice: Optional[str] = None, output_format: str = "wav") -> str:
        """
        Synthesize text to audio file.

        Returns path to generated audio file.
        """
        if len(text) > MAX_TEXT_LENGTH:
            raise ValueError(f"Text exceeds maximum length of {MAX_TEXT_LENGTH} characters")

        if self._engine_type == "piper":
            return self._synthesize_piper(text, voice, output_format)
        elif self._engine_type == "espeak":
            return self._synthesize_espeak(text, voice, output_format)
        elif self._engine_type == "macos_say":
            return self._synthesize_macos_say(text, voice, output_format)
        else:
            raise RuntimeError("No TTS engine available. Install piper, espeak, or run on macOS.")

    def _synthesize_piper(self, text: str, voice: Optional[str], output_format: str) -> str:
        """Synthesize using Piper TTS."""
        voice_id = voice or self.default_voice
        voice_info = self._available_voices.get(voice_id)

        if not voice_info:
            # Try fuzzy match
            for vid, vinfo in self._available_voices.items():
                if voice_id in vid or vid.startswith(voice_id.split("-")[0]):
                    voice_info = vinfo
                    break

        if not voice_info:
            voice_info = self._available_voices.get(self.default_voice)
            if not voice_info:
                raise ValueError(f"Voice '{voice_id}' not found and no default voice available")

        output_file = str(Path(OUTPUT_DIR) / f"tts_{uuid.uuid4().hex}.wav")

        try:
            result = subprocess.run(
                [
                    self._piper_binary,
                    "--model", voice_info["model_path"],
                    "--config", voice_info["config_path"],
                    "--output_file", output_file,
                    "--output_format", "wav" if output_format == "wav" else "wav",
                ],
                input=text.encode("utf-8"),
                capture_output=True,
                timeout=30,
            )

            if result.returncode != 0:
                stderr = result.stderr.decode("utf-8", errors="replace")
                raise RuntimeError(f"Piper synthesis failed: {stderr}")

            if not Path(output_file).exists():
                raise RuntimeError("Piper produced no output file")

            # Convert format if needed
            if output_format == "mp3":
                output_file = self._convert_wav_to_mp3(output_file)

            return output_file

        except subprocess.TimeoutExpired:
            raise RuntimeError("Piper synthesis timed out")

    def _synthesize_espeak(self, text: str, voice: Optional[str], output_format: str) -> str:
        """Synthesize using espeak fallback."""
        output_file = str(Path(OUTPUT_DIR) / f"tts_{uuid.uuid4().hex}.wav")

        cmd = ["espeak", "-w", output_file]
        if voice:
            cmd.extend(["-v", voice])

        cmd.append(text)

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                raise RuntimeError(f"espeak synthesis failed: {result.stderr}")

            if not Path(output_file).exists():
                raise RuntimeError("espeak produced no output file")

            if output_format == "mp3":
                output_file = self._convert_wav_to_mp3(output_file)

            return output_file

        except FileNotFoundError:
            raise RuntimeError("espeak not found")
        except subprocess.TimeoutExpired:
            raise RuntimeError("espeak synthesis timed out")

    def _synthesize_macos_say(self, text: str, voice: Optional[str], output_format: str) -> str:
        """Synthesize using macOS 'say' fallback."""
        output_aiff = str(Path(OUTPUT_DIR) / f"tts_{uuid.uuid4().hex}.aiff")
        output_file = str(Path(OUTPUT_DIR) / f"tts_{uuid.uuid4().hex}.wav")

        cmd = ["say", "-o", output_aiff]
        if voice:
            cmd.extend(["-v", voice])
        cmd.append(text)

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                raise RuntimeError(f"macOS say synthesis failed: {result.stderr}")

            # Convert AIFF to WAV using afconvert
            subprocess.run(
                ["afconvert", output_aiff, output_file, "-f", "WAVE", "-d", "LEI16"],
                capture_output=True,
                timeout=10,
            )

            # Clean up AIFF
            if Path(output_aiff).exists():
                Path(output_aiff).unlink()

            if not Path(output_file).exists():
                # If afconvert failed, try using the AIFF directly
                if Path(output_aiff).exists():
                    output_file = output_aiff
                else:
                    raise RuntimeError("macOS say produced no output file")

            if output_format == "mp3":
                output_file = self._convert_wav_to_mp3(output_file)

            return output_file

        except FileNotFoundError:
            raise RuntimeError("macOS 'say' not found")
        except subprocess.TimeoutExpired:
            raise RuntimeError("macOS say synthesis timed out")

    def synthesize_to_bytes(self, text: str, voice: Optional[str] = None) -> bytes:
        """Synthesize text and return raw audio bytes (WAV format)."""
        output_path = self.synthesize(text, voice, "wav")
        with open(output_path, "rb") as f:
            data = f.read()
        # Clean up temp file
        Path(output_path).unlink(missing_ok=True)
        return data

    def _convert_wav_to_mp3(self, wav_path: str) -> str:
        """Convert WAV to MP3 using ffmpeg."""
        mp3_path = wav_path.rsplit(".", 1)[0] + ".mp3"
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-i", wav_path, "-codec:a", "libmp3lame", "-qscale:a", "2", mp3_path],
                capture_output=True,
                timeout=15,
            )
            if Path(mp3_path).exists():
                Path(wav_path).unlink(missing_ok=True)
                return mp3_path
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # Return WAV if conversion fails
        return wav_path

    def estimate_duration(self, text: str) -> float:
        """Estimate speech duration in seconds based on text length."""
        # Average English speech rate: ~150 words per minute = ~2.5 words/sec
        # Average word length: ~5 characters + 1 space = ~6 chars/word
        word_count = len(text.split())
        return word_count / 2.5


# ---------------------------------------------------------------------------
# Global engine instance
# ---------------------------------------------------------------------------

_engine: Optional[PiperEngine] = None


def get_engine() -> PiperEngine:
    global _engine
    if _engine is None:
        _engine = PiperEngine()
    return _engine


# ---------------------------------------------------------------------------
# REST endpoint: POST /tts
# ---------------------------------------------------------------------------

@app.post("/tts", response_model=TTSResult)
async def synthesize_speech(request: TTSRequest):
    """
    Synthesize speech from text.

    Supports multiple voices and output formats (wav, mp3).
    Falls back to espeak or macOS 'say' if Piper is unavailable.
    """
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Empty text provided")

    engine = get_engine()

    try:
        loop = asyncio.get_event_loop()
        output_path = await loop.run_in_executor(
            None,
            engine.synthesize,
            request.text,
            request.voice,
            request.output_format or "wav",
        )

        voice_used = request.voice or engine.default_voice
        duration = engine.estimate_duration(request.text)
        filename = Path(output_path).name

        return TTSResult(
            audio_url=f"/tts/audio/{filename}",
            voice=voice_used,
            duration_estimate=duration,
            format=request.output_format or "wav",
        )

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/tts/audio/{filename}")
async def get_audio_file(filename: str):
    """Serve generated audio file."""
    file_path = Path(OUTPUT_DIR) / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")

    media_type = "audio/wav"
    if filename.endswith(".mp3"):
        media_type = "audio/mpeg"

    return FileResponse(path=str(file_path), media_type=media_type, filename=filename)


@app.post("/tts/stream_audio")
async def synthesize_streaming_audio(request: TTSRequest):
    """
    Synthesize and stream audio directly as a streaming response.
    Useful for real-time playback without saving to disk.
    """
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Empty text provided")

    engine = get_engine()

    async def audio_generator():
        try:
            output_path = await asyncio.get_event_loop().run_in_executor(
                None,
                engine.synthesize,
                request.text,
                request.voice,
                "wav",
            )

            with open(output_path, "rb") as f:
                while True:
                    chunk = f.read(4096)
                    if not chunk:
                        break
                    yield chunk

            Path(output_path).unlink(missing_ok=True)

        except Exception as exc:
            logger.error("Streaming synthesis error: %s", exc)
            raise

    return StreamingResponse(
        audio_generator(),
        media_type="audio/wav",
        headers={"Content-Disposition": "inline; filename=tts_output.wav"},
    )


# ---------------------------------------------------------------------------
# WebSocket endpoint: /tts/stream
# ---------------------------------------------------------------------------

@app.websocket("/tts/stream")
async def tts_stream(websocket: WebSocket):
    """
    Streaming TTS via WebSocket.

    Protocol:
    - Client sends JSON messages: {"text": "...", "voice": "optional_voice"}
    - Server responds with binary audio chunks (WAV data)
    - Server sends JSON: {"is_final": true} when synthesis is complete
    - Client may send: {"action": "stop"} to abort current synthesis
    """
    await websocket.accept()

    session_id = str(uuid.uuid4())
    engine = get_engine()

    logger.info("TTS stream session started: %s", session_id)

    try:
        while True:
            message = await websocket.receive()

            if message["type"] == "websocket.disconnect":
                break

            if message["type"] == "text":
                try:
                    import json
                    data = json.loads(message["text"])

                    action = data.get("action")
                    if action == "stop":
                        continue

                    text = data.get("text", "")
                    voice = data.get("voice")

                    if not text.strip():
                        await websocket.send_json({"error": "Empty text", "session_id": session_id})
                        continue

                    # Synthesize in executor to avoid blocking
                    loop = asyncio.get_event_loop()
                    output_path = await loop.run_in_executor(
                        None, engine.synthesize, text, voice, "wav"
                    )

                    # Stream the audio file in chunks
                    try:
                        with open(output_path, "rb") as f:
                            while True:
                                chunk = f.read(4096)
                                if not chunk:
                                    break
                                await websocket.send_bytes(chunk)

                        # Signal completion
                        await websocket.send_json({
                            "is_final": True,
                            "session_id": session_id,
                            "voice": voice or engine.default_voice,
                        })

                    finally:
                        Path(output_path).unlink(missing_ok=True)

                except Exception as exc:
                    logger.error("TTS stream synthesis error: %s", exc)
                    try:
                        await websocket.send_json({"error": str(exc), "session_id": session_id})
                    except Exception:
                        pass

    except WebSocketDisconnect:
        logger.info("TTS stream client disconnected: %s", session_id)
    except Exception as exc:
        logger.error("TTS stream error: %s", exc)
    finally:
        logger.info("TTS stream session ended: %s", session_id)


# ---------------------------------------------------------------------------
# Voice management endpoints
# ---------------------------------------------------------------------------

@app.get("/tts/voices", response_model=List[VoiceInfo])
async def list_voices():
    """List available TTS voices."""
    engine = get_engine()
    return engine.available_voices


@app.get("/tts/status")
async def tts_status():
    """Get TTS service status and engine info."""
    engine = get_engine()
    return {
        "engine": engine.engine_type,
        "voices_available": len(engine.available_voices),
        "default_voice": engine.default_voice,
        "sample_rate": SAMPLE_RATE,
    }


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    engine = get_engine()
    return {
        "status": "healthy" if engine.engine_type != "unavailable" else "degraded",
        "engine": engine.engine_type,
        "voices": len(engine.available_voices),
    }


@app.on_event("startup")
async def startup():
    logging.basicConfig(level=logging.INFO)
    get_engine()
    logger.info("Aethera TTS service started (engine=%s)", get_engine().engine_type)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8502)