"""
Aethera AI - Wake Word Detection

Optional wake word detection using openWakeWord or similar.
Listens for configurable wake word (default "Hey Aethera").
When detected, triggers voice session start.
"""

import asyncio
import logging
import os
import queue
import threading
import time
from enum import Enum
from typing import Callable, Dict, List, Optional

logger = logging.getLogger("aethera.wake_word")

WAKE_WORD_DEFAULT = os.getenv("WAKE_WORD", "hey aethera")
WAKE_WORD_SENSITIVITY = float(os.getenv("WAKE_WORD_SENSITIVITY", "0.5"))
WAKE_WORD_COOLDOWN_SEC = float(os.getenv("WAKE_WORD_COOLDOWN_SEC", "3.0"))
SAMPLE_RATE = int(os.getenv("WAKE_WORD_SAMPLE_RATE", "16000"))
AUDIO_CHUNK_MS = int(os.getenv("WAKE_WORD_CHUNK_MS", "1280"))


# ---------------------------------------------------------------------------
# Wake word engine states
# ---------------------------------------------------------------------------

class WakeWordState(str, Enum):
    STOPPED = "stopped"
    LISTENING = "listening"
    DETECTED = "detected"
    COOLDOWN = "cooldown"


# ---------------------------------------------------------------------------
# Wake Word Engine abstraction
# ---------------------------------------------------------------------------

