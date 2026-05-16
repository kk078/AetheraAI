import { useState, useCallback, useRef, useEffect } from 'react';

const DEFAULT_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/api/voice/stream';
const INITIAL_RECONNECT_DELAY_MS = 1000;
const MAX_RECONNECT_DELAY_MS = 30000;
const MAX_RECONNECT_ATTEMPTS = 10;

/**
 * WebSocket connection hook with automatic reconnection and exponential backoff.
 *
 * @param {string} url - WebSocket server URL
 * @param {object} options
 * @param {boolean}  options.autoConnect     - Connect on mount (default true)
 * @param {number}   options.reconnectDelay - Initial reconnect delay in ms
 * @param {number}   options.maxDelay       - Maximum reconnect delay in ms
 * @param {number}   options.maxAttempts    - Maximum reconnect attempts
 * @param {function} options.onMessage       - Called with each incoming message
 * @param {function} options.onOpen          - Called when connection opens
 * @param {function} options.onClose        - Called when connection closes
 * @param {function} options.onError        - Called on error
 *
 * @returns {{ isConnected, send, lastMessage, error, connect, disconnect }}
 */
export function useWebSocket(url = DEFAULT_URL, options = {}) {
  const {
    autoConnect = true,
    reconnectDelay = INITIAL_RECONNECT_DELAY_MS,
    maxDelay = MAX_RECONNECT_DELAY_MS,
    maxAttempts = MAX_RECONNECT_ATTEMPTS,
    onMessage,
    onOpen,
    onClose,
    onError,
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState(null);
  const [error, setError] = useState(null);

  const wsRef = useRef(null);
  const reconnectTimerRef = useRef(null);
  const attemptRef = useRef(0);
  const intentionalCloseRef = useRef(false);
  const mountedRef = useRef(true);

  // Stable refs for callbacks so the connection logic doesn't depend on identity
  const onMessageRef = useRef(onMessage);
  const onOpenRef = useRef(onOpen);
  const onCloseRef = useRef(onClose);
  const onErrorRef = useRef(onError);

  useEffect(() => { onMessageRef.current = onMessage; }, [onMessage]);
  useEffect(() => { onOpenRef.current = onOpen; }, [onOpen]);
  useEffect(() => { onCloseRef.current = onClose; }, [onClose]);
  useEffect(() => { onErrorRef.current = onError; }, [onError]);

  const clearReconnectTimer = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    if (!mountedRef.current) return;
    if (wsRef.current && (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) {
      return;
    }

    intentionalCloseRef.current = false;
    clearReconnectTimer();

    let ws;
    try {
      ws = new WebSocket(url);
    } catch (err) {
      setError(err.message);
      onErrorRef.current?.(err);
      return;
    }

    wsRef.current = ws;

    ws.onopen = () => {
      if (!mountedRef.current) return;
      attemptRef.current = 0;
      setIsConnected(true);
      setError(null);
      onOpenRef.current?.();
    };

    ws.onmessage = (event) => {
      if (!mountedRef.current) return;

      let data;
      try {
        data = JSON.parse(event.data);
      } catch {
        data = event.data;
      }

      setLastMessage(data);
      onMessageRef.current?.(data);
    };

    ws.onerror = (event) => {
      if (!mountedRef.current) return;
      const err = event.error || new Error('WebSocket error');
      setError(err.message || 'WebSocket error');
      onErrorRef.current?.(err);
    };

    ws.onclose = (event) => {
      if (!mountedRef.current) return;
      wsRef.current = null;
      setIsConnected(false);

      onCloseRef.current?.(event);

      // Schedule reconnect unless we intentionally closed
      if (!intentionalCloseRef.current && attemptRef.current < maxAttempts) {
        const delay = Math.min(reconnectDelay * Math.pow(2, attemptRef.current), maxDelay);
        attemptRef.current += 1;

        reconnectTimerRef.current = setTimeout(() => {
          if (mountedRef.current && !intentionalCloseRef.current) {
            connect();
          }
        }, delay);
      }
    };
  }, [url, reconnectDelay, maxDelay, maxAttempts, clearReconnectTimer]);

  const disconnect = useCallback(() => {
    intentionalCloseRef.current = true;
    clearReconnectTimer();
    attemptRef.current = 0;

    if (wsRef.current) {
      wsRef.current.close(1000, 'Client disconnect');
      wsRef.current = null;
    }

    setIsConnected(false);
  }, [clearReconnectTimer]);

  /**
   * Send data over the WebSocket. Serialises objects to JSON automatically.
   * Returns false if the socket is not open.
   */
  const send = useCallback((data) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      return false;
    }

    const payload = typeof data === 'string' ? data : JSON.stringify(data);
    wsRef.current.send(payload);
    return true;
  }, []);

  // Auto-connect on mount, clean up on unmount
  useEffect(() => {
    mountedRef.current = true;

    if (autoConnect) {
      connect();
    }

    return () => {
      mountedRef.current = false;
      intentionalCloseRef.current = true;
      clearReconnectTimer();

      if (wsRef.current) {
        wsRef.current.close(1000, 'Component unmount');
        wsRef.current = null;
      }
    };
  }, [autoConnect, connect, clearReconnectTimer]);

  return {
    isConnected,
    send,
    lastMessage,
    error,
    connect,
    disconnect,
  };
}

export default useWebSocket;