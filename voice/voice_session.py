"""
Aethera AI - WebSocket Voice Session Handler

Manages full-duplex voice sessions:
  Client sends audio chunks -> STT -> Orchestrator processes -> TTS -> Client receives audio

Handles: session creation, VAD (voice activity detection), turn-taking, interruption.
"""

import asyncio
import json
import logging
import os
import time
import uuid
from enum import Enum
from typing import Dict, List, Optional

import aiohttp
from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

logger = logging.getLogger("aethera.voice_session")

ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://localhost:8000")
STT_SERVICE_URL = os.getenv("STT_SERVICE_URL", "http://localhost:8501")
TTS_SERVICE_URL = os.getenv("TTS_SERVICE_URL", "http://localhost:8502")

VAD_SILENCE_THRESHOLD = float(os.getenv("VAD_SILENCE_THRESHOLD", "0.02"))
VAD_SILENCE_DURATION_MS = int(os.getenv("VAD_SILENCE_DURATION_MS", "1200"))
VAD_SPEECH_THRESHOLD = float(os.getenv("VAD_SPEECH_THRESHOLD", "0.08"))
VAD_MIN_SPEECH_DURATION_MS = int(os.getenv("VAD_MIN_SPEECH_DURATION_MS", "300"))

MAX_SESSION_DURATION_SEC = int(os.getenv("MAX_SESSION_DURATION_SEC", "1800"))  # 30 min
INTERRUPTION_COOLDOWN_MS = int(os.getenv("INTERRUPTION_COOLDOWN_MS", "500"))


# ---------------------------------------------------------------------------
# Session states
# ---------------------------------------------------------------------------

class SessionState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    INTERRUPTED = "interrupted"
    ENDED = "ended"


class VoiceSessionConfig(BaseModel):
    voice: Optional[str] = None
    language: Optional[str] = None
    vad_enabled: bool = True
    auto_gain: bool = True
    interruption_enabled: bool = True


class VoiceSessionInfo(BaseModel):
    session_id: str
    state: SessionState
    config: VoiceSessionConfig
    created_at: float
    last_activity: float
    turn_count: int
    total_speech_duration: float
    total_listening_duration: float


# ---------------------------------------------------------------------------
# Voice Activity Detector
# ---------------------------------------------------------------------------

class VoiceActivityDetector:
    """
    Energy-based voice activity detector.

    Uses RMS energy of raw PCM 16-bit audio chunks to determine
    whether the user is speaking. Tracks speech/silence transitions
    for turn-taking decisions.
    """

    def __init__(
        self,
        silence_threshold: float = VAD_SILENCE_THRESHOLD,
        speech_threshold: float = VAD_SPEECH_THRESHOLD,
        silence_duration_ms: int = VAD_SILENCE_DURATION_MS,
        min_speech_duration_ms: int = VAD_MIN_SPEECH_DURATION_MS,
        sample_rate: int = 16000,
    ):
        self.silence_threshold = silence_threshold
        self.speech_threshold = speech_threshold
        self.silence_duration_ms = silence_duration_ms
        self.min_speech_duration_ms = min_speech_duration_ms
        self.sample_rate = sample_rate

        self._is_speaking = False
        self._speech_start_time: Optional[float] = None
        self._silence_start_time: Optional[float] = None
        self._speech_frames = 0
        self._silence_frames = 0

    def process_chunk(self, audio_chunk: bytes) -> Dict:
        """
        Process an audio chunk and return VAD result.

        Returns dict with:
          - is_speaking: current speaking state
          - speech_started: True on speech onset
          - speech_ended: True when speech ends after min duration
          - energy: RMS energy value
        """
        try:
            import numpy as np
            audio = np.frombuffer(audio_chunk, dtype=np.int16).astype(np.float32)
            rms = np.sqrt(np.mean(audio ** 2)) / 32768.0
        except (ImportError, ValueError):
            # Fallback: simple byte-level energy estimate
            sample_count = len(audio_chunk) // 2
            if sample_count == 0:
                rms = 0.0
            else:
                total = 0
                for i in range(0, min(len(audio_chunk), 4096), 2):
                    val = int.from_bytes(audio_chunk[i:i+2], byteorder="little", signed=True)
                    total += val * val
                rms = (total / sample_count) ** 0.5 / 32768.0

        now = time.time()
        result = {
            "is_speaking": self._is_speaking,
            "speech_started": False,
            "speech_ended": False,
            "energy": rms,
        }

        if rms >= self.speech_threshold:
            self._speech_frames += 1
            self._silence_frames = 0
            self._silence_start_time = None

            if not self._is_speaking:
                self._is_speaking = True
                self._speech_start_time = now
                result["speech_started"] = True

        elif rms < self.silence_threshold:
            self._silence_frames += 1

            if self._is_speaking:
                silence_duration = self._silence_frames * (1000 * len(audio_chunk) / (2 * self.sample_rate))

                if silence_duration >= self.silence_duration_ms:
                    speech_duration_ms = 0
                    if self._speech_start_time:
                        speech_duration_ms = (now - self._speech_start_time) * 1000

                    if speech_duration_ms >= self.min_speech_duration_ms:
                        self._is_speaking = False
                        self._speech_start_time = None
                        self._speech_frames = 0
                        result["speech_ended"] = True
                        result["is_speaking"] = False

        return result

    def reset(self):
        """Reset detector state."""
        self._is_speaking = False
        self._speech_start_time = None
        self._silence_start_time = None
        self._speech_frames = 0
        self._silence_frames = 0


# ---------------------------------------------------------------------------
# Voice Session
# ---------------------------------------------------------------------------

class VoiceSession:
    """
    Manages a single full-duplex voice conversation session.

    Flow:
    1. Client sends audio chunks via WebSocket
    2. VAD determines when user is speaking / has stopped
    3. When speech ends, audio is sent to STT
    4. Transcription is sent to orchestrator for processing
    5. Response text is sent to TTS
    6. Audio response is streamed back to client
    7. Client can interrupt TTS output by speaking
    """

    def __init__(
        self,
        session_id: str,
        websocket: WebSocket,
        config: VoiceSessionConfig,
    ):
        self.session_id = session_id
        self.websocket = websocket
        self.config = config
        self.state = SessionState.IDLE
        self.created_at = time.time()
        self.last_activity = time.time()
        self.turn_count = 0
        self.total_speech_duration = 0.0
        self.total_listening_duration = 0.0

        self._vad = VoiceActivityDetector() if config.vad_enabled else None
        self._audio_buffer = bytearray()
        self._current_tts_task: Optional[asyncio.Task] = None
        self._is_interrupted = False
        self._last_interruption_time = 0.0
        self._listening_start_time: Optional[float] = None
        self._aiohttp_session: Optional[aiohttp.ClientSession] = None

    async def _get_http_session(self) -> aiohttp.ClientSession:
        if self._aiohttp_session is None or self._aiohttp_session.closed:
            self._aiohttp_session = aiohttp.ClientSession()
        return self._aiohttp_session

    async def run(self):
        """Main session loop. Handles incoming audio, VAD, and turn management."""
        await self.websocket.send_json({
            "type": "session_started",
            "session_id": self.session_id,
            "state": self.state,
        })

        self.state = SessionState.LISTENING
        self._listening_start_time = time.time()

        try:
            while self.state != SessionState.ENDED:
                # Check session timeout
                if time.time() - self.created_at > MAX_SESSION_DURATION_SEC:
                    await self._end_session("session_timeout")
                    break

                try:
                    message = await asyncio.wait_for(self.websocket.receive(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue

                if message["type"] == "websocket.disconnect":
                    await self._end_session("client_disconnected")
                    break

                if message["type"] == "text":
                    await self._handle_text_message(message["text"])
                    continue

                if message["type"] == "bytes":
                    audio_chunk = message.get("bytes", b"")
                    await self._handle_audio_chunk(audio_chunk)

        except WebSocketDisconnect:
            await self._end_session("websocket_disconnect")
        except Exception as exc:
            logger.error("Session %s error: %s", self.session_id, exc)
            await self._end_session("error")
        finally:
            if self._aiohttp_session and not self._aiohttp_session.closed:
                await self._aiohttp_session.close()

    async def _handle_text_message(self, text: str):
        """Handle JSON control messages from client."""
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return

        msg_type = data.get("type", "")

        if msg_type == "interrupt":
            await self._handle_interruption()

        elif msg_type == "end_session":
            await self._end_session("client_ended")

        elif msg_type == "config_update":
            new_voice = data.get("voice")
            if new_voice:
                self.config.voice = new_voice
            new_lang = data.get("language")
            if new_lang:
                self.config.language = new_lang
            await self.websocket.send_json({
                "type": "config_updated",
                "config": self.config.dict(),
            })

        elif msg_type == "push_to_talk_start":
            self.state = SessionState.LISTENING
            self._audio_buffer.clear()
            self._vad.reset() if self._vad else None
            self._listening_start_time = time.time()

        elif msg_type == "push_to_talk_end":
            if self.state == SessionState.LISTENING and len(self._audio_buffer) > 0:
                await self._process_turn()

    async def _handle_audio_chunk(self, audio_chunk: bytes):
        """Process incoming audio chunk with VAD."""
        self.last_activity = time.time()

        # If currently speaking (TTS output), check for interruption
        if self.state == SessionState.SPEAKING and self.config.interruption_enabled:
            if self._vad:
                vad_result = self._vad.process_chunk(audio_chunk)
                if vad_result.get("speech_started", False):
                    now = time.time()
                    if (now - self._last_interruption_time) > (INTERRUPTION_COOLDOWN_MS / 1000.0):
                        await self._handle_interruption()
                        # Buffer this chunk as the start of new speech
                        self._audio_buffer.extend(audio_chunk)
                        return

        # Only buffer audio when in listening state
        if self.state not in (SessionState.LISTENING, SessionState.IDLE):
            return

        self.state = SessionState.LISTENING
        self._audio_buffer.extend(audio_chunk)

        # VAD processing
        if self._vad:
            vad_result = self._vad.process_chunk(audio_chunk)

            if vad_result.get("speech_ended", False):
                # User stopped speaking; process the turn
                await self._process_turn()

    async def _process_turn(self):
        """Process a complete speech turn: STT -> Orchestrator -> TTS."""
        if len(self._audio_buffer) == 0:
            return

        # Track listening duration
        if self._listening_start_time:
            self.total_listening_duration += time.time() - self._listening_start_time

        self.state = SessionState.PROCESSING
        audio_data = bytes(self._audio_buffer)
        self._audio_buffer.clear()

        await self.websocket.send_json({
            "type": "state_change",
            "state": self.state,
            "session_id": self.session_id,
        })

        # Step 1: Speech-to-text
        transcription = await self._transcribe(audio_data)

        if not transcription or not transcription.strip():
            self.state = SessionState.LISTENING
            self._listening_start_time = time.time()
            await self.websocket.send_json({
                "type": "state_change",
                "state": self.state,
            })
            return

        await self.websocket.send_json({
            "type": "transcription",
            "text": transcription,
            "session_id": self.session_id,
        })

        self.turn_count += 1

        # Step 2: Send to orchestrator
        response_text = await self._query_orchestrator(transcription)

        if not response_text:
            self.state = SessionState.LISTENING
            self._listening_start_time = time.time()
            await self.websocket.send_json({
                "type": "state_change",
                "state": self.state,
            })
            return

        await self.websocket.send_json({
            "type": "response_text",
            "text": response_text,
            "session_id": self.session_id,
        })

        # Step 3: Text-to-speech
        self.state = SessionState.SPEAKING
        await self.websocket.send_json({
            "type": "state_change",
            "state": self.state,
        })

        self._is_interrupted = False
        await self._synthesize_and_stream(response_text)

        # Return to listening
        if not self._is_interrupted:
            self.state = SessionState.LISTENING
            self._listening_start_time = time.time()
            await self.websocket.send_json({
                "type": "state_change",
                "state": self.state,
            })

    async def _transcribe(self, audio_data: bytes) -> Optional[str]:
        """Send audio to STT service for transcription."""
        session = await self._get_http_session()

        try:
            # Send audio to STT service REST endpoint
            data = aiohttp.FormData()
            data.add_field(
                "file",
                audio_data,
                filename="audio.wav",
                content_type="audio/wav",
            )

            params = {}
            if self.config.language:
                params["language"] = self.config.language

            async with session.post(
                f"{STT_SERVICE_URL}/stt",
                data=data,
                params=params,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return result.get("text", "")
                else:
                    logger.error("STT service error: %s", resp.status)
                    return None

        except Exception as exc:
            logger.error("STT request failed: %s", exc)
            return None

    async def _query_orchestrator(self, text: str) -> Optional[str]:
        """Send transcription to orchestrator and get response."""
        session = await self._get_http_session()

        try:
            payload = {
                "query": text,
                "mode": "voice",
                "session_id": self.session_id,
            }

            async with session.post(
                f"{ORCHESTRATOR_URL}/api/chat",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60),
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    # Orchestrator returns response in various formats
                    if isinstance(result, dict):
                        return result.get("response") or result.get("text") or result.get("message", "")
                    return str(result)
                else:
                    logger.error("Orchestrator error: %s", resp.status)
                    return None

        except Exception as exc:
            logger.error("Orchestrator request failed: %s", exc)
            return None

    async def _synthesize_and_stream(self, text: str):
        """Synthesize TTS and stream audio back to client."""
        session = await self._get_http_session()

        try:
            # Use streaming audio endpoint
            payload = {
                "text": text,
                "voice": self.config.voice,
                "output_format": "wav",
            }

            async with session.post(
                f"{TTS_SERVICE_URL}/tts/stream_audio",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status == 200:
                    while True:
                        chunk = await resp.content.read(4096)
                        if not chunk:
                            break

                        if self._is_interrupted:
                            break

                        await self.websocket.send_bytes(chunk)

                    await self.websocket.send_json({
                        "type": "tts_complete",
                        "session_id": self.session_id,
                        "interrupted": self._is_interrupted,
                    })
                else:
                    error_body = await resp.text()
                    logger.error("TTS service error: %s - %s", resp.status, error_body)
                    await self.websocket.send_json({
                        "type": "tts_error",
                        "error": f"TTS failed: {resp.status}",
                        "session_id": self.session_id,
                    })

        except Exception as exc:
            logger.error("TTS synthesis failed: %s", exc)
            try:
                await self.websocket.send_json({
                    "type": "tts_error",
                    "error": str(exc),
                    "session_id": self.session_id,
                })
            except Exception:
                pass

    async def _handle_interruption(self):
        """Handle user interruption of TTS output."""
        self._is_interrupted = True
        self._last_interruption_time = time.time()
        self.state = SessionState.INTERRUPTED

        await self.websocket.send_json({
            "type": "interrupted",
            "session_id": self.session_id,
        })

        # Cancel any in-flight TTS task
        if self._current_tts_task and not self._current_tts_task.done():
            self._current_tts_task.cancel()

        # Reset VAD for new utterance
        if self._vad:
            self._vad.reset()

        # Clear audio buffer from interruption noise
        self._audio_buffer.clear()

        # Transition back to listening after cooldown
        await asyncio.sleep(INTERRUPTION_COOLDOWN_MS / 1000.0)
        self.state = SessionState.LISTENING
        self._listening_start_time = time.time()

    async def _end_session(self, reason: str = "unknown"):
        """End the voice session."""
        self.state = SessionState.ENDED

        # Track final listening duration
        if self._listening_start_time:
            self.total_listening_duration += time.time() - self._listening_start_time

        try:
            await self.websocket.send_json({
                "type": "session_ended",
                "session_id": self.session_id,
                "reason": reason,
                "stats": {
                    "turn_count": self.turn_count,
                    "total_speech_duration": self.total_speech_duration,
                    "total_listening_duration": self.total_listening_duration,
                    "session_duration": time.time() - self.created_at,
                },
            })
        except Exception:
            pass

        logger.info(
            "Session %s ended (reason=%s, turns=%d, duration=%.1fs)",
            self.session_id, reason, self.turn_count, time.time() - self.created_at,
        )

    def get_info(self) -> VoiceSessionInfo:
        return VoiceSessionInfo(
            session_id=self.session_id,
            state=self.state,
            config=self.config,
            created_at=self.created_at,
            last_activity=self.last_activity,
            turn_count=self.turn_count,
            total_speech_duration=self.total_speech_duration,
            total_listening_duration=self.total_listening_duration,
        )


# ---------------------------------------------------------------------------
# Session Manager
# ---------------------------------------------------------------------------

class VoiceSessionManager:
    """
    Manages all active voice sessions.
    Provides session creation, lookup, and cleanup.
    """

    def __init__(self):
        self._sessions: Dict[str, VoiceSession] = {}
        self._lock = asyncio.Lock()

    async def create_session(self, websocket: WebSocket, config: Optional[VoiceSessionConfig] = None) -> VoiceSession:
        """Create and register a new voice session."""
        session_id = str(uuid.uuid4())
        if config is None:
            config = VoiceSessionConfig()

        session = VoiceSession(
            session_id=session_id,
            websocket=websocket,
            config=config,
        )

        async with self._lock:
            self._sessions[session_id] = session

        logger.info("Created voice session: %s", session_id)
        return session

    async def remove_session(self, session_id: str):
        """Remove a session from tracking."""
        async with self._lock:
            self._sessions.pop(session_id, None)

    def get_session(self, session_id: str) -> Optional[VoiceSession]:
        return self._sessions.get(session_id)

    def get_active_sessions(self) -> List[VoiceSessionInfo]:
        return [s.get_info() for s in self._sessions.values() if s.state != SessionState.ENDED]

    @property
    def active_count(self) -> int:
        return len([s for s in self._sessions.values() if s.state != SessionState.ENDED])


# ---------------------------------------------------------------------------
# FastAPI WebSocket endpoint
# ---------------------------------------------------------------------------

from fastapi import APIRouter

voice_router = APIRouter()
_session_manager = VoiceSessionManager()


@voice_router.websocket("/voice/session")
async def voice_session_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for full-duplex voice sessions.

    Protocol:
    - Connect: client opens WebSocket
    - Optional initial config: {"type": "config", "voice": "...", "language": "..."}
    - Audio: client sends binary audio chunks (PCM 16-bit 16kHz mono)
    - Server events: state_change, transcription, response_text, tts_complete, interrupted
    - Control: {"type": "interrupt"}, {"type": "end_session"}
    - Push-to-talk: {"type": "push_to_talk_start"} / {"type": "push_to_talk_end"}
    """
    await websocket.accept()

    # Read optional initial config
    config = VoiceSessionConfig()
    try:
        init_msg = await asyncio.wait_for(websocket.receive(), timeout=5.0)
        if init_msg["type"] == "text":
            data = json.loads(init_msg["text"])
            if data.get("type") == "config":
                config = VoiceSessionConfig(
                    voice=data.get("voice"),
                    language=data.get("language"),
                    vad_enabled=data.get("vad_enabled", True),
                    interruption_enabled=data.get("interruption_enabled", True),
                )
    except (asyncio.TimeoutError, json.JSONDecodeError, KeyError):
        pass

    session = await _session_manager.create_session(websocket, config)

    try:
        await session.run()
    finally:
        await _session_manager.remove_session(session.session_id)


@voice_router.get("/voice/sessions")
async def list_sessions():
    """List active voice sessions."""
    return _session_manager.get_active_sessions()


@voice_router.get("/voice/sessions/{session_id}")
async def get_session_info(session_id: str):
    """Get info about a specific session."""
    session = _session_manager.get_session(session_id)
    if not session:
        return {"error": "Session not found"}
    return session.get_info()


def get_session_manager() -> VoiceSessionManager:
    """Get the global session manager."""
    return _session_manager


# ---------------------------------------------------------------------------
# Standalone runner
# ---------------------------------------------------------------------------

def create_app():
    """Create a standalone FastAPI app for the voice session service."""
    from fastapi import FastAPI

    app = FastAPI(title="Aethera Voice Session Service", version="1.0.0")
    app.include_router(voice_router)

    @app.get("/health")
    async def health():
        return {
            "status": "healthy",
            "active_sessions": _session_manager.active_count,
        }

    return app


if __name__ == "__main__":
    import uvicorn

    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8500)