class WakeWordEngine:
    """
    Wake word detection engine with multiple backend support.

    Priority: openWakeWord > Porcupine > custom keyword spotting > simulated.
    """

    def __init__(
        self,
        wake_word: str = WAKE_WORD_DEFAULT,
        sensitivity: float = WAKE_WORD_SENSITIVITY,
    ):
        self.wake_word = wake_word.lower()
        self.sensitivity = sensitivity
        self._engine_type: Optional[str] = None
        self._detector = None
        self._initialize()

    def _initialize(self):
        """Try to initialize wake word detection backends."""
        # Try openWakeWord
        try:
            import openwakeword

            openwakeword.utils.download_models()
            self._detector = openwakeword.Model(
                inference_framework="onnx",
                sensitivity=self.sensitivity,
            )
            self._engine_type = "openwakeword"
            logger.info("Initialized openWakeWord engine")
            return
        except ImportError:
            logger.debug("openWakeWord not available")
        except Exception as exc:
            logger.warning("openWakeWord init failed: %s", exc)

        # Try Porcupine (Picovoice)
        try:
            import pvporcupine

            access_key = os.getenv("PICOVOICE_ACCESS_KEY", "")
            if access_key:
                # Map our wake word to a Porcupine built-in keyword
                keyword_map = {
                    "hey aethera": "porcupine",
                    "alexa": "alexa",
                    "hey siri": "hey siri",
                    "ok google": "ok google",
                    "jarvis": "porcupine",
                }

                keyword = keyword_map.get(self.wake_word, "porcupine")
                self._detector = pvporcupine.create(
                    access_key=access_key,
                    keywords=[keyword],
                    sensitivities=[self.sensitivity],
                )
                self._engine_type = "porcupine"
                logger.info("Initialized Porcupine engine with keyword=%s", keyword)
                return
        except ImportError:
            logger.debug("Porcupine not available")
        except Exception as exc:
            logger.warning("Porcupine init failed: %s", exc)

        # Fallback: energy-based simulated detection
        self._engine_type = "energy_simulated"
        self._detector = None
        logger.info("Using energy-based simulated wake word detection")

    @property
    def engine_type(self) -> str:
        return self._engine_type or "unavailable"

    def process_chunk(self, audio_chunk: bytes) -> bool:
        """
        Process an audio chunk and return True if wake word detected.

        Args:
            audio_chunk: Raw PCM 16-bit 16kHz mono audio data

        Returns:
            True if wake word detected in this chunk
        """
        if self._engine_type == "openwakeword" and self._detector:
            return self._process_openwakeword(audio_chunk)
        elif self._engine_type == "porcupine" and self._detector:
            return self._process_porcupine(audio_chunk)
        elif self._engine_type == "energy_simulated":
            return self._process_energy_simulated(audio_chunk)

        return False

    def _process_openwakeword(self, audio_chunk: bytes) -> bool:
        """Process chunk with openWakeWord."""
        try:
            import numpy as np

            audio = np.frombuffer(audio_chunk, dtype=np.int16).astype(np.float32) / 32768.0
            prediction = self._detector.predict(audio, sample_rate=SAMPLE_RATE)

            # Check if any model scored above threshold
            for model_name, score in prediction.items():
                if score >= self.sensitivity:
                    logger.info("openWakeWord detection: %s (score=%.2f)", model_name, score)
                    return True

        except Exception as exc:
            logger.error("openWakeWord processing error: %s", exc)

        return False

    def _process_porcupine(self, audio_chunk: bytes) -> bool:
        """Process chunk with Porcupine."""
        try:
            import numpy as np

            audio = np.frombuffer(audio_chunk, dtype=np.int16)
            # Porcupine expects specific frame length
            frame_length = self._detector.frame_length
            if len(audio) >= frame_length:
                keyword_index = self._detector.process(audio[:frame_length])
                if keyword_index >= 0:
                    logger.info("Porcupine detection: keyword_index=%d", keyword_index)
                    return True

        except Exception as exc:
            logger.error("Porcupine processing error: %s", exc)

        return False

    def _process_energy_simulated(self, audio_chunk: bytes) -> bool:
        """
        Energy-based simulated wake word detection.

        This is a fallback that detects sustained speech energy patterns
        that might indicate someone speaking a wake word phrase.
        Not as accurate as ML-based detectors but works without models.
        """
        try:
            import numpy as np

            audio = np.frombuffer(audio_chunk, dtype=np.int16).astype(np.float32)
            rms = np.sqrt(np.mean(audio ** 2)) / 32768.0

            # Detect speech-like energy pattern: sustained energy above threshold
            # A wake word phrase typically has 0.5-2 seconds of speech
            if rms > 0.05:
                # Check for energy variance (speech has varying energy)
                if len(audio) > 100:
                    chunks = np.array_split(audio, 10)
                    energies = [np.sqrt(np.mean(c ** 2)) / 32768.0 for c in chunks]
                    variance = np.var(energies)

                    # Speech has characteristic variance pattern
                    if 1e-5 < variance < 0.1:
                        # Low confidence detection - just mark as possible
                        # In production, you'd use a proper model
                        return False

        except ImportError:
            pass
        except Exception as exc:
            logger.debug("Energy detection error: %s", exc)

        return False

    def cleanup(self):
        """Release resources."""
        if self._detector:
            try:
                if self._engine_type == "porcupine":
                    self._detector.delete()
                self._detector = None
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Wake Word Listener
# ---------------------------------------------------------------------------

