import React, { useState } from 'react';
import { api } from '../../utils/api';
import ModelConfig from './ModelConfig';
import ProfileEditor from './ProfileEditor';
import PrivacySettings from './PrivacySettings';
import NotificationSettings from './NotificationSettings';

const TABS = [
  { key: 'general', label: 'General', icon: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z' },
  { key: 'models', label: 'Models', icon: 'M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z' },
  { key: 'profile', label: 'Profile', icon: 'M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z' },
  { key: 'privacy', label: 'Privacy', icon: 'M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z' },
  { key: 'notifications', label: 'Notifications', icon: 'M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9' },
];

export default function SettingsPanel() {
  const [activeTab, setActiveTab] = useState('general');
  const [generalSettings, setGeneralSettings] = useState({
    language: 'en',
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC',
    dateFormat: 'MM/DD/YYYY',
    theme: localStorage.getItem('aethera-theme') || 'dark',
    autoSave: true,
    compactMode: false,
  });
  const [saving, setSaving] = useState(false);

  const handleGeneralChange = (key, value) => {
    setGeneralSettings((prev) => ({ ...prev, [key]: value }));
  };

  const handleSaveGeneral = async () => {
    setSaving(true);
    try {
      await api.updateSettings(generalSettings);
    } catch (err) {
      console.error('Failed to save settings:', err);
    } finally {
      setSaving(false);
    }
  };

  const renderContent = () => {
    switch (activeTab) {
      case 'general':
        return (
          <div className="space-y-6">
            <SettingGroup title="Appearance">
              <SettingRow label="Theme" description="Choose light or dark mode">
                <select
                  value={generalSettings.theme}
                  onChange={(e) => {
                    handleGeneralChange('theme', e.target.value);
                    localStorage.setItem('aethera-theme', e.target.value);
                    const root = document.documentElement;
                    root.classList.toggle('light', e.target.value === 'light');
                    root.classList.toggle('dark', e.target.value === 'dark');
                  }}
                  className="bg-aethera-tertiary border border-aethera-border rounded-lg px-3 py-1.5 text-sm text-aethera-foreground focus:outline-none focus:border-aethera-primary"
                >
                  <option value="dark">Dark</option>
                  <option value="light">Light</option>
                </select>
              </SettingRow>
              <SettingRow label="Compact Mode" description="Reduce spacing and padding">
                <ToggleSwitch
                  enabled={generalSettings.compactMode}
                  onToggle={() => handleGeneralChange('compactMode', !generalSettings.compactMode)}
                />
              </SettingRow>
            </SettingGroup>

            <SettingGroup title="Regional">
              <SettingRow label="Language" description="Interface language">
                <select
                  value={generalSettings.language}
                  onChange={(e) => handleGeneralChange('language', e.target.value)}
                  className="bg-aethera-tertiary border border-aethera-border rounded-lg px-3 py-1.5 text-sm text-aethera-foreground focus:outline-none focus:border-aethera-primary"
                >
                  <option value="en">English</option>
                  <option value="es">Spanish</option>
                  <option value="fr">French</option>
                  <option value="de">German</option>
                </select>
              </SettingRow>
              <SettingRow label="Timezone" description="Your local timezone">
                <select
                  value={generalSettings.timezone}
                  onChange={(e) => handleGeneralChange('timezone', e.target.value)}
                  className="bg-aethera-tertiary border border-aethera-border rounded-lg px-3 py-1.5 text-sm text-aethera-foreground focus:outline-none focus:border-aethera-primary"
                >
                  <option value="UTC">UTC</option>
                  <option value="America/New_York">Eastern</option>
                  <option value="America/Chicago">Central</option>
                  <option value="America/Denver">Mountain</option>
                  <option value="America/Los_Angeles">Pacific</option>
                  <option value="Europe/London">London</option>
                </select>
              </SettingRow>
              <SettingRow label="Date Format" description="How dates are displayed">
                <select
                  value={generalSettings.dateFormat}
                  onChange={(e) => handleGeneralChange('dateFormat', e.target.value)}
                  className="bg-aethera-tertiary border border-aethera-border rounded-lg px-3 py-1.5 text-sm text-aethera-foreground focus:outline-none focus:border-aethera-primary"
                >
                  <option value="MM/DD/YYYY">MM/DD/YYYY</option>
                  <option value="DD/MM/YYYY">DD/MM/YYYY</option>
                  <option value="YYYY-MM-DD">YYYY-MM-DD</option>
                </select>
              </SettingRow>
            </SettingGroup>

            <SettingGroup title="Behavior">
              <SettingRow label="Auto-Save" description="Automatically save conversations">
                <ToggleSwitch
                  enabled={generalSettings.autoSave}
                  onToggle={() => handleGeneralChange('autoSave', !generalSettings.autoSave)}
                />
              </SettingRow>
            </SettingGroup>

            <div className="flex justify-end">
              <button
                onClick={handleSaveGeneral}
                disabled={saving}
                className="px-4 py-2 bg-aethera-primary text-white rounded-lg font-medium hover:bg-cyan-600 disabled:opacity-50 transition-colors"
              >
                {saving ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </div>
        );
      case 'models':
        return <ModelConfig />;
      case 'profile':
        return <ProfileEditor />;
      case 'privacy':
        return <PrivacySettings />;
      case 'notifications':
        return <NotificationSettings />;
      default:
        return null;
    }
  };

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-aethera-foreground">Settings</h1>
        <p className="text-aethera-text-secondary mt-1">Manage your Aethera preferences</p>
      </div>

      <div className="flex gap-6">
        {/* Sidebar Tabs */}
        <nav className="w-48 flex-shrink-0">
          <div className="space-y-1">
            {TABS.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors ${
                  activeTab === tab.key
                    ? 'bg-aethera-primary/20 text-aethera-foreground font-medium'
                    : 'text-aethera-text-secondary hover:text-aethera-foreground hover:bg-aethera-tertiary'
                }`}
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={tab.icon} />
                </svg>
                {tab.label}
              </button>
            ))}
          </div>
        </nav>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {renderContent()}
        </div>
      </div>
    </div>
  );
}

function SettingGroup({ title, children }) {
  return (
    <div>
      <h2 className="text-sm font-semibold text-aethera-foreground mb-3">{title}</h2>
      <div className="bg-aethera-surface rounded-xl border border-aethera-border divide-y divide-aethera-border">
        {children}
      </div>
    </div>
  );
}

function SettingRow({ label, description, children }) {
  return (
    <div className="px-4 py-3 flex items-center justify-between gap-4">
      <div>
        <p className="text-sm font-medium text-aethera-foreground">{label}</p>
        {description && <p className="text-xs text-aethera-text-secondary mt-0.5">{description}</p>}
      </div>
      <div className="flex-shrink-0">{children}</div>
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