import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../../utils/api';

const ENCRYPTED_FIELDS = ['ssn', 'npi', 'taxId', 'dateOfBirth', 'licenseNumber'];

export default function ProfileEditor() {
  const [profile, setProfile] = useState({
    name: '',
    role: '',
    specializations: [],
    preferences: {},
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [editMode, setEditMode] = useState(false);

  const fetchProfile = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get('/api/memory/profile');
      const json = await res.json();
      setProfile(json.profile || json || { name: '', role: '', specializations: [], preferences: {} });
    } catch (err) {
      setError(err.message || 'Failed to load profile');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchProfile(); }, [fetchProfile]);

  const handleSave = async () => {
    setSaving(true);
    setSaved(false);
    try {
      await api.post('/api/memory/profile', profile);
      setEditMode(false);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      setError(err.message || 'Failed to save profile');
    } finally {
      setSaving(false);
    }
  };

  const handleChange = (field, value) => {
    setProfile((prev) => ({ ...prev, [field]: value }));
  };

  const handleSpecToggle = (spec) => {
    setProfile((prev) => ({
      ...prev,
      specializations: prev.specializations.includes(spec)
        ? prev.specializations.filter((s) => s !== spec)
        : [...prev.specializations, spec],
    }));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-32">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-aethera-primary" />
      </div>
    );
  }

  if (error && !profile.name) {
    return (
      <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-400">
        <p className="font-medium">Failed to load profile</p>
        <p className="text-sm mt-1">{error}</p>
        <button onClick={fetchProfile} className="mt-2 text-sm underline hover:no-underline">Retry</button>
      </div>
    );
  }

  const SPECIALIZATION_OPTIONS = [
    'Healthcare Provider',
    'Payer Operations',
    'Clinical Documentation',
    'Medical Coding',
    'Revenue Cycle',
    'Compliance',
    'Finance',
    'Legal',
    'Software Engineering',
    'Data Analytics',
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-aethera-foreground">Profile</h2>
          <p className="text-xs text-aethera-text-secondary">Manage your identity and preferences</p>
        </div>
        <div className="flex items-center gap-2">
          {saved && (
            <span className="text-xs text-green-400 flex items-center gap-1">
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              Saved
            </span>
          )}
          {!editMode ? (
            <button
              onClick={() => setEditMode(true)}
              className="text-sm px-3 py-1.5 rounded-lg border border-aethera-border text-aethera-text-secondary hover:text-aethera-foreground hover:border-aethera-primary transition-colors"
            >
              Edit Profile
            </button>
          ) : (
            <div className="flex gap-2">
              <button
                onClick={() => { setEditMode(false); fetchProfile(); }}
                className="text-sm px-3 py-1.5 rounded-lg border border-aethera-border text-aethera-text-secondary hover:text-aethera-foreground transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="text-sm px-3 py-1.5 rounded-lg bg-aethera-primary text-white hover:bg-cyan-600 disabled:opacity-50 transition-colors"
              >
                {saving ? 'Saving...' : 'Save'}
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="bg-aethera-surface rounded-xl border border-aethera-border divide-y divide-aethera-border">
        {/* Name */}
        <div className="p-4">
          <label className="block text-xs font-medium text-aethera-text-secondary mb-1.5">Full Name</label>
          {editMode ? (
            <input
              type="text"
              value={profile.name || ''}
              onChange={(e) => handleChange('name', e.target.value)}
              className="w-full bg-aethera-tertiary border border-aethera-border rounded-lg px-3 py-2 text-sm text-aethera-foreground focus:outline-none focus:border-aethera-primary"
              placeholder="Your name"
            />
          ) : (
            <p className="text-sm text-aethera-foreground">{profile.name || 'Not set'}</p>
          )}
        </div>

        {/* Role */}
        <div className="p-4">
          <label className="block text-xs font-medium text-aethera-text-secondary mb-1.5">Role</label>
          {editMode ? (
            <input
              type="text"
              value={profile.role || ''}
              onChange={(e) => handleChange('role', e.target.value)}
              className="w-full bg-aethera-tertiary border border-aethera-border rounded-lg px-3 py-2 text-sm text-aethera-foreground focus:outline-none focus:border-aethera-primary"
              placeholder="e.g. Medical Coder, Practice Manager"
            />
          ) : (
            <p className="text-sm text-aethera-foreground">{profile.role || 'Not set'}</p>
          )}
        </div>

        {/* Email */}
        <div className="p-4">
          <label className="block text-xs font-medium text-aethera-text-secondary mb-1.5">
            Email
            {ENCRYPTED_FIELDS.includes('email') && (
              <span className="ml-1 text-xs text-aethera-primary" title="This field is encrypted">
                <svg className="w-3 h-3 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
              </span>
            )}
          </label>
          {editMode ? (
            <input
              type="email"
              value={profile.email || ''}
              onChange={(e) => handleChange('email', e.target.value)}
              className="w-full bg-aethera-tertiary border border-aethera-border rounded-lg px-3 py-2 text-sm text-aethera-foreground focus:outline-none focus:border-aethera-primary"
              placeholder="your@email.com"
            />
          ) : (
            <p className="text-sm text-aethera-foreground">{profile.email || 'Not set'}</p>
          )}
        </div>

        {/* NPI */}
        <div className="p-4">
          <label className="block text-xs font-medium text-aethera-text-secondary mb-1.5">
            NPI Number
            <span className="ml-1 text-xs text-aethera-primary" title="This field is encrypted at rest">
              <svg className="w-3 h-3 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
              Encrypted
            </span>
          </label>
          {editMode ? (
            <input
              type="password"
              value={profile.npi || ''}
              onChange={(e) => handleChange('npi', e.target.value)}
              className="w-full bg-aethera-tertiary border border-aethera-border rounded-lg px-3 py-2 text-sm text-aethera-foreground focus:outline-none focus:border-aethera-primary"
              placeholder="Enter NPI"
            />
          ) : (
            <p className="text-sm text-aethera-foreground">{profile.npi ? '********' : 'Not set'}</p>
          )}
        </div>

        {/* Specializations */}
        <div className="p-4">
          <label className="block text-xs font-medium text-aethera-text-secondary mb-1.5">Specializations</label>
          {editMode ? (
            <div className="flex flex-wrap gap-2">
              {SPECIALIZATION_OPTIONS.map((spec) => (
                <button
                  key={spec}
                  onClick={() => handleSpecToggle(spec)}
                  className={`text-xs px-2.5 py-1 rounded-full transition-colors ${
                    profile.specializations?.includes(spec)
                      ? 'bg-aethera-primary text-white'
                      : 'bg-aethera-tertiary text-aethera-text-secondary hover:text-aethera-foreground'
                  }`}
                >
                  {spec}
                </button>
              ))}
            </div>
          ) : (
            <div className="flex flex-wrap gap-1.5">
              {profile.specializations?.length > 0
                ? profile.specializations.map((spec) => (
                    <span key={spec} className="text-xs px-2 py-0.5 rounded-full bg-aethera-primary/20 text-aethera-primary">{spec}</span>
                  ))
                : <p className="text-sm text-aethera-text-secondary">None selected</p>
              }
            </div>
          )}
        </div>

        {/* Preferences */}
        <div className="p-4">
          <label className="block text-xs font-medium text-aethera-text-secondary mb-1.5">Preferences</label>
          {editMode ? (
            <textarea
              value={profile.preferences ? JSON.stringify(profile.preferences, null, 2) : '{}'}
              onChange={(e) => {
                try {
                  handleChange('preferences', JSON.parse(e.target.value));
                } catch {}
              }}
              rows={4}
              className="w-full bg-aethera-tertiary border border-aethera-border rounded-lg px-3 py-2 text-sm text-aethera-foreground font-mono focus:outline-none focus:border-aethera-primary resize-none"
            />
          ) : (
            <pre className="text-xs text-aethera-text-secondary bg-aethera-tertiary/50 rounded-lg p-3 overflow-x-auto">
              {JSON.stringify(profile.preferences || {}, null, 2)}
            </pre>
          )}
        </div>
      </div>
    </div>
  );
}