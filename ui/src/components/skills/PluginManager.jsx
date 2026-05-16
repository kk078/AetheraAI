import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../../utils/api';

export default function PluginManager() {
  const [plugins, setPlugins] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [configPlugin, setConfigPlugin] = useState(null);
  const [saving, setSaving] = useState(false);
  const [toggling, setToggling] = useState(new Set());

  const fetchPlugins = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get('/api/plugins');
      const json = await res.json();
      setPlugins(json.plugins || json || []);
    } catch (err) {
      setError(err.message || 'Failed to load plugins');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchPlugins(); }, [fetchPlugins]);

  const handleToggle = async (pluginId, enabled) => {
    setToggling((prev) => new Set(prev).add(pluginId));
    try {
      await api.post(`/api/plugins/${pluginId}/${enabled ? 'disable' : 'enable'}`, {});
      setPlugins((prev) => prev.map((p) => p.id === pluginId ? { ...p, enabled: !enabled } : p));
    } catch (err) {
      console.error('Failed to toggle plugin:', err);
    } finally {
      setToggling((prev) => {
        const next = new Set(prev);
        next.delete(pluginId);
        return next;
      });
    }
  };

  const handleSaveConfig = async (pluginId, config) => {
    setSaving(true);
    try {
      await api.post(`/api/plugins/${pluginId}/config`, config);
      setPlugins((prev) => prev.map((p) => p.id === pluginId ? { ...p, config: { ...p.config, ...config } } : p));
      setConfigPlugin(null);
    } catch (err) {
      console.error('Failed to save config:', err);
    } finally {
      setSaving(false);
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
          <p className="font-medium">Failed to load plugins</p>
          <p className="text-sm mt-1">{error}</p>
          <button onClick={fetchPlugins} className="mt-2 text-sm underline hover:no-underline">Retry</button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-aethera-foreground">Plugins</h1>
          <p className="text-aethera-text-secondary mt-1">Manage and configure plugins</p>
        </div>
        <button onClick={fetchPlugins} className="text-sm text-aethera-primary hover:underline flex items-center gap-1">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Refresh
        </button>
      </div>

      {/* Plugin List */}
      {plugins.length === 0 ? (
        <div className="bg-aethera-surface rounded-xl border border-aethera-border p-8 text-center">
          <svg className="w-12 h-12 text-aethera-text-secondary mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M11 4a2 2 0 114 0v1a1 1 0 001 1h3a1 1 0 011 1v3a1 1 0 01-1 1h-1a2 2 0 100 4h1a1 1 0 011 1v3a1 1 0 01-1 1h-3a1 1 0 01-1-1v-1a2 2 0 10-4 0v1a1 1 0 01-1 1H7a1 1 0 01-1-1v-3a1 1 0 00-1-1H4a2 2 0 110-4h1a1 1 0 001-1V7a1 1 0 011-1h3a1 1 0 001-1V4z" />
          </svg>
          <p className="text-aethera-text-secondary">No plugins available</p>
        </div>
      ) : (
        <div className="space-y-3">
          {plugins.map((plugin) => (
            <div key={plugin.id} className="bg-aethera-surface rounded-xl border border-aethera-border p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3 min-w-0">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${plugin.enabled ? 'bg-aethera-primary/20' : 'bg-aethera-tertiary'}`}>
                    <svg className={`w-5 h-5 ${plugin.enabled ? 'text-aethera-primary' : 'text-aethera-text-secondary'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 4a2 2 0 114 0v1a1 1 0 001 1h3a1 1 0 011 1v3a1 1 0 01-1 1h-1a2 2 0 100 4h1a1 1 0 011 1v3a1 1 0 01-1 1h-3a1 1 0 01-1-1v-1a2 2 0 10-4 0v1a1 1 0 01-1 1H7a1 1 0 01-1-1v-3a1 1 0 00-1-1H4a2 2 0 110-4h1a1 1 0 001-1V7a1 1 0 011-1h3a1 1 0 001-1V4z" />
                    </svg>
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <h3 className="text-sm font-medium text-aethera-foreground">{plugin.name}</h3>
                      <StatusIndicator status={plugin.status} enabled={plugin.enabled} />
                    </div>
                    <p className="text-xs text-aethera-text-secondary mt-0.5 truncate">{plugin.description}</p>
                  </div>
                </div>

                <div className="flex items-center gap-2 flex-shrink-0">
                  {plugin.configurable && (
                    <button
                      onClick={() => setConfigPlugin(plugin)}
                      className="text-xs px-3 py-1.5 rounded-lg border border-aethera-border text-aethera-text-secondary hover:text-aethera-foreground hover:border-aethera-primary transition-colors"
                    >
                      Configure
                    </button>
                  )}
                  <ToggleSwitch
                    enabled={plugin.enabled}
                    onToggle={() => handleToggle(plugin.id, plugin.enabled)}
                    disabled={toggling.has(plugin.id)}
                  />
                </div>
              </div>

              {plugin.version && (
                <span className="mt-2 inline-block text-xs text-aethera-text-secondary">v{plugin.version}</span>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Config Modal */}
      {configPlugin && (
        <ConfigModal
          plugin={configPlugin}
          onSave={(config) => handleSaveConfig(configPlugin.id, config)}
          onClose={() => setConfigPlugin(null)}
          saving={saving}
        />
      )}
    </div>
  );
}

function StatusIndicator({ status, enabled }) {
  if (!enabled) {
    return <span className="text-xs px-1.5 py-0.5 rounded bg-gray-500/20 text-gray-400">Disabled</span>;
  }
  const colors = {
    running: 'bg-green-500/20 text-green-400',
    error: 'bg-red-500/20 text-red-400',
    stopped: 'bg-amber-500/20 text-amber-400',
    idle: 'bg-blue-500/20 text-blue-400',
  };
  return <span className={`text-xs px-1.5 py-0.5 rounded ${colors[status] || colors.idle}`}>{status || 'Active'}</span>;
}

function ToggleSwitch({ enabled, onToggle, disabled }) {
  return (
    <button
      onClick={onToggle}
      disabled={disabled}
      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none ${
        enabled ? 'bg-aethera-primary' : 'bg-aethera-tertiary'
      } ${disabled ? 'opacity-50' : ''}`}
    >
      <span
        className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
          enabled ? 'translate-x-6' : 'translate-x-1'
        }`}
      />
    </button>
  );
}

function ConfigModal({ plugin, onSave, onClose, saving }) {
  const [config, setConfig] = useState({ ...plugin.config });

  const fields = plugin.configSchema || Object.keys(plugin.config || {}).map((k) => ({ key: k, type: 'text', label: k }));

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-aethera-surface rounded-xl border border-aethera-border max-w-lg w-full max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="p-5 border-b border-aethera-border flex items-center justify-between">
          <h2 className="text-lg font-semibold text-aethera-foreground">Configure {plugin.name}</h2>
          <button onClick={onClose} className="text-aethera-text-secondary hover:text-aethera-foreground">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div className="p-5 space-y-4">
          {fields.map((field) => (
            <div key={field.key}>
              <label className="block text-sm font-medium text-aethera-foreground mb-1">{field.label || field.key}</label>
              {field.type === 'select' ? (
                <select
                  value={config[field.key] || ''}
                  onChange={(e) => setConfig((prev) => ({ ...prev, [field.key]: e.target.value }))}
                  className="w-full bg-aethera-tertiary border border-aethera-border rounded-lg px-3 py-2 text-sm text-aethera-foreground focus:outline-none focus:border-aethera-primary"
                >
                  {(field.options || []).map((opt) => (
                    <option key={opt.value ?? opt} value={opt.value ?? opt}>{opt.label ?? opt}</option>
                  ))}
                </select>
              ) : field.type === 'textarea' ? (
                <textarea
                  value={config[field.key] || ''}
                  onChange={(e) => setConfig((prev) => ({ ...prev, [field.key]: e.target.value }))}
                  rows={3}
                  className="w-full bg-aethera-tertiary border border-aethera-border rounded-lg px-3 py-2 text-sm text-aethera-foreground focus:outline-none focus:border-aethera-primary resize-none"
                />
              ) : (
                <input
                  type={field.type === 'password' ? 'password' : 'text'}
                  value={config[field.key] ?? ''}
                  onChange={(e) => setConfig((prev) => ({ ...prev, [field.key]: e.target.value }))}
                  className="w-full bg-aethera-tertiary border border-aethera-border rounded-lg px-3 py-2 text-sm text-aethera-foreground focus:outline-none focus:border-aethera-primary"
                />
              )}
            </div>
          ))}
          <div className="flex gap-3 pt-2">
            <button onClick={onClose} className="flex-1 py-2 rounded-lg border border-aethera-border text-aethera-text-secondary hover:text-aethera-foreground transition-colors">
              Cancel
            </button>
            <button onClick={() => onSave(config)} disabled={saving} className="flex-1 py-2 rounded-lg bg-aethera-primary text-white hover:bg-cyan-600 disabled:opacity-50 transition-colors">
              {saving ? 'Saving...' : 'Save'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}