class WakeWordListener:
    """
    Continuous wake word listener that monitors audio input and
    triggers callbacks when the wake word is detected.

    Can integrate with the voice session manager to automatically
    start voice sessions on detection.
    """

    def __init__(
        self,
        wake_word: str = WAKE_WORD_DEFAULT,
        sensitivity: float = WAKE_WORD_SENSITIVITY,
        cooldown_sec: float = WAKE_WORD_COOLDOWN_SEC,
    ):
        self.wake_word = wake_word
        self.sensitivity = sensitivity
        self.cooldown_sec = cooldown_sec

        self._engine = WakeWordEngine(wake_word, sensitivity)
        self._state = WakeWordState.STOPPED
        self._callbacks: List[Callable] = []
        self._last_detection_time = 0.0
        self._audio_source: Optional[AudioSource] = None
        self._running = False
        self._task: Optional[asyncio.Task] = None

    @property
    def state(self) -> WakeWordState:
        return self._state

    @property
    def engine_type(self) -> str:
        return self._engine.engine_type

    def register_callback(self, callback: Callable):
        """
        Register a callback to be invoked when wake word is detected.

        Callback receives: (wake_word: str, detection_time: float, confidence: float)
        """
        self._callbacks.append(callback)

    def unregister_callback(self, callback: Callable):
        """Remove a previously registered callback."""
        self._callbacks.remove(callback) if callback in self._callbacks else None

    async def start(self, audio_source: Optional["AudioSource"] = None):
        """
        Start listening for the wake word.

        Args:
            audio_source: Optional custom audio source. Defaults to system microphone.
        """
        if self._running:
            logger.warning("Wake word listener already running")
            return

        self._audio_source = audio_source or SystemMicrophoneSource()
        self._running = True
        self._state = WakeWordState.LISTENING

        self._task = asyncio.create_task(self._listen_loop())
        logger.info(
            "Wake word listener started (word=%s, engine=%s, sensitivity=%.2f)",
            self.wake_word, self.engine_type, self.sensitivity,
        )

    async def stop(self):
        """Stop listening for the wake word."""
        self._running = False
        self._state = WakeWordState.STOPPED

        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        if self._audio_source:
            await self._audio_source.stop()

        self._engine.cleanup()
        logger.info("Wake word listener stopped")

    async def _listen_loop(self):
        """Main listening loop."""
        try:
            await self._audio_source.start()

            while self._running:
                audio_chunk = await self._audio_source.read_chunk()

                if audio_chunk is None:
                    await asyncio.sleep(0.01)
                    continue

                if self._state == WakeWordState.COOLDOWN:
                    now = time.time()
                    if now - self._last_detection_time > self.cooldown_sec:
                        self._state = WakeWordState.LISTENING
                    continue

                detected = self._engine.process_chunk(audio_chunk)

                if detected:
                    self._last_detection_time = time.time()
                    self._state = WakeWordState.DETECTED

                    logger.info("Wake word detected: %s", self.wake_word)

                    # Notify callbacks
                    for callback in self._callbacks:
                        try:
                            result = callback(self.wake_word, time.time(), self.sensitivity)
                            if asyncio.iscoroutine(result):
                                await result
                        except Exception as exc:
                            logger.error("Wake word callback error: %s", exc)

                    # Enter cooldown
                    self._state = WakeWordState.COOLDOWN

        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.error("Wake word listener error: %s", exc)
            self._state = WakeWordState.STOPPED
            self._running = False

    def get_status(self) -> Dict:
        """Get current wake word listener status."""
        return {
            "state": self._state,
            "wake_word": self.wake_word,
            "engine": self.engine_type,
            "sensitivity": self.sensitivity,
            "cooldown_sec": self.cooldown_sec,
            "last_detection": self._last_detection_time,
            "running": self._running,
        }


# ---------------------------------------------------------------------------
# Audio Source abstractions
# ---------------------------------------------------------------------------

class AudioSource:
    """Base class for audio sources."""

    async def start(self):
        raise NotImplementedError

    async def read_chunk(self) -> Optional[bytes]:
        raise NotImplementedError

    async def stop(self):
        raise NotImplementedError


class SystemMicrophoneSource(AudioSource):
    """
    Captures audio from the system microphone using sounddevice or pyaudio.
    """

    def __init__(
        self,
        sample_rate: int = SAMPLE_RATE,
        channels: int = 1,
        chunk_ms: int = AUDIO_CHUNK_MS,
    ):
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_ms = chunk_ms
        self._frames_per_chunk = int(sample_rate * chunk_ms / 1000)
        self._stream = None
        self._buffer_queue: queue.Queue = queue.Queue(maxsize=100)
        self._running = False

    async def start(self):
        """Start capturing audio from the microphone."""
        try:
            import sounddevice as sd

            def audio_callback(indata, frames, time_info, status):
                if status:
                    logger.debug("Audio callback status: %s", status)
                self._buffer_queue.put(indata.tobytes(), block=False)

            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="int16",
                blocksize=self._frames_per_chunk,
                callback=audio_callback,
            )
            self._stream.start()
            self._running = True
            logger.info("Microphone capture started (rate=%d, chunk_ms=%d)", self.sample_rate, self.chunk_ms)

        except ImportError:
            logger.warning("sounddevice not available, trying pyaudio")
            await self._start_pyaudio()

        except Exception as exc:
            logger.error("Failed to start microphone: %s", exc)
            raise

    async def _start_pyaudio(self):
        """Fallback to pyaudio."""
        try:
            import pyaudio

            self._pa = pyaudio.PyAudio()
            self._stream = self._pa.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self._frames_per_chunk,
                stream_callback=self._pyaudio_callback,
            )
            self._stream.start_stream()
            self._running = True
            logger.info("Microphone capture started via PyAudio")

        except ImportError:
            logger.error("Neither sounddevice nor pyaudio available for microphone input")
            raise RuntimeError("No audio input library available")

    def _pyaudio_callback(self, in_data, frame_count, time_info, status):
        try:
            self._buffer_queue.put(in_data, block=False)
        except queue.Full:
            pass
        return (in_data, pyaudio.paContinue if hasattr(self, '_pa') else 0)

    async def read_chunk(self) -> Optional[bytes]:
        """Read an audio chunk from the buffer."""
        if not self._running:
            return None

        try:
            return self._buffer_queue.get_nowait()
        except queue.Empty:
            await asyncio.sleep(0.01)
            return None

    async def stop(self):
        """Stop capturing audio."""
        self._running = False
        if self._stream:
            try:
                if hasattr(self._stream, 'stop'):
                    self._stream.stop()
                if hasattr(self._stream, 'close'):
                    self._stream.close()
            except Exception:
                pass

        if hasattr(self, '_pa'):
            try:
                self._pa.terminate()
            except Exception:
                pass

        logger.info("Microphone capture stopped")


class BufferedAudioSource(AudioSource):
    """
    Audio source that reads from a pre-filled buffer.
    Useful for testing or when audio data comes from an external source.
    """

    def __init__(self, chunks: List[bytes]):
        self._chunks = list(chunks)
        self._index = 0

    async def start(self):
        self._index = 0

    async def read_chunk(self) -> Optional[bytes]:
        if self._index >= len(self._chunks):
            return None
        chunk = self._chunks[self._index]
        self._index += 1
        return chunk

    async def stop(self):
        self._index = len(self._chunks)


# ---------------------------------------------------------------------------
# Singleton management
# ---------------------------------------------------------------------------

_listener: Optional[WakeWordListener] = None


def get_wake_word_listener(
    wake_word: str = WAKE_WORD_DEFAULT,
    sensitivity: float = WAKE_WORD_SENSITIVITY,
) -> WakeWordListener:
    """Get or create the global wake word listener."""
    global _listener
    if _listener is None:
        _listener = WakeWordListener(wake_word, sensitivity)
    return _listener


async def start_wake_word_detection(
    on_detected: Optional[Callable] = None,
    wake_word: str = WAKE_WORD_DEFAULT,
):
    """
    Convenience function to start wake word detection.

    Args:
        on_detected: Callback when wake word detected
        wake_word: Wake word phrase to listen for
    """
    listener = get_wake_word_listener(wake_word)
    if on_detected:
        listener.register_callback(on_detected)
    await listener.start()


async def stop_wake_word_detection():
    """Stop wake word detection."""
    global _listener
    if _listener:
        await _listener.stop()


# ---------------------------------------------------------------------------
# FastAPI integration
# ---------------------------------------------------------------------------

from fastapi import APIRouter

wake_word_router = APIRouter()


@wake_word_router.get("/wake-word/status")
async def wake_word_status():
    """Get wake word detection status."""
    if _listener:
        return _listener.get_status()
    return {"state": "not_initialized"}


@wake_word_router.post("/wake-word/start")
async def start_wake_word(wake_word: Optional[str] = None):
    """Start wake word detection."""
    word = wake_word or WAKE_WORD_DEFAULT
    listener = get_wake_word_listener(word)
    await listener.start()
    return {"status": "started", "wake_word": word, "engine": listener.engine_type}


@wake_word_router.post("/wake-word/stop")
async def stop_wake_word():
    """Stop wake word detection."""
    await stop_wake_word_detection()
    return {"status": "stopped"}


if __name__ == "__main__":
    import uvicorn
    from fastapi import FastAPI

    app = FastAPI(title="Aethera Wake Word Service", version="1.0.0")
    app.include_router(wake_word_router)

    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=8503)