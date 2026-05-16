import { useState, useCallback, useRef } from 'react';

/**
 * Voice recording hook using the MediaRecorder API.
 * Manages recording lifecycle and produces audio blobs ready for upload.
 *
 * @returns {{ isRecording, startRecording, stopRecording, audioBlob, error }}
 */
export function useVoice(options = {}) {
  const { mimeType, maxDurationMs = 120000, onStart, onStop, onError } = options;

  const [isRecording, setIsRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState(null);
  const [error, setError] = useState(null);

  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const timeoutRef = useRef(null);
  const streamRef = useRef(null);

  /**
   * Pick the best supported MIME type for voice recording.
   * Prefer webm/opus, then webm, then fall back to whatever the browser offers.
   */
  const selectMimeType = useCallback(() => {
    if (mimeType) return mimeType;

    const candidates = [
      'audio/webm;codecs=opus',
      'audio/webm',
      'audio/ogg;codecs=opus',
      'audio/ogg',
      'audio/mp4',
    ];

    for (const candidate of candidates) {
      if (MediaRecorder.isTypeSupported(candidate)) {
        return candidate;
      }
    }

    // Let the browser decide
    return '';
  }, [mimeType]);

  /**
   * Start capturing audio from the default microphone.
   */
  const startRecording = useCallback(async () => {
    try {
      setError(null);
      setAudioBlob(null);
      chunksRef.current = [];

      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error('MediaRecorder API is not supported in this browser.');
      }

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 16000,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });

      streamRef.current = stream;

      const selectedMimeType = selectMimeType();
      const recorderOptions = selectedMimeType ? { mimeType: selectedMimeType } : {};

      const recorder = new MediaRecorder(stream, recorderOptions);
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      recorder.onerror = (event) => {
        const err = event.error || new Error('MediaRecorder error');
        setError(err.message);
        setIsRecording(false);
        cleanup();
        onError?.(err);
      };

      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, {
          type: selectedMimeType || 'audio/webm',
        });

        setAudioBlob(blob);
        setIsRecording(false);
        cleanup();
        onStop?.(blob);
      };

      // Start recording in 100ms slices for responsiveness
      recorder.start(100);
      setIsRecording(true);
      onStart?.();

      // Auto-stop after max duration to prevent indefinite recording
      timeoutRef.current = setTimeout(() => {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
          mediaRecorderRef.current.stop();
        }
      }, maxDurationMs);
    } catch (err) {
      setError(err.message);
      setIsRecording(false);
      cleanup();
      onError?.(err);
    }
  }, [selectMimeType, maxDurationMs, onStart, onStop, onError]);

  /**
   * Stop the current recording and release the microphone.
   */
  const stopRecording = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }

    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
    }
  }, []);

  /**
   * Release the media stream and clean up refs.
   */
  const cleanup = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }

    mediaRecorderRef.current = null;
  }, []);

  return {
    isRecording,
    startRecording,
    stopRecording,
    audioBlob,
    error,
  };
}

export default useVoice;