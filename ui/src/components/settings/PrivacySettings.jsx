import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../../utils/api';

export default function PrivacySettings() {
  const [settings, setSettings] = useState({
    phiRouting: 'local_only',
    encryptionLevel: 'aes256',
    dataRetention: 365,
    auditLogEnabled: true,
    anonymizationEnabled: true,
    crossBorderDataAllowed: false,
    thirdPartySharing: false,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [auditLog, setAuditLog] = useState([]);
  const [showAuditLog, setShowAuditLog] = useState(false);
  const [apiKeyInput, setApiKeyInput] = useState(api.getApiKey());
  const [apiKeySaved, setApiKeySaved] = useState(false);

  const handleSaveApiKey = () => {
    api.setApiKey(apiKeyInput.trim());
    setApiKeySaved(true);
    setTimeout(() => setApiKeySaved(false), 3000);
  };

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get('/api/settings/privacy');
      const json = await res.json();
      setSettings(json.settings || json || settings);
    } catch (err) {
      // Use defaults if endpoint not available
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchAuditLog = useCallback(async () => {
    try {
      const res = await api.get('/api/settings/privacy/audit-log');
      const json = await res.json();
      setAuditLog(json.entries || json || []);
    } catch (err) {
      setAuditLog([]);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleSave = async () => {
    setSaving(true);
    setSaved(false);
    try {
      await api.post('/api/settings/privacy', settings);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      setError(err.message || 'Failed to save privacy settings');
    } finally {
      setSaving(false);
    }
  };

  const handleChange = (key, value) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
  };

  const handleViewAuditLog = () => {
    setShowAuditLog(true);
    fetchAuditLog();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-32">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-aethera-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-aethera-foreground">Privacy & Security</h2>
          <p className="text-xs text-aethera-text-secondary">Control how sensitive data is handled</p>
        </div>
        {saved && (
          <span className="text-xs text-green-400 flex items-center gap-1">
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            Settings saved
          </span>
        )}
      </div>

      <div className="bg-aethera-surface rounded-xl border border-aethera-border divide-y divide-aethera-border">
        {/* API Access Key (required when the backend has API auth enabled) */}
        <div className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-aethera-foreground">API Access Key</p>
              <p className="text-xs text-aethera-text-secondary mt-0.5">
                Sent as a bearer token. Required when the server runs with API_AUTH_ENABLED.
              </p>
            </div>
            {apiKeySaved && (
              <span className="text-xs text-green-400">Key saved</span>
            )}
          </div>
          <div className="mt-2 flex items-center gap-2">
            <input
              type="password"
              value={apiKeyInput}
              onChange={(e) => setApiKeyInput(e.target.value)}
              placeholder="Paste your API key"
              autoComplete="off"
              className="flex-1 bg-aethera-tertiary border border-aethera-border rounded-lg px-3 py-1.5 text-sm text-aethera-foreground focus:outline-none focus:border-aethera-primary font-mono"
            />
            <button
              onClick={handleSaveApiKey}
              className="px-3 py-1.5 bg-aethera-primary text-white rounded-lg text-sm font-medium hover:bg-cyan-600 transition-colors"
            >
              Save Key
            </button>
            <button
              onClick={() => { setApiKeyInput(''); api.setApiKey(''); setApiKeySaved(true); setTimeout(() => setApiKeySaved(false), 3000); }}
              className="px-3 py-1.5 border border-aethera-border text-aethera-text-secondary rounded-lg text-sm hover:text-aethera-foreground hover:border-aethera-primary transition-colors"
            >
              Clear
            </button>
          </div>
        </div>

        {/* PHI Routing */}
        <div className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-aethera-foreground">PHI Data Routing</p>
              <p className="text-xs text-aethera-text-secondary mt-0.5">Control where Protected Health Information is processed</p>
            </div>
            <select
              value={settings.phiRouting}
              onChange={(e) => handleChange('phiRouting', e.target.value)}
              className="bg-aethera-tertiary border border-aethera-border rounded-lg px-3 py-1.5 text-sm text-aethera-foreground focus:outline-none focus:border-aethera-primary"
            >
              <option value="local_only">Local Only</option>
              <option value="local_preferred">Local Preferred</option>
              <option value="cloud_allowed">Cloud Allowed</option>
            </select>
          </div>
          {settings.phiRouting === 'cloud_allowed' && (
            <div className="mt-2 p-2 rounded-lg bg-amber-500/10 text-amber-400 text-xs">
              Warning: Allowing PHI in cloud processing may have compliance implications. Ensure your BAA is current.
            </div>
          )}
        </div>

        {/* Encryption Level */}
        <div className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-aethera-foreground">Encryption Level</p>
              <p className="text-xs text-aethera-text-secondary mt-0.5">Data encryption standard for stored and transmitted data</p>
            </div>
            <select
              value={settings.encryptionLevel}
              onChange={(e) => handleChange('encryptionLevel', e.target.value)}
              className="bg-aethera-tertiary border border-aethera-border rounded-lg px-3 py-1.5 text-sm text-aethera-foreground focus:outline-none focus:border-aethera-primary"
            >
              <option value="aes128">AES-128</option>
              <option value="aes256">AES-256</option>
              <option value="aes256_gcm">AES-256-GCM</option>
            </select>
          </div>
        </div>

        {/* Data Retention */}
        <div className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-aethera-foreground">Data Retention</p>
              <p className="text-xs text-aethera-text-secondary mt-0.5">How long data is retained before automatic deletion</p>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="number"
                value={settings.dataRetention}
                onChange={(e) => handleChange('dataRetention', parseInt(e.target.value, 10) || 0)}
                min={1}
                max={3650}
                className="w-20 bg-aethera-tertiary border border-aethera-border rounded-lg px-3 py-1.5 text-sm text-aethera-foreground focus:outline-none focus:border-aethera-primary text-right"
              />
              <span className="text-xs text-aethera-text-secondary">days</span>
            </div>
          </div>
          <div className="mt-2 flex gap-2">
            {[30, 90, 180, 365].map((days) => (
              <button
                key={days}
                onClick={() => handleChange('dataRetention', days)}
                className={`text-xs px-2 py-0.5 rounded-full transition-colors ${
                  settings.dataRetention === days
                    ? 'bg-aethera-primary text-white'
                    : 'bg-aethera-tertiary text-aethera-text-secondary hover:text-aethera-foreground'
                }`}
              >
                {days}d
              </button>
            ))}
          </div>
        </div>

        {/* Toggles */}
        <div className="p-4 flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-aethera-foreground">Anonymization</p>
            <p className="text-xs text-aethera-text-secondary mt-0.5">Automatically anonymize PHI before cloud processing</p>
          </div>
          <ToggleSwitch enabled={settings.anonymizationEnabled} onToggle={() => handleChange('anonymizationEnabled', !settings.anonymizationEnabled)} />
        </div>

        <div className="p-4 flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-aethera-foreground">Cross-Border Data Transfer</p>
            <p className="text-xs text-aethera-text-secondary mt-0.5">Allow data to be processed outside your region</p>
          </div>
          <ToggleSwitch enabled={settings.crossBorderDataAllowed} onToggle={() => handleChange('crossBorderDataAllowed', !settings.crossBorderDataAllowed)} />
        </div>

        <div className="p-4 flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-aethera-foreground">Third-Party Data Sharing</p>
            <p className="text-xs text-aethera-text-secondary mt-0.5">Allow sharing anonymized data with third parties</p>
          </div>
          <ToggleSwitch enabled={settings.thirdPartySharing} onToggle={() => handleChange('thirdPartySharing', !settings.thirdPartySharing)} />
        </div>

        <div className="p-4 flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-aethera-foreground">Audit Logging</p>
            <p className="text-xs text-aethera-text-secondary mt-0.5">Log all data access and modifications</p>
          </div>
          <div className="flex items-center gap-2">
            <ToggleSwitch enabled={settings.auditLogEnabled} onToggle={() => handleChange('auditLogEnabled', !settings.auditLogEnabled)} />
            {settings.auditLogEnabled && (
              <button
                onClick={handleViewAuditLog}
                className="text-xs px-2.5 py-1 rounded-lg border border-aethera-border text-aethera-text-secondary hover:text-aethera-foreground hover:border-aethera-primary transition-colors"
              >
                View Log
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Save Button */}
      <div className="flex justify-end">
        <button
          onClick={handleSave}
          disabled={saving}
          className="px-4 py-2 bg-aethera-primary text-white rounded-lg font-medium hover:bg-cyan-600 disabled:opacity-50 transition-colors"
        >
          {saving ? 'Saving...' : 'Save Privacy Settings'}
        </button>
      </div>

      {/* Audit Log Modal */}
      {showAuditLog && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={() => setShowAuditLog(false)}>
          <div className="bg-aethera-surface rounded-xl border border-aethera-border max-w-2xl w-full max-h-[80vh] overflow-hidden" onClick={(e) => e.stopPropagation()}>
            <div className="px-4 py-3 border-b border-aethera-border flex items-center justify-between">
              <h2 className="text-lg font-semibold text-aethera-foreground">Audit Log</h2>
              <button onClick={() => setShowAuditLog(false)} className="text-aethera-text-secondary hover:text-aethera-foreground">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="max-h-[60vh] overflow-y-auto">
              {auditLog.length === 0 ? (
                <p className="p-6 text-center text-aethera-text-secondary text-sm">No audit log entries</p>
              ) : (
                <div className="divide-y divide-aethera-border">
                  {auditLog.map((entry, i) => (
                    <div key={i} className="p-3 hover:bg-aethera-tertiary/50 transition-colors">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-aethera-foreground">{entry.action}</span>
                        <span className="text-xs text-aethera-text-secondary">{new Date(entry.timestamp).toLocaleString()}</span>
                      </div>
                      <p className="text-xs text-aethera-text-secondary mt-0.5">{entry.user || entry.actor || 'System'} - {entry.resource || ''}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-400 text-sm">{error}</div>
      )}
    </div>
  );
}

function ToggleSwitch({ enabled, onToggle }) {
  return (
    <button
      onClick={onToggle}
      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none ${
        enabled ? 'bg-aethera-primary' : 'bg-aethera-tertiary'
      }`}
    >
      <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${enabled ? 'translate-x-6' : 'translate-x-1'}`} />
    </button>
  );
}