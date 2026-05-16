import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../../utils/api';

const STATUS_STYLES = {
  connected: { dot: 'bg-green-400', text: 'text-green-400', label: 'Connected' },
  disconnected: { dot: 'bg-gray-400', text: 'text-gray-400', label: 'Disconnected' },
  error: { dot: 'bg-red-400', text: 'text-red-400', label: 'Error' },
  connecting: { dot: 'bg-amber-400 animate-pulse', text: 'text-amber-400', label: 'Connecting' },
};

export default function ConnectorPanel() {
  const [connectors, setConnectors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionInProgress, setActionInProgress] = useState({});
  const [testResults, setTestResults] = useState({});

  const fetchConnectors = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get('/api/connectors');
      const json = await res.json();
      setConnectors(json.connectors || json || []);
    } catch (err) {
      setError(err.message || 'Failed to load connectors');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchConnectors(); }, [fetchConnectors]);

  const handleConnect = async (connectorId) => {
    setActionInProgress((prev) => ({ ...prev, [connectorId]: 'connecting' }));
    try {
      await api.post(`/api/connectors/${connectorId}/connect`, {});
      setConnectors((prev) => prev.map((c) => c.id === connectorId ? { ...c, status: 'connected' } : c));
    } catch (err) {
      setConnectors((prev) => prev.map((c) => c.id === connectorId ? { ...c, status: 'error', lastError: err.message } : c));
    } finally {
      setActionInProgress((prev) => {
        const next = { ...prev };
        delete next[connectorId];
        return next;
      });
    }
  };

  const handleDisconnect = async (connectorId) => {
    setActionInProgress((prev) => ({ ...prev, [connectorId]: 'disconnecting' }));
    try {
      await api.post(`/api/connectors/${connectorId}/disconnect`, {});
      setConnectors((prev) => prev.map((c) => c.id === connectorId ? { ...c, status: 'disconnected' } : c));
    } catch (err) {
      console.error('Failed to disconnect:', err);
    } finally {
      setActionInProgress((prev) => {
        const next = { ...prev };
        delete next[connectorId];
        return next;
      });
    }
  };

  const handleTest = async (connectorId) => {
    setActionInProgress((prev) => ({ ...prev, [connectorId]: 'testing' }));
    setTestResults((prev) => {
      const next = { ...prev };
      delete next[connectorId];
      return next;
    });
    try {
      const res = await api.post(`/api/connectors/${connectorId}/test`, {});
      const json = await res.json();
      setTestResults((prev) => ({ ...prev, [connectorId]: { success: true, ...json } }));
    } catch (err) {
      setTestResults((prev) => ({ ...prev, [connectorId]: { success: false, error: err.message } }));
    } finally {
      setActionInProgress((prev) => {
        const next = { ...prev };
        delete next[connectorId];
        return next;
      });
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-aethera-primary" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-400">
          <p className="font-medium">Failed to load connectors</p>
          <p className="text-sm mt-1">{error}</p>
          <button onClick={fetchConnectors} className="mt-2 text-sm underline hover:no-underline">Retry</button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-aethera-foreground">Connectors</h1>
          <p className="text-aethera-text-secondary mt-1">Manage external data source connections</p>
        </div>
        <button onClick={fetchConnectors} className="text-sm text-aethera-primary hover:underline flex items-center gap-1">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Refresh
        </button>
      </div>

      {/* Connectors List */}
      {connectors.length === 0 ? (
        <div className="bg-aethera-surface rounded-xl border border-aethera-border p-8 text-center">
          <svg className="w-12 h-12 text-aethera-text-secondary mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
          </svg>
          <p className="text-aethera-text-secondary">No connectors available</p>
        </div>
      ) : (
        <div className="space-y-3">
          {connectors.map((connector) => {
            const statusStyle = STATUS_STYLES[connector.status] || STATUS_STYLES.disconnected;
            const isBusy = actionInProgress[connector.id] !== undefined;
            const testResult = testResults[connector.id];

            return (
              <div key={connector.id} className="bg-aethera-surface rounded-xl border border-aethera-border p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="relative">
                      <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${connector.status === 'connected' ? 'bg-aethera-primary/20' : 'bg-aethera-tertiary'}`}>
                        <ConnectorIcon type={connector.type} />
                      </div>
                      <span className={`absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full border-2 border-aethera-surface ${statusStyle.dot}`} />
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <h3 className="text-sm font-medium text-aethera-foreground">{connector.name}</h3>
                        <span className={`text-xs ${statusStyle.text}`}>{statusStyle.label}</span>
                      </div>
                      <p className="text-xs text-aethera-text-secondary mt-0.5 truncate">
                        {connector.description || connector.type}
                      </p>
                      {connector.lastError && (
                        <p className="text-xs text-red-400 mt-0.5">{connector.lastError}</p>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 flex-shrink-0">
                    <button
                      onClick={() => handleTest(connector.id)}
                      disabled={isBusy || connector.status !== 'connected'}
                      className="text-xs px-3 py-1.5 rounded-lg border border-aethera-border text-aethera-text-secondary hover:text-aethera-foreground hover:border-aethera-primary disabled:opacity-40 transition-colors"
                    >
                      {actionInProgress[connector.id] === 'testing' ? 'Testing...' : 'Test'}
                    </button>
                    {connector.status === 'connected' ? (
                      <button
                        onClick={() => handleDisconnect(connector.id)}
                        disabled={isBusy}
                        className="text-xs px-3 py-1.5 rounded-lg bg-red-500/20 text-red-400 hover:bg-red-500/30 disabled:opacity-50 transition-colors"
                      >
                        {actionInProgress[connector.id] === 'disconnecting' ? 'Disconnecting...' : 'Disconnect'}
                      </button>
                    ) : (
                      <button
                        onClick={() => handleConnect(connector.id)}
                        disabled={isBusy}
                        className="text-xs px-3 py-1.5 rounded-lg bg-aethera-primary text-white hover:bg-cyan-600 disabled:opacity-50 transition-colors"
                      >
                        {actionInProgress[connector.id] === 'connecting' ? 'Connecting...' : 'Connect'}
                      </button>
                    )}
                  </div>
                </div>

                {/* Test Result */}
                {testResult && (
                  <div className={`mt-3 p-2.5 rounded-lg text-xs ${testResult.success ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}`}>
                    {testResult.success
                      ? `Connection test passed${testResult.latencyMs ? ` (${testResult.latencyMs}ms)` : ''}`
                      : `Connection test failed: ${testResult.error}`}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function ConnectorIcon({ type }) {
  const iconPath = {
    database: 'M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4',
    api: 'M13 10V3L4 14h7v7l9-11h-7z',
    file: 'M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z',
    cloud: 'M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 1.8A4.001 4.001 0 003 15z',
    messaging: 'M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z',
  };

  return (
    <svg className="w-5 h-5 text-aethera-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={iconPath[type] || iconPath.api} />
    </svg>
  );
}