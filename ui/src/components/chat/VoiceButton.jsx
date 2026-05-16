import React, { useState, useRef, useCallback, useEffect } from 'react';
import { useVoice } from '../../hooks/useVoice';
import { api } from '../../utils/api';

const STATES = {
  idle: 'idle',
  recording: 'recording',
  sending: 'sending',
  playing: 'playing',
  error: 'error',
};

export default function VoiceButton({ onTranscript, onTTSReady, autoSpeak = false, disabled = false }) {
  const [state, setState] = useState(STATES.idle);
  const [duration, setDuration] = useState(0);
  const [error, setError] = useState(null);
  const [audioUrl, setAudioUrl] = useState(null);
  const timerRef = useRef(null);
  const audioRef = useRef(null);

  const handleTranscript = useCallback((transcript) => {
    onTranscript?.(transcript);

    // Auto-speak the response if enabled
    if (autoSpeak && transcript) {
      speakText(transcript);
    }
  }, [onTranscript, autoSpeak]);

  const {
    isRecording,
    startRecording,
    stopRecording,
    audioBlob,
    error: voiceError,
  } = useVoice({
    maxDurationMs: 120000,
    onStop: async (blob) => {
      // Recording stopped, send to STT
      setState(STATES.sending);
      try {
        const result = await api.transcribeAudio(blob);
        const transcript = result.transcript || result.text || '';
        if (transcript.trim()) {
          handleTranscript(transcript.trim());
        } else {
          setError('No speech detected. Please try again.');
        }
      } catch (err) {
        setError(err.message || 'Speech recognition failed');
        setState(STATES.error);
        setTimeout(() => setState(STATES.idle), 3000);
        return;
      }
      setState(STATES.idle);
    },
    onError: (err) => {
      setError(err.message || 'Microphone error');
      setState(STATES.error);
      setTimeout(() => setState(STATES.idle), 3000);
    },
  });

  // Sync state with hook
  useEffect(() => {
    if (isRecording && state !== STATES.recording) {
      setState(STATES.recording);
      setDuration(0);
      timerRef.current = setInterval(() => setDuration((d) => d + 1), 1000);
    }
  }, [isRecording]);

  const speakText = useCallback(async (text) => {
    try {
      const result = await api.synthesizeSpeech(text);
      if (result.audio_url || result.audio_path) {
        const url = result.audio_url || `${api.baseURL}/api/voice/tts/audio/${result.audio_path?.split('/')?.pop()}`;
        setAudioUrl(url);
        onTTSReady?.(url);
      }
    } catch {
      // TTS not available, ignore
    }
  }, [onTTSReady]);

  const playAudio = useCallback(() => {
    if (audioRef.current) {
      setState(STATES.playing);
      audioRef.current.play();
    }
  }, []);

  const handleAudioEnded = useCallback(() => {
    setState(STATES.idle);
  }, []);

  const handleMouseDown = useCallback((e) => {
    e.preventDefault();
    if (!disabled && state === STATES.idle) {
      setError(null);
      startRecording();
    }
  }, [disabled, state, startRecording]);

  const handleMouseUp = useCallback((e) => {
    e.preventDefault();
    if (isRecording) {
      clearInterval(timerRef.current);
      stopRecording();
    }
  }, [isRecording, stopRecording]);

  const handleTouchStart = useCallback((e) => {
    e.preventDefault();
    if (!disabled && state === STATES.idle) {
      setError(null);
      startRecording();
    }
  }, [disabled, state, startRecording]);

  const handleTouchEnd = useCallback((e) => {
    e.preventDefault();
    if (isRecording) {
      clearInterval(timerRef.current);
      stopRecording();
    }
  }, [isRecording, stopRecording]);

  const isActive = isRecording || state === STATES.requesting;
  const isSending = state === STATES.sending;
  const isPlaying = state === STATES.playing;
  const isError = state === STATES.error;

  const formatDuration = (seconds) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  return (
    <div className="relative">
      <button
        onMouseDown={handleMouseDown}
        onMouseUp={handleMouseUp}
        onMouseLeave={isRecording ? handleMouseUp : undefined}
        onTouchStart={handleTouchStart}
        onTouchEnd={handleTouchEnd}
        disabled={disabled || isSending}
        className={`
          relative p-2 rounded-lg transition-all duration-200
          ${isActive
            ? 'bg-red-500 text-white scale-110'
            : isPlaying
              ? 'bg-blue-500 text-white'
              : isError
                ? 'bg-red-500/20 text-red-400'
                : 'text-aethera-text-secondary hover:text-aethera-foreground hover:bg-aethera-tertiary'
          }
          ${disabled || isSending ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
        `}
        title={isActive ? 'Release to stop recording' : 'Hold to record voice'}
      >
        {isRecording && (
          <span className="absolute inset-0 rounded-lg bg-red-500 animate-ping opacity-30" />
        )}

        {isSending ? (
          <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
        ) : isPlaying ? (
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
            <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02z" />
          </svg>
        ) : (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
          </svg>
        )}
      </button>

      {isRecording && (
        <div className="absolute -top-8 left-1/2 -translate-x-1/2 px-2 py-1 bg-red-500 text-white text-xs font-mono rounded-md whitespace-nowrap animate-fade-in">
          {formatDuration(duration)}
        </div>
      )}

      {isSending && (
        <div className="absolute -top-8 left-1/2 -translate-x-1/2 px-2 py-1 bg-aethera-surface border border-aethera-border text-aethera-text-secondary text-xs rounded-md whitespace-nowrap animate-fade-in">
          Transcribing...
        </div>
      )}

      {isError && error && (
        <div className="absolute -top-10 left-1/2 -translate-x-1/2 px-2 py-1 bg-red-500/20 border border-red-500/30 text-red-400 text-xs rounded-md whitespace-nowrap animate-fade-in">
          {error}
        </div>
      )}

      {audioUrl && !isPlaying && (
        <button
          onClick={playAudio}
          className="absolute -top-8 left-1/2 -translate-x-1/2 p-1 bg-blue-500 text-white rounded-md text-xs hover:bg-blue-600 transition-colors"
          title="Play TTS response"
        >
          <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 24 24">
            <path d="M3 9v6h4l5 5V4L7 9H3z" />
          </svg>
        </button>
      )}

      {audioUrl && (
        <audio ref={audioRef} src={audioUrl} onEnded={handleAudioEnded} className="hidden" />
      )}
    </div>
  );
}