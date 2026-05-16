"""
Aethera AI - Voice Subsystem

Speech-to-text and text-to-speech using local models.
"""
import asyncio
import aiohttp
from typing import Optional, AsyncIterator
from pathlib import Path


class SpeechToText:
    """
    Speech-to-text using local Whisper via Ollama.
    """

    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url

    async def transcribe(self, audio_path: str) -> str:
        """
        Transcribe audio file to text.

        Args:
            audio_path: Path to audio file (WAV, MP3, etc.)

        Returns:
            Transcribed text
        """
        # Ollama doesn't have built-in STT, so we'd use Whisper directly
        # This is a placeholder for local Whisper integration
        try:
            import whisper
            model = whisper.load_model("base")
            result = model.transcribe(audio_path)
            return result["text"]
        except ImportError:
            return "Whisper not installed. Run: pip install openai-whisper"
        except Exception as e:
            return f"Transcription error: {e}"

    async def transcribe_stream(self, audio_stream: AsyncIterator[bytes]) -> AsyncIterator[str]:
        """
        Transcribe streaming audio.

        Args:
            audio_stream: Async iterator of audio chunks

        Yields:
            Transcribed text chunks
        """
        # Streaming transcription requires buffering
        # This is a simplified implementation
        buffer = b""
        async for chunk in audio_stream:
            buffer += chunk
            # Process every 5 seconds of audio (approx 80KB at 16kHz)
            if len(buffer) >= 80000:
                # Would send buffer to Whisper model
                yield "[transcription chunk]"
                buffer = b""


class TextToSpeech:
    """
    Text-to-speech using local TTS models.
    """

    def __init__(self, output_dir: str = "./data/voice"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def synthesize(
        self,
        text: str,
        voice: str = "default",
        output_path: Optional[str] = None
    ) -> str:
        """
        Synthesize speech from text.

        Args:
            text: Text to synthesize
            voice: Voice ID (default, male, female, etc.)
            output_path: Optional output file path

        Returns:
            Path to generated audio file
        """
        # Using Coqui TTS or similar
        try:
            from TTS.api import TTS

            tts = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC", progress_bar=False)

            output = output_path or str(self.output_dir / f"tts_{hash(text)}.wav")
            tts.tts_to_file(text=text, output_path=output)

            return output
        except ImportError:
            return self._fallback_tts(text, output_path)
        except Exception as e:
            return f"TTS error: {e}"

    def _fallback_tts(self, text: str, output_path: Optional[str] = None) -> str:
        """Fallback TTS using system speech."""
        import subprocess

        output = output_path or str(self.output_dir / f"tts_{hash(text)}.wav")

        # Try espeak or say (macOS)
        try:
            subprocess.run(["espeak", "-w", output, text], check=True)
            return output
        except Exception:
            try:
                subprocess.run(["say", "-o", output, text], check=True)
                return output
            except Exception:
                return "TTS not available on this system"

    async def synthesize_streaming(
        self,
        text_stream: AsyncIterator[str],
        voice: str = "default"
    ) -> AsyncIterator[bytes]:
        """
        Synthesize streaming text to audio.

        Args:
            text_stream: Async iterator of text chunks
            voice: Voice ID

        Yields:
            Audio chunks
        """
        # Buffer text and synthesize in chunks
        buffer = ""
        async for text in text_stream:
            buffer += text + " "
            # Synthesize every sentence
            if "." in buffer or "?" in buffer or "!" in buffer:
                # Would synthesize complete sentences
                yield b"[audio chunk]"
                buffer = ""


class VoiceActivityDetector:
    """
    Voice activity detection for streaming input.
    """

    def __init__(self, threshold: float = 0.5):
        self.threshold = threshold
        self._is_speaking = False

    def detect(self, audio_chunk: bytes, sample_rate: int = 16000) -> bool:
        """
        Detect if audio contains speech.

        Args:
            audio_chunk: Raw audio bytes
            sample_rate: Audio sample rate

        Returns:
            True if speech detected
        """
        import numpy as np

        # Convert to numpy array
        audio = np.frombuffer(audio_chunk, dtype=np.int16)

        # Calculate RMS energy
        rms = np.sqrt(np.mean(audio ** 2))

        # Normalize and compare to threshold
        normalized = rms / 32768  # Max for 16-bit audio
        is_speaking = normalized > self.threshold

        # State change detection
        if is_speaking and not self._is_speaking:
            self._is_speaking = True
            return True  # Speech started
        elif not is_speaking and self._is_speaking:
            self._is_speaking = False
            return False  # Speech ended

        return self._is_speaking


# Convenience functions
_stt: Optional[SpeechToText] = None
_tts: Optional[TextToSpeech] = None


def get_stt(ollama_url: str = "http://localhost:11434") -> SpeechToText:
    """Get speech-to-text instance."""
    global _stt
    if _stt is None:
        _stt = SpeechToText(ollama_url)
    return _stt


def get_tts(output_dir: str = "./data/voice") -> TextToSpeech:
    """Get text-to-speech instance."""
    global _tts
    if _tts is None:
        _tts = TextToSpeech(output_dir)
    return _tts
