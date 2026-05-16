import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../../utils/api';

const CHANNELS = [
  { key: 'ui', label: 'In-App (UI)', icon: 'M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z' },
  { key: 'telegram', label: 'Telegram', icon: 'M12 19l9 2-9-18-9 18 9-2zm0 0v-8' },
  { key: 'push', label: 'Push Notifications', icon: 'M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9' },
  { key: 'email', label: 'Email', icon: 'M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z' },
];

const ALERT_TYPES = [
  { key: 'critical', label: 'Critical Alerts', description: 'System failures and critical errors' },
  { key: 'urgent', label: 'Urgent Alerts', description: 'High-priority items needing attention' },
  { key: 'warnings', label: 'Warnings', description: 'Non-critical issues and degradations' },
  { key: 'info', label: 'Informational', description: 'General updates and status changes' },
  { key: 'task_complete', label: 'Task Completion', description: 'When queued tasks finish' },
  { key: 'model_errors', label: 'Model Errors', description: 'AI model failures or rate limits' },
];

export default function NotificationSettings() {
  const [settings, setSettings] = useState({
    channels: { ui: true, telegram: false, push: true, email: false },
    alertTypes: { critical: true, urgent: true, warnings: true, info: false, task_complete: true, model_errors: true },
    quietHoursEnabled: false,
    quietHoursStart: '22:00',
    quietHoursEnd: '07:00',
    digestEnabled: false,
    digestFrequency: 'daily',
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState(null);

  const fetchSettings = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.get('/api/settings/notifications');
      const json = await res.json();
      setSettings((prev) => ({ ...prev, ...json.settings, ...json }));
    } catch {
      // Use defaults
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchSettings(); }, [fetchSettings]);

  const handleSave = async () => {
    setSaving(true);
    setSaved(false);
    setError(null);
    try {
      await api.post('/api/settings/notifications', settings);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      setError(err.message || 'Failed to save notification settings');
    } finally {
      setSaving(false);
    }
  };

  const toggleChannel = (key) => {
    setSettings((prev) => ({
      ...prev,
      channels: { ...prev.channels, [key]: !prev.channels[key] },
    }));
  };

  const toggleAlertType = (key) => {
    setSettings((prev) => ({
      ...prev,
      alertTypes: { ...prev.alertTypes, [key]: !prev.alertTypes[key] },
    }));
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
          <h2 className="text-sm font-semibold text-aethera-foreground">Notifications</h2>
          <p className="text-xs text-aethera-text-secondary">Configure how and when you receive alerts</p>
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

      {/* Delivery Channels */}
      <div>
        <h3 className="text-xs font-medium text-aethera-text-secondary uppercase tracking-wider mb-3">Delivery Channels</h3>
        <div className="bg-aethera-surface rounded-xl border border-aethera-border divide-y divide-aethera-border">
          {CHANNELS.map((channel) => (
            <div key={channel.key} className="p-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-aethera-primary/20 flex items-center justify-center">
                  <svg className="w-4 h-4 text-aethera-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={channel.icon} />
                  </svg>
                </div>
                <div>
                  <p className="text-sm font-medium text-aethera-foreground">{channel.label}</p>
                </div>
              </div>
              <ToggleSwitch enabled={settings.channels[channel.key]} onToggle={() => toggleChannel(channel.key)} />
            </div>
          ))}
        </div>
      </div>

      {/* Alert Types */}
      <div>
        <h3 className="text-xs font-medium text-aethera-text-secondary uppercase tracking-wider mb-3">Alert Types</h3>
        <div className="bg-aethera-surface rounded-xl border border-aethera-border divide-y divide-aethera-border">
          {ALERT_TYPES.map((type) => (
            <div key={type.key} className="p-4 flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-aethera-foreground">{type.label}</p>
                <p className="text-xs text-aethera-text-secondary mt-0.5">{type.description}</p>
              </div>
              <ToggleSwitch enabled={settings.alertTypes[type.key]} onToggle={() => toggleAlertType(type.key)} />
            </div>
          ))}
        </div>
      </div>

      {/* Quiet Hours */}
      <div>
        <h3 className="text-xs font-medium text-aethera-text-secondary uppercase tracking-wider mb-3">Quiet Hours</h3>
        <div className="bg-aethera-surface rounded-xl border border-aethera-border divide-y divide-aethera-border">
          <div className="p-4 flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-aethera-foreground">Enable Quiet Hours</p>
              <p className="text-xs text-aethera-text-secondary mt-0.5">Mute non-critical notifications during specified hours</p>
            </div>
            <ToggleSwitch enabled={settings.quietHoursEnabled} onToggle={() => setSettings((prev) => ({ ...prev, quietHoursEnabled: !prev.quietHoursEnabled }))} />
          </div>
          {settings.quietHoursEnabled && (
            <div className="p-4 flex items-center gap-4">
              <div>
                <label className="block text-xs text-aethera-text-secondary mb-1">From</label>
                <input
                  type="time"
                  value={settings.quietHoursStart}
                  onChange={(e) => setSettings((prev) => ({ ...prev, quietHoursStart: e.target.value }))}
                  className="bg-aethera-tertiary border border-aethera-border rounded-lg px-3 py-1.5 text-sm text-aethera-foreground focus:outline-none focus:border-aethera-primary"
                />
              </div>
              <svg className="w-4 h-4 text-aethera-text-secondary mt-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
              </svg>
              <div>
                <label className="block text-xs text-aethera-text-secondary mb-1">To</label>
                <input
                  type="time"
                  value={settings.quietHoursEnd}
                  onChange={(e) => setSettings((prev) => ({ ...prev, quietHoursEnd: e.target.value }))}
                  className="bg-aethera-tertiary border border-aethera-border rounded-lg px-3 py-1.5 text-sm text-aethera-foreground focus:outline-none focus:border-aethera-primary"
                />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Digest */}
      <div>
        <h3 className="text-xs font-medium text-aethera-text-secondary uppercase tracking-wider mb-3">Notification Digest</h3>
        <div className="bg-aethera-surface rounded-xl border border-aethera-border divide-y divide-aethera-border">
          <div className="p-4 flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-aethera-foreground">Enable Digest</p>
              <p className="text-xs text-aethera-text-secondary mt-0.5">Receive a summary instead of individual notifications</p>
            </div>
            <ToggleSwitch enabled={settings.digestEnabled} onToggle={() => setSettings((prev) => ({ ...prev, digestEnabled: !prev.digestEnabled }))} />
          </div>
          {settings.digestEnabled && (
            <div className="p-4 flex items-center justify-between">
              <p className="text-sm font-medium text-aethera-foreground">Frequency</p>
              <select
                value={settings.digestFrequency}
                onChange={(e) => setSettings((prev) => ({ ...prev, digestFrequency: e.target.value }))}
                className="bg-aethera-tertiary border border-aethera-border rounded-lg px-3 py-1.5 text-sm text-aethera-foreground focus:outline-none focus:border-aethera-primary"
              >
                <option value="hourly">Hourly</option>
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
              </select>
            </div>
          )}
        </div>
      </div>

      {/* Save Button */}
      <div className="flex justify-end">
        <button
          onClick={handleSave}
          disabled={saving}
          className="px-4 py-2 bg-aethera-primary text-white rounded-lg font-medium hover:bg-cyan-600 disabled:opacity-50 transition-colors"
        >
          {saving ? 'Saving...' : 'Save Notification Settings'}
        </button>
      </div>

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