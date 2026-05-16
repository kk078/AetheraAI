import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../../utils/api';

const PRIORITY_CONFIG = {
  critical: { color: 'bg-red-500/20 text-red-400 border-red-500/30', bar: 'bg-red-400', label: 'Critical', order: 0 },
  urgent: { color: 'bg-orange-500/20 text-orange-400 border-orange-500/30', bar: 'bg-orange-400', label: 'Urgent', order: 1 },
  normal: { color: 'bg-blue-500/20 text-blue-400 border-blue-500/30', bar: 'bg-blue-400', label: 'Normal', order: 2 },
  low: { color: 'bg-gray-500/20 text-gray-400 border-gray-500/30', bar: 'bg-gray-400', label: 'Low', order: 3 },
};

export default function ActionQueue() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedId, setExpandedId] = useState(null);
  const [completing, setCompleting] = useState(new Set());
  const [filter, setFilter] = useState('all');

  const fetchQueue = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get('/api/queue');
      const json = await res.json();
      setItems(json.items || json || []);
    } catch (err) {
      setError(err.message || 'Failed to load action queue');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchQueue(); }, [fetchQueue]);

  const handleComplete = async (itemId) => {
    setCompleting((prev) => new Set(prev).add(itemId));
    try {
      await api.post(`/api/queue/${itemId}/complete`, {});
      setItems((prev) => prev.filter((item) => item.id !== itemId));
    } catch (err) {
      console.error('Failed to complete action:', err);
    } finally {
      setCompleting((prev) => {
        const next = new Set(prev);
        next.delete(itemId);
        return next;
      });
    }
  };

  const filteredItems = items
    .filter((item) => filter === 'all' || item.priority === filter)
    .sort((a, b) => {
      const orderDiff = (PRIORITY_CONFIG[a.priority]?.order ?? 9) - (PRIORITY_CONFIG[b.priority]?.order ?? 9);
      if (orderDiff !== 0) return orderDiff;
      return new Date(b.createdAt || b.timestamp) - new Date(a.createdAt || a.timestamp);
    });

  const counts = { all: items.length, critical: 0, urgent: 0, normal: 0, low: 0 };
  items.forEach((item) => { if (counts[item.priority] !== undefined) counts[item.priority]++; });

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
          <p className="font-medium">Failed to load action queue</p>
          <p className="text-sm mt-1">{error}</p>
          <button onClick={fetchQueue} className="mt-2 text-sm underline hover:no-underline">Retry</button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-aethera-foreground">Action Queue</h1>
          <p className="text-aethera-text-secondary mt-1">Prioritized tasks requiring attention</p>
        </div>
        <button onClick={fetchQueue} className="text-sm text-aethera-primary hover:underline flex items-center gap-1">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Refresh
        </button>
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-2 flex-wrap">
        {['all', 'critical', 'urgent', 'normal', 'low'].map((key) => (
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

      {/* Queue Items */}
      {filteredItems.length === 0 ? (
        <div className="bg-aethera-surface rounded-xl border border-aethera-border p-8 text-center">
          <svg className="w-12 h-12 text-aethera-text-secondary mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
          </svg>
          <p className="text-aethera-text-secondary">No actions in queue</p>
        </div>
      ) : (
        <div className="space-y-2">
          {filteredItems.map((item) => {
            const pri = PRIORITY_CONFIG[item.priority] || PRIORITY_CONFIG.normal;
            const isExpanded = expandedId === item.id;
            return (
              <div
                key={item.id}
                className={`bg-aethera-surface rounded-xl border border-aethera-border overflow-hidden transition-all hover:border-aethera-primary/50`}
              >
                <button
                  onClick={() => setExpandedId(isExpanded ? null : item.id)}
                  className="w-full p-4 flex items-center gap-3 text-left"
                >
                  <div className={`w-1 h-10 rounded-full flex-shrink-0 ${pri.bar}`} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-aethera-foreground">{item.title}</p>
                    <p className="text-xs text-aethera-text-secondary mt-0.5 truncate">{item.description}</p>
                  </div>
                  <span className={`text-xs px-2 py-0.5 rounded-full flex-shrink-0 ${pri.color}`}>{pri.label}</span>
                  {item.dueDate && (
                    <span className="text-xs text-aethera-text-secondary flex-shrink-0">
                      Due {formatDueDate(item.dueDate)}
                    </span>
                  )}
                  <svg className={`w-4 h-4 text-aethera-text-secondary transition-transform flex-shrink-0 ${isExpanded ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>

                {isExpanded && (
                  <div className="px-4 pb-4 border-t border-aethera-border pt-3">
                    <div className="text-sm text-aethera-text-secondary space-y-2">
                      {item.details && <p>{item.details}</p>}
                      {item.assignee && (
                        <p><span className="text-aethera-foreground font-medium">Assigned to:</span> {item.assignee}</p>
                      )}
                      {item.specialist && (
                        <p><span className="text-aethera-foreground font-medium">Specialist:</span> {item.specialist}</p>
                      )}
                      {item.createdAt && (
                        <p><span className="text-aethera-foreground font-medium">Created:</span> {new Date(item.createdAt).toLocaleString()}</p>
                      )}
                    </div>
                    <button
                      onClick={() => handleComplete(item.id)}
                      disabled={completing.has(item.id)}
                      className="mt-3 text-sm px-3 py-1.5 rounded-lg bg-green-600 text-white hover:bg-green-700 disabled:opacity-50 transition-colors flex items-center gap-1"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      {completing.has(item.id) ? 'Completing...' : 'Complete'}
                    </button>
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

function formatDueDate(dateStr) {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = date - now;
  const diffDays = Math.ceil(diffMs / 86400000);
  if (diffDays < 0) return `${Math.abs(diffDays)}d overdue`;
  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Tomorrow';
  return `${diffDays}d`;
}