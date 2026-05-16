import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../../utils/api';

const SEVERITY_CONFIG = {
  info: { color: 'bg-blue-500/20 text-blue-400 border-blue-500/30', dot: 'bg-blue-400', label: 'Info' },
  warning: { color: 'bg-amber-500/20 text-amber-400 border-amber-500/30', dot: 'bg-amber-400', label: 'Warning' },
  urgent: { color: 'bg-orange-500/20 text-orange-400 border-orange-500/30', dot: 'bg-orange-400', label: 'Urgent' },
  critical: { color: 'bg-red-500/20 text-red-400 border-red-500/30', dot: 'bg-red-400', label: 'Critical' },
};

const SEVERITY_ORDER = { critical: 0, urgent: 1, warning: 2, info: 3 };

export default function AlertsFeed() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedId, setExpandedId] = useState(null);
  const [filter, setFilter] = useState('all');
  const [acknowledging, setAcknowledging] = useState(new Set());

  const fetchAlerts = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get('/api/alerts');
      const json = await res.json();
      setAlerts(json.alerts || json || []);
    } catch (err) {
      setError(err.message || 'Failed to load alerts');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchAlerts(); }, [fetchAlerts]);

  const handleAcknowledge = async (alertId) => {
    setAcknowledging((prev) => new Set(prev).add(alertId));
    try {
      await api.post(`/api/alerts/${alertId}/acknowledge`, {});
      setAlerts((prev) => prev.map((a) => a.id === alertId ? { ...a, acknowledged: true } : a));
    } catch (err) {
      console.error('Failed to acknowledge alert:', err);
    } finally {
      setAcknowledging((prev) => {
        const next = new Set(prev);
        next.delete(alertId);
        return next;
      });
    }
  };

  const filteredAlerts = alerts
    .filter((a) => filter === 'all' || a.severity === filter)
    .sort((a, b) => {
      const sevDiff = (SEVERITY_ORDER[a.severity] ?? 9) - (SEVERITY_ORDER[b.severity] ?? 9);
      if (sevDiff !== 0) return sevDiff;
      return new Date(b.timestamp) - new Date(a.timestamp);
    });

  const counts = { all: alerts.length, critical: 0, urgent: 0, warning: 0, info: 0 };
  alerts.forEach((a) => { if (counts[a.severity] !== undefined) counts[a.severity]++; });

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
          <p className="font-medium">Failed to load alerts</p>
          <p className="text-sm mt-1">{error}</p>
          <button onClick={fetchAlerts} className="mt-2 text-sm underline hover:no-underline">Retry</button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-aethera-foreground">Alerts</h1>
          <p className="text-aethera-text-secondary mt-1">Proactive alerts and notifications</p>
        </div>
        <button onClick={fetchAlerts} className="text-sm text-aethera-primary hover:underline flex items-center gap-1">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Refresh
        </button>
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-2 flex-wrap">
        {['all', 'critical', 'urgent', 'warning', 'info'].map((key) => (
          <button
            key={key}
            onClick={() => setFilter(key)}
            className={`text-xs px-3 py-1.5 rounded-full font-medium transition-colors ${
              filter === key
                ? 'bg-aethera-primary text-white'
                : 'bg-aethera-tertiary text-aethera-text-secondary hover:text-aethera-foreground'
            }`}
          >
            {key.charAt(0).toUpperCase() + key.slice(1)} ({counts[key]})
          </button>
        ))}
      </div>

      {/* Alerts List */}
      {filteredAlerts.length === 0 ? (
        <div className="bg-aethera-surface rounded-xl border border-aethera-border p-8 text-center">
          <svg className="w-12 h-12 text-aethera-text-secondary mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p className="text-aethera-text-secondary">No alerts to display</p>
        </div>
      ) : (
        <div className="space-y-2">
          {filteredAlerts.map((alert) => {
            const sev = SEVERITY_CONFIG[alert.severity] || SEVERITY_CONFIG.info;
            const isExpanded = expandedId === alert.id;
            return (
              <div
                key={alert.id}
                className={`bg-aethera-surface rounded-xl border overflow-hidden transition-all ${
                  alert.acknowledged ? 'border-aethera-border opacity-60' : sev.color.replace('text-', 'border-')
                }`}
              >
                <button
                  onClick={() => setExpandedId(isExpanded ? null : alert.id)}
                  className="w-full p-4 flex items-center gap-3 text-left hover:bg-aethera-tertiary/50 transition-colors"
                >
                  <span className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${sev.dot} ${alert.acknowledged ? '' : 'animate-pulse'}`} />
                  <div className="flex-1 min-w-0">
                    <p className={`text-sm font-medium ${alert.acknowledged ? 'text-aethera-text-secondary line-through' : 'text-aethera-foreground'}`}>
                      {alert.title}
                    </p>
                    <p className="text-xs text-aethera-text-secondary mt-0.5 truncate">{alert.message}</p>
                  </div>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${sev.color} flex-shrink-0`}>{sev.label}</span>
                  <span className="text-xs text-aethera-text-secondary flex-shrink-0">{formatTime(alert.timestamp)}</span>
                  <svg className={`w-4 h-4 text-aethera-text-secondary transition-transform ${isExpanded ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>

                {isExpanded && (
                  <div className="px-4 pb-4 border-t border-aethera-border pt-3">
                    <div className="text-sm text-aethera-text-secondary space-y-2">
                      {alert.details && <p>{alert.details}</p>}
                      {alert.source && (
                        <p><span className="text-aethera-foreground font-medium">Source:</span> {alert.source}</p>
                      )}
                      {alert.metadata && Object.keys(alert.metadata).length > 0 && (
                        <div className="bg-aethera-tertiary/50 rounded-lg p-3 mt-2">
                          <p className="text-xs font-medium text-aethera-foreground mb-1">Metadata</p>
                          {Object.entries(alert.metadata).map(([k, v]) => (
                            <p key={k} className="text-xs"><span className="text-aethera-text-secondary">{k}:</span> {String(v)}</p>
                          ))}
                        </div>
                      )}
                    </div>
                    {!alert.acknowledged && (
                      <button
                        onClick={() => handleAcknowledge(alert.id)}
                        disabled={acknowledging.has(alert.id)}
                        className="mt-3 text-sm px-3 py-1.5 rounded-lg bg-aethera-primary text-white hover:bg-cyan-600 disabled:opacity-50 transition-colors"
                      >
                        {acknowledging.has(alert.id) ? 'Acknowledging...' : 'Acknowledge'}
                      </button>
                    )}
                    {alert.acknowledged && (
                      <span className="mt-3 inline-flex text-xs text-green-400 items-center gap-1">
                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                        Acknowledged
                      </span>
                    )}
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

function formatTime(timestamp) {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}