/**
 * Aethera AI — PC Control Hook
 * React hook for PC control WebSocket and REST API communication.
 * Manages command sending, confirmation requests, and agent status.
 */
import { useState, useEffect, useRef, useCallback } from 'react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const WS_URL = API_URL.replace('http', 'ws');

export function usePCControl() {
  const [agentStatus, setAgentStatus] = useState(null);
  const [confirmations, setConfirmations] = useState([]);
  const [commandResults, setCommandResults] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const wsRef = useRef(null);
  const reconnectRef = useRef(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 10;

  // Connect to confirmation WebSocket
  const connectConfirmationWS = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(`${WS_URL}/api/pc/confirmations`);

    ws.onopen = () => {
      reconnectAttempts.current = 0;
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'confirmation_request') {
          setConfirmations(prev => [...prev, {
            command_id: data.command_id,
            action: data.action,
            description: data.description,
            risk_level: data.risk_level,
            parameters: data.parameters,
            timestamp: data.timestamp || new Date().toISOString(),
          }]);
        }
      } catch (e) {
        console.error('PC Control WS parse error:', e);
      }
    };

    ws.onclose = () => {
      reconnectAttempts.current += 1;
      if (reconnectAttempts.current < maxReconnectAttempts) {
        const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);
        reconnectRef.current = setTimeout(connectConfirmationWS, delay);
      }
    };

    ws.onerror = () => {
      ws.close();
    };

    wsRef.current = ws;
  }, []);

  // Disconnect WebSocket
  const disconnectConfirmationWS = useCallback(() => {
    if (reconnectRef.current) clearTimeout(reconnectRef.current);
    if (wsRef.current) wsRef.current.close();
    wsRef.current = null;
  }, []);

  // Auto-connect on mount
  useEffect(() => {
    connectConfirmationWS();
    return () => disconnectConfirmationWS();
  }, [connectConfirmationWS, disconnectConfirmationWS]);

  // Send a PC control command
  const sendCommand = useCallback(async (action, parameters = {}) => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_URL}/api/pc/command`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, parameters }),
      });
      const result = await response.json();
      setCommandResults(prev => ({
        ...prev,
        [action]: result,
      }));
      return result;
    } catch (e) {
      setError(e.message);
      return { success: false, error: e.message };
    } finally {
      setLoading(false);
    }
  }, []);

  // Confirm or deny a pending action
  const confirmAction = useCallback(async (commandId, approved, reason = null) => {
    try {
      const response = await fetch(`${API_URL}/api/pc/confirm/${commandId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approved, reason }),
      });
      const result = await response.json();
      if (approved) {
        setConfirmations(prev => prev.filter(c => c.command_id !== commandId));
      }
      return result;
    } catch (e) {
      setError(e.message);
      return { success: false, error: e.message };
    }
  }, []);

  // Dismiss a confirmation (remove from list without denying)
  const dismissConfirmation = useCallback((commandId) => {
    setConfirmations(prev => prev.filter(c => c.command_id !== commandId));
  }, []);

  // Fetch agent status
  const refreshStatus = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/pc/status`);
      const status = await response.json();
      setAgentStatus(status);
      return status;
    } catch (e) {
      setError(e.message);
      return null;
    }
  }, []);

  // Auto-refresh status periodically
  useEffect(() => {
    refreshStatus();
    const interval = setInterval(refreshStatus, 30000);
    return () => clearInterval(interval);
  }, [refreshStatus]);

  return {
    agentStatus,
    confirmations,
    commandResults,
    loading,
    error,
    sendCommand,
    confirmAction,
    dismissConfirmation,
    refreshStatus,
    isConnected: wsRef.current?.readyState === WebSocket.OPEN,
  };